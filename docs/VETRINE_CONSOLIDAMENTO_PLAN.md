# Vetrine pubbliche — analisi olistica e consolidamento (5 luglio 2026, sera)

Richiesta founder: refinement olistico di directory E store come appaiono al
pubblico + analisi del processo di creazione di TUTTI i prodotti e di come
appaiono nello store con le voci menu automatiche. Domande guida: *"gli store
sono navigabili facilmente e hanno design moderno e capibile? e la directory?
in entrambe riesco a risalire in maniera semplice a prodotti, pagine, bio
operatore?"*

## 0 · Le risposte oneste alle tue domande

**La directory è navigabile e moderna?** SÌ, dopo F1 — hero, ricerca,
categorie a chip, card con operatore cliccabile. Voto 8/10. Rifiniture
possibili (sotto), nessun problema strutturale.

**Lo store è navigabile e moderno?** NI. Le fondamenta sono buone (menu
categorie automatico, card evento forte, checkout onesto) ma ha DUE problemi
strutturali:
1. **Non esiste una home**: /s/:slug REDIRIGE alla prima categoria — l'utente
   atterra su una lista secca, senza vetrina, senza identità, senza "chi è
   questo operatore". È la differenza tra un negozio e un magazzino.
2. **Dall'header non risali a niente**: logo+nome+carrello, stop. La bio
   operatore è raggiungibile SOLO dal footer ("Chi siamo", F2.1). Nessuna
   ricerca globale (esiste solo dentro la pagina categoria).

**Riesco a risalire a prodotti/pagine/bio da entrambe?** Directory: sì
(card→landing→profilo→store, F2.1). Store: solo scendendo fino al footer —
da fixare nell'header.

**Il processo di creazione è unificato?** NO — è il gap più grosso lato
operatore (dettaglio in §2).

## 1 · Stato reale delle vetrine (verificato)

| Superficie | Cosa c'è | Gap |
|---|---|---|
| Menu store automatico | `CATEGORY_DEFS` per item_type (Ritiri/Corsi/Servizi/Prodotti/…), voci SOLO se count>0 — solido, zero backend | Nessun contatore; dentro "Ritiri" niente sotto-filtro per categoria tassonomica (yoga/detox…) |
| Card store | Variants per tipo (`build*CardProps` ×6) — la card evento è forte (foto dark, badge data) | Le altre 5 variants non sono alla qualità della card evento/directory; anatomie diverse |
| Header store | Logo, nome, lingua, carrello, account; nav categorie sotto; custom links merchant (Phase 8.2) | NIENTE ricerca, NIENTE "Chi siamo"; il brand respira poco |
| Home store | **NON ESISTE** (redirect a prima categoria) | Il gap n°1 |
| Footer store | Privacy, Termini, Chi siamo→profilo, Scopri altri ritiri→directory (F2.1) | ok |
| Directory | F1 fresca: hero+search+chips+card+sticky | Tap categoria sulla card non filtra; ricerca non sticky |

## 2 · Processi di creazione — l'incoerenza misurata

I 5 wizard hanno 5 spine dorsali DIVERSE (verificato nel codice):

| Wizard | Tab |
|---|---|
| Ritiro (Event) | base → where → tickets → payments → publish |
| Servizio | base → when → options → publish |
| Fisico | **identity** → pricing → fulfillment → extras → publish |
| Digitale | **identity** → pricing → file → policy → extras → publish |
| Noleggio | (flavor range/slot, altra struttura ancora) |

Problemi concreti:
- **Naming incoerente** (base vs identity) e ordini diversi → l'operatore
  multi-prodotto ri-impara ogni volta. Va bene che gli step CENTRALI
  differiscano (un file per il digitale, la spedizione per il fisico), ma
  primo e ultimo tab devono essere IDENTICI ovunque.
- **Categoria: tre regimi diversi** — Ritiro: dropdown tassonomia
  OBBLIGATORIO (fix di oggi); Fisico: TESTO LIBERO che non alimenta nulla
  (il menu store usa item_type, non category); Servizio/Digitale: nulla.
  Il testo libero è il peggio dei due mondi: fatica per l'operatore, zero
  valore per il visitatore.
