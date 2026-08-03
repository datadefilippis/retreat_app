"""RF2 — voce narrativa, seconda ondata: i quattro con piu' frammenti.

Cerchi di donne (74% di parole in prosa, 17 frammenti), shiatsu (67%,
15), cammini italiani (70%, 17), promuovere un ritiro (63%, 17). Sono
i quattro in cui il difetto era piu' fitto: una sequenza di titoletti
in grassetto seguiti da una frase, che si legge come una scheda
tecnica e non porta da nessuna parte.

COSA CAMBIA IN OGNUNO, oltre alla prosa.

CERCHI. Apertura sulla scena vera — entrare in una stanza con dieci
donne che non conosci — e il giro di condivisione raccontato come si
svolge davvero: l'oggetto che passa, il silenzio dopo che una ha
finito, cosa fa chi conduce quando qualcuna si rompe.

SHIATSU. I tre punti da premere erano un elenco; ora sono una pratica
guidata, con la pressione che si costruisce in tre respiri, cosa si
sente e dove ci si ferma.

CAMMINI. La sezione sulle vesciche diventa il racconto di come si
prende un punto caldo prima che diventi una vescica, che e' l'unica
cosa che decide se arrivi in fondo.

PROMUOVERE. Il calendario di lancio resta un calendario, perche' li'
la scansione E' l'informazione, ma smette di essere l'unica forma
dell'articolo: intorno torna la prosa che spiega perche' quelle
settimane sono quelle.

    venv/bin/python scripts/rf2_voce_narrativa_ondata2.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

CERCHI = "cerchi-di-donne-cosa-sono-come-funzionano"
SHIATSU = "shiatsu-cose-come-funziona-una-seduta"
CAMMINI = "cammini-italiani-quale-scegliere-la-prima-volta"
PROMO = "come-promuovere-un-ritiro-e-riempire-i-posti"

SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
TAROCCHI = "/blog/tarocchi-oracoli-strumento-evolutivo"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
CICLO = "/blog/ciclo-mestruale-quattro-fasi-come-ascoltarlo"
MASSAGGIO = "/blog/massaggio-olistico-tipi-cosa-aspettarsi"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"
CAMMINARE = "/blog/camminare-bagni-di-foresta-cammini"
PREZZO = "/blog/prezzo-giusto-ritiro-come-calcolarlo"
IVA = "/blog/partita-iva-operatore-olistico-fiscalita-guida"

# ─────────────────────────────────────────────────────────── cerchi
TITOLO_CE = "Cerchi di donne: cosa succede davvero dentro"
DESCR_CE = (
    "Come si svolge un incontro, il patto iniziale, come funziona la "
    "riservatezza, chi facilita e come si riconosce un cerchio fatto bene."
)

CONTENUTO_CE = f"""\
La prima volta si arriva in anticipo e si resta in macchina qualche minuto in più del necessario. Dentro c'è una stanza con dieci donne che non conosci, dei cuscini per terra, e nessuna idea precisa di cosa succederà.

È il momento in cui quasi tutte pensano la stessa cosa: che dovranno raccontare qualcosa di intimo a delle sconosciute.

Non è così, e capire perché non è così è il modo migliore per decidere se un cerchio fa per te. Questa guida racconta cosa succede dentro quella stanza — il patto che si dice ad alta voce all'inizio, come funziona davvero il giro di parola, cosa fa chi conduce quando qualcuna si commuove — e come si riconosce un cerchio condotto bene da uno improvvisato.

## Cos'è, e cosa lo rende diverso da una serata fra amiche

Un cerchio è un incontro guidato da una facilitatrice in cui un gruppo di donne si riunisce per condividere, ascoltare e praticare insieme. La forma circolare non è un dettaglio estetico: nel cerchio non c'è una cattedra, nessuna sta davanti e nessuna dietro, e ogni voce ha lo stesso spazio.

È una forma che attraversa quasi tutte le culture, dalle tende rosse delle tradizioni mediorientali ai cerchi delle donne native americane fino ai gruppi di parola del femminismo del Novecento. La versione che si incontra oggi in Italia intreccia questi fili con pratiche di consapevolezza recenti, e vale la pena saperlo: non è una tradizione unica tramandata intatta, è un incontro fra tradizioni diverse e un bisogno molto contemporaneo.

Quel bisogno è riconoscibile, e spiega anche la differenza con una serata fra amiche. In un cerchio le altre non ti conoscono, non hanno una storia con te, e soprattutto non dovranno gestire le conseguenze di quello che dici. È questa distanza a rendere possibile una vicinanza che con chi ti conosce da vent'anni sarebbe più complicata.

## Come si svolge un incontro

Ogni facilitatrice ha il suo stile, ma la struttura ricorre e conviene conoscerla prima di entrare.

Si comincia dall'apertura, che serve a segnare che quello che viene dopo è un tempo diverso: una candela accesa al centro, un oggetto, qualche minuto di silenzio o una breve [meditazione]({MEDIT}). Sembra una formalità e non lo è: è il momento in cui si smette di essere dieci persone arrivate di corsa e si comincia a essere un gruppo.

Subito dopo, in un cerchio condotto bene, arriva **il patto**. Le regole vengono dette ad alta voce, ogni volta, anche se ci sono le stesse dell'incontro precedente: quello che viene detto qui resta qui, non si interrompe, non si danno consigli, si può passare. È il passaggio più importante di tutta la serata, ed è anche il primo segnale su chi conduce — se questo momento manca, mancano le fondamenta di tutto il resto.

Poi la facilitatrice propone un tema. La ciclicità, il lasciare andare, i confini, la rinascita: un filo intorno a cui si muoverà l'incontro, abbastanza largo perché ognuna ci trovi la propria cosa.

E arriva il cuore, che è il giro di condivisione. Spesso passa di mano un oggetto — una pietra, un ramo, qualsiasi cosa — e la regola è semplice: chi lo tiene parla, le altre tacciono. Non si commenta, non si annuisce con troppa enfasi, non si dice «anche a me». Quando una finisce, non parte una risposta: c'è un silenzio breve, l'oggetto passa, e comincia la successiva.

