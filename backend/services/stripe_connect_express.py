"""
Stripe Connect Express Service — dedicated connected accounts for merchant commerce.

Model: Destination Charges on Express Accounts.
  - Platform (AFianco) creates a child Stripe account per merchant organization
  - Merchant onboarding and identity verification happen on Stripe-hosted pages
  - Merchant dashboard only shows transactions collected via AFianco
    (data isolation — core privacy/compliance benefit over Standard Connect)
  - Funds are paid out to the merchant's bank account managed by Stripe
  - Future: application_fee_amount for platform revenue

Flow:
  1. start_express_onboarding(org_id)
       → creates a fresh Express account if none exists
       → returns a one-time onboarding Account Link URL (expires in ~5 minutes)
  2. Merchant completes onboarding on Stripe-hosted UI
  3. Merchant is redirected back to {FRONTEND_URL}/settings?stripe_connect=express_return
  4. complete_express_onboarding(org_id)
       → retrieves account from Stripe, checks capability flags
       → updates payment_connections with runtime_status based on charges_enabled
  5. Stripe sends account.updated webhooks on capability changes
       → handle_account_updated(event) keeps runtime_status in sync

This module is intentionally isolated from:
  - services/stripe_connect.py (legacy Standard OAuth flow — untouched)
  - services/stripe_service.py (billing/subscription flow — untouched)
  - services/payment_checkout_service.py (checkout creation — agnostic consumer)

Requires env:
  STRIPE_SECRET_KEY    — platform secret key (shared with billing, by design)
  FRONTEND_URL         — base URL for onboarding return/refresh links
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ── Low-level helpers ─────────────────────────────────────────────────────

def _get_stripe():
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


def _get_frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "https://afianco.app")


def is_express_configured() -> bool:
    """Check if Express Connect can be used (platform secret key is enough)."""
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def _account_capability_snapshot(account) -> dict:
    """Extract capability and requirement state from a Stripe Account object.

    Works with stripe-python v8 typed objects. Uses getattr with sensible defaults
    so a partially-populated account (mid-onboarding) is represented truthfully.
    """
    requirements = getattr(account, "requirements", None)
    currently_due = []
    if requirements is not None:
        currently_due = (
            getattr(requirements, "currently_due", None)
            or (requirements.get("currently_due") if hasattr(requirements, "get") else None)
            or []
        )
    return {
        "charges_enabled": bool(getattr(account, "charges_enabled", False)),
        "payouts_enabled": bool(getattr(account, "payouts_enabled", False)),
        "details_submitted": bool(getattr(account, "details_submitted", False)),
        "requirements_currently_due": list(currently_due),
    }


def _paese_e_valuta(account) -> dict:
    """Lotto S: {country, default_currency} letti da un Account Stripe
    (oggetto o dict del webhook); vuoto se mancano, cosi' un $set non
    cancella mai un valore gia' salvato."""
    def _leggi(k):
        if isinstance(account, dict):
            return account.get(k)
        return getattr(account, k, None) or (account.get(k) if hasattr(account, "get") else None)
    out = {}
    c = _leggi("country")
    if c:
        out["country"] = str(c).upper()
    v = _leggi("default_currency")
    if v:
        out["default_currency"] = str(v).lower()
    return out


def _runtime_status_from_capabilities(caps: dict) -> str:
    """Map a capability snapshot to a PaymentConnection runtime_status.

    Rules (more specific → less specific):
      charges_enabled=True                              → "ready"
      details_submitted=False                           → "needs_auth" (onboarding incomplete)
      requirements_currently_due non-empty              → "needs_auth" (merchant action required)
      charges_enabled=False with no requirements listed → "error"     (disabled by Stripe)
    """
    if caps["charges_enabled"]:
        return "ready"
    if not caps["details_submitted"]:
        return "needs_auth"
    if caps["requirements_currently_due"]:
        return "needs_auth"
    return "error"


# ── Express account creation ──────────────────────────────────────────────

