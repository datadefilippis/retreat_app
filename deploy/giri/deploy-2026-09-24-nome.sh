#!/bin/bash
# GIRO 24/9/2026 sera (2°) — UNA variabile nome: solo BACKEND (services/
# nome_persona.py, GET profilo con nome dall'account, allineamento
# account, script di riempimento). Frontend invariato → giro corto:
# backup organizations+users, rsync, build+recreate del solo backend,
# riempimento del pregresso in prova e poi vero, verifica dei nomi
# pubblici. Si lancia DAL MAC.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-09-24-nome
SSH="ssh -i $KEY $HOST"
C='docker compose -f docker-compose.prod.yml --env-file .env.production'

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [1] backup organizations + users"
$SSH 'cd /opt/aurya && mkdir -p backups && DB=$(grep -E "^DB_NAME=" .env.production | cut -d= -f2) && for C in organizations users; do docker exec ms-mongodb sh -c "mongodump --username=\$MONGO_INITDB_ROOT_USERNAME --password=\$MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase=admin --db='"'"'$DB'"'"' --collection=$C --archive" > backups/predeploy-'"$GIRO"'-$C.archive; done && ls backups/predeploy-'"$GIRO"'* | wc -l'

echo "== [2] nomi pubblici PRIMA (per confronto)"
curl -s "https://aurya.life/api/public/operators?preview=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(i['name'].strip() for i in d['items']))" | tee /tmp/nomi-prima.txt

echo "== [3] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [4] build + recreate del solo backend"
$SSH "cd /opt/aurya && $C build backend 2>&1 | tail -1 && $C up -d --no-deps backend 2>&1 | tail -1"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://aurya.life/api/health || true)
  [ "$code" = "200" ] && { echo "   health ok ($i)"; break; }
  sleep 2
done
[ "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/api/health)" = "200" ] || { echo "HEALTH NON OK"; exit 1; }

echo "== [5] riempimento del pregresso: prova, poi vero"
$SSH "cd /opt/aurya && $C exec -T backend python scripts/riempi_nome_persona.py --prova 2>&1 | grep -v 'bcrypt\|__about__\|Traceback\|File \|version = \|\^\^'"
$SSH "cd /opt/aurya && $C exec -T backend python scripts/riempi_nome_persona.py 2>&1 | grep -v 'bcrypt\|__about__\|Traceback\|File \|version = \|\^\^' | tail -1"

echo "== [6] nomi pubblici DOPO"
sleep 3
curl -s "https://aurya.life/api/public/operators?preview=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(i['name'].strip() for i in d['items']))" | tee /tmp/nomi-dopo.txt
for u in / /operatori /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
echo "== FATTO. Ora: git tag prod-$GIRO, memoria."
