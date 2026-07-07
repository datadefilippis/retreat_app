"""Ciclo SA — System Admin 360° (docs/SYSTEM_ADMIN_360_PIANO_2026-07-07.md).

SA1: il fee ledger è la fonte di verità dei guadagni piattaforma —
ogni incasso ONLINE timbra transato + percentuale + fee al webhook;
il manuale non scrive mai; i rimborsi scrivono righe negative.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


class TestFeeLedgerSa1:
    CHECKOUT_SRC = (BACKEND_DIR / "services" / "payment_checkout_service.py").read_text()

    def test_fee_math_half_up(self):
        """La fee si arrotonda commercialmente (HALF_UP), mai floor."""
        from services.platform_fee_ledger import compute_fee_minor
        assert compute_fee_minor(80000, 5.0) == 4000   # 800€ → 40€
        assert compute_fee_minor(3333, 2.0) == 67      # 33,33€ → 0,67€ (66.66 → 67)
        assert compute_fee_minor(24000, 5.0) == 1200
        assert compute_fee_minor(0, 5.0) == 0

    def test_webhook_stamps_ledger_on_both_paths(self):
        """Prima riscossione E saldi/rate su ordine gia' collected:
        entrambe le vie del reconcile scrivono il ledger."""
        assert self.CHECKOUT_SRC.count("record_from_session") >= 2

    def test_session_metadata_carries_fee_percent(self):
        """La percentuale viaggia con la session (checkout principale
        e session per-riga): al webhook si timbra il valore VERO
        della creazione, non quello corrente dell'org."""
        assert self.CHECKOUT_SRC.count(
            '"application_fee_percent": str(application_fee_percent)') == 2

    def test_refund_writes_negative_entry(self):
        src = (BACKEND_DIR / "services" / "payment_refund_service.py").read_text()
        assert "record_platform_fee" in src
        assert 'kind="refund"' in src
        assert '-int(item["amount_minor"])' in src

    def test_ledger_never_blocks_payment_flow(self):
        """Un errore di scrittura ledger si logga e NON propaga: il
        pagamento del cliente viene prima della contabilita' interna."""
        import inspect
        from services import platform_fee_ledger as pfl
        src = inspect.getsource(pfl.record_platform_fee)
        assert "except Exception" in src
        assert "raise" not in src.split("except Exception")[1]

    def test_manual_flows_never_write_ledger(self):
        """mark-paid manuale e pagina Dati non generano fee: nessun
        riferimento al ledger fuori dai flussi Stripe."""
        for rel in ("services/order_service.py",
                    "routers/cashflow.py"):
            src = (BACKEND_DIR / Path(rel)).read_text()
            assert "platform_fee_ledger" not in src, rel


class TestSalesChannelAlwaysStamped:
    """SA1 — ogni ordine nasce con un canale: le statistiche per
    canale (SA2/SA4) non devono avere buchi come i 23 ordini pre-GT1."""

    def test_create_order_stamps_channel_from_source(self):
        import inspect
        from services import order_service as osvc
        src = inspect.getsource(osvc.create_order)
        assert '"sales_channel"' in src
        assert '"manual": "manual"' in src and '"pos": "pos"' in src

    def test_storefront_defaults_to_store(self):
        """Payload senza channel esplicito (vecchi embed) → 'store',
        mai vuoto."""
        src = (BACKEND_DIR / "services" / "order_creation_service.py").read_text()
        assert 'channel = "store"' in src

    def test_backfill_script_exists_and_is_idempotent(self):
        src = (BACKEND_DIR / "scripts" / "backfill_fee_ledger.py").read_text()
        assert "sales_channel" in src
        assert "entry_key" in src          # upsert idempotente
        assert "--dry-run" in src


class TestPlatformOverviewSa2:
    """SA2 — /admin/platform: panoramica del business, 100%
    system-admin, solo dati timbrati."""

    ROUTER_SRC = (BACKEND_DIR / "routers" / "admin_platform.py").read_text()

    def test_all_endpoints_require_system_admin(self):
        """Ogni endpoint del router porta la guardia — nessuna route
        di piattaforma leggibile da un operatore."""
        routes = self.ROUTER_SRC.count("@router.get")
        guards = self.ROUTER_SRC.count("require_system_admin")
        assert routes >= 2
        assert guards >= routes + 1  # import + una per endpoint

    def test_router_registered_in_server(self):
        src = (BACKEND_DIR / "server.py").read_text()
        assert "admin_platform" in src

    def test_overview_reads_only_stamped_sources(self):
        """Fee dal ledger SA1, GMV dagli ordini confermati, directory
        dalle condizioni GT1b — niente stime parallele."""
        insights = (BACKEND_DIR / "services" / "platform_insights.py").read_text()
        assert "platform_fee_ledger" in insights
        assert '"confirmed", "completed"' in insights
        assert '"status": "active", "runtime_status": "ready"' in insights

    def test_directory_snapshot_reason_codes_stable(self):
        """I reason code sono il contratto col frontend (SA3)."""
        insights = (BACKEND_DIR / "services" / "platform_insights.py").read_text()
        for code in ("stripe_not_ready", "no_public_page",
                     "no_direct_retreats"):
            assert f'"{code}"' in insights

    def test_admin_page_has_overview_tab(self):
        base = BACKEND_DIR.parent / "frontend" / "src" / "features" / "admin"
        page = (base / "AdminPage.js").read_text()
        assert "PlatformOverviewTab" in page
        assert 'defaultValue="overview"' in page
        tab = (base / "PlatformOverviewTab.js").read_text()
        assert "/admin/platform/overview" in tab
        # riuso kit grafico condiviso, non recharts diretto
        assert "components/charts" in tab


class TestDirectoryTabSa3:
    """SA3 — la plancia directory: una riga per org, motivi del gate,
    polso degli ordini che il calendario porta."""

    def test_snapshot_includes_marketplace_pulse(self):
        insights = (BACKEND_DIR / "services" / "platform_insights.py").read_text()
        assert '"orders_marketplace_30d"' in insights
        assert '"orders_total_30d"' in insights

    def test_directory_tab_wired_with_reason_labels(self):
        base = BACKEND_DIR.parent / "frontend" / "src" / "features" / "admin"
        page = (base / "AdminPage.js").read_text()
        assert "DirectoryAdminTab" in page
        tab = (base / "DirectoryAdminTab.js").read_text()
        assert "/admin/platform/directory" in tab
        # ogni reason code del backend ha la sua etichetta
        for code in ("stripe_not_ready", "no_public_page",
                     "no_direct_retreats"):
            assert code in tab, f"etichetta mancante per {code}"
