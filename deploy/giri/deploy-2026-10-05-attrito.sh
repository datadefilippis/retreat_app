#!/bin/bash
# GIRO 5/10/2026 (sera, 4°) — «Iscrizione senza attrito», primo giro (FL2+FL1+FL0+FL4+FL5):
#   FL2 il pulsante dell'email apre davvero (?prova= nel redirect di /v/ e /entra/, salvata prima del render)
#   FL1 il risultato si vede dove hai cliccato (lib/esito.js su 14 form; via i reload del blog)
#   FL0 banner cookie: «Accetta tutto» pieno + Personalizza + Continua senza accettare
#   FL4 una frase sola «sei dentro, cosa succede adesso», senza genere
#   FL5 il clic di verifica dell'account cliente fa entrare (sessione come il magic link)
# Backend + frontend, NIENTE nginx, nessun flag, nessuna email parte da sola.
# FL3 (testi delle email) NON e' in questo giro: aspetta la lettura del founder.
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-05-attrito
SSH="ssh -i $KEY $HOST"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

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
for u in / /cerca-ritiro /meditazioni /o/anpoche /entra-nella-rete /accedi /account/verifica /blog /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/ | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · stesso su /meditazioni → %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/meditazioni | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)"
printf "   bundle con raccogliProvaDaUrl → %s (atteso ≥1)\n" "$(curl -s https://aurya.life/$JS | grep -o 'prova' | wc -l | tr -d ' ')"
printf "   bundle col banner nuovo → %s (atteso 1)\n" "$(curl -s https://aurya.life/$JS | grep -c 'cookie-continua-senza' || true)"
# FL2: il redirect verificante porta la prova (token di prova firmato dal container, nessuna email)
TOKEN=$($SSH "docker exec \$(docker ps -qf name=backend | head -1) python -c \"from core.subscriber_token import generate_subscriber_token; print(generate_subscriber_token('verifica-giro-fl@example.com'))\" 2>/dev/null | tail -1")
printf "   /v/{token}?to=/meditazioni → %s\n" "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "https://aurya.life/api/public/newsletter/v/$TOKEN?to=/meditazioni" | sed 's/prova=.*/prova=<token>/')"
printf "   /v/rotto?to=/meditazioni → %s (atteso 302 senza prova)\n" "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' 'https://aurya.life/api/public/newsletter/v/non.un.token?to=/meditazioni')"
# FL5: token rotto = 400 senza sessione
printf "   verify-email token rotto → %s (atteso 400)\n" "$(curl -s -o /dev/null -w '%{http_code}' -X POST https://aurya.life/api/platform/auth/verify-email -H 'Content-Type: application/json' -d '{"token":"non-esiste"}')"
echo "== [3b] pulizia: il clic di prova ha creato un iscritto? (segna_verificato su email sconosciuta: no)"
$SSH 'docker exec $(docker ps -qf name=backend | head -1) python -c "
import asyncio
from database import db
async def m():
    r = await db.aurya_subscribers.delete_many({\"email\": \"verifica-giro-fl@example.com\"})
    print(\"   cancellati\", r.deleted_count, \"(atteso 0)\")
asyncio.run(m())" 2>/dev/null | tail -1'
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser: banner nuovo → Accetta tutto → iscrizione → risultato al centro; email di benvenuto → pulsante meditazioni → aperte senza form."
