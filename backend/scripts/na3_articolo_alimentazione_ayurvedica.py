"""NA3 — l'alimentazione ayurvedica, secondo pezzo della stanza nuova.

PERCHE' QUESTO E PERCHE' ORA. E' la porta da cui quasi tutti entrano
nell'ayurveda, ed e' anche la parte del sistema a rischio piu' basso:
nessuna sostanza da ingerire, nessun trattamento, solo abitudini. Una
categoria appena aperta con un pezzo solo sarebbe una stanza vuota;
con questo diventa una stanza.

LA SCELTA DI STRUTTURA. Quasi tutte le pagine italiane su questo tema
partono dai tre elenchi "cosa mangia vata, cosa mangia pitta, cosa
mangia kapha", che e' la parte meno utile perche' presuppone di sapere
la propria costituzione — che non si stabilisce da soli. Qui l'ordine
e' rovesciato: prima COME si mangia, che vale per tutti e cambia di
piu', poi i sei sapori, e solo alla fine le differenze per
costituzione, dette come orientamenti e non come diete.

DUE ONESTA' NECESSARIE. Le combinazioni alimentari sconsigliate
(latte e frutta acida, pesce e latte) non hanno riscontro nella
scienza dell'alimentazione, e vanno raccontate come tradizione. E
nessuno studio ha validato una dieta per dosha. Quello che regge —
orari regolari, pasto principale a mezzogiorno, mangiare senza
schermi — regge per strade diverse, ed e' anche la parte che le
persone applicano davvero.

    venv/bin/python scripts/na3_articolo_alimentazione_ayurvedica.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "alimentazione-ayurvedica-principi-sei-sapori"
TITOLO = "Alimentazione ayurvedica: i principi, i sei sapori, come cominciare"
DESCRIZIONE = (
    "Il fuoco digestivo, i sei sapori, come si mangia prima ancora di cosa, "
    "gli orientamenti per costituzione e cosa regge alla prova della ricerca."
)
CATEGORIA = "ayurveda"

AYU = "/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
DETOX = "/blog/digiuno-consapevole-detox-benefici-falsi-miti"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"

CONTENUTO = f"""\
«Mangiare secondo la tua costituzione» suona come l'ennesima dieta con un nome esotico.

Non lo è, e la differenza sta nella domanda di partenza. Una dieta chiede *cosa* mangiare. L'ayurveda chiede prima *come*, e considera quella la parte che cambia di più — al punto che, nei suoi testi, un cibo perfetto mangiato male vale meno di un cibo qualsiasi mangiato bene.

Questa guida segue quell'ordine: prima il come, poi i sapori, e solo alla fine le differenze fra costituzioni. Alla fine trovi anche cosa di tutto questo regge alla prova della ricerca contemporanea, che è meno di quanto si dice e più di quanto si pensi.

## Il centro di tutto: il fuoco digestivo

L'ayurveda chiama *agni* la capacità digestiva, e la mette al centro di tutto il sistema.

Il ragionamento è questo: non conta quello che mangi, conta quello che riesci a trasformare. Un alimento eccellente che il corpo non digerisce produce quello che il sistema chiama *ama*, un residuo non trasformato che si accumula e che nel linguaggio ayurvedico è all'origine di gran parte dei disturbi.

Da qui discende tutto il resto. Le regole che seguono servono a una cosa sola: non spegnere quel fuoco.

Come si riconosce che funziona, secondo i segni che l'ayurveda usa: hai fame a orari regolari, dopo mangiato ti senti leggero e non assonnato, la lingua al mattino è pulita, l'intestino è regolare, l'alito è neutro.

## Come si mangia

Questa sezione vale per chiunque, a prescindere dalla costituzione, ed è quella che produce il cambiamento maggiore. Nove indicazioni.

**Il pasto principale a mezzogiorno.** È la regola più importante e la più disattesa in Italia, dove la cena è il pasto sociale. Nel sistema la capacità digestiva segue il sole ed è massima a metà giornata.

