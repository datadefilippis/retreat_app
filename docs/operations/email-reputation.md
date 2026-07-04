# Email Reputation Setup (SPF + DKIM + DMARC)

> DNS config per autenticare le email transazionali inviate via Brevo
> SMTP da `afianco.ch`. Senza SPF + DKIM, le email finiscono in spam.
> **Track L Step 3** — ✅ **ALREADY COMPLETE** (audit 2026-05-29).

---

## Status attuale (verified 2026-05-29 via DNS lookup)

| Record | Status | Value |
|---|---|---|
| **SPF** | ✅ ATTIVO STRICT | `v=spf1 include:spf.brevo.com include:secureserver.net -all` |
| **DKIM brevo1** | ✅ ATTIVO | CNAME `brevo1._domainkey.afianco.ch` → `b1.afianco-ch.dkim.brevo.com` |
| **DKIM brevo2** | ✅ ATTIVO | CNAME `brevo2._domainkey.afianco.ch` → `b2.afianco-ch.dkim.brevo.com` |
| **DMARC** | ✅ ATTIVO (p=none monitoring) | `v=DMARC1; p=none; adkim=r; aspf=r; rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net` |
| **MX** | ✅ Microsoft 365 inbox | `afianco-ch.mail.protection.outlook.com` |

**Verify command** (anytime):
```bash
dig +short txt afianco.ch | grep spf
dig +short cname brevo1._domainkey.afianco.ch
dig +short txt _dmarc.afianco.ch
```

## Possibili miglioramenti V2 (non blocker)

- **DMARC `p=none` → `p=quarantine`**: dopo 1-2 settimane di verify dei
  report aggregati senza alert anomali, upgrade per proteggere brand
  reputation contro spoofing
- **`rua=mailto:dmarc@afianco.ch`**: aggiungere proprio alias per
  ricevere report direttamente (oggi vanno a Brevo + GoDaddy default)
- **SPF Microsoft 365**: se attivi invio email anche da Outlook/M365,
  aggiungere `include:spf.protection.outlook.com` al SPF esistente

---

## (Setup procedure originale — solo se DNS si rompe / nuovo dominio)

---

## Why this matters

Le email transazionali (signup confirm, password reset, order confirm)
sono **inviate da Brevo** (provider SMTP) ma con `From: noreply@afianco.app`.

Senza DNS authentication, i mail provider (Gmail, Outlook, Yahoo) vedono:
- **From**: noreply@afianco.app (claim)
- **Sent by**: brevo.com SMTP server (reality)

→ Mismatch → spoofing detection → **spam folder o reject totale**.

Soluzione: 3 record DNS che autorizzano Brevo a inviare per conto di
`afianco.app`:

1. **SPF** — autorizza Brevo come sender IP range
2. **DKIM** — Brevo firma ogni email con private key, riceventi verificano via public key in DNS
3. **DMARC** — policy che dice "se SPF o DKIM falliscono, fai X"

---

## Setup procedure (2 ore one-shot)

### Pre-requisiti

- Accesso DNS del dominio `afianco.app` (provider tipo Cloudflare, GoDaddy, Aruba, OVH)
- Accesso Brevo dashboard: https://app.brevo.com/senders/domains

### Step 1 — SPF record (10 min)

**Cosa fa**: dichiara "questi IP sono autorizzati a inviare email per `afianco.app`".

**DNS record da aggiungere**:

| Type | Host/Name | Value | TTL |
|---|---|---|---|
| `TXT` | `@` (o `afianco.app`) | `v=spf1 include:spf.brevo.com ~all` | 3600 |

⚠️ **Se hai GIA' un SPF record** (es. per Google Workspace), **NON
duplicare**. Aggiungi `include:spf.brevo.com` all'esistente:

```
v=spf1 include:_spf.google.com include:spf.brevo.com ~all
```

Solo UN SPF record per dominio (RFC 7208). Più records = configurazione
invalida + reject.

**Verifica** dopo propagazione (5-30 min):
```bash
dig +short txt afianco.app | grep spf
# Atteso: "v=spf1 include:spf.brevo.com ~all"

# Oppure
nslookup -type=txt afianco.app
```

Online check: https://mxtoolbox.com/spf.aspx → inserisci `afianco.app`
→ verde se valid.

### Step 2 — DKIM record (15 min)

**Cosa fa**: Brevo firma ogni email con private key. Receiver verifica
firma usando public key pubblicata in DNS.

**Procedura**:

1. Vai su https://app.brevo.com/senders/domains
2. Click "Add a domain" → inserisci `afianco.app`
3. Brevo genera **3 CNAME record** specifici. Esempio (i valori reali
   saranno diversi):

| Type | Host/Name | Value | TTL |
|---|---|---|---|
| `CNAME` | `mail._domainkey.afianco.app` | `mail.domainkey.uXXXXXXXX.dkim.brevo.com` | 3600 |
| `CNAME` | `mail2._domainkey.afianco.app` | `mail2.domainkey.uXXXXXXXX.dkim.brevo.com` | 3600 |
| `CNAME` | `mail3._domainkey.afianco.app` | `mail3.domainkey.uXXXXXXXX.dkim.brevo.com` | 3600 |

4. Aggiungi i 3 CNAME al DNS provider
5. Torna in Brevo dashboard → click "Authenticate" → Brevo verifica
6. ✅ Status "Authenticated" = DKIM funzionante

