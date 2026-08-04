# -*- coding: utf-8 -*-
"""ED3 — tre uscite del calendario di agosto, in un colpo solo.

I TRE PEZZI E PERCHE' LORO. Dalla coda del piano espansione
(docs/PIANO_ESPANSIONE_BLOG_2026-08.md), i tre senza revisione
founder preventiva:

1. «Come scegliere un insegnante di yoga» (yoga) — query decisionale
   scoperta; la guida allo yoga e quella agli stili rimandano entrambe
   ai criteri generali, ma il passo specifico (lezione di prova,
   segnali in sala, quando cambiare) mancava.
2. «Mindfulness e meditazione: che differenza c'e'» (meditazione) —
   la domanda piu' frequente del cluster, oggi liquidata in due FAQ;
   query da featured snippet, merita il pezzo dedicato.
3. «Il primo colloquio con un operatore olistico» (scegliere) — la
   guida all'operatore serio dice COSA chiedere; questo pezzo racconta
   il momento in cui lo chiedi: prima, durante, dopo, e come si dice no.

ONESTA' DEI DATI. Nessun numero nuovo: prezzi yoga (10-20 euro,
abbonamenti 50-80) e formazioni 200/500 ore ripresi dalle guide
esistenti; MBSR (1979, otto settimane, primo studio 1982 PubMed
7042457) dalla guida MBSR. Un solo link esterno, gia' in whitelist.

Idempotente; da rieseguire in prod al lancio.

    venv/bin/python scripts/ed3_tre_articoli_agosto.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

ART_YOGA = {
    "slug": "come-scegliere-un-insegnante-di-yoga",
    "titolo": "Come scegliere un insegnante di yoga: i segnali che contano",
    "descrizione": ("La lezione di prova, le domande da fare, cosa valgono "
                    "le formazioni, i segnali in sala e quando cambiare: "
                    "come trovare la persona giusta."),
    "categoria": "yoga",
    "related": ["differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
                "yoga-cose-da-dove-viene-come-cominciare",
                "come-capire-se-un-operatore-olistico-e-serio"],
    "contenuto": """La storia si racconta quasi sempre con le stesse parole: «ho provato yoga, non fa per me». E a chiedere com'è andata, esce quasi sempre lo stesso dettaglio: una lezione sola, un insegnante solo, e una conclusione tratta su tutta la disciplina.

Quella frase, il più delle volte, sbaglia soggetto. Non era lo yoga: era quella lezione, con quella persona. Nella [guida agli stili](/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini) lo diciamo chiaramente: fra due lezioni dello stesso stile, la differenza la fa l'insegnante, non il nome sul volantino. Questa pagina esiste per il passo successivo, quello che nessuno spiega: come si sceglie la persona.

## Perché l'insegnante pesa più dello stile

Lo stile decide il ritmo e la forma della lezione. L'insegnante decide tutto il resto: se ti accorgi di quello che fa il tuo corpo o lo forzi, se una posizione ti costruisce o ti fa male, se torni la settimana dopo.

C'è anche una ragione più concreta. Lo yoga si trasmette per correzione: qualcuno guarda quello che fai e ti aiuta ad aggiustarlo. Un video non lo fa, un insegnante distratto nemmeno. Stai scegliendo gli occhi che ti guarderanno mentre impari — ed è una scelta che merita più attenzione del colore del tappetino.

## Cosa c'è dietro la parola «formato»

In Italia insegnare yoga non richiede un titolo di Stato: non esiste un albo, e la cornice è quella delle professioni non organizzate. Le formazioni però esistono, e capirle serve a leggere le presentazioni.

**I percorsi a monte ore.** Le formazioni più diffuse dichiarano un numero di ore, tipicamente 200 o 500. Il numero da solo non dice la qualità — dice l'investimento: un percorso da 500 ore, spesso pluriennale, è un impegno diverso da un intensivo. Un insegnante serio dichiara ore, scuola e anno senza che tu debba chiederli.

