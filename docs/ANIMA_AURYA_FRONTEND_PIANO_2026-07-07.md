# L'Anima di Aurya — piano finale di refinement del frontend pubblico

**Data:** 2026-07-07 · **Metodo:** 5 audit paralleli sul codice (brand/messaging, navigazione/IA, geo+scoperta operatori, legal, infrastruttura blog/SEO) · **Contesto:** fase finale di refinement di tutto ciò che vede l'utente pubblico, pre-lancio GTM 1-a-1.

---

## PARTE 1 — Diagnosi (sintesi dei 5 audit)

### 1a. Brand: Aurya è una piattaforma invisibile a casa propria
Il brand tecnicamente esiste (config/brand.js + core/brand.py, logo loto+sole, palette Salvia&Terracotta, motto "Connect. Heal. Grow.", tagline ×4 lingue) ma **la home non dice mai cos'è Aurya**: nessun hero di valore, nessuna pagina /chi-siamo, /come-funziona o /missione, il tagline vive sepolto nel footer, i meta SEO sono generici ("Ritiri yoga Toscana") senza una riga di differenziazione. I trust signal esistono nel codice (recensioni verificate, caparra, Stripe, Passaporto) ma sono **invisibili proprio dove servono**: niente rating sulle card, niente "come ti proteggiamo", niente FAQ caparra prima del pagamento, Passaporto mai promosso. Nota: il tagline dice "in tutto il mondo" — non è vero, siamo Italia-first.

### 1b. Navigazione: due mondi scollegati e un menu che non c'è
L'architettura è SEO-friendly (35+ route pubbliche, aggregatori, breadcrumb) ma **non c'è un menu di navigazione principale**: gli aggregatori (/operatori, /destinazioni, /esperienze) si scoprono solo dal footer; le pagine categoria SEO (/ritiri/yoga) sono orfane (il footer linka la variante ?categoria=); dentro uno store il visitatore è **intrappolato** (StorefrontHeader non torna mai al marketplace); su mobile spariscono ricerca e CTA "Sei un organizzatore?"; gli aggregatori non si linkano tra loro.

### 1c. Geo: il motore c'è, ma è cablato solo sui ritiri
Nominatim+cache, indice 2dsphere, filtro raggio, autocomplete "Dove?", "Vicino a me", mappa Leaflet: tutto già costruito (G1/G3) e riusabile. Ma il **profilo operatore non ha coordinate** (`public_profile` ha solo city/region come testo libero senza autocomplete), `/operatori` non ha filtri geografici né mappa, e le regioni derivano dalle occorrenze future → **un operatore senza ritiri in programma sparisce dalla scoperta geografica** (rompe il gradino 0 profilo-first del GTM).

### 1d. Legal: infrastruttura buona, contenuti di un'altra azienda
Routing, versioning consensi (v1.0+hash, audit trail IP/UA), legal per-merchant, checkout GDPR: tutto solido. Ma i testi backend descrivono ancora **"AFianco — Business Intelligence per PMI"**: 11 occorrenze residue del vecchio brand (header pagine, email davide@afianco.ch, contenuti .md), sezioni sui moduli BI irrilevanti, **zero menzione** di ritiri, caparre, fee di piattaforma, Stripe Connect, Passaporto, recensioni, ruoli operatore/cliente. Il consenso al signup operatore è un checkbox unico (non granulare privacy/terms).

### 1e. Blog: quasi tutto riusabile, manca solo il blog
La SEO shell server-side, il sitemap index, IndexNow, hreflang, il pattern di traduzione manuale (+LLM), la pipeline immagini WebP/S3, il sanitizer markdown e l'editor a tab-lingua (RetreatContentEditor) sono asset pronti. Mancano: modello Article + CRUD, pagine /blog, generazione cover programmatica (Pillow: non esiste ancora), namespace i18n.

## PARTE 2 — Principi

1. **La home vende Aurya, non solo i ritiri**: chi atterra deve capire in 5 secondi cos'è, perché fidarsi, come funziona.
2. **Una sola verità di navigazione**: menu principale unico su tutte le superfici pubbliche; dallo store si torna sempre al marketplace.
3. **Riuso prima di costruire**: geo, mappa, SEO shell, traduzioni, editor — tutto esiste; si estende, non si duplica.
4. **Il legal racconta il business vero**: caparre, fee, Passaporto, recensioni — con versioning che già c'è (bump v2.0).
5. **Il blog è un motore SEO, non un vezzo**: stessa tassonomia dei ritiri, stesse rotaie multilingua, cover coerenti col brand.

## PARTE 3 — Il ciclo AN (Anima), 7 step

### AN1 — Fondamenta brand: la voce di Aurya (~1–1,5 giornate)
- **Definizione scritta del brand** (docs/BRAND_AURYA.md): missione, visione, promessa, USP («il marketplace italiano dei ritiri olistici: operatori con recensioni verificate, prenoti online con caparra protetta»), tono di voce ×4 lingue.
- **Home rifatta sopra il calendario**: hero con value prop vera (non solo search), sezione "Come funziona" (Scegli → Prenota con caparra → Vivi il ritiro → Recensisci), sezione "Perché Aurya" (recensioni solo verificate · caparra protetta Stripe · Passaporto Ritiri · operatori italiani), blocco "Sei un organizzatore?" con CTA /inizia.
- **Pagine /chi-siamo e /come-funziona** (×4 lingue, SEO shell + sitemap).
- **Meta SEO con brand**: title/description di home e aggregatori con Aurya e la promessa; tagline onesta («in Italia» invece di «in tutto il mondo»).

