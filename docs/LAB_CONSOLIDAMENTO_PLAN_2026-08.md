# Aurya Sound Lab — il consolidamento (ciclo LB, 27/8/2026)

*Richiesta del founder: «deve essere un vero e proprio laboratorio» —
il microfono che ascolta una campana tibetana, ne identifica le
frequenze, la analizza a fondo e la risintetizza; nuove onde (esistono
onde 3D?); e a un certo punto la cimatica. Questo piano dice cosa
costruire, in che ordine, e dove passa il confine tra scienza e
marketing — perché il Lab è nato con un patto: «un segnale generato
davvero dal tuo dispositivo», niente trucchi.*

---

## 0 · Da dove partiamo (verificato nel codice)

La V1 è COMPLETA e verificata: **Generatore** (4 forme, fase vera via
PeriodicWave anti-aliasata, 20 Hz–20 kHz), **Sweep** (rampa
sample-accurate nel motore, `freqOra()` = stessa formula del browser,
prova regina superata), **Oscilloscopio**, **Spettro**,
**Spettrogramma**; il **motore React-free** (`lab/motore.js`) con le
tre regole di casa (suono solo dal ponte, rampe DK 12 ms, crossfade
sui cambi di forma); e la scelta architetturale che paga oggi:
`analisi.sorgente(nodo)` accetta QUALSIASI nodo — i moduli di lettura
non sanno da dove viene il segnale. La presa per il microfono esiste
dal primo giorno. Questo piano è tutto terreno nuovo.

---

## LB1 — La seconda sorgente *(fondamenta)*

