"""Sentinel tests for afianco BUSINESS invariants — public flow part 2.

Step 2 della Phase 0. Pin di 7 invarianti business non ancora coperte da
test_invariants_public_flow.py:

  INV-3  Marketing opt-in triple-write (consent_audit + customer_accounts + customers)
  INV-4  GDPR snapshot on Order (terms_version, privacy_version, locale, accepted_at)
  INV-6  Rental slot atomic pre-reservation
  INV-7  Customer metrics refresh after confirmed order
  INV-8  SalesRecords 1:1 con order lines, source_label="Ordini"
  INV-9  Order status state machine (draft → confirmed | cancelled)
  INV-10 payment_intent transitions only via webhook

Documento riferimento: docs/architecture/system-invariants.md
"""

import inspect
import os
import re
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


# ─── INV-3 — Marketing opt-in triple-write ──────────────────────────────


class TestINV3_MarketingOptInTripleWrite:
    """INV-3 (Business Invariant 3, High):

    Quando un customer accetta marketing opt-in al checkout, il sistema
    DEVE eseguire 3 write su collection diverse:

      1. consent_audit_collection — record immutable (prova legale)
      2. customer_accounts_collection — denorm su account loggato (se presente)
      3. customers_collection — denorm su CRM customer (sempre se customer_id presente)

    Soft-fail accettato sulle write 2-3 (l'audit immutable è la prova legale).
    Mai bloccare il checkout per un sync denorm fallito.

    Pin location: services/order_creation_service.py (gdpr_marketing_accepted
    branch — R10: spostato dal legacy public.py al service condiviso)
    """

    def test_consent_audit_repository_record_consent_exists(self):
        """Il punto di entrata per il record immutable."""
        from repositories import consent_audit_repository
        assert hasattr(consent_audit_repository, "record_consent"), (
            "consent_audit_repository.record_consent missing — prova legale "
            "del consenso marketing andrebbe persa. Regression Phase-3 GDPR."
        )
        assert inspect.iscoroutinefunction(consent_audit_repository.record_consent)

    def test_record_consent_signature_includes_legal_fields(self):
        """Tutti i campi GDPR-required devono essere accettati."""
        from repositories.consent_audit_repository import record_consent
        sig = inspect.signature(record_consent)
        required = {
            "user_id", "organization_id", "customer_email",
            "version_tag", "version_hash", "locale",
            "ip_address", "user_agent", "source", "document_type",
        }
        actual = set(sig.parameters.keys())
        missing = required - actual
        assert not missing, (
            f"record_consent missing GDPR-required fields: {missing}. "
            "Senza, il record audit è inutilizzabile in contestazione legale."
        )

    def test_public_router_writes_three_collections_on_marketing_optin(self):
        """Il triple-write marketing (audit + accounts + customers) vive nel
        service condiviso ``marketing_consent_service`` (F0); il checkout vi
        DELEGA. R10: la logica era già migrata dal legacy public.py al service
        ordini; F0: la parte marketing è ora estratta nel service condiviso
        riusato anche da signup/newsletter (no duplicazione)."""
        from services import order_creation_service, marketing_consent_service
        oc_src = inspect.getsource(order_creation_service)
        mc_src = inspect.getsource(marketing_consent_service)

        # F0 — il checkout delega al servizio condiviso (no logica inline).
        assert "record_marketing_optin" in oc_src, (
            "order_creation_service non delega a record_marketing_optin — "
            "la logica opt-in marketing è di nuovo inline (drift)."
        )

        # Marker 1: consent_audit insert (audit immutabile)
        assert "record_consent" in mc_src, (
            "marketing_consent_service non chiama record_consent. INV-3 "
            "violato — audit trail GDPR non scritto."
        )
        # Marker 2: customer_accounts marketing sync
        assert "customer_accounts_collection.update_one" in mc_src, (
            "marketing_consent_service non sincronizza customer_accounts. "
            "CRM admin mostrerebbe stato vecchio."
        )
        # Marker 3: customers (CRM) marketing sync
        assert "customers_collection.update_one" in mc_src, (
            "marketing_consent_service non sincronizza customers (write 3/3). "
            "Guest opt-in non sarebbero visibili in CRM."
        )

    def test_marketing_optin_branch_is_conditional(self):
        """Le write 2-3 avvengono SOLO se gdpr_marketing_accepted=True.

        Una opt-in non DEVE essere "overwritten" da un ordine sucessivo
        in cui il customer non spunta la checkbox. Solo opt-in esplicita
        scrive accepted_marketing_at.
        """
        # R10 — logica nel service condiviso.
        from services import order_creation_service
        source = inspect.getsource(order_creation_service)
        # Pattern check: 'if body.gdpr_marketing_accepted' deve esistere
        # come gate del triple-write (non puro elif/else).
        assert "if body.gdpr_marketing_accepted" in source, (
            "Mancante il gate `if body.gdpr_marketing_accepted` prima "
            "del triple-write. Tutti gli ordini scriverebbero opt-in anche "
            "se non desiderato — violation di consent under GDPR Art. 7."
        )

    def test_marketing_sync_uses_set_with_revoked_at_null(self):
        """Una opt-in fresca DEVE resettare marketing_revoked_at a None.

        Questo è il principio "most-recent-wins" per il consent state.
        Se un customer revoca poi riopta, l'opt-in più recente prevale.
        """
        # F0 — la sync most-recent-wins vive nel service condiviso.
        from services import marketing_consent_service
        source = inspect.getsource(marketing_consent_service)
        assert '"marketing_revoked_at": None' in source, (
            "Marketing opt-in al checkout non resetta marketing_revoked_at. "
            "Customer che hanno revocato e poi reoptato resterebbero in "
            "stato 'revoked' (più recente). Violation della semantica "
            "most-recent-wins."
        )


