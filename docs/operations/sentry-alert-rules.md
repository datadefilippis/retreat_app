# Sentry Alert Rules — Open Beta Configuration

> Configurazione canonica delle alert rules in Sentry per l'open beta
> (50-200 merchant). Le rules sono **manualmente create** nella web UI
> di Sentry (no API per single-person ops); questo doc e' la
> specifica versionata. **Track O Step 3.1.**
>
> **Owner unico (pilot + open beta):** davide@afianco.ch
> **No Slack / PagerDuty integration** (limitamo tool esterni, single
> operator). Email = canale primario. Sentry inbox = dashboard primario.

---

## Quick reference

| Categoria | Tool | Frequenza review | Notification |
|---|---|---|---|
| **Errors P0/P1** (payment, auth, 500 spike) | Sentry Issue Alerts | Immediate (email + push) | davide@afianco.ch |
| **Errors P2** (new feature regression) | Sentry Issue Alerts | 1/h digest | davide@afianco.ch |
| **Performance** (slow endpoints) | Skip per open beta | — | Traces rate 0.0001 = statistical noise |
| **Custom business** (mass-signup, embed broken) | Tag-based filtered alerts | Immediate | davide@afianco.ch |
| **Uptime / health** | UptimeRobot (free tier) | 5min poll | Vedi `uptime-monitoring.md` (O3.4) |

---

## Sentry project setup verification

Prima di creare le rules, verifica che il project sia configurato
correttamente:

| Setting | Valore atteso | Dove |
|---|---|---|
| Project name | `afianco-backend` | Project Settings → General |
| Platform | Python (FastAPI) | Project Settings → General |
| DSN env var backend | `SENTRY_DSN` | Settings → Client Keys (DSN) |
| Environments tracked | `production`, `staging`, `development` | Project → Environments |
| PII scrubbing | Default ON + custom scrubber attivo (vedi `core/observability/sentry.py`) | Verify via test event |
| Default issue grouping | Fingerprint per `exception.type` + frame.function | Issue Settings (default) |

Frontend project (separato, opzionale):
| Setting | Valore atteso |
|---|---|
| Project name | `afianco-frontend` |
| Platform | React |
| DSN env var | `REACT_APP_SENTRY_DSN` |

---

## Alert rules da creare (CANONICAL — 6 rules)

Vai su **Alerts → Create Alert Rule → Issue Alert** per ognuna.

---

### Rule 1 — `[P0] Payment failure spike`

**Trigger:** payment fails > 3 times in 5 minutes (production)
**Razionale:** spike improvviso di payment fail = Stripe outage,
webhook broken, o key rotated senza update env. Critical.

| Field | Value |
|---|---|
| **Name** | `[P0] Payment failure spike` |
| **Environment** | `production` |
| **Filter** | `event.tags['action']` contains `payment_` |
| **Trigger** | `The issue is seen more than 3 times in 5 minutes` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `10 minutes` |

Tag `action:payment_*` viene popolato da `core/observability/sentry.py`
quando `capture_exception` viene chiamato con tag context (vedi O3.2).

---

### Rule 2 — `[P0] Auth failure spike`

**Trigger:** auth-related errors > 20 in 5 minutes (production)
**Razionale:** spike improvviso di auth errors = bug nella verifica
JWT, Mongo down, o brute-force che bypassa rate limit. Critical.

| Field | Value |
|---|---|
| **Name** | `[P0] Auth failure spike` |
| **Environment** | `production` |
| **Filter** | `event.tags['action']` contains `auth_` |
| **Trigger** | `The issue is seen more than 20 times in 5 minutes` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `10 minutes` |

---

### Rule 3 — `[P1] 500 error spike (any endpoint)`

**Trigger:** any `level:error` > 10 in 5 minutes (production)
**Razionale:** general purpose safety net. Cattura categorie non
ancora taggate (es. Mongo connection error, OOM, internal serializer
error). Soglia generosa (10/5min = ~120/h) per evitare alert fatigue
ma identifica spike reali.

| Field | Value |
|---|---|
| **Name** | `[P1] 500 error spike` |
| **Environment** | `production` |
| **Filter** | `event.level` is `error` |
| **Trigger** | `The issue is seen more than 10 times in 5 minutes` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `30 minutes` |

---

### Rule 4 — `[P1] New issue in production`

**Trigger:** primo evento di un'issue MAI VISTA in production
**Razionale:** ogni nuovo bug in prod va triagato. Anche se la
frequenza e' bassa (1 evento), un nuovo error type = potential bug
appena introdotto da deploy.

| Field | Value |
|---|---|
| **Name** | `[P1] New issue in production` |
| **Environment** | `production` |
| **Filter** | `event.level` is `error` OR `event.level` is `fatal` |
| **Trigger** | `A new issue is created` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `5 minutes` per issue |

---

### Rule 5 — `[P1] Regression detected`

**Trigger:** issue marcata "resolved" che ricompare in production
**Razionale:** fix che non ha funzionato o regression introdotta da
codice successivo. Sentry detecta automaticamente via fingerprint.

| Field | Value |
|---|---|
| **Name** | `[P1] Regression detected` |
| **Environment** | `production` |
| **Filter** | (none — all environments) |
| **Trigger** | `The issue changes state from resolved to unresolved` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `1 hour` per issue |

---

### Rule 6 — `[P2] Embed-SDK error spike`

