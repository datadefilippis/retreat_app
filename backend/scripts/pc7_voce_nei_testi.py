"""PC7 — la revisione di voce arriva DENTRO i testi.

La passata di luglio (PE3) aveva ripulito titoli e descrizioni, cioe'
le due righe che si leggono nei risultati di ricerca. Il corpo degli
articoli era rimasto indietro: dodici pezzi su ventuno avevano ancora
i tic.

IL CRITERIO, che non e' meccanico. La regola scritta nel piano dice
che "davvero" sparisce QUASI sempre, e che una negazione resta se
corregge un malinteso. Applicata a mano, si divide cosi'.

VIA — quando siamo NOI a dichiarare la nostra onesta':
  "con la solita onesta'", "con l'onesta' che ci caratterizza",
  "la regola della casa: onesta' radicale", "Due onesta' doverose",
  "Ne abbiamo scritto con onesta'", "senza misteri e senza
  idealizzazioni", "senza promesse impossibili".
E' la stessa cosa dei titoli: chi deve dichiararsi onesto insinua il
dubbio, e per giunta lo insinua su di se'.

RESTA — quando "onesto" descrive una qualita' da valutare in ALTRI:
  "Linguaggio onesto: parla di esplorazione, non di guarigione",
  "Ottima esperienza, aspettative oneste", "Si', se i numeri sono
  onesti". Li' non e' un vanto, e' un criterio.

RESTA — quando "davvero" porta un contrasto vero:
  "se le tue prestazioni sono davvero saltuarie" (precisione
  fiscale), "servizi davvero individuali", "la pratica migliore e'
  quella che FAI davvero", "arrivare davvero, non solo col corpo".
Toglierlo li' toglierebbe il senso, non il tic.

Idempotente: sostituzioni esatte che spariscono dopo la prima
applicazione.

    venv/bin/python scripts/pc7_voce_nei_testi.py [--dry-run]
"""
import asyncio
import os
import re
import sys

# (slug, testo esatto, sostituto)
CAMBI = [
    ("bagno-di-gong-sound-healing-benefici",
     "Con onestà: la ricerca scientifica sul sound healing specifico è ancora giovane",
     "La ricerca scientifica sul sound healing specifico è ancora giovane"),

    ("campane-tibetane-benefici-come-funzionano",
     "cosa aspettarsi da un trattamento, con la solita onestà.",
     "cosa aspettarsi da un trattamento."),
    ("campane-tibetane-benefici-come-funzionano",
     "Come per tutto il sound healing, onestà: gli studi specifici sulle campane sono pochi e piccoli.",
     "Come per tutto il sound healing, gli studi specifici sulle campane sono pochi e piccoli."),

    ("cerchi-di-donne-cosa-sono-come-funzionano",
     "Questa guida risponde alle domande che tutte fanno prima del primo cerchio, senza misteri e senza idealizzazioni.",
     "Questa guida risponde alle domande che tutte fanno prima del primo cerchio."),

    ("come-promuovere-un-ritiro-e-riempire-i-posti",
     "Questa guida raccoglie quello che funziona davvero, osservando gli operatori",
     "Questa guida raccoglie quello che funziona, osservando gli operatori"),

    ("costellazioni-familiari-cosa-sono-come-funzionano",
     "Questa guida racconta cosa sono davvero, cosa succede in una sessione e, con l'onestà che ci caratterizza, cosa dice (e cosa non dice) la ricerca.",
     "Questa guida racconta cosa sono, cosa succede in una sessione e cosa dice, o non dice, la ricerca."),

    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "il marketing ha sepolto una pratica che, raccontata onestamente, ha un",
     "il marketing ha sepolto una pratica che ha un"),

    ("kit-pratiche-quotidiane-15-minuti",
     "per ognuna trovi il protocollo passo passo, quanto tempo serve davvero, cosa dice la r",
     "per ognuna trovi il protocollo passo passo, quanto tempo serve, cosa dice la r"),
    ("kit-pratiche-quotidiane-15-minuti",
     "Una nota di onesta' che vale per tutto il kit: queste pratiche sostengono",
     "Una nota che vale per tutto il kit: queste pratiche sostengono"),
    ("kit-pratiche-quotidiane-15-minuti",
     "C'e' un limite onesto in tutto questo: 15 minuti al giorno mantengono",
     "C'e' un limite in tutto questo: 15 minuti al giorno mantengono"),

    ("lettura-tema-natale-cosa-aspettarsi",
     "Questa guida spiega cosa aspettarsi davvero da un consulto, scritta da chi lo fa con serietà e senza promesse impossibili.",
     "Questa guida spiega cosa aspettarsi da un consulto e come si riconosce chi lo conduce con serietà."),
    ("lettura-tema-natale-cosa-aspettarsi",
     "E l'onestà fino in fondo: l'astrologia non ha validazione scientifica",
     "E il punto che conta: l'astrologia non ha validazione scientifica"),

    ("meditazione-per-chi-inizia-guida-semplice",
     "** Davvero, è tutto qui.",
     "** È tutto qui."),
    ("meditazione-per-chi-inizia-guida-semplice",
     "Due onestà doverose.",
     "Due cose da dire."),

    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "tra tutte le pratiche che promettono di aiutare, cosa funziona davvero?",
     "tra tutte le pratiche che promettono di aiutare, cosa funziona?"),
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "Questa guida risponde con la regola della casa: onestà radicale.",
     "Questa guida risponde guardando cosa dicono gli studi, dove ci sono."),
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "[Ne abbiamo scritto con onestà](/blog/reiki-cose-come-funziona-una-sessione)",
     "[Ne abbiamo scritto qui](/blog/reiki-cose-come-funziona-una-sessione)"),
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "quelle che percorri davvero, un respiro alla volta, con l'onestà di sapere cosa possono fare e cosa no.",
     "quelle che percorri davvero, un respiro alla volta, sapendo cosa possono fare e cosa no."),

    # I TITOLI DI SEZIONE, trovati alla seconda lettura. Sono i piu'
    # visibili di tutti: li legge chi scorre e li legge un motore di
    # ricerca. "La parte onesta" dice al lettore che le altre sezioni
    # lo sono meno.
    ("bagno-di-gong-sound-healing-benefici",
     "## Cosa si prova (racconto onesto)", "## Cosa si prova"),
    ("meditazione-per-chi-inizia-guida-semplice",
     "## Cosa dice la scienza (onestamente)", "## Cosa dice la scienza"),
    ("costellazioni-familiari-cosa-sono-come-funzionano",
     "## Cosa dice la ricerca: la parte onesta", "## Cosa dice la ricerca"),
    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "## I benefici onesti (quelli che puoi aspettarti)",
     "## I benefici (quelli che puoi aspettarti)"),
    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "## Cosa succede davvero in un ritiro detox serio",
     "## Cosa succede in un ritiro detox serio"),
    ("kit-pratiche-quotidiane-15-minuti",
     "cosa dice la ricerca (onestamente, senza gonfiare) e gli errori",
     "cosa dice la ricerca e gli errori"),
    ("kit-pratiche-quotidiane-15-minuti",
     "Come riuscirci davvero:", "Come riuscirci:"),
    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "## Quando le pratiche NON bastano (leggilo davvero)",
     "## Quando le pratiche non bastano"),
]

