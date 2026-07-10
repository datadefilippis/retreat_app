"""Popola la vetrina di pre-lancio con operatori e ritiri CAMPIONE.

Tutti i documenti sono marchiati is_sample=True → appaiono solo con
PRELAUNCH_MODE attivo (sfocati, non prenotabili) e si cancellano in un
colpo con scripts.wipe_prelaunch_samples. I dati veri non vengono toccati.

Idempotente: prima cancella i sample esistenti, poi reinserisce.

Uso:
    JWT_SECRET_KEY=... venv/bin/python -m scripts.seed_prelaunch_samples
"""

import asyncio
import json
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
# ritiri: [(titolo, categoria, prezzo, "YYYY-MM-DD", durata, foto, desc_it, translations)]
#
# PL14 — i titoli sono EVOCATIVI e descrittivi (comunicano il concept al
# visitatore) ma non identitari: il nome dell'organizzatore resta redatto.
# Tutte le date nel 2027, distribuite lungo l'anno.
# PL18 — OGNI ritiro campione ha name+description in en/de/fr: il filtro
# lingue del marketplace (is_available_in) nasconde i prodotti senza
# traduzione, e la vetrina di pre-lancio deve esistere in TUTTE le lingue.
_OPERATORS = [
    ("Masseria degli Ulivi", "masseria-ulivi-sample", "Ostuni", "Puglia",
     40.7295, 17.5772, "Yoga e silenzio tra gli ulivi secolari",
     "Un casale di pietra nella campagna di Ostuni: pratica al mattino, "
     "cucina del territorio, e il silenzio vero della Valle d'Itria.",
     True, (4.9, 23),
     [("Ritorna a respirare: yoga tra gli ulivi secolari della Valle d'Itria",
       "yoga", 690, "2027-05-14", 4, "r01",
       "Quattro giorni di pratica lenta, cucina del territorio e silenzio vero nella campagna di Ostuni.",
       json.loads('{"en": {"name": "Breathe again: yoga among the ancient olive trees of Valle d\u2019Itria", "description": "Four days of slow practice, local food and true silence in the Ostuni countryside."}, "de": {"name": "Wieder atmen: Yoga zwischen jahrhundertealten Olivenb\u00e4umen im Itria-Tal", "description": "Vier Tage sanfte Praxis, regionale K\u00fcche und echte Stille auf dem Land bei Ostuni."}, "fr": {"name": "Respire \u00e0 nouveau : yoga parmi les oliviers s\u00e9culaires de la Vall\u00e9e d\u2019Itria", "description": "Quatre jours de pratique douce, cuisine locale et vrai silence dans la campagne d\u2019Ostuni."}}')),
      ("Il tramonto in silenzio: due giorni per svuotare la mente",
       "meditazione", 320, "2027-06-18", 2, "r02",
       "Un weekend di meditazione al tramonto per lasciare andare il rumore e ritrovare spazio.",
       json.loads('{"en": {"name": "Sunset in silence: two days to empty the mind", "description": "A weekend of sunset meditation to let go of the noise and find space again."}, "de": {"name": "Sonnenuntergang in Stille: zwei Tage, um den Kopf freizubekommen", "description": "Ein Wochenende Meditation bei Sonnenuntergang, um den L\u00e4rm loszulassen."}, "fr": {"name": "Coucher de soleil en silence : deux jours pour vider l\u2019esprit", "description": "Un week-end de m\u00e9ditation au coucher du soleil pour l\u00e2cher le bruit et retrouver de l\u2019espace."}}'))]),
    ("Rifugio del Bosco", "rifugio-bosco-sample", "Bolzano", "Trentino-Alto Adige",
     46.4983, 11.3548, "Cammini e respiro tra le Dolomiti",
     "Sulle porte delle Dolomiti: camminate consapevoli, bagni di foresta "
     "e breathwork con vista sulle vette.",
     True, (5.0, 17),
     [("A passo lento tra le Dolomiti: cinque giorni di cammino e respiro",
       "cammini", 850, "2027-07-05", 5, "r03",
       "Camminate consapevoli, bagni di foresta e respiro con vista sulle vette.",
       json.loads('{"en": {"name": "Slow steps in the Dolomites: five days of mindful walking and breath", "description": "Mindful hikes, forest bathing and breathwork with a view of the peaks."}, "de": {"name": "Langsamen Schrittes durch die Dolomiten: f\u00fcnf Tage Gehen und Atmen", "description": "Achtsame Wanderungen, Waldbaden und Atemarbeit mit Blick auf die Gipfel."}, "fr": {"name": "\u00c0 pas lents dans les Dolomites : cinq jours de marche et de respiration", "description": "Marches conscientes, bains de for\u00eat et travail du souffle face aux sommets."}}')),
      ("Il respiro della foresta: breathwork e bagni di bosco in quota",
       "breathwork", 410, "2027-08-27", 3, "r04",
       "Tre giorni di respiro tra gli abeti, alle porte delle Dolomiti.",
       json.loads('{"en": {"name": "The forest breathes: breathwork and forest bathing in the mountains", "description": "Three days of breathwork among the firs, on the doorstep of the Dolomites."}, "de": {"name": "Der Atem des Waldes: Breathwork und Waldbaden in den Bergen", "description": "Drei Tage Atemarbeit zwischen den Tannen, am Tor zu den Dolomiten."}, "fr": {"name": "Le souffle de la for\u00eat : breathwork et bains de for\u00eat en altitude", "description": "Trois jours de respiration parmi les sapins, aux portes des Dolomites."}}'))]),
    ("Casa Serena Cilento", "casa-serena-sample", "Pollica", "Campania",
     40.1889, 15.0912, "Detox e mare nel cuore del Cilento",
     "Tra il blu del Cilento e gli orti biologici: detox dolce, yoga sulla "
     "terrazza e cene a km zero.",
     False, (4.8, 31),
     [("Ritrova leggerezza: detox dolce e yoga davanti al mare del Cilento",
       "detox", 740, "2027-06-07", 5, "r05",
       "Cinque giorni di detox dolce, yoga in terrazza e cene a km zero.",
       json.loads('{"en": {"name": "Find lightness again: gentle detox and yoga by the Cilento sea", "description": "Five days of gentle detox, terrace yoga and zero-kilometre dinners."}, "de": {"name": "Wieder leicht werden: sanftes Detox und Yoga am Meer des Cilento", "description": "F\u00fcnf Tage sanftes Detox, Yoga auf der Terrasse und K\u00fcche aus dem eigenen Garten."}, "fr": {"name": "Retrouver la l\u00e9g\u00e8ret\u00e9 : d\u00e9tox douce et yoga face \u00e0 la mer du Cilento", "description": "Cinq jours de d\u00e9tox douce, yoga en terrasse et d\u00eeners du potager."}}'))]),
    ("Borgo del Suono", "borgo-suono-sample", "Todi", "Umbria",
     42.7817, 12.4126, "Bagni di gong e meditazione nel cuore verde",
     "Un borgo umbro dove il suono guida la pratica: campane tibetane, gong "
     "e meditazione nel verde più profondo d'Italia.",
     False, (4.7, 12),
     [("Immersi nel suono: gong e campane tibetane nel cuore verde d'Italia",
       "suono", 280, "2027-04-16", 2, "r06",
       "Un weekend dove il suono guida la pratica, nel verde profondo dell'Umbria.",
       json.loads('{"en": {"name": "Immersed in sound: gongs and Tibetan bowls in Italy\u2019s green heart", "description": "A weekend where sound guides the practice, in the deep green of Umbria."}, "de": {"name": "Eintauchen in den Klang: Gongs und Klangschalen im gr\u00fcnen Herzen Italiens", "description": "Ein Wochenende, in dem der Klang die Praxis f\u00fchrt, im tiefen Gr\u00fcn Umbriens."}, "fr": {"name": "Immerg\u00e9s dans le son : gongs et bols tib\u00e9tains au c\u0153ur vert de l\u2019Italie", "description": "Un week-end o\u00f9 le son guide la pratique, dans le vert profond de l\u2019Ombrie."}}')),
      ("Quattro giorni di silenzio per sentire di nuovo te stesso",
       "meditazione", 560, "2027-09-10", 4, "r07",
       "Un ritiro del silenzio in un borgo umbro: meditazione, quiete, presenza.",
       json.loads('{"en": {"name": "Four days of silence to hear yourself again", "description": "A silent retreat in an Umbrian village: meditation, stillness, presence."}, "de": {"name": "Vier Tage Stille, um dich selbst wieder zu h\u00f6ren", "description": "Ein Schweige-Retreat in einem umbrischen Dorf: Meditation, Ruhe, Pr\u00e4senz."}, "fr": {"name": "Quatre jours de silence pour t\u2019entendre \u00e0 nouveau", "description": "Une retraite silencieuse dans un bourg d\u2019Ombrie : m\u00e9ditation, calme, pr\u00e9sence."}}'))]),
    ("Cascina Luna", "cascina-luna-sample", "Greve in Chianti", "Toscana",
     43.5836, 11.3157, "Cerchi femminili tra le vigne del Chianti",
     "Una cascina tra le vigne: cerchi femminili, yoga e vino naturale al "
     "tramonto, nel paesaggio più iconico della Toscana.",
     True, (4.9, 26),
     [("Cerchio di donne tra le vigne: tre giorni per ritrovarsi nel Chianti",
       "femminile", 620, "2027-05-28", 3, "r08",
       "Cerchi femminili, yoga dolce e luce dorata sulle colline toscane.",
       json.loads('{"en": {"name": "A women\u2019s circle among the vineyards: three days to reconnect in Chianti", "description": "Women\u2019s circles, gentle yoga and golden light over the Tuscan hills."}, "de": {"name": "Frauenkreis zwischen den Weinbergen: drei Tage Ankommen im Chianti", "description": "Frauenkreise, sanftes Yoga und goldenes Licht \u00fcber den H\u00fcgeln der Toskana."}, "fr": {"name": "Cercle de femmes parmi les vignes : trois jours pour se retrouver dans le Chianti", "description": "Cercles de femmes, yoga doux et lumi\u00e8re dor\u00e9e sur les collines toscanes."}}')),
      ("Saluto al sole tra i filari: yoga e vino naturale in Toscana",
       "yoga", 390, "2027-09-24", 2, "r09",
       "Un weekend di pratica all'alba e vino naturale al tramonto, nel Chianti.",
       json.loads('{"en": {"name": "Sun salutations among the vines: yoga and natural wine in Tuscany", "description": "A weekend of practice at dawn and natural wine at sunset, in the Chianti."}, "de": {"name": "Sonnengru\u00df zwischen den Rebzeilen: Yoga und Naturwein in der Toskana", "description": "Ein Wochenende: Praxis im Morgenlicht und Naturwein bei Sonnenuntergang, mitten im Chianti."}, "fr": {"name": "Salutation au soleil entre les vignes : yoga et vin nature en Toscane", "description": "Un week-end de pratique \u00e0 l\u2019aube et de vin nature au couchant, en plein Chianti."}}'))]),
    ("Eremo del Lago", "eremo-lago-sample", "Bracciano", "Lazio",
     42.1030, 12.1774, "Massaggio sonoro e riposo sulle rive del lago",
     "Sulle rive del lago di Bracciano, a un'ora da Roma: massaggio sonoro, "
     "meditazione e lunghe passeggiate sull'acqua.",
     False, (4.6, 9),
     [("Lascia andare: massaggio sonoro e riposo in riva al lago",
       "massaggio", 340, "2027-04-30", 2, "r10",
       "Massaggio sonoro, meditazione e lunghe passeggiate sull'acqua, a un'ora da Roma.",
       json.loads('{"en": {"name": "Let go: sound massage and rest on the lakeshore", "description": "Sound massage, meditation and long walks by the water, an hour from Rome."}, "de": {"name": "Loslassen: Klangmassage und Ruhe am Seeufer", "description": "Klangmassage, Meditation und lange Spazierg\u00e4nge am Wasser, eine Stunde von Rom."}, "fr": {"name": "L\u00e2cher prise : massage sonore et repos au bord du lac", "description": "Massage sonore, m\u00e9ditation et longues balades au bord de l\u2019eau, \u00e0 une heure de Rome."}}'))]),
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

        for (title, category, price, date_str, duration, photo,
             desc_it, translations) in retreats:
            prod_id = str(uuid.uuid4())
            occ_id = str(uuid.uuid4())
            occ_slug = f"{slug}-{category}-{occ_id[:6]}"
            # PL14 — date esplicite nel 2027 (inizio ore 17, fine ore 12)
            start = datetime.fromisoformat(f"{date_str}T17:00:00+00:00")
            end = (start + timedelta(days=duration)).replace(hour=12)
            img = _img(photo)
            products.append({
                "id": prod_id, "organization_id": org_id, "name": title,
                # PL18 — descrizione + traduzioni en/de/fr: il campione
                # esiste (tradotto) in ogni lingua del marketplace
                "description": desc_it, "translations": translations,
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
