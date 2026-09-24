# System admin: regia operatori e Cerchio — analisi e piano

24 settembre 2026. Richiesta del founder: consolidare l'area system admin su tre fronti.

1. **Operatori**: filtrare chi ha solo l'account da chi ha anche creato il profilo; per ognuno vedere nome, nome attività, telefono oltre all'email; poter modificare voci e campi del profilo pubblico.
2. **Verifica email del Cerchio**: togliere o rendere facoltativa la conferma via email, restando in regola col GDPR (nota di consenso con data e ora?), e poter scrivere anche a chi non conferma.
3. **Lista iscritti**: una struttura di informazioni completa (manca il budget, mancano altri dati utili), unica per gli iscritti al Cerchio e per quelli del prelancio, con la provenienza mappata bene. Lo scopo è mappare chi è interessato a ritiri e newsletter.

Sotto: com'è oggi (codice + prod), cosa non va, il piano in tre giri, le decisioni da prendere.

---

## 0. I numeri di prod (24/9, solo lettura)

**Operatori**

| | |
|---|---|
| Organizzazioni | 30 (4 senza alcun `public_profile`) |
| Con bio scritta | 20 |
| Con telefono | 12 |
| Con `nome_persona` | 0 (il campo nasce col giro 1, in locale) |
| Utenti | 31: 1 system admin, 30 admin di org |
| Email verificate | 27 sì, 3 no, 1 senza flag (account pre-verifica) |

Quindi oggi in prod ci sono **10 operatori con account ma senza profilo** e 20 con profilo. È esattamente il filtro che manca.

**Cerchio (`aurya_subscribers`)**

| | |
|---|---|
| Iscritti totali | 39 |
| Confermati | 22 (56%) |
| In attesa di conferma | 17, di cui **11 iscritti a settembre** |
| In attesa per sorgente | cerca-ritiro 10, prelancio 4, newsletter 1, gestionale 1, home 1 |
| Hanno lasciato il budget | 26 su 39 (under500: 18, flessibile: 7, 500–1000: 1) |
| Hanno città | 29 · «dove» (vicino/Italia/estero) 29 · vie 28 · avviso ritiri 30 |

**Lead del prelancio (`prelaunch_leads`)**: 12 documenti, 8 professionisti (therapist 4, venue 1, teacher 1, other 1, senza attività 1) e 4 viaggiatori. 5 di questi 12 esistono anche fra gli iscritti (migrati in agosto: sono i 4 «prelaunch_lead» in attesa più uno).

Lettura: il dato di profilazione c'è già (budget, città, dove, vie) per due terzi degli iscritti, ma **quasi metà degli iscritti non riceve nulla** perché non ha cliccato la conferma. E la conferma è l'unica prova di consenso che esiste per il Cerchio.

---

## 1. Operatori in admin

### 1.1 Com'è oggi

- **Lista** `GET /admin/organizations` (`routers/admin.py:200-260`): solo `skip`/`limit`, **nessun filtro né ricerca** lato server. Il repository legge il documento intero senza proiezione. Per pagina calcola `slug_pubblico` (negozio pubblicato o `public_slug` + vetrina pubblicata), `pubblicate`, `email_titolare` (primo utente admin).
- **Riga** (`_org_summary`, `models/admin.py OrgSummary`): id, name, piano, stato, rete, intervista, directory, `profile_published`, `admin_email`, `profile_slug`, date. **Mancano** nome persona, telefono, `show_contacts`, lunghezza bio, discipline.
- **Pagina** `/admin/operatori` → `OrganizationsTab.js` (1169 righe): colonne Nome (con email sotto), Piano, Profilo (link `/o/slug` o «non pubblicato»), Stato, Creata, Azioni. Filtri solo commerciali (drift/warning/restricted, piano, billing), **nessuna casella di ricerca**.
- **Scheda 360°** `OrgBusinessProfileDialog.js` (`business-recapito` con persona e telefono privato) esiste ma è montata solo da Segnalazioni e Directory, **non dalla lista Operatori**.
- **Scrittura admin sul profilo**: esistono `PUT …/directory`, `/badges`, `/network-member`, `/interview` (unico che scrive dentro `public_profile`). **Nessun endpoint modifica nome, bio, telefono, discipline, sedi.** Nessuno di questi scrive in `audit_logs` (che esiste, con forma canonica in `admin.py:3201`).
- **Pulitore del profilo** (whitelist, social, discipline, sedi, geo, link page): tutto **inline** in `PATCH /organizations/current/public-profile` (`organizations.py:1940-2084`), con cinque effetti post-salvataggio (geocoding, sedi, superficie pubblica, cache, IndexNow). Non c'è ancora `services/profilo_pubblico.py`.

