# Registration Fix Plan — Onda 9.Z

**Status**: PLANNING. Implementation requires explicit user approval per phase.
**Owner**: Backend + DB lifecycle owner (Claude + Davide)
**Goal**: chiudere il bug P0 che blocca tutte le registrazioni nuove (sia signup diretto sia invitation), in modo isolato, scalabile e senza impattare altre logiche già funzionanti.

---

## 0. Stato attuale (verificato live)

### Locale
```
3 signup back-to-back: HTTP 500 / 500 / 429
DB:    6 org totali, 1 con public_slug=null esplicito
Index: organizations.public_slug_1  unique=true, sparse=true (NON partial)
```

### Produzione (deduzione da audit + accesso SSH parziale)
- Container `ms-backend` running `gunicorn` da 25h
- MongoDB 7.0 (stessa versione del locale → comportamento sparse identico)
- Stesso codice + stessa schema → con altissima probabilità lo stesso bug è attivo
- L'errore riportato dal tuo invitato è coerente: lui era almeno "il secondo" che ha tentato registrazione dopo un'org pre-esistente con public_slug null

### Root cause (riconfermata)
```
Organization.public_slug: Optional[str] = None
   ↓ Pydantic model_dump()
{... "public_slug": null ...}
   ↓ insert_one
MongoDB sparse index INCLUDE i null espliciti
   ↓ secondo insert con null
E11000 DuplicateKey
   ↓ except Exception
HTTP 500 "Errore durante la registrazione"
```

---

## 1. Principi guida del piano

| Principio | Cosa significa per ogni step |
|---|---|
| **Isolato** | Ogni step è un commit separato, git-revert sicuro, no dipendenze cross-step |
| **Scalabile** | Pattern riutilizzabile per i 7 altri indici sparse+unique latenti del DB |
| **Non-impacting** | Zero modifiche a codice fuori dal pipeline di signup/registration. Tutti gli endpoint esistenti continuano a funzionare invariati |
| **Idempotente** | Migration + backfill possono essere ri-eseguiti senza side effect |
| **Backward-compatible** | Nessuna API breaking, nessun cambio schema osservabile dai client |
| **Reversibile** | Ogni step ha rollback documentato |

---

## 2. Architettura del fix (sintetica)

```
┌─────────────────────────────────────────────┐
│  Step A — Index migration (P0, root cause)  │  ← chirurgico, fix immediato
├─────────────────────────────────────────────┤
│  Step B — Backfill legacy null org docs     │  ← cleanup retroattivo dati esistenti
├─────────────────────────────────────────────┤
│  Step C — Error handling DuplicateKey       │  ← UX: 500 generico → 409 specifico
├─────────────────────────────────────────────┤
│  Step D — Hardening 7 indici latenti        │  ← prevenzione futura, stesso pattern
├─────────────────────────────────────────────┤
│  Step E — Test E2E + smoke verification     │  ← regression-proof
├─────────────────────────────────────────────┤
│  Step F — Rollout staging → prod            │  ← deploy controllato
└─────────────────────────────────────────────┘
```

Step A da solo **chiude il bug**. Step B-F sono hardening sequenziale.

---

## 3. Step A — Index migration (P0 critico)

**Obiettivo**: cambiare l'indice `organizations.public_slug_1` da `sparse` a `partialFilterExpression`, così documenti con `public_slug=null` esplicito vengono esclusi dall'indice (e non causano duplicate).

### 3.1 Backend code change (1 file, ~3 righe)

**File**: `backend/database.py` (~linea 847)

**Prima**:
```python
await organizations_collection.create_index(
    "public_slug", unique=True, sparse=True
)
```

**Dopo**:
```python
await organizations_collection.create_index(
    "public_slug",
    unique=True,
    partialFilterExpression={"public_slug": {"$type": "string"}},
    name="public_slug_1",  # mantieni stesso nome per idempotenza
)
```

