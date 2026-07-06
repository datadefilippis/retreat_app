"""R2a (2026-07-06) — lingua email timbrata sull'ordine + Passaporto localizzato.

Contratto sotto guardia:
  1. order.locale (lingua UI al checkout) e' la PRIORITA' 1 nella catena
     di risoluzione lingua delle email al compratore.
  2. Un locale invalido sull'ordine cade sulla catena esistente (store).
  3. OrderRequestPayload accetta `locale` (client legacy: opzionale).
  4. request_magic_link aggiorna la preferenza lingua dell'account
     quando il frontend la manda, e l'email OTP parte in quella lingua.
  5. Le email Passaporto (OTP + claim) sono localizzate in 4 lingue.
  6. I cluster pagamenti/dunning, prenotazioni e Passaporto esistono in
     TUTTE e 4 le lingue (prima: solo it/en → _t ripiegava su it).
"""

import os, sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services import order_email_service as oes
from services.email_service import EMAIL_TRANSLATIONS, SUPPORTED_LOCALES


# ── 1+2: catena risoluzione lingua compratore ────────────────────────────


class TestOrderLocalePriority:
    @pytest.mark.asyncio
    async def test_order_locale_wins_over_everything(self):
        """order.locale valido → vince senza toccare account ne' store."""
        store_fallback = AsyncMock(return_value="it")
        with patch.object(oes, "_resolve_store_locale", store_fallback):
            email, locale = await oes._get_customer_email_and_locale(
                {"locale": "de"},
            )
        assert locale == "de"
        store_fallback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_order_locale_falls_through(self):
        """Valore fuori dalle 4 lingue → catena store come prima."""
        with patch.object(oes, "_resolve_store_locale",
                          AsyncMock(return_value="fr")):
            _, locale = await oes._get_customer_email_and_locale(
                {"locale": "xx", "organization_id": "org1"},
            )
        assert locale == "fr"

    @pytest.mark.asyncio
    async def test_missing_order_locale_keeps_legacy_chain(self):
        """Ordini pre-R2a (senza campo) → comportamento identico a prima."""
        with patch.object(oes, "_resolve_store_locale",
                          AsyncMock(return_value=None)):
            _, locale = await oes._get_customer_email_and_locale(
                {"organization_id": "org1"},
            )
        assert locale == "it"


# ── 3: il payload del checkout accetta locale ────────────────────────────


class TestCheckoutPayload:
    def test_payload_accepts_locale(self):
        from routers.public import OrderRequestPayload
        p = OrderRequestPayload(
            slug="demo-store", customer_name="Anna", customer_email="a@b.de",
            items=[{"product_id": "p1", "quantity": 1}], locale="de",
        )
        assert p.locale == "de"

    def test_payload_locale_optional(self):
        """Client legacy senza il campo → None, nessun errore."""
        from routers.public import OrderRequestPayload
        p = OrderRequestPayload(
            slug="demo-store", customer_name="Anna", customer_email="a@b.de",
            items=[{"product_id": "p1", "quantity": 1}],
        )
        assert p.locale is None

    def test_create_order_stamps_only_valid_locales(self):
        """order_service accetta il kwarg e scarta i valori invalidi
        (contratto: doc['locale'] solo se in {it,en,de,fr})."""
        import inspect
        from services.order_service import create_order
        assert "locale" in inspect.signature(create_order).parameters
        src = inspect.getsource(create_order)
        assert '"it", "en", "de", "fr"' in src.replace("'", '"')


# ── 4: la richiesta OTP aggiorna la lingua dell'account ──────────────────


def _fake_platform_db(existing_account):
    """Prepara mock delle collection platform_* su database module."""
    accounts = MagicMock()
    accounts.find_one = AsyncMock(return_value=existing_account)
    accounts.insert_one = AsyncMock()
    accounts.update_one = AsyncMock()
    tokens = MagicMock()
    tokens.insert_one = AsyncMock()
    return accounts, tokens