### 1.2 Cosa non va

1. Non si distingue chi si è fermato all'account da chi ha una pagina: la colonna Profilo dice solo «non pubblicato», che vale sia per chi non ha scritto una riga sia per chi ha la bio ma non ha ancora un servizio.
2. Per contattare un operatore bisogna aprire un'altra scheda o guardare il DB: nome, attività e telefono non sono in riga.
3. Correggere una pagina richiede impersonare l'operatore o chiedergli di farlo.
4. Le tre «verità» sullo stato del profilo (lista admin: `profile_published`; onboarding: `profile_ok`/`online`; sequenze: `stato_operatore` con pagina/listino/online) sono calcolate in tre posti diversi. La lista admin deve usare la stessa dell'accompagnamento, altrimenti l'admin vede «pubblicato» dove l'operatore vede «Passo 2 di 3».

### 1.3 Piano · Giro A «Regia operatori» (1 giornata)

**SA1 · Stato del profilo, una verità sola.** Un helper `services/stato_profilo.py::stato_profilo(org, n_servizi)` che restituisce uno di quattro stati, derivati dagli stessi campi di `stato_operatore` (sequenze):

| stato | regola | cosa vede l'operatore |
|---|---|---|
| `account` | nessuna bio | striscia «Passo 1 di 3» |
| `bozza` | bio ma pagina non raggiungibile (niente slug pubblicato) | idem |
| `pagina` | slug pubblicato, nessun servizio | «Passo 2 di 3: il listino» |
| `online` | pagina + almeno un servizio | completo |

Usato dalla lista admin, dalla dashboard admin (conteggi per stato) e, quando toccheremo la striscia, dall'onboarding. Non cambia nulla per l'operatore oggi.

**SA2 · Lista con filtri e ricerca server-side.** `GET /admin/organizations` accetta `q` (nome, nome persona, email, telefono, slug), `stato` (uno dei quattro), `telefono` (con/senza). La riga aggiunge `nome_persona`, `nome_pubblico`, `telefono`, `telefono_pubblico`, `stato_profilo`, `n_servizi`, `bio_len`, `email_verificata` (dal titolare). Il repository passa a una proiezione esplicita. La risposta porta anche i **conteggi per stato**, così i filtri mostrano i numeri («Solo account 10 · Pagina 8 · Online 12»). I letterali protetti dai test restano (`slug_pubblico`, `pubblicate = set(slug_pubblico)`, `email_titolare`, `directory_listed`).

