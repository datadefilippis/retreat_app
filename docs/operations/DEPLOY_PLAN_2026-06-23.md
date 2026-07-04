# Piano di Deploy Controllato — 2026-06-23

**Obiettivo:** allineare la produzione a `main` (`80c8dda`) — hotfix modello AI
(`claude-sonnet-4-6`, risolve il 404 su `/api/ai/chat`) + modulo **Newsletter** +
pacchetto **embed/ecommerce embedding** completo.

**Vincolo critico:** in produzione c'è **un utente attivo che usa Cashflow**.
Il deploy **non deve** impattarlo né perdere dati. Il codice Cashflow **non è
cambiato**.

**Esecuzione:** i comandi verso `root@46.224.29.40` li lancio io via Bash,
**fermandomi a ogni GATE** per conferma esplicita prima di ogni passo
irreversibile.

---

## Riepilogo rischio

| Aspetto | Valutazione |
|---|---|
| Dati Cashflow | **Sicuri.** Startup backend additivo/idempotente (solo creazione indici su `sales_records`/`expense_records`/`fixed_costs`; nessuna scrittura/migrazione distruttiva). Mongo gira su volume `ms-mongo-data`, non ricostruito dal deploy. |
| Newsletter / Embed | **Additivi.** Collezioni nuove (`newsletter_forms`, `newsletter_subscriptions`); nessuna migrazione su collezioni esistenti. |
| Downtime | **Breve** (secondi): `up -d --build` builda con i container vecchi attivi, poi ricrea solo backend+frontend. Mongo non viene ricreato. |
| Rollback | **Pronto.** Backup cifrato pre-deploy + commit attuale di prod come target di checkout. |
| Superficie | Più ampia del solo hotfix (newsletter+embed mai stati in prod), ma tutto additivo e con test verdi. |

---

## Parametri deploy

```bash
export VPS_HOST=root@46.224.29.40
export VPS_DIR=/opt/margin-sentinel
export SSH_KEY=~/.ssh/hetzner_rsa     # DA CONFERMARE al GATE 0 (fallback: ~/.ssh/id_ed25519)
export DOMAIN=afianco.app
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"
```

---

## FASE 0 — Pre-flight LOCALE (nessun impatto su prod)

0.1 **Working tree pulito su `main`** — confermato HEAD `80c8dda`. I due file
untracked (`AFIANCO_Presentation_Report.docx`, `Codice 2FA Demo.command`) **non
devono finire in prod**: spostarli fuori dal repo prima del rsync (o aggiungerli
agli `--exclude`).

0.2 **Test completi in locale** (catturare regressioni prima del VPS):
- Backend: `pytest` sulle suite toccate (llm/cost calculator, newsletter, embed).
- SDK: `vitest` newsletter + embed.

0.3 **Build frontend in locale** (`pnpm --filter frontend build` o equivalente):
il build CRA è il passo più pesante; farlo fallire **qui** invece che sul VPS
evita un deploy a metà.

**GATE 0 → conferma per passare al pre-flight su prod (read-only).**

---

## FASE 1 — Pre-flight su PROD (READ-ONLY, nessuna modifica)

1.1 **Connettività SSH** (provo `hetzner_rsa`, fallback `id_ed25519`):
```bash
ssh -i $SSH_KEY $VPS_HOST 'echo OK; uname -a'
```

1.2 **Stato attuale = target di rollback:**
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && git log --oneline -1 && git rev-parse HEAD"
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && $COMPOSE ps"
```
→ **annotare il commit hash attuale** (rollback target).

1.3 **Risorse VPS** (il build ha bisogno di spazio/RAM):
```bash
ssh -i $SSH_KEY $VPS_HOST 'df -h / && free -m'
```

1.4 **Verifica env modello** (il fix è inutile se `.env.production` pinna il
vecchio ID):
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && grep -E 'CLAUDE_MODEL|LLM_NON_CHAT_MODEL|ENVIRONMENT|ANTHROPIC_API_KEY' .env.production || true"
```
→ atteso: `ENVIRONMENT=production`, `ANTHROPIC_API_KEY` valorizzato, e
**nessun** `CLAUDE_MODEL`/`LLM_NON_CHAT_MODEL` puntato a `claude-sonnet-4-20250514`.
Se presente, va rimosso o messo a `claude-sonnet-4-6`.

1.5 **Snapshot integrità dati Cashflow** (baseline da riconfrontare dopo):
```bash
ssh -i $SSH_KEY $VPS_HOST "docker exec ms-mongodb mongosh \
  -u \$MONGO_ROOT_USER -p \$MONGO_ROOT_PASSWORD --authenticationDatabase admin --quiet \
  \$DB_NAME --eval 'print(\"sales=\"+db.sales_records.countDocuments({}), \"expenses=\"+db.expense_records.countDocuments({}), \"fixed=\"+db.fixed_costs.countDocuments({}))'"
```
→ **annotare i conteggi** (sales / expenses / fixed_costs). Devono essere
**identici** dopo il deploy.

