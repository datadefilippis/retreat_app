# Backup & Recovery — AFianco

How to restore from the encrypted backups stored on Hetzner Storage Box.

Backup pipeline (Phase 1, Steps C1-C5):
- Source: VPS `46.224.29.40` (Hetzner Cloud Falkenstein)
- Destination: Hetzner Storage Box `u578174@u578174.your-storagebox.de:afianco-backups/`
- Schedule: cron daily at 03:00 UTC
- Encryption: `age` with public key in `deploy/age_pubkey.txt`; private key OFFLINE (1Password + USB)
- Retention: 30 days, auto-cleaned via SFTP from the script (Step C2)
- Failure alert: email to `BACKUP_ALERT_EMAIL` via Brevo (Step C3)

---

## File naming on Storage Box

| Filename | Contents | Required for restore |
|---|---|---|
| `db_<YYYYMMDD>_<HHMMSS>.gz.age` | MongoDB full dump (mongodump --archive --gzip), encrypted | DB restore |
| `uploads_<YYYYMMDD>_<HHMMSS>.tar.gz.age` | `/app/uploads` Docker volume (product images, logos), encrypted | Visual asset restore |
| `config_<YYYYMMDD>_<HHMMSS>.tar.gz.age` | `.env.production`, `docker-compose.prod.yml`, `deploy/nginx/`, `letsencrypt/` (snapshot of Docker volume `ms-certbot-conf`), root crontab — encrypted | Disaster recovery (rebuild stack on fresh VPS) |

All files end in `.age` → encrypted with the AFianco backup key. The plain
intermediate files exist only briefly on the VPS during the backup run and
are deleted as soon as encryption completes.

---

## Prerequisites for any restore operation

1. **Private key**: retrieve from 1Password vault → "AFianco / Production / age backup encryption key"
   - The key is the `AGE-SECRET-KEY-1...` line (3rd line of the original key file).
   - Save to a file: `~/Desktop/age_priv.txt` with `chmod 600`.
2. **age binary**: `brew install age` (macOS) or `apt install age` (Debian/Ubuntu).
3. **SSH access to Storage Box**: SSH key for `u578174@u578174.your-storagebox.de` on port 23.

When you finish a restore session, **delete the local copy of the private
key** — it should never linger on a working filesystem.

---

## Recipe 1 — Restore MongoDB

### When to use
- Catastrophic data loss (corruption, accidental drop, ransomware).
- Cloning prod state to staging for a restore drill (Step C4).

### Steps

```bash
# 1. List available DB backups on Storage Box (newest first)
sftp -P 23 u578174@u578174.your-storagebox.de <<EOF
cd afianco-backups
ls -1
bye
EOF

# 2. Download the chosen DB backup
scp -P 23 \
    u578174@u578174.your-storagebox.de:afianco-backups/db_<TIMESTAMP>.gz.age \
    /tmp/db_to_restore.gz.age

# 3. Decrypt
age -d -i ~/Desktop/age_priv.txt -o /tmp/db_to_restore.gz /tmp/db_to_restore.gz.age
rm /tmp/db_to_restore.gz.age

# 4a. Restore IN PLACE on the production server (DESTRUCTIVE — drops existing data)
docker exec -i ms-mongodb mongorestore \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
    --archive --gzip --drop \
    < /tmp/db_to_restore.gz

# 4b. OR restore to a temp database for inspection (safe)
docker exec -i ms-mongodb mongorestore \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}_restore?authSource=admin" \
    --archive --gzip \
    < /tmp/db_to_restore.gz

# 5. Cleanup
rm /tmp/db_to_restore.gz ~/Desktop/age_priv.txt
```

### Verification after restore

```bash
docker exec ms-mongodb mongosh \
    --username "${MONGO_ROOT_USER}" --password "${MONGO_ROOT_PASSWORD}" \
    --authenticationDatabase admin \
    --eval 'db.getSiblingDB("'${DB_NAME}'").getCollectionNames().forEach(c => print(c, db.getCollection(c).countDocuments()))'
```

---

## Recipe 2 — Restore uploads volume

```bash
# 1. Download
scp -P 23 \
    u578174@u578174.your-storagebox.de:afianco-backups/uploads_<TIMESTAMP>.tar.gz.age \
    /tmp/uploads.tar.gz.age

# 2. Decrypt
age -d -i ~/Desktop/age_priv.txt -o /tmp/uploads.tar.gz /tmp/uploads.tar.gz.age
rm /tmp/uploads.tar.gz.age

# 3. Extract into the live volume (DESTRUCTIVE)
UPLOADS_VOLUME=$(docker volume inspect ms-backend-uploads --format '{{.Mountpoint}}')
tar -xzf /tmp/uploads.tar.gz -C "${UPLOADS_VOLUME}"

# 4. Cleanup
rm /tmp/uploads.tar.gz
```

The backend container does not need a restart — files are read on demand.

---

## Recipe 3 — Disaster recovery: rebuild stack on a fresh VPS

When the entire VPS is gone (Hetzner outage, account compromise, total
filesystem corruption). Goal: restore service in <4 hours.

### Pre-requisites
- A new clean Ubuntu VPS provisioned.
- DNS still pointing to the old IP — update DNS to the new IP at the end
  (or use Hetzner Floating IP if pre-arranged).
- Docker + Docker Compose installed on the new VPS.

### Steps

