# Piano — Refinement di Crea: tempi, voce, taglio (24/8/2026)

Quattro osservazioni del founder componendo un mix vero. Tre sono
difetti reali (li ho trovati nel codice, riga per riga), uno è una
funzione che manca. Nessuno richiede di toccare l'architettura.

---

## 1 · «Entra a / esce a» ogni tanto non prende quello che scrivo

### La diagnosi (FrequenzePage, riga ~1219)

```jsx
<input defaultValue={fmt(l.start)} key={`in${l.id}-${Math.round(l.start)}`}
       onBlur={...clamp silenzioso...} />
```

Tre difetti che si sommano, e spiegano esattamente il sintomo:

1. **Campo non controllato con chiave arrotondata.** L'input vive di
   `defaultValue`; si aggiorna solo quando React lo RIMONTA, cioè
   quando cambia `key` — che usa `Math.round(l.start)`. Sposti la
   barra di mezzo secondo? La chiave non cambia, il campo mostra un
   numero vecchio. Scrivi `2:10.4` e il valore diventa 130.4? La
   chiave non cambia → il campo resta com'era.
2. **Il clamp è silenzioso**: `Math.max(0, Math.min(v, l.end - 0.5))`.
   Se scrivi un valore che si scontra col compagno (entra dopo esce),
   viene cambiato senza dire niente: «mi appariva il valore sbagliato».
3. **Solo `onBlur`**: premere Invio non conferma nulla. Se dopo aver
   scritto premi Ascolta, il campo non ha mai perso il fuoco → il
   valore digitato **non viene mai applicato**. È il «non mi prendeva
   ciò che inserivo», alla lettera.

### La cura (TF)

- Campo **controllato con bozza locale**: mentre scrivi comanda il tuo
  testo; alla conferma il valore entra nel modello e il campo si
  riallinea al valore vero (nessuna chiave-fantasma, nessun rimonto).
- **Invio conferma**, Esc annulla, il blur conferma come oggi.
- **Il clamp parla**: se il valore viene corretto (fuori dalla
  sessione, o incrocia il compagno) lo dice nella riga di stato, con
  la ragione — mai una correzione muta.
- **Testo tollerante**: `90`, `1:30`, `1.30`, `01:30` sono la stessa
  cosa. Oggi `parseT` è già gentile: si estende e si dichiara nel
  titolo del campo.
- **Più semplice ancora**: accanto ai due campi, i due gesti che si
  usano davvero — «⟵ da qui» (porta l'inizio al punto in cui sei con
  l'ascolto) e «fin qui ⟶». Chi compone ragiona per punti d'ascolto,
  non per numeri.

Rischio: nullo per il resto (il modello non cambia, cambia solo il
modo in cui il campo scrive dentro `patchLayer`).

---

## 2 · La voce parte bassa e poi sale

### La diagnosi (voicefx.js → `cleanVoiceBuffer`, riga ~209)

Non è una dissolvenza voluta: è il **gate anti-fruscio** della
pulizia automatica.

```js
const gateThr = floor * 2;                 // il doppio del fondo
for (w) if (rms[w] < gateThr) gains[w] = 0.12;      // −18 dB
for (w) gains[w] = max(gains[w], gains[w-1] * 0.85); // risalita a scalini
```

Una voce che attacca **dolcemente** (com'è naturale iniziare a
parlare) sta sotto la soglia per qualche decina di millisecondi:
quelle finestre vengono abbassate di 18 dB e poi risalgono del 15%
ogni 10 ms. Il risultato è precisamente «inizia bassa e il volume si
alza». Si somma un declick di 20 ms e la dissolvenza di 120 ms
all'ingresso della catena (quelli sì, voluti e impercettibili).

La pulizia fa anche cose buone (taglia i silenzi ai bordi, toglie il
fruscio nelle pause, normalizza il volume): non va spenta d'ufficio —
va messa **in mano all'autore**.

### La cura (VP)

Nel leggio, sotto la registrazione, **«Pulizia della voce»** con tre
scelte oneste:

| scelta | cosa fa |
|---|---|
| **Naturale** (nuovo default per i take nuovi) | normalizza il volume e toglie i silenzi ai bordi. **Nessun gate**: l'attacco resta com'è |
| **Pulita** (comportamento di oggi) | anche il gate sulle pause: per stanze rumorose |
| **Grezza** | nessun ritocco: la registrazione così com'è |

- Il campo vive **sull'asset voce** (`clean_mode`, accanto a
  `trim_start/trim_end` che già esistono): si decide una volta,
  vale ovunque quel take sia usato — anteprima, master, export.
- **Le tracce già pubblicate non cambiano suono**: senza il campo si
  legge `pulita`, cioè esattamente ciò che si sente oggi.
- Il gate «Pulita» va comunque addolcito: risalita più morbida e
  soglia meno aggressiva (il -18 dB secco è troppo per una voce che
  respira).

---

## 3 · Una base che non voglio tutta: il taglio

### La diagnosi

La **voce** ha già il taglio (`trim_start`/`trim_end` sull'asset,
`clip_in` sul layer). Le **basi** no: in `synth.js` il layer audio fa
`src.start(when, startOffset)` dove `startOffset` è solo il seek
della sessione. Non esiste modo di dire «parti dal decimo secondo».

### La cura (TG)

- Nuovo campo di layer **`clip_in`** (secondi da saltare dentro la
  base), già previsto dal vocabolario della voce: stesso nome, stessa
  semantica. Validato nel modello (0 ≤ clip_in < durata base).
- **Motore**: `synth.js` e `render.js` sommano `clip_in` all'offset —
  poche righe, gli stessi due punti dove già vive per la voce. Per i
  loop, il giro riparte dal punto scelto (modulo la durata).
- **Rete della banda**: chi taglia i primi 10″ di una base di 30′ non
  deve scaricare 30′ → il calcolo dello spezzone parte da `clip_in`
  (per i tappeti pre-prodotti resta tutto com'è: sono già corti).
- **UI**, nella riga della base (accanto a «in loop»): **«parte da»**
  con lo stesso campo tempo del punto 1 — un vocabolario solo. E il
  gesto rapido: **«taglia fin qui»** mentre stai ascoltando.
- Chi non lo tocca non vede differenza: `clip_in` assente = 0.

---

## 4 · Semplicità: un vocabolario solo per il tempo

Oggi in Crea convivono tre modi di scrivere un tempo (i campi della
riga, il punto di partenza in /sound/visual, la durata). Il refinement
li unifica in **un solo componente** «campo tempo» (bozza locale,
Invio conferma, correzione parlante, formati tolleranti). Meno codice,
meno bug possibili, e la stessa sensazione ovunque.

---

## Onde e ordine

- **TF** — il campo tempo che non tradisce (+ «da qui / fin qui»).
  *È il bug che ti ha fatto perdere tempo: prima di tutto.*
- **VP** — la pulizia voce in mano all'autore (default Naturale sui
  take nuovi, «Pulita» per l'esistente: nessun suono cambia da solo).
- **TG** — il taglio delle basi (modello → motore → banda → UI).
- **TU** — il campo tempo unico, riusato ovunque (pulizia finale).

Ogni onda: guardie nella suite + prova viva in Crea. Nessuna
migrazione dati; tutti i campi nuovi sono opzionali e assenti =
comportamento di oggi.

## Cosa NON si tocca

Il motore del suono (sintesi, ponte, master, tappeti), la
pubblicazione, il privilegio del comporre, il player pubblico. Il
refinement vive dentro Crea e nel vocabolario dei layer.
