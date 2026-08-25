# Aurya Sound Lab — analisi, architettura e piano (V1)

26 agosto 2026. Richiesta: evolvere Aurya Sound aggiungendo il **Lab**
(Generator, Oscilloscope, Spectrum, Sweep) senza toccare la biblioteca
educativa. Questo documento è la FASE 1-4 chiesta dal founder: nessuna
riga di codice è stata modificata.

---

# FASE 1 — Analisi dell'esistente

## La mappa di Aurya Sound oggi

```
/sound                → SoundLandingPage      (landing editoriale)
/sound/visual         → VisualPage            (strumento visual, three.js)
/sound/*              → FrequenzePage         (viste interne via URL:
                          esplora | impara | crea | tracce)
```

`FrequenzePage` (126 KB di sorgente) instrada le viste con la mappa
`PATH_VIEW = { esplora, crea, impara, tracce }`. La biblioteca vive in
`content/biblioteca.js` (le 4 categorie: bande cerebrali, altre
frequenze, ritmi del corpo, metodi — **non si toccano**), la guida in
`content/guida.js`, la sicurezza in `content/safety.js`.

## Cosa c'è già, pezzo per pezzo

| pezzo | cos'è | per il Lab |
|---|---|---|
| **`engine/ponte.js`** | l'unico sbocco del suono: `MediaStreamDestination → <audio playsinline>`. Nato da un bug vero su iPhone: il WebAudio collegato a `ctx.destination` è «suono di contorno», azzerabile dal silenziatore; un `<audio>` è «musica» e suona sempre | **RIUSO DIRETTO, ed è il pezzo più prezioso.** Senza il ponte, il generatore sarebbe muto su metà dei telefoni. È già singleton per contesto (`ctx._fqzPonte`) |
| **`visual/analisi.js` → `creaLettore`** | involucro dell'AnalyserNode: «si innesta su un grafo che esiste già e resta un ospite». Espone `analyser`, bande, spettro grezzo | **RIUSO DELLA FILOSOFIA, non del codice**: il lettore produce bande lisciate per i visual; il Lab vuole dati grezzi (float, non byte) e FFT più fine. Ma il principio — l'analisi è un osservatore agnostico rispetto alla sorgente — è esattamente l'architettura chiesta per il futuro microfono |
| **`engine/synth.js`** | il motore delle meditazioni: decine di oscillatori orchestrati da una ricetta. Contiene già i pattern giusti: declick 12 ms, `setPeriodicWave` (riga 538), inviluppi su `GainNode` | **RIUSO DEGLI IDIOMI, non del modulo**: synth è guidato dallo score delle meditazioni, il Lab è guidato dall'utente in tempo reale. Copiare i pattern (rampe anti-click, wiring osc→gain), non importare il file |
| **`visual/prototipo.js`** | già legge `getByteFrequencyData` + `getByteTimeDomainData` a ogni frame (righe 1350-51) e disegna | precedente interno: il loop rAF condiviso, la pausa su `visibilitychange` |
| **`frequenze.css`** | la palette del mondo Sound: `--ink #0C1618`, `--panel`, `--lamp` (oro), `--water`, `--mono` per i numeri, serif per i titoli | **RIUSO TOTALE**: il Lab veste `.fqz` e sembra nato lì. Niente estetica da software industriale: è già così |
| **`content/safety.js` + SafetyCurtain** | la cultura della sicurezza (cuffie, volume moderato, epilessia) | riuso della **riga di sicurezza**: un generatore a 20 kHz a piena ampiezza merita lo stesso rispetto delle meditazioni |
| **`SoundTopbar` / `SoundLandingPage`** | la navigazione del mondo Sound | i due punti dove appare la porta del Lab |
| **Registro rotte + shell SEO** | `sound` è già `pubblica` nel registro; `_SOUND_PAGES` dà meta per landing/esplora/impara e noindex a crea/tracce | aggiungere la voce `lab` (meta + eventuale corpo SSR): infrastruttura già pronta |

## Cosa NON esiste (da creare)

Un generatore comandato dall'utente, un oscilloscopio, uno spettro
disegnato, uno sweep. **Tutti e quattro i moduli sono nuovi** — ma
poggiano su fondamenta collaudate in produzione da settimane.

## Librerie

**Zero dipendenze nuove.** Web Audio API nativa (OscillatorNode,
AnalyserNode, AudioParam) + Canvas 2D. Three.js esiste ma NON serve al
Lab e non deve entrare nel suo chunk. Questo tiene fede al lavoro
appena fatto sul peso del bundle: il Lab sarà un chunk lazy autonomo.

## Verità tecniche verificate (per le richieste specifiche)

- **Precisione della frequenza**: `AudioParam.frequency` è un float a
  doppia precisione — `137.42 Hz` è nativo, nessun trucco.
