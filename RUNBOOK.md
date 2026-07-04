# AFianco — Runbook

Troubleshooting per i problemi piu' comuni in produzione.

---

## Backend non parte

**Sintomo:** `ms-backend` in stato `Restarting` o `Exit 1`.

```bash
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

| Log contiene | Causa | Fix |
|-------------|-------|-----|
| `JWT_SECRET_KEY environment variable is not set` | `.env.production` mancante o JWT_SECRET_KEY vuoto | Impostare JWT_SECRET_KEY in `.env.production` |
| `MONGO_URL` / `KeyError: 'MONGO_URL'` | `--env-file .env.production` non passato al compose | Rilanciare con `--env-file .env.production` |
| `ServerSelectionTimeoutError` | MongoDB non ancora healthy o credenziali errate | Verificare che `ms-mongodb` sia healthy: `docker inspect ms-mongodb --format='{{.State.Health.Status}}'` |
| `ModuleNotFoundError` | Dipendenza mancante in `requirements.prod.txt` | Aggiungere la dipendenza, ricostruire con `--build` |

---

## MongoDB non healthy

**Sintomo:** `ms-mongodb` health status `unhealthy`.

```bash
docker compose -f docker-compose.prod.yml logs mongodb --tail 30
docker inspect ms-mongodb --format='{{json .State.Health}}'
```

| Log contiene | Causa | Fix |
|-------------|-------|-----|
| `Authentication failed` | MONGO_ROOT_USER o MONGO_ROOT_PASSWORD non corrispondono | Se e' il primo avvio: `docker compose down -v` e riavviare con credenziali corrette. Se il volume esiste gia' con credenziali diverse, NON usare `-v` — modificare `.env.production` con le credenziali originali |
| `WiredTiger` error | Volume corrotto (raro) | Restore da backup (vedi DEPLOY.md sezione K) |

**ATTENZIONE:** `docker compose down -v` cancella il volume MongoDB. Usare SOLO se il database e' vuoto (primo avvio) o se si ha un backup.

---

## nginx non parte

**Sintomo:** `ms-nginx` in stato `Exit 1` o `Restarting`.

```bash
docker compose -f docker-compose.prod.yml logs nginx-proxy --tail 20
```

| Log contiene | Causa | Fix |
|-------------|-------|-----|
| `cannot load certificate` / `No such file` | Config TLS attiva ma certificati non ancora ottenuti | Tornare alla config bootstrap: `cp deploy/nginx/nginx-bootstrap.conf deploy/nginx/nginx.conf` poi `docker compose restart nginx-proxy` |
| `host not found in upstream "backend"` | Il service backend non e' partito | Risolvere prima il problema backend |
| `host not found in upstream "frontend"` | Il service frontend non e' partito | Verificare `docker compose logs frontend` |
| `bind() to 0.0.0.0:80 failed` | Porta 80 gia' occupata da un altro processo | `sudo lsof -i :80` per trovare il processo, fermarlo, poi riavviare |

---

## Certbot fallisce

**Sintomo:** `certbot certonly` restituisce errore.

```bash
docker compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot -d $DOMAIN --dry-run
```

| Errore | Causa | Fix |
|--------|-------|-----|
| `Challenge failed` / `unauthorized` | DNS non punta al VPS, o porta 80 bloccata | `dig +short $DOMAIN` deve restituire IP del VPS. `curl http://$DOMAIN/` deve rispondere |
| `too many certificates already issued` | Rate limit Let's Encrypt (5 cert/settimana per dominio) | Attendere 7 giorni, oppure usare `--staging` per test |
| `Connection refused` | nginx-proxy non e' running | Verificare stato nginx: `docker compose ps nginx-proxy` |

**Nota:** aggiungere `--dry-run` al comando certbot per testare senza consumare il rate limit.

---

## Backup non crea file

**Sintomo:** `deploy/backup.sh` fallisce o directory `backups/` vuota.

```bash
bash -x deploy/backup.sh   # eseguire in debug mode
```

| Errore | Causa | Fix |
|--------|-------|-----|
| `Permission denied` | Script non eseguibile | `chmod +x deploy/backup.sh` |
| `Missing MONGO_ROOT_USER` | `.env.production` non trovato o variabili mancanti | Verificare che `.env.production` esista nella root del progetto |
| `Error: No such container: ms-mongodb` | Container MongoDB non running | `docker compose -f docker-compose.prod.yml ps mongodb` — riavviare se necessario |
| File creato ma dimensione 0 | Credenziali MongoDB errate nel backup | Verificare che MONGO_ROOT_USER e MONGO_ROOT_PASSWORD in `.env.production` corrispondano a quelli usati dal container |

---

## Comandi diagnostici rapidi

```bash
# Stato di tutti i container
docker compose -f docker-compose.prod.yml ps

# Log di un servizio specifico (ultimi 100 righe, follow)
docker compose -f docker-compose.prod.yml logs -f --tail 100 backend

# Spazio disco usato dai volumi Docker
docker system df -v

# Connessione diretta a MongoDB (debug)
docker exec -it ms-mongodb mongosh \
  -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" \
  --authenticationDatabase admin "$DB_NAME"

# Riavvio singolo servizio (senza rebuild)
docker compose -f docker-compose.prod.yml restart backend

# Rebuild e riavvio singolo servizio
docker compose -f docker-compose.prod.yml up -d --build backend

# Health check manuale del backend
docker exec ms-backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())"
```
