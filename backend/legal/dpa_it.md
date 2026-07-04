# Accordo di Trattamento Dati (DPA)
## tra **{{merchant_name}}** ("Titolare del trattamento") e **{{platform_controller_name}}** ("Responsabile del trattamento")

**Versione:** v1.0
**Data di efficacia:** {{date}}
**Riferimento organizzazione (afianco):** {{org_id}}

---

## 1. Oggetto e finalità

Il presente Accordo di Trattamento Dati ("**DPA**") disciplina il trattamento di dati personali effettuato da **afianco**, piattaforma SaaS fornita da {{platform_controller_name}} ({{platform_controller_country}}), per conto del Titolare del trattamento **{{merchant_name}}**, ai sensi dell'art. 28 del Regolamento (UE) 2016/679 ("**GDPR**").

Il DPA è parte integrante dei Termini di Servizio di afianco accettati dal Titolare al momento della registrazione.

---

## 2. Definizioni

- **"Dati Personali"**: qualsiasi informazione relativa a una persona fisica identificata o identificabile, ai sensi dell'art. 4(1) GDPR.
- **"Trattamento"**: qualsiasi operazione applicata ai Dati Personali, ai sensi dell'art. 4(2) GDPR.
- **"Interessato"**: la persona fisica i cui Dati Personali sono trattati (utenti, clienti finali del Titolare).
- **"Titolare"**: il Titolare del trattamento di cui sopra, **{{merchant_name}}**.
- **"Responsabile"**: il Responsabile del trattamento di cui sopra, {{platform_controller_name}}.
- **"Sub-responsabile"**: un terzo a cui il Responsabile affida specifiche attività di trattamento (vedi sez. 7).

---

## 3. Ruolo delle parti

- Il **Titolare** determina le finalità e i mezzi del trattamento dei Dati Personali dei propri clienti finali raccolti tramite la piattaforma afianco.
- Il **Responsabile** tratta i Dati Personali esclusivamente per conto del Titolare e secondo le istruzioni documentate, salvo diversi obblighi di legge.

afianco **non** ha alcun rapporto contrattuale diretto con i clienti finali del Titolare. La relazione contrattuale clientela ↔ Titolare resta interamente del Titolare.

---

## 4. Categorie di dati trattati

Il Responsabile, per conto del Titolare, tratta le seguenti categorie di Dati Personali:

- **Account cliente finale**: email, nome, password (cifrata), lingua preferita
- **Dati ordine**: prodotti acquistati, quantità, prezzi, indirizzo di spedizione (se applicabile), data ordine
- **Metadati tecnici**: indirizzo IP, user-agent, timestamp accessi (per sicurezza e audit log)
- **Pagamenti**: tramite Stripe (Responsabile esterno) — afianco non conserva dati di carta
- **Preferenze marketing**: solo se raccolte esplicitamente dal Titolare

afianco **non** tratta categorie particolari (art. 9 GDPR) né dati relativi a condanne penali (art. 10 GDPR).

---

## 5. Finalità e durata del trattamento

Il trattamento ha le seguenti finalità:

- Fornire al Titolare l'infrastruttura per gestire il proprio negozio commerce
- Permettere ai clienti finali di registrarsi, effettuare ordini, ricevere comunicazioni transazionali
- Generare audit log di sicurezza e integrità

**Durata**: per tutta la durata del contratto SaaS tra Titolare e afianco. Al termine, i Dati Personali vengono restituiti o cancellati secondo la sez. 11.

---

## 6. Obblighi del Responsabile

Il Responsabile si impegna a:

