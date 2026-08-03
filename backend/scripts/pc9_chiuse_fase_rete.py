"""PC9 — dodici articoli chiudevano promettendo il marketplace.

COSA HO TROVATO. Cercando un link mancante e' saltata fuori una cosa
piu' seria: dodici articoli su ventidue finivano con un paragrafo che
promette "al lancio ti proporremo esperienze scelte per te", "profili
chiari e recensioni verificate", "le prenotazioni arrivano con caparra
e pagamento online", "paghi una piccola commissione". E' il sito della
fase precedente. Oggi il sito e' una rete di professionisti
intervistati, e niente di tutto quello esiste.

I LINK NON SONO ROTTI, ed e' il motivo per cui la cosa era passata
inosservata: /cerca-ritiro reindirizza su /newsletter e /per-operatori
su /entra-nella-rete. Il lettore clicca "raccontaci cosa cerchi" e
atterra sulla Lettera. Il testo promette una cosa e la destinazione ne
consegna un'altra.

E SONO DOPPIONI. BlogArticlePage aggiunge gia' una chiamata in fondo a
ogni articolo, scelta in base alla categoria: la Lettera per i pezzi
dei lettori, /entra-nella-rete per quelli dei professionisti. Quei
paragrafi ripetevano una CTA che il componente mette gia', e la
ripetevano con le parole sbagliate.

COSA RESTA. Il contenuto vero dentro quei paragrafi (dove c'era) e
tutti i link interni: dove la promessa era incastrata insieme a un
rimando utile, il rimando sopravvive come frase propria. In due casi
la sezione perdeva senso restando monca — "Come trovare un cerchio",
"Dove entra Aurya" — e l'ho riscritta con quello che il lettore
cercava li'.

UNA FRASE RESTA COM'E': "E' uno dei criteri con cui selezioniamo chi
entra su Aurya", nell'articolo sullo stress. Nella fase rete e' vera:
la selezione la facciamo per davvero.

    venv/bin/python scripts/pc9_chiuse_fase_rete.py [--dry-run]
"""
import asyncio
import os
import re
import sys

SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"

