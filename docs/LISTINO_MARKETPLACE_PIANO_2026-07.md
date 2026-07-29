# Piano Listino in un passo + Marketplace operatori — 29 lug 2026

Quarto ciclo (dopo TW, RS, PN). Richieste founder:
1. configurare una voce di listino TUTTO nello stesso passo, armonioso
   e senza sovraccarico (ispirazione Treatwell)
2. pagina operatori visibile (footer "Esplora operatori") e ricerca
   stile Treatwell: dove (vicino a me / localita'), cosa (tipo
   servizio), quando (data e orario su disponibilita' reali); card
   con recensioni, anteprima servizi, quick view in pagina, poi profilo.

## Parte 1 — Cosa dice il codice (verificato)

LATO OPERATORE
1. "Tutte le impostazioni" porta a ServiceDashboardPage (912 righe,
   10 sezioni). Le 4 cose che un operatore benessere tocca davvero e
   che oggi NON sono nella riga listino: opzioni servizio (varianti
   30/60/90 min, editor ServiceOptionsEditor gia' riusabile con API
   pronte), agenda (il toggle use_default_schedule "calendario
   ufficiale" esiste gia' ed e' ON di default: E' l'agenda unica
   Treatwell), incasso online (transaction_mode direct + gate Stripe),
   foto. Il resto (descrizione lunga, multilingua, regole orari
   per-giorno, T&C, campi ordine, multi-store) e' giustamente avanzato.
2. La riga espansa del listino (RowFields) e' una grid semplice:
   aggiungere sezioni e' facile.

LATO CLIENTE
3. /operatori ha due anime: fase network = landing della rete (scelta
   voluta, resta); fase marketplace = OperatorsIndexPage con filtri
   gia' end-to-end (categorie, localita' testuale, vicino a me con
   geolocalizzazione, raggio, mappa). MA la card e' povera: niente
   rating, niente servizi, niente prezzo, link secco al profilo.
4. I dati per la card ricca ESISTONO gia': reviews_stats sul doc org
   (gia' esposto su /network/members), listino sintetico con
   services_count e price_from (_operator_listino). Manca solo la
   proiezione su /public/operators.
5. Il pattern quick view esiste gia' sul profilo (riga listino
   espandibile PN3): si porta sulla card.
6. Geo: il filtro raggio oggi e' haversine in-memory su 500 store;
   l'indice 2dsphere an3_org_geo esiste ma non e' usato → passare a
   $geoNear per scalare.
7. GAP STRUTTURALE: il filtro "quando" cross-operatore oggi e'
   impossibile in modo scalabile. Gli slot si calcolano a runtime per
   singolo servizio/operatore; non esiste un "chi ha posto il giorno
   X". Serve denormalizzare la disponibilita'.

## Parte 2 — Onde LM

### LM1 — La voce di listino si configura in un passo
Riga espansa riorganizzata in 3 momenti progressivi (mai tutti aperti):
1. Base (sempre visibile, com'e' oggi): nome, categoria, durata,
   prezzo, dove si svolge, nota.
2. "Opzioni e varianti" (accordion): ServiceOptionsEditor riusato
   as-is (label, prezzo, durata override). Copre il pattern Treatwell
   massaggio 30/60/90.
3. "Prenotazione e incasso" (accordion): toggle "Prenotabile sul
   calendario ufficiale" (use_default_schedule, ON default, con frase
   che spiega che gli orari si governano da /calendar) + scelta
   "Su richiesta / Paga online" (transaction_mode, con
   StripeRequiredAlert quando serve) + foto del servizio.
"Tutte le impostazioni" resta per l'avanzato. Microcopy che
accompagna, zero gergo. Guardie: payload invariato per i campi base.

### LM2 — Card operatore ricca + footer
1. /public/operators espone reviews_stats (org_rating), services_count,
   price_from, listino_preview (prime 3 righe da _operator_listino).
2. Card: rating stelle + numero recensioni, "da X euro · N servizi",
   bottone "Vista rapida" che espande IN CARD l'anteprima servizi
   (nome/durata/prezzo) + CTA "Vai al profilo" (l'acquisto vero resta
   sul profilo PN3, niente checkout in card).
3. Footer marketplace: voce "Esplora operatori" nella colonna Esplora
   (in fase network continua a portare alla pagina rete; al flip
   diventa la ricerca completa senza altri interventi).

### LM3 — Barra di ricerca Treatwell (Dove / Cosa)
1. Barra unica sticky in testa a /operatori: Dove (localita' o vicino
   a me, GeoSearchBar riorganizzata), Cosa (tipo servizio: categorie
   listino + categorie ritiri unificate), ordinamento (distanza,
   rating, prezzo da).
2. Backend: /public/operators passa a $geoNear sull'indice 2dsphere
   (scalabilita'), aggiunge filtro service_category e sort.

### LM4 — Il filtro Quando (cantiere strutturale, da solo)
1. Denormalizzazione: collection availability_index {org_id,
   product_id, date, first_slot, last_slot} per i prossimi 30 giorni,
   scritta dal motore slot a ogni cambio di regole, prenotazione o
   blocco calendario + refresh notturno di sicurezza. Indice su date.
2. /public/operators accetta date (e fascia oraria opzionale): filtra
   e ordina chi ha davvero posto quel giorno; la card mostra "primo
   posto libero: gio 14:00".
3. Invarianti: il motore slot resta l'unica fonte di verita' al
   momento del checkout (l'indice e' solo ricerca, mai prenotazione).

### LM5 — Rifiniture design + chiusura
Polish visivo stile Treatwell su card e barra (foto grandi, rating in
evidenza, chip filtri), empty state onesti, mobile, guardie cicliche,
suite, runbook.

Ordine: LM1 → LM2 → LM3 → LM4 → LM5. LM4 e' l'unica onda con modello
dati nuovo: commit isolato, feature flag lato query (se l'indice non
c'e', il filtro data semplicemente non appare).

## Valore
Operatore: il listino si rifinisce dove si crea, in 3 gesti, e
l'agenda resta UNA (Treatwell). Cliente: cerca dove-cosa-quando, vede
subito fiducia (rating) e prezzi, approfondisce senza cambiare pagina
e compra sul profilo. Piattaforma: geo indicizzato e disponibilita'
denormalizzata = ricerca che scala con centinaia di operatori.
