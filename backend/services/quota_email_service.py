"""Quota Email Service — quota warning + exceeded transactional emails.

Onda 6 (v5.8). Triggered by `background_service.quota_warning_sweep`,
this service renders + delivers the two quota emails:

    quota_warning   — usage hit 80% of effective_limit (advisory upsell)
    quota_exceeded  — usage hit/passed 100% of effective_limit (info)

Idempotency:
    Each (org, metric_key, level, period_start) tuple has a unique index
    in `org_quota_notices`. The service inserts the notice BEFORE sending
    the email so a race in concurrent sweeps results in at most one send.
    If the email send returns False (Brevo failure), the notice still
    counts as "attempted" — we don't retry within the same period because
    a flaky Brevo can otherwise spam the merchant on every cron tick.

Locale resolution:
    Reuses `_resolve_user_email_locale` from order_email_service (the
    chain we consolidated in Onde 1-7): user.locale > storefront default
    > "it". So a German admin with email_alerts on receives the warning
    email in German.

Branding:
    Reuses `_load_store_context` (Onde 5 multi-store) for sender_name,
    reply_to, store_name. Multi-store orgs see the right brand on every
    quota email.

Public API:
    notify_quota_warning_email(org_id, metric_key, level, used, limit, ...)
        Renders + sends + records. Returns True on success, False on
        skip (already sent this period) / failure.

This service is intentionally NOT called from request-handling code —
only from the cron. Synchronous quota checks at request time use 429
responses with the structured paywall hint (see Onda 4 enforcement).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from services.email_service import _t, _wrap_template, send_email, APP_URL

logger = logging.getLogger(__name__)


# ── Metric → module_key mapping ──────────────────────────────────────────────
#
# The sweep iterates a fixed set of metrics; each is owned by a module.
# Used by `notify_quota_warning_email` to record `module_key` on the notice.

METRIC_TO_MODULE = {
    "chat": "ai_assistant",
    "digest": "ai_assistant",
    "data_rows": "cashflow_monitor",
    "email_alerts": "cashflow_monitor",
    "products": "product_catalog",
    "orders_monthly": "commerce",
    "stores_max": "commerce",
}

# Which add-on slug should we suggest as the cheapest extension for each
# metric. Empty when there is no add-on for the metric (use generic
# upgrade copy).
#
# v5.8 / Onda 10 Step B.4 — Now consultable also via the catalog:
# `commercial_plans.{slug}.addon_ctas` (admin-editable). The dict below
# remains the GLOBAL fallback for metrics not mapped at the per-plan
# level, AND for the case where the org has no commercial_plan_slug.
#
# Resolution order (used by `resolve_addon_for_metric()`):
#   1. plan_doc.addon_ctas[metric_key]  (per-plan override, admin-editable)
#   2. METRIC_TO_ADDON_OFFER[metric_key] (global fallback, this dict)
#   3. None  → frontend renders "Upgrade plan" generic CTA

METRIC_TO_ADDON_OFFER = {
    "chat": "addon_ai_chat_pack",
    "orders_monthly": "addon_orders_pack",
    "stores_max": "addon_extra_store",
    # data_rows / digest / email_alerts have no add-on at v5.8 — fall
    # back to "upgrade plan" CTA.
}


async def resolve_addon_for_metric(metric_key: str, plan_slug: str) -> str | None:
    """Return the addon_slug to suggest for a given (metric, plan), or None.

    Onda 10 Step B.4: per-plan override > global fallback. Admin can
    override the global mapping by setting `addon_ctas` on a specific
    CommercialPlan, e.g. to point Solo to a Solo-specific orders pack.
    """
    try:
        from repositories import billing_repository
        plan = await billing_repository.get_commercial_plan(plan_slug)
        if plan and isinstance(plan.get("addon_ctas"), dict):
            override = plan["addon_ctas"].get(metric_key)
            if override:
                return override
    except Exception:
        pass
    return METRIC_TO_ADDON_OFFER.get(metric_key)

# Whether the metric is "blocking" when exceeded (hard block) vs "soft"
# (always succeeds, only quota-billed). Drives the body copy choice
# between `quota_exceeded_outro_blocking` vs `quota_exceeded_outro_soft`.
METRIC_BLOCKING = {
    "chat": True,            # 429 in check_module_access
    "digest": True,
    "data_rows": True,
    "products": True,        # product_catalog gate
    "stores_max": True,      # routers/stores.py 429
    "orders_monthly": True,  # routers/public.py 429
    "email_alerts": False,   # email_alerts is a flag, never quota'd
}


def _current_period_start() -> str:
    """ISO YYYY-MM for the calendar month, used as the period_start key
    for monthly quotas. State-based metrics (stores_max / products) reuse
    the same monotonic identifier — fine for the once-per-period semantic
    of the unique index, no extra logic needed."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _metric_label(metric_key: str, locale: str) -> str:
    """Translated user-facing name of a metric, e.g. 'chat AI'."""
    label_key = f"quota_metric_{metric_key}"
    label = _t(label_key, locale)
    if label == label_key:  # fallback when key not in translations
        label = _t("quota_metric_fallback", locale)
    return label


def _addon_offer_text(metric_key: str, locale: str) -> str:
    """Translated upsell copy for the metric — refers to a specific
    add-on slug when one exists, or the generic 'upgrade plan' line."""
    if metric_key in METRIC_TO_ADDON_OFFER:
        return _t(f"quota_addon_offer_{metric_key}", locale)
    return _t("quota_addon_offer_fallback", locale)


