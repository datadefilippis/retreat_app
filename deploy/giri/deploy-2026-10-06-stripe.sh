#!/bin/bash
# GIRO 6/10/2026 (sera) — Lotto S: il paese dell'account Stripe Express.
# La piattaforma e' svizzera e Account.create non passava `country`: ogni
# Express nasceva CH (3 in prod, 0 completati). Da oggi: paese scelto nel
# riquadro «Collega gli incassi» (Italia preselezionata) → country +
# default_currency alla creazione, TWINT solo CH; «Ricomincia col paese
# giusto» per gli account mai completati; il paese vero arriva da Stripe
# in complete e webhook. Backend + frontend. Nessun flag, nessun nginx,
# nessuna email, NESSUNA scrittura sui dati: i 3 account svizzeri restano
# finche' i loro operatori non ricominciano dalla card (o noi su richiesta).
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-06-stripe
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] stato dei 3 account Express in prod (prima)"
$SSH "$PY -c \"
import asyncio
from database import payment_connections_collection
async def m():
    async for c in payment_connections_collection.find({'provider':'stripe','archived':{'\\\$ne':True}}, {'_id':0,'organization_id':1,'external_account_id':1,'runtime_status':1,'details_submitted':1,'charges_enabled':1,'country':1}):
        print('  ', c)
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] build backend+frontend, recreate frontend poi backend, sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
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
  if $SSH "grep -q '== FINE\|FALLITO' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [3] verifica dal container: la piattaforma e i paesi veri dei 3 account (lettura, nessuna scrittura)"
$SSH "$PY -c \"
import asyncio, os, stripe
from database import payment_connections_collection
from services.stripe_connect_express import PAESI_STRIPE, paese_suggerito
stripe.api_key = os.environ['STRIPE_SECRET_KEY']
print('   paesi ammessi:', PAESI_STRIPE)
async def m():
    async for c in payment_connections_collection.find({'provider':'stripe','archived':{'\\\$ne':True}}, {'_id':0,'organization_id':1,'external_account_id':1,'details_submitted':1,'charges_enabled':1}):
        try:
            a = stripe.Account.retrieve(c['external_account_id'])
            print('  ', c['external_account_id'][:14], 'paese', a.country, a.default_currency, '| details', a.details_submitted, '| charges', a.charges_enabled, '| ricominciabile:', not a.details_submitted and not a.charges_enabled)
        except Exception as e:
            print('  ', c['external_account_id'][:14], 'ERRORE', str(e)[:80])
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt
for u in / /settings /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   /api/payment-connections/stripe/express/paesi senza login → %s (atteso 401)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/payment-connections/stripe/express/paesi)"
JS=$(curl -s https://aurya.life/settings | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · pc-paese-select nel bundle: %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/$JS | grep -c 'pc-paese-select')"
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser (login operatore): Impostazioni → Pagamenti, il select del paese prima di «Collega gli incassi con Stripe»."
