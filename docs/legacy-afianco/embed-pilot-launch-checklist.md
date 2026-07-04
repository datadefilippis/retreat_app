# AFianco Embed Widget — Pilot Launch Checklist

> **Target**: Primo merchant pilota integrato live entro **15 giugno 2026**.
> **Goal**: validare end-to-end UX su traffic reale + 1 ciclo settimanale di
> ordini reali prima di GA marketing.

## Stato attuale (2026-06-05)

| Track | Status | Note |
|---|---|---|
| E1 — API contract consolidation | ✅ Done | v1 stable + versioning protocol |
| E2 — Type-aware buy flow | ✅ Done | 17 web components, 7 product types |
| E3 — Critical UX fixes | ✅ Done | Cart auto-close, z-index defense, coupon dry-run |
| E4 — Conversion completeness | ✅ Done | Coupon, shipping, design tokens, profile, i18n |
| E5 — UX parity gaps | ✅ Done | Search, ICS, forgot pwd, analytics, maps |
| E6 — UX symmetry audit | ✅ Done | 97% parita confermata, 3 deferred V2 |
| E7.1 — Landing pages deep-link | ⏭️ Skipped | Low ROI per pilot, deferred V2 |
| E7.2 — Documentation suite | ✅ Done | 3 docs (integration, onboarding, troubleshooting) |
| E7.3 — Pilot prep | 🔄 In progress | Questo documento |

**Sentinel tests**: 534/534 passing (backend invariants security).
**Bundle size**: 426 KB raw / 85 KB gzip (62 moduli, 0 errori TS).
**Parity storefront vs widget**: ~97% (3 deferred items per V2).

---

## Pre-launch checklist

### Backend infra

- [ ] **Database backup snapshot** preso entro 4h prima launch
- [ ] **Sentry alert rules** attive:
  - [ ] `[P2] Embed-SDK error spike` (>50/h)
  - [ ] `[P1] Embed checkout failure` (>5/h)
  - [ ] `[P1] Embed CORS rejection spike` (>20/h da stesso origin)
- [ ] **Rate limits configurati** in produzione:
  - [ ] `/init/{slug}` 60/min per (IP, slug)
  - [ ] `/products/{slug}` 60/min
  - [ ] `/checkout/start` 10/min
  - [ ] `/coupons/validate/{slug}` 30/min
- [ ] **MongoDB indexes**:
  - [ ] `customers_collection { email: 1, organization_id: 1 }`
  - [ ] `orders_collection { customer_account_id: 1, organization_id: 1, status: 1 }`
  - [ ] `coupons_collection { code: 1, organization_id: 1 }`
  - [ ] `bookings_collection { customer_account_id: 1, organization_id: 1 }`
- [ ] **Stripe production keys** configurate per il merchant pilot
- [ ] **Webhook Stripe** registrato + verificato (`/api/webhooks/stripe`)
- [ ] **Email transport** (SendGrid/Mailgun) verificato per:
  - [ ] Order confirmation
  - [ ] Password reset
  - [ ] GDPR erasure confirm
  - [ ] Booking confirm + ICS
- [ ] **Bunny Stream account** attivo (se merchant ha videocorsi)

### Frontend / CDN

- [ ] **Bundle deployato** a `https://app.afianco.ch/embed/v1/afianco-embed.es.js`
- [ ] **Cache-Control headers** corretti:
  - [ ] Bundle JS: `public, max-age=86400, immutable` (con hash version)
  - [ ] API responses: `public, max-age=300` + ETag
- [ ] **Cloudflare**:
  - [ ] CORS preflight cached
  - [ ] Geo-routing EU-first
  - [ ] DDoS protection attivo
- [ ] **CDN failover** tested (origin down → cache serve last-known-good)
- [ ] **Source maps** uploadati su Sentry per stack traces leggibili

### Sentinel / regression

- [ ] `pytest backend/tests/test_invariants_security.py` — **534/534 passing**
- [ ] `npm run build` apps/embed-sdk — **0 errori TS**
- [ ] **Manual smoke test** su `embed-local-test.html`:
  - [ ] Init load
  - [ ] Category navigation
  - [ ] Search bar
  - [ ] Add to cart (physical + service + event_ticket)
  - [ ] Checkout end-to-end (test Stripe key)
  - [ ] Customer signup inline
  - [ ] Login + portal access
  - [ ] Profile edit + password change
  - [ ] Language switch IT → EN
- [ ] **Cross-browser test** (Chrome, Safari, Firefox latest)
- [ ] **Mobile test** (iOS Safari, Android Chrome)

### Merchant pilot setup