Quel silenzio è la parte che spiazza di più chi arriva dal mondo normale, dove il silenzio dopo una confidenza è imbarazzo. Qui è il contrario: è lo spazio in cui quello che è stato detto resta appoggiato senza che nessuna se ne impossessi.

Chi non vuole parlare passa, e passare non richiede spiegazioni.

Dopo il giro c'è la pratica, che cambia molto da un cerchio all'altro: scrittura, movimento, meditazione, rituali stagionali, lavoro con la luna o con il ciclo. Niente è obbligatorio.

E infine la chiusura, spesso con un gesto condiviso, che chiude lo spazio come l'apertura lo aveva aperto. Un incontro dura in genere fra le due e le tre ore.

## La riservatezza, in concreto

È la regola che rende possibile tutto il resto, e nella pratica significa quattro cose che vale la pena avere chiare.

Quello che viene detto nel cerchio **non esce dal cerchio**: non si racconta fuori, nemmeno in forma anonima, nemmeno alla propria migliore amica come esempio di una cosa interessante sentita ieri sera.

**Non si nomina chi c'era.** Se incontri per strada una donna conosciuta in un cerchio, la saluti come chiunque, e davanti ad altri il cerchio non esiste.

**Non si fotografa** durante la condivisione. Un cerchio che raccoglie contenuti per i social mentre qualcuna sta parlando ha un problema di priorità che riguarda anche te.

E **non si torna sull'argomento dopo**, a meno che non sia lei ad aprirlo. Chiedere «come è andata poi con tuo padre?» la settimana dopo, fuori dal cerchio, è un'invasione anche quando nasce da affetto sincero.

## Cosa non è

Vale la pena sgombrare il campo da tre malintesi.

Non è una terapia di gruppo: la facilitatrice non è necessariamente una terapeuta, e il cerchio non cura, accompagna. Se stai attraversando una sofferenza importante può affiancare un percorso professionale, mai sostituirlo.

Non è un club esoterico. Esistono cerchi dal linguaggio molto spirituale e cerchi del tutto laici, e la condivisione resta il centro in entrambi: il resto è vocabolario, e se un vocabolario non ti risuona ne esistono altri.

E non è contro nessuno. Lo spazio fra sole donne serve a costruire un tipo particolare di intimità, non a escludere, ed esistono anche cerchi di uomini e cerchi misti con dinamiche loro.

## Chi facilita, e perché la domanda conta

Qui va detta una cosa che nel settore si preferisce non dire: **facilitare un cerchio non è una professione regolata**. Non esiste un titolo, non esiste un albo, e chiunque può aprire un cerchio la settimana prossima.

Esistono formazioni serie, di durata molto variabile, che lavorano su conduzione di gruppo, ascolto attivo e gestione delle emozioni intense. E ne esistono di brevissime.

La differenza fra le une e le altre si vede in un momento preciso, ed è quello in cui una condivisione tocca qualcosa di grosso e chi parla si rompe. Chi ha esperienza in quel momento non fa niente di appariscente: resta, non si precipita a consolare, non chiede dettagli, tiene il tempo del gruppo, e alla fine sa riconoscere se quella persona ha bisogno di qualcosa che il cerchio non può darle. Chi non ha esperienza, di solito, interviene troppo.

Le domande da fare prima di iscriversi sono quattro: da quanto facilita, quante persone accoglie, che formazione ha fatto e con chi, e cosa fa se qualcuna sta male. Valgono [gli stessi criteri]({SERIO}) di chiunque ti accompagni.

## Cosa aspettarsi la prima volta

Sentirsi osservatrici è normale, e nessuna facilitatrice seria forza a condividere: passare è previsto e non è una sconfitta.

Molte raccontano la stessa parabola nei primi mesi — primo cerchio in silenzio, secondo cerchio due parole, terzo cerchio qualcosa che non sapevano di trattenere. Commuoversi è frequente, e non è un incidente: succede perché per una volta nessuno interrompe, nessuno consola e nessuno propone soluzioni, e in quello spazio le cose salgono da sole.

Si esce stanche, ed è la cosa che sorprende di più. Due ore di ascolto pieno costano più di quanto sembri: conviene non incastrare un impegno subito dopo.

Serve portare vestiti comodi, una bottiglia d'acqua e un cuscino se richiesto. Nient'altro.

## Quanto costa

In Italia un cerchio costa in genere fra i 10 e i 30 euro a incontro, spesso con formule a offerta libera o a contributo consapevole. Quelli dentro un ritiro sono compresi nell'esperienza.

Un percorso a cicli — quattro o otto incontri con lo stesso gruppo chiuso — costa di più e funziona in modo diverso: il gruppo si conosce, e la profondità cresce di incontro in incontro invece di ripartire ogni volta da capo.

## I sei segnali di un cerchio da evitare

Sono netti, e riconoscerne anche uno solo basta per non tornare.

Il patto iniziale non viene detto: se le regole non vengono nominate, non ci sono. La facilitatrice parla per metà del tempo, e il cerchio diventa la sua lezione. Si danno consigli, e «io al posto tuo farei» è esattamente la cosa che il cerchio esiste per non fare. Si insiste perché tu parli, anche con delicatezza, anche solo «una parola»: il passo deve essere davvero libero. Si vende qualcosa alla fine — un percorso, una consulenza, un prodotto — proprio nel momento in cui le persone sono più aperte. E si promettono guarigioni, che è il confine oltre il quale un cerchio sta facendo un mestiere che non è il suo.

## Come trovarne uno

I canali restano sparsi: passaparola, gruppi social locali, studi di yoga che ospitano cerchi mensili. Conviene chiedere direttamente nello studio dove pratichi, perché moltissimi cerchi non vengono annunciati da nessun'altra parte e vivono di voce.

Se quello che stai valutando è un ritiro del femminile e non un incontro singolo, le domande da fare diventano di più e riguardano anche soldi, gruppo e giornate: le abbiamo raccolte [qui]({DOMANDE}).

## Domande frequenti

