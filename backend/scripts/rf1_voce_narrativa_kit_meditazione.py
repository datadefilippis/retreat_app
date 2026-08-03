"""RF1 — la riscrittura narrativa. Prima ondata: il kit e la meditazione.

IL DIFETTO, detto dal founder e confermato dai numeri: "provando a
leggere l'articolo ogni tanto mi perdo, sembra scritto frettolosamente".
Il kit aveva 47 paragrafi in 1360 parole, media 29 parole a paragrafo.
Non e' un articolo, e' un elenco di elenchi. Il difetto non e' la
lunghezza ne' il contenuto: e' che tutto ha lo stesso peso, non c'e'
un filo, e chi legge non viene portato da nessuna parte.

LO STANDARD, che vale da qui in avanti per tutto il Magazine.

1. L'APERTURA E' UNA SCENA, non un enunciato di argomento. Chi legge
   deve riconoscersi in qualcosa nelle prime tre righe. "C'e' un
   equivoco che blocca quasi tutti" e' un enunciato; la sveglia messa
   alle sei che il terzo giorno viene spostata e' una scena.

2. LE SEZIONI SI TENGONO PER MANO. Ogni sezione apre con una riga che
   raccoglie quella prima o prepara quella dopo. Senza ponti si legge
   una raccolta di schede.

3. LE PRATICHE SI GUIDANO, NON SI ELENCANO. Un protocollo numerato in
   frammenti — "Siediti comodo. Timer a 5 minuti." — e' un promemoria
   per chi sa gia' fare. Chi non sa fare ha bisogno di una voce che
   accompagna: cosa fai, cosa senti, cosa succede quando va storto,
   quanto dura. E' la parte che il founder ha nominato per prima, ed
   e' quella su cui questo lavoro si misura.

4. IL GRASSETTO TORNA A ESSERE UN'ECCEZIONE. Serve per gli elenchi di
   cose davvero parallele, non come sostituto della punteggiatura.
   Trenta grassetti per articolo non evidenziano niente.

5. NIENTE PAROLE INUTILI. La prosa non e' la prolissita': ogni riga
   aggiunta deve aggiungere un'istruzione, una sensazione o un
   perche'. Si taglia mentre si espande.

ALTRO CHE ESCE DAL KIT, trovato riscrivendo: "la verita' che vediamo
ogni giorno negli operatori della nostra rete" — un'osservazione che
non abbiamo fatto, come il dato inventato sulle caparre — e "quando
apriremo le prenotazioni, chi e' iscritto alla lettera sara' il primo
a saperlo", che e' una promessa della fase marketplace.

    venv/bin/python scripts/rf1_voce_narrativa_kit_meditazione.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

KIT = "kit-pratiche-quotidiane-15-minuti"
MEDIT = "meditazione-per-chi-inizia-guida-semplice"

CAMMINI = "/blog/camminare-bagni-di-foresta-cammini"
MINDFUL = "/blog/mindfulness-cose-mbsr-come-funziona"
NIDRA = "/blog/yoga-nidra-cose-come-funziona-una-sessione"
STILI = "/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"

TITOLO_K = "Quindici minuti al giorno: sette pratiche spiegate per bene"
DESCR_K = (
    "Sette pratiche brevi guidate passo passo — respiro, meditazione, scan, "
    "camminata, scrittura — con cosa si sente e cosa va storto."
)

CONTENUTO_K = f"""\
La sveglia suona alle sei e mezza invece che alle sette. Ti siedi sul bordo del letto con la migliore delle intenzioni, fai dieci minuti di qualcosa, e ti senti pure bene. Il secondo giorno funziona ancora. Il terzo giorno hai dormito male, la sveglia torna alle sette, e la pratica finisce nel cassetto dei buoni propositi insieme all'abbonamento in palestra.

Succede a quasi tutti, e non è una questione di disciplina. È che le pratiche vengono quasi sempre insegnate come esercizi da eseguire — una lista di passaggi, un tempo, un obiettivo — invece che come cose da imparare a fare, con la loro goffaggine iniziale e i loro inciampi prevedibili.

Questa guida raccoglie sette pratiche brevi, e prova a fare l'opposto: per ognuna trovi cosa fai davvero, cosa senti mentre lo fai, cosa succede quando va storto, e in quanto tempo la cosa comincia a cambiare qualcosa. Alla fine ci sono tre modi di combinarle in un quarto d'ora.

