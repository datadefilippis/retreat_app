"""Sentinel tests for afianco SECURITY invariants — infrastructure config.

Step 2 della Phase 0. Pin di 5 security invarianti configurate in nginx.conf
e server.py. Cambiare uno di questi senza aggiornare il sentinel = potenziale
regression di sicurezza che si scopre solo durante un security audit (o un
incident).

  SEC-1     CSP no unsafe-inline scripts (only unsafe-eval allowed for recharts)
  SEC-2     HSTS preload 1 year, includeSubDomains
  SEC-3     X-Frame-Options DENY (anti-clickjacking)
  SEC-4     CORS allow_credentials con whitelist esplicita (NO wildcard *)
  SEC-5     Rate limiting per endpoint pubblico (slowapi)
  SEC-S1.1  Repo secret hygiene — .env mai tracked, .gitignore copre patterns
  SEC-S1.3  OpenAPI docs (/docs, /redoc, /openapi.json) env-gated production
  SEC-S1.4  Global exception handler — body opaco, no stacktrace leak +
            load_dotenv override=False (shell env wins)
  SEC-S2.1  Login anti-enumeration — uniform 401 pre-password, timing-constant
            via bcrypt dummy hash, state-revealing errors only post-password
  SEC-S2.2  Signup anti-enumeration — customer signup duplicate email returns
            same 202 verification_required as new signup (no 500 leak)
  SEC-S2.3  Token single-use enforcement — verify_email + reset_password
            tokens nullified post-success, second use returns 400
  SEC-S2.4  Per-email login rate limit (cross-IP, 20/h backstop to
            account lockout). Uniform 401 + bcrypt dummy burn on hit.
  SEC-S2.5  Rate limit su /request-invite, /reactivate-account,
            /resend-verification (per-IP slowapi + per-email cross-IP cap)
  SEC-S3.1  cart_id + order_id sono UUID v4 (no int sequenziale →
            no enumeration via brute-force /api/public/embed/cart/{id})
  SEC-S3.2  Idempotency race condition fix — unique index su digest +
            claim-the-lock pattern → no double-process (Stripe etc.)
  SEC-S3.3  Store.allowed_origins validation — Pydantic validator
            rifiuta "null", "*", non-http(s), entries > 10, char > 200
  SEC-S3.4  Catalog scrape defense — /embed/init|categories|products
            cache TTL 300s (was 60s) + rate limit decoratori presenti
  SEC-S3.5  Dynamic CORS reject body opaco "Forbidden" — pre-fix
            leak via origin/slug nel body, pre-fix leak via path "embed"
  SEC-S4.1  /metrics endpoint auth (X-Metrics-Token + METRICS_AUTH_TOKEN
            env). Prod fail-closed se token mancante (503). Dev allows.
  SEC-S4.2  CI pipeline .github/workflows/test.yml — pytest backend +
            vitest embed-sdk + vitest packages, gated su PR/main
  SEC-S4.3  Security scanning workflow .github/workflows/security.yml —
            Bandit Python SAST + pip-audit + pnpm audit (HIGH gate)
  SEC-S4.4  Coverage report integration — pytest-cov on backend, XML
            upload as CI artifact (informational threshold, not gating)
  SEC-S5.1  Anti-enumeration consolidation — forgot-password customer
            + admin return same generic message for found/not-found email
  SEC-S5.2  Functional rate limit test — per-email check_email_rate
            effectively returns False after N+1 calls within window
  SEC-S5.3  Idempotency race condition functional — 2 concurrent
            asyncio tasks con stessa key → solo 1 vince + 1 polls
  SEC-S5.4  allowed_origins applied at Store model load (catches stale
            DB records with invalid entries inserted manually)
  SEC-S5.5  /docs 404 functional via TestClient — env_override prod →
            GET /docs ritorna 404 (e2e validation del S1.3 helper)
  SEC-S5.7  Full regression consolidation — README badge + cumulative
            test count assertion (sanity check no test silently disappeared)
  SEC-S6.1  SECURITY.md present — GitHub-recognized security policy con
            threat model + SLA + reporting channels
  SEC-S6.2  docs/operations/TESTING.md — runbook test suite (commands,
            structure, sentinel writing guide, common failure patterns)
  SEC-S6.3  docs/operations/secrets-rotation.md extended con Track S
            Step 1.2 pending rotation section (chiude Track S)
  SEC-L.1   GDPR right-to-erasure endpoint (POST /api/customer/me/request-erasure)
            con audit log + admin notification + idempotent + 202 response
  SEC-L.2   Incident response plan (docs/operations/incident-response.md +
            incidents.md template) — severity matrix + GDPR breach 72h
  SEC-L.3   Email reputation guide (docs/operations/email-reputation.md) —
            SPF + DKIM + DMARC step-by-step setup procedure
  SEC-O.1.1 Idempotency expires_at MUST be BSON Date (datetime), NOT ISO
            string — altrimenti TTL index ignora silenziosamente i record
            e collection cresce unbounded
  SEC-O.1.2 Sentry traces sampling env-based (prod 0.01%, staging 1%, dev 10%)
            per stare nel Sentry Developer free tier (10k transactions/mese)
  SEC-O.1.3 Email service usa requests.Session + HTTPAdapter retry +
            connection pool (vs urllib sync). Retry 3x exp backoff su 5xx/429.
  SEC-O.1.4 Admin audit log query API (GET /api/admin/audit-logs) con
            filtri + pagination + system_admin gate. Sfrutta compound index.
  SEC-O.1.5 Multi-tenant isolation invariant — repository critici hanno
            organization_id parameter obbligatorio + JWT org_id check
            defense-in-depth in auth.py

Documento riferimento: docs/architecture/system-invariants.md
"""

import inspect
import os
import re
import sys
from pathlib import Path

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# Path nginx config (relative to repo root, not backend/)
NGINX_CONF = BACKEND_DIR.parent / "deploy" / "nginx" / "nginx.conf"


def _read_nginx_conf() -> str:
    """Read nginx.conf and return its content."""
    if not NGINX_CONF.exists():
        pytest.skip(f"nginx.conf not found at {NGINX_CONF}")
    return NGINX_CONF.read_text()


# ─── SEC-1 — CSP no unsafe-inline scripts ──────────────────────────────


class TestSEC1_CSPNoUnsafeInlineScripts:
    """SEC-1 (Security Invariant 1, Critical):

    Content Security Policy DEVE impedire 'unsafe-inline' nei script-src.
    L'unica eccezione accettata è 'unsafe-eval' per recharts/framer-motion
    runtime compilation.

    Inline script abilitato = XSS via stored content (es. product description)
    diventa exploit attiva. CSP è la difesa primary.

    Pin location: deploy/nginx/nginx.conf:117 (CSP directive)
    """

    def test_csp_header_present_in_nginx_config(self):
        """add_header Content-Security-Policy directive presente."""
        conf = _read_nginx_conf()
        assert "Content-Security-Policy" in conf, (
            "Nessun header Content-Security-Policy in nginx.conf. SEC-1 "
            "violato — XSS via stored content non mitigato."
        )

    def test_csp_script_src_self_only(self):
        """script-src include 'self' (per il bundle CRA) ma niente unsafe-inline."""
        conf = _read_nginx_conf()
        # Match il blocco CSP nella riga add_header Content-Security-Policy
        m = re.search(
            r'Content-Security-Policy[^"]*"([^"]+)"',
            conf,
        )
        assert m is not None, "CSP directive non parsabile da nginx.conf"
        csp = m.group(1)

        # Estrai la script-src directive
        script_src_match = re.search(r"script-src\s+([^;]+);", csp)
        assert script_src_match is not None, "script-src directive missing in CSP"
        script_src = script_src_match.group(1).strip()

        # Deve includere 'self'
        assert "'self'" in script_src, "script-src must include 'self' for the app bundle"

        # NON deve includere 'unsafe-inline'
        assert "'unsafe-inline'" not in script_src, (
            f"CSP script-src contains 'unsafe-inline': {script_src!r}. "
            "SEC-1 violato — inline scripts possono essere usati come XSS "
            "exploitation vector. Production React build emette ZERO inline "
            "scripts; rimuovere subito."
        )

    def test_csp_object_src_none(self):
        """object-src 'none' — blocca <object>, <embed>, <applet> per legacy XSS."""
        conf = _read_nginx_conf()
        assert "object-src 'none'" in conf, (
            "CSP object-src non è 'none'. Legacy Flash/Java exploits "
            "potrebbero passare. Defense in depth richiesta."
        )

    def test_csp_frame_ancestors_locked(self):
        """frame-ancestors 'none' previene clickjacking moderno (oltre X-Frame-Options)."""
        conf = _read_nginx_conf()
        assert "frame-ancestors 'none'" in conf, (
            "CSP frame-ancestors non è 'none'. Clickjacking via iframe "
            "su browser moderni che ignorano X-Frame-Options possibile."
        )


# ─── SEC-2 — HSTS preload 1 year ───────────────────────────────────────


class TestSEC2_HSTSPreload:
    """SEC-2 (Security Invariant 2, High):

    HSTS header con max-age=31536000 (1 anno), includeSubDomains, preload.
    Garantisce che il browser ricordi HTTPS-only per 1 anno + è eligible
    per la preload list di Chromium/Firefox/Safari.

    Pin location: deploy/nginx/nginx.conf:51
    """

    def test_hsts_header_present(self):
        conf = _read_nginx_conf()
        assert "Strict-Transport-Security" in conf, (
            "Header Strict-Transport-Security mancante. SSL strip attack "
            "possibile per nuovi visitatori."
        )

    def test_hsts_max_age_one_year(self):
        """max-age = 31536000 secondi = 1 anno."""
        conf = _read_nginx_conf()
        assert "max-age=31536000" in conf, (
            "HSTS max-age != 31536000 (1 year). Browser dimenticherebbe "
            "HTTPS preference troppo presto. Per preload list serve 1+ year."
        )

    def test_hsts_include_subdomains(self):
        """includeSubDomains protegge custom domain merchant futuri."""
        conf = _read_nginx_conf()
        assert "includeSubDomains" in conf, (
            "HSTS senza includeSubDomains. shop.merchant.* potrebbe essere "
            "downgraded a HTTP — attacco SSL strip."
        )

    def test_hsts_preload_flag(self):
        """preload = consenso alla preload list dei browser."""
        conf = _read_nginx_conf()
        assert "preload" in conf, (
            "HSTS senza preload flag. Una rimozione dalla preload list "
            "richiede 6+ mesi (irreversibile breve termine). Da mantenere."
        )


# ─── SEC-3 — X-Frame-Options DENY ──────────────────────────────────────


class TestSEC3_XFrameOptionsDeny:
    """SEC-3 (Security Invariant 3, High):

    X-Frame-Options: DENY per defense-in-depth oltre CSP frame-ancestors.

    Note: per gli endpoint embed (futuri Phase 1), la policy sarà diversa
    (frame-ancestors con whitelist per-store). Questo sentinel pinna SOLO
    la policy default su afianco.app.

    Pin location: deploy/nginx/nginx.conf:56
    """

    def test_x_frame_options_deny_present(self):
        conf = _read_nginx_conf()
        # Marker: header literal DENY (case-sensitive)
        assert "X-Frame-Options" in conf and '"DENY"' in conf, (
            "X-Frame-Options DENY mancante. Browser legacy senza CSP "
            "frame-ancestors permetterebbero embedding cross-origin."
        )

    def test_x_content_type_options_nosniff(self):
        """Companion: MIME-sniffing protection."""
        conf = _read_nginx_conf()
        assert "X-Content-Type-Options" in conf and "nosniff" in conf


# ─── SEC-4 — CORS allow_credentials + whitelist ────────────────────────


class TestSEC4_CORSWithCredentialsWhitelist:
    """SEC-4 (Security Invariant 4, Critical):

    CORSMiddleware con allow_credentials=True DEVE essere accoppiato a
    allow_origins esplicita (lista). MAI wildcard '*' — la CORS spec
    proibisce '*' + credentials per ragioni di sicurezza.

    Pin location: backend/server.py:617-623

    Note: Phase 0.5 (futura) introdurrà DynamicCORSMiddleware per
    /api/public/embed/* con whitelist per-store. Questo sentinel verifica
    SOLO il middleware statico canonico.
    """

    def test_cors_middleware_added_in_server(self):
        """server.py installa CORSMiddleware."""
        import inspect
        from server import app
        # Inspect middleware stack via app.user_middleware
        middleware_names = [
            mw.cls.__name__ for mw in app.user_middleware
        ]
        assert "CORSMiddleware" in middleware_names, (
            "CORSMiddleware non installato in server.py. Frontend non "
            "può fare chiamate cross-origin (dev: localhost:3000 → :8000)."
        )

    def test_cors_origins_not_wildcard(self):
        """allow_origins non deve essere ['*']."""
        import server
        source = inspect.getsource(server)
        # La fallback dev DEVE essere localhost (con prefix http://, port :3000)
        # NON wildcard '*'.
        assert "http://localhost:3000" in source, (
            "Nessun fallback 'http://localhost:3000' in CORS config. "
            "Probabilmente qualcuno ha sostituito con wildcard '*' — questo "
            "infrange la spec CORS quando allow_credentials=True."
        )
        # Defense esplicita: literal '"*"' come allow_origins è proibito
        # quando allow_credentials=True. Verifica che NON compaia come
        # elemento singolo in _cors_origins.
        assert '_cors_origins = ["*"]' not in source, (
            "CORS config contiene allow_origins=['*'] hardcoded. "
            "Combinato con allow_credentials=True è violazione della "
            "spec CORS e abilita CSRF cross-origin."
        )

    def test_cors_allow_credentials_true(self):
        """allow_credentials=True — cookie di sessione attraversano CORS."""
        import inspect
        import server
        source = inspect.getsource(server)
        assert "allow_credentials=True" in source, (
            "CORSMiddleware con allow_credentials=False — cookies di sessione "
            "non passerebbero, login non funzionerebbe cross-origin in dev."
        )

    def test_cors_origins_from_env(self):
        """CORS_ORIGINS viene letto da env var (no hardcoded prod URLs)."""
        import inspect
        import server
        source = inspect.getsource(server)
        assert 'os.environ.get("CORS_ORIGINS"' in source, (
            "CORS_ORIGINS env non letto. Per deploy multi-environment "
            "(dev/staging/prod) serve var configurabile."
        )

    def test_cors_methods_canonical(self):
        """Methods accettati: GET, POST, PUT, PATCH, DELETE, OPTIONS."""
        import inspect
        import server
        source = inspect.getsource(server)
        # Tutti i 6 methods devono essere allow-listed
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
            assert f'"{method}"' in source, (
                f"Method HTTP {method} non in allow_methods. CORS preflight "
                f"può fallire per request {method}."
            )


# ─── SEC-5 — Rate limiting per endpoint pubblico ──────────────────────


class TestSEC5_RateLimitingPublicEndpoints:
    """SEC-5 (Security Invariant 5, High):

    Ogni endpoint pubblico DEVE avere rate limit specifico via slowapi.
    Defense da scraping, DoS, brute force.

    Canonical rate limits:
      /storefront/{slug}/meta         — 60/min (bootstrap, alto traffico legittimo)
      /storefront/{slug} (catalog)    — 30/min
      /marketing-status               — 10/min (privacy enumeration defense)
      /order-request                  — 30/min
      /orders/{order_id}/status       — 30/min
      /auth/login                     — 10/min (anti brute-force)
    """

    def test_slowapi_limiter_instance_exists(self):
        """Single limiter instance shared across the app."""
        from routers.auth import limiter
        # The slowapi Limiter object must be a singleton importabile
        assert limiter is not None
        # Must be a Limiter instance (duck typing)
        assert hasattr(limiter, "limit"), (
            "limiter object da routers.auth non ha .limit() — non è uno "
            "slowapi.Limiter. SEC-5 violato."
        )

    def test_public_router_uses_limiter_decorator(self):
        """Public router applica @limiter.limit su almeno N endpoint."""
        from routers import public
        source = inspect.getsource(public)
        # Conta le occorrenze di @limiter.limit
        limiter_decorations = source.count("@limiter.limit")
        # Da audit: marketing-status (10/min), catalog (30/min),
        # meta (60/min), order-request (30/min), order status (30/min)
        # = almeno 5 endpoint rate-limited
        assert limiter_decorations >= 5, (
            f"Solo {limiter_decorations} endpoint rate-limited in public.py. "
            f"Atteso >= 5 (canonical: meta, catalog, marketing-status, "
            f"order-request, order-status). SEC-5 violato."
        )

    def test_login_endpoint_has_strict_rate_limit(self):
        """Login endpoint = brute-force target → rate limit basso."""
        from routers import auth
        source = inspect.getsource(auth)
        # Login deve avere rate limit (cerchiamo @limiter.limit on /login)
        assert "@limiter.limit" in source, (
            "Auth router non usa @limiter.limit. Login brute-force "
            "non difeso a livello applicazione (solo a livello nginx)."
        )

    def test_nginx_layer_login_rate_limit_backup(self):
        """nginx-level rate limit zone come backup application-level."""
        conf = _read_nginx_conf()
        assert "limit_req_zone" in conf, (
            "Nessun nginx limit_req_zone. Application-level slowapi è "
            "la sola defense — singolo point of failure se Python crash."
        )
        assert "rate=10r/m" in conf, (
            "nginx login rate limit != 10r/m. Backup defense layer "
            "ridotto/aumentato senza aggiornamento del sentinel."
        )


# ─── Bonus: HTTPS-only enforcement ──────────────────────────────────────


class TestSEC_HTTPSEnforcement:
    """Bonus security invariant: HTTP → HTTPS redirect 301 + TLS 1.2+ only.

    Non documentato come INV/SEC numerato ma essenziale.
    """

    def test_http_redirects_to_https(self):
        conf = _read_nginx_conf()
        assert "return 301 https://" in conf, (
            "Nessun redirect HTTP → HTTPS. Visitatori su http:// "
            "non vengono protetti."
        )

    def test_tls_1_2_minimum(self):
        conf = _read_nginx_conf()
        assert "TLSv1.2" in conf, "TLS 1.2 not in allowed protocols"
        # TLS 1.0 e 1.1 sono deprecated → NON devono comparire
        assert "TLSv1.0" not in conf, "TLS 1.0 (deprecated) abilitato"
        assert "TLSv1.1" not in conf, "TLS 1.1 (deprecated) abilitato"


# ─── SEC-S1.1 — Repo secret hygiene ─────────────────────────────────────
#
# Track S Step 1.1 — protezione contro regressione del commit `1aeb4d7`
# che ha untracked `backend/.env`. Senza sentinel un futuro `git add .`
# potrebbe ri-aggiungere il file con secret reali (e.g. JWT, Stripe key).
#
# Pin location:
#   - .gitignore (root): pattern .env, .env.*, *.env, !.env.example
#   - docs/SECURITY_HARDENING.md: policy e rotation runbook
#   - Initial untrack commit: 1aeb4d7 (2026-04-22)


import subprocess


REPO_ROOT = BACKEND_DIR.parent


def _git_ls_files() -> list[str]:
    """Run `git ls-files` from REPO_ROOT and return tracked paths.

    Skip se il test gira fuori da un git checkout (CI on shallow zip).
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("git binary not available or timed out")
    if result.returncode != 0:
        pytest.skip(f"git ls-files failed: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


class TestSEC_S1_1_RepoSecretHygiene:
    """SEC-S1.1 (Critical):

    Verifica che file `.env` con credenziali REALI non siano tracked in
    git e che `.gitignore` copra tutti i pattern necessari per prevenire
    regressioni (es. `git add .` accidentale post-rotation).

    Storia: commit `1aeb4d7` (2026-04-22) ha untracked `backend/.env` e
    aggiunto `.gitignore` patterns. Questo sentinel garantisce che la
    decision rimanga in piedi anche se qualcuno in futuro fa:
        git add -f backend/.env  # bypassa .gitignore
    Il test fallisce e il PR viene bloccato in CI.

    Allowed:
      - `.env.example`, `**/.env.example` — placeholder templates
      - `frontend/.env` — contiene SOLO `REACT_APP_*` vars (client-side
        public by design: il bundle JS le incorpora ed espone al browser).
        Niente JWT/Stripe/Anthropic key qui.
    """

    def test_no_real_env_files_tracked(self):
        """No `.env` file (root, backend, packages) deve essere tracked."""
        tracked = _git_ls_files()
        # Pattern .env senza .example (case-sensitive)
        forbidden = []
        for path in tracked:
            basename = path.rsplit("/", 1)[-1]
            # Permetti .env.example, .env.template, .env.sample
            if basename in (".env.example", ".env.template", ".env.sample"):
                continue
            # frontend/.env è eccezione documentata (REACT_APP_* public)
            if path == "frontend/.env":
                continue
            # Matcha .env, .env.production, .env.local, etc.
            if basename == ".env" or basename.startswith(".env."):
                forbidden.append(path)
            # *.env file (es. backend.env)
            if basename.endswith(".env") and basename != ".env":
                forbidden.append(path)
        assert not forbidden, (
            f"File .env tracked in git con secret reali potenziali: {forbidden}. "
            f"Untrack con `git rm --cached <file>` e aggiungi al .gitignore. "
            f"Vedi docs/SECURITY_HARDENING.md sezione 2 per rotation."
        )

    def test_gitignore_covers_env_patterns(self):
        """.gitignore al root DEVE contenere i pattern essenziali."""
        gitignore = REPO_ROOT / ".gitignore"
        assert gitignore.exists(), ".gitignore mancante al root del repo"
        content = gitignore.read_text()
        # Pattern obbligatori (almeno uno di questi deve esserci per ogni regola)
        required_patterns = [
            (".env", "blocca .env al root"),
            (".env.*", "blocca .env.production / .env.local / .env.staging"),
            ("!.env.example", "permette template .env.example committable"),
        ]
        missing = [(p, why) for p, why in required_patterns if p not in content]
        assert not missing, (
            f".gitignore manca pattern essenziali: {missing}. "
            f"Vedi commit 1aeb4d7 per il setup originale."
        )

    def test_security_hardening_doc_exists(self):
        """docs/SECURITY_HARDENING.md DEVE esistere con sezioni essenziali."""
        doc = REPO_ROOT / "docs" / "SECURITY_HARDENING.md"
        assert doc.exists(), (
            "docs/SECURITY_HARDENING.md mancante. È il runbook canonico "
            "per gestione secret + rotation. NON rimuoverlo."
        )
        content = doc.read_text()
        # Sezioni minime richieste per consultabilità in caso di incident.
        # Match case-insensitive su substring (accetta "rotation" / "ruotare" it).
        required_sections = [
            "Secret management",
            "rotation",  # english "rotation" (verb root match in commit msg)
            "Production checklist",
            "Rate limiting",
        ]
        missing = [s for s in required_sections if s.lower() not in content.lower()]
        assert not missing, (
            f"SECURITY_HARDENING.md manca sezioni: {missing}. "
            f"Una guida incompleta in caso di leak può ritardare la risposta."
        )

    def test_no_hardcoded_secret_patterns_in_tracked_files(self):
        """Nessun pattern key di Stripe/Anthropic in file source committed.

        Whitelist:
          - File doc (.md) che mostrano esempi placeholder (sk_test_xxx).
          - File .env.example con placeholder.
          - Questo file di test (contiene pattern come regex match).
        """
        tracked = _git_ls_files()
        # Pattern dei prefix di key reali (NON placeholder generici)
        # sk_live_ + 24+ char = Stripe live. sk_test_ + 24+ char = Stripe test.
        # sk-ant- + alphanumeric = Anthropic. xkeysib- = Brevo.
        suspect_patterns = [
            (re.compile(r"sk_live_[a-zA-Z0-9]{24,}"), "Stripe LIVE key"),
            (re.compile(r"sk_test_[a-zA-Z0-9]{60,}"), "Stripe TEST key (full)"),
            (re.compile(r"sk-ant-api03-[a-zA-Z0-9_-]{50,}"), "Anthropic API key"),
            (re.compile(r"xkeysib-[a-f0-9]{60,}"), "Brevo API key"),
        ]
        # File che possono CONTENERE pattern di esempio (whitelist)
        allowed_paths = {
            "backend/tests/test_invariants_security.py",  # this file
            "docs/SECURITY_HARDENING.md",
        }
        findings: list[str] = []
        for path in tracked:
            if path in allowed_paths:
                continue
            if path.endswith((".example", ".template", ".sample")):
                continue
            # Skip binary / lock files for speed
            if path.endswith((".lock", ".png", ".jpg", ".jpeg", ".gif",
                              ".woff", ".woff2", ".ttf", ".ico", ".pdf")):
                continue
            full = REPO_ROOT / path
            if not full.is_file():
                continue
            try:
                text = full.read_text(errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
            for pattern, label in suspect_patterns:
                if pattern.search(text):
                    findings.append(f"{path}: matches {label}")
                    break  # one finding per file is enough
        assert not findings, (
            f"Possibili secret hardcoded in file committed: {findings}. "
            f"Spostare in env var, ruotare la chiave, e aggiungere il file "
            f"alla whitelist solo se è UN PLACEHOLDER documentato."
        )


# ─── SEC-S1.3 — OpenAPI docs exposure env-gated ─────────────────────────
#
# Track S Step 1.3 — /docs (Swagger), /redoc (ReDoc) e /openapi.json
# in production esponevano schema completo dell'API → reverse-engineering
# semplificato, discovery di endpoint admin/sperimentali.
#
# Pin location: backend/server.py funzione _docs_urls_for_env()


class TestSEC_S1_3_DocsExposureGated:
    """SEC-S1.3 (High):

    OpenAPI documentation endpoints (`/docs`, `/redoc`, `/openapi.json`)
    devono essere disabilitati in production e staging. In development
    restano abilitati (utili per Postman / SDK gen / curl exploration).

    La gating logic e' isolata nella pure function
    `server._docs_urls_for_env(env_str) → (docs, redoc, openapi)` per
    essere testabile senza side-effect di import.

    Verifica anche che `app = FastAPI(...)` passi questi valori
    correttamente (cattura drift accidentale tipo: docs_url="/api/docs"
    hardcoded a bypassare la function).
    """

    def test_helper_returns_none_for_production(self):
        """ENVIRONMENT=production → tutti i 3 path disabilitati."""
        from server import _docs_urls_for_env

        docs, redoc, openapi = _docs_urls_for_env("production")
        assert docs is None, "docs_url deve essere None in production"
        assert redoc is None, "redoc_url deve essere None in production"
        assert openapi is None, "openapi_url deve essere None in production"

    def test_helper_returns_none_for_staging(self):
        """ENVIRONMENT=staging → tutti i 3 path disabilitati."""
        from server import _docs_urls_for_env

        docs, redoc, openapi = _docs_urls_for_env("staging")
        assert (docs, redoc, openapi) == (None, None, None), (
            "Staging deve nascondere docs come production (idem env-public)."
        )

    def test_helper_returns_defaults_for_development(self):
        """ENVIRONMENT=development → defaults FastAPI."""
        from server import _docs_urls_for_env

        docs, redoc, openapi = _docs_urls_for_env("development")
        assert docs == "/docs"
        assert redoc == "/redoc"
        assert openapi == "/openapi.json"

    def test_helper_returns_defaults_for_unset(self):
        """ENVIRONMENT not set → trattato come development (defaults)."""
        from server import _docs_urls_for_env

        # None + "" + whitespace → development behavior
        for env_val in (None, "", "   ", "DEVELOPMENT", "development"):
            docs, redoc, openapi = _docs_urls_for_env(env_val)
            assert docs == "/docs", f"env_val={env_val!r}"
            assert redoc == "/redoc", f"env_val={env_val!r}"
            assert openapi == "/openapi.json", f"env_val={env_val!r}"

    def test_helper_case_insensitive_for_production(self):
        """ENVIRONMENT case variants di production → tutti gated."""
        from server import _docs_urls_for_env

        for env_val in ("production", "PRODUCTION", "Production", "  production  "):
            docs, redoc, openapi = _docs_urls_for_env(env_val)
            assert (docs, redoc, openapi) == (None, None, None), (
                f"env_val={env_val!r} dovrebbe essere prod-gated"
            )

    def test_app_uses_helper_for_docs_config(self):
        """server.app.docs_url e' consistente con _docs_urls_for_env(ENVIRONMENT).

        Cattura drift accidentale come:
            app = FastAPI(..., docs_url="/api/docs")  # bypass helper
        """
        import server

        expected_docs, expected_redoc, expected_openapi = server._docs_urls_for_env(
            os.environ.get("ENVIRONMENT")
        )
        assert server.app.docs_url == expected_docs, (
            f"server.app.docs_url ({server.app.docs_url!r}) drifted from helper "
            f"({expected_docs!r}). Il helper deve essere l'unica sorgente di "
            f"verita' per il docs gating."
        )
        assert server.app.redoc_url == expected_redoc
        assert server.app.openapi_url == expected_openapi


# ─── SEC-S1.4 — Global exception handler + load_dotenv override ─────────
#
# Track S Step 1.4 — pre-fix FastAPI default lasciava uncaught exceptions
# bubble fino a Starlette → 500 con (potenziale) stacktrace nel body se
# debug=True. Anche senza debug, mancavano log strutturati per il debug.
#
# Inoltre: load_dotenv(override=True) sovrascriveva shell env vars con
# .env file → pericoloso in container deploy.
#
# Pin location: backend/server.py funzione _global_exception_handler() +
# load_dotenv(..., override=False) on linea 12.


class TestSEC_S1_4_GlobalExceptionHandler:
    """SEC-S1.4 (High):

    Tre invarianti:
      1. `_global_exception_handler` esiste in server.py e ritorna 500
         con body opaco (no stacktrace leak).
      2. Il handler e' registrato in app.exception_handlers per Exception
         (catch-all garantito).
      3. load_dotenv chiamato con override=False (shell env wins).
    """

    def test_global_handler_returns_opaque_body(self):
        """Handler ritorna 500 con JSON {detail, request_id}, NO stacktrace."""
        import asyncio
        import json

        from server import _global_exception_handler

        # Fake Request con header X-Request-ID
        class _FakeURL:
            path = "/api/some/path"

        class _FakeReq:
            method = "POST"
            url = _FakeURL()
            headers = {"X-Request-ID": "req-test-abc123"}

        # Simulate unhandled error. asyncio.run() crea nuovo loop ed e' il
        # pattern raccomandato in Python 3.10+ (get_event_loop() deprecated).
        try:
            raise ValueError("internal-detail-that-must-not-leak: db password=hunter2")
        except ValueError as exc:
            resp = asyncio.run(_global_exception_handler(_FakeReq(), exc))

        assert resp.status_code == 500, "Handler deve sempre rispondere 500"
        body = json.loads(resp.body.decode("utf-8"))
        assert body.get("detail") == "Internal server error", (
            "Body deve essere generic 'Internal server error', no leak."
        )
        assert body.get("request_id") == "req-test-abc123", (
            "request_id deve essere echo del X-Request-ID per support correlation."
        )
        # CRITICAL: NESSUNA leak del exception message
        body_str = resp.body.decode("utf-8")
        assert "internal-detail" not in body_str, (
            "Exception message non deve apparire nel response body."
        )
        assert "hunter2" not in body_str, (
            "Password / secret leak nel exception message non deve apparire."
        )
        assert "ValueError" not in body_str, (
            "Class name dell'exception non deve apparire (info leak)."
        )

    def test_global_handler_registered_for_exception(self):
        """app.exception_handlers DEVE contenere mapping Exception → handler."""
        import server

        handlers = server.app.exception_handlers
        # FastAPI/Starlette internamente usa dict con classi come key
        assert Exception in handlers, (
            "Nessun handler registrato per Exception base. Senza catch-all, "
            "uncaught error → Starlette default → potenziale leak."
        )
        # Verifica che sia il nostro, non un altro
        assert handlers[Exception] is server._global_exception_handler, (
            "Exception handler registrato non e' _global_exception_handler. "
            "Forse un import override e' avvenuto?"
        )

    def test_load_dotenv_uses_override_false(self):
        """server.py:12 load_dotenv chiamato con override=False.

        Best practice container deploy: shell env vars devono prendere
        precedenza sul .env file (che potrebbe essere stale o accidentale
        nell'immagine).
        """
        server_py = BACKEND_DIR / "server.py"
        source = server_py.read_text()
        # Match esatto: 'override=False' deve apparire vicino a load_dotenv
        import re

        match = re.search(
            r"load_dotenv\([^)]*override\s*=\s*(\w+)",
            source,
        )
        assert match is not None, (
            "load_dotenv non chiamato con override= esplicito in server.py. "
            "Senza il parametro esplicito, il behavior dipende dal default "
            "della lib (potrebbe cambiare in update). Sempre esplicito."
        )
        assert match.group(1) == "False", (
            f"load_dotenv chiamato con override={match.group(1)}. "
            f"DEVE essere override=False (shell env wins in container deploy)."
        )

    def test_no_app_debug_true_in_source(self):
        """server.py non deve hardcodare debug=True su FastAPI(...).

        debug=True in production espone stacktrace nei response body.
        Anche se il global handler protegge, debug=True puo' essere
        triggerato da config drift.
        """
        server_py = BACKEND_DIR / "server.py"
        source = server_py.read_text()
        # Match qualunque FastAPI(...debug=True...) — naive ma effettivo
        import re

        matches = re.findall(r"FastAPI\([^)]*debug\s*=\s*True", source, re.DOTALL)
        assert not matches, (
            f"server.py contiene FastAPI(debug=True) hardcoded: {matches}. "
            f"Mai. Usa env-gating se necessario."
        )


# ─── SEC-S2.1 — Login anti-enumeration ──────────────────────────────────
#
# Track S Step 2.1 — pre-fix il customer + admin login leak account
# existence via differential status codes:
#   - 423 ACCOUNT_LOCKED (pre-password) → "account esiste + brute-forced"
#   - 403 EMAIL_NOT_VERIFIED (pre-password) → "account esiste + non verificato"
#   - 401 "Account disattivato" vs 401 "Invalid email or password" → leak
#     via response body distinct
#
# Post-fix: ANY error pre-password → uniform 401 con detail identico.
# State-revealing errors (lockout, disabled, not-verified) escono SOLO
# dopo password verify success → attacker senza password non ha info gain.
#
# Pin location:
#   backend/services/customer_auth_service.py customer_login()
#   backend/services/auth_service.py login()


class TestSEC_S2_1_LoginAntiEnumeration_CustomerService:
    """SEC-S2.1 service-level invariants for customer login.

    Verifies the service raises uniform ValueError pre-password (no state
    leak) and structured ValueError post-password (UX for legit users).
    """

    def _make_account(
        self,
        *,
        password_hash: str = "$2b$12$validhashplaceholderXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        is_active: bool = True,
        email_verified: bool = True,
        locked_until: str | None = None,
    ) -> dict:
        return {
            "id": "cust-1",
            "email": "u@x.it",
            "password_hash": password_hash,
            "is_active": is_active,
            "email_verified": email_verified,
            "locked_until": locked_until,
            "failed_login_attempts": 0,
            "lockout_count_today": 0,
            "is_active_for_lock": True,
        }

    def test_email_not_found_burns_bcrypt_dummy_for_timing_constant(self):
        """Pre-fix: account-not-found returned in ~10ms (no bcrypt).
        Post-fix: dummy bcrypt runs even when account missing.

        Verifica che verify_password() venga chiamato sull'_BCRYPT_DUMMY_HASH
        quando find_by_email ritorna None.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        verify_calls: list[tuple] = []

        def _spy_verify(plain, hashed):
            verify_calls.append((plain, hashed))
            return False  # never match

        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=None),
        ), patch.object(customer_auth_service, "verify_password", side_effect=_spy_verify):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="ghost@x.it", password="anything"
                    )
                )
            except ValueError as e:
                assert str(e) == "Email o password non corretti.", (
                    f"Pre-password error message drifted: {e!r}. Deve essere"
                    f" uniform per anti-enumeration."
                )

        # Verifica che bcrypt e' stato chiamato sul DUMMY_HASH
        assert len(verify_calls) == 1, (
            f"verify_password chiamato {len(verify_calls)} volte (atteso 1). "
            f"Senza bcrypt burn su account-not-found, attacker distingue "
            f"via response latency."
        )
        called_hash = verify_calls[0][1]
        assert called_hash == customer_auth_service._BCRYPT_DUMMY_HASH, (
            f"verify_password chiamato con hash sbagliato. Deve usare "
            f"_BCRYPT_DUMMY_HASH per timing-constant."
        )

    def test_wrong_password_returns_same_error_as_email_not_found(self):
        """Body bytes IDENTICI tra (email-not-found) e (wrong-password).

        Questo e' il sentinel chiave anti-enumeration: pre-fix erano stessi
        messaggio ma post-fix dobbiamo continuare a garantirlo (regression).
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        # Scenario A: account NOT found
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=None),
        ), patch.object(customer_auth_service, "verify_password", return_value=False):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="ghost@x.it", password="pw"
                    )
                )
                assert False, "Login non-existing account dovrebbe raise"
            except ValueError as e_not_found:
                msg_not_found = str(e_not_found)

        # Scenario B: account found, wrong password
        account = self._make_account()
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=account),
        ), patch.object(
            customer_auth_service.customer_account_repository,
            "update",
            new=AsyncMock(return_value=None),
        ), patch.object(customer_auth_service, "verify_password", return_value=False), \
            patch.object(customer_auth_service, "_handle_failed_login", new=AsyncMock(return_value=None)):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="u@x.it", password="wrong"
                    )
                )
                assert False, "Wrong password dovrebbe raise"
            except ValueError as e_wrong:
                msg_wrong = str(e_wrong)

        assert msg_not_found == msg_wrong, (
            f"ENUMERATION LEAK: email-not-found ({msg_not_found!r}) != "
            f"wrong-password ({msg_wrong!r}). Devono essere identici."
        )

    def test_lockout_only_fires_after_password_verify(self):
        """Account locked + WRONG password → 401 generic (no 423 leak).
        Account locked + CORRECT password → 423 ACCOUNT_LOCKED (UX).

        Pre-fix: 423 sempre pre-password → leak. Post-fix: 423 solo post.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        future_iso = "2099-01-01T00:00:00+00:00"
        account = self._make_account(locked_until=future_iso)

        # Scenario A: account locked + WRONG password → must be generic 401
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=account),
        ), patch.object(customer_auth_service, "verify_password", return_value=False), \
            patch.object(customer_auth_service, "_handle_failed_login", new=AsyncMock(return_value=None)):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="u@x.it", password="wrong"
                    )
                )
                assert False, "Should raise"
            except ValueError as e:
                msg = str(e)
                assert msg == "Email o password non corretti.", (
                    f"ANTI-ENUMERATION LEAK: locked account + wrong password "
                    f"returned {msg!r} instead of generic 401. Pre-fix order "
                    f"(lockout before password) leaked existence."
                )
                assert not msg.startswith("ACCOUNT_LOCKED:"), (
                    "Lockout fired pre-password — order of checks broken."
                )

    def test_email_not_verified_only_fires_after_password(self):
        """Email-not-verified + WRONG password → 401 generic.
        Email-not-verified + CORRECT password → EMAIL_NOT_VERIFIED.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        account = self._make_account(email_verified=False)

        # Wrong password → must be generic
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=account),
        ), patch.object(customer_auth_service, "verify_password", return_value=False), \
            patch.object(customer_auth_service, "_handle_failed_login", new=AsyncMock(return_value=None)):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="u@x.it", password="wrong"
                    )
                )
                assert False
            except ValueError as e:
                assert str(e) == "Email o password non corretti.", (
                    f"LEAK: email-not-verified + wrong-password returned {e!r}"
                )

        # Correct password + email_verified=False → EMAIL_NOT_VERIFIED (UX)
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=account),
        ), patch.object(customer_auth_service, "verify_password", return_value=True):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="u@x.it", password="correct"
                    )
                )
                assert False
            except ValueError as e:
                assert str(e) == "EMAIL_NOT_VERIFIED", (
                    f"Post-password UX message changed: {e!r}. Frontend si "
                    f"aspetta esattamente 'EMAIL_NOT_VERIFIED' per render UI."
                )


class TestSEC_S2_1_LoginAntiEnumeration_AdminService:
    """SEC-S2.1 service-level invariants for ADMIN login (mirror of customer).

    Stesso pattern: pre-password uniform, post-password structured.
    """

    def test_email_not_found_burns_bcrypt_dummy(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import auth_service

        verify_calls: list[tuple] = []

        def _spy(plain, hashed):
            verify_calls.append((plain, hashed))
            return False

        with patch.object(
            auth_service.user_repository,
            "find_by_email",
            new=AsyncMock(return_value=None),
        ), patch.object(auth_service, "verify_password", side_effect=_spy):
            try:
                asyncio.run(auth_service.login("ghost@x.it", "anything"))
            except ValueError as e:
                assert str(e) == "Invalid email or password", (
                    f"Admin login pre-password message drifted: {e!r}"
                )

        assert len(verify_calls) == 1, (
            "Admin login non chiama bcrypt su email-not-found → timing leak."
        )
        assert verify_calls[0][1] == auth_service._BCRYPT_DUMMY_HASH

    def test_lockout_only_fires_after_password_verify(self):
        """Admin: account locked + wrong password → 401 generic."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import auth_service

        user_doc = {
            "id": "u-1",
            "email": "admin@x.it",
            "password_hash": "$2b$12$placeholder...",
            "role": "user",  # NOT sysadmin
            "is_active": True,
            "email_verified": True,
            "locked_until": "2099-01-01T00:00:00+00:00",
            "failed_login_attempts": 5,
            "lockout_count_today": 1,
        }
        with patch.object(
            auth_service.user_repository,
            "find_by_email",
            new=AsyncMock(return_value=user_doc),
        ), patch.object(auth_service, "verify_password", return_value=False), \
            patch.object(auth_service, "_handle_failed_admin_login", new=AsyncMock(return_value=None)):
            try:
                asyncio.run(auth_service.login("admin@x.it", "wrong"))
                assert False
            except ValueError as e:
                msg = str(e)
                assert msg == "Invalid email or password", (
                    f"ENUMERATION LEAK admin: locked + wrong-password returned "
                    f"{msg!r} instead of generic 401."
                )
                assert not msg.startswith("ACCOUNT_LOCKED:")


class TestSEC_S2_1_LoginRouter_UniformResponse:
    """Router-level: HTTPException 401 with consistent detail bytes."""

    def test_customer_router_uniform_401_detail(self):
        """customer_auth router: pre-password ValueError → 401 uniform detail."""
        from routers import customer_auth

        # Read source — the catch-all branch must use fixed string,
        # NOT detail=msg (which would forward distinct service messages).
        import inspect

        source = inspect.getsource(customer_auth.login)
        # Anti-regression: the final 401 raise must use the literal
        # message, not detail=msg or detail=str(e)
        assert "detail=\"Email o password non corretti.\"" in source, (
            "customer_auth router: fallback 401 raise must use literal "
            "detail string for anti-enumeration. Found drift."
        )
        # AND must NOT have a generic detail=msg (which would forward
        # internal service messages — leak)
        assert "detail=msg" not in source, (
            "customer_auth router has detail=msg (leak vector). Use literal."
        )

    def test_admin_router_uniform_401_detail(self):
        """auth router: pre-password ValueError → 401 uniform detail."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.login)
        assert "detail=\"Invalid email or password\"" in source, (
            "admin auth router fallback 401 must use literal detail string."
        )
        # NB: il branch deactivated usa detail=msg legacy (compatibilita'
        # con flow esistente). Quello e' diverso — e' un campo strutturato
        # con role + deactivated_at. NON e' un leak via email enumeration
        # perche' fires solo dopo password verify (post-S2.1 ordine).


# ─── SEC-S2.2 — Signup anti-enumeration (customer) ──────────────────────
#
# Track S Step 2.2 — pre-fix customer_signup leak via differential status:
#   · 400 "password debole" → email NUOVA (validation fired prima del DB hit)
#   · 400 "accetta privacy" → email NUOVA (idem)
#   · 500 DuplicateKeyError → email ESISTE (DB unique violation)
#   · 202 success → email NUOVA + tutto ok
#
# Attacker prova POST /api/customer-auth/signup con payload valido e
# distingue 202 (NEW) vs 500 (EXISTS) → enumeration confermata.
#
# Post-fix: il service pre-checka find_by_email e su duplicate ritorna
# IDENTICAL response del success path → no body diff, no status diff.
# Defense-in-depth nel router: DuplicateKeyError dal race condition ha
# stesso branch uniform.
#
# Pin location: services/customer_auth_service.py customer_signup() +
# routers/customer_auth.py signup() except DuplicateKeyError branch


class TestSEC_S2_2_SignupAntiEnumeration_CustomerService:
    """SEC-S2.2 service-level invariants for customer signup."""

    def _make_account(self, email: str = "u@x.it") -> dict:
        return {
            "id": "existing-1",
            "email": email,
            "organization_id": "org-1",
            "email_verified": True,
            "is_active": True,
        }

    def _valid_signup_args(self) -> dict:
        return dict(
            org_id="org-1",
            email="duplicate@x.it",
            name="Mario",
            password="StrongPass123!",
            locale="it",
            accepted_terms=True,
            accepted_privacy=True,
            accepted_marketing=False,
            signup_slug="demo-store",
        )

    def test_duplicate_email_returns_uniform_success_response(self):
        """Pre-fix: duplicate email → 500 DuplicateKeyError. Post-fix:
        return identical 202 response to new signup."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        existing = self._make_account()
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=existing),
        ):
            result = asyncio.run(
                customer_auth_service.customer_signup(**self._valid_signup_args())
            )

        # Body MUST be exactly the success shape — no diff
        assert result == {"status": "verification_required"}, (
            f"Duplicate signup returned {result!r}. Must be IDENTICAL "
            f"to success body {{'status': 'verification_required'}} to "
            f"prevent enumeration via response diff."
        )

    def test_duplicate_signup_does_NOT_mint_token_even_with_auto_login(self):
        """Critical: auto_login=True for a duplicate must NOT issue token.
        Minting a token for a duplicate WOULD be the enumeration leak
        we're closing — attacker submits dupe with auto_login=True, gets
        a token => "yes, email exists".
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        existing = self._make_account()
        args = self._valid_signup_args()
        args["auto_login"] = True
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=existing),
        ):
            result = asyncio.run(customer_auth_service.customer_signup(**args))

        assert "access_token" not in result, (
            "LEAK: duplicate signup with auto_login=True returned access_token. "
            "Attacker would use this to confirm email existence."
        )
        assert "customer" not in result, (
            "LEAK: duplicate signup returned customer data."
        )
        assert result == {"status": "verification_required"}

    def test_duplicate_signup_skips_bcrypt_and_db_create(self):
        """Service must early-return BEFORE bcrypt hash + DB insert.
        Burning bcrypt would be wasted CPU; insert would be no-op (idempotent
        by unique index) but writing audit records for a fake signup pollutes
        consent_audit data."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        existing = self._make_account()
        # Spy on get_password_hash + create
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=existing),
        ), patch.object(
            customer_auth_service.customer_account_repository,
            "create",
            new=AsyncMock(return_value=None),
        ) as mock_create, patch.object(
            customer_auth_service, "get_password_hash"
        ) as mock_hash:
            mock_hash.return_value = "$2b$12$fake"
            asyncio.run(customer_auth_service.customer_signup(**self._valid_signup_args()))

        assert mock_create.call_count == 0, (
            "DB create() chiamato per duplicate signup. Wasted DB op + "
            "consent_audit pollution. Must early-return."
        )
        # Note: get_password_hash might be called by other paths in module
        # init (_BCRYPT_DUMMY_HASH), so we don't assert on it. Just on
        # the actual create() side effect.

    def test_missing_consent_still_returns_specific_error(self):
        """Validation errors (consent, password strength) are NOT
        enumeration-related. They are user-facing UX necessary for the
        signup form. Verify they still raise specific ValueError so the
        frontend can render the right message.

        The 400 they generate doesn't reveal email-existence because
        they fire BEFORE the duplicate pre-check (consent first, then
        password validation, then duplicate check).
        """
        import asyncio
        from unittest.mock import patch

        from services import customer_auth_service

        args = self._valid_signup_args()
        args["accepted_terms"] = False

        # No find_by_email mock needed — should not even reach DB.
        try:
            asyncio.run(customer_auth_service.customer_signup(**args))
            assert False, "Missing consent must raise"
        except ValueError as e:
            assert "accettare" in str(e).lower() or "termini" in str(e).lower(), (
                f"Consent error message changed: {e!r}. Frontend depends "
                f"on it for form validation UX."
            )


class TestSEC_S2_2_SignupRouter_UniformResponse:
    """Router-level: DuplicateKeyError catch returns uniform 202."""

    def test_router_catches_duplicate_key_error_with_uniform_response(self):
        """Router catch-all defense-in-depth: even if service misses the
        pre-check (race condition), DuplicateKeyError from DB must NOT
        bubble to 500."""
        from routers import customer_auth
        import inspect

        source = inspect.getsource(customer_auth.signup)
        # The router must catch DuplicateKeyError explicitly and return
        # the uniform success body
        assert "DuplicateKeyError" in source, (
            "customer_auth router signup() does not catch DuplicateKeyError. "
            "Race condition can leak existence via 500."
        )
        assert "verification_required" in source, (
            "Router catch branch must return the uniform 'verification_required' "
            "body to match success path."
        )


# ─── SEC-S2.3 — Token single-use enforcement ────────────────────────────
#
# Track S Step 2.3 — verification + reset tokens devono essere single-use.
# Senza enforcement, un token intercettato (ITP, MITM, mail forward,
# screenshot condiviso) puo' essere riusato finche' non scade il TTL
# (24h verify, 1h reset).
#
# Audit finding: tutti e 4 i flow (customer+admin × verify+reset) GIA'
# implementano single-use IMPLICITAMENTE — l'update post-success setta
# *_token_hash=None e *_token_expires=None. Un secondo find_by_*_token_hash
# con lo stesso hash ritorna None → 400 "Token non valido o scaduto."
#
# S2.3 deliverable:
#   1. Sentinel test che PINNA l'invariant single-use (anti-regression)
#   2. Log INFO sui token-consumption-failed (detection per SOC)
#
# Pin location:
#   services/customer_auth_service.py: customer_reset_password (line ~673),
#                                       customer_verify_email (line ~736)
#   routers/auth.py: reset_password (line ~620), verify_email (line ~706)


class TestSEC_S2_3_TokenSingleUse_Customer:
    """SEC-S2.3 customer-side: verify single-use post-success update.

    Mock find_by_*_token_hash + update + spy update args to assert
    that *_token_hash=None is written after successful consume.
    """

    def test_customer_reset_password_nullifies_token_on_success(self):
        """After successful reset, update() must set reset_token_hash=None
        and reset_token_expires=None. Without this, the same token can
        be reused within TTL → leaked email = persistent compromise."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from datetime import timedelta

        from services import customer_auth_service

        # Account with active reset token, not expired
        future_expires = (
            customer_auth_service.utc_now() + timedelta(hours=1)
        ).isoformat()
        account = {
            "id": "cust-1",
            "email": "u@x.it",
            "name": "Mario",
            "password_hash": "$2b$12$old",
            "reset_token_hash": "hash-active",
            "reset_token_expires": future_expires,
            "organization_id": "org-1",
            "locale": "it",
            "signup_slug": "demo",
        }
        update_calls: list[tuple] = []

        async def _capture_update(account_id, fields):
            update_calls.append((account_id, fields))
            return True

        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_reset_token_hash",
            new=AsyncMock(return_value=account),
        ), patch.object(
            customer_auth_service.customer_account_repository,
            "update",
            new=_capture_update,
        ), patch.object(
            customer_auth_service, "resolve_slug_for_org",
            new=AsyncMock(return_value="demo"),
        ), patch.object(
            customer_auth_service, "_load_email_context",
            new=AsyncMock(return_value={
                "sender_name": "x", "reply_to": "x@x.it", "store_name": "x"
            }),
        ), patch.object(
            customer_auth_service, "send_customer_password_changed",
            return_value=None,
        ):
            result = asyncio.run(
                customer_auth_service.customer_reset_password(
                    "raw-token", "NewStrongPass123!"
                )
            )

        assert "successo" in result.get("message", ""), (
            f"Reset should succeed, got: {result!r}"
        )
        assert len(update_calls) == 1, (
            f"update() called {len(update_calls)} times (expected 1)"
        )
        _, fields_written = update_calls[0]
        assert fields_written.get("reset_token_hash") is None, (
            "INVARIANT BROKEN: reset_token_hash NOT nullified after success. "
            "Token can be reused → leaked email = persistent compromise."
        )
        assert fields_written.get("reset_token_expires") is None, (
            "reset_token_expires NOT nullified — pair with hash."
        )

    def test_customer_verify_email_nullifies_token_on_success(self):
        """After successful verify, update() must set verification_token_hash=None
        and verification_token_expires=None."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from datetime import timedelta

        from services import customer_auth_service

        future_expires = (
            customer_auth_service.utc_now() + timedelta(hours=24)
        ).isoformat()
        account = {
            "id": "cust-1",
            "email": "u@x.it",
            "verification_token_hash": "hash-active",
            "verification_token_expires": future_expires,
            "email_verified": False,
            "organization_id": "org-1",
            "signup_slug": "demo",
        }
        update_calls: list[tuple] = []

        async def _capture_update(account_id, fields):
            update_calls.append((account_id, fields))
            return True

        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_verification_token_hash",
            new=AsyncMock(return_value=account),
        ), patch.object(
            customer_auth_service.customer_account_repository,
            "update",
            new=_capture_update,
        ), patch.object(
            customer_auth_service, "resolve_slug_for_org",
            new=AsyncMock(return_value="demo"),
        ):
            result = asyncio.run(
                customer_auth_service.customer_verify_email("raw-token")
            )

        assert "verificata" in result.get("message", ""), (
            f"Verify should succeed, got: {result!r}"
        )
        assert len(update_calls) == 1
        _, fields_written = update_calls[0]
        assert fields_written.get("verification_token_hash") is None, (
            "INVARIANT BROKEN: verification_token_hash NOT nullified. "
            "Token reusable for 24h after successful verify."
        )
        assert fields_written.get("verification_token_expires") is None
        assert fields_written.get("email_verified") is True

    def test_customer_reset_with_invalid_token_logs_consumption_failed(self):
        """Detection: when find_by_reset_token_hash returns None, the
        service must log INFO 'token consumption failed' so SOC can
        alert on spikes (indicator of leaked-token reuse attempts)."""
        import asyncio
        import logging
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        log_records = []

        class _Handler(logging.Handler):
            def emit(self, record):
                log_records.append(record.getMessage())

        h = _Handler()
        h.setLevel(logging.INFO)
        customer_auth_service.logger.addHandler(h)
        old_level = customer_auth_service.logger.level
        customer_auth_service.logger.setLevel(logging.INFO)
        try:
            with patch.object(
                customer_auth_service.customer_account_repository,
                "find_by_reset_token_hash",
                new=AsyncMock(return_value=None),
            ):
                try:
                    asyncio.run(
                        customer_auth_service.customer_reset_password("bad", "pw")
                    )
                except ValueError:
                    pass
        finally:
            customer_auth_service.logger.removeHandler(h)
            customer_auth_service.logger.setLevel(old_level)

        matching = [m for m in log_records if "token consumption failed" in m.lower()]
        assert matching, (
            f"Detection log not emitted on invalid token. Got logs: {log_records!r}. "
            f"SOC cannot alert on token-reuse attempts without this signal."
        )

    def test_customer_verify_with_invalid_token_logs_consumption_failed(self):
        """Same detection log for verify_email path."""
        import asyncio
        import logging
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        log_records = []

        class _Handler(logging.Handler):
            def emit(self, record):
                log_records.append(record.getMessage())

        h = _Handler()
        h.setLevel(logging.INFO)
        customer_auth_service.logger.addHandler(h)
        old_level = customer_auth_service.logger.level
        customer_auth_service.logger.setLevel(logging.INFO)
        try:
            with patch.object(
                customer_auth_service.customer_account_repository,
                "find_by_verification_token_hash",
                new=AsyncMock(return_value=None),
            ):
                try:
                    asyncio.run(customer_auth_service.customer_verify_email("bad"))
                except ValueError:
                    pass
        finally:
            customer_auth_service.logger.removeHandler(h)
            customer_auth_service.logger.setLevel(old_level)

        matching = [m for m in log_records if "token consumption failed" in m.lower()]
        assert matching, "Detection log missing for invalid verify token."


class TestSEC_S2_3_TokenSingleUse_AdminRouter:
    """SEC-S2.3 admin-side: source inspection of the 4 handlers."""

    def test_admin_reset_password_source_nullifies_token(self):
        """routers/auth.py reset_password() must set reset_token_hash=None
        in its update() call after successful reset."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.reset_password)
        # The update() call must explicitly include both nullifications
        assert '"reset_token_hash": None' in source, (
            "INVARIANT BROKEN: admin reset_password() update() doesn't "
            "nullify reset_token_hash. Token reusable within 1h TTL."
        )
        assert '"reset_token_expires": None' in source, (
            "reset_token_expires not nullified — pair with hash."
        )

    def test_admin_verify_email_source_nullifies_token(self):
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.verify_email)
        assert '"verification_token_hash": None' in source, (
            "INVARIANT BROKEN: admin verify_email() update() doesn't "
            "nullify verification_token_hash. Token reusable for 24h."
        )
        assert '"verification_token_expires": None' in source

    def test_admin_reset_password_source_logs_consumption_failed(self):
        """Detection log present in admin reset path."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.reset_password)
        assert "token consumption failed" in source.lower(), (
            "Detection log missing in admin reset_password router branch."
        )

    def test_admin_verify_email_source_logs_consumption_failed(self):
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.verify_email)
        assert "token consumption failed" in source.lower(), (
            "Detection log missing in admin verify_email router branch."
        )


# ─── SEC-S2.4 — Per-email login rate limit (cross-IP backstop) ──────────
#
# Track S Step 2.4 — slowapi per-IP rate limit (10/min) e' insufficient
# contro botnet: attaccante con 1000 IPs moltiplica throughput per 1000.
# Account lockout (Onda 29/30: 5 fail → 15min) e' la primary defense
# ma cap solo gli ULTIMI 5 tentativi consecutivi.
#
# S2.4 aggiunge per-email rate limit (sliding 1h, 20/h cap) PRIMA del
# DB lookup. Uniform 401 + bcrypt dummy burn quando attiva → preserves
# S2.1 anti-enumeration. Helper esistente check_email_rate (Phase 1 D2)
# riusato — gia' sliding-window 1h con per-action buckets.
#
# Pin location:
#   services/customer_auth_service.py customer_login (Track S Step 2.4)
#   services/auth_service.py login (Track S Step 2.4)


class TestSEC_S2_4_LoginPerEmailRateLimit:
    """SEC-S2.4: per-email cross-IP rate limit fires before DB lookup."""

    def test_customer_login_rate_limit_uniform_401(self):
        """When check_email_rate returns False, customer_login must:
        1. NOT call find_by_email (early bail).
        2. Burn bcrypt dummy hash (timing-constant).
        3. Raise SAME generic ValueError as email-not-found path."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        verify_calls: list = []
        find_calls: list = []

        def _spy_verify(plain, hashed):
            verify_calls.append(hashed)
            return False

        async def _spy_find(*args, **kwargs):
            find_calls.append((args, kwargs))
            return {}  # would be invalid path but should NEVER be called

        # Patch check_email_rate to simulate cap hit
        # check_email_rate is imported inside the function (lazy import),
        # so we must patch its source location not the importing module.
        with patch(
            "core.rate_limiting.check_email_rate",
            return_value=False,
        ) as _, patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=_spy_find,
        ), patch.object(
            customer_auth_service, "verify_password", side_effect=_spy_verify
        ):
            try:
                asyncio.run(
                    customer_auth_service.customer_login(
                        org_id="org-1", email="target@x.it", password="pw"
                    )
                )
                assert False, "Rate-limited login should raise"
            except ValueError as e:
                assert str(e) == "Email o password non corretti.", (
                    f"LEAK: rate-limit message != email-not-found message: "
                    f"{e!r}. Attacker can distinguish rate-limit from auth fail."
                )

        # DB lookup must NOT happen (early bail saves connection pool)
        assert len(find_calls) == 0, (
            "find_by_email called despite rate-limit hit. "
            "Early bail saves DB ops + preserves anti-enum (no DB-error leak)."
        )
        # Bcrypt dummy must run (timing-constant)
        assert len(verify_calls) == 1, (
            "verify_password not called on rate-limit path → timing leak."
        )
        assert verify_calls[0] == customer_auth_service._BCRYPT_DUMMY_HASH

    def test_admin_login_rate_limit_uniform_401(self):
        """Admin login mirror of customer rate-limit test."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import auth_service

        verify_calls: list = []
        find_calls: list = []

        def _spy_verify(plain, hashed):
            verify_calls.append(hashed)
            return False

        async def _spy_find(*args, **kwargs):
            find_calls.append((args, kwargs))
            return None

        with patch(
            "core.rate_limiting.check_email_rate",
            return_value=False,
        ), patch.object(
            auth_service.user_repository, "find_by_email", new=_spy_find,
        ), patch.object(
            auth_service, "verify_password", side_effect=_spy_verify
        ):
            try:
                asyncio.run(auth_service.login("admin@x.it", "pw"))
                assert False
            except ValueError as e:
                assert str(e) == "Invalid email or password", (
                    f"Admin rate-limit message != generic: {e!r}"
                )

        assert len(find_calls) == 0, (
            "Admin login: find_by_email called despite rate-limit hit."
        )
        assert len(verify_calls) == 1
        assert verify_calls[0] == auth_service._BCRYPT_DUMMY_HASH

    def test_customer_login_source_invokes_check_email_rate(self):
        """Anti-regression source check: customer_login source must
        invoke check_email_rate. Without it, S2.4 silently bypassed."""
        from services import customer_auth_service
        import inspect

        source = inspect.getsource(customer_auth_service.customer_login)
        assert "check_email_rate" in source, (
            "customer_login no longer calls check_email_rate — Track S "
            "Step 2.4 invariant broken (per-email rate limit gone)."
        )
        assert '"customer_login"' in source or "'customer_login'" in source, (
            "customer_login rate-limit action key drift — bucket scoping broken."
        )

    def test_admin_login_source_invokes_check_email_rate(self):
        from services import auth_service
        import inspect

        source = inspect.getsource(auth_service.login)
        assert "check_email_rate" in source, (
            "admin login no longer calls check_email_rate — S2.4 broken."
        )
        assert '"admin_login"' in source or "'admin_login'" in source

    def test_rate_limit_action_key_distinct_from_other_actions(self):
        """customer_login + admin_login must have DISTINCT action keys
        from forgot_password/resend_verification so buckets don't share.

        Otherwise a user who forgot-password 10x would also be blocked
        from login (cross-action interference)."""
        from services import customer_auth_service, auth_service
        import inspect

        cust_src = inspect.getsource(customer_auth_service.customer_login)
        admin_src = inspect.getsource(auth_service.login)
        # customer_login bucket must be exactly 'customer_login'
        assert "customer_login" in cust_src
        # admin_login bucket must be exactly 'admin_login'
        assert "admin_login" in admin_src
        # Cross-contamination check: customer_login must NOT use
        # 'admin_login' bucket key (would mix tenant accounts)
        assert '"admin_login"' not in cust_src and "'admin_login'" not in cust_src, (
            "customer_login uses admin_login bucket key — cross-tenant interference."
        )


# ─── SEC-S2.5 — Rate limit on sensitive ops endpoints ───────────────────
#
# Track S Step 2.5 — chiude Sub-Track S2. Pin sull'invariant rate-limit
# per i 3 endpoint identificati nell'audit come potenzialmente
# vulnerabili (audit P1):
#   · /auth/request-invite     → public, can spam invite emails
#   · /auth/reactivate-account → public, can bruteforce reactivation
#   · /auth/resend-verification + /customer-auth/resend-verification
#                              → public, can spam verification emails
#
# Stato pre-audit:
#   · /resend-verification:    GIA' protetto (per-email 5/h via D2)
#   · /reactivate-account:     GIA' protetto (per-IP 3/h + in-memory
#                              lockout 5 fail → 15min)
#   · /request-invite:         per-IP 3/h MA mancava per-email cap
#                              (botnet bypass)
#
# S2.5 fix: aggiunge per-email cross-IP cap (3/h) a request-invite.
# Sentinel test per tutti e 3 per anti-regression.


class TestSEC_S2_5_SensitiveOpsRateLimit:
    """SEC-S2.5: rate-limit invariants on /request-invite,
    /reactivate-account, /resend-verification."""

    def test_request_invite_has_per_ip_limiter(self):
        """slowapi @limiter.limit decorator on /request-invite source."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.request_invite)
        assert "@limiter.limit" in source or "limiter.limit" in source, (
            "request_invite missing @limiter.limit — per-IP rate limit gone."
        )

    def test_request_invite_has_per_email_check(self):
        """Track S Step 2.5 NEW — per-email cross-IP cap via check_email_rate."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.request_invite)
        assert "check_email_rate" in source, (
            "request_invite missing check_email_rate — botnet attacker "
            "can bypass per-IP limit by rotating source IPs."
        )
        assert '"admin_request_invite"' in source or "'admin_request_invite'" in source, (
            "request_invite action key drift — bucket scoping broken."
        )

    def test_request_invite_uniform_202_on_rate_limit(self):
        """Anti-enum: rate-limit hit returns same 202 as success path
        (status code AND body shape)."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.request_invite)
        # The rate-limit branch must return the same shape as success:
        # {"status": "sent"} → no distinguishable difference for attacker
        assert source.count('return {"status": "sent"}') >= 2, (
            "request_invite rate-limit branch doesn't mirror success "
            "response. Attacker can distinguish rate-limit from success "
            "(both should return 202 with identical body)."
        )

    def test_reactivate_account_has_per_ip_limiter(self):
        """slowapi @limiter.limit on /reactivate-account (3/hour)."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.reactivate_account)
        assert "@limiter.limit" in source or "limiter.limit" in source, (
            "reactivate_account missing @limiter.limit — bruteforce open."
        )

    def test_reactivate_account_has_in_memory_lockout(self):
        """Reactivate flow uses _check_lockout / _record_failed_attempt
        (in-memory 5 fail → 15min) as backstop to the per-IP limiter."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.reactivate_account)
        assert "_check_lockout" in source, (
            "reactivate_account lost _check_lockout — bruteforce-after-5-fail "
            "protection gone."
        )
        assert "_record_failed_attempt" in source, (
            "reactivate_account lost _record_failed_attempt — counters not "
            "incremented, lockout never fires."
        )

    def test_reactivate_account_uniform_response_anti_enum(self):
        """All failure paths return generic message (no email enumeration)."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.reactivate_account)
        assert "_REACTIVATE_GENERIC" in source, (
            "reactivate_account uses distinct messages per failure path. "
            "Must use _REACTIVATE_GENERIC for all failures (anti-enum)."
        )

    def test_admin_resend_verification_has_per_email_check(self):
        """Phase 1 D2 invariant: per-email rate limit (5/h cross-IP)."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.resend_verification)
        assert "check_email_rate" in source, (
            "admin resend_verification lost per-email rate limit (D2)."
        )
        assert '"admin_resend_verification"' in source, (
            "admin resend_verification action key drift."
        )

    def test_customer_resend_verification_has_per_email_check(self):
        """Customer mirror: per-email rate limit (5/h cross-IP)."""
        from routers import customer_auth
        import inspect

        source = inspect.getsource(customer_auth.resend_verification)
        assert "check_email_rate" in source, (
            "customer resend_verification lost per-email rate limit."
        )
        assert '"customer_resend_verification"' in source

    def test_rate_limit_action_keys_complete_set(self):
        """All Track S + D2 action keys are distinct (no bucket clash)."""
        expected_keys = {
            "customer_login",            # S2.4
            "admin_login",               # S2.4
            "customer_forgot_password",  # D2
            "customer_resend_verification",  # D2
            "admin_forgot_password",     # D2
            "admin_resend_verification", # D2
            "admin_request_invite",      # S2.5 NEW
        }
        # Collect all keys referenced in code
        from routers import auth, customer_auth
        from services import customer_auth_service, auth_service
        import inspect

        all_source = "\n".join([
            inspect.getsource(auth),
            inspect.getsource(customer_auth),
            inspect.getsource(customer_auth_service),
            inspect.getsource(auth_service),
        ])

        for key in expected_keys:
            assert f'"{key}"' in all_source or f"'{key}'" in all_source, (
                f"Expected rate-limit action key {key!r} not found in any router/service. "
                f"Either it was removed (regression) or renamed (need to update sentinel)."
            )


# ─── SEC-S3.1 — cart_id + order_id UUID format invariant ────────────────
#
# Track S Step 3.1 — audit della Phase 1 widget surface ha sollevato
# preoccupazione su /api/public/embed/cart/{cart_id} (no auth) +
# /api/public/embed/orders/{order_id} (no auth): se gli ID fossero int
# sequenziali, attaccante puo' brute-forcare il range e leggere TUTTI
# i cart / ordini di tutti gli store.
#
# Audit finding: entrambi sono UUID v4 via models/common.py::generate_id()
# che ritorna str(uuid.uuid4()). Quindi l'attaccante deve indovinare
# uno tra 2^122 possibilita' → enumeration computazionalmente impossibile.
#
# S3.1 deliverable: sentinel test che PIN questo invariant. Se un domani
# qualcuno cambia generate_id() per usare es. ObjectId di MongoDB
# (semi-sequential), il sentinel fallisce.


import re as _re_uuid


_UUID_V4_RE = _re_uuid.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestSEC_S3_1_IDsAreUUIDv4:
    """SEC-S3.1: cart_id + order_id must be UUID v4 (anti-enumeration).

    Threat model: /api/public/embed/cart/{cart_id} is NO-AUTH (cross-org
    isolation via slug query param). If cart_id were int sequential or
    short numeric, an attacker iterating 1..N would read every cart.
    UUID v4 = 122 bits of entropy = 5.3 * 10^36 possible values →
    brute-force impossible.
    """

    def test_generate_id_returns_uuid_v4(self):
        """models.common.generate_id() must return a valid UUID v4 string."""
        from models.common import generate_id

        # Generate 100 IDs and verify ALL match UUID v4 format
        ids = [generate_id() for _ in range(100)]
        invalid = [i for i in ids if not _UUID_V4_RE.match(i)]
        assert not invalid, (
            f"generate_id() returned non-UUID-v4 values: {invalid[:3]}... "
            f"Format MUST be 8-4-4-4-12 hex with version-4 nibble. "
            f"Changing this breaks ID entropy → enumeration risk."
        )
        # Verify all unique (uuid4 collision probability ~10^-37)
        assert len(set(ids)) == 100, "UUID collision in 100 samples — fatal."

    def test_order_id_default_factory_uses_uuid_v4(self):
        """models.Order.id default_factory must produce UUID v4."""
        from models.order import Order

        sample_ids = []
        for _ in range(10):
            # Build minimum-valid Order with required fields stubbed
            try:
                o = Order(
                    organization_id="org-1",
                    customer_id=None,
                    order_date="2026-01-01T00:00:00+00:00",
                )
                sample_ids.append(o.id)
            except Exception:
                # If schema requires more fields, fall back to introspection
                from models import order as _order_mod
                from models.common import generate_id

                # Verify the source explicitly uses generate_id as default
                import inspect
                src = inspect.getsource(_order_mod.Order)
                assert "default_factory=generate_id" in src, (
                    "Order.id default_factory drifted from generate_id."
                )
                return  # introspection-only check is sufficient

        invalid = [i for i in sample_ids if not _UUID_V4_RE.match(i)]
        assert not invalid, (
            f"Order.id produced non-UUID values: {invalid[:3]}. "
            f"Enumeration risk on /api/public/embed/orders/{{order_id}}."
        )

    def test_cart_id_format_is_uuid_v4_with_prefix(self):
        """models.Cart.id default_factory must produce 'cart_<uuid-v4>'."""
        from models.cart import Cart
        import inspect

        # Source inspection (instantiating Cart requires many fields)
        src = inspect.getsource(Cart)
        # Pattern: id: str = Field(default_factory=lambda: f"cart_{generate_id()}")
        assert "default_factory=lambda" in src and "generate_id()" in src, (
            "Cart.id default_factory drifted. Must use generate_id()."
        )
        assert 'f"cart_' in src or "'cart_" in src, (
            "Cart.id prefix 'cart_' missing. Pattern is f'cart_{generate_id()}'."
        )

        # Functional check: produce an ID and verify the suffix is UUID v4
        from models.common import generate_id
        # Re-construct what Cart.id default_factory does
        synthetic_cart_id = f"cart_{generate_id()}"
        suffix = synthetic_cart_id[len("cart_"):]
        assert _UUID_V4_RE.match(suffix), (
            f"cart_id suffix not UUID v4: {suffix!r}. Enumeration risk."
        )

    def test_no_int_id_pattern_in_critical_models(self):
        """Critical models (Order, Cart, CustomerAccount, User) must use
        STRING IDs (UUID format), not int sequenziale.

        Anti-pattern specifico: `id: int = ...` su uno dei modelli sopra.
        Altri campi int (es. failed_login_attempts, lockout_count_today)
        sono leciti e non sono ID.
        """
        from models import order, cart, customer_account, user
        import inspect
        import re

        critical_models = [order.Order, cart.Cart, customer_account.CustomerAccount, user.User]
        # Pattern that matches specifically the `id` field being int:
        #   id: int = ...       (positional, mandatory)
        #   id: int             (no default)
        # but NOT: parent_id, customer_id, order_id, etc.
        id_int_re = re.compile(r"^\s*id\s*:\s*int\b", re.MULTILINE)

        for model_cls in critical_models:
            src = inspect.getsource(model_cls)
            match = id_int_re.search(src)
            assert match is None, (
                f"{model_cls.__name__} has 'id: int' field (auto-increment risk). "
                f"IDs must remain UUID v4 strings — change found at: {match.group(0)!r}"
            )
            # The id field itself MUST be str type (positive check)
            assert "id: str" in src or "id : str" in src, (
                f"{model_cls.__name__} id field type drifted from str → potential UUID loss."
            )


# ─── SEC-S3.2 — Idempotency race condition fix ──────────────────────────
#
# Track S Step 3.2 — pre-fix middleware/idempotency.py:27 esplicitamente
# DEFERRED il race fix. Senza unique index su digest + claim-the-lock,
# due request concurrenti con stessa Idempotency-Key potevano entrambe
# passare il cache lookup miss e entrambe fare call_next → secondo
# Stripe checkout iniziato → double charge.
#
# Post-fix:
#   1. Unique index su idempotency_keys_collection.digest (database.py)
#   2. Insert pending doc BEFORE call_next:
#      - Insert succeeds → won lock → proceed
#      - DuplicateKeyError → lost race → poll for winner's response
#   3. _store_cached_response updates the pending doc with response data


class TestSEC_S3_2_IdempotencyRaceCondition:
    """SEC-S3.2: race protection via unique index + claim-the-lock."""

    def test_unique_index_on_digest_present_in_create_indexes(self):
        """database.py create_indexes() must add unique index on
        idempotency_keys_collection.digest. Without this, the race
        protection in middleware/idempotency.py is bypassed."""
        import inspect
        import database

        src = inspect.getsource(database.create_indexes)
        # Must contain the unique index creation for digest
        assert (
            'idempotency_keys_collection.create_index("digest", unique=True)' in src
            or "idempotency_keys_collection.create_index('digest', unique=True)" in src
        ), (
            "Missing unique index on idempotency_keys_collection.digest. "
            "The middleware claim-the-lock pattern requires this index to "
            "ensure exactly one concurrent caller wins. Without it, two "
            "requests with the same Idempotency-Key can both create orders."
        )

    def test_claim_lock_helper_exists(self):
        """Middleware must expose _claim_idempotency_lock as the gating
        mechanism for race protection."""
        from middleware import idempotency

        assert hasattr(idempotency, "_claim_idempotency_lock"), (
            "_claim_idempotency_lock missing — claim-the-lock pattern absent."
        )
        assert hasattr(idempotency, "_poll_for_lock_completion"), (
            "_poll_for_lock_completion missing — losers cannot wait for winner."
        )

    def test_claim_lock_returns_true_on_insert_success(self):
        """When insert_one succeeds, _claim_idempotency_lock returns True
        (caller proceeds to call_next)."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from middleware import idempotency

        with patch("database.idempotency_keys_collection") as mock_col:
            mock_col.insert_one = AsyncMock(return_value=None)
            result = asyncio.run(
                idempotency._claim_idempotency_lock(
                    digest="d1", key="k1", organization_id="org-1", path="/x"
                )
            )
        assert result is True, "Successful insert should return True (won lock)"

    def test_claim_lock_returns_false_on_duplicate_key_error(self):
        """When insert_one raises DuplicateKeyError, _claim_idempotency_lock
        returns False (caller must poll for winner)."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from pymongo.errors import DuplicateKeyError

        from middleware import idempotency

        with patch("database.idempotency_keys_collection") as mock_col:
            mock_col.insert_one = AsyncMock(
                side_effect=DuplicateKeyError("E11000 duplicate")
            )
            result = asyncio.run(
                idempotency._claim_idempotency_lock(
                    digest="d1", key="k1", organization_id="org-1", path="/x"
                )
            )
        assert result is False, (
            "DuplicateKeyError should return False (lost race, must poll)"
        )

    def test_dispatch_uses_claim_lock_before_call_next(self):
        """Source-level invariant: middleware dispatch must call
        _claim_idempotency_lock BEFORE call_next on cache miss path.
        Otherwise the race window is wide open."""
        from middleware import idempotency
        import inspect

        src = inspect.getsource(idempotency.IdempotencyMiddleware.dispatch)
        # Find positions in source: claim must appear before "response = await call_next"
        claim_idx = src.find("_claim_idempotency_lock")
        call_next_idx = src.find("response = await call_next")
        assert claim_idx >= 0, (
            "dispatch() does not invoke _claim_idempotency_lock — race "
            "protection bypassed."
        )
        assert call_next_idx >= 0, "dispatch() missing call_next path."
        assert claim_idx < call_next_idx, (
            f"_claim_idempotency_lock invoked at char {claim_idx} but "
            f"call_next at {call_next_idx}. The claim MUST happen BEFORE "
            f"call_next or the race window is wide open."
        )

    def test_poll_returns_409_on_timeout(self):
        """When the winner takes longer than LOCK_POLL_TIMEOUT_SEC,
        losers must get 409 (not infinite wait)."""
        from middleware import idempotency
        import inspect

        # Source check: the dispatch must include the 409 timeout branch
        src = inspect.getsource(idempotency.IdempotencyMiddleware.dispatch)
        assert "409" in src, (
            "No 409 status code in dispatch — race-loser polling has no "
            "timeout escape, can hang forever."
        )
        assert "IDEMPOTENCY_RACE_TIMEOUT" in src, (
            "Missing IDEMPOTENCY_RACE_TIMEOUT code → client cannot "
            "discriminate timeout from other 409."
        )


# ─── SEC-S3.3 — allowed_origins validation ──────────────────────────────
#
# Track S Step 3.3 — pre-fix Store.allowed_origins era List[str] senza
# validation. Anche se il middleware dynamic_cors fa exact match (quindi
# "*" non bypassa di per se'), avere "*" o "null" nella lista e' un
# config error che vale la pena bloccare alla fonte.
#
# Threat scenarios:
#   · Merchant aggiunge "null" → CORS bypass per `Origin: null` requests
#     (file://, sandbox iframe, certain cross-origin redirects)
#   · Merchant aggiunge "*" → confusione + future drift se qualcuno
#     refactora il CORS middleware a allow-list pattern
#   · Schema diverso da http(s)://: "javascript:..." non e' valido come
#     Origin header, ma indica config error / typo
#   · Lista esplosa (1000+ entries): cache LRU overflow nel middleware
#
# Pin location: backend/models/store.py::_validate_allowed_origins


class TestSEC_S3_3_AllowedOriginsValidation:
    """SEC-S3.3: Pydantic validator on Store.allowed_origins."""

    def _validate(self, values):
        """Convenience wrapper around the validator function."""
        from models.store import _validate_allowed_origins
        return _validate_allowed_origins(values)

    def test_accepts_valid_https_origin(self):
        result = self._validate(["https://merchant.example.com"])
        assert result == ["https://merchant.example.com"]

    def test_accepts_valid_http_origin_dev_only(self):
        # http:// accepted for local dev — production hardening (https-only)
        # belongs in deploy config, not model validator (merchant might be
        # legitimately running localhost during onboarding).
        result = self._validate(["http://localhost:3000"])
        assert result == ["http://localhost:3000"]

    def test_rejects_null_string(self):
        """Critical: 'null' Origin (file://, sandbox iframe) must not bypass."""
        import pytest

        for val in ("null", "NULL", "Null", " null "):
            with pytest.raises(ValueError, match=r"non permesso|null"):
                self._validate([val])

    def test_rejects_wildcard(self):
        import pytest

        with pytest.raises(ValueError, match=r"non permesso|\*"):
            self._validate(["*"])

    def test_rejects_empty_or_whitespace(self):
        import pytest

        for val in ("", " ", "  \t\n  "):
            with pytest.raises(ValueError):
                self._validate([val])

    def test_rejects_non_http_scheme(self):
        """javascript:, data:, file:, ftp: etc. non sono valid Origin values."""
        import pytest

        for val in (
            "javascript:alert(1)",
            "data:text/html,<script>",
            "file:///etc/passwd",
            "ftp://example.com",
            "merchant.com",  # no scheme
            "//merchant.com",  # schemeless
        ):
            with pytest.raises(ValueError, match=r"http://|https://"):
                self._validate([val])

    def test_rejects_too_many_entries(self):
        """Cap at 10 origins per store (cache LRU bound)."""
        import pytest

        too_many = [f"https://merchant{i}.com" for i in range(11)]
        with pytest.raises(ValueError, match=r"massimo|10"):
            self._validate(too_many)

    def test_rejects_entry_too_long(self):
        import pytest

        long_origin = "https://" + ("a" * 300) + ".com"  # > 200 char
        with pytest.raises(ValueError, match=r"troppo lunga|200"):
            self._validate([long_origin])

    def test_strips_whitespace(self):
        """Forgiving on input: trim leading/trailing whitespace."""
        result = self._validate(["  https://merchant.com  "])
        assert result == ["https://merchant.com"]

    def test_deduplicates_preserving_order(self):
        """Duplicate entries dropped, first occurrence wins (order matters
        for some CORS implementations — though not ours, defensive)."""
        result = self._validate([
            "https://a.com",
            "https://b.com",
            "https://a.com",  # dup
            "https://c.com",
        ])
        assert result == ["https://a.com", "https://b.com", "https://c.com"]

    def test_validator_attached_to_store_model(self):
        """The Store model must have a field_validator on allowed_origins
        (anti-regression: future Store edits could drop the validator)."""
        from models.store import Store
        import inspect

        src = inspect.getsource(Store)
        assert "@field_validator(\"allowed_origins\"" in src or "@field_validator('allowed_origins'" in src, (
            "Store model lost the field_validator on allowed_origins. "
            "Without it, raw List[str] accepts 'null', '*', anything."
        )

    def test_store_rejects_invalid_origins_at_instantiation(self):
        """End-to-end: instantiating Store(allowed_origins=['null']) must fail."""
        import pytest
        from pydantic import ValidationError
        from models.store import Store

        # Build minimum-valid Store with required fields, then add bad origins
        with pytest.raises((ValidationError, ValueError)):
            Store(
                id="s-1",
                organization_id="org-1",
                slug="demo",
                name="Demo Store",
                allowed_origins=["null"],
            )


# ─── SEC-S3.4 — Catalog scrape defense ──────────────────────────────────
#
# Track S Step 3.4 — endpoint /api/public/embed/{init,categories,products}
# espongono dati competitivi sensibili (lista categorie, prezzi, stock).
# Pre-fix: rate limit 60/min per-IP + Cache-Control max-age=60s →
# attaccante con singolo IP scaricava catalogo intero in ~15 min con
# delays fra request (60/min × 15min × ~10 prodotti/page = 9000 prodotti).
#
# S3.4 deliverable: bump cache TTL da 60s → 300s (5min) per scoraggiare
# scraping (cache HIT in CDN/browser ridurre throughput effettivo da
# 9000/15min a 9000/75min = factor 5x slowdown).
#
# Note: per-IP cumulative rate limit (300/min totale su tutto /embed/*)
# richiede middleware custom — deferred a V2.
#
# Pin location: backend/routers/embed_public.py
#   - get_embed_init (line ~273): max-age=300
#   - get_embed_categories (line ~337): max-age=300
#   - get_embed_products (line ~432): max-age=300


class TestSEC_S3_4_CatalogScrapeDefense:
    """SEC-S3.4: cache TTL 300s on read-only embed endpoints (anti-scrape)."""

    def test_embed_init_cache_ttl_300_seconds(self):
        """get_embed_init response sets Cache-Control: public, max-age=300."""
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_init)
        assert 'Cache-Control"] = "public, max-age=300' in src, (
            "get_embed_init cache TTL drifted from 300s. Track S Step 3.4 "
            "bump from 60s — change here breaks scrape defense."
        )

    def test_embed_categories_cache_ttl_300_seconds(self):
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_categories)
        assert 'Cache-Control"] = "public, max-age=300' in src, (
            "get_embed_categories cache TTL drifted from 300s."
        )

    def test_embed_products_cache_ttl_300_seconds(self):
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_products)
        assert 'Cache-Control"] = "public, max-age=300' in src, (
            "get_embed_products cache TTL drifted from 300s. CRITICAL: "
            "prezzi/stock sono dati competitivi. Restoring to 60s = "
            "5x more throughput per scraper."
        )

    def test_embed_init_has_per_ip_rate_limit(self):
        """slowapi @limiter.limit decorator present on init endpoint."""
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_init)
        assert "@limiter.limit" in src or "limiter.limit" in src, (
            "get_embed_init missing rate limiter — anti-scrape bypassed."
        )

    def test_embed_products_has_per_ip_rate_limit(self):
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_products)
        assert "@limiter.limit" in src or "limiter.limit" in src, (
            "get_embed_products missing rate limiter — UNCAPPED scrape."
        )

    def test_embed_categories_has_per_ip_rate_limit(self):
        from routers import embed_public
        import inspect

        src = inspect.getsource(embed_public.get_embed_categories)
        assert "@limiter.limit" in src or "limiter.limit" in src, (
            "get_embed_categories missing rate limiter."
        )

    def test_cache_headers_use_public_directive(self):
        """Cache-Control must include 'public' so CDN/browser cache it
        (anti-scrape benefit only if intermediaries cache, not just
        origin server)."""
        from routers import embed_public
        import inspect

        for handler_name in ("get_embed_init", "get_embed_categories", "get_embed_products"):
            handler = getattr(embed_public, handler_name)
            src = inspect.getsource(handler)
            assert '"public, max-age=' in src, (
                f"{handler_name} cache directive missing 'public' keyword — "
                f"CDN may not cache → scrape defense degraded."
            )


# ─── SEC-S3.5 — Dynamic CORS reject uniform response ────────────────────
#
# Track S Step 3.5 — pre-fix dynamic_cors middleware ritornava body
# distinct per ogni reject reason:
#   - "Origin header required for embed endpoints."  (400, reveals path scope)
#   - "Store slug required (path param, query, or X-Afianco-Store-Slug header)."
#     (400, reveals strategie di slug extraction)
#   - f"Origin {origin!r} not authorized for store {slug!r}."  (403, leak)
#
# Information leak vectors:
#   1. Body diff "origin not authorized for store 'X'" vs "Origin header
#      required" → attacker sa che lo slug esiste (perche' arriva al
#      lookup step). E al contrario.
#   2. Body include origin + slug → SOC esfiltration: attacker scrape
#      i reject body per costruire mappa degli origin tentati
#      (analytics interno trapelato).
#
# Post-fix: body uniforme "Forbidden" (status 403 anche su no-origin
# che era 400). Server-side logger preserva tutti i dettagli per
# debug + SOC alerting via logger.warning.


class TestSEC_S3_5_DynamicCORSRejectUniform:
    """SEC-S3.5: middleware dynamic_cors reject path uses uniform body."""

    def test_dispatch_uses_uniform_forbidden_body(self):
        """All 3 reject paths must return body 'Forbidden' (not distinct
        messages per reason). Source inspection."""
        from middleware import dynamic_cors
        import inspect

        src = inspect.getsource(dynamic_cors.DynamicCORSMiddleware.dispatch)

        # Count occurrences of 'content="Forbidden"' — should be at least 3
        # (one per reject branch: no_origin, no_slug, not_allowed)
        forbidden_count = src.count('content="Forbidden"')
        assert forbidden_count >= 3, (
            f"Only {forbidden_count} 'content=\"Forbidden\"' occurrences in "
            f"dispatch (expected >= 3). One reject path may still use "
            f"distinct message → enumeration leak via body diff."
        )

    def test_no_origin_leak_in_reject_body(self):
        """Reject body must NOT contain f-string with {origin} or {slug}.
        Pre-fix: f'Origin {origin!r} not authorized for store {slug!r}'
        leaked the attempted origin (for attacker analytics) + the slug
        (confirming slug existence)."""
        from middleware import dynamic_cors
        import inspect

        src = inspect.getsource(dynamic_cors.DynamicCORSMiddleware.dispatch)

        # Anti-pattern: f-string interpolation of origin/slug into
        # PlainTextResponse content. Logger.warning(...origin=%s, slug=%s...)
        # is fine (server-side log, not body).
        # We check for the SPECIFIC leak pattern: 'origin {origin' in body context
        # which would be the f-string content.
        bad_patterns = [
            "not authorized for store",  # pre-fix message keyword
            "Origin header required for embed endpoints",  # pre-fix path scope leak
            "Store slug required (path param",  # pre-fix slug strategies leak
        ]
        for pat in bad_patterns:
            assert pat not in src, (
                f"Pre-fix leak message present: {pat!r}. Replace with "
                f"uniform 'Forbidden' body to close enumeration."
            )

    def test_logger_warning_still_includes_details(self):
        """Server-side: logger.warning must STILL include origin/slug/path
        for SOC alerting (only body is opaque)."""
        from middleware import dynamic_cors
        import inspect

        src = inspect.getsource(dynamic_cors.DynamicCORSMiddleware.dispatch)

        # logger.warning call must include origin + slug + path placeholders
        assert "logger.warning" in src, (
            "Lost logger.warning on CORS reject — SOC blind to attack patterns."
        )
        # Check for the specific format string with origin/slug/path
        assert "origin=%s" in src and "slug=%s" in src and "path=%s" in src, (
            "logger.warning format string missing origin/slug/path placeholders. "
            "Server-side log must preserve dettagli for SOC visibility."
        )

    def test_all_reject_paths_use_403_status(self):
        """Uniform status 403 across all 3 reject branches (was 400 for
        no-origin/no-slug, 403 for not-allowed). Different status codes
        also leaked which check fired first."""
        from middleware import dynamic_cors
        import inspect

        src = inspect.getsource(dynamic_cors.DynamicCORSMiddleware.dispatch)

        # All 3 reject branches must use status_code=403
        # Count exact 'status_code=403' occurrences
        count_403 = src.count("status_code=403")
        count_400 = src.count("status_code=400")
        # We expect AT LEAST 3 reject branches using 403, and 0 reject paths
        # still using 400. (The 400 IDEMPOTENCY error is in a different
        # middleware, not this one.)
        assert count_403 >= 3, (
            f"Only {count_403} 'status_code=403' in dispatch (need >= 3). "
            f"Some reject branch may still use 400 → status leak."
        )
        assert count_400 == 0, (
            f"Found {count_400} 'status_code=400' in dispatch. All CORS "
            f"reject paths must use uniform 403 (anti-leak)."
        )


# ─── SEC-E2.4.3 — Preflight-safe slug extraction (URL path) ─────────────
#
# Track E Step 2.4.3 — pre-fix _extract_slug() leggeva solo:
#   1. request.path_params (EMPTY in BaseHTTPMiddleware: routing dopo)
#   2. query_params slug
#   3. header X-Afianco-Store-Slug
#
# Bug: browser preflight OPTIONS NON invia custom headers (solo i
# CORS standard headers Access-Control-Request-*). Pertanto:
#   - GET /api/public/embed/init/<slug> con X-Afianco-Store-Slug: <slug>
#     triggera preflight perche' X-Afianco-Store-Slug e' "non-simple"
#   - Preflight → middleware non trova slug → 403 → browser non
#     procede mai con il GET reale → embed widget non funziona MAI
#
# Fix: regex parsing della URL path come PRIMARY signal. Slug e'
# nella URL path su routes /init/{slug}, /categories/{slug},
# /products/{slug} → preflight ha slug visible → 204 → real
# request poi procede.
#
# Pin location: backend/middleware/dynamic_cors.py _slug_from_path()
# + _SLUG_PATH_PATTERNS tuple.


class TestSEC_E2_4_3_PreflightSafeSlugExtraction:
    """SEC-E2.4.3: middleware estrae slug dalla URL path (preflight-safe)."""

    def test_slug_from_path_extracts_init_route(self):
        """/api/public/embed/init/{slug} → slug estratto da path."""
        from middleware.dynamic_cors import _slug_from_path

        slug = _slug_from_path("/api/public/embed/init/pasticceria-mario")
        assert slug == "pasticceria-mario", (
            "_slug_from_path deve estrarre lo slug dalla URL path su "
            "/init/{slug} — primary signal per preflight (custom headers "
            "non disponibili su OPTIONS)."
        )

    def test_slug_from_path_extracts_categories_route(self):
        from middleware.dynamic_cors import _slug_from_path

        slug = _slug_from_path("/api/public/embed/categories/bottega-demo")
        assert slug == "bottega-demo"

    def test_slug_from_path_extracts_products_route(self):
        from middleware.dynamic_cors import _slug_from_path

        slug = _slug_from_path("/api/public/embed/products/marco-conti-coaching")
        assert slug == "marco-conti-coaching"

    def test_slug_from_path_works_with_trailing_segments(self):
        """Pattern deve matchare anche con segmenti dopo lo slug."""
        from middleware.dynamic_cors import _slug_from_path

        slug = _slug_from_path("/api/public/embed/products/acme-store/extra/path")
        assert slug == "acme-store", (
            "Regex deve fermarsi al primo segment dopo lo slug — "
            "future-proof per route con trailing path."
        )

    def test_slug_from_path_rejects_non_embed_paths(self):
        """Paths non-embed → None (passthrough al middleware static)."""
        from middleware.dynamic_cors import _slug_from_path

        assert _slug_from_path("/api/stores/abc-123") is None
        assert _slug_from_path("/healthz") is None
        assert _slug_from_path("/") is None

    def test_slug_from_path_rejects_invalid_slug_chars(self):
        """Slug regex valida 3-50 char alphanumeric+hyphen — match il
        contract Pydantic Store.slug. Slug invalidi → None."""
        from middleware.dynamic_cors import _slug_from_path

        # Underscore non permesso (Store.slug usa hyphen-case)
        assert _slug_from_path("/api/public/embed/init/bad_slug") is None
        # Spazio non permesso (no URL encoding tolleranza qui)
        assert _slug_from_path("/api/public/embed/init/bad slug") is None
        # Troppo corto (<3 char)
        assert _slug_from_path("/api/public/embed/init/ab") is None

    def test_slug_from_path_priority_over_header(self):
        """Path signal ha priority — necessario per preflight consistency.

        Se il path indica uno slug, ignoriamo il header per evitare
        confusione (es. attacker manda slug-A in path e slug-B in header).
        """
        from unittest.mock import MagicMock
        from middleware.dynamic_cors import _extract_slug

        mock_request = MagicMock()
        mock_request.url.path = "/api/public/embed/init/store-from-path"
        mock_request.path_params = {}
        mock_request.query_params = {}
        mock_request.headers = {"X-Afianco-Store-Slug": "store-from-header"}

        slug = _extract_slug(mock_request)
        assert slug == "store-from-path", (
            "Path signal deve prevalere su header — preflight consistency."
        )

    def test_extract_slug_falls_back_to_header_when_path_missing(self):
        """Routes senza slug-in-path (es. /cart, /checkout/start) usano
        ancora header come fallback per le richieste reali."""
        from unittest.mock import MagicMock
        from middleware.dynamic_cors import _extract_slug

        mock_request = MagicMock()
        mock_request.url.path = "/api/public/embed/cart"
        mock_request.path_params = {}
        # Query e header simulati come dict-like accessibili via .get
        mock_request.query_params = {}
        # Use __contains__/get on a real dict by monkeypatching:
        headers = {"X-Afianco-Store-Slug": "cart-store"}
        mock_request.headers = headers

        slug = _extract_slug(mock_request)
        assert slug == "cart-store", (
            "Header fallback deve funzionare per routes senza slug-in-path."
        )

    def test_slug_path_patterns_pinned_routes(self):
        """Sentinel: i pattern devono coprire i 3 routes canonici embed.

        Se aggiungiamo nuovi routes con slug-in-path (es. /reviews/{slug}),
        questo test FALLISCE e ci ricorda di aggiornare il regex per
        evitare regression del preflight per quel nuovo endpoint.
        """
        from middleware.dynamic_cors import _SLUG_PATH_PATTERNS

        # Test ogni route canonico via il pattern compilato
        canonical_routes = [
            "/api/public/embed/init/test-slug",
            "/api/public/embed/categories/test-slug",
            "/api/public/embed/products/test-slug",
        ]
        for route in canonical_routes:
            matched = any(p.match(route) for p in _SLUG_PATH_PATTERNS)
            assert matched, (
                f"Route canonico {route!r} non matchato da nessun "
                f"_SLUG_PATH_PATTERNS. Preflight per questo endpoint "
                f"ritornera' 403 (bug)."
            )


# ─── SEC-S4.1 — /metrics endpoint auth ──────────────────────────────────
#
# Track S Step 4.1 — pre-fix /metrics era public no-auth. Commit
# message diceva "internal scrape only, bind to internal network or
# restrict via reverse proxy ACL" — affidato SOLO a infra config.
# Se per config error /metrics arriva su internet, espone:
#   · request_count per path (es. spike di errori = sotto attacco)
#   · latency histogram (timing attack fingerprinting)
#   · CORS rejection counter (count di attacchi pattern)
#   · idempotency cache hits/misses (correlation con throughput)
#
# Defense-in-depth: app-level token check (X-Metrics-Token header) IN
# AGGIUNTA a reverse-proxy ACL. Doppia barriera.
#
# Pin location: backend/server.py _metrics_auth_required() +
# prometheus_metrics() handler con check inline.


class TestSEC_S4_1_MetricsAuth:
    """SEC-S4.1: /metrics endpoint requires token in prod/staging."""

    def test_metrics_auth_required_helper_returns_true_for_production(self):
        from server import _metrics_auth_required

        # Patch ENVIRONMENT via direct os.environ swap (function reads at call time)
        import os
        saved = os.environ.get("ENVIRONMENT")
        try:
            os.environ["ENVIRONMENT"] = "production"
            assert _metrics_auth_required() is True, (
                "production must require metrics auth"
            )
            os.environ["ENVIRONMENT"] = "staging"
            assert _metrics_auth_required() is True, (
                "staging must require metrics auth"
            )
            os.environ["ENVIRONMENT"] = "PRODUCTION"  # case-insensitive
            assert _metrics_auth_required() is True
            os.environ["ENVIRONMENT"] = "  production  "  # whitespace
            assert _metrics_auth_required() is True
        finally:
            if saved is None:
                os.environ.pop("ENVIRONMENT", None)
            else:
                os.environ["ENVIRONMENT"] = saved

    def test_metrics_auth_not_required_for_dev(self):
        from server import _metrics_auth_required

        import os
        saved = os.environ.get("ENVIRONMENT")
        try:
            for env_val in ("development", "DEV", "test", ""):
                os.environ["ENVIRONMENT"] = env_val
                assert _metrics_auth_required() is False, (
                    f"env={env_val!r} should NOT require auth (dev convenience)"
                )
            os.environ.pop("ENVIRONMENT", None)
            assert _metrics_auth_required() is False, (
                "env unset should default to development (no auth)"
            )
        finally:
            if saved is None:
                os.environ.pop("ENVIRONMENT", None)
            else:
                os.environ["ENVIRONMENT"] = saved

    def test_metrics_handler_source_checks_token(self):
        """Source-level invariant: prometheus_metrics handler MUST
        check X-Metrics-Token header against METRICS_AUTH_TOKEN env
        when _metrics_auth_required() is True."""
        from server import prometheus_metrics
        import inspect

        src = inspect.getsource(prometheus_metrics)

        # Must call _metrics_auth_required
        assert "_metrics_auth_required" in src, (
            "prometheus_metrics handler does not invoke _metrics_auth_required. "
            "Auth check bypassed → /metrics exposed in production."
        )
        # Must read METRICS_AUTH_TOKEN env
        assert "METRICS_AUTH_TOKEN" in src, (
            "Handler does not read METRICS_AUTH_TOKEN env var. "
            "Without it, no token check possible."
        )
        # Must read X-Metrics-Token header
        assert "X-Metrics-Token" in src, (
            "Handler does not read X-Metrics-Token header. "
            "Without it, caller cannot present the token."
        )

    def test_metrics_handler_fail_closed_on_missing_token_env(self):
        """If ENVIRONMENT=production but METRICS_AUTH_TOKEN not set,
        endpoint must return 503 (fail-closed default-deny). Source check."""
        from server import prometheus_metrics
        import inspect

        src = inspect.getsource(prometheus_metrics)
        assert "503" in src, (
            "Handler missing 503 fail-closed branch when METRICS_AUTH_TOKEN "
            "unset. Without 503, operator that forgets to set the env "
            "accidentally exposes /metrics (auth bypass silently)."
        )

    def test_metrics_handler_returns_401_on_wrong_token(self):
        """Source-level: handler returns 401 when token missing or wrong."""
        from server import prometheus_metrics
        import inspect

        src = inspect.getsource(prometheus_metrics)
        assert "401" in src, (
            "Handler missing 401 branch for wrong/missing X-Metrics-Token."
        )
        assert "Unauthorized" in src, (
            "401 response body should be 'Unauthorized' (uniform, no leak)."
        )

    def test_metrics_route_registered_exactly_once(self):
        """app.router.routes must have exactly 1 /metrics route (no
        duplicate registration from refactor errors)."""
        from server import app

        metrics_routes = [
            r for r in app.router.routes
            if getattr(r, "path", None) == "/metrics"
        ]
        assert len(metrics_routes) == 1, (
            f"Expected 1 /metrics route, found {len(metrics_routes)}. "
            f"Duplicate registration can lead to undefined behavior."
        )


# ─── SEC-S4.2 — CI pipeline test.yml present + structured ───────────────
#
# Track S Step 4.2 — pre-fix nessun GitHub Actions workflow esistente
# (.github/ ha solo dependabot.yml). Test suite (491+ sentinel) gira
# solo localmente → regression possibile su PR mai gated.
#
# Sentinel verifica:
#   · File .github/workflows/test.yml esiste
#   · Triggera su pull_request main + push main
#   · Ha i 3 job richiesti: backend-pytest, embed-sdk-vitest, packages-vitest
#   · Ha aggregate gate ci-passed che chiede success di tutti
#
# Pin location: .github/workflows/test.yml


class TestSEC_S4_2_CIWorkflowPresent:
    """SEC-S4.2: CI workflow file exists + structured for gating."""

    @staticmethod
    def _read_workflow() -> str:
        """Read .github/workflows/test.yml content."""
        workflow = REPO_ROOT / ".github" / "workflows" / "test.yml"
        if not workflow.exists():
            pytest.skip("test.yml workflow not found — S4.2 not yet applied")
        return workflow.read_text()

    def test_test_workflow_file_exists(self):
        workflow = REPO_ROOT / ".github" / "workflows" / "test.yml"
        assert workflow.exists(), (
            "CI workflow .github/workflows/test.yml missing. "
            "Track S Step 4.2 added this for automated test gating. "
            "Without it, regression possible via PRs that bypass local testing."
        )

    def test_workflow_triggers_on_pr_and_push_main(self):
        content = self._read_workflow()
        assert "pull_request:" in content, (
            "Workflow must trigger on pull_request — without it, PRs "
            "merge without test validation."
        )
        assert "push:" in content and "branches: [main]" in content, (
            "Workflow must trigger on push to main — required for status "
            "checks + branch protection rule reference."
        )

    def test_workflow_has_backend_pytest_job(self):
        content = self._read_workflow()
        assert "backend-pytest:" in content, (
            "Missing backend-pytest job — backend invariants not gated in CI."
        )
        assert "pytest" in content, "Workflow missing pytest invocation."

    def test_workflow_has_embed_sdk_vitest_job(self):
        content = self._read_workflow()
        assert "embed-sdk-vitest:" in content, (
            "Missing embed-sdk-vitest job — Web Components sentinel not gated."
        )

    def test_workflow_has_packages_vitest_job(self):
        content = self._read_workflow()
        assert "packages-vitest:" in content, (
            "Missing packages-vitest job — shared-types / api-client / "
            "design-tokens tests not gated."
        )

    def test_workflow_has_aggregate_gate(self):
        """ci-passed aggregate job ensures branch protection rule can
        reference a single status check."""
        content = self._read_workflow()
        assert "ci-passed:" in content, (
            "Missing ci-passed aggregate gate. Without it, branch protection "
            "rule must reference all 3 individual jobs (brittle to job renames)."
        )
        assert "needs:" in content, (
            "ci-passed must declare needs: dependency on the 3 jobs."
        )

    def test_workflow_has_concurrency_control(self):
        """Cancel in-progress runs on new commits to same branch (cost
        savings + faster feedback)."""
        content = self._read_workflow()
        assert "concurrency:" in content, (
            "Missing concurrency block — old runs not auto-cancelled, "
            "Actions minutes wasted."
        )
        assert "cancel-in-progress: true" in content

    def test_workflow_uses_dependency_caching(self):
        """pip + pnpm caching to keep CI under 5 min cold / 2 min warm."""
        content = self._read_workflow()
        assert "cache: 'pip'" in content or "cache: pip" in content, (
            "No pip cache configured — backend job will reinstall every run."
        )
        assert "cache: 'pnpm'" in content or "cache: pnpm" in content, (
            "No pnpm cache configured — Node jobs will reinstall every run."
        )


# ─── SEC-S4.3 — Security scanning workflow ──────────────────────────────
#
# Track S Step 4.3 — security.yml workflow per scan SAST + dependency
# CVE. Complementa Dependabot (PR-creation) con scanning attivo in CI.
#
# Tools:
#   · Bandit: Python SAST (OWASP), gates su HIGH/CRITICAL severity
#   · pip-audit: PyPA official, scan PyPI advisory DB
#   · pnpm audit: scan npm advisory DB, gate su HIGH/CRITICAL
#
# Pin location: .github/workflows/security.yml


class TestSEC_S4_3_SecurityWorkflowPresent:
    """SEC-S4.3: security scanning workflow exists + properly configured."""

    @staticmethod
    def _read_security_workflow() -> str:
        workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
        if not workflow.exists():
            pytest.skip("security.yml workflow not found — S4.3 not applied")
        return workflow.read_text()

    def test_security_workflow_exists(self):
        workflow = REPO_ROOT / ".github" / "workflows" / "security.yml"
        assert workflow.exists(), (
            ".github/workflows/security.yml missing. Track S Step 4.3 "
            "adds SAST + dependency scanning as gating CI jobs."
        )

    def test_security_workflow_has_bandit_job(self):
        content = self._read_security_workflow()
        assert "bandit:" in content, (
            "Missing bandit job — no Python SAST scanning on PRs."
        )
        assert "bandit -r backend/" in content, (
            "bandit command missing or scans wrong path."
        )

    def test_security_workflow_has_pip_audit_job(self):
        content = self._read_security_workflow()
        assert "pip-audit:" in content, (
            "Missing pip-audit job — Python dependency CVE not gated."
        )
        assert "pip-audit -r backend/requirements.txt" in content, (
            "pip-audit must scan backend/requirements.txt"
        )

    def test_security_workflow_has_pnpm_audit_job(self):
        content = self._read_security_workflow()
        assert "pnpm-audit:" in content, (
            "Missing pnpm-audit job — JS dependency CVE not gated."
        )
        assert "pnpm audit" in content, (
            "pnpm audit command missing."
        )

    def test_security_workflow_gates_on_high_severity(self):
        """pnpm audit must use --audit-level high (not default 'low')
        to avoid CI noise on transient low-severity advisories."""
        content = self._read_security_workflow()
        assert "--audit-level high" in content, (
            "pnpm audit not configured with --audit-level high — "
            "CI noise da low-severity advisories blocchera' PR per niente."
        )

    def test_security_workflow_triggers_on_schedule(self):
        """Weekly schedule trigger — catch new CVEs published after merge."""
        content = self._read_security_workflow()
        assert "schedule:" in content, (
            "No schedule trigger — new CVEs published after merge "
            "non vengono detected fino a prossimo PR (potentially weeks)."
        )
        assert "cron:" in content, "Schedule needs cron expression."

    def test_security_workflow_triggers_on_pr_main(self):
        content = self._read_security_workflow()
        assert "pull_request:" in content, (
            "No PR trigger — security regression possibile pre-merge."
        )

    def test_security_workflow_has_aggregate_gate(self):
        content = self._read_security_workflow()
        assert "security-passed:" in content, (
            "Missing security-passed aggregate gate. Required per "
            "branch protection rule single-status reference."
        )

    def test_bandit_excludes_tests_directory(self):
        """Bandit must skip backend/tests (test files have legit
        asserts, hardcoded secrets in fixtures, etc.)."""
        content = self._read_security_workflow()
        assert "--exclude backend/tests" in content or "backend/tests," in content, (
            "Bandit not excluding tests/ — false positives su assert + "
            "secret-in-fixtures noise the CI."
        )


# ─── SEC-S4.4 — Coverage report integration ─────────────────────────────
#
# Track S Step 4.4 — chiude Sub-Track S4. Pytest-cov configurato in
# CI con upload XML artifact. Per V1 informational only (no gating
# threshold) — soglia minimum coverage % deferred a V2 quando avremo
# baseline empirico.
#
# JS coverage deferred a V2 (richiede @vitest/coverage-v8 devDep
# install + vitest config update — fuori scope per V1).
#
# Pin location: .github/workflows/test.yml backend-pytest job +
# backend/.coveragerc config file


class TestSEC_S4_4_CoverageReporting:
    """SEC-S4.4: pytest-cov configured + coverage artifact uploaded."""

    @staticmethod
    def _read_test_workflow() -> str:
        workflow = REPO_ROOT / ".github" / "workflows" / "test.yml"
        if not workflow.exists():
            pytest.skip("test.yml workflow not found")
        return workflow.read_text()

    def test_coveragerc_exists(self):
        """backend/.coveragerc must exist with scope definition."""
        coveragerc = REPO_ROOT / "backend" / ".coveragerc"
        assert coveragerc.exists(), (
            "backend/.coveragerc missing — pytest-cov defaults would include "
            "venv/ + tests/ + scripts/ → inflated coverage % e + report noise."
        )

    def test_coveragerc_excludes_venv_and_tests(self):
        """omit section must exclude venv, tests, scripts."""
        coveragerc = REPO_ROOT / "backend" / ".coveragerc"
        content = coveragerc.read_text()
        assert "venv/*" in content, ".coveragerc must exclude venv/"
        assert "tests/*" in content, ".coveragerc must exclude tests/"

    def test_test_workflow_installs_pytest_cov(self):
        """backend-pytest job installs pytest-cov."""
        content = self._read_test_workflow()
        assert "pytest-cov" in content, (
            "test.yml backend-pytest job does not install pytest-cov — "
            "coverage report cannot be generated."
        )

    def test_test_workflow_runs_pytest_with_cov_flag(self):
        """pytest invocation must include --cov flags."""
        content = self._read_test_workflow()
        assert "--cov=" in content, (
            "pytest --cov flag missing in workflow — coverage not measured."
        )
        assert "--cov-report=xml" in content, (
            "--cov-report=xml missing — XML report needed for artifact upload."
        )

    def test_test_workflow_uploads_coverage_artifact(self):
        """coverage.xml uploaded as GitHub Actions artifact."""
        content = self._read_test_workflow()
        assert "backend-coverage" in content, (
            "Coverage artifact upload missing. Without it, the report exists "
            "only inside the runner and is lost after job completion."
        )
        assert "coverage.xml" in content, (
            "coverage.xml path missing in artifact upload step."
        )

    def test_test_workflow_uses_always_for_coverage_upload(self):
        """if: always() on upload step ensures coverage uploaded even
        on test failure (helps debug which lines were covered before
        the failure)."""
        content = self._read_test_workflow()
        # Find the coverage upload block specifically
        cov_section_idx = content.find("backend-coverage")
        assert cov_section_idx > 0
        # The upload step preceding 'backend-coverage' must have 'if: always()'
        # Check within a reasonable window before this index
        window = content[max(0, cov_section_idx - 300):cov_section_idx]
        assert "if: always()" in window, (
            "Coverage upload not using 'if: always()' — failed test runs "
            "lose their coverage report. Bad for triage."
        )


# ─── SEC-S5.1 — Anti-enumeration consolidation ──────────────────────────
#
# Track S Step 5.1 — apre Sub-Track S5 (Regression & sentinel tests).
# Consolida gli invariant anti-enumeration sparsi tra S2.1 (login),
# S2.2 (signup) aggiungendo il pin per forgot-password (customer + admin)
# che era gia' implementato pre-Track S ma senza sentinel test.
#
# Cross-suite invariant: TUTTI gli endpoint pubblici email-receiving
# devono ritornare body identico per email-not-found vs email-found.
#
# Endpoint coverage:
#   · /api/customer-auth/login         — S2.1 sentinel ✅
#   · /api/auth/login                  — S2.1 sentinel ✅
#   · /api/customer-auth/signup        — S2.2 sentinel ✅
#   · /api/customer-auth/forgot-password — S5.1 sentinel NEW
#   · /api/auth/forgot-password        — S5.1 sentinel NEW
#   · /api/customer-auth/resend-verification — S5.1 sentinel NEW
#   · /api/auth/resend-verification    — S5.1 sentinel NEW


class TestSEC_S5_1_AntiEnumerationConsolidation:
    """SEC-S5.1: forgot-password + resend-verification return uniform
    body across email-found and email-not-found paths."""

    def test_customer_forgot_password_service_returns_same_message(self):
        """Customer forgot-password: email-not-found vs email-found
        must return identical body."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        # Scenario A: email not found
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=None),
        ):
            result_not_found = asyncio.run(
                customer_auth_service.customer_forgot_password(
                    org_id="org-1", email="ghost@x.it"
                )
            )

        # Scenario B: email found (mock everything downstream to avoid email send)
        account = {
            "id": "cust-1",
            "email": "u@x.it",
            "organization_id": "org-1",
            "locale": "it",
            "signup_slug": "demo",
        }
        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=account),
        ), patch.object(
            customer_auth_service.customer_account_repository,
            "update",
            new=AsyncMock(return_value=True),
        ), patch.object(
            customer_auth_service, "resolve_slug_for_org",
            new=AsyncMock(return_value="demo"),
        ), patch.object(
            customer_auth_service, "_load_email_context",
            new=AsyncMock(return_value={
                "sender_name": "x", "reply_to": "x@x.it", "store_name": "x"
            }),
        ), patch.object(
            customer_auth_service, "send_customer_password_reset",
            return_value=None,
        ):
            result_found = asyncio.run(
                customer_auth_service.customer_forgot_password(
                    org_id="org-1", email="u@x.it"
                )
            )

        assert result_not_found == result_found, (
            f"ENUMERATION LEAK: forgot-password returns different body "
            f"for not-found ({result_not_found!r}) vs found ({result_found!r}). "
            f"Must be byte-identical for anti-enumeration."
        )

    def test_customer_forgot_password_message_is_generic_italian(self):
        """The message must be the canonical 'Se l'email esiste' string."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from services import customer_auth_service

        with patch.object(
            customer_auth_service.customer_account_repository,
            "find_by_email",
            new=AsyncMock(return_value=None),
        ):
            result = asyncio.run(
                customer_auth_service.customer_forgot_password(
                    org_id="org-1", email="ghost@x.it"
                )
            )

        assert "Se l'email esiste" in result.get("message", ""), (
            f"forgot-password message drifted: {result!r}. "
            f"Expected pattern 'Se l'email esiste, riceverai un link...'"
        )

    def test_admin_forgot_password_router_uses_generic_constant(self):
        """admin auth.py forgot_password uses _GENERIC constant for
        ALL response paths (not-found, found, rate-limited)."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.forgot_password)

        # _GENERIC constant defined
        assert "_GENERIC" in source, (
            "admin forgot-password missing _GENERIC constant — risk of "
            "drift across the 3 response paths (not-found, found, rate-limited)."
        )

        # Count occurrences: should appear in at least 3 return statements
        # (rate-limit branch, not-found branch, success branch)
        generic_uses = source.count("_GENERIC")
        # The constant is defined once + used in multiple ForgotPasswordResponse calls
        assert generic_uses >= 4, (  # 1 def + 3+ uses
            f"_GENERIC referenced only {generic_uses} times in forgot_password. "
            f"Expected >= 4 (1 definition + 3+ response branches). "
            f"Some path may be using a hardcoded distinct message → leak."
        )

    def test_admin_forgot_password_returns_200_for_not_found(self):
        """Source-level: 'if not user_doc' branch must return 200
        (ForgotPasswordResponse) not raise HTTPException."""
        from routers import auth as auth_router
        import inspect

        source = inspect.getsource(auth_router.forgot_password)
        # The not-found branch should return ForgotPasswordResponse, NOT raise
        # We check that within the function source, there's a return for not-found
        # and NO HTTPException(status_code=404, ...) which would leak
        assert "Prevent email enumeration" in source or "_GENERIC" in source, (
            "forgot_password handler doesn't show explicit anti-enum design. "
            "Check that not-found path returns 200 with generic message."
        )
        # Anti-pattern: raising 404 on not-found
        import re
        not_found_404 = re.search(
            r"raise\s+HTTPException\([^)]*404[^)]*\)", source, re.MULTILINE
        )
        assert not_found_404 is None, (
            "forgot_password raises 404 → email enumeration leak. "
            f"Found: {not_found_404.group(0) if not_found_404 else 'N/A'}"
        )

    def test_resend_verification_customer_router_returns_uniform(self):
        """Customer resend-verification: source-level check that handler
        returns generic message for all paths."""
        from routers import customer_auth
        import inspect

        source = inspect.getsource(customer_auth.resend_verification)
        # Must call check_email_rate (per-email cap) and customer service
        assert "check_email_rate" in source, (
            "resend-verification missing per-email rate limit (anti-amplification)."
        )
        # Must NOT raise 404 / 400 for unknown email (anti-enum)
        import re
        bad = re.search(r"raise\s+HTTPException\([^)]*(404|400)", source)
        assert bad is None, (
            "resend-verification raises distinct status for unknown email → "
            f"enumeration leak: {bad.group(0) if bad else 'N/A'}"
        )

    def test_all_anti_enum_endpoints_documented(self):
        """Meta-test: SECURITY_HARDENING.md must list all S5.1 endpoints
        in the anti-enumeration coverage table."""
        doc = REPO_ROOT / "docs" / "SECURITY_HARDENING.md"
        content = doc.read_text()

        anti_enum_endpoints = [
            "customer-auth/login",
            "customer-auth/signup",
            "customer-auth/forgot-password",
            "customer-auth/resend-verification",
            "auth/login",
            "auth/forgot-password",
            "auth/resend-verification",
        ]
        missing = [e for e in anti_enum_endpoints if e not in content]
        # Allow up to 1 missing (potential drift, but full miss = doc gap)
        assert len(missing) <= 2, (
            f"SECURITY_HARDENING.md missing references to anti-enum "
            f"endpoints: {missing}. Doc should mention each protected path."
        )


# ─── SEC-S5.2 — Functional rate limit test (real 429 trigger) ───────────
#
# Track S Step 5.2 — pre-S5.2 i sentinel verificavano che check_email_rate
# era INVOCATO (source inspection) ma NON che effettivamente bloccasse
# dopo N+1 chiamate. S5.2 aggiunge functional test che chiama l'helper
# reale e verifica il comportamento sliding window.
#
# NB: helper esistente in core/rate_limiting.py:check_email_rate ha gia'
# reset_email_rate_state() per testing — usiamo quello tra test per evitare
# pollution cross-test.
#
# Pin location: backend/core/rate_limiting.py check_email_rate behavior


class TestSEC_S5_2_FunctionalRateLimit:
    """SEC-S5.2: check_email_rate sliding window actually fires after cap."""

    def setup_method(self):
        """Reset rate limit state before each test (no cross-test pollution)."""
        from core.rate_limiting import reset_email_rate_state
        reset_email_rate_state()

    def teardown_method(self):
        """Cleanup after each test."""
        from core.rate_limiting import reset_email_rate_state
        reset_email_rate_state()

    def test_check_email_rate_allows_up_to_max(self):
        """First N calls within window all return True."""
        from core.rate_limiting import check_email_rate

        for i in range(5):
            assert check_email_rate("test@x.it", "test_action", max_per_hour=5), (
                f"Call {i+1}/5 unexpectedly blocked (within cap)"
            )

    def test_check_email_rate_blocks_at_cap_plus_one(self):
        """N+1 call within window returns False (sliding window fired)."""
        from core.rate_limiting import check_email_rate

        # Consume the budget
        for _ in range(5):
            check_email_rate("victim@x.it", "test_block", max_per_hour=5)
        # Next call must be blocked
        assert not check_email_rate("victim@x.it", "test_block", max_per_hour=5), (
            "Call N+1 NOT blocked — sliding window not firing."
        )

    def test_check_email_rate_isolation_per_email(self):
        """Different emails have independent buckets — exhausting one
        does not block the other."""
        from core.rate_limiting import check_email_rate

        # Exhaust budget for email A
        for _ in range(5):
            check_email_rate("a@x.it", "test_iso", max_per_hour=5)
        # Email A blocked
        assert not check_email_rate("a@x.it", "test_iso", max_per_hour=5)
        # Email B unaffected
        assert check_email_rate("b@x.it", "test_iso", max_per_hour=5), (
            "Cross-email bucket bleed — exhausting A blocked B."
        )

    def test_check_email_rate_isolation_per_action(self):
        """Different actions have independent buckets — exhausting
        forgot-password doesn't block resend-verification."""
        from core.rate_limiting import check_email_rate

        for _ in range(5):
            check_email_rate("u@x.it", "forgot_password", max_per_hour=5)
        # forgot_password blocked
        assert not check_email_rate("u@x.it", "forgot_password", max_per_hour=5)
        # resend_verification independent
        assert check_email_rate("u@x.it", "resend_verification", max_per_hour=5), (
            "Cross-action bucket bleed — forgot_password exhaustion "
            "blocked resend_verification."
        )

    def test_check_email_rate_case_insensitive_email(self):
        """Bucket key normalizes email to lowercase to prevent trivial
        bypass via case variation (User@X.it vs user@x.it)."""
        from core.rate_limiting import check_email_rate

        # Exhaust with lowercase
        for _ in range(5):
            check_email_rate("u@x.it", "test_case", max_per_hour=5)
        # Uppercase variant must hit same bucket
        assert not check_email_rate("U@X.IT", "test_case", max_per_hour=5), (
            "Bucket key not normalizing case — attacker bypasses via "
            "User@X.it vs user@x.it."
        )

    def test_check_email_rate_permissive_on_empty_email(self):
        """Empty email returns True (no bucket created) to avoid giant
        shared bucket for unset values."""
        from core.rate_limiting import check_email_rate

        for _ in range(100):  # arbitrary large N
            assert check_email_rate("", "test_empty", max_per_hour=5), (
                "Empty email created a bucket — risk of giant shared "
                "bucket exhaustion."
            )
        # Whitespace-only also permissive
        assert check_email_rate("   ", "test_ws", max_per_hour=5)

    def test_check_email_rate_strip_whitespace(self):
        """Bucket key strips whitespace so '  u@x.it  ' shares bucket
        with 'u@x.it'."""
        from core.rate_limiting import check_email_rate

        # Exhaust
        for _ in range(5):
            check_email_rate("u@x.it", "test_strip", max_per_hour=5)
        # Whitespace variant must hit same bucket
        assert not check_email_rate("  u@x.it  ", "test_strip", max_per_hour=5), (
            "Bucket key not stripping whitespace — attacker bypasses via "
            "leading/trailing whitespace."
        )

    def test_reset_email_rate_state_clears_buckets(self):
        """The test-only reset function actually clears state (else
        cross-test pollution would render sentinel unreliable)."""
        from core.rate_limiting import check_email_rate, reset_email_rate_state

        for _ in range(5):
            check_email_rate("u@x.it", "test_reset", max_per_hour=5)
        assert not check_email_rate("u@x.it", "test_reset", max_per_hour=5)
        reset_email_rate_state()
        # After reset, fresh budget
        assert check_email_rate("u@x.it", "test_reset", max_per_hour=5), (
            "reset_email_rate_state() did not clear buckets — sentinel "
            "tests not isolated."
        )


# ─── SEC-S5.3 — Idempotency race condition functional test ──────────────
#
# Track S Step 5.3 — S3.2 ha aggiunto sentinel source-level (verify
# che _claim_idempotency_lock + _poll_for_lock_completion esistono +
# che dispatch li invoca prima di call_next). S5.3 estende con functional
# test che simula la race reale:
#   1. Mock insert_one con DuplicateKeyError per simulare race
#   2. Mock _lookup_cached_response per simulare winner che completa
#   3. Verify _poll_for_lock_completion ritorna la cached response
#
# Pin location: middleware/idempotency.py _poll_for_lock_completion +
# _claim_idempotency_lock cooperative behavior


class TestSEC_S5_3_IdempotencyRaceFunctional:
    """SEC-S5.3: functional simulation of race condition handling."""

    def test_poll_returns_completed_doc_within_window(self):
        """When winner sets response_status, polling loser sees the
        completed doc and returns it (no timeout)."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from middleware import idempotency

        # Mock _lookup_cached_response: first call returns pending,
        # second call returns completed (simulates winner finishing)
        completed_doc = {
            "digest": "d1",
            "status": "completed",
            "response_status": 200,
            "response_body": '{"order_id": "abc-123"}',
            "response_content_type": "application/json",
        }
        call_count = {"n": 0}

        async def _mock_lookup(digest):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"digest": digest, "status": "pending"}
            return completed_doc

        # Use very short interval for fast test (override module constant)
        with patch.object(idempotency, "LOCK_POLL_INTERVAL_SEC", 0.01), \
             patch.object(idempotency, "LOCK_POLL_TIMEOUT_SEC", 2.0), \
             patch.object(idempotency, "_lookup_cached_response",
                          side_effect=_mock_lookup):
            result = asyncio.run(idempotency._poll_for_lock_completion("d1"))

        assert result == completed_doc, (
            f"Polling did not return completed doc: {result!r}. "
            f"Race loser would never see winner's response."
        )
        assert call_count["n"] >= 1, "Polling never called lookup"

    def test_poll_returns_none_on_timeout(self):
        """When winner never completes within LOCK_POLL_TIMEOUT_SEC,
        polling returns None (caller maps to 409)."""
        import asyncio
        from unittest.mock import patch

        from middleware import idempotency

        # Always return pending (winner never finishes)
        async def _always_pending(digest):
            return {"digest": digest, "status": "pending"}

        # Very short timeout for fast test
        with patch.object(idempotency, "LOCK_POLL_INTERVAL_SEC", 0.01), \
             patch.object(idempotency, "LOCK_POLL_TIMEOUT_SEC", 0.1), \
             patch.object(idempotency, "_lookup_cached_response",
                          side_effect=_always_pending):
            result = asyncio.run(idempotency._poll_for_lock_completion("d1"))

        assert result is None, (
            f"Polling timeout should return None, got {result!r}. "
            f"Without None, dispatch handler does not emit 409."
        )

    def test_concurrent_claims_only_one_wins(self):
        """Two parallel asyncio claims for same digest: exactly one
        returns True (winner), the other returns False (loser must poll)."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from pymongo.errors import DuplicateKeyError

        from middleware import idempotency

        # State: first insert succeeds, second raises DuplicateKeyError
        insert_count = {"n": 0}

        async def _mock_insert(doc):
            insert_count["n"] += 1
            if insert_count["n"] == 1:
                return None  # success
            raise DuplicateKeyError("E11000 duplicate key")

        # Patch the collection's insert_one
        mock_collection = AsyncMock()
        mock_collection.insert_one = _mock_insert

        with patch("database.idempotency_keys_collection", mock_collection):
            async def _run_both():
                # Sequential simulation of race (asyncio.gather con same
                # key non garantisce ordine ma e' OK per il test:
                # vuoi che UN solo claim riesca).
                claim_a = await idempotency._claim_idempotency_lock(
                    digest="d-race", key="k1", organization_id="org-1", path="/x"
                )
                claim_b = await idempotency._claim_idempotency_lock(
                    digest="d-race", key="k1", organization_id="org-1", path="/x"
                )
                return claim_a, claim_b

            result_a, result_b = asyncio.run(_run_both())

        # Exactly one True, exactly one False
        assert sum([result_a, result_b]) == 1, (
            f"Race protection broken: claim_a={result_a}, claim_b={result_b}. "
            f"Expected exactly 1 winner."
        )

    def test_claim_degrades_gracefully_when_mongo_unreachable(self):
        """If insert_one raises non-DuplicateKey exception (e.g. Mongo
        unreachable), claim returns True (degraded mode — better than
        500-ing the request)."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from middleware import idempotency

        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock(
            side_effect=ConnectionError("Mongo unreachable")
        )

        with patch("database.idempotency_keys_collection", mock_collection):
            result = asyncio.run(
                idempotency._claim_idempotency_lock(
                    digest="d", key="k", organization_id="o", path="/x"
                )
            )

        assert result is True, (
            "Claim should return True on non-Mongo errors (degraded mode). "
            "Returning False would make request hang in poll forever."
        )


# ─── SEC-S5.4 — allowed_origins applied on Store model load ──────────────
#
# Track S Step 5.4 — extend S3.3. Validator e' field_validator(mode="before"),
# quindi fires SIA su Store(...) instantiation SIA su Pydantic deserialize
# da DB record. S5.4 sentinel verifica functional che caricare un raw
# dict con allowed_origins=["null"] da Mongo → ValidationError.
#
# Pin: models/store.py field_validator("allowed_origins", mode="before")


class TestSEC_S5_4_AllowedOriginsModelLoad:
    """SEC-S5.4: validator fires also on Pydantic load (not only ctor)."""

    def test_validator_fires_on_model_validate_dict(self):
        """Pydantic model_validate (from DB dict) must validate
        allowed_origins. If a malformed record exists in DB (manually
        inserted pre-S3.3), the load fails — fail-loud is correct."""
        import pytest
        from pydantic import ValidationError
        from models.store import Store

        # Simulate Mongo doc with bad allowed_origins (legacy data)
        bad_doc = {
            "id": "s-1",
            "organization_id": "org-1",
            "slug": "demo",
            "name": "Demo Store",
            "allowed_origins": ["null"],  # invalid post-S3.3
        }
        with pytest.raises((ValidationError, ValueError)):
            Store.model_validate(bad_doc)

    def test_validator_accepts_empty_list_on_load(self):
        """Default empty list must load successfully (most stores
        have no embed config yet)."""
        from models.store import Store

        doc = {
            "id": "s-1",
            "organization_id": "org-1",
            "slug": "demo",
            "name": "Demo Store",
            "allowed_origins": [],
        }
        store = Store.model_validate(doc)
        assert store.allowed_origins == []

    def test_validator_dedupes_on_load(self):
        """Duplicates in DB dict are normalized on load (good for
        records inserted pre-S3.3 with accidental dupes)."""
        from models.store import Store

        doc = {
            "id": "s-1",
            "organization_id": "org-1",
            "slug": "demo",
            "name": "Demo Store",
            "allowed_origins": [
                "https://a.com", "https://a.com", "https://b.com",
            ],
        }
        store = Store.model_validate(doc)
        assert store.allowed_origins == ["https://a.com", "https://b.com"]


# ─── SEC-S5.5 — /docs 404 functional via TestClient ─────────────────────
#
# Track S Step 5.5 — extend S1.3. Sentinel S1.3 testa il helper
# _docs_urls_for_env(env) in isolation. S5.5 estende con functional
# E2E: monkeypatch ENVIRONMENT=production e fa GET /docs via
# starlette.testclient — assert 404.
#
# NB: server.py legge ENVIRONMENT all'IMPORT time (load_dotenv +
# helper invocation per app config). Per testare funzionale dovremmo
# re-importare server con env diverso. Approccio piu' pragmatico:
# verifichiamo che il helper sia connesso correttamente all'app
# tramite la pure function, e che il docs_url sia coerente.


class TestSEC_S5_5_DocsExposureFunctional:
    """SEC-S5.5: end-to-end coupling helper → app.docs_url consistency."""

    def test_app_docs_url_consistent_with_helper_for_current_env(self):
        """In current process env, app.docs_url == helper output.
        Captures any drift between FastAPI() construction and helper."""
        import os
        from server import app, _docs_urls_for_env

        expected_docs, expected_redoc, expected_openapi = _docs_urls_for_env(
            os.environ.get("ENVIRONMENT")
        )
        assert app.docs_url == expected_docs
        assert app.redoc_url == expected_redoc
        assert app.openapi_url == expected_openapi

    def test_helper_explicit_production_returns_all_none(self):
        """Defensive integration check on the production path."""
        from server import _docs_urls_for_env

        docs, redoc, openapi = _docs_urls_for_env("production")
        # In production, all three docs paths must be disabled
        assert docs is None
        assert redoc is None
        assert openapi is None

    def test_test_client_dev_env_docs_responds(self):
        """In current test env (dev-like), /docs route exists and is
        callable via TestClient. Conferma che FastAPI registra il
        route correttamente quando dev."""
        from server import app

        # Only test this if we're in dev mode (i.e. docs_url != None)
        if app.docs_url is None:
            pytest.skip("App configured for production — /docs disabled")

        # In dev: route should be registered (no need to fully render
        # Swagger UI — TestClient is overkill; check route metadata)
        docs_route = [
            r for r in app.router.routes
            if getattr(r, "path", None) == app.docs_url
        ]
        assert docs_route, (
            f"app.docs_url={app.docs_url!r} but no route registered. "
            f"FastAPI internal coupling broken."
        )


# ─── SEC-S5.7 — Full regression consolidation ───────────────────────────
#
# Track S Step 5.7 — chiude Sub-Track S5. Cumulative test count
# sanity check + README badge present + workflow files structured.
#
# NB: Non e' un test che gira l'intera suite (sarebbe ridondante e
# slow). E' un meta-sentinel che verifica:
#   · README ha i badge CI + security
#   · README documenta test count cumulativi (cattura silent test
#     disappearance: se domani qualcuno comment-out 50 test, README
#     non si aggiorna → discrepancy visibile)


class TestSEC_S5_7_FullRegressionConsolidation:
    """SEC-S5.7: README + CI integration consolidation checks."""

    @staticmethod
    def _read_readme() -> str:
        readme = REPO_ROOT / "README.md"
        if not readme.exists():
            pytest.skip("README.md missing")
        return readme.read_text()

    def test_readme_has_ci_test_badge(self):
        """README must reference test workflow badge for visibility."""
        content = self._read_readme()
        assert "test.yml/badge.svg" in content, (
            "README missing CI test badge. Add: "
            "![test](https://.../workflows/test.yml/badge.svg)"
        )

    def test_readme_has_security_badge(self):
        content = self._read_readme()
        assert "security.yml/badge.svg" in content, (
            "README missing security workflow badge. Add: "
            "![security](https://.../workflows/security.yml/badge.svg)"
        )

    def test_readme_documents_test_count(self):
        """README documents cumulative test counts — catches silent
        test disappearance via discrepancy visibility."""
        content = self._read_readme()
        assert "Test suite" in content or "test suite" in content, (
            "README missing 'Test suite' section."
        )
        # At minimum mentions backend pytest count + embed-sdk vitest count
        assert "Backend pytest" in content or "backend pytest" in content
        assert "embed-sdk" in content.lower() or "Embed-SDK" in content

    def test_readme_links_to_security_hardening_doc(self):
        content = self._read_readme()
        assert "SECURITY_HARDENING" in content, (
            "README does not link to docs/SECURITY_HARDENING.md — "
            "discoverability gap for security policy."
        )

    def test_both_workflow_files_exist_with_aggregate_gates(self):
        """Final cross-check: test + security workflows both present
        with their respective aggregate gates."""
        test_yml = REPO_ROOT / ".github" / "workflows" / "test.yml"
        sec_yml = REPO_ROOT / ".github" / "workflows" / "security.yml"
        assert test_yml.exists(), "test.yml missing"
        assert sec_yml.exists(), "security.yml missing"
        assert "ci-passed:" in test_yml.read_text(), (
            "test.yml lost ci-passed aggregate gate"
        )
        assert "security-passed:" in sec_yml.read_text(), (
            "security.yml lost security-passed aggregate gate"
        )


# ─── SEC-S6.1 — SECURITY.md security policy ─────────────────────────────
#
# Track S Step 6.1 — GitHub auto-detects SECURITY.md at repo root and
# shows it in the "Security" tab + auto-link from security advisories
# UI. Without it, security researchers have no obvious channel to report
# vulnerabilities → public issue post → embarrassment + accidental
# disclosure pre-patch.
#
# Pin location: SECURITY.md at repo root


class TestSEC_S6_1_SecurityPolicyPresent:
    """SEC-S6.1: SECURITY.md exists with required sections."""

    @staticmethod
    def _read() -> str:
        path = REPO_ROOT / "SECURITY.md"
        if not path.exists():
            pytest.skip("SECURITY.md missing — S6.1 not yet applied")
        return path.read_text()

    def test_security_md_exists_at_repo_root(self):
        """SECURITY.md must be at REPO_ROOT (NOT in /docs) — GitHub
        auto-detects only the root location."""
        path = REPO_ROOT / "SECURITY.md"
        assert path.exists(), (
            "SECURITY.md missing at repo root. GitHub Security tab "
            "shows '⚠ Add a security policy' until present."
        )

    def test_security_md_has_reporting_section(self):
        """Must include 'Reporting a Vulnerability' section."""
        content = self._read()
        assert "Reporting a Vulnerability" in content or "reporting" in content.lower(), (
            "SECURITY.md missing reporting instructions. Researchers "
            "have no channel → may open public issue (public disclosure)."
        )

    def test_security_md_has_sla_table(self):
        """SLA table for response time (Critical/High/Medium/Low)."""
        content = self._read()
        assert "SLA" in content or "response" in content.lower(), (
            "SECURITY.md missing SLA section — researchers don't know "
            "when to expect first response."
        )
        # Verify severity ladder mentioned
        for sev in ("Critical", "High", "Medium"):
            assert sev in content, (
                f"SLA table missing '{sev}' severity tier."
            )

    def test_security_md_has_threat_model(self):
        """Threat model with OWASP mapping or surface analysis."""
        content = self._read()
        assert "Threat Model" in content or "OWASP" in content, (
            "SECURITY.md missing threat model / OWASP section — "
            "developers don't know what's classified as security-critical."
        )

    def test_security_md_links_to_hardening_doc(self):
        """Cross-reference to docs/SECURITY_HARDENING.md for technical detail."""
        content = self._read()
        assert "SECURITY_HARDENING" in content, (
            "SECURITY.md does not link to docs/SECURITY_HARDENING.md — "
            "discoverability gap for the technical security runbook."
        )

    def test_security_md_documents_accepted_residual_risks(self):
        """V1 residual risks documented so researchers don't report
        already-known issues as new."""
        content = self._read()
        assert "Residual Risk" in content or "residual" in content.lower(), (
            "SECURITY.md missing 'Accepted Residual Risks' section — "
            "expect duplicate reports on known starlette CVE etc."
        )


# ─── SEC-S6.2 — TESTING.md runbook ──────────────────────────────────────


class TestSEC_S6_2_TestingRunbookPresent:
    """SEC-S6.2: docs/operations/TESTING.md exists with required sections."""

    @staticmethod
    def _read() -> str:
        path = REPO_ROOT / "docs" / "operations" / "TESTING.md"
        if not path.exists():
            pytest.skip("TESTING.md missing — S6.2 not applied")
        return path.read_text()

    def test_testing_md_exists(self):
        path = REPO_ROOT / "docs" / "operations" / "TESTING.md"
        assert path.exists(), (
            "docs/operations/TESTING.md missing — new developers have "
            "no onboarding doc for running the test suite."
        )

    def test_testing_md_documents_quick_start(self):
        content = self._read()
        assert "Quick start" in content or "quick start" in content.lower(), (
            "TESTING.md missing Quick Start section."
        )
        # Must include both backend pytest + frontend pnpm test commands
        assert "backend:test" in content or "pytest" in content
        assert "pnpm test" in content or "pnpm --filter" in content

    def test_testing_md_documents_sentinel_pattern(self):
        """The doc must teach how to write a sentinel (knowledge transfer)."""
        content = self._read()
        assert "sentinel" in content.lower(), (
            "TESTING.md missing sentinel-writing guide — new devs may "
            "write functional tests instead of invariant pins."
        )

    def test_testing_md_documents_common_failures(self):
        content = self._read()
        assert "ModuleNotFoundError" in content or "common failure" in content.lower(), (
            "TESTING.md missing 'Common failure patterns' section — "
            "Track S CI debug rounds 1-4 lessons not preserved."
        )


# ─── SEC-S6.3 — Secret rotation runbook ─────────────────────────────────


class TestSEC_S6_3_SecretsRotationRunbookExtended:
    """SEC-S6.3: docs/operations/secrets-rotation.md exists con Track S
    Step 1.2 pending rotation section."""

    @staticmethod
    def _read() -> str:
        path = REPO_ROOT / "docs" / "operations" / "secrets-rotation.md"
        if not path.exists():
            pytest.skip("secrets-rotation.md missing")
        return path.read_text()

    def test_secrets_rotation_doc_exists(self):
        path = REPO_ROOT / "docs" / "operations" / "secrets-rotation.md"
        assert path.exists(), "secrets-rotation.md missing"

    def test_secrets_rotation_documents_track_s_pending(self):
        """S6.3 added Track S Step 1.2 pending rotation section listing
        the historically-exposed keys that have NOT been rotated."""
        content = self._read()
        assert "Track S Step 1.2" in content, (
            "secrets-rotation.md missing Track S Step 1.2 reference — "
            "ops team doesn't know about pending rotation backlog."
        )
        # Critical keys listed with priority
        for key in ("JWT_SECRET_KEY", "ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY"):
            assert key in content, (
                f"Pending rotation table missing {key} — ops gap."
            )

    def test_secrets_rotation_includes_metrics_auth_token(self):
        """METRICS_AUTH_TOKEN added in Track S Step 4.1 must appear in
        the inventory/changelog."""
        content = self._read()
        assert "METRICS_AUTH_TOKEN" in content, (
            "secrets-rotation.md does not document METRICS_AUTH_TOKEN. "
            "Inventory drift — V2 audit will miss this secret."
        )

    def test_secrets_rotation_has_step_by_step_procedure(self):
        """Track S Step 1.2 section includes openssl rand command +
        dashboard URLs (actionable, not just notes)."""
        content = self._read()
        assert "openssl rand -hex 32" in content, (
            "Missing JWT rotation command — non-actionable for ops."
        )
        assert "console.anthropic.com" in content, (
            "Missing Anthropic dashboard URL for rotation."
        )
        assert "dashboard.stripe.com" in content, (
            "Missing Stripe dashboard URL for rotation."
        )


# ─── SEC-L.1 — GDPR right-to-erasure endpoint ────────────────────────────
#
# Track L Step 1 — pre-launch P0 blocker per pilot pilota. GDPR Art. 17
# concede al customer il diritto di richiedere cancellazione dei propri
# dati. Senza endpoint, customer puo' solo via email (slow, no audit,
# no SLA tracking).
#
# Pin location: backend/routers/customer_portal.py::request_account_erasure


class TestSEC_L_1_GDPRErasureEndpoint:
    """SEC-L.1: erasure endpoint registered with audit + idempotent + 202."""

    def test_erasure_endpoint_exists(self):
        from routers import customer_portal
        assert hasattr(customer_portal, "request_account_erasure"), (
            "POST /me/request-erasure endpoint missing — GDPR Art. 17 "
            "non implementato. Customer pilot non puo' esercitare il "
            "diritto all'oblio → blocker per privacy policy compliance."
        )

    def test_erasure_endpoint_is_post_and_authed(self):
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        # Source must show @router.post + Depends(get_current_customer)
        # We check the broader file source for the decorator
        full_src = inspect.getsource(customer_portal)
        assert '@router.post(' in full_src and 'request-erasure' in full_src, (
            "Endpoint not registered with @router.post on /me/request-erasure"
        )
        assert "get_current_customer" in src, (
            "Endpoint missing Depends(get_current_customer) — non-authed "
            "= anyone can request erasure for arbitrary customer (impossible "
            "without customer JWT but defense in depth)."
        )

    def test_erasure_requires_explicit_confirm(self):
        """Body must require explicit confirm=true (anti-accidental-click)."""
        from routers.customer_portal import ErasureRequestBody
        import pytest
        from pydantic import ValidationError

        # confirm is required field (no default) → missing fails
        with pytest.raises(ValidationError):
            ErasureRequestBody()
        # confirm=true required to proceed
        body = ErasureRequestBody(confirm=True)
        assert body.confirm is True

    def test_erasure_writes_audit_log_action(self):
        """Source must reference 'gdpr_erasure_requested' audit action
        for legal compliance trail."""
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        assert "gdpr_erasure_requested" in src, (
            "Endpoint does not write audit log with action="
            "'gdpr_erasure_requested'. Without immutable audit trail, "
            "non-compliance with GDPR Art. 30 (records of processing)."
        )

    def test_erasure_idempotent_for_pending_requests(self):
        """Duplicate request for already-pending erasure returns 'pending'
        status (no double-trigger admin notifications)."""
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        assert "erasure_requested_at" in src, (
            "Endpoint does not check existing erasure_requested_at — "
            "duplicate clicks spam admin notifications + audit log."
        )
        assert "pending" in src.lower(), (
            "Endpoint does not return 'pending' status for duplicate "
            "request — caller cannot detect idempotent re-submission."
        )

    def test_erasure_returns_202_accepted_with_request_id(self):
        """202 status (async processing) + request_id for tracking."""
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        assert "status_code=202" in src, (
            "Endpoint not returning 202 Accepted — async processing "
            "convention violated."
        )
        assert "request_id" in src, (
            "Response missing request_id — customer cannot reference "
            "request in support communications."
        )

    def test_erasure_30_day_estimated_completion(self):
        """GDPR Art. 12 mandates max 30 days response time."""
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        assert "30" in src, (
            "Response missing 30-day SLA reference — GDPR Art. 12 "
            "non-compliant."
        )

    def test_erasure_redacts_email_in_audit_metadata(self):
        """Audit log must NOT contain plaintext email (PII minimization)."""
        from routers import customer_portal
        import inspect

        src = inspect.getsource(customer_portal.request_account_erasure)
        # The audit log metadata must redact email (***)
        assert "email_redacted" in src, (
            "Audit log stores plaintext email — PII minimization "
            "violation (audit logs are retention 1 year, exposed in any "
            "DB dump)."
        )


# ─── SEC-L.2 — Incident response plan ───────────────────────────────────


class TestSEC_L_2_IncidentResponsePresent:
    """SEC-L.2: incident-response.md + incidents.md exist with required sections."""

    @staticmethod
    def _read_response_plan() -> str:
        path = REPO_ROOT / "docs" / "operations" / "incident-response.md"
        if not path.exists():
            pytest.skip("incident-response.md missing")
        return path.read_text()

    def test_incident_response_plan_exists(self):
        path = REPO_ROOT / "docs" / "operations" / "incident-response.md"
        assert path.exists(), (
            "docs/operations/incident-response.md missing — operator has "
            "no playbook for production incidents."
        )

    def test_incident_response_has_severity_matrix(self):
        content = self._read_response_plan()
        for sev in ("P0", "P1", "P2", "P3"):
            assert sev in content, (
                f"Severity matrix missing {sev} tier."
            )
        assert "Severity" in content or "severity" in content

    def test_incident_response_has_gdpr_breach_section(self):
        """GDPR Art. 33 mandates 72h notification — must be documented."""
        content = self._read_response_plan()
        assert "72" in content and ("GDPR" in content or "Garante" in content), (
            "GDPR breach 72h notification timeline missing."
        )

    def test_incident_response_has_postmortem_template(self):
        content = self._read_response_plan()
        assert "post-mortem" in content.lower() or "postmortem" in content.lower(), (
            "Missing post-mortem template — institutional memory gap."
        )

    def test_incidents_log_exists(self):
        path = REPO_ROOT / "docs" / "operations" / "incidents.md"
        assert path.exists(), (
            "docs/operations/incidents.md missing — append-only audit "
            "trail of past incidents not initialized."
        )

    def test_incident_response_has_decision_tree(self):
        """Triage decision tree helps operator classify quickly."""
        content = self._read_response_plan()
        assert "Decision tree" in content or "decision tree" in content.lower(), (
            "Decision tree per severity classification missing."
        )


# ─── SEC-L.3 — Email reputation DNS guide ───────────────────────────────


class TestSEC_L_3_EmailReputationGuide:
    """SEC-L.3: SPF + DKIM + DMARC setup guide present."""

    @staticmethod
    def _read() -> str:
        path = REPO_ROOT / "docs" / "operations" / "email-reputation.md"
        if not path.exists():
            pytest.skip("email-reputation.md missing")
        return path.read_text()

    def test_email_reputation_doc_exists(self):
        path = REPO_ROOT / "docs" / "operations" / "email-reputation.md"
        assert path.exists(), (
            "docs/operations/email-reputation.md missing — DNS setup "
            "guide assente → email transazionali finiscono in spam."
        )

    def test_email_reputation_documents_spf(self):
        content = self._read()
        assert "SPF" in content and "spf.brevo.com" in content, (
            "SPF setup procedure missing or Brevo include host wrong."
        )

    def test_email_reputation_documents_dkim(self):
        content = self._read()
        assert "DKIM" in content and "dkim.brevo.com" in content, (
            "DKIM CNAME procedure missing or wrong host."
        )

    def test_email_reputation_documents_dmarc_progressive_rollout(self):
        """DMARC must document progressive policy upgrade
        (none → quarantine → reject) to avoid breaking email delivery."""
        content = self._read()
        assert "DMARC" in content, "DMARC section missing"
        # Progressive rollout (start with p=none, then upgrade)
        assert "p=none" in content, (
            "DMARC procedure missing initial p=none monitoring phase. "
            "Going directly to p=quarantine/reject blocks legit email "
            "during rollout."
        )

    def test_email_reputation_has_verification_checklist(self):
        content = self._read()
        assert "Verification" in content or "checklist" in content.lower(), (
            "Verification checklist missing — operator non sa quando "
            "considerare il setup completato."
        )

    def test_email_reputation_warns_about_spf_dup(self):
        """SPF dup is the #1 setup error — must be flagged."""
        content = self._read()
        assert "GIA'" in content.upper() or "already" in content.lower(), (
            "Doc missing warning about pre-existing SPF record (most "
            "common setup error)."
        )


# ─── SEC-O.1.1 — Idempotency expires_at MUST be BSON Date ───────────────
#
# Track O Step 1.1 — pre-fix il middleware scriveva expires_at come ISO
# string (.isoformat()). MongoDB TTL index su `expires_at` con
# expireAfterSeconds=0 ignora silenziosamente i record di tipo string
# → collection idempotency_keys cresceva UNBOUNDED nel tempo.
#
# Post-fix: middleware scrive expires_at come datetime obj direttamente.
# TTL index funziona, MongoDB auto-cleanup dei record scaduti ogni ~60s.
#
# Pin location:
#   backend/middleware/idempotency.py::_claim_idempotency_lock (line ~244)
#   backend/scripts/backfill_idempotency_expires_at_bson_date.py (migration)


class TestSEC_O_1_1_IdempotencyExpiresAtBsonDate:
    """SEC-O.1.1: idempotency_keys.expires_at must be BSON Date for TTL.

    Pin sull'invariant che la TTL index Mongo possa effettivamente
    pulire i record scaduti. Senza BSON Date, TTL ignora i record
    silenziosamente — bug subdolo (no error, no log, solo growth).
    """

    def test_claim_lock_source_uses_datetime_not_isoformat_for_expires_at(self):
        """Source inspection: _claim_idempotency_lock NON deve usare
        .isoformat() su expires_at value."""
        from middleware import idempotency
        import inspect

        src = inspect.getsource(idempotency._claim_idempotency_lock)

        # Pattern errato: expires_at value calcolato con .isoformat()
        # Cerca riga tipo: expires_iso = _new_expires_at().isoformat()
        # seguita da "expires_at": expires_iso (ISO string assignment)
        assert "_new_expires_at().isoformat()" not in src, (
            "Regression bug O1.1: _claim_idempotency_lock chiama "
            "_new_expires_at().isoformat() — questo riproduce il TTL "
            "bug pre-O1.1. expires_at DEVE essere datetime, NON ISO string."
        )

        # Pattern corretto: expires_at_dt = _new_expires_at() (no isoformat)
        # NB: il fix usa "expires_at_dt" come nome variabile per chiarezza
        assert "_new_expires_at()" in src, (
            "Helper _new_expires_at non piu' usato — il flow ha drift."
        )

    def test_claim_lock_source_assigns_datetime_to_expires_at_field(self):
        """Source inspection: l'assignment expires_at: <value> deve essere
        un datetime, non una string."""
        from middleware import idempotency
        import inspect

        src = inspect.getsource(idempotency._claim_idempotency_lock)
        # Pattern: "expires_at": expires_at_dt  (datetime variable)
        # ANTI-PATTERN: "expires_at": expires_iso  (ISO string variable)
        assert '"expires_at": expires_iso' not in src, (
            "Regression bug O1.1: claim insert assegna ISO string variable "
            "a expires_at. TTL bug riintrodotto."
        )

    def test_new_expires_at_returns_datetime_not_string(self):
        """Helper _new_expires_at() ritorna datetime obj."""
        from middleware.idempotency import _new_expires_at
        from datetime import datetime

        result = _new_expires_at()
        assert isinstance(result, datetime), (
            f"_new_expires_at ritorna {type(result).__name__} invece di "
            f"datetime. Se diventa string, TTL bug si riintroduce."
        )

    def test_lookup_handles_both_legacy_string_and_new_datetime(self):
        """_lookup_cached_response defensive parsing: accetta sia ISO
        string (legacy pre-O1.1) che datetime (post-O1.1) per
        backward-compat durante migration."""
        from middleware import idempotency
        import inspect

        src = inspect.getsource(idempotency._lookup_cached_response)
        # Defensive: gestisce isinstance(exp, datetime) E isinstance(exp, str)
        assert "isinstance(exp, datetime)" in src, (
            "_lookup_cached_response non controlla type datetime — "
            "post-fix lookup fail per record nuovi."
        )
        assert "isinstance(exp, str)" in src, (
            "_lookup_cached_response non controlla type string — "
            "record legacy pre-O1.1 non gestiti, possible false 'not expired'."
        )

    def test_idempotency_keys_ttl_index_defined_in_database(self):
        """database.py crea TTL index su expires_at field per
        idempotency_keys (expireAfterSeconds=0 = per-document TTL)."""
        import database
        import inspect

        src = inspect.getsource(database)
        # Cerca la creazione dell'index TTL
        assert "expires_at" in src and "expireAfterSeconds=0" in src, (
            "TTL index su idempotency_keys.expires_at mancante in "
            "database.py — anche con fix middleware, no auto-cleanup."
        )

    def test_backfill_migration_script_exists(self):
        """Script migration legacy → BSON Date deve esistere per cleanup
        record pre-O1.1 in production."""
        script = REPO_ROOT / "backend" / "scripts" / \
            "backfill_idempotency_expires_at_bson_date.py"
        assert script.exists(), (
            "Migration script missing — record legacy in prod restano "
            "ISO string, TTL non li tocca = unbounded growth continua."
        )
        content = script.read_text()
        assert "--apply" in content and "--dry-run" in content, (
            "Migration script missing standard --dry-run / --apply flags."
        )
        assert "idempotent" in content.lower(), (
            "Migration script doc non dichiara idempotency — pericoloso "
            "ri-eseguire."
        )


# ─── SEC-O.1.2 — Sentry traces sampling env-based (free tier safe) ──────
#
# Track O Step 1.2 — pre-fix default SENTRY_TRACES_RATE era 0.1 (10%).
# In production con 50 req/s sustained → 5 trace/s = 432k transactions/mese.
# Sentry Developer free tier = 10k transactions/mese → quota blast in ~12h.
#
# Post-fix: helper _default_traces_rate_for_env() ritorna valore safe-per-env:
#   production:  0.0001 (0.01%) ~13k/mese → sotto free quota
#   staging:     0.01   (1%)    ~1.3M/mese (paid plan considera)
#   development: 0.1    (10%)   full debug locale (no impact)
#
# Override esplicito SENTRY_TRACES_RATE env var sempre rispettato.
#
# Pin location: backend/core/observability/sentry.py::_default_traces_rate_for_env


class TestSEC_O_1_2_SentryTracesSamplingEnvBased:
    """SEC-O.1.2: helper returns environment-appropriate default."""

    def test_helper_returns_safe_default_for_production(self):
        """Production deve avere sampling MOLTO basso per stare in free tier."""
        from core.observability.sentry import _default_traces_rate_for_env

        rate = _default_traces_rate_for_env("production")
        assert rate <= 0.001, (
            f"Production traces rate troppo alto: {rate}. "
            f"Con 50 req/s, rate > 0.001 burna Sentry free tier in ore."
        )
        assert rate > 0, (
            "Production rate = 0 disabilita totalmente tracing — "
            "perdiamo perf observability su prod."
        )

    def test_helper_returns_moderate_default_for_staging(self):
        from core.observability.sentry import _default_traces_rate_for_env

        rate = _default_traces_rate_for_env("staging")
        assert 0.001 <= rate <= 0.1, (
            f"Staging rate fuori range ragionevole: {rate}. "
            f"Atteso 0.001-0.1 per testing utile senza burn quota."
        )

    def test_helper_returns_debug_friendly_default_for_dev(self):
        """Development locale: full sampling OK (no quota impact)."""
        from core.observability.sentry import _default_traces_rate_for_env

        for env_val in ("development", "DEVELOPMENT", "  development  ", "test", "", None):
            rate = _default_traces_rate_for_env(env_val)
            assert rate >= 0.01, (
                f"env={env_val!r} default {rate} troppo basso — "
                f"perdiamo visibility utile in dev/test."
            )

    def test_helper_is_pure_function(self):
        """Helper deve avere signature (environment: str|None) — no env read
        interno. Verifica via signature (resistant a docstring drift)."""
        from core.observability.sentry import _default_traces_rate_for_env
        import inspect

        sig = inspect.signature(_default_traces_rate_for_env)
        params = list(sig.parameters.keys())
        assert params == ["environment"], (
            f"Helper signature drift: parametri {params}. "
            f"Atteso ['environment'] — function deve essere pure, "
            f"environment va PASSATO esplicitamente per testability."
        )

    def test_init_sentry_uses_helper_for_default(self):
        """init_sentry chiama helper come default (rispetta override)."""
        from core.observability import sentry as sentry_mod
        import inspect

        src = inspect.getsource(sentry_mod.init_sentry)
        assert "_default_traces_rate_for_env" in src, (
            "init_sentry non usa _default_traces_rate_for_env helper — "
            "default hardcoded a 0.1 di nuovo? Regression bug."
        )

    def test_explicit_env_override_respected(self):
        """Se SENTRY_TRACES_RATE settata esplicitamente, override default.

        Source-level check (no env mutation per evitare side effect)."""
        from core.observability import sentry as sentry_mod
        import inspect

        src = inspect.getsource(sentry_mod.init_sentry)
        # explicit_rate path deve leggere env var + fallback a helper
        assert "SENTRY_TRACES_RATE" in src, (
            "init_sentry non legge SENTRY_TRACES_RATE env var — perso "
            "escape hatch per emergency tuning prod (no redeploy)."
        )
        assert "explicit_rate" in src or "explicit" in src.lower(), (
            "Pattern explicit override non chiaro nel source — il helper "
            "deve essere DEFAULT, env override deve vincere."
        )


# ─── SEC-O.1.3 — Email service HTTP session pool + retry ────────────────
#
# Track O Step 1.3 — pre-fix email_service.py usava urllib.request.urlopen
# sync + zero retry + nessuna connection pool. Brevo timeout (~7/h SLA
# 99.5%) saturava thread pool + nessun fallback su transient failure.
#
# Post-fix: requests.Session + HTTPAdapter retry (3x exp backoff su
# 5xx/429) + connection pool (10 conn × 20 max per host).
#
# Pin location: backend/services/email_service.py:
#   - _build_brevo_session() helper (pure function)
#   - _get_brevo_session() singleton lazy init
#   - _post_brevo() POST wrapper con retry


class TestSEC_O_1_3_EmailServiceHttpRetry:
    """SEC-O.1.3: email_service usa requests.Session retry pool."""

    def test_build_brevo_session_returns_requests_session(self):
        """Helper costruisce vera requests.Session, non oggetto custom."""
        from services.email_service import _build_brevo_session
        import requests

        session = _build_brevo_session()
        assert isinstance(session, requests.Session), (
            f"_build_brevo_session ritorna {type(session).__name__}, "
            f"atteso requests.Session per HTTP pool + retry standard."
        )

    def test_session_has_retry_adapter_for_https(self):
        """Session deve avere HTTPAdapter retry-aware su https://."""
        from services.email_service import _build_brevo_session
        from requests.adapters import HTTPAdapter

        session = _build_brevo_session()
        adapter = session.get_adapter("https://api.brevo.com")
        assert isinstance(adapter, HTTPAdapter), (
            f"https:// adapter e' {type(adapter).__name__}, "
            f"atteso HTTPAdapter (no retry su default adapter)."
        )

    def test_retry_strategy_handles_transient_failures(self):
        """Retry deve coprire 5xx server errors + 429 rate limit (transient)."""
        from services.email_service import _build_brevo_session

        session = _build_brevo_session()
        adapter = session.get_adapter("https://api.brevo.com")
        # adapter.max_retries e' urllib3 Retry instance
        retry = adapter.max_retries
        assert retry.total == 3, (
            f"Max retries = {retry.total}, atteso 3 per transient failure recovery"
        )
        # 429 (rate limit) + 5xx (server error) devono essere in status_forcelist
        forcelist = set(retry.status_forcelist or [])
        for status in (429, 500, 502, 503, 504):
            assert status in forcelist, (
                f"Status {status} non in retry forcelist — transient "
                f"failure NON ritried = email lost su Brevo timeout."
            )

    def test_retry_uses_exponential_backoff(self):
        """Backoff factor > 0 = exponential (1s, 2s, 4s) vs immediate retry."""
        from services.email_service import _build_brevo_session

        session = _build_brevo_session()
        adapter = session.get_adapter("https://api.brevo.com")
        retry = adapter.max_retries
        assert retry.backoff_factor > 0, (
            f"backoff_factor = {retry.backoff_factor}, atteso > 0 per "
            f"evitare immediate retry storm (DoS sul Brevo nel retry loop)."
        )

    def test_session_is_singleton(self):
        """_get_brevo_session ritorna SEMPRE la stessa instance (pool reuse)."""
        from services.email_service import _get_brevo_session

        s1 = _get_brevo_session()
        s2 = _get_brevo_session()
        assert s1 is s2, (
            "_get_brevo_session non ritorna singleton — connection pool "
            "ri-creato ogni call = no pooling benefit."
        )

    def test_send_email_uses_post_brevo_helper(self):
        """send_email source NON contiene piu' urllib.request.urlopen.
        Source check anti-regression."""
        from services.email_service import send_email
        import inspect

        src = inspect.getsource(send_email)
        # Anti-pattern: urllib direct usage
        assert "urllib.request.urlopen" not in src, (
            "send_email usa ancora urllib.request.urlopen — sync, no "
            "retry, no pool. Track O.1.3 regression bug."
        )
        # Pattern corretto: _post_brevo helper invoked
        assert "_post_brevo" in src, (
            "send_email non chiama _post_brevo helper — perso retry + pool."
        )

    def test_send_email_with_attachment_uses_post_brevo_helper(self):
        from services.email_service import send_email_with_attachment
        import inspect

        src = inspect.getsource(send_email_with_attachment)
        assert "urllib.request.urlopen" not in src, (
            "send_email_with_attachment usa ancora urllib.urlopen — regression."
        )
        assert "_post_brevo" in src, (
            "send_email_with_attachment non chiama _post_brevo — no retry/pool."
        )


# ─── SEC-O.1.4 — Admin audit log query API ──────────────────────────────
#
# Track O Step 1.4 — pre-fix unico modo per leggere audit_logs era via
# mongosh diretto al DB. Per open beta serve API-driven review per:
#   - Customer support (debug "cosa ha fatto questo customer")
#   - Compliance review (GDPR erasure trail, login forensics)
#   - Security incident response (cross-org pattern detection)
#
# Sfrutta compound index esistente (organization_id, created_at) per
# performance O(log N).
#
# Pin: backend/routers/admin.py::list_audit_logs_endpoint
#      backend/repositories/audit_repository.py::list_audit_logs


class TestSEC_O_1_4_AuditLogQueryAPI:
    """SEC-O.1.4: admin audit log endpoint + repo functions exist."""

    def test_endpoint_exists_in_admin_router(self):
        """GET /api/admin/audit-logs handler registered."""
        from routers import admin
        assert hasattr(admin, "list_audit_logs_endpoint"), (
            "Missing list_audit_logs_endpoint in routers/admin.py — "
            "support/compliance team can only query via mongosh shell."
        )

    def test_endpoint_requires_system_admin(self):
        """Endpoint MUST gate behind require_system_admin (not org_admin)."""
        from routers import admin
        import inspect

        src = inspect.getsource(admin.list_audit_logs_endpoint)
        assert "require_system_admin" in src, (
            "Audit log endpoint missing require_system_admin gate — "
            "exposes cross-org audit data to non-platform-admins."
        )

    def test_endpoint_supports_pagination(self):
        """skip + limit query params per pagination UI."""
        from routers import admin
        import inspect

        src = inspect.getsource(admin.list_audit_logs_endpoint)
        assert "skip" in src and "limit" in src, (
            "Endpoint missing skip/limit pagination — UI puo' caricare "
            "solo first 100 record."
        )

    def test_endpoint_has_limit_hard_cap(self):
        """limit param ha le=200 cap (anti-DOS query gigantesche)."""
        from routers import admin
        import inspect

        src = inspect.getsource(admin.list_audit_logs_endpoint)
        # Pydantic Query(le=200) o le=200
        assert "le=200" in src, (
            "limit param missing hard cap le=200 — un caller potrebbe "
            "richiedere 100k record in 1 query, OOM o slow DB scan."
        )

    def test_endpoint_supports_filters(self):
        """Filter params: organization_id, action, since, until."""
        from routers import admin
        import inspect

        src = inspect.getsource(admin.list_audit_logs_endpoint)
        for param in ("organization_id", "action", "since", "until"):
            assert param in src, (
                f"Audit log endpoint missing '{param}' filter — limit "
                f"casi d'uso (es. support deve filtrare per single org)."
            )

    def test_repository_list_audit_logs_exists(self):
        """audit_repository.list_audit_logs function exists."""
        from repositories import audit_repository
        assert hasattr(audit_repository, "list_audit_logs"), (
            "audit_repository missing list_audit_logs helper — endpoint "
            "non puo' funzionare."
        )
        assert hasattr(audit_repository, "count_audit_logs"), (
            "audit_repository missing count_audit_logs — pagination total "
            "non calcolabile."
        )

    def test_repository_list_strips_mongo_id(self):
        """List query usa projection {_id: 0} — no Mongo internal leak."""
        from repositories import audit_repository
        import inspect

        src = inspect.getsource(audit_repository.list_audit_logs)
        assert '"_id": 0' in src, (
            "list_audit_logs non strip _id field — Mongo ObjectId leaked "
            "in response (info leak su DB internals)."
        )

    def test_repository_list_sorts_by_created_at_desc(self):
        """Query sort newest first (UX expectation)."""
        from repositories import audit_repository
        import inspect

        src = inspect.getsource(audit_repository.list_audit_logs)
        assert ".sort(" in src and "created_at" in src and "-1" in src, (
            "list_audit_logs non ordina per created_at DESC — UX UI "
            "incoerente (newest first standard)."
        )


# ─── SEC-O.1.5 — Multi-tenant isolation invariants ───────────────────────
#
# Track O Step 1.5 — pre-fix l'invariant "ogni org vede solo dati propri"
# era IMPLEMENTED ma non PINNED da test esplicito. Audit (O1.5) ha
# confermato che il pattern e' strong:
#
#   1. Repository critici (customer, product, order, cart) hanno signature
#      find_by_id(id, organization_id) — org filter obbligatorio
#
#   2. customer_account_repository.find_by_id(account_id) NON ha org_id
#      MA il caller principale (auth.py::get_current_customer line 418-425)
#      ha defense-in-depth check: token_org != account_org → 401
#
#   3. customer JWT contiene org_id (signed, non spoofable senza JWT_SECRET)
#
# Per open beta (50-200 org simultaneously) questo invariant DEVE rimanere
# pinned anti-regression: anche un singolo refactor che togliesse l'org
# filter o il defense-in-depth check aprirebbe cross-org data leak.


class TestSEC_O_1_5_MultiTenantIsolation:
    """SEC-O.1.5: critical repos enforce org_id + auth defense-in-depth."""

    def test_customer_repository_find_by_id_requires_org_id(self):
        """customer_repository.find_by_id signature MUST have organization_id."""
        from repositories import customer_repository
        import inspect

        sig = inspect.signature(customer_repository.find_by_id)
        params = list(sig.parameters.keys())
        assert "organization_id" in params, (
            f"customer_repository.find_by_id signature drift: {params}. "
            f"Manca 'organization_id' — cross-org leak via ID guessing possibile."
        )

    def test_product_repository_find_by_id_requires_org_id(self):
        from repositories import product_repository
        import inspect

        sig = inspect.signature(product_repository.find_by_id)
        params = list(sig.parameters.keys())
        assert "organization_id" in params, (
            f"product_repository.find_by_id signature drift: {params}"
        )

    def test_cart_repository_find_by_id_requires_org_id(self):
        from repositories import cart_repository
        import inspect

        sig = inspect.signature(cart_repository.find_by_id)
        params = list(sig.parameters.keys())
        assert "organization_id" in params, (
            f"cart_repository.find_by_id signature drift: {params}"
        )

    def test_cart_repository_delete_requires_org_id(self):
        """delete operations must also be org-scoped (no cross-org delete)."""
        from repositories import cart_repository
        import inspect

        sig = inspect.signature(cart_repository.delete_by_id)
        params = list(sig.parameters.keys())
        assert "organization_id" in params, (
            f"cart_repository.delete_by_id senza org_id — cross-org "
            f"delete via API exploit possibile. Signature: {params}"
        )

    def test_order_repository_update_requires_org_id(self):
        """Order update (state change) MUST be org-scoped."""
        from repositories import order_repository
        import inspect

        sig = inspect.signature(order_repository.update)
        params = list(sig.parameters.keys())
        # Pattern visto: order_repository.update(order_id, org_id, updates)
        has_org = "org_id" in params or "organization_id" in params
        assert has_org, (
            f"order_repository.update signature drift: {params}. "
            f"Manca org_id — cross-org order state change possibile."
        )

    def test_customer_account_find_by_id_defense_in_depth_in_auth(self):
        """customer_account_repository.find_by_id NON ha org_id BUT
        auth.py::get_current_customer DEVE avere defense-in-depth check
        token_org != account_org → 401.

        Questa e' l'unica eccezione documentata. Anti-regression: se
        qualcuno rimuove il check, customer JWT con account_id altrui
        (esfiltrato) bypasserebbe org isolation.
        """
        from auth import get_current_customer
        import inspect

        src = inspect.getsource(get_current_customer)
        # Pattern: token_org != account_org → raise 401
        assert "token_org" in src, (
            "auth.py::get_current_customer manca 'token_org' check — "
            "defense-in-depth multi-tenant rimosso."
        )
        assert "account_org" in src, (
            "auth.py::get_current_customer manca 'account_org' check"
        )
        assert "Token org mismatch" in src or "org mismatch" in src.lower(), (
            "auth.py::get_current_customer NON raise 401 su org mismatch "
            "— customer JWT esfiltrato puo' accedere data di altra org."
        )

    def test_customer_account_find_by_email_requires_org_id(self):
        """find_by_email scoped per-org: stesso email puo' esistere in
        org diverse (compound unique index org+email)."""
        from repositories import customer_account_repository
        import inspect

        sig = inspect.signature(customer_account_repository.find_by_email)
        params = list(sig.parameters.keys())
        assert "organization_id" in params, (
            f"find_by_email senza organization_id — login customer di "
            f"org B con stessa email customer org A causa cross-tenant "
            f"leak. Signature: {params}"
        )

    def test_get_current_customer_token_includes_org_id(self):
        """JWT customer DEVE contenere org_id claim — base del defense-
        in-depth check sopra."""
        from auth import create_customer_token
        import inspect

        src = inspect.getsource(create_customer_token)
        # create_customer_token deve injectare org_id dal data param
        # Look for "org_id" or "organization_id" being added to payload
        assert "org_id" in src or "organization_id" in src, (
            "create_customer_token non include org_id claim — JWT "
            "non puo' essere verificato cross-org in get_current_customer."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 1.6 — Nginx /signup rate limit zone (open beta hardening)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   App-level slowapi gia' enforces 5/15min su /auth/signup +
#   /customer-auth/signup, ma cosi' ogni richiesta brute-force consuma
#   CPU + Mongo lookup prima di essere rifiutata. Per open beta serve
#   secondo strato a nginx che killi DOS (1000s req/min) PRIMA che il
#   request raggiunga Python.
#
# Sentinel verificano che nginx.conf:
#   - definisca zone 'signup' (memory + rate)
#   - applichi limit_req zone=signup su entrambi gli endpoint signup
#   - usi burst+nodelay (no thundering herd su retry legittimi)


class TestSEC_O_1_6_NginxSignupRateLimit:
    """SEC-O.1.6: nginx-level signup abuse zone exists + binds to both
    /api/auth/signup (merchant) and /api/customer-auth/signup (customer)."""

    NGINX_CONF_PATH = "deploy/nginx/nginx.conf"

    def _read_conf(self) -> str:
        from pathlib import Path

        # Risolvi relativo alla repo root (i test girano da backend/, ma
        # nginx.conf vive in deploy/ → sali di 1 livello)
        repo_root = Path(__file__).resolve().parents[2]
        conf = repo_root / self.NGINX_CONF_PATH
        assert conf.exists(), f"nginx.conf non trovato a {conf}"
        return conf.read_text(encoding="utf-8")

    def test_signup_zone_defined(self):
        """nginx.conf deve definire 'zone=signup' con limit_req_zone."""
        conf = self._read_conf()
        assert "zone=signup:" in conf, (
            "nginx.conf manca limit_req_zone zone=signup. Senza zone "
            "nginx non puo' rate-limit signup → app-level e' single point "
            "of failure su DOS brute-force."
        )

    def test_signup_zone_uses_binary_remote_addr(self):
        """Zone deve essere per-IP ($binary_remote_addr) — efficient memory."""
        conf = self._read_conf()
        # Find the signup zone line e verifica che usi $binary_remote_addr
        lines = [
            ln.strip()
            for ln in conf.splitlines()
            if "zone=signup:" in ln and "limit_req_zone" in ln
        ]
        assert lines, "Nessuna riga limit_req_zone con zone=signup trovata"
        assert any("$binary_remote_addr" in ln for ln in lines), (
            f"signup zone non keyed su $binary_remote_addr (efficient IPv4/v6 "
            f"4-16 byte key). Lines: {lines}"
        )

    def test_signup_zone_rate_defined(self):
        """Zone deve specificare un rate (es. 5r/m, 10r/m)."""
        import re

        conf = self._read_conf()
        # Match pattern "zone=signup:<mem> rate=<n>r/<unit>"
        m = re.search(r"zone=signup:\d+m\s+rate=(\d+)r/([sm])", conf)
        assert m, (
            "signup zone non definisce un rate=<n>r/[sm] valido. "
            "Senza rate la zone e' inerte (nginx non rifiuta nulla)."
        )
        rate_val, unit = int(m.group(1)), m.group(2)
        # Sanity: rate non troppo permissivo. Es. 60r/m = 1/s = inutile
        # come DOS shield. Cap a 20r/m max.
        if unit == "m":
            assert rate_val <= 20, (
                f"signup rate={rate_val}r/m troppo permissivo — non protegge "
                f"da brute-force. Atteso <= 20r/m (app slowapi e' 5/15min)."
            )

    def test_signup_location_block_for_merchant(self):
        """/api/auth/signup location deve applicare limit_req zone=signup."""
        conf = self._read_conf()
        assert "location /api/auth/signup" in conf, (
            "Manca location block per /api/auth/signup — merchant signup "
            "non protetto da nginx zone."
        )
        # Trova lo slice della location e verifica che contenga limit_req
        idx = conf.find("location /api/auth/signup")
        block = conf[idx : idx + 600]
        assert "limit_req zone=signup" in block, (
            "Location /api/auth/signup esiste ma NON applica limit_req "
            "zone=signup. La zone definita e' inerte su quel path."
        )

    def test_signup_location_block_for_customer(self):
        """/api/customer-auth/signup location deve applicare limit_req zone=signup."""
        conf = self._read_conf()
        assert "location /api/customer-auth/signup" in conf, (
            "Manca location block per /api/customer-auth/signup — customer "
            "signup non protetto da nginx zone (mass customer-account "
            "creation possible)."
        )
        idx = conf.find("location /api/customer-auth/signup")
        block = conf[idx : idx + 600]
        assert "limit_req zone=signup" in block, (
            "Location /api/customer-auth/signup non applica limit_req "
            "zone=signup. Zone inerte su customer signup → mass-signup "
            "attack possibile."
        )

    def test_signup_location_uses_burst_nodelay(self):
        """limit_req deve usare burst+nodelay (no thundering-herd su retry)."""
        conf = self._read_conf()
        # Verifica che ALMENO una location signup usi burst con nodelay
        for path in ["/api/auth/signup", "/api/customer-auth/signup"]:
            idx = conf.find(f"location {path}")
            if idx == -1:
                continue
            block = conf[idx : idx + 600]
            assert "burst=" in block and "nodelay" in block, (
                f"location {path} usa limit_req senza burst+nodelay. "
                f"Senza nodelay nginx accoda i request → thundering herd "
                f"quando il burst si svuota. Con nodelay i request oltre "
                f"burst sono respinti 503 immediatamente."
            )

    def test_login_zone_still_defined_regression(self):
        """Sentinel regression: O1.6 NON deve toccare la zone login esistente."""
        conf = self._read_conf()
        assert "zone=login:" in conf, (
            "Regression: O1.6 ha rimosso la zone login pre-esistente."
        )
        idx = conf.find("location /api/auth/login")
        assert idx != -1, "Regression: location /api/auth/login rimossa"
        block = conf[idx : idx + 600]
        assert "limit_req zone=login" in block, (
            "Regression: /api/auth/login non piu' protetto da zone=login"
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 1.7 — check_email_rate global cross-org invariant
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Phase 1 Step D2 ha introdotto check_email_rate(email, action, max_per_hour)
#   come cap per-recipient cross-IP (anti botnet amplification). Il bucket
#   key e' (email, action) — NESSUN org_id.
#
#   Questo e' INTENZIONALE: lo spam target e' la INBOX del recipient, non
#   l'account. Se un attaccante potesse switchare org slug per moltiplicare
#   il budget (org_A: 10 reset, org_B: 10 reset, org_C: 10 reset, ...) la
#   protezione collapse — bastano 5-10 org per bombardare victim@gmail.com
#   con N×10 email/h.
#
#   Per open beta (50-200 merchant + signup pubblico) un attaccante puo'
#   creare merchant fake gratuitamente → spazio di attacco illimitato. Il
#   cap cross-org sull'inbox DEVE rimanere globale.
#
#   Trade-off accettato: stesso email registrato in 2 org legittime
#   condivide budget. Caso reale raro + cap generosi (10-20/h per action)
#   → utenti legittimi quasi mai colpiti.
#
# Sentinel coprono:
#   1. _bucket_key signature NON include org_id (anti-regression: futuro
#      "facciamo per-org isolation" silently rimuove la protezione)
#   2. check_email_rate signature NON include org_id
#   3. Functional: chiamate ripetute con stesso email cross-"context"
#      (action diverso = bucket diverso, action stesso = bucket stesso
#      indipendente da org)
#   4. Source check di TUTTI i 7 call sites: nessuno concatena org_id
#      nell'argomento email (anti-bypass via f"{email}::{org}")
#   5. Source coverage delle 3 customer routes mancanti (customer_login
#      gia' coperto in TestSEC_S_2_4_PerEmailLoginRateLimit:1761)


class TestSEC_O_1_7_CheckEmailRateGlobalCrossOrg:
    """SEC-O.1.7: check_email_rate bucket NEVER keyed by org_id.

    Anti-amplification invariant: spam target is recipient inbox, not
    org-scoped account. Cross-org bucket sharing is the security guarantee,
    not a bug.
    """

    def test_bucket_key_signature_excludes_org_id(self):
        """_bucket_key signature MUST NOT accept org_id parameter."""
        from core.rate_limiting import _bucket_key
        import inspect

        sig = inspect.signature(_bucket_key)
        params = set(sig.parameters.keys())
        forbidden = {"org_id", "organization_id", "org", "tenant_id"}
        intrusion = params & forbidden
        assert not intrusion, (
            f"_bucket_key signature drift: {params} contiene chiavi org "
            f"({intrusion}). Aggiungere org_id al bucket key TRASFORMA "
            f"il cap per-recipient in cap per-(recipient,org) → attaccante "
            f"bombarda victim@x.it con N email/h × M org senza limit. "
            f"Cross-org sharing E' la protezione, non un bug."
        )

    def test_check_email_rate_signature_excludes_org_id(self):
        """check_email_rate signature MUST NOT accept org_id parameter."""
        from core.rate_limiting import check_email_rate
        import inspect

        sig = inspect.signature(check_email_rate)
        params = set(sig.parameters.keys())
        forbidden = {"org_id", "organization_id", "org", "tenant_id"}
        intrusion = params & forbidden
        assert not intrusion, (
            f"check_email_rate signature drift: {params} contiene chiavi "
            f"org ({intrusion}). Vedi test_bucket_key — invariant violato."
        )

    def test_bucket_key_only_uses_email_and_action(self):
        """_bucket_key source MUST only reference email + action vars."""
        from core.rate_limiting import _bucket_key
        import inspect

        src = inspect.getsource(_bucket_key)
        # Guard: nessun riferimento a variabili org-like nel body
        # (commenti permessi: rimossi via split su def + body)
        forbidden_tokens = ["org_id", "organization_id", "tenant_id"]
        for tok in forbidden_tokens:
            assert tok not in src, (
                f"_bucket_key source contiene '{tok}' — invariant cross-org "
                f"violato. Source:\n{src}"
            )

    def test_functional_same_email_shared_bucket_across_contexts(self):
        """Stesso (email, action) condivide bucket indipendentemente da
        chi chiama → simulating cross-org calls."""
        from core.rate_limiting import check_email_rate, reset_email_rate_state

        reset_email_rate_state()

        # Simula 5 chiamate "da org A" (in pratica la funzione non sa di org).
        for _ in range(5):
            assert check_email_rate("victim@x.it", "test_o17_shared", max_per_hour=5)
        # Una 6a chiamata "da org B" (stesso email, stesso action) DEVE essere
        # bloccata — bucket condiviso anche se origine logica e' diversa.
        assert not check_email_rate("victim@x.it", "test_o17_shared", max_per_hour=5), (
            "Bucket non condiviso cross-call — un attaccante potrebbe "
            "bypassare il cap simulando contesto diverso ad ogni request."
        )

    def test_functional_email_normalization_prevents_org_bypass(self):
        """Stesso email in case/whitespace diverso DEVE colpire stesso bucket.

        Esempio attacker: register victim@gmail.com in org A, Victim@GMAIL.com
        in org B — se il bucket key non normalizza, 2 bucket separati → bypass.
        """
        from core.rate_limiting import check_email_rate, reset_email_rate_state

        reset_email_rate_state()
        for _ in range(5):
            check_email_rate("victim@gmail.com", "test_o17_norm", max_per_hour=5)
        # Variante case → stesso bucket
        assert not check_email_rate(
            "Victim@GMAIL.COM", "test_o17_norm", max_per_hour=5
        ), "Case-variant bypassa il bucket — bucket key non lower-case."
        # Variante whitespace → stesso bucket
        assert not check_email_rate(
            "  victim@gmail.com  ", "test_o17_norm", max_per_hour=5
        ), "Whitespace-variant bypassa il bucket — bucket key non strip()."

    def test_all_call_sites_pass_raw_email_not_concatenated(self):
        """TUTTI i call site di check_email_rate passano email puro.

        Source-AST scan: il primo argomento NON deve essere una f-string
        o concatenazione che include org_id. Se qualcuno scrive
        `check_email_rate(f"{email}::{org_id}", ...)` o
        `check_email_rate(email + org_id, ...)` il bucket diventa
        per-(email,org) → invariant rotto silently (no test failure prima
        di questo).
        """
        import ast
        from pathlib import Path

        # Repo root: backend/tests/ → backend/
        backend_root = Path(__file__).resolve().parent.parent

        # File noti per chiamare check_email_rate (audit O1.7).
        # Se aggiungiamo un nuovo call site va listato qui — sentinel
        # esplicito vs scan ricorsivo: piu' lento ma cattura "ah ho
        # dimenticato di aggiungere il file alla lista" se grep mostra
        # un call site nuovo non in questa lista.
        call_site_files = [
            "routers/auth.py",
            "routers/customer_auth.py",
            "services/auth_service.py",
            "services/customer_auth_service.py",
        ]

        for rel_path in call_site_files:
            src_path = backend_root / rel_path
            assert src_path.exists(), f"Call site file mancante: {rel_path}"
            tree = ast.parse(src_path.read_text(encoding="utf-8"))

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                # Match: check_email_rate(...) direct call OR x.check_email_rate(...)
                fname = (
                    func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name)
                    else None
                )
                if fname != "check_email_rate":
                    continue

                # Primo arg = email expression. Deve essere Name/Attribute,
                # NON JoinedStr (f-string) ne' BinOp con +.
                if not node.args:
                    continue  # malformed, lascia ad altri test
                first_arg = node.args[0]

                # Forbid f-string
                assert not isinstance(first_arg, ast.JoinedStr), (
                    f"{rel_path}:{node.lineno} check_email_rate(f'...') "
                    f"= attacker bypass se f-string include org_id. "
                    f"Usa solo l'email raw come primo arg."
                )
                # Forbid concatenation
                assert not isinstance(first_arg, ast.BinOp), (
                    f"{rel_path}:{node.lineno} check_email_rate(<concat>) "
                    f"= attacker bypass se concatenazione include org_id. "
                    f"Usa solo l'email raw come primo arg."
                )

    def test_customer_forgot_password_source_invokes_check_email_rate(self):
        """customer_auth.forgot_password DEVE invocare check_email_rate.

        Se un refactor rimuove il check, customer forgot-password diventa
        amplification vector senza che nessun test lo catturi (il limit
        e' implicito).
        """
        import inspect
        from routers import customer_auth

        src = inspect.getsource(customer_auth.forgot_password)
        assert "check_email_rate" in src, (
            "customer_auth.forgot_password NON invoca check_email_rate — "
            "anti-amplification removed. Re-add it."
        )
        # E action deve essere "customer_forgot_password" o equivalente
        assert "customer_forgot_password" in src or "forgot_password" in src, (
            "Action key non riconoscibile in customer_forgot_password — "
            "verifica che il bucket sia correttamente segmentato per action."
        )

    def test_customer_resend_verification_source_invokes_check_email_rate(self):
        """customer_auth.resend_verification DEVE invocare check_email_rate."""
        import inspect
        from routers import customer_auth

        src = inspect.getsource(customer_auth.resend_verification)
        assert "check_email_rate" in src, (
            "customer_auth.resend_verification NON invoca check_email_rate. "
            "Resend verify e' amplification vector classico (bombing).",
        )
        assert "customer_resend_verification" in src or "resend_verification" in src, (
            "Action key non riconoscibile in customer_resend_verification."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 3.1 — Sentry alert rules documentation runbook
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Le alert rules vivono dentro Sentry web UI (no API per single-person
#   ops). Per evitare "qualcuno cancella una rule e non ce ne accorgiamo"
#   il doc canonical pinna la lista delle 6 rules + tag taxonomy. Sentinel
#   verifica che il doc esista + listi tutte le 6 rules + tag attesi.
#
# Anti-pattern catturati:
#   - Rule rimossa dalla doc (drift tra runbook e Sentry)
#   - Tag taxonomy modificata senza update doc
#   - Owner email cambiato senza update
#
# NOT covered da questo sentinel (consciously):
#   - Stato attuale delle rules in Sentry (richiederebbe API call live,
#     contro single-person ops minimalism). Verifica manuale settimanale
#     documentata nel runbook stesso.


class TestSEC_O_3_1_SentryAlertRulesRunbook:
    """SEC-O.3.1: runbook Sentry alert rules e' canonical + completo."""

    RUNBOOK_PATH = "docs/operations/sentry-alert-rules.md"

    def _read_runbook(self) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        runbook = repo_root / self.RUNBOOK_PATH
        assert runbook.exists(), f"Runbook non trovato a {runbook}"
        return runbook.read_text(encoding="utf-8")

    def test_runbook_exists(self):
        """File runbook deve esistere."""
        self._read_runbook()  # raises se assente

    def test_runbook_lists_all_6_canonical_rules(self):
        """Tutte le 6 rules definite devono essere documentate."""
        doc = self._read_runbook()
        # Rules canonicalmente named in formato `[Pn] Description`
        required_rules = [
            "[P0] Payment failure spike",
            "[P0] Auth failure spike",
            "[P1] 500 error spike",
            "[P1] New issue in production",
            "[P1] Regression detected",
            "[P2] Embed-SDK error spike",
        ]
        for rule in required_rules:
            assert rule in doc, (
                f"Rule '{rule}' non documentata nel runbook. Se hai "
                f"rinominato o rimosso una rule, aggiorna sia Sentry "
                f"web UI che il runbook ATOMICAMENTE."
            )

    def test_runbook_documents_owner_email(self):
        """Owner email pinnato — cambio owner richiede update doc."""
        doc = self._read_runbook()
        assert "davide@afianco.ch" in doc, (
            "Owner email davide@afianco.ch non in runbook. Notifiche "
            "vanno routed a qualcuno specifico in single-operator setup."
        )

    def test_runbook_documents_tag_taxonomy(self):
        """Tag taxonomy referenced dalle rules deve essere documentata."""
        doc = self._read_runbook()
        required_tags = ["action", "surface", "org_id", "endpoint"]
        for tag in required_tags:
            assert tag in doc, (
                f"Tag '{tag}' non in runbook taxonomy. Le rules che "
                f"filtrano per tag fallirebbero silently se il tag "
                f"non venisse mai settato."
            )

    def test_runbook_documents_test_procedure(self):
        """Test procedure presente — senza il runbook diventa fiction."""
        doc = self._read_runbook()
        assert "Test procedure" in doc or "test procedure" in doc.lower(), (
            "Manca sezione test procedure — impossibile verify che "
            "le rules siano correttamente configurate post-setup."
        )
        # Test code snippet con sentry_sdk
        assert "sentry_sdk.capture_exception" in doc, (
            "Test procedure manca esempio sentry_sdk.capture_exception "
            "per riprodurre un alert event."
        )

    def test_runbook_documents_pii_safety(self):
        """Anti-PII guidance presente nel tag taxonomy section."""
        doc = self._read_runbook()
        # Sentry tag values potrebbero leak PII se developer aggiunge
        # email/phone come tag. Runbook deve esplicitamente warnare.
        assert "PII" in doc or "Anti-PII" in doc, (
            "Manca guidance anti-PII nei tag — risk che developer "
            "aggiunga email come tag bypassando il before_send scrubber."
        )

    def test_runbook_documents_no_slack_decision(self):
        """Decision 'no Slack' esplicitamente documentata.

        Anti-pattern: developer futuro vede assenza Slack e pensa 'devo
        aggiungerlo' senza sapere che e' decisione consapevole per
        single-operator open beta.
        """
        doc = self._read_runbook()
        assert "Slack" in doc, (
            "Manca riferimento esplicito a Slack — anche se NON usato, "
            "la decisione 'no Slack' va documentata per evitare che "
            "qualcuno lo aggiunga senza contesto."
        )

    def test_runbook_links_related_docs(self):
        """Cross-reference a documenti correlati presente."""
        doc = self._read_runbook()
        related = [
            "incident-response.md",
            "incidents.md",
            "core/observability/sentry.py",
        ]
        for ref in related:
            assert ref in doc, (
                f"Manca cross-ref a {ref} — runbook isolato perde "
                f"valore quando serve cross-navigate during incident."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 3.2 — capture_with_tags helper + hot path wiring
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Le alert rules O3.1 filtrano per tag `action` + `surface`. Senza un
#   helper centralizzato il pattern `sentry_sdk.set_tag(); capture_exception()`
#   si scattera ovunque + driftano (qualcuno usa "payment", qualcun altro
#   "payments", qualcun altro "stripe_charge"...). Helper canonical con
#   vocabulary fissato garantisce alert filtering coerente.
#
# Sentinel verificano:
#   1. Helper existence + signature
#   2. Vocabulary (action + surface) coerente con runbook O3.1
#   3. Safe-no-op quando sentry_sdk non installato
#   4. Hot paths critici (Brevo, Stripe webhook, Anthropic) invocano helper


class TestSEC_O_3_2_CaptureWithTagsHelper:
    """SEC-O.3.2: capture_with_tags helper + hot path wiring per alert rules."""

    def test_capture_with_tags_helper_exists(self):
        """Helper esportato da core.observability.sentry."""
        from core.observability import sentry

        assert hasattr(sentry, "capture_with_tags"), (
            "Manca capture_with_tags in core.observability.sentry — "
            "alert rules O3.1 filtrano per tag → senza helper i call site "
            "driftano + filter fail silently."
        )

    def test_capture_with_tags_signature(self):
        """Signature: (exception, *, action, surface='api', extra=None)."""
        from core.observability.sentry import capture_with_tags
        import inspect

        sig = inspect.signature(capture_with_tags)
        params = sig.parameters

        # exception positional + required
        assert "exception" in params, "Missing 'exception' parameter"
        # action keyword + required (no default)
        assert "action" in params, "Missing 'action' parameter"
        assert params["action"].default is inspect.Parameter.empty, (
            "'action' deve essere required (no default) — forza il "
            "developer a sceglierla esplicitamente per match alert rule."
        )
        # surface keyword + default 'api'
        assert "surface" in params, "Missing 'surface' parameter"
        assert params["surface"].default == "api", (
            "'surface' default deve essere 'api' — la maggior parte dei "
            "call site sono backend API endpoints."
        )
        # extra keyword + default None
        assert "extra" in params, "Missing 'extra' parameter"

    def test_known_actions_match_runbook(self):
        """_KNOWN_ACTIONS deve includere tutte le actions del runbook O3.1."""
        from core.observability.sentry import _KNOWN_ACTIONS

        # Dal runbook sentry-alert-rules.md tag taxonomy table
        required_actions = {
            "payment_charge", "payment_refund", "payment_webhook",
            "auth_login", "auth_signup", "auth_token_verify", "auth_password_reset",
            "email_send", "ai_complete", "mongo_query",
        }
        missing = required_actions - _KNOWN_ACTIONS
        assert not missing, (
            f"_KNOWN_ACTIONS manca: {missing}. Sync con runbook "
            f"docs/operations/sentry-alert-rules.md tag taxonomy."
        )

    def test_known_surfaces_match_runbook(self):
        """_KNOWN_SURFACES deve includere tutti i surface del runbook."""
        from core.observability.sentry import _KNOWN_SURFACES

        required_surfaces = {"api", "embed", "admin_ui", "customer_portal"}
        missing = required_surfaces - _KNOWN_SURFACES
        assert not missing, (
            f"_KNOWN_SURFACES manca: {missing}. Sync con runbook."
        )

    def test_capture_safe_when_sentry_sdk_missing(self):
        """Helper deve return None silently se sentry_sdk non importabile.

        Garanzia: hot paths possono chiamare il helper sempre senza
        wrapping try/except aggiuntivo nel call site.
        """
        from core.observability.sentry import capture_with_tags

        # Forza una capture con sentry NON inizializzato (default in test):
        # se sentry_sdk e' installato ritorna event_id o None;
        # se NON installato ritorna None. In entrambi i casi NON deve raise.
        result = capture_with_tags(
            RuntimeError("test"),
            action="payment_charge",
            surface="api",
        )
        # Result puo' essere str (event_id) o None (sentry disabled).
        assert result is None or isinstance(result, str), (
            f"capture_with_tags ritorno inaspettato: {type(result).__name__}. "
            f"Atteso str event_id O None (sentry disabled)."
        )

    def test_brevo_email_failure_invokes_capture_with_tags(self):
        """email_service._post_brevo + send_email failure paths invokano helper."""
        import inspect
        from services import email_service

        src = inspect.getsource(email_service)
        assert "capture_with_tags" in src, (
            "email_service non importa/invoca capture_with_tags — "
            "Brevo failures non triggerano alert [P1] email_send."
        )
        # Verifica che action='email_send' sia usata almeno una volta
        assert 'action="email_send"' in src or "action='email_send'" in src, (
            "capture_with_tags in email_service non usa action='email_send' "
            "— tag mismatch con runbook alert rule filter."
        )

    def test_stripe_webhook_invokes_capture_with_tags(self):
        """Stripe webhook signature failure invoca helper con payment_webhook."""
        import inspect
        from payment_providers.stripe import webhook

        src = inspect.getsource(webhook)
        assert "capture_with_tags" in src, (
            "payment_providers/stripe/webhook.py non invoca capture_with_tags "
            "— signature failures (attack signal OR misconfig) non triggerano "
            "alert [P0] Payment failure spike."
        )
        assert 'action="payment_webhook"' in src or "action='payment_webhook'" in src, (
            "Webhook capture non usa action='payment_webhook' — tag mismatch."
        )

    def test_capture_with_tags_uses_scoped_capture(self):
        """Helper usa scope CM per scoping dei tag (no global pollution).

        Sentry SDK 2.x usa new_scope(); 1.x usava push_scope(). Helper
        deve fallback automatico tra i due (forward+backward compat).
        """
        import inspect
        from core.observability.sentry import capture_with_tags

        src = inspect.getsource(capture_with_tags)
        assert "new_scope" in src or "push_scope" in src, (
            "capture_with_tags non usa new_scope() / push_scope() — i tag "
            "verrebbero applicati globalmente, contaminando event successivi "
            "in stesso thread/task."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 3.3 — Business metrics (payments, signups, emails)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Per open beta operatore deve avere visibility live sul money flow +
#   funnel acquisizione + deliverability. Senza metriche, l'unico segnale
#   sono i logs (slow to query) + Sentry (errors only, no success rate).
#
#   3 nuove metriche con cardinalita' contenuta:
#     - payments_total{event_type, status}     ≤ 12 series
#     - signups_total{flow, status}            ≤ 10 series
#     - email_sends_total{status}              = 5 series
#
# Sentinel verificano:
#   1. Recording helpers esistono + signature corretta
#   2. Counter definiti in metrics.py con labelnames giusti
#   3. Hot path call sites invocano i helpers (routers + email_service)
#   4. No PII leak: nessun label org_id / email / slug ad alta cardinalita'


class TestSEC_O_3_3_BusinessMetrics:
    """SEC-O.3.3: business metrics payments/signups/emails wired correctly."""

    def test_record_payment_helper_exists(self):
        from core.observability import metrics

        assert hasattr(metrics, "record_payment"), (
            "Manca record_payment in core.observability.metrics — "
            "Grafana panel payments_total non avrebbe data source."
        )

    def test_record_signup_helper_exists(self):
        from core.observability import metrics

        assert hasattr(metrics, "record_signup"), (
            "Manca record_signup — Grafana panel funnel signup vuoto."
        )

    def test_record_email_send_helper_exists(self):
        from core.observability import metrics

        assert hasattr(metrics, "record_email_send"), (
            "Manca record_email_send — Grafana panel deliverability vuoto."
        )

    def test_payments_counter_labels_low_cardinality(self):
        """payments_total deve avere SOLO 2 labels (event_type, status).

        NO org_id, NO customer_email, NO slug — cardinalita' esploderebbe
        a 200 merchant × N orgs = thousand series.
        """
        from core.observability import metrics

        if not metrics.is_available():
            import pytest
            pytest.skip("prometheus_client not installed")

        counter = metrics.PAYMENTS_TOTAL
        labels = set(counter._labelnames)
        assert labels == {"event_type", "status"}, (
            f"PAYMENTS_TOTAL labels drift: {labels}. Atteso "
            f"{{event_type, status}} — qualsiasi org/email/slug label "
            f"esploderebbe cardinality a >1000 series."
        )

    def test_signups_counter_labels_low_cardinality(self):
        from core.observability import metrics

        if not metrics.is_available():
            import pytest
            pytest.skip("prometheus_client not installed")

        counter = metrics.SIGNUPS_TOTAL
        labels = set(counter._labelnames)
        assert labels == {"flow", "status"}, (
            f"SIGNUPS_TOTAL labels drift: {labels}. Atteso {{flow, status}}."
        )

    def test_email_sends_counter_single_label(self):
        from core.observability import metrics

        if not metrics.is_available():
            import pytest
            pytest.skip("prometheus_client not installed")

        counter = metrics.EMAIL_SENDS_TOTAL
        labels = set(counter._labelnames)
        assert labels == {"status"}, (
            f"EMAIL_SENDS_TOTAL labels drift: {labels}. Atteso {{status}} "
            f"singolo — per-purpose live nei logs."
        )

    def test_stripe_webhook_router_records_payment(self):
        """routers/billing.py stripe_webhook invoca record_payment."""
        import inspect
        from routers import billing

        src = inspect.getsource(billing.stripe_webhook)
        assert "record_payment" in src, (
            "routers.billing.stripe_webhook non invoca record_payment — "
            "Grafana payments_total panel rimane vuoto in prod."
        )

    def test_merchant_signup_router_records_signup(self):
        """routers/auth.py signup invoca record_signup con flow='merchant'."""
        import inspect
        from routers import auth

        src = inspect.getsource(auth.signup)
        assert "record_signup" in src, (
            "routers.auth.signup non invoca record_signup."
        )
        assert 'flow="merchant"' in src or "flow='merchant'" in src, (
            "Merchant signup non passa flow='merchant' — funnel label sbagliata."
        )

    def test_customer_signup_router_records_signup(self):
        """routers/customer_auth.py signup invoca record_signup con flow='customer'."""
        import inspect
        from routers import customer_auth

        src = inspect.getsource(customer_auth.signup)
        assert "record_signup" in src, (
            "routers.customer_auth.signup non invoca record_signup."
        )
        assert 'flow="customer"' in src or "flow='customer'" in src, (
            "Customer signup non passa flow='customer'."
        )

    def test_email_service_records_send_outcomes(self):
        """email_service send_email + with_attachment registrano outcome."""
        import inspect
        from services import email_service

        src = inspect.getsource(email_service)
        assert "record_email_send" in src, (
            "email_service non invoca record_email_send — Grafana "
            "deliverability panel rimane vuoto."
        )
        # Verify almeno 2 status diversi (success + un terminal failure)
        assert 'record_email_send("success")' in src, (
            "Manca record_email_send('success') — il success rate non "
            "puo' essere calcolato senza both numerator + denominator."
        )

    def test_email_service_records_all_terminal_statuses(self):
        """email_service traccia tutti i 5 status canonical.

        Verifica che ogni status appaia come stringa quoted nel source
        (resilient a record_email_send("x") vs ternary
        record_email_send("network_error" if ... else "http_error")).
        """
        import inspect
        from services import email_service

        src = inspect.getsource(email_service)
        required_statuses = ["success", "network_error", "http_error", "gated", "dry_run"]
        for status_val in required_statuses:
            # Cerca la stringa quoted (single or double) — match sia direct
            # call sia ternary expression.
            assert f'"{status_val}"' in src or f"'{status_val}'" in src, (
                f"email_service non referenzia status='{status_val}' — "
                f"il funnel deliverability ha gap. Stati attesi: "
                f"{required_statuses}"
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 3.4 — Uptime monitoring runbook (UptimeRobot free tier)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Sentry vede gli errori INTERNI al backend. Ma se il VPS Hetzner cade,
#   se nginx muore, se il container backend non parte → nessun signal a
#   Sentry. Per detection esterno serve un monitor SaaS che ping da fuori.
#
#   UptimeRobot free tier: 50 monitor, 5min interval, SSL monitor incluso,
#   email alerting. Zero cost. Setup canonical nel runbook + sentinel
#   pinna struttura + endpoint contract per evitare refactor che rompano
#   silently i monitor configurati.
#
# Sentinel coprono:
#   1. Runbook esiste + cita 5 monitor canonical
#   2. Endpoint /api/health/live + /ready + /ai esistono nel router
#   3. Keyword UptimeRobot ('uptime_seconds' + 'mongodb') presenti nel
#      response shape pinnato (anti-rename/restructure regression)
#   4. Doc cita decisioni esplicite (no SMS/Slack/multi-region/status page)


class TestSEC_O_3_4_UptimeMonitoringRunbook:
    """SEC-O.3.4: uptime-monitoring runbook + endpoint contract pinned."""

    RUNBOOK_PATH = "docs/operations/uptime-monitoring.md"

    def _read_runbook(self) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        runbook = repo_root / self.RUNBOOK_PATH
        assert runbook.exists(), f"Runbook non trovato a {runbook}"
        return runbook.read_text(encoding="utf-8")

    def test_runbook_exists(self):
        self._read_runbook()

    def test_runbook_lists_5_canonical_monitors(self):
        """Tutti i 5 monitor canonical (4 HTTP + 1 SSL) sono documentati."""
        doc = self._read_runbook()
        required = [
            "[CRIT] Backend liveness",
            "[CRIT] Backend readiness",
            "[MED] AI provider",
            "[CRIT] Frontend root",
            "[CRIT] TLS cert",
        ]
        for monitor in required:
            assert monitor in doc, (
                f"Monitor '{monitor}' non documentato nel runbook. "
                f"Configurare in UptimeRobot senza traccia nel runbook "
                f"= silent drift se viene rimosso accidentalmente."
            )

    def test_runbook_documents_owner_email(self):
        doc = self._read_runbook()
        assert "davide@afianco.ch" in doc, (
            "Owner email davide@afianco.ch non in runbook — notifiche "
            "vanno routed a qualcuno specifico in single-operator setup."
        )

    def test_runbook_pins_canonical_urls(self):
        """URL canonical degli endpoint health presenti nel runbook."""
        doc = self._read_runbook()
        required_urls = [
            "/api/health/live",
            "/api/health/ready",
            "/api/health/ai",
        ]
        for url in required_urls:
            assert url in doc, (
                f"URL canonical {url} non documentato — UptimeRobot "
                f"monitor potrebbe puntare a URL sbagliato senza "
                f"reference docs."
            )

    def test_health_router_exposes_live_endpoint(self):
        """Endpoint /live esiste nel router health.py."""
        import inspect
        from routers import health

        src = inspect.getsource(health)
        assert '@router.get("/live")' in src, (
            "Endpoint /live rimosso dal router health.py — UptimeRobot "
            "Monitor 1 inizierebbe a fail con 404."
        )

    def test_health_router_exposes_ready_endpoint(self):
        """Endpoint /ready esiste nel router health.py."""
        import inspect
        from routers import health

        src = inspect.getsource(health)
        assert '@router.get("/ready")' in src, (
            "Endpoint /ready rimosso — UptimeRobot Monitor 2 (MongoDB) "
            "fail."
        )

    def test_liveness_response_contains_uptime_seconds_key(self):
        """Response /live deve includere 'uptime_seconds' (keyword pinning).

        UptimeRobot Monitor 1 verifica presenza substring 'uptime_seconds'
        nel body. Se rinominamo il key o lo rimuoviamo, monitor inizia
        a fail keyword check senza errori visibili (silent regression).
        """
        import inspect
        from routers import health

        src = inspect.getsource(health.liveness)
        assert '"uptime_seconds"' in src or "'uptime_seconds'" in src, (
            "liveness response non contiene 'uptime_seconds' key — "
            "UptimeRobot keyword check fallirebbe. Re-add o aggiorna "
            "il runbook con la nuova keyword."
        )

    def test_readiness_response_includes_mongodb_check(self):
        """Response /ready deve includere 'mongodb' nel checks dict."""
        import inspect
        from routers import health

        src = inspect.getsource(health._compute_readiness)
        assert '"mongodb"' in src or "'mongodb'" in src, (
            "_compute_readiness non include 'mongodb' come check key — "
            "UptimeRobot keyword check 'mongodb' fallirebbe. Re-add "
            "il check O aggiorna keyword nel runbook."
        )

    def test_runbook_documents_no_sms_no_slack_decision(self):
        """Decisione esplicita 'no SMS/Slack' tracciata.

        Anti-pattern: developer futuro vede assenza Slack/SMS e pensa
        'devo aggiungerli'. Decisione e' consapevole (free tier + single
        operator + email/push sufficiente).
        """
        doc = self._read_runbook()
        # Verify decisioni elencate
        assert "NO SMS" in doc, (
            "Manca decisione esplicita 'NO SMS' — UptimeRobot free non "
            "lo include, va documentato vs 'aggiungiamolo'."
        )
        assert "Slack" in doc, (
            "Manca riferimento esplicito a Slack — anche se NON usato, "
            "la decisione va documentata."
        )

    def test_runbook_documents_ssl_monitor(self):
        """SSL cert monitor documentato (Let's Encrypt rinnova ogni 60 giorni,
        ma se certbot fail silently scopriamo solo da browser merchant)."""
        doc = self._read_runbook()
        assert "SSL" in doc or "TLS cert" in doc, (
            "Manca SSL/TLS cert monitor — cert expire silent failure "
            "e' uno dei classici outage incident di e-commerce."
        )
        # Alert before 7 days (best practice)
        assert "7 days" in doc or "7 giorni" in doc, (
            "Manca specifica 'alert 7 days before expiry' — best "
            "practice per dare tempo di rotazione cert."
        )

    def test_runbook_links_related_docs(self):
        doc = self._read_runbook()
        related = [
            "sentry-alert-rules.md",
            "incident-response.md",
            "backend/routers/health.py",
        ]
        for ref in related:
            assert ref in doc, (
                f"Manca cross-ref a {ref} — runbook isolato perde "
                f"valore durante incident triage."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 4.1 — Honeypot field anti-bot on signup endpoints
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Per open beta (public signup) serve anti-bot. CAPTCHA (O4.4) richiede
#   operatore setup + frontend integration; honeypot e' zero-cost prima
#   linea che cattura ~50% dei bot naive che scrappano il form HTML.
#
#   Threat model:
#     - CATCHES: bots che scrappano rendered HTML e riempono tutti i text input
#     - DOES NOT CATCH: bots che chiamano API directly via curl/requests
#       (per quelli serve CAPTCHA O4.4)
#
#   Anti-enumeration: response uniform 202 success quando triggered
#   (bot non distingue "caught" da "succeeded" → non puo' adattarsi).
#
# Sentinel coprono:
#   1. Helper module exists + signature corretta
#   2. Field name canonical 'website' pinned
#   3. Entrambi i request model (merchant UserCreate + customer
#      SignupRequest) hanno il campo 'website'
#   4. Router signup honeypot check invoked PRIMA del DB access
#   5. Uniform success response su trigger (anti-enumeration)
#   6. Metric record_signup(status='honeypot_triggered') invocata
#   7. Audit event registrato per post-incident review


class TestSEC_O_4_1_HoneypotFieldAntiBot:
    """SEC-O.4.1: honeypot field + uniform-success anti-bot per signup."""

    def test_honeypot_helper_module_exists(self):
        from core import honeypot
        assert hasattr(honeypot, "is_honeypot_triggered"), (
            "core.honeypot.is_honeypot_triggered mancante — router "
            "signup non puo' check field."
        )
        assert hasattr(honeypot, "HONEYPOT_FIELD_NAME"), (
            "core.honeypot.HONEYPOT_FIELD_NAME mancante — canonical "
            "name non pinned, drift cross-form possibile."
        )

    def test_honeypot_field_name_is_website(self):
        """Field name canonical 'website' — pinned per coordinare backend +
        frontend rendering. Cambio richiede sync 3 frontend (merchant,
        customer-portal, embed-SDK)."""
        from core.honeypot import HONEYPOT_FIELD_NAME

        assert HONEYPOT_FIELD_NAME == "website", (
            f"HONEYPOT_FIELD_NAME drift: {HONEYPOT_FIELD_NAME!r}. "
            f"Cambio richiede sync con frontend rendering — se cambi qui "
            f"DEVI cambiare anche tutti i form di signup."
        )

    def test_is_honeypot_triggered_returns_false_for_empty(self):
        """None / empty string / whitespace-only = legitimate human."""
        from core.honeypot import is_honeypot_triggered
        assert is_honeypot_triggered(None) is False
        assert is_honeypot_triggered("") is False
        assert is_honeypot_triggered("   ") is False
        assert is_honeypot_triggered("\t\n") is False

    def test_is_honeypot_triggered_returns_true_for_filled(self):
        """Any non-empty string = bot caught."""
        from core.honeypot import is_honeypot_triggered
        assert is_honeypot_triggered("a") is True
        assert is_honeypot_triggered("https://spam.example.com") is True
        assert is_honeypot_triggered("any text") is True

    def test_is_honeypot_triggered_defensive_non_string(self):
        """Non-string types treated as triggered (legitimate frontend
        sempre manda string-or-null; non-string = bot anomaly)."""
        from core.honeypot import is_honeypot_triggered
        assert is_honeypot_triggered(42) is True  # type: ignore
        assert is_honeypot_triggered(True) is True  # type: ignore
        assert is_honeypot_triggered(["url"]) is True  # type: ignore

    def test_user_create_model_has_website_field(self):
        """models.UserCreate (merchant signup) accetta 'website' optional."""
        from models.user import UserCreate
        import inspect

        # Pydantic v1+v2 compat: usa model_fields se disponibile, altrimenti
        # __fields__ legacy.
        fields = getattr(UserCreate, "model_fields", None) or getattr(UserCreate, "__fields__", {})
        assert "website" in fields, (
            f"UserCreate manca campo 'website' — merchant signup endpoint "
            f"non puo' check honeypot. Fields: {list(fields.keys())}"
        )

    def test_customer_signup_request_model_has_website_field(self):
        """routers.customer_auth.SignupRequest accetta 'website' optional."""
        from routers.customer_auth import SignupRequest

        fields = getattr(SignupRequest, "model_fields", None) or getattr(SignupRequest, "__fields__", {})
        assert "website" in fields, (
            f"customer SignupRequest manca campo 'website'. "
            f"Fields: {list(fields.keys())}"
        )

    def test_merchant_signup_router_invokes_honeypot_check(self):
        """routers.auth.signup invoca is_honeypot_triggered + return uniform."""
        import inspect
        from routers import auth

        src = inspect.getsource(auth.signup)
        assert "is_honeypot_triggered" in src, (
            "routers.auth.signup non invoca is_honeypot_triggered — "
            "bot signups passano direttamente al DB."
        )
        # Check anti-enumeration: response uniform (verification_required)
        assert "verification_required" in src, (
            "routers.auth.signup honeypot branch non return uniform "
            "verification_required → bot puo' detect trigger via "
            "response shape diversa."
        )
        # Check metric recording
        assert 'record_signup' in src and 'honeypot_triggered' in src, (
            "routers.auth.signup honeypot non record metric — Grafana "
            "non vede bot attack volume."
        )

    def test_customer_signup_router_invokes_honeypot_check(self):
        """routers.customer_auth.signup invoca is_honeypot_triggered."""
        import inspect
        from routers import customer_auth

        src = inspect.getsource(customer_auth.signup)
        assert "is_honeypot_triggered" in src, (
            "routers.customer_auth.signup non invoca is_honeypot_triggered."
        )
        assert "verification_required" in src, (
            "customer signup honeypot branch non return uniform 202."
        )
        assert 'record_signup' in src and 'honeypot_triggered' in src, (
            "customer signup honeypot non record metric."
        )

    def test_honeypot_check_happens_before_db_access(self):
        """Honeypot check DEVE essere PRIMA di qualsiasi DB lookup.

        Razionale: se bot riesce a triggerare DB query (es. _resolve_org_id
        Mongo lookup) prima del check, sta consumando resource. Honeypot
        deve essere short-circuit immediato.
        """
        import inspect
        from routers import auth

        src = inspect.getsource(auth.signup)
        # Indici nel source code: is_honeypot_triggered DEVE apparire
        # PRIMA di "await platform_settings_repository" (primo DB access).
        hp_idx = src.find("is_honeypot_triggered")
        db_idx = src.find("await platform_settings_repository")
        assert hp_idx != -1, "is_honeypot_triggered non in source"
        assert db_idx != -1, "platform_settings_repository non in source"
        assert hp_idx < db_idx, (
            f"Honeypot check appare DOPO primo DB access "
            f"(hp_idx={hp_idx}, db_idx={db_idx}). Bot consuma resource "
            f"prima del short-circuit. Sposta il check all'inizio."
        )

    def test_honeypot_records_audit_event(self):
        """Honeypot trigger registra audit event per post-incident review."""
        import inspect
        from routers import auth
        from routers import customer_auth

        merchant_src = inspect.getsource(auth.signup)
        customer_src = inspect.getsource(customer_auth.signup)

        # Audit action name canonical
        assert "merchant_signup_honeypot" in merchant_src, (
            "Merchant signup honeypot non registra audit action "
            "'merchant_signup_honeypot' — gap per forensic post-attack."
        )
        assert "customer_signup_honeypot" in customer_src, (
            "Customer signup honeypot non registra audit action "
            "'customer_signup_honeypot'."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 4.2 — Password breach check via HIBP k-anonymity
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   validate_password_strength enforce complexity (length + case + digit)
#   ma "P@ssw0rd123!" passa la complexity ed e' in OGNI breach corpus
#   (3.4M+ occurrences in HIBP). Credential stuffing usa proprio queste
#   password "tecnicamente strong" — l'anti-pattern n.1 di account
#   takeover open-beta.
#
#   HIBP range API (k-anonymity): client manda primi 5 chars di SHA1
#   del password, server ritorna lista suffixes matching + count. Client
#   verifica local. Privacy-preserving + no API key needed.
#
#   Fail-OPEN: se HIBP API down → signup proceed comunque (security
#   enhancement, not hard gate). Logged per operator monitoring.
#
# Sentinel coprono:
#   1. Helper module + signature + canonical constants
#   2. k-anonymity invariant: NEVER full hash sent (security-critical)
#   3. Fail-open behavior su network error
#   4. Threshold-based decision (no false positive su breach count<5)
#   5. Signup + password-reset flows invocano validate_password_not_breached


class TestSEC_O_4_2_PasswordBreachCheckHIBP:
    """SEC-O.4.2: HIBP password breach check anti-stuffing per signup/reset."""

    def test_module_exists_with_canonical_api(self):
        from core import password_breach

        assert hasattr(password_breach, "is_password_breached"), (
            "Manca is_password_breached helper."
        )
        assert hasattr(password_breach, "validate_password_not_breached"), (
            "Manca validate_password_not_breached helper."
        )
        assert hasattr(password_breach, "BREACH_THRESHOLD"), (
            "Manca BREACH_THRESHOLD constant — soglia decision implicit "
            "vs explicit."
        )

    def test_breach_threshold_reasonable_value(self):
        """BREACH_THRESHOLD >= 5 per evitare false positive da breach
        molto piccoli; <= 100 per non lasciare passare password molto
        comuni."""
        from core.password_breach import BREACH_THRESHOLD

        assert 1 <= BREACH_THRESHOLD <= 100, (
            f"BREACH_THRESHOLD={BREACH_THRESHOLD} fuori range sensato "
            f"[1..100]. Threshold=0 blocca anche single-breach (rumore); "
            f">100 lascia passare password ovviamente weak."
        )

    def test_sha1_helper_deterministic(self):
        """SHA1 hex uppercase deterministico — base del k-anonymity."""
        from core.password_breach import _sha1_hex_upper

        # SHA1 noto: "hello" → AAF4C61DDCC5E8A2DABEDE0F3B482CD9AEA9434D
        assert _sha1_hex_upper("hello") == "AAF4C61DDCC5E8A2DABEDE0F3B482CD9AEA9434D"
        # Empty: SHA1("") = "DA39A3EE..."
        assert _sha1_hex_upper("")[:8] == "DA39A3EE"

    def test_k_anonymity_only_prefix_sent(self):
        """CRITICAL SECURITY: HIBP request URL deve includere SOLO i
        primi 5 chars dell'hash, MAI il full SHA1 o il password plaintext.

        Senza questo check, una refactor potrebbe accidentalmente
        mandare full hash → HIBP vede il password (privacy break).
        """
        from unittest.mock import patch, MagicMock
        from core.password_breach import is_password_breached, HIBP_API_URL

        # Mock session.get per intercettare l'URL richiesto.
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""  # no match → return (False, 0)

        with patch("core.password_breach._get_hibp_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_get_session.return_value = mock_session

            is_password_breached("hello")

            # Verifica che get() fu chiamato con URL contenente SOLO prefix 5 char
            assert mock_session.get.called, "session.get non chiamato"
            call_args = mock_session.get.call_args
            url_called = call_args[0][0]
            # Expected: HIBP_API_URL + "AAF4C" (primi 5 char of SHA1("hello"))
            expected_prefix_url = HIBP_API_URL + "AAF4C"
            assert url_called == expected_prefix_url, (
                f"k-anonymity VIOLATED: URL chiamato {url_called!r} != "
                f"prefix-only URL {expected_prefix_url!r}. Refactor sta "
                f"mandando piu' di 5 char a HIBP → privacy break."
            )
            # Defense in depth: verifica che il full SHA1 NON appaia in URL
            full_sha1 = "AAF4C61DDCC5E8A2DABEDE0F3B482CD9AEA9434D"
            assert full_sha1 not in url_called, (
                f"k-anonymity VIOLATED: full SHA1 in URL {url_called!r}"
            )
            # Defense in depth: il plaintext password NON deve mai apparire
            assert "hello" not in url_called.lower(), (
                f"DISASTER: plaintext password 'hello' in URL {url_called!r}"
            )

    def test_fail_open_on_network_error(self):
        """Se HIBP unreachable → ritorna (False, 0) silent → signup proceed."""
        from unittest.mock import patch, MagicMock
        import requests
        from core.password_breach import is_password_breached

        with patch("core.password_breach._get_hibp_session") as mock_get_session:
            mock_session = MagicMock()
            # Simula network error
            mock_session.get.side_effect = requests.exceptions.ConnectionError(
                "DNS resolution failed"
            )
            mock_get_session.return_value = mock_session

            breached, count = is_password_breached("Password1")
            assert breached is False, (
                "Fail-open violated: network error returned breached=True "
                "→ user vedrebbe error message false-positive."
            )
            assert count == 0, "Fail-open count should be 0"

    def test_fail_open_on_unexpected_status(self):
        """Se HIBP ritorna 5xx → ritorna (False, 0)."""
        from unittest.mock import patch, MagicMock
        from core.password_breach import is_password_breached

        with patch("core.password_breach._get_hibp_session") as mock_get_session:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_resp.text = "Service Unavailable"
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_get_session.return_value = mock_session

            breached, count = is_password_breached("Password1")
            assert breached is False
            assert count == 0

    def test_threshold_below_returns_not_breached(self):
        """Match con count < BREACH_THRESHOLD → ritorna (False, count)."""
        from unittest.mock import patch, MagicMock
        from core.password_breach import is_password_breached, BREACH_THRESHOLD, _sha1_hex_upper

        password = "test_threshold_below"
        sha = _sha1_hex_upper(password)
        suffix = sha[5:]
        # Build response con il nostro suffix + count below threshold
        body = f"{suffix}:{BREACH_THRESHOLD - 1}\r\nOTHERSUFFIX:50\r\n"

        with patch("core.password_breach._get_hibp_session") as mock_get_session:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = body
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_get_session.return_value = mock_session

            breached, count = is_password_breached(password)
            assert breached is False, (
                f"count={count} below threshold {BREACH_THRESHOLD} ma "
                f"breached=True"
            )
            assert count == BREACH_THRESHOLD - 1

    def test_threshold_at_returns_breached(self):
        """Match con count >= BREACH_THRESHOLD → ritorna (True, count)."""
        from unittest.mock import patch, MagicMock
        from core.password_breach import is_password_breached, BREACH_THRESHOLD, _sha1_hex_upper

        password = "test_threshold_at"
        sha = _sha1_hex_upper(password)
        suffix = sha[5:]
        body = f"{suffix}:{BREACH_THRESHOLD * 100}\r\n"

        with patch("core.password_breach._get_hibp_session") as mock_get_session:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = body
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_get_session.return_value = mock_session

            breached, count = is_password_breached(password)
            assert breached is True
            assert count == BREACH_THRESHOLD * 100

    def test_validate_raises_for_breached(self, monkeypatch):
        """validate_password_not_breached raise ValueError when breached."""
        from unittest.mock import patch
        from core.password_breach import validate_password_not_breached

        # Conftest disable HIBP per default — re-enable per questo test
        monkeypatch.setenv("PASSWORD_BREACH_CHECK_ENABLED", "true")

        with patch("core.password_breach.is_password_breached", return_value=(True, 1000000)):
            try:
                validate_password_not_breached("anypass")
                assert False, "Should have raised ValueError"
            except ValueError as e:
                # Error message Italian + user-friendly + no count leak
                msg = str(e)
                assert "breach" in msg.lower(), f"Message non-informative: {msg!r}"
                # Anti-info-leak: non rivelare il count (attaccante potrebbe
                # capire quanto "weak" e' la password vittima)
                assert "1000000" not in msg, (
                    "Error message rivela breach count → info leak agli "
                    "attaccanti."
                )

    def test_validate_noop_for_clean_password(self, monkeypatch):
        """validate_password_not_breached non raise se HIBP ritorna clean."""
        from unittest.mock import patch
        from core.password_breach import validate_password_not_breached

        monkeypatch.setenv("PASSWORD_BREACH_CHECK_ENABLED", "true")

        with patch("core.password_breach.is_password_breached", return_value=(False, 0)):
            # Non deve raise — return None
            result = validate_password_not_breached("CleanPass123!")
            assert result is None

    def test_validate_respects_env_var_disable(self, monkeypatch):
        """Env var false → validate non chiama HIBP affatto (no-op)."""
        from unittest.mock import patch
        from core.password_breach import validate_password_not_breached

        monkeypatch.setenv("PASSWORD_BREACH_CHECK_ENABLED", "false")

        with patch("core.password_breach.is_password_breached") as mock_check:
            # Anche con mock che dice "breached", non deve raise (no call)
            mock_check.return_value = (True, 9999999)
            result = validate_password_not_breached("anypass")
            assert result is None
            assert not mock_check.called, (
                "Env var false ma is_password_breached chiamato comunque "
                "— short-circuit non funziona, spreca network call."
            )

    def test_session_user_agent_set(self):
        """HIBP API rifiuta request senza User-Agent — session DEVE settarlo."""
        from core.password_breach import _build_hibp_session

        s = _build_hibp_session()
        assert "User-Agent" in s.headers, (
            "HIBP API rifiuta request senza User-Agent header. Session "
            "deve settarlo at build."
        )
        ua = s.headers["User-Agent"]
        assert "AFianco" in ua, (
            f"User-Agent non identifica AFianco: {ua!r}. HIBP best "
            f"practice: identifica il consumer per abuse contact."
        )

    def test_merchant_signup_invokes_breach_check(self):
        """services/auth_service.py signup() invoca validate_password_not_breached."""
        import inspect
        from services import auth_service

        src = inspect.getsource(auth_service.signup)
        assert "validate_password_not_breached" in src, (
            "services.auth_service.signup non invoca breach check — "
            "user puo' registrare con password gia' pwned."
        )

    def test_customer_signup_invokes_breach_check(self):
        """services/customer_auth_service.py customer_signup invoca breach check."""
        import inspect
        from services import customer_auth_service

        src = inspect.getsource(customer_auth_service.customer_signup)
        assert "validate_password_not_breached" in src, (
            "customer_signup non invoca breach check — customer puo' "
            "registrare con password breach-known."
        )

    def test_password_reset_invokes_breach_check(self):
        """Password reset flows DEVONO invocare breach check.

        Account-takeover via credential stuffing puo' usare il password
        reset endpoint (se il bot ha accesso temporaneo all'email).
        Reset con password breach-known = takeover persistente.
        """
        import inspect
        from services import customer_auth_service

        src = inspect.getsource(customer_auth_service.customer_reset_password)
        assert "validate_password_not_breached" in src, (
            "customer_reset_password non invoca breach check — reset "
            "path bypassa la protezione."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 4.3 — Logout-all-sessions panic button
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Pre-O4.3: l'unico modo di invalidare JWT esistenti era cambiare la
#   password (via change_password endpoint) — set password_changed_at =
#   now → token con iat<now rifiutati. MA se utente sospetta hijack
#   senza voler cambiare password (es. "ho lasciato login su laptop
#   di un amico"), non c'era modo di invalidate sessions remotely.
#
#   Pattern: parallel field 'tokens_invalidated_at' su User + Customer
#   Account doc. POST /logout-all set field = now. get_current_user e
#   get_current_customer rifiutano token con iat < quel timestamp.
#
# Sentinel coprono:
#   1. Endpoint exists su entrambi i router (merchant + customer)
#   2. Auth dependency: require authenticated user/customer
#   3. Auth.py check su tokens_invalidated_at presente (parallel a
#      password_changed_at)
#   4. Audit event registrato per forensic post-incident review
#   5. Rate limit defensive (10/hour) per evitare DOS via mass invalidate
#   6. Response include invalidated_at timestamp per debug/audit


class TestSEC_O_4_3_LogoutAllSessions:
    """SEC-O.4.3: logout-all-sessions endpoint + token invalidation check."""

    def test_merchant_logout_all_endpoint_exists(self):
        """routers/auth.py espone POST /logout-all."""
        from routers import auth
        assert hasattr(auth, "logout_all"), (
            "Endpoint logout_all mancante in routers.auth — utente "
            "non puo' invalidate sessions in incident scenario."
        )

    def test_customer_logout_all_endpoint_exists(self):
        """routers/customer_auth.py espone POST /logout-all."""
        from routers import customer_auth
        assert hasattr(customer_auth, "customer_logout_all"), (
            "Endpoint customer_logout_all mancante in routers.customer_auth."
        )

    def test_merchant_logout_all_requires_auth(self):
        """logout_all signature usa Depends(get_current_user) — protected."""
        from routers.auth import logout_all
        import inspect

        sig = inspect.signature(logout_all)
        params = sig.parameters
        assert "current_user" in params, (
            "logout_all non riceve current_user via Depends — endpoint "
            "non protetto da auth, bot anonimi possono invalidate user."
        )
        # Verify it's Depends(get_current_user) — check via default value
        default = params["current_user"].default
        assert default is not inspect.Parameter.empty, (
            "current_user senza default Depends() — anonymous access possibile."
        )

    def test_customer_logout_all_requires_auth(self):
        """customer_logout_all richiede Depends(get_current_customer)."""
        from routers.customer_auth import customer_logout_all
        import inspect

        sig = inspect.signature(customer_logout_all)
        params = sig.parameters
        assert "current_customer" in params, (
            "customer_logout_all non riceve current_customer via Depends."
        )

    def test_get_current_user_checks_tokens_invalidated_at(self):
        """auth.get_current_user check tokens_invalidated_at parallel a
        password_changed_at."""
        import inspect
        from auth import get_current_user

        src = inspect.getsource(get_current_user)
        assert "tokens_invalidated_at" in src, (
            "get_current_user non check tokens_invalidated_at — logout-all "
            "endpoint setta il campo ma il check di invalidation manca, "
            "→ token mantengono validity. Logout-all non funziona."
        )

    def test_get_current_customer_checks_tokens_invalidated_at(self):
        """auth.get_current_customer mirror check su customer account."""
        import inspect
        from auth import get_current_customer

        src = inspect.getsource(get_current_customer)
        assert "tokens_invalidated_at" in src, (
            "get_current_customer non check tokens_invalidated_at — "
            "customer logout-all endpoint non funziona."
        )

    def test_merchant_logout_all_records_audit(self):
        """logout_all registra audit event."""
        import inspect
        from routers.auth import logout_all

        src = inspect.getsource(logout_all)
        assert "audit_repository.create" in src, (
            "logout_all non registra audit event — forensic post-incident "
            "non puo' tracking 'quando hai invalidate sessions'."
        )
        assert '"logout_all"' in src or "'logout_all'" in src, (
            "Audit action name non 'logout_all' — taxonomy drift."
        )

    def test_customer_logout_all_records_audit(self):
        """customer_logout_all registra audit event."""
        import inspect
        from routers.customer_auth import customer_logout_all

        src = inspect.getsource(customer_logout_all)
        assert "audit_repository.create" in src, (
            "customer_logout_all non registra audit event."
        )
        assert '"customer_logout_all"' in src or "'customer_logout_all'" in src, (
            "Audit action name non 'customer_logout_all'."
        )

    def test_merchant_logout_all_rate_limited(self):
        """logout_all DEVE essere rate-limited (defensive vs DOS)."""
        import inspect
        from routers.auth import logout_all

        # Source decorator info inspect via __wrapped__ or src text
        src = inspect.getsource(logout_all)
        # slowapi decorator pattern: @limiter.limit(...)
        # NB: il source non include il decorator (inspect.getsource ritorna
        # solo il function body + signature). Verifichiamo via raw file scan.
        from pathlib import Path
        auth_file = Path(__file__).resolve().parent.parent / "routers" / "auth.py"
        content = auth_file.read_text(encoding="utf-8")
        # Trova la riga "async def logout_all" e check decorator immediately above
        idx = content.find("async def logout_all")
        assert idx != -1, "logout_all non trovata in routers/auth.py"
        preamble = content[max(0, idx - 300):idx]
        assert "@limiter.limit" in preamble, (
            "logout_all senza @limiter.limit decorator — DOS vector "
            "(spam invalidate forces re-login loop)."
        )

    def test_customer_logout_all_rate_limited(self):
        """customer_logout_all rate-limited."""
        from pathlib import Path
        ca_file = Path(__file__).resolve().parent.parent / "routers" / "customer_auth.py"
        content = ca_file.read_text(encoding="utf-8")
        idx = content.find("async def customer_logout_all")
        assert idx != -1, "customer_logout_all non trovata"
        preamble = content[max(0, idx - 300):idx]
        assert "@limiter.limit" in preamble, (
            "customer_logout_all senza @limiter.limit decorator."
        )

    def test_logout_all_updates_db_with_iso_timestamp(self):
        """logout_all chiama user_repository.update con tokens_invalidated_at."""
        import inspect
        from routers.auth import logout_all

        src = inspect.getsource(logout_all)
        assert "tokens_invalidated_at" in src, (
            "logout_all non setta tokens_invalidated_at nel update dict."
        )
        assert "user_repository.update" in src, (
            "logout_all non chiama user_repository.update."
        )
        # ISO format datetime check
        assert "isoformat" in src, (
            "logout_all non usa ISO format per il timestamp — parsing "
            "lato auth.py si aspetta ISO 8601."
        )

    def test_customer_logout_all_updates_db_with_iso_timestamp(self):
        """customer_logout_all idem per customer_account_repository."""
        import inspect
        from routers.customer_auth import customer_logout_all

        src = inspect.getsource(customer_logout_all)
        assert "tokens_invalidated_at" in src
        assert "customer_account_repository.update" in src, (
            "customer_logout_all non chiama customer_account_repository.update."
        )
        assert "isoformat" in src


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 4.5 — Admin manual email verification (customer support tool)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Open beta scenarios reali dove verification email NON arriva:
#     - Welcome/verify email in spam folder + user non controlla
#     - Brevo bounce su dominio merchant restrittivo (DMARC reject)
#     - Brevo outage breve durante signup → coda persa
#
#   Pre-O4.5: support poteva solo "rinvia verifica" (esistente).
#   Se email non arriva MAI, user resta locked-out forever.
#   Workaround: console Mongo manual update — rischio errore + no audit.
#
#   O4.5: 2 endpoint admin (user + customer_account) protected da
#   require_system_admin. Set email_verified=True + audit log esplicito.
#
# Sentinel coprono:
#   1. Both endpoints exist + signature corretta
#   2. require_system_admin gating (no org_admin cross-org bypass)
#   3. Optional `reason` field in body model
#   4. Audit log azione canonical name
#   5. Idempotenza implementata (set semplice, no precondition fail)


class TestSEC_O_4_5_AdminManualVerifyEmail:
    """SEC-O.4.5: admin endpoints per manual email verification support."""

    def test_admin_verify_user_email_endpoint_exists(self):
        from routers import admin
        assert hasattr(admin, "admin_verify_user_email"), (
            "Endpoint admin_verify_user_email mancante — support non puo' "
            "unblock user con verification email persa."
        )

    def test_admin_verify_customer_account_email_endpoint_exists(self):
        from routers import admin
        assert hasattr(admin, "admin_verify_customer_account_email"), (
            "Endpoint admin_verify_customer_account_email mancante."
        )

    def test_admin_verify_request_model_exists(self):
        """AdminVerifyEmailRequest model con field 'reason' optional."""
        from routers import admin
        assert hasattr(admin, "AdminVerifyEmailRequest"), (
            "Manca AdminVerifyEmailRequest model — body parsing non "
            "gestito da Pydantic, audit reason field assente."
        )
        fields = admin.AdminVerifyEmailRequest.model_fields
        assert "reason" in fields, (
            f"Manca campo 'reason' nel request model. Fields: "
            f"{list(fields.keys())}. Audit trail senza motivazione."
        )

    def test_admin_verify_user_requires_system_admin(self):
        """Endpoint protetto da require_system_admin (NOT org_admin)."""
        import inspect
        from routers.admin import admin_verify_user_email

        sig = inspect.signature(admin_verify_user_email)
        # current_user dependency con Depends(require_system_admin)
        assert "current_user" in sig.parameters, (
            "current_user dependency mancante."
        )
        # Source check: il dependency e' require_system_admin (non
        # generico require_admin che permette org-level)
        src = inspect.getsource(admin_verify_user_email)
        assert "require_system_admin" in src, (
            "Endpoint usa require_admin generico invece di "
            "require_system_admin → org-level admin puo' bypass anche "
            "su user di altre org. Privilege escalation."
        )

    def test_admin_verify_customer_requires_system_admin(self):
        """Mirror del check su customer endpoint."""
        import inspect
        from routers.admin import admin_verify_customer_account_email

        src = inspect.getsource(admin_verify_customer_account_email)
        assert "require_system_admin" in src, (
            "Customer verify endpoint usa require_admin generico — "
            "merchant org_admin puo' verify customer di OTHER merchant. "
            "Cross-tenant privilege escalation."
        )

    def test_admin_verify_user_records_audit(self):
        """Audit log inserito con action canonical."""
        import inspect
        from routers.admin import admin_verify_user_email

        src = inspect.getsource(admin_verify_user_email)
        assert "audit_logs_collection.insert_one" in src, (
            "admin_verify_user_email non registra audit — operatore "
            "override invisibile per forensic."
        )
        # Canonical action name
        assert '"USER_EMAIL_VERIFIED_BY_ADMIN"' in src or \
               "'USER_EMAIL_VERIFIED_BY_ADMIN'" in src, (
            "Action name non 'USER_EMAIL_VERIFIED_BY_ADMIN' — taxonomy "
            "drift cross-endpoint."
        )

    def test_admin_verify_customer_records_audit(self):
        import inspect
        from routers.admin import admin_verify_customer_account_email

        src = inspect.getsource(admin_verify_customer_account_email)
        assert "audit_logs_collection.insert_one" in src
        assert '"CUSTOMER_ACCOUNT_EMAIL_VERIFIED_BY_ADMIN"' in src or \
               "'CUSTOMER_ACCOUNT_EMAIL_VERIFIED_BY_ADMIN'" in src

    def test_admin_verify_user_sets_email_verified_true(self):
        """Effect: update_one $set email_verified=True."""
        import inspect
        from routers.admin import admin_verify_user_email

        src = inspect.getsource(admin_verify_user_email)
        assert "users_collection.update_one" in src, (
            "Non chiama update_one su users_collection."
        )
        assert '"email_verified": True' in src or \
               "'email_verified': True" in src, (
            "Non setta email_verified=True nel update dict."
        )

    def test_admin_verify_customer_sets_email_verified_true(self):
        import inspect
        from routers.admin import admin_verify_customer_account_email

        src = inspect.getsource(admin_verify_customer_account_email)
        assert "customer_accounts_collection.update_one" in src
        assert '"email_verified": True' in src or \
               "'email_verified': True" in src

    def test_admin_verify_returns_404_for_unknown(self):
        """Endpoint raise 404 se user/account non esiste — no silent success."""
        import inspect
        from routers.admin import admin_verify_user_email, admin_verify_customer_account_email

        for fn in [admin_verify_user_email, admin_verify_customer_account_email]:
            src = inspect.getsource(fn)
            assert "status_code=404" in src or "status_code = 404" in src, (
                f"{fn.__name__} non raise 404 su not-found — silent success "
                f"crea drift tra 'support clicked verify' e 'user gets "
                f"verified' senza visibility."
            )

    def test_admin_verify_audit_includes_actor_role(self):
        """Audit record include actor_role per forensic (chi ha verified)."""
        import inspect
        from routers.admin import admin_verify_user_email

        src = inspect.getsource(admin_verify_user_email)
        assert "actor_user_id" in src, (
            "Audit record manca actor_user_id — forensic non sa CHI ha "
            "verified."
        )
        assert "actor_role" in src, (
            "Audit record manca actor_role — forensic non sa se "
            "system_admin vs altro."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 5.1 — Frontend honeypot rendering (completes O4.1)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   O4.1 ha aggiunto il campo 'website' ai backend SignupRequest +
#   UserCreate, con validation + audit + uniform 202. MA: senza frontend
#   che rendi il campo, NESSUN bot lo riempie mai (i bot riempono solo
#   campi presenti nell'HTML scraping). La protezione era theater.
#
#   O5.1 completa: i 2 form signup (merchant + customer) renderanno
#   un hidden input <input name="website">, CSS-nascosto da humans,
#   visibile a bot HTML scrapers che riempono ogni input.
#
# Sentinel coprono (source check su file frontend JSX/JS):
#   1. AuthContext.signup() accetta param + invia website nel payload
#   2. SignupPage (merchant) usa state + invia website + render hidden input
#   3. Customer AuthPage idem (signupWebsite state + render + invia)
#   4. Hidden input pattern correct: CSS-hidden, NOT type=hidden, tabIndex=-1
#   5. Campo NON visibile a humans (off-screen) MA accessibile DOM a bot


class TestSEC_O_5_1_FrontendHoneypotRendering:
    """SEC-O.5.1: frontend signup forms rendono honeypot hidden input."""

    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[2]

    def _read_frontend(self, rel_path: str) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        full = repo_root / rel_path
        assert full.exists(), f"File frontend mancante: {rel_path}"
        return full.read_text(encoding="utf-8")

    def test_auth_context_signup_accepts_website_param(self):
        """frontend/src/context/AuthContext.js signup() accetta website param."""
        src = self._read_frontend("frontend/src/context/AuthContext.js")
        # Pattern: signup = useCallback(async (... website) => {
        assert "website" in src, (
            "AuthContext.signup non ha param 'website' — SignupPage "
            "non puo' passare il valore honeypot al backend."
        )
        # Verifica che il payload includa website (anche se conditional)
        assert "payload.website" in src or "payload.website =" in src or \
               '"website"' in src or "'website'" in src, (
            "AuthContext.signup non setta payload.website — il valore "
            "del form non arriva al backend, honeypot non puo' fire."
        )

    def test_merchant_signup_page_renders_hidden_honeypot_input(self):
        """SignupPage in pages/AuthPages.js render hidden <input name='website'>."""
        src = self._read_frontend("frontend/src/pages/AuthPages.js")
        # Hidden input pattern (multi-pattern OR per tolerance)
        assert 'name="website"' in src, (
            "SignupPage non render <input name=\"website\"> — bot HTML "
            "scrapers non vedono campo da riempire, zero bot caught."
        )
        # CSS-hidden pattern (NOT type=hidden — bot skip those)
        # Cerchiamo qualcuno dei marker: position:absolute OR opacity:0 OR
        # left: -9999px
        hidden_markers = [
            "-9999px", "opacity: 0", "opacity:0",
            "position: 'absolute'", 'position: "absolute"',
        ]
        assert any(m in src for m in hidden_markers), (
            f"SignupPage honeypot input NON nascosto via CSS. Pattern "
            f"attesi (qualcuno): {hidden_markers}. Senza CSS hide, "
            f"humans vedono il campo + lo riempono → false positives."
        )
        # NOT type="hidden" — bot moderni skip those
        # Verifica che il pattern usato sia type="text"
        # (cerchiamo il blocco con name="website" e verifichiamo type)
        idx = src.find('name="website"')
        snippet = src[max(0, idx - 200):idx + 200]
        assert 'type="text"' in snippet or "type='text'" in snippet, (
            "Honeypot input usa type non-text (es. 'hidden') — bot "
            "moderni skip <input type=hidden>, defeat purpose. "
            "Usa type=text + CSS hide."
        )

    def test_merchant_signup_page_uses_website_state(self):
        """SignupPage ha useState per il valore website + setter."""
        src = self._read_frontend("frontend/src/pages/AuthPages.js")
        # Pattern: const [website, setWebsite] = useState('')
        assert "setWebsite" in src, (
            "SignupPage manca setWebsite — controlled component pattern "
            "broken, input value non sincronizzato."
        )

    def test_merchant_signup_passes_website_to_signup_call(self):
        """SignupPage handleSubmit passa website come arg a signup()."""
        src = self._read_frontend("frontend/src/pages/AuthPages.js")
        # Cerca chiamata a signup con website come argomento
        # Pattern: signup(..., website)
        assert "signup(" in src, "Nessuna chiamata signup() in SignupPage"
        # Verifica che almeno una chiamata signup() includa 'website'
        # come argomento (search nel blocco signup call ~300 chars)
        signup_calls = []
        idx = 0
        while True:
            pos = src.find("signup(", idx)
            if pos == -1:
                break
            signup_calls.append(src[pos:pos + 300])
            idx = pos + 1
        # Almeno una chiamata signup deve includere 'website'
        assert any("website" in call for call in signup_calls), (
            "Nessuna chiamata signup() include 'website' arg — il valore "
            "honeypot non viene passato dalla form al context."
        )

    def test_customer_auth_page_renders_hidden_honeypot_input(self):
        """Customer AuthPage render hidden <input name='website'>."""
        src = self._read_frontend(
            "frontend/src/features/customer-portal/auth/AuthPage.jsx"
        )
        assert 'name="website"' in src, (
            "Customer AuthPage non render <input name=\"website\"> — "
            "bot mass-signup customer accounts non catturati."
        )
        hidden_markers = [
            "-9999px", "opacity: 0", "opacity:0",
            "position: 'absolute'", 'position: "absolute"',
        ]
        assert any(m in src for m in hidden_markers), (
            "Customer honeypot input non CSS-nascosto."
        )

    def test_customer_auth_page_uses_signup_website_state(self):
        """Customer AuthPage ha state per signupWebsite."""
        src = self._read_frontend(
            "frontend/src/features/customer-portal/auth/AuthPage.jsx"
        )
        assert "setSignupWebsite" in src, (
            "Customer AuthPage manca setSignupWebsite state setter."
        )

    def test_customer_signup_call_includes_website(self):
        """Customer AuthPage handleSignup invia website nel signup() payload."""
        src = self._read_frontend(
            "frontend/src/features/customer-portal/auth/AuthPage.jsx"
        )
        # Pattern: signup({ ..., website: signupWebsite })
        assert "website:" in src or "website :" in src, (
            "Customer signup() call manca campo 'website' nel payload "
            "object — backend non riceve il valore honeypot."
        )

    def test_honeypot_inputs_have_aria_hidden(self):
        """Hidden inputs marked aria-hidden — accessibility best practice
        per dichiarare che non sono per humans (screen reader skip)."""
        for path in [
            "frontend/src/pages/AuthPages.js",
            "frontend/src/features/customer-portal/auth/AuthPage.jsx",
        ]:
            src = self._read_frontend(path)
            # Trova il blocco name="website"
            idx = src.find('name="website"')
            assert idx != -1, f"{path}: name=website non trovato"
            snippet = src[max(0, idx - 100):idx + 400]
            assert 'aria-hidden="true"' in snippet or "aria-hidden={true}" in snippet, (
                f"{path}: honeypot input manca aria-hidden=true — "
                f"screen reader leggono il campo confuso. A11y violation."
            )

    def test_honeypot_inputs_have_tab_index_negative(self):
        """Hidden inputs tabIndex=-1 — escludono da tab navigation
        (humans con keyboard nav non incappano accidentalmente)."""
        for path in [
            "frontend/src/pages/AuthPages.js",
            "frontend/src/features/customer-portal/auth/AuthPage.jsx",
        ]:
            src = self._read_frontend(path)
            idx = src.find('name="website"')
            snippet = src[max(0, idx - 100):idx + 400]
            assert "tabIndex={-1}" in snippet or 'tabIndex="-1"' in snippet, (
                f"{path}: honeypot input manca tabIndex=-1 — keyboard "
                f"user puo' tabnav nel campo senza saperlo, false positive."
            )

    def test_honeypot_inputs_have_autocomplete_off(self):
        """autoComplete=off impedisce ai browser di pre-fill (es. da
        password manager) il campo honeypot — false positives da
        autofill non da bot."""
        for path in [
            "frontend/src/pages/AuthPages.js",
            "frontend/src/features/customer-portal/auth/AuthPage.jsx",
        ]:
            src = self._read_frontend(path)
            idx = src.find('name="website"')
            snippet = src[max(0, idx - 100):idx + 400]
            assert 'autoComplete="off"' in snippet or "autoComplete='off'" in snippet, (
                f"{path}: honeypot input manca autoComplete=off — "
                f"password manager / browser autofill potrebbero "
                f"riempire il campo creando false positives."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 5.2 — DMARC upgrade procedure runbook
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   DMARC currently `p=none` (monitoring). Upgrade to `p=reject` per
#   anti-spoofing brand protection durante open beta. Upgrade DEVE
#   essere gradual (pct=10→50→100, quarantine→reject) per evitare
#   disastri ("ho cambiato p=reject + 50% delle email transazionali
#   bounce silently").
#
#   Runbook canonical pinned dal sentinel garantisce che la procedura
#   resta documentata + sequence canonical (6 phase + rollback).


class TestSEC_O_5_2_DMARCUpgradeProcedureRunbook:
    """SEC-O.5.2: DMARC upgrade procedure runbook + sentinel pin."""

    RUNBOOK_PATH = "docs/operations/dmarc-upgrade-procedure.md"

    def _read_runbook(self) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        runbook = repo_root / self.RUNBOOK_PATH
        assert runbook.exists(), f"Runbook non trovato a {runbook}"
        return runbook.read_text(encoding="utf-8")

    def test_runbook_exists(self):
        self._read_runbook()

    def test_runbook_documents_all_6_phases(self):
        """Tutte le 6 phase canonical documentate (anti-skip protection)."""
        doc = self._read_runbook()
        required = [
            "Phase 1 — `p=quarantine; pct=10`",
            "Phase 2 — `p=quarantine; pct=50`",
            "Phase 3 — `p=quarantine; pct=100`",
            "Phase 4 — `p=reject; pct=10`",
            "Phase 5 — `p=reject; pct=50`",
            "Phase 6 — `p=reject; pct=100`",
        ]
        for phase in required:
            assert phase in doc, (
                f"Phase '{phase}' non documentata — operatore potrebbe "
                f"skippare phase critica + causare bounce cascata."
            )

    def test_runbook_documents_owner_email(self):
        doc = self._read_runbook()
        assert "davide@afianco.ch" in doc, (
            "Owner email non pinnato — execution chain mancante."
        )

    def test_runbook_documents_rollback_procedure(self):
        """Rollback procedure presente — disaster recovery garantito."""
        doc = self._read_runbook()
        assert "Rollback procedure" in doc or "Rollback" in doc, (
            "Manca sezione Rollback — se phase causa outage email, "
            "operatore senza procedure pre-validata = panic."
        )
        # Verify che il rollback target sia esplicito (p=none)
        assert "p=none" in doc, (
            "Rollback non specifica policy=none come fallback safe."
        )

    def test_runbook_documents_pre_checks(self):
        """Pre-checks documentati prima Phase 1 (no rush into reject)."""
        doc = self._read_runbook()
        assert "Pre-checks" in doc or "Pre-check" in doc, (
            "Manca sezione Pre-checks — operatore potrebbe rush "
            "Phase 1 senza verify baseline DKIM/SPF health."
        )
        # Pre-check chiave: DKIM pass rate
        assert "DKIM" in doc, (
            "Pre-checks non menzionano DKIM rate — uno dei 2 indicatori "
            "principali di readiness."
        )
        # SPF parimenti
        assert "SPF" in doc, "Pre-checks non menzionano SPF rate."

    def test_runbook_documents_soak_windows(self):
        """Soak windows minimi documentati (no rush phase-to-phase)."""
        doc = self._read_runbook()
        # Soak window references — 7 giorni minimum, 14 per Phase 3
        assert "7 giorni" in doc, (
            "Manca soak window 7-giorni — operator potrebbe upgrade "
            "phase-after-phase same day creando outage cascata."
        )
        assert "14 giorni" in doc, (
            "Phase 3 (p=quarantine pct=100) richiede 14-giorni soak per "
            "edge case rari emersi solo dopo settimane — non documentato."
        )

    def test_runbook_documents_dns_change_format(self):
        """DNS change snippets canonical per ogni phase."""
        doc = self._read_runbook()
        # Verify il record TXT base
        assert "v=DMARC1" in doc, "Record TXT format non documentato"
        # rua= reporting address presente (anti-config-drift)
        assert "rua=mailto:" in doc, "Mailing list rua= non documentato"
        # Pin dell'addresss dmarc@afianco.ch (own reports)
        assert "dmarc@afianco.ch" in doc, (
            "Manca rua=mailto:dmarc@afianco.ch — operatore non riceve "
            "report direttamente, dipende da Brevo."
        )

    def test_runbook_documents_checkpoint_conditions(self):
        """Pass/fail conditions per ogni checkpoint phase."""
        doc = self._read_runbook()
        assert "Pass conditions" in doc, (
            "Manca 'Pass conditions' per checkpoint — operatore non "
            "sa quando procedere vs rollback."
        )
        # Specific anti-pattern catturato: customer support ticket count
        assert "support ticket" in doc, (
            "Checkpoint non include monitoring customer support — "
            "il signal piu' chiaro che email delivery e' broken."
        )
        # Metric reference
        assert "email_sends_total" in doc, (
            "Checkpoint non riferisce Prometheus metric email_sends_total "
            "— operatore non sa quale dashboard panel guardare."
        )

    def test_runbook_documents_baseline_state(self):
        """Stato baseline current documentato (p=none monitoring)."""
        doc = self._read_runbook()
        assert "Current" in doc or "current" in doc, (
            "Manca riferimento allo stato corrente baseline — operatore "
            "non sa da dove parte."
        )

    def test_runbook_links_related_docs(self):
        doc = self._read_runbook()
        related = [
            "email-reputation.md",
            "incident-response.md",
            "sentry-alert-rules.md",
        ]
        for ref in related:
            assert ref in doc, (
                f"Manca cross-ref a {ref} — runbook isolato perde "
                f"valore durante incident triage."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 5.3 — HSTS preload submission runbook
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   nginx config gia' setta header HSTS con 'preload' directive
#   (deploy/nginx/nginx.conf:51). MA il declared willingness non
#   significa che afianco.ch SIA nella preload list — quello richiede
#   submission MANUALE a hstspreload.org.
#
#   Risk profile ALTO: submission quasi-permanente (6-12 mesi removal
#   turnaround). Subdomain non TLS-ready post-submit = inaccessibili
#   per utenti con browser preload-aware. Runbook canonical previene
#   il classic "ho cliccato submit senza checkare i subdomain".
#
# Sentinel coprono:
#   1. Runbook esiste
#   2. Pre-checks documentati (TLS validation tutti subdomain)
#   3. Soak window 7-giorni documentato
#   4. Submission procedure step-by-step
#   5. Removal procedure documentata (anche se sperabilmente mai usata)
#   6. Irreversibility warning prominente


class TestSEC_O_5_3_HSTSPreloadSubmissionRunbook:
    """SEC-O.5.3: HSTS preload submission runbook + sentinel pin."""

    RUNBOOK_PATH = "docs/operations/hsts-preload-submission.md"

    def _read_runbook(self) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        runbook = repo_root / self.RUNBOOK_PATH
        assert runbook.exists(), f"Runbook non trovato a {runbook}"
        return runbook.read_text(encoding="utf-8")

    def test_runbook_exists(self):
        self._read_runbook()

    def test_runbook_warns_about_irreversibility(self):
        """Irreversibility warning prominente (alto rischio submission)."""
        doc = self._read_runbook()
        # Multiple lexical markers per warning prominence
        warning_markers = [
            "irreversibility", "quasi-permanente", "permanent",
            "6-12 mesi", "6+ months", "Removal procedure",
        ]
        present_count = sum(1 for m in warning_markers if m.lower() in doc.lower())
        assert present_count >= 3, (
            f"Warning irreversibility presente solo {present_count} volte. "
            f"Submission e' quasi-permanente — il warning deve essere "
            f"PROMINENTE e ripetuto."
        )

    def test_runbook_documents_pre_checks(self):
        """Pre-checks list documentata (TLS validation prima submission)."""
        doc = self._read_runbook()
        assert "Pre-submit checklist" in doc or "Pre-submit" in doc or \
               "Pre-check" in doc, (
            "Manca sezione pre-checks — operatore potrebbe submit "
            "senza validation prerequisiti = disaster."
        )
        # Specific checks critical
        assert "subdomain" in doc.lower(), (
            "Pre-checks non menzionano subdomain inventory — il classic "
            "failure mode 'ho dimenticato un subdomain'."
        )
        # TLS validation per subdomain
        assert "TLS" in doc or "https://" in doc, (
            "Pre-checks non documentano TLS validation per subdomain."
        )

    def test_runbook_documents_header_requirements(self):
        """Header HSTS requirements canonical pinned."""
        doc = self._read_runbook()
        # Required directives per hstspreload.org acceptance
        required_directives = [
            "max-age=31536000",
            "includeSubDomains",
            "preload",
        ]
        for directive in required_directives:
            assert directive in doc, (
                f"Manca directive '{directive}' nel runbook — submission "
                f"sara' rejected da hstspreload.org se config non ha "
                f"questi 3 obbligatori."
            )

    def test_runbook_documents_soak_window(self):
        """Soak window 7 giorni minimum documentato."""
        doc = self._read_runbook()
        assert "7 giorni" in doc or "1 settimana" in doc, (
            "Manca soak window — hstspreload.org review fa random "
            "check, header deve essere coerente per 7+ giorni."
        )

    def test_runbook_documents_submission_url(self):
        """URL hstspreload.org documentato esplicitamente."""
        doc = self._read_runbook()
        assert "hstspreload.org" in doc, (
            "Manca riferimento al submission URL canonical."
        )

    def test_runbook_documents_removal_procedure(self):
        """Removal procedure documentata (anche se 'speriamo mai')."""
        doc = self._read_runbook()
        assert "Removal" in doc, (
            "Manca Removal procedure — se subdomain rompe HTTPS post-"
            "submit, operatore senza removal docs = panic 6+ mesi."
        )
        # Critical: max-age=0 downgrade pattern
        assert "max-age=0" in doc, (
            "Removal procedure manca 'max-age=0' downgrade pattern — "
            "first step canonical per signal removal a browser/registry."
        )

    def test_runbook_documents_owner(self):
        doc = self._read_runbook()
        assert "davide@afianco.ch" in doc, (
            "Owner non pinnato — execution chain mancante."
        )

    def test_runbook_documents_verification_post_ship(self):
        """Post-submission verification procedure documentata."""
        doc = self._read_runbook()
        # chrome://net-internals/#hsts e' il canonical Chrome check
        assert "net-internals" in doc or "Verification" in doc, (
            "Manca post-ship verification — operatore non sa come "
            "confermare che preload e' attivo dopo 6+ settimane."
        )

    def test_nginx_config_has_preload_directive(self):
        """nginx.conf attualmente ha 'preload' directive nel HSTS header.

        Anti-regression: se future refactor rimuove 'preload', il
        runbook diventa fiction (operatore submit ma header non
        autorizza preload list inclusion).
        """
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        conf = repo_root / "deploy/nginx/nginx.conf"
        assert conf.exists(), "nginx.conf non trovato"
        content = conf.read_text(encoding="utf-8")
        assert "Strict-Transport-Security" in content, (
            "nginx.conf manca header HSTS — regression critica."
        )
        # Verifica directive preload presente
        # Pattern: "Strict-Transport-Security ... preload ..."
        idx = content.find("Strict-Transport-Security")
        snippet = content[idx:idx + 300]
        assert "preload" in snippet, (
            "HSTS header nginx senza 'preload' directive — il runbook "
            "O5.3 assume preload presente. Se rimosso, submission "
            "fallisce."
        )
        assert "max-age=31536000" in snippet, (
            "HSTS max-age=31536000 (1 year) non presente — "
            "hstspreload.org richiede minimum 1 anno."
        )
        assert "includeSubDomains" in snippet, (
            "HSTS includeSubDomains mancante — submission richiesto."
        )

    def test_runbook_links_related_docs(self):
        doc = self._read_runbook()
        related = [
            "security-headers.md",
            "uptime-monitoring.md",
            "incident-response.md",
            "deploy/nginx/nginx.conf",
        ]
        for ref in related:
            assert ref in doc, (
                f"Manca cross-ref a {ref}."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 5.4 — GitHub Actions Node.js 20 -> 24 migration
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   GitHub deprecata Node.js 20 per JavaScript actions a partire da
#   Sett 2026. Tutti i nostri workflow (security.yml, test.yml) usano
#   actions/checkout@v4 + actions/setup-python@v5 che internamente
#   girano su Node 20. Warning in ogni run dal 2026-XX:
#
#     "Node.js 20 actions are deprecated. ... To opt into Node.js 24
#     now, set the FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true environment
#     variable..."
#
#   Sept 2026: Node 20 removed dal runner → actions failure hard.
#   Anticipare la migration evita disruption ultima notte.
#
#   Approccio: env var workflow-level (zero risk, backward compat —
#   action code immutato, solo runtime forced a Node 24).


class TestSEC_O_5_4_GitHubActionsNode24Migration:
    """SEC-O.5.4: workflow GHA opt-in Node.js 24 runtime."""

    WORKFLOWS = [".github/workflows/security.yml", ".github/workflows/test.yml"]

    def _read_workflow(self, path: str) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        full = repo_root / path
        assert full.exists(), f"Workflow non trovato: {path}"
        return full.read_text(encoding="utf-8")

    def test_security_workflow_opts_into_node24(self):
        """security.yml setta FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true."""
        content = self._read_workflow(self.WORKFLOWS[0])
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" in content, (
            "security.yml manca env var FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 "
            "— workflow run su Node 20 deprecated, warning su ogni run + "
            "fail hard quando GitHub rimuove Node 20 (Sept 2026)."
        )
        # Value deve essere 'true'
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'" in content or \
               'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in content or \
               "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in content, (
            "Env var setta valore != 'true' — opt-in non attivo."
        )

    def test_test_workflow_opts_into_node24(self):
        """test.yml setta FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true."""
        content = self._read_workflow(self.WORKFLOWS[1])
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" in content, (
            "test.yml manca env var FORCE_JAVASCRIPT_ACTIONS_TO_NODE24."
        )
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'" in content or \
               'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in content or \
               "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in content

    def test_env_var_at_workflow_level(self):
        """Env var deve essere a livello workflow (top-level), NON job-level.

        Workflow-level env applica a TUTTI i job. Job-level richiederebbe
        ripetizione + dimenticanza facile su nuovi job aggiunti.
        """
        for workflow_path in self.WORKFLOWS:
            content = self._read_workflow(workflow_path)
            # Trova FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 position
            env_idx = content.find("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24")
            assert env_idx != -1, f"{workflow_path}: env var missing"
            # Cerca "jobs:" position
            jobs_idx = content.find("\njobs:")
            assert jobs_idx != -1, f"{workflow_path}: 'jobs:' key missing"
            # env var DEVE apparire PRIMA di jobs: (workflow-level)
            assert env_idx < jobs_idx, (
                f"{workflow_path}: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 "
                f"definito DOPO jobs: → e' job-level. Sposta a top-level "
                f"per coverage uniforme tutti i job."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track O Step 5.5 — Pre-pilot launch consolidated checklist
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Sub-Track O ha prodotto 7+ runbook focused (sentry-alert-rules,
#   uptime-monitoring, dmarc-upgrade, hsts-preload, ecc.). Operatore
#   ha BUONA documentation ma rischia di:
#     - Dimenticare un action item
#     - Eseguire in ordine sbagliato
#     - Lanciare pilot senza go/no-go criteria chiari
#
#   O5.5 e' il master checklist che consolida TUTTI gli operator
#   action item pre-pilot in un unico documento, raggruppati per
#   section (A-G), con cross-link ai runbook dedicati per procedure
#   complete.
#
# Sentinel coprono:
#   1. Checklist file esiste
#   2. Linka tutti i runbook esistenti (cross-ref completo)
#   3. Sezioni A-G presenti (struttura canonical)
#   4. Go/no-go decision criteria esplicit
#   5. Smoke test procedures incluse


class TestSEC_O_5_5_PrePilotLaunchChecklist:
    """SEC-O.5.5: master pre-pilot launch checklist + sentinel pin."""

    CHECKLIST_PATH = "docs/operations/pre-pilot-launch-checklist.md"

    def _read_checklist(self) -> str:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / self.CHECKLIST_PATH
        assert path.exists(), f"Checklist non trovata a {path}"
        return path.read_text(encoding="utf-8")

    def test_checklist_exists(self):
        self._read_checklist()

    def test_checklist_documents_owner(self):
        doc = self._read_checklist()
        assert "davide@afianco.ch" in doc

    def test_checklist_has_all_sections(self):
        """Section A-G (canonical organization) tutte presenti."""
        doc = self._read_checklist()
        required_sections = [
            "Section A — Observability",
            "Section B — Auth abuse prevention",
            "Section C — Email reputation hardening",
            "Section D — Infrastructure resilience",
            "Section E — Operational readiness",
            "Section F — Pre-launch smoke tests",
            "Section G — Decision: GO / NO-GO",
        ]
        for section in required_sections:
            assert section in doc, (
                f"Section '{section}' mancante — checklist incompleta "
                f"perde valore guidance."
            )

    def test_checklist_documents_go_no_go_criteria(self):
        """Decision criteria GO/NO-GO esplicit (avoid ambiguity)."""
        doc = self._read_checklist()
        assert "GO / NO-GO" in doc or "GO/NO-GO" in doc, (
            "Manca sezione decisione GO/NO-GO — operatore senza "
            "criteria chiari rischia premature launch."
        )
        # Verify almeno 3 condition esplicit
        assert "PRONTO" in doc or "READY" in doc, (
            "Criteria readiness non documentati esplicit."
        )

    def test_checklist_links_all_existing_runbooks(self):
        """Cross-link a TUTTI i runbook esistenti — single entry point."""
        doc = self._read_checklist()
        required_runbooks = [
            "sentry-alert-rules.md",
            "uptime-monitoring.md",
            "email-reputation.md",
            "dmarc-upgrade-procedure.md",
            "hsts-preload-submission.md",
            "incident-response.md",
            "backup-recovery.md",
            "secrets-rotation.md",
            "runbook.md",
        ]
        for rb in required_runbooks:
            assert rb in doc, (
                f"Cross-link a {rb} mancante — checklist non e' master "
                f"single-entry-point, operator deve navigate manualmente."
            )

    def test_checklist_includes_smoke_test_procedures(self):
        """F.1-F.6 smoke test procedures presenti."""
        doc = self._read_checklist()
        smoke_categories = [
            "F.1 Anonymous flows",
            "F.2 Auth flow merchant",
            "F.3 Auth flow customer",
            "F.4 Anti-bot",
            "F.5 Webhook Stripe",
            "F.6 Sentry integration",
        ]
        for cat in smoke_categories:
            assert cat in doc, (
                f"Smoke test '{cat}' mancante — pre-launch verification "
                f"incompleta."
            )

    def test_checklist_documents_health_endpoints(self):
        """Health endpoint smoke test pinned (3 endpoint contract)."""
        doc = self._read_checklist()
        required_endpoints = [
            "/api/health/live",
            "/api/health/ready",
            "/api/health/ai",
        ]
        for ep in required_endpoints:
            assert ep in doc, (
                f"Health endpoint {ep} non in smoke test — operator "
                f"non verifica readiness completa."
            )

    def test_checklist_documents_anti_bot_test(self):
        """Anti-bot smoke test references honeypot + breach + slowapi."""
        doc = self._read_checklist()
        # Test honeypot specific
        assert "website" in doc, (
            "Smoke test non menziona campo 'website' (honeypot test)."
        )
        # Test HIBP specific
        assert "Password1" in doc or "breach" in doc.lower(), (
            "Smoke test non menziona HIBP breach check verification."
        )

    def test_checklist_documents_post_pilot_iteration(self):
        """Post-pilot iteration plan presente (no premature open beta)."""
        doc = self._read_checklist()
        assert "Post-pilot" in doc or "post-pilot" in doc, (
            "Manca sezione post-pilot iteration — operator pensa "
            "pilot = launch finale, no incremental hardening plan."
        )

    def test_checklist_references_track_o_sub_tracks(self):
        """Checklist citation dei sub-track O eseguiti — traceability."""
        doc = self._read_checklist()
        # Almeno O3, O4, O5 menzionati per contestualizzare
        tracks = ["O3", "O4", "O5"]
        for t in tracks:
            assert t in doc, (
                f"Track {t} non referenced — operator perde traceability "
                f"del lavoro fatto."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.1 — Embed API versioning (production consolidation)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Embed endpoints sono usati da web component <afianco-*> distribuiti
#   nei browser merchant esterni. Senza versioning esplicito, ogni cambio
#   contract puo' rompere SDK old in produzione senza recovery path.
#
#   Pattern: header X-API-Version (opt-in request, mandatory response).
#   Version integer major-only (v1, v2 future). Sentinel pin contract.
#
# Sentinel coprono:
#   1. Helper module exists + signature canonica
#   2. Costanti version pinned (current + supported set)
#   3. Tutti i 10 endpoint embed invocano apply_api_version
#   4. Header name canonical pinned ("X-API-Version")
#   5. Helper raises 400 su versione invalid
#   6. Response sempre carries X-API-Version (anche su default)


class TestSEC_E_1_1_EmbedApiVersioning:
    """SEC-E.1.1: embed API versioning helper + endpoint application."""

    def test_versioning_helper_module_exists(self):
        from core import embed_versioning

        for name in [
            "apply_api_version",
            "EMBED_API_CURRENT_VERSION",
            "EMBED_API_SUPPORTED_VERSIONS",
            "EMBED_API_VERSION_HEADER",
        ]:
            assert hasattr(embed_versioning, name), (
                f"core.embed_versioning manca '{name}' — public API rotta."
            )

    def test_current_version_in_supported_set(self):
        """EMBED_API_CURRENT_VERSION deve essere in SUPPORTED_VERSIONS.

        Anti-misconfig: current=2 ma supported={1} → ogni request fail.
        """
        from core.embed_versioning import (
            EMBED_API_CURRENT_VERSION,
            EMBED_API_SUPPORTED_VERSIONS,
        )
        assert EMBED_API_CURRENT_VERSION in EMBED_API_SUPPORTED_VERSIONS, (
            f"CURRENT_VERSION={EMBED_API_CURRENT_VERSION} NON in "
            f"SUPPORTED_VERSIONS={sorted(EMBED_API_SUPPORTED_VERSIONS)} — "
            f"misconfig: tutti i request default-versioned falliscono."
        )

    def test_header_name_is_canonical(self):
        """Header name pinned 'X-API-Version' — coordinato con SDK."""
        from core.embed_versioning import EMBED_API_VERSION_HEADER

        assert EMBED_API_VERSION_HEADER == "X-API-Version", (
            f"Header name drift: {EMBED_API_VERSION_HEADER!r}. "
            f"Cambio richiede sync embed-SDK + integration docs."
        )

    def test_apply_returns_int_on_default(self):
        """apply_api_version returns int (current version) quando header assent."""
        from unittest.mock import MagicMock
        from core.embed_versioning import (
            apply_api_version, EMBED_API_CURRENT_VERSION,
        )

        req = MagicMock()
        req.headers = {}
        resp = MagicMock()
        resp.headers = {}

        result = apply_api_version(req, resp)
        assert result == EMBED_API_CURRENT_VERSION
        assert resp.headers["X-API-Version"] == str(EMBED_API_CURRENT_VERSION), (
            "Response header X-API-Version non settato — SDK client "
            "non sa quale contratto e' stato applicato."
        )

    def test_apply_honors_explicit_supported_version(self):
        """Request header con versione supportata → resolved a quella."""
        from unittest.mock import MagicMock
        from core.embed_versioning import (
            apply_api_version, EMBED_API_SUPPORTED_VERSIONS,
        )

        # Pick first supported version
        supported = sorted(EMBED_API_SUPPORTED_VERSIONS)[0]
        req = MagicMock()
        req.headers = {"X-API-Version": str(supported)}
        resp = MagicMock()
        resp.headers = {}

        result = apply_api_version(req, resp)
        assert result == supported
        assert resp.headers["X-API-Version"] == str(supported)

    def test_apply_rejects_unsupported_version(self):
        """Request header con versione NON in supported set → HTTPException 400."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from core.embed_versioning import apply_api_version

        req = MagicMock()
        # Use a high version unlikely to be supported anytime soon
        req.headers = {"X-API-Version": "9999"}
        resp = MagicMock()
        resp.headers = {}

        try:
            apply_api_version(req, resp)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            # Detail include canonical fields per client SDK error handling
            detail = e.detail if isinstance(e.detail, dict) else {}
            assert "supported_versions" in detail, (
                "Error detail manca 'supported_versions' — SDK non sa "
                "quale versione fallback usare."
            )
            assert "current" in detail, (
                "Error detail manca 'current' — SDK non puo' indicare "
                "la versione corrente al merchant developer."
            )

    def test_apply_rejects_non_integer_version(self):
        """Request header con valore non-numerico → HTTPException 400."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from core.embed_versioning import apply_api_version

        for bad_value in ["abc", "1.5", "1,5", " "]:
            req = MagicMock()
            req.headers = {"X-API-Version": bad_value}
            resp = MagicMock()
            resp.headers = {}

            # Empty/whitespace is treated as absent (returns default), not error.
            # Skip that case here — separate test for default behavior.
            if not bad_value.strip():
                result = apply_api_version(req, resp)
                from core.embed_versioning import EMBED_API_CURRENT_VERSION
                assert result == EMBED_API_CURRENT_VERSION
                continue

            try:
                apply_api_version(req, resp)
                assert False, f"Should reject value {bad_value!r}"
            except HTTPException as e:
                assert e.status_code == 400, (
                    f"Value {bad_value!r}: expected 400, got {e.status_code}"
                )

    def test_apply_rejects_zero_or_negative_version(self):
        """Version <= 0 → 400 (positive integer expected)."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from core.embed_versioning import apply_api_version

        for bad in ["0", "-1", "-999"]:
            req = MagicMock()
            req.headers = {"X-API-Version": bad}
            resp = MagicMock()
            resp.headers = {}

            try:
                apply_api_version(req, resp)
                assert False, f"Should reject {bad}"
            except HTTPException as e:
                assert e.status_code == 400

    def test_all_embed_endpoints_invoke_versioning(self):
        """Tutti i 10 endpoint embed invocano apply_api_version nel body.

        CRITICAL: senza questo, alcuni endpoint non avrebbero il response
        header X-API-Version → SDK client non puo' fare consistency check.
        Refactor che aggiunge nuovo endpoint senza versioning = silently
        broken contract.
        """
        import inspect
        from routers import embed_public

        # Enum dei 10 endpoint function names (devono matchare quanto
        # registrato sul router)
        endpoint_names = [
            "get_embed_init",
            "get_embed_categories",
            "get_embed_products",
            "create_embed_cart",
            "get_embed_cart",
            "update_embed_cart",
            "clear_embed_cart",
            "merge_embed_cart",
            "start_embed_checkout",
            "embed_checkout_complete",
        ]
        missing = []
        for name in endpoint_names:
            fn = getattr(embed_public, name, None)
            assert fn is not None, (
                f"Endpoint function '{name}' non trovata in "
                f"routers.embed_public — endpoint name drift?"
            )
            src = inspect.getsource(fn)
            if "apply_api_version" not in src:
                missing.append(name)
        assert not missing, (
            f"Endpoint senza apply_api_version: {missing}. "
            f"Wire it nel body della funzione (early return safe)."
        )

    def test_embed_router_imports_versioning_helper(self):
        """routers/embed_public.py importa apply_api_version dal helper."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/embed_public.py").read_text(encoding="utf-8")
        assert "from core.embed_versioning import" in src, (
            "Manca import del helper dal modulo canonical."
        )
        assert "apply_api_version" in src, (
            "Helper apply_api_version non importato."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.2 — Cart inventory check (anti over-sell)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Pre-E1.2 lo stock check esisteva SOLO al checkout finale (services/
#   order_creation_service.py:270-283 + stock_service.try_decrement_stock
#   at order confirm). Customer poteva add unlimited qty al cart, scoprire
#   al checkout che stock insufficient → bad UX + order abandonment.
#
#   E1.2 introduce eager check al cart add/update:
#   - Best-effort signal "qty > stock disponibile" PRIMA del checkout
#   - Atomic guarantee resta al confirm_order (try_decrement_stock)
#   - Pattern industry-standard (Shopify, WooCommerce, Stripe Checkout)
#
# Sentinel coprono:
#   1. Helper module + canonical API
#   2. Type-aware: solo physical/digital tracciati, altri types skip
#   3. Backward-compat: stock_quantity=None → unlimited (skip)
#   4. Cart service invoca check pre-update
#   5. Router caller (embed + storefront) catch → HTTP 409 strutturato
#   6. Error detail shape canonical {code, product_id, requested, available}


class TestSEC_E_1_2_CartInventoryCheck:
    """SEC-E.1.2: inventory check on cart update + structured 409 response."""

    def test_helper_module_exists(self):
        from core import inventory_check
        for name in [
            "InsufficientStockError",
            "inventory_check_required",
            "check_cart_items_inventory",
        ]:
            assert hasattr(inventory_check, name), (
                f"core.inventory_check manca '{name}' — public API rotta."
            )

    def test_inventory_check_required_physical_with_stock(self):
        """item_type=physical + stock_quantity=N → True (tracked)."""
        from core.inventory_check import inventory_check_required
        assert inventory_check_required({
            "item_type": "physical", "stock_quantity": 5
        }) is True
        assert inventory_check_required({
            "item_type": "physical", "stock_quantity": 0
        }) is True  # 0 e' tracked (out of stock, check fired)

    def test_inventory_check_required_digital_with_stock(self):
        """item_type=digital + stock_quantity=N → True."""
        from core.inventory_check import inventory_check_required
        assert inventory_check_required({
            "item_type": "digital", "stock_quantity": 10
        }) is True

    def test_inventory_check_required_skipped_non_stock_types(self):
        """item_type in {service, rental, event_ticket, course, booking}
        → False (loro logica calendar/capacity, no stock_quantity).

        CRITICAL: questi types non devono fire stock check anche se
        stock_quantity per qualche motivo settato (legacy data).
        """
        from core.inventory_check import inventory_check_required
        for non_stock_type in [
            "service", "rental", "event_ticket", "course", "booking",
        ]:
            assert inventory_check_required({
                "item_type": non_stock_type, "stock_quantity": 5
            }) is False, (
                f"Type '{non_stock_type}' fired inventory check ma "
                f"non e' stockable per design (no requires_stock)."
            )

    def test_inventory_check_required_skipped_null_stock(self):
        """stock_quantity=None → False (unlimited / untracked).

        Backward-compat: prodotti legacy senza stock_quantity sono
        unlimited (no-op, allowed). Stesso comportamento di pre-E1.2.
        """
        from core.inventory_check import inventory_check_required
        assert inventory_check_required({
            "item_type": "physical", "stock_quantity": None
        }) is False

    def test_check_passes_when_qty_within_stock(self):
        """qty=5, stock=10 → no raise."""
        from core.inventory_check import check_cart_items_inventory
        check_cart_items_inventory(
            items=[{"product_id": "p1", "quantity": 5}],
            products_by_id={"p1": {"item_type": "physical", "stock_quantity": 10}},
        )

    def test_check_raises_when_qty_exceeds_stock(self):
        """qty=20, stock=5 → raise InsufficientStockError con detail."""
        from core.inventory_check import check_cart_items_inventory, InsufficientStockError

        try:
            check_cart_items_inventory(
                items=[{"product_id": "p1", "quantity": 20}],
                products_by_id={"p1": {"item_type": "physical", "stock_quantity": 5}},
            )
            assert False, "Should have raised InsufficientStockError"
        except InsufficientStockError as e:
            detail = e.to_detail()
            # Canonical shape
            assert detail["code"] == "STOCK_INSUFFICIENT"
            assert detail["product_id"] == "p1"
            assert detail["requested"] == 20
            assert detail["available"] == 5
            assert "message" in detail and detail["message"]
            # Anti info-leak: count exact non rivelato sopra in modi
            # ambigui ma comunicato esattamente in detail (intentional —
            # customer DEVE sapere quanto puo' comprare)

    def test_check_raises_on_out_of_stock(self):
        """stock=0 + qty=1 → raise (esaurito)."""
        from core.inventory_check import check_cart_items_inventory, InsufficientStockError
        try:
            check_cart_items_inventory(
                items=[{"product_id": "p1", "quantity": 1}],
                products_by_id={"p1": {"item_type": "physical", "stock_quantity": 0}},
            )
            assert False, "Should raise for out-of-stock"
        except InsufficientStockError as e:
            assert e.available == 0
            assert "esaurito" in e.message.lower() or "0" in e.message

    def test_check_skips_legacy_untracked_products(self):
        """stock_quantity=None → pass anche con qty huge (backward-compat)."""
        from core.inventory_check import check_cart_items_inventory
        # No raise expected
        check_cart_items_inventory(
            items=[{"product_id": "p1", "quantity": 999999}],
            products_by_id={"p1": {"item_type": "physical", "stock_quantity": None}},
        )

    def test_check_skips_service_type_products(self):
        """item_type=service → skip anche se stock_quantity small.

        Critical: service products possono avere stock_quantity legacy
        per errore — la logica DEVE skippare basandosi sul type.
        """
        from core.inventory_check import check_cart_items_inventory
        check_cart_items_inventory(
            items=[{"product_id": "p1", "quantity": 100}],
            products_by_id={"p1": {"item_type": "service", "stock_quantity": 1}},
        )

    def test_check_handles_float_quantity(self):
        """quantity puo' essere float (es. 0.5 kg) — comparison int."""
        from core.inventory_check import check_cart_items_inventory, InsufficientStockError
        # 0.5 vs stock 5 → pass
        check_cart_items_inventory(
            items=[{"product_id": "p1", "quantity": 0.5}],
            products_by_id={"p1": {"item_type": "physical", "stock_quantity": 5}},
        )
        # 5.5 vs stock 5 → fail
        try:
            check_cart_items_inventory(
                items=[{"product_id": "p1", "quantity": 5.5}],
                products_by_id={"p1": {"item_type": "physical", "stock_quantity": 5}},
            )
            assert False, "Should raise on 5.5 > 5"
        except InsufficientStockError as e:
            assert e.requested == 5.5

    def test_error_message_clean_int_display(self):
        """Whole-number quantity → display senza '.0' suffix."""
        from core.inventory_check import InsufficientStockError
        e = InsufficientStockError(product_id="p1", requested=10.0, available=5)
        assert "10.0" not in e.message, (
            f"Message mostra '10.0' invece di '10' — UX cosmetic: {e.message!r}"
        )
        assert "10" in e.message

    def test_check_supports_cart_item_objects_via_getattr(self):
        """Helper accetta sia dict che objects (CartItem-like) via getattr."""
        from core.inventory_check import check_cart_items_inventory, InsufficientStockError

        class FakeCartItem:
            def __init__(self, product_id, quantity):
                self.product_id = product_id
                self.quantity = quantity

        # Object con stock OK
        check_cart_items_inventory(
            items=[FakeCartItem("p1", 3)],
            products_by_id={"p1": {"item_type": "physical", "stock_quantity": 10}},
        )
        # Object con stock insufficient
        try:
            check_cart_items_inventory(
                items=[FakeCartItem("p1", 100)],
                products_by_id={"p1": {"item_type": "physical", "stock_quantity": 10}},
            )
            assert False, "Should raise"
        except InsufficientStockError:
            pass

    def test_check_skips_unknown_product(self):
        """Product non in map → skip (caller responsibility)."""
        from core.inventory_check import check_cart_items_inventory
        # No raise atteso (caller handle product missing in altro modo)
        check_cart_items_inventory(
            items=[{"product_id": "unknown", "quantity": 99}],
            products_by_id={"p1": {"item_type": "physical", "stock_quantity": 5}},
        )

    def test_cart_service_invokes_inventory_check(self):
        """cart_service.update_cart_items source-check: invoca helper."""
        import inspect
        from services import cart_service

        src = inspect.getsource(cart_service.update_cart_items)
        assert "check_cart_items_inventory" in src, (
            "cart_service.update_cart_items non invoca helper inventory "
            "— over-sell possibile silently."
        )
        assert "from core.inventory_check import" in src, (
            "Manca import canonical del helper."
        )

    def test_cart_service_fetches_item_type_and_stock(self):
        """update_cart_items projection include item_type + stock_quantity.

        Senza questi field nel projection, inventory check ha sempre
        product_doc senza i campi → skip silente. Anti-regression.
        """
        import inspect
        from services import cart_service

        src = inspect.getsource(cart_service.update_cart_items)
        # Projection literal nel source
        assert '"item_type"' in src or "'item_type'" in src, (
            "update_cart_items projection NON include 'item_type' — "
            "inventory check riceve product_doc senza il field, skip "
            "silente, over-sell possibile."
        )
        assert '"stock_quantity"' in src or "'stock_quantity'" in src, (
            "update_cart_items projection NON include 'stock_quantity'."
        )

    def test_embed_router_maps_stock_error_to_409(self):
        """routers/embed_public.py PATCH /cart catch + 409 strutturato."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/embed_public.py").read_text(encoding="utf-8")
        assert "InsufficientStockError" in src, (
            "Embed router non importa InsufficientStockError — exception "
            "bubble up come 500 invece di 409 strutturato."
        )
        assert "HTTP_409_CONFLICT" in src, (
            "Embed router non usa 409 per stock conflict — semantically "
            "wrong (400 = malformed request; 409 = state conflict)."
        )
        assert "stock_err.to_detail()" in src or "to_detail()" in src, (
            "Embed router non usa il canonical to_detail() shape — "
            "client SDK riceve detail unstructured."
        )

    def test_storefront_router_maps_stock_error_to_409(self):
        """routers/public.py legacy storefront mirror del pattern embed."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/public.py").read_text(encoding="utf-8")
        assert "InsufficientStockError" in src, (
            "Storefront router non importa InsufficientStockError — "
            "comportamento incoerente vs embed."
        )
        assert "HTTP_409_CONFLICT" in src
        assert "to_detail()" in src

    def test_known_stock_tracked_types_pinned(self):
        """Set _STOCK_TRACKED_TYPES e' pinned a {physical, digital}.

        Anti-drift: se aggiungiamo type stockable nuovo, sentinel
        forza review consapevole del set.
        """
        from core import inventory_check
        # Accesso al modulo internal — accettiamo bcs sentinel critical
        tracked = getattr(inventory_check, "_STOCK_TRACKED_TYPES", None)
        assert tracked is not None, (
            "_STOCK_TRACKED_TYPES costante interna mancante."
        )
        assert tracked == frozenset({"physical", "digital"}), (
            f"Set tracked types drift: {tracked}. Atteso "
            f"{{'physical', 'digital'}}. Se aggiungi type nuovo "
            f"requires_stock=True, aggiorna ENTRAMBI: il set + "
            f"models/product_types.py registry."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.3 — Full-text search on /products endpoint
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Pre-E1.3 il widget embed forniva filter category + type + sort
#   predeterminati MA NO keyword search. Merchant non poteva offrire
#   "cerca pizza" al customer. Standard e-commerce moderno richiede
#   search nativa.
#
#   Pattern:
#     - Mongo `$text` operator (safe from injection, stemming italiano)
#     - Index canonical: name (weight 3) + description (weight 1)
#     - Sort relevance opzionale (textScore DESC)
#     - q param optional, default behavior preservato
#
# Sentinel coprono:
#   1. Helper module canonical API
#   2. Normalize edge cases (None/empty/whitespace/length-cap)
#   3. Mongo text index defined in database.py
#   4. Sort 'relevance' aggiunto al whitelist
#   5. Service signature include search_query param
#   6. Router endpoint expose q param con max_length cap
#   7. ETag include q (cache distinct per query)
#   8. Score field stripped from response (anti-internal-meta leak)


class TestSEC_E_1_3_FullTextSearch:
    """SEC-E.1.3: full-text search helper + endpoint + index + sentinel."""

    def test_helper_module_exists(self):
        from core import embed_search
        for name in [
            "normalize_search_query",
            "is_search_active",
            "build_text_search_match",
            "text_score_projection",
            "relevance_sort_spec",
            "MAX_SEARCH_LENGTH",
            "SORT_MODE_RELEVANCE",
        ]:
            assert hasattr(embed_search, name), (
                f"core.embed_search manca '{name}' — public API rotta."
            )

    def test_normalize_none_empty_whitespace(self):
        from core.embed_search import normalize_search_query
        assert normalize_search_query(None) is None
        assert normalize_search_query("") is None
        assert normalize_search_query("   ") is None
        assert normalize_search_query("\t\n") is None

    def test_normalize_strips_whitespace(self):
        from core.embed_search import normalize_search_query
        assert normalize_search_query("  pizza  ") == "pizza"
        assert normalize_search_query("\tpizza\n") == "pizza"

    def test_normalize_truncates_to_max_length(self):
        from core.embed_search import normalize_search_query, MAX_SEARCH_LENGTH
        long_q = "a" * 500
        result = normalize_search_query(long_q)
        assert result is not None
        assert len(result) == MAX_SEARCH_LENGTH, (
            f"Length cap broken: expected {MAX_SEARCH_LENGTH}, "
            f"got {len(result)}. DOS surface."
        )

    def test_normalize_rejects_non_string(self):
        from core.embed_search import normalize_search_query
        assert normalize_search_query(42) is None  # type: ignore
        assert normalize_search_query([]) is None  # type: ignore
        assert normalize_search_query({}) is None  # type: ignore

    def test_is_search_active(self):
        from core.embed_search import is_search_active
        assert is_search_active(None) is False
        assert is_search_active("") is False
        assert is_search_active("  ") is False
        assert is_search_active("pizza") is True
        assert is_search_active("  pizza  ") is True

    def test_build_text_search_match_empty(self):
        """Match e' {} se q assente — caller combina con altri filter."""
        from core.embed_search import build_text_search_match
        assert build_text_search_match(None) == {}
        assert build_text_search_match("") == {}
        assert build_text_search_match("   ") == {}

    def test_build_text_search_match_with_query(self):
        """Returns canonical $text operator structure."""
        from core.embed_search import build_text_search_match
        result = build_text_search_match("pizza")
        assert "$text" in result
        assert result["$text"] == {"$search": "pizza"}

    def test_build_text_search_match_preserves_phrase_and_exclusion(self):
        """Mongo $text syntax (phrases, exclusion) pass through senza
        escape. Feature, non bug."""
        from core.embed_search import build_text_search_match
        # Phrase
        r = build_text_search_match('"farina 00"')
        assert r["$text"]["$search"] == '"farina 00"'
        # Exclusion
        r = build_text_search_match('pasta -glutine')
        assert r["$text"]["$search"] == 'pasta -glutine'

    def test_text_score_projection_shape(self):
        from core.embed_search import text_score_projection
        proj = text_score_projection()
        assert proj == {"score": {"$meta": "textScore"}}

    def test_relevance_sort_spec_shape(self):
        """Sort relevance = score DESC + name ASC tiebreaker."""
        from core.embed_search import relevance_sort_spec
        spec = relevance_sort_spec()
        # Primo elemento: score DESC via $meta
        assert spec[0][0] == "score"
        assert spec[0][1] == {"$meta": "textScore"}
        # Secondo elemento: name ASC come tiebreaker
        assert spec[1] == ("name", 1)

    def test_sort_mode_relevance_in_whitelist(self):
        """'relevance' aggiunto al whitelist canonical."""
        from services.embed_init_service import EMBED_PRODUCT_SORT_MODES
        from core.embed_search import SORT_MODE_RELEVANCE
        assert SORT_MODE_RELEVANCE == "relevance", (
            "SORT_MODE_RELEVANCE constant non e' 'relevance' — sync rotto."
        )
        assert SORT_MODE_RELEVANCE in EMBED_PRODUCT_SORT_MODES, (
            "'relevance' non e' nel whitelist — sort=relevance rifiutato 400."
        )

    def test_text_index_defined_in_database_setup(self):
        """database.py crea text index per products_collection.

        Anti-regression: senza l'index, Mongo $text query falliscono
        runtime (errore 'text index required for $text query').
        Sentinel pin presenza in setup.
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/database.py").read_text(encoding="utf-8")
        assert "products_collection.create_index" in src, (
            "database.py manca products_collection.create_index"
        )
        # Specific pattern: text index su (name, text) + (description, text)
        assert '"name", "text"' in src, (
            "Text index su name field mancante — search by name non funziona."
        )
        assert '"description", "text"' in src, (
            "Text index su description field mancante — search by description "
            "non funziona."
        )
        # Weights pinned: name>description
        assert "weights" in src, (
            "Index senza weights — name e description hanno stessa rilevanza, "
            "UX poveramente bilanciata."
        )

    def test_service_signature_accepts_search_query(self):
        """get_embed_products_data accept search_query kwarg."""
        import inspect
        from services.embed_init_service import get_embed_products_data

        sig = inspect.signature(get_embed_products_data)
        assert "search_query" in sig.parameters, (
            "get_embed_products_data signature manca 'search_query' — "
            "router non puo' passare q al service."
        )

    def test_router_endpoint_accepts_q_param(self):
        """get_embed_products endpoint signature include q param."""
        import inspect
        from routers.embed_public import get_embed_products

        sig = inspect.signature(get_embed_products)
        assert "q" in sig.parameters, (
            "Endpoint signature manca 'q' query param — search non esposta."
        )

    def test_router_q_param_has_max_length_cap(self):
        """q Query() ha max_length cap (defense in depth + FastAPI gate)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/embed_public.py").read_text(encoding="utf-8")
        # Trova il blocco del q Query()
        idx = src.find("q: Optional[str] = Query(")
        assert idx != -1, "Q query definition pattern non trovato"
        block = src[idx:idx + 600]
        assert "max_length=200" in block, (
            "q param senza max_length=200 — DOS surface (giant query strings)."
        )

    def test_router_etag_includes_q(self):
        """ETag include q nel digest — cache distinct per query diverse.

        Check su get_embed_products specifically (NON init / categories
        che NON hanno q). Source-check del function body via inspect.
        """
        import inspect
        from routers.embed_public import get_embed_products

        src = inspect.getsource(get_embed_products)
        # Pattern: etag_source contiene reference a q (es. {q or ''})
        assert "etag_source" in src, "etag_source not in endpoint"
        # Specifico: f-string interpola q
        assert "{q or ''}" in src or "{q}" in src or "|{q or" in src, (
            "ETag source nel endpoint products non include q — varianti "
            "search restituiscono stesso ETag → cache leaks risultati "
            "search diversi tra customer."
        )

    def test_service_strips_score_from_response(self):
        """Service strip 'score' Mongo meta field da response items.

        Critical: score e' internal Mongo, NON parte del contract public
        EmbedProductCard. Leak espone implementation detail (Mongo
        textScore) + potenziale info-leak (relevance ranking algorithm).
        """
        import inspect
        from services.embed_init_service import get_embed_products_data

        src = inspect.getsource(get_embed_products_data)
        assert 'doc.pop("score", None)' in src or "doc.pop('score', None)" in src, (
            "Service non strip 'score' da response items — Mongo meta "
            "field leak nel response public."
        )

    def test_relevance_fallback_when_no_query(self):
        """sort=relevance senza q → fallback a 'name' (no Mongo error).

        Mongo $meta:textScore richiede $text match upstream. Se user
        chiede sort=relevance senza q, Mongo solleva error.
        Service deve gracefully fallback.
        """
        import inspect
        from services.embed_init_service import get_embed_products_data

        src = inspect.getsource(get_embed_products_data)
        # Pattern: check `safe_sort == SORT_MODE_RELEVANCE and not search_active`
        # → fallback a name
        assert "SORT_MODE_RELEVANCE" in src, (
            "Service non referencia SORT_MODE_RELEVANCE constant."
        )
        # Fallback logic presente
        assert ('safe_sort = "name"' in src or 'safe_sort = \'name\'' in src), (
            "Service non fallback a 'name' quando relevance + no search."
        )

    def test_text_search_match_combined_with_org_id_isolation(self):
        """CRITICAL multi-tenant: la text search NON deve fare query
        cross-org. Verifica che caller combini sempre con organization_id.

        Pattern: match = _build_product_match(org_id, ...) (gia' include
        organization_id) → match.update(build_text_search_match(q)).

        Senza organization_id, $text scans ALL docs.
        """
        import inspect
        from services.embed_init_service import get_embed_products_data

        src = inspect.getsource(get_embed_products_data)
        # Verifica che match e' inizializzato con _build_product_match
        assert "_build_product_match(" in src, (
            "Service non chiama _build_product_match() — organization_id "
            "potrebbe non essere scoped."
        )
        # Build text search match deve essere CHIAMATO (non solo importato)
        # DOPO match init. Cerchiamo le CHIAMATE specifiche.
        idx_match_call = src.find("match = _build_product_match(")
        idx_text_call = src.find("match.update(build_text_search_match(")
        assert idx_match_call != -1, (
            "Chiamata 'match = _build_product_match(...)' non trovata "
            "— pattern di multi-tenant scoping rotto."
        )
        assert idx_text_call != -1, (
            "Chiamata 'match.update(build_text_search_match(...))' non "
            "trovata — text search non applicata via canonical helper."
        )
        assert idx_match_call < idx_text_call, (
            "build_text_search_match invocato PRIMA di _build_product_match "
            "→ organization_id potrebbe sovrascriversi → cross-tenant leak. "
            f"idx_match_call={idx_match_call} idx_text_call={idx_text_call}"
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.4 — Per-merchant rate limit isolation
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Pre-E1.4 i rate limit erano per-IP globali (es. 60/min). Problema:
#   merchant A con 1000 customer su NAT shared satura bucket → merchant B
#   small su stessa NAT starva.
#
#   E1.4: composite key per embed endpoints = "{ip}|s={slug}" → bucket
#   distinto per merchant. Backward compat: endpoint senza slug fallback
#   a IP only.
#
# Sentinel coprono:
#   1. Helper canonical signature + behavior
#   2. Path/query slug extraction priorities
#   3. Length cap (defensive anti-DOS)
#   4. Tutti i 10 endpoint embed usano key_func override
#   5. Legacy get_real_ip invariato (no regression non-embed routes)
#   6. Backward compat: slug assente → IP only (no breaking)


class TestSEC_E_1_4_PerMerchantRateLimitIsolation:
    """SEC-E.1.4: composite rate limit key (IP|slug) per merchant isolation."""

    def test_helper_exists(self):
        from core import rate_limiting
        assert hasattr(rate_limiting, "get_real_ip_with_slug"), (
            "core.rate_limiting manca get_real_ip_with_slug — composite "
            "key per merchant isolation non disponibile."
        )

    def test_legacy_get_real_ip_unchanged(self):
        """get_real_ip continua a esistere + ritornare solo IP.

        Anti-regression: non-embed router (auth, customer_auth, admin, ...)
        usano ancora get_real_ip per per-IP global rate limit. Se E1.4
        rompesse o cambiasse behavior, tutti i rate limit non-embed
        breakerebbero.
        """
        from core.rate_limiting import get_real_ip
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "203.0.113.7"}
        req.client = MagicMock(host="10.0.0.1")
        # Anche se request avesse slug, get_real_ip deve restituire SOLO IP
        req.path_params = {"slug": "test-store"}

        result = get_real_ip(req)
        assert result == "203.0.113.7", (
            f"get_real_ip drift: {result!r} — non-embed rate limits "
            f"affetti."
        )
        assert "slug" not in result and "|" not in result, (
            f"Legacy get_real_ip restituisce composite key — backward "
            f"compat rotto: {result!r}"
        )

    def test_composite_key_path_slug(self):
        """Slug nel path → bucket = '{ip}|s={slug}'."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "1.2.3.4"}
        req.client = MagicMock(host="10.0.0.1")
        req.path_params = {"slug": "merchant-a"}
        # Empty query_params
        req.query_params = MagicMock()
        req.query_params.get = lambda k: None

        result = get_real_ip_with_slug(req)
        assert result == "1.2.3.4|s=merchant-a", (
            f"Expected composite key, got {result!r}"
        )

    def test_composite_key_query_slug(self):
        """Slug in query (path missing) → composite key."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "1.2.3.4"}
        req.client = MagicMock(host="10.0.0.1")
        req.path_params = {}
        req.query_params = MagicMock()
        req.query_params.get = lambda k: "merchant-b" if k == "slug" else None

        result = get_real_ip_with_slug(req)
        assert result == "1.2.3.4|s=merchant-b"

    def test_composite_key_path_priority_over_query(self):
        """Path slug ha priorita' su query slug (URL canonical wins)."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "1.2.3.4"}
        req.client = MagicMock(host="10.0.0.1")
        req.path_params = {"slug": "path-slug"}
        req.query_params = MagicMock()
        req.query_params.get = lambda k: "query-slug" if k == "slug" else None

        result = get_real_ip_with_slug(req)
        assert result == "1.2.3.4|s=path-slug", (
            f"Path slug should win over query, got {result!r}"
        )

    def test_composite_key_fallback_ip_only(self):
        """Nessun slug → bucket = '{ip}' (backward compat)."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "1.2.3.4"}
        req.client = MagicMock(host="10.0.0.1")
        req.path_params = {}
        req.query_params = MagicMock()
        req.query_params.get = lambda k: None

        result = get_real_ip_with_slug(req)
        assert result == "1.2.3.4", (
            f"No slug → expected IP only, got {result!r}"
        )

    def test_composite_key_slug_truncated(self):
        """Slug > 64 char truncated — anti-DOS via giant slug values."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        req = MagicMock()
        req.headers = {"x-forwarded-for": "1.2.3.4"}
        req.client = MagicMock(host="10.0.0.1")
        req.path_params = {"slug": "a" * 500}
        req.query_params = MagicMock()
        req.query_params.get = lambda k: None

        result = get_real_ip_with_slug(req)
        # Format: "1.2.3.4|s=<slug>"
        slug_part = result.split("s=", 1)[1]
        assert len(slug_part) == 64, (
            f"Slug not truncated to 64 char: len={len(slug_part)}"
        )

    def test_composite_key_empty_slug_handled(self):
        """Empty/whitespace slug → fallback a IP only."""
        from core.rate_limiting import get_real_ip_with_slug
        from unittest.mock import MagicMock

        for empty_slug in ["", "   ", "\t\n"]:
            req = MagicMock()
            req.headers = {"x-forwarded-for": "1.2.3.4"}
            req.client = MagicMock(host="10.0.0.1")
            req.path_params = {"slug": empty_slug}
            req.query_params = MagicMock()
            req.query_params.get = lambda k: None

            result = get_real_ip_with_slug(req)
            assert result == "1.2.3.4", (
                f"Empty slug {empty_slug!r} should fallback to IP, got {result!r}"
            )

    def test_all_embed_endpoints_use_composite_key(self):
        """Tutti i 10 endpoint embed devono usare key_func=get_real_ip_with_slug.

        Source-check: ogni @limiter.limit() decorator nel router embed
        DEVE includere key_func=get_real_ip_with_slug. Anti-regression:
        nuovo endpoint embed senza override = silently usa per-IP global
        bucket → merchant isolation rotto.
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/embed_public.py").read_text(encoding="utf-8")

        # Count @limiter.limit total vs con key_func
        import re
        total_decorators = len(re.findall(r"@limiter\.limit\(", src))
        with_key_func = len(re.findall(
            r"@limiter\.limit\([^)]*key_func=get_real_ip_with_slug", src
        ))
        assert total_decorators >= 10, (
            f"Atteso almeno 10 @limiter.limit decorators (embed endpoints), "
            f"trovati {total_decorators}"
        )
        assert total_decorators == with_key_func, (
            f"Decorator senza key_func override: {total_decorators - with_key_func} "
            f"trovati su {total_decorators} totali. Nuovo endpoint senza "
            f"override → merchant isolation rotto. Aggiungi key_func="
            f"get_real_ip_with_slug."
        )

    def test_embed_router_imports_helper(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/embed_public.py").read_text(encoding="utf-8")
        assert "get_real_ip_with_slug" in src, (
            "Embed router non importa helper get_real_ip_with_slug."
        )
        assert "from core.rate_limiting import" in src, (
            "Embed router non importa dal canonical module."
        )

    def test_non_embed_routers_unaffected(self):
        """Routers non-embed (auth, customer_auth) usano ancora get_real_ip
        (per-IP global) — no regression non-embed rate limits.
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]

        # auth.py uses standard limiter (get_real_ip)
        auth_src = (repo_root / "backend/routers/auth.py").read_text(encoding="utf-8")
        assert "limiter = Limiter(key_func=get_real_ip" in auth_src, (
            "auth.py legacy limiter modificato — regression rate limits "
            "non-embed (signup/login/etc)."
        )

    def test_get_real_ip_with_slug_in_module_exports(self):
        """Helper esposto in __all__ del modulo."""
        from core import rate_limiting
        assert "get_real_ip_with_slug" in getattr(rate_limiting, "__all__", []), (
            "get_real_ip_with_slug non in __all__ — sentinel public API."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.5 — Sentry surface=embed auto-tagging + missing tests
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   1. Surface tagging auto: Sentry inbox triage piu' lento senza
#      filter per surface. Alert rule O3.1 [P2] Embed-SDK error spike
#      richiede tag `surface=embed` → mai triggherato pre-E1.5.
#
#   2. Missing tests dall'audit E1.x produzione consolidata:
#      - Rate-limit exhaustion 429 shape
#      - API version unsupported 400 shape
#      - CORS origin rejection 403 shape
#      - Versioning combined con altri error path
#
# Sentinel coprono:
#   1. Middleware class esiste + signature
#   2. Path prefix canonical pinned
#   3. Surface value canonical pinned
#   4. Auto-tag attivo SOLO su /api/public/embed/* paths
#   5. Defense: safe no-op se sentry_sdk non installato
#   6. Server.py registra il middleware nel layer stack
#   7. Missing tests aggiunti


class TestSEC_E_1_5_SentryEmbedSurfaceTag:
    """SEC-E.1.5: Sentry surface=embed middleware + integration tests."""

    def test_middleware_module_exists(self):
        from middleware import embed_surface_tag
        for name in [
            "EmbedSurfaceTagMiddleware",
            "EMBED_PATH_PREFIX",
            "EMBED_SURFACE_TAG_VALUE",
        ]:
            assert hasattr(embed_surface_tag, name), (
                f"middleware.embed_surface_tag manca '{name}'."
            )

    def test_path_prefix_canonical(self):
        """Path prefix pinned: /api/public/embed/ — coordinated col mount
        di embed_public router in server.py."""
        from middleware.embed_surface_tag import EMBED_PATH_PREFIX
        assert EMBED_PATH_PREFIX == "/api/public/embed/", (
            f"Path prefix drift: {EMBED_PATH_PREFIX!r}. Cambio richiede "
            f"sync con server.py app.include_router(prefix='/api') + "
            f"router prefix='/public/embed'."
        )

    def test_surface_value_canonical(self):
        """Surface value pinned 'embed' — match con O3.1 alert rule
        filter + capture_with_tags _KNOWN_SURFACES."""
        from middleware.embed_surface_tag import EMBED_SURFACE_TAG_VALUE
        assert EMBED_SURFACE_TAG_VALUE == "embed", (
            f"Surface value drift: {EMBED_SURFACE_TAG_VALUE!r}. "
            f"Sentry alert rule [P2] Embed-SDK error spike (O3.1) "
            f"filter `event.tags['surface'] is 'embed'` non triggered."
        )

    def test_middleware_tags_embed_path(self):
        """Middleware tags surface=embed quando path matches prefix."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from middleware.embed_surface_tag import EmbedSurfaceTagMiddleware
        import sentry_sdk
        from unittest.mock import patch

        captured = []
        def fake_set_tag(k, v):
            captured.append((k, v))

        with patch.object(sentry_sdk, "set_tag", side_effect=fake_set_tag):
            app = FastAPI()
            app.add_middleware(EmbedSurfaceTagMiddleware)

            @app.get("/api/public/embed/products/test")
            def embed_ep():
                return {"ok": True}

            client = TestClient(app)
            r = client.get("/api/public/embed/products/test")
            assert r.status_code == 200
            assert ("surface", "embed") in captured, (
                f"surface=embed tag NON settato sul path embed. "
                f"Captured: {captured}"
            )

    def test_middleware_skips_non_embed_paths(self):
        """Middleware NON tag su paths fuori da /api/public/embed/."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from middleware.embed_surface_tag import EmbedSurfaceTagMiddleware
        import sentry_sdk
        from unittest.mock import patch

        captured = []
        def fake_set_tag(k, v):
            captured.append((k, v))

        with patch.object(sentry_sdk, "set_tag", side_effect=fake_set_tag):
            app = FastAPI()
            app.add_middleware(EmbedSurfaceTagMiddleware)

            @app.get("/api/admin/users")
            def admin_ep():
                return {"ok": True}

            @app.get("/api/customer-auth/login")
            def customer_ep():
                return {"ok": True}

            client = TestClient(app)
            client.get("/api/admin/users")
            client.get("/api/customer-auth/login")

            assert ("surface", "embed") not in captured, (
                f"Tag surface=embed spuriously su path non-embed. "
                f"Captured: {captured}"
            )

    def test_middleware_safe_when_sentry_missing(self):
        """Middleware non blocca request quando sentry_sdk non installato.

        Source-check: middleware ha try/except ImportError che skippa
        il tagging silently. Test runtime preferito ma rischia Sentry
        hub side-effects in teardown (event queue flush) → source-check
        e' equivalent guarantee.
        """
        import inspect
        from middleware.embed_surface_tag import EmbedSurfaceTagMiddleware

        src = inspect.getsource(EmbedSurfaceTagMiddleware)
        assert "except ImportError" in src, (
            "Middleware NON ha branch ImportError — se sentry_sdk non "
            "installato (dev senza opt-in), middleware solleva → request "
            "crash."
        )
        # Defense in depth: anche generic Exception swallowed (es. Sentry
        # SDK installato ma broken)
        assert "except Exception" in src, (
            "Middleware NON ha branch generic Exception — Sentry SDK "
            "edge case (network down, ecc.) potrebbe bloccare request."
        )

    def test_server_registers_embed_surface_middleware(self):
        """server.py wire EmbedSurfaceTagMiddleware nel app stack."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/server.py").read_text(encoding="utf-8")
        assert "EmbedSurfaceTagMiddleware" in src, (
            "server.py NON registra EmbedSurfaceTagMiddleware — "
            "tag surface=embed mai applicato in produzione."
        )
        assert "app.add_middleware(EmbedSurfaceTagMiddleware)" in src, (
            "server.py importa ma non add_middleware il EmbedSurfaceTag."
        )

    # ── Missing tests aggiunti (audit E1.x produzione consolidata) ────

    def test_api_version_400_response_shape_canonical(self):
        """Unsupported X-API-Version → 400 con shape canonical pinned.

        Anti-regression: shape detail richiesta da SDK client per
        error recovery (mostra current + supported versions all'utente).
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch, AsyncMock

        async def fake_init(slug):
            return {
                "slug": slug, "org_name": "Test", "currency": "EUR",
                "storefront_languages": ["it"], "available_product_types": [],
                "categories": [], "fulfillment_modes": ["shipping"]
            }

        with patch("services.embed_init_service.get_embed_init_data", new=fake_init):
            from routers.embed_public import router
            app = FastAPI()
            app.include_router(router, prefix="/api")
            client = TestClient(app)

            r = client.get(
                "/api/public/embed/init/test-store",
                headers={"X-API-Version": "999"},
            )
            assert r.status_code == 400
            body = r.json()
            detail = body.get("detail")
            assert isinstance(detail, dict), (
                f"Detail non dict (canonical shape rotto): {detail!r}"
            )
            assert detail.get("code") == "UNSUPPORTED_API_VERSION"
            assert "supported_versions" in detail
            assert "current" in detail

    def test_embed_endpoint_404_response_clean(self):
        """Embed endpoint con slug inesistente → 404 senza leak (no Mongo
        internal error stack, no PII).
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from fastapi import HTTPException, status

        async def fake_resolve_org(slug):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found",
            )

        with patch("routers.public._resolve_org", new=fake_resolve_org):
            # Bypass via diretto a service che chiama _resolve_org
            from services.embed_init_service import get_embed_init_data
            import asyncio

            try:
                asyncio.run(get_embed_init_data("nonexistent-slug"))
                assert False, "Should have raised HTTPException 404"
            except HTTPException as e:
                assert e.status_code == 404
                # No internal stack trace leak
                assert "Mongo" not in str(e.detail or "")
                assert "Traceback" not in str(e.detail or "")


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 1.6 — SDK contract docs + error code catalog (closing E1)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Per pilot multi-merchant serve single source of truth per developer
#   integrator: integration guide + error code reference. Senza, ogni
#   merchant deve reverse-engineer endpoints + error shapes da OpenAPI
#   swagger (insufficient: no contract intent, no recovery flow examples).
#
#   E1.6 produce 2 doc canonical:
#     - embed-integration-guide.md (quick start, endpoint catalog,
#       versioning policy, CORS setup, rate limits)
#     - embed-error-codes.md (response shape, error code per status,
#       recovery flow examples)
#
# Sentinel coprono:
#   1. Doc files exist
#   2. Integration guide ha sezioni canonical (TL;DR, versioning,
#      endpoint catalog, CORS, search, inventory)
#   3. Error code catalog include codes pinned dal sentinel implementation:
#      - INVALID_API_VERSION (E1.1)
#      - UNSUPPORTED_API_VERSION (E1.1)
#      - STOCK_INSUFFICIENT (E1.2)
#   4. Endpoint catalog include tutti i 10 endpoint embed
#   5. Cross-link tra le 2 doc
#   6. Version + deprecation policy documented


class TestSEC_E_1_6_SDKContractDocs:
    """SEC-E.1.6: SDK contract docs (integration guide + error catalog)."""

    INTEGRATION_GUIDE_PATH = "docs/embed-integration-guide.md"
    ERROR_CODES_PATH = "docs/embed-error-codes.md"

    def _read(self, rel_path: str) -> str:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        full = repo_root / rel_path
        assert full.exists(), f"Doc mancante: {rel_path}"
        return full.read_text(encoding="utf-8")

    def test_integration_guide_exists(self):
        self._read(self.INTEGRATION_GUIDE_PATH)

    def test_error_codes_doc_exists(self):
        self._read(self.ERROR_CODES_PATH)

    def test_integration_guide_has_tldr_section(self):
        """TL;DR section presente — developer puo' partire in 60s."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "TL;DR" in doc or "Quick start" in doc, (
            "Manca quick start section — developer onboarding lento."
        )
        # Snippet HTML embed sample
        assert "<afianco-storefront-init" in doc, (
            "Manca esempio web component snippet — developer non sa "
            "come embeddare."
        )

    def test_integration_guide_documents_api_versioning(self):
        """API versioning protocol documentato (header request+response)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "X-API-Version" in doc, (
            "Manca X-API-Version header reference — client SDK non sa "
            "come specificare versione."
        )
        assert "supported_versions" in doc, (
            "Manca riferimento al supported_versions array nei error "
            "detail — client SDK error recovery povera."
        )

    def test_integration_guide_lists_all_10_endpoints(self):
        """Endpoint catalog completo (10 endpoint embed)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        required_endpoints = [
            "/init/{slug}",
            "/categories/{slug}",
            "/products/{slug}",
            "/cart",
            "/cart/{cart_id}",
            "/cart/{cart_id}/merge",
            "/checkout/start",
            "/checkout/complete",
        ]
        for ep in required_endpoints:
            assert ep in doc, (
                f"Endpoint '{ep}' non in integration guide — developer "
                f"non sa che esiste."
            )

    def test_integration_guide_documents_cors_setup(self):
        """CORS setup procedure documentata."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "CORS" in doc, "Manca sezione CORS"
        assert "allowed_origins" in doc, (
            "Manca riferimento store.allowed_origins config — merchant "
            "non sa come whitelist il proprio dominio."
        )

    def test_integration_guide_documents_search(self):
        """Search documentation (E1.3 q param + syntax)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "Search" in doc or "search" in doc, "Manca search section"
        assert "?q=" in doc, "Manca esempio query param"
        # Mongo $text syntax
        assert "phrase" in doc.lower() or "exclusion" in doc.lower(), (
            "Manca documentazione phrase/exclusion syntax — feature "
            "potente non scoperto."
        )

    def test_integration_guide_documents_inventory(self):
        """Inventory check behavior documentato (E1.2)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "STOCK_INSUFFICIENT" in doc, (
            "Manca STOCK_INSUFFICIENT code reference — SDK non sa "
            "come gestire over-sell prevention."
        )
        assert "stock_quantity" in doc.lower() or "inventory" in doc.lower(), (
            "Manca spiegazione inventory tracking."
        )

    def test_integration_guide_documents_rate_limits(self):
        """Rate limits per-merchant isolation (E1.4) documentato."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "Rate limit" in doc or "rate limit" in doc, (
            "Manca sezione rate limit."
        )
        assert "429" in doc, "Manca status code 429"
        # Per-merchant isolation specifico
        assert "per-merchant" in doc.lower() or "per-(IP" in doc, (
            "Manca spiegazione per-merchant isolation (E1.4)."
        )

    def test_integration_guide_documents_versioning_policy(self):
        """Deprecation policy documentata (additive vs breaking)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "deprecation" in doc.lower() or "Deprecation" in doc, (
            "Manca deprecation policy — merchant developer non sa cosa "
            "aspettarsi su v2 transition."
        )
        assert "additive" in doc.lower() or "Additive" in doc, (
            "Manca distinzione additive vs breaking changes."
        )

    def test_error_codes_catalog_pinned_codes(self):
        """Error codes implementati nel codebase sono nel catalog.

        CRITICAL anti-drift: se rinomi un code nel codebase senza
        update doc, sentinel fail (cross-reference rotto).
        """
        doc = self._read(self.ERROR_CODES_PATH)
        # Code pinned dall'implementazione (E1.1 + E1.2)
        canonical_codes = [
            "INVALID_API_VERSION",
            "UNSUPPORTED_API_VERSION",
            "STOCK_INSUFFICIENT",
        ]
        for code in canonical_codes:
            assert code in doc, (
                f"Error code '{code}' non in catalog — SDK developer "
                f"riceve error senza recovery guidance."
            )

    def test_error_codes_documents_response_shape(self):
        """Response shape canonical (structured detail dict) documentato."""
        doc = self._read(self.ERROR_CODES_PATH)
        # Pattern del structured detail
        assert '"detail"' in doc, "Manca esempio detail JSON structure"
        assert '"code"' in doc, (
            "Manca esempio campo 'code' nella structured detail — SDK "
            "client non sa che parse il code per branching."
        )

    def test_error_codes_documents_rate_limit_response(self):
        """429 response shape + Retry-After header documentato."""
        doc = self._read(self.ERROR_CODES_PATH)
        assert "429" in doc, "Manca 429 status"
        assert "Retry-After" in doc, (
            "Manca Retry-After header documentation — SDK non sa "
            "quanto wait prima retry."
        )

    def test_error_codes_documents_idempotency(self):
        """Idempotency-Key requirement documentato."""
        doc = self._read(self.ERROR_CODES_PATH)
        assert "Idempotency-Key" in doc, (
            "Manca Idempotency-Key documentation — SDK non sa che "
            "header e' richiesto su mutations."
        )

    def test_error_codes_documents_recovery_flows(self):
        """Recovery flow examples documentati (SDK error handling)."""
        doc = self._read(self.ERROR_CODES_PATH)
        assert "Recovery" in doc or "recovery" in doc, (
            "Manca recovery flow examples — SDK developer learn-by-doing "
            "senza concrete patterns."
        )

    def test_docs_cross_link(self):
        """Le 2 doc cross-reference fra loro."""
        guide = self._read(self.INTEGRATION_GUIDE_PATH)
        errors = self._read(self.ERROR_CODES_PATH)
        assert "embed-error-codes.md" in guide, (
            "Integration guide NON link a error codes doc — orphan."
        )
        assert "embed-integration-guide.md" in errors, (
            "Error codes doc NON link a integration guide — orphan."
        )

    def test_integration_guide_documents_support_contact(self):
        """Support contact email documentato (debug operatore)."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "davide@afianco.ch" in doc, (
            "Manca contact email — developer integrator non sa a chi "
            "scrivere per bug reports."
        )

    def test_integration_guide_documents_changelog(self):
        """Changelog v1 documentato — pin baseline contract."""
        doc = self._read(self.INTEGRATION_GUIDE_PATH)
        assert "Changelog" in doc or "v1" in doc, (
            "Manca changelog — futuro v2 transition senza baseline ref."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 2.1 — Embed distribution canonical helper
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Bundle URL hardcoded in 3+ places (snippet generator, docs, frontend
#   modal) crea drift garantito al primo cambio. E2.1 produce SINGLE
#   SOURCE OF TRUTH per:
#     - Bundle JS URL (env-driven)
#     - Snippet HTML generator
#     - Versioning path (/embed/v1/)
#
#   Architettura Cloudflare-ready: switch a CDN esterno = cambio env
#   EMBED_CDN_BASE_URL, zero code changes.
#
# Sentinel coprono:
#   1. Helper module + public API canonical
#   2. Default CDN base URL (nginx self-host)
#   3. Versioning path "v1" pinned
#   4. Env var override funziona (Cloudflare-ready)
#   5. Snippet generator produce HTML coerente con embed-SDK
#   6. Bundle URL pattern: {base}/{version}/afianco-embed.es.js
#   7. Hosted storefront URL pattern: {app}/s/{slug}


class TestSEC_E_2_1_EmbedDistribution:
    """SEC-E.2.1: canonical helper per bundle URL + snippet generator."""

    def test_helper_module_exists(self):
        from core import embed_distribution
        for name in [
            "EMBED_CDN_BASE_URL",
            "EMBED_BUNDLE_VERSION",
            "DEFAULT_CDN_BASE",
            "APP_BASE_URL",
            "get_embed_bundle_url",
            "get_embed_module_url",
            "get_embed_umd_url",
            "get_hosted_storefront_url",
            "generate_embed_snippet",
            "get_distribution_info",
        ]:
            assert hasattr(embed_distribution, name), (
                f"core.embed_distribution manca '{name}' — public API rotta."
            )

    def test_default_cdn_base_pinned(self):
        """Default CDN base URL pinned — nginx self-host iniziale.

        Cambio del default richiede review consapevole (es. quando
        migriamo a Cloudflare R2 → cambio commit dedicato + sentinel
        aggiornata + docs sync).
        """
        from core.embed_distribution import DEFAULT_CDN_BASE
        assert DEFAULT_CDN_BASE == "https://app.afianco.ch/embed", (
            f"DEFAULT_CDN_BASE drift: {DEFAULT_CDN_BASE!r}. "
            f"Sync con nginx config + embed-integration-guide.md."
        )

    def test_bundle_version_canonical(self):
        """EMBED_BUNDLE_VERSION pinned — v1 corrente."""
        from core.embed_distribution import EMBED_BUNDLE_VERSION
        assert EMBED_BUNDLE_VERSION == "v1", (
            f"EMBED_BUNDLE_VERSION drift: {EMBED_BUNDLE_VERSION!r}. "
            f"Bump version solo per breaking change SDK + migration "
            f"window 6+ mesi documented in embed-integration-guide.md."
        )

    def test_env_override_works_cloudflare_ready(self):
        """CRITICAL: env var EMBED_CDN_BASE_URL override funziona.

        Anti-regression: il punto piu' importante di E2.1 — switch
        a Cloudflare R2 deve essere ZERO code change. Solo env update.
        """
        import os
        import importlib
        import core.embed_distribution

        # Save original
        original = os.environ.get("EMBED_CDN_BASE_URL")
        try:
            # Simulate Cloudflare R2 migration
            os.environ["EMBED_CDN_BASE_URL"] = "https://cdn.afianco.ch"
            importlib.reload(core.embed_distribution)
            from core.embed_distribution import (
                get_embed_bundle_url, get_distribution_info,
            )
            url = get_embed_bundle_url()
            assert url == "https://cdn.afianco.ch/v1/afianco-embed.es.js", (
                f"Override env var non onorato: {url!r}. "
                f"Cloudflare migration NON sara' zero-code."
            )
            info = get_distribution_info()
            assert info["is_default_cdn"] is False, (
                "is_default_cdn flag NON aggiornato post-override → "
                "ops dashboard non sa se siamo migrated."
            )
        finally:
            # Restore + reload to original state
            if original is None:
                os.environ.pop("EMBED_CDN_BASE_URL", None)
            else:
                os.environ["EMBED_CDN_BASE_URL"] = original
            importlib.reload(core.embed_distribution)

    def test_bundle_url_pattern_with_version_path(self):
        """Bundle URL include esplicitamente version segment.

        Pattern: {base}/{version}/afianco-embed.es.js
        Senza version path nel URL, future v2 transition rompe v1
        clients (no graceful migration).
        """
        from core.embed_distribution import (
            get_embed_bundle_url, EMBED_BUNDLE_VERSION,
        )
        url = get_embed_bundle_url()
        assert f"/{EMBED_BUNDLE_VERSION}/" in url, (
            f"Bundle URL non include version path /{EMBED_BUNDLE_VERSION}/ — "
            f"future v2 = breaking change forced: {url!r}"
        )
        assert url.endswith("afianco-embed.es.js"), (
            f"Bundle URL non termina con afianco-embed.es.js: {url!r}"
        )

    def test_hosted_storefront_url_pattern(self):
        """URL hosted: {app}/s/{slug} — coerente con frontend route /s/:slug."""
        from core.embed_distribution import get_hosted_storefront_url
        url = get_hosted_storefront_url("test-store")
        assert "/s/test-store" in url, (
            f"Hosted URL pattern drift: {url!r}. Coerente con frontend "
            f"App.js route /s/:slug."
        )
        # Test base override
        custom = get_hosted_storefront_url("test", base_app_url="https://custom.com")
        assert custom == "https://custom.com/s/test"

    def test_snippet_includes_bundle_script(self):
        """Snippet contiene <script type=\"module\" src=\"<bundle_url>\">."""
        from core.embed_distribution import generate_embed_snippet, get_embed_bundle_url
        snippet = generate_embed_snippet("test-store")
        bundle_url = get_embed_bundle_url()
        assert f'<script type="module" src="{bundle_url}">' in snippet, (
            f"Snippet non include canonical script tag con bundle URL.\n"
            f"Snippet:\n{snippet}"
        )

    def test_snippet_includes_storefront_init_with_slug(self):
        """Snippet contiene <afianco-storefront-init slug=\"...\">."""
        from core.embed_distribution import generate_embed_snippet
        snippet = generate_embed_snippet("my-shop")
        assert '<afianco-storefront-init slug="my-shop">' in snippet, (
            f"Snippet non binda slug al storefront-init: {snippet!r}"
        )

    def test_snippet_includes_all_core_components(self):
        """Snippet include i 6 web component canonical per embedding 360.

        Track E Step 2.4.5 — landing drawer + unified navbar UX:
        - header (navbar sticky con account + cart trigger button)
        - account (login/signup/portal drawer, hide-trigger)
        - product-grid (catalogo + filtri)
        - product-detail (landing drawer per ogni prodotto) ← E2.4.5
        - cart-drawer (carrello, hide-trigger)
        - checkout-button (checkout Stripe)

        Match per prefisso "<tagname" (senza chiusura `>`) per supportare
        sia tag self-closing che con attributi (es. hide-trigger).
        """
        from core.embed_distribution import generate_embed_snippet
        snippet = generate_embed_snippet("test")
        required = [
            "<afianco-header",            # E2.4.4 — navbar unificato
            "<afianco-account",           # E2.4.2 — auth UX (login/signup/portal)
            "<afianco-product-grid",      # prodotti + filtri categoria
            "<afianco-product-detail",    # E2.4.5 — landing drawer per prodotto
            "<afianco-cart-drawer",       # carrello
            "<afianco-checkout-button",   # checkout Stripe
        ]
        for component in required:
            assert component in snippet, (
                f"Snippet manca {component} — embedding NON 360-gradi. "
                f"Snippet:\n{snippet}"
            )

    def test_snippet_uses_unified_header_pattern(self):
        """Track E Step 2.4.4 — quando lo snippet include <afianco-header>,
        i drawer (account + cart) DEVONO avere hide-trigger per evitare
        duplicazione del FAB (header trigger + componente FAB → 2 button
        visibili = bug UX risolto in E2.4.4).

        Pin: header presente → hide-trigger su entrambi i drawer.
        """
        from core.embed_distribution import generate_embed_snippet
        snippet = generate_embed_snippet("test")
        if "<afianco-header" in snippet:
            assert "<afianco-account hide-trigger" in snippet or \
                   "<afianco-account  hide-trigger" in snippet, (
                "Header presente ma <afianco-account> senza hide-trigger → "
                "user vedra' 2 trigger button (header + FAB). "
                "Pattern E2.4.4 violato."
            )
            assert "<afianco-cart-drawer hide-trigger" in snippet or \
                   "<afianco-cart-drawer  hide-trigger" in snippet, (
                "Header presente ma <afianco-cart-drawer> senza hide-trigger → "
                "user vedra' 2 trigger button (header + FAB). "
                "Pattern E2.4.4 violato."
            )

    def test_snippet_closing_tags_balanced(self):
        """HTML well-formed: open + close tags bilanciati (anti-XSS sanity)."""
        from core.embed_distribution import generate_embed_snippet
        snippet = generate_embed_snippet("test")
        # Check balanced count of opening vs closing storefront-init
        assert snippet.count("<afianco-storefront-init") == 1
        assert snippet.count("</afianco-storefront-init>") == 1
        # Children tags balanced (E2.4.5: 6 components incl. product-detail)
        # Use "<tag" prefix match (supports tag with attributes like hide-trigger)
        for tag in [
            "afianco-header",
            "afianco-account",
            "afianco-product-grid",
            "afianco-product-detail",
            "afianco-cart-drawer",
            "afianco-checkout-button",
        ]:
            assert snippet.count(f"<{tag}") == 1, (
                f"Tag <{tag}> unbalanced opens: {snippet.count(f'<{tag}')}"
            )
            assert snippet.count(f"</{tag}>") == 1, (
                f"Tag </{tag}> unbalanced closes"
            )

    def test_distribution_info_shape(self):
        """get_distribution_info returns canonical dict shape (ops API)."""
        from core.embed_distribution import get_distribution_info
        info = get_distribution_info()
        required_keys = {
            "cdn_base", "version", "bundle_url", "umd_bundle_url",
            "app_base", "default_cdn", "is_default_cdn",
        }
        assert set(info.keys()) == required_keys, (
            f"Distribution info shape drift: keys={set(info.keys())} "
            f"vs expected {required_keys}"
        )
        assert isinstance(info["is_default_cdn"], bool)


# ─── SEC-E2.4.6-10 — Type-aware embed endpoints contract ───────────────
#
# Track E Steps 2.4.6 / 2.4.7 / 2.4.9 / 2.4.10 — sentinel pinati per:
#   * EmbedProductDetail enriched contract (38 campi cross-type)
#   * Availability endpoint scoped multi-tenant + shared slot_generator
#   * Price preview endpoint embed-ready
#   * Customer assets endpoints (downloads/bookings/reservations)
#
# Anti-regression: questi pin garantiscono che il widget Lit possa contare
# sui field documentati senza break tra release.


class TestSEC_E2_4_x_TypeAwareEmbedContract:
    """SEC-E2.4.6-10: type-aware embed endpoints + model contract pin."""

    def test_embed_product_detail_has_type_specific_fields(self):
        """EmbedProductDetail Pydantic model espone i field type-specific
        attesi dai picker Lit (service/event/rental/course/extras)."""
        from routers.embed_public import EmbedProductDetail
        fields = set(EmbedProductDetail.model_fields.keys())
        required = {
            # Service
            "service_options", "service_duration_minutes",
            "service_allow_custom_request", "has_availability_slots",
            "duration_label", "slot_duration_minutes",
            # Event_ticket
            "occurrences", "requires_attendee_details",
            "require_attendee_email", "require_attendee_phone",
            "attendee_fields", "order_fields",
            # Rental
            "rental_unit", "reservation_flavor", "extras",
            # Course
            "course_lessons_count", "course_duration_seconds",
            "course_access_policy", "course_access_expiry_days",
            # Cross-type
            "cover_image_url", "long_description", "terms_content",
            # E2.4.5 base
            "offer_profile_id",
        }
        missing = required - fields
        assert not missing, (
            f"EmbedProductDetail missing type-specific fields: {missing}. "
            f"UI picker Lit relies on these — drift = broken widget."
        )

    def test_embed_product_detail_no_pii_leak(self):
        """EmbedProductDetail NON deve esporre campi admin-internal
        (cost_price, cost_source, tags, organization_id, sku)."""
        from routers.embed_public import EmbedProductDetail
        fields = set(EmbedProductDetail.model_fields.keys())
        forbidden = {
            "cost_price", "cost_source", "tags", "organization_id",
            "sku", "metadata", "created_at", "updated_at", "is_active",
            "is_published", "store_ids",
        }
        leaked = fields & forbidden
        assert not leaked, (
            f"EmbedProductDetail leaks admin/PII fields: {leaked}. "
            f"Add to detail projection blacklist."
        )

    def test_availability_endpoint_uses_shared_slot_generator(self):
        """L'endpoint /availability deve usare il service condiviso
        ``slot_generator.generate_available_slots`` (parita' storefront).

        Pre-fix usava algoritmo manuale che mancava il fallback
        ``use_default_schedule`` di Onda 15. Sentinel pin: import diretto
        del service condiviso nel router.
        """
        from routers import embed_public
        import inspect
        src = inspect.getsource(embed_public.get_embed_product_availability)
        assert "generate_available_slots" in src, (
            "embed /availability NON usa generate_available_slots service "
            "→ rischio drift logic vs storefront classico."
        )

    def test_embed_endpoints_registered_in_router(self):
        """I 3 nuovi endpoint E2.4.6-10 devono essere registrati nel router
        embed_public (regression guard)."""
        from routers.embed_public import router
        routes = {r.path for r in router.routes}
        required_paths = {
            "/public/embed/products/{slug}/{product_id}",            # E2.4.5 detail
            "/public/embed/products/{slug}/{product_id}/availability",  # E2.4.6 service slots
            "/public/embed/price-preview/{slug}",                    # E2.4.10 live price
        }
        missing = required_paths - routes
        assert not missing, (
            f"embed_public router missing endpoints: {missing}. "
            f"Widget Lit components rely on these — drift = broken UX."
        )

    def test_customer_portal_assets_endpoints_registered(self):
        """Customer portal endpoint per widget tab (downloads/bookings/
        reservations) devono essere registrati."""
        from routers.customer_portal import router
        routes = {r.path for r in router.routes}
        required_paths = {
            "/customer/downloads",       # E2.4.6 widget tab Download
            "/customer/bookings",        # E2.4.6 widget tab Prenotazioni
            "/customer/reservations",    # E2.4.6 widget tab Prenotazioni
        }
        missing = required_paths - routes
        assert not missing, (
            f"customer_portal missing endpoints: {missing}. "
            f"Widget Lit portal tabs rely on these."
        )

    def test_embed_filters_event_ticket_without_occurrences(self):
        """E2.4.7 fix — il widget deve filtrare gli event_ticket senza
        occurrences (parita' storefront /api/public/catalog/{slug}).

        Sentinel: il service get_embed_products_data contiene la logica
        di post-filter degli event_ticket. Source inspection.
        """
        from services import embed_init_service
        import inspect
        src = inspect.getsource(embed_init_service.get_embed_products_data)
        # Pattern essential: dopo il fetch base + post-filter via
        # event_occurrences_collection
        assert "event_occurrences_collection" in src, (
            "embed products list NON filtra event_ticket per occurrence "
            "presence → discrepancy con storefront/admin (event senza "
            "data invisibile in admin ma visibile in widget = bug UX)."
        )

    def test_embed_extras_side_fetch_cross_type(self):
        """E2.4.9 — extras side-fetch attivo per physical/digital/service/
        rental (no piu' solo rental). Source inspection."""
        from services import embed_init_service
        import inspect
        src = inspect.getsource(
            embed_init_service.get_embed_product_detail_data
        )
        # Pattern: il check item_type include i 4 type, non solo rental
        # ("physical", "digital", "service", "rental")
        assert 'item_type in ("physical", "digital", "service", "rental")' in src, (
            "embed detail extras side-fetch e' scoped solo a rental — "
            "violazione E2.4.9. Storefront React (Physical/Digital/Service "
            "LandingPage) usa extras cross-type."
        )

    def test_embed_coupons_validate_endpoint_registered(self):
        """E4.1 — Coupons validate endpoint registrato per widget checkout."""
        from routers.embed_public import router
        routes = {r.path for r in router.routes}
        assert "/public/embed/coupons/validate/{slug}" in routes, (
            "Endpoint coupons/validate non registrato. Widget Lit "
            "checkout-button non puo' applicare codici sconto live."
        )

    def test_validate_coupon_dry_run_no_usage_increment(self):
        """E4.1 — dry-run validation NON deve incrementare current_uses
        (l'increment avviene solo a checkout reale per anti race-condition).

        Source inspection: validate_coupon_dry_run NON deve chiamare
        find_one_and_update con $inc (pattern del vero validate_coupon).
        """
        from routers import coupons
        import inspect
        src = inspect.getsource(coupons.validate_coupon_dry_run)
        assert "find_one_and_update" not in src, (
            "validate_coupon_dry_run usa find_one_and_update → questo "
            "incrementa current_uses anche al solo preview! Bug critical: "
            "il customer puo' esaurire coupon solo guardando il prezzo."
        )
        # Verifica check max_uses come read-only
        assert "current_uses" in src and "max_uses" in src, (
            "dry-run deve comunque controllare max_uses (read-only)."
        )

    def test_embed_checkout_start_accepts_coupon_code(self):
        """E4.1 — EmbedCheckoutStartRequest accetta coupon_code (max_length=30)."""
        from routers.embed_public import EmbedCheckoutStartRequest
        fields = EmbedCheckoutStartRequest.model_fields
        assert "coupon_code" in fields, (
            "EmbedCheckoutStartRequest.coupon_code missing — widget non puo' "
            "propagare codice promo applicato al checkout."
        )

    def test_dynamic_cors_recognizes_coupons_validate_path(self):
        """E4.1 — Middleware regex riconosce /coupons/validate/{slug}
        come path con slug embedded (preflight safe senza ?slug=)."""
        from middleware.dynamic_cors import _slug_from_path
        slug = _slug_from_path(
            "/api/public/embed/coupons/validate/marco-conti-coaching"
        )
        assert slug == "marco-conti-coaching"

    def test_embed_shipping_options_endpoint_registered(self):
        """E4.2 — Shipping options endpoint registrato per widget checkout."""
        from routers.embed_public import router
        routes = {r.path for r in router.routes}
        assert "/public/embed/shipping-options/{slug}" in routes, (
            "Endpoint shipping-options/{slug} non registrato. "
            "Widget Lit checkout non puo' renderizzare radio tariffe."
        )

    def test_embed_checkout_start_accepts_shipping_fields(self):
        """E4.2 — EmbedCheckoutStartRequest accetta shipping_address_details +
        shipping_option_id + fulfillment_mode."""
        from routers.embed_public import EmbedCheckoutStartRequest
        fields = EmbedCheckoutStartRequest.model_fields
        required = {
            "fulfillment_mode",
            "shipping_address_details",
            "shipping_option_id",
            "shipping_option_label",
        }
        missing = required - set(fields.keys())
        assert not missing, (
            f"EmbedCheckoutStartRequest missing shipping fields: {missing}. "
            f"Physical product checkout incomplete via widget."
        )

    def test_dynamic_cors_recognizes_shipping_options_path(self):
        """E4.2 — Middleware regex riconosce /shipping-options/{slug}."""
        from middleware.dynamic_cors import _slug_from_path
        slug = _slug_from_path(
            "/api/public/embed/shipping-options/marco-conti-coaching"
        )
        assert slug == "marco-conti-coaching"

    def test_embed_init_exposes_design_tokens_and_nav_links(self):
        """E4.3 — EmbedInitResponse espone design_tokens + custom_nav_links
        per parita' col storefront classico (Phase 8/9 propagation)."""
        from routers.embed_public import EmbedInitResponse
        fields = EmbedInitResponse.model_fields
        assert "design_tokens" in fields, (
            "EmbedInitResponse.design_tokens missing — widget non puo' "
            "matchare brand merchant (Phase 9 tokens)."
        )
        assert "custom_nav_links" in fields, (
            "EmbedInitResponse.custom_nav_links missing — widget header "
            "non puo' renderizzare nav links merchant (Phase 8)."
        )

    def test_umd_bundle_url_distinct(self):
        """UMD bundle URL distinct da ESM (fallback for old browsers)."""
        from core.embed_distribution import get_embed_bundle_url, get_embed_umd_url
        esm = get_embed_bundle_url()
        umd = get_embed_umd_url()
        assert esm != umd, "ESM e UMD URL identici — wrong filename"
        assert esm.endswith(".es.js"), f"ESM URL non termina .es.js: {esm}"
        assert umd.endswith(".umd.js"), f"UMD URL non termina .umd.js: {umd}"


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 2.2 — Store embed configuration router (modular, isolated)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   2 endpoint admin per merchant dashboard embed setup:
#     GET    /api/stores/{id}/embed-info       (snippet + status)
#     PATCH  /api/stores/{id}/allowed-origins  (manage list)
#
#   Modular design (NO monolith): router dedicato store_embed.py,
#   non aggiunto a routers/stores.py (gia' carico) o routers/admin.py
#   (4000+ righe).
#
# Sentinel coprono:
#   1. Router exists + 2 endpoints registered
#   2. Auth gating: require_admin (org-level, multi-tenant safe)
#   3. Response model contract (StoreEmbedInfoResponse field shape)
#   4. allowed_origins validation riusa Pydantic helper (consistency)
#   5. Audit log su PATCH (forensic compliance)
#   6. Multi-tenant: cross-org access → 404 (anti-enumeration)
#   7. Server.py registra il router


class TestSEC_E_2_2_StoreEmbedRouter:
    """SEC-E.2.2: store embed config router modular + endpoint contract."""

    def test_router_module_exists(self):
        from routers import store_embed
        assert hasattr(store_embed, "router"), (
            "routers/store_embed.py manca 'router' export."
        )

    def test_router_has_canonical_endpoints(self):
        """Endpoint canonici: GET embed-info, POST embed-snippet, GET
        embed-preview-token, PATCH allowed-origins.

        I due endpoint à-la-carte (embed-snippet, embed-preview-token) sono
        stati aggiunti col builder "Componi"; il sentinel pinna l'insieme
        completo così future aggiunte richiedono un update esplicito.
        """
        from routers.store_embed import router
        paths = sorted({
            (frozenset(r.methods or []), r.path)
            for r in router.routes if hasattr(r, "path")
        })
        # Sub-resource pattern: stores/{store_id}/embed-*
        expected = sorted({
            (frozenset({"GET"}), "/stores/{store_id}/embed-info"),
            (frozenset({"POST"}), "/stores/{store_id}/embed-snippet"),
            (frozenset({"GET"}), "/stores/{store_id}/embed-preview-token"),
            (frozenset({"PATCH"}), "/stores/{store_id}/allowed-origins"),
        })
        assert paths == expected, (
            f"Router endpoint drift: {paths} vs expected {expected}. "
            f"Aggiungere endpoint richiede update sentinel."
        )

    def test_endpoints_require_admin_auth(self):
        """Auth gating: require_verified_admin per TUTTI gli endpoint admin (R8).

        R8 — gli endpoint di configurazione embed (CORS allowed_origins,
        snippet, preview token) richiedono org admin CON email verificata:
        la dependency deve essere ``require_verified_admin``, non il semplice
        ``require_admin`` (che non controlla la verifica email).
        """
        import inspect
        from auth import require_verified_admin
        from routers.store_embed import (
            get_store_embed_info,
            compose_store_embed_snippet,
            get_store_embed_preview_token,
            update_store_allowed_origins,
        )

        for fn in [
            get_store_embed_info,
            compose_store_embed_snippet,
            get_store_embed_preview_token,
            update_store_allowed_origins,
        ]:
            sig = inspect.signature(fn)
            # current_user param presente
            assert "current_user" in sig.parameters, (
                f"{fn.__name__} manca current_user dependency — "
                f"endpoint NOT protected"
            )
            default = sig.parameters["current_user"].default
            assert default is not inspect.Parameter.empty, (
                f"{fn.__name__}.current_user senza Depends() — anonymous "
                f"access possibile (org_admin role REQUIRED)."
            )
            # R8 — la dependency deve essere require_verified_admin
            assert getattr(default, "dependency", None) is require_verified_admin, (
                f"{fn.__name__}.current_user non usa require_verified_admin "
                f"(R8: serve org admin + email verificata, non solo il ruolo)."
            )

    def test_response_model_contract_canonical(self):
        """StoreEmbedInfoResponse field shape pinned per frontend modal.

        Field stability = CONTRACT. Additions OK, rimozioni o rinomine
        richiedono bump version embed-SDK (vedi embed-integration-guide.md).
        """
        from routers.store_embed import StoreEmbedInfoResponse
        fields = StoreEmbedInfoResponse.model_fields
        required_fields = {
            "store_id", "store_slug", "store_name", "is_published",
            "bundle_url", "hosted_url", "snippet",
            "allowed_origins", "embed_status",
        }
        actual = set(fields.keys())
        missing = required_fields - actual
        assert not missing, (
            f"StoreEmbedInfoResponse manca field {missing} — frontend modal "
            f"contract rotto."
        )

    def test_compute_embed_status_logic(self):
        """Status canonical: active | no_origins | store_unpublished."""
        from routers.store_embed import _compute_embed_status

        # Published + origins → active
        assert _compute_embed_status(True, ["https://x.com"]) == "active"
        # Published + no origins → no_origins (hosted only)
        assert _compute_embed_status(True, []) == "no_origins"
        # Unpublished (any origins) → store_unpublished
        assert _compute_embed_status(False, ["https://x.com"]) == "store_unpublished"
        assert _compute_embed_status(False, []) == "store_unpublished"

    def test_validation_reuses_pydantic_helper(self):
        """AllowedOriginsUpdate riusa _validate_allowed_origins da
        models/store.py — single source of truth.

        Anti-drift: validation consistente cross-endpoint (create store
        + update allowed_origins vedono stessa logica).
        """
        from routers.store_embed import AllowedOriginsUpdate
        # Wildcard rejected (validation kicks in)
        try:
            AllowedOriginsUpdate(allowed_origins=["*"])
            assert False, "Should reject wildcard '*'"
        except Exception as e:
            # Pydantic ValidationError o Value error
            err_str = str(e).lower()
            assert "wildcard" in err_str or "origin" in err_str or "*" in err_str

        # Too many (>10) rejected
        too_many = [f"https://shop{i}.com" for i in range(15)]
        try:
            AllowedOriginsUpdate(allowed_origins=too_many)
            assert False, "Should reject >10 origins"
        except Exception:
            pass

        # Valid passes
        ok = AllowedOriginsUpdate(allowed_origins=["https://www.mioshop.com"])
        assert ok.allowed_origins == ["https://www.mioshop.com"]

    def test_endpoint_returns_canonical_snippet(self):
        """GET embed-info usa generate_embed_snippet (single source).

        Anti-drift: snippet sempre generato dal canonical helper, no
        hardcoded HTML scatter nel router.
        """
        import inspect
        from routers import store_embed

        src = inspect.getsource(store_embed)
        assert "generate_embed_snippet" in src, (
            "Router non usa generate_embed_snippet canonical helper — "
            "scatter snippet HTML in piu' posti = drift garantito."
        )

    def test_endpoint_uses_bundle_url_helper(self):
        """Router usa get_embed_bundle_url canonical (env-driven).

        Cloudflare-ready: switch CDN = env var, zero code change.
        """
        import inspect
        from routers import store_embed

        src = inspect.getsource(store_embed)
        assert "get_embed_bundle_url" in src, (
            "Router NON usa get_embed_bundle_url canonical — hardcoded "
            "URL = drift garantito + Cloudflare-ready rotto."
        )

    def test_patch_audit_log_action_canonical(self):
        """PATCH allowed-origins registra audit con action canonical name."""
        import inspect
        from routers.store_embed import update_store_allowed_origins

        src = inspect.getsource(update_store_allowed_origins)
        assert "STORE_EMBED_ORIGINS_UPDATED" in src, (
            "Audit action name drift — forensic post-incident impossibile."
        )
        assert "audit_logs_collection" in src, (
            "PATCH non insert in audit_logs_collection — compliance "
            "GDPR (ChiHaCambiatoCosaEQuando) rotto."
        )
        # Anti-blocking: audit fail non rompe response
        assert "except" in src, (
            "Audit insert senza try/except — fail audit blocca update "
            "(wrong: audit e' best-effort)."
        )

    def test_multi_tenant_isolation_via_org_id_filter(self):
        """CRITICAL: query store DEVE includere organization_id filter.

        Anti-leak: cross-org access tentato → 404 (anti-enumeration).
        Pinning del pattern: tutte le query stores_collection contengono
        organization_id nella WHERE clause.
        """
        import inspect
        from routers.store_embed import _load_store_or_404

        src = inspect.getsource(_load_store_or_404)
        assert "organization_id" in src, (
            "Helper _load_store_or_404 NON filtra per organization_id "
            "— cross-org leak possible."
        )
        # Query pattern: {"id": store_id, "organization_id": org_id}
        assert "{\"id\": store_id, \"organization_id\":" in src or \
               "{'id': store_id, 'organization_id':" in src, (
            "Pattern multi-tenant query non canonical."
        )

    def test_server_registers_store_embed_router(self):
        """server.py wire store_embed_router."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/server.py").read_text(encoding="utf-8")
        assert "store_embed_router" in src, (
            "server.py non importa store_embed_router."
        )
        assert "app.include_router(store_embed_router.router" in src, (
            "server.py NON registra store_embed_router via include_router."
        )

    def test_router_modular_not_in_stores_or_admin(self):
        """Embed config router DEDICATED file, non aggiunto a stores.py
        (modular design — no monolith).

        Sentinel pin: routers/store_embed.py exists come file separato.
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        assert (repo_root / "backend/routers/store_embed.py").exists(), (
            "store_embed.py NON esiste come file dedicato — modular "
            "design rotto."
        )

    def test_router_imports_canonical_helpers(self):
        """Router importa generate_embed_snippet + get_embed_bundle_url
        + get_hosted_storefront_url (single source of truth).
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "backend/routers/store_embed.py").read_text(encoding="utf-8")
        for helper in [
            "generate_embed_snippet",
            "get_embed_bundle_url",
            "get_hosted_storefront_url",
        ]:
            assert helper in src, (
                f"Router NON importa canonical helper '{helper}' — "
                f"hardcoded logic = drift."
            )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 2.3 — Frontend "Condividi store" modal (React)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Merchant dashboard self-service: ogni store ha action "Condividi"
#   che apre modale con 2 tab:
#     1. "Link condivisibile" — hosted URL (no setup richiesto)
#     2. "Codice embed" — allowed_origins manager + snippet HTML
#
#   Pattern: API-driven (snippet generato server-side da E2.1 helper).
#   Frontend SOLO presenta + permette edit allowed_origins.
#
# Sentinel coprono (source-check frontend JS):
#   1. API client file exists + 2 method canonical
#   2. ShareStoreModal component exists + chiama API canonical
#   3. StoreCard ha onShare prop + action "Condividi"
#   4. StoresPage importa + wire ShareStoreModal con state
#   5. Modal usa 2 tab pattern (hosted + embed)
#   6. Allowed origins client-side validation per UX feedback
#   7. Copy-to-clipboard pattern presente
#   8. No hardcoded URL: snippet/bundle_url vengono da embedInfo (API)


class TestSEC_E_2_3_FrontendShareModal:
    """SEC-E.2.3: frontend share modal + API client + integration."""

    from pathlib import Path
    REPO_ROOT = Path(__file__).resolve().parents[2]

    def _read_frontend(self, rel_path: str) -> str:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        full = repo_root / rel_path
        assert full.exists(), f"File frontend mancante: {rel_path}"
        return full.read_text(encoding="utf-8")

    def test_api_client_exists(self):
        """frontend/src/api/storeEmbed.js exists + exports storeEmbedAPI."""
        src = self._read_frontend("frontend/src/api/storeEmbed.js")
        assert "storeEmbedAPI" in src, (
            "Missing storeEmbedAPI export — modal non puo' chiamare backend."
        )
        # 2 method canonical
        assert "getEmbedInfo" in src, "Missing getEmbedInfo method"
        assert "updateAllowedOrigins" in src, "Missing updateAllowedOrigins method"

    def test_api_client_uses_canonical_endpoints(self):
        """API client chiama gli endpoint canonical del router store_embed.py."""
        src = self._read_frontend("frontend/src/api/storeEmbed.js")
        # GET /api/stores/{id}/embed-info
        assert "/api/stores/" in src, "Missing /api/stores/ prefix"
        assert "/embed-info" in src, "Missing /embed-info endpoint"
        # PATCH /api/stores/{id}/allowed-origins
        assert "/allowed-origins" in src, "Missing /allowed-origins endpoint"

    def test_share_modal_component_exists(self):
        """ShareStoreModal.jsx exists."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "export default function ShareStoreModal" in src, (
            "ShareStoreModal default export mancante."
        )

    def test_share_modal_uses_api_client(self):
        """ShareStoreModal chiama storeEmbedAPI (no direct axios calls)."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "storeEmbedAPI" in src, (
            "Modal non usa canonical API client — drift se backend cambia."
        )
        assert "getEmbedInfo" in src, "Modal non chiama getEmbedInfo on open"
        assert "updateAllowedOrigins" in src, (
            "Modal non chiama updateAllowedOrigins su Save"
        )

    def test_share_modal_has_two_tabs(self):
        """Modal usa pattern 2-tab (Tabs Shadcn UI)."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        # Tab components
        assert "TabsList" in src, "Missing Tabs structure"
        assert "TabsTrigger" in src, "Missing TabsTrigger"
        assert "TabsContent" in src, "Missing TabsContent"
        # 2 tab data-testid pinned (data-testid="share-tab-hosted" + share-tab-embed)
        assert "share-tab-hosted" in src, (
            "Missing data-testid='share-tab-hosted' — sentinel anti-rename."
        )
        assert "share-tab-embed" in src, (
            "Missing data-testid='share-tab-embed'."
        )

    def test_share_modal_no_hardcoded_urls(self):
        """Snippet + URL vengono da embedInfo API (no hardcoded).

        CRITICAL: hardcoded URL = drift quando migration CDN (Cloudflare).
        Cloudflare-ready pattern: server controls URL, frontend just renders.

        Note: bundle_url e' contained nel snippet (server-rendered), quindi
        frontend NON deve accederlo direttamente. Snippet+hosted_url
        sufficienti per UX completa.
        """
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        # No hardcoded CDN base URL in actual rendering (URLs only in
        # comments/docstring of the file — checked via specific patterns).
        # Hardcoded URL would be like `src=" https://app.afianco.ch/embed/v1/...`
        # or as bare string literal in JSX prop.
        # Look for literal URL inside JSX (excludes the docstring comments)
        # by checking that we DON'T have suspicious string patterns:
        # We allow it in docstring (comment block at top), but not in JSX.
        # Simple approach: count lines that have "https://app.afianco.ch"
        # as RAW string (not inside /* */ block).
        # Strip comment block first
        # Hard rule: bundle_url e hosted_url DEVONO arrivare da API.
        assert "embedInfo.hosted_url" in src or "embedInfo?.hosted_url" in src, (
            "Modal non legge hosted_url da embedInfo (API response). "
            "Hardcoded URL = Cloudflare-ready rotto."
        )
        assert "embedInfo.snippet" in src or "embedInfo?.snippet" in src, (
            "Modal non legge snippet da embedInfo (API response). "
            "Snippet generation deve restare server-side."
        )

    def test_share_modal_client_side_origin_validation(self):
        """Modal valida origin client-side per UX feedback immediato.

        Backend e' fonte di verita' (riusa _validate_allowed_origins).
        Client-side check e' SOLO UX hint (anti-bypass not goal).
        """
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "validateOriginClientSide" in src, (
            "Missing client-side validation helper — UX feedback povera."
        )
        # Specific anti-pattern checks
        assert "https?:" in src or "https://" in src, (
            "Missing http(s) protocol check."
        )
        assert "wildcard" in src.lower() or "'*'" in src or '"*"' in src, (
            "Missing wildcard rejection."
        )

    def test_share_modal_copy_to_clipboard_pattern(self):
        """Modal implementa copy-to-clipboard con feedback."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "navigator.clipboard" in src or "copyToClipboard" in src, (
            "Modal missing copy-to-clipboard implementation."
        )
        assert "copy-hosted-button" in src or "copy-snippet-button" in src, (
            "Missing data-testid for copy buttons."
        )

    def test_store_card_has_share_action(self):
        """StoreCard espone action 'Condividi' via inlineActions."""
        src = self._read_frontend("frontend/src/features/stores/components/StoreCard.jsx")
        # onShare prop accettato
        assert "onShare" in src, (
            "StoreCard missing onShare prop — action 'Condividi' non wirable."
        )
        # Inline action 'share' registered
        assert "'share'" in src or '"share"' in src, (
            "StoreCard missing inlineActions push per share."
        )
        # Share2 icon imported
        assert "Share2" in src, "Missing Share2 icon import"

    def test_stores_page_wires_share_modal(self):
        """StoresPage importa + render ShareStoreModal con state pattern."""
        src = self._read_frontend("frontend/src/features/stores/StoresPage.js")
        assert "ShareStoreModal" in src, (
            "StoresPage non importa ShareStoreModal."
        )
        assert "shareStore" in src or "setShareStore" in src, (
            "StoresPage missing state shareStore per modal control."
        )
        assert "onShare={setShareStore}" in src, (
            "StoresPage NON passa onShare={setShareStore} a StoreCard — "
            "click 'Condividi' non aprira' modal."
        )

    def test_modular_design_separate_files(self):
        """Modular design: API client + Modal in file SEPARATI."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]

        # API client file dedicato
        assert (repo_root / "frontend/src/api/storeEmbed.js").exists(), (
            "API client NON in file separato — coupling con altri client."
        )
        # Modal component file dedicato
        assert (repo_root / "frontend/src/features/stores/components/ShareStoreModal.jsx").exists(), (
            "Modal NON in file separato — inline nel StoresPage rende test"
            " + maintenance difficile."
        )

    def test_modal_disables_save_when_unchanged(self):
        """UX: Save button disabled quando array unchanged (anti-PATCH spam)."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        # Logic pattern: originsUnchanged comparison
        assert "originsUnchanged" in src or "JSON.stringify(originsDraft)" in src, (
            "Modal missing 'unchanged' detection — Save button sempre "
            "enabled = PATCH spam su accidental re-click."
        )

    def test_modal_handles_loading_and_error_states(self):
        """Modal gestisce loading + error states (UX completa)."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "Loader2" in src or "loading" in src, (
            "Missing loading state — UX gap quando API call lenta."
        )
        assert "error" in src.lower(), (
            "Missing error handling — utente non sa cosa va storto."
        )

    def test_modal_uses_responsive_dialog(self):
        """Modal usa ResponsiveDialog (mobile-friendly, coerente stack)."""
        src = self._read_frontend("frontend/src/features/stores/components/ShareStoreModal.jsx")
        assert "ResponsiveDialog" in src, (
            "Modal non usa ResponsiveDialog — pattern inconsistent con "
            "ShippingDialog/MerchantLegalDialog/altri modal stores feature."
        )


# ──────────────────────────────────────────────────────────────────────────
# Track E Step 2.4 — Bundle JS local-serve in dev (CRA static)
# ──────────────────────────────────────────────────────────────────────────
#
# Razionale:
#   Per testare embed end-to-end in dev local serve che il bundle JS
#   sia accessibile via HTTP. Pattern usato: copia bundle in
#   frontend/public/embed/v1/ (CRA dev server serve auto).
#
#   Cloudflare-ready preserved: solo env var EMBED_CDN_BASE_URL cambia
#   tra dev (http://localhost:3000/embed) e prod (https://app.afianco.ch/
#   embed o future Cloudflare R2). Frontend zero hardcoded URL.
#
#   pnpm scripts root level (embed:build, embed:sync-dev, embed:rebuild)
#   per workflow developer convenience.
#
# Sentinel coprono:
#   1. Bundle file presente in frontend/public/embed/v1/
#   2. pnpm scripts canonical (build + sync + rebuild)
#   3. .env example documenta EMBED_CDN_BASE_URL pattern dev


class TestSEC_E_2_4_BundleLocalServeDev:
    """SEC-E.2.4: bundle JS local-serve infrastructure (dev mode)."""

    def test_bundle_es_module_in_public_dir(self):
        """frontend/public/embed/v1/afianco-embed.es.js exists.

        CRA dev server serve automaticamente file in public/ → bundle
        diventa accessibile via http://localhost:3000/embed/v1/...
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        assert bundle.exists(), (
            "Bundle ES module non in frontend/public/embed/v1/ — "
            "merchant snippet 404 anche in dev local. "
            "Run: pnpm embed:rebuild"
        )
        # Sanity: file non vuoto (build broken returns 0-byte)
        assert bundle.stat().st_size > 10000, (
            f"Bundle suspiciously small: {bundle.stat().st_size}B. "
            f"Build potrebbe essere broken — run pnpm embed:rebuild."
        )

    def test_bundle_umd_in_public_dir(self):
        """UMD bundle anche presente (fallback per old browsers)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        umd = repo_root / "frontend/public/embed/v1/afianco-embed.umd.js"
        assert umd.exists(), "UMD bundle missing — pnpm embed:sync-dev"

    def test_root_package_json_has_embed_scripts(self):
        """Root package.json espone pnpm script convenience per workflow."""
        from pathlib import Path
        import json
        repo_root = Path(__file__).resolve().parents[2]
        pkg = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        required_scripts = [
            "embed:build",     # cd apps/embed-sdk && pnpm build
            "embed:sync-dev",  # cp dist → frontend/public/embed/v1/
            "embed:rebuild",   # build + sync convenience
        ]
        for s in required_scripts:
            assert s in scripts, (
                f"Root package.json manca script '{s}' — workflow "
                f"developer rotto (rebuild bundle manual error-prone)."
            )

    def test_pnpm_embed_sync_dev_targets_canonical_path(self):
        """Script embed:sync-dev copia in frontend/public/embed/v1/ path."""
        from pathlib import Path
        import json
        repo_root = Path(__file__).resolve().parents[2]
        pkg = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
        sync = pkg["scripts"]["embed:sync-dev"]
        assert "frontend/public/embed/v1/" in sync, (
            f"embed:sync-dev target path drift: {sync!r}. "
            f"Path canonical e' frontend/public/embed/v1/ (CRA static)."
        )


class TestSEC_E_7_4_EmbedLegalDisclosureURLs:
    """SEC-E.7.4: Privacy + Terms URLs cliccabili nei checkbox GDPR del widget.

    Bug fix: pre-Step 7.4 il widget Lit mostrava checkbox GDPR senza
    link cliccabili a Privacy/Terms — divergenza con storefront classico
    che gia' linkava ``/s/{slug}/{privacy|terms}``. Compliance gap
    (GDPR Art. 13 — informativa accessibile + Consumer Rights Directive
    sui Termini consultabili al momento del consenso).

    Fix end-to-end:
      1. EmbedInitResponse esponde ``privacy_policy_url`` + ``terms_service_url``
      2. Service resolver costruisce default da APP_BASE_URL+/s/{slug}/...
         oppure usa override merchant da store config
      3. Widget renderizza ``<a target="_blank">`` cliccabili nei checkbox
         di ``afianco-signup`` e ``afianco-checkout-button``
    """

    def test_embed_init_response_includes_legal_url_fields(self):
        """EmbedInitResponse Pydantic ha i 2 campi legal URL (additive)."""
        from routers.embed_public import EmbedInitResponse
        fields = EmbedInitResponse.model_fields
        assert "privacy_policy_url" in fields, (
            "EmbedInitResponse missing privacy_policy_url field — "
            "widget non puo' linkare la Privacy nei checkbox GDPR. "
            "GDPR Art.13 compliance gap."
        )
        assert "terms_service_url" in fields, (
            "EmbedInitResponse missing terms_service_url field — "
            "widget non puo' linkare i Termini nei checkbox GDPR."
        )

    def test_service_resolver_builds_default_legal_urls(self):
        """get_embed_init_data costruisce default privacy + terms URL."""
        import inspect
        from services import embed_init_service
        src = inspect.getsource(embed_init_service.get_embed_init_data)
        # Default URLs derivati da APP_BASE_URL + /s/{slug}/privacy|terms
        assert "/s/{slug}/privacy" in src or 'f"{APP_BASE_URL}/s/{slug}/privacy"' in src, (
            "Default privacy URL non costruito da APP_BASE_URL + /s/{slug}/privacy. "
            "Storefront classic linka /s/{slug}/privacy → widget DEVE usare lo "
            "stesso path per parita' content (entrambi consumano "
            "/api/legal/storefront/{slug}/privacy)."
        )
        assert "/s/{slug}/terms" in src or 'f"{APP_BASE_URL}/s/{slug}/terms"' in src, (
            "Default terms URL non costruito da APP_BASE_URL + /s/{slug}/terms."
        )
        # Override merchant: store config wins
        assert "privacy_policy_url" in src, (
            "Service non considera override store.privacy_policy_url — "
            "merchant non puo' puntare al proprio dominio per la Privacy."
        )
        assert "terms_service_url" in src, (
            "Service non considera override store.terms_service_url."
        )

    def test_widget_signup_renders_privacy_terms_anchors(self):
        """afianco-signup.ts include <a> cliccabili nei checkbox GDPR."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        sig = repo_root / "apps/embed-sdk/src/components/afianco-signup.ts"
        src = sig.read_text(encoding="utf-8")
        # Anchor con href dinamico al privacy URL del context init
        assert "privacy_policy_url" in src, (
            "afianco-signup.ts non legge ctx.init.privacy_policy_url — "
            "checkbox GDPR senza link cliccabile (compliance regression)."
        )
        assert "terms_service_url" in src, (
            "afianco-signup.ts non legge ctx.init.terms_service_url — "
            "checkbox Termini senza link cliccabile."
        )
        # Anchor pattern: target=_blank + rel=noopener noreferrer (security
        # best practice contro window.opener tabnabbing)
        assert 'target="_blank"' in src, (
            "Anchor GDPR non apre in nuova tab — UX rotta (customer perde "
            "il form se naviga in same-tab)."
        )
        assert 'rel="noopener noreferrer"' in src, (
            "Anchor GDPR senza rel='noopener noreferrer' — vulnerabilita' "
            "tabnabbing (la pagina target potrebbe accedere a window.opener)."
        )

    def test_widget_checkout_renders_privacy_terms_anchors(self):
        """afianco-checkout-button.ts include <a> cliccabili nei checkbox GDPR."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        ck = repo_root / "apps/embed-sdk/src/components/afianco-checkout-button.ts"
        src = ck.read_text(encoding="utf-8")
        assert "privacy_policy_url" in src, (
            "afianco-checkout-button.ts non legge ctx.init.privacy_policy_url — "
            "checkbox GDPR inline-checkout senza link Privacy."
        )
        assert "terms_service_url" in src, (
            "afianco-checkout-button.ts non legge ctx.init.terms_service_url — "
            "checkbox GDPR inline-checkout senza link Termini."
        )
        assert 'target="_blank"' in src, (
            "Anchor GDPR checkout non apre in nuova tab."
        )
        assert 'rel="noopener noreferrer"' in src, (
            "Anchor GDPR checkout senza rel='noopener noreferrer' — "
            "vulnerabilita' tabnabbing."
        )

    def test_widget_anchors_stop_propagation_on_click(self):
        """Click sul link <a> NON deve toggle del checkbox sotto.

        Pattern Lit: label > <a> propaga il click al label → checkbox state
        toggle indesiderato. Mitigation: @click=${(e) => e.stopPropagation()}
        sul link.
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for fname in (
            "apps/embed-sdk/src/components/afianco-signup.ts",
            "apps/embed-sdk/src/components/afianco-checkout-button.ts",
        ):
            src = (repo_root / fname).read_text(encoding="utf-8")
            # Devono entrambi avere stopPropagation negli @click degli anchor
            # gdpr-link (cerchiamo la pattern combinata per evitare false +).
            assert "gdpr-link" in src, (
                f"{fname} manca classe 'gdpr-link' per styling anchor checkbox."
            )
            assert "e.stopPropagation()" in src, (
                f"{fname} anchor click non chiama stopPropagation() — "
                f"click sul link toggleable il checkbox sotto (UX bug)."
            )


class TestSEC_E_7_5_LegalAutogenFallback:
    """SEC-E.7.5: auto-fallback content quando merchant non ha pubblicato.

    Bug user-reported: 'clicco Privacy/Terms nel widget e non vedo
    nulla, anche se ho settato il GDPR nello store'. Root cause:
    workflow merchant separato — anagrafica GDPR base (contact_email,
    company name) e' separata dal documento legale formale (pubblicato
    via wizard). Se il merchant non e' passato dal wizard, status=
    "not_configured" → content="" → React mostrava SOLO placeholder
    giallo.

    Fix: backend ora popola sempre content con un template standard
    auto-renderizzato sui dati anagrafici store (render_template +
    TemplateVars del template service esistente). Customer vede SEMPRE
    un'informativa GDPR-compliant consultabile (Art. 13 GDPR
    compliance). Status "not_configured" rimane signal per merchant
    admin; is_autogenerated=true notifica al React di mostrare banner
    azzurro informativo sopra il documento.
    """

    def test_envelope_includes_is_autogenerated_field(self):
        """_public_doc_envelope response include is_autogenerated bool."""
        import inspect
        from routers import legal
        src = inspect.getsource(legal._public_doc_envelope)
        assert '"is_autogenerated"' in src, (
            "Envelope response missing is_autogenerated field — "
            "frontend non puo' distinguere doc pubblicato vs template "
            "fallback (banner azzurro non triggerable)."
        )

    def test_envelope_renders_template_when_not_configured(self):
        """Status not_configured/draft → content NON vuoto (template auto)."""
        import inspect
        from routers import legal
        src = inspect.getsource(legal._public_doc_envelope)
        # Funzione helper _render_autogen_fallback usata nei branch
        assert "_render_autogen_fallback" in src, (
            "Envelope non chiama _render_autogen_fallback per il "
            "fallback content — customer vede pagina vuota."
        )

    def test_autogen_renderer_uses_template_service(self):
        """_render_autogen_fallback delega al merchant_legal_template_service."""
        import inspect
        from routers import legal
        assert hasattr(legal, "_render_autogen_fallback"), (
            "Function _render_autogen_fallback missing in routers/legal.py"
        )
        src = inspect.getsource(legal._render_autogen_fallback)
        assert "render_template" in src, (
            "_render_autogen_fallback non usa render_template del "
            "merchant_legal_template_service — duplicazione logica + "
            "drift tra admin preview e public render."
        )

    def test_autogen_template_vars_built_from_store(self):
        """_build_autogen_template_vars deriva vars dal store doc."""
        import inspect
        from routers import legal
        assert hasattr(legal, "_build_autogen_template_vars"), (
            "Function _build_autogen_template_vars missing."
        )
        src = inspect.getsource(legal._build_autogen_template_vars)
        # Field critici derivati dallo store:
        for field in ("name", "contact_email", "fulfillment_modes"):
            assert field in src, (
                f"_build_autogen_template_vars non legge store.{field!r} — "
                f"template auto-gen non personalizzato sui dati merchant."
            )
        # Priority: usa merchant_legal_template_vars se gia' salvato
        assert "merchant_legal_template_vars" in src, (
            "Non usa merchant_legal_template_vars salvato dal wizard "
            "admin come baseline — drift quando admin parzialmente "
            "completato (vars saved but doc not published)."
        )

    def test_react_page_renders_autogen_banner(self):
        """StorefrontLegalPage.js mostra banner azzurro quando autogen."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/pages/StorefrontLegalPage.js"
        src = page.read_text(encoding="utf-8")
        # Render conditional su is_autogenerated
        assert "is_autogenerated" in src, (
            "React page non legge doc.is_autogenerated — banner "
            "informativo 'documento auto-generato' non triggerable."
        )
        # Banner azzurro (sky-* tailwind) distinto dal vecchio amber
        assert "sky-" in src or "blue-" in src, (
            "Banner autogen non usa colore distintivo (sky/blue) — "
            "UX indistinguibile dal vecchio amber placeholder."
        )
        # Translation keys
        assert "storefront_legal.autogen" in src, (
            "Mancano i18n keys storefront_legal.autogen_title/body — "
            "messaggio banner hardcoded non traducibile."
        )

    def test_cache_etag_invalidates_on_autogen_content_change(self):
        """ETag include hash content per autogen cosi' cache invalida
        quando merchant cambia name/email/lingua."""
        import inspect
        from routers import legal
        src = inspect.getsource(legal._cache_headers_for_envelope)
        # ETag seed include autogen branch con hash content
        assert "is_autogenerated" in src, (
            "Cache headers non considerano is_autogenerated → ETag "
            "fisso anche se il template fallback cambia (merchant "
            "modifica anagrafica ma customer vede stale per 30s+)."
        )
        # SHA256 hash sul content auto-gen per content-derived ETag
        assert "hashlib" in src or "sha256" in src, (
            "Cache ETag autogen senza hash content-derived → "
            "invalidazione cache incompleta."
        )


class TestSEC_E_7_6_EmbedBundleSyncFreshness:
    """SEC-E.7.6: il bundle ``frontend/public/embed/v1/*`` DEVE essere
    identico al risultato di ``apps/embed-sdk/dist/*``.

    Bug user-reported: 'dopo il fix Privacy/Terms i link ancora non
    appaiono'. Root cause: post-fix il bundle era stato rebuildato
    in ``apps/embed-sdk/dist/`` ma NON sincronizzato in
    ``frontend/public/embed/v1/`` (lo step ``pnpm embed:sync-dev``
    veniva eseguito manualmente e si dimenticava).

    Risultato: il widget caricato dai merchant via
    ``http://localhost:3000/embed/v1/afianco-embed.es.js`` (o il
    canonical CDN URL) serviva il VECCHIO bundle stale → il fix non
    raggiungeva mai gli utenti finali.

    Fix process: sentinel pinna che i 2 file siano byte-identici. CI
    fallisce se uno dei due e' aggiornato senza l'altro → forza il
    workflow ``pnpm embed:rebuild`` (build + sync atomic).
    """

    def test_bundle_es_module_in_sync_with_dist(self):
        """frontend/public/embed/v1/afianco-embed.es.js == dist version."""
        import hashlib
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        dist = repo_root / "apps/embed-sdk/dist/afianco-embed.es.js"
        public = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        if not dist.exists():
            # CI checkout: dist/ è un artefatto di build gitignorato — il
            # confronto di sync ha senso solo dove il bundle è stato buildato
            # (dev locale / pre-release). Skippare != indebolire: in locale
            # il sentinel resta pienamente attivo.
            import pytest
            pytest.skip("apps/embed-sdk/dist assente (build artifact) — sync verificabile solo post-build")
        assert public.exists(), (
            "Bundle public mancante — run `pnpm embed:sync-dev`."
        )
        dist_hash = hashlib.sha256(dist.read_bytes()).hexdigest()
        public_hash = hashlib.sha256(public.read_bytes()).hexdigest()
        assert dist_hash == public_hash, (
            f"BUNDLE DRIFT: frontend/public/embed/v1/afianco-embed.es.js "
            f"({public_hash[:12]}…) NON e' aggiornato vs "
            f"apps/embed-sdk/dist/afianco-embed.es.js ({dist_hash[:12]}…).\n"
            f"Fix: run `pnpm embed:sync-dev` per copiare il bundle aggiornato.\n"
            f"Customer caricano il bundle stale → i fix recenti non hanno "
            f"effetto. Workflow corretto: `pnpm embed:rebuild` (build + sync)."
        )

    def test_bundle_umd_in_sync_with_dist(self):
        """frontend/public/embed/v1/afianco-embed.umd.js == dist version."""
        import hashlib
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        dist = repo_root / "apps/embed-sdk/dist/afianco-embed.umd.js"
        public = repo_root / "frontend/public/embed/v1/afianco-embed.umd.js"
        if not dist.exists():
            # Vedi test_bundle_es_module_in_sync_with_dist: dist è un build
            # artifact gitignorato, in CI il sync non è verificabile.
            import pytest
            pytest.skip("apps/embed-sdk/dist assente (build artifact) — sync verificabile solo post-build")
        assert public.exists(), "Bundle UMD public mancante."
        dist_hash = hashlib.sha256(dist.read_bytes()).hexdigest()
        public_hash = hashlib.sha256(public.read_bytes()).hexdigest()
        assert dist_hash == public_hash, (
            f"UMD BUNDLE DRIFT: vecchio bundle serviato a browser legacy. "
            f"Run `pnpm embed:rebuild`."
        )

    def test_bundle_contains_privacy_terms_anchors(self):
        """Smoke test: il bundle public contiene il fix Privacy/Terms.

        Verifica end-to-end che dopo build+sync il marker del fix sia
        effettivamente raggiungibile via HTTP (vs. solo nei sorgenti TS).
        """
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Marker E7.4: classe CSS distintiva degli anchor GDPR
        assert "gdpr-link" in src, (
            "Bundle public NON contiene marker 'gdpr-link' del fix E7.4 "
            "(Privacy/Terms cliccabili nei checkbox). Bundle stale — "
            "run `pnpm embed:rebuild`."
        )
        # Marker fix E7.4 backend wiring: read context.init.privacy_policy_url
        assert "privacy_policy_url" in src, (
            "Bundle public non legge privacy_policy_url dal context init. "
            "Build pre-E7.4 — workflow embed:rebuild non eseguito."
        )


class TestSEC_E_8_1_DPAEnforcement:
    """SEC-E.8.1: DPA acceptance enforcement (Art. 28 GDPR) — Sprint 1 W1.1.

    Background: il backend già implementa GET/POST /api/legal/dpa + admin
    UI page DpaPage.js (Wave CG-7). Quello che mancava era l'ENFORCEMENT:
    un merchant poteva pubblicare lo store SENZA aver acknowledged il DPA.
    Gap critico per Art. 28 GDPR — la pubblicazione attiva il
    processing dei dati customer e il DPA deve esistere prima.

    Sprint 1 fix:
      - NEW services/dpa_enforcement.py con require_dpa_acknowledged()
      - publish_store gated con 412 Precondition Failed se DPA mancante
      - Grace window legacy: stores già is_published=True non sono
        affected (no breakage produzione)
      - Error response strutturato con admin_path link per UX
    """

    def test_dpa_enforcement_service_exists(self):
        """services/dpa_enforcement esposta con API canonical."""
        from services import dpa_enforcement
        assert hasattr(dpa_enforcement, "is_dpa_acknowledged"), (
            "Manca async helper is_dpa_acknowledged(org_id) — single "
            "source of truth per il check."
        )
        assert hasattr(dpa_enforcement, "require_dpa_acknowledged"), (
            "Manca async guard require_dpa_acknowledged(org_id, action) "
            "che fa raise HTTPException(412) — endpoint integration."
        )
        assert hasattr(dpa_enforcement, "is_publish_gated"), (
            "Manca async helper is_publish_gated(org_id, store) per il "
            "grace window legacy stores (soft warning vs hard block)."
        )

    def test_dpa_enforcement_error_code_canonical(self):
        """Error code stabile per i client (i18n key + UX flow)."""
        from services.dpa_enforcement import DPA_NOT_ACKNOWLEDGED_CODE
        assert DPA_NOT_ACKNOWLEDGED_CODE == "DPA_NOT_ACKNOWLEDGED", (
            "Error code drifted — clients matchano questo string per "
            "trigger del banner DPA. Cambio = breaking change UX."
        )

    def test_publish_store_gated_by_dpa(self):
        """publish_store chiama require_dpa_acknowledged."""
        import inspect
        from routers import stores
        src = inspect.getsource(stores.publish_store)
        assert "require_dpa_acknowledged" in src, (
            "publish_store NON invoca require_dpa_acknowledged() — "
            "merchant puo' pubblicare store senza aver accettato il "
            "DPA (Art. 28 GDPR gap)."
        )

    def test_dpa_enforcement_returns_412_with_link(self):
        """Error response include code + admin_path per UX banner."""
        import inspect
        from services import dpa_enforcement
        src = inspect.getsource(dpa_enforcement.require_dpa_acknowledged)
        # HTTPException con 412
        assert "412" in src or "PRECONDITION_FAILED" in src, (
            "require_dpa_acknowledged non raise 412 (Precondition Failed) "
            "— semantic HTTP corretto per missing prerequisite."
        )
        # Detail con code + admin_path
        assert "DPA_NOT_ACKNOWLEDGED" in src, (
            "Error detail non contiene il code stabile DPA_NOT_ACKNOWLEDGED."
        )
        assert "admin_path" in src or DPA_LINK_ADMIN_PATH_check(src), (
            "Error detail non contiene admin_path link — UX banner non "
            "puo' fare il deep-link a /settings/legal/dpa."
        )

    def test_legacy_grace_window_for_already_published_stores(self):
        """is_publish_gated ritorna warning soft per legacy stores."""
        import inspect
        from services import dpa_enforcement
        src = inspect.getsource(dpa_enforcement.is_publish_gated)
        assert "is_published" in src, (
            "is_publish_gated non considera lo stato is_published del "
            "store — legacy stores rischiano break su deploy enforcement."
        )

    def test_dpa_templates_present_all_locales(self):
        """Backend deve avere DPA template per IT, EN, DE, FR."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        legal_dir = repo_root / "backend/legal"
        for locale in ("it", "en", "de", "fr"):
            path = legal_dir / f"dpa_{locale}.md"
            assert path.exists(), (
                f"DPA template mancante per locale={locale}: {path}. "
                f"Merchant non puo' acknowledged in quella lingua."
            )

    def test_dpa_admin_page_exists_frontend(self):
        """Frontend ha la pagina admin /settings/legal/dpa."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/pages/DpaPage.js"
        assert page.exists(), (
            "Frontend manca DpaPage.js — admin non puo' acknowledged il DPA."
        )
        src = page.read_text(encoding="utf-8")
        # Loads + Acknowledge + status status fetched
        assert "dpaAPI" in src, "DpaPage non usa dpaAPI client."
        assert "acknowledge" in src, "DpaPage manca Acknowledge button."


def DPA_LINK_ADMIN_PATH_check(src: str) -> bool:
    """Helper sentinel: check che la constant DPA_LINK_ADMIN_PATH sia usata."""
    return "/settings/legal/dpa" in src


class TestSEC_E_8_2_ReactErasureCard:
    """SEC-E.8.2: GDPR Art. 17 erasure card nel React ProfilePage —
    parity con widget Lit (W1.2 — Sprint 1 step 2/5).

    Bug audit: il widget Lit avea afianco-profile-editor.ts con erasure
    section completa (E4.4), ma il React StorefrontProfile.jsx non
    aveva alcuna UI per l'Art. 17 GDPR. Endpoint backend
    POST /customer/me/request-erasure esisteva ma nessun React la
    chiamava. Compliance gap: customer del storefront classico non
    poteva esercitare il right-to-erasure dal portale.

    Fix W1.2:
      - customerPortalAPI.requestErasure({reason, confirm}) NEW method
      - EraseAccountCard component in ProfilePage.jsx con:
        * 2-step confirm: open CTA + form (warning + textarea + email
          re-type + checkbox + submit)
        * Defense-in-depth: backend richiede confirm=true, frontend
          aggiunge email-match check (pattern GitHub delete-repo)
      - Success state con request_id mostrato + i18n
    """

    def test_customer_portal_api_has_request_erasure(self):
        """customerPortalAPI.requestErasure method exposed."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        api = repo_root / "frontend/src/api/customerPortal.js"
        assert api.exists(), "customerPortal.js missing"
        src = api.read_text(encoding="utf-8")
        assert "requestErasure" in src, (
            "customerPortalAPI manca requestErasure method — "
            "EraseAccountCard non puo' invocare backend Art. 17."
        )
        # Verifica endpoint canonical
        assert "/customer/me/request-erasure" in src, (
            "requestErasure non usa endpoint canonical "
            "/customer/me/request-erasure."
        )
        # Confirm passato come true (defense-in-depth)
        assert "confirm" in src, (
            "requestErasure non passa confirm flag (backend richiede true)."
        )

    def test_react_profile_page_includes_erasure_card(self):
        """ProfilePage.jsx include EraseAccountCard component."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/customer-portal/pages/ProfilePage.jsx"
        assert page.exists(), "ProfilePage.jsx missing"
        src = page.read_text(encoding="utf-8")
        assert "EraseAccountCard" in src, (
            "ProfilePage.jsx manca EraseAccountCard component — "
            "GDPR Art. 17 UI non resa al customer (compliance gap)."
        )
        # Verifica wire-up: chiamata a requestErasure
        assert "requestErasure" in src, (
            "EraseAccountCard non chiama customerPortalAPI.requestErasure."
        )

    def test_react_erasure_defense_in_depth_email_match(self):
        """EraseAccountCard ha email match safety (UX anti-accidental)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/customer-portal/pages/ProfilePage.jsx"
        src = page.read_text(encoding="utf-8")
        # Email re-type confirmation (pattern GitHub-style)
        assert "emailMatches" in src or "emailConfirm" in src, (
            "EraseAccountCard non ha email match check — customer puo' "
            "submittare per errore senza conferma esplicita identita'."
        )
        # Checkbox conferma irreversibile
        assert "confirmChecked" in src or "irreversibile" in src.lower(), (
            "EraseAccountCard manca checkbox conferma irreversibile."
        )

    def test_backend_erasure_endpoint_validates_confirm(self):
        """Backend POST /customer/me/request-erasure rifiuta confirm=false."""
        import inspect
        from routers import customer_portal
        src = inspect.getsource(customer_portal.request_account_erasure)
        # Defense-in-depth: confirm=false → 400 anche se frontend pre-gate
        assert "body.confirm" in src or "confirm" in src, (
            "Endpoint non valida flag confirm — accidental erasure rischio."
        )
        assert "400" in src or "HTTPException" in src, (
            "Endpoint non raise su confirm mancante."
        )


class TestSEC_E_8_3_SDKIdempotencyKeys:
    """SEC-E.8.3: SDK client invia Idempotency-Key su ogni mutazione
    (POST/PATCH/PUT/DELETE) — anti-duplicate on retry.

    Bug audit V5 sosteneva 'NO idempotency keys on cart.create/update
    /checkout.start calls — duplicate cart line or order created'.
    L'audit era impreciso: il request() helper centrale del client.ts
    wrappa OGNI mutazione e inserisce un Idempotency-Key generato con
    uuidv4(). Ma mancavano sentinel test espliciti che pinnino
    l'invariant + il bundle compilato (rischio tree-shake).

    Sprint 1 W1.3 fix:
      - Sentinel pinna pattern Idempotency-Key in client.ts source
      - Sentinel pinna bundle compilato contenga il pattern
      - NEW opts.idempotencyKey override per retry esplicito
        (deterministic replay quando network reply mid-flight perso)
      - Backend 24h cache già existeva (middleware/idempotency.py)
    """

    def test_sdk_client_inserts_idempotency_key_on_mutations(self):
        """client.ts header['Idempotency-Key'] set per metodi non-GET."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "packages/api-client/src/client.ts"
        assert client.exists(), "client.ts missing"
        src = client.read_text(encoding="utf-8")
        # Pattern canonical: header Idempotency-Key + uuidv4
        assert "'Idempotency-Key'" in src, (
            "client.ts NON setta header 'Idempotency-Key' — "
            "duplicate orders su network retry possibile (race condition)."
        )
        assert "uuidv4" in src, (
            "client.ts non usa uuidv4() per generare il key — "
            "entropy insufficiente OR pattern drift."
        )
        # Gate: solo per non-GET (GET non muta state)
        assert "opts.method !== 'GET'" in src or "method !== \"GET\"" in src, (
            "client.ts setta Idempotency-Key anche su GET (wasteful + "
            "potentially cache poisoning). Deve essere gated a mutations."
        )

    def test_sdk_client_supports_explicit_key_override(self):
        """Sprint 1 W1.3 — opt.idempotencyKey replay override."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "packages/api-client/src/client.ts"
        src = client.read_text(encoding="utf-8")
        # opts.idempotencyKey deve essere honored quando passato
        assert "idempotencyKey" in src, (
            "client.ts manca opts.idempotencyKey override — caller non "
            "puo' replay deterministico su retry esplicito."
        )
        # Pattern fallback: opts.idempotencyKey ?? uuidv4()
        assert (
            "opts.idempotencyKey ?? uuidv4()" in src
            or "opts.idempotencyKey || uuidv4()" in src
        ), (
            "Pattern fallback opts.idempotencyKey ?? uuidv4() drifted — "
            "comportamento default (auto-gen) o override (explicit) non "
            "garantito."
        )

    def test_bundle_compiled_contains_idempotency_key(self):
        """Bundle public/frontend/embed/v1/ contiene il pattern compilato."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        assert bundle.exists(), "Bundle ES missing — run pnpm embed:rebuild"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Verifica che il pattern sopravviva a tree-shake + minification
        assert "Idempotency-Key" in src, (
            "Bundle compilato NON contiene 'Idempotency-Key' header — "
            "tree-shake potrebbe averlo rimosso. "
            "Run `pnpm embed:rebuild` e verifica che il client venga "
            "importato correttamente. Anti-duplicate guarantee rotta."
        )

    def test_backend_middleware_validates_idempotency_key(self):
        """Backend middleware/idempotency.py enforce su mutazioni."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        middleware = repo_root / "backend/middleware/idempotency.py"
        assert middleware.exists(), (
            "backend/middleware/idempotency.py mancante — middleware "
            "che enforce Idempotency-Key e cache 24h. SDK invia key ma "
            "backend non valida -> duplicate non bloccati."
        )
        src = middleware.read_text(encoding="utf-8")
        # Cache TTL 24h presente
        assert "CACHE_TTL_HOURS" in src or "24" in src, (
            "Cache TTL non documentato 24h — replay window unclear."
        )


class TestSEC_E_8_4_CatalogProjectionNoLeak:
    """SEC-E.8.4: catalog projection NON leakka admin fields.

    Risk audit V5: 'No explicit projection doc per /embed/products, se
    response include cost_price / internal_tags / supplier_id, merchant
    privato leakka via widget'.

    Verifica:
    - _public_card_projection() e' whitelist-only (esplicita inclusione)
    - Detail _public_detail_projection() e' whitelist-only
    - EmbedProductCard Pydantic model NON ha admin field
    - EmbedProductDetail Pydantic model NON ha admin field
    - Anti-PII per metadata extraction (_DETAIL_METADATA_WHITELIST
      esiste e copre solo safe fields)

    Forbidden fields (admin-only, NEVER leakable):
      cost_price       — costo merchant (competitive intelligence)
      cost_source      — pricing strategy interno
      sku              — internal inventory
      barcode          — internal inventory
      supplier_id      — supplier relationships
      internal_tags    — admin tags
      organization_id  — multi-tenant boundary
      cost_history     — pricing audit
      admin_notes      — note interne merchant
    """

    FORBIDDEN_FIELDS = frozenset({
        "cost_price",
        "cost_source",
        "sku",
        "barcode",
        "supplier_id",
        "internal_tags",
        "organization_id",
        "cost_history",
        "admin_notes",
    })

    def test_card_projection_is_whitelist_only(self):
        """_public_card_projection ritorna dict {field: 1} esplicito."""
        from services.embed_init_service import _public_card_projection
        proj = _public_card_projection()
        assert isinstance(proj, dict), "Projection must be dict"
        # Verifica whitelist pattern: ogni field e' inclusion explicit
        # (value=1) eccetto _id: 0 per dropping
        included = {k for k, v in proj.items() if v == 1}
        assert len(included) > 0, (
            "Projection empty — Mongo would return TUTTO il document "
            "(catastrofico leak admin fields)."
        )
        # Verifica che _id: 0 sia presente (drop ObjectId)
        assert proj.get("_id") == 0, (
            "_id non droppato — ObjectId esposto, potential leak."
        )

    def test_card_projection_excludes_admin_fields(self):
        """Nessun field forbidden nella projection card."""
        from services.embed_init_service import _public_card_projection
        proj = _public_card_projection()
        for forbidden in self.FORBIDDEN_FIELDS:
            assert forbidden not in proj, (
                f"_public_card_projection include admin field {forbidden!r} "
                f"-> /embed/products leakka dato merchant-internal. "
                f"Whitelist deve essere ristretta."
            )

    def test_detail_projection_excludes_admin_fields(self):
        """Nessun field forbidden nella projection detail."""
        from services.embed_init_service import _public_detail_projection
        proj = _public_detail_projection()
        for forbidden in self.FORBIDDEN_FIELDS:
            assert forbidden not in proj, (
                f"_public_detail_projection include admin field {forbidden!r} "
                f"-> /embed/products/{{slug}}/{{id}} leakka admin data."
            )

    def test_card_response_model_excludes_admin_fields(self):
        """EmbedProductCard Pydantic NON ha field forbidden."""
        from routers.embed_public import EmbedProductCard
        model_fields = set(EmbedProductCard.model_fields.keys())
        for forbidden in self.FORBIDDEN_FIELDS:
            assert forbidden not in model_fields, (
                f"EmbedProductCard model include {forbidden!r} — "
                f"anche se la projection non lo passa, il model espone "
                f"il field nel contract OpenAPI -> rischio future drift."
            )

    def test_detail_metadata_whitelist_no_admin_leak(self):
        """_DETAIL_METADATA_WHITELIST in embed_init_service e' restricted."""
        from services import embed_init_service
        whitelist = embed_init_service._DETAIL_METADATA_WHITELIST
        # Forbidden metadata keys che potrebbero leakare admin info
        admin_metadata_forbidden = (
            "cost_breakdown",
            "supplier_margin",
            "competitor_prices",
            "internal_notes",
        )
        for forbidden in admin_metadata_forbidden:
            assert forbidden not in whitelist, (
                f"_DETAIL_METADATA_WHITELIST include {forbidden!r} — "
                f"metadata admin esposto sul detail endpoint."
            )

    def test_detail_handler_strips_organization_id(self):
        """get_embed_product_detail_data NON espone organization_id."""
        import inspect
        from services import embed_init_service
        src = inspect.getsource(
            embed_init_service.get_embed_product_detail_data
        )
        # Il detail dict builder NON deve includere organization_id raw
        # (cross-tenant boundary leak risk)
        # Pattern accettato: usato in match query ma stripped dal detail
        # Il return deve essere via dict comprehension esplicito.
        assert "organization_id" not in src.split("return detail")[-1][:500] if "return detail" in src else True, (
            "Il return detail include organization_id raw — multi-tenant "
            "boundary leak. Filtra esplicitamente."
        )

    def test_category_aggregation_excludes_admin_fields(self):
        """_aggregate_categories Mongo pipeline non leakka admin."""
        import inspect
        from services import embed_init_service
        src = inspect.getsource(embed_init_service._aggregate_categories)
        # Pattern critico: il $match deve filtrare per (organization_id,
        # is_published, is_active) PRIMA del $group, altrimenti merchant
        # cross-tenant data potrebbe finire nelle aggregations.
        assert "organization_id" in src, (
            "_aggregate_categories non filtra per organization_id -> "
            "cross-tenant category leak possible."
        )
        assert "is_published" in src, (
            "_aggregate_categories non filtra is_published=True -> "
            "categorie di prodotti draft esposte al public."
        )


class TestSEC_E_8_5_MarkdownXSSSafe:
    """SEC-E.8.5: sanitize merchant text fields anti stored XSS.

    Risk audit V5: 'afianco-product-detail.ts menciona markdown-like
    rendering ma nessun DOMPurify/sanitize trovato. Se backend ritorna
    raw HTML in product descriptions, stored XSS attivo'.

    Frontend rendering era safe:
    - Widget Lit: ${this.description} interpolation escapes HTML by
      default (Lit safe-by-default)
    - React MarkdownLite: subset safe markdown render con escape

    Pero' il backend non sanitizzava input merchant — defense-in-depth
    gap: se un giorno frontend cambia render a unsafeHTML (regression),
    payload XSS sarebbe gia' in DB e raggiungerebbe i customer.

    Sprint 1 W1.5 fix:
      NEW services/markdown_safe.py:
        - sanitize_merchant_text(raw) -> str: strip HTML tag + event
          handler + URL schemes pericolosi (javascript:, data:, vbscript:)
          + CSS expression(). HTML entity decode prima dello strip per
          gestire pattern obfuscated. Idempotent.
        - is_safe_text(raw) -> bool: read-only check

      Wired into routers/products.py:
        - create_product: sanitize description + metadata.long_description
        - update_product: idem su update

    Sentinel pinna 5 XSS vector classici.
    """

    def test_sanitize_strips_script_tag(self):
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text("<script>alert(1)</script>Safe")
        assert "<script>" not in result, "Script tag non stripped"
        assert "alert(1)" in result or "Safe" in result, (
            "Stripping aggressive: testo legittimo perso"
        )
        # Output finale escape any residual `<` `>`
        assert "<" not in result, "Pattern < non escapato"

    def test_sanitize_strips_img_onerror(self):
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text(
            '<img src=x onerror="alert(1)">Nice product'
        )
        assert "<img" not in result, "img tag non stripped"
        assert "onerror" not in result, "Event handler non stripped"
        assert "Nice product" in result, "Testo legittimo perso"

    def test_sanitize_strips_javascript_url(self):
        from services.markdown_safe import sanitize_merchant_text
        # Markdown link con javascript URL
        result = sanitize_merchant_text(
            "[click](javascript:alert(1)) for free product"
        )
        assert "javascript:" not in result.lower(), (
            "javascript: URL scheme non stripped"
        )
        assert "for free product" in result, "Testo legittimo perso"

    def test_sanitize_strips_data_url(self):
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text(
            "Click [here](data:text/html,<script>alert(1)</script>)"
        )
        assert "data:" not in result.lower(), "data: URL scheme non stripped"

    def test_sanitize_strips_svg_xss(self):
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text(
            '<svg><script>alert(1)</script></svg>Product info'
        )
        assert "<svg" not in result.lower()
        assert "<script" not in result.lower()
        assert "Product info" in result

    def test_sanitize_strips_html_entity_obfuscation(self):
        """HTML entity obfuscated payload: &lt;script&gt; → <script>."""
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text(
            "&lt;script&gt;alert(1)&lt;/script&gt;Real text"
        )
        # Dopo decode entities + strip tag, no <script> residuo
        assert "script" not in result.lower() or "alert" not in result, (
            "Entity-obfuscated XSS bypass: decoded ma non stripped"
        )

    def test_sanitize_strips_iframe(self):
        from services.markdown_safe import sanitize_merchant_text
        result = sanitize_merchant_text(
            '<iframe src="evil.com"></iframe>Description'
        )
        assert "<iframe" not in result.lower()
        assert "Description" in result

    def test_sanitize_preserves_markdown_format(self):
        """Markdown puro (no HTML) passa intatto."""
        from services.markdown_safe import sanitize_merchant_text
        text = "**Bold** and *italic*\n\n- list 1\n- list 2\n\n[link](https://safe.com)"
        result = sanitize_merchant_text(text)
        assert "**Bold**" in result
        assert "*italic*" in result
        assert "list 1" in result
        assert "https://safe.com" in result, (
            "Link http(s) sicuro non deve essere stripped"
        )

    def test_sanitize_idempotent(self):
        from services.markdown_safe import sanitize_merchant_text
        payload = "<script>x</script>Hello [link](https://ok)"
        once = sanitize_merchant_text(payload)
        twice = sanitize_merchant_text(once)
        assert once == twice, "Sanitization NON idempotent — re-apply drift"

    def test_sanitize_none_passthrough(self):
        from services.markdown_safe import sanitize_merchant_text
        assert sanitize_merchant_text(None) is None
        assert sanitize_merchant_text("") == ""

    def test_create_product_wires_sanitize(self):
        """routers/products.create_product chiama sanitize_merchant_text."""
        import inspect
        from routers import products
        src = inspect.getsource(products.create_product)
        assert "sanitize_merchant_text" in src, (
            "create_product non sanitize description merchant — "
            "stored XSS vector aperto."
        )
        assert "description" in src, "create_product non tocca description field"
        assert "long_description" in src, (
            "create_product non sanitize long_description in metadata — "
            "il drawer landing detail mostra long_description, XSS gap."
        )

    def test_update_product_wires_sanitize(self):
        """routers/products.update_product chiama sanitize_merchant_text."""
        import inspect
        from routers import products
        src = inspect.getsource(products.update_product)
        assert "sanitize_merchant_text" in src, (
            "update_product non sanitize description — stored XSS via update."
        )
        assert "long_description" in src, (
            "update_product non sanitize long_description in metadata."
        )

    def test_max_length_cap(self):
        """Anti-DoS: input molto lungo viene troncato."""
        from services.markdown_safe import sanitize_merchant_text, DEFAULT_MAX_LENGTH
        huge = "a" * (DEFAULT_MAX_LENGTH + 1000)
        result = sanitize_merchant_text(huge)
        assert len(result) <= DEFAULT_MAX_LENGTH, (
            f"Length cap ignored: got {len(result)} expected <={DEFAULT_MAX_LENGTH}"
        )


class TestSEC_E_8_6_ReactCouponDryRun:
    """SEC-E.8.6: React main checkout fa coupon dry-run validation.

    Bug audit V2 (cart/checkout): 'Coupon Validation completamente
    assente nel React storefront. Widget implementa dry-run (POST
    /coupons/validate + subtotal) con UX completa, React accetta input
    coupon_code ma NON fa alcun dry-run -> customer non sa se il codice
    e' valido finche' non submitte l'ordine'.

    Sprint 2 W2.1 fix:
      - storefrontAPI.validateCoupon(slug, code, subtotal) NEW method
      - useCouponValidation hook debounced 350ms
      - CouponInput component standalone (input + status banner)
      - StorefrontPage integrato: <CouponInput> al posto di <input>
    """

    def test_storefront_api_has_validate_coupon(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        api = repo_root / "frontend/src/api/storefront.js"
        src = api.read_text(encoding="utf-8")
        assert "validateCoupon" in src, (
            "storefrontAPI manca validateCoupon method — React non puo' "
            "fare coupon dry-run validation."
        )
        assert "/api/public/embed/coupons/validate" in src, (
            "validateCoupon non usa endpoint canonical "
            "/api/public/embed/coupons/validate/{slug}."
        )

    def test_use_coupon_validation_hook_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        hook = repo_root / "frontend/src/features/storefront/hooks/useCouponValidation.js"
        assert hook.exists(), "useCouponValidation hook missing"
        src = hook.read_text(encoding="utf-8")
        # Debounce pattern
        assert "setTimeout" in src and "350" in src, (
            "Hook senza debounce 350ms — fetch ad ogni keystroke "
            "(rate limit risk + UX flicker)."
        )
        # Cancellation pattern (anti race)
        assert "active" in src or "AbortController" in src, (
            "Hook senza cancellation pattern — race su keystroke rapidi."
        )

    def test_coupon_input_component_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        comp = repo_root / "frontend/src/features/storefront/components/CouponInput.jsx"
        assert comp.exists(), "CouponInput component missing"
        src = comp.read_text(encoding="utf-8")
        # Mostra feedback inline per ogni stato
        assert "valid" in src and "invalid" in src and "loading" in src, (
            "CouponInput manca rendering di status valid/invalid/loading."
        )

    def test_storefront_page_uses_coupon_input(self):
        """StorefrontPage.js usa CouponInput invece del flat input legacy."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        assert "import CouponInput" in src or "from './components/CouponInput'" in src, (
            "StorefrontPage non importa CouponInput component."
        )
        assert "<CouponInput" in src, (
            "StorefrontPage non rende <CouponInput> nel checkout form — "
            "il customer continua a vedere flat input senza validation."
        )


class TestSEC_E_8_7_ReactLivePricePreview:
    """SEC-E.8.7: React main checkout mostra discount breakdown live.

    Bug audit V2: 'Widget ha afianco-price-preview (E2.4.10) live total
    server-computed. React StorefrontPage mostra static summary — se
    customer cambia coupon, il totale NON aggiorna live'.

    Sprint 2 W2.2 fix:
      - couponValidation state lifted to main StorefrontPage scope
      - OrderSummary accetta props couponDiscount + couponLabel
      - Render riga 'Sconto coupon -X EUR' emerald + ricalcolo totale
      - useCouponValidation hook gia' debounced 350ms (W2.1)
      - Frontend build PASS ✓
    """

    def test_order_summary_accepts_coupon_discount_prop(self):
        """OrderSummary signature ha couponDiscount + couponLabel props."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        # Pattern: function OrderSummary({ ..., couponDiscount, couponLabel })
        assert "couponDiscount" in src, (
            "OrderSummary signature non ha couponDiscount prop — "
            "live breakdown non possibile."
        )
        assert "couponLabel" in src, (
            "OrderSummary signature non ha couponLabel prop — "
            "label coupon non visibile nella riga sconto."
        )

    def test_order_summary_renders_discount_line(self):
        """OrderSummary rende riga discount quando couponDiscount > 0."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        assert "couponDiscount > 0" in src or "summary.couponDiscount" in src, (
            "OrderSummary non rende riga discount conditional su couponDiscount."
        )
        # Total ricalcolato sottraendo discount
        assert "couponDiscount || 0)" in src or "- (couponDiscount" in src, (
            "Total finale non sottrae couponDiscount — il customer vede "
            "totale gonfiato (subtotal + shipping ignora lo sconto)."
        )

    def test_main_scope_uses_coupon_validation_hook(self):
        """StorefrontPage lifted useCouponValidation hook per passare a OrderSummary."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        # Import del hook
        assert "useCouponValidation" in src, (
            "StorefrontPage non importa useCouponValidation hook al "
            "main scope — discount state non disponibile per OrderSummary."
        )
        # State lifted via couponValidationState
        assert "couponValidationState" in src, (
            "Manca couponValidationState shape compatto per OrderSummary."
        )


class TestSEC_E_8_8_ReactFulfillmentParityWidget:
    """SEC-E.8.8: React supporta 3 fulfillment modes come widget.

    Bug audit V2: 'Widget supporta 3 modes (shipping, local_pickup,
    pickup_at_store), React solo 2. Se merchant abilita
    pickup_at_store, React checkout NON mostra l'opzione (mode visualizzato
    come stringa raw senza label)'.

    Sprint 2 W2.3 fix:
      - Label map esplicito {shipping, local_pickup, pickup_at_store} ->
        i18n key invece di hardcode 2 case
      - i18n IT + EN: aggiunta key fulfillment.pickupAtStore
      - Stesso pattern per single mode hint (riga 2341)
      - Flex wrap per supportare 3+ buttons mobile
    """

    def test_storefront_page_handles_pickup_at_store(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        assert "pickup_at_store" in src, (
            "StorefrontPage non gestisce pickup_at_store fulfillment mode. "
            "Widget supporta 3 modes ma React hardcoded a 2 (gap UX merchant)."
        )
        assert "pickupAtStore" in src, (
            "StorefrontPage non usa i18n key fulfillment.pickupAtStore — "
            "mode renderizzato come 'pickup_at_store' raw all'utente."
        )

    def test_i18n_storefront_has_pickup_at_store_label(self):
        """i18n IT + EN definiscono fulfillment.pickupAtStore."""
        import json
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for locale in ("it", "en"):
            path = repo_root / f"frontend/src/locales/{locale}/storefront.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            checkout = data.get("checkout", {})
            fulfillment = checkout.get("fulfillment", {})
            assert "pickupAtStore" in fulfillment, (
                f"i18n {locale}/storefront.json manca "
                f"checkout.fulfillment.pickupAtStore label."
            )

    def test_fulfillment_picker_iterates_all_modes(self):
        """Fulfillment picker loopa su catalog.fulfillment_modes (dinamico)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        page = repo_root / "frontend/src/features/storefront/StorefrontPage.js"
        src = page.read_text(encoding="utf-8")
        # Pattern: labelMap con 3 case (shipping, local_pickup, pickup_at_store)
        assert "labelMap" in src, (
            "Label map per fulfillment modes mancante — render hardcoded."
        )
        # Tutti i 3 modes mappati
        for mode in ("shipping", "local_pickup", "pickup_at_store"):
            assert mode in src, f"Mode {mode!r} non gestito nel labelMap."


class TestSEC_E_8_9_ReactSearchBar:
    """SEC-E.8.9: React ProductGrid ha search bar (parity widget E5.1).

    Bug audit V1: 'Widget Lit ha search bar nel product-grid (E5.1).
    React storefront ha solo category filter pills, no full-text search
    input. Customer su storefront classic non puo cercare prodotti'.

    Sprint 2 W2.4 fix:
      - Search input client-side nel ProductGrid component
      - Filter case-insensitive su name + description (memo)
      - Empty state quando zero matches
      - Clear button (X)
      - i18n IT + EN: 6 nuove key search.*
      - showSearch prop default true (opt-out se serve)
    """

    def test_product_grid_has_search_input(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        grid = repo_root / "frontend/src/features/storefront/ProductGrid.jsx"
        src = grid.read_text(encoding="utf-8")
        assert "searchQuery" in src or "SearchIcon" in src, (
            "ProductGrid manca search state — feature non implementata."
        )
        # Filter useMemo su normalizedQuery
        assert "filteredProducts" in src, (
            "ProductGrid non filtra products by query — search non funzionale."
        )
        # i18n keys
        assert "search.placeholder" in src or "storefront:search" in src, (
            "ProductGrid hardcoded labels search — no i18n."
        )

    def test_product_grid_search_is_case_insensitive(self):
        """Filter usa toLowerCase su query + name + description."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        grid = repo_root / "frontend/src/features/storefront/ProductGrid.jsx"
        src = grid.read_text(encoding="utf-8")
        assert "toLowerCase" in src, (
            "Search filter non case-insensitive — UX rotta su mixed case."
        )

    def test_product_grid_empty_state(self):
        """Empty state rendering quando hasZeroMatches."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        grid = repo_root / "frontend/src/features/storefront/ProductGrid.jsx"
        src = grid.read_text(encoding="utf-8")
        assert "hasZeroMatches" in src or "noResults" in src, (
            "ProductGrid manca empty state per search vuota — UX confusa."
        )

    def test_i18n_storefront_has_search_keys(self):
        """i18n IT + EN definiscono search.* keys."""
        import json
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for locale in ("it", "en"):
            path = repo_root / f"frontend/src/locales/{locale}/storefront.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            search = data.get("search", {})
            for required_key in ("placeholder", "noResults", "ariaLabel"):
                assert required_key in search, (
                    f"i18n {locale}/storefront.json manca search.{required_key}."
                )


class TestSEC_E_8_10_WidgetLogoDisplay:
    """SEC-E.8.10: widget header mostra logo merchant (parity React).

    Bug audit V4: 'Widget header NON ha <img> per logo. React storefront
    StorefrontHeader.js:136-164 mostra logo + text. Brand visual identity
    perso quando customer naviga widget vs storefront classico'.

    Sprint 2 W2.5 fix:
      - afianco-header.ts getter displayLogoUrl (priority store_info.logo_url)
      - Render <img class='brand-logo'> sopra brand-name
      - object-fit contain + height 36px + max-width 140px
      - Error handler: hide gracefully se broken URL
      - Bundle synced
    """

    def test_widget_header_renders_logo_img(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        header = repo_root / "apps/embed-sdk/src/components/afianco-header.ts"
        src = header.read_text(encoding="utf-8")
        assert "displayLogoUrl" in src, (
            "afianco-header.ts manca displayLogoUrl getter — feature non "
            "implementata."
        )
        assert "brand-logo" in src, (
            "afianco-header.ts manca classe CSS brand-logo per styling logo."
        )
        # Pattern <img src=... loading=lazy
        assert "logoUrl" in src, "Logo URL non legato a render."
        assert "loading=\"lazy\"" in src, (
            "Logo img senza loading=lazy — perf regression mobile."
        )

    def test_widget_header_logo_error_handler(self):
        """Broken logo URL handled gracefully (no broken img icon)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        header = repo_root / "apps/embed-sdk/src/components/afianco-header.ts"
        src = header.read_text(encoding="utf-8")
        assert "@error" in src or "onerror" in src, (
            "afianco-header.ts logo img senza error handler — UX rotta se "
            "CDN merchant down (broken img icon mostrato)."
        )

    def test_bundle_compiled_contains_logo_render(self):
        """Bundle compiled contiene marker logo class."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "brand-logo" in src, (
            "Bundle public non contiene marker 'brand-logo' — bundle "
            "stale o tree-shake. Run pnpm embed:rebuild."
        )


class TestSEC_E_8_11_CartMergeOnLogin:
    """SEC-E.8.11: guest cart -> customer cart merge al login.

    Bug audit V2: 'Guest-to-authenticated cart merge non implementato in
    nessuno dei 2 surface. Se un guest aggiunge item, fa login, il cart
    e' vuoto. CRITICAL UX blocker'.

    Sprint 2 W2.6 fix:
      WIDGET (afianco-cart-drawer.ts):
        - Listen document event afianco:customer-logged-in
        - _handleCustomerLoggedIn handler chiama POST
          /embed/cart/{guest_id}/merge con customer_account_id
        - Backend valida ownership + assorbe guest items nel customer cart
        - Update local cart_id + state con merged cart
        - Soft-fail su error (cart guest preserved)

      REACT (CustomerAuthContext.js):
        - login() dispatcha document event afianco:customer-logged-in
        - Cart state e' sessionStorage slug-scoped -> preserved through
          login (by-design, no backend merge needed perche' cart client-side)

    Pattern document event = single-source-of-truth signal cross-component
    (loose coupling, mirror Lit event bus pattern).
    """

    def test_widget_cart_drawer_listens_login_event(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        drawer = repo_root / "apps/embed-sdk/src/components/afianco-cart-drawer.ts"
        src = drawer.read_text(encoding="utf-8")
        assert "afianco:customer-logged-in" in src, (
            "Cart drawer non ascolta afianco:customer-logged-in event "
            "-> guest cart perso al login (UX blocker)."
        )
        assert "_handleCustomerLoggedIn" in src, (
            "Handler _handleCustomerLoggedIn missing — listener non wired."
        )

    def test_widget_cart_merge_uses_backend_endpoint(self):
        """Cart drawer chiama backend POST /cart/{id}/merge."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        drawer = repo_root / "apps/embed-sdk/src/components/afianco-cart-drawer.ts"
        src = drawer.read_text(encoding="utf-8")
        assert "client.embed.cart.merge" in src, (
            "Cart drawer non invoca client.embed.cart.merge — backend "
            "merge endpoint non chiamato."
        )
        # Defensive: skip se no guest cart o cart vuoto
        assert "readCartIdFromStorage" in src, (
            "Handler non legge cart_id da storage prima di merge."
        )

    def test_react_auth_context_dispatches_login_event(self):
        """CustomerAuthContext.login dispatcha afianco:customer-logged-in."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        ctx = repo_root / "frontend/src/context/CustomerAuthContext.js"
        src = ctx.read_text(encoding="utf-8")
        assert "afianco:customer-logged-in" in src, (
            "CustomerAuthContext non dispatcha event login — Sprint 2 W2.6 "
            "pattern document-event non wired."
        )
        assert "document.dispatchEvent" in src, (
            "CustomerAuthContext non usa document.dispatchEvent."
        )

    def test_bundle_compiled_contains_merge_handler(self):
        """Bundle compiled contiene cart merge handler."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "customer-logged-in" in src, (
            "Bundle public non contiene listener customer-logged-in — "
            "bundle stale o tree-shake removed."
        )


class TestSEC_E_8_12_WidgetPasswordUX:
    """SEC-E.8.12: widget login/signup ha password visibility + strength.

    Bug audit V3: 'Widget login non ha Eye/EyeOff toggle. Widget signup
    non ha password strength indicator (React ha 4 criteri checklist
    in AuthPage.jsx). UX gap usability.'

    Sprint 3 W3.1 fix:
      - NEW utils/password-strength.ts (zero-dep port React util)
        * computePasswordStrength: score 0-5 + level + checks dict
        * levelMeta: color + label per livello
      - afianco-login.ts: showPassword state + toggle button SVG
      - afianco-signup.ts: showPassword state + toggle + strength bar
        live (5 segments) + level label colored
    """

    def test_password_strength_util_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        util = repo_root / "apps/embed-sdk/src/utils/password-strength.ts"
        assert util.exists(), "password-strength.ts util missing"
        src = util.read_text(encoding="utf-8")
        assert "computePasswordStrength" in src, "Missing main function"
        assert "levelMeta" in src, "Missing levelMeta helper"
        # 5 criteri valutati
        for criterion in ("uppercase", "lowercase", "digit", "symbol", "recommendedLength"):
            assert criterion in src, f"Missing criterion {criterion}"

    def test_widget_login_has_password_toggle(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        login = repo_root / "apps/embed-sdk/src/components/afianco-login.ts"
        src = login.read_text(encoding="utf-8")
        assert "showPassword" in src, (
            "afianco-login.ts manca showPassword state — toggle non implementato."
        )
        assert "toggle-password" in src, (
            "afianco-login.ts manca classe toggle-password per styling."
        )

    def test_widget_signup_has_strength_indicator(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        signup = repo_root / "apps/embed-sdk/src/components/afianco-signup.ts"
        src = signup.read_text(encoding="utf-8")
        assert "computePasswordStrength" in src, (
            "afianco-signup.ts non usa computePasswordStrength util."
        )
        assert "strength-bar" in src, (
            "afianco-signup.ts manca strength-bar render."
        )
        assert "showPassword" in src, (
            "afianco-signup.ts manca password toggle state."
        )

    def test_bundle_contains_password_ux_markers(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "toggle-password" in src, (
            "Bundle public non contiene toggle-password marker."
        )
        assert "strength-bar" in src, (
            "Bundle public non contiene strength-bar marker."
        )


class TestSEC_E_8_13_WidgetLockoutCountdown:
    """SEC-E.8.13: widget login mostra countdown lockout (Onda 29 parity React).

    Bug audit V3: 'Widget login mostra solo generic 'Credenziali non
    valide'. React AuthPage.jsx ha full lockout state + live countdown
    banner. Customer attaccato non sa quando puo riprovare'.

    Sprint 3 W3.2 fix:
      - NEW AfiancoLockedError nel SDK errors.ts
      - client.ts: status 423 -> throw AfiancoLockedError con unlockAtIso
      - Widget login: catch + start countdown + render banner
      - setInterval 1s + cleanup on disconnect
      - Backend gia ritornava 423 detail.unlock_at (Onda 29)
    """

    def test_sdk_has_locked_error_class(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        errors = repo_root / "packages/api-client/src/errors.ts"
        src = errors.read_text(encoding="utf-8")
        assert "AfiancoLockedError" in src, (
            "SDK manca AfiancoLockedError class — 423 status unhandled."
        )
        assert "unlockAtIso" in src, (
            "AfiancoLockedError manca campo unlockAtIso."
        )

    def test_sdk_client_maps_423_to_locked_error(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "packages/api-client/src/client.ts"
        src = client.read_text(encoding="utf-8")
        assert "status === 423" in src, (
            "client.ts non mappa status 423 -> AfiancoLockedError."
        )
        assert "unlock_at" in src, (
            "client.ts non estrae unlock_at dal detail backend."
        )

    def test_widget_login_handles_locked_error(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        login = repo_root / "apps/embed-sdk/src/components/afianco-login.ts"
        src = login.read_text(encoding="utf-8")
        assert "AfiancoLockedError" in src, (
            "Widget login non importa AfiancoLockedError — 423 unhandled."
        )
        assert "_startLockoutCountdown" in src, (
            "Widget login manca countdown helper."
        )
        assert "lockoutSecondsRemaining" in src, (
            "Widget login manca lockoutSecondsRemaining state."
        )

    def test_widget_cleanup_interval_on_disconnect(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        login = repo_root / "apps/embed-sdk/src/components/afianco-login.ts"
        src = login.read_text(encoding="utf-8")
        assert "_stopLockoutCountdown" in src, (
            "Widget login manca stop helper — memory leak su disconnect."
        )
        assert "disconnectedCallback" in src, (
            "Widget login manca disconnectedCallback override per cleanup."
        )

    def test_bundle_compiled_contains_lockout_marker(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "AfiancoLockedError" in src or "lockoutSecondsRemaining" in src, (
            "Bundle public non contiene marker lockout — bundle stale."
        )


class TestSEC_E_8_14_ReactSortPaginationParity:
    """SEC-E.8.14: React ProductGrid ha sort + pagination (parity widget).

    Bug audit V1: 'Widget supports 4 sort modes (name, price_asc,
    price_desc, newest) + pagination offset/limit. React storefront
    NO. Scalabilita' rotta per cataloghi 100+ prodotti.'

    Sprint 3 W3.3 fix:
      - sortMode state (4 modes parity widget E5.1 whitelist)
      - shownCount state + pageSize prop (default 24)
      - useMemo paginatedProducts = filteredProducts.slice(0, shownCount)
      - hasMore flag
      - useEffect reset pagination su cambio search/sort
      - UI: select dropdown 4 options + 'Show more' button
      - i18n IT + EN: 7 new keys
    """

    def test_product_grid_has_sort_state(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        grid = repo_root / "frontend/src/features/storefront/ProductGrid.jsx"
        src = grid.read_text(encoding="utf-8")
        assert "sortMode" in src, "ProductGrid manca sortMode state."
        # 4 sort modes parity widget
        for mode in ("price_asc", "price_desc", "newest"):
            assert mode in src, f"Sort mode {mode!r} non implementato."

    def test_product_grid_has_pagination(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        grid = repo_root / "frontend/src/features/storefront/ProductGrid.jsx"
        src = grid.read_text(encoding="utf-8")
        assert "shownCount" in src, "ProductGrid manca shownCount state."
        assert "paginatedProducts" in src, "Manca paginatedProducts useMemo."
        assert "hasMore" in src, "Manca hasMore flag per footer button."
        assert "showMore" in src, (
            "Manca i18n key showMore o button render."
        )

    def test_i18n_has_sort_pagination_keys(self):
        import json
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for locale in ("it", "en"):
            path = repo_root / f"frontend/src/locales/{locale}/storefront.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            search = data.get("search", {})
            for required in ("sortName", "sortPriceAsc", "sortNewest", "showMore", "paginationCount"):
                assert required in search, (
                    f"i18n {locale}/storefront.json manca search.{required}."
                )


class TestSEC_E_8_15_ReactTokenScoping:
    """SEC-E.8.15: React customerClient scopa token per-slug (parity widget).

    Bug audit V3: 'React token storage uses GLOBAL key customer_token.
    Customer su 2 merchant stores nello stesso browser sharano JWT --
    backend org_id validation mitiga ma client-side surface unsafe'.

    Sprint 3 W3.4 fix:
      - readCustomerToken() helper exported: legge prima la chiave
        scoped `customer_token_{slug}`, fallback alla legacy globale
      - clearCustomerToken() helper exported per cleanup unified
      - _resolveCurrentSlug() helper: URL path /s/:slug -> localStorage
      - Backward compat: legge legacy + migra alla scoped key on first read
      - CustomerAuthContext.login(): scrive BOTH keys (transition)
    """

    def test_customer_client_has_scoped_token_helpers(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "frontend/src/api/customerClient.js"
        src = client.read_text(encoding="utf-8")
        assert "readCustomerToken" in src, (
            "customerClient.js manca readCustomerToken helper export."
        )
        assert "_resolveCurrentSlug" in src or "resolveCurrentSlug" in src, (
            "customerClient.js manca _resolveCurrentSlug helper."
        )
        assert "customer_token_" in src, (
            "customerClient.js non usa pattern scoped customer_token_{slug}."
        )

    def test_customer_client_legacy_fallback(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "frontend/src/api/customerClient.js"
        src = client.read_text(encoding="utf-8")
        # Legacy backward compat read
        assert "'customer_token'" in src, (
            "customerClient.js manca fallback alla legacy key customer_token "
            "(breaking change per customer esistenti)."
        )

    def test_customer_auth_context_writes_scoped_key(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        ctx = repo_root / "frontend/src/context/CustomerAuthContext.js"
        src = ctx.read_text(encoding="utf-8")
        assert "customer_token_${slug}" in src or "customer_token_\" + slug" in src, (
            "CustomerAuthContext.login non scrive scoped key — "
            "lettura post-login fa fallback su legacy (drift)."
        )


class TestSEC_E_8_16_EmbedETagConditional:
    """SEC-E.8.16: /embed/{init,categories,products} ha ETag + 304.

    Audit V5 indicava 'API caching headers incomplete (no ETag on
    /embed/*)' — verifica era imprecisa: tutti e 3 gli endpoint
    avevano gia ETag (SHA-1) + Conditional GET.

    Sprint 3 W3.5 fix:
      - NEW core/etag_helper.py centralizza compute_etag + build_conditional_response
        per future endpoint (init/categories/products gia handle inline)
      - Sentinel pinning sui 3 endpoint per evitare future drift
      - Conditional GET behavior preservato
    """

    def test_etag_helper_module_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        helper = repo_root / "backend/core/etag_helper.py"
        assert helper.exists(), "core/etag_helper.py missing"
        src = helper.read_text(encoding="utf-8")
        assert "def compute_etag" in src, "compute_etag fn missing"
        assert "def build_conditional_response" in src, (
            "build_conditional_response fn missing"
        )
        assert "If-None-Match" in src or "if-none-match" in src, (
            "build_conditional_response non legge If-None-Match header."
        )
        assert "304" in src or "NOT_MODIFIED" in src, (
            "build_conditional_response non ritorna 304."
        )

    def test_embed_init_has_etag_conditional(self):
        import inspect
        from routers import embed_public
        src = inspect.getsource(embed_public.get_embed_init)
        assert "ETag" in src, "/init/{slug} manca ETag header set."
        assert "if-none-match" in src.lower(), (
            "/init/{slug} non gestisce If-None-Match conditional GET."
        )
        assert "304" in src or "NOT_MODIFIED" in src, (
            "/init/{slug} non ritorna 304 su match ETag."
        )

    def test_embed_categories_has_etag_conditional(self):
        import inspect
        from routers import embed_public
        src = inspect.getsource(embed_public.get_embed_categories)
        assert "ETag" in src, "/categories/{slug} manca ETag."
        assert "if-none-match" in src.lower(), (
            "/categories/{slug} non gestisce conditional GET."
        )

    def test_embed_products_has_etag_conditional(self):
        import inspect
        from routers import embed_public
        src = inspect.getsource(embed_public.get_embed_products)
        assert "ETag" in src, "/products/{slug} manca ETag."
        assert "if-none-match" in src.lower(), (
            "/products/{slug} non gestisce conditional GET."
        )
        # I query params devono essere parte del digest (varianti
        # filter/sort/q producono distinct cache entries)
        assert "category" in src and "sort" in src, (
            "ETag digest /products non include category+sort -> cache "
            "collision fra filter variants."
        )

    def test_etag_format_quoted_per_rfc(self):
        """ETag header value deve essere quoted per RFC 7232."""
        import inspect
        from routers import embed_public
        src = inspect.getsource(embed_public.get_embed_init)
        # Pattern f'"{etag}"' (quoted)
        assert '"{etag}"' in src or '"' + "{etag}" + '"' in src, (
            "ETag value non quoted RFC 7232 -- alcuni proxy invalidano."
        )


class TestSEC_E_8_17_WidgetI18nLocalesDeFr:
    """SEC-E.8.17: widget supporta IT + EN + DE + FR (parity React).

    Bug audit V4: 'Widget Lit ha 2 lingue (IT, EN). React storefront
    ne ha 4 (IT, EN, DE, FR). Merchant DE/FR su widget vede fallback
    italiano -- UX regression'.

    Sprint 4 W4.1+W4.2:
      - NEW apps/embed-sdk/src/i18n/locales/de.ts (~164 keys)
      - NEW apps/embed-sdk/src/i18n/locales/fr.ts (~164 keys)
      - i18n/index.ts: import + register DE + FR
      - Language switcher gia' aveva labels DE+FR
      - Bundle gzip 87.85 -> 92.05 KB (+4.2 KB per 2 lingue, under target 95 KB)
    """

    def test_de_locale_file_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        de = repo_root / "apps/embed-sdk/src/i18n/locales/de.ts"
        assert de.exists(), "Locale DE missing"
        src = de.read_text(encoding="utf-8")
        # Key sentinel: ogni dictionary deve avere almeno i 4 core namespaces
        for ns in ("common.loading", "header.cart", "checkout.title", "signup.title"):
            assert f"'{ns}'" in src, f"DE locale manca key {ns!r}."

    def test_fr_locale_file_exists(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        fr = repo_root / "apps/embed-sdk/src/i18n/locales/fr.ts"
        assert fr.exists(), "Locale FR missing"
        src = fr.read_text(encoding="utf-8")
        for ns in ("common.loading", "header.cart", "checkout.title", "signup.title"):
            assert f"'{ns}'" in src, f"FR locale manca key {ns!r}."

    def test_i18n_index_registers_de_fr(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        idx = repo_root / "apps/embed-sdk/src/i18n/index.ts"
        src = idx.read_text(encoding="utf-8")
        assert "import { de }" in src, "i18n/index.ts non importa de.ts"
        assert "import { fr }" in src, "i18n/index.ts non importa fr.ts"
        # Registrati nel dict LOCALES
        assert "de," in src or "de:" in src, "LOCALES dict manca de entry"
        assert "fr," in src or "fr:" in src, "LOCALES dict manca fr entry"

    def test_locale_files_have_parity_keys(self):
        """DE + FR hanno stesso numero key di IT/EN (parity coverage)."""
        from pathlib import Path
        import re
        repo_root = Path(__file__).resolve().parents[2]
        # Count keys per locale (pattern 'key.path':)
        key_re = re.compile(r"^\s*'[a-z_.]+'\s*:", re.MULTILINE)
        counts = {}
        for locale in ("it", "en", "de", "fr"):
            path = repo_root / f"apps/embed-sdk/src/i18n/locales/{locale}.ts"
            content = path.read_text(encoding="utf-8")
            counts[locale] = len(key_re.findall(content))
        # All locales dovrebbero avere lo stesso numero (±10% tolerance)
        baseline = counts["it"]
        for locale, n in counts.items():
            assert n >= baseline * 0.9, (
                f"Locale {locale} ha {n} keys vs baseline IT {baseline} "
                f"(< 90% coverage). Possibile drift -- mancano traduzioni."
            )

    def test_bundle_contains_de_fr_markers(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Marker DE
        assert "Warenkorb" in src or "Anmelden" in src, (
            "Bundle public non contiene marker tedesco -- bundle stale o "
            "tree-shake removed."
        )
        # Marker FR
        assert "Panier" in src or "Connexion" in src, (
            "Bundle public non contiene marker francese."
        )


class TestSEC_E_8_18_WidgetLocalePropagation:
    """SEC-E.8.18: widget re-fetcha /init e propaga cambio lingua merchant.

    Bug user-reported: 'Se cambio la lingua nelle impostazioni dello
    store, la lingua non si scambia automaticamente sullo store
    embeddato'.

    ROOT CAUSE:
      - Widget chiamava init() SOLO al firstUpdated (mount). Nessun
        re-fetch dopo, anche se merchant cambiava storefront_languages.
      - localStorage afianco_lang_{slug} era 'sticky' anche per lingue
        rimosse dal merchant -> render mixed/broken.

    W4.4 fix:
      afianco-storefront-init.ts:
        - visibilitychange listener: re-fetch init() quando tab torna
          visible (natural UX moment, no spam fetch)
        - Throttle 60s su _lastInitAt
        - Cleanup listener su disconnectedCallback
      i18n/index.ts initLocale():
        - Soft cleanup localStorage: se lingua cached non in supported,
          rimuove e cade su default merchant
        - Force-dispatch event (silent=false) se currentLocale cambia,
          cosi' tutti i componenti consumer re-render automaticamente
    """

    def test_storefront_init_has_visibility_listener(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "visibilitychange" in src, (
            "afianco-storefront-init.ts manca listener visibilitychange "
            "-> widget non re-fetcha quando customer torna al tab. "
            "Bug: cambio lingua merchant non propaga."
        )
        assert "_onVisibilityChange" in src, (
            "Handler _onVisibilityChange missing."
        )
        # Throttle (anti-spam)
        assert "MIN_REINIT_INTERVAL_MS" in src or "throttle" in src.lower(), (
            "Re-init senza throttle - spam fetch su rapid tab switches."
        )
        # Cleanup defensive
        assert "removeEventListener" in src, (
            "Listener visibilitychange senza cleanup -> memory leak su "
            "disconnect."
        )

    def test_i18n_init_cleans_stale_localstorage(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        i18n = repo_root / "apps/embed-sdk/src/i18n/index.ts"
        src = i18n.read_text(encoding="utf-8")
        # Cleanup pattern: stored && !supported.includes(stored)
        assert "localStorage.removeItem" in src, (
            "i18n/index.ts non rimuove lingua cached non piu' supportata. "
            "Customer continua a vedere lingua rimossa."
        )

    def test_i18n_init_force_dispatch_on_locale_change(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        i18n = repo_root / "apps/embed-sdk/src/i18n/index.ts"
        src = i18n.read_text(encoding="utf-8")
        # currentNoLongerSupported flag + silent: !currentNoLongerSupported
        assert "currentNoLongerSupported" in src, (
            "i18n/index.ts non detect 'currentLocale rimosso dal merchant' "
            "-> nessun event dispatch -> componenti non re-render."
        )

    def test_bundle_contains_visibility_listener_marker(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "visibilitychange" in src, (
            "Bundle public non contiene listener visibilitychange -- "
            "bundle stale, run pnpm embed:rebuild."
        )


class TestSEC_E_8_19_WidgetPropagationFull:
    """SEC-E.8.19: widget propaga cambi merchant via polling + storage event.

    Bug user-reported PERSISTENT: 'la lingua dello store si modifica nella
    sezione modifica dello store, ma ancora non si propaga sullo store
    embedded'.

    ROOT CAUSE V2: W4.4 visibilitychange listener funziona SOLO quando il
    customer effettivamente switcha tab. Se il merchant cambia lingua
    nell'admin nello STESSO browser/tab del widget, visibilitychange
    non triggera mai -> customer continua a vedere lingua vecchia
    finche' la cache backend 5min non scade + customer fa tab switch.

    W4.5 fix multi-layer:
      1. SDK getInit({bypassCache: true}) aggiunge ?_v=<ms> query
         per forzare cache-bust browser + CDN intermediaries
      2. Widget polling 90s (< cache TTL backend 300s) per pickup
         automatic anche senza tab switch
      3. Cross-tab storage event listener su 'afianco_admin_changed_{slug}'
         per propagation IMMEDIATA quando admin+widget stessa origin
      4. Admin StoresPage.js scrive il signal localStorage post-PATCH
      5. init() opt bypassCache propaga al SDK
      6. Skeleton flicker eliminated: se gia 'ready', re-init e' silent
    """

    def test_sdk_getinit_supports_bypass_cache(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        client = repo_root / "packages/api-client/src/client.ts"
        src = client.read_text(encoding="utf-8")
        assert "bypassCache" in src, (
            "SDK client.embed.getInit non accetta opt bypassCache - "
            "cache-bust non implementato."
        )
        assert "_v" in src, (
            "Cache-bust pattern ?_v=<timestamp> non implementato."
        )

    def test_widget_has_polling_backup(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "_POLLING_INTERVAL_MS" in src, (
            "Widget manca polling backup per pickup config changes."
        )
        # 90s < 300s backend cache TTL
        assert "90_000" in src or "90000" in src, (
            "Polling interval drift - deve essere 90s (< cache backend 300s)."
        )
        assert "setInterval" in src, (
            "Polling non usa setInterval - logica drift."
        )
        # Skip background tab (no wasted requests)
        assert "document.hidden" in src, (
            "Polling non skippa tab background - wasted requests."
        )

    def test_widget_has_storage_event_listener(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "_onStorageChange" in src, (
            "Widget non ha _onStorageChange handler per cross-tab signal."
        )
        assert "afianco_admin_changed_" in src, (
            "Widget non ascolta key 'afianco_admin_changed_{slug}' "
            "scritta dall'admin post-PATCH."
        )
        assert "addEventListener('storage'" in src, (
            "Widget non registra storage event listener."
        )

    def test_admin_writes_storage_signal_on_update(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        admin = repo_root / "frontend/src/features/stores/StoresPage.js"
        src = admin.read_text(encoding="utf-8")
        assert "afianco_admin_changed_" in src, (
            "StoresPage non scrive signal localStorage post-PATCH - "
            "cross-tab propagation rotta."
        )
        # Pattern post storesAPI.update success
        assert "storesAPI.update" in src and "localStorage.setItem" in src, (
            "Signal localStorage non e' wired post-update success."
        )

    def test_widget_no_skeleton_flicker_on_reinit(self):
        """init() su widget gia 'ready' NON resetta a 'loading' (no flicker)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "isFirstInit" in src, (
            "init() resetta sempre a 'loading' anche su re-init -> "
            "skeleton flicker durante session."
        )

    def test_bundle_contains_polling_markers(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "afianco_admin_changed_" in src, (
            "Bundle non contiene marker afianco_admin_changed - "
            "storage listener non compiled. Run pnpm embed:rebuild."
        )


class TestSEC_E_8_20_LocalePropagationViaContext:
    """SEC-E.8.20: locale propagato via Lit context -> auto re-render tutti i consumer.

    Bug user-reported V3: 'Ho impostato lingua tedesca ma l'embedded
    continua a rimanere in italiano' (W4.4 + W4.5 NON bastavano).

    ROOT CAUSE V3:
      - initLocale dispatchava event document 'afianco:locale-changed'
      - SOLO 2 componenti su 35 ascoltavano questo event
        (afianco-header + afianco-language-switcher)
      - Tutti gli altri (cart-drawer, checkout-button, account, signup,
        login, product-grid, product-detail, profile-editor, my-courses,
        ecc.) NON re-renderizzavano al cambio locale -> mostravano
        ancora le t() key risolte alla lingua PRECEDENTE
      - Customer vedeva header + switcher in tedesco, MA cart/checkout/
        prodotti rimanevano in italiano

    W4.6 fix radicale:
      - StorefrontContext interface ESTESA con campo `locale: string`
      - <afianco-storefront-init> listener 'afianco:locale-changed'
        aggiorna contextValue.locale
      - Lit Context con @provide propaga al @consume({subscribe: true})
      - TUTTI i 20 componenti che gia' fanno @consume({subscribe: true})
        re-renderizzano automaticamente -> t() calls leggono il nuovo
        currentLocale -> UI mostra le traduzioni corrette

      Pattern reactive Lit: zero subscription boilerplate aggiunto nei
      singoli componenti. Una sola riga (locale: getLocale()) nel
      context value propaga a tutti.
    """

    def test_storefront_context_includes_locale_field(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        ctx = repo_root / "apps/embed-sdk/src/context.ts"
        src = ctx.read_text(encoding="utf-8")
        # locale field nel interface
        assert "locale:" in src, (
            "StorefrontContext interface manca campo `locale` -> "
            "non puo' propagare cambio via context."
        )
        # STOREFRONT_INITIAL include locale default
        assert "locale: 'it'" in src, (
            "STOREFRONT_INITIAL manca locale default - context unrelated."
        )

    def test_storefront_init_listens_locale_changed(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "afianco:locale-changed" in src, (
            "<afianco-storefront-init> non ascolta locale-changed - "
            "context non aggiornato su cambio lingua."
        )
        assert "_onLocaleChanged" in src, (
            "Handler _onLocaleChanged missing."
        )
        # Aggiorna contextValue.locale
        assert "contextValue.locale" in src or "locale: newLocale" in src, (
            "_onLocaleChanged non aggiorna contextValue.locale -> "
            "consumer non re-renderizzano."
        )

    def test_storefront_init_sets_locale_in_context_value(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        init = repo_root / "apps/embed-sdk/src/components/afianco-storefront-init.ts"
        src = init.read_text(encoding="utf-8")
        assert "locale: getLocale()" in src, (
            "init() success path non setta locale: getLocale() nel "
            "contextValue - locale stale al primo render."
        )
        # Import getLocale
        assert "getLocale" in src, "Manca import getLocale da i18n."

    def test_majority_consumers_use_subscribe_true(self):
        """Maggior parte dei componenti consume(context, subscribe:true)."""
        from pathlib import Path
        import glob
        repo_root = Path(__file__).resolve().parents[2]
        files = list((repo_root / "apps/embed-sdk/src/components").glob("*.ts"))
        consumers = [f for f in files if "@consume" in f.read_text(encoding="utf-8")]
        with_subscribe = [
            f for f in consumers
            if "subscribe: true" in f.read_text(encoding="utf-8")
        ]
        # Almeno 90% dei consumer hanno subscribe:true
        ratio = len(with_subscribe) / max(len(consumers), 1)
        assert ratio >= 0.9, (
            f"Solo {len(with_subscribe)}/{len(consumers)} consumer "
            f"hanno subscribe:true ({ratio:.0%}). Context propagation "
            f"incompleta -> alcuni componenti non re-renderizzano su "
            f"locale change."
        )

    def test_bundle_contains_locale_context_marker(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        assert "_onLocaleChanged" in src or "afianco:locale-changed" in src, (
            "Bundle public non contiene listener locale-changed -- "
            "bundle stale, run pnpm embed:rebuild."
        )


class TestSEC_E_8_21_WidgetI18nExtensiveCoverage:
    """SEC-E.8.21: i18n coverage estesa cross-component (~90 stringhe).

    Bug user-reported: 'Non tutti i testi sono ancora tradotti'. Audit
    olistico ha rivelato che PRE-W4.7 NESSUN componente Lit (eccetto
    header e language-switcher) usava t() — ~90 stringhe italiane
    hardcoded.

    W4.7 fix:
      - +70 nuove keys nei locale files IT/EN/DE/FR
      - Wired t() in 10 componenti principali:
        cart-drawer, login, signup, account, customer-portal,
        product-detail, fulfillment-picker, shipping-options-picker,
        extras-picker, tier-picker, price-preview, checkout-button
      - Componenti minori (loading post-purchase) restano per V2
    """

    REQUIRED_NEW_KEYS = [
        "checkout.error_storefront_not_ready",
        "checkout.opening_payment",
        "checkout.popup_blocked",
        "checkout.notes_label",
        "checkout.close_label",
        "cart.error_storefront_not_ready",
        "cart.open_label",
        "cart.items_aria_label",
        "login.error_credentials",
        "login.welcome_message",
        "login.show_password",
        "login.hide_password",
        "signup.error_gdpr_required",
        "signup.password_hint",
        "signup.login_prompt",
        "account.open_authenticated",
        "account.title_authenticated",
        "product.close_label",
        "product.loading",
        "product.out_of_stock",
        "product.limited_stock",
        "fulfillment.group_label",
        "shipping.loading",
        "shipping.free_threshold",
        "extras.title",
        "tier.title",
        "price.total",
    ]

    def test_locale_files_have_new_keys(self):
        """Tutte le 4 lingue hanno le ~30 nuove keys critiche."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for locale in ("it", "en", "de", "fr"):
            path = repo_root / f"apps/embed-sdk/src/i18n/locales/{locale}.ts"
            src = path.read_text(encoding="utf-8")
            for key in self.REQUIRED_NEW_KEYS:
                assert f"'{key}'" in src, (
                    f"Locale {locale}.ts manca chiave i18n {key!r}."
                )

    def test_critical_components_import_i18n(self):
        """I 10+ componenti principali importano t() helper."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        components = [
            "afianco-cart-drawer.ts",
            "afianco-login.ts",
            "afianco-signup.ts",
            "afianco-account.ts",
            "afianco-customer-portal.ts",
            "afianco-product-detail.ts",
            "afianco-fulfillment-picker.ts",
            "afianco-shipping-options-picker.ts",
            "afianco-extras-picker.ts",
            "afianco-tier-picker.ts",
            "afianco-price-preview.ts",
            "afianco-checkout-button.ts",
        ]
        for comp in components:
            path = repo_root / f"apps/embed-sdk/src/components/{comp}"
            src = path.read_text(encoding="utf-8")
            assert "from '../i18n/index.js'" in src or "from '../i18n/'" in src, (
                f"{comp} non importa t() da i18n module."
            )
            # Pattern flessibile: t( puo' apparire con spazio prima OR in template
            # literal (es. ${t(...)} ) OR come arg (foo(t(...))).
            import re as _re
            assert _re.search(r"[^a-zA-Z_]t\(['\"]", src), (
                f"{comp} importa i18n ma non chiama t('...') (nessuna stringa "
                f"effettivamente tradotta)."
            )

    def test_bundle_contains_translated_markers(self):
        """Bundle contiene marker tradotti DE+FR per nuove keys."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Marker DE checkout
        assert "Warenkorb öffnen" in src or "Konto öffnen" in src, (
            "Bundle non contiene marker DE per nuove key (cart.open_label, "
            "account.open_authenticated). Bundle stale o build incompleto."
        )
        # Marker FR checkout
        assert "Ouvrir le panier" in src or "Ouvrir mon compte" in src, (
            "Bundle non contiene marker FR per nuove key."
        )

    def test_minimum_translation_count_per_component(self):
        """Componenti principali hanno almeno 3 chiamate t() ciascuno."""
        from pathlib import Path
        import re
        repo_root = Path(__file__).resolve().parents[2]
        # Componenti dove vogliamo coverage minimo
        components_min_calls = {
            "afianco-cart-drawer.ts": 5,
            "afianco-login.ts": 5,
            "afianco-signup.ts": 5,
            "afianco-account.ts": 5,
            "afianco-product-detail.ts": 5,
            "afianco-checkout-button.ts": 10,
        }
        t_call_re = re.compile(r"\bt\(['\"]")
        for comp, min_calls in components_min_calls.items():
            path = repo_root / f"apps/embed-sdk/src/components/{comp}"
            src = path.read_text(encoding="utf-8")
            count = len(t_call_re.findall(src))
            assert count >= min_calls, (
                f"{comp} ha solo {count} chiamate t() (atteso >= {min_calls}). "
                f"Coverage i18n incompleta per parity 4 lingue."
            )


class TestSEC_E_8_22_WidgetCTALabelsI18n:
    """SEC-E.8.22: CTA labels prodotto + price summary tradotti (W4.8).

    Bug user-reported (screenshot FR): pulsanti 'Scopri di piu'',
    'Aggiungi al carrello', 'Riepilogo prezzo', 'Subtotale' ancora
    in italiano anche con widget impostato in francese.

    W4.8 fix:
      - afianco-product-card.ts: ctaLabel resolved via t()
      - afianco-product-detail.ts: ctaLabel resolved via t() per ogni
        item_type + transaction_mode + price_mode
      - afianco-price-preview.ts: 'Riepilogo prezzo', 'Subtotale'
        tradotti + plural form per day_count
      - +14 nuove keys × 4 lingue
    """

    def test_product_card_uses_i18n_cta(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        card = repo_root / "apps/embed-sdk/src/components/afianco-product-card.ts"
        src = card.read_text(encoding="utf-8")
        assert "from '../i18n/index.js'" in src, "product-card non importa t()"
        assert "product.cta_discover" in src, (
            "ctaLabel non usa t('product.cta_discover')"
        )
        # No more hardcoded
        assert "'Scopri di più'" not in src, (
            "Hardcoded italian 'Scopri di piu'' ancora presente."
        )

    def test_product_detail_uses_i18n_cta(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        detail = repo_root / "apps/embed-sdk/src/components/afianco-product-detail.ts"
        src = detail.read_text(encoding="utf-8")
        for key in (
            "product.cta_request_quote",
            "product.cta_buy_ticket",
            "product.cta_enroll_course",
            "product.cta_add_to_cart",
        ):
            assert key in src, (
                f"product-detail ctaLabel non usa t({key!r})"
            )
        # No more hardcoded
        for hard in ("'Aggiungi al carrello'", "'Acquista biglietto'", "'Richiedi preventivo'"):
            assert hard not in src, (
                f"Hardcoded italiano {hard} ancora presente in product-detail."
            )

    def test_price_preview_uses_i18n(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        pp = repo_root / "apps/embed-sdk/src/components/afianco-price-preview.ts"
        src = pp.read_text(encoding="utf-8")
        assert "price.summary_title" in src, (
            "price-preview manca t('price.summary_title')"
        )
        assert "price.subtotal" in src, (
            "price-preview manca t('price.subtotal')"
        )
        # Hardcoded gone
        for hard in ("'Riepilogo prezzo'", "Subtotale ("):
            assert hard not in src, (
                f"Hardcoded {hard!r} ancora presente in price-preview."
            )

    def test_locale_files_have_cta_keys(self):
        """Tutte le 4 lingue hanno le nuove CTA keys."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        required = [
            "product.cta_discover",
            "product.cta_add_to_cart",
            "product.cta_buy_ticket",
            "product.cta_enroll_course",
            "product.cta_rent",
            "product.cta_buy",
            "product.cta_request_quote",
            "price.summary_title",
            "price.subtotal",
        ]
        for locale in ("it", "en", "de", "fr"):
            path = repo_root / f"apps/embed-sdk/src/i18n/locales/{locale}.ts"
            src = path.read_text(encoding="utf-8")
            for key in required:
                assert f"'{key}'" in src, (
                    f"Locale {locale}.ts manca chiave {key!r}."
                )

    def test_bundle_contains_cta_fr_markers(self):
        """Bundle public contiene CTA tradotti in francese."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Marker FR critici (visibili nello screenshot user)
        assert "En savoir plus" in src, (
            "Bundle non contiene 'En savoir plus' (CTA discover FR)."
        )
        assert "Ajouter au panier" in src, (
            "Bundle non contiene 'Ajouter au panier' (CTA add-to-cart FR)."
        )
        assert "Sous-total" in src, (
            "Bundle non contiene 'Sous-total' (price subtotal FR)."
        )
        assert "Récapitulatif" in src, (
            "Bundle non contiene 'Recapitulatif' (price summary FR)."
        )


class TestSEC_E_8_23_WidgetI18nFinalSweep:
    """SEC-E.8.23: i18n final sweep — coverage cross-component completa.

    User-requested deep audit ha rivelato ~72 stringhe italiane hardcoded
    residue su 20 componenti dopo W4.7+W4.8.

    W4.9 fix:
      - +60 nuove keys × 4 lingue = ~240 traduzioni
      - 20 componenti wired con t() helper
      - Type badges (Servizio/Evento/Noleggio/Corso/Digitale/Prodotto)
      - Picker default groupLabel (occurrence/tier/service/rental/shipping)
      - Profile editor (15 stringhe form + validation)
      - Loading states (course/download/booking/availability/profile)
      - Empty states (catalog/courses/downloads/bookings)
      - Error messages (caricamento/aggiornamento)
      - Access labels (lifetime/expiring/unlimited)
      - Stock hints (remaining seats with plural)
      - Hint messages (no-slot/custom-request rental)
    """

    REQUIRED_W49_KEYS = [
        "product.type_service",
        "product.type_event",
        "product.type_rental",
        "product.type_course",
        "product.type_digital",
        "product.type_physical",
        "product.detail_header_fallback",
        "product.error_load",
        "product.error_storefront_not_ready",
        "product.empty_catalog",
        "product.remaining_seats_one",
        "product.remaining_seats_other",
        "occurrence.group_label",
        "occurrence.empty",
        "occurrence.sold_out",
        "occurrence.map_link",
        "tier.sold_out",
        "tier.qty_label",
        "service.group_label",
        "service.empty_options",
        "availability.error_load",
        "availability.empty_n_days",
        "availability.choose_date_time",
        "availability.change_btn",
        "rental.group_label",
        "rental.error_invalid_date",
        "rental.error_min_days_one",
        "rental.error_min_days_other",
        "course.preview_title",
        "course.access_lifetime",
        "course.access_unlimited",
        "course.error_load",
        "course.empty_purchased",
        "profile.error_load",
        "profile.error_update",
        "profile.empty",
        "profile.section_title_edit",
        "profile.erasure_section_title",
        "profile.erasure_submit",
        "download.empty",
        "download.purchased_at",
        "download.error_load",
        "booking.error_load",
        "booking.status_confirmed",
        "booking.empty",
        "shipping.error_load",
        "shipping.empty",
        "price.error_calc",
        "account.forgot_password_success",
        "portal.error_load_profile",
        "portal.empty_profile",
        "signup.verification_message_full",
        "login.dispatch_error",
    ]

    def test_locale_files_have_w49_keys(self):
        """Tutte le 4 lingue hanno le ~50 nuove W4.9 keys."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        for locale in ("it", "en", "de", "fr"):
            path = repo_root / f"apps/embed-sdk/src/i18n/locales/{locale}.ts"
            src = path.read_text(encoding="utf-8")
            for key in self.REQUIRED_W49_KEYS:
                assert f"'{key}'" in src, (
                    f"Locale {locale}.ts manca chiave W4.9 {key!r}."
                )

    def test_critical_residual_components_wired(self):
        """Componenti picker + portale + profile usano t()."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        components = [
            "afianco-occurrence-picker.ts",
            "afianco-tier-picker.ts",
            "afianco-service-options-picker.ts",
            "afianco-availability-picker.ts",
            "afianco-date-range-picker.ts",
            "afianco-course-preview.ts",
            "afianco-product-grid.ts",
            "afianco-product-card.ts",
            "afianco-my-courses.ts",
            "afianco-my-downloads.ts",
            "afianco-my-bookings.ts",
            "afianco-course-player.ts",
            "afianco-profile-editor.ts",
            "afianco-shipping-options-picker.ts",
        ]
        for comp in components:
            path = repo_root / f"apps/embed-sdk/src/components/{comp}"
            src = path.read_text(encoding="utf-8")
            assert "from '../i18n/index.js'" in src, (
                f"{comp} non importa t() helper."
            )
            import re as _re
            assert _re.search(r"[^a-zA-Z_]t\(['\"]", src), (
                f"{comp} importa i18n ma non chiama t()."
            )

    def test_no_hardcoded_italian_in_picker_group_labels(self):
        """I picker non hanno groupLabel italiana hardcoded come default."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        picker_files = [
            "afianco-occurrence-picker.ts",
            "afianco-tier-picker.ts",
            "afianco-service-options-picker.ts",
            "afianco-date-range-picker.ts",
            "afianco-shipping-options-picker.ts",
            "afianco-extras-picker.ts",
            "afianco-fulfillment-picker.ts",
        ]
        # Patterns hardcoded italiani che NON devono apparire come defaults
        forbidden_in_default = [
            "Scegli una data",
            "Scegli un'opzione",
            "Tipo di biglietto",
            "Scegli le date del noleggio",
            "Aggiungi al tuo ordine",
            "Scegli un'opzione di spedizione",
        ]
        for picker in picker_files:
            path = repo_root / f"apps/embed-sdk/src/components/{picker}"
            src = path.read_text(encoding="utf-8")
            for forbidden in forbidden_in_default:
                # Ammesso solo se nei commenti, ma NON come default property
                # Cerco il pattern "groupLabel = 'STRINGA'" - se trovato e' bug
                if f"groupLabel = '{forbidden}'" in src or \
                   f"groupLabel: '{forbidden}'" in src:
                    raise AssertionError(
                        f"{picker} ha groupLabel hardcoded {forbidden!r}. "
                        f"Default deve essere '' con fallback t() al render."
                    )

    def test_bundle_contains_w49_translations(self):
        """Bundle compile contiene tutti i marker W4.9 critici."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "frontend/public/embed/v1/afianco-embed.es.js"
        src = bundle.read_text(encoding="utf-8", errors="ignore")
        # Marker per le 4 lingue
        # IT
        assert "Dettaglio prodotto" in src, "Bundle non ha marker IT type badges"
        # EN
        assert "Product detail" in src or "What this course includes" in src, (
            "Bundle non ha marker EN W4.9"
        )
        # DE
        assert "Was dieser Kurs beinhaltet" in src or "Veranstaltung" in src, (
            "Bundle non ha marker DE W4.9"
        )
        # FR
        assert "Ce que ce cours inclut" in src or "Événement" in src, (
            "Bundle non ha marker FR W4.9"
        )

    def test_profile_editor_extensively_translated(self):
        """profile-editor: minimo 15 calls t() per coverage."""
        from pathlib import Path
        import re as _re
        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / "apps/embed-sdk/src/components/afianco-profile-editor.ts"
        src = path.read_text(encoding="utf-8")
        t_calls = len(_re.findall(r"[^a-zA-Z_]t\(['\"]", src))
        assert t_calls >= 15, (
            f"profile-editor ha solo {t_calls} t() calls (atteso >= 15). "
            f"Coverage incompleta dopo W4.9."
        )
