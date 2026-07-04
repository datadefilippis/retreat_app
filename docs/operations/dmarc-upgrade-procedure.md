# DMARC Upgrade Procedure — `p=none` → `p=quarantine` → `p=reject`

> Procedura canonical per stringere la DMARC policy da monitoring
> (`p=none`) ad enforcement strict (`p=reject`) durante l'open beta.
> **Track O Step 5.2.**
>
> **Owner:** davide@afianco.ch
> **Total timeline:** 6-8 settimane (gradual rollout con soak windows)
> **Risk profile:** ALTO se non graduale — `p=reject` con misconfig
> = bounce TUTTE le email transazionali → user lockout cascata.

---

## Quick reference

| Phase | Policy | Soak | Goal |
|---|---|---|---|
| **Current** | `p=none; pct=100` (monitoring) | n/a | Baseline metrics |
| **P1** | `p=quarantine; pct=10` | 7 giorni | Validate sample failure rate |
| **P2** | `p=quarantine; pct=50` | 7 giorni | Half traffic quarantine OK |
| **P3** | `p=quarantine; pct=100` | 14 giorni | Full quarantine soak |
| **P4** | `p=reject; pct=10` | 7 giorni | Start reject sample |
| **P5** | `p=reject; pct=50` | 7 giorni | Half reject |
| **P6** | `p=reject; pct=100` | DONE | Strict enforce |

**Total:** ~42 giorni minimum (6 settimane). Skippa fase se report
mostrano zero anomalie + accelera. NON skippare se report indicano
qualsiasi DKIM/SPF fail anche minor.

---

## Why graduate vs jump

DMARC `p=reject` immediato = se hai 1 single edge case di email
legittima che fallisce SPF o DKIM (es. mail-forwarding via mailing
list, third-party sender non yet whitelisted), QUELLA email viene
**rifiutata silently** dai receiver. User non riceve verification
email → locked out → support nightmare.

`pct=N` parameter (RFC 7489 §6.6.4): solo N% del traffic e' soggetto
alla policy enforce. Il resto e' trattato come `p=none` (monitoring).
Permette ramp-up controllato.

`p=quarantine` (intermediate): email failing → spam folder, NOT
rejected. User puo' ancora recover manualmente. Safer than `p=reject`
durante validation.

---

## Pre-checks (BEFORE Phase 1)

Esegui DOPO almeno **14 giorni di p=none soak** in produzione +
**5+ DMARC report aggregati ricevuti**.

### Check 1 — DKIM signing rate

```bash
# Estrai da DMARC report XML (Brevo invia daily a rua@dmarc.brevo.com)
# Conta: % di email con DKIM result=pass per dominio afianco.ch
# TARGET: >99.5%
```

Se DKIM pass rate < 99.5%: investiga PRIMA di procedere. Cause comuni:
- Email body modified post-signing (es. mail proxy che injects footer)
- Key rotation senza update DNS
- Brevo DKIM key issue → contact support

### Check 2 — SPF alignment rate

```bash
# Target: >99% di email con SPF result=pass + alignment=pass
```

Se SPF fail rate alto: identifica IP non in `include:spf.brevo.com`.
Se legittimi (es. Microsoft 365 inviato anche da Outlook): aggiungi
al SPF record prima di procedere.

### Check 3 — Zero anomalous senders

DMARC report mostra "source IP" per ogni email failing. Verifica
che NESSUN IP suspicious stia provando di spoofare afianco.ch.
Se trovi spoof attempts: contact ISP abuse + procedi (DMARC reject
li rifiuterà).

### Check 4 — Setup ricezione report

Aggiungi `rua=mailto:dmarc@afianco.ch` al record DMARC corrente:

```
Current:  v=DMARC1; p=none; adkim=r; aspf=r; rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net
Updated:  v=DMARC1; p=none; adkim=r; aspf=r; rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

Aspetta 24h propagation + verifica che dmarc@afianco.ch riceva primi
report.

---

## Phase 1 — `p=quarantine; pct=10`

### DNS Change

GoDaddy DNS Manager → TXT record `_dmarc.afianco.ch`:

```
v=DMARC1; p=quarantine; pct=10; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

### Verify (entro 1h)

```bash
dig +short txt _dmarc.afianco.ch
# Expected: include "p=quarantine; pct=10"
```

### Soak: 7 giorni

Durante questo periodo:
- Monitor inbox dmarc@afianco.ch — leggi i daily report
- Monitor Sentry: alert su email_send failures sopra baseline
- Monitor Grafana: `email_sends_total{status="http_error"}` rate
- Test signup endpoint: verifica che verification email arriva (Brevo,
  Gmail, Outlook personal)

### Checkpoint Phase 1

Pass conditions:
- ✅ Zero customer support ticket "non ricevo email"
- ✅ `email_sends_total{status="success"}` rate ≥ pre-change baseline
- ✅ DMARC report mostra <1% delle nostre email quarantined erroneamente

Se PASS → procedi Phase 2.
Se FAIL → vedi "Rollback" sotto.