- **Seconda sorgente**: il Generatore raddoppia. Da qui nascono le
  cose che oggi il Lab promette e non mantiene:
  - la **fase** finalmente si sente (oggi il pannello lo ammette:
    «conterà quando le sorgenti saranno due») — interferenza
    costruttiva/distruttiva, cancellazione a 180°;
  - **battimenti monaurali** (440+444 Hz nello stesso canale: il
    battito a 4 Hz si VEDE nell'oscilloscopio);
  - **binaurale da laboratorio**: una sorgente per orecchio — quello
    che il prodotto usa nelle sessioni, qui si smonta e si misura.
- Oscilloscopio in **modo XY** (Lissajous): con due sorgenti è il
  modo più bello di vedere rapporto di frequenza e fase — costa poco,
  è pura lettura dell'analyser.

*Effort: 1 giornata (lo sweep c'è già: la rampa del motore e
`freqOra()` sono la presa pronta del resonance finder di LB6).
Rischi: il crossfade di forma/fase va replicato pulito sulla seconda
voce.*

## LB2 — L'ORECCHIO: il microfono entra nel Lab *(la richiesta)*

`getUserMedia` → `MediaStreamSource` → `analisi.sorgente(mic)`. I
moduli esistenti (spettro, spettrogramma, oscilloscopio) leggono il
microfono SENZA TOCCARLI: è il raccolto dell'architettura ospite.

- **I vincoli che decidono la qualità** (qui si vince o si perde):
  `echoCancellation: false, noiseSuppression: false,
  autoGainControl: false` — i filtri «da videochiamata» del browser
  mangiano esattamente ciò che vogliamo misurare (code di
  risonanza, parziali acuti, dinamica vera).
- **L'accordatore**: fondamentale in tempo reale via
  **autocorrelazione** (la stessa matematica già in casa nel polso
  della Danza) + interpolazione parabolica sul picco → lettura in Hz
  con un decimale, nota più vicina e scarto in cents.
- **Privacy dichiarata nel pannello**: il suono non lascia il
  dispositivo — niente upload, niente registrazione salvata senza un
  gesto esplicito. (Coerente con la regola della voce: il microfono
  è un gesto in-app, mai un file manager.)

*Effort: 1 giornata. Rischi: permessi mic su iOS/Safari (gesto
utente obbligatorio), device senza mic (il pannello si spegne con
garbo).*

## LB3 — IL RITRATTO: l'analisi solida di un suono *(la campana, parte 1)*

Registri 5–10 secondi (la campana suonata davanti al telefono) in un
buffer. Poi l'analisi OFFLINE, fatta bene — non l'analyser live, ma
la nostra FFT sul buffer intero:

- **FFT propria** (radix-2, finestra di Hann, zero-padding ×4) —
  niente dipendenze nuove, ~60 righe, e controlliamo noi risoluzione
  e finestra;
- **la tabella dei parziali**: picchi con interpolazione parabolica →
  per ciascuno frequenza (±0,1 Hz), ampiezza relativa, rapporto col
  fondamentale e scarto in cents dall'armonico teorico. Una campana
  tibetana NON è armonica: i suoi modi stanno tipicamente su rapporti
  ~1 · 2,7 · 4,9 · 7,6… — il ritratto lo mostra, ed è il momento in
  cui il Lab insegna qualcosa di vero;
- **gli inviluppi**: per ogni parziale, attacco e tempo di
  decadimento (T60) misurati con STFT — i parziali acuti muoiono
  prima, il fondamentale resta: è la firma temporale del timbro;
- **i doppietti**: nelle campane i modi vivono in coppie quasi
  coincidenti (es. 440,0 e 441,8 Hz) e il loro battimento è lo
  «shimmer» che si sente girare. Si misurano distanza in Hz e
  profondità: senza doppietti, la risintesi suonerà finta;
- **il RITRATTO è DATI** (JSON: parziali, inviluppi, doppietti) — la
  filosofia della casa: come lo score è la ricetta della sessione, il
  ritratto è la ricetta del timbro. Piccolo, confrontabile,
  risintetizzabile.
- **Onestà strumentale, scritta nel pannello**: un microfono da
  telefono colora lo spettro — sotto ~100 Hz e sopra ~15 kHz le
  ampiezze sono indicative; le FREQUENZE invece sono affidabili
  (è ciò che conta per l'accordatura e la cimatica).

*Effort: 2 giornate. Rischi: rumore ambiente (si mitiga: soglia sul
floor + «registra il silenzio prima» opzionale); parziali che il mic
taglia.*

## LB4 — LA CAMPANA RIFATTA: la risintesi *(la campana, parte 2)*

Dal ritratto si ricostruisce il suono — sintesi **additiva**: un
oscillatore per parziale, il SUO inviluppo esponenziale, e per i
doppietti la coppia vera di oscillatori (il battimento rinasce da
solo, perché è fisica, non effetto).

- **La prova A/B**: un pulsante — originale / risintesi — e gli
  spettri sovrapposti. Il Lab non dice «uguale»: te lo fa sentire e
  vedere, e il ritratto si può ritoccare (togli un parziale, allunga
  un decadimento) sentendo subito la differenza. Questo È il
  laboratorio.
- **Due modi**: *colpo* (inviluppi misurati, il suono muore da solo)
  e *tenuto* (i parziali reggono come nella campana strofinata — per
  meditazione e cimatica).
- **Il ponte col prodotto**: «Usa in Crea» — la risintesi si
  renderizza offline (pipeline mp3 già in casa) e diventa una base
  della libreria (categoria strumenti, titolata «Campana di …»).
  Il Lab smette di essere una stanza chiusa: quello che scopri lo
  porti nelle sessioni.

*Effort: 2 giornate. Rischi: attacco percussivo del colpo (i primi
50 ms sono rumore a banda larga, non parziali — si aggiunge un
transiente di rumore sagomato, dichiarato nel ritratto).*

## LB5 — LE NUOVE ONDE: il catalogo onesto *(la domanda «esistono onde 3D?»)*

La risposta va data col rigore del Lab, perché qui fuori si vende
di tutto:

- **Il suono 3D ESISTE** ed è spazializzazione: **HRTF**
  (`PannerNode`) — in cuffia, una sorgente che orbita attorno alla
  testa, sopra, dietro. È percezione vera, misurabile, e nel Lab ci
  sta benissimo: *Orbita* come modulo (traiettorie: cerchio, otto,
  spirale; velocità; quota). Spettacolare e onesto.
- **Le «frequenze 3D» del marketing** (l'onda che «sarebbe»
  tridimensionale di suo) NON esistono: un'onda di pressione è
  un'onda di pressione. Il Lab lo dice con le etichette di casa
  (A/B/C) — la credibilità di Aurya vale più di una parola di moda.
- **Il principio delle meraviglie (27/8, founder: «onde belle,
  affascinanti — vortici, geometrie, trascendenti»): la geometria
  non si aggiunge al suono, EMERGE dal suono.** Ogni meraviglia del
  catalogo e' un fenomeno vero mostrato dal lato giusto — mai un
  effetto dipinto sopra. Tre famiglie:

  *Lo spazio (col telaio HRTF dell'Orbita):*
  - **il Vortice** — orbita a spirale che si stringe salendo (o si
    allarga scendendo), Doppler naturale del PannerNode, un filo di
    glissando: il suono avvita attorno alla testa;
  - **la rotazione nella testa** — sfasamento interaurale che ruota
    piano: la sorgente gira DENTRO il cranio (lateralizzazione di
    fase, psicoacustica documentata).

  *La geometria (che emerge dai rapporti):*
  - **i Rapporti** — l'intervallo scelto come rapporto intero (2:1,
    3:2, 4:3, 5:4): lo SENTI come consonanza e lo VEDI in XY — le
    figure di Lissajous sono la geometria dell'intervallo; stonato
    di poco, la figura RUOTA (il vortice geometrico a schermo);
  - **il Mandala** — vista polare dell'oscilloscopio (l'onda avvolta
    in cerchio, raggio = ampiezza): ogni timbro un mandala che
    respira; stesso analyser, solo un pittore nuovo;
  - **Phi** — due sorgenti in rapporto aureo 1:1,618…: il numero
    «piu' irrazionale» da' un battimento che non si ripete MAI;
    etichetta C sul simbolo, matematica vera sul fenomeno.

  *L'illusione e il trascendente (psicoacustica vera):*
  - **Shepard-Risset** — la scala infinita (il catalogo ha gia' la
    «discesa infinita»: il Lab ne mostra il trucco) + il ritmo di
    Risset che accelera per sempre;
  - **il terzo suono (Tartini)** — 1200+1500 Hz e l'orecchio genera
    un 300 Hz che NELL'ARIA NON C'E' (lo spettro lo dimostra: il
    picco manca);
  - **la fondamentale fantasma** — armoniche 400+600+800 senza il
    200: il cervello sente il 200. Il suono che non c'e'.

  *Il banco classico:*
  - **rumori colorati** (bianco/rosa/marrone) — anche segnale di
    prova per LB3;
  - **FM alla Chowning** — campane sintetiche da confrontare con
    quelle vere di LB4;
  - **la corda pizzicata** (Karplus-Strong) — una corda simulata in
    ~20 righe, fisica vera che decade da sola;
  - **isocroni e battimenti** di casa: sul banco, misurati;
  - **onda disegnata / catturata** — un ciclo col dito o dal mic →
    PeriodicWave (il telaio della fase lo permette quasi gratis).

