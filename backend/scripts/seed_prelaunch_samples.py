"""Popola la vetrina di pre-lancio con operatori e ritiri CAMPIONE.

Tutti i documenti sono marchiati is_sample=True → appaiono solo con
PRELAUNCH_MODE attivo (sfocati, non prenotabili) e si cancellano in un
colpo con scripts.wipe_prelaunch_samples. I dati veri non vengono toccati.

Idempotente: prima cancella i sample esistenti, poi reinserisce.

Uso:
    JWT_SECRET_KEY=... venv/bin/python -m scripts.seed_prelaunch_samples
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.prelaunch import SAMPLE_FLAG
from scripts.wipe_prelaunch_samples import wipe_samples


# PL14 — foto VERE (Pexels, ottimizzate) servite dal frontend: niente
# dipendenze esterne, la vetrina di pre-lancio è credibile anche offline.
def _img(name: str) -> str:
    return f"/media/prelaunch/{name}.jpg"


# name, slug, città, regione, lat, lng, tagline, bio, featured, rating(avg,count),
# ritiri: [(titolo, categoria, prezzo, "YYYY-MM-DD", durata_giorni, foto)]
#
# PL14 — i titoli sono EVOCATIVI e descrittivi (comunicano il concept al
# visitatore) ma non identitari: il nome dell'organizzatore resta redatto.
# Tutte le date nel 2027, distribuite lungo l'anno.
_OPERATORS = [
    ("Masseria degli Ulivi", "masseria-ulivi-sample", "Ostuni", "Puglia",
     40.7295, 17.5772, "Yoga e silenzio tra gli ulivi secolari",
     "Un casale di pietra nella campagna di Ostuni: pratica al mattino, "
     "cucina del territorio, e il silenzio vero della Valle d'Itria.",
     True, (4.9, 23),
     [("Ritorna a respirare: yoga tra gli ulivi secolari della Valle d'Itria",
       "yoga", 690, "2027-05-14", 4, "r01"),
      ("Il tramonto in silenzio: due giorni per svuotare la mente",
       "meditazione", 320, "2027-06-18", 2, "r02")]),
    ("Rifugio del Bosco", "rifugio-bosco-sample", "Bolzano", "Trentino-Alto Adige",
     46.4983, 11.3548, "Cammini e respiro tra le Dolomiti",
     "Sulle porte delle Dolomiti: camminate consapevoli, bagni di foresta "
     "e breathwork con vista sulle vette.",
     True, (5.0, 17),
     [("A passo lento tra le Dolomiti: cinque giorni di cammino e respiro",
       "cammini", 850, "2027-07-05", 5, "r03"),
      ("Il respiro della foresta: breathwork e bagni di bosco in quota",
       "breathwork", 410, "2027-08-27", 3, "r04")]),
    ("Casa Serena Cilento", "casa-serena-sample", "Pollica", "Campania",
     40.1889, 15.0912, "Detox e mare nel cuore del Cilento",
     "Tra il blu del Cilento e gli orti biologici: detox dolce, yoga sulla "
     "terrazza e cene a km zero.",
     False, (4.8, 31),
     [("Ritrova leggerezza: detox dolce e yoga davanti al mare del Cilento",
       "detox", 740, "2027-06-07", 5, "r05")]),
    ("Borgo del Suono", "borgo-suono-sample", "Todi", "Umbria",
     42.7817, 12.4126, "Bagni di gong e meditazione nel cuore verde",
     "Un borgo umbro dove il suono guida la pratica: campane tibetane, gong "
     "e meditazione nel verde più profondo d'Italia.",
     False, (4.7, 12),
     [("Immersi nel suono: gong e campane tibetane nel cuore verde d'Italia",
       "suono", 280, "2027-04-16", 2, "r06"),
      ("Quattro giorni di silenzio per sentire di nuovo te stesso",
       "meditazione", 560, "2027-09-10", 4, "r07")]),
    ("Cascina Luna", "cascina-luna-sample", "Greve in Chianti", "Toscana",
     43.5836, 11.3157, "Cerchi femminili tra le vigne del Chianti",
     "Una cascina tra le vigne: cerchi femminili, yoga e vino naturale al "
     "tramonto, nel paesaggio più iconico della Toscana.",
     True, (4.9, 26),
     [("Cerchio di donne tra le vigne: tre giorni per ritrovarsi nel Chianti",
       "femminile", 620, "2027-05-28", 3, "r08"),
      ("Saluto al sole tra i filari: yoga e vino naturale in Toscana",
       "yoga", 390, "2027-09-24", 2, "r09")]),
    ("Eremo del Lago", "eremo-lago-sample", "Bracciano", "Lazio",
     42.1030, 12.1774, "Massaggio sonoro e riposo sulle rive del lago",
     "Sulle rive del lago di Bracciano, a un'ora da Roma: massaggio sonoro, "
     "meditazione e lunghe passeggiate sull'acqua.",
     False, (4.6, 9),
     [("Lascia andare: massaggio sonoro e riposo in riva al lago",
       "massaggio", 340, "2027-04-30", 2, "r10")]),
]


async def seed_samples() -> dict:
    from database import db

    wiped = await wipe_samples()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    orgs, stores, products, occs = [], [], [], []

    for (name, slug, city, region, lat, lng, tagline, bio,
         featured, rating, retreats) in _OPERATORS:
        org_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        # PL14 — cover = foto del primo ritiro; niente logo (il frontend
        # mostra la foglia Aurya) e gallery = foto dei ritiri dell'org
        _org_imgs = [_img(r[5]) for r in retreats]
        cover = _org_imgs[0]
        logo = None

        orgs.append({
            "id": org_id, "name": name, "is_active": True,
            "deactivated_at": None, "public_slug": slug,
            "created_at": now_iso,
            "directory_featured": featured,
            "reviews_stats": {"avg": rating[0], "count": rating[1]},
            "public_profile": {
                "bio": bio, "tagline": tagline, "city": city,
                "region": region, "latitude": lat, "longitude": lng,
                "cover_url": cover, "logo_url": logo,
                "founded_year": "2019", "languages": ["it", "en"],
                "photos": _org_imgs,
                "geo": {"type": "Point", "coordinates": [lng, lat]},
            },
            "store_settings": {"is_storefront_published": True,
                               "display_name": name},
            SAMPLE_FLAG: True,
        })
        stores.append({
            "id": store_id, "organization_id": org_id, "slug": slug,
            "name": name, "description": bio, "logo_url": logo,
            "is_published": True, "is_active": True, "visibility": "public",
            "created_at": now_iso, SAMPLE_FLAG: True,
        })

        for (title, category, price, date_str, duration, photo) in retreats:
            prod_id = str(uuid.uuid4())
            occ_id = str(uuid.uuid4())
            occ_slug = f"{slug}-{category}-{occ_id[:6]}"
            # PL14 — date esplicite nel 2027 (inizio ore 17, fine ore 12)
            start = datetime.fromisoformat(f"{date_str}T17:00:00+00:00")
            end = (start + timedelta(days=duration)).replace(hour=12)
            img = _img(photo)
            products.append({
                "id": prod_id, "organization_id": org_id, "name": title,
                "category": category, "item_type": "event_ticket",
                "transaction_mode": "direct", "unit_price": float(price),
                "currency": "EUR", "image_url": img,
                "is_published": True, "is_active": True,
                "store_ids": [store_id], "slug": occ_slug,
                "metadata": {}, "created_at": now_iso, SAMPLE_FLAG: True,
            })
            occs.append({
                "id": occ_id, "organization_id": org_id,
                "product_id": prod_id, "product_name": title,
                "slug": occ_slug, "status": "published",
                "start_at": start.isoformat()[:16],
                "end_at": end.isoformat()[:16],
                "city": city, "region": region, "country": "IT",
                "latitude": lat, "longitude": lng,
                "geo": {"type": "Point", "coordinates": [lng, lat]},
                "cover_image_url": img, "price_override": float(price),
                "capacity": 12, "reserved_seats": 0,
                "venue_name": name, "created_at": now_iso, SAMPLE_FLAG: True,
            })

    if orgs:
        await db.organizations.insert_many(orgs)
        await db.stores.insert_many(stores)
        await db.products.insert_many(products)
        await db.event_occurrences.insert_many(occs)

    return {"wiped": wiped, "operators": len(orgs),
            "retreats": len(occs)}


async def _main():
    res = await seed_samples()
    print(f"Sample rimossi prima: {sum(res['wiped'].values())}")
    print(f"Operatori campione creati: {res['operators']}")
    print(f"Ritiri campione creati:    {res['retreats']}")
    print("Ricorda: appaiono solo con PRELAUNCH_MODE attivo.")


if __name__ == "__main__":
    asyncio.run(_main())
