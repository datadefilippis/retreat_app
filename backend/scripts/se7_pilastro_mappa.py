# -*- coding: utf-8 -*-
"""SE7 — la pagina pilastro: "Le discipline olistiche, una per una".

PERCHE'. Il Magazine ha 39 articoli in 12 cluster ma nessuna pagina
che intercetti la query madre ("discipline olistiche", "quali sono",
"da dove comincio") e smisti verso i cluster. Il pilastro e' quella
pagina: la parola del brand fatta articolo ("Il mondo del benessere e'
largo. Questa e' la mappa."), con ogni disciplina spiegata in tre
righe oneste e il link alla guida completa. Diventa la pagina piu'
linkante del sito e il punto naturale dove concentrare i link interni.

Categoria "scegliere": e' una guida alla scelta, non una disciplina.
Idempotente; da rieseguire in prod al lancio.

    venv/bin/python scripts/se7_pilastro_mappa.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "discipline-olistiche-la-mappa"
TITOLO = "Le discipline olistiche, una per una: la mappa"
DESCRIZIONE = ("Una mappa per orientarsi nel mondo del benessere: le "
               "principali discipline spiegate in breve, senza promesse, "
               "con la guida completa a un passo.")
CATEGORIA = "scegliere"

CONTENUTO = """Il mondo del benessere è largo, e chi ci si affaccia lo scopre subito: decine di nomi, metà in sanscrito, pratiche che si somigliano senza essere uguali, e nessuna cartina. Questa pagina è la cartina. Ogni disciplina in poche righe oneste, e per ognuna la guida completa a un passo: cos'è, cosa si sente, cosa dice la ricerca, quanto costa.

Una premessa che vale per tutte: nessuna di queste pratiche sostituisce le cure mediche, e chi le presenta come cure sta facendo un'altra cosa, spiegata nella [guida per riconoscere un operatore serio](/blog/come-capire-se-un-operatore-olistico-e-serio). Qui si parla di benessere: che è già molto, quando è raccontato per quello che è.

## Il corpo

**Il massaggio olistico** lavora sul corpo per arrivare a tutto il resto: tensioni, sonno, respiro. Le tecniche sono molte e diverse fra loro, e la [guida ai tipi di massaggio](/blog/massaggio-olistico-tipi-cosa-aspettarsi) spiega come orientarsi e cosa aspettarsi da una seduta.

**Lo shiatsu** viene dal Giappone e usa pressioni, non manipolazioni: si riceve vestiti, su un futon. [Cos'è e come funziona una seduta](/blog/shiatsu-cose-come-funziona-una-seduta).

**L'ayurveda** è il sistema tradizionale indiano: costituzioni individuali, consulti lunghi, trattamenti e una [visione del cibo](/blog/alimentazione-ayurvedica-principi-sei-sapori) tutta sua. La [guida all'ayurveda](/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi) parte dai tre dosha e arriva fino a cosa dice la ricerca.

## Il respiro e l'energia

**Il breathwork** usa il respiro come strumento attivo: dalle tecniche lente a quelle intense, che non sono per tutti. [Tecniche, benefici e controindicazioni](/blog/breathwork-cose-tecniche-benefici), da leggere prima di iscriversi a una sessione. Il ramo yogico del lavoro sul respiro è il [pranayama](/blog/pranayama-tecniche-respirazione-yoga).

**Il reiki** è una pratica energetica giapponese fatta di tocco leggero e quiete. [Cosa succede in una sessione e cosa dice la ricerca](/blog/reiki-cose-come-funziona-una-sessione), detto senza giri.

**I chakra** sono la mappa energetica che molte discipline usano come linguaggio comune: [cosa sono i sette e come si usano](/blog/chakra-cosa-sono-i-sette-come-si-usano), fra tradizione e uso contemporaneo.

## La mente

**La meditazione** è la pratica più studiata di questo mondo, e anche quella con più falsi miti. La [guida per chi inizia](/blog/meditazione-per-chi-inizia-guida-semplice) parte da zero, effetti indesiderati compresi.