**Trigger:** errori taggati `surface:embed` > 50 in 1 ora
**Razionale:** embed-SDK gira su browser merchant cliente —
errori qui significano widget broken su sito merchant. Soglia
piu' alta (50/h) perche' include molte browser-specific issues
(adblock, CSP merchant restrittive, ecc.) che sono fuori dal
nostro controllo. Spike > 50 = bug reale nella nostra SDK.

| Field | Value |
|---|---|
| **Name** | `[P2] Embed-SDK error spike` |
| **Environment** | `production` |
| **Filter** | `event.tags['surface']` is `embed` |
| **Trigger** | `The issue is seen more than 50 times in 1 hour` |
| **Action** | Send email to `davide@afianco.ch` |
| **Frequency** | Perform this action at most once every `2 hours` |

---

## Tag taxonomy (referenced from rules)

Le rules usano questi tag — popolati da `sentry_sdk.set_tag()` o
`scope.set_tag()` nei call site `capture_exception()` (O3.2):

| Tag key | Valori | Set da |
|---|---|---|
| `action` | `payment_charge`, `payment_refund`, `payment_webhook`, `auth_login`, `auth_signup`, `auth_token_verify`, `auth_password_reset`, `email_send`, `ai_complete`, `mongo_query` | Hot path try/except handlers |
| `surface` | `api`, `embed`, `admin_ui`, `customer_portal` | Set automatically da SDK init per backend; manualmente nei frontend handlers |
| `org_id` | UUID stringa (NEVER raw email/PII) | Set in middleware quando JWT decoded |
| `endpoint` | path pattern (es. `/api/orders/checkout`) | Set automatically da FastAPI integration |

**Anti-PII:** mai aggiungere `email`, `phone`, `name`, `address` come
tag (filtrati dal `before_send` scrubber comunque).

---

## Notification routing

**Single operator setup (open beta):**
- Tutti gli alert → davide@afianco.ch
- Email throttling: vedi "Frequency" su ogni rule
- Sentry inbox come dashboard primario (Issues view → filter by
  environment=production, sort by Last Seen)

**Mobile push (recommended):**
- Sentry mobile app (iOS/Android) → notifications on per alert
  rules elencate. Configurazione: app → Settings → Notifications →
  toggle on per ogni rule.

**Setup post-pilot (V2 — quando aggiungiamo secondary operator):**
- Add secondary in `Team Settings → Members`
- Update rules: action target = "Send email to Team `oncall`"
- Configure Slack integration (Sentry → Integrations → Slack)
- Set up PagerDuty per P0 only

---

## Test procedure (verifica setup)

Dopo aver creato le 6 rules, valida ognuna con un test event.

### Test Rule 1 (Payment failure spike)

```python
# In Python console / test script con ENVIRONMENT=production e DSN reale:
import sentry_sdk
sentry_sdk.set_tag("action", "payment_charge")
for i in range(4):
    try:
        raise RuntimeError(f"TEST Rule 1 — payment failure {i+1}")
    except Exception as e:
        sentry_sdk.capture_exception(e)
```

Atteso: email arriva a davide@afianco.ch entro 5min con subject
`[Sentry] [P0] Payment failure spike`. Se NO → check filter su tag
`action`, verify rule active, verify environment=production esatto.

### Test Rule 4 (New issue)

Cambia il messaggio in un'eccezione mai vista prima:
```python
import sentry_sdk
import uuid
try:
    raise RuntimeError(f"TEST Rule 4 — new issue {uuid.uuid4()}")
except Exception as e:
    sentry_sdk.capture_exception(e)
```

Atteso: email entro 5min con subject `[Sentry] [P1] New issue...`.

### Cleanup post-test

Dopo verify, marca le 4-6 test issues come "Resolved" + "Ignored"
in Sentry web UI. Senza cleanup, rules continuano a fire su retry
del test stesso.

---

## Maintenance schedule

| Cadenza | Task |
|---|---|
| **Settimanale** | Review inbox Sentry (filter environment:production, last 7d). Triage tutti gli unresolved. |
| **Mensile** | Re-tune soglie se troppi false positive O troppi miss. Verifica che le 6 rules siano ancora attive (Sentry NON disabilita rules sole, ma audit comunque). |
| **Post-incident** | Se rule NON ha catturato un incident reale → add new rule O ridurre soglia esistente. Documenta in `incidents.md`. |
| **Pre-release major** | Resolve tutte le issues vecchie (>30 giorni) per ridurre noise nella prima settimana post-deploy. |

---

## Rules NON create (e perche')

- ❌ **Performance / slow transaction alerts**: traces sampling e' 0.0001
  in prod (O1.2) → 13k traces/mese, statistical noise per alert.
  V2: aumentare sampling solo se necessario.
- ❌ **User feedback alerts**: feature non abilitata; richiede form
  custom su frontend.
- ❌ **Crash-free sessions alert**: frontend crash tracking minimal,
  rule sarebbe dominata da browser-specific noise (adblock, ecc.).
- ❌ **Slack integration**: explicit decision per single-operator open
  beta. Email + mobile push sufficiente. Re-evaluate quando team > 1.

---

## Riferimenti

- O1.2 — Sentry traces sampling: `backend/core/observability/sentry.py`
- O3.2 — `capture_exception` invocations + tagging: hot paths Stripe/Brevo/auth
- O3.4 — Uptime monitoring (UptimeRobot): `docs/operations/uptime-monitoring.md`
- `incident-response.md` — playbook quando rule fire
- `incidents.md` — post-mortem log

---

**Last reviewed:** 2026-05-29
**Next review:** post-O3 completion + 1 settimana di soak prod
