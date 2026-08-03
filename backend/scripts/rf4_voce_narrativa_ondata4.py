"""RF4 — voce narrativa, quarta ondata: cinque pezzi.

Tema natale (82%, 11 frammenti), alimentazione ayurvedica (82%, 11),
domande prima di prenotare (83%, 10), ciclo mestruale (78%, 8),
camminare (80%, 8).

LE PRATICHE DI QUESTA ONDATA, che sono la parte che conta.

CAMMINARE. Il bagno di foresta era sei righe puntate — vai piano,
niente meta, telefono spento, un senso alla volta. E' la pratica piu'
facile da spiegare male, perche' la difficolta' vera non e' capire cosa
fare: e' reggere la lentezza. Ora e' guidata dai primi passi
all'ultima mezz'ora, con quello che succede alla testa in mezzo.

CICLO. Il diario di tre mesi era un elenco di quattro punti. Ora e'
una pratica accompagnata, con il perche' dietro ogni regola — in
particolare quella di non guardare i dati prima del terzo mese, che
serve a non cercare conferme.

ALIMENTAZIONE. Le tre cose da cui cominciare erano una lista. Ora sono
raccontate come si applicano davvero a una giornata italiana, dove il
pasto principale a mezzogiorno si scontra con la cena come momento
sociale.

DOMANDE PRIMA DI PRENOTARE resta un articolo a domande, perche' li'
l'elenco E' l'informazione — ma le domande hanno smesso di essere
frammenti isolati e stanno dentro un ragionamento per gruppi.

    venv/bin/python scripts/rf4_voce_narrativa_ondata4.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

TEMA = "lettura-tema-natale-cosa-aspettarsi"
CIBO = "alimentazione-ayurvedica-principi-sei-sapori"
DOMANDE_S = "domande-da-fare-prima-di-prenotare-un-ritiro"
CICLO = "ciclo-mestruale-quattro-fasi-come-ascoltarlo"
CAMMINARE = "camminare-bagni-di-foresta-cammini"

SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
TAROCCHI = "/blog/tarocchi-oracoli-strumento-evolutivo"
AYU = "/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
DETOX = "/blog/digiuno-consapevole-detox-benefici-falsi-miti"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
CERCHI = "/blog/cerchi-di-donne-cosa-sono-come-funzionano"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
PREZZO = "/blog/prezzo-giusto-ritiro-come-calcolarlo"
BREATH = "/blog/breathwork-cose-tecniche-benefici"
CAMMINI_IT = "/blog/cammini-italiani-quale-scegliere-la-prima-volta"

# ─────────────────────────────────────────────────────── tema natale
TITOLO_TE = "Lettura del tema natale: cos'è, come funziona, cosa aspettarsi"
DESCR_TE = (
    "Com'è fatta una carta, Sole Luna e Ascendente, come si svolge un "
    "consulto, cosa dice la ricerca e come si trova l'ora esatta di nascita."
)

CONTENUTO_TE = f"""\
«Ma quindi mi dici il futuro?»

È la domanda che chi legge i temi natali riceve più spesso, e la risposta sorprende quasi tutti: no. Una lettura del tema natale non predice, racconta. E quello che racconta sei tu.

Questa guida spiega com'è fatta una carta — perché senza saperlo un consulto resta un'ora di parole affascinanti e opache — cosa succede durante l'incontro, come si trova l'ora esatta di nascita che serve per calcolarla, e cosa dice la ricerca. Quest'ultima parte è quella che di solito manca, e vale la pena leggerla fino in fondo.

## Cos'è il tema natale

È la fotografia del cielo nel momento esatto della nascita: dove si trovavano il Sole, la Luna e i pianeti, e come si disponevano rispetto al luogo in cui sei venuto al mondo.

Servono tre dati — data, ora esatta e luogo — e quello che pesa di più è l'ora. Bastano pochi minuti di differenza per cambiare l'ascendente, e con l'ascendente cambia buona parte della lettura.

Nell'astrologia evolutiva, che è l'approccio diffuso oggi in Italia, questa mappa non è un destino scritto ma un linguaggio simbolico per esplorare inclinazioni, nodi e potenzialità. I pianeti sono archetipi, non sentenze.

## Come è fatta una carta

Quattro elementi, e conoscerli rende comprensibile un consulto che altrimenti sembra una lingua straniera.

