# Informativa sul trattamento dei dati personali (Privacy Policy)

**Versione:** v2.0
**In vigore dal:** 7 luglio 2026
**Lingua di riferimento legale:** italiano

**Titolare del trattamento (Data Controller):**
Davide De Filippis, Lugano, Svizzera
Email: info@aurya.life

---

## 1. Definizioni

Ai fini della presente informativa, e in conformita' al GDPR (art. 4) e alla LPD svizzera (art. 5):

- **Aurya** (o "la Piattaforma"): il marketplace di ritiri olistici e il gestionale per operatori del benessere accessibile all'indirizzo https://aurya.life.
- **Titolare** (o "Noi"): Davide De Filippis, Lugano, Svizzera, titolare della Piattaforma.
- **Operatore** (o "Organizzatore"): il professionista, l'insegnante o la struttura che si registra ad Aurya per pubblicare e vendere ritiri, esperienze, prodotti e corsi tramite la Piattaforma. L'Operatore e' cliente di Aurya e, per i dati dei propri clienti finali, Titolare autonomo del trattamento (vedi art. 2.2).
- **Cliente finale** (o "Partecipante"): la persona fisica che prenota, acquista o partecipa a un ritiro, un'esperienza, un corso o acquista un prodotto offerto da un Operatore tramite la Piattaforma. Il Cliente finale puo' creare un account personale ("**Passaporto Ritiri**") valido presso tutti gli Operatori della Piattaforma, con ordini, biglietti QR e storico delle esperienze.
- **Visitatore**: chiunque navighi le pagine pubbliche della Piattaforma (directory, calendario pubblico, vetrine degli Operatori) senza registrarsi.
- **Utente** (o "Interessato"): la persona fisica i cui dati personali vengono trattati; include Operatori, Clienti finali e Visitatori.
- **Dati personali**: qualunque informazione riguardante una persona fisica identificata o identificabile (art. 4(1) GDPR).
- **Trattamento**: qualsiasi operazione effettuata sui dati personali, automatizzata o meno (art. 4(2) GDPR).
- **Titolare del trattamento (Controller)**: chi determina finalita' e mezzi del trattamento (art. 4(7) GDPR).
- **Responsabile del trattamento (Processor)**: chi tratta i dati per conto del Titolare (art. 4(8) GDPR).
- **Sub-responsabile (Sub-processor)**: il responsabile incaricato dal Responsabile principale (art. 28(2) GDPR).
- **AI / Intelligenza Artificiale**: la funzionalita' di traduzione automatica dei contenuti pubblicati dagli Operatori (schede di ritiri, esperienze, prodotti), basata su modelli linguistici di terze parti (Anthropic) e attivata esclusivamente su richiesta dell'Operatore.

---

## 2. Ruolo del Titolare

Aurya e' un marketplace: mette in relazione Operatori e Clienti finali. Per questo il Titolare opera in DUE ruoli distinti, secondo il tipo di dato e di interessato:

### 2.1 Aurya come Titolare del trattamento (Data Controller)

Per i seguenti trattamenti Aurya e' Titolare:

- Dati di registrazione e gestione dell'account degli Operatori
- Dati di registrazione e gestione dell'account Passaporto Ritiri dei Clienti finali (credenziali, preferenze, storico ordini aggregato cross-operatore)
- Dati di fatturazione degli abbonamenti e delle commissioni di piattaforma dovuti dagli Operatori
- Pubblicazione delle recensioni verificate sulla Piattaforma (moderazione e verifica di autenticita' incluse)
- Log di sicurezza e audit della Piattaforma
- Email transazionali per l'erogazione del servizio Aurya (verifica account, reset password, ricevute)
- Dati di navigazione strettamente tecnici dei Visitatori (vedi art. 15)

### 2.2 Aurya come Responsabile del trattamento (Data Processor)

Per i seguenti trattamenti Aurya agisce come Responsabile ex art. 28 GDPR per conto dell'Operatore (Titolare autonomo):

- Dati dei Clienti finali raccolti tramite prenotazioni, ordini e acquisti sulla vetrina o dal calendario pubblico (nome, email, telefono, partecipanti, note)
- Anagrafica clienti gestita dall'Operatore nel proprio gestionale (Customer Relationship)
- Iscritti alla newsletter dell'Operatore raccolti tramite i form di iscrizione per-operatore
- Promemoria automatici via email per saldi e rate dei piani di pagamento, inviati per conto dell'Operatore

Per i trattamenti in cui Aurya e' Responsabile, l'Operatore e' Titolare verso i propri interessati e ne assume integralmente la responsabilita' di compliance, inclusa la fornitura di una propria informativa privacy ai sensi degli artt. 13-14 GDPR. Aurya mette a disposizione il proprio **Data Processing Agreement (DPA)** standard a richiesta scritta a info@aurya.life.

---

## 3. Tipologie di dati personali raccolti

### 3.1 Dati forniti direttamente dall'Utente

**Dati di account dell'Operatore:**
- Nome e cognome
- Indirizzo email
- Password (conservata esclusivamente in forma di hash crittografico bcrypt a 12 round; il valore in chiaro non viene mai memorizzato ne' trasmesso a sistemi diversi dal modulo di autenticazione)
- Lingua preferita (it / en / de / fr)
- Fuso orario

**Dati della vetrina dell'Operatore (pubblici per scelta dell'Operatore):**
- Denominazione, descrizione dell'attivita', foto, offerta (ritiri, esperienze, prodotti, corsi)
- Localita' dell'attivita', indicata dall'Operatore e geocodificata in coordinate tramite OpenStreetMap/Nominatim (viene trasmessa al servizio di geocoding esclusivamente la stringa di localita', mai dati identificativi — vedi art. 6)

**Dati di account Passaporto Ritiri (Cliente finale):**
- Nome e cognome, indirizzo email, password (hash bcrypt come sopra), lingua preferita
- Storico ordini, biglietti con codice QR, esperienze prenotate

**Dati di prenotazione e ordine (trattati per conto dell'Operatore):**
- Nome, email, telefono di chi prenota
- Dati dei partecipanti indicati alla prenotazione (nome, eventuali requisiti comunicati dal Cliente)
- Dettagli dell'ordine: ritiro/esperienza/prodotto, date, quantita', importi, caparra versata, piano di pagamento (rate e scadenze)
- Eventuale consenso marketing espresso al checkout (separato, opzionale e revocabile)

**Recensioni:**
- Nome del recensore, valutazione e testo della recensione — pubblicati sulla Piattaforma
- Verifica di autenticita' tramite codice OTP inviato all'indirizzo email associato all'ordine: possono recensire solo Clienti che hanno realmente prenotato

**Newsletter:**
- Indirizzo email ed eventuale nome dell'iscritto ai form newsletter dell'Operatore, con registrazione del consenso; disiscrizione self-service tramite link personale (/u/{token}) presente in ogni email

### 3.2 Dati generati automaticamente dalla Piattaforma

- **Metadati di accesso**: data/ora di primo accesso, ultimo accesso, accettazione dei termini di servizio (con versione del documento e lingua accettata)
- **Log di sicurezza**: tentativi di login falliti, lockout, reset password, modifiche di configurazione dell'account, del team o dell'abbonamento
- **Log di audit operativo**: principali azioni effettuate sull'account a fini di tracciabilita' (export dati, disattivazione, riattivazione)
- **Indirizzo IP** e **User-Agent**: registrati al momento dell'accettazione dei termini, a fini di prova legale del consenso (audit immutabile, art. 7 GDPR)
- **Eventi di pagamento**: identificativo della transazione Stripe, importo, esito (non vengono memorizzati dati della carta di pagamento — vedi art. 9)
- **Codici OTP di verifica recensione**: generati, verificati e scaduti automaticamente; non riutilizzabili
- **Statistiche di visibilita' in forma aggregata e anonima**: le visualizzazioni delle pagine pubbliche (profili degli Operatori, pagine dei ritiri, store) sono conteggiate direttamente dalla Piattaforma, senza cookie, senza servizi di terze parti e senza memorizzare l'indirizzo IP; viene utilizzato un identificatore tecnico che cambia ogni giorno e non e' riconducibile alla persona. Questi conteggi servono esclusivamente a fornire agli Operatori statistiche aggregate sulla visibilita' ottenuta tramite la Piattaforma

### 3.3 Geolocalizzazione del Visitatore

La ricerca "vicino a me" puo' utilizzare, previa autorizzazione esplicita concessa dal Visitatore al proprio browser, la posizione del dispositivo. La posizione e' utilizzata esclusivamente per ordinare i risultati di ricerca al momento della richiesta e **non viene mai salvata sui server** di Aurya ne' associata all'identita' del Visitatore.

### 3.4 Dati NON raccolti

Aurya **non raccoglie**, **non richiede** e **non tratta**:

- Dati di geolocalizzazione persistente o tracciamento della posizione (la posizione del Visitatore non viene mai memorizzata — art. 3.3)
- Documenti d'identita' (carte d'identita', passaporti)
- Dati biometrici (impronte, riconoscimento facciale, voce)
- Dati di navigazione su siti terzi (no cookie di tracciamento, no analytics esterne, no pixel pubblicitari)
- **Categorie particolari di dati** ai sensi dell'art. 9 GDPR (origine razziale o etnica, opinioni politiche, convinzioni religiose o filosofiche, appartenenza sindacale, dati genetici, biometrici, sulla salute, sulla vita sessuale o orientamento sessuale)
- **Dati relativi a condanne penali** ai sensi dell'art. 10 GDPR

I ritiri olistici possono toccare temi di benessere personale: l'Operatore e' tenuto a non richiedere ne' registrare nella Piattaforma dati sanitari o altre categorie particolari (es. condizioni mediche dei partecipanti). Eventuali esigenze particolari vanno gestite dall'Operatore fuori Piattaforma, sotto la propria titolarita' e responsabilita'. In caso di caricamento accidentale, Aurya si riserva il diritto di rimuovere tali dati previa comunicazione all'Operatore.

---

## 4. Finalita' e basi giuridiche del trattamento

| # | Finalita' del trattamento | Base giuridica (GDPR art. 6) | Dati trattati | Conservazione |
|---|---|---|---|---|
| 1 | Erogazione del servizio agli Operatori (registrazione, vetrina, calendario, gestionale ordini/clienti) | Esecuzione di un contratto (art. 6.1.b) | Account Operatore, contenuti della vetrina, localita' | Durata account + 30 giorni (vedi art. 8) |
| 2 | Gestione di prenotazioni, ordini, caparre e piani di pagamento per conto dell'Operatore | Esecuzione di un contratto tra Operatore e Cliente finale (art. 6.1.b) — Aurya agisce come Responsabile | Dati di prenotazione, partecipanti, importi, scadenze | Determinata dall'Operatore titolare (default: durata account Operatore + 30 giorni) |
| 3 | Account Passaporto Ritiri (accesso, biglietti QR, storico ordini) | Esecuzione di un contratto (art. 6.1.b) | Account Cliente finale, ordini, biglietti | Durata account + 30 giorni |
| 4 | Gestione pagamenti, abbonamenti e commissioni di piattaforma | Esecuzione di un contratto (art. 6.1.b) + obbligo legale fiscale (art. 6.1.c) | Email, denominazione Operatore, ID Stripe, importi | 10 anni (obbligo conservazione fiscale) |
| 5 | Email transazionali (verifica account, reset password, conferme d'ordine, biglietti, promemoria saldo/rate) | Esecuzione di un contratto (art. 6.1.b) | Email, nome, dettagli ordine | Fino a 12 mesi nel servizio email (Brevo) |
| 6 | Verifica di autenticita' delle recensioni (codice OTP all'email dell'ordine) e loro pubblicazione | Consenso (art. 6.1.a) per la pubblicazione + legittimo interesse (art. 6.1.f) alla genuinita' delle recensioni | Email dell'ordine, OTP, nome, contenuto della recensione | Recensione: finche' pubblicata; OTP: durata di validita' del codice |
| 7 | Newsletter e comunicazioni marketing dell'Operatore | Consenso (art. 6.1.a), specifico, separato e revocabile via link di disiscrizione | Email, nome, consenso con timestamp | Fino a revoca del consenso |
| 8 | Traduzione automatica dei contenuti dell'Operatore (IT/EN/DE/FR) | Esecuzione di un contratto (art. 6.1.b) — attivata su richiesta dell'Operatore | Testi pubblici della vetrina (vedi art. 7) | Solo durante l'elaborazione |
| 9 | Sicurezza, prevenzione frodi e abusi, audit | Legittimo interesse (art. 6.1.f) bilanciato con i diritti dell'interessato | IP, User-Agent, log di audit | 365 giorni (anonimizzati dopo cancellazione account) |
| 10 | Conservazione della prova del consenso (audit immutabile) | Adempimento di un obbligo legale (art. 7 GDPR, dimostrabilita' del consenso) | Versione del documento, lingua, timestamp, IP, User-Agent | 365 giorni |
| 11 | Tutela dei diritti in sede giudiziaria (eventuali contenziosi) | Legittimo interesse (art. 6.1.f) | Tutti i dati pertinenti all'eventuale contenzioso | Per la durata del termine di prescrizione applicabile |

### 4.1 Revoca del consenso

Laddove la base giuridica del trattamento sia il consenso (newsletter, marketing al checkout, pubblicazione della recensione), l'Interessato puo' revocarlo in qualsiasi momento — tramite il link di disiscrizione presente in ogni email (/u/{token}), dalle impostazioni dell'account o scrivendo a info@aurya.life — senza pregiudicare la liceita' dei trattamenti effettuati prima della revoca. La revoca del consenso marketing non incide in alcun modo sulle prenotazioni in corso.

---

## 5. Categorie di interessati

I trattamenti riguardano le seguenti categorie di interessati:

1. **Operatori / Organizzatori**: le persone fisiche che si registrano ad Aurya per pubblicare e vendere la propria offerta (o che agiscono per conto della struttura registrata).
2. **Clienti finali / Partecipanti**: le persone fisiche che prenotano, acquistano o partecipano tramite la Piattaforma, con o senza account Passaporto Ritiri. Per i dati raccolti nell'ambito di prenotazioni e ordini, Aurya e' Responsabile e l'Operatore e' Titolare (art. 2.2 e art. 18).
3. **Iscritti alle newsletter degli Operatori**: persone che si iscrivono tramite i form per-operatore. Aurya e' Responsabile, l'Operatore e' Titolare.
4. **Visitatori** del sito pubblico: trattamento limitato ai dati tecnici essenziali (art. 15) e all'eventuale geolocalizzazione lato browser mai salvata (art. 3.3).

---

## 6. Sub-responsabili del trattamento (Sub-processors)

Per l'erogazione del servizio, Aurya si avvale dei seguenti sub-responsabili. La condivisione dei dati e' limitata a quanto strettamente necessario alla finalita' indicata. Tutti i sub-responsabili sono vincolati da contratto a misure di sicurezza e riservatezza conformi al GDPR e/o agli equivalenti standard locali.

| Sub-responsabile | Servizio fornito | Dati trasmessi | Sede / Trasferimento | Garanzie applicabili |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Hosting infrastruttura (server, database, file system) | Tutti i dati gestiti dalla Piattaforma | Germania (UE) | Sub-processore UE; conforme al GDPR per design |
| **Stripe Payments Europe Ltd.** | Pagamenti delle prenotazioni (Stripe Connect), abbonamenti degli Operatori (Stripe Billing), rimborsi | Email, nome del pagante, importo della transazione, identificativi interni; i dati carta sono raccolti direttamente da Stripe (vedi art. 9) | Irlanda (UE) + USA per processing | SCC + EU-U.S. DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Invio email transazionali (conferme ordine, biglietti, promemoria saldo, OTP recensioni) e newsletter degli Operatori | Indirizzo email destinatario, nome, contenuto dell'email | Francia (UE) | Sub-processore UE; conforme al GDPR — https://www.brevo.com/legal/privacypolicy/ |
| **Anthropic, PBC** | Traduzione automatica dei contenuti pubblici della vetrina, su richiesta dell'Operatore | Esclusivamente i testi pubblici da tradurre (titoli, descrizioni di ritiri/esperienze/prodotti). Mai dati di Clienti finali, ordini o pagamenti. | Stati Uniti d'America | Clausole Contrattuali Tipo UE (SCC) ai sensi della Decisione (UE) 2021/914 e/o EU-U.S. Data Privacy Framework (DPF) — https://www.anthropic.com/legal |
| **OpenStreetMap Foundation (Nominatim)** | Geocodifica della localita' indicata dall'Operatore (conversione in coordinate per la ricerca geografica) | Esclusivamente la stringa di localita' (es. "Ostuni, Puglia"); mai nomi, email o altri dati identificativi | UE/Regno Unito | Servizio pubblico; policy https://osmfoundation.org/wiki/Privacy_Policy |

L'elenco aggiornato dei sub-responsabili e' richiedibile in qualsiasi momento via email a info@aurya.life.

**Modifiche all'elenco**: in caso di sostituzione o aggiunta di un sub-responsabile, Aurya fornira' preavviso di almeno 30 giorni tramite email all'Operatore. L'Operatore avra' la facolta' di opporsi alla modifica ai sensi dell'art. 28(2) GDPR; in tal caso le parti concorderanno una soluzione, fermo restando il diritto di recesso dell'Operatore.

---

## 7. Dettaglio sulla funzionalita' AI (traduzioni automatiche)

L'unica funzionalita' basata su intelligenza artificiale presente nella Piattaforma e' la **traduzione automatica dei contenuti pubblici dell'Operatore** (schede di ritiri, esperienze, prodotti e corsi) nelle lingue supportate (IT/EN/DE/FR).

### 7.1 Come funziona

- La traduzione viene eseguita **esclusivamente su richiesta dell'Operatore**, dal proprio gestionale.
- Al fornitore AI (Anthropic) vengono trasmessi **soltanto i testi pubblici da tradurre**: titoli, descrizioni, programmi. Si tratta di contenuti che l'Operatore ha gia' destinato alla pubblicazione.
- **NON vengono mai trasmessi**: dati di Clienti finali, dati di prenotazione o pagamento, indirizzi email, numeri di telefono, anagrafiche clienti, log, recensioni.
- L'Operatore puo' sempre rivedere e correggere le traduzioni generate prima e dopo la pubblicazione.

### 7.2 Termini di trattamento da parte di Anthropic

Secondo i termini di servizio API di Anthropic, i dati trasmessi tramite API:
- Sono utilizzati esclusivamente per generare la traduzione richiesta
- Non vengono utilizzati per l'addestramento dei modelli AI
- Sono soggetti a conservazione temporanea per finalita' di sicurezza e moderazione (massimo 30 giorni secondo la policy Anthropic attuale)
- Sono coperti da SCC e/o EU-U.S. DPF

Per consultare i termini Anthropic: https://www.anthropic.com/legal/commercial-terms

### 7.3 Decisioni automatizzate (art. 22 GDPR)

La Piattaforma **non effettua alcuna decisione automatizzata** che produca effetti giuridici sugli interessati o incida significativamente sulla loro persona ai sensi dell'art. 22 GDPR. Non vengono effettuate profilazioni, scoring, approvazioni o rifiuti automatizzati. La funzionalita' AI si limita alla traduzione linguistica di contenuti editoriali.

---

## 8. Conservazione dei dati

| Categoria di dati | Periodo di conservazione | Modalita' di cancellazione |
|---|---|---|
| Account dell'Operatore | Per tutta la durata dell'account attivo | Cancellazione manuale + grace period 30 giorni (vedi art. 12) |
| Contenuti della vetrina (ritiri, esperienze, prodotti, corsi, foto, localita') | Per tutta la durata dell'account | Idem |
| Account Passaporto Ritiri del Cliente finale | Per tutta la durata dell'account attivo | Cancellazione su richiesta + grace period 30 giorni |
| Dati di prenotazioni e ordini (trattati per conto dell'Operatore) | Determinati dall'Operatore titolare (default: durata account Operatore + 30 giorni); fermi gli obblighi fiscali dell'Operatore | Conformi alle istruzioni del Titolare |
| Iscritti newsletter | Fino a revoca del consenso (disiscrizione) o cancellazione da parte dell'Operatore | Rimozione immediata dalle liste attive |
| Recensioni pubblicate | Finche' pubblicate sulla Piattaforma; rimozione su richiesta motivata del recensore | Rimozione manuale |
| Codici OTP di verifica recensione | Durata di validita' del codice | Scadenza e invalidazione automatica |
| Log di audit operativi | 365 giorni | Eliminazione automatica tramite TTL del database |
| Log di sicurezza (rate limit, lockout, IP) | 365 giorni | Eliminazione automatica |
| Audit immutabile del consenso (art. 7 GDPR) | 365 giorni dal momento dell'accettazione | Eliminazione automatica |
| Backup dei dati | Massimo 30 giorni a rotazione | Sovrascrittura automatica |
| Dati post-disattivazione dell'account | 30 giorni di grace period (notifica email 7 giorni prima della cancellazione definitiva) | Cancellazione definitiva e irreversibile dopo i 30 giorni — vedi art. 12 |
| Dati di fatturazione (abbonamenti e commissioni) | 10 anni (obbligo conservazione documenti contabili) | Conservazione conforme alla normativa fiscale applicabile |

**Principio di minimizzazione**: i dati sono conservati solo per il tempo strettamente necessario alle finalita' indicate, salvo obblighi di legge piu' restrittivi.

---

## 9. Dati di pagamento

I pagamenti sulla Piattaforma avvengono tramite **Stripe Connect**:

- Il Cliente finale paga online con carta; i fondi vengono accreditati **direttamente sull'account Stripe dell'Operatore**, non su conti di Aurya.
- Aurya trattiene una **commissione di piattaforma** (application fee) esclusivamente sulle prenotazioni provenienti dal calendario pubblico, secondo il piano dell'Operatore (5% piano Gratis, 2% piano Pro — vedi Termini di Servizio art. 7).
- Sono supportati **caparre e piani di pagamento**: acconto alla prenotazione e saldo (o rate) successivi, con promemoria automatici via email inviati per conto dell'Operatore.
- Gli abbonamenti degli Operatori al piano Pro sono gestiti tramite **Stripe Billing**.

I dati della carta di pagamento (numero, scadenza, CVV) **non vengono mai memorizzati** sui server di Aurya, non transitano attraverso la nostra infrastruttura e non sono accessibili all'Operatore. Il processo di pagamento si svolge interamente all'interno dell'ambiente Stripe, certificato PCI-DSS Level 1.

Aurya conserva esclusivamente:
- Gli identificativi Stripe (cliente, pagamento, abbonamento, account connesso dell'Operatore)
- Lo storico degli eventi di pagamento (data, importo, esito, quota caparra/saldo) ricevuti via webhook firmato di Stripe
- L'indirizzo email associato all'ordine e la denominazione dell'Operatore (necessari per ricevute e fatturazione)

---

## 10. Sicurezza dei dati (art. 32 GDPR)

Aurya adotta misure tecniche e organizzative adeguate al rischio:

### 10.1 Misure tecniche

- **Cifratura in transito**: TLS 1.2/1.3 obbligatorio su tutte le connessioni (HTTPS), certificati Let's Encrypt; HTTP Strict Transport Security (HSTS) attivo
- **Cifratura delle password**: bcrypt con 12 round e salt automatico; nessuna password viene mai conservata in chiaro
- **Cifratura at rest**: il database e i backup sono cifrati a livello di volume Hetzner
- **Token di autenticazione**: JWT firmati, con scadenza configurabile e invalidazione automatica al cambio password
- **Rate limiting**: limiti per IP sugli endpoint di autenticazione (5 tentativi / 15 minuti)
- **Account lockout**: blocco temporaneo per tentativi falliti ripetuti (backoff esponenziale)
- **Verifica OTP delle recensioni**: codici monouso a scadenza inviati all'email dell'ordine, per impedire recensioni non genuine
- **Header di sicurezza**: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Validazione delle webhook**: firma HMAC sui webhook in entrata (Stripe, Brevo)
- **Isolamento multi-tenant**: separazione rigorosa dei dati per organizzazione/Operatore su ogni query database; verifica automatica a livello di ORM
- **Mascheramento email nei log**: parziale mascheramento delle email negli output di logging
- **Audit log immutabile**: scritture append-only su collection dedicata
- **Backup automatici**: backup giornalieri cifrati con retention rolling 30 giorni
- **Monitoring**: rilevamento anomalie su pattern di accesso e tentativi di brute-force

### 10.2 Misure organizzative

- **Principio del privilegio minimo**: gli amministratori di sistema accedono ai dati solo per finalita' tecniche di manutenzione, senza autorizzazione a consultare il contenuto dei dati degli Operatori e dei loro clienti
- **Separazione dei ruoli**: gli admin di piattaforma possono gestire account e abbonamenti, ma NON visualizzare le anagrafiche clienti degli Operatori al di fuori di quanto necessario al supporto richiesto
- **Audit periodico**: revisione periodica degli accessi, dei sub-responsabili e delle misure di sicurezza
- **Procedura di gestione data breach**: definita ai sensi degli artt. 33-34 GDPR (vedi art. 14)

### 10.3 Vulnerability disclosure

In caso di scoperta di vulnerabilita' di sicurezza nella Piattaforma, segnalare a `info@aurya.life` con oggetto "Security disclosure". Aurya si impegna a riscontrare entro 5 giorni lavorativi.

---

## 11. Diritti dell'interessato

Ai sensi degli artt. 15-22 GDPR e degli analoghi diritti previsti dalla LPD svizzera, l'Interessato ha diritto di:

### 11.1 Diritto di accesso (art. 15 GDPR)
Ottenere conferma dell'esistenza di dati personali che lo riguardano, riceverne copia, conoscere finalita', categorie di dati, destinatari, periodo di conservazione e provenienza.

### 11.2 Diritto di rettifica (art. 16 GDPR)
Ottenere la correzione di dati inesatti o l'integrazione di dati incompleti.

### 11.3 Diritto alla cancellazione / "diritto all'oblio" (art. 17 GDPR)
Ottenere la cancellazione dei propri dati personali nei casi previsti dall'art. 17 GDPR. La modalita' self-service e' descritta all'art. 12. E' inoltre possibile richiedere la cancellazione immediata scrivendo a info@aurya.life.

### 11.4 Diritto di limitazione (art. 18 GDPR)
Ottenere la sospensione temporanea del trattamento in attesa di verifica di contestazioni o per finalita' di tutela giudiziaria.

### 11.5 Diritto alla portabilita' dei dati (art. 20 GDPR)
Ricevere in formato strutturato, di uso comune e leggibile da dispositivo automatico tutti i dati personali forniti, o richiederne la trasmissione diretta ad altro Titolare ove tecnicamente fattibile. Per gli Operatori la funzionalita' di export e' disponibile direttamente dalle Impostazioni dell'account ("Esporta i tuoi dati") e produce un archivio con i dati dell'attivita' (ordini, clienti, contenuti).

### 11.6 Diritto di opposizione (art. 21 GDPR)
Opporsi in qualsiasi momento al trattamento dei propri dati fondato sul legittimo interesse, anche con riferimento alla profilazione (non applicata da Aurya — vedi art. 7.3).

### 11.7 Diritto di non essere sottoposto a decisioni automatizzate (art. 22 GDPR)
Aurya non effettua decisioni esclusivamente automatizzate che producano effetti giuridici significativi sull'Interessato (vedi art. 7.3).

### 11.8 Diritti specifici previsti dalla LPD svizzera
Per i residenti in Svizzera si applicano in aggiunta i diritti previsti dalla LPD/nDSG, in particolare il diritto di consultazione e di rettifica.

### 11.9 Diritto di reclamo all'autorita' di controllo
L'Interessato ha diritto di proporre reclamo presso:
- **Per i residenti in Svizzera**: Incaricato federale della protezione dei dati e della trasparenza (PFPDT/IFPDT) — https://www.edoeb.admin.ch
- **Per i residenti nell'UE**: l'autorita' garante per la protezione dei dati personali dello Stato membro di residenza, lavoro o presunta violazione. Per l'Italia: Garante per la protezione dei dati personali — https://www.garanteprivacy.it

L'esercizio dei diritti e' gratuito, salvo richieste manifestamente infondate o eccessive (art. 12(5) GDPR) per le quali il Titolare potra' richiedere un contributo spese o rifiutare la richiesta.

**Nota per i Clienti finali**: per i dati trattati da Aurya in qualita' di Responsabile (prenotazioni, ordini, newsletter — art. 2.2), il primo referente per l'esercizio dei diritti e' l'Operatore titolare. Le richieste possono comunque essere inviate a info@aurya.life: Aurya le inoltrera' senza ritardo all'Operatore competente e cooperera' alla loro evasione.

---

## 12. Modalita' di esercizio dei diritti

### 12.1 Disattivazione self-service dell'account

L'Operatore puo' disattivare il proprio account in qualsiasi momento dalle Impostazioni della Piattaforma. La disattivazione comporta:

1. **Immediatamente**:
   - Blocco di accesso all'account e rimozione della vetrina e dell'offerta dalle pagine pubbliche
   - Cancellazione di eventuali abbonamenti attivi presso Stripe
   - Invio di una notifica email
2. **Periodo di grace di 30 giorni**: l'account puo' essere riattivato contattando il supporto. Durante questo periodo i dati sono soft-deleted (non accessibili ma ancora presenti nel database, eccezion fatta per gli abbonamenti che restano cancellati).
3. **23 giorni dopo la disattivazione (7 giorni prima della cancellazione definitiva)**: invio di un'email di promemoria con le istruzioni per esportare i dati (art. 11.5) o riattivare l'account.
4. **30 giorni dopo la disattivazione**: cancellazione definitiva e irreversibile di tutti i dati personali e dell'attivita' dell'Operatore, eseguita automaticamente. I log di audit vengono anonimizzati (rimozione dell'associazione con identificativi personali) ma conservati per il periodo residuo della loro retention al fine di tutela giudiziaria e sicurezza.

Il Cliente finale puo' richiedere la cancellazione del proprio account Passaporto Ritiri scrivendo a info@aurya.life o tramite le funzionalita' self-service disponibili nell'account; si applicano il medesimo grace period di 30 giorni e le medesime garanzie. Restano salvi i dati d'ordine che l'Operatore titolare deve conservare per obblighi fiscali o contabili.

### 12.2 Richieste tramite email

Tutte le altre richieste relative ai propri diritti vanno indirizzate a `info@aurya.life`. Il Titolare risponde entro **30 giorni** dal ricevimento; in caso di richieste particolarmente complesse il termine potra' essere prorogato di ulteriori 60 giorni con preavviso motivato all'Interessato (art. 12(3) GDPR).

Per garantire la sicurezza della richiesta, il Titolare puo' chiedere conferma dell'identita' dell'Interessato (es. verifica tramite email associata all'account o all'ordine).

---

## 13. Trasferimenti internazionali di dati

I dati personali sono prevalentemente conservati ed elaborati nello Spazio Economico Europeo (Germania, Francia, Irlanda) sui server dei sub-responsabili indicati all'art. 6.

I trasferimenti verso Paesi terzi (Stati Uniti) avvengono esclusivamente verso:
- **Anthropic (USA)** — per la traduzione automatica dei contenuti pubblici della vetrina (art. 7)
- **Stripe (USA)** — per parte del processing dei pagamenti

In tutti i casi i trasferimenti sono coperti dalle garanzie indicate all'art. 6:
- **Clausole Contrattuali Tipo UE (Standard Contractual Clauses, SCC)** ai sensi della Decisione di esecuzione (UE) 2021/914 della Commissione
- **EU-U.S. Data Privacy Framework (DPF)** ove i sub-responsabili siano certificati
- Misure tecniche supplementari (cifratura in transito, pseudonimizzazione ove applicabile)

Per ottenere copia delle clausole contrattuali standard o ulteriori informazioni, scrivere a `info@aurya.life`.

---

## 14. Notifica di violazione dei dati (Data Breach)

In caso di violazione dei dati personali ai sensi dell'art. 33 GDPR (Personal Data Breach), il Titolare:

1. **Entro 72 ore** dalla conoscenza della violazione, notifica all'autorita' di controllo competente (Svizzera: PFPDT; UE: Garante per la protezione dei dati del Paese di stabilimento o del Paese dell'Interessato), salvo che la violazione non sia suscettibile di presentare un rischio per i diritti e le liberta' delle persone fisiche.
2. **Senza ingiustificato ritardo**, comunica la violazione direttamente agli Interessati qualora la violazione sia suscettibile di presentare un rischio elevato per i loro diritti e liberta' (art. 34 GDPR).
3. Per i dati trattati in qualita' di Responsabile (art. 2.2), notifica **senza ingiustificato ritardo agli Operatori titolari** le violazioni che li riguardano, ai sensi dell'art. 33(2) GDPR.
4. Documenta internamente ogni violazione, le sue conseguenze e i provvedimenti adottati per porvi rimedio, indipendentemente dall'obbligo di notifica.

La comunicazione all'Interessato include almeno: natura della violazione, dati di contatto del referente privacy, conseguenze probabili, misure adottate o proposte.

---

## 15. Cookie e tecnologie simili

Aurya **non utilizza cookie di profilazione, analytics o marketing**. Non sono utilizzati Google Analytics, Mixpanel, Hotjar, Facebook Pixel o altri servizi di tracciamento di terze parti.

### 15.1 Tecnologie utilizzate (essenziali, esenti da consenso ai sensi dell'art. 122 Codice Privacy IT e Direttiva ePrivacy)

| Tecnologia | Tipo | Scopo | Durata |
|---|---|---|---|
| Token di sessione (localStorage) | Token JWT | Autenticazione dell'Utente loggato (strettamente necessario) | Fino al logout o alla scadenza del token |
| Preferenza lingua (localStorage) | Preferenza UI | Memorizzare la lingua scelta dall'Utente (IT/EN/DE/FR) | Persistente fino a cancellazione manuale |

Tutte queste tecnologie operano esclusivamente lato client (nel browser dell'Utente) e non comportano trasmissione di dati a terzi.

### 15.2 Cookie di terze parti

**Nessun cookie di terze parti** viene impiantato direttamente dalle pagine di Aurya. I sub-responsabili (Stripe, Brevo) possono impostare propri cookie esclusivamente nei rispettivi flussi (es. modulo di checkout Stripe) e secondo le loro proprie informative privacy.

---

## 16. Minori

La registrazione di un account (Operatore o Passaporto Ritiri) e l'effettuazione di prenotazioni e pagamenti sono riservate a **persone maggiorenni** (eta' >= 18 anni). Eventuali minori partecipanti a un ritiro possono essere indicati tra i partecipanti esclusivamente da un adulto (genitore o esercente la responsabilita' genitoriale) che effettua la prenotazione e ne assume la responsabilita'; l'ammissione di minori alle attivita' e' regolata dall'Operatore.

Il Titolare non raccoglie consapevolmente dati personali direttamente da minori. Qualora venga a conoscenza di un account creato da un minore, procedera' alla cancellazione immediata dei dati e al blocco dell'account.

Per qualsiasi segnalazione: info@aurya.life.

---

## 17. Modifiche all'informativa

Il Titolare si riserva il diritto di aggiornare la presente informativa. In caso di **modifiche sostanziali** (ad esempio: introduzione di nuove finalita' di trattamento, nuovi sub-responsabili, cambio di base giuridica), gli Utenti registrati verranno informati con almeno **30 giorni di preavviso** tramite:

1. Email all'indirizzo registrato
2. Avviso visibile nella Piattaforma al login successivo
3. Pubblicazione della nuova versione su https://aurya.life/privacy

Per le modifiche sostanziali, sara' richiesto un nuovo consenso esplicito ove necessario (es. nuove finalita' di marketing). L'audit immutabile del consenso (art. 4, riga 10) traccia la versione di ogni informativa accettata.

Per modifiche meramente formali (correzioni di refusi, aggiornamento dati di contatto, riformulazioni che non alterano la sostanza), il preavviso sara' di 15 giorni.

---

## 18. Disposizioni specifiche per i dati dei Clienti finali degli Operatori

Aurya consente all'Operatore di esporre una vetrina pubblica e un calendario prenotabile per vendere ritiri, esperienze, prodotti e corsi ai propri Clienti finali. Per i dati raccolti dai Clienti finali tramite prenotazioni, ordini e form newsletter:

### 18.1 Ruoli

- **Titolare del trattamento**: l'Operatore, che utilizza Aurya per vendere ai propri clienti
- **Responsabile del trattamento (Processor)**: Aurya

### 18.2 Dati trattati
- Nome, email, telefono del Cliente finale
- Dati dei partecipanti indicati alla prenotazione
- Dati dell'ordine (ritiro/esperienza/prodotto, date, quantita', prezzi, caparra, piano di pagamento)
- Iscrizioni alla newsletter dell'Operatore (email, nome, consenso)
- Eventuali dati dell'account Passaporto Ritiri limitatamente agli ordini presso quell'Operatore

### 18.3 Responsabilita' dell'Operatore

L'Operatore e':
- Titolare del trattamento dei dati dei propri Clienti finali
- Responsabile della propria informativa privacy verso i Clienti finali
- Tenuto a indicare correttamente nella propria vetrina i propri dati di contatto e i diritti dei clienti
- Tenuto a gestire le richieste di esercizio dei diritti (artt. 15-22 GDPR) provenienti dai propri Clienti finali
- Tenuto a utilizzare la newsletter e le funzioni marketing esclusivamente verso contatti che abbiano prestato valido consenso

Per agevolare l'adempimento, Aurya mette a disposizione dell'Operatore un modello di **Data Processing Agreement (DPA)** che disciplina i rapporti tra Titolare (Operatore) e Responsabile (Aurya), conforme all'art. 28 GDPR. Il DPA puo' essere richiesto via email a `info@aurya.life`.

### 18.4 Cooperazione di Aurya

Aurya coopera con l'Operatore per:
- Fornire export dei dati su richiesta
- Cancellare specifici record di Clienti finali su richiesta dell'Operatore
- Gestire le disiscrizioni newsletter in modo automatico (link /u/{token}) senza intervento dell'Operatore
- Notificare all'Operatore eventuali violazioni di dati che lo riguardano

### 18.5 Condizioni dell'Operatore verso il Cliente finale

Le condizioni di vendita e la politica di cancellazione/rimborso sono definite dall'Operatore sulla pagina del ritiro o del prodotto, e si applicano direttamente al rapporto tra Operatore e Cliente finale. Aurya fornisce l'infrastruttura tecnica; il contenuto contrattuale e' di responsabilita' dell'Operatore (vedi Termini di Servizio art. 13).

---

## 19. Protezione dei dati by design e by default (art. 25 GDPR)

Aurya adotta i seguenti principi di protezione dei dati fin dalla progettazione:

- **Minimizzazione**: raccolta dei soli dati strettamente necessari per le finalita' indicate (es. la geolocalizzazione del Visitatore non viene mai salvata; al geocoding viene inviata solo la stringa di localita')
- **Limitazione delle finalita'**: ogni dato e' trattato per le sole finalita' compatibili con quelle dichiarate al momento della raccolta
- **Limitazione della conservazione**: TTL automatici e retention espliciti per ogni categoria
- **Default privacy-friendly**: consenso marketing al checkout non preselezionato; newsletter solo su iscrizione esplicita; recensioni pubblicate solo previa verifica e conferma del recensore
- **Pseudonimizzazione**: ove tecnicamente fattibile, i dati personali sono sostituiti da identificativi opachi (es. UUID) nei log
- **Accountability**: l'audit immutabile del consenso e l'audit log operativo consentono di dimostrare la conformita' del trattamento

---

## 20. Contatti

### 20.1 Titolare del trattamento

**Davide De Filippis**
Lugano, Svizzera
Email: `info@aurya.life`

Il presente recapito email e' anche il canale ufficiale per:
- Esercizio dei diritti di cui all'art. 11
- Richiesta del DPA per gli Operatori (art. 18.3)
- Richiesta di copia delle Clausole Contrattuali Standard (art. 13)
- Segnalazione di vulnerabilita' di sicurezza (art. 10.3)
- Reclami interni prima di rivolgersi all'autorita' di controllo

### 20.2 Responsabile della protezione dei dati (DPO)

Allo stato attuale il Titolare non ha l'obbligo di nominare un Responsabile della protezione dei dati ai sensi dell'art. 37 GDPR (l'attivita' principale non consiste in trattamento su larga scala di categorie particolari di dati ne' in monitoraggio sistematico). Qualora si rendesse necessaria la nomina, la presente informativa sara' aggiornata.

### 20.3 Tempo di risposta

Le richieste vengono evase entro 30 giorni dal ricevimento, prorogabili di 60 giorni in caso di particolare complessita' (art. 12(3) GDPR).
