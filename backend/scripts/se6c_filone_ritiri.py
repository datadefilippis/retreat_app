# -*- coding: utf-8 -*-
"""SE6c — il filone ritiri lato partecipante: scegliere e prepararsi.

DUE INTENTI DIVERSI, gia' mappati nell'analisi SEO. "Come scegliere un
ritiro" e' la domanda di chi decide (tipo, durata, budget) e completa
le "ventidue domande" gia' pubblicate, che restano la guida al
controllo di QUEL ritiro; "cosa portare" e' long-tail puro, cercato da
chi ha gia' prenotato, con concorrenza debole. Insieme presidiano il
percorso del partecipante in fase rete: al flip del marketplace
diventano il funnel d'acquisto gia' indicizzato.

EFFETTO COLLATERALE VOLUTO: la categoria "ritiri" del Magazine era
VUOTA (hub in noindex). Con questi due articoli si accende: entra in
sitemap e la guardia BN5 del noindex-se-vuota smette di valere per lei.

Cifre: solo quelle gia' pubblicate (400-1500 euro dal pezzo delle
domande). Idempotente; da rieseguire in prod al lancio.

    venv/bin/python scripts/se6c_filone_ritiri.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

ARTICOLI = [
    {
        "slug": "come-scegliere-un-ritiro",
        "title": "Come scegliere un ritiro: tipo, durata e budget",
        "description": ("Il primo ritiro: capire quale tipo fa per te, "
                        "quanto deve durare, che budget serve e come "
                        "leggere un programma prima di innamorartene."),
        "category": "ritiri",
        "related": ["domande-da-fare-prima-di-prenotare-un-ritiro",
                    "quanto-costano-pratiche-olistiche",
                    "cosa-portare-a-un-ritiro"],
        "content": """Dieci schede aperte nel browser, e tutte dicono le stesse cose: natura, silenzio, cibo sano, «un viaggio dentro te stesso». Le foto sono intercambiabili, i programmi si somigliano, i prezzi no. E la domanda vera resta senza risposta: come si capisce quale ritiro è quello giusto?

Si capisce partendo dalla fine, non dall'inizio. Non «quale ritiro è bello» ma «cosa voglio che sia successo quando torno a casa». Le risposte oneste sono poche, e ognuna porta a ritiri diversi.

## La domanda che viene prima del catalogo

**Voglio riposare.** Sonno, cibo fatto da altri, niente decisioni. Allora cerchi un ritiro con poca struttura e tanta libertà: pratiche facoltative, tempo vuoto difeso nel programma. Un ritiro con la giornata piena dalle sette alle ventuno ti restituirà a casa più stanco di prima.

**Voglio imparare una pratica.** Allora conta chi insegna, molto più del posto. Cerchi un programma con ore di pratica vere, un conduttore di cui puoi leggere formazione e percorso, e un gruppo piccolo abbastanza da avere correzioni. La [guida allo yoga](/blog/yoga-cose-da-dove-viene-come-cominciare) e quella alla [meditazione](/blog/meditazione-per-chi-inizia-guida-semplice) aiutano a capire cosa aspettarsi dalla pratica stessa.

**Voglio lavorare su qualcosa.** Un passaggio di vita, un lutto, una decisione. Qui la serietà di chi conduce non è un dettaglio ma l'intera questione: i formati intensi che promettono trasformazioni in un weekend meritano il doppio delle domande, e la [guida per capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio) è il posto da cui partire.

**Voglio staccare e camminare.** Forse non cerchi un ritiro ma un cammino, che è un'esperienza diversa: più economica, più solitaria, più fisica. I [cammini italiani](/blog/cammini-italiani-quale-scegliere-la-prima-volta) sono un mondo a sé, e per qualcuno funzionano meglio di qualunque sala.

## La durata

Per un primo ritiro il weekend lungo, due o tre notti, è la misura giusta: abbastanza per staccare davvero, abbastanza poco da non rischiare troppo su un formato che non conosci. La settimana intera ha senso quando sai già che la pratica ti regge e che il silenzio prolungato non ti spaventa. Diffida dell'idea che di più sia meglio: un buon weekend lascia più di una settimana sbagliata.

## Il budget

