# AI Module Baseline — 2026-05-15 (Wave 0)

Snapshot misurabile dello stato del modulo AI **prima** dell'inizio del piano di consolidamento (Wave 1-6). Ogni metrica qui è il punto di riferimento per misurare l'impatto netto del refactor.

## 1. Surface area — SLOC dei file core

### Layer 1 — Platform/Service (servizi AI condivisi)

| File | SLOC | Ruolo |
|---|---|---|
| `services/chat_service.py` | **530** | Chat orchestrator + prompt builder + tool dispatch + persistence |
| `services/claude_client.py` | **319** | LLM client wrapper (Anthropic-specific) |
| `services/ai_tool_registry.py` | **147** | Tool collection da moduli + Anthropic format conversion |
| `services/business_summary.py` | **307** | Cross-module summary + reasoning contract |
| `services/ai_insight_service.py` | **99** | Single-shot insight generation |
| `repositories/usage_repository.py` | **121** | Usage event persistence |
| `repositories/chat_session_repository.py` | **116** | Session persistence (MongoDB TTL-based) |
| `routers/chat.py` | **232** | Endpoints (sessions, history, chat, access-status) |
| `routers/ai_store.py` | ~250 | Store setup AI endpoints (used by frontend wizard) |
| `models/ai_usage.py` | **26** | AIUsageEvent model |
| **Subtotal Layer 1** | **~2147** | |

### Layer 2 — Modules (per-module AI tools + builders)

| File | SLOC | Ruolo |
|---|---|---|
| `modules/cashflow_monitor/ai_tools.py` | **1893** | Tool registry + executors per cashflow |
| `modules/cashflow_monitor/digest_builder.py` | **564** | Digest narrative builder (uses LLM) |
| `modules/cashflow_monitor/digest_report_builder.py` | **309** | Digest PDF report (uses LLM) — overlap con sopra? |
| `modules/cashflow_monitor/health_explanation.py` | **244** | AI explanation per health score |
| `modules/cashflow_monitor/alert_analysis.py` | **109** | AI "why this alert?" |
| `modules/customer_insights/ai_tools.py` | **498** | Tools per customer analysis |
| `modules/commerce_signals/ai_tools.py` | **133** | Tools per commerce signals |
| `modules/commerce_signals/ai_enrichment.py` | **125** | Signal description enrichment via LLM |
| `modules/product_catalog/ai_tools.py` | **368** | Tools per product catalog |
| **Subtotal Layer 2** | **~4243** | |

### Totale: ~6390 SLOC AI

## 2. Provider coupling — chi chiama claude_client

**9 callers totali** (verificati via grep):

| # | File | Funzione |
|---|---|---|
| 1 | `services/chat_service.py` | `send_messages_with_tools`, `is_available` |
| 2 | `services/ai_insight_service.py` | `send_message`, `is_available` |
| 3 | `routers/ai_store.py` | `send_message`, `is_available` |
| 4 | `modules/commerce_signals/ai_enrichment.py` | `send_message`, `is_available` |
| 5 | `modules/cashflow_monitor/digest_builder.py` | `send_message`, `is_available` |
| 6 | `modules/cashflow_monitor/digest_report_builder.py` | `send_message`, `is_available` |
| 7 | `modules/cashflow_monitor/alert_analysis.py` | `send_message`, `is_available` |
| 8 | `modules/cashflow_monitor/health_explanation.py` | `send_message`, `is_available` |
| 9 | `routers/chat.py` | `ClaudeUnavailableError` (only import) |

**Test files:**
- `tests/test_chat_persistence.py` (patches `services.claude_client.send_messages_with_tools`)
- `tests/test_digest_locale.py` (patches `services.claude_client.send_message`)
- `tests/test_ai_eval_harness.py` (does not import claude_client directly)

**Provider lock-in analysis:**
- Nessun caller importa `anthropic` direttamente
- Tutti passano per l'interfaccia `claude_client.{send_message, send_messages, send_messages_with_tools, is_available, ClaudeUnavailableError}`
- 80% del lavoro di abstraction è già fatto — bisogna formalizzare il contract e isolare 4 punti Anthropic-specific dentro `claude_client.py`

## 3. Test coverage

| Metrica | Valore |
|---|---|
| File test AI dedicati | 2 (`test_chat_persistence.py`, `test_ai_eval_harness.py`) |
| Test count chat persistence | 11 |
| Test count AI eval harness | 14 |
| **Totale test AI dedicati** | **25** |
| Full backend suite | 1577 passed, 7 skipped |

**Tempo esecuzione:**
- `pytest tests/test_chat_persistence.py tests/test_ai_eval_harness.py -q`: **~3.4s**

**Gap principale:** ZERO golden test sul comportamento del prompt (es. "se chiedo X all'AI deve chiamare tool Y e includere caveat Z"). Esiste solo `test_ai_eval_harness.py` ma è generico, non scenario-driven. Wave 4 introdurrà il golden test suite.

## 4. Technical debt counter

| Tipo | Conteggio | Note |
|---|---|---|
| `TODO`/`FIXME`/`XXX`/`HACK` nei file AI core | **0** | Codebase pulito a livello marker |
| Dead code identificato | 1 branch | `chat_service.py:515-521` (parts[1:] mai eseguito, sostituito subito dopo) |
| File con responsabilità overlap | 2 | `digest_builder.py` + `digest_report_builder.py` — da consolidare in Wave 5 |
| Naming brand-coupled | 4 simboli | `claude_client.py` filename, `ClaudeUnavailableError`, `_to_anthropic_format`, `_MODEL` hardcoded |
| Direct DB access da `chat_service` | 4 collection | `customer_metrics`, `orders`, `alert_repository`, `cashflow_summary` — Wave 4 astrae |
| Prompt hardcoded come stringhe Python | 7 costanti | `_PROMPT_CORE`, `_PROMPT_CASHFLOW`, ecc. — Wave 4 sposta in DB |

