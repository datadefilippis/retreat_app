# DEPLOY_CHECKLIST.md — andare in produzione su aurya.life

> R5 (6/7/2026). Questa è LA sequenza: eseguirla dall'alto in basso su
> staging prima, poi in produzione. Le voci 【founder】 sono operazioni
> sui servizi esterni che solo tu puoi fare.

## 1 · Infrastruttura

- [ ] 【founder】 VPS (Hetzner CX22 basta per il lancio) con Ubuntu LTS,
      firewall: aperte solo 80/443 (+ SSH da IP tuo).
- [ ] 【founder】 Cloudflare: `aurya.life` → A record verso il VPS,
      proxy ARANCIONE attivo (TLS + cache + protezione L7 gratis).
- [ ] MongoDB: istanza locale al VPS o Atlas M0/M10; abilitare auth e
      bind solo su localhost/rete privata.
- [ ] Reverse proxy (Caddy consigliato: HTTPS automatico):
      `aurya.life` → frontend build statica; `/api` e `/metrics` →
      backend :8000. Bloccare `/metrics` dall'esterno (ACL) — c'è anche
      il token app-level, doppia difesa.
- [ ] **SEO shell (S0.2)** — le route PUBBLICHE vanno al backend, che
      serve l'HTML con i meta già iniettati (`/__seo/*`):
      ```
      @public path / /ritiri* /e/* /p/* /ph/* /dg/* /co/* /r/* /o/* /s/*
      rewrite @public /__seo{path}
      reverse_proxy @public 127.0.0.1:8000
      ```
      e `SEO_SHELL_INDEX_PATH=/percorso/frontend/build/index.html` nel
      .env del backend. Verifica: `curl -A WhatsApp https://aurya.life/e/...`
      deve mostrare title e og:image del ritiro.

## 2 · Variabili d'ambiente backend (.env di produzione)

Obbligatorie — il boot fallisce o funziona male senza:

| Var | Valore produzione |
|---|---|
| `ENVIRONMENT` | `production` (accende cookie Secure, HSTS, auth /metrics) |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` — MAI riusare quella dev |
| `MONGO_URL` / `DB_NAME` | istanza prod / `aurya_prod` |
| `CORS_ORIGINS` | `https://aurya.life` (senza slash finale) |
| `PUBLIC_APP_URL` / `APP_URL` / `FRONTEND_URL` | `https://aurya.life` |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` | chiavi **LIVE** |
| `STRIPE_WEBHOOK_SECRET` | dal webhook LIVE (punto 4) |
| `STRIPE_CLIENT_ID` | Connect LIVE |
| `BREVO_API_KEY` | chiave LIVE — senza, le 39 email restano dry-run! |
| `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` | `noreply@aurya.life` / `Aurya` |
| `METRICS_AUTH_TOKEN` | `openssl rand -hex 24` |
| `SENTRY_DSN` | progetto Sentry prod |

Consigliate: `BREVO_WEBHOOK_SECRET` (eventi bounce/spam), `S3_*` (5 var,
upload su object storage — senza restano su disco: ok solo
single-instance), `LOG_FORMAT=json`, `BACKUP_ALERT_EMAIL`.

**Rotazione `JWT_SECRET_KEY`**: generare nuova chiave → deploy → tutte
le sessioni admin/customer decadono (re-login; il Passaporto usa token
propri in DB e sopravvive). Ruotare: a sospetto compromissione, a
offboarding di chi aveva accesso al server, o ogni 12 mesi.

## 3 · Email — Brevo + DNS 【founder】

- [ ] Account Brevo → chiave API LIVE in `.env`.
- [ ] In Brevo: aggiungere dominio `aurya.life` → copiare i record
      DKIM/SPF proposti → incollarli in Cloudflare DNS.
- [ ] `_dmarc` TXT: `v=DMARC1; p=quarantine; rua=mailto:info@aurya.life`.
- [ ] Cloudflare Email Routing: `info@` e `hello@` → la tua Gmail.
- [ ] Test di resa (checklist in docs/EMAILS.md §Verifica): 5 email
      campione a Gmail/Apple Mail/Outlook — controllare anche che il
      logo (https://aurya.life/logo-aurya-128.png) si veda.

## 4 · Stripe LIVE 【founder】

- [ ] Attivare l'account LIVE + Connect (stesse impostazioni del test:
      direct charges, fee per piano).
- [ ] Webhook LIVE: endpoint `https://aurya.life/api/billing/webhooks`,
      stessi eventi del test → copiare il signing secret in `.env`.
- [ ] Onboarding Connect di UN operatore vero prima del lancio.

## 5 · Deploy applicativo

- [ ] Backend: `pip install -r requirements.txt` (python 3.12+),
      `uvicorn server:app --host 127.0.0.1 --port 8000 --workers 2`
      sotto systemd (restart=always).
- [ ] Frontend: `pnpm install && pnpm build` con
      `REACT_APP_BACKEND_URL=https://aurya.life` → servire `build/`.
- [ ] Primo boot: gli indici si creano da soli; il seed demo NON va
      eseguito in prod.
- [ ] `python scripts/backfill_geo.py` (una volta: geocoding dei ritiri
      esistenti — rispetta il rate limit Nominatim, può metterci minuti).
- [ ] Backup: cron di `deploy/backup.sh` (age, retention 30gg — guida
      completa in docs/operations/backup-recovery.md) e UNA prova di
      RESTORE su DB vuoto.

## 6 · Smoke test post-deploy (10 minuti)

- [ ] `curl https://aurya.life/api/health/live` → ok; `/ready` → ok.
- [ ] `/metrics` senza token → 401; con token → testo Prometheus.
- [ ] Header presenti: `strict-transport-security`, `x-content-type-options`.
- [ ] Giro completo dal TELEFONO: /ritiri → landing → checkout con
      caparra vera (carta reale, importo piccolo) → email ricevute
      (conferma + OTP Passaporto) → biglietto → rimborso dal pannello.
- [ ] Login admin, lingua UI, creazione di un prodotto di prova.
- [ ] `/termini`, `/privacy`, `/sub-processors` raggiungibili dal footer.

## 7 · Dopo il lancio

- [ ] UptimeRobot (gratis) su `/api/health/live` e `/api/health/ready`.
- [ ] Sentry: alert email sugli error rate.
- [ ] `pip-audit` mensile (o GitHub Dependabot sul repo remoto).
- [ ] Rinnovo dominio Porkbun: auto-renew ON.

## Non nel perimetro di questa checklist

Contenuti legali definitivi (bozze da rivedere con un legale — R1),
foto vere dei ritiri, pagina piani pubblica coi prezzi finali (decisioni
founder, tracciate in PRODUCTION_PLAN.md §Cosa manca al PRODOTTO).
