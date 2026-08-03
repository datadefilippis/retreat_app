"""RF5 — voce narrativa, seconda meta' della quarta ondata.

Camminare (80%, 8 frammenti), ciclo mestruale (78%, 8), domande prima
di prenotare (83%, 10).

LE DUE PRATICHE, che sono il motivo di questa ondata.

IL BAGNO DI FORESTA era sei righe puntate: vai piano, niente meta,
telefono spento, un senso alla volta, fermati spesso, due ore. E'
la pratica piu' facile da spiegare male, perche' la difficolta' vera
non e' capire cosa fare — e' reggere la lentezza. Ora e' guidata dai
primi passi all'ultima mezz'ora, con quello che succede alla testa in
mezzo: la prima mezz'ora in cui continua a produrre liste, il momento
in cui ci si annoia (che quasi nessuno nomina, ed e' il passaggio), e
la parte finale in cui molte persone smettono di pensare in frasi.

IL DIARIO DEL CICLO era quattro punti. Ora e' una pratica
accompagnata, con il perche' dietro ogni regola — in particolare
quella di non guardare i dati prima del terzo mese, che serve a non
cercare conferme in un materiale che si presta benissimo a darne.

DOMANDE PRIMA DI PRENOTARE resta un articolo a domande, perche' li'
l'elenco E' l'informazione: si consulta prima di scrivere a qualcuno.
Ma le domande hanno smesso di essere frammenti isolati e stanno dentro
un ragionamento per gruppi, con l'apertura che spiega perche' quasi
nessuno le fa.

    venv/bin/python scripts/rf5_voce_narrativa_ondata4b.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

CAMMINARE = "camminare-bagni-di-foresta-cammini"
CICLO = "ciclo-mestruale-quattro-fasi-come-ascoltarlo"
DOMANDE_S = "domande-da-fare-prima-di-prenotare-un-ritiro"

MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
CAMMINI_IT = "/blog/cammini-italiani-quale-scegliere-la-prima-volta"
CERCHI = "/blog/cerchi-di-donne-cosa-sono-come-funzionano"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
PREZZO = "/blog/prezzo-giusto-ritiro-come-calcolarlo"
BREATH = "/blog/breathwork-cose-tecniche-benefici"

TITOLO_CA = "Camminare come pratica: bagni di foresta, cammini, natura"
DESCR_CA = (
    "Il bagno di foresta guidato passo passo, la camminata meditativa, i "
    "cammini di più giorni e quanto tempo serve stare fuori davvero."
)

CONTENUTO_CA = f"""\
Di tutte le pratiche di cui si parla in questo Magazine, questa è l'unica che puoi cominciare adesso: senza prenotare, senza pagare, senza trovare qualcuno che te la insegni.

Probabilmente è anche il motivo per cui se ne parla poco. Non c'è un corso da vendere, non c'è un attestato da esporre, e in fondo alla pagina non c'è niente da prenotare. Eppure camminare è fra le pratiche con le prove migliori di tutto questo mondo — meglio di parecchie cose che si pagano care.

Questa guida racconta tre modi di camminare che non sono spostarsi: il bagno di foresta, la camminata meditativa e il cammino di più giorni. E poi cosa dice la ricerca su quanto tempo serva stare fuori, che è meno di quanto pensi.

## Il bagno di foresta

*Shinrin-yoku*, letteralmente «immergersi nell'atmosfera della foresta»: stare in un bosco senza meta e senza scopo, lasciando che i sensi facciano il lavoro.

Prima di come si fa, una precisazione che serve, perché viene venduto come pratica millenaria giapponese. **Il termine è stato coniato nel 1982 dall'agenzia forestale giapponese**, dentro un programma di salute pubblica. Non è antico. E il fatto che sia nato come politica sanitaria è anzi la ragione per cui è stato studiato sul serio: il Giappone ci ha investito ricerca invece che marketing.

### Come si fa

La differenza con una passeggiata sta tutta nel ritmo, e il ritmo è la parte difficile. Non perché sia complicato andare piano, ma perché andare così piano è innaturale e per la prima mezz'ora ti sembrerà di perdere tempo.

**Lascia il telefono spento, non silenzioso.** Un telefono acceso in tasca continua a occupare una parte dell'attenzione, anche se non vibra: sai che potrebbe.

**Entra nel bosco e fermati dopo venti passi.** Prima di camminare, sta' fermo un minuto: è il modo più veloce per far scendere il ritmo dai piedi in su.

**Poi cammina lentissimo.** Un'ora per un chilometro è normale, e all'inizio ti sembrerà assurdo. Non c'è una vetta, non c'è un giro da chiudere, non c'è un punto in cui devi arrivare: se ti accorgi di stare andando *verso* qualcosa, rallenta.

