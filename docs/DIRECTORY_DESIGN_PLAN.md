# Directory pubblica — consolidamento design, SEO, multilingua (piano, 5 luglio 2026)

Richiesta founder: directory /ritiri bella e moderna con navigazione unica;
pagina ritiro → profilo operatore → e-commerce dell'operatore (ecosistema
collegato); SEO automatico best-practice su directory E store; refinement
e-commerce senza rompere nulla; multilingua della directory CON traduzione
automatica dei contenuti degli operatori (fattibilità). **Solo piano.**

## 0 · Investigazione olistica — lo stato reale (verificato nel codice)

| Area | Stato | Gap |
|---|---|---|
| Directory /ritiri | Funziona: griglia card, filtri categoria/regione/mese, pagine SEO /ritiri/:cat/:reg, useSeoMeta | Design "v1 funzionale": header piatto, filtri = 3 select nudi, card basiche, niente hero/categorie visuali/skeleton |
| Landing ritiro → profilo operatore | **NESSUN LINK** — il nome operatore sulla card non è cliccabile, la landing non menziona il profilo | L'ecosistema esiste ma è scollegato |
| Profilo operatore /o/:slug → store | **NESSUN LINK** — il profilo mostra bio + prossimi ritiri, mai lo store | Idem |
| Store → profilo/directory | Nessun link inverso | Idem |
| SEO | useSeoMeta (title/description/OG/canonical) sulle pagine pubbliche | **ZERO**: sitemap.xml, robots.txt, JSON-LD/schema.org, hreflang, OG image di default. E CRA = SPA: i crawler "poveri" (Bing, social) vedono HTML vuoto — Google ok, il resto no |
| E-commerce design | Tema token (D1) già applicato; card store decenti | Coerenza da rifinire: header store anonimo, niente breadcrumb, footer povero, nessun aggancio all'ecosistema |
| Multilingua | UI in 4 lingue (it/en/de/fr). **Contenuti operatore in lingua unica** (name, description, long_description markdown, programma, FAQ) | Da costruire; LLM client già in casa (claude_client.py con budget guard + circuit breaker + costi) |

## 1 · Principio architetturale: l'ecosistema a tre livelli

```
DIRECTORY /ritiri  ←→  LANDING ritiro  ←→  PROFILO operatore /o/:slug  ←→  STORE /s/:slug
   (domanda)            (conversione)         (fiducia)                     (catalogo completo)
```

Ogni superficie linka le adiacenti nei DUE sensi. Il valore per l'utente:
scopro un ritiro → mi fido dell'organizzatore (profilo) → scopro tutto ciò
che offre (store) → torno alla directory per confrontare. Il valore SEO:
internal linking = la struttura che Google premia di più, gratis.

## 2 · Le fasi

### F1 · Directory /ritiri — redesign (2 gg)
Obiettivo: da "lista funzionale" a "posto dove è bello cercare il prossimo ritiro".
- [ ] **Hero** con la palette olistica (gradient salvia), payoff, search bar
      prominente (cerca per titolo/luogo — client-side sul dataset già caricato)
- [ ] **Categorie visuali**: chip/card orizzontali con icona per Yoga /
      Meditazione / Detox / Sound / … (dalle categorie reali del backend,
      mai hardcoded) — un tap filtra
- [ ] **Card ritiro raffinate**: foto full-bleed, data in badge sovrapposto,
      operatore cliccabile → /o/:slug, prezzo "da", badge caparra, "ultimi N
      posti" (già c'è), hover lift
- [ ] **Filtri sticky** in una barra compatta (categoria · regione · mese ·
      reset) che segue lo scroll; risultati con conteggio
- [ ] **Skeleton loading** + empty state caldo ("Nessun ritiro qui, prova
      ad allargare la ricerca") + **pagine categoria×regione** già indicizzabili
      arricchite con un intro testuale (SEO: contenuto unico per pagina)
- [ ] Mobile-first: filtri in bottom-sheet, card a colonna singola
- **DoD**: la directory regge il confronto con i portali verticali moderni;
  Lighthouse mobile ≥ 90 performance/accessibility.

### F2 · Ecosistema collegato (1 gg)
- [ ] Landing ritiro: blocco "Organizzato da" con avatar/logo, bio breve,
      link a /o/:slug ("Vedi il profilo e gli altri ritiri")
- [ ] Profilo operatore: sezione "Il negozio di {nome}" → /s/:slug (visibile
      solo se lo store è pubblicato); social/contatti se presenti; ritiri
      passati come social proof ("12 ritiri organizzati")
- [ ] Store: header con link "Profilo organizzatore" + footer con "Trova
      altri ritiri su {piattaforma}" → /ritiri (regola: MAI link alla
      directory dentro il funnel di checkout — solo header/footer browsing)
- [ ] Card directory: nome operatore → /o/:slug (stop propagation sul click card)
- **DoD**: da ogni superficie raggiungo le adiacenti in 1 click, nei due sensi.

### F3 · SEO automatico (2 gg) — "automatico" = derivato dai dati, zero lavoro operatore
- [ ] **JSON-LD** generato dai dati reali: `Event` (nome, date, luogo,
      offerta/prezzo, disponibilità) sulle landing; `Organization` sul
      profilo; `Product` sulle schede store; `BreadcrumbList` ovunque;
      `ItemList` sulla directory
