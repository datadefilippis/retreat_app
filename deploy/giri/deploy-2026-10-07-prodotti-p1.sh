#!/bin/bash
# GIRO 7/10/2026 — P0 + P1 + P2 PRODOTTI, insieme (nessuno e' mai andato in prod):
#  P0  la commissione la decide la riga (prodotti 15% Gratis / 0 abbonati,
#      ritiri e servizi 0 sempre), modulo «prodotti» + tier + interruttore
#      prodotti_spento, patto DPA sui prodotti, VOLUME per i file digitali,
#      migrazione d'avvio migrate_prodotti_p0_v1 (modulo + tier + mappa fee
#      sulle org esistenti).
#  P1  prodotti DIGITALI: API /prodotti, wizard in tre gesti, scheda,
#      sezione «Prodotti» sul profilo con acquisto in pagina (account Aurya
#      obbligatorio), «I miei file» in /account, limite file per piano.
#  P2  prodotti FISICI: wizard in tre gesti (cos'e', come arriva, pubblica),
#      consegna dell'org (ritiro di persona / spedizione a costo fisso) via
#      store settings + opzione «Spedizione»; magazzino, indirizzo e stati
#      di evasione gia' nel gestionale; commissione in chiaro in /prodotti.
#  CONS consolidamento pre-live: verifica immediata del pagamento dalla
#      pagina di successo (+ lucchetto e riconciliazione idempotente), email
#      «Nuovo ordine pagato» con i contatti, email cliente per tipo, hint
#      «Il tuo file e' pronto», contatti nella lista Ordini.
#  DP   design del modulo + LA PAGINA DEL PRODOTTO /prodotto/{org}/{slug}
#      (endpoint pubblico dal public_slug, meta per i bot, rotta nel registro,
#      sitemap), profilo con «Scopri di più» + «Compra», kit del gestionale.
#  GL   galleria di foto per prodotto (API /prodotti/{id}/foto), landing che
#      sfoglia, card del profilo della misura dei ritiri.
#  ANTEPRIMA: in prod i Prodotti restano «In arrivo» (stato.js
#      PRODOTTI_UI_PRONTA=false): scheda oscurata in Strumenti, /prodotti
#      chiuso; aperti solo al pilota admin@demo.com. Sblocco = un giro frontend.
#  NEWSLETTER seconda via: nome+email, ritiri facoltativi (stessi campi di
#      /cerca-ritiro), landing col testo del founder.
#  TESTI + LEGALE v2.12: /costi, landing, piani, Termini ×4 (commissione
#      SOLO sui prodotti, nella misura pubblicata su /costi: i numeri vivono
#      solo li'). Il bump innesca il re-consent degli operatori (un clic).
# Backend + frontend + NGINX (le rotte /prodotti nel registro → nginx.conf
# rigenerato: force-recreate di nginx-proxy dopo il test della conf).
# NESSUNA scrittura sui dati oltre la
# migrazione d'avvio (flag-gated, idempotente). Nessuna email parte.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-07-prodotti-p1
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] prima: org retreat_*, fee % > 0, righe modulo prodotti, versione legale servita"
$SSH "$PY -c \"
import asyncio
from database import organizations_collection, organization_modules_collection
from core.legal_versions import CURRENT_VERSION_TAG
async def m():
    n = await organizations_collection.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    f = await organizations_collection.count_documents({'application_fee_percent': {'\\\$gt': 0}})
    p = await organization_modules_collection.count_documents({'module_key': 'prodotti'})
    print('   org retreat_*:', n, '| fee % > 0:', f, '| righe modulo prodotti:', p, '| legale in prod:', CURRENT_VERSION_TAG)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [0c] backup delle collezioni che il giro tocca (migrazione + re-consent legale)"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in organizations users organization_modules module_subscriptions commercial_plans; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive; done && ls -la backups/predeploy-'"$GIRO"'* | awk "{print \"   \" \$5, \$9}"'

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

echo "== [2b] nginx: test della conf nuova nel container vivo, poi force-recreate (rotte /prodotti)"
$SSH 'cd /opt/aurya && docker exec $(docker ps -qf name=nginx-proxy | head -1) nginx -t 2>&1 | tail -1 && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate nginx-proxy 2>&1 | tail -1'
for i in $(seq 1 20); do code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health || true); [ "$code" = "200" ] && { echo "   health dopo nginx ok ($i)"; break; }; sleep 2; done
printf "   /prodotti (shell app, senza login) → %s\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/prodotti)"

echo "== [3] la migrazione d'avvio e il seed nel log del backend"
$SSH 'docker logs $(docker ps -qf name=backend | head -1) 2>&1 | grep -i "migrate_prodotti_p0_v1\|pricing plans for module .prodotti\|Seeded.*commercial" | tail -5'

echo "== [4] dopo: piani, org, modulo, volume, legale, rotte"
$SSH "$PY -c \"
import asyncio
from database import db, organizations_collection, organization_modules_collection
from core.legal_versions import CURRENT_VERSION_TAG, CURRENT_VERSION_HASH
async def m():
    async for p in db['commercial_plans'].find({'slug': {'\\\$regex': '^retreat_'}}, {'_id':0,'slug':1,'transaction_fee_by_type':1,'module_plans.prodotti':1}):
        print('   piano', p['slug'], '| per tipo', p.get('transaction_fee_by_type'), '| tier', (p.get('module_plans') or {}).get('prodotti'))
    n = await organizations_collection.count_documents({'commercial_plan_slug': {'\\\$regex': '^retreat_'}})
    con = await organizations_collection.count_documents({'application_fee_by_type': {'\\\$exists': True}})
    g15 = await organizations_collection.count_documents({'application_fee_by_type.physical': 15})
    mod = await organization_modules_collection.count_documents({'module_key': 'prodotti', 'is_active': True})
    sub = await db['module_subscriptions'].count_documents({'module_key': 'prodotti', 'status': 'active'})
    print('   org:', n, '| con mappa:', con, '| a 15%:', g15, '| modulo attivo:', mod, '| abbonamenti modulo:', sub)
    print('   migrazione:', await db['migrations'].find_one({'_id': 'prodotti_p0_v1'}, {'_id':0}))
    print('   legale:', CURRENT_VERSION_TAG, CURRENT_VERSION_HASH)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt
$SSH 'docker volume ls | grep private-uploads; docker exec $(docker ps -qf name=backend | head -1) sh -c "ls -ld /app/private_uploads && touch /app/private_uploads/.volume-ok && echo \"   volume scrivibile\""'
for u in / /costi /esperienze /api/health /api/legal/terms; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   /api/prodotti senza login → %s (atteso 401/403)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/prodotti)"
printf "   /api/platform/me/file senza login → %s\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/platform/me/file)"
printf "   /prodotto/x/y (shell, slug ignoto) → %s (atteso 200 shell o 404)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/prodotto/x/y)"
printf "   /api/public/prodotto/x/y → %s (atteso 404)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/public/prodotto/x/y)"
printf "   /newsletter → %s\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/newsletter)"
curl -s https://aurya.life/newsletter | grep -o "Vorrei ricevere anche ritiri" | head -1 | sed 's/^/   seconda via: /'
curl -s 'https://aurya.life/api/legal/terms?locale=it' | grep -o "esclusivamente ai Prodotti" | head -1 | sed 's/^/   termini in prod: /'
curl -s https://aurya.life/costi | grep -o "senza commissioni su ritiri e servizi" | head -1 | sed 's/^/   \/costi (shell): /'
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser: /costi, Strumenti → Prodotti, il wizard digitale, il profilo con «Compra»."
