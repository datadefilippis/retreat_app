# Trial-Once Enforcement — Analisi + Piano implementativo

**Versione**: v5.8 / Onda 9.T (proposta)
**Severity**: 🔴 CRITICAL — anti-fraud
**Stato attuale**: gap di sicurezza confermato (test runner skipped questa verifica)

---

## 1. Diagnosi attuale (codice analizzato)

### 1.1 Come è gestita oggi la "trial-once policy"

**Backend** (`services/stripe_service.py:341-346`):
```python
if plan.get("trial_days", 0) > 0:
    org = await billing_repository.get_org_billing_summary(org_id)
    has_had_trial = org and org.get("trial_ends_at") is not None  # ← PROXY FRAGILE
    if not has_had_trial:
        session_params["subscription_data"]["trial_period_days"] = plan["trial_days"]
        session_params["payment_method_collection"] = "always"
```

**Frontend** (`hooks/useBilling.js:68`):
```js
hasHadTrial: status.has_had_trial || false,
```

**API** (`routers/billing.py:117`):
```python
"has_had_trial": bool(summary.get("trial_ends_at")),  # ← STESSO PROXY FRAGILE
```

### 1.2 Il bug

`trial_ends_at` viene **resettato a None** quando l'org cancella e torna a Free
(`services/plan_provisioning.py:308`):
```python
await billing_repository.update_org_billing_fields(org_id, {
    ...
    "trial_ends_at": None,  # ← RESET FATALE
    ...
})
```

### 1.3 Esploit possibile (scenario fraudolento)

Un utente malizioso può fare:

```
Giorno 1:  Inizia trial Solo (€19/mo) → trial_ends_at = +14d
Giorno 2:  Cancella subito (immediate cancel)
           → webhook customer.subscription.deleted
           → plan_provisioning.deprovision → trial_ends_at = None
           → org → free
Giorno 3:  Inizia trial Commerce Starter (€39/mo)
           → has_had_trial = (None is not None) = False
           → 🚨 STRIPE CHECKOUT INCLUDE TRIAL_PERIOD_DAYS=14
           → 14gg gratis di Commerce Starter
Giorno 17: Cancella subito → free
Giorno 18: Inizia trial Commerce Pro (€79/mo)
           → 🚨 14gg gratis di Pro
```

**Total free usage**: 42 giorni × 3 piani = ~€137 di valore non pagato.

### 1.4 Cancel-during-trial: stato attuale

Il backend `cancel_subscription` accetta sia `at_period_end=True` che `at_period_end=False`
indipendentemente dallo stato della sub:

- **at_period_end=True durante trial** ✓ (ok): trial continua, sub cancellata a trial_end → org→free
- **at_period_end=False durante trial** ⚠ (subottimale): sub cancellata SUBITO,
  org → free immediatamente. L'utente perde i giorni residui di trial già "consumati".

L'utente preferisce: **durante il trial, "Cancella subito" non dovrebbe essere
un'opzione disponibile**. Solo "Cancella a fine trial" (= at_period_end). Il sistema
mantiene il trial fino a scadenza poi auto-fall a free.

### 1.5 Trial history / audit

**Niente**. Nessuna traccia storica di "questo org ha avuto trial X il giorno Y".
Per support / forensics / analytics non c'è da dove pescare.

---

## 2. Soluzione proposta

### Phase 1 — Campo esplicito `has_used_trial` (anti-fraud core)

**Modello** `backend/models/organization.py`:
```python
class Organization(BaseModel):
    ...
    # v5.8 / Onda 9.T — Trial-once enforcement.
    # Once True, NEVER reset to False except by manual admin override.
    # Set when an org enters trialing state (webhook customer.subscription.created
    # with trial_end set). Survives cancellations, plan changes, and re-subscriptions.
    has_used_trial: bool = False
    has_used_trial_at: Optional[str] = None
    has_used_trial_plan_slug: Optional[str] = None  # which plan was the trial on
```

**Webhook** `services/stripe_service.py _handle_subscription_created`:
```python
if sub.get("trial_end"):
    # Set has_used_trial=True permanently.
    # Use $set + $setOnInsert pattern to NEVER override an existing True value.
    await billing_repository.mark_trial_used(
        org_id=org_id,
        plan_slug=plan_slug,
        started_at=utc_now().isoformat(),
    )
```