**Devo parlare per forza?**
No. Il passo è sempre concesso e l'ascolto è partecipazione piena.

**Serve credere in qualcosa?**
No. Esistono cerchi con linguaggio spirituale e cerchi del tutto laici: se il linguaggio di uno non ti risuona, cercane un altro.

**Posso andare se non conosco nessuna?**
È la norma, ed è parte del punto: la forza del cerchio sta proprio nel fatto che le altre non hanno una storia con te.

**E se mi metto a piangere?**
Capita spesso e non è un problema. In un cerchio condotto bene nessuno si precipita a consolarti: ti lasciano il tempo, che è quello che serve.

**Che differenza c'è con la tenda rossa?**
La tenda rossa è una forma specifica legata alla ciclicità femminile, tradizionalmente uno spazio di riposo nei giorni del ciclo. Ogni tenda rossa è un cerchio, non ogni cerchio è una tenda rossa. Sul ciclo come mappa abbiamo scritto [a parte]({CICLO}).

**Sono adatti in gravidanza o nel post parto?**
Sì, ed esistono cerchi dedicati a quelle fasi. Dirlo prima alla facilitatrice cambia cosa propone.

**Cosa succede se incontro per strada una donna del cerchio?**
La saluti come chiunque. Il patto dice di non nominare il cerchio davanti ad altri e di non tornare su quello che ha condiviso, a meno che non sia lei ad aprirlo.

**Ci sono cerchi con le carte?**
Alcuni le usano come traccia per la scrittura o la condivisione: sui [tarocchi come strumento riflessivo]({TAROCCHI}) abbiamo scritto a parte.
"""

# ────────────────────────────────────────────────────────── shiatsu
TITOLO_SH = "Shiatsu: come funziona una seduta, e perché si resta vestiti"
DESCR_SH = (
    "Cosa succede su quel futon, le due scuole, cosa si prova, cosa dice la "
    "ricerca, le controindicazioni e tre punti da premere da soli."
)

CONTENUTO_SH = f"""\
Sei disteso a terra su un futon, completamente vestito, con dei calzini di cotone. Qualcuno ti solleva un braccio, lo appoggia in una posizione che non avresti scelto, e comincia a premere lungo il bordo esterno con il gomito.

Non è quello che ti aspettavi da un trattamento corporeo, e in effetti lo shiatsu non somiglia a niente di quello che conosciamo come massaggio: niente olio, niente lettino, niente scorrimento delle mani sulla pelle.

Ed è proprio per questo che per molte persone è la porta d'ingresso più semplice al lavoro sul corpo — perché non richiede di spogliarsi. Questa guida racconta cosa succede in quella seduta, da dove viene questa pratica, cosa dice la ricerca e come si sceglie chi la conduce.

## Cos'è

*Shiatsu* significa letteralmente «pressione con le dita», e la descrizione è precisa. Chi conduce applica una pressione perpendicolare e sostenuta con pollici, palmi, gomiti e a volte ginocchia, lungo percorsi che nella tradizione orientale corrispondono ai meridiani, alternandola a stiramenti e a mobilizzazioni delle articolazioni.

Due cose lo separano dal massaggio a cui siamo abituati, e sono entrambe evidenti nei primi minuti.

La prima è che **non c'è scorrimento**: la mano non scivola, si appoggia, affonda lentamente, resta, e poi si sposta altrove. La sensazione somiglia più a un peso che a una carezza, e chi si aspettava di essere accarezzato all'inizio resta interdetto.

La seconda è che **chi riceve non è passivo**. Il respiro guida il ritmo della pressione, e in molte scuole viene chiesto esplicitamente di espirare mentre la pressione affonda. Non stai subendo un trattamento: stai facendo qualcosa insieme a qualcuno.

## Da dove viene

È più recente di quanto il futon e i calzini lascino intuire, e c'è un dettaglio che vale la pena conoscere prima di scegliere chi lo pratica.

Lo shiatsu nasce in Giappone nella prima metà del Novecento, dall'incontro fra le tecniche manuali tradizionali giapponesi, l'agopuntura e le nozioni di anatomia occidentale che in quegli anni arrivavano nel paese. Le due figure di riferimento sono Tokujiro Namikoshi, che ne codifica una versione fondata su punti e pressione, e Shizuto Masunaga, che negli anni Settanta sviluppa lo *zen shiatsu*, con una teoria dei meridiani estesa e una diagnosi che parte dall'addome.

Il dettaglio è questo: **in Giappone lo shiatsu è riconosciuto dallo Stato**, con un percorso formativo regolamentato e una licenza rilasciata dal ministero della salute a partire dagli anni Cinquanta.

In Italia no. Chi lo pratica qui non ha un titolo sanitario e rientra fra le professioni non organizzate della legge 4/2013. È la stessa asimmetria che riguarda l'ayurveda, e genera lo stesso equivoco: la serietà di una tradizione regolamentata altrove non si trasferisce automaticamente a chiunque ne usi il nome qui.

## Le due scuole, e perché la domanda serve

Due sedute di shiatsu possono somigliarsi poco, e quasi sempre il motivo è la scuola.

Chi si è formato nell'impostazione **Namikoshi** lavora su punti anatomicamente definiti, con una sequenza abbastanza standard e una lettura vicina alla fisiologia occidentale. È più sistematico e più prevedibile: due sedute si somigliano.

Chi viene da **Masunaga**, lo zen shiatsu, lavora sui meridiani estesi, parte spesso dalla palpazione dell'addome e costruisce la seduta su quello che sente in quel momento. È più interpretativo e meno standardizzato: due sedute possono essere molto diverse.

Molti operatori italiani mescolano le due impostazioni, e nessuna delle due è migliore. Ma chiedere «in che scuola ti sei formato» prima di prenotare ti dice in anticipo che tipo di ora ti aspetta.

## Come si svolge

Una seduta dura fra i cinquanta e i settantacinque minuti e in Italia costa fra i 50 e gli 80 euro.

Si comincia da un colloquio: qualche minuto su come stai, sui dolori se ce ne sono, su condizioni di salute e terapie in corso. In alcune scuole si aggiunge la palpazione dell'addome, e se non te l'aspetti va spiegata prima — è una cosa che si fa vestiti, ma resta un contatto ravvicinato e va nominato.

