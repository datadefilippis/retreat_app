#!/bin/bash
# GIRO 5/10/2026 (2°) — SOLO nginx: la CSP ammette il Meta Pixel
# (script-src connect.facebook.net; connect-src www.facebook.com +
# connect.facebook.net). Trovato al primo giro dal browser: col consenso
# marketing fbevents.js veniva bloccato (stato 0), nessun evento dal browser.
# Niente backend/frontend da ricostruire. Il file e' bind-mountato: dopo il
# rsync serve --force-recreate di nginx-proxy (un reload non vede il file
# nuovo). Prima: nginx -t sul conf nuovo DENTRO il container vivo.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-05-meta-csp
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [1] rsync del solo nginx.conf"
rsync -avz -e "ssh -i $KEY" "$REPO/deploy/nginx/nginx.conf" "$HOST:/opt/aurya/deploy/nginx/nginx.conf" | tail -1

echo "== [2] nginx -t sul conf nuovo dentro il container vivo"
$SSH 'cd /opt/aurya && docker cp deploy/nginx/nginx.conf ms-nginx:/tmp/new.conf && docker exec ms-nginx sh -c "sed \"s#include /etc/nginx/conf.d/\*.conf;#include /tmp/new.conf;#\" /etc/nginx/nginx.conf > /tmp/main.conf && nginx -t -c /tmp/main.conf" 2>&1 | tail -2'
$SSH 'docker exec ms-nginx sh -c "nginx -t -c /tmp/main.conf" >/dev/null 2>&1' || { echo "CONF NON VALIDO: FERMO"; exit 1; }

echo "== [3] force-recreate nginx-proxy (pochi secondi)"
$SSH 'cd /opt/aurya && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate nginx-proxy 2>&1 | tail -1'
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "   health ok ($i)"; break; }
  sleep 2
done

echo "== [4] verifica"
for u in / /cerca-ritiro /o/anpoche /api/health /l/anpoche; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   CSP script-src → %s\n" "$(curl -sI https://aurya.life/cerca-ritiro | grep -i '^content-security-policy' | grep -o "script-src [^;]*")"
printf "   CSP connect-src ha facebook → %s (atteso 2)\n" "$(curl -sI https://aurya.life/cerca-ritiro | grep -i '^content-security-policy' | grep -o "connect-src [^;]*" | grep -o "facebook" | wc -l | tr -d ' ')"
printf "   unsafe-inline negli script → %s (atteso 0)\n" "$(curl -sI https://aurya.life/ | grep -i '^content-security-policy' | grep -o "script-src [^;]*" | grep -c "unsafe-inline" || true)"
echo "== FATTO. Ora: git tag prod-$GIRO."
