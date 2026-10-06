#!/bin/bash
# GIRO 6/10/2026 — P4 «formato» delle esperienze (ritiro · evento ·
# formazione): il secondo asse accanto alla disciplina. Backend (schema,
# wizard, PATCH, listing e landing pubblici, tassonomie, script di
# mappatura) + frontend (tre carte nel wizard, selettore nel pannello
# evento, filtro «Tipo» ed etichetta su /esperienze). Nessun flag, nessun
# nginx, nessuna email. ADDITIVO: le 10 esperienze in prod restano senza
# formato finche' la mappatura [4] non lo scrive (solo metadata.formato).
#
# Uso:  deploy/giri/deploy-2026-10-06-formato.sh            # giro completo
#       deploy/giri/deploy-2026-10-06-formato.sh --solo-mappa  # solo [4]+[5]
set -euo pipefail
HOST=root@46.224.0.96
KEY=$HOME/.ssh/aurya_deploy
REPO=$HOME/Desktop/retreat_app
GIRO=2026-10-06-formato
SSH="ssh -i $KEY $HOST"
PY='docker exec $(docker ps -qf name=backend | head -1) python'

# La mappatura decisa dal founder con la regia (6/10): prefisso id = formato.
# Le quattro tappe de «Il Potere dell'Immaginazione» sono seminari di due
# giorni in sala, senza pernottamento → evento. I due corsi → formazione.
# «Il ritorno alle origini» (tre giorni con alloggio) → ritiro.
MAPPA="bcbb8682=evento a8f3d66f=evento d773d469=formazione e162b7eb=evento ed15775b=formazione fbea1186=ritiro 624fa27f=evento 6090c2b6=evento f1800183=evento e27a6b6e=evento"

echo "== [0] Regola Zero: DNS"
IP=$(dig +short aurya.life A | tail -1)
[ "$IP" = "46.224.0.96" ] || { echo "aurya.life punta a $IP: FERMO"; exit 1; }

if [ "${1:-}" != "--solo-mappa" ]; then
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

echo "== [3] verifica: listing con la chiave nuova, filtro, landing, bundle nuovo"
curl -s 'https://aurya.life/api/public/retreats?preview=1' | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('   items', d['total'], '· formati', d.get('formati'), '· card con formato:', sum(1 for i in d['items'] if i.get('formato')))
assert 'formati' in d and all('formato' in i for i in d['items'])"
curl -s 'https://aurya.life/api/public/retreats?preview=1&formato=corso' | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['items']==[] and 'formati' in d; print('   formato ignoto → lista vuota, 200')"
for u in / /esperienze /api/health; do printf "   %s → %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life$u)"; done
JS=$(curl -s https://aurya.life/esperienze | grep -o 'static/js/main\.[a-z0-9]*\.js' | head -1)
printf "   bundle %s → %s · esp-f-tipo nel bundle: %s\n" "$JS" "$(curl -s -o /dev/null -w '%{http_code}' https://aurya.life/$JS)" "$(curl -s https://aurya.life/$JS | grep -c 'esp-f-tipo')"
fi

echo "== [4] mappatura delle esperienze gia' in prod: prova generale, poi scrittura"
ARGS=""; for v in $MAPPA; do ARGS="$ARGS --imposta $v"; done
$SSH "$PY scripts/formato_esperienze.py --lista $ARGS" 2>/dev/null | grep -v bcrypt
$SSH "$PY scripts/formato_esperienze.py $ARGS --scrivi" 2>/dev/null | grep -v bcrypt | tail -12

echo "== [5] verifica dopo la mappatura"
$SSH "$PY scripts/formato_esperienze.py --lista" 2>/dev/null | grep -v bcrypt
curl -s 'https://aurya.life/api/public/retreats?preview=1' | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('   formati in lista →', {k: v['count'] for k, v in d.get('formati', {}).items()})
for i in d['items']: print('   ', i['formato'], '|', i['category'], '|', i['title'])"
curl -s 'https://aurya.life/api/public/retreats?preview=1&formato=formazione' | python3 -c "import json,sys; d=json.load(sys.stdin); print('   solo formazione →', [i['title'] for i in d['items']])"
echo "== FATTO. Ora: git tag prod-$GIRO. Poi dal browser: /esperienze (filtro Tipo), il pannello di un evento (Che cos'è?), il wizard (tre carte)."
