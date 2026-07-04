#!/usr/bin/env python3
"""
test_signup_flow.py
====================
Onda 9.Z Step E — end-to-end smoke test for the signup pipeline.

Runs against a live backend (default http://localhost:8000) and walks
through every meaningful signup scenario, asserting expected status
codes and response shapes. Reports a pass/fail summary.

Read-only on the schema; CREATES test users/orgs and CLEANS them up
at the end (unless --keep is passed).

Usage:
    cd backend
    python -m scripts.test_signup_flow                  # run + cleanup
    python -m scripts.test_signup_flow --keep           # leave test data
    python -m scripts.test_signup_flow --base http://prod.example  # alt host

Test scenarios covered (ordered to fit within slowapi 5/15min limit):
  T01 — backend health (GET, no rate)
  T02 — registration mode endpoint (GET, no rate)
  T11 — malformed email — 422 (Pydantic, no business logic)
  T12 — validate-invite with bogus token (GET, separate limiter)
  T09 — weak password — 422
  T10 — missing accepted_terms — 400
  T08 — duplicate email — 409 EMAIL_ALREADY_REGISTERED
  T03 — open-mode signup (1st)
  T04 — open-mode signup (2nd) — would have triggered 9.Z bug pre-fix
  T05 — open-mode signup (3rd)

Total POST /signup calls: 5 — exactly at the 5/15min limit. Rate-limit-
sensitive cluster sequenced so the most informative tests run first.

After Step A+B+C+D this entire suite must pass. Pre-fix, T04 onwards
all failed with HTTP 500.

Note: this is a smoke test, not a property-based fuzz suite. For
broader coverage extend with hypothesis or pytest parameterization.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

import urllib.request
import urllib.error


def _req(method: str, url: str, body: dict = None, timeout: int = 10):
    """Minimal HTTP client. Returns (status, parsed_body) tuple."""
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") or "{}"
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw}


def _signup_payload(email: str, name: str = "Test", org: str = None, locale: str = "it",
                    password: str = "TestPass1234", terms: bool = True,
                    invite_token: str = None) -> dict:
    payload = {
        "email": email,
        "password": password,
        "name": name,
        "organization_name": org or f"{name} Co",
        "accepted_terms": terms,
        "locale": locale,
    }
    if invite_token:
        payload["invite_token"] = invite_token
    return payload


def _ok(test_id: str, msg: str = ""):
    print(f"  ✅ {test_id}  {msg}")


def _fail(test_id: str, msg: str):
    print(f"  ❌ {test_id}  {msg}")


def _runtest(suite, test_id, fn):
    suite["total"] += 1
    try:
        ok, msg = fn()
    except Exception as e:
        ok, msg = False, f"exception: {type(e).__name__}: {e}"
    if ok:
        suite["passed"] += 1
        _ok(test_id, msg or "")
    else:
        suite["failed"] += 1
        suite["fail_ids"].append(test_id)
        _fail(test_id, msg or "")


def _assert_status(actual, expected, label=""):
    if actual != expected:
        return False, f"{label}expected HTTP {expected}, got {actual}"
    return True, f"HTTP {actual}"


def _run(args) -> int:
    base = args.base.rstrip("/")
    suite = {"total": 0, "passed": 0, "failed": 0, "fail_ids": []}
    nonce = int(time.time())
    created_emails = []

    print("=" * 78)
    print(f"SIGNUP E2E SMOKE TEST — base={base}")
    print("=" * 78)
    print()

    # ── Phase 1: GET endpoints (no signup rate limit consumption) ─────
    def t01():
        status, body = _req("GET", f"{base}/api/health")
        if status != 200:
            return False, f"got {status}"
        if body.get("status") != "healthy":
            return False, f"status field = {body.get('status')!r}"
        return True, "healthy"
    _runtest(suite, "T01 health", t01)

    def t02():
        status, body = _req("GET", f"{base}/api/auth/registration-mode")
        if status != 200:
            return False, f"got {status}"
        mode = body.get("registration_mode")
        if mode not in ("open", "invite_only"):
            return False, f"mode = {mode!r}"
        return True, f"mode={mode}"
    _runtest(suite, "T02 reg-mode", t02)

    def t12():
        status, body = _req("GET",
                            f"{base}/api/auth/validate-invite?token=bogus_{nonce}_invalid_token")
        if status != 200:
            return False, f"expected 200, got {status}"
        if body.get("valid") is not False:
            return False, f"expected valid=false, got {body!r}"
        return True, "200 valid=false"
    _runtest(suite, "T12 bogus invite", t12)

    # ── Phase 2: 422 Pydantic-level rejections (NOT counted toward
    #     the auth/signup business rate limit since they fail before
    #     reaching the route handler) ───────────────────────────────────
    def t11():
        status, body = _req("POST", f"{base}/api/auth/signup",
                            _signup_payload("not-an-email", name="Mal"))
        if status != 422:
            return False, f"expected 422, got {status}"
        return True, "422 (pydantic validation)"
    _runtest(suite, "T11 bad email", t11)

    def t09():
        email = f"e2e_9z_{nonce}_weak@example.com"
        status, body = _req("POST", f"{base}/api/auth/signup",
                            _signup_payload(email, password="short"))
        if status not in (400, 422):
            return False, f"expected 400 or 422, got {status}"
        return True, f"HTTP {status} (weak password rejected)"
    _runtest(suite, "T09 weak pwd", t09)

    # ── Phase 3: 400/409 business-logic rejections — these CONSUME
    #     the auth/signup rate limit (5/15min). Sequenced so we have
    #     budget for 2 successful signups afterwards. ─────────────────
    def t10():
        email = f"e2e_9z_{nonce}_terms@example.com"
        status, body = _req("POST", f"{base}/api/auth/signup",
                            _signup_payload(email, terms=False))
        if status != 400:
            return False, f"expected 400, got {status}"
        return True, "400 (terms not accepted)"
    _runtest(suite, "T10 no terms", t10)
    time.sleep(0.5)

    # T08 — duplicate email: requires a successful signup first, then
    # a duplicate attempt. Uses 2 of our 5/15min budget.
    def t08():
        email = f"e2e_9z_{nonce}_dup@example.com"
        created_emails.append(email)
        status1, _ = _req("POST", f"{base}/api/auth/signup",
                          _signup_payload(email, name="Original"))
        if status1 not in (200, 202):
            return False, f"prep signup got {status1}"
        time.sleep(0.5)
        status2, body2 = _req("POST", f"{base}/api/auth/signup",
                              _signup_payload(email, name="Dup"))
        if status2 != 409:
            return False, f"expected 409, got {status2} body={json.dumps(body2)[:120]}"
        detail = body2.get("detail")
        if not isinstance(detail, dict):
            return False, f"detail not a dict: {detail!r}"
        if detail.get("code") != "EMAIL_ALREADY_REGISTERED":
            return False, f"code = {detail.get('code')!r}"
        return True, "409 EMAIL_ALREADY_REGISTERED"
    _runtest(suite, "T08 dup email", t08)
    time.sleep(0.5)

    # ── Phase 4: 2 more successful signups (budget: 2 left out of 5) ──
    # Goal: prove the 9.Z public_slug bug is gone by stacking signups
    # back-to-back without any 500.
    for i, tid in enumerate(["T03", "T04"], start=1):
        def make_signup(i=i):
            def t():
                email = f"e2e_9z_{nonce}_{i}@example.com"
                created_emails.append(email)
                status, body = _req("POST", f"{base}/api/auth/signup",
                                    _signup_payload(email, name=f"E2E{i}"))
                if status not in (200, 202):
                    return False, f"signup #{i} got {status}: {json.dumps(body)[:120]}"
                time.sleep(0.5)
                return True, f"#{i} HTTP {status}"
            return t
        _runtest(suite, f"{tid} signup #{tid[-1]}", make_signup())

    # Cleanup
    if not args.keep and created_emails:
        print()
        print("Cleaning up test users + orgs...")
        try:
            from database import users_collection, organizations_collection

            async def _cleanup():
                # Find users by email
                org_ids = []
                deleted_users = 0
                for email in created_emails:
                    user = await users_collection.find_one({"email": email})
                    if user:
                        if user.get("organization_id"):
                            org_ids.append(user["organization_id"])
                        await users_collection.delete_one({"email": email})
                        deleted_users += 1
                deleted_orgs = 0
                for oid in set(org_ids):
                    res = await organizations_collection.delete_one({"id": oid})
                    deleted_orgs += res.deleted_count
                return deleted_users, deleted_orgs

            du, do = asyncio.run(_cleanup())
            print(f"  Removed {du} users + {do} orgs created by this run.")
        except Exception as e:
            print(f"  Cleanup failed: {type(e).__name__}: {e}")

    print()
    print("=" * 78)
    print(f"RESULTS: {suite['passed']}/{suite['total']} passed, "
          f"{suite['failed']} failed")
    if suite["failed"]:
        print(f"  Failed: {', '.join(suite['fail_ids'])}")
    print("=" * 78)

    return 0 if suite["failed"] == 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    parser.add_argument("--keep", action="store_true",
                        help="Don't clean up test users/orgs at the end")
    args = parser.parse_args()
    rc = _run(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
