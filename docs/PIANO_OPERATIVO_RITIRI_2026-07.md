# Piano Operativo — La piattaforma dei ritiri
**Journey dell'operatore · Gap analysis AFianco · Motore acconti/rate · Monetizzazione · Piano di build · Luglio 2026**

> Questo piano parte dai panni dell'operatore che organizza ritiri (non dalla tecnologia), mappa ogni suo passo contro ciò che AFianco sa già fare oggi (verificato file per file nel codebase), progetta il motore di acconti e rate, ridisegna la monetizzazione da abbonamento-moduli a fee transazionale, e chiude con un piano di build sprint per sprint. Legenda stato: **OK** = esiste ed è maturo · **PARZIALE** = esiste ma va adattato · **MANCA** = da costruire.

---

## Parte I — Il journey dell'operatore, passo per passo

Mettiamoci nei panni di Giulia, insegnante di yoga e sound healing, che organizza 4 ritiri l'anno. Ogni passo elenca cosa le serve e lo stato reale di AFianco oggi.

### Passo 1 — Ideare il ritiro e definire i prezzi
Le serve: date, location, prezzi per tipologia (camera condivisa/doppia/singola), early bird, posti totali e per tipologia.
**AFianco oggi: OK.** Il wizard eventi a 4 tab (`EventWizard.js`) crea prodotto + data + tier di prezzo in un colpo solo, con capienza per tier E per evento, prezzi override, riordino tier. Il modello evento supporta multi-giorno nativo (`start_at`/`end_at`).

### Passo 2 — Creare la pagina di vendita
Le serve: pagina bella con foto, programma giorno-per-giorno, descrizione della location, FAQ, cosa è incluso/escluso.
**AFianco oggi: PARZIALE.** Esistono landing per evento con slug, cover image, descrizione markdown (5000 char), venue strutturata (indirizzo, coordinate, mappa). Mancano: galleria multi-foto, editor del programma/agenda strutturato, sezione incluso/escluso, FAQ.

### Passo 3 — Impostare come incassare
Le serve: caparra 30% alla prenotazione, saldo 30 giorni prima, oppure 3 rate; politica di cancellazione chiara (rimborso 100% fino a 60 gg, 50% fino a 30, poi 0).
**AFianco oggi: MANCA — è il gap n.1.** Esiste solo il pagamento unico immediato (Stripe Checkout mode=payment). Zero acconti, zero rate, zero carte salvate, zero payment link, zero fatture pendenti. La Parte III progetta questo motore per intero.

### Passo 4 — Pubblicare e condividere
Le serve: un link da mettere in bio Instagram, un widget per il suo sito, la comparsa sul calendario pubblico.
**AFianco oggi: PARZIALE.** Slug/deep-link per evento e SDK embed maturi. Manca il calendario pubblico cross-operatore (oggi ogni org ha solo il proprio catalogo).

### Passo 5 — Promuovere
Le serve: essere trovata da chi cerca "ritiro yoga Puglia"; scrivere alla sua mailing list; codici sconto per i follower.
**AFianco oggi: PARZIALE.** Newsletter con form embeddabili: OK. Coupon: OK. Discovery pubblica per categoria/regione/data: MANCA (è il calendario, Parte V).

### Passo 6 — Ricevere le prenotazioni
Le serve: il partecipante prenota e paga la caparra da solo; per ogni posto raccoglie nome, email, telefono e campi custom (allergie, esperienza, taglia).
**AFianco oggi: OK (sorpresa positiva).** Il sistema attendee è maturo: dati per-partecipante quando si comprano N posti (`AttendeeInfo`), campi custom configurabili (`FieldConfig`), un biglietto QR individuale per posto con pagina web dedicata e stato di consegna email tracciato (`IssuedTicket`). Da rifinire: configurare i campi partecipante direttamente nel wizard (oggi solo post-creazione) e la lista d'attesa quando è sold-out (manca).

### Passo 7 — Tenere d'occhio gli incassi
Le serve: chi ha pagato la caparra, chi deve il saldo, chi è in ritardo; promemoria automatici senza rincorrere nessuno su WhatsApp.
**AFianco oggi: MANCA (dipende dal Passo 3).** La dashboard evento esiste (biglietti emessi/validati, breakdown tier, acquisti) ma non c'è il concetto di "pagamento parziale/scadenza", né promemoria automatici: **nel backend non esiste alcuno scheduler** (no cron, no APScheduler, no Celery) — tutte le email partono solo su azione.

