#!/usr/bin/env python3
"""M1 (25/8/2026) — «In breve»: la risposta prima del racconto.

MISURA che ha motivato il lavoro: su quattro articoli presi a caso,
TRE aprono con una scena («Il modulo è quasi finito. Nome, indirizzo,
regime fiscale…»). È la voce del brand e non si tocca — ma chi cerca
«codice ateco operatore olistico» vuole il codice, e un motore
generativo che cerca una frase da citare trova un preambolo.

Il blocco sta SOPRA il racconto e ogni riga deve essere vera **da
sola, fuori dal contesto**: è così che una risposta AI la cita, ed è
anche il modo in cui la legge chi è arrivato da una ricerca precisa e
sta decidendo in cinque secondi se restare.

Le righe qui sotto sono TRATTE dagli articoli, non inventate: numeri,
codici e regole vengono dal testo che la redazione ha già scritto e
verificato. Restano una BOZZA da rivedere in /admin (tab Blog).

Uso:
  python3 scripts/in_breve_articoli.py --prova    # dice cosa farebbe
  python3 scripts/in_breve_articoli.py --esegui   # scrive
  python3 scripts/in_breve_articoli.py --esegui --solo slug1,slug2
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# slug → righe dell'«In breve». Una riga = un fatto autonomo.
IN_BREVE = {

    # ── operatori (B2B: alto intento, bassa concorrenza) ──────────────
    "codice-ateco-operatore-olistico": [
        "Non esiste un codice ATECO dedicato agli operatori olistici: si sceglie fra più famiglie.",
        "Il più usato resta il 96.09.09, «altre attività di servizi per la persona».",
        "La classificazione ATECO 2025 ha sostituito quella del 2007 e ha introdotto voci per la medicina complementare: le guide scritte prima riportano numeri che non corrispondono più.",
        "Chi insegna (yoga, meditazione) ragiona su codici diversi da chi riceve su appuntamento, e si possono dichiarare più codici.",
        "Il codice incide su gestione previdenziale e coefficiente del forfettario: la scelta va fatta con un commercialista, non da un articolo.",
    ],
    "partita-iva-operatore-olistico-fiscalita-guida": [
        "La parola che decide è «abitualità»: non conta quanto incassi, ma se l'attività è continuativa e organizzata.",
        "L'attività occasionale si gestisce con ricevuta e ritenuta d'acconto del 20% verso le aziende, con soglia INPS a 5.000 euro lordi annui.",
        "Chi pubblica un calendario, ha un listino e clienti che tornano svolge attività abituale, e serve la partita IVA.",
        "Per alcune discipline riconosciute in ambito sportivo esiste la via dell'ASD/SSD, con franchigia sui compensi sportivi fino a 15.000 euro annui.",
        "È una guida informativa: il commercialista resta l'investimento più sensato dei primi cinquecento euro di attività.",
    ],
    "assicurazione-rc-operatore-olistico": [
        "Servono due coperture diverse: la RC professionale (il danno legato a quello che fai) e la RC della struttura (il danno legato al luogo).",
        "Il massimale è il primo numero da guardare, prima del prezzo: è la cifra oltre la quale la copertura si ferma.",
        "Le attività vanno dichiarate tutte per iscritto, comprese le occasionali: una polizza per il counseling non copre i trattamenti con contatto fisico.",
        "Una polizza da studio non copre da sola un ritiro residenziale: va dichiarato.",
        "Nessuna polizza copre l'esercizio abusivo di professioni sanitarie.",
    ],
    "legge-4-2013-professioni-olistiche": [
        "La legge 4/2013 riconosce le «professioni non organizzate» — quelle senza albo — e permette di esercitarle liberamente, senza autorizzazioni preventive.",
        "Non «abilita» nessuna disciplina e non crea un albo: in cambio della libertà chiede trasparenza verso il cliente.",
        "La legge va citata in ogni documento scritto (preventivi, fatture, contratti, sito): ometterla è trattata come pratica commerciale scorretta.",
        "Presentare una disciplina di benessere come una cura è esattamente il tipo di scorrettezza che la legge sanziona.",
        "Le associazioni professionali sono di natura privata: possono dare standard e codici deontologici, non titoli abilitanti.",
    ],
    "prezzo-giusto-ritiro-come-calcolarlo": [
        "Un prezzo si costruisce dal basso, dai costi veri: guardare cosa fanno i colleghi serve alla fine, per collocarsi, non per copiare.",
        "Nei costi vivi vanno contati anche quelli che non sembrano costi: le tue notti e i tuoi pasti, il tuo viaggio, le commissioni di incasso, l'assicurazione.",
        "Il tuo lavoro è un costo: un weekend di ritiro dura le settimane di preparazione, non due giorni.",
        "Il metro immediato è il costo-opportunità: quanto incasseresti dedicando lo stesso monte ore alle sessioni individuali alla tua tariffa.",
        "I costi fissi e quelli a persona vanno separati: è ciò che dice quanti iscritti servono perché il ritiro stia in piedi.",
    ],


    # ── le pratiche più cercate ───────────────────────────────────────
    "cammini-italiani-quale-scegliere-la-prima-volta": [
        "Per una prima volta il più consigliato è la Via degli Dei: Bologna-Firenze, circa 130 km in cinque-sei tappe.",
        "La credenziale non è obbligatoria ma dà accesso agli alloggi riservati e costa pochi euro: conviene.",
        "Stagione migliore: aprile-giugno e settembre-ottobre quasi ovunque; luglio e agosto sono difficili al centro-sud.",
        "Col cane si può su molti cammini, ma gli alloggi che lo accettano sono meno: verificare tappa per tappa.",
        "Molti cammini nascono da pellegrinaggi ma si percorrono per qualsiasi ragione: nessuno chiede la tua.",
    ],
    "camminare-bagni-di-foresta-cammini": [
        "Tre modi di camminare che non sono spostarsi: il bagno di foresta (shinrin-yoku), la camminata meditativa e il cammino di più giorni.",
        "Gli effetti sullo stress dello stare nel verde sono ben documentati; il filone sul sistema immunitario è il più citato e il meno solido.",
        "Il tempo necessario è meno di quanto si pensi: la ricerca indica benefici già con esposizioni brevi e regolari.",
        "Coi bambini funziona cambiando aspettativa: l'esplorazione prende il posto della contemplazione, e vale comunque.",
        "La camminata meditativa non sostituisce la meditazione, ma è la porta d'ingresso per chi non riesce a stare seduto.",
    ],
    "cosa-portare-a-un-ritiro": [
        "La regola che risolve quasi tutto: metà dei vestiti che pensi, il doppio degli strati.",
        "Due domande all'organizzatore prima di fare la valigia: cosa è fornito (tappetini, cuscini, coperte) e qual è la politica sui telefoni.",
        "Vestirsi a strati e comodi: il corpo in pratica si scalda e si raffredda in fretta, e le sale al mattino sono fredde.",
        "Le tre cose che tutti dimenticano: tappi per le orecchie (le camere condivise sono la norma), uno strato caldo per le pratiche da fermi, una torcia per i sentieri di notte.",
    ],
    "come-promuovere-un-ritiro-e-riempire-i-posti": [
        "Gli ultimi due posti di un ritiro sono spesso quasi tutto il margine: sotto il pareggio si lavora gratis.",
        "L'errore più comune è cercare sconosciuti: il pubblico più prezioso è quello che hai già.",
        "Date e prezzo si annunciano INSIEME: un annuncio senza prezzo genera messaggi da gestire uno a uno e perde chi non scrive.",
        "Per le email promozionali serve un consenso specifico e documentabile: avere l'indirizzo per un altro motivo non basta.",
        "Nella fase di lancio tre-quattro email in tre mesi sono normali, se ognuna dice qualcosa di nuovo.",
    ],
    "bio-professionale-operatore-olistico": [
        "Fra «accompagno in un viaggio trasformativo di riconnessione» e «insegno hatha yoga a persone che lavorano sedute otto ore, formata in tre anni alla scuola X, prima lezione di prova a dieci euro» — chi legge si fida della seconda.",
        "Le persone arrivano preparate: prima di scriverti hanno letto come si riconosce un operatore serio.",
        "Il prezzo nascosto non aumenta le richieste: aumenta i messaggi di chi voleva solo saperlo e gli abbandoni di chi non ha voglia di chiedere.",
        "La foto giusta è una foto vera, recente, con luce naturale e sguardo in camera: non un logo, non un tramonto.",
        "Stessa sostanza ovunque, taglio diverso per canale — e le versioni non devono contraddirsi, a partire dai prezzi.",
    ],
    "lettura-tema-natale-cosa-aspettarsi": [
        "Il tema natale è la fotografia del cielo nel momento della nascita: servono data, ora esatta e luogo, e l'ora è il dato che pesa di più.",
        "Pochi minuti di differenza cambiano l'ascendente: senza l'ora esatta la lettura perde precisione.",
        "I calcoli sono gratuiti online e i tre elementi principali si imparano; l'interpretazione d'insieme è un'altra cosa.",
        "Il «ritorno di Saturno» (ventinove e cinquantotto anni) è una narrazione efficace, non un meccanismo dimostrato.",
        "Come per i tarocchi, il valore del consulto è lo sguardo esterno: vede quello che il proprio punto cieco copre.",
    ],
    "costellazioni-familiari-cosa-sono-come-funzionano": [
        "Nelle costellazioni familiari degli sconosciuti rappresentano i membri della famiglia di chi porta un tema, disposti nello spazio.",
        "È il metodo che divide più di ogni altro: esperienza profonda per chi la vive, teatro suggestivo per chi guarda da fuori.",
        "La spiegazione documentata è la lettura consapevole dei segnali non verbali del gruppo (fenomeno reale e studiato); il «campo condiviso» della tradizione non ha riscontro sperimentale.",
        "Nei giorni dopo sono comuni sensibilità aumentata o stanchezza: l'indicazione classica è non prendere decisioni importanti nell'immediato.",
        "Non è una professione regolata né un metodo validato, e chi lo pratica non è per questo un terapeuta.",
    ],
    "tarocchi-oracoli-strumento-evolutivo": [
        "I tarocchi come strumento riflessivo: le carte non predicono, fanno da specchio a una domanda.",
        "La «antica sapienza egizia» è un racconto: la storia documentata è più recente.",
        "Per cominciare: il mazzo Rider-Waite-Smith, perché ogni carta ha una scena illustrata e si legge anche senza aver studiato.",
        "Si può imparare da soli come strumento personale; il consulto resta diverso — lo sguardo esterno vede il punto cieco.",
        "Un consulto ha senso quando c'è una domanda vera: chi propone appuntamenti fissi settimanali sta costruendo un'abitudine, non accompagnando un percorso.",
    ],
    "ciclo-mestruale-quattro-fasi-come-ascoltarlo": [
        "La mappa delle quattro fasi è utile, ma non è il territorio: presentarla come legge naturale fa sentire sbagliata chi non ci si riconosce.",
        "I ventotto giorni sono una media, non una regola.",
        "Gli studi sull'influenza del ciclo sulla lucidità sono contraddittori e gli effetti misurati piccoli: il proprio diario vale più della media di uno studio.",
        "Le app funzionano come diario; le previsioni sull'ovulazione sono stime, e quei dati sono dati sanitari — vale la pena sapere a chi si danno.",
        "Il diario si tiene da sole: un cerchio aggiunge il confronto con altre, che è un valore diverso.",
    ],
    "cerchi-di-donne-cosa-sono-come-funzionano": [
        "Un cerchio è un incontro guidato da una facilitatrice, con un patto detto ad alta voce all'inizio: ciò che si condivide resta lì.",
        "Nessuna è obbligata a raccontare: il giro di parola si può passare, e capirlo è il modo migliore per decidere se fa per sé.",
        "Costa in genere fra i 10 e i 30 euro a incontro.",
        "Esistono cerchi dedicati a gravidanza e post parto: dirlo prima alla facilitatrice cambia cosa propone.",
        "Il patto vale anche fuori: incontrando una donna del cerchio non si nomina il cerchio né ciò che ha condiviso, a meno che non sia lei ad aprirlo.",
    ],
    "pratiche-olistiche-contro-stress-cosa-funziona": [
        "Lo stress non è un'emozione: è una risposta fisiologica, e pratiche diversissime funzionano perché spengono lo stesso interruttore.",
        "Per iniziare: una pratica sola, piccola e quotidiana — la semplicità protegge la costanza.",
        "Le tecniche di respiro lento sono l'effetto più rapido; la costanza nelle settimane è ciò che stabilizza.",
        "Un buon ritiro anti-stress produce effetti reali su sonno e tono: la domanda giusta è cosa ti manda a casa — una pratica sostenibile o solo un bel ricordo.",
    ],
    "rebirthing-cose-come-funziona-una-sessione": [
        "Il rebirthing è una tecnica esperienziale di respirazione circolare connessa: si respira ampio e senza pause per un tempo lungo, con un facilitatore.",
        "Porta a stati di attivazione intensa e ha controindicazioni precise: non si pratica da soli, e non è adatto a tutti.",
        "L'irrigidimento di mani e viso durante la sessione è alcalosi respiratoria: respirare più del necessario elimina troppa anidride carbonica — è temporaneo e si risolve rallentando.",
        "Non è psicoterapia e non la sostituisce: chi conduce non è un terapeuta.",
    ],
    "respiro-sistema-nervoso-cosa-succede": [
        "Il respiro è l'unica funzione automatica del corpo che possiamo governare a piacere: per questo è la porta d'accesso al sistema nervoso.",
        "Il meccanismo si sente con due dita sul polso: inspirando il battito accelera leggermente, espirando rallenta.",
        "Allungare l'espirazione è il modo più diretto per attivare il freno del sistema nervoso: pochi minuti bastano per l'effetto immediato.",
        "Per un cambiamento stabile servono due-tre settimane di pratica quotidiana breve.",
    ],
    "alimentazione-ayurvedica-principi-sei-sapori": [
        "L'alimentazione ayurvedica chiede prima COME mangiare, non cosa: nei suoi testi un cibo perfetto mangiato male vale meno di un cibo qualsiasi mangiato bene.",
        "La costituzione non si stabilisce da soli: gli elenchi «cosa mangia vata/pitta/kapha» presuppongono un consulto che la maggior parte delle pagine salta.",
        "Non servono ingredienti particolari: ghee e spezie si trovano ovunque, e un'alimentazione ayurvedica che richiede un negozio specializzato è stata venduta male.",
        "Le «combinazioni vietate» non hanno riscontro scientifico; il principio sotto — i pasti semplici si digeriscono meglio — si verifica da sé.",
        "Sul sonno e sulla pesantezza i primi effetti si notano in una-due settimane; sul resto, mesi.",
    ],
    "smettere-alcol-zucchero-caffeina-cosa-succede": [
        "Togliere caffè, alcol e zucchero non «elimina tossine» — fegato e reni fanno quel lavoro comunque: si tolgono tre sostanze che agiscono sul sistema nervoso, e ciò che si sente è il riassestamento.",
        "La sospensione della caffeina ha una descrizione clinica precisa: mal di testa e stanchezza nei primi giorni, poi passa.",
        "L'avvertimento serio riguarda l'alcol: in chi beve molto e regolarmente la sospensione brusca può essere pericolosa e va fatta con supporto medico.",
        "Quasi nessuno toglie per sempre, e non è il punto: il valore è capire quanto era scelta e quanto automatismo.",
        "Chi prende farmaci ne parli col medico: alcune terapie interagiscono con caffeina e alcol.",
    ],
    "digiuno-consapevole-detox-benefici-falsi-miti": [
        "L'idea che il corpo accumuli tossine che solo succhi e tisane eliminano non ha basi: fegato e reni fanno quel lavoro ogni giorno, gratis.",
        "Il valore vero di un periodo detox non è biochimico, è comportamentale: fermarsi, alleggerire, rompere gli automatismi.",
        "Detox e digiuno terapeutico sono cose diverse: il secondo è pratica clinica con supervisione medica continua — confonderli è l'errore più pericoloso del settore.",
        "Il rischio maggiore del digiuno lungo è la rialimentazione, per gli spostamenti di elettroliti: non si improvvisa.",
        "Con una storia di disturbo alimentare la risposta è no senza valutazione clinica: il digiuno può riattivare uno schema anche a distanza di anni.",
    ],
    "kit-pratiche-quotidiane-15-minuti": [
        "Sette pratiche brevi spiegate come si imparano davvero: cosa fai, cosa senti, cosa succede quando va storto.",
        "Una pratica fatta tutti i giorni vale più di sette provate una volta: è il fraintendimento più costoso.",
        "La continuità si misura sui mesi, non sui giorni: nei giorni storti bastano anche due minuti.",
        "Chi è agitato comincia dalla camminata o dai cinque sensi, non dalla pratica seduta: chiedere immobilità a un corpo attivato è il modo più veloce per mollare.",
        "Le app vanno bene per cominciare; dopo qualche settimana il silenzio con un timer è una pratica diversa e più tua.",
    ],
    "yoga-cose-da-dove-viene-come-cominciare": [
        "Lo yoga non è solo posizioni: nella tradizione sono un ramo su otto, insieme a respiro, etica, concentrazione e meditazione.",
        "Per cominciare non serve essere flessibili: la flessibilità è un effetto della pratica, non un requisito.",
        "Una lezione singola costa 10-20 euro; un abbonamento mensile in genere 50-80.",
        "La differenza vera fra due lezioni non la fa lo stile: la fa l'insegnante.",
        "Due volte a settimana è la soglia sotto cui i cambiamenti si notano poco.",
    ],
    "pranayama-tecniche-respirazione-yoga": [
        "Il pranayama è il ramo dello yoga dedicato al respiro, con una cornice e un ordine di apprendimento propri.",
        "Le tecniche lente (respiro alternato, ujjayi) calmano e sono adatte a quasi tutti; quelle intense (kapalabhati, bhastrika) attivano e hanno controindicazioni.",
        "Il breathwork contemporaneo comprende anche pratiche occidentali novecentesche: alcune tecniche intense si somigliano molto.",
        "Si comincia dalle tecniche lente, pochi minuti al giorno: la costanza conta più della durata.",
    ],
    "kriya-yoga-cose-come-funziona": [
        "«Kriya yoga» indica due cose diverse: le sequenze del kundalini (kriya come esercizio) e la tradizione di meditazione detta Kriya Yoga — questa guida parla della seconda.",
        "È una via di pratica quotidiana che si riceve da un'organizzazione con un percorso di iniziazione, non uno stile da lezione settimanale.",
        "L'impegno tipico è fra i venti minuti e l'ora, una o due volte al giorno.",
        "Non richiede preparazione fisica, ma è un impegno di lungo periodo: chi cerca un primo assaggio dello yoga trova strade più leggere.",
        "Sui costi: alcune organizzazioni chiedono una quota, altre lavorano a offerta libera — chiedere la cifra completa prima di impegnarsi.",
    ],
    "come-scegliere-un-insegnante-di-yoga": [
        "«Ho provato yoga, non fa per me» quasi sempre sbaglia soggetto: non era lo yoga, era quella lezione con quella persona.",
        "Lo stile decide ritmo e forma; l'insegnante decide tutto il resto — è la scelta che pesa di più.",
        "Con una condizione fisica (ernia, ecc.): prima il medico, poi un insegnante che risponde con domande invece che con «nessun problema».",
        "Le correzioni col contatto sono legittime a una condizione: che venga chiesto prima, e che si possa dire di no senza giustificarsi.",
        "Le lezioni online funzionano per una pratica avviata, non per cominciare: all'inizio serve qualcuno che veda il tuo corpo.",
    ],
    "massaggio-olistico-tipi-cosa-aspettarsi": [
        "«Massaggio olistico» copre pratiche molto diverse: sfioramenti lenti con gli oli e pressioni shiatsu hanno in comune il lettino e poco altro.",
        "Il confine che conta: il massaggio di benessere (per persone sane, praticabile da un operatore non sanitario) è cosa diversa dal massaggio terapeutico, che è atto sanitario.",
        "Un'ora costa in genere fra i 50 e i 90 euro, con differenze fra tecniche e città.",
        "Per la prima volta: classico o californiano per rilassarsi, shiatsu per restare vestiti, deep tissue solo con tensioni croniche.",
        "In gravidanza si può, con tecniche dedicate e dopo aver sentito chi ti segue; molti operatori evitano il primo trimestre per prudenza.",
        "Commuoversi durante un massaggio è normale: è il rilassamento che scioglie ciò che era trattenuto.",
    ],
    "bagno-di-gong-sound-healing-benefici": [
        "Un bagno di gong si vive sdraiati e coperti: il suono cresce fino a sentirlo nello sterno, e all'uscita la sensazione tipica è di aver dormito una notte intera.",
        "Una sessione di gruppo costa in genere fra i 15 e i 40 euro; non ci sono limiti di frequenza.",
        "La spiegazione più ripetuta — «il suono sincronizza le onde cerebrali» — è anche la meno sostenuta: l'effetto di rilassamento è reale, la spiegazione è più semplice.",
        "Gong e campane lavorano diversamente: il gong sull'ampiezza, le campane sulla precisione e sul contatto; nei bagni sonori si usano insieme.",
        "Addormentarsi capita spesso e non è un problema.",
    ],
    "meditazione-per-chi-inizia-guida-semplice": [
        "«Non ci riesco, penso troppo» descrive una meditazione RIUSCITA: l'esercizio non è tenere la mente vuota, è accorgersi che se n'è andata e riportarla indietro.",
        "Una sessione in cui succede cinquanta volte è una sessione da cinquanta ripetizioni: le distrazioni sono il lavoro, non l'ostacolo.",
        "Non serve credere in niente: concentrazione e mindfulness restano laiche anche quando vengono da una tradizione.",
        "In una minoranza di casi la pratica intensiva può portare ansia o riemersione di materiale doloroso, quasi sempre transitori: con sessioni brevi il rischio è basso, con una storia di trauma conviene essere accompagnati.",
        "I chakra non c'entrano con la meditazione di base: sono una mappa a parte, usabile da chi la trova utile.",
    ],
    "chakra-cosa-sono-i-sette-come-si-usano": [
        "«Chakra» in sanscrito significa ruota: nelle tradizioni indica i nodi dove si incrociano i canali (nadi) di un corpo sottile percorso dal prana.",
        "Una porzione di quello che si racconta oggi in Italia sui chakra ha meno di cent'anni: l'associazione fissa con i sette colori è un'aggiunta occidentale novecentesca.",
        "La mappa funziona come strumento di attenzione: portare consapevolezza a zone del corpo ha effetti reali su come ci si sente, chiamarlo «riequilibrio dei chakra» è una scelta di vocabolario.",
        "Non servono cristalli né oggetti: nessuno studio attribuisce loro un effetto proprio.",
        "Diffida di chi promette un risultato misurabile in un numero fisso di sedute.",
    ],
    "ayurveda-cose-i-tre-dosha-cosa-aspettarsi": [
        "L'ayurveda («scienza della vita») è il sistema medico tradizionale indiano: in India è una laurea di cinque anni e mezzo e fa parte del servizio sanitario nazionale.",
        "Parte dalla persona invece che dalla malattia, e si occupa insieme di alimentazione, routine, sonno, preparati vegetali, trattamenti manuali e purificazione.",
        "Per qualsiasi preparato da ingerire serve parlarne prima col medico: alcune erbe interferiscono con anticoagulanti, antidiabetici e farmaci tiroidei.",
        "Il panchakarma è una procedura medica intensa fatta sotto supervisione: la settimana di massaggi e alimentazione leggera che molte strutture chiamano così è un'altra cosa, legittima ma con un altro nome.",
        "Si comincia dalla routine e dall'automassaggio, che non costano niente e non hanno controindicazioni; il consulto ha senso dopo.",
        "Primo consulto 80-150 euro; trattamenti come l'abhyanga 60-100 euro per circa un'ora.",
    ],
    "mindfulness-cose-mbsr-come-funziona": [
        "La mindfulness ha una data di nascita: 1979, in un ospedale universitario americano, in un programma per pazienti con dolore cronico.",
        "La definizione di Jon Kabat-Zinn è: prestare attenzione intenzionalmente, al momento presente, senza giudicare.",
        "Il protocollo MBSR vero dura otto settimane, con incontri di gruppo, pratica quotidiana e una giornata intensiva: non è una meditazione guidata di tre minuti su un'app.",
        "Gli effetti su stress percepito e sintomi d'ansia sono fra i più replicati dalla ricerca; per un disturbo diagnosticato affianca un percorso clinico, non lo sostituisce.",
        "Si comincia dallo «spazio di respiro dei tre minuti», due volte al giorno per una settimana.",
    ],
    "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini": [
        "In Occidente «yoga» è diventato sinonimo di posizioni, ma nella tradizione le posizioni sono un ramo su otto: ci sono anche respiro, etica, ritiro dei sensi, concentrazione e meditazione.",
        "Gli stili si distinguono per ritmo e intento: dinamici (vinyasa, ashtanga), lenti e lunghi (yin), didattici e precisi (iyengar), energetici (kundalini), generalisti (hatha).",
        "Praticare più stili insieme è una delle combinazioni più equilibrate: uno dinamico durante la settimana e uno lento per compensare.",
        "Due volte a settimana è la soglia sotto la quale i cambiamenti si notano poco; tre è la frequenza in cui la maggior parte delle persone sente una differenza stabile.",
        "La flessibilità è un effetto della pratica, non un requisito: il vero requisito è un insegnante che sappia adattare le posizioni al corpo che hai adesso.",
        "Conta più l'insegnante dello stile.",
    ],
    "reiki-cose-come-funziona-una-sessione": [
        "Il Reiki è una pratica di imposizione delle mani: chi conduce appoggia le mani sul corpo o le tiene a pochi centimetri, seguendo una sequenza di posizioni.",
        "Si riceve vestiti, sdraiati o seduti, e chi riceve non deve fare niente.",
        "Il nome unisce «rei» (dimensione universale) e «ki» (energia vitale), lo stesso concetto del qi cinese e del prana indiano; nella cornice della disciplina l'operatore fa da tramite, non trasmette energia propria.",
        "Non è una religione e non richiede alcuna fede: nasce in Giappone a inizio Novecento ma non prevede credenze né appartenenze.",
        "Una sessione costa in Italia fra i 40 e i 70 euro; chi cerca un percorso lavora per cicli di quattro o cinque sedute ravvicinate.",
        "Si può praticare su di sé fin dal primo livello: nella maggior parte delle scuole l'auto-trattamento quotidiano è il fondamento della pratica.",
    ],
    "mindfulness-e-meditazione-la-differenza": [
        "La meditazione è una famiglia di pratiche; la mindfulness ne è un membro — il più famoso, il più studiato, e l'unico con una data di nascita precisa.",
        "Tutta la mindfulness è meditazione, ma non tutta la meditazione è mindfulness: nella famiglia ci sono anche concentrazione, visione profonda, amorevolezza, mantra e pratiche in movimento.",
        "La meditazione ha millenni di tradizioni diverse, ognuna dentro una propria cornice di senso; la mindfulness nasce da un protocollo strutturato e laico.",
        "Non serve credere in niente per meditare: concentrazione e mindfulness restano laiche anche quando vengono da tradizioni religiose.",
        "Si comincia da cinque minuti al giorno di attenzione al respiro; il percorso di otto settimane serve a chi vuole struttura e gruppo.",
    ],
    "naturopatia-cose-consulto-cosa-dice-ricerca": [
        "La naturopatia è un approccio NON sanitario al benessere: alimentazione, stile di vita, rimedi naturali, tecniche di rilassamento.",
        "In Italia il naturopata è una professione non organizzata: nessun albo, nessun percorso di Stato, nessun titolo abilitante — la parola sulla targhetta non garantisce da sola alcuna formazione.",
        "Un consulto dura circa un'ora e ricostruisce sonno, alimentazione, digestione e stress; le analisi non convenzionali eventualmente proposte non hanno validità diagnostica.",
        "Le componenti di buon senso (mangiare meglio, dormire, gestire lo stress) fanno bene ma non sono esclusive della naturopatia; il sistema nel suo insieme ha poche prove di qualità.",
        "Nessuna cura medica si sospende o si modifica su consiglio di un naturopata, e il medico va sempre informato di erbe e integratori: un naturopata serio è il primo a dirlo.",
    ],
    "aromaterapia-cose-come-si-usa-ricerca": [
        "Gli oli essenziali sono concentrati potenti estratti dalle piante, non acque profumate: per questo le regole di diluizione non sono pignolerie.",
        "L'aromaterapia è una pratica di benessere, non una terapia, e in Italia rientra fra le discipline non sanitarie.",
        "L'olfatto si satura in fretta: l'esposizione continua al diffusore non aggiunge beneficio.",
        "Con bambini piccoli, in gravidanza e con animali servono cautele specifiche — i gatti in particolare metabolizzano queste sostanze in modo diverso.",
        "Un olio essenziale non è una fragranza: sull'etichetta si distingue dal nome botanico; se c'è scritto solo «aroma» o «profumo», è un sintetico senza uso in aromaterapia.",
    ],
    "shiatsu-cose-come-funziona-una-seduta": [
        "Lo shiatsu lavora con la pressione delle mani, senza olio e senza scorrimento: appoggia e affonda, e include stiramenti e mobilizzazioni.",
        "Usa la mappa tradizionale dei meridiani come l'agopuntura, ma con le mani invece degli aghi: in Italia l'agopuntura è atto medico, lo shiatsu no.",
        "Una seduta dura fra i 50 e i 75 minuti e costa fra i 50 e gli 80 euro.",
        "Per una tensione specifica servono in genere quattro o cinque sedute ravvicinate; per il benessere generale la frequenza più comune è una al mese.",
        "In gravidanza si può, ma con un operatore formato specificamente: cambiano le posizioni e alcuni punti vanno evitati.",
        "Non serve credere nei meridiani: l'effetto della pressione sui tessuti e sul sistema nervoso non dipende da cosa si crede.",
    ],
    "yoga-nidra-cose-come-funziona-una-sessione": [
        "Lo yoga nidra si pratica sdraiati sulla schiena, senza fare niente con il corpo: si segue solo la voce di chi conduce.",
        "Una pratica dura fra i venti e i quarantacinque minuti; venti è la durata più comune per cominciare.",
        "È l'unica pratica dello yoga in cui addormentarsi non è un errore, e capita spesso le prime volte.",
        "Non è una meditazione guidata: quella si fa seduti e chiede di mantenere l'attenzione, lo yoga nidra ammette il sonno e segue fasi codificate.",
        "Non richiede prerequisiti: è la pratica dello yoga che ne chiede meno di tutte, e si incontra anche senza aver mai fatto una posizione.",
        "Due o tre volte a settimana è la frequenza in cui la maggior parte delle persone nota un cambiamento sul sonno.",
    ],
    "campane-tibetane-benefici-come-funzionano": [
        "Le campane tibetane sono ciotole di metallo himalayane che si percuotono con un battente o si sfregano sul bordo, da cui il nome inglese singing bowls.",
        "Ogni campana produce una nota fondamentale e una famiglia di armonici: è questo a rendere il suono così pieno.",
        "La storia va corretta: erano in larga parte oggetti d'uso quotidiano, l'impiego terapeutico si afferma in Occidente nel Novecento e la «lega dei sette metalli» è un racconto commerciale.",
        "Rispetto al gong la differenza è netta: il gong sommerge di frequenze, la campana accompagna con precisione.",
        "Non richiede credenze né sforzo, e non ci sono limiti di frequenza: molti lo vivono come un appuntamento mensile.",
        "Una sessione individuale costa in genere fra i 40 e i 70 euro.",
    ],
    "breathwork-cose-tecniche-benefici": [
        "Sotto il nome «breathwork» convivono due famiglie che fanno cose opposte, e sapere in quale si entra è la cosa più utile.",
        "Le tecniche di regolazione (diaframmatica, coerenza cardiaca, respiro quadrato, buona parte del pranayama) rallentano il respiro e abbassano l'attivazione: adatte a quasi tutti, si praticano da soli.",
        "Le tecniche esperienziali (respirazione circolare connessa, olotropica, rebirthing) amplificano il respiro a lungo e portano a stati di coscienza non ordinari: richiedono un facilitatore e hanno controindicazioni precise.",
        "L'irrigidimento delle mani durante una sessione intensa è alcalosi respiratoria: temporaneo, meccanico e reversibile rallentando il respiro — non è un blocco che si scioglie.",
        "Il breathwork non sostituisce la psicoterapia: chi conduce una sessione non è un terapeuta.",
        "Una sessione di gruppo costa in genere fra i 25 e i 60 euro.",
    ],

    # ── scegliere (guida del consumatore: il nostro territorio) ───────
    "come-capire-se-un-operatore-olistico-e-serio": [
        "In Italia non esiste un albo delle professioni olistiche: nessun esame di Stato, nessun ente pubblico che verifichi la competenza.",
        "La legge 4/2013 impone però una cosa verificabile: chi esercita deve dichiararlo in ogni documento e comunicazione al pubblico.",
        "Le sigle delle associazioni non sono titoli abilitanti: sono adesioni private, e si controllano una per una.",
        "Il segnale più affidabile per allontanarsi è chi promette guarigioni: una pratica di benessere non cura le malattie.",
        "La disponibilità a una chiamata preliminare di dieci minuti è già una risposta sulla serietà di chi hai davanti.",
    ],
    "primo-colloquio-operatore-olistico": [
        "Il primo incontro fatto bene è soprattutto una conversazione: nelle pratiche serie c'è un colloquio prima di qualsiasi altra cosa.",
        "Chi ti mette sul lettino dopo due minuti sta evadendo un appuntamento; chi ti fa domande sta facendo il mestiere.",
        "Nelle pratiche corporee il contatto si nomina e si concorda PRIMA: se arriva senza che ne abbiate parlato, hai il diritto di fermare tutto, anche a metà sessione.",
        "Se non ti convince, basta una riga il giorno dopo: nessuna spiegazione è dovuta e nessun professionista serio la pretende.",
        "Un professionista può dirti di no, e quando succede è quasi sempre un buon segno.",
    ],
    "come-scegliere-un-ritiro": [
        "La scelta parte dalla fine: non «quale ritiro è bello» ma «cosa voglio che sia successo quando torno a casa».",
        "Chi cerca riposo ha bisogno di poca struttura e di tempo vuoto difeso nel programma: una giornata piena dalle sette alle ventuno riporta a casa più stanchi di prima.",
        "Chi vuole imparare una pratica deve guardare chi insegna, non il posto: ore di pratica vere, formazione leggibile, gruppo piccolo.",
        "Un ritiro di quattro giorni in Italia costa in genere fra i 400 e i 1.500 euro.",
        "Prima di confrontare i prezzi si confronta cosa includono: sistemazione, pasti, dimensione del gruppo e conduzione spiegano quasi tutta la differenza.",
        "Per la maggior parte dei ritiri non serve esperienza, e un programma serio lo dice chiaramente prima della caparra.",
    ],
    "domande-da-fare-prima-di-prenotare-un-ritiro": [
        "Un ritiro è una delle spese meno reversibili che si fanno per il proprio benessere: chiede soldi, ferie e fiducia per giorni interi.",
        "Chiedere non è diffidenza: chi organizza da anni ha già le risposte pronte, e chi si irrigidisce davanti a una domanda semplice ti sta dando l'informazione più utile della conversazione.",
        "Sui soldi si chiede il prezzo finale (IVA, tassa di soggiorno, quote associative comprese) e cosa resta fuori.",
        "Dieci minuti di telefono dicono più di dieci email, e la disponibilità stessa è una risposta.",
        "Il prezzo si confronta su cosa include: alloggio in singola, pasti e transfer non sono paragonabili alle sole sessioni.",
    ],
    "discipline-olistiche-la-mappa": [
        "È la mappa delle discipline olistiche: per ognuna cosa è, cosa si sente, cosa dice la ricerca e quanto costa.",
        "Nessuna di queste pratiche sostituisce le cure mediche: chi le presenta come cure sta facendo un'altra cosa.",
        "Le professioni olistiche in Italia sono professioni non organizzate regolate dalla legge 4/2013: si esercitano liberamente, con obblighi di trasparenza verso il cliente.",
        "Si comincia da una pratica semplice fatta con costanza, non dalla disciplina più affascinante: quindici minuti al giorno dicono più di qualunque descrizione.",
    ],
    "quanto-costano-pratiche-olistiche": [
        "Sedute individuali in Italia: reiki 40-70 €, shiatsu 50-80 €, massaggio olistico 50-90 € l'ora.",
        "Ayurveda: primo consulto 80-150 €, trattamenti come l'abhyanga 60-100 € per circa un'ora.",
        "Pratiche di gruppo: lezione di yoga 10-20 € (abbonamento mensile 50-80 €), bagno di gong 15-40 €, breathwork 25-60 €, cerchi di donne 10-30 €.",
        "Campane tibetane in sessione individuale: 40-70 €.",
        "Sono forchette reali, non listini: dentro ognuna pesano città, durata ed esperienza di chi conduce.",
        "Il prezzo dice quanto costa, non quanto vale: per il valore servono altre domande.",
    ],
}


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prova", action="store_true")
    g.add_argument("--esegui", action="store_true")
    ap.add_argument("--solo", default=None,
                    help="slug separati da virgola")
    ap.add_argument("--sovrascrivi", action="store_true",
                    help="rifà anche gli articoli che ce l'hanno già "
                         "(default: si salta chi è stato rivisto a mano)")
    args = ap.parse_args()

    from database import db
    from models.common import utc_now

    voluti = (set(args.solo.split(",")) if args.solo else set(IN_BREVE))
    scritti = saltati = mancanti = 0

    for slug in sorted(voluti):
        righe = IN_BREVE.get(slug)
        if not righe:
            print(f"  ?  {slug}: nessun testo pronto")
            mancanti += 1
            continue
        doc = await db.articles.find_one({"slug": slug},
                                         {"_id": 0, "in_breve": 1, "title": 1})
        if not doc:
            print(f"  !  {slug}: articolo non trovato")
            mancanti += 1
            continue
        # chi l'ha già NON si tocca: potrebbe essere stato riscritto
        # dalla redazione, e sovrascriverlo in silenzio sarebbe il modo
        # più rapido di perdere un lavoro fatto a mano
        if (doc.get("in_breve") or "").strip() and not args.sovrascrivi:
            print(f"  =  {slug}: ha già un «In breve», lasciato com'è")
            saltati += 1
            continue
        testo = "\n".join(righe)
        if args.esegui:
            await db.articles.update_one(
                {"slug": slug},
                {"$set": {"in_breve": testo, "updated_at": utc_now()}})
        print(f"  +  {slug}  ({len(righe)} righe)")
        scritti += 1

    print(f"\n{'PROVA — nulla scritto' if args.prova else 'SCRITTI'}: {scritti}"
          f" · già presenti: {saltati} · non pronti: {mancanti}")
    print(f"Testi pronti nello script: {len(IN_BREVE)} su 47 articoli.")
    if args.esegui and scritti:
        print("\nORA: rivedili in /admin → Blog. Sono bozze tratte dagli "
              "articoli,\nnon parole nuove: ma la voce finale è della "
              "redazione.")


if __name__ == "__main__":
    asyncio.run(main())
