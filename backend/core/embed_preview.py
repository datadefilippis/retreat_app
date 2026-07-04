"""
Embed preview token — Embed à-la-carte, Fase 5 (2026-06-19).

Token firmato a breve durata che permette all'admin di vedere un'anteprima
LIVE dei blocchi embeddabili del PROPRIO store dentro la dashboard, senza
dover aggiungere l'origin dell'admin agli ``allowed_origins`` pubblici del
merchant.

Sicurezza
=========
- Firmato HMAC (stesso ``JWT_SECRET_KEY`` dell'app), HS256.
- TTL breve (15 min): un token trapelato scade in fretta.
- Scoped allo SLUG: vale solo per quello store.
- READ-ONLY: il ``DynamicCORSMiddleware`` accetta il bypass solo per GET
  (init/products/categories). Mutazioni (cart/checkout POST) restano bloccate
  → nessun ordine creato da un'anteprima.
- NON tocca ``store.allowed_origins``: la configurazione CORS pubblica del
  merchant resta invariata.

Il token e' generato da un endpoint require_admin org-scoped
(``GET /api/stores/{id}/embed-preview-token``), quindi solo il proprietario
dello store puo' ottenerlo.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt

_SECRET = os.environ.get("JWT_SECRET_KEY", "")
_ALG = "HS256"
_TYP = "embed_preview"
_TTL_MINUTES = 15


def mint_preview_token(slug: str, store_id: str, org_id: str) -> tuple[str, int]:
    """Crea un token preview per (slug, store). Ritorna (token, ttl_seconds)."""
    if not _SECRET:
        # Fail-closed: senza secret il token sarebbe firmabile/forgiabile.
        raise RuntimeError("JWT_SECRET_KEY non configurato: preview disabilitata.")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=_TTL_MINUTES)
    token = jwt.encode(
        {
            "typ": _TYP,
            "slug": slug,
            "store_id": store_id,
            "org_id": org_id,
            "iat": int(now.timestamp()),
            "exp": exp,
        },
        _SECRET,
        algorithm=_ALG,
    )
    return token, _TTL_MINUTES * 60


def decode_preview_token(token: str) -> dict | None:
    """Decodifica e valida (firma+exp+typ) il token preview. Ritorna il payload
    (con slug/store_id/org_id) oppure None se invalido. Funzione PURA (no DB)."""
    if not token or not _SECRET:
        return None
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALG])
    except Exception:
        return None
    if payload.get("typ") != _TYP:
        return None
    return payload


def verify_preview_token(token: str, slug: str) -> bool:
    """True se il token e' valido (firma+exp+typ) ed e' per QUESTO slug."""
    payload = decode_preview_token(token)
    return bool(payload) and payload.get("slug") == slug
