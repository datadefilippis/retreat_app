"""ASCOLTI — l'abitudine di chi ascolta e la regia (lotto CS, 8/10/2026).

docs/PIANO_CASA_CONSIGLI_2026-10-08.md. Gli eventi stanno in `sound_ascolti`
(evento: avvio · q25 · q50 · q75 · fine; secondo; at; slug; account_id).
Qui si RIASSUMONO, non si scrive nulla: `abitudine(account_id)` per il
motore dei consigli (CS2); le viste della regia (CS4) sono sotto.
Le ore si leggono nel fuso di Roma: il pubblico e' italiano e la fascia
(mattina · pausa · sera · notte) e' quella che la persona vive.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from database import db

ROMA = ZoneInfo("Europe/Rome")
GIORNI_ABITUDINE = 90
GIORNI_STANCHEZZA = 7


def fascia_ora(h: int) -> str:
    if 5 <= h < 11:
        return "mattina"
    if 11 <= h < 17:
        return "pausa"
    if 17 <= h < 22:
        return "sera"
    return "notte"


def _locale(at):
    if at is None:
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return at.astimezone(ROMA)


async def abitudine(account_id: str) -> dict:
    """Quello che il motore dei consigli chiede della persona, dagli eventi:
    fascia abituale, durata media di un ascolto, completamenti recenti,
    ascoltati oggi/ieri, ultimo ascolto per titolo. Mai bloccante."""
    if not account_id:
        return {}
    da = datetime.now(timezone.utc) - timedelta(days=GIORNI_ABITUDINE)
    cur = db.sound_ascolti.find(
        {"account_id": account_id, "at": {"$gte": da}},
        {"_id": 0, "evento": 1, "secondo": 1, "at": 1, "slug": 1},
    ).sort("at", 1)
    fasce = Counter()
    sessioni = defaultdict(int)        # (slug, giorno) -> secondo massimo
    completati = Counter()
    ascoltati_oggi = set()
    ultimo = {}
    adesso = datetime.now(timezone.utc)
    soglia_oggi = adesso - timedelta(hours=36)
    soglia_7 = adesso - timedelta(days=GIORNI_STANCHEZZA)
    async for e in cur:
        at = e.get("at")
        if at is None:
            continue
        at_utc = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        loc = _locale(at)
        slug = e.get("slug") or ""
        ev = e.get("evento")
        if ev == "avvio":
            fasce[fascia_ora(loc.hour)] += 1
            if at_utc >= soglia_oggi:
                ascoltati_oggi.add(slug)
            ultimo[slug] = int(at_utc.timestamp() * 1000)
        k = (slug, loc.date().isoformat())
        sessioni[k] = max(sessioni[k], int(e.get("secondo") or 0))
        if ev == "fine" and at_utc >= soglia_7:
            completati[slug] += 1
    fascia = fasce.most_common(1)[0][0] if sum(fasce.values()) >= 3 else None
    durate = [v for v in sessioni.values() if v > 0]
    return {
        "fascia": fascia,
        "durata_media_sec": int(sum(durate) / len(durate)) if durate else 0,
        "completati": dict(completati),
        "ascoltati_oggi": sorted(ascoltati_oggi),
        "ultimo_ascolto": ultimo,
        "ascolti_90g": sum(fasce.values()),
    }


# ═══════════════════════════════════════════════════════════════════════
# CS4 — LA REGIA DEGLI ASCOLTI (system admin → Sound → Ascolti)
# ═══════════════════════════════════════════════════════════════════════
PERIODI = {"7": 7, "30": 30, "90": 90, "tutto": None}
QUARTILI = {"avvio": 0, "q25": 25, "q50": 50, "q75": 75, "fine": 100}

# lo score «seguito» (0–100): una somma leggibile, non un numero magico
PESI_SEGUITO = {"frequenza": 30, "costanza": 20, "profondita": 25, "ampiezza": 15, "affetto": 10}
TETTI_SEGUITO = {"giorni_attivi": 12, "settimane": 8, "preferite": 5}


def _da_periodo(periodo: str):
    g = PERIODI.get(str(periodo), 30)
    return (datetime.now(timezone.utc) - timedelta(days=g)) if g else None


async def _eventi(filtro: dict, da) -> list:
    q = dict(filtro)
    if da is not None:
        q["at"] = {"$gte": da}
    cur = db.sound_ascolti.find(q, {"_id": 0}).sort("at", 1)
    out = []
    async for e in cur:
        at = e.get("at")
        if at is None:
            continue
        e["at"] = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        out.append(e)
    return out


def _sessioni(eventi: list) -> list:
    """Una SESSIONE = un avvio; i quartili e la fine che seguono (stessa
    persona, stesso titolo, stesso giorno locale) le appartengono."""
    per = {}
    ordine = []
    for e in eventi:
        loc = _locale(e["at"])
        k = (e.get("account_id") or "anon", e.get("slug") or "", loc.date().isoformat())
        if k not in per:
            per[k] = {"account_id": e.get("account_id"), "slug": e.get("slug") or "", "track_id": e.get("track_id"),
                      "giorno": loc.date().isoformat(), "at": e["at"], "fascia": fascia_ora(loc.hour),
                      "provenienza": e.get("provenienza") or "altro", "playlist": e.get("playlist"),
                      "avvii": 0, "secondo": 0, "quartile": 0, "fine": False}
            ordine.append(k)
        s = per[k]
        ev = e.get("evento")
        if ev == "avvio":
            s["avvii"] += 1
        s["secondo"] = max(s["secondo"], int(e.get("secondo") or 0))
        s["quartile"] = max(s["quartile"], QUARTILI.get(ev, 0))
        if ev == "fine":
            s["fine"] = True
    return [per[k] for k in ordine if per[k]["avvii"] > 0 or per[k]["quartile"] > 0]


async def _titoli() -> dict:
    cur = db.frequency_tracks.find({}, {"_id": 0, "slug": 1, "title": 1, "status": 1, "visibility": 1, "categoria": 1, "score.duration_sec": 1})
    out = {}
    async for t in cur:
        out[t.get("slug")] = t
    return out


async def _conti_preferiti() -> dict:
    out = Counter()
    async for f in db.frequency_favorites.find({}, {"_id": 0, "slug": 1}):
        out[f.get("slug")] += 1
    return out


async def panoramica(periodo: str = "30") -> dict:
    da = _da_periodo(periodo)
    sess = _sessioni(await _eventi({}, da))
    con_account = [s for s in sess if s["account_id"]]
    persone = {s["account_id"] for s in con_account}
    minuti = sum(s["secondo"] for s in sess) / 60
    completate = sum(1 for s in sess if s["fine"])
    per_giorno = Counter(s["giorno"] for s in sess)
    per_fascia = Counter(s["fascia"] for s in sess)
    # nuovi ascoltatori: il PRIMO avvio di sempre cade nel periodo
    nuovi = 0
    if da is not None and persone:
        primi = db.sound_ascolti.aggregate([
            {"$match": {"account_id": {"$in": list(persone)}, "evento": "avvio"}},
            {"$group": {"_id": "$account_id", "primo": {"$min": "$at"}}},
        ])
        async for p in primi:
            primo = p["primo"] if p["primo"].tzinfo else p["primo"].replace(tzinfo=timezone.utc)
            if primo >= da:
                nuovi += 1
    else:
        nuovi = len(persone)
    pref_q = {} if da is None else {"created_at": {"$gte": da}}
    preferiti = await db.frequency_favorites.count_documents(pref_q)
    return {
        "periodo": periodo, "ascolti": len(sess), "ascolti_anonimi": len(sess) - len(con_account),
        "persone": len(persone), "nuovi_ascoltatori": nuovi, "minuti": round(minuti, 1),
        "completamento": round(completate / len(sess), 3) if sess else 0.0,
        "preferiti_aggiunti": preferiti,
        "per_giorno": [{"giorno": g, "ascolti": n} for g, n in sorted(per_giorno.items())],
        "per_fascia": {f: per_fascia.get(f, 0) for f in ("mattina", "pausa", "sera", "notte")},
    }


def _riassunto_titolo(slug: str, sess: list, titoli: dict, preferiti: Counter) -> dict:
    t = titoli.get(slug) or {}
    persone = {s["account_id"] for s in sess if s["account_id"]}
    fine = sum(1 for s in sess if s["fine"])
    quart = [s["quartile"] for s in sess]
    fasce = Counter(s["fascia"] for s in sess)
    prov = Counter(s["provenienza"] for s in sess)
    return {
        "slug": slug, "titolo": t.get("title") or slug, "stato": t.get("status"), "visibilita": t.get("visibility"),
        "categoria": t.get("categoria"), "durata_sec": (t.get("score") or {}).get("duration_sec"),
        "ascolti": len(sess), "persone": len(persone), "anonimi": sum(1 for s in sess if not s["account_id"]),
        "minuti": round(sum(s["secondo"] for s in sess) / 60, 1),
        "completamento": round(fine / len(sess), 3) if sess else 0.0,
        "abbandono_medio": round(sum(quart) / len(quart)) if quart else 0,   # il quartile medio raggiunto (0–100)
        "preferiti": preferiti.get(slug, 0),
        "momento_punta": fasce.most_common(1)[0][0] if fasce else None,
        "provenienze": dict(prov),
    }


async def per_meditazione(periodo: str = "30") -> list:
    da = _da_periodo(periodo)
    sess = _sessioni(await _eventi({}, da))
    titoli = await _titoli()
    preferiti = await _conti_preferiti()
    per = defaultdict(list)
    for s in sess:
        per[s["slug"]].append(s)
    # anche i titoli pubblicati senza ascolti nel periodo: la regia vede il silenzio
    for slug, t in titoli.items():
        if t.get("status") == "published" and slug not in per:
            per[slug] = []
    out = [_riassunto_titolo(slug, ss, titoli, preferiti) for slug, ss in per.items()]
    out.sort(key=lambda r: (-r["ascolti"], r["titolo"]))
    return out


async def dettaglio_meditazione(slug: str, periodo: str = "30") -> dict:
    da = _da_periodo(periodo)
    sess = _sessioni(await _eventi({"slug": slug}, da))
    titoli = await _titoli()
    preferiti = await _conti_preferiti()
    base = _riassunto_titolo(slug, sess, titoli, preferiti)
    n = len(sess) or 1
    base["curva"] = {k: round(sum(1 for s in sess if s["quartile"] >= v) / n, 3) for k, v in (("q25", 25), ("q50", 50), ("q75", 75), ("fine", 100))}
    per_persona = defaultdict(list)
    for s in sess:
        if s["account_id"]:
            per_persona[s["account_id"]].append(s)
    conti = await _anagrafiche(list(per_persona))
    base["persone_elenco"] = sorted([{
        "account_id": aid, **conti.get(aid, {}), "ascolti": len(ss), "minuti": round(sum(s["secondo"] for s in ss) / 60, 1),
        "completati": sum(1 for s in ss if s["fine"]), "ultimo": max(s["at"] for s in ss).isoformat(),
    } for aid, ss in per_persona.items()], key=lambda r: -r["ascolti"])
    return base


async def _anagrafiche(ids: list) -> dict:
    out = {}
    if not ids:
        return out
    async for a in db.platform_accounts.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1, "created_at": 1}):
        out[a["id"]] = {"nome": a.get("name") or "", "email": a.get("email") or "", "iscritto_il": a.get("created_at")}
    return out


def score_seguito(stat: dict, titoli_catalogo: int) -> dict:
    """stat: giorni_attivi_30, settimane_consecutive, completati, ascolti, titoli_diversi, preferite."""
    frequenza = min(1.0, (stat.get("giorni_attivi_30") or 0) / TETTI_SEGUITO["giorni_attivi"])
    costanza = min(1.0, (stat.get("settimane_consecutive") or 0) / TETTI_SEGUITO["settimane"])
    profondita = (stat.get("completati") or 0) / stat["ascolti"] if stat.get("ascolti") else 0.0
    ampiezza = min(1.0, (stat.get("titoli_diversi") or 0) / titoli_catalogo) if titoli_catalogo else 0.0
    affetto = min(1.0, (stat.get("preferite") or 0) / TETTI_SEGUITO["preferite"])
    parti = {"frequenza": frequenza, "costanza": costanza, "profondita": profondita, "ampiezza": ampiezza, "affetto": affetto}
    score = sum(PESI_SEGUITO[k] * v for k, v in parti.items())
    return {"score": round(score), "parti": {k: round(v, 2) for k, v in parti.items()}}


def _settimane_consecutive(giorni: set, oggi) -> int:
    """quante settimane di fila (da questa a ritroso) hanno almeno un ascolto"""
    if not giorni:
        return 0
    settimane = {datetime.fromisoformat(g).isocalendar()[:2] for g in giorni}
    n = 0
    cur = oggi
    while (cur.isocalendar()[0], cur.isocalendar()[1]) in settimane:
        n += 1
        cur = cur - timedelta(days=7)
    return n


async def per_persona(periodo: str = "30") -> list:
    da = _da_periodo(periodo)
    sess = [s for s in _sessioni(await _eventi({"account_id": {"$ne": None}}, da)) if s["account_id"]]
    per = defaultdict(list)
    for s in sess:
        per[s["account_id"]].append(s)
    conti = await _anagrafiche(list(per))
    titoli = await _titoli()
    pubblicati = sum(1 for t in titoli.values() if t.get("status") == "published") or 1
    pref = Counter()
    async for f in db.frequency_favorites.find({"platform_account_id": {"$in": list(per)}}, {"_id": 0, "platform_account_id": 1}):
        pref[f["platform_account_id"]] += 1
    oggi = datetime.now(ROMA).date()
    soglia30 = oggi - timedelta(days=30)
    out = []
    for aid, ss in per.items():
        giorni = {s["giorno"] for s in ss}
        giorni30 = {g for g in giorni if datetime.fromisoformat(g).date() >= soglia30}
        fasce = Counter(s["fascia"] for s in ss)
        stat = {"giorni_attivi_30": len(giorni30), "settimane_consecutive": _settimane_consecutive(giorni, oggi),
                "completati": sum(1 for s in ss if s["fine"]), "ascolti": len(ss),
                "titoli_diversi": len({s["slug"] for s in ss}), "preferite": pref.get(aid, 0)}
        out.append({
            "account_id": aid, **conti.get(aid, {"nome": "", "email": "", "iscritto_il": None}),
            "primo_ascolto": min(s["at"] for s in ss).isoformat(), "ultimo_ascolto": max(s["at"] for s in ss).isoformat(),
            "ascolti": len(ss), "minuti": round(sum(s["secondo"] for s in ss) / 60, 1),
            "completati": stat["completati"], "titoli_diversi": stat["titoli_diversi"], "preferite": stat["preferite"],
            "fascia_abituale": fasce.most_common(1)[0][0] if fasce else None,
            "giorni_attivi_30": stat["giorni_attivi_30"], "settimane_consecutive": stat["settimane_consecutive"],
            **score_seguito(stat, pubblicati),
        })
    out.sort(key=lambda r: (-r["score"], -r["ascolti"]))
    return out


async def dettaglio_persona(account_id: str) -> dict:
    sess = _sessioni(await _eventi({"account_id": account_id}, None))
    titoli = await _titoli()
    conti = await _anagrafiche([account_id])
    acc = await db.platform_accounts.find_one({"id": account_id}, {"_id": 0, "sound_riprendi": 1, "sound_recenti": 1})
    pref = [f["slug"] async for f in db.frequency_favorites.find({"platform_account_id": account_id}, {"_id": 0, "slug": 1})]
    linea = sorted([{
        "at": s["at"].isoformat(), "slug": s["slug"], "titolo": (titoli.get(s["slug"]) or {}).get("title") or s["slug"],
        "provenienza": s["provenienza"], "playlist": s["playlist"], "minuti": round(s["secondo"] / 60, 1),
        "quartile": s["quartile"], "completata": s["fine"], "fascia": s["fascia"],
    } for s in sess], key=lambda r: r["at"], reverse=True)
    persone = await per_persona("tutto")
    mio = next((p for p in persone if p["account_id"] == account_id), None)
    return {
        "account_id": account_id, **conti.get(account_id, {"nome": "", "email": "", "iscritto_il": None}),
        "riepilogo": mio, "linea": linea,
        "preferite": [{"slug": s, "titolo": (titoli.get(s) or {}).get("title") or s} for s in pref],
        "riprendi": (acc or {}).get("sound_riprendi"), "recenti": (acc or {}).get("sound_recenti") or [],
    }


# ═══ CS5 — la conservazione: 24 mesi, poi via ═══
CONSERVAZIONE_GIORNI = 730


async def conserva() -> int:
    """Cancella gli eventi di ascolto piu' vecchi di 24 mesi. Idempotente."""
    soglia = datetime.now(timezone.utc) - timedelta(days=CONSERVAZIONE_GIORNI)
    r = await db.sound_ascolti.delete_many({"at": {"$lt": soglia}})
    return r.deleted_count
