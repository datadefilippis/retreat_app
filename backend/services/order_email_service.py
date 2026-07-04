"""
Order Email Service — centralized transactional email triggers for orders.

Single place for all order-related email logic. Called from order_service.py
and public.py at state-change points. Never from routers directly.

Design:
  - Every function is best-effort (try/except, log, never raise)
  - Uses store_settings for sender name and reply-to
  - Uses customer locale when available, falls back to "it"
  - All emails use email_service._wrap_template for consistent branding
"""

import logging
from typing import Optional

from services.email_service import (
    send_email, _wrap_template, _t, _link_block,
    SMTP_FROM_NAME, APP_URL,
)
from services.url_builder import build_public_url, build_app_url

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _load_store_context(
    org_id: str,
    *,
    store_id: Optional[str] = None,
    store_slug: Optional[str] = None,
) -> dict:
    """Load store branding for email context. Returns safe defaults.

    Multi-store-aware (Onda 6):
      - When `store_id` (or `store_slug`) is provided AND it resolves
        to a real `stores` document, the per-store fields override the
        legacy org-level `organizations.store_settings` block. This
        prevents email branding from leaking between sibling stores
        of the same org (e.g. an order placed on a German store no
        longer ships from "Studio Italia" with the Italian reply-to).
      - When neither is provided OR the lookup misses, falls back to
        the existing org-level shape — preserves behaviour for orders
        that pre-date `store_id` backfill, single-store orgs, and
        any caller that hasn't yet been updated.

    The returned dict shape is unchanged so all existing callers keep
    working without code changes:
        { store_name, notification_email, sender_name, reply_to }
    """
    from database import organizations_collection, stores_collection

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "name": 1, "store_settings": 1},
    )
    if not org:
        return {"store_name": "Store", "notification_email": None,
                "sender_name": SMTP_FROM_NAME, "reply_to": None}

    org_name = org.get("name", "Store")
    legacy = org.get("store_settings") or {}

    # Per-store lookup. Only succeeds when caller passed an identifier
    # AND the store actually exists in this org (defensive against
    # cross-org id reuse).
    store_doc: Optional[dict] = None
    if store_id:
        store_doc = await stores_collection.find_one(
            {"id": store_id, "organization_id": org_id},
            {"_id": 0, "name": 1, "sender_display_name": 1,
             "reply_to_email": 1, "notification_email": 1},
        )
    elif store_slug:
        store_doc = await stores_collection.find_one(
            {"slug": store_slug, "organization_id": org_id},
            {"_id": 0, "name": 1, "sender_display_name": 1,
             "reply_to_email": 1, "notification_email": 1},
        )

    # Per-store wins when present, with org-level legacy as the
    # fallback for each individual field (so a partially-configured
    # store still inherits sender/reply-to from the org).
    if store_doc:
        store_name = (
            store_doc.get("name")
            or legacy.get("display_name")
            or org_name
        )
        sender_name = (
            store_doc.get("sender_display_name")
            or legacy.get("sender_display_name")
            or SMTP_FROM_NAME
        )
        reply_to = (
            store_doc.get("reply_to_email")
            or legacy.get("reply_to_email")
        )
        notification_email = (
            store_doc.get("notification_email")
            or legacy.get("notification_email")
        )
        return {
            "store_name": store_name,
            "notification_email": notification_email,
            "sender_name": sender_name,
            "reply_to": reply_to,
        }

    # Legacy path — no store-id given (or store not found): same shape
    # as before this commit, byte-for-byte equivalent.
    return {
        "store_name": legacy.get("display_name") or org_name,
        "notification_email": legacy.get("notification_email"),
        "sender_name": legacy.get("sender_display_name") or SMTP_FROM_NAME,
        "reply_to": legacy.get("reply_to_email"),
    }


_VALID_EMAIL_LOCALES = {"it", "en", "de", "fr"}


def _normalize_locale(value) -> Optional[str]:
    """Coerce any locale-ish input to one of the 4 supported codes, or None.

    Accepts both bare codes (`it`) and region tags (`it-IT`, `en_US`),
    case-insensitive. Mirrors the frontend resolver's normalisation
    (`useStorefrontLocale.js`) so the same string values map identically
    on both sides.
    """
    if not value:
        return None
    code = str(value).strip().lower().replace("_", "-").split("-")[0]
    return code if code in _VALID_EMAIL_LOCALES else None


async def _resolve_store_locale(org_id: str, store_id: Optional[str] = None) -> Optional[str]:
    """Resolve a default email locale from the storefront's `storefront_languages`.

    Returns None when no store-aware locale can be derived; the caller
    decides the next fallback in its own chain. Never raises — a DB blip
    during email rendering should silently fall through, never block the
    transactional flow.

    Resolution order:
      1. The order's own `store_id` (when set after backfill / new orders).
      2. First published+public store of the org (legacy single-store orgs).
    """
    if not org_id:
        return None
    try:
        from database import stores_collection
        if store_id:
            store = await stores_collection.find_one(
                {"id": store_id, "organization_id": org_id},
                {"_id": 0, "storefront_languages": 1},
            )
            if store:
                langs = store.get("storefront_languages") or []
                if langs:
                    code = _normalize_locale(langs[0])
                    if code:
                        return code
        store = await stores_collection.find_one(
            {"organization_id": org_id, "is_published": True,
             "is_active": True, "visibility": "public"},
            {"_id": 0, "storefront_languages": 1},
        )
        if store:
            langs = store.get("storefront_languages") or []
            if langs:
                code = _normalize_locale(langs[0])
                if code:
                    return code
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("order_email: _resolve_store_locale failed org=%s: %s", org_id, exc)
    return None


