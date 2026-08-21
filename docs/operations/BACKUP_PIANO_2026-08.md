# Backup di Aurya — piano ed esecuzione (21 agosto 2026)

Stato di partenza, verificato sul server: **nessun backup automatico**.
In `/root/backups` c'erano solo i dump manuali fatti prima dei deploy;
i 639 MB di upload (audio, foto profilo, loghi, copertine,
registrazioni vocali) **non erano salvati da nessuna parte**.

## 1. La scoperta che ha cambiato il piano

Stavo per proporre restic + una Storage Box nuova, quando ho trovato
`deploy/backup.sh` **già nel repo**: 21 KB, scritto per AFianco e
finito qui perché Aurya nasce da quel fork. Non era un abbozzo — era
un impianto maturo:

- **Storage Box Hetzner già attiva** (`u578174.your-storagebox.de`);
- **cifratura `age`**: ogni archivio è cifrato PRIMA di partire dal
  server, con la chiave privata custodita offline (1Password + chiavetta).
  Hetzner non vede mai nulla in chiaro;
- **avvisi via Brevo** in caso di fallimento: nessun servizio nuovo,
  riusa il canale email che Aurya già ha;
- **rotazione a 30 giorni** via SFTP, con una nota preziosa: la
  versione precedente usava `find` via SSH e **falliva in silenzio da
  tre settimane**, perché la Storage Box non esegue comandi SSH
  arbitrari.

Non c'era niente da inventare: andava adattato e acceso.

## 2. Cosa ho cambiato

| cosa | perché |
|---|---|
| percorsi `/opt/margin-sentinel` → `/opt/aurya` | 7 occorrenze: il backup della configurazione puntava a un progetto che su questo server non esiste |
| `STORAGE_DIR` → `aurya-backups` | spazio separato da AFianco sulla stessa Storage Box: la rotazione di uno non tocca l'altro |
| chiave SSH **dedicata** (`/root/.ssh/aurya_storagebox`) su ogni comando remoto | senza `-i` userebbe la chiave di default, che su questo server non esiste: il backup sarebbe fallito al primo upload. Ed essendo dedicata, revocarla non tocca il deploy |
| identità e avvisi: AFianco → Aurya | l'email di allarme diceva il nome sbagliato |
| **modalità `--db-only`** | vedi §3 |
| **rete di sicurezza sulla rotazione** | vedi §4 |

## 3. Scalabilità: perché il db ogni notte e gli upload no

Lo script originale ritrasferiva **l'intero volume ogni notte**: 639 MB
di audio già compresso (il gzip non lo stringe), cioè ~19 GB al mese
spediti per copiare file che non erano cambiati. E cresce ogni volta
che un operatore registra la voce.

Ora:
- `--db-only` → **ogni notte**: il database è ~1 MB e cambia in
  continuazione. È lì che stanno utenti, ordini, iscritti;
- `--full` → **una volta a settimana**: gli upload cambiano di rado.

Costo: al massimo si perdono 7 giorni di file caricati, contro un
database sempre fresco. Se un giorno gli upload diventassero critici
quanto il database, la strada giusta è **restic** (deduplica: solo i
blocchi cambiati, ogni notte) — ma comporta una gestione delle chiavi
diversa da `age`, e non si cambia impianto di corsa.

## 4. La rete di sicurezza sulla rotazione

Con gli upload settimanali e la pulizia a 30 giorni si apriva un buco:
se il giro settimanale fallisse per cinque settimane, la rotazione
cancellerebbe **l'ultima copia rimasta**, lasciando il backup
formalmente attivo e di fatto senza upload.

Ora **l'archivio più recente di ogni tipo non si cancella mai**, per
vecchio che sia. Un backup vecchio è un problema; nessun backup è un
disastro.

## 5. ATTIVO dal 21 agosto 2026

Sotto-account `u578174-sub2` (base `/aurya-backups`, SSH sì, scrittura
sì, SMB/WebDAV no, **external reachability NO**: il VPS è anche lui a
Falkenstein e raggiunge la Storage Box dalla rete interna di Hetzner,
quindi la casella resta chiusa a internet).