1. Trattare i Dati Personali **esclusivamente su istruzione documentata** del Titolare, inclusi i trasferimenti verso paesi terzi (vedi sez. 8). Eventuali obblighi di legge in deroga vengono notificati al Titolare prima del trattamento.
2. Garantire che il personale autorizzato al trattamento sia soggetto a obblighi di **riservatezza**.
3. Adottare misure tecniche e organizzative **adeguate** ai sensi dell'art. 32 GDPR (vedi sez. 9).
4. Assistere il Titolare, con misure tecniche e organizzative appropriate, nell'adempimento dell'obbligo di rispondere a richieste degli Interessati (artt. 12-23 GDPR).
5. Assistere il Titolare nel garantire il rispetto degli obblighi di cui agli artt. 32-36 GDPR (sicurezza, notifica violazioni, valutazioni d'impatto).
6. Su scelta del Titolare, **cancellare o restituire** tutti i Dati Personali al termine della prestazione (vedi sez. 11).
7. Mettere a disposizione del Titolare tutte le **informazioni necessarie** per dimostrare la conformità agli obblighi del presente DPA.

---

## 7. Sub-responsabili autorizzati

Il Titolare **autorizza in via generale** il Responsabile a ricorrere ai sub-responsabili elencati di seguito. Il Responsabile rimane pienamente responsabile dell'adempimento degli obblighi GDPR da parte dei sub-responsabili.

| Sub-responsabile | Paese | Finalità |
|---|---|---|
| **Hetzner Online GmbH** | Germania | Hosting infrastruttura (VPS, storage) |
| **MongoDB (auto-ospitato)** | Germania | Database operativo |
| **Stripe Payments Europe Ltd.** | Irlanda | Elaborazione pagamenti |
| **Brevo SAS** | Francia | Invio email transazionali |
| **Anthropic PBC** | USA | Modelli AI (chat assistant, analisi) — solo dati aggregati |

L'elenco aggiornato è pubblicato all'indirizzo: https://afianco.app/legal/sub-processors

In caso di **modifiche** all'elenco (aggiunta o sostituzione), il Responsabile informa il Titolare con preavviso di **30 giorni** via email. Il Titolare può opporsi entro tale termine; in caso di opposizione il Responsabile può proporre soluzioni alternative o risolvere il contratto.

---

## 8. Trasferimenti internazionali

I dati sono trattati primariamente nell'UE/SEE. Per i trasferimenti verso paesi terzi (in particolare Anthropic, USA) si applicano:

- **Clausole Contrattuali Tipo (SCC)** della Commissione Europea (Decisione 2021/914)
- **EU-US Data Privacy Framework** (DPF) quando il fornitore vi aderisce

Il Titolare può richiedere copia delle SCC firmate scrivendo a {{platform_controller_email}}.

---

## 9. Misure di sicurezza (art. 32 GDPR)

Il Responsabile applica le seguenti misure:

- **Cifratura in transito**: TLS 1.2+ per tutte le comunicazioni
- **Cifratura a riposo**: AES-256 per i dati su disco
- **Autenticazione**: password con hash bcrypt 12-round; JWT a breve scadenza
- **Anti-brute-force**: rate limit per IP + lockout per account
- **Backup**: snapshot giornalieri, retention 30 giorni, ripristino testato
- **Audit log immutabili**: tutte le operazioni di accesso e modifica tracciate
- **Isolamento multi-tenant**: ogni dato del Titolare scopato su `organization_id` con verifica a livello di query
- **Patching**: aggiornamenti di sicurezza applicati entro 7 giorni dal rilascio
- **Personale**: contratti di riservatezza, accesso minimo necessario

---

## 10. Violazioni dei dati (Data Breach)

In caso di violazione dei Dati Personali, il Responsabile **notifica al Titolare** senza ingiustificato ritardo e comunque entro **72 ore** dalla constatazione, fornendo:

- natura della violazione e categorie di Interessati interessati
- numero approssimativo di Interessati coinvolti
- conseguenze probabili
- misure adottate o proposte per attenuare gli effetti

La notifica all'Autorità di controllo (art. 33 GDPR) e agli Interessati (art. 34 GDPR) resta obbligo del Titolare; il Responsabile fornisce tutta l'assistenza necessaria.

---

## 11. Cancellazione o restituzione al termine

Al termine del contratto SaaS:

- Il Titolare può **esportare** in autonomia tutti i propri dati tramite l'apposita funzione self-service nel pannello admin (formato JSON/ZIP).
- Trascorsi **30 giorni** dalla disattivazione dell'account, tutti i Dati Personali del Titolare e dei suoi clienti finali vengono **cancellati definitivamente** dai sistemi di produzione del Responsabile.
- I backup sono ruotati con retention di 30 giorni; i Dati Personali permangono nei backup fino al naturale scadere del ciclo (massimo 60 giorni totali dalla cancellazione).
- Eventuali obblighi di conservazione di legge (es. fatturazione) sono adempiuti dal Titolare; il Responsabile non conserva alcun dato oltre i termini sopra.

---

## 12. Audit e ispezioni

Il Titolare ha diritto di:

- Richiedere informazioni scritte sull'adeguatezza delle misure di sicurezza del Responsabile (risposta entro 30 giorni)
- Richiedere copia del **rapporto di audit annuale** del Responsabile (se applicabile)
- Effettuare un audit on-site, su preavviso di almeno 30 giorni, non più di **una volta all'anno**, salvo violazioni constatate. I costi dell'audit sono a carico del Titolare.

---

## 13. Responsabilità e limitazioni

Le limitazioni di responsabilità previste dai Termini di Servizio di afianco si applicano anche al presente DPA, fatti salvi gli obblighi imperativi di legge e i casi di dolo o colpa grave.

Il Responsabile è responsabile solo per i danni causati dal proprio inadempimento agli obblighi specificamente imposti dal GDPR ai responsabili del trattamento, o per aver agito al di fuori o in contrasto con le legittime istruzioni del Titolare (art. 82.2 GDPR).

---

## 14. Modifiche al DPA

Il Responsabile può aggiornare il presente DPA per riflettere:

- Modifiche normative (aggiornamenti GDPR, decisioni dell'EDPB, sentenze rilevanti)
- Aggiunta/sostituzione di sub-responsabili (con preavviso ex sez. 7)
- Miglioramenti delle misure di sicurezza

Le modifiche sostanziali vengono comunicate via email al Titolare con preavviso di **30 giorni** e richiedono nuova accettazione. Le modifiche tecniche/redazionali sono pubblicate all'indirizzo: https://afianco.app/legal/dpa

---

## 15. Legge applicabile e foro

Il presente DPA è regolato dal diritto **svizzero**, salvo per le disposizioni che richiedono inderogabilmente l'applicazione del GDPR e della normativa UE in materia di protezione dati.

Per qualsiasi controversia è competente il foro di **Lugano (CH)**, fatti salvi i fori del consumatore.

---

## 16. Contatti

**Titolare del trattamento (Cliente)**
{{merchant_name}}
{{merchant_country}}
Email: {{merchant_email}}

**Responsabile del trattamento (afianco)**
{{platform_controller_name}}
{{platform_controller_country}}
Email: {{platform_controller_email}}

---

*Il presente DPA si intende accettato dal Titolare al momento della conferma via il pannello admin di afianco. La conferma viene registrata in un audit log immutabile con timestamp, IP e User-Agent del confermante.*