**I pianeti dicono il cosa.** Dieci corpi celesti, ognuno associato a una funzione psichica: il Sole è l'identità e la direzione, la Luna il mondo emotivo e i bisogni, Mercurio il pensiero e la parola, Venere il modo di amare e di valutare, Marte l'azione e la rabbia, Giove l'espansione e il senso, Saturno il limite e la responsabilità. I tre lenti — Urano, Nettuno, Plutone — si muovono così adagio da riguardare intere generazioni più che il singolo.

**I segni dicono il come.** I dodici segni colorano il modo in cui ogni pianeta si esprime: Marte in Ariete agisce di slancio, Marte in Bilancia agisce dopo aver soppesato. È lo stesso motore con due guide diverse.

**Le case dicono il dove.** Dodici settori che indicano gli ambiti di vita — il corpo e l'immagine, i beni, la comunicazione, la casa e le origini, e così via. Un pianeta in una casa dice in quale zona della vita quel tema si gioca.

**Gli aspetti dicono le relazioni.** Sono gli angoli fra i pianeti: alcuni indicano scorrevolezza, altri attrito. Nella lettura evolutiva l'attrito è la parte interessante, perché è lì che di solito sta il lavoro.

## Sole, Luna e Ascendente

Sono i tre che tutti cercano per primi, e anche i tre più utili da capire, perché insieme raccontano già una figura riconoscibile.

Il **Sole** è il segno dell'oroscopo, quello che tutti conoscono. Indica la direzione che si sta imparando a percorrere, più che quello che si è già — ed è il motivo per cui molte persone non si riconoscono nel proprio segno a vent'anni e ci si riconoscono a quaranta.

La **Luna** è la vita emotiva: come ci si consola, di cosa si ha bisogno, come si reagisce quando si è stanchi. Molte persone si riconoscono più nella Luna che nel Sole, ed è una delle scoperte più frequenti di una prima lettura.

L'**Ascendente** è il segno che sorgeva all'orizzonte nell'ora della nascita: il modo in cui ci si presenta al mondo e si affrontano le cose nuove. È l'elemento che richiede l'ora esatta, ed è la ragione per cui l'ora conta più della data.

## Come si svolge una lettura

Prima dell'incontro si inviano i dati di nascita, e chi legge prepara la carta: è uno studio che avviene in anticipo, e un consulto serio non si improvvisa davanti a te.

L'incontro dura in genere fra i 60 e i 90 minuti, di persona o online, e non è un monologo: è un dialogo. Chi conduce racconta quello che la carta suggerisce, tu riconosci o non riconosci quei temi nella tua vita, e la lettura prende senso proprio in quello scambio. È anche il motivo per cui una lettura registrata e spedita vale molto meno di un incontro: manca la metà che dovresti mettere tu.

Si esplorano l'energia vitale, il mondo emotivo, il modo di amare e di agire, dove si tende a ripetere schemi e dove la carta suggerisce direzioni. In chiave evolutiva l'attenzione va soprattutto ai nodi, cioè ai punti di tensione che, letti bene, diventano leve.

Molti lasciano una registrazione o una sintesi scritta, e i temi emersi continuano a lavorare nei giorni successivi.

## I transiti, e il ritorno di Saturno

Oltre alla carta di nascita, che non cambia mai, c'è il movimento dei pianeti nel cielo di oggi rispetto a quella carta. Sono i **transiti**, ed è il motivo per cui alcune persone tornano da chi legge in momenti precisi della vita invece che a caso.

Il più noto è il **ritorno di Saturno**. Saturno impiega circa ventinove anni a completare il giro, quindi intorno ai ventotto o trent'anni torna esattamente dove stava alla nascita, e ci torna di nuovo verso i cinquantotto. Nella tradizione astrologica quel passaggio coincide con un periodo di resa dei conti e di assunzione di responsabilità.

Va detto con precisione: è una **coincidenza narrativa efficace**, non un meccanismo dimostrato. Che intorno ai trent'anni molte persone rivedano la propria vita è un fatto sociologico prima che astronomico — è l'età in cui si consolidano lavoro, legami e scelte fatte a venti. Il che non toglie che come cornice funzioni bene.

## Cosa dice la ricerca

Qui va detta la cosa per intero, perché è la parte che di solito manca e perché ometterla renderebbe questa guida uguale a tutte le altre.

**L'astrologia non ha validazione scientifica.** Non è un'opinione: è stata messa alla prova.

