"""PC5 — quarto pezzo del cluster yoga: lo yoga nidra.

PERCHE' ORA. E' la pratica piu' fraintesa del gruppo: chi la cerca la
confonde con una meditazione guidata o con una tecnica per dormire, e
in italiano quasi nessuno spiega la differenza. E' anche l'unica dello
yoga che si fa da sdraiati e senza sforzo, quindi e' la porta piu'
larga per chi pensa di non poter praticare.

Lega tre cluster che oggi si toccano appena: yoga (dove sta), la
meditazione (con cui viene confusa) e il breathwork (perche' il respiro
e' uno dei suoi passaggi).

    venv/bin/python scripts/pc5_articolo_yoga_nidra.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "yoga-nidra-cose-come-funziona-una-sessione"
TITOLO = "Yoga nidra: cos'è, come funziona una sessione e a cosa serve"
DESCRIZIONE = (
    "Il sonno consapevole dello yoga: come si svolge una pratica, in cosa "
    "differisce dalla meditazione, cosa dice la ricerca e come cominciare."
)
CATEGORIA = "yoga"

CONTENUTO = """\
Di tutte le pratiche dello yoga, questa è quella che chi la sente nominare capisce meno. Il nome promette sonno, la descrizione parla di consapevolezza, e le due cose sembrano escludersi.

Non si escludono, e la traduzione più utile è proprio quella letterale: *nidra* è il sonno, e lo yoga nidra è la pratica di restare presenti mentre il corpo si addormenta.

## Cosa succede, in concreto

Ci si sdraia sulla schiena, coperti, con un cuscino sotto le ginocchia. Da lì in poi non si fa più niente con il corpo: si segue la voce di chi conduce, che porta l'attenzione in una sequenza precisa attraverso zone del corpo, sensazioni, respiro e immagini.

Una pratica dura fra i venti e i quarantacinque minuti. Non ci si muove, non si assumono posizioni, e l'unico compito è ascoltare. È l'unica pratica dello yoga in cui addormentarsi non è un errore: molte persone lo fanno, soprattutto le prime volte.

## Le fasi di una pratica

Le scuole variano nei dettagli, ma la struttura ricorre.

**La preparazione.** Ci si sistema e si lascia che il corpo si posi. Chi conduce dà qualche indicazione per rendere la posizione sostenibile per mezz'ora.

**Il sankalpa.** Una frase breve, al presente e in positivo, che si ripete mentalmente tre volte. Nella tradizione è un'intenzione che si pianta in uno stato in cui la mente è più ricettiva. Alcune scuole la considerano il cuore della pratica, altre la propongono come facoltativa.

**La rotazione della coscienza.** Il passaggio centrale: la voce nomina una parte del corpo dopo l'altra, in una sequenza fissa, e l'attenzione si sposta senza fermarsi. Pollice destro, indice, medio, e via così per tutto il corpo. È rapido, e la rapidità è voluta: non c'è tempo per commentare.

**Il respiro.** Si osserva il respiro senza modificarlo, spesso contando all'indietro. È il momento in cui il rallentamento diventa evidente.

**Gli opposti.** Si evocano coppie di sensazioni — pesantezza e leggerezza, caldo e freddo — una dopo l'altra. Serve a portare il corpo a uno stato che nessuna delle due domina.

**Le immagini.** Una serie rapida di immagini nominate dalla voce, senza collegamento logico fra loro. È la parte che somiglia di più al sogno da svegli.

**Il ritorno.** Si torna al respiro, alla stanza, al corpo, con calma. Chi conduce lascia il tempo che serve.

## In cosa differisce da una meditazione

È la domanda più frequente, e la differenza è netta su tre punti.

**La posizione.** Nella [meditazione](/blog/meditazione-per-chi-inizia-guida-semplice) si sta seduti, e la seduta serve a restare svegli. Nello yoga nidra si sta sdraiati, e il sonno è ammesso.

**Lo sforzo.** Meditare significa riportare l'attenzione ogni volta che se ne va: c'è un lavoro. Nello yoga nidra il lavoro lo fa la voce, e chi pratica si limita a seguire.

**Lo stato.** La meditazione allena la capacità di stare con quello che c'è. Lo yoga nidra porta in uno stato di confine fra veglia e sonno, che nella tradizione ha un nome proprio e che oggi si descriverebbe come uno stato ipnagogico.

La conseguenza pratica è che sono due pratiche complementari, e che lo yoga nidra è quasi sempre più facile da cui cominciare.

## Cosa dice la ricerca

La letteratura è cresciuta negli ultimi anni ed è più solida di quella su molte pratiche vicine, con un limite da conoscere.

