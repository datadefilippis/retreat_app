# SEO MASTER PLAN — Aurya come macchina di traffico organico

> 6/7/2026 — lente: web designer + product owner + SEO expert.
> Obiettivo founder: «chiunque pubblichi sulla piattaforma, e la
> piattaforma stessa, super-indicizzata in maniera scalabile».
> Ogni voce della diagnosi è verificata nel codice, non a memoria.

---

## DIAGNOSI — dove siamo davvero

**Cosa c'è già (F3, buone fondamenta):**
- sitemap.xml dinamica (ritiri futuri, coppie categoria×regione con
  contenuto, profili /o/, store /s/), cache 1h — `routers/seo.py`
- robots.txt corretto (aree private escluse)
- `useSeoMeta` (title/description/OG/canonical/JSON-LD) su **3 pagine**:
  directory /ritiri, landing ritiro /e/, profilo operatore /o/
- JSON-LD: Event, Organization, ItemList, BreadcrumbList
- slug puliti per landing e store

**I 7 buchi, in ordine di gravità:**

| # | Problema | Impatto |
|---|---|---|
| 1 | **La root `/` è la LOGIN degli operatori** (App.js:246) | La pagina col 100% della link equity del dominio è una form di login. La home page di un marketplace È la directory. |
| 2 | **SPA client-side pura** (CRA): title/meta/JSON-LD iniettati via JS dopo il render | Google ce la fa (con ritardo di rendering budget); Bing/DuckDuck/social scraper (WhatsApp, iMessage, LinkedIn) vedono UNA pagina vuota con title generico per TUTTI gli URL. Le condivisioni — il canale n°1 dei ritiri — non hanno anteprima. |
| 3 | **4 tipi di prodotto su 5 invisibili**: le landing /p (servizi), /ph (fisici), /dg (digitali), /co (corsi), /r (prenotazioni) NON hanno né meta né JSON-LD né presenza in sitemap | Un massaggiatore che pubblica il suo servizio non esiste su Google. Contraddice la promessa "chiunque pubblica è indicizzato". |
| 4 | **Niente aggregatore operatori**: i profili /o/ esistono ma nessuna pagina li elenca | Zero pagine per query "centri yoga Toscana", "operatori olistici"; i profili sono foglie orfane con link interni deboli. |
| 5 | **Niente hreflang / segnali multilingua**: 4 lingue UI + contenuti tradotti, ma Google non sa che esistono | Il traffico DE/EN/FR (il mercato vero dei ritiri in Italia!) atterra sulle pagine italiane o non le trova affatto. |
| 6 | **Store /s/ senza SEO**: StorefrontPage e chi-siamo senza meta/JSON-LD (LocalBusiness); og:image mai di default | La vetrina dell'operatore — il suo "sito" — non è ottimizzata; il co-marketing operatore→piattaforma si perde. |
| 7 | Dettagli: sitemap senza `hreflang` e senza sitemap-index (tetto 50k url), robots con Sitemap URL relativo (deve essere assoluto), niente IndexNow/ping, niente FAQPage schema (le FAQ dei ritiri ci sono già!), niente noindex sugli stati vuoti | Attriti che si pagano alla scala. |

---

## LA STRATEGIA IN UNA RIGA

Tre motori di pagine indicizzabili che crescono DA SOLE coi dati
(prodotti, operatori, destinazioni), serviti con HTML già completo di
meta al primo byte, collegati tra loro da una gerarchia hub→foglia.

```
                    aurya.life (home = directory)
        ┌──────────────┼───────────────┬──────────────┐
   /ritiri        /esperienze      /operatori      /destinazioni
   (eventi)       (servizi/corsi)  (aggregatore    (luoghi con copy)
   /ritiri/{cat}                    NUOVO)
   /ritiri/{cat}/{reg}             /operatori/{cat}
        │                               │
   /e/{org}/{slug}   /p /co /r     /o/{org_slug} ←→ /s/{org_slug}
   (landing evento)  (landing       (profilo)        (store+prodotti)
                      prodotto)
```

---

## S0 · Home & rendering — il moltiplicatore (2 gg) ⚠️ PRIMA DI TUTTO

**S0.1 — La home è il marketplace.**
- `/` → directory pubblica (la RetreatsCalendarPage, ripensata come
  home: hero brand + ricerca + categorie + in evidenza + operatori top
  + blocco "Sei un organizzatore?").
- Login operatori → `/accedi-operatore` (o resta su /login), redirect
  301 dal vecchio path; utenti loggati che aprono / vedono comunque la
  home pubblica (il back-office si raggiunge dal menu).
- `/ritiri` resta come hub eventi (canonical proprio, non duplicato
  della home: la home mostra il MIX, /ritiri solo eventi).

