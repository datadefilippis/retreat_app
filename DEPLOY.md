# AFianco — Deploy Guide

Single VPS deployment with Docker Compose, nginx reverse proxy, Let's Encrypt TLS.

---

## Prerequisites

- VPS with Ubuntu 22.04+ (2 vCPU, 4 GB RAM minimum)
- Docker Engine 24+ and Docker Compose v2 installed
- Domain with DNS A record pointing to the VPS IP
- Ports 80 and 443 open in firewall
- Git installed on VPS

---

## A. Preparazione locale

**Obiettivo:** repository pronto per il deploy.

```bash
# Verificare che tutti i file di deploy esistano
ls backend/Dockerfile frontend/Dockerfile docker-compose.prod.yml \
   deploy/nginx/nginx.conf deploy/nginx/nginx-bootstrap.conf \
   .env.example deploy/backup.sh
```

Tutti e 7 devono esistere. Push su GitHub se non ancora fatto:

```bash
git add -A && git commit -m "Deploy artifacts" && git push origin main
```

---

## B. Preparazione VPS

**Obiettivo:** VPS pronto con Docker e il codice.

```bash
# Sul VPS
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# IMPORTANTE: logout e login per applicare il gruppo docker

# Clona il repo
git clone https://github.com/TUO_USER/BI_PMI.git /opt/margin-sentinel
cd /opt/margin-sentinel
```

**Expected:** directory `/opt/margin-sentinel` con tutto il codice.

---

## C. Configurazione .env.production

**Obiettivo:** file environment con tutti i valori reali.

```bash
cd /opt/margin-sentinel
cp .env.example .env.production
```

Compilare `.env.production` con valori reali:

```bash
# Genera i segreti
openssl rand -base64 24    # → usare come MONGO_ROOT_PASSWORD
openssl rand -hex 32       # → usare come JWT_SECRET_KEY
```

Valori OBBLIGATORI da impostare:

| Variabile | Valore |
|-----------|--------|
| `MONGO_ROOT_PASSWORD` | output di `openssl rand -base64 24` |
| `JWT_SECRET_KEY` | output di `openssl rand -hex 32` |
| `CORS_ORIGINS` | `https://app.tuodominio.it` |

Verificare che `ENVIRONMENT=production` (già presente nel template).

---

## D. Sostituzione YOUR_DOMAIN + Bootstrap HTTP-only

**Obiettivo:** stack running in HTTP per ottenere i certificati TLS.

```bash
cd /opt/margin-sentinel

# 1. Sostituisci YOUR_DOMAIN nei file nginx
DOMAIN="app.tuodominio.it"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" deploy/nginx/nginx.conf
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" deploy/nginx/nginx-bootstrap.conf

# 2. Salva la config TLS e metti la bootstrap al suo posto
cp deploy/nginx/nginx.conf deploy/nginx/nginx-tls.conf
cp deploy/nginx/nginx-bootstrap.conf deploy/nginx/nginx.conf

# 3. Avvia lo stack
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

**Expected:** `docker compose -f docker-compose.prod.yml ps` mostra 4 container Up (mongodb healthy, backend healthy, frontend running, nginx-proxy running).

**Tempo stimato:** 3-8 minuti per il primo build.

---

## E. Ottenimento certificato TLS

**Obiettivo:** certificato Let's Encrypt emesso e salvato nel volume.

```bash
docker compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot -d $DOMAIN
```

**Expected:** output con `Congratulations!` e percorso `/etc/letsencrypt/live/DOMAIN/`.

**Se fallisce:** verificare che il DNS A record sia corretto (`dig +short $DOMAIN`) e che la porta 80 sia raggiungibile (`curl http://$DOMAIN/.well-known/acme-challenge/test` dal browser).

---

## F. Attivazione config TLS finale

**Obiettivo:** nginx serve HTTPS con il certificato ottenuto.

```bash
# Ripristina la config TLS completa
cp deploy/nginx/nginx-tls.conf deploy/nginx/nginx.conf

# Ricarica nginx (zero downtime)
docker compose -f docker-compose.prod.yml exec nginx-proxy nginx -s reload
```

**Expected:** `curl -I https://$DOMAIN/api/health` restituisce HTTP 200.

---

## G. Smoke test

```bash
# Health check API
curl https://$DOMAIN/api/health
# Expected: {"status":"healthy","service":"margin-sentinel-ai","version":"2.0.0"}

# Frontend carica
curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/
# Expected: 200

# Redirect HTTP → HTTPS funziona
curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/
# Expected: 301
```

