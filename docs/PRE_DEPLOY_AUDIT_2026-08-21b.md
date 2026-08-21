# Audit pre-deploy — 21 agosto 2026, secondo giro (delta AT)

Delta da **prod-2026-08-21** (stamattina): **6 commit, 18 file,
+1.375 righe**. Dentro: il ciclo AT (ascolto dal telefono), il fix
della mappa categorie, la testata multipiattaforma, e l'impianto di
backup (già attivo sul server, qui entra solo nel repo).

Il contrasto col giro precedente è tutto: quello erano 81 commit su
100 file con due azioni obbligatorie di migrazione dati. Questo è
**additivo e confinato al frontend**.

## 1. Continuità verificata

| cosa | verifica | esito |
|---|---|---|
| backend runtime | **nessun file** in `backend/` fuori da `tests/` | ✔ |
| migrazioni dati | zero (nessun campo nuovo, nessun significato cambiato) | ✔ |
| env nuove | nessuna | ✔ |
| build come la prod (`CI=false`, come forza il Dockerfile) | **exit 0**, nessun file del delta tra i warning | ✔ |
| suite | 4.171 verdi; i 5 rossi noti verdi in isolamento | ✔ |
| `deploy/backup.sh` locale vs server | **md5 identico** (`5eecfceb…`) → il rsync non tocca il giro notturno | ✔ |
| API nuove usate dal client | `wakeLock`, `mediaSession`, `MediaMetadata` tutte dietro feature-detect; il render è in try/catch | ✔ |
| cancello dei 90 secondi | l'ascolto continuo è offerto **solo** a sblocco avvenuto (guardia) | ✔ |
| pagine toccate | solo il mondo Sound (`features/frequenze/*`) | ✔ |
| disco VPS | 37% usato, 46G liberi | ✔ |

## 2. Cosa cambia per chi già usa Aurya

- **Operatori**: nella biblioteca, sulle schede che suonano sotto i
  500 Hz e **solo da telefono**, compare una riga che spiega perché
  non si sente nulla senza cuffie. Sul desktop non cambia niente.
- **Chi riceve un link a una sessione**: stessa pagina, più un
  pulsante (solo telefono, solo a sblocco fatto) per preparare
  l'ascolto che sopravvive al blocco schermo.
- **Chiunque apra `/sound`**: «Ritmi del corpo» ora si apre davvero e
  ha la sua descrizione (prima era un riquadro muto al clic).

Nessuno di questi cambia dati, sessioni o permessi.

## 3. Rischi, con la loro misura

1. **Il render occupa memoria sul telefono**: ~158 MB nel caso
   peggiore (30 minuti). Mitigato dal tetto: oltre, il pulsante non
   compare. Il fallimento è gestito (try/catch) e lascia l'ascolto dal
   vivo intatto.
2. **Il Wake Lock consuma batteria** mentre si ascolta dal vivo: è il
   suo scopo, e si rilascia appena il suono finisce.
3. **`--delete` nel rsync**: è la prassi già usata il 21/8 e le
   esclusioni coprono `.env*`, `backups`, `node_modules`, i volumi.
   Verificato dopo il sync che `backup.sh` è rimasto identico.

## 4. Sequenza eseguita

1. push `main` (6 commit) → `origin/main` = `bfa63f66`;
2. backup Mongo pre-deploy: `/root/backups/predeploy-2026-08-21b.gz`
   (840K, dump completo — la prima prova senza credenziali aveva
   prodotto un file di 23 byte: mongodump vuole `--uri` con auth);
3. rsync (1,06 MB trasferiti) + verifica `backup.sh` intatto;
4. `compose up -d --build` + **restart di nginx** (bind-mount: il
   reload rilegge l'inode vecchio) in nohup server-side;
5. smoke sul vivo;
6. tag `prod-2026-08-21b`.

## 5. Cosa NON serve

Backfill, script di contenuto (nessuno nel delta), copie di upload nel
volume (nessun file nuovo), riavvii di Mongo.