**Lavora un senso alla volta.** Dieci minuti solo ad ascoltare, e conta quanti suoni distinti riesci a separare. Dieci minuti solo a guardare quello che si muove — le foglie, la luce che cambia, un insetto. Dieci minuti a toccare: cortecce diverse, muschio, una pietra, la terra. Dieci minuti agli odori, che nel bosco cambiano ogni cinquanta metri e che quasi nessuno registra mai.

**Fermati spesso e per davvero.** Siediti su un tronco per venti minuti senza fare niente. Questa è la parte in cui succede quello che deve succedere, ed è anche quella che tutti tagliano.

### Cosa succede alla testa

Vale la pena saperlo prima, perché altrimenti si scambia il processo per un fallimento.

Nella **prima mezz'ora** la testa continua a produrre liste: cose da fare, conversazioni da chiudere, la sensazione netta che potresti impiegare meglio questo tempo. È normale, e non va combattuta: quando te ne accorgi, torna a un senso.

Verso la **metà** arriva quasi sempre la noia, ed è il passaggio vero — quasi nessuno lo nomina, e invece è lì che la maggior parte delle persone tira fuori il telefono e chiude la pratica senza accorgersene. Se resisti alla noia per dieci minuti, di solito si scioglie da sola.

Nell'**ultima mezz'ora** molte persone descrivono la stessa cosa: smettere di pensare in frasi. Non è un'esperienza mistica, è quello che succede quando l'attenzione ha smesso di essere richiesta da qualcos'altro per novanta minuti di fila.

**Due ore è la durata giusta.** Sotto l'ora l'effetto c'è ma è più debole, e proprio perché la prima mezz'ora è quella inutile.

## La camminata meditativa

È un'altra cosa dal bagno di foresta, ed è più formale. La praticano molte tradizioni buddhiste, spesso alternandola alla [meditazione seduta]({MEDIT}) durante i ritiri lunghi, quando il corpo non regge altre ore ferme.

Si sceglie un percorso brevissimo — dieci o venti passi, avanti e indietro — e si cammina lentamente. L'attenzione sta su una cosa sola: la sensazione del piede che si stacca, si muove nell'aria, appoggia. Quando la mente parte, torni al piede. È tutto qui, e le prime volte è più difficile della pratica seduta perché il movimento sembra promettere che stia succedendo qualcosa.

Funziona bene proprio per chi non riesce a stare fermo: il movimento occupa il corpo quel tanto che basta a togliere l'irrequietezza, senza occupare la mente. Molte persone che avevano mollato la meditazione seduta ritrovano qui la porta.

E si fa ovunque — un corridoio, una stanza, il tratto dal parcheggio all'ufficio. Non serve un bosco: serve non avere fretta per cinque minuti.

## Il cammino di più giorni

È la versione lunga, e cambia natura rispetto a tutto il resto: non è un'ora di pratica, sono giorni in cui l'unica cosa da fare è andare avanti.

I racconti convergono tutti su una cosa, che è **il terzo giorno**. I primi due il corpo protesta e la testa fa i conti — quanto manca, come va la spalla, se è stata una buona idea. Dal terzo, quando il ritmo si stabilizza e il corpo smette di essere un problema, molte persone descrivono un cambiamento nella qualità del pensiero: meno liste, e più cose che tornano a galla da sole senza essere state cercate.

È il motivo per cui tre giorni sono il minimo perché un cammino sia un cammino e non una gita lunga.

Su quale scegliere, con chilometri, giorni e difficoltà veri, abbiamo scritto [una guida a parte]({CAMMINI_IT}).

## Cosa dice la ricerca

Qui la letteratura è più solida di quanto ci si aspetti, e va divisa in tre.

**Dove le prove sono buone.** L'esposizione alla natura riduce in modo misurabile gli indicatori fisiologici dello stress — cortisolo salivare, pressione arteriosa, frequenza cardiaca — ed è l'area più replicata, anche fuori dal Giappone.

E c'è un dato che vale la pena ricordare per intero. Uno studio pubblicato su *Scientific Reports* nel 2019 da White e colleghi, su un campione ampio nel Regno Unito, ha trovato che **circa 120 minuti a settimana** passati in ambienti naturali si associano a una probabilità significativamente maggiore di riportare buona salute e benessere. Sotto quella soglia l'associazione non compariva; sopra le cinque ore non cresceva più. Due ore a settimana, comunque distribuite: una passeggiata lunga la domenica o venti minuti al giorno funzionano allo stesso modo.