### Passo 8 — Comunicare con i partecipanti prima del ritiro
Le serve: email automatica "manca una settimana" con info pratiche, broadcast per avvisi, risposte alle domande.
**AFianco oggi: PARZIALE.** Il broadcast manuale ai partecipanti esiste già con template pronti (reminder, logistica, cancellazione, testo libero) e localizzazione per lingua del destinatario. Manca la versione *automatica/schedulata* (di nuovo: serve lo scheduler).

### Passo 9 — Gestire l'operatività
Le serve: lista partecipanti con diete/allergie/camere, esportabile; assegnazione camere; check-in all'arrivo.
**AFianco oggi: OK in gran parte.** Gestione biglietti per evento con filtri e re-invio, pagina check-in con scanner QR e conferma manuale. Manca: export CSV lista partecipanti con i campi custom, vista "camere/tipologie" aggregata.

### Passo 10 — Gestire gli imprevisti
Le serve: un partecipante rinuncia (rimborso secondo policy, il posto si libera); oppure deve annullare il ritiro (rimborsare tutti e avvisarli in un colpo).
**AFianco oggi: PARZIALE, con buone fondamenta.** L'annullamento del singolo ordine è una cascata completa e collaudata (libera i posti, invalida i biglietti QR, notifica il cliente via email, ripristina coupon). Mancano: endpoint admin per **emettere il rimborso** (oggi si fa solo dentro Stripe, la piattaforma lo registra via webhook), e la **cascata di annullamento evento** (oggi: stato "cancelled" a mano, poi ordine per ordine).

### Passo 11 — Durante il ritiro
Le serve: check-in, lista sottomano, contatti.
**AFianco oggi: OK.** Check-in QR da telefono già funzionante.

### Passo 12 — Dopo il ritiro
Le serve: email di ringraziamento con foto, invito al prossimo ritiro, la lista clienti che cresce nella sua newsletter.
**AFianco oggi: PARZIALE.** Newsletter e storico clienti ci sono; il follow-up automatico post-evento no (scheduler). Recensioni: non esistono (rimandate a fase 3, scelta deliberata).

---

## Parte II — Gap analysis: il quadro completo

### 2.1 Le sorprese positive (più pronto del previsto)
| Area | Cosa c'è già | Evidenza |
|---|---|---|
| Partecipanti per-posto | Nome/email/telefono + campi custom per ogni posto venduto, snapshot congelato sull'ordine | `models/attendee.py`, `models/order.py` |
| Biglietti individuali | QR univoco, pagina web per biglietto, stato consegna email, scadenza token | `models/issued_ticket.py` |
| Wizard creazione | 4 tab guidati, creazione atomica prodotto+data+tier, protezione modifiche non salvate | `features/events/EventWizard.js` |
| Dashboard evento | Analytics biglietti, breakdown tier, check-in live, azioni | `EventDashboardPage.js` |
| Broadcast partecipanti | Template reminder/logistica/cancellazione/custom, multi-lingua | `services/event_email_service.py` |
| Capienza anti-oversell | Riserva atomica a 2 livelli (tier + evento) con idempotenza e rollback | `services/event_capacity.py`, `tier_capacity.py` |
| Cascata annullo ordine | 12 passi: posti, biglietti, stock, email, coupon, metriche | `services/order_service.py` |
| Fee piattaforma | `application_fee_percent` per-org già nel flusso checkout (oggi a 0) | `payment_providers/stripe/provider.py` |