Lo studio più noto è di Shawn Carlson, pubblicato su *Nature* nel 1985. Era disegnato in doppio cieco, e — dettaglio che conta — il protocollo era stato **concordato in anticipo con astrologi professionisti**, che lo avevano giudicato equo. Il compito era abbinare carte natali a profili di personalità ottenuti con un test standardizzato. Il risultato: non hanno fatto meglio del caso. Altri lavori successivi sono arrivati a conclusioni analoghe.

E allora perché una lettura fa spesso un'impressione così forte? Le ragioni sono le stesse dei [tarocchi]({TAROCCHI}), e sono interessanti di per sé.

C'è **l'effetto Barnum**, cioè la tendenza a riconoscersi in descrizioni abbastanza generali da valere per molti — che funziona perché ci mettiamo dentro il nostro materiale. C'è **la ricchezza del sistema**: una carta contiene decine di elementi combinabili, e chi legge sceglie, spesso in perfetta buona fede, quelli che risuonano con la persona che ha davanti. E c'è la cosa più semplice, cioè **un'ora dedicata a te**, in cui qualcuno parla di te con attenzione e tu ti racconti: è un'esperienza rara e produce un effetto reale a prescindere dallo strumento.

Nulla di tutto questo toglie valore alla lettura come strumento simbolico di auto-esplorazione, che funziona quando apre consapevolezza. Toglie valore a chi la vende come conoscenza predittiva. E chi la pratica con serietà questa distinzione la fa da solo — è il primo criterio con cui riconoscerlo.

## A cosa serve, e a cosa no

Serve a vedersi da un'angolazione nuova, a dare un nome a dinamiche che si sentono da sempre senza saperle formulare, a orientarsi nei momenti di passaggio, ad aprire domande su cui lavorare.

Non serve a predire il futuro, a prendere decisioni al posto tuo, a sostituire un percorso terapeutico, a dire chi sposare o quando cambiare casa. E non serve mai a decidere di salute: nessuna carta dice se fare un esame, un intervento o una terapia.

## Come si trova l'ora esatta di nascita

È la domanda pratica più frequente, e ha una risposta semplice che quasi nessuno conosce.

L'ora è registrata nell'**atto di nascita**, conservato dal Comune in cui sei nato. Quello che devi chiedere è un **estratto dell'atto di nascita**: a differenza del certificato, l'estratto riporta anche l'ora. Molti Comuni permettono di richiederlo online o via posta elettronica, gratuitamente, e arriva in pochi giorni.

Anche il cartellino dell'ospedale o il libretto della nascita spesso la riportano. Quello che invece è il dato meno affidabile in assoluto è la memoria dei genitori: gli scarti di mezz'ora sono frequentissimi, e mezz'ora può cambiare l'ascendente.

Senza ora si può comunque lavorare, con una carta parziale in cui mancano ascendente e case, cioè una parte consistente.

## Come si sceglie chi legge

Chi lavora con serietà **chiede l'ora esatta**, perché senza sta lavorando su una carta incompleta e lo sa. **Non promette previsioni**: il linguaggio serio parla di tendenze, archetipi e domande, quello commerciale parla di scoprire cosa accadrà. E **dice che l'astrologia non è una scienza** — chi la presenta come dimostrata sta dicendo il falso, e su questo non ci sono scuole di pensiero.

Poi non tocca salute, denaro e decisioni legali, e ti lascia libero: un buon consulto si chiude senza agganci, senza ritorni mensili e senza paure indotte.

Una lettura in Italia costa fra i 60 e i 120 euro. Valgono anche i [criteri generali]({SERIO}).

## Domande frequenti

**Serve sapere l'ora esatta di nascita?**
Il più possibile. La trovi nell'estratto dell'atto di nascita del Comune. Senza, si lavora su una carta parziale, priva di ascendente e case.

**L'astrologia è scientificamente provata?**
No. Le verifiche controllate, a partire dallo studio di Carlson pubblicato su Nature nel 1985, non hanno trovato risultati migliori del caso. Il valore di una lettura sta altrove.

**Che differenza c'è con l'oroscopo?**
L'oroscopo dei giornali usa solo il segno solare, uguale per un dodicesimo dell'umanità. Il tema natale è calcolato sul minuto e sul luogo della tua nascita.

**Online o di persona?**
La qualità dipende dalla preparazione di chi legge, non dal mezzo.

**Ogni quanto ha senso una lettura?**
La carta natale non cambia: una lettura approfondita può bastare per anni. Hanno senso ritorni mirati nei momenti di passaggio, non appuntamenti mensili.

