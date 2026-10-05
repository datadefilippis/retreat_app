#!/bin/bash
# GIRO 5/10/2026 — Meta Pixel + Conversions API (MP0-MP4):
#   MP0 provenienza estesa (utm content/term, fbclid/gclid, tracciamento) anche
#       per professionisti e account; META_* nel compose; meta_pixel_id nel site-config
#   MP1 banner cookie a TRE scelte (lib/consenso.js, aurya_consent_v3), link
#       «Preferenze cookie» nel footer, informativa v2.11 (→ gli operatori
#       rivedranno il modal di ri-consenso al prossimo accesso: previsto)
#   MP2 lib/meta.js: fbevents SOLO col consenso marketing, eventi con eventID
#   MP3 services/meta_capi.py: stesso evento dal server, registro tracciamento_eventi
#   MP4 regia: campagna › inserzione negli Iscritti, provenienza negli Operatori,
#       campagne + stato Meta nei numeri del lunedì
# Backend + frontend, NIENTE nginx, nessun flag nuovo: META_PIXEL_ID e
# META_CAPI_TOKEN sono GIA' in .env.production (5/10, root 600, esclusi dal
# rsync). L'env entra nel backend solo con --force-recreate (come sempre).
# PROVA: con META_TEST_EVENT_CODE=<codice> gli eventi compaiono in «Testa gli
# eventi» senza contare nelle campagne; si toglie a prova finita (giro-env).
# Nessuna email parte da questo giro.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-05-meta
SSH="ssh -i $KEY $HOST"
TEST_CODE="${META_TEST_EVENT_CODE:-}"   # facoltativo: META_TEST_EVENT_CODE=TESTxxxx bash deploy/giri/deploy-2026-10-05-meta.sh

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] env di prod: META_PIXEL_ID e META_CAPI_TOKEN devono esserci (mai stampati)"
$SSH "cd /opt/aurya && grep -q '^META_PIXEL_ID=1093685309713150' .env.production && grep -q '^META_CAPI_TOKEN=.\{20,\}' .env.production && echo '   ok: pixel e token presenti' || { echo '   MANCANO META_PIXEL_ID/META_CAPI_TOKEN in .env.production: FERMO'; exit 1; }"
if [ -n "$TEST_CODE" ]; then
  echo "== [0c] modalita' prova: META_TEST_EVENT_CODE in .env.production (idempotente)"
  $SSH "cd /opt/aurya && grep -q '^META_TEST_EVENT_CODE=' .env.production && sed -i 's/^META_TEST_EVENT_CODE=.*/META_TEST_EVENT_CODE=$TEST_CODE/' .env.production || echo 'META_TEST_EVENT_CODE=$TEST_CODE' >> .env.production; grep -c '^META_TEST_EVENT_CODE=' .env.production"
fi

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] build + recreate (frontend, poi backend) sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -1 && echo "== frontend pronto $(date -u +%H:%M:%S)" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
$C up -d --no-deps --force-recreate frontend 2>&1 | tail -1
sleep 5
$C up -d --no-deps --force-recreate backend 2>&1 | tail -1
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "== health ok ($i) $(date -u +%H:%M:%S)"; break; }
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
$SSH "grep -q 'health ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK"; exit 1; }

echo "== [3] verifica"
for u in / /cerca-ritiro /o/anpoche /operatori /accedi /privacy /api/health /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · stesso su /o/anpoche → %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/o/anpoche | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)"
printf "   legale → %s (atteso v2.11)\n" "$(curl -s https://aurya.life/api/legal/versions | grep -o "\"version_tag\":\"[^\"]*\"")"
printf "   site-config meta_pixel_id → %s (atteso 1093685309713150)\n" "$(curl -s https://aurya.life/api/public/site-config | grep -o '"meta_pixel_id":"[0-9]*"')"
printf "   site-config senza token → %s (atteso 0)\n" "$(curl -s https://aurya.life/api/public/site-config | grep -c 'META_CAPI\|EAAL' || true)"
printf "   fbevents nel bundle come stringa → %s (atteso 1: si carica solo al consenso)\n" "$(curl -s https://aurya.life/$JS | grep -o 'connect.facebook.net/en_US/fbevents.js' | wc -l | tr -d ' ')"
printf "   nessuno <script> Meta nell'HTML → %s (atteso 0)\n" "$(curl -s https://aurya.life/ | grep -c 'fbevents\|connect.facebook.net' || true)"
printf "   token nel container → %s\n" "$($SSH "docker exec \$(docker ps -qf name=backend | head -1) python -c \"from services.meta_capi import configurato, test_event_code; print('configurato' if configurato() else 'NON CONFIGURATO', '· prova' if test_event_code() else '· reale')\" 2>/dev/null | tail -1")"
# subscribe col payload di ieri (senza tracciamento) e con quello nuovo senza consenso:
# nessun evento parte (marketing assente/false), risposta identica a prima
printf "   subscribe payload nuovo senza consenso marketing → %s\n" "$(curl -s -X POST https://aurya.life/api/public/newsletter/subscribe -H 'Content-Type: application/json' -d '{"email":"verifica-giro-meta@example.com","consent":true,"language":"it","source":"landing_cerchio","tracciamento":{"marketing":false}}' | cut -c1-80)"
printf "   contatti senza Bearer → %s (atteso 401)\n" "$(curl -s -o /dev/null -w '%{http_code}' 'https://aurya.life/api/public/operator/anpoche/contatti?ev=contact_0123456789abcdef')"
echo "== [3b] pulizia dell'iscritto di verifica (nessuna email: era in attesa da pochi secondi)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python -c "
import asyncio
from database import db
async def m():
    r = await db.aurya_subscribers.delete_many({\"email\": \"verifica-giro-meta@example.com\"})
    print(\"   cancellati\", r.deleted_count)
asyncio.run(m())" 2>/dev/null | tail -1'
echo "== FATTO. Ora: git tag prod-$GIRO. Poi in Gestione eventi → «Testa gli eventi»: un'iscrizione vera dal browser col consenso marketing deve mostrare Lead (browser + server, deduplicati)."
