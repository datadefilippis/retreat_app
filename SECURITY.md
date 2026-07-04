# Security Policy

> AFianco è un Business Operating System per PMI italiane. Il backend
> espone API pubbliche (embed widget cross-origin, customer auth,
> Stripe checkout) → la security è first-class.

---

## Supported Versions

| Version | Status | Notes |
|---|---|---|
| `main` (latest) | ✅ Supported | Production target, security fix landing diretto |
| `v0.x` releases | ✅ Supported | Phase 1 (current), bug + security fix backported |
| Pre-Phase 0 | ❌ EOL | Migrare a `main` |

## Reporting a Vulnerability

**Per favore NON aprire issue pubblici per vulnerabilità di sicurezza.**

### Canali di reporting (in ordine di preferenza)

1. **GitHub Security Advisory** (preferito):
   - Vai su https://github.com/datadefilippis/BI_PMI/security/advisories/new
   - Compila il form (privato, visibile solo ai maintainer)
   - Risposta entro 48 ore lavorative

2. **Email**:
   - `davidedefilippis94@gmail.com` con subject prefix `[SECURITY]`
   - PGP key disponibile su richiesta
   - Risposta entro 72 ore lavorative

3. **Per terze parti** (security researcher, pen-tester):
   - Stesso canale GitHub Security Advisory
   - Include POC + impact analysis se possibile
   - Crediti pubblici nei release notes (opt-in)

### SLA di risposta

| Severity | First response | Patch released |
|---|---|---|
| **Critical** (RCE, auth bypass, data leak globale) | 24h | 7 giorni |
| **High** (privilege escalation, PII leak) | 48h | 14 giorni |
| **Medium** (info disclosure, CSRF) | 5 giorni | 30 giorni |
| **Low** (best-practice improvements) | 7 giorni | 60 giorni |

### Coordinated disclosure

- 90 giorni di embargo prima di disclosure pubblica
- Negotiable a richiesta del reporter
- CVE assegnato per Critical/High via MITRE o GitHub CNA

---

## Threat Model (OWASP Top 10 mapping)

Il backend FastAPI + frontend React + embed-SDK ha 3 surface principali:

### Surface A — Embed widget cross-origin (`/api/public/embed/*`)

| OWASP | Threat | Mitigation | Pin |
|---|---|---|---|
| A01 Broken Access Control | Cart/order ID enumeration | UUID v4 (2^122 entropy) | `TestSEC_S3_1_IDsAreUUIDv4` |
| A02 Cryptographic Failures | SHA-1 weak hash | SHA-1 solo per ETag (`usedforsecurity=False`) | `TestSEC_S3_4` |
| A03 Injection | NoSQL/SQL injection | Pydantic + Motor parametrized queries | (no raw queries) |
| A04 Insecure Design | Idempotency race → doppio ordine | Unique index + claim-the-lock | `TestSEC_S3_2` |
| A05 Security Misconfig | CORS wildcard / null bypass | Dynamic CORS per-store + `allowed_origins` validation | `TestSEC_S3_3` |
| A07 Auth Failures | Email enumeration via login/signup | Uniform 401/202 + bcrypt dummy timing | `TestSEC_S2_1`, `TestSEC_S2_2` |
| A09 Logging Failures | No detection of token reuse | Detection log su token-consumption-failed | `TestSEC_S2_3` |

### Surface B — Customer auth (`/api/customer-auth/*` + `/api/customer/*`)

| OWASP | Threat | Mitigation | Pin |
|---|---|---|---|
| A01 | Cross-tenant data access | JWT con `org_id` claim + per-org repository scoping | Customer signup test |
| A02 | Password hash weak | bcrypt cost 12 | (passlib config) |
| A04 | Lockout bypass via password reset | Reset clears lockout state + token single-use | `TestSEC_S2_3` |
| A07 | Bruteforce | Per-IP slowapi + per-email rate limit (cross-IP, 20/h) + account lockout (5 fail → 15min) | `TestSEC_S2_4` |
| A08 | Token tampering | JWT HS256 + fail-fast on missing secret + `password_changed_at` invalidation | `auth.py:12-18` |

### Surface C — Admin & internal (`/api/admin/*`, `/api/auth/*`, `/metrics`)

