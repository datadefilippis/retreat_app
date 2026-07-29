# Piano Profilo = Negozio v2 — 28 lug 2026

Terzo ciclo (dopo Listino TW e Ritiri RS). Richieste founder:
1. non e' chiaro dove si configurano termini, condizioni e privacy
2. ritiro senza Stripe: l'avviso parla di "store" e il ritiro deve
   comunque comparire sul profilo pubblico
3. acquisto di un servizio dal profilo TUTTO in una pagina: scegli
   servizio → data e orario (dalla disponibilita' vera) → checkout,
   senza passare da landing /p/ e senza finire sullo storefront
4. anche il ritiro deve comprarsi senza mai vedere lo store
Vincoli: non sfasciare nulla, riusare componenti esistenti, solido
e scalabile. Invarianti I1-I8 sempre validi.

---

## Parte 1 — Cosa dice il codice (verificato)

1. CONDIZIONI POCO SCOPRIBILI. La card "Condizioni di vendita" (RS3)
   esiste ma e' in fondo a Impostazioni, dopo billing e pagamenti.
   Nessun rimando da Profilo pubblico ne' da /inizia.
2. RITIRI SUL PROFILO. Il backend GIA' mostra sul profilo tutti i
   ritiri pubblicati (public.py:4095, nessun gate Stripe/GT1b), ma la
   sezione e' NASCOSTA in fase network (OperatorProfilePage.js:573,
   sitePhase !== 'network'). Il gate GT1b riguarda solo la directory.
3. COPY "STORE" RESIDUI visibili: DirectoryListingHint ("Resta
   prenotabile dal tuo store"), dashboard.json:135 ("appare nel tuo
   store E nella directory"), products.json:359/:833 ("pubblica lo
   store"), bottone "Visita il negozio" sul profilo /o/
   (OperatorProfilePage.js:679, landings.json:492), guscio ?store=1
   della landing /e/ (header "← Catalogo", menu store, Chi siamo → /s/).
4. CHECKOUT: il form vive SOLO dentro StorefrontPage (JSX 2372-3138,
   handleSubmit 1597-1851, ~30 useState). Ma il cuore e' GIA' estratto
   e riusabile: useCheckoutSubmit (submit+Stripe+errori),
   useCouponValidation + CouponInput, useStorefrontCart,
   ProductExtrasPicker, e 3 slot picker PURI (AvailabilityCalendarSlotPicker
   e fratelli, zero fetch interna) + storefrontAPI.getServiceSlots
   (endpoint pubblico /public/services/{id}/slots gia' pronto).
   OrderSummary e' una funzione locale (~200 righe, estrazione facile).
5. PROFILO: data.listino porta solo nome/prezzo/slug/durata/modalita',
   niente flag slot/opzioni: per l'inline serve sapere se un servizio
   ha slot prenotabili.
6. Nel checkout marketplace l'overlay gia' COPRE il negozio (il
   cliente non lo vede); il problema e' il PERCORSO (handoff a /s/)
   e i copy, non la vista.

## Parte 2 — Principi

1. Il profilo /o/ E' il negozio: tutto cio' che si vende si vede e si
   compra da li'. Lo store esiste solo come motore.
2. Estrarre prima, comporre poi: il form checkout diventa un
   componente condiviso USATO ANCHE dallo storefront (parita' totale,
   zero fork di logica). Un solo checkout nel codice, tre superfici
   (storefront legacy, profilo, landing ritiro).
3. La disponibilita' e' quella vera dell'operatore (stessi endpoint
   slot del calendario, nessun nuovo motore).

## Parte 3 — Onde PN

### PN0 — Scopribilita' e copy (subito, basso rischio)
- Card Condizioni di vendita SU in Impostazioni (subito dopo
  l'anagrafica org) + link "Le tue condizioni di vendita" dalla
  pagina Profilo pubblico e da /inizia (passo Presentati).
- Sezione ritiri sul profilo /o/ VISIBILE anche in fase network
  (e' la vetrina dell'operatore, non il marketplace): mostra i
  pubblicati, incluso chi e' su richiesta o senza Stripe.
- Copy sweep: DirectoryListingHint → "Resta prenotabile dal tuo
  profilo"; dashboard.json publish_why → "appare sul tuo profilo e,
  se prenotabile online, nella directory"; products.json 359/833
  senza "store"; via il bottone "Visita il negozio" dal profilo;
  "Chi siamo" della landing → /o/.
- VERIFICA: profilo con ritiro request-mode visibile; nessuna parola
  "store/negozio" nel percorso operatore snello e cliente.

### PN1 — Endpoint profilo pronto per l'inline
- Riga listino arricchita: has_availability_slots, service_options
  (id/label/prezzo), allow_custom_request. Solo campi in piu',
  nessun breaking change.
- VERIFICA: guardia shape + /o/ invariato a occhio.

### PN2 — Estrazione del checkout (parita' totale, la piu' delicata)
- Da StorefrontPage escono: components/checkout/OrderSummary.jsx,
  components/checkout/CheckoutForm.jsx (form 2372-3138
  parametrizzato), hooks/useCheckoutForm.js (i ~30 stati +
  handleSubmit 1597-1851). StorefrontPage li monta identici.
- REGOLA: zero cambi di comportamento in quest'onda. Guardie: il
  payload submit resta identico (stessi campi), suite checkout verde,
  giro E2E acquisto evento su storefront.

### PN3 — Compra dal profilo, tutto in pagina
- Riga listino espandibile sul profilo: opzioni servizio → slot
  picker (AvailabilityCalendarSlotPicker + getServiceSlots) →
  CheckoutForm inline. Su richiesta = stesso form senza pagamento
  (order-request); diretto = submit → redirect Stripe e ritorno su
  /s/checkout-success (gia' vivo).
- La landing /p/ resta viva (SEO + link esterni) ma il profilo non
  ci rimanda piu'.
- VERIFICA: giro completo servizio request e direct dal profilo,
  consensi RS3 presenti, ordine e cliente in Ordini/Clienti.

### PN4 — Ritiro senza store
- Landing /e/: il checkout si apre in pagina (CheckoutForm nel
  drawer/overlay che gia' esiste) senza navigare a /s/. L'handoff
  attuale resta come fallback finche' PN2/PN3 non sono maturi.
- Guscio ?store=1 della landing: solo per org legacy_commerce.
- VERIFICA: acquisto ritiro dal marketplace e dal profilo senza mai
  vedere URL o testi store; invarianti I1-I3.

### PN5 — Chiusura
- Copy pass finale (storefront.json per superfici legacy invariate),
  guardie cicliche (no 'store' nei percorsi snelli), suite completa,
  runbook aggiornato.

Ordine: PN0 → PN1 → PN2 → PN3 → PN4 → PN5. PN2 e' il cantiere grosso
(~1000 righe da estrarre): commit separato, nessuna feature dentro.

## Valore
Cliente: dal profilo alla prenotazione in 3 gesti sulla stessa
pagina, date vere, un solo blocco consensi. Operatore: un solo posto
da condividere (il profilo), condizioni facili da trovare, i ritiri
visibili anche senza Stripe. Codice: UN checkout componentizzato
invece di un monolite, riusato da tre superfici.
