# Preparazione al live in prod — ciclo PP (4 agosto 2026)

> Scopo: portare in prod in sicurezza il delta accumulato dal 27/7
> (ultimo deploy ≈ 7d7a226) a oggi: **122 commit, 301 file,
> +46.886/−5.982 righe** — il nuovo meccanismo di vendita
> (profilo=negozio, listino, checkout unico, account Aurya, potatura
> store) più i cicli contenuti/SEO. Deploy SOLO su ok esplicito del
> founder (regola dall'11/7).

## Esito in una riga

Il sistema è pronto sul piano tecnico: suite completa verde (3.791
test), build di produzione verificata sul percorso esatto del server,
un P0 di packaging trovato e chiuso (pillow-heif), sei incoerenze di
fase sistemate. Restano DUE decisioni del founder prima del go
(vedi «Decisioni aperte»).

## Cosa è stato verificato (PP0–PP5)

### PP0 — Fotografia del delta
- Confine prod: `7d7a226` (27/7, pre-ciclo Listino). Tutto ciò che i
  memory marcano «solo locale» è nel delta.
- Aree: frontend/src (151 file), scripts contenuti (52), routers (17),
  services (16), tests (19), legal ×4 lingue (16), models (5).
- Infra nel delta: SOLO `requirements.txt` (pillow-heif). Niente
  docker-compose/nginx → il deploy è il percorso standard.
- Collection nuove con indici già in `create_indexes()` (si creano da
  soli all'avvio): availability_index, aurya_subscribers,
  platform_accounts/magic_tokens, reviews, orders.platform_account_id.

### PP1 — Suite e build
- **Backend: 3.791 passed, 7 skipped** (skip = rate-limit login live,
  autosananti), 2 guardie stantie riallineate come guardie di
  dispositivo (vedi sotto).
- **Frontend: build di produzione OK** sul percorso esatto del server
  (`npm ci --legacy-peer-deps` + `CI=false npm run build`, come il
  Dockerfile). NOTA per il debug futuro: con un node_modules locale
  «derivato» la build fallisce con `[eslint] Invalid Options` — è un
  falso allarme; il lock ha un ESLint 8.57.1 annidato sotto
  react-scripts che npm ci ripristina. In caso di dubbio: `npm ci`.
- Guardie riallineate (decisioni deliberate, non regressioni):
  - `test_brand_copy_in_four_languages`: aboutPage è IT-only per
    scelta (solo-italiano 2/8 + copy CS2 del founder; fallbackLng
    copre le altre lingue). Parità ×4 resta su brandHome/howPage.
  - `test_motto_overline_in_brand_font`: ChiSiamoPage è il testo del
    founder senza BrandPayoff (052026d) — fuori dalla lista.

### PP2 — Residui commerce in fase rete (audit multi-agente + verifica)
Lettura chiave: il commercio dal profilo (`/o/:slug` con listino,
prezzi, checkout inline; landing `/e/` acquistabili) **NON è un
residuo: è il meccanismo PN0** deciso il 29/7 — resta vivo anche in
fase rete, la scoperta passa solo dai profili membri. Idem gli embed
pubblici (prodotto per i siti degli operatori) e `/esplora-*`
(anteprime volute, non linkate — richiesta founder 29/7).

Incoerenze VERE trovate e sistemate in questo ciclo:
1. `/ritiri/:categoria` restava fuori dal gate di fase e mostrava i
   campioni sfocati dell'era prelaunch → ora segue `/ritiri`
   (redirect a `/` in rete) con `RitiriCategoryGate`.
2. `robots.txt`: aggiunto `Disallow: /esplora-` (le anteprime avevano
   solo un noindex client-side) + commento LC1 corretto.
3. Meta description statica di `index.html` (fallback per le rotte non
   servite dalla shell) prometteva «prenota con caparra» → ora neutra
   di fase.
4. `_meta_category` (shell SEO): le anteprime social di `/ritiri/*`
   promettevano prenotazione anche in rete → description phase-aware.
5. Commenti stantii in `seo.py`/`server.py` che affermavano «/e/ e /o/
   rispondono 404 ai crawler in rete» (falso dopo PN0) → riscritti
   con la verità: pagine VIVE, non pubblicizzate (sitemap vuote,
   niente Allow).
6. `OperatorProfilePage`: variabile `sitePhase` morta + commento RT3
   superato da PN0 → rimossi.

Suite SEO+LC dopo i fix: **348 passed**; robots e meta verificati a
runtime in locale.

### PP3 — Sicurezza (superfici nuove)
- Account Aurya: bcrypt via `auth.get_password_hash`, dummy-hash anche
  su account inesistente (niente timing oracle), rate limit 5-10/min
  su tutti gli endpoint auth, token magic/verifica hashati a DB
  (sha256) con TTL. Verificato a campione su
  `platform_account_service.py` + `platform_accounts.py`.
- Le suite di invarianti sicurezza (test_invariants_security e
  affini) sono nel conteggio verde.
- Niente segreti nel delta; `.env.production` resta solo sul server.

### PP4 — Scalabilità
- Indici per le query nuove presenti e creati all'avvio.
- Nessun `to_list(None)` introdotto nel delta.
- availability_index: si ripopola da solo (job schedulato LM4 +
  rebuild on-write); nessun backfill manuale necessario.
- Nota post-crescita (non blocca): `organizations.network_member` non
  ha indice — irrilevante con poche org, da aggiungere quando la rete
  cresce. Cache shell per-URL TTL 600s: dopo publish di contenuti gli
  hub si aggiornano entro 10 min (comportamento voluto).

### PP5 — Manutenibilità / isolamento del legacy
- Commerce legacy congelato dietro `organizations.legacy_commerce`
  (default False), documentato in docs/LEGACY_COMMERCE.md: dati e
  codice intatti, riattivazione per-org.
- Raccomandazione strutturale (non fatta, da valutare come ciclo
  futuro): `site_phase()` oggi è un `if` copiato a mano in ~10 punti;
  una dependency FastAPI/route-guard unica renderebbe ogni endpoint
  nuovo «chiuso di default» invece che aperto di default.

## Decisioni aperte (founder) — PRIMA del go

1. **Legal v2.3 in BOZZA.** Il delta contiene il legal a due livelli
   (AP-L): sezioni nuove marcate come bozza in attesa di revisione
   legale; il bump innesca il re-consent degli utenti admin al primo
   login. Serve il tuo via (o quello del legale) sui testi PRIMA del
   deploy — è l'unico pezzo del delta pensato per una revisione umana.
2. ~~Indicizzazione dei profili membri~~ **FATTO (ok founder 4/8,
   PP2b)**: in fase rete la sitemap operators elenca i soli
   network_member, solo profilo /o/ (mai /s/), e l'indice la dichiara.
   Guardie: test_operators_sitemap_members_only_in_network_pp2b +
   test_index_declares_operators_in_network_pp2b.

## Runbook del deploy (quando dai il go)

1. **Tag di sicurezza**: `git tag prod-2026-08-pre` sull'attuale
   commit di prod (rollback = redeploy del tag).
2. **Deploy standard**: `VPS_HOST=root@46.224.0.96 ./deploy/deploy-prod.sh`
   (rebuild immagini backend+frontend; pillow-heif entra col rebuild).
3. **Script contenuti in prod** — nell'ORDINE (tutti idempotenti,
   `--dry-run` prima di ognuno; i bn* possono risultare già applicati):
   `bn1 bn2 bn3 bn4 sw4 · pe1 pe2 pe3 pe4 pe5 pe6 pe7 · pc2 pc3 pc4
   pc5 pc6 pc7 pc8 pc9 · pl1 · na1 na2 na3 na4 na5 · pl2 · es1 es2
   es3 · na6 na7 · es4 es5 es6 · na8 na9 · rf1 rf2 rf3 rf4 rf5 rf6 ·
   lc3 · se4 se5 se6a se6b se6c se7 · ed1 ed2 ed3 ed4`
   (55 script; l'ordine è quello cronologico dei commit — i backlink
   si ancorano ai contenuti precedenti).
4. **Smoke test post-deploy** (2 minuti):
   - `/robots.txt` → niente Allow commerciali, `Disallow: /esplora-`
   - `/api/public/sitemap-articles.xml` → 47 articoli
   - `/__seo/blog/discipline-olistiche-la-mappa` → contenuto SSR pieno
   - `/blog/kit-pratiche-quotidiane-15-minuti` da anonimo → anteprima
     gated (~120 parole nella shell)
   - `/ritiri/yoga` → redirect a `/` (SPA) e description neutra (shell)
   - `/o/<slug-membro>` → profilo con listino visibile
   - upload di una foto HEIC da iPhone su un profilo → convertita WebP
   - login operatore + login account Aurya → ok (re-consent admin
     appare una volta, se legal v2.3 approvato)
5. **Effetti attesi post-deploy**: email «Limite negozi» tace dal
   periodo successivo (QF1 — serve deploy prima del 1/9); gli hub del
   Magazine si aggiornano entro 10 min (cache shell).

## Cosa NON cambia con questo deploy
Stripe LIVE e Brevo restano spenti (le email si loggano soltanto);
la fase resta `network`; il flip a marketplace è un'operazione
separata con la sua checklist (campioni, GT1b, sitemap piene).
