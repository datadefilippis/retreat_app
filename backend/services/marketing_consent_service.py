"""Shared marketing opt-in recorder — F0 (fondamenta modulo Newsletter).

Single source of truth per registrare un opt-in marketing. Esegue:
  1. record immutabile in ``consent_audit`` (document_type="merchant_marketing");
  2. snapshot sync su ``customer_accounts`` (accepted_marketing_at, revoke→None);
  3. snapshot sync su ``customers`` CRM (idem).

Prima questa logica era DUPLICATA inline nel checkout
(``order_creation_service``). Estraendola qui, checkout, signup e il futuro
form newsletter condividono UNA sola implementazione → niente drift
(lezione delle ondate R1–R14).

Semantica "most-recent-wins": settare ``accepted_marketing_at`` e azzerare
``marketing_revoked_at`` fa prevalere un opt-in fresco su qualsiasi revoca
precedente — coerente con la lettura in customer_insights/marketing_consent.

Trust/robustezza:
  - L'audit (prova legale) PUÒ sollevare: i caller che non devono fallire
    (checkout, signup) avvolgono la chiamata nel loro try/except esistente.
  - I due snapshot sync sono best-effort (loggati, mai sollevati) — identico
    al comportamento inline precedente: un sync denormalizzato fallito non
    deve mai bloccare il flusso chiamante.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_VALID_LOCALES = ("it", "en", "de", "fr")


def _normalize_locale(locale: Optional[str]) -> str:
    """consent_audit richiede locale ∈ {it,en,de,fr}; fallback difensivo a 'it'."""
    return locale if locale in _VALID_LOCALES else "it"


async def record_marketing_optin(
    *,
    organization_id: str,
    customer_id: Optional[str] = None,          # FK → customers.id (CRM)
    customer_account_id: Optional[str] = None,  # FK → customer_accounts.id (login)
    store_id: Optional[str] = None,
    email: Optional[str] = None,
    locale: str = "it",
    version_tag: str = "v1.0",
    version_hash: str = "unknown",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    source: str = "customer_marketing_optin",
    order_id: Optional[str] = None,
) -> None:
    """Registra un opt-in marketing su audit + i due snapshot denormalizzati.

    Args (tutti keyword-only per stabilità della signature cross-caller):
        organization_id: org dello store/risorsa.
        customer_id: riga CRM ``customers`` da sincronizzare (None se assente).
        customer_account_id: account login da sincronizzare (None per guest).
        store_id: store di provenienza (None per risorse non legate a store).
        email: email del cliente (per audit guest senza user_id).
        locale/version_tag/version_hash: snapshot legale del consenso.
        ip_address/user_agent: contesto request (forensic).
        source: valore enum di consent_audit (default opt-in marketing cliente).
        order_id: lega l'audit a un ordine (solo checkout; None altrove).

    L'audit può sollevare (caller decide); i sync sono best-effort.
    """
    from repositories import consent_audit_repository as _car

    audit_locale = _normalize_locale(locale)

    # 1. Prova legale immutabile (può sollevare → il caller la gestisce).
    await _car.record_consent(
        user_id=customer_account_id,
        organization_id=organization_id,
        store_id=store_id,
        customer_email=email,
        order_id=order_id,
        locale=audit_locale,
        version_tag=version_tag or "v1.0",
        version_hash=version_hash or "unknown",
        ip_address=ip_address,
        user_agent=user_agent,
        source=source,
        document_type="merchant_marketing",
    )

    # 2 + 3. Snapshot denormalizzati (best-effort, most-recent-wins).
    iso_now = datetime.now(timezone.utc).isoformat()
    set_doc = {
        "accepted_marketing_at": iso_now,
        "marketing_revoked_at": None,
        "updated_at": iso_now,
    }

    if customer_account_id:
        try:
            from database import customer_accounts_collection
            await customer_accounts_collection.update_one(
                {"id": customer_account_id, "organization_id": organization_id},
                {"$set": set_doc},
            )
        except Exception as exc:  # best-effort: non bloccare il caller
            logger.warning(
                "marketing_optin: customer_account sync failed account=%s org=%s: %s",
                customer_account_id, organization_id, exc,
            )

    if customer_id:
        try:
            from database import customers_collection
            await customers_collection.update_one(
                {"id": customer_id, "organization_id": organization_id},
                {"$set": set_doc},
            )
        except Exception as exc:  # best-effort: non bloccare il caller
            logger.warning(
                "marketing_optin: customer CRM sync failed customer=%s org=%s: %s",
                customer_id, organization_id, exc,
            )
