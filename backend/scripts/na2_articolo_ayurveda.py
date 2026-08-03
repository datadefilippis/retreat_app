"""NA2 — l'ayurveda: si apre una stanza nuova del Magazine.

PERCHE' UNA CATEGORIA SUA. Non entra sotto "massaggio", che nella
tassonomia dei ritiri e' bodywork, ne' sotto "energia": e' un sistema
intero, con una diagnostica, una dietetica e una farmacopea proprie. E
in Italia e' fra le discipline piu' cercate e meno spiegate.

LA PARTE CHE NESSUNO SCRIVE, ed e' il motivo per cui questo pezzo ha
un dovere in piu' degli altri: i METALLI PESANTI. Le indagini
pubblicate su JAMA da Saper e colleghi (2004 e 2008) hanno trovato
piombo, mercurio o arsenico in una quota rilevante dei preparati
ayurvedici analizzati, soprattutto quelli della tradizione rasa
shastra, che li contiene per scelta e non per contaminazione. E'
un'informazione di sicurezza che riguarda chiunque compri erbe
ayurvediche online, e in italiano non la scrive quasi nessuno.

L'ALTRO CONFINE: in India l'ayurveda e' una laurea di cinque anni e
mezzo dentro il servizio sanitario. In Italia no. Chi la pratica qui
non e' un medico, e la distanza fra le due cose e' la fonte principale
di equivoci.

COSA RESTA UTILE, e resta molto: la routine, l'attenzione alla
digestione e al sonno, i principi alimentari, l'automassaggio. Sono a
rischio zero e si provano stasera.

    venv/bin/python scripts/na2_articolo_ayurveda.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
TITOLO = "Ayurveda: cos'è, i tre dosha e cosa aspettarsi da una visita"
DESCRIZIONE = (
    "Il sistema, la costituzione, come si svolge un consulto, i trattamenti, "
    "cosa dice la ricerca e la questione dei metalli pesanti nelle erbe."
)
CATEGORIA = "ayurveda"

YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DETOX = "/blog/digiuno-consapevole-detox-benefici-falsi-miti"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"

CONTENUTO = f"""\
L'ayurveda arriva in Italia quasi sempre da una porta laterale: un massaggio con l'olio caldo in una spa, un test online che ti dice che sei *pitta*, un barattolo di ashwagandha comprato dopo un articolo.

Sono tre frammenti di un sistema che in India è una laurea di cinque anni e mezzo e fa parte del servizio sanitario nazionale.

Questa guida racconta l'insieme: da dove viene, come ragiona, cosa succede in un consulto vero, cosa dice la ricerca, e due cose che riguardano la tua sicurezza e che in italiano quasi nessuno scrive.

## Cos'è

*Ayurveda* si traduce di solito con «scienza della vita», dalle parole sanscrite *ayus*, vita, e *veda*, conoscenza.

È un sistema medico tradizionale indiano che si occupa insieme di alimentazione, routine quotidiana, sonno, preparati vegetali, trattamenti manuali e procedure di purificazione. La sua logica di fondo è diversa da quella occidentale: invece di partire dalla malattia e cercare il rimedio, parte dalla persona e cerca quello che nella sua vita alimenta lo squilibrio.

Da qui viene la cosa che colpisce chi ci si avvicina: due persone con lo stesso sintomo possono ricevere indicazioni opposte.

## Da dove viene

I testi fondativi sono di un'antichità considerevole e ancora in uso.

**La Charaka Samhita**, il trattato di medicina interna, e **la Sushruta Samhita**, quello chirurgico, sono composti fra alcuni secoli prima e alcuni dopo l'era volgare. Il secondo descrive procedure di chirurgia ricostruttiva che sono state riconosciute come notevoli anche dalla storiografia medica occidentale.

**In India oggi** l'ayurveda è una professione regolata: il titolo si chiama BAMS, dura cinque anni e mezzo più tirocinio, ha un ministero dedicato e ospedali pubblici.

**In Italia no.** Chi pratica ayurveda qui non è un medico e non può esercitare atti medici, a meno che non sia anche laureato in medicina. È la distanza fra i due paesi a generare quasi tutti gli equivoci, e conviene tenerla presente da subito.

## I tre dosha

È la parte che tutti hanno sentito nominare e quasi nessuno spiega bene.

