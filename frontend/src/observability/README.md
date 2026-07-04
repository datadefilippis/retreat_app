# Observability Module (frontend)

Centralized observability components for AFianco React frontend.

## Components

| Component | Env var trigger | Step | Status |
|---|---|---|---|
| Sentry SDK | `REACT_APP_SENTRY_DSN` | A2 | implemented |

## Design principles

1. **Opt-in via env var**: missing config → component disabled silently. The app must boot and run identically without observability.
2. **Fail-safe**: errors during init are logged but never crash the app. External services being unreachable does not impact user-facing flows.
3. **PII-safe**: 4-layer scrubbing (field names, HTTP headers, regex patterns, keyword-value pairs).
4. **Privacy-first MVP**: session replay disabled. Re-evaluate post-GA.
5. **Mirror backend**: scrubber rules and configuration shape align with `backend/core/observability/`.

## Usage

This module has a **side effect**: it calls `initSentry()` on import. Import it as early as possible in `src/index.js`:

```js
// src/index.js — first import, before anything that might throw
import "@/observability";

import "@/index.css";
import "@/i18n";
// ...
```

In application code:

```js
import { captureException, captureMessage } from "@/observability";

try {
  riskyOperation();
} catch (e) {
  captureException(e, { context: "what-was-happening" });
}

// Track notable events
captureMessage("User completed onboarding", "info");
```

Both functions are **no-ops** when Sentry is not initialized — safe to call unconditionally.

## ErrorBoundary integration

The existing `components/ErrorBoundary.js` calls `captureException(error, { errorInfo })` from its `componentDidCatch` lifecycle method. This means every React render crash is automatically reported (when Sentry is on) without changing the boundary's UI behaviour.

## PII scrubbing

See `_pii_scrubber.js`. To extend:

- Add field names (case-insensitive substring) to `PII_FIELDS`
- Add HTTP header names (case-insensitive exact) to `PII_HEADERS`
- Add regex patterns inside `maskText()` for free-text masking

The scrubber runs at two Sentry hooks:
- `beforeSend` — for events (exceptions, captured messages)
- `beforeBreadcrumb` — for breadcrumbs (HTTP requests, navigation events, console logs)

If the scrubber throws, the event is **dropped entirely** rather than sent unmasked.

## Environment variables

| Var | Required | Default | Description |
|---|---|---|---|
| `REACT_APP_SENTRY_DSN` | No | (empty) | Sentry project DSN. Leave empty to disable. |
| `REACT_APP_SENTRY_TRACES_RATE` | No | `0.1` | Pageloads to trace (0.0–1.0). |
| `REACT_APP_SENTRY_ENVIRONMENT` | No | `NODE_ENV` | Tag events (production/staging/development). |
| `REACT_APP_RELEASE_SHA` | No | `unknown` | Git SHA for release tracking. |

CRA only injects vars matching `REACT_APP_*` prefix into `process.env` at build time.

## Verification

After enabling Sentry (set `REACT_APP_SENTRY_DSN`):

1. Trigger an error in any component (e.g. throw in onClick).
2. Check the Sentry dashboard for the event within 30s.
3. Verify the event tree contains `[Filtered]` for any sensitive fields.
4. Verify HTTP headers like `Authorization` are redacted.
5. Verify free-text email/Bearer/JWT in error messages are redacted.

Without `REACT_APP_SENTRY_DSN`, every flow runs identically — no events sent, no outbound calls, zero overhead.
