"""PC6 — quinto pezzo del cluster yoga: il kriya yoga.

PERCHE'. Chiude l'omonimia che la guida agli stili aveva aperto: nel
kundalini "kriya" indica le sequenze di una lezione, nel kriya yoga di
Yogananda indica un percorso di meditazione che si riceve per
iniziazione e a cui non ci si iscrive come a un corso. Chi cerca
"kriya yoga" in italiano trova pagine che mescolano le due cose.

ATTENZIONE ALLA MATERIA. Qui NON si danno istruzioni operative, ed e'
una scelta: le tecniche di questa tradizione sono trasmesse sotto
vincolo di riservatezza e chiunque le pubblichi sta gia' dicendo
qualcosa di se'. Il pezzo spiega cos'e', da dove viene, come funziona
il percorso e cosa aspettarsi, senza fingere di insegnare quello che
non si insegna per iscritto. E' anche il modo di essere utili a chi
cerca: la domanda vera e' "come ci si avvicina", non "come si fa".

    venv/bin/python scripts/pc6_articolo_kriya_yoga.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "kriya-yoga-cose-come-funziona"
TITOLO = "Kriya yoga: cos'è, da dove viene e in cosa si distingue"
DESCRIZIONE = (
    "Un percorso di meditazione, non un corso di posizioni: origini, come "
    "funziona l'iniziazione, le scuole in Italia e l'omonimia da sciogliere."
)
CATEGORIA = "yoga"

CONTENUTO = """\
Chi cerca «kriya yoga» trova due cose diverse chiamate allo stesso modo, e le pagine in italiano tendono a mescolarle.

La prima è quella che si incontra in una lezione di kundalini: lì *kriya* indica una sequenza precisa di movimenti, respiro e mantra, e ce ne sono decine. La seconda è il **kriya yoga** come percorso, una tradizione di meditazione che non si insegna in una lezione e a cui non ci si iscrive come a un corso.

Questa guida parla della seconda. Se cercavi la prima, la trovi nella guida alle [differenze fra i tipi di yoga](/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini).

## Cosa significa la parola

*Kriya* viene da una radice che indica l'azione, il fare. Nel contesto di questa tradizione indica un'azione interiore: una tecnica che agisce sull'energia e sull'attenzione, non sul corpo visibile.

Il kriya yoga è quindi una via di pratica, non uno stile di lezione. Il suo campo è la meditazione, e le posizioni — se ci sono — servono solo a poter stare seduti a lungo.

## Da dove viene

La linea che ha reso il nome noto in Occidente passa da quattro figure.

**Mahavatar Babaji**, la figura fondativa, che nella tradizione avrebbe trasmesso la tecnica nell'Ottocento. È una figura di cui non esiste documentazione storica: appartiene al racconto della tradizione, e conviene saperlo.

**Lahiri Mahasaya**, che riceve la trasmissione e comincia a insegnarla anche a persone comuni, cioè fuori dai monasteri. È il passaggio che rende questa via accessibile a chi ha una famiglia e un lavoro, ed è una delle ragioni della sua diffusione.

**Sri Yukteswar**, suo discepolo e maestro del successivo.

**Paramahansa Yogananda**, che porta la pratica negli Stati Uniti a partire dal 1920 e nel 1946 pubblica *Autobiografia di uno yogi*, il libro che ha fatto conoscere lo yoga a milioni di persone in Occidente. È da lì che quasi tutti arrivano a questo nome.

## Come funziona il percorso

Qui sta la differenza più concreta con qualsiasi altra pratica raccontata in questo Magazine: **le tecniche non si trovano scritte, e chi le pubblica sta violando l'impegno che ha preso ricevendole**.

Il percorso ha una forma ricorrente nelle scuole che lo trasmettono.

**Un periodo di preparazione.** Prima dell'iniziazione si studiano materiali introduttivi e si praticano tecniche preliminari di concentrazione e respiro, spesso per mesi. Serve a costruire l'abitudine quotidiana prima di ricevere il resto.

**L'iniziazione.** La trasmissione vera e propria delle tecniche, che avviene in un incontro dedicato, in presenza o in alcune scuole a distanza. Da quel momento chi la riceve si impegna a praticare e a non divulgare.

**La pratica quotidiana.** È la sostanza di tutto: una sessione al giorno, spesso al mattino, per anni. Chi conosce questa via dice che il percorso è la pratica, non l'iniziazione.

Non aspettarti quindi una lezione settimanale in una sala. Questa tradizione somiglia più a uno studio lungo che a un corso.

## Cosa aspettarsi, e cosa no

**Non è una pratica fisica.** Chi cerca movimento resterà deluso: si sta seduti, e il lavoro è interiore.

