"""MR7 (8/10/2026 sera, founder) — I PERCORSI: solidi, senza perdere l'utente.

docs/ANALISI_PERCORSI_MEDITAZIONI_2026-10-08.md. La soglia solo se il server
dice «locked» (un token scaduto non chiude la casa a chi e' nel Cerchio),
«Crea» solo a chi puo' comporre, «Il suono» dalla casa apre un foglio senza
uscire, il «torna» del corso rispetta da dove si viene.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestNonChiedereDueVolte:
    def test_la_soglia_solo_se_locked(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        # con l'account scaduto (401) si riprova con la prova del Cerchio
        assert "if (via === conAccount && (st === 401 || st === 403) && prova()) { via = conProva; return via(before); }" in src
        # con l'account si manda anche la prova: il server la legge per prima
        assert "...(prova() ? { headers: { 'X-Fqz-Unlock': prova() } } : {})," in src
        # la soglia solo su 403/401 dal server; la rete non chiede l'iscrizione
        assert "if (st === 403 || st === 401) {" in src
        assert "setErrore('Non riesco a raggiungere le meditazioni in questo momento.');" in src
        assert 'data-testid="casa-errore"' in src and 'onClick={carica}>Riprova</button>' in src

    def test_le_email_aprono_la_casa(self):
        # la prova nell'indirizzo si salva PRIMA del primo render (FL2), per ogni pagina
        idx = (FRONTEND / "index.js").read_text()
        assert "raccogliProvaDaUrl();" in idx
        sub = (BACKEND / "routers" / "subscribers.py").read_text()
        assert 'def _con_prova(percorso: str, token: str) -> str:' in sub


class TestCreaSoloAChiPuo:
    def test_passerella(self):
        src = (FQ / "SoundTopbar.jsx").read_text()
        assert "puoComporre = cappelliAddosso().operatore && localStorage.getItem('aurya_sound_crea') === '1'" in src
        assert "(puoComporre ? [...CASA_PASSERELLA, CASA_VOCE_CREA] : CASA_PASSERELLA)" in src
        # il portiere vero resta sul server
        assert "Depends(require_sound_crea)" in (BACKEND / "routers" / "frequencies.py").read_text()
        # e il menu dell'omino non ha un link diretto a Crea
        assert "/sound/crea" not in (FRONTEND / "lib" / "cappelli.js").read_text()


class TestNonPerdersi:
    def test_il_suono_dalla_casa_e_un_foglio(self):
        src = (FQ / "SoundTopbar.jsx").read_text()
        assert "const inCasa = SOUND_CASA_NUOVA && qui === '/meditazioni';" in src
        assert 'data-testid="fqz-nav-suono"' in src and 'data-testid="fqz-foglio-suono"' in src
        for porta in ("'/sound/esplora'", "'/sound/impara'", "'/sound/lab'"):
            assert porta in src, porta
        assert "La pagina di Aurya Sound →" in src

    def test_il_corso_torna_da_dove_si_viene(self):
        casa = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "<Link to={`${c.url}?da=meditazioni`} className=\"mcard tono-oro\"" in casa
        corso = (FRONTEND / "features" / "storefront" / "CorsoLandingPage.js").read_text()
        assert "const daMeditazioni = cercaParams.get('da') === 'meditazioni';" in corso
        assert "<Link to={daMeditazioni ? '/meditazioni' : `/o/${orgSlug}`}" in corso
        assert "{daMeditazioni ? 'Le meditazioni' : (org?.name || 'Il profilo')}" in corso
