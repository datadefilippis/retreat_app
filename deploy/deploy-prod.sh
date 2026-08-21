#!/bin/bash
# ── AFianco — Deploy to Production ───────────────────
#
# Usage (dal tuo Mac, dalla root del progetto):
#   ./deploy/deploy-prod.sh
#
# Cosa fa:
#   1. Sync dei file sul VPS via rsync (esclude node_modules, .env, etc)
#   2. Rebuild e restart dei container Docker
#   3. Attende healthcheck e mostra lo stato
#
# NOTA: NON sovrascrive .env.production, nginx.conf (già configurati sul VPS)
#       NON tocca i volumi MongoDB (i dati persistono)

set -euo pipefail

VPS_HOST="${VPS_HOST:?ERROR: Set VPS_HOST env var (e.g. export VPS_HOST=root@1.2.3.4)}"
VPS_DIR="${VPS_DIR:-/opt/aurya}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/aurya_deploy}"
DOMAIN="${DOMAIN:-aurya.life}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

echo "── [1/3] Syncing files to VPS..."
rsync -avz --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='data/' \
  --exclude='mongodb-macos-*' \
  --exclude='.claude/worktrees' \
  --exclude='backups' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='frontend/build' \
  --exclude='frontend/node_modules' \
  --exclude='backend/uploads/*.csv' \
  --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' \
  --exclude='AFIANCO_Presentation_Report.docx' \
  --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $SSH_KEY" \
  ./ "${VPS_HOST}:${VPS_DIR}/"

echo ""
echo "── [2/3] Rebuilding and restarting containers..."
ssh -i "$SSH_KEY" "$VPS_HOST" "cd $VPS_DIR && $COMPOSE up -d --build"

# La config nginx e' un BIND-MOUNT DI FILE SINGOLO: rsync sostituisce il
# file (inode nuovo) e il container continua a leggere quello VECCHIO.
# `nginx -s reload` NON basta — rilegge lo stesso inode. Serve il
# restart del container. Successo due volte (12/8 certificati, 21/8
# rotte SEO di /sound): un secondo di blip, sempre meglio di una config
# che sembra applicata e non lo e'.
echo ""
echo "── [2b/3] Restarting nginx (bind-mount: il reload non rilegge il file)..."
ssh -i "$SSH_KEY" "$VPS_HOST" "cd $VPS_DIR && $COMPOSE restart nginx-proxy"

echo ""
echo "── [3/3] Waiting for healthcheck..."
sleep 15
# HTTP redirige a HTTPS: il check va fatto in HTTPS (-k: il cert è per
# il dominio, non per localhost) sull'endpoint /live.
ssh -i "$SSH_KEY" "$VPS_HOST" "cd $VPS_DIR && $COMPOSE ps && echo '---' && curl -sk https://localhost/api/health/live"

echo ""
echo "── Deploy complete! https://${DOMAIN}"
echo ""
echo "PROMEMORIA — cose che questo script NON fa (e che vanno a mano):"
echo "  • uploads: NON stanno in $VPS_DIR/backend/uploads ma nel VOLUME"
echo "    docker (backend_uploads → /app/uploads). Il rsync qui sopra"
echo "    non li tocca. Per portarne di nuovi:"
echo "      docker cp <dir>/. ms-backend:/app/uploads/<sotto>/"
echo "  • migrazioni dati una tantum (es. backfill di campi nuovi)"
echo "  • script di contenuto (/root/run_content_scripts.sh)"