Poi ci si distende sul futon. Si sta vestiti, con abiti comodi e preferibilmente di cotone, e si cambia posizione più volte nel corso della seduta: supini, proni, su un fianco, a volte seduti.

Durante il lavoro chi conduce si sposta intorno a te e usa il proprio peso più che la forza delle braccia — è il motivo per cui una pressione profonda può arrivare da una persona minuta. La soglia giusta è una sola: **la pressione può essere intensa, e devi poter continuare a respirare normalmente**. Se stai trattenendo il fiato, è troppa, e dirlo fa parte della seduta.

Si chiude restando fermi qualche minuto, e ci si rialza con calma.

## Cosa si prova

I racconti convergono su tre cose.

La prima è una **pesantezza piacevole**, diversa dal rilassamento morbido di un massaggio con l'olio: più radicata, meno vellutata, come se il corpo si fosse appoggiato più in basso.

La seconda sono i **punti che parlano**: capita che una pressione in una zona produca una sensazione in un'altra, a volte lontana. È un fenomeno di riferimento noto e non ha bisogno della teoria dei meridiani per essere reale.

La terza è la **stanchezza dopo**, soprattutto le prime volte, seguita da una notte in cui molti dormono meglio del solito. Conviene non programmare niente di impegnativo nelle ore successive.

## Cosa dice la ricerca

Va detto con precisione, perché è il punto in cui molte pagine diventano vaghe: **le prove specifiche sullo shiatsu sono poche e deboli**.

Esistono studi su campioni piccoli che riportano miglioramenti su dolore lombare, ansia e qualità del sonno, ma con disegni sperimentali fragili e con una difficoltà evidente a costruire un confronto credibile — non si può somministrare uno shiatsu finto. Le revisioni sistematiche concludono in genere che i dati non bastano per trarre conclusioni.

Quello che è documentato meglio riguarda la famiglia più larga a cui lo shiatsu appartiene: il contatto manuale prolungato ha effetti misurabili su dolore percepito, ansia e tensione muscolare, ed è la stessa base su cui poggia [il massaggio in generale]({MASSAGGIO}).

Quanto ai meridiani, sono una mappa tradizionale senza corrispettivo anatomico, esattamente come i [chakra]({CHAKRA}): servono come sistema di orientamento a chi lavora, non come descrizione del corpo. In pratica lo shiatsu è una pratica di benessere e non una terapia sostitutiva, e chi lo presenta diversamente sta oltrepassando un confine.

## Controindicazioni

Vanno dette prima della seduta, e un operatore preparato le chiede senza che tu debba pensarci.

Escludono la seduta la febbre e le infezioni in corso, e soprattutto la trombosi o il sospetto di trombosi, che è la controindicazione più seria in assoluto. Richiedono adattamento o esclusione delle zone interessate le fratture recenti, l'osteoporosi grave e le protesi recenti. La gravidanza chiede posizioni dedicate e l'esclusione di alcuni punti, e quindi un operatore formato specificamente su questo. Con un tumore in corso serve il via libera dell'oncologo, con una terapia anticoagulante le pressioni profonde sono sconsigliate, e le lesioni cutanee escludono le zone interessate.

## Tre punti, e come si premono

Non sostituiscono una seduta, e sono il modo più semplice per capire di che tipo di sensazione stiamo parlando. La tecnica è la stessa per tutti e tre, e vale la pena impararla prima dei punti.

**Come si preme.** Appoggia il pollice o il dito senza premere, e prendi un respiro. Sul secondo respiro, mentre espiri, lascia che il peso scenda dentro — non spingere con la forza del dito, lascia andare il braccio. Sul terzo respiro sei arrivato: resta lì, fermo, per un minuto intero, continuando a respirare lentamente. Poi risali con la stessa lentezza con cui sei sceso, senza staccare di colpo.

**Il primo punto** sta nell'incavo carnoso del dorso della mano, fra pollice e indice. Premilo con il pollice dell'altra mano, angolando leggermente verso l'osso dell'indice. È il punto più usato per la tensione a testa e collo, e quasi tutti lo trovano sorprendentemente dolente la prima volta. **Va evitato in gravidanza.**

**Il secondo** sta sotto la nuca, nelle due fossette ai lati della colonna, dove il collo incontra il cranio. Usa i pollici di entrambe le mani insieme e lascia che la testa si appoggi indietro sul loro sostegno: è il peso della testa a fare il lavoro, non le braccia.

**Il terzo** sta quattro dita sotto il ginocchio, sul lato esterno della tibia, dentro il muscolo — non sull'osso. Nella tradizione è il punto legato all'energia generale e alla digestione, e si preme seduti, con il pollice.

La regola vale qui come nella seduta: se una pressione fa male in modo acuto o ti fa trattenere il respiro, alleggerisci o togli la mano.

## Come si sceglie chi lo pratica

Oltre ai [criteri generali]({SERIO}), quattro domande valgono la conversazione.

In quale scuola ti sei formato e per quante ore — le formazioni serie in Italia durano tre anni con pratica supervisionata, non un fine settimana. Namikoshi o Masunaga, che ti dice come lavorerà. Se è coperto da un'assicurazione professionale, che è una domanda normale da fare a chiunque metta le mani sul tuo corpo. E cosa fa se hai un problema che non è di sua competenza: la risposta giusta contiene il nome di una figura sanitaria.

E poi c'è il criterio che vale più di tutti, identico a quello del massaggio: **una seduta non deve fare male**. Scomoda sì, respirabile sempre.

## Domande frequenti

**Devo spogliarmi?**
No, ed è la caratteristica dello shiatsu. Si sta vestiti, con abiti comodi e preferibilmente di cotone.

**Fa male?**
La pressione è profonda ma sostenibile. Se stringi i denti o trattieni il fiato è troppa, e dirlo è tuo diritto.

**Che differenza c'è con il massaggio tradizionale?**
Il massaggio scorre sulla pelle con l'olio; lo shiatsu appoggia e affonda, senza scorrimento e senza olio, e include stiramenti e mobilizzazioni.