Nessuna richiede attrezzatura, un maestro o un posto silenzioso.

## Prima di cominciare: una sola

C'è un modo sbagliato di usare questa pagina, ed è provarle tutte lunedì.

Il modo che funziona è scegliere **una** pratica — quella che leggendo ti fa dire «questa potrei farla» — e tenerla per due settimane. Non trenta giorni: due settimane, che è il tempo in cui un gesto smette di richiedere una decisione.

E agganciala a qualcosa che già fai. Non «alle sette del mattino», ma «dopo aver messo su il caffè», «prima della doccia», «appena chiudo il portatile». L'ora del giorno è una promessa che si rompe; un gesto che già compi è un gancio che regge.

La routine completa da quindici minuti, in fondo alla pagina, è un punto di arrivo. Chi parte da lì di solito arriva al giovedì.

Una cosa che vale per tutto il kit: queste pratiche sostengono il benessere, non sostituiscono un percorso medico o psicologico. Se stai attraversando un momento difficile, usale accanto a un professionista, non al posto suo.

## 1. Il respiro che spegne l'allarme

*Due minuti, in piedi o seduto, ovunque.*

È la pratica da conoscere per prima perché è l'unica che agisce in tempo reale: si usa mentre la cosa sta succedendo. Prima di una telefonata che rimandi da due giorni, dopo un messaggio che ti ha fatto salire il sangue alla testa, in macchina prima di entrare in casa.

**Come si fa.** Inspira dal naso come faresti normalmente. Quando senti di aver finito, e ti sembrerà di non avere più spazio, aggiungi **un secondo piccolo sorso d'aria**: breve, dal naso, come se rubassi un ultimo goccio. Poi lascia andare tutto dalla bocca, lentamente, con un'espirazione lunga — più lunga dell'inspirazione, senza contare, finché l'aria finisce da sola.

Poi ricomincia. Tre volte bastano per sentire qualcosa. Due minuti sono il formato pieno.

**Cosa senti.** Il secondo sorso è strano le prime volte: sembra che non ci stia. Poi entra, e la sensazione è di uno spazio che si apre nel torace. Sull'espirazione lunga molte persone notano le spalle che scendono da sole, senza averlo deciso. Chi è molto attivato può sentire un attimo di vertigine: rallenta e basta.

**Cosa va storto.** L'errore è uno solo, ed è sempre lo stesso: fare inspirazioni enormi e teatrali. Il primo respiro è normale, il secondo sorso è **piccolo**. Il lavoro vero lo fa l'espirazione.

**Cosa dice la ricerca.** Uno studio randomizzato di Stanford ha confrontato tre tecniche di respiro con una pratica di mindfulness: questo pattern, chiamato *cyclic sighing*, è risultato il più efficace nel migliorare l'umore e abbassare la frequenza respiratoria a riposo, con cinque minuti al giorno (Balban e colleghi, *Cell Reports Medicine*, 2023).

## 2. Cinque minuti seduti

*Cinque minuti, seduto, con un timer.*

Se la pratica precedente è il pronto soccorso, questa è il lavoro di fondo: non serve a spegnere un incendio, serve a fare in modo che gli incendi si accendano meno.

**Come si fa.** Siediti su una sedia normale, piedi a terra, schiena appoggiata se serve. Metti un timer a cinque minuti e appoggialo lontano dalla mano, così non lo guardi.

Chiudi gli occhi e trova il punto in cui **senti** il respiro di più: per qualcuno è l'aria fresca alle narici, per altri il petto che si alza, per altri ancora la pancia. Non è importante quale: importa che sia un punto solo. Resta lì.

Dopo pochi secondi — pochi, non minuti — ti accorgerai di stare pensando ad altro. Quando succede, e succederà cinquanta volte, nota in silenzio *«pensiero»* e torna al punto che avevi scelto. Senza commentare, senza riprenderti: anche il rimprovero è un altro pensiero.

Al timer, prima di alzarti, resta fermo dieci secondi e nota com'è il corpo rispetto a cinque minuti fa. È il passaggio che quasi tutti saltano ed è quello che costruisce l'abitudine, perché è lì che il cervello registra che è servito a qualcosa.

**Cosa senti.** Nei primi minuti quasi sempre irrequietezza: prude il naso, la posizione non va bene, ti ricordi una mail. È normale ed è la pratica. Verso la fine, in molte sessioni, qualcosa si posa — non sempre, e le sessioni in cui non succede contano uguale.

