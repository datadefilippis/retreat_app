# -*- coding: utf-8 -*-
"""ED1 — prima uscita del piano espansione: la naturopatia.

PERCHE' QUESTO PEZZO PER PRIMO. Query ad alto volume («naturopata»,
«naturopatia cos'e'»), SERP dominate da scuole che vendono corsi e
blog promozionali: l'angolo guida-del-consumatore (cosa fa e cosa NO,
cosa regge alla prova della ricerca, come riconoscere chi lavora bene)
e' scoperto. Ed e' il pezzo che apre la categoria nuova "naturopatia"
(modello+palette+sigillo aggiunti in questo stesso ciclo), dove
arriveranno aromaterapia e fitoterapia.

ONESTA' DELLE FONTI. La revisione sistematica sui fiori di Bach e'
citata E linkata (Ernst 2010, Swiss Medical Weekly — PubMed 20734279,
verificato). Nessun prezzo: non abbiamo forchette verificate per i
consulti naturopatici, e inventarle non e' un'opzione. Il pezzo entra
anche nella mappa delle discipline e riceve un backlink dall'ancora
naturale nella guida all'operatore serio.

    venv/bin/python scripts/ed1_articolo_naturopatia.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "naturopatia-cose-consulto-cosa-dice-ricerca"
TITOLO = "Naturopatia: cos'è, il consulto e cosa dice la ricerca"
DESCRIZIONE = ("Cosa fa un naturopata e cosa no, come si svolge un "
               "consulto, cosa regge alla prova della ricerca e come "
               "riconoscere chi lavora seriamente.")
CATEGORIA = "naturopatia"

CONTENUTO = """La targhetta accanto al campanello dice «Naturopata». Dentro, una persona che ti ascolterà per un'ora parlando di sonno, digestione, energia e abitudini. La domanda che ti porti dietro salendo le scale è legittima e ha una risposta meno semplice di quanto sembri: che cos'è, esattamente, un naturopata?

Questa guida risponde come sempre: cosa è, cosa non è, cosa succede in un consulto, cosa dice la ricerca. Senza vendere niente, perché non abbiamo niente da venderti.

## Cos'è la naturopatia

La naturopatia è un approccio non sanitario al benessere che punta sulle capacità di riequilibrio della persona: alimentazione, stile di vita, rimedi di origine naturale, tecniche di rilassamento. Le radici stanno nei movimenti igienisti e della «cura naturale» fra Ottocento e Novecento, fra Europa centrale e Stati Uniti; la forma attuale è un contenitore che cambia molto da scuola a scuola.

In Italia il naturopata è una professione non organizzata: nessun albo, nessun percorso di Stato, nessun titolo abilitante. La cornice è quella della [legge 4/2013](/blog/legge-4-2013-professioni-olistiche), che permette l'esercizio libero e chiede in cambio trasparenza. Questo significa una cosa concreta: la parola «naturopata» sulla targhetta non garantisce, da sola, nessun percorso formativo. Esistono scuole serie con corsi pluriennali ed esistono attestati da un weekend; distinguere è compito di chi sceglie, e più sotto c'è il come.

## Cosa fa, e cosa non fa

Un naturopata serio lavora sull'educazione al benessere: osserva le abitudini, propone aggiustamenti di alimentazione e stile di vita, suggerisce rimedi naturali e tecniche di gestione dello stress, accompagna nel tempo.

Quello che non può fare è tutto ciò che è sanitario: **non fa diagnosi, non prescrive farmaci, non cura malattie, non sostituisce il medico**. Non è una limitazione di stile: è il confine di legge che separa le professioni non organizzate da quelle sanitarie. Il naturopata che «diagnostica» un'intolleranza, che promette di curare una patologia o che suggerisce di ridurre una terapia sta superando quel confine, e la cosa migliore da fare è alzarsi e uscire.

## Come si svolge un consulto

Il primo incontro è soprattutto un colloquio, più lungo di una visita medica: si parla di sonno, digestione, energia nelle diverse ore del giorno, alimentazione, stress, storia personale. Molti naturopati usano griglie di osservazione proprie della disciplina, dalla lettura della costituzione ad analisi non convenzionali: vale la pena sapere che queste ultime non hanno validità diagnostica, qualunque nome portino.

Alla fine arriva di solito una proposta: cambiamenti nelle abitudini, un piano alimentare orientativo, rimedi. È il momento di fare domande: perché questo rimedio, cosa contiene, per quanto tempo, con quali controlli. Le risposte, e la disponibilità a darle, dicono molto della persona che hai davanti.

## Cosa dice la ricerca

Qui serve la distinzione più importante dell'articolo, perché «la naturopatia funziona?» sono in realtà tre domande diverse.

**Il sistema nel suo insieme** ha poche prove: gli studi di qualità sull'efficacia della naturopatia come approccio complessivo sono scarsi, e quelli esistenti sono difficili da interpretare perché ogni naturopata combina strumenti diversi.

**Le componenti di buon senso** stanno in piedi da sole: mangiare meglio, dormire di più, muoversi, gestire lo stress sono raccomandazioni solide che la naturopatia condivide con la medicina, non un suo brevetto. Se un consulto ti porta a fare queste cose, ti fa bene — ma ti avrebbe fatto bene comunque.

