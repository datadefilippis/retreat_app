"""ES2 — il cluster suono: due pezzi magri e in prima persona.

IL DIFETTO PIU' GRAVE non era la lunghezza. Erano scritti da una
praticante: "le persone che accompagno descrivono", "ricordo di
essermi sdraiata scettica", "chiedi alla me di qualche anno fa", e una
meta descrizione che dice "Guida di un'operatrice" — cioe' una riga
che compare nei risultati di ricerca e in cui Aurya rivendica di
suonare le campane. E' lo stesso difetto corretto sul reiki e sul
breathwork, rimasto in altri due posti.

COSA SI AGGIUNGE, ed e' la parte per cui vale la pena riscriverli.

Sulle CAMPANE, due cose che in italiano non le scrive quasi nessuno.
La lega dei sette metalli associati ai sette pianeti e' un racconto da
mercato turistico: le analisi delle ciotole antiche trovano bronzo,
cioe' rame e stagno, con tracce variabili. E soprattutto: nelle
regioni himalayane queste ciotole erano oggetti d'uso domestico, e il
loro impiego come strumenti di guarigione sonora e' in gran parte una
costruzione occidentale del Novecento. Non toglie nulla all'esperienza
del trattamento, toglie una pretesa di antichita' che serve a vendere.

Sul GONG, il gong da sala e' uno strumento orchestrale occidentale
contemporaneo, e va detto perche' viene presentato come antico. E la
storia del "trascinamento delle onde cerebrali", che circola come
spiegazione scientifica del bagno sonoro, poggia su basi molto piu'
deboli di come viene raccontata.

    venv/bin/python scripts/es2_espansione_suono.py [--dry-run]
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

CAMPANE = "campane-tibetane-benefici-come-funzionano"
GONG = "bagno-di-gong-sound-healing-benefici"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"
NIDRA = "/blog/yoga-nidra-cose-come-funziona-una-sessione"

TITOLO_C = "Campane tibetane: cosa sono, come funzionano, cosa si prova"
DESCR_C = (
    "Come sono fatte, da dove vengono per davvero, come si svolge un "
    "trattamento, la differenza con il cristallo e cosa dice la ricerca."
)

CONTENUTO_C = f"""\
La prima cosa che sorprende di una campana tibetana non è il suono: è quanto dura. Si colpisce il bordo, e la vibrazione continua, si trasforma, respira per decine di secondi. La seconda sorpresa arriva quando la campana suona appoggiata sul corpo, e la vibrazione non si sente con le orecchie ma con la schiena, il petto, le mani.

Questa guida racconta cosa sono, da dove vengono, come si svolge un trattamento e cosa aspettarsi. Compresa una parte che nei negozi non si racconta.

## Cosa sono

Le campane tibetane, o ciotole armoniche, sono ciotole di metallo originarie dell'area himalayana. Si suonano in due modi: percuotendole con un battente, e allora il suono si espande e poi decade lentamente, oppure sfregandone il bordo con un movimento circolare continuo, che genera il canto ininterrotto da cui viene il nome inglese *singing bowls*.

Ogni campana ha una voce sua. Dimensione, spessore, forma del bordo e composizione della lega determinano la frequenza fondamentale e la ricchezza degli armonici, cioè le note secondarie che la campana produce insieme a quella principale. È la loro presenza a rendere il suono così pieno: una campana non emette una nota, ne emette una famiglia.

Chi lavora con il suono usa in genere un insieme di campane, dalle piccole e squillanti alle grandi e profonde.

## Da dove vengono

Qui conviene separare quello che si legge dai negozi da quello che sostiene la ricerca.

**La versione diffusa.** Antichi strumenti rituali tibetani, forgiati con sette metalli corrispondenti ai sette pianeti, usati per millenni dai monaci a scopo di guarigione.

**Quello che risulta.** Le analisi delle ciotole antiche trovano in genere **bronzo**, cioè una lega di rame e stagno, con tracce variabili di altri metalli. La corrispondenza con i sette pianeti è un racconto ricorrente nei mercati turistici e non trova conferma nei manufatti.

