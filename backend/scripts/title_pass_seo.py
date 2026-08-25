#!/usr/bin/env python3
"""Title pass SEO (26/8/2026) — 24 titoli che si troncavano in SERP.

Il titolo in pagina dei risultati è l'unica cosa che decide se ti
cliccano, e Google ne mostra ~60 caratteri: col suffisso « | Aurya»
(8) il testo utile è ~52. Ventiquattro articoli su 47 sforavano, e i
titoli tagliati a metà («...e cosa si sen…») buttano via proprio la
parte che convince.

La regola delle riscritture: la parola chiave resta IN TESTA, la voce
resta onesta, si taglia la coda ridondante — mai il senso. Il titolo è
anche l'H1 della pagina: cambia pure quello, e va bene, perché queste
versioni corte sono titoli migliori anche per chi legge. Lo slug (e
quindi l'URL) NON cambia mai: nessun link si rompe.

Non sovrascrive un titolo cambiato a mano nel frattempo: applica solo
se trova ESATTAMENTE il titolo vecchio atteso.

Uso:
  python3 scripts/title_pass_seo.py --prova
  python3 scripts/title_pass_seo.py --esegui
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# slug → (titolo atteso oggi, titolo nuovo ≤52)
TITLES = {
    "aromaterapia-cose-come-si-usa-ricerca": (
        "Aromaterapia: cos'è, come si usa e cosa dice la ricerca",
        "Aromaterapia: cos'è, usi e cosa dice la ricerca"),
    "assicurazione-rc-operatore-olistico": (
        "Assicurazione per operatori olistici: cosa serve davvero",
        "Assicurazione RC per operatori olistici: la guida"),
    "ayurveda-cose-i-tre-dosha-cosa-aspettarsi": (
        "Ayurveda: cos'è, i tre dosha e cosa aspettarsi da una visita",
        "Ayurveda: cos'è, i dosha e come funziona la visita"),
    "bagno-di-gong-sound-healing-benefici": (
        "Bagno di gong: come funziona una sessione e cosa si prova",
        "Bagno di gong: come funziona e cosa si prova"),
    "bio-professionale-operatore-olistico": (
        "La bio professionale che crea fiducia: guida per operatori",
        "Bio professionale dell'operatore olistico: la guida"),
    "camminare-bagni-di-foresta-cammini": (
        "Camminare come pratica: bagni di foresta, cammini, natura",
        "Bagni di foresta e cammini: camminare come pratica"),
    "campane-tibetane-benefici-come-funzionano": (
        "Campane tibetane: benefici e differenza con il cristallo",
        "Campane tibetane: benefici e come funzionano"),
    "chakra-cosa-sono-i-sette-come-si-usano": (
        "I chakra: cosa sono, quali sono i sette e come si usano",
        "I sette chakra: cosa sono e come si usano"),
    "ciclo-mestruale-quattro-fasi-come-ascoltarlo": (
        "Il ciclo mestruale come mappa: le quattro fasi, cosa cambia",
        "Ciclo mestruale: le quattro fasi come mappa"),
    "come-scegliere-un-insegnante-di-yoga": (
        "Come scegliere un insegnante di yoga: i segnali che contano",
        "Come scegliere un insegnante di yoga"),
    "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini": (
        "Tipi di yoga: differenze fra hatha, vinyasa, yin e altri",
        "Tipi di yoga: hatha, vinyasa, yin e le differenze"),
    "kit-pratiche-quotidiane-15-minuti": (
        "Quindici minuti al giorno: sette pratiche spiegate per bene",
        "Sette pratiche da quindici minuti al giorno"),
    "kriya-yoga-cose-come-funziona": (
        "Kriya yoga: cos'è, da dove viene e in cosa si distingue",
        "Kriya yoga: cos'è e in cosa si distingue"),
    "massaggio-olistico-tipi-cosa-aspettarsi": (
        "Massaggio olistico: i tipi principali e cosa aspettarsi",
        "Massaggio olistico: i tipi e cosa aspettarsi"),
    "naturopatia-cose-consulto-cosa-dice-ricerca": (
        "Naturopatia: cos'è, il consulto e cosa dice la ricerca",
        "Naturopatia: cos'è e cosa dice la ricerca"),
    "pratiche-olistiche-contro-stress-cosa-funziona": (
        "Pratiche contro lo stress: cosa funziona secondo la ricerca",
        "Pratiche contro lo stress: cosa funziona"),
    "prezzo-giusto-ritiro-come-calcolarlo": (
        "Come calcolare il prezzo di un ritiro, passo per passo",
        "Come calcolare il prezzo di un ritiro"),
    "rebirthing-cose-come-funziona-una-sessione": (
        "Rebirthing: cos'è, la sessione e le controindicazioni",
        "Rebirthing: cos'è e le controindicazioni"),
    "reiki-cose-come-funziona-una-sessione": (
        "Reiki: cos'è, come funziona una sessione e cosa si sente",
        "Reiki: cos'è e come funziona una sessione"),
    "respiro-sistema-nervoso-cosa-succede": (
        "Respiro e sistema nervoso: cosa succede quando rallenti",
        "Respiro e sistema nervoso: cosa succede"),
    "shiatsu-cose-come-funziona-una-seduta": (
        "Shiatsu: come funziona una seduta, e perché si resta vestiti",
        "Shiatsu: come funziona una seduta"),
    "smettere-alcol-zucchero-caffeina-cosa-succede": (
        "Alcol, zucchero e caffeina: cosa succede quando smetti",
        "Smettere alcol, zucchero e caffeina: cosa succede"),
    "tarocchi-oracoli-strumento-evolutivo": (
        "Tarocchi evolutivi: cosa sono, come funziona un consulto",
        "Tarocchi evolutivi: cosa sono e come funzionano"),
    "yoga-nidra-cose-come-funziona-una-sessione": (
        "Yoga nidra: cos'è, come funziona una sessione e a cosa serve",
        "Yoga nidra: cos'è e come funziona una sessione"),
}


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prova", action="store_true")
    g.add_argument("--esegui", action="store_true")
    args = ap.parse_args()

    from database import db
    from models.common import utc_now

    # la rete di sicurezza prima di tutto: nessun titolo nuovo sfora
    for slug, (_, nuovo) in TITLES.items():
        if len(nuovo) > 52:
            sys.exit(f"FERMO: '{nuovo}' ha {len(nuovo)} caratteri (max 52)")

    fatti = saltati = 0
    for slug, (atteso, nuovo) in sorted(TITLES.items()):
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "title": 1})
        if not doc:
            print(f"  !  {slug}: non trovato")
            continue
        if doc["title"] != atteso:
            print(f"  =  {slug}: titolo diverso dall'atteso, NON toccato")
            saltati += 1
            continue
        if args.esegui:
            await db.articles.update_one(
                {"slug": slug},
                {"$set": {"title": nuovo, "updated_at": utc_now()}})
        print(f"  +  {slug}")
        print(f"       {len(atteso)+8:>3} → {len(nuovo)+8:<3} {nuovo}")
        fatti += 1

    print(f"\n{'PROVA' if args.prova else 'FATTI'}: {fatti} · saltati: {saltati}")


if __name__ == "__main__":
    asyncio.run(main())