**Cosa va storto.** Giudicare la sessione. «Oggi è andata male» non esiste: una sessione in cui la mente è scappata cinquanta volte e tu sei tornato cinquanta volte è una sessione riuscita cinquanta volte. Il ritorno **è** l'esercizio, non l'interruzione dell'esercizio.

**Cosa dice la ricerca.** È fra le pratiche più studiate. Le meta-analisi mostrano effetti moderati ma consistenti su ansia, sintomi depressivi e dolore (Goyal e colleghi, *JAMA Internal Medicine*, 2014). Moderati: non miracolosi, e costruiti sulla costanza più che sulla durata delle sessioni.

Se vuoi capirla meglio, ne parliamo per esteso nella [guida alla meditazione](/blog/{MEDIT}) e nella [guida alla mindfulness]({MINDFUL}).

## 3. Il giro del corpo

*Tre minuti, seduto o sdraiato. La pratica della sera.*

Quella di prima allena l'attenzione a stare ferma. Questa la manda in giro, ed è più facile per chi con il respiro si annoia.

**Come si fa.** Chiudi gli occhi e porta l'attenzione ai **piedi**. Non a immaginarli: a sentirli. La pressione sul pavimento o sul materasso, il calore, il contatto con il calzino. Due respiri.

Poi sali, una zona alla volta, con due o tre respiri ciascuna: polpacci, ginocchia, cosce, bacino, schiena bassa, pancia, petto, spalle, braccia, mani, collo, mascella, fronte, cima della testa.

Dove trovi tensione non provare a scioglierla. Restaci un respiro in più e vai avanti. Molte volte si scioglie da sola quando smetti di combatterla; quando non lo fa, va bene lo stesso, e non è un fallimento.

**Cosa senti.** In alcune zone non sentirai niente, e «niente» è una risposta legittima: annotala mentalmente e passa oltre. Quasi tutti scoprono un punto che tenevano contratto senza saperlo — la mascella e le spalle sono i due candidati più frequenti.

**Cosa va storto.** Andare troppo veloce. Tre minuti sembrano pochi per quindici zone, e infatti la versione da tre minuti si fa a gruppi: tutta la gamba, tutto il tronco, tutto il braccio. La versione lenta, zona per zona, vuole venti minuti ed è un'altra pratica.

**Quando usarla.** A letto, partendo dalla testa e scendendo verso i piedi, è fra le cose più efficaci contro il pensiero che gira di notte. E nei momenti in cui ti accorgi di essere «solo testa», seduto alla scrivania da tre ore.

## 4. Cinque cose che vedi

*Un minuto, ovunque, a occhi aperti.*

Questa è la pratica di emergenza, e a differenza delle altre non richiede di chiudere gli occhi né di essere da soli. Si fa in fila alla posta, in ascensore, in mezzo a una discussione.

**Come si fa.** Conta, in silenzio e una alla volta:

Cinque cose che **vedi**. Non uno sguardo d'insieme: cinque oggetti distinti, guardati per un secondo ciascuno.

Quattro cose che **senti sulla pelle**. I piedi dentro le scarpe, l'elastico dell'orologio, l'aria sul dorso della mano, il tessuto sulla schiena.

Tre **suoni**. Anche il ronzio del frigorifero.

Due **odori**. Se non ne trovi due, cercali: è parte dell'esercizio.

Un **sapore**. Anche solo quello che hai in bocca adesso.

**Cosa senti.** Verso il terzo passaggio la testa si stacca dal pensiero che stava macinando. Non perché sia stato risolto: perché il canale che stava usando è occupato da altro.

**Perché funziona.** L'attenzione sensoriale interrompe la ruminazione — il pensiero che gira su sé stesso — occupandone lo spazio. È una tecnica di ancoraggio usata anche in ambito clinico negli stati d'ansia acuta, ed è il motivo per cui funziona anche quando sei convinto che non funzionerà.

## 5. Dieci minuti a piedi

*Dieci minuti, fuori, senza cuffie.*

Se stare seduti è il tuo ostacolo, questa sostituisce tutte le altre. È la stessa attenzione, in movimento, e per molte persone è l'unica che sopravvive nel tempo.

**Come si fa.** Esci e cammina al tuo passo naturale. Niente telefono in mano, niente cuffie, niente podcast: è la parte difficile e non è negoziabile.

