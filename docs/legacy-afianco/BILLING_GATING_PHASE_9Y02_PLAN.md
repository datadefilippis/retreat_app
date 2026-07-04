# Onda 9.Y.0.2 — Cashflow data_rows: chiusura definitiva

**Status**: piano + Step A in implementazione.
**Riferimento audit**: `docs/BILLING_GATING_HOLISTIC_AUDIT_PLAN.md`

---

## 1. Diagnosi finale — perché non si vedono blocchi cashflow

Tre audit forensici paralleli (backend insert paths, frontend forms, lifecycle module_subscription) hanno triangolato la causa. **Il gate backend funziona; il problema è altrove.**

### 1.1 Backend gate coverage (audit forense)

11 chokepoint cashflow tutti gated, counter accuracy ovunque corretta. Fonti verificate:

| Endpoint | Gate | Record |
|---|---|---|
| `POST /sales` | ✅ | ✅ qty=count |
| `POST /expenses` | ✅ | ✅ qty=count |
| `POST /purchases` | ✅ | ✅ qty=count |
| `POST /fixed-costs` + `/bulk` | ✅ | ✅ |
| `POST /purchase-records` | ✅ (9.Y.0) | ✅ |
| `POST /datasets/upload` + `/upload-with-mapping` | ✅ | ✅ qty=len(records) |
| `POST /orders/import` + `/import-with-mapping` | ✅ (9.Y.0) | ✅ |
| `POST /orders/{id}/confirm` (manual + webhook) | ✅ | ✅ |
| `POST /orders/{id}/cancel` (storno) | ✅ (9.Y.0.1) | ✅ |
| `POST /orders/pos` | ✅ (9.Y.0) | ✅ |

Zero gap. `purchase_record_repository.create_many` è dead code (P2 latent, da rimuovere).

### 1.2 Frontend forms (audit forense)

**Nessun bug `setDialogOpen`-style nei form cashflow** — sono top-level components, non sub-components nidificati come `OrderFormDialog`. Però 4 spot hanno toast che compete con paywall + ZERO pre-emptive UI gate.

| Issue | File:linea | Severity |
|---|---|---|
| 2A — `isPaywallHandled` missing | `PurchaseEntryForm.js:124-128` | medium |
| 2B — idem | `FixedCostEntryForm.js:106-110` | medium |
| 2C — `UploadPage.js:316` 429 fallthrough generico | `UploadPage.js` | low (smartToast salva) |
| 2D — `OrderImportDialog.js:111,139` competing toast | `OrderImportDialog.js` | low |
| 3 — Nessun pre-emptive UI gate per data_rows | tutti gli entry form | medium |

### 1.3 Root cause cashflow bypass (audit forense)

**Lifecycle `module_subscription` ha un drift window confermato.**

Path:
1. Trial Pro creato → `provision_commercial_plan` scrive `cashflow_monitor_pro` con `status=active` e `data_rows=-1`
2. Trial finisce senza pagamento. Stripe manda `customer.subscription.updated` con `status=canceled` (senza necessariamente `deleted` immediato)
3. `_handle_subscription_updated` in `plan_provisioning.py:347-401`:
   - Se `new_plan_slug` = `current_plan_slug` (entrambi "pro"), va al **branch metadata-only (linee 382-401)** che aggiorna SOLO i campi org (`billing_status`, `cancel_at_period_end`, ecc.). **NON tocca `module_subscriptions`.**
4. Risultato: org sits con `commercial_plan_slug=pro`, `billing_status=canceled`, `cashflow_monitor_pro` ATTIVA.
5. `_sync_expired_trial` (`billing_lifecycle.py:66-149`) cerca solo `billing_status=trialing` — questo org è già `canceled`, lo perde.
6. Il gate `module_access.py:218` (Step 1 di `get_module_entitlements`) si fida del `module_subscription` attivo → ritorna `data_rows=-1` → bypass totale.

Inoltre: `module_subscription` ha solo stati `active`/`cancelled`, non `trialing`. Quindi a livello entitlement, **trial Pro = paid Pro**. Stripe distingue, AFianco no.

**Query di detection drift** (per Mongo shell):
```js
db.module_subscriptions.aggregate([
  { $match: { status: "active" } },
  { $lookup: { from: "organizations", localField: "organization_id",
               foreignField: "id", as: "org" } },
  { $unwind: "$org" },
  { $match: {
      "org.commercial_plan_slug": { $in: ["free", "starter"] },
      "commercial_plan_slug": { $in: ["core", "pro", "enterprise"] }
  }},
])
```

---

## 2. Piano fix (6 step, sequenziali, isolati)

Ogni step è git-revert-safe. Ogni step ha smoke test deterministico.

### Step A — Root cause: lifecycle drift fix (P0, ~30 LOC)

**File**: `backend/services/plan_provisioning.py`

**Cambio**: nel branch `_handle_subscription_updated` metadata-only, quando `status` transiziona a `canceled` / `unpaid` / `incomplete_expired`, chiamare `cancel_subscriptions_by_stripe_sub` per tutti i `module_subscriptions` legati a quello `stripe_subscription_id`. Defence-in-depth: usare lo stesso path di `deprovision_stripe_subscription` per cleanup completo.

Aggiungere log esplicito quando si rileva la transizione, così è tracciabile.

**Risultato**: trial cancel + subscription cancel non lasciano più subs Pro orfane.

### Step B — Audit + auto-fix degli org già in drift (P0, ~40 LOC)

**File**: `backend/scripts/diagnose_data_rows_gate.py` (estensione) + nuovo `backend/scripts/repair_module_subscription_drift.py`.