**È come l'agopuntura?**
Condivide la mappa tradizionale dei meridiani ma usa la pressione delle mani invece degli aghi. L'agopuntura in Italia è atto medico, lo shiatsu no.

**Quante sedute servono?**
Per una tensione specifica, un ciclo di quattro o cinque ravvicinate. Per il benessere generale, una al mese è la frequenza più comune.

**Posso farlo in gravidanza?**
Sì, con un operatore formato specificamente: cambiano le posizioni e alcuni punti vanno evitati. Diffida di chi non fa questa distinzione.

**Serve credere nei meridiani?**
No. Sono una mappa di orientamento per chi lavora, e l'effetto della pressione sui tessuti e sul sistema nervoso non dipende da cosa credi.
"""

# ─────────────────────────────────────────────────────────── cammini
TITOLO_CA = "I cammini italiani: quale scegliere la prima volta"
DESCR_CA = (
    "Sei cammini con chilometri e giorni veri, come si sceglie, quanto costa, "
    "la credenziale, cosa mettere nello zaino e come si evitano le vesciche."
)

CONTENUTO_CA = f"""\
Hai deciso che vuoi camminare per qualche giorno. Poi apri il computer e scopri che l'Italia ha decine di cammini, che le informazioni stanno sparse fra siti di associazioni, guide cartacee e gruppi di camminatori, e che ognuno ti dice che il suo è il più bello.

Questa guida mette in fila i principali con i numeri veri — chilometri, giorni, difficoltà — e poi affronta le tre cose che decidono se arrivi in fondo: cosa metti nello zaino, come si prenota, e come si evitano le vesciche. Su come si cammina quando camminare è una pratica, e non un modo di spostarsi, abbiamo scritto [a parte]({CAMMINARE}).

## I sei da cui si comincia

**La Via degli Dei**, da Bologna a Firenze, sono circa 130 chilometri in cinque o sei tappe, attraverso l'Appennino su strade romane e crinali. È il più consigliato per una prima volta e i motivi sono pratici: dura meno di una settimana, è ben segnato, ha alloggi lungo tutto il percorso e si raggiunge in treno da entrambe le estremità. L'impegno è medio, con dislivelli veri.

**Il Cammino di San Benedetto** va da Norcia a Montecassino, circa 300 chilometri in una quindicina di tappe fra Umbria e Lazio interno, passando per abbazie e paesi piccoli. È meno battuto dei più noti e ha un carattere silenzioso: capita di camminare mezza giornata senza incontrare nessuno.

**Il Cammino di San Francesco** collega la Verna, Assisi e Roma, e si percorre a sezioni. Il tratto più frequentato è quello verso Assisi, che per molti è il primo cammino italiano proprio per il valore del punto di arrivo. Alloggi abbondanti.

**La Via Francigena** è il grande itinerario europeo: nel tratto italiano va dal Gran San Bernardo a Roma per oltre mille chilometri e prosegue verso la Puglia. Non si fa tutta la prima volta, si sceglie una sezione, e la più percorsa è quella toscana da Lucca a Siena — splendida, e in primavera piuttosto affollata.

**Il Cammino Materano** è una rete di percorsi che convergono su Matera fra Puglia e Basilicata, con tappe fra i 15 e i 25 chilometri fra gravine e masserie. Ha una particolarità che gli altri non hanno: la città di arrivo si vede da lontano, per ore, prima di raggiungerla.

**Il Sentiero Italia del CAI** non è un cammino ma la spina dorsale escursionistica del paese, migliaia di chilometri dalle Alpi alla Sicilia percorsi a tappe da chi ha esperienza di montagna. È un'altra categoria di impegno e non è da qui che si comincia.

E vale la pena sapere che quasi ogni regione ha i suoi cammini minori, spesso meno affollati e altrettanto belli.

## Come si sceglie

Il tempo che hai è il primo filtro: cinque giorni portano alla Via degli Dei o a una sezione della Francigena, due settimane aprono San Benedetto o un cammino intero.

Il secondo filtro non sono i chilometri ma **il dislivello**. Venti chilometri in pianura e venti in Appennino sono due giornate che non si somigliano, e guardare il profilo altimetrico prima di scegliere risparmia sorprese.

Poi c'è la stagione. Aprile-giugno e settembre-ottobre sono i mesi giusti quasi ovunque; luglio e agosto sono duri al centro-sud e affollati in Toscana; l'inverno è per chi sa quello che fa.

E infine una domanda che quasi nessuno si pone in anticipo: **quanto vuoi stare solo**. La Francigena toscana a maggio è animata e la sera si mangia in compagnia; San Benedetto a ottobre può regalarti giornate intere senza incontrare nessuno. Sono due esperienze diverse, entrambe legittime, e conviene sapere quale stai cercando.

Un'ultima cosa pratica: un cammino che comincia e finisce vicino a una stazione ti risparmia due giorni di logistica.

## Quanto costa

Meno di quanto si pensi, ed è una delle ragioni per cui chi ne fa uno poi ne fa un altro.

Il posto letto in ostello, foresteria o alloggio per camminatori va in genere dai 15 ai 35 euro, e alcune strutture religiose lavorano su offerta libera. Mangiare costa quello che costa: colazione al bar, pranzo comprato in paese, cena in trattoria, fra i 20 e i 35 euro al giorno.

In tutto si sta fra i 40 e i 70 euro al giorno, meno se ti organizzi con i pasti. Quello che costa davvero, semmai, sono le scarpe se non le hai e i giorni di ferie.

## La credenziale

È il documento del camminatore: un cartoncino che si fa timbrare lungo il percorso — negli alloggi, nelle chiese, nei bar, negli uffici turistici.

Serve a due cose concrete. Dà accesso agli alloggi riservati ai camminatori, che sono spesso i più economici, e certifica il percorso per chi vuole l'attestato all'arrivo.

