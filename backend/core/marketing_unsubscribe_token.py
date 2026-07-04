"""Marketing unsubscribe token — Wave GDPR-Commerce Piece 1b (2026-05-19).

Signed, long-lived, scope-isolated tokens that let a customer revoke
marketing consent WITHOUT logging in. Required by GDPR Art. 7(3)
("withdrawal must be as easy as giving consent") for the GUEST
checkout path: a guest customer who ticked "I want the newsletter"
at checkout has no account → no portal login → must still be able
to opt out with one click.

Design choices (and why):

  · JWT signed with the existing ``SECRET_KEY`` (HS256). We piggy-back
    on the auth.py secret so there's exactly ONE shared secret to
    rotate; the ``scope`` claim guards against confusion attacks (a
    login token can never be replayed as an unsubscribe token, and
    vice versa).

  · TTL = 5 years (1825 days). The token lives inside email campaigns
    the customer may open weeks or months after delivery — short
    TTLs would make the unsubscribe link silently broken, which is
    legally worse than a long-lived link (the consequence of a leaked
    token is "someone gets opted out of marketing", not financial loss).

  · No customer_account_id in the payload — the token is keyed on
    ``email + organization_id`` so it works identically for guests
    (no account at all) and registered customers.

  · Lowercase + trim of the email at sign-time so the token always
    encodes the canonical form. The verifier does NOT re-normalise,
    so the decoded payload IS the source of truth for downstream
    consent_audit writes.

The two public functions:

  generate_marketing_unsubscribe_token(email, organization_id,
                                       ttl_days=1825) -> str
  decode_marketing_unsubscribe_token(token) -> dict
      Returns {"email": ..., "organization_id": ..., "iat": ..., "exp": ...}.
      Raises TokenInvalidError (401-style) or TokenExpiredError (410-style)
      on failure so the router can map each to the right HTTP code.

Token shape (decoded payload):
  {
    "scope":  "marketing_unsubscribe",  # constant — confusion-attack guard
    "email":  "<lowercase trimmed>",
    "org_id": "<organization_id>",
    "iat":    <unix int>,
    "exp":    <unix int>,
  }
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any  # noqa: F401

from jose import JWTError, jwt


# ── Constants ──────────────────────────────────────────────────────────────

# Confusion-attack guard. Any token whose payload is missing this exact
# scope value is rejected as if the signature were invalid — so a JWT
# minted by ``create_access_token`` in auth.py CANNOT be replayed against
# the unsubscribe endpoint even though both share the same secret.
_SCOPE = "marketing_unsubscribe"

# 5-year default TTL — long enough to outlive any reasonable email
# campaign retention. The customer can open a 2023 newsletter in 2027
# and the link will still work.
_DEFAULT_TTL_DAYS = 1825


# ── Exceptions ─────────────────────────────────────────────────────────────

class TokenInvalidError(Exception):
    """Token signature is wrong, payload malformed, or scope mismatched.

    Maps to HTTP 401 in the router. The customer should be told the
    link is invalid (do NOT leak whether the email exists in the DB —
    treat all signature/scope failures uniformly).
    """


class TokenExpiredError(Exception):
    """Token signature is valid but the exp claim has passed.

    Maps to HTTP 410 in the router. The merchant should re-export
    their CSV (with fresh tokens) before sending another campaign.
    """


# ── Public API ─────────────────────────────────────────────────────────────

def generate_marketing_unsubscribe_token(
    *,
    email: str,
    organization_id: str,
    ttl_days: int = _DEFAULT_TTL_DAYS,
) -> str:
    """Sign and return an unsubscribe token for the given email + org.

    The email is canonicalised (lowercase + strip) before signing so
    that the same logical address always produces the same payload
    regardless of how the merchant copy-pasted it into Mailchimp.

    Raises ValueError if email or organization_id are falsy — these
    are programmer errors, not user errors; the caller (CSV exporter
    or admin tool) should never feed empty values.
    """
    # Import lazily so importing this module does not trigger the
    # fail-fast secret check in auth.py before tests have a chance
    # to set the env var. (auth.py raises at import-time if the
    # env var is missing — see its top-of-file guard.)
    from auth import SECRET_KEY, ALGORITHM

    if not email or not str(email).strip():
        raise ValueError("generate_marketing_unsubscribe_token: email required")
    if not organization_id or not str(organization_id).strip():
        raise ValueError(
            "generate_marketing_unsubscribe_token: organization_id required"
        )
    if ttl_days <= 0:
        raise ValueError(
            "generate_marketing_unsubscribe_token: ttl_days must be positive"
        )

    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=int(ttl_days))

    payload = {
        "scope": _SCOPE,
        "email": str(email).strip().lower(),
        "org_id": str(organization_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_marketing_unsubscribe_token(token: str) -> dict:
    """Validate signature + scope + expiry and return the decoded claims.

    Raises:
      TokenInvalidError — bad signature, malformed payload, missing
        or wrong ``scope`` claim, missing email/org_id.
      TokenExpiredError — signature OK but ``exp`` in the past.

    Returns:
      {"email": str, "organization_id": str, "iat": int, "exp": int}

    The returned ``organization_id`` is mapped from the compact
    ``org_id`` claim so the caller can pass it to consent_audit
    writers without renaming.
    """
    from auth import SECRET_KEY, ALGORITHM

    if not token or not isinstance(token, str):
        raise TokenInvalidError("missing token")

    try:
        # python-jose raises ExpiredSignatureError (a subclass of JWTError)
        # specifically when `exp` is in the past — we catch it first to
        # map to the dedicated 410 error class.
        from jose.exceptions import ExpiredSignatureError
        try:
            claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except ExpiredSignatureError as exc:
            raise TokenExpiredError(str(exc)) from exc
    except JWTError as exc:
        # Any other JWT error (bad signature, malformed, unsupported
        # algorithm) collapses to "invalid" — we do NOT leak the
        # specific reason to the caller.
        raise TokenInvalidError(str(exc)) from exc

    if not isinstance(claims, dict):
        raise TokenInvalidError("decoded payload not an object")

    if claims.get("scope") != _SCOPE:
        # Confusion-attack guard — a non-unsubscribe token (e.g. a
        # login JWT) signed with the same secret would otherwise pass
        # the signature check. We treat this as "invalid" to avoid
        # leaking whether the token was a real JWT from another scope.
        raise TokenInvalidError("scope mismatch")

    email = claims.get("email")
    org_id = claims.get("org_id")
    if not isinstance(email, str) or not email:
        raise TokenInvalidError("payload missing email")
    if not isinstance(org_id, str) or not org_id:
        raise TokenInvalidError("payload missing org_id")

    return {
        "email": email,
        "organization_id": org_id,
        "iat": int(claims.get("iat") or 0),
        "exp": int(claims.get("exp") or 0),
    }


# ── URL builders (helpers for CSV export + email footers) ──────────────────

def build_unsubscribe_url(
    *,
    email: str,
    organization_id: str,
    frontend_base_url: str | None = None,
    ttl_days: int = _DEFAULT_TTL_DAYS,
) -> str:
    """Return a fully-qualified ``{frontend}/u/<token>`` URL.

    Used by the CSV export (CI-admin-vis) so the merchant can paste
    the column straight into Mailchimp / Brevo as a merge tag, or
    into a hand-rolled newsletter footer.

    ``frontend_base_url`` defaults to ``FRONTEND_URL`` env var, which
    in turn defaults to ``https://afianco.app`` (the production
    domain — see services/payment_checkout_service.py for the same
    pattern). A trailing slash on the base URL is tolerated.
    """
    import os

    base = (
        frontend_base_url
        or os.environ.get("FRONTEND_URL")
        or "https://afianco.app"
    ).rstrip("/")
    token = generate_marketing_unsubscribe_token(
        email=email,
        organization_id=organization_id,
        ttl_days=ttl_days,
    )
    return f"{base}/u/{token}"