Un altro lavoro, del 2015 su *PNAS* a firma di Bratman e colleghi, ha misurato che novanta minuti di camminata in un ambiente naturale riducevano la **ruminazione** — il rimuginare a ciclo chiuso — rispetto alla stessa camminata in ambiente urbano, con una differenza visibile anche nell'attività di un'area cerebrale associata.

**Dove le prove sono più deboli** è proprio la parte più citata dal marketing: l'effetto sulle cellule natural killer del sistema immunitario, attribuito ai composti volatili emessi dagli alberi. Gli studi esistono e riportano aumenti, ma sono piccoli, senza gruppi di controllo robusti e condotti in gran parte dallo stesso gruppo di ricerca. È un filone promettente, non un fatto acquisito, e viene citato come se lo fosse.

**Quello che regge in ogni caso** è che due ore a settimana fuori restano una delle poche raccomandazioni di questo mondo che costano zero e hanno alle spalle numeri veri — più di [molte pratiche]({STRESS}) che si pagano.

## Se vivi in città

La ricerca parla di «ambienti naturali», e non significa foresta primaria.

**I parchi contano**, e sono inclusi negli studi: gli effetti sugli indicatori di stress si misurano anche lì. Anche una via alberata percorsa lentamente non è un bosco, ma non è nemmeno niente. E **venti minuti bastano** per l'effetto acuto sul cortisolo secondo diversi lavori, cioè la durata di una pausa pranzo.

La regola pratica sta in una riga: trova il parco più vicino, vacci tre volte a settimana per venti minuti, e lascia il telefono in tasca spento. Si incastra bene con le altre abitudini brevi del [kit dei quindici minuti]({KIT}).

## Come cominciare questa settimana

**Oggi**, venti minuti nel parco più vicino, telefono spento, senza cuffie, camminando più lentamente di come cammini di solito.

**Questo fine settimana**, due ore in un bosco senza meta, fermandoti venti minuti seduto da qualche parte — e aspettandoti che la prima mezz'ora sia inutile.

**Questo mese**, una camminata di una giornata intera, dalla mattina al tramonto, con un pranzo nello zaino.

**Questa stagione**, se l'idea ti resta addosso, tre giorni su un cammino. Tre, non due, per la cosa del terzo giorno.

L'unica attrezzatura indispensabile sono scarpe comode e già usate. Tutto il resto si compra dopo, se serve, e quasi sempre non serve.

## Domande frequenti

**Che differenza c'è fra un bagno di foresta e una passeggiata?**
Il ritmo e l'assenza di meta. Una passeggiata va da qualche parte; un bagno di foresta sta in un posto e lascia lavorare i sensi, molto più lentamente di quanto sembri naturale.

**Serve una guida?**
No, si fa da soli. Le sessioni guidate esistono e possono aiutare la prima volta a rallentare davvero, che è la parte difficile.

**Quanto tempo serve perché funzioni?**
Per l'effetto immediato bastano venti minuti. Per l'associazione con il benessere generale, la ricerca indica intorno a due ore a settimana, comunque distribuite.

**Funziona anche d'inverno o con la pioggia?**
Sì, e in molti casi il bosco d'inverno è più silenzioso. Serve solo vestirsi in modo da non pensare al freddo.

**È vero che gli alberi rafforzano il sistema immunitario?**
È il filone più citato e il meno solido: gli studi sono piccoli e in gran parte dello stesso gruppo. Gli effetti sullo stress, invece, sono ben documentati.

**Posso farlo con i bambini?**
Sì, cambiando l'aspettativa: con i bambini il silenzio non c'è, e l'esplorazione prende il posto della contemplazione. Vale comunque.

**Camminare sostituisce la meditazione?**
No, sono cose diverse, ma la camminata meditativa è spesso la porta d'ingresso per chi non riesce a stare seduto. Le due si sostengono, come si sostengono con il [lavoro sul respiro]({PRANA}).
"""

TITOLO_CI = "Il ciclo mestruale come mappa: le quattro fasi, cosa cambia"
DESCR_CI = (
    "Le quattro fasi, cosa regge e cosa no del racconto delle stagioni, come "
    "si tiene un diario e quando un dolore va portato da un medico."
)

CONTENUTO_CI = f"""\
Nei [cerchi di donne]({CERCHI}) e nei percorsi sul femminile il ciclo viene raccontato come una mappa: quattro fasi, quattro stagioni, quattro modi di stare al mondo che si ripetono ogni mese.

È una mappa utile, e come tutte le mappe non è il territorio. Il problema è che viene presentata come legge naturale, e chi non ci si riconosce finisce per pensare di avere qualcosa che non va.

