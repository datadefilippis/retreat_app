# Ciclo TS — Tocco e Suono: consolidamento dell'esperienza Sound su mobile (21 agosto 2026)

Richiesta del founder: *«analizza tutta l'area sound da esplora a suoni
a crea e assicurati che funzioni correttamente e in maniera snella
multipiattaforma: strutturato, scalabile, user-friendly, niente bug e
inefficienze»* — includendo i punti 2 e 3 della diagnosi di «Crea muta»
(anteprima senza dissolvenza + attacco del motore), e ricordando che
l'obiettivo è **un'esperienza di suono profonda ed esperienziale**: il
piano è scritto con tre cappelli — architetto, UX, sound engineer.

---

## Parte I — L'analisi: cosa ho trovato, con le prove

### A. Il play in Crea è «muto» per matematica, non per guasto

Tre dissolvenze si **moltiplicano** all'avvio:

| fattore | valore | dove vive |
|---|---|---|
| dissolvenza d'ingresso della sessione | 10 s (default) | `fade_in_sec`, scelto dall'operatore |
| attacco del livello | fino a **12 s** | `envAt`, invisibile all'operatore |
| (rilascio del livello) | fino a **16 s** | idem, in coda |

Risultato misurato: **a 3 secondi dal play il volume è al 4,7%**, a 5 s
al 18,8%. Su un telefono, con portanti gravi già penalizzate
dall'altoparlante, i primi secondi sono silenzio percepito. Le schede
di Esplora salgono invece in 1,5 s: ecco l'asimmetria che il founder
sente come «da mobile Crea si comporta diversamente».

Da **sound engineer**: l'attacco di 12 s dentro il motore è un doppione
della dissolvenza di sessione — due responsabili per lo stesso gesto
musicale. L'anti-click richiede ~20 ms; la morbidezza musicale la deve
governare **una** manopola (quella visibile all'operatore), non due di
cui una nascosta.

### B. Il cursore non si sposta col dito: tutte le barre sono solo-click

- il **seekbar** di Crea: solo `onClick` (riga ~1601) — il **drag** col
  dito non fa nulla, e su mobile il gesto naturale È il drag;
- il **seekbar** della pagina pubblica: identico;
- il **righello** della linea del tempo: solo `onClick`;
- in più, ogni click su un punto = **riavvio completo del motore**
  (stop → resume → risoluzione layer → nuovo grafo): trascinare pixel
  per pixel sarebbe comunque impossibile con questo contratto;
- `dragX` (barre dei livelli, maniglie, fasi) usa pointer events —
  giusto — ma **senza `setPointerCapture` né `pointercancel`**: su
  touch un gesto interrotto dal sistema lascia i listener appesi.
- feedback visivo assente: il playhead esiste solo `{playing && …}` e
  il knob si muove solo col timer → se l'audio è inudibile (punto A),
  l'utente non ha **nessun** segnale che il play sia partito. «Non
  funziona» è la conclusione corretta dal suo punto di vista.

### C. Schede: il resume non è atteso

`audioCtx()` chiama `ctx.resume()` **senza await**; `toggleCard` è
sincrono. Su iOS, se il contesto è `suspended`/`interrupted` (dopo una
chiamata in arrivo, un cambio app), la scheda può dichiararsi «in
riproduzione» restando muta. `playSession` invece attende: i due
percorsi devono comportarsi allo stesso modo.

### D. Cose verificate SANE (non si toccano)

- registrazione voce: catena mime con fallback `audio/mp4` → Safari ok;
- cache delle basi per URL (`assets.js`): un download e un decode per
  base — il seek non ripaga il costo;
- `touch-action:none` presente su barre/maniglie/fasi/seekbar (i
  selettori con i commenti incastrati sono brutti ma **validi** — da
  riscrivere puliti, non da riparare);
- target touch ≥40 px e font 16px sugli input (anti-zoom iOS) già in CSS;
- anteprime del mondo Suoni via `<audio>` streaming: giuste così.

### E. Inefficienze/rischi da tenere d'occhio (misura minima ora)

- `bufferCache` è una Map **senza tetto**: AudioBuffer decodificati a
  48 kHz stereo pesano ~0,4 MB/s — una sessione con tre basi lunghe può
  superare i 200 MB su telefono. Non è il bug di oggi, ma è una bomba a
  orologeria mobile;
- nessun ascolto di `ctx.statechange`: dopo un'interruzione iOS la UI
  può mentire («suona» che non suona).

---

## Parte II — Il piano, in sei onde

### TS1 — Il volume che arriva (i punti 2 e 3, decisi dal founder)

**TS1a (punto 3)** — l'attacco del motore scende a misura anti-click
musicale: `envAt` da `min(12, span*0.3)` → **`min(1.5, span*0.1)`**, e
il rilascio da `min(16, span*0.3)` → **`min(2.5, span*0.15)`**, in
`envAt` (render e anello) **e** nel grafo live (`startPreview` usa
`min(6,…)/min(8,…)`: si allineano agli stessi numeri — oggi render e
live hanno perfino attacchi diversi tra loro).
*Conseguenze dichiarate:* cambia l'audio anche del pubblicato (deciso
dal founder); la guardia sulla parità attacco/margine dell'anello va
aggiornata — è nata apposta per obbligare questo ricontrollo, il
margine di 30 s resta abbondante.