---

## H. Creazione system admin

**Obiettivo:** primo utente admin della piattaforma.

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_system_admin.py \
  --email admin@tuodominio.it \
  --password 'UnaPasswordForte12+'
```

**Expected:** `System admin created successfully` con ID e email.

**Vincoli:** password minimo 12 caratteri. Un solo system admin per piattaforma.

---

## I. Test backup

```bash
chmod +x deploy/backup.sh
./deploy/backup.sh
ls -lh backups/
```

**Expected:** file `backups/ms_backup_YYYYMMDD_HHMMSS.gz` presente con dimensione > 0.

---

## J. Cron minimi

```bash
# Backup giornaliero alle 03:00
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/margin-sentinel/deploy/backup.sh >> /var/log/ms-backup.log 2>&1") | crontab -

# Rinnovo certificati giornaliero alle 04:00
(crontab -l 2>/dev/null; echo "0 4 * * * cd /opt/margin-sentinel && docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx-proxy nginx -s reload >> /var/log/ms-certbot.log 2>&1") | crontab -

# Verifica
crontab -l
```

---

## K. Rollback minimo

Se qualcosa non funziona dopo un aggiornamento:

```bash
# 1. Ferma tutto
docker compose -f docker-compose.prod.yml down

# 2. Torna al commit precedente
git log --oneline -5          # trova il commit buono
git checkout <COMMIT_HASH>

# 3. Ricostruisci e riavvia
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

I dati MongoDB persistono nel volume `ms-mongo-data` e sopravvivono a `docker compose down`.

Per un rollback dei dati MongoDB:

```bash
# Restore da backup
docker exec -i ms-mongodb mongorestore \
  --uri="mongodb://USER:PASS@localhost:27017/DB?authSource=admin" \
  --archive --gzip --drop \
  < backups/ms_backup_YYYYMMDD_HHMMSS.gz
```

---

## Operator Mistakes to Avoid

| Errore | Conseguenza | Prevenzione |
|--------|-------------|-------------|
| Non sostituire `YOUR_DOMAIN` | nginx rifiuta di partire o serve il dominio sbagliato | `grep -r YOUR_DOMAIN deploy/` deve restituire 0 risultati |
| `.env.production` incompleto | Backend crash all'avvio (JWT_SECRET_KEY mancante) | Verificare che `MONGO_ROOT_PASSWORD`, `JWT_SECRET_KEY`, `CORS_ORIGINS` siano valorizzati |
| DNS non ancora puntato | Certbot fallisce con errore di validazione | `dig +short $DOMAIN` deve restituire l'IP del VPS |
| Usare nginx.conf TLS prima di avere i certificati | nginx non parte (file .pem non trovati) | Sempre bootstrap HTTP → certbot → switch TLS |
| Path sbagliato per create_system_admin | `ModuleNotFoundError` | Il path corretto e' `scripts/create_system_admin.py` (relativo a `/app` nel container) |
| Gunicorn con `--workers > 1` | Background scheduler duplicato, alert generati N volte | Il Dockerfile forza `--workers 1` — non sovrascrivere |
| `docker compose down -v` | Cancella i volumi MongoDB — perdita dati totale | Usare `docker compose down` SENZA `-v` |
| Dimenticare `--env-file .env.production` | Compose non interpola le variabili, MongoDB parte senza auth | Sempre includere `--env-file .env.production` |

---

## Reference — Service Names

| Service (compose) | Container name | Porta interna | Porta esposta |
|-------------------|---------------|---------------|---------------|
| `mongodb` | `ms-mongodb` | 27017 | nessuna |
| `backend` | `ms-backend` | 8000 | nessuna |
| `frontend` | `ms-frontend` | 80 | nessuna |
| `nginx-proxy` | `ms-nginx` | 80, 443 | 80, 443 |
| `certbot` | `ms-certbot` | — | — |

## Reference — Named Volumes

| Volume | Mount point | Contenuto |
|--------|-------------|-----------|
| `ms-mongo-data` | `/data/db` | Database MongoDB |
| `ms-backend-uploads` | `/app/uploads` | File CSV/XLSX caricati |
| `ms-certbot-conf` | `/etc/letsencrypt` | Certificati TLS |
| `ms-certbot-www` | `/var/www/certbot` | ACME challenge files |
