# Profilo operatore 2.0 + Sistema recensioni — piano (6/7/2026)

> Obiettivo founder: il profilo come CARTA D'IDENTITÀ dell'operatore
> (vetrina moderna: cover + ritratto + descrizione a lato + link + info)
> e un sistema di recensioni SOLIDO: recensisce solo chi ha ordinato
> da quell'operatore (anti-spam via email negli ordini), con opzione
> sbloccabile per recensioni aperte; gestione in una pagina del menu.

## Stato attuale (verificato nel codice)

- `organizations.public_profile` (whitelist rigida): bio 600, city,
  region, cover_url, instagram/website/facebook, public_email/phone,
  show_contacts. Upload cover già esistente (pattern logo org).
- OperatorProfilePage (/o/{slug}): hero cover + card identità + griglia
  ritiri. NESSUNA recensione (M3 aveva previsto solo lo slot).
- Editor admin: PublicProfilePage su /public-profile — NON nel menu
  (solo un CTA dentro StoresPage).
- SEO: Organization JSON-LD client+shell; profilo in sitemap-operators.

## Decisioni architetturali (le fondamenta della solidità)

1. **Chi può recensire** — due livelli:
   - **Cliente verificato** (default, sempre attivo): l'email deve
     appartenere a ≥1 ordine NON-draft di quell'org. Prova di possesso
     email con **codice OTP a 6 cifre via email** — riusiamo l'intero
     pattern del Passaporto (token hash-only, one-shot, max 5
     tentativi, rate limit). Niente account richiesto: zero attrito.
   - **Recensioni aperte** (opt-in per organizzazione,
     `reviews_open=false` di default): chi non ha ordini può scrivere,
     ma la recensione nasce `pending` e va in **moderazione
     dell'operatore** prima di apparire; MAI badge "Cliente verificato".
2. **Anti-spam a strati**: OTP email (possesso) + 1 recensione per
   email per operatore (la nuova sostituisce la vecchia, marcata
   "aggiornata") + rate limit endpoint (5/min IP, 3/ora per email) +
   honeypot nel form + lunghezze min/max (20–1500) + l'hash
   dell'email a DB (mai l'email in chiaro sul documento pubblico).
3. **Credibilità marketplace**: l'operatore NON può cancellare né
   modificare le recensioni verificate — può **rispondere**
   (reply pubblica, il vero strumento di fiducia) e **segnalare** ad
   Aurya (flag abuse → nasconde in attesa di revisione piattaforma).
   Le recensioni verificate pubblicano SUBITO (nessun filtro).
4. **Aggregati denormalizzati**: `organizations.reviews_stats`
   {avg, count, distribution} ricalcolato a ogni transizione di stato
   (scala: niente aggregation per render; il profilo legge un campo).
5. **SEO recensioni**: aggregateRating + Review nel JSON-LD del
   profilo. Nota policy Google: le stelle in SERP su recensioni
   "self-serving" non vengono mostrate per le pagine dell'entità
   stessa — ma il markup resta corretto e alimenta comunque i dati;
   il rating alimenta anche le card di /operatori e la landing ritiro.

## PR1 · Profilo vetrina 2.0 — la carta d'identità (1,5 gg)

**Nuovi campi** `public_profile` (whitelist estesa):
`tagline` (80), `portrait_url` (il ritratto/foto a lato — upload
dedicato, pattern cover), `photos` (galleria: lista url, max 8, upload
multiplo riusando save_public_upload → WebP automatico da S6),
`founded_year` (4), `languages` (lista di codici es. ["it","en"]).

**Redesign pagina /o/{slug}** (2 colonne, mobile-first):
- **Hero**: cover full-width (fetchpriority=high) + logo sovrapposto +
  nome + tagline + badge fiducia: «Su Aurya dal {anno}», «{n} ritiri
  organizzati», «★ {avg} ({count} recensioni)» quando esistono.
- **Colonna sinistra**: Chi siamo (bio) · Galleria foto (grid + 
  lightbox, riuso pattern M2) · Prossimi ritiri (card esistenti) ·
  Esperienze non-evento dell'operatore · **Recensioni** (PR4).
- **Sidebar destra sticky** (la "carta d'identità"): ritratto ·
  tagline/descrizione breve · 📍 città/regione (link alla
  destinazione!) · lingue parlate · social + sito · contatti (se
  opt-in) · «Visita il negozio» · CTA «Scrivi una recensione».
