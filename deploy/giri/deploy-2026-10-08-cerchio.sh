#!/bin/bash
# GIRO 8/10/2026 notte — il CERCHIO negli ascolti con nome ed email (persona
# cerchio:<email> in regia, anonimizzazione alla disiscrizione), INFORMATIVA
# v2.13 (riga 7-quater + art. 8, IT/EN/DE/FR: al prossimo accesso chi aveva
# accettato rivede l'informativa), PREFERITE senza account con la porta unica
# dentro l'invito del cuore, TABLET a 768, POTATURA dei vestiti vecchi di
# Crea e Lab, regia con «Di sempre».
#  Backend: routers/frequencies (subscriber_email sull'evento), services/
#    ascolti_regia (_sessioni_unite, scorda_iscritto), routers/subscribers
#    (3 chiamate _scorda_ascolti), platform_account_service (export/delete
#    anche gli ascolti dal Cerchio), core/legal_versions v2.13. Nessuna chiave
#    nuova, nessuna migrazione.
#  Frontend: Cuore/preferite (porta nell'invito, cuore in attesa), casa.css
#    768, SoundAscoltiSezione (etichetta Cerchio), Crea/Lab senza vestiti vecchi.
#  NGINX: registro rotte INVARIATO → niente force-recreate di nginx.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-08-cerchio
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
    print('   tracce:', await db.frequency_tracks.count_documents({}), '| ascolti:', await db.sound_ascolti.count_documents({}),
          '| con account:', await db.sound_ascolti.count_documents({'account_id': {'\\\$ne': None}}),
          '| dal Cerchio:', await db.sound_ascolti.count_documents({'cerchio': True}),
          '| preferiti:', await db.frequency_favorites.count_documents({}), '| account:', await db.platform_accounts.count_documents({}))
asyncio.run(m())\"" 2>/dev/null | grep -v bcrypt

echo "== [0c] backup delle collezioni toccate"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && for C in sound_ascolti platform_accounts frequency_favorites frequency_tracks aurya_subscribers consent_audit; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive 2>/dev/null; done && ls -la backups/predeploy-'"$GIRO"'* | awk "{print \"   \" \$5, \$9}"'

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

echo "== [3] verifiche (solo codici e JSON: mai grep sul testo della SPA)"
set +e
for u in / /api/health /meditazioni /sound /sound/lab /sound/lab/banco /sound/lab/ritratto /sound/esplora /sound/crea /sound/studio /admin/sound; do printf "   %-20s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
printf "   regia senza token → %s (401/403 atteso)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/admin/sound/ascolti/panoramica)"
printf "   /platform/me senza token → %s (401 atteso)\n" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/platform/me)"
printf "   catalogo anonimo → %s (403 locked atteso)\n" "$(curl -s https://aurya.life/api/frequencies/catalog | head -c 60)"
printf "   informativa v2.13 (7-quater) → %s\n" "$(curl -s 'https://aurya.life/api/legal/privacy?locale=it' | grep -o '7-quater' | head -1)"
printf "   vetrina → %s\n" "$(curl -s https://aurya.life/api/frequencies/public/vetrina | head -c 80)"
printf "   bundle shell → %s | nel container → %s\n" "$(curl -s -A Mozilla https://aurya.life/manifesto | grep -o 'main\.[a-z0-9]*\.js' | head -1)" "$($SSH 'docker exec $(docker ps -qf name=ms-frontend | head -1) ls /usr/share/nginx/html/static/js 2>/dev/null | grep -o "^main\.[a-z0-9]*\.js"' | head -1)"
$SSH 'docker logs $(docker ps -qf name=ms-backend | head -1) 2>&1 | grep -i "ascolti\|conservazione" | tail -2'
$SSH 'docker logs $(docker ps -qf name=ms-backend | head -1) 2>&1 | grep -i "error\|traceback" | grep -v "bcrypt" | tail -3'
echo "== FATTO. Ora: git tag prod-$GIRO e push. Poi dal telefono: /meditazioni (cuore senza account), Regia → Sound → Gli ascolti → Persone."
