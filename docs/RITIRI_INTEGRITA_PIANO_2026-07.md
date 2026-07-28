# Piano Ritiri e Integrita' — 28 lug 2026

Secondo ciclo dopo il Listino (docs/LISTINO_PIANO_2026-07.md). Cinque
fronti aperti dal founder:
1. la pagina Ritiri mostra ancora tutti i tipi di prodotto
2. creazione ritiro da semplificare, linguaggio piu' esplicativo
3. terms e condizioni personalizzate dell'operatore, processo intuitivo
4. bug: /listino perde il menu dell'app
5. pagina Clienti sparita col menu snello; integrita' degli opt-in nel
   checkout (account, newsletter)

Valgono gli INVARIANTI I1-I8 del piano Listino, in particolare:
landing /e/ intatta, Stripe intatto, motore ordini/booking intatto,
dati mai cancellati, codice mai eliminato (solo dietro flag/redirect).

---

## Parte 1 — Censimento (verificato nel codice)

### 1a. La voce "Ritiri" apre l'hub e-commerce

- /events e' solo un redirect a /products?type=event_ticket
  (App.js:632). La pagina vera e' ProductsPage (713 righe): hub
  multi-tipo con chip fisici/digitali/servizi/corsi/noleggi, CTA
  "+ Nuovo prodotto", ricerca che filtra anche per SKU.
- L'operatore ritiri atterra quindi su una pagina che parla di
  "prodotti" e mostra 6 tipi, 5 dei quali congelati da TW3.
- La griglia eventi esiste gia' come componente riusabile:
  EventsGrid (350 righe, embedded in ProductsPage) con cambio stato
  inline draft/published/closed/cancelled. "Duplica" vive nella
  dashboard del singolo evento.

### 1b. EventWizard: 6 step, 1858 righe

- Step attuali: Cosa offri, Quando e dove, Biglietti, Programma,
  Come incassi, Pubblica. Obbligatori SOLO nome, categoria, data
  inizio: tutto il resto e' opzionale ma visivamente pesa uguale.
- Residui e-commerce nel percorso ritiri: transaction_mode/price_mode
  esposti come "modalita' acquisto", COGS ancora nel payload,
  campi partita IVA come esempio, store_ids multi-store, "tipologie
  biglietto" (tier) con drag&drop e preset.
- Il backend e' sano e resta: POST /event-occurrences/wizard crea
  atomicamente Product + EventOccurrence + tiers con rollback.
  Product 1-N EventOccurrence (edizioni) gia' a modello.

### 1c. Terms: due sistemi paralleli che non si parlano

- Sistema A, legale store-level: merchant_terms_content_{it,en,de,fr}
  + privacy, editor markdown (MerchantLegalDialog) DENTRO StoresPage,
  con fallback autogenerato dai dati anagrafici. Reso su /s/:slug/terms.
  PROBLEMA: nel mondo snello /stores e' nascosta, quindi l'operatore
  snello NON PUO' raggiungere l'editor dei propri termini.
- Sistema B, commerciale evento-level: PaymentPlan.cancellation_policy
  (scaglioni giorni → % rimborso, default 60/100 30/50 0/0) + campo
  legacy terms_content per-prodotto. Reso sulla landing /e/ ma NON
  collegato all'accettazione formale al checkout.
- Il contratto quadro Aurya (terms_it.md sez. 13.3) gia' dice: "le
  condizioni di cancellazione e rimborso sono definite dall'Operatore
  e pubblicate sulla pagina del ritiro". Il prodotto non mantiene
  fino in fondo questa promessa.
- Richieste di appuntamento dal listino: passano dallo stesso checkout
  quindi ereditano i consensi SE lo store ha pubblicato i legal;
  altrimenti niente.

### 1d. Bug /listino senza menu

- ListinoPage restituisce un div nudo: manca il wrapper
  <AppLayout> + <Header> che tutte le altre pagine si danno da sole
  (OrdersPage.js:1423, IncassiPage.js:174). Fix da poche righe.

### 1e. Clienti e newsletter: nascoste per eccesso di potatura

- La pagina Clienti (Customer Insights, /modules/customers-light) e'
  l'UNICO posto dove l'operatore vede: consenso marketing per cliente
  (colonna Marketing), filtro "iscritti al marketing", segmento "Da
  ricontattare", export CSV con unsubscribe link, ContactActions.
