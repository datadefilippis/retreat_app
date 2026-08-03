"""ES5 — tema natale e digiuno: gli ultimi due magri rivolti ai lettori.

TEMA NATALE (858 → ~1500). Era ancora scritto DA un'astrologa: "la
domanda che ricevo piu' spesso quando dico che leggo i temi natali",
"l'approccio con cui lavoro", "mi invii i tuoi dati di nascita e
preparo la carta", e una descrizione che diceva "Il racconto di chi
legge i cieli". Il mio filtro l'aveva mancata due volte perche'
cercavo formule diverse; alla fine di questo script ne uso uno molto
piu' largo.

Manca poi tutto l'impianto: pianeti, segni, case, aspetti, e i tre
elementi che tutti cercano — Sole, Luna, Ascendente. E manca la cosa
che un articolo onesto su questo tema deve contenere: lo studio in
doppio cieco di Shawn Carlson pubblicato su Nature nel 1985, in cui
gli astrologi non hanno saputo abbinare le carte natali ai profili di
personalita' meglio del caso. Dirlo non impedisce di raccontare
perche' una lettura fa bene lo stesso: impedisce di spacciarla per
un'altra cosa.

DIGIUNO (769 → ~1400). Manca cosa succede nel corpo, mancano i tipi di
digiuno — compreso il mimadigiuno di Valter Longo, che e' italiano e
molto cercato — e manca soprattutto LA SINDROME DA RIALIMENTAZIONE:
gli spostamenti di elettroliti che possono seguire la ripresa
dell'alimentazione dopo un digiuno prolungato, potenzialmente gravi.
E' il rischio piu' serio di tutta questa materia e in italiano, fuori
dalla letteratura clinica, non lo nomina quasi nessuno.

    venv/bin/python scripts/es5_espansione_tema_e_digiuno.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

TEMA = "lettura-tema-natale-cosa-aspettarsi"
DIGIUNO = "digiuno-consapevole-detox-benefici-falsi-miti"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
TAROCCHI = "/blog/tarocchi-oracoli-strumento-evolutivo"
AYU = "/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
CIBO = "/blog/alimentazione-ayurvedica-principi-sei-sapori"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"

TITOLO_T = "Lettura del tema natale: cos'è, come funziona, cosa aspettarsi"
DESCR_T = (
    "Come è fatta una carta natale, Sole Luna e Ascendente, come si svolge "
    "un consulto, cosa dice la ricerca e come si sceglie chi la legge."
)

CONTENUTO_T = f"""\
«Ma quindi mi dici il futuro?» È la domanda che chi legge i temi natali riceve più spesso. La risposta, che sorprende quasi tutti, è no: una lettura del tema natale non predice, racconta. E quello che racconta sei tu.

Questa guida spiega com'è fatta una carta, cosa succede in un consulto, come si sceglie chi lo conduce, e cosa dice la ricerca — che è una parte di solito assente e che vale la pena leggere fino in fondo.

## Cos'è il tema natale

È la fotografia del cielo nel momento esatto della nascita: dove si trovavano il Sole, la Luna e i pianeti, e come si disponevano rispetto al luogo in cui sei venuto al mondo.

Servono tre dati: **data, ora esatta e luogo**. L'ora è quella che pesa di più — bastano pochi minuti di differenza per cambiare l'ascendente, e quindi buona parte della lettura.

Nell'astrologia evolutiva, che è l'approccio diffuso oggi in Italia, questa mappa non è un destino scritto ma un linguaggio simbolico per esplorare inclinazioni, nodi e potenzialità. I pianeti sono archetipi, non sentenze.

## Come è fatta una carta

Quattro elementi, e sapere cosa sono rende una lettura molto più comprensibile.

**I pianeti — il *cosa*.** Dieci corpi celesti, ognuno associato a una funzione psichica. Il Sole è l'identità e la direzione, la Luna il mondo emotivo e i bisogni, Mercurio il pensiero e la parola, Venere il modo di amare e di valutare, Marte l'azione e la rabbia, Giove l'espansione e il senso, Saturno il limite e la responsabilità. I tre lenti — Urano, Nettuno, Plutone — si muovono così adagio da riguardare intere generazioni più che il singolo.

**I segni — il *come*.** I dodici segni zodiacali colorano il modo in cui ogni pianeta si esprime. Marte in Ariete agisce di slancio, Marte in Bilancia agisce dopo aver soppesato.