**Cos'è il ritorno di Saturno?**
Il momento, intorno ai ventinove anni e poi ai cinquantotto, in cui Saturno torna dove stava alla nascita. Nella tradizione coincide con una resa dei conti; è una narrazione efficace, non un meccanismo dimostrato.

**Posso leggermi la carta da solo?**
I calcoli sono gratuiti online e i tre elementi principali si imparano. L'interpretazione d'insieme è un'altra cosa, e come per i [tarocchi]({TAROCCHI}) lo sguardo esterno vede quello che il proprio punto cieco copre.
"""

# ────────────────────────────────────────────── alimentazione ayurvedica
TITOLO_CI = "Alimentazione ayurvedica: come si mangia, prima ancora di cosa"
DESCR_CI = (
    "Il fuoco digestivo, le nove regole che valgono per tutti, i sei sapori, "
    "gli orientamenti per costituzione e cosa regge alla prova della ricerca."
)

CONTENUTO_CI = f"""\
«Mangiare secondo la tua costituzione» suona come l'ennesima dieta con un nome esotico, e la maggior parte delle pagine che trovi in italiano rafforzano l'impressione: partono dai tre elenchi di cosa mangia vata, cosa mangia pitta, cosa mangia kapha.

Il problema è che quegli elenchi presuppongono che tu sappia la tua costituzione, e la costituzione non si stabilisce da soli.

Ma soprattutto: nell'ayurveda quella non è la domanda principale. Una dieta chiede *cosa* mangiare; questo sistema chiede prima *come*, e considera quella la parte che cambia di più — al punto che, nei suoi testi, un cibo perfetto mangiato male vale meno di un cibo qualsiasi mangiato bene.

Questa guida segue lo stesso ordine: prima il come, che vale per chiunque e si applica da stasera, poi i sapori, e solo alla fine le differenze fra costituzioni.

## Il centro di tutto: il fuoco digestivo

L'ayurveda chiama *agni* la capacità digestiva e la mette al centro di tutto il sistema.

Il ragionamento è semplice: non conta quello che mangi, conta quello che riesci a trasformare. Un alimento eccellente che il corpo non digerisce produce quello che il sistema chiama *ama*, un residuo non trasformato che si accumula e che nel linguaggio ayurvedico sta all'origine di gran parte dei disturbi.

Da qui discende tutto il resto: le regole che seguono servono a una cosa sola, non spegnere quel fuoco.

E c'è un modo per capire se sta funzionando, con i segni che il sistema usa: hai fame a orari regolari, dopo mangiato ti senti leggero e non assonnato, la lingua al mattino è pulita, l'intestino è regolare, l'alito è neutro.

## Come si mangia

Nove indicazioni che valgono per chiunque, a prescindere dalla costituzione, e che producono il cambiamento maggiore.

**Il pasto principale a mezzogiorno**, perché nel sistema la capacità digestiva segue il sole ed è massima a metà giornata. È la regola più importante e la più disattesa in Italia, dove la cena è il pasto sociale e spostare il baricentro significa riorganizzare una giornata intera. Chi ci riesce anche solo tre volte a settimana se ne accorge.

**La cena leggera e presto**, idealmente tre ore prima di coricarsi. In questo schema una cena pesante e tardiva è la causa più comune di sonno cattivo e di lingua sporca al mattino.

**Mangia solo quando hai fame.** Non per orario, non per noia, non perché è ora. E se a un pasto non hai fame, il sistema dice di saltarlo: significa che il precedente non è ancora stato digerito.

**Lascia un quarto di stomaco vuoto.** L'indicazione classica divide il pasto in metà cibo solido, un quarto liquido, un quarto aria. In pratica: alzati da tavola che potresti ancora mangiare qualcosa.

**Siediti, e senza schermo.** È la raccomandazione che le persone applicano meno e che cambia di più. Mangiare in piedi, camminando o davanti a un telefono riduce la percezione della sazietà, e questa parte è ampiamente documentata anche fuori dall'ayurveda.

**Acqua tiepida, a piccoli sorsi.** L'acqua ghiacciata durante il pasto è, nella logica del sistema, il modo più diretto per spegnere il fuoco. Un bicchiere di acqua calda al risveglio è l'altra abitudine classica.

**Niente frutta a fine pasto**, perché digerisce più rapidamente del resto e mangiata dopo resta ferma. Lontano dai pasti va benissimo.

**Cucinato meglio che crudo**, soprattutto d'inverno e per chi ha digestione delicata. L'insalata cruda a cena, in questo schema, è fra le cose più difficili da digerire.