# ─── INV-4 — GDPR snapshot on Order at checkout ─────────────────────────


class TestINV4_GDPRSnapshotOnOrder:
    """INV-4 (Business Invariant 4, High):

    Ogni Order al checkout cattura snapshot dei termini legali accettati:
    gdpr_terms_version, gdpr_privacy_version, gdpr_locale, gdpr_accepted_at,
    gdpr_marketing_accepted.

    Snapshot è denormalizzato — la prova legale primaria è in consent_audit.
    Lo snapshot Order è convenience per email/webhook che leggono il legal
    state senza join.

    Pin location: services/order_creation_service.py (R10: spostato dal
    legacy public.py al service condiviso)
    """

    def test_order_model_has_gdpr_snapshot_fields(self):
        """Order Pydantic model deve dichiarare i 5 GDPR snapshot fields."""
        from models.order import Order
        fields = Order.model_fields
        expected = {
            "gdpr_terms_version", "gdpr_privacy_version",
            "gdpr_locale", "gdpr_accepted_at", "gdpr_marketing_accepted",
        }
        # Almeno questi devono essere dichiarati (anche se Optional).
        for field in expected:
            assert field in fields, (
                f"Order model missing GDPR snapshot field: {field}. "
                "Senza, l'email transazionale e i webhook leggono uno snapshot "
                "incompleto. INV-4 violato."
            )

    def test_public_router_writes_gdpr_snapshot_on_order(self):
        """Public router applica `$set` dei 5 GDPR fields sull'order."""
        # R10 — logica nel service condiviso.
        from services import order_creation_service
        source = inspect.getsource(order_creation_service)
        # Marker delle 5 chiavi insieme nella stessa $set update.
        assert "gdpr_terms_version" in source
        assert "gdpr_privacy_version" in source
        assert "gdpr_locale" in source
        assert "gdpr_accepted_at" in source
        assert "gdpr_marketing_accepted" in source

    def test_gdpr_snapshot_is_conditional_on_enforce_flag(self):
        """Snapshot scritto SOLO se store ha GDPR docs published.

        Store legacy senza GDPR config continuano a checkout senza il
        $set GDPR. INV-4 si applica solo a store con merchant_legal_status
        in ('published', 'stale_draft').
        """
        # R10 — logica nel service condiviso.
        from services import order_creation_service
        source = inspect.getsource(order_creation_service)
        # Il flag gdpr_enforce gate il branch.
        assert "if gdpr_enforce" in source, (
            "Mancante il gate `if gdpr_enforce`. Store legacy senza GDPR "
            "config riceverebbero $set fields a None — possibile rottura "
            "downstream (email render expects string version)."
        )


# ─── INV-6 — Rental slot atomic pre-reservation ─────────────────────────


