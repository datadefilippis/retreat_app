#!/bin/bash
# GIRO 2/10/2026 — Il registro vivo delle discipline (DV1-DV3: il system admin
# aggiunge discipline dalla regia e sono subito di tutti) + «Regressione &
# Vite passate» e sinonimi Pranic Healing (25d09d60). Backend + frontend,
# NIENTE nginx (la rotta nuova /api/public/discipline sta sotto /api/public/,
# gia' instradata). Flag DISCIPLINE_VIVE=1 scritto in .env.production e
# backend ricreato con --force-recreate (lezione 25/9: l'env entra solo cosi').
# Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-02-discipline-vive
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

echo "== [1b] flag DISCIPLINE_VIVE=1 in .env.production (idempotente)"
$SSH "cd /opt/aurya && grep -q '^DISCIPLINE_VIVE=' .env.production && sed -i 's/^DISCIPLINE_VIVE=.*/DISCIPLINE_VIVE=1/' .env.production || echo 'DISCIPLINE_VIVE=1' >> .env.production; grep '^DISCIPLINE_VIVE=' .env.production"

echo "== [2] build + recreate (frontend, poi backend) sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -1 && echo "== frontend pronto $(date -u +%H:%M:%S)" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1
sleep 5
$C up -d --no-deps --force-recreate backend 2>&1 | tail -1
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

echo "== [3] verifica"
for u in / /o/anpoche /operatori /meditazioni /accedi /entra-nella-rete /api/health /privacy /termini /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   discipline vive → %s (atteso vive:true, totale 60, extra [])\n" "$(curl -s https://aurya.life/api/public/discipline | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[\"vive\"], d[\"totale\"], d[\"extra\"], len(d[\"famiglie\"]))')"
printf "   regia senza token → %s (atteso 401/403)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/admin/discipline)"
printf "   legale → %s (atteso v2.8) · contatti anpoche dietro la porta → %s (atteso 0)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o "\"version_tag\":\"[^\"]*\"")" "$(curl -s https://aurya.life/api/public/operator/anpoche | grep -c public_phone)"
printf "   flag nel container → %s\n" "$($SSH "docker exec \$(docker ps -qf name=backend | head -1) printenv DISCIPLINE_VIVE")"
echo "== FATTO. Ora: git tag prod-$GIRO."
