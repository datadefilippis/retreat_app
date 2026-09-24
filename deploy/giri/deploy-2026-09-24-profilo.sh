#!/bin/bash
# GIRO 24/9/2026 — onboarding e profilo, giro 1: PE (email coerenti, via g2),
# P1 (persona · marchio), P3 (telefono privato), P2 (bio che presenta),
# DI7 (due discipline chakra). Backend + frontend; nginx invariato; nessuna
# variabile nuova; nessuna migrazione dati (i profili restano com'erano).
# Si lancia DAL MAC dopo il «vai» del founder.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-09-24-profilo
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP, non a 46.224.0.96: FERMO"; exit 1; }

echo "== [1] backup organizations + users (le collezioni toccate dal giro)"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in organizations users; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive; done && ls -la backups/predeploy-'"$GIRO"'*'

echo "== [2] rsync del codice"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -3

echo "== [3] immagini e container (script remoto sotto nohup, log /root/deploy-$GIRO.log)"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -2 && echo "== immagine backend pronta $(date -u +%H:%M:%S)" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -2 && echo "== immagine frontend pronta $(date -u +%H:%M:%S)" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1 && echo "== frontend ricreato $(date -u +%H:%M:%S)" || echo "== FRONTEND FALLITO"
sleep 5
$C up -d --no-deps backend 2>&1 | tail -1 && echo "== backend ricreato $(date -u +%H:%M:%S)" || echo "== BACKEND FALLITO"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "== health backend ok ($i) $(date -u +%H:%M:%S)"; break; }
  sleep 2
done
echo "== FINE $(date -u +%H:%M:%S)"
REMOTO
$SSH "chmod +x /root/deploy-$GIRO.sh && nohup /root/deploy-$GIRO.sh > /root/deploy-$GIRO.log 2>&1 &"
for i in $(seq 1 90); do
  if $SSH "grep -q '== FINE\|FALLITO' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health backend ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [4] verifica sul vivo"
for u in / /accedi /public-profile /operatori /operatori/allineamento-chakra /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   directory (nomi invariati, primi 3): "; curl -s "https://aurya.life/api/public/operators" | python3 -c "import sys,json; d=json.load(sys.stdin); print([i['name'] for i in d.get('items',[])][:3])"
printf "   signup telefono malformato → %s (atteso 422)\n" "$(curl -s -o /dev/null -w '%{http_code}' -X POST https://aurya.life/api/auth/signup -H 'Content-Type: application/json' -d '{"email":"verifica-p3@esempio.invalid","name":"Verifica P3","password":"Password-Lunga-12","accepted_terms":true,"phone":"12"}')"
echo "== [5] sequenze: anteprima del prossimo giro (dry run, nessun invio)"
$SSH 'cd /opt/aurya && docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend python -c "
import asyncio
from services.sequenze import run_sequenze_sweep
r = asyncio.run(run_sequenze_sweep(dry_run=True))
print(\"candidati:\", r[\"candidati\"])"'
echo "== FATTO. Ora: git tag prod-$GIRO, proponi_nome_persona.py in prod, memoria."