**Repository** `repositories/billing_repository.py`:
```python
async def mark_trial_used(org_id: str, plan_slug: str, started_at: str) -> None:
    """Mark org as having used a trial. Idempotent — once True, stays True.

    Anti-fraud: this flag protects against the
    'cancel → re-subscribe with new trial' exploit.
    """
    await organizations_collection.update_one(
        {"id": org_id, "has_used_trial": {"$ne": True}},  # only set if not already
        {"$set": {
            "has_used_trial": True,
            "has_used_trial_at": started_at,
            "has_used_trial_plan_slug": plan_slug,
        }},
    )
```

**Gate update** `services/stripe_service.py create_checkout_session`:
```python
if plan.get("trial_days", 0) > 0:
    org = await billing_repository.get_org_billing_summary(org_id)
    # NEW: explicit field, immune to cancel-and-retry exploit
    has_used = bool(org and org.get("has_used_trial"))
    if not has_used:
        session_params["subscription_data"]["trial_period_days"] = plan["trial_days"]
        session_params["payment_method_collection"] = "always"
```

**Don't reset on deprovision** `services/plan_provisioning.py:308`:
```python
# DELETE trial_ends_at: None  ← non resettare!
# Solo current_period_end, stripe_subscription_id, ecc. vengono ripuliti.
# Il trial_ends_at storico rimane per forensic. Il flag `has_used_trial`
# è il source of truth per il gate, non più trial_ends_at.
```

**API exposure** `routers/billing.py:117`:
```python
"has_had_trial": bool(summary.get("has_used_trial")),  # source of truth nuovo
```

### Phase 2 — Cancel-during-trial UX

**Backend** `services/stripe_service.py cancel_subscription`:
```python
if at_period_end is False:
    # Check if currently trialing → force at_period_end=True instead.
    if current_status == "trialing":
        logger.info(
            "cancel_subscription: org=%s in trialing → forcing at_period_end (preserve trial benefit)",
            org_id,
        )
        at_period_end = True  # downgrade hard cancel to soft
```

**Frontend** `components/BillingSection.js` — cancel modal:
```jsx
{billing.isTrialing ? (
  // During trial: only show at_period_end option, force-set
  <div className="rounded-md bg-blue-50 border border-blue-200 px-3 py-2">
    <p className="text-xs">
      {t('billing.cancel_during_trial_explainer',
        'Sei in prova. Annullando ora, manterrai accesso fino al {{date}}, poi tornerai a Free senza addebiti.',
        { date: formatDate(billing.trialEndsAt) })}
    </p>
  </div>
) : (
  // After trial: show both options (at_period_end + immediate)
  <RadioGroup ... />
)}
```

### Phase 3 — Trial history tracking (audit)

**Modello esteso**:
```python
class TrialHistoryEntry(BaseModel):
    plan_slug: str
    started_at: str  # ISO
    ended_at: Optional[str] = None
    outcome: Optional[str] = None  # "converted" | "cancelled_during_trial" | "expired_to_free"
    stripe_subscription_id: Optional[str] = None

class Organization(BaseModel):
    ...
    trial_history: List[TrialHistoryEntry] = []
```

**Tracking points**:
- `_handle_subscription_created` con trial → append entry con `outcome=None` (in corso)
- `_handle_subscription_deleted` durante trial → patch entry con `outcome="cancelled_during_trial"` o `"expired_to_free"`
- `_handle_subscription_updated` quando status passa trialing → active → patch entry con `outcome="converted"`

### Phase 4 — Migration backfill

```python
# scripts/migrate_set_has_used_trial.py
async def migrate():
    """Backfill has_used_trial=True for orgs that have ever had a trial.

    Source-of-truth: any org with trial_ends_at != null in current state OR
    in audit_log entry of type 'trial_started' OR with stripe customer
    that has trial events in history.
    """
    # Strategy: query Stripe for ALL customers, check subscription history,
    # if any subscription had trial_end != null → mark org has_used_trial=True
```

For prod (no trial users yet): migration banale, tutti has_used_trial=False initially. Dal go-live in poi il flag si setta correttamente via webhook.

### Phase 5 — Tests

Aggiungere a `scripts/run_payment_safety_tests.py`:

| ID | Severity | Cosa testa |
|---|---|---|
| **PMT-T01** | 🔴 | Org has_used_trial=False → checkout SET trial_period_days |
| **PMT-T02** | 🔴 | Org has_used_trial=True → checkout NON SET trial_period_days |
| **PMT-T03** | 🔴 | Webhook customer.subscription.created con trial → has_used_trial=True |
| **PMT-T04** | 🔴 | Cancel via plan_provisioning.deprovision NON resetta has_used_trial |
| **PMT-T05** | 🔴 | Cancel-during-trial con at_period_end=false → backend forza at_period_end=true |
| **PMT-T06** | 🟠 | Trial_history viene popolato correttamente |

---

## 3. Migration strategy (prod)

### Stato attuale produzione
- Tutti gli utenti prod sono cashflow-only
- Nessun trial mai attivato (Solo plan = no trial promotion)
- `has_used_trial` field non esiste ancora → tutti orgs implicitamente False

### Steps deploy
1. Deploy backend con nuovo field (default False) — backward-compatible
2. Deploy frontend con nuova UX cancel modal
3. Run migration script (no-op per produzione attuale, per consistency)
4. Smoke test: nuovo subscribe Solo → has_used_trial=True → tentativo Commerce Starter trial → DENIED

### Rollback
- Field has_used_trial è additive → safe to keep even if rollback frontend
- Per emergency rollback: `db.organizations.updateMany({}, {$unset: {has_used_trial: ""}})`

---

## 4. Cosa cambia per l'utente

### Scenario: utente prova Solo, poi cancella, prova Commerce Starter

**PRIMA (oggi, BUG)**:
1. Inizia Solo trial → trial_ends_at=+14d
2. Cancella subito → trial_ends_at=null, org=free
3. Prova Commerce Starter → 🚨 ottiene 14gg gratis di nuovo

**DOPO (Onda 9.T, FIX)**:
1. Inizia Solo trial → has_used_trial=True (PERMANENT)
2. Cancella → backend forza at_period_end (mantiene trial fino a expiry)
3. Trial scade → org auto-fall a free (webhook customer.subscription.deleted)
4. Prova Commerce Starter → checkout senza trial → addebito immediato €39

### UX cancel modal

**PRIMA**: 2 opzioni (at_period_end / immediate)

**DOPO durante trial**: solo info banner blu "Sei in prova fino al X. Annullando manterrai accesso fino a quella data, poi free."

**DOPO post-trial**: stesse 2 opzioni di prima (situazione attuale)

---

## 5. Effort stimato

| Phase | LoC ~ | Tempo |
|---|---|---|
| 1 — Campo + gate + webhook | 80 | 30 min |
| 2 — Cancel-during-trial enforcement | 40 | 20 min |
| 3 — Trial history audit | 60 | 30 min |
| 4 — Migration script | 50 | 20 min |
| 5 — Test runner additions (6 nuovi PMT) | 200 | 45 min |
| 6 — Documentation update | — | 15 min |
| **Totale** | ~430 | **~2.5 ore** |

---

## 6. Domande prima di procedere

1. **Trial history depth**: vogliamo tracciare solo l'outcome del trial (converted / cancelled / expired) o anche analytics più granulari (giorni di utilizzo, feature più usate)?
   - Suggerimento: solo l'outcome — più analytics si aggiungono dopo se servono.

2. **Admin override**: deve esistere un admin endpoint per "concedere un secondo trial" a un utente specifico (es. customer support, partner deal)?
   - Suggerimento: SÌ — `POST /admin/organizations/{id}/grant-trial` con audit log obbligatorio.

3. **Cancel-during-trial UX**: davvero blocchi totalmente l'opzione "cancel immediate" o lo trasformi silenziosamente in at_period_end con info banner?
   - Suggerimento: trasforma silenziosamente + mostra info chiara (meno friction, stessa protezione).

4. **Migration aggressiva**: vuoi che il migration setti `has_used_trial=True` per ogni org con trial_ends_at OR con sub history Stripe?
   - Suggerimento: SÌ, per closure di qualsiasi gap retroattivo.

---

## 7. Stato di approvazione

- [ ] User conferma Phase 1 (gate + field) — CRITICAL anti-fraud
- [ ] User conferma Phase 2 (cancel-during-trial)
- [ ] User conferma Phase 3 (trial history audit)
- [ ] User conferma Phase 4 (migration)
- [ ] User conferma Phase 5 (test)

Una volta approvato, implementazione coordinata in ~2.5 ore con commit unico
incrementale + rollback plan.
