# Visual in Crea — analisi di integrazione (ciclo VC)

**Data**: 22 agosto 2026 · **Stato**: analisi, in attesa di decisioni founder
**Richiesta**: «che sia l'utente che crea le meditazioni a scegliere la forma
che più gli piace e tutti i parametri e i colori […] mentre ascolta osserva i
visual, li modifica, ci parla sopra col microfono, e quando salva la bozza o
pubblica salva esattamente tutte le informazioni. L'userfriendly dei processi
è al primo posto.»

---

## 1. Cosa cambia di concetto

Finora il visual era in due stanze separate:

| Dove | Chi decide l'aspetto | Cosa si salva |
|---|---|---|
| `/sound/visual` | chi guarda (stanza personale) | localStorage del suo browser |
| Meditazione pubblica | noi (preset Aurya fisso, AV5) | niente |

Il ciclo VC introduce la terza figura, quella giusta: **l'autore**. La scena
diventa parte della composizione — come le dissolvenze, come la voce. Ne
seguono due conseguenze che ordinano tutto il resto:

1. **La scena si salva nella ricetta.** Lo score è già la filosofia giusta:
   un documento di byte, non di megabyte. Le impostazioni del visual sono
   ~150 byte di JSON. Costo server: zero, per costruzione.
2. **La regola dell'uniformità si estende agli occhi.** In Crea si sente
   esattamente ciò che sentirà chi ascolta (decisione founder, 21/8, dopo la
   ritrattazione di TS1b). Da VC in poi: in Crea si **vede** esattamente ciò
   che vedrà chi ascolta. Stesso motore + stesse impostazioni = garantito per
   costruzione, non per disciplina.

## 2. Perché l'integrazione è più piccola di quanto sembra

L'idraulica esiste già tutta. Non è un caso: è il dividendo delle scelte dei
cicli AV/ES.

- **`startPreview(ctx, score, { uscita })`** accetta già un nodo intermedio:
  è come la pagina pubblica aggancia l'analizzatore. Crea oggi semplicemente
  non passa `uscita`. Il cablaggio audio→visual in Crea è **una riga**.
- **`creaLettore(ctx)`** (analisi.js) è l'unica verità su «cosa fa il suono»:
  si innesta sul grafo dell'anteprima come su quello della pagina pubblica.
- **`avviaPrototipo(root, { incorporato, analizzatore })`** — il motore unico
  di AV5 sa già disegnare senza pannelli su un analizzatore prestato. Per VC
  gli servono solo due opzioni in più (§4).
- **Lo score è un contratto additivo** (`score_version`: «il formato può
  evolvere solo aggiungendo»). Un campo `visual` opzionale è l'evoluzione per
  cui il contratto è stato scritto.

Il lavoro vero quindi non è tecnico: è **UX**. Ed è giusto così, perché è lì
che il founder ha messo la priorità.

## 3. Il principio UX: tre piani di sforzo, il primo è zero

Crea è già denso (timeline, leggio, fasi, dissolvenze). Il rischio concreto
di «integrare il visualizzatore» è aggiungere un'altra sezione da gestire, un
altro pannello che chiede attenzione. La risposta è non aggiungere una
sezione: **la scena non è un compito, è il palco su cui l'ascolto già
avviene**. La personalizzazione si nasconde dietro un gesto solo.

### Piano 0 — non fare nulla (il 100% degli autori parte da qui)
Chi compone e pubblica senza mai toccare il visual ottiene il preset Aurya
multicolore — esattamente ciò che è in produzione oggi con AV5. **Zero scelte
obbligatorie**: nessun passo nuovo nel flusso di pubblicazione, nessun campo
in più da capire. Le meditazioni già pubblicate restano identiche (score
senza `visual` → default).

### Piano 1 — un tocco (il gesto per il 90% di chi sceglie)
Durante l'ascolto in Crea, sulla scena, una striscia discreta: **i 7 preset
del prototipo** (Aurya, Cosmos, Anahata, Prana, Nirvana, Kundalini, Samadhi),
ognuno un nome + i tre punti colore della sua palette. Un tocco = la scena
cambia dal vivo, mentre il suono continua. Niente vocabolario tecnico: si
sceglie a occhio, come si sceglie un filtro fotografico. Accanto, i **6
pallini palette** per cambiare solo il colore tenendo la forma.

### Piano 2 — «Regola fine» (per chi esplora)
Un accordion/foglio che apre gli 11 cursori + camera — le stesse manopole di
`/sound/visual`, con **etichette italiane** (Intensità, Scala, Velocità,
Ciclo respiro, Deriva, Particelle, Bagliore, Scie, Profondità, Luce,
Contrasto). Tutto agisce dal vivo sulla scena che suona. Chi ha imparato
nella stanza personale ritrova esattamente le stesse leve.