Per i primi due minuti l'attenzione sta **solo sui piedi**. Il tallone che tocca, il peso che rotola in avanti, la spinta dell'avampiede, il piede che si stacca. Un piede, poi l'altro, come un metronomo lento.

Dopo due minuti allarga: l'aria sulla faccia, i suoni, quello che entra nel campo visivo. Non descrivere niente a parole, solo lascia arrivare.

Quando la testa riparte con i pensieri — e ripartirà — torna ai piedi. I piedi sono il tuo punto di ritorno, come il respiro nella pratica seduta.

**Cosa senti.** I primi due minuti sono i più goffi: camminare pensando a come cammini rende il passo innaturale. Passa da solo verso il terzo minuto, quando l'attenzione smette di controllare e comincia a osservare.

**Cosa dice la ricerca.** L'attività fisica leggera e regolare è uno dei fattori più solidi per umore e sonno, e farla in un ambiente naturale amplifica l'effetto sulla ruminazione (Bratman e colleghi, *PNAS*, 2015). Se l'idea ti prende, [camminare come pratica]({CAMMINI}) è un mondo intero.

## 6. Tre minuti di scrittura, la sera

*Tre minuti, carta e penna, prima di dormire.*

Non è tenere un diario, e non serve saper scrivere. Serve a svuotare la testa prima di coricarla, così che non debba farlo lei alle tre di notte.

**Come si fa.** Carta e penna, non il telefono: il telefono apre altre dieci cose e la pratica muore lì.

Scrivi per tre minuti rispondendo a due domande soltanto: **cosa mi porto di oggi** e **cosa lascio qui**. Scrivi di getto, senza rileggere, senza curare la forma, anche frasi mozze. Nessuno lo leggerà, tu compreso.

Poi chiudi il quaderno. Il gesto di chiuderlo conta quanto quello di scrivere, e chi lo salta se ne accorge.

**Cosa senti.** Le prime sere sembra un compito. Dalla quarta o quinta, di solito, comincia a uscire qualcosa che non sapevi di avere in testa — ed è quello il momento in cui la pratica smette di essere un esercizio.

**Una variante che ha dei numeri alle spalle.** Al posto delle due domande, tre cose precise per cui sei grato oggi. Precise: non «la famiglia», ma «la telefonata di mia sorella mentre tornavo a casa». Gli studi di Emmons e McCullough sulla gratitudine mostrano effetti misurabili su benessere percepito e qualità del sonno quando la pratica è regolare. Il dettaglio conta più della quantità.

## 7. La mezz'ora che non guardi

*Zero minuti, ed è la più difficile.*

L'unica pratica del kit che consiste nel non fare: niente telefono per i primi trenta minuti dopo il risveglio.

**Come si fa, davvero.** Il primo passo non è la forza di volontà, è togliere il telefono dalla stanza. Finché è la tua sveglia, questa pratica non esiste: la spegni e sei dentro.

Compra una sveglia da dieci euro. Metti il telefono a caricare in un'altra stanza, o almeno dall'altra parte della camera, dove per prenderlo devi alzarti e fare cinque passi. Quei cinque passi sono tutta la tecnica.

Nei trenta minuti che si liberano non devi infilare nient'altro. Ci stanno il respiro della pratica numero uno, il caffè fatto con calma, la doccia, guardare fuori. Non serve riempirli: serve non riempirli di quello che decidono gli altri.

**Cosa senti.** I primi tre giorni la mano va al comodino da sola, ed è impressionante quanto sia automatico. Dalla settimana successiva, la maggior parte delle persone descrive le mattine come «più lunghe», che è una cosa curiosa da dire di una durata identica.

**Perché è nel kit.** Cominciare la giornata dentro il proprio filo, invece che dentro quello di qualcun altro, è il moltiplicatore silenzioso di tutte le altre sei.

## Tre modi di metterle insieme

Quando una pratica è diventata automatica, e non prima, si può comporre.

**Il mattino, quindici minuti.** Il telefono resta dov'è. Due minuti di respiro appena seduto sul letto, cinque minuti di pratica seduta, e otto minuti di camminata — anche solo fino al bar e ritorno.

**La giornata di lavoro, tre minuti sparsi.** Un minuto di respiro prima di ogni conversazione che ti pesa. Un minuto di cinque sensi nei passaggi fra una cosa e l'altra. Dieci minuti a piedi in pausa pranzo, se ci sono.

