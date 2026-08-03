"""NA9 — un secondo pezzo per le tre categorie che ne avevano uno.

Femminile, detox e cammini avevano un articolo ciascuna. Una stanza con
un oggetto solo si visita una volta e non ci si torna.

I TRE PEZZI, scelti perche' sono quelli che le persone cercano e che
mancavano, non per riempire.

IL CICLO MESTRUALE. Nei cerchi si usa la metafora delle quattro
stagioni, ed e' una mappa utile che pero' viene presentata come legge
naturale. La variabilita' fra donne e fra cicli e' enorme, e la
ricerca sugli effetti della fase su umore e prestazioni e' molto piu'
incerta di come viene raccontata. Ma soprattutto: questo e' il pezzo
in cui va detto che UN DOLORE CHE TI FERMA NON E' NORMALE. In Italia
la diagnosi di endometriosi arriva mediamente dopo anni di sintomi, e
una parte di quel ritardo passa dal fatto che alle donne viene detto
di sopportare. Un articolo sul femminile che non lo dice e' complice.

ALCOL, ZUCCHERO E CAFFEINA. La domanda vera dietro "detox" e' cosa
succede quando smetti. Con un avvertimento di sicurezza che nel mondo
benessere non si legge mai: chi beve molto NON deve smettere di colpo
senza un medico, perche' l'astinenza da alcol e' l'unica di questa
lista che puo' essere pericolosa per la vita.

I CAMMINI ITALIANI. Il primo pezzo raccontava come si cammina; questo
dice dove, con chilometri, giorni e difficolta'. E' la domanda pratica
che segue naturalmente.

    venv/bin/python scripts/na9_tre_stanze_da_uno.py [--dry-run]
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone

CERCHI = "/blog/cerchi-di-donne-cosa-sono-come-funzionano"
DIGIUNO = "/blog/digiuno-consapevole-detox-benefici-falsi-miti"
CAMMINARE = "/blog/camminare-bagni-di-foresta-cammini"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
CIBO = "/blog/alimentazione-ayurvedica-principi-sei-sapori"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"

SLUG_C = "ciclo-mestruale-quattro-fasi-come-ascoltarlo"
TITOLO_C = "Il ciclo mestruale come mappa: le quattro fasi, cosa cambia"
DESCR_C = (
    "Cosa succede davvero nelle quattro fasi, come si tiene un diario, "
    "cosa dice la ricerca e quando un dolore va portato da un medico."
)

CONTENUTO_C = f"""\
Nei [cerchi di donne]({CERCHI}) e nei percorsi sul femminile il ciclo viene raccontato come una mappa: quattro fasi, quattro stagioni, quattro modi di stare al mondo che si ripetono ogni mese.

È una mappa utile, e come tutte le mappe non è il territorio. Questa guida racconta cosa succede in ciascuna fase, cosa di quel racconto regge alla prova dei dati, come si costruisce una mappa propria — che è l'unica che conta — e a che punto un sintomo smette di essere una cosa da attraversare e diventa una cosa da far vedere.

## Le quattro fasi

Su un ciclo di ventotto giorni, che è una media e non una regola: la durata normale va dai ventuno ai trentacinque giorni.

**La fase mestruale, dal primo giorno.** Estrogeni e progesterone sono al minimo. Molte donne riferiscono stanchezza, bisogno di stare ferme, minore tolleranza per il rumore e per le richieste. Nel linguaggio dei cerchi è l'inverno.

**La fase follicolare, dopo il flusso.** Gli estrogeni risalgono. È la fase in cui più spesso si riporta energia in crescita, voglia di cominciare cose, mente più sgombra. La primavera.

**L'ovulazione, verso metà ciclo.** Picco di estrogeni e ormone luteinizzante, l'ovulo viene rilasciato. Molte riferiscono più socialità, più sicurezza, più desiderio. Alcune sentono un dolore breve da un lato, che ha un nome proprio ed è comune. L'estate.

**La fase luteale, dall'ovulazione al flusso.** Sale il progesterone, poi crolla se non c'è gravidanza. È la fase più variabile: c'è chi la descrive come raccoglimento e lucidità critica, chi come irritabilità e gonfiore. L'autunno.

## Cosa regge e cosa no

Vale la pena separare, perché su questo tema circola molto materiale presentato come scientifico.

