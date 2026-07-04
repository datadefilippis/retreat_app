#!/bin/bash
# ── AFianco — Self-hosted uptime monitor (Phase 1 Step B1) ──────────
#
# Cron-driven liveness probe against the public /api/health/ready endpoint.
# Sends an email alert via Brevo when the endpoint is down N times in a row,
# and a "RESOLVED" email when it comes back up.
#
# Self-hosted (zero external services, zero new account, zero monthly cost).
# Reuses BREVO_API_KEY + SMTP_FROM_EMAIL + BACKUP_ALERT_EMAIL already in
# .env.production for transactional emails.
#
# Usage:
#   ./deploy/uptime_monitor.sh
#
# Cron (every minute):
#   * * * * * /opt/margin-sentinel/deploy/uptime_monitor.sh >> /var/log/ms-uptime.log 2>&1
#
# Trade-off (documented in docs/operations/runbook.md): this monitor runs
# ON THE SAME VPS as the app. If the VPS itself is down (network outage,
# kernel panic, Hetzner DC issue), the monitor cannot send email. Hetzner
# Cloud's own infrastructure monitoring covers VPS-level outages and emails
# the account owner directly. This script covers the more common
# application-level scenarios: container crash loop, MongoDB OOM, expired
# certificate, deploy regression — situations where the VPS is up but the
# app is not.
#
# State machine:
#
#       (start)
#          │
#          ▼
#   ┌──────────────┐    ready=200    ┌──────────────┐
#   │   UP (0)     │ ◀───────────────│   DOWN (n)   │
#   │              │                 │              │
#   │  no email    │   ready≠200     │  if n=THRESH │
#   │              │ ───────────────▶│  send DOWN   │
#   └──────────────┘                 │  email once  │
#         │ │                        └──────────────┘
#         │ └── on UP→UP: nothing      │
#         │                            │ ready=200, was DOWN→UP transition
#         └────────────────────────────┘
#                     send RESOLVED email

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STATE_DIR="/var/lib/afianco-uptime"
STATE_FILE="${STATE_DIR}/state"
HEALTH_URL="https://afianco.app/api/health/ready"
TIMEOUT_SECONDS=10
THRESHOLD_FAILS=3                  # consecutive failures before alert email
ALERT_COOLDOWN_SECONDS=900         # 15 min — no re-alert if still down
HOSTNAME_TAG="$(hostname)"

# ── Load env ─────────────────────────────────────────────────────────
if [ -f "${PROJECT_DIR}/.env.production" ]; then
    export $(grep -v '^#' "${PROJECT_DIR}/.env.production" | xargs) 2>/dev/null || true
fi

# ── State store ──────────────────────────────────────────────────────
mkdir -p "${STATE_DIR}"
# Default state: UP, 0 fails, no last alert
if [ ! -f "${STATE_FILE}" ]; then
    cat > "${STATE_FILE}" <<EOF
status=UP
consecutive_fails=0
last_alert_sent=0
last_check=0
EOF
fi

# Read state
# shellcheck disable=SC1090
source "${STATE_FILE}"
prev_status="${status:-UP}"
prev_fails="${consecutive_fails:-0}"
prev_last_alert="${last_alert_sent:-0}"

now_unix=$(date +%s)
now_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ── Probe ────────────────────────────────────────────────────────────
http_code=$(curl -s -o /tmp/uptime-resp.txt -w "%{http_code}" \
    --max-time "${TIMEOUT_SECONDS}" \
    "${HEALTH_URL}" || echo "000")
body_snippet=$(head -c 200 /tmp/uptime-resp.txt 2>/dev/null || echo "")
rm -f /tmp/uptime-resp.txt

# Determine current status: 200 = UP, anything else = DOWN
if [ "${http_code}" = "200" ]; then
    current_status="UP"
else
    current_status="DOWN"
fi

# ── Email sender ─────────────────────────────────────────────────────
send_alert_email() {
    local subject=$1
    local body_html=$2

    if [ -z "${BREVO_API_KEY:-}" ] || [ -z "${BACKUP_ALERT_EMAIL:-}" ]; then
        echo "[WARN] $(date) — Uptime alert NOT sent: BREVO_API_KEY or BACKUP_ALERT_EMAIL is empty"
        return 0
    fi

    local sender_email="${SMTP_FROM_EMAIL:-noreply@afianco.app}"
    local payload
    payload=$(printf '{"sender":{"name":"AFianco Uptime","email":"%s"},"to":[{"email":"%s"}],"subject":"%s","htmlContent":"%s"}' \
        "${sender_email}" "${BACKUP_ALERT_EMAIL}" "${subject}" "${body_html}")

    if curl -s --max-time 5 -X POST "https://api.brevo.com/v3/smtp/email" \
        -H "accept: application/json" \
        -H "api-key: ${BREVO_API_KEY}" \
        -H "content-type: application/json" \
        -d "${payload}" > /dev/null 2>&1; then
        echo "[INFO] $(date) — Uptime alert email sent: ${subject}"
        return 0
    else
        echo "[WARN] $(date) — Uptime alert email FAILED: ${subject}"
        return 1
    fi
}