Un ritiro di quattro giorni in Italia costa fra i quattrocento e i millecinquecento euro. La forchetta è larga perché dentro ci sono cose diverse: la sistemazione (camera condivisa o singola), i pasti, il numero di conduttori, la dimensione del gruppo. Prima di confrontare i prezzi, confronta cosa includono: un ritiro a 500 euro con camera doppia e pratiche in gruppo da venti non è più economico di uno a 700 con singola e gruppo da dieci, è un prodotto diverso. Il quadro dei prezzi delle pratiche, per capire se le singole voci sono ragionevoli, è nella [pagina dei prezzi](/blog/quanto-costano-pratiche-olistiche).

## Leggere il programma come un adulto

Tre controlli veloci separano i programmi seri dalle brochure. Il primo: le ore. Somma le ore di pratica dichiarate e guarda quanto tempo libero resta; se la giornata è piena da sveglia a cena, torni stanco. Il secondo: i nomi. Chi conduce ha nome, cognome e un percorso verificabile, o è «il nostro team di facilitatori»? Il terzo: le promesse. «Imparerai le basi del pranayama» è una promessa onesta; «guarirai le tue ferite» non lo è, e la differenza non è di stile.

Quando un ritiro passa questi tre controlli, arriva il momento delle domande vere, quelle da fare per iscritto prima di versare un acconto: sono [ventidue, e stanno qui](/blog/domande-da-fare-prima-di-prenotare-un-ritiro). E quando il posto è bloccato, resta solo il pensiero più leggero: [la valigia giusta](/blog/cosa-portare-a-un-ritiro).

## Domande frequenti

**Qual è la durata giusta per un primo ritiro?**
Un weekend lungo, due o tre notti: abbastanza per staccare, abbastanza poco da non rischiare molto su un formato che ancora non conosci.

**Quanto costa un ritiro in Italia?**
Un ritiro di quattro giorni costa in genere fra i quattrocento e i millecinquecento euro. Prima di confrontare i prezzi, confronta cosa includono: sistemazione, pasti, dimensione del gruppo e conduzione spiegano quasi tutta la differenza.

**Serve esperienza per partecipare?**
Per la maggior parte dei ritiri no, e un programma serio lo dice chiaramente, indicando a chi si rivolge. Se un formato richiede esperienza, il programma deve dirlo prima, non a caparra versata.

**Ritiro o cammino?**
Sono esperienze diverse: il ritiro è un luogo e un gruppo, il cammino è un movimento e spesso una solitudine. Chi cerca soprattutto di staccare e stancarsi bene a volte trova nel cammino quello che cercava in un ritiro, a un costo minore.""",
    },
    {
        "slug": "cosa-portare-a-un-ritiro",
        "title": "Cosa portare a un ritiro: la lista che serve davvero",
        "description": ("La valigia per un ritiro di yoga o meditazione: "
                        "cosa serve, cosa lasciare a casa e le tre cose "
                        "che quasi tutti dimenticano."),
        "category": "ritiri",
        "related": ["come-scegliere-un-ritiro",
                    "domande-da-fare-prima-di-prenotare-un-ritiro",
                    "kit-pratiche-quotidiane-15-minuti"],
        "content": """La valigia è aperta sul letto da mezz'ora e il problema non è cosa metterci: è che non sai dove stai andando davvero. Un ritiro non è una vacanza e non è un corso; la valigia giusta sta nel mezzo, ed è più leggera di quella che stai immaginando.

La regola che risolve quasi tutto: porta metà dei vestiti che pensi e il doppio degli strati. Poi ci sono le cose che nessuna lista generica ti dice, e le tre che quasi tutti dimenticano.

## Prima di fare la valigia: due domande all'organizzatore

Ogni ritiro serio risponde volentieri a due domande pratiche. La prima: cosa è fornito? Tappetini, cuscini di meditazione, coperte per il rilassamento di solito ci sono, ma «di solito» non è una risposta: chiedi. La seconda: qual è la politica sui telefoni? Alcuni ritiri chiedono il silenzio digitale, altri no; saperlo prima cambia cosa porti e come organizzi chi resta a casa.

Se queste due risposte tardano ad arrivare, hai imparato qualcosa che vale più della lista: le [domande da fare prima di prenotare](/blog/domande-da-fare-prima-di-prenotare-un-ritiro) esistono esattamente per questo.

## Per la pratica

Abbigliamento comodo a strati: leggings o pantaloni morbidi, maglie che non stringono, una felpa che si mette e si toglie senza cerimonie. Il corpo in pratica si scalda e si raffredda in fretta, e le sale la mattina presto sono più fredde di quanto prometta la foto col tramonto. Calze antiscivolo o calze di lana per le pratiche a terra. Se hai un tuo tappetino e ci sei affezionato portalo, ma solo dopo aver chiesto se serve.