**TS1b (punto 2)** — in Crea l'anteprima **salta le dissolvenze di
sessione**: `startPreview(..., { fades: false })` solo dal compositore.
Si ascolta per verificare; la traccia pubblicata entra ed esce morbida
come composta. Una riga sotto il player lo dice: *«Anteprima senza
dissolvenze — nella traccia pubblicata entra in 10 s ed esce in 20 s»*
(coi numeri veri dell'operatore).
*Insieme:* il play in Crea suona **entro ~0,3 s**.

### TS2 — Il cursore che si sposta col dito

- **drag sul seekbar** (Crea + pagina pubblica): pointer events con
  `setPointerCapture`; durante il drag il knob e il tempo **seguono il
  dito subito** (aggiornamento ottimistico, il motore non si tocca);
  al **rilascio** un solo riavvio del motore sul punto scelto. Il tap
  secco resta come oggi;
- stesso gesto sul **righello** della linea del tempo;
- `dragX` diventa robusto: `setPointerCapture` + `pointercancel`
  (niente listener appesi dopo un gesto interrotto);
- in modalità continua/anello il drag comanda l'`<audio>` direttamente
  (già istantaneo, nessun riavvio).

### TS3 — Vedere che sta suonando

- nel createbar e nel player pubblico, quando `playing`, un **respiro
  visivo** sul pulsante (animazione CSS sobria, già nel linguaggio del
  mondo scuro): l'occhio sa che il suono c'è anche quando l'orecchio
  non ancora;
- il playhead della linea del tempo visibile anche in pausa (fermo
  sull'ultimo punto), non solo `{playing && …}`;
- **avviso cuffie anche in Crea** (solo mobile, riuso di
  `avvisoCuffieScore` sullo score del compositore): oggi c'è in Esplora
  e sulla pagina pubblica, ma manca proprio dove il founder l'ha
  cercato.

### TS4 — Il motore onesto su iOS

- `toggleCard` diventa async e **attende** `ctx.resume()` (come già fa
  `playSession`): mai più una scheda «in riproduzione» muta;
- listener su `ctx.statechange`: se il sistema sospende il contesto
  (chiamata, cambio app), la UI passa a ferma invece di mentire;
- tetto alla `bufferCache`: quando supera ~60 MB si svuotano le voci
  non usate dallo score corrente (misura minima, non un LRU).

### TS5 — Crea a schermo stretto: passata visiva

Con viewport 375 px, vista per vista (linea del tempo, controlli
livello, leggio voce, protocolli, barra fissa): verifica di overflow,
sovrapposizioni e bersagli, e correzione puntuale di ciò che emerge.
*(Nota onesta: la verifica dal vivo di Crea richiede un account
operatore nel browser; la farò con l'org demo in locale.)*

### TS6 — Guardie e verifica finale

- guardie nuove: `fades:false` esiste SOLO nel percorso del
  compositore; attacchi identici fra render e live; drag presente sui
  seekbar; `pointercancel` gestito; avviso cuffie in Crea; tetto cache;
- aggiornamento coerente delle guardie che fissavano i numeri vecchi
  (`min(12…)`, margine anello);
- suite intera + giro visivo mobile di **tutte** le viste (Esplora,
  Impara, Suoni, Crea, pagina pubblica, landing) con screenshot;
- doc di chiusura col prima/dopo misurato (volume a 1/3/5 s).

---

## Ordine e dipendenze

TS1 → TS3 (il feedback ha senso quando il volume è vero) → TS2 →
TS4 → TS5 → TS6. Nessuna migrazione, nessun cambio server: è tutto
frontend + guardie. Deploy solo a go esplicito, come sempre.

## Cosa NON faccio (e perché)

- niente riscrittura del compositore: l'impianto (score→motore) è
  sano, i difetti sono ai bordi (dissolvenze, gesti, feedback);
- niente drag «live» che riavvia il motore a ogni pixel: il contratto
  resta un riavvio per gesto;
- niente aumento del sample rate del continuo (22050): questione
  separata già documentata in ANELLO_FREQUENZE_AT4 §6, da decidere a
  parte.


---

## ESEGUITO (21 agosto, sera) — esiti

| onda | esito |
|---|---|
| TS1a | `attackRelease` unica verità in synth.js (1,5/2,5 s); render, live e anello la importano. Prima render e live avevano perfino numeri diversi (12/16 vs 6/8) |
| TS1b | `fades:false` solo dal compositore; nota coi numeri veri sotto il player; il player pubblico e il render non conoscono l'opzione (guardie) |
| TS2 | `SeekBar.jsx` condiviso (capture, movimento ottimistico, UN commit al rilascio, pulizia su cancel/lost); righello a gesto pointer; `dragX` con capture+pointercancel |
| TS3 | respiro visivo sul play (rispetta prefers-reduced-motion), playhead visibile in pausa, avviso cuffie in Crea |
| TS4 | resume atteso anche sulle schede, `sorvegliaContesto` (statechange → UI onesta), tetto 60 MB alla cache buffer che non tocca mai le basi in ascolto |
| TS5 | giro visivo Crea a 375px con org demo: niente overflow orizzontale, barra impilata, nota e avviso al posto giusto |
| TS6 | +14 guardie (classe TestToccoESuonoTs), aggiornate le guardie MD/margine ai nuovi ancoraggi |

**Misura del risultato (volume dopo il play in Crea)**: prima 1,5% a 2s
e 4,7% a 3s; ora ~74% a 1 secondo, 100% a 1,5 s.

**Verificato dal vivo (viewport mobile, org demo)**: protocollo caricato,
play immediato con stato «suona», avviso cuffie in Crea (180 Hz
presentato), nota dissolvenze coi numeri veri, drag del cursore →
commit unico e motore ripartito dal punto scelto. Nota d'ambiente: il
mouse sintetico del pannello resta «premuto» quando il tool va in
timeout — un gesto per il browser ancora in corso, che nessun
lostpointercapture può chiudere; non riproducibile con un dito vero.

**Resta al founder**: la conferma con un telefono fisico (suono al
play in Crea, drag del cursore, avvisi) — l'unico banco che qui non
posso simulare fino in fondo.