async def notify_quota_warning_email(
    org_id: str,
    metric_key: str,
    level: str,                     # "warn_80" | "exceeded"
    used: int,
    effective_limit: int,
    *,
    recipient_email: Optional[str] = None,
) -> bool:
    """Render + send the quota email and record the idempotency notice.

    Returns:
        True   — notice recorded for the first time and email send attempted
        False  — already sent this period (deduplicated) or input invalid

    Best-effort: Mongo / Brevo errors are logged but never raised.
    """
    if level not in ("warn_80", "exceeded"):
        logger.warning("quota_email: invalid level=%s for org=%s metric=%s", level, org_id, metric_key)
        return False
    if metric_key not in METRIC_TO_MODULE:
        logger.warning("quota_email: unknown metric_key=%s for org=%s", metric_key, org_id)
        return False

    from repositories import billing_repository
    from services.order_email_service import _resolve_user_email_locale, _load_store_context

    period_start = _current_period_start()

    # Idempotency check (cheap pre-filter; the unique index is the
    # actual guarantee — see record_quota_notice).
    if await billing_repository.has_quota_notice(org_id, metric_key, level, period_start):
        return False

    # Resolve recipient email if not provided. Priority:
    #   1. explicit recipient_email arg
    #   2. store.notification_email (Onde 5)
    #   3. first admin of the org
    if not recipient_email:
        from database import organizations_collection, users_collection
        org_doc = await organizations_collection.find_one(
            {"id": org_id},
            {"_id": 0, "store_settings": 1, "store_id": 1},
        ) or {}
        ss = org_doc.get("store_settings") or {}
        recipient_email = ss.get("notification_email")
        if not recipient_email:
            admin = await users_collection.find_one(
                {"organization_id": org_id, "role": {"$in": ["admin"]}, "is_active": True},
                {"_id": 0, "email": 1},
                sort=[("created_at", 1)],
            )
            recipient_email = (admin or {}).get("email")

    if not recipient_email:
        logger.warning("quota_email: no recipient resolvable for org=%s — skipping send", org_id)
        # Record notice anyway so we don't keep retrying every 6h.
        await billing_repository.record_quota_notice({
            "id": __import__("models.common", fromlist=["generate_id"]).generate_id(),
            "organization_id": org_id,
            "metric_key": metric_key,
            "module_key": METRIC_TO_MODULE[metric_key],
            "level": level,
            "period_start": period_start,
            "used": used,
            "effective_limit": effective_limit,
            "recipient_email": None,
            "locale": "it",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return False

    # Locale + branding
    locale = await _resolve_user_email_locale(org_id, recipient_email)
    ctx = await _load_store_context(org_id)

    metric_label = _metric_label(metric_key, locale)
    settings_url = f"{APP_URL}/settings/billing"
    plans_url = f"{APP_URL}/plans"

    subject = _t(f"quota_{level}_subject", locale, metric=metric_label)
    intro = _t(f"quota_{level}_intro", locale, metric=metric_label, used=used, limit=effective_limit)

    if level == "warn_80":
        outro = _t("quota_warning_outro", locale)
    else:
        outro_key = (
            "quota_exceeded_outro_blocking"
            if METRIC_BLOCKING.get(metric_key, True)
            else "quota_exceeded_outro_soft"
        )
        outro = _t(outro_key, locale)

    cta_addon_label = _t("quota_warning_cta_addon", locale)
    cta_upgrade_label = _t("quota_warning_cta_upgrade", locale)
    addon_offer = _addon_offer_text(metric_key, locale)

    # Two CTA buttons — addon first (cheaper, more aligned to need),
    # upgrade-plan fallback for metrics without a dedicated add-on.
    has_addon = metric_key in METRIC_TO_ADDON_OFFER
    addon_btn = (
        f'<p style="text-align:center;margin:20px 0 10px;">'
        f'<a href="{plans_url}#addons" class="btn">{cta_addon_label}</a>'
        f'</p>' if has_addon else ""
    )
    upgrade_btn = (
        f'<p style="text-align:center;margin:8px 0;">'
        f'<a href="{plans_url}" class="btn" style="background:#374151;">{cta_upgrade_label}</a>'
        f'</p>'
    )

    body_html = (
        f'<p>{_t("greeting", locale)},</p>'
        f'<p>{intro}</p>'
        f'<p>{outro}</p>'
        f'<p style="color:#6b7280;font-style:italic;">{addon_offer}</p>'
        f'{addon_btn}'
        f'{upgrade_btn}'
        f'<p style="color:#9ca3af;font-size:12px;margin-top:20px;">'
        f'{_t("quota_period_label", locale, period=period_start)}'
        f'</p>'
    )

    html = _wrap_template(
        body_html, locale,
        reply_to=ctx.get("reply_to"),
        store_name=ctx.get("store_name"),
    )

    # Record the notice FIRST, so a race in concurrent sweeps loses
    # at the unique-index level (DuplicateKeyError → False). The email
    # send is best-effort after.
    inserted = await billing_repository.record_quota_notice({
        "id": __import__("models.common", fromlist=["generate_id"]).generate_id(),
        "organization_id": org_id,
        "metric_key": metric_key,
        "module_key": METRIC_TO_MODULE[metric_key],
        "level": level,
        "period_start": period_start,
        "used": used,
        "effective_limit": effective_limit,
        "recipient_email": recipient_email,
        "locale": locale,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    if not inserted:
        # Lost the idempotency race — already sent this period.
        return False

    try:
        ok = send_email(
            recipient_email,
            subject,
            html,
            reply_to=ctx.get("reply_to"),
            sender_name=ctx.get("sender_name"),
        )
        logger.info(
            "quota_email: org=%s metric=%s level=%s used=%d/%d sent_to=%s ok=%s locale=%s",
            org_id, metric_key, level, used, effective_limit, recipient_email, ok, locale,
        )
        return bool(ok)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.error(
            "quota_email: send failed org=%s metric=%s level=%s: %s",
            org_id, metric_key, level, exc,
        )
        return False