- [ ] **Slug merchant** assegnato + verificato no conflict
- [ ] **`allowed_origins`** configurato per il dominio del merchant
- [ ] **Stripe Connect** completato (onboarding KYC)
- [ ] **Branding** configurato nell'admin:
  - [ ] Logo
  - [ ] `brand_color` + `brand_color_text`
  - [ ] Design tokens (font_family, border_radius, density)
- [ ] **Catalogo** popolato:
  - [ ] Min 5 prodotti pubblicati
  - [ ] Categorie create
  - [ ] Immagini ottimizzate (<200KB ciascuna)
- [ ] **Lingue attive**: almeno `it` (default) + `en` per UX test
- [ ] **Shipping options** create (se ha prodotti physical):
  - [ ] Standard + Express
  - [ ] `free_shipping_threshold` (opzionale)
- [ ] **Coupon di lancio** creato (es. `PILOT10` -10% per il pilot)

---

## Pilot merchant onboarding script

### Sessione 1 — Tech onboarding (30 min)

1. **Welcome + obiettivi pilot** (5')
2. **Walk-through admin AFianco** (10'):
   - Login → dashboard
   - Store settings → branding
   - Catalogo → publish workflow
   - Pagamenti → Stripe Connect
3. **Embed integration live** (10'):
   - Copy snippet da "Condividi" modale
   - Paste nel CMS del merchant (es. WordPress block)
   - Save → reload → verifica widget visibile
4. **Test ordine end-to-end** (5'):
   - Customer test → add to cart → checkout
   - Verifica order in admin
   - Verifica email confirm ricevuta

### Sessione 2 — Customer support training (20 min)

1. **Dashboard ordini** (5'): come filtrare, esportare, refundare
2. **Customer portal** (5'): cosa vede il cliente post-acquisto
3. **Troubleshooting common cases** (10'):
   - Customer "non ricevo email" → check spam + admin re-send
   - Customer "pagamento fallito" → check Stripe dashboard
   - "Coupon non funziona" → admin coupon settings

### Sessione 3 — Go-live (15 min)

1. Soft launch: visibile solo a beta tester (es. ~20 clienti fidati)
2. Slack/WhatsApp channel diretto con davide@afianco.ch per H+0/H+24
3. Daily standup primo 5 giorni (15 min ogni mattina)

---

## Success criteria (4 settimane post-launch)

### Metrics quantitative

| KPI | Target | Threshold |
|---|---|---|
| Orders/week | ≥ 5 | ≥ 1 (validation only) |
| Cart abandonment rate | < 75% | < 85% |
| Checkout completion (cart → paid) | > 25% | > 15% |
| Time-to-Interactive (p75) | < 1.5s | < 3s |
| Embed init success rate | > 99.5% | > 99% |
| Sentry P1 errors/week | 0 | ≤ 2 |
| Customer support tickets | < 5 | < 15 |

### Metrics qualitative

- [ ] Merchant Net Promoter Score (NPS) ≥ 7
- [ ] Almeno 3 customer feedback positivi (collected via email)
- [ ] Zero crisi di trust (es. pagamenti smarriti, dati persi)
- [ ] Zero data leak cross-tenant (verificato by audit log)

### Decision matrix post-pilot

| Esito | Azione |
|---|---|
| Tutti i KPI verde | GA launch a tutti i merchant esistenti (~30 giorni) |
| KPI quantitative ok, qualitative no | Iterazione UX 2 settimane, poi GA |
| KPI quantitative no | Root cause analysis, post-mortem, V2 plan |
| Crisi (dati/pagamenti) | Rollback immediato, audit, P1 fix |

---

## Rollback plan

### Hot rollback (< 5 min)

Se incident severo (es. checkout 100% broken):

1. Cloudflare → rule "force cache miss on `/embed/v1/*`"
2. Revert deploy: redeploy bundle versione precedente (CI/CD pipeline)
3. Communicate con merchant: "tech issue, expect downtime 5-10 min"
4. Post-incident: aggiorna `status.afianco.ch`

### Soft rollback (degradation)

Se KPI cattivi senza incident hard:

1. Disable `allowed_origin` del merchant pilot (admin override)
2. Widget mostra "Maintenance" placeholder
3. Customer redirect a `app.afianco.ch/s/{slug}` (storefront classic)
4. Investigation 24-48h, poi re-enable con fix

### Data rollback

Se data corruption (worst case):

1. MongoDB restore da snapshot pre-launch
2. Stripe webhook replay per ricondiliare ordini
3. Customer email manuale: "tech recovery, your order is still safe"

---

## Communication templates

### Pre-launch (T-7 days)

> Subject: 🚀 AFianco Embed — Go-live previsto per [DATE]
>
> Ciao [MERCHANT],
>
> Siamo pronti per il pilot del widget AFianco sul tuo sito. Ti propongo
> queste 3 sessioni 30+20+15 min per integrazione + training + go-live:
>
> - [DATE-3] ore [TIME]: Tech onboarding
> - [DATE-1] ore [TIME]: Customer support training
> - [DATE] ore [TIME]: Soft go-live
>
> Tutto su Google Meet, mando link calendario.
>
> Davide

### Go-live (T+0)

> Subject: ✅ Widget AFianco LIVE su [DOMAIN]
>
> Il widget e' online dalle [TIME]. Per le prossime 48h:
>
> - Monitoraggio attivo Sentry + uptime check ogni 5 min
> - Sono raggiungibile su WhatsApp [NUMBER] 8-22 CEST
> - Daily standup 15 min ore 9:30 per primi 5 giorni
>
> Buon launch! Davide

### Post-pilot retrospective (T+30)

> Subject: 📊 Retrospettiva pilot AFianco — [MERCHANT]
>
> Ciao [MERCHANT],
>
> Ecco i numeri del primo mese:
> - Ordini: N
> - Customer attivi: N
> - Conversion rate: X%
> - Tickets support: N
>
> Domande per la chiamata di retrospettiva (45 min, propongo [DATE]):
> 1. Cosa ha funzionato bene?
> 2. Cosa ti ha fatto bestemmiare?
> 3. Top 3 feature requests per V2?
> 4. NPS 1-10?
>
> Output: piano V2 + roadmap Q3.
>
> Davide

---

## Post-launch monitoring

### Daily checks (T+0 to T+14)

- [ ] Sentry inbox @ 9:00 + 18:00 CEST
- [ ] `embed_init_requests_total` Prometheus counter
- [ ] `embed_checkout_started_total{outcome="success"}` rate
- [ ] Stripe dashboard → ordini ultime 24h
- [ ] MongoDB slow query log → query >100ms

### Weekly review (T+7, T+14, T+21, T+28)

- [ ] Compilare KPI dashboard
- [ ] Update success criteria table
- [ ] Identificare top 3 issues (bug + UX + perf)
- [ ] Pianificare prossima settimana

### Monthly retro (T+30)

- [ ] Compilare retrospective doc (sessione con merchant)
- [ ] Aggiornare `docs/embed-ux-symmetry-audit.md` con findings reali
- [ ] Roadmap V2 (Q3 2026):
  - [ ] Design tokens namespace unification (E6 deferred)
  - [ ] Landing pages deep-link (E7.1 deferred)
  - [ ] Search bar React storefront (E6 deferred)
  - [ ] Password strength widget (E6 deferred)
  - [ ] Code splitting per perf (T+30 perf review)

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Stripe webhook miss → order orphan | Medium | High | Reconciliation cron 1/h + manual replay tool |
| CORS misconfiguration merchant | High | Low | Admin UI validation + clear error message |
| Bundle cache stale post-deploy | Medium | Medium | Force cache-buster via hash, communicate to merchant |
| GDPR erasure incompleto | Low | High | Audit log + 30d window reversibilita |
| Coupon race condition (sold out) | High | Low | Dry-run + atomic backend check (E4.1) |
| Mobile UX broken su browser obscure | Medium | Medium | Top 5 browser tested, edge case = "best effort" |
| Customer email delivery fail | Medium | High | SendGrid retry + admin manual re-send button |
| Payment fraud / chargeback | Low | High | Stripe Radar default + merchant 3DS opt-in |

---

## Lessons learned (post-pilot — DA COMPILARE)

> Sezione da popolare 30 giorni dopo il launch. Include:
> - Top 3 surprise (positive + negative)
> - Quick wins identificati per V2
> - Architectural debts da pagare prima di scaling
> - Process improvements (es. CI/CD, on-call rotation)

---

## Support escalation

| Severity | Response time | Owner | Channel |
|---|---|---|---|
| **P1** (production down) | 30 min | Davide | WhatsApp + phone |
| **P2** (degraded UX) | 4 h | Davide | Email |
| **P3** (minor bug) | 24 h | Davide | Email |
| **P4** (feature request) | Next sprint | Davide | GitHub issue |

**Contact**: davide@afianco.ch | WhatsApp [NUMBER]
**Status page**: status.afianco.ch
**Docs**: docs/embed-integration-guide.md + onboarding-merchant.md + troubleshooting.md

---

**Document version**: 1.0
**Last updated**: 2026-06-05
**Next review**: T+7 post-launch
