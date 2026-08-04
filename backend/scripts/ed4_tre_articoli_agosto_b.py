# -*- coding: utf-8 -*-
"""ED4 — seconda tripletta del calendario di agosto.

I TRE PEZZI. Dalla coda del piano espansione (confini-sanitari resta
in attesa della revisione founder):

1. «Aromaterapia» (naturopatia) — secondo pezzo della categoria nuova,
   volume alto, SERP piene di siti che vendono oli. Fonte primaria
   VERIFICATA in questa sessione: Donelli et al., Phytomedicine 2019,
   doi 10.1016/j.phymed.2019.153099 (revisione sistematica lavanda e
   ansia: orale efficace in preparazioni standardizzate, inalazione
   solo indicazione di effetto per eterogeneita' degli studi).
2. «Respiro e sistema nervoso» (breathwork) — anello 2/3: il pezzo
   fisiologico che aggancia breathwork, pranayama, kit e stress.
   Fonte: Balban 2023 (doi gia' in whitelist dal kit, ED2).
3. «La bio professionale» (operatori) — B2B, lead operatori: speculare
   alle guide consumer (le persone arrivano armate delle NOSTRE
   domande; la bio che risponde prima vince).

Nessun numero nuovo: ventimila respiri/giorno, sei respiri/minuto,
fisiologia CO2 e cyclic sighing ripresi da breathwork/pranayama/kit.

Idempotente; da rieseguire in prod al lancio.

    venv/bin/python scripts/ed4_tre_articoli_agosto_b.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

ART_AROMA = {
    "slug": "aromaterapia-cose-come-si-usa-ricerca",
    "titolo": "Aromaterapia: cos'è, come si usa e cosa dice la ricerca",
    "descrizione": ("Gli oli essenziali senza marketing: come si usano "
                    "davvero, cosa regge alla prova degli studi e le "
                    "regole di sicurezza che nessuno racconta."),
    "categoria": "naturopatia",
    "related": ["naturopatia-cose-consulto-cosa-dice-ricerca",
                "massaggio-olistico-tipi-cosa-aspettarsi",
                "pratiche-olistiche-contro-stress-cosa-funziona"],
    "contenuto": """Quasi sempre comincia con un regalo: un diffusore, tre boccette, un biglietto che dice «per rilassarti». Il diffusore finisce su una mensola, le boccette accanto, e lì si ferma tutto — perché nessuno ti ha detto cosa farci davvero, e le istruzioni sembrano scritte per chi già sa.

Questa guida fa quel lavoro: cosa sono gli oli essenziali, come si usano, cosa regge alla prova degli studi e — la parte che il marketing salta sempre — le regole di sicurezza. Perché in queste boccette c'è una quantità di pianta sorprendente, e «naturale» non ha mai significato «innocuo».

## Cos'è, e cosa non è

L'aromaterapia è l'uso degli oli essenziali — sostanze aromatiche concentrate estratte dalle piante, in genere per distillazione o per spremitura delle scorze — a scopo di benessere: attraverso l'olfatto, o attraverso la pelle in forma diluita.

Due cose vanno dette subito. La prima: un olio essenziale è un concentrato potente, non un'acqua profumata — per riempire una boccetta servono quantità di pianta che sorprendono chiunque le veda la prima volta, ed è il motivo per cui le regole di diluizione non sono pignolerie. La seconda: l'aromaterapia è una pratica di benessere, non una terapia. In Italia rientra nel mondo delle discipline non sanitarie, spesso dentro un consulto di [naturopatia](/blog/naturopatia-cose-consulto-cosa-dice-ricerca) o un [massaggio](/blog/massaggio-olistico-tipi-cosa-aspettarsi): nessun olio cura una malattia, e chi lo promette sta superando un confine preciso.

## Da dove passa l'effetto

L'olfatto è un senso anomalo: è l'unico collegato in modo diretto alle aree del cervello che gestiscono memoria ed emozione. È l'esperienza che tutti conoscono — un odore che riporta in un istante a una cucina di vent'anni fa — ed è la strada principale da cui passa l'effetto rilassante di un profumo: rapida, potente e personale, perché costruita sulla storia di ciascuno.

Poi c'è la via della pelle, dove le molecole vengono in parte assorbite: è quella su cui lavora il massaggio aromatico. E c'è una conseguenza onesta da trarre: se l'effetto passa in gran parte dall'esperienza dell'odore, una parte di quello che senti è legata al contesto, al ricordo e all'aspettativa. Non è un difetto — è come funziona l'olfatto.

