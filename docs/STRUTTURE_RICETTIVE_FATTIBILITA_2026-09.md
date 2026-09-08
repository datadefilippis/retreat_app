# Strutture ricettive su Aurya: fattibilità e come farlo (8/9/2026)

Domanda del founder: alcuni professionisti hanno chiesto se Aurya
offre il servizio «organizzo il ritiro e trovo la struttura». Con
Valentina vogliono iniziare a contattare strutture per avere una base
di contatti con prezzi, capienza, tipologia e tutti i dettagli utili a
un ritiro. Si può costruire un marketplace di strutture dentro Aurya,
senza rompere il sistema e senza trasformare il gestionale in un
«mappazzone»? Serve un'area nuova con un account apposito? Le
strutture possono diventare un canale di monetizzazione con
abbonamento?

Risposta breve: **sì, è fattibile e si può isolare bene**, ma la
sequenza giusta è «prima il servizio a mano, poi il prodotto», e il
punto delicato non è tecnico: è la Masseria.

## 1. Cosa dice la storia del progetto

A luglio (`docs/BUSINESS_CONCEPT_RITIRI_2026-07.md`, sezione 2) la
directory di strutture fu scartata con tre argomenti: le strutture
pagano poco per un listing (modello Holly Maps), il valore SEO è già
coperto da altri, e soprattutto **il conflitto con la Masseria**:
elencare le masserie concorrenti davanti agli stessi organizzatori
che si stanno corteggiando. La conclusione era: il business è il
gestionale dell'organizzatore, il calendario pubblico dei ritiri è il
motore di domanda, le strutture non si fanno nelle fasi 1-2.

Cosa è cambiato in due mesi: la domanda arriva **dal lato giusto**,
cioè dagli operatori della rete che chiedono aiuto a trovare un posto.
Non è più «vendere visibilità alle strutture», è «servire chi già è
dentro». Questo ribalta il primo argomento (chi paga) e attenua il
terzo: la Masseria diventa la prima struttura della lista, non la
vittima dell'elenco. Resta vero che una directory aperta a tutti,
gratis, alimenta i concorrenti della Masseria: per questo la proposta
tiene la lista **curata e riservata** nella prima fase.

## 2. Cosa serve sapere di una struttura per un ritiro

I dati che Valentina raccoglierà a mano sono lo schema del prodotto
futuro. Meglio raccoglierli subito nel formato giusto.

- Identità: nome, tipo (masseria, agriturismo, casale, eremo, centro
  ritiri, B&B, villa), comune, regione, come si arriva, distanza da
  stazione e aeroporto.
- Capienza: posti letto totali, camere per tipologia (singola, doppia,
  multipla), bagni, se accetta gruppi con letti condivisi.
- Spazi di pratica: sale coperte con metri quadri e altezza, pavimento,
  riscaldamento, spazi esterni per la pratica, silenzio e privacy.
- Cucina: chi cucina (struttura, cuoco esterno ammesso, self), regimi
  (vegetariano, vegano, intolleranze), pasti inclusi.
- Prezzi: a persona a notte per tipologia camera, pensione completa o
  mezza, affitto esclusivo dell'intera struttura, minimo notti, minimo
  persone, acconto e politica di cancellazione, stagionalità.
- Attrezzatura: tappetini, cuscini, impianto audio, coperte, sauna o
  piscina, accessibilità.
- Adatta a: yoga, meditazione, digiuno, cerchi, sound healing, cammini,
  aziende. Disponibilità di massima per stagione.
- Contatti e prova: referente, telefono, email, sito, foto, visite
  fatte da Valentina, note oneste (pro e contro).

Questo è già il modello dati della collezione `strutture`. Raccoglierlo
in un foglio libero e riconvertirlo dopo costa il doppio.

## 3. Le tre strade e l'isolamento

### A. Nuovo «mondo» dentro Aurya (consigliata)

