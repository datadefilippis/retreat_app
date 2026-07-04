# Retreat App — Piattaforma italiana dei ritiri olistici

Fork indipendente (hard fork) del codebase AFianco, ripartito con history pulita il 4/7/2026. Il prodotto: calendario pubblico di ritiri prenotabili + gestionale per organizzatori (caparre, rate, partecipanti, comunicazioni). La strategia completa è in `docs/`.

## Documenti guida (in ordine di lettura)
1. `RETREAT_MASTER_PLAN.md` — **il piano esecutivo che si segue**: fasi 0–7 con checkbox e Definition-of-Done. Si lavora SOLO su step del piano, in ordine; le checkbox si spuntano con data solo a DoD verificata.
2. `docs/PIANO_OPERATIVO_RITIRI_2026-07.md` — journey operatore, gap analysis, design del motore caparre/rate.
3. `docs/BUSINESS_CONCEPT_RITIRI_2026-07.md` — visione prodotto, monetizzazione (Free 5% / Pro 29€ + 2%).
4. `docs/ECOSISTEMA_OLISTICO_STRATEGIA_2026-07.md` — analisi di mercato con fonti.
5. `docs/legacy-afianco/` — documenti ereditati da AFianco, sola consultazione.

## Regole non negoziabili
- **Hard fork**: nessun merge da BI_PMI; cherry-pick solo per fix critici, registrati nella tabella in RETREAT_MASTER_PLAN.md.
- **Segreti**: mai in repo, mai riusati da AFianco. La history è stata ripulita apposta — non committare MAI file `.env` (il gitignore li esclude; `.env.example` è l'unica eccezione).
- **Denaro**: importi solo server-side in minor units; ogni flusso di pagamento è idempotente e ha test; niente merge di codice pagamenti senza suite verde.
- **Snapshot, non riferimenti** per policy di cancellazione, piani di pagamento, prezzi, consensi (pattern già presente nel codebase).
- **Lingua di dominio**: *ritiro, partecipante, caparra, saldo, organizzatore* — non evento/ticket-holder/acconto. UI it-first.
- **Kill-list**: i moduli AFianco non pertinenti (AI assistant, cashflow monitor, POS, spedizioni, magazzino, noleggi) restano nascosti via configurazione piani; non riattivarli senza decisione scritta nel master plan.

## Stack (ereditato, invariato)
- Backend: FastAPI (Python 3.11+) + MongoDB 7 — `backend/`
- Frontend: React (CRA) + TS, feature-driven — `frontend/`
- Embed SDK: Lit Web Components — `apps/embed-sdk/`
- Monorepo: pnpm + turborepo · Pagamenti: Stripe Connect Express (application_fee) · Email: Brevo
- Deploy: Docker Compose su VPS singolo — `docker-compose.prod.yml`, `deploy/`

## Convenzioni
- Conventional commits (`feat:`, `fix:`, `chore:`...), branch `feat/s<fase>-<tema>`.
- Il branch `main` non riceve push diretti dopo la Fase 0 — feature branch + merge.

## Comandi dev (verificati 4/7/2026)
- **Invocare SEMPRE `backend/venv/bin/python -m ...`** — gli shebang degli script del venv (pip/pytest diretti) puntano ancora al path BI_PMI: mai usare `venv/bin/pip` o `venv/bin/pytest` direttamente.
- Backend: `cd backend && venv/bin/python -m uvicorn server:app --port 8000` (Mongo locale attivo; `.env` → DB `retreat_dev`).
- Bootstrap dev (seed + org "Masseria Montanari Dev" su retreat_free + verifica kill-list): `cd backend && venv/bin/python scripts/bootstrap_dev_org.py`.
- Test backend: `cd backend && venv/bin/python -m pytest -q --ignore=tests/test_new_features.py` (baseline verde: 3796). `tests/test_new_features.py` è e2e e richiede il server su :8000 con `REACT_APP_BACKEND_URL` impostata.
- Frontend: `cd frontend && pnpm start` (proxy verso :8000).
- Nota ereditata: il warning `bcrypt has no attribute __about__` all'avvio è rumore di passlib, innocuo.

## Contesto business (per capire le priorità)
Primo cliente e location-faro: Masseria Montanari (ritiri olistici in Puglia, progetto di famiglia del founder). Le fasi 0–2 del piano tecnico corrono in parallelo alla validazione commerciale (interviste organizzatori); il motore dei soldi (Fase 2) si costruisce per primo perché è il valore immediato per l'operatore.
