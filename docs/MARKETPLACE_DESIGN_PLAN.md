# Marketplace ritiri — refinement olistico del design (piano PM, 8 luglio 2026)

> **ESITO (8/7/2026)** — M1 ✅ M2 ✅ M3 ✅ M4 ✅ M5 ✅ M6 ✅ su main, suite
> 4143 verdi, verifiche browser (desktop+mobile 390px) su ogni fase.
> **M0 APERTO**: nome piattaforma da decidere (founder) — placeholder in
> frontend/src/config/brand.js, UNA riga da cambiare. Rimandati (per
> scelta): recensioni vere (post-lancio), wishlist, "In evidenza"
> editoriale (serve flag admin), scroll-spy sezioni landing.

Lente: product manager di un marketplace di prenotazioni. Obiettivo
founder: "piattaforma di riferimento per prenotare ritiri olistici in
tutto il mondo — moderna, professionale, user-friendly, design
accattivante e figo".

## La diagnosi (perché "la navigazione non è snella")

Il sintomo che il founder ha visto è IL problema strutturale: **il
marketplace non ha un guscio**. Ogni superficie pubblica ha una testata
diversa o nessuna:

| Pagina | Testata attuale | Cosa si rompe |
|---|---|---|
| /ritiri (directory) | hero proprio, lingua nell'hero | ok da sola, ma è un vicolo cieco di ritorno |
| /e/… (landing ritiro) | header dell'OPERATORE (store) | chi arriva dalla directory perde il marketplace: per tornare deve usare il back del browser o un link nel footer |
| /o/… (profilo operatore) | barra "← Tutti i ritiri" improvvisata | funziona ma sembra una toppa, non un prodotto |
| /account (Passaporto) | guscio proprio | scollegato dal resto |
| checkout | flusso store | corretto che sia asciutto, ma senza fil rouge visivo |

I grandi booking (Airbnb, Booking) risolvono con UNA regola: **header
persistente del marketplace su ogni pagina del funnel di scoperta**,
che scompare (si riduce) solo nel checkout. Noi abbiamo già il pattern
gemello sul lato store ("dentro lo store non si esce mai") — va
replicato sul lato marketplace: **dentro il marketplace non ti perdi
mai**.

Contesto doppio già risolto altrove e da riusare: la landing serve DUE
mondi (directory e store, via `?store=1`). Regola proposta: guscio
STORE con `?store=1`, guscio MARKETPLACE in tutti gli altri casi
(arrivo da directory, link condiviso, Google) — l'operatore resta ben
visibile nella pagina, ma la navigazione è del marketplace.

## M0 · Fondamenta di brand (DECISIONE FOUNDER, 0 gg di codice)

Un marketplace "di riferimento" ha un nome e un volto. Oggi il brand è
"Retreat App" (placeholder dev).
- [ ] **Nome definitivo** della piattaforma (decisione founder — blocca
      logo, dominio, header, email, SEO)
- [ ] Logo/wordmark semplice (anche solo tipografico + un glifo foglia/
      cerchio zen nella palette Salvia&Terracotta)
- [ ] Micro-manifesto visivo (1 pagina): toni foto (luce naturale,
      pietra, verde), voce ("calma, concreta, zero cliché new-age"),
      uso dei colori (Salvia = struttura, Terracotta = azione/CTA)
- **DoD**: nome scelto; il resto del piano lo indossa.

## M1 · Il guscio marketplace (1 gg) — la mossa che ripara la navigazione

