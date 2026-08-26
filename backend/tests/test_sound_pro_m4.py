"""Sound Professional M4/1 + M-URL + M-CRM — onde, indirizzi, persone
(26/8/2026).

Tre richieste del founder nello stesso giro:
- «belle onde reali in movimento... che rappresentano realmente
  quello che si sta ascoltando» → il RUBINETTO sul player condiviso
  (additivo per contratto) + il pittore Onde;
- «link unici per ogni pagina» → ogni vista ha il suo URL;
- «inserimento cliente snello... si sincronizza col gestionale?» →
  il combobox cerca-o-crea sul CRM, che è UNO (nessuna sincronia:
  la fonte è la stessa collezione).
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
PRO = FQ / "pro"
ASCOLTO = FQ / "esperienze" / "ascolto.js"
ONDE = PRO / "Onde.jsx"
RITO = PRO / "Rito.jsx"
PAGINA = PRO / "SoundProPage.jsx"
PERSONA = PRO / "ScegliPersona.jsx"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


class TestIlRubinetto:
    """L'unica modifica al player condiviso: un AnalyserNode opzionale
    fra motore e ponte. ADDITIVA PER CONTRATTO: senza l'opzione non
    nasce nessun nodo e il percorso audio è identico — CALM e GROUND
    non passano di qui e non cambiano."""

    def test_01_opzionale_e_di_passaggio(self):
        src = _senza_commenti(ASCOLTO.read_text())
        assert "analisi" in src
        # il nodo nasce SOLO se chiesto...
        assert re.search(r"if \(analisi && !sonda\)", src)
        # ...e senza, lo sbocco resta il ponte: identico a prima
        assert "sbocco: sonda || ponte.nodo" in src
        # il rubinetto non colora: si INSERISCE, connesso al ponte
        assert "sonda.connect(ponte.nodo)" in src
        assert "analisi: () => sonda" in src

    def test_02_le_esperienze_non_lo_chiedono(self):
        """CALM e GROUND restano come sono: nessuna opzione analisi
        nella pagina delle esperienze."""
        esp = _senza_commenti((FQ / "esperienze" / "EsperienzaPage.js").read_text())
        assert "analisi" not in esp, \
            "le esperienze hanno acceso il rubinetto: non era il patto"

    def test_03_le_esperienze_pubblicate_non_cambiano_suono(self):
        """L'invariante durevole. La lista-fotografia e' caduta con C2
        (Respiro 2.0 ESTENDE il motore, opt-in, ed e' il suo mestiere):
        quel che deve restare vero e' che le ricette gia' pubblicate
        suonino come prima — nessuna di loro chiede la guida, e il Lab
        resta fuori."""
        import subprocess as sp
        for nome in ("calm.js", "ground.js"):
            # SENZA commenti: la parola «guida» vive nella prosa di
            # CALM (che il respiro lo usa come texture, e lo spiega) —
            # quel che non deve esserci e' il CAMPO
            testo = _senza_commenti((FQ / "content" / nome).read_text())
            assert "guida:" not in testo, f"{nome} e' diventata un pacer"
        r = sp.run(["git", "diff", "--name-only", "HEAD", "--",
                    "frontend/src/features/frequenze/content/calm.js",
                    "frontend/src/features/frequenze/content/ground.js",
                    "frontend/src/features/frequenze/lab"],
                   cwd=BACKEND_DIR.parent, capture_output=True, text=True)
        if r.returncode != 0:
            import pytest
            pytest.skip("git non disponibile")
        assert not r.stdout.strip(), f"toccato: {r.stdout}"


class TestLeOnde:
    def test_04_onde_vere_non_animazioni(self):
        """Il pittore legge la forma d'onda dall'analyser: se si vede
        qualcosa, sta suonando davvero."""
        src = _senza_commenti(ONDE.read_text())
        assert "getByteTimeDomainData" in src
        # non crea audio e non conosce il motore: riceve un prestito
        basso = src.lower()
        for vietato in ("audiocontext", "createanalyser", "creaascolto",
                        "startpreview", "engine/"):
            assert vietato not in basso, f"le onde contengono «{vietato}»"
        assert "sorgente?.()" in src, "l'analyser deve arrivare in prestito"

    def test_05_l_orologio_e_suo_e_muore_con_lui(self):
        src = _senza_commenti(ONDE.read_text())
        assert "requestAnimationFrame" in src
        assert "cancelAnimationFrame" in src, "il rAF sopravvive allo smontaggio"
        assert "vivo = false" in src

    def test_06_nel_rito_e_col_rubinetto_aperto(self):
        src = _senza_commenti(RITO.read_text())
        assert "analisi: true" in src, "il rito non chiede il rubinetto"
        assert "<Onde" in src
        assert "ascoltoRef.current?.analisi?.()" in src, \
            "le onde non ricevono l'analyser in prestito"


class TestGliIndirizzi:
    def test_07_ogni_vista_ha_il_suo_url(self):
        src = _senza_commenti(PAGINA.read_text())
        for segmento in ("'registro'", "'catalogo'", "'percorso'",
                         "'protocollo'"):
            assert segmento in src, f"manca il segmento {segmento}"
        # la navigazione VA agli indirizzi, non a uno stato interno
        for rotta in ("/sound/pro/registro", "/sound/pro/catalogo/",
                      "/sound/pro/percorso/", "/sound/pro/protocollo/"):
            assert rotta in src, f"nessuna navigazione verso {rotta}"

    def test_08_i_vecchi_link_dell_editor_reggono(self):
        """/sound/pro/<id> (P3) deve continuare a funzionare: un
        segmento solo e ignoto vale come id dell'editor."""
        src = _senza_commenti(PAGINA.read_text())
        assert "seg.length === 1" in src
        assert ("!['registro', 'catalogo', 'percorso', 'metodo']"
                ".includes(seg[0])") in src

    def test_09_il_renderer_copre_tutto_il_sottoalbero(self):
        """_meta_sound guarda solo parts[0]: 'pro' copre anche
        /sound/pro/registro e compagnia — nessun 404 dal prerender per
        gli URL nuovi."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        m = re.search(r"sub = parts\[0\] if parts else None", shell)
        assert m, "la shell non risolve più per primo segmento: rivedere"
        assert '"pro"' in shell


class TestLaPersona:
    def test_10_cerca_o_crea_sul_crm_unico(self):
        src = _senza_commenti(PERSONA.read_text())
        assert "customersAPI.list" in src
        assert "customersAPI.create" in src, "manca la creazione al volo"
        # la creazione chiede solo il nome: due secondi, non un modulo
        assert "create({ name: nome })" in src
        # e il filtro cerca mentre scrivi
        assert "toLowerCase().includes(filtro)" in src

    def test_11_dove_si_crea_e_dove_no(self):
        """Nel rito e nella scheda percorso si può creare; nel filtro
        del registro NO — un filtro non inventa persone."""
        pagina = _senza_commenti(PAGINA.read_text())
        blocco_registro = pagina[pagina.find("function Registro()"):]
        assert "permettiCrea={false}" in blocco_registro
        rito = _senza_commenti(RITO.read_text())
        assert "permettiCrea={false}" not in rito

    def test_12_niente_doppio_elenco(self):
        """La risposta alla domanda del founder («si sincronizza col
        gestionale?»): la fonte è UNA — il combobox usa customersAPI,
        la stessa del CRM. Nessuna collezione parallela."""
        src = _senza_commenti(PERSONA.read_text())
        assert "soundProAPI" not in src, \
            "il combobox parla con un'API sua: elenco parallelo in arrivo"
        importi = re.findall(r"from '([^']+)'", src)
        for imp in importi:
            assert imp.startswith((".", "..")) or imp == "react"