# (slug, testo esatto da togliere o sostituire, sostituto)
CAMBI = [
    # ── gli otto in cui basta togliere la coda promozionale.
    ("come-promuovere-un-ritiro-e-riempire-i-posti",
     "\n\nÈ esattamente quello che stiamo costruendo con Aurya: la casa dei "
     "ritiri olistici italiani, dove il tuo profilo racconta chi sei, le "
     "prenotazioni arrivano con caparra e pagamento diretto, e le recensioni "
     "verificate costruiscono la tua reputazione nel tempo. Entrare è gratis: "
     "paghi una piccola commissione solo sulle prenotazioni che ti portiamo "
     "noi. Se il cliente è tuo, non paghi nulla.\n\n"
     "[Presentati qui](/per-operatori): i primi operatori entrano da "
     "fondatori, con visibilità in prima fila al lancio.", ""),

    ("bagno-di-gong-sound-healing-benefici",
     "\n\nSu Aurya stiamo riunendo le esperienze di suono e sound healing di "
     "tutta Italia, con operatori dal volto chiaro e recensioni verificate. "
     "[Raccontaci cosa cerchi](/cerca-ritiro): al lancio ti proporremo "
     "esperienze scelte per te.", ""),

    ("campane-tibetane-benefici-come-funzionano",
     "\n\nSu Aurya stiamo riunendo operatori del suono ed esperienze di tutta "
     "Italia, con profili chiari e recensioni verificate. [Raccontaci cosa "
     "cerchi](/cerca-ritiro): al lancio ti proporremo esperienze adatte a te.",
     ""),

    ("tarocchi-oracoli-strumento-evolutivo",
     "\n\nSu Aurya stiamo riunendo gli operatori olistici italiani, lettrici e "
     "lettori seri compresi, con profili chiari e recensioni verificate. "
     "[Raccontaci cosa cerchi](/cerca-ritiro): al lancio ti aiuteremo a "
     "trovare la persona giusta.", ""),

    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "\n\nSu Aurya stiamo riunendo i ritiri detox seri d'Italia, con profili "
     "chiari e recensioni verificate di chi c'è stato. [Raccontaci cosa "
     "cerchi](/cerca-ritiro): al lancio ti proporremo esperienze adatte al "
     "tuo punto di partenza.", ""),

    ("prezzo-giusto-ritiro-come-calcolarlo",
     "\n\nÈ la stessa filosofia con cui costruiamo Aurya: prezzi chiari, "
     "condizioni visibili prima del pagamento, caparra e incasso online senza "
     "rincorse. Entrare è gratis e paghi una piccola commissione solo sulle "
     "prenotazioni che il calendario pubblico ti porta: se il cliente è tuo, "
     "non paghi nulla. [Presentati qui](/per-operatori): i primi operatori "
     "entrano da fondatori.", ""),

    ("pratiche-olistiche-contro-stress-cosa-funziona",
     "\n\nSe senti che è il momento di dare una struttura al tuo percorso, "
     "[raccontaci cosa cerchi](/cerca-ritiro): al lancio di Aurya ti "
     "proporremo esperienze e operatori scelti, con recensioni verificate e "
     "la trasparenza che questo mondo merita.", ""),

    # ── i tre in cui la promessa era incastrata con un rimando utile:
    #    il rimando sopravvive, la promessa no.
    ("lettura-tema-natale-cosa-aspettarsi",
     "Su Aurya stiamo riunendo gli operatori olistici italiani, letture dei "
     "cieli comprese, con profili chiari e recensioni verificate. "
     "[Raccontaci cosa cerchi](/cerca-ritiro) e al lancio ti aiuteremo a "
     "trovare la persona giusta. Se invece la domanda è più larga, parti da "
     f"[come capire se un operatore è serio]({SERIO}).",
     "Su come si riconosce chi conduce un consulto con serietà, i criteri "
     f"generali stanno in [come capire se un operatore è serio]({SERIO})."),

    ("meditazione-per-chi-inizia-guida-semplice",
     "Se senti che è il momento di fare sul serio, [raccontaci cosa cerchi]"
     "(/cerca-ritiro): al lancio di Aurya ti proporremo ritiri di meditazione "
     "scelti per te, con guide dal volto chiaro e recensioni verificate. E "
     "per capire come scegliere chi ti accompagna, leggi [come capire se un "
     f"operatore è serio]({SERIO}).",
     "Se stai valutando un ritiro di meditazione, la scelta di chi lo conduce "
     "pesa più del luogo: i criteri stanno in [come capire se un operatore è "
     f"serio]({SERIO}), e le domande da fare prima di prenotare le abbiamo "
     "raccolte [qui](/blog/domande-da-fare-prima-di-prenotare-un-ritiro)."),

    ("costellazioni-familiari-cosa-sono-come-funzionano",
     "Le costellazioni compaiono spesso nei ritiri olistici come esperienza "
     "serale o come giornata dedicata, e il contesto del ritiro (gruppo che "
     "si conosce, tempo disteso, natura) le rende spesso più profonde di una "
     "serata singola in città. Se l'esperienza ti incuriosisce, [raccontaci "
     "cosa cerchi](/cerca-ritiro): al lancio di Aurya ti proporremo "
     "esperienze con facilitatori dal volto chiaro e recensioni verificate. "
     "Per capire come si valuta chi conduce, parti da [come capire se un "
     f"operatore è serio]({SERIO}).",
     "Le costellazioni compaiono spesso nei ritiri olistici come esperienza "
     "serale o come giornata dedicata, e il contesto del ritiro (gruppo che "
     "si conosce, tempo disteso, natura) le rende spesso più profonde di una "
     "serata singola in città. Per capire come si valuta chi conduce, parti "
     f"da [come capire se un operatore è serio]({SERIO})."),

    # ── i due in cui la sezione restava monca: riscritta con quello
    #    che il lettore era venuto a cercare in quel punto.
    ("cerchi-di-donne-cosa-sono-come-funzionano",
     "Oggi i canali sono sparsi: passaparola, gruppi social locali, studi di "
     "yoga che ospitano cerchi mensili. È esattamente la frammentazione che "
     "stiamo ricucendo con Aurya: la casa dei ritiri olistici italiani "
     "riunirà anche i cerchi di donne e le esperienze del femminile, con "
     "facilitatrici dal volto chiaro e recensioni verificate.\n\n"
     "Nel frattempo, se un cerchio o un ritiro del femminile ti chiama, "
     "[raccontaci cosa cerchi](/cerca-ritiro): al lancio ti proporremo "
     "esperienze scelte per te.",
     "I canali sono sparsi: passaparola, gruppi social locali, studi di yoga "
     "che ospitano cerchi mensili. Conviene chiedere direttamente nello "
     "studio dove pratichi, perché molti cerchi non vengono annunciati da "
     "nessun'altra parte.\n\n"
     "Quando ne trovi uno, le domande utili sono poche: chi lo facilita e con "
     "quale formazione, ogni quanto si tiene, se è un gruppo chiuso o aperto "
     "a nuove arrivate. Sono [le stesse che valgono per chiunque ti "
     f"accompagni]({SERIO})."),

    ("partita-iva-operatore-olistico-fiscalita-guida",
     "## Dove entra Aurya (e perché ti semplifica la vita fiscale)\n\n"
     "C'è un filo che unisce tutto questo articolo: la **tracciabilità**. "
     "Un'attività fiscalmente serena è un'attività dove ogni prenotazione, "
     "ogni caparra e ogni incasso hanno una traccia ordinata.\n\n"
     "È esattamente come funziona Aurya: le prenotazioni dei tuoi ritiri "
     "arrivano con caparra e pagamento online tracciato, ogni incasso è "
     "documentato e riconciliato nella tua tesoreria, e a fine anno hai il "
     "quadro pulito da passare al commercialista, senza fogli di calcolo "
     "ricostruiti a memoria. Entrare è gratis: profilo, vetrina e gestionale "
     "senza canone, con una piccola commissione solo sulle prenotazioni che "
     "ti porta il calendario pubblico. Se il cliente è tuo, non paghi "
     "nulla.\n\n"
     "[Presentati qui](/per-operatori): i primi operatori entrano da "
     "fondatori. E se stai costruendo i tuoi primi ritiri, leggi anche [come "
     "calcolare il prezzo giusto](/blog/prezzo-giusto-ritiro-come-calcolarlo) "
     "e [come riempire i posti]"
     "(/blog/come-promuovere-un-ritiro-e-riempire-i-posti).",

     "## La tracciabilità è la vera semplificazione\n\n"
     "C'è un filo che unisce tutto questo articolo: un'attività fiscalmente "
     "serena è quella dove ogni prenotazione, ogni caparra e ogni incasso "
     "hanno una traccia ordinata. Non è una questione di software, è "
     "l'abitudine di registrare le cose quando succedono invece di "
     "ricostruirle a memoria a marzo.\n\n"
     "In pratica: un conto separato dal personale, le caparre incassate con "
     "un metodo tracciabile, e le condizioni di cancellazione scritte prima "
     "del pagamento — perché un rimborso senza una regola concordata diventa "
     "una discussione, e la discussione lascia il segno anche in "
     "contabilità.\n\n"
     "Se stai costruendo i tuoi primi ritiri, leggi anche [come calcolare il "
     "prezzo giusto](/blog/prezzo-giusto-ritiro-come-calcolarlo) e [come "
     "riempire i posti](/blog/come-promuovere-un-ritiro-e-riempire-i-posti)."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    testi = {}
    fatti = gia = persi = 0
    for slug, vecchio, nuovo in CAMBI:
        if slug not in testi:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
            testi[slug] = d["content"] if d else None
        c = testi[slug]
        if c is None:
            print(f"  ASSENTE {slug}")
            continue
        if vecchio in c:
            testi[slug] = c.replace(vecchio, nuovo, 1).rstrip() + "\n"
            fatti += 1
        elif nuovo and nuovo in c:
            gia += 1
        else:
            print(f"  NON TROVATO in {slug}")
            persi += 1

    if not dry_run:
        for slug, c in testi.items():
            if c is not None:
                await db.articles.update_one({"slug": slug},
                                             {"$set": {"content": c}})

    print(f"\nchiuse riscritte: {fatti}, gia' a posto: {gia}, non trovate: {persi}")

    print("\n── promesse della fase precedente rimaste")
    vecchia = re.compile(r"(/cerca-ritiro|/per-operatori|al lancio|"
                         r"stiamo riunendo|recensioni verificate|"
                         r"entrano da fondatori|piccola commissione)", re.I)
    resti = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1}):
        for h in vecchia.finditer(a["content"]):
            i = max(0, h.start() - 60)
            print(f"  {a['slug'][:34]:36} …{a['content'][i:h.end() + 60]}…"
                  .replace("\n", " "))
            resti += 1
    print(f"  totale: {resti}")

    print("\n── link interni")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"  rotti: {rotti or 'nessuno'}")
    print(f"  articoli: {len(arts)}, parole: "
          f"{sum(len(a['content'].split()) for a in arts)}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
