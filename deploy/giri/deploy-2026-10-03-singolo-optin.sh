#!/bin/bash
# GIRO 3/10/2026 — Singolo opt-in del Cerchio ACCESO (SO): CERCHIO_SINGOLO_OPTIN=1
# in .env.production, AURYA_INVIABILE allineato alla stessa regola del motore
# (consenso basta; il clic resta la prova di qualita'), riallineamento Brevo.
# SOLO BACKEND (nessun file frontend toccato). Nessuna email parte
# dall'accensione: il benvenuto ha una finestra di 0-2 giorni, i vecchi
# «in attesa» non ricevono nulla di arretrato (verificato nel motore).
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-03-singolo-optin
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

echo "== [1b] interruttore CERCHIO_SINGOLO_OPTIN=1 in .env.production (idempotente)"
$SSH "cd /opt/aurya && grep -q '^CERCHIO_SINGOLO_OPTIN=' .env.production && sed -i 's/^CERCHIO_SINGOLO_OPTIN=.*/CERCHIO_SINGOLO_OPTIN=1/' .env.production || echo 'CERCHIO_SINGOLO_OPTIN=1' >> .env.production; grep '^CERCHIO_SINGOLO_OPTIN=' .env.production"

echo "== [2] build + recreate SOLO backend sotto nohup (l'env entra solo con --force-recreate)"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
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
for u in / /cerca-ritiro /o/anpoche /api/health /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s (invariato, frontend non toccato)\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)"
printf "   interruttore nel container → %s (atteso 1)\n" "$($SSH "docker exec \$(docker ps -qf name=backend | head -1) printenv CERCHIO_SINGOLO_OPTIN")"
printf "   modalita' del subscribe → %s (atteso benvenuto)\n" "$($SSH "docker exec \$(docker ps -qf name=backend | head -1) python -c \"from routers.subscribers import _modalita_risposta; print(_modalita_risposta())\" 2>/dev/null | tail -1")"

echo "== [4] Brevo dal container: riallineo il Cerchio (AURYA_INVIABILE) e verifico (solo API contatti)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python scripts/brevo_segmentazione.py --backfill --verifica 2>&1 | grep -v "bcrypt\|Traceback\|^  File\|version = \|\^\|AttributeError"'
echo "== FATTO. Ora: git tag prod-$GIRO."
