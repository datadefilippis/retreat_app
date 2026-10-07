#!/bin/bash
# GIRO 7/10/2026 — HOME con tre schede + AC0 fondamenta Accademia (anteprima).
#  HOME  la scheda «Esperienze» torna dopo «Professionisti» con la porta a
#        /esperienze; tre schede sulla stessa riga da desktop.
#  AC0   modulo `accademia` nel registro (tier accademia_retreat_free/_pro,
#        interruttore accademia_spento, patto DPA + course), fee per riga
#        con la chiave `course` (15 Gratis / 0 abbonati: usata solo da righe
#        di tipo course, in prod nessuna), migrazione d'avvio
#        migrate_accademia_a0_v1 (modulo + tier + SOLO la chiave course
#        nella mappa fee di ogni org), iscrizioni sull'account Aurya
#        (campi additivi), scheda Strumenti «Accademia · In arrivo».
#  Nessuna rotta nuova (nginx invariato). Nessuna email parte.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-07-home-ac0
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=ms-backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] prima: org, mappa fee con course, modulo accademia"
$SSH "$PY -c \"
import asyncio
from database import db
async def m():
    n = await db.organizations.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    c = await db.organizations.count_documents({'application_fee_by_type.course': {'\\\$exists': True}})
    a = await db.organization_modules.count_documents({'module_key': 'accademia'})
    print('   org retreat_*:', n, '| con course nella mappa:', c, '| righe modulo accademia:', a)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [0c] backup delle collezioni che la migrazione tocca"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in organizations organization_modules module_subscriptions commercial_plans; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive 2>/dev/null; done && ls -la backups/predeploy-'"$GIRO"'* | awk "{print \"   \" \$5, \$9}"'

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='backend/private_uploads' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] build backend+frontend, recreate frontend poi backend, sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C config -q && echo "== compose valido" || { echo "== COMPOSE NON VALIDO"; exit 1; }
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -1 && echo "== frontend pronto" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1
$C up -d --no-deps --force-recreate backend 2>&1 | tail -1
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "== health ok ($i) $(date -u +%H:%M:%S)"; break; }
  sleep 2
done
echo "== FINE $(date -u +%H:%M:%S)"
REMOTO
$SSH "chmod +x /root/deploy-$GIRO.sh && nohup /root/deploy-$GIRO.sh > /root/deploy-$GIRO.log 2>&1 &"
for i in $(seq 1 160); do
  if $SSH "grep -q '== FINE\|FALLITO\|NON VALIDO' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [3] la migrazione nel log del backend"
$SSH 'docker logs $(docker ps -qf name=ms-backend | head -1) 2>&1 | grep -i "migrate_accademia_a0_v1\|pricing plans for module .accademia" | tail -4'

echo "== [4] dopo: modulo, tier, mappa, pagine"
$SSH "$PY -c \"
import asyncio
from database import db
async def m():
    n = await db.organizations.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    c = await db.organizations.count_documents({'application_fee_by_type.course': {'\\\$exists': True}})
    c15 = await db.organizations.count_documents({'application_fee_by_type.course': 15})
    ph = await db.organizations.count_documents({'application_fee_by_type.physical': 15})
    mod = await db.organization_modules.count_documents({'module_key': 'accademia', 'is_active': True})
    sub = await db.module_subscriptions.count_documents({'module_key': 'accademia', 'status': 'active'})
    async for p in db['commercial_plans'].find({'slug': {'\\\$in': ['retreat_free','retreat_pro']}}, {'_id':0,'slug':1,'transaction_fee_by_type':1,'module_plans.accademia':1}):
        print('   piano', p['slug'], p.get('transaction_fee_by_type'), (p.get('module_plans') or {}).get('accademia'))
    print('   org:', n, '| course nella mappa:', c, '| a 15:', c15, '| physical ancora a 15:', ph, '| modulo attivo:', mod, '| abbonamenti:', sub)
    print('   migrazione:', await db['migrations'].find_one({'_id': 'accademia_a0_v1'}, {'_id':0}))
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt
for u in / /esperienze /operatori /blog /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser: la home con le tre schede, Strumenti con «Accademia · In arrivo»."
