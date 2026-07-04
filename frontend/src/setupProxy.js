/**
 * Frontend dev-server proxy.
 *
 * CRA / craco picks this file up automatically when present.
 * Forwards two prefixes to the backend so the browser can request
 * relative URLs (e.g. `/api/health`, `<img src="/uploads/logos/..."`)
 * without hardcoding the backend port.
 *
 *   /api      → FastAPI router tree
 *   /uploads  → uploaded media (store logos, product images, etc.)
 *
 * Critical: the target MUST match the actual backend port. Drift
 * here was the root cause of the "logo not loading" bug (target was
 * 8001 while the backend runs on 8000) — every `<img src="/uploads/..."`
 * timed out with 504 from the dev server.
 *
 * Note on /api in production
 * --------------------------
 * In production the API is accessed via `REACT_APP_BACKEND_URL` set
 * to the absolute origin (see frontend/.env). axios bypasses this
 * proxy and goes direct. The proxy only matters for:
 *   1. The dev workflow (this file)
 *   2. Static asset URLs that go through the browser's URL bar
 *      (logos, uploads — these are RELATIVE paths so they always
 *      take the page origin, which in dev is :3000 → proxy).
 *
 * Production deploy puts the frontend behind a reverse proxy that
 * serves both /api and /uploads from the same origin, so no
 * setupProxy.js indirection is involved.
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

// Single source of truth — keep in sync with backend/.env PORT and
// the package.json `"proxy"` fallback.
const BACKEND_TARGET = 'http://localhost:8000';

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: BACKEND_TARGET,
      changeOrigin: true,
    })
  );
  app.use(
    '/uploads',
    createProxyMiddleware({
      target: BACKEND_TARGET,
      changeOrigin: true,
    })
  );
};
