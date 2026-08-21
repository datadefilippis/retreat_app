# Deploy 21 agosto 2026, quarto giro — cicli TS7 + ES

Delta da **prod-2026-08-21c**: **8 commit, 22 file, +1.980 righe**. È
stato il deploy più delicato della giornata: tocca **backend runtime**,
**nginx**, **docker-compose** e porta **una migrazione di dati audio**.

## 1. Cosa conteneva

barra sui suoni e fix del riquadro (TS7) · Range HTTP nel backend ·
ES1 nginx serve gli audio · ES3 lo spezzone · ES4 vetrina indicizzata e
paginata · ES2 basi non compresse · tetto 30:00 con code sfumate ·
dissolvenze 5/10 uniformi.

## 2. Il problema scoperto in audit, e come l'ho aggirato

Gli script di trasformazione audio usano `afconvert`: **in produzione
non c'è né afconvert né ffmpeg**. Non si potevano eseguire là.

Soluzione: **migrare il risultato, non il processo** — gli 8 file erano
già stati prodotti in locale, quindi sono stati caricati nel volume e i
documenti aggiornati (R1). Stessa logica della libreria del 21/8.

## 3. R1 — la migrazione audio, nell'ordine studiato

1. copia di sicurezza degli 8 file da ritirare (`/app/uploads/_pre21d`);
2. **prima** entrano i file nuovi nel volume (nessun istante in cui un
   asset punta al nulla);
3. **poi** i documenti puntano ai nuovi;
4. **infine** i vecchi si ritirano.

Esito: volume audio da **636 MB a 495 MB (−141 MB, −22%)**, 61 file.

## 4. Verifiche sul vivo

| cosa | esito |
|---|---|
| chi serve gli audio | **nginx** (`server: nginx`), non più il worker Python |
| tipo dei file | `audio/mpeg` e `audio/mp4` — non più `text/plain` |
| Range | **206** con `Content-Range` corretto |
| 7 rotte chiave | 200 |
| errori nei log backend | **0** |
| indice `es4_catalog` | creato all'avvio |
| basi oltre 30:00 | **nessuna** |
| basi non compresse | **nessuna** |
| spezzone su una base migrata | 206, **4,4 MB** scaricati, 71 MB di RAM |

## 5. Due inciampi, e cosa ho imparato

- **heredoc via SSH**: la citazione si è rotta e metà comando è stato
  eseguito sul Mac invece che sul server. Nessun danno (docker locale
  non gira), server verificato intatto prima di riprovare. Rimedio
  adottato: scrivere lo script in locale e copiarlo con `scp` — mai
  più heredoc dentro `ssh`.
- **header duplicati**: `expires` e `add_header Cache-Control` emettono
  la stessa intestazione due volte, e `Accept-Ranges` lo manda già
  nginx. Visto nel primo smoke e corretto subito.

## 6. Il volume di nginx voleva la RICREAZIONE

Un mount nuovo non si applica con un `restart`: serve
`up -d --force-recreate`. Nota da tenere accanto alla trappola del
bind-mount della config.

## 7. Rollback, se servisse

tag precedente `prod-2026-08-21c` · dump
`/root/backups/predeploy-2026-08-21d.gz` (844K) · file audio originali
in `/app/uploads/_pre21d` dentro il volume.
