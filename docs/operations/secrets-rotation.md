# Secrets Rotation Playbook — AFianco

How and when to rotate every credential / secret used by the production
stack. Used proactively (annual scheduled rotation) or reactively
(suspected compromise).

This document is the authoritative source for "what is sensitive, where
does it live, how do we change it without downtime."

---

## Inventory

Each row maps one secret to its **storage**, **blast radius if leaked**,
and **rotation cadence**. Sorted by severity.

| Secret | Where it lives | Severity | Rotation cadence | Blast radius if leaked |
|---|---|---|---|---|
| `MONGO_ROOT_PASSWORD` | `.env.production` | 🔴 Critical | 12 months | Full DB read/write/wipe |
| `JWT_SECRET_KEY` | `.env.production` | 🔴 Critical | 12 months | Forge any user session |
| `STRIPE_SECRET_KEY` | `.env.production` | 🔴 Critical | 12 months | Charge cards, refund, read PII |
| `BREVO_API_KEY` | `.env.production` | 🔴 Critical | 12 months | Send phishing as us, exfiltrate contact list |
| age private key | 1Password vault + USB key offline | 🔴 Critical | On compromise only | Decrypt all past + future Storage Box backups |
| `STRIPE_WEBHOOK_SECRET` | `.env.production` | 🟡 High | 12 months | Forge webhook events (e.g. fake refund "succeeded") |
| `STRIPE_WEBHOOK_SECRET_CONNECT` | `.env.production` | 🟡 High | 12 months | Same, on Connect events |
| `ANTHROPIC_API_KEY` | `.env.production` | 🟡 High | 12 months | API spend abuse, model output exfiltration |
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | `.env.production` | 🟡 High (only if S3 active) | 12 months | S3 bucket read/write; today S3 is inactive (empty values) |
| `SSH key` for Storage Box (`/root/.ssh/id_*`) | VPS server | 🟡 High | 24 months | Read/delete encrypted backups |
| `SSH key` GitHub deploy (if used) | VPS server | 🟡 High | 24 months | Pull repo, push (if rw) |
| `SENTRY_DSN` (backend) | `.env.production` | 🟢 Medium | 24 months | Inject fake events into the backend Sentry project |
| `REACT_APP_SENTRY_DSN` (frontend) | `.env.production` | 🟢 Medium | 24 months | Inject fake events into the frontend Sentry project |
| `STRIPE_CLIENT_ID` | `.env.production` (legacy, unused after Block 6) | 🟢 Medium | On rotation of others | Pre-Block-6 OAuth flow, deprecated |
| TLS certificates `/etc/letsencrypt/live/afianco.app/` | VPS server | 🟢 Medium | Every 60 days (auto via certbot) | Decrypt past traffic if combined with private key |

**Not secrets** (kept here for inventory clarity, never need rotation):
- `MONGO_ROOT_USER`, `STRIPE_PUBLISHABLE_KEY`, `DB_NAME`, `ENVIRONMENT`,
  `CORS_ORIGINS`, `*_URL`, `SMTP_FROM_*`, `LOG_*`, `RELEASE_SHA*`,
  `BACKGROUND_*`, `AWS_REGION`, `BACKUP_ALERT_EMAIL`, `*_SENTRY_TRACES_RATE`,
  `*_SENTRY_ENVIRONMENT`.

---

## Two playbooks

This document has TWO modes of operation:

- **A. Scheduled rotation** (proactive): annually on January 7th. Goal:
  reduce window of exposure. Plan downtime, communicate to users where
  needed (none today — all rotations are zero-downtime if executed in
  the documented order).
- **B. Compromise response** (reactive): a secret may have leaked
  (laptop stolen, repo accidentally public, dependency CVE, ...). Goal:
  revoke ASAP, then rotate. **Speed over elegance.**

The procedures below are the same body for both, with notes on what
"compromise mode" changes.

---