class TestMagicLinkLanguage:
    @pytest.mark.asyncio
    async def test_language_updates_account_and_email(self):
        from services import platform_account_service as pas
        account = {"id": "pa1", "email": "a@b.de", "name": None,
                   "language": "it", "email_verified": False}
        accounts, tokens = _fake_platform_db(account)
        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(pas, "_send_magic_link_email") as send:
            await pas.request_magic_link("a@b.de", language="de")
        accounts.update_one.assert_awaited_once()
        set_doc = accounts.update_one.await_args.args[1]["$set"]
        assert set_doc == {"language": "de"}
        assert send.call_args.kwargs.get("locale") == "de"

    @pytest.mark.asyncio
    async def test_no_language_keeps_account_preference(self):
        """Client legacy (language=None) → nessun update, email nella
        lingua gia' salvata sull'account."""
        from services import platform_account_service as pas
        account = {"id": "pa1", "email": "a@b.fr", "name": None,
                   "language": "fr", "email_verified": False}
        accounts, tokens = _fake_platform_db(account)
        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(pas, "_send_magic_link_email") as send:
            await pas.request_magic_link("a@b.fr")
        accounts.update_one.assert_not_awaited()
        assert send.call_args.kwargs.get("locale") == "fr"

    @pytest.mark.asyncio
    async def test_invalid_language_ignored(self):
        from services import platform_account_service as pas
        account = {"id": "pa1", "email": "a@b.it", "name": None,
                   "language": "it", "email_verified": False}
        accounts, tokens = _fake_platform_db(account)
        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(pas, "_send_magic_link_email") as send:
            await pas.request_magic_link("a@b.it", language="xx")
        accounts.update_one.assert_not_awaited()
        assert send.call_args.kwargs.get("locale") == "it"


# ── 5: email Passaporto localizzate ──────────────────────────────────────


class TestPassportEmailsLocalized:
    def test_otp_email_in_english(self):
        from services import platform_account_service as pas
        with patch("services.email_service.send_email") as send:
            pas._send_magic_link_email("a@b.com", "tok", "Anna",
                                       code="123456", locale="en")
        _, subject, html = send.call_args.args[:3]
        assert subject == EMAIL_TRANSLATIONS["en"]["passport_login_subject"]
        assert "123456" in html
        assert "Sign in to your account" in html
        assert "Accedi" not in html

    def test_claim_email_in_german(self):
        from services import platform_account_service as pas
        with patch("services.email_service.send_email") as send:
            pas._send_claim_email("a@b.de", "tok", None, locale="de")
        _, subject, html = send.call_args.args[:3]
        assert subject == EMAIL_TRANSLATIONS["de"]["passport_claim_subject"]
        assert "Buchungen verwalten" in html


# ── 6: copertura 4 lingue dei cluster prima solo it/en ───────────────────

R2A_KEYS = [
    # dunning / promemoria pagamenti (compratore + operatore)
    "payment_plan_heading", "payment_plan_paid_row",
    "payment_plan_pending_row", "payment_plan_reminder_note",
    "pay_reminder_subject_t7", "pay_reminder_subject_t0",
    "pay_sollecito_subject", "pay_reminder_body", "pay_sollecito_body",
    "pay_now_cta", "pay_reminder_footer",
    "pay_atrisk_merchant_subject", "pay_atrisk_merchant_body",
    "pay_atrisk_merchant_actions",
    # conferma prenotazione (Onda 16)
    "reservation_confirm_subject", "reservation_confirm_body",
    "reservation_keep_note", "reservation_code_label",
    "reservation_view_cta",
    # Passaporto (OTP + claim)
    "passport_login_subject", "passport_code_intro", "passport_code_hint",
    "passport_link_intro", "passport_login_cta", "passport_login_ignore",
    "passport_claim_subject", "passport_claim_body", "passport_claim_cta",
    "passport_claim_footer",
]


class TestFourLanguageCoverage:
    @pytest.mark.parametrize("key", R2A_KEYS)
    def test_key_present_in_all_locales(self, key):
        for loc in SUPPORTED_LOCALES:
            assert key in EMAIL_TRANSLATIONS[loc], (
                f"chiave email '{key}' mancante nel blocco '{loc}' — "
                "R2a garantisce 4 lingue su dunning/prenotazioni/Passaporto"
            )

    def test_at_risk_no_longer_hardcoded(self):
        """Il sollecito at-risk all'operatore usa il resolver, non 'it'."""
        import inspect
        from services.payment_email_service import send_at_risk_to_operator
        src = inspect.getsource(send_at_risk_to_operator)
        assert 'locale = "it"' not in src
        assert "_resolve_merchant_locale" in src

    def test_reservation_confirmation_no_longer_hardcoded(self):
        import inspect
        from services.email_service import send_reservation_confirmation_email
        src = inspect.getsource(send_reservation_confirmation_email)
        assert "_get_customer_email_and_locale" in src
        assert "reservation_confirm_subject" in src
