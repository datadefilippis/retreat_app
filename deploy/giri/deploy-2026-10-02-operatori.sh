#!/bin/bash
# GIRO 2/10/2026 (sera, 4°) — Operatori in Brevo (OP1-OP3): informativa 1-bis +
# Termini 19.4 (v2.10, modal riscritto), sync operatori (profilo + job
# giornaliero), opposizione dal webhook. Backend + frontend (il testo del
# modal e' nel bundle), NIENTE nginx. Poi dal container: attributi nuovi,
# riallineamento del Cerchio (per AURYA_TIPO) e degli operatori, verifica.
# Solo API contatti: NESSUNA email. Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-02-operatori
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

echo "== [3] verifica sito"
for u in / /cerca-ritiro /o/anpoche /operatori /accedi /api/health /privacy /termini /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   legale → %s (atteso v2.10)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o "\"version_tag\":\"[^\"]*\"")"
printf "   informativa 1-bis → %s (atteso 1)\n" "$(curl -s "https://aurya.life/api/legal/privacy?lang=it" | grep -c "| 1-bis |" || true)"
printf "   termini 19.4 nuovo → %s (atteso 1)\n" "$(curl -s "https://aurya.life/api/legal/terms?lang=it" | grep -c "aggiornamenti sulla Piattaforma" || true)"
JS=$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · stesso su /operatori → %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/operatori | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)"

echo "== [4] Brevo dal container: attributi → Cerchio (AURYA_TIPO) → operatori → verifica (solo API contatti)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python scripts/brevo_segmentazione.py --attributi --backfill --operatori --verifica 2>&1 | grep -v "bcrypt\|Traceback\|^  File\|version = \|\^\|AttributeError"'
echo "== FATTO. Ora: git tag prod-$GIRO."