- [ ] **sitemap.xml dinamica** (endpoint backend, cache 1h): directory,
      pagine categoria×regione, tutte le landing PUBBLICATE e future,
      profili operatore, store e prodotti pubblicati. lastmod da updated_at
- [ ] **robots.txt**: allow pubblico, disallow /account, /admin, /pay,
      /t/, /b/ (token!), checkout; link alla sitemap
- [ ] **OG image**: default brand per directory/profili; foto cover del
      ritiro sulle landing (già c'è il campo — va nel meta)
- [ ] **Prerender per i bot** (la decisione infra): CRA è SPA — Google
      renderizza JS, Bing/social/LLM-crawler NO. Soluzione pragmatica al
      lancio: middleware prerender SOLO per user-agent bot (servizio tipo
      prerender.io oppure rendertron self-hosted sul VPS di Fase 6) — zero
      cambi al codice app. SSR/Next è la soluzione "vera" ma è una
      MIGRAZIONE: non ora, valutare post-lancio se il SEO diventa il canale
      primario. → decisione registrata, si collega a Fase 6.3
- [ ] Canonical + hreflang (si aggancia a F5)
- **DoD**: Rich Results Test verde su landing/profilo/store; sitemap valida
  in Search Console; share su WhatsApp/Facebook mostra foto+titolo giusti.

### F4 · Refinement e-commerce (1 gg — senza rompere nulla)
Regola: SOLO additivo/estetico, zero cambi a checkout/carrello/pagamenti
(appena consolidati e testati con soldi veri).
- [ ] Header store: logo/nome più curati, link profilo, lingua
- [ ] Breadcrumb (Store → Categoria → Prodotto) — utile anche per JSON-LD
- [ ] Card prodotto: stessa qualità delle card directory (coerenza F1)
- [ ] Footer store: profilo operatore, privacy/termini, "powered by" con
      link directory
- [ ] Sweep spaziature/radius/empty states col tema token
- **DoD**: browser sweep completo del funnel acquisto INVARIATO (stessi
  test del fix caparra); nessun file di checkout logic toccato.

### F5 · Multilingua directory + traduzione automatica contenuti (2-3 gg)
**Verdetto fattibilità: SÌ, ed economico.** Il client LLM è già nel codebase
(claude_client.py: budget guard, circuit breaker, cost tracking). Architettura:

```
publish/update ritiro → job traduzione (scheduler esistente, best-effort)
  → collection content_translations:
     { entity_type, entity_id, lang, fields{name, description,
       long_description, program[], faq[]}, source_hash, translated_at }
  → API pubblica: ?lang=en → merge traduzione se esiste, fallback originale
```

- [ ] **Trigger**: alla pubblicazione + su modifica (hash dei campi sorgente:
      se il contenuto cambia, la traduzione si invalida e si rigenera —
      MAI traduzioni stantie). Job async sullo scheduler esistente: la
      pubblicazione non aspetta la traduzione
- [ ] **Lingue**: en/de/fr (le stesse della UI). Un ritiro medio
      (~800 parole × 3 lingue) ≈ **1-2 centesimi** con un modello piccolo —
      trascurabile anche su migliaia di ritiri; budget guard già esistente
      come rete di sicurezza
- [ ] **Qualità e onestà**: prompt di traduzione conservativo (mai inventare
      contenuti, preservare markdown/struttura); badge "Tradotto
      automaticamente" + link "vedi originale"; l'operatore Pro potrà in
      futuro modificare le traduzioni (post-lancio)
- [ ] **Cosa NON si traduce**: prezzi, date, nomi propri, contenuti store
      generici (fase 2 — si parte SOLO dai ritiri in directory)
- [ ] **SEO multilingua**: URL con prefisso (/en/ritiri → /en/retreats?
      no: stesso path + ?lang oppure /en/ prefix — DECISIONE: prefisso
      /en/ /de/ /fr/ solo sulle superfici directory/landing, hreflang
      reciproci, x-default italiano). Sitemap con alternates
- [ ] UI directory: switcher lingua già esistente nello storefront → si
      estende alla directory
- **DoD**: /ritiri in 4 lingue con contenuti operatore tradotti, hreflang
  validi, badge trasparenza, costo per ritiro tracciato nel cost calculator.

## 3 · Ordine, stime, dipendenze
F1 (2gg) → F2 (1gg) → F3 (2gg) → F4 (1gg) → F5 (2-3gg) ≈ **8-9 giorni**.
- F1/F2/F4 solo frontend: zero rischio backend.
- F3 prerender si decide/attiva con l'infra di Fase 6.3 (stesso VPS).
- F5 tocca backend (collection nuova + job) ma è ISOLATO (modulo nuovo,
  pattern Passaporto: feature flag, best-effort, mai bloccare publish).

## 4 · Cosa NON facciamo
- Nessuna migrazione SSR/Next ora (prerender-for-bots al lancio; SSR è
  un progetto a sé, si valuta coi dati Search Console)
- Nessun cambio a checkout/carrello/pagamenti (F4 è estetica)
- Nessuna traduzione umana/di terze parti (LLM in casa + badge trasparenza)
- Niente recensioni/rating in questo giro (feature a sé, post-lancio)