**Regge che gli ormoni cambiano in modo ciclico e prevedibile**, e che influenzano temperatura corporea, sonno, appetito e ritenzione di liquidi. Questo è fisiologia.

**Regge che la sindrome premestruale esiste**: sintomi fisici ed emotivi nella fase luteale sono riportati dalla maggioranza delle donne, e una minoranza sperimenta una forma severa, il disturbo disforico premestruale, che è una diagnosi clinica e si tratta.

**È molto più incerto di come viene raccontato** l'effetto della fase su umore, prestazioni cognitive e capacità atletiche. Gli studi esistono e i risultati sono contraddittori: la variabilità fra donne è più grande della variabilità fra fasi. Tradotto: i tuoi mesi si somigliano più di quanto il tuo mese somigli a quello di un'altra.

**Non regge la sincronizzazione dei cicli** fra donne che vivono insieme. È una delle idee più diffuse in assoluto, nasce da uno studio degli anni Settanta, e le verifiche successive su campioni più ampi non l'hanno confermata: quello che sembra sincronia è in gran parte l'effetto di cicli di durata diversa che ogni tanto si incrociano.

**Non regge, o quasi**, il *cycle syncing*: i protocolli che prescrivono allenamenti e alimentazione specifici per ogni fase. L'idea è sensata, le prove che serva seguirla alla lettera sono scarse. Come principio generale — allenarsi quando si ha energia, riposare quando serve — è ragionevole e non ha bisogno di un protocollo a pagamento.

## Costruisci la tua mappa

È la parte utile, e richiede tre mesi e due minuti al giorno.

**Segna il primo giorno del flusso.** È il giorno uno del ciclo.

**Ogni sera annota tre cose**, con un numero da uno a cinque: energia, umore, sonno. Più una parola sul corpo, se c'è qualcosa da dire.

**Non guardare i dati per tre mesi.** Guardarli subito porta a cercare conferme.

**Al terzo mese, allinea i tre cicli** e guarda dove i numeri si somigliano. Quelli sono i tuoi schemi, e non è detto che coincidano con le quattro stagioni del racconto.

Molte donne scoprono che la loro fase difficile non è quella che si aspettavano, o che dura tre giorni e non due settimane. È un'informazione che cambia come si organizza un mese.

Bastano un quaderno o una nota sul telefono. Le app dedicate funzionano, con un'avvertenza: stai affidando dati sanitari a un'azienda, e vale la pena leggere cosa ne fa.

## Cosa farne, in pratica

Senza protocolli, tre applicazioni che le donne che tengono un diario finiscono per fare da sole.

**Metti le cose difficili dove hai energia.** Se sai che i giorni otto-quattordici sono i tuoi, è lì che vanno la conversazione difficile, la presentazione, la decisione.

**Proteggi i due o tre giorni che sai essere pesanti.** Non azzerare la vita: togliere un impegno rinviabile basta quasi sempre.

**Muoviti comunque.** L'idea che durante il flusso si debba stare ferme è una generalizzazione: molte donne stanno meglio muovendosi, e il movimento leggero è fra le poche cose con un effetto documentato sul dolore mestruale. Una pratica di [yoga]({YOGA}) dolce o una camminata valgono più del divano, se il corpo te lo permette.

**Dormi di più nella fase luteale**, se puoi. È la richiesta più frequente che il corpo fa in quei giorni e la più semplice da concedere.

## Quando non è una fase da attraversare

Questa sezione è la ragione per cui vale la pena scrivere questo articolo.

Nel mondo del benessere il dolore mestruale viene spesso raccontato come qualcosa da accogliere, ascoltare, attraversare. Per un fastidio gestibile va benissimo. Ma esiste una soglia, e va detta chiaramente.

**Un dolore che ti impedisce di lavorare, studiare o alzarti non è normale.** Non è una questione di soglia personale né di rapporto con la femminilità: è un sintomo, e va portato da un medico.

Vale la pena saperlo perché il ritardo diagnostico su condizioni come l'**endometriosi** si misura in anni, e una parte di quel ritardo passa proprio dal fatto che a molte donne viene detto — da chiunque, in famiglia, a scuola, a volte in ambito sanitario — che il dolore fa parte del pacchetto.

Le cose che meritano una visita e non una pratica:

