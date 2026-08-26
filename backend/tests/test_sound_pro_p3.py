"""Sound Professional P3 — il Builder (26/8/2026).

Il principio sotto guardia:

    il Builder non crea suoni;
    il Builder descrive un protocollo;
    il compilatore lo traduce;
    il motore lo esegue.

Il repo non ha un runner JS per i componenti React (nessun .test.js,
nessuna dipendenza da aggiungere — e il brief dice di non aggiungerne).
Le guardie sono quelle di casa: leggono il sorgente vero, ed ESEGUONO
in Node le funzioni pure della pagina (conversione volume, andata e
ritorno dei passi, lettura dell'errore del server) contro il
compilatore vero. Dove la prova è strutturale invece che renderizzata,
è detto nel nome e nel corpo del test.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRO = FRONTEND_SRC / "features" / "frequenze" / "pro"
PAGINA = PRO / "SoundProPage.jsx"
CSS = PRO / "pro.css"
APP_JS = FRONTEND_SRC / "App.js"

_NODE = shutil.which("node") or \
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"
node_c_e = pytest.mark.skipif(not Path(_NODE).exists(),
                              reason="node non disponibile")


def _senza_commenti(testo: str) -> str:
    """Il sorgente senza commenti: le guardie devono leggere il CODICE,
    non la prosa che spiega perché una cosa non c'è."""
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _esegui(corpo: str):
    """Esegue le funzioni pure della pagina in Node.

    La pagina importa React: non si può importare tale e quale. Si
    ESTRAGGONO le funzioni pure (quelle esportate senza JSX) in un
    modulo temporaneo che importa il compilatore VERO — così quello
    che si prova è il codice che gira in produzione, non una copia.
    """
    src = PAGINA.read_text()

    def blocco(nome):
        """Dal `export` fino alla chiusura a colonna zero: regge sia
        `export function`, sia una const-freccia, sia un array."""
        m = re.search(rf"^export (?:const {nome}\b|function {nome}\b)",
                      src, re.M)
        assert m, f"non trovo l'export puro «{nome}» nella pagina"
        resto = src[m.start():]
        fine = re.search(r"^(\}|\]);?$", resto, re.M)
        assert fine, f"«{nome}» non chiude a colonna zero"
        return resto[:fine.end()]

    pezzi = [blocco(n) for n in ("METODI", "fmtTempo", "versoDsl", "daDsl",
                                 "guaiEvidenti", "leggiErroreServer")]
    modulo = (
        f"import {{ BATTITO_MAX, BATTITO_MIN, PASSI_MAX, PORTANTE_MAX, "
        f"PORTANTE_MIN, durataTotale, compila }} "
        f"from {json.dumps(str(PRO / 'compilatore.js'))};\n"
        f"import {{ PERCENTO_DEFAULT, PERCENTO_MAX, PERCENTO_MIN, aGain, "
        f"aPercento }} from {json.dumps(str(PRO / 'volume.js'))};\n"
        + "\n".join(pezzi)
        + "\nconst METODO = Object.fromEntries(METODI.map((m) => [m.id, m]));\n"
        + corpo
    )
    r = subprocess.run([_NODE, "--input-type=module", "-e", modulo],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:600]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