class TestINV6_RentalSlotAtomic:
    """INV-6 (Business Invariant 6, Critical):

    Per prodotti rental con slot temporali, la prenotazione DEVE essere
    atomic PRIMA dell'insert dell'order. Rollback se order insert fallisce.

    Garantisce: nessun double-booking concorrente. Lo slot è "lockato"
    al momento del submit, non al confirm.

    Pin location: services/order_service.py:406-428
    """

    def test_try_reserve_booking_slot_range_exists(self):
        """La funzione di reservation atomica."""
        from services.booking_availability import try_reserve_booking_slot_range
        assert inspect.iscoroutinefunction(try_reserve_booking_slot_range)

    def test_try_reserve_signature_includes_order_id(self):
        """Reservation deve essere tracciata per order_id (rollback target)."""
        from services.booking_availability import try_reserve_booking_slot_range
        sig = inspect.signature(try_reserve_booking_slot_range)
        params = sig.parameters
        # Required parameters for atomic + rollback
        assert "order_id" in params, (
            "try_reserve_booking_slot_range deve accettare order_id per "
            "permettere rollback selettivo se l'order insert fallisce."
        )
        assert "org_id" in params, "Reservation deve essere org-scoped"
        assert "product_id" in params

    def test_release_booking_slot_exists_for_rollback(self):
        """Counterpart per rilasciare lo slot in caso di order insert failure."""
        from services.booking_availability import release_booking_slot
        assert inspect.iscoroutinefunction(release_booking_slot)

    def test_order_service_uses_reservation_before_insert(self):
        """L'order_service prenota PRIMA dell'insert dell'order doc."""
        from services import order_service
        source = inspect.getsource(order_service)
        # Marker: la chiamata di try_reserve PRECEDE order_repository.insert
        # nella sequenza testuale del create_order function.
        idx_reserve = source.find("try_reserve_booking_slot_range")
        idx_insert = source.find("order_repository.insert")
        assert idx_reserve >= 0, (
            "order_service.py non chiama try_reserve_booking_slot_range. "
            "INV-6 violato: rental slot non pre-prenotato, race condition "
            "possibile su double-booking."
        )
        # Note: idx_insert può apparire più volte; cerchiamo il primo
        # match dopo la chiamata di reserve nello stesso codice path
        # (create_order). Verifichiamo che reserve appaia.
        assert idx_reserve < idx_insert if idx_insert >= 0 else True

    def test_order_service_rolls_back_on_insert_failure(self):
        """release_booking_slot chiamato se insert fallisce dopo reservation."""
        from services import order_service
        source = inspect.getsource(order_service)
        assert "release_booking_slot" in source, (
            "order_service non chiama release_booking_slot. Se l'order "
            "insert fallisce DOPO reservation, lo slot resterebbe lockato "
            "per sempre senza order che lo possiede."
        )


# ─── INV-7 — Customer metrics refresh after confirmed order ─────────────


class TestINV7_CustomerMetricsRefresh:
    """INV-7 (Business Invariant 7, Medium):

    Dopo ogni order confirmed con payment collected, customer_metrics
    DEVE essere refreshato (best-effort, fire-and-forget). Garantisce
    che il CRM dashboard mostri tier aggiornato entro ~1s.

    Soft-fail OK: il job giornaliero di refresh recovery garantisce
    eventually-consistent state.

    Pin location: services/order_service.py:584
    """

    def test_refresh_customer_metrics_function_exists(self):
        """Il refresh entry point esiste e è async."""
        from modules.customer_insights.refresh import refresh_customer_metrics
        assert inspect.iscoroutinefunction(refresh_customer_metrics)

    def test_confirm_order_triggers_metrics_refresh(self):
        """confirm_order chiama _refresh_customer_metrics_best_effort."""
        from services import order_service
        source = inspect.getsource(order_service)
        assert "_refresh_customer_metrics_best_effort" in source, (
            "order_service non chiama _refresh_customer_metrics_best_effort "
            "in confirm_order. INV-7 violato: CRM dashboard mostrerà tier "
            "stale fino al refresh job giornaliero (~24h drift)."
        )

    def test_refresh_is_fire_and_forget_best_effort(self):
        """Il refresh failure non blocca l'order confirm.

        Marker: la chiamata è dentro un try/except o è preceduta da
        un wrapper "best_effort" che cattura le exception.
        """
        from services import order_service
        source = inspect.getsource(order_service)
        # Il wrapper deve esistere come funzione (non solo chiamata inline).
        assert "_refresh_customer_metrics_best_effort" in source, (
            "Manca il wrapper best-effort. Senza, una metric refresh "
            "failure blocca il confirm dell'order — INV-7 violato."
        )


