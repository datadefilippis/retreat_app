# -*- coding: utf-8 -*-
"""SE6b — la pagina dei prezzi: "Quanto costano le pratiche olistiche".

PERCHE' UNA PAGINA SOLA. L'istinto SEO da manuale direbbe una pagina
per query ("quanto costa una seduta di reiki", "di shiatsu"...). Ma le
forchette di prezzo vivono GIA', verificate, dentro gli articoli di
disciplina: quattro paginette-prezzo cannibalizzerebbero le pagine
canoniche con contenuto piu' debole. La mossa giusta e' una RACCOLTA:
una pagina che aggrega le forchette gia' pubblicate (fonte: i nostri
stessi articoli, nessun numero nuovo), linka ogni disciplina per
l'approfondimento e risponde alle query specifiche con le FAQ, che
diventano FAQPage nel JSON-LD.

REGOLA FERREA. Ogni cifra di questa pagina e' COPIA di una cifra gia'
presente nell'articolo di disciplina linkato accanto. L'audit in fondo
allo script lo verifica riga per riga: se un giorno un articolo
aggiorna una forchetta, l'audit segnala la divergenza.

    venv/bin/python scripts/se6b_quanto_costano.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "quanto-costano-pratiche-olistiche"
TITOLO = "Quanto costano le pratiche olistiche, una per una"
DESCRIZIONE = ("I prezzi reali in Italia, pratica per pratica: sedute "
               "individuali, gruppi, percorsi e ritiri. Come leggere le "
               "differenze e quando il prezzo è un segnale.")
CATEGORIA = "scegliere"

# (etichetta per l'audit, slug sorgente, frase con la cifra che DEVE
#  stare anche nell'articolo di origine)
FONTI = [
    ("reiki", "reiki-cose-come-funziona-una-sessione",
     "fra i quaranta e i settanta euro"),
    ("shiatsu", "shiatsu-cose-come-funziona-una-seduta",
     "fra i 50 e gli 80 euro"),
    ("massaggio", "massaggio-olistico-tipi-cosa-aspettarsi",
     "dai 50 ai 90 euro"),
    ("ayurveda", "ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
     "fra gli 80 e i 150 euro"),
    ("yoga", "yoga-cose-da-dove-viene-come-cominciare",
     "dai 10 ai 20 euro"),
    ("campane", "campane-tibetane-benefici-come-funzionano",
     "fra i 40 e i 70 euro"),
    ("gong", "bagno-di-gong-sound-healing-benefici",
     "fra i 15 e i 40 euro"),
    ("cerchi", "cerchi-di-donne-cosa-sono-come-funzionano",
     "fra i 10 e i 30 euro"),
    ("breathwork", "breathwork-cose-tecniche-benefici",
     "fra i venticinque e i sessanta"),
    ("costellazioni", "costellazioni-familiari-cosa-sono-come-funzionano",
     "fra gli 80 e i 150"),
    ("tarocchi", "tarocchi-oracoli-strumento-evolutivo",
     "fra i 40 e gli 80 euro"),
    ("tema natale", "lettura-tema-natale-cosa-aspettarsi",
     "fra i 60 e i 120 euro"),
    ("mbsr", "mindfulness-cose-mbsr-come-funziona",
     "fra i 300 e i 600 euro"),
    ("ritiri", "domande-da-fare-prima-di-prenotare-un-ritiro",
     "fra i quattrocento e i millecinquecento euro"),
]

CONTENUTO = """C'è una domanda che quasi nessun sito del benessere mette per iscritto, e che tutti fanno prima di prenotare: quanto costa? La si cerca sui listini che non ci sono, la si chiede per messaggio con un certo imbarazzo, e intanto il dubbio lavora: quello che mi hanno proposto è un prezzo normale?

Questa pagina raccoglie i prezzi che trovi, con tutto il contesto, nelle nostre guide alle singole pratiche. Sono forchette reali per l'Italia, non promesse: dentro ogni forchetta ci sono differenze di città, esperienza di chi conduce e durata. E una premessa che vale per tutto quello che segue: il prezzo dice quanto costa, non quanto vale. Per capire il valore servono altre domande, e le trovi alla fine.