async def _get_customer_email_and_locale(order: dict) -> tuple:
    """Resolve customer email + locale from customer record or account.

    Returns (email, locale). Email may be None if not found.

    Locale resolution chain (matches frontend resolver in spirit):
      1. customer_account.locale — when the buyer is logged in. Their
         explicit preference wins over store defaults.
      2. store.storefront_languages[0] — the storefront the order came
         from. Lets a guest checkout on a DE store receive a DE email
         without forcing signup.
      3. First published+public store storefront_languages[0] — legacy
         single-store orgs whose orders pre-date the per-store backfill.
      4. "it" — final hardcoded fallback. Never raises.

    Validates each candidate against the 4 supported locales — invalid
    values (legacy region-tagged strings, typos) silently fall through
    instead of producing broken email rendering.
    """
    from database import customers_collection, customer_accounts_collection

    # ── Email lookup ─────────────────────────────────────────────────
    customer_id = order.get("customer_id")
    email = None
    if customer_id:
        customer = await customers_collection.find_one(
            {"id": customer_id},
            {"_id": 0, "email": 1},
        )
        email = (customer or {}).get("email")

    # ── Locale resolution chain ──────────────────────────────────────
    locale: Optional[str] = None

    # Priority 1: linked customer account
    account_id = order.get("customer_account_id")
    if account_id:
        try:
            account = await customer_accounts_collection.find_one(
                {"id": account_id},
                {"_id": 0, "locale": 1},
            )
            if account:
                locale = _normalize_locale(account.get("locale"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("order_email: customer_account locale lookup failed: %s", exc)

    # Priority 2 & 3: store-aware fallback
    if locale is None:
        locale = await _resolve_store_locale(
            order.get("organization_id"),
            order.get("store_id"),
        )

    # Priority 4: final hardcoded fallback
    return email, (locale or "it")


async def _resolve_user_email_locale(
    org_id: str,
    user_email: Optional[str] = None,
    *,
    store_id: Optional[str] = None,
) -> str:
    """Resolve a locale for any operational email targeted at a merchant
    user (admin / notification recipient). Used by the cashflow HIGH-alert
    pipeline (Onda 7) and the store-status transition emails (Onda 7).

    Chain:
      1. user.locale of the recipient — when the email is configured to
         a real `users` row of this org. Their explicit UI preference
         wins over store defaults.
      2. store.storefront_languages[0] — falls back to the storefront's
         primary language so a German operator who set their store to
         DE without yet picking a UI locale still reads alerts in DE.
      3. "it" — final hardcoded fallback.

    Always returns a valid locale string; never raises. The order-email
    sibling `_resolve_merchant_locale` keeps existing behaviour for the
    order pipeline; this helper exposes the same chain for non-order
    operational emails without coupling them to an `order` dict.
    """
    from database import users_collection

    if user_email:
        try:
            user = await users_collection.find_one(
                {"organization_id": org_id, "email": user_email,
                 "is_active": True},
                {"_id": 0, "locale": 1},
            )
            if user:
                code = _normalize_locale(user.get("locale"))
                if code:
                    return code
        except Exception as exc:  # noqa: BLE001
            logger.debug("order_email: _resolve_user_email_locale lookup failed: %s", exc)

    code = await _resolve_store_locale(org_id, store_id)
    return code or "it"


async def _resolve_merchant_locale(
    order: dict,
    org_id: str,
    notification_user_email: Optional[str] = None,
) -> str:
    """Resolve the locale for the merchant-facing notification email.

    Chain:
      1. user.locale of the notification recipient — picks up the admin
         who configured `notification_email` (or any matching admin user).
      2. store.storefront_languages[0] — operator who set their store
         in DE/FR/EN reads the operational email in that language too.
      3. "it" — final fallback.

    Always returns a valid locale string; never raises.
    """
    from database import users_collection

    # Priority 1
    if notification_user_email:
        try:
            user = await users_collection.find_one(
                {"organization_id": org_id, "email": notification_user_email,
                 "is_active": True},
                {"_id": 0, "locale": 1},
            )
            if user:
                code = _normalize_locale(user.get("locale"))
                if code:
                    return code
        except Exception as exc:  # noqa: BLE001
            logger.debug("order_email: merchant user locale lookup failed: %s", exc)

    # Priority 2
    locale = await _resolve_store_locale(org_id, order.get("store_id"))
    return locale or "it"


def _fmt_total(total: float, currency: str = "EUR", locale: str = "it") -> str:
    """Format an order total for email display, currency- and locale-aware.

    Delegates to :func:`core.currency_format.format_amount` so the layout
    matches the PDF receipt and the in-app frontend exactly. The ``locale``
    argument is forwarded so European-style numerics (``1.234,56``) are
    used for it/de/fr and US-style (``1,234.56``) for en. CHF is always
    rendered with apostrophe thousands and dot decimals regardless of
    locale.

    Backwards-compatible: existing callers that pass only
    ``(total, currency)`` keep the previous behaviour (Italian locale).
    """
    from core.currency_format import format_amount

    return format_amount(total, currency, locale=locale)


def _fmt_fulfillment_mode(mode: str, locale: str) -> str:
    """Translate fulfillment mode for email display."""
    key = f"fulfillment_mode_{mode}"
    return _t(key, locale)


async def _build_customer_account_url(order: dict, org_id: str, path: str = "/account") -> str:
    """Build the URL the "Vedi dettaglio ordine" / "Vai al tuo account"
    button should target, with the right `?store=<slug>` query string.

    Why a helper exists
    -------------------
    Three different customer-facing email functions emit a CTA into the
    customer area: order received, order confirmed, fulfillment update.
    Each used to hardcode `f"{APP_URL}/account"` (or
    `/account/orders/<id>`) inline. The result was that customers
    clicking the button landed on /account/login WITHOUT a storefront
    slug, the customer-auth resolver couldn't identify the org, and
    login surfaced "Account non esiste per questo store" — even when
    the account did exist. Same shape as the verify-email bug fixed
    in commit 2cd3000. Each one was patched separately, which left
    the third site (`notify_customer_order_received`) silently broken
    for several deploys. This helper closes that gap.

    Resolution order for the slug:
      1. customer_account.signup_slug — the storefront the buyer
         originally registered from. Wins as long as it still resolves
         to this org (defensive against renames / deactivations).
      2. The first published+public store for the org (modern
         multi-store layout).
      3. The legacy `organizations.public_slug`.
      4. None — caller ships the bare URL; login still has localStorage
         as a fallback for returning customers, and the existing
         "select your store" path for everyone else.

    Path is relative to APP_URL — pass the customer-area route the CTA
    points at, e.g. "/account", "/account/orders/<id>".
    """
    from services.customer_auth_service import resolve_slug_for_org
    from database import customer_accounts_collection

    signup_slug = None
    account_id = order.get("customer_account_id")
    if account_id:
        try:
            account = await customer_accounts_collection.find_one(
                {"id": account_id},
                {"_id": 0, "signup_slug": 1},
            )
            signup_slug = (account or {}).get("signup_slug")
        except Exception:
            # DB blip during email rendering should never raise — we
            # degrade to the slugless URL instead. The customer can
            # still log in via localStorage / store selector.
            signup_slug = None

    try:
        store_slug = await resolve_slug_for_org(org_id, preferred=signup_slug)
    except Exception:
        store_slug = None

    base = f"{APP_URL}{path}"
    return f"{base}?store={store_slug}" if store_slug else base


# ── Bulk cart helpers (used across the 3 notify_* functions below) ───────────
#
# These helpers surface the order composition in the email body in a way
# that works for bulk multi-type carts (e.g. 1 event + 1 physical + 1
# digital). They are pure: input = `order` dict + locale, output = HTML
# string (or "" when there is nothing meaningful to render). Never raise.

# Map order.items[].item_type → i18n key prefix for the typecount line.
_TYPECOUNT_KEY_PREFIX = {
    "event_ticket": "order_typecount_event",
    "service": "order_typecount_service",
    "rental": "order_typecount_rental",
    "physical": "order_typecount_physical",
    "digital": "order_typecount_digital",
    # Release 4 (Courses)
    "course": "order_typecount_course",
}

# Stable presentation order for the typecount line. Mirrors the order of
# the specialized sections later in the confirmation email (tickets →
# bookings → reservations → physical → downloads).
_TYPECOUNT_ORDER = ["event_ticket", "service", "rental", "physical", "digital", "course"]


def _fmt_qty(value) -> str:
    """Render a quantity without trailing ".0" when it is a round integer."""
    try:
        q = float(value or 0)
    except (TypeError, ValueError):
        q = 0
    return str(int(q)) if q == int(q) else f"{q:g}"


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# ── Locale-aware date formatters (Onda 5) ──────────────────────────────────
#
# The embedded sections inside the order-confirmed email render dates
# in two flavors:
#   - short "12 mag 2026" style (booking + reservation rows) — uses the
#     12 month_short_N keys from EMAIL_TRANSLATIONS so DE customers see
#     "12 Mai 2026" and FR ones "12 mai 2026" instead of the IT mesi[].
#   - numeric "12/05/2026" / "5/12/2026" style (download expiry hint) —
#     locale-aware ordering: IT/FR use D/M/Y, EN uses M/D/Y, DE uses
#     D.M.Y. Kept inline because it's the only locale-dependent numeric
#     format we need; pulling in `babel` for one helper is overkill.
#
# Both helpers degrade gracefully on malformed input (empty string in,
# empty string out) — the email never crashes for a missing date.


def _fmt_short_date_localized(ymd: str, locale: str) -> str:
    """Return e.g. '12 mag 2026' (it), '12 May 2026' (en),
    '12 Mai 2026' (de), '12 mai 2026' (fr).

    Accepts an ISO YYYY-MM-DD string. On parse error returns the input
    unchanged — the email body never crashes for a malformed date.
    """
    if not ymd:
        return ""
    try:
        from datetime import date as _date
        d = _date.fromisoformat(ymd)
        month_label = _t(f"month_short_{d.month}", locale)
        return f"{d.day} {month_label} {d.year}"
    except Exception:
        return ymd


def _fmt_numeric_date_localized(iso_or_ymd: str, locale: str) -> str:
    """Return a short numeric date in the conventional locale order.

      it -> 12/05/2026
      fr -> 12/05/2026
      en -> 5/12/2026     (US M/D/Y)
      de -> 12.05.2026

    Accepts both YYYY-MM-DD and full ISO timestamps with timezone. On
    parse error returns the input unchanged.
    """
    if not iso_or_ymd:
        return ""
    try:
        from datetime import datetime as _dt
        # Tolerate both bare YYYY-MM-DD and full ISO; replace trailing Z.
        s = iso_or_ymd.replace("Z", "+00:00") if "T" in iso_or_ymd else iso_or_ymd
        d = _dt.fromisoformat(s) if "T" in s else _dt.strptime(s, "%Y-%m-%d")
        if locale == "en":
            return f"{d.month}/{d.day}/{d.year}"
        if locale == "de":
            return f"{d.day:02d}.{d.month:02d}.{d.year}"
        # it / fr (and any unknown -> default IT shape)
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except Exception:
        return iso_or_ymd


def _render_order_summary_section(order: dict, locale: str) -> str:
    """Render the "Riepilogo ordine" table for the confirmation email.

    Lists every order line (name, qty, line_total) plus a subtotal (when
    it differs from total), shipping (when > 0), and the final total.
    Returns "" when the order has no items — a defensive guard; a
    confirmed order always has lines.

    Note: line_total already includes per-line extras and discount (see
    OrderItem.line_total in models/order.py), so no extras/discount
    subrows are needed to keep the math consistent with the order total.
    """
    items = order.get("items") or []
    if not items:
        return ""
    # CH compliance v1: derive currency from the order snapshot (with the
    # legacy EUR fallback baked into get_currency_for_order). Locale is
    # already resolved by the caller and threads through to format_amount.
    from services.currency_service import get_currency_for_order
    currency = get_currency_for_order(order)

    rows_html = []
    for it in items:
        name = _html_escape(it.get("product_name") or "—")
        qty_label = _fmt_qty(it.get("quantity"))
        line_total = _safe_float(it.get("line_total"))
        rows_html.append(
            '<tr>'
            f'<td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;color:#111;">{name}</td>'
            f'<td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;text-align:center;color:#374151;">{qty_label}</td>'
            f'<td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;text-align:right;color:#111;white-space:nowrap;">{_fmt_total(line_total, currency, locale)}</td>'
            '</tr>'
        )

    subtotal = _safe_float(order.get("subtotal"))
    total = _safe_float(order.get("total"))
    ff = order.get("fulfillment") or {}
    shipping_cost = _safe_float(ff.get("shipping_cost"))

    totals_rows = []
    # Subtotal row only when it differs meaningfully from total (shipping
    # added on top, order-level discount, etc.). Keeps the table clean
    # for simple orders where subtotal == total.
    if abs(subtotal - total) > 0.005:
        totals_rows.append(
            '<tr>'
            f'<td colspan="2" style="padding:6px;text-align:right;color:#6b7280;">'
            f'{_t("order_summary_subtotal", locale, total=_fmt_total(subtotal, currency, locale))}</td>'
            '<td></td></tr>'
        )
    if shipping_cost > 0:
        shipping_str = _fmt_total(shipping_cost, currency, locale)
        totals_rows.append(
            '<tr>'
            f'<td colspan="2" style="padding:6px;text-align:right;color:#6b7280;">'
            f'{_t("order_summary_shipping", locale, cost=shipping_str)}</td>'
            '<td></td></tr>'
        )
    # Final total row — always shown.
    totals_rows.append(
        '<tr>'
        f'<td colspan="2" style="padding:10px 6px 4px;text-align:right;font-weight:700;color:#111;font-size:15px;">'
        f'{_t("order_summary_total", locale, total=_fmt_total(total, currency, locale))}</td>'
        '<td></td></tr>'
    )

    heading = _t("order_summary_heading", locale)
    col_item = _t("order_summary_col_item", locale)
    col_qty = _t("order_summary_col_qty", locale)
    col_price = _t("order_summary_col_price", locale)

    return (
        '<div style="margin:16px 0;padding:12px 14px;background:#f9fafb;'
        'border-left:3px solid #374151;border-radius:6px;">'
        f'<p style="margin:0 0 8px;font-weight:600;color:#111;">{heading}</p>'
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        '<thead><tr>'
        f'<th style="padding:6px;text-align:left;color:#6b7280;font-weight:600;border-bottom:2px solid #e5e7eb;">{col_item}</th>'
        f'<th style="padding:6px;text-align:center;color:#6b7280;font-weight:600;border-bottom:2px solid #e5e7eb;">{col_qty}</th>'
        f'<th style="padding:6px;text-align:right;color:#6b7280;font-weight:600;border-bottom:2px solid #e5e7eb;">{col_price}</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        f'<tfoot>{"".join(totals_rows)}</tfoot>'
        '</table>'
        '</div>'
    )


def _render_items_list_compact(order: dict, locale: str) -> str:
    """Render a compact product list for the admin notification email.

    One line per item ("2× Vino Barolo — €24.00"), no totals (the admin
    template already shows them above). Returns "" for empty orders.
    Reuses the "Riepilogo ordine" heading i18n key so the two emails
    read consistently.
    """
    items = order.get("items") or []
    if not items:
        return ""
    from services.currency_service import get_currency_for_order
    currency = get_currency_for_order(order)

    lines = []
    for it in items:
        name = _html_escape(it.get("product_name") or "—")
        qty_label = _fmt_qty(it.get("quantity"))
        line_total = _safe_float(it.get("line_total"))
        lines.append(
            '<p style="margin:4px 0;color:#333;font-size:14px;">'
            f'<strong>{qty_label}×</strong> {name} — '
            f'<span style="color:#111;font-weight:600;">{_fmt_total(line_total, currency, locale)}</span>'
            '</p>'
        )

    heading = _t("order_summary_heading", locale)
    return (
        '<div style="margin:12px 0;padding:10px 12px;background:#f9fafb;'
        'border-left:3px solid #374151;border-radius:6px;">'
        f'<p style="margin:0 0 6px;font-weight:600;color:#111;">{heading}</p>'
        f'{"".join(lines)}'
        '</div>'
    )


def _render_items_typecount_line(order: dict, locale: str) -> str:
    """Aggregate items by `item_type` and return a localized summary string.

    Examples:
      "1 evento"                       (mono-type)
      "2 prodotti, 1 download"         (mixed)
      "Articoli: 4"                    (fallback when item_type missing)

    For event_ticket, `quantity` is the seats count per line so the
    aggregate correctly sums tiers of the same event. Integer-looking
    quantities are rendered without decimals. The fallback is used when
    the order has items but none matches a known item_type — keeps the
    string truthful rather than hiding the item count.
    """
    items = order.get("items") or []
    if not items:
        return _t("order_typecount_fallback", locale, count=0)

    counts = {}
    for it in items:
        itype = it.get("item_type") or "physical"
        q = _safe_float(it.get("quantity"))
        if q <= 0:
            continue
        counts[itype] = counts.get(itype, 0) + q

    if not counts:
        return _t("order_typecount_fallback", locale, count=len(items))

    parts = []
    for itype in _TYPECOUNT_ORDER:
        n = counts.get(itype, 0)
        if n <= 0:
            continue
        n_int = int(n) if n == int(n) else n
        prefix = _TYPECOUNT_KEY_PREFIX.get(itype)
        if not prefix:
            continue
        suffix = "_one" if n_int == 1 else "_other"
        parts.append(_t(f"{prefix}{suffix}", locale, count=n_int))

    if not parts:
        # Only unknown item_types were present — be truthful.
        total_qty = int(sum(counts.values()))
        return _t("order_typecount_fallback", locale, count=total_qty or len(items))

    return ", ".join(parts)


# ── Customer: Order/Request Received ─────────────────────────────────────────

async def notify_customer_order_received(order: dict, org_id: str) -> None:
    """Send "your request has been received" email to the customer.

    Called from public.py after storefront order creation.
    Truthful: says "registered/received", never "confirmed".
    """
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        email, locale = await _get_customer_email_and_locale(order)
        if not email:
            return

        store_name = ctx["store_name"]
        order_ref = order.get("order_number") or order.get("id", "")[:12]
        from services.currency_service import get_currency_for_order
        total = _fmt_total(order.get("total", 0), get_currency_for_order(order), locale)

        # Type-aware breakdown (e.g. "1 evento, 2 prodotti, 1 download") —
        # distinguishes bulk multi-type carts instead of the generic
        # "Articoli: N". Falls back to the item count when item_type is
        # missing on the lines.
        typecount_line = _render_items_typecount_line(order, locale)

        account_url = await _build_customer_account_url(order, org_id, "/account")

        html = _wrap_template(f"""
            <p>{_t("greeting", locale)},</p>
            <p>{_t("order_received_body", locale)}</p>
            <p>{_t("order_received_ref", locale, order_ref=order_ref)}</p>
            <p>{typecount_line}<br>
               {_t("order_received_total", locale, total=total)}</p>
            <p style="text-align: center;">
                <a href="{account_url}" class="btn">{_t("order_received_cta", locale)}</a>
            </p>
        """, locale, reply_to=ctx["reply_to"], store_name=store_name)

        subject = _t("order_received_subject", locale, store_name=store_name)
        send_email(email, subject, html, reply_to=ctx["reply_to"], sender_name=ctx["sender_name"])
        logger.info("order_email: customer_received sent to=%s order=%s", email, order_ref)

    except Exception as e:
        logger.warning("order_email: customer_received failed: %s", e)


# ── Merchant: New Order/Request Received ─────────────────────────────────────

async def notify_merchant_new_order(
    order: dict, org_id: str,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> None:
    """Send "new order/request arrived" email to the merchant.

    Uses notification_email from store_settings if configured,
    otherwise falls back to org admin users.

    `customer_name` / `customer_email` are kept as optional parameters
    for backward compatibility with the storefront caller, which has
    the values straight from the form. When called from the Stripe
    webhook handler the form is gone, so we resolve them from the
    denormalized `order.customer_name` and a lookup on the `customers`
    collection.
    """
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))

        # Determine recipients
        recipients = []
        if ctx["notification_email"]:
            recipients = [ctx["notification_email"]]
        else:
            from database import users_collection
            cursor = users_collection.find(
                {"organization_id": org_id, "role": {"$in": ["admin"]}, "is_active": True},
                {"_id": 0, "email": 1},
            )
            admins = await cursor.to_list(10)
            recipients = [a["email"] for a in admins if a.get("email")]

        if not recipients:
            return

        # Resolve customer identity if the caller didn't pass it explicitly.
        # The webhook reconciliation path goes through this branch — it
        # has only the order doc, not the original form payload.
        if customer_name is None:
            customer_name = order.get("customer_name") or ""
        if customer_email is None:
            cust_id = order.get("customer_id")
            if cust_id:
                from database import customers_collection
                cust = await customers_collection.find_one(
                    {"id": cust_id, "organization_id": org_id},
                    {"_id": 0, "email": 1},
                )
                customer_email = (cust or {}).get("email", "") or ""
            else:
                customer_email = ""

        order_ref = order.get("order_number") or order.get("id", "")[:12]
        items_count = len(order.get("items", []))

        ff = order.get("fulfillment") or {}
        ff_mode = ff.get("mode", "not_required")

        # Resolve merchant locale: notification user → store storefront →
        # "it". Lets a German operator who set their storefront to DE
        # receive the operational email in DE without further config.
        # The first recipient drives the choice — when notification_email
        # is set we have a single recipient anyway; when it isn't, we
        # use the first admin found, which is a stable enough proxy.
        locale = await _resolve_merchant_locale(
            order, org_id,
            notification_user_email=recipients[0] if recipients else None,
        )

        # CH compliance v1: format total in the order's currency with the
        # merchant's locale (note: this email is for the merchant, not the
        # customer — locale follows the recipient).
        from services.currency_service import get_currency_for_order
        total = _fmt_total(order.get("total", 0), get_currency_for_order(order), locale)
        orders_url = f"{APP_URL}/orders"

        # Replace the generic "Articoli: N" line with a type-aware summary
        # (e.g. "2 prodotti, 1 download") and render a compact list of the
        # order lines below, so the admin sees what was ordered without
        # opening the panel.
        typecount_line = _render_items_typecount_line(order, locale)
        items_list_html = _render_items_list_compact(order, locale)

        lines = [
            f'<p>{_t("order_merchant_body", locale)}</p>',
            f'<p>{_t("order_merchant_customer", locale, customer_name=customer_name, customer_email=customer_email)}</p>',
            f'<p>{typecount_line}<br>',
            f'   {_t("order_merchant_total", locale, total=total)}</p>',
            items_list_html,
        ]

        if ff_mode != "not_required":
            mode_label = _fmt_fulfillment_mode(ff_mode, locale)
            lines.append(f'<p>{_t("order_merchant_fulfillment", locale, mode=mode_label)}</p>')

        if order.get("notes"):
            lines.append(f'<p>{_t("order_merchant_notes", locale, notes=_html_escape(order["notes"]))}</p>')

        lines.append(f"""
            <p style="text-align: center;">
                <a href="{orders_url}" class="btn">{_t("order_merchant_cta", locale)}</a>
            </p>
            <p style="color: #aaa; font-size: 12px;">
                {_t("order_merchant_draft_hint", locale)}
            </p>
        """)

        html = _wrap_template("\n".join(lines), locale)
        subject = _t("order_merchant_subject", locale, customer_name=customer_name)

        for recipient in recipients:
            ok = send_email(recipient, subject, html, sender_name=ctx["sender_name"])
            if ok:
                logger.info("order_email: merchant_new sent to=%s order=%s", recipient, order_ref)

    except Exception as e:
        logger.warning("order_email: merchant_new failed: %s", e)


# ── Customer: Order Confirmed ─────────────────────────────────────────────────

async def _render_tickets_section(order: dict, org_id: str, locale: str = "it") -> str:
    """Render the E4 "I tuoi biglietti" block for the confirmation email.

    Returns "" when the order has no event_ticket items / no issued
    tickets — the caller concatenates the result into the email HTML
    unconditionally.

    Groups tickets by occurrence so a buyer with 2 VIP + 1 Standard in
    the same cart sees one block per event with all codes listed and a
    QR per seat. Each card carries:
      - event title (from product.name)
      - date/time (from occurrence.start_at)
      - venue (structured if present, else legacy `location`)
      - per-ticket code + tier label + seat index + inline QR image

    `locale` (Onda 5) drives every translatable string; the caller
    resolves it via `_get_customer_email_and_locale` and passes the
    same value to all 4 embedded sections so the email reads
    consistently in one language.
    """
    try:
        issued = order.get("_issued_tickets")
        if not issued:
            from services.ticket_service import list_tickets_for_order
            issued = await list_tickets_for_order(order.get("id", ""), org_id)
        if not issued:
            return ""

        from database import (
            event_occurrences_collection,
            products_collection,
        )

        # Group by occurrence — one section per event.
        by_occ: dict = {}
        for t in issued:
            by_occ.setdefault(t.get("occurrence_id"), []).append(t)

        blocks: list[str] = []
        for occ_id, tickets in by_occ.items():
            if not occ_id:
                continue
            occ = await event_occurrences_collection.find_one(
                {"id": occ_id, "organization_id": org_id},
                {"_id": 0},
            ) or {}
            prod_id = tickets[0].get("product_id")
            prod = await products_collection.find_one(
                {"id": prod_id, "organization_id": org_id},
                {"_id": 0, "name": 1},
            ) or {}

            # Pretty date/time
            start_at = occ.get("start_at") or ""
            dt_line = start_at.replace("T", " · ")[:16] if start_at else ""

            # Venue line: prefer structured venue_name/address/city, fall
            # back to legacy `location`, else blank.
            venue_parts = []
            if occ.get("venue_name"):
                venue_parts.append(occ["venue_name"])
            addr_city = ", ".join(p for p in [occ.get("address"), occ.get("city")] if p)
            if addr_city:
                venue_parts.append(addr_city)
            if not venue_parts and occ.get("location"):
                venue_parts.append(occ["location"])
            venue_line = " · ".join(venue_parts)

            # F1 Onda 8 — Link-based ticket list (scales to 100+ tickets).
            # Instead of inline QR per ticket (~50KB each → 5MB emails that
            # get rejected), each row is a link to the /t/{access_token}
            # landing page which renders the QR on demand.
            ticket_rows = []
            for t in tickets:
                code = t.get("code", "")
                holder = t.get("holder_name") or ""
                tier = t.get("tier_label")
                seat_idx = int(t.get("seat_index") or 1)
                seat_count = int(t.get("seat_count") or 1)
                token = t.get("access_token")
                # Customer-facing landing — see services/url_builder.py.
                ticket_url = build_public_url(f"/t/{token}") if token else ""
                open_cta_label = _t("order_section_tickets_open_cta", locale)
                open_btn = (
                    f'<a href="{ticket_url}" style="display:inline-block;padding:8px 14px;background:#111827;color:#ffffff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">{open_cta_label}</a>'
                    if ticket_url else ""
                )
                meta_parts = []
                if holder:
                    meta_parts.append(_html_escape(holder))
                if tier:
                    meta_parts.append(_html_escape(tier))
                if seat_count > 1:
                    meta_parts.append(_t("order_section_tickets_seat_hint", locale,
                                         seat_index=seat_idx, seat_count=seat_count))
                meta_line = " · ".join(meta_parts)

                ticket_rows.append(f"""
                <tr>
                  <td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <div style="font-family:monospace;font-size:14px;color:#374151;letter-spacing:0.5px;">{_html_escape(code)}</div>
                          {f'<div style="color:#6b7280;font-size:12px;margin-top:3px;">{meta_line}</div>' if meta_line else ""}
                        </td>
                        <td style="vertical-align:middle;text-align:right;">
                          {open_btn}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height:8px;line-height:8px;">&nbsp;</td></tr>
                """)

            event_name = prod.get("name") or _t("order_section_tickets_event_fallback", locale)
            heading_label = _t("order_section_tickets_heading", locale)
            privacy_hint = _t("order_section_tickets_privacy_hint", locale)
            block = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
                  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{heading_label}</div>
                  <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(event_name)}</h3>
                  <div style="color:#374151;font-size:14px;">{_html_escape(dt_line)}</div>
                  {f'<div style="color:#6b7280;font-size:13px;margin-top:2px;">{_html_escape(venue_line)}</div>' if venue_line else ""}
                  <div style="height:12px;"></div>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    {"".join(ticket_rows)}
                  </table>
                  <div style="color:#6b7280;font-size:12px;margin-top:8px;">
                    {privacy_hint}
                  </div>
                </td>
              </tr>
            </table>
            """
            blocks.append(block)

        return "".join(blocks)
    except Exception as exc:
        logger.warning("order_email: tickets render failed: %s", exc)
        return ""


def _html_escape(s) -> str:
    """Minimal HTML-escape for email string fields."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