**I diplomi degli enti sportivi.** È la via da cui passa gran parte degli insegnanti in Italia, perché permette di insegnare in palestre e associazioni sportive con una cornice fiscale e assicurativa definita. Sono qualifiche tecniche sportive: valide nel loro campo, e non sono titoli sanitari. Il quadro completo di sigle e attestati è nella [guida per capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

**I lignaggi.** Alcuni insegnanti si presentano attraverso la tradizione in cui si sono formati o il maestro con cui hanno studiato. È un'informazione vera e verificabile — una scuola con un nome ha allievi, storia, un metodo riconoscibile — ma funziona come le ore: dice da dove viene, non come insegna.

La regola pratica: la formazione dichiarata con precisione è un segnale, la formazione vaga è un altro. «Insegno da dieci anni» senza dire dove ti sei formato è una frase che dovrebbe farti fare una domanda in più.

## La lezione di prova: cosa guardare

La prova non serve a capire se lo yoga ti piace — per quello [servono almeno tre lezioni](/blog/yoga-cose-da-dove-viene-come-cominciare). Serve a guardare come lavora la persona. Cinque cose, in ordine di importanza.

**Ti chiede come stai, prima.** Infortuni, schiena, pressione, gravidanza. Un insegnante che comincia senza sapere niente di te sta insegnando a una sala, non a delle persone. È il segnale che da solo vale metà della scelta.

**Il contatto è nominato.** Nelle sale che lavorano bene, ti viene chiesto se va bene essere toccato prima che succeda, non dopo. Se le mani arrivano senza che nessuno ne abbia parlato, hai già un'informazione importante.

**Propone alternative, non prestazioni.** «Se oggi le ginocchia dicono no, fai così» è insegnamento. Una sala dove tutti devono arrivare nella posizione intera, a qualsiasi costo, è un'altra cosa.

**Ti lascia uscire da una posizione senza farti sentire in difetto.** Puoi fermarti, sederti, saltare un passaggio. Un insegnante preparato lo dice all'inizio; uno bravo lo rende normale.

**Guarda gli allievi.** Sembra ovvio e non lo è: c'è chi passa la lezione a praticare la propria sequenza davanti alla sala. L'insegnante che cammina fra i tappetini, e vede la mano appoggiata male in fondo alla stanza, sta facendo il mestiere.

## Le domande da fare

Si fanno in un messaggio o nei cinque minuti prima della prova, e le risposte pesano più di qualsiasi recensione.

**«Dove ti sei formato, e per quanto?»** La risposta buona è specifica. La risposta evasiva è una risposta anche lei.

**«Ho questo problema — la classe va bene per me?»** Ernia, cervicale, pressione, un intervento recente. Chi ti dice «nessun problema, è adatto a tutti» senza fare domande ti ha appena detto come lavora. Chi ti fa due domande, o ti indirizza a una classe più adatta — magari a uno stile che usa supporti, come l'Iyengar — sta lavorando bene prima ancora di conoscerti.

**«Com'è composta la classe?»** Quante persone, che livello, da quanto si conoscono. Una classe da trenta è un'esperienza diversa da una da otto, e nessuna delle due è sbagliata: devi solo sapere in cosa stai entrando.

E vale la regola generale delle [domande al primo contatto](/blog/come-capire-se-un-operatore-olistico-e-serio): la disponibilità a rispondere conta quanto il contenuto delle risposte.

## I segnali che non dicono niente

**Il corpo dell'insegnante.** Un fisico scolpito o una flessibilità spettacolare raccontano la sua pratica, non la sua capacità di accompagnare la tua. Alcuni degli insegnanti migliori non fanno più le posizioni estreme da anni, e proprio per questo sanno spiegarle.

**Le acrobazie sui social.** La verticale in riva al mare misura la capacità di comunicare, che è un mestiere diverso. Nessuna lezione per principianti contiene quella posizione.

**Il sanscrito fluente.** Nominare le posizioni nella lingua originale è parte della tradizione, non una prova di competenza. E un buon insegnante le dice anche in italiano, perché gli importa che tu capisca.

**Il prezzo alto o basso.** Le lezioni in Italia si muovono in una forchetta nota — [i numeri sono qui](/blog/quanto-costano-pratiche-olistiche) — e dentro quella forchetta il prezzo riflette città e contesto più che qualità.

## Quando cambiare

Cambiare insegnante è normale, non è un tradimento, e capita anche a chi pratica da anni. Ci sono però tre casi in cui non è una preferenza: è una necessità.

**Il dolore ignorato.** Hai detto che una posizione fa male e la risposta è stata di insistere. Il fastidio muscolare del lavoro è una cosa; il dolore articolare è un'altra, e un insegnante che non distingue è un rischio.

**Le mani senza consenso.** Correzioni fisiche mai nominate, contatto che non ti è stato chiesto. Non serve altro contesto.

**Il sentirsi in difetto.** Se esci dalle lezioni sistematicamente con la sensazione di non essere all'altezza, il problema non è il tuo corpo. Una pratica insegnata bene fa l'effetto opposto, a qualsiasi livello.

Per tutto il resto — il ritmo che non ti corrisponde, la voce che non ti arriva, la sala scomoda — vale la formula semplice: si ringrazia e si prova altrove. Nessuna spiegazione dovuta.

## Il punto

La sequenza pratica è questa: scegli lo stile in base a dove parti, prova tre insegnanti diversi, e guarda le cinque cose della lezione di prova. Chi ti chiede come stai, nomina il contatto, propone alternative e ti guarda mentre pratichi è la persona giusta — anche se la sua sala è meno bella e il suo profilo ha meno follower.

E se la prima scelta si rivela sbagliata, non hai perso: hai raccolto l'informazione che serviva per la seconda.

## Domande frequenti

**Che formazione deve avere un insegnante di yoga?**
Non esiste un titolo obbligatorio: le formazioni più diffuse dichiarano 200 o 500 ore, e molti insegnanti hanno diplomi di enti sportivi che permettono di insegnare in palestre e associazioni. Più del tipo di attestato conta che formazione, scuola e anni siano dichiarati con precisione.

**Un bravo praticante è automaticamente un bravo insegnante?**
No: sono due capacità diverse. Saper fare una posizione e saper accompagnare un corpo diverso dal proprio a farla in sicurezza non coincidono, e la seconda si impara insegnando, non praticando.

**Quante lezioni di prova servono per giudicare?**
Una basta per osservare come lavora la persona: se ti chiede come stai, se nomina il contatto, se propone alternative. Per capire se lo stile ti corrisponde ne servono almeno tre, possibilmente con insegnanti diversi.

**Le lezioni online vanno bene?**
Per mantenere una pratica già avviata sì. Per cominciare no: all'inizio serve qualcuno che veda quello che fa il tuo corpo, e uno schermo non lo permette.

**Ho un'ernia (o un'altra condizione): come scelgo?**
Parlane prima con il tuo medico, poi cerca un insegnante che alla tua domanda risponda con domande — dove, da quanto, cosa ti hanno detto — invece che con «nessun problema». Gli stili che usano supporti e lavorano sull'allineamento sono spesso il punto di partenza più adatto.