**Le case — il *dove*.** Dodici settori che indicano gli ambiti di vita: il corpo e l'immagine, i beni, la comunicazione, la casa e le origini, e così via. Un pianeta in una casa dice in quale zona della vita quel tema si gioca.

**Gli aspetti — le *relazioni*.** Gli angoli fra i pianeti. Alcuni indicano scorrevolezza, altri attrito. Nella lettura evolutiva l'attrito è la parte interessante: è lì che di solito sta il lavoro.

## Sole, Luna e Ascendente

Sono i tre che si cercano per primi, e sono anche i più utili da capire.

**Il Sole** è il segno dell'oroscopo, quello che tutti conoscono. Indica la direzione che si sta imparando a percorrere, più che quello che si è già.

**La Luna** è la vita emotiva: come ci si consola, di cosa si ha bisogno, come si reagisce quando si è stanchi. Molte persone si riconoscono più nella Luna che nel Sole, ed è una delle scoperte più frequenti di una prima lettura.

**L'Ascendente** è il segno che sorgeva all'orizzonte all'ora della nascita: il modo in cui ci si presenta al mondo e si affrontano le cose nuove. È quello che richiede l'ora esatta, ed è il motivo per cui l'ora conta.

Sole, Luna e Ascendente insieme raccontano già una figura riconoscibile. Il resto della carta la articola.

## Come si svolge una lettura

**Prima.** Si inviano i dati di nascita e chi legge prepara la carta: è uno studio che avviene prima dell'incontro. Un consulto serio non si improvvisa.

**L'incontro.** Dura in genere fra i 60 e i 90 minuti, di persona o online. Non è un monologo: è un dialogo. Chi conduce racconta quello che la carta suggerisce, tu riconosci o non riconosci quei temi. È in questo scambio che la lettura prende senso, ed è il motivo per cui una lettura registrata e spedita vale molto meno di un incontro.

**Cosa si esplora.** L'energia vitale, il mondo emotivo, il modo di amare e di agire, dove si tende a ripetere schemi e dove la carta suggerisce direzioni. In chiave evolutiva l'attenzione va ai nodi: i punti di tensione che, letti bene, diventano leve.

**Dopo.** Molti lasciano una registrazione o una sintesi scritta. I temi emersi continuano a lavorare nei giorni successivi.

## I transiti, e il ritorno di Saturno

Oltre alla carta di nascita, che non cambia mai, esiste il movimento dei pianeti nel cielo di oggi rispetto a quella carta: sono i **transiti**, ed è il motivo per cui alcune persone tornano da chi legge in momenti specifici.

Il più noto è il **ritorno di Saturno**: Saturno impiega circa ventinove anni a completare il giro, quindi intorno ai ventotto o trent'anni torna dove stava alla nascita, e di nuovo verso i cinquantotto. Nella tradizione astrologica coincide con un periodo di resa dei conti e di assunzione di responsabilità.

Va detto con precisione: è una **coincidenza narrativa efficace**, non un meccanismo dimostrato. Che intorno ai trent'anni molte persone rivedano la propria vita è un fatto sociologico prima che astronomico.

## Cosa dice la ricerca

Qui va detta la cosa per intero, perché è la parte che di solito manca.

**L'astrologia non ha validazione scientifica.** Non è un'opinione: è stata messa alla prova.

Lo studio più noto è di **Shawn Carlson, pubblicato su *Nature* nel 1985**. Disegnato in doppio cieco e concordato in anticipo con astrologi professionisti, chiedeva loro di abbinare carte natali a profili di personalità ottenuti con un test standardizzato. Il risultato: **non hanno fatto meglio del caso**. Altri lavori successivi sono arrivati a conclusioni analoghe.

Perché allora una lettura fa spesso un'impressione forte? Le ragioni sono le stesse dei [tarocchi]({TAROCCHI}), e sono interessanti di per sé.

**L'effetto Barnum.** Ci si riconosce in descrizioni abbastanza generali da valere per molti, perché ci mettiamo dentro il nostro materiale.

**La ricchezza del sistema.** Una carta contiene decine di elementi combinabili: chi legge sceglie, spesso in buona fede, quelli che risuonano con la persona che ha davanti.

**Un'ora dedicata a te.** Sessanta minuti in cui qualcuno parla di te con attenzione e tu ti racconti sono un'esperienza rara, e producono un effetto reale a prescindere dallo strumento.

