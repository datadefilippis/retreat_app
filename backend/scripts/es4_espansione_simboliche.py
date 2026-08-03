"""ES4 — tarocchi e costellazioni: le due pratiche simboliche magre.

PERCHE' INSIEME. Sono le due su cui la voce di questa casa conta di
piu': pratiche senza validazione, che a molte persone fanno un gran
bene, e su cui in italiano si trova o entusiasmo o sbeffeggiamento.
Dire cosa sono, da dove vengono e perche' funzionano — con la
spiegazione semplice, non con quella magica — e' l'unica posizione
utile a chi legge.

TAROCCHI (805 → ~1600). Manca tutto l'impianto: cosa sono i 78 arcani,
quali sono i mazzi e cosa cambia fra loro, e soprattutto LA STORIA.
Le carte compaiono nell'Italia del Quattrocento come GIOCO di carte —
i trionfi — e l'uso divinatorio nasce in Francia alla fine del
Settecento, con l'invenzione di un'origine egizia che non ha alcun
fondamento. Chi vende "sapienza egizia millenaria" sta vendendo una
storia inventata nel 1781.

Piu' l'effetto Barnum, che e' il meccanismo vero e viene di solito
usato solo per demolire: raccontato bene spiega perche' funziona
anche quando le carte non sanno niente.

COSTELLAZIONI (779 → ~1500). Mancano i tre "ordini dell'amore", che
sono il modello di contenuto del metodo, e manca Hellinger: la sua
figura e' stata oggetto di critiche serie, anche da associazioni
professionali, per posizioni espresse pubblicamente. Un articolo che
presenta il metodo senza nominare le controversie sul fondatore lascia
il lettore a scoprirle altrove.

E LA VOCE. Nei tarocchi era rimasto un "molti operatori, me compresa"
e una descrizione che dice "raccontati da chi li legge": la stessa
rivendicazione corretta altrove, sfuggita al filtro perche' la formula
era diversa.

    venv/bin/python scripts/es4_espansione_simboliche.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

TAROCCHI = "tarocchi-oracoli-strumento-evolutivo"
COST = "costellazioni-familiari-cosa-sono-come-funzionano"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
TEMA = "/blog/lettura-tema-natale-cosa-aspettarsi"
CERCHI = "/blog/cerchi-di-donne-cosa-sono-come-funzionano"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"

TITOLO_T = "Tarocchi evolutivi: cosa sono, come funziona un consulto"
DESCR_T = (
    "Da dove vengono davvero le carte, i 78 arcani, i mazzi principali, come "
    "si svolge un consulto e perché funziona anche senza poteri."
)

CONTENUTO_T = f"""\
Chi tira fuori un mazzo di tarocchi davanti a qualcuno che non li ha mai visti riconosce sempre lo stesso sguardo: metà curiosità, metà «adesso mi dice quando muoio».

E chi li usa in senso evolutivo comincia sempre dallo stesso punto: queste carte non predicono niente. Sono più interessanti così.

Questa guida racconta da dove vengono, come sono fatte, cosa succede in un consulto e — la parte che di solito manca — perché producono un effetto reale anche se le carte non sanno nulla.

## Da dove vengono, per davvero

La storia raccontata nei negozi parla di antica sapienza egizia. La storia documentata è un'altra, ed è più interessante.

**Quattrocento, Italia settentrionale.** Compaiono i primi mazzi di *trionfi*, poi detti tarocchi. Sono **carte da gioco**: un gioco di prese con briscola permanente, che si gioca ancora oggi in alcune zone d'Europa. I mazzi più antichi conservati sono commissioni di corte, dipinti a mano.

**1781, Francia.** Antoine Court de Gébelin pubblica un saggio in cui sostiene che i tarocchi conservino la sapienza dell'antico Egitto. È **un'invenzione**, formulata prima che i geroglifici venissero decifrati e smentita da tutto quello che è emerso dopo. Ma è l'atto di nascita dell'uso divinatorio.

**Fine Settecento e Ottocento.** Etteilla e poi gli occultisti francesi costruiscono i sistemi di lettura che conosciamo, associando le carte a significati, corrispondenze astrologiche e cabalistiche.

**1909, Londra.** Esce il mazzo Rider-Waite-Smith, disegnato da Pamela Colman Smith su indicazioni di Arthur Edward Waite. È il primo in cui **anche le carte numerali hanno una scena illustrata**, e questa scelta grafica è la ragione per cui oggi i tarocchi si leggono come si leggono: le immagini raccontano situazioni riconoscibili anche a chi non ha studiato nulla.