Un'organizzazione con `kind = "struttura"` accanto a quella di default
(`kind = "professionista"`). Stesso login, stessa fatturazione, stesso
renderer SEO, stesso caricamento foto e stesse email; **menu, pagine,
rotte, modello dati e API tutti separati**.

Come si isola davvero, in questo codice:
- **Il campo `kind` sull'organizzazione** (oggi non esiste; c'è
  `industry`, libero e mai usato per decidere). Il gestionale già
  costruisce il menu in base a flag e moduli (`Layout.js`,
  `legacy_commerce`, moduli attivi): si aggiunge un terzo ramo che, per
  `kind = "struttura"`, mostra **solo** le voci della struttura e mai
  quelle del professionista. Una guardia vieta le voci incrociate.
- **Rotte proprie nel registro**: `struttura` (gestionale, categoria
  `app`, noindex) e `strutture` (pubblico, `/strutture/{slug}`). Il
  registro genera nginx: niente rotte a mano.
- **Collezione propria** `strutture` con lo schema della sezione 2,
  legata a `organization_id`. Niente campi nuovi su `organizations`
  oltre a `kind`; niente riuso di `public_profile` (che è pensato per
  una persona con discipline e intervista).
- **Router proprio** `routers/strutture.py` con dependency
  `require_struttura` (org admin **e** `kind == "struttura"`): un
  professionista non può chiamare le API delle strutture e viceversa.
- **Modulo proprio** `venues` nel registro dei moduli, con un piano
  proprio (`plan family = struttura`) nel motore di fatturazione per
  modulo che già esiste: è così che si vende l'abbonamento senza
  toccare i piani dei professionisti.
- **Onboarding proprio**: dall'interruttore di `/accedi?vista=crea`
  nasce un professionista; la struttura entra da una porta sua
  (`/strutture/entra`), su invito nella prima fase.
- **Guardie**: lessico (una struttura non è un «professionista»), menu
  senza incroci, API con 403 incrociato, sitemap separata
  `sitemap-strutture.xml`, parità del renderer.

Pro: un solo prodotto da deployare, riuso di tutto ciò che è
infrastruttura, un'unica identità di marca. Contro: la disciplina va
tenuta con le guardie, non con la buona volontà.

### B. Applicazione separata (secondo dominio, secondo backend)

Isolamento totale, ma si duplicano login, fatturazione, email, SEO,
deploy e monitoraggio. Per due persone è un costo che non ripaga
finché le strutture non sono decine. Da riconsiderare solo se le
strutture diventassero un business con un team suo.

### C. Solo un elenco interno (CRM) senza account

La lista delle strutture vive nel pannello di sistema, la vedono solo
Davide e Valentina, e il servizio agli operatori è a mano. Nessun
account per le strutture, nessun abbonamento. È il modo più veloce di
partire ed è **la fase 0 della strada A**, non un'alternativa.

## 4. Il percorso proposto, con i cancelli

**Fase 0 · Il servizio a mano (2-3 giorni di sviluppo).**
- Collezione `strutture` e tab «Strutture» nel pannello di sistema:
  scheda completa (sezione 2), foto, note di Valentina, stato
  (contattata, visitata, in lista, sospesa).
- Nel gestionale del professionista una sola cosa: il pulsante
  «Cerco una struttura per un ritiro» che apre una richiesta con
  regione, date, persone, budget, esigenze. La richiesta arriva a voi
  per email e nel pannello; la risposta è vostra, a mano.
- La Masseria è la prima scheda.
- Cancello: **dieci richieste vere** dagli operatori in due mesi e
  **venti strutture schedate**. Sotto questi numeri non si costruisce
  altro.

**Fase 1 · La struttura ha il suo account (1-2 settimane).**
- `kind = "struttura"`, mondo separato nel gestionale: la struttura
  compila e aggiorna la propria scheda, carica foto, dichiara
  disponibilità per stagione, riceve le richieste che voi le girate.