Questo non toglie valore alla lettura come **strumento simbolico di auto-esplorazione** — funziona quando apre consapevolezza. Toglie valore a chi la vende come conoscenza predittiva. Chi la pratica con serietà questa distinzione la fa da solo, ed è il primo criterio con cui riconoscerlo.

## A cosa serve, e a cosa no

**Serve a** vedersi da un'angolazione nuova, dare un nome a dinamiche che si sentono da sempre senza saperle formulare, orientarsi nei momenti di passaggio, aprire domande su cui lavorare.

**Non serve a** predire il futuro, prendere decisioni al posto tuo, sostituire un percorso terapeutico, dire chi sposare o quando cambiare casa.

E non serve mai a decidere di salute. Nessuna carta dice se fare un esame, un intervento o una terapia.

## Come si trova l'ora esatta di nascita

È la domanda pratica più frequente, e ha una risposta semplice.

L'ora è registrata nell'**atto di nascita**, conservato dal Comune dove sei nato. Si richiede un **estratto dell'atto di nascita**, che a differenza del certificato riporta anche l'ora; molti Comuni permettono di farlo online o via posta elettronica, gratuitamente.

Il cartellino dell'ospedale o il libretto della nascita spesso la riportano. La memoria dei genitori è il dato meno affidabile: gli scarti di mezz'ora sono frequentissimi.

Senza ora si può comunque lavorare, con una carta parziale: mancano l'ascendente e le case, cioè una parte consistente.

## Come si sceglie chi legge

**Chiede l'ora esatta.** Chi legge un tema con la sola data sta lavorando su una carta incompleta.

**Non promette previsioni.** Il linguaggio serio parla di tendenze, archetipi e domande; quello commerciale parla di scoprire cosa accadrà.

**Dice che l'astrologia non è una scienza.** Chi la presenta come dimostrata sta dicendo il falso, e su questo non ci sono scuole di pensiero.

**Non tocca salute, denaro e decisioni legali.**

**Ti lascia libero.** Un buon consulto si chiude senza agganci: niente ritorni mensili, niente paure indotte.

Una lettura in Italia costa fra i 60 e i 120 euro. Valgono anche i [criteri generali]({SERIO}).

## Domande frequenti

**Serve sapere l'ora esatta di nascita?**
Il più possibile. La trovi nell'estratto dell'atto di nascita del Comune. Senza, si lavora su una carta parziale, priva di ascendente e case.

**L'astrologia è scientificamente provata?**
No. Le verifiche controllate, a partire dallo studio di Carlson pubblicato su Nature nel 1985, non hanno trovato risultati migliori del caso. Il valore di una lettura sta altrove.

**Che differenza c'è con l'oroscopo?**
L'oroscopo dei giornali usa solo il segno solare, uguale per un dodicesimo dell'umanità. Il tema natale è calcolato sul minuto e sul luogo della tua nascita.

**Online o di persona?**
La qualità dipende dalla preparazione di chi legge, non dal mezzo. Online si accede a consulenti di tutta Italia.

**Ogni quanto ha senso una lettura?**
La carta natale non cambia: una lettura approfondita può bastare per anni. Hanno senso ritorni mirati nei momenti di passaggio, non appuntamenti mensili.

**Cos'è il ritorno di Saturno?**
Il momento, intorno ai ventinove anni e poi ai cinquantotto, in cui Saturno torna dove stava alla nascita. Nella tradizione coincide con un periodo di resa dei conti; è una narrazione efficace, non un meccanismo dimostrato.

**Posso leggermi la carta da solo?**
I calcoli sono gratuiti online e i tre elementi principali si imparano. L'interpretazione d'insieme è un'altra cosa, e come per i [tarocchi]({TAROCCHI}) lo sguardo esterno vede quello che il proprio punto cieco copre.
"""

TITOLO_D = "Digiuno e detox: cosa succede nel corpo, benefici, controindicazioni"
DESCR_D = (
    "Il mito delle tossine, i tipi di digiuno, cosa succede davvero nel "
    "corpo, la rialimentazione e come si sceglie un ritiro serio."
)

CONTENUTO_D = f"""\
Poche parole del mondo benessere sono state maltrattate quanto «detox». Fra tisane miracolose, succhi che puliscono il fegato e promesse di purificazione in quarantott'ore, il marketing ha sepolto una pratica che ha una sua dignità antica e moderna: fermarsi, alleggerire, dare tregua al corpo e alla mente.