- Dolore che non passa con i comuni antidolorifici o che ti costringe a letto
- Flusso molto abbondante, o che dura più di sette giorni
- Cicli più corti di ventuno giorni o più lunghi di trentacinque, se non è la tua normalità
- Sanguinamento fra un ciclo e l'altro
- Dolore durante i rapporti o nell'evacuazione
- Assenza del ciclo per più di tre mesi senza gravidanza
- Un cambiamento netto rispetto a com'è sempre stato per te

Nessuna pratica olistica sostituisce quella visita, e chi lo lascia intendere ha oltrepassato [un confine noto]({SERIO}). Un cerchio, una pratica di respiro o un percorso corporeo possono accompagnare benissimo una cura: al posto, mai.

## Domande frequenti

**Le quattro fasi valgono per tutte?**
Come schema generale sì, nella loro fisiologia. Come descrizione di come ti senti, no: la variabilità individuale è molto grande, ed è il motivo per cui il diario vale più di qualsiasi schema.

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

SLUG_A = "smettere-alcol-zucchero-caffeina-cosa-succede"
TITOLO_A = "Alcol, zucchero e caffeina: cosa succede quando smetti"
DESCR_A = (
    "Giorno per giorno, cosa cambia davvero quando togli i tre stimolanti "
    "più comuni, cosa non cambia e l'avvertenza che riguarda l'alcol."
)

