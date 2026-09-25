#!/bin/bash
# GIRO 25/9/2026 — un'email, un account: normalizzazione in minuscolo
# (modelli + ricerca), script per il pregresso, e risoluzione del doppione
# vero di prod (spaziomarilisa: si tiene il PRIMO account, delle 08:55 del
# 24/9, quello su cui ha anche riaccettato i termini alle 16:16; si
# elimina il secondo, vuoto, delle 16:18). Solo backend. Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-09-25-email
SSH="ssh -i $KEY $HOST"
C='docker compose -f docker-compose.prod.yml --env-file .env.production'
ORG_DOPPIA=2f0084b9-a642-41ec-82cf-013a9e76d68b     # Cazzaniga #2 (16:18), utente b4a09b35 «Spaziomarilisa@gmail.com»
ORG_BUONA=9af9a015-1e68-4e13-b058-ffb71ae22be6      # Cazzaniga #1 (08:55), utente a9a72e47 «spaziomarilisa@gmail.com»

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [1] backup users + organizations"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && for C in users organizations; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive; done && ls backups/predeploy-'"$GIRO"'* | wc -l'

echo "== [2] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [3] build + recreate del solo backend"
$SSH "cd /opt/aurya && $C build backend 2>&1 | tail -1 && $C up -d --no-deps backend 2>&1 | tail -1"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health || true)
  [ "$code" = "200" ] && { echo "   health ok ($i)"; break; }
  sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/health)" = "200" ] || { echo "HEALTH NON OK"; exit 1; }

echo "== [4] il doppione: controllo che il secondo account sia davvero vuoto, poi lo elimino (cascade)"
$SSH "cd /opt/aurya && $C exec -T backend python - <<'EOF' 2>&1 | grep -v 'bcrypt\|__about__\|Traceback\|File \|version = \|\^\^'
import asyncio
from database import db
ORG_DOPPIA='$ORG_DOPPIA'; ORG_BUONA='$ORG_BUONA'
async def go():
    o = await db.organizations.find_one({'id': ORG_DOPPIA}, {'_id':0,'name':1,'public_slug':1,'public_profile.bio':1})
    u = await db.users.find_one({'organization_id': ORG_DOPPIA}, {'_id':0,'email':1,'last_login_at':1})
    b = await db.users.find_one({'organization_id': ORG_BUONA}, {'_id':0,'email':1})
    n_prod = await db.products.count_documents({'organization_id': ORG_DOPPIA})
    n_ord = await db.orders.count_documents({'organization_id': ORG_DOPPIA})
    n_store = await db.stores.count_documents({'organization_id': ORG_DOPPIA})
    print('doppio:', o, '| utente:', u, '| prodotti', n_prod, 'ordini', n_ord, 'store', n_store)
    print('buono resta:', b)
    ok = (o and o.get('name') == 'Cazzaniga' and not o.get('public_slug') and not (o.get('public_profile') or {}).get('bio')
          and u and u['email'] == 'Spaziomarilisa@gmail.com' and n_prod == 0 and n_ord == 0
          and b and b['email'] == 'spaziomarilisa@gmail.com')
    if not ok:
        print('CONDIZIONI NON RISPETTATE: non elimino nulla'); return
    # il telefono, l'unico dato in piu' del secondo account, passa al primo (solo se il primo non ce l'ha)
    pp2 = (await db.organizations.find_one({'id': ORG_DOPPIA}, {'_id':0,'public_profile.public_phone':1}) or {}).get('public_profile') or {}
    tel = pp2.get('public_phone')
    if tel:
        r_tel = await db.organizations.update_one({'id': ORG_BUONA, 'public_profile.public_phone': {'\$in': [None, '']}}, {'\$set': {'public_profile.public_phone': tel}})
        print('telefono copiato sul primo account:', tel, '| scritto:', r_tel.modified_count == 1)
        dopo = await db.organizations.find_one({'id': ORG_BUONA}, {'_id':0,'public_profile.public_phone':1})
        if ((dopo or {}).get('public_profile') or {}).get('public_phone') != tel:
            print('TELEFONO NON COPIATO: non elimino nulla'); return
    from services.hard_delete_service import cascade_hard_delete
    r = await cascade_hard_delete(ORG_DOPPIA)
    print('eliminato:', {k: v for k, v in r.items() if v})
    print('utenti rimasti con quella email:', await db.users.count_documents({'email': {'\$regex': '^spaziomarilisa@', '\$options': 'i'}}))
asyncio.run(go())
EOF"

echo "== [5] normalizzazione email pregresso: prova, poi vera"
$SSH "cd /opt/aurya && $C exec -T backend python scripts/normalizza_email_utenti.py --prova 2>&1 | grep -v 'bcrypt\|__about__\|Traceback\|File \|version = \|\^\^'"
$SSH "cd /opt/aurya && $C exec -T backend python scripts/normalizza_email_utenti.py 2>&1 | grep -v 'bcrypt\|__about__\|Traceback\|File \|version = \|\^\^' | tail -1"

echo "== [6] verifica"
for u in / /accedi /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
echo "== FATTO. Ora: git tag prod-$GIRO."