**La cena leggera e presto.** Idealmente tre ore prima di coricarsi. Una cena pesante e tardiva è, in questo schema, la causa più comune di sonno cattivo e di lingua sporca al mattino.

**Mangia solo quando hai fame.** Non per orario, non per noia. E se non hai fame a un pasto, il sistema dice di saltarlo: significa che il precedente non è stato digerito.

**Lascia un quarto di stomaco vuoto.** L'indicazione classica divide il pasto in metà cibo solido, un quarto liquido, un quarto aria. In pratica: alzati che potresti ancora mangiare qualcosa.

**Siediti, e senza schermo.** È la raccomandazione che le persone applicano meno e che cambia di più. Mangiare in piedi, camminando o davanti a un telefono riduce la percezione della sazietà, e questa parte è ampiamente documentata anche fuori dall'ayurveda.

**Acqua tiepida, a piccoli sorsi.** L'acqua ghiacciata durante il pasto è, nella logica del sistema, il modo più diretto per spegnere il fuoco. Un bicchiere di acqua calda al risveglio è l'altra abitudine classica.

**Niente frutta a fine pasto.** La frutta digerisce più rapidamente del resto: mangiata dopo, resta ferma. Lontano dai pasti, invece, va benissimo.

**Cucinato meglio che crudo**, soprattutto d'inverno e per chi ha digestione delicata. L'insalata cruda a cena, in questo schema, è una delle cose più difficili da digerire.

**Le spezie non sono decorazione.** Zenzero, cumino, finocchio, curcuma, pepe nero: nell'ayurveda servono a sostenere la digestione, e ogni cucina regionale del mondo è arrivata da sola alle stesse combinazioni.

## I sei sapori

L'ayurveda classifica gli alimenti in sei sapori, i *rasa*, e sostiene che un pasto completo li contenga tutti — anche in quantità minime.

**Dolce** — cereali, latte, frutta matura, carne, la maggior parte delle verdure amidacee. Nutre e appesantisce. È il sapore dominante di quasi tutta la dieta occidentale.

**Acido** — limone, aceto, yogurt, fermentati, pomodoro. Stimola l'appetito e la digestione.

**Salato** — sale, alghe, salumi. Trattiene i liquidi e stimola.

**Piccante** — peperoncino, zenzero, pepe, cipolla, aglio. Riscalda e smuove.

**Amaro** — verdure a foglia scura, tarassaco, carciofo, curcuma, cacao puro. Alleggerisce e disintossica secondo il sistema. È il sapore più assente dalla nostra alimentazione.

**Astringente** — legumi, melagrana, tè, mela verde, molte verdure crude. Asciuga e compatta.

L'osservazione utile, indipendentemente da quanto si creda al modello: **la nostra alimentazione è satura di dolce e salato e povera di amaro e astringente**. Aggiungere verdura amara e legumi è un'indicazione che funziona per motivi che l'ayurveda spiega a modo suo e la nutrizione moderna a modo proprio.

## Le tre costituzioni, come orientamento

