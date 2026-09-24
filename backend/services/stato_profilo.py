"""SA1 (24/9/2026) — lo stato del profilo di un operatore: UNA verita'.

Quattro stati, derivati dagli stessi fatti che `services.sequenze.
stato_operatore` calcola per le email di accompagnamento (non si
ricalcolano qui: si riusano), cosi' la lista admin dice cio' che
l'operatore vede nella sua striscia-guida.

  account = nessuna bio (si e' fermato alla registrazione)
  bozza   = bio scritta ma pagina non raggiungibile (nessuno slug)
  pagina  = pagina raggiungibile (slug + bio), nessun servizio pubblicato
  online  = pagina + almeno un servizio pubblicato
"""
from typing import Any, Dict, List

STATI = ("account", "bozza", "pagina", "online")


def classifica(bio_len: int, pagina: bool, n_servizi: int) -> str:
    """La regola pura, senza database: la usa `stato_profilo` e la
    possono usare i test (e i conteggi) senza inventarne una seconda."""
    if bio_len <= 0:
        return "account"
    if not pagina:
        return "bozza"
    return "online" if n_servizi > 0 else "pagina"


async def stato_profilo(org: dict) -> Dict[str, Any]:
    """→ {"stato": account|bozza|pagina|online, "n_servizi": int,
    "slug": str|None, "bio_len": int}. `org` deve avere almeno `id` e
    `public_profile` (la proiezione della regia li porta)."""
    from services.sequenze import stato_operatore
    so = await stato_operatore(org)
    pp = org.get("public_profile") or {}
    bio_len = len((pp.get("bio") or "").strip())
    return {
        "stato": classifica(bio_len, bool(so.get("pagina")), int(so.get("n_servizi") or 0)),
        "n_servizi": int(so.get("n_servizi") or 0),
        "slug": so.get("slug") or None,
        "bio_len": bio_len,
    }


def conteggi(stati: List[Dict[str, Any]]) -> Dict[str, int]:
    """Quanti per stato, sempre con le quattro chiavi (anche a zero)."""
    out = {s: 0 for s in STATI}
    for st in stati:
        k = (st or {}).get("stato")
        if k in out:
            out[k] += 1
    return out
