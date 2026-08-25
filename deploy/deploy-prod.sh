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

# ── GUARDIA DEL BERSAGLIO (22/8/2026) ──────────────────────────────
# Il 22 agosto questo deploy e' finito sul server di AFianco perche' il
# runbook — ereditato dal fork — riportava l'IP di QUELL'altro progetto:
# rsync --delete sopra il suo codice e afianco.app giu' per 15 minuti.
# Da allora lo script si rifiuta di partire se il target non e' il
# server a cui punta davvero il dominio. La macchina controlla, non la
# memoria di chi lancia.
echo "── [0/3] Verifica del bersaglio (DNS vs VPS_HOST)..."
IP_DNS="$(dig +short "$DOMAIN" A 2>/dev/null | tail -1)"
IP_TARGET="${VPS_HOST##*@}"
if [ -z "$IP_DNS" ]; then
  echo "   ⚠  DNS di $DOMAIN non risolvibile: verifica a mano prima di procedere." >&2
  exit 1
fi
if [ "$IP_DNS" != "$IP_TARGET" ]; then
  cat >&2 <<FINE
   ⛔ FERMO: stai puntando al server SBAGLIATO.
      $DOMAIN risponde su .... $IP_DNS
      tu stai deployando su ... $IP_TARGET
   Se e' voluto, esporta FORZA_BERSAGLIO=1. Altrimenti rileggi la
   Regola Zero in docs/operations/runbook.md.
FINE
  [ "${FORZA_BERSAGLIO:-0}" = "1" ] || exit 1
  echo "   (forzato a mano: FORZA_BERSAGLIO=1)"
fi
echo "   ✓ $DOMAIN → $IP_TARGET: bersaglio giusto"

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
# LA PROVA PRIMA DEL RIAVVIO (26/8/2026, dopo un sito giu' per una
# regex). nginx legge `{` e `}` come delimitatori di blocco: un
# quantificatore {1,6} non quotato lo fa morire all'avvio, e siccome
# qui si RIAVVIA (il bind-mount non rilegge col reload) il container
# entra in loop e il sito sparisce. `nginx -t` costa un secondo e
# risponde alla sola domanda che conta: questa config parte?
# Se non parte ci si ferma PRIMA, con i container vecchi ancora in
# piedi e il sito acceso.
echo "   verifico la configurazione prima di toccare nulla..."
if ! ssh -i "$SSH_KEY" "$VPS_HOST" \
        "docker exec ms-nginx nginx -t -c /etc/nginx/nginx.conf" 2>&1 \
        | grep -q "syntax is ok"; then
  echo ""
  echo "   ✗ FERMO: la configurazione nginx non e' valida."
  ssh -i "$SSH_KEY" "$VPS_HOST" \
      "docker exec ms-nginx nginx -t -c /etc/nginx/nginx.conf" 2>&1 | tail -5
  echo ""
  echo "   Il sito e' ancora ACCESO con la configurazione precedente."
  echo "   Correggi deploy/nginx/nginx.conf e rilancia il deploy."
  exit 1
fi
echo "   ✓ configurazione valida"
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

