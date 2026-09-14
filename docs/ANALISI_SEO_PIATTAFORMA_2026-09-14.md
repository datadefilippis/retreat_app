# Aurya, 14 settembre 2026 sera — SEO dell'intera piattaforma: stato, gap, piano

Richiesta del founder: «rianalizzare l'indicizzazione del sito e fare
un'analisi profonda a livello olistico dell'intera piattaforma per
verificare che abbiamo implementato tutte le best practice e siamo
pronti a rankare. Identifica gap e spazi di miglioramento».

Metodo: crawl del sito vivo come Googlebot su 30 rotte (titoli,
description, canonical, robots, dati strutturati, H1, link interni,
parole), lettura di sitemap, robots, header e prestazioni reali dal
browser, e lettura riga per riga del codice che produce tutto questo
(registro rotte, shell per i crawler, sitemap, nginx, build). Ogni
affermazione ha una prova. Prima ciò che è solido, poi i gap in ordine
di peso, poi il piano.

*Fatto stasera, prima dell'analisi:* «a Lecce» ma «in Puglia», «nel
Lazio», «nelle Marche», «ad Acri» nei titoli e nelle description del
profilo (commit 78b40022, non ancora in produzione).

---

## 1. Quello che è già solido (e va difeso)

L'impianto tecnico è sopra la media di un sito di questa età.

- **Stesso HTML per bot e persone, niente cloaking.** nginx manda ogni
  rotta pubblica alla shell del backend, che inietta titolo, description,
  canonical, Open Graph, JSON-LD **e un corpo leggibile** (H1, testo,
  link) dentro `index.html`; React idrata sopra. Home 925 parole, landing
  operatore 1.438, articolo 3.526, profilo 337.
- **404 veri.** Percorso ignoto → HTTP 404 con `noindex`; profilo
  inesistente → 404; radici nude (`/o`, `/e`, `/frequenze`) → 404.
  Redirect 301 puliti: http→https, www→apex, `/ritiri`, `/esplora-*`,
  `/come-funziona`, `/index.html`.
- **Dati strutturati giusti per tipo**: `WebSite`+`Organization` in
  home, `LocalBusiness` con address/geo/areaServed/rating/offerte sul
  profilo, `Event` con Place/Offer/organizer sulla landing del ritiro,
  `BlogPosting`+`FAQPage`+`BreadcrumbList` sugli articoli, `ItemList` su
  directory e categorie, `AudioObject` sulle frequenze, `CollectionPage`
  su Sound. Date umane, mai ISO nudo.
- **HEAD gestito** (i fetcher delle AI non prendono più 405),
  `llms.txt` e `llms-full.txt` reali, hreflang onesto (solo `it` +
  `x-default` in fase rete).
- **Sicurezza e trasporto**: HTTP/2, HSTS con preload, CSP completa,
  gzip, asset immutabili per un anno, `no-cache` sull'HTML.
- **Prestazioni misurate** (desktop, rete vera): home TTFB 261 ms, LCP
  908 ms sull'immagine hero, load 398 ms; profilo TTFB 77 ms. I Core
  Web Vitals di laboratorio sono verdi.
- **Guardie**: otto suite di test proteggono registro rotte, shell,
  sitemap, schema, parità client/shell, `llms.txt`.

---

## 2. La fotografia del crawl (30 rotte, come Googlebot)