### 2.2 I gap, in ordine di priorità
| # | Gap | Perché conta per l'operatore | Effort |
|---|---|---|---|
| **P0-1** | **Motore acconti/rate/saldo** (nessun pagamento parziale, no carte salvate, no payment link, no scadenze) | È il dolore n.1: caparre e saldi sono LA ragione per cui oggi usa IBAN+Excel | 3 settimane (Parte III) |
| **P0-2** | **Scheduler nel backend** (zero cron/job: niente promemoria, dunning, follow-up) | Senza, ogni comunicazione resta manuale: il "pilota automatico" promesso non esiste | inclusa in P0-1 (fondazione) |
| **P0-3** | **Calendario pubblico cross-operatore** con categorie/filtri | È la promessa consumer e il motore SEO | 1–1,5 settimane (Parte V) |
| **P0-4** | **Rimborso da admin + cascata annullo evento** | Un annullamento oggi = ore di lavoro manuale ordine per ordine dentro Stripe | 4–5 giorni |
| P1-1 | Campi partecipante configurabili nel wizard (oggi solo post-creazione) | Riduce frizione alla creazione | 2–3 giorni |
| P1-2 | Agenda/programma strutturato + galleria multi-foto + incluso/escluso | Qualità della pagina di vendita | 4–5 giorni |
| P1-3 | Export CSV partecipanti con campi custom | Operatività di base | 1–2 giorni |
| P1-4 | Duplica ritiro su nuova data | Chi fa 4 ritiri/anno ricrea tutto da zero | 2 giorni |
| P1-5 | Onboarding operatore (registrazione → Stripe Connect → primo ritiro) | Time-to-value: 15 minuti o abbandona | 1 settimana |
| P2-1 | Lista d'attesa su sold-out | Nice-to-have finché i volumi sono bassi | fase 2 |
| P2-2 | Link unsubscribe / preference center nelle email | Igiene GDPR, va fatto entro il lancio pubblico | 2–3 giorni |
| P2-3 | Template email personalizzabili dall'operatore | Brand control, non blocca | fase 2 |
| P2-4 | Fix oversell "pagato-ma-non-confermato" | Caso raro oggi documentato: pagamento riuscito ma posti finiti → annullo manuale. Con le caparre va chiuso: riserva del posto al pagamento della caparra | incluso in P0-1 |

---

## Parte III — Il motore di acconti e rate (progettazione)

