# Tracking visite profilo/ritiri — analisi e piano (VT)

**Data:** 2026-07-09 · **Obiettivo business:** dare all'operatore la PROVA
che Aurya gli porta traffico — visite al profilo `/o/` e alle landing
ritiro `/e/`, separate per canale (directory Aurya vs store proprio) —
così la fee si giustifica da sola e l'upsell Pro ha numeri veri dietro.

---

## 1. Vincoli e asset esistenti (perché NON serve Google Analytics)

**Vincolo di prodotto già dichiarato al pubblico** (cookie banner):
"Nessun tracking di terze parti, nessuna analytics esterna, nessun cookie
pubblicitario". Qualsiasi soluzione deve essere **first-party, cookieless,
senza PII**. Questo esclude GA4/Plausible cloud e rende il tracking
interno l'unica via coerente con la promessa. È anche un VANTAGGIO
commerciale: "misuriamo le visite senza tracciare le persone".

**Asset riusabili:**
- `sales_channel` sugli ordini (GT1/SA1): la CONVERSIONE per canale è già
  tracciata. Manca solo il TRAFFICO a monte — il funnel si chiude.
- Contesto store vs directory già esplicito nel routing: landing con
  `?store=1` = arrivo dallo store; senza = directory/SEO/link diretto.
  `/o/` è sempre directory; `/s/` è sempre store.
- Rate limiter `slowapi` condiviso (routers/auth) per proteggere
  l'endpoint di ping.
- Kit grafico CF1 (`StatCard`, `MiniBars`, `TrendArea`) + OperatorHome:
  la dashboard dove mostrare i numeri esiste già.
- Pattern best-effort consolidato (fee ledger, IndexNow): il tracking
  non deve MAI rompere la pagina.

## 2. Modello dati proposto

Collection **`page_views`** — un documento per hit, poi aggregati:

```
{
  organization_id,           # sempre: la vista è DELL'operatore
  surface: "profile"|"event"|"store",
  slug,                      # org_slug o occ_slug
  channel: "directory"|"store"|"seo",   # vedi §3
  referrer_host,             # solo hostname, mai URL completo (no PII)
  lang, day: "YYYY-MM-DD",   # troncamento: mai timestamp precisi
  visitor_hash               # vedi §4 — dedup senza identificare
}
```

Indici: `(organization_id, day)`, `(organization_id, surface, slug, day)`.
TTL 13 mesi sui grezzi (`created_at` TTL index) — gli AGGREGATI mensili
(`page_view_stats`: org × surface × channel × mese → count) vivono per
sempre e sono ciò che la dashboard legge. Rollup giornaliero nello
scheduler esistente (stesso lock dei job attuali).

## 3. Attribuzione del canale (il cuore della promessa)

Decisa dal FRONTEND al mount della pagina, con regole deterministiche:

| Arrivo | channel |
|---|---|
| Landing `/e/` con `?store=1` (nav interna store) | `store` |
| Landing `/e/` con referrer interno directory (/, /ritiri, /destinazioni, /operatori) | `directory` |
| Landing `/e/` con referrer esterno o nullo (Google, social, link diretto) | `seo` |
| Profilo `/o/` | `directory` (referrer esterno → `seo`) |
| Store `/s/` | `store` |

`seo` separato da `directory` è ciò che rende il numero VENDIBILE:
"questo mese Google ti ha portato 340 visite tramite Aurya" è l'argomento
che nessun operatore ha da solo. (In v1 può confluire in `directory` se
si vuole partire più semplici; lo schema lo prevede da subito.)

## 4. Privacy by design (coerente col banner)

- **Niente cookie, niente localStorage**: `visitor_hash =
  sha256(ip + user_agent + day + salt_giornaliero)[:16]` calcolato SOLO
  server-side e mai reversibile — serve unicamente a dedup "visitatori
  unici del giorno". L'IP non viene MAI salvato. Il salt ruota a
  mezzanotte: impossibile ricostruire percorsi tra giorni.
- **Referrer**: solo l'hostname (google.com, instagram.com), mai il path.
- Nessun consenso aggiuntivo richiesto: misurazione aggregata first-party
  senza identificatori persistenti = interesse legittimo, in linea col
  banner attuale. (Da riflettere in una riga della privacy policy.)

## 5. Anti-bot (i numeri devono essere credibili)

1. **User-Agent filter** server-side: lista bot note (Googlebot, bingbot,
   AhrefsBot, GPTBot, curl, python-requests, headless) → scartati.
   Oggi NON esiste bot-detection nel codebase: va scritta, è ~20 righe.
2. **Il ping parte solo dal JS** (`navigator.sendBeacon` dopo ~3s o al
   primo scroll): i crawler senza JS non pingano affatto; quelli con JS
   li ferma il filtro UA. Il ritardo scarta anche i bounce istantanei.
3. **Rate limit** sull'endpoint (slowapi, per IP) + dedup `visitor_hash`
   per (surface, slug, day): refresh compulsivi contano 1.

## 6. Architettura

- **Endpoint**: `POST /api/public/track` — body {surface, slug, channel,
  referrer_host, lang}. Fire-and-forget, risponde SEMPRE 204 anche su
  errore interno (best-effort assoluto, mai rompere la pagina), risolve
  org da slug, scrive il grezzo.
- **Frontend**: hook `useTrackView(surface, slug, channel)` (~30 righe)
  montato su EventLandingPage, OperatorProfilePage, StorefrontPage.
  `sendBeacon` (sopravvive alla chiusura pagina), timer 3s, una volta
  per mount.
- **Dashboard operatore** (OperatorHome + eventualmente /incassi):
  - StatCard "Visite questo mese" con split *directory / store / Google*
  - MiniBars ultimi 30 giorni
  - per-evento: visite nella Event Dashboard (accanto alla timeline
    vendite CF5) → **conversion rate visite→prenotazioni** per canale,
    incrociando con `sales_channel` degli ordini. Questo è il grafico
    che vende Aurya da solo.
- **Admin piattaforma** (SA2): traffico totale per org nella scheda
  Operatore 360° — utile per il TUO pitch commerciale e i Segnali SA5
  ("tanto traffico, zero Stripe configurato → sbloccalo").

## 7. Cosa NON fare

- Niente analytics di terze parti (romperebbe la promessa del banner).
- Niente session replay, heatmap, fingerprinting persistente.
- Niente conteggio lato SEO-shell (conteremmo i bot e non i visitatori
  reali): il render JS È il filtro più naturale.
- Non mostrare numeri piccoli in modo imbarazzante: sotto una soglia
  (es. <10 visite/mese) la dashboard dice "I primi dati stanno
  arrivando" invece di "3 visite".

## 8. Stima e ordine di lavoro

| Step | Contenuto | Stima |
|---|---|---|
| VT1 | Modello + endpoint /track + anti-bot UA + indici + TTL | ½ giornata |
| VT2 | Hook frontend sulle 3 superfici + attribuzione canale | ½ giornata |
| VT3 | Aggregato giornaliero (scheduler) + endpoint /analytics/visits | ½ giornata |
| VT4 | Dashboard operatore (StatCard+MiniBars+per-evento) + admin 360° | 1 giornata |
| VT5 | Guardie (no-PII: il doc grezzo non contiene ip/email/url; anti-bot; best-effort) | ¼ |

Totale ~2,5-3 giornate. Nessuna dipendenza esterna, nessun costo.