**È normale che l'insegnante mi tocchi per correggermi?**
È una pratica diffusa e legittima, a una condizione: che ti venga chiesto prima se va bene, e che tu possa dire di no in qualsiasi momento senza doverti giustificare.""",
}

ART_MIND = {
    "slug": "mindfulness-e-meditazione-la-differenza",
    "titolo": "Mindfulness e meditazione: che differenza c'è",
    "descrizione": ("La meditazione è la famiglia, la mindfulness il suo "
                    "membro più famoso: da dove viene ognuna, cosa cambia "
                    "in pratica e quale scegliere per cominciare."),
    "categoria": "meditazione",
    "related": ["mindfulness-cose-mbsr-come-funziona",
                "meditazione-per-chi-inizia-guida-semplice",
                "kit-pratiche-quotidiane-15-minuti"],
    "contenuto": """Succede in quasi ogni corso, di solito verso la fine del primo incontro. Qualcuno alza la mano e fa la domanda che tutti avevano in mente: «ma quindi mindfulness e meditazione sono la stessa cosa?».

Le due parole si usano ormai come sinonimi — sulle app, nei corsi, negli articoli — e la confusione è comprensibile, perché la risposta breve sembra un gioco di parole: sì e no. Questa pagina dà la risposta lunga, che è più utile: da dove viene ognuna delle due, cosa cambia in pratica, e quale conviene a te.

