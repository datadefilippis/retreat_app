# Incident Response Plan

> Authoritative playbook per gestire incident di sicurezza, downtime,
> data loss, e breach durante pilot + open-beta. **Track L Step 2.**

---

## Quick reference (when shit hits the fan)

1. **Triage** (5 min): assegna severity (P0/P1/P2/P3 — vedi tabella sotto)
2. **Mitigate** (immediate): contenimento — feature flag off, IP block, rollback
3. **Comm internal** (15 min): Slack/email a backup operator
4. **Investigate** (h-1): root cause via logs + Sentry
5. **Comm external** (se P0/P1 customer-facing): status update + GDPR breach if PII leak
6. **Fix** (h-? depends): patch + verify
7. **Post-mortem** (within 48h): append a `docs/operations/incidents.md`

---

## Severity matrix

| Sev | Definition | Examples | Response time | Communication |
|---|---|---|---|---|
| **P0** | Payment/auth broken, data loss, security breach con PII leak, total outage | Stripe webhook fail al 100%, JWT bypass discovered, MongoDB compromise, customer data esfiltrato | **15 min triage**, immediate page | Status page + email tutti customer + GDPR Art. 33 (72h to authority) |
| **P1** | Single service degraded, partial data loss risk, security vuln senza exploit attivo | Embed-SDK broken per 1 merchant, slow API responses (>2s p95), CVE Critical published su dep usata | **1h triage** | Internal Slack + status page se prolonged (> 1h) |
| **P2** | Feature non funzionante, no data risk, workaround disponibile | Email transazionali in delay, admin UI bug, single customer logged-out spam | **4h triage** | Internal Slack, comm a customer affected solo se reporta |
| **P3** | Cosmetic, typo, performance minor | UI label wrong, slow non-critical endpoint, error log noise | **next business day** | Issue tracker (GitHub Issues), no escalation |

---

## On-call rotation

| Tier | Name | Channel | Pager | Backup |
|---|---|---|---|---|
| Primary | David | Email/SMS davidedefilippis94@gmail.com | (none — pilot phase) | Self (sole maintainer) |
| Secondary (V2 open-beta) | TBD | TBD | TBD | TBD |

**Pilot phase**: single operator (David). No 24/7 SLA promesso a customer.
Pilot agreement deve esplicitamente menzionare "best-effort support
mon-fri 9-18 CET".

**Open-beta (post-Track F)**: aggiungere secondary operator + tools:
- PagerDuty (or AWS SNS) per P0/P1 paging
- Status page (statuspage.io, instatus, hosted)
- On-call calendar (weekly rotation)

---

## Decision tree — è un incident?

```
Errore segnalato (customer / monitoring / Sentry)
        │
        ▼
    Data loss / PII leak?    ─── Yes ──► P0
        │ No
        ▼
    Payment broken?          ─── Yes ──► P0
        │ No
        ▼
    Security vuln in code?   ─── Yes ──► P0 (exploit) / P1 (theoretical)
        │ No
        ▼
    Total service outage?    ─── Yes ──► P0
        │ No
        ▼
    Single service degraded? ─── Yes ──► P1
        │ No
        ▼
    Feature non funziona,    ─── Yes ──► P2
    workaround disponibile?
        │ No
        ▼
    Cosmetic / minor             ──────► P3
```

---

## Communication templates

### P0 customer-facing (status page + email)

```
[STATUS] [P0] Service disruption — investigating

Time: <UTC + CET>
Affected: <e.g. embed widget checkout, customer login>
Impact: <e.g. customers unable to complete purchases>

We're investigating an issue affecting <service>. Our team is engaged
and we're working on resolution.

Next update: <30 min from now>

— AFianco team
```

### GDPR breach notification (if PII leaked)

**Legal deadline**: 72 hours from awareness, to data protection authority
(Garante per la Protezione dei Dati Personali in IT).

Use template at https://www.garanteprivacy.it/web/guest/home/docweb/-/docweb-display/docweb/9476758
(Italian DPA breach notification form).

**Required fields**:
- Nature of the breach
- Categories of data affected (email, name, address, payment data, etc.)
- Approximate number of subjects
- Consequences (likely impact on subjects)
- Measures taken / proposed

**Internal flow**:
1. Hour 0: discovery → start `incidents.md` entry, freeze deploys
2. Hour 0-24: scope assessment (how many records? which fields?)
3. Hour 24-48: legal review + breach notification draft
4. Hour 48-72: submit to Garante + notify affected subjects
5. Hour 72+: public post-mortem (no PII) on blog/status page

---

## Triage runbook — first 15 minutes

When notified of a potential incident:

1. **Acknowledge** (1 min): reply "investigating" su channel di reporting
2. **Reproduce** (3 min): can you trigger the issue locally / staging?
3. **Scope** (5 min): grep logs, query DB, check Sentry:
   ```bash
   # MongoDB recent errors (audit_logs)
   db.audit_logs.find({severity: "error", created_at: {$gte: <last 1h>}}).limit(20)

   # Sentry
   # → https://sentry.io/issues/?project=afianco&statsPeriod=24h

   # Prometheus (request rate / error rate)
   # → /metrics endpoint con METRICS_AUTH_TOKEN

   # Application logs (uvicorn output)
   journalctl -u afianco-backend --since "1 hour ago" | grep ERROR | head -50
   ```