`MarketplaceShell`: header + footer comuni per TUTTE le pagine lato
viaggiatore.
- [ ] **Header sticky**: [logo → /ritiri] · barra ricerca compatta
      ("Dove? · Quando?" che riapre i filtri della directory) ·
      selettore lingua (spostato qui dall'hero) · "I miei viaggi"
      (→ /account, il Passaporto) · CTA discreta "Sei un organizzatore?"
      (→ /inizia — acquisizione lato offerta, gratis)
- [ ] Applicato a: /ritiri, landing ritiro (senza `?store=1`), /o/…,
      /account e pagine magic-link
- [ ] Nel checkout: header ridotto (solo logo + lucchetto) — focus
      totale sulla conversione
- [ ] **Footer marketplace**: categorie top, destinazioni top (SEO
      interno), Chi siamo/Privacy/Termini, selettore lingua, "Per gli
      organizzatori"
- [ ] La barra "← Tutti i ritiri" su /o/… SPARISCE (assorbita dal logo/
      breadcrumb del guscio)
- **DoD**: da qualsiasi pagina pubblica torno alla directory in UN tap;
  il back del browser non è mai l'unica via.

## M2 · Landing ritiro: da scheda a vetrina (1,5 gg) — dove si decide l'acquisto

È la pagina più importante del funnel. Riferimento: Airbnb listing.
- [ ] **Breadcrumb**: Ritiri › {Categoria} › {titolo} (con link filtranti)
- [ ] **Galleria hero a griglia** (1 grande + 4 piccole, "Mostra tutte
      le foto" → lightbox) al posto della singola cover — le foto
      vendono i ritiri
- [ ] **Colonna prenotazione sticky** (desktop): prezzo "da", date,
      posti rimasti, caparra evidente, CTA Terracotta — sempre visibile
      allo scroll; su mobile bottom-bar fissa (già c'è? verificare)
- [ ] Sezioni ancorate con nav interna (Programma · Incluso · Dove ·
      FAQ · Organizzatore) — scroll-spy leggero
- [ ] Blocco fiducia: caparra/rimborso spiegati con icone, "Prenoti con
      caparra, saldo dopo" come promessa di piattaforma
- [ ] Condividi (nativo/copy-link) — i ritiri si prenotano in gruppo
- **DoD**: sopra la piega vedo foto grandi + prezzo + CTA; prenoto
  senza mai scrollare a vuoto.

## M3 · Profilo operatore = pagina di fiducia (0,5 gg)

- [ ] Nel guscio marketplace (M1), breadcrumb Ritiri › {operatore}
- [ ] Card identità arricchita: badge "Su {piattaforma} dal {anno}",
      contatore ritiri organizzati, link store ("Visita il negozio")
      ben distinto dal funnel ritiri
- [ ] Griglia ritiri con le STESSE card della directory (riuso, zero
      nuovi pattern)
- [ ] Predisposizione (solo layout, niente dati finti): slot recensioni
      future — la fiducia è la valuta dei marketplace
- **DoD**: il profilo risponde a "posso fidarmi?" in 5 secondi.

## M4 · Directory: da elenco a destinazione (1 gg)

- [ ] **Hero evocativo**: foto/gradiente di atmosfera (pietra+ulivi),
      titolo grande display, la barra Dove?/Quando?/Cosa? come UNICO
      elemento centrale (pattern Airbnb search-first); categorie come
      riga di icone circolari SOTTO l'hero (stile Explore)
- [ ] **Card v2**: foto più alta (4:3), titolo più forte, riga meta
      unica (data · luogo · distanza), prezzo "da" allineato a destra,
      badge caparra più discreto; hover lift già ok
- [ ] Riga "In evidenza questo mese" (curatela manuale semplice:
      flag admin) sopra la griglia — dà vita editoriale alla pagina
- [ ] Empty state con arte (illustrazione zen) e azioni utili
- [ ] Skeleton coerenti ovunque (card, mappa)
- **DoD**: la home /ritiri regge il confronto visivo con un marketplace
  vero; un utente nuovo capisce cosa può fare in 3 secondi.

## M5 · Design system marketplace (0,5 gg, trasversale)

- [ ] Tipografia: display serif/humanist per i titoli pubblici (calore
      olistico), sans attuale per UI — 2 font, non di più
- [ ] Scala spaziature e radius unificata (audit rapido delle 5 pagine)
- [ ] Micro-interazioni: transizioni 150-200ms su hover/focus, skeleton
      pulse, cuori/badge con spring leggero — MAI animazioni > 300ms
- [ ] Accessibilità: contrasti AA sulla palette, focus ring visibili
- **DoD**: le 5 superfici sembrano UN prodotto.

## M6 · Mobile-first + performance (0,5 gg)

- [ ] Pass mobile su directory/landing/profilo (il traffico ritiri è
      70%+ mobile): filtri in bottom-sheet, galleria swipe, CTA fissa
- [ ] Immagini: lazy + srcset dove mancano; LCP della landing < 2,5s
- **DoD**: giro completo scoperta→prenotazione col pollice, fluido.

## Cosa NON facciamo (scelte esplicite)
- Recensioni/rating VERI: dopo il lancio (servono prenotazioni reali);
  ora solo lo slot visivo (M3).
- App nativa, salvataggi/wishlist persistenti: post-lancio.
- Rebrand colori: la palette Salvia&Terracotta resta (è giusta);
  cambiano gerarchia, foto e tipografia.

## Metriche per giudicare il lavoro (post-deploy)
- % utenti che dalla landing tornano alla directory (oggi ~impossibile
  senza back) — atteso: da ~0 a >20%
- Scroll-depth landing e click su CTA prenota
- Pagine/sessione sul lato marketplace

## Ordine e stima
M0 (decisione nome, subito) → M1 (guscio, ripara la navigazione) →
M2 (landing) → M4 (directory) → M3 (profilo) → M5+M6 (rifiniture)
≈ **5 giorni** di lavoro. M1 da solo risolve il dolore segnalato:
proposta = partire da lì appena il founder conferma il piano e il nome
(o un placeholder migliore di "Retreat App").
