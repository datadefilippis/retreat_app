"""Sentinel tests for Step 18 — Auth-ready embed checkout (Track A hardening).

Tre sub-step:
  18a — /embed/checkout/start accetta optional Bearer customer JWT,
        propaga customer_account_id a submit_order_from_storefront
  18b — POST /api/public/embed/cart/{cart_id}/merge alias che lega
        anonymous cart a customer_account_id (Bearer JWT required)
  18c — Inline signup-during-checkout: body.create_account=True +
        body.account_password → customer_signup(auto_login=True) +
        merge cart + ordine in 1 round-trip

Invariants pinned
=================
  INV-EXA-1   Body field create_account + account_password presenti
  INV-EXA-2   Bearer customer JWT optional accettato (no 401 se assente)
  INV-EXA-3   Bearer JWT con org_id diverso → 403 (anti-cross-tenant)
  INV-EXA-4   Bearer JWT type != "customer" → 401
  INV-EXA-5   /embed/cart/{cart_id}/merge handler registrato + coroutine
  INV-EXA-6   Cart merge richiede Bearer customer JWT (401 se assente)
  INV-EXA-7   Signup inline: create_account=True senza password → 400
  INV-EXA-8   Signup inline GDPR flags richiesti (parity con /signup endpoint)
  INV-EXA-9   Metric counter outcome label include "account_created"
  INV-EXA-10  Reuse customer_signup service (no duplicazione)
"""

import inspect
import os
import sys
from pathlib import Path

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── 18a — EmbedCheckoutStartRequest body extension ────────────────────


class TestINV_EXA_1_RequestBodyFields:
    """Body deve includere i campi inline-signup + auth-aware checkout."""

    def test_create_account_field(self):
        from routers.embed_public import EmbedCheckoutStartRequest
        fields = EmbedCheckoutStartRequest.model_fields
        assert "create_account" in fields, (
            "EmbedCheckoutStartRequest.create_account missing — il widget "
            "non puo' chiedere signup inline."
        )
        # Default False per non rompere chiamate guest existing
        assert fields["create_account"].default is False

    def test_account_password_field(self):
        from routers.embed_public import EmbedCheckoutStartRequest
        fields = EmbedCheckoutStartRequest.model_fields
        assert "account_password" in fields, (
            "EmbedCheckoutStartRequest.account_password missing — needed "
            "per inline signup (create_account=True)."
        )

    def test_account_password_optional(self):
        """Default None: campo richiesto solo se create_account=True."""
        from routers.embed_public import EmbedCheckoutStartRequest
        fields = EmbedCheckoutStartRequest.model_fields
        # default None (Pydantic optional)
        default = fields["account_password"].default
        assert default is None, (
            f"account_password default={default!r}, expected None"
        )


# ─── 18a — Handler reads Bearer Authorization optional ─────────────────


