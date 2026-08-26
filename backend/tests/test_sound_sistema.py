"""Aurya Sound — il sistema intero, onde L1-L4 (26/8/2026, sera).

Le decisioni di docs/AURYA_SOUND_SISTEMA_2026-08.md sotto guardia:
Crea invisibile a chi non ha il privilegio (la concessione resta al
system admin, invariata); l'invito alla Lettera a fine esperienza
(un invito, MAI un muro); la porta del sistema su /sound; la vendita
pubblica e indicizzata su /sound/professional, separata dallo
strumento (noindex).
"""
import asyncio
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _testo(percorso: Path) -> str:
    t = _senza_commenti(percorso.read_text())
    t = re.sub(r"'\s*\n\s*\+\s*'", "", t)
    return t


class TestL1CreaInvisibile:
    def test_01_niente_vetrina_solo_redirect(self):
        """Chi non ha il privilegio non legge un pitch: viene
        accompagnato in silenzio alla porta del mondo Sound."""
        src = _senza_commenti((FQ / "FrequenzePage.js").read_text())
        blocco = src[src.find("needsAuth && senzaInvito"):]
        blocco = blocco[:blocco.find("}")]
        assert '<Navigate to="/sound" replace />' in blocco
        # e la vecchia vetrina non esiste piu'
        assert "su invito: la stiamo" not in src
        assert "vorrei%20comporre" not in src

    def test_02_la_concessione_resta_al_system_admin(self):
        """Precisazione founder: /admin/sound e il flag restano
        INVARIATI — sparisce la pubblicità di Crea, non Crea."""
        admin = (BACKEND_DIR / "routers" / "admin_sound.py").read_text()
        assert "sound_composer" in admin
        assert "require_system_admin" in admin
        # chi ha il privilegio vede tutto come prima
        src = _senza_commenti((FQ / "FrequenzePage.js").read_text())
        assert "canCompose" in src

    def test_03_la_porta_di_sistema_non_nomina_crea(self):
        src = _testo(FQ / "SoundLandingPage.js").lower()
        assert "/sound/crea" not in src, "la porta pubblicizza l'atelier"


class TestL2InvitoLettera:
    def test_04_a_fine_esperienza_un_invito_non_un_muro(self):
        src = _senza_commenti((FQ / "esperienze" / "EsperienzaPage.js").read_text())
        assert 'data-testid="esp-invito-lettera"' in src
        assert 'to="/newsletter"' in src
        # chi e' gia' nel cerchio non riceve inviti a entrarci
        assert "!prova() && (" in src
        assert "from '../../../lib/cerchio'" in src
        # e l'ascolto NON e' condizionato: l'invito sta solo nella
        # schermata di fine
        blocco_fine = src[src.find("stato === 'fine'"):]
        assert "esp-invito-lettera" in blocco_fine[:1400]

    def test_05_le_esperienze_restano_libere(self):
        """NESSUN muro nuovo: niente lucchetti del cerchio sull'avvio
        delle esperienze."""
        src = _senza_commenti((FQ / "esperienze" / "EsperienzaPage.js").read_text())
        assert "sblocca" not in src and "iscriviESblocca" not in src, \
            "un muro e' entrato dalla porta di servizio"


class TestL3PortaDiSistema:
    def test_06_la_via_professionale_e_in_fondo_e_distinta(self):
        src = _senza_commenti((FQ / "SoundLandingPage.js").read_text())
        assert 'data-testid="sld-professional"' in src
        assert 'to="/sound/professional"' in src
        # prima ci si fida (biblioteca, esperienze), poi si compra:
        # la sezione pro viene DOPO le esperienze nel sorgente
        esp = src.find("sld-esperienze")
        pro = src.find("sld-professional")
        assert -1 < esp < pro, "la vendita prima della fiducia"


class TestL4LaVendita:
    def test_07_due_indirizzi_due_nature(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/sound/professional"' in app
        prof = app.find('path="/sound/professional"')
        catch = app.find('path="/sound/*"')
        assert -1 < prof < catch

    def test_08_la_shell_indicizza_la_vendita_non_lo_strumento(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from routers.seo_shell import _meta_sound
        vendita = asyncio.run(_meta_sound(["professional"]))
        assert vendita and not vendita.get("noindex")
        assert vendita["canonical"].endswith("/sound/professional")
        assert "content_html" in vendita and "ASSR" in vendita["content_html"]
        strumento = asyncio.run(_meta_sound(["pro"]))
        assert strumento and strumento.get("noindex") is True

    def test_09_in_sitemap(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/professional" in seo

    def test_10_la_voce_c0_anche_in_vendita(self):
        """Scienza in avanti, promesse mai: l'ASSR apre, le review
        sono nominate, e le parole del veleno non entrano nemmeno
        nella pagina piu' commerciale del mondo Sound."""
        src = _testo(FQ / "ProfessionalLanding.jsx")
        basso = src.lower()
        for pezzo in ("risposta uditiva stazionaria", "assr",
                      "garcia-argibay", "nessuna attrezzatura"):
            assert pezzo in basso, f"la vendita ha perso: {pezzo}"
        for veleno in ("guarig", "ripara", "riequilibr", "chakra",
                       "biorisonanza", "528", "% dei", "85%",
                       "ti sentirai", "garantis"):
            assert veleno not in basso, f"la vendita dice «{veleno}»"
        assert not re.search(r"\bcur(a|e|are)\b", basso)

    def test_11_le_prove_visive_sono_vere(self):
        """Le partiture in vendita si generano dagli score REALI del
        catalogo: nessun mockup."""
        src = _senza_commenti((FQ / "ProfessionalLanding.jsx").read_text())
        assert "from './pro/catalogo'" in src
        assert "<Partitura" in src
        assert "costruisci()" in src
        # e la pagina non suona: e' vendita, non strumento
        basso = src.lower()
        for vietato in ("creaascolto", "audiocontext", "startpreview"):
            assert vietato not in basso

    def test_12_il_funnel_e_quello_esistente(self):
        """La CTA scrive sul funnel leads gia' in produzione
        (type=operator), niente collezioni nuove."""
        src = _senza_commenti((FQ / "ProfessionalLanding.jsx").read_text())
        assert "'/public/leads'" in src
        assert "type: 'operator'" in src
        assert "'sound_professional'" in src
        # e il fallimento parla (normalizzatore, mai detail crudo)
        assert "messaggio(" in src
