"""PE7 — il sistema di collegamenti interni del Magazine.

TRE COSE, IN QUEST'ORDINE.

1. RIPARA GLI OTTO LINK ROTTI. Cancellando i cinque articoli sui
   ritiri (PE2) sono rimasti otto collegamenti in entrata che ora
   portano a pagine inesistenti, sparsi in sette pezzi. Nessuno aveva
   controllato i link in ingresso prima di cancellare: e' il tipo di
   danno che non si vede finche' non lo cerchi, e che i motori vedono
   subito. Dove la frase aveva senso solo per i ritiri, la frase
   sparisce; dove il senso resta, il link cambia destinazione.

2. COLLEGA I TRE ARTICOLI NUOVI. Nascevano senza un solo link in
   entrata o in uscita, quindi per un motore erano isole. I link in
   mezzo al testo, con un'ancora che dice dove porta, pesano molto
   piu' delle schede in fondo alla pagina.

3. CURA IL GRAFO. Ogni articolo dichiara i suoi correlati veri
   (`related_slugs`), invece di lasciare che la pagina scelga per
   categoria e data. Il frontend usa questa lista se c'e' e ripiega
   sull'automatismo se manca: nessun articolo resta senza correlati.

Idempotente: le riparazioni sono sostituzioni esatte che spariscono
dopo la prima applicazione, le aggiunte controllano se il link c'e'
gia'. Rilanciarlo non fa danni.

    venv/bin/python scripts/pe7_link_interni.py [--dry-run]
"""
import asyncio
import os
import re
import sys

# ── 1. Le riparazioni: (slug, testo esatto da trovare, sostituto) ──
# Dove la frase parlava solo di ritiri sparisce; dove il senso regge,
# il link va su "come capire se un operatore e' serio", che e' il pezzo
# che ha ereditato il ruolo di guida alla scelta.
RIPARAZIONI = [
    # la frase esisteva solo per mandare al ritiro: via tutta
    ("cerchi-di-donne-cosa-sono-come-funzionano",
     " E se vuoi capire come un'esperienza più lunga può approfondire il "
     "lavoro del cerchio, leggi la nostra guida su [come scegliere un ritiro "
     "olistico](/blog/ritiri-olistici-in-italia-come-scegliere).",
     ""),
    # "il quadro delle discipline" non esiste piu': diventa "come si
    # sceglie la persona", che e' la domanda vera di chi legge un pezzo
    # su un consulto
    ("lettura-tema-natale-cosa-aspettarsi",
     "Se invece vuoi capire il quadro delle discipline, parti da [cosa sono i "
     "ritiri olistici](/blog/ritiri-olistici-in-italia-come-scegliere).",
     "Se invece la domanda è più larga, parti da [come capire se un operatore "
     "è serio](/blog/come-capire-se-un-operatore-olistico-e-serio)."),
    ("meditazione-per-chi-inizia-guida-semplice",
     " E per capire come orientarti tra le esperienze, leggi [come scegliere "
     "un ritiro olistico](/blog/ritiri-olistici-in-italia-come-scegliere) e "
     "[quanto costa davvero](/blog/quanto-costa-un-ritiro-yoga-in-italia).",
     " E per capire come scegliere chi ti accompagna, leggi [come capire se un "
     "operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio)."),
    ("costellazioni-familiari-cosa-sono-come-funzionano",
     "Per il quadro generale, parti da [cosa sono i ritiri olistici]"
     "(/blog/ritiri-olistici-in-italia-come-scegliere).",
     "Per capire come si valuta chi conduce, parti da [come capire se un "
     "operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio)."),
    # la mappatura dei prezzi non esiste piu': via la parentesi, resta
    # il consiglio, che regge da solo
    ("prezzo-giusto-ritiro-come-calcolarlo",
     "guarda ORA il mercato (i [prezzi reali dei ritiri in Italia]"
     "(/blog/quanto-costa-un-ritiro-yoga-in-italia) li abbiamo mappati): non "
     "per copiare",
     "guarda ORA il mercato: non per copiare"),
    # "le regole di sempre" e' esattamente il pezzo nuovo
    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "Valgono le [regole di sempre](/blog/ritiri-olistici-in-italia-come-scegliere):",
     "Valgono le [regole di sempre](/blog/come-capire-se-un-operatore-olistico-e-serio):"),
    # qui serviva solo la parola, non il link
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "(un weekend, [un ritiro](/blog/ritiri-olistici-in-italia-come-scegliere))",
     "(un weekend, un ritiro)"),
]

