"""SN3 (8/10/2026, piano Aurya Sound §4.1 punto 5 e §4.4) — IL TUO SPAZIO.

Con l'account: «riprendi da dove eri», gli ascolti recenti e le preferite
in una sezione della casa, «I tuoi» nella barra; il player salva il punto
ogni quindici secondi e spegne «riprendi» alla fine. Lato founder la
dashboard «Ascolti» per traccia in Crea. Senza account non si salva nulla.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestServer:
    def test_endpoint_ascolto(self):
        src = (BACKEND / "routers" / "platform_accounts.py").read_text()
        corpo = src.split('@router.post("/me/sound/ascolto")')[1].split("\nclass ")[0]
        # al via entra nei recenti (senza doppi, venti al massimo)
        assert "recenti = [slug, *recenti][:20]" in corpo
        # alla fine «riprendi» si spegne solo se era di questa traccia
        assert 'if riprendi and riprendi.get("slug") == slug:' in corpo
        assert '"secondo": max(0, int(body.secondo))' in corpo


class TestPlayer:
    def test_salva_il_punto_con_account(self):
        src = (FQ / "PublicFrequencyPage.js").read_text()
        assert "const haAccount = !!localStorage.getItem('platform_token');" in src
        assert "platformApi.post('/platform/me/sound/ascolto', { slug, ...dati })" in src
        assert "if (evento === 'avvio') segnaSpazio({ secondo: 0 });" in src
        assert "if (evento === 'fine') segnaSpazio({ fine: true });" in src
        assert "elapsed - ultimoSalvatoRef.current >= 15" in src
        # ?t= dal «riprendi» della casa: si parte da li', mai dagli ultimi secondi
        assert "if (t > 5 && t < d - 5) setElapsed(t);" in src


class TestCasa:
    def test_sezione_e_barra(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "platformApi.get('/platform/me')" in src and "sound_riprendi" in src and "sound_recenti" in src
        assert 'id="tuo-spazio"' in src and 'data-testid="casa-riprendi"' in src and 'data-testid="casa-recenti"' in src
        assert "?da=riprendi&t=${riprendi.secondo}" in src
        # la sezione vive solo con l'account e solo se ha qualcosa da dire
        assert "hasAccount && (riprendi || recenti.length > 0 || preferite.length > 0)" in src
        assert "vaiA('tuo-spazio') : setHeartAsk(true)" in src and ">I tuoi</button>" in src
        # i recenti sono solo quelli ancora in catalogo
        assert "(spazio.recenti || []).map((s) => perSlug[s]).filter(Boolean)" in src


class TestDashboardAscolti:
    def test_in_crea(self):
        src = (FQ / "CasaCampi.jsx").read_text()
        assert "export function AscoltiTraccia({ traccia })" in src
        assert "frequenciesAPI.ascolti(traccia.id)" in src
        assert "{pubblica && <AscoltiTraccia traccia={traccia} />}" in src
        for k in ("casa", "playlist", "email", "riprendi", "recenti"):
            assert f"{k}:" in src.split("const PROVENIENZE")[1].split("};")[0], k
