#!/bin/bash
# GIRO 8/10/2026 sera — AURYA SOUND: la casa delle meditazioni (SN0-SN4), il
# refinement (MR1-MR7), Esplora nuova (ES), Crea nuova (CR0-CR6), landing
# /sound e /sound/studio, foglio «Il suono».
#  Backend: playlist (/api/frequencies/playlists), categorie dalla regia
#    (/api/admin/sound/categorie, /api/frequencies/categorie), vetrina del
#    giorno (/public/vetrina), favoriti con playlist, ascolti (/platform/me/
#    sound/*), Più SPENTO (SOUND_PIU_ATTIVO assente = 404), annunci al Cerchio
#    SPENTI (SOUND_ANNUNCI_ATTIVI assente = 404), copertine quadrate, shell SEO
#    (meditazioni, playlist, calm/ground/respiro → noindex con rimando,
#    libreria noindex), sitemap. Indici nuovi all'avvio (sound_playlists,
#    sound_ascolti). Nessuna chiave nuova in .env.production.
#  Frontend: /meditazioni = la casa (lettore in casa, playlist, cuori,
#    categorie), /sound/esplora + /sound/impara pagine proprie, Crea col
#    vestito nuovo (?vestito=vecchio = prima), /sound/libreria per chi compone.
#  NGINX: registro rotte cambiato (rimandi sound/calm|ground|respiro →
#    /meditazioni) → nginx -t sulla conf nuova, poi force-recreate.
#  DOPO: i due script (seme delle categorie, copertine quadrate) nel backend.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-08-sound
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=ms-backend | head -1) python'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] prima"
$SSH "$PY -c \"
import asyncio
from database import db
async def m():
    print('   tracce:', await db.frequency_tracks.count_documents({}), '| pubblicate:', await db.frequency_tracks.count_documents({'status':'published'}),
          '| playlist:', await db.sound_playlists.count_documents({}), '| categorie:', await db.sound_categorie.count_documents({}),
          '| iscritti:', await db.aurya_subscribers.count_documents({}), '| favoriti:', await db.frequency_favorites.count_documents({}))
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [0c] backup delle collezioni toccate"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in frequency_tracks sound_playlists sound_categorie frequency_favorites aurya_subscribers platform_accounts; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive 2>/dev/null; done && ls -la backups/predeploy-'"$GIRO"'* | awk "{print \"   \" \$5, \$9}"'

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
set -o pipefail
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

echo "== [2b] nginx: force-recreate (rimandi calm/ground/respiro) + nginx -t nel container vivo"
$SSH 'cd /opt/aurya && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps --force-recreate nginx-proxy 2>&1 | tail -1 && sleep 3 && docker exec ms-nginx nginx -t 2>&1 | tail -1'
for i in $(seq 1 20); do code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health || true); [ "$code" = "200" ] && { echo "   health dopo nginx ok ($i)"; break; }; sleep 2; done

echo "== [2c] gli script del lotto nel backend: seme delle categorie, copertine quadrate"
$SSH "$PY scripts/categorie_sound_seme.py --applica" 2>&1 | grep -v bcrypt | tail -4
$SSH "$PY scripts/copertine_sound_quadrate.py --applica" 2>&1 | grep -v bcrypt | tail -6

echo "== [3] verifiche (solo codici e JSON: mai grep sul testo della SPA)"
set +e
for u in / /api/health /meditazioni /sound /sound/esplora /sound/impara /sound/lab /sound/studio /sound/crea /sound/libreria /sound/esplora/delta /accedi; do printf "   %-22s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
for u in /sound/calm /sound/ground /sound/respiro; do printf "   %-22s → %s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)" "$(curl -s -o /dev/null -w '%{redirect_url}' https://aurya.life$u)"; done
printf "   catalogo anonimo → %s (403 locked atteso)\n" "$(curl -s https://aurya.life/api/frequencies/catalog | head -c 60)"
printf "   vetrina → %s\n" "$(curl -s https://aurya.life/api/frequencies/public/vetrina | head -c 80)"
printf "   piu (spento) → %s (404 atteso)\n" "$(curl -s -o /dev/null -w '%{http_code}' -X POST https://aurya.life/api/platform/me/piu/checkout)"
printf "   shell /meditazioni → %s\n" "$(curl -s -A Googlebot https://aurya.life/meditazioni | grep -o '<title>[^<]*</title>' | head -1)"
printf "   shell /sound/libreria → %s\n" "$(curl -s -A Googlebot https://aurya.life/sound/libreria | grep -o 'name=\"robots\"[^>]*' | head -1)"
printf "   shell /sound/calm → %s\n" "$(curl -s -A Googlebot https://aurya.life/sound/calm | grep -o 'name=\"robots\"[^>]*' | head -1)"
printf "   sitemap: calm fuori? → %s righe con calm (0 atteso)\n" "$(curl -s https://aurya.life/api/public/sitemap-core.xml | grep -c 'sound/calm')"
printf "   bundle shell → %s | nel container → %s\n" "$(curl -s -A Mozilla https://aurya.life/manifesto | grep -o 'main\.[a-z0-9]*\.js' | head -1)" "$($SSH 'docker exec $(docker ps -qf name=ms-frontend | head -1) ls /usr/share/nginx/html/static/js 2>/dev/null | grep -o "^main\.[a-z0-9]*\.js"' | head -1)"
$SSH 'docker logs $(docker ps -qf name=ms-backend | head -1) 2>&1 | grep -i "error\|traceback" | grep -v "bcrypt" | tail -3'
echo "== FATTO. Ora: git tag prod-$GIRO e push. Poi dal telefono: /meditazioni, /sound/esplora, Crea."
