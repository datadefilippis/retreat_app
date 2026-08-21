# Audit pre-deploy — 21 agosto 2026, terzo giro (AT4 + TS)

Delta da **prod-2026-08-21b**: **3 commit, 15 file, +1.224 righe**.
Dentro: l'anello delle frequenze (AT4), la correzione dell'avviso che
non diceva *che cosa* fosse quel numero di Hz, e il ciclo TS —
consolidamento mobile dell'area Sound.

## 1. Continuità verificata

| cosa | verifica | esito |
|---|---|---|
| backend runtime | **nessun file** fuori da `backend/tests/` | ✔ |
| migrazioni / env nuove | zero | ✔ |
| build come la prod (`CI=false`) | **exit 0** | ✔ |
| suite | 4.200 verdi; i 4+1 rossi noti verdi in isolamento | ✔ |
| `deploy/backup.sh` prima e dopo il rsync | md5 identico (`5eecfceb…`) | ✔ |
| API nuove del client | `wakeLock`, `mediaSession`, `setPointerCapture` tutte dietro feature-detect o opzionali | ✔ |
| disco VPS | 37 % | ✔ |

## 2. Il rischio dichiarato, e perché in pratica è nullo

**TS1a cambia l'audio anche delle tracce già pubblicate**: l'attacco
del livello scende da 12 s a 1,5 s. È stato deciso esplicitamente dal
founder, ma andava misurato: in produzione le tracce pubblicate sono
**0** (verificato su `/api/frequencies/catalog` prima del deploy),
quindi **nessun ascolto esistente cambia**. Il nuovo attacco vale per
tutto ciò che verrà composto da qui in avanti.

## 3. Cosa cambia per chi usa Aurya

- **operatori in «Crea»**: il play suona subito (≈74 % del volume dopo
  1 s, contro l'1,5 % a 2 s di prima), il cursore si trascina col dito,
  una riga dichiara dove sono finite le dissolvenze, e su telefono
  compare l'avviso cuffie che prima mancava proprio lì;
- **chi ascolta una scheda della biblioteca**: da telefono può
  preparare l'anello e bloccare lo schermo; l'avviso ora spiega che il
  numero nominato è il *tono*, non il ritmo;
- **chi apre una meditazione condivisa**: cursore che segue il dito;
  l'anello non la tocca (render integrale, guardia a monte).

Nessun dato, sessione o permesso cambia.

## 4. Sequenza eseguita

1. push `main` → `2a1cbafe`;
2. backup Mongo `/root/backups/predeploy-2026-08-21c.gz` (841 K, con
   `--uri` autenticato: senza credenziali il dump esce di 23 byte
   senza fallire);
3. rsync (995 KB) + verifica `backup.sh` intatto;
4. `up -d --build` + **restart** di nginx (bind-mount) in nohup;
5. smoke sul vivo, incluso il controllo che i chunk nuovi escano
   davvero dal web (i bundle Sound sono lazy: grep su `main.js` dà
   falso negativo);
6. tag `prod-2026-08-21c`.

## 5. Cosa NON serve

Backfill, script di contenuto, copie di upload nel volume, riavvii di
Mongo: il delta è tutto frontend.