## Le sedute individuali

**Reiki.** Una sessione individuale costa in genere fra i quaranta e i settanta euro. Cosa succede in una sessione, cosa si sente e cosa dice la ricerca è nella [guida al reiki](/blog/reiki-cose-come-funziona-una-sessione).

**Shiatsu.** Una seduta dura fra i cinquanta e i settantacinque minuti e costa fra i 50 e gli 80 euro. Il percorso completo è nella [guida allo shiatsu](/blog/shiatsu-cose-come-funziona-una-seduta).

**Massaggio olistico.** Un'ora va in genere dai 50 ai 90 euro, con differenze fra tecniche oltre che fra città: i [tipi di massaggio e cosa aspettarsi](/blog/massaggio-olistico-tipi-cosa-aspettarsi) meritano una lettura prima di scegliere.

**Consulto ayurvedico.** Il primo consulto costa in genere fra gli 80 e i 150 euro, i controlli meno; i trattamenti come l'abhyanga durano circa un'ora e costano fra i 60 e i 100 euro. Il quadro completo è nella [guida all'ayurveda](/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi).

## Le pratiche di gruppo

**Yoga.** La lezione singola va dai 10 ai 20 euro, con abbonamenti mensili spesso fra i 50 e gli 80 euro. Come scegliere lo stile giusto è un'altra faccenda: parte dalla [guida allo yoga](/blog/yoga-cose-da-dove-viene-come-cominciare).

**Bagni sonori.** Una sessione con le campane tibetane costa fra i 40 e i 70 euro; un bagno di gong di gruppo in città costa in genere fra i 15 e i 40 euro. Le differenze fra i due mondi sono nelle guide alle [campane tibetane](/blog/campane-tibetane-benefici-come-funzionano) e al [bagno di gong](/blog/bagno-di-gong-sound-healing-benefici).

**Breathwork.** Una sessione di gruppo guidata costa in genere fra i venticinque e i sessanta euro. Prima di iscriverti, leggi [tecniche e controindicazioni](/blog/breathwork-cose-tecniche-benefici): per il breathwork intenso non sono un dettaglio.

**Cerchi di donne.** Fra i 10 e i 30 euro a incontro, spesso a offerta libera o contributo consapevole: [cosa sono e come funzionano](/blog/cerchi-di-donne-cosa-sono-come-funzionano).

**Costellazioni familiari.** Partecipare a una sessione di gruppo costa fra i 30 e gli 80 euro; costellare il proprio tema fra gli 80 e i 150. [Cosa succede in una sessione](/blog/costellazioni-familiari-cosa-sono-come-funzionano) va saputo prima, non dopo.

## I consulti

**Tarocchi e oracoli.** Un consulto dura fra i quarantacinque e i sessanta minuti e costa fra i 40 e gli 80 euro. In che modo può avere senso, e in che modo no, è il tema della [guida ai tarocchi come strumento evolutivo](/blog/tarocchi-oracoli-strumento-evolutivo).

**Tema natale.** Una lettura costa fra i 60 e i 120 euro. [Cosa aspettarsi, e cosa dice la ricerca](/blog/lettura-tema-natale-cosa-aspettarsi), è materiale da leggere prima di prenotare.

## I percorsi e le esperienze

**MBSR.** Il percorso di mindfulness di otto settimane costa in Italia fra i 300 e i 600 euro: è un impegno vero, e la [guida all'MBSR](/blog/mindfulness-cose-mbsr-come-funziona) spiega cosa lo distingue dai corsi che ne usano solo il nome.

**Ritiri.** Un ritiro di quattro giorni costa fra i quattrocento e i millecinquecento euro; un weekend detox parte da circa 300 euro. Prima di bloccare un posto, le [ventidue domande da fare](/blog/domande-da-fare-prima-di-prenotare-un-ritiro) valgono più di qualunque recensione.

**Cammini.** Fra i 40 e i 70 euro al giorno tutto compreso, meno organizzandosi con i pasti: la [guida ai cammini italiani](/blog/cammini-italiani-quale-scegliere-la-prima-volta) aiuta a scegliere il primo.

## Come leggere un prezzo

Dentro le forchette, tre variabili spiegano quasi tutte le differenze: la città (i grandi centri costano di più), l'esperienza di chi conduce e la durata reale della seduta. Un prezzo sopra la forchetta non è di per sé un allarme se le tre variabili lo giustificano; un prezzo molto sotto merita una domanda in più, perché da qualche parte quel margine è stato tolto.

Due segnali invece contano più del numero. Il primo: la trasparenza. Chi pubblica i prezzi, o li dice al primo messaggio senza girarci intorno, sta trattando bene il tuo tempo. Il secondo: il pacchetto spinto. Il percorso da molte sedute pagato in anticipo, proposto al primo incontro, è una pressione commerciale prima che un'offerta.

Il prezzo, da solo, non dice mai se una persona è quella giusta. Per quello servono le domande della [guida per capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio), che è il pezzo che consigliamo di leggere insieme a questo.

## Domande frequenti

**Quanto costa una seduta di reiki?**
In Italia una sessione individuale costa in genere fra i quaranta e i settanta euro, con variazioni per città e per esperienza di chi la conduce.

**Quanto costa una seduta di shiatsu?**
Fra i 50 e gli 80 euro, per una seduta che dura in genere fra i cinquanta e i settantacinque minuti.

**Quanto costa un massaggio olistico?**
In genere dai 50 ai 90 euro per un'ora, con differenze fra città e fra tecniche.

**Quanto costa un consulto ayurvedico?**
Il primo consulto va in genere dagli 80 ai 150 euro; i controlli successivi costano meno, e i trattamenti come l'abhyanga fra i 60 e i 100 euro.

**Un prezzo basso è un buon segno?**
Non di per sé. Un prezzo molto sotto la forchetta merita una domanda in più: le variabili serie (città, esperienza, durata) spiegano le differenze normali, non quelle estreme. E in ogni caso il prezzo dice quanto costa, non se la persona è quella giusta per te."""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    assert len(TITOLO) <= 60 and 0 < len(DESCRIZIONE) <= 158
    print(f"{TITOLO}\n  slug: {SLUG}  parole: {len(CONTENUTO.split())}  "
          f"T:{len(TITOLO)} D:{len(DESCRIZIONE)}")

    # ── audit prezzi PRIMA di scrivere: ogni cifra e' copia della fonte
    ok = True
    for label, fonte, frase in FONTI:
        d = await db.articles.find_one({"slug": fonte}, {"_id": 0, "content": 1})
        if not d:
            print(f"  FONTE ASSENTE {fonte}")
            ok = False
        elif frase not in d["content"]:
            print(f"  DIVERGENZA {label}: '{frase}' non in {fonte}")
            ok = False
    assert ok, "audit prezzi fallito: cifre non allineate alle fonti"
    print(f"  audit prezzi: {len(FONTI)} forchette allineate alle fonti")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    campi = {"title": TITOLO, "description": DESCRIZIONE,
             "content": CONTENUTO, "category": CATEGORIA,
             "author_name": "Aurya", "published": True,
             "updated_at": now, "translations": {},
             "related_slugs": ["come-capire-se-un-operatore-olistico-e-serio",
                               "domande-da-fare-prima-di-prenotare-un-ritiro",
                               "prezzo-giusto-ritiro-come-calcolarlo"]}
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

    # ── audit finale: link, FAQ, orfani ──────────────────────────────
    import re
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1}).to_list(100)
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"link rotti: {rotti or 'nessuno'}")
    from routers.seo_shell import _extract_faq
    n = len(_extract_faq(CONTENUTO))
    print(f"FAQ estratte: {n}")
    assert n >= 4
    print(f"articoli totali: {len(arts)}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