| OWASP | Threat | Mitigation | Pin |
|---|---|---|---|
| A01 | Admin endpoint exposure | `require_system_admin` dependency | All admin routes |
| A05 | `/docs` Swagger leak | Env-gated `docs_url=None` in prod | `TestSEC_S1_3` |
| A05 | `/metrics` Prometheus leak | X-Metrics-Token + env var fail-closed | `TestSEC_S4_1` |
| A06 Vulnerable Components | Outdated deps with CVEs | pip-audit + pnpm audit + Dependabot weekly | `.github/workflows/security.yml` |

---

## Defense in Depth — Layered controls

```
                            ┌─────────────────────────┐
   Internet ──────────────► │  nginx (reverse proxy)  │
                            │  - TLS 1.2+, HSTS       │
                            │  - Rate limit fallback  │
                            │  - HTTP→HTTPS redirect  │
                            └────────────┬────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  DynamicCORS middleware │  ← per-store allowlist
                            ├─────────────────────────┤
                            │  Idempotency middleware │  ← claim-the-lock
                            ├─────────────────────────┤
                            │  Rate limit (slowapi)   │  ← per-IP
                            ├─────────────────────────┤
                            │  RequestContext mw      │  ← X-Request-ID
                            ├─────────────────────────┤
                            │  Global exception handler│ ← opaque 500
                            └────────────┬────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  FastAPI handler        │
                            │  - Pydantic validation  │
                            │  - Auth dependencies    │
                            │  - check_email_rate     │  ← cross-IP per email
                            │  - Account lockout      │  ← Onda 29/30
                            └────────────┬────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  MongoDB (Atlas TLS)    │
                            │  - Unique indexes        │
                            │  - Per-org filter        │
                            │  - Audit collections     │
                            └─────────────────────────┘
```

---

## Accepted Residual Risks (V1)

Risks consciously deferred to V2 (documented in
`docs/SECURITY_HARDENING.md`):

| Risk | Why deferred | When |
|---|---|---|
| Starlette CVE-2024-47874 + 2 more | Requires FastAPI 0.110 → 0.115+ major migration | Phase 2 |
| Refresh token mechanism (access token 7 days) | UX-only, no security gap | Phase 2 |
| JWT in httpOnly cookie vs localStorage | Requires CSRF token + refactor | Phase 2 (post pen-test) |
| Stripe `STRIPE_CLIENT_ID` rotation | Invalidates all Connect connections | Phase 2 |
| Admin signup 409 enumeration | Mitigated by `invite_only` mode (default) | Phase 2 |
| Redis-based rate limit (multi-worker) | Single worker today | When scaling |
| `pandas` Dependabot update | Wheel build issue, investigation needed | Phase 2 |

---

## Security Audit Tooling

| Tool | Coverage | Frequency | CI gated |
|---|---|---|---|
| **Bandit** | Python SAST (HIGH severity) | Every PR + weekly | ✅ |
| **pip-audit** | Python deps CVE | Every PR + weekly | ✅ |
| **pnpm audit** | JS deps CVE | Every PR + weekly | ✅ |
| **Dependabot** | Auto-PR for dep updates | Weekly Monday | n/a (opens PRs) |
| **pytest sentinel** | 161 security invariant tests | Every PR + push | ✅ |
| **Sentry** | Runtime exception capture | Real-time | n/a |

See `.github/workflows/security.yml` + `docs/SECURITY_HARDENING.md`.

---

## Hall of Fame

Security researchers who responsibly disclosed vulnerabilities are
recognized here (with permission):

_(empty — Phase 1, pre-pilot)_

---

## Compliance & Certifications

- **GDPR**: customer consent capture (Privacy + Terms versioned),
  audit trail in `consent_audit` collection, right-to-erasure via
  `/api/customer/me/delete` (Phase 1 Wave GDPR-Commerce CG-4).
- **PCI DSS**: card data never touches our backend (Stripe Checkout
  redirect handles tokenization). We store only `payment_intent`
  status + last4 from Stripe webhook.
- **SOC2**: not certified V1. Roadmap Q4 2026.

---

## Disclosure Coordination

- **CVE assignment**: via GitHub CNA when applicable
- **Public advisory**: published after patch + 7 days grace period
- **Credit**: optional but encouraged in advisory + CHANGELOG

---

_Last updated: 2026-05-29 — Track S Step 6.1_
