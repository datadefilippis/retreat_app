#!/bin/bash
# GIRO 25/9/2026 (2°) — rientrare e' semplice: striscia «sei dentro» sulle
# pagine pubbliche, /spazio, «Accedi» in cima alla landing, email del
# giorno zero che dice come si rientra. Backend + frontend + NGINX (la
# rotta /spazio entra nella location del renderer: il conf e' un FILE
# bind-mount, rsync ne cambia l'inode e `nginx -s reload` dentro il
# container vivo rilegge il VECCHIO file → serve il force-recreate,
# dopo un `nginx -t` in un container usa-e-getta; lezione del 25/9).
# Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-09-25-rientro
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] nginx: il conf e' un FILE montato (bind): rsync cambia l'inode e il container vivo continua a vedere il vecchio."
echo "       Quindi: prova del conf NUOVO in un container usa-e-getta nella rete di compose, poi force-recreate (servizio nginx-proxy)."
$SSH 'cd /opt/aurya && C="docker compose -f docker-compose.prod.yml --env-file .env.production" && $C run --rm --no-deps --entrypoint nginx nginx-proxy -t 2>&1 | grep -q "test is successful" && $C up -d --force-recreate --no-deps nginx-proxy 2>&1 | tail -1 && sleep 4 && echo "   dentro il container: $(docker exec ms-nginx grep -c spazio /etc/nginx/conf.d/default.conf) occorrenze di spazio (attese 2)"'
printf "   /spazio dal renderer → %s (atteso 200)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/spazio)"

echo "== [3] build + recreate (frontend, poi backend) sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -1 && echo "== frontend pronto $(date -u +%H:%M:%S)" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1
sleep 5
$C up -d --no-deps backend 2>&1 | tail -1
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "== health ok ($i) $(date -u +%H:%M:%S)"; break; }
  sleep 2
done
echo "== FINE $(date -u +%H:%M:%S)"
REMOTO
$SSH "chmod +x /root/deploy-$GIRO.sh && nohup /root/deploy-$GIRO.sh > /root/deploy-$GIRO.log 2>&1 &"
for i in $(seq 1 100); do
  if $SSH "grep -q '== FINE\|FALLITO' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [4] verifica"
for u in / /spazio /accedi /entra-nella-rete /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   /spazio contiene la shell React → %s\n" "$(curl -s https://aurya.life/spazio | grep -c 'id=\"root\"')"
echo "== FATTO. Ora: git tag prod-$GIRO."
