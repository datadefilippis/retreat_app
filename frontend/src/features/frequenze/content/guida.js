/*
 * Aurya Sound — Le fondamenta.
 * I DATI della Guida e del Glossario. La resa sta in GuidaView.js.
 *
 * Regola editoriale di questo file: evocativo nel linguaggio, rigoroso
 * nella sostanza, progressivo nell'apprendimento. Ogni volta che una
 * frase passa da «questo fenomeno esiste» a «questo fenomeno produce
 * questo effetto», il livello di evidenza va verificato: qui si dice
 * «e' associato a», «e' stato studiato per», «la ricerca sta esplorando»
 * — mai «porta il cervello in», «sincronizza», «riequilibra».
 */

// Il percorso: sei tappe, in ordine di lettura. `short` alimenta la
// micro-navigazione, `n`/`kicker`/`t` la mappa sotto l'hero.
export const PERCORSO = [
  { id: 'gd-cervello', n: '01', kicker: 'Il cervello', short: 'Cervello',
    t: 'Che cosa sono le onde cerebrali' },
  { id: 'gd-entrainment', n: '02', kicker: 'Lo stimolo', short: 'Entrainment',
    t: "Che cos'è l'entrainment" },
  { id: 'gd-metodi', n: '03', kicker: 'Il metodo', short: 'Metodi',
    t: 'Binaurale, monaurale, isocronico e bilaterale' },
  { id: 'gd-ascolto', n: '04', kicker: "L'ascolto", short: 'Ascolto',
    t: 'Cuffie o altoparlanti?' },
  { id: 'gd-sessione', n: '05', kicker: "L'esperienza", short: 'Sessione',
    t: 'Come costruire una sessione' },
  { id: 'gd-precisione', n: '06', kicker: 'La precisione', short: 'Precisione',
    t: 'Quanto è accurato ciò che ascolti' },
];

// Le cinque bande, in scala logaritmica: `w` e' la larghezza del segmento
// sulla striscia (0,5 → 60 Hz), calcolata sui logaritmi degli estremi,
// non a occhio. Cambiando i confini vanno ricalcolate anche le larghezze.
export const BANDE = [
  { t: 'Delta', hz: '~0,5–4 Hz', d: 'attività lenta', w: 43.4 },
  { t: 'Theta', hz: '~4–8 Hz', d: 'attività lenta/intermedia', w: 14.5 },
  { t: 'Alpha', hz: '~8–13 Hz', d: 'ritmo tipico dello stato di veglia rilassata', w: 10.1 },
  { t: 'Beta', hz: '~13–30 Hz', d: 'attività più rapida', w: 17.5 },
  { t: 'Gamma', hz: 'oltre ~30 Hz', d: 'attività ad alta frequenza', w: 14.5 },
];

