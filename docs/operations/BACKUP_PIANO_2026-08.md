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

## 5. Cosa deve fare il founder su Hetzner (un minuto)

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

## 6. Cosa succede appena la chiave è autorizzata

1. primo giro **manuale** `--full`, guardandolo girare;
2. **prova di ripristino vera**: scarico l'archivio, lo decifro con la
   chiave offline, confronto il dump e un campione di file audio con
   gli originali. Un backup non verificato è un'ipotesi, non un backup;
3. cron: `--db-only` ogni notte alle 03:15, `--full` la domenica alle
   03:40;
4. prova dell'**allarme**: un fallimento finto per vedere se l'email
   arriva davvero a `info@aurya.life`.

## 7. Costo

Zero: Storage Box e Brevo ci sono già. L'unica spesa nuova sarebbe la
Storage Box se un domani servisse più spazio (BX11 = 1 TB; oggi
occupiamo meno dell'1%).