Si richiede alle associazioni che curano il cammino, in genere online, con qualche settimana di anticipo e per pochi euro; su alcuni cammini si trova anche al punto di partenza. E alla fine resta la cosa che si conserva: un cartoncino pieno di timbri diversi, ognuno di un posto in cui hai dormito.

## Prepararsi: le tre cose che contano

**Cammina prima.** Tre o quattro uscite da quindici chilometri nel mese precedente, con lo zaino che porterai davvero. È l'unico allenamento che conta, e serve meno alle gambe che ai piedi e alle spalle, che devono abituarsi al carico.

**Le scarpe devono essere già usate**, mai nuove: almeno cento chilometri sotto le suole prima di partire. È la regola che si legge ovunque e che ogni anno qualcuno ignora, tornando a casa il secondo giorno.

**Lo zaino sotto il dieci per cento del tuo peso**, acqua compresa. Sessanta chili di persona significano sei chili di zaino. È il numero che salva ginocchia e spalle, e quello che quasi tutti scoprono al terzo giorno quando è tardi.

Dentro ci vanno due cambi e non di più, un guscio antipioggia, un pile per la sera, delle ciabatte, un sacco lenzuolo, un kit minimo per le vesciche, una borraccia da almeno un litro e mezzo, i documenti e la credenziale. Fuori restano il terzo paio di pantaloni, l'asciugamano grande, i libri, e quasi tutto quello che stai considerando adesso.

Sulle prenotazioni: **le prime due notti sì, le altre no**. Il ritmo vero lo scopri camminando, e quasi tutti lo scoprono più lento di come lo avevano previsto.

E parti presto. Le sei o le sette del mattino cambiano una giornata d'estate: si cammina al fresco, si arriva per pranzo, e il pomeriggio è tuo.

## Le vesciche, che sono il vero motivo per cui si smette

Detta senza retorica: la ragione più comune per cui un cammino finisce prima non è la stanchezza né la pioggia. Sono i piedi.

E le vesciche non arrivano all'improvviso. Arrivano da un **punto caldo** — una zona che comincia a scaldare, poi a bruciare leggermente, di solito su un tallone o sul lato di un dito. Quel punto caldo dura fra i dieci e i trenta minuti prima di diventare una vescica, e in quella finestra si decide la settimana.

**Cosa fare quando lo senti.** Fermati subito, e intendo subito: non alla prossima fontanella, non fra un chilometro. Siediti, togli scarpa e calza, e guarda. Se la pelle è arrossata e calda ma intera, asciuga bene e coprila con un cerotto specifico per vesciche — quelli in idrocolloide, che restano attaccati e fanno da seconda pelle. Rimetti la calza tirandola bene, senza pieghe. Cinque minuti adesso ti risparmiano tre giorni.

**Come si evitano prima che succedano.** Calze tecniche e mai di cotone, perché il cotone trattiene l'umidità e l'umidità è metà del problema. Cambia le calze a metà giornata, anche solo per dieci minuti a piedi scoperti all'ombra. E allaccia bene le scarpe in discesa, dove il piede scivola in avanti e le unghie soffrono.

**Se una vescica si è già aperta**, disinfetta, copri, e tienila pulita. Se si arrossa intorno e diventa calda, non è più una questione di cammino: è un'infezione e vuole un medico.

## Da soli, in due o in gruppo

**Da soli** si sta con sé e si decide il ritmo, e si incontrano più persone di quanto si pensi: sui cammini frequentati ci si ritrova la sera negli stessi alloggi, e le conversazioni con chi ha camminato le tue stesse ore hanno una qualità particolare.

**In gruppo organizzato** ti tolgono la logistica: trasporto bagagli, alloggi prenotati, a volte una guida. È la formula giusta se è il pensiero dell'organizzazione a bloccarti. Se lo stai valutando, le [domande da fare prima di prenotare]({DOMANDE}) valgono anche qui, con due in più: chi porta gli zaini, e cosa succede se un giorno non riesci a camminare.

**In due** è la formula più difficile, e vale la pena saperlo prima di partire: ritmi diversi che si incontrano per otto ore al giorno mettono alla prova qualsiasi rapporto. Accordarsi in anticipo sul diritto di camminare separati e ritrovarsi la sera risolve quasi tutto.

## Domande frequenti

**Quale cammino per la prima volta?**
La Via degli Dei, per la durata contenuta, la segnaletica buona e la facilità di arrivo e ritorno in treno.

**Quanti chilometri al giorno?**
Quindici per cominciare, venti quando il corpo si è abituato. Chi parte a venticinque il primo giorno spesso si ferma al terzo.

**Devo essere allenato?**
Non servono prestazioni, serve abitudine a camminare. Tre uscite lunghe nel mese prima bastano per la maggior parte dei cammini di questa lista.

**Si può fare con il cane?**
Su molti cammini sì, ma gli alloggi che lo accettano sono meno: va verificato tappa per tappa prima di partire.

**Serve la credenziale?**
Non è obbligatoria per camminare, ma dà accesso agli alloggi riservati e costa pochi euro. Conviene.

**Quando è la stagione migliore?**
Aprile-giugno e settembre-ottobre quasi ovunque. Luglio e agosto sono difficili al centro-sud.

**È una cosa religiosa?**
Molti cammini nascono da percorsi di pellegrinaggio e attraversano luoghi religiosi, ma si percorrono per qualsiasi ragione e nessuno chiede la tua.
"""

# ────────────────────────────────────────────────────────── promuovere
TITOLO_PR = "Come promuovere un ritiro e riempire i posti"
DESCR_PR = (
    "Il pubblico che hai già, la lista contatti a norma, la pagina che "
    "convince, la caparra, e il calendario di lancio settimana per settimana."
)

CONTENUTO_PR = f"""\
Il luogo è quello giusto. Il programma lo hai costruito per mesi. Le date sono bloccate, la struttura ha confermato, e tu sei pronto.

Poi arriva la settimana prima e gli iscritti sono quattro su otto.

È la scena che quasi tutti conoscono, e la cosa che la rende più amara è che i posti vuoti non pesano quanto sembra: pesano molto di più. Come mostrano i conti nella [guida al prezzo]({PREZZO}), gli ultimi due posti di un ritiro sono spesso quasi tutto il margine — sotto il pareggio lavori gratis, e sopra ogni iscritto porta la differenza piena fra prezzo e costo.