## La risposta in una frase

La meditazione è una famiglia di pratiche; la mindfulness è un membro di quella famiglia — il più famoso, il più studiato, e l'unico con una data di nascita precisa.

Tutta la mindfulness è meditazione. Non tutta la meditazione è mindfulness: nella famiglia ci sono anche la concentrazione su un oggetto, la visione profonda, l'amorevolezza, i mantra, le pratiche guidate e quelle in movimento — [le abbiamo messe in fila qui](/blog/meditazione-per-chi-inizia-guida-semplice).

## Due storie diverse

**La meditazione** non ha una data di nascita: ha millenni di tradizioni che l'hanno sviluppata in forme diverse — buddhiste, induiste, taoiste, contemplative cristiane — ognuna dentro una propria cornice di senso. Quando oggi qualcuno dice «medito», può stare facendo pratiche molto lontane fra loro: ripetere un mantra, osservare il respiro, camminare con attenzione, recitare frasi di augurio.

**La mindfulness** una data di nascita ce l'ha: il 1979, in un ospedale universitario americano, quando Jon Kabat-Zinn costruì un programma per pazienti con dolore cronico che la medicina non riusciva più ad aiutare. Prese la sostanza della vipassana buddhista — l'osservazione di quello che accade, momento per momento — e la estrasse dalla cornice religiosa, deliberatamente, per poterla portare in un reparto senza chiedere a nessuno di aderire a una tradizione. Ne nacque il protocollo MBSR, otto settimane con una forma precisa, e [il primo studio pubblicato è del 1982](https://pubmed.ncbi.nlm.nih.gov/7042457/): da lì la parola ha cominciato il viaggio che l'ha portata ovunque.

La definizione di Kabat-Zinn resta la più precisa in circolazione: prestare attenzione intenzionalmente, al momento presente, senza giudicare.

## Cosa cambia in pratica

Se ti siedi cinque minuti a osservare il respiro, stai facendo l'una o l'altra? Il gesto è lo stesso — ed è il punto a cui arriveremo. Ma quattro differenze reali ci sono.

**La struttura.** La mindfulness che ha le prove scientifiche è quella dei protocolli: [otto settimane, incontri di gruppo, pratica quotidiana a casa](/blog/mindfulness-cose-mbsr-come-funziona), con un inizio e una fine. La meditazione tradizionale è un percorso aperto: si pratica per anni, spesso dentro una relazione con un insegnante, senza un traguardo dichiarato.

**Il linguaggio.** La mindfulness parla la lingua della psicologia: stress, attenzione, regolazione emotiva. Le tradizioni parlano ognuna la propria: risveglio, unione, liberazione, grazia. Sotto le parole diverse i gesti spesso si somigliano, ma il linguaggio decide chi si sente invitato e chi no.

**Il contesto.** La mindfulness è nata per entrare dove le tradizioni non potevano: ospedali, scuole, aziende. È il suo pregio e il suo rischio insieme — della versione aziendale e delle sue critiche parliamo nella [guida all'MBSR](/blog/mindfulness-cose-mbsr-come-funziona).

**Lo scopo dichiarato.** I protocolli mirano a qualcosa di misurabile: meno stress percepito, meno ricadute, una relazione diversa con il dolore. Le tradizioni mirano più in alto e più lontano, a una trasformazione della persona che nessun questionario misura. Nessuno dei due scopi è migliore: sono promesse diverse, e conviene sapere quale ti stanno facendo.

## Gli equivoci più comuni

**«La mindfulness è rilassamento».** No: è attenzione, anche alle cose spiacevoli — è la parte che la versione commerciale tende a saltare. Il rilassamento è un effetto collaterale frequente, non l'obiettivo.

**«La meditazione è religiosa».** Dipende dalla pratica: la concentrazione sul respiro e la mindfulness sono laiche anche quando discendono da tradizioni religiose, e non chiedono di credere in niente. Altre pratiche mantengono la loro cornice, e chi le propone dovrebbe dirlo.

**«La mindfulness è meditazione per principianti».** Nemmeno: è meditazione con una forma specifica, e il protocollo completo — quaranta minuti al giorno per otto settimane — è tutt'altro che una versione ridotta. Semmai è la porta d'ingresso più documentata.

**«Sono cose diverse, devo scegliere».** In pratica no: chi inizia con un protocollo e continua per conto suo, o chi arriva da una tradizione e frequenta un MBSR, sta camminando nello stesso territorio con mappe diverse.

## Quale delle due, per te

**Se vuoi struttura, un gruppo e delle prove**, il percorso di otto settimane è la strada: ha una forma verificabile, un inizio e una fine, e la letteratura scientifica più ampia del campo.

**Se vuoi semplicemente cominciare, stasera e gratis**, non serve scegliere un'etichetta: [cinque minuti di attenzione al respiro](/blog/meditazione-per-chi-inizia-guida-semplice), tutti i giorni, sono il punto di partenza di entrambe le strade. E le pratiche brevi del [kit dei quindici minuti](/blog/kit-pratiche-quotidiane-15-minuti) tengono l'abitudine in piedi nei giorni pieni.

**Se una tradizione ti chiama** — per storia personale, per curiosità, per il suo linguaggio — quella è una ragione legittima quanto uno studio clinico. L'unica avvertenza vale per tutti: [chi ti guida conta più dell'etichetta](/blog/come-capire-se-un-operatore-olistico-e-serio), e i percorsi intensivi non sono il punto da cui cominciare.

## Il punto

La distinzione è utile per orientarsi e per non farsi vendere una cosa per un'altra. Ma il gesto che sta sotto le due parole è lo stesso: accorgersi che la mente se n'è andata, e riportarla. Chi lo fa tutti i giorni, con qualsiasi nome, sta facendo la pratica; chi conosce perfettamente la differenza e non si siede mai, no.

## Domande frequenti

**Mindfulness e meditazione sono la stessa cosa?**
La mindfulness è un tipo di meditazione: la versione laica e strutturata in protocolli della vipassana buddhista, nata nel 1979 in ambito ospedaliero. La meditazione è la famiglia grande, che comprende anche concentrazione, amorevolezza, mantra e pratiche guidate.

**La mindfulness è più efficace della meditazione?**
È la più studiata, che non è la stessa cosa: i protocolli hanno una forma stabile che si presta alla ricerca, le pratiche tradizionali meno. Sulle misure disponibili — stress percepito, sintomi d'ansia, ricadute depressive — i risultati più solidi vengono dai protocolli strutturati.

**Posso praticare entrambe?**
Sì, e succede continuamente: molte persone iniziano con un corso di mindfulness e proseguono con una pratica personale, o viceversa. Il gesto di fondo è lo stesso.

**Serve credere in qualcosa per meditare?**
No. Concentrazione e mindfulness sono laiche anche quando provengono da tradizioni religiose. Alcune pratiche mantengono la loro cornice spirituale, ed è legittimo sia cercarla sia evitarla: l'importante è che chi propone sia trasparente su cosa stai frequentando.

**Da dove conviene cominciare?**
Da cinque minuti al giorno di attenzione al respiro, che sono il punto di partenza comune. Se poi vuoi struttura e gruppo, un percorso di otto settimane; se vuoi solo consolidare l'abitudine, bastano costanza e una pratica breve.""",
}

