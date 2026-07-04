#!/usr/bin/env bash
# Embed Widget — Smoke Test Script
#
# Esegue check rapidi sull'API embed widget:
#   - Bundle sync (E7.6)
#   - Endpoint init/{slug}
#   - Endpoint coupons/validate/{slug}
#   - Endpoint shipping-options/{slug}
#   - Endpoint legal/storefront/{slug}/privacy
#
# Usage:
#   ./scripts/embed-smoke-test.sh [SLUG] [BASE_URL]
#
# Defaults:
#   SLUG      = acme-pilot
#   BASE_URL  = http://localhost:8000
#
# Exit codes:
#   0  = tutti i check pass
#   >0 = numero di check failed

set -eu

SLUG="${1:-acme-pilot}"
BASE_URL="${2:-http://localhost:8000}"
ORIGIN="${ORIGIN:-http://localhost:8080}"

# Color codes (disabled se NO_COLOR set)
if [[ -n "${NO_COLOR:-}" ]] || [[ ! -t 1 ]]; then
  RED=""; GREEN=""; YELLOW=""; BLUE=""; RESET=""
else
  RED=$'\033[31m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  BLUE=$'\033[34m'
  RESET=$'\033[0m'
fi

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() { printf "  ${GREEN}✓${RESET} %s\n" "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { printf "  ${RED}✗${RESET} %s\n" "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
skip() { printf "  ${YELLOW}⊘${RESET} %s\n" "$1"; SKIP_COUNT=$((SKIP_COUNT+1)); }
section() { printf "\n${BLUE}━━━ %s ━━━${RESET}\n" "$1"; }

trap 'echo; echo "Summary: ${GREEN}${PASS_COUNT} pass${RESET}, ${RED}${FAIL_COUNT} fail${RESET}, ${YELLOW}${SKIP_COUNT} skip${RESET}"; exit $FAIL_COUNT' EXIT

echo "${BLUE}AFianco Embed — Smoke Test${RESET}"
echo "  SLUG:     ${SLUG}"
echo "  BASE_URL: ${BASE_URL}"
echo "  ORIGIN:   ${ORIGIN}"

# ─────────────────────────────────────────────────────────────────────
section "Bundle Sync (E7.6)"
# ─────────────────────────────────────────────────────────────────────

DIST_BUNDLE="apps/embed-sdk/dist/afianco-embed.es.js"
PUBLIC_BUNDLE="frontend/public/embed/v1/afianco-embed.es.js"

if [[ -f "$DIST_BUNDLE" && -f "$PUBLIC_BUNDLE" ]]; then
  if diff -q "$DIST_BUNDLE" "$PUBLIC_BUNDLE" >/dev/null 2>&1; then
    pass "Bundle dist == public (drift-free)"
  else
    fail "Bundle drift! Run: pnpm embed:sync-dev"
  fi
  SIZE_KB=$(($(stat -f%z "$PUBLIC_BUNDLE" 2>/dev/null || stat -c%s "$PUBLIC_BUNDLE")/1024))
  if [[ $SIZE_KB -lt 600 ]]; then
    pass "Bundle size ${SIZE_KB}KB raw (<600KB ok)"
  else
    fail "Bundle size ${SIZE_KB}KB raw (>600KB, troppo grosso)"
  fi
else
  skip "Bundle files mancanti (run pnpm embed:rebuild)"
fi

# ─────────────────────────────────────────────────────────────────────
section "Backend Health"
# ─────────────────────────────────────────────────────────────────────

if curl -sf --max-time 3 "${BASE_URL}/api/health" >/dev/null 2>&1 \
   || curl -sf --max-time 3 "${BASE_URL}/health" >/dev/null 2>&1 \
   || curl -sf --max-time 3 "${BASE_URL}/" >/dev/null 2>&1; then
  pass "Backend reachable at ${BASE_URL}"
else
  fail "Backend NOT reachable. Test rimanenti SKIPPED."
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────
section "GET /init/{slug}"
# ─────────────────────────────────────────────────────────────────────

INIT_URL="${BASE_URL}/api/public/embed/init/${SLUG}"
INIT_RESP=$(curl -sf --max-time 5 -H "Origin: ${ORIGIN}" "$INIT_URL" 2>&1 || echo "FAILED")

if [[ "$INIT_RESP" == "FAILED" ]] || [[ -z "$INIT_RESP" ]]; then
  fail "/init/${SLUG} unreachable (CORS o slug invalido?)"
else
  # Check JSON keys via grep (avoid jq dependency)
  for key in "slug" "currency" "storefront_languages" "capabilities" \
             "fulfillment_modes" "design_tokens" "privacy_policy_url" \
             "terms_service_url"; do
    if echo "$INIT_RESP" | grep -q "\"${key}\""; then
      pass "init.${key} presente"
    else
      fail "init.${key} mancante (contract regression)"
    fi
  done

  # Languages check
  if echo "$INIT_RESP" | grep -qE "\"storefront_languages\":\[[^]]*\"it\""; then
    pass "storefront_languages include 'it'"
  fi
  if echo "$INIT_RESP" | grep -qE "\"storefront_languages\":\[[^]]*\"fr\""; then
    pass "storefront_languages include 'fr'"
  else
    skip "storefront_languages NON include 'fr' (merchant config?)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────
section "GET /products/{slug}"
# ─────────────────────────────────────────────────────────────────────

PROD_URL="${BASE_URL}/api/public/embed/products/${SLUG}"
PROD_RESP=$(curl -sf --max-time 5 -H "Origin: ${ORIGIN}" "$PROD_URL" 2>&1 || echo "FAILED")

if [[ "$PROD_RESP" == "FAILED" ]]; then
  fail "/products/${SLUG} unreachable"
else
  # Verify no admin field leak (W1.4)
  for forbidden in "cost_price" "cost_source" "supplier_id" "internal_tags"; do
    if echo "$PROD_RESP" | grep -q "\"${forbidden}\""; then
      fail "LEAK: ${forbidden} esposto in /products (W1.4 regression!)"
    else
      pass "No leak: ${forbidden} non esposto"
    fi
  done

  # Items array
  if echo "$PROD_RESP" | grep -q "\"items\""; then
    pass "products.items presente"
  fi
fi

# ─────────────────────────────────────────────────────────────────────
section "GET /shipping-options/{slug}"
# ─────────────────────────────────────────────────────────────────────

SHIP_URL="${BASE_URL}/api/public/embed/shipping-options/${SLUG}"
SHIP_RESP=$(curl -sf --max-time 5 -H "Origin: ${ORIGIN}" "$SHIP_URL" 2>&1 || echo "FAILED")

if [[ "$SHIP_RESP" == "FAILED" ]]; then
  skip "Shipping-options endpoint unreachable o no opzioni configurate"
else
  if echo "$SHIP_RESP" | grep -q "\"options\""; then
    pass "shipping.options presente"
  fi
fi

# ─────────────────────────────────────────────────────────────────────
section "POST /coupons/validate/{slug} (dry-run)"
# ─────────────────────────────────────────────────────────────────────

COUPON_URL="${BASE_URL}/api/public/embed/coupons/validate/${SLUG}"
COUPON_RESP=$(curl -sf --max-time 5 \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Origin: ${ORIGIN}" \
  -H "Idempotency-Key: smoke-test-$(date +%s)" \
  -d '{"code":"INVALID_TEST","cart_subtotal":50}' \
  "$COUPON_URL" 2>&1 || echo "FAILED")

if [[ "$COUPON_RESP" == "FAILED" ]]; then
  fail "Coupon validate endpoint unreachable (W2.1 regression)"
else
  if echo "$COUPON_RESP" | grep -q "\"valid\""; then
    pass "Coupon dry-run risponde con valid flag"
  fi
fi

# ─────────────────────────────────────────────────────────────────────
section "GET /legal/storefront/{slug}/privacy (E7.4 + E7.5)"
# ─────────────────────────────────────────────────────────────────────

LEGAL_URL="${BASE_URL}/api/legal/storefront/${SLUG}/privacy"
LEGAL_RESP=$(curl -sf --max-time 5 "$LEGAL_URL" 2>&1 || echo "FAILED")

if [[ "$LEGAL_RESP" == "FAILED" ]]; then
  fail "Legal endpoint unreachable"
else
  if echo "$LEGAL_RESP" | grep -q "\"is_autogenerated\""; then
    pass "Legal response include is_autogenerated flag (E7.5)"
  else
    fail "is_autogenerated mancante (E7.5 regression!)"
  fi
  if echo "$LEGAL_RESP" | grep -q "\"content\""; then
    pass "Legal content presente (template auto-fallback se merchant non pubblicato)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────
section "CORS preflight"
# ─────────────────────────────────────────────────────────────────────

CORS_RESP=$(curl -s --max-time 5 \
  -X OPTIONS \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: GET" \
  -I "$INIT_URL" 2>&1 || echo "FAILED")

if echo "$CORS_RESP" | grep -qi "access-control-allow-origin"; then
  pass "CORS preflight OK (ORIGIN ${ORIGIN} accepted)"
else
  fail "CORS preflight REJECTED (aggiungi ${ORIGIN} a allowed_origins admin)"
fi

# Exit handled by trap