# Lotto S (6/10/2026) — IL PAESE DELL'ACCOUNT. La piattaforma Stripe di
# Aurya e' svizzera (country=CH, chf): fino a oggi Account.create non
# passava `country`, quindi OGNI Express nasceva svizzero e agli operatori
# italiani Stripe chiedeva indirizzo e IBAN svizzeri (3 account in prod,
# nessuno completato: zero incassi online su 45 organizzazioni). Il paese
# di un account Stripe non si cambia dopo la creazione, quindi si sceglie
# PRIMA (Italia preselezionata) e, per chi e' nato svizzero senza volerlo,
# c'e' `ricomincia_express` qui sotto. Paese → valuta dell'account.
PAESI_STRIPE = {
    "IT": "eur", "CH": "chf", "DE": "eur", "FR": "eur", "AT": "eur", "ES": "eur",
}
PAESE_DEFAULT = "IT"
NOMI_PAESI = {"IT": "Italia", "CH": "Svizzera", "DE": "Germania", "FR": "Francia",
              "AT": "Austria", "ES": "Spagna"}


def paese_valido(country: Optional[str]) -> Optional[str]:
    """Il codice paese in maiuscolo se e' fra quelli ammessi, altrimenti None."""
    c = (country or "").strip().upper()
    return c if c in PAESI_STRIPE else None


def paese_suggerito(org: Optional[dict]) -> str:
    """Il paese da preselezionare per un'org: Svizzera se la valuta e' CHF
    o la sede principale e' in Svizzera, altrimenti Italia. E' un
    suggerimento: l'operatore sceglie nel riquadro «Collega gli incassi»."""
    org = org or {}
    if (org.get("currency") or "").upper() == "CHF":
        return "CH"
    try:
        from services.sedi import sedi_da_profilo
        sedi = sedi_da_profilo(org.get("public_profile"))
        paese = (sedi[0].get("paese") or "") if sedi else ""
        if paese.strip().lower() in ("svizzera", "schweiz", "suisse", "switzerland", "ch"):
            return "CH"
    except Exception:  # noqa: BLE001 — un suggerimento non deve mai fermare l'onboarding
        pass
    return PAESE_DEFAULT


async def _create_express_account(org_id: str, email: Optional[str],
                                  country: str = PAESE_DEFAULT) -> str:
    """Create a new Express connected account under the platform.

    Returns the newly created Stripe account ID (acct_...).

    Lotto S (6/10/2026): `country` e `default_currency` passano SEMPRE
    (prima no: ogni account ereditava CH dalla piattaforma). TWINT si
    chiede solo per CH: Stripe lo rifiuta sugli altri paesi e la
    capability non ha senso fuori dalla Svizzera. Per CH resta la regola
    di Sub-stream 2.x: chiesta alla creazione, perche' Connect Express
    non ha un interruttore lato operatore e non si aggiunge dopo.

    See ``ensure_twint_capability_for_org`` below for the post-onboarding
    path used when an org switches currency to CHF after the Stripe
    account already exists.
    """
    stripe = _get_stripe()
    country = paese_valido(country) or PAESE_DEFAULT
    capabilities = {
        "card_payments": {"requested": True},
        "transfers": {"requested": True},
    }
    if country == "CH":
        capabilities["twint_payments"] = {"requested": True}
    kwargs = {
        "type": "express",
        "country": country,
        "default_currency": PAESI_STRIPE[country],
        "metadata": {
            "afianco_org_id": org_id,
        },
        "capabilities": capabilities,
    }
    if email:
        kwargs["email"] = email

    account = await asyncio.to_thread(stripe.Account.create, **kwargs)
    account_id = getattr(account, "id", None) or (account.get("id") if hasattr(account, "get") else None)
    if not account_id:
        raise RuntimeError("Stripe Account.create returned no id")

    logger.info("stripe_connect_express: created Express account %s for org=%s country=%s",
                account_id, org_id, country)
    return account_id