**La mindfulness** nella sua forma seria è un protocollo con una storia precisa: [cos'è l'MBSR e come funziona](/blog/mindfulness-cose-mbsr-come-funziona) il percorso delle otto settimane.

**Lo yoga nidra** è il rilassamento profondo guidato, sdraiati e immobili: [cos'è e come funziona una sessione](/blog/yoga-nidra-cose-come-funziona-una-sessione).

## Il suono

**Le campane tibetane** e **il bagno di gong** usano il suono come strada verso il rilassamento: due mondi vicini ma diversi, raccontati nelle guide alle [campane](/blog/campane-tibetane-benefici-come-funzionano) e al [gong](/blog/bagno-di-gong-sound-healing-benefici).

## Il movimento

**Lo yoga** è la porta d'ingresso più comune, ed è molto più largo di come appare: la [guida allo yoga](/blog/yoga-cose-da-dove-viene-come-cominciare) racconta da dove viene e come cominciare, e quella sulle [differenze fra i tipi](/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini) aiuta a scegliere lo stile. Rami particolari come il [kriya yoga](/blog/kriya-yoga-cose-come-funziona) hanno guide proprie.

**Il camminare come pratica** va dai [bagni di foresta ai grandi cammini](/blog/camminare-bagni-di-foresta-cammini): per qualcuno è la disciplina definitiva. I [cammini italiani](/blog/cammini-italiani-quale-scegliere-la-prima-volta) meritano un capitolo a parte.

## Il femminile e il cerchio

**I cerchi di donne** sono spazi di parola e ascolto con regole precise: [cosa sono e come funzionano](/blog/cerchi-di-donne-cosa-sono-come-funzionano). E il [ciclo mestruale letto in quattro fasi](/blog/ciclo-mestruale-quattro-fasi-come-ascoltarlo) è una delle chiavi di quel mondo.

## Gli strumenti simbolici

**I tarocchi e gli oracoli** [come strumento evolutivo](/blog/tarocchi-oracoli-strumento-evolutivo), non predittivo. **Il tema natale** e [cosa aspettarsi da una lettura](/blog/lettura-tema-natale-cosa-aspettarsi), ricerca inclusa. **Le costellazioni familiari** e [cosa succede davvero in una sessione](/blog/costellazioni-familiari-cosa-sono-come-funzionano). Tre pratiche dove la serietà di chi conduce fa l'intera differenza.

## Il cibo e le rinunce

**Il digiuno consapevole e il detox**, [fra benefici reali e falsi miti](/blog/digiuno-consapevole-detox-benefici-falsi-miti). E cosa succede davvero [togliendo alcol, zucchero e caffeina](/blog/smettere-alcol-zucchero-caffeina-cosa-succede).

## Le esperienze

**I ritiri** mettono insieme pratiche, luogo e gruppo: [come scegliere il primo](/blog/come-scegliere-un-ritiro), [le domande da fare prima di prenotare](/blog/domande-da-fare-prima-di-prenotare-un-ritiro) e perfino [cosa mettere in valigia](/blog/cosa-portare-a-un-ritiro).

## Da dove cominciare

Se non sai da dove partire, tre strade oneste. La prima: [quindici minuti al giorno](/blog/kit-pratiche-quotidiane-15-minuti) di pratiche semplici, a casa, per capire cosa ti chiama. La seconda: [le pratiche contro lo stress](/blog/pratiche-olistiche-contro-stress-cosa-funziona), se il punto di partenza è quello. La terza: scegli una disciplina da questa mappa, leggi la guida, e prima di prenotare passa dalla [pagina dei prezzi](/blog/quanto-costano-pratiche-olistiche) e dalla [guida all'operatore serio](/blog/come-capire-se-un-operatore-olistico-e-serio). Il resto è pratica.

## Domande frequenti

**Cosa sono le discipline olistiche?**
Pratiche che guardano alla persona nel suo insieme: corpo, respiro, mente, relazioni. Vanno dal massaggio alla meditazione, dallo yoga al lavoro col suono. Sono pratiche di benessere, non cure: la distinzione è la prima cosa da tenere ferma.

**Le discipline olistiche sono riconosciute in Italia?**
Sono professioni non organizzate in ordini o collegi, regolate dalla legge 4/2013: si esercitano liberamente, con obblighi di trasparenza verso il cliente. Cosa significa davvero è spiegato nella guida alla legge 4/2013.

**Da dove conviene cominciare?**
Da una pratica semplice fatta con costanza, non dalla disciplina più affascinante: quindici minuti al giorno dicono più di qualunque descrizione. Poi, quando una strada chiama, la guida completa di quella disciplina spiega cosa aspettarsi.

**Le pratiche olistiche sostituiscono il medico?**
No, mai. Accompagnano il benessere, non curano le malattie: chi promette guarigioni sta superando un confine preciso, ed è il segnale più affidabile per allontanarsi."""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    assert len(TITOLO) <= 60 and 0 < len(DESCRIZIONE) <= 158
    print(f"{TITOLO}\n  slug: {SLUG}  parole: {len(CONTENUTO.split())}  "
          f"T:{len(TITOLO)} D:{len(DESCRIZIONE)}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    campi = {"title": TITOLO, "description": DESCRIZIONE,
             "content": CONTENUTO, "category": CATEGORIA,
             "author_name": "Aurya", "published": True,
             "updated_at": now, "translations": {},
             "related_slugs": ["kit-pratiche-quotidiane-15-minuti",
                               "quanto-costano-pratiche-olistiche",
                               "come-capire-se-un-operatore-olistico-e-serio"]}
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

    await aggiungi_backlink()

    # audit: il pilastro linka TANTO, e tutto risolve
    import re
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1}).to_list(100)
    slugs = {a["slug"] for a in arts}
    miei = re.findall(r"\]\(/blog/([a-z0-9-]+)\)", CONTENUTO)
    rotti_miei = [l for l in miei if l not in slugs]
    print(f"link del pilastro: {len(miei)} (unici: {len(set(miei))}), "
          f"rotti: {rotti_miei or 'nessuno'}")
    assert not rotti_miei
    assert len(set(miei)) >= 25, "il pilastro deve coprire la mappa"
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"link rotti nel Magazine: {rotti or 'nessuno'}")
    from routers.seo_shell import _extract_faq
    n = len(_extract_faq(CONTENUTO))
    print(f"FAQ estratte: {n}")
    assert n >= 4
    inbound = {a["slug"]: 0 for a in arts}
    for a in arts:
        for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]):
            if l in inbound and l != a["slug"]:
                inbound[l] += 1
    orfani = [s for s, n in inbound.items() if n == 0 and s != SLUG]
    print(f"orfani (escluso il pilastro appena nato): {orfani or 'nessuno'}")
    print(f"articoli totali: {len(arts)}")




# ── SE7b: il pilastro riceve link dagli ingressi naturali ────────────
# (aggiunto dopo la prima esecuzione: il pilastro nasceva orfano)
AGGIUNTE = [
    ("kit-pratiche-quotidiane-15-minuti",
     "e le domande da fare prima di prenotare [qui]"
     "(/blog/domande-da-fare-prima-di-prenotare-un-ritiro).",
     "e le domande da fare prima di prenotare [qui]"
     "(/blog/domande-da-fare-prima-di-prenotare-un-ritiro). E se dopo "
     "queste settimane una pratica ti chiama piu' delle altre, [la mappa "
     "delle discipline](/blog/discipline-olistiche-la-mappa) e' il posto "
     "dove capire dove porta."),
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "E le pratiche che funzionano sono quelle che percorri davvero, un "
     "respiro alla volta, sapendo cosa possono fare e cosa no.",
     "E le pratiche che funzionano sono quelle che percorri davvero, un "
     "respiro alla volta, sapendo cosa possono fare e cosa no. Per "
     "esplorare il resto del panorama, [la mappa delle discipline]"
     "(/blog/discipline-olistiche-la-mappa) le tiene tutte in una pagina."),
]


async def aggiungi_backlink() -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db
    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif f"/blog/{SLUG})" in d["content"]:
            print(f"  link gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  backlink aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
