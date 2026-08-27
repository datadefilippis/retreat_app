"""TR1 — LA CHIAVE 2: Crea Studio si accende con l'abbonamento
(deciso col founder il 27/8/2026, piano in
docs/CREA_TRACCE_RISERVATE_PLAN_2026-08.md).

Il principio: DERIVARE, MAI SINCRONIZZARE. Nessun flag scritto dai
webhook — ogni copia sincronizzata è una deriva che aspetta di
succedere (abbonamento scaduto ma flag acceso, o viceversa). Lo stato
si CALCOLA a ogni richiesta da ciò che il billing già sa. Questa
funzione è l'UNICA definizione di «Studio attivo» in tutto il
sistema: cambia il prezzo o arriva un piano nuovo, si tocca qui.

Le due chiavi:
  1. `sound_composer` — la concessione manuale del system admin
     (/admin/sound). Apre TUTTO, non scade mai, non c'entra col
     billing. È la chiave del founder e di Valentina: il loro flusso
     non cambia di un byte.
  2. il piano Pro attivo (o in prova, o `manual`) — apre comporre e
     condividere in privato. MAI le Meditazioni pubbliche: quel
     cancello resta `require_sound_composer`, che non passa di qui.

`sound_studio_override` è il campo per i casi umani: "on" = Studio a
mano (partnership) senza abbonamento; "off" = kill switch per-org
che vince su tutto, abbonamento compreso. Assente = vita normale.
"""

# Gli stati del billing che accendono Studio. `trialing` è la prova
# gratuita GIÀ esistente del piano (con l'anti-doppia-prova
# has_used_trial_plan_slug); `manual` è la fatturazione fuori
# piattaforma che il billing già contempla.
STATI_BILLING_VALIDI = ("active", "trialing", "manual")

# I piani che accendono Studio. TROVATO DAL COLLAUDO TR6 (27/8): la
# fonte del piano corrente è `commercial_plan_slug` (retreat_pro,
# retreat_founding, retreat_partner...), NON il campo legacy `plan`
# (spesso None/"free" anche su org abbonate) — col campo sbagliato
# nessun abbonato vero avrebbe mai avuto Studio. Founding e Partner
# sono trattamento-Pro assegnato dall'admin: Studio incluso.
PIANI_STUDIO = ("retreat_pro", "retreat_founding", "retreat_partner")

# La proiezione minima che serve a decidere: chiederla tutta uguale
# ovunque tiene le query piccole e il contratto visibile.
PROIEZIONE_STUDIO = {
    "_id": 0, "sound_composer": 1, "sound_studio_override": 1,
    "commercial_plan_slug": 1, "billing_status": 1,
}


def studio_attivo(org: dict | None) -> bool:
    """La verità su «questa org può usare Crea?», calcolata ora.

    L'ordine conta: il kill switch vince su tutto (anche sulla
    concessione manuale — è il freno d'emergenza); poi la chiave
    manuale (mai legata al billing); poi l'override "on"; infine
    l'abbonamento."""
    org = org or {}
    if org.get("sound_studio_override") == "off":
        return False
    if org.get("sound_composer"):
        return True
    if org.get("sound_studio_override") == "on":
        return True
    return (org.get("commercial_plan_slug") in PIANI_STUDIO
            and org.get("billing_status") in STATI_BILLING_VALIDI)


async def org_per_studio(org_id: str) -> dict:
    """L'org con la sola proiezione che serve alla decisione."""
    from database import organizations_collection
    return await organizations_collection.find_one(
        {"id": org_id}, PROIEZIONE_STUDIO) or {}