**La sera, dieci minuti.** Cinque minuti di camminata dopo cena, tre di scrittura, due di giro del corpo già a letto. Su quest'ultima quasi nessuno arriva ai piedi, ed è esattamente il punto.

## Quando quindici minuti non bastano

C'è un limite, e vale la pena dirlo. Un quarto d'ora al giorno costruisce e mantiene, ma certe soglie si attraversano solo con l'immersione: qualche giorno di pratica continuata, senza telefono, con qualcuno che conduce e un gruppo intorno, porta in profondità in poco tempo quello che a casa chiede mesi.

Non è un punto di partenza ed è un buon punto di arrivo. Se lo stai valutando, la scelta di chi conduce pesa più del luogo — i criteri stanno in [come capire se un operatore è serio]({SERIO}) e le domande da fare prima di prenotare [qui]({DOMANDE}).

## Domande frequenti

**Quanto tempo prima di vedere qualcosa?**
La calma dopo la singola sessione arriva subito. I cambiamenti che restano — sonno, reattività allo stress — chiedono dalle quattro alle otto settimane di costanza. Chi promette meno sta promettendo altro.

**Meglio la mattina o la sera?**
Il momento in cui la fai davvero. La mattina ha un vantaggio pratico: nessuna giornata storta può cancellarla.

**Ho saltato tre giorni, ricomincio da capo?**
No, e questa domanda è il motivo per cui molti mollano. Riprendi oggi, con la versione più corta che riesci a fare, anche due minuti. La continuità si misura sui mesi, non sui giorni.

**Le app vanno bene?**
Per cominciare sì: una voce che guida è una stampella utile quando non sai cosa fare. Dopo qualche settimana prova il silenzio con un timer semplice, che è una pratica diversa e più tua.

**Devo farle tutte e sette?**
No, ed è il fraintendimento più costoso. Una pratica fatta tutti i giorni vale più di sette provate una volta.

**Sono agitato e non riesco a stare fermo.**
Comincia dalla camminata o dai cinque sensi, non dalla pratica seduta. Chiedere immobilità a un corpo attivato è il modo più veloce per concludere che «non fa per te».
"""

TITOLO_M = "Meditazione per chi inizia: come cominciare e cosa aspettarsi"
DESCR_M = (
    "La pratica guidata passo passo, come si sta seduti, le famiglie di "
    "meditazione, cosa dice la ricerca e cosa fare se smuove qualcosa."
)

CONTENUTO_M = f"""\
Quasi tutti quelli che hanno provato a meditare e hanno smesso raccontano la stessa scena. Si siedono, chiudono gli occhi, e dopo venti secondi si accorgono di stare pensando alla lavatrice. Ci riprovano, e dopo altri venti secondi è la mail di ieri. Al terzo giro arriva il pensiero che chiude tutto: *«non ci riesco, penso troppo»*.

Ed è qui che vale la pena fermarsi, perché quella frase descrive una meditazione riuscita.

Il malinteso è sul cosa sia l'esercizio. Non è tenere la mente vuota — non ci riesce nessuno, e chi dice il contrario ricorda male. L'esercizio è il momento in cui **ti accorgi** che la mente se n'è andata e la riporti indietro. Quello, ripetuto. Una sessione in cui succede cinquanta volte è una sessione da cinquanta ripetizioni.

Questa guida racconta come si fa, come si sta seduti, quali famiglie di meditazione esistono e in cosa differiscono, cosa dice la ricerca — e una parte che si legge di rado, su cosa fare se la pratica smuove qualcosa di scomodo.

## La pratica, passo per passo

Cinque minuti. Non trenta: cinque. Chi comincia da mezz'ora al terzo giorno non si siede più.

**Prepara.** Siediti su una sedia normale, con i piedi a terra e la schiena appoggiata se ti serve. Metti un timer a cinque minuti e appoggialo lontano dalla mano, perché altrimenti lo guarderai.

**Trova il punto.** Chiudi gli occhi e cerca dove **senti** il respiro con più chiarezza. Per alcuni è l'aria che entra fresca alle narici, per altri il petto che si allarga, per altri la pancia che si muove. Non è importante quale sia, è importante che sia uno solo. Appoggia lì l'attenzione, come si appoggia una mano.

**Lascia respirare.** Non modificarlo, non allungarlo, non contarlo. Il respiro fa il suo lavoro da solo da tutta la vita: qui lo guardi soltanto.