**I singoli rimedi vanno giudicati uno per uno.** La fitoterapia dipende dalla pianta: per alcune esistono studi seri, e proprio per questo esistono anche interazioni reali con i farmaci — l'iperico, per fare l'esempio più noto, interferisce con molti medicinali comuni. I fiori di Bach invece hanno una risposta chiara: la [revisione sistematica degli studi clinici randomizzati](https://pubmed.ncbi.nlm.nih.gov/20734279/) pubblicata da Edzard Ernst su *Swiss Medical Weekly* nel 2010 non ha trovato differenze dal placebo negli studi rigorosi. Saperlo non demolisce nulla: fa parte delle informazioni con cui si sceglie.

## Naturale non significa innocuo

È la frase da portare a casa. Erbe e integratori sono sostanze attive: possono interagire con i farmaci, accumularsi, fare male in gravidanza o con certe condizioni. Le due regole non negoziabili: il medico va informato di tutto quello che assumi, anche se «è naturale»; e nessuna terapia si tocca su consiglio di un naturopata. Un professionista serio queste due regole le dice lui per primo.

## Come riconoscere chi lavora bene

I segnali sono quelli di sempre, declinati sulla disciplina. Una formazione lunga e dichiarata, con scuola e ore verificabili. L'iscrizione a un'[associazione professionale della legge 4/2013](/blog/legge-4-2013-professioni-olistiche), con la dicitura di legge nei documenti. La trasparenza sui limiti: chi ti dice cosa non può fare per te è più affidabile di chi promette tutto. La collaborazione con la medicina invece della contrapposizione: il naturopata che parla male dei medici sta dicendo qualcosa di sé, non della medicina. Il metodo completo, con le domande da fare e le bandiere rosse, è nella [guida per capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

## Domande frequenti

**Il naturopata è un medico?**
No. In Italia la naturopatia è una professione non organizzata (legge 4/2013): il naturopata non fa diagnosi, non prescrive farmaci e non cura malattie. Chi supera questi confini sta violando la legge, oltre che la tua fiducia.

**Cosa si fa in un consulto di naturopatia?**
Soprattutto un colloquio lungo su abitudini, sonno, alimentazione, digestione e stress, seguito da proposte su stile di vita e rimedi naturali. Le eventuali analisi non convenzionali proposte non hanno validità diagnostica.

**La naturopatia funziona?**
Dipende da cosa si intende. Le componenti di buon senso (mangiare meglio, dormire, gestire lo stress) fanno bene, ma non sono esclusive della naturopatia. Il sistema nel suo insieme ha poche prove di qualità, e i singoli rimedi vanno giudicati uno per uno: per i fiori di Bach, ad esempio, gli studi rigorosi non mostrano differenze dal placebo.

**Posso sostituire una cura medica con la naturopatia?**
No, mai. Nessuna terapia si modifica o sospende su consiglio di un naturopata, e il medico va sempre informato di erbe e integratori che assumi. Un naturopata serio è il primo a dirtelo."""

RELATED = ["ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
           "come-capire-se-un-operatore-olistico-e-serio",
           "legge-4-2013-professioni-olistiche"]

# backlink dalle ancore naturali
AGGIUNTE = [
    # la guida all'operatore serio nomina il naturopata: da li' si
    # approfondisce
    ("come-capire-se-un-operatore-olistico-e-serio",
     "**Naturopata** non è un titolo riconosciuto dallo Stato italiano:",
     "**Naturopata** non è un titolo riconosciuto dallo Stato italiano "
     "(cosa significhi in pratica è spiegato nella [guida alla "
     "naturopatia](/blog/naturopatia-cose-consulto-cosa-dice-ricerca)):"),
    # la mappa delle discipline accoglie la stanza nuova, accanto
    # all'ayurveda
    ("discipline-olistiche-la-mappa",
     "La [guida all'ayurveda](/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi) "
     "parte dai tre dosha e arriva fino a cosa dice la ricerca.",
     "La [guida all'ayurveda](/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi) "
     "parte dai tre dosha e arriva fino a cosa dice la ricerca.\n\n"
     "**La naturopatia** è l'approccio occidentale al riequilibrio "
     "attraverso alimentazione, stile di vita e rimedi naturali: [cosa "
     "fa un naturopata, cosa no e cosa dice la ricerca]"
     "(/blog/naturopatia-cose-consulto-cosa-dice-ricerca)."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    contenuto = CONTENUTO
    assert len(TITOLO) <= 60 and 0 < len(DESCRIZIONE) <= 158
    print(f"{TITOLO}\n  slug: {SLUG}  parole: {len(contenuto.split())}  "
          f"T:{len(TITOLO)} D:{len(DESCRIZIONE)}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    campi = {"title": TITOLO, "description": DESCRIZIONE,
             "content": contenuto, "category": CATEGORIA,
             "author_name": "Aurya", "published": True,
             "updated_at": now, "translations": {},
             "related_slugs": RELATED}
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
            print(f"  backlink aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]}")

    # audit
    import re
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1}).to_list(100)
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\nlink rotti: {rotti or 'nessuno'}")
    from routers.seo_shell import _extract_faq
    n = len(_extract_faq(contenuto))
    print(f"FAQ estratte: {n}")
    assert n >= 4
    inbound = {a["slug"]: 0 for a in arts}
    for a in arts:
        for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]):
            if l in inbound and l != a["slug"]:
                inbound[l] += 1
    orfani = [s for s, cnt in inbound.items() if cnt == 0]
    print(f"orfani: {orfani or 'nessuno'}")
    print(f"articoli totali: {len(arts)}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
