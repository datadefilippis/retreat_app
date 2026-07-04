# AFianco — Business Operating System per PMI italiane

[![test](https://github.com/datadefilippis/BI_PMI/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/datadefilippis/BI_PMI/actions/workflows/test.yml)
[![security](https://github.com/datadefilippis/BI_PMI/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/datadefilippis/BI_PMI/actions/workflows/security.yml)

Backend FastAPI + frontend React + embed-SDK (Web Components Lit) monorepo.

## Test suite

Aggregata cross-package — gated by CI su PR + push main.

| Suite | Test count | Comando |
|---|---|---|
| Backend pytest | **3184** | `npm run backend:test` |
| Embed-SDK vitest | **133** | `pnpm --filter @afianco/embed-sdk test` |
| api-client vitest | **25** | `pnpm --filter @afianco/api-client test` |
| shared-types vitest | **14** | `pnpm --filter @afianco/shared-types test` |
| design-tokens vitest | **12** | `pnpm --filter @afianco/design-tokens test` |
| **TOT cross-package** | **3368** | `npm run backend:test && pnpm test` |

Di cui **518 backend sentinel/invariant** (Phase 0 + Phase 1 + Track S),
**133 embed-sdk sentinel** (con E2E customer flow).

## Quick start

```bash
# Backend dev server
npm run backend:dev

# Frontend dev server
npm run frontend:dev

# Embed-SDK playground (Vite hot-reload)
pnpm --filter @afianco/embed-sdk dev
```

## Documentation

- [`docs/SECURITY_HARDENING.md`](docs/SECURITY_HARDENING.md) — security
  policy + runbook (29 sezioni, Track S completo)
- [`docs/architecture/`](docs/architecture/) — architecture decisions,
  system invariants
- [`docs/operations/`](docs/operations/) — operational runbooks

## CI gating

| Workflow | Trigger | Gating job |
|---|---|---|
| `.github/workflows/test.yml` | PR + push main + manual | `ci / all-passed` |
| `.github/workflows/security.yml` | PR + push main + weekly + manual | `security / all-passed` |

Branch protection rule on `main` references both aggregate gates.

## Stack

- **Backend**: FastAPI 0.110, Python 3.14, MongoDB (Motor async)
- **Frontend (admin)**: React 18, CRA, recharts
- **Embed widget**: Lit 3.2 Web Components, Vite, ~28KB gzip
- **Packages**: shared-types, api-client (typed fetch wrapper),
  design-tokens (CSS custom properties)
- **Monorepo**: pnpm workspaces 11.4 + Turborepo
