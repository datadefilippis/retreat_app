"""Token iscritto newsletter Aurya — BN2 (BLOG_NEWSLETTER_STRATEGIA).

Stesso disegno del marketing_unsubscribe_token (JWT HS256 sul secret
unico, claim ``scope`` anti-confusione, TTL lungo): un solo token per
email che serve TUTTO il ciclo di vita senza login:
  - link di conferma nell'email di double opt-in (la prova del
    consenso GDPR e' il click);
  - pagina preferenze /newsletter/preferenze/{token};
  - unsubscribe a un click dal footer di ogni lettera.

TTL 5 anni: il link vive dentro email che possono essere aperte mesi
dopo; un link di gestione rotto e' legalmente peggio di un token
longevo (il danno massimo di un token rubato e' modificare le
preferenze di UNA iscrizione, non un accesso).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from core.marketing_unsubscribe_token import (  # riuso: stessi errori tipati
    TokenExpiredError,
    TokenInvalidError,
)

_SCOPE = "newsletter_subscriber"
_ALGORITHM = "HS256"


def _secret() -> str:
    from auth import SECRET_KEY
    return SECRET_KEY


def generate_subscriber_token(email: str, ttl_days: int = 1825) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "scope": _SCOPE,
        "email": (email or "").strip().lower(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=ttl_days)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_subscriber_token(token: str) -> dict:
    """Ritorna {"email", "iat", "exp"}. Solleva TokenInvalidError /
    TokenExpiredError (mappate dal router su 401/410)."""
    if not token or not isinstance(token, str):
        raise TokenInvalidError("missing token")
    try:
        from jose.exceptions import ExpiredSignatureError
        try:
            payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
        except ExpiredSignatureError as exc:
            raise TokenExpiredError(str(exc)) from exc
    except JWTError as exc:
        raise TokenInvalidError(str(exc)) from exc
    if not isinstance(payload, dict) or payload.get("scope") != _SCOPE:
        raise TokenInvalidError("scope mismatch")
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise TokenInvalidError("email assente")
    return {"email": email, "iat": payload.get("iat"), "exp": payload.get("exp")}