**Aspettati di perderti, presto.** Dopo pochi secondi sarai altrove. È il funzionamento normale di una mente, non un difetto tuo.

**Torna.** Quando te ne accorgi, nota mentalmente *«pensiero»* — una parola, non un discorso — e riporta l'attenzione al punto. Senza rimproverarti: il rimprovero è solo un altro pensiero che ti porta via una seconda volta.

**Chiudi bene.** Al timer, resta fermo dieci secondi prima di alzarti e nota com'è il corpo rispetto a cinque minuti fa. È il passaggio che quasi tutti saltano ed è quello che fa attaccare l'abitudine, perché è lì che registri di aver ottenuto qualcosa.

Fai così tutti i giorni per due settimane, agganciato a un gesto che già compi — dopo il caffè, prima della doccia. Non serve altro, e soprattutto non serve niente di più lungo.

## Come si sta seduti

Sembra un dettaglio finché non arrivano i venti minuti in cui la schiena comincia a parlare.

**La sedia** è la soluzione più sottovalutata e la più pratica. Piedi a terra, mani sulle cosce, schiena appoggiata se serve. Funziona per chiunque, non ha controindicazioni, e l'unico suo difetto è che sembra troppo ordinaria per essere giusta.

**Il cuscino**, seduti a terra, chiede una cosa sola: che il bacino stia **più in alto delle ginocchia**. È questo che permette alla schiena di stare dritta senza sforzo, non l'incrocio delle gambe. Vanno bene un cuscino da meditazione, due cuscini del divano o una coperta piegata in quattro. Il difetto è che senza abitudine, dopo dieci minuti, le gambe si addormentano e l'unica cosa che osservi è la scomodità.

**Sdraiato** è legittimo, soprattutto con dolori alla schiena, e ha un difetto ovvio: ci si addormenta. Se ti succede sempre e la cosa non ti dispiace, quello che stai cercando somiglia più allo [yoga nidra]({NIDRA}), che si pratica proprio da sdraiati e non considera il sonno un errore.

La regola sotto tutte e tre: la posizione deve reggere per il tempo che hai deciso. Se la stai correggendo di continuo, stai meditando sulla posizione.

## Le famiglie

«Meditazione» è un cognome, non un nome. Sotto ci stanno pratiche che fanno cose diverse, e sapere quale hai davanti evita di concludere che una cosa non fa per te quando ne hai provata un'altra.

La **concentrazione** tiene l'attenzione su un oggetto solo — il respiro, un suono, una fiamma — e ci torna ogni volta. È la porta d'ingresso di quasi tutte le tradizioni, ed è la pratica descritta qui sopra.

La **visione profonda**, la vipassana, non resta su un oggetto: osserva quello che passa — sensazioni, pensieri, impulsi — uno dopo l'altro, senza seguirlo. Nella forma tradizionale si pratica in ritiri di dieci giorni in silenzio.

La **mindfulness** è la versione laica e strutturata della vipassana, codificata alla fine degli anni Settanta in ambito ospedaliero. È la forma più studiata di tutte e ne parliamo [per esteso qui]({MINDFUL}).

L'**amorevolezza**, o metta, ripete mentalmente frasi di augurio rivolte prima a sé, poi a una persona cara, poi a una neutra, poi a una difficile. Suona sentimentale e non lo è: è la pratica con gli effetti più misurabili su umore e reattività.

La **meditazione trascendentale** ripete internamente un mantra ricevuto da un insegnante, venti minuti due volte al giorno, dentro un percorso a pagamento con una struttura organizzativa propria.

Le **meditazioni guidate** accompagnano con una voce dentro un'immagine o un percorso interiore. Sono utilissime per cominciare, e fanno una cosa diversa dalla pratica silenziosa.

Le **pratiche in movimento** — camminata meditativa, e in senso lato il lavoro sul [respiro dello yoga]({PRANA}) — sono spesso la porta per chi l'immobilità non la sopporta.

Nessuna è migliore. La domanda utile è una sola: quale riesco a fare tutti i giorni.

## Cosa dice la ricerca

È la pratica di questo mondo con la letteratura più ampia, e proprio per questo conviene distinguere invece di prendere il pacchetto intero.