**Le spezie non sono decorazione.** Zenzero, cumino, finocchio, curcuma, pepe nero servono a sostenere la digestione — e ogni cucina regionale del mondo è arrivata da sola a combinazioni simili.

## I sei sapori

L'ayurveda classifica gli alimenti in sei sapori, i *rasa*, e sostiene che un pasto completo li contenga tutti, anche in quantità minime.

Il **dolce** — cereali, latte, frutta matura, carne, verdure amidacee — nutre e appesantisce, ed è il sapore dominante di quasi tutta la dieta occidentale. L'**acido**, dal limone all'aceto ai fermentati al pomodoro, stimola appetito e digestione. Il **salato** trattiene i liquidi e stimola. Il **piccante** — peperoncino, zenzero, pepe, cipolla, aglio — riscalda e smuove. L'**amaro**, che sta nelle verdure a foglia scura, nel tarassaco, nel carciofo, nella curcuma e nel cacao puro, alleggerisce. E l'**astringente** — legumi, melagrana, tè, mela verde, molte verdure crude — asciuga e compatta.

C'è un'osservazione che vale a prescindere da quanto si creda al modello: **la nostra alimentazione è satura di dolce e salato e povera di amaro e astringente**. Aggiungere verdura amara e legumi è un'indicazione che funziona per ragioni che l'ayurveda spiega a modo suo e la nutrizione moderna a modo proprio, arrivando alla stessa conclusione.

## Le tre costituzioni, come orientamento