## Come si usa, in pratica

**La diffusione.** Poche gocce nel diffusore, per periodi brevi — meglio mezz'ora che una giornata intera — e in una stanza che respira. Di più non è meglio: l'olfatto si satura in fretta, e un ambiente saturo non rilassa nessuno.

**L'inalazione diretta.** Una goccia su un fazzoletto, da annusare quando serve. È il formato più semplice e il più sottovalutato: portatile, dosabile, senza apparecchi.

**Sulla pelle, sempre diluiti.** Mai puri: si diluiscono in un olio vettore — mandorle dolci, jojoba — in percentuali basse, e prima del primo uso si prova su una piccola zona per un giorno. Le eccezioni che sentirai citare non valgono la regola: la pelle si sensibilizza, e una sensibilizzazione è per sempre.

**Per bocca: no.** L'uso orale fai-da-te è il modo più diretto di farsi male con questo mondo. Ne riparliamo sotto, perché la ricerca su questo punto crea un equivoco che va sciolto.

## Cosa dice la ricerca

L'olio più studiato in assoluto è la **lavanda**, e su di lei esiste una [revisione sistematica con meta-analisi](https://doi.org/10.1016/j.phymed.2019.153099) (Donelli e colleghi, *Phytomedicine*, 2019) che è il riferimento più utile per capire lo stato delle prove. La conclusione ha due facce. Per la **via orale** — capsule standardizzate studiate in ambito clinico — l'efficacia sull'ansia risulta documentata. Per l'**inalazione**, cioè l'aromaterapia come la pratica chiunque, c'è solo un'indicazione di effetto: gli studi sono troppo eterogenei per una conclusione solida.

E qui va sciolto l'equivoco: quel risultato sulla via orale riguarda preparazioni farmaceutiche a dosaggio controllato, dentro studi clinici. **Non dice che ingerire gocce di olio essenziale a casa funzioni o sia sicuro** — non lo è. È il caso da manuale di un dato vero usato per giustificare una pratica diversa.

Sugli altri oli le prove sono più deboli: studi piccoli, risultati misti, molta distanza fra ciò che si vende e ciò che è documentato. E su tutto il campo pesa un limite strutturale che è onesto conoscere: **un profumo non si può nascondere**. In uno studio sui farmaci il gruppo di controllo non sa cosa sta prendendo; in uno studio sugli odori lo sente, e questo rende difficile separare l'effetto della molecola da quello dell'esperienza.

La sintesi ragionevole: come sostegno al rilassamento, dentro una pratica o una serata, l'aromaterapia ha senso e un'indicazione di effetto. Come trattamento di un disturbo, no.

## Naturale non significa innocuo

È la stessa frase della [guida alla naturopatia](/blog/naturopatia-cose-consulto-cosa-dice-ricerca), e qui vale il doppio, perché gli oli essenziali sono fra le sostanze più concentrate che entrano in una casa.

**Mai puri sulla pelle**, come detto: irritazioni e sensibilizzazioni sono l'incidente più frequente di questo mondo.

**Gli agrumi rendono la pelle fotosensibile.** Bergamotto e parenti, applicati prima di esporsi al sole, possono causare vere ustioni. D'estate è la regola da conoscere prima di tutte.

**Bambini piccoli, gravidanza, animali.** Sono le tre situazioni in cui il fai-da-te va sospeso e le indicazioni vanno chieste a chi ha una formazione specifica — e per la gravidanza anche a chi la segue. Gli animali domestici, i gatti in particolare, metabolizzano queste sostanze in modo diverso da noi: un diffusore acceso in continuo in una stanza da cui l'animale non può uscire non è una coccola.

**Il medico va informato**, come per erbe e integratori: alcune sostanze interagiscono con i farmaci, e «è solo un profumo» non è una valutazione, è una speranza. E la regola madre resta quella di sempre: nessuna terapia si tocca per un olio.

## Come si riconosce un olio serio

Quattro cose sull'etichetta, prima del profumo. Il **nome botanico in latino**, perché «lavanda» dice poco e *Lavandula angustifolia* dice tutto. L'**origine e il metodo di estrazione**. Il **lotto e la scadenza**, perché gli oli si ossidano. E un **prezzo coerente con la pianta**: oli diversi hanno rese diversissime, e se tutte le boccette di un marchio costano uguale, qualche domanda è legittima.

«100% naturale» e «puro», da soli, non sono garanzie: sono parole di marketing che nessun ente verifica. La trasparenza su ciò che c'è dentro vale più di qualsiasi aggettivo.