L'ayurveda descrive cinque elementi — spazio, aria, fuoco, acqua, terra — che si combinano in tre principi funzionali, i **dosha**. Non sono personalità: sono descrizioni di *come funziona un corpo*, cioè come si muove, come trasforma, come tiene insieme.

**Vata — il movimento.** Aria e spazio. Governa tutto ciò che si sposta: respiro, circolazione, impulsi nervosi, transito intestinale, pensieri. Chi ha vata dominante tende a essere magro, rapido, freddoloso, creativo e irregolare. Quando è in eccesso porta insonnia, ansia, secchezza, gonfiore, digestione capricciosa.

**Pitta — la trasformazione.** Fuoco e acqua. Governa la digestione, il metabolismo, la temperatura, la capacità di analizzare. Chi ha pitta dominante tende a essere di corporatura media, caloroso, con appetito forte, determinato, a volte insofferente. In eccesso porta acidità, infiammazione, irritabilità, problemi della pelle.

**Kapha — la struttura.** Acqua e terra. Governa la solidità, l'idratazione, l'immunità, la stabilità emotiva. Chi ha kapha dominante tende a essere robusto, resistente, calmo, lento a scaldarsi e lento a mollare. In eccesso porta pesantezza, ristagno, aumento di peso, apatia, muco.

Due precisazioni che cambiano tutto.

**Ci sono tutti e tre in tutti.** Nessuno è «un vata». Ognuno ha una proporzione propria, che l'ayurveda chiama *prakriti*, la costituzione di nascita, e che non cambia.

**Quello che cambia è lo squilibrio.** Si chiama *vikriti*, ed è lo stato attuale. Il lavoro dell'ayurveda è tutto lì: riportare il presente verso la costituzione, non trasformare la costituzione.

I test online confondono queste due cose sistematicamente, ed è il motivo per cui danno risultati diversi a distanza di un mese. Sono un gioco, e come tale valgono.

## Cosa succede in un consulto

Un primo incontro serio dura fra i sessanta e i novanta minuti, e la maggior parte del tempo si parla.

**Il colloquio.** Molto lungo e molto concreto: come dormi, a che ora hai fame, com'è la digestione dopo i pasti, come vanno le evacuazioni, come reagisci al freddo, quanto ti stanchi, come sono le tue giornate. Chi conduce sta ricostruendo un profilo funzionale, e le domande sulla pancia sono la parte più importante.

**L'osservazione.** Costituzione fisica, pelle, capelli, unghie, occhi, e la lingua, che nell'ayurveda è una mappa dello stato digestivo.

**Il polso.** *Nadi pariksha*: tre dita sull'arteria radiale, qualche minuto in silenzio. È la parte più suggestiva e la meno verificabile. Un professionista misurato lo presenta come uno strumento fra gli altri; chi ti dice di leggerti il fegato dal polso sta esagerando.

**Le indicazioni.** Quasi sempre in quest'ordine: alimentazione, routine quotidiana, sonno, movimento, e solo dopo eventuali preparati o trattamenti.

In Italia un primo consulto costa in genere fra gli 80 e i 150 euro, i controlli meno. Un professionista serio ti dice il prezzo prima e non ti vende i suoi prodotti nella stessa seduta in cui te li prescrive.

## I trattamenti

**Abhyanga.** Il massaggio con olio caldo, di solito di sesamo, su tutto il corpo. È il trattamento ayurvedico più diffuso in Occidente e il più semplice, e nella versione domestica si può fare da soli. Dura circa un'ora, costa fra i 60 e i 100 euro.

**Shirodhara.** Un filo continuo di olio tiepido versato sulla fronte per venti o quaranta minuti. L'effetto riportato è un rilassamento profondo, e chi lo prova lo descrive come una delle esperienze più insolite di questo mondo.

**Swedana.** Bagno di vapore alle erbe, spesso dopo l'abhyanga, per aiutare l'olio a penetrare.

**Panchakarma.** La procedura di purificazione completa: dura da una a tre settimane e comprende, a seconda del protocollo, purghe, emesi indotta, clisteri medicati. **Non è un pacchetto benessere.** È una procedura intensa che in India si fa sotto supervisione medica, e va valutata con serietà — molte delle sue componenti sono controindicate in gravidanza, in età avanzata, con patologie cardiache o gastrointestinali, con disturbi del comportamento alimentare. Le versioni di tre giorni proposte come «panchakarma» in molte spa sono un'altra cosa, di solito una serie di massaggi, e sarebbe più corretto chiamarle così. Su come si distingue un percorso serio da un pacchetto, valgono le stesse regole del [digiuno e del detox]({DETOX}).

