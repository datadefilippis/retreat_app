# Upload e backup — dove stanno le cose, e cosa manca (21 agosto 2026)

Nato da una domanda del founder dopo il deploy: «gli upload in Docker
sono inefficienti? dove li mettiamo?». La risposta breve è che il posto
va bene; il problema è un altro, ed è più serio.

## 1. Docker non è inefficiente (e i numeri lo dicono)

Un volume Docker **è** una cartella sul disco del server —
`/var/lib/docker/volumes/ms-backend-uploads/_data` — letta
direttamente dal filesystem. Nessun overlay, nessuna penalità: stessa
velocità di qualunque altra directory. Il container ci accede come se
fosse `/app/uploads`, che è esattamente ciò che è.

Spazio: **639 MB su 75 GB, con 46 GB liberi (37% usato)**. Non è lo
spazio il problema.

## 2. I due problemi veri

### a) L'invisibilità (fastidiosa)
Il volume sta sotto `/var/lib/docker`, non dentro `/opt/aurya`. Di
conseguenza **il rsync del deploy non lo tocca** — cosa giusta (non
vogliamo che un deploy sovrascriva i file caricati dagli operatori),
ma che sorprende: durante il deploy del 21/8 i 635 MB di audio erano
finiti sull'host senza arrivare al container, e sono serviti
`docker cp` espliciti. Ora è scritto nel promemoria di
`deploy/deploy-prod.sh`.

### b) NON C'È NESSUN BACKUP AUTOMATICO (serio)
Verificato sul server: `crontab -l` contiene solo `aurya-certbot` e
`e2scrub_all`. In `/root/backups` ci sono **solo i dump manuali**
fatti prima dei deploy (12 MB in tutto, l'ultimo del 21/8).

Questo significa che oggi:
- il **database** è salvato solo quando qualcuno fa un deploy;
- gli **upload** — 639 MB fra audio della libreria, foto profilo,
  loghi, copertine articoli, registrazioni vocali degli operatori —
  **non sono salvati da nessuna parte**.

Se il disco del VPS muore adesso, si perdono i dati dall'ultimo deploy
in poi e **tutti i file caricati, per intero**.

## 3. Cosa proporrei, in ordine di urgenza

### P1 — Backup automatico (da fare presto, ~1 ora)
Un cron notturno che:
1. `mongodump --archive --gzip` del database;
2. `tar` incrementale del volume uploads;
3. rotazione (7 giornalieri + 4 settimanali);
4. **copia fuori dal server** — un backup che vive sullo stesso disco
   che dovrebbe proteggere non è un backup. Bastano uno storage a
   oggetti economico o un secondo host.

È l'intervento col rapporto valore/costo più alto di tutta questa
lista, e l'unico che protegge da un guasto vero.

### P2 — Rendere visibili gli upload (facoltativo, ~30 min)
Spostare da volume nominato a bind mount `/opt/aurya-data/uploads`.
**Non cambia le prestazioni**: cambia che un umano lo vede, lo
rsyncca e lo mette nel backup senza conoscere i comandi Docker. Va
fatto con i container fermi (copia di 639 MB, un minuto di
indisponibilità), quindi in una finestra tranquilla e non subito dopo
un deploy.

### P3 — Storage a oggetti (quando l'audio cresce)
S3-compatibile (Hetzner, Scaleway, Cloudflare R2) per i file audio:
sono pubblici comunque, sono il grosso del peso, e servirli da CDN
toglierebbe banda e disco al server. **Non ora**: 639 MB non
giustificano il lavoro (adattatore di storage, migrazione URL,
riscrittura degli `stream_url`). Diventa interessante sopra i ~5 GB o
quando le registrazioni vocali degli operatori si moltiplicano.

## 4. Riassunto in una riga

Il posto degli upload va bene; quello che manca è **una copia di
sicurezza di qualunque cosa**, database compreso.