## Con chi, quando serve una guida

Per la diffusione e il fazzoletto basti tu. Il passo successivo — miscele personali, uso sulla pelle, situazioni delicate — merita una figura formata: spesso l'aromaterapia arriva dentro un consulto naturopatico o un massaggio aromatico, e valgono i criteri di sempre per [capire chi lavora bene](/blog/come-capire-se-un-operatore-olistico-e-serio). Con l'aggiunta specifica di questo campo: chi ti propone oli da bere, o un olio «per» una patologia, ti sta dando la migliore ragione per scegliere qualcun altro.

## Domande frequenti

**L'aromaterapia funziona contro l'ansia?**
Come sostegno al rilassamento c'è un'indicazione di effetto, soprattutto per la lavanda; gli studi sull'inalazione sono però eterogenei e la conclusione resta prudente. Per un disturbo d'ansia il percorso è clinico, e l'aromaterapia può al massimo accompagnarlo.

**Posso ingerire gli oli essenziali?**
No, non da soli: l'uso orale fai-da-te è pericoloso. Gli studi che documentano effetti per via orale riguardano capsule standardizzate a dosaggio controllato in ambito clinico, che sono un'altra cosa.

**Posso mettere un olio essenziale puro sulla pelle?**
No: si diluisce sempre in un olio vettore, in percentuali basse, con una prova su una piccola zona prima del primo uso. Gli oli puri irritano e possono sensibilizzare in modo permanente.

**Posso tenere il diffusore acceso tutto il giorno?**
Meglio di no: periodi brevi in ambienti ventilati. L'olfatto si satura in fretta e l'esposizione continua non aggiunge beneficio; con animali in casa la ventilazione e la possibilità di allontanarsi diventano regole, non consigli.

**Gli oli essenziali sono sicuri con bambini e animali?**
Con cautele precise che il fai-da-te non copre: per i bambini piccoli e in gravidanza servono indicazioni di chi ha formazione specifica, e i gatti in particolare metabolizzano queste sostanze in modo diverso. Nel dubbio, meno è meglio.

**Che differenza c'è fra un olio essenziale e una fragranza?**
L'olio essenziale è estratto dalla pianta; una fragranza sintetica è costruita in laboratorio per profumare e non ha alcun uso in aromaterapia. Sull'etichetta la differenza si vede dal nome botanico e dalla dicitura: se c'è scritto solo «aroma» o «profumo», è la seconda.""",
}