async def _render_bookings_section(order: dict, org_id: str, locale: str = "it") -> str:
    """Render the "Le tue prenotazioni" block for service consulenze.

    Onda 14 — mirrors _render_tickets_section. Returns "" when the order
    has no service bookings. Each booking row links to /b/{access_token}
    which renders full details + an "Aggiungi al calendario" .ics download.

    Groups bookings by product so a customer with 3 sessions of the same
    consulenza sees one block with 3 rows.

    `locale` (Onda 5) drives copy + month-name short formatting.
    """
    try:
        issued = order.get("_issued_bookings")
        if not issued:
            from database import issued_bookings_collection
            issued = await issued_bookings_collection.find(
                {"organization_id": org_id, "order_id": order.get("id", "")},
                {"_id": 0},
            ).to_list(None)
        if not issued:
            return ""

        from database import products_collection

        # Group by product
        by_product: dict = {}
        for b in issued:
            by_product.setdefault(b.get("product_id"), []).append(b)

        blocks: list[str] = []
        product_fallback = _t("order_section_bookings_product_fallback", locale)
        open_cta_label = _t("order_section_bookings_open_cta", locale)
        for prod_id, bookings in by_product.items():
            prod = await products_collection.find_one(
                {"id": prod_id, "organization_id": org_id},
                {"_id": 0, "name": 1},
            ) or {}
            product_name = prod.get("name") or product_fallback

            booking_rows = []
            for b in bookings:
                code = b.get("code", "")
                option = b.get("service_option_label") or ""
                bdate = b.get("booking_date") or ""
                bstart = b.get("booking_start_time") or ""
                bend = b.get("booking_end_time") or ""
                # Pretty date "12 mag 2026" — locale-aware month names
                pretty = _fmt_short_date_localized(bdate, locale)
                time_line = f"{pretty} · {bstart}" + (f" → {bend}" if bend else "")

                token = b.get("access_token")
                booking_url = build_public_url(f"/b/{token}") if token else ""
                open_btn = (
                    f'<a href="{booking_url}" style="display:inline-block;padding:8px 14px;background:#111827;color:#ffffff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">{open_cta_label}</a>'
                    if booking_url else ""
                )
                meta_parts = []
                if option:
                    meta_parts.append(_html_escape(option))
                if b.get("location"):
                    meta_parts.append("📍 " + _html_escape(b["location"]))
                meta_line = " · ".join(meta_parts)

                booking_rows.append(f"""
                <tr>
                  <td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <div style="font-size:14px;color:#111827;font-weight:600;">{_html_escape(time_line)}</div>
                          <div style="font-family:monospace;font-size:12px;color:#6b7280;margin-top:3px;letter-spacing:0.5px;">{_html_escape(code)}</div>
                          {f'<div style="color:#6b7280;font-size:12px;margin-top:3px;">{meta_line}</div>' if meta_line else ""}
                        </td>
                        <td style="vertical-align:middle;text-align:right;">
                          {open_btn}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height:8px;line-height:8px;">&nbsp;</td></tr>
                """)

            heading_label = _t("order_section_bookings_heading", locale)
            help_hint = _t("order_section_bookings_help_hint", locale)
            block = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
                  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{heading_label}</div>
                  <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(product_name)}</h3>
                  <div style="height:12px;"></div>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    {"".join(booking_rows)}
                  </table>
                  <div style="color:#6b7280;font-size:12px;margin-top:8px;">
                    {help_hint}
                  </div>
                </td>
              </tr>
            </table>
            """
            blocks.append(block)

        return "".join(blocks)
    except Exception as exc:
        logger.warning("order_email: bookings render failed: %s", exc)
        return ""


async def _render_reservations_section(order: dict, org_id: str, locale: str = "it") -> str:
    """Render the "La tua prenotazione" block for rental + slot reservations.

    Onda 16 — mirrors _render_bookings_section. Returns "" when the order
    has no IssuedReservation rows. Each row links to /rsv/{access_token}.
    Extras applied on each line are summarized inline so the customer sees
    exactly what has been charged.

    `locale` (Onda 5) drives copy + month-name short formatting.
    """
    try:
        issued = order.get("_issued_reservations")
        if not issued:
            from database import issued_reservations_collection
            issued = await issued_reservations_collection.find(
                {"organization_id": org_id, "order_id": order.get("id", "")},
                {"_id": 0},
            ).to_list(None)
        if not issued:
            return ""

        from database import products_collection

        # Group by product so multiple reservations of the same product
        # appear under one product header (rare for rentals but symmetric
        # with the bookings block for consistency).
        by_product: dict = {}
        for r in issued:
            by_product.setdefault(r.get("product_id"), []).append(r)

        def _pretty_date(ymd: str) -> str:
            return _fmt_short_date_localized(ymd or "", locale)

        blocks: list[str] = []
        product_fallback = _t("order_section_reservations_product_fallback", locale)
        open_cta_label = _t("order_section_reservations_open_cta", locale)
        for prod_id, reservations in by_product.items():
            prod = await products_collection.find_one(
                {"id": prod_id, "organization_id": org_id},
                {"_id": 0, "name": 1},
            ) or {}
            product_name = prod.get("name") or reservations[0].get("product_name") or product_fallback

            reservation_rows = []
            for r in reservations:
                flavor = r.get("reservation_flavor")
                if flavor == "range":
                    dfrom = _pretty_date(r.get("date_from") or "")
                    dto = _pretty_date(r.get("date_to") or "")
                    when = f"{dfrom} → {dto}" if dto and dto != dfrom else dfrom
                else:
                    sdate = _pretty_date(r.get("slot_date") or "")
                    sstart = r.get("slot_start_time") or ""
                    send = r.get("slot_end_time") or ""
                    when = f"{sdate} · {sstart}" + (f" → {send}" if send else "")

                code = r.get("code", "")
                token = r.get("access_token")
                rsv_url = build_public_url(f"/rsv/{token}") if token else ""
                open_btn = (
                    f'<a href="{rsv_url}" style="display:inline-block;padding:8px 14px;background:#111827;color:#ffffff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">{open_cta_label}</a>'
                    if rsv_url else ""
                )

                extras_lines = ""
                for ex in (r.get("extras_snapshot") or []):
                    label = _html_escape(ex.get("label", ""))
                    amt = ex.get("line_total", 0)
                    extras_lines += (
                        f'<div style="color:#6b7280;font-size:12px;margin-top:2px;">+ {label} · €{amt:.2f}</div>'
                    )

                meta_parts = []
                if r.get("location"):
                    meta_parts.append("📍 " + _html_escape(r["location"]))
                meta_line = " · ".join(meta_parts)

                reservation_rows.append(f"""
                <tr>
                  <td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <div style="font-size:14px;color:#111827;font-weight:600;">{_html_escape(when)}</div>
                          <div style="font-family:monospace;font-size:12px;color:#6b7280;margin-top:3px;letter-spacing:0.5px;">{_html_escape(code)}</div>
                          {f'<div style="color:#6b7280;font-size:12px;margin-top:3px;">{meta_line}</div>' if meta_line else ""}
                          {extras_lines}
                        </td>
                        <td style="vertical-align:middle;text-align:right;">
                          {open_btn}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height:8px;line-height:8px;">&nbsp;</td></tr>
                """)

            heading_label = _t("order_section_reservations_heading", locale)
            help_hint = _t("order_section_reservations_help_hint", locale)
            block = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
                  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{heading_label}</div>
                  <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(product_name)}</h3>
                  <div style="height:12px;"></div>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    {"".join(reservation_rows)}
                  </table>
                  <div style="color:#6b7280;font-size:12px;margin-top:8px;">
                    {help_hint}
                  </div>
                </td>
              </tr>
            </table>
            """
            blocks.append(block)

        return "".join(blocks)
    except Exception as exc:
        logger.warning("order_email: reservations render failed: %s", exc)
        return ""