Prima una premessa che vale tutto il resto: la costituzione non si stabilisce da soli e nemmeno con un test online, e i dettagli su come funziona stanno nella [guida generale all'ayurveda]({AYU}). Quelli che seguono sono orientamenti, non prescrizioni.

**Vata** è leggero, freddo, secco, irregolare, e si bilancia con il contrario: cibi caldi, cotti, oleosi, morbidi — zuppe, cereali cotti, verdure al vapore con olio, spezie dolci. Si riducono crudo, freddo e secco, e soprattutto l'irregolarità degli orari, che per vata pesa più del contenuto del piatto.

**Pitta** è caldo, intenso, acido, e si bilancia con il fresco: verdure dolci e amare, cereali, legumi, latticini freschi, frutta dolce. Si riducono piccante, fritto, alcol, aceto e pomodoro in eccesso — e si evitano i pasti saltati, perché pitta affamato diventa irritabile.

**Kapha** è pesante, umido, lento, e si bilancia con il leggero e il caldo: verdure, legumi, cereali integrali, spezie piccanti, poco olio. Si riducono latticini, dolci e fritti, e soprattutto le porzioni. È la costituzione che beneficia di più del saltare la cena ogni tanto.

Dietro i tre elenchi c'è un principio solo: **il simile aumenta il simile, l'opposto bilancia**. Ed è la ragione per cui a due persone con lo stesso problema si consigliano cose opposte.

## Le stagioni

L'ayurveda considera la stagione tanto quanto la costituzione, e questa parte è la più facile da applicare perché non richiede di sapere niente di sé.

D'**inverno** predominano freddo e secco, e si mangia caldo, cotto, unto: zuppe, stufati, cereali, spezie riscaldanti. In **primavera** il sistema colloca l'alleggerimento — verdure amare, meno latticini e dolci, porzioni ridotte — ed è anche il momento in cui colloca le pratiche di purificazione, su cui abbiamo scritto [a proposito di digiuno e detox]({DETOX}). D'**estate** si raffredda, con frutta, verdure fresche, meno piccante e meno alcol. In **autunno** il vento e il secco chiedono di tornare a cibi caldi, oleosi e regolari.

## Le combinazioni sconsigliate

L'ayurveda ne elenca diverse, e le più citate sono latte con frutta acida, latte con pesce, miele scaldato, frutta insieme ad altri cibi.

Va detto con precisione: **queste indicazioni non hanno riscontro nella scienza dell'alimentazione**. Sono parte della tradizione e vanno prese come tale.

Il principio generale che le sottende, però, ha una sua utilità verificabile: pasti semplici, con pochi alimenti diversi, si digeriscono meglio di pasti complessi. Chi passa da un piatto unico bilanciato a un pasto con sei portate se ne accorge senza bisogno di un modello per spiegarlo.

## Cosa dice la ricerca

Ci sono due risposte diverse ed è importante non confonderle.

**Sulla dieta per dosha non c'è nulla.** Non esistono studi che validino un'alimentazione differenziata per costituzione ayurvedica, e il modello dei dosha non ha riscontro nella fisiologia. Chi presenta questo come scientificamente provato sta usando prove che riguardano altro.

**Sul come si mangia c'è parecchio**, ed è la parte interessante, perché la ricerca contemporanea è arrivata per strade completamente diverse a conclusioni sovrapponibili. Concentrare le calorie nella prima parte della giornata e cenare presto ha effetti documentati su metabolismo e qualità del sonno, ed è uno dei filoni più solidi della cronobiologia nutrizionale. Mangiare senza distrazioni aumenta la percezione di sazietà e riduce la quantità assunta, con una letteratura consistente. La regolarità degli orari ha effetti su glicemia e appetito indipendenti dal contenuto. E verdure amare e legumi in più sono una raccomandazione su cui ayurveda e nutrizione moderna concordano senza saperlo.

La sintesi utile è questa: la parte esoterica del sistema resta una tradizione, la parte comportamentale è la meno esotica e la più sostenuta. Ed è anche quella che puoi provare stasera senza chiedere il permesso a nessuno.

## Da dove cominciare

Tre cose, per due settimane, e nient'altro. Sono scelte perché non richiedono di sapere la tua costituzione e perché reggono a una vita normale.

**Sposta il pasto principale a mezzogiorno.** È la più difficile in Italia, dove la cena è il momento in cui si sta insieme, e vale la pena affrontarla con realismo: se cinque giorni su sette sono impossibili, comincia dai giorni in cui pranzi a casa o puoi permetterti un pranzo vero. La sera, in quei giorni, mangia leggero e almeno tre ore prima di coricarti.

**Mangia seduto, senza telefono e senza schermo**, a tutti i pasti. È la più semplice da capire e la più difficile da mantenere, perché il gesto di sbloccare il telefono mentre si mastica è automatico. Il trucco che funziona è fisico: lascia il telefono in un'altra stanza prima di sederti, non accanto al piatto girato a faccia in giù.

**Bevi un bicchiere di acqua calda appena sveglio**, e acqua tiepida invece che fredda durante i pasti. Costa niente ed è l'unica delle tre che non richiede di rinunciare a nulla.

Dopo due settimane guarda tre segnali, che sono anche quelli che l'ayurveda usa e che si osservano senza strumenti: **come dormi, com'è la lingua al mattino, e quanto sei assonnato dopo pranzo**. Se non è cambiato niente, l'hai scoperto in due settimane invece che in sei mesi.

E se stai costruendo un'abitudine nuova, il [kit delle pratiche quotidiane]({KIT}) è il posto in cui infilarla.

## Domande frequenti

**Devo conoscere la mia costituzione per cominciare?**
No, ed è la ragione per cui le indicazioni su come mangiare vengono prima in questa guida: valgono per tutti e cambiano di più.

**L'alimentazione ayurvedica è vegetariana?**
Non necessariamente. I testi classici includono la carne per alcune costituzioni e condizioni; la versione diffusa in Occidente è prevalentemente vegetariana per ragioni culturali più che dottrinali.

**Fa dimagrire?**
Non è il suo scopo. Le abitudini che propone hanno spesso quell'effetto come conseguenza.

**Posso seguirla se ho una patologia o sono in terapia?**
Le indicazioni comportamentali sì. Per qualsiasi cambiamento importante della dieta, e per qualsiasi preparato da ingerire, parlane con chi ti segue.

**Servono ingredienti particolari?**
No. Ghee e alcune spezie si trovano ovunque, e il grosso si fa con quello che hai già in cucina. Un'alimentazione ayurvedica che richiede una spesa in un negozio specializzato è stata venduta male.

**Le combinazioni vietate sono vere?**
Non hanno riscontro scientifico e vanno prese come tradizione. Il principio che le sottende — pasti semplici si digeriscono meglio — è verificabile sulla propria pelle.

**Quanto ci vuole per notare qualcosa?**
Sul sonno e sulla pesantezza dopo i pasti, in genere una o due settimane. Sul resto, mesi: è un sistema che ragiona per abitudini, non per risultati rapidi.
"""

PEZZI_TESTA = [
    (TEMA, TITOLO_TE, DESCR_TE, CONTENUTO_TE),
    (CIBO, TITOLO_CI, DESCR_CI, CONTENUTO_CI),
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

    for slug, titolo, descr, contenuto in PEZZI_TESTA:
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
