"""PlatformAccount — identita' unica dell'utente finale sul marketplace.

Piano: docs/PLATFORM_ACCOUNT_PLAN.md (P1, 5/7/2026).

Livello IDENTITA' sopra i customer_accounts org-scoped (che restano il
CRM di ogni operatore, intatti): una email = un account per tutta la
piattaforma pubblica. Il link avviene via platform_account_id sui
customer_accounts e (denormalizzato) sugli ordini — mai fusione.

Auth magic-link-first: nessuna password al primo giro (password_hash
opzionale, per chi la vorra'). Il token magic e' salvato SOLO hashed
(sha256), one-shot, TTL 15 minuti.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import generate_id


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlatformAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    email: str                                   # normalizzata (lower, strip)
    name: Optional[str] = None
    phone: Optional[str] = None
    language: str = "it"

    email_verified: bool = False                 # True al primo magic link usato
    is_active: bool = True

    # Password OPZIONALE (magic-link-first): None finche' l'utente non
    # decide di impostarla dall'area personale.
    password_hash: Optional[str] = None

    # AP1b — signup con password: verifica email con token one-shot
    # (sha256 a DB, in chiaro solo nell'email) e reset password. Stesso
    # pattern collaudato dei customer_accounts, portato a livello
    # piattaforma. Il reset serve ANCHE agli account nati passwordless
    # (claim acquisto) per impostare la password la prima volta.
    verification_token_hash: Optional[str] = None
    verification_token_expires: Optional[str] = None
    reset_token_hash: Optional[str] = None
    reset_token_expires: Optional[str] = None
    password_changed_at: Optional[str] = None

    # AP1b — anti-bruteforce sul login password (stesse soglie e backoff
    # dei customer: core/security_config + core/lockout_helpers).
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    lockout_count_today: int = 0
    last_failed_login_at: Optional[str] = None

    # Invalidation di tutte le sessioni (logout-all): i JWT con iat
    # precedente vengono rifiutati dalla dependency.
    sessions_invalidated_at: Optional[datetime] = None

    # ID (20/8) — il legame dei cappelli: se questa persona e' anche un
    # operatore, qui vive il suo users.id (e il reciproco
    # users.platform_account_id punta qui). Solo fra email verificate
    # da entrambe le parti; regole in services/identity_link_service.py.
    operator_user_id: Optional[str] = None

    created_at: datetime = Field(default_factory=_utc_now)
    last_login_at: Optional[datetime] = None

    # P2 — anti-spam per l'email "Gestisci le tue prenotazioni": una
    # sola claim email nelle 24h, anche con acquisti multipli ravvicinati.
    claim_last_sent_at: Optional[datetime] = None


class MagicLinkToken(BaseModel):
    """Token magic-link: salvato SOLO l'hash sha256. One-shot + TTL."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    account_id: str
    token_hash: str                              # sha256 hex del token in chiaro
    # OTP a 6 cifre (stessa email del link): hash + contatore tentativi.
    # Il codice e' corto → brute-force mitigato da MAX 5 tentativi,
    # TTL breve e rate-limit sull'endpoint.
    code_hash: Optional[str] = None
    code_attempts: int = 0
    expires_at: datetime
    used_at: Optional[datetime] = None           # one-shot: set al primo uso
    created_at: datetime = Field(default_factory=_utc_now)
