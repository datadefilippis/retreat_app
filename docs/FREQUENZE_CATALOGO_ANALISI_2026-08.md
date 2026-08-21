# Espandere il catalogo delle frequenze — analisi (21 agosto 2026)

Richiesta del founder: analizzare le frequenze di Aurya Sound (non le
basi audio caricate), capire cosa manca e come renderle più dinamiche —
«ci sono frequenze che vanno su e giù, quasi un'onda» — valutando gli
effetti e come aggiungerle a livello di struttura.

Riferimenti: `engine/synth.js`, `content/biblioteca.js`,
`content/protocolli.js`, `models/frequency_track.py`,
`docs/FREQUENZE_PLAN_2026-08.md`.

---

## 1. Cosa c'è oggi, esattamente

**Il motore** conosce 6 metodi — binaurale, isocronico, monoaurale,
bilaterale, soffio (rumore rosa modulato), tono puro — 2 timbri (puro /
caldo, cioè fondamentale + 2ª e 3ª armonica deboli) e 3 curve del
battito: costante, naturale (esponenziale), a gradini. Limiti: battito
0,2–60 Hz (bilaterale max 3), portante 20–2000 Hz, 24 livelli, 2 ore.

**Il catalogo** ha **28 schede**: 6 bande cerebrali, 16 «altre
frequenze» (40 Hz, Schumann e armoniche, 4 accordature, 9 Solfeggio) e
6 metodi. Ogni scheda porta un grado di evidenza A/B/C e un testo che
distingue con onestà il fenomeno dalla sua attribuzione.

**Il fatto rilevante**: di quelle 28, **14 sono toni puri fermi** e
altre 10 hanno battito costante. Solo 4 schede portano un movimento nei
dati — Delta 4→2,5 · Theta 8→5 · Beta 15→18 · Binaurale 10→6.

## 2. La scoperta: il movimento c'è già, ma nessuno lo sente

In `FrequenzePage.js:561` l'ascolto di una scheda fa così:

```js
const fval = cfg.method === 'tone' ? (cfg.carrier ?? 432) : (cfg.f0 ?? 10);
```

Prende **solo `f0`** e lo tiene fisso. `f1`, la curva e il «respiro»
(la micro-oscillazione ±8% ogni 26 s di `envAt`) esistono nel motore e
funzionano **solo dentro una sessione composta**, mai in Esplora.

Quindi: la scheda Delta *dice* «da 4 a 2,5 Hz», e suona 4 Hz fissi
finché non la fermi. La sensazione di staticità che hai notato non
nasce dal catalogo — nasce da tre righe del player delle schede.

**È il primo intervento da fare, ed è piccolo.** Prima di aggiungere
qualsiasi frequenza nuova: far sentire il movimento che abbiamo già.

## 3. Cosa manca davvero

### A. Il movimento come forma, non come rampa

Oggi una curva va **da un valore a un altro, una volta sola**. Manca
esattamente ciò che descrivi: un valore che **va su e giù e torna**.

- **curva `wave`** — il battito oscilla tra `f0` e `f1` con un periodo
  (es. 40 s): 8 → 6 → 8 → 6, all'infinito. Un livello smette di essere
  una discesa e diventa una marea. Serve un campo nuovo (`period`), è
  l'aggiunta più piccola con l'effetto percettivo più grande.
- **deriva della portante** — oggi la portante è un chiodo. Farla
  respirare di ±0,3% con periodo lento (30–60 s) toglie il carattere
  «sintetizzatore» ai bordoni lunghi, senza cambiare la nota.
- **`breath` nelle schede** — già scritto e già usato nelle sessioni:
  basta accenderlo in Esplora.

### B. Metodi che non abbiamo

1. **Coppia disaccordata** (`pair`) — due portanti vicine sullo stesso
   canale (es. 111 e 111,4 Hz): il battito nasce **nell'aria**, come tra
   due campane. Diverso dal monoaurale (che somma due toni a metà
   volume) perché qui i due toni restano pieni e il battimento è lento
   e corposo. È il suono che la gente associa alle campane tibetane, e
   oggi non lo sappiamo fare.
2. **Rumore colorato** (`noise` con colore) — abbiamo solo il rosa. Il
   **marrone** (più cupo, meno acuti) è il fondo notturno per
   eccellenza; il **bianco** serve come riferimento. Il filtro rosa
   esiste già in `pinkBuf`: aggiungere il marrone è poche righe.
3. **Soffio filtrato in movimento** (`surf`) — rumore + filtro
   risonante che sale e scende lentamente: è **l'onda del mare**, il
   suono più richiesto in assoluto nelle pratiche, e oggi possiamo
   ottenerlo solo caricando un file.
4. **Bordone armonico** (`drone`) — fondamentale + quinta + terza in
   intonazione naturale (1 : 3/2 : 5/4). Un tono solo è povero; tre
   parziali giuste sono un armonium.
5. **Discesa infinita** (`shepard`) — l'illusione Shepard-Risset: un
   suono che sembra scendere per sempre. È psicoacustica documentata,
   non misticismo, ed è perfetta per le pratiche di «lasciar andare».

### C. Le schede che mancano — e qui cambia il discorso

Le 9 Solfeggio sono tutte grado C: attribuzioni tradizionali, e la
biblioteca lo dice chiaramente. **Aggiungerne altre dello stesso tipo
non migliora l'offerta**: allunga l'elenco senza alzare la qualità.

