# Pre-Pilot Launch — Security Hardening Checklist

> Master checklist consolidato: tutti gli operator action item da
> completare PRIMA di portare il primo merchant pilot in production.
> **Track O Step 5.5 — final consolidation pre-pilot.**
>
> **Owner:** davide@afianco.ch
> **Pattern:** una operazione per riga, cross-link al runbook
> dedicato per la procedura completa.

---

## Quick reference — go/no-go criteria

Sono **READY per pilot** quando TUTTE le sezioni sotto sono ✅:

| Categoria | Status target | Verifica |
|---|---|---|
| **Sentry alert rules** | 6 rule attive web UI | Test ogni rule + verify email arriva |
| **UptimeRobot monitors** | 5 monitor attivi | Trigger test outage, verify alert |
| **DMARC** | minimo Phase 1 (`p=quarantine pct=10`) | `dig +short txt _dmarc.afianco.ch` |
| **HSTS** | header confermato (preload submission opzionale per pilot) | `curl -sI https://afianco.ch/ \| grep HSTS` |
| **Backup verified** | Restore drill recente < 30gg | Vedi `restore-drill-history.md` |
| **Secrets rotated** | JWT + Brevo + Anthropic recenti | Vedi `secrets-rotation.md` |
| **CI all green** | Latest main commit security + test pass | GitHub Actions tab |
| **Incident response** | Runbook letto + comprensibile | Self-review |

---

## Section A — Observability (Sub-Track O3) ✅