- **Range**: il limite fisico è Nyquist (`sampleRate/2`, tipicamente
  22.05 o 24 kHz). UI 20 Hz–20 kHz; il motore accetta 1 Hz–Nyquist
  con clamp dichiarato.
- **La fase**: l'OscillatorNode nativo **non ha un parametro fase**.
  Si ottiene con `setPeriodicWave`: per la sinusoide è una rotazione
  dei coefficienti (banale ed esatta); per square/triangle/saw si
  costruisce la serie di Fourier con N armoniche (limitate a Nyquist,
  quindi anche anti-aliasate) e si ruota ogni armonica di `k·φ`.
  A fase 0 si usano i tipi nativi (purezza massima). Nota onesta: la
  fase di un oscillatore **solo** è inudibile — diventa reale con due
  sorgenti (interferenza, futura). La esponiamo perché l'architettura
  la chiede, dicendo nel pannello a cosa serve.
- **Lo sweep preciso**: non si fa da JavaScript (jitter del timer). Si
  usa `exponentialRampToValueAtTime` / `linearRampToValueAtTime`
  sull'AudioParam: **sample-accurate**, il browser calcola la rampa
  campione per campione. La UI mostra la frequenza corrente
  ricalcolando la STESSA formula dal tempo trascorso — display e
  suono non possono divergere.
- **La waveform visualizzata è il segnale vero**: l'oscilloscopio
  legge `getFloatTimeDomainData` dall'analyser collegato al segnale
  reale. Se il DAC riproduce X, il canvas disegna X. Nessuna grafica
  indipendente.

---

# FASE 2 — Architettura

## Il principio

Un motore solo, React fuori dal motore. Come `prototipo.js` e
`creaLettore`: il Lab vive in un modulo JS puro; React monta i
pannelli e legge lo stato, mai il contrario.

## Il grafo audio (V1, con le prese per il futuro)

```
        GENERATORE (OscillatorNode | PeriodicWave)
              │
        GainNode ampiezza (rampe declick 12ms — mai un click)
              │
              ├────────────► AnalyserNode  ◄─── [FUTURO: MediaStreamSource
              │               (osservatore)          dal microfono]
              │                   │
              │             ┌─────┴─────┐
              │        OSCILLOSCOPIO  SPETTRO
              │
        ponte.nodo (MediaStreamDestination)
              │
        <audio playsinline>  ──►  ALTOPARLANTE
                                      │
                              [FUTURO: sistema fisico
                               → microfono → analisi]
```

Tre proprietà che rendono possibile tutto il futuro elencato:

1. **L'analisi è un rubinetto, non un tubo** (lezione del ponte:
   «guarda, non trasporta»). `analisi.sorgente(nodo)` accetta
   *qualsiasi* AudioNode: oggi il generatore, domani un
   `MediaStreamSource` dal microfono, dopodomani un file. Oscilloscopio
   e spettro non sanno né chiedono da dove viene il segnale.
2. **Lo sweep è un evento, non un ciclo chiuso**: emette
   `onTick(freq, t)` — il futuro resonance finder si iscrive lì e
   confronta con la risposta del microfono. Il motore non cambia.
3. **Ogni esperimento è serializzabile**: lo stato del generatore è un
   oggetto piatto `{forma, freq, amp, fase, sweep}` — il futuro
   «experiment recording» è salvare quell'oggetto più i tick, non
   ristrutturare.

## I moduli (file nuovi, tutti sotto `features/frequenze/lab/`)

```
lab/
  motore.js        ← il cuore, React-free. creaLaboratorio(ctx) → API
  SoundLabPage.js  ← la pagina (route /sound/lab, chunk lazy)
  Generatore.jsx   ← pannello sorgente + sweep integrato
  Oscilloscopio.jsx← canvas dominio tempo (trigger incluso)
  Spettro.jsx      ← canvas dominio frequenze (picchi inclusi)
  lab.css          ← sopra la palette di frequenze.css
```

### `motore.js` — l'API

```
creaLaboratorio(ctx) → {
  generatore: {
    imposta({ forma, freq, amp, fase }),   // rampe, mai click
    avvia(), ferma(), stato(),
  },
  sweep: {
    avvia({ da, a, durataSec, scala }),    // 'log' (default) | 'lin'
    ferma(),
    corrente(),                             // {freq, t, quota}
    onTick(fn),                             // la presa del futuro
  },
  analisi: {
    analyser,                               // fftSize 8192
    tempo(bufFloat),  spettro(bufFloat),    // dati grezzi float
    sorgente(nodo),                         // input-agnostico (mic futuro)
  },
  spegni(),                                 // smontaggio pulito
}
```

