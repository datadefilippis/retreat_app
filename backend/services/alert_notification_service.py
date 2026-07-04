"""
Alert Notification Service — email dispatch for alert events.

- notify_high_severity_batch: immediate email for HIGH alerts (max 1/day)
- send_weekly_alert_digest: weekly summary of open alerts

Uses existing email_service.send_email() for Brevo delivery.

v14.0 changes:
  - Reads email_high_alerts / email_weekly_digest from org preferences (was ignored)
  - Rate limit persisted to MongoDB (survives restart)
  - Cooldown increased from 6h to 24h
  - Structural alert suppression (no re-fire email for concentration alerts)
  - Improved email templates with footer links
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List

from models import Alert

logger = logging.getLogger(__name__)

# Cooldown: max 1 HIGH alert email per org per 24 hours
_HIGH_COOLDOWN_HOURS = 24

# Entity key patterns for structural alerts that should not re-fire email
_STRUCTURAL_PATTERNS = ("supplier_", "product_", "revenue_conc_")

# Email subject templates per locale
_SUBJECTS = {
    "it": {
        "high_alert": "AFianco — {count} alert critici richiedono attenzione",
        "weekly_digest": "AFianco — Riepilogo settimanale alert",
    },
    "en": {
        "high_alert": "AFianco — {count} critical alerts need attention",
        "weekly_digest": "AFianco — Weekly alert digest",
    },
    "de": {
        "high_alert": "AFianco — {count} kritische Alerts erfordern Aufmerksamkeit",
        "weekly_digest": "AFianco — Woechentliche Alert-Uebersicht",
    },
    "fr": {
        "high_alert": "AFianco — {count} alertes critiques necessitent attention",
        "weekly_digest": "AFianco — Resume hebdomadaire des alertes",
    },
}

# Email footer template (Onda 7) — locale-aware. Built dynamically by
# `_render_alert_footer(locale)` so each recipient sees the footer in
# their language, not the legacy IT default. APP_URL is read at call
# time to keep the dev/prod hosts swappable.
def _render_alert_footer(locale: str) -> str:
    """Return the alert email footer HTML in the given locale.

    Used by both notify_high_severity_batch and send_weekly_alert_digest.
    Pulls labels via _t() so the 4 locales share one shape.
    """
    from services.email_service import _t, APP_URL
    alerts_url = f"{APP_URL}/cashflow?tab=alerts"
    settings_url = f"{APP_URL}/settings"
    view = _t("cashflow_alert_footer_view", locale)
    settings = _t("cashflow_alert_footer_settings", locale)
    disable = _t("cashflow_alert_footer_disable", locale, settings_url=settings_url)
    return f"""
<div style="margin-top:30px; padding-top:20px; border-top:1px solid #E5E7EB; font-size:12px; color:#9CA3AF;">
    <p>
        <a href="{alerts_url}" style="color:#2563EB; text-decoration:none;">{view}</a>
        &nbsp;\u00b7&nbsp;
        <a href="{settings_url}" style="color:#2563EB; text-decoration:none;">{settings}</a>
    </p>
    <p style="margin-top:8px;">{disable}</p>