async def _render_downloads_section(order: dict, org_id: str, locale: str = "it") -> str:
    """Release 3 (Digital) — "Il tuo download" block for digital deliveries.

    Mirrors _render_reservations_section. Returns "" when the order has no
    IssuedDownload rows. Each row links to /d/{access_token} where the
    landing shows a "Scarica" button + remaining-downloads / expiry info.

    `locale` (Onda 5) drives copy + locale-aware numeric date formatting.
    """
    try:
        issued = order.get("_issued_downloads")
        if not issued:
            from database import issued_downloads_collection
            issued = await issued_downloads_collection.find(
                {"organization_id": org_id, "order_id": order.get("id", "")},
                {"_id": 0},
            ).to_list(None)
        if not issued:
            return ""

        from database import products_collection

        def _fmt_bytes(n):
            try:
                n = int(n or 0)
            except Exception:
                return ""
            if n <= 0:
                return ""
            kb = n / 1024
            if kb < 1024:
                return f"{kb:.0f} KB"
            mb = kb / 1024
            if mb < 1024:
                return f"{mb:.1f} MB"
            return f"{mb / 1024:.2f} GB"

        def _pretty_date(iso):
            return _fmt_numeric_date_localized(iso or "", locale)

        # Group by product so repeated digital lines (rare — one per line
        # by convention) show under one product header.
        by_product: dict = {}
        for d in issued:
            by_product.setdefault(d.get("product_id"), []).append(d)

        blocks: list[str] = []
        product_fallback = _t("order_section_downloads_product_fallback", locale)
        file_fallback = _t("order_section_downloads_file_fallback", locale)
        open_cta_label = _t("order_section_downloads_open_cta", locale)
        for prod_id, downloads in by_product.items():
            prod = await products_collection.find_one(
                {"id": prod_id, "organization_id": org_id},
                {"_id": 0, "name": 1},
            ) or {}
            product_name = prod.get("name") or downloads[0].get("product_name") or product_fallback

            download_rows = []
            for d in downloads:
                code = d.get("code", "")
                token = d.get("access_token")
                dl_url = build_public_url(f"/d/{token}") if token else ""
                open_btn = (
                    f'<a href="{dl_url}" style="display:inline-block;padding:8px 14px;background:#111827;color:#ffffff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">{open_cta_label}</a>'
                    if dl_url else ""
                )

                filename = _html_escape(d.get("download_filename") or file_fallback)
                size_txt = _fmt_bytes(d.get("download_size_bytes"))
                meta_parts = [filename]
                if size_txt:
                    meta_parts.append(size_txt)

                policy_bits = []
                max_dl = d.get("max_downloads")
                if max_dl:
                    policy_bits.append(_t("order_section_downloads_max_hint", locale, max=max_dl))
                exp = d.get("access_token_expires_at")
                if exp:
                    policy_bits.append(_t("order_section_downloads_expiry_hint", locale, date=_pretty_date(exp)))
                policy_line = " · ".join(policy_bits)

                download_rows.append(f"""
                <tr>
                  <td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <div style="font-size:14px;color:#111827;font-weight:600;">📁 {" · ".join(meta_parts)}</div>
                          <div style="font-family:monospace;font-size:12px;color:#6b7280;margin-top:3px;letter-spacing:0.5px;">{_html_escape(code)}</div>
                          {f'<div style="color:#6b7280;font-size:12px;margin-top:3px;">{_html_escape(policy_line)}</div>' if policy_line else ""}
                        </td>
                        <td style="vertical-align:middle;text-align:right;">
                          {open_btn}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height:8px;line-height:8px;">&nbsp;</td></tr>
                """)

            heading_label = _t("order_section_downloads_heading", locale)
            privacy_hint = _t("order_section_downloads_privacy_hint", locale)
            block = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
                  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{heading_label}</div>
                  <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(product_name)}</h3>
                  <div style="height:12px;"></div>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    {"".join(download_rows)}
                  </table>
                  <div style="color:#6b7280;font-size:12px;margin-top:8px;">
                    {privacy_hint}
                  </div>
                </td>
              </tr>
            </table>
            """
            blocks.append(block)

        return "".join(blocks)
    except Exception as exc:
        logger.warning("order_email: downloads render failed: %s", exc)
        return ""


async def _render_courses_section(order: dict, org_id: str, locale: str) -> str:
    """Release 4 (Courses) Step 8 — "I tuoi corsi" block for enrollments.

    Mirror of _render_downloads_section. Renders one card per
    IssuedCourseAccess with:
      - cover image + course title + instructor (when available)
      - access policy line ("a vita" / "valido fino al <date>")
      - CTA "Vai al corso" → /account/courses/:enrollment_id

    Returns "" when the order has no course enrollments. Stashed rows
    from confirm_order are preferred; otherwise we fetch by order_id.
    Anti-leak: never embeds bunny_video_guid.
    """
    try:
        issued = order.get("_issued_course_accesses")
        if not issued:
            from database import issued_course_accesses_collection
            issued = await issued_course_accesses_collection.find(
                {"organization_id": org_id, "order_id": order.get("id", "")},
                {"_id": 0},
            ).to_list(None)
        if not issued:
            return ""

        # Drop revoked enrollments from the confirmation email — on the
        # (rare) case where an admin revokes between confirm and email send.
        issued = [e for e in issued if not e.get("revoked_at")]
        if not issued:
            return ""

        from database import courses_collection

        def _pretty_date(val):
            """Accepts str (ISO) or datetime; returns a locale-aware
            short numeric date string (Onda 5) — matches the locale of
            the surrounding email instead of always using IT formatting.
            """
            if not val:
                return ""
            try:
                if hasattr(val, "isoformat"):
                    val = val.isoformat()
                return _fmt_numeric_date_localized(str(val), locale)
            except Exception:
                return ""

        heading = _t("order_courses_heading", locale)
        cta_label = _t("order_courses_cta", locale)
        lifetime_label = _t("order_courses_access_lifetime", locale)

        blocks: list[str] = []
        for enr in issued:
            course_id = enr.get("course_id")
            course_doc = None
            if course_id:
                course_doc = await courses_collection.find_one(
                    {"id": course_id, "organization_id": org_id},
                    {"_id": 0, "title": 1, "cover_image_url": 1, "instructor_name": 1,
                     "modules": 1},
                )

            title = _html_escape(
                (course_doc or {}).get("title")
                or enr.get("course_title_snapshot")
                or "Corso"
            )
            cover = (course_doc or {}).get("cover_image_url") or ""
            instructor = (course_doc or {}).get("instructor_name") or ""

            # Lessons count + duration (best-effort from live course doc).
            lessons_count = 0
            total_duration = 0
            for m in ((course_doc or {}).get("modules") or []):
                for l in (m.get("lessons") or []):
                    lessons_count += 1
                    try:
                        total_duration += int(l.get("duration_seconds") or 0)
                    except (TypeError, ValueError):
                        pass
            meta_bits = []
            if lessons_count:
                meta_bits.append(
                    f"{lessons_count} lezion{'e' if lessons_count == 1 else 'i'}"
                )
            if total_duration:
                mins = total_duration // 60
                if mins >= 60:
                    h = mins // 60
                    m = mins % 60
                    meta_bits.append(f"{h}h" if m == 0 else f"{h}h {m}m")
                else:
                    meta_bits.append(f"{mins} min")
            meta_line = " · ".join(meta_bits)

            # Access line
            expires_at = enr.get("expires_at")
            if expires_at:
                access_line = _t(
                    "order_courses_access_expiry", locale,
                    date=_pretty_date(expires_at),
                )
            else:
                access_line = lifetime_label

            # Customer-facing player URL — JWT-protected; the access_token
            # is an internal fingerprint, NOT the URL credential.
            #
            # Goes through _build_customer_account_url so the link
            # carries `?store=<slug>`. The page is gated by
            # CustomerProtectedRoute, which on a fresh device falls
            # back to the URL's query string for the storefront slug —
            # without that, the post-login bounce ends up at
            # /account/login with no store and rejects the buyer with
            # "Account non esiste per questo store" (same shape as the
            # /account/orders bug fixed earlier in this commit chain).
            # Sharing the helper with the other customer-area CTAs
            # keeps the slug-resolution logic in one place.
            enrollment_id = enr.get("id") or ""
            player_url = await _build_customer_account_url(
                order, org_id, f"/account/courses/{enrollment_id}",
            )

            cover_img = (
                f'<img src="{_html_escape(cover)}" alt="" '
                f'style="display:block;width:100%;max-width:480px;height:auto;border-radius:8px;margin-bottom:12px;">'
                if cover else ""
            )

            instructor_line = (
                f'<div style="color:#6b7280;font-size:13px;margin-top:2px;">'
                f'a cura di {_html_escape(instructor)}</div>'
                if instructor else ""
            )

            meta_block = (
                f'<div style="color:#6b7280;font-size:12px;margin-top:6px;">{_html_escape(meta_line)}</div>'
                if meta_line else ""
            )

            block = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
                  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{heading}</div>
                  <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">🎓 {title}</h3>
                  {instructor_line}
                  {meta_block}
                  <div style="height:12px;"></div>
                  {cover_img}
                  <div style="color:#374151;font-size:13px;margin-bottom:12px;">🔑 {_html_escape(access_line)}</div>
                  <a href="{player_url}" style="display:inline-block;padding:10px 18px;background:#111827;color:#ffffff;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">{cta_label} →</a>
                  <div style="color:#6b7280;font-size:12px;margin-top:10px;">
                    💡 Accedi alla tua area riservata per seguire il corso e tenere traccia dei progressi.
                  </div>
                </td>
              </tr>
            </table>
            """
            blocks.append(block)

        return "".join(blocks)
    except Exception as exc:
        logger.warning("order_email: courses render failed: %s", exc)
        return ""


