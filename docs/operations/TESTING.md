# Testing Runbook

> How to run, debug, and extend the test suite across the AFianco
> monorepo. Authoritative reference for `Track S Step 6.2`.

---

## Quick start — one command

```bash
# From repo root
npm run backend:test       # Backend pytest (~3200 test, ~30s warm)
pnpm test                  # Embed-SDK + packages vitest (~200 test, ~10s)
```

CI runs both in parallel — see `.github/workflows/test.yml`.

---

## Test suite structure

### Backend (pytest, Python 3.14)

| Folder | Count | Pattern |
|---|---|---|
| `backend/tests/test_invariants_*.py` | ~600 sentinel | Invariant pinning (anti-regression) |
| `backend/tests/test_wave_*.py` | ~800 wave tests | Feature-tested business flows |
| `backend/tests/test_*.py` | ~1800 unit/integration | Misc legacy + per-feature |
| **TOTAL** | **3184** | + 7 skipped |

**Critical sentinel files** (security):
- `test_invariants_security.py` — **161 sentinel** (Phase 0 + Track S)
- `test_invariants_dynamic_cors.py` — 32 sentinel
- `test_invariants_idempotency.py` — 27 sentinel
- `test_invariants_embed_*.py` (9 files) — embed surface tests

### Embed-SDK (vitest + happy-dom)

| File | Count |
|---|---|
| `tests/afianco-*.test.ts` (9 files) | 128 sentinel |
| `tests/e2e-customer-flow.test.ts` | 5 sentinel |
| **TOTAL** | **133** |

### Packages

| Package | Test count |
|---|---|
| `@afianco/api-client` | 25 (tests/client.test.ts) |
| `@afianco/shared-types` | 14 (tests/shape-parity.test.ts) |
| `@afianco/design-tokens` | 12 (tests/tokens.test.ts) |
| **TOTAL** | **51** |

---

## Run individual files

### Backend pytest

```bash
cd backend
# Single file
./venv/bin/pytest tests/test_invariants_security.py -v

# Single class
./venv/bin/pytest tests/test_invariants_security.py::TestSEC_S2_1_LoginAntiEnumeration_CustomerService -v

# Single test
./venv/bin/pytest \
  tests/test_invariants_security.py::TestSEC_S2_1_LoginAntiEnumeration_CustomerService::test_email_not_found_burns_bcrypt_dummy_for_timing_constant \
  -v

# Verbose with stdout
./venv/bin/pytest tests/foo.py -v -s

# Stop at first failure
./venv/bin/pytest tests/foo.py -x

# Just the failed tests from last run
./venv/bin/pytest --lf

# Coverage report (HTML in htmlcov/)
./venv/bin/pytest --cov=. --cov-report=html
```

### Embed-SDK vitest

```bash
# Run all
pnpm --filter @afianco/embed-sdk test -- --run

# Single file (no --run = watch mode)
pnpm --filter @afianco/embed-sdk test tests/afianco-login.test.ts

# Watch mode + UI
pnpm --filter @afianco/embed-sdk test:watch
```

### Packages

```bash
# All packages
pnpm --filter "./packages/**" test -- --run

# Single package
pnpm --filter @afianco/api-client test
```

---

## Writing a new sentinel test

Sentinel test = **invariant pinning** test. Fails if the invariant
breaks → forces a code review + intentional decision to change behavior.

### Naming convention

```python
class TestSEC_<TRACK>_<STEP>_<ShortName>:
    """SEC-<TRACK>.<STEP>: <plain-english invariant>.

    Pin location: backend/<file>.py <function/class>
    """

    def test_<invariant_in_words>(self):
        # Mock minimal dependencies
        # Call the target function/class
        # Assert the specific invariant
        ...
```

### Anti-pattern checklist