CONTENUTO_A = f"""\
Dietro quasi ogni proposito di «detox» c'è una domanda molto più concreta: cosa succede se per un po' tolgo il caffè, l'alcol, lo zucchero.

La risposta è documentata, è meno spettacolare di come viene raccontata, ed è più interessante. Con un avvertimento in mezzo che nel mondo del benessere non si legge quasi mai, e che riguarda la sicurezza.

Prima di tutto, la premessa che vale per tutti e tre: **non stai eliminando tossine**. Fegato e reni fanno quel lavoro comunque. Stai togliendo tre sostanze che agiscono sul sistema nervoso, e quello che senti è il sistema nervoso che si riassesta. Ne abbiamo scritto anche [a proposito di digiuno e detox]({DIGIUNO}).

## La caffeina

È la sostanza psicoattiva più consumata al mondo e l'unica delle tre per cui la sospensione ha una descrizione clinica precisa.

**Cosa fa mentre la prendi.** Blocca i recettori dell'adenosina, la molecola che accumulandosi durante la giornata segnala al cervello che è ora di dormire. Non ti dà energia: ti nasconde la stanchezza. Il corpo compensa producendo più recettori, ed è per questo che la dose efficace sale nel tempo.

**Quando smetti.**
- *Dopo 12-24 ore:* comincia il mal di testa, il più comune dei sintomi.
- *Dopo 20-48 ore:* il picco. Mal di testa, stanchezza, irritabilità, difficoltà di concentrazione, a volte nausea. È una sindrome descritta in letteratura, non una purificazione.
- *Dopo 2-9 giorni:* rientra, in modo abbastanza prevedibile.
- *Dopo 2-3 settimane:* i recettori si riassestano. È il punto in cui molte persone riferiscono un'energia più piatta ma più costante, e un sonno che si approfondisce.

**Come renderlo sopportabile.** Scala invece di tagliare: meno venticinque per cento ogni tre o quattro giorni. Il mal di testa quasi sparisce.

**Cosa non succede.** Non dormirai improvvisamente come un bambino se il problema del tuo sonno è un altro, e non perderai peso.

## L'alcol

Qui viene l'avvertimento, e va prima di tutto il resto.

**Chi beve molto e da tempo non deve smettere di colpo senza un medico.** L'astinenza da alcol è l'unica di questa pagina che può essere pericolosa per la vita: nelle forme gravi comporta tremori, confusione, crisi convulsive e delirium tremens, ed è un'emergenza medica. Se bevi ogni giorno, se hai già avuto tremori al mattino, o se bevi per far passare i sintomi del giorno prima, la sospensione va fatta assistita. Non è un consiglio prudenziale: è la cosa più importante di questo articolo.

Per un consumo moderato e occasionale, invece, il quadro è questo.

**Dopo 3-7 giorni.** Il sonno cambia per primo, ed è l'effetto più consistente. L'alcol accorcia il tempo per addormentarsi e peggiora la seconda metà della notte, comprimendo il sonno REM: togliendolo, molte persone riferiscono sogni più vividi e risvegli meno frammentati.

**Dopo 2-4 settimane.** Idratazione, aspetto della pelle, digestione. Molti riportano meno gonfiore e umore più stabile, perché l'alcol è un depressivo del sistema nervoso centrale e il rimbalzo ansioso del giorno dopo sparisce.

**Dopo 4-6 settimane.** Gli indicatori epatici migliorano nelle persone che bevevano regolarmente: è uno dei pochi effetti misurabili su cui esistono dati solidi.

**Il pezzo che nessuno racconta.** La parte più difficile non è fisica, è sociale. Le cene, i brindisi, la domanda «come mai non bevi?». Avere una risposta breve pronta — «questo mese no» — risolve il novanta per cento delle situazioni.

## Lo zucchero

Il più raccontato e il meno drammatico.

**L'astinenza da zucchero come sindrome definita non esiste** nella letteratura clinica come esiste quella da caffeina. Quello che molte persone sperimentano nei primi giorni — irritabilità, voglia intensa, calo di energia — è reale e si spiega con l'abitudine, con la caduta della gratificazione e con l'assestamento della glicemia, non con una disintossicazione.

**Cosa cambia.**
- *Prima settimana:* la voglia è forte, soprattutto nei momenti in cui c'era un rituale — il dolce dopo pranzo, il biscotto delle sedici.
- *Dopo 2-3 settimane:* **il palato si ricalibra**. È l'effetto più riferito e il più piacevole: la frutta torna a sembrare dolce, e le cose che prima erano normali diventano stucchevoli.
- *Dopo un mese:* energia più stabile durante il giorno, senza i cali di metà pomeriggio.

**Cosa non succede.** Non ti disintossichi, e togliere lo zucchero non fa dimagrire di per sé se le calorie restano quelle. E lo zucchero della frutta intera non è il problema di cui si parla.

## Cosa aspettarsi se li togli tutti e tre

È quello che succede in un ritiro detox, ed è il motivo per cui i primi due giorni sono i più duri.

**Giorni 1-2.** Mal di testa da caffeina, voglia di zucchero, irritabilità. È il momento in cui quasi tutti pensano che sia stata una pessima idea.

**Giorni 3-5.** Il sonno migliora per primo. Molte persone lo notano come il cambiamento più netto di tutta l'esperienza.

**Giorni 6-14.** Il palato si ricalibra e l'energia diventa più piatta ma più costante. Sparisce il ciclo su e giù della giornata.

**Dopo.** Il vantaggio che dura non è aver tolto, è aver **scoperto quanto di quello che prendevi era abitudine**. La maggior parte delle persone reintroduce, in quantità minori, e questo è un buon risultato.

## Come si fa senza soffrire

**Uno alla volta**, se puoi. Tre insieme è un ritiro; nella vita quotidiana, uno alla volta funziona meglio.

**Scala la caffeina**, non tagliarla.

**Sostituisci il rituale, non solo la sostanza.** Il caffè delle undici non è caffeina, è una pausa. Se la pausa resta, la sostanza manca meno.

**Scegli due settimane senza eventi**, non dicembre.

**Dì a qualcuno cosa stai facendo.** È il singolo accorgimento che alza di più le probabilità di arrivare in fondo.

**Bevi acqua e mangia regolarmente.** Metà dei sintomi dei primi giorni si attenua così. Sui principi di come si mangia più che di cosa, [l'impianto ayurvedico]({CIBO}) dice cose sensate e verificabili.

E se stai costruendo un'abitudine nuova, il [kit delle pratiche quotidiane]({KIT}) è il posto in cui infilarla.

## Domande frequenti

**Quanto dura il mal di testa da caffeina?**
Comincia dopo dodici o ventiquattro ore, ha il picco fra le venti e le quarantotto, e rientra in genere entro nove giorni. Scalare gradualmente lo riduce quasi del tutto.

**Posso smettere di bere alcol da solo?**
Se il consumo è moderato e occasionale sì. Se bevi ogni giorno o hai tremori al mattino, la sospensione va fatta con un medico: l'astinenza da alcol grave è un'emergenza.

**Esiste la dipendenza da zucchero?**
Il dibattito scientifico è aperto e il consenso attuale è che non si configura come una dipendenza da sostanza. L'abitudine e la gratificazione sono reali, e bastano a spiegare la fatica dei primi giorni.

**Quanto ci vuole perché migliori il sonno?**
Togliendo l'alcol, in genere tre-sette giorni. Togliendo la caffeina, due-tre settimane, perché il riassestamento è più lento.

**Devo togliere per sempre?**
Quasi nessuno lo fa e non è il punto. Il valore sta nel capire quanto di quello che prendevi era scelta e quanto era automatismo.

**Serve un ritiro per farlo?**
No, si fa a casa. Un ritiro toglie le occasioni e aggiunge un contesto, che per alcune persone è la differenza fra provarci e riuscirci — e le [domande da fare prima di prenotarne uno]({DOMANDE}) restano quelle di sempre.

**Posso farlo se prendo farmaci?**
Parlane con il medico. Alcuni farmaci interagiscono con la caffeina, e la sospensione dell'alcol in chi assume certe terapie va sempre valutata.
"""

