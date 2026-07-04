# Security Hardening — AFianco Backend

Checklist e procedura per gestione dei secret e hardening dell'infrastruttura.

> **Track S — Security Consolidation (Phase 1)**: questo documento è il
> runbook canonico per la security hygiene del backend. Ogni modifica
> deve essere accompagnata da sentinel test in
> `backend/tests/test_invariants_security.py` (classe
> `TestSEC_S1_1_RepoSecretHygiene` e seguenti per Track S).

---

## 1. Secret management

### Regole fondamentali

- **Mai** committare `.env`, `.env.production`, `.env.staging` o qualsiasi file contenente credenziali reali.
- **Mai** incollare chiavi in commit messages, PR description, issue, log di debug committati.
- Usare sempre `.env.example` come template versionato, `.env` come file locale.
- In produzione: secret manager (AWS Secrets Manager, Doppler, 1Password Secrets Automation, Kubernetes Secrets) — **non** file `.env`.

### Secret attualmente gestiti

| Variabile | Scope | Dove ruotare |
|---|---|---|
| `JWT_SECRET_KEY` | Sessioni utente | Generare con `openssl rand -hex 32`, aggiornare `.env`. Rotazione invalida tutte le sessioni attive. |
| `STRIPE_SECRET_KEY` | Pagamenti | [Stripe dashboard → Developers → API keys](https://dashboard.stripe.com/apikeys) |
| `STRIPE_PUBLISHABLE_KEY` | Pagamenti (lato client) | Stesso pannello Stripe |
| `STRIPE_CLIENT_ID` | Connect | [Stripe Connect settings](https://dashboard.stripe.com/settings/connect) |
| `ANTHROPIC_API_KEY` | LLM (Claude) | [Anthropic console](https://console.anthropic.com/settings/keys) |
| `BREVO_API_KEY` | Email transazionali | [Brevo SMTP & API](https://app.brevo.com/settings/keys/api) |
| `MONGO_URL` | Database | Cambiare password Mongo (`db.changeUserPassword`) |

---

## 2. Se una chiave è stata esposta (leak detected)

### Azioni immediate

1. **Ruota subito** la chiave esposta dalla dashboard del provider. Non aspettare.
2. Se la chiave è stata committata su git:
   - Verifica con: `git log -p --all -- path/to/secret_file | grep -i 'key_or_pattern'`
   - Rimuovi dall'HEAD: `git rm --cached path/to/file`
   - Se il repo è pubblico o condiviso: riscrivi la storia con [git-filter-repo](https://github.com/newren/git-filter-repo):
     ```bash
     git filter-repo --invert-paths --path backend/.env
     git push --force-with-lease origin main
     ```
     ⚠️ Force-push riscrive la storia — coordinati con il team.
3. Invalida sessioni esistenti se era `JWT_SECRET_KEY` (bastano uno script `await db.users.update_many({}, {"$set": {"password_changed_at": now}})`).
4. Monitora la dashboard del provider per uso anomalo (Stripe radar, Anthropic usage logs, Mongo logs).

### Post-mortem

- Annota data leak, vettore (git history / log / screenshot), azioni intraprese.
- Aggiungi regole a `.gitignore` se necessario.
- Considera [git-secrets](https://github.com/awslabs/git-secrets) pre-commit hook.

---

## 3. Local dev setup

```bash
cd backend
cp .env.example .env
# Modifica .env con i valori reali (JWT_SECRET_KEY obbligatorio)
openssl rand -hex 32   # copia l'output dentro JWT_SECRET_KEY
```

Il server `uvicorn server:app` **rifiuta di avviarsi** se `JWT_SECRET_KEY` non è settata (intentional, vedi `auth.py:12-18`).

---

## 4. Production checklist

Prima del deploy in produzione:

- [ ] `backend/.env.production` **NON** è nel repo (verifica con `git ls-files | grep env`).
- [ ] `JWT_SECRET_KEY` prod è distinto da quello di staging e dev.
- [ ] Stripe keys prod sono `sk_live_*` / `pk_live_*`, non `sk_test_*`.
- [ ] `CORS_ORIGINS` è una lista esplicita di domini, non `*`.
- [ ] MongoDB ha autenticazione attiva (`MONGO_INITDB_ROOT_USERNAME` + password, non default).
- [ ] Mongo port 27017 **non** esposta all'esterno (solo network Docker interno).
- [ ] nginx con HTTPS valido (Let's Encrypt via certbot, vedi `deploy/` per la config).
- [ ] Rate limiting attivo su tutti gli endpoint auth-critical.
- [ ] Backup MongoDB automatico (`deploy/backup.sh` via cron).

---

## 5. Rate limiting

Policy standard per endpoint:

| Tipo endpoint | Limite |
|---|---|
| Auth (login, signup, forgot password) | 5/min |
| Auth (retry, verify) | 10/min |
| Dashboard read | 30/min |
| POST write (orders, products, events) | 10/min |
| Payment verify (Stripe round-trip) | 6/min |
| File upload / import | 5/hour |
| Webhook inbound (Stripe) | 100/min |

Implementato via `slowapi` (`@limiter.limit("X/min")`). Vedi `server.py` per setup globale.

Endpoint attualmente NON rate-limited (da sistemare):
- `POST /event-occurrences/wizard`
- `POST /event-occurrences/{id}/duplicate`
- `POST /products` / `POST /products/{id}/duplicate`
- `POST /orders/import` / `POST /orders/import-with-mapping`
- `POST /orders/{id}/mark-paid` / `mark-unpaid`

---

## 6. Input validation

Tutti i route devono usare Pydantic schema con `Field(..., constraints)`:

```python
class OrderLineCreate(BaseModel):
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount_pct: float = Field(ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=2000)
```

Geo, price, quantity, date — SEMPRE bound con `ge`/`le`/`min_length`/`max_length`.

---

## 7. Permission model

Ruoli:
- `system_admin` — platform-level, `organization_id=None`. Unica persona che può accedere a `/api/admin/*`.
- `admin` — org-level, accede solo alla propria org tramite `organization_id` scoping enforzato nei repository.
- `user` — org-level read-only o limitato (dipende dal route).
- `customer` — via `CustomerAccount`, scoped per-org tramite token `type="customer"`.

Depends di riferimento in `auth.py`:
- `get_current_user` — baseline auth
- `require_admin` — org admin
- `require_system_admin` — platform admin
- `get_current_customer` — customer portal auth

**Nessun** bypass via env var o query param. Nessun "superuser" non loggato.

---

## 8. Audit & logging

- Tutti i mutation endpoints emettono `audit_logs` record (`action`, `actor_id`, `target_id`, `org_id`, `ts`).
- Log livello INFO di default, DEBUG solo in dev.
- **Non** loggare: password, token JWT, stripe payment intents completi, email body con dati sensibili.
- PII nei log: mascherare email (`u***@ex.com`), telefoni.

---

## 9. Stato corrente rotation (audit 2026-05-28)

**Track S Step 1.1**: audit del repo ha confermato che `backend/.env`
è correttamente untracked (commit `1aeb4d7`) e `.gitignore` copre
tutti i pattern necessari. Tuttavia, le chiavi esposte tra il commit
`287c633` (2026-03-07) e `1aeb4d7` (2026-04-22) **non sono ancora state
ruotate**.

| Chiave | Status | Priorità | Dove ruotare |
|---|---|---|---|
| `JWT_SECRET_KEY` | 🔴 ESPOSTA, non ruotata | **P0** | Locale: `openssl rand -hex 32` → `.env`. Invalida tutte le sessioni admin attive (effetto desiderato dopo rotation). |
| `ANTHROPIC_API_KEY` | 🔴 ESPOSTA, non ruotata | **P0** | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) → genera nuova → revoca vecchia |
| `STRIPE_SECRET_KEY` (test) | 🔴 ESPOSTA, non ruotata | **P1** | [dashboard.stripe.com/test/apikeys](https://dashboard.stripe.com/test/apikeys) → "Roll key" |
| `STRIPE_CLIENT_ID` | 🟡 ESPOSTA, non ruotata | **P2** | [dashboard.stripe.com/settings/connect](https://dashboard.stripe.com/settings/connect) — richiede revoke OAuth connessioni esistenti |
| `EMERGENT_LLM_KEY` | ✅ Rimosso dal `.env` corrente | OK | n/a (key non più in uso) |
| `BREVO_API_KEY` | ✅ Mai esposta in git | OK | n/a (aggiunta post-untrack) |

**Mitigazione attuale**: il repo è privato (verificato `2026-05-28`),
quindi exposure limitata a chi ha già clone access. Non è una crisi
immediata ma la rotation va completata prima di:
- aprire il repo a contributor esterni
- pushare su mirror pubblici (CDN distribution, Track E)
- on-board pilot merchant (Track F)

**Quando ruotare**: idealmente entro la chiusura della Track S Step 1.2.

---

## 10. Pre-commit hook (opzionale, raccomandato)

Per bloccare commit accidentali di file `.env` o pattern key, installa
[git-secrets](https://github.com/awslabs/git-secrets):

```bash
# macOS
brew install git-secrets

# Setup nel repo (una sola volta)
cd /path/to/BI_PMI
git secrets --install
git secrets --register-aws    # patterns AWS standard
# Patterns custom afianco
git secrets --add 'sk_live_[a-zA-Z0-9]{24,}'
git secrets --add 'sk_test_[a-zA-Z0-9]{60,}'
git secrets --add 'sk-ant-api03-[a-zA-Z0-9_-]{50,}'
git secrets --add 'xkeysib-[a-f0-9]{60,}'
# Allowlist dei file di test che contengono i pattern come regex
git secrets --add --allowed 'backend/tests/test_invariants_security.py'
git secrets --add --allowed 'docs/SECURITY_HARDENING.md'
```

Da quel momento ogni `git commit` esegue scan automatico e fallisce se
trova match.

---

## 11. Sentinel test di regressione

Track S aggiunge sentinel pytest che falliscono in CI se la repo
hygiene degrada:

| Test | File | Cosa pinna |
|---|---|---|
| `test_no_real_env_files_tracked` | `backend/tests/test_invariants_security.py` | `.env` mai tracked (eccezione: `frontend/.env` con solo `REACT_APP_*`) |
| `test_gitignore_covers_env_patterns` | idem | `.gitignore` ha pattern `.env`, `.env.*`, `!.env.example` |
| `test_security_hardening_doc_exists` | idem | Questo doc esiste con sezioni minime |
| `test_no_hardcoded_secret_patterns_in_tracked_files` | idem | Grep su tutti i file tracked per pattern Stripe/Anthropic/Brevo (whitelist documentata) |
| `test_helper_returns_none_for_production` | idem | `_docs_urls_for_env("production")` → `(None, None, None)` |
| `test_helper_returns_none_for_staging` | idem | Idem per staging |
| `test_helper_returns_defaults_for_development` | idem | Development → `/docs`, `/redoc`, `/openapi.json` |
| `test_app_uses_helper_for_docs_config` | idem | `app.docs_url` consistente con helper (anti-drift) |

Run:
```bash
cd backend && ./venv/bin/pytest tests/test_invariants_security.py::TestSEC_S1_1_RepoSecretHygiene -v
cd backend && ./venv/bin/pytest tests/test_invariants_security.py::TestSEC_S1_3_DocsExposureGated -v
```

---

## 12. OpenAPI docs exposure (Track S Step 1.3)

I path `/docs` (Swagger UI), `/redoc` (ReDoc), `/openapi.json` espongono
lo schema COMPLETO dell'API (tutti gli endpoint, payload shapes, response
models). In production sono un vettore di reverse-engineering — un
attaccante con accesso a `/docs` ha la mappa stradale dell'app.

**Policy**: gated via env var `ENVIRONMENT`:

| ENVIRONMENT | docs_url | redoc_url | openapi_url |
|---|---|---|---|
| `production` | None (404) | None (404) | None (404) |
| `staging` | None (404) | None (404) | None (404) |
| `development` / unset | `/docs` | `/redoc` | `/openapi.json` |

Implementato in `backend/server.py` come pure function `_docs_urls_for_env()`
per testabilità. Vedi sentinel `TestSEC_S1_3_DocsExposureGated`.

**NB load_dotenv override**: `server.py:12` usa `load_dotenv(..., override=True)`
quindi il `.env` file sovrascrive le shell env. In production deploy:
- NON includere il file `backend/.env` nell'immagine container
- OPPURE settare `ENVIRONMENT="production"` nel `.env` di prod

~~Da fare in S1.4: valutare `override=False`~~ ✅ **Fatto in S1.4** —
shell env vars vincono. In container deploy puoi settare `ENVIRONMENT=production`
direttamente nella shell (no .env nell'immagine) o nel .env (entrambi
funzionano, ma il primo e' best practice).

---

## 13. Global exception handler (Track S Step 1.4)

Pre-S1.4: FastAPI default lasciava `uncaught Exception` bubble fino a
Starlette → 500 con potenziale stacktrace nel body se `debug=True` o
config drift. Anche senza body leak, mancavano log strutturati per
debug + Sentry capture.

**Policy**:
- Catch-all handler `_global_exception_handler` registrato per `Exception`
- Log SERVER-SIDE: stacktrace COMPLETO via `logger.exception` (debug +
  Sentry breadcrumb)
- Response CLIENT-SIDE: body OPACO `{"detail": "Internal server error",
  "request_id": "<echo X-Request-ID>"}` — niente leak di:
  - exception message (puo' contenere DB passwords, paths, secret)
  - exception class name (info leak su lib usata)
  - stacktrace (path interni del codebase)

Implementato in `backend/server.py` come `_global_exception_handler()`
async function. Vedi sentinel `TestSEC_S1_4_GlobalExceptionHandler`.

**Bonus invariant**: il sentinel test verifica anche che `FastAPI(debug=True)`
non sia hardcoded nel source — `debug=True` in production espone
stacktrace nei response body, anche senza il global handler. Doppia
defense.

---

## 14. Login & signup anti-enumeration (Track S Steps 2.1 + 2.2)

### 14.1 Login flow (S2.1)

**Pre-fix attack** (customer + admin login):
```
for email in wordlist:
    r = POST /api/customer-auth/login { email, password: "x" }
    # 423 → email exists + locked (LEAK)
    # 403 → email exists + not verified (LEAK)
    # 401 "Account disattivato." → exists + disabled (LEAK via body)
    # 401 generic → not exists OR wrong password (no info)
```

**Post-fix order of checks**:
1. `find_by_email` → if not found, **RUN bcrypt verify(DUMMY_HASH)** for
   timing-constant, then raise uniform `ValueError`.
2. `verify_password` → if wrong, raise SAME uniform `ValueError`.
3. ⇒ From here caller proved password knowledge — state errors are safe.
4. lockout / is_active / email_verified → structured errors for legit UX.

**Implemented in**:
- `backend/services/customer_auth_service.py::customer_login`
- `backend/services/auth_service.py::login`
- Both files have `_BCRYPT_DUMMY_HASH` constant.

**Pin**: `TestSEC_S2_1_LoginAntiEnumeration_{Customer,Admin}Service` + `TestSEC_S2_1_LoginRouter_UniformResponse` (8 tests).

### 14.2 Signup flow (S2.2)

**Pre-fix attack** (customer signup):
```
POST /api/customer-auth/signup { email, password: <valid>, all consents }
# 202 verification_required → email NEW (account created)
# 500 internal server error → email EXISTS (DuplicateKeyError on unique index)
```

**Post-fix**: pre-check `find_by_email` BEFORE bcrypt/create; if duplicate,
return identical 202 response (no body diff). Router also catches
`DuplicateKeyError` from race conditions with same uniform body.

**Critical sub-invariant**: `auto_login=True` + duplicate email DOES NOT
mint a token. Minting would BE the enumeration leak we're closing.

**Implemented in**:
- `backend/services/customer_auth_service.py::customer_signup` (pre-check)
- `backend/routers/customer_auth.py::signup` (DuplicateKeyError catch)

**Pin**: `TestSEC_S2_2_SignupAntiEnumeration_CustomerService` (4 tests)
+ `TestSEC_S2_2_SignupRouter_UniformResponse` (1 test).

### 14.3 Residual risk: admin signup 409

`backend/routers/auth.py::signup` ritorna ancora `409 EMAIL_ALREADY_REGISTERED`
(line 105-113). Questo è leak SE `registration_mode == "public"`.

**Mitigazione attuale**: in production `registration_mode` di default è
`invite_only` — l'attacker non passa la prima validazione (riga 50-76,
gate `invite_token` required). Senza invite valid → 403 prima del 409.

**Accepted residual risk** per V1: il refactor del 409 → 202 richiede
update del frontend admin signup form (gestione status code). Da fare
in Phase 2 quando si tocca quel flow.

---

## 15. Token single-use enforcement (Track S Step 2.3)

Verification email token + reset password token devono essere
**single-use**: dopo il consumo, lo stesso token non puo' essere
riutilizzato anche se ancora dentro al TTL.

**Stato pre-audit**: single-use era gia' implementato implicitamente
(post-success update setta `*_token_hash=None` e `*_token_expires=None`).
Un secondo `find_by_*_token_hash(token_hash)` ritorna None → 400
"Token non valido o scaduto."

**S2.3 deliverable**:
1. **Sentinel test** che PIN l'invariant (anti-regression): se in futuro
   qualcuno toglie il null-out dei `_token_hash`, il sentinel fallisce.
2. **Detection log** INFO sui `token consumption failed`: SOC team puo'
   alertare su spike per-IP (indicatore di tentativi di riuso di token
   intercettati).

**TTL attuali (best-practice, no change)**:
| Token | TTL | File |
|---|---|---|
| Customer verification | 24h | `customer_auth_service.py:349` |
| Customer reset password | 1h | `customer_auth_service.py:646` |
| Customer resend verification | 24h | `customer_auth_service.py:788` |
| Admin verification | 24h | `auth_service.py:118` |
| Admin reset password | 1h | (in auth router/service) |

**Pin**:
- Service-level: `TestSEC_S2_3_TokenSingleUse_Customer` (4 test)
- Router-level: `TestSEC_S2_3_TokenSingleUse_AdminRouter` (4 test)

---

## 16. Per-email login rate limit (Track S Step 2.4)

**Threat**: slowapi per-IP rate limit (10/min) e' insufficient contro
botnet — attaccante con 1000 IPs moltiplica throughput per 1000. Account
lockout (Onda 29/30: 5 fail → 15min) cap solo gli ULTIMI 5 tentativi
consecutivi, ma un attacker che alterna 20 password diverse senza far
scattare il counter (es. test parallel su account distinti) bypassa.

**S2.4**: aggiunge per-email rate limit cross-IP (sliding 1h, 20/h cap)
PRIMA del DB lookup, riusando l'helper `check_email_rate` esistente
(Phase 1 D2, in-memory sliding-window per worker).

**Quando attiva (rate-limit hit)**:
1. NO `find_by_email` (early bail saves DB ops + niente leak via DB error)
2. SI `verify_password(pw, _DUMMY_HASH)` (timing-constant — bcrypt sempre)
3. Raise `ValueError("Email o password non corretti.")` → 401 uniform
4. Log INFO con email redacted per detection SOC

**Uniform 401 = preserva anti-enumeration**: un attaccante che spamma una
email vede esattamente le stesse risposte di un legit user con password
sbagliata. NO leak "questa email e' rate-limited" (che rivelerebbe attivita').

**Action keys**:
| Bucket | Cap | Usato in |
|---|---|---|
| `customer_login` | 20/h | `customer_auth_service.customer_login` |
| `admin_login` | 20/h | `auth_service.login` |
| `customer_forgot_password` | 10/h | `customer_auth.forgot_password` (D2) |
| `customer_resend_verification` | 5/h | `customer_auth.resend_verification` (D2) |
| `admin_forgot_password` | 10/h | `auth.forgot_password` (D2) |
| `admin_resend_verification` | 5/h | `auth.resend_verification` (D2) |

Bucket keys distinti → cross-action interference esclusa (un utente che
fa 10x forgot-password NON viene bloccato sul login).

**Pin**: `TestSEC_S2_4_LoginPerEmailRateLimit` (5 test).

---

## 17. Sensitive ops endpoints rate limit (Track S Step 2.5)

Chiude la Sub-Track S2. Pin sull'invariant rate-limit per i 3 endpoint
flagged dall'audit P1:

| Endpoint | Per-IP | Per-email | Lockout extra |
|---|---|---|---|
| `/auth/request-invite` | 3/h slowapi | **3/h S2.5 NEW** | — |
| `/auth/reactivate-account` | 3/h slowapi | — | in-memory 5 fail → 15min |
| `/auth/resend-verification` | slowapi | 5/h (D2) | — |
| `/customer-auth/resend-verification` | slowapi | 5/h (D2) | — |

`/request-invite` era l'unico gap — per-IP 3/h cap bypassabile con
botnet (1000 IP × 3/h = 3000/h sulla stessa email). S2.5 aggiunge cap
per-email cross-IP 3/h come backstop.

Anti-enumeration preserved: rate-limit hit ritorna **stesso 202 body
del success path** (`{"status": "sent"}`). Attaccante non distingue.

**Pin**: `TestSEC_S2_5_SensitiveOpsRateLimit` (9 test). Include test
`test_rate_limit_action_keys_complete_set` che verifica TUTTE le 7
action keys (login + signup + ops) siano presenti — catch globale
contro regressione di QUALSIASI rate limit S2/D2.

---

## 18. ID format — UUID v4 invariant (Track S Step 3.1)

**Threat**: `/api/public/embed/cart/{cart_id}` e `/api/public/embed/orders/{order_id}`
sono no-auth (cross-org isolation via slug query param). Se gli ID
fossero int sequenziali (es. ObjectId Mongo native, auto-increment),
attaccante iterando 1..N legge ogni cart/ordine.

**Stato attuale (audit S3.1)**: ✅ entrambi sono UUID v4 via
`models/common.py::generate_id()` → `str(uuid.uuid4())`.

| Model | ID format | File |
|---|---|---|
| `Order.id` | `<uuid-v4>` (36 char) | `models/order.py:252` |
| `Cart.id` | `cart_<uuid-v4>` (41 char) | `models/cart.py:116` |
| `CustomerAccount.id` | `<uuid-v4>` | `services/customer_auth_service.py:358` |
| `User.id` | `<uuid-v4>` | (defaults to generate_id) |
| Order `order_number` | `ORD-NNNN` sequenziale | display-only, NON used per lookup |

**Entropy**: UUID v4 = 122 bit di entropia = 5.3 × 10³⁶ valori possibili.
Brute-force computazionalmente impossibile (worst case ~10²⁵ anni a
1 trillion guess/sec).

**Pin**: `TestSEC_S3_1_IDsAreUUIDv4` (4 test):
- `generate_id()` ritorna UUID v4 valido (100 sample, no collision)
- `Order.id` default_factory usa `generate_id`
- `Cart.id` default_factory usa `f"cart_{generate_id()}"` (prefix + UUID)
- Critical models (Order/Cart/CustomerAccount/User) non hanno `id: int`
  (anti-pattern auto-increment).

**Note**: `order_number` (`ORD-0042`) IS sequential by design — è il
display-friendly per UI/email. NON è usato come key di lookup nelle
query (query usa `id` UUID). Quindi enumeration di `order_number`
non da' accesso a nessun ordine.

---

## 19. Idempotency race condition fix (Track S Step 3.2)

**Pre-fix bug** (riconosciuto in `middleware/idempotency.py:27`):

```
1. Request A arriva con Idempotency-Key: X → cache miss
2. Request A entra in call_next() (es. Stripe checkout, ~3 secondi)
3. Request B arriva con stessa Idempotency-Key: X PRIMA che A finisca
4. Request B cache miss (A non ha ancora scritto la response)
5. Request B entra in call_next() → 🔴 SECONDO ordine Stripe creato
```

L'`update_one(..., upsert=True)` esistente in `_store_cached_response`
veniva chiamato DOPO call_next → too late per prevenire la race.

**Post-fix design** (claim-the-lock pattern):

1. **Unique index** su `idempotency_keys_collection.digest`
   (`database.py:create_indexes()`).
2. **Insert pending doc BEFORE call_next** via `_claim_idempotency_lock`:
   - `insert_one({digest, status: "pending", ...})` → exactly one
     concurrent caller wins (unique index)
   - Loser gets `DuplicateKeyError` → returns False
3. **Loser polls** via `_poll_for_lock_completion`:
   - Interval 200ms, timeout 30s
   - Returns the winner's cached response when ready
   - On timeout → 409 with `IDEMPOTENCY_RACE_TIMEOUT` code
4. **`_store_cached_response` upgrades to UPDATE** (no upsert) the
   pending doc with response data + `status: completed`.

**Fail-safe**: se `pymongo` non disponibile o Mongo unreachable,
`_claim_idempotency_lock` ritorna True (degraded mode = pre-fix
behavior) — meglio rischiare un double-process raro che 500 tutte le
request.

**Pin**: `TestSEC_S3_2_IdempotencyRaceCondition` (6 test):
- Unique index presence in `create_indexes`
- Helper functions exist (`_claim_idempotency_lock`, `_poll_for_lock_completion`)
- Helper return True/False correctly based on insert outcome
- dispatch invokes claim BEFORE call_next (source-level ordering check)
- 409 timeout branch present with `IDEMPOTENCY_RACE_TIMEOUT` code

---

## 20. allowed_origins validation (Track S Step 3.3)

**Pre-fix**: `Store.allowed_origins: List[str] = Field(default_factory=list)`
con zero validation. Anche se `middleware/dynamic_cors.py` fa exact match
(quindi `"*"` di per se' non bypassa), avere `"null"` o `"*"` nella lista
e' un config error che vale la pena bloccare alla fonte.

**Threat scenarios bloccati**:
- `"null"` → CORS bypass per `Origin: null` requests (file://, sandbox iframe)
- `"*"`   → wildcard catch-all (confusione + future drift se CORS middleware
  viene refactorato a allow-list pattern)
- `"javascript:..."`, `"data:..."`, `"file://..."` → schemi non-HTTP non
  validi come Origin header
- Empty / whitespace → noise nel record DB
- Lista > 10 entries → cache LRU overflow nel middleware

**Validator rules** (`models/store.py::_validate_allowed_origins`):
| Rule | Limit |
|---|---|
| Max entries | 10 |
| Max char per entry | 200 |
| Required scheme | `http://` or `https://` |
| Forbidden values | `null`, `*`, empty/whitespace |
| Sanitization | trim whitespace, deduplicate (preserve order) |

**Implementation**:
- Pure function `_validate_allowed_origins(values: List[str]) -> List[str]`
- Attached as `@field_validator("allowed_origins", mode="before")` on `Store`
- Fires both on instantiation AND on DB record load (Pydantic deserialize)

**Note**: HTTP (non-HTTPS) accettato per supportare dev locale del merchant.
Production-only HTTPS enforcement appartiene al deploy config, non al
model validator (merchant might legitimately run localhost during onboarding).

**Pin**: `TestSEC_S3_3_AllowedOriginsValidation` (12 test) — copre tutti
i casi positivi + negativi + integration con `Store(...)` instantiation.

---

## 21. Catalog scrape defense (Track S Step 3.4)

**Threat**: `/api/public/embed/products/{slug}` espone prezzi + stock
quantity in chiaro (dati competitivi sensibili). Pre-S3.4 un attaccante
con singolo IP scaricava catalogo intero in ~15 min:
- Rate limit 60/min per-IP
- Cache TTL 60s → ogni request raggiunge l'origin
- Pagination ~10 prodotti/page = 9000 prodotti scrapati in 15 min

**S3.4 fix**: bump Cache-Control TTL da 60s → 300s su 3 endpoint
read-only (init, categories, products). Effetto:
- CDN/browser cache hit aumenta → origin throughput ridotto 5x
- Tempo di scrape per merchant medio: 15min → ~75min
- Trade-off: prezzo/stock changes propagano in 5min invece di 1min
  (accettabile, mitigato da ETag + stock check fresh al cart submit)

| Endpoint | TTL pre | TTL post | Rate limit (invariato) |
|---|---|---|---|
| `/embed/init/{slug}` | 60s | **300s** | 60/min per-IP |
| `/embed/categories/{slug}` | 60s | **300s** | 60/min per-IP |
| `/embed/products/{slug}` | 60s | **300s** | 60/min per-IP |

**Per-IP cumulative limit** (cap aggregato 300/min su tutto `/embed/*`):
deferred a V2. Richiede middleware custom — sentinel anti-regression
gia' in place per i decoratori esistenti.

**Pin**: `TestSEC_S3_4_CatalogScrapeDefense` (7 test) — verifica TTL=300
+ rate-limit decorator presence + `public` directive nei Cache-Control.

---

## 22. Dynamic CORS reject uniform response (Track S Step 3.5)

Chiude la Sub-Track S3. Il middleware `dynamic_cors` pre-fix ritornava
body distinct per ogni reject reason:

| Reason | Pre-fix body | Status |
|---|---|---|
| Origin header missing | `"Origin header required for embed endpoints."` | 400 |
| Slug missing | `"Store slug required (path param, query, or X-Afianco-Store-Slug header)."` | 400 |
| Origin not allowed | `f"Origin {origin!r} not authorized for store {slug!r}."` | 403 |

**Information leak vectors**:
- Body diff → attacker scopre "lo slug esiste" (raggiungendo il lookup
  step) vs "lo slug non esiste" (fermandosi prima)
- Body include `origin` + `slug` literal → attacker scrape i reject body
  per costruire mappa degli origin tentati (utile per analytics di attack
  pattern, per individuare honeypot, ecc.)
- Status 400 vs 403 → leak di quale check ha fatto fail (early-exit
  cascade visible)

**S3.5 fix**: tutti e 3 i path → `PlainTextResponse("Forbidden", 403)`.
Server-side `logger.warning(origin=%s, slug=%s, path=%s, method=%s)`
preservato per debug + SOC alerting.

**Pin**: `TestSEC_S3_5_DynamicCORSRejectUniform` (4 test):
- Body literal `"Forbidden"` su tutti e 3 i reject branch
- Anti-regression contro pre-fix message keywords (`not authorized for store`,
  `Origin header required`, `Store slug required`)
- Server-side logger preserva i dettagli
- Status uniforme 403 (no 400 leak)

**Test esistente aggiornato**: `tests/test_invariants_dynamic_cors.py::TestF3_CustomerOptInGuard::test_strict_embed_path_enforces_without_slug_signal` cambiato da `assert status == 400` a `assert status == 403` (intenzionale, documentato).

---

## Sub-Track S3 status — COMPLETE (5/5)

| Step | Cosa | Commit | Sentinel |
|---|---|---|---|
| S3.1 | UUID v4 invariant pin (cart_id, order_id) | `f433953` | 4 |
| S3.2 | Idempotency race condition fix | `d2aa111` | 6 |
| S3.3 | `allowed_origins` Pydantic validation | `580d255` | 12 |
| S3.4 | Catalog scrape defense (cache TTL 300s) | `b704cdf` | 7 |
| S3.5 | CORS reject uniform response | _(this commit)_ | 4 |

**Sub-Track S3 sentinel totali: 33**

---

## 23. /metrics endpoint authentication (Track S Step 4.1)

**Threat**: pre-S4.1 `/metrics` no-auth, affidato solo a reverse-proxy
ACL. Se per config error (es. nginx misrouted, IP whitelist sbagliata,
direct Kubernetes service exposure) il path arriva su internet, expone:
- `request_count_total` per path/method/status → mappa endpoint
- `request_duration_seconds` histogram → timing attack fingerprinting
- `cors_rejections_total` per slug → quanti attacchi tentati
- `idempotency_hits_total` → correlation con throughput

**S4.1 fix** (defense-in-depth, app-level token):

```
ENVIRONMENT=production or staging:
  · METRICS_AUTH_TOKEN env var REQUIRED
  · Missing → 503 (fail-closed default-deny)
  · Caller must send: X-Metrics-Token: <value>
  · Token mismatch → 401 Unauthorized

ENVIRONMENT=development (or unset):
  · No auth (dev convenience per Prometheus local)
```

**Generate token**:
```bash
openssl rand -hex 32  # 64 char hex (256-bit entropy)
```

**Prometheus scraper config**:
```yaml
scrape_configs:
  - job_name: afianco
    static_configs: [{ targets: ['afianco-backend:8000'] }]
    metrics_path: /metrics
    authorization:
      type: X-Metrics-Token
      credentials: ${METRICS_AUTH_TOKEN}
```

**Defense in depth**: token in-app + nginx ACL (esistente) = doppia
barriera. Anche se nginx config error, token blocca.

**Pin**: `TestSEC_S4_1_MetricsAuth` (6 test):
- Helper `_metrics_auth_required()` ritorna True per production/staging,
  False per dev/test/unset
- Handler source check: invoca helper, legge `METRICS_AUTH_TOKEN`,
  legge `X-Metrics-Token` header
- Fail-closed branch 503 presente
- 401 + `Unauthorized` body uniforme
- Esattamente 1 route `/metrics` registrata (no duplicate)

---

## 24. CI pipeline test gating (Track S Step 4.2)

**Pre-S4.2**: zero GitHub Actions workflow (`.github/` aveva solo
`dependabot.yml`). 491+ sentinel test giravano solo localmente — PR
mergeable senza validazione automatica → regression possibili.

**S4.2** crea `.github/workflows/test.yml` con 3 job in parallelo:

| Job | Cosa testa | Timeout |
|---|---|---|
| `backend-pytest` | pytest backend (490+ invariant + business) | 10min |
| `embed-sdk-vitest` | 128 sentinel Web Components Lit | 8min |
| `packages-vitest` | shared-types, api-client, design-tokens | 5min |
| `ci-passed` | Aggregate gate (single status per branch protection rule) | 1min |

**Triggers**: `pull_request` su main + `push` su main + `workflow_dispatch`
(manual).

**Optimizations**:
- pip cache su `requirements.txt` hash → backend job warm < 30s install
- pnpm cache su `pnpm-lock.yaml` hash → JS jobs warm < 20s install
- `concurrency.cancel-in-progress: true` → push veloci cancellano run
  vecchi (saving Actions minutes)
- `timeout-minutes` per job → no runner stuck infinite

**Branch protection setup** (manuale GitHub UI):
1. Settings → Branches → Add rule for `main`
2. Require status checks to pass: select `ci / all-passed`
3. Require branches up to date before merging: ✓
4. Include administrators: ✓ (no bypass)

**Pin**: `TestSEC_S4_2_CIWorkflowPresent` (8 test) — verifica struttura
workflow + triggers + jobs + concurrency + caching. Sentinel cattura
qualsiasi rimozione o dilution del CI.

---

## 25. Security scanning workflow (Track S Step 4.3)

`.github/workflows/security.yml` aggiunge SAST + dependency CVE
scanning come gating job. Complementa GitHub Dependabot (PR-creation
post-event) con scanning attivo in CI.

| Job | Tool | Scope | Gate |
|---|---|---|---|
| `bandit` | [Bandit](https://github.com/PyCQA/bandit) | Python SAST OWASP | severity ≥ HIGH |
| `pip-audit` | [pip-audit](https://github.com/pypa/pip-audit) | PyPI advisory DB | strict (any vuln) |
| `pnpm-audit` | `pnpm audit` | npm advisory DB | severity ≥ HIGH |
| `security-passed` | aggregate gate | — | all 3 must succeed |

**Triggers**: PR/push main + weekly schedule (`cron: '0 6 * * 1'` =
Monday 06:00 UTC, after Dependabot's window so auto-merged dep updates
get re-scanned).

**Bandit config** (skip benign false positives):
- `--skip B101` (assert) — useful in tests, fired in fixtures
- `--skip B104` (hardcoded 0.0.0.0 bind) — intentional uvicorn dev
- `--skip B311` (pseudo-random) — intentional retry jitter
- `--exclude backend/tests,backend/venv,backend/__pycache__`

**Trade-off accettato**:
- pnpm `--audit-level high` filters out low-severity transient advisories
  che inquinerebbero il CI. Medium-low riportato solo nei log.
- Bandit livello `-ll -ii` (HIGH severity + HIGH confidence) — focus su
  veri rischi, evita noise di pattern ambigui.

**Pin**: `TestSEC_S4_3_SecurityWorkflowPresent` (9 test) — verifica
presence del workflow, dei 3 job + aggregate gate, dei trigger correct,
dell'audit-level high configurato. Sentinel cattura qualsiasi
rimozione o downgrade del security scan.

---

## 26. Coverage reporting (Track S Step 4.4)

Chiude Sub-Track S4. `pytest-cov` installato in CI workflow, coverage
report XML generato + uploaded come GitHub Actions artifact (retention
30gg).

**Config**: `backend/.coveragerc` definisce:
- `source = .` (backend root)
- `omit = venv/*, tests/*, scripts/*, __pycache__/*` (no inflate %)
- Exclude lines: pragma no cover, `__main__`, `TYPE_CHECKING`,
  `@abstractmethod`, ecc.

**CI integration** (in `test.yml::backend-pytest`):
```yaml
- run: pip install pytest-cov
- run: pytest --cov=. --cov-report=xml --cov-report=term-missing:skip-covered
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: backend-coverage
    path: backend/coverage.xml
```

**Per V1: informational only, no gating threshold**. Baseline empirico
emergera' dai primi run CI; in V2 setteremo soglia minimum (es. 70%)
e fail CI sotto quel valore.

**JS coverage** (embed-sdk, packages) deferred a V2 — richiede:
- Install `@vitest/coverage-v8` devDep
- Update `vite.config.ts` con coverage section
- Workflow flag `--coverage` (gia' supportato vitest)

**Pin**: `TestSEC_S4_4_CoverageReporting` (6 test):
- `.coveragerc` esiste con exclude su venv + tests
- Workflow installa pytest-cov
- pytest invocato con `--cov` + `--cov-report=xml`
- Coverage uploaded come artifact `backend-coverage`
- Upload step usa `if: always()` (coverage anche su test failure)

---

## Sub-Track S4 status — COMPLETE (4/4)

| Step | Cosa | Commit | Sentinel |
|---|---|---|---|
| S4.1 | /metrics endpoint auth (token + env gate) | `cee7aa9` | 6 |
| S4.2 | CI test pipeline (pytest + vitest gating) | `8baf579` | 8 |
| S4.3 | Security scanning workflow (Bandit + audit) | `5760344` | 9 |
| S4.4 | Coverage reporting (pytest-cov + artifact) | _(this commit)_ | 6 |

**Sub-Track S4 sentinel totali: 29**

---

## 27. Anti-enumeration consolidation (Track S Step 5.1)

Apre Sub-Track S5 (Regression & sentinel tests). Consolida l'invariant
anti-enumeration sparsi tra S2.1 (login), S2.2 (signup) aggiungendo
il pin per forgot-password (customer + admin) e resend-verification
che erano già implementati pre-Track S ma senza sentinel test.

**Coverage matrix anti-enumeration**:

| Endpoint | Anti-enum mechanism | Sentinel pin |
|---|---|---|
| `/api/customer-auth/login` | Uniform 401, bcrypt dummy timing | S2.1 ✅ |
| `/api/auth/login` | Uniform 401, bcrypt dummy timing | S2.1 ✅ |
| `/api/customer-auth/signup` | Pre-check + uniform 202 on duplicate | S2.2 ✅ |
| `/api/customer-auth/forgot-password` | Same body found vs not-found | **S5.1 NEW** |
| `/api/auth/forgot-password` | `_GENERIC` constant on all paths | **S5.1 NEW** |
| `/api/customer-auth/resend-verification` | Same body, per-email rate limit | **S5.1 NEW** |
| `/api/auth/resend-verification` | Same body, per-email rate limit | **S5.1 NEW** |
| `/api/customer-auth/verify-email` | Token-gated (no email enum vector) | N/A |
| `/api/customer-auth/reset-password` | Token-gated (no email enum vector) | N/A |

**Pin**: `TestSEC_S5_1_AntiEnumerationConsolidation` (6 test):
- Customer forgot-password service: same dict for found vs not-found
- Generic message contains canonical italian string
- Admin forgot-password uses `_GENERIC` constant ≥4 times
- Anti-pattern: no `raise HTTPException(404)` in forgot-password
- Customer resend-verification: source-check, no distinct status leak
- Meta: SECURITY_HARDENING.md documenta tutti gli endpoint anti-enum

**Trade-off accettato**: il sentinel verify-email + reset-password
**non** è incluso perché token-gated by design (attacker non ha vector
per email enumeration su questi endpoint).

---

## 28. Functional rate limit test (Track S Step 5.2)

Pre-S5.2 i sentinel anti-rate-limit verificavano che `check_email_rate`
era **invocato** (source inspection) ma non che **effettivamente bloccasse**
dopo N+1 chiamate. S5.2 aggiunge functional test sul helper reale.

**Coverage (8 sentinel)**:
| Test | Verifies |
|---|---|
| `test_check_email_rate_allows_up_to_max` | Primi N call return True |
| `test_check_email_rate_blocks_at_cap_plus_one` | Call N+1 return False |
| `test_check_email_rate_isolation_per_email` | Buckets indipendenti per email |
| `test_check_email_rate_isolation_per_action` | Buckets indipendenti per action key |
| `test_check_email_rate_case_insensitive_email` | `User@X.it` = `user@x.it` (anti-bypass) |
| `test_check_email_rate_permissive_on_empty_email` | Empty → True (no shared giant bucket) |
| `test_check_email_rate_strip_whitespace` | `  u@x.it  ` = `u@x.it` (anti-bypass) |
| `test_reset_email_rate_state_clears_buckets` | Test infrastructure works |

**Pin**: `TestSEC_S5_2_FunctionalRateLimit` (8 test). Setup/teardown
chiamano `reset_email_rate_state()` per garantire isolation cross-test
(no pollution).

---

## Sub-Track S5 status — COMPLETE (7/7)

| Step | Cosa | Commit | Sentinel |
|---|---|---|---|
| S5.1 | Anti-enumeration consolidation | `973972b` | 6 |
| S5.2 | Functional rate limit test (real 429) | `1ad82a3` | 8 |
| S5.3 | Idempotency race functional test | `ba4fa87` | 4 |
| S5.4 + S5.5 | Model-load + docs-exposure ratify | `81eb3bc` | 6 |
| S5.6 | E2E embed customer flow | `156a35d` | 5 (vitest) |
| S5.7 | README + cumulative regression sanity | _(this commit)_ | 5 |

**Sub-Track S5 sentinel totali: 34** (29 backend + 5 vitest E2E)

**Cumulative full regression** (run 2026-05-29):
- Backend pytest: 3184 passed (1 legacy test aggiornato S3.5 + nuovi S5.x)
- Embed-SDK vitest: 133 passed (cross-component E2E in S5.6)
- Packages vitest: 51 passed
- **Total: 3368 test green**

---

## Sub-Track S6 status — COMPLETE (3/3)

| Step | Cosa | Sentinel |
|---|---|---|
| S6.1 | `SECURITY.md` GitHub-recognized policy | 6 |
| S6.2 | `docs/operations/TESTING.md` runbook | 4 |
| S6.3 | `docs/operations/secrets-rotation.md` extended con Track S Step 1.2 pending | 4 |

**Sub-Track S6 sentinel totali: 14**

---

## Track S — FINAL STATUS (23/24 step, 96%)

| Sub-Track | Status | Sentinel | Commit count |
|---|---|---|---|
| **S1** Config & secret hardening | ✅ 3/4 + 1 deferred (S1.2 rotation utente) | 14 | 3 |
| **S2** Auth surface hardening | ✅ **5/5 COMPLETE** | 35 | 5 |
| **S3** Embed surface hardening | ✅ **5/5 COMPLETE** | 33 | 5 |
| **S4** Operational security & CI | ✅ **4/4 COMPLETE** | 29 | 4 |
| **S5** Regression & sentinel tests | ✅ **7/7 COMPLETE** | 34 (29 + 5 vitest E2E) | 6 |
| **S6** Documentation & runbook | ✅ **3/3 COMPLETE** | 14 | 1 (this) |

**Track S grand total**:
- Backend sentinel cumulati: **524 (era 370 baseline + 154 nuovi Track S)**
- Embed-SDK sentinel: **133 (era 128 + 5 E2E)**
- 9 bug critici di sicurezza chiusi
- 2 GitHub Actions workflow operativi (test + security)
- 4 round CI debug (commit 57ed0f9 → a57c970 → 90d5160 → 89eb4cf) tutti GREEN
- 3 file documentazione nuovi (SECURITY.md, TESTING.md, secrets-rotation extended)

**Solo S1.2 (rotation chiavi storiche) richiede azione utente** — procedura
documentata in `docs/operations/secrets-rotation.md` sezione "Track S Step 1.2 — Pending rotation".

---

## 30. Track L — Launch Readiness (P0 pre-pilot)

Audit post-Track S ha identificato 3 P0 gap restanti per pilot launch:

| Step | Cosa | File | Status |
|---|---|---|---|
| L.1 | GDPR right-to-erasure endpoint | `routers/customer_portal.py::request_account_erasure` | ✅ COMPLETE |
| L.2 | Incident response plan | `docs/operations/incident-response.md` + `incidents.md` | ✅ COMPLETE |
| L.3 | Email reputation DNS guide | `docs/operations/email-reputation.md` | ✅ COMPLETE (doc; **DNS setup richiede user action**) |

**Track L sentinel totali: 20** (8 + 6 + 6)

### L.1 — GDPR right-to-erasure

`POST /api/customer/me/request-erasure` (auth: customer JWT):
- Required body: `confirm=true` (anti-accidental-click) + optional `reason`
- Marks `erasure_requested_at` + `erasure_request_id` su CustomerAccount
- Audit log permanente `gdpr_erasure_requested` (PII redacted)
- Admin notification via Brevo (best-effort)
- Idempotent: duplicate request ritorna stato pending
- Response 202 con SLA 30 giorni (GDPR Art. 12)

**V1 = semi-manual**: customer richiede via endpoint, admin processa
entro 30gg con cascade DELETE manuale (cart, orders, consent_audit).
**V2** automatizza con dry-run + 24h grace period.

### L.2 — Incident response

- `incident-response.md` con severity matrix (P0/P1/P2/P3), decision
  tree triage, GDPR 72h breach timeline, post-mortem template
- `incidents.md` placeholder per append-only audit log
- Comunicazione templates (status page + GDPR Garante Italia)
- Mitigation playbook per 5 scenari comuni (webhook flood, account
  compromise, DB compromise, Stripe key leak, CVE Critical)

### L.3 — Email reputation (DNS — USER ACTION required)

`email-reputation.md` documenta setup SPF + DKIM + DMARC su `afianco.app`.
**Effort utente**: ~2 ore one-shot (DNS provider + Brevo dashboard).
Senza: tutte le email transazionali finiscono in spam.

Procedura completa nel doc:
1. SPF record con `include:spf.brevo.com`
2. 3 CNAME DKIM da Brevo dashboard
3. DMARC progressive rollout: `p=none` → `p=quarantine` → `p=reject`

---

## Final security posture

**Cumulative**: Phase 0 baseline + Phase 1 + Track S + Track L =

| Metric | Count |
|---|---|
| Backend sentinel test | **544** (370 baseline + 174 new) |
| Embed-SDK sentinel test | 133 (incl. 5 E2E) |
| Packages sentinel | 51 |
| **TOTAL cross-package** | **3388** |
| GitHub Actions workflow | 2 (test + security) — entrambi green |
| Security doc files | 5 (SECURITY.md, SECURITY_HARDENING.md, TESTING.md, incident-response.md, email-reputation.md, secrets-rotation.md) |
| Bug critici chiusi | 9 |

**User actions completed (2026-05-29)**:
- ✅ JWT_SECRET_KEY rotated (256-bit hex)
- ✅ ANTHROPIC_API_KEY rotated (vecchia revoked in console)
- ✅ GitHub PAT esposto in chat — revoked
- ✅ DNS SPF/DKIM/DMARC su `afianco.ch` — già configurati (verified via dig)

**User actions deferred V2 (non-blocker)**:
- 🟡 Stripe test key rotation — accepted residual risk (basso blast radius, no fondi reali). P0 al passaggio sk_live_*
- 🟡 DMARC `p=none` → `p=quarantine` upgrade (post 1-2w monitoring)
- 🟡 STRIPE_CLIENT_ID rotation (richiede ri-connettere Stripe Connect)

**🎉 FASE SICUREZZA CHIUSA per pilot launch ✅**

---

## 29. Idempotency race condition functional (Track S Step 5.3)

S3.2 ha aggiunto sentinel **source-level** (verify che le helper exist
+ che dispatch invoca claim prima di call_next). S5.3 estende con
**functional test** che simulano la race reale con mock atomic ops.

**Coverage (4 sentinel)**:
| Test | Verifies |
|---|---|
| `test_poll_returns_completed_doc_within_window` | Loser sees winner's response when winner completes |
| `test_poll_returns_none_on_timeout` | Timeout → None → dispatch maps to 409 |
| `test_concurrent_claims_only_one_wins` | 2 claims same digest → exactly 1 True + 1 False |
| `test_claim_degrades_gracefully_when_mongo_unreachable` | Non-Mongo errors → return True (degraded mode > 500) |

**Pin**: `TestSEC_S5_3_IdempotencyRaceFunctional` (4 test). Override
`LOCK_POLL_INTERVAL_SEC` e `LOCK_POLL_TIMEOUT_SEC` con valori molto
brevi (10ms / 100ms) per test veloci.
