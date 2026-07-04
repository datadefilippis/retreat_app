#!/bin/bash
# ── AFianco — MongoDB + Uploads Backup to Hetzner Storage Box ──────
#
# Usage:
#   ./deploy/backup.sh
#
# Cron (daily at 03:00):
#   0 3 * * * /opt/margin-sentinel/deploy/backup.sh >> /var/log/ms-backup.log 2>&1
#
# Requires:
#   - .env.production in the project root with:
#       MONGO_ROOT_USER, MONGO_ROOT_PASSWORD, DB_NAME    (MongoDB dump)
#       BREVO_API_KEY                                   (failure alerts; optional)
#       BACKUP_ALERT_EMAIL                              (failure alerts; optional)
#       SMTP_FROM_EMAIL                                 (sender; optional)
#   - SSH key configured for Storage Box (ssh-copy-id -p 23 u578174@u578174.your-storagebox.de)
#
# What it does:
#   1. Dumps MongoDB to a compressed archive
#   2. Tars the uploads volume (product images, logos)
#   3. Uploads both to Hetzner Storage Box via scp
#   4. Cleans up local temp files
#   5. Removes backups older than RETENTION_DAYS via SFTP (Phase 1 Step C2)
#   6. On failure (any non-zero exit), emails BACKUP_ALERT_EMAIL via Brevo
#      (Phase 1 Step C3 — self-hosted, no healthchecks.io needed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="${PROJECT_DIR}/backups/tmp"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# ── Storage Box config ───────────────────────────────────────────────
STORAGE_HOST="u578174.your-storagebox.de"
STORAGE_USER="u578174"
STORAGE_PORT=23
STORAGE_DIR="afianco-backups"

# ── Encryption config (Phase 1 Step C1) ──────────────────────────────
# Each backup archive (db_, uploads_, config_) is encrypted with `age`
# before uploading to Storage Box. The PRIVATE key is held offline only
# (1Password + USB key). The Storage Box never sees plaintext.
#
# If age is missing or the public key is unreadable the script fails
# loudly: encryption is non-optional, we don't ship plaintext to Storage.
AGE_PUBKEY_FILE="${SCRIPT_DIR}/age_pubkey.txt"

# ── Failure alert (Phase 1 Step C3 — self-hosted, no healthchecks.io) ─
# When the script exits with non-zero status, send a one-shot email via
# Brevo API to BACKUP_ALERT_EMAIL. Reuses the transactional email setup
# (BREVO_API_KEY, SMTP_FROM_EMAIL) so no new account / cost is required.
# Silent no-op when either env var is empty — useful in dev / CI runs.
ALERT_SENT=0
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SCRIPT_NAME="$(basename "$0")"
HOSTNAME_TAG="$(hostname)"

send_alert_on_failure() {
    local exit_code=$?
    # Skip on success
    if [ ${exit_code} -eq 0 ]; then
        return 0
    fi
    # Avoid double-send (defensive: if both ERR and EXIT traps fire)
    if [ ${ALERT_SENT} -eq 1 ]; then
        return 0
    fi
    ALERT_SENT=1

    local end_ts
    end_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "[ERROR] $(date) — Backup FAILED (exit=${exit_code}, started ${START_TS}, ended ${end_ts})"

    # Cannot send alert if Brevo not configured — log and bail out silently.
    if [ -z "${BREVO_API_KEY:-}" ] || [ -z "${BACKUP_ALERT_EMAIL:-}" ]; then
        echo "[WARN] $(date) — Alert email NOT sent: BREVO_API_KEY or BACKUP_ALERT_EMAIL is empty"
        return 0
    fi

    local sender_email="${SMTP_FROM_EMAIL:-noreply@afianco.app}"
    local subject="[AFianco] Backup FAILED on ${HOSTNAME_TAG} (exit=${exit_code})"
    local body="<h2 style=\"color:#c00\">Backup failure on ${HOSTNAME_TAG}</h2><table style=\"font-family:sans-serif;border-collapse:collapse\"><tr><td style=\"padding:4px 12px 4px 0\"><b>Server</b></td><td>${HOSTNAME_TAG}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Script</b></td><td>${SCRIPT_NAME}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Started</b></td><td>${START_TS}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Failed at</b></td><td>${end_ts}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Exit code</b></td><td><code>${exit_code}</code></td></tr></table><p style=\"margin-top:16px\">Inspect tail logs:<br><code>tail -100 /var/log/ms-backup.log</code></p><p style=\"color:#666;font-size:0.9em\">Sent automatically by ${SCRIPT_NAME} on backup failure (Phase 1 Step C3).</p>"

    # JSON payload (printf-safe quoting).
    local payload
    payload=$(printf '{"sender":{"name":"AFianco Ops","email":"%s"},"to":[{"email":"%s"}],"subject":"%s","htmlContent":"%s"}' \
        "${sender_email}" "${BACKUP_ALERT_EMAIL}" "${subject}" "${body}")

    # 5-second cap so a hung Brevo never delays the next cron tick.
    if curl -s --max-time 5 -X POST "https://api.brevo.com/v3/smtp/email" \
        -H "accept: application/json" \
        -H "api-key: ${BREVO_API_KEY}" \
        -H "content-type: application/json" \
        -d "${payload}" > /dev/null 2>&1; then
        echo "[INFO] $(date) — Alert email sent to ${BACKUP_ALERT_EMAIL}"
    else
        echo "[WARN] $(date) — Alert email send FAILED (Brevo API unreachable / invalid key)"
    fi
}