### A.1 Sentry alert rules setup
- [ ] Login Sentry web UI (DSN gia' configurato)
- [ ] Crea 6 alert rules per `docs/operations/sentry-alert-rules.md`:
  - [ ] `[P0] Payment failure spike`
  - [ ] `[P0] Auth failure spike`
  - [ ] `[P1] 500 error spike`
  - [ ] `[P1] New issue in production`
  - [ ] `[P1] Regression detected`
  - [ ] `[P2] Embed-SDK error spike`
- [ ] Verify notification routing → `davide@afianco.ch`
- [ ] Install Sentry mobile app + enable push notifications
- [ ] Test 1 rule (capture_exception sintetico con tag) → verify email/push

### A.2 UptimeRobot monitors setup
- [ ] Sign up uptimerobot.com con `davide@afianco.ch`
- [ ] Crea 5 monitor per `docs/operations/uptime-monitoring.md`:
  - [ ] `[CRIT] Backend liveness` (5min poll)
  - [ ] `[CRIT] Backend readiness` (5min poll)
  - [ ] `[MED] AI provider health` (15min poll)
  - [ ] `[CRIT] Frontend root` (5min poll)
  - [ ] `[CRIT] TLS cert afianco.ch` (1x/day SSL check)
- [ ] Install UptimeRobot mobile app + enable push
- [ ] Test 1 monitor (ferma container in ora off-peak) → verify alert

### A.3 Business metrics dashboard (optional V2)
- [ ] (Opzionale) Setup Grafana Cloud free tier + Prometheus
  remote_write da VPS — defer V2 se non serve subito
- [ ] (Opzionale) Import dashboard JSON — defer

---

## Section B — Auth abuse prevention (Sub-Track O4) ✅

### B.1 Anti-bot defenses verified
- [ ] Honeypot field rendering verified su entrambi i form
  (DevTools Inspector: `<input name="website">` con CSS hide presente)
- [ ] (Opzionale) hCaptcha (O4.4 deferred) — pre-pilot NON necessario,
  honeypot copre ~50% naive bot abuse

### B.2 Password security
- [ ] Verifica HIBP password breach check attivo
  (env var `PASSWORD_BREACH_CHECK_ENABLED` non false in produzione)
- [ ] Test: signup con password "Password1" → 400 "trovata in breach"

### B.3 Session security
- [ ] Test endpoint POST `/api/auth/logout-all` con token valid → 200
- [ ] Test successivo con stesso token → 401 "Sessione invalidata"
- [ ] Mirror per `/api/customer-auth/logout-all`

### B.4 Customer support tools
- [ ] Documentare procedura support in Notion / internal wiki:
  - Endpoint `POST /api/admin/users/{id}/verify-email` (verifica manuale)
  - Endpoint `POST /api/admin/users/{id}/unlock` (sblocco lockout)
  - Endpoint `POST /api/admin/users/{id}/reset-password` (reset)
- [ ] Backup operator (V2 — pilot single-operator OK)

---

## Section C — Email reputation hardening (Sub-Track O5) ✅

### C.1 Baseline current (✅ verified 2026-05-29)
- [x] SPF strict (`include:spf.brevo.com include:secureserver.net -all`)
- [x] DKIM brevo1 + brevo2 active
- [x] DMARC `p=none` monitoring
- [x] MX Microsoft 365

### C.2 DMARC upgrade (procedure 42-giorni)
- [ ] Aggiungi `rua=mailto:dmarc@afianco.ch` al TXT current (zero rischio)
- [ ] **POST PILOT LAUNCH** (non blocker pre-launch):
  - [ ] Phase 1: `p=quarantine pct=10` + soak 7gg
  - [ ] Phase 2: `p=quarantine pct=50` + soak 7gg
  - [ ] Phase 3: `p=quarantine pct=100` + soak 14gg
  - [ ] Phase 4: `p=reject pct=10` + soak 7gg
  - [ ] Phase 5: `p=reject pct=50` + soak 7gg
  - [ ] Phase 6: `p=reject pct=100` (FINAL)
- [ ] Vedi `docs/operations/dmarc-upgrade-procedure.md`

### C.3 HSTS preload submission (opzionale per pilot)
- [ ] (Opzionale pre-pilot) Submission a hstspreload.org
- [ ] Se SI: completa pre-checks 1-6 di `docs/operations/hsts-preload-submission.md`
- [ ] Se NO: ok, header gia' setta `preload` directive ready, submit
  in V2 quando subdomain inventory consolidato

---

## Section D — Infrastructure resilience

### D.1 Backup + restore drill
- [ ] Read `docs/operations/backup-recovery.md`
- [ ] Verify ultimo restore drill < 30 giorni in `restore-drill-history.md`
- [ ] Se obsoleto: esegui drill ora seguendo `restore-drill.md`
- [ ] Verify Hetzner Storage Box ha snapshot recente (< 24h)

### D.2 Secrets rotation
- [ ] Read `docs/operations/secrets-rotation.md`
- [ ] Verify JWT_SECRET_KEY rotated < 90 giorni
- [ ] Verify BREVO_API_KEY funzionante (test send via /api/admin/audit-logs?action=email_sent)
- [ ] Verify ANTHROPIC_API_KEY funzionante (vedi `/api/health/ai`)
- [ ] Documentare rotazione next due date in calendar

### D.3 CI/CD pipeline health
- [ ] GitHub Actions tab: ultimo commit main → both workflow green
- [ ] Nessun Dependabot PR aperto > 7 giorni (mergi o rejecta)
- [ ] Sentinel count: 717+ backend tests passing (vedi pytest)

---

## Section E — Operational readiness

### E.1 Runbooks letti
- [ ] `docs/operations/incident-response.md` — playbook severity matrix
- [ ] `docs/operations/runbook.md` — daily operator checklist
- [ ] `docs/operations/sentry-alert-rules.md` — quando fire ogni rule
- [ ] `docs/operations/uptime-monitoring.md` — UptimeRobot setup
- [ ] `docs/operations/email-reputation.md` — SPF/DKIM/DMARC baseline

### E.2 Communication setup
- [ ] Email `davide@afianco.ch` controllato almeno 1x/day
- [ ] Status communication template prepared (es. "Stiamo investigando un
  issue, update entro 1h") in Notion/draft
- [ ] (V2 quando team > 1) PagerDuty / Slack notification

### E.3 Pilot agreement readiness
- [ ] Pilot agreement template ready (best-effort support mon-fri 9-18 CET)
- [ ] SLA disclaimer chiaro (no 24/7 promise nel pilot)
- [ ] Comunicazione "in caso di issue scrivi a davide@afianco.ch +
  expected response time"

---

## Section F — Pre-launch smoke tests

Test manuale prima di go-live. Su produzione live.

### F.1 Anonymous flows
- [ ] GET `https://afianco.ch/` → 200, "AFianco" nel body
- [ ] GET `https://afianco.ch/api/health/live` → 200, `uptime_seconds` present
- [ ] GET `https://afianco.ch/api/health/ready` → 200, `mongodb: ok`
- [ ] GET `https://afianco.ch/api/health/ai` → 200, circuit_state present

### F.2 Auth flow merchant
- [ ] POST `/api/auth/signup` con email + password VALID → 202 verification_required
- [ ] Verify email arriva (controlla spam folder)
- [ ] Click verify link → email_verified=true (verify via /api/admin/users)
- [ ] POST `/api/auth/login` con stesso credentials → 200 + JWT
- [ ] GET `/api/users/me` con JWT → 200

### F.3 Auth flow customer
- [ ] POST `/api/customer-auth/signup` con slug + email → 202
- [ ] Verify customer email arriva
- [ ] Click verify → POST `/api/customer-auth/login` → 200 + customer JWT

### F.4 Anti-bot
- [ ] POST `/api/auth/signup` con `website: "spam.com"` → 202 (uniform success,
  ma audit log mostra action=`merchant_signup_honeypot`)
- [ ] POST `/api/auth/signup` con password "Password1" → 400 "trovata in breach"
- [ ] Burst 10x POST `/api/auth/signup` da stesso IP → 5° + bloccato slowapi 5/15min

### F.5 Webhook Stripe (test mode)
- [ ] Inietta evento test `checkout.session.completed` via Stripe CLI
- [ ] Verify `payments_total{event_type="checkout_completed",status="ok"}`
  counter incrementato in `/metrics`
- [ ] Verify audit log action mostra l'evento

### F.6 Sentry integration
- [ ] Trigger error sintetico (es. POST endpoint con body malformato)
- [ ] Verify event in Sentry inbox entro 1 min
- [ ] Verify tag `surface:api` presente

---

## Section G — Decision: GO / NO-GO

Sono PRONTO per il pilot quando:

- ✅ TUTTE le checkbox sopra (Section A-F) verificate
- ✅ Sentry + UptimeRobot live monitoring attivi
- ✅ Almeno 1 settimana di prod stable senza issue P0/P1
- ✅ Self-confidence: capisco cosa fare se hits the fan
- ✅ Pilot agreement firmato dal merchant

**Se SI a tutti**: invita primo merchant pilot.

**Se NO a uno**: NON LANCIARE. Ogni gap = increased risk profile, e
single-operator setup NON puo' permettere debugging in produzione mid-
incident con merchant attivi.

---

## Post-pilot iteration

Dopo 1-3 merchant pilot stable per 2-4 settimane:

1. **Review incidents.md** — se ZERO incident P0/P1, alza confidence
   livello → procedi a sub-track O7 (open beta full launch)
2. **Activate DMARC upgrade Phase 1** — se non gia' fatto pre-pilot
3. **Activate HSTS preload** — submit se subdomain inventory stable
4. **Plan O4.4 (hCaptcha)** — quando vedi bot abuse anche con honeypot
5. **Plan O6 (validation comprensiva)** — Playwright E2E + pen-test

---

## Riferimenti completi

Operatore runbooks (in ordine di lettura raccomandata):

1. `runbook.md` — daily checklist operativo
2. `incident-response.md` — quando hits the fan
3. `sentry-alert-rules.md` — what each alert means
4. `uptime-monitoring.md` — UptimeRobot setup
5. `email-reputation.md` — SPF/DKIM/DMARC baseline
6. `dmarc-upgrade-procedure.md` — DMARC reject procedura
7. `hsts-preload-submission.md` — HSTS preload submit
8. `secrets-rotation.md` — chiavi rotation cadence
9. `backup-recovery.md` — backup + restore
10. `restore-drill.md` — drill periodico
11. `data-retention.md` — GDPR retention policies
12. `security-headers.md` — header HTTP reference
13. `ai-baseline-2026-05.md` — AI provider config

---

**Last reviewed:** 2026-05-29
**Pilot target launch:** TBD by operatore (when all checkboxes ✅)
**Document version:** 1.0 (Track O Step 5.5 — final consolidation)