**Verifica** dopo propagazione:
```bash
dig +short cname mail._domainkey.afianco.app
# Atteso: mail.domainkey.uXXXXXXXX.dkim.brevo.com
```

### Step 3 — DMARC record (10 min)

**Cosa fa**: dichiara cosa fare se SPF o DKIM falliscono + indirizzo
dove ricevere report aggregati (alert su tentativi spoofing).

**Inizia con policy soft (monitoring only)** per 1-2 settimane:

| Type | Host/Name | Value | TTL |
|---|---|---|---|
| `TXT` | `_dmarc.afianco.app` | `v=DMARC1; p=none; rua=mailto:dmarc@afianco.app; ruf=mailto:dmarc@afianco.app; fo=1` | 3600 |

- `p=none` → solo report, no enforcement (safe per iniziale rollout)
- `rua=` → aggregate report (daily summaries)
- `ruf=` → forensic report (sample of failures)
- `fo=1` → tutti i forensic reports (anche solo SPF fail)

⚠️ **Crea l'alias email `dmarc@afianco.app`** prima di pubblicare il
record (es. forward a `davidedefilippis94@gmail.com`).

**Dopo 1-2 settimane** di clean monitoring (zero spoofing alerts in
inbox), upgrade a quarantine:

```
v=DMARC1; p=quarantine; rua=mailto:dmarc@afianco.app
```

`p=quarantine` → email non autenticate vanno in spam (no reject totale).

**Production-ready (post pilot)**: upgrade a `p=reject`:

```
v=DMARC1; p=reject; rua=mailto:dmarc@afianco.app; pct=100
```

`p=reject` → email non autenticate rifiutate totalmente. Massima
protezione contro spoofing del tuo brand.

**Verifica** dopo propagazione:
```bash
dig +short txt _dmarc.afianco.app
# Atteso: "v=DMARC1; p=none; rua=mailto:dmarc@afianco.app..."
```

Online check: https://mxtoolbox.com/dmarc.aspx

---

## Verification checklist

Una volta tutti i 3 record live + propagati:

- [ ] `dig +short txt afianco.app | grep spf` ritorna SPF con `spf.brevo.com`
- [ ] `dig +short cname mail._domainkey.afianco.app` ritorna `*.dkim.brevo.com`
- [ ] `dig +short txt _dmarc.afianco.app` ritorna DMARC policy
- [ ] Brevo dashboard mostra dominio "Authenticated" (verde)
- [ ] https://mxtoolbox.com/SuperTool.aspx?action=mx%3aafianco.app → verde
- [ ] Test email: signup customer test → email arriva in **Inbox** (NON spam)
- [ ] Test con https://www.mail-tester.com — score >= 9/10

---

## Common pitfalls

### "SPF record sovrascritto"
Se il dominio aveva già SPF per Google/Microsoft365, **NON aggiungere
un secondo TXT** — fonderli in unico record:
```
v=spf1 include:_spf.google.com include:spf.brevo.com ~all
```

### "DKIM CNAME points to wrong domain"
Verifica che i 3 CNAME punti esattamente al valore che Brevo dashboard
mostra (case-sensitive, no trailing dot per alcuni DNS provider).

### "DMARC report email overflow"
`p=none` su un dominio attivo genera 1-10 email/day. Setup un filtro
Gmail "from:dmarc-noreply OR from:dmarcreports" → label `DMARC` → archive
automaticamente (review settimanale invece di continuo).

### "Email arriva ancora in spam dopo setup"
Cause comuni:
1. DNS propagazione non completa (aspettare 24-48h)
2. Manca DKIM CNAME (verifica TUTTI e 3)
3. SPF `~all` invece di `-all` → mail provider trattano come "soft fail"
   (OK per fase rollout, upgrade a `-all` dopo 1 mese clean)
4. Reputazione brand nuova → graduale (Gmail/Outlook richiedono settimane
   di clean send per uscire dal "low reputation" pool)

---

## Maintenance ongoing

### Weekly
- Check inbox `dmarc@afianco.app` per alert anomali (spike di failures = sospetto spoofing attacco)

### Monthly
- mxtoolbox.com → verify SPF + DKIM + DMARC still valid
- Brevo dashboard → check bounce rate (dovrebbe essere < 2%)

### Annual
- Review DMARC policy: upgrade `p=none` → `p=quarantine` → `p=reject`
  (vedi sezione Step 3)
- Rotate DKIM key se Brevo lo richiede (rare)

---

## Cross-references

- [`docs/operations/secrets-rotation.md`](secrets-rotation.md) — `BREVO_API_KEY` rotation
- [`docs/operations/incident-response.md`](incident-response.md) — se sospetto spoofing del tuo brand
- [`backend/services/email_service.py`](../../backend/services/email_service.py) — Brevo SMTP integration code
- [`backend/.env.example`](../../backend/.env.example) — Brevo env vars

---

## External resources

- Brevo DKIM/SPF setup: https://help.brevo.com/hc/en-us/articles/360019559099
- SPF syntax: https://datatracker.ietf.org/doc/html/rfc7208
- DKIM RFC: https://datatracker.ietf.org/doc/html/rfc6376
- DMARC RFC: https://datatracker.ietf.org/doc/html/rfc7489
- Online tester: https://www.mail-tester.com

---

_Last updated: 2026-05-29 — Track L Step 3_