// Livello 3: l'approfondimento facoltativo. Si apre nel popup gia'
// esistente («Approfondisci»), lo stesso della biblioteca.
export const APPROFONDIMENTI = {
  soglie: {
    title: 'Perché le soglie delle bande non sono identiche ovunque',
    body:
      "<h4>Categorie, non confini naturali</h4><p>Le bande sono uno strumento di analisi: servono a descrivere come l'energia dell'EEG si distribuisce lungo lo spettro. Non sono compartimenti separati da muri fisici, e infatti i valori di soglia cambiano leggermente tra laboratori, protocolli e tradizioni di ricerca.</p>" +
      "<h4>Dove cambiano più spesso</h4><p>Il confine tra theta e alpha viene collocato da alcuni a 7 Hz e da altri a 8; il limite superiore di beta oscilla tra 30 e 35 Hz; gamma viene definita a volte come «oltre 30 Hz», a volte come «oltre 40 Hz». Alcuni approcci definiscono la banda alpha in modo individuale, ancorandola al picco di ciascuna persona invece che a una soglia fissa.</p>" +
      "<h4>Perché è importante saperlo</h4><p>Significa che un numero, da solo, non identifica uno stato. Quando leggi «6 Hz — Theta» stai leggendo una collocazione dentro una convenzione descrittiva, non una coordinata esatta di uno stato mentale.</p>",
  },
  ricerca: {
    title: 'Che cosa dice davvero la ricerca sugli stimoli ritmici uditivi',
    body:
      "<h4>Un campo reale, ma eterogeneo</h4><p>Gli stimoli ritmici uditivi — battiti binaurali, battiti monaurali, toni isocronici — sono studiati da decenni. Esistono ricerche su attenzione, memoria di lavoro, ansia percepita, rilassamento soggettivo e attività EEG.</p>" +
      "<h4>Perché i risultati non convergono</h4><p>Gli studi differiscono per frequenza del battito, frequenza portante, durata dell'esposizione, presenza o assenza di musica di sottofondo, tipo di misura (questionari, prestazione a un compito, EEG) e numero di partecipanti. Con protocolli così diversi, i risultati sono difficili da confrontare tra loro, e le revisioni della letteratura segnalano spesso effetti piccoli o incoerenti.</p>" +
      "<h4>La distinzione che regge tutto</h4><p class=\"warn\">Percepire chiaramente un battito è un fatto acustico e percettivo. Che quel battito porti stabilmente l'attività cerebrale alla stessa frequenza è un'affermazione molto più forte, che la ricerca disponibile non permette di dare per acquisita.</p>" +
      "<h4>Come lo trattiamo qui</h4><p>Descriviamo che cosa viene generato e come si percepisce. Dove la ricerca è aperta, lo diciamo — non è una cautela formale, è la parte più interessante del discorso.</p>",
  },
  fisica: {
    title: 'Binaurale e battimento acustico: due fenomeni diversi',
    body:
      "<h4>Quando i toni restano separati</h4><p>Con cuffie o auricolari stereo, il tono destro e il tono sinistro arrivano a due orecchie diverse senza mai incontrarsi nell'aria. La pulsazione che senti non è presente in nessuno dei due segnali: emerge dall'elaborazione del sistema uditivo. È il battito binaurale in senso classico.</p>" +
      "<h4>Quando i toni si incontrano nell'aria</h4><p>Dagli altoparlanti i due toni si sommano prima di raggiungerti, e la loro somma produce una variazione periodica di ampiezza: il battimento acustico, lo stesso fenomeno che usa chi accorda uno strumento a orecchio. È fisicamente presente nel suono, ed è per questo che continui a sentire una pulsazione anche senza cuffie.</p>" +
      "<h4>Perché la distinzione conta</h4><p>Il suono non «svanisce» senza cuffie: cambia natura. Quello che ascolti dalle casse è un fenomeno reale e udibile, ma non è più lo stimolo binaurale che gli studi sui binaural beats descrivono.</p>",
  },
  segnale: {
    title: 'Come viene costruito il segnale',
    body:
      "<h4>Il valore impostato è il valore generato</h4><p>Le frequenze non vengono scelte da una libreria di file preregistrati: vengono calcolate. Se imposti 6 Hz, la modulazione viene costruita a sei cicli al secondo secondo i parametri del sistema, e lo stesso vale per la frequenza portante.</p>" +
      "<h4>Le transizioni non spezzano il suono</h4><p>Quando una frequenza cambia nel corso di una sessione, il motore fa avanzare la fase in modo continuo invece di ricominciare da capo a ogni aggiornamento. È il motivo per cui una discesa graduale si sente come un movimento unico e non come una serie di scatti.</p>" +
      "<h4>Gli attacchi e le chiusure sono smussati</h4><p>L'inizio e la fine di ogni livello sono raccordati con brevi dissolvenze. Serve a evitare il click secco che si produce quando un suono viene acceso o interrotto di netto.</p>" +
      "<h4>Dove finisce la garanzia</h4><p class=\"warn\">Tutto questo riguarda il segnale digitale. Quello che accade dopo — la resa dell'impianto, il volume scelto, l'acustica della stanza, l'ascoltatore — non è governato dal sistema, e non permette di promettere a nessuno la stessa esperienza.</p>",
  },
};

