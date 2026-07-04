# AFianco Operations Runbook

10 procedures for recurring operational tasks. Each is self-contained: in
panic mode at 03:00, jump straight to the relevant section without reading
anything else. All procedures assume:

- SSH access to the production VPS: `ssh root@46.224.29.40`
- Production stack: `/opt/margin-sentinel/` with `docker-compose.prod.yml`
- Containers: `ms-backend`, `ms-frontend`, `ms-mongodb`, `ms-nginx`
- DB: `margin_sentinel` (MongoDB 7.0)
- Storage Box: `u578174@u578174.your-storagebox.de:afianco-backups/` (port 23, SFTP)
- Public URL: `https://afianco.app`

When in doubt, **prefer the safer of two options** and check Sentry +
healthcheck before declaring an issue resolved.

---

## Quick index

1. [Reset admin password (user locked out of UI)](#1-reset-admin-password)
2. [Unlock account (admin or customer, post-bruteforce)](#2-unlock-account)
3. [Manual Stripe refund](#3-manual-stripe-refund)
4. [Replay missed Stripe webhook](#4-replay-stripe-webhook)
5. [Rolling restart backend (zero downtime)](#5-rolling-restart-backend)
6. [Partial restore (one MongoDB collection)](#6-partial-restore-collection)
7. [Debug a stuck order](#7-debug-stuck-order)
8. [Throttle / block abusive IP at nginx](#8-throttle-abusive-ip)
9. [Update a Python dependency safely](#9-update-python-dependency)
10. [Emergency hotfix deploy](#10-emergency-hotfix-deploy)

---

## 1. Reset admin password

**When**: an admin (User table, role=admin/owner/system_admin) is locked
out and forgot-password email is unreachable (lost mailbox, Brevo down,
spam folder, ...).

**Pre-req**: SSH access; you know the user's email or `id`.

```bash
ssh root@46.224.29.40
docker exec -it ms-mongodb mongosh \
    --username "${MONGO_ROOT_USER:-margin_admin}" \
    --authenticationDatabase admin \
    margin_sentinel
```

Inside `mongosh`:

```javascript
// 1. Find the user
db.users.findOne({ email: "USER_EMAIL_HERE" }, { id: 1, email: 1, role: 1, organization_id: 1 });

// 2. Set a temporary password — bcrypt hash of "TempPass2026!"
//    (regenerate with: docker exec ms-backend python -c
//     "from passlib.hash import bcrypt; print(bcrypt.hash('TempPass2026!'))")
db.users.updateOne(
  { email: "USER_EMAIL_HERE" },
  { $set: {
      password_hash: "<NEW_BCRYPT_HASH>",
      password_changed_at: new Date(),
      // Reset lockout state too
      failed_login_attempts: 0,
      locked_until: null,
      lockout_count_today: 0
  }}
);
```

**Tell the user**: "Login with `TempPass2026!`, then immediately change
password via `/account/change-password`. The temporary password expires
at next login automatically (forces password change UI flow)."

**Verification**: user logs in → reaches change-password screen → sets
new password → can use the app normally.

**Audit**: this bypass is loggable. Add an entry manually:

```javascript
db.audit_logs.insertOne({
  id: UUID().toString(),
  actor_user_id: "manual-runbook-reset",
  actor_role: "system_admin",
  organization_id: <ORG_ID>,
  action: "USER_PASSWORD_RESET_BY_OPERATOR",
  target_type: "user",
  target_id: <USER_ID>,
  metadata: { reason: "<short reason>", reset_by_human: "your-name" },
  created_at: new Date().toISOString(),
  expire_at: new Date()  // BSON Date for TTL
});
```

---

## 2. Unlock account

Onda 29 (customer) and Onda 30 (admin User) both ship a per-account
lockout that triggers after 5 failed login attempts. Lockout escalates
exponentially (15, 30, 60, 120, 240, 480, 960, 1440 minutes).

### 2a — Admin User (Onda 30)

Via the API endpoint (preferred — keeps audit trail):

```bash
ssh root@46.224.29.40

# Get a system_admin JWT first
SYSADMIN_TOKEN=$(curl -s -X POST https://afianco.app/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"YOUR_SYSADMIN_EMAIL","password":"YOUR_SYSADMIN_PASS"}' \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Unlock the target user (replace USER_ID)
curl -X POST https://afianco.app/api/admin/users/USER_ID/unlock \
    -H "Authorization: Bearer ${SYSADMIN_TOKEN}"
```

Or directly in MongoDB if the API path is broken:

```javascript
// Inside mongosh on margin_sentinel
db.users.updateOne(
  { email: "USER_EMAIL" },
  { $set: { failed_login_attempts: 0, locked_until: null, lockout_count_today: 0 }}
);
```

### 2b — Customer (Onda 29)

```bash
curl -X POST https://afianco.app/api/admin/customer-accounts/CUSTOMER_ID/unlock \
    -H "Authorization: Bearer ${SYSADMIN_TOKEN}"
```

Or in MongoDB:

```javascript
db.customer_accounts.updateOne(
  { email: "CUSTOMER_EMAIL", organization_id: ORG_ID },
  { $set: { failed_login_attempts: 0, locked_until: null, lockout_count_today: 0 }}
);
```

**Verification**: ask the user to attempt login. Sentry should NOT
record an `ACCOUNT_LOCKED` event for them again unless they fail 5x more.

---

## 3. Manual Stripe refund

**When**: a customer asks for a refund and Stripe Connect Express does
not auto-route the request.

**Pre-req**: Stripe Dashboard access (`dashboard.stripe.com`), Connect
Account ID of the merchant, the `payment_intent_id` or `charge_id` from
our DB.

### Step 1 — Find the payment intent

```javascript
// In mongosh
db.orders.findOne(
  { id: "ORDER_ID" },
  { id: 1, status: 1, stripe_payment_intent_id: 1, stripe_account_id: 1, amount_cents: 1 }
);
```

Note the `stripe_payment_intent_id` (starts with `pi_`).

### Step 2 — Issue refund via Stripe Dashboard

1. Open https://dashboard.stripe.com/connect/accounts (Connect view)
2. Find the merchant's connected account → click → "View account"
3. Navigate to Payments → search by `pi_*` → select the payment
4. Click "Refund" → choose amount (full or partial) → reason
5. Confirm

Stripe webhook (charge.refunded) will arrive within minutes and update
our `orders` collection automatically. If it does NOT arrive, see
procedure [4. Replay missed Stripe webhook](#4-replay-stripe-webhook).

### Step 3 — Verify in our DB

```javascript
db.orders.findOne(
  { id: "ORDER_ID" },
  { status: 1, refunded_at: 1, refund_amount_cents: 1 }
);
// Expect: status="refunded" or refund_amount_cents > 0
```

### Step 4 — Customer-facing communication

The Stripe Connect Express auto-emails the customer about the refund.
Optional: send a short follow-up via Brevo confirming.

**Audit**: Stripe records the operator (you, in dashboard); our audit_log
records the webhook landing. No additional manual log needed.

---

## 4. Replay Stripe webhook

**When**: a Stripe event was sent but our backend did not process it
(server down, webhook signature error, transient 5xx). Symptoms:
order stuck in `pending`, refund not reflected, subscription state
out of sync.

### Step 1 — Find the failed event in Stripe

1. https://dashboard.stripe.com/webhooks
2. Open the AFianco webhook endpoint
3. Filter by status: `Failed` (or `404`, `5xx`)
4. Find the relevant event (sort by time)

### Step 2 — Replay

In the event detail page, click **"Resend"**. Stripe re-sends to our
webhook URL with the same payload + a fresh signature.

Our handler is **idempotent** (Step 5 of `confirm_order` checks if the
order is already in target state). Resending is safe.

### Step 3 — Verify

```bash
ssh root@46.224.29.40
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    logs --since 5m backend 2>&1 | grep -E "stripe_webhook|payment_intent|charge"
```

Look for `[INFO]` line confirming the order id was processed.

If still failing → check the webhook signing secret rotation. If the
secret was rotated AFTER this event was originally sent, replay will
fail with signature error. Solution: capture the raw payload from
Stripe dashboard, manually update the order in DB.

---

## 5. Rolling restart backend

**When**: deploy a code change with minimal disruption, or backend is
showing high latency / memory pressure but is otherwise healthy.

**Downtime**: ~8 seconds (single worker, gunicorn graceful restart).
Frontend and DB unaffected.

### Step 1 — Pre-flight check

```bash
ssh root@46.224.29.40

# Container healthy?
docker ps --filter name=ms-backend --format "{{.Status}}"
# expect: "Up X (healthy)"

# Recent errors?
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    logs --since 5m backend 2>&1 | grep -iE "error|critical" | tail -5
```

### Step 2 — Capture current image ID for rollback

```bash
docker inspect ms-backend --format "{{.Image}}" > /tmp/rollback-image.txt
cat /tmp/rollback-image.txt
# example: sha256:799be3578120...
```

### Step 3 — Restart

```bash
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production \
    up -d --no-deps --force-recreate backend
```

### Step 4 — Wait for healthy

```bash
for i in $(seq 1 20); do
    STATUS=$(docker inspect --format="{{.State.Health.Status}}" ms-backend 2>/dev/null)
    echo "T+${i}*2s: ${STATUS}"
    [ "$STATUS" = "healthy" ] && break
    sleep 2
done
```

Expected: healthy within 15-20 seconds.

### Step 5 — Verify endpoints

```bash
curl -s https://afianco.app/api/health/ready
# expect: {"status":"ok","ready":true,"checks":{"mongodb":{"status":"ok"},...}}
```

### Step 6 — Rollback if needed

```bash
OLD_IMAGE=$(cat /tmp/rollback-image.txt)
docker tag $OLD_IMAGE margin-sentinel-backend:latest
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    up -d --no-deps --force-recreate backend
```

---

## 6. Partial restore (one MongoDB collection)

**When**: one collection got corrupted, accidentally truncated, or
needs to be reverted to yesterday's state without affecting the rest.

**Pre-req**: backup recovery key from 1Password (see backup-recovery.md).

### Step 1 — Download the chosen backup

```bash
DRILL=/tmp/afianco_partial_$(date +%Y%m%d_%H%M)
mkdir -p $DRILL && cd $DRILL

# Pick a timestamp from Storage Box
TIMESTAMP=20260508_030001  # adjust

scp -P 23 \
    u578174@u578174.your-storagebox.de:afianco-backups/db_${TIMESTAMP}.gz.age \
    db.gz.age
```

### Step 2 — Decrypt + restore the single collection

```bash
# Save the private key locally (see docs/operations/backup-recovery.md)
vim age_priv.txt   # paste from 1Password
chmod 600 age_priv.txt

# Decrypt
age -d -i age_priv.txt -o db.gz db.gz.age
rm db.gz.age

# Restore ONLY the target collection. mongorestore --nsInclude lets us
# scope down to one namespace. Use --drop to replace the entire
# collection content (DESTRUCTIVE), OR omit --drop and use
# --maintainInsertionOrder to merge.
COLLECTION="orders"  # the one to restore

# Copy the gzip onto the running mongo container
docker cp db.gz ms-mongodb:/tmp/db.gz

# Run restore inside the container
docker exec -i ms-mongodb mongorestore \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
    --archive=/tmp/db.gz --gzip \
    --nsInclude="${DB_NAME}.${COLLECTION}" \
    --drop

# Cleanup
docker exec ms-mongodb rm /tmp/db.gz
```

### Step 3 — Verify

```javascript
// In mongosh
db.<COLLECTION>.countDocuments();
// Compare with the count you saved BEFORE the corruption (if available)
// or with yesterday's nightly metric if you log them
```

### Step 4 — Cleanup

```bash
shred -u $DRILL/age_priv.txt 2>/dev/null || rm -P $DRILL/age_priv.txt
rm -rf $DRILL
```

---

## 7. Debug a stuck order

**When**: a customer reports their order is in `pending` / not paid /
not received tickets, and the backend logs do not surface an obvious
error.

### Step 1 — Reproduce the order context

```javascript
// In mongosh
const order = db.orders.findOne({ id: "ORDER_ID" });
print(JSON.stringify(order, null, 2));

// What did the customer see?
const customer = db.customer_accounts.findOne({ id: order.customer_account_id });
print("customer email:", customer?.email);
```

### Step 2 — Check Stripe state

In `dashboard.stripe.com` → search `pi_*` from `order.stripe_payment_intent_id`:
- Status: `succeeded` / `requires_action` / `requires_payment_method` / `canceled`
- Last activity timestamp

### Step 3 — Check audit log

```javascript
db.audit_logs.find(
  { target_id: "ORDER_ID" },
  { action: 1, actor_user_id: 1, created_at: 1, metadata: 1 }
).sort({ created_at: -1 }).limit(20);
```

Look for the last action and its outcome.

### Step 4 — Check backend logs by request ID (if customer provided it)

If the customer's browser shows an `X-Request-ID` header from the failure:

```bash
ssh root@46.224.29.40
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    logs backend 2>&1 | grep "req_<ID>"
```

(JSON format makes this trivially greppable now.)

### Step 5 — Check Sentry

https://afianco.sentry.io/issues/?project=4511353656115200 → search
the customer email or order id. Often the answer is here in the form
of a captured exception with stack trace.

### Step 6 — Resolution paths

| Symptom | Action |
|---|---|
| Stripe `succeeded` but order `pending` | Replay webhook (procedure 4) |
| Stripe `requires_action` | Email customer with re-checkout link |
| Stripe `canceled` | Mark order canceled in DB, refund any partial |
| Stripe shows nothing | Cart never reached payment — close order with status `abandoned` |
| Backend exception in Sentry | Fix code → emergency hotfix (procedure 10) |

---

## 8. Throttle abusive IP

**When**: an IP is hammering the API (DDoS, scraper, brute force).
slowapi handles per-IP rate limits at the application level, but
sometimes you want a hard nginx-level cut-off.

### Step 1 — Identify the IP

```bash
ssh root@46.224.29.40
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    logs --since 30m nginx-proxy 2>&1 \
    | grep -oE '^ms-nginx \\| [0-9.]+ ' \
    | sort | uniq -c | sort -rn | head -10
```

Top IPs by hit count.

### Step 2 — Block via iptables (immediate, server-level)

```bash
ABUSER_IP="1.2.3.4"
iptables -I INPUT -s ${ABUSER_IP} -j DROP

# Verify
iptables -L INPUT -n | grep ${ABUSER_IP}
```

Effect is immediate. The IP cannot reach our nginx anymore.

### Step 3 — Make it persistent (survive reboot)

```bash
# Save current rules to file (survives reboot if iptables-persistent is installed)
apt-get install -y iptables-persistent  # one-time
netfilter-persistent save
```

### Step 4 — Unblock when done

```bash
iptables -D INPUT -s ${ABUSER_IP} -j DROP
netfilter-persistent save
```

### Step 5 — Long-term mitigation

If the same pattern repeats, add to nginx:

```nginx
# In deploy/nginx/nginx.conf, top of http block (need new file for that)
geo $abuser {
    default 0;
    1.2.3.0/24 1;
    5.6.7.0/24 1;
}
```

Then in server block:

```nginx
if ($abuser) { return 444; }
```

Reload: `docker exec ms-nginx nginx -s reload`.

---

## 9. Update Python dependency

**When**: Dependabot opens a PR for a CVE patch (or you want to bump a
dep manually).

### Step 1 — Local test

```bash
cd /Users/davidedefilippis/Desktop/BI_PMI/backend
# Activate venv
source venv/bin/activate

# Check current version
pip show <package>

# Bump
pip install --upgrade <package>

# Re-run the relevant unit tests
python -m pytest tests/ -k <related-keyword>
```

### Step 2 — Update requirements files

Edit `backend/requirements.prod.txt` AND `backend/requirements.txt` —
the prod one is what the Docker build uses. Keep them in sync.

### Step 3 — Build and verify locally

```bash
docker build -t backend-test backend/
docker run --rm backend-test python -c "import <package>; print(<package>.__version__)"
```

### Step 4 — Deploy to prod

Follow procedure 5 (Rolling restart backend) but FIRST:

```bash
# rsync requirements files only
rsync -avz backend/requirements.prod.txt root@46.224.29.40:/opt/margin-sentinel/backend/

# On the server: rebuild
ssh root@46.224.29.40
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production build backend

# Then proceed with the rolling restart from procedure 5
```

### Step 5 — Verify

After restart:

```bash
docker exec ms-backend pip show <package>
curl -s https://afianco.app/api/health/ready
```

If anything regresses → procedure 5 step 6 (rollback to old image).

### Step 6 — Commit

```bash
cd /Users/davidedefilippis/Desktop/BI_PMI
git add backend/requirements*.txt
git commit -m "deps(backend): bump <package> to <version> (CVE-XXXX or feature)"
git push
```

---

## 10. Emergency hotfix deploy

**When**: a production-breaking bug is discovered (data loss, payment
failure, login broken) and you need to deploy a fix in <30 minutes,
bypassing usual review steps.

### Pre-flight (5 min)

1. **Confirm the bug** is real (reproduce locally first if possible).
2. **Take a manual MongoDB snapshot** before any fix:

   ```bash
   ssh root@46.224.29.40
   docker exec ms-mongodb mongodump \
       --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
       --archive=/tmp/manual-pre-hotfix-$(date +%Y%m%d_%H%M).gz --gzip
   ```

   (Stays on the VPS, NOT uploaded — it's a quick rollback safety net.)

3. **Capture current image ID** (procedure 5 step 2).

### Step 1 — Build the patch locally

```bash
cd /Users/davidedefilippis/Desktop/BI_PMI
# Make the minimal change
vim <file>
```

Run a smoke test (`pytest tests/<relevant>`).

### Step 2 — rsync directly to prod (bypass git for now)

```bash
rsync -avz backend/path/to/file.py root@46.224.29.40:/opt/margin-sentinel/backend/path/to/file.py
```

### Step 3 — Rebuild + restart backend

```bash
ssh root@46.224.29.40
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production build backend
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate backend
```

### Step 4 — Verify

```bash
sleep 10
curl -s https://afianco.app/api/health/ready  # MUST return ok
```

Then **immediately** test the bug: trigger the failure path and confirm
it now succeeds.

### Step 5 — If verification fails

Rollback (procedure 5 step 6) AND restore from manual snapshot if data
got corrupted:

```bash
docker exec -i ms-mongodb mongorestore \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
    --archive=/tmp/manual-pre-hotfix-<TS>.gz --gzip --drop
```

### Step 6 — Commit + push the fix (post-deploy)

After the hotfix is verified live:

```bash
cd /Users/davidedefilippis/Desktop/BI_PMI
git add <file>
git commit -m "Hotfix: <short description>

Deployed via rsync to prod at <UTC time> ahead of git push because of
<reason>. Verified by <verification steps>. Manual snapshot taken at
/tmp/manual-pre-hotfix-<TS>.gz on the VPS.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin main
```

### Step 7 — Cleanup

After 24 hours of stability:

```bash
ssh root@46.224.29.40
rm /tmp/manual-pre-hotfix-*.gz
```

### Post-mortem

For every emergency hotfix, schedule a 30-min post-mortem within 48
hours: what happened, why, how we caught it, what could have prevented
it (better tests? Sentry alert? CSP violation report?). Append a 2-line
summary to `docs/operations/incidents.md` (create if absent).

---

## Appendix — quick reference

```bash
# Status of everything
ssh root@46.224.29.40 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Backend logs last 30 minutes (JSON-greppable)
docker compose -f /opt/margin-sentinel/docker-compose.prod.yml \
    --env-file /opt/margin-sentinel/.env.production \
    logs --since 30m backend 2>&1 | jq -r 'select(.level=="ERROR")'

# MongoDB shell, default DB
docker exec -it ms-mongodb mongosh \
    --username "$MONGO_ROOT_USER" --password "$MONGO_ROOT_PASSWORD" \
    --authenticationDatabase admin margin_sentinel

# nginx config test + reload
docker exec ms-nginx nginx -t
docker exec ms-nginx nginx -s reload

# Healthcheck
curl -s https://afianco.app/api/health/ready | jq .

# Sentry
open https://afianco.sentry.io/issues/

# Storage Box browse
sftp -P 23 u578174@u578174.your-storagebox.de
> ls afianco-backups/
```

---

## Maintenance

This runbook is alive. After each real incident:
- If the procedure helped: refine wording.
- If a step was missing: add it.
- If a procedure became obsolete: archive (don't delete) at the bottom.

Suggested review cadence: every 3 months OR after any procedure was
actually invoked.