# EXIT trap covers both explicit `exit N` and `set -e`-triggered failures.
trap 'send_alert_on_failure' EXIT

# ── Load env vars ────────────────────────────────────────────────────
if [ -f "${PROJECT_DIR}/.env.production" ]; then
    export $(grep -v '^#' "${PROJECT_DIR}/.env.production" | xargs)
fi

if [ -z "${MONGO_ROOT_USER:-}" ] || [ -z "${MONGO_ROOT_PASSWORD:-}" ] || [ -z "${DB_NAME:-}" ]; then
    echo "[ERROR] $(date) — Missing MONGO_ROOT_USER, MONGO_ROOT_PASSWORD, or DB_NAME"
    exit 1
fi

# ── Verify encryption prerequisites (Phase 1 Step C1) ────────────────
if ! command -v age >/dev/null 2>&1; then
    echo "[ERROR] $(date) — 'age' binary not installed. Install with: apt install age"
    exit 1
fi

if [ ! -f "${AGE_PUBKEY_FILE}" ]; then
    echo "[ERROR] $(date) — age public key file missing: ${AGE_PUBKEY_FILE}"
    exit 1
fi

# Read first non-comment, non-empty line as the recipient public key.
AGE_RECIPIENT=$(grep -v '^#' "${AGE_PUBKEY_FILE}" | grep -v '^[[:space:]]*$' | head -1 | tr -d '[:space:]')
if [ -z "${AGE_RECIPIENT}" ] || [[ ! "${AGE_RECIPIENT}" =~ ^age1[a-z0-9]+$ ]]; then
    echo "[ERROR] $(date) — age public key invalid in ${AGE_PUBKEY_FILE}: '${AGE_RECIPIENT}'"
    exit 1
fi
echo "[INFO] $(date) — Encryption: age recipient ${AGE_RECIPIENT:0:25}..."

# Helper: encrypt a file in-place (input → input.age, original removed).
# Echoes the new filename (.age) to stdout for caller to capture.
encrypt_file() {
    local plain_path=$1
    local encrypted_path="${plain_path}.age"
    age -r "${AGE_RECIPIENT}" -o "${encrypted_path}" "${plain_path}"
    rm -f "${plain_path}"
    echo "${encrypted_path}"
}

# ── Prepare ──────────────────────────────────────────────────────────
# Filenames distinguish PLAIN (transient, on local disk only) from final
# encrypted .age (uploaded to Storage Box). Plain files are deleted right
# after encryption — they never leave the VPS.
mkdir -p "${TMP_DIR}"
DB_PLAIN="db_${TIMESTAMP}.gz"
UPLOADS_PLAIN="uploads_${TIMESTAMP}.tar.gz"
CONFIG_PLAIN="config_${TIMESTAMP}.tar.gz"
DB_FILE="${DB_PLAIN}.age"
UPLOADS_FILE="${UPLOADS_PLAIN}.age"
CONFIG_FILE="${CONFIG_PLAIN}.age"

echo "[INFO] $(date) — Starting backup..."

# ── Step 1: MongoDB dump ─────────────────────────────────────────────
echo "[INFO] $(date) — Dumping MongoDB (${DB_NAME})..."
docker exec ms-mongodb mongodump \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/${DB_NAME}?authSource=admin" \
    --archive --gzip \
    > "${TMP_DIR}/${DB_PLAIN}"

# Encrypt: produces ${DB_FILE} (= ${DB_PLAIN}.age), removes plain.
encrypt_file "${TMP_DIR}/${DB_PLAIN}" >/dev/null
DB_SIZE=$(du -h "${TMP_DIR}/${DB_FILE}" | cut -f1)
echo "[INFO] $(date) — MongoDB dump encrypted: ${DB_FILE} (${DB_SIZE})"

