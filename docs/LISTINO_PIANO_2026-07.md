# Il Listino — semplificazione commerce (analisi deep + piano)

Data: 28 luglio 2026. Riferimento del founder: il modello Treatwell
(gestionale + marketplace per estetiste): l'operatore compila un
listino di servizi e quello E' contemporaneamente la sua pagina web e
la sua presenza nel marketplace. Obiettivo: stessa semplicita' per gli
operatori olistici. Meno step, meno pagine, meno configurazioni.

---

## PARTE 1 — Stato attuale, misurato (censimento 28/7)

### 1a. Quanto e' complesso oggi pubblicare una consulenza

Percorso minimo reale (signup → servizio acquistabile):
1. Signup + verifica email
2. Creazione STORE a mano (non si auto-crea; e' OBBLIGATORIO:
   il gate store_guard risponde 409 su ogni porta di pubblicazione)
3. ServiceWizard: 775 righe, 4 tab (base / disponibilita' / opzioni /
   pubblica)
4. Pubblicazione (assegnazione store, termini, campi custom...)

E l'onboarding /inizia NON aiuta: la checklist ha 5 step tutti
event-centrici (profilo, Stripe, store, ritiro creato, ritiro
pubblicato). Chi pubblica una consulenza non fa avanzare la barra:
il funnel ufficiale ignora il caso d'uso piu' comune.

### 1b. L'inventario della complessita'

- 7 TIPI PRODOTTO registrati: physical, service, rental, event_ticket,
  booking, digital, course
- 6 WIZARD per ~6.360 righe di frontend: Event 1858 (6 tab),
  Course 1156, Digital 863 (6 tab), Reservation 861 (6 tab),
  Physical 850 (5 tab), Service 775 (4 tab)