Sapere questo non toglie valore alla pratica. Toglie valore a chi vende millenni che non ci sono.

## Come è fatto un mazzo

Settantotto carte, divise in due gruppi.

**I ventidue arcani maggiori.** Dal Matto al Mondo: figure che rappresentano situazioni umane grandi — la scelta, il rovesciamento, la perdita, il tempo, la rinascita. Sono le carte che tutti riconoscono, e in una lettura indicano i temi di fondo.

**I cinquantasei arcani minori.** Quattro semi — bastoni, coppe, spade, denari — dall'asso al dieci più quattro figure. Nella lettura riguardano il quotidiano: il seme di coppe le emozioni e le relazioni, spade i pensieri e i conflitti, bastoni l'azione e il desiderio, denari il concreto e il materiale.

Una lettura in cui escono soprattutto arcani maggiori parla di un momento di passaggio; una fatta di minori parla della vita di tutti i giorni. È la prima cosa che chi legge guarda.

## I mazzi principali

**Marsiglia.** Il più antico fra quelli in uso, con arcani minori non illustrati. Lettura più severa e più simbolica, molto diffusa in Francia e in Italia.

**Rider-Waite-Smith.** Il più diffuso al mondo e il più semplice per cominciare, proprio per via delle scene illustrate su ogni carta.

**Thoth.** Disegnato su indicazioni di Aleister Crowley, denso di riferimenti esoterici. Bellissimo e non adatto all'inizio.

**Gli oracoli.** Mazzi liberi che non seguono la struttura dei settantotto: ogni mazzo ha un tema proprio — natura, animali, archetipi femminili — e un linguaggio in genere più dolce. Sono spesso la porta d'ingresso più facile: meno codice da imparare, stessa funzione di specchio.

## Evolutivo e cartomanzia: la differenza

La cartomanzia tradizionale usa le carte per rispondere a domande sul futuro: tornerà, vincerò, quando. È il modello della televisione notturna, ed è quello che ha riempito il settore di dipendenza, paure indotte e tariffe al minuto.

L'approccio evolutivo usa lo stesso strumento in modo opposto: le carte come specchio del presente, non come finestra sul futuro.

La domanda cambia di conseguenza. Non «tornerà?», ma «cosa mi sta chiedendo questa relazione?». Non «andrà bene?», ma «cosa non sto guardando di questa scelta?».

## Come funziona un consulto

**L'apertura.** Si parte dal tema che porti — una situazione, una decisione, un passaggio — e insieme lo si trasforma in una domanda aperta. Le domande da sì o no sono le meno fertili.

**La stesa.** Si mescolano le carte e se ne dispongono alcune secondo uno schema in cui ogni posizione ha un significato: la situazione, la radice, la risorsa, la direzione.

**La lettura.** Qui si vede chi lavora bene: non recita significati a memoria, ma intreccia i simboli con quello che **tu** riconosci. Le intuizioni migliori arrivano quasi sempre da chi riceve, davanti a un'immagine che sblocca qualcosa.

**La chiusura.** Un buon consulto finisce con una o due domande da portare a casa, non con sentenze.

Dura in genere fra i quarantacinque e i sessanta minuti e in Italia costa fra i 40 e gli 80 euro.

## Perché funziona, senza bisogno di poteri

È la domanda che chi è scettico si fa, e ha una risposta precisa.

**L'effetto Barnum.** Descritto negli anni Quaranta dallo psicologo Bertram Forer, è la tendenza a riconoscersi in affermazioni generiche che potrebbero valere per chiunque. Viene di solito citato per demolire, e in realtà spiega solo metà della cosa: un'affermazione generica funziona **perché ci mettiamo dentro il nostro materiale**, ed è esattamente quello che serve a un lavoro di riflessione.

**La proiezione.** Davanti a un'immagine ambigua, la mente ci proietta quello che ha in mente. Un'immagine di una figura che si allontana da tre coppe rovesciate diventa la tua storia, non una storia qualunque.

**Il pensiero costretto a fermarsi.** Un'ora dedicata a una domanda sola, con qualcuno che ascolta e nessuna distrazione, è una cosa che quasi nessuno si concede. Buona parte del valore sta lì, ed è la stessa ragione per cui funziona una [pratica di meditazione]({MEDIT}).

Nessuna evidenza sostiene che le carte sappiano alcunché, e chi le usa con serietà non lo sostiene. Il valore non è nella magia: è nella qualità della riflessione che attivano. Vale lo stesso discorso della [lettura del tema natale]({TEMA}).

## Provare da soli: la stesa a tre carte

Non serve un maestro per cominciare, e questa è la pratica più semplice che esista.

