# Frequenze by Aurya — Voce guidata nel compositore (ciclo FV)

*19 agosto 2026 — analisi e piano. Stato: PROPOSTO (in attesa del go).*

## 1. Il concetto: che cos'è la «voce da sogno» di SomaBreath

Non è un effetto solo: è una **catena di 4 ingredienti**, e il carattere onirico
nasce dal contrasto tra i primi due.

1. **Voce intimissima davanti** — microfono vicino (bassi caldi da prossimità),
   compressione decisa (la voce non ha picchi né cali: è un flusso costante),
   low-cut sotto ~90 Hz. Da sola = voce ASMR, "nell'orecchio".
2. **Coda enorme e scura dietro** — riverbero lungo (3–6 s) ma con due
   accorgimenti che lo separano dal "riverbero del bagno":
   - **pre-delay 60–120 ms**: la coda parte DOPO la parola, così la voce resta
     intelligibile e il riverbero diventa un alone, non una sbavatura;
   - **coda filtrata** (taglio sopra ~5 kHz): il riverbero è morbido, "lontano".
3. **Eco filtrata** — delay 350–500 ms, feedback 25–40 %, con un lowpass nel
   loop: ogni ripetizione è più scura della precedente → la parola "si
   allontana nel sogno". Spesso ping-pong destra/sinistra.
4. **Doubling leggero** (opzionale) — una copia della voce detunata di ±5–10
   cents, 10–20 ms di ritardo, panpottata: l'effetto "angelico/largo".

**Perché sembra un sogno**: il cervello riceve due indizi spaziali
contraddittori — la voce dry dice "è a 10 cm da te", la coda dice "sei in uno
spazio di 50 metri". Quella impossibilità fisica è esattamente la cifra
onirica. Riverbero da solo (senza compressione né pre-delay) dà "voce nella
chiesa vuota", non "voce nel sogno".

### Mappa Web Audio (tutto nativo, zero librerie)

| Ingrediente | Nodo |
|---|---|
| Compressione | `DynamicsCompressorNode` (thr −24, ratio 4–6, att 3 ms, rel 250 ms) |
| EQ | `BiquadFilter` highpass 90 Hz + highshelf −3 dB @ 8 kHz sul wet |
| Riverbero | `ConvolverNode` con **IR sintetica generata** (rumore stereo a decadimento esponenziale, filtrato) — pochi KB di codice, nessun file |
| Pre-delay | `DelayNode` 90 ms prima del convolver |
| Eco | `DelayNode` 420 ms + `GainNode` feedback 0.3 + `BiquadFilter` lowpass 3 kHz nel loop |
| Doubling | secondo `BufferSource` con `detune` ±8 cents + delay 15 ms + pan |

### Preset per l'operatore (semplici, nominati)

- **Naturale** — solo pulizia (compressore + EQ). Per istruzioni pratiche.
- **Sogno** — la catena SomaBreath completa. Il default per le meditazioni.
- **Tempio** — riverbero grande senza eco (mantra, spazi sacri).
- **Sussurro** — compressione forte, riverbero corto: intimità pura.

Un solo controllo in più: **«Quanto effetto»** (slider dry/wet 0–100). Nessun
altro parametro esposto: i numeri giusti vivono nei preset.

## 2. Architettura

### La voce è l'eccezione dichiarata alla «ricetta non audio»

Le frequenze restano sintesi (score JSON). La voce è per forza un file — ma è
piccolo: opus/aac parlato ≈ 0.25 MB/min. 10 minuti ≈ 2.5 MB, meno di una foto.

- **Solo registrazione in-app** (getUserMedia + MediaRecorder), **niente
  upload di file** — coerente con la decisione founder del 18/8 (l'operatore
  non importa audio suo; la voce la registra qui, è sua per definizione).
- Storage: `uploads/voice/{org_id}/{uuid}.(webm|m4a)` + collection
  `voice_assets` **org-scoped** (id, org_id, title, duration_sec, size,
  mime, created_at). Quota per org (100 MB, clip ≤ 10 min) → niente abusi.
- I clip («spezzoni») sono riusabili: lo stesso asset può stare in N punti
  della timeline (N layer che puntano allo stesso asset_id).

### Score v2 (additivo, mai degradare)