```bash
# On a workstation with the private key:

# 1. Download all 3 archives for the chosen restore point
TIMESTAMP=20260508_030001
mkdir /tmp/afianco_restore && cd /tmp/afianco_restore
for arch in db_${TIMESTAMP}.gz.age uploads_${TIMESTAMP}.tar.gz.age config_${TIMESTAMP}.tar.gz.age; do
    scp -P 23 u578174@u578174.your-storagebox.de:afianco-backups/${arch} ./
done

# 2. Decrypt all
for f in *.age; do
    age -d -i ~/Desktop/age_priv.txt -o "${f%.age}" "${f}"
    rm "${f}"
done

# 3. Extract config archive
tar -xzf config_${TIMESTAMP}.tar.gz -C /tmp/afianco_restore/

# 4. SCP everything to the new VPS
NEW_VPS=root@<new-server-ip>
ssh ${NEW_VPS} "mkdir -p /opt/margin-sentinel"
scp -r /tmp/afianco_restore/opt/margin-sentinel/* ${NEW_VPS}:/opt/margin-sentinel/
# letsencrypt/ is a snapshot of the Docker volume ms-certbot-conf. We
# stage it under /tmp on the new VPS and populate the Docker volume
# directly (Step 5 below) — host /etc/letsencrypt is not used.
scp -r /tmp/afianco_restore/letsencrypt ${NEW_VPS}:/tmp/letsencrypt-snapshot
scp /tmp/afianco_restore/var/spool/cron/crontabs/root ${NEW_VPS}:/var/spool/cron/crontabs/root
scp /tmp/afianco_restore/db_${TIMESTAMP}.gz ${NEW_VPS}:/tmp/db.gz
scp /tmp/afianco_restore/uploads_${TIMESTAMP}.tar.gz ${NEW_VPS}:/tmp/uploads.tar.gz

# 5. On the new VPS: bring up MongoDB and restore
ssh ${NEW_VPS}
cd /opt/margin-sentinel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d mongodb
sleep 10

docker exec -i ms-mongodb mongorestore \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
    --archive --gzip < /tmp/db.gz

docker volume create ms-backend-uploads
UPLOADS_VOLUME=$(docker volume inspect ms-backend-uploads --format '{{.Mountpoint}}')
tar -xzf /tmp/uploads.tar.gz -C "${UPLOADS_VOLUME}"

# Populate the certbot volume (TLS certs) from the staged snapshot.
# The volume is created on `docker compose up` below if missing, but
# populating it BEFORE bringing up nginx ensures the proxy comes up
# already serving the live certs (no transient HTTPS outage).
docker volume create ms-certbot-conf
docker run --rm \
    -v ms-certbot-conf:/dest \
    -v /tmp/letsencrypt-snapshot:/source:ro \
    alpine sh -c 'cp -a /source/. /dest/'
rm -rf /tmp/letsencrypt-snapshot

# Full stack up
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 6. DNS swap: point afianco.app A record to the new IP

# 7. Verify
curl -I https://afianco.app/api/health/ready
# expect: 200 OK with mongodb: ok

# 8. Cleanup
rm /tmp/db.gz /tmp/uploads.tar.gz
```

### Recovery time budget
| Step | Time |
|---|---|
| Provision new VPS | 5-10 min |
| Download + decrypt 3 archives | 5 min (~3 MB total today) |
| SCP transfer to new VPS | 5 min |
| `docker compose up` (build) | 5-10 min |
| MongoDB restore (~1.5 MB current) | <1 min |
| DNS propagation (TTL-dependent) | 5 min – 24h |
| **Total (excl. DNS)** | **~30 min** |

Keep DNS TTL low (300s) on the A record to minimize swap time.

---

## Key rotation procedure

If the private key may have been compromised (laptop stolen, USB lost,
1Password account breached), rotate immediately:

```bash
# 1. Generate new keypair on a clean machine
age-keygen -o /tmp/new_age_key.txt

# 2. Save new PRIVATE key to 1Password + USB (replacing old)

# 3. Update the public key file in the repo + on the VPS
new_pubkey=$(grep "^# public key:" /tmp/new_age_key.txt | sed 's/^# public key: //')
# Edit deploy/age_pubkey.txt — replace old pubkey with new_pubkey

# 4. rsync to server, no restart needed (next backup uses new pubkey)
rsync deploy/age_pubkey.txt root@<vps>:/opt/margin-sentinel/deploy/age_pubkey.txt

# 5. The OLD private key still decrypts old backups. Keep it offline until
#    retention expires (30 days), then destroy it.
shred -u /tmp/new_age_key.txt
```

Do NOT re-encrypt old backups with the new key — they expire in 30 days
anyway, and re-encryption costs Storage Box bandwidth + risks key handling
errors.

---

## Quick reference

```bash
# Decrypt a single archive
age -d -i ~/Desktop/age_priv.txt -o output.gz input.gz.age

# List available backups via SFTP
sftp -P 23 u578174@u578174.your-storagebox.de <<< "ls afianco-backups/"

# Find the most recent timestamp
sftp -P 23 u578174@u578174.your-storagebox.de <<< "ls afianco-backups/" | grep "^db_" | sort -r | head -1
```

---

## Restore drill (Phase 1 Step C4)

Schedule monthly. The first one will be performed during C4 setup.
See `docs/operations/restore-drill.md` (created in Step C4).