Soprattutto: nelle regioni himalayane queste ciotole erano in larga parte **oggetti d'uso quotidiano** — per il cibo, per le offerte, come recipienti. Il loro impiego sistematico come strumenti di guarigione sonora si afferma in Occidente a partire dalla seconda metà del Novecento, e da lì torna indietro come tradizione.

Non toglie niente all'esperienza di un trattamento, che è reale e la si prova. Toglie una pretesa di antichità che serve soprattutto a chi vende.

## Come si usano

**Nei bagni sonori di gruppo.** Le campane sono fra le protagoniste dei [bagni sonori](/blog/{GONG}), insieme al gong e ad altri strumenti: si sta sdraiati, gli strumenti suonano intorno, il suono fa il lavoro.

**Nei trattamenti individuali sul corpo.** È la modalità più caratteristica: le campane vengono appoggiate direttamente sul corpo vestito — schiena, torace, gambe — e fatte suonare. La vibrazione si trasmette meccanicamente ai tessuti, ed è un massaggio sonoro nel senso letterale, percepibile come un'onda che attraversa.

**Nella pratica personale.** Una campana singola per aprire e chiudere la [meditazione]({MEDIT}), o per accompagnare il respiro. È uno degli strumenti di questo mondo più semplici da usare in autonomia.

## Come si svolge un trattamento

Dura in genere fra i quarantacinque e i sessanta minuti, e in Italia costa fra i 40 e i 70 euro.

**Il colloquio.** Qualche minuto in cui si racconta come si sta e in cui chi conduce chiede di eventuali condizioni di salute. Se questa parte manca, manca la parte che riguarda la tua sicurezza.

**La sistemazione.** Sdraiati vestiti su un lettino o su un materassino, coperti. La temperatura del corpo scende quando ci si rilassa a lungo, ed è il motivo per cui una coperta cambia l'esperienza più di quanto sembri.

**Il lavoro.** Le campane vengono suonate prima nello spazio, per portare l'attenzione, poi appoggiate sul corpo in punti diversi. Chi conduce alterna percussione e sfregamento, e sposta le campane seguendo una sequenza.

**La chiusura.** Il suono si dirada, si resta qualche minuto in silenzio, ci si rialza con calma. Molte persone si addormentano, e non è un problema.

## Cosa si prova

I racconti si somigliano su tre punti.

**Il rilassamento arriva in fretta.** Più in fretta che in una pratica di meditazione, perché non c'è niente da fare: il suono occupa lo spazio che di solito occupano i pensieri.

**La vibrazione viaggia.** Molti la percepiscono in punti lontani da dove la campana è appoggiata. È un effetto meccanico: i tessuti trasmettono.

**La mente smette di commentare.** È l'effetto che le persone descrivono come più insolito, e somiglia a quello dello [yoga nidra]({NIDRA}): uno stato di confine fra veglia e sonno.

C'è anche chi non prova niente di particolare e vive un'ora di riposo. In un mondo che non si ferma, è un buon risultato.

## Cosa dice la ricerca

Gli studi specifici sulle campane sono pochi e su campioni piccoli. Alcuni riportano riduzioni dello stress percepito e miglioramenti dell'umore dopo sessioni di bagno sonoro, ma i disegni sperimentali sono difficili da controllare: non si può fare un placebo di un'ora di suono in una stanza tranquilla.

Quello che è documentato con più solidità è **l'effetto dello stato di rilassamento profondo** che queste pratiche inducono, che è un effetto reale e non specifico dello strumento.

In pratica: una pratica di benessere, mai una terapia sostitutiva. Chi la presenta come cura sta oltrepassando un confine, ed è [uno dei criteri]({SERIO}) con cui si riconosce chi lavora bene.

## Controindicazioni

Poche e reali, e vanno dette prima della sessione.

- **Gravidanza**, per cui l'appoggio diretto sull'addome e sul bacino si evita
- **Pacemaker e dispositivi impiantati**, che richiedono un confronto preventivo e in genere l'esclusione dell'appoggio sul torace
- **Protesi recenti o fratture in via di guarigione**, dove la vibrazione diretta va evitata
- **Epilessia**, per cui vale un confronto con il proprio medico
- **Acufeni severi**, che in alcune persone peggiorano con esposizioni sonore intense