- Le iscrizioni ai form newsletter dell'operatore accendono proprio
  quel consenso (record_marketing_optin al submit del form). Quindi
  nascondere Clienti nasconde anche "chi si e' iscritto alla mia
  newsletter e chi posso contattare".
- Anche /newsletter-forms (form embeddabili + lista iscritti) e'
  dietro legacyCommerce: un operatore snello non puo' raccogliere
  iscritti.
- Le richieste di appuntamento creano ordine + cliente: i contatti si
  vedono in Ordini, ma la vista consenso/contattabilita' no.

### 1f. Checkout: 6 attriti di integrita'

1. L'opt-in marketing appare SOLO se l'operatore ha pubblicato i
   legal GDPR (gdprRequired): store senza legal = zero consensi
   raccolti, CRM contattabilita' vuoto.
2. Percorso "crea account al checkout": doppio record consent_audit
   per lo stesso click (signup + ordine).
3. Chi spunta marketing al checkout finisce nel CRM ma NON tra gli
   iscritti del modulo newsletter: doppio binario invisibile
   all'operatore.
4. Il Passaporto (platform_account) nasce comunque pending anche
   senza scelta: la checkbox riguarda solo l'account store.
5. Richieste di appuntamento: account pending creato ma magic link
   mai inviato (parte solo al primo pagamento). Promessa in UI non
   mantenuta per gli ordini non pagati.
6. Doppio set di checkbox termini possibile: terms_content legacy F4
   + gdpr_terms (CG-5) coesistono.

---

## Parte 2 — Principi

1. Il vocabolario dell'operatore snello e': ritiro, servizio, listino,
   richiesta, prenotazione, condizioni. Mai: prodotto, SKU, tier,
   transaction mode, fulfillment.
2. Un solo posto per ogni cosa: una pagina Ritiri, una pagina
   Condizioni, una vista Contatti. Zero doppi binari.
3. Il consenso e' un patrimonio dell'operatore: ogni opt-in raccolto
   deve essere visibile e azionabile da lui, una volta sola.
4. Reversibilita' come in TW3: niente delete, ProductsPage e wizard
   completi restano vivi per legacy_commerce.

---

## Parte 3 — Onde

### RS0 — Fix immediati (mezz'ora)
- ListinoPage avvolta in AppLayout + Header come le altre pagine.
- Guardia: test che il sorgente ListinoPage contiene AppLayout.
- VERIFICA: /listino col menu visibile, navigazione avanti-indietro.

### RS1 — Ritiri e' una pagina di ritiri
- Nuova EventsHomePage leggera su /events (niente redirect): titolo
  "I tuoi ritiri", EventsGrid gia' esistente, filtro stato/periodo,
  CTA "Crea un ritiro" → /events/new. Zero chip tipi, zero SKU,
  zero "prodotto".
- ProductsPage resta viva per legacy_commerce (rotta /products) e
  per i tipi congelati.
- Card ritiro con le 3 info decisive: data, posti venduti/capienza,
  stato (+ scorciatoie: vedi pagina, dashboard, duplica).
- VERIFICA: menu → Ritiri apre solo ritiri; org legacy vede ancora
  /products completa.