# ── 2. I link nuovi: (slug, testo esatto, testo con il link) ──
AGGIUNTE = [
    # il pezzo sui tipi di yoga tira dentro le pratiche vicine
    ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
     "- **Yoga nidra** — non è una lezione di posizioni: si sta sdraiati e si "
     "segue la voce dell'insegnante attraverso il corpo, in uno stato fra "
     "veglia e sonno. Serve a riposare, non ad allenarsi.",
     "- **Yoga nidra** — non è una lezione di posizioni: si sta sdraiati e si "
     "segue la voce dell'insegnante attraverso il corpo, in uno stato fra "
     "veglia e sonno. Serve a riposare, non ad allenarsi. Se cerchi qualcosa "
     "che si avvicini, guarda anche [la meditazione per chi inizia]"
     "(/blog/meditazione-per-chi-inizia-guida-semplice)."),
    ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
     "Un buon insegnante ti chiede come stai prima di cominciare",
     "Su come si riconosce, abbiamo scritto una guida a parte: [come capire "
     "se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio). "
     "Un buon insegnante ti chiede come stai prima di cominciare"),
    # il rebirthing dentro la sua famiglia
    ("rebirthing-cose-come-funziona-una-sessione",
     "Nella famiglia del breathwork è una delle tecniche a respirazione "
     "intensa",
     "Nella famiglia del [breathwork](/blog/breathwork-cose-tecniche-benefici) "
     "è una delle tecniche a respirazione intensa"),
    ("rebirthing-cose-come-funziona-una-sessione",
     "In Italia il rebirthing non è una professione regolamentata: chiunque "
     "può proporsi.",
     "In Italia il rebirthing non è una professione regolamentata: chiunque "
     "può proporsi. Le regole generali per orientarsi stanno in [come capire "
     "se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio)."),
    # il pezzo sulla scelta manda alle pratiche, cosi' il traffico
    # informativo scende nel cluster invece di uscire
    ("come-capire-se-un-operatore-olistico-e-serio",
     "Alcune tecniche si trasmettono in tempi brevi, ed è legittimo.",
     "Alcune tecniche si trasmettono in tempi brevi, ed è legittimo — vale per "
     "esempio per certe pratiche di [respirazione]"
     "(/blog/breathwork-cose-tecniche-benefici)."),
    ("come-capire-se-un-operatore-olistico-e-serio",
     "Cerchi «reiki» o «costellazioni familiari» nella tua città",
     "Cerchi [«reiki»](/blog/reiki-cose-come-funziona-una-sessione) o "
     "[«costellazioni familiari»](/blog/costellazioni-familiari-cosa-sono-come-funzionano) "
     "nella tua città"),
    # e i pezzi esistenti tirano dentro i nuovi
    ("breathwork-cose-tecniche-benefici",
     "## Domande frequenti",
     "Fra le tecniche a respirazione intensa di questa famiglia c'è anche il "
     "[rebirthing](/blog/rebirthing-cose-come-funziona-una-sessione), che ha "
     "una storia e delle cautele proprie.\n\n## Domande frequenti"),
    ("meditazione-per-chi-inizia-guida-semplice",
     "## Domande frequenti",
     "Se stai valutando anche una pratica sul tappetino, [le differenze fra i "
     "tipi di yoga]"
     "(/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini) "
     "spiegano cosa cambia da una lezione all'altra.\n\n## Domande frequenti"),
    ("reiki-cose-come-funziona-una-sessione",
     "## Domande frequenti",
     "Per le domande da fare prima di prenotare, la guida su [come capire se "
     "un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio) "
     "vale per il Reiki come per il resto.\n\n## Domande frequenti"),
]