Questa guida separa quello che succede da quello che viene raccontato.

## Il falso mito da cui partire

L'idea che il corpo accumuli **tossine** misteriose che solo succhi e tisane possono eliminare non ha basi. Fegato e reni fanno questo lavoro ogni giorno, gratis, meglio di qualsiasi beverone. Nessun alimento purifica: se un prodotto promette di detossificare, stai leggendo marketing.

E allora perché un ritiro detox può avere senso? Perché il valore non è biochimico, **è comportamentale**. Qualche giorno di alimentazione essenziale, senza alcol, caffeina, zuccheri e cibo industriale, dentro un contesto di riposo, è una pausa che il corpo riconosce subito. Non stai eliminando tossine: stai togliendo carico. E la differenza si sente.

## I tipi di digiuno

Sotto la stessa parola stanno pratiche molto diverse per rischio e per evidenze.

**Digiuno intermittente a finestra.** Il più diffuso: si concentra l'alimentazione in otto ore e si digiuna nelle sedici restanti, oppure varianti simili. Nella pratica, per molti significa saltare la colazione o cenare presto.

**Cinque e due.** Cinque giorni di alimentazione normale e due a forte restrizione calorica.

**Digiuno prolungato.** Oltre le ventiquattro o quarantotto ore. È un'altra categoria, con rischi propri, e non è una pratica da fai da te.

**Mimadigiuno.** Un protocollo di pochi giorni con alimentazione molto ridotta e composizione controllata, studiato per ottenere alcuni effetti del digiuno continuando a mangiare. È stato sviluppato dal gruppo di ricerca di Valter Longo, fra Stati Uniti e Italia, ed è oggetto di studi in corso.

## Cosa succede nel corpo

Le prime ore sono le più fraintese, e conoscerle toglie ansia.

**Fino a circa dodici ore.** Il corpo usa il glucosio disponibile e le riserve di glicogeno del fegato. È la fase in cui compare la fame per abitudine, che passa.

**Fra le dodici e le ventiquattro ore.** Il glicogeno si esaurisce e il metabolismo si sposta progressivamente sui grassi. È qui che chi consuma molta caffeina e zuccheri incontra mal di testa e irritabilità: è una sospensione, non una purificazione, ed è nota e gestibile.

**Oltre le ventiquattro ore.** La produzione di corpi chetonici aumenta e diventa la fonte energetica principale, cervello compreso. Molte persone riferiscono lucidità; altre stanchezza. Da qui in poi, senza supervisione, non si va.

Quello che **non** succede è l'espulsione di sostanze accumulate. È il punto su cui il marketing insiste di più e quello con meno fondamento.

## La rialimentazione, che è la parte pericolosa

Questa sezione riguarda la sicurezza e in italiano, fuori dai testi clinici, non la scrive quasi nessuno.

Dopo un digiuno prolungato, **il momento più rischioso non è il digiuno: è la ripresa**. Reintrodurre cibo, in particolare carboidrati, provoca uno spostamento rapido di elettroliti — fosforo, potassio, magnesio — dal sangue alle cellule. Nei casi seri questo quadro, che in medicina si chiama **sindrome da rialimentazione**, può portare a complicanze cardiache e neurologiche, e può essere fatale.

Riguarda soprattutto chi è denutrito, chi ha una storia di disturbi alimentari, chi ha digiunato a lungo, chi abusa di alcol, gli anziani.

La conseguenza pratica è netta: **un digiuno prolungato serio prevede una rialimentazione graduata e sorvegliata**, che dura almeno quanto il digiuno. Un ritiro che propone giorni di digiuno e poi una cena di gruppo abbondante l'ultima sera non sa cosa sta facendo.

## Cosa dice la ricerca

**Sul digiuno intermittente.** Gli studi sono numerosi e i risultati più modesti di come vengono raccontati: sul calo di peso i risultati sono in genere **equivalenti a quelli della semplice restrizione calorica**, cioè funziona per chi con quello schema mangia meno, non per una magia metabolica. Su alcuni marcatori — glicemia a digiuno, sensibilità insulinica, profilo lipidico — emergono effetti in una parte degli studi, con eterogeneità alta.

**Sul digiuno prolungato e sul mimadigiuno.** La ricerca è attiva e interessante, in particolare su marcatori metabolici e infiammatori, e in gran parte ancora su campioni piccoli o su modelli animali. Promettente non significa dimostrato.

