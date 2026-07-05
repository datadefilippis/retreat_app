# Store — analisi commerce e piano di fix (5 luglio 2026, notte)

Tre problemi segnalati dal founder, analizzati alla radice.

## 1 · Il "phantom store": perché /s/masseria-demo esiste senza averlo creato

**Anatomia (verificata nel DB):** l'org demo è nel formato **legacy
mono-store** ereditato da AFianco: `org.public_slug="masseria-demo"` +
`org.store_settings` — e la collection `stores` è **VUOTA (0 documenti)**.
Tutte le superfici pubbliche funzionano via fallback legacy (landing
resolver, catalogo, sitemap, guard store-first). Risultato paradossale
per l'operatore:
- la pagina "I miei Store" dice: *nessuno store, creane uno*
- ma /s/masseria-demo è online e vende

**Il colmo:** la migrazione che materializza il legacy in uno store vero
(`_ensure_default_store`) **esiste nel codice ma nessuno la chiama più**
(rimossa dal percorso di lettura in un refactoring passato).

**Verdetto da commerce specialist:** il doppio binario (store doc vs
slug legacy) è debito tecnico che LEAKA nella UX. Ogni funzione nuova
deve gestire due forme (l'abbiamo fatto 3 volte: guard, sitemap,
onboarding) e l'operatore non capisce cosa possiede.

### Fix S1 · Materializzare il legacy (0,5 gg)
- [ ] GET /stores richiama la migrazione lazy `_ensure_default_store`
      quando l'org ha public_slug/store_settings e zero store doc
      (la funzione c'è già, è idempotente, gestisce anche la race)
- [ ] Da quel momento: "I miei Store" mostra lo store REALE (nome, slug,
      pubblicato), l'operatore lo gestisce, il paradosso sparisce
- [ ] I fallback legacy restano (difesa in profondità) ma diventano
      codice morto per le org migrate
- **DoD**: la demo apre "I miei Store" e vede masseria-demo gestibile.

## 2 · Home store: la duplicazione menu/card

La home (V1) mostra le card "Esplora" (Ritiri · Prodotti) MENTRE la nav
in alto mostra le stesse voci → duplicazione. Decisione founder: **via
le card, resta il menu**.

### Fix S2 · Home snella (0,25 gg)
- [ ] Rimuovere la sezione "Esplora" dalla home
- [ ] Resta: hero brand (chi sei) + Prossimi ritiri (cosa c'è di vivo)
- [ ] Controllo anti-doppione ulteriore: il vecchio blocco "Merchant
      info" (descrizione store sotto l'header) ora duplica l'hero della
      home → nascosto SULLA home (resta sulle pagine categoria)
- **DoD**: sulla home ogni informazione appare UNA volta.

## 3 · Navigazione spezzata: store → bio → menu perso

Dallo store, "Chi siamo" porta a /o/:slug — che è la pagina profilo
**della directory**: header proprio, niente nav store, niente carrello.
Il visitatore "esce" dal negozio senza accorgersene e non sa tornare.
Nel commerce la regola è: **dentro lo store non si esce mai** — ogni
pagina ha lo stesso guscio (header, nav, footer, carrello).

### Fix S3 · "Chi siamo" DENTRO lo store (0,75 gg)
- [ ] Nuova route **/s/:slug/chi-siamo**: il CONTENUTO del profilo
      pubblico (cover, bio, social, contatti, prossimi ritiri) reso
      DENTRO la shell dello store (StorefrontHeader + CategoryNav +
      footer + carrello persistente)
- [ ] Tutti i link interni allo store puntano lì: nav "Chi siamo",
      footer, CTA hero della home
- [ ] /o/:slug RESTA com'è per il contesto directory/marketplace
      (chi arriva da /ritiri non ha un carrello store da preservare)
      — stessa fonte dati, due gusci
- **DoD**: click su Chi siamo dallo store → bio visibile CON menu e
  carrello; un click e sei di nuovo sui prodotti. Zero interruzioni.

## Ordine e stima
S2 (rapido) → S1 (radice) → S3 (continuità) ≈ **1,5 giorni**.
Funnel di acquisto non toccato; verifica browser completa a ogni fix.