### 3.1 Cosa configura l'operatore (per ritiro)
**Piano di pagamento** — 3 modalità, scelte nel wizard:
1. **Pagamento unico** (com'è oggi) — per ritiri economici o last-minute.
2. **Caparra + saldo** (il default consigliato): caparra in % (es. 30%) o fissa (es. 150€); saldo dovuto X giorni prima dell'inizio (es. 30).
3. **Rate**: caparra + N rate mensili che si chiudono X giorni prima dell'inizio.

**Politica di cancellazione** (dichiarata sulla pagina, snapshot sull'ordine come già avviene per i consensi): rimborso 100% fino a A giorni, B% fino a C giorni, 0 oltre. La policy pubblicata è quella che il motore applica ai rimborsi — niente discussioni.

### 3.2 Modello dati (2 concetti nuovi, coerenti con i pattern esistenti)
- **PaymentPlan** (sul prodotto-ritiro): `mode` (full/deposit/installments), `deposit_percent|deposit_fixed`, `balance_due_days_before`, `installments_count`, `cancellation_policy[]`. Snapshot congelato sull'ordine alla prenotazione (stesso pattern dello snapshot attendee/consensi).
- **PaymentSchedule** (per ordine): righe `{seq, label, amount, due_at, status: pending|paid|overdue|failed|waived|refunded, stripe_ref}`. È il "libro mastro" che la dashboard incassi mostra all'operatore e il motore usa per promemoria e dunning.

### 3.3 Meccanica Stripe — costruita su ciò che esiste
**Caparra (alla prenotazione):** la Checkout Session attuale (mode=payment, già con application_fee e idempotency) con line item "Caparra — [ritiro]". Alla conferma webhook: **riserva atomica dei posti** (il meccanismo P7/E1 esiste — si sposta il momento della riserva alla caparra, chiudendo anche il bug oversell P2-4), emissione biglietti in stato "confermato — saldo dovuto".

**Saldo e rate — due opzioni, decisione presa:**
- **Opzione A (MVP — scelta):** alla scadenza, lo scheduler genera una nuova Checkout Session e la invia via email ("Salda il tuo posto — 1 click"). Pro: zero carte salvate, zero problemi SCA/3DS, riusa al 100% il flusso già collaudato, il partecipante mantiene controllo. Contro: serve un click del partecipante — mitigato dal dunning.
- **Opzione B (fase 2, se i dati la giustificano):** SetupIntent alla caparra (carta salvata) + addebito off-session automatico alla scadenza, con fallback a email+link se la banca richiede autenticazione. Pro: conversione saldo più alta. Contro: complessità reale (SCA, retry, mandati). *Non nel MVP.*

**Dunning (promemoria automatici, via scheduler + template broadcast esistenti):** T-7 giorni dalla scadenza: promemoria gentile · T-0: "scade oggi" · T+3: sollecito con avviso · T+7: stato "a rischio", notifica all'operatore con azione a scelta (proroga / libera il posto / contatta). Nessuna cancellazione automatica del posto: sui ritiri la relazione conta, decide l'operatore con un click.

**Rimborsi:** endpoint admin `refund` (nuovo) che chiama l'API Stripe, applica la policy snapshot (calcolo automatico dell'importo dovuto in base alla data), aggiorna il PaymentSchedule e innesca la cascata di annullo ordine già esistente. **Cascata annullo ritiro** (nuovo): stato "cancelled" sull'evento → rimborso automatico di tutte le caparre/saldi + void biglietti + broadcast template "cancellation" (già esistente) — da ore di lavoro a un click con conferma.

### 3.4 Lo scheduler (fondazione infrastrutturale)
Scelta: **APScheduler in-process** nel container backend con lock su MongoDB (un solo nodo attivo — l'infra è single-VPS, niente Celery/Redis da aggiungere). Job: scan quotidiano del PaymentSchedule (scadenze → email), reminder pre-evento (T-7, T-1 con template logistica), follow-up post-evento (T+2). Ogni job idempotente e loggato — stesso rigore dei webhook esistenti.

### 3.5 Edge case — comportamento definito a tavolino
| Caso | Comportamento |
|---|---|
| Partecipante rinuncia entro policy | Refund automatico % da policy, posto liberato, biglietto void, email di conferma |
| Rinuncia oltre policy | Nessun refund automatico; l'operatore può concedere refund manuale (override tracciato) |
| Saldo mai pagato dopo dunning completo | Posto "a rischio": decide l'operatore (libera con refund caparra parziale da policy, o proroga) |
| Ritiro cancellato dall'operatore | Cascata: refund 100% a tutti (caparra+saldo), void, broadcast — indipendente dalla policy |
| Pagamento caparra riuscito ma posti esauriti (race) | Non più possibile: riserva atomica contestuale alla caparra |
| Ritiro con piano "unico" | Flusso identico a oggi, zero regressioni |

---

## Parte IV — Monetizzazione: dal listino-moduli alla fee transazionale

### 4.1 Il problema del listino attuale
Oggi AFianco vende bundle di moduli (Free €0 / Solo €19 / Core €49 / Pro €89 / Enterprise €199 + add-on) costruiti attorno a AI assistant e cashflow monitor — **cose che all'organizzatore di ritiri non servono e che confondono il messaggio**. Il valore per lui sta in: incassare bene, essere trovato, gestire i partecipanti.

### 4.2 Il nuovo listino (2 piani, un principio)
Principio: **la piattaforma guadagna quando l'operatore incassa** — incentivi allineati, zero barriera d'ingresso.

| | **GRATIS** | **PRO — 29€/mese** |
|---|---|---|
| Pubblicazione ritiri + calendario pubblico | illimitata | illimitata + posizione in evidenza |
| Prenotazioni, caparre, rate, partecipanti, check-in | tutto incluso | tutto incluso |
| **Fee piattaforma sul transato** | **5%** | **2%** |
| Promemoria/dunning automatici | standard | personalizzabili |
| Newsletter | fino a 500 iscritti | illimitata |
| Campi partecipante custom | 3 per ritiro | illimitati |
| Profilo pubblico operatore | base | esteso (video, articoli) |

Break-even dell'upgrade: sopra ~1.000€/mese di transato il Pro si ripaga da solo (3% risparmiato = 30€) — **l'upgrade si vende con un banner nella dashboard incassi**, non con una trattativa. Ancoraggio esterno: i marketplace USA (BookRetreats, Retreat Guru) prendono il 14–15%.

### 4.3 Implementazione tecnica (leggera, verificata)
- La **fee è già nel codice**: `application_fee_percent` per-org attraversa già tutto il flusso checkout (oggi impostata a 0). Sviluppo: collegarla al piano commerciale (Free=5, Pro=2) al cambio piano — giorni, non settimane.
- **Nascondere i moduli inutili è configurazione, non codice**: il gating esistente nasconde interi moduli dalla UI quando i limiti sono a 0. Si seedano due nuovi commercial plan (`retreat_free`, `retreat_pro`) con AI=0, cashflow=0, e sul nuovo deploy quei moduli non esistono mai agli occhi dell'operatore.
- **Kill list per il nuovo deploy** (nascosti via config, il codice resta nel fork): AI assistant e add-on chat, cashflow monitor, POS, spedizioni/fulfillment fisico, magazzino, noleggi. Restano: eventi, pagamenti, newsletter, clienti, coupon, corsi video (upsell futuro), embed.
- Fatturazione Pro: riusa lo Stripe Billing della piattaforma già esistente (subscription + webhook + stati past_due già gestiti).

---

## Parte V — La piattaforma pubblica: calendario, categorie, profili

### 5.1 Tassonomia (filtri del calendario)
Categorie di lancio (mappabili sulle 9 SIAF): **Yoga · Meditazione & Mindfulness · Detox & Digiuno · Suono & Sound Healing · Massaggio & Bodywork · Breathwork · Cammini & Natura · Cerchi & Femminile sacro · Benessere aziendale**. Ogni ritiro: 1 categoria primaria + tag secondari. Filtri: categoria, regione, mese, durata (weekend/3-5 gg/settimana), fascia prezzo, tipo camera.

### 5.2 Le pagine pubbliche
- **/ritiri** — calendario con card (foto, date, luogo, prezzo "da", posti rimasti — il calcolo advisory esiste già).
- **/ritiri/[categoria]/[regione]** — pagine SEO statiche/rigenerate ("ritiri yoga in Puglia"): è qui che si vince su EventiYoga, perché ogni risultato è *prenotabile subito*.
- **/o/[slug-operatore]** — profilo pubblico: bio, foto, categorie, prossimi ritiri, (fase 3: recensioni).
- **/location/masseria-montanari** — pagina location founding partner: la sala a volta, i ritiri ospitati, contatto per organizzatori. Unica pagina location al lancio — *nessuna directory di strutture* (decisione presa nel business concept: confligge con la Masseria nelle fasi 1–2).
- **Account partecipante unico di piattaforma**: sul deploy nuovo si modella così dal giorno zero (DB vergine — il refactor da 4–6 settimane non serve).

---

## Parte VI — Piano di build, sprint per sprint (~10 settimane)

| Sprint | Durata | Contenuto | Definition of done |
|---|---|---|---|
| **S0 — Fondazione** | 4–5 gg | Fork repo + deploy separato; env rebrand (dominio, Brevo, from-name); nuovo account Stripe Connect platform; seed piani `retreat_free/pro`; kill list moduli; copy "ritiro" al posto di "evento" | Istanza nuova online, wizard crea un ritiro end-to-end col vecchio pagamento unico |
| **S1 — Scheduler + PaymentPlan** | 1 sett | APScheduler con lock Mongo; modelli PaymentPlan + PaymentSchedule; UI piano di pagamento nel wizard; snapshot policy su ordine | Job schedulati girano e loggano; ordine nasce con schedule corretto |
| **S2 — Caparra** | 1 sett | Checkout caparra; riserva posti atomica alla caparra (fix oversell); biglietti "saldo dovuto"; dashboard incassi v1 | Su Stripe test: prenoto con caparra 30%, posti scalati, ticket emesso |
| **S3 — Saldo + dunning + rimborsi** | 1,5 sett | Session saldo generata a scadenza + email; sequenza dunning; endpoint refund admin con policy; cascata annullo ritiro | Ciclo completo testato: caparra → promemoria → saldo → refund parziale da policy; annullo ritiro rimborsa tutti |
| **S4 — Pagina di vendita** | 1 sett | Agenda strutturata; galleria; incluso/escluso; campi partecipante nel wizard; duplica ritiro; export CSV | La pagina ritiro regge il confronto con BookRetreats |
| **S5 — Comms automatiche** | 0,5 sett | Reminder T-7/T-1 (template esistenti agganciati allo scheduler); follow-up T+2; link unsubscribe | Email automatiche end-to-end su un ritiro di test |
| **S6 — Calendario pubblico** | 1,5 sett | /ritiri con filtri; pagine SEO categoria×regione; profilo operatore; pagina Masseria; account partecipante unico | Un utente trova, filtra e prenota un ritiro di un operatore mai visto |
| **S7 — Onboarding + pricing** | 1 sett | Wizard operatore: registrazione → Stripe Connect Express → primo ritiro in 15 min; fee 5/2% collegata al piano; upgrade Pro self-service | Un operatore esterno si attiva da solo, la fee arriva sul conto piattaforma |
| **S8 — Hardening + dogfooding** | 1 sett | QA sul denaro (test suite payment engine); vendita reale dei ritiri Masseria; onboarding assistito dei 3–5 founding member | Primo transato reale; zero intervento manuale su un ciclo completo |

**Totale: ~10 settimane.** (Rispetto alla stima 6–8 del business concept: i partecipanti/biglietti/check-in sono più pronti del previsto, ma scheduler, dunning, rimborsi e cascate — verificati oggi come del tutto assenti — sono lavoro vero che lì era sottostimato. Questa è la stima onesta.)

**Ordine non negoziabile:** prima i soldi (S1–S3), poi la bellezza (S4), poi la scala (S6). Se il tempo stringe, S4 si comprime; S1–S3 no.

---

## Parte VII — Solidità e consistenza (le regole del build)

1. **Il denaro è una macchina a stati esplicita.** Ogni riga del PaymentSchedule ha stati definiti e transizioni sole-andata loggati; nessun importo calcolato al volo due volte.
2. **Idempotenza ovunque tocchi Stripe** — il codebase ha già il pattern giusto (idempotency key sulle session, riserve posti idempotenti per chiave composita, webhook con dedup per event_id): il motore rate lo eredita, non lo reinventa.
3. **Snapshot, mai riferimenti vivi**, per tutto ciò che ha valore legale/economico: policy di cancellazione, piano di pagamento, prezzi — congelati sull'ordine (pattern già usato per consensi e attendee).
4. **Test prioritari dove girano i soldi**: la suite payment engine (caparra, saldo, refund parziale, cascata annullo, race sulla capienza) si scrive in S1–S3 contestualmente, non "dopo".
5. **Superficie piccola**: la kill list non si tocca. Ogni modulo nascosto che si "riaccende" senza decisione esplicita è un bug di focus, prima che di codice.
6. **Un solo linguaggio di dominio**: nella UI e nel codice nuovo si dice *ritiro, partecipante, caparra, saldo* — non evento, ticket-holder, acconto generico. La coerenza del linguaggio è ciò che fa sembrare il prodotto "fatto per me".
7. **Observability sul denaro**: ogni job dello scheduler e ogni transizione di pagamento produce un log strutturato interrogabile — quando Giulia chiama dicendo "Maria dice di aver pagato", la risposta si trova in 30 secondi.

---

## Parte VIII — Rebranding & refinement per il nuovo target

- **Identità**: brand evocativo + dominio SEO in coppia (verificati liberi al 3/7/26: **ritirando.it**, ritiriinitalia.it, ritiriitalia.it, prenotaritiri.it). Prima di registrare: check marchio EUIPO + handle Instagram (30 min).
- **Copy & UI**: tutte le stringhe rivolte all'operatore parlano di ritiri; la dashboard mostra 4 cose sopra la piega: *prossimo ritiro, incassato/da incassare, posti venduti, azioni in attesa*. Tutto il resto (metriche commerce generiche) sparisce con la kill list.
- **Design**: i design token per-store esistenti pilotano il tema caldo/naturale del nuovo brand senza fork del frontend.
- **Metrica nord dell'onboarding**: *dal signup al primo ritiro pubblicato con caparra attiva in meno di 15 minuti.* Ogni scelta di S7 si giudica su questa.
- **Email transazionali**: from-name e wrapper brand nuovi (già env/config); i testi riscritti nel tono del brand (caldo, diretto, zero legalese dove non serve).
- **Sequenza di lancio**: il rebrand non è un big-bang: S0 mette online il brand; il "lancio" pubblico coincide con S6 (calendario) — prima di allora la piattaforma vive solo attraverso i ritiri Masseria e i founding member, che è esattamente il collaudo che serve.

---

## Chiusura — cosa rende questo piano solido

1. **Parte dal journey, non dalle feature**: ogni sviluppo in Parte VI risale a un passo concreto di Giulia in Parte I.
2. **È verificato sul codice, non sulle impressioni**: le "sorprese positive" (attendee, QR, capienza atomica, broadcast) riducono il lavoro; i gap (scheduler, rate, rimborsi) sono certi perché cercati e non trovati.
3. **Il modello di business è nel prodotto**: la fee del 5/2% usa un campo che esiste già; il piano Gratis elimina la barriera; l'upgrade si vende da solo nella dashboard incassi.
4. **Il rischio è sequenziato**: prima il motore dei soldi (il valore immediato per l'operatore), poi la vetrina, poi la scala — e il gate di Fase 0 (interviste + 2 ritiri Masseria ipotecati) resta il cancello prima della settimana 1.