def _render_fulfillment_section(order: dict, locale: str, store_name: str) -> str:
    """Release 1 (Physical) — inline fulfillment summary for the confirmation
    email. Renders a small box with shipping address (mode=shipping) or
    pickup location (mode=local_pickup). Returns "" when fulfillment is
    not_required or manual_arrangement (covered by other sections).
    """
    ff = order.get("fulfillment") or {}
    mode = ff.get("mode")
    if mode not in ("shipping", "local_pickup"):
        return ""
    notes = (ff.get("fulfillment_notes") or "").strip()
    if mode == "shipping":
        addr = (ff.get("shipping_address") or "").strip()
        shipping_label = (ff.get("shipping_option_label") or "").strip()
        shipping_cost = ff.get("shipping_cost")
        try:
            shipping_cost_f = float(shipping_cost or 0)
        except (TypeError, ValueError):
            shipping_cost_f = 0.0
        if not addr and not notes and not shipping_label:
            return ""
        label = _t("fulfillment_mode_shipping", locale)
        header = _t("fulfillment_destination_label", locale)
        body = ""
        if addr:
            body = (
                f'<p style="margin: 4px 0; color: #333;">'
                f'📍 <strong>{header}:</strong><br>'
                f'<span style="color:#555;">{addr}</span></p>'
            )
        # Shipping option line — rendered whenever the order has a
        # resolved option at checkout time, so the customer sees the
        # method they paid for alongside the address.
        if shipping_label:
            cost_str = (
                f'<strong>€{shipping_cost_f:.2f}</strong>'
                if shipping_cost_f > 0
                else f'<strong>{_t("fulfillment_shipping_free", locale)}</strong>'
            )
            body += (
                f'<p style="margin: 4px 0; color: #333;">'
                f'🚚 {shipping_label} — {cost_str}</p>'
            )
        if notes:
            body += f'<p style="margin: 4px 0; color:#666; font-style: italic;">{notes}</p>'
        return (
            f'<div style="margin: 16px 0; padding: 12px 14px; background: #f9fafb; '
            f'border-left: 3px solid #374151; border-radius: 6px;">'
            f'<p style="margin: 0 0 6px; font-weight: 600; color: #111;">{label}</p>'
            f'{body}'
            f'</div>'
        )
    # local_pickup
    label = _t("fulfillment_mode_local_pickup", locale)
    header = _t("fulfillment_pickup_label", locale)
    body = (
        f'<p style="margin: 4px 0; color: #333;">'
        f'🏪 <strong>{header}:</strong> {store_name}</p>'
    )
    if notes:
        body += f'<p style="margin: 4px 0; color:#666; font-style: italic;">{notes}</p>'
    return (
        f'<div style="margin: 16px 0; padding: 12px 14px; background: #f9fafb; '
        f'border-left: 3px solid #374151; border-radius: 6px;">'
        f'<p style="margin: 0 0 6px; font-weight: 600; color: #111;">{label}</p>'
        f'{body}'
        f'</div>'
    )


