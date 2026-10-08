#!/bin/bash
# GIRO 8/10/2026 — ACCADEMIA in ANTEPRIMA (AC1 operatore, AC2 studente, AC3
# pubblico, AC4 regia, RF refinement, AU audio/suono/allegati) + MANIFESTO MF3
# + account hub con barra + scroll al cambio pagina.
#  Backend: /api/accademia (Bunny gestito: la chiave e' gia' in .env.production,
#    il backend va RICREATO per leggerla), /api/platform/me/corsi, /api/public/
#    corso|corsi, webhook Bunny, regia Strumenti + kill switch, lezioni audio su
#    volume privato, CORS X-Aurya-Account. Nessuna migrazione d'avvio nuova.
#  Frontend: UI chiusa ai non piloti (ACCADEMIA_UI_PRONTA=false), landing
#    /corso, directory /corsi (vuota in prod → noindex), profilo a schede,
#    account hub + barra, Manifesto nuovo, legacy /co /courses /account/courses
#    rimandati.
#  NGINX: registro rotte cambiato (corsi, corso, rimandi co/courses) →
#    nginx -t sulla conf nuova, poi force-recreate di nginx-proxy.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-08-accademia
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=ms-backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0a] la chiave Bunny e' in prod? (solo i nomi)"
$SSH 'cd /opt/aurya && grep -cE "^BUNNY_ACCOUNT_API_KEY=.+" .env.production && grep -cE "^BUNNY_WEBHOOK_BASE_URL=https://aurya.life" .env.production' | tr '\n' ' '; echo

echo "== [0b] prima"
$SSH "$PY -c \"
import asyncio
from database import db
async def m():
    print('   corsi:', await db.courses.count_documents({}), '| prodotti course:', await db.products.count_documents({'item_type':'course'}),
          '| iscrizioni:', await db.issued_course_accesses.count_documents({}), '| org:', await db.organizations.count_documents({}))
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [0c] backup delle collezioni toccate"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in organizations courses products issued_course_accesses orders; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive 2>/dev/null; done && ls -la backups/predeploy-'"$GIRO"'* | awk "{print \"   \" \$5, \$9}"'

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

echo "== [2b] nginx: test della conf nuova nel container vivo, poi force-recreate (rotte corsi/corso, rimandi co/courses)"
$SSH 'cd /opt/aurya && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate nginx-proxy 2>&1 | tail -1 && sleep 3 && docker exec ms-nginx nginx -t 2>&1 | tail -1'
for i in $(seq 1 20); do code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health || true); [ "$code" = "200" ] && { echo "   health dopo nginx ok ($i)"; break; }; sleep 2; done

echo "== [3] verifiche (solo codici e JSON: mai grep sul testo della SPA)"
set +e
for u in / /api/health /corsi /accademia /account /manifesto /esperienze /operatori; do printf "   %-14s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   /corso (radice) → %s (404 atteso: solo con slug)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/corso)"
printf "   /co/x/y → %s %s\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/co/x/y)" "$(curl -s -o /dev/null -w '%{redirect_url}' https://aurya.life/co/x/y)"
printf "   /courses → %s %s\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/courses)" "$(curl -s -o /dev/null -w '%{redirect_url}' https://aurya.life/courses)"
printf "   /api/public/corsi → %s\n" "$(curl -s https://aurya.life/api/public/corsi | head -c 80)"
printf "   shell /corsi → %s\n" "$(curl -s -A Googlebot https://aurya.life/corsi | grep -o 'name=\"robots\"[^>]*' | head -1)"
printf "   shell /manifesto → %s\n" "$(curl -s -A Googlebot https://aurya.life/manifesto | grep -o '<title>[^<]*</title>' | head -1)"
printf "   accademia senza token → %s (401 atteso)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/accademia)"
printf "   webhook bunny vuoto → %s (400 atteso)\n" "$(curl -s -o /dev/null -w '%{http_code}' -X POST https://aurya.life/api/webhooks/bunny -H 'Content-Type: application/json' -d '{}')"
$SSH 'docker logs $(docker ps -qf name=ms-backend | head -1) 2>&1 | grep -i "error\|traceback" | grep -v "bcrypt" | tail -3'
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser: /manifesto, /account (barra), /corsi (vuota, «I primi corsi stanno arrivando»), Strumenti col pilota."
