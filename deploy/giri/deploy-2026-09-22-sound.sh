#!/bin/bash
# GIRO 22/9/2026 — Aurya Sound: spazio (F2/F2b), 90 minuti (F4/F4b), guida
# del respiro (F1), libreria +74 (23 estasi + 10 respiro + 41 Pixabay).
# Si lancia DAL MAC, dopo il «vai» del founder. Non tocca nginx (rotte
# invariate), non tocca .env.production (nessuna variabile nuova).
#
# Ordine (lezioni 10/9 e 14/9): backup → rsync → immagini → frontend
# ricreato → backend ricreato DOPO → health → pacchetto libreria nel
# volume → verifica → tag.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
PACCHETTO=$HOME/Desktop/pacchetto_libreria_2026-09-22
GIRO=2026-09-22-sound
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP, non a 46.224.0.96: FERMO"; exit 1; }
[ -f "$PACCHETTO/documenti.json" ] || { echo "manca il pacchetto $PACCHETTO"; exit 1; }

echo "== [1] backup delle collezioni toccate (audio_assets, frequency_tracks)"
# il nome del db vive in .env.production (DB_NAME), non nel container mongo
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && [ -n "$DB" ] && docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=audio_assets --archive" > backups/predeploy-'"$GIRO"'-audio_assets.archive && docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=frequency_tracks --archive" > backups/predeploy-'"$GIRO"'-frequency_tracks.archive && ls -la backups/predeploy-'"$GIRO"'*'

echo "== [2] rsync del codice (gli exclude di deploy/deploy-prod.sh + uploads/audio: viaggia col pacchetto)"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -3

echo "== [3] pacchetto libreria sul server (770 MB)"
rsync -avz -e "ssh -i $KEY" "$PACCHETTO/" "$HOST:/opt/aurya/pacchetto-$GIRO/" | tail -2

echo "== [4] immagini e container (script remoto sotto nohup, log /root/deploy-$GIRO.log)"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -2 && echo "== immagine backend pronta $(date -u +%H:%M:%S)" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
$C build frontend 2>&1 | tail -2 && echo "== immagine frontend pronta $(date -u +%H:%M:%S)" || { echo "== BUILD FRONTEND FALLITO"; exit 1; }
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
echo "   attendo il giro…"
for i in $(seq 1 90); do
  if $SSH "grep -q '== FINE' /root/deploy-$GIRO.log 2>/dev/null"; then break; fi
  sleep 5
done
$SSH "cat /root/deploy-$GIRO.log"
$SSH "grep -q 'health backend ok' /root/deploy-$GIRO.log" || { echo "HEALTH NON OK: FERMO prima del pacchetto"; exit 1; }

echo "== [5] pacchetto libreria nel volume (docker cp) e import idempotente"
$SSH "cd /opt/aurya && docker cp pacchetto-$GIRO ms-backend:/app/uploads/pacchetto && \
  docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend python scripts/pacchetto_libreria.py importa /app/uploads/pacchetto --prova | tail -3 && \
  docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend python scripts/pacchetto_libreria.py importa /app/uploads/pacchetto | tail -3 && \
  docker exec -u root ms-backend rm -rf /app/uploads/pacchetto && rm -rf pacchetto-$GIRO"
# (-u root: i file entrati con docker cp sono di root, l'utente dell'app
#  non li puo' cancellare — successo al giro del 22/9, import gia' fatto)

echo "== [6] verifica sul vivo"
N=$(curl -s https://aurya.life/api/frequencies/sounds | python3 -c "import sys,json; d=json.load(sys.stdin)['items']; print(len(d), sum(1 for s in d if s.get('guida')), sum(1 for s in d if s.get('tappeto_url')))")
echo "   suoni · guida · con tappeto: $N   (atteso 260 · 10 · ~106)"
T=$(curl -s https://aurya.life/api/frequencies/sounds | python3 -c "import sys,json; d=json.load(sys.stdin)['items']; print(next(s['tappeto_url'] for s in d if s.get('title','').startswith('Magic Night')))")
echo "   tappeto Magic Night → $(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$T)"
for u in / /sound/crea /sound/esplora /frequenze/x; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
echo "== FATTO. Ora: git tag prod-$GIRO && memoria."
