# Restore Drill — AFianco

Monthly procedure to **prove** the backup is actually restorable.
Untested backup = no backup. This document is the authoritative runbook
for the drill.

Setup: Phase 1 Step C4 (defined YYYY-MM-DD).
Schedule: first **Monday of every month**, calendar reminder.

---

## Why monthly

The risk we are insuring against is silent backup degradation:
- Mongo schema migrations that break older dump compatibility
- age key rotation desync
- Storage Box quota exhaustion (uploads succeed, downloads fail)
- SSH key rotations on Storage Box that break automated downloads
- Container image drift on the VPS (mongorestore version vs dump version)

Catching these requires periodically going through the FULL pipeline,
not just `ls` on the Storage Box.

---

## Prerequisites (one-time setup, before first drill)

1. **Local Docker Desktop** running (target = a Mac for isolation).
2. **age binary** installed locally (`brew install age`).
3. **Private age key** retrievable (1Password vault → "AFianco / Production").
4. **SSH key** for the Storage Box configured locally:
   - Public key copied to `u578174@u578174.your-storagebox.de` via `ssh-copy-id -p 23 …`
5. **Disk space**: ~500 MB free in `/tmp` (DB ~1.5 MB + uploads ~1 MB + Docker volume + working space).

The drill DOES NOT touch production. Everything happens in an isolated
local Docker container with a throwaway database name (`afianco_drill`).

---

## Drill procedure (single run)

Allocate **~30-60 minutes** uninterrupted. Take notes inline; the result
goes into `restore-drill-history.md`.

### Step 1 — Pick a backup to restore

```bash
# List remote backups, sorted newest-first, group by date
ssh -p 23 u578174@u578174.your-storagebox.de "ls -1 afianco-backups/" \
    | grep -E "^(db_|uploads_|config_)" | sort -r | head -20
```

Pick a TIMESTAMP from yesterday (or any from the last 7 days). Record the
chosen timestamp in your notes:

```
TIMESTAMP: 20260508_030001
```

### Step 2 — Download the 3 archives

```bash
DRILL_DIR="$HOME/afianco_drill_$(date +%Y%m%d_%H%M)"
mkdir -p "${DRILL_DIR}" && cd "${DRILL_DIR}"
TIMESTAMP=20260508_030001  # adjust to your chosen timestamp

for arch in db_${TIMESTAMP}.gz.age uploads_${TIMESTAMP}.tar.gz.age config_${TIMESTAMP}.tar.gz.age; do
    scp -P 23 u578174@u578174.your-storagebox.de:afianco-backups/${arch} ./
done

ls -lah
# Expect 3 .age files
```

**Note in history**: download time, sizes.

### Step 3 — Retrieve private key (TEMPORARY)

Open 1Password → "AFianco / Production / age backup encryption key" →
copy the full content (3 lines) into:

```bash
vim "${DRILL_DIR}/age_priv.txt"
chmod 600 "${DRILL_DIR}/age_priv.txt"
```

⚠️ This file lives ONLY for the duration of the drill. Step 9 deletes it.

### Step 4 — Decrypt all archives

```bash
cd "${DRILL_DIR}"
for f in *.age; do
    age -d -i age_priv.txt -o "${f%.age}" "${f}"
    rm "${f}"
done
ls -lah
# Expect: age_priv.txt + 3 plain archives (db_*.gz, uploads_*.tar.gz, config_*.tar.gz)
```

If decryption fails, **STOP** — the drill has already caught a real issue.

### Step 5 — Spin up isolated Mongo container

```bash
docker run -d --rm \
    --name afianco-drill-mongo \
    -p 37017:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=drill \
    -e MONGO_INITDB_ROOT_PASSWORD=drill_password_throwaway \
    mongo:7.0

# Wait until the container is healthy
until docker exec afianco-drill-mongo mongosh --quiet \
    --username drill --password drill_password_throwaway --authenticationDatabase admin \
    --eval "db.adminCommand('ping').ok" >/dev/null 2>&1; do
    sleep 2
done
echo "Drill mongo ready."
```

### Step 6 — Restore the DB into the drill container

```bash
docker exec -i afianco-drill-mongo mongorestore \
    --uri="mongodb://drill:drill_password_throwaway@localhost:27017/afianco_drill?authSource=admin" \
    --archive --gzip \
    < "${DRILL_DIR}/db_${TIMESTAMP}.gz"
```

Expect ~30 seconds for current DB size (~1.5 MB compressed). Watch for
warnings — index conflicts on `access_token_1` are pre-existing (Onda 16+
schema drift) and NOT a drill failure.

### Step 7 — Verify integrity