**Sui ritiri detox.** Nessuno studio sostiene che eliminino tossine, curino patologie o producano dimagrimenti stabili. Quello che è ragionevole aspettarsi è l'effetto di alcuni giorni di riposo, alimentazione leggera e assenza di alcol e stimolanti — che è un effetto reale.

## Cosa succede in un ritiro detox serio

**L'alimentazione.** Cucina vegetale leggera, a volte fasi di soli liquidi per chi le sceglie. I ritiri seri graduano: giorni di avvicinamento, fase centrale, reintroduzione dolce.

**Il contesto.** Il cibo è metà dell'esperienza; l'altra metà è il ritmo. Yoga dolce, camminate, riposo vero, pochi schermi, sonno abbondante. È il pacchetto a fare l'effetto, non il succo verde.

**L'accompagnamento.** Personale che sa cosa sta facendo, colloquio iniziale sulle condizioni di salute, flessibilità, attenzione ai segnali.

## Le domande da fare prima di prenotare

Se un ritiro propone digiuni oltre le ventiquattro o quarantotto ore, queste sono precise.

1. **Chi supervisiona?** C'è personale con formazione sanitaria?
2. **C'è uno screening iniziale** serio delle condizioni di salute?
3. **Come è gestita la rialimentazione**, e quanto dura?
4. **Cosa succede se sto male?**

Risposte vaghe significano ritiro da evitare. Le domande generali da fare prima di prenotare qualsiasi ritiro stanno [qui]({DOMANDE}).

## Controindicazioni

Il digiuno è controindicato, o richiede il via libera del medico, in caso di:

- **Gravidanza e allattamento**
- **Disturbi del comportamento alimentare**, presenti o passati — ed è la controindicazione più importante di tutte, perché il digiuno può riattivare uno schema
- **Diabete in trattamento**, soprattutto con insulina o farmaci che abbassano la glicemia
- **Età inferiore ai diciotto anni** e età avanzata
- **Sottopeso o denutrizione**
- **Patologie renali, epatiche o cardiache**
- **Terapie farmacologiche** che richiedono assunzione con cibo o glicemie stabili

Il parere del medico prima di prenotare non è un consiglio prudente: è il requisito.

## I benefici che puoi aspettarti

Da un ritiro ben fatto: sonno che migliora già dalla seconda notte, palato che si risveglia, energia più stabile senza le montagne russe di zuccheri e caffè, una relazione più consapevole con la fame vera e quella nervosa. Molti tornano a casa con una o due abitudini cambiate stabilmente, ed è questo l'effetto che dura.

Cosa non aspettarsi: dimagrimenti stabili in cinque giorni — i chili persi sono in gran parte acqua — guarigioni, purificazioni.

## Quanto costa e come scegliere

In Italia un weekend parte da circa 300 euro, una settimana va dai 700 ai 1.500 e oltre, in base a struttura e livello di accompagnamento. Il personale qualificato costa, ed è la voce che vale.

Valgono le [regole di sempre]({SERIO}): chi conduce ha nome e storia, il programma è scritto, le condizioni sono chiare prima del pagamento.

Un sistema che sul tema della purificazione ha una posizione molto più articolata è l'[ayurveda]({AYU}), dove il panchakarma è una procedura medica e non un pacchetto benessere, e dove [l'alimentazione]({CIBO}) è un impianto a sé.

## Domande frequenti

**Il ritiro detox fa dimagrire?**
Nei giorni del ritiro sì, ma in gran parte è acqua. Il valore è il cambio di abitudini, che può portare a effetti duraturi.

**Starò male i primi giorni?**
Chi consuma molta caffeina e zuccheri può attraversare ventiquattro o quarantott'ore di mal di testa e stanchezza da sospensione: è noto e gestibile, e i ritiri seri preparano.

**Il digiuno intermittente funziona?**
Per il calo di peso funziona quanto la restrizione calorica: è utile se con quello schema mangi meno. Su alcuni marcatori metabolici ci sono risultati, con studi eterogenei.

**Posso farlo se prendo farmaci?**
Solo dopo aver parlato col tuo medico. Alcuni farmaci richiedono assunzione con cibo o glicemie stabili, e nessun facilitatore può sostituire quella valutazione.

**Che differenza c'è fra detox e digiuno terapeutico?**
Il primo è alleggerimento alimentare in contesto di benessere; il secondo è una pratica clinica in strutture specializzate con supervisione medica continua. Confonderli è l'errore più pericoloso del settore.

