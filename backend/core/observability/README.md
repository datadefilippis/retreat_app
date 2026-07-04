# Observability Module

Centralized observability components for AFianco backend.

## Components

| Component | Env var trigger | Step | Status |
|---|---|---|---|
| Sentry SDK | `SENTRY_DSN` | A1 | implemented |
| JSON logging + request_id | (auto, with `LOG_FORMAT=json`) | A3 | TODO |
| Prometheus metrics | (auto) | A5 | TODO |

## Design principles

1. **Opt-in via env var**: missing config → component disabled silently. The app must boot and run identically without observability.
2. **Fail-safe**: errors during init are logged but never crash the app. External services (Sentry, Prometheus) being unreachable does not impact user-facing flows.
3. **PII-safe**: 3-layer scrubbing (field names, HTTP headers, regex patterns for free-text).
4. **Extensible**: new components added as separate modules under `observability/` with their own `init_*` function exposed via `__init__.py`.

## Adding a new component

1. Create `backend/core/observability/<component>.py` with an `init_<component>() -> bool` function.
2. The function must:
   - Read its own env var(s) for opt-in.
   - Return `False` early if not configured.
   - Wrap third-party SDK init in `try/except` and log+swallow errors.
3. Export from `__init__.py`.
4. Update this README.

## PII scrubbing

See `_pii_scrubber.py`. To extend the scrubber:

- Add field names (case-insensitive substring match) to `PII_FIELDS`.
- Add HTTP header names (case-insensitive exact match) to `PII_HEADERS`.
- Add regex patterns for free-text masking inside `_mask_text()`.

The scrubber is invoked at two Sentry hooks:
- `before_send` — for events (exceptions, captured messages).
- `before_breadcrumb` — for breadcrumbs (HTTP requests, log records).

## Verification

After enabling Sentry (set `SENTRY_DSN`):

1. Trigger an exception in any endpoint.
2. Check the Sentry dashboard for the event within 30s.
3. Verify the event tree contains `[Filtered]` for any sensitive fields.
4. Verify HTTP headers like `Authorization` are redacted.

Without `SENTRY_DSN`, every flow runs identically — no events sent, no outbound calls.