Chi conduce chiede queste cose all'inizio. Se nessuno chiede niente, quella è già un'informazione.

## Campane tibetane e campane di cristallo

La domanda che tutti fanno, in quattro punti.

**Materiale e suono.** Le tibetane, di metallo, hanno un suono ricco di armonici, complesso, terroso. Le campane di cristallo, di quarzo, producono un tono più puro e penetrante, che riempie lo spazio in modo quasi fisico.

**Uso sul corpo.** Le tibetane si appoggiano e trasmettono per contatto. Quelle di cristallo, fragili e molto direttive nel suono, lavorano quasi sempre nello spazio.

**Tradizione e modernità.** Le tibetane hanno alle spalle una storia himalayana, con le precisazioni fatte sopra. Quelle di cristallo sono uno strumento contemporaneo, nato negli ultimi decenni.

**Quale scegliere.** Molti operatori le combinano: la tibetana per radicare e massaggiare, il cristallo per aprire. Provare entrambe è il modo più semplice di decidere.

## Come si sceglie una campana da comprare

Se l'idea è portarla a casa, quattro criteri.

**Ascoltala prima.** È l'unico criterio che conta davvero. Due campane identiche a vedersi possono avere voci diverse.

**Misura media per cominciare**, fra i quindici e i venti centimetri: abbastanza grande da avere profondità, abbastanza piccola da essere maneggevole.

**Prova sia il colpo sia lo sfregamento.** Alcune campane cantano male sotto il battente circolare, e te ne accorgi solo provando.

**Diffida dei set economici mai suonati.** Una campana industriale a basso costo produce un suono povero di armonici, ed è la ragione per cui chi la compra online spesso la abbandona.

## Domande frequenti

**Le campane riequilibrano i chakra?**
È il linguaggio della tradizione, usato da molti operatori come mappa simbolica. Quello che è osservabile è il rilassamento e la vibrazione meccanica sui tessuti; la lettura energetica è una cornice, e chi lavora bene distingue i due piani. Sulla mappa in sé abbiamo scritto [qui]({CHAKRA}).

**Sono davvero antiche e tibetane?**
Le ciotole hanno una storia himalayana, ma erano in larga parte oggetti d'uso. L'impiego come strumenti terapeutici si afferma in Occidente nel Novecento, e la lega dei sette metalli è un racconto commerciale.

**Che differenza c'è con il gong?**
Il gong sommerge di frequenze, la campana accompagna con precisione. Nei bagni sonori si completano.

**Un trattamento è adatto a chi non ha mai fatto nulla di simile?**
È una delle porte d'ingresso più semplici: non richiede credenze, non richiede sforzo, e il corpo capisce subito.

**Ogni quanto si può fare?**
Non ci sono limiti di frequenza. Molte persone lo vivono come un appuntamento mensile.

**Posso impararlo per farlo ad altri?**
Esistono formazioni, di durata molto variabile. Prima di iscriverti a una, valgono i criteri con cui si valuta [qualsiasi scuola]({SERIO}): ore dichiarate, chi insegna, da quanto esiste.
"""

TITOLO_G = "Bagno di gong e sound healing: come funziona e cosa aspettarsi"
DESCR_G = (
    "Cos'è un bagno sonoro, come si svolge una sessione, cosa si prova, "
    "le controindicazioni e cosa regge alla prova della ricerca."
)

CONTENUTO_G = f"""\
Chi ci va per la prima volta di solito non sa cosa aspettarsi, e la descrizione più ricorrente all'uscita è la stessa: la sensazione di aver dormito una notte intera in un'ora.

Questa guida racconta cos'è un bagno sonoro, come si svolge, cosa si prova, e cosa di tutto questo regge alla prova della ricerca.

## Cos'è il sound healing

È una famiglia di pratiche che usa il suono e le vibrazioni per accompagnare corpo e mente in uno stato di rilassamento profondo. Gli strumenti più diffusi sono il gong, le [campane tibetane](/blog/{CAMPANE}), le campane di cristallo, i tamburi, la voce.