C'è invece una categoria intera che manca ed è **l'unica dove
l'evidenza è dalla nostra parte**:

> **Ritmi del corpo** — non frequenze che «agiscono» sul corpo, ma
> ritmi *del* corpo su cui il suono fa da metronomo.

- **Respiro lento — 0,1 Hz (6 respiri al minuto).** Qui l'evidenza non
  riguarda il suono: riguarda **il respiro**. La respirazione lenta e
  ritmata ha effetti misurabili e ben documentati sulla variabilità
  cardiaca e sul tono autonomico. Il suono è il metronomo che rende la
  pratica facile — ed è onesto dirlo così: *l'effetto è della pratica,
  noi diamo il passo*. È il contenuto più solido che possiamo
  aggiungere, e non ce l'abbiamo. (Nota tecnica: 0,1 Hz è sotto il
  minimo attuale di 0,2 Hz — va abbassato `BEAT_MIN`.)
- **Passo del cuore a riposo — 1 Hz (60 bpm)** e **cadenza del
  cammino — 2 Hz (120 passi/min)**. La sincronizzazione del movimento
  a un ritmo udibile è un fenomeno robusto (la stimolazione uditiva
  ritmica è usata seriamente in riabilitazione del cammino). Come
  scheda: grado B, con la stessa cautela di sempre.
- **Onda del mare — 0,1–0,2 Hz**, che è poi il metodo `surf` di sopra:
  il ritmo naturale più vicino al respiro lento.

Aggiungerei anche, tra le bande, **Mu (8–13 Hz sensomotorio)** — è
l'unica banda classica assente e completa il quadro con SMR.

E due schede **di mestiere**, che oggi mancano e servono più di dieci
Solfeggio: **«Scegliere la portante»** (perché 400 Hz per il binaurale
e 180 per gli altri, e cosa cambia) e **«Rosa, marrone, bianco»** (che
differenza fa davvero un rumore).

## 4. Il punto sugli «effetti terapeutici»

Vale la pena dirlo netto, perché è il patto che regge la biblioteca:
**non aggiungerei nemmeno una promessa terapeutica nuova.** Sul suono
in sé le evidenze restano eterogenee, e la biblioteca oggi lo scrive
con onestà rara nel settore — è un pezzo di identità, non una cautela
legale.

La strada per «offrire un'esperienza migliore» non è dichiarare più
effetti: è **avere più suono vero**. Un mare che sale e scende, un
bordone che respira, un passo che accompagna il respiro sono
esperienze migliori *in quanto suono*, e non richiedono di promettere
nulla. Dove l'evidenza c'è — respiro lento, ritmo e movimento — è
sull'attività della persona, e va raccontata così.

## 5. Come aggiungerle, strutturalmente

Il contratto dello score è: si evolve **solo aggiungendo versioni**, e
una ricetta sale di versione **solo se usa la roba nuova** (è già così
per la voce, v2). Quindi:

| cosa | dove | versione |
|---|---|---|
| schede nuove (Mu, ritmi del corpo, mestiere) | `content/biblioteca.js` — solo contenuto | nessuna |
| movimento nelle schede (f0→f1, curva, respiro) | `FrequenzePage.js` + `startCardLive` | nessuna |
| `BEAT_MIN` 0,2 → 0,05 Hz | `models/frequency_track.py` | nessuna (allarga un range) |
| curva `wave` + campo `period` | `synth.js` (`freqAt`), modello, editor | **v3** |
| metodi `pair`, `surf`, `drone`, `shepard` + colore del rumore | `synth.js` (le due sintesi), `METHODS`, editor | **v3** |

Le due sintesi vanno tenute gemelle: `neuroSample` (render esatto,
campione per campione) e il grafo WebAudio dell'anteprima. Ogni metodo
nuovo si scrive **due volte** — è già così oggi, ed è il motivo per cui
render e anteprima suonano identici. Chi aggiunge un metodo e ne scrive
solo una fa un bug che si sente solo all'export.

Le schede sono dati (`cfg`), quindi ogni metodo nuovo diventa
immediatamente una o più schede ascoltabili senza toccare la UI.

## 6. Cosa suggerisco, in ordine

**Onda 1 — far sentire quello che c'è già** (mezza giornata)
Le schede onorano `f0→f1`, la curva e il respiro. Quattro schede
smettono di mentire, e tutto il catalogo diventa vivo. Nessuna versione
nuova, nessun contenuto nuovo.

**Onda 2 — la marea** (una giornata)
Curva `wave` + periodo, deriva lenta della portante. È la risposta
diretta a «frequenze che vanno su e giù»: da qui ogni scheda esistente
può diventare un'onda.

**Onda 3 — i ritmi del corpo** (una giornata)
`BEAT_MIN` a 0,05 Hz, nuova categoria con respiro lento (0,1 Hz),
cuore (1 Hz), cammino (2 Hz). Il contenuto migliore che possiamo
aggiungere, e l'unico con evidenza vera — dichiarata onestamente come
evidenza *della pratica*.

**Onda 4 — il timbro** (1,5 giornate)
Rumore marrone, coppia disaccordata, bordone armonico, soffio filtrato
(il mare). Qui il catalogo smette di suonare «di sintesi».

**Onda 5 — Shepard e le schede di mestiere** (mezza giornata)
La discesa infinita e i due articoli su portante e rumori.

Totale ~4,5 giornate. Le prime due sono indipendenti da tutto e si
possono fare subito; la 3 tocca un limite del modello; 4 e 5 aprono la
v3 dello score.
