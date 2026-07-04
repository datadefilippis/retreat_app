# Uptime Monitoring — Open Beta Configuration

> Setup canonical degli uptime monitor esterni per l'open beta (50-200
> merchant). Usiamo **UptimeRobot free tier** (50 monitor / 5min interval
> gratis) come sentinel esterno indipendente dal nostro stack: se il VPS
> Hetzner cade o nginx muore, Sentry non vede nulla (e' interno al
> backend), MA UptimeRobot pinga da fuori e ci avvisa via email.
> **Track O Step 3.4.**
>
> **Owner unico (pilot + open beta):** davide@afianco.ch
> **Tier:** Free (zero cost, 50 monitor, 5min interval)
> **No SMS/Voice/Slack** (limitamo tool esterni, single operator).

---

## Quick reference

| Componente | Strumento | Cost | Probe frequency | Alert |
|---|---|---|---|---|
| HTTP backend | UptimeRobot HTTP(s) | €0 | 5min (free tier) | Email immediato |
| MongoDB health | UptimeRobot via /api/health/ready | €0 | 5min | Email immediato |
| Anthropic circuit | UptimeRobot via /api/health/ai | €0 | 15min (lower priority) | Email immediato |
| Frontend (root) | UptimeRobot HTTP(s) | €0 | 5min | Email immediato |
| SSL cert expiry | UptimeRobot SSL monitor | €0 | 1x/day | Email 7 giorni prima |

**Perche' UptimeRobot vs altri:**
- Better Uptime / Pingdom: free tier troppo limitato (10 monitor max)
- StatusCake: free tier OK ma UI dated
- UptimeRobot: 50 monitor + 5min interval + SSL monitor inclusi free

---

## Setup steps

### 1. Account creation (one-time, ~3min)

1. Vai su https://uptimerobot.com/signUp
2. Sign up con `davide@afianco.ch`
3. Verify email (link nella inbox)
4. Conferma timezone Europe/Rome nelle settings (per orari report)

### 2. API access (optional, V2)

Free tier dashboard e' web-only sufficient. Per provisioning programmatico
(V2 quando aggiungiamo nuovi env), generare main API key in:
`My Settings → API Settings → Main API Key`. NON necessario per setup
manuale single-operator.

---

## Monitor da creare (CANONICAL — 5 monitor)

Per ogni monitor: **Dashboard → + Add New Monitor**.

---

### Monitor 1 — `[CRIT] Backend HTTP liveness`

**Trigger:** GET `https://afianco.ch/api/health/live` non-2xx OR no
response in 30s.
**Razionale:** liveness probe e' la baseline — se questo cade, il backend
container Python e' morto. Pre-O3.4 down detection richiedeva check manuale
ogni qualche ora.

| Field | Value |
|---|---|
| **Monitor type** | HTTP(s) |
| **Friendly name** | `[CRIT] Backend liveness` |
| **URL** | `https://afianco.ch/api/health/live` |
| **Monitoring interval** | `5 minutes` |
| **Monitor timeout** | `30 seconds` |
| **Keyword (advanced)** | `uptime_seconds` — verify response body contains it (robust al spacing JSON) |
| **Alert contacts** | `davide@afianco.ch` |
| **Notification when** | `Down` (alert) + `Up` (recovery) |

Endpoint contract (vedi `backend/routers/health.py:54`):
- 200 always se processo alive
- `{"status": "ok", "uptime_seconds": int, "version": str}`
- No DB / external dependency
- Keyword `uptime_seconds` scelta vs `"status":"ok"` perche' JSON
  serialization puo' aggiungere spazi (`"status": "ok"` vs `"status":"ok"`).
  `uptime_seconds` e' un identifier univoco sempre presente, no spacing.

---

### Monitor 2 — `[CRIT] Backend readiness (MongoDB)`

