# Il Listino — semplificazione commerce (piano v2, blindato)

Data: 28 luglio 2026 (v2: invarianti di compatibilita', analisi
Treatwell con fonti, bisogni reali dell'operatore benessere,
reversibilita' garantita dei tipi congelati).

Principio guida del founder: semplice come Treatwell, ma per gli
operatori olistici. SENZA sfasciare cio' che funziona: eventi con
landing page, calendario, checkout e Stripe restano intatti.

---

## PARTE 0 — Gli INVARIANTI (cosa NON si tocca, verificato a fine di ogni onda)

Questi sono contratti: ogni onda TW chiude con una verifica esplicita
che restino veri. Se un'onda li rompe, si torna indietro.

I1. EVENTI = LANDING PAGE. /e/{org}/{slug} resta la pagina di vendita
    completa del ritiro (galleria, programma, biglietti, colonna
    prenotazione, FAQ, schema Event). I servizi NON avranno landing
    propria di default: vivono nel listino sul profilo. La landing
    /p/{org}/{slug} dei service RESTA VIVA come pagina raggiungibile
    (retrocompatibilita' + slot picker), ma il percorso primario
    diventa il profilo.
I2. STRIPE INTATTO. Zero modifiche a: Stripe Connect onboarding,
    webhook, checkout session, caparra/acconto, fee ledger, split.
    Il Listino cambia DOVE si clicca "prenota", non cosa succede dopo.
I3. CHECKOUT E ORDINI INTATTI. order_creation_service,
    transaction_mode request|direct|approval, downgrade Free
    direct→request, booking_service, token /b/, email ordine:
    invariati. Il listino li CHIAMA, non li riscrive.
I4. CALENDARIO E SLOT INTATTI. Agenda ufficiale, AvailabilityRules,
    generate_available_slots (agenda condivisa cross-prodotto),
    blocked_slots: invariati. Il listino ci si aggancia coi default.
I5. DATI MAI CANCELLATI. Nessun drop, nessuna delete sui prodotti dei
    tipi congelati; ordini storici leggibili sempre (la pagina Ordini
    rende qualsiasi item_type storico).
I6. URL MAI MORTI. /s/*, /services/*, /physicals/* ecc: redirect,
    mai 404. SEO shell aggiornata coi canonical.
I7. RECENSIONI, PASSAPORTO, GT1b, visibilita', GDPR: invariati.
I8. Il modello dati Product NON cambia forma: una riga di listino E'
    un Product item_type=service. Niente nuova collection, niente
    doppia verita'.

Guardia meccanica: tests/test_listino_tw.py conterra' una classe
TestInvariants che verifica I1-I8 (rotte vive, servizi non toccati,
firma delle funzioni checkout invariata) e la suite completa (3.44x
test) deve restare verde a ogni onda: e' la rete di protezione contro
gli sfasci.

---

## PARTE 1 — Stato attuale, misurato (censimento 28/7, invariato da v1)

- Funnel minimo per una consulenza online: 4 macro-step, incluso lo
  STORE OBBLIGATORIO (store_guard 409 su ogni porta di pubblicazione),
  creato a mano, 47 campi configurabili, 7 rotte pubbliche /s/*
- /inizia: 5 step tutti event-centrici; un servizio pubblicato non fa
  avanzare la checklist
- 7 tipi prodotto, 6 wizard (~6.360 righe: Event 1858, Course 1156,
  Digital 863, Rental 861, Physical 850, Service 775 a 4 tab)
- Back-office: ~14-15 voci menu, ~42 pagine
- Il profilo /o/ mostra SOLO i ritiri; i servizi stanno dietro
  "Visita il negozio" → /s/ (doppia vetrina)
- PROD REALE: 2 org, 1 store, 1 ordine, 1 solo prodotto pubblicato:
  "Consulenza reiki" (service). Physical/digital/course/rental:
  adozione zero.

Il motore buono da riusare (non si butta niente di questo):
transaction_mode request|direct con downgrade Free, slot/agenda
condivisa, checkout caparra K1-K4, fee ledger, recensioni verificate,
profilo /o/ ricco del pivot rete, tassonomie.

---

## PARTE 2 — Analisi Treatwell (come funziona davvero, fonti in fondo)

Cosa fa Treatwell per un salone, in concreto:

1. UN SOLO OGGETTO MENTALE: il listino trattamenti. Nome, descrizione
   breve, durata, prezzo. I "pacchetti" sono combinazioni di
   trattamenti dentro lo stesso listino, non un altro tipo prodotto.
2. UN SOLO PROFILO PUBBLICO per luogo ("profilo unico del luogo sulla
   vetrina Treatwell"): presentazione + listino + recensioni +
   prenota. Niente doppio sito.
3. AGENDA AL CENTRO: "agenda digitale per gestire gli appuntamenti,
   ovunque"; le prenotazioni da marketplace, widget sito, bottoni
   Facebook/Instagram atterrano TUTTE sulla stessa agenda.
4. PROMEMORIA AUTOMATICI (SMS/email illimitati) contro i no-show:
   per un'attivita' su appuntamento e' la feature numero uno.
5. MODELLO ECONOMICO ALLINEATO: 25% solo sulla PRIMA prenotazione di
   un cliente nuovo portato dal marketplace; 0% sui clienti che
   ritornano e su quelli portati dai canali propri del salone; ~2%
   sui prepagamenti online. "Paghi solo i clienti nuovi che ti porto".
6. IL RESTO E' OPZIONALE: POS e magazzino sono nel piano Advanced,
   non nel percorso base.

Cosa ne copiamo (e' il cuore del piano): 1, 2, 3 → listino unico,
profilo unico, agenda unica. Il 4 (promemoria) esiste gia' in parte
da noi (appointment_reminder per i service): va promosso a default.

Cosa NON copiamo e perche':
- Il 25% sui nuovi clienti: il nostro modello e' gia' deciso e piu'
  gentile (fee 5% Gratis / 0% Pro sul transato online + abbonamento);
  cambiarlo ora significherebbe rifare fee ledger e piani. Ma la
  LEZIONE di Treatwell la incassiamo: la nostra narrativa commerciale
  deve dire la stessa cosa ("il profilo e i clienti tuoi non ci
  devono niente; paghi solo lo strumento e/o il transato online").
- Il contratto 12 mesi: contrario al nostro posizionamento.
- Il widget embeddabile sul sito del salone: CE L'ABBIAMO GIA'
  (embed a-la-carte + form newsletter): al listino si aggiunge in
  un ciclo futuro un embed "prenota" riusando la stessa infra.

---

## PARTE 3 — Cosa serve DAVVERO a un operatore del benessere

Il nostro operatore tipo non e' un salone con 6 poltrone: e' una
persona (o una coppia, o un piccolo centro) che fa sedute individuali
e qualche esperienza di gruppo. I suoi lavori da fare, in ordine:

1. "Fammi trovare e fammi capire in 10 secondi": pagina con volto,
   storia, cosa faccio, quanto costa → profilo + listino
2. "Fatti prenotare senza che io risponda a 20 messaggi": slot online
   o richiesta strutturata → prenota/richiedi dal listino
3. "Proteggimi dai buchi": caparra sui ritiri, promemoria sulle
   sedute → checkout caparra (c'e') + reminder default (da promuovere)
4. "Riempi il mio ritiro" (2-4 volte l'anno): landing evento ricca +
   directory → /e/ e /ritiri (INVARIANTE I1, non si tocca)
5. "Fammi sembrare professionale": recensioni verificate, link unico
   da mettere in bio → gia' costruito, va solo unificato sul profilo
6. "Non farmi fare l'imprenditore digitale": niente store, niente
   SKU, niente spedizioni, niente configurazioni → la potatura

Cosa NON gli serve (oggi, dati alla mano): vendere olii (physical),
PDF (digital), video corsi (course), noleggi (rental). Possibile
domani? Si', per questo si CONGELA, non si cancella (Parte 4).

Servizi tipo del listino olistico (per i placeholder e le categorie):
seduta individuale (reiki, massaggio, riflessologia...), lezione
privata (yoga, meditazione), consulto (naturopatia, tema natale,
tarocchi), sessione online (via link video), lezione di gruppo
ricorrente, percorso in N incontri (= riga con nota "pacchetto da 5",
niente nuovo tipo: come i pacchetti Treatwell).

---

## PARTE 4 — Reversibilita' dei tipi congelati (garanzie tecniche)

Il congelamento di physical/digital/course/rental e' progettato per
essere riaperto in un giorno, non ricostruito:

R1. Il CODICE resta nel repo: wizard, router, servizi (stock,
    shipping, extras) NON si eliminano; si spengono le porte UI
    (voci menu e rotte di creazione dietro flag). Niente delete di
    file: il diff della potatura e' fatto di `if` e route guard,
    non di rimozioni.
R2. Il flag e' PER-ORG: organizations.legacy_commerce (default
    false). Il system admin lo accende dalla scheda org → per quella
    org ricompaiono menu, wizard e tipi. Nessun deploy necessario.
R3. I DATI restano al loro posto (I5): prodotti, ordini, giacenze,
    spedizioni. Un'org riattivata ritrova tutto com'era.
R4. Il registro product_types resta completo (i 7 tipi validano
    ancora): un documento legacy non diventa mai invalido.
R5. GUARDIA di reversibilita' nel test suite: attivando il flag su
    un'org di test, le rotte wizard rispondono e un prodotto physical
    di prova si crea e pubblica. Cosi' la riattivazione non puo'
    marcire in silenzio.
R6. Documentazione: docs/LEGACY_COMMERCE.md con la procedura di
    riattivazione (2 righe) e l'inventario di cosa e' dietro il flag.

---

## PARTE 5 — Architettura target (v2)

### I due oggetti
1. LISTINO (service): righe = Product item_type=service (I8).
2. RITIRO (event): INVARIATO, con la sua landing /e/ (I1) e la
   directory /ritiri. Il wizard evento non si tocca in questo ciclo.

### La pagina unica pubblica: /o/{slug}
Hero → Chi sono + intervista → LISTINO (righe per categoria, prezzo/
durata, bottone per riga) → Prossimi ritiri (card → landing /e/) →
Gallery → Recensioni → Contatti.

Bottone per riga di listino, riusando I2/I3/I4 cosi' come sono:
- transaction_mode=direct + Stripe pronto → "Prenota": slot picker
  (stesso componente di /p/) in overlay + checkout Stripe esistente
- default (request) → "Richiedi appuntamento": flusso richiesta
  esistente (ordine in stato richiesta + notifica operatore)
- price_mode=inquiry → "Chiedi info"

/s/{slug}* → redirect 301 a /o/{slug} (I6). /p/ resta viva (I1).

### Back-office target (7 voci)
Home · Listino · Ritiri · Calendario · Richieste e ordini ·
Profilo pubblico · Impostazioni.
(Incassi, Recensioni, Visibilita', Newsletter form, Clienti: si
decidono in TW0 dove atterrano; nulla si cancella.)

### La pagina Listino
Editing inline, niente wizard: riga = nome*, categoria, durata,
prezzo o "su richiesta", modalita' (in presenza/online), note.
"Avanzate" collassate = descrizione lunga, immagine, calendario
dedicato, opzioni, campi custom richiesta, promemoria (le TAB 2-3-4
del vecchio wizard diventano un accordion: le impostazioni esistenti
si SFRUTTANO, non si ricostruiscono: stesso payload API products).
Interruttore "Listino online" + link "vedi il tuo profilo".
Promemoria appuntamento: ON di default sulle nuove righe.

### Gate: da store-first a profile-first
Per pubblicare bastano nome pubblico + citta' + foto. Lo store
tecnico si auto-crea invisibile alla prima pubblicazione (name = nome
org, is_default, mai in UI): ordini e legal continuano a referenziare
uno store vero → NIENTE cambi al checkout (I2/I3).

### Onboarding 3 passi
Presentati → Il tuo listino → Sei online (+ Stripe opzionale per
incassare online; ritiro come suggerimento post-onboarding).

---

## PARTE 6 — Piano operativo v2 (onde TW con verifica di non-regressione)

### TW0 — Decisioni founder
- [ ] Congelamento physical/digital/course/rental con garanzie R1-R6
- [ ] POS: proposta congelato col legacy (era legato allo store)
- [ ] /s/ → 301 su /o/
- [ ] Dove atterrano Incassi/Clienti/Newsletter form/Visibilita'
- [ ] Promemoria appuntamento default ON: conferma

### TW1 — Pagina Listino (back-office), zero rotture
- GET/PUT listino sopra i products service esistenti (stessa API
  products sotto, default: transaction_mode=request, agenda ufficiale)
- Pagina /listino: righe inline + Avanzate (accordion che riusa i
  componenti del wizard: AvailabilityRulesEditor, ServiceOptionsEditor)
- Auto-store invisibile alla prima pubblicazione
- /services/new e /services/:id → redirect a /listino
- VERIFICA: la Consulenza reiki appare nel listino senza migrazione;
  suite verde; /p/ e /e/ rispondono identici a prima

### TW2 — Il profilo diventa il negozio (pubblico)
- /public/operator/{slug} espone `listino`; sezione Listino su /o/
  con Prenota/Richiedi (overlay slot picker + checkout ESISTENTI)
- Card directory /operatori: "da X€ · N servizi · categorie"
- SEO: Service schema per riga nel LocalBusiness del profilo
- Fase rete: listino visibile (presentazione), bottoni transazionali
  gated da prelaunch_mode come il resto
- VERIFICA: un acquisto service end-to-end in locale via profilo
  (request e direct) + un acquisto evento via landing /e/ INVARIATO

### TW3 — Potatura reversibile (dopo TW0)
- organizations.legacy_commerce (default off; ON automatico per org
  che possiedono gia' prodotti dei tipi congelati: nessuno oggi)
- Menu a 7 voci; Stores/Store Settings via dalla nav; store_guard →
  profile_guard; /s/* → 301 /o/
- Admin: interruttore legacy nella scheda org + docs/LEGACY_COMMERCE.md
- VERIFICA: guardia R5 (riattivazione funziona), ordini storici
  leggibili, suite verde

### TW4 — Onboarding 3 passi + chiusura
- /inizia riscritta (Presentati → Listino → Online; ritiro suggerito
  dopo); onboarding-status sui 3 passi
- Guardie invarianti I1-I8 in test_listino_tw.py; metrica GA4
  "primo servizio online"; runbook deploy
- VERIFICA: percorso completo da signup nuovo a profilo online in
  locale, cronometrato

Ordine: TW1 → TW2 → (TW0) → TW3 → TW4. EventWizard: ciclo successivo.

---

## Fonti (analisi Treatwell)

- Prezzi e modello: https://www.treatwell.it/partners/prezzi/
  (25% prima prenotazione nuovi clienti marketplace, 0% ritorni,
  ~2% prepagamenti online, agenda/SMS/profilo unico, POS in Advanced)
- Piattaforma partner: https://www.treatwell.it/partners/
- Best practice listino: https://www.treatwell.it/partners/risorse/blog/come-aggiornare-la-lista-dei-servizi-del-tuo-salone-in-primavera-e-ottenere-piu-prenotazioni/