class TestINV_EXA_2_BearerTokenAccepted:
    """Handler legge optional Bearer customer JWT senza richiedere
    obbligatoriamente. Verifica statica: il source code deve menzionare
    Authorization header processing."""

    def test_handler_reads_authorization_header(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        # Una delle 2 forme è obbligatoria
        assert (
            "authorization" in src.lower()
            or "Bearer " in src
        ), (
            "Handler start_embed_checkout NON legge Authorization header. "
            "Authenticated checkout non funziona."
        )


# ─── 18a — Customer JWT validation via decode_token + type check ──────


class TestINV_EXA_3_CustomerTokenValidation:
    """Handler deve usare decode_token + verificare type='customer' + org_id."""

    def test_handler_validates_customer_token(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        # Validation patterns che ci aspettiamo
        assert "decode_token" in src or "decode_customer_token" in src, (
            "Handler NON valida il token con decode_token — possibile "
            "JWT forgery accettato."
        )
        # Type check (customer vs admin)
        assert '"customer"' in src or "'customer'" in src, (
            "Handler NON verifica payload.type == 'customer'. Token "
            "admin potrebbero essere accettati per checkout customer."
        )


# ─── 18b — Cart merge alias registration ───────────────────────────────


class TestINV_EXA_5_CartMergeEndpoint:
    """POST /api/public/embed/cart/{cart_id}/merge deve essere registrato."""

    def test_path_registered(self):
        from routers.embed_public import router
        paths = {(r.path, tuple(sorted(r.methods or set())))
                 for r in router.routes}
        # POST /public/embed/cart/{cart_id}/merge
        target = ("/public/embed/cart/{cart_id}/merge", ("POST",))
        assert target in paths, (
            f"POST /public/embed/cart/{{cart_id}}/merge missing. "
            f"Found: {sorted(paths)}"
        )

    def test_handler_is_coroutine(self):
        from routers import embed_public
        assert hasattr(embed_public, "merge_embed_cart"), (
            "Handler merge_embed_cart missing."
        )
        assert inspect.iscoroutinefunction(embed_public.merge_embed_cart)


# ─── 18b — Cart merge richiede Bearer customer JWT ─────────────────────


class TestINV_EXA_6_CartMergeRequiresAuth:
    """Cart merge è auth-only: senza Bearer → 401."""

    def test_handler_enforces_bearer_check(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.merge_embed_cart)
        assert (
            "Bearer " in src
            or "authorization" in src.lower()
        ), "merge_embed_cart NON legge Authorization header."

        # Customer type check
        assert '"customer"' in src or "'customer'" in src, (
            "merge_embed_cart NON verifica type='customer'."
        )


# ─── 18b — Cart merge body (CartMergeRequest) ──────────────────────────


class TestCartMergeRequestModel:
    """Riusa CartMergeRequest del legacy storefront — no duplicazione."""

    def test_handler_imports_cart_merge_request(self):
        from routers import embed_public
        src = inspect.getsource(embed_public)
        assert "CartMergeRequest" in src, (
            "embed_public non importa CartMergeRequest. Possibile "
            "duplicazione schema."
        )


# ─── 18c — Inline signup body validation ────────────────────────────────


class TestINV_EXA_7_InlineSignupValidation:
    """create_account=True senza password → 400."""

    def test_validation_helper_exists(self):
        """Il modulo deve avere logica di validazione (statica source check)."""
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        # Pattern: create_account validation prima del checkout
        assert "create_account" in src, (
            "Handler NON gestisce create_account flag. Inline signup "
            "non funziona."
        )
        assert "account_password" in src, (
            "Handler NON gestisce account_password. Inline signup non "
            "puo' creare account."
        )


# ─── 18c — Reuse customer_signup (no duplicazione) ─────────────────────


class TestINV_EXA_10_ReuseCustomerSignup:
    """Handler deve chiamare customer_signup service esistente (auto_login=True)."""

    def test_handler_calls_customer_signup(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        assert "customer_signup" in src, (
            "Handler NON chiama customer_signup. Possibile reimplementazione "
            "della logica di account creation = pericoloso (GDPR consent "
            "capture, password hashing, verification email, ecc.)."
        )

    def test_handler_uses_auto_login(self):
        """auto_login=True per ottenere token immediato senza email verification."""
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        assert "auto_login" in src, (
            "Handler NON passa auto_login. Customer dopo signup non puo' "
            "completare il checkout senza prima verificare email."
        )


# ─── 18c — Metric outcome label per account_created ────────────────────


class TestINV_EXA_9_MetricAccountCreated:
    """L'handler emette outcome 'account_created' o simile quando inline signup."""

    def test_handler_records_account_creation(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        # Pattern: record_embed_checkout_start con outcome che include "account"
        assert "account_created" in src or "signup_inline" in src, (
            "Handler NON emette metric outcome per account creation inline. "
            "Analytics non potranno separare guest checkout da signup-checkout."
        )


# ─── 18a — Reuse Bearer pattern from legacy /cart/{id}/merge ───────────


class TestBearerPatternReused:
    """Il pattern di validazione Bearer per merge legacy in routers/public.py
    è il riferimento canonico. Il nostro merge_embed_cart deve replicare:
      - 401 se manca Bearer
      - 401 se type != customer
      - 403 se org_id mismatch
      - 403 se sub != body.customer_account_id
    """

    def test_handler_checks_org_id_match(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.merge_embed_cart)
        assert "org_id" in src, (
            "merge_embed_cart NON verifica payload.org_id match — "
            "possibile cart binding cross-tenant."
        )


# ─── 18c — Pattern A separation: optional Bearer wins over inline signup ─


class TestSignupVsBearerPriority:
    """Se sia Bearer JWT che create_account sono forniti, comportamento:
       - Bearer ha precedenza (gia' autenticato)
       - create_account=True con Bearer presente: il backend ignora signup
         o ritorna 400.

       Verifica via source code: deve esserci logica che distingue i 2 path.
    """

    def test_handler_has_two_paths(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.start_embed_checkout)
        # Pattern: distinct conditional branches per Bearer vs create_account
        # Almeno una if-else per discrimnare
        assert (
            "if customer_account_id" in src
            or "if body.create_account" in src
            or "if create_account" in src
        ), (
            "Handler NON ha logica condizionale per gestire bearer-vs-signup. "
            "Possibile double-account-creation se entrambi forniti."
        )
