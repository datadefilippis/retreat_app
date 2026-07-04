"""Newsletter form models — F1 (modulo Newsletter / form embeddabili).

Un ``NewsletterForm`` è una risorsa **org-scoped** con identità embed propria
(slug + allowed_origins), opzionalmente collegata a uno store ma non
obbligatoriamente (l'utente può crearla solo per embed esterno). Riusa
``FieldConfig`` per i campi custom (oltre ai built-in email/name/phone).

Una ``NewsletterSubscription`` è l'evento di iscrizione: traccia email +
campi compilati + la **sorgente** esatta (D7) da cui è arrivata. L'opt-in
marketing effettivo è delegato a ``services.marketing_consent_service`` e
riflesso sui ``customers`` (così l'iscritto appare in Customer Insights).
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator

from .common import generate_id, utc_now
from .field_config import FieldConfig
from .store import _validate_allowed_origins

import re

# Slug embed del form: lowercase, numeri, trattini (come gli store slug).
_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def normalize_external_url(url: Optional[str]) -> Optional[str]:
    """Normalizza un URL esterno: senza schema → assoluto https:// così il
    link privacy custom NON viene trattato come relativo (es. evita che
    'afianco.ch/x' diventi '<origin>/afianco.ch/x'). None/'' → None."""
    u = (url or "").strip()
    if not u:
        return None
    if not re.match(r"^https?://", u, re.IGNORECASE):
        u = "https://" + u
    return u
# Colore esadecimale #RRGGBB.
_HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class NewsletterTheme(BaseModel):
    """Personalizzazione colori del form (F7). Mappati a CSS custom properties
    dal web component: primary_color → --afianco-color-primary (bottone), ecc."""
    model_config = ConfigDict(extra="ignore")
    primary_color: Optional[str] = Field(default=None, pattern=_HEX_COLOR)
    primary_text_color: Optional[str] = Field(default=None, pattern=_HEX_COLOR)


# ── NewsletterForm (config admin) ─────────────────────────────────────────

class NewsletterFormBase(BaseModel):
    """Campi condivisi tra create/update/full del form."""
    name: str = Field(min_length=1, max_length=120)
    # Store opzionale: il form può vivere standalone (solo embed esterno).
    store_id: Optional[str] = None
    # Campi built-in attivabili (email è SEMPRE presente, non configurabile).
    collect_name: bool = False
    collect_phone: bool = False
    # Campi custom (riusa FieldConfig: text/textarea/number/email/tel/select/checkbox).
    field_configs: List[FieldConfig] = Field(default_factory=list, max_length=30)
    # Testo consenso privacy/marketing mostrato accanto alla checkbox.
    consent_text: Optional[str] = Field(default=None, max_length=2000)
    # Se True, il submit richiede la spunta privacy esplicita.
    privacy_required: bool = True
    success_message: Optional[str] = Field(default=None, max_length=500)
    redirect_url: Optional[str] = Field(default=None, max_length=500)
    # F8 — layout del form: verticale (default), orizzontale, inline.
    layout: Literal["vertical", "horizontal", "inline"] = "vertical"
    # F7 — personalizzazione colori.
    theme: Optional[NewsletterTheme] = None
    # F7 — sorgente della privacy policy linkata nel consenso:
    #   'none'   = nessun link (solo consent_text);
    #   'store'  = riusa la privacy di uno store dell'org (privacy_store_id);
    #   'custom' = URL personalizzato (privacy_custom_url).
    privacy_mode: Literal["none", "store", "custom"] = "none"
    privacy_store_id: Optional[str] = None
    privacy_custom_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("privacy_custom_url")
    @classmethod
    def _norm_custom_url(cls, v):
        return normalize_external_url(v)


class NewsletterForm(NewsletterFormBase):
    """Documento completo persistito in ``newsletter_forms``."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    # Identità embed propria: unico per org, usato nel path pubblico.
    slug: str = Field(min_length=3, max_length=50, pattern=_SLUG_PATTERN)
    # Origins autorizzati per l'embed di QUESTO form (CORS). Se store_id è
    # valorizzato, a runtime si possono ereditare quelli dello store.
    allowed_origins: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("allowed_origins")
    @classmethod
    def _check_origins(cls, v):
        return _validate_allowed_origins(v)