# ── Fase 2 S2 (retreat) — piano pagamenti nell'email di conferma ────────────

async def _render_payment_schedule_section(order: dict, org_id: str, locale: str) -> str:
    """Blocco "Il tuo piano di pagamenti" per ordini con schedule multi-riga.

    Vuoto per: ordini senza schedule (non-ritiro / legacy) e piani a riga
    unica gia' saldata (nessun piano da raccontare). Mostra righe pagate
    (con spunta) e future (con scadenza) + nota promemoria. Nessun link di
    pagamento qui: i link /pay/{token} viaggiano nei promemoria (S3),
    generati freschi a ridosso della scadenza.
    """
    try:
        from services.payment_schedule_service import get_schedule_for_order
        schedule = await get_schedule_for_order(order.get("id"), org_id)
        if not schedule:
            return ""
        rows = schedule.get("rows") or []
        if len(rows) < 2:
            return ""  # pagamento unico: niente sezione
        currency = schedule.get("currency") or "EUR"

        items_html = []
        for row in rows:
            status = row.get("status")
            if status in ("cancelled",):
                continue
            amount = _fmt_total(row.get("amount_minor", 0) / 100.0, currency, locale)
            if status in ("paid", "paid_manual"):
                items_html.append(
                    "<li>" + _t("payment_plan_paid_row", locale,
                                label=row.get("label", ""), amount=amount) + "</li>"
                )
            else:
                due = _fmt_short_date_localized((row.get("due_at") or "")[:10], locale)
                items_html.append(
                    "<li>" + _t("payment_plan_pending_row", locale,
                                label=row.get("label", ""), amount=amount,
                                due_date=due) + "</li>"
                )
        if not items_html:
            return ""
        return (
            '<h3 style="margin:24px 0 8px;">' + _t("payment_plan_heading", locale) + "</h3>"
            + '<ul style="margin:0 0 8px; padding-left:20px;">' + "".join(items_html) + "</ul>"
            + '<p style="color:#666; font-size:13px;">'
            + _t("payment_plan_reminder_note", locale) + "</p>"
        )
    except Exception as exc:
        logger.warning("order_email: payment schedule section failed: %s", exc)
        return ""