Dettagli fissati ora perché costano zero ora e tanto dopo:
- **declick**: ogni cambio di ampiezza/forma passa da rampe 12 ms (la
  costante di casa); il cambio forma fa crossfade fra due oscillatori
  (uno muore, uno nasce) — cambiare `type` a caldo produce click.
- **fftSize 8192** → ~5.4 Hz/bin a 44.1k: abbastanza fine per leggere
  i picchi; con l'interpolazione parabolica (sotto) si scende a ~0.5 Hz.
- **un solo loop rAF** per entrambi i canvas, spento su
  `visibilitychange` (pattern AuryaMode): mai due disegnatori.

### Stato React

Un hook `useLaboratorio()` che possiede il ciclo di vita del motore e
espone `{stato, comandi}`. I canvas ricevono l'`analisi` via prop e si
disegnano da soli. Niente store globale: il Lab è una pagina, il
motore è suo.

---

# FASE 3 — UI/UX

## Dove vive il Lab

- **Route**: `/sound/lab` — pagina propria, chunk lazy, registrata in
  App.js PRIMA del catch-all `/sound/*`. Non una vista dentro
  FrequenzePage: quel file fa già quattro mestieri, e il Lab merita
  un modulo suo (anche per il peso).
- **Navigazione**: una card sulla landing di Sound («Il Laboratorio —
  genera, osserva, misura») + voce nel SoundTopbar. La biblioteca non
  si sposta di un pixel.