## Procedure 1 — `MONGO_ROOT_PASSWORD`

**Severity**: 🔴 Critical. **Downtime**: brief (~30 sec to restart container if needed; usually zero).

### Steps

```bash
# 1. Generate new strong password
NEW_PWD=$(openssl rand -hex 32)
echo "$NEW_PWD"   # save in 1Password BEFORE applying

# 2. Connect to mongo as current root and create the new password
ssh root@46.224.29.40
docker exec -it ms-mongodb mongosh \
    --username "$MONGO_ROOT_USER" \
    --authenticationDatabase admin \
    --eval "db.getSiblingDB('admin').changeUserPassword('$MONGO_ROOT_USER', '<NEW_PWD>')"

# 3. Edit .env.production with the new password
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^MONGO_ROOT_PASSWORD=.*|MONGO_ROOT_PASSWORD=<NEW_PWD>|" /opt/margin-sentinel/.env.production

# 4. Restart backend (mongo container does NOT need restart — password change is in DB)
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: `curl https://afianco.app/api/health/ready` → `mongodb: ok`.

**Compromise mode**: do NOT keep the old password as a fallback. If the
attacker had write access, audit `db.users.find()` for unfamiliar admins
and `db.audit_logs` for last 7 days of suspicious actions.

---

## Procedure 2 — `JWT_SECRET_KEY`

**Severity**: 🔴 Critical. **Downtime**: ~10 sec. **Side effect**: every
existing session is invalidated — all users must log in again.

### Steps

```bash
# 1. Generate
NEW_JWT=$(openssl rand -hex 32)
echo "$NEW_JWT"   # 1Password

# 2. Backup + edit
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_JWT|" /opt/margin-sentinel/.env.production

# 3. Restart
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: existing user attempts request → 401 (token invalid). Same
user logs in → new token issued, requests work.

**User-facing**: send a maintenance email if this is a scheduled
rotation in business hours. If reactive (compromise), don't email —
just rotate, users will see "session expired" which is a normal UX.

**Compromise mode**: also invalidate all `password_reset_tokens` and
`email_verify_tokens` (they were signed with the old secret too):

```javascript
// In mongosh
db.users.updateMany({}, { $unset: {
    password_reset_token_hash: "",
    password_reset_expires_at: "",
    email_verify_token_hash: "",
    email_verify_expires_at: ""
}});
```

---

## Procedure 3 — `STRIPE_SECRET_KEY`

**Severity**: 🔴 Critical. **Downtime**: zero (rotation is dual-key).

### Steps

```text
1. Open https://dashboard.stripe.com/apikeys
2. "Create restricted key" with the same scopes as the current one
   (or "Roll secret key" for live mode — irreversible after 12h grace)
3. Copy the new sk_live_... value (shown ONCE)
```

```bash
# 4. Update .env.production
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=<NEW_KEY>|" /opt/margin-sentinel/.env.production

# 5. Restart backend
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: trigger a `checkout/sessions` API call (or wait for the
next real customer order). Stripe Dashboard → Logs should show the
request authenticated with the new key.