async def notify_customer_order_confirmed(order: dict, org_id: str) -> None:
    """Send "your order has been confirmed" email to the customer.

    Truthful: says "confirmed and being processed", never "shipped" or "delivered".

    E4: when the order contains event_ticket lines, an "I tuoi biglietti"
    section with per-seat codes + QR codes is appended to the email body.
    Onda 14: when the order contains service lines with booked slots, a
    "Le tue prenotazioni" section with per-booking links is appended too.
    """
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        email, locale = await _get_customer_email_and_locale(order)
        if not email:
            return

        store_name = ctx["store_name"]
        order_ref = order.get("order_number") or order.get("id", "")[:12]
        order_id = order.get("id", "")
        # Customer area deep-link with the right ?store=<slug> query
        # string — see _build_customer_account_url for the rationale.
        detail_url = await _build_customer_account_url(
            order, org_id, f"/account/orders/{order_id}",
        )

        # Bulk-cart summary table: renders all lines + totals in one block
        # above the type-specialized sections below. Ensures physical items
        # in mixed orders aren't invisible and the total is always in sight.
        summary_html = _render_order_summary_section(order, locale)
        # E4: tickets block (empty string when no event_ticket items).
        # All 4 embedded renderers receive `locale` (Onda 5) so headings,
        # CTAs, month names and date formats match the rest of the email
        # instead of staying in the IT default they used to ship.
        tickets_html = await _render_tickets_section(order, org_id, locale)
        # Onda 14: bookings block (empty string when no service lines)
        bookings_html = await _render_bookings_section(order, org_id, locale)
        # Onda 16: reservations block (rental + slot)
        reservations_html = await _render_reservations_section(order, org_id, locale)
        # Release 3 (Digital): download links block
        downloads_html = await _render_downloads_section(order, org_id, locale)
        # Release 4 (Courses): enrollment cards block
        courses_html = await _render_courses_section(order, org_id, locale)
        # Release 1 (Physical): inline shipping / pickup summary
        fulfillment_html = _render_fulfillment_section(order, locale, store_name)
        # Fase 2 S2 (retreat): piano pagamenti (caparra pagata + scadenze)
        payments_html = await _render_payment_schedule_section(order, org_id, locale)

        html = _wrap_template(f"""
            <p>{_t("greeting", locale)},</p>
            <p>{_t("order_confirmed_body", locale)}</p>
            <p>{_t("order_confirmed_ref", locale, order_ref=order_ref)}</p>
            {summary_html}
            {payments_html}
            {fulfillment_html}
            {tickets_html}
            {bookings_html}
            {reservations_html}
            {downloads_html}
            {courses_html}
            <p style="text-align: center;">
                <a href="{detail_url}" class="btn">{_t("order_confirmed_cta", locale)}</a>
            </p>
        """, locale, reply_to=ctx["reply_to"], store_name=store_name)

        subject = _t("order_confirmed_subject", locale, store_name=store_name)
        send_email(email, subject, html, reply_to=ctx["reply_to"], sender_name=ctx["sender_name"])
        logger.info("order_email: confirmed sent to=%s order=%s", email, order_ref)

    except Exception as e:
        logger.warning("order_email: confirmed failed: %s", e)