---

## Phase 2 — `p=quarantine; pct=50`

### DNS Change

```
v=DMARC1; p=quarantine; pct=50; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

### Soak: 7 giorni

Same monitoring as Phase 1.

### Checkpoint Phase 2

Same pass conditions. Se PASS → Phase 3.

---

## Phase 3 — `p=quarantine; pct=100`

### DNS Change

```
v=DMARC1; p=quarantine; pct=100; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

### Soak: **14 giorni** (extended)

Phase 3 = full quarantine — ogni email failing va in spam folder. Soak
piu' lungo perche':
- Customer non controlla spam quotidianamente → ticket delay
- Edge case rari (es. specific corporate mail server config) emergono
  solo dopo settimane

### Checkpoint Phase 3

Pass conditions (PIU' STRICT):
- ✅ Zero customer support ticket "non ricevo email" **per 14 giorni**
- ✅ `email_sends_total{status="success"}` rate stable
- ✅ DMARC report mostra DKIM+SPF pass rate ≥ 99.5%

Se PASS → procedi Phase 4 (`p=reject`).

---

## Phase 4 — `p=reject; pct=10`

⚠️ **CRITICAL JUMP** — passa da quarantine (spam folder, recoverable)
a reject (email destroyed, no recovery). Solo se Phase 3 e' stato
PERFETTO per 14 giorni.

### DNS Change

```
v=DMARC1; p=reject; pct=10; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

### Soak: 7 giorni

Vigilance extra:
- Daily check di dmarc@afianco.ch report
- Daily check Sentry email_send failures
- Daily check customer support inbox

### Checkpoint Phase 4

Pass conditions:
- ✅ DMARC report: REJECT count rimane bassissimo (<0.1%
  delle email outbound). 0.1% di 50 email/giorno = 1 reject/20 giorni.
  Sospetto se > 0.5%.
- ✅ Zero customer ticket

Se PASS → Phase 5.

---

## Phase 5 — `p=reject; pct=50`

Same procedure as Phase 4, soak 7 giorni.

---

## Phase 6 — `p=reject; pct=100` (FINAL)

### DNS Change

```
v=DMARC1; p=reject; pct=100; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

Oppure (equivalente — `pct` default = 100):

```
v=DMARC1; p=reject; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

**FINISHED.** Email che falliscono DMARC = rejected by receiver.
Brand protection MASSIMA contro spoofing.

---

## Rollback procedure

Qualsiasi phase, se checkpoint FAIL:

### Step 1 — Immediate rollback

Cambia DNS record DMARC al previous phase value (o `p=none` se
incertezza):

```
v=DMARC1; p=none; adkim=r; aspf=r;
rua=mailto:rua@dmarc.brevo.com,mailto:dmarc_rua@onsecureserver.net,mailto:dmarc@afianco.ch
```

DNS propagation: 5min - 1h (TTL=3600).

### Step 2 — Investigate

Identifica root cause via DMARC report XML:
- Quali IP sender failing?
- DKIM o SPF a causa del fail?
- Pattern: random vs systematic?

### Step 3 — Fix

Cause comuni + fix:
- Brevo DKIM key issue → contact Brevo support, attendi fix
- New email sender added (es. Outlook 365) → aggiungi al SPF
- Email modified in transit (es. mailing list footer) → identifica
  forwarder + chiedere DMARC-aware forwarding

### Step 4 — Re-attempt phase

Solo dopo 7 giorni di p=none soak fresh → retry phase precedente.

---

## DMARC report parsing helper

Setup IMAP fetch + parse XML report (V2 — automation):

```python
# Pseudocodice futuro
# Per ora: leggi manualmente dmarc@afianco.ch inbox
# Reports: 1/day per receiver (Gmail, Microsoft, Yahoo separati)
# Files: .xml.gz attached
# Parse: <record> per source IP, count, DKIM result, SPF result
```

Tools online (drag-drop XML):
- https://www.dmarcian.com/dmarc-xml/
- https://easydmarc.com/tools/dmarc-xml-parser

---

## Maintenance schedule

| Cadenza | Task |
|---|---|
| **Setup** | Aggiungere mailto:dmarc@afianco.ch al rua list (Check 4) |
| **Pre-Phase 1** | 14 giorni p=none soak + verify 4 checks |
| **Settimanale** | Durante upgrade phases: read DMARC report + verify checkpoint |
| **Mensile** | Anche post-completamento: DMARC report inspection per
spoof attempts detect |

---

## Riferimenti

- `email-reputation.md` — baseline SPF/DKIM/DMARC setup
- `incident-response.md` — playbook se DMARC reject causa outage email
- `sentry-alert-rules.md` — alert su email_send failures (P1 alert)
- `uptime-monitoring.md` — UptimeRobot non monitora email delivery
- RFC 7489 — DMARC spec
- DMARC tutorial: https://dmarc.org/overview/

---

**Last reviewed:** 2026-05-29
**Next review:** Phase 1 execution date (TBD by operatore)
