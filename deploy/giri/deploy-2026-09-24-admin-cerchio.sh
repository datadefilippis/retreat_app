#!/bin/bash
# GIRO 24/9/2026 sera — regia operatori + Cerchio (lotti A-E), legale v2.7,
# login senza verifica (interruttore SPENTO), opt-in singolo (interruttore
# SPENTO), pagina link «Un solo link per tutto», onboarding giro 1 (PE, P1,
# P3, P2, DI7-9). Backend + frontend; nginx invariato; nessuna variabile
# nuova richiesta (i due interruttori restano spenti finche' il founder non
# li accende in .env.production); DUE migrazioni dati additive sugli
# iscritti (provenienza, consenso), prima in --prova poi vere.
# Prova generale fatta sulla copia di prod (24/9 12:30). Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-09-24-admin-cerchio
SSH="ssh -i $KEY $HOST"
C='docker compose -f docker-compose.prod.yml --env-file .env.production'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP, non a 46.224.0.96: FERMO"; exit 1; }

echo "== [1] backup delle collezioni toccate (+ dump intero gia' fatto alle 12:29: /root/prod-copia-2026-09-24.archive.gz)"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in organizations users aurya_subscribers prelaunch_leads consent_audit audit_logs stores products; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive; done && ls -la backups/predeploy-'"$GIRO"'* | wc -l'

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
# prima il frontend, POI il backend (la cache dell'index shell vive nel backend: lezione del 10/9)
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
for i in $(seq 1 100); do
  if $SSH "grep -q '== FINE\|FALLITO' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health backend ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [4] sequenze: i passi «profilo_online» maturati PRIMA di oggi si segnano come saltati (niente «la tua pagina e' online» a chi ce l'ha da settimane)"
$SSH "cd /opt/aurya && $C exec -T backend python -c \"
import asyncio
from datetime import datetime, timezone
from database import db
from services.sequenze import run_sequenze_sweep
async def go():
    r = await run_sequenze_sweep(dry_run=True)
    cand = [c for c in r.get('candidati', []) if c[0] == 'operatore' and c[2] == 'profilo_online']
    now = datetime.now(timezone.utc).isoformat()
    for _, org_id, passo in cand:
        await db.organizations.update_one({'id': org_id, 'sequenza.' + passo: {'\\\$exists': False}},
                                          {'\\\$set': {'sequenza.' + passo: 'saltato ' + now + ' (deploy 24/9: pagina gia online prima del passo)'}})
    r2 = await run_sequenze_sweep(dry_run=True)
    print('profilo_online segnati come saltati:', len(cand), '| candidati residui:', r2.get('candidati'))
asyncio.run(go())
\""

echo "== [5] migrazioni additive sugli iscritti: prima in prova, poi vere"
$SSH "cd /opt/aurya && $C exec -T backend python scripts/migra_provenienza.py --prova | tail -4 && $C exec -T backend python scripts/migra_provenienza.py | tail -2 && $C exec -T backend python scripts/migra_consenso_cerchio.py --prova | tail -6 && $C exec -T backend python scripts/migra_consenso_cerchio.py | tail -2"

echo "== [6] verifica sul vivo"
for u in / /accedi /public-profile /operatori /newsletter /cerca-ritiro /meditazioni /admin/operatori /admin/cerchio /api/health /privacy; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   legale servito → %s (atteso v2.7)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o 'v2\.[0-9]' | sort -u | tail -1)"
printf "   directory (nomi, primi 3): "; curl -s "https://aurya.life/api/public/operators?preview=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print([i['name'] for i in d.get('items',[])][:3])"
printf "   admin senza token → %s (atteso 401/403)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/admin/subscribers)"
printf "   v-link rotto → %s (atteso 302 verso /newsletter)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/public/newsletter/v/token-rotto)"
printf "   entra rotto → %s (atteso 302)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/public/newsletter/entra/token-rotto)"
printf "   signup telefono malformato → %s (atteso 422)\n" "$(curl -s -o /dev/null -w '%{http_code}' -X POST https://aurya.life/api/auth/signup -H 'Content-Type: application/json' -d '{"email":"verifica-p3@esempio.invalid","name":"Verifica P3","password":"Password-Lunga-12","accepted_terms":true,"phone":"12"}')"
echo "== [7] sequenze: anteprima del prossimo giro (dry run, nessun invio)"
$SSH "cd /opt/aurya && $C exec -T backend python -c \"
import asyncio
from services.sequenze import run_sequenze_sweep
r = asyncio.run(run_sequenze_sweep(dry_run=True))
print('candidati:', r['candidati'])\""
echo "== FATTO. Ora: git tag prod-$GIRO, stats Cerchio dall'admin, memoria. Interruttori LOGIN_SENZA_VERIFICA e CERCHIO_SINGOLO_OPTIN restano SPENTI."