Questa guida racconta cosa succede in ciascuna fase, cosa di quel racconto regge alla prova dei dati e cosa no, come si costruisce una mappa propria — che è l'unica che conta davvero — e a che punto un sintomo smette di essere una cosa da attraversare e diventa una cosa da far vedere.

## Le quattro fasi

Su un ciclo di ventotto giorni, che è una media e non una regola: la durata normale va dai ventuno ai trentacinque.

Nella **fase mestruale**, dal primo giorno, estrogeni e progesterone sono al minimo. Molte donne riferiscono stanchezza, bisogno di stare ferme, minore tolleranza per il rumore e per le richieste degli altri. Nel linguaggio dei cerchi è l'inverno.

Nella **fase follicolare**, dopo il flusso, gli estrogeni risalgono. È quella in cui più spesso si riporta energia in crescita, voglia di cominciare cose, mente più sgombra: la primavera.

All'**ovulazione**, verso metà ciclo, c'è il picco di estrogeni e di ormone luteinizzante e l'ovulo viene rilasciato. Molte riferiscono più socialità, più sicurezza, più desiderio, e alcune sentono un dolore breve da un lato — ha un nome proprio ed è comune. L'estate.

Nella **fase luteale**, dall'ovulazione al flusso, sale il progesterone e poi crolla se non c'è gravidanza. È la più variabile di tutte: c'è chi la descrive come raccoglimento e lucidità critica, e chi come irritabilità e gonfiore. L'autunno.

## Cosa regge e cosa no

Vale la pena separare, perché su questo tema circola molto materiale presentato come scientifico.

**Regge che gli ormoni cambiano in modo ciclico e prevedibile**, e che influenzano temperatura corporea, sonno, appetito e ritenzione di liquidi. Questa è fisiologia e non è in discussione.

**Regge che la sindrome premestruale esiste**: sintomi fisici ed emotivi nella fase luteale sono riportati dalla maggioranza delle donne, e una minoranza sperimenta una forma severa — il disturbo disforico premestruale — che è una diagnosi clinica e si tratta.

**È molto più incerto di come viene raccontato** l'effetto della fase su umore, prestazioni cognitive e capacità atletiche. Gli studi esistono e i risultati sono contraddittori, e c'è un dato che spiega quasi tutto: **la variabilità fra donne è più grande della variabilità fra fasi**. Tradotto, i tuoi mesi si somigliano fra loro molto più di quanto il tuo mese somigli a quello di un'altra — ed è la ragione per cui uno schema generale può non descriverti affatto senza che ci sia niente di strano in te.

**Non regge la sincronizzazione dei cicli** fra donne che vivono insieme. È una delle idee più diffuse in assoluto, nasce da uno studio degli anni Settanta, e le verifiche successive su campioni più ampi non l'hanno confermata: quello che sembra sincronia è in gran parte l'effetto di cicli di durata diversa che ogni tanto si incrociano.

**Non regge, o quasi**, il *cycle syncing*, cioè i protocolli che prescrivono allenamenti e alimentazione specifici per ogni fase. L'idea di fondo è sensata, le prove che serva seguirla alla lettera sono scarse. Come principio generale — allenarsi quando si ha energia, riposare quando serve — è ragionevole e non ha bisogno di un protocollo a pagamento.

## Costruisci la tua mappa

Questa è la parte utile, e richiede tre mesi e due minuti al giorno. È anche l'unico modo per sapere se le quattro stagioni descrivono te o descrivono qualcun'altra.

**Segna il primo giorno del flusso**, che è il giorno uno del ciclo. Da lì contano i giorni in sequenza, non le date del calendario.

**Ogni sera annota tre numeri da uno a cinque: energia, umore, sonno.** Tre numeri, non un racconto — se scrivi paragrafi, dopo due settimane smetti. Aggiungi una parola sul corpo solo se c'è qualcosa da dire.

**Non guardare i dati per tre mesi.** È la regola che conta di più ed è la più difficile da rispettare. Guardarli subito porta a cercare conferme, e un materiale come questo si presta benissimo a darne: se hai in testa che il giorno ventitré dovresti essere giù, il giorno ventitré ti sembrerà di essere giù.

**Al terzo mese, allinea i tre cicli** mettendo il giorno uno sotto il giorno uno, e guarda dove i numeri si somigliano. Quelli sono i tuoi schemi.

E aspettati di scoprire qualcosa che non ti aspettavi. Molte donne trovano che la loro fase difficile non è quella che credevano, o che dura tre giorni invece di due settimane. È un'informazione che cambia il modo di organizzare un mese, e non l'avresti avuta da nessuno schema.