# ── 1-4 · la pagina esiste, è raggiungibile, ha i suoi stati ───────────────
class TestPagina:
    def test_01_la_rotta_precede_il_catch_all(self):
        """/sound/* mangia tutto ciò che gli sta dopo: è la trappola
        già annotata nel codice per il Lab, e pagata con /sound/visual."""
        src = APP_JS.read_text()
        pro = src.find('path="/sound/pro/*"')
        catch = src.find('path="/sound/*"')
        assert pro != -1 and catch != -1, "rotte mancanti in App.js"
        assert pro < catch, "/sound/pro sta DOPO il catch-all: sarà mangiata"
        # M-URL (26/8): una wildcard sola, i segmenti li risolve la pagina
        assert 'path="/sound/pro/*"' in src, "manca la wildcard di Professional"
        assert 'lazy(() => import("./features/frequenze/pro/SoundProPage"))' in src

    def test_02_il_renderer_conosce_pro_e_non_la_indicizza(self):
        """Senza questo ramo chi arriva su /sound/pro prende un 404 dal
        prerender (successo davvero con /sound/visual il 22/8). Ed è
        uno strumento: noindex, non contenuto."""
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        m = re.search(r'if sub in \(([^)]+)\):\s*\n\s*meta = \{\*\*_SOUND_PAGES'
                      r'\[None\], "noindex": True\}', src)
        assert m, "non trovo il ramo «workspace operatore» in _meta_sound"
        assert '"pro"' in m.group(1), \
            "«pro» non è fra gli strumenti noindex: verrà indicizzato o farà 404"

    def test_03_il_registro_rotte_resta_intatto(self):
        """`sound` è già classificato, e il registro conosce SOLO i
        segmenti di primo livello: aggiungere «sound/pro» creerebbe un
        fantasma e romperebbe la guardia del registro."""
        reg = json.loads(
            (BACKEND_DIR / "config" / "rotte.json").read_text(encoding="utf-8"))
        tutti = set(reg["pubblica"]) | set(reg["servizio"]) | set(reg["app"])
        assert "sound" in tutti
        assert not [x for x in tutti if "/" in x], \
            "il registro ha imparato i sotto-percorsi: rivedere questa guardia"

    def test_04_gli_stati_ci_sono_tutti(self):
        """Caricamento, vuoto, errore, e il modulo non abilitato."""
        src = _senza_commenti(PAGINA.read_text())
        for testid in ("pro-senza-invito", "pro-lista-vuota", "pro-editor",
                       "pro-lista", "pro-avviso"):
            assert f'data-testid="{testid}"' in src, f"manca lo stato {testid}"
        assert "pro-vuoto" in src, "manca lo stato di caricamento"

    def test_04b_il_cancello_e_quello_di_casa(self):
        src = _senza_commenti(PAGINA.read_text())
        assert "user?.sound_professional" in src
        assert "/login?next=" in src
        # e il flag arriva davvero al client
        assert "sound_professional: bool = False" in \
            (BACKEND_DIR / "models" / "user.py").read_text()
        assert "sound_professional=sound_professional," in \
            (BACKEND_DIR / "services" / "auth_service.py").read_text()


# ── 5-8 · la lista ─────────────────────────────────────────────────────────
class TestLista:
    def test_05_la_lista_mostra_le_sette_colonne_chieste(self):
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function Lista"):src.find("export default")]
        for pezzo, cosa in ((".nome", "nome"), (".descrizione", "descrizione"),
                            ("fmtTempo(p.durata_sec)", "durata"),
                            ("p.passi", "numero passi"),
                            ("p.versione", "versione"), ("p.stato", "stato"),
                            ("p.updated_at", "ultima modifica")):
            assert pezzo in blocco, f"la lista non mostra: {cosa}"

    def test_06_filtro_stato_e_archiviazione(self):
        src = _senza_commenti(PAGINA.read_text())
        assert "soundProAPI.list(stato)" in src
        assert "soundProAPI.archive(p.id)" in src
        assert 'pro-filtro-' in src

    def test_07_niente_di_cio_che_il_brief_vieta(self):
        """Né ricerca, né tag, né analytics, né condivisione, né
        duplicazione — e niente audio DIRETTO: la pagina compone e
        registra, chi suona è il rito (pro/Rito.jsx, S3), che a sua
        volta passa dal player condiviso. «sessione» e «customer» erano
        vietate in P3 perché fuori scope: da S2/S3 SONO lo scope."""
        src = _senza_commenti(PAGINA.read_text()).lower()
        for vietato in ("startpreview", "audiocontext", "creaponte",
                        "duplica", "analytics", "waveform", "canvas",
                        "biofeedback", "biorisonanza", "cafl",
                        "diagnos", "terap"):
            assert vietato not in src, f"il Builder contiene «{vietato}»"
        assert "engine/" not in src and "../engine" not in src

    def test_08_il_client_manda_solo_il_progetto(self):
        """organization_id, created_by, versione e score non partono da
        qui — e se partissero, il server farebbe 422."""
        src = _senza_commenti(PAGINA.read_text())
        corpo = src[src.find("const corpo = {"):]
        corpo = corpo[:corpo.find("};")]
        assert set(re.findall(r"^\s*(\w+):", corpo, re.M)) == {
            "nome", "descrizione", "note_operative", "steps"}, \
            f"il corpo della richiesta è cambiato: {corpo}"
        api = (FRONTEND_SRC / "api" / "soundPro.js").read_text()
        for proibito in ("organization_id", "created_by", "versione", "score"):
            assert proibito not in _senza_commenti(api)