**Compromise mode**: in Stripe Dashboard, REVOKE the old key immediately
(don't wait the 12h grace). Then audit Payments tab for the last 24h
for any unrecognized refunds, transfers, or PaymentIntents.

---

## Procedure 4 — `BREVO_API_KEY`

**Severity**: 🔴 Critical. **Downtime**: zero (instant cutover).

### Steps

```text
1. Open https://app.brevo.com/settings/keys/smtp
2. "Create new SMTP & API key" → name "afianco-prod-YYYYMMDD"
3. Copy the new xkeysib-... value
```

```bash
# 4. Update + restart
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^BREVO_API_KEY=.*|BREVO_API_KEY=<NEW_KEY>|" /opt/margin-sentinel/.env.production
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: trigger a forgot-password (any non-existent email) → check
Brevo dashboard "Transactional emails" → see the request with the new key.

**Then**: in Brevo dashboard, **DELETE the old key**. (Brevo doesn't
auto-deactivate.)

**Compromise mode**: also check Brevo "Sent emails" log for the last
24h — if the attacker sent phishing as `noreply@afianco.app`, you need
to draft a notice email to recipients (or in worst case, change SPF /
DKIM to break the attacker's existing campaigns).

---

## Procedure 5 — age private key (backup encryption)

**Severity**: 🔴 Critical. **Downtime**: zero. **Special**: dual-key
overlap to keep old backups decryptable.

### Steps

```bash
# 1. Generate new keypair on a CLEAN machine (NOT the prod VPS)
age-keygen -o /tmp/new_age_key.txt

# 2. Save the new PRIVATE key (3 lines) to 1Password + USB
#    LABEL: "AFianco / Production / age backup encryption key — rotated YYYY-MM-DD"
#    KEEP the OLD key in a separate 1Password item labeled
#    "age legacy until YYYY-MM-DD+30days" — you need it to decrypt
#    backups created before the rotation, until they age out (30-day retention).

# 3. Update the public key in the repo
new_pubkey=$(grep "^# public key:" /tmp/new_age_key.txt | sed 's/^# public key: //')
# Edit deploy/age_pubkey.txt — replace the only non-comment line

# 4. rsync new pubkey to server
rsync deploy/age_pubkey.txt root@46.224.29.40:/opt/margin-sentinel/deploy/age_pubkey.txt

# 5. NO restart needed — backup.sh re-reads the pubkey on every cron run
#    Tonight's 03:00 backup will use the new pubkey automatically

# 6. Securely delete the local /tmp/new_age_key.txt
shred -u /tmp/new_age_key.txt
```

**Verify**: tomorrow morning, check the new backup file on Storage Box,
download a copy, and decrypt with the NEW private key from 1Password.
Should round-trip cleanly.

**Compromise mode**: rotate IMMEDIATELY, don't wait. The compromise
window means an attacker can decrypt any backup made before the
rotation — but rotation does NOT retroactively re-encrypt. Acceptable
trade-off: the old backups age out within 30 days under retention.

---

## Procedure 6 — `STRIPE_WEBHOOK_SECRET` + `STRIPE_WEBHOOK_SECRET_CONNECT`

**Severity**: 🟡 High. **Downtime**: brief (between rotation and our
backend pickup, webhooks may fail signature verification — Stripe will
retry for 3 days, so a few-minute gap is harmless).

### Steps

```text
1. Stripe Dashboard → Developers → Webhooks
2. Open the relevant endpoint (one for STRIPE_WEBHOOK_SECRET, one for
   STRIPE_WEBHOOK_SECRET_CONNECT)
3. "Roll signing secret" → copy new whsec_...
```

```bash
# 4. Update + restart for each secret
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=<NEW_VALUE>|" /opt/margin-sentinel/.env.production
sed -i "s|^STRIPE_WEBHOOK_SECRET_CONNECT=.*|STRIPE_WEBHOOK_SECRET_CONNECT=<NEW_VALUE_CONNECT>|" /opt/margin-sentinel/.env.production
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: from Stripe Dashboard → Webhooks → "Send test webhook" →
our backend should accept it (200 in webhook delivery log).

**Compromise mode**: same procedure, just no "test webhook" delay —
roll, verify, monitor.

---

## Procedure 7 — `ANTHROPIC_API_KEY`

**Severity**: 🟡 High. **Downtime**: zero.

### Steps

```text
1. Open https://console.anthropic.com/settings/keys
2. "Create key" → label "afianco-prod-YYYYMMDD"
3. Copy sk-ant-...
```

```bash
# 4. Update + restart
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=<NEW_KEY>|" /opt/margin-sentinel/.env.production
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: trigger an AI chat from the admin UI → response arrives.
In Anthropic console, the new key has `last used: <few seconds ago>`.

**Then**: revoke old key in Anthropic console.

**Compromise mode**: check `console.anthropic.com` Usage tab for
unexpected token spikes in the last 24h. If yes, lock down billing
limit while investigating.

---

## Procedure 8 — `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`

**Severity**: 🟡 High (when active; today's `.env.production` has empty
values → S3 backup feature inactive, no rotation needed).

### Steps (when active)

```text
1. AWS Console → IAM → Users → "afianco-s3-backup" → Security credentials
2. Create access key → tag "afianco-prod-YYYYMMDD"
3. Copy AccessKeyId + SecretAccessKey
```

```bash
# 4. Update both vars + restart
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=<NEW_AKID>|" /opt/margin-sentinel/.env.production
sed -i "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=<NEW_SAK>|" /opt/margin-sentinel/.env.production
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

**Verify**: trigger an upload that copies to S3 → file appears in bucket.

**Then**: deactivate the old access key in IAM console (don't delete
yet — keep for 7 days as fallback).

---

## Procedure 9 — SSH key for Storage Box

**Severity**: 🟡 High. **Downtime**: zero (dual-key overlap).

### Steps

```bash
# 1. Generate new keypair on the prod VPS
ssh root@46.224.29.40
ssh-keygen -t ed25519 -f /root/.ssh/storage_box_new -C "afianco-storage-box-rotated-$(date +%Y%m%d)"

# 2. Add the new pubkey to Storage Box
ssh-copy-id -i /root/.ssh/storage_box_new.pub -p 23 u578174@u578174.your-storagebox.de

# 3. Test new key works
ssh -i /root/.ssh/storage_box_new -p 23 u578174@u578174.your-storagebox.de "ls afianco-backups/" | head -3

# 4. Update backup.sh to use new key (or move new -> default key)
mv /root/.ssh/id_ed25519 /root/.ssh/id_ed25519.OLD
mv /root/.ssh/id_ed25519.pub /root/.ssh/id_ed25519.OLD.pub
mv /root/.ssh/storage_box_new /root/.ssh/id_ed25519
mv /root/.ssh/storage_box_new.pub /root/.ssh/id_ed25519.pub

# 5. Test backup.sh manual run
bash /opt/margin-sentinel/deploy/backup.sh

# 6. Once confirmed working, remove old pubkey from Storage Box
sftp -P 23 u578174@u578174.your-storagebox.de
> get .ssh/authorized_keys /tmp/auth_keys
# Edit /tmp/auth_keys removing the old entry
> put /tmp/auth_keys .ssh/authorized_keys
> bye

# 7. Securely delete old key
shred -u /root/.ssh/id_ed25519.OLD /root/.ssh/id_ed25519.OLD.pub
```

---

## Procedure 10 — `SENTRY_DSN` (backend + frontend)

**Severity**: 🟢 Medium. **Downtime**: zero (instant cutover).

### Steps (per project)

```text
For backend (afianco-backend project):
1. Sentry → Settings → Projects → afianco-backend → Client Keys (DSN)
2. "Generate new key" → label "rotated-YYYYMMDD"
3. Copy the new DSN

For frontend (afianco-frontend project): same path under afianco-frontend.
```

```bash
# 4. Update env + rebuild image (frontend) or just restart (backend)
ssh root@46.224.29.40
cp /opt/margin-sentinel/.env.production /opt/margin-sentinel/.env.production.backup.$(date +%Y%m%d-%H%M%S)
sed -i "s|^SENTRY_DSN=.*|SENTRY_DSN=<NEW_BACKEND_DSN>|" /opt/margin-sentinel/.env.production
sed -i "s|^REACT_APP_SENTRY_DSN=.*|REACT_APP_SENTRY_DSN=<NEW_FRONTEND_DSN>|" /opt/margin-sentinel/.env.production

# 5. Restart backend (env runtime)
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend

# 6. REBUILD frontend (env baked at build time) + restart
docker compose -f docker-compose.prod.yml --env-file .env.production build frontend
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate frontend
```

**Verify**: trigger an error in admin UI → confirm event appears in
Sentry under the new DSN's project.

**Then**: in Sentry, deactivate the old client key.

---

## Annual rotation calendar

Schedule a recurring 2-hour block once a year — January 7th 14:00 UTC.

Order (designed to minimize cumulative downtime — each item picks up
where the previous one left off):

| Order | Item | Time |
|---|---|---|
| 1 | Backup `MONGO_ROOT_PASSWORD` | 10 min |
| 2 | Backup `JWT_SECRET_KEY` (ALL users will need to log in again) | 10 min |
| 3 | `BREVO_API_KEY` | 10 min |
| 4 | `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `..._CONNECT` | 20 min |
| 5 | `ANTHROPIC_API_KEY` | 10 min |
| 6 | `AWS_*` (skip if S3 inactive) | 10 min |
| 7 | `SENTRY_DSN` (backend + frontend) | 20 min |
| 8 | age private key (backup encryption) | 15 min |
| 9 | SSH Storage Box key | 15 min |
| **Total** | | **~2h** |

Then update the change log at the bottom of this file.

---

## Compromise response — quick reference

When you suspect a leak:

1. **TRIAGE** (5 min): which secret? evidence? scope?
2. **REVOKE** (5 min): in the upstream provider (Stripe, Brevo, Anthropic,
   ...), revoke the old credential immediately.
3. **ROTATE** (15 min): generate new + update `.env.production` + restart
   the relevant service.
4. **AUDIT** (1-2h): check provider logs for the last 7 days for
   suspicious activity. Pull MongoDB audit_logs for the same window.
5. **NOTIFY** (1h): if customer data may have been accessed, draft GDPR
   breach notification to data subjects (72-hour deadline to authority
   per GDPR Art. 33).
6. **POST-MORTEM** (within 1 week): how did the leak happen? what's the
   structural fix? Append to `docs/operations/incidents.md`.

---

## Change log

| Date | Action | Operator | Notes |
|---|---|---|---|
| 2026-05-08 | Initial playbook + `EMERGENT_LLM_KEY` flagged for removal at next rotation | runbook owner | Phase 1 Step E2 |
| 2026-05-14 | Removed `EMERGENT_LLM_KEY` from all configs + `@emergentbase/visual-edits` dep + obsolete `backend/backend_test.py` (legacy platform fully dismissed) | davide | Pillar 2 sidecar cleanup |
| 2026-05-29 | Added `METRICS_AUTH_TOKEN` to inventory (Track S Step 4.1) | claude | New secret per `/metrics` Prometheus endpoint auth |
| 2026-05-29 | Track S Step 1.2 — keys storicamente esposte (commit 287c633→1aeb4d7) **non ancora ruotate** (utente azione richiesta): `JWT_SECRET_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY` (test), `STRIPE_CLIENT_ID` | claude | See "Track S Step 1.2 — Pending rotation" section below |
| 2026-05-29 | Track S Step 1.2 — **Rotated**: `JWT_SECRET_KEY` (openssl rand -hex 32), `ANTHROPIC_API_KEY` (new key in console, old revoked) | davide | 2/4 P0/P1 keys rotated |
| 2026-05-29 | Track S Step 1.2 — Stripe test key deferred V2 (P2 accepted residual risk) — test mode no fondi reali → blast radius basso. Rotation P0 al passaggio a sk_live_* (Track F pilot live) | davide | Decisione esplicita post-audit |

---

## Track S Step 1.2 — Pending rotation (URGENT)

**Audit `2026-05-29` (Track S Step 1.1)** ha confermato che le chiavi
storicamente esposte in `backend/.env` (committed tra `287c633` e
`1aeb4d7`) **non sono state ruotate** dopo il commit di hardening
`1aeb4d7` (2026-04-22). Il commit msg di `1aeb4d7` conteneva un
"REMINDER: rotate" — l'azione e' overdue di ~5 settimane.

**Repo PRIVATO** (verified 2026-05-28) → exposure limitata a chi ha
clone access (utente + AI services autorizzati + GitHub support).
**Non è una crisi immediata** ma va chiusa prima di:
- Track E (CDN distribution) — push CDN apre superfici
- Track F (pilot merchant) — esterni col repo nelle dipendenze
- Apertura del repo a contributor esterni

### Stato per chiave

| Chiave | Status | Priorità | Where to rotate |
|---|---|---|---|
| `JWT_SECRET_KEY` | ✅ **Ruotata 2026-05-29** | DONE | `openssl rand -hex 32` (256-bit entropy, hex 64 char) |
| `ANTHROPIC_API_KEY` | ✅ **Ruotata 2026-05-29** | DONE | Console Anthropic, vecchia revoked |
| `STRIPE_SECRET_KEY` (test) | 🟡 ESPOSTA, **deferred V2** | **P2** (accepted residual risk) | Test mode → no fondi reali → low blast radius. Rotation P0 quando si passa a `sk_live_*` (Track F pilot live payments) |
| `STRIPE_CLIENT_ID` | 🟡 ESPOSTA, non ruotata | **P2** (deferred V2) | Revoca richiede ri-connettere TUTTI i merchant Stripe Connect — too invasive per V1 |
| `EMERGENT_LLM_KEY` | ✅ Rimossa dal `.env` | OK | Key non più in uso (commit 2026-05-14) |
| `BREVO_API_KEY` | ✅ Mai esposta in git | OK | Aggiunta post-untrack |

### Procedura step-by-step

1. **JWT_SECRET_KEY** (2 min, locale)
   ```bash
   openssl rand -hex 32
   # Copia output e sostituisci in backend/.env: JWT_SECRET_KEY="..."
   # Restart uvicorn — tutte le sessioni admin invalidate (effetto desiderato)
   ```

2. **ANTHROPIC_API_KEY** (5 min, dashboard)
   - Vai su https://console.anthropic.com/settings/keys
   - Click "Create Key" (nome: `afianco-2026-05-29-rotation`)
   - Copia + sostituisci in `backend/.env`: `ANTHROPIC_API_KEY=sk-ant-...`
   - Restart uvicorn
   - Torna in console → **revoca** la vecchia key (`...DH4TG9R24T...`)

3. **STRIPE_SECRET_KEY** test → **DEFERRED V2** (vedi policy sotto)
   - Test keys non danno accesso a fondi reali (test mode isolato)
   - Blast radius leak: basso (max spam test API, non fraud)
   - **Rotation policy**: P2 differita per test keys, P0 immediata per live
   - Quando passi a `sk_live_*` (Track F pilot pagamenti veri):
     - Rotation diventa P0 (12 mesi cadenza + immediata su sospetto leak)
     - Procedura: dashboard.stripe.com/apikeys → "Roll key" → 60min grace

4. **POST-rotation verify**:
   ```bash
   cd backend && ./venv/bin/pytest tests/test_invariants_security.py -q
   # 161/161 verdi attesi (nessun dipendenza dalle key esatte)
   ```

5. **Append a questo changelog**:
   ```markdown
   | 2026-MM-DD | Track S Step 1.2 — Rotated JWT_SECRET_KEY, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY post-S1.1 audit | davide | All P0/P1 keys rotated |
   ```

---

## Cross-references (Track S Step 6.3)

- [`docs/SECURITY_HARDENING.md`](../SECURITY_HARDENING.md) — security
  policy + sentinel test catalog
- [`SECURITY.md`](../../SECURITY.md) — vulnerability reporting policy
- [`docs/operations/TESTING.md`](TESTING.md) — test suite runbook
- [`backend/.env.example`](../../backend/.env.example) — env var template