ART_COLLOQUIO = {
    "slug": "primo-colloquio-operatore-olistico",
    "titolo": "Il primo colloquio con un operatore olistico",
    "descrizione": ("Cosa succede al primo incontro, cosa dire della tua "
                    "salute, come fare le domande senza imbarazzo e come "
                    "decidere dopo — anche per un no."),
    "categoria": "scegliere",
    "related": ["come-capire-se-un-operatore-olistico-e-serio",
                "quanto-costano-pratiche-olistiche",
                "discipline-olistiche-la-mappa"],
    "contenuto": """Il messaggio è partito ieri, la risposta è arrivata gentile, l'appuntamento è fra tre giorni. E adesso che è tutto deciso arriva la parte che nessuna guida racconta: cosa succede, esattamente, la prima volta? Cosa devo dire, cosa mi chiederanno, posso fare domande senza sembrare diffidente, e se poi non mi convince — come si fa a dirlo?

Della scelta a monte ci siamo occupati altrove: [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio) mette in fila verifiche, domande e bandiere rosse. Questa pagina racconta il momento in cui quelle domande si fanno davvero: prima, durante e dopo il primo incontro.

## Un colloquio, non una sessione

La prima cosa da sapere ribalta un'aspettativa: il primo incontro fatto bene è soprattutto una conversazione. Nelle pratiche serie c'è un colloquio prima di qualsiasi altra cosa — qualche minuto, a volte l'incontro intero, in cui racconti perché sei lì e ti viene chiesto della tua situazione.

Non è tempo perso, è il contrario: è il segnale più affidabile che hai davanti qualcuno che lavora bene. Chi ti mette sul lettino dopo due minuti sta trattando il tuo corpo come un appuntamento da evadere; chi ti fa domande sta facendo il mestiere.

Molti professionisti offrono anche una conversazione preliminare gratuita, al telefono o per messaggio, prima ancora di fissare: una decina di minuti per capire se ha senso incontrarsi. Se te la propongono, prendila: è il modo più economico che esista per raccogliere informazioni. E la disponibilità stessa a concederla è già una risposta.

## Prima: cosa portare

Non servono documenti. Servono tre cose pensate prima, perché sul momento l'agitazione le mangia.

**La tua storia, in breve.** Condizioni di salute, farmaci che prendi, gravidanza in corso o cercata, percorsi psicologici in corso, interventi recenti. Dirlo non è burocrazia: è il materiale con cui una persona seria decide se e come lavorare con te — e in certi casi se dirti che la sua pratica, per te, adesso, non è indicata. Ometterlo per riservatezza è comprensibile e controproducente insieme: chi lavora bene queste cose le chiede comunque, e a chi non le chiede affatto non dovresti affidarti.

**Cosa stai cercando, detto semplice.** «Dormo male da mesi», «sono in un periodo pesante», «voglio provare perché me ne hanno parlato bene» sono tutte risposte legittime. Non serve una motivazione nobile: serve una frase vera, perché è su quella che la persona ti dirà cosa può fare e cosa no. Se non sai ancora bene cosa cerchi, la [mappa delle discipline](/blog/discipline-olistiche-la-mappa) aiuta a orientarsi prima di scegliere una porta.

**Le domande, scritte.** Sembra eccessivo e non lo è: le domande pensate a casa spariscono davanti a una persona gentile che parla bene. Scrivile sul telefono — dove si è formata, cosa succede passo per passo, quando questa pratica non è indicata, costi e disdetta — e guardale prima di salutare.

## Durante: cosa dovrebbe succedere

**Ti viene chiesto della salute.** Prima di qualsiasi pratica, non dopo. Se il colloquio non tocca mai la tua situazione — farmaci, condizioni, momenti di fragilità — manca la cosa più importante, e la mancanza è un'informazione.

**Ti viene spiegato cosa succederà.** Passo per passo, in parole normali: quanto dura, cosa farai tu, cosa farà l'altra persona, cosa è normale sentire. Le spiegazioni piene di gergo che ti lasciano più confuso di prima non sono profondità: sono nebbia.

**Il contatto fisico viene nominato prima.** Nelle pratiche a mediazione corporea è il punto che protegge di più: ti viene detto dove verrai toccato e ti viene chiesto se va bene, prima. E hai il diritto di dire no — a una parte, a tutto, anche a metà sessione — senza doverti giustificare.

**I soldi si dicono chiari.** Prezzo, durata, cosa succede se disdici: prima, senza che tu debba insistere, idealmente per iscritto. Le forchette normali per le pratiche più diffuse [le trovi qui](/blog/quanto-costano-pratiche-olistiche), e servono a una cosa sola: riconoscere quando un numero merita una domanda in più.

**Nessuna proposta di pacchetto.** Il percorso da molte sedute pagato in anticipo, proposto al primo incontro — magari mentre ti rimetti le scarpe — è pressione commerciale nel momento in cui sei più aperto. Un professionista serio al primo incontro ti saluta, e semmai ti dice quando ha senso risentirsi.

Sulle domande da fare: le cinque che separano — formazione, svolgimento, controindicazioni, condizioni, rete di colleghi — [le abbiamo raccolte qui](/blog/come-capire-se-un-operatore-olistico-e-serio), con il modo di leggere le risposte. Il punto in più che riguarda il colloquio è il come: falle come faresti con qualsiasi altro professionista, senza premesse e senza scuse. Chi lavora bene le riceve tutti i giorni e risponde volentieri; chi si irrigidisce a una domanda normale ti sta mostrando come gestirà le domande difficili.

## Dopo: come si decide

**Lascia passare una notte.** La decisione presa sulla porta è la più esposta: all'entusiasmo, alla soggezione, alla fatica di dire no a una persona gentile. Un giorno di distanza rimette le cose in proporzione, e nessun professionista serio ha problemi ad aspettare una risposta.

**Come ti sei sentito è un dato.** Non l'unico, ma uno vero: se sei uscito messo fretta, valutato, o vagamente in colpa per le domande che hai fatto, quella sensazione vale quanto un attestato — e arriva prima.

**Rileggi le risposte, non l'atmosfera.** L'ambiente accogliente e il modo di parlare contano, e sono anche le cose più facili da costruire. Le risposte alle tue domande — precise o evasive, complete o a metà — sono più difficili da truccare.

**Se sei in un momento fragile, delega una parte del giudizio.** Un lutto, una separazione, una diagnosi: nei momenti in cui hai bisogno che qualcosa funzioni, fare domande scomode diventa più difficile proprio quando servirebbe di più. Il correttivo è semplice e funziona: fai leggere la conversazione a una persona di cui ti fidi, prima di impegnarti.

## Dire di no

È la parte che trattiene più persone dal fare domande: la paura di dover poi gestire un rifiuto. Vale allora la pena dirlo chiaramente: no è una risposta normale, e si dà in una riga — «grazie del tempo, ho deciso di non proseguire». Senza spiegazioni, che non sono dovute, e senza recensioni negative se non è successo niente di grave: semplicemente non era la persona giusta per te.

Se invece qualcosa di grave è successo — promesse di cura, pressioni sui farmaci, contatto non consensuale — non è più una questione di preferenze: i passi da fare sono nella [guida all'operatore serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

E c'è anche il no che arriva dall'altra parte: il professionista che ti dice «per questa situazione non sono io la persona giusta» e magari ti indirizza altrove. Non è un rifiuto: è il segnale di qualità più alto che esista in questo campo, e se ti capita, quel nome tienilo da parte per un'altra occasione.

## Domande frequenti

**Il primo colloquio si paga?**
Dipende: molti professionisti offrono una conversazione preliminare gratuita di una decina di minuti, mentre il primo incontro completo è di solito a pagamento. L'importante è che il costo sia detto chiaro prima di fissare, qualunque sia.

**Devo dire dei farmaci che prendo?**
Sì, sempre: farmaci, condizioni di salute, gravidanza e percorsi in corso sono il materiale con cui una persona seria decide se e come lavorare con te. Chi non te lo chiede affatto sta saltando il passaggio più importante.

**Posso portare qualcuno con me?**
Al colloquio conoscitivo sì, ed è una richiesta normale — soprattutto se stai attraversando un periodo difficile. La reazione alla richiesta è essa stessa un'informazione.

**Posso rifiutare il contatto fisico?**
Sempre, in qualsiasi momento, anche a metà sessione e senza giustificarti. Nelle pratiche corporee serie il contatto viene nominato e concordato prima; se arriva senza che ne abbiate parlato, hai il diritto di fermare tutto.

**E se dopo il colloquio non mi convince?**
Lascia passare una notte e rispondi con una riga: «grazie del tempo, ho deciso di non proseguire». Nessuna spiegazione è dovuta, e nessun professionista serio la pretende.

**Il professionista può dirmi di no?**
Sì, e quando succede è quasi sempre un buon segno: dire «per questa situazione non sono la persona giusta» richiede l'onestà che vorresti trovare. Spesso arriva insieme a un'indicazione più adatta — un collega, o una figura sanitaria quando serve quella.""",
}

