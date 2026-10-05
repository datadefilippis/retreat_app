#!/bin/bash
# GIRO 5/10/2026 (notte, 5°) — FL3: le 47 email automatiche nelle parole del
# founder (docs/EMAIL_COPY_2026-10_FOUNDER.md). SOLO BACKEND: testi, piede unico,
# passo «canali» della sequenza professionisti, invito nel team con link di
# prima password (mai piu' la password in chiaro), richieste con un'email per
# stato, recensioni, ordini, prenotazioni con date in italiano.
# Nessun frontend, niente nginx, nessun flag. NESSUNA EMAIL PARTE DAL GIRO:
# le sequenze mandano solo ai passi dovuti (il passo «canali» va a chi ha la
# pagina online E ha gia' ricevuto l'email della pagina: al massimo una email
# nuova, utile, a chi e' online da meno di 60 giorni).
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-05-email
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

echo "== [0b] quante email «canali» partirebbero al primo giro (pagina online, profilo_online mandato, canali no)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python -c "
import asyncio
from database import organizations_collection
async def m():
    n = await organizations_collection.count_documents({\"sequenza.profilo_online\": {\"\$exists\": True}, \"sequenza.canali\": {\"\$exists\": False}})
    print(\"   candidati canali (prima del filtro 60 giorni):\", n)
asyncio.run(m())" 2>/dev/null | tail -1'

echo "== [1] rsync"
rsync -avz --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/audio' --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='.DS_Store' --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $KEY" "$REPO/" "$HOST:/opt/aurya/" | tail -2

echo "== [2] build + recreate SOLO backend sotto nohup"
$SSH "cat > /root/deploy-$GIRO.sh" <<'REMOTO'
#!/bin/bash
cd /opt/aurya
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
echo "== inizio $(date -u +%H:%M:%S)"
$C build backend 2>&1 | tail -1 && echo "== backend pronto" || { echo "== BUILD BACKEND FALLITO"; exit 1; }
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

echo "== [3] verifica dal container: i testi nuovi si renderizzano (nessun invio)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python -c "
import services.email_sequenze as T
from services.email_service import _wrap_template, _t
o, c = T.benvenuto_cerchio_ritiri({\"nome\": \"Prova\", \"email\": \"x@example.com\", \"token\": \"t\", \"citta\": \"Bari\", \"interessi\": [\"yoga\"], \"travel\": \"near\", \"vuole_ritiri\": True})
print(\"   benvenuto ritiri →\", o, \"|\", c[c.index(\"Sappiamo\"):c.index(\"Sappiamo\")+70])
print(\"   piede →\", \"Ritiri ed esperienze olistiche, in un posto solo\" in _wrap_template(\"<p>x</p>\", \"it\"), \"· scrivi a:\", \"Per rispondere\" in _wrap_template(\"<p>x</p>\", \"it\"))
print(\"   conferma account →\", _t(\"aurya_verify_subject\", \"it\"), \"· ordine →\", _t(\"order_confirmed_subject\", \"it\", store_name=\"Anna\"))
from services.sequenze import PASSI
print(\"   passi professionista →\", [p.nome for p in PASSI[\"operatore\"]])
" 2>/dev/null | grep -v bcrypt'
for u in / /api/health /api/public/discipline; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s (invariato: frontend non toccato)\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)"
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal pannello admin (Cerchio → Sequenze) l'anteprima [PROVA] di un benvenuto a una tua email."
