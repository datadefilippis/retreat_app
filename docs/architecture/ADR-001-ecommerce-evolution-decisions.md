# ADR-001 — E-commerce Evolution: Architectural Decisions

**Status:** Accepted
**Date:** 2026-05-28
**Deciders:** afianco core team
**Scope:** Stream A (Embed Widget) + Stream B (AI Site Builder) + Stream C (Custom Domain)

---

## Context

afianco oggi è un Business Operating System con catalogo prodotti hostato in
``afianco.app/s/<slug>``. L'evoluzione strategica richiede tre capability nuove:

1. **Embed Widget**: prodotti + carrello + checkout afianco embeddabili su
   qualsiasi sito esterno (WordPress, Wix, sito statico, ecc.)
2. **AI Site Builder**: generazione storefront completo via chat AI (stile
   V0/Bolt.new) con slot tags afianco per la parte commerce
3. **Custom Domain**: ogni storefront può vivere su ``shop.merchant.com``
   invece che su afianco.app

Questo documento fissa le **8 decisioni architetturali fondative** che
guideranno l'intero progetto. Ogni decisione include razionale, alternative
scartate, e implicazioni a lungo termine.

---

## Principi guida

Le decisioni sono prese contro questi 5 principi non negoziabili:

1. **Invariant-first development** — invariante → sentinel test → code
2. **Zero downtime, zero breaking changes** — ogni deploy reversibile
3. **Observability prima delle feature** — metric + log + dashboard PRIMA del go-live
4. **Security review per ogni surface esterna** — CORS + CSP + rate limit + audit
5. **Documentation parity** — ogni feature ha 3 doc: ADR + runbook + customer

---

## Decisione 1 — Persistent cart: dual-write per 60 giorni, poi cutover

**Decisione:** server-side cart come single source of truth. Dual-write
(sessionStorage + server) per 60 giorni, poi disable completo del fallback.

**Razionale:**
- 30 giorni insufficiente per coprire stagionalità (utente browse a maggio,
  compra a luglio per vacanze)
- 60 giorni cattura ~95% dei carrelli abbandonati riattivati
- Dual-write garantisce zero data loss durante migrazione
- Telemetria su tasso utilizzo legacy fallback prima del cutover

**Alternative scartate:**
- Big-bang migration → rischio inaccettabile per ordini in volo
- Solo server-side senza fallback → utenti con cart in sessionStorage perdono dati

**Impatto:** nuovo modello ``Cart`` su Mongo, cookie ``afianco_cart_id``
(HttpOnly, Secure, SameSite=Lax, 60gg TTL), worker abandon recovery.

---

## Decisione 2 — Idempotency enforcement scalato per surface