Bastano un quaderno o una nota sul telefono. Le app dedicate funzionano, con un'avvertenza: stai affidando dati sanitari a un'azienda, e vale la pena leggere cosa ne fa.

## Cosa farne

Senza protocolli, tre applicazioni che le donne che tengono un diario finiscono per fare da sole.

**Metti le cose difficili dove hai energia.** Se i tuoi giorni sono l'otto e il quattordici, è lì che vanno la conversazione difficile, la presentazione, la decisione che rimandi.

**Proteggi i due o tre giorni che sai essere pesanti**, senza azzerare la vita: togliere un impegno rinviabile basta quasi sempre, e funziona meglio di un piano elaborato.

**Muoviti comunque.** L'idea che durante il flusso si debba stare ferme è una generalizzazione: molte donne stanno meglio muovendosi, e il movimento leggero è fra le poche cose con un effetto documentato sul dolore mestruale. Una pratica di [yoga]({YOGA}) dolce o una camminata valgono più del divano, se il corpo te lo permette.

E dormi di più nella fase luteale, se puoi: è la richiesta più frequente che il corpo fa in quei giorni e la più semplice da concedere.

## Quando non è una fase da attraversare

Questa sezione è la ragione principale per cui vale la pena scrivere questo articolo.

Nel mondo del benessere il dolore mestruale viene spesso raccontato come qualcosa da accogliere, ascoltare, attraversare. Per un fastidio gestibile va benissimo. Ma esiste una soglia, e va detta senza ambiguità.

**Un dolore che ti impedisce di lavorare, studiare o alzarti dal letto non è normale.** Non è una questione di soglia personale né di rapporto con la propria femminilità: è un sintomo, e va portato da un medico.

Vale la pena insistere perché il ritardo diagnostico su condizioni come l'**endometriosi** si misura in anni, e una parte di quel ritardo passa proprio dal fatto che a molte donne viene detto — in famiglia, a scuola, fra amiche, a volte perfino in ambito sanitario — che il dolore fa parte del pacchetto.

Le cose che meritano una visita e non una pratica sono queste: un dolore che non passa con i comuni antidolorifici o che ti costringe a letto; un flusso molto abbondante o che dura più di sette giorni; cicli più corti di ventuno giorni o più lunghi di trentacinque, se non è la tua normalità; sanguinamento fra un ciclo e l'altro; dolore durante i rapporti o nell'evacuazione; assenza del ciclo per più di tre mesi senza gravidanza; e qualsiasi cambiamento netto rispetto a com'è sempre stato per te.

Nessuna pratica olistica sostituisce quella visita, e chi lo lascia intendere ha oltrepassato [un confine noto]({SERIO}). Un cerchio, una pratica di respiro o un percorso corporeo possono accompagnare benissimo una cura: al posto, mai.

## Domande frequenti

**Le quattro fasi valgono per tutte?**
Come schema fisiologico sì. Come descrizione di come ti senti, no: la variabilità individuale è grande, ed è il motivo per cui il diario vale più di qualsiasi schema.

**È vero che i cicli si sincronizzano fra donne che convivono?**
Le verifiche su campioni ampi non lo confermano. È un'idea molto diffusa nata da uno studio degli anni Settanta.

**Posso allenarmi durante il flusso?**
Sì, e per molte donne il movimento riduce il dolore. Il criterio è come ti senti, non la fase.

**La sindrome premestruale è reale?**
Sì, e nella sua forma severa è una diagnosi clinica con trattamenti. Se ogni mese perdi giorni di vita, non è qualcosa da attraversare in silenzio.

**Il ciclo influenza la lucidità mentale?**
Gli studi sono contraddittori e gli effetti misurati sono piccoli. Quello che noti tu sui tuoi mesi vale più della media di uno studio.

**Le app per il ciclo sono affidabili?**
Come diario sì. Le previsioni sull'ovulazione sono stime, e i tuoi dati sono dati sanitari: vale la pena sapere a chi li stai dando.

**Serve un cerchio o un percorso per lavorare sul ciclo?**
No, il diario si tiene da sole. Un [cerchio]({CERCHI}) aggiunge il confronto con altre, che è una cosa diversa e per molte è il valore vero.
"""

TITOLO_DO = "Le domande da fare prima di prenotare un ritiro"
DESCR_DO = (
    "Ventidue domande su soldi, gruppo, giornata e salute, come si leggono "
    "le risposte e i tre casi in cui conviene lasciar perdere."
)

CONTENUTO_DO = f"""\
Un ritiro di quattro giorni costa fra i quattrocento e i millecinquecento euro, chiede ferie, e mette il tuo corpo nelle mani di qualcuno per un tempo lungo. È una delle spese meno reversibili che si fanno per il proprio benessere.