async def _create_account_link(account_id: str, org_id: str) -> str:
    """Create a one-time onboarding Account Link URL (expires in ~5 min)."""
    stripe = _get_stripe()
    frontend_url = _get_frontend_url()
    return_url = f"{frontend_url}/settings?stripe_connect=express_return"
    refresh_url = f"{frontend_url}/settings?stripe_connect=express_refresh"

    link = await asyncio.to_thread(
        stripe.AccountLink.create,
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    url = getattr(link, "url", None) or (link.get("url") if hasattr(link, "get") else None)
    if not url:
        raise RuntimeError("Stripe AccountLink.create returned no url")

    logger.info(
        "stripe_connect_express: created onboarding link for account=%s org=%s", account_id, org_id
    )
    return url


# ── Public entry points (used by the router) ─────────────────────────────

async def start_express_onboarding(org_id: str, email: Optional[str] = None,
                                   country: Optional[str] = None) -> dict:
    """Start or resume Express onboarding for an org.

    Lotto S: `country` e' il paese scelto nel riquadro (IT default); se
    manca si suggerisce dall'org (paese_suggerito). Conta SOLO alla
    creazione: un account esistente ha gia' il suo paese (immutabile) e
    si riprende com'e'; per cambiarlo c'e' ricomincia_express.

    Idempotent:
      - If no connection exists → creates Express account + link
      - If Express connection exists but onboarding incomplete → returns fresh link
      - If a *Standard* connection exists → refuses (legacy coexistence safeguard)
      - If Express connection exists and is ready → returns {status: "ready"}

    Returns: {url?, account_id, status}
    """
    if not is_express_configured():
        return {"status": "error", "error": "Stripe non configurato nel sistema"}

    from database import payment_connections_collection
    from models.common import utc_now

    existing = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "archived": {"$ne": True}},
        {"_id": 0},
    )

    # Block 6: the Standard coexistence guard previously lived here. With
    # Standard fully removed there is only one legitimate connect_type
    # ("express"), so the guard is no longer meaningful. Archived Standard
    # rows (Fase 10a) carry `archived=true` and are ignored by queries that
    # matter (payment_resolution reads is_default+active).

    # Already onboarded and ready — nothing to do.
    if existing and existing.get("connect_type") == "express" and existing.get("runtime_status") == "ready":
        return {
            "status": "ready",
            "account_id": existing.get("external_account_id"),
        }

    # Reuse the existing Express account if we have one; create otherwise.
    account_id = existing.get("external_account_id") if existing else None
    paese_nuovo: Optional[str] = None
    if not account_id:
        paese_nuovo = paese_valido(country)
        if not paese_nuovo:
            from database import organizations_collection
            org = await organizations_collection.find_one(
                {"id": org_id}, {"_id": 0, "currency": 1, "public_profile": 1})
            paese_nuovo = paese_suggerito(org)
        account_id = await _create_express_account(org_id, email, country=paese_nuovo)

    # Upsert the connection document in a pending state.
    now = utc_now()
    if existing:
        await payment_connections_collection.update_one(
            {"id": existing["id"], "organization_id": org_id},
            {"$set": {
                "external_account_id": account_id,
                "connect_type": "express",
                "status": "pending",
                "runtime_status": "needs_auth",
                "runtime_error": None,
                "last_runtime_check_at": now,
                "updated_at": now,
                # Lotto S: il paese si scrive solo se l'account e' nuovo
                **({"country": paese_nuovo, "default_currency": PAESI_STRIPE[paese_nuovo]}
                   if paese_nuovo else {}),
            }},
        )
    else:
        from models.common import generate_id
        doc = {
            "id": generate_id(),
            "organization_id": org_id,
            "provider": "stripe",
            "display_name": "Stripe",
            "external_account_id": account_id,
            "is_default": True,
            "status": "pending",
            "runtime_status": "needs_auth",
            "connect_type": "express",
            # Lotto S (6/10/2026): il paese dell'account, per la card e la regia
            "country": paese_nuovo,
            "default_currency": PAESI_STRIPE.get(paese_nuovo) if paese_nuovo else None,
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
            "requirements_currently_due": [],
            "runtime_error": None,
            "last_runtime_check_at": now,
            "connected_at": None,
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        await payment_connections_collection.insert_one(doc)

    url = await _create_account_link(account_id, org_id)

    # Fase 7b: audit the transition. "resumed" when we reused an existing
    # Express doc, "started" otherwise.
    try:
        from services.payment_connection_history import (
            record_transition, EVENT_ONBOARDING_STARTED, EVENT_ONBOARDING_RESUMED,
        )
        event_kind = EVENT_ONBOARDING_RESUMED if existing else EVENT_ONBOARDING_STARTED
        await record_transition(
            org_id=org_id,
            event=event_kind,
            to_connect_type="express",
            from_connect_type=(existing.get("connect_type") if existing else None),
            external_account_id=account_id,
            metadata={"status": "onboarding", **({"country": paese_nuovo} if paese_nuovo else {})},
        )
    except Exception:
        pass  # history is best-effort by contract

    return {"status": "onboarding", "url": url, "account_id": account_id,
            "country": paese_nuovo or (existing or {}).get("country")}


def si_puo_ricominciare(conn: Optional[dict]) -> bool:
    """Un account si puo' buttare e rifare SOLO se non ha mai lavorato:
    niente dati inviati a Stripe, niente addebiti abilitati, non pronto.
    Un account operativo ha storia (saldo, pagamenti): non si tocca."""
    if not conn or conn.get("connect_type") != "express" or not conn.get("external_account_id"):
        return False
    return (not conn.get("details_submitted") and not conn.get("charges_enabled")
            and conn.get("runtime_status") != "ready" and conn.get("status") != "active")


async def ricomincia_express(org_id: str, country: str, email: Optional[str] = None,
                             actor_user_id: Optional[str] = None) -> dict:
    """Lotto S — «Ricomincia col paese giusto»: elimina su Stripe l'account
    Express mai completato (nato svizzero per il bug della piattaforma),
    archivia la riga locale con traccia, e avvia un onboarding nuovo col
    paese scelto. Rifiuta (status=error) se l'account e' operativo o il
    paese non e' ammesso. Idempotente sul lato Stripe: se l'account non
    esiste piu' (gia' eliminato), si va avanti lo stesso.

    Returns: {status: "onboarding", url, account_id, country} | {status: "error", error}
    """
    if not is_express_configured():
        return {"status": "error", "error": "Stripe non configurato nel sistema"}
    paese = paese_valido(country)
    if not paese:
        return {"status": "error", "error": "Paese non ammesso. Scegli fra: "
                + ", ".join(NOMI_PAESI.values()) + "."}

    from database import payment_connections_collection
    from models.common import utc_now

    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "connect_type": "express",
         "archived": {"$ne": True}},
        {"_id": 0},
    )
    if not conn:
        return {"status": "error", "error": "Nessun account Stripe da rifare: collega gli incassi."}
    if not si_puo_ricominciare(conn):
        return {"status": "error",
                "error": "Questo account Stripe e' gia' operativo: il paese non si puo' cambiare. "
                         "Scrivici a aurya.life@gmail.com e vediamo insieme."}

    vecchio = conn["external_account_id"]
    stripe = _get_stripe()
    try:
        await asyncio.to_thread(stripe.Account.delete, vecchio)
        eliminato = True
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        # gia' sparito su Stripe: l'obiettivo e' comunque raggiunto
        if "No such account" in msg or "resource_missing" in msg:
            eliminato = False
        else:
            logger.error("stripe_connect_express: ricomincia, Account.delete failed account=%s org=%s: %s",
                         vecchio, org_id, exc)
            return {"status": "error", "error": "Stripe non ha permesso di eliminare il vecchio account. Riprova fra poco."}

    now = utc_now()
    await payment_connections_collection.update_one(
        {"id": conn["id"], "organization_id": org_id},
        {"$set": {"archived": True, "archived_at": now, "status": "disconnected",
                  "runtime_status": "unavailable", "is_default": False, "updated_at": now,
                  "metadata": {**(conn.get("metadata") or {}),
                               "ricomincia": {"motivo": "paese", "da": conn.get("country"),
                                              "a": paese, "account_eliminato": eliminato,
                                              "quando": now.isoformat()}}}},
    )
    try:
        from services.payment_connection_history import record_transition
        await record_transition(
            org_id=org_id, event=EVENT_RICOMINCIATO, to_connect_type="express",
            from_connect_type="express", actor_user_id=actor_user_id,
            external_account_id=vecchio,
            metadata={"da": conn.get("country"), "a": paese, "account_eliminato": eliminato},
        )
    except Exception:
        pass  # history is best-effort

    logger.info("stripe_connect_express: ricomincia org=%s vecchio=%s (eliminato=%s) paese=%s",
                org_id, vecchio, eliminato, paese)
    return await start_express_onboarding(org_id, email=email, country=paese)