Il ciclo immersivo richiesto emerge da solo: *aggiungo tracce → Ascolta → la
scena si accende col mio suono → tocco un preset, ritocco un cursore → parlo
al leggio mentre la scena respira → Salva bozza / Pubblica → tutto dentro,
audio e scena insieme.*

## 4. Architettura — le decisioni una per una

### 4.1 Dove vivono i dati: dentro lo score
```
score.visual = {
  mode: 4, pal: 5, cam: 2,
  intensity: 96, scale: 102, speed: 36, breath: 10, drift: 34,
  particles: 15000, glow: 132, trails: 92, depth: 135,
  brightness: 122, contrast: 104
}
```
- **Valori risolti, non nome del preset**: come per le dissolvenze, si salva
  ciò che si applica. Se domani un preset cambia taratura, le opere già
  pubblicate non cambiano faccia a insaputa dell'autore.
- **`clean_visual()`** nel modello con la filosofia listino: valori fuori
  range riportati nel range, struttura assente = campo assente (mai rifiuto
  dell'intero score per colpa del visual).
- **Niente bump di `score_version`**: campo opzionale ignorato dai lettori
  vecchi = additivo puro. (Da verificare in VC1: che il serializzatore
  pubblico faccia passare `score.visual` — se fa whitelist, va aggiunto.)
- Alternativa scartata: campo `visual` fuori dallo score, sulla traccia.
  Permetterebbe ritocchi senza ripubblicare, ma spezza «un documento = tutta
  l'opera» e raddoppia i percorsi di salvataggio. Il flusso bozza→pubblica
  già gestisce lo score: il visual gli viaggia dentro gratis.

### 4.2 Il motore resta UNO — due opzioni in più, nessuna copia
`avviaPrototipo(root, opz)` cresce di:
- **`opz.impostazioni`**: override iniziale delle S (oggi il ramo
  `incorporato` fissa Aurya+Prism in casa; diventa il *default* quando
  `impostazioni` manca — pagina pubblica con score vecchi inclusa);
- **ritorno di un manico**: oggi torna `cleanup`; tornerà
  `{ pulisci, applica(patch), leggi() }` — `applica` scrive le stesse chiavi
  S e la scena cambia al fotogramma dopo. Compatibilità: la pagina strumento
  continua a chiamare la pulizia.

I controlli di Crea sono un **velo React sottile** che chiama `applica()`:
etichette italiane, testid, foglio mobile. NON si rimontano i pannelli DOM
del prototipo dentro Crea (sono in inglese, fissi, pensati per il desktop a
schermo pieno) — ma non è una seconda versione del motore: è solo un'altra
tastiera sullo stesso strumento. Guardia dedicata: le chiavi che il velo
scrive ⊆ le chiavi di `SLIDERS` del prototipo — se il prototipo evolve, il
velo non può divergere in silenzio.

### 4.3 Il cablaggio audio in Crea
`playSession` passa `uscita: lettoreRef.current.analyser` a `startPreview`
(riga singola, identica alla pagina pubblica). Il lettore si crea pigro al
primo «Guarda», sul `ctx` che Crea già possiede. **La voce del leggio**: la
scena reagisce a ciò che passa dall'analizzatore, cioè al mix in uscita —
se il monitor della voce non ci passa, la scena respira con le basi ma non
con la voce mentre si registra. Da verificare sul grafo vero in VC2; se
serve, si aggancia anche il ramo del leggio. Non promettere «reagisce alla
tua voce» finché non è vero.

### 4.4 Dove sta la scena in Crea (mobile-first)
Come nella pagina pubblica: **una scheda sopra la timeline**, montata solo
quando si chiede «Guarda» (disegnare consuma — regola AV1 invariata), col
tocco che apre a tutto schermo (il componente AV5 esiste già). A tutto
schermo, overlay minimo: frecce preset + pallini palette + «Regola fine», e
lo spirito «hide interface» del prototipo — l'interfaccia si fa da parte da
sola. La scena si spegne con lo stop. Batteria: quality/particles già scalati
dal ramo `incorporato` sugli schermi stretti.

## 5. Cosa NON si tocca (il perimetro di «senza sfasciare»)

| Regola esistente | Sorte |
|---|---|
| Ascolto continuo a schermo bloccato **senza** visual | invariata (guardare e schermo spento si escludono) |
| Sipario sicurezza prima del suono | invariato — la scena parte dopo il cancello |
| `/sound/visual` = stanza personale con localStorage | intatta; in Crea la memoria è **la bozza**, mai localStorage |
| Attacco/dissolvenze uniformi anteprima=pubblicato | invariati |
| Motore unico (guardia AV5) | si estende: nemmeno Crea può farsi un motore suo |
| Three lazy, mai nel main | invariato — la scena monta on demand |
| Score additivo, pregresso identico | il cuore di VC1 |
| Privacy `/sound/visual` (l'audio non lascia il dispositivo) | invariata — in Crea basi e voce sono già asset del sistema, niente di nuovo esce |

## 6. Il piano a onde — ognuna consegnabile da sola

- **VC1 — Il contratto** (piccola, di fondazione): `clean_visual()` +
  passthrough nel serializzatore pubblico; `opz.impostazioni` + manico
  `applica()` nel motore; la pagina pubblica applica `score.visual` se c'è.
  Fine VC1: una meditazione *seminata* a mano con un visual custom lo mostra
  a chi ascolta. Il filo è teso da capo a capo prima di costruire UI.
- **VC2 — La scena in Crea**: «Guarda» in Crea, analizzatore
  sull'anteprima, default Aurya, tutto schermo col tocco (riuso AV5),
  verifica del ramo voce/leggio.
- **VC3 — La scelta a un tocco**: striscia dei 7 preset + pallini palette
  sulla scena, salvataggio in bozza/pubblicazione. **Questa è l'onda in cui
  la richiesta del founder diventa vera per gli utenti.**
- **VC4 — Regola fine**: gli 11 cursori + camera in italiano, dal vivo.
- **VC5 — I ponti** (opzionale, dopo): da `/sound/visual` «Usa in una
  meditazione» e viceversa «Apri nello strumento». Solo se i piedi (VC1-4)
  reggono e l'uso lo chiede.

Ordine pensato per il rischio: il contratto prima della UI, la UI a un tocco
prima delle manopole. Ogni onda lascia il sistema pubblicabile.

## 7. Domande aperte per il founder

1. **La scena è dell'autore o di chi ascolta?** Proposta: **dell'autore**
   (fa parte dell'opera; chi ascolta tiene solo il tutto schermo). Lasciare
   a chi ascolta il cambio palette è possibile ma diluisce la firma — e la
   stanza per giocare esiste già ed è `/sound/visual`.
2. **Ritocco dopo la pubblicazione**: col visual nello score, cambiare la
   scena di un'opera pubblicata passa dal normale flusso di aggiornamento
   della traccia. Va bene così, o serve un «cambia solo la scena» rapido?
3. **I 7 preset così come sono** nel prototipo, o una selezione curata per
   Crea? Proposta: tutti e 7 — sono già buoni e già suoi.

---

# VC6 — Lo studio della scena (analisi, 22 agosto sera)

**Richiesta founder**: tutte le regolazioni — parametri, colori, preset,
forma — in un pannello a tutto schermo, «esattamente come /sound/visual»:
cliccando sulla forma in Crea si apre lo studio, tornando indietro le scelte
restano salvate per quella meditazione. Ottimizzato mobile; i pannelli si
chiudono per vedere la forma a schermo pieno.

## 1. La tesi: lo studio ESISTE già, va solo invitato

`/sound/visual` è già il pannello a tutto schermo che il founder descrive:
pannelli laterali, 11 cursori, palette, preset, modi, «Hide interface» (H)
per vedere la forma nuda, fullscreen (F). Non si costruisce una seconda
schermata: si monta **lo stesso prototipo** dentro Crea in una terza
modalità. La lezione di AV5 resta la legge: mai due versioni della stessa
cosa.

La matrice delle modalità diventa:

| | pannelli | audio | memoria |
|---|---|---|---|
| **strumento** (`/sound/visual`) | sì | mic / file dell'utente | localStorage |
| **incorporato** (meditazione, scena in Crea) | no | analizzatore prestato | la ricetta |
| **studio** (nuovo) | sì | analizzatore prestato | la ricetta (via `leggi()` alla chiusura) |

Cioè: `studio` = pannelli dello strumento + audio dell'incorporato. Tre
flag ortogonali, un file solo.

## 2. Cosa cambia nel motore (`opz.studio`)

- **Sorgenti spente**: niente mic, niente carica-traccia, niente gate — il
  suono è la sessione che suona sotto. L'etichetta sorgente dice «La tua
  sessione». (Patch al markup con assert: id alla sezione sorgenti, così
  la si nasconde con una classe, non cercando bottoni alla cieca.)
- **localStorage OFF** (come incorporato): la memoria è la bozza. `save()`
  già è un no-op fuori dallo strumento puro; il ramo si allarga a studio.
- **La stessa base d'ambiente**: la taratura AV5 (trails 92, glow 132…)
  esce dal ramo incorporato in un oggetto `AMBIENTE` condiviso: studio e
  meditazione partono IDENTICI, poi `opz.impostazioni` (la scena della
  bozza) vince su tutto.
- **Il marchio chiude, non naviga**: in studio il brand AURYA non deve
  portare a /sound (perderesti la sessione): diventa «← Torna alla
  sessione», più un bottone «✓ Fatto» esplicito nel topbar.
- **Round-trip**: Crea apre lo studio passando `impostazioni: visual`;
  alla chiusura chiama `manico.leggi()` → `setVisual` → si salva con la
  bozza. Nessun canale nuovo: il manico di VC1 basta.
- Il ramo audio `if (incorporato && opz.analizzatore)` diventa
  `if (opz.analizzatore)` — vale per entrambe le modalità prestate.

## 3. Il flusso in Crea

- Il tasto «✦ Guarda il suono» resta: accende la scheda-scena.
- **Tap sulla scena** (solo in Crea): apre lo **studio** a tutto schermo —
  non più il semplice fullscreen. Per chi ascolta (pagina pubblica) il tap
  resta fullscreen puro: la scelta è autoriale, lo studio non esiste lì.
- **La striscia inline (ScenaControlli) SPARISCE**: il founder ha chiesto
  tutte le regolazioni nel pannello. Un solo posto dove si sceglie = meno
  UI in Crea, zero divergenza possibile. Il file si elimina; le guardie
  VC3 si riscrivono sullo studio.
- L'audio **continua a suonare** mentre lo studio è aperto: è un overlay
  nella stessa pagina (`.avz` è già `position:fixed inset:0`), non una
  navigazione. Chiudendo, la sessione è dove l'avevi lasciata.
- Studio aperto **da fermo**: si passa `analizzatore` solo se sta suonando;
  senza, il prototipo usa il suo moto idle (respiro finto, già suo) — si
  scelgono forma e colori su una scena che si muove piano. Un chip lo dice:
  «Ascolta dalla sessione per vederla reagire». Niente autoplay: il suono
  si chiede, regola di casa.

## 4. Mobile — il lavoro vero

Stato attuale del prototipo sotto i 1080px: solo la modebar si stringe.
I pannelli fissi laterali (438px totali) su un telefono da 390px coprono
tutto. Piano:

- **Fogli dal basso**: sotto i 760px, `#left` e `#right` diventano fogli a
  tutta larghezza ancorati in basso (`max-height: 62dvh`, scroll interno),
  chiusi di default, aperti UNO alla volta da una barra di chip:
  `[◈ Preset] [☼ Regola] [▦ Forme]` + «Fatto». Solo CSS + una manciata di
  listener nel ramo studio: il DOM dei pannelli non si tocca.
- **La forma resta protagonista**: fogli chiusi = scena piena (è già lo
  spirito hidden-ui del prototipo). Aprire un foglio copre al massimo il
  60% dello schermo, la scena respira sopra.
- Touch: target ≥44px sui chip, `safe-area-inset-bottom`, cursori nativi
  (già ok), OrbitControls touch già funziona (la tela è fullscreen, non
  c'è scroll da rubare).
- Batteria: `S.quality` già limato su schermi stretti; il tetto particelle
  di resa (VC1) già non firma la ricetta.
- Desktop resta ESATTAMENTE il prototipo: le patch mobile vivono sotto
  media query e classe `.studio`, la pagina `/sound/visual` non cambia di
  un pixel.

## 5. Onde

- **VC6a — il motore sa fare lo studio**: flag + sorgenti spente +
  `AMBIENTE` condiviso + brand-chiude + «Fatto»; guardie di matrice.
- **VC6b — Crea**: overlay `StudioScena` (monta markup+`avviaPrototipo`
  con `studio`), tap sulla scena lo apre, round-trip `leggi()`→bozza,
  eliminazione ScenaControlli e riscrittura guardie.
- **VC6c — mobile**: fogli dal basso, chip, safe-area, topbar compresso.
- **VC6d — rifiniture**: play/pausa della sessione DENTRO lo studio (per
  non uscire a far partire il suono), evidenza del preset attivo.

## 6. Proposte (non bloccanti, si parte con questi default)

1. La striscia inline sparisce del tutto → **sì** (un solo posto).
2. Play/pausa dentro lo studio → **sì, ma in VC6d** (prima il flusso).
3. Chi ascolta non vede mai lo studio → già deciso (scena autoriale).