# ── 9-14 · l'editor, provato eseguendo il suo codice vero ─────────────────
@node_c_e
class TestEditor:
    def test_09_i_metodi_sono_quelli_del_dsl(self):
        out = _esegui("console.log(JSON.stringify(METODI.map(m => m.id)));")
        js = (PRO / "compilatore.js").read_text()
        dsl = re.search(r"METODI_PASSO = Object\.freeze\(\[([^\]]+)\]\)", js)
        assert set(out) == set(re.findall(r"'(\w+)'", dsl.group(1)))
        # e nessun metodo del contratto che il DSL non prevede
        assert set(out) == {"tone", "drone", "bin", "iso"}

    def test_10_i_campi_del_battito_sono_condizionali(self):
        """Un campo che il motore ignorerebbe è una promessa falsa: il
        compilatore lo RIFIUTA, quindi la UI non deve mostrarlo."""
        out = _esegui("console.log(JSON.stringify("
                      "METODI.map(m => [m.id, !!m.battito])));")
        assert dict(out) == {"tone": False, "drone": False,
                             "bin": True, "iso": True}
        src = _senza_commenti(PAGINA.read_text())
        assert "{m.battito && (" in src, "i campi del battito non sono condizionali"

    def test_11_battito_finale_opzionale(self):
        """Vuoto = battito fermo. Valorizzato = transizione. Il campo
        vuoto NON deve arrivare al DSL come chiave."""
        out = _esegui("""
const fermo = versoDsl({metodo:'bin', hz:400, battito_hz:10,
  battito_fine_hz:'', durata_sec:120, pausa_dopo_sec:0, percento:25});
const scivola = versoDsl({metodo:'bin', hz:400, battito_hz:10,
  battito_fine_hz:6, durata_sec:120, pausa_dopo_sec:0, percento:25});
const tono = versoDsl({metodo:'tone', hz:220, battito_hz:8,
  battito_fine_hz:6, durata_sec:120, pausa_dopo_sec:0, percento:25});
console.log(JSON.stringify({fermo, scivola, tono}));""")
        assert "battito_fine_hz" not in out["fermo"]
        assert out["scivola"]["battito_fine_hz"] == 6
        # il tono non porta battito, nemmeno se il modulo lo ricorda
        assert "battito_hz" not in out["tono"]

    def test_12_pausa_e_durata_totale_dal_compilatore(self):
        """La matematica del tempo NON è ricopiata: il totale mostrato
        è quello di durataTotale, e coincide con lo score compilato."""
        out = _esegui("""
const passi = [
  {metodo:'tone', hz:220, durata_sec:180, pausa_dopo_sec:30, percento:30},
  {metodo:'iso', hz:180, battito_hz:8, battito_fine_hz:'',
   durata_sec:300, pausa_dopo_sec:99, percento:22},
].map(versoDsl);
console.log(JSON.stringify({
  totale: durataTotale(passi),
  compilato: compila(passi).duration_sec,
  finestre: compila(passi).layers.map(l => [l.start, l.end]),
}));""")
        assert out["totale"] == 510, "180 + 30 di pausa + 300"
        assert out["compilato"] == 510, "il totale mostrato mente sul salvato"
        assert out["finestre"] == [[0, 180], [210, 510]]
        # la pagina usa la funzione del compilatore, non una sua copia
        src = _senza_commenti(PAGINA.read_text())
        assert "durataTotale(passi.map(versoDsl))" in src
        assert "reduce" not in src, "qualcuno ha ricopiato la somma delle durate"

    def test_13_il_volume_e_una_percentuale_deterministica(self):
        """0.17 non si mostra: si mostra 17%. Andata e ritorno esatti
        su tutta la scala, e il valore mandato è quello del DSL."""
        out = _esegui("""
const giro = [];
for (let p = PERCENTO_MIN; p <= PERCENTO_MAX; p++) giro.push(aPercento(aGain(p)) === p);
console.log(JSON.stringify({
  tuttiUguali: giro.every(Boolean),
  esempi: [aGain(17), aGain(5), aGain(100), aPercento(0.22)],
  fuoriScala: [aGain(0), aGain(999)],
}));""")
        assert out["tuttiUguali"], "la conversione volume non è reversibile"
        assert out["esempi"] == [0.17, 0.05, 1, 22]
        assert out["fuoriScala"] == [0.05, 1], "la conversione non è limitata"
        src = _senza_commenti(PAGINA.read_text())
        assert "gain: aGain(Number(p.percento))" in src
        # niente scale psicologiche
        for parola in ("rilassante", "intenso", "profondo", "energizzante"):
            assert parola not in src.lower()

    def test_14_andata_e_ritorno_non_perde_niente(self):
        """IL VERDETTO DEL BRIEF: creare, salvare, riaprire senza
        perdere informazioni. Si simula il giro intero — UI → DSL →
        (quel che il server salva) → UI — e si confronta."""
        out = _esegui("""
const iniziale = [
  {metodo:'drone', hz:110, battito_hz:8, battito_fine_hz:'',
   durata_sec:120, pausa_dopo_sec:15, percento:25},
  {metodo:'bin', hz:400, battito_hz:10, battito_fine_hz:6,
   durata_sec:240, pausa_dopo_sec:20, percento:20},
  {metodo:'iso', hz:180, battito_hz:8, battito_fine_hz:'',
   durata_sec:180, pausa_dopo_sec:0, percento:22},
];
const salvati = iniziale.map(versoDsl);
const riaperti = salvati.map(daDsl);
const dinuovo = riaperti.map(versoDsl);
console.log(JSON.stringify({
  salvati, uguali: JSON.stringify(salvati) === JSON.stringify(dinuovo),
  riaperti: riaperti.map(p => ({metodo: p.metodo, hz: p.hz,
    battito_fine_hz: p.battito_fine_hz, percento: p.percento,
    pausa: p.pausa_dopo_sec})),
}));""")
        assert out["uguali"], "riaprire e risalvare cambia il protocollo"
        assert out["riaperti"][0]["battito_fine_hz"] == "", \
            "il battito assente torna come campo vuoto, non come undefined"
        assert out["riaperti"][1]["battito_fine_hz"] == 6
        assert [p["percento"] for p in out["riaperti"]] == [25, 20, 22]
        assert out["riaperti"][0]["pausa"] == 15
        # e gli stessi passi rimandati non fanno una versione nuova (P2)
        router = (BACKEND_DIR / "routers" / "sound_pro.py").read_text()
        assert 'if steps != prima.get("steps"):' in router