Eppure la maggior parte delle persone prenota dopo aver letto una pagina e guardato dieci foto, senza scrivere una riga. Il motivo è quasi sempre lo stesso, ed è comprensibile: chiedere sembra diffidenza, e la diffidenza sembra fuori posto in un contesto che parla di apertura e di fiducia.

È il contrario. Chi organizza ritiri da anni si aspetta le domande — la maggior parte ha già le risposte pronte in un documento — e chi si irrigidisce di fronte a una domanda semplice ti sta dando l'informazione più utile di tutta la conversazione.

Queste sono le domande che contano, raggruppate per quello che proteggono. Non serve farle tutte: servono quelle che pesano sul tuo caso.

## Sui soldi

Il gruppo più importante, perché è quello dove finiscono i disaccordi.

**Quanto costa in tutto, comprese le tasse?** La cifra che ti interessa è quella finale: chiedi se il prezzo esposto include IVA, tassa di soggiorno, eventuali quote associative.

**Cosa è incluso e cosa no?** Le voci che più spesso restano fuori sono i transfer dall'aeroporto o dalla stazione, i pasti del primo e dell'ultimo giorno, i trattamenti individuali, le bevande, la biancheria. Un programma serio ha un elenco scritto.

**Quanto è la caparra e quando si paga il saldo?** La forma diffusa è un acconto fra il venti e il trenta per cento alla prenotazione e il saldo qualche settimana prima. Diffida di chi chiede l'intero importo mesi prima senza spiegare perché.

**Cosa succede se disdico?** È la domanda che salva più soldi di tutte, e la risposta deve essere una politica scritta con date e percentuali — entro trenta giorni rimborso pieno meno la caparra, entro quindici il cinquanta per cento, e così via. «Vediamo caso per caso» non è una politica, è una speranza.

**E se annullate voi?** Succede, per numeri insufficienti o per un imprevisto di chi conduce. Chiedi se in quel caso il rimborso è integrale e in quanti giorni arriva, ed entro quando decidete — perché quella data è il momento fino al quale puoi ancora annullare un volo senza perderlo tutto.

**Come si paga?** Bonifico e carta vanno bene. Un pagamento che deve passare solo per canali senza tracciabilità, con la richiesta di non specificare la causale, è un segnale da prendere sul serio.

E se il prezzo ti sembra alto o basso senza capire perché, aiuta sapere [come si calcola il prezzo di un ritiro]({PREZZO}): vitto e alloggio pesano più di quanto sembri, e un prezzo molto sotto la media di solito significa che qualcosa è stato tagliato.

## Su chi conduce

**Chi conduce, esattamente?** Nome e cognome, non «il nostro team». Se le sessioni sono tenute da persone diverse, chiedi chi fa cosa.

**Che formazione ha, e con chi?** Non serve un diploma, serve una risposta specifica: «formazione di cinquecento ore con questa scuola, nel 2019» è una risposta, «studio da tutta la vita» non lo è.

**Da quanti anni conduce ritiri, e quante edizioni ha fatto questo?** Un primo ritiro può essere ottimo, ma è utile saperlo, perché la prima edizione ha sempre qualcosa che non funziona.

**C'è qualcuno che parla la mia lingua?** Sembra ovvio finché non ti trovi in una sessione di lavoro emotivo con una traduzione approssimativa.

Su come si legge una formazione e su cosa vale un attestato, il quadro completo sta in [come capire se un operatore è serio]({SERIO}).

## Sul gruppo

**Quante persone siete?** È la domanda che cambia di più l'esperienza. Sotto le dodici persone c'è spazio per parlare; sopra le venticinque, in una pratica intensa, un solo facilitatore non riesce a vedere tutti.

**Quanti facilitatori per quante persone?** Vale soprattutto per le pratiche che possono smuovere: [respiro intenso]({BREATH}), lavoro sul trauma, cerchi.

**Che tipo di persone partecipa di solito?** Chiedi l'età media e se vengono più da sole o in coppia. Non è curiosità: se hai quarantacinque anni e il gruppo ne ha in media venticinque, la settimana sarà diversa da come te la immagini.

**Dormo in camera singola o condivisa, e con chi?** La condivisa abbassa il prezzo e alza l'intensità. Se la singola esiste, chiedi quanto costa in più prima di prenotare.

## Sulla giornata

