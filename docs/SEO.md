# SEO.md — le regole operative (fonte unica)

> Compagno di docs/SEO_MASTER_PLAN.md (il piano). Qui: come FUNZIONA e
> come NON romperlo. Guardie: tests/test_seo_shell.py +
> tests/test_seo_invariants.py.

## Architettura in 30 secondi

1. **SEO shell** (`routers/seo_shell.py`, `/__seo/*`): il proxy manda le
   route pubbliche qui; l'HTML esce già con title/OG/canonical/hreflang/
   JSON-LD. Il client poi idrata (useSeoMeta/useProductSeo guidano la
   navigazione SPA).
2. **Sitemap index** (`routers/seo.py`): 4 sotto-sitemap derivate dai
   dati. Pagina in sitemap ⟺ contenuto reale.
3. **IndexNow** (`services/indexnow.py`): ping automatico al publish.
4. **Pagine programmatiche**: /operatori, /destinazioni, /esperienze +
   categoria×regione — crescono sole coi dati, noindex quando vuote.

## Title pattern (non inventarne di nuovi)

| Superficie | Pattern |
|---|---|
| Home | `Aurya — Ritiri ed esperienze olistiche` |
| Landing ritiro | `{nome} — {luogo}, {data} \| Aurya` |
| Landing prodotto | `{nome} — {store} \| Aurya` |
| Categoria | `Ritiri di {categoria} in {regione} \| Aurya` |
| Destinazione | `Ritiri ed esperienze a {luogo} \| Aurya` |
| Operatore | `{nome} — organizzatore su Aurya` |
| Store | governato da Phase 7.6 in StorefrontPage (seo_title custom) |

## Regole d'oro

- **UN solo writer per meta**: StorefrontPage ha già l'effetto 7.6 per
  title/canonical — lì si aggiunge SOLO jsonLd via useSeoMeta (due
  writer sul title si pestano: successo a S7, non ripetere).
- **Canonical sempre senza query**: `?store=1` e `?lang=` puntano alla
  versione pulita; le varianti lingua vivono negli hreflang.
- **hreflang solo se vero**: landing → solo lingue con description
  tradotta (gate multilingua manuale); hub → tutte e 4 (UI completa).
  Con alternates DEVE esserci x-default (guardia attiva).
- **noindex** su: pagine indice con 0 risultati, pagine di flusso
  (checkout result, /account), token page. MAI su una landing.
- **og:image mai vuota**: fallback logo Aurya (già nel resolver).
- **Niente url private in sitemap** (guardia attiva).

## Aggiungere un NUOVO tipo di prodotto alla pipeline (checklist)

1. `routers/seo.py` → `_PRODUCT_PREFIX` (item_type → prefisso landing).
2. `routers/seo_shell.py` → `_PRODUCT_KINDS` + tipo schema in
   `_meta_product`.
3. Frontend: `useProductSeo` → `SCHEMA_TYPE`.
4. `services/indexnow`: nessun cambio (usa _PRODUCT_PREFIX).
5. Run `pytest tests/test_seo_invariants.py tests/test_seo_shell.py`.

## Performance (S6)

- Le immagini upload passano da `_optimize_image` (object_storage):
  WebP q82, max 1600px, fail-safe sull'originale. Non aggiungere
  upload che bypassano `save_public_upload`.
- Il back-office è lazy (React.lazy in App.js): le pagine PUBBLICHE
  restano import statici — non spostarle nei chunk, sono la superficie
  SEO.
- Font via <link> in index.html (mai @import nel CSS).

## Operativo post-deploy 【founder】

1. Google Search Console + Bing Webmaster: verifica dominio via DNS
   (TXT su Cloudflare) → submit `https://aurya.life/api/public/sitemap.xml`.
2. `INDEXNOW_KEY` nel .env (già in DEPLOY_CHECKLIST).
3. Dopo 1 settimana: Search Console → Copertura (0 errori attesi),
   Rich Results Test su un URL per tipo.
4. KPI mensili: impression/click per hub, CTR landing, tempo
   publish→indexed.