**Trigger:** GET `https://afianco.ch/api/health/ready` non-2xx.
**Razionale:** se Mongo cade, backend non puo' servire traffic. /ready
ritorna 503 con detail → app degraded ma processo vivo (Monitor 1
ancora green). Senza Monitor 2 vedremmo "backend OK" mentre tutti gli
endpoint /api/* falliscono.

| Field | Value |
|---|---|
| **Monitor type** | HTTP(s) |
| **Friendly name** | `[CRIT] Backend readiness` |
| **URL** | `https://afianco.ch/api/health/ready` |
| **Monitoring interval** | `5 minutes` |
| **Monitor timeout** | `30 seconds` |
| **Keyword (advanced)** | `mongodb` — verify response body cita la key check (key sempre presente sia in 200 che 503) |
| **Alert contacts** | `davide@afianco.ch` |
| **Notification when** | `Down` (alert) + `Up` (recovery) |

Endpoint contract (vedi `backend/routers/health.py:145`):
- 200 se MongoDB reachable + Stripe/Brevo configurati
- 503 se Mongo down → UptimeRobot alert via status code
- Body: `{"status": ..., "ready": bool, "checks": {"mongodb": {...},
  "stripe": {...}, "brevo": {...}}, ...}`
- Cached 10s lato server (READY_CACHE_TTL_SECONDS) → no DB hammering
- Keyword `mongodb` solo defense-in-depth (UptimeRobot alert su 503
  status code e' il primary signal)

---

### Monitor 3 — `[MED] AI provider circuit breaker`

**Trigger:** GET `https://afianco.ch/api/health/ai` non-2xx.
**Razionale:** Anthropic outage o circuit breaker aperto → AI features
degradate (insights, digest, health-explanation) MA core e-commerce
funziona. Severity MED = email ma non page.

| Field | Value |
|---|---|
| **Monitor type** | HTTP(s) |
| **Friendly name** | `[MED] AI provider health` |
| **URL** | `https://afianco.ch/api/health/ai` |
| **Monitoring interval** | `15 minutes` (free tier minimum, sufficient) |
| **Monitor timeout** | `30 seconds` |
| **Alert contacts** | `davide@afianco.ch` |
| **Notification when** | `Down` (alert) + `Up` (recovery) |

Endpoint contract (vedi `backend/routers/health.py:188`):
- 200 con `circuit_state: closed | open | half_open`
- 503 se Anthropic config malformata (env var manca)

---

### Monitor 4 — `[CRIT] Frontend root`

**Trigger:** GET `https://afianco.ch/` non-2xx OR keyword "AFianco"
missing nel response body.
**Razionale:** frontend container down (es. nginx config broken, build
asset 404, CDN issue) → merchant non possono accedere a admin UI.
Diverso dal Monitor 1 (backend Python) — qui testiamo il frontend
container separato.

| Field | Value |
|---|---|
| **Monitor type** | HTTP(s) |
| **Friendly name** | `[CRIT] Frontend root` |
| **URL** | `https://afianco.ch/` |
| **Monitoring interval** | `5 minutes` |
| **Monitor timeout** | `30 seconds` |
| **Keyword (advanced)** | `AFianco` — verify SPA HTML render |
| **Alert contacts** | `davide@afianco.ch` |
| **Notification when** | `Down` (alert) + `Up` (recovery) |

---

### Monitor 5 — `[CRIT] TLS certificate expiry`

**Trigger:** certificato SSL `afianco.ch` scade in < 7 giorni.
**Razionale:** Let's Encrypt rinnova ogni 60 giorni via certbot
container, MA se certbot ha bug / quota / DNS issue il rinnovo fail
silently. Senza monitor scopriamo solo quando il browser merchant
mostra "Not Secure" → reputazione devastata.

| Field | Value |
|---|---|
| **Monitor type** | SSL/TLS |
| **Friendly name** | `[CRIT] TLS cert afianco.ch` |
| **Hostname** | `afianco.ch` |
| **Port** | `443` |
| **Alert before** | `7 days` |
| **Alert contacts** | `davide@afianco.ch` |

---

## Notification setup

**Single operator (open beta):**
- Email: `davide@afianco.ch` (Default + only contact)
- Mobile push: install UptimeRobot iOS/Android app → enable push per
  ogni monitor → push immediato senza email delay
- NO SMS (free tier non lo include)
- NO Slack/PagerDuty (decisione consapevole, vedi sentry-alert-rules.md)

**V2 (post-pilot, team > 1):**
- Aggiungere secondary contact (es. ops@afianco.ch group)
- Configure Slack integration (UptimeRobot → Integrations → Slack)
- Considerare PagerDuty per Monitor 1+2 (CRIT) solo

---

## Maintenance procedure

| Cadenza | Task |
|---|---|
| **Settimanale** | Login UptimeRobot dashboard, verify tutti 5 monitor "Up", review eventuali incident della settimana |
| **Mensile** | Verifica keyword check ancora funzioni (es. se cambiamo struttura JSON di /health/live il keyword "status:ok" potrebbe non matchare) |
| **Trimestrale** | Review false positive rate (es. monitor down per 30s ma backend ok) — adjust timeout o interval se necessario |
| **Post-incident** | Se outage NON catturato da monitor (false negative), add new monitor O affinare keyword |

---

## Test procedure (verify setup)

Dopo creazione, testa ogni monitor che fire correttamente:

### Test Monitor 1 (Backend liveness)

```bash
# Sul VPS, ferma backend temporaneamente (DEVE essere fuori orario, no
# customer impact):
ssh root@<vps> "docker stop ms-backend"

# Aspetta ≤10min (2 polling cycle UptimeRobot).
# Atteso: email "[Monitor is DOWN]" a davide@afianco.ch.

# Riavvia:
ssh root@<vps> "docker start ms-backend"

# Aspetta ≤10min.
# Atteso: email "[Monitor is UP]" con downtime duration.
```

### Test Monitor 5 (TLS)

Non possiamo "scadere" il cert per testare. In alternativa:
1. Verify che il monitor mostri "days until expiry" corretto nel dashboard
2. Se < 30 giorni: l'auto-renewal certbot dovrebbe scattare a 30 giorni
3. Se > 30 giorni: dashboard OK, alert fire solo a 7 giorni

---

## Endpoint pinning (anti-regression)

I 3 endpoint health (`/live`, `/ready`, `/ai`) sono il **contract pubblico
verso UptimeRobot**. Cambiarli (rinomare, rimuovere) **rompe** i monitor
senza errori visibili — UptimeRobot inizia a fail su keyword check.

Sentinel test `TestSEC_O_3_4_UptimeMonitoringRunbook` pinna:
- Esistenza dei 3 endpoint nel router `health.py`
- Keyword `"status":"ok"` nella response /live (matched dal monitor)
- Keyword `"mongodb":"ok"` nella response /ready (idem)

Refactor che cambia questi pattern fa fallire CI prima del deploy.

---

## Riferimenti

- `backend/routers/health.py` — implementazione endpoint
- `docs/operations/sentry-alert-rules.md` — alert rules application-level
  (complementare: Sentry vede errors interni, UptimeRobot vede outage
  esterni)
- `docs/operations/incident-response.md` — playbook quando monitor fire
- `docs/operations/runbook.md` — daily operator checklist

---

## Cosa NON e in questo runbook

- ❌ **Synthetic transaction monitoring** (es. "esegui un signup full e
  verify success"). UptimeRobot free tier non lo supporta. V2 con
  Playwright cron in GitHub Actions (Track O6).
- ❌ **Multi-region monitoring** (Asia-Pacific, US-East). Free tier
  monitora da location random; per multi-region serve paid plan.
- ❌ **Latency / Apdex monitoring** (es. "alert se p95 > 2s"). Free tier
  alert solo su availability, non latency. Per latency vedi Sentry
  performance dashboard (O1.2 traces sampling 0.0001 → statistical noise
  per ora).
- ❌ **Status page pubblica** (es. status.afianco.ch). UptimeRobot offre
  public status page free MA decisione consapevole NON pubblicarla in
  open beta: customer feedback channel via email diretto piu' adeguato
  per 50-200 merchant. V2 quando team > 1.

---

**Last reviewed:** 2026-05-29
**Next review:** post-O3 completion + 2 settimane di soak prod