SLUG_I = "cammini-italiani-quale-scegliere-la-prima-volta"
TITOLO_I = "I cammini italiani: quale scegliere la prima volta"
DESCR_I = (
    "Sei cammini con chilometri, giorni e difficoltà reali, quanto costa, "
    "come funziona la credenziale e come si prepara la prima partenza."
)

CONTENUTO_I = f"""\
Deciso che vuoi camminare per qualche giorno, arriva la domanda pratica: dove.

L'Italia ha decine di cammini e le informazioni sono sparse fra siti di associazioni, guide cartacee e gruppi di camminatori. Questa guida mette in fila i principali con i numeri veri — chilometri, giorni, difficoltà — più quello che serve sapere prima di partire la prima volta.

Su come si cammina quando camminare è una pratica, e non un modo di spostarsi, abbiamo scritto [qui]({CAMMINARE}).

## I sei da cui si comincia

**La Via degli Dei.** Bologna–Firenze, circa 130 chilometri, cinque o sei tappe. Attraversa l'Appennino su strade romane e crinali. È il più consigliato per una prima volta: dura meno di una settimana, è ben segnato, ha alloggi lungo tutto il percorso, e si raggiunge in treno da entrambe le estremità. Impegno medio, con dislivelli veri.

**Il Cammino di San Benedetto.** Da Norcia a Montecassino, circa 300 chilometri in una quindicina di tappe. Attraversa il Lazio interno e l'Umbria fra abbazie e paesi piccoli. Meno affollato dei più noti, con un carattere silenzioso.

**Il Cammino di San Francesco.** Fra la Verna, Assisi e Roma, percorribile a tratti. La sezione più battuta è quella verso Assisi, e per molti è il primo cammino italiano proprio per il valore del punto di arrivo. Ben servito di alloggi.

**La Via Francigena.** Il grande itinerario europeo, che nel tratto italiano va dal Gran San Bernardo a Roma per oltre mille chilometri, e prosegue a sud verso la Puglia. Non si fa tutta la prima volta: si sceglie una sezione. La più frequentata è quella toscana, da Lucca a Siena, splendida e affollata in primavera.

**Il Cammino Materano.** Una rete di percorsi che convergono su Matera, fra Puglia e Basilicata, con tappe fra i 15 e i 25 chilometri. Paesaggio di gravine e masserie, e la particolarità di arrivare in una città che si vede da lontano.

**Il Sentiero Italia del CAI.** Non un cammino ma la spina dorsale escursionistica del paese, migliaia di chilometri dalle Alpi alla Sicilia, percorsa a tappe da chi ha esperienza di montagna. È un'altra categoria di impegno.

E vale la pena sapere che quasi ogni regione ha i suoi cammini minori, spesso meno affollati e altrettanto belli.

## Come si sceglie

**Il tempo che hai.** Cinque giorni portano alla Via degli Dei o a una sezione della Francigena. Due settimane aprono San Benedetto o un cammino intero.

**Il dislivello, non i chilometri.** Venti chilometri in pianura e venti in Appennino sono due giornate diverse. Guarda il profilo altimetrico prima di scegliere.

**La stagione.** Aprile-giugno e settembre-ottobre sono i mesi giusti quasi ovunque. Luglio e agosto sono duri al centro-sud e affollati in Toscana. L'inverno è per chi sa quello che fa.

**Quanto vuoi stare solo.** La Francigena toscana in maggio è animata; San Benedetto in ottobre può regalarti giornate intere senza incontrare nessuno. Entrambe le cose sono legittime, e conviene sapere cosa stai cercando.

**Come ci si arriva.** Un cammino che comincia e finisce vicino a una stazione ti risparmia due giorni di logistica.

## Quanto costa

Meno di quanto si pensi, ed è una delle ragioni per cui si torna.

**Il posto letto** in ostello, foresteria o alloggio per camminatori va in genere dai 15 ai 35 euro. Alcune strutture religiose lavorano su offerta libera.

**Mangiare** costa quello che costa: colazione al bar, pranzo al sacco comprato in paese, cena in trattoria. Fra i 20 e i 35 euro al giorno.

**In totale**, dai 40 ai 70 euro al giorno tutto compreso, meno se ti organizzi con i pasti.

**Cosa costa davvero** sono le scarpe, se non le hai, e i giorni di ferie.

## La credenziale

È il documento del camminatore: un cartoncino che si fa timbrare lungo il percorso, in alloggi, chiese, bar, uffici turistici.

Serve a due cose. Dà **accesso agli alloggi riservati ai camminatori**, spesso più economici, e certifica il percorso per chi vuole l'attestato all'arrivo.

Si richiede alle associazioni che curano il cammino, in genere online, con qualche settimana di anticipo e per pochi euro. Su alcuni cammini si trova anche al punto di partenza.

Alla fine resta la cosa che si conserva: un cartoncino pieno di timbri diversi, ognuno di un posto in cui hai dormito.

## Come si prepara la prima volta

**Cammina prima.** Tre o quattro uscite da quindici chilometri nel mese precedente, con lo zaino che porterai. È l'unico allenamento che conta.

**Le scarpe già usate**, mai nuove. Almeno cento chilometri sotto le suole prima di partire.

**Lo zaino sotto il dieci per cento del tuo peso.** È la regola che salva ginocchia e spalle, e quella che quasi tutti scoprono al terzo giorno. Sessanta chili di persona significano sei chili di zaino, acqua compresa.

**Cosa mettere dentro:** due cambi e non di più, un guscio antipioggia, un pile, ciabatte per la sera, un sacco lenzuolo, un kit minimo per le vesciche, una borraccia da almeno un litro e mezzo, i documenti e la credenziale.

**Cosa lasciare a casa:** il terzo paio di pantaloni, l'asciugamano grande, i libri, e quasi tutto quello che stai considerando adesso.

**Prenota le prime due notti** e lascia libere le altre. Il ritmo vero lo scopri camminando, e quasi tutti lo scoprono più lento di come lo avevano previsto.

**Parti presto.** Le sei o le sette del mattino cambiano una giornata d'estate: si cammina al fresco, si arriva per pranzo, il pomeriggio è tuo.

## Le vesciche, perché è il vero motivo per cui si smette

Detta senza retorica: la ragione più comune per cui un cammino finisce prima non è la stanchezza, sono i piedi.

**Calze tecniche, non di cotone.** Il cotone trattiene l'umidità, e l'umidità fa le vesciche.

**Cambia le calze a metà giornata**, anche solo per dieci minuti a piedi scoperti.

**Al primo punto che scalda, fermati subito** e metti un cerotto specifico. Non a fine tappa: adesso. Cinque minuti risparmiano tre giorni.

**Se una vescica si apre**, disinfetta e copri. Se si infiamma, non è più una questione di cammino.

## In gruppo o da soli

**Da soli** si sta con sé, si decide il ritmo, si incontrano più persone di quanto si pensi — sui cammini frequentati ci si ritrova la sera negli stessi alloggi.

**In gruppo organizzato** ti tolgono la logistica: trasporto bagagli, alloggi prenotati, a volte una guida. È la formula giusta se il pensiero dell'organizzazione ti blocca. Se lo stai valutando, le [domande da fare prima di prenotare]({DOMANDE}) valgono anche qui, con una in più: chi porta gli zaini e cosa succede se un giorno non riesci a camminare.

**In due** è la formula più difficile, e vale la pena saperlo: ritmi diversi che si incontrano per otto ore al giorno mettono alla prova qualsiasi rapporto. Accordarsi prima sul diritto di camminare separati e ritrovarsi la sera risolve quasi tutto.

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
Molti cammini nascono da percorsi di pellegrinaggio e attraversano luoghi religiosi, ma si percorrono per qualsiasi ragione e nessuno chiede la tua. Sui cammini si incontrano credenti, curiosi e persone che volevano solo camminare.
"""