# ── Step 2: Uploads volume ───────────────────────────────────────────
echo "[INFO] $(date) — Archiving uploads volume..."
UPLOADS_VOLUME=$(docker volume inspect ms-backend-uploads --format '{{.Mountpoint}}' 2>/dev/null || echo "")

if [ -n "${UPLOADS_VOLUME}" ] && [ -d "${UPLOADS_VOLUME}" ]; then
    tar -czf "${TMP_DIR}/${UPLOADS_PLAIN}" -C "${UPLOADS_VOLUME}" . 2>/dev/null || true
    if [ -f "${TMP_DIR}/${UPLOADS_PLAIN}" ] && [ -s "${TMP_DIR}/${UPLOADS_PLAIN}" ]; then
        encrypt_file "${TMP_DIR}/${UPLOADS_PLAIN}" >/dev/null
        UPLOADS_SIZE=$(du -h "${TMP_DIR}/${UPLOADS_FILE}" | cut -f1)
        echo "[INFO] $(date) — Uploads archive encrypted: ${UPLOADS_FILE} (${UPLOADS_SIZE})"
    else
        echo "[WARN] $(date) — Uploads tar empty, skipping"
        rm -f "${TMP_DIR}/${UPLOADS_PLAIN}"
        UPLOADS_FILE=""
    fi
else
    echo "[WARN] $(date) — Uploads volume not found, skipping"
    UPLOADS_FILE=""
fi

# ── Step 2.5: Server config snapshot (Phase 1 Step C5 + drill #1 fix) ─
# Captures everything needed to rebuild the running stack on a fresh VPS:
#   - .env.production           → all secrets (Stripe, JWT, Mongo, Brevo, ...)
#   - docker-compose.prod.yml   → stack definition (services, volumes, env propagation)
#   - deploy/nginx/             → reverse-proxy + TLS routing + security headers
#   - letsencrypt/              → ACME state, fullchain.pem, privkey.pem (from
#                                  Docker volume ms-certbot-conf — see below)
#   - root crontab              → backup + certbot renewal schedule
#
# Why letsencrypt is sourced from a volume snapshot, not /etc/letsencrypt:
# the certs live exclusively inside the Docker volume `ms-certbot-conf`
# (mounted at /etc/letsencrypt inside the ms-nginx container). The host
# path /etc/letsencrypt does NOT exist — the previous version of this
# script silently skipped certs because of `--ignore-failed-read`. The
# 2026-05-09 restore drill exposed this gap (see
# docs/operations/restore-drill-history.md → finding #1). The fix below
# snapshots the volume to ${TMP_DIR}/letsencrypt/ via a throwaway alpine
# container with the volume mounted read-only, then includes that
# directory in the tar via a second `-C` switch.
#
# WARNING: this archive contains plaintext secrets and TLS private keys.
# Phase 1 Step C1 already encrypts all backups (db_, uploads_, config_)
# at rest with `age` so the Storage Box never holds unencrypted secrets.

LETSENCRYPT_SNAPSHOT="${TMP_DIR}/letsencrypt"
LETSENCRYPT_AVAILABLE=0
if docker volume inspect ms-certbot-conf >/dev/null 2>&1; then
    echo "[INFO] $(date) — Snapshotting Docker volume ms-certbot-conf..."
    rm -rf "${LETSENCRYPT_SNAPSHOT}"
    mkdir -p "${LETSENCRYPT_SNAPSHOT}"
    # Read-only mount on the source: we cannot accidentally mutate the
    # live volume. `cp -a` preserves perms / symlinks / ownership which
    # certbot relies on.
    if docker run --rm \
        -v ms-certbot-conf:/source:ro \
        -v "${LETSENCRYPT_SNAPSHOT}:/dest" \
        alpine:3 sh -c "cp -a /source/. /dest/" 2>/dev/null; then
        CERT_COUNT=$(find "${LETSENCRYPT_SNAPSHOT}" -name 'fullchain.pem' 2>/dev/null | wc -l | tr -d ' ')
        if [ "${CERT_COUNT}" -gt 0 ]; then
            LETSENCRYPT_AVAILABLE=1
            echo "[INFO] $(date) — Volume snapshot: ${CERT_COUNT} cert chain(s) captured"
        else
            # Volume exists but is empty — still include it so a fresh
            # restore at least sets up the dir structure correctly.
            LETSENCRYPT_AVAILABLE=1
            echo "[WARN] $(date) — Volume snapshot: 0 fullchain.pem (volume empty?), including dir anyway"
        fi
    else
        echo "[WARN] $(date) — Docker snapshot of ms-certbot-conf failed, certs WILL be missing in this backup"
    fi