*Effort: 2–3 giornate a moduli indipendenti (si può spezzare).
Rischio: nessuno tecnico; il rischio è di vetrina — ogni onda entra
SOLO col suo cartellino di verità.*

## Le didascalie — ogni modulo si racconta *(trasversale, 27/8 founder)*

Ogni pannello e ogni onda nasce con la sua **didascalia breve** (2–3
righe, tono da museo della scienza: cosa stai vedendo, perche' e'
interessante, cosa provare) + dove serve l'approfondimento col
pattern «learn» gia' in casa nella biblioteca. Non si spedisce un
modulo muto: la didascalia fa parte della definizione di fatto.
Il tono, con tre esempi che fanno da diapason:

- *Vortice* — «Il suono gira davvero attorno alla tua testa: e' la
  spazializzazione HRTF, la stessa matematica con cui il cervello
  localizza i suoni nel mondo. Chiudi gli occhi e seguilo.»;
- *Terzo suono* — «Stiamo suonando solo 1200 e 1500 Hz. Il 300 Hz
  che senti lo sta generando il tuo orecchio: nell'aria non c'e' —
  guarda lo spettro. Si chiama tono di Tartini, dal 1714.»;
- *Rapporti* — «Un intervallo musicale e' un rapporto tra numeri:
  3:2 e' la quinta. La figura che vedi E' quel rapporto disegnato —
  quando la senti consonante, stai sentendo la geometria.».

