"""BS (2/10/2026) — la segmentazione solida in Brevo.

Tre gesti, tutti SOLO sull'API contatti (mai una campagna, mai un
transazionale: questo script non puo' mandare email a nessuno):

  --attributi   crea in Brevo gli attributi del registro ATTRIBUTI_BREVO
                che ancora mancano (idempotente: quelli che esistono si
                saltano, un 409 vale come «gia' c'e'»)
  --backfill    riallinea OGNI iscritto del nostro DB (la fonte di verita')
                sul contatto Brevo: stessi attributi della sync di sempre,
                nessuna lista (BREVO_LIST_ID resta la regola della sync),
                disiscritti in blacklist come oggi
  --verifica    rilegge i contatti da Brevo e conta cosa hanno addosso
                (inviabili, con le vie, con l'eta', con la fascia...)

Uso (dentro il container backend, che parla IPv4: la chiave Brevo e'
legata agli IP autorizzati e da IPv6 risponde 401):
  python scripts/brevo_segmentazione.py --attributi
  python scripts/brevo_segmentazione.py --backfill
  python scripts/brevo_segmentazione.py --verifica
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "https://api.brevo.com/v3"


def _chiave() -> str:
    k = os.environ.get("BREVO_API_KEY", "").strip()
    if not k:
        sys.exit("BREVO_API_KEY mancante: niente da fare.")
    return k


def _headers() -> dict:
    return {"api-key": _chiave(), "Content-Type": "application/json", "Accept": "application/json"}


def attributi() -> int:
    import requests
    from services.subscriber_brevo_sync import ATTRIBUTI_BREVO
    from services.operatori_brevo_sync import ATTRIBUTI_BREVO_OP     # OP2: anche le facce operatore
    r = requests.get(f"{BASE}/contacts/attributes", headers=_headers(), timeout=15)
    r.raise_for_status()
    esistenti = {a["name"].upper(): a for a in r.json().get("attributes", [])}
    creati, saltati, falliti = [], [], []
    for nome, tipo in {**ATTRIBUTI_BREVO, **ATTRIBUTI_BREVO_OP}.items():
        if nome.upper() in esistenti:
            saltati.append(nome)
            continue
        resp = requests.post(f"{BASE}/contacts/attributes/normal/{nome}",
                             json={"type": tipo}, headers=_headers(), timeout=15)
        if resp.status_code in (200, 201, 204, 409):
            creati.append(f"{nome}:{tipo}")
        else:
            falliti.append(f"{nome} → {resp.status_code} {resp.text[:120]}")
        time.sleep(0.2)
    print(f"attributi: creati {len(creati)} {creati}")
    print(f"           gia' presenti {len(saltati)} {saltati}")
    if falliti:
        print(f"           FALLITI {falliti}")
    return 1 if falliti else 0


async def _backfill() -> int:
    from database import db
    from services.subscriber_brevo_sync import _PROIEZIONE_SYNC, _attributes, _push_to_brevo
    ok = ko = 0
    inviabili = 0
    from services.operatori_brevo_sync import tipo_contatto
    async for d in db.aurya_subscribers.find({}, {**_PROIEZIONE_SYNC, "email": 1}).sort("created_at", 1):
        attr = _attributes(d, await tipo_contatto(d["email"]))
        inviabili += 1 if attr.get("AURYA_INVIABILE") else 0
        riuscito = await asyncio.to_thread(_push_to_brevo, d["email"], attr, d.get("status") == "unsubscribed")
        ok += 1 if riuscito else 0
        ko += 0 if riuscito else 1
        await asyncio.sleep(0.15)          # 56 contatti ≈ 10 s; Brevo non si lamenta
    print(f"backfill: {ok} contatti allineati, {ko} falliti, {inviabili} inviabili (confermati col consenso)")
    return 1 if ko else 0


async def _operatori() -> int:
    """OP2 — ogni operatore sul suo contatto Brevo (stesso contatto di un
    eventuale iscritto al Cerchio: Brevo identifica per email)."""
    from services.operatori_brevo_sync import sync_tutti
    e = await sync_tutti()
    print(f"operatori: {e['allineati']} allineati, {e['falliti']} falliti, {e['saltati']} saltati "
          f"(campioni o senza titolare), {e['comunicazioni']} con le comunicazioni accese")
    return 1 if e["falliti"] else 0


def verifica() -> int:
    import requests
    from services.subscriber_brevo_sync import ATTRIBUTI_BREVO
    contatti, offset = [], 0
    while True:
        r = requests.get(f"{BASE}/contacts", params={"limit": 50, "offset": offset},
                         headers=_headers(), timeout=20)
        r.raise_for_status()
        blocco = r.json().get("contacts", [])
        contatti += blocco
        if len(blocco) < 50:
            break
        offset += 50
    con_status = [c for c in contatti if (c.get("attributes") or {}).get("AURYA_STATUS")]
    inviabili = [c for c in con_status if (c["attributes"].get("AURYA_INVIABILE") is True)]
    con_vie = [c for c in con_status if c["attributes"].get("AURYA_INTERESTS")]
    con_eta = [c for c in con_status if c["attributes"].get("AURYA_ETA")]
    con_canale = [c for c in con_status if c["attributes"].get("AURYA_CANALE")]
    black = [c for c in contatti if c.get("emailBlacklisted")]
    print(f"verifica: {len(contatti)} contatti in Brevo, {len(con_status)} con AURYA_STATUS, "
          f"{len(inviabili)} inviabili, {len(con_vie)} con le vie, {len(con_canale)} col canale, "
          f"{len(con_eta)} con l'eta', {len(black)} in blacklist")
    # OP2 — le facce
    tipi = {}
    for c in contatti:
        t = (c.get("attributes") or {}).get("AURYA_TIPO") or "(senza)"
        tipi[t] = tipi.get(t, 0) + 1
    op = [c for c in contatti if (c.get("attributes") or {}).get("AURYA_OP") is True]
    op_com = [c for c in op if c["attributes"].get("AURYA_OP_COMUNICAZIONI") is True]
    op_online = [c for c in op if c["attributes"].get("AURYA_OP_STATO") == "online"]
    print(f"          tipi: {tipi} · operatori {len(op)}, con comunicazioni {len(op_com)}, con pagina online {len(op_online)}")
    mancanti = [k for k in ATTRIBUTI_BREVO if con_status and not any(k in (c.get("attributes") or {}) for c in con_status)]
    if mancanti:
        print(f"          attributi mai valorizzati su nessun contatto: {mancanti}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--attributi", action="store_true")
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--operatori", action="store_true")
    p.add_argument("--verifica", action="store_true")
    a = p.parse_args()
    if not (a.attributi or a.backfill or a.operatori or a.verifica):
        p.print_help()
        return 2
    esito = 0
    if a.attributi:
        esito |= attributi()

    # UN solo ciclo asyncio per i gesti sul DB: il client Motor resta
    # legato al primo loop e un secondo ciclo lo trova chiuso
    # («Event loop is closed», visto in prod il 2/10 sera)
    async def _gesti_db() -> int:
        e = 0
        if a.backfill:
            e |= await _backfill()
        if a.operatori:
            e |= await _operatori()
        return e
    if a.backfill or a.operatori:
        esito |= asyncio.run(_gesti_db())
    if a.verifica:
        esito |= verifica()
    return esito


if __name__ == "__main__":
    sys.exit(main())