| Rotta | Title (car.) | Desc (car.) | Canonical | Robots | JSON-LD | Link interni | Note |
|---|---|---|---|---|---|---|---|
| `/` | 41 | 120 | self | — | WebSite, Organization | 28 | ok |
| `/cerca-ritiro` | 59 | **190** | self | — | WebPage | 8 | **non in sitemap** |
| `/entra-nella-rete` | **72** | 182 | self | — | WebPage, FAQPage | 4 | title lungo |
| `/operatori` | 67 | 102 | self | — | ItemList | 12 | title client ≠ shell |
| `/operatori/yoga` | 67 | 102 | **`/operatori`** | — | ItemList | 12 | pagina categoria annullata |
| `/o/ilaria` | 57 | **35** | self | — | LocalBusiness, Breadcrumb | **2** | description magra |
| `/s/ilaria` | 57 | 35 | `/o/ilaria` | — | idem | 2 | ok (duplicato risolto) |
| `/@ilaria` | 57 | 35 | — | noindex | — | 2 | ok per scelta |
| `/esperienze` | 51 | **221** | self | — | — | 2 | 1 ritiro |
| `/esperienze/yoga` | 22 | 125 | self | noindex | Breadcrumb | 0 | < 10 ritiri |
| `/destinazioni/puglia` | 37 | 128 | self | noindex | Breadcrumb | 0 | «a Puglia»; in fase rete la SPA rimanda in home |
| `/e/…/silente…` | **83** | 94 | self | — | Event, Breadcrumb | — | non in sitemap in fase rete |
| `/blog` | 63 | 127 | self | — | Breadcrumb | 14 | 47 articoli linkati |
| `/blog/aromaterapia…` | 60 | 139 | self | — | BlogPosting, FAQPage, Breadcrumb | 12 | 3.526 parole, cover `alt=""` |
| `/magazine` | **5** | 0 | — | noindex | — | 0 | **200 invece di 301 → /blog** |
| `/costi` | 57 | 161 | self | — | WebPage | 4 | ok |
| `/chi-siamo` | 17 | 125 | self | — | AboutPage | 4 | title corto |
| `/manifesto` | 64 | 124 | self | — | Article | 4 | ok |
| `/sound`, `/sound/esplora` | 55/61 | 169/163 | self | — | CollectionPage | 13/0 | ok |
| `/meditazioni`, `/newsletter` | 47/64 | 151/177 | self | — | CollectionPage/WebPage | 7/4 | ok |
| `/aziende` | 65 | **293** | self | — | WebPage | 4 | **in sitemap**, description troppo lunga |
| `/privacy`, `/termini` | 5 | 0 | — | noindex | — | 0 | per scelta |
| `/strutture`, `/x-inesistente` | — | — | — | 404 | — | — | ok |
| `/operatori/` (barra finale) | 67 | 102 | `/operatori` | — | — | — | 200 invece di 301 |

Sitemap: `core` 62 URL (di cui 36 schede Sound; **manca `/cerca-ritiro`**,
c'è `/aziende`, c'è una `/frequenze/…` legacy), `operators` 9,
`articles` 62 (47 articoli + 15 categorie, **tutti con lo stesso
`lastmod` 25/8**); in fase rete `retreats` e `products` non esistono.

Magazine: 47 articoli, **tutti pubblicati il 4 agosto**, nessuno dopo.

Bundle: `main.js` **1,59 MB** (435 KB gzip) caricato su ogni pagina;
cinque famiglie Google Fonts da terze parti; immagini senza
`width/height` esplicite sul profilo.

---

## 3. I gap, in ordine di peso

### G1 — Nessuna pagina locale indicizzabile (il gap più grande)

Le ricerche che portano clienti agli operatori sono locali: «yoga
Lecce», «reiki Milano», «operatore olistico Puglia», «ritiro yoga
Puglia». Oggi:

- `/operatori/{categoria}` esiste ma **canonicalizza a `/operatori`**:
  per Google è una pagina sola.
- `/destinazioni/{luogo}` nasce **dai ritiri**, non dagli operatori, è
  `noindex` in fase rete e la SPA la rimanda in home.
