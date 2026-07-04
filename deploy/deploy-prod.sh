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
VPS_DIR="${VPS_DIR:-/opt/margin-sentinel}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
DOMAIN="${DOMAIN:-afianco.app}"
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
  --exclude='deploy/nginx/nginx.conf' \
  --exclude='deploy/nginx/nginx-tls.conf' \
  --exclude='deploy/nginx/nginx-bootstrap.conf' \
  -e "ssh -i $SSH_KEY" \
  ./ "${VPS_HOST}:${VPS_DIR}/"

echo ""
echo "── [2/3] Rebuilding and restarting containers..."
ssh -i "$SSH_KEY" "$VPS_HOST" "cd $VPS_DIR && $COMPOSE up -d --build"

echo ""
echo "── [3/3] Waiting for healthcheck..."
sleep 15
ssh -i "$SSH_KEY" "$VPS_HOST" "cd $VPS_DIR && $COMPOSE ps && echo '---' && curl -s http://localhost/api/health"

echo ""
echo "── Deploy complete! https://${DOMAIN}"