# ── State transitions + alerting ─────────────────────────────────────
new_fails=0
new_last_alert="${prev_last_alert}"

if [ "${current_status}" = "UP" ]; then
    # Probe successful
    if [ "${prev_status}" = "DOWN" ]; then
        # DOWN → UP transition: send RESOLVED email
        echo "[INFO] $(date) — Uptime RECOVERED on ${HOSTNAME_TAG} (was DOWN, now UP)"
        body="<h2 style=\"color:#0a0\">AFianco — Service RECOVERED</h2><p>The probe at <code>${HEALTH_URL}</code> is responding 200 again.</p><p><b>Server:</b> ${HOSTNAME_TAG}<br><b>Recovered at:</b> ${now_iso}<br><b>Previous fails:</b> ${prev_fails} consecutive checks</p><p style=\"color:#666;font-size:0.9em\">Sent automatically by uptime_monitor.sh (Phase 1 Step B1).</p>"
        send_alert_email "[AFianco] Service RECOVERED on ${HOSTNAME_TAG}" "${body}" || true
    fi
    # else UP→UP: no-op (every minute, would spam logs)
    new_fails=0
else
    # Probe failed
    new_fails=$(( prev_fails + 1 ))
    echo "[WARN] $(date) — Uptime probe failed on ${HOSTNAME_TAG} (http_code=${http_code}, consecutive_fails=${new_fails})"

    # Threshold check + cooldown to avoid re-emailing every minute on a long outage
    if [ "${new_fails}" -ge "${THRESHOLD_FAILS}" ]; then
        time_since_alert=$(( now_unix - prev_last_alert ))
        # Send only if (a) we haven't alerted yet, OR (b) cooldown expired
        if [ "${prev_last_alert}" = "0" ] || [ "${time_since_alert}" -gt "${ALERT_COOLDOWN_SECONDS}" ]; then
            body_snip_escaped=$(echo "${body_snippet}" | head -c 150 | sed "s/'/\&#39;/g; s/\"/\&quot;/g; s/</\&lt;/g; s/>/\&gt;/g")
            body="<h2 style=\"color:#c00\">AFianco — Service DOWN</h2><p>The probe at <code>${HEALTH_URL}</code> failed <b>${new_fails}</b> consecutive times.</p><table style=\"font-family:sans-serif;border-collapse:collapse\"><tr><td style=\"padding:4px 12px 4px 0\"><b>Server</b></td><td>${HOSTNAME_TAG}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>HTTP code</b></td><td><code>${http_code}</code></td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Failed at</b></td><td>${now_iso}</td></tr><tr><td style=\"padding:4px 12px 4px 0\"><b>Body snippet</b></td><td><code>${body_snip_escaped}</code></td></tr></table><p>Possible causes:<ul><li>Backend container crashed (check <code>docker ps</code>)</li><li>MongoDB OOM (check <code>docker logs ms-mongodb</code>)</li><li>nginx misconfig (recent deploy?)</li><li>TLS cert expired (rare — certbot auto-renews)</li></ul></p><p>Inspect logs: <code>tail -100 /var/log/ms-uptime.log</code> and <code>docker compose logs --since 30m</code>.</p><p style=\"color:#666;font-size:0.9em\">Re-alert cooldown: ${ALERT_COOLDOWN_SECONDS}s. Sent by uptime_monitor.sh (Phase 1 Step B1).</p>"
            send_alert_email "[AFianco] Service DOWN on ${HOSTNAME_TAG} (${new_fails} fails)" "${body}" \
                && new_last_alert="${now_unix}"
        else
            echo "[INFO] $(date) — Re-alert suppressed (cooldown ${ALERT_COOLDOWN_SECONDS}s, last alert ${time_since_alert}s ago)"
        fi
    fi
fi

# ── Persist new state ────────────────────────────────────────────────
cat > "${STATE_FILE}" <<EOF
status=${current_status}
consecutive_fails=${new_fails}
last_alert_sent=${new_last_alert}
last_check=${now_unix}
EOF

# Concise log line (1 per minute is acceptable noise)
echo "[INFO] $(date) — probe status=${current_status} http=${http_code} fails=${new_fails}"