**S0.2 — Meta server-side (SEO shell).**
La mossa pragmatica per lo stack CRA, senza migrare framework:
- endpoint FastAPI che serve l'`index.html` della build con
  **iniezione server-side** di title, meta description, OG completi
  (incl. og:image), canonical, hreflang e JSON-LD per le route
  pubbliche (`/`, `/ritiri*`, `/esperienze*`, `/operatori*`,
  `/destinazioni*`, `/e/`, `/p/`, `/ph/`, `/dg/`, `/co/`, `/r/`,
  `/o/`, `/s/`, legali). Stessi dati delle API già esistenti; il JS
  poi idrata come oggi (useSeoMeta resta per la navigazione SPA).
- Caddy/nginx: route pubbliche → questo endpoint; asset statici →
  build. Cache 5-15 min per URL.
- Risultato: ogni bot e ogni scraper social vede l'HTML giusto al
  primo byte. Niente cloaking (stesso HTML per tutti).
- **Post-lancio** (annotato, non ora): se il progetto cresce,
  migrazione a Next.js/Remix per SSR completo dei contenuti.
- **DoD**: `curl -A WhatsApp https://aurya.life/e/...` mostra
  title/og:image del ritiro; la home risponde con l'HTML della
  directory.

## S1 · Ogni prodotto indicizzabile (2 gg)

Parità SEO per TUTTI i tipi (il punto 3 della diagnosi):
- `useSeoMeta` + JSON-LD su ProductLandingPage (**Service**),
  PhysicalLandingPage (**Product+Offer**), DigitalLandingPage
  (**Product+Offer**), CourseLandingPage (**Course**),
  ReservationLandingPage (**Product+Offer** con disponibilità).
- EventLandingPage: aggiungere **FAQPage** (le FAQ ci sono già nei
  dati!) e **offers** dentro Event (prezzo "da", priceCurrency,
  availability da posti rimasti) → rich results con prezzo.
- Breadcrumb JSON-LD su tutte le landing.
- og:image: cover del prodotto → logo store → logo Aurya (fallback
  SEMPRE presente).
- Canonical: la landing è UNA (`/e/org/slug` senza query); `?store=1`
  e `?lang=` puntano il canonical alla versione pulita.
- noindex su: risultati vuoti, pagine di stato (checkout success,
  magic link), /account.
- **DoD**: Rich Results Test di Google verde su un URL per TIPO.

## S2 · Aggregatore operatori + directory delle destinazioni (2 gg)

**`/operatori` — il secondo pilastro** (richiesta founder):
- indice pubblico di tutti gli operatori con store/profilo pubblicato:
  card (logo, nome, luogo, categorie, n° esperienze attive), filtri
  per categoria e luogo, ricerca.
- pagine programmatiche `/operatori/{categoria}` (es. /operatori/yoga)
  SOLO se ≥1 operatore reale (regola anti-thin-content già usata per
  categoria×regione).
- API: `GET /public/operators` (org con store pubblicato + conteggi).
  JSON-LD ItemList di Organization.
- Il profilo /o/ si arricchisce: link "in soli 2 click" verso tutti i
  suoi prodotti (non solo ritiri), breadcrumb Operatori › {nome}.

**`/destinazioni` — il terzo pilastro (query "ritiri + luogo"):**
- pagine `/destinazioni/{luogo}` generate dai dati geo REALI (regioni/
  città con ≥1 ritiro futuro o esperienza attiva): H1 "Ritiri e
  esperienze a {luogo}", mappa, elenco, operatori della zona, copy
  template + campo copy curabile a mano (admin) per le destinazioni top.
- Le query "yoga retreat Tuscany / Toskana / Toscane" sono LA domanda
  organica del settore: queste pagine sono fatte per intercettarla
  nelle 4 lingue.

**`/esperienze` — hub dei non-eventi:**
- aggregatore di servizi/corsi/prenotazioni attivi (i fisici/digitali
  restano indicizzati a livello di landing e store: aggregarli
  cross-operatore è una scelta commerce da NON fare ora — coerente con
  l'audit di giugno "commerce congelato").

## S3 · Sitemap 2.0 + segnali di scoperta (1 gg)

- **Sitemap index** → sotto-sitemap: `sitemap-core.xml` (home, hub,
  destinazioni, legali), `sitemap-retreats.xml`, `sitemap-products.xml`
  (TUTTE le landing prodotto pubblicate, tutti i tipi),
  `sitemap-operators.xml` (/o/ + /s/ + chi-siamo). Chunking a 45k
  url/file (scala domani senza toccare nulla).
- `xhtml:link rel="alternate" hreflang` DENTRO le sitemap per le
  lingue davvero disponibili per quell'URL (dal multilingua manuale:
  lingue accettate = description tradotta) + x-default.
- lastmod reali ovunque; robots.txt con URL sitemap ASSOLUTO.
- **IndexNow** (Bing/Seznam/Yandex — gratis) + ping sitemap a Google
  al publish/update di un prodotto: indicizzazione in ore, non giorni.
- **DoD**: Search Console e Bing Webmaster senza errori di copertura.

## S4 · Multilingua internazionale (1 gg)

- hreflang nelle `<head>` server-side (S0.2) e nelle sitemap (S3):
  4 lingue con x-default=it — SOLO dove la traduzione esiste.
