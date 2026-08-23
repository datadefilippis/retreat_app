# IL MASTER — piano profondo: un mix pesa quanto una canzone (23/8/2026)

Founder: «alla fine è una canzone da 27 minuti… non è possibile che
sia così pesante. Se ogni operatore fa mix così grandi non scaliamo.
Mi aspetto che un mix alla fine pesi quanto una traccia standard.»

Ha ragione, e il criterio è esattamente quello. Questo piano lo
realizza alla lettera.

## 1 · La diagnosi dal principio primo

Una meditazione PUBBLICATA è **congelata**: la ricetta non cambia mai
più. Eppure il player la **ri-sintetizza da capo a ogni ascolto**:
scarica le basi (12 file per «Rinascita»), le decodifica tutte in PCM
(~700 MB di RAM anche dopo i tappeti/ritagli), accende il motore e
rifà il mix dal vivo. È l'architettura giusta per il COMPOSITORE — in
Crea si modifica, serve la sintesi viva — ed è puro spreco per
l'ASCOLTATORE, che riceve sempre lo stesso identico suono.

La prova che il sistema lo sa già: per l'ascolto a schermo bloccato
(`engine/continuo.js`) **già oggi renderizziamo il file intero della
sessione** — ma sul telefono dell'ascoltatore, a ogni richiesta, in
WAV 22 kHz da ~158 MB, con minuti di attesa e un tetto di 30 minuti.
Il lavoro giusto, fatto dal dispositivo più debole, nel momento
peggiore, nel formato più pesante, ogni volta.

## 2 · L'idea: il render si fa UNA volta, alla pubblicazione

Quando l'operatore preme **Pubblica**, il suo browser (il computer
dell'operatore, non il telefono di chi ascolta) renderizza il mix
completo offline e lo carica come **master**: un normale file audio
compresso. Da quel momento:

- **chi ascolta riceve UN file in streaming**, come su Spotify:
  27 min a 192 kbps ≈ **37 MB di rete**, partenza immediata (Range),
  **RAM da streaming (~pochi MB)** — non 700;
- l'ascolto a schermo bloccato è GRATIS (è un media element: la
  macchina Media Session di continuo.js si semplifica, il render
  sul telefono sparisce, il tetto dei 30 minuti pure);
- **la roulette del decoder iOS sparisce per gli ascoltatori**: un
  <audio> che suona un file è il caso più rodato del web — niente
  spezzoni, niente fallback, niente ponte;
- il server resta quasi immune: **zero CPU** (il render è del client
  dell'operatore), solo storage.

Il motore c'è già tutto: `render.js` (renderPcm — sintesi offline
esatta dello score, nato per l'export operatore) + `lamejs` (MP3,
già vendored). Non si scrive un renderer: si sposta QUANDO gira.

## 3 · I numeri

| | oggi (dopo tappeti) | col master |
|---|---|---|
| rete per ascolto | ~60 MB (12 richieste) | ~37 MB (1 file, streaming) |
| RAM ascoltatore | ~700 MB residenti | ~pochi MB (streaming) |
| partenza | attesa decode di 12 basi | immediata (Range) |
| schermo bloccato | render WAV sul telefono (minuti, ≤30′) | nativo, gratis |
| iOS | fallback e casi limite | il caso più rodato del web |
| server | zero CPU | zero CPU + ~37 MB disco/traccia |

Disco VPS misurato: 40 GB liberi (+20 recuperabili di build cache) →
~1.900 master. Sfogo futuro già in casa: la Storage Box Hetzner dei
backup. **Scala.**

## 4 · Le onde

**M1 — Il render alla pubblicazione.** In Crea, «Pubblica» diventa:
renderPcm dell'intero score (44.1 kHz stereo) → MP3 192 kbps con
lamejs (in un Web Worker, con barra di progresso onesta: ~1–3 minuti
una tantum) → upload. Il publish si completa solo a master caricato;
in caso di errore la traccia resta in bozza con messaggio chiaro.
192 kbps è la scelta: le code di riverbero delle meditazioni si
mangiano i 128.

**M2 — Storage e modello.** Endpoint org-scoped `POST
/frequencies/{id}/master` (tetto 64 MB, solo owner, solo su publish);
file in `uploads/masters/{track_id}.mp3` — directory **NON servita
staticamente** (vedi M3); campi `master_url`, `master_at`,
`master_bytes` sul documento traccia. Il re-publish rigenera e
sovrascrive: un master per traccia, mai orfani.

**M3 — Il cancello resta sovrano.** Un file statico pubblico sarebbe
«il cancello demolito da un'altra porta» (continuo.js docet). Quindi:
- il master si scarica via backend con **verifica dello sblocco**
  (la prova unica del cerchio, SB1) e consegna **X-Accel-Redirect**:
  nginx serve i byte (Range compreso, zero CPU python), il backend
  fa solo da portiere;
- per i non sbloccati, alla pubblicazione si genera anche
  **anteprima.mp3 (90 s, ~2 MB, pubblica)**: l'assaggio diventa
  leggerissimo pure lui.

**M4 — Il player pubblico suona il master.** Se `master_url` esiste:
<audio> + Media Session (titolo, copertina, comandi sul blocco
schermo); il visual Aurya Mode prende l'analyser da
`createMediaElementSource` — stessa analisi, sorgente diversa. Le
tracce SENZA master (vecchie pubblicazioni) restano sul percorso
attuale: **zero rotture**, i tappeti C1/C2 restano come rete di
sicurezza e per Crea.

**M5 — La migrazione dell'esistente.** «Rinascita» e le altre già
pubblicate: bottone «Rigenera il master» in Crea (di fatto un
re-publish). Poche tracce oggi: si fa a mano col founder.

**M6 — Guardie e collaudo.** Il master non si serve mai statico
(guardia su nginx/route); publish senza master non esiste; il player
preferisce il master; l'anteprima è ≤90 s. Collaudo iPhone del
founder: partenza, seek, blocco schermo, consumo dati reale.

## 5 · Cosa NON cambia

- **Crea**: sintesi viva per comporre — è il suo mestiere.
- **Lo score resta la verità** della composizione: il master è un
  derivato, rigenerabile sempre (ri-publish). Nessun lock-in.
- **Le basi e i tappeti**: servono a Crea e al fallback.
- **/sound/visual**: già locale, non c'entra.

## 6 · Rischi, detti chiaro

- Il master diventa il **suono ufficiale**: minime differenze dal
  live di oggi (già vero e accettato per export e continuo).
- Il publish costa ~1–3 minuti di attesa all'operatore (con
  progresso): il prezzo giusto pagato dalla persona giusta una volta
  sola.
- lamejs va messo in un Worker per non congelare la pagina durante
  l'encode (dettaglio di M1).
- Disco: misurato e con sfogo; da tenere d'occhio nel pannello.
