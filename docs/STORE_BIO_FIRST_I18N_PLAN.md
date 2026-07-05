# Store bio-first + navigazione directory + multilingua VERO (piano, 6 luglio 2026)

Tre richieste founder + la domanda chiave sui costi di traduzione.

## T1 · Store: la bio come PRIMA pagina (0,25 gg)
Oggi /s/:slug apre la home V1 (hero + prossimi ritiri). Decisione founder:
la prima pagina è la **pagina bio** (chi siamo).
- [ ] /s/:slug (root) rende il contenuto Chi-siamo (cover, bio completa,
      social, contatti, prossimi ritiri) — è già costruito (StoreAbout, S3)
- [ ] La nav categoria resta in alto: dal primo secondo l'utente può
      andare su Ritiri/Prodotti; "Chi siamo" in nav → root (attivo quando ci sei)
- [ ] /s/:slug/chi-siamo resta come alias (link già in giro)
- [ ] Il redirect per store mono-categoria piccoli SPARISCE: la bio-first
      vale per tutti (identità prima del catalogo — è la scelta di brand)
- **DoD**: atterri sullo store → vedi chi è l'operatore; un tap → prodotti.

## T2 · Directory → bio: la via del ritorno (0,25 gg)
/o/:slug non ha modo di tornare alla directory (il visitatore marketplace
resta bloccato).
- [ ] Barra sticky in alto su /o/:slug: **"← Tutti i ritiri"** → /ritiri,
      ben visibile, sempre presente allo scroll
- [ ] Stessa barra sulla landing ritiro quando si arriva dalla directory?
      NO per ora — la landing ha già il footer con "Scopri altri ritiri";
      il funnel di prenotazione non si appesantisce
- **DoD**: da /o/:slug torni a /ritiri con un tap, da qualsiasi punto.

## T3 · Multilingua directory: perché "non funziona" e il fix (0,75 gg)
**Diagnosi (verificata):** lo switch lingua funziona, ma traduce solo le
chiavi aggiunte di recente. Le chiavi BASE della directory (titolo,
sottotitolo, "da 800 €", "Prenoti con caparra", filtri…) **esistono solo
in italiano** — en/de/fr non le hanno mai avute. E le label categoria
(Yoga, Detox & Digiuno…) arrivano dal backend hardcoded in italiano.
Quindi: UI mezza italiana in ogni lingua → percezione "rotto". Il fix è
TUTTO statico e GRATIS (zero LLM):
- [ ] **Audit automatico**: script che confronta le chiavi it vs en/de/fr
      per landings + storefront e elenca i buchi (una volta trovati, mai più)
- [ ] Colmare TUTTE le chiavi mancanti in en/de/fr: directory (calendar.*),
      landing (event.*), operatore (operator.*), checkout (storefront:*)
- [ ] **Label categorie via i18n frontend**: chiave per slug
      (categories.yoga → "Yoga"/"Йога"…) in 4 lingue, fallback alla label
      backend — le 9 categorie sono statiche, si traducono UNA volta a mano
- [ ] Date: già localizzate (fmtDates usa la lingua attiva) — verificare
- [ ] Verifica browser nelle 4 lingue: directory → landing → checkout
- **DoD**: switch su EN/DE/FR → TUTTA la UI cambia lingua (i contenuti
  operatore seguono la decisione T4).

## T4 · Traduzione CONTENUTI: come funziona e quanto costa (decisione founder)

**Il meccanismo, spiegato semplice:**
1. L'operatore scrive i contenuti UNA volta, in italiano. Stop.
2. Un job orario passa i testi all'API Claude che li traduce in en/de/fr.
3. La traduzione viene SALVATA per sempre nel DB. Si ritraduce SOLO se
   l'operatore modifica il testo (hash del contenuto).
4. Il visitatore straniero riceve la traduzione dal NOSTRO database:
   **le visite non costano nulla**, mai.

**Quanto costa:** solo il passaggio 2, una tantum per ritiro:
- ~**1-2 centesimi di euro** per ritiro per TUTTE e tre le lingue
- 100 ritiri = ~1-2 €. 1.000 ritiri = ~15 €. Una volta sola.
- c'è già un budget guard nel codice che impedisce sforamenti

**Stato attuale: costo ZERO.** La chiave API non è configurata → il job
non parte → non si spende nulla. I contenuti restano in italiano con
fallback pulito (la UI intorno è tradotta da T3).

**Le opzioni:**
- **A (raccomandata):** T3 subito (UI 4 lingue, GRATIS); pipeline
  contenuti SPENTA al lancio. Si accende quando/se vorrai, mettendo la
  chiave: a quel punto ~1-2 cent/ritiro. "Oneroso" non è la parola giusta
  per questi numeri, ma la scelta resta tua e reversibile.
- **B:** annullare del tutto il multilingua contenuti: si rimuove il
  badge "tradotto automaticamente" e la pipeline resta come codice
  dormiente. La directory resta navigabile in 4 lingue (T3), i testi dei
  ritiri in italiano.

In entrambi i casi NON si paga nulla finché non decidi diversamente.

## Ordine e stima
T3 (il percepito "rotto") → T1 → T2 ≈ **1,5 giorni**. T4 = solo decisione.