**Cambio**:
1. Estendere `diagnose_data_rows_gate.py` con flag `--auto-fix` che, se rileva `commercial_plan_slug ∈ {free, starter}` ma module_subscription attiva con `data_rows=-1`, chiama `provision_commercial_plan(commercial_plan_slug)` per ricreare lo stato corretto.
2. Nuovo script `repair_module_subscription_drift.py` che scansiona TUTTI gli org con la query del §1.3 e li ripara (dry-run di default, `--apply` per execute).

**Risultato**: org test attualmente in drift viene riparato. Davide può lanciare `python -m scripts.repair_module_subscription_drift` per pulizia globale.

### Step C — Hardening DB: indice unique (P1, 1 LOC)

**File**: `backend/database.py`

**Cambio**: aggiungere indice unique parziale su `module_subscriptions`:
```python
await db.module_subscriptions.create_index(
    [("organization_id", 1), ("module_key", 1)],
    unique=True,
    partialFilterExpression={"status": "active"},
)
```

**Risultato**: race condition tra webhook concorrenti non può più creare 2 row attive. Doppio insert fallirebbe a livello DB.

### Step D — Pre-emptive UI gate per data_rows (P1, ~120 LOC)

**File**:
- `backend/routers/billing.py`: estendi `/usage-summary` con `data_rows: {limit, usage, remaining}` se non già presente
- `frontend/src/hooks/useEntitlements.js` (nuovo): hook generale read-only
- `frontend/src/features/cashflow/SalesEntryForm.js` + `ExpensesEntryForm.js` + `PurchaseEntryForm.js` + `FixedCostEntryForm.js` + `ModuleDatasetManager.js`: import hook, disable Save quando `remaining <= 0`, mostra inline `<UpgradeHint>`

**Risultato**: l'utente Free a 200/200 vede il bottone Save disabilitato CON tooltip "Limite righe dati raggiunto, aggiorna piano". Niente più "spingo Salva e non capisco perché non succede nulla".

### Step E — Fix UX paywall: 4 spot frontend (P2, ~20 LOC)

**File**:
- `PurchaseEntryForm.js:125`: import + guard `isPaywallHandled`
- `FixedCostEntryForm.js:107`: idem
- `UploadPage.js:316`: idem
- `OrderImportDialog.js:111,139`: idem (×2)

**Risultato**: nessun toast generico compete più col paywall.

### Step F — Cleanup dead code (P3, ~10 LOC)

**File**:
- `backend/repositories/purchase_record_repository.py`: rimuovi `create_many` (dead code, P2 latente che potrebbe diventare bypass se qualcuno lo wireasse)
- Cleanup componenti frontend dead (vedi audit precedente: `QuotaExceededBanner`, `UpgradePaywall`, `QuotaProgressBanner` se confermati senza caller)

**Risultato**: codebase più pulita, nessuna superficie d'attacco latente.

---

## 3. Ordine d'esecuzione e effort

| Step | Effort | Priorità | Bloccante per quale problema utente? |
|---|---|---|---|
| A. Lifecycle fix | 30 min | **P0** | Sì — root cause dei bypass cashflow |
| B. Repair drift esistenti | 30 min | **P0** | Sì — org test attuale è in drift |
| C. Indice unique | 10 min | P1 | No (preventivo) |
| D. Pre-emptive UI gate | 1.5h | P1 | Migliora UX, non bloccante |
| E. Fix toast UX | 30 min | P2 | Polish |
| F. Cleanup | 20 min | P3 | Debt |

**Totale: ~3.5h** spalmati in commit incrementali.

---

## 4. Strategia esecutiva

**Step A + B + C in un commit** (chiusura definitiva del bypass): immediato.

**Step D in commit separato**: feature additiva, può andare dopo.

**Step E + F in commit separato**: polish, può andare dopo.

Ogni commit:
- py_compile + import test backend
- acorn-jsx parse frontend
- diff stat ridotto e mirato
- commit message dettagliato che spiega root cause + fix

---

## 5. Test post-deploy (acceptance)

Dopo Step A+B+C:
1. ✅ Su tenant test, esegui `python -m scripts.diagnose_data_rows_gate --org-id <ORG>`. Verdict: `EXPECTED-PASS` (Free → effective_limit=200, usage_via_gate=N).
2. ✅ Tenant Free a 200/200 → POST `/sales`, `/expenses`, `/purchases`, `/fixed-costs`, `/purchase-records`, `/datasets/upload`, `/orders/import`: TUTTI ritornano 429 `QUOTA_EXCEEDED`.
3. ✅ Lancio `repair_module_subscription_drift.py --apply`: 0 drift residui in tutto il DB.

Dopo Step D:
4. ✅ Tenant Free a 200/200 → tutti i 4 entry form mostrano Save disabled + tooltip + upgrade hint inline.
5. ✅ ModuleDatasetManager (importa CSV in cashflow) mostra warning prima dell'upload se quota piena.

Dopo Step E:
6. ✅ Su 429 in `PurchaseEntryForm`, `FixedCostEntryForm`, `UploadPage`, `OrderImportDialog`: solo paywall, niente toast competing.

---

## 6. Approval gate

Davide rivede questo doc e:
- [ ] OK partire con Step A+B+C (1.5h, deploy in giornata)?
- [ ] Step D: vuoi `useEntitlements` come hook generale (consigliato, scalabile) o estendere `useBilling`?
- [ ] Step F cleanup: rimuovere subito i 3 componenti frontend dead-code (QuotaExceededBanner, UpgradePaywall, QuotaProgressBanner) oppure preserve per ora?

Risposta: parto a implementare Step A subito.