**Com'è una giornata tipo, ora per ora?** Un programma vero ha degli orari: «pratiche, natura, condivisione» descrive un'atmosfera, non una giornata.

**A che ora si comincia?** Alcuni ritiri partono alle sei del mattino. È una scelta legittima e conviene saperla prima di prenotare, non alla prima sveglia.

**Quanto del programma è obbligatorio?** La risposta giusta è che nulla lo è: chiedi esplicitamente se puoi saltare una sessione e restare in camera senza che sia un problema.

**Quanto tempo libero c'è?** Un ritiro pieno dalle sei alle ventidue non è riposo, è un altro tipo di intensità. Entrambi vanno bene, purché tu sappia quale hai comprato.

**Ci sono momenti di silenzio, e per quanto?** Per qualcuno sono la parte migliore, per altri sono la ragione per scegliere un altro ritiro.

**C'è campo, e posso usare il telefono?** Molti ritiri chiedono di consegnarlo: se hai figli piccoli o un genitore anziano, chiedi come si fa a essere raggiungibili in caso di urgenza.

## Sul corpo e sulla salute

**Mi chiedete qualcosa sulla mia salute prima?** Questa rovescia il tavolo, ed è la più informativa di tutto l'elenco. Un ritiro che prevede pratiche intense e non fa nessuna anamnesi — questionario, colloquio, anche solo una mail di domande — sta saltando un passaggio che riguarda la tua sicurezza.

**Ci sono controindicazioni per quello che farete?** Chi conosce la propria pratica sa elencarle senza esitare.

**Come funziona il cibo, e gestite intolleranze e allergie?** Chiedi il tipo di alimentazione, quanti pasti, e se una celiachia o un'allergia seria sono gestibili in quella cucina.

**Cosa succede se sto male, fisicamente o emotivamente?** La risposta migliore è concreta: dov'è l'ospedale più vicino, chi resta con te, cosa è successo le altre volte.

**Assumo farmaci o sono in terapia: cambia qualcosa?** Devi poterlo dire senza sentirti giudicato. E nessuno, in nessun contesto, può suggerirti di sospendere una terapia: se succede, quello è il momento di andarsene.

## Sul luogo

**Dove si svolge, con l'indirizzo?** Un luogo che resta vago fino al pagamento è un'anomalia: cerca la struttura, guarda le recensioni di chi ci ha soggiornato per altri motivi.

**Come ci si arriva, e c'è un transfer?** Un ritiro in mezzo alla natura può significare quaranta minuti di auto dalla stazione più vicina.

**Le camere e i bagni come sono?** Bagno in camera o condiviso, riscaldamento, wifi: nessuna di queste cose è superflua a febbraio.

## Le domande da fare a te stesso

Sono quattro e vengono prima di tutte le altre, perché un ritiro può essere organizzato benissimo e restare quello sbagliato per te in questo momento.

**Cosa sto cercando?** Riposo, movimento, o una risposta a qualcosa: sono tre ritiri diversi, e il primo si riconosce dal programma leggero mentre il secondo si riconosce dagli orari.

**Sto attraversando un momento difficile?** Un lutto recente, una separazione, un periodo di terapia in corso non escludono un ritiro, ma cambiano quale — le pratiche intense in un momento fragile chiedono un contesto che sappia reggerle, e vale la pena dirlo a chi organizza prima di partire.

**Voglio stare in gruppo o voglio stare da solo?** Un ritiro è quasi sempre una convivenza stretta con dieci sconosciuti. Se quello che cerchi è silenzio e nessuno intorno, esistono formule diverse.

**Sono disposto a stare scomodo?** Sveglie presto, cibo diverso, un letto in condivisione, ore senza telefono. La scomodità è spesso il punto, ed è utile sapere quanta ne accetti prima di pagare.

## Come si leggono le risposte

Il contenuto conta, ma tre cose contano di più.

**La velocità.** Una risposta entro due giorni lavorativi è normale, e chi impiega una settimana a rispondere prima che tu abbia pagato non diventerà più presente dopo.

**La precisione.** Le risposte utili contengono numeri, nomi e date; quelle evasive contengono aggettivi.

**La reazione alla domanda.** Un organizzatore esperto risponde volentieri, perché sa che chi chiede è anche chi poi partecipa con attenzione. Chi si offende, chi ti fa sentire poco spirituale per aver chiesto di soldi, chi risponde che «devi fidarti del processo», ti ha appena mostrato come gestirà un tuo dubbio quando sarai lì.

## Tre risposte che valgono un no

**Promesse di guarigione.** Un ritiro che dichiara di curare una patologia, o che suggerisce di ridurre farmaci, sta oltrepassando un confine che è anche legale.