```bash
docker exec afianco-drill-mongo mongosh --quiet \
    --username drill --password drill_password_throwaway --authenticationDatabase admin \
    afianco_drill --eval '
const collections = db.getCollectionNames().sort();
print("Collection count:", collections.length);
collections.forEach(c => {
    const n = db.getCollection(c).countDocuments();
    print("  " + c.padEnd(40), n);
});
'
```

**Compare counts with prod** (manually, eyeball):

```bash
# On production VPS:
ssh root@46.224.29.40 'docker exec ms-mongodb mongosh --quiet \
    -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
    "$DB_NAME" --eval "db.getCollectionNames().sort().forEach(c => print(c.padEnd(40), db.getCollection(c).countDocuments()))"'
```

**Pass criterion**: collections match (same set), counts within ±5%
(small drift expected because the backup is from yesterday, prod has new
events since).

### Step 8 — Verify uploads + config

```bash
# Uploads — peek inside the tarball without extracting
tar -tzf "${DRILL_DIR}/uploads_${TIMESTAMP}.tar.gz" | head -20
tar -tzf "${DRILL_DIR}/uploads_${TIMESTAMP}.tar.gz" | wc -l
echo "(should match prod /app/uploads file count)"

# Config — verify critical paths are present
tar -tzf "${DRILL_DIR}/config_${TIMESTAMP}.tar.gz" | sort | head -20
# Expect:
#   opt/margin-sentinel/.env.production
#   opt/margin-sentinel/docker-compose.prod.yml
#   opt/margin-sentinel/deploy/nginx/...
#   etc/letsencrypt/...
#   var/spool/cron/crontabs/root
```

### Step 9 — Cleanup (mandatory)

```bash
# Stop drill mongo container
docker stop afianco-drill-mongo

# Delete the local private key file
shred -u "${DRILL_DIR}/age_priv.txt" 2>/dev/null || rm -P "${DRILL_DIR}/age_priv.txt" 2>/dev/null || rm "${DRILL_DIR}/age_priv.txt"

# Verify gone
ls -la "${DRILL_DIR}/age_priv.txt" 2>&1 | grep -q "No such" && echo "✓ age_priv.txt deleted"

# (Optional) wipe the entire drill directory
rm -rf "${DRILL_DIR}"
```

### Step 10 — Record the drill result

Append a line to `restore-drill-history.md`:

```markdown
| 2026-05-08 | 20260508_030001 | OK / FAIL | <duration> | <notes> |
```

If FAIL: open a follow-up task with the failure type (decryption, mongo
restore mismatch, missing config path, …) and address before the next
scheduled drill.

---

## Pass / Fail criteria

A drill passes if **ALL** of these are true:

| # | Check | Pass condition |
|---|---|---|
| 1 | All 3 archives downloaded | sizes > 0, no SCP error |
| 2 | All 3 archives decrypted | age exits 0, plain files exist |
| 3 | Mongo container starts | `mongosh` ping returns ok |
| 4 | mongorestore exits 0 | (warnings OK, errors FAIL) |
| 5 | Collection count match | same set as prod, counts ±5% |
| 6 | Uploads tarball lists files | `tar -t` shows expected entries |
| 7 | Config tarball complete | `.env.production`, nginx, letsencrypt all present |
| 8 | Cleanup completed | private key file gone, drill mongo stopped |

ANY failure → drill FAIL → investigate before next monthly cycle.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `age: failed to decrypt: no identity matched any of the recipients` | Wrong private key, or key was rotated | Verify 1Password matches `deploy/age_pubkey.txt` |
| `mongorestore: ... error connecting to host` | Drill mongo not ready, port conflict | Wait longer, check `docker ps` for port 37017 |
| `mongorestore: index already exists` | Pre-existing schema drift (Onda 16+) | Warning only, does NOT fail the drill |
| `tar: ... cannot open: No such file` on extraction | Backup was made when path was missing | Fix at source (next backup will be clean) |
| Counts wildly different | Migration / wipe between backup and prod | Confirm with deploy log |

---

## Calendar reminder

Set a recurring reminder:
- **Frequency**: monthly, first Monday
- **Notification**: 1 hour before
- **Estimated effort**: 30-60 minutes
- **Tool**: Apple Calendar / Google Calendar / your password manager (1Password has reminders)

After the drill, fill `restore-drill-history.md` immediately to keep the
audit trail honest.

---

## Annual full disaster-recovery drill

Once a year, instead of the simple monthly drill, do the FULL DR drill:
- Provision a fresh VPS (Hetzner Cloud, smallest tier suffices for the drill).
- Follow Recipe 3 from `backup-recovery.md` end-to-end.
- Time it. Goal: **<4 hours** total.

This validates that not just the backups, but the operational know-how, is
intact.