- `/esperienze/{categoria}/{regione}` è `noindex` sotto 10 ritiri (giusto
  oggi: ce n'è uno).
- Il profilo ha **2 link interni** nel corpo per i crawler: nessuna
  maglia «altri operatori di Yoga in Puglia».

Con le sedi (da stasera ogni operatore ha città e **regione canonica**)
la materia prima c'è: disciplina × regione × città è calcolabile.

### G2 — Directory: il client contraddice la shell

Su `/operatori` il titolo del client («Professionisti del benessere in
Italia») è diverso da quello della shell («Operatori olistici e
professionisti del benessere in Italia»), e su `/operatori/{categoria}` il
client mette canonical `/operatori/{categoria}` mentre la shell mette
`/operatori`. Google vede due verità sulla stessa pagina; la guardia
esistente controlla solo il `noindex`.

### G3 — Igiene di indicizzazione (piccole cose che pesano)

- `/magazine` risponde 200 `noindex` con titolo «Aurya» invece di 301 a
  `/blog`.
- barra finale: `/operatori/` risponde 200 (canonical giusto, ma un 301
  chiude il caso).
- `/cerca-ritiro`, la porta di chi cerca, **non è in sitemap**;
  `/aziende` sì (è una porta viva o un residuo? da decidere).
- `lastmod` uniforme su 47 articoli (25/8): Google lo ignora quando
  è finto; `core` ha un solo `lastmod`.
- la sitemap dei ritiri per categoria emette `/ritiri/…` mentre il
  canonical è `/esperienze/…` (oggi inerte perché la sitemap è vuota
  in fase rete, ma è una mina per la fase marketplace).
- lunghezze fuori misura: title `/entra-nella-rete` 72 e landing ritiro
  83 (Google taglia a ~60); description `/aziende` 293,
  `/esperienze` 221, `/cerca-ritiro` 190 (taglio a ~155); `/chi-siamo`
  title 17.

### G4 — Il profilo operatore è magro per Google

- description = tagline anche quando è di 35 caratteri (Ilaria);
  la bio, 200-580 caratteri, è quasi sempre più utile.
- `LocalBusiness` senza `@id`, `image` (obbligatoria per il rich
  result), `priceRange`; `aggregateRating` c'è solo con recensioni
  (oggi: quasi nessuna).
- nessun link a disciplina, regione, ritiri dell'operatore, articoli
  del Magazine sulla sua disciplina: il PageRank interno non circola.
- l'intervista (quando c'è) non è una pagina indicizzabile a sé.

### G5 — Contenuto fermo, E-E-A-T debole

47 articoli in un giorno (4/8) e poi silenzio: Google legge la cadenza.
Autore = Organizzazione o Persona senza pagina; nessuna pagina
«Redazione»; nessun articolo firmato da un operatore con link al suo
profilo (sarebbe E-E-A-T vero: esperienza di chi pratica). La cover
degli articoli ha `alt=""`.

### G6 — Prestazioni: verde oggi, fragile domani

`main.js` 1,59 MB (435 KB gzip) su ogni pagina, inclusa la home: CRA
senza `splitChunks`, con Leaflet, il motore audio di Sound e l'admin
nel bundle comune. Cinque famiglie di font da Google (render-blocking,
terza parte, cookie-free ma un DNS in più). Immagini del profilo senza
dimensioni esplicite (rischio CLS su mobile). Mobile non misurato qui:
è dove Google misura.

### G7 — Fuori dal sito: zero segnali

Backlink 0 (noto dal 25/8), Search Console con la sitemap da
ripresentare, Bing Webmaster non attivo, nessuna citazione. Con nove
profili e 47 articoli il contenuto c'è; l'autorità no.

### G8 — Piccoli difetti di schema e copy

«Ritiri ed esperienze **a** Puglia» nelle destinazioni (stessa regola
di stasera da applicare); `Event` senza `image`; `og:image` assente su
alcune pagine senza copertina; `/come-funziona` è 301 e va bene, ma
`/aziende` e `/frequenze/…` in sitemap vanno decisi.

---

## 4. Il piano (ciclo SEO-A…G)

