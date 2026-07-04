"""
Commerce — AI tool definitions and execution.

Wave 7B.1 (2026-05): these 6 tools were moved here from
modules.cashflow_monitor.ai_tools. They belong with the commerce module
conceptually — they query orders, fulfillment, payments, events,
bookings and rentals, none of which are cashflow concerns.

The move is behavior-preserving: same tool names, same response shape,
same epistemic metadata. Only the registering module changes, which
means these tools are now gated by the `commerce` module entitlement
instead of `cashflow_monitor` — which is the correct gate. A new tool
in Wave 7B.2 will sit on top of this scaffold.

Provider-agnostic tool definitions; provider-specific formatting (e.g.
Anthropic input_schema) is handled by services.ai_tool_registry.

Public interface:
    TOOL_DEFINITIONS  — list of provider-agnostic tool dicts
    execute_tool(org_id, tool_name, tool_input) -> dict
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ── Provider-agnostic tool definitions ───────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "query_order_pipeline",
        "description": (
            "Pipeline ordini: raggruppa gli ordini per stato (bozza, confermato, completato, annullato) "
            "in un periodo. Restituisce conteggio e importo per ogni stato, totale ordini e ricavo totale. "
            "Usa per domande su ordini in attesa, pipeline vendite, conversione ordini."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio periodo (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine periodo (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_fulfillment_status",
        "description": (
            "Stato evasione ordini: snapshot degli ordini confermati/completati raggruppati per stato "
            "fulfillment (in attesa, spedito, consegnato, pronto ritiro, ritirato, evaso). "
            "Include ritardi (ordini pendenti da piu giorni). Nessun parametro richiesto."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_payment_pipeline",
        "description": (
            "Pipeline pagamenti: raggruppa ordini attivi per stato pagamento e intent. "
            "Mostra quanti ordini attendono pagamento, quanti hanno pagamento raccolto ma non confermato, "
            "e quanti sono pagati. Utile per capire cassa in arrivo."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_event_metrics",
        "description": (
            "Metriche eventi: per ogni evento (nel periodo o futuri), restituisce nome, data, luogo, "
            "capienza, posti prenotati, fill rate percentuale e ricavo. "
            "Usa per domande su riempimento eventi, biglietti venduti, eventi con poca partecipazione."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD). Se omesso, da oggi."},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD). Se omesso, tutti futuri."},
        },
        "required": [],
    },
    {
        "name": "query_booking_utilization",
        "description": (
            "Utilizzo agenda prenotazioni: calcola slot totali disponibili vs slot prenotati nel periodo. "
            "Restituisce percentuale utilizzo, giorno piu pieno, slot liberi oggi. "
            "Usa per domande su carico di lavoro, disponibilita agenda, quanto e piena l'agenda."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio periodo (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine periodo (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_rental_utilization",
        "description": (
            "Utilizzo noleggi: per ogni prodotto noleggiabile, calcola giorni prenotati vs giorni nel periodo. "
            "Restituisce percentuale utilizzo per prodotto. Filtrabile per singolo prodotto. "
            "Se date omesse, ultimi 30 giorni."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD). Default: 30 giorni fa."},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD). Default: oggi."},
            "product_id": {"type": "string", "description": "Filtra per singolo prodotto (opzionale)."},
        },
        "required": [],
    },

    # ── Wave 7B.2: orders & catalog commerce analytics ─────────────────────
    {
        "name": "query_orders_dashboard",
        "description": (
            "Dashboard ordini per un periodo: conteggio totale, fatturato totale, AOV (valore medio ordine), "
            "completion rate, breakdown per source (manual/storefront/...), e i 5 giorni con piu ordini. "
            "Usa per overview operativo: 'come vanno gli ordini questo mese?', 'quanto fatturo via storefront?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_aov_trend",
        "description": (
            "Trend dell'Average Order Value: confronta l'AOV del periodo corrente con quello del periodo "
            "precedente di pari durata, restituisce delta percentuale. Usa per 'sta crescendo il valore "
            "medio carrello?', 'i clienti spendono di piu?'."
        ),
        "parameters": {
            "period": {
                "type": "string",
                "description": "Periodo di analisi: '30d' (default), '60d', '90d'. Il periodo precedente confrontato e' di pari durata immediatamente precedente.",
            },
        },
        "required": [],
    },
    {
        "name": "query_cancellations_breakdown",
        "description": (
            "Analisi cancellazioni nel periodo: numero ordini cancellati, fatturato perso (somma dei total), "
            "tasso cancellazione vs totale ordini, e top 10 prodotti piu cancellati (estratti da items). "
            "Usa per 'quanto perdo in cancellazioni?', 'quali prodotti vengono piu spesso cancellati?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_dormant_products",
        "description": (
            "Prodotti dormienti: nessuna vendita da N giorni (default 30) o mai venduti. "
            "Restituisce nome, fatturato storico, giorni dall'ultima vendita. Usa per 'quali prodotti "
            "non vendo piu?', 'cosa c'e' fermo nel catalogo?', 'long tail morto'."
        ),
        "parameters": {
            "days_threshold": {
                "type": "integer",
                "description": "Soglia in giorni: un prodotto e' dormiente se la sua last_sale_date e' anteriore a (oggi - N giorni). Default: 30. Max: 365.",
            },
            "limit": {
                "type": "integer",
                "description": "Numero massimo di prodotti (default: 10, max: 50).",
            },
        },
        "required": [],
    },

    # ── Wave 7B.3: channels, stores, catalog health, customer & basket mix ──
    {
        "name": "query_channels_performance",
        "description": (
            "Performance per canale di vendita (source): per ogni canale "
            "(manual/storefront/storefront_direct/storefront_approval) restituisce conteggio ordini, "
            "fatturato, AOV, completion rate, cancellation rate. Usa per 'da dove arrivano le vendite?', "
            "'lo storefront converte come il POS?', 'qual e' il canale migliore?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_stores_overview",
        "description": (
            "Overview di tutti gli store dell'organizzazione: nome, attivo, pubblicato, "
            "ordini totali (lifetime e ultimi 30 giorni), fatturato. Usa per 'quanti store ho?', "
            "'sono tutti pubblicati?', 'qual e' lo store piu performante?'."
        ),
        "parameters": {
            "include_inactive": {
                "type": "boolean",
                "description": "Se true include anche gli store con is_active=false (default: false).",
            },
        },
        "required": [],
    },
    {
        "name": "query_store_performance",
        "description": (
            "Performance di un singolo store nel periodo: ordini, fatturato, AOV, top 5 prodotti "
            "venduti, breakdown per status. Richiede store_id. Usa per 'come va lo store X?', "
            "'quali sono i bestseller di store Y questo mese?'."
        ),
        "parameters": {
            "store_id": {"type": "string", "description": "ID dello store da analizzare (obbligatorio)."},
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD). Default: 30 giorni fa."},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD). Default: oggi."},
        },
        "required": ["store_id"],
    },
    {
        "name": "query_catalog_health",
        "description": (
            "Salute del catalogo prodotti: conteggio dei prodotti con dati mancanti "
            "(senza prezzo, senza costo, senza descrizione, inattivi). Restituisce 5 esempi per "
            "categoria di problema. Usa per 'il catalogo e' a posto?', 'cosa manca?', "
            "'quanti prodotti senza prezzo?'."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_new_vs_returning_split",
        "description": (
            "Split fatturato tra nuovi clienti, clienti che tornano e guest nel periodo. "
            "'Returning' = il customer_account_id aveva gia' ordini non cancellati prima dell'inizio periodo. "
            "'New' = primo ordine nel periodo. 'Guest' = ordine senza customer_account_id. "
            "Usa per 'i clienti tornano?', 'quanto fatturo da nuovi vs ricorrenti?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_basket_size_distribution",
        "description": (
            "Distribuzione della dimensione carrello (quantita totale di prodotti per ordine) "
            "in 4 bucket: '1 item', '2-3', '4-5', '6+'. Per ogni bucket: count, revenue, AOV. "
            "Usa per 'come sono fatti i miei carrelli?', 'i clienti comprano un solo prodotto?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },

    # ── Wave 7C.1: Calendar A — agenda/servizi (consulting bookings) ───────
    # These tools focus on the AGENDA calendar (services/consultations).
    # Rental-specific tools come in Wave 7C.2. Scope-aware: blocked_slots
    # with scope='rentals' are excluded; scope='agenda' OR scope=null
    # (global "person busy") are included.
    {
        "name": "query_agenda_today",
        "description": (
            "Agenda di oggi: tutte le prenotazioni confermate (issued_bookings) ordinate per orario, "
            "piu i blocchi agenda (personal/holiday/booking) per oggi. Usa per 'cosa ho oggi?', "
            "'chi vedo oggi?', 'sono libero oggi?'."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_agenda_upcoming",
        "description": (
            "Agenda dei prossimi N giorni: per ogni giorno restituisce conteggio prenotazioni "
            "confermate, prenotazioni cancellate, e principali appuntamenti (top 5 per giorno). "
            "Usa per 'cosa ho questa settimana?', 'come e' carica l'agenda prossimi 7 giorni?'."
        ),
        "parameters": {
            "days_ahead": {
                "type": "integer",
                "description": "Giorni da analizzare a partire da oggi (default: 7, max: 30).",
            },
        },
        "required": [],
    },
    {
        "name": "query_agenda_summary",
        "description": (
            "Sintesi agenda: KPI aggregati su oggi, domani, settimana. Per ognuno: prenotazioni "
            "confermate, completate, cancellate, no-show, slot liberi residui. Usa per 'panoramica "
            "agenda', 'come va l'agenda?'."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_free_slots",
        "description": (
            "Slot liberi tra due date: per ogni giorno calcola gli slot disponibili dalle regole "
            "ricorrenti meno gli slot bloccati (scope=agenda o globali) e meno le prenotazioni "
            "confermate. Restituisce per ogni giorno: total_slots, free_slots, prima e ultima "
            "fascia oraria libera. Usa per 'quando sono libero?', 'ho slot disponibili venerdi?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD). Max 30 giorni dal start_date."},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_blocked_periods",
        "description": (
            "Periodi bloccati in un range: lista dei blocked_slots con scope agenda o globali, "
            "raggruppati per reason (personal/holiday/booking/event). Esclude i blocchi rental. "
            "Usa per 'quando sono bloccato?', 'ferie programmate?', 'quante festivita questo mese?'."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
            "reason": {
                "type": "string",
                "description": "Filtro opzionale per reason: personal | holiday | booking | event.",
            },
        },
        "required": ["start_date", "end_date"],
    },

    # ── Wave 7C.2: Calendar B — rentals (asset-level, range + slot) ────────
    # Mirror of agenda tools but for rentals. Source of truth:
    # issued_reservations_collection (reservation_flavor in {range, slot}).
    # These tools are FORWARD-looking (current state + future) — for the
    # backward-looking utilization, see query_rental_utilization (Wave 7B.1)
    # and query_idle_rentals (Wave 7A.3).
    {
        "name": "query_rentals_today",
        "description": (
            "Noleggi attualmente in corso oggi. Range = data_from <= oggi <= date_to. "
            "Slot = slot_date = oggi. Solo status=active. Restituisce per ogni rental: prodotto, "
            "cliente, data inizio/fine, codice. Usa per 'cosa ho a noleggio oggi?', "
            "'quali asset sono fuori?'."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_rentals_upcoming",
        "description": (
            "Noleggi in partenza nei prossimi N giorni. Range = date_from in [oggi, oggi+N]. "
            "Slot = slot_date in [oggi, oggi+N]. Restituisce per ogni rental futuro: prodotto, "
            "cliente, date, codice, giorni di anticipo. Usa per 'cosa esce questa settimana?', "
            "'quanti noleggi confermati per i prossimi giorni?'."
        ),
        "parameters": {
            "days_ahead": {
                "type": "integer",
                "description": "Giorni da analizzare a partire da oggi (default: 7, max: 60).",
            },
        },
        "required": [],
    },
    {
        "name": "query_rentals_returning",
        "description": (
            "Noleggi in rientro nei prossimi N giorni. Range = date_to in [oggi, oggi+N]. "
            "Utile per pianificare ritiri, sanificazione, controllo. Restituisce per ogni rental "
            "in rientro: prodotto, cliente, data rientro, codice. Usa per 'cosa rientra "
            "domani?', 'devo preparare la sanificazione?'."
        ),
        "parameters": {
            "days_ahead": {
                "type": "integer",
                "description": "Giorni da analizzare a partire da oggi (default: 7, max: 30).",
            },
        },
        "required": [],
    },
    {
        "name": "query_rental_availability",
        "description": (
            "Disponibilita di un singolo asset in un range: per ogni giorno indica se e' "
            "prenotato (con cliente) o libero. Richiede product_id. Range max 30 giorni. "
            "Usa per 'quando e' disponibile la bici X?', 'la casa Y e' libera il prossimo "
            "weekend?'."
        ),
        "parameters": {
            "product_id": {"type": "string", "description": "ID del prodotto/asset (obbligatorio)."},
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD). Max 30 giorni da start_date."},
        },
        "required": ["product_id", "start_date", "end_date"],
    },
    {
        "name": "query_rental_pipeline",
        "description": (
            "Pipeline noleggi futuri aggregata: numero di rental futuri (status=active, "
            "date_from > oggi) per i prossimi N giorni, raggruppati per asset. Restituisce "
            "top 10 asset per rental confermati, totale rental futuri, primo rental in arrivo. "
            "Usa per 'quanti noleggi confermati ho per il prossimo mese?', 'qual e' l'asset "
            "piu prenotato?'."
        ),
        "parameters": {
            "days_ahead": {
                "type": "integer",
                "description": "Giorni in avanti da considerare (default: 30, max: 90).",
            },
        },
        "required": [],
    },

    # ── Wave 7C.3: Events calendar (public events, occurrence-level) ───────
    # Operational counterpart of query_event_metrics (analytics). This tool
    # gives the AI a forward-looking events calendar view for "what events
    # do I have coming up?" — distinct from event_metrics which is about
    # fill_rate, capacity, revenue analysis.
    {
        "name": "query_events_calendar",
        "description": (
            "Calendario eventi pubblici (event_occurrences) nei prossimi N giorni. Restituisce "
            "per ogni evento: nome, data/ora, location, capienza, biglietti venduti (booked), "
            "stato (published/draft). Differente da query_event_metrics che invece e' focalizzato "
            "su fill_rate e ricavi. Usa per 'che eventi ho questa settimana?', "
            "'quali sono i prossimi eventi pubblicati?'."
        ),
        "parameters": {
            "days_ahead": {
                "type": "integer",
                "description": "Giorni in avanti da considerare (default: 14, max: 60).",
            },
            "include_past": {
                "type": "boolean",
                "description": "Se true, include anche eventi nel passato recente (default: false).",
            },
        },
        "required": [],
    },

    # ── Wave 7D: coupons + courses (commerce polish) ──────────────────────
    {
        "name": "query_coupon_usage",
        "description": (
            "Analytics coupon: per ogni coupon configurato (coupons_collection) restituisce "
            "utilizzi totali (current_uses), max_uses, scontistica totale concessa (somma "
            "discount_total su ordini con coupon_code), tasso utilizzo. Usa per 'quanto sconto "
            "ho dato?', 'qual e' il coupon piu usato?', 'sto perdendo margine con i coupon?'."
        ),
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "Data inizio per il calcolo dello sconto totale (opzionale, default: lifetime).",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine (opzionale, default: oggi).",
            },
            "include_inactive": {
                "type": "boolean",
                "description": "Se true include coupon disattivati (default: false).",
            },
        },
        "required": [],
    },
    {
        "name": "query_course_engagement",
        "description": (
            "Engagement corsi: per ogni corso (courses_collection) conta iscritti totali "
            "(issued_course_accesses), iscritti attivi (non revocati e non scaduti), accessi "
            "recenti (last_accessed_at negli ultimi 30 giorni). Usa per 'quanti iscritti ho?', "
            "'qual e' il corso piu seguito?', 'gli iscritti sono attivi?'."
        ),
        "parameters": {
            "limit": {
                "type": "integer",
                "description": "Numero massimo di corsi (default 10, max 50).",
            },
        },
        "required": [],
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slots_from_rule(start_time: str, end_time: str, duration_min: int) -> int:
    """Count how many slots fit in a rule window. Used by query_booking_utilization."""
    sh, sm = map(int, start_time.split(":"))
    eh, em = map(int, end_time.split(":"))
    return max(0, ((eh * 60 + em) - (sh * 60 + sm)) // duration_min)


async def _get_org_currency(org_id: str) -> str:
    """Fetch the organization's configured currency (default EUR)."""
    try:
        from repositories import organization_repository
        org = await organization_repository.find_by_id(org_id)
        return (org.get("currency") if org else None) or "EUR"
    except Exception:
        return "EUR"