1.6 **Health pre-deploy:**
```bash
ssh -i $SSH_KEY $VPS_HOST 'curl -s http://localhost/api/health'
```

**GATE 1 → conferma per eseguire il BACKUP.**

---

## FASE 2 — RETE DI SICUREZZA (PRIMA di qualsiasi modifica)

> **Realtà prod (verificata al pre-flight):** `/opt/margin-sentinel` **non è un
> repo git** (rsync esclude `.git`). Il rollback NON è `git checkout`. La
> convenzione consolidata dell'operatore è: **snapshot directory** +
> **tag immagini Docker** `:pre-<tag>-rollback`. Seguo la stessa.

2.1 **Backup fresco cifrato** (mongodump + uploads + config → Storage Box):
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && ./deploy/backup.sh 2>&1 | tail -30"
```
Atteso: `Backup complete!` con `db_YYYYMMDD_*.age` di dimensione > 0.

2.2 **Tag immagini correnti come rollback** (le `:latest` verranno sovrascritte
dal `--build`; qui le preserviamo per un rollback istantaneo senza rebuild):
```bash
TAG=pre-deploy-20260623
ssh -i $SSH_KEY $VPS_HOST "
  docker tag margin-sentinel-backend:latest  margin-sentinel-backend:$TAG &&
  docker tag margin-sentinel-frontend:latest margin-sentinel-frontend:$TAG &&
  docker images | grep -E 'margin-sentinel-(backend|frontend)' | grep $TAG"
```

2.3 **Snapshot directory** (codice + compose + nginx, per rollback file):
```bash
ssh -i $SSH_KEY $VPS_HOST "cp -a $VPS_DIR ${VPS_DIR}.PRE_DEPLOY_20260623 && ls -d ${VPS_DIR}.PRE_DEPLOY_*"
```

**GATE 2 → conferma per il DEPLOY (azione che modifica la prod).**

---

## FASE 3 — DEPLOY (gated)

3.1 **Finestra a basso traffico**: scegliere un momento in cui l'utente Cashflow
non sta lavorando (downtime atteso: secondi). Eventuale avviso all'utente.

3.2 **Rsync DRY-RUN** (vedere cosa cambia e — soprattutto — **cosa verrebbe
cancellato** dal `--delete`, senza scrivere nulla):
```bash
rsync -avzn --delete \
  --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='.venv' \
  --exclude='__pycache__' --exclude='data/' --exclude='mongodb-macos-*' \
  --exclude='.claude' --exclude='backups' --exclude='.env' --exclude='.env.*' \
  --exclude='frontend/build' --exclude='frontend/node_modules' \
  --exclude='backend/uploads/*.csv' --exclude='backend/uploads/*.xlsx' \
  --exclude='deploy/nginx/nginx.conf' --exclude='deploy/nginx/nginx-tls.conf' \
  --exclude='deploy/nginx/nginx-bootstrap.conf' \
  --exclude='AFIANCO_Presentation_Report.docx' --exclude='Codice 2FA Demo.command' \
  -e "ssh -i $SSH_KEY" ./ "$VPS_HOST:$VPS_DIR/"
```
→ revisionare la lista. **GATE 3a**: niente di inatteso in `deleting ...`.

3.3 **Deploy reale** — rsync + rebuild + restart. Userò
[`deploy/deploy-prod.sh`](../../deploy/deploy-prod.sh) con le env sopra (estende
gli exclude per i 2 file untracked), oppure i comandi espliciti equivalenti:
```bash
VPS_HOST=$VPS_HOST VPS_DIR=$VPS_DIR SSH_KEY=$SSH_KEY DOMAIN=$DOMAIN ./deploy/deploy-prod.sh
```
Lo script: rsync `--delete` → `compose up -d --build` → attesa 15s → `ps` +
`curl /api/health`.

> Nota: lo script **non** tocca `.env.production`, le `nginx.conf`, né i volumi
> Mongo. Mongo non viene ricostruito.

**GATE 3b → verifica post-deploy.**

---

## FASE 4 — VERIFICA post-deploy (smoke + integrità dati)

4.1 **Container su:**
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && $COMPOSE ps"
```
→ `ms-mongodb` healthy, `ms-backend` healthy, `ms-frontend`/`ms-nginx` up.

4.2 **Smoke base:**
```bash
ssh -i $SSH_KEY $VPS_HOST 'curl -s http://localhost/api/health'
curl -s -o /dev/null -w "%{http_code}\n" https://$DOMAIN/
curl -s -o /dev/null -w "%{http_code}\n" -I https://$DOMAIN/api/health
```

