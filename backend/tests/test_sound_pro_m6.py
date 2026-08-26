"""Sound Professional M6 — il metodo e le schede consolidate
(26/8/2026).

Il feedback del founder: «l'operatore entra e non capisce perché lo
usa; anche io non capisco cosa abbiamo creato». La risposta in-product:
la pagina «Il metodo» (cosa è, perché, con che attrezzatura, da dove
viene, cosa NON è, perché il registro) + le schede consolidate col
«come si conduce». E il fix di flusso: la persona si sceglie UNA
volta — dalla scheda percorso viaggia fino al rito.
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRO = FRONTEND_SRC / "features" / "frequenze" / "pro"
METODO = PRO / "metodo.js"
CATALOGO = PRO / "catalogo.js"
PAGINA = PRO / "SoundProPage.jsx"
RITO = PRO / "Rito.jsx"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _testo(percorso: Path) -> str:
    """Il CONTENUTO di un file di dati JS, pronto per le asserzioni:
    senza commenti (la prosa che nega inciampa le guardie), con le
    concatenazioni RICONGIUNTE ('come una ' + 'marea' → come una
    marea — la trappola dei '+' già pagata nei cicli FQ), minuscolo."""
    t = _senza_commenti(percorso.read_text())
    t = re.sub(r"'\s*\n\s*\+\s*'", "", t)
    return t.lower()


class TestIlMetodo:
    def test_01_le_sei_sezioni_che_rispondono(self):
        ids = re.findall(r"id: '([\w-]+)'", METODO.read_text())
        assert ids == ["cosa", "perche", "come", "basi", "non-e",
                       "registro"], f"sezioni: {ids}"
        # le risposte alle domande del founder, presenti davvero
        src = _testo(METODO)
        for pezzo, domanda in (
                ("cuffie stereo", "con che attrezzo?"),
                ("conduzione ossea", "le ossee vanno bene?"),
                ("non esistono frequenze che", "è biorisonanza?"),
                ("programmi internazionali di ascolto", "con chi competiamo?"),
                ("grado b", "ci siamo ispirati alla letteratura?"),
                ("banco aurya", "da dove vengono le esperienze?"),
                ("la volta scorsa", "perché il registro?")):
            assert pezzo in src, f"il metodo non risponde a: {domanda}"

    def test_02_le_negazioni_ci_sono_e_i_claim_no(self):
        """La parola «biorisonanza» può esistere SOLO dentro la
        negazione; le promesse mai."""
        src = _testo(METODO)
        i = src.find("biorisonanza")
        assert i != -1
        contesto = src[max(0, i - 120):i + 120]
        assert "non è biorisonanza" in contesto
        basso = src
        assert not re.search(r"\bcur(a|e|are)\b", basso)
        for veleno in ("guarig", "ripara", "riequilibr", "528", "chakra",
                       "diagnos"):
            assert veleno not in basso, f"il metodo dice «{veleno}»"
        # e la parola «terapia» esiste solo negata
        for m in re.finditer(r"\bterapia\b", basso):
            contesto = basso[max(0, m.start() - 60):m.start()]
            assert "non è una" in contesto or "non sostituisce" in contesto

    def test_03_la_pagina_lo_serve_con_un_url_suo(self):
        src = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-metodo"' in src
        assert "'metodo'" in src and "/sound/pro/metodo" in src
        assert "'Il metodo'" in src, "manca la voce in testata"
        assert 'data-testid="pro-invito-metodo"' in src, \
            "il primo giro non ha l'invito"


class TestLeSchedeConsolidate:
    def test_04_ogni_scheda_dice_come_si_conduce(self):
        assert _senza_commenti(CATALOGO.read_text()).count("come: '") == 8, \
            "non tutte le schede dicono come condursi"
        src = _testo(CATALOGO)
        # le parole dell'attrezzatura, dove servono
        assert "confronto fra le due orecchie" in src, \
            "il binaurale non spiega PERCHÉ vuole le cuffie"
        assert "diffusore" in src, "i bassi veri non nominano il diffusore"
        pagina = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-come"' in pagina, \
            "la scheda non mostra il come"

    def test_05_i_racconti_hanno_anima_e_niente_promesse(self):
        """Storytelling sì, claim no: le frasi evocative descrivono il
        SUONO e la PRATICA, mai uno stato interiore promesso."""
        src = _testo(CATALOGO)
        # le immagini che raccontano
        for immagine in ("si sente prima nel corpo", "caffè sonoro",
                         "come una marea", "la soglia"):
            assert immagine in src, f"il racconto ha perso: «{immagine}»"
        # le promesse che non entrano
        for promessa in ("ti sentirai", "sentirai", "raggiungerai",
                         "ti porterà", "garantis", "trasforma la tua"):
            assert promessa not in src, f"una promessa: «{promessa}»"

    def test_06_le_negazioni_delle_schede_delicate(self):
        src = _testo(CATALOGO)
        blocco = src[src.find("elaborare"):src.find("concentrare")]
        assert "non li sostituisce" in blocco
        assert "mai lasciato da solo" in blocco


class TestIlFlussoPersona:
    def test_07_si_sceglie_una_volta(self):
        """Dalla scheda percorso al rito: la persona viaggia — il
        feedback del founder («devo riselezionare il cliente»)."""
        pagina = _senza_commenti(PAGINA.read_text())
        assert "}, cliente);" in pagina, \
            "la scheda percorso non passa la persona al rito"
        assert "clienteIniziale={rito.cliente || null}" in pagina
        rito = _senza_commenti(RITO.read_text())
        assert "clienteIniziale = null" in rito
        assert "useState(clienteIniziale)" in rito, \
            "il rito non parte dalla persona già scelta"

    def test_08_il_progresso_si_aggiorna_al_ritorno(self):
        """Chiusa la tappa, la scheda percorso rilegge le fatte senza
        ricaricare: `chiave` cambia con onEsci e l'effetto dipende da
        lei."""
        pagina = _senza_commenti(PAGINA.read_text())
        assert re.search(r"\}, \[clienteId, pc\.id, chiave\]\);", pagina), \
            "il progresso non dipende dalla chiave del ritorno"
        assert "setChiave((k) => k + 1)" in pagina