Le prove più solide riguardano la **riduzione dello stress percepito e dei sintomi d'ansia**, il **miglioramento della qualità del sonno** e una maggiore capacità di regolare le emozioni. I programmi strutturati di otto settimane sono fra gli interventi non farmacologici più studiati degli ultimi decenni, ed esiste una letteratura sull'uso della mindfulness nella prevenzione delle ricadute depressive, entrata in alcune linee guida cliniche come intervento di accompagnamento.

Più incerti sono gli effetti su pressione arteriosa, dolore cronico e prestazioni cognitive: esistono, e sono modesti e variabili.

C'è poi un limite che attraversa tutto il campo ed è onesto conoscere: molti studi confrontano la meditazione con il non fare nulla, invece che con un'altra attività di pari impegno. Quando il confronto è con un programma attivo, le differenze si assottigliano. Il che non toglie valore alla pratica: significa che una parte dell'effetto è lo stare fermi mezz'ora con attenzione, e quella è una cosa che quasi nessuno fa.

## Quando la pratica smuove qualcosa

Questa parte si legge di rado e serve.

La meditazione ha effetti indesiderati documentati. Un gruppo di ricerca guidato da Willoughby Britton se ne occupa da anni, e uno studio pubblicato su *JAMA Psychiatry* nel 2022 su un campione di popolazione ha trovato che una quota non trascurabile di chi pratica riporta almeno un episodio di questo tipo: ansia che cresce invece di calare, senso di distacco da sé o dalla realtà, riemersione di ricordi o emozioni dolorose, sonno peggiorato, a volte un senso di vuoto.

Tre cose vanno tenute insieme. Sono quasi sempre **transitori**, e nella maggior parte delle persone passano da soli. Sono più probabili con **pratiche lunghe e intensive**, nei ritiri in silenzio, e in chi ha una storia di trauma o di dissociazione — ed è il motivo per cui un ritiro di dieci giorni non è il posto da cui cominciare. E soprattutto: **saperlo cambia come li si attraversa**, perché chi li incontra senza averne mai sentito parlare tende a concludere di essere rotto, e smette in silenzio.

Se succede, la cosa da fare è concreta: accorcia la sessione, apri gli occhi, passa a una pratica in movimento o a una guidata, e parlane con qualcuno. Se attraversi un periodo difficile o hai una storia di trauma, comincia accompagnato da chi ha una formazione specifica su quel terreno — è uno dei casi in cui [scegliere bene chi ti guida]({SERIO}) conta più della tecnica.

E vale la regola generale: la meditazione affianca un percorso di cura, non lo sostituisce.

## I tre modi in cui si molla

Riconoscerli in anticipo è metà del lavoro.

Il primo è **aspettarsi il rilassamento**. A volte arriva, a volte no. Meditare non è rilassarsi, è osservare; il rilassamento è un effetto collaterale frequente, non l'obiettivo, e cercarlo trasforma ogni sessione in un esame.

Il secondo è **dare i voti alle sessioni**. Non esistono sessioni andate male: esistono sessioni in cui la mente era agitata e tu le hai fatto compagnia comunque, e sono le più utili.

Il terzo è **la terza settimana**, quando l'entusiasmo è finito e l'abitudine non si è ancora formata. Sapere che quel momento arriva è quasi tutta la soluzione: quando arriva, riduci a tre minuti, ma non saltare.

## Meditare senza sedersi

È la pratica che tiene in vita l'abitudine nelle settimane in cui quella seduta salta, e in molte tradizioni è considerata il vero obiettivo: portare la stessa attenzione dentro le cose che fai già.

**Lavare i piatti.** Acqua, temperatura, peso del piatto, rumore. Quando la mente parte, torni alle mani.

**Camminare.** Cento metri senza telefono, sentendo il piede che appoggia. Anche solo dal parcheggio all'ufficio.

**Tre respiri.** Prima di aprire una porta, prima di rispondere a un messaggio che ti ha irritato, prima di mangiare. Tre respiri interi, contati.

**Aspettare.** Alla cassa, al semaforo, in coda. Il momento in cui l'istinto è tirare fuori il telefono è esattamente il momento di praticare.

Non sostituiscono la pratica seduta, che resta il posto dove si costruisce il muscolo. Si incastrano bene con le altre pratiche brevi del [kit dei quindici minuti](/blog/{KIT}).

## Come si va avanti

**Le prime tre settimane, cinque minuti.** L'unico obiettivo è esserci tutti i giorni. Com'è andata non conta.

**Dalla quarta all'ottava, dieci minuti.** Qui la maggior parte delle persone comincia a notare qualcosa fuori dalla sessione: una reazione che non è partita, un sonno più semplice.