**Formula una domanda aperta.** «Cosa mi serve vedere di questa situazione?» funziona quasi sempre. Scrivila.

**Mescola e prendi tre carte**, mettendole in fila.

**Leggile in questo ordine:** la prima è la situazione com'è, la seconda è quello che la alimenta o la ostacola, la terza è la direzione possibile.

**Non cercare il significato sul libro per prima cosa.** Guarda l'immagine per un minuto e scrivi cosa vedi. Solo dopo, se vuoi, apri il manuale.

**Rileggi fra una settimana** quello che hai scritto. È la parte che sorprende di più.

## Come riconoscere chi legge con serietà

**Non predice il futuro e te lo dice subito.** Il linguaggio è quello dell'esplorazione, non della sentenza.

**Non alimenta paure.** Nessuna carta maledetta, nessun malocchio, nessun rituale da comprare per rimediare. Chi usa la paura sta vendendo.

**Prezzo a sessione, mai al minuto.** La tariffa al minuto è il modello economico della dipendenza: chi guadagna sulla durata ha interesse a non chiudere.

**Non tocca salute, soldi e decisioni legali.** Nessuna carta dice se fare un intervento, se lasciare il lavoro o se firmare. Chi lo fa sta oltrepassando un confine — vale qui come per [ogni pratica]({SERIO}).

**Ti lascia più autonomo, non più bisognoso.** Il test definitivo: dopo il consulto ti senti con più strumenti o con più bisogno di tornare?

## Le carte nei percorsi

Nei ritiri e nei percorsi di crescita i tarocchi evolutivi compaiono come traccia per la scrittura riflessiva, nei [cerchi di condivisione]({CERCHI}) o nei consulti individuali a margine delle giornate.

## Domande frequenti

**I tarocchi sono antichi ed egizi?**
No. Nascono nell'Italia del Quattrocento come gioco di carte; l'origine egizia è un'invenzione francese del 1781, formulata prima che i geroglifici fossero decifrati.

**Devo credere nei tarocchi perché il consulto funzioni?**
No. Serve disponibilità a riflettere davanti a immagini simboliche. Lo scetticismo curioso è un ottimo punto di partenza.

**Le carte possono dire qualcosa di brutto?**
Nell'approccio evolutivo nessuna carta è negativa: anche le più dure — la Torre, la Morte — parlano di chiusure e ricominciamenti. Chi legge con serietà non manda a casa nessuno spaventato.

**Meglio tarocchi o oracoli per iniziare?**
Gli oracoli sono più immediati, i tarocchi più strutturati. Per un primo consulto va bene lasciar scegliere a chi legge.

**Quale mazzo compro?**
Il Rider-Waite-Smith, perché ogni carta ha una scena illustrata e si legge anche senza aver studiato.

**Posso imparare da solo?**
Sì, ed è un buon strumento di riflessione personale. Il consulto con un'altra persona resta un'esperienza diversa: lo sguardo esterno vede quello che il tuo punto cieco copre.

**Ogni quanto ha senso un consulto?**
Quando c'è una domanda vera. Chi ti propone appuntamenti fissi settimanali sta costruendo un'abitudine, non accompagnando un percorso.
"""

TITOLO_C = "Costellazioni familiari: cosa sono, come funzionano, cosa dice la ricerca"
DESCR_C = (
    "Il metodo, i tre ordini dell'amore, come si svolge una sessione, le "
    "controversie su Hellinger e perché non è e non sostituisce una terapia."
)

CONTENUTO_C = f"""\
Poche pratiche di questo mondo dividono quanto le costellazioni familiari. Chi le ha vissute ne parla spesso come di un'esperienza che ha spostato qualcosa di profondo; i critici le liquidano come teatro suggestivo.

Questa guida racconta cosa sono, su quale modello poggiano, cosa succede in una sessione, cosa dice la ricerca e cosa si sa del suo fondatore — che è una parte di solito assente.

## Cosa sono

Un metodo di esplorazione delle dinamiche familiari e relazionali, sviluppato dal tedesco **Bert Hellinger** a partire dagli anni Ottanta e Novanta.

L'idea di fondo: portiamo dentro di noi, spesso senza saperlo, lealtà, esclusioni e pesi che appartengono al nostro sistema familiare, anche a generazioni che non abbiamo conosciuto. La costellazione è un modo per rendere visibili queste dinamiche disponendole nello spazio.

## I tre ordini

Il metodo poggia su tre principi che Hellinger chiama *ordini dell'amore*, e conoscerli aiuta a capire cosa il facilitatore sta guardando.