Gli studi riportano in modo abbastanza consistente **riduzione dell'ansia percepita, miglioramenti sulla qualità del sonno e sullo stress**, con effetti misurati anche su parametri fisiologici come frequenza cardiaca e cortisolo in alcune ricerche. Esistono lavori su popolazioni specifiche, dal personale sanitario agli studenti in periodi d'esame.

Il limite è quello di tutto il campo: campioni piccoli, protocolli che variano da uno studio all'altro, e difficoltà a distinguere l'effetto della tecnica da quello di sdraiarsi mezz'ora in silenzio con qualcuno che parla piano. Che, di nuovo, resta un intervento con effetti propri.

Su una cosa spesso ripetuta conviene essere precisi: la frase «un'ora di yoga nidra vale quattro ore di sonno» circola molto e **non ha basi**. È una pratica che riposa, non un sostituto del dormire.

## A chi è adatta, e le poche cautele

È fra le pratiche più accessibili che esistono: si fa da sdraiati, non richiede mobilità né esperienza, ed è praticabile da chi ha limitazioni fisiche che escludono le posizioni.

Due accortezze meritano di essere dette. Chi attraversa un **disturbo post-traumatico** può trovare difficile la parte di attenzione al corpo, e in quel caso conviene farlo accompagnato da chi ha una formazione specifica sul trauma. E chi ha una **storia di dissociazione** dovrebbe parlarne con chi lo ha in cura prima di cominciare.

Per il resto, addormentarsi non è un problema. Nella tradizione si dice che una parte dell'ascolto continua comunque, e in pratica chi si addormenta si sveglia riposato: nessuna delle due cose è un fallimento.

## Come cominciare

**Da una registrazione va benissimo.** È una delle poche pratiche in cui la voce registrata funziona quanto quella dal vivo, perché il compito è seguire e non essere corretti. Comincia con una pratica di venti minuti.

**L'orario conta.** Nel primo pomeriggio o prima di dormire sono i momenti in cui è più facile lasciarsi andare. Al mattino presto è più difficile restare in quel confine.

**Copriti.** La temperatura del corpo scende quando si sta fermi a lungo, e il freddo è la ragione più comune per cui una pratica non funziona.

**In presenza cambia poco, ma non è inutile.** Una sessione dal vivo aggiunge il contesto e la possibilità di fare domande. Sulla scelta di chi conduce valgono i criteri di [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

## Domande frequenti

**Se mi addormento, la pratica funziona lo stesso?**
Sì. Nella tradizione una parte dell'ascolto continua, e in ogni caso il riposo c'è. Con la pratica capita di restare in quel confine più a lungo.

**Quanto dura una sessione?**
Fra i venti e i quarantacinque minuti. Venti minuti è la durata più comune per cominciare.

**È la stessa cosa della meditazione guidata?**
No. Una meditazione guidata di solito si fa seduti e chiede di mantenere l'attenzione; lo yoga nidra si fa sdraiati, ammette il sonno e segue una sequenza codificata di fasi.

**Serve conoscere lo yoga per praticarlo?**
No. È la pratica dello yoga che richiede meno prerequisiti di tutte, e molte persone la incontrano senza aver mai fatto una posizione.

**Ogni quanto conviene praticarlo?**
Due o tre volte a settimana è la frequenza in cui la maggior parte delle persone nota un cambiamento sul sonno. Quotidianamente va bene e non ha controindicazioni.

**Il sankalpa è obbligatorio?**
No. Alcune scuole lo considerano centrale, altre lo propongono come facoltativo. Si può praticare senza, e la parte sul corpo e sul respiro resta la stessa.
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
            "meditazione-per-chi-inizia-guida-semplice",
            "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
            "pranayama-tecniche-respirazione-yoga",
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

    # i link in entrata: la guida agli stili lo nominava senza spiegarlo,
    # e la meditazione e' la pratica con cui viene confuso piu' spesso.
    aggiunte = [
        ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
         "Serve a riposare, non ad allenarsi. Se cerchi qualcosa "
         "che si avvicini, guarda anche [la meditazione per chi inizia]"
         "(/blog/meditazione-per-chi-inizia-guida-semplice).",
         f"Serve a riposare, non ad allenarsi: come funziona una pratica "
         f"lo abbiamo raccontato [qui](/blog/{SLUG})."),
        ("meditazione-per-chi-inizia-guida-semplice",
         "Se stai valutando anche una pratica sul tappetino,",
         f"Se l'idea di stare seduti ti sembra il vero ostacolo, "
         f"[lo yoga nidra](/blog/{SLUG}) si pratica da sdraiati e ammette "
         f"perfino di addormentarsi. Se invece stai valutando una pratica "
         f"sul tappetino,"),
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
