# Aurya Mode — visualizzatore audio-reattivo: analisi e piano (21 agosto 2026)

Idea del founder: le meditazioni pubblicate hanno una **visualizzazione
che si muove col suono**, in stile Aurya; e la stessa cosa diventa uno
**strumento a sé** dove chiunque carica una traccia (o usa microfono /
audio del PC), sceglie un tema, e **esporta un video** per Instagram e
YouTube. Vincolo: gira **sul dispositivo dell'utente**, costo nostro
vicino a zero.

**Risposta corta: è fattibile, il costo per noi è davvero ~zero, e il
browser ha già tutto. La parte difficile non è tecnica: è artistica.**

---

## 1. Fattibilità tecnica — verificata, non supposta

Ho interrogato il browser su `aurya.life`. Tutto ciò che serve **c'è**:

| serve per | API | esito |
|---|---|---|
| leggere il suono (spettro, bande, picchi) | `AnalyserNode` | ✅ |
| disegnare scene dense | `WebGL2` | ✅ |
| filmare la tela | `canvas.captureStream()` | ✅ |
| registrare video+audio | `MediaRecorder` | ✅ |
| **MP4/H.264 nativo** (Instagram non accetta WebM) | `video/mp4;codecs=avc1` | ✅ **supportato** |
| esportare più veloce del tempo reale | `WebCodecs / VideoEncoder` | ✅ disponibile |
| audio del PC | `getDisplayMedia` | ✅ |
| microfono | `getUserMedia` | ✅ (già usato per la voce) |

Il pezzo che temevo — l'MP4 — **non richiede ffmpeg.wasm** (25 MB di
WebAssembly): il browser sa già produrlo. È la differenza fra una
funzione elegante e una zavorra.

*Nota onesta: la velocità di codifica NON l'ho misurata — il contesto
JS del mio pannello non tiene vivi i timer fra una chiamata e l'altra.
Va misurata su una macchina vera prima di promettere tempi.*

## 2. Il costo per noi: davvero ~zero

| voce | costo |
|---|---|
| analisi del suono | CPU dell'utente |
| rendering | GPU dell'utente |
| codifica video | CPU/GPU dell'utente |
| la traccia caricata dall'utente | **non ci arriva mai** |
| il video esportato | resta sul suo dispositivo |
| **nostro costo di banda** | solo il chunk JS, ~100–250 KB, caricato una volta e poi in cache |

Non è solo economia: **non ricevere le tracce degli utenti ci toglie
anche un problema di diritti d'autore**. Chi carica un brano protetto
lo elabora a casa sua; noi non lo ospitiamo, non lo distribuiamo, non
lo vediamo. Questa è una scelta di architettura che vale quanto quella
di costo — e va detta esplicitamente nell'interfaccia.

## 3. La cosa che devo dirti sui mockup

Le immagini che mi hai mandato sono **concept art**, non schermate di
un visualizzatore reale. Sono splendide e danno benissimo la
direzione, ma un motore in tempo reale nel browser **non produrrà
quelle immagini identiche**: quelle hanno la densità e la libertà di
un rendering non vincolato a 60 fotogrammi al secondo.

Cosa è realistico, e comunque bellissimo: campi di particelle che
respirano col suono, onde e mandala che si aprono sui picchi, nebulose
per accumulo di bagliori, spettri tridimensionali. Il livello di
riferimento onesto è quello dei bravi visualizzatori WebGL, non quello
di un rendering d'artista.

**Il mio consiglio è di considerarlo un vantaggio**: se puntiamo a
imitare quelle immagini, perdiamo. Se puntiamo a *una firma visiva
riconoscibile come Aurya*, vinciamo — perché lì non c'è concorrenza.

## 4. La domanda di marca che nessuna API risolve

