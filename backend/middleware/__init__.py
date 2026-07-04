"""HTTP middleware package — Phase 0 Step 7 (2026-05-28).

Middleware custom installati su FastAPI app (vedi server.py):
  - dynamic_cors:  CORS per-store con lookup db sui ``/api/public/embed/*``
                   e ``/api/public/ai-site/*`` (Stream A + B).
  - idempotency:   ``Idempotency-Key`` enforcement con response cache.
                   (Step 8, separate)

Posizionamento middleware order matters (LIFO — last added = first executed):
  1. DynamicCORSMiddleware  — primo (gate per cross-origin)
  2. IdempotencyMiddleware  — secondo (su nuovi endpoints solo)
  3. RequestContextMiddleware — (existing — X-Request-ID injection)
  4. CORSMiddleware (statico legacy) — ultimo (fallback per route esistenti)

Vedi backend/server.py per la composition.
"""