## Per la persona

Una borraccia, perché le bottigliette non sono lo stile di questi posti. I farmaci personali, con la stessa serietà di qualunque viaggio, e tutto ciò che riguarda la tua salute detto all'organizzatore prima, non a cena. Scarpe comode per camminare, perché quasi ogni ritiro ha un fuori. Il necessario da bagno essenziale, in strutture che spesso hanno più natura che mensole.

Carta e penna. Sembra un dettaglio d'altri tempi ed è una delle cose più usate in assoluto: dopo una pratica si scrive volentieri, e farlo sul telefono non è la stessa cosa.

## Le tre cose che quasi tutti dimenticano

**I tappi per le orecchie.** Le camere condivise sono la norma nei ritiri, e il sonno è metà del ritiro.

**Uno strato caldo vero.** Maglione o pile: le meditazioni serali e i rilassamenti finali si fanno da fermi, e da fermi fa freddo anche d'estate.

**Una torcia o frontalino.** Le strutture nella natura hanno sentieri, e i sentieri di notte sono bui davvero.

## Cosa lasciare a casa

Il laptop, salvo che la politica del ritiro dica altro e tu abbia un motivo vero. I libri in quantità: uno basta, e spesso resta chiuso. E l'aspettativa di una versione precisa dell'esperienza: la valigia più pesante è quella delle idee su come dovrà essere. Se il ritiro è ancora da scegliere, [il criterio giusto parte da un'altra domanda](/blog/come-scegliere-un-ritiro).

## Domande frequenti

**Devo portare il tappetino da yoga?**
Di solito è fornito dalla struttura, ma va chiesto prima: è una delle due domande pratiche da fare all'organizzatore insieme alla politica sui telefoni.

**Posso portare il telefono a un ritiro?**
Dipende dal ritiro: alcuni chiedono il silenzio digitale, altri si limitano a chiederne un uso discreto. Chiedi la politica prima di partire e organizza di conseguenza chi resta a casa.

**Come ci si veste a un ritiro?**
A strati e comodi: il corpo in pratica si scalda e si raffredda in fretta, e le sale al mattino sono fredde. Leggings o pantaloni morbidi, maglie comode, una felpa, calze per le pratiche a terra e uno strato caldo vero per le sessioni serali.

**Cosa dimenticano tutti?**
Tappi per le orecchie (le camere condivise sono la norma), uno strato caldo per le pratiche da fermi e una torcia per i sentieri di notte.""",
    },
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for art in ARTICOLI:
        assert len(art["title"]) <= 60, art["slug"]
        assert 0 < len(art["description"]) <= 158, art["slug"]
        print(f"{art['title']}\n  slug: {art['slug']}  "
              f"parole: {len(art['content'].split())}  "
              f"T:{len(art['title'])} D:{len(art['description'])}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    for art in ARTICOLI:
        esistente = await db.articles.find_one({"slug": art["slug"]},
                                               {"_id": 0, "id": 1})
        campi = {"title": art["title"], "description": art["description"],
                 "content": art["content"], "category": art["category"],
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
            url = await _autogen_cover(art["slug"], art["category"])
            if url:
                await db.articles.update_one(
                    {"slug": art["slug"]},
                    {"$set": {"featured_image_url": url}})
                print(f"  copertina: {url}")

    # audit: link, FAQ, orfani, e la categoria ritiri che si accende
    import re
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1,
                                   "category": 1}).to_list(100)
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\nlink rotti: {rotti or 'nessuno'}")
    from routers.seo_shell import _extract_faq
    for art in ARTICOLI:
        n = len(_extract_faq(art["content"]))
        print(f"  FAQ estratte da {art['slug'][:40]}: {n}")
        assert n >= 3
    n_ritiri = sum(1 for a in arts if a.get("category") == "ritiri")
    print(f"categoria ritiri: {n_ritiri} articoli (prima era vuota)")
    inbound = {a["slug"]: 0 for a in arts}
    for a in arts:
        for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]):
            if l in inbound and l != a["slug"]:
                inbound[l] += 1
    orfani = [s for s, n in inbound.items() if n == 0]
    print(f"orfani: {orfani or 'nessuno'}")
    print(f"articoli totali: {len(arts)}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