## LB6 — VERSO LA CIMATICA *(il traguardo dichiarato)*

La cimatica (sabbia su piastra, acqua in coppa) chiede al Lab quattro
cose precise — e le chiede al software, non ancora all'hardware:

1. **precisione e tenuta**: frequenza a passo fine (±0,1 Hz), tono
   stabile per minuti, ampiezza calibrata con rampa (i pattern di
   Chladni vivono in finestre strette di frequenza);
2. **il resonance finder**: sweep LENTO + il microfono che ascolta la
   risposta del sistema fisico (la rampa del motore + l'orecchio di
   LB2) → il grafico eccitazione/risposta con i picchi segnati: trovi
   le risonanze della TUA piastra/coppa e le salvi come preset.
   E vale per QUALSIASI OGGETTO (27/8, founder): bottiglia, lattina,
   bicchiere — due strade complementari:
   - *il colpo* (passiva, gia' con LB2/LB3): l'oggetto colpito suona
     SOLO sui suoi modi — lo spettro del colpo e' la risposta; la
     bottiglia ne ha due di nature diverse (il «ping» del vetro =
     modi strutturali; il tono di soffio = risonanza di Helmholtz
     dell'aria: con l'acqua il primo scende e il secondo sale — un
     esperimento didattico perfetto);
   - *lo sweep* (attiva, LB6): quando il colpo non basta, si
     interroga l'oggetto con la rampa e il mic sente dove canta.
   Trovata la frequenza, la tieni addosso all'oggetto col tono
   fermo e GUARDI la reazione (riso, acqua, vibrazione): cimatica
   con oggetti di casa. Onesta' dichiarata: sotto ~200 Hz
   l'altoparlante del telefono spinge poco — per muovere davvero
   serve l'export WAV verso un ampli;
3. **uscita dedicata**: modo mono (una piastra ha un attuatore solo),
   opzione di disattivare il limiter di comodo, **export WAV** del
   tono/sweep per amplificatori e attuatori esterni;
4. **il quaderno**: le risonanze trovate e i ritratti (LB3) si
   salvano per-org come «esperimenti» — dati, riproducibili, alla
   maniera delle ricette.

L'hardware (attuatori, piastre, vibroacustica) resta fuori scope
software: è il substrato della fase-vibrazioni di Professional, e
questo piano gli prepara il banco. **Mai claim terapeutici**: la
cimatica nel Lab è fisica visibile, non medicina.

*Effort: 2 giornate (senza hardware). Dipende da LB1+LB2.*

## LB7 — IL VESTITO DEGLI STRUMENTI: il redesign dei grafici *(27/8, founder)*

I tre pannelli (oscilloscopio, spettro, spettrogramma) funzionano ma
vestono ancora da prototipo. Diventano **strumenti belli da guardare
anche spenti** — estetica da strumentazione moderna dentro l'Ora
d'oro del mondo Sound:

- **traccia viva**: linea con bagliore (glow) e persistenza al
  fosforo per l'oscilloscopio (la scia che svanisce, come sugli
  oscilloscopi veri — e' anche INFORMAZIONE: mostra la stabilita');
- **spettro**: area riempita con gradiente che si spegne verso il
  fondo, picco principale marcato con quota in Hz leggibile,
  griglia sottile che non urla, etichette in --mono;