| Passo | Cosa | Effetto atteso | Stima |
|---|---|---|---|
| **SEO-A** Igiene | `/magazine` 301; barra finale 301; parità client/shell su `/operatori` (title e canonical) con guardia; `/cerca-ritiro` in sitemap, via `/aziende` e `/frequenze` legacy (se il founder conferma); `lastmod` veri (solo su modifica); prefisso `/esperienze` nella sitemap; lunghezze title/description sulle 7 pagine; «in Puglia» anche nelle destinazioni; deploy insieme al fix di stasera | Zero segnali contraddittori; Google smette di scegliere al posto nostro | ½ giornata |
| **SEO-B** Pagine locali | `/operatori/{disciplina}`, `/operatori/{disciplina}/{regione}` e `/operatori/{regione}`: indicizzabili solo con **≥ 3 operatori** (altrimenti `noindex`, mai pagine vuote), ItemList, intro di 2-3 frasi per disciplina (dalle famiglie di `models/disciplines.py`) e per regione, breadcrumb, FAQ, sitemap; filtro «regione» nella directory viva; **maglia**: dal profilo «Altri operatori di Yoga in Puglia», dalla pagina locale ai profili e agli articoli della categoria | Le query locali hanno finalmente una pagina | 2 giornate |
| **SEO-C** Profilo forte | description dalla bio se la tagline < 80 car.; `LocalBusiness` con `@id`, `image`, `priceRange` dal listino; link a disciplina/regione/ritiri/articoli; intervista come pagina indicizzabile `/o/{slug}/intervista` con `Article` e autore = operatore | Rich result e PageRank che circola | 1 giornata |
| **SEO-D** Contenuto e E-E-A-T | cadenza: **2 articoli a settimana** (piano editoriale per disciplina × domanda locale); pagina «Redazione» e autori con `Person`; articoli firmati dagli operatori con link al profilo; `alt` = titolo sulla cover; aggiornare 3-4 articoli al mese con `updated_at` vero | L'unico modo di far crescere l'autorità senza backlink comprati | continuo (½ g di setup) |
| **SEO-E** Prestazioni | `splitChunks`: Leaflet, motore audio, admin e Sound Lab in chunk propri (obiettivo home < 200 KB gzip); due font self-hosted con `preload` (Manrope + Cinzel), le altre via; `width/height` su tutte le `img`; misura mobile con PageSpeed prima/dopo; guardia sul peso del bundle | CWV verdi anche su mobile 4G | 1 giornata |
| **SEO-F** Fuori dal sito | Search Console: sitemap ripresentata, «richiedi indicizzazione» sui 9 profili e sulle 3 porte; Bing Webmaster; badge «Fatta con Aurya» già nel piede della pagina link → chiedere agli operatori di linkare il profilo dal loro sito e dalla bio Instagram (backlink veri); 5 directory/portali olistici italiani per citazioni; PR: un articolo-dati («la mappa degli operatori olistici in Italia») | I primi backlink e la scoperta rapida | founder + ½ g |
| **SEO-G** Misura e guardie | il crawl di stasera diventa uno script ripetibile (`scripts/seo_crawl.py`) con soglie (lunghezze, parità client/shell, JSON-LD valido, 404); esportazione mensile GSC (query, pagine, copertura) in `docs/seo/`; Rich Results Test sui 5 tipi | Si vede se funziona, e si sa cosa rompe | ½ giornata |

Ordine consigliato: A (subito, con il fix di stasera) → B → C → E, con D
e F che partono in parallelo e non finiscono mai. Circa 5 giornate di
sviluppo più il lavoro editoriale.

## 5. Le decisioni che spettano al founder

1. **Pagine locali**: soglia di 3 operatori per indicizzare (proposta) o
   2? Sotto soglia la pagina esiste ma è `noindex`.
2. **`/aziende`**: porta viva da tenere in sitemap, o residuo da
   togliere (oggi è raggiungibile e indicizzabile)?
3. **Cadenza editoriale**: 2 articoli/settimana è sostenibile? Chi
   scrive (redazione, AI con revisione, operatori)?
4. **Font**: ridurre a due famiglie self-hosted cambia leggermente
   l'aspetto di alcune pagine Sound (JetBrains Mono, Public Sans): ok?
5. **Fase rete vs marketplace**: in fase rete la sitemap non dichiara
   ritiri né prodotti e le destinazioni sono `noindex`. È coerente con
   «marketplace spento fino a rete viva»; le pagine locali di SEO-B
   nascono dagli operatori, quindi vivono anche in fase rete.
