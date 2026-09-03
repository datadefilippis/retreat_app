# LA VETRINA — refinement design mobile + carosello Instagram (ciclo IG, 3/9/2026)

*Il founder prepara un carosello Instagram per convincere operatori:
servono 3 screenshot (profilo mobile, servizi+calendario mobile,
dashboard desktop) belli come i mockup allegati. Ma il profilo
pubblico da mobile oggi non regge lo screenshot: solo design,
interfaccia — SIAMO LIVE con operatori veri, zero logica toccata,
zero API nuove, zero campi nuovi.*

## 0 · Lo stato attuale, misurato dal vivo (prod, 375×812)

Profilo /o/goccia-di-luna da telefono:
1. **Primo schermo = quasi solo foto**: cover ~460px con titolo
   sovrapposto, e SUBITO sotto un'altra foto-card da ~400px. Uno
   screenshot mostra una foto, non un prodotto.
2. **La bio compare DUE volte** (sottotitolo dell'hero + citazione
   sotto la foto).
3. **Identità sparsa**: la città arriva in fondo alla prima card, i
   servizi a ~1300px di scroll, nessuna CTA primaria visibile
   all'arrivo.
4. Servizi = righe di testo con link «Richiedi appuntamento»: onesti
   ma non da vetrina.
5. Nessun calendario in profilo (i mockup lo promettono).

I mockup del founder (la bussola): card identità compatta — avatar
tondo, nome, ruolo, 📍 città, bio breve, chips pratiche, CTA verde
«Prenota una sessione» — poi servizi come card con prezzo e bottone,
poi calendario; desktop: «Benvenuta, Giulia» + Panoramica a 3 numeri
+ prossime prenotazioni.

## 1 · I principi (i paletti del non-stravolgere)

- **Solo pelle**: layout, CSS, riordino di JSX. Stessi componenti,
  stessi percorsi di prenotazione, stessi dati che il profilo GIÀ
  riceve. Nessun endpoint nuovo, nessun campo nuovo.
- **Gli operatori live non devono accorgersi di nulla** se non che è
  più bello: ogni informazione di oggi resta visibile (magari
  ripiegata), ogni link di oggi porta dove portava.
- Desktop non peggiora: le modifiche mobile-first degradano con
  grazia sopra i 768px.
- Ogni onda: collaudo visivo 375×812 E desktop + guardie evolute se
  fotografavano il markup.

## 2 · Le onde

### IG1 — L'IDENTITÀ COMPATTA (il primo schermo che vende)
Il hero si ridisegna come la card del mockup:
- cover come **banda ~38vh** (non 60) con gradiente scuro in basso;
- **card identità che sale sopra la cover** (bordo 16px, ombra
  morbida): avatar tondo dalla foto profilo (anello sottile oro),
  nome in serif, tagline UNA riga, riga «📍 città · ✓ Professionista
  su Aurya dal {anno}», bio in 3 righe con «Leggi tutto» (line-clamp,
  il testo intero resta nel DOM: il crawler lo legge), chips
  discipline (prime 4 + «+N»), **CTA piena verde «Prenota una
  sessione»** che scrolla ai servizi;
- la seconda foto grande NON apre più la pagina: entra in una
  **galleria orizzontale compatta** (120px, scroll laterale) dopo la
  card — le foto restano tutte, ma non mangiano lo schermo;
- via il doppione della bio (una casa sola: la card).
- Su mobile, **CTA sticky in basso** («Prenota una sessione») quando
  i servizi non sono in viewport — pattern già di casa (createbar).

### IG2 — I SERVIZI COME CARD
Ogni servizio diventa una card: nome (serif), riga «60 min · in
presenza oppure online», **prezzo in evidenza** a destra (o «Su
richiesta» discreto), bottone verde pieno «Prenota» per riga — che
fa ESATTAMENTE ciò che fa oggi «Richiedi appuntamento» (solo pelle).
Massimo 4 card visibili + «Vedi tutti i servizi (N)» ripiegabile.

### IG3 — IL CALENDARIO IN VETRINA (coi dati che già arrivano)
Sotto i servizi, un **mini-calendario mensile read-only** disegnato
sui dati che il profilo GIÀ riceve (le occorrenze dei ritiri/eventi
futuri + next_available dove presente): i giorni con qualcosa si
accendono in verde; il tap porta al percorso di prenotazione
esistente. Se l'org non ha nulla in agenda, il calendario NON
compare (mai una griglia vuota). Zero API: è un modo nuovo di
disegnare dati vecchi.

### IG4 — LA DASHBOARD «BENVENUTA» (desktop, per lo screen 3)
Sulla home operatore: saluto «Benvenuta, {nome}» in serif,
**Panoramica** a 3 stat-card (Prenotazioni · Eventi · Clienti — i
numeri che la dashboard già possiede), lista «Prossime prenotazioni»
(data · servizio · cliente · ora, già in pagina oggi). Solo
gerarchia, spaziature e card: nessun numero nuovo, nessun calcolo
nuovo.

### IG5 — COERENZA & POLISH TRASVERSALE
Ritmo a 8pt, angoli 16px, UNA ombra morbida di casa, serif nei
titoli ovunque nel pubblico, breadcrumb più discreto, contrasti
verificati (l'audit del 30/8 fa scuola). Un file di tocchi CSS, non
un tema nuovo.

### IG6 — LA SIMULAZIONE PER IL CAROSELLO
A design implementato: profilo demo curato con dati veri e belli
(foto, bio, 3-4 servizi con prezzi, un ritiro in agenda), e i **3
screenshot finali**: profilo mobile (375×812), servizi+calendario
mobile, dashboard desktop — consegnati come PNG pronti per il
montaggio del carosello. (La cornice-telefono e i testi del
carosello restano al designer/founder.)

## 3 · Collaudo e sicurezza
- Visivo: 375×812 e desktop, prima/dopo per ogni onda.
- Funzionale: ogni link/CTA porta dove portava (click-through sul
  percorso prenotazione completo in locale).
- Guardie: quelle che fotografano il markup del profilo si evolvono
  con nota; nessuna logica cambia = suite backend intatta.
- Deploy separato, col go del founder, DOPO che i tre screenshot
  gli piacciono.

*Ordine: IG1 → IG2 → IG3 → IG5 (mobile completo) → IG4 (desktop) →
IG6 (screenshot). Effort: ~1,5-2 giornate. In attesa del «procedi».*