**L'appartenenza.** Ogni membro del sistema ha diritto di farne parte, compresi quelli che sono stati esclusi, dimenticati o taciuti — un figlio non nato, un parente allontanato, chi ha fatto qualcosa di grave. Secondo il modello, chi viene escluso «torna» attraverso qualcun altro, che ne ripete il destino senza saperlo.

**L'ordine.** Chi è arrivato prima ha una precedenza rispetto a chi è arrivato dopo: i genitori prima dei figli, i primi legami prima dei successivi. Molte tensioni, nel modello, nascono da qualcuno che occupa un posto che non è il suo — tipicamente un figlio che si mette al posto di un genitore.

**L'equilibrio fra dare e ricevere.** Nelle relazioni fra pari, dare e ricevere devono compensarsi. Fra genitori e figli no: i figli ricevono e non possono restituire, e possono solo passare avanti.

Sono lenti di lettura, non leggi verificate. La loro utilità sta in quello che fanno vedere.

## Come funziona una sessione di gruppo

**La domanda.** Chi costella porta un tema: una relazione bloccata, uno schema che si ripete, un senso di estraneità. Il facilitatore lo mette a fuoco con poche domande sui fatti essenziali del sistema familiare.

**La messa in scena.** Qui accade la cosa che spiazza chi arriva la prima volta: altri partecipanti vengono scelti come **rappresentanti** dei membri della famiglia e disposti nello spazio, uno rispetto all'altro. Nessuno recita: i rappresentanti riferiscono quello che sentono nella posizione in cui si trovano.

**Il movimento.** Il facilitatore osserva, sposta, dà voce. Le dinamiche — vicinanze, esclusioni, pesi — emergono nella disposizione con una nitidezza che sorprende. Il lavoro si chiude cercando un'immagine di maggiore equilibrio, a volte con frasi rituali semplici.

**Dopo.** Chi ha costellato porta a casa un'immagine più che una spiegazione, e l'indicazione classica è lasciarla lavorare senza analizzarla troppo nei giorni successivi.

Esistono formati individuali, con oggetti o sagome al posto dei rappresentanti, e sessioni online. L'intensità del gruppo dal vivo resta un'altra cosa.

## Cosa provano i rappresentanti

È il fenomeno che colpisce di più: persone che non sanno nulla della famiglia riferiscono sensazioni ed emozioni che chi costella riconosce.

Le spiegazioni proposte vanno da una parte all'altra.

**La più prudente**, e anche la più sostenuta: **lettura inconsapevole dei segnali**. Il gruppo riceve moltissima informazione non verbale — la postura di chi ha portato il tema, il tono con cui ha nominato una persona, come si dispone chi lo circonda — e la elabora senza accorgersene. È un fenomeno reale e ben studiato in psicologia sociale.

**Quella della tradizione**, che parla di un campo informativo condiviso a cui i rappresentanti accedono. Non ha riscontro sperimentale.

Non serve scegliere un campo per vivere l'esperienza con beneficio, ed è utile sapere che la prima spiegazione basta a rendere conto di quello che succede.

## Cosa dice la ricerca

Va detto senza giri di parole: **le costellazioni familiari non hanno validazione scientifica come metodo terapeutico**. Gli studi esistenti sono pochi e su campioni piccoli; alcuni riportano miglioramenti del benessere percepito dopo i seminari, nulla che soddisfi gli standard delle evidenze cliniche. Diverse voci della psicologia invitano esplicitamente alla prudenza.

In pratica:

1. **Non sono una psicoterapia e non la sostituiscono.** Mai.
2. **Sono un'esperienza simbolica ed evocativa**: uno specchio, non una cura.
3. **Su temi delicati** — lutti recenti, traumi, disturbi psichici — il contesto giusto è quello clinico. La costellazione, eventualmente, dopo e a fianco.

Un facilitatore serio queste cose le dice da solo. Se qualcuno promette di guarire il transgenerazionale o spinge a interrompere una terapia, quello è il momento di andarsene.

## Bert Hellinger, e perché va nominato

Chi si avvicina al metodo prima o poi incontra le polemiche sul suo fondatore, e conviene arrivarci preparati.

Hellinger, morto nel 2019, è stato una figura discussa ben oltre il merito della tecnica. Ha espresso pubblicamente posizioni che hanno suscitato critiche dure, anche da parte di associazioni professionali del settore psicologico, in particolare per il modo in cui ha trattato temi come la responsabilità fra vittime e autori di violenza, e per interventi su casi delicati condotti in pubblico.