class NewsletterFormCreate(NewsletterFormBase):
    """Payload create. slug opzionale (derivato da name se assente, lato router)."""
    slug: Optional[str] = Field(default=None, min_length=3, max_length=50, pattern=_SLUG_PATTERN)
    allowed_origins: List[str] = Field(default_factory=list)

    @field_validator("allowed_origins")
    @classmethod
    def _check_origins(cls, v):
        return _validate_allowed_origins(v)


class NewsletterFormPublic(BaseModel):
    """Shape public-safe esposta all'embed (no org/store/origins/timestamps).

    È ciò che ``<afianco-newsletter-form>`` fetcha per renderizzare i campi.
    """
    id: str
    name: str
    collect_name: bool = False
    collect_phone: bool = False
    field_configs: List[FieldConfig] = Field(default_factory=list)
    consent_text: Optional[str] = None
    privacy_required: bool = True
    success_message: Optional[str] = None
    redirect_url: Optional[str] = None
    # F8 — layout
    layout: Literal["vertical", "horizontal", "inline"] = "vertical"
    # F7 — colori + privacy policy risolta lato server per il render.
    theme: Optional[NewsletterTheme] = None
    privacy_policy_url: Optional[str] = None


class NewsletterFormUpdate(BaseModel):
    """Payload update parziale (PATCH)."""
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    store_id: Optional[str] = None
    collect_name: Optional[bool] = None
    collect_phone: Optional[bool] = None
    field_configs: Optional[List[FieldConfig]] = Field(default=None, max_length=30)
    consent_text: Optional[str] = Field(default=None, max_length=2000)
    privacy_required: Optional[bool] = None
    success_message: Optional[str] = Field(default=None, max_length=500)
    redirect_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    # F8
    layout: Optional[Literal["vertical", "horizontal", "inline"]] = None
    # F7
    theme: Optional[NewsletterTheme] = None
    privacy_mode: Optional[Literal["none", "store", "custom"]] = None
    privacy_store_id: Optional[str] = None
    privacy_custom_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("privacy_custom_url")
    @classmethod
    def _norm_custom_url(cls, v):
        return normalize_external_url(v)


# ── NewsletterSubscription (evento di iscrizione) ─────────────────────────

class NewsletterSubscription(BaseModel):
    """Iscrizione registrata via form. Include il tracciamento sorgente (D7)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    form_id: str
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    # Valori dei campi custom, keyed by FieldConfig.id.
    fields_data: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["confirmed", "unsubscribed"] = "confirmed"
    # FK → customers.id (org-scoped), per il join in Customer Insights.
    customer_id: Optional[str] = None
    # ── Tracciamento sorgente (D7) ──
    source_url: Optional[str] = None              # client: window.location.href
    source_origin: Optional[str] = None           # server: header Origin (trust)
    source_referrer: Optional[str] = None         # client: document.referrer
    source_referrer_server: Optional[str] = None  # server: header Referer (trust)
    source_label: Optional[str] = None            # attributo snippet source="..."
    # Forensic
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NewsletterSubmitRequest(BaseModel):
    """Payload pubblico del submit form (dal web component embed)."""
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)
    fields_data: Dict[str, Any] = Field(default_factory=dict)
    consent_privacy: bool = False
    # D7 — sorgente lato client
    source_url: Optional[str] = Field(default=None, max_length=2000)
    source_referrer: Optional[str] = Field(default=None, max_length=2000)
    source_label: Optional[str] = Field(default=None, max_length=120)
    # Anti-bot honeypot: se valorizzato → bot → si scarta silenziosamente.
    hp: Optional[str] = Field(default=None, max_length=200)


class NewsletterSubmitResponse(BaseModel):
    success: bool
    message: str
    subscriber_id: Optional[str] = None
