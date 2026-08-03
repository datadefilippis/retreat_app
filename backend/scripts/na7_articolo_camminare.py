"""NA7 — camminare: si riempie l'ultima stanza vuota.

"Cammini & Natura" esisteva nella tassonomia con zero articoli, come
"Massaggio" fino a un'ora fa.

PERCHE' QUESTO PEZZO CONTA PIU' DI QUANTO SEMBRI. Il founder ha
chiesto che chi entra nel Magazine si senta invogliato a praticare.
Tutte le altre pratiche di cui scriviamo richiedono di prenotare, di
pagare o di trovare qualcuno. Questa no: si fa oggi, da soli, a costo
zero. E' l'unico articolo del Magazine la cui chiamata all'azione e'
"esci di casa", e proprio per questo e' quello che nessuno scrive,
perche' non c'e' niente da vendere in fondo.

LA COSA DA NON SBAGLIARE. Lo shinrin-yoku viene raccontato come
un'antica tradizione giapponese: e' un programma di salute pubblica,
il termine e' stato coniato nel 1982 dall'agenzia forestale
giapponese. Non e' un difetto — e' anzi il motivo per cui e' stato
studiato — ma raccontarlo come millenario e' l'ennesima antichita'
inventata.

E la ricerca va divisa: sugli indicatori di stress regge, sulle
cellule natural killer poggia su studi piccoli e in gran parte dello
stesso gruppo. Le due cose vengono citate insieme come se avessero lo
stesso peso.

    venv/bin/python scripts/na7_articolo_camminare.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "camminare-bagni-di-foresta-cammini"
TITOLO = "Camminare come pratica: bagni di foresta, cammini, natura"
DESCRIZIONE = (
    "Lo shinrin-yoku spiegato, la camminata meditativa, i cammini di più "
    "giorni e cosa dice la ricerca su quanto tempo serve stare fuori."
)
CATEGORIA = "cammini"

MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"

CONTENUTO = f"""\
Di tutte le pratiche di cui si parla in questo Magazine, questa è l'unica che puoi cominciare adesso, da solo, senza pagare niente e senza chiedere il permesso a nessuno.

È probabilmente il motivo per cui se ne parla poco: non c'è un corso da vendere, non c'è un attestato da esporre, e in fondo alla pagina non c'è niente da prenotare. Eppure è fra le pratiche con le prove migliori di tutto questo mondo.

Questa guida racconta come si cammina quando camminare è una pratica: il bagno di foresta, la camminata meditativa, il cammino di più giorni, e cosa dice la ricerca su quanto tempo serve stare fuori.

## Il bagno di foresta

**Cos'è.** *Shinrin-yoku*, letteralmente «immergersi nell'atmosfera della foresta»: stare in un bosco senza meta e senza scopo, lasciando che i sensi lavorino.

**Da dove viene, precisamente.** Il termine è stato coniato **nel 1982 dall'agenzia forestale giapponese**, dentro un programma di salute pubblica. Non è una pratica millenaria, ed è utile saperlo perché viene venduta spesso come tale. Il fatto che sia nata come politica sanitaria è anzi la ragione per cui è stata studiata seriamente: il Giappone ci ha investito ricerca.

**Come si fa, in concreto.** La differenza con una passeggiata sta tutta nel ritmo e nell'intenzione.

- **Vai piano.** Molto piano. Un'ora per un chilometro è normale. Non è un'escursione, non c'è una vetta.
- **Niente meta.** Se hai in testa un punto di arrivo, stai facendo un'altra cosa.
- **Telefono spento**, non silenzioso. Il telefono in tasca acceso continua a occupare una parte dell'attenzione.
- **Un senso alla volta.** Dieci minuti solo ad ascoltare. Dieci minuti solo a guardare i movimenti, il vento nelle foglie. Dieci minuti a toccare le cortecce. Dieci minuti a sentire gli odori, che nel bosco cambiano ogni cinquanta metri.
- **Fermati spesso.** Siediti su un tronco per venti minuti senza fare niente. È la parte in cui succede quello che deve succedere.
- **Due ore è la durata giusta.** Sotto l'ora l'effetto c'è ma è più debole.

**Cosa aspettarsi.** Nella prima mezz'ora la testa continua a produrre liste. Dopo, in genere, qualcosa si allenta. Molte persone descrivono l'ultima mezz'ora come la parte in cui smettono di pensare in frasi.

## La camminata meditativa