- Pagina pubblica `/strutture/{slug}` con renderer SEO e sitemap
  propria, **visibile solo se voi la pubblicate** (curata). La lista
  completa resta riservata agli operatori loggati.
- Abbonamento: piano «Struttura» (visibilità curata + ricezione
  richieste), fatturazione per modulo già esistente. Prezzo da
  validare con le prime cinque strutture, non prima.
- Cancello: **cinque strutture che pagano**.

**Fase 2 · L'incontro (2-3 settimane).**
- Richiesta dell'operatore → strutture compatibili (regione, capienza,
  date) → la struttura risponde con un preventivo dalla sua area →
  l'operatore confronta. Voi restate nel mezzo dove serve.
- Calendario di disponibilità della struttura, richieste con stato,
  email a ogni passaggio (la lezione delle recensioni: nessuno si perde).

**Fase 3 · La prenotazione (da decidere allora).**
- Opzione, caparra e contratto passano da Aurya; commissione oltre
  all'abbonamento. Solo se la fase 2 mostra volume: è qui che il
  rischio legale e operativo sale.

## 5. Monetizzazione, onestamente

- Abbonamento struttura: i comparabili italiani pagano 30-50 euro al
  mese per visibilità pura, e con churn alto. Il valore di Aurya non è
  la visibilità: è **la richiesta qualificata** di un organizzatore che
  ha già un gruppo. Vendere «ricevi richieste vere di ritiri» regge un
  prezzo più alto della visibilità, ma solo dopo che le richieste
  esistono (fase 0).
- Commissione sulla prenotazione: è il modello con più valore ma
  arriva in fase 3 e porta contratti, caparre e contenziosi.
- Il servizio a mano di oggi si può far pagare all'operatore come
  «organizzazione del ritiro»: è consulenza, non prodotto, e non ha
  bisogno di codice.

## 6. Rischi e come si tengono

- **Masseria**: la lista resta curata e riservata; la Masseria è la
  prima struttura e ha la scheda migliore. Se un giorno la directory
  diventa aperta, va deciso a mente fredda, non per inerzia.
- **Mercato a due lati vuoto**: la fase 0 usa gli operatori che già
  chiedono; le strutture entrano perché ricevono richieste, non per
  «essere su Aurya».
- **Il mappazzone**: `kind`, rotte, router, collezione, modulo e
  guardie separate dal primo giorno. Nessuna voce delle strutture nel
  menu dei professionisti e viceversa; una guardia lo controlla.
- **Legale**: in fase 0-2 Aurya mette in contatto, non contratta.
  Termini per le strutture da scrivere alla fase 1 (versione legal
  dedicata, come per i professionisti).
- **Lessico e SEO**: «struttura» è un mestiere diverso da
  «professionista»; pagine pubbliche solo quando curate, altrimenti
  guscio e duplicati (la lezione del ciclo IX).
- **Tempo delle persone**: la fase 0 richiede a Valentina di visitare e
  schedare; è lavoro di campo, non di software. Il software deve
  solo non farle perdere quello che raccoglie.

## 7. Cosa NON tocca il sistema di oggi

Professionisti, listino, ordini, calendario, recensioni, Sound,
Magazine, Cerchio: nessun campo, nessuna rotta, nessun menu cambia.
La fase 0 aggiunge una collezione, un tab admin, un pulsante di
richiesta e le email. Zero migrazioni sui dati esistenti.

## 8. Stima

| fase | sviluppo | dipende da |
|---|---|---|
| 0 · servizio a mano | 2-3 giorni | schema dati concordato |
| 1 · account struttura | 1-2 settimane | 10 richieste, 20 strutture |
| 2 · incontro e preventivi | 2-3 settimane | 5 strutture paganti |
| 3 · prenotazione | da stimare | volume fase 2 |

Se procediamo, il primo passo è la scheda: la scrivo come modulo dati
e come modulo di raccolta per Valentina (anche un foglio con le stesse
colonne va bene), così ogni struttura contattata da domani entra già
nel formato che il prodotto userà.
