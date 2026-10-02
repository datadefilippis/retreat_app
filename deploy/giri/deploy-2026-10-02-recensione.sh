#!/bin/bash
# GIRO 2/10/2026 (sera, 5°) — Il Cerchio dalla recensione (RC1-RC2): casella
# facoltativa nel modal, un solo invio, iscrizione best-effort con prova OTP.
# Backend + frontend, NIENTE nginx, nessun flag. Nessuna email parte da sola.
# Verifica in prod SENZA creare recensioni: un submit con codice sbagliato deve
# dare il 400 di sempre, e la pagina dell'operatore deve servire il bundle nuovo.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-02-recensione
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
for u in / /cerca-ritiro /o/anpoche /operatori /api/health /api/public/discipline /privacy; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/o/anpoche | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · stesso su / → %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)"
printf "   legale → %s (atteso v2.10)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o "\"version_tag\":\"[^\"]*\"")"
printf "   submit con codice sbagliato (payload nuovo) → %s (atteso 400 invalid_code, nessuna scrittura)\n" "$(curl -s -X POST https://aurya.life/api/public/reviews/submit -H 'Content-Type: application/json' -d '{"org_slug":"anpoche","email":"verifica-giro@example.invalid","code":"000000","rating":5,"body":"verifica del giro, nessuna scrittura attesa qui","author_name":"Giro","website":"","cerchio":true,"consenso_versione":"cerchio-v3"}' | cut -c1-80)"
printf "   submit con codice sbagliato (payload di oggi) → %s\n" "$(curl -s -X POST https://aurya.life/api/public/reviews/submit -H 'Content-Type: application/json' -d '{"org_slug":"anpoche","email":"verifica-giro@example.invalid","code":"000000","rating":5,"body":"verifica del giro, nessuna scrittura attesa qui","author_name":"Giro","website":""}' | cut -c1-80)"
echo "== FATTO. Ora: git tag prod-$GIRO."
