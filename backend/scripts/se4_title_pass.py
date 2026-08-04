"""SE4 — title pass: gli 11 title oltre i 60 caratteri.

PERCHE'. Google tronca i title in SERP intorno ai 580px (~60
caratteri), e la shell aggiunge " | Aurya" (+8): gli 11 title lunghi
arrivavano troncati proprio dove stava la promessa. La regola del
pass: keyword primaria nei primi caratteri, il taglio non butta via
il significato ma il di piu' ("la guida completa", "una per una",
le enumerazioni doppie).

COSA NON CAMBIA. Le description (tutte gia' nel taglio), gli slug
(gli URL non si toccano), il contenuto. Il title e' anche l'H1 della
pagina articolo: i nuovi restano frasi vere, non stringhe da SERP.

Idempotente: riesegue senza effetto se i title sono gia' i nuovi.
Da rieseguire in produzione al lancio.

    venv/bin/python scripts/se4_title_pass.py [--dry-run]
"""
import asyncio
import os
import sys

# (slug, title vecchio, title nuovo ≤60)
CAMBI = [
    ("alimentazione-ayurvedica-principi-sei-sapori",
     "Alimentazione ayurvedica: come si mangia, prima ancora di cosa",
     "Alimentazione ayurvedica: come si mangia e perché"),
    ("pranayama-tecniche-respirazione-yoga",
     "Pranayama: le tecniche di respirazione dello yoga, una per una",
     "Pranayama: le tecniche di respirazione dello yoga"),
    ("come-capire-se-un-operatore-olistico-e-serio",
     "Come capire se un operatore olistico è serio: la guida completa",
     "Come capire se un operatore olistico è serio"),
    ("rebirthing-cose-come-funziona-una-sessione",
     "Rebirthing: cos'è, come funziona una sessione e quando è sconsigliato",
     "Rebirthing: cos'è, la sessione e le controindicazioni"),
    ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
     "Hatha, vinyasa, ashtanga, yin, kundalini: le differenze fra i tipi di yoga",
     "Tipi di yoga: differenze fra hatha, vinyasa, yin e altri"),
    ("partita-iva-operatore-olistico-fiscalita-guida",
     "Partita IVA e fiscalità per operatori olistici: la guida 2026",
     "Partita IVA per operatori olistici: la guida 2026"),
    ("breathwork-cose-tecniche-benefici",
     "Breathwork: cos'è, le tecniche principali, benefici e controindicazioni",
     "Breathwork: cos'è, tecniche e controindicazioni"),
    ("costellazioni-familiari-cosa-sono-come-funzionano",
     "Costellazioni familiari: cosa sono e cosa succede in una sessione",
     "Costellazioni familiari: cosa sono e come funzionano"),
    ("digiuno-consapevole-detox-benefici-falsi-miti",
     "Digiuno e detox: cosa succede nel corpo, benefici, controindicazioni",
     "Digiuno e detox: benefici veri e controindicazioni"),
    ("lettura-tema-natale-cosa-aspettarsi",
     "Lettura del tema natale: cos'è, come funziona, cosa aspettarsi",
     "Lettura del tema natale: cos'è e cosa aspettarsi"),
    ("meditazione-per-chi-inizia-guida-semplice",
     "Meditazione per chi inizia: come cominciare e cosa aspettarsi",
     "Meditazione per chi inizia: la guida semplice"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for _, vecchio, nuovo in CAMBI:
        assert len(nuovo) <= 60, f"nuovo title oltre i 60: {nuovo!r}"
        assert len(nuovo) < len(vecchio), f"non accorcia: {nuovo!r}"

    fatti = gia = 0
    for slug, vecchio, nuovo in CAMBI:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "title": 1})
        if not d:
            print(f"  ASSENTE {slug}")
            continue
        if d["title"] == nuovo:
            gia += 1
            continue
        if d["title"] != vecchio:
            print(f"  DIVERSO {slug}: {d['title']!r}")
            continue
        print(f"  {len(vecchio)}→{len(nuovo)}  {slug}")
        if not dry_run:
            await db.articles.update_one({"slug": slug},
                                         {"$set": {"title": nuovo}})
        fatti += 1

    print(f"\naggiornati: {fatti}, gia' fatti: {gia}")
    # audit: dopo il pass nessun title pubblicato oltre i 60
    lunghi = []
    async for a in db.articles.find({"published": True},
                                    {"_id": 0, "slug": 1, "title": 1}):
        if len(a["title"]) > 60:
            lunghi.append((len(a["title"]), a["slug"]))
    print(f"title ancora oltre i 60: {lunghi or 'nessuno'}")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