ART_RESPIRO = {
    "slug": "respiro-sistema-nervoso-cosa-succede",
    "titolo": "Respiro e sistema nervoso: cosa succede quando rallenti",
    "descrizione": ("Perché l'espirazione lunga calma, cosa fa il nervo "
                    "vago, il sospiro fisiologico e quale tecnica usare "
                    "in ogni momento: la fisiologia spiegata semplice."),
    "categoria": "breathwork",
    "related": ["breathwork-cose-tecniche-benefici",
                "pranayama-tecniche-respirazione-yoga",
                "kit-pratiche-quotidiane-15-minuti"],
    "contenuto": """«Respira». È il consiglio più irritante che esista, di solito pronunciato da qualcuno di calmo mentre tu non lo sei. Ed è anche, fastidiosamente, un consiglio fondato: dietro quella parola c'è un pezzo di fisiologia preciso, e conoscerlo trasforma un luogo comune in uno strumento.

Questa è la guida a quel pezzo di fisiologia. Niente tecniche nuove — [quelle](/blog/breathwork-cose-tecniche-benefici) [esistono](/blog/pranayama-tecniche-respirazione-yoga) [già](/blog/kit-pratiche-quotidiane-15-minuti) — ma il perché che le tiene insieme: cosa succede dentro, quando rallenti.

## Il sistema che non comandi, e la sua unica porta

Il sistema nervoso autonomo governa tutto quello che il corpo fa da solo: battito, digestione, pressione, sudore. Ha due rami che lavorano come acceleratore e freno. Il **simpatico** prepara all'azione — accelera il cuore, tende i muscoli, mette in circolo energia. Il **parasimpatico** fa il contrario: riposo, digestione, recupero.

Il problema della vita moderna non è avere un acceleratore: è che resta premuto. La minaccia per cui il simpatico è stato progettato arrivava e se ne andava; le email, le scadenze e i pensieri delle tre di notte restano, e il sistema resta acceso con loro.

Su niente di tutto questo hai un comando diretto — non puoi decidere di rallentare il battito — tranne che su una funzione: il respiro. Respiriamo circa ventimila volte al giorno in automatico, ma possiamo prendere il controllo in qualsiasi momento. È l'unica porta d'ingresso volontaria nel sistema autonomo, e ogni tecnica di respiro che funziona passa da lì.

## L'asimmetria che fa funzionare tutto

Il meccanismo centrale è un'asimmetria che puoi sentire adesso, con due dita sul polso: **quando inspiri il battito accelera leggermente, quando espiri rallenta**.

Non è un difetto, è il progetto. L'espirazione è il momento in cui il **nervo vago** — il grande cavo del parasimpatico, che collega il tronco encefalico a cuore e visceri — aumenta la sua attività frenante. Ogni espirazione è una piccola frenata; un'espirazione lunga è una frenata lunga.

Da questa asimmetria discende quasi tutto quello che le tradizioni hanno codificato per tentativi in millenni. Se l'espirazione frena, **allungarla sposta l'equilibrio verso il freno**: è il principio del quattro-dentro-otto-fuori, ed è il motivo per cui funziona in due o tre minuti, senza bisogno di crederci. Il corpo non sta ricevendo una suggestione: sta ricevendo un segnale meccanico di sicurezza, nel suo linguaggio.

## Perché proprio sei respiri al minuto

Fra le tecniche lente ricorre sempre lo stesso numero: circa sei respiri al minuto — cinque secondi dentro, cinque fuori, la cadenza della coerenza cardiaca. Non è un numero magico: è la frequenza a cui i sistemi che oscillano insieme al respiro — battito, pressione, attività vagale — entrano in fase, e l'effetto di ogni respiro si somma invece di disperdersi. A quella cadenza la variabilità del battito aumenta, che è esattamente il segnale di un freno che lavora bene.

Non serve cercare la precisione al secondo: serve la lentezza regolare. Cinque minuti, due o tre volte al giorno, e il sistema impara la strada.

## Il sospiro fisiologico

C'è un gesto che il corpo fa da solo — nei bambini dopo il pianto, in chiunque prima di addormentarsi — e che si può usare deliberatamente: **due inspirazioni dal naso, una lunga e una piccola in cima, e un'espirazione lenta dalla bocca**.

La seconda inspirazione riapre le zone dei polmoni che tendono a chiudersi e rende più efficiente lo scambio dei gas; l'espirazione lunga fa il resto, per la via che ormai conosci. È il pattern che uno [studio pubblicato su *Cell Reports Medicine* nel 2023](https://doi.org/10.1016/j.xcrm.2022.100895) da Balban e colleghi ha trovato più efficace — con cinque minuti al giorno — nel migliorare l'umore e abbassare la frequenza respiratoria a riposo, confrontandolo con altre tecniche di respiro e con la meditazione. Due o tre cicli bastano per l'uso al volo; [nel kit](/blog/kit-pratiche-quotidiane-15-minuti) è la prima pratica, spiegata passo per passo.

## E quando respiri troppo

La stessa leva funziona anche al contrario, ed è bene saperlo. Respirare più del necessario — volontariamente, nelle tecniche intense, o involontariamente, nell'ansia — elimina più anidride carbonica di quanta il corpo ne produca. Il sangue diventa temporaneamente più alcalino, i nervi periferici più eccitabili, i vasi cerebrali si restringono: formicolii, testa leggera, mani che si irrigidiscono.

Sono effetti meccanici e transitori, si risolvono rallentando — e sono il motivo per cui le tecniche intense [hanno regole e controindicazioni proprie](/blog/breathwork-cose-tecniche-benefici). Ma c'è anche un risvolto quotidiano: molta della sensazione fisica dell'ansia — il torace che stringe, la testa che gira — è respiro rapido e alto che si autoalimenta. Riconoscerlo mentre succede è già metà dell'uscita, perché sposta la domanda da «cosa mi sta succedendo» a «come sto respirando».

## La pratica: quale leva, quando

**Nel momento acuto** — prima di parlare in pubblico, dopo la telefonata, nell'onda d'ansia — le due leve rapide: l'espirazione doppia dell'inspirazione, o due o tre sospiri fisiologici. Agiscono in minuti perché non chiedono al sistema di calmarsi: glielo segnalano nel suo linguaggio.

**Come manutenzione quotidiana**, la lentezza regolare: coerenza cardiaca o [nadi shodhana](/blog/pranayama-tecniche-respirazione-yoga), cinque minuti al giorno. Qui l'obiettivo non è l'effetto immediato ma la taratura: un sistema che si allena a frenare, frena meglio anche quando non glielo chiedi. Le [pratiche contro lo stress](/blog/pratiche-olistiche-contro-stress-cosa-funziona) che funzionano lavorano quasi tutte su questo.

**Quando il respiro è il problema** — patologie respiratorie, attacchi di panico che partono dal respiro — la regola è cominciare accompagnati: le tecniche restano utili, ma il primo interlocutore è chi ti segue.

## Il punto

Il respiro non è una pratica olistica fra le altre: è il meccanismo che molte pratiche usano senza dirlo. L'ora di yoga, i dieci minuti seduti, il canto, perfino il sonno che arriva — passano tutti, in parte, da un'espirazione che si allunga e da un nervo che frena.

Saperlo non toglie niente all'esperienza. Aggiunge una cosa sola, e non è piccola: la leva ce l'hai sempre con te, e adesso sai dove sta.

## Domande frequenti

**Perché l'espirazione lunga calma?**
Perché durante l'espirazione il nervo vago — il principale nervo del sistema parasimpatico — aumenta la sua azione frenante su cuore e visceri. Allungare l'espirazione allunga la frenata: è un segnale meccanico, non una suggestione.

**Quanto tempo serve perché il respiro faccia effetto?**
Le tecniche lente agiscono in due o tre minuti sull'attivazione del momento. L'effetto stabile — reattività più bassa, sonno migliore — chiede pratica quotidiana per due o tre settimane, anche solo cinque minuti al giorno.

**Meglio respirare dal naso o dalla bocca?**
Nelle tecniche lente si inspira dal naso, che filtra e rallenta l'aria; l'espirazione dalla bocca socchiusa aiuta ad allungarla. È anche la struttura del sospiro fisiologico: dentro dal naso, fuori dalla bocca.

**Qual è la tecnica migliore per addormentarsi?**
Qualsiasi respirazione con l'espirazione doppia dell'inspirazione, sdraiati, per qualche minuto: è la leva più diretta sul freno del sistema. Se la testa continua a correre, il problema non è la tecnica ed è normale: la pratica serve proprio a quello.

**Il respiro può sostituire un ansiolitico o una terapia?**
No. È uno strumento di regolazione potente e documentato, e accompagna bene un percorso clinico — ma non lo sostituisce, e nessuna decisione sui farmaci si prende senza il medico.

**Perché sento formicolii se respiro velocemente?**
Perché respirando più del necessario elimini troppa anidride carbonica: il sangue diventa più alcalino e i nervi periferici più eccitabili. È temporaneo e si risolve rallentando il respiro.""",
}