`partialFilterExpression` esclude rigorosamente:
- Documenti dove il campo è missing (come sparse)
- Documenti dove il campo è `null` esplicito (cosa che sparse NON fa su MongoDB 7)
- Documenti dove il campo è di tipo non-string (defensive)

Include nell'indice solo doc con `public_slug` come stringa. Comportamento identico a sparse PER lo use case voluto: "garantire unicità degli slug pubblici, ignorare gli unset".

### 3.2 Migration script

**File nuovo**: `backend/scripts/migrate_public_slug_index.py`

**Cosa fa** (read-only check + idempotent migration):
1. Stampa lo stato dell'indice attuale (è sparse? partial? unique?)
2. Se è già `partialFilterExpression`: log "already migrated", exit 0
3. Se è `sparse=True`: drop + create new spec
4. Verifica post-migration: 3 test insert documents (uno con string, uno con null, uno senza) per validare il comportamento atteso, poi cleanup
5. Stampa diff before/after

**Idempotenza**: re-running è safe — la lookup dello state corrente determina cosa fare.

**No data migration**: non tocca documenti, solo l'indice.

### 3.3 Test consolidamento Step A

Su locale:
1. Run `python -m scripts.migrate_public_slug_index`
2. Verifica indice: `db.organizations.getIndexes()` deve mostrare `partialFilterExpression`
3. 5 signup back-to-back via curl → tutti **HTTP 202**
4. Counter org: cresce di +5
5. Counter org con `public_slug=null` esplicito: cresce di +5 (i null vengono persi nell'indice ma scritti nel doc — comportamento atteso e tollerato)

### 3.4 Rollback Step A

```
db.organizations.dropIndex("public_slug_1")
# Then revert database.py and re-run migration to restore sparse
```

`migrate_public_slug_index.py` ha un flag `--rollback` che ricrea l'indice sparse=True. Idempotente.

### 3.5 Effort + risk
- **Effort**: ~15 min (3 righe codice + 80 righe script + test)
- **Risk**: 🟢 BASSO — operazione DB standard, atomica. Drop+create dell'indice avviene in ms.

---

## 4. Step B — Backfill legacy null org docs

**Obiettivo**: pulire i doc esistenti che hanno `public_slug=null` esplicito, sostituendolo con campo missing. Operazione cosmetica (no perdita info perché null = niente slug), ma rende lo stato del DB coerente.

### 4.1 Decisione: serve davvero?

**No, dopo Step A non è strettamente necessario.** L'indice partialFilterExpression esclude i null espliciti da solo. Lo stato "ibrido" (mix di null espliciti e missing) funziona correttamente.

**Ma**: pulire migliora consistenza per query future tipo `find({public_slug: {$exists: false}})` o aggregation pipelines.

### 4.2 Script

**File nuovo**: `backend/scripts/backfill_drop_null_public_slug.py`

**Cosa fa**:
1. Counts doc con `public_slug=null` esplicito (NOT missing)
2. Dry-run di default — mostra cosa farebbe
3. Con `--apply`: `update_many({public_slug: null, public_slug: {$exists: true}}, {$unset: {public_slug: ""}})`
4. Re-counts post-apply

**Sicurezza**: il filtro `$exists: true` evita di matchare doc dove il campo è già missing (nessun side effect).

### 4.3 Test consolidamento Step B

- Pre-apply: count org con null esplicito > 0
- Post-apply: count = 0
- Verifica indice: counts allineati

### 4.4 Rollback
Non strettamente necessario (è solo cleanup). In caso, `update_many` di reset a `null`. Ma non c'è motivo.

### 4.5 Effort + risk
- **Effort**: ~10 min
- **Risk**: 🟢 BASSO — `$unset` su campo null è idempotente

---

## 5. Step C — Error handling per DuplicateKey

**Obiettivo**: il signup non dovrebbe mai più ritornare `500 generico` per un duplicate key. Casi reali di duplicate (email già registrata, slug collision) devono diventare `409 Conflict` con messaggio user-friendly + i18n.

### 5.1 Backend change

**File**: `backend/routers/auth.py` (~linea 80-85)

**Prima**:
```python
except Exception as e:
    logger.error(f"signup failed: {e}")
    raise HTTPException(status_code=500, detail="Errore durante la registrazione...")
```

**Dopo**:
```python
except DuplicateKeyError as e:
    # Identify which field collided from e.details["keyPattern"]
    field = next(iter((e.details or {}).get("keyPattern", {})), None)
    if field == "email":
        raise HTTPException(409, detail={
            "code": "EMAIL_ALREADY_REGISTERED",
            "message": "Email già registrata. Prova a fare login.",
            "field": "email",
        })
    if field == "public_slug":
        # Should never happen post-Step A — log + alert
        logger.error(f"public_slug collision (should be impossible): {e}")
        raise HTTPException(500, ...)
    raise HTTPException(409, detail={
        "code": "REGISTRATION_CONFLICT",
        "message": f"Registrazione bloccata da conflitto sul campo '{field}'.",
    })
except Exception as e:
    logger.error(f"signup failed: {e}", exc_info=True)
    raise HTTPException(500, detail="Errore durante la registrazione...")
```

### 5.2 Frontend change

**File**: `frontend/src/pages/AuthPages.js` `handleSubmit`

Aggiungi gestione 409 con `error.response?.data?.detail?.code`:
- `EMAIL_ALREADY_REGISTERED` → mostra `t('signup.email_already_registered')`
- `REGISTRATION_CONFLICT` → toast generico "Registrazione bloccata, riprova"

### 5.3 i18n keys × 4 locale

Aggiungi a `auth.json` (it/en/de/fr):
- `signup.email_already_registered`
- `signup.registration_conflict`
- `signup.invitation_used`
- `signup.invitation_expired`

### 5.4 Test consolidamento Step C
- Email già esistente → 409 con copy localizzato
- Token già usato → 409 con copy
- 500 generico solo per errori veramente imprevedibili

### 5.5 Rollback
Revert su 1 file backend + 1 frontend. Tutto additivo.

### 5.6 Effort + risk
- **Effort**: ~30 min
- **Risk**: 🟢 BASSO — additivo, no behaviour change su altri endpoint

---

## 6. Step D — Hardening preventivo 7 indici latenti

**Obiettivo**: applicare lo stesso pattern (`partialFilterExpression` invece di `sparse`) ai 7 indici unique+sparse del DB che oggi sono dormienti (0 null) ma potrebbero rompersi se in futuro qualcuno scrivesse `null` esplicito.

### 6.1 Lista indici da migrare

Dall'audit live precedente:

| Collection | Index | Field | Type futuro |
|---|---|---|---|
| `stores` | `slug_1` | `slug` | string |
| `addon_subscriptions` | `stripe_subscription_item_id_1` | `stripe_subscription_item_id` | string |
| `issued_bookings` | `access_token_1` | `access_token` | string |
| `issued_course_accesses` | `access_token_1` | `access_token` | string |
| `issued_tickets` | `access_token_1` | `access_token` | string |
| `issued_downloads` | `access_token_1` | `access_token` | string |
| `issued_reservations` | `access_token_1` | `access_token` | string |

Tutti string, semantica "presente o assente" (mai esplicitamente null).

### 6.2 Backend code change

**File**: `backend/database.py` — 7 modifiche puntuali, stesso pattern di Step A.

### 6.3 Migration script

Estendere `migrate_public_slug_index.py` (o nuovo `migrate_unique_sparse_indices.py`) per migrare tutti e 7. Iterare su una lista di tuple `(collection_name, field_name)`.

### 6.4 Test consolidamento Step D

Per ogni indice:
- Verifica spec post-migration
- Test insert con valore string → OK
- Test insert con missing → OK
- Test insert con null esplicito → OK (incluso nell'indice ma duplicate solo se >1 null, cosa impossibile in pratica)

### 6.5 Rollback
Stesso pattern di Step A — revert codice + rerun migration con `--rollback`.

### 6.6 Effort + risk
- **Effort**: ~25 min
- **Risk**: 🟢 BASSO — preventivo, comportamento osservabile invariato

---

## 7. Step E — Test E2E + smoke verification

**Obiettivo**: garantire che il pipeline signup funzioni end-to-end e non regredisca in futuro.

### 7.1 Script test E2E

**File nuovo**: `backend/scripts/test_signup_flow.py`

**Scenari coperti** (15-20 test cases):
1. Open mode signup × 3 successivi (3 org distinte)
2. Open mode signup con email già esistente → 409
3. Open mode signup con password debole → 400
4. Open mode signup senza terms → 400
5. Open mode signup con email malformata → 422
6. Invite-only mode signup con token valido → 200 con JWT
7. Invite-only mode signup con token mancante → 403
8. Invite-only mode signup con token scaduto → 400
9. Invite-only mode signup con token già usato → 400
10. Invite-only mode signup con email mismatch → 400
11. Validate-invite endpoint con token valido → 200
12. Validate-invite endpoint con token expired → 400
13. Rate limit 5/15min stress test → 429 dopo soglia
14. CORS preflight test
15. Stato DB post-test: counts coerenti

**Modalità**:
- `--integration`: contro backend running su :8000 + Mongo locale
- `--cleanup`: rimuove tutti i test users/orgs creati

### 7.2 CI integration (opzionale, non bloccante)

Aggiungere step in `pre-commit` o pipeline CI per eseguire questi test su PR che toccano `routers/auth.py`, `services/auth_service.py`, `database.py`.

### 7.3 Effort + risk
- **Effort**: ~45 min
- **Risk**: 🟢 BASSO — read-only validation suite

---

## 8. Step F — Rollout strategy

**Obiettivo**: deploy controllato in produzione con verifica post-deploy.

### 8.1 Sequenza deploy

| Stage | Cosa fa Davide | Verifica |
|---|---|---|
| 1. Locale | merge commit Step A → run migration → 3 signup test | tutti 202 |
| 2. Staging (se disponibile) | pull + restart container | 3 signup test |
| 3. Produzione | dump DB precauzionale → pull + restart → run migration | 3 signup test post-deploy |
| 4. Monitoring | tail backend log per 30 min | 0 errori `E11000.*public_slug` |

### 8.2 Pre-deploy backup

```
docker exec ms-mongodb mongodump --db test_database --out /backup/pre_9z
```

Tenuto 7 giorni, idempotente.

### 8.3 Communication

Comunicare al tuo invitato di prod (quello del bug originale) che può ritentare la registrazione dopo il deploy.

### 8.4 Rollback strategy

- Se Step A breaks something: `migrate --rollback` ri-crea sparse=True
- Se Step C breaks frontend: revert frontend commit
- Se Step D breaks una feature non-cashflow: revert solo l'indice problematico

### 8.5 Effort
- **Effort**: ~30 min (incluso monitoring window)
- **Risk**: 🟡 MEDIO — è prod, ma migration testata su locale prima

---

## 9. Stima totali e priorità

| Step | Effort | Severity gestita | Bloccante? |
|---|---|---|---|
| **A — Index migration** | 15 min | **P0** root cause | ✅ Solo questo basta a sbloccare prod |
| B — Backfill | 10 min | P2 cosmetic | No |
| C — Error handling | 30 min | P1 UX | No |
| D — Hardening 7 indici | 25 min | P2 latente | No |
| E — Test E2E | 45 min | regression prevention | No |
| F — Rollout | 30 min | deploy | Sì per prod |

**Totale**: ~2.5 ore split in 6 commit indipendenti.

**Minimo viable per sbloccare prod**: Step A + Step F (~45 min totali, deployable oggi).

---

## 10. Acceptance criteria (fine 9.Z)

1. ✅ Su locale, staging, prod: 5+ signup successivi tutti con HTTP 202/200
2. ✅ DuplicateKey errors → 409 con copy localizzato in 4 locale, mai più 500 generici
3. ✅ Tutti gli 8 indici unique+sparse migrati a `partialFilterExpression`
4. ✅ Backfill idempotente, zero perdita dati
5. ✅ Test E2E coverage di 15+ scenari signup, eseguibili in 1 comando
6. ✅ Audit `db.organizations.find({public_slug:null,public_slug:{$exists:true}})` → 0 doc post-Step B
7. ✅ Tail backend log per 30 min post-deploy → 0 errori signup-related

---

## 11. Cosa NON faccio in questo piano (out of scope)

- Refactor del flusso invitation/signup completo
- Cambiamento della semantica di `public_slug` (resta Optional[str])
- Migrazione a transactions per garantire atomicity org+user (separato follow-up)
- Cambio rate limiter da slowapi in-memory a Redis (separato)
- Localizzazione di TUTTI gli error message backend (separato — solo il subset di signup è in scope)
- Rotazione di JWT_SECRET_KEY o BREVO_API_KEY (out of scope, infra-only)
- Modifica a frontend `PublicRoute` redirect su user authenticated che clicca invito (separato — è UX issue diversa)

Tutti questi sono stati identificati nei 3 audit forensici precedenti come **issue P1/P2 latenti** ma sono **separati dal P0 bloccante** che questo piano risolve.

---

## 12. Approval gate

Prima di iniziare Step A, Davide rivede questo piano e:

- [ ] Conferma che Step A da solo è sufficiente per sbloccare prod, oppure vuole il pacchetto completo A→F
- [ ] Sceglie se eseguire Step B (cleanup retroattivo) o lasciare lo stato ibrido
- [ ] Conferma se vuole anche Step D (hardening 7 indici) ora o rimanda
- [ ] Approva strategia di rollout (Step F): deploy diretto vs staging-first
- [ ] Conferma comunicazione all'invitato del bug originale: messaggio personalizzato vs nessuna notifica

Una volta approvato, inizio da Step A. Implementazione segue rigorosamente i principi §1.

---

## Appendice — Risk matrix

| Step | Probability of regression | Impact | Mitigation |
|---|---|---|---|
| A | <1% | Sblocca tutto | Test 5x signup post-migration |
| B | <0.5% | Cosmetic only | Idempotent script, dry-run default |
| C | 5% (tocca frontend) | Solo error UX | Test su 4 locale |
| D | 2% (7 collection diverse) | Solo indici, no data | Test per ogni collection |
| E | 0% (read-only suite) | None | n/a |
| F | 5% (è prod) | Outage durante deploy | Pre-backup + rollback prepared |

---

## Appendice — File touched estimate

| File | Tipo modifica | Step |
|---|---|---|
| `backend/database.py` | 1 indice cambiato (A) + 7 indici cambiati (D) | A, D |
| `backend/routers/auth.py` | exception handling esteso | C |
| `backend/scripts/migrate_public_slug_index.py` | NEW | A |
| `backend/scripts/backfill_drop_null_public_slug.py` | NEW | B |
| `backend/scripts/migrate_unique_sparse_indices.py` | NEW | D |
| `backend/scripts/test_signup_flow.py` | NEW | E |
| `frontend/src/pages/AuthPages.js` | catch handler 409 | C |
| `frontend/src/locales/{it,en,de,fr}/auth.json` | +4 chiavi × 4 locale = 16 stringhe | C |

**Totale**: 4 file modificati additivi + 4 file nuovi. Zero deletion. Zero breaking change.

---

**END OF PLAN.**