else
    echo "[WARN] $(date) — Docker volume ms-certbot-conf not found, certs WILL be missing in this backup"
fi

echo "[INFO] $(date) — Archiving server config..."
if [ "${LETSENCRYPT_AVAILABLE}" -eq 1 ]; then
    # Two `-C` blocks: host paths first, then the volume snapshot dir.
    # Inside the tar, the snapshot lives at `letsencrypt/...` which is
    # what backup-recovery.md → "Recipe 3" expects on restore.
    tar -czf "${TMP_DIR}/${CONFIG_PLAIN}" \
        --ignore-failed-read \
        -C / \
            "opt/margin-sentinel/.env.production" \
            "opt/margin-sentinel/docker-compose.prod.yml" \
            "opt/margin-sentinel/deploy/nginx" \
            "var/spool/cron/crontabs/root" \
        -C "${TMP_DIR}" \
            "letsencrypt" \
        2>/dev/null || true
else
    # Fall-through: produce the archive without certs rather than failing
    # the entire backup. Operator gets the WARN above + email alert never
    # fires because tar exit is masked by `|| true`. Document loudly.
    tar -czf "${TMP_DIR}/${CONFIG_PLAIN}" \
        --ignore-failed-read \
        -C / \
            "opt/margin-sentinel/.env.production" \
            "opt/margin-sentinel/docker-compose.prod.yml" \
            "opt/margin-sentinel/deploy/nginx" \
            "var/spool/cron/crontabs/root" \
        2>/dev/null || true
fi

# Snapshot dir is no longer needed once the tar is built. Always cleaned
# up, even if tar above failed, to leave the VPS state predictable.
rm -rf "${LETSENCRYPT_SNAPSHOT}"

if [ -f "${TMP_DIR}/${CONFIG_PLAIN}" ] && [ -s "${TMP_DIR}/${CONFIG_PLAIN}" ]; then
    encrypt_file "${TMP_DIR}/${CONFIG_PLAIN}" >/dev/null
    CONFIG_SIZE=$(du -h "${TMP_DIR}/${CONFIG_FILE}" | cut -f1)
    echo "[INFO] $(date) — Config archive encrypted: ${CONFIG_FILE} (${CONFIG_SIZE})"
else
    echo "[WARN] $(date) — Config archive missing or empty, skipping upload"
    rm -f "${TMP_DIR}/${CONFIG_PLAIN}"
    CONFIG_FILE=""
fi

# ── Step 3: Upload to Storage Box ────────────────────────────────────
echo "[INFO] $(date) — Uploading to Storage Box..."

# Create remote directory if it doesn't exist
ssh -p ${STORAGE_PORT} -o StrictHostKeyChecking=no -o BatchMode=yes \
    ${STORAGE_USER}@${STORAGE_HOST} "mkdir -p ${STORAGE_DIR}" 2>/dev/null || true

# Upload database
scp -P ${STORAGE_PORT} -o BatchMode=yes \
    "${TMP_DIR}/${DB_FILE}" \
    "${STORAGE_USER}@${STORAGE_HOST}:${STORAGE_DIR}/${DB_FILE}"
echo "[INFO] $(date) — Uploaded ${DB_FILE}"

# Upload uploads archive (if exists)
if [ -n "${UPLOADS_FILE}" ] && [ -f "${TMP_DIR}/${UPLOADS_FILE}" ]; then
    scp -P ${STORAGE_PORT} -o BatchMode=yes \
        "${TMP_DIR}/${UPLOADS_FILE}" \
        "${STORAGE_USER}@${STORAGE_HOST}:${STORAGE_DIR}/${UPLOADS_FILE}"
    echo "[INFO] $(date) — Uploaded ${UPLOADS_FILE}"
fi

# Upload config archive (if produced — Phase 1 Step C5)
if [ -n "${CONFIG_FILE}" ] && [ -f "${TMP_DIR}/${CONFIG_FILE}" ]; then
    scp -P ${STORAGE_PORT} -o BatchMode=yes \
        "${TMP_DIR}/${CONFIG_FILE}" \
        "${STORAGE_USER}@${STORAGE_HOST}:${STORAGE_DIR}/${CONFIG_FILE}"
    echo "[INFO] $(date) — Uploaded ${CONFIG_FILE}"
fi