**SA3 · La pagina Operatori.** Sopra la tabella: casella «Cerca nome, email, telefono» + quattro chip di stato con i conteggi + interruttore «senza telefono». Colonne: **Chi** (nome pubblico in grassetto, sotto email e telefono con lucchetto se privato), **Profilo** (chip di stato + link alla pagina se c'è + «N servizi»), **Piano**, **Creato**, **Azioni**. La scheda 360° si apre dal nome. I quattro gesti della regia (Rete, Directory, Stato, Elimina) restano dove sono: i test li guardano.

**SA4 · L'admin modifica il profilo (era P5 nel piano onboarding).**
- Estrazione del pulitore in `services/profilo_pubblico.py`: `pulisci(body, org) → updates` (whitelist, nome persona, social, contatti, discipline, lingue, traduzioni, sedi/geo, link page) e `dopo_salvataggio(org_id, updates)` (i cinque effetti). La rotta dell'operatore chiama le due funzioni: **zero cambi di comportamento**, coperto dai test esistenti su `_PUBLIC_PROFILE_FIELDS` e dal giro E2E del giro 1.
- Nuova rotta `PATCH /admin/organizations/{id}/public-profile` (system admin) che usa le stesse due funzioni, più `name` dell'org. Ogni salvataggio scrive una riga in `audit_logs` (`action: "PUBLIC_PROFILE_ADMIN_EDIT"`, metadata con i campi toccati, prima/dopo per i testi corti, e il `motivo` libero). **Nessuna email automatica** all'operatore: il founder scrive lui (decisione del 24/9).
- UI: nella scheda dell'operatore, un tab **«Profilo»** con un form compatto: nome persona, attività (marchio), tagline, bio (con contatore e la guida a 6 punti), telefono + «mostrato/privato», discipline (lo stesso `SelettoreDiscipline`), sede principale (`LocationAutocomplete`), Instagram/sito/Facebook, campo «Motivo della modifica» obbligatorio. Salvataggio esplicito, anteprima del nome pubblico con la regola «Nome · Marchio». Non si duplica l'editor intero dell'operatore (foto, galleria, link page restano sue).
- **Coda «da rivedere»**: sotto la tabella, un filtro rapido che elenca chi ha bio < 300, nome solo di marchio, telefono mancante, pagina senza listino. È la lista di lavoro per il founder.

Test: nuova guardia `test_regia_operatori_sa.py` (helper stato, filtri, proiezione, audit, rotta admin guardata da `require_system_admin`, estrazione senza regressioni su `_PUBLIC_PROFILE_FIELDS`).

---

## 2. Verifica email del Cerchio: togliere il doppio opt-in?

### 2.1 Com'è oggi

- Iscrizione → documento `pending` → email «Un clic per entrare nel Cerchio di Aurya» → clic → `confirmed` → benvenuto immediato + sequenze. Un solo promemoria a 48 ore (`cerchio_reminder`). Chi non clicca **resta `pending` per sempre**: escluso da tutte le email, escluso dai contenuti riservati, mai cancellato.
- **Prova del consenso** per il Cerchio: solo `consent: true` (che il client manda sempre a `true`), `consent_at`, e il clic di conferma. **Niente IP, user agent, testo accettato, versione, pagina.** La collezione `consent_audit` (immutabile, con IP/UA/versione/hash) esiste ed è usata per account, checkout e marketing dell'operatore, ma **non per il Cerchio**.
- Il testo legale promette il doppio consenso: `backend/legal/privacy_it.md:69` «per la newsletter di Aurya (iscrizione con doppio consenso…)»; le caselle dicono «Confermerai dall'email che ti arriva» (CancelloLettera) e «Una conferma via email, poi sei dentro» (landing Cerchio).
- `confirmed` è **portante in sei punti**: meditazioni riservate (`frequencies.py:635`, con un docstring che ricorda perché `pending` non deve passare), guide riservate (`articles.py:138, 235`), sblocco (`subscribers.py:404`), sequenze (`_FILTRO_SUB`), contatori domanda ritiri (`organizations.py:2438`), token dell'account. Due test vietano espressamente di allentarlo.
- Igiene invii: tutte le email del Cerchio passano con `bypass_gate=True`, quindi **ignorano la lista dei rimbalzi**; il gate legge `email_status` solo su `users` e `customer_accounts`, non sugli iscritti; **nessun header `List-Unsubscribe`**; il link di disiscrizione è solo nel corpo. Il webhook Brevo dei bounce esiste ma non tocca gli iscritti.

### 2.2 Cosa dice la legge (in breve, non è un parere legale)

- Il GDPR **non impone il doppio opt-in**. Impone consenso libero, specifico, informato, inequivocabile (art. 4.11, 7) e la capacità di **dimostrarlo** (art. 7.1). Il Garante italiano lo raccomanda come buona pratica probatoria, non come obbligo.
- Un'iscrizione «a un clic» è lecita se conservi: **chi** (email), **quando** (data e ora UTC), **cosa ha accettato** (il testo esatto della casella e la versione dell'informativa), **come** (casella non preselezionata, azione esplicita), **da dove** (pagina/sorgente, IP, user agent). Questo è il «registro del consenso» che il founder intuiva.
- I rischi reali del singolo opt-in non sono legali ma pratici: indirizzi sbagliati o altrui (qualcuno iscrive un'email non sua e quella persona riceve email non richieste: lì il consenso non è dimostrabile), spam trap e reputazione del mittente su Brevo, reclami. Si mitigano con le regole della sezione 2.4.
- Ogni cambiamento va riflesso nell'informativa (oggi promette il doppio consenso) e nel microcopy dei form. Toccare `privacy_*.md` significa una nuova versione legale (v2.7) e quindi il **re-consent** per i 30 utenti operatori al prossimo accesso (un clic). È accettabile, ma va messo in conto e fatto **prima** di accendere gli invii ai non confermati.

### 2.3 Le tre strade

**A · Tenere il doppio opt-in, ma smettere di perdere la gente.** Zero cambi legali. Si aggiungono: secondo promemoria a 7 giorni, «Reinvia conferma» e «Conferma a mano (con motivo)» in admin, registro del consenso anche per il Cerchio (utile comunque), pulizia dei `pending` dopo 90 giorni. Recupera una parte dei 17, non tutti.

**B · Singolo opt-in con registro del consenso (consigliata).** L'iscrizione è attiva subito per le **email editoriali** (Lettera, benvenuto, avvisi ritiri). La conferma resta come «chiave» solo per i **contenuti riservati** (meditazioni, guide) e per il token dell'account: lì non cambia nulla, i sei punti portanti restano intatti, i due test restano verdi. Richiede: registro del consenso (2.4), igiene invii (2.4), aggiornamento informativa v2.7 e microcopy, nuova semantica del promemoria («conferma per aprire le meditazioni», non «per entrare»).

**C · Singolo opt-in totale** (anche i contenuti riservati si aprono senza conferma). Sconsigliata: riapre il buco già chiuso il 20/8 («chiunque digitasse un indirizzo qualsiasi apriva le meditazioni»), e i contenuti riservati sono la leva che oggi fa cliccare la conferma.

### 2.4 Cosa serve comunque (in A e in B)

1. **Registro del consenso del Cerchio.** All'iscrizione si scrive sul documento un blocco `consenso: {at, testo, versione, ip, user_agent, pagina, modalita}` (`modalita` ∈ `doppio` se poi confermato, `singolo`, `prelancio` per i migrati, `manuale` per le conferme admin) e una riga in `consent_audit` con `document_type: "aurya_newsletter"`, `source: "newsletter_subscribe" | "newsletter_confirm" | "newsletter_unsubscribe"`, `version_tag` = versione del testo della casella, `version_hash` = hash del testo. Nota: `consent_audit` ha TTL 365 giorni; la prova per la newsletter deve durare **fino a revoca**, quindi la copia sul documento dell'iscritto è quella che conta. I testi delle caselle vanno centralizzati in un file (`services/testi_consenso.py` + specchio FE) con versione, così `versione` non è inventata.
2. **Igiene invii.** Gli iscritti entrano nel gate: il webhook Brevo scrive `email_status` anche su `aurya_subscribers`; le email editoriali (sequenze, promemoria, Lettera) **non** usano più `bypass_gate` (resta solo per conferma e magic link); header `List-Unsubscribe` + `List-Unsubscribe-Post` nel payload Brevo (Gmail/Yahoo li richiedono dal 2024 per i mittenti bulk); il link di disiscrizione resta nel corpo.
3. **Stop automatico** per chi non conferma e non interagisce: in B, un `pending` che dopo 90 giorni non ha mai confermato viene messo in `sospeso` (niente più invii, non cancellato). Protegge la reputazione e rispetta la minimizzazione.
4. **Conferma manuale in admin** con motivo e riga di audit, per chi si iscrive a voce o via WhatsApp.

### 2.5 Sequenza di rilascio se si sceglie B

1. Giro B1 (codice, deployabile da solo): registro del consenso + igiene invii + azioni admin. Nessun cambio di comportamento verso gli iscritti.
2. Legale v2.7: la frase dell'informativa (×4 lingue) diventa «iscrizione con consenso registrato: data e ora, indirizzo IP, testo accettato; conferma via email per i contenuti riservati»; microcopy delle caselle («Ti scriviamo da subito; per le meditazioni riservate ti chiederemo un clic di conferma»). Re-consent operatori.
3. Giro B2: interruttore `CERCHIO_SINGOLO_OPTIN=1`: `_FILTRO_SUB` diventa `status in (pending, confirmed)` per i passi editoriali, il promemoria cambia testo, lo stop a 90 giorni si accende. I 17 in attesa di oggi ricevono la prima Lettera **solo** se il loro consenso è ricostruibile (hanno `consent_at` e una sorgente con casella: tutti tranne i 4 del prelancio, che vanno confermati a mano o esclusi).

---

## 3. La struttura dati dell'iscritto e la lista in admin

### 3.1 Com'è oggi

- Documento: `email, name, language, source, consent, consent_at, status, created_at, confirmed_at, unsubscribed_at/by, reminder_sent_at, sequenza{}, preferences{topics, format, retreat_alert{enabled, scope, regions}}, profile{interests, city, travel, budget}`. Il **budget c'è nel dato** (26 su 39) ma **non è una colonna** della tabella: appare solo nel dettaglio. Il CSV lo ha.
- **Provenienza**: `source` è una stringa libera con almeno 13 forme (`cerca-ritiro`, `newsletter`, `home_letter`, `blog_<cat>`, `gate_<slug>`, `meditazioni`, `cancello:<slug>`, `sound:esplora:<slug>`, `sound:lab:<slug>`, `signup_pro`, `account_signup`, `gestionale`, `frequenze:<slug>`, più il suffisso `:<porta>`). La «porta» è **derivata in lettura** da `porta_cerchio()`. Niente URL, referrer, UTM, dispositivo. Il filtro «Fonte» in admin mostra le stringhe grezze.
- **Lead del prelancio**: collezione a parte con campi propri (`type`, `activity`, `phone`, `message`, `venue_type`, `capacity`, `budget`, `travel`, `interests` liberi). Tab «Contatti dalle landing», sola lettura. Un lead viaggiatore diventa iscritto solo con lo script una tantum di agosto; un lead professionista non c'entra col Cerchio.
- **Tabella admin** (`IscrittiTab.js`): Email, Nome, Stato, Fonte, Iscritto, Confermato, Disiscritto, Vie, Città, Dove, Avviso ritiri. Filtri: stato, porta, fonte, ritiri, regione, interesse, testo. Azioni: solo «Disiscrivi». Niente reinvio conferma, niente conferma manuale, niente nota, niente cancellazione (GDPR art. 17 la fa solo l'utente con account).
- Brevo riceve gli attributi ma **non il budget**.

### 3.2 La struttura completa (una per tutti, anche i migrati)

Sei blocchi, tutti già scrivibili senza toccare le collezioni esistenti (si aggiungono campi, non se ne tolgono):

| blocco | campi | note |
|---|---|---|
| **Identità** | email, nome, lingua | |
| **Consenso** | at, testo, versione, ip, user_agent, pagina, modalita, confirmed_at | sezione 2.4 |
| **Provenienza** | canale, superficie, dettaglio, porta, url, referrer, utm{source, medium, campaign}, dispositivo (mobile/desktop) | scritta **all'iscrizione**, non derivata |
| **Interessi** | topics (temi editoriali), format, vie (interests) | come oggi |
| **Ritiri** | avviso {enabled, scope, regions}, città, dove (travel), **budget**, quando (opzionale, nuovo: «entro 3 mesi / quest'anno / non so») | il «quando» è l'unico dato che manca davvero per qualificare la domanda |
| **Ciclo di vita** | status, created_at, unsubscribed_at/by, reminder_sent_at, sequenza{}, email_status (bounce), ultima_email_at, n_email, note_admin[], tag[] | note e tag sono l'operatività del founder |
| **Legami** | account piattaforma (se esiste), lead prelancio (id), organizzazione (se `gestionale`/`signup_pro`) | per non vedere lo stesso essere umano in tre liste |

**Provenienza, tassonomia a tre livelli** (mappa in `services/provenienza.py`, unica fonte, con etichette umane):

| canale | superfici |
|---|---|
| `sito` | `cerca-ritiro`, `home`, `landing-cerchio`, `esperienze` |
| `magazine` | `articolo:<slug>`, `guida:<slug>` (gate), `cta-categoria:<cat>` |
| `sound` | `meditazioni`, `cancello:<slug>`, `esplora:<slug>`, `lab:<slug>`, `frequenza:<slug>` |
| `account` | `signup`, `signup-pro`, `reinvio` |
| `gestionale` | `lettera-operatore` |
| `prelancio` | `lead-viaggiatore`, `lead-professionista` |
| `manuale` | `admin`, `import` |

La `porta` (parametro `?porta=` / UTM) resta un asse separato: da dove è arrivato il traffico, non dove si è iscritto. Uno script `migra_provenienza.py` rimappa i 39 esistenti dal `source` grezzo (tabella di corrispondenza, `--prova` prima), e `source` **resta** com'è per compatibilità con sequenze e test.

**Lead del prelancio**: i 4 viaggiatori sono già iscritti (migrati); i **professionisti** (8) non appartengono al Cerchio: proposta di spostarli in una vista «Contatti professionisti» dentro `/admin/operatori` (tab Account), con un bottone «Ha creato l'account?» che li lega all'org se l'email coincide. La collezione resta come archivio; il tab «Contatti dalle landing» sparisce dal Cerchio.

### 3.3 La pagina Iscritti rifatta (user-friendly, controllo pieno)

- **In testa, la mappa**: quattro card (iscritti, confermati, in attesa, disiscritti) + tre piccole ripartizioni **cliccabili come filtri**: per budget, per «dove», per canale. `GET /admin/newsletter-stats` si estende con `by_budget`, `by_travel`, `by_canale`, `by_regione`.
- **Filtri**: testo, stato, canale › superficie (due tendine collegate), porta, budget, dove, regione, vie, avviso ritiri, «con telefono» (dai lead), periodo di iscrizione.
- **Tabella** con colonne scelte dall'admin (selettore colonne, scelta ricordata nel browser). Predefinite: Email · Nome · Stato · Provenienza (canale › superficie) · Iscritto il · Budget · Dove · Città · Avviso ritiri · Email ricevute. Disponibili in più: Vie, Temi, Lingua, Confermato il, Porta, Ultima email, Tag, Consenso (modalità).
- **Scheda iscritto** (drawer) con i sei blocchi per esteso, il registro del consenso leggibile («ha accettato il testo v3 il 12/9 alle 18:42 da cerca-ritiro, IP …»), la cronologia (iscritto, promemoria, confermato, email della sequenza), le note e i tag.
- **Azioni** (tutte con riga di audit): Reinvia conferma · Conferma a mano (motivo) · Modifica preferenze (ritiri, budget, città, vie) · Aggiungi nota / tag · Disiscrivi · **Elimina** (cancellazione GDPR su richiesta, con conferma a due passi) · Esporta la scheda (JSON).
- **CSV** allineato alle colonne: aggiunge canale, superficie, porta, budget, consenso, n_email.
- **Brevo**: attributo `AURYA_BUDGET` e `AURYA_CANALE`, così le liste in Brevo si segmentano con gli stessi assi.

### 3.4 Piano · Giro B «Cerchio, dati e regia» (1,5 giornate)

- **CB1** `services/provenienza.py` + scrittura all'iscrizione (canale, superficie, porta, url, referrer, utm, dispositivo) + script di migrazione dei 39 + filtri e stats per canale.
- **CB2** Registro del consenso (2.4 punto 1) con testi centralizzati e versionati; `consent_audit` esteso ai due nuovi enum. Retroattivo: ai 39 si scrive `modalita: doppio` se confermati, `prelancio` per i 4 migrati, `singolo-senza-prova` per gli altri pending (etichetta onesta: sapremo che per loro la prova è debole).
- **CB3** Lista rifatta (3.3): stats, filtri, colonne, scheda, azioni con audit, CSV, Brevo budget.
- **CB4** Igiene invii (2.4 punto 2): gate sugli iscritti, bounce dal webhook, header List-Unsubscribe, `bypass_gate` solo dove serve.
- **CB5** Lead professionisti spostati nella regia operatori; tab «Contatti dalle landing» ritirato.

Giro C (solo se si sceglie B della sezione 2): legale v2.7 + interruttore + promemoria nuovo + stop a 90 giorni (0,5 giornata di codice più i testi legali ×4).

---

## 4. Ordine consigliato e vincoli

1. **Giro A (operatori)** per primo: è isolato, non tocca gli iscritti, e sblocca il lavoro di regia sui 10 «solo account» già oggi.
2. **Giro B** subito dopo: CB1+CB2 sono la base di qualunque scelta sull'opt-in; CB3 è la lista che il founder usa; CB4 è dovuto comunque.
3. **Giro C** solo dopo la decisione e dopo il legale.

Vincoli che restano fermi: gli operatori in prod non cambiano stato né ricevono email nuove per effetto dei giri A e B; `confirmed` resta la chiave dei contenuti riservati; nessun campo esistente viene rinominato o rimosso; ogni scrittura admin lascia una riga di audit; tutto dietro test di guardia con la stessa disciplina dei giri precedenti.

## 5. Decisioni da prendere

1. **Opt-in**: A (tenere il doppio e recuperare meglio), **B** (singolo per le email, conferma solo per i riservati: consigliata) o C (singolo totale, sconsigliata).
2. Se B: ok a una **versione legale v2.7** con re-consent di un clic per i 30 operatori, prima di accendere gli invii ai non confermati?
3. I **4 lead del prelancio** in attesa (iscritti da noi ad agosto, mai confermati): confermarli a mano (li conosci) o lasciarli fuori?
4. Il campo **«quando»** (orizzonte del ritiro) nel form di cerca-ritiro: aggiungerlo? È una domanda in più nel form, ma è quella che trasforma un iscritto in una domanda qualificata.
5. **Lead professionisti** fuori dal Cerchio e dentro la regia operatori: ok?
6. Nel tab «Profilo» dell'admin, il **motivo della modifica** obbligatorio (finisce nell'audit e resta a futura memoria): ok?