## Cosa dice la ricerca

Il quadro va diviso, perché mettere tutto insieme fa perdere l'informazione utile.

**Dove ci sono prove.** Alcuni singoli preparati sono stati studiati con metodi convenzionali e con risultati incoraggianti: la **curcuma** per il dolore da osteoartrosi, l'**ashwagandha** su stress percepito e qualità del sonno, il **triphala** sulla regolarità intestinale. Sono studi su singole sostanze, non validazioni del sistema.

**Dove le prove sono deboli.** Il modello dei dosha non ha riscontro nella fisiologia, e la diagnosi dal polso non ha mostrato riproducibilità nelle verifiche condotte. Sono strumenti interni a un sistema di pensiero, e vanno presi per quello.

**Dove non ce ne sono.** Nessuno studio sostiene che l'ayurveda curi patologie oncologiche, autoimmuni o metaboliche gravi. Chi lo afferma sta facendo un'altra cosa, e in Italia sta anche commettendo un reato.

Vale la pena notare una cosa: la parte dell'ayurveda meno esotica — mangiare a orari regolari, cenare presto e leggero, dormire abbastanza, muoversi ogni giorno, adattare le abitudini alla stagione — è anche quella che la ricerca contemporanea sostiene di più, arrivandoci per strade completamente diverse.

## La questione dei metalli pesanti

Questa parte riguarda la tua sicurezza e in italiano si legge di rado.

Una porzione della farmacopea ayurvedica appartiene a una tradizione chiamata **rasa shastra**, che include intenzionalmente metalli — piombo, mercurio, arsenico — in preparati sottoposti a lunghi processi di trasformazione. Nella tradizione quei processi li renderebbero sicuri.

Le analisi indipendenti dicono altro. Due indagini pubblicate su *JAMA* da Robert Saper e colleghi, nel 2004 e nel 2008, hanno esaminato preparati ayurvedici in commercio: la prima su prodotti venduti in negozi dell'area di Boston, la seconda su prodotti acquistati via internet da siti indiani e statunitensi. In entrambe **circa un prodotto su cinque conteneva piombo, mercurio o arsenico**, in diversi casi in quantità che superavano ampiamente i limiti giornalieri accettati. Sono documentati casi clinici di **avvelenamento da piombo** in persone che assumevano questi preparati.

Cosa farne, in pratica:

- **Non comprare preparati ayurvedici online** da venditori che non puoi verificare.
- **Preferisci prodotti con analisi dichiarate** sui metalli pesanti e conformi alla normativa europea sugli integratori.
- **Diffida delle formule tradizionali complesse** dai nomi sanscriti, che sono quelle in cui il rischio si concentra. Le singole erbe di uso alimentare — curcuma, zenzero, ashwagandha da fornitori europei — sono un'altra categoria.
- **Se sei in gravidanza, allatti, o dai qualcosa a un bambino**, questa cautela vale doppio.
- **Dillo al tuo medico** se stai assumendo preparati: alcune erbe interagiscono con farmaci comuni, anticoagulanti e tiroidei fra i primi.

Nessuna di queste righe demolisce l'ayurveda. Servono a distinguere la parte alimentare e comportamentale, che è a rischio molto basso, dalla farmacopea, che va trattata con la stessa serietà di qualsiasi altra sostanza che si ingerisce.

## Come si sceglie chi ti segue

Valgono i criteri generali di [come capire se un operatore è serio]({SERIO}), con quattro specificità.

**Dichiara la formazione, e dove.** Le scuole italiane serie durano anni, non fine settimana. Chi ha studiato in India lo dice e sa dirti dove.

**Distingue il proprio ruolo.** «Non sono un medico» è una frase che un professionista onesto dice per primo, senza che tu la chieda.

**Non tocca le terapie in corso.** Nessuna riduzione di farmaci, nessun «vedrai che poi non ti servirà più».

**Non vende quello che prescrive** nella stessa seduta, o se lo fa, te lo dichiara come conflitto e ti lascia libero di comprare altrove.

## Cosa puoi provare da solo

