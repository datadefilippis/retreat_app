"""PE3 — via dai titoli i qualificatori che si auto-elogiano.

IL DIFETTO. "guida onesta", "senza fronzoli", "spiegati bene",
"davvero", "senza svendersi", "falsi miti", "senza fumo": aggettivi
che DICHIARANO il valore invece di dimostrarlo. Sono difensivi (una
guida che deve dirsi onesta insinua il dubbio che le altre non lo
siano, e la propria) e occupano caratteri che dovrebbero portare le
parole con cui la gente cerca davvero.

Si toccano titolo e descrizione, perche' sono le due righe che si
leggono nei risultati di ricerca. **Lo slug NON si tocca**: e'
l'indirizzo che i motori hanno indicizzato.

Restano invariati "cosa dice la scienza" e "cosa dice la ricerca":
non sono tic, sono la promessa dell'articolo.

Idempotente: rilanciarlo non cambia nulla.

    venv/bin/python scripts/pe3_titoli_senza_autoelogi.py [--dry-run]
"""
import asyncio
import os
import sys

# slug → (titolo nuovo, descrizione nuova). La descrizione sta sotto i
# 155 caratteri: oltre, i risultati di ricerca la tagliano a meta'.
NUOVI = {
    "kit-pratiche-quotidiane-15-minuti": (
        "Il kit delle pratiche quotidiane: 15 minuti al giorno",
        "Sette pratiche olistiche essenziali in un unico kit: protocolli "
        "passo passo, cosa dice la ricerca, errori comuni e come costruire "
        "la tua routine di 15 minuti.",
    ),
    "meditazione-per-chi-inizia-guida-semplice": (
        "Meditazione per chi inizia: come cominciare e cosa aspettarsi",
        "Come iniziare a meditare: 5 minuti al giorno, gli errori che fanno "
        "mollare tutti, cosa dice la scienza e quando un ritiro accelera la "
        "pratica.",
    ),
    "partita-iva-operatore-olistico-fiscalita-guida": (
        "Partita IVA e fiscalità per operatori olistici: la guida 2026",
        "Quando serve la partita IVA, il codice ATECO, il forfettario con un "
        "esempio numerico, INPS e legge 4/2013. La guida per chi lavora nel "
        "benessere.",
    ),
    "come-promuovere-un-ritiro-e-riempire-i-posti": (
        "Come promuovere un ritiro e riempire i posti",
        "Strategie concrete per riempire un ritiro: il pubblico che hai già, "
        "la pagina che converte, caparre e recensioni.",
    ),
    "prezzo-giusto-ritiro-come-calcolarlo": (
        "Come calcolare il prezzo di un ritiro",
        "Costi reali, punto di pareggio, psicologia del prezzo e gli errori "
        "che fanno lavorare in perdita.",
    ),
    "digiuno-consapevole-detox-benefici-falsi-miti": (
        "Digiuno consapevole e detox: cosa sono, benefici e controindicazioni",
        "Digiuno consapevole e ritiri detox: cosa dice la scienza, il mito "
        "delle tossine, per chi sono adatti e come scegliere un ritiro "
        "serio.",
    ),
    # Questi otto avevano il titolo pulito e il tic nella descrizione,
    # che e' l'altra riga che si legge nei risultati di ricerca.
    # "spiegato da chi lo pratica" resta dov'e': non e' un elogio, e'
    # un'informazione sulla fonte, ed e' la cosa che ci distingue.
    "breathwork-cose-tecniche-benefici": (
        "Breathwork: cos'è, le tecniche principali, benefici e controindicazioni",
        "Respirazione consapevole: le tecniche principali, cosa si prova, "
        "benefici documentati e controindicazioni.",
    ),
    "campane-tibetane-benefici-come-funzionano": (
        "Campane tibetane: benefici e differenza con il cristallo",
        "Le campane tibetane raccontate da chi le suona: come funzionano, "
        "cosa si prova in un trattamento e le differenze con le campane di "
        "cristallo.",
    ),
    "cerchi-di-donne-cosa-sono-come-funzionano": (
        "Cerchi di donne: cosa sono, come funzionano, come trovarne uno",
        "Cosa succede in un cerchio di donne, come si svolge un incontro e "
        "come trovarne uno vicino a te. Il racconto di una facilitatrice.",
    ),
    "costellazioni-familiari-cosa-sono-come-funzionano": (
        "Costellazioni familiari: cosa sono e cosa dice la ricerca",
        "Come funziona una sessione di costellazioni familiari, cosa si "
        "prova, cosa dice la ricerca scientifica e come scegliere un "
        "facilitatore.",
    ),
    "lettura-tema-natale-cosa-aspettarsi": (
        "Lettura del tema natale: a cosa serve e cosa aspettarsi da un consulto",
        "Cos'è il tema natale, come si svolge una lettura, a cosa serve e "
        "come scegliere chi la fa. Il racconto di chi legge i cieli.",
    ),
    "pratiche-olistiche-contro-stress-cosa-funziona": (
        "Pratiche olistiche contro lo stress: cosa funziona secondo la ricerca",
        "Meditazione, respirazione, yoga, natura e suono: cosa dice la "
        "ricerca sulle pratiche per lo stress, come scegliere e quando "
        "serve un professionista.",
    ),
    "reiki-cose-come-funziona-una-sessione": (
        "Reiki: cos'è, come funziona una sessione e cosa si sente",
        "Il Reiki raccontato da chi lo pratica: origini, come si svolge una "
        "sessione, cosa si sente e come scegliere un operatore.",
    ),
    "tarocchi-oracoli-strumento-evolutivo": (
        "Tarocchi e oracoli come strumento evolutivo: come funziona un consulto",
        "I tarocchi evolutivi raccontati da chi li legge: differenza dalla "
        "cartomanzia, come funziona un consulto e come riconoscere un "
        "lettore serio.",
    ),
}


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    cambiati = 0
    for slug, (titolo, descrizione) in NUOVI.items():
        doc = await db.articles.find_one(
            {"slug": slug}, {"_id": 0, "title": 1, "description": 1})
        if not doc:
            print(f"  ASSENTE: {slug}")
            continue
        if doc.get("title") == titolo and doc.get("description") == descrizione:
            continue
        print(f"\n{slug}")
        print(f"  T  {doc.get('title')}")
        print(f"  →  {titolo}")
        if doc.get("description") != descrizione:
            print(f"  D  ({len(descrizione)} car.) {descrizione}")
        cambiati += 1
        if not dry_run:
            await db.articles.update_one(
                {"slug": slug},
                {"$set": {"title": titolo, "description": descrizione}})

    if not cambiati:
        print("titoli e descrizioni gia' a posto: niente da fare")
    elif dry_run:
        print(f"\n--dry-run: {cambiati} da cambiare, nessuna scrittura")
    else:
        print(f"\naggiornati: {cambiati}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