Una parte consistente di chi pratica oggi in Europa ha preso distanza esplicita da quelle posizioni e lavora con impostazioni più prudenti, spesso con formazione psicologica alle spalle. **Chiedere quale linea segue chi conduce è una domanda legittima**, e la risposta dice molto.

## Chi dovrebbe rimandare

- Chi ha subito un **lutto recente** e non lo ha ancora attraversato
- Chi ha una **storia di trauma non elaborato**, dove il contesto clinico viene prima
- Chi attraversa un **disturbo psichico in fase acuta**
- Chi ci arriva **spinto da qualcun altro** invece che da una domanda propria
- Chi cerca una **risposta a una decisione pratica**: non è quello che il metodo fa

## Come scegliere un facilitatore

**Formazione dichiarata e verificabile**, meglio se con un background in ambito relazionale o psicologico.

**Linguaggio onesto**: parla di esplorazione ed esperienza, non di guarigione garantita.

**Screening iniziale**: chiede come stai e cosa porti, e sa dire «questo tema non è da costellazione».

**Nessuna pressione a continuare**: niente pacchetti obbligati, niente dipendenza indotta.

**Sa cosa fa se qualcuno sta male** durante o dopo il lavoro, e te lo racconta senza esitare.

Valgono anche i [criteri generali]({SERIO}). Una sessione di gruppo in Italia costa fra i 30 e gli 80 euro come rappresentante o partecipante, e fra gli 80 e i 150 per costellare il proprio tema.

## Costellazioni e ritiri

Compaiono spesso nei ritiri olistici come esperienza serale o come giornata dedicata, e il contesto del ritiro — gruppo che si conosce, tempo disteso — le rende spesso più intense di una serata singola in città. Il che è un motivo in più per informarsi prima: le domande da fare stanno [qui]({DOMANDE}).

## Domande frequenti

**Devo raccontare tutta la mia storia familiare?**
No. Una particolarità del metodo è che lavora con pochissime informazioni: il facilitatore chiede solo i fatti essenziali.

**Posso partecipare solo come rappresentante?**
Sì, ed è il modo più graduale di conoscere il metodo: si vive dall'interno senza esporre un tema proprio.

**È un percorso o un evento singolo?**
Tradizionalmente si costella un tema una volta e lo si lascia lavorare. Diffida di chi propone costellazioni a ripetizione sullo stesso tema.

**È compatibile con una psicoterapia?**
Spesso sì come esperienza complementare, ma parlane prima con il tuo terapeuta, che è la persona giusta per valutare tempi e opportunità.

**Come mai i rappresentanti sentono cose che non sanno?**
La spiegazione più sostenuta è la lettura inconsapevole dei segnali non verbali del gruppo, che è un fenomeno reale e studiato. La lettura tradizionale parla di un campo condiviso e non ha riscontro sperimentale.

**Che effetto fa nei giorni dopo?**
Molte persone riferiscono qualche giorno di sensibilità aumentata o di stanchezza. L'indicazione classica è non prendere decisioni importanti nell'immediato e lasciare sedimentare.

**Il metodo è riconosciuto?**
No, non è una professione regolata né un metodo validato, e chi lo pratica non è per questo un terapeuta.
"""

# la voce sfuggita al filtro: la formula era diversa
VOCE = [
    (TAROCCHI,
     "Molti operatori, me compresa, usano entrambi a seconda della persona "
     "e del momento.",
     "Molti operatori usano entrambi a seconda della persona e del momento."),
]

PEZZI = [
    (TAROCCHI, TITOLO_T, DESCR_T, CONTENUTO_T,
     [TEMA.split("/blog/")[1], COST,
      "come-capire-se-un-operatore-olistico-e-serio"]),
    (COST, TITOLO_C, DESCR_C, CONTENUTO_C,
     ["come-capire-se-un-operatore-olistico-e-serio", TAROCCHI,
      "cerchi-di-donne-cosa-sono-come-funzionano"]),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, vecchio, nuovo in VOCE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if d and vecchio in d["content"] and not dry_run:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})

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

    print("\n── controlli")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1,
                                                   "description": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"  link rotti: {rotti or 'nessuno'}")
    P = re.compile(r"(me compresa|me compreso|chi li legge|un'operatrice|"
                   r"una facilitatrice|nella mia pratica|io leggo)", re.I)
    resti = [(a["slug"], h.group(0)) for a in arts
             for h in P.finditer(a["content"] + " " + (a.get("description") or ""))]
    print(f"  prima persona: {resti or 'nessuna'}")
    magri = [(a["slug"], len(a["content"].split())) for a in arts
             if len(a["content"].split()) < 900]
    print(f"  sotto le 900 parole: {magri or 'nessuno'}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