# ── 3. Il grafo curato: slug → correlati, in ordine di pertinenza ──
GRAFO = {
    "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini": [
        "meditazione-per-chi-inizia-guida-semplice",
        "breathwork-cose-tecniche-benefici",
        "come-capire-se-un-operatore-olistico-e-serio"],
    "rebirthing-cose-come-funziona-una-sessione": [
        "breathwork-cose-tecniche-benefici",
        "come-capire-se-un-operatore-olistico-e-serio",
        "pratiche-olistiche-contro-stress-cosa-funziona"],
    "come-capire-se-un-operatore-olistico-e-serio": [
        "reiki-cose-come-funziona-una-sessione",
        "costellazioni-familiari-cosa-sono-come-funzionano",
        "rebirthing-cose-come-funziona-una-sessione"],
    "breathwork-cose-tecniche-benefici": [
        "rebirthing-cose-come-funziona-una-sessione",
        "pratiche-olistiche-contro-stress-cosa-funziona",
        "meditazione-per-chi-inizia-guida-semplice"],
    "meditazione-per-chi-inizia-guida-semplice": [
        "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
        "kit-pratiche-quotidiane-15-minuti",
        "pratiche-olistiche-contro-stress-cosa-funziona"],
    "pratiche-olistiche-contro-stress-cosa-funziona": [
        "breathwork-cose-tecniche-benefici",
        "meditazione-per-chi-inizia-guida-semplice",
        "kit-pratiche-quotidiane-15-minuti"],
    "kit-pratiche-quotidiane-15-minuti": [
        "meditazione-per-chi-inizia-guida-semplice",
        "breathwork-cose-tecniche-benefici",
        "pratiche-olistiche-contro-stress-cosa-funziona"],
    "reiki-cose-come-funziona-una-sessione": [
        "come-capire-se-un-operatore-olistico-e-serio",
        "campane-tibetane-benefici-come-funzionano",
        "costellazioni-familiari-cosa-sono-come-funzionano"],
    "costellazioni-familiari-cosa-sono-come-funzionano": [
        "come-capire-se-un-operatore-olistico-e-serio",
        "cerchi-di-donne-cosa-sono-come-funzionano",
        "lettura-tema-natale-cosa-aspettarsi"],
    "lettura-tema-natale-cosa-aspettarsi": [
        "tarocchi-oracoli-strumento-evolutivo",
        "come-capire-se-un-operatore-olistico-e-serio",
        "costellazioni-familiari-cosa-sono-come-funzionano"],
    "tarocchi-oracoli-strumento-evolutivo": [
        "lettura-tema-natale-cosa-aspettarsi",
        "come-capire-se-un-operatore-olistico-e-serio",
        "cerchi-di-donne-cosa-sono-come-funzionano"],
    "cerchi-di-donne-cosa-sono-come-funzionano": [
        "come-capire-se-un-operatore-olistico-e-serio",
        "costellazioni-familiari-cosa-sono-come-funzionano",
        "meditazione-per-chi-inizia-guida-semplice"],
    "campane-tibetane-benefici-come-funzionano": [
        "bagno-di-gong-sound-healing-benefici",
        "meditazione-per-chi-inizia-guida-semplice",
        "come-capire-se-un-operatore-olistico-e-serio"],
    "bagno-di-gong-sound-healing-benefici": [
        "campane-tibetane-benefici-come-funzionano",
        "pratiche-olistiche-contro-stress-cosa-funziona",
        "come-capire-se-un-operatore-olistico-e-serio"],
    "digiuno-consapevole-detox-benefici-falsi-miti": [
        "come-capire-se-un-operatore-olistico-e-serio",
        "pratiche-olistiche-contro-stress-cosa-funziona",
        "kit-pratiche-quotidiane-15-minuti"],
    # i tre professionali restano fra loro: il pubblico e' un altro
    "partita-iva-operatore-olistico-fiscalita-guida": [
        "prezzo-giusto-ritiro-come-calcolarlo",
        "come-promuovere-un-ritiro-e-riempire-i-posti"],
    "prezzo-giusto-ritiro-come-calcolarlo": [
        "come-promuovere-un-ritiro-e-riempire-i-posti",
        "partita-iva-operatore-olistico-fiscalita-guida"],
    "come-promuovere-un-ritiro-e-riempire-i-posti": [
        "prezzo-giusto-ritiro-come-calcolarlo",
        "partita-iva-operatore-olistico-fiscalita-guida"],
}


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    testi = {}          # slug → contenuto in lavorazione

    async def contenuto(slug):
        if slug not in testi:
            doc = await db.articles.find_one({"slug": slug},
                                             {"_id": 0, "content": 1})
            testi[slug] = doc["content"] if doc else None
        return testi[slug]

    print("── 1. riparazioni dei link rotti")
    for slug, vecchio, nuovo in RIPARAZIONI:
        c = await contenuto(slug)
        if c is None:
            print(f"  ASSENTE {slug}")
            continue
        if vecchio in c:
            testi[slug] = c.replace(vecchio, nuovo, 1)
            print(f"  riparato  {slug[:44]}")
        elif nuovo and nuovo in c:
            print(f"  gia' ok   {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:40]} — controllare a mano")

    print("\n── 2. link nuovi in mezzo al testo")
    for slug, vecchio, nuovo in AGGIUNTE:
        c = await contenuto(slug)
        if c is None:
            print(f"  ASSENTE {slug}")
            continue
        if nuovo in c:
            print(f"  gia' ok   {slug[:44]}")
        elif vecchio in c:
            testi[slug] = c.replace(vecchio, nuovo, 1)
            print(f"  aggiunto  {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:40]} — controllare a mano")

    if not dry_run:
        for slug, c in testi.items():
            if c is not None:
                await db.articles.update_one({"slug": slug},
                                             {"$set": {"content": c}})

    print("\n── 3. grafo dei correlati")
    vivi = {a["slug"] async for a in db.articles.find({}, {"_id": 0, "slug": 1})}
    for slug, correlati in GRAFO.items():
        if slug not in vivi:
            print(f"  ASSENTE {slug}")
            continue
        puliti = [s for s in correlati if s in vivi]
        if len(puliti) != len(correlati):
            print(f"  {slug[:40]}: scartati {set(correlati) - set(puliti)}")
        if not dry_run:
            await db.articles.update_one({"slug": slug},
                                         {"$set": {"related_slugs": puliti}})
    print(f"  {len(GRAFO)} articoli con correlati dichiarati")

    # verifica finale: nessun link punta piu' nel vuoto
    print("\n── verifica: link interni che puntano nel vuoto")
    rotti = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1}):
        for dest in re.findall(r"\]\(/blog/([^)#]+)\)", a["content"]):
            if dest not in vivi:
                print(f"  ROTTO {a['slug'][:36]} → {dest}")
                rotti += 1
    print("  nessuno" if not rotti else f"  {rotti} da sistemare")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