Primo giro completo eseguito e **verificato sul remoto**:

| file | dimensione |
|---|---|
| `db_20260821_122936.gz.age` | 859 KB |
| `uploads_20260821_122936.tar.gz.age` | **661.418.091 byte** (631 MB) |
| `config_20260821_122936.tar.gz.age` | 21 KB (include la catena dei certificati) |

Cifratura verificata: intestazione `age-encryption.org/v1`, chiave
`age1j9u3de…` — quella con la privata offline del founder. Allarme
verificato con un fallimento finto: email partita a `info@aurya.life`.

Cron attivo (`/etc/cron.d/aurya-backup`): `--db-only` lun-sab 03:15,
`--full` domenica 03:40. Rotazione del log via logrotate (con la
direttiva `su root adm`, senza la quale rifiutava di ruotare).

### Un bug trovato provando la modalità che NON era comoda da provare
Il giro `--db-only` falliva **dopo** aver caricato tutto: con
`UPLOADS_FILE` vuota, la pulizia finale faceva `rm -f` sulla CARTELLA
temporanea invece che su un file; il comando fallisce, `set -e` uccide
lo script, e sarebbe partita un'email di allarme **ogni notte** per un
backup in realtà riuscito. Allarme che nessuno avrebbe più letto dopo
la terza notte — cioè il modo migliore per non accorgersi di un guasto
vero. Ora i nomi vuoti si saltano.

## 6. Quello che resta da fare: la prova di ripristino (serve la tua chiave)

La Storage Box c'è già e risponde. Manca solo autorizzare **questo**
server, che prima non aveva alcuna chiave SSH.

Chiave pubblica generata sul VPS di Aurya (la privata resta lì e non
esce mai):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPvRde4kNZXakNfd5NbGCqdfif1kCC1QedeuxU0M3i9q aurya-backup@ubuntu-4gb-fsn1-1
```

Due strade, uguali nel risultato:

- **console Hetzner** → Storage Box `u578174` → *SSH keys* → incolla la
  riga qui sopra;
- **oppure dal tuo Mac**, se hai la password della Storage Box a
  portata: `ssh-copy-id -p 23 -f -i <file.pub> u578174@u578174.your-storagebox.de`
  (la password la digiti tu: non deve passare da qui).

Facoltativi, consigliati:
- **snapshot della Storage Box** (funzione sua, gratuita): se qualcuno
  entrasse nel server e cancellasse i backup, gli snapshot lato Hetzner
  sopravvivono;
- **Backups del VPS** in console Cloud (+20% del prezzo server):
  immagini dell'intera macchina. Con questo impianto hai i *dati*; con
  gli snapshot hai la *macchina*.

Io posso verificare che i file esistano, siano interi e siano cifrati
con la chiave giusta — e l'ho fatto. **Non posso aprirli**: la chiave
privata è offline, ed è giusto così.

La prova la fai tu, una volta, dal tuo Mac (serve `age`:
`brew install age`):

```bash
# 1. scarica un archivio dalla Storage Box
sftp -P 23 u578174-sub2@u578174.your-storagebox.de
> get db_20260821_122936.gz.age
> quit

# 2. decifra con la chiave privata (da 1Password / chiavetta)
age -d -i ~/percorso/chiave-privata.txt db_20260821_122936.gz.age > db.gz

# 3. il dump deve aprirsi e contenere le collection vere
tar tzf db.gz 2>/dev/null | head || gzip -t db.gz && echo "archivio integro"
```

Se il passo 2 produce un file e il 3 non protesta, il cerchio è chiuso:
i backup si possono davvero ripristinare. **Da rifare due volte
l'anno** — una chiave che non si prova è una chiave che si scopre
persa nel momento peggiore.

## 7. Costo

Zero: Storage Box e Brevo ci sono già. L'unica spesa nuova sarebbe la
Storage Box se un domani servisse più spazio (BX11 = 1 TB; oggi
occupiamo meno dell'1%).
