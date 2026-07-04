# apps/

Applicazioni full-stack o frontend nuove. Distinte da ``frontend/`` (CRA admin
app legacy) e ``backend/`` (FastAPI) che restano nelle loro location storiche.

## Roadmap applicazioni

| App | Scope | Status |
|---|---|---|
| `@afianco/embed-sdk` | Web Components SDK per merchant embed (Stream A) | Step 11 |
| `@afianco/ai-site-renderer` | Bundle statico per siti AI-generated (Stream B) | Stream B |

## Convenzioni

- Build tool: Vite (preferito vs CRA per nuovi apps — più veloce + tree-shaking superiore)
- TypeScript strict mode
- Lit per Web Components
- Bundle target: ES2017 (compat WordPress + browser legacy)
- Bundle size budget: ~80 KB gzip per embed-sdk