ARTICOLI = [ART_YOGA, ART_MIND, ART_COLLOQUIO]

# backlink dalle ancore naturali dei pezzi esistenti
AGGIUNTE = [
    # la guida allo yoga rimanda ai criteri generali: da li' si scende
    # nel pezzo specifico
    ("yoga-cose-da-dove-viene-come-cominciare",
     "e un insegnante serio le dichiara senza che tu debba chiederle.",
     "e un insegnante serio le dichiara senza che tu debba chiederle. "
     "Il passo per passo — la lezione di prova, le domande, i segnali "
     "in sala — sta in [come scegliere un insegnante di yoga]"
     "(/blog/come-scegliere-un-insegnante-di-yoga)."),
    # la guida agli stili chiude proprio sul tema: l'insegnante conta
    # piu' dello stile
    ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
     "Alla terza avrai capito più di quanto ti abbia detto questa pagina.",
     "Alla terza avrai capito più di quanto ti abbia detto questa "
     "pagina. E per valutare chi hai davanti, [come scegliere un "
     "insegnante di yoga](/blog/come-scegliere-un-insegnante-di-yoga) "
     "entra nel dettaglio."),
    # le due FAQ gemelle sulla differenza rimandano alla risposta lunga
    ("mindfulness-cose-mbsr-come-funziona",
     "è la famiglia grande, che comprende anche concentrazione, mantra, "
     "amorevolezza e pratiche devozionali.",
     "è la famiglia grande, che comprende anche concentrazione, mantra, "
     "amorevolezza e pratiche devozionali. La risposta estesa sta in "
     "[mindfulness e meditazione: che differenza c'è]"
     "(/blog/mindfulness-e-meditazione-la-differenza)."),
    ("meditazione-per-chi-inizia-guida-semplice",
     "La meditazione è la famiglia grande: dentro ci sono anche "
     "concentrazione, amorevolezza, mantra e pratiche devozionali.",
     "La meditazione è la famiglia grande: dentro ci sono anche "
     "concentrazione, amorevolezza, mantra e pratiche devozionali. "
     "La risposta estesa sta in [mindfulness e meditazione: che "
     "differenza c'è](/blog/mindfulness-e-meditazione-la-differenza)."),
    # la guida all'operatore serio nomina la conversazione preliminare:
    # da li' al racconto del colloquio
    ("come-capire-se-un-operatore-olistico-e-serio",
     "La disponibilità a una conversazione preliminare gratuita di "
     "dieci minuti è già una risposta.",
     "La disponibilità a una conversazione preliminare gratuita di "
     "dieci minuti è già una risposta. Come usare bene quel primo "
     "scambio — e il primo incontro vero — è il tema della [guida al "
     "primo colloquio](/blog/primo-colloquio-operatore-olistico)."),
    # la raccolta prezzi consiglia la guida all'operatore serio: il
    # colloquio e' il terzo pezzo del trittico
    ("quanto-costano-pratiche-olistiche",
     "che è il pezzo che consigliamo di leggere insieme a questo.",
     "che è il pezzo che consigliamo di leggere insieme a questo. E "
     "per il momento in cui quelle domande si fanno davvero, c'è la "
     "[guida al primo colloquio](/blog/primo-colloquio-operatore-olistico)."),
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
        atteso = re.search(r"/blog/([a-z0-9-]+)\)", nuovo).group(1)
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