Qui serve una premessa: la costituzione non si stabilisce da soli e nemmeno con un test online, e i dettagli su come funziona stanno nella [guida generale all'ayurveda]({AYU}). Quello che segue sono orientamenti, non prescrizioni.

**Vata — leggero, freddo, secco, irregolare.** Si bilancia con il contrario: cibi caldi, cotti, oleosi, morbidi. Zuppe, cereali cotti, verdure al vapore con olio, spezie dolci. Si riducono crudo, freddo, secco (gallette, insalate), e soprattutto l'irregolarità degli orari, che per vata pesa più del contenuto del piatto.

**Pitta — caldo, intenso, acido.** Si bilancia con il fresco: verdure dolci e amare, cereali, legumi, latticini freschi, frutta dolce. Si riducono piccante, fritto, alcol, aceto, pomodoro in eccesso, e i pasti saltati, perché pitta affamato diventa irritabile.

**Kapha — pesante, umido, lento.** Si bilancia con il leggero e il caldo: verdure, legumi, cereali integrali, spezie piccanti, poco olio. Si riducono latticini, dolci, fritti, e soprattutto le porzioni. Kapha è la costituzione che beneficia di più del saltare la cena ogni tanto.

Un principio unico dietro i tre elenchi: **il simile aumenta il simile, l'opposto bilancia**. È il motivo per cui a due persone con lo stesso problema si consigliano cose opposte.

## Le stagioni

L'ayurveda considera la stagione tanto quanto la costituzione, e questa parte è facile da applicare.

**Inverno.** Predominano freddo e secco: si mangia caldo, cotto, unto. Zuppe, stufati, cereali, spezie riscaldanti.

**Primavera.** Il periodo in cui il sistema colloca l'alleggerimento: verdure amare, meno latticini e dolci, porzioni ridotte. È anche il momento in cui l'ayurveda colloca le pratiche di purificazione, e su come distinguere quelle serie dai pacchetti abbiamo scritto [a proposito di digiuno e detox]({DETOX}).

**Estate.** Si raffredda: frutta, verdure fresche, meno piccante e meno alcol, pasti più leggeri.

**Autunno.** Il vento e il secco richiedono di tornare a cibi caldi, oleosi e regolari.

## Le combinazioni sconsigliate

L'ayurveda ne elenca diverse, e le più citate sono latte con frutta acida, latte con pesce, miele scaldato, frutta insieme ad altri cibi.

Va detto con precisione: **queste indicazioni non hanno riscontro nella scienza dell'alimentazione**. Sono parte della tradizione e vanno prese come tale.

Il principio generale che le sottende, però, ha una sua utilità pratica: **pasti semplici, con pochi alimenti diversi, si digeriscono meglio di pasti complessi**. Chi passa da un piatto unico bilanciato a un pasto con sei portate diverse se ne accorge, e non serve un modello per spiegarlo.

## Cosa dice la ricerca

Due risposte diverse, ed è importante non confonderle.

**Sulla dieta per dosha, nulla.** Non esistono studi che validino un'alimentazione differenziata per costituzione ayurvedica, e il modello dei dosha non ha riscontro nella fisiologia. Chi presenta questo come «scientificamente provato» sta usando prove che riguardano altro.

**Sul come si mangia, parecchio.** E qui è interessante, perché la ricerca contemporanea è arrivata per strade completamente diverse a conclusioni sovrapponibili:

- Concentrare le calorie nella **prima parte della giornata** e cenare presto ha effetti documentati su metabolismo e qualità del sonno, ed è uno dei filoni più solidi della cronobiologia nutrizionale.
- Mangiare **senza distrazioni** aumenta la percezione di sazietà e riduce la quantità assunta, con una letteratura consistente sul *mindful eating*.
- La **regolarità degli orari** dei pasti ha effetti su glicemia e appetito indipendenti dal contenuto.
- **Verdure amare e legumi** in più sono una raccomandazione su cui ayurveda e nutrizione moderna concordano senza saperlo.

La sintesi utile: la parte esoterica del sistema resta una tradizione, la parte comportamentale è la meno esotica e la più sostenuta. Ed è anche quella che si può provare stasera senza chiedere il permesso a nessuno.

## Da dove cominciare

Tre cose, per due settimane. Non serve altro.

**1. Sposta il pasto principale a mezzogiorno** e fai una cena leggera almeno tre ore prima di coricarti.

**2. Mangia seduto, senza telefono e senza schermo**, per tutti i pasti.

**3. Bevi un bicchiere di acqua calda appena sveglio** e acqua tiepida durante i pasti.

Dopo due settimane guarda tre segnali: come dormi, com'è la lingua al mattino, quanto sei assonnato dopo pranzo. Sono gli indicatori che l'ayurveda usa, e sono anche i più facili da osservare senza strumenti.

Se stai già costruendo un'abitudine quotidiana, queste si incastrano bene con il [kit delle pratiche di quindici minuti]({KIT}).

## Domande frequenti

**Devo conoscere la mia costituzione per cominciare?**
No, ed è la ragione per cui le indicazioni su *come* mangiare vengono prima in questa guida: valgono per tutti e sono quelle che cambiano di più.

**L'alimentazione ayurvedica è vegetariana?**
Non necessariamente. I testi classici includono la carne per alcune costituzioni e condizioni. La versione diffusa in Occidente è prevalentemente vegetariana per ragioni culturali più che dottrinali.

**Fa dimagrire?**
Non è il suo scopo. Le abitudini che propone — pasto principale a mezzogiorno, cena leggera, mangiare senza distrazioni, porzioni misurate — hanno spesso quell'effetto come conseguenza.

**Posso seguirla se ho una patologia o sono in terapia?**
Le indicazioni comportamentali sì. Per qualsiasi cambiamento importante della dieta, e per qualsiasi preparato da ingerire, parlane con chi ti segue: è un principio che vale a prescindere dalla tradizione di riferimento.

**Servono ingredienti particolari?**
No. Ghee e alcune spezie si trovano ovunque, ma il grosso si fa con quello che hai già in cucina. Un'alimentazione ayurvedica che richiede una spesa in un negozio specializzato è stata venduta male.

**Le combinazioni vietate sono vere?**
Non hanno riscontro scientifico e vanno prese come tradizione. Il principio che le sottende — pasti semplici si digeriscono meglio — è verificabile sulla propria pelle.

**Quanto ci vuole per notare qualcosa?**
Sul sonno e sulla pesantezza dopo i pasti, in genere una o due settimane. Sul resto, mesi: è un sistema che ragiona per abitudini, non per risultati rapidi.
"""

AGGIUNTE = [
    ("ayurveda-cose-i-tre-dosha-cosa-aspettarsi", "## Domande frequenti",
     f"Della parte alimentare, che e' quella con cui quasi tutti cominciano, "
     f"abbiamo scritto [una guida a parte](/blog/{SLUG}): i sei sapori, come "
     f"si mangia prima ancora di cosa, e cosa regge alla prova della "
     f"ricerca.\n\n## Domande frequenti"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    print(f"{TITOLO}\n  slug: {SLUG}\n  categoria: {CATEGORIA}\n"
          f"  parole: {len(CONTENUTO.split())}\n"
          f"  descrizione: {len(DESCRIZIONE)} caratteri")
    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    print("  stato:", "gia' presente, si aggiorna" if esistente else "nuovo")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    campi = {
        "title": TITOLO, "description": DESCRIZIONE, "content": CONTENUTO,
        "category": CATEGORIA, "author_name": "Aurya", "published": True,
        "updated_at": now, "translations": {},
        "related_slugs": ["ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
                          "digiuno-consapevole-detox-benefici-falsi-miti",
                          "kit-pratiche-quotidiane-15-minuti"],
    }
    if not esistente:
        campi |= {"id": str(uuid.uuid4()), "slug": SLUG,
                  "created_at": now, "published_at": now}
    await db.articles.update_one({"slug": SLUG}, {"$set": campi}, upsert=True)

    doc = await db.articles.find_one({"slug": SLUG},
                                     {"_id": 0, "featured_image_url": 1})
    if not doc.get("featured_image_url"):
        from routers.articles import _autogen_cover
        url = await _autogen_cover(SLUG, CATEGORIA)
        if url:
            await db.articles.update_one({"slug": SLUG},
                                         {"$set": {"featured_image_url": url}})
            print(f"  copertina: {url}")

    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif f"/blog/{SLUG})" in d["content"]:
            print(f"  link gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  link aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]} — controllare a mano")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
