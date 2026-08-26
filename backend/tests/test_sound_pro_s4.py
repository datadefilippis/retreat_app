"""Sound Professional S4 — lo storico (26/8/2026).

Il momento in cui il registro RIPAGA: «la volta scorsa GROUND, da 4 a
7, dodici giorni fa». Due superfici, zero backend nuovo — l'API di S2
bastava, ed era il punto: se per leggere lo storico fosse servito un
endpoint nuovo, S2 sarebbe stata disegnata male.
"""
import re
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRO = FRONTEND_SRC / "features" / "frequenze" / "pro"
RITO = PRO / "Rito.jsx"
PAGINA = PRO / "SoundProPage.jsx"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


class TestLaContinuita:
    def test_01_scelto_il_cliente_si_vede_la_volta_scorsa(self):
        src = _senza_commenti(RITO.read_text())
        assert 'data-testid="rito-ultima"' in src
        # dal registro vero, filtrato per QUEL cliente
        assert "sessioni.list({ customer_id: clienteId })" in src
        # e si mostra il vissuto com'era: da X a Y
        assert "ultima.feedback_pre" in src and "ultima.feedback_post" in src

    def test_02_solo_sessioni_chiuse_e_niente_invenzioni(self):
        """Una riga in corso non è memoria; e se non c'è mai stata una
        sessione lo si dice, non si tace e non si inventa."""
        src = _senza_commenti(RITO.read_text())
        assert "!== 'in_corso'" in src
        assert 'data-testid="rito-prima-volta"' in src
        assert "Prima sessione insieme" in src

    def test_03_gli_esiti_storti_si_dicono(self):
        """La volta scorsa può essere andata male: interrotta o con
        l'audio caduto. La continuità onesta lo riporta."""
        src = _senza_commenti(RITO.read_text())
        assert "ultima.stato === 'interrotta'" in src
        assert "ultima.stato === 'persa'" in src

    def test_04_quando_come_lo_direbbe_una_persona(self):
        src = _senza_commenti(RITO.read_text())
        assert "export function quandoFa" in src
        for parola in ("'oggi'", "'ieri'", "giorni fa"):
            assert parola in src


class TestIlRegistro:
    def test_05_la_vista_esiste_e_si_raggiunge(self):
        src = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-registro"' in src
        # l'interruttore e' templato: pro-vista-${v} sui due valori
        assert "data-testid={`pro-vista-${v}`}" in src
        assert "'registro', 'Registro'" in src
        assert "vista === 'registro'" in src

    def test_06_le_righe_dicono_tutto_il_necessario(self):
        """Quando, cosa, con chi, com'è finita, quanto s'è ascoltato,
        il vissuto. Le colonne del quaderno."""
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function RigaSessione"):src.find("function Registro")]
        for pezzo, cosa in (("quandoFa(s.iniziata_il)", "quando"),
                            ("s.protocollo?.titolo", "cosa"),
                            ("reg-cliente", "con chi"),
                            ("ESITO_LABEL[s.stato]", "esito"),
                            ("s.ascolto_sec", "ascoltato"),
                            ("s.durata_prevista_sec", "previsto"),
                            ("s.feedback_pre", "vissuto")):
            assert pezzo in blocco, f"la riga non dice: {cosa}"

    def test_07_esiti_con_parole_oneste(self):
        """«Audio caduto» dice cosa è successo; «persa» da sola no. E
        nessuna etichetta si inventa esiti che il modello non ha."""
        src = _senza_commenti(PAGINA.read_text())
        m = re.search(r"const ESITO_LABEL = \{(.*?)\};", src, re.S)
        assert m, "manca la mappa degli esiti"
        chiavi = set(re.findall(r"(\w+):", m.group(1)))
        assert chiavi == {"in_corso", "completata", "interrotta", "persa"}
        assert "Audio caduto" in m.group(1)

    def test_08_le_note_solo_nel_dettaglio(self):
        """La lista non porta le note (proiezione S2): la riga le va a
        chiedere alla singola sessione quando si apre."""
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function RigaSessione"):src.find("function Registro")]
        assert "sessioni.get(s.id)" in blocco
        assert "Nessuna nota." in blocco

    def test_09_i_nomi_non_dimenticano(self):
        """Il registro risolve i nomi anche dei clienti disattivati:
        è memoria, non deve dimenticare chi c'era."""
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function Registro"):src.find("function SessioniAperte")]
        assert "customersAPI.list(false" in blocco, \
            "solo gli attivi: le sessioni vecchie perdono il nome"
        assert "reg-filtro-cliente" in src and "reg-filtro-stato" in src

    def test_10_zero_backend_nuovo(self):
        """S4 legge, non aggiunge: il router delle sessioni e quello
        dei protocolli sono INTATTI rispetto a S3."""
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "backend/"],
            cwd=BACKEND_DIR.parent, capture_output=True, text=True)
        if r.returncode != 0:
            import pytest
            pytest.skip("git non disponibile")
        toccati = [x for x in r.stdout.strip().splitlines()
                   if not x.startswith("backend/tests/")]
        assert not toccati, f"S4 doveva solo leggere, ha toccato: {toccati}"

    def test_11_le_guardie_audio_reggono_ancora(self):
        """Registro e continuità non hanno aperto porte all'audio nella
        pagina: suona solo il rito, tramite il player condiviso."""
        src = _senza_commenti(PAGINA.read_text()).lower()
        for vietato in ("creaascolto", "esperienze/ascolto",
                        "startpreview", "audiocontext"):
            assert vietato not in src, f"la pagina importa «{vietato}»"