- ❌ Test "happy path works" — that's a functional test, not a sentinel
- ❌ Test brand-new feature — sentinel = pinning EXISTING behavior
- ❌ Test that mocks everything → tests the mock, not the code
- ✅ Test that breaks CI if someone changes the code carelessly
- ✅ Cross-reference the pin location in docstring

### Example template

```python
class TestSEC_S2_1_LoginAntiEnumeration_CustomerService:
    """SEC-S2.1 service-level invariants for customer login.

    Pin location: backend/services/customer_auth_service.py::customer_login
    """

    def test_email_not_found_burns_bcrypt_dummy_for_timing_constant(self):
        # Mock find_by_email returning None
        # Spy on verify_password
        # Call customer_login()
        # Assert: verify_password called 1x with _BCRYPT_DUMMY_HASH
```

---

## Common failure patterns

### `ModuleNotFoundError` in CI

Module installed locally (transitive of another dep) but missing in
`backend/requirements.txt`. Run:

```bash
cd backend
./venv/bin/pip list --format=freeze | cut -d= -f1 | sort -u > /tmp/venv.txt
grep -oE '^[a-zA-Z0-9._-]+' requirements.txt | sort -u > /tmp/req.txt
comm -23 /tmp/venv.txt /tmp/req.txt
```

Add missing direct deps (not transitive) to `requirements.txt`.

### `async def functions are not natively supported`

`pytest-asyncio` not installed. Already pinned in `requirements.txt`
since Track S Step 4.4 round 2. If you remove it, CI fails.

### `Failed to resolve entry for package @afianco/*`

Workspace package `dist/` not built. Run:

```bash
pnpm --filter "./packages/**" build
```

CI handles this automatically in `test.yml::embed-sdk-vitest`.

### Sentinel test breaks intentionally

If you changed behavior intentionally (e.g. S3.5 changed CORS status
400 → 403), update BOTH:

1. The legacy test asserting old behavior (e.g. `assert status == 400`)
2. Add new sentinel pinning the new behavior

Pattern: see `tests/test_invariants_dynamic_cors.py::TestF3_CustomerOptInGuard::test_strict_embed_path_enforces_without_slug_signal` after S3.5 fix.

### Idempotency race timeouts

Sentinel `TestSEC_S5_3_IdempotencyRaceFunctional` overrides
`LOCK_POLL_INTERVAL_SEC=0.01` and `LOCK_POLL_TIMEOUT_SEC=0.1` for fast
tests. If you change these constants in production, the test may need
re-tuning.

---

## CI gating

Both workflows MUST pass before merge to `main`:

| Workflow | Required? | Where to configure branch protection |
|---|---|---|
| `.github/workflows/test.yml` | ✅ Required | Settings → Branches → Protect `main` |
| `.github/workflows/security.yml` | ✅ Required | Same |

Branch protection rule references the **aggregate gate** jobs
(`ci-passed` + `security-passed`) — single status checks stable to
job renames.

---

## Coverage

Backend pytest generates coverage XML (Track S Step 4.4):

```bash
cd backend
./venv/bin/pytest --cov=. --cov-report=xml --cov-report=html
open htmlcov/index.html
```

CI uploads `coverage.xml` as artifact (retention 30 days). Access via
GitHub Actions UI → run → Artifacts → `backend-coverage`.

**V1 informational only** (no gating threshold). V2 will set minimum
coverage % once baseline established.

JS coverage deferred to V2 (requires `@vitest/coverage-v8` install).

---

## Cross-references

- [`docs/SECURITY_HARDENING.md`](../SECURITY_HARDENING.md) — security
  policy + sentinel test catalog
- [`SECURITY.md`](../../SECURITY.md) — vulnerability reporting policy
- [`docs/operations/secrets-rotation.md`](secrets-rotation.md) — secret
  rotation playbook
- [`.github/workflows/test.yml`](../../.github/workflows/test.yml) — CI config
- [`backend/pytest.ini`](../../backend/pytest.ini) — pytest config

---

_Last updated: 2026-05-29 — Track S Step 6.2_
