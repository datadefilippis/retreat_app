"""Sentinel tests for OrderCreationService (Phase 0 Step 3).

Pin del contract del service appena estratto. Garantisce che:
  1. Il service module esista e sia importabile
  2. La signature di ``submit_order_from_storefront`` sia stabile
  3. Il router public.py chiami il service (unico path dopo R10)
  4. Il legacy inline + flag siano stati rimossi (R10) — niente drift

Questi sentinel sono la rete di sicurezza per i futuri callers
(embed widget Stream A, AI site Stream B): se uno di loro chiamerà
il service con la wrong shape, fallisce CI prima del deploy.
"""

import inspect
import os
import sys
from pathlib import Path

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── Service module contract ────────────────────────────────────────────


class TestOrderCreationServiceModule:
    """Contract del modulo services.order_creation_service."""

    def test_service_module_importable(self):
        """Il modulo deve essere importabile senza circular import."""
        from services import order_creation_service
        assert order_creation_service is not None

    def test_submit_order_from_storefront_exists(self):
        """L'entry point principale esiste e è async."""
        from services.order_creation_service import submit_order_from_storefront
        assert inspect.iscoroutinefunction(submit_order_from_storefront), (
            "submit_order_from_storefront deve essere async (interagisce "
            "con Mongo Motor + altri service async)."
        )

    def test_submit_order_signature(self):
        """Signature must accept keyword-only parameters with explicit types.

        Tutti i parametri sono keyword-only per evitare passaggi
        posizionali errati dai callers (Stream A embed, Stream B AI).
        Migliore type safety + leggibilità.
        """
        from services.order_creation_service import submit_order_from_storefront
        sig = inspect.signature(submit_order_from_storefront)
        params = sig.parameters

        # Required parameters
        required = {"org", "body", "customer_account_id", "customer_id"}
        for p in required:
            assert p in params, f"submit_order_from_storefront missing required param: {p}"

        # Optional parameters
        optional = {"client_ip", "user_agent"}
        for p in optional:
            assert p in params, f"submit_order_from_storefront missing param: {p}"

    def test_submit_order_uses_keyword_only_params(self):
        """Tutti i parametri sono keyword-only (dopo `*`).

        Previene chiamate posizionali ambiguous da callers che
        passerebbero `org` e `body` in ordine inverso senza errore.
        """
        from services.order_creation_service import submit_order_from_storefront
        sig = inspect.signature(submit_order_from_storefront)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
                f"Parameter {name!r} non è keyword-only. Cambiare la "
                "signature dopo che embed/AI surface l'hanno integrata "
                "è un breaking change."
            )


# ─── R10: flag rimosso ──────────────────────────────────────────────────


class TestFeatureFlagRemoved:
    """R10 — il dual-path/flag è stato eliminato: il service è l'unico path."""

    def test_feature_flag_function_gone(self):
        """``use_order_creation_service`` non deve più esistere."""
        import services.order_creation_service as svc
        assert not hasattr(svc, "use_order_creation_service"), (
            "use_order_creation_service è ancora presente: R10 prevede la "
            "rimozione del flag (service = unico path)."
        )


# ─── Router integration contract ────────────────────────────────────────


class TestRouterUsesService:
    """Verify the router public.py routes through the service (unico path, R10)."""

    def test_router_imports_service(self):
        """The router uses `submit_order_from_storefront` in submit_order_request."""
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        assert "submit_order_from_storefront" in source, (
            "Router submit_order_request non chiama submit_order_from_storefront."
        )

    def test_router_no_longer_references_flag(self):
        """R10 — il router non deve più riferire il flag rimosso."""
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        assert "use_order_creation_service" not in source, (
            "Router referenzia ancora il flag rimosso (R10)."
        )

    def test_router_preserves_response_shape(self):
        """The router still returns OrderRequestResponse with same 7 fields."""
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        # Marker: la response constructor deve essere ancora OrderRequestResponse
        assert "OrderRequestResponse(" in source, (
            "Router non costruisce più OrderRequestResponse. CTR-1 violato."
        )
        # Tutti i 5 campi opzionali + 2 obbligatori
        for field in [
            "message=", "order_id=", "transaction_mode=",
            "order_status=", "payment_checkout_url=", "payment_reason=",
        ]:
            assert field in source, (
                f"Router response missing field assignment: {field}. "
                "CTR-1 response shape violato."
            )


# ─── R10: legacy inline rimosso ─────────────────────────────────────────


class TestLegacyPathRemoved:
    """R10 — il legacy inline order-creation in public.py è stato eliminato."""

    def test_legacy_order_creation_gone_from_public(self):
        """Il triple-write GDPR vive SOLO nel service ora (non più in public.py).

        Prima di R10 il triple-write (record_consent) esisteva sia nel legacy
        inline di ``public.py`` sia nel service. Rimosso il legacy, in
        ``public.py`` non deve più comparire la logica di order-creation
        (record_consent): è la prova che il drift-path è andato.
        """
        from routers import public
        source = inspect.getsource(public)
        assert "record_consent" not in source, (
            "public.py contiene ancora logica legacy di order-creation "
            "(record_consent): R10 prevede la rimozione del path inline."
        )

    def test_service_module_has_marketing_optin_triple_write(self):
        """Il triple-write marketing vive nel service condiviso
        ``marketing_consent_service`` (F0); il modulo ordini vi delega."""
        from services import order_creation_service, marketing_consent_service
        oc_src = inspect.getsource(order_creation_service)
        mc_src = inspect.getsource(marketing_consent_service)
        # F0 — delega
        assert "record_marketing_optin" in oc_src, (
            "order_creation_service non delega a record_marketing_optin (drift)."
        )
        # Triple-write nel service condiviso
        assert "record_consent" in mc_src, (
            "marketing_consent_service manca record_consent. INV-3 non protetto."
        )
        assert "customer_accounts_collection.update_one" in mc_src, (
            "marketing_consent_service manca la sync customer_accounts."
        )
        assert "customers_collection.update_one" in mc_src, (
            "marketing_consent_service manca la sync customers (write 3/3)."
        )

    def test_service_module_has_gdpr_snapshot(self):
        """INV-4 (GDPR snapshot) presente nel service."""
        from services import order_creation_service
        source = inspect.getsource(order_creation_service)
        for field in [
            "gdpr_terms_version", "gdpr_privacy_version",
            "gdpr_locale", "gdpr_accepted_at", "gdpr_marketing_accepted",
        ]:
            assert field in source, (
                f"Service module manca GDPR field: {field}. INV-4 "
                "non protetto nel nuovo path."
            )