- URL: restano `?lang=` (pragmatico per ora); i canonical per lingua
  puntano a `?lang=xx` stesso (self-canonical per variante) — regola
  standard hreflang+canonical. Path `/en/...` = refactoring post-lancio
  se i dati Search Console lo giustificano.
- title/description delle pagine hub tradotti (i file i18n ci sono già).

## S5 · Internal linking + contenuto programmatico (1 gg)

- Landing ritiro: blocco "Altri ritiri di {categoria} in {regione}" +
  "Altre esperienze di {operatore}" (link a 3-6 foglie sorelle).
- Footer marketplace: destinazioni top e categorie top DINAMICHE (dai
  dati, non hardcoded — oggi 3 link fissi).
- Home: sezioni che linkano i 3 hub + destinazioni top.
- Copy template per pagine categoria (2-3 frasi vere per categoria,
  scritte una volta, 4 lingue) — le pagine indice non devono essere
  liste nude.
- Regola globale anti-thin-content: indice con 0 risultati = noindex.

## S6 · Performance / Core Web Vitals (1 gg)

- Immagini: conversione WebP + resize al momento dell'UPLOAD (pipeline
  object_storage — una volta per sempre, non on-the-fly), `srcset` e
  `loading=lazy` dove manca, `fetchpriority=high` sull'immagine hero
  della landing.
- Font: `display=swap` (già), preload di Cinzel woff2, subsetting.
- Code splitting: `React.lazy` per il back-office admin (il bundle
  admin non deve pesare sul First Load delle pagine pubbliche — oggi
  App.js importa TUTTO staticamente).
- Cache: asset immutabili con hash (già CRA), uploads con max-age
  lungo (fatto in R3), HTML pubblico no-cache/short-cache.
- **DoD**: Lighthouse mobile ≥90 performance sulla landing ritiro e
  sulla home; LCP < 2,5s su 4G simulato.

## S7 · SEO dello store (il "sito" dell'operatore) (1 gg)

- StorefrontPage e /s/{slug}/chi-siamo: useSeoMeta + **LocalBusiness**
  (nome, logo, indirizzo se presente, sameAs dai social del profilo) +
  ItemList del catalogo.
- title pattern: `{Store} — {categoria principale} | Aurya`.
- Le pagine categoria dello store (/s/slug/c/{cat}) con canonical e
  meta; in sitemap-operators.
- Ogni pagina store linka il profilo directory /o/ e viceversa (equity
  circola tra i due volti dell'operatore).
- Nota post-lancio: custom domain per store (CNAME operatore →
  aurya) = feature premium futura, fuori scope.

## S8 · Misura, automazione, guardie (0,5 gg + operativo)

- 【founder】 Google Search Console + Bing Webmaster Tools (verifica
  dominio via DNS Cloudflare), submit sitemap index.
- Guard-test pytest sulle invarianti SEO (stile test esistenti):
  ogni route landing nel router pubblico ha meta server-side; la
  sitemap contiene ogni landing pubblicata (test con seed); nessuna
  pagina privata nella sitemap; canonical senza query.
- docs/SEO.md: le regole (title pattern per tipo, quando noindex,
  come si aggiunge un tipo di prodotto nuovo alla pipeline SEO).
- KPI post-lancio: copertura indicizzazione, click/impression per hub,
  CTR delle landing (rich results), tempo publish→indexed (IndexNow).

---

## ORDINE E STIME

| Fase | Giorni | Dipendenze |
|---|---|---|
| S0 home + SEO shell | 2 | — (il moltiplicatore: farla PRIMA) |
| S1 parità prodotti | 2 | S0.2 per l'iniezione server |
| S2 aggregatori (operatori/destinazioni/esperienze) | 2 | S0.1 |
| S3 sitemap 2.0 + IndexNow | 1 | S1, S2 (nuove url) |
| S4 hreflang | 1 | S0.2, S3 |
| S5 linking interno + copy | 1 | S2 |
| S6 performance | 1 | indipendente |
| S7 store SEO | 1 | S0.2 |
| S8 misura + guardie | 0,5 | tutto |
| **Totale** | **~11,5 gg** | |

**MVP-lancio se vuoi comprimere (6 gg)**: S0 + S1 + S3 + S7 — home
giusta, ogni prodotto indicizzabile con meta server-side, sitemap
completa, store a posto. S2/S4/S5 sono i moltiplicatori di traffico da
fare subito dopo, S6 in parallelo quando capita.

## Cosa NON facciamo (scelte esplicite)

- Migrazione a Next.js ora: la SEO shell dà l'80% del beneficio con
  il 5% del rischio pre-lancio. Rivalutare a traffico reale.
- Aggregatore cross-store di prodotti fisici/digitali: scelta commerce
  congelata (audit giugno).
- Blog/contenuti editoriali: dopo il lancio (prima le pagine
  programmatiche, che scalano da sole).
- Recensioni/AggregateRating nello schema: quando esisteranno le
  recensioni vere (slot già previsto post-lancio).