EVENT_RICOMINCIATO = "restarted_with_country"


async def ensure_twint_capability_for_org(org_id: str) -> dict:
    """Idempotently request ``twint_payments`` on the org's Express account.

    Called from the org-update endpoint when the merchant changes their
    currency to ``CHF`` *after* having already onboarded Stripe. Newer
    accounts (post Sub-stream 2.x) get the capability requested at
    creation time via ``_create_express_account``; this function handles
    the legacy / migration case where the account predates the change.

    Behaviour matrix:

    - No connection / no Stripe account yet
        → {"status": "noop", "reason": "no_account"}
        (The merchant will get the capability requested on first onboarding.)

    - Account is CH and capability already requested/active
        → {"status": "noop", "reason": "already_requested"}
        Stripe is also idempotent on its own — re-requesting an already
        requested capability is a no-op there too — but we short-circuit
        to avoid the round-trip.

    - Account is CH and capability missing
        → calls ``stripe.Account.modify`` with the requested capability,
          returns {"status": "ok", "capability": <new state>}.

    - Account is non-CH (country != "CH")
        → {"status": "country_mismatch", "country": <country>}.
          We do NOT call Stripe.modify in this case: even though Stripe
          would ignore the request silently, surfacing the mismatch lets
          the caller decide whether to warn the merchant ("your Stripe
          account is registered in IT, TWINT is unavailable").

    - Stripe API error
        → {"status": "error", "error": str(exc)}.
          Logged at WARNING; the org-update endpoint should NOT fail the
          currency change because of this — TWINT is a nice-to-have,
          not a blocking precondition for using CHF.

    Never raises: always returns a dict.
    """
    if not is_express_configured():
        return {"status": "noop", "reason": "stripe_not_configured"}

    from database import payment_connections_collection

    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "connect_type": "express"},
        {"_id": 0, "external_account_id": 1},
    )
    if not conn or not conn.get("external_account_id"):
        return {"status": "noop", "reason": "no_account"}

    account_id = conn["external_account_id"]
    stripe = _get_stripe()

    # Retrieve to inspect country + current capability state. Stripe gates
    # TWINT to country=CH: for non-CH accounts we don't even attempt the
    # modify, since a country change is impossible after creation and the
    # caller likely needs to surface a "migrate account" message.
    try:
        account = await asyncio.to_thread(stripe.Account.retrieve, account_id)
    except Exception as exc:
        logger.warning(
            "ensure_twint_capability: Account.retrieve failed account=%s org=%s: %s",
            account_id, org_id, exc,
        )
        return {"status": "error", "error": str(exc), "account_id": account_id}

    country = getattr(account, "country", None) or (
        account.get("country") if hasattr(account, "get") else None
    )
    if country and country != "CH":
        logger.info(
            "ensure_twint_capability: skipping account=%s org=%s — country=%s "
            "(TWINT is gated to country=CH)",
            account_id, org_id, country,
        )
        return {
            "status": "country_mismatch",
            "country": country,
            "account_id": account_id,
        }

    # Inspect current capability dict to short-circuit if already requested.
    # Stripe's capability state is one of: active, pending, inactive,
    # unrequested. Anything other than unrequested means we already asked
    # for it (or got it).
    caps = getattr(account, "capabilities", None) or {}
    if hasattr(caps, "to_dict"):
        try:
            caps = caps.to_dict()
        except Exception:
            caps = {}
    twint_state = caps.get("twint_payments") if isinstance(caps, dict) else None
    if twint_state and twint_state != "unrequested":
        return {
            "status": "noop",
            "reason": "already_requested",
            "capability": twint_state,
            "account_id": account_id,
        }

    # Actually request the capability. ``Account.modify`` is idempotent
    # on Stripe's side: re-requesting is a no-op rather than an error.
    try:
        updated = await asyncio.to_thread(
            stripe.Account.modify,
            account_id,
            capabilities={"twint_payments": {"requested": True}},
        )
    except Exception as exc:
        logger.warning(
            "ensure_twint_capability: Account.modify failed account=%s org=%s: %s",
            account_id, org_id, exc,
        )
        return {"status": "error", "error": str(exc), "account_id": account_id}

    # Read back the new capability state for the response.
    new_caps = getattr(updated, "capabilities", None) or {}
    if hasattr(new_caps, "to_dict"):
        try:
            new_caps = new_caps.to_dict()
        except Exception:
            new_caps = {}
    new_twint = new_caps.get("twint_payments") if isinstance(new_caps, dict) else None

    logger.info(
        "ensure_twint_capability: requested twint_payments on account=%s org=%s state=%s",
        account_id, org_id, new_twint,
    )
    return {
        "status": "ok",
        "capability": new_twint,
        "account_id": account_id,
    }