4.3 **Il bug originale è risolto** — niente più 404 modello nei log backend:
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && $COMPOSE logs --tail=80 backend | grep -iE 'not_found|sonnet-4-20250514|LLMUnavailable' || echo 'nessun errore modello'"
```
+ (se possibile) un giro reale di AI chat dall'app e conferma risposta.

4.4 **Integrità dati Cashflow** — riconfrontare i conteggi col baseline 1.5:
```bash
ssh -i $SSH_KEY $VPS_HOST "docker exec ms-mongodb mongosh \
  -u \$MONGO_ROOT_USER -p \$MONGO_ROOT_PASSWORD --authenticationDatabase admin --quiet \
  \$DB_NAME --eval 'print(\"sales=\"+db.sales_records.countDocuments({}), \"expenses=\"+db.expense_records.countDocuments({}), \"fixed=\"+db.fixed_costs.countDocuments({}))'"
```
→ **devono coincidere** con i valori pre-deploy. + verifica veloce in app che
l'utente Cashflow veda i suoi dati.

4.5 **Newsletter additiva presente** (no errori, route attive):
```bash
ssh -i $SSH_KEY $VPS_HOST "cd $VPS_DIR && $COMPOSE logs --tail=120 backend | grep -iE 'error|traceback' | tail -20 || echo 'log puliti'"
```

**GATE 4 → deploy confermato OK, oppure → ROLLBACK.**

---

## FASE 5 — ROLLBACK (se GATE 4 fallisce)

I dati Mongo restano sul volume `ms-mongo-data` in ogni caso. Tre livelli, dal
più veloce al più completo:

**A) Rollback immagini (più rapido — niente rebuild):**
```bash
TAG=pre-deploy-20260623
ssh -i $SSH_KEY $VPS_HOST "
  docker tag margin-sentinel-backend:$TAG  margin-sentinel-backend:latest &&
  docker tag margin-sentinel-frontend:$TAG margin-sentinel-frontend:latest &&
  cd $VPS_DIR && $COMPOSE up -d --no-build"
```

**B) Rollback codice + immagini (se anche compose/nginx sono cambiati):**
```bash
ssh -i $SSH_KEY $VPS_HOST "
  rm -rf ${VPS_DIR}.BROKEN && mv $VPS_DIR ${VPS_DIR}.BROKEN &&
  cp -a ${VPS_DIR}.PRE_DEPLOY_20260623 $VPS_DIR &&
  cd $VPS_DIR && $COMPOSE up -d --no-build"
```
(le immagini `:latest` sono ancora le pre-deploy se non si è ri-buildato; in
caso, applicare prima il punto A.)

**C) Rollback dati** (solo se i conteggi 4.4 non coincidono — non atteso, lo
startup è additivo): restore dal backup cifrato del passo 2.1 (decrittare con
chiave `age` offline → `mongorestore --drop`). Vedi `deploy/backup.sh` +
`docs/operations/` restore drill.

---

## Mitigazioni rischi noti

- **Build OOM sul VPS (4GB)**: il frontend è già stato buildato lì in passato;
  se il build CRA va in OOM, abilitare swap o `NODE_OPTIONS=--max-old-space-size`.
  Controllo `free -m` al passo 1.3.
- **`--delete` rsync**: dry-run obbligatorio (3.2) per non rimuovere file legittimi
  presenti solo sul VPS.
- **CLAUDE_MODEL pinnato in prod**: verificato al passo 1.4; va sistemato prima
  del restart altrimenti il 404 persiste.
- **Errori da evitare** (da DEPLOY.md): mai `compose down -v`; sempre
  `--env-file .env.production`; mai `--workers > 1`.

---

## Checklist GATE — ESEGUITO 2026-06-23 ✅

- [x] GATE 0 — pre-flight locale (backend 3783 passed/0 fail, build frontend ok; 15 test SDK stale non bloccanti → task separato)
- [x] GATE 1 — pre-flight prod (no git sul VPS; rollback via tag immagini+snapshot dir; env modello ok; baseline dati annotato)
- [x] GATE 2 — backup cifrato su Storage Box + tag `pre-deploy-20260623` + snapshot `/opt/margin-sentinel.PRE_DEPLOY_20260623`
- [x] GATE 3a — rsync dry-run: unica cancellazione `backend/src/` (codice stale, ok)
- [x] GATE 3b — deploy eseguito (build con container vecchi attivi; mongo NON ricreato)
- [x] GATE 4 — health ok, frontend 200, nessun errore modello nei log, **conteggi Cashflow invariati** (5/7/664/1257/6/1244)

**Esito: deploy riuscito, prod allineata a `main` (80c8dda), dati intatti.**
Rollback disponibile: immagini `:pre-deploy-20260623` + dir `.PRE_DEPLOY_20260623`.
