"""CALM 1.0 — la prima esperienza di Aurya Sound (STEP 8, 26/8/2026).

CALM non e' un motore: e' uno SCORE (dati) che il motore di casa suona
da sempre, piu' una porta. Queste guardie tengono le due cose che
possono scivolare: i numeri del protocollo (che sono il prodotto) e la
promessa che non facciamo (nessuna affermazione fisiologica).

Piano e specifica: nel commento in testa a content/calm.js
"""
import re
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
CALM = FQ / "content" / "calm.js"
PAGINA = FQ / "calm" / "CalmPage.js"
ASCOLTO = FQ / "esperienze" / "ascolto.js"
REGISTRO = FQ / "content" / "esperienze.js"


def _codice(p: Path) -> str:
    """Il file spogliato dei commenti: si giudica cio' che fa, non cio'
    che racconta (lezione ripetuta tre volte nel ciclo del Lab)."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", p.read_text(), flags=re.S)


class TestIlProtocollo:
    """I numeri approvati dal founder. Se cambiano, e' una decisione —
    e allora si cambia anche qui, con lui."""

    def test_dura_sei_minuti(self):
        src = _codice(CALM)
        assert "CALM_DURATA = 360" in src, "la durata non e' piu' 6:00"
        # e il tetto di casa (10 minuti) non e' mai in discussione
        assert 360 <= 600

    def test_i_tre_livelli_e_i_loro_numeri(self):
        src = _codice(CALM)
        atteso = [
            ("drone", "carrier: 110", "gain: 0.22"),
            ("breath", "carrier: 220", "gain: 0.30"),
            ("bin", "carrier: 330", "gain: 0.16"),
        ]
        for metodo, portante, guadagno in atteso:
            assert f"method: '{metodo}'" in src, f"manca il livello {metodo}"
            assert portante in src, f"{metodo}: portante cambiata ({portante})"
            assert guadagno in src, f"{metodo}: guadagno cambiato ({guadagno})"
        # TRE, non quattro: il miscuglio olistico e' cio' che CALM non e'
        assert src.count("layer({") == 3, "CALM ha cambiato numero di livelli"

    def test_le_portanti_sono_imparentate(self):
        """110 · 220 · 330 — la nota, la sua ottava, la sua quinta: si
        fondono invece di litigare. Se una scivola fuori dalla serie,
        l'accordo si rompe."""
        src = _codice(CALM)
        portanti = sorted(int(m) for m in re.findall(r"carrier: (\d+)", src))
        assert portanti == [110, 220, 330]
        assert portanti[1] == 2 * portanti[0] and portanti[2] == 3 * portanti[0]

    def test_le_finestre_temporali(self):
        src = _codice(CALM)
        assert "respiroDa: 6, respiroA: 320" in src
        assert "battitoDa: 150, battitoA: 270" in src, \
            "il battito non entra piu' a 2:30 o non esce a 4:30"
        # il respiro finisce 40 s PRIMA del fondo: sono i due finali
        # annidati che evitano lo stop brusco
        assert 320 < 360

    def test_il_respiro_rallenta_e_non_riaccelera(self):
        """E' l'unico vero dispositivo dell'esperienza: 8 → 5,5 cicli
        al minuto. Al rientro NON si torna su — spingere indietro chi
        si e' appena posato sarebbe il contrario del progetto."""
        src = _codice(CALM)
        assert "f0: alMinuto(8), f1: alMinuto(5.5)" in src
        assert "const alMinuto = (n) => n / 60" in src, \
            "i cicli al minuto non si convertono piu' in hertz"

    def test_il_battito_scende_da_7_a_6(self):
        src = _codice(CALM)
        assert "f0: 7, f1: 6" in src

    def test_le_dissolvenze(self):
        src = _codice(CALM)
        assert "CALM_FADE_IN = 12" in src and "CALM_FADE_OUT = 24" in src

    def test_le_cinque_fasi(self):
        src = _codice(CALM)
        for t, nome in ((0, 'arrivo'), (90, 'rallentamento'), (150, 'sosta'),
                        (270, 'rientro'), (320, 'congedo')):
            assert f"{{ t: {t}, name: '{nome}' }}" in src, \
                f"fase {nome} spostata o rinominata"

    def test_niente_di_piu(self):
        """Il vincolo del founder, scritto in codice: nessun elemento
        aggiunto «perche' e' olistico»."""
        src = _codice(CALM)
        for vietato in ("'noise'", "'shepard'", "'iso'", "'tone'", "'mono'",
                        "'bil'", "432", "528"):
            assert vietato not in src, f"CALM ha guadagnato {vietato}"