// Glossario rapido: tre famiglie, definizioni di una o due frasi.
// `go` porta alla categoria corrispondente della biblioteca.
export const GLOSSARIO = [
  {
    fam: 'Le basi',
    voci: [
      { t: 'Hz (Hertz)', d: "L'unità che conta quanti cicli avvengono in un secondo. 6 Hz significa sei cicli al secondo; nei suoni udibili, più Hz corrispondono a un tono più acuto." },
      { t: 'EEG', d: "Elettroencefalogramma: la registrazione dell'attività elettrica del cervello raccolta da elettrodi sul cuoio capelluto. È lo strumento con cui si osservano i ritmi cerebrali." },
      { t: 'Modulazione', d: "La variazione regolare di un parametro del suono nel tempo, tipicamente il volume. È il meccanismo con cui un tono continuo diventa una pulsazione." },
      { t: 'Stereo', d: 'Due canali distinti, destro e sinistro. È la condizione che permette di inviare informazioni sonore diverse alle due orecchie.' },
    ],
  },
  {
    fam: 'Il cervello',
    voci: [
      { t: 'Banda cerebrale', d: "Un intervallo di frequenze usato per descrivere la distribuzione dell'attività EEG. È una categoria di analisi, non un suono e non uno stato mentale.", go: 'Bande cerebrali' },
      { t: 'Delta', d: 'La gamma più lenta, indicativamente 0,5–4 Hz. Nell\'EEG è associata soprattutto alle fasi di sonno profondo.', go: 'Bande cerebrali' },
      { t: 'Theta', d: "Indicativamente 4–8 Hz. Osservata nell'addormentamento, in alcune condizioni di quiete profonda e in compiti di memoria.", go: 'Bande cerebrali' },
      { t: 'Alpha', d: 'Indicativamente 8–13 Hz. È il ritmo tipico della veglia rilassata, particolarmente evidente a occhi chiusi.', go: 'Bande cerebrali' },
      { t: 'Beta', d: "Indicativamente 13–30 Hz. Attività più rapida, presente in molte condizioni di veglia attiva.", go: 'Bande cerebrali' },
      { t: 'Gamma', d: "Oltre i 30 Hz circa. Attività ad alta frequenza, studiata in relazione a percezione e attenzione.", go: 'Bande cerebrali' },
      { t: 'Entrainment', d: "Termine usato in neuroscienza per descrivere fenomeni di sincronizzazione tra un'attività ritmica e uno stimolo periodico. Applicato al suono, è un campo di ricerca aperto." },
    ],
  },
  {
    fam: 'Il suono e i metodi',
    voci: [
      { t: 'Battito binaurale', d: "Due toni leggermente diversi, uno per orecchio: il sistema uditivo percepisce una pulsazione pari alla loro differenza. Richiede cuffie o auricolari stereo.", go: 'Metodi' },
      { t: 'Battito monaurale', d: 'Due toni combinati prima della riproduzione: la pulsazione è già fisicamente presente nel segnale. Non richiede cuffie.', go: 'Metodi' },
      { t: 'Tono isocronico', d: 'Un tono singolo modulato ritmicamente, che produce impulsi regolari e chiaramente percepibili. Non richiede cuffie.', go: 'Metodi' },
      { t: 'Frequenza di battito', d: 'La pulsazione lenta di una sessione, tipicamente tra 0,5 e 40 Hz. È il valore che nomina la banda: «theta 6 Hz» si riferisce a questo.' },
      { t: 'Frequenza portante', d: 'Il tono udibile che porta il battito fino all\'orecchio. Nel binaurale la sua scelta incide sulla percezione del battito; negli altri metodi determina soprattutto il colore del suono.' },
      { t: 'Tono puro', d: 'Un suono costituito idealmente da una sola frequenza, senza pulsazione. È il punto di partenza più semplice per ascoltare una frequenza.', go: 'Metodi' },
      { t: 'Rumore rosa', d: "Un rumore continuo la cui energia decresce verso le frequenze acute. All'ascolto risulta più morbido del rumore bianco, e ricorda il respiro del mare.", go: 'Metodi' },
    ],
  },
];
