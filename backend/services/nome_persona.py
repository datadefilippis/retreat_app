"""Nome della persona: UNA variabile, due posti (24/9/2026 sera, founder).

Il nome che l'operatore scrive alla registrazione vive sull'account
(`users.name`) ed e' lo stesso che il profilo pubblico mostra come
`public_profile.nome_persona` («Nome · Marchio», regola in
services/nome_pubblico.py). Da qui in poi:

  - chi si registra: i due campi nascono insieme (auth_service);
  - chi cambia il nome nel profilo (operatore o admin): l'account lo
    segue (`allinea_account`, chiamato da profilo_pubblico.dopo_salvataggio);
  - chi si e' registrato PRIMA di oggi: il profilo lo eredita
    dall'account (`riempi_pregresso`, script scripts/riempi_nome_persona.py)
    e, finche' il riempimento non e' passato, l'editor lo mostra comunque
    (`nome_persona_effettivo`, letto dalla GET del profilo).

Il nome dell'account e' quello del PRIMO admin dell'org (per created_at):
e' chi si e' registrato. Tutto best-effort e idempotente: non si
rinomina mai un account che ha gia' quel nome, non si tocca un profilo
che ha gia' un nome.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

NOME_PERSONA_MAX = 80
PARTICELLE = {"di", "de", "del", "della", "da", "dal", "la", "le", "lo", "e", "van", "von"}


def ripulisci(nome: str) -> str:
    """«Paola ARTICO» → «Paola Artico», «Ilaria Barbaccia Barbaccia» →
    «Ilaria Barbaccia», particelle minuscole («de Franchis»), spazi
    ripetuti via. Non inventa nulla: una parola sola resta una parola."""
    parole = [p for p in re.split(r"\s+", (nome or "").strip()) if p]
    out = []
    for p in parole:
        if out and out[-1].casefold() == p.casefold():
            continue
        if p.casefold() in PARTICELLE and out:
            out.append(p.lower())
        else:
            out.append("-".join(x[:1].upper() + x[1:].lower() for x in p.split("-")))
    return " ".join(out)[:NOME_PERSONA_MAX]


async def _primo_admin(org_id: str) -> Optional[dict]:
    from database import users_collection
    return await users_collection.find_one(
        {"organization_id": org_id, "role": "admin"},
        {"_id": 0, "id": 1, "name": 1}, sort=[("created_at", 1)])


async def nome_dall_account(org_id: str) -> str:
    """Il nome di chi si e' registrato, ripulito; vuoto se non c'e'."""
    u = await _primo_admin(org_id)
    return ripulisci((u or {}).get("name") or "")


async def nome_persona_effettivo(org_doc: dict) -> str:
    """Quello del profilo se c'e', altrimenti quello dell'account: cosi'
    l'editor (operatore o admin) mostra sempre il nome, anche prima del
    riempimento del pregresso."""
    pp = org_doc.get("public_profile") or {}
    salvato = " ".join((pp.get("nome_persona") or "").split()).strip()
    if salvato:
        return salvato
    try:
        return await nome_dall_account(org_doc.get("id") or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("nome_persona_effettivo: account non letto per %s: %s", org_doc.get("id"), exc)
        return ""


async def allinea_account(org_id: str, nome_persona: str) -> bool:
    """Il profilo ha un nome nuovo → l'account lo segue. True se ha scritto."""
    from database import users_collection
    nome = " ".join((nome_persona or "").split()).strip()[:NOME_PERSONA_MAX]
    if not nome:
        return False
    u = await _primo_admin(org_id)
    if not u or (u.get("name") or "").strip() == nome:
        return False
    r = await users_collection.update_one(
        {"id": u["id"]}, {"$set": {"name": nome, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return r.modified_count == 1


async def riempi_pregresso(prova: bool = True) -> dict:
    """Ogni org senza `public_profile.nome_persona` lo eredita dall'account.
    Idempotente: chi ce l'ha non si tocca. Ritorna cosa ha fatto (o farebbe)."""
    from database import organizations_collection
    from services.nome_pubblico import nome_pubblico
    esito = {"prova": prova, "scritte": 0, "senza_account": 0, "gia_piene": 0, "righe": []}
    async for o in organizations_collection.find(
            {"is_sample": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1, "public_profile": 1}):
        pp = o.get("public_profile") or {}
        if (pp.get("nome_persona") or "").strip():
            esito["gia_piene"] += 1
            continue
        nome = await nome_dall_account(o["id"])
        if not nome:
            esito["senza_account"] += 1
            continue
        dopo = nome_pubblico({**o, "public_profile": {**pp, "nome_persona": nome}})
        esito["righe"].append({"org": o.get("name"), "nome_persona": nome, "prima": nome_pubblico(o), "dopo": dopo})
        if not prova:
            await organizations_collection.update_one(
                {"id": o["id"], "public_profile.nome_persona": {"$in": [None, ""]}},
                {"$set": {"public_profile.nome_persona": nome}})
        esito["scritte"] += 1
    return esito
