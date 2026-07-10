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


def _img(seed: str, w: int = 1200, h: int = 800) -> str:
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"


# name, slug, città, regione, lat, lng, tagline, bio, featured, rating(avg,count),
# ritiri: [(titolo, categoria, prezzo, giorni_da_oggi, durata_giorni)]
_OPERATORS = [
    ("Masseria degli Ulivi", "masseria-ulivi-sample", "Ostuni", "Puglia",
     40.7295, 17.5772, "Yoga e silenzio tra gli ulivi secolari",
     "Un casale di pietra nella campagna di Ostuni: pratica al mattino, "
     "cucina del territorio, e il silenzio vero della Valle d'Itria.",
     True, (4.9, 23),
     [("Ritiro Yoga & Respiro tra gli ulivi", "yoga", 690, 34, 4),
      ("Weekend di Meditazione al tramonto", "meditazione", 320, 61, 2)]),
    ("Rifugio del Bosco", "rifugio-bosco-sample", "Bolzano", "Trentino-Alto Adige",
     46.4983, 11.3548, "Cammini e respiro tra le Dolomiti",
     "Sulle porte delle Dolomiti: camminate consapevoli, bagni di foresta "
     "e breathwork con vista sulle vette.",
     True, (5.0, 17),
     [("Cammino consapevole nelle Dolomiti", "cammini", 850, 48, 5),
      ("Breathwork & Foresta", "breathwork", 410, 75, 3)]),
    ("Casa Serena Cilento", "casa-serena-sample", "Pollica", "Campania",
     40.1889, 15.0912, "Detox e mare nel cuore del Cilento",
     "Tra il blu del Cilento e gli orti biologici: detox dolce, yoga sulla "
     "terrazza e cene a km zero.",
     False, (4.8, 31),
     [("Ritiro Detox & Yoga sul mare", "detox", 740, 40, 5)]),
    ("Borgo del Suono", "borgo-suono-sample", "Todi", "Umbria",
     42.7817, 12.4126, "Bagni di gong e meditazione nel cuore verde",
     "Un borgo umbro dove il suono guida la pratica: campane tibetane, gong "
     "e meditazione nel verde più profondo d'Italia.",
     False, (4.7, 12),
     [("Bagno di Suono & Meditazione", "suono", 280, 29, 2),
      ("Ritiro del Silenzio", "meditazione", 560, 68, 4)]),
    ("Cascina Luna", "cascina-luna-sample", "Greve in Chianti", "Toscana",
     43.5836, 11.3157, "Cerchi femminili tra le vigne del Chianti",
     "Una cascina tra le vigne: cerchi femminili, yoga e vino naturale al "
     "tramonto, nel paesaggio più iconico della Toscana.",
     True, (4.9, 26),
     [("Ritiro al Femminile nel Chianti", "femminile", 620, 45, 3),
      ("Yoga & Vino tra le vigne", "yoga", 390, 80, 2)]),
    ("Eremo del Lago", "eremo-lago-sample", "Bracciano", "Lazio",
     42.1030, 12.1774, "Massaggio sonoro e riposo sulle rive del lago",
     "Sulle rive del lago di Bracciano, a un'ora da Roma: massaggio sonoro, "
     "meditazione e lunghe passeggiate sull'acqua.",
     False, (4.6, 9),
     [("Weekend di Riequilibrio sul Lago", "massaggio", 340, 38, 2)]),
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
        cover = _img(f"{slug}-cover")
        logo = _img(f"{slug}-logo", 256, 256)

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
                "photos": [_img(f"{slug}-{i}") for i in range(1, 4)],
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

        for (title, category, price, days, duration) in retreats:
            prod_id = str(uuid.uuid4())
            occ_id = str(uuid.uuid4())
            occ_slug = f"{slug}-{category}-{occ_id[:6]}"
            start = now + timedelta(days=days)
            end = start + timedelta(days=duration)
            img = _img(f"{occ_slug}")
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
