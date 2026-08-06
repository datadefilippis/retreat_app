"""TA — ticketing per eventi E servizi + account utente, senza buchi.

Dispositivo sotto guardia (ciclo TA, 6 ago 2026, dall'audit
ticketing/account):
  TA1 — alla conferma l'ordine viene idratato con email/telefono dal
        CRM (senza, ticket e prenotazioni nascevano con holder muto e
        le email individuali venivano saltate in silenzio); anche gli
        ordini manuali agganciano il platform account.
  TA2 — i servizi sono cittadini: link /b/ nel Passaporto, chiusura
        appuntamento (svolta / non presentato) esposta e raggiungibile.
  TA3 — servizio con inizio ma senza fine: la fine si deriva dalla
        durata del prodotto, mai piu' appuntamenti fantasma.
  TA4 — la success page consegna i pass appena l'ordine e' confermato.
  TA5 — account: password impostabile dall'hub, GDPR con superficie,
        CTA attiva-account su ogni superficie di acquisto.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


def _src(rel: str) -> str:
    return (BACKEND_DIR / rel).read_text()


def _fsrc(rel: str) -> str:
    return (FRONTEND_SRC / rel).read_text()


class TestTa1ContattiVeri:
    def test_confirm_hydrates_customer_contact(self):
        src = _src("services/order_service.py")
        assert "_hydrate_customer_contact" in src
        confirm = src.split("async def confirm_order")[1].split("\nasync def ")[0]
        assert "_hydrate_customer_contact(org_id, order)" in confirm, \
            "senza idratazione i ticket nascono con holder_email vuoto"
        i_hyd = confirm.index("_hydrate_customer_contact")
        i_tk = confirm.index("issue_tickets_for_order")
        assert i_hyd < i_tk, "l'idratazione deve precedere l'emissione"

    def test_manual_orders_link_platform_account(self):
        src = _src("services/order_service.py")
        confirm = src.split("async def confirm_order")[1].split("\nasync def ")[0]
        assert "link_order_to_platform_account" in confirm, \
            "un cliente inserito a mano non deve restare fuori da /account"


class TestTa2ServiziCittadini:
    def test_passport_exposes_booking_links(self):
        src = _src("routers/platform_accounts.py")
        assert "issued_bookings_collection" in src
        assert '"bookings": bookings_by_order' in src

    def test_account_page_links_booking_landing(self):
        src = _fsrc("features/account/AccountPage.js")
        assert "/b/${bk.access_token}" in src

    def test_booking_close_endpoints_exposed(self):
        src = _src("routers/issued_bookings.py")
        assert '/complete"' in src.replace("'", '"')
        assert '/no-show"' in src.replace("'", '"')

    def test_calendar_has_close_buttons(self):
        src = _fsrc("features/calendar/CalendarPage.js")
        assert "Segna svolta" in src
        assert "Non si è presentato" in src
        assert "completeBooking" in _fsrc("api/calendar.js")


class TestTa3FineDerivata:
    def test_derivation_runs_before_calendar_sync(self):
        src = _src("services/order_service.py")
        assert "async def _derive_service_end_times" in src
        confirm = src.split("async def confirm_order")[1].split("\nasync def ")[0]
        i_der = confirm.index("_derive_service_end_times")
        i_cal = confirm.index("_sync_calendar_blocks")
        assert i_der < i_cal, \
            "la fine mancante va derivata PRIMA del blocco calendario"

    def test_duration_hierarchy_matches_slot_generator(self):
        src = _src("services/order_service.py")
        deriv = src.split("async def _derive_service_end_times")[1].split(
            "\nasync def ")[0]
        assert "duration_minutes" in deriv and "slot_duration_minutes" in deriv


class TestTa4SuccessConsegna:
    def test_public_status_carries_passes_only_when_confirmed(self):
        src = _src("routers/public.py")
        chunk = src.split("async def get_public_order_status")[1].split(
            "\nasync def ")[0]
        assert '("confirmed", "completed")' in chunk, \
            "i pass escono SOLO a ordine confermato"
        assert "issued_tickets_collection" in chunk
        assert "issued_bookings_collection" in chunk

    def test_success_page_renders_passes(self):
        src = _fsrc("features/storefront/CheckoutResultPage.js")
        assert "status.passes" in src
        assert "/t/${p.access_token}" in src and "/b/${p.access_token}" in src


class TestTa5Account:
    def test_password_endpoint_exists(self):
        src = _src("routers/platform_accounts.py")
        assert '"/me/password"' in src.replace("'", '"')
        assert "validate_password_strength" in src
        assert "has_password" in src, "la UI deve sapere se chiedere l'attuale"

    def test_password_change_requires_current_when_set(self):
        src = _src("routers/platform_accounts.py")
        chunk = src.split("async def set_my_password")[1].split("\nasync def ")[0]
        assert 'account.get("password_hash")' in chunk
        assert "verify_password" in chunk

    def test_account_page_has_settings_section(self):
        src = _fsrc("features/account/AccountPage.js")
        assert 'data-testid="account-settings"' in src
        assert "/platform/me/password" in src
        assert "/platform/me/export" in src
        assert "delete('/platform/me'" in src
        assert "/platform/auth/logout-all" in src

    def test_activate_cta_on_every_surface(self):
        src = _fsrc("features/storefront/hooks/useCheckoutForm.js")
        chunk = src.split("const handleSubmit")[1][:600]
        assert "mktp_email" in chunk
        assert "mktpCheckout &&" not in chunk, \
            "l'email per la CTA account va salvata su OGNI superficie"

    def test_email_cta_points_to_reachable_page(self):
        src = _src("services/order_email_service.py")
        assert 'f"/account/orders/{order_id}"' not in src, \
            "quella rotta redirige: la CTA deve puntare a /account"
