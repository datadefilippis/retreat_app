#!/bin/bash
# GIRO 2/10/2026 (sera) — La fascia d'eta' nel Cerchio (ET1-ET4): campo
# facoltativo su /cerca-ritiro, regia Iscritti, informativa v2.9.
# Backend + frontend, NIENTE nginx, nessun flag nuovo. PRIMA del giro:
# attributo di contatto AURYA_ETA (testo) creato in Brevo. Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-02-eta
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
for u in / /cerca-ritiro /o/anpoche /operatori /meditazioni /accedi /api/health /privacy /termini /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   legale → %s (atteso v2.9)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o "\"version_tag\":\"[^\"]*\"")"
printf "   informativa 7-bis → %s (atteso 1)\n" "$(curl -s https://aurya.life/api/legal/privacy?lang=it | grep -c "fascia d'eta' facoltativa" || true)"
JS=$(curl -s https://aurya.life/cerca-ritiro | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · preferenze-eta nel bundle → %s (atteso ≥1)\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/$JS | grep -c 'preferenze-eta')"
printf "   stesso bundle su / → %s\n" "$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)"
printf "   discipline vive → %s (atteso True 60)\n" "$(curl -s https://aurya.life/api/public/discipline | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['vive'], d['totale'])")"
echo "== FATTO. Ora: git tag prod-$GIRO."