async def refresh_express_link(org_id: str) -> dict:
    """Regenerate an onboarding link (e.g. if the previous one expired).

    Returns: {url, account_id, status} or {status: "error", error}.
    """
    if not is_express_configured():
        return {"status": "error", "error": "Stripe non configurato nel sistema"}

    from database import payment_connections_collection

    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "connect_type": "express",
         "archived": {"$ne": True}},
        {"_id": 0},
    )
    if not conn or not conn.get("external_account_id"):
        return {"status": "error", "error": "Nessun account Express esistente"}

    account_id = conn["external_account_id"]
    url = await _create_account_link(account_id, org_id)
    return {"status": "onboarding", "url": url, "account_id": account_id}


async def create_dashboard_login_link(org_id: str) -> dict:
    """Generate a short-lived Stripe Express Dashboard login link.

    Express accounts are isolated from the merchant's main Stripe account,
    so merchants can't access them from dashboard.stripe.com directly.
    This wraps `stripe.Account.create_login_link` to give them an entry
    point straight from AFianco settings.

    Preconditions:
      - Express Connect configured on the platform (STRIPE_SECRET_KEY set)
      - A connection exists for the org with connect_type="express" and
        a real external_account_id
      - Stripe's create_login_link requires the account to have completed
        onboarding; we surface its error if not.

    The returned URL is single-use and expires within minutes — do not cache
    it anywhere durable. The frontend should open it as a new tab.

    Returns: {status, url, account_id} or {status: "error", error}.
    """
    if not is_express_configured():
        return {"status": "error", "error": "Stripe non configurato nel sistema"}

    from database import payment_connections_collection

    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "connect_type": "express"},
        {"_id": 0, "external_account_id": 1, "status": 1, "runtime_status": 1},
    )
    if not conn or not conn.get("external_account_id"):
        return {"status": "error", "error": "Nessun account Express esistente"}

    account_id = conn["external_account_id"]
    stripe = _get_stripe()

    try:
        link = await asyncio.to_thread(stripe.Account.create_login_link, account_id)
    except Exception as exc:
        logger.warning(
            "stripe_connect_express: create_login_link failed for account=%s org=%s: %s",
            account_id, org_id, exc,
        )
        return {"status": "error", "error": str(exc), "account_id": account_id}

    url = getattr(link, "url", None) or (link.get("url") if hasattr(link, "get") else None)
    if not url:
        return {"status": "error", "error": "Stripe non ha restituito un URL", "account_id": account_id}

    logger.info(
        "stripe_connect_express: dashboard login link generated for account=%s org=%s",
        account_id, org_id,
    )
    return {"status": "ok", "url": url, "account_id": account_id}