PEZZI = [
    (SLUG_C, TITOLO_C, DESCR_C, CONTENUTO_C, "femminile",
     [CERCHI.split("/blog/")[1], YOGA.split("/blog/")[1],
      SERIO.split("/blog/")[1]]),
    (SLUG_A, TITOLO_A, DESCR_A, CONTENUTO_A, "detox",
     [DIGIUNO.split("/blog/")[1], CIBO.split("/blog/")[1],
      KIT.split("/blog/")[1]]),
    (SLUG_I, TITOLO_I, DESCR_I, CONTENUTO_I, "cammini",
     [CAMMINARE.split("/blog/")[1], DOMANDE.split("/blog/")[1],
      MEDIT.split("/blog/")[1]]),
]

AGGIUNTE = [
    ("cerchi-di-donne-cosa-sono-come-funzionano", "## Domande frequenti",
     f"Il tema che nei cerchi torna piu' spesso di ogni altro e' il ciclo, e "
     f"la mappa delle quattro fasi: cosa regge e cosa no lo abbiamo scritto "
     f"[qui](/blog/{SLUG_C}).\n\n## Domande frequenti"),
    ("digiuno-consapevole-detox-benefici-falsi-miti", "## Domande frequenti",
     f"La domanda concreta dietro quasi ogni proposito di detox e' cosa "
     f"succede quando togli caffe', alcol e zucchero: [giorno per giorno]"
     f"(/blog/{SLUG_A}), con l'avvertenza che riguarda l'alcol.\n\n"
     f"## Domande frequenti"),
    ("camminare-bagni-di-foresta-cammini", "## Domande frequenti",
     f"E se la domanda diventa dove, i [cammini italiani principali]"
     f"(/blog/{SLUG_I}) sono in fila con chilometri, giorni e difficolta' "
     f"veri.\n\n## Domande frequenti"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto, categoria, correlati in PEZZI:
        print(f"{titolo}\n  {categoria} | {len(contenuto.split())} parole | "
              f"descrizione {len(descr)} caratteri")
        esistente = await db.articles.find_one({"slug": slug}, {"_id": 0, "id": 1})
        print("  stato:", "aggiornato" if esistente else "nuovo")
        if dry_run:
            continue
        now = datetime.now(timezone.utc)
        campi = {"title": titolo, "description": descr, "content": contenuto,
                 "category": categoria, "author_name": "Aurya",
                 "published": True, "updated_at": now, "translations": {},
                 "related_slugs": correlati}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": slug,
                      "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": slug}, {"$set": campi},
                                     upsert=True)
        doc = await db.articles.find_one({"slug": slug},
                                         {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(slug, categoria)
            if url:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "featured_image_url": url}})
                print(f"  copertina: {url}")

    if not dry_run:
        for slug, vecchio, nuovo in AGGIUNTE:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0,
                                                            "content": 1})
            if not d:
                print(f"  ASSENTE {slug}")
            elif nuovo.split("\n\n")[0] in d["content"]:
                print(f"  link gia' presente in {slug[:42]}")
            elif vecchio in d["content"]:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1)}})
                print(f"  link aggiunto in {slug[:42]}")
            else:
                print(f"  NON TROVATO in {slug[:42]}")

    print("\n── controlli")
    from collections import defaultdict
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1, "category": 1,
                                                   "description": 1,
                                                   "featured_image_url": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    orfani = [a["slug"] for a in arts
              if not any(f"/blog/{a['slug']})" in b["content"]
                         for b in arts if b["slug"] != a["slug"])]
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  vicoli: {orfani or 'nessuno'}")
    print(f"  magri: {[(a['slug'], len(a['content'].split())) for a in arts if len(a['content'].split()) < 900] or 'nessuno'}")
    print(f"  copertine distinte: "
          f"{len({a.get('featured_image_url') for a in arts})} su {len(arts)}")
    cl = defaultdict(int)
    for a in arts:
        cl[a["category"]] += 1
    print(f"  cluster da un solo pezzo: "
          f"{[c for c, n in cl.items() if n == 1] or 'nessuno'}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