# quello che DEVE restare: se una di queste sparisce, il criterio e'
# stato applicato a macchina invece che a mano.
DA_CONSERVARE = [
    ("partita-iva-operatore-olistico-fiscalita-guida", "davvero saltuarie"),
    ("prezzo-giusto-ritiro-come-calcolarlo", "davvero individuali"),
    ("pratiche-olistiche-contro-stress-cosa-funziona", "quella che FAI davvero"),
    ("cerchi-di-donne-cosa-sono-come-funzionano", "arrivare davvero"),
    ("costellazioni-familiari-cosa-sono-come-funzionano", "Linguaggio onesto"),
    ("come-promuovere-un-ritiro-e-riempire-i-posti", "se i numeri sono onesti"),
    ("pratiche-olistiche-contro-stress-cosa-funziona", "aspettative oneste"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    testi = {}

    async def contenuto(slug):
        if slug not in testi:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
            testi[slug] = d["content"] if d else None
        return testi[slug]

    fatti = gia = persi = 0
    for slug, vecchio, nuovo in CAMBI:
        c = await contenuto(slug)
        if c is None:
            print(f"  ASSENTE {slug}")
            continue
        if vecchio in c:
            testi[slug] = c.replace(vecchio, nuovo, 1)
            fatti += 1
        elif nuovo in c:
            gia += 1
        else:
            print(f"  NON TROVATO in {slug[:42]}: «{vecchio[:60]}…»")
            persi += 1

    if not dry_run:
        for slug, c in testi.items():
            if c is not None:
                await db.articles.update_one({"slug": slug},
                                             {"$set": {"content": c}})

    print(f"\nsostituzioni: {fatti} applicate, {gia} gia' a posto, {persi} non trovate")

    print("\n── quello che deve essere rimasto")
    for slug, frammento in DA_CONSERVARE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        ok = d and frammento in d["content"]
        print(f"  {'ok ' if ok else 'PERSO'} {slug[:42]}: «{frammento}»")

    print("\n── tic residui nei testi")
    tic = re.compile(r"(davvero|onest\w+|senza misteri|senza promesse|"
                     r"senza fronzoli|falsi miti)", re.I)
    resti = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1}):
        for h in tic.finditer(a["content"]):
            i = max(0, h.start() - 55)
            print(f"  {a['slug'][:34]:36} …{a['content'][i:h.end() + 55]}…"
                  .replace("\n", " "))
            resti += 1
    print(f"  totale: {resti} (attesi solo quelli dell'elenco da conservare)")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