La parte a rischio zero, e non è la meno interessante.

**La routine.** L'ayurveda chiama *dinacharya* la giornata regolare: svegliarsi e coricarsi a orari stabili, il pasto principale a mezzogiorno quando la capacità digestiva è al massimo, cena leggera e presto. È la raccomandazione più antica del sistema, e la più sostenuta dalla cronobiologia contemporanea.

**L'automassaggio con l'olio.** Cinque minuti prima della doccia, con olio di sesamo tiepido, dai piedi verso il cuore. Costa poco, si fa a casa, e chi lo prova per due settimane in inverno di solito non smette.

**Il raschietto per la lingua.** Al mattino, prima di lavare i denti. È l'abitudine ayurvedica che più spesso resta.

**L'acqua calda.** Un bicchiere appena sveglio, e acqua tiepida invece che fredda durante i pasti. Nel sistema serve a non spegnere il fuoco digestivo.

**Mangiare seduti e senza schermo.** Banale, ed è la raccomandazione che cambia di più la digestione delle persone che la seguono.

Se già pratichi [yoga]({YOGA}) o [tecniche di respiro]({PRANA}), queste abitudini si incastrano naturalmente: nascono dalla stessa cultura e si presuppongono a vicenda.

## Domande frequenti

**L'ayurveda è una medicina?**
In India sì, con una laurea di cinque anni e mezzo e un ruolo nel sistema sanitario. In Italia no: chi la pratica non è un medico e non può fare diagnosi né prescrivere terapie.

**Come faccio a sapere qual è la mia costituzione?**
Solo con un consulto, e nemmeno subito: serve un professionista che osservi e faccia domande. I test online confondono la costituzione di nascita con lo squilibrio del momento, ed è il motivo per cui danno risultati diversi ogni volta.

**I trattamenti ayurvedici fanno dimagrire?**
Le indicazioni alimentari e la routine possono contribuire, come qualsiasi cambiamento di abitudini sostenuto nel tempo. I massaggi no, e chi li vende come dimagranti sta vendendo altro.

**Le erbe ayurvediche sono sicure?**
Le singole spezie di uso alimentare da fornitori europei sì. I preparati tradizionali complessi vanno trattati con cautela: analisi indipendenti hanno trovato metalli pesanti in una quota rilevante dei campioni, e ne parliamo nella sezione dedicata qui sopra.

**Quanto costa un percorso?**
Un primo consulto in Italia va dagli 80 ai 150 euro, un abhyanga dai 60 ai 100. I percorsi in struttura costano molto di più e vanno valutati come si valuta un ritiro.

**Posso fare ayurveda se sto assumendo farmaci?**
Le indicazioni alimentari e di routine sì, sempre. Per qualsiasi preparato da ingerire, parlane prima con il medico che ti segue: alcune erbe interferiscono con anticoagulanti, antidiabetici e farmaci tiroidei.

**Panchakarma e detox sono la stessa cosa?**
No. Il panchakarma è una procedura medica intensa che in India si fa sotto supervisione. Quello che molte strutture chiamano panchakarma è una settimana di massaggi e alimentazione leggera, che è una cosa legittima con un altro nome.

**Da dove comincio se voglio provare?**
Dalla routine e dall'automassaggio, che non costano niente e non hanno controindicazioni. Il consulto ha senso dopo, quando hai qualcosa da raccontare su come stai.
"""

AGGIUNTE = [
    ("digiuno-consapevole-detox-benefici-falsi-miti", "## Domande frequenti",
     f"Un sistema che sul tema della purificazione ha una posizione molto "
     f"piu' articolata e' l'[ayurveda](/blog/{SLUG}), dove il panchakarma e' "
     f"una procedura medica e non un pacchetto benessere.\n\n"
     f"## Domande frequenti"),
    ("yoga-cose-da-dove-viene-come-cominciare", "## Domande frequenti",
     f"Dalla stessa cultura arriva l'[ayurveda](/blog/{SLUG}), che dello "
     f"yoga e' considerata la sorella: una si occupa della pratica, l'altra "
     f"di come vivi il resto della giornata.\n\n## Domande frequenti"),
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
        "related_slugs": ["yoga-cose-da-dove-viene-come-cominciare",
                          "digiuno-consapevole-detox-benefici-falsi-miti",
                          "come-capire-se-un-operatore-olistico-e-serio"],
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
