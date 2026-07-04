# Data Retention Policy

Active retention policies for AFianco data stores. Each entry documents
**what** is retained, **for how long**, **why** that duration was chosen,
and **how** the deletion is enforced.

This document is the authoritative reference for GDPR Art. 5(1)(e)
("storage limitation") compliance.

---

## audit_logs collection

| Aspect | Value |
|---|---|
| **Retention period** | 365 days (1 year) |
| **Enforcement** | MongoDB TTL index `audit_logs_ttl` on field `expire_at` |
| **Triggered by** | Phase 1 Step D3 (deployed YYYY-MM-DD) |
| **Index definition** | `db.audit_logs.createIndex({"expire_at": 1}, {expireAfterSeconds: 31536000, name: "audit_logs_ttl"})` |

### What is retained

Operator actions captured by `repositories.audit_repository` and direct
inserts in `routers.admin` (account unlocks, refunds, policy overrides).

Each document carries:
- `actor_user_id`, `actor_role`, `organization_id`
- `action` (e.g. `USER_UNLOCKED`, `CUSTOMER_ACCOUNT_UNLOCKED`)
- `target_type`, `target_id`
- `metadata` (action-specific fields)
- `created_at` (ISO string, human-readable)
- `expire_at` (BSON Date, drives the TTL — added in D3)

### Why 365 days

- **Operational debugging**: covers a full annual cycle (yearly reports,
  recurring incidents).
- **GDPR alignment**: 1 year is at the lower end of "reasonable" retention
  for operational logs (vs 2-3 years for financial records).
- **DB hygiene**: at current write rate, indefinite retention would push
  the collection past 100k docs/year and slow the `(organization_id, created_at)`
  index used by the admin audit view.

### Migration notes

- Documents inserted **before** D3 deploy lack the `expire_at` field. MongoDB
  TTL silently ignores them — they will not be deleted automatically.
- A backfill is intentionally NOT scheduled: the population of pre-D3 audit
  logs is small (<10k docs as of writing) and they remain queryable via the
  legacy `created_at` index.
- If you need to apply retention retroactively, run `scripts/backfill_audit_expire_at.py`
  (see SCRIPTS section below; document if added).

### Verification

```javascript
// In mongosh:
use margin_sentinel;
db.audit_logs.getIndexes();
// Expect to see "audit_logs_ttl" with expireAfterSeconds: 31536000

// Check how many docs already have expire_at (post-D3):
db.audit_logs.countDocuments({ expire_at: { $exists: true } });

// Pre-D3 documents (no auto-delete):
db.audit_logs.countDocuments({ expire_at: { $exists: false } });
```

### Override / extension

To extend retention to 2 years for compliance reasons:

```javascript
db.audit_logs.dropIndex("audit_logs_ttl");
db.audit_logs.createIndex(
  { expire_at: 1 },
  { expireAfterSeconds: 63072000, name: "audit_logs_ttl" }
);
```

Update this document with the new value and the rationale.

---

## Other collections (current state — not actively pruned)

The following collections currently grow unboundedly. Each is flagged for
future retention review:

| Collection | Current size | Action item |
|---|---|---|
| `chat_sessions` | small | Review at 100k docs (likely Phase 3) |
| `insights` | small | Review at 100k docs |
| `email_logs` (if present) | unbounded | Schedule TTL after Brevo webhook (B2) |
| `sales_records`, `expense_records`, `purchase_records` | grows with usage | NEVER prune — these are merchant business data |
| `orders`, `issued_*` | grows with usage | NEVER prune — accounting / GDPR right-to-know |
| `users`, `customer_accounts`, `organizations` | bounded | NEVER prune — handled by GDPR delete-account flow |

---

## GDPR Right-to-Erasure (separate from retention)

Retention is automatic deletion based on age. The user-facing right to be
forgotten ("delete my account") is implemented separately in:
- `routers.customer_portal` — customer self-service delete
- `services.gdpr_service` (if applicable) — admin-initiated delete

When a user requests deletion, all their PII (email, name, addresses, payment
methods) is removed, but **audit_logs are PII-light by design**: they store
`user_id` (opaque ID), not email or name. So expiring the user doc but keeping
audit logs for the remaining TTL window is GDPR-compliant.

If a regulator requires immediate audit_log deletion for a specific user,
manually run:

```javascript
db.audit_logs.deleteMany({ actor_user_id: "<user_id>" });
db.audit_logs.deleteMany({ "metadata.user_email": "<email>" });
```

---

## chat_sessions collection (Wave GDPR-Admin A audit)

| Aspect | Value |
|---|---|
| **Retention period** | 7 days (default — Free plan); configurable per commercial plan |
| **Enforcement** | MongoDB TTL index `expires_at_1` on field `expires_at` (per-document expiry) |
| **Per-document expiry** | `services.chat_service._compute_expires_at(org_id)` — resolved from `commercial_plans.<slug>.platform_limits.chat_session_ttl_days` (catalog) → `_PLAN_TTL_DAYS_FALLBACK` (legacy) → 7 days (default) |
| **Index definition** | `db.chat_sessions.createIndex({"expires_at": 1}, {expireAfterSeconds: 0, name: "expires_at_1"})` — TTL=0 means "expire when expires_at is reached" |

### Why 7 days

- **GDPR Art. 5(1)(c) data minimisation**: chat history is conversational context, not authoritative business data — it does not need to persist.
- **Business records remain**: financial transactions (sales, expenses, purchases) are stored in their own collections with their own retention.
- **Plan differentiation**: higher commercial plans can extend retention via `platform_limits.chat_session_ttl_days`.

### Verification

```javascript
db.chat_sessions.countDocuments({}) ==
  db.chat_sessions.countDocuments({expires_at: {$exists: true, $ne: null}})
```

---

## Deactivated organizations — Hard Delete after 30-day grace (Wave GDPR-Admin A audit)

| Aspect | Value |
|---|---|
| **Grace period** | 30 days from `organization.deactivated_at` |
| **Warning email** | Sent **7 days before deletion** (~23 days after deactivation) — Wave GDPR-Admin A |
| **Enforcement** | `services.background_service._hard_delete_cleanup_job` runs every 6 hours, deletes orgs past the grace cutoff via `services.hard_delete_service.cascade_hard_delete` |
| **Cascade scope** | 22 org-scoped collections + users + audit_logs (anonymised) + organization (last) |
| **Idempotency** | `delete_many` on already-deleted records is a no-op |

### Warning email pipeline (Wave GDPR-Admin A)

1. `_hard_delete_warning_job` runs every 12 hours (staggered after the cleanup job).
2. Selects orgs where `deactivated_at` is between (now − 30d) and (now − 23d) AND `hard_delete_warning_sent_at` IS NULL.
3. For each org, fetches all members (locale per user, fallback `it`).
4. Sends `send_final_delete_warning(email, org_name, days_ago, delete_date_str, locale)`.
5. Marks `organization.hard_delete_warning_sent_at = now` after the batch. Idempotent across job runs.
6. The actual cascade fires 7 days later via the cleanup job — the warning never blocks the deletion path (legal commitment).

### Why 30-day grace + 7-day warning

- **GDPR Art. 17**: right to erasure must be honoured; 30 days is a reasonable buffer.
- **Operational safety**: brief grace lets ops staff revert mistaken cancellations.
- **User notice**: 7-day warning gives the user time to export their data or reactivate.

### Verification

```javascript
// Orgs in the warning window (next tick should email them)
db.organizations.find({
  deactivated_at: { $ne: null,
    $lt: new Date(Date.now() - 23 * 86400 * 1000),
    $gte: new Date(Date.now() - 30 * 86400 * 1000) },
  $or: [{ hard_delete_warning_sent_at: { $exists: false } }, { hard_delete_warning_sent_at: null }],
})

// Orgs past hard-delete cutoff (cleanup job processes within 6h)
db.organizations.find({
  deactivated_at: { $ne: null, $lt: new Date(Date.now() - 30 * 86400 * 1000) },
})
```

---

## Change log

| Date | Change | Phase / Step |
|---|---|---|
| 2026-05-08 | Initial policy: audit_logs TTL 365 days via expire_at field | Phase 1 Step D3 |
| 2026-05-16 | Document chat_sessions per-doc TTL (already implemented since Onda 10) | Wave GDPR-Admin A (audit) |
| 2026-05-16 | Document org hard-delete cascade (in prod since v6.0) | Wave GDPR-Admin A (audit) |
| 2026-05-16 | NEW: 7-day warning email before hard-delete (`_hard_delete_warning_job`) | Wave GDPR-Admin A |
