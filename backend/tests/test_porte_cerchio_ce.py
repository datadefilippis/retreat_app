"""
Lotto E1–E4 · Porte nuove per il Cerchio (24/9/2026) — le guardie.

docs/PIANO_ESECUZIONE_ADMIN_CERCHIO_2026-09-24.md (Lotto E) e
docs/ANALISI_SYSTEM_ADMIN_2026-09-24.md §6.3: il cliente e' cliente
dell'OPERATORE; il Cerchio e' marketing di un altro titolare, quindi
consenso a parte, mai preselezionato, mai unito alla casella
`gdpr_marketing_accepted`.

  E0 estrazione: `iscrivi(payload, request)` col corpo della route,
     `subscribe` involucro sottile con i suoi decoratori; i letterali
     che le altre guardie leggono restano al loro posto.
  E1 checkout: `cerchio_optin` facoltativo e False; casella separata,
     non preselezionata, testo corrente; iscrizione best-effort con
     fonte «checkout».
  E2 account cliente: casella non preselezionata col testo corrente,
     versione dichiarata su entrambe le strade.
  E3 UNA riga nelle due email (ordine, codice recensione) col link
     firmato; rotta /entra/{token} (consenso + verifica + 302 interno);
     niente riga a chi e' gia' dentro.
  E4 pagina grazie: casella + bottone, fonte «pagina-grazie», nascosto
     se spuntato al checkout.
  Tassonomia: canale «commercio» con le quattro superfici.
"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND.parent / "frontend" / "src"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

SUBS = (BACKEND / "routers" / "subscribers.py").read_text()
OCS = (BACKEND / "services" / "order_creation_service.py").read_text()
PUBLIC = (BACKEND / "routers" / "public.py").read_text()
ORDER_EMAIL = (BACKEND / "services" / "order_email_service.py").read_text()
REVIEW = (BACKEND / "services" / "review_service.py").read_text()
PORTE = (BACKEND / "services" / "porte_cerchio.py").read_text()
ACCOUNTS = (BACKEND / "routers" / "platform_accounts.py").read_text()

CHECKOUT_FORM = (FRONTEND_SRC / "features" / "storefront" / "components" / "checkout" / "CheckoutForm.jsx").read_text()
HOOK = (FRONTEND_SRC / "features" / "storefront" / "hooks" / "useCheckoutForm.js").read_text()
GRAZIE = (FRONTEND_SRC / "features" / "storefront" / "components" / "checkout" / "GrazieCerchio.jsx").read_text()
RESULT = (FRONTEND_SRC / "features" / "storefront" / "CheckoutResultPage.js").read_text()
LOGIN = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()


def _corpo(src: str, inizio: str, fine: str = "\n\n\n") -> str:
    return src.split(inizio, 1)[1].split(fine, 1)[0]


class TestE0Estrazione:
    def test_iscrivi_esiste_e_la_route_e_un_involucro(self):
        assert "async def iscrivi(payload: SubscribePayload, request: Request" in SUBS
        route = _corpo(SUBS, '@router.post("/public/newsletter/subscribe"', "\n\n\ndef ")
        assert "@limiter.limit" in route, "la route ha perso il rate limit"
        assert "return await iscrivi(payload, request)" in route
        assert "aurya_subscribers" not in route, "la route deve restare sottile"

    def test_il_corpo_e_intatto(self):
        corpo = _corpo(SUBS, "async def iscrivi(", "\n\n\ndef _provenienza_da_payload")
        for atteso in ("status_code=503",
                       "inviato = await invia_subito_se_singolo(email) if singolo_optin() else None",
                       "if not inviato:", "_send_confirm_email", "_send_access_email(",   # 24/9 sera: la conferma parte via to_thread
                       "if not payload.unlock_flow:", "_audit_consenso_subscribe("):
            assert atteso in corpo, atteso

    def test_gia_verificato_salta_solo_le_email(self):
        corpo = _corpo(SUBS, "async def iscrivi(", "\n\n\ndef _provenienza_da_payload")
        assert "gia_verificato: bool = False" in corpo
        i_audit = corpo.index("await _audit_consenso_subscribe(email, consenso, payload.language)\n    if gia_verificato")
        assert i_audit < corpo.index("invia_subito_se_singolo(email)"), \
            "il salto deve venire DOPO il salvataggio e l'audit, PRIMA delle email"

    def test_richiesta_sintetica(self):
        from core.rate_limiting import get_real_ip
        from routers.subscribers import richiesta_sintetica
        r = richiesta_sintetica("10.1.2.3", "UA di prova")
        assert get_real_ip(r) == "10.1.2.3" and r.headers.get("user-agent") == "UA di prova"
        r2 = richiesta_sintetica(None, None)
        assert get_real_ip(r2) and r2.headers.get("user-agent") is None


class TestE1Checkout:
    def test_campo_facoltativo_e_falso(self):
        from routers.public import OrderRequestPayload
        campo = OrderRequestPayload.model_fields["cerchio_optin"]
        assert campo.default is False and not campo.is_required()

    def test_iscrizione_best_effort_con_fonte_checkout(self):
        blocco = _corpo(OCS, "Lotto E1 (24/9/2026)", "# ── AP-L Legal a due livelli")
        assert 'getattr(body, "cerchio_optin", False)' in blocco
        assert "iscrivi(SubscribePayload(" in blocco and 'source="checkout"' in blocco
        assert "consenso_versione=VERSIONE_CORRENTE" in blocco and "unlock_flow=True" in blocco
        assert "richiesta_sintetica(client_ip, user_agent)" in blocco
        assert "try:" in blocco and "except Exception" in blocco, "deve essere best effort"
        assert "raise" not in blocco, "l'ordine non fallisce mai per la Lettera"

    def test_non_unita_alla_casella_dell_operatore(self):
        # la casella dell'operatore resta com'era: la sua logica non legge cerchio_optin
        cg5 = _corpo(OCS, "Wave GDPR-Commerce CG-5 (2026-05-19) ──", "Lotto E1 (24/9/2026)")
        assert "cerchio_optin" not in cg5
        assert '"gdpr_marketing_accepted": bool(body.gdpr_marketing_accepted)' in cg5

    def test_casella_separata_non_preselezionata(self):
        assert 'data-testid="checkout-cerchio-optin"' in CHECKOUT_FORM
        assert "checked={cerchioOptin}" in CHECKOUT_FORM
        assert "useState(false)" in HOOK.split("const [cerchioOptin")[1][:60], \
            "la casella del Cerchio nasce spuntata (GDPR)"
        assert "payload.cerchio_optin = !!cerchioOptin" in HOOK
        # due caselle, non una: quella dell'operatore resta
        assert "checked={gdprMarketingAccepted}" in CHECKOUT_FORM
        assert "payload.gdpr_marketing_accepted = !!gdprMarketingAccepted" in HOOK

    def test_testo_corrente_e_link_privacy(self):
        blocco = CHECKOUT_FORM.split('data-testid="checkout-cerchio-optin"')[1][:700]
        assert "{testoConsenso().testo}" in blocco and 'href="/privacy"' in blocco
        assert "from '../../../../lib/testiConsenso'" in CHECKOUT_FORM
        # la pagina grazie sa che la casella e' gia' stata spuntata
        assert "sessionStorage.setItem('storefront:cerchio_optin'" in HOOK


class TestE2AccountCliente:
    def test_casella_non_preselezionata_col_testo_corrente(self):
        assert "useState(false)" in LOGIN.split("const [wantsLetter")[1][:60]
        blocco = LOGIN.split('data-testid="signup-letter"')[1][:300]
        assert "{testoConsenso().testo}" in blocco
        assert "from '../../lib/testiConsenso'" in LOGIN

    def test_versione_dichiarata_su_entrambe_le_strade(self):
        assert LOGIN.count("consenso_versione: VERSIONE_CORRENTE") >= 3, \
            "magic link, signup con password e signup_pro devono dichiarare la versione"
        assert ACCOUNTS.count("consenso_versione: Optional[str]") == 2, \
            "MagicLinkRequest e PasswordSignup accettano la versione"
        assert ACCOUNTS.count("body.language, body.consenso_versione)") == 2
        fn = _corpo(ACCOUNTS, "async def _subscribe_to_letter", "\n@router")
        assert "consenso_versione=consenso_versione or None" in fn


class TestE3EmailERotta:
    def test_una_riga_sola_nelle_email_ordine(self):
        for fn in ("async def notify_customer_order_received(",
                   "async def notify_customer_order_confirmed("):
            corpo = _corpo(ORDER_EMAIL, fn)
            assert corpo.count('riga_cerchio_html(email, "email-ordine", locale)') == 1, fn
            assert corpo.count("{riga_cerchio}") == 1, fn

    def test_una_riga_sola_nell_email_recensione(self):
        richiesta = _corpo(REVIEW, "async def request_review_otp(")
        assert 'riga_cerchio_html(email_n, "email-recensione", locale)' in richiesta
        assert "_send_review_otp_email(email_n, code, org_slug, locale, riga_cerchio)" in richiesta
        template = _corpo(REVIEW, "def _send_review_otp_email(")
        assert template.count("{riga_cerchio}") == 1

    def test_il_testo_della_riga(self):
        from services.porte_cerchio import TESTO_RIGA
        assert TESTO_RIGA == "Vuoi la Lettera del Cerchio di Aurya (meditazioni, guide, ritiri)? Un clic:"

    def test_link_firmato_verso_la_rotta_entra(self):
        from core.subscriber_token import decode_subscriber_token
        from services.porte_cerchio import link_entra
        url = link_entra("Chi@Esempio.it", "email-recensione")
        assert "/api/public/newsletter/entra/" in url and url.endswith("?da=email-recensione")
        token = url.split("/entra/")[1].split("?")[0]
        assert decode_subscriber_token(token)["email"] == "chi@esempio.it"
        assert link_entra("a@b.it", "boh").endswith("?da=email-ordine")

    def test_riga_vuota_fuori_dall_italiano(self):
        from services.porte_cerchio import riga_cerchio_html
        assert asyncio.run(riga_cerchio_html("a@b.it", "email-ordine", "en")) == ""
        assert asyncio.run(riga_cerchio_html("", "email-ordine", "it")) == ""

    def test_la_rotta_entra(self):
        rotta = _corpo(SUBS, '@router.get("/public/newsletter/entra/{token}")', "\n\n\nclass ")
        assert "@limiter.limit" in rotta
        assert "gia_verificato=True" in rotta and 'segna_verificato(email, "clic", "entra")' in rotta
        assert "consent=True" in rotta and "consenso_versione=VERSIONE_CORRENTE" in rotta
        assert "unlock_flow=True" in rotta, "il gia' confermato non deve ricevere il magic link"
        assert "percorso_interno(to)" in rotta, "mai un open redirect"
        assert "status_code=302" in rotta
        assert "fonte = da if da in SUPERFICI_EMAIL" in rotta

    def test_token_rotto_non_iscrive(self):
        from routers.subscribers import entra_con_un_clic, richiesta_sintetica
        r = richiesta_sintetica("127.0.0.1", "test")
        r.scope["path"] = "/api/public/newsletter/entra/x"
        risposta = asyncio.run(entra_con_un_clic(r, "non-un-token", to="/x", da="email-ordine"))
        assert risposta.status_code == 302 and risposta.headers["location"].endswith("/newsletter")


class TestE4PaginaGrazie:
    def test_componente(self):
        assert 'data-testid="grazie-cerchio"' in GRAZIE
        assert "useState(false)" in GRAZIE.split("const [consenso")[1][:40], "casella preselezionata"
        assert "iscriviESblocca(" in GRAZIE and "source = 'pagina-grazie'" in GRAZIE
        assert "{testoConsenso().testo}" in GRAZIE
        assert "sessionStorage.getItem('storefront:cerchio_optin') === '1'" in GRAZIE

    def test_montato_nella_pagina_grazie(self):
        assert "import GrazieCerchio from './components/checkout/GrazieCerchio'" in RESULT
        assert "<GrazieCerchio" in RESULT


class TestTassonomia:
    def test_canale_commercio(self):
        from services.provenienza import ETICHETTE, TASSONOMIA, canali_per_admin, classifica
        assert TASSONOMIA["commercio"] == ("checkout", "pagina-grazie", "email-ordine", "email-recensione")
        for s in ("commercio",) + TASSONOMIA["commercio"]:
            assert s in ETICHETTE, s
            if s != "commercio":
                assert classifica(s) == {"canale": "commercio", "superficie": s,
                                         "dettaglio": None, "porta": None}
        assert "commercio" in [c["canale"] for c in canali_per_admin()]
        # le voci di prima non si toccano
        assert TASSONOMIA["sito"] == ("cerca-ritiro", "home", "landing-cerchio", "esperienze")
        assert classifica("account_signup")["canale"] == "account"
