"""SD6 (14/9/2026) — UNA regola per «questo ritiro si puo' prenotare», letta
da tre posti: lista pubblica (`routers/public._ritiro_listabile`),
griglia del gestionale (`routers/event_occurrences`, ragioni del bollino)
e Admin › Directory/Segnali (`services/platform_insights`).

Storia: il 10/9 (P3 + prova generale) l'obbligo di Stripe per la
directory e' stato tolto nella lista pubblica e nella griglia, ma il
riquadro in home del gestionale e l'admin erano rimasti a luglio
(GT1b): dicevano «non compari» a chi era in lista. Tre copie a mano
divergono; una funzione no.

La regola: un ritiro e' PRENOTABILE se e' «su richiesta» (la richiesta
arriva via email, caparra con bonifico) oppure se e' «prenotazione
online» e Stripe dell'operatore e' pronto. Un ritiro «online» senza
Stripe non si puo' prenotare in nessun modo: non si lista, e il
gestionale lo dice all'operatore (ragione `stripe_not_ready`).
"""
from typing import Dict, Iterable, List, Set

RAGIONE_STRIPE = "stripe_not_ready"


def modo(prod: Dict) -> str:
    return prod.get("transaction_mode") or "request"


def prenotabile(prod: Dict, pay_ready: Set[str]) -> bool:
    """Su richiesta: sempre. Online: solo con Stripe pronto."""
    return modo(prod) == "request" or prod.get("organization_id") in pay_ready


def prenotabile_con_stripe(prod: Dict, stripe_ready: bool) -> bool:
    """La stessa regola quando si guarda UNA org (griglia, home)."""
    return modo(prod) == "request" or bool(stripe_ready)


def ragioni_pagamento(prod: Dict, stripe_ready: bool) -> List[str]:
    """Le ragioni legate al pagamento (le altre — prodotto/data non
    pubblicati, pagina pubblica — vivono accanto, non dipendono dal modo)."""
    return [] if prenotabile_con_stripe(prod, stripe_ready) else [RAGIONE_STRIPE]


def conta_online_senza_stripe(prodotti: Iterable[Dict], stripe_ready: bool) -> int:
    """Quanti ritiri «online» resterebbero fuori: e' il numero che accende
    il riquadro in home del gestionale (solo questo caso, con il testo
    giusto)."""
    if stripe_ready:
        return 0
    return sum(1 for p in prodotti if modo(p) == "direct")