### AN2 — Navigazione unificata (~1 giornata)
- **Menu principale nel MarketplaceShell**: Ritiri · Esperienze · Operatori · Destinazioni · Blog (quando esiste) · Chi siamo — desktop inline, mobile hamburger con ricerca e CTA organizzatori (oggi spariscono).
- **Fix link categoria**: footer e chips puntano ai path SEO (/ritiri/yoga), non alla query (?categoria=).
- **Ponte store→marketplace**: nello StorefrontHeader una via di ritorno discreta ("Parte di Aurya ✦" → /) — lo store resta il protagonista, ma non è più una trappola.
- **Cross-nav aggregatori**: tabs/link fra /operatori, /destinazioni, /esperienze.

### AN3 — Operatori geolocalizzati (~1–1,5 giornate)
- **Modello**: `public_profile.latitude/longitude/geo` (GeoJSON) + indice 2dsphere su organizations; geocoding automatico best-effort di city/region al salvataggio profilo (riuso services/geocoding, stessa cache).
- **Editor profilo**: campo località con autocomplete (/geo/search riusato) che compila city/region/coordinate — l'operatore configura la sua posizione, come chiesto.
- **API /public/operators**: filtri `lat/lng/radius_km` + `location` dal PROFILO (fix: l'operatore senza ritiri futuri resta scopribile), regioni = profilo ∪ occorrenze.
- **Pagina /operatori**: GeoSearchBar ("Dove?" + "Vicino a me" + raggio) + toggle vista mappa (riuso RetreatsMapView con pin operatori → /o/{slug}) + filtri categoria esistenti.
- Backfill geocoding per i profili esistenti con city.

### AN4 — Legal della piattaforma vera (~1 giornata)
- **Riscrittura privacy_it.md e terms_it.md** per Aurya marketplace: ruoli (Aurya/operatore/cliente/visitatore), caparre e piani di pagamento, fee di piattaforma, Stripe Connect, Passaporto Ritiri, recensioni verificate (OTP), newsletter, cookie; poi EN/DE/FR.
- **Pulizia 11 occorrenze AFianco** (header pagine legal, email di supporto → supporto@aurya.life, contenuti).
- **Bump versione consensi a v2.0** (il meccanismo hash c'è già) — i nuovi consensi timbrano la versione nuova; niente re-accept forzato pre-lancio (zero utenti reali).
- **Signup operatore granulare**: due checkbox separati (privacy / terms) come già fa il cliente.
- Guardia CI: "AFianco" vietato nei contenuti pubblici e legal.

### AN5 — Blog: fondamenta (~1,5 giornate)
- **Modello `Article`** (slug, title, description, content markdown sanitized, category dalla tassonomia RETREAT_CATEGORIES, featured_image_url, translations {en,de,fr}, published) + router CRUD admin (system admin scrive; struttura pronta per autori futuri) + endpoint pubblici.
- **ArticleEditor** admin sul pattern RetreatContentEditor (tab lingua, markdown, anteprima, bottone "traduci con LLM" riusando il servizio F4/F5).
- **Pagine pubbliche /blog e /blog/{slug}**: lista con filtro categoria, dettaglio con markdown renderizzato safe, lingue via useStorefrontLocale, dentro il MarketplaceShell (e nel menu AN2).
- i18n namespace blog ×4.

### AN6 — Blog: SEO industriale + cover autogenerate (~1 giornata)
- **SEO shell** `_meta_article` (title/description/OG/canonical/hreflang + JSON-LD BlogPosting), **sitemap-articles.xml** nel sitemap index, **IndexNow** al publish — stesse rotaie dei ritiri.
- **Generatore cover** (Pillow, servizio `services/article_cover.py`): template per ognuna delle 9 categorie olistiche nello stile Aurya (fondo salvia/crema con texture radiale come l'hero, glifo di categoria, palette Salvia #376254/Terracotta #C97B5D, font Cinzel/Manrope) **col titolo dentro l'immagine**, output WebP 1200×630 (OG-perfetto) su object storage. Generata al publish se l'autore non carica una foto propria; rigenerabile.

### AN7 — Trust in vetrina + Passaporto (~1 giornata)
- **Rating visibile**: stelle+conteggio (recensioni verificate) sulle card della directory e nell'hero della landing ritiro (i dati ci sono già: reviews_stats).
- **Sezione recensioni nella landing ritiro** ("Cosa dicono i partecipanti", badge Cliente verificato).
- **FAQ caparra/pagamenti** nella landing prima del checkout («la caparra è protetta da Stripe», policy rimborso) — il momento della carta di credito è il momento della fiducia.
- **Passaporto promosso**: CTA nel menu/footer e nel post-checkout («le tue esperienze, tutte in un posto»).

## PARTE 4 — Ordine, dipendenze, stima

```
AN1 (brand/copy) ──► AN2 (nav: il menu ospita le pagine nuove)
AN4 (legal)          indipendente — anticipabile se i contatti operatori partono prima
AN3 (geo operatori)  indipendente
AN5 (blog core) ──► AN6 (blog SEO+cover)   [il menu Blog in AN2 si attiva qui]
AN7 (trust)          dopo AN1 (il racconto) — tocca card e landing
```
**Ordine proposto:** AN1 → AN2 → AN4 → AN3 → AN5 → AN6 → AN7. Totale stimato **~7–8,5 giornate**. Ogni step: branch dedicato, guardie di test (i18n ×4, AFianco-ban, SEO shell, geo), E2E, merge --no-ff.

**Fuori scope dichiarato:** redesign visivo del tema (Salvia&Terracotta resta), app mobile, contenuti degli articoli (il blog nasce con 1-2 articoli seme per collaudo — il piano editoriale è attività founder), CMS multi-autore avanzato (il modello lo predispone).