- **SEO**: voce `lab` in `_SOUND_PAGES` con meta oneste + corpo SSR
  breve (cos'è il laboratorio, cosa si può fare) + `/sound/lab` in
  sitemap-core. Indicizzabile: è contenuto vero, ed è una pagina che
  nessun concorrente italiano ha.

## Il banco (layout della pagina)

Non quattro strumenti sparsi: **un banco da laboratorio**, tutto
visibile, tutto collegato — l'architettura unica resa visibile.

```
┌────────────────────────────────────────────────┐
│  AURYA SOUND · LAB                             │
│  Genera un segnale. Osservalo. Misuralo.       │
│  ⚠ riga sicurezza: volume moderato, cuffie     │
├────────────────────────────────────────────────┤
│  GENERATORE                                    │
│  [∿] [⊓] [△] [◺]   forma (sagome disegnate)    │
│  437.00 Hz          readout mono grande,       │
│  ────────●────      editabile coi decimali,    │
│                     slider logaritmico          │
│  ampiezza ▁▂▃▄   fase ◔                        │
│  ( ▶ Genera )   [ Tono fisso | Sweep ]         │
│  └ se Sweep: da [20] a [2000] Hz in [30]s      │
│    scala [log|lin]  ▶ progress ──────          │
├──────────────────────┬─────────────────────────┤
│  OSCILLOSCOPIO       │  SPETTRO                │
│  (tempo)             │  (frequenze)            │
│  canvas, traccia     │  canvas, scala log,     │
│  stabile (trigger),  │  dB, picchi etichettati │
│  [freeze]            │  in Hz  [freeze] [log]  │
├──────────────────────┴─────────────────────────┤
│  «Cosa stai guardando» — 2 righe in linguaggio │
│  Aurya + link alla scheda della biblioteca     │
│  pertinente (40 Hz → scheda Gamma, ecc.)       │
└────────────────────────────────────────────────┘
```

Su mobile: le stesse card impilate.

**Il ponte Knowledge ↔ Lab** è la scelta di prodotto più importante:
la riga «cosa stai guardando» collega la frequenza attiva alla scheda
della biblioteca (`CAT_LINK` esiste già). Il Lab non è un giocattolo
accanto alla biblioteca: è la biblioteca che si fa toccare. E,
simmetricamente (fase futura), le schede potranno avere «provala nel
Lab».

**Il vestito**: palette `.fqz` (fondo `--ink`, pannelli `--panel`,
numeri in `--mono` color `--lamp`, tracce dei canvas in `--water` su
griglia appena accennata `--line-soft`). Le forme d'onda del selettore
sono piccole sagome disegnate, non icone da DAW. Un solo accento oro
per il readout della frequenza: il numero È il protagonista.

---

# FASE 4 — Piano di implementazione

### STEP 0 — Il telaio *(preparazione, piccolo)*
- **Crea**: route `/sound/lab` (lazy), `SoundLabPage` scheletro,
  `lab.css`, card sulla landing, voce topbar, meta shell + sitemap.
- **Verifica**: la pagina apre con l'estetica giusta; collaudo rotte
  verde; nessun peso aggiunto al main (chunk separato).
- **Rischi**: nessuno. È infrastruttura già rodata (registro, shell).

### STEP 1 — GENERATORE *(il cuore)*
- **Crea**: `lab/motore.js` (generatore + uscita via ponte + declick +
  crossfade cambio forma + fase via PeriodicWave), `Generatore.jsx`.
- **Difficoltà**: media. **Rischi**: (a) iOS/gesto — mitigato: il
  ponte esiste e `avvia()` va chiamato nel tocco, pattern collaudato;
  (b) la fase su square/tri/saw via serie di Fourier — se desse
  problemi, ripiego dichiarato: fase solo su sine in V1, il resto
  quando ci sono due sorgenti (dove la fase si sente davvero).
- **Funziona quando**: 440 Hz suona; `137.42` accettato e mantenuto;
  cambio forma senza click; stop pulito; suona su iPhone col
  silenziatore com'è; volume di default prudente (~0.3) e la riga di
  sicurezza c'è.
- **Come si verifica**: a orecchio + con lo smartphone; la verifica
  strumentale vera arriva con lo STEP 3 (lo spettro deve leggere
  440.0 ±1).

### STEP 2 — OSCILLOSCOPIO
- **Crea**: `Oscilloscopio.jsx` + il tap `analisi` in motore.js
  (`getFloatTimeDomainData`).
- **Il dettaglio che lo rende uno strumento**: il **trigger** a fronte
  di salita con isteresi — senza, la traccia scorre e sembra rotta;
  con, la sinusoide sta ferma come su un oscilloscopio vero. Più
  `freeze` per fermare l'immagine.
- **Difficoltà**: media-bassa. **Rischi**: stabilità del trigger su
  segnali rumorosi (per V1 il segnale è pulito; l'isteresi basta).
- **Funziona quando**: a 100 Hz si vedono ~4-5 cicli stabili nella
  finestra; la square mostra fronti ripidi; ampiezza a metà = traccia
  a metà; **è predisposto per il microfono**: il componente riceve
  `analisi`, non «il generatore».
- **Verifica misurabile**: contare i cicli a schermo e confrontarli
  con finestra/frequenza (2048 campioni a 44.1k = 46.4 ms → a 100 Hz
  → 4.6 cicli).

### STEP 3 — SPETTRO
- **Crea**: `Spettro.jsx` (scala log/lin, dB, floor −100).
- **Il dettaglio che lo rende uno strumento**: i picchi etichettati
  con **interpolazione parabolica** fra i bin — la FFT da sola ha
  passo ~5.4 Hz, con l'interpolazione il picco di 137.42 Hz si legge
  come `137.4`, non `137.9`. È ciò che rende il Lab credibile.
- **Difficoltà**: media. **Rischi**: la resa della scala log sul
  canvas (banding a bassa risoluzione) — si disegna per pixel, non
  per bin.
- **Funziona quando**: generi 440 → il picco etichetta `440.0 ±1`;
  generi una square → si vedono le armoniche dispari (3f, 5f, 7f) con
  ampiezze decrescenti; lo spettro funziona identico se la sorgente
  cambierà (stessa prova dell'oscilloscopio).
- **Verifica misurabile**: la fisica è il test — le armoniche della
  square sono matematica nota, o ci sono o lo spettro è rotto.

### STEP 4 — SWEEP / EXPLORER
- **Crea**: `sweep` in motore.js (rampe sample-accurate su AudioParam,
  `onTick`, formula condivisa motore↔UI) + la sezione Sweep nel
  Generatore.
- **Difficoltà**: media-bassa (il grosso è già in piedi).
  **Rischi**: pausa/ripresa a metà rampa (`cancelScheduledValues` +
  ripartenza dal valore corrente — da collaudare bene); durate
  lunghe con tab in background (il suono continua, il disegno si
  ferma: comportamento giusto, va solo dichiarato).
- **Funziona quando**: sweep log 20→2000 Hz in 30 s: **a 15 s il
  readout e il picco dello spettro dicono entrambi √(20·2000) =
  200 Hz** — è la prova regina, perché lega tutti e quattro i moduli
  in una sola misura; lo stop a metà non lascia code; `onTick` emette
  (il resonance finder futuro ha già la sua presa).

### Guardie (trasversali, come da casa)
- il motore è React-free (nessun import react in `lab/motore.js`);
- nessuna dipendenza nuova in package.json;
- il suono esce SOLO dal ponte (mai `connect(ctx.destination)`);
- l'analisi accetta una sorgente arbitraria (la firma è nel codice);
- three.js non entra nel chunk del Lab.

---

## Cosa resta fuori dalla V1, di proposito

Microfono, resonance detection, cimatica, Chladni, webcam, sensori,
registrazione esperimenti: **niente di tutto questo si costruisce
ora** — ma ogni punto dell'architettura sopra (analisi input-agnostica,
sweep a eventi, stato serializzabile) esiste perché quel futuro non
trovi porte murate.

*In attesa di approvazione per lo STEP 0+1.*
