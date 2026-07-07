# Analisi deep — Sistema moduli, abbonamenti e coerenza promesse↔consegna

**Data:** 2026-07-07 · **Domande founder:** (1) il concetto di modulo si è perso? (2) mantenerlo ma tutto attivo subito; (3) le voci degli abbonamenti sono promesse VERE? il €29 "insight avanzate" è coerente? i meccanismi moduli↔abo funzionano?

---

## PARTE 1 — Confermo: il modulo si è perso a metà. Ecco esattamente dove.

### L'architettura ha DUE strati che non si parlano

| Strato | Collection | Chi lo scrive | Cosa governa |
|---|---|---|---|
| **Billing** (ModuleSubscription) | subscriptions | `provision_commercial_plan` — automatico al signup (`retreat_free`) e a ogni cambio piano | Quote e limiti (`check_module_access`: orders_monthly, data_rows, products…) |
| **Attivazione** (organization_modules) | organization_modules | SOLO `POST /modules/{key}/activate` — cioè la pagina /modules, che nel menu è **visibile solo al system_admin** | Il MENU (dynamicOpsNav se `activeSet.has('commerce')`), le pagine moduli, i widget |

**Conseguenza concreta:** un operatore che si iscrive oggi riceve automaticamente le subscription di tutti e 5 i moduli (billing ok)… ma **zero organization_modules** → il suo menu operativo è VUOTO (niente Ordini, Incassi, Dati, Store, Recensioni, Newsletter) finché un system_admin non gli attiva i moduli a mano. L'org demo funziona solo perché i seed l'hanno attivata. Questo è il buco più grave: non "concettuale", operativo.

### Le feature nuove sono nate apolidi

Verificato riga per riga: `reviews`, `outreach`, `cashflow` (/incassi), `newsletter_forms`, `sales-stats`, `cross-sell` hanno **zero riferimenti ai moduli** — né gating né appartenenza dichiarata. Nel menu stanno tutte sotto l'ombrello `commerce` per posizione, non per design. Il sistema quota (`data_rows` sul gestionale Dati: c'è!) convive con endpoint gemelli senza alcun gate. Il concetto c'è ancora per le feature del fork AFianco, non per quelle costruite dopo.

## PARTE 2 — Audit abbonamenti: promesse vs realtà

### La scala retreat (signup → retreat_free automatico)

| | Gratis (0€, fee 5%) | Pro (29€, fee 2%) | Founding/Partner (admin) |
|---|---|---|---|
| module_plans | catalog_free(100)·commerce_retreat(1 store)·customers_free·cashflow_retreat | catalog_pro(∞)·commerce_pro(3 store)·customers_pro·cashflow_retreat | = Pro (fee 2%/0%) |

### Voce per voce del Pro (29€) — è vero?

| Promessa (features_display) | Realtà | Verdetto |
|---|---|---|
| Fee ridotta 5%→2% | `transaction_fee_percent` applicato dal provider Stripe | ✅ VERO — la leva reale del piano |
| Catalogo illimitato (vs 100) | limits products 100→-1, enforcement quota esistente | ✅ VERO |
| 3 store (vs 1) | stores_max 1→3 | ✅ VERO |
| Team 5 (vs 2) | platform_limits | ✅ VERO |
| **"In evidenza nel calendario pubblico"** (`retreat_featured`) | **NESSUN enforcement**: la directory non ordina/evidenzia per piano — la chiave esiste solo nel testo | 🔴 **PROMESSA VUOTA** |
| **"Insight clienti avanzati"** (`retreat_customers_pro`) | customers_light_free e _pro hanno **limiti IDENTICI** (analytics -1 entrambi): il free vede tutto quello che vede il pro | 🔴 **PROMESSA VUOTA** |
| Supporto prioritario | processo umano, non software | ⚪ ok (fuori scope codice) |

**Risposta secca alla tua domanda:** no, oggi NON ci sono moduli/insight che chi paga 0 non vede e chi paga 29 ottiene. Le differenze vere sono fee, limiti quantitativi e team. Le due voci "qualitative" del Pro sono scritte ma non consegnate — l'opposto della filosofia realtà-dei-dati che stiamo applicando ovunque.

### I meccanismi funzionano?

- provision→subscription→quote: ✅ solido (canonical entry point, idempotente, usato da signup/Stripe/admin);
- subscription→attivazione: 🔴 **rotto by design** (mai riconciliati nel fork);
- promessa→enforcement: 🔴 nessuna guardia collega `features_display` a codice reale (le 2 voci vuote non le ha mai intercettate nessun test).

## PARTE 3 — Piano MD1–MD4 (Moduli & Denaro)

### MD1 — Attivazione automatica (il meccanismo resta, il default diventa "tutto acceso")
- `provision_commercial_plan` attiva anche `organization_modules` per ogni modulo il cui piano non è `*_disabled` (e disattiva i disabled, es. ai_assistant). Idempotente;
- migrazione one-shot per le org esistenti (stessa regola);
- la pagina /modules e attiva/disattiva restano (system_admin) — modularità intatta, come chiesto: il meccanismo vive, l'operatore non deve pensarci.
- guardia: dopo provision(retreat_free), org_modules attivi = {commerce, product_catalog, customers_light, cashflow_monitor} e ai_assistant NO.

### MD2 — Cittadinanza dei senza-modulo (coerenza concettuale)
- Registry esplicito `MODULE_OWNERSHIP` in `services/module_access.py`: reviews→commerce, newsletter→commerce, outreach→customers_light, cashflow analytics (/incassi)→cashflow_monitor, sales-stats→product_catalog, cross-sell→customers_light;
- dependency `require_module(key)` leggera sui 5 router orfani (no-op con tutto attivo, ma il giorno che un piano spegne un modulo, la feature lo rispetta);
- nav: le voci si mostrano in base al SUO modulo (oggi: tutto sotto commerce). Con MD1 il risultato visivo non cambia — cambia la correttezza.

### MD3 — Verità dell'abbonamento (le 2 promesse vuote)
Proposta (decidi tu la variante):
- **`retreat_featured` → renderla VERA**: boost di ordinamento nella directory /ritiri per le org su piani fee-2% (pro/founding/partner) + badge discreto "In evidenza" sulla card. Costo contenuto: un sort key in più nell'endpoint directory. *(alternativa: togliere la voce dal pricing — ma è un buon incentivo, meglio costruirla)*;
- **`retreat_customers_pro` → sostituirla con promesse vere già esistenti**: il Pro oggi include davvero "Export CSV clienti illimitato"? (verificare gate export) — altrimenti riformulare la voce in ciò che il pro dà realmente (es. accorpare in "Limiti estesi") e NON vendere insight che il free ha già. Niente paywall retroattivo sugli insight: l'essenzialità per tutti è una scelta di prodotto giusta per la crescita del verticale.

### MD4 — Guardie promesse↔codice (mai più voci vuote)
- test "promises registry": ogni chiave in `features_display` dei piani retreat DEVE avere una entry in un registro `PROMISE_ENFORCEMENT` = {feature_key: puntatore all'enforcement (limit key / funzione / 'process')} — una voce nuova senza enforcement dichiarato rompe la CI;
- test attivazione automatica MD1 + test boost featured MD3;
- parità i18n voci billing ×4 (già nel guard pattern).

Ordine: MD1 (sblocco operatori) → MD2 → MD3 → MD4. Ogni step: branch, suite, verifica browser, merge.