# ── Tool execution dispatch ──────────────────────────────────────────────────

async def execute_tool(org_id: str, tool_name: str, tool_input: dict) -> dict:
    """Execute a commerce AI tool and return the result as a JSON-serializable dict.

    Returns {"error": "..."} if the tool is unknown or execution fails.
    """
    logger.info("commerce ai_tools: executing %s with input %s", tool_name, tool_input)

    currency = await _get_org_currency(org_id)

    try:
        if tool_name == "query_order_pipeline":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            pipeline = [
                {"$match": {"organization_id": org_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {"_id": "$status",
                            "count": {"$sum": 1},
                            "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
            ]
            results = {}
            async for doc in orders_collection.aggregate(pipeline):
                results[doc["_id"]] = {"count": doc["count"], "amount": round(doc["amount"], 2)}

            total_orders = sum(v["count"] for v in results.values())
            total_revenue = round(sum(v["amount"] for v in results.values()), 2)
            has_data = total_orders > 0

            # Analysis
            completed = results.get("completed", {}).get("count", 0)
            confirmed = results.get("confirmed", {}).get("count", 0)
            draft = results.get("draft", {}).get("count", 0)
            cancelled = results.get("cancelled", {}).get("count", 0)
            active = completed + confirmed + draft
            conversion_rate = round(completed / active * 100, 1) if active > 0 else 0
            cancellation_rate = round(cancelled / total_orders * 100, 1) if total_orders > 0 else 0

            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "by_status": results,
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "analysis": {
                    "conversion_rate_pct": conversion_rate,
                    "cancellation_rate_pct": cancellation_rate,
                    "draft_pending": draft,
                    "revenue_at_risk": results.get("draft", {}).get("amount", 0),
                    "revenue_confirmed": round(results.get("confirmed", {}).get("amount", 0) + results.get("completed", {}).get("amount", 0), 2),
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Ordini filtrati per data creazione nel periodo richiesto.",
                },
                "analytical_hints": {
                    "cross_module": ["Confrontare total_revenue con query_cashflow_summary.total_sales per allineamento periodo"],
                    "interpretation": "draft_pending = ordini non ancora confermati, revenue_at_risk = potenziale non realizzato. cancellation_rate > 15% indica problemi.",
                },
                "_caveat": None if has_data else "Nessun ordine nel periodo selezionato.",
            }

        elif tool_name == "query_fulfillment_status":
            from database import orders_collection
            from datetime import datetime as dt

            # Group by fulfillment status
            pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": {"$in": ["confirmed", "completed"]}}},
                {"$group": {"_id": {"$ifNull": ["$fulfillment.status", "not_required"]},
                            "count": {"$sum": 1}}},
            ]
            by_ff = {}
            async for doc in orders_collection.aggregate(pipeline):
                by_ff[doc["_id"]] = doc["count"]

            # Find delays (pending fulfillment > 3 days)
            now = dt.utcnow()
            delay_cursor = orders_collection.find(
                {"organization_id": org_id,
                 "status": {"$in": ["confirmed", "completed"]},
                 "fulfillment.status": "pending"},
                {"_id": 0, "order_number": 1, "created_at": 1, "customer_name": 1},
            ).sort("created_at", 1).limit(20)
            delays = []
            async for o in delay_cursor:
                created = o.get("created_at")
                if isinstance(created, dt):
                    days = (now - created).days
                    if days >= 3:
                        delays.append({
                            "order_number": o.get("order_number"),
                            "customer": o.get("customer_name"),
                            "days_pending": days,
                        })

            has_data = sum(by_ff.values()) > 0
            total_ff = sum(v for k, v in by_ff.items() if k != "not_required")
            completed_ff = sum(v for k, v in by_ff.items() if k in ("delivered", "picked_up", "fulfilled"))
            urgent = [d for d in delays if d["days_pending"] >= 7]

            return {
                "has_data": has_data,
                "by_fulfillment_status": by_ff,
                "delays": delays,
                "delay_count": len(delays),
                "analysis": {
                    "total_requiring_fulfillment": total_ff,
                    "completion_rate_pct": round(completed_ff / total_ff * 100, 1) if total_ff > 0 else 0,
                    "urgent_delays": len(urgent),
                    "avg_delay_days": round(sum(d["days_pending"] for d in delays) / len(delays), 1) if delays else 0,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "current_state",
                    "note": "Snapshot attuale degli ordini confermati/completati. Non riflette dati storici.",
                },
                "analytical_hints": {
                    "cross_module": ["Confrontare con query_payment_pipeline per vedere pagamento vs evasione"],
                    "interpretation": "pending > 7gg = critico, suggerire azione immediata. urgent_delays > 0 = priorita operativa.",
                },
                "_caveat": None if has_data else "Nessun ordine confermato/completato trovato.",
            }

        elif tool_name == "query_payment_pipeline":
            from database import orders_collection

            pipeline = [
                {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"}}},
                {"$group": {
                    "_id": {"ps": "$payment_status", "pi": "$payment_intent"},
                    "count": {"$sum": 1},
                    "amount": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
            ]
            buckets = {
                "awaiting_payment": {"count": 0, "amount": 0},
                "collected_not_confirmed": {"count": 0, "amount": 0},
                "paid": {"count": 0, "amount": 0},
                "pending_no_payment_required": {"count": 0, "amount": 0},
            }
            async for doc in orders_collection.aggregate(pipeline):
                ps = doc["_id"]["ps"]
                pi = doc["_id"]["pi"]
                c, a = doc["count"], round(doc["amount"], 2)
                if ps == "paid":
                    buckets["paid"]["count"] += c
                    buckets["paid"]["amount"] += a
                elif pi == "collected":
                    buckets["collected_not_confirmed"]["count"] += c
                    buckets["collected_not_confirmed"]["amount"] += a
                elif pi == "required":
                    buckets["awaiting_payment"]["count"] += c
                    buckets["awaiting_payment"]["amount"] += a
                else:
                    buckets["pending_no_payment_required"]["count"] += c
                    buckets["pending_no_payment_required"]["amount"] += a

            for b in buckets.values():
                b["amount"] = round(b["amount"], 2)
            total = sum(b["count"] for b in buckets.values())

            cash_at_risk = round(buckets["awaiting_payment"]["amount"] + buckets["collected_not_confirmed"]["amount"], 2)
            collection_rate = round(buckets["paid"]["count"] / total * 100, 1) if total > 0 else 0

            return {
                "has_data": total > 0,
                "currency": currency,
                "buckets": buckets,
                "total_active_orders": total,
                "analysis": {
                    "collection_rate_pct": collection_rate,
                    "cash_at_risk": cash_at_risk,
                    "collected_not_confirmed_critical": buckets["collected_not_confirmed"]["count"] > 0,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "current_state",
                    "note": "Stato attuale pagamenti su ordini non cancellati.",
                },
                "analytical_hints": {
                    "cross_module": ["Confrontare cash_at_risk con scadenzario cashflow (open_receivables)"],
                    "interpretation": "collected_not_confirmed = denaro incassato ma ordine non confermato, azione urgente. cash_at_risk = potenziale incasso non ancora realizzato.",
                },
                "_caveat": None if total > 0 else "Nessun ordine attivo trovato.",
            }

        elif tool_name == "query_event_metrics":
            from database import orders_collection
            eo_coll = __import__("database", fromlist=["db"]).db.event_occurrences

            start = tool_input.get("start_date")
            end = tool_input.get("end_date")

            occ_query = {"organization_id": org_id, "status": "published"}
            if start:
                occ_query["start_at"] = {"$gte": start}
            elif not end:
                from datetime import date
                occ_query["start_at"] = {"$gte": date.today().isoformat()}
            if end:
                occ_query.setdefault("start_at", {})
                if isinstance(occ_query["start_at"], dict):
                    occ_query["start_at"]["$lte"] = end + "T23:59:59"
                else:
                    occ_query["start_at"] = {"$gte": occ_query["start_at"], "$lte": end + "T23:59:59"}

            occ_list = await eo_coll.find(occ_query, {"_id": 0}).sort("start_at", 1).to_list(100)
            occ_ids = [o["id"] for o in occ_list]

            # Booked counts + revenue per occurrence
            booked_map = {}
            revenue_map = {}
            if occ_ids:
                pipeline = [
                    {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                                "items.occurrence_id": {"$in": occ_ids}}},
                    {"$unwind": "$items"},
                    {"$match": {"items.occurrence_id": {"$in": occ_ids}}},
                    {"$group": {"_id": "$items.occurrence_id",
                                "booked": {"$sum": "$items.quantity"},
                                "revenue": {"$sum": "$items.line_total"}}},
                ]
                async for doc in orders_collection.aggregate(pipeline):
                    booked_map[doc["_id"]] = int(doc["booked"])
                    revenue_map[doc["_id"]] = round(doc["revenue"], 2)

            events = []
            for occ in occ_list:
                cap = occ.get("capacity")
                booked = booked_map.get(occ["id"], 0)
                rev = revenue_map.get(occ["id"], 0)
                fill = round(booked / cap * 100, 1) if cap and cap > 0 else None
                events.append({
                    "name": occ.get("product_name", "Evento"),
                    "date": occ.get("start_at", "")[:10],
                    "time": occ.get("start_at", "")[11:16] if len(occ.get("start_at", "")) > 11 else None,
                    "location": occ.get("location"),
                    "capacity": cap,
                    "booked": booked,
                    "fill_rate_pct": fill,
                    "revenue": rev,
                })

            # Analysis
            capped_events = [e for e in events if e["capacity"] is not None]
            total_cap = sum(e["capacity"] for e in capped_events) if capped_events else 0
            total_booked = sum(e["booked"] for e in events)
            total_rev = round(sum(e["revenue"] for e in events), 2)
            fill_rates = [e["fill_rate_pct"] for e in capped_events if e["fill_rate_pct"] is not None]
            avg_fill = round(sum(fill_rates) / len(fill_rates), 1) if fill_rates else None
            underperforming = [e for e in capped_events if (e["fill_rate_pct"] or 0) < 30]

            return {
                "has_data": len(events) > 0,
                "currency": currency,
                "events": events,
                "total_events": len(events),
                "analysis": {
                    "total_capacity": total_cap,
                    "total_booked": total_booked,
                    "total_revenue": total_rev,
                    "avg_fill_rate_pct": avg_fill,
                    "underperforming_count": len(underperforming),
                    "underperforming_events": [e["name"] for e in underperforming],
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "fill_rate disponibile solo per eventi con capienza definita." if not capped_events else None,
                },
                "temporal_context": {
                    "scope": "period_filtered" if start else "future_snapshot",
                    "note": "Eventi futuri o nel periodo selezionato. Prenotazioni basate su ordini non cancellati.",
                },
                "analytical_hints": {
                    "cross_module": ["Confrontare total_revenue con cashflow total_sales per quota eventi su ricavo totale"],
                    "interpretation": "fill_rate < 30% a meno di 3 giorni dall'evento = azione urgente (promozione, reminder). underperforming_count > 0 = attenzione operativa necessaria.",
                },
                "_caveat": None if events else "Nessun evento trovato nel periodo.",
            }

        elif tool_name == "query_booking_utilization":
            from database import availability_rules_collection, blocked_slots_collection
            from datetime import date as date_type, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            d_start = date_type.fromisoformat(start)
            d_end = date_type.fromisoformat(end)
            days = (d_end - d_start).days + 1
            if days > 60:
                return {"error": "Intervallo massimo 60 giorni."}

            # Load rules
            rules = await availability_rules_collection.find(
                {"organization_id": org_id, "is_active": True}, {"_id": 0}
            ).to_list(100)
            rules_by_day = {}
            for r in rules:
                rules_by_day.setdefault(r["day_of_week"], []).append(r)

            # Count total available slots
            total_slots = 0
            current = d_start
            while current <= d_end:
                for r in rules_by_day.get(current.weekday(), []):
                    total_slots += _slots_from_rule(r["start_time"], r["end_time"], r.get("slot_duration_minutes", 60))
                current += timedelta(days=1)

            # Count booked slots (reason=booking in range)
            booked_cursor = blocked_slots_collection.find(
                {"organization_id": org_id, "reason": "booking",
                 "date": {"$gte": start, "$lte": end}},
                {"_id": 0, "date": 1},
            )
            booked_dates = {}
            async for b in booked_cursor:
                booked_dates[b["date"]] = booked_dates.get(b["date"], 0) + 1
            booked_slots = sum(booked_dates.values())

            util_pct = round(booked_slots / total_slots * 100, 1) if total_slots > 0 else 0
            busiest_day = max(booked_dates, key=booked_dates.get) if booked_dates else None

            # Free slots today
            today_str = date_type.today().isoformat()
            today_total = sum(
                _slots_from_rule(r["start_time"], r["end_time"], r.get("slot_duration_minutes", 60))
                for r in rules_by_day.get(date_type.today().weekday(), [])
            )
            today_booked = booked_dates.get(today_str, 0)

            avg_daily = round(booked_slots / days, 1) if days > 0 else 0

            return {
                "period": {"start_date": start, "end_date": end, "days": days},
                "has_data": total_slots > 0,
                "total_slots": total_slots,
                "booked_slots": booked_slots,
                "utilization_pct": util_pct,
                "busiest_day": busiest_day,
                "free_slots_today": max(0, today_total - today_booked),
                "analysis": {
                    "avg_daily_bookings": avg_daily,
                    "capacity_status": "alta" if util_pct > 80 else "media" if util_pct > 40 else "bassa",
                },
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "medium",
                    "ai_usability": "partial",
                    "caveat": "Basato su regole availability configurate. Se le regole non sono complete, la capacita totale potrebbe essere sottostimata.",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Slot disponibili calcolati dalle regole ricorrenti settimanali. Slot prenotati da ordini confermati.",
                },
                "analytical_hints": {
                    "interpretation": "utilization > 80% = agenda quasi piena, valutare espansione orari. < 20% = capacita inutilizzata, valutare promozione.",
                },
                "_caveat": None if total_slots > 0 else "Nessuna regola di disponibilita configurata.",
            }

        elif tool_name == "query_rental_utilization":
            from database import blocked_slots_collection, products_collection
            from datetime import date as date_type, timedelta

            end = tool_input.get("end_date") or date_type.today().isoformat()
            start = tool_input.get("start_date") or (date_type.fromisoformat(end) - timedelta(days=30)).isoformat()
            product_id = tool_input.get("product_id")
            days_in_period = (date_type.fromisoformat(end) - date_type.fromisoformat(start)).days + 1

            match = {"organization_id": org_id, "reason": "rental",
                     "date": {"$gte": start, "$lte": end}}
            if product_id:
                match["product_id"] = product_id

            pipeline = [
                {"$match": match},
                {"$group": {"_id": "$product_id", "dates": {"$addToSet": "$date"}}},
                {"$project": {"product_id": "$_id", "days_booked": {"$size": "$dates"}, "_id": 0}},
            ]
            results = []
            async for doc in blocked_slots_collection.aggregate(pipeline):
                pid = doc.get("product_id")
                prod = await products_collection.find_one(
                    {"id": pid, "organization_id": org_id},
                    {"_id": 0, "name": 1},
                ) if pid else None
                results.append({
                    "product_name": prod.get("name", "Sconosciuto") if prod else "Sconosciuto",
                    "product_id": pid,
                    "days_booked": doc["days_booked"],
                    "days_in_period": days_in_period,
                    "utilization_pct": round(doc["days_booked"] / days_in_period * 100, 1) if days_in_period > 0 else 0,
                })

            results.sort(key=lambda x: x["utilization_pct"], reverse=True)

            # Analysis
            avg_util = round(sum(r["utilization_pct"] for r in results) / len(results), 1) if results else 0
            top = results[0] if results else None
            underutilized = [r for r in results if r["utilization_pct"] < 20]
            idle = [r for r in results if r["days_booked"] == 0]

            return {
                "period": {"start_date": start, "end_date": end, "days": days_in_period},
                "has_data": len(results) > 0,
                "products": results,
                "total_rental_products": len(results),
                "analysis": {
                    "avg_utilization_pct": avg_util,
                    "top_performer": top["product_name"] if top else None,
                    "underutilized_count": len(underutilized),
                    "underutilized_names": [r["product_name"] for r in underutilized],
                    "idle_count": len(idle),
                    "idle_names": [r["product_name"] for r in idle],
                },
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "medium",
                    "ai_usability": "partial",
                    "caveat": "Utilizzo basato su blocchi calendario (giorni interi). Non riflette ore effettive di utilizzo.",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Giorni noleggiati nel periodo. Un giorno con blocco parziale conta come giorno intero.",
                },
                "analytical_hints": {
                    "interpretation": "utilization < 20% = asset sottoutilizzato, valutare riduzione prezzo o promozione. idle = asset mai noleggiato nel periodo, potenziale costo morto.",
                    "cross_module": ["Confrontare con query_order_pipeline per vedere revenue da noleggi nel periodo"],
                },
                "_caveat": None if results else "Nessun noleggio trovato nel periodo.",
            }

        # ── Wave 7B.2: orders & catalog commerce analytics ─────────────────

        elif tool_name == "query_orders_dashboard":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # Aggregate counts by status + source, plus daily distribution
            pipeline_status_source = [
                {"$match": {"organization_id": org_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {
                    "_id": {"status": "$status", "source": {"$ifNull": ["$source", "manual"]}},
                    "count": {"$sum": 1},
                    "amount": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
            ]
            by_status = {}
            by_source = {}
            total_orders = 0
            total_revenue = 0.0
            active_revenue = 0.0  # excl. cancelled, used for AOV
            async for doc in orders_collection.aggregate(pipeline_status_source):
                status = doc["_id"]["status"]
                source = doc["_id"]["source"]
                c, a = doc["count"], round(doc["amount"], 2)
                by_status[status] = by_status.get(status, 0) + c
                by_source.setdefault(source, {"count": 0, "amount": 0.0})
                by_source[source]["count"] += c
                by_source[source]["amount"] += a
                total_orders += c
                total_revenue += a
                if status != "cancelled":
                    active_revenue += a
            for s in by_source.values():
                s["amount"] = round(s["amount"], 2)

            total_revenue = round(total_revenue, 2)
            active_revenue = round(active_revenue, 2)
            completed = by_status.get("completed", 0)
            cancelled = by_status.get("cancelled", 0)
            active_orders = total_orders - cancelled
            # AOV uses active revenue / active count (excludes cancelled).
            aov = round(active_revenue / active_orders, 2) if active_orders > 0 else 0
            completion_rate = round(completed / active_orders * 100, 1) if active_orders > 0 else 0
            cancellation_rate = round(cancelled / total_orders * 100, 1) if total_orders > 0 else 0

            # Top 5 days by order count
            pipeline_daily = [
                {"$match": {"organization_id": org_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1},
                    "revenue": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 5},
            ]
            top_days = []
            async for d in orders_collection.aggregate(pipeline_daily):
                top_days.append({"date": d["_id"], "orders": d["count"],
                                 "revenue": round(d["revenue"], 2)})

            has_data = total_orders > 0
            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "aov": aov,
                "by_status": by_status,
                "by_source": by_source,
                "top_days_by_volume": top_days,
                "analysis": {
                    "completion_rate_pct": completion_rate,
                    "cancellation_rate_pct": cancellation_rate,
                    "active_orders_excl_cancelled": active_orders,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Ordini per data creazione nel periodo. AOV calcolato escludendo i cancellati.",
                },
                "analytical_hints": {
                    "cross_module": [
                        "Confrontare total_revenue con query_cashflow_summary.total_sales per allineamento",
                        "Usa query_aov_trend per il delta AOV vs periodo precedente",
                    ],
                    "interpretation": "AOV in crescita = clienti spendono di piu o mix prodotti spostato verso fascia alta. cancellation_rate > 10% = problema operativo.",
                },
                "_caveat": None if has_data else "Nessun ordine nel periodo selezionato.",
            }

        elif tool_name == "query_aov_trend":
            from database import orders_collection
            from datetime import date as date_type, datetime as dt, timedelta

            period_str = tool_input.get("period", "30d")
            try:
                days = int(period_str.rstrip("d"))
            except (ValueError, AttributeError):
                days = 30
            days = max(7, min(days, 365))

            today = date_type.today()
            cur_end = dt.combine(today, dt.min.time()) + timedelta(days=1)
            cur_start = cur_end - timedelta(days=days)
            prev_end = cur_start
            prev_start = prev_end - timedelta(days=days)

            async def _aov(start_dt, end_dt):
                pipeline = [
                    {"$match": {"organization_id": org_id,
                                 "status": {"$ne": "cancelled"},
                                 "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                    {"$group": {
                        "_id": None,
                        "count": {"$sum": 1},
                        "revenue": {"$sum": {"$ifNull": ["$total", 0]}},
                    }},
                ]
                async for doc in orders_collection.aggregate(pipeline):
                    cnt = doc["count"]
                    rev = round(doc["revenue"], 2)
                    return cnt, rev, (round(rev / cnt, 2) if cnt > 0 else 0)
                return 0, 0.0, 0.0

            cur_count, cur_rev, cur_aov = await _aov(cur_start, cur_end)
            prev_count, prev_rev, prev_aov = await _aov(prev_start, prev_end)

            delta_pct = None
            if prev_aov > 0:
                delta_pct = round((cur_aov - prev_aov) / prev_aov * 100, 1)
            direction = "n/a"
            if delta_pct is not None:
                direction = "growing" if delta_pct > 2 else "declining" if delta_pct < -2 else "stable"

            has_data = cur_count > 0 or prev_count > 0
            return {
                "period_days": days,
                "has_data": has_data,
                "currency": currency,
                "current_period": {
                    "start_date": cur_start.date().isoformat(),
                    "end_date": (cur_end - timedelta(days=1)).date().isoformat(),
                    "orders": cur_count, "revenue": cur_rev, "aov": cur_aov,
                },
                "previous_period": {
                    "start_date": prev_start.date().isoformat(),
                    "end_date": (prev_end - timedelta(days=1)).date().isoformat(),
                    "orders": prev_count, "revenue": prev_rev, "aov": prev_aov,
                },
                "delta": {
                    "aov_delta_pct": delta_pct,
                    "direction": direction,
                },
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "high" if (cur_count >= 10 and prev_count >= 10) else "medium",
                    "ai_usability": "strong" if (cur_count >= 10 and prev_count >= 10) else "qualify_with_caveat",
                    "caveat": None if (cur_count >= 10 and prev_count >= 10) else "Volume ordini basso (<10 per periodo) — il trend potrebbe non essere statisticamente significativo.",
                },
                "temporal_context": {
                    "scope": "period_comparison",
                    "note": f"Periodo corrente: ultimi {days} giorni. Periodo precedente: i {days} giorni immediatamente prima. Esclusi gli ordini cancellati.",
                },
                "analytical_hints": {
                    "interpretation": "AOV growing senza order count growing = clienti spendono di piu (positivo). AOV growing + count declining = pochi clienti grossi (rischio concentrazione). AOV declining + count growing = scontistica eccessiva.",
                },
                "_caveat": None if has_data else "Nessun ordine in entrambi i periodi.",
            }

        elif tool_name == "query_cancellations_breakdown":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # Total orders in period (for rate calc)
            total_pipeline = [
                {"$match": {"organization_id": org_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$count": "n"},
            ]
            total_orders = 0
            async for doc in orders_collection.aggregate(total_pipeline):
                total_orders = doc["n"]

            # Cancelled orders + revenue lost
            cancel_pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": "cancelled",
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "lost_revenue": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
            ]
            cancelled_count = 0
            lost_revenue = 0.0
            async for doc in orders_collection.aggregate(cancel_pipeline):
                cancelled_count = doc["count"]
                lost_revenue = round(doc["lost_revenue"], 2)

            cancellation_rate = round(cancelled_count / total_orders * 100, 1) if total_orders > 0 else 0

            # Top cancelled products via items[] unwind
            top_pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": "cancelled",
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$unwind": "$items"},
                {"$group": {
                    "_id": {"product_id": "$items.product_id", "name": "$items.product_name"},
                    "cancel_count": {"$sum": "$items.quantity"},
                    "lost_amount": {"$sum": "$items.line_total"},
                }},
                {"$sort": {"lost_amount": -1}},
                {"$limit": 10},
            ]
            top_cancelled = []
            async for doc in orders_collection.aggregate(top_pipeline):
                top_cancelled.append({
                    "product_name": doc["_id"].get("name") or "Sconosciuto",
                    "product_id": doc["_id"].get("product_id"),
                    "cancelled_units": int(doc["cancel_count"]),
                    "lost_amount": round(doc["lost_amount"], 2),
                })

            has_data = cancelled_count > 0
            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "total_orders_in_period": total_orders,
                "cancelled_count": cancelled_count,
                "lost_revenue": lost_revenue,
                "cancellation_rate_pct": cancellation_rate,
                "top_cancelled_products": top_cancelled,
                "analysis": {
                    "severity": "critica" if cancellation_rate > 15 else "alta" if cancellation_rate > 8 else "fisiologica",
                    "avg_lost_per_cancelled": round(lost_revenue / cancelled_count, 2) if cancelled_count > 0 else 0,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Ordini cancellati per data creazione nel periodo. Lost_revenue = sommatoria total degli ordini cancellati.",
                },
                "analytical_hints": {
                    "cross_module": ["Confrontare top_cancelled_products con query_high_cancellation_products (catalogo) per pattern strutturali"],
                    "interpretation": "cancellation_rate > 15% = problema sistemico (pagamenti? logistica? UX?). top_cancelled concentrato su 1-2 prodotti = problema specifico (stock? prezzo?).",
                },
                "_caveat": None if has_data else "Nessun ordine cancellato nel periodo.",
            }

        elif tool_name == "query_dormant_products":
            from database import product_metrics_collection
            from datetime import datetime as dt, timedelta

            raw_thr = tool_input.get("days_threshold", 30)
            try:
                threshold_days = int(raw_thr)
            except (TypeError, ValueError):
                threshold_days = 30
            threshold_days = max(1, min(threshold_days, 365))

            raw_limit = tool_input.get("limit", 10)
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                limit = 10
            limit = max(1, min(limit, 50))

            cutoff = (dt.utcnow() - timedelta(days=threshold_days)).isoformat()

            # Find products with last_sale_date < cutoff OR missing entirely
            # Use $or to capture both buckets (dormant vs never-sold)
            query = {
                "organization_id": org_id,
                "$or": [
                    {"last_sale_date": {"$lt": cutoff}},
                    {"last_sale_date": None},
                ],
            }
            metrics = await product_metrics_collection.find(
                query, {"_id": 0}
            ).sort("last_sale_date", 1).to_list(length=limit)

            products = []
            now = dt.utcnow()
            for m in metrics:
                last_sale = m.get("last_sale_date")
                days_since = None
                bucket = "never_sold"
                if last_sale:
                    try:
                        parsed = dt.fromisoformat(last_sale.replace("Z", "+00:00") if isinstance(last_sale, str) else "")
                        if parsed.tzinfo is not None:
                            parsed = parsed.replace(tzinfo=None)
                        days_since = (now - parsed).days
                        bucket = "dormant"
                    except (ValueError, TypeError):
                        days_since = None
                products.append({
                    "name": m.get("product_name", "Sconosciuto"),
                    "sku": m.get("sku"),
                    "category": m.get("category"),
                    "bucket": bucket,
                    "last_sale_date": last_sale[:10] if isinstance(last_sale, str) and len(last_sale) >= 10 else None,
                    "days_since_last_sale": days_since,
                    "lifetime_revenue": m.get("total_revenue", 0),
                    "lifetime_units_sold": m.get("total_units_sold", 0),
                })

            never_sold = sum(1 for p in products if p["bucket"] == "never_sold")
            dormant = len(products) - never_sold

            return {
                "data": {
                    "has_data": bool(products),
                    "threshold_days_used": threshold_days,
                    "count": len(products),
                    "dormant_count": dormant,
                    "never_sold_count": never_sold,
                    "products": products,
                },
                "currency": currency,
                "epistemic_class": "factual",
                "reliability": "high" if len(products) >= 3 else "conditional",
                "temporal_scope": "all_time_with_recency_window",
                "temporal_alignment_safe": False,  # lifetime revenue, not period
                "ai_usability": "cite_directly" if len(products) >= 3 else "qualify_with_caveat",
                "caveat": None if len(products) >= 3 else "Pochi prodotti dormienti — l'analisi potrebbe non essere indicativa.",
                "analytical_hints": {
                    "interpretation": "never_sold = catalogo gonfiato senza domanda. dormant con high lifetime_revenue = stagionalita o fine ciclo. Considerare promozione, bundling, o ritiro.",
                },
            }

        # ── Wave 7B.3: channels, stores, catalog health, customer & basket mix ─

        elif tool_name == "query_channels_performance":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            pipeline = [
                {"$match": {"organization_id": org_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {
                    "_id": {"source": {"$ifNull": ["$source", "manual"]}, "status": "$status"},
                    "count": {"$sum": 1},
                    "amount": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
            ]
            # Aggregate into {source: {status: {count, amount}}}
            by_source: dict = {}
            async for doc in orders_collection.aggregate(pipeline):
                src = doc["_id"]["source"]
                status = doc["_id"]["status"]
                c = doc["count"]
                a = round(doc["amount"], 2)
                by_source.setdefault(src, {"_statuses": {}, "total_orders": 0,
                                           "total_revenue": 0.0, "active_revenue": 0.0,
                                           "active_orders": 0})
                by_source[src]["_statuses"][status] = {"count": c, "amount": a}
                by_source[src]["total_orders"] += c
                by_source[src]["total_revenue"] += a
                if status != "cancelled":
                    by_source[src]["active_revenue"] += a
                    by_source[src]["active_orders"] += c

            channels = []
            for src, data in sorted(by_source.items(), key=lambda kv: -kv[1]["total_revenue"]):
                statuses = data["_statuses"]
                completed = statuses.get("completed", {}).get("count", 0)
                cancelled = statuses.get("cancelled", {}).get("count", 0)
                completion = round(completed / data["active_orders"] * 100, 1) if data["active_orders"] > 0 else 0
                cancellation = round(cancelled / data["total_orders"] * 100, 1) if data["total_orders"] > 0 else 0
                aov = round(data["active_revenue"] / data["active_orders"], 2) if data["active_orders"] > 0 else 0
                channels.append({
                    "source": src,
                    "total_orders": data["total_orders"],
                    "total_revenue": round(data["total_revenue"], 2),
                    "aov": aov,
                    "completion_rate_pct": completion,
                    "cancellation_rate_pct": cancellation,
                    "by_status": statuses,
                })

            has_data = bool(channels)
            grand_total_revenue = round(sum(c["total_revenue"] for c in channels), 2)
            top_channel = channels[0]["source"] if channels else None

            # Mix percentages
            for c in channels:
                c["revenue_share_pct"] = round(c["total_revenue"] / grand_total_revenue * 100, 1) if grand_total_revenue > 0 else 0

            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "channels": channels,
                "total_channels": len(channels),
                "total_revenue": grand_total_revenue,
                "top_channel": top_channel,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Ordini per data creazione, raggruppati per source (canale).",
                },
                "analytical_hints": {
                    "interpretation": "Confronta cancellation_rate tra canali: differenze >5pp = problema specifico al canale. AOV piu alto su storefront = transazioni online con basket maggiore.",
                },
                "_caveat": None if has_data else "Nessun ordine nel periodo.",
            }

        elif tool_name == "query_stores_overview":
            from database import stores_collection, orders_collection
            from datetime import datetime as dt, timedelta

            include_inactive = bool(tool_input.get("include_inactive", False))

            store_query = {"organization_id": org_id}
            if not include_inactive:
                store_query["is_active"] = {"$ne": False}

            stores = await stores_collection.find(
                store_query,
                {"_id": 0, "id": 1, "name": 1, "is_active": 1, "is_published": 1,
                 "visibility": 1, "slug": 1},
            ).to_list(length=100)

            # Per-store aggregation (lifetime + last 30d)
            store_ids = [s["id"] for s in stores]
            now = dt.utcnow()
            cutoff_30d = now - timedelta(days=30)

            lifetime_agg = {}
            last30d_agg = {}
            if store_ids:
                async for doc in orders_collection.aggregate([
                    {"$match": {"organization_id": org_id,
                                 "store_id": {"$in": store_ids},
                                 "status": {"$ne": "cancelled"}}},
                    {"$group": {"_id": "$store_id",
                                 "count": {"$sum": 1},
                                 "revenue": {"$sum": {"$ifNull": ["$total", 0]}}}},
                ]):
                    lifetime_agg[doc["_id"]] = {
                        "count": doc["count"],
                        "revenue": round(doc["revenue"], 2),
                    }

                async for doc in orders_collection.aggregate([
                    {"$match": {"organization_id": org_id,
                                 "store_id": {"$in": store_ids},
                                 "status": {"$ne": "cancelled"},
                                 "created_at": {"$gte": cutoff_30d}}},
                    {"$group": {"_id": "$store_id",
                                 "count": {"$sum": 1},
                                 "revenue": {"$sum": {"$ifNull": ["$total", 0]}}}},
                ]):
                    last30d_agg[doc["_id"]] = {
                        "count": doc["count"],
                        "revenue": round(doc["revenue"], 2),
                    }

            stores_out = []
            for s in stores:
                sid = s["id"]
                lifetime = lifetime_agg.get(sid, {"count": 0, "revenue": 0.0})
                last30 = last30d_agg.get(sid, {"count": 0, "revenue": 0.0})
                stores_out.append({
                    "store_id": sid,
                    "name": s.get("name", "Senza nome"),
                    "slug": s.get("slug"),
                    "is_active": s.get("is_active", True),
                    "is_published": s.get("is_published", False),
                    "visibility": s.get("visibility"),
                    "lifetime_orders": lifetime["count"],
                    "lifetime_revenue": lifetime["revenue"],
                    "last_30d_orders": last30["count"],
                    "last_30d_revenue": last30["revenue"],
                })

            # Sort by lifetime revenue
            stores_out.sort(key=lambda s: s["lifetime_revenue"], reverse=True)

            active_count = sum(1 for s in stores_out if s["is_active"])
            published_count = sum(1 for s in stores_out if s["is_published"])
            top_store = stores_out[0]["name"] if stores_out else None

            return {
                "has_data": bool(stores_out),
                "currency": currency,
                "stores": stores_out,
                "total_stores": len(stores_out),
                "active_stores": active_count,
                "published_stores": published_count,
                "top_store_by_revenue": top_store,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "mixed",
                    "note": "Lifetime = tutti gli ordini storici non cancellati. last_30d = ultimi 30 giorni.",
                },
                "analytical_hints": {
                    "interpretation": "Store con published=false ma lifetime_orders > 0 = pubblicato in passato e poi nascosto. Store con last_30d=0 ma lifetime>0 = potenzialmente in standby.",
                },
                "_caveat": None if stores_out else "Nessuno store trovato. Configurare almeno uno store per attivare il commerce.",
            }

        elif tool_name == "query_store_performance":
            from database import stores_collection, orders_collection
            from datetime import date as date_type, datetime as dt, timedelta

            store_id = tool_input["store_id"]
            end = tool_input.get("end_date") or date_type.today().isoformat()
            start = tool_input.get("start_date") or (date_type.fromisoformat(end) - timedelta(days=30)).isoformat()
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # Resolve store name
            store = await stores_collection.find_one(
                {"id": store_id, "organization_id": org_id},
                {"_id": 0, "name": 1, "is_active": 1, "is_published": 1},
            )
            if not store:
                return {
                    "has_data": False,
                    "error": f"Store {store_id} non trovato.",
                    "epistemic": {"epistemic_class": "factual", "reliability": "high",
                                  "ai_usability": "strong", "caveat": None},
                }

            # By-status aggregation for this store
            by_status = {}
            active_revenue = 0.0
            active_count = 0
            total_count = 0
            async for doc in orders_collection.aggregate([
                {"$match": {"organization_id": org_id, "store_id": store_id,
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {"_id": "$status",
                             "count": {"$sum": 1},
                             "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
            ]):
                status = doc["_id"]
                c = doc["count"]
                a = round(doc["amount"], 2)
                by_status[status] = {"count": c, "amount": a}
                total_count += c
                if status != "cancelled":
                    active_revenue += a
                    active_count += c

            # Top 5 products for this store
            top_products = []
            async for doc in orders_collection.aggregate([
                {"$match": {"organization_id": org_id, "store_id": store_id,
                             "status": {"$ne": "cancelled"},
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$unwind": "$items"},
                {"$group": {
                    "_id": {"product_id": "$items.product_id", "name": "$items.product_name"},
                    "units": {"$sum": "$items.quantity"},
                    "revenue": {"$sum": "$items.line_total"},
                }},
                {"$sort": {"revenue": -1}},
                {"$limit": 5},
            ]):
                top_products.append({
                    "product_name": doc["_id"].get("name") or "Sconosciuto",
                    "product_id": doc["_id"].get("product_id"),
                    "units_sold": int(doc["units"]),
                    "revenue": round(doc["revenue"], 2),
                })

            aov = round(active_revenue / active_count, 2) if active_count > 0 else 0

            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": total_count > 0,
                "currency": currency,
                "store": {
                    "store_id": store_id,
                    "name": store.get("name"),
                    "is_active": store.get("is_active", True),
                    "is_published": store.get("is_published", False),
                },
                "total_orders": total_count,
                "active_orders": active_count,
                "active_revenue": round(active_revenue, 2),
                "aov": aov,
                "by_status": by_status,
                "top_products": top_products,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Ordini dello store nel periodo. active = non cancellati.",
                },
                "analytical_hints": {
                    "cross_module": ["Confronta con query_stores_overview per la posizione relativa nello stack."],
                },
                "_caveat": None if total_count > 0 else f"Nessun ordine per lo store {store.get('name')} nel periodo.",
            }

        elif tool_name == "query_catalog_health":
            from database import products_collection

            # Count per problem class via parallel queries
            base_q = {"organization_id": org_id}

            async def _count(extra):
                q = {**base_q, **extra}
                return await products_collection.count_documents(q)

            async def _examples(extra, limit=5):
                q = {**base_q, **extra}
                cursor = products_collection.find(
                    q, {"_id": 0, "id": 1, "name": 1, "sku": 1}
                ).limit(limit)
                return [{"name": d.get("name"), "sku": d.get("sku"), "id": d.get("id")}
                        async for d in cursor]

            total_products = await _count({})
            missing_price_q = {
                "$or": [
                    {"unit_price": None},
                    {"unit_price": {"$exists": False}},
                    {"unit_price": 0},
                ],
                "price_mode": {"$ne": "inquiry"},  # inquiry products legitimately have no price
            }
            missing_cost_q = {
                "$or": [
                    {"cost_price": None},
                    {"cost_price": {"$exists": False}},
                ],
            }
            missing_description_q = {
                "$or": [
                    {"description": None},
                    {"description": ""},
                    {"description": {"$exists": False}},
                ],
            }
            inactive_q = {"is_active": False}

            missing_price = await _count(missing_price_q)
            missing_cost = await _count(missing_cost_q)
            missing_desc = await _count(missing_description_q)
            inactive = await _count(inactive_q)

            examples_missing_price = await _examples(missing_price_q)
            examples_missing_cost = await _examples(missing_cost_q)
            examples_missing_desc = await _examples(missing_description_q)
            examples_inactive = await _examples(inactive_q)

            # Health score: simple weighted sum, lower is worse
            issues = missing_price + missing_cost + missing_desc + inactive
            health_pct = round(max(0.0, 100.0 - (issues / max(total_products, 1) * 25)), 1)

            return {
                "has_data": total_products > 0,
                "total_products": total_products,
                "issues": {
                    "missing_unit_price": {"count": missing_price, "examples": examples_missing_price},
                    "missing_cost_price": {"count": missing_cost, "examples": examples_missing_cost},
                    "missing_description": {"count": missing_desc, "examples": examples_missing_desc},
                    "inactive_products": {"count": inactive, "examples": examples_inactive},
                },
                "health_score_pct": health_pct,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "current_state",
                    "note": "Snapshot attuale dei prodotti registrati.",
                },
                "analytical_hints": {
                    "interpretation": "missing_cost_price = margini non calcolabili. missing_unit_price (non inquiry) = prodotto non vendibile via storefront. missing_description impatta SEO + UX.",
                },
                "_caveat": None if total_products > 0 else "Nessun prodotto registrato.",
            }

        elif tool_name == "query_new_vs_returning_split":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # Step 1: collect distinct customer_account_ids that ordered in the period (non-cancelled)
            period_customer_ids = set()
            async for doc in orders_collection.aggregate([
                {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                             "customer_account_id": {"$ne": None},
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {"_id": "$customer_account_id"}},
            ]):
                period_customer_ids.add(doc["_id"])

            # Step 2: of those, which had a prior non-cancelled order before start_dt?
            returning_ids = set()
            if period_customer_ids:
                async for doc in orders_collection.aggregate([
                    {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                                 "customer_account_id": {"$in": list(period_customer_ids)},
                                 "created_at": {"$lt": start_dt}}},
                    {"$group": {"_id": "$customer_account_id"}},
                ]):
                    returning_ids.add(doc["_id"])
            new_ids = period_customer_ids - returning_ids

            # Step 3: aggregate orders/revenue in period for each bucket
            async def _bucket_stats(match):
                async for doc in orders_collection.aggregate([
                    {"$match": match},
                    {"$group": {"_id": None,
                                 "count": {"$sum": 1},
                                 "revenue": {"$sum": {"$ifNull": ["$total", 0]}}}},
                ]):
                    return doc["count"], round(doc["revenue"], 2)
                return 0, 0.0

            base_match = {"organization_id": org_id, "status": {"$ne": "cancelled"},
                           "created_at": {"$gte": start_dt, "$lt": end_dt}}

            new_count, new_rev = (0, 0.0)
            if new_ids:
                new_count, new_rev = await _bucket_stats({**base_match,
                                                          "customer_account_id": {"$in": list(new_ids)}})
            ret_count, ret_rev = (0, 0.0)
            if returning_ids:
                ret_count, ret_rev = await _bucket_stats({**base_match,
                                                           "customer_account_id": {"$in": list(returning_ids)}})
            guest_count, guest_rev = await _bucket_stats({**base_match,
                                                            "customer_account_id": None})

            total_rev = round(new_rev + ret_rev + guest_rev, 2)
            total_count = new_count + ret_count + guest_count

            def _pct(x):
                return round(x / total_rev * 100, 1) if total_rev > 0 else 0

            has_data = total_count > 0
            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "buckets": {
                    "new": {"orders": new_count, "revenue": new_rev,
                            "revenue_share_pct": _pct(new_rev),
                            "unique_customers": len(new_ids)},
                    "returning": {"orders": ret_count, "revenue": ret_rev,
                                  "revenue_share_pct": _pct(ret_rev),
                                  "unique_customers": len(returning_ids)},
                    "guest": {"orders": guest_count, "revenue": guest_rev,
                              "revenue_share_pct": _pct(guest_rev),
                              "unique_customers": None},  # guests not deduplicable
                },
                "totals": {"orders": total_count, "revenue": total_rev},
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "Guest orders (no customer_account_id) non deduplicabili — il fatturato e' affidabile ma 'unique customers' guest e' null.",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Returning = customer_account_id con almeno un ordine non cancellato prima del periodo. Esclusi cancellati ovunque.",
                },
                "analytical_hints": {
                    "interpretation": "returning share basso (<20%) = retention debole. guest share alto (>50%) = opportunita di account creation per fidelizzare. new share dominante = canale acquisition forte ma fragile.",
                },
                "_caveat": None if has_data else "Nessun ordine nel periodo.",
            }

        elif tool_name == "query_basket_size_distribution":
            from database import orders_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # Compute total quantity per order via items.quantity sum
            pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": {"$ne": "cancelled"},
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$project": {
                    "total": 1,
                    "basket_qty": {"$sum": "$items.quantity"},
                }},
                {"$project": {
                    "total": 1,
                    "bucket": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lte": ["$basket_qty", 1]}, "then": "1_item"},
                                {"case": {"$lte": ["$basket_qty", 3]}, "then": "2-3"},
                                {"case": {"$lte": ["$basket_qty", 5]}, "then": "4-5"},
                            ],
                            "default": "6+",
                        },
                    },
                }},
                {"$group": {
                    "_id": "$bucket",
                    "count": {"$sum": 1},
                    "revenue": {"$sum": {"$ifNull": ["$total", 0]}},
                }},
            ]

            buckets_init = ["1_item", "2-3", "4-5", "6+"]
            buckets = {b: {"orders": 0, "revenue": 0.0} for b in buckets_init}
            async for doc in orders_collection.aggregate(pipeline):
                key = doc["_id"]
                if key in buckets:
                    buckets[key] = {
                        "orders": doc["count"],
                        "revenue": round(doc["revenue"], 2),
                    }

            # Add AOV + share per bucket
            total_orders = sum(b["orders"] for b in buckets.values())
            total_revenue = round(sum(b["revenue"] for b in buckets.values()), 2)
            out_buckets = {}
            for k, v in buckets.items():
                out_buckets[k] = {
                    **v,
                    "aov": round(v["revenue"] / v["orders"], 2) if v["orders"] > 0 else 0,
                    "order_share_pct": round(v["orders"] / total_orders * 100, 1) if total_orders > 0 else 0,
                }

            single_item_share = out_buckets["1_item"]["order_share_pct"]
            multi_item_share = round(100 - single_item_share, 1) if total_orders > 0 else 0

            has_data = total_orders > 0
            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": has_data,
                "currency": currency,
                "buckets": out_buckets,
                "totals": {"orders": total_orders, "revenue": total_revenue},
                "analysis": {
                    "single_item_share_pct": single_item_share,
                    "multi_item_share_pct": multi_item_share,
                    "concentration_note": "single-item heavy" if single_item_share > 70 else "balanced" if single_item_share > 30 else "multi-item heavy",
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Bucket calcolato sulla somma di items.quantity per ordine. Esclusi i cancellati.",
                },
                "analytical_hints": {
                    "interpretation": "single_item_share > 70% = opportunita di bundling/upsell. multi_item_share alto + AOV basso = scontistica eccessiva sui carrelli grandi. Confronta AOV per bucket con il prezzo medio prodotto.",
                },
                "_caveat": None if has_data else "Nessun ordine attivo nel periodo.",
            }

        # ── Wave 7C.1: Calendar A — agenda/servizi ─────────────────────────

        elif tool_name == "query_agenda_today":
            from database import blocked_slots_collection, issued_bookings_collection
            from datetime import date as date_type

            today_str = date_type.today().isoformat()

            # Confirmed bookings for today (status confirmed or completed)
            bookings_cur = issued_bookings_collection.find(
                {"organization_id": org_id,
                 "booking_date": today_str,
                 "status": {"$in": ["confirmed", "completed"]}},
                {"_id": 0, "booking_start_time": 1, "booking_end_time": 1,
                 "service_option_label": 1, "holder_name": 1, "holder_email": 1,
                 "location": 1, "code": 1, "status": 1},
            ).sort("booking_start_time", 1)
            bookings = []
            async for b in bookings_cur:
                bookings.append({
                    "start_time": b.get("booking_start_time"),
                    "end_time": b.get("booking_end_time"),
                    "service": b.get("service_option_label") or "Servizio",
                    "customer": b.get("holder_name") or "—",
                    "location": b.get("location"),
                    "code": b.get("code"),
                    "status": b.get("status"),
                })

            # Agenda-scope blocked slots for today (scope=agenda or null, exclude rental reason)
            blocks_cur = blocked_slots_collection.find(
                {"organization_id": org_id,
                 "date": today_str,
                 "scope": {"$in": [None, "agenda"]},
                 "reason": {"$ne": "rental"}},
                {"_id": 0, "start_time": 1, "end_time": 1, "reason": 1, "note": 1},
            ).sort("start_time", 1)
            blocks = []
            async for b in blocks_cur:
                blocks.append({
                    "start_time": b.get("start_time"),
                    "end_time": b.get("end_time"),
                    "reason": b.get("reason"),
                    "note": b.get("note"),
                })

            # Free-text summary
            confirmed_count = sum(1 for b in bookings if b["status"] == "confirmed")
            first_appt = bookings[0]["start_time"] if bookings else None
            last_appt = bookings[-1]["end_time"] if bookings else None

            return {
                "date": today_str,
                "has_data": bool(bookings or blocks),
                "bookings": bookings,
                "blocks": blocks,
                "summary": {
                    "confirmed_appointments": confirmed_count,
                    "total_appointments": len(bookings),
                    "blocks_count": len(blocks),
                    "first_appointment_at": first_appt,
                    "last_appointment_at": last_appt,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "current_day",
                    "note": "Snapshot di oggi. Cancellati esclusi dalle prenotazioni.",
                },
                "_caveat": None if bookings or blocks else "Giornata libera: nessuna prenotazione ne blocco.",
            }

        elif tool_name == "query_agenda_upcoming":
            from database import issued_bookings_collection, blocked_slots_collection
            from datetime import date as date_type, timedelta

            raw_days = tool_input.get("days_ahead", 7)
            try:
                days_ahead = int(raw_days)
            except (TypeError, ValueError):
                days_ahead = 7
            days_ahead = max(1, min(days_ahead, 30))

            start_date = date_type.today()
            end_date = start_date + timedelta(days=days_ahead - 1)
            start_str = start_date.isoformat()
            end_str = end_date.isoformat()

            # Confirmed + cancelled in range
            bookings_cur = issued_bookings_collection.find(
                {"organization_id": org_id,
                 "booking_date": {"$gte": start_str, "$lte": end_str}},
                {"_id": 0, "booking_date": 1, "booking_start_time": 1,
                 "booking_end_time": 1, "service_option_label": 1,
                 "holder_name": 1, "status": 1, "code": 1},
            ).sort([("booking_date", 1), ("booking_start_time", 1)])

            by_day: dict = {}
            confirmed_total = 0
            cancelled_total = 0
            async for b in bookings_cur:
                d = b.get("booking_date")
                by_day.setdefault(d, {"date": d, "confirmed": 0, "cancelled": 0,
                                       "no_show": 0, "completed": 0,
                                       "top_appointments": []})
                status = b.get("status", "confirmed")
                by_day[d][status] = by_day[d].get(status, 0) + 1
                if status == "confirmed":
                    confirmed_total += 1
                elif status == "cancelled":
                    cancelled_total += 1
                if status in ("confirmed", "completed") and len(by_day[d]["top_appointments"]) < 5:
                    by_day[d]["top_appointments"].append({
                        "start_time": b.get("booking_start_time"),
                        "service": b.get("service_option_label") or "Servizio",
                        "customer": b.get("holder_name") or "—",
                        "code": b.get("code"),
                    })

            # Fill missing days (range may extend beyond what bookings cover)
            days_out = []
            cur = start_date
            while cur <= end_date:
                key = cur.isoformat()
                days_out.append(by_day.get(key, {
                    "date": key, "confirmed": 0, "cancelled": 0,
                    "no_show": 0, "completed": 0, "top_appointments": [],
                }))
                cur += timedelta(days=1)

            busiest_day = max(days_out, key=lambda d: d["confirmed"], default=None)
            busiest_day_name = busiest_day["date"] if busiest_day and busiest_day["confirmed"] > 0 else None

            return {
                "range": {"start_date": start_str, "end_date": end_str,
                          "days_ahead": days_ahead},
                "has_data": confirmed_total + cancelled_total > 0,
                "days": days_out,
                "summary": {
                    "total_confirmed": confirmed_total,
                    "total_cancelled": cancelled_total,
                    "busiest_day": busiest_day_name,
                    "avg_per_day": round(confirmed_total / days_ahead, 1) if days_ahead > 0 else 0,
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "forward_window",
                    "note": f"Prossimi {days_ahead} giorni a partire da oggi.",
                },
                "_caveat": None if confirmed_total + cancelled_total > 0 else "Nessuna prenotazione nei prossimi giorni.",
            }

        elif tool_name == "query_agenda_summary":
            from database import issued_bookings_collection, availability_rules_collection, blocked_slots_collection
            from datetime import date as date_type, timedelta

            today = date_type.today()
            today_str = today.isoformat()
            tomorrow_str = (today + timedelta(days=1)).isoformat()
            week_end = today + timedelta(days=6)
            week_end_str = week_end.isoformat()

            # Aggregate by status across 3 windows
            async def _counts_for_range(start_s, end_s):
                pipeline = [
                    {"$match": {"organization_id": org_id,
                                 "booking_date": {"$gte": start_s, "$lte": end_s}}},
                    {"$group": {"_id": "$status", "n": {"$sum": 1}}},
                ]
                out = {"confirmed": 0, "completed": 0, "cancelled": 0, "no_show": 0}
                async for d in issued_bookings_collection.aggregate(pipeline):
                    out[d["_id"]] = d["n"]
                return out

            today_counts = await _counts_for_range(today_str, today_str)
            tomorrow_counts = await _counts_for_range(tomorrow_str, tomorrow_str)
            week_counts = await _counts_for_range(today_str, week_end_str)

            # Today free slots calculation (rules - blocks - bookings)
            rules = await availability_rules_collection.find(
                {"organization_id": org_id, "is_active": True}, {"_id": 0}
            ).to_list(100)
            today_dow = today.weekday()
            today_total_slots = sum(
                _slots_from_rule(r["start_time"], r["end_time"],
                                 r.get("slot_duration_minutes", 60))
                for r in rules if r.get("day_of_week") == today_dow
            )

            # Count today's bookings + agenda-scope blocks
            today_taken = today_counts["confirmed"] + today_counts["completed"]
            today_block_count = await blocked_slots_collection.count_documents(
                {"organization_id": org_id, "date": today_str,
                 "scope": {"$in": [None, "agenda"]},
                 "reason": {"$nin": ["rental", "booking"]}},
            )
            free_today = max(0, today_total_slots - today_taken - today_block_count)

            return {
                "as_of": today_str,
                "today": {**today_counts, "total": sum(today_counts.values())},
                "tomorrow": {**tomorrow_counts, "total": sum(tomorrow_counts.values())},
                "this_week": {**week_counts, "total": sum(week_counts.values())},
                "free_slots_today": free_today,
                "today_total_slots": today_total_slots,
                "has_data": (sum(today_counts.values()) + sum(tomorrow_counts.values())
                             + sum(week_counts.values()) > 0),
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "free_slots_today = slot da regole meno appuntamenti meno blocchi non-booking. Approssimazione: non considera blocchi parziali entro slot.",
                },
                "temporal_context": {
                    "scope": "current_day_plus_window",
                    "note": "Today = oggi. Tomorrow = domani. This_week = prossimi 7 giorni (oggi incluso).",
                },
                "_caveat": None,
            }

        elif tool_name == "query_free_slots":
            from database import availability_rules_collection, blocked_slots_collection, issued_bookings_collection
            from datetime import date as date_type, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            d_start = date_type.fromisoformat(start)
            d_end = date_type.fromisoformat(end)
            days = (d_end - d_start).days + 1
            if days > 30:
                return {"error": "Intervallo massimo 30 giorni per query_free_slots."}
            if days < 1:
                return {"error": "end_date deve essere >= start_date."}

            rules = await availability_rules_collection.find(
                {"organization_id": org_id, "is_active": True}, {"_id": 0}
            ).to_list(100)
            rules_by_dow: dict = {}
            for r in rules:
                rules_by_dow.setdefault(r.get("day_of_week"), []).append(r)

            # Pre-count agenda blocks per date (excluding rental + booking which we count separately)
            blocks_count: dict = {}
            async for b in blocked_slots_collection.find(
                {"organization_id": org_id,
                 "date": {"$gte": start, "$lte": end},
                 "scope": {"$in": [None, "agenda"]},
                 "reason": {"$nin": ["rental", "booking"]}},
                {"_id": 0, "date": 1},
            ):
                blocks_count[b["date"]] = blocks_count.get(b["date"], 0) + 1

            # Pre-count confirmed/completed bookings per date
            bookings_count: dict = {}
            pipeline = [
                {"$match": {"organization_id": org_id,
                             "booking_date": {"$gte": start, "$lte": end},
                             "status": {"$in": ["confirmed", "completed"]}}},
                {"$group": {"_id": "$booking_date", "n": {"$sum": 1}}},
            ]
            async for doc in issued_bookings_collection.aggregate(pipeline):
                bookings_count[doc["_id"]] = doc["n"]

            days_out = []
            total_free = 0
            total_slots_all = 0
            cur = d_start
            while cur <= d_end:
                date_str = cur.isoformat()
                day_rules = rules_by_dow.get(cur.weekday(), [])
                day_slots = sum(
                    _slots_from_rule(r["start_time"], r["end_time"],
                                     r.get("slot_duration_minutes", 60))
                    for r in day_rules
                )
                day_blocked = blocks_count.get(date_str, 0)
                day_booked = bookings_count.get(date_str, 0)
                day_free = max(0, day_slots - day_blocked - day_booked)

                first_free = day_rules[0]["start_time"] if day_rules and day_free > 0 else None
                last_free = day_rules[-1]["end_time"] if day_rules and day_free > 0 else None

                days_out.append({
                    "date": date_str,
                    "day_of_week": cur.weekday(),
                    "total_slots": day_slots,
                    "free_slots": day_free,
                    "booked_slots": day_booked,
                    "blocked_count": day_blocked,
                    "approximate_first_free": first_free,
                    "approximate_last_free": last_free,
                })
                total_free += day_free
                total_slots_all += day_slots
                cur += timedelta(days=1)

            utilization = round((1 - total_free / total_slots_all) * 100, 1) if total_slots_all > 0 else 0
            busiest = min(days_out, key=lambda d: d["free_slots"], default=None) if days_out else None
            emptiest = max(days_out, key=lambda d: d["free_slots"], default=None) if days_out else None

            return {
                "period": {"start_date": start, "end_date": end, "days": days},
                "has_data": total_slots_all > 0,
                "days": days_out,
                "summary": {
                    "total_free_slots": total_free,
                    "total_capacity_slots": total_slots_all,
                    "utilization_pct": utilization,
                    "busiest_day": busiest["date"] if busiest and total_slots_all > 0 else None,
                    "emptiest_day": emptiest["date"] if emptiest and total_slots_all > 0 else None,
                },
                "epistemic": {
                    "epistemic_class": "derived", "reliability": "medium",
                    "ai_usability": "partial",
                    "caveat": "Slot calcolati dalle regole weekly. approximate_first_free e' l'inizio della prima fascia con capacita residua, NON necessariamente il primo slot effettivamente libero (puo' essere prenotato all'interno).",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Free = slot da regole - blocchi (scope agenda) - prenotazioni confermate.",
                },
                "_caveat": None if total_slots_all > 0 else "Nessuna regola di disponibilita attiva nel periodo.",
            }

        elif tool_name == "query_blocked_periods":
            from database import blocked_slots_collection

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            reason_filter = tool_input.get("reason")

            query: dict = {
                "organization_id": org_id,
                "date": {"$gte": start, "$lte": end},
                "scope": {"$in": [None, "agenda"]},
                "reason": {"$ne": "rental"},
            }
            if reason_filter in ("personal", "holiday", "booking", "event"):
                query["reason"] = reason_filter

            cursor = blocked_slots_collection.find(
                query,
                {"_id": 0, "date": 1, "start_time": 1, "end_time": 1,
                 "reason": 1, "note": 1, "product_id": 1},
            ).sort([("date", 1), ("start_time", 1)])

            periods = []
            by_reason: dict = {}
            async for b in cursor:
                r = b.get("reason", "personal")
                by_reason[r] = by_reason.get(r, 0) + 1
                periods.append({
                    "date": b.get("date"),
                    "start_time": b.get("start_time"),
                    "end_time": b.get("end_time"),
                    "reason": r,
                    "note": b.get("note"),
                })

            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": bool(periods),
                "periods": periods,
                "total_blocks": len(periods),
                "by_reason": by_reason,
                "filter_applied": reason_filter,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Blocchi con scope agenda o globali. Esclusi i blocchi rental.",
                },
                "analytical_hints": {
                    "interpretation": "reason=booking = prenotazioni che hanno generato blocco. holiday = ferie. personal = blocchi manuali. event = blocchi da eventi pubblici.",
                },
                "_caveat": None if periods else "Nessun blocco agenda nel periodo.",
            }

        # ── Wave 7C.2: Calendar B — rentals (asset-level) ──────────────────

        elif tool_name == "query_rentals_today":
            from database import issued_reservations_collection
            from datetime import date as date_type

            today_str = date_type.today().isoformat()

            # Match active reservations covering today.
            # Range: date_from <= today <= date_to
            # Slot: slot_date == today
            cursor = issued_reservations_collection.find(
                {"organization_id": org_id,
                 "status": "active",
                 "$or": [
                     {"reservation_flavor": "range",
                      "date_from": {"$lte": today_str},
                      "date_to": {"$gte": today_str}},
                     {"reservation_flavor": "slot",
                      "slot_date": today_str},
                 ]},
                {"_id": 0, "product_id": 1, "product_name": 1,
                 "reservation_flavor": 1, "date_from": 1, "date_to": 1,
                 "slot_date": 1, "slot_start_time": 1, "slot_end_time": 1,
                 "code": 1, "holder_name": 1, "holder_email": 1},
            )
            rentals = []
            async for r in cursor:
                flavor = r.get("reservation_flavor")
                entry = {
                    "product_id": r.get("product_id"),
                    "product_name": r.get("product_name", "Asset"),
                    "flavor": flavor,
                    "customer": r.get("holder_name") or "—",
                    "code": r.get("code"),
                }
                if flavor == "range":
                    entry["date_from"] = r.get("date_from")
                    entry["date_to"] = r.get("date_to")
                    # Days remaining for this rental
                    try:
                        de = date_type.fromisoformat(r["date_to"])
                        entry["days_remaining"] = (de - date_type.today()).days
                    except (ValueError, TypeError, KeyError):
                        entry["days_remaining"] = None
                else:  # slot
                    entry["slot_date"] = r.get("slot_date")
                    entry["start_time"] = r.get("slot_start_time")
                    entry["end_time"] = r.get("slot_end_time")
                rentals.append(entry)

            by_flavor = {"range": 0, "slot": 0}
            for r in rentals:
                by_flavor[r["flavor"]] = by_flavor.get(r["flavor"], 0) + 1

            return {
                "date": today_str,
                "has_data": bool(rentals),
                "rentals": rentals,
                "total_active": len(rentals),
                "by_flavor": by_flavor,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "current_day",
                    "note": "Rental con status=active che coprono oggi. Range = date_from <= oggi <= date_to. Slot = slot_date = oggi.",
                },
                "_caveat": None if rentals else "Nessun asset a noleggio oggi.",
            }

        elif tool_name == "query_rentals_upcoming":
            from database import issued_reservations_collection
            from datetime import date as date_type, timedelta

            raw = tool_input.get("days_ahead", 7)
            try:
                days_ahead = int(raw)
            except (TypeError, ValueError):
                days_ahead = 7
            days_ahead = max(1, min(days_ahead, 60))

            today = date_type.today()
            end_date = today + timedelta(days=days_ahead)
            today_str = today.isoformat()
            end_str = end_date.isoformat()

            cursor = issued_reservations_collection.find(
                {"organization_id": org_id,
                 "status": "active",
                 "$or": [
                     {"reservation_flavor": "range",
                      "date_from": {"$gt": today_str, "$lte": end_str}},
                     {"reservation_flavor": "slot",
                      "slot_date": {"$gt": today_str, "$lte": end_str}},
                 ]},
                {"_id": 0, "product_id": 1, "product_name": 1,
                 "reservation_flavor": 1, "date_from": 1, "date_to": 1,
                 "slot_date": 1, "slot_start_time": 1, "slot_end_time": 1,
                 "code": 1, "holder_name": 1},
            )
            rentals = []
            async for r in cursor:
                flavor = r.get("reservation_flavor")
                start_field = r.get("date_from") if flavor == "range" else r.get("slot_date")
                try:
                    days_until = (date_type.fromisoformat(start_field) - today).days
                except (ValueError, TypeError):
                    days_until = None
                entry = {
                    "product_id": r.get("product_id"),
                    "product_name": r.get("product_name", "Asset"),
                    "flavor": flavor,
                    "customer": r.get("holder_name") or "—",
                    "code": r.get("code"),
                    "days_until": days_until,
                    "start_date": start_field,
                }
                if flavor == "range":
                    entry["date_to"] = r.get("date_to")
                else:
                    entry["start_time"] = r.get("slot_start_time")
                    entry["end_time"] = r.get("slot_end_time")
                rentals.append(entry)

            rentals.sort(key=lambda r: (r.get("days_until") or 0, r["start_date"] or ""))

            next_rental = rentals[0] if rentals else None
            return {
                "range": {"start_date": today_str, "end_date": end_str,
                          "days_ahead": days_ahead},
                "has_data": bool(rentals),
                "rentals": rentals,
                "total_upcoming": len(rentals),
                "next_rental": {
                    "product_name": next_rental["product_name"],
                    "start_date": next_rental["start_date"],
                    "days_until": next_rental["days_until"],
                } if next_rental else None,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "forward_window",
                    "note": f"Rental con inizio dopo oggi nei prossimi {days_ahead} giorni.",
                },
                "_caveat": None if rentals else "Nessun noleggio futuro in arrivo.",
            }

        elif tool_name == "query_rentals_returning":
            from database import issued_reservations_collection
            from datetime import date as date_type, timedelta

            raw = tool_input.get("days_ahead", 7)
            try:
                days_ahead = int(raw)
            except (TypeError, ValueError):
                days_ahead = 7
            days_ahead = max(1, min(days_ahead, 30))

            today = date_type.today()
            end_date = today + timedelta(days=days_ahead)
            today_str = today.isoformat()
            end_str = end_date.isoformat()

            # Range rentals ending in window
            cursor = issued_reservations_collection.find(
                {"organization_id": org_id,
                 "status": "active",
                 "reservation_flavor": "range",
                 "date_to": {"$gte": today_str, "$lte": end_str}},
                {"_id": 0, "product_id": 1, "product_name": 1,
                 "date_from": 1, "date_to": 1,
                 "code": 1, "holder_name": 1},
            ).sort("date_to", 1)

            returning = []
            async for r in cursor:
                try:
                    days_until = (date_type.fromisoformat(r["date_to"]) - today).days
                except (ValueError, TypeError, KeyError):
                    days_until = None
                returning.append({
                    "product_id": r.get("product_id"),
                    "product_name": r.get("product_name", "Asset"),
                    "customer": r.get("holder_name") or "—",
                    "code": r.get("code"),
                    "date_from": r.get("date_from"),
                    "date_to": r.get("date_to"),
                    "days_until_return": days_until,
                })

            today_returns = sum(1 for r in returning if r.get("days_until_return") == 0)
            tomorrow_returns = sum(1 for r in returning if r.get("days_until_return") == 1)

            return {
                "range": {"start_date": today_str, "end_date": end_str,
                          "days_ahead": days_ahead},
                "has_data": bool(returning),
                "returning": returning,
                "total_returning": len(returning),
                "returning_today": today_returns,
                "returning_tomorrow": tomorrow_returns,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "forward_window",
                    "note": "Solo rental range con date_to nel periodo. Slot rental sono single-day quindi non rientrano qui.",
                },
                "analytical_hints": {
                    "interpretation": "returning_today + returning_tomorrow = volume operativo immediato per ritiro/sanificazione/controllo.",
                },
                "_caveat": None if returning else "Nessun asset in rientro nei prossimi giorni.",
            }

        elif tool_name == "query_rental_availability":
            from database import issued_reservations_collection, products_collection
            from datetime import date as date_type, timedelta

            product_id = tool_input["product_id"]
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            d_start = date_type.fromisoformat(start)
            d_end = date_type.fromisoformat(end)
            days = (d_end - d_start).days + 1
            if days > 30:
                return {"error": "Intervallo massimo 30 giorni per query_rental_availability."}
            if days < 1:
                return {"error": "end_date deve essere >= start_date."}

            # Resolve product name
            product = await products_collection.find_one(
                {"id": product_id, "organization_id": org_id},
                {"_id": 0, "name": 1},
            )
            if not product:
                return {
                    "has_data": False,
                    "error": f"Asset {product_id} non trovato.",
                    "epistemic": {"epistemic_class": "factual", "reliability": "high",
                                  "ai_usability": "strong", "caveat": None},
                }

            # Active reservations overlapping the window
            overlap_cursor = issued_reservations_collection.find(
                {"organization_id": org_id,
                 "product_id": product_id,
                 "status": "active",
                 "$or": [
                     {"reservation_flavor": "range",
                      "date_from": {"$lte": end},
                      "date_to": {"$gte": start}},
                     {"reservation_flavor": "slot",
                      "slot_date": {"$gte": start, "$lte": end}},
                 ]},
                {"_id": 0, "reservation_flavor": 1,
                 "date_from": 1, "date_to": 1, "slot_date": 1,
                 "slot_start_time": 1, "slot_end_time": 1,
                 "code": 1, "holder_name": 1},
            )
            bookings = []
            async for r in overlap_cursor:
                bookings.append(r)

            # Build per-day occupancy
            booked_dates = set()
            for r in bookings:
                if r.get("reservation_flavor") == "range":
                    try:
                        df = date_type.fromisoformat(r["date_from"])
                        dt_ = date_type.fromisoformat(r["date_to"])
                    except (ValueError, TypeError, KeyError):
                        continue
                    # Mark every day from df to dt as booked within window
                    cur = max(df, d_start)
                    last = min(dt_, d_end)
                    while cur <= last:
                        booked_dates.add(cur.isoformat())
                        cur += timedelta(days=1)
                elif r.get("reservation_flavor") == "slot":
                    sd = r.get("slot_date")
                    if sd and d_start <= date_type.fromisoformat(sd) <= d_end:
                        booked_dates.add(sd)

            days_out = []
            free_count = 0
            cur = d_start
            while cur <= d_end:
                ds = cur.isoformat()
                is_booked = ds in booked_dates
                if not is_booked:
                    free_count += 1
                days_out.append({"date": ds, "day_of_week": cur.weekday(), "booked": is_booked})
                cur += timedelta(days=1)

            booked_count = days - free_count
            utilization = round(booked_count / days * 100, 1) if days > 0 else 0

            return {
                "period": {"start_date": start, "end_date": end, "days": days},
                "has_data": True,
                "product": {"id": product_id, "name": product.get("name")},
                "days": days_out,
                "summary": {
                    "free_days": free_count,
                    "booked_days": booked_count,
                    "utilization_pct": utilization,
                },
                "active_reservations_in_window": len(bookings),
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "Slot rental in mezzo a un giorno marcano l'intera giornata come booked. Per dettagli orari, vedere il calendario.",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Booked = il giorno e' coperto da almeno una reservation active per l'asset.",
                },
                "_caveat": None,
            }

        elif tool_name == "query_rental_pipeline":
            from database import issued_reservations_collection
            from datetime import date as date_type, timedelta

            raw = tool_input.get("days_ahead", 30)
            try:
                days_ahead = int(raw)
            except (TypeError, ValueError):
                days_ahead = 30
            days_ahead = max(1, min(days_ahead, 90))

            today = date_type.today()
            end_date = today + timedelta(days=days_ahead)
            today_str = today.isoformat()
            end_str = end_date.isoformat()

            # Aggregate future rentals by product_id
            pipeline = [
                {"$match": {
                    "organization_id": org_id,
                    "status": "active",
                    "$or": [
                        {"reservation_flavor": "range",
                         "date_from": {"$gt": today_str, "$lte": end_str}},
                        {"reservation_flavor": "slot",
                         "slot_date": {"$gt": today_str, "$lte": end_str}},
                    ],
                }},
                {"$group": {
                    "_id": {"product_id": "$product_id",
                            "product_name": "$product_name"},
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]

            top_assets = []
            total_future = 0
            async for doc in issued_reservations_collection.aggregate(pipeline):
                top_assets.append({
                    "product_id": doc["_id"].get("product_id"),
                    "product_name": doc["_id"].get("product_name", "Asset"),
                    "future_rentals_count": doc["count"],
                })
                total_future += doc["count"]

            # Find earliest upcoming reservation for the headline
            earliest = None
            cursor = issued_reservations_collection.find(
                {"organization_id": org_id, "status": "active",
                 "$or": [
                     {"reservation_flavor": "range", "date_from": {"$gt": today_str, "$lte": end_str}},
                     {"reservation_flavor": "slot", "slot_date": {"$gt": today_str, "$lte": end_str}},
                 ]},
                {"_id": 0, "product_name": 1, "reservation_flavor": 1,
                 "date_from": 1, "slot_date": 1, "holder_name": 1},
            ).sort([("date_from", 1), ("slot_date", 1)]).limit(1)
            async for r in cursor:
                start_field = r.get("date_from") if r.get("reservation_flavor") == "range" else r.get("slot_date")
                try:
                    days_until = (date_type.fromisoformat(start_field) - today).days
                except (ValueError, TypeError):
                    days_until = None
                earliest = {
                    "product_name": r.get("product_name"),
                    "customer": r.get("holder_name") or "—",
                    "start_date": start_field,
                    "days_until": days_until,
                }

            return {
                "range": {"start_date": today_str, "end_date": end_str,
                          "days_ahead": days_ahead},
                "has_data": total_future > 0,
                "total_future_rentals": total_future,
                "top_assets_by_volume": top_assets,
                "next_rental": earliest,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong", "caveat": None,
                },
                "temporal_context": {
                    "scope": "forward_window",
                    "note": f"Rental con inizio dopo oggi nei prossimi {days_ahead} giorni.",
                },
                "analytical_hints": {
                    "interpretation": "top_assets per future_rentals_count = portafoglio asset piu richiesto in arrivo. Confronta con query_rental_utilization (storico) per capire crescita o stagionalita.",
                },
                "_caveat": None if total_future > 0 else "Nessun noleggio futuro in pipeline.",
            }

        # ── Wave 7C.3: Events calendar (operational view) ──────────────────

        elif tool_name == "query_events_calendar":
            from database import orders_collection
            eo_coll = __import__("database", fromlist=["db"]).db.event_occurrences
            from datetime import date as date_type, timedelta

            raw = tool_input.get("days_ahead", 14)
            try:
                days_ahead = int(raw)
            except (TypeError, ValueError):
                days_ahead = 14
            days_ahead = max(1, min(days_ahead, 60))
            include_past = bool(tool_input.get("include_past", False))

            today = date_type.today()
            end_date = today + timedelta(days=days_ahead)
            today_str = today.isoformat()
            end_str = end_date.isoformat()

            occ_query: dict = {"organization_id": org_id, "status": "published"}
            if include_past:
                # Stretch back 7 days for "events I just had"
                back_str = (today - timedelta(days=7)).isoformat()
                occ_query["start_at"] = {"$gte": back_str + "T00:00:00",
                                          "$lte": end_str + "T23:59:59"}
            else:
                occ_query["start_at"] = {"$gte": today_str + "T00:00:00",
                                          "$lte": end_str + "T23:59:59"}

            occ_list = await eo_coll.find(
                occ_query,
                {"_id": 0, "id": 1, "product_name": 1, "start_at": 1,
                 "location": 1, "capacity": 1, "status": 1},
            ).sort("start_at", 1).to_list(200)
            occ_ids = [o["id"] for o in occ_list]

            # Booked counts per occurrence via orders (active, non-cancelled)
            booked_map = {}
            if occ_ids:
                pipeline = [
                    {"$match": {"organization_id": org_id,
                                 "status": {"$ne": "cancelled"},
                                 "items.occurrence_id": {"$in": occ_ids}}},
                    {"$unwind": "$items"},
                    {"$match": {"items.occurrence_id": {"$in": occ_ids}}},
                    {"$group": {"_id": "$items.occurrence_id",
                                "booked": {"$sum": "$items.quantity"}}},
                ]
                async for doc in orders_collection.aggregate(pipeline):
                    booked_map[doc["_id"]] = int(doc["booked"])

            events = []
            future_events = 0
            past_events = 0
            for occ in occ_list:
                cap = occ.get("capacity")
                booked = booked_map.get(occ["id"], 0)
                fill = round(booked / cap * 100, 1) if cap and cap > 0 else None
                start_at = occ.get("start_at", "")
                date_part = start_at[:10] if start_at else ""
                try:
                    days_until = (date_type.fromisoformat(date_part) - today).days
                except (ValueError, TypeError):
                    days_until = None

                if days_until is not None and days_until < 0:
                    past_events += 1
                else:
                    future_events += 1

                events.append({
                    "event_id": occ["id"],
                    "name": occ.get("product_name", "Evento"),
                    "date": date_part,
                    "time": start_at[11:16] if len(start_at) > 11 else None,
                    "location": occ.get("location"),
                    "capacity": cap,
                    "booked": booked,
                    "fill_rate_pct": fill,
                    "days_until": days_until,
                    "status_label": "past" if (days_until is not None and days_until < 0)
                                     else "today" if days_until == 0
                                     else "upcoming",
                })

            next_event = None
            for ev in events:
                if ev["days_until"] is not None and ev["days_until"] >= 0:
                    next_event = {"name": ev["name"], "date": ev["date"],
                                  "days_until": ev["days_until"],
                                  "booked": ev["booked"], "capacity": ev["capacity"]}
                    break

            return {
                "range": {"start_date": today_str if not include_past else (today - timedelta(days=7)).isoformat(),
                          "end_date": end_str, "days_ahead": days_ahead,
                          "include_past": include_past},
                "has_data": bool(events),
                "events": events,
                "total_events": len(events),
                "future_events": future_events,
                "past_events": past_events,
                "next_event": next_event,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "fill_rate disponibile solo per eventi con capacity definita." if any(e["capacity"] is None for e in events) else None,
                },
                "temporal_context": {
                    "scope": "forward_window" if not include_past else "past_plus_forward",
                    "note": f"Eventi published nei prossimi {days_ahead} giorni. include_past=True estende a 7 giorni nel passato.",
                },
                "analytical_hints": {
                    "cross_module": [
                        "Per metriche di fill_rate + ricavi vedere query_event_metrics",
                        "Per eventi sottoperformanti vedere query_underperforming_events (catalog-level)",
                    ],
                    "interpretation": "fill_rate basso e days_until basso = azione urgente (promozione, reminder). events senza capacity = eventi a registrazione libera.",
                },
                "_caveat": None if events else "Nessun evento pubblicato nel periodo.",
            }

        # ── Wave 7D: coupons + courses ─────────────────────────────────────

        elif tool_name == "query_coupon_usage":
            from database import coupons_collection, orders_collection

            include_inactive = bool(tool_input.get("include_inactive", False))
            start = tool_input.get("start_date")
            end = tool_input.get("end_date")

            coupon_query: dict = {"organization_id": org_id}
            if not include_inactive:
                coupon_query["is_active"] = {"$ne": False}

            coupons = await coupons_collection.find(
                coupon_query,
                {"_id": 0, "id": 1, "code": 1, "discount_pct": 1,
                 "discount_amount": 1, "current_uses": 1, "max_uses": 1,
                 "is_active": 1, "valid_from": 1, "valid_to": 1},
            ).to_list(length=200)

            # Aggregate discount_total from orders per coupon_code in window
            order_match: dict = {
                "organization_id": org_id,
                "coupon_code": {"$ne": None, "$exists": True},
                "status": {"$ne": "cancelled"},
            }
            if start or end:
                from datetime import datetime as dt, timedelta
                created_filter: dict = {}
                if start:
                    created_filter["$gte"] = dt.strptime(start, "%Y-%m-%d")
                if end:
                    created_filter["$lt"] = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                order_match["created_at"] = created_filter

            discount_by_code: dict = {}
            uses_by_code: dict = {}
            async for doc in orders_collection.aggregate([
                {"$match": order_match},
                {"$group": {
                    "_id": {"$toUpper": "$coupon_code"},
                    "discount": {"$sum": {"$ifNull": ["$discount_total", 0]}},
                    "uses": {"$sum": 1},
                }},
            ]):
                code_up = doc["_id"]
                discount_by_code[code_up] = round(doc["discount"], 2)
                uses_by_code[code_up] = doc["uses"]

            coupons_out = []
            for c in coupons:
                code_up = (c.get("code") or "").upper()
                in_window_uses = uses_by_code.get(code_up, 0)
                discount_total = discount_by_code.get(code_up, 0)
                max_uses = c.get("max_uses")
                usage_pct = round(c.get("current_uses", 0) / max_uses * 100, 1) if max_uses else None
                coupons_out.append({
                    "id": c.get("id"),
                    "code": c.get("code"),
                    "is_active": c.get("is_active", True),
                    "discount_pct": c.get("discount_pct"),
                    "discount_amount": c.get("discount_amount"),
                    "current_uses_lifetime": c.get("current_uses", 0),
                    "max_uses": max_uses,
                    "usage_quota_pct": usage_pct,
                    "uses_in_window": in_window_uses,
                    "discount_granted_in_window": discount_total,
                    "valid_from": c.get("valid_from"),
                    "valid_to": c.get("valid_to"),
                })

            # Sort by discount granted in window desc
            coupons_out.sort(key=lambda x: x["discount_granted_in_window"], reverse=True)

            total_discount = round(sum(c["discount_granted_in_window"] for c in coupons_out), 2)
            top_coupon = coupons_out[0]["code"] if coupons_out and coupons_out[0]["discount_granted_in_window"] > 0 else None

            return {
                "has_data": bool(coupons_out),
                "currency": currency,
                "window": {"start_date": start, "end_date": end} if (start or end) else {"scope": "lifetime"},
                "coupons": coupons_out,
                "total_coupons": len(coupons_out),
                "total_discount_granted": total_discount,
                "top_coupon_by_discount": top_coupon,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "Discount_granted = somma di order.discount_total su ordini non cancellati. Le righe del coupon stesso (current_uses) sono cumulative lifetime, non filtrate per finestra.",
                },
                "temporal_context": {
                    "scope": "period_filtered" if (start or end) else "lifetime",
                    "note": "discount_granted_in_window e' filtrato per data. usage_quota_pct e' su current_uses/max_uses (lifetime).",
                },
                "analytical_hints": {
                    "interpretation": "discount_granted > 20% del fatturato totale = aggressivita promozionale alta. usage_quota_pct > 80% su coupon attivi = considera estensione max_uses o nuova promo.",
                },
                "_caveat": None if coupons_out else "Nessun coupon configurato (o tutti inattivi se include_inactive=false).",
            }

        elif tool_name == "query_course_engagement":
            from database import courses_collection, issued_course_accesses_collection
            from datetime import datetime as dt, timedelta

            raw_limit = tool_input.get("limit", 10)
            try:
                limit = max(1, min(int(raw_limit), 50))
            except (TypeError, ValueError):
                limit = 10

            courses = await courses_collection.find(
                {"organization_id": org_id, "is_active": {"$ne": False}},
                {"_id": 0, "id": 1, "title": 1, "is_published": 1},
            ).to_list(length=200)

            # Aggregate enrollments per course
            cutoff_recent = dt.utcnow() - timedelta(days=30)
            now = dt.utcnow()

            enrollment_pipeline = [
                {"$match": {"organization_id": org_id}},
                {"$group": {
                    "_id": "$course_id",
                    "total_enrolled": {"$sum": 1},
                    "active_enrolled": {"$sum": {"$cond": [
                        {"$and": [
                            {"$eq": [{"$ifNull": ["$revoked_at", None]}, None]},
                            {"$or": [
                                {"$eq": [{"$ifNull": ["$expires_at", None]}, None]},
                                {"$gt": ["$expires_at", now]},
                            ]},
                        ]},
                        1, 0,
                    ]}},
                    "recent_access_count": {"$sum": {"$cond": [
                        {"$and": [
                            {"$ne": [{"$ifNull": ["$last_accessed_at", None]}, None]},
                            {"$gte": ["$last_accessed_at", cutoff_recent]},
                        ]},
                        1, 0,
                    ]}},
                }},
            ]
            stats_by_course: dict = {}
            async for doc in issued_course_accesses_collection.aggregate(enrollment_pipeline):
                stats_by_course[doc["_id"]] = {
                    "total_enrolled": doc["total_enrolled"],
                    "active_enrolled": doc["active_enrolled"],
                    "recent_access_count": doc["recent_access_count"],
                }

            courses_out = []
            for c in courses:
                s = stats_by_course.get(c["id"], {"total_enrolled": 0,
                                                   "active_enrolled": 0,
                                                   "recent_access_count": 0})
                engagement_pct = round(s["recent_access_count"] / s["active_enrolled"] * 100, 1) if s["active_enrolled"] > 0 else 0
                courses_out.append({
                    "course_id": c["id"],
                    "title": c.get("title", "Senza titolo"),
                    "is_published": c.get("is_published", False),
                    "total_enrolled": s["total_enrolled"],
                    "active_enrolled": s["active_enrolled"],
                    "recent_active_30d": s["recent_access_count"],
                    "engagement_30d_pct": engagement_pct,
                })

            courses_out.sort(key=lambda x: x["total_enrolled"], reverse=True)
            courses_out = courses_out[:limit]

            total_enrolled_all = sum(c["total_enrolled"] for c in courses_out)
            top_course = courses_out[0]["title"] if courses_out and courses_out[0]["total_enrolled"] > 0 else None

            return {
                "has_data": total_enrolled_all > 0,
                "courses": courses_out,
                "total_courses": len(courses_out),
                "total_enrollments": total_enrolled_all,
                "top_course_by_enrollments": top_course,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "active_enrolled = non revocato + non scaduto. engagement_30d_pct = accessi negli ultimi 30 giorni su attivi (puo' essere > 0 anche per corsi che il cliente sta consumando lentamente).",
                },
                "temporal_context": {
                    "scope": "mixed",
                    "note": "Iscritti totali = lifetime. recent_active_30d = ultimi 30 giorni.",
                },
                "analytical_hints": {
                    "interpretation": "engagement_30d_pct basso (< 20%) su corsi recenti = problema di completion / drop-off. corso con active_enrolled grande e recent=0 = abbandono di massa.",
                },
                "_caveat": None if total_enrolled_all > 0 else "Nessun iscritto trovato. I corsi sono configurati ma non venduti.",
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except KeyError as exc:
        logger.warning("commerce ai_tools: %s missing required input: %s", tool_name, exc)
        return {"error": f"Missing required parameter: {exc}"}
    except Exception as exc:
        logger.error("commerce ai_tools: %s failed: %s", tool_name, exc, exc_info=True)
        return {"error": str(exc)}