La differenza con l'ascoltare musica è quella che le persone faticano a spiegare e riconoscono subito: **non è suono da ascoltare, è vibrazione da attraversare**. Un gong suonato a tre metri di distanza si sente nello sterno prima che nelle orecchie.

## Cos'è un gong

Vale la pena dirlo, perché viene spesso presentato come uno strumento antico e sacro.

Il gong da sala — un grande disco di lega metallica sospeso a un telaio — è nella sua forma attuale uno **strumento orchestrale contemporaneo**, prodotto soprattutto in Europa e in Asia orientale a partire dal Novecento. I modelli più usati nei bagni sonori sono di due tipi: quelli sinfonici, dal suono ampio e indistinto, e quelli accordati su frequenze associate ai corpi celesti, che sono una convenzione commerciale recente e non una scoperta astronomica.

La famiglia dei gong ha certamente radici antiche in Asia, in contesti rituali e cerimoniali. Lo strumento che si trova in una sala italiana, però, è figlio del Novecento, e la sua efficacia non dipende da quanto è antico.

## Come si svolge una sessione

**Prima.** Si arriva, ci si sistema su un materassino con cuscino e coperta. Conviene vestirsi a strati, perché la temperatura corporea scende con il rilassamento. Chi conduce introduce brevemente la pratica e chiede di eventuali condizioni di salute.

**Durante.** Sdraiati, occhi chiusi. Il suono comincia piano, quasi impercettibile, poi cresce in onde che salgono e si ritirano. Il gong produce una gamma di frequenze così fitta che l'orecchio smette presto di analizzarla e si limita a seguirla. Una sessione dura fra i quarantacinque e i settantacinque minuti.

**Dopo.** Il suono si spegne gradualmente e si resta qualche minuto in silenzio prima di rialzarsi. La fretta, in quel momento, è la cosa che rovina di più l'esperienza.

## Cosa si prova

Le esperienze variano molto. Le più ricorrenti:

- **Rilassamento profondo**, simile allo stato fra veglia e sonno: il corpo pesante, la mente che rallenta
- **Immagini e colori** che affiorano spontanei, senza che si stia cercando di visualizzare
- **Percezione fisica della vibrazione**, soprattutto nel torace e nell'addome
- **Sonno vero e proprio**, che capita spesso e va benissimo
- **Emozioni che emergono**, a volte commozione senza una ragione evidente: è il rilassamento che scioglie quello che era trattenuto

E c'è chi non sente niente di particolare la prima volta, e vive semplicemente un'ora di riposo raro.

## Cosa dice la ricerca

Il quadro va diviso in due, perché il modo in cui viene raccontato confonde le due parti.

**Quello che è documentato.** Gli effetti dello stato di rilassamento profondo: riduzione degli indicatori di stress percepito, tensione muscolare più bassa, sonno migliore nelle ore successive. Esistono alcuni studi su sessioni di bagno sonoro con risultati incoraggianti su umore e ansia, su campioni piccoli.

**Quello che viene raccontato come dimostrato e non lo è.** La spiegazione più diffusa nelle sale è il **trascinamento delle onde cerebrali**: l'idea che una frequenza esterna sincronizzi l'attività elettrica del cervello portandola in stati theta o delta. Il fenomeno esiste in condizioni sperimentali molto controllate, ma la sua applicazione a un gong suonato dal vivo in una stanza è un salto che gli studi non autorizzano. È una metafora, non un meccanismo misurato.

Il che non toglie nulla all'esperienza. Significa che l'effetto reale ha una spiegazione più semplice — un'ora di immobilità, buio, calore e un suono avvolgente che occupa l'attenzione — e che quella spiegazione basta.

## Controindicazioni

Poche, e vanno dette prima.

- **Gravidanza**, soprattutto nel primo trimestre: molti operatori la sconsigliano o adattano la distanza dagli strumenti
- **Pacemaker e dispositivi impiantati**, che richiedono un confronto preventivo
- **Epilessia**, per cui vale un confronto con il proprio medico
- **Acufeni severi e ipersensibilità uditiva**, che in alcune persone peggiorano
- **Disturbi psichiatrici in fase acuta**, dove uno stato alterato prolungato non è indicato

