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

    # Invalidation di tutte le sessioni (logout-all): i JWT con iat
    # precedente vengono rifiutati dalla dependency.
    sessions_invalidated_at: Optional[datetime] = None

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
    expires_at: datetime
    used_at: Optional[datetime] = None           # one-shot: set al primo uso
    created_at: datetime = Field(default_factory=_utc_now)