# ── 15-17 · errori, validazione, aggiungi/togli ───────────────────────────
@node_c_e
class TestErrori:
    def test_15_l_errore_del_server_si_appende_al_passo(self):
        out = _esegui("""
console.log(JSON.stringify([
  leggiErroreServer('passo 3: frequenza 9000 fuori da 20–2000 Hz'),
  leggiErroreServer('Limite di 200 protocolli raggiunto.'),
  leggiErroreServer(undefined),
]));""")
        assert out[0] == {"indice": 2, "testo": "frequenza 9000 fuori da 20–2000 Hz"}
        assert out[1]["indice"] is None
        assert out[2]["testo"], "un errore muto non aiuta nessuno"
        src = _senza_commenti(PAGINA.read_text())
        assert "setErroriPasso({ [indice]: testo })" in src

    def test_16_la_ui_valida_l_ovvio_ma_non_e_una_seconda_copia(self):
        out = _esegui("""
const ok = {metodo:'bin', hz:400, battito_hz:10, battito_fine_hz:'',
  durata_sec:120, pausa_dopo_sec:0, percento:25};
console.log(JSON.stringify({
  buono: guaiEvidenti(ok),
  hz: !!guaiEvidenti({...ok, hz: 9000}),
  battito: !!guaiEvidenti({...ok, battito_hz: 90}),
  fine: !!guaiEvidenti({...ok, battito_fine_hz: 90}),
  durata: !!guaiEvidenti({...ok, durata_sec: 0}),
  vuoto: !!guaiEvidenti({...ok, hz: ''}),
  pausa: !!guaiEvidenti({...ok, pausa_dopo_sec: -5}),
}));""")
        assert out["buono"] is None
        assert all(out[k] for k in ("hz", "battito", "fine", "durata",
                                    "vuoto", "pausa"))
        # ma la durata TOTALE non la ricontrolla: è il server a dire
        # se un protocollo è troppo corto o troppo lungo
        src = _senza_commenti(PAGINA.read_text())
        assert "DURATA_MIN" not in src and "DURATA_MAX" not in src, \
            "la UI ha iniziato a copiare il contratto"

    def test_17_aggiungere_e_togliere_passi(self):
        src = _senza_commenti(PAGINA.read_text())
        assert "passi.length >= PASSI_MAX" in src, "manca il tetto dei passi"
        assert "prec.length === 1 ? prec" in src, \
            "si può restare senza nemmeno un passo"
        assert 'data-testid="pro-aggiungi"' in src