ART_BIO = {
    "slug": "bio-professionale-operatore-olistico",
    "titolo": "La bio professionale che crea fiducia: guida per operatori",
    "descrizione": ("Cosa scrivere nella tua presentazione e cosa togliere: "
                    "formazione verificabile, limiti dichiarati, dicitura "
                    "di legge e la struttura che convince."),
    "categoria": "operatori",
    "related": ["legge-4-2013-professioni-olistiche",
                "come-promuovere-un-ritiro-e-riempire-i-posti",
                "come-capire-se-un-operatore-olistico-e-serio"],
    "contenuto": """Due bio, stessa disciplina, stessa città.

La prima: «Accompagno le persone in un viaggio trasformativo di riconnessione con la propria essenza attraverso un approccio olistico e integrato».

La seconda: «Insegno hatha yoga a persone che lavorano sedute otto ore al giorno. Mi sono formata in tre anni alla scuola X (500 ore, diploma 2019). Le classi sono da otto persone al massimo; la prima lezione è di prova e costa dieci euro».

Chi legge si fida della seconda, e quasi mai sa spiegare perché. Questa guida spiega il perché — e come si scrive.

## La bio è il tuo primo colloquio

C'è una cosa che è cambiata e che conviene guardare in faccia: **le persone arrivano preparate**. Prima di scriverti hanno letto guide come quella per [capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio) — l'abbiamo scritta noi, e la leggono in tanti — e arrivano con le domande in tasca: dove ti sei formato e per quanto, cosa succede in una sessione, in quali casi questa pratica non fa per me, quanto costa e come si disdice.

La bio che risponde a quelle domande **prima che vengano fatte** vince due volte: risparmia a chi legge la fatica di chiedere, e comunica la cosa più difficile da comunicare — che non hai niente da nascondere. La bio che non risponde non è neutra: per un lettore preparato, ogni risposta mancante è un piccolo segnale nella direzione sbagliata.

## Le cinque cose che deve dire

**1. Chi aiuti a fare cosa.** La prima riga, e la più difficile. Non chi sei tu: cosa cambia per chi viene da te, detto concreto. «Lavoro con persone che dormono male da mesi» seleziona e attira più di qualsiasi «benessere psicofisico a 360 gradi» — che non seleziona nessuno perché parla a tutti.

**2. La formazione, verificabile.** Scuola, durata, anno. «Formata in shiatsu» dice poco; «tre anni alla scuola X, diploma 2019» dice tutto, perché chi legge può controllare — e il fatto stesso che tu scriva in modo controllabile è il segnale. Se la tua formazione è un percorso lungo, dillo con le date: è l'asset che un fine settimana di corso non può imitare.

**3. Cosa succede, passo per passo.** La sessione tipo, in tre o quattro frasi senza gergo: quanto dura, come si svolge, cosa è normale sentire. È la sezione che abbassa la soglia d'ingresso per chi non è mai stato da nessuno — cioè esattamente le persone che stai cercando di raggiungere.

**4. Per chi non è indicato.** La riga che quasi nessuno scrive ed è la più potente di tutte, perché va contro il tuo interesse immediato — e chi legge lo sa. «Questa pratica non sostituisce un percorso medico o psicologico; in questi casi ti indirizzo a…» non ti toglie clienti: ti toglie i clienti sbagliati e conquista tutti gli altri.

**5. La cornice: dicitura, prezzi, condizioni.** La dicitura «professionista di cui alla legge n. 4 del 14 gennaio 2013» — che [la legge chiede](/blog/legge-4-2013-professioni-olistiche) in ogni comunicazione verso il pubblico, bio compresa — più prezzi, durata e regole di disdetta, scritti chiari. Ogni informazione che il lettore trova qui è un messaggio che non dovrà mandarti e un dubbio che non lavorerà contro di te.

## Le cose da togliere

**Gli aggettivi che non selezionano.** «Unico», «profondo», «trasformativo», «autentico»: parole che ogni bio usa e che quindi non distinguono nessuna. La regola pratica: se la frase può stare nella bio del tuo concorrente senza cambiare una virgola, non sta descrivendo te.

**Le liste di benefici lunghe.** Ansia, insonnia, digestione, autostima, relazioni: più la lista si allunga, meno è credibile — lo diciamo ai lettori [dall'altra parte dello specchio](/blog/come-capire-se-un-operatore-olistico-e-serio), e i lettori lo sanno. Meglio un problema descritto bene che dieci evocati.

**Le promesse di risultato.** «Ritroverai il tuo equilibrio» è una promessa che non puoi mantenere per contratto. Racconta il metodo e i tempi; i risultati raccontali con le recensioni di chi c'è stato, che sono le uniche promesse credibili perché non le fai tu.

**Il gergo di scuola.** I termini della tua formazione sono la tua lingua madre professionale, non quella di chi legge. Ogni parola che il lettore non capisce è un piccolo pedaggio; qualcuna va bene, spiegata — un muro no.

## La struttura che funziona

Nell'ordine: la riga su chi aiuti a fare cosa; la formazione con le date; la sessione raccontata; per chi non è indicato; la logistica — prezzi, durata, disdetta, dove. E una **foto vera**: tu, luce normale, sguardo in camera. Le persone non prenotano un programma, prenotano te — vale per la [pagina di un ritiro](/blog/come-promuovere-un-ritiro-e-riempire-i-posti) e vale il doppio per la bio.

La lunghezza giusta è quella che serve alle cinque cose: di solito fra le centocinquanta e le trecento parole. Sotto, manca qualcosa; sopra, di solito è entrato il superfluo.

## La prova del nove

Prima di pubblicarla, falla leggere a una persona che non ti conosce professionalmente e falle tre domande: cosa faccio, dove mi sono formato, quanto costa. Se non sa rispondere a una delle tre senza rileggere, la bio non funziona — non perché sia scritta male, ma perché sta facendo un altro mestiere: parlare di te invece che a chi legge.

E poi tienila viva: una formazione nuova, un cambio di prezzi, una specializzazione — la bio si aggiorna come si aggiorna un listino. Quella ferma al 2019, con i prezzi vecchi, racconta anche lei qualcosa.

## Il punto

La bio non è un esercizio di scrittura: è la versione scritta del tuo primo colloquio, quella che lavora mentre dormi. E le regole sono le stesse che valgono di persona — dire cosa fai, da dove vieni, cosa non fai, quanto costa — perché la fiducia si costruisce con le stesse cose, dette in qualsiasi formato.

Il vantaggio è tutto qui: la maggior parte delle bio di questo mondo è ancora fatta di essenze e viaggi trasformativi. Una bio che risponde alle domande vere si riconosce in dieci secondi. Falla, e sarai in pochi.

## Domande frequenti

**Quanto deve essere lunga una bio professionale?**
Fra le centocinquanta e le trecento parole: abbastanza per le cinque informazioni che contano (chi aiuti, formazione, come lavori, per chi non è indicato, condizioni), non abbastanza per il superfluo.

**Devo davvero scrivere per chi NON è indicata la mia pratica?**
Sì, ed è la riga più redditizia della bio: va contro il tuo interesse immediato, e proprio per questo è il segnale di serietà più credibile che puoi dare. Seleziona meglio i clienti e previene le situazioni che non vuoi.

**Devo mettere la dicitura della legge 4/2013?**
Sì: la legge chiede di indicarla in ogni comunicazione verso il pubblico, e la bio lo è. In più è un segnale che i lettori informati riconoscono: dice che sai in quale cornice lavori.

**Metto i prezzi nella bio?**
Sì, o comunque in un punto raggiungibile senza scriverti. Il prezzo nascosto non aumenta le richieste: aumenta i messaggi di chi voleva solo saperlo e gli abbandoni di chi non ha voglia di chiedere.

**Posso usare la stessa bio ovunque?**
Il contenuto sì — le cinque cose non cambiano. Cambia il taglio: sul sito c'è spazio per la versione piena, sui social serve la sintesi. L'importante è che le versioni non si contraddicano, a partire dai prezzi.

**Che foto uso?**
Una foto vera di te, recente, con luce naturale e sguardo in camera. Non un logo, non un tramonto, non una posizione spettacolare: chi legge sta decidendo se fidarsi di una persona, e vuole vederla.""",
}