async def complete_express_onboarding(org_id: str) -> dict:
    """Verify onboarding completion by retrieving the account from Stripe.

    Called by the frontend after the merchant returns from the Stripe-hosted
    onboarding flow. Writes capability flags + runtime_status to the DB.

    Returns: {status, account_id, charges_enabled, ...}
    """
    if not is_express_configured():
        return {"status": "error", "error": "Stripe non configurato nel sistema"}

    from database import payment_connections_collection
    from models.common import utc_now

    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "connect_type": "express",
         "archived": {"$ne": True}},
        {"_id": 0},
    )
    if not conn or not conn.get("external_account_id"):
        return {"status": "error", "error": "Nessun account Express da verificare"}

    account_id = conn["external_account_id"]
    stripe = _get_stripe()

    try:
        account = await asyncio.to_thread(stripe.Account.retrieve, account_id)
    except Exception as exc:
        logger.error(
            "stripe_connect_express: Account.retrieve failed for account=%s org=%s: %s",
            account_id, org_id, exc,
        )
        return {"status": "error", "error": str(exc)}

    # Fase 5c: reject test-mode connected accounts in production.
    # Returns a structured error so the frontend can show a specific message
    # instead of silently proceeding and accepting test charges as real revenue.
    try:
        from services.stripe_mode_guard import assert_account_mode_matches, StripeModeMismatch
        assert_account_mode_matches(account, account_id)
    except StripeModeMismatch as mode_err:
        logger.error(
            "stripe_connect_express: mode mismatch for account=%s org=%s (%s)",
            account_id, org_id, mode_err,
        )
        return {
            "status": "error",
            "error": "test_account_in_production",
            "error_detail": str(mode_err),
            "account_id": account_id,
        }

    caps = _account_capability_snapshot(account)
    runtime_status = _runtime_status_from_capabilities(caps)

    now = utc_now()
    update = {
        "charges_enabled": caps["charges_enabled"],
        "payouts_enabled": caps["payouts_enabled"],
        "details_submitted": caps["details_submitted"],
        "requirements_currently_due": caps["requirements_currently_due"],
        "runtime_status": runtime_status,
        "last_runtime_check_at": now,
        "updated_at": now,
        # Lotto S: il paese vero dell'account, da Stripe (anche per le righe nate prima)
        **_paese_e_valuta(account),
    }
    # Flip high-level status and connected_at only when the account goes live.
    if runtime_status == "ready":
        update["status"] = "active"
        update["runtime_error"] = None
        if not conn.get("connected_at"):
            update["connected_at"] = now

    await payment_connections_collection.update_one(
        {"id": conn["id"], "organization_id": org_id},
        {"$set": update},
    )

    logger.info(
        "stripe_connect_express: completed verification for account=%s org=%s runtime=%s",
        account_id, org_id, runtime_status,
    )

    # Fase 7b: when the capability check flips to ready, persist the
    # milestone. runtime_ready events are the heartbeat of a successful
    # onboarding — a drop-off between onboarding_started and runtime_ready
    # is an obvious signal for support.
    if runtime_status == "ready" and conn.get("runtime_status") != "ready":
        try:
            from services.payment_connection_history import (
                record_transition, EVENT_RUNTIME_READY,
            )
            await record_transition(
                org_id=org_id,
                event=EVENT_RUNTIME_READY,
                to_connect_type="express",
                from_connect_type="express",
                external_account_id=account_id,
                metadata={
                    "charges_enabled": caps["charges_enabled"],
                    "payouts_enabled": caps["payouts_enabled"],
                    "details_submitted": caps["details_submitted"],
                },
            )
        except Exception:
            pass  # history is best-effort

    return {
        "status": runtime_status,
        "account_id": account_id,
        "charges_enabled": caps["charges_enabled"],
        "payouts_enabled": caps["payouts_enabled"],
        "details_submitted": caps["details_submitted"],
        "requirements_currently_due": caps["requirements_currently_due"],
    }