Nuovo layer `kind:'voice'`:
```json
{ "kind": "voice", "asset_id": "…", "name": "Respira…", "start": 120,
  "end": 150, "gain": 0.9, "fx": "dream", "fx_amount": 0.6 }
```
- `clean_score` accetta v1 e v2; uno score si salva v2 SOLO se contiene voce.
- Player/engine rifiutano version > 2 (regola esistente).
- ⚠ I filtri del motore oggi dicono `kind !== 'audio'` → un layer voice
  cadrebbe nel ramo neuro. Vanno portati a `kind === 'neuro'` (guardia).

### Motore

- `engine/voicefx.js` (JS puro, come il resto): `buildVoiceChain(ctx, preset,
  amount)` → { input, output } e `makeImpulse(ctx, seconds, tone)` per l'IR.
- **Anteprima**: buffer del clip → catena live → bus sessione. Lo stop ferma
  la sorgente e lascia decadere la coda (naturale).
- **Export**: pre-render di ogni clip CON effetto in un OfflineAudioContext
  dedicato (durata clip + 8 s di coda) → il buffer "wet" entra nel mixer
  audio esistente di render.js come una base qualsiasi. Niente code troncate
  ai bordi dei chunk da 20 s.
- **Ducking deterministico**: opzione di sessione «Abbassa le basi sotto la
  voce» — conoscendo le finestre dei clip, il gain delle basi scende di 7 dB
  con rampe dolci (1 s) dentro quelle finestre. Non serve sidechain: è
  scritto nello score, quindi identico in anteprima, export e player.

### Player pubblico

Le tracce pubblicate con voce funzionano già per architettura: il player
risolve gli asset (come le basi), applica la stessa catena live. I file voce
sono serviti da /uploads come le basi. Diritti: la voce è dell'operatore che
pubblica — clausola nei Patti chiari (stessa onda della clausola basi).

## 3. UI in Crea — «il leggio»

Pannello **Voce** accanto alla libreria Suoni:

1. **REC** → chiede il microfono, registra (visualizzatore di livello,
   timer). Stop → il clip appare in «I tuoi spezzoni» con nome editabile
   ("Respira dal naso", "Rilassa le spalle"…). Consiglio in microcopy: cuffie
   se registri mentre la sessione suona.
2. Ogni spezzone: ▶ anteprima (con selettore preset per provare l'effetto),
   **+ alla sessione** → nasce un layer voice al punto del cursore.
3. In timeline i layer voce hanno la loro corsia col colore dedicato e
   l'icona 🎙; trascinabili come gli altri; per-layer: preset, quantità
   effetto, volume.
4. Registrazione "sopra la sessione": premi REC mentre la sessione suona in
   cuffia → parli a tempo sui passaggi. (v1: registrazione semplice; il
   REC-durante-ascolto è già possibile di fatto, basta non bloccarlo.)

## 4. Fasi

- **FV1 — Backend voce**: voice_assets + endpoints org-scoped (POST
  registrazione multipart, GET lista, DELETE), quota, score v2 con
  clean_layer voice, indici. Guardie: org-scoped sempre, quota, v1 intatto.
- **FV2 — Motore**: voicefx.js (4 preset + IR sintetica), filtri kind
  aggiornati, anteprima live in startPreview, pre-render wet nell'export,
  ducking. Guardie: engine puro, nessun kind ignoto nel ramo neuro.
- **FV3 — UI Crea**: pannello Voce (REC/spezzoni/+ sessione), corsia voce in
  timeline, selettore preset + quantità, microcopy cuffie. Guardie: nessun
  type="file" nuovo (solo registrazione).
- **FV4 — Filiera completa**: player pubblico con voce, ducking ovunque,
  E2E (registra → 2 punti → pubblica → ascolta da anonimo), batteria.

## 5. Rischi e paletti

- **Safari**: MediaRecorder produce mp4/aac (non webm) → si conserva il
  container originale, decodeAudioData li legge entrambi. Da testare.
- **Permesso microfono negato** → stato UI chiaro, mai crash.
- **Punto architettura da non tradire**: la voce NON passa da Mongo (solo
  metadati), NON è nella libreria di piattaforma (è per-org), NON introduce
  upload di file arbitrari.
- **Peso pubblico**: una meditazione 20 min con 15 min di voce ≈ 4 MB di
  file voce — accettabile; le frequenze restano a costo zero.