È un'altra cosa dal bagno di foresta, ed è più formale. La praticano molte tradizioni buddhiste, spesso alternandola alla [meditazione seduta]({MEDIT}) durante i ritiri lunghi, quando il corpo non regge altre ore ferme.

**Il protocollo.** Un percorso breve, dieci o venti passi, avanti e indietro. Si cammina lentamente, e l'attenzione sta su una cosa sola: la sensazione del piede che si stacca, si muove, appoggia. Quando la mente parte, si torna al piede.

**Perché funziona per chi non riesce a stare fermo.** Il movimento occupa il corpo quel tanto che basta a togliere l'irrequietezza, senza occupare la mente. Molte persone che hanno mollato la meditazione seduta ritrovano qui la porta.

**Si può fare ovunque.** Un corridoio, una stanza, il tratto dal parcheggio all'ufficio. Non serve un bosco: serve non avere fretta per cinque minuti.

## Il cammino di più giorni

È la versione lunga, e cambia natura rispetto a tutto il resto: non è un'ora di pratica, sono giorni in cui l'unica cosa da fare è andare avanti.

**I cammini italiani principali.** La **Via Francigena**, che attraversa il paese da nord verso Roma e oltre. Il **Cammino di San Francesco**, fra Toscana, Umbria e Lazio. Il **Cammino Materano**, in Puglia e Basilicata. Il **Sentiero Italia** del CAI, che è la rete escursionistica più lunga d'Italia e si percorre a tappe. E decine di cammini regionali più brevi, spesso meno affollati e altrettanto belli.

**Cosa succede.** I racconti si somigliano tutti su una cosa: **il terzo giorno**. I primi due il corpo protesta e la testa fa i conti. Dal terzo, quando il ritmo si stabilizza, molte persone descrivono un cambiamento di qualità del pensiero — meno liste, più cose che tornano a galla da sole.

**Cosa serve, in pratica.**
- **Venti chilometri al giorno** è la misura che regge per la maggior parte delle persone non allenate. Meglio partire da quindici.
- **Lo zaino sotto il dieci per cento del tuo peso.** È la regola che salva le spalle e le ginocchia, ed è quella che quasi tutti scoprono troppo tardi.
- **Le scarpe già usate.** Mai partire con scarpe nuove: le vesciche del primo giorno rovinano tutta la settimana.
- **La credenziale**, se il cammino la prevede: il documento che si fa timbrare lungo il percorso e che dà accesso agli alloggi per camminatori.
- **Prenotare le prime notti** e lasciare libere le successive, perché il ritmo vero lo scopri camminando.

**Da soli o in gruppo.** In solitaria si sta con sé, e per molti è il punto. In gruppo organizzato ci si toglie la logistica, ed è la formula giusta la prima volta. Se stai valutando un cammino guidato o un ritiro in natura, le domande da fare stanno [qui]({DOMANDE}).

## Cosa dice la ricerca

Qui la letteratura è più solida di quanto ci si aspetti, e va divisa in tre.

**Dove le prove sono buone.** L'esposizione alla natura riduce in modo misurabile gli **indicatori fisiologici dello stress**: cortisolo salivare, pressione arteriosa, frequenza cardiaca. È l'area più replicata, anche fuori dal Giappone.

Poi c'è un dato che vale la pena ricordare per intero. Uno studio pubblicato su *Scientific Reports* nel 2019 da White e colleghi, su un campione ampio nel Regno Unito, ha trovato che **circa 120 minuti a settimana** passati in ambienti naturali si associano a una probabilità significativamente maggiore di riportare buona salute e benessere. Sotto quella soglia l'associazione non compariva; sopra le cinque ore non cresceva più. Due ore a settimana, comunque distribuite: una passeggiata lunga o venti minuti al giorno funzionano uguale.

E uno studio del 2015 su *PNAS*, di Bratman e colleghi, ha misurato che novanta minuti di camminata in un ambiente naturale riducevano la **ruminazione** — il rimuginare a ciclo chiuso — rispetto alla stessa camminata in ambiente urbano, con una differenza visibile anche nell'attività di un'area cerebrale associata.

**Dove le prove sono più deboli.** La parte più citata dal marketing: l'effetto sulle **cellule natural killer** del sistema immunitario, attribuito ai composti volatili emessi dagli alberi. Gli studi esistono, riportano aumenti, e sono **piccoli, senza gruppi di controllo robusti e condotti in gran parte dallo stesso gruppo di ricerca**. È un filone promettente, non un fatto acquisito, e viene citato come se lo fosse.

