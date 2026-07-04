# Informativa sul trattamento dei dati personali (Privacy Policy)

**Versione:** v1.0
**In vigore dal:** 16 maggio 2026
**Lingua di riferimento legale:** italiano

**Titolare del trattamento (Data Controller):**
Davide De Filippis, Lugano, Svizzera
Email: davide@afianco.ch

---

## 1. Definizioni

Ai fini della presente informativa, e in conformita' al GDPR (art. 4) e alla LPD svizzera (art. 5):

- **AFianco** (o "la Piattaforma"): il servizio web di Business Intelligence accessibile all'indirizzo https://afianco.app.
- **Utente** (o "Interessato"): la persona fisica i cui dati personali vengono trattati. Include: (a) l'**Amministratore** dell'organizzazione che si registra ad AFianco; (b) i **Membri del team** invitati dall'Amministratore; (c) i **clienti finali** del Modulo Commerce (vedi art. 18); (d) i **contatti commerciali** (clienti, fornitori) inseriti dall'Amministratore nei propri dataset.
- **Organizzazione**: l'entita' giuridica, ditta individuale o professionista per conto della quale l'Utente si registra come account su AFianco.
- **Dati personali**: qualunque informazione riguardante una persona fisica identificata o identificabile (art. 4(1) GDPR).
- **Trattamento**: qualsiasi operazione effettuata sui dati personali, automatizzata o meno (art. 4(2) GDPR).
- **Titolare del trattamento (Controller)**: chi determina finalita' e mezzi del trattamento (art. 4(7) GDPR).
- **Responsabile del trattamento (Processor)**: chi tratta i dati per conto del Titolare (art. 4(8) GDPR).
- **Sub-responsabile (Sub-processor)**: il responsabile incaricato dal Responsabile principale (art. 28(2) GDPR).
- **AI / Intelligenza Artificiale**: le funzionalita' di analisi, chat e report automatici basate su modelli linguistici di terze parti integrati nella Piattaforma.

---

## 2. Ruolo del Titolare

Il Titolare opera in DUE ruoli distinti, secondo il tipo di dato e di interessato:

### 2.1 AFianco come Titolare del trattamento (Data Controller)

Per i seguenti trattamenti AFianco e' Titolare:

- Dati di registrazione e gestione dell'account dell'Amministratore e dei Membri del team
- Dati di fatturazione del servizio AFianco
- Log di sicurezza e audit della Piattaforma
- Email transazionali per l'erogazione del servizio AFianco
- Dati di utilizzo dell'AI per finalita' di miglioramento operativo del servizio

### 2.2 AFianco come Responsabile del trattamento (Data Processor)

Per i seguenti trattamenti AFianco agisce come Responsabile per conto dell'Organizzazione (Titolare):

- Dati finanziari e operativi dell'Organizzazione caricati dall'Utente (vendite, acquisti, spese, costi fissi, anagrafiche clienti/fornitori/prodotti)
- Dati dei clienti finali raccolti tramite il Modulo Commerce (storefront pubblico) — vedi art. 18

Per i trattamenti in cui AFianco e' Responsabile, l'Organizzazione e' Titolare verso i propri interessati e ne assume integralmente la responsabilita' di compliance, inclusa la fornitura di una propria informativa privacy ai sensi degli artt. 13-14 GDPR. AFianco mette a disposizione il proprio **Data Processing Agreement (DPA)** standard a richiesta scritta a davide@afianco.ch.

---

## 3. Tipologie di dati personali raccolti

### 3.1 Dati forniti direttamente dall'Utente