Questa guida raccoglie quello che funziona, in ordine di importanza, e in fondo mette tutto in un calendario.

## Il pubblico più prezioso è quello che hai già

L'errore più comune è cercare sconosciuti prima di aver parlato con chi ti conosce. Chi ha già praticato con te, chi ha ricevuto un tuo trattamento, chi ti segue da mesi: sono persone che valgono molte volte qualsiasi pubblico freddo, perché la parte difficile — decidere se fidarsi — l'hanno già fatta.

In pratica significa tre cose. Annunciare il ritiro **prima ai tuoi**, con una comunicazione dedicata e non con un post che vedranno per caso, magari con una condizione riservata a chi prenota entro una data. Curare la lista contatti come si cura un giardino, perché è l'unico asset della tua attività che nessun algoritmo può toglierti. E chiedere il passaparola in modo esplicito: «se conosci qualcuno a cui questo ritiro farebbe bene, giragli questo messaggio» funziona molto meglio di quanto sembri, perché toglie a chi legge il compito di capire cosa vorresti.

## La lista contatti, fatta come si deve

Questa parte gli operatori la sbagliano regolarmente, e può costare cara.

Il punto di partenza è che **il consenso va raccolto, non presunto**. Avere l'email di qualcuno perché ha partecipato a una tua lezione non ti autorizza a inserirlo in una lista di comunicazioni promozionali: serve un consenso specifico, dato liberamente, e documentabile.

Concretamente vuol dire un modulo con la casella non pre-spuntata e una riga chiara su cosa riceverà e ogni quanto. Vuol dire che ogni email deve poter essere disiscritta con un clic, e che la disiscrizione va rispettata subito, non alla prossima pulizia. Vuol dire tenere traccia di quando e come hai raccolto ogni contatto, perché se ti viene chiesto devi poterlo dimostrare. E vuol dire non comprare liste e non importare la rubrica del telefono, che oltre a essere fuori regola funziona malissimo.

Una lista di duecento persone che ti hanno detto di sì vale più di duemila indirizzi presi da qualche parte, e ti fa dormire meglio.

## La pagina del ritiro

Chi arriva sulla pagina decide in pochi minuti, e in quei minuti deve trovare risposte.

Deve vedere **chi conduce**, con volto e storia, perché le persone non prenotano un programma: prenotano te. Deve trovare un programma giorno per giorno, anche indicativo ma concreto. Deve sapere cosa è incluso e cosa no, senza zone grigie. E deve vedere prezzo e condizioni di cancellazione senza doverli cercare: nasconderli non aumenta le prenotazioni, aumenta le domande via messaggio e gli abbandoni silenziosi di chi non ha voglia di scrivere.

Poi servono le recensioni di chi c'è già stato, verificate e con nome, e le foto vere del luogo e dei tuoi ritiri passati — le immagini d'archivio si riconoscono, e raccontano che qualcosa non è ancora reale.

E infine, la cosa che quasi nessuno mette: **le risposte alle domande che si fanno tutti**. Quante persone siete, come si dorme, quanto è obbligatorio il programma, cosa succede se sto male. [Sono note]({DOMANDE}), e metterle sulla pagina ti risparmia venti conversazioni e convince le persone che le stavano per fare.

## La caparra

Un «mi interessa» non riempie un ritiro. Una caparra sì.

La prenotazione con caparra fra il venti e il trenta per cento e saldo successivo è lo standard, e il motivo per cui funziona non ha bisogno di statistiche: **chi ha versato del denaro si comporta in modo diverso da chi ha scritto un messaggio**. Ha preso una decisione, l'ha segnata in calendario, e da quel momento non sta più valutando altre tre opzioni in parallelo.

Per te il vantaggio è ancora più concreto. Pianifichi su numeri reali invece che su intenzioni, e sai con settimane di anticipo se il gruppo minimo è raggiunto — che è esattamente l'informazione che ti serve per decidere in tempo.

## I social: semina, non raccolta

I social servono, ma non come si pensa. Il post «ultimi posti disponibili» pubblicato tre volte a settimana non riempie ritiri: costruisce assuefazione, e insegna a chi ti segue a scorrere oltre.

Quello che funziona è la semina lunga: contenuti che mostrano la tua pratica, il luogo, le persone con il loro consenso, i momenti veri. Chi ti segue per mesi e vede coerenza, quando sente il bisogno di fermarsi penserà a te — e non perché glielo hai chiesto.

Il ritiro si vende nei mesi in cui non lo stai vendendo.

## La collaborazione moltiplica

Un ritiro condotto da due professionisti complementari — yoga e suono, meditazione e lavoro sul corpo — raggiunge due comunità con lo stesso sforzo. Divide i costi, moltiplica il pubblico, e quasi sempre migliora l'esperienza perché due sguardi vedono più di uno.

Su come si propone, una cosa concreta che fa la differenza: scrivi a chi stimi con una **proposta già abbozzata** — date, luogo, ipotesi di programma, come dividereste ricavi e costi — non con un generico «facciamo qualcosa insieme». La prima richiede una risposta sì o no, la seconda richiede a chi la riceve di fare il lavoro al posto tuo, e per questo resta senza risposta.

## Dopo il ritiro, che è il momento più sottovalutato

Il lavoro migliore comincia quando il ritiro finisce, ed è il momento in cui quasi tutti sono troppo stanchi per farlo.

Chiedi la recensione **subito**, nei giorni successivi, quando l'esperienza è ancora viva, e rendila facile: un link, due minuti. Annuncia la prossima edizione ai partecipanti prima che a chiunque altro, perché chi ha appena vissuto un buon ritiro con te è il pubblico più caldo che avrai mai. Resta in contatto con delicatezza, dove una comunicazione stagionale vale più di dieci post.

E scrivi cosa ha funzionato e cosa no entro tre giorni, finché ricordi i dettagli. È la cosa che rende la seconda edizione più semplice della prima, ed è anche la prima a saltare.

