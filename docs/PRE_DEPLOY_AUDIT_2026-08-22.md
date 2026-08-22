# Deploy 22 agosto 2026 — cicli AV, VC, DA, FM

Delta da **prod-2026-08-21d**: **24 commit, 26 file, +5.068 righe**.
Contesto: ci sono utenti attivi in produzione, non si sfascia nulla.

## 1. Cosa contiene

Tutto il mondo visual di Aurya Sound, in quattro cicli:
- **AV** — Aurya Mode: la meditazione che si guarda mentre suona; poi il
  prototipo del founder portato integrale su `/sound/visual`;
- **VC** — la scena è dell'AUTORE: si compone in Crea, viaggia nella
  ricetta (`score.visual`), chi ascolta vede quella. Studio a tutto
  schermo, mobile a tendine, marchio di casa, inquadratura salvata;
- **DA** — il ballerino: la scena danza col suono vero (polso, battito
  di modulazione, coreografie per forma, onde propagative);
- **FM** — dodici forme: loto pieno da ogni prospettiva, sfera
  armillare, kundalini, e le cinque mistiche (Flower, Merkaba, Torus,
  Ocean, Portal).

## 2. Il rischio, misurato (non stimato)

| Verifica | Esito |
|---|---|
| Infrastruttura toccata (docker, nginx, .env, requirements) | **NESSUNA** |
| Migrazioni dati | **NESSUNA** — `score.visual` è additivo |
| Ricette esistenti in produzione | **ZERO** (`frequency_tracks` vuota): nessun documento che il validatore nuovo possa toccare |
| Backend modificato | +69 righe **puramente additive** (costanti + `clean_visual`; `clean_score` scrive `visual` solo se presente) |
| `three` (dipendenza nuova) | il Dockerfile usa già `npm ci --legacy-peer-deps`; lock coerente verificato con `--dry-run` |
| Peso per chi NON apre Sound | **zero**: `WebGLRenderer` assente dal main bundle (three solo in chunk lazy) |
| Suite piena | 4.385 verdi; i 5 rossi sono la famiglia flaky del tetto per-email (il 5°, AP5, **verificato verde in isolamento**) |
| rsync `--delete` | 245 cancellazioni, tutte cache/test/residui della potatura R4 (già in produzione, nessun import): **nessun file operativo** |

Stato produzione prima del deploy: 4 container up (mongodb e backend
healthy), disco 44%, load 0.08. Dati: 7 utenti, 5 organizzazioni, 27
ordini storici, nessuna attività negli ultimi 30 giorni.

## 3. Rete di sicurezza

Backup Mongo **prima** di toccare qualsiasi cosa:
`/root/backups/predeploy-2026-08-22.gz` (4,6 MB, esito 0).

## 4. Trappole d'ambiente incontrate

- la directory di deploy è `/opt/margin-sentinel` (nome storico), non
  l'`/opt/aurya` che lo script ha come default: va passato `VPS_DIR`;
- la chiave SSH buona è `~/.ssh/id_ed25519` (non `aurya_deploy`);
- `mongodump` dentro il container mongodb vuole le sue credenziali di
  root (`MONGO_INITDB_ROOT_*`), non la `MONGO_URL` del backend;
- il database si chiama `margin_sentinel`.
