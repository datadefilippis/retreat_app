#!/bin/bash
# GIRO 6/10/2026 (notte) — P0 FONDAMENTA dei prodotti: la commissione la
# decide la riga (prodotti 15% nel Gratis, 0 negli abbonamenti; ritiri e
# servizi 0 per sempre), modulo «prodotti» nel registro + tier + interruttore
# prodotti_spento, patto DPA sui prodotti, volume per i file digitali,
# scheda «Prodotti · In arrivo» negli Strumenti. NIENTE si vende ancora
# (nessuna rotta prodotti: arriva con P1): per chi usa Aurya oggi il
# checkout produce fee 0 identica a ieri (solo ritiri e servizi).
# All'avvio il backend esegue migrate_prodotti_p0_v1 (modulo attivo +
# tier + mappa fee sulle org esistenti; flag-gated, idempotente).
# Il volume nuovo (ms-backend-private-uploads) nasce vuoto: in prod non
# c'e' ancora nessun file digitale.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-06-prodotti-p0
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] prima: org con piano retreat_*, fee per org, file privati nel container"
$SSH "$PY -c \"
import asyncio
from database import organizations_collection, organization_modules_collection
async def m():
    n = await organizations_collection.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    f = await organizations_collection.count_documents({'application_fee_percent': {'\\\$gt': 0}})
    p = await organization_modules_collection.count_documents({'module_key': 'prodotti'})
    print('   org retreat_*:', n, '| org con fee % > 0:', f, '| righe modulo prodotti:', p)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt
$SSH 'docker exec $(docker ps -qf name=backend | head -1) sh -c "ls -la /app/private_uploads 2>/dev/null | head -5 || echo \"   nessuna cartella private_uploads nel container\""'

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] build backend+frontend, recreate frontend poi backend (volume nuovo), sotto nohup"
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

echo "== [3] la migrazione d'avvio nel log del backend"
$SSH 'docker logs $(docker ps -qf name=backend | head -1) 2>&1 | grep -i "migrate_prodotti_p0_v1\|Seeded.*commercial\|prodotti" | tail -6'

echo "== [4] dopo: piani con la mappa, org con la mappa e il modulo, volume"
$SSH "$PY -c \"
import asyncio
from database import db, organizations_collection, organization_modules_collection
async def m():
    async for p in db['commercial_plans'].find({'slug': {'\\\$regex': '^retreat_'}}, {'_id':0,'slug':1,'transaction_fee_by_type':1,'transaction_fee_percent':1,'module_plans.prodotti':1}):
        print('   piano', p['slug'], '| per tipo', p.get('transaction_fee_by_type'), '| % storica', p.get('transaction_fee_percent'), '| tier prodotti', (p.get('module_plans') or {}).get('prodotti'))
    n = await organizations_collection.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    con = await organizations_collection.count_documents({'application_fee_by_type': {'\\\$exists': True}})
    g15 = await organizations_collection.count_documents({'application_fee_by_type.physical': 15})
    f = await organizations_collection.count_documents({'application_fee_percent': {'\\\$gt': 0}})
    mod = await organization_modules_collection.count_documents({'module_key': 'prodotti', 'is_active': True})
    sub = await db['module_subscriptions'].count_documents({'module_key': 'prodotti', 'status': 'active'})
    print('   org retreat_*:', n, '| con mappa:', con, '| a 15%:', g15, '| fee % storica > 0:', f, '| modulo prodotti attivo:', mod, '| abbonamenti modulo:', sub)
    mig = await db['migrations'].find_one({'_id': 'prodotti_p0_v1'}, {'_id':0})
    print('   migrazione:', mig)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt
$SSH 'docker volume ls | grep private-uploads; docker exec $(docker ps -qf name=backend | head -1) sh -c "ls -ld /app/private_uploads"'
for u in / /esperienze /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal gestionale: Strumenti → la scheda «Prodotti · In arrivo»."