**Dati di account (Amministratore e Membri team):**
- Nome e cognome
- Indirizzo email
- Password (conservata esclusivamente in forma di hash crittografico bcrypt a 12 round; il valore in chiaro non viene mai memorizzato ne' trasmesso a sistemi diversi dal modulo di autenticazione)
- Lingua preferita (it / en / de / fr)
- Fuso orario

**Dati dell'Organizzazione:**
- Denominazione (libera, scelta dall'Amministratore)
- Settore di attivita' (facoltativo)
- Valuta di riferimento

**Dati commerciali/anagrafici inseriti dall'Utente nei propri dataset:**
- Nomi, indirizzi, email, numeri di telefono di clienti, fornitori, prodotti dell'Organizzazione

**Dati finanziari aziendali:**
- Record di vendite, acquisti, spese, costi fissi (importo, data, categoria, descrizione, riferimenti a controparti)
- Caricamento tramite file CSV/XLSX o inserimento manuale

### 3.2 Dati generati automaticamente dalla Piattaforma

- **Metadati di accesso**: data/ora di primo accesso, ultimo accesso, accettazione dei termini di servizio (con versione del documento e lingua accettata)
- **Log di sicurezza**: tentativi di login falliti, lockout, reset password, modifiche di configurazione dell'organizzazione, team o abbonamento
- **Log di audit operativo**: principali azioni effettuate sull'account a fini di tracciabilita' (export dati, disattivazione, riattivazione)
- **Conversazioni con l'assistente AI**: messaggi inviati dall'Utente all'AI e risposte generate (conservazione: 7 giorni — vedi art. 8)
- **Indirizzo IP** e **User-Agent**: registrati al momento dell'accettazione dei termini, a fini di prova legale del consenso (audit immutabile, art. 7 GDPR)
- **Eventi di pagamento**: identificativo della transazione Stripe, importo, esito (non vengono memorizzati dati della carta di pagamento — vedi art. 9)

### 3.3 Dati NON raccolti

AFianco **non raccoglie**, **non richiede** e **non tratta**:

- Fotografie o immagini di profilo
- Dati di geolocalizzazione precisa (GPS, posizione del dispositivo)
- Documenti d'identita' (carte d'identita', passaporti)
- Dati biometrici (impronte, riconoscimento facciale, voce)
- Dati di navigazione su siti terzi (no cookie di tracciamento, no analytics, no pixel pubblicitari)
- **Categorie particolari di dati** ai sensi dell'art. 9 GDPR (origine razziale o etnica, opinioni politiche, convinzioni religiose o filosofiche, appartenenza sindacale, dati genetici, biometrici, sulla salute, sulla vita sessuale o orientamento sessuale)
- **Dati relativi a condanne penali** ai sensi dell'art. 10 GDPR

L'Utente e' tenuto a non caricare nei propri dataset informazioni rientranti nelle categorie particolari sopra elencate. In caso di caricamento accidentale, AFianco si riserva il diritto di rimuoverle previa comunicazione all'Utente.

---

## 4. Finalita' e basi giuridiche del trattamento

| # | Finalita' del trattamento | Base giuridica (GDPR art. 6) | Dati trattati | Conservazione |
|---|---|---|---|---|
| 1 | Erogazione del servizio (registrazione, accesso, dashboard, import e analisi dati, alert) | Esecuzione di un contratto (art. 6.1.b) | Account, organizzazione, dati finanziari caricati | Durata account + 30 giorni (vedi art. 8) |
| 2 | Funzionalita' AI (chat assistente, digest, health score) | Consenso (art. 6.1.a) — attivabile/disattivabile dall'Utente | Riassunti aggregati dei dati dell'Organizzazione (vedi art. 7) | Solo durante l'elaborazione + log 7 giorni |
| 3 | Gestione pagamenti e fatturazione del servizio AFianco | Esecuzione di un contratto (art. 6.1.b) + obbligo legale fiscale (art. 6.1.c) | Email, nome dell'Organizzazione, ID Stripe | 10 anni (obbligo conservazione fiscale) |
| 4 | Email transazionali (verifica account, reset password, invito team, avvisi disattivazione/cancellazione) | Esecuzione di un contratto (art. 6.1.b) | Email, nome | Fino a 12 mesi nel servizio email (Brevo) |
| 5 | Sicurezza, prevenzione abusi, audit | Legittimo interesse (art. 6.1.f) bilanciato con i diritti dell'interessato | IP, User-Agent, log di audit | 365 giorni (anonimizzati dopo cancellazione account) |
| 6 | Conservazione della prova del consenso (audit immutabile) | Adempimento di un obbligo legale (art. 7 GDPR, dimostrabilita' del consenso) | Versione del documento, lingua, timestamp, IP, User-Agent | 365 giorni |
| 7 | Tutela dei diritti in sede giudiziaria (eventuali contenziosi) | Legittimo interesse (art. 6.1.f) | Tutti i dati pertinenti all'eventuale contenzioso | Per la durata del termine di prescrizione applicabile |

### 4.1 Revoca del consenso

Laddove la base giuridica del trattamento sia il consenso (es. funzionalita' AI), l'Utente puo' revocarlo in qualsiasi momento dalle Impostazioni dell'account, senza pregiudicare la liceita' dei trattamenti effettuati prima della revoca. La revoca disattiva immediatamente le funzionalita' AI; il servizio principale di AFianco rimane operativo.

---

## 5. Categorie di interessati

I trattamenti riguardano le seguenti categorie di interessati:

1. **Amministratore dell'Organizzazione**: la persona fisica che si registra ad AFianco e crea l'account.
2. **Membri del team**: utenti invitati dall'Amministratore con ruoli "admin" o "user".
3. **Contatti commerciali dell'Organizzazione**: persone fisiche o giuridiche inserite dall'Amministratore come clienti, fornitori, contatti nei dataset finanziari. AFianco tratta questi dati come Responsabile per conto dell'Organizzazione (art. 2.2).
4. **Clienti finali del Modulo Commerce**: persone fisiche che acquistano tramite lo storefront pubblico esposto dall'Organizzazione. AFianco e' Responsabile, l'Organizzazione e' Titolare (vedi art. 18).

---

## 6. Sub-responsabili del trattamento (Sub-processors)

Per l'erogazione del servizio, AFianco si avvale dei seguenti sub-responsabili. La condivisione dei dati e' limitata a quanto strettamente necessario alla finalita' indicata. Tutti i sub-responsabili sono vincolati da contratto a misure di sicurezza e riservatezza conformi al GDPR e/o agli equivalenti standard locali.

| Sub-responsabile | Servizio fornito | Dati trasmessi | Sede / Trasferimento | Garanzie applicabili |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Hosting infrastruttura (server, database, file system) | Tutti i dati gestiti dalla Piattaforma | Germania (UE) | Sub-processore UE; conforme al GDPR per design |
| **Anthropic, PBC (Claude AI)** | Elaborazione dell'AI (chat, digest, analisi) | Riassunti finanziari aggregati dell'Organizzazione, nomi dei principali fornitori/clienti (top 5-10 per volume nella chat interattiva). Mai record individuali di transazione. | Stati Uniti d'America | Clausole Contrattuali Tipo UE (SCC) ai sensi della Decisione (UE) 2021/914 e/o EU-U.S. Data Privacy Framework (DPF) — per dettagli https://www.anthropic.com/legal |
| **Stripe Payments Europe Ltd.** | Gestione pagamenti, abbonamenti, fatturazione | Email, nome Organizzazione, ID interno, importo della transazione | Irlanda (UE) + USA per processing | SCC + EU-U.S. DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Invio email transazionali | Indirizzo email destinatario, nome utente, contenuto dell'email | Francia (UE) | Sub-processore UE; conforme al GDPR — https://www.brevo.com/legal/privacypolicy/ |

L'elenco aggiornato dei sub-responsabili e' accessibile in qualsiasi momento all'indirizzo https://afianco.app/legal/subprocessors o richiedibile via email a davide@afianco.ch.

**Modifiche all'elenco**: in caso di sostituzione o aggiunta di un sub-responsabile, AFianco fornira' preavviso di almeno 30 giorni tramite email all'Amministratore. L'Organizzazione avra' la facolta' di opporsi alla modifica ai sensi dell'art. 28(2) GDPR; in tal caso le parti concorderanno una soluzione, fermo restando il diritto di recesso dell'Organizzazione.

---

## 7. Dettaglio sui dati trasmessi all'AI (Anthropic)

Le funzionalita' AI sono opzionali. L'Utente puo' utilizzare la Piattaforma senza alcuna interazione con l'AI.

Quando l'Utente attiva e utilizza una funzionalita' AI, AFianco trasmette ad Anthropic dati strettamente funzionali alla risposta. Le modalita' di trasmissione sono diversificate per tipo di funzionalita':

### 7.1 Digest e analisi automatiche
Vengono trasmessi **esclusivamente indicatori aggregati**:
- Totali per periodo (ricavi, spese, acquisti, costi fissi)
- Margini operativi e punteggio di salute finanziaria (KPI numerici)
- Trend percentuali e variazioni YoY
- Conteggio di alert attivi

**NON vengono trasmessi**: nomi di fornitori o clienti, dettagli di singole transazioni, contatti personali, importi individuali per controparte.

### 7.2 Chat interattiva
Quando l'Utente pone una domanda, il modello AI accede tramite strumenti automatizzati (tool-use) a riassunti che possono includere:
- Nomi dei principali fornitori (top 5 per volume di spesa nel periodo)
- Nomi dei principali clienti (top 10 per fatturato nel periodo)
- Categorie aggregate di spesa
- KPI calcolati

**NON vengono trasmessi**: numeri di telefono, indirizzi, email di terzi, dati di pagamento, contenuto di fatture o documenti caricati, log di audit.

### 7.3 Termini di trattamento da parte di Anthropic
Secondo i termini di servizio API di Anthropic, i dati trasmessi tramite API:
- Sono utilizzati esclusivamente per generare la risposta richiesta
- Non vengono utilizzati per l'addestramento dei modelli AI
- Sono soggetti a conservazione temporanea per finalita' di sicurezza e moderazione (massimo 30 giorni secondo la policy Anthropic attuale)
- Sono coperti da SCC e/o EU-U.S. DPF

Per consultare i termini Anthropic: https://www.anthropic.com/legal/commercial-terms

### 7.4 Decisioni automatizzate (art. 22 GDPR)
Le elaborazioni AI di AFianco hanno carattere **puramente informativo e consultivo**. Non producono effetti giuridici sull'Utente ne' incidono significativamente sulla sua persona ai sensi dell'art. 22 GDPR. L'Utente conserva sempre la piena autonomia decisionale; le analisi AI sono strumenti di supporto, non automatismi di approvazione, rifiuto, scoring o profilazione.

---

## 8. Conservazione dei dati

| Categoria di dati | Periodo di conservazione | Modalita' di cancellazione |
|---|---|---|
| Account dell'Amministratore e dei Membri | Per tutta la durata dell'account attivo | Cancellazione manuale + grace period 30 giorni (vedi art. 12) |
| Dati dell'Organizzazione (denominazione, settore, valuta) | Per tutta la durata dell'account | Idem |
| Dati finanziari caricati (vendite, acquisti, spese, costi fissi) | Per tutta la durata dell'account | Idem |
| Anagrafiche clienti/fornitori inserite | Per tutta la durata dell'account | Idem |
| Conversazioni con l'AI | 7 giorni (eliminazione automatica tramite TTL del database) | Eliminazione automatica e definitiva |
| Log di audit operativi | 365 giorni | Eliminazione automatica tramite TTL del database |
| Log di sicurezza (rate limit, lockout, IP) | 365 giorni | Eliminazione automatica |
| Audit immutabile del consenso (art. 7 GDPR) | 365 giorni dal momento dell'accettazione | Eliminazione automatica |
| Backup dei dati | Massimo 30 giorni a rotazione | Sovrascrittura automatica |
| Dati post-disattivazione dell'account | 30 giorni di grace period (notifica email 7 giorni prima della cancellazione definitiva) | Cancellazione definitiva e irreversibile dopo i 30 giorni — vedi art. 12 |
| Dati di fatturazione del servizio AFianco | 10 anni (obbligo conservazione documenti contabili) | Conservazione conforme alla normativa fiscale applicabile |
| Dati dei clienti finali del Commerce (vedi art. 18) | Determinati dall'Organizzazione titolare (default: per tutta la durata dell'account + 30 giorni) | Conformi alle istruzioni del Titolare |

**Principio di minimizzazione**: i dati sono conservati solo per il tempo strettamente necessario alle finalita' indicate, salvo obblighi di legge piu' restrittivi.

---

## 9. Dati di pagamento

I dati della carta di pagamento (numero, scadenza, CVV) **non vengono mai memorizzati** sui server di AFianco ne' transitano attraverso la nostra infrastruttura. Il processo di pagamento si svolge interamente all'interno dell'ambiente Stripe, certificato PCI-DSS Level 1.

AFianco conserva esclusivamente:
- L'identificativo del cliente Stripe (`stripe_customer_id`) e del singolo abbonamento (`stripe_subscription_id`)
- Lo storico degli eventi di pagamento (data, importo, esito) ricevuti via webhook firmato di Stripe
- L'indirizzo email associato e il nome dell'Organizzazione (necessari per la fatturazione)

---

## 10. Sicurezza dei dati (art. 32 GDPR)

AFianco adotta misure tecniche e organizzative adeguate al rischio:

### 10.1 Misure tecniche

- **Cifratura in transito**: TLS 1.2/1.3 obbligatorio su tutte le connessioni (HTTPS), certificati Let's Encrypt; HTTP Strict Transport Security (HSTS) attivo
- **Cifratura delle password**: bcrypt con 12 round e salt automatico; nessuna password viene mai conservata in chiaro
- **Cifratura at rest**: il database e i backup sono cifrati a livello di volume Hetzner
- **Token di autenticazione**: JWT firmati, con scadenza configurabile e invalidazione automatica al cambio password
- **Rate limiting**: limiti per IP sugli endpoint di autenticazione (5 tentativi / 15 minuti)
- **Account lockout**: blocco temporaneo per tentativi falliti ripetuti (backoff esponenziale)
- **Header di sicurezza**: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Validazione delle webhook**: firma HMAC sui webhook in entrata (Stripe, Brevo)
- **Isolamento multi-tenant**: separazione rigorosa dei dati per `organization_id` su ogni query database; verifica automatica a livello di ORM
- **Mascheramento email nei log**: parziale mascheramento delle email negli output di logging
- **Audit log immutabile**: scritture append-only su collection dedicata
- **Backup automatici**: backup giornalieri cifrati con retention rolling 30 giorni
- **Monitoring**: rilevamento anomalie su pattern di accesso e tentativi di brute-force

### 10.2 Misure organizzative

- **Principio del privilegio minimo**: gli amministratori di sistema accedono ai dati solo per finalita' tecniche di manutenzione, senza autorizzazione a consultare il contenuto dei dataset degli Utenti
- **Separazione dei ruoli**: gli admin di piattaforma possono gestire account e abbonamenti, ma NON visualizzare i dati finanziari delle Organizzazioni
- **Audit periodico**: revisione periodica degli accessi, dei sub-responsabili e delle misure di sicurezza
- **Procedura di gestione data breach**: definita ai sensi degli artt. 33-34 GDPR (vedi art. 14)

### 10.3 Vulnerability disclosure

In caso di scoperta di vulnerabilita' di sicurezza nella Piattaforma, segnalare a `davide@afianco.ch` con oggetto "Security disclosure". AFianco si impegna a riscontrare entro 5 giorni lavorativi.

---

## 11. Diritti dell'interessato

Ai sensi degli artt. 15-22 GDPR e degli analoghi diritti previsti dalla LPD svizzera, l'Interessato ha diritto di:

### 11.1 Diritto di accesso (art. 15 GDPR)
Ottenere conferma dell'esistenza di dati personali che lo riguardano, riceverne copia, conoscere finalita', categorie di dati, destinatari, periodo di conservazione e provenienza.

### 11.2 Diritto di rettifica (art. 16 GDPR)
Ottenere la correzione di dati inesatti o l'integrazione di dati incompleti.

### 11.3 Diritto alla cancellazione / "diritto all'oblio" (art. 17 GDPR)
Ottenere la cancellazione dei propri dati personali nei casi previsti dall'art. 17 GDPR. La modalita' self-service e' descritta all'art. 12. E' inoltre possibile richiedere la cancellazione immediata scrivendo a davide@afianco.ch.

### 11.4 Diritto di limitazione (art. 18 GDPR)
Ottenere la sospensione temporanea del trattamento in attesa di verifica di contestazioni o per finalita' di tutela giudiziaria.

### 11.5 Diritto alla portabilita' dei dati (art. 20 GDPR)
Ricevere in formato strutturato, di uso comune e leggibile da dispositivo automatico tutti i dati personali forniti, o richiederne la trasmissione diretta ad altro Titolare ove tecnicamente fattibile. La funzionalita' di export e' disponibile direttamente dalle Impostazioni dell'account ("Esporta i tuoi dati") e produce un archivio ZIP contenente file JSON con i dati dell'Organizzazione.

### 11.6 Diritto di opposizione (art. 21 GDPR)
Opporsi in qualsiasi momento al trattamento dei propri dati fondato sul legittimo interesse, anche con riferimento alla profilazione (non applicata da AFianco — vedi art. 7.4).

### 11.7 Diritto di non essere sottoposto a decisioni automatizzate (art. 22 GDPR)
AFianco non effettua decisioni esclusivamente automatizzate che producano effetti giuridici significativi sull'Interessato (vedi art. 7.4).

### 11.8 Diritti specifici previsti dalla LPD svizzera
Per i residenti in Svizzera si applicano in aggiunta i diritti previsti dalla LPD/nDSG, in particolare il diritto di consultazione e di rettifica.

### 11.9 Diritto di reclamo all'autorita' di controllo
L'Interessato ha diritto di proporre reclamo presso:
- **Per i residenti in Svizzera**: Incaricato federale della protezione dei dati e della trasparenza (PFPDT/IFPDT) — https://www.edoeb.admin.ch
- **Per i residenti nell'UE**: l'autorita' garante per la protezione dei dati personali dello Stato membro di residenza, lavoro o presunta violazione. Per l'Italia: Garante per la protezione dei dati personali — https://www.garanteprivacy.it

L'esercizio dei diritti e' gratuito, salvo richieste manifestamente infondate o eccessive (art. 12(5) GDPR) per le quali il Titolare potra' richiedere un contributo spese o rifiutare la richiesta.

---

## 12. Modalita' di esercizio dei diritti

### 12.1 Disattivazione self-service dell'account

L'Amministratore puo' disattivare l'account in qualsiasi momento dalle Impostazioni della Piattaforma. La disattivazione comporta:

1. **Immediatamente**:
   - Blocco di accesso per l'Amministratore e tutti i Membri del team
   - Cancellazione di eventuali abbonamenti attivi presso Stripe
   - Invio di una notifica email ai membri dell'Organizzazione
2. **Periodo di grace di 30 giorni**: l'account puo' essere riattivato contattando il supporto. Durante questo periodo i dati sono soft-deleted (non accessibili ma ancora presenti nel database, eccezion fatta per gli abbonamenti che restano cancellati).
3. **23 giorni dopo la disattivazione (7 giorni prima della cancellazione definitiva)**: invio di un'email di promemoria all'Amministratore con le istruzioni per esportare i dati (art. 11.5) o riattivare l'account.
4. **30 giorni dopo la disattivazione**: cancellazione definitiva e irreversibile di tutti i dati personali e aziendali dell'Organizzazione, eseguita automaticamente. I log di audit vengono anonimizzati (rimozione dell'associazione con identificativi personali) ma conservati per il periodo residuo della loro retention al fine di tutela giudiziaria e sicurezza.

### 12.2 Richieste tramite email

Tutte le altre richieste relative ai propri diritti vanno indirizzate a `davide@afianco.ch`. Il Titolare risponde entro **30 giorni** dal ricevimento; in caso di richieste particolarmente complesse il termine potra' essere prorogato di ulteriori 60 giorni con preavviso motivato all'Interessato (art. 12(3) GDPR).

Per garantire la sicurezza della richiesta, il Titolare puo' chiedere conferma dell'identita' dell'Interessato (es. verifica tramite email associata all'account).

---

## 13. Trasferimenti internazionali di dati

I dati personali sono prevalentemente conservati ed elaborati nello Spazio Economico Europeo (Germania, Francia, Irlanda) sui server dei sub-responsabili indicati all'art. 6.

I trasferimenti verso Paesi terzi (Stati Uniti) avvengono esclusivamente verso:
- **Anthropic (USA)** — per le funzionalita' AI
- **Stripe (USA)** — per parte del processing dei pagamenti

In tutti i casi i trasferimenti sono coperti dalle garanzie indicate all'art. 6:
- **Clausole Contrattuali Tipo UE (Standard Contractual Clauses, SCC)** ai sensi della Decisione di esecuzione (UE) 2021/914 della Commissione
- **EU-U.S. Data Privacy Framework (DPF)** ove i sub-responsabili siano certificati
- Misure tecniche supplementari (cifratura in transito, pseudonimizzazione ove applicabile)

Per ottenere copia delle clausole contrattuali standard o ulteriori informazioni, scrivere a `davide@afianco.ch`.

---

## 14. Notifica di violazione dei dati (Data Breach)

In caso di violazione dei dati personali ai sensi dell'art. 33 GDPR (Personal Data Breach), il Titolare:

1. **Entro 72 ore** dalla conoscenza della violazione, notifica all'autorita' di controllo competente (Svizzera: PFPDT; UE: Garante per la protezione dei dati del Paese di stabilimento o del Paese dell'Interessato), salvo che la violazione non sia suscettibile di presentare un rischio per i diritti e le liberta' delle persone fisiche.
2. **Senza ingiustificato ritardo**, comunica la violazione direttamente agli Interessati qualora la violazione sia suscettibile di presentare un rischio elevato per i loro diritti e liberta' (art. 34 GDPR).
3. Documenta internamente ogni violazione, le sue conseguenze e i provvedimenti adottati per porvi rimedio, indipendentemente dall'obbligo di notifica.

La comunicazione all'Interessato include almeno: natura della violazione, dati di contatto del responsabile privacy, conseguenze probabili, misure adottate o proposte.

---

## 15. Cookie e tecnologie simili

AFianco **non utilizza cookie di profilazione, analytics o marketing**. Non sono utilizzati Google Analytics, Mixpanel, Hotjar, Sentry, Facebook Pixel o altri servizi di tracciamento di terze parti.

### 15.1 Tecnologie utilizzate (essenziali, esenti da consenso ai sensi dell'art. 122 Codice Privacy IT e Direttiva ePrivacy)

| Tecnologia | Tipo | Scopo | Durata |
|---|---|---|---|
| `localStorage.token` | Token JWT | Autenticazione dell'Utente loggato (strettamente necessario) | Fino al logout o alla scadenza del token |
| `localStorage.i18n_lang` | Preferenza UI | Memorizzare la lingua scelta dall'Utente | Persistente fino a cancellazione manuale |
| `localStorage.cashflow_active_period` | Preferenza UI | Memorizzare il periodo di reportistica attivo | Persistente |

Tutte queste tecnologie operano esclusivamente lato client (nel browser dell'Utente) e non comportano trasmissione di dati a terzi.

### 15.2 Cookie di terze parti

**Nessun cookie di terze parti** viene impiantato direttamente dalle pagine di AFianco. I sub-responsabili (Stripe, Brevo) possono impostare propri cookie esclusivamente nei rispettivi flussi (es. modulo di checkout Stripe in iframe) e secondo le loro proprie informative privacy.

---

## 16. Minori

AFianco e' un servizio rivolto **esclusivamente a professionisti e imprenditori maggiorenni** (eta' >= 18 anni). La Piattaforma non e' progettata per minori ne' diretta a essi.

Il Titolare non raccoglie consapevolmente dati personali di minori. Qualora venga a conoscenza di dati raccolti involontariamente da un minore, procedera' alla loro cancellazione immediata e bloccera' l'eventuale account.

Per qualsiasi segnalazione: davide@afianco.ch.

---

## 17. Modifiche all'informativa

Il Titolare si riserva il diritto di aggiornare la presente informativa. In caso di **modifiche sostanziali** (ad esempio: introduzione di nuove finalita' di trattamento, nuovi sub-responsabili, cambio di base giuridica), gli Utenti verranno informati con almeno **30 giorni di preavviso** tramite:

1. Email all'indirizzo registrato
2. Avviso visibile nella Piattaforma al login successivo
3. Pubblicazione della nuova versione su https://afianco.app/privacy

Per le modifiche sostanziali, sara' richiesto un nuovo consenso esplicito ove necessario (es. funzionalita' AI). L'audit immutabile del consenso (art. 4.6) traccia la versione di ogni informativa accettata.

Per modifiche meramente formali (correzioni di refusi, aggiornamento dati di contatto, riformulazioni che non alterano la sostanza), il preavviso sara' di 15 giorni.

---

## 18. Disposizioni specifiche per il Modulo Commerce (dati dei clienti finali)

Il Modulo Commerce di AFianco consente all'Organizzazione di esporre uno storefront pubblico per vendere prodotti, servizi, biglietti per eventi o effettuare prenotazioni e noleggi ai propri clienti finali. Per i dati raccolti dai clienti finali tramite tale storefront:

### 18.1 Ruoli

- **Titolare del trattamento**: l'Organizzazione (il "Merchant"), che utilizza AFianco per vendere ai propri clienti
- **Responsabile del trattamento (Processor)**: AFianco

### 18.2 Dati trattati
- Nome, email, telefono del cliente finale
- Indirizzo di spedizione / fatturazione
- Dati dell'ordine (prodotti, quantita', prezzi)
- Eventuali dati specifici legati al tipo di prodotto/servizio (es. data della prenotazione, partecipanti all'evento)
- Eventuali dati di account cliente se il cliente si registra (email, password hash, ordini storici)

### 18.3 Responsabilita' del Merchant

L'Organizzazione (Merchant) e':
- Titolare del trattamento dei dati dei propri clienti finali
- Responsabile della propria informativa privacy verso i clienti finali
- Tenuta a indicare correttamente nel proprio sito i propri dati di contatto e i diritti dei clienti
- Tenuta a gestire le richieste di esercizio dei diritti (artt. 15-22) provenienti dai propri clienti finali

Per agevolare l'adempimento, AFianco mette a disposizione del Merchant un modello di **Data Processing Agreement (DPA)** che disciplina i rapporti tra Titolare (Merchant) e Responsabile (AFianco), conforme all'art. 28 GDPR. Il DPA puo' essere richiesto via email a `davide@afianco.ch`.

### 18.4 Cooperazione di AFianco

AFianco coopera con il Merchant per:
- Fornire export dei dati su richiesta
- Cancellare specifici record di clienti finali su richiesta del Merchant
- Notificare al Merchant eventuali violazioni di dati che lo riguardano

### 18.5 Termini e condizioni del Merchant verso il cliente finale

I termini di vendita (resi, garanzie, diritto di recesso, condizioni di consegna) sono configurabili dal Merchant a livello di store o di singolo prodotto, e si applicano direttamente al rapporto tra Merchant e cliente finale. AFianco fornisce il container tecnico; il contenuto contrattuale e' di responsabilita' del Merchant.

---

## 19. Protezione dei dati by design e by default (art. 25 GDPR)

AFianco adotta i seguenti principi di protezione dei dati fin dalla progettazione:

- **Minimizzazione**: raccolta dei soli dati strettamente necessari per le finalita' indicate
- **Limitazione delle finalita'**: ogni dato e' trattato per le sole finalita' compatibili con quelle dichiarate al momento della raccolta
- **Limitazione della conservazione**: TTL automatici e retention espliciti per ogni categoria
- **Default privacy-friendly**: AI disattivata di default su nuovi account; consenso esplicito richiesto per attivazione
- **Pseudonimizzazione**: ove tecnicamente fattibile, i dati personali sono sostituiti da identificativi opachi (es. UUID) nei log
- **Accountability**: l'audit immutabile del consenso e l'audit log operativo consentono di dimostrare la conformita' del trattamento

---

## 20. Contatti

### 20.1 Titolare del trattamento

**Davide De Filippis**
Lugano, Svizzera
Email: `davide@afianco.ch`

Il presente recapito email e' anche il canale ufficiale per:
- Esercizio dei diritti di cui all'art. 11
- Richiesta del DPA per il Modulo Commerce (art. 18.3)
- Richiesta di copia delle Clausole Contrattuali Standard (art. 13)
- Segnalazione di vulnerabilita' di sicurezza (art. 10.3)
- Reclami interni prima di rivolgersi all'autorita' di controllo

### 20.2 Responsabile della protezione dei dati (DPO)

Allo stato attuale il Titolare non ha l'obbligo di nominare un Responsabile della protezione dei dati ai sensi dell'art. 37 GDPR (l'attivita' principale non consiste in trattamento su larga scala di categorie particolari di dati ne' in monitoraggio sistematico). Qualora si rendesse necessaria la nomina, la presente informativa sara' aggiornata.

### 20.3 Tempo di risposta

Le richieste vengono evase entro 30 giorni dal ricevimento, prorogabili di 60 giorni in caso di particolare complessita' (art. 12(3) GDPR).