**Dopo il secondo mese, venti minuti o due sessioni.** È la soglia in cui molte tradizioni collocano il punto in cui la pratica cambia qualità.

**Un insegnante** ha senso quando vuoi approfondire una famiglia specifica, quando la pratica smuove qualcosa, o quando sei fermo da mesi senza capire perché.

**Un ritiro** porta in profondità in pochi giorni quello che a casa chiede mesi, e non è il punto di partenza: è un acceleratore per chi ha già un'abitudine. Se lo stai valutando, chi conduce pesa più del luogo — i criteri stanno in [come capire se un operatore è serio]({SERIO}) e le domande da fare [qui]({DOMANDE}).

E se stare seduti resta l'ostacolo vero, [lo yoga nidra]({NIDRA}) si pratica da sdraiati e ammette perfino di addormentarsi; se invece stai valutando una pratica sul tappetino, [le differenze fra i tipi di yoga]({STILI}) spiegano cosa cambia da una lezione all'altra.

## Domande frequenti

**Quanto tempo serve per vedere i benefici?**
Con cinque o dieci minuti quotidiani, la maggior parte delle persone nota qualcosa su sonno, reattività e lucidità entro tre o quattro settimane. Il cambiamento è graduale: si vede meglio guardando indietro di due mesi che di due giorni.

**Meglio la mattina o la sera?**
Il momento in cui la fai davvero. La mattina ha un vantaggio pratico: la giornata non ha ancora avuto il tempo di travolgerti.

**Ho bisogno di un insegnante?**
Per iniziare no, i cinque minuti descritti qui bastano. Diventa prezioso quando vuoi approfondire, quando la pratica smuove qualcosa, o quando sei fermo senza capire perché.

**Che differenza c'è fra meditazione e mindfulness?**
La [mindfulness]({MINDFUL}) è un tipo di meditazione, resa laica e strutturata in protocolli. La meditazione è la famiglia grande: dentro ci sono anche concentrazione, amorevolezza, mantra e pratiche devozionali.

**Da quale famiglia conviene cominciare?**
Dalla concentrazione sul respiro, che è la più semplice da spiegare e la più difficile da sbagliare. Le altre hanno senso dopo, quando la pratica c'è.

**È normale addormentarsi?**
Sì, soprattutto la sera e da sdraiati. Se succede sempre, prova seduto e a un'altra ora.

**Meditare può fare male?**
In una minoranza di casi la pratica intensiva porta ansia, distacco o riemersione di materiale doloroso, quasi sempre transitori. Con sessioni brevi il rischio è basso; con una storia di trauma conviene essere accompagnati.

**Serve credere in qualcosa?**
No. Concentrazione e mindfulness sono laiche e non richiedono adesione a nessuna tradizione, anche quando da una tradizione provengono.

**Devo lavorare sui chakra mentre medito?**
No, sono due cose distinte. La mappa dei [chakra]({CHAKRA}) può essere usata come guida dell'attenzione da chi la trova utile, e non è parte del protocollo di base.
"""

PEZZI = [
    (KIT, TITOLO_K, DESCR_K, CONTENUTO_K),
    (MEDIT, TITOLO_M, DESCR_M, CONTENUTO_M),
]

RESIDUI = ["vediamo ogni giorno negli operatori", "quando apriremo le prenotazioni",
           "dalla nostra esperienza", "stiamo riunendo"]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto in PEZZI:
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not doc:
            print(f"ASSENTE: {slug}")
            continue
        pr, do = doc["content"], contenuto
        misura = lambda t: (len(t.split()),
                            len([p for p in t.split("\n\n") if p.strip()]),
                            t.count("**") // 2)
        p1, g1, b1 = misura(pr)
        p2, g2, b2 = misura(do)
        print(f"{titolo}")
        print(f"  parole {p1} → {p2}   paragrafi {g1} → {g2}   "
              f"grassetti {b1} → {b2}")
        print(f"  parole per paragrafo: {p1/g1:.0f} → {p2/g2:.0f}")
        if pr == do:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya",
            "updated_at": datetime.now(timezone.utc)}})
        print("  riscritto")

    print("\n── controlli")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    res = [(a["slug"], f) for a in arts for f in RESIDUI
           if f.lower() in a["content"].lower()]
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  rivendicazioni e promesse vecchie: {res or 'nessuna'}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