- STORE: modello da 47 campi configurabili (brand color, SEO, legal
  per lingua, nav custom, design tokens, email di consegna...),
  7 rotte pubbliche /s/*, 2 pagine admin (Stores + Store Settings)
- BACK-OFFICE: ~14-15 voci di menu, ~42 pagine protette
- Product: 27 campi
- Contorno commerce: POS, giacenze (stock_service), spedizioni
  (shipping_options), extra/kit, moduli futuri (inventory_tracker...)

### 1c. La frattura profilo/negozio

Il profilo pubblico /o/{slug} (la pagina che il pivot rete sta
rendendo preziosa: intervista, recensioni, gallery) mostra SOLO i
ritiri. I servizi vivono altrove, dietro il link "Visita il negozio"
→ /s/{slug}, una seconda vetrina con altra navigazione, altro layout,
altra gestione. Due pagine pubbliche da capire e mantenere, quando il
visitatore ne vuole UNA: chi sei, cosa fai, quanto costa, prenota.

### 1d. Cosa dice la realta' dei dati (prod, 28/7)

- Organizzazioni reali: 2. Store reali: 1. Ordini: 1.
- Prodotti reali pubblicati: UNO. Ed e' "Consulenza reiki",
  item_type=service, categoria consulenze.

Tradotto: l'unico uso reale del commerce e' esattamente il listino
servizi. Physical, digital, course, rental hanno ZERO adozione reale.
La semplificazione radicale non ha quasi nulla da migrare.

### 1e. Cosa c'e' di BUONO da riusare (non si butta il motore)

- transaction_mode request | direct GIA' esiste sul Product, con
  downgrade automatico direct→request per i piani Free: e' la coppia
  perfetta "Richiedi appuntamento" / "Prenota e paga"
- Slot/agenda: generate_available_slots con agenda condivisa
  dell'operatore + AvailabilityRulesEditor + calendario ufficiale
  default Lun-Ven 9-18: il motore di prenotazione c'e'
- Checkout marketplace K1-K4 (caparra, Passaporto), fee ledger,
  recensioni verificate, GT1b (prenotabile online ⟺ listato)
- Profilo /o/ ricco (pivot rete): hero, bio, intervista, gallery,
  recensioni, geo
- Tassonomia service esistente (categorie consulenze ecc.)

Il problema NON e' il motore: e' l'IMPALCATURA intorno (store
obbligatorio, wizard a tab, tipi inutilizzati, doppia vetrina).

---

## PARTE 2 — Architettura target ("modello Treatwell olistico")

### I due soli oggetti

1. IL LISTINO (servizi): cio' che l'operatore offre su appuntamento.
   Una riga di listino = nome, categoria, durata, prezzo (o "su
   richiesta"), modalita' (in presenza / online / entrambe), note.
2. IL RITIRO (evento): l'esperienza con una data. Resta il wizard
   evento (semplificato in seguito, non in questo ciclo).

Tutto il resto (fisici, digitali, corsi, noleggi) esce dal percorso:
congelato, non cancellato (vedi TW3).

### La pagina unica: il profilo E' il negozio

/o/{slug} diventa presentazione + ecommerce immediato:

1. Hero (foto, nome, tagline, rating)
2. Chi sono + intervista (rete)
3. IL LISTINO ← nuovo: righe raggruppate per categoria, prezzo e
   durata a destra, bottone per riga:
   - "Prenota" (transaction_mode=direct + Stripe pronto): slot picker
     + checkout, riuso del flusso esistente
   - "Richiedi appuntamento" (default, zero configurazione): form
     nome/email/messaggio → ordine in stato richiesta + notifica
     all'operatore (flusso request esistente)
4. Prossimi ritiri (in fase marketplace; oggi nascosto in fase rete)
5. Gallery, Recensioni, Contatti

/s/{slug} sparisce dal percorso: redirect 301 → /o/{slug} (gli URL
non muoiono mai). La condivisione e' UN link: aurya.life/o/tuonome.

### Lo split automatico (come chiesto)

- Pubblichi un RITIRO → entra nella directory /ritiri (gia' cosi')
- Compili il LISTINO → appare sul tuo profilo, e la directory
  /operatori mostra sulla card "da 60€ · 5 servizi · Reiki, Yoga..."
- Due directory, come deciso: /ritiri (eventi) e /operatori (persone
  + servizi). Nessuna terza superficie.

### Il back-office che ne consegue

Menu target (da ~14 voci a 7):
1. Home (dashboard)
2. Listino          ← LA pagina nuova
3. Ritiri           (eventi)
4. Calendario       (agenda + prenotazioni)
5. Richieste e ordini
6. Profilo pubblico (con anteprima = quello che vede il cliente)
7. Impostazioni     (Stripe, team, abbonamento)

Restano raggiungibili ma fuori menu: Incassi, Recensioni (dentro
Profilo), Visibilita', Newsletter form, Clienti (li si valuta in un
secondo ciclo: prima si semplifica il percorso di vendita).

### La pagina Listino (il cuore)

UNA pagina, zero wizard. Lista dei servizi raggruppata per categoria,
editing INLINE (clic sulla riga → si espande la scheda):

Campi per riga (visibili): nome*, categoria, durata, prezzo o "su
richiesta", modalita' (in presenza/online), note brevi.
In "Avanzate" (collassato, mai richiesto): descrizione lunga,
immagine, calendario dedicato (default: agenda ufficiale), opzioni a
scelta, campi custom richiesta.

Un interruttore in testa: "Listino online" (pubblica/nascondi tutto).
Un link fisso: "Guarda il tuo profilo come lo vedono i clienti".

Il modello dati NON cambia: una riga di listino E' un Product
item_type=service. Cambia solo l'interfaccia (e i default). Zero
migrazione: "Consulenza reiki" appare gia' nel listino.

### Il gate: da store-first a profile-first

store_guard (409 store_required) si sostituisce con profile-first:
per andare online bastano nome pubblico + citta' + una foto. Lo store
si auto-crea invisibile dietro le quinte SOLO come contenitore tecnico
(ordini/legal lo referenziano), senza UI, senza scelta, senza slug da
inventare: l'operatore non sapra' mai che esiste.

### Onboarding: 3 passi, non 5

1. Presentati (nome, citta', foto, due righe) → /public-profile
2. Il tuo listino (aggiungi almeno un servizio) → /listino
3. Sei online (link del profilo da condividere + opzionale: collega
   Stripe per incassare online, altrimenti ricevi richieste)
Il ritiro diventa un passo FACOLTATIVO suggerito dopo, non il centro.

---

## PARTE 3 — Cosa si taglia e cosa se ne fa (onesta' sui trade-off)

| Cosa | Sorte | Perche' |
|---|---|---|
| Physical, Digital, Course, Rental | CONGELATI dietro flag org (`legacy_commerce`): spariscono da menu, wizard e nuovo onboarding; i dati restano; riattivabili per singola org dal system admin | Zero adozione reale; un domani un operatore che vende olii o video corsi si riaccende in un click |
| Store come concetto UI (pagine Stores, Store Settings, 47 campi) | Via dalla UI; store tecnico auto-creato invisibile | Era il gradino piu' alto del funnel, per nessun valore percepito |
| Vetrina /s/* (7 rotte) | Redirect 301 → /o/ | Una sola pagina pubblica; la SEO migra col canonical |
| POS /pos/:storeId | Decisione founder (dipendeva dallo store) | Scelta storica "POS resta": va riconfermata nel nuovo mondo |
| Wizard Service (775 righe, 4 tab) | Sostituito dall'editor inline del Listino | Il 90% dei campi ha gia' default giusti |
| Spedizioni, giacenze, extra fisici | Congelati col legacy | Servono solo ai tipi congelati |
| EventWizard (1858 righe) | RESTA cosi' per ora; semplificazione in un ciclo successivo | Un cantiere alla volta |
| Ordini, checkout, slot, recensioni, fee, Passaporto | RESTANO identici | E' il motore buono |

---

## PARTE 4 — Piano operativo (onde TW, step-by-step come RT/BN)

### TW0 — Decisioni founder (bloccano TW3, non TW1-TW2)
- [ ] Conferma congelamento physical/digital/course/rental (dati
      conservati, riattivazione per-org da admin)
- [ ] Sorte del POS nel nuovo mondo (proposta: congelato col legacy)
- [ ] /s/ → redirect a /o/ (proposta: si')
- [ ] Le voci fuori menu (Incassi, Clienti, Newsletter form,
      Visibilita'): dove atterrano (proposta: dentro Home/Profilo,
      si rivaluta dopo)

### TW1 — La pagina Listino (back-office)
- GET/PUT /organizations/current/listino: lettura e salvataggio
  righe (sopra products item_type=service; default transaction_mode
  request, calendario ufficiale)
- Pagina /listino: lista per categoria, editing inline, riordino,
  interruttore online/offline, "Avanzate" collassate
- Auto-store invisibile: alla prima riga salvata, se l'org non ha
  store se ne crea uno tecnico (name = nome org, mai mostrato)
- Nav: voce "Listino"; /services/new e /services/:id redirigono a
  /listino (URL vecchi vivi)

### TW2 — Il profilo diventa il negozio (pubblico)
- GET /public/operator/{slug}: aggiunge `listino` (righe pubblicate,
  raggruppate per categoria, con modalita' e prezzo)
- OperatorProfilePage: sezione Listino con "Prenota" / "Richiedi
  appuntamento" per riga (riuso slot picker + checkout /p/ esistenti,
  anche in overlay senza cambiare pagina)
- Card directory /operatori: "da X€ · N servizi · categorie"
- SEO: Service schema per riga (provider = LocalBusiness del profilo),
  shell aggiornata
- Fase rete: il listino si VEDE (e' presentazione), i bottoni Prenota
  seguono prelaunch_mode come oggi il checkout

### TW3 — La potatura (dopo TW0)
- Flag org `legacy_commerce` (default off; on per org che hanno gia'
  prodotti dei tipi congelati): governa menu, rotte wizard, moduli
- Menu ridotto alle 7 voci; pagine Stores/Store Settings via dalla
  nav; store_guard → profile_guard (nome+citta'+foto)
- Redirect: /s/{slug}* → /o/{slug} (301 SPA + shell canonical)
- Admin: pannello riattivazione legacy per org

### TW4 — Onboarding 3 passi + chiusura
- /inizia riscritta: Presentati → Listino → Online (ritiro come
  suggerimento successivo); onboarding-status riscritto sui 3 passi
- Guardie: profilo pubblico DEVE avere listino se ha servizi
  pubblicati; niente rotte store nella nav; redirect vivi; suite
- Metriche: tempo-a-primo-servizio-online (evento GA4 sul publish
  della prima riga), funnel onboarding

### Dipendenze
TW1 → TW2 (il pubblico legge cio' che il back-office scrive).
TW3 dopo TW0. TW4 ultima. EventWizard e semplificazione ritiri:
ciclo successivo dedicato.

---

## La misura del successo

Oggi: 4 macro-step, ~10 schermate, un concetto (store) da capire
senza valore percepito, e il servizio invisibile sul profilo.

Target: signup → nome+citta'+foto → una riga di listino → ONLINE.
Tre passi, una pagina da gestire, un link da condividere
(aurya.life/o/tuonome) che e' insieme biglietto da visita e cassa.