**Qual è il rischio maggiore?**
La rialimentazione dopo un digiuno prolungato, per gli spostamenti di elettroliti che comporta. È il motivo per cui il digiuno lungo non si improvvisa.

**Posso digiunare se ho avuto un disturbo alimentare?**
È la situazione in cui la risposta è no senza una valutazione clinica: il digiuno può riattivare uno schema anche a distanza di anni.
"""

PEZZI = [
    (TEMA, TITOLO_T, DESCR_T, CONTENUTO_T,
     ["tarocchi-oracoli-strumento-evolutivo",
      "come-capire-se-un-operatore-olistico-e-serio",
      "costellazioni-familiari-cosa-sono-come-funzionano"]),
    (DIGIUNO, TITOLO_D, DESCR_D, CONTENUTO_D,
     ["ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
      "alimentazione-ayurvedica-principi-sei-sapori",
      "domande-da-fare-prima-di-prenotare-un-ritiro"]),
]

# IL FILTRO. Prima versione sbagliata e vale la pena scriverlo: cercavo
# i verbi nudi di prima persona (lavoro, suono, uso, noto, tratto,
# vedo) e in italiano quelle sono anche parole comunissime. Sessantacinque
# risultati, quasi tutti sostantivi: "il lavoro degli operatori", "un
# suono avvolgente", "erbe di uso alimentare".
#
# Anche la seconda versione aveva due buchi, trovati rileggendo i suoi
# quattro risultati: "che seguo" matchava dentro "che seguono" (manca
# il confine di parola) e "da chi legge" prendeva una terza persona
# perfettamente legittima. Un rilevatore che segnala il falso e' un
# rilevatore a cui si smette di credere, quindi valeva chiuderli.
#
# La versione che funziona non cerca il verbo, cerca il MARCATORE che
# rende la frase una rivendicazione: il pronome, la particella, il
# possessivo, la relativa, l'autopresentazione. Sono le forme in cui i
# casi veri si erano nascosti — "me compresa", "mi invii i tuoi dati",
# "l'approccio con cui lavoro", "la domanda che ricevo" — e nessuna
# delle due versioni le avrebbe prese tutte cercando i verbi.
PRIMA_PERSONA = re.compile(
    r"(?<![\w'’])("
    r"io\s+\w+|me compres|mi (?:invii|invia|scrivi|scrivono|contatt|chied)|"
    r"la mia (?:pratica|esperienza|formazione|clientela|sala|scuola)|"
    r"il mio (?:studio|percorso|metodo|lavoro)|"
    r"i miei (?:clienti|pazienti|allievi|percorsi)|"
    r"le mie (?:client|allieve|sessioni)|"
    r"(?:con cui|in cui) (?:lavoro|pratico|insegno)|"
    r"che (?:seguo|accompagno|ricevo|conduco|tratto)\\b|"
    r"(?:sono|faccio) (?:un'|un |la |il )?(?:operatric|operator|facilitatric|"
    r"facilitator|insegnant|astrolog|terapeut)|"
    r"racconto di (?:una|un)\s|guida di (?:una|un)\s|"
    r"da chi (?:li|le|lo) (?:legge|suona|pratica|conduce)"
    r")", re.I)


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto, correlati in PEZZI:
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not doc:
            print(f"ASSENTE: {slug}")
            continue
        print(f"{titolo}\n  prima: {len(doc['content'].split())} parole"
              f"  →  dopo: {len(contenuto.split())} parole"
              f"  (descrizione {len(descr)} caratteri)")
        if contenuto == doc["content"]:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya", "related_slugs": correlati,
            "updated_at": datetime.now(timezone.utc)}})
        print("  aggiornato")

    print("\n── il filtro largo su tutto il Magazine")
    n = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1,
                                         "description": 1}):
        t = a["content"] + "\n" + (a.get("description") or "")
        for h in PRIMA_PERSONA.finditer(t):
            i = max(0, h.start() - 60)
            print(f"  {a['slug'][:30]:32} …{t[i:h.end() + 60]}…"
                  .replace("\n", " "))
            n += 1
    print(f"  occorrenze: {n or 'nessuna'}")

    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    magri = [(a["slug"], len(a["content"].split())) for a in arts
             if len(a["content"].split()) < 900]
    print(f"\n  link rotti: {rotti or 'nessuno'}")
    print(f"  sotto le 900 parole: {magri or 'nessuno'}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