# ── 18-20 · versioni, responsive, e ciò che non si tocca ──────────────────
class TestFormaEConfini:
    def test_18_la_versione_si_vede_e_non_si_modifica_all_indietro(self):
        src = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-versione"' in src
        assert "Versione {protocollo.versione}" in src
        assert "versioni_precedenti?.length" in src
        # nessun ritorno indietro: né rollback, né diff, né branch
        for vietato in ("rollback", "ripristina", "diff", "confronta"):
            assert vietato not in src.lower()

    def test_19_mobile_senza_scorrimento_laterale(self):
        """Prova STRUTTURALE, non una misura sul telefono: nessuna
        tabella nell'editor, e le griglie collassano a una colonna al
        breakpoint già in casa."""
        pagina = _senza_commenti(PAGINA.read_text())
        assert "<table" not in pagina, "una tabella nell'editor = scroll laterale"
        css = _senza_commenti(CSS.read_text())
        assert "@media (max-width: 760px)" in css
        stretto = css[css.find("@media (max-width: 760px)"):]
        assert ".pro-griglia { grid-template-columns: 1fr; }" in stretto
        assert ".pro-corpo { grid-template-columns: 1fr; }" in \
            css[css.find("@media (max-width: 900px)"):]
        # e nessuna larghezza fissa che sfondi lo schermo
        assert not re.search(r"(?<![-a-z])width:\s*\d{3,}px", css), \
            "larghezza fissa nel CSS del Builder"

    def test_20_niente_neon_ne_estetica_biohacking(self):
        css = _senza_commenti(CSS.read_text()).lower()
        for vietato in ("#0ff", "#0f0", "#f0f", "neon", "glow",
                        "text-shadow: 0 0", "432", "528"):
            assert vietato not in css, f"il CSS ha «{vietato}»"

    def test_21_i_file_intatti_sono_intatti(self):
        """Il Builder non duplica il player e non tocca il motore."""
        import subprocess as sp
        radice = BACKEND_DIR.parent
        intatti = [
            "frontend/src/features/frequenze/engine",
            "frontend/src/features/frequenze/lab",
            "frontend/src/features/frequenze/content/calm.js",
            "frontend/src/features/frequenze/content/ground.js",
            "frontend/src/features/frequenze/content/esperienze.js",
            "frontend/src/features/frequenze/PublicFrequencyPage.js",
            "frontend/src/features/frequenze/MeditazioniPage.js",
            "frontend/package.json",
            "frontend/src/features/frequenze/pro/compilatore.js",
        ]
        r = sp.run(["git", "diff", "--name-only", "HEAD", "--", *intatti],
                   cwd=radice, capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("git non disponibile")
        assert not r.stdout.strip(), f"file che dovevano restare intatti: {r.stdout}"


# ── 22 · IL VERDETTO: creare, salvare, riaprire senza perdere niente ───────
BASE_URL = "http://localhost:8000"


def _sessione():
    """Il login del banco, lo stesso di test_frequencies_fq.py."""
    import requests
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
    except Exception:
        pytest.skip("backend non raggiungibile")
    if r.status_code != 200:
        pytest.skip("login demo non disponibile (rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestIlGiroCompleto:
    """La condizione che il brief pone per dichiarare P3 pronto: un
    operatore crea un protocollo vero, lo salva, lo riapre e non ha
    perso niente. Si prova contro il SERVER VERO, con lo stesso corpo
    che manda il Builder — la funzione `versoDsl` gira in Node e il suo
    risultato viene spedito, così non si prova una copia a mano."""

    def test_22_crea_salva_riapri(self):
        import requests
        hdr = _sessione()
        passi = _esegui("""
console.log(JSON.stringify([
  {metodo:'drone', hz:110, battito_hz:8, battito_fine_hz:'',
   durata_sec:120, pausa_dopo_sec:15, percento:25},
  {metodo:'bin', hz:400, battito_hz:10, battito_fine_hz:6,
   durata_sec:240, pausa_dopo_sec:20, percento:20},
  {metodo:'iso', hz:180, battito_hz:8, battito_fine_hz:'',
   durata_sec:180, pausa_dopo_sec:0, percento:22},
].map(versoDsl)));""")
        corpo = {"nome": "Collaudo P3", "descrizione": "Creato dal Builder",
                 "note_operative": "Appunti dell'operatore", "steps": passi}

        r = requests.post(f"{BASE_URL}/api/sound/pro/protocolli",
                          json=corpo, headers=hdr, timeout=15)
        if r.status_code == 403:
            pytest.skip("l'org demo non ha il privilegio sound_professional")
        assert r.status_code == 201, r.text
        creato = r.json()
        try:
            assert creato["versione"] == 1
            assert creato["durata_sec"] == 120 + 15 + 240 + 20 + 180
            assert len(creato["score"]["layers"]) == 3

            # RIAPRI: il GET deve ridare esattamente i passi mandati
            letto = requests.get(
                f"{BASE_URL}/api/sound/pro/protocolli/{creato['id']}",
                headers=hdr, timeout=15).json()
            assert letto["steps"] == passi, "riaprire ha perso informazioni"
            assert letto["note_operative"] == "Appunti dell'operatore"

            # e il giro completo dell'editor: DSL → UI → DSL → server
            ritorno = _esegui(
                "const passi = " + json.dumps(letto["steps"]) + ";\n"
                "console.log(JSON.stringify(passi.map(daDsl).map(versoDsl)));")
            assert ritorno == passi, "il giro dell'editor altera il protocollo"

            # risalvare identico NON fa una versione nuova (decisione P2)
            uguale = requests.patch(
                f"{BASE_URL}/api/sound/pro/protocolli/{creato['id']}",
                json={"steps": ritorno}, headers=hdr, timeout=15)
            assert uguale.status_code == 200 and uguale.json()["versione"] == 1

            # cambiare i passi sì, e la versione 1 resta recuperabile
            nuovi = [dict(passi[0], durata_sec=200)]
            dopo = requests.patch(
                f"{BASE_URL}/api/sound/pro/protocolli/{creato['id']}",
                json={"steps": nuovi}, headers=hdr, timeout=15).json()
            assert dopo["versione"] == 2
            assert dopo["versioni_precedenti"][0]["durata_sec"] == 575
        finally:
            requests.delete(f"{BASE_URL}/api/sound/pro/protocolli/{creato['id']}",
                            headers=hdr, timeout=15)
