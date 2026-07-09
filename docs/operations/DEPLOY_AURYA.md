# DEPLOY_AURYA.md — il processo di deploy, stabile e replicabile

> Prod live dal 9/7/2026 su **https://aurya.life** — Hetzner CPX22
> (Falkenstein), Ubuntu 26.04, Docker Compose. Questo è il runbook
> operativo: cosa gira, come si aggiorna, come si recupera.

## Architettura in una riga

`Cloudflare DNS → nginx (:80/:443, TLS Let's Encrypt) → { SEO shell &
API su backend :8000 · asset su frontend :80 } · MongoDB interno`.
Tutto in Docker Compose su un solo host. La build del frontend avviene
sul server (swap 4 GB come rete di sicurezza sui 4 GB di RAM).

## Server

- **Host:** `root@46.224.0.96` · **dir:** `/opt/aurya`
- **Chiave SSH:** `~/.ssh/aurya_deploy` (dedicata, sul Mac del founder)
- **Segreti:** `/opt/aurya/.env.production` (solo sul server, MAI in git;
  generato con `openssl rand`). Contiene JWT, password Mongo, token
  metrics, chiave IndexNow. Stripe/Brevo da riempire quando si attivano.

## Redeploy (dopo aver mergiato codice su main) — UN comando

Dal Mac, dalla root del repo:

```bash
VPS_HOST=root@46.224.0.96 ./deploy/deploy-prod.sh
```

Fa: rsync del codice → `docker compose up -d --build` → healthcheck.
NON tocca `.env.production` né i volumi Mongo (i dati persistono).
Il primo giro dopo un cambio di `docker-compose.prod.yml`/nginx richiede
il rebuild; i deploy di solo codice backend/frontend rifanno solo le
immagini interessate.

## Prima messa in produzione (già fatta — qui per replicabilità)

1. Server Hetzner (≥4 GB RAM), Ubuntu LTS, chiave `aurya_deploy` iniettata.
2. Provisioning: swap 4 GB, `ufw` (22/80/443), Docker via get.docker.com.
3. `rsync` del repo in `/opt/aurya` + `.env.production` (chmod 600).
4. **Bootstrap HTTP** (nessun cert ancora):
   `NGINX_CONF=./deploy/nginx/nginx-bootstrap.conf docker compose … up -d --build`
   → sito visibile su `http://<IP>` con routing SEO corretto.
5. DNS: record A `@` e `www` → IP (Cloudflare, **grigio/DNS-only** per
   la challenge Let's Encrypt).
6. Certificato: `docker compose … run --rm certbot certonly --webroot
   -w /var/www/certbot -d aurya.life -d www.aurya.life --email … --agree-tos`.
7. **Switch a TLS**: `docker compose … up -d` (senza `NGINX_CONF` →
   usa `deploy/nginx/nginx.conf` con TLS). Redirect 80→443 attivo.
8. Cron auto-rinnovo in `/etc/cron.d/aurya-certbot` (renew notturno +
   `nginx -s reload`).

## Dettagli che NON sono ovvi (imparati sul campo)

- **SEO shell in Docker**: il backend legge l'`index.html` della build
  via HTTP dal container frontend (`SEO_SHELL_INDEX_PATH=http://frontend/
  index.html`, in `docker-compose.prod.yml`). Senza, le pagine pubbliche
  escono VUOTE (template dev senza `<script>`).
- **Lockfile frontend**: `npm ci` nel build esige `package-lock.json`
  in sync con `package.json` (leaflet/react-leaflet aggiunti in G1
  vanno nel lock, altrimenti il build fallisce).
- **nginx versionato**: `deploy/nginx/nginx.conf` è ora sincronizzato dal
  deploy (rimosso dall'exclude rsync) — modifiche al routing arrivano in
  prod col deploy, non a mano.
- **Bootstrap vs TLS**: due config nginx. `nginx-bootstrap.conf` (HTTP,
  serve ACME) per il primo giro / ri-emissione cert; `nginx.conf` (TLS)
  a regime. Si sceglie con la variabile `NGINX_CONF`.

## Da configurare quando si attivano (oggi in dry-run/off)

- **Email (Brevo)**: `BREVO_API_KEY` in `.env.production` + DNS SPF/DKIM/
  DMARC su Cloudflare (senza chiave le 39 email sono loggate, non spedite).
- **Stripe LIVE**: `STRIPE_SECRET_KEY`/`STRIPE_PUBLISHABLE_KEY`/
  `STRIPE_WEBHOOK_SECRET` + webhook `https://aurya.life/api/billing/webhooks`.
  Senza, il calendario ritiri resta vuoto (gate GT1b: solo operatori con
  Stripe attivo sono listabili) e il checkout non incassa.
- Dopo aver toccato `.env.production`: `docker compose … up -d` (ricrea i
  container con le nuove env).

## Rinnovo / recupero

- **Cert**: rinnovo automatico (cron). Forzare a mano: `docker compose …
  run --rm certbot renew --force-renewal && docker compose … exec -T
  nginx-proxy nginx -s reload`.
- **Log**: `docker compose … logs -f backend` (o nginx/frontend/mongodb).
- **Backup Mongo**: `deploy/backup.sh` (age, retention 30gg) da mettere in
  cron — TODO se non ancora fatto; provare SEMPRE un restore su DB vuoto.
- **Rollback**: il deploy è idempotente; per tornare indietro, `git
  checkout <sha>` sul Mac e ri-lanciare `deploy-prod.sh`.

## Opzionali (miglioramenti, non bloccanti)

- Cloudflare **arancione** (proxy on) + SSL mode "Full (strict)": CDN +
  DDoS gratis. Il cert origin Let's Encrypt resta valido.
- Hardening SSH: disabilitare `PasswordAuthentication` (la chiave basta).
- `http2 on;` al posto di `listen … http2` (warning cosmetico nginx).