I mockup sono **arcobaleno**: viola, ciano, magenta, oro. Aurya è
**oro (#C9B37E), verde acqua (#66B79C), petrolio scuro** — e il tuo
stesso lavoro di marca dice «criterio invisibile», sobrietà, niente
spettacolo gratuito.

Sono due strade, e vanno scelte prima di scrivere una riga:

- **A — arcobaleno**: più «wow» sui social, ma Aurya diventa
  indistinguibile da mille visualizzatori;
- **B — tavolozza Aurya** (oro/verde acqua su petrolio, con
  variazioni): meno esplosivo al primo sguardo, ma **ogni video
  esportato è pubblicità riconoscibile di Aurya**. Uno guarda un reel e
  sa da dove viene.

Consiglio **B come identità di casa**, con 2–3 temi alternativi più
accesi per chi vuole. Il nome «Aurya Mode» dei tuoi mockup funziona
proprio se quel modo *ha una faccia sua*.

## 5. Come si innesta in ciò che esiste già

### Nelle meditazioni
Il suono è sintetizzato nel browser: basta **innestare un
`AnalyserNode`** nel grafo del motore. Nessun file da scaricare in
più, nessuna latenza: la visualizzazione legge esattamente ciò che
esce dagli altoparlanti.

**Un'attenzione vera**: collegare un `<audio>` (l'ascolto continuo)
alla catena WebAudio, su iOS, lo riporta sotto il tasto silenzioso e
può rompere la riproduzione a schermo bloccato. Ma il conflitto è solo
apparente: **se guardi, lo schermo è acceso**. Guardare e ascoltare a
schermo bloccato sono esperienze mutuamente esclusive per natura — si
attiva l'una o l'altra.

### Come strumento a sé
Una pagina dentro il mondo Sound (`/sound/visual`): scegli la
sorgente (file, microfono, audio del PC), scegli il tema, guardi, e se
vuoi registri. Il file non lascia mai il dispositivo.

## 6. Architettura proposta — la disciplina che già usiamo

Tre strati separati, come per il motore audio (dove analisi e resa
sono gemelli testati):

1. **lettura** (`analisi.js`): dall'`AnalyserNode` a un oggetto onesto
   — bande (bassi/medi/alti), energia, picchi, tonalità dominante —
   con lisciatura temporale. **Un solo posto** dove si decide cosa
   significa «il suono adesso»;
2. **temi** (`temi/*.js`): ogni modo è una funzione pura
   `disegna(ctx, lettura, tempo)`. Aggiungerne uno non tocca nulla
   d'altro. È lo stesso contratto delle schede della biblioteca;
3. **uscita** (`filma.js`): tela + audio → MediaRecorder → MP4, nei
   formati 9:16 (Instagram) e 16:9 (YouTube).

Gli stessi princìpi che ci hanno risparmiato guai stanotte: una verità
sola per ogni fatto, e guardie che difendono i punti che si romperebbero
in silenzio.

## 7. Complessità onesta, in onde

| onda | cosa | difficoltà | note |
|---|---|---|---|
| **AV1** | strato di lettura + **un** tema (il mandala Aurya) dentro il player delle meditazioni, opzionale | media | è il cuore: se questo è bello, il resto è ripetizione |
| **AV2** | pagina a sé con le tre sorgenti (file, microfono, audio PC) e 3–4 temi | media | nessun caricamento sul server |
| **AV3** | **esportazione video** MP4 nei due formati | **alta** | il punto più insidioso: tempi reali, memoria, differenze fra browser |
| **AV4** | WebGL per i temi densi + freni automatici (meno particelle su dispositivi lenti) | alta | senza freni, un telefono si scalda e rallenta |
| **AV5** | rifinitura artistica, preset, coerenza di marca | media | è qui che si decide se sembra Aurya o un giocattolo |

**Stima complessiva realistica: 6–10 giornate di lavoro**, di cui una
buona parte artistica più che tecnica. AV1 da solo — la meditazione
che si guarda mentre suona — è **1–2 giornate** ed è già un pezzo di
prodotto che nessuno dei concorrenti ha.

## 8. I rischi veri, con la loro misura

| rischio | quanto è serio | rimedio |
|---|---|---|
| **l'export è in tempo reale**: 10 minuti di video = 10 minuti d'attesa | alto per l'esperienza | dirlo chiaramente e proporre clip brevi (30–60 s è il formato social); WebCodecs più avanti per andare più veloci |
| **memoria**: un video lungo cresce in RAM prima di essere salvato | alto su telefono | tetto onesto sulla durata (es. 3 min), e export **da desktop** in prima battuta |
| **la batteria**: WebGL + audio insieme scaldano | medio | freni automatici, e la visualizzazione **non parte da sola**: la si chiede |
| **differenze fra browser** su MediaRecorder/MP4 | medio | provare le capacità *prima* di offrire il pulsante, come già facciamo per l'ascolto continuo |
| **aspettativa vs realtà** dopo i mockup | **alto** | prototipo di AV1 da guardare insieme prima di investire nel resto |
| **diritti d'autore** delle tracce caricate | basso per noi | non ci arrivano mai; una riga che lo dice, e la responsabilità resta di chi carica |