class TestContrattoDelProtocollo:
    """FASE 4 (consolidamento) — gli score delle esperienze INTEGRATE
    devono rispettare lo stesso contratto degli score degli operatori.

    Il punto delicato: la fonte della verita' resta UNA — il
    validatore del server (`models.frequency_track`). Qui non si
    riscrivono le regole: si estraggono i numeri dal file JS
    dell'esperienza e si passano al validatore VERO. Se un valore
    fosse fuori range, `clean_layer` lo riporterebbe dentro — e la
    differenza fra quello che abbiamo scritto e quello che il
    contratto accetta e' il difetto. Nessuna seconda implementazione.
    """

    @staticmethod
    def _layers_di(js: str):
        """I livelli scritti in un protocollo integrato, come dizionari."""
        blocchi = re.findall(r"layer\(\{(.*?)\}\)", js, re.S)
        fuori = []
        for b in blocchi:
            d = {}
            for chiave, valore in re.findall(r"(\w+):\s*'([^']*)'", b):
                d[chiave] = valore
            for chiave, valore in re.findall(r"(\w+):\s*(-?[\d.]+)\b", b):
                d[chiave] = float(valore)
            # alMinuto(8) → 8/60 Hz: la conversione e' del protocollo
            for chiave, valore in re.findall(r"(\w+):\s*alMinuto\(([\d.]+)\)", b):
                d[chiave] = float(valore) / 60.0
            fuori.append(d)
        return fuori

    def test_ogni_livello_di_calm_passa_il_validatore_senza_essere_corretto(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_layer, DURATION_MIN, DURATION_MAX

        js = CALM.read_text()
        durata = float(re.search(r"CALM_DURATA = (\d+)", js).group(1))
        assert DURATION_MIN <= durata <= DURATION_MAX, \
            f"durata {durata}s fuori dal contratto ({DURATION_MIN}-{DURATION_MAX})"

        livelli = self._layers_di(js)
        assert len(livelli) == 3, f"letti {len(livelli)} livelli invece di 3"
        for l in livelli:
            pulito = clean_layer(dict(l), durata)
            assert pulito is not None, f"{l.get('name')}: rifiutato dal contratto"
            # il validatore riporta i valori fuori range DENTRO il range:
            # se ha dovuto correggere qualcosa, quel qualcosa era fuori
            for campo in ("carrier", "f0", "f1", "gain", "start", "end"):
                if campo not in l:
                    continue
                assert abs(pulito[campo] - l[campo]) < 0.01, \
                    (f"{l.get('name')}: {campo} = {l[campo]} e' stato "
                     f"riportato a {pulito[campo]} dal contratto")
            assert pulito["method"] == l["method"]
            assert pulito.get("curve", "lin") == l.get("curve", "lin")

    def test_lo_score_intero_e_accettato(self):
        """Non solo i livelli: la forma completa, con le fasi."""
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_score, PHASES_MAX, LAYERS_MAX

        js = CALM.read_text()
        durata = float(re.search(r"CALM_DURATA = (\d+)", js).group(1))
        fasi = [{"t": float(t), "name": n}
                for t, n in re.findall(r"\{ t: (\d+), name: '(\w+)' \}", js)]
        score = {
            "score_version": 1, "duration_sec": durata,
            "fade_in_sec": float(re.search(r"CALM_FADE_IN = (\d+)", js).group(1)),
            "fade_out_sec": float(re.search(r"CALM_FADE_OUT = (\d+)", js).group(1)),
            "layers": [dict(l) for l in self._layers_di(js)],
            "phases": fasi,
        }
        pulito = clean_score(score)
        assert pulito is not None, "lo score di CALM non e' uno score valido"
        assert len(pulito["layers"]) == len(score["layers"]), \
            "il contratto ha scartato un livello"
        assert len(pulito["phases"]) == len(fasi) <= PHASES_MAX
        assert len(pulito["layers"]) <= LAYERS_MAX
        assert pulito["duration_sec"] == durata

    def test_la_regola_vale_per_OGNI_esperienza_registrata(self):
        """La guardia non e' su CALM: e' sul registro. Una futura
        esperienza che scivolasse fuori dai limiti verrebbe fermata
        qui, senza che nessuno debba ricordarsi di aggiungere un test."""
        registro = (FQ / "content" / "esperienze.js").read_text()
        ids = re.findall(r"^  (\w+): \{", registro, re.M)
        assert ids, "il registro non elenca nessuna esperienza"
        for eid in ids:
            protocollo = FQ / "content" / f"{eid}.js"
            assert protocollo.exists(), \
                f"{eid}: registrata ma senza protocollo in content/{eid}.js"
            js = protocollo.read_text()
            assert "duration_sec:" in js and "layers:" in js, \
                f"{eid}: il protocollo non ha la forma di uno score"
            # il tetto di casa per le esperienze integrate
            m = re.search(r"_DURATA = (\d+)", js)
            assert m and int(m.group(1)) <= 600, \
                f"{eid}: le esperienze integrate durano al massimo 10 minuti"


class TestArchitettura:
    """esperienza → protocollo (dati) → synth → ponte → audio."""

    def test_nessuno_si_fabbrica_un_motore(self):
        """Dal consolidamento il motore lo chiama l'ASCOLTO condiviso,
        non la pagina: ne' l'uno ne' l'altra si fabbricano nodi audio."""
        assert "startPreview" in _codice(ASCOLTO), \
            "l'ascolto non usa il motore di casa"
        for f in (PAGINA, ASCOLTO):
            src = _codice(f)
            for vietato in ("createOscillator", "createGain", "createAnalyser",
                            "OscillatorNode"):
                assert vietato not in src, f"{f.name} si fabbrica {vietato}"
        # e la pagina non conosce piu' il motore: e' il senso dello step
        assert "startPreview" not in _codice(PAGINA), \
            "la pagina e' tornata a parlare col motore"

    def test_il_player_e_condiviso_e_sottile(self):
        """Dodici gesti duplicati sono diventati uno solo. L'ascolto
        resta React-free, come il motore del Lab."""
        src = _codice(ASCOLTO)
        importati = re.findall(r"^import .*?from '([^']+)'", src, re.M)
        assert all(i.startswith('../engine/') for i in importati), \
            f"l'ascolto importa altro dalle primitive di casa: {importati}"
        assert "react" not in src.lower()
        for gesto in ("creaPonte", "ponte.avvia()", "ctx.resume()",
                      "schermoAcceso()", "sorvegliaContesto", "startPreview",
                      "schermoLibero()", "rilascia()", "ctx?.close()"):
            assert gesto in src, f"l'ascolto ha perso il gesto {gesto}"

    def test_il_protocollo_e_dati_e_riusa_la_fabbrica(self):
        """`layer()` e' UNA in tutta Aurya Sound: CALM la importa invece
        di copiarsela."""
        src = _codice(CALM)
        assert "import { layer } from './protocolli'" in src
        protocolli = (FQ / "content" / "protocolli.js").read_text()
        assert "export const layer" in protocolli
        # e CALM non entra nel menu preset degli operatori: e'
        # un'esperienza finita, non un preset del Lab. Si guarda il
        # CODICE (il commento che spiega il prestito non conta).
        assert "CALM:" not in _codice(FQ / "content" / "protocolli.js")

    def test_il_suono_esce_dal_ponte(self):
        src = _codice(ASCOLTO)
        assert "creaPonte" in src and "sbocco: ponte.nodo" in src, \
            "senza ponte, su iPhone il suono se ne va col silenziatore"
        assert "ctx.destination" not in src

    def test_nessun_orologio_pilota_il_suono(self):
        """L'unico setInterval sta nella pagina e scrive solo quanto
        manca: se si fermasse, il suono continuerebbe identico."""
        assert "setInterval" not in _codice(PAGINA), \
            "la pagina si e' rifatta un orologio suo"
        src = _codice(ASCOLTO)
        assert src.count("setInterval") == 1, \
            "l'ascolto ha piu' di un orologio"
        blocco = src.split("setInterval")[1][:400]
        for vietato in ("imposta(", "frequency", "gain.", "startPreview"):
            assert vietato not in blocco, \
                f"l'orologio della pagina tocca il suono ({vietato})"

    def test_il_sipario_e_lo_schermo(self):
        """Le due regole di casa prima di ogni suono: le
        controindicazioni e lo schermo che non si spegne."""
        src = _codice(PAGINA)
        assert "useSafetyGate" in src and "guard(avvia)" in src, \
            "si puo' partire senza passare dal sipario"
        # lo schermo e la sorveglianza vivono nell'ascolto condiviso
        asc = _codice(ASCOLTO)
        assert "schermoAcceso()" in asc and "schermoLibero()" in asc
        assert "sorvegliaContesto" in asc, \
            "se il contesto audio muore, nessuno se ne accorge"
        assert "onPerso" in _codice(PAGINA), \
            "la pagina non dice all'utente perche' il suono si e' fermato"

    def test_si_spegne_tutto_uscendo(self):
        assert "smonta()" in _codice(PAGINA), "uscendo la pagina non smonta nulla"
        asc = _codice(ASCOLTO)
        assert "live.stop()" in asc and "ctx?.close()" in asc, \
            "il contesto audio resta aperto"

    def test_la_pagina_prende_i_dati_dal_registro(self):
        src = _codice(PAGINA)
        assert "esperienza('calm')" in src, "la pagina non usa il registro"
        for duplicato in ("360", "CALM_DURATA", "costruisciCalm"):
            assert duplicato not in src, \
                f"la pagina tiene una copia di «{duplicato}»"
        reg = _codice(REGISTRO)
        assert "costruisci: costruisciCalm" in reg and "durata: CALM_DURATA" in reg


class TestLaPromessa:
    """CALM racconta cosa si sente, non cosa succede nel corpo."""

    @pytest.mark.parametrize("bugia", [
        "sistema nervoso", "cortisolo", "riequilibr", "guarisc", "cura ",
        "terapeutic", "theta", "onde cerebrali", "resetta", "scientificamente",
    ])
    def test_nessuna_affermazione_fisiologica(self, bugia):
        for f in (CALM, PAGINA):
            testo = f.read_text().lower()
            assert bugia not in testo, f"{f.name}: promette «{bugia}»"

    def test_il_binaurale_e_descritto_per_quello_che_si_sente(self):
        # il testo va a capo nel JSX: si confronta a spazi normalizzati
        testo = " ".join(PAGINA.read_text().split())
        assert "battito lento fra i due canali" in testo
        # la vecchia riga («senza cuffie resta intera») era ottimista:
        # le tre portanti di CALM stanno TUTTE sotto la soglia
        # dell'altoparlante del telefono (500 Hz, engine/altoparlante.js)
        assert "senza cuffie l'esperienza resta intera" not in testo
        assert "dall'altoparlante di un telefono i toni gravi si perdono" in testo
        assert "non sono obbligatorie" in testo, \
            "chi non ha le cuffie non deve sentirsi escluso"

    def test_l_avviso_cuffie_e_quello_di_casa(self):
        """La soglia non si ricopia: la decide engine/altoparlante.js,
        come per il player degli operatori."""
        asc = _codice(ASCOLTO)
        assert "avvisoCuffieScore(score)" in asc
        assert "500" not in asc, "la soglia e' stata ricopiata nel player"
        pag = _codice(PAGINA)
        assert "calm-avviso-cuffie" in pag and "solo-telefono-block" in pag, \
            "l'avviso non compare, o compare anche dove non serve"

    def test_dice_cosa_non_e(self):
        testo = " ".join(PAGINA.read_text().split())
        assert "Non è una terapia e non promette effetti" in testo


class TestLaPorta:
    """La rotta, la shell, la sitemap — le trappole gia' pagate due volte."""

    def test_rotta_lazy_prima_del_catchall(self):
        src = (FRONTEND_SRC / "App.js").read_text()
        assert 'lazy(() => import("./features/frequenze/calm/CalmPage"))' in src
        assert src.index('path="/sound/calm"') < src.index('path="/sound/*"'), \
            "il catch-all mangia CALM"

    @pytest.mark.asyncio
    async def test_la_shell_conosce_calm(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from routers import seo_shell as shell
        meta = await shell.resolve_meta("/sound/calm")
        assert meta is not None, "la shell non conosce /sound/calm: 404"
        assert not meta.get("noindex")
        assert meta["canonical"].endswith("/sound/calm")
        corpo = meta.get("content_html", "").lower()
        assert "calma" in corpo and "cuffie" in corpo
        for bugia in ("terapia:", "cortisolo", "theta"):
            assert bugia not in corpo

    def test_sitemap_e_landing(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/calm" in seo
        landing = (FQ / "SoundLandingPage.js").read_text()
        assert 'data-testid="sld-calm"' in landing
        assert landing.index("sld-calm") < landing.index("fqz-landing-cats"), \
            "CALM deve stare prima delle schede: si ascolta prima di studiare"

    def test_niente_tecnicismi_davanti_all_utente(self):
        """Chi ascolta non deve vedere il Laboratorio."""
        src = PAGINA.read_text()
        for tecnico in ("Hz", "FFT", "spettro", "sweep", "forma d'onda",
                        "binaurale", "portante", "ampiezza"):
            assert tecnico not in src, f"la pagina mostra «{tecnico}»"


class TestNessunaRegressione:
    """CALM non deve aver toccato niente di cio' che gia' funzionava."""

    def test_il_lab_e_intatto(self):
        lab = FQ / "lab"
        for f in ("motore.js", "quadro.js", "Oscilloscopio.jsx",
                  "Spettro.jsx", "Spettrogramma.jsx", "Generatore.jsx"):
            assert (lab / f).exists()
        # e nessun file del Lab conosce CALM
        for f in lab.glob("*.js*"):
            assert "calm" not in f.read_text().lower(), f"{f.name} sa di CALM"

    def test_i_sei_protocolli_esistenti_sono_al_loro_posto(self):
        src = (FQ / "content" / "protocolli.js").read_text()
        for nome in ("Dormire", "Meditare", "Rilassare", "Concentrare",
                     "Elaborare", "Energizzare"):
            assert f"  {nome}: {{" in src, f"protocollo {nome} sparito"

    def test_il_motore_non_e_stato_toccato(self):
        """La specifica aveva verificato che le API bastavano: se il
        motore e' cambiato per CALM, la verifica era sbagliata."""
        synth = (FQ / "engine" / "synth.js").read_text()
        assert "calm" not in synth.lower()