**Nessuna politica di cancellazione scritta.** Non è una formalità: è il segnale che quell'organizzazione non ha ancora affrontato la prima disdetta, oppure che preferisce non impegnarsi.

**Pressione a decidere subito.** «Restano due posti» ripetuto per tre settimane è una tecnica di vendita, e un ritiro che vale la pena resta valido anche fra due giorni.

## Come chiedere senza sentirti a disagio

Una mail sola, cinque o sei domande, in tono normale. Non serve giustificarsi né spiegare perché chiedi.

Una traccia che funziona:

> Buongiorno, sto valutando il ritiro di [date] e vorrei qualche informazione prima di prenotare: quante persone siete di solito, cosa comprende esattamente la quota, come funziona in caso di disdetta da parte mia, e se è previsto un questionario sulla salute prima dell'arrivo. Grazie.

E quando le risposte arrivano al telefono, riassumile in una mail e mandale a chi le ha date: «riepilogo quello che ci siamo detti, fammi sapere se ho capito bene». Nessuno si offende, e da quel momento gli accordi esistono in una forma che entrambi potete rileggere — cosa che conta soprattutto sulle tre cose che generano i disaccordi veri, cioè cosa comprende la quota, cosa succede in caso di disdetta, e cosa ti è stato detto sulla tua situazione di salute.

Chi organizza ritiri riceve messaggi così ogni settimana. Se sei il primo a mandarne uno, quella è già un'informazione.

## Domande frequenti

**Non è scortese fare tutte queste domande?**
No, ed è il timore che ferma quasi tutti. Un organizzatore che lavora bene le riceve di continuo e spesso ha già un documento pronto.

**Quante ne faccio senza esagerare?**
Cinque o sei in una mail sola. Scegli quelle che pesano sul tuo caso: se hai un'allergia seria, la domanda sul cibo viene prima di quella sul silenzio.

**Se non rispondono a tutto, è un problema?**
Dipende da cosa saltano. Una risposta parziale sul programma capita; il silenzio sulle regole di disdetta o sulla salute è un'altra cosa.

**Posso chiedere di parlare al telefono?**
Sì, e dieci minuti di conversazione dicono più di dieci mail. La disponibilità stessa è una risposta.

**Come faccio a sapere se il prezzo è giusto?**
Confronta cosa include, non la cifra. Un ritiro che comprende alloggio in singola, tutti i pasti e i transfer non è paragonabile a uno che comprende solo le sessioni.

**E se ho già prenotato e le risposte non mi convincono?**
Rileggi le condizioni: se sei nella finestra di rimborso, la caparra persa costa meno di una settimana passata male. Se non lo sei, scrivi comunque le tue preoccupazioni prima di partire, così che chi conduce le sappia.
"""

PEZZI = [
    (CAMMINARE, TITOLO_CA, DESCR_CA, CONTENUTO_CA),
    (CICLO, TITOLO_CI, DESCR_CI, CONTENUTO_CI),
    (DOMANDE_S, TITOLO_DO, DESCR_DO, CONTENUTO_DO),
]


def analizza(testo):
    blocchi = [b.strip() for b in testo.split("\n\n") if b.strip()]
    prosa = frammenti = parole_prosa = 0
    for b in blocchi:
        if b.startswith("#"):
            continue
        if b.startswith(("-", ">", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")):
            continue
        if b.startswith("**") and b.count(".") <= 2 and len(b.split()) < 28:
            frammenti += 1
            continue
        prosa += 1
        parole_prosa += len(b.split())
    return (round(100 * parole_prosa / max(len(testo.split()), 1)),
            prosa, frammenti)


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto in PEZZI:
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not doc:
            print(f"ASSENTE: {slug}")
            continue
        q1, _, f1 = analizza(doc["content"])
        q2, _, f2 = analizza(contenuto)
        print(f"{titolo[:52]:54} prosa {q1}% → {q2}%   frammenti {f1} → {f2}   "
              f"parole {len(doc['content'].split())} → {len(contenuto.split())}")
        if doc["content"] == contenuto:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya",
            "updated_at": datetime.now(timezone.utc)}})

    print("\n── quello che resta sotto l'85%")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    righe = sorted(((analizza(a["content"]), a["slug"]) for a in arts))
    for (q, _, f), s in righe:
        if q < 85:
            print(f"  {s[:48]:50} {q:3}%  frammenti {f}")
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\n  link rotti: {rotti or 'nessuno'}")
    print(f"  sopra l'85%: "
          f"{sum(1 for (q, _, _), _ in righe if q >= 85)} su {len(arts)}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