## 9. Cosa NON farei

- **niente rendering sul server**: annullerebbe l'unico motivo per cui
  questa funzione è gratis;
- **niente ffmpeg.wasm** finché l'MP4 nativo basta: 25 MB per un
  problema che non abbiamo;
- **niente galleria dei video sul nostro sito**: ospitare video
  significa banda e diritti — esattamente ciò che abbiamo appena
  evitato. I video li pubblica l'utente, dove vuole;
- **niente promesse sui tempi di export** prima di averli misurati su
  macchine vere.

## 10. Il passo che propongo

**Un prototipo di AV1**, misurabile e guardabile: lo strato di lettura
e *un* tema — il mandala Aurya che respira col suono — dentro il player
di una meditazione, come pulsante «Guarda». Una-due giornate.

Poi lo guardiamo insieme e decidiamo con gli occhi, non con le
parole: se quel primo tema emoziona, il resto è costruzione; se non
emoziona, abbiamo speso due giorni invece di dieci.

**Prima però serve la tua risposta su §4**: arcobaleno o Aurya? È la
scelta che orienta tutto il resto, e non è tecnica.


---

## AV1 COSTRUITO (21 agosto, notte)

Risposta del founder su §4: **stile pulito di Aurya con colori
trascendenti** — con la giusta correzione che non tutti i mockup erano
arcobaleno (il secondo e il terzo sono già oro su nero, mandala e
geometria sacra: quelli *sono* Aurya).

La tavolozza non è stata inventata: è la famiglia di accenti che il
mondo Sound ha già in `frequenze.css` — oro `#C9B37E`, verde acqua
`#66B79C`, **viola tenue `#9B8BC4`** (il terzo colore «trascendente»
era già lì), su petrolio `#0C1618`, con l'osso `#E9E4D9` per i nuclei.

### Cosa c'è ora

| pezzo | file | cosa fa |
|---|---|---|
| lo strato che **ascolta** | `visual/analisi.js` | 5 bande d'orecchio (non aritmetiche), energia, dominante, colpo; ogni grandezza lisciata col **suo** tempo |
| il **tema** | `visual/temi/mandala.js` | tre corone che ruotano a velocità diverse, alone, onda del colpo, scintille, cuore |
| la **tela** | `visual/AuryaMode.jsx` | fa girare il tema, coi freni |
| l'**innesto** | `startPreview({ uscita })` | l'analizzatore sta *fra* motore e altoparlante |
| l'**invito** | `PublicFrequencyPage` | «✦ Guarda il suono», mai automatico |

### Come si muove, e perché

Il **raggio** respira coi bassi (il corpo del suono è lì), i **petali**
ruotano coi medi (la parte che canta), le **scintille** nascono sugli
alti (l'aria), un colpo apre un'**onda** che si allarga. Su una
meditazione senza percussioni non pulsa: **respira** — voluto, la
scena accompagna, non intrattiene.

### I freni, perché una scena bella che scalda il telefono è sbagliata

DPR limitato a 2 (a 3x sarebbero nove volte i pixel per zero guadagno
percepito); il disegno **si ferma** quando la pagina non è visibile;
`prefers-reduced-motion` dà una scena più lenta, non un rifiuto.

### Le due regole difese dalle guardie (18)

1. **la visualizzazione non tocca MAI il suono**: la tela non conosce
   `AudioContext`, il motore non si fa un analizzatore, e in ascolto
   continuo la tela non compare (su iOS portare un `<audio>` dentro
   WebAudio lo rimetterebbe sotto il tasto silenzioso);
2. **i colori sono quelli della marca**: una guardia rifiuta qualunque
   colore fuori dalla famiglia, e un'altra vieta l'`hsl()` girevole —
   il trucco più comune dei visualizzatori, ed esattamente ciò che
   renderebbe Aurya indistinguibile da mille altri.

### Verificato dal vivo

Non solo «la tela esiste»: ho letto i **pixel** al centro della scena
mentre la meditazione suonava — 6.400 pixel illuminati su fondo nero,
luminosità media 52. Sta davvero leggendo l'audio, non disegnando a
vuoto. Screenshot: mandala d'oro con alone viola, cuore d'osso.

**Suite: 4.275 verdi.**

### Il passo dopo, quando lo vorrai

AV2 (pagina a sé con file/microfono/audio del PC e altri temi) e AV3
(esportazione video MP4). Ma prima: **guardalo**. Se il mandala
emoziona, il resto è costruzione.