# ── Customer: Order Cancelled ────────────────────────────────────────────────

async def notify_customer_order_cancelled(order: dict, org_id: str) -> None:
    """Send "your order has been cancelled" email to the customer.

    Truthful: says "cancelled", never "refunded" (refund is a separate concern).
    """
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        email, locale = await _get_customer_email_and_locale(order)
        if not email:
            return

        store_name = ctx["store_name"]
        order_ref = order.get("order_number") or order.get("id", "")[:12]

        html = _wrap_template(f"""
            <p>{_t("greeting", locale)},</p>
            <p>{_t("order_cancelled_body", locale)}</p>
            <p>{_t("order_cancelled_ref", locale, order_ref=order_ref)}</p>
            <p>{_t("order_cancelled_contact", locale)}</p>
        """, locale, reply_to=ctx["reply_to"], store_name=store_name)

        subject = _t("order_cancelled_subject", locale, store_name=store_name)
        send_email(email, subject, html, reply_to=ctx["reply_to"], sender_name=ctx["sender_name"])
        logger.info("order_email: cancelled sent to=%s order=%s", email, order_ref)

    except Exception as e:
        logger.warning("order_email: cancelled failed: %s", e)


# ── Customer: Fulfillment Status Update ──────────────────────────────────────

async def notify_customer_fulfillment_update(
    order: dict, org_id: str, new_status: str,
) -> None:
    """Send fulfillment status update email to the customer.

    Called from order_service.update_fulfillment_status() after successful transition.
    Only sends for statuses that are meaningful to the customer.
    """
    # Only email-worthy statuses
    EMAIL_WORTHY = {"shipped", "ready_for_pickup", "delivered", "picked_up", "fulfilled"}
    if new_status not in EMAIL_WORTHY:
        return

    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        email, locale = await _get_customer_email_and_locale(order)
        if not email:
            return

        store_name = ctx["store_name"]
        order_ref = order.get("order_number") or order.get("id", "")[:12]

        # Map status to translation key prefix
        KEY_MAP = {
            "shipped": "fulfillment_shipped",
            "ready_for_pickup": "fulfillment_ready",
            "delivered": "fulfillment_delivered",
            "picked_up": "fulfillment_picked_up",
            "fulfilled": "fulfillment_fulfilled",
        }
        prefix = KEY_MAP.get(new_status, "fulfillment_fulfilled")

        subject = _t(f"{prefix}_subject", locale, store_name=store_name)
        body_text = _t(f"{prefix}_body", locale)
        ref_text = _t("fulfillment_ref", locale, order_ref=order_ref)

        # Shipping address reminder for shipped status
        ff = order.get("fulfillment") or {}
        address_line = ""
        if new_status == "shipped" and ff.get("shipping_address"):
            address_line = f'<p style="color: #666;">{ff["shipping_address"]}</p>'

        # Release 1 (Physical) — carrier tracking block when the admin captured
        # it at ship-time. Rendered only on the "shipped" notification so the
        # customer gets a single, actionable link to follow the parcel.
        tracking_block = ""
        if new_status == "shipped":
            tnum = (ff.get("tracking_number") or "").strip()
            turl = (ff.get("tracking_url") or "").strip()
            if tnum or turl:
                tracking_label = _t("fulfillment_tracking_label", locale)
                tracking_cta = _t("fulfillment_tracking_cta", locale)
                # The tracking number is always shown; the URL becomes a CTA.
                if tnum and turl:
                    tracking_block = (
                        f'<p style="color: #333; margin-top: 8px;">'
                        f'📦 <strong>{tracking_label}:</strong> {tnum}'
                        f' &nbsp;·&nbsp; <a href="{turl}">{tracking_cta}</a>'
                        f'</p>'
                    )
                elif tnum:
                    tracking_block = (
                        f'<p style="color: #333; margin-top: 8px;">'
                        f'📦 <strong>{tracking_label}:</strong> {tnum}'
                        f'</p>'
                    )
                elif turl:
                    tracking_block = (
                        f'<p style="color: #333; margin-top: 8px;">'
                        f'📦 <a href="{turl}">{tracking_cta}</a>'
                        f'</p>'
                    )

        account_url = await _build_customer_account_url(order, org_id, "/account")

        html = _wrap_template(f"""
            <p>{_t("greeting", locale)},</p>
            <p>{body_text}</p>
            <p>{ref_text}</p>
            {address_line}
            {tracking_block}
            <p style="text-align: center;">
                <a href="{account_url}" class="btn">{_t("order_received_cta", locale)}</a>
            </p>
        """, locale, reply_to=ctx["reply_to"], store_name=store_name)

        send_email(email, subject, html, reply_to=ctx["reply_to"], sender_name=ctx["sender_name"])
        logger.info("order_email: fulfillment_%s sent to=%s order=%s", new_status, email, order_ref)

    except Exception as e:
        logger.warning("order_email: fulfillment_%s failed: %s", new_status, e)