**Quello che regge in ogni caso.** Che tu ci creda o no ai fitoncidi, due ore a settimana fuori restano una delle poche raccomandazioni di questo mondo che costano zero e hanno alle spalle numeri veri — più di [molte pratiche]({STRESS}) che si pagano.

## Se vivi in città

La ricerca sopra parla di «ambienti naturali», e non significa foresta primaria.

**I parchi contano.** Gli studi includono parchi urbani, e gli effetti sugli indicatori di stress si misurano anche lì.

**Anche gli alberi in strada.** Una via alberata percorsa lentamente non è un bosco, e non è nemmeno niente.

**Venti minuti bastano** per l'effetto acuto sul cortisolo, secondo diversi lavori. È la pausa pranzo.

**La regola pratica.** Cerca il parco più vicino, vacci tre volte a settimana per venti minuti, lascia il telefono in tasca spento. Si incastra bene con le altre abitudini brevi del [kit dei quindici minuti]({KIT}).

## Come cominciare questa settimana

**Oggi.** Venti minuti nel parco più vicino, telefono spento, senza cuffie. Cammina più lentamente di come cammini di solito.

**Questo fine settimana.** Due ore in un bosco, senza meta. Fermati venti minuti seduto da qualche parte. Aspettati che la prima mezz'ora sia inutile.

**Questo mese.** Una camminata di una giornata intera, dalla mattina al tramonto, con un pranzo nello zaino.

**Questa stagione.** Se l'idea ti resta addosso, tre giorni su un cammino. Tre giorni sono il minimo perché succeda la cosa del terzo giorno.

L'unica attrezzatura indispensabile sono scarpe comode e già usate. Tutto il resto si compra dopo, se serve, e quasi sempre non serve.

## Domande frequenti

**Che differenza c'è fra un bagno di foresta e una passeggiata?**
Il ritmo e l'assenza di meta. Una passeggiata va da qualche parte; un bagno di foresta sta in un posto e lascia lavorare i sensi, molto più lentamente di quanto sembri naturale.

**Serve una guida?**
No, si fa da soli. Le sessioni guidate esistono e possono aiutare la prima volta a rallentare davvero, che è la parte difficile.

**Quanto tempo serve perché funzioni?**
Per l'effetto immediato bastano venti minuti. Per l'associazione con il benessere generale, la ricerca indica intorno a due ore a settimana, comunque distribuite.

**Funziona anche d'inverno o con la pioggia?**
Sì, e in molti casi il bosco d'inverno è più silenzioso. Serve solo vestirsi in modo da non pensare al freddo.

**È vero che gli alberi rafforzano il sistema immunitario?**
È il filone più citato e il meno solido: gli studi sono piccoli e in gran parte dello stesso gruppo. Gli effetti sullo stress, invece, sono ben documentati.

**Posso farlo con i bambini?**
Sì, cambiando l'aspettativa: con i bambini il silenzio non c'è, e l'esplorazione prende il posto della contemplazione. Vale comunque.

**Quanti chilometri al giorno su un cammino?**
Quindici per cominciare, venti quando il corpo si è abituato. Chi parte a venticinque il primo giorno di solito si ferma il terzo.

**Camminare sostituisce la meditazione?**
No, sono cose diverse, ma la camminata meditativa è spesso la porta d'ingresso per chi non riesce a stare seduto. Le due si sostengono, come si sostengono con il [lavoro sul respiro]({PRANA}).
"""

AGGIUNTE = [
    ("kit-pratiche-quotidiane-15-minuti", "## Domande frequenti",
     f"La pratica che sta fuori da questo kit perche' vuole piu' tempo, e "
     f"che ha alle spalle numeri altrettanto solidi, e' camminare: "
     f"[bagni di foresta, camminata meditativa e cammini](/blog/{SLUG}).\n\n"
     f"## Domande frequenti"),
    ("meditazione-per-chi-inizia-guida-semplice", "## Domande frequenti",
     f"E se stare seduti resta il problema, esiste una forma che si pratica "
     f"in movimento: la [camminata meditativa](/blog/{SLUG}), che molte "
     f"tradizioni alternano alla pratica seduta.\n\n## Domande frequenti"),
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
        "related_slugs": ["meditazione-per-chi-inizia-guida-semplice",
                          "kit-pratiche-quotidiane-15-minuti",
                          "pratiche-olistiche-contro-stress-cosa-funziona"],
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