## Il calendario di lancio

Per un weekend. Per una settimana, sposta tutto indietro di un mese.

Le settimane non sono arbitrarie: seguono il modo in cui le persone decidono. Chi ti conosce prenota presto se sa che esiste, e chi non ti conosce ha bisogno di vederti passare più volte prima di considerare l'idea.

- **Quattro mesi prima.** Date bloccate con la struttura, prezzo calcolato, pagina scritta. Non annunci ancora niente.
- **Tre mesi prima.** Annuncio alla tua lista e ai tuoi allievi, con la condizione riservata. Le iscrizioni si aprono con caparra.
- **Dieci settimane prima.** Annuncio pubblico, con un post che racconta il perché di questo ritiro e non l'elenco delle attività.
- **Otto settimane prima.** Scade la condizione riservata, ed è di solito il momento in cui arriva la prima ondata.
- **Sei settimane prima.** Verifica onesta: a che punto sei rispetto al gruppo minimo? Se sei sotto la metà, le leve si attivano adesso, non fra un mese.
- **Quattro settimane prima.** Ultima chiamata pubblica, e riattivazione personale di chi aveva chiesto informazioni senza prenotare.
- **Tre settimane prima.** Decisione sul gruppo minimo. Se si annulla, si annulla adesso: farlo ora è una scelta professionale, farlo tre giorni prima è un danno che resta.
- **Una settimana prima.** Informazioni pratiche ai partecipanti: come si arriva, cosa portare, a che ora, chi chiamare.

## Cosa non fare

Quattro cose bruciano fiducia più velocemente di quanto qualsiasi campagna la costruisca.

La **scarsità finta**: «ultimi due posti» ripetuto per tre settimane si nota, e chi ti segue da tempo se lo ricorda. Il **conto alla rovescia perpetuo**, che se ogni annuncio è un'urgenza allora nessuno lo è. **Promettere risultati** — «tornerai trasformato» è una promessa che non puoi mantenere, ed è anche il tipo di frase che allontana le persone più consapevoli, cioè le stesse che leggono [come si riconosce chi lavora bene]({SERIO}). E **sparire fra un'edizione e l'altra**, perché la visibilità non è una campagna, è una presenza.

## Il punto di tutto

Nessuna di queste strategie è un trucco. Sono la stessa cosa detta in modi diversi: rendere visibile e affidabile un lavoro che lo merita. La visibilità porta le persone alla porta, e la trasparenza — prezzi, condizioni, recensioni — le fa entrare.

## Domande frequenti

**Quanto tempo prima devo iniziare a promuovere?**
Almeno tre mesi per un weekend, quattro o sei per una settimana. I primi posti si riempiono con la tua comunità, gli ultimi con la visibilità esterna: entrambi hanno bisogno di tempo.

**Devo fare pubblicità a pagamento?**
Non all'inizio. Prima esaurisci i canali gratuiti: la pubblicità amplifica quello che già funziona, e se la pagina non convince pagherai per portare persone a una porta chiusa.

**Come gestisco le cancellazioni?**
Con regole scritte prima della prenotazione: entro quando si può annullare e cosa viene rimborsato. Le decidi tu, l'importante è che chi prenota le veda prima di pagare.

**Un ritiro piccolo può essere sostenibile?**
Sì, se i numeri sono onesti. Otto persone con caparra sono meglio di venti interessati: calcola il pareggio prima di fissare il prezzo, e considera anche [come si fattura tutto questo]({IVA}).

**Posso scrivere a chi ha partecipato a una mia lezione?**
Per comunicazioni promozionali serve un consenso specifico, raccolto e documentabile. Avere l'indirizzo per un altro motivo non basta.

**Quante email posso mandare senza infastidire?**
Nella fase di lancio, tre o quattro in tre mesi sono normali se ognuna dice qualcosa di nuovo. Il problema non è la frequenza, è mandare quattro volte lo stesso messaggio.

**Meglio annunciare prima le date o prima il prezzo?**
Insieme. Un annuncio senza prezzo genera messaggi che devi gestire uno a uno, e perde le persone che non scrivono.
"""

PEZZI = [
    (CERCHI, TITOLO_CE, DESCR_CE, CONTENUTO_CE),
    (SHIATSU, TITOLO_SH, DESCR_SH, CONTENUTO_SH),
    (CAMMINI, TITOLO_CA, DESCR_CA, CONTENUTO_CA),
    (PROMO, TITOLO_PR, DESCR_PR, CONTENUTO_PR),
]


def analizza(testo):
    """La quota di parole che sta in prosa continua, cioe' in blocchi di
    due o piu' frasi che non siano titoli, elenchi o frammenti in
    grassetto. E' l'unica misura che corrisponde a "mi perdo mentre
    leggo": le parole per paragrafo contano una voce di elenco come un
    paragrafo e non vedono la differenza."""
    blocchi = [b.strip() for b in testo.split("\n\n") if b.strip()]
    prosa = frammenti = 0
    parole_prosa = 0
    for b in blocchi:
        if b.startswith("#"):
            continue
        if b.startswith(("-", ">", "1.", "2.", "3.", "4.", "5.")):
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
        q1, p1, f1 = analizza(doc["content"])
        q2, p2, f2 = analizza(contenuto)
        print(f"{titolo[:56]:58} prosa {q1}% → {q2}%   "
              f"frammenti {f1} → {f2}   parole "
              f"{len(doc['content'].split())} → {len(contenuto.split())}")
        if doc["content"] == contenuto:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya",
            "updated_at": datetime.now(timezone.utc)}})

    print("\n── il Magazine, ordinato per quota di prosa")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    righe = sorted(((analizza(a["content"]), a["slug"]) for a in arts))
    for (q, p, f), s in righe:
        segno = "  " if q >= 85 else "→ "
        print(f"  {segno}{s[:46]:48} {q:3}%  frammenti {f}")
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\n  link rotti: {rotti or 'nessuno'}")
    print(f"  sopra l'85%: {sum(1 for (q, _, _), _ in righe if q >= 85)} "
          f"su {len(arts)}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