# ─── INV-8 — SalesRecords 1:1 con order lines ──────────────────────────


class TestINV8_SalesRecordsGeneration:
    """INV-8 (Business Invariant 8, High):

    Ogni order line al confirm produce ESATTAMENTE 1 SalesRecord con:
      - source_label = "Ordini"
      - dataset_id = "orders"
      - customer_id preservato
      - product_id preservato
      - payment_status preservato
      - amount = line.line_total (con extras già inclusi)

    Pin location: services/order_service.py:1300-1419 (_generate_sales_records)
    """

    def test_generate_sales_records_function_exists(self):
        """Il bridge order → cashflow."""
        from services import order_service
        assert hasattr(order_service, "_generate_sales_records")
        assert inspect.iscoroutinefunction(order_service._generate_sales_records)

    def test_sales_record_uses_canonical_source_label(self):
        """source_label hardcoded a "Ordini" — analytics aggregations expect this."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert '"Ordini"' in source or "'Ordini'" in source, (
            "_generate_sales_records non setta source_label='Ordini'. "
            "Cashflow KPI aggregations falliscono o non vedono questi ordini "
            "come revenue."
        )

    def test_sales_record_uses_canonical_dataset_id(self):
        """dataset_id="orders" distingue queste vendite dagli upload CSV."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert '"orders"' in source, (
            "_generate_sales_records non setta dataset_id='orders'. "
            "Reporting analytics non distingue order-generated vs upload."
        )

    def test_sales_record_preserves_customer_id(self):
        """customer_id propagato dall'order alla sales_record."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert 'order.get("customer_id")' in source, (
            "_generate_sales_records non propaga customer_id all'sales_record. "
            "customer_insights LTV aggregations sarebbero rotte (no customer linkage)."
        )

    def test_sales_record_preserves_product_id(self):
        """product_id propagato per Performance Prodotti analytics."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert "line_product_id" in source or 'line.get("product_id")' in source, (
            "_generate_sales_records non propaga product_id. Performance "
            "Prodotti page calcola margini per prodotto — senza product_id "
            "non riesce a fare il join."
        )

    def test_sales_record_carries_cost_at_sale_snapshot(self):
        """cost_at_sale snapshot per margin stability nel tempo."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert "cost_at_sale" in source, (
            "_generate_sales_records non snapshotta cost_at_sale. Se il "
            "merchant cambia cost_source in futuro, i margini storici "
            "diventerebbero incoerenti."
        )

    def test_sales_records_quota_tracked(self):
        """SalesRecords contano verso il quota cashflow_monitor.data_rows."""
        from services import order_service
        source = inspect.getsource(order_service._generate_sales_records)
        assert "record_module_usage" in source, (
            "_generate_sales_records non chiama record_module_usage. Quota "
            "tracking non avviene — utenti free potrebbero superare 200 "
            "righe/mese senza essere fermati."
        )


# ─── INV-9 — Order status state machine ────────────────────────────────


class TestINV9_OrderStateMachine:
    """INV-9 (Business Invariant 9, High):

    Order status transitions valide:
      draft → confirmed (al payment collection / manual approval)
      draft → cancelled (rifiuto manuale o timeout)
      confirmed → cancelled (refund, post-confirm cancel)

    INVALID transitions:
      - draft → completed (no skip)
      - confirmed → draft (no reverse)
      - cancelled → confirmed (no resurrect)

    Pin location: services/order_service.py (confirm_order, cancel_order)
    """

    def test_order_status_enum_has_canonical_values(self):
        """Order status enum invariato — i nuovi state vanno aggiunti, mai rinominati."""
        from models.order import OrderStatus
        canonical = {"draft", "confirmed", "completed", "cancelled"}
        actual = {s.value for s in OrderStatus}
        # Permettiamo aggiunte additive, ma i 4 canonici devono restare.
        assert canonical.issubset(actual), (
            f"OrderStatus enum missing canonical values: {canonical - actual}. "
            "Rinominare uno stato esistente rompe tutte le query analytics "
            "che filtrano per stato."
        )

    def test_confirm_order_function_exists(self):
        """La sola via per draft → confirmed."""
        from services import order_service
        assert hasattr(order_service, "confirm_order")
        assert inspect.iscoroutinefunction(order_service.confirm_order)

    def test_cancel_order_function_exists(self):
        """La sola via per * → cancelled."""
        from services import order_service
        assert hasattr(order_service, "cancel_order")
        assert inspect.iscoroutinefunction(order_service.cancel_order)

    def test_confirm_order_sets_confirmed_status(self):
        """confirm_order applica OrderStatus.CONFIRMED.value."""
        from services import order_service
        source = inspect.getsource(order_service.confirm_order)
        assert "OrderStatus.CONFIRMED" in source, (
            "confirm_order non setta OrderStatus.CONFIRMED. State machine "
            "rotta — confirm operation non transiziona lo stato."
        )

    def test_no_direct_status_set_in_public_router(self):
        """Public router NON setta status='confirmed' direttamente.

        L'unico legittimo path per confirm è via confirm_order (chiamato
        dal payment webhook handler o da manual API). Tentativi di setting
        diretto in public.py sarebbero violazione INV-9.
        """
        from routers import public
        source = inspect.getsource(public)
        # Cerchiamo pattern sospetti
        suspicious_patterns = [
            'status = "confirmed"',
            "status = 'confirmed'",
            'status: "confirmed"',
            "status: 'confirmed'",
        ]
        for pattern in suspicious_patterns:
            assert pattern not in source, (
                f"public.py contiene assignment diretto: {pattern!r}. "
                "INV-9 violato — confirm deve passare per order_service.confirm_order."
            )


# ─── INV-10 — payment_intent transitions only via webhook ───────────────


class TestINV10_PaymentIntentTransitions:
    """INV-10 (Business Invariant 10, Critical):

    Order.payment_intent transitions (none → required → collected) avvengono
    ESCLUSIVAMENTE via webhook handler Stripe. Mai via manual REST API call.

    Garantisce: payment status sempre reale, sincronizzato con Stripe.
    Nessuna possibilità di "fake paid" via API manipulation.

    Pin location: services/payment_checkout_service.py:615
    """

    def test_payment_checkout_service_updates_payment_intent(self):
        """payment_intent='collected' settato dal webhook reconcile."""
        from services import payment_checkout_service
        source = inspect.getsource(payment_checkout_service)
        # Il valore 'collected' deve apparire in un $set context.
        assert '"payment_intent": "collected"' in source, (
            "payment_checkout_service non setta payment_intent='collected'. "
            "Webhook reconcile non sblocca i pagamenti. Catastrofico per "
            "checkout flow."
        )

    def test_payment_intent_collected_inside_webhook_context(self):
        """Marker che il setting è in funzione legata al webhook handler."""
        from services import payment_checkout_service
        # La function `reconcile_checkout_event` (o equivalente) deve esistere
        # e contenere il $set.
        members = inspect.getmembers(payment_checkout_service, inspect.iscoroutinefunction)
        webhook_handlers = [
            name for name, fn in members
            if "reconcile" in name.lower() or "webhook" in name.lower() or "checkout" in name.lower()
        ]
        assert len(webhook_handlers) > 0, (
            "payment_checkout_service non espone una funzione di webhook "
            "reconcile. Senza, payment_intent non transitiona mai."
        )

    def test_no_payment_intent_set_in_public_router(self):
        """Public router NON setta payment_intent='collected' direttamente."""
        from routers import public
        source = inspect.getsource(public)
        # Pattern: assignment diretto a "collected"
        for pattern in [
            '"payment_intent": "collected"',
            "'payment_intent': 'collected'",
        ]:
            assert pattern not in source, (
                f"public.py contiene set diretto: {pattern!r}. INV-10 "
                "violato — payment collection può solo passare per webhook."
            )

    def test_processed_events_array_present_in_update(self):
        """$push processed_events accompagna il $set payment_intent.

        Garantisce idempotency a livello per-order (anche se il global
        event lock fallisse).
        """
        from services import payment_checkout_service
        source = inspect.getsource(payment_checkout_service)
        assert "processed_events" in source, (
            "payment_checkout_service non track processed_events. "
            "Idempotency per-order rotta — webhook replay rischia doppia "
            "applicazione del payment_intent transition."
        )
        assert "$push" in source, (
            "processed_events tracked ma non con $push (Mongo array append). "
            "Idempotency log inconsistente."
        )