- **spettrogramma**: mappa colori curata (percettivamente uniforme,
  dal blu profondo all'oro del mondo), niente arcobaleni da anni 90;
- **il numerone** (frequenza) come protagonista tipografico — la
  cifra e' il cuore dello strumento, si vede da un metro;
- **micro-transizioni**: i cambi (forma, sorgente, congela) si
  muovono con le rampe che il suono gia' usa — l'occhio e
  l'orecchio ricevono lo stesso gesto;
- tutto CSS + canvas gia' in casa: zero dipendenze, zero costo
  server; i pittori restano nel contratto `quadro.js` (un solo rAF).

*Effort: 1,5 giornate. Si puo' fare in qualunque momento dopo LB1;
ideale prima di LB5 cosi' le meraviglie nascono gia' vestite.*

## LB8 — LA REVISIONE OLISTICA: bello, facile, utile *(il sigillo)*

A valle delle onde, un giro completo sul Lab come ESPERIENZA — non
una lista di pannelli ma un laboratorio dove si entra, ci si
orienta e si ha voglia di restare:

- **la navigazione**: indice del banco sempre a portata (le sezioni
  del Lab come stanze — generatore, letture, orecchio, meraviglie,
  esperimenti), scroll con ancore, la barra dello strumento sticky
  senza rubare schermo; su telefono i fogli alla maniera di VM1;
- **il primo minuto**: chi entra a freddo deve capire in 60 secondi
  cosa si fa qui — un invito iniziale («premi play, muovi la
  frequenza, guarda lo spettro rispondere») al posto del silenzio;
- **i percorsi guidati**: 3–4 esperimenti raccontati passo-passo
  che legano i moduli («Misura la tua bottiglia»: colpo → spettro →
  accordatore → risintesi; «La geometria degli intervalli»: rapporti
  → XY → mandala; «L'orecchio che inventa»: Tartini → fondamentale
  fantasma) — e' qui che «utile e interessante» diventa concreto;
- **la coerenza dei comandi**: stessi cursori, stessi campi, stesse
  distanze in ogni pannello; gli stati vuoti parlano; ogni azione
  distruttiva chiede col modale di casa;
- **l'accessibilita'**: fuochi visibili, contrasti misurati, tutto
  usabile col dito su schermo piccolo (la lezione dei 767px e' gia'
  in memoria);
- **il collaudo del racconto**: una persona che non ha mai visto il
  Lab lo attraversa senza guida — se si perde, e' un difetto nostro.

*Effort: 1,5–2 giornate. Va per ultimo: rivede TUTTO quello che le
onde hanno costruito.*

---

## Solidità trasversale (in ogni onda)

- Guardie di casa: motore React-free, **zero dipendenze nuove**
  (FFT e autocorrelazione si scrivono, sono poche righe), suono solo
  dal ponte, analisi input-agnostica, three.js fuori dal chunk Lab;
- iOS: contesto/silenziatore già gestiti dal ponte; il mic chiede il
  gesto; i fogli mobile alla maniera di VM1;
- ogni modulo nasce col suo **«funziona quando»** misurabile (alla
  maniera della prova regina dello sweep) + collaudo a schermo;
- sicurezza: gli avvisi cuffie/volume esistenti valgono anche qui.

## Ordine consigliato e totale

**LB1 → LB2 → LB3 → LB4** è la spina dorsale (la campana del founder:
~6 giornate). **LB7** (vestito dei grafici) ideale subito dopo LB1,
così tutto il resto nasce già vestito. **LB5** si affianca a piacere
(moduli indipendenti, con didascalia). **LB6** chiude quando LB1+LB2
sono in piedi. **LB8** (revisione olistica) sigilla il ciclo per
ultimo. Totale: ~13–15 giornate spezzabili in cicli piccoli, ognuno
rilasciabile da solo.

## Fuori scope, di proposito

Upload di file audio (il Lab ascolta il mondo col microfono, in-app);
webcam sulla piastra di Chladni; hardware e pilotaggio attuatori;
qualunque promessa terapeutica.

---

**ESEGUITO PER INTERO il 27-28/8/2026** (solo locale, deploy al go):
LB1 630ba5ae · LB2 b79178f3 · LB3 917f769c · LB4 e6039815 ·
LB7 57c124fc · LB5 5e93d960 · LB6 b2481dcb · LB8 ae5e72bb.
91 guardie in tests/test_sound_lab.py. Resta al founder il collaudo
col MICROFONO VERO (il pannello dell'automazione lo blocca):
accordatore, ritratto di una campana vera, cercatore di risonanze.