Chi conduce chiede queste cose prima della sessione. Se non le chiede nessuno, quella è l'informazione più importante che riceverai su quel contesto.

## Come prepararsi la prima volta

- **Vestiti comodi e a strati**, con calze calde
- **Niente pasti pesanti** nelle due ore precedenti
- **Nessuna aspettativa.** L'esperienza migliore è quella che non si prova a controllare
- **Bevi acqua** prima e dopo
- **Arriva in anticipo**, perché entrare di corsa in una sala già in silenzio è il modo peggiore di cominciare

## Come si sceglie una sala

Quattro cose che distinguono una sessione condotta bene.

**Il volume.** Un bagno sonoro non deve fare male alle orecchie. Se il suono è aggressivo o la testa pulsa, quella sala sta suonando troppo forte.

**La distanza dagli strumenti.** Sotto il gong l'intensità è molto diversa che a cinque metri. Chi conduce con esperienza dispone le persone tenendone conto e lo dice.

**La possibilità di uscire.** Ti viene detto che puoi alzarti e andartene in qualsiasi momento, senza spiegazioni.

**Cosa succede se qualcuno sta male.** Una domanda che si può fare prima, e chi ha esperienza ha una risposta pronta.

Sul resto valgono i criteri generali di [come capire se un operatore è serio]({SERIO}), e se quello che stai valutando è un ritiro di suono, le domande da fare stanno [qui]({DOMANDE}).

## Dove provare

**Una sessione di gruppo** nella propria città è il modo più accessibile: in Italia costa in genere fra i 15 e i 40 euro.

**Un trattamento individuale**, di solito con le campane appoggiate sul corpo, permette un lavoro più mirato ed è il passo successivo naturale.

**Un ritiro di suono**, dove i bagni sonori si intrecciano con meditazione, yoga e silenzio. L'immersione ripetuta porta la pratica a una profondità che la sessione singola accenna soltanto.

## Domande frequenti

**Il bagno di gong è adatto a tutti?**
Quasi. Le eccezioni sono gravidanza, pacemaker, epilessia, acufeni severi e disturbi psichiatrici in fase acuta: in tutti questi casi serve un confronto preventivo.

**Serve credere in qualcosa perché funzioni?**
No. Un'ora di immobilità, buio e suono avvolgente agisce sul sistema nervoso indipendentemente dalle convinzioni, e lo scetticismo iniziale non rovina l'esperienza.

**Meglio individuale o di gruppo?**
Per iniziare il gruppo va benissimo e costa meno. L'individuale permette un lavoro più mirato.

**Quanto spesso si può fare?**
Non ci sono controindicazioni alla frequenza. Molte persone lo vivono come un appuntamento mensile.

**È vero che il suono sincronizza le onde cerebrali?**
È la spiegazione più ripetuta e la meno sostenuta: il fenomeno esiste in condizioni sperimentali controllate, ma non è dimostrato per un gong suonato dal vivo. L'effetto di rilassamento è reale, la spiegazione è più semplice.

**Che differenza c'è fra gong e campane?**
Il gong lavora sull'ampiezza e sull'indistinto, le campane sulla precisione e sul contatto col corpo. Nei bagni sonori si usano insieme.

**Posso addormentarmi?**
Sì, capita spesso e non è un problema: il corpo prende quello che gli serve.
"""

PEZZI = [
    (CAMPANE, TITOLO_C, DESCR_C, CONTENUTO_C,
     [GONG, "chakra-cosa-sono-i-sette-come-si-usano",
      "meditazione-per-chi-inizia-guida-semplice"]),
    (GONG, TITOLO_G, DESCR_G, CONTENUTO_G,
     [CAMPANE, "meditazione-per-chi-inizia-guida-semplice",
      "yoga-nidra-cose-come-funziona-una-sessione"]),
]


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
            "updated_at": datetime.now(timezone.utc),
        }})
        print("  aggiornato")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
