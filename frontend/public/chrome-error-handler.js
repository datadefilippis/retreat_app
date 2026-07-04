/*
 * AFianco — Chrome DataCloneError suppression (workaround for browser bug).
 *
 * Why this file exists
 * --------------------
 * Some Chrome versions throw an uncatchable DataCloneError on
 * PerformanceServerTiming objects when an extension or devtools tries
 * to serialize them. The error reaches window.onerror and floods Sentry
 * with noise about a non-issue. This handler catches and swallows it.
 *
 * Why an external file (not inline)
 * ---------------------------------
 * The Phase 1 Step D1 CSP enforces `script-src 'self' 'unsafe-eval'`
 * (no `'unsafe-inline'`). Inline <script> tags are blocked. Loading this
 * snippet as a same-origin file complies with the policy and is served
 * by nginx with the same caching headers as the rest of /static/.
 *
 * Keep this file tiny and self-contained — it must run before any
 * application code can throw. It is referenced from public/index.html
 * with a normal <script src="/chrome-error-handler.js"></script> tag.
 */
window.addEventListener(
    "error",
    function (e) {
        if (
            e.error instanceof DOMException &&
            e.error.name === "DataCloneError" &&
            e.message &&
            e.message.includes("PerformanceServerTiming")
        ) {
            e.stopImmediatePropagation();
            e.preventDefault();
        }
    },
    true
);