# ── Webhook handler (registered into stripe_service._EVENT_HANDLERS) ─────

async def handle_account_updated(event) -> dict:
    """Handler for Stripe `account.updated` events (Connect-only).

    Defensive design (Option A — billing-safety gate):
      - If event.account is None → platform-level event, ignore
      - If no matching payment_connection found → ignore (not our account)
      - If connection is `standard` → ignore (Express webhook only updates Express docs)
      - Otherwise → refresh capability flags and runtime_status

    Never raises: always returns {status: "processed" | "ignored", ...}.
    This keeps the webhook endpoint returning 200 for any account.updated event
    and prevents Stripe retries for events we legitimately do not care about.
    """
    from database import payment_connections_collection
    from models.common import utc_now

    event_id = event.get("id", "unknown") if hasattr(event, "get") else getattr(event, "id", "unknown")
    data = event.get("data", {}) if hasattr(event, "get") else {}
    account = data.get("object", {}) if isinstance(data, dict) else {}
    account_id = account.get("id") if isinstance(account, dict) else None

    if not account_id:
        logger.debug("stripe_connect_express: account.updated event=%s has no account id", event_id)
        return {"status": "ignored", "reason": "no_account_id", "event_id": event_id}

    conn = await payment_connections_collection.find_one(
        {"provider": "stripe", "external_account_id": account_id},
        {"_id": 0},
    )
    if not conn:
        logger.debug(
            "stripe_connect_express: account.updated for unknown account=%s — ignoring",
            account_id,
        )
        return {"status": "ignored", "reason": "unknown_account", "event_id": event_id, "account": account_id}

    # Legacy Standard connections: we don't currently sync capability changes for them.
    # This is intentional — Standard accounts represent the merchant's own Stripe account
    # which they manage directly; our runtime_status stays "ready" until OAuth is revoked.
    if conn.get("connect_type") == "standard":
        return {
            "status": "ignored",
            "reason": "standard_account",
            "event_id": event_id,
            "account": account_id,
        }

    caps = _account_capability_snapshot(account if not isinstance(account, dict) else type("A", (), account)())
    # Fallback: when account is a plain dict (common in webhook payloads), use dict access.
    if isinstance(account, dict):
        requirements = account.get("requirements") or {}
        caps = {
            "charges_enabled": bool(account.get("charges_enabled", False)),
            "payouts_enabled": bool(account.get("payouts_enabled", False)),
            "details_submitted": bool(account.get("details_submitted", False)),
            "requirements_currently_due": list(requirements.get("currently_due") or []),
        }

    runtime_status = _runtime_status_from_capabilities(caps)
    now = utc_now()

    update = {
        "charges_enabled": caps["charges_enabled"],
        "payouts_enabled": caps["payouts_enabled"],
        "details_submitted": caps["details_submitted"],
        "requirements_currently_due": caps["requirements_currently_due"],
        "runtime_status": runtime_status,
        "last_runtime_check_at": now,
        "updated_at": now,
        **_paese_e_valuta(account),   # Lotto S
    }
    if runtime_status == "ready":
        update["status"] = "active"
        update["runtime_error"] = None
        if not conn.get("connected_at"):
            update["connected_at"] = now

    await payment_connections_collection.update_one(
        {"id": conn["id"], "organization_id": conn["organization_id"]},
        {"$set": update},
    )

    logger.info(
        "stripe_connect_express: synced account=%s org=%s runtime=%s event=%s",
        account_id, conn["organization_id"], runtime_status, event_id,
    )
    return {
        "status": "processed",
        "event_id": event_id,
        "account": account_id,
        "org_id": conn["organization_id"],
        "runtime_status": runtime_status,
    }