</div>
"""


async def _get_alert_settings(org_id: str) -> dict:
    """Load alert email preferences from module_configs_collection."""
    from database import module_configs_collection
    config = await module_configs_collection.find_one(
        {"organization_id": org_id, "module_key": "cashflow_monitor"},
        {"_id": 0, "settings": 1},
    )
    return (config or {}).get("settings", {})


async def _check_rate_limit(org_id: str, settings: dict) -> bool:
    """Check persistent rate limit. Returns True if email is allowed."""
    last_sent = settings.get("_last_high_email_at")
    if not last_sent:
        return True
    try:
        last_dt = datetime.fromisoformat(str(last_sent))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return elapsed >= _HIGH_COOLDOWN_HOURS * 3600
    except (ValueError, TypeError):
        return True


async def _update_rate_limit(org_id: str):
    """Persist the last email sent timestamp to MongoDB."""
    from database import module_configs_collection
    now_iso = datetime.now(timezone.utc).isoformat()
    await module_configs_collection.update_one(
        {"organization_id": org_id, "module_key": "cashflow_monitor"},
        {"$set": {"settings._last_high_email_at": now_iso}},
        upsert=True,
    )


async def notify_high_severity_batch(
    alerts: List[Alert], org_id: str, locale: str = "it"
) -> int:
    """Send email notification for HIGH severity alerts.

    Checks:
    1. User preference email_high_alerts (must be True)
    2. Persistent rate limit (max 1/day, survives restart)
    3. Plan gating (email_alerts feature)
    4. Structural alert suppression (no email for re-fired concentration alerts)

    Returns 1 if email sent, 0 otherwise.
    """
    high_alerts = [a for a in alerts if a.severity.value == "high"]
    if not high_alerts:
        return 0

    try:
        from repositories import organization_repository, alert_repository
        from database import users_collection
        from services.module_access import can_use_module

        # ── Check user preference ────────────────────────────────────────
        settings = await _get_alert_settings(org_id)
        if settings.get("email_high_alerts") is False:
            logger.info(
                "alert_notification: email_high_alerts DISABLED by user for org=%s",
                org_id,
            )
            return 0

        # ── Persistent rate limit (survives restart) ─────────────────────
        if not await _check_rate_limit(org_id, settings):
            logger.debug(
                "alert_notification: skipping HIGH email for org=%s (cooldown %dh active)",
                org_id, _HIGH_COOLDOWN_HOURS,
            )
            return 0

        # ── Plan gating ──────────────────────────────────────────────────
        org = await organization_repository.find_by_id(org_id)
        if not org:
            return 0
        if not await can_use_module(org, "cashflow_monitor", "email_alerts"):
            logger.debug(
                "alert_notification: email_alerts not available for org=%s (plan gating)",
                org_id,
            )
            return 0

        # ── Structural alert suppression ─────────────────────────────────
        # Don't email for re-fired concentration alerts (supplier_, product_, etc.)
        from database import alerts_collection
        filtered_alerts = []
        for a in high_alerts:
            ek = getattr(a, "entity_key", None) or ""
            is_structural = any(ek.startswith(p) for p in _STRUCTURAL_PATTERNS)
            if is_structural:
                # Check if this entity_key was already alerted before (resolved in last 60 days)
                existing = await alerts_collection.find_one({
                    "organization_id": org_id,
                    "entity_key": ek,
                    "status": "resolved",
                    "resolved_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()},
                })
                if existing:
                    logger.info(
                        "alert_notification: suppressing re-fire email for structural alert %s org=%s",
                        ek, org_id,
                    )
                    continue
            filtered_alerts.append(a)

        if not filtered_alerts:
            return 0

        # ── Find admin users ─────────────────────────────────────────────
        admin_cursor = users_collection.find(
            {"organization_id": org_id, "role": {"$in": ["admin", "system_admin"]}},
            {"_id": 0, "email": 1, "name": 1},
        )
        admins = await admin_cursor.to_list(10)
        if not admins:
            return 0

        # ── Send per-recipient (Onda 7) ──────────────────────────────────
        # Each admin gets the email in their own locale (User.locale >
        # storefront default > "it"). The body is rendered once per
        # distinct locale and cached so multi-admin orgs don't pay 1
        # render per recipient when admins share a language.
        from services.email_service import send_email, _t, APP_URL
        from services.order_email_service import _resolve_user_email_locale

        n = len(filtered_alerts)
        remaining_count = n - 5
        alerts_view_url = f"{APP_URL}/cashflow?tab=alerts"
        body_cache: dict = {}
        subject_cache: dict = {}

        def _render_for_locale(loc: str) -> str:
            cat_tpl = _t("cashflow_alert_category_label", loc, category="__CAT__")
            heading_key = "cashflow_alert_high_heading_one" if n == 1 else "cashflow_alert_high_heading_other"
            heading = _t(heading_key, loc, count=n)

            alert_rows = ""
            for a in filtered_alerts[:5]:
                title = a.title
                summary = a.summary[:200]
                suggestion = a.suggested_action or ""
                cat = getattr(a, "alert_category", "") or ""
                cat_label = cat_tpl.replace("__CAT__", cat) if cat else ""
                cat_html = (
                    f'<span style="color:#9CA3AF; font-size:11px;"> ({cat_label})</span>'
                    if cat_label else ""
                )
                alert_rows += f"""
                <tr>
                    <td style="padding:12px; border-bottom:1px solid #eee;">
                        <strong style="color:#DC2626;">&#x1F534; {title}</strong>
                        {cat_html}
                        <br>
                        <span style="color:#666; font-size:14px;">{summary}</span>
                        {"<br><em style='color:#2563EB; font-size:13px;'>&#x2192; " + suggestion + "</em>" if suggestion else ""}
                    </td>
                </tr>"""

            if remaining_count > 0:
                rem_key = (
                    "cashflow_alert_high_remaining_one"
                    if remaining_count == 1
                    else "cashflow_alert_high_remaining_other"
                )
                remaining_note = (
                    f"<p style='color:#9CA3AF; font-size:13px;'>{_t(rem_key, loc, count=remaining_count)}</p>"
                )
            else:
                remaining_note = ""

            view_cta = _t("cashflow_alert_view_all_cta", loc)

            return f"""
            <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
                <h2 style="color:#DC2626;">&#x26A0;&#xFE0F; {heading}</h2>
                <table style="width:100%; border-collapse:collapse;">
                    {alert_rows}
                </table>
                {remaining_note}
                <p style="margin-top:20px;">
                    <a href="{alerts_view_url}"
                       style="background:#2563EB; color:#fff; padding:10px 20px;
                              text-decoration:none; border-radius:6px; display:inline-block;">
                        {view_cta}
                    </a>
                </p>
                {_render_alert_footer(loc)}
            </div>
            """

        sent = 0
        for admin in admins:
            recipient_locale = await _resolve_user_email_locale(org_id, admin.get("email"))
            if recipient_locale not in body_cache:
                body_cache[recipient_locale] = _render_for_locale(recipient_locale)
                subjects_for_loc = _SUBJECTS.get(recipient_locale, _SUBJECTS["it"])
                subject_cache[recipient_locale] = subjects_for_loc["high_alert"].format(count=n)
            ok = send_email(admin["email"], subject_cache[recipient_locale], body_cache[recipient_locale])
            if ok:
                sent += 1
            else:
                logger.warning(
                    "alert_notification: HIGH alert email FAILED for %s org=%s",
                    admin["email"], org_id,
                )

        # Persist rate limit to MongoDB (survives restart)
        await _update_rate_limit(org_id)

        logger.info(
            "alert_notification: sent HIGH alert email to %d/%d admins for org=%s (%d alerts)",
            sent, len(admins), org_id, len(filtered_alerts),
        )
        return 1 if sent > 0 else 0

    except Exception as exc:
        logger.error(
            "alert_notification: failed to send HIGH email for org=%s: %s",
            org_id, exc,
        )
        return 0


async def send_weekly_alert_digest(org_id: str, locale: str = "it") -> int:
    """Send weekly digest of all open alerts.

    Checks email_weekly_digest preference before sending.
    Returns 1 if email sent, 0 otherwise.
    """
    try:
        from repositories import alert_repository, organization_repository
        from database import users_collection
        from services.module_access import can_use_module

        # ── Check user preference ────────────────────────────────────────
        settings = await _get_alert_settings(org_id)
        if settings.get("email_weekly_digest") is False:
            logger.info(
                "alert_notification: email_weekly_digest DISABLED by user for org=%s",
                org_id,
            )
            return 0

        open_alerts = await alert_repository.find_open_alerts_for_digest(org_id)
        if not open_alerts:
            return 0

        org = await organization_repository.find_by_id(org_id)
        if not org:
            return 0

        if not await can_use_module(org, "cashflow_monitor", "email_digest"):
            logger.debug(
                "alert_notification: email_digest not available for org=%s (plan gating)",
                org_id,
            )
            return 0

        admin_cursor = users_collection.find(
            {"organization_id": org_id, "role": {"$in": ["admin", "system_admin"]}},
            {"_id": 0, "email": 1},
        )
        admins = await admin_cursor.to_list(10)
        if not admins:
            return 0

        # Count by severity
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for a in open_alerts:
            sev = a.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Onda 7 — render the digest body in the recipient's locale.
        # Same caching strategy as notify_high_severity_batch: render
        # once per distinct locale.
        from services.email_service import send_email, _t, APP_URL
        from services.order_email_service import _resolve_user_email_locale

        alerts_view_url = f"{APP_URL}/cashflow?tab=alerts"

        def _severity_label(sev: str, count: int, loc: str) -> str:
            suffix = "_one" if count == 1 else "_other"
            return _t(f"cashflow_severity_{sev}{suffix}", loc, count=count)

        def _render_for_locale(loc: str) -> str:
            cat_tpl = _t("cashflow_alert_category_label", loc, category="__CAT__")
            alert_rows = ""
            for a in open_alerts[:10]:
                sev = a.get("severity", "low")
                color = {"high": "#DC2626", "medium": "#F59E0B", "low": "#3B82F6"}.get(sev, "#666")
                title = a.get("title", "")
                cat = a.get("alert_category", "")
                cat_label = cat_tpl.replace("__CAT__", cat) if cat else ""
                cat_html = (
                    f'<span style="color:#9CA3AF; font-size:11px;"> ({cat_label})</span>'
                    if cat_label else ""
                )
                alert_rows += f"""
                <tr>
                    <td style="padding:8px; border-bottom:1px solid #f0f0f0;">
                        <span style="color:{color};">&#x25CF;</span> {title}
                        {cat_html}
                    </td>
                </tr>"""

            heading = _t("cashflow_digest_heading", loc)
            view_cta = _t("cashflow_digest_view_cta", loc)
            sev_high = _severity_label("high", severity_counts["high"], loc)
            sev_med = _severity_label("medium", severity_counts["medium"], loc)
            sev_low = _severity_label("low", severity_counts["low"], loc)

            return f"""
            <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
                <h2>&#x1F4CA; {heading}</h2>
                <p>
                    <strong style="color:#DC2626;">{sev_high}</strong> &middot;
                    <strong style="color:#F59E0B;">{sev_med}</strong> &middot;
                    <strong style="color:#3B82F6;">{sev_low}</strong>
                </p>
                <table style="width:100%; border-collapse:collapse;">
                    {alert_rows}
                </table>
                <p style="margin-top:20px;">
                    <a href="{alerts_view_url}"
                       style="background:#2563EB; color:#fff; padding:10px 20px;
                              text-decoration:none; border-radius:6px; display:inline-block;">
                        {view_cta}
                    </a>
                </p>
                {_render_alert_footer(loc)}
            </div>
            """

        body_cache: dict = {}
        subject_cache: dict = {}

        sent = 0
        for admin in admins:
            recipient_locale = await _resolve_user_email_locale(org_id, admin.get("email"))
            if recipient_locale not in body_cache:
                body_cache[recipient_locale] = _render_for_locale(recipient_locale)
                subjects_for_loc = _SUBJECTS.get(recipient_locale, _SUBJECTS["it"])
                subject_cache[recipient_locale] = subjects_for_loc["weekly_digest"]
            ok = send_email(admin["email"], subject_cache[recipient_locale], body_cache[recipient_locale])
            if ok:
                sent += 1
            else:
                logger.warning(
                    "alert_notification: weekly digest email FAILED for %s org=%s",
                    admin["email"], org_id,
                )

        logger.info(
            "alert_notification: sent weekly digest to %d/%d admins for org=%s (%d open alerts)",
            sent, len(admins), org_id, len(open_alerts),
        )
        return 1 if sent > 0 else 0

    except Exception as exc:
        logger.error(
            "alert_notification: weekly digest failed for org=%s: %s", org_id, exc,
        )
        return 0


# ── Digest Report Email ──────────────────────────────────────────────────────

_DIGEST_SUBJECTS = {
    "it": {"weekly": "Il tuo report settimanale AFianco", "monthly": "Il tuo report mensile AFianco"},
    "en": {"weekly": "Your weekly AFianco report", "monthly": "Your monthly AFianco report"},
    "de": {"weekly": "Ihr woechentlicher AFianco-Bericht", "monthly": "Ihr monatlicher AFianco-Bericht"},
    "fr": {"weekly": "Votre rapport hebdomadaire AFianco", "monthly": "Votre rapport mensuel AFianco"},
}


async def send_digest_report_email(
    org_id: str,
    pdf_bytes: bytes,
    sections: dict,
    digest_type: str = "weekly",
    period_label: str = "",
    locale: str = "it",
) -> int:
    """Send digest report email with PDF attachment.

    Checks email_weekly_digest preference before sending.
    Returns 1 if sent, 0 otherwise.
    """
    try:
        from repositories import organization_repository
        from database import users_collection
        from services.module_access import can_use_module

        # Check user preference
        settings = await _get_alert_settings(org_id)
        if settings.get("email_weekly_digest") is False:
            logger.info(
                "alert_notification: email_weekly_digest DISABLED for org=%s (skipping digest report)",
                org_id,
            )
            return 0

        org = await organization_repository.find_by_id(org_id)
        if not org:
            return 0

        if not await can_use_module(org, "cashflow_monitor", "email_digest"):
            return 0

        # CH compliance v1: render the headline numbers in the org's
        # currency. Previously the template hardcoded "EUR" which left
        # CHF merchants reading their digest in the wrong unit.
        from services.currency_service import get_currency_for_org
        org_currency = get_currency_for_org(org)

        admin_cursor = users_collection.find(
            {"organization_id": org_id, "role": {"$in": ["admin", "system_admin"]}},
            {"_id": 0, "email": 1},
        )
        admins = await admin_cursor.to_list(10)
        if not admins:
            return 0

        snapshot = sections.get("snapshot", {})
        health = snapshot.get("health_score", 0)
        sales = snapshot.get("total_sales", 0)
        outflows = snapshot.get("total_outflows", 0)
        margin = snapshot.get("operating_margin_pct", 0)
        alerts_count = sections.get("alerts_count", 0)

        health_color = "#16A34A" if health >= 70 else "#F59E0B" if health >= 40 else "#DC2626"

        body_html = f"""
        <div style="font-family:Arial,sans-serif; max-width:500px; margin:0 auto; padding:20px;">
            <h2 style="color:#2563EB; margin-bottom:5px;">AFianco Report</h2>
            <p style="color:#6B7280; font-size:13px;">{period_label}</p>
            <div style="text-align:center; margin:20px 0;">
                <div style="display:inline-block; width:80px; height:80px; border-radius:50%;
                            background:{health_color}22; line-height:80px; text-align:center;">
                    <span style="font-size:28px; font-weight:bold; color:{health_color};">{health}</span>
                </div>
                <p style="color:#6B7280; font-size:12px; margin-top:4px;">Health Score /100</p>
            </div>
            <table style="width:100%; border-collapse:collapse; margin:15px 0;">
                <tr>
                    <td style="padding:10px; text-align:center; border:1px solid #E5E7EB;">
                        <div style="font-size:16px; font-weight:bold;">{org_currency} {sales:,.0f}</div>
                        <div style="font-size:11px; color:#6B7280;">Ricavi</div>
                    </td>
                    <td style="padding:10px; text-align:center; border:1px solid #E5E7EB;">
                        <div style="font-size:16px; font-weight:bold;">{org_currency} {outflows:,.0f}</div>
                        <div style="font-size:11px; color:#6B7280;">Uscite</div>
                    </td>
                    <td style="padding:10px; text-align:center; border:1px solid #E5E7EB;">
                        <div style="font-size:16px; font-weight:bold;">{margin:.1f}%</div>
                        <div style="font-size:11px; color:#6B7280;">Margine</div>
                    </td>
                    <td style="padding:10px; text-align:center; border:1px solid #E5E7EB;">
                        <div style="font-size:16px; font-weight:bold;">{alerts_count}</div>
                        <div style="font-size:11px; color:#6B7280;">Alert</div>
                    </td>
                </tr>
            </table>
            <p style="font-size:13px; color:#6B7280; text-align:center;">
                Il report completo e' in allegato (PDF).
            </p>
            <div style="text-align:center; margin:20px 0;">
                <a href="https://afianco.app/modules/cashflow?tab=digest"
                   style="background:#2563EB; color:#fff; padding:10px 24px;
                          text-decoration:none; border-radius:6px; font-size:14px; display:inline-block;">
                    Apri Dashboard
                </a>
            </div>
            {_render_alert_footer(locale)}
        </div>
        """

        subjects = _DIGEST_SUBJECTS.get(locale, _DIGEST_SUBJECTS["it"])
        subject = subjects.get(digest_type, subjects["weekly"])
        filename = f"afianco_report_{digest_type}.pdf"

        from services.email_service import send_email_with_attachment

        sent = 0
        for admin in admins:
            ok = send_email_with_attachment(
                admin["email"], subject, body_html,
                pdf_bytes, filename,
            )
            if ok:
                sent += 1
            else:
                logger.warning(
                    "alert_notification: digest email FAILED for %s org=%s",
                    admin["email"], org_id,
                )

        logger.info(
            "alert_notification: sent digest report to %d/%d admins for org=%s",
            sent, len(admins), org_id,
        )
        return 1 if sent > 0 else 0

    except Exception as exc:
        logger.error(
            "alert_notification: digest report email failed for org=%s: %s",
            org_id, exc,
        )
        return 0