- Ancore interne (Chi siamo · Foto · Ritiri · Recensioni).
- SEO: Organization arricchito (foundingDate, sameAs dai social,
  aggregateRating quando c'è) client + shell.

**Editor admin** (PublicProfilePage): sezioni nuove (ritratto,
galleria con riordino, tagline, anno, lingue) + anteprima live.

**Menu**: voce **«Profilo pubblico»** nel nav admin (icona
UserCircle, sotto My Stores) → /public-profile.

- **DoD**: profilo demo completo che "vende" l'operatore; Rich Results
  verde; mobile fluido.

## PR2 · Backend recensioni (1,5 gg)

**Modello** `reviews`:
```
{ id, organization_id, org_slug, rating 1-5, title? (80), body (1500),
  author_name (60), author_email_hash (sha256+salt), verified: bool,
  order_ref: bool (ha ordini), status: published|pending|flagged|removed,
  reply: {body (1000), at} | null, lang, created_at, updated_at }
```
Indici: (organization_id, status, created_at desc) + unique
(organization_id, author_email_hash).

**Flusso pubblico** (`/api/public/reviews/*`):
1. `POST /reviews/request-otp` {org_slug, email} → 202 SEMPRE
   (enumeration-safe). Genera OTP (riuso MagicLinkToken pattern,
   collection propria review_otp, TTL 15min). Nell'email: "stai per
   recensire {operatore}".
2. `POST /reviews/submit` {org_slug, email, code, rating, title?,
   body, author_name, honeypot} → verifica OTP one-shot → controlla
   ordini dell'email in quell'org (customers→orders, stessa
   risoluzione del claim Passaporto):
   - ha ordini → `verified=true, status=published`
   - niente ordini + org.reviews_open → `verified=false, status=pending`
   - niente ordini + closed → 403 con messaggio gentile.
   Upsert su (org, email_hash): la nuova sostituisce la vecchia.
3. `GET /public/reviews/{org_slug}?page=` → published, paginate 10,
   author_name + rating + body + verified + reply (MAI email/hash).
4. Ricalcolo `reviews_stats` a ogni publish/remove.

**Admin** (`/api/reviews/*`, require_admin):
- `GET /reviews` (filtri status) · `POST /reviews/{id}/reply` ·
  `PATCH /reviews/{id}/moderate` {approve|reject} (SOLO pending
  unverified) · `POST /reviews/{id}/flag` (abuse → flagged, nascosta,
  notifica piattaforma) · `PATCH /reviews/settings` {reviews_open}.

- **DoD**: suite con i casi: verified publish, open→pending→approve,
  closed→403, upsert stessa email, OTP sbagliato/riusato, honeypot,
  stats corrette, MAI email in chiaro nelle risposte.

## PR3 · Pagina Recensioni nel back-office (1 gg)

- Route `/reviews` (lazy, come da S6) + voce menu **«Recensioni»**
  (icona Star, gruppo operations).
- Header: media grande + distribuzione 5→1 (barre) + toggle
  **«Accetta recensioni da chi non ha ancora prenotato»** con spiega.
- Tab: Pubblicate · In attesa (badge count — solo se reviews_open) ·
  Segnalate.
- Card recensione: rating, testo, badge verificata, data; azioni:
  **Rispondi** (textarea inline), Approva/Rifiuta (pending), Segnala.
- Empty state che spiega il meccanismo e invita a condividere il
  profilo.

## PR4 · Recensioni sul profilo pubblico (0,5 gg)

- Sezione «Recensioni» nel profilo: media + distribuzione + cards
  (nome, data, rating, badge «Cliente verificato», testo, reply
  dell'operatore evidenziata), paginazione "mostra altre".
- Modale «Scrivi una recensione»: email → OTP → form (stessa UX
  dell'attivazione Passaporto: familiare e già collaudata).
- Rating nelle card di /operatori e sulla landing ritiro (accanto
  all'organizzatore).
- JSON-LD aggregateRating+Review (client + shell).

## PR5 · Guardie, scala, i18n (0,5 gg)

- Test guardia: invarianti anti-spam sopra + "reply mai senza
  recensione" + "unverified mai published senza approve".
- 4 lingue per tutto il flusso (form, email OTP recensione, admin).
- Email OTP recensione nel template R2b.
- Rate limit + indici verificati con explain.

## Ordine e stime

| Fase | Giorni |
|---|---|
| PR1 profilo vetrina + editor + menu | 1,5 |
| PR2 backend recensioni | 1,5 |
| PR3 pagina admin | 1 |
| PR4 pubblico + SEO | 0,5 |
| PR5 guardie + i18n | 0,5 |
| **Totale** | **~5 gg** |

Sequenza consigliata: PR2 (fondamenta dati) → PR1 (vetrina, così la
sezione recensioni ha già l'API) → PR4 → PR3 → PR5. In pratica
PR1 e PR2 sono indipendenti: si può partire dalla vetrina per vedere
subito il design.

## Cosa NON facciamo (scelte esplicite)

- Recensioni per SINGOLO ritiro/prodotto: prima quelle per operatore
  (più recensioni per pagina = massa critica; il per-prodotto arriva
  quando c'è volume).
- Foto nelle recensioni: v2 (moderazione immagini = altro problema).
- Incentivi/richieste automatiche post-ordine via email: ottima idea,
  MA dopo il lancio (è marketing automation, non fondamenta).
- Import recensioni da Google/TripAdvisor: mai (violazione ToS).