# ── Step 4: Cleanup local temp ───────────────────────────────────────
# Defensive: remove both encrypted (.age) and any leftover plain files.
# Plain files SHOULD already be gone (encrypt_file rm's them) but a partial
# crash could leave them on disk — and plaintext on the VPS is exactly what
# encryption is supposed to avoid.
rm -f "${TMP_DIR}/${DB_FILE}" "${TMP_DIR}/${UPLOADS_FILE}" "${TMP_DIR}/${CONFIG_FILE}" \
      "${TMP_DIR}/${DB_PLAIN}" "${TMP_DIR}/${UPLOADS_PLAIN}" "${TMP_DIR}/${CONFIG_PLAIN}" 2>/dev/null
rmdir "${TMP_DIR}" 2>/dev/null || true
echo "[INFO] $(date) — Local temp files cleaned"

# ── Step 5: Remote retention (delete > RETENTION_DAYS) ───────────────
# Phase 1 Step C2 — fixed remote cleanup.
# Hetzner Storage Box does NOT allow arbitrary SSH commands (find/while
# loops) over its SSH login — only SFTP is reliably supported. The old
# implementation relied on a `find` over SSH and silently failed every
# night for ~3 weeks (visible as "Remote cleanup skipped" in the log).
#
# New approach:
#   1. List remote files via SFTP `ls -1`.
#   2. Filter to our naming patterns (db_, uploads_, config_).
#   3. Parse the YYYYMMDD timestamp from the filename and compare
#      against today minus RETENTION_DAYS — no need to query mtime.
#   4. Delete out-of-window files via a single SFTP batch command.
#
# Robust on Linux (GNU date) and macOS (BSD date, dev-only).
echo "[INFO] $(date) — Cleaning old backups on Storage Box..."

# 1. List remote files
REMOTE_LIST=$(sftp -P ${STORAGE_PORT} -o BatchMode=yes -o StrictHostKeyChecking=no \
    "${STORAGE_USER}@${STORAGE_HOST}" 2>/dev/null <<EOF
cd ${STORAGE_DIR}
ls -1
EOF
) || REMOTE_LIST=""

REMOTE_FILES=$(echo "${REMOTE_LIST}" | grep -E '^(db_|uploads_|config_)' || true)

if [ -z "${REMOTE_FILES}" ]; then
    echo "[INFO] $(date) — No backup files found on Storage Box (clean state)"
else
    # 2. Compute cutoff (YYYYMMDD). Linux first, macOS fallback.
    DELETE_BEFORE_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y%m%d 2>/dev/null \
        || date -v "-${RETENTION_DAYS}d" +%Y%m%d)

    # 3. Filter old files
    DELETE_LIST=()
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        FILE_DATE=$(echo "$f" | grep -oE '[0-9]{8}' | head -1)
        if [ -n "${FILE_DATE}" ] && [ "${FILE_DATE}" -lt "${DELETE_BEFORE_DATE}" ]; then
            DELETE_LIST+=("$f")
        fi
    done <<< "${REMOTE_FILES}"

    if [ ${#DELETE_LIST[@]} -eq 0 ]; then
        echo "[INFO] $(date) — No backups older than ${RETENTION_DAYS} days to delete"
    else
        # 4. Build SFTP batch and execute
        echo "[INFO] $(date) — Deleting ${#DELETE_LIST[@]} backup(s) older than ${RETENTION_DAYS} days (cutoff: ${DELETE_BEFORE_DATE})..."
        SFTP_CMDS="cd ${STORAGE_DIR}"$'\n'
        for f in "${DELETE_LIST[@]}"; do
            SFTP_CMDS="${SFTP_CMDS}rm ${f}"$'\n'
            echo "  - ${f}"
        done
        if echo "${SFTP_CMDS}" | sftp -P ${STORAGE_PORT} -o BatchMode=yes \
            "${STORAGE_USER}@${STORAGE_HOST}" >/dev/null 2>&1; then
            echo "[INFO] $(date) — Deleted ${#DELETE_LIST[@]} file(s) successfully"
        else
            echo "[WARN] $(date) — SFTP rm batch failed (retry tomorrow). Files: ${DELETE_LIST[*]}"
        fi
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────
echo "[INFO] $(date) — Backup complete!"
echo "  Database: ${DB_FILE} (${DB_SIZE})"
[ -n "${UPLOADS_FILE}" ] && echo "  Uploads:  ${UPLOADS_FILE} (${UPLOADS_SIZE:-0})"
[ -n "${CONFIG_FILE}" ] && echo "  Config:   ${CONFIG_FILE} (${CONFIG_SIZE:-0})"
echo "  Location: ${STORAGE_USER}@${STORAGE_HOST}:${STORAGE_DIR}/"