ARTICOLI = [ART_AROMA, ART_RESPIRO, ART_BIO]

# backlink dalle ancore naturali dei pezzi esistenti
AGGIUNTE = [
    # la naturopatia elenca gli strumenti: l'aromaterapia e' il primo
    # approfondimento della categoria
    ("naturopatia-cose-consulto-cosa-dice-ricerca",
     "suggerisce rimedi naturali e tecniche di gestione dello stress, "
     "accompagna nel tempo.",
     "suggerisce rimedi naturali e tecniche di gestione dello stress, "
     "accompagna nel tempo. Fra gli strumenti più usati c'è "
     "l'[aromaterapia](/blog/aromaterapia-cose-come-si-usa-ricerca): "
     "come si usa e cosa dice la ricerca lo raccontiamo a parte."),
    # la mappa accoglie la stanza nuova accanto alla naturopatia
    ("discipline-olistiche-la-mappa",
     "l'approccio occidentale al riequilibrio attraverso alimentazione, "
     "stile di vita e rimedi naturali: [cosa fa un naturopata, cosa no "
     "e cosa dice la ricerca](/blog/naturopatia-cose-consulto-cosa-dice-ricerca).",
     "l'approccio occidentale al riequilibrio attraverso alimentazione, "
     "stile di vita e rimedi naturali: [cosa fa un naturopata, cosa no "
     "e cosa dice la ricerca](/blog/naturopatia-cose-consulto-cosa-dice-ricerca).\n\n"
     "**L'aromaterapia** lavora con gli oli essenziali, per diffusione "
     "o sulla pelle in forma diluita: [come si usa e cosa regge alla "
     "prova degli studi](/blog/aromaterapia-cose-come-si-usa-ricerca)."),
    # breathwork chiude la sezione fisiologica proprio sul punto
    ("breathwork-cose-tecniche-benefici",
     "È il motivo per cui sei respiri al minuto calmano: non è "
     "suggestione, è fisiologia.",
     "È il motivo per cui sei respiri al minuto calmano: non è "
     "suggestione, è fisiologia — e l'abbiamo raccontata per esteso in "
     "[respiro e sistema nervoso](/blog/respiro-sistema-nervoso-cosa-succede)."),
    # pranayama, stessa ancora fisiologica
    ("pranayama-tecniche-respirazione-yoga",
     "Il meccanismo è compreso: il respiro lento stimola il nervo vago "
     "e sposta l'equilibrio verso il sistema parasimpatico.",
     "Il meccanismo è compreso: il respiro lento stimola il nervo vago "
     "e sposta l'equilibrio verso il sistema parasimpatico — [qui il "
     "perché, per esteso](/blog/respiro-sistema-nervoso-cosa-succede)."),
    # la guida allo stress presenta la respirazione lenta: il perche'
    # fisiologico e' il pezzo nuovo
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "È anche la porta d'ingresso al [mondo del breathwork]"
     "(/blog/breathwork-cose-tecniche-benefici).",
     "È anche la porta d'ingresso al [mondo del breathwork]"
     "(/blog/breathwork-cose-tecniche-benefici), e il perché funziona "
     "— nervo vago, espirazione, sospiro fisiologico — sta in [respiro "
     "e sistema nervoso](/blog/respiro-sistema-nervoso-cosa-succede)."),
    # la guida alla promozione nomina il chi-conduce: la bio e' il come
    ("come-promuovere-un-ritiro-e-riempire-i-posti",
     "Deve vedere **chi conduce**, con volto e storia, perché le "
     "persone non prenotano un programma: prenotano te.",
     "Deve vedere **chi conduce**, con volto e storia, perché le "
     "persone non prenotano un programma: prenotano te — e come si "
     "scrive quella presentazione è il tema della [guida alla bio "
     "professionale](/blog/bio-professionale-operatore-olistico)."),
    # la legge 4/2013 dice di mettere la dicitura ovunque: la bio e' il
    # primo posto
    ("legge-4-2013-professioni-olistiche",
     "**Se lavori nel benessere:** metti la dicitura ovunque,",
     "**Se lavori nel benessere:** metti la dicitura ovunque — a "
     "partire dalla [bio professionale]"
     "(/blog/bio-professionale-operatore-olistico) —,"),
]

