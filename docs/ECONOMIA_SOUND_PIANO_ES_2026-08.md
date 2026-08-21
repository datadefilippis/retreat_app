# Ciclo ES — Economia del suono: costi e scala di TUTTA Aurya Sound (21 agosto 2026)

Richiesta del founder: analisi profonda e olistica di costi e
scalabilità dell'intera area Sound, e un piano per minimizzare i costi
e scalare. Completa `SCALABILITA_MEDITAZIONI_2026-08.md` (le
meditazioni) allargando a ogni superficie: biblioteca, suoni, voce,
vetrina, ascolto continuo, infrastruttura, backup.

---

## Parte I — La mappa dei costi, superficie per superficie

### Dove i costi NON crescono (ed è merito dell'architettura)

| superficie | costo server per ascolto | perché |
|---|---|---|
| 36 schede della biblioteca | **zero** | sintesi nel browser |
| meditazioni (le ricette) | **~zero** | 581 byte a documento; il suono lo fa il client |
| ascolto continuo (AT3) | **zero** | render sul dispositivo |
| anello (AT4) | **zero** | idem |

La scelta «si salva la ricetta, non l'audio» è ciò che rende il numero
di meditazioni pubblicate **irrilevante** per il server. Non esiste
crescita esponenziale: mille mix da 30 minuti = ~3 MB in Mongo.

### Dove i costi crescono davvero

**1. La banda delle basi audio** — l'unico flusso pesante.
115 MB per ascolto di una sessione con 2 basi lunghe. Con i 20 TB
inclusi Hetzner il tetto economico è ~170.000 ascolti/mese: lontano,
ma ogni MB risparmiato sposta il giorno del CDN.

**2. La CPU di UN worker Python** — il collo più vicino, misurato:
in produzione il backend gira con **`--workers 1`** (vincolo del job
in lifespan), e nginx fa da **semplice tubo** verso di lui
(`proxy_pass http://backend:8000/uploads/`). Ogni download da 55 MB
occupa l'event loop dello **stesso identico worker che serve tutte le
API**: con 20 ascoltatori simultanei che scaricano basi, ordini e
dashboard rallentano. Il server ha 4 GB di RAM e regge — ma sta
facendo col Python un lavoro per cui nginx è nato.

**3. La RAM del telefono di chi ascolta** — il muro invisibile:
misurato, una base da 30 minuti decodificata occupa **611 MB** (×11
rispetto al file). Due basi lunghe = ~1,2 GB = crash su mobile. Il
costo scala con la **durata** della base, non col bitrate.

**4. Lo storage della voce** — l'unico dato che cresce per operatore:
~1 MB/minuto, oggi 4 MB. A 100 operatori attivi con 30 min di voce
l'uno: 3 GB. Gestibile, ma senza quota è una crescita senza contratto.

**5. Il backup settimanale** — ricarica l'intero volume uploads
(661 MB cifrati oggi) ogni domenica: cresce linearmente con voce e
libreria.

### La radiografia della libreria (misurata)

| fatto | numero |
|---|---|
| basi totali | 61 file, 635 MB |
| bitrate mediano | 146 kbps (sano) |
| **2 file non compressi** (1.411 kbps: «Pioggia leggera», «Drone caldo 110 Hz») | 10 MB per 1 minuto di audio |
| **10 basi oltre i 10 minuti** | **378 MB — il 60% della libreria** |
| ricodifica a 128 kbps AAC | 635 → 443 MB (−30%) |

Le 10 basi lunghe sono al tempo stesso il grosso della banda, del
backup **e** le bombe di RAM sul client. Un solo intervento le
disinnesca su tre fronti.

### La vetrina (già diagnosticata, entra nel piano)

`SORT → COLLSCAN` + `to_list(500)` che tronca in silenzio + proiezione
che trasporta i layers per contarli. Oggi invisibile, a 5.000 tracce no.

### I costi in euro, oggi e domani

| voce | oggi | quando cambia |
|---|---|---|
| VPS Hetzner 4 GB | ~15 €/mese | CPU: mai, se ES1 toglie i file dal Python |
| banda | inclusa (20 TB) | CDN (~0,01 €/GB su Bunny) oltre ~5 TB/mese reali o pubblico extra-UE |
| Storage Box | già pagata (condivisa) | mai per questo |
| Brevo | già pagato | — |

**Il piano serve a tenere questa tabella com'è fino a ~100k
ascolti/mese.**

---

## Parte II — Il piano, in sei onde

### ES1 — nginx serve gli audio (il colpo più grosso, quasi gratis)

Montare il volume `backend_uploads` **in sola lettura dentro nginx** e
servire `location /uploads/` direttamente: `sendfile` del kernel,
Range nativo, header `immutable` — e il worker Python torna a fare
solo API. In più: `limit_req` per IP sugli /uploads (le basi sono
pubbliche per necessità — debito noto — ma un raschiatore non deve
poterci svuotare la banda).