4. **Classify** (2 min): use Decision Tree above → assign P0/P1/P2/P3
5. **Mitigate** (4 min if P0/P1): feature flag off, IP block, scale down
   request rate, rollback last deploy. Use:
   ```bash
   # Rollback last commit
   git revert HEAD --no-edit && git push

   # Disable specific feature via env flag
   # (es. IDEMPOTENCY_ENFORCED=false for emergency unblock)

   # IP block via nginx
   echo "deny <ip>;" >> /etc/nginx/conf.d/blocklist.conf
   nginx -s reload
   ```

---

## Mitigation playbook per scenario comune

### Webhook flood (Stripe replay attack o bug client)

```bash
# Stripe dashboard → Webhooks → temporarily disable endpoint
# https://dashboard.stripe.com/webhooks

# Local: verify idempotency cache is working
mongo > db.idempotency_keys.count({created_at: {$gte: <last 1h>}})
# If absurdly high (>10k/h), likely under attack — investigate via IP
```

### Account compromise reported (customer says "non sono io a fare ordini")

```bash
# 1. Invalidate ALL sessions of that customer:
mongo > db.customer_accounts.update(
  {id: "<customer_id>"},
  {$set: {password_changed_at: ISODate()}}
)
# Tutti i JWT precedenti diventano invalid (auth.py:175-202 check)

# 2. Force password reset email
# (use customer-auth/forgot-password endpoint, manual trigger)

# 3. Audit log inspection
mongo > db.audit_logs.find({actor_id: "<customer_id>"}).sort({created_at:-1}).limit(50)
```

### Database compromise suspected

```bash
# 1. IMMEDIATE: rotate MONGO_URL password
# (Atlas dashboard → Database → Connect → Edit user)

# 2. Restart all backend instances con new MONGO_URL

# 3. Audit recent admin queries (Atlas Profiler):
# Atlas → Performance Advisor → Profiler

# 4. Triggera GDPR breach notification timer (72h)

# 5. Restore from backup if needed (vedi backup-recovery.md)
```

### Stripe API key leaked

```bash
# 1. Stripe dashboard → API keys → "Roll key" (vecchia scade in 60min)
# 2. Update .env.production + restart backend
# 3. Monitor Stripe Radar for suspicious activity ultime 24h
# 4. Append a docs/operations/secrets-rotation.md changelog
```

### CVE Critical published su dep usata

```bash
# 1. Check pip-audit / pnpm audit per detail
# 2. Patch in branch dedicato: deps/cve-<CVE-ID>-fix
# 3. Test locale: full regression suite
# 4. Deploy con feature flag off se possible
# 5. Append a SECURITY_HARDENING.md residual risk update
```

---

## Post-mortem template (append a `incidents.md`)

```markdown
## Incident YYYY-MM-DD — <short title>

**Severity**: P<0/1/2/3>
**Duration**: <hh:mm to hh:mm UTC> (total <X min>)
**Affected**: <service / customer count / data records>
**Root cause**: <1-2 sentences>

### Timeline (UTC)

- HH:MM — Issue detected via <channel>
- HH:MM — Triage started, severity P<X>
- HH:MM — Mitigation: <action>
- HH:MM — Root cause identified
- HH:MM — Fix deployed
- HH:MM — Service restored
- HH:MM — Customer comm sent
- HH:MM — Closed

### Root cause (technical)

<3-5 sentences explaining what broke and why>

### Impact

- Customer affected: <count>
- Data lost / corrupted: <yes/no, scope>
- Revenue impact: <Euro estimate if known>
- Reputation impact: <low/medium/high>

### Mitigations applied

1. <immediate action 1>
2. <immediate action 2>

### Long-term remediation (action items)

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | <e.g. add sentinel test for this regression> | David | YYYY-MM-DD | [ ] |
| 2 | <e.g. document this scenario in runbook> | David | YYYY-MM-DD | [ ] |

### Lessons learned

<2-3 bullets: what would catch this earlier, what process to add>

### GDPR notification

- Subjects affected: <count> / 0 (no PII)
- Notification to Garante: <yes/no, date>
- Notification to subjects: <yes/no, date, template used>
```

---

## Tools + access

| Tool | URL | Why | Who has access |
|---|---|---|---|
| Sentry | https://sentry.io/ | Real-time error tracking | David |
| MongoDB Atlas | https://cloud.mongodb.com | DB admin + backups | David |
| Stripe dashboard | https://dashboard.stripe.com | Payment + webhook + Connect | David |
| Brevo dashboard | https://app.brevo.com | Email + bounce monitoring | David |
| Anthropic console | https://console.anthropic.com | LLM usage + key mgmt | David |
| GitHub Actions | https://github.com/datadefilippis/BI_PMI/actions | CI status | David |
| Domain DNS | <provider TBD> | DNS records (SPF/DKIM/DMARC) | David |
| nginx config | server ssh | Reverse proxy + rate limit | David |

---

## Cross-references

- [`docs/operations/runbook.md`](runbook.md) — 10 operational procedures
- [`docs/operations/secrets-rotation.md`](secrets-rotation.md) — secret rotation playbook
- [`docs/operations/backup-recovery.md`](backup-recovery.md) — backup + restore
- [`docs/operations/restore-drill-history.md`](restore-drill-history.md) — monthly restore drills
- [`docs/operations/incidents.md`](incidents.md) — append-only post-mortem log (created next incident)
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy
- [`docs/SECURITY_HARDENING.md`](../SECURITY_HARDENING.md) — security policy detail

---

_Last updated: 2026-05-29 — Track L Step 2_