**Decisione:**
- Nuovi endpoint (``/api/public/embed/*``, ``/api/public/ai-site/*``):
  ``Idempotency-Key`` header obbligatorio dal day 1
- Legacy ``POST /api/public/order-request``: 90 giorni di grace period
  con warning log strutturato, poi enforcement

**Razionale:**
- Client legacy esistono già in produzione (frontend afianco.app + PWA cached).
  Non possiamo rompere ordini in flight.
- Client nuovi nascono con disciplina corretta. Niente "tech debt da day 1"
- 90 giorni > 30 perché vogliamo audit completo della distribuzione client

**Alternative scartate:**
- Enforcement immediato globale → rompe ordini in produzione
- Mai obbligatorio → debito tecnico permanente, rischio doppi ordini

**Impatto:** middleware ``apps/backend/middleware/idempotency.py``, cache
response 24h per ``(key, org_id)``, feature flag ``IDEMPOTENCY_ENFORCED``.

---

## Decisione 3 — Monorepo pnpm + Turborepo da subito

**Decisione:** migrazione a monorepo ``pnpm workspaces + Turborepo`` come primo
step di Phase 0.

```
afianco/
├── apps/
│   ├── admin/          (ex frontend/, CRA invariato)
│   ├── embed-sdk/      (NUOVO, Vite + Lit)
│   ├── ai-site-renderer/ (NUOVO, Phase 3)
│   └── backend/        (ex backend/, invariato)
├── packages/
│   ├── shared-types/   (TS types backend ↔ frontend)
│   ├── design-tokens/  (brand colors, typography)
│   ├── api-client/     (axios client + types)
│   ├── embed-runtime/  (logica condivisa)
│   └── slot-elements/  (Web Components afianco-*)
└── turbo.json
```

**Razionale:**
- Scalabile a 5-10 packages senza refactor futuri
- Type safety end-to-end con shared-types (generato da Pydantic)
- Build cache Turborepo accelera CI 5-10×
- Permette future pubblicazioni npm (``@afianco/embed-sdk``)
- Single source of truth per design tokens
- Pattern usato da Shopify, Vercel, Linear

**Alternative scartate:**
- Stessa repo con 2 build pipeline → debito tecnico, alias duplicati
- Yarn workspaces → pnpm è 2× più veloce, deduplica meglio
- Lerna → deprecato

**Impatto:** +1 settimana in Phase 0 (pagamento upfront). Sentinel test:
``turbo run build`` produce admin bundle byte-identico al CRA precedente.

---

## Decisione 4 — Cloudflare for SaaS per custom domain

**Decisione:** Cloudflare for SaaS dal day 1 di Phase 2 per gestione custom
domain merchant.

**Razionale:**
- Battle-tested su Shopify, Webflow, Wix (>10M custom domain in prod)
- SSL automation impeccabile (no Let's Encrypt edge case)
- Edge CDN globale incluso
- Origin shield, DDoS protection, bot management
- $0.10/hostname/mese = trascurabile a qualsiasi scala
- Manutenzione zero da parte nostra

**Alternative scartate:**
- Build in-house wildcard SSL + nginx + Certbot → 6+ settimane lavoro +
  manutenzione perenne + edge case mai testati a scala
- AWS Route 53 + ACM → comparable ma più complesso multi-region

**Vendor lock-in mitigation:** runbook ``migration-off-cloudflare-saas.md``
preparato come piano B (nginx wildcard self-hosted).

---

## Decisione 5 — Lit (Google Web Components library)

**Decisione:** Lit 3 per tutti i Web Components afianco (embed + slot tags AI site).

**Razionale:**
- Bundle ~5 KB minified gzip (vs React 45 KB)
- Standard Web Components → funziona ovunque (React, Vue, vanilla, WP)
- Built-in reactive rendering, decorators, lifecycle hooks
- TypeScript-first
- Production-proven: Google Material Web, Adobe Spectrum, Salesforce LWC
- SSR support per futuro SEO

**Alternative scartate:**
- Vanilla JS puro → maintenance nightmare a scala
- React minimale → 30 KB runtime + peer dep conflicts con altri React
- Preact → leggero ma framework dependency, non standard WC
- Stencil → alternativa valida ma Lit ha ecosystem migliore

**Verifica:** Lit usato in produzione da Google Material 3, Adobe Spectrum,
ING bank, Smartwheel.

---

## Decisione 6 — Hybrid Shadow DOM + Stripe popup

**Decisione:**

| Surface | Tecnica | Razionale |
|---|---|---|
| Product cards, grids, navigation | Shadow DOM | Integrated UX, CSS isolation |
| Cart drawer | Shadow DOM | Stesso |
| Checkout completo | Stripe Checkout popup | PCI scope minimization |
| Confirmation toast | Shadow DOM | UX integrata |
| Heavy widgets opzionali (video) | Iframe sandboxed | Isolation totale |

**Razionale:**
- Shadow DOM per UI = nessun CSS bleeding dal sito merchant
- Popup Stripe = PCI compliance triviale (no card input mai nel nostro DOM)
- Iframe per heavy content = isolamento massimo dove serve

**Alternative scartate:**
- Tutto iframe → UX peggiore, mobile responsive complicato
- Tutto Shadow DOM → checkout dentro = PCI scope cresce, audit costoso

---

## Decisione 7 — AI Builder: Managed + BYOK + Tiered quotas

**Decisione:** tre livelli di accesso AI Builder.

| Tier | Modello | Quota | Costo |
|---|---|---|---|
| Managed Standard | Claude Haiku 4 | Per piano | Incluso nel piano |
| Managed Premium | Sonnet 4 init + Haiku edit | Quota separata | +€19-29/mese add-on |
| BYOK Enterprise | User-provided key | Illimitato | Solo Enterprise |

**Razionale:**
- Mass market merchant non sa cos'è una API key → managed con Haiku ottimo
- Power user → Sonnet 4 a pagamento per quality max
- Enterprise → BYOK per scelta modello + controllo costo
- Tiered = ARPU diverso per segmenti diversi
- Cost ceiling automatico per noi (Haiku 75% cheaper di Sonnet)

**Cost guard:**
1. Per-organization budget mensile (€10-€100 per piano)
2. Throttle dinamico se costi mensili si avvicinano alla soglia
3. Cache aggressiva prompt-level e org-level
4. Model downgrade automatico (Sonnet → Haiku) se quota stretta
5. Hard cap per request (max 50K token output)

---

## Decisione 8 — AI site: bundle statico su Cloudflare R2 + Edge

**Decisione:** siti AI-generated pubblicati come bundle statici HTML/CSS/JS
su Cloudflare R2, serviti via Workers + edge CDN globale.

```
AI builder → HTML/CSS sanitized → bundle minified → R2 → Worker edge
```

**Razionale:**
- Costo storage trascurabile ($0.015/GB-month)
- Bandwidth gratuito su Cloudflare
- Latency < 50ms globalmente (edge cache)
- Scala a milioni di pageviews/mese a costo costante
- SEO ottimo (vero HTML statico, no JS rendering blocking)
- Versioning naturale (ogni publish = nuovo bundle in R2)
- Rollback istantaneo (point al bundle precedente)

**Alternative scartate:**
- React app live → 100× costo runtime, latency peggiore, SEO complicato
- SSR backend → over-engineered, scaling problem

---

## Consequences

Queste 8 decisioni implicano:

**Effort totale stimato:**
- Phase 0 (Foundation): 7 settimane
- Phase 1 (Embed): 10 settimane
- Phase 2 (Custom Domain): 5 settimane (parallelo a fine Phase 1)
- Phase 3 (AI Builder): 16 settimane
- Phase 4 (Hardening + Launch): 6 settimane
- **Totale: ~38 settimane (~10 mesi calendar con 1 dev FT)**

**Budget infrastructure incrementale:**
- ~€700-1.500/mese ricorrente
- ~€10.000 one-time (penetration test + bug bounty setup)

**Revenue projection (conservativo):**
- M+12 post-launch: €127.500/mese MRR

**Trade-off accettati:**
- 10 mesi calendar invece di 4-5 (MVP approach scartato)
- Monorepo migration +1 settimana upfront (pagamento per scalabilità)
- Sentinel test 30+ scritti PRIMA di refactor (rallenta start, accelera lifecycle)
- BYOK riservato Enterprise (segmenta il mercato, non confonde mass market)

**Test coverage target:**
- Public flows: 6% → 50%+ entro Phase 0
- Embed: 0% → 70% entro Phase 1
- Custom domain: 0% → 80% entro Phase 2
- AI builder: 0% → 60% entro Phase 3
- Critical paths: 80%+ entro Phase 4

---

## Review schedule

- **Settimanale:** review dei deliverable della settimana
- **Fine fase:** Definition of Done verificata + go/no-go per fase successiva
- **Trimestrale:** ADR review per eventuali correzioni di rotta

---

## References

- Roadmap completo: ``docs/architecture/phase-0-plan.md`` (e seguenti)
- Invarianti del sistema: ``docs/architecture/invariants.md`` (work in progress)
- Sentinel test: ``apps/backend/tests/test_invariants_*.py``
