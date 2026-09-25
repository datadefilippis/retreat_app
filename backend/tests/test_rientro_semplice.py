"""25/9/2026 — rientrare e' semplice (punti 1, 3, 4, 5 decisi dal founder
dopo il doppio account di Marilisa; il 2, link magico, e' rinviato).

  1. striscia «Ciao, sei dentro, passo N di 3 → Continua» sulle pagine
     pubbliche per chi ha il cappello operatore;
  3. l'email del giorno zero dice come si rientra (aurya.life/spazio,
     password dimenticata, niente nuova registrazione);
  4. «Hai già un account? Accedi» in CIMA al modulo della landing;
  5. /spazio: dentro → gestionale, fuori → accesso; registrata nel
     registro rotte e in nginx (l'ignoto fa 404).
"""
from pathlib import Path
import json

RADICE = Path(__file__).resolve().parents[2]
FE = RADICE / "frontend" / "src"
BACKEND = RADICE / "backend"


class TestStriscia:
    def test_esiste_e_sta_nel_guscio(self):
        src = (FE / "components" / "StrisciaBentornato.js").read_text(encoding="utf-8")
        assert 'data-testid="striscia-bentornato"' in src and 'data-testid="striscia-bentornato-cta"' in src
        assert "onboarding-status" in src and "if (!user || user.role !== 'admin') return null;" in src
        # i tre passi seguono la stessa logica della striscia del gestionale
        assert "if (!s.profile_completed) return { passo: 1, dest: '/public-profile' };" in src
        assert "if (!s.listino_filled) return { passo: 2, dest: '/listino' };" in src
        shell = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text(encoding="utf-8")
        assert "{hasOperatorToken && <StrisciaBentornato />}" in shell


class TestEmailGiornoZero:
    def test_dice_come_si_rientra(self):
        src = (BACKEND / "services" / "email_sequenze.py").read_text(encoding="utf-8")
        blocco = src[src.index("def benvenuto_operatore("):src.index("def op_np5(")]
        assert "/spazio" in blocco and "Password\n            dimenticata" in blocco.replace("«", "").replace("»", "") or "dimenticata" in blocco
        assert "Non serve registrarsi" in blocco


class TestLanding:
    def test_accedi_in_cima(self):
        src = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text(encoding="utf-8")
        i_form = src.index('data-testid="ol-inline-signup"')
        i_top = src.index('data-testid="ol-hai-account"')
        i_bottom = src.index("opPro.haveAccount", i_top + 10)
        assert i_form < i_top < i_bottom


class TestSpazio:
    def test_rotta_registro_e_nginx(self):
        app = (FE / "App.js").read_text(encoding="utf-8")
        assert '<Route path="/spazio" element={<SpazioRedirect />} />' in app
        red = (FE / "components" / "SpazioRedirect.js").read_text(encoding="utf-8")
        assert "isAuthenticated ? '/dashboard' : '/accedi?next=%2Fdashboard'" in red
        reg = json.loads((BACKEND / "config" / "rotte.json").read_text(encoding="utf-8"))
        assert "spazio" in reg["servizio"]
        ngx = (RADICE / "deploy" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        assert "|spazio|" in ngx