## 5. Bug critici noti pre-Wave 1

| ID | File:Linea | Bug | Severità | Fix in |
|---|---|---|---|---|
| B1 | `chat_session_repository.py:20-28` | `find_session` non filtra per `user_id` → session hijack intra-org possibile | ALTA | Wave 1 |
| B2 | `chat_session_repository.py:107-116` | `update_title` non filtra per `user_id` | ALTA | Wave 1 |
| B3 | `chat_session_repository.py:31-71` | `upsert_messages` ignora `user_id` su update esistente | ALTA | Wave 1 |
| B4 | `routers/chat.py:154-186` | GET `/chat/history` non filtra per `user_id` | ALTA | Wave 1 |
| B5 | `ai_tool_registry.py:122-127` | Tool collision logga warning ma non blocca → silent overwrite | MEDIA | Wave 1 |
| B6 | `models/ai_usage.py:9-26` | Manca `user_id`, `model_version`, `cost_usd` → monitoring per-user impossibile | CRITICA | Wave 1 |
| B9 | `chat_service.py:483` | `_build_proactive_context` hardcoded `locale="it"` → admin con locale diverso vede italiano nel system prompt | MEDIA | Wave 1.5 |
| B10 | `modules/cashflow_monitor/ai_tools.py:dispatcher` | `query_business_summary` + `query_cashflow_summary` hardcoded `locale="it"` quando chiamano `build_unified_summary` / `build_ai_summary` | MEDIA | Wave 1.5 |
| B11 | `modules/{customer_insights,commerce_signals,product_catalog}/ai_tools.py` | Nessun tool di questi 3 moduli include `currency` nel response. Per org CHF la chat risponde in EUR perché il modello defaulta sul system prompt — verificato via smoke W1.A | **ALTA** | **Wave 1.10** (nuovo) |
| B12 | `modules/cashflow_monitor/cashflow_summary.py:build_ai_summary` | Il summary canonical del cashflow non include `currency` nel response root → smoke W1.A ha mostrato che `query_cashflow_summary` per org CHF risponderebbe senza currency | **ALTA** | **Wave 1.10** |
| B7 | `claude_client.py:229-245` | Zero retry su 429/529 transient → 503 utente-facing | ALTA | Wave 3 |
| B8 | `claude_client.py:230-237` | Nessun Anthropic prompt caching → costo inflated 3-5× | ALTA | Wave 3 |

## 6. Capacity baseline — Anthropic tier

| Voce | Valore |
|---|---|
| Tier attuale | **Tier 1** (Livello 1) |
| Spesa cumulativa | €15 |
| Rate limit Sonnet | 50 req/min |
| Output tokens/min Sonnet | 8K |
| Input tokens/min Sonnet | 30K (escluse cache reads) |
| Per Tier 2 servono | $40+ spesi cumulativi + 7 giorni di attesa |

**Verdetto**: sufficiente per dev + smoke (1-5 utenti contemporanei). Per launch produzione con 30+ utenti contemporanei serve Tier 2.

**Path raccomandato**: caricare $50 credito prepagato + (parallelo) contact Anthropic sales con use case AFianco.

## 7. Architettura attuale — astrazione

| Layer | Esiste? | Gap |
|---|---|---|
| LLM Provider interface | ❌ NO | Wave 2 introduce |
| Agent definition / registry | ❌ NO | Wave 4 introduce |
| Prompt versioning (DB) | ❌ NO | Wave 4 introduce |
| Cost calculator | ❌ NO | Wave 1 introduce |
| Per-user usage tracking | ❌ NO | Wave 1 introduce |
| Tool collision detection | ⚠️ Soft warn | Wave 1 hard block |
| Retry/circuit breaker | ❌ NO | Wave 3 introduce |
| Streaming | ❌ NO | Wave 3 introduce |
| Prompt caching | ❌ NO | Wave 3 introduce |
| PII redaction | ❌ NO | Wave 5 introduce |
| Feedback channel | ❌ NO | Wave 5 introduce |

## 8. Reference numbers (per misurare delta Wave-by-Wave)

Misurazioni manuali su 3 chat di prova (sample, non scientifico):

| Metrica | Valore baseline | Target post-Wave 6 |
|---|---|---|
| Latency P50 chat completa | ~6-12s (non streaming) | <2.5s perceived (streaming) |
| Costo medio per chat (Sonnet, no cache) | ~€0.018 | ~€0.004 (-78% via prompt caching) |
| Tokens system prompt per round | ~4500 input | ~4500 input (ma cache → quasi free) |
| Tokens response per chat | ~600 output | invariato |
| User_id nel tracking | ❌ assente | ✅ presente |
| Sentry tagging | minimo | completo (agent_id + module + tool + user + provider) |

## 9. Risk register pre-launch

| Rischio | Severità | Wave che lo chiude |
|---|---|---|
| Session hijack intra-org | ALTA | 1 |
| Monitoring per-user impossibile | CRITICA | 1 |
| Sotto carico picchia 503 (no retry) | ALTA | 3 |
| Costi 3-5× inflated (no caching) | ALTA | 3 |
| Multi-agent refactor rompe chat exist | ALTA | 4 (feature flag + golden tests) |
| PII clienti in chiaro ad Anthropic | ALTA | 5 |
| DPA Anthropic non firmato | CRITICA | 5 (legal parallel) |

---

**Doc owner**: davide
**Created**: 2026-05-15 (Wave 0)
**Next update**: end of each wave
