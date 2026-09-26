#!/bin/bash
# GIRO SOLO FRONTEND — riusabile (26/9/2026).
#
# LEZIONE del 26/9 (e gia' del 10/9): la shell SEO del backend tiene in
# cache il manifest del bundle. Se si ricrea SOLO il frontend, le pagine
# servite dal renderer (/, /o/*, /meditazioni, /operatori…) puntano al
# main.<hash>.js VECCHIO → 404 → pagina statica senza React, per tutti,
# finche' il backend non viene RICREATO (up -d senza --force-recreate non
# basta: «Running», cache intatta). Questo script fa sempre entrambe le
# cose, nell'ordine giusto, e verifica il bundle su quattro rotte.
# Si lancia DAL MAC:  bash deploy/giri/giro-solo-frontend.sh <etichetta>
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=${1:-frontend-$(date +%Y-%m-%d-%H%M)}
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [1] rsync frontend/src + public + package"
rsync -az --delete --exclude='node_modules' --exclude='build' -e "ssh -i $KEY" "$REPO/frontend/src/" "$HOST:/opt/aurya/frontend/src/"
rsync -az -e "ssh -i $KEY" "$REPO/frontend/public/" "$HOST:/opt/aurya/frontend/public/"
rsync -az -e "ssh -i $KEY" "$REPO/frontend/package.json" "$REPO/frontend/package-lock.json" "$HOST:/opt/aurya/frontend/" 2>/dev/null || true

echo "== [2] build frontend, recreate frontend, POI force-recreate backend (manifest della shell)"
$SSH "cd /opt/aurya && C=\"docker compose -f docker-compose.prod.yml --env-file .env.production\" && \$C build frontend 2>&1 | tail -1 && \$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1 && sleep 4 && \$C up -d --no-deps --force-recreate backend 2>&1 | tail -1; for i in \$(seq 1 30); do curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/health | grep -q 200 && { echo \"   health ok (\$i)\"; break; }; sleep 2; done"

echo "== [3] verifica: ogni rotta della shell punta a un bundle vivo"
KO=0
for u in / /o/anpoche /meditazioni /operatori; do
  M=$(curl -s "https://aurya.life$u" | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "https://aurya.life/$M")
  printf "   %s → %s → %s\n" "$u" "$M" "$CODE"
  [ "$CODE" = "200" ] || KO=1
done
[ "$KO" = "0" ] || { echo "BUNDLE NON VIVO: ricrea il backend a mano"; exit 1; }
echo "== FATTO ($GIRO). Ora: git tag prod-$GIRO."