### RS2 — Wizard ritiro: da 6 step a 4, linguaggio esplicativo
Nessun campo eliminato dal backend: si riorganizza la UI e si
riscrive il microcopy. Proposta di struttura:
1. "Il tuo ritiro": nome, categoria, data inizio/fine, luogo
   (nome + citta'; indirizzo e coordinate in "dettagli facoltativi").
   Sotto ogni campo una riga che spiega dove apparira'.
2. "Prezzo e posti": prezzo, capienza, e SOLO come accordion
   facoltativo "piu' opzioni di prezzo" (le attuali tipologie
   biglietto, ribattezzate "opzioni di partecipazione": es. camera
   singola, condivisa, senza alloggio).
3. "Regole e caparra": come si prenota (subito online / su richiesta,
   spiegato in italiano), caparra e saldo, politica di cancellazione
   con 3 preset (Flessibile, Equilibrata, Rigida) + personalizza.
   Qui si aggancia RS3.
4. "Racconta e pubblica": descrizione, programma giorno per giorno
   (facoltativo), foto, campi partecipante (facoltativo), pubblica.
- Via dal percorso ritiri: COGS dal payload, esempio "partita IVA",
  distribuzione multi-store (lo store e' quello tecnico), price_mode.
- Il commento "4-step" in testa al file torna vero.
- VERIFICA: creazione ritiro completa in preview cronometrata,
  guardia sugli step, editor avanzato ancora raggiungibile.

### RS3 — Patti chiari: le condizioni dell'operatore
Un solo concetto per l'operatore: "Le tue condizioni". Attuazione:
- Nuova sezione "Condizioni di vendita" in Impostazioni (raggiungibile
  nel mondo snello, NON dentro Stores): riusa MerchantLegalDialog
  esistente (spostato/richiamato da li') + un campo strutturato nuovo
  org-level: politica di cancellazione di default (stessi scaglioni
  di PaymentPlan) che il wizard eredita come preset "Le mie condizioni".
- Sulla landing /e/ resta la sezione caparra/cancellazione (gia' c'e');
  sul profilo /o/ e sulle landing /p/ del listino si aggiunge il link
  "Condizioni di [nome operatore]" → /s/:slug/terms (che gia' esiste,
  autogenerato o custom).
- Checkout: UN solo blocco consensi. La checkbox termini legacy F4
  (terms_content) si fonde nel blocco GDPR: se il prodotto ha
  condizioni specifiche, il link della checkbox unica punta a un
  pannello che mostra condizioni store + condizioni del ritiro
  (caparra e scaglioni inclusi). Versione e timestamp gia' snapshottati
  sull'ordine (CG-5), si aggiunge il riferimento al payment_plan.
- Richieste dal listino: stesso blocco consensi anche quando lo store
  non ha legal custom, usando il fallback autogenerato (che esiste
  gia'): cosi' ogni richiesta ha sempre privacy + condizioni accettate.
- VERIFICA: operatore snello pubblica condizioni da Impostazioni;
  cliente al checkout vede UNA checkbox termini con dentro caparra e
  cancellazione; snapshot su ordine.

### RS4 — Clienti e newsletter tornano nel mondo snello
- Menu snello a 8 voci: Home, Listino, Ritiri, Calendario, Ordini,
  Clienti, Profilo pubblico, Impostazioni.
- "Clienti" = Customer Insights esistente (ha gia' tutto: Marketing,
  Da ricontattare, ContactActions). Dentro, tab o link "I tuoi form
  newsletter" → /newsletter-forms (anche lei fuori dal gate legacy).
- Gate backend: require_module anche sugli endpoint lista/overview di
  customer_insights (oggi solo frontend), coerenza MD2.
- VERIFICA: org snella vede Clienti con consensi; org legacy invariata.

### RS5 — Integrita' del funnel (i 6 attriti)
1. Opt-in marketing sganciato da gdprRequired: visibile sempre, con
   informativa che punta ai legal autogenerati se non pubblicati.
2. Consent audit deduplicato nel percorso account+ordine.
3. Fonte unica del consenso: la vista iscritti newsletter
   dell'operatore legge anche i marketing opt-in da checkout
   (customers.accepted_marketing_at), etichettati per origine
   (form, checkout). Niente doppia lista.
4. Passaporto onesto: il magic link "gestisci le tue prenotazioni"
   parte anche alla conferma di una richiesta approvata, non solo al
   pagamento. La promessa in UI diventa vera.
5. Un solo blocco termini (fatto in RS3).
6. Copy del checkout riletto: cosa succede al mio indirizzo email,
   cosa ricevo, come mi cancello. Una riga ciascuno.
- VERIFICA: giro completo guest su richiesta listino e su acquisto
  ritiro; controllare consensi in Clienti, iscritto in newsletter
  view, magic link ricevuto, zero doppioni in consent_audit.

Ordine: RS0 subito, poi RS1 → RS2 → RS3 → RS4 → RS5. Ogni onda:
guardie in tests/ + suite + verifica founder su localhost + commit.
Niente deploy senza ok esplicito.

---

## Valore (risposta alla domanda del founder)

Per il cliente finale: un solo blocco di scelte chiare al checkout,
condizioni di caparra e cancellazione leggibili PRIMA di pagare,
un Passaporto che arriva davvero quando serve.

Per l'operatore: la pagina Ritiri parla la sua lingua, il wizard
chiede prima le 4 cose essenziali, le sue condizioni sono un asset
pubblicato ovunque (profilo, landing, checkout) e ogni consenso
raccolto e' visibile e usabile in una sola vista Clienti. E' la
stessa logica Treatwell del ciclo precedente: meno superfici, piu'
fiducia.