WHITELIST = ("doi.org", "pubmed.ncbi.nlm.nih.gov", "normattiva.it")


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db
    from routers.seo_shell import _extract_faq
    import re

    for art in ARTICOLI:
        t, d = art["titolo"], art["descrizione"]
        assert len(t) <= 60, f"title lungo: {art['slug']} ({len(t)})"
        assert 0 < len(d) <= 158, f"description: {art['slug']} ({len(d)})"
        n_faq = len(_extract_faq(art["contenuto"]))
        assert n_faq >= 4, f"FAQ scarse in {art['slug']}: {n_faq}"
        esterni = re.findall(r"\]\((https?://[^)\s]+)\)", art["contenuto"])
        assert all(any(w in u for w in WHITELIST) for u in esterni), esterni
        print(f"{t}\n  slug: {art['slug']}  parole: "
              f"{len(art['contenuto'].split())}  T:{len(t)} D:{len(d)}  "
              f"FAQ:{n_faq}  esterni:{len(esterni)}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    for art in ARTICOLI:
        esistente = await db.articles.find_one({"slug": art["slug"]},
                                               {"_id": 0, "id": 1})
        campi = {"title": art["titolo"], "description": art["descrizione"],
                 "content": art["contenuto"], "category": art["categoria"],
                 "author_name": "Aurya", "published": True,
                 "updated_at": now, "translations": {},
                 "related_slugs": art["related"]}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": art["slug"],
                      "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": art["slug"]},
                                     {"$set": campi}, upsert=True)

        doc = await db.articles.find_one({"slug": art["slug"]},
                                         {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(art["slug"], art["categoria"])
            if url:
                await db.articles.update_one(
                    {"slug": art["slug"]},
                    {"$set": {"featured_image_url": url}})
                print(f"  copertina {art['slug'][:40]}: ok")

    nuovi = {a["slug"] for a in ARTICOLI}
    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        # il link che qualifica l'aggiunta e' quello verso il pezzo
        # NUOVO, non il primo del testo (che puo' essere preesistente)
        atteso = next(l for l in re.findall(r"/blog/([a-z0-9-]+)\)", nuovo)
                      if l in nuovi)
        if not d:
            print(f"  ASSENTE {slug}")
        elif f"/blog/{atteso})" in d["content"]:
            print(f"  link gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  backlink aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]}")

    # audit di chiusura sull'intero corpus
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1}).to_list(200)
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\nlink rotti: {rotti or 'nessuno'}")
    assert not rotti
    inbound = {a["slug"]: 0 for a in arts}
    for a in arts:
        for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]):
            if l in inbound and l != a["slug"]:
                inbound[l] += 1
    orfani = [s for s, cnt in inbound.items() if cnt == 0]
    print(f"orfani: {orfani or 'nessuno'}")
    assert not [s for s in nuovi if inbound[s] == 0], "nuovo pezzo orfano"
    print(f"articoli totali: {len(arts)}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