- **Gate store-first** applicato oggi SOLO al wizard ritiri: gli altri tipi
  si pubblicano ancora senza store → incoerenza col principio appena deciso.
- Il tab Pubblica ha layout/riepiloghi diversi per tipo.

## 3 · Il piano — V1→V4 (senza sfasciare: additivo + unificazione graduale)

### V1 · La home dello store ✅ (fatto 5/7/2026 sera — merge su main)
Sostituisce il redirect: /s/:slug diventa una VETRINA.
- [ ] **Hero brand**: cover del profilo pubblico (o gradient brand), logo,
      nome, bio breve + "Scopri chi siamo" → profilo — il negozio ha una
      faccia, e la bio è a UN click dall'ingresso
- [ ] **Categorie visuali** con conteggi (dal menu automatico esistente)
- [ ] **In evidenza**: prossimi ritiri (se esistono) + ultimi prodotti —
      2 sezioni max, niente muri di card
- [ ] Il redirect resta SOLO per store mono-categoria con ≤N prodotti
      (li porti diretti al sodo)
- **DoD**: atterri su /s/:slug e in 5 secondi sai CHI è l'operatore e COSA
  offre; bio a 1 click.

### V2 · Header store navigabile ✅ (fatto 5/7/2026 sera — Chi siamo + contatori nella nav; la ricerca vive nelle pagine categoria e nella home, non duplicata nell'header)
- [ ] Ricerca globale nel header (client-side sul catalogo già caricato,
      come la directory)
- [ ] Voce "Chi siamo" → profilo (accanto alle categorie)
- [ ] Contatori discreti sulle voci categoria
- **DoD**: da QUALSIASI pagina store raggiungi bio e ricerca in 1 click.

### V3 · Card unificate ✅ (verificato 5/7/2026: la shell CommerceCard era GIA' unificata — aspect 16/10, token radius/shadow, hover — le 6 varianti passano solo dati. Rifiniture directory fatte: tap categoria filtra + search sticky)
Un'unica anatomia per TUTTE le card (store + directory): immagine
full-bleed → badge contestuale (data per ritiri, durata per corsi, "digitale"
per file) → titolo → riga info → prezzo + CTA. Stessi radius/hover/skeleton
del tema. Le 6 variants restano (i DATI cambiano), l'anatomia si unifica.
- **DoD**: mettendo 6 card di tipi diversi in griglia sembrano UNA famiglia.

### V4 · Wizard unificati ✅ (fatto 5/7/2026 sera — PIANO VETRINE COMPLETO V1-V4)
- [ ] **Spina dorsale comune**: tab 1 sempre "Cosa offri" (nome, categoria,
      descrizione, foto, prezzo base), tab centrali specifici per tipo
      (INVARIATI nella sostanza), tab finale sempre "Pubblica" con lo STESSO
      riepilogo + distribuzione store + gate store-first
- [ ] **Categoria coerente per tipo**: ritiri = tassonomia (fatto); servizi/
      fisici/digitali = dropdown con categorie semplici per-tipo (es. servizi:
      trattamenti/consulenze/lezioni) usate come SOTTO-FILTRO nella pagina
      categoria dello store — o NIENTE campo dove non serve (mai testo libero)
- [ ] **Gate store-first su TUTTI i tipi** (oggi solo ritiri): stesso 409 +
      stesso banner
- [ ] Naming tab uniforme (via i18n, zero refactor di logica)
- **DoD**: l'operatore che sa creare un ritiro sa creare qualsiasi cosa;
  nessun campo che non alimenta niente.

### Rifiniture directory (dentro V3, 0,5 gg)
- [ ] Tap sulla categoria della card → filtra la directory
- [ ] Search anche nella barra sticky (non solo hero)

Ordine: V1 → V2 → V3 → V4 ≈ **4,5 giorni**. Ogni fase mergiabile da sola,
verificata in browser sul funnel acquisto completo (il checkout NON si tocca).

## 4 · Cosa NON si tocca
- Checkout/carrello/pagamenti (consolidati e testati con soldi veri)
- La logica del menu automatico (funziona: si arricchisce, non si riscrive)
- Gli step centrali dei wizard (la sostanza per-tipo è giusta)
- I template/override custom dei merchant (Phase 8.2 custom links restano)