Il Range-shim appena messo nel backend **resta**: serve il dev (dove
nginx non c'è) ed è il fallback.

*Costo: mezza giornata. Tocca compose + nginx.conf → deploy con
restart di nginx (la trappola del bind-mount è nota).*

### ES2 — la dieta della libreria

1. i **2 file non compressi** → AAC 160 kbps (−90% su quei file);
2. le **basi lunghe a 256 kbps** → AAC 128–160 kbps: per un tappeto
   ambient la differenza è inudibile su qualunque impianto domestico,
   e banda e backup si dimezzano su 378 MB;
3. **file nuovi = id nuovi**: gli URL sono cache-ati `immutable` un
   anno — sostituire i byte sotto lo stesso URL darebbe a metà utenti
   la versione vecchia per mesi. Si pubblicano come asset nuovi e si
   ritirano i vecchi, con uno script che aggiorna gli score che li
   citano.

*Costo: una giornata con lo script di import già esistente (ciclo SL).*

### ES3 — il muro RAM di chi ascolta

1. **curatela loop** (la mossa migliore, zero codice): una base
   ambient di 2–4 minuti **in loop** — il motore lo supporta già —
   suona come una da 30 e costa 40–80 MB di RAM invece di 611. Le 10
   basi lunghe si affiancano/sostituiscono con versioni loopabili
   curate (crossfade in coda, come per l'anello);
2. **stima di memoria in Crea**: alla composizione, se la sessione
   supera ~350 MB stimati di buffer, una riga onesta: *«su molti
   telefoni questa sessione non partirà: basi più corte in loop
   suonano uguale e pesano un decimo»*;
3. *(esperimento futuro, non ora)*: riprodurre le basi live via
   `MediaElementSource` (streaming, RAM ~zero). Va provato su iOS
   prima di prometterlo.

### ES4 — la vetrina che scala

Indice `(status, published_at)`; `layers_count` **materializzato alla
pubblicazione** (non contato trasportando l'array); paginazione a
cursore al posto di `to_list(500)` — che oggi tronca in silenzio.
Guardia col query planner: la query deve fare IXSCAN.

*Costo: mezza giornata.*

### ES5 — governance della crescita

- **quota voce per org** (es. 60 minuti inclusi): oggi la crescita
  dell'unico storage per-operatore non ha contratto;
- pulizia spezzoni orfani (registrati e mai usati in nessuno score);
- niente sistemi di metriche nuovi: i log di nginx bastano già a
  leggere la banda quando servirà.

### ES6 — le soglie scritte (quando spendere, deciso ORA a mente fredda)

| segnale | mossa |
|---|---|
| > ~5 TB/mese di banda audio o ascoltatori extra-UE | CDN (Bunny, ~0,01 €/GB) davanti a /uploads |
| CPU del VPS stabilmente > 70% | prima domanda: ES1 è fatto? poi upgrade VPS (+~10 €/mese) |
| volume uploads > 2 GB | backup a blocchi (restic) al posto del tar settimanale |
| Mongo > 1 GB | è ancora lontanissimo: oggi il DB è ~1 MB |

## Ordine proposto

**ES1 → ES4** (i due colli reali, un giorno in tutto) → **ES2 → ES3**
(la dieta e il muro RAM, che sono due facce delle stesse 10 basi) →
**ES5** → ES6 è un documento, ed è già scritto qui.

## Cosa NON fare (e perché)

- **niente CDN oggi**: banda inclusa per ~15× il traffico prevedibile;
  aggiungerebbe un fornitore e un DNS da gestire per zero beneficio;
- **niente transcodifica on-the-fly** sul server: è il contrario di
  ES1 (torna CPU Python per ascolto);
- **niente object storage (S3) per ora**: 635 MB su un disco al 37%
  non lo giustificano; se ne riparla col CDN;
- **niente seconda macchina**: il giorno in cui servisse, prima si
  separa Mongo — ma il DB è a tre ordini di grandezza da quel giorno.


---

## ESEGUITO — ES1 + ES4 (21 agosto, sera)

**ES1** — `docker-compose.prod.yml` monta `backend_uploads` in nginx
(`:ro`); `location /uploads/` è ora `alias` con sendfile, Range nativo,
`immutable`, mappa `types` completa (la voce di Chrome è webm — e
`types` in una location SOSTITUISCE la mappa ereditata) e
`limit_req 30r/m per IP` (burst 20) contro i raschiatori. Il
Range-shim nel backend resta per il dev e come fallback.
*Verificabile solo al deploy: in locale nginx non c'è. Smoke previsto:
`curl -H "Range: bytes=100-199"` su aurya.life → 206 servito da nginx.*

**ES4** — misurato prima/dopo col query planner: `SORT → COLLSCAN`
diventa **`FETCH → IXSCAN`** (indice `es4_catalog`). Alla pubblicazione
si materializzano `layers_count` e `duration_sec` (prima il catalogo
trasportava l'array dei livelli di ogni traccia per contarli);
paginazione a cursore su `published_at` — col cursore **riportato a
datetime**, o il `$lt` fra tipi BSON diversi non troverebbe mai niente
(vetrina vuota a pagina due, senza errori). Frontend: la vetrina
accumula le pagine e mostra «Carica altre meditazioni» solo quando il
cursore esiste. Provato dal vivo: pagina 1 → cursore → pagina 2 con la
traccia più vecchia, payload senza `score`.

**Guardie**: `test_economia_sound.py` (13) — fra cui il PIANO di query
(explain, non la dichiarazione dell'indice) e la paginazione via HTTP
con token firmato col segreto vero (il conftest ne inietta uno finto
per la suite: firmare importando il modulo dava 403).

**Trappola trovata**: `types` dentro una location nginx sostituisce
l'intera mappa ereditata — elencare solo gli audio avrebbe fatto
uscire loghi e copertine come octet-stream.

Restano: ES2 (dieta libreria), ES3 (curatela loop + stima RAM in
Crea), ES5 (quota voce). ES6 è il capitolo delle soglie qui sopra.
