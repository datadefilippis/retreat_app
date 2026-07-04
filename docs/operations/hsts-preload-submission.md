# HSTS Preload List Submission Procedure

> Submission canonical procedure per inserire `afianco.ch` nella
> [HSTS Preload List](https://hstspreload.org) hardcoded in Chrome,
> Firefox, Safari, Edge. Effetto: **i browser rifiutano HTTP per
> afianco.ch + tutti i subdomain INSTANT al primo visit** (no need
> per HTTPS first request).
> **Track O Step 5.3.**
>
> **Owner:** davide@afianco.ch
> **Effort:** ~10 min submission + 6-12 settimane ship in browser
> **Risk profile:** **PERMANENTE** — rimozione ≥ 6 mesi turnaround
> + qualsiasi subdomain non TLS-ready dopo submission = browser error
> per quel subdomain.

---

## ⚠️ Read this FIRST — irreversibility warning

HSTS Preload List submission e' **quasi-permanente**:

1. Chrome, Firefox, Safari, Edge shipano la lista hardcoded nel
   browser binary
2. Rimozione richiesta richiede:
   - Submit removal request a hstspreload.org
   - Aspettare next browser major version (~3 mesi each)
   - User aggiorna browser (~3+ mesi adoption)
   - **Total: 6-12 mesi minimum** prima che il removal sia effettivo

Conseguenza: ogni subdomain `*.afianco.ch` che NON e' TLS-ready
**dopo** la submission diventerà **inaccessibile** per gli utenti
con browser preload-aware. NESSUN fallback.

→ **NON SUBMITTARE** se non sei 100% sicuro che tutti i subdomain
servono HTTPS validamente.

---

## Quick reference

| Step | Action | Effort |
|---|---|---|
| **1** | Pre-submit checklist (TLS validation tutti subdomain) | 30 min |
| **2** | Soak: header servito coerentemente 1 settimana | 7 giorni |
| **3** | Submission form hstspreload.org | 10 min |
| **4** | Pending review (manuale Google Chrome team) | ~1 settimana |
| **5** | Approved → ship in next Chrome stable | 6 settimane |
| **6** | Propagation a Firefox, Safari, Edge | 3-6 mesi |

---

## Pre-submit checklist

Esegui PRIMA di submittare. Failing one = submission rejected (best
case) o irreversible mess (worst case).

### Check 1 — HSTS header config correct

Verifica nginx config:

```bash
# Sul VPS:
docker exec ms-nginx cat /etc/nginx/conf.d/nginx.conf | grep -i strict-transport
```

**Expected output:**
```
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

3 directives MANDATORY per hstspreload.org acceptance:
- `max-age=31536000` (1 year minimum)
- `includeSubDomains` (cover tutti i subdomain)
- `preload` (declared willingness)

### Check 2 — Header servito da apex domain

```bash
curl -sI https://afianco.ch/ | grep -i strict-transport
# Expected: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

Se header missing o malformato → fix nginx config + reload + retry.

### Check 3 — Redirect HTTP → HTTPS apex

```bash
curl -sI http://afianco.ch/ | head -5
# Expected: HTTP/1.1 301 Moved Permanently
# Location: https://afianco.ch/
```

HSTS preload requires explicit 301 redirect chain HTTP → HTTPS apex.

### Check 4 — Subdomain inventory

**CRITICAL** — questo e' il pre-check che PIU' SPESSO sbaglia + causa
disastro post-submit. Lista TUTTI i subdomain esistenti:

```bash
# DNS records query:
dig +short afianco.ch any
dig +short www.afianco.ch
dig +short admin.afianco.ch
dig +short api.afianco.ch
dig +short app.afianco.ch
dig +short mail.afianco.ch
dig +short cdn.afianco.ch
# ... aggiungi qualsiasi altro subdomain che hai mai creato
```

**Per OGNI subdomain found:**
1. Verifica TLS cert valido (`curl -sI https://<sub>.afianco.ch/`)
2. Se return error / cert mismatch → BLOCKER pre-submit
3. Fix prima di procedere (renew cert, add cert SAN, ecc.)

GoDaddy DNS dashboard:
- `https://dcc.godaddy.com/manage/dns?domainName=afianco.ch`
- Review ALL A/CNAME/MX records → identify subdomain

### Check 5 — Wildcard cert covers (if used)

Se usi wildcard cert `*.afianco.ch`:
- Verifica include sia `afianco.ch` (apex) sia `*.afianco.ch`
- Verifica scadenza > 6 mesi (Let's Encrypt auto-renew via certbot)

Se NON usi wildcard:
- Per OGNI subdomain serve cert valido individual
- Setup certbot per ognuno

### Check 6 — Static site verifier

Usa il tool ufficiale:

```
https://hstspreload.org/?domain=afianco.ch
```

Il tool fa runtime check di tutti i criteri. **Risultato deve essere
ALL GREEN** prima di submittare. Se rosso → fix + richeck.

---

## Soak window (1 settimana)

Dopo che pre-checks tutti pass, lascia header in produzione per
**almeno 7 giorni consecutivi** SENZA rimuoverlo o downgradare.

Razionale: hstspreload.org review team puo' randomly check il sito
durante la review. Se header missing in qualche momento → reject.

Monitor durante soak:
- UptimeRobot deve continuare a fire 5/5 (vedi `uptime-monitoring.md`)
- Sentry: zero new TLS-related issue
- Manuale: 1 curl al giorno → verify header presente

---

## Submission procedure

### Step 1 — Final verifier check

```
https://hstspreload.org/?domain=afianco.ch
```

ALL GREEN obbligatorio. Se anche un solo warning → STOP, fix, retry.

### Step 2 — Submit form

1. Vai su https://hstspreload.org/
2. Inserisci domain `afianco.ch`
3. Click **"Check eligibility"**
4. Read TUTTI i warning sotto il form (anche se status e' eligible)
5. Tick TUTTE le checkbox di confirmation:
   - [ ] HTTPS served on all subdomains
   - [ ] HSTS header on all subdomains (or wildcard cert)
   - [ ] HTTP 301 redirect to HTTPS works
   - [ ] Understood removal procedure
6. Click **"Submit afianco.ch to the HSTS preload list"**

### Step 3 — Confirmation

Il submission e' confirmed via email a webmaster@afianco.ch o
admin@afianco.ch (operator email di GoDaddy registrar contact).

**Salva il submission ID/timestamp** in `incidents.md` per future
reference (especially se needed per removal request).

---

## Post-submission timeline

| Phase | Duration | What happens |
|---|---|---|
| **Pending** | ~1 settimana | Chromium team manual review |
| **Approved** | Email confirmation | Added to Chromium HSTS list source |
| **Ship Chrome** | ~6 settimane | Next Chrome stable release contains list |
| **Ship Firefox** | ~3 mesi | Mozilla picks up from Chromium sync |
| **Ship Safari** | ~3-6 mesi | Apple sync (slower cadence) |
| **Ship Edge** | ~6 settimane | Auto with Chromium upstream |

Status check anytime:
```
https://hstspreload.org/?domain=afianco.ch
```
Status field shows:
- `Pending` → in review
- `Preloaded` → in current Chromium HSTS list
- `Preloading` → committed but not yet shipped

---

## Verification post-ship

Dopo 6+ settimane (Chrome released):

### Method 1 — Chrome devtools

1. Chrome → Settings → Privacy and Security → Security
2. Click "Manage certificates" → tab "HSTS/PKP" (chrome://net-internals/#hsts)
3. Query domain: `afianco.ch`
4. Expected: `static_sts_domain` field shows entry with `force_https`

### Method 2 — Curl test from clean browser profile

```bash
# Open Chrome con --user-data-dir=/tmp/test-profile (no cache)
# Visit http://afianco.ch (HTTP, not HTTPS)
# Expected: browser INSTANT redirect a HTTPS senza prima HTTP request
# Network tab DevTools: zero HTTP request mai sent
```

Se HTTPS upgrade NON instant → preload non ancora attivo per la tua
Chrome version. Aspetta update.

---

## Removal procedure (HOPE YOU NEVER NEED IT)

Se devi rimuovere afianco.ch dal preload list:

1. **Pre-rimozione**: aggiorna nginx config DOWNGRADE
   ```
   Strict-Transport-Security: max-age=0
   ```
   Questo dice ai browser "remove HSTS state" — funziona PRIMA del
   preload effect.

2. **Soak**: lascia max-age=0 per 1 settimana (hstspreload.org
   review requirement).

3. **Submission form removal**:
   ```
   https://hstspreload.org/removal/?domain=afianco.ch
   ```

4. **Wait 6-12 mesi** per ship through Chrome/Firefox/Safari major
   versions.

5. **During wait**: nessun browser preload-aware permette HTTP per
   afianco.ch. **Mitigation: nothing.** Customer experience compromised.

→ **Ripeto: NON SUBMITTARE** se hai dubbi sulla TLS readiness di
qualche subdomain.

---

## Maintenance schedule

| Cadenza | Task |
|---|---|
| **Mensile** | Verifica TLS cert renewal automatic per tutti subdomain |
| **Pre nuovo subdomain** | Setup TLS cert PRIMA di pubblicarlo (subdomain senza HTTPS post-preload = inaccessibile) |
| **Trimestrale** | Check status hstspreload.org per verify preloaded state |
| **Cert expiry** | Setup alert UptimeRobot SSL monitor (gia' done in O3.4) |

---

## Riferimenti

- `security-headers.md` — full security headers reference
- `uptime-monitoring.md` — SSL cert expiry monitoring (UptimeRobot O3.4)
- `incident-response.md` — playbook se HSTS causa subdomain outage
- `deploy/nginx/nginx.conf` — header configuration source
- HSTS Preload Tool: https://hstspreload.org/
- RFC 6797 — HSTS spec: https://datatracker.ietf.org/doc/html/rfc6797
- Chromium preload list source: https://chromium.googlesource.com/chromium/src/+/main/net/http/transport_security_state_static.json

---

**Last reviewed:** 2026-05-29
**Submission status:** NOT YET SUBMITTED (awaiting operator decision post pre-checks)