**Richiede costanza, non intensità.** Il criterio è praticare ogni giorno, non praticare a lungo ogni tanto.

**Ha una cornice spirituale esplicita.** A differenza di una lezione di hatha, qui il contesto è dichiaratamente devozionale, con una linea di maestri e un rapporto con chi trasmette. Chi cerca solo una tecnica di rilassamento troverà più cose di quelle che cercava.

**Le scuole sono più di una.** In Italia sono presenti organizzazioni diverse, alcune legate direttamente alla linea di Yogananda, altre nate da altre ramificazioni. Chiedono impegni diversi e hanno stili diversi.

## Cosa dice la ricerca

Poco, e per una ragione strutturale: una tecnica non pubblicata non si può standardizzare in un protocollo sperimentale, e senza protocollo non ci sono studi confrontabili.

Quello che esiste riguarda la **meditazione in generale** — riduzione dello stress percepito, effetti su attenzione e regolazione emotiva — e non si può attribuire a questa tecnica invece che a un'altra. Chi presenta il kriya yoga come «scientificamente provato» sta usando prove che riguardano altro.

Il che non toglie nulla a chi lo pratica: significa solo che le ragioni per farlo stanno altrove.

## Come avvicinarsi

**Comincia dal libro.** *Autobiografia di uno yogi* è il modo in cui quasi tutti incontrano questa via, e dopo averlo letto molte persone capiscono se le riguarda.

**Verifica la scuola.** Da quanto esiste, chi la rappresenta in Italia, cosa chiede in termini di tempo e di denaro. Un percorso serio è chiaro su tutti e tre i punti prima che tu decida.

**Diffida delle scorciatoie.** Chi promette l'iniziazione in un fine settimana, o vende le tecniche in un corso online senza preparazione, sta proponendo qualcosa che la tradizione stessa non prevede.

**Guarda i costi.** Alcune organizzazioni chiedono una quota per i materiali e l'iniziazione, altre lavorano su offerta libera. Entrambe le forme sono legittime; quello che conta è che il costo sia dichiarato prima.

Valgono anche qui i criteri generali di [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio), con un'attenzione in più: dove c'è una linea di maestri e un rapporto di devozione, la chiarezza su tempo e denaro conta il doppio.

## Domande frequenti

**Kriya yoga e kundalini yoga sono la stessa cosa?**
No, e l'omonimia è la fonte principale di confusione. Nel kundalini *kriya* indica una sequenza di una lezione; il kriya yoga è un percorso di meditazione trasmesso per iniziazione.

**Posso impararlo da un libro o da un video?**
Le tecniche complete no: non vengono pubblicate, e chi le diffonde sta rompendo l'impegno che ha preso. Le pratiche preliminari di concentrazione e respiro invece sono disponibili.

**Serve essere induisti o credenti?**
No, e le scuole lo dichiarano. La cornice è però esplicitamente spirituale, e conviene saperlo prima di cominciare invece di scoprirlo dopo.

**Quanto tempo richiede al giorno?**
Le indicazioni variano fra i venti minuti e l'ora, una o due volte al giorno. La costanza conta più della durata.

**Quanto costa?**
Dipende dall'organizzazione: alcune chiedono una quota per materiali e iniziazione, altre lavorano su offerta libera. Chiedi la cifra completa prima di impegnarti.

**È adatto a chi comincia da zero con lo yoga?**
Può esserlo, perché non richiede preparazione fisica. Ma è un impegno quotidiano di lungo periodo: chi cerca un primo assaggio dello yoga trova strade più leggere, per esempio [lo yoga nidra](/blog/yoga-nidra-cose-come-funziona-una-sessione) o una pratica di meditazione.
"""


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
        "related_slugs": [
            "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
            "yoga-nidra-cose-come-funziona-una-sessione",
            "meditazione-per-chi-inizia-guida-semplice",
        ],
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

    # la guida agli stili aveva aperto l'omonimia: ora la chiude
    aggiunte = [
        ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
         "Il kriya yoga diffuso da Paramahansa Yogananda è un percorso di "
         "**tecniche di meditazione e respiro** trasmesse per iniziazione, "
         "non un corso di asana in cui ci si iscrive.",
         f"Il kriya yoga diffuso da Paramahansa Yogananda è un percorso di "
         f"**tecniche di meditazione e respiro** trasmesse per iniziazione, "
         f"non un corso di asana in cui ci si iscrive: [qui lo abbiamo "
         f"raccontato per intero](/blog/{SLUG})."),
    ]
    for slug, vecchio, nuovo in aggiunte:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
            continue
        if nuovo in d["content"]:
            print(f"  link gia' presente in {slug[:40]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  link aggiunto in {slug[:40]}")
        else:
            print(f"  NON TROVATO in {slug[:40]} — controllare a mano")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
