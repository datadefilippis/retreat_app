# Security Headers Policy

Reference for the HTTP response headers configured in `deploy/nginx/nginx.conf`
under `server { listen 443 }`. Each header is documented with rationale,
trade-offs, and the failure mode if removed.

Configured at: **Phase 1 Step D1** (deployed YYYY-MM-DD).
Validated via: `securityheaders.com` rating target **A or A+**.

---

## 1. Strict-Transport-Security (HSTS)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Effect**: browsers refuse plain HTTP for `afianco.app` and any subdomain
for 1 year after first visit.

**`preload` directive**: declares willingness to be in browsers' built-in
preload list. **Submission is NOT automatic** — manually submit at
[hstspreload.org](https://hstspreload.org/) **after 1 week of soak in production**
to confirm:
- TLS valid on apex domain
- TLS valid on all subdomains
- Header is consistently served on every request

**⚠️ Removal from preload takes 6+ months**. Confirm all subdomains are TLS-
ready before submitting.

---

## 2. X-Frame-Options + frame-ancestors

```
X-Frame-Options: DENY
Content-Security-Policy: ...; frame-ancestors 'none';
```

**Effect**: AFianco pages cannot be embedded in any `<iframe>`, `<frame>`,
or `<object>` (anti-clickjacking).

`X-Frame-Options` is the legacy header (kept for older browsers).
`frame-ancestors 'none'` is the CSP-3 modern equivalent. Both present =
defense in depth.

If you ever need to embed AFianco UI (e.g. partner integration via iframe):
- Switch to `X-Frame-Options: ALLOW-FROM <partner-origin>` (deprecated, Chrome ignores)
- OR `frame-ancestors https://partner.example.com` (preferred)

---

## 3. X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

**Effect**: browser does NOT MIME-sniff the response body. Trust only the
`Content-Type` header. Prevents image-as-script attacks where uploaded
`.png` content actually contains JavaScript.

---

## 4. X-XSS-Protection (REMOVED)

**Removed on purpose.** All modern browsers (Chrome 78+, Firefox 78+,
Safari 12+) deprecated this header. The legacy XSS auditor was itself
exploited in several CVEs. CSP `script-src` is the proper replacement.

If `securityheaders.com` flags this as missing, add a comment to the
nginx config explaining the removal — that scanner uses old criteria.

---

## 5. Referrer-Policy

```
Referrer-Policy: strict-origin-when-cross-origin
```

**Effect**:
- Same-origin requests → full URL in `Referer` (path + query).
- Cross-origin HTTPS → only `https://afianco.app` (origin only, no path).
- Cross-origin HTTP downgrade → empty referer.

Balances analytics needs (we know which page generated the click) with
privacy (we don't leak query strings to external trackers).

---

## 6. Permissions-Policy

```
Permissions-Policy: camera=(), microphone=(), geolocation=(),
                    payment=(self), usb=(), bluetooth=(),
                    magnetometer=(), gyroscope=()
```

**Effect**: explicit deny for browser APIs the app does not use. `payment=(self)`
keeps the future Payment Request API available for AFianco's own pages
(useful when we wire Apple Pay / Google Pay).

If a feature needs one of these later, change `()` to `(self)` for that key.

---

## 7. X-Permitted-Cross-Domain-Policies

```
X-Permitted-Cross-Domain-Policies: none
```

**Effect**: blocks legacy Adobe Flash / PDF cross-domain access policy
files (`crossdomain.xml`, `clientaccesspolicy.xml`). We have neither;
deny outright.

---

## 8. Content Security Policy (CSP) — the big one

Single-line declaration in nginx, decomposed here for review:

| Directive | Value | Reason |
|---|---|---|
| `default-src` | `'self'` | Fallback for any directive not listed below. |
| `script-src` | `'self' 'unsafe-eval'` | App bundle (CRA single `main.js`) + `unsafe-eval` kept temporarily for libs that may use `new Function()` (recharts, framer-motion). Plan: remove after browser-side audit. **No `'unsafe-inline'`** — React production build emits no inline scripts. |
| `style-src` | `'self' 'unsafe-inline' https://fonts.googleapis.com` | `'unsafe-inline'` is **required** by Tailwind / Radix UI / framer-motion runtime style injection. fonts.googleapis.com for the `@import` in `src/index.css`. |
| `font-src` | `'self' data: https://fonts.gstatic.com` | gstatic for Google Fonts files. data: for tiny inline font glyphs. |
| `img-src` | `'self' data: blob: https:` | App-uploaded images, inline previews (data:/blob: during upload), and OG-card images. |
| `connect-src` | `'self' https://*.ingest.sentry.io https://*.ingest.de.sentry.io` | `/api/*` calls + Sentry SDK ingest. **Stripe API NOT included** — checkout is full-page redirect, no XHR from frontend. |
| `frame-src` | `https://iframe.mediadelivery.net` | Bunny Stream embed for video courses. **No 'self'**, no Stripe. |
| `media-src` | `'self' https: blob:` | Inline `<video>`/`<audio>` defensive. |
| `object-src` | `'none'` | No Flash, no `<embed>`, no `<object>`. |
| `base-uri` | `'self'` | Cannot change `<base>` to redirect relative URLs. |
| `form-action` | `'self'` | Forms submit only to AFianco. |
| `frame-ancestors` | `'none'` | Anti-clickjacking (modern equivalent of X-Frame-Options DENY). |
| `worker-src` | `'self' blob:` | Service workers / web workers. |
| `manifest-src` | `'self'` | PWA manifest. |

### What is intentionally NOT in CSP

| External | Why excluded |
|---|---|
| `https://js.stripe.com` | Stripe Checkout is full-page redirect; the frontend does NOT load stripe.js. |
| `https://api.stripe.com` | Same: backend handles Stripe API calls server-side. |
| `https://www.google-analytics.com` | We do NOT run GA. (Sentry is our only telemetry, already included.) |
| `unsafe-inline` in `script-src` | React production build does not need it; opens XSS surface. |

---

## Test plan post-deploy

After applying these headers in production, **MUST verify**:

1. **`securityheaders.com`** rating: `A` or `A+`.
2. **`observatory.mozilla.org`** score: 90+ (ideally 100).
3. **Manual browser test** (Chrome, incognito):
   - Open `afianco.app` → DevTools Console: **zero CSP violations**.
   - Login flow → no errors.
   - Storefront page → fonts load (Manrope, Public Sans visible).
   - Sentry initialization log present (`[AFIANCO observability] ✅ Sentry INITIALIZED`).
   - Trigger error (`setTimeout(() => { throw new Error('test'); }, 0)`) → arrives in Sentry.
   - Bunny Stream video player loads in customer course page (when Step Course Player is deployed).
4. **Stripe checkout E2E**: complete a test purchase flow with Stripe test card. Redirect to checkout.stripe.com works. Return URL works. No CSP violations on either page.
5. **Mobile Safari + Firefox**: at minimum spot-check, browsers differ in CSP enforcement strictness.

### How to monitor CSP violations after launch

We do **NOT** ship a `report-uri` / `report-to` directive yet (no endpoint
to receive reports). When integrating Sentry tunnel (Phase 3 task), Sentry
can also receive CSP reports — we will add `report-uri /api/sentry-tunnel/csp`
at that time.

Until then, violations are visible only in users' browser consoles. Monitor
via:
- Frontend Sentry dashboard for `SecurityError` events
- Direct user reports during beta testing
- `securityheaders.com` re-scan monthly

---

## Rollback procedure (if a header breaks something in production)

The previous CSP was very permissive (`script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' https:; ...`).
If the new CSP causes blocking issues:

```bash
# Option 1 — quick revert via SSH
ssh root@<server>
nginx_ts=$(date +%Y%m%d-%H%M%S)
cp /opt/margin-sentinel/deploy/nginx/nginx.conf /tmp/nginx-bad-${nginx_ts}.conf.bak
git -C /opt/margin-sentinel checkout HEAD -- deploy/nginx/nginx.conf  # if git is initialized
docker exec ms-nginx nginx -t
docker exec ms-nginx nginx -s reload

# Option 2 — relax CSP one directive at a time via a side-effect file
# (preferred: keeps the rest of D1 intact)
# Edit nginx.conf, change ONLY the directive that violates,
# nginx -t && nginx -s reload.
```

Document the regression and revisit during the next release window.

---

## Change log

| Date | Change | Phase / Step |
|---|---|---|
| 2026-05-08 | Initial hardening: HSTS preload + CSP rigoroso + Permissions-Policy esteso | Phase 1 Step D1 |
