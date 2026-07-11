# SEO Playbook — Aurya (documento operativo permanente)

> QUESTO è il documento da rileggere prima di qualsiasi lavoro SEO o
> editoriale su Aurya: come scriviamo, come linkiamo, cosa è automatico
> e cosa va fatto a mano, e cosa cambiare al lancio ufficiale.
> Strategia di mercato: docs/SEO_STRATEGY_2026-07.md.
> Calendario editoriale: docs/MAGAZINE_EDITORIAL_PLAN_2026-07.md.
> Ultimo consolidamento: 2026-07-11 (SEO4).

---

## 1. L'infrastruttura (cosa è GIÀ automatico)

Ogni articolo pubblicato (via ArticleEditor admin o seed) ottiene da solo:

| Cosa | Dove vive | Note |
|---|---|---|
| Title/description/OG/canonical server-side | `backend/routers/seo_shell.py` (`_meta_blog_article`) | serviti nell'HTML iniziale, zero JS richiesto |
| JSON-LD `BlogPosting` con **articleBody completo** | idem (SEO4) | i crawler LLM (GPTBot, ClaudeBot, PerplexityBot) NON eseguono JS: il testo integrale nel JSON-LD è come ci leggono |
| JSON-LD `FAQPage` | estratto dal blocco `## Domande frequenti` (SEO4) | domanda = riga in grassetto che finisce con `?`, risposta = paragrafi successivi |
| Autore `Person` + affiliation Aurya | SEO4 | "Valentina · Aurya" → Person "Valentina"; "Aurya" → Organization. E-E-A-T |
| BreadcrumbList, hreflang (solo lingue tradotte), inLanguage | shell | |
| Cover brand (titolo serif + geometria sacra di categoria) | `services/article_cover.py`, generata al publish | design v2 armonizzato card Masseria |
| Sitemap articles + lastmod | `routers/seo.py` | inclusa nel sitemap index |
| Ping IndexNow | hook di publish nel router; nel seed è esplicito | Bing/Yandex immediati |
| llms.txt | `frontend/public/llms.txt` | presentazione del sito per gli assistenti AI; aggiornare le "guide di riferimento" quando nascono pilastri nuovi |

Guardie di regressione: `backend/tests/test_prelaunch_pl.py` e
`test_blog_an5.py` e `test_seo_shell.py`. Se un refactor tocca la shell,
DEVONO restare verdi.

## 2. Regole di scrittura articoli (checklist per ogni pezzo)

1. **Keyword nel titolo, all'inizio.** Il title servito è `{titolo} | Aurya`: tenere il titolo entro ~55-60 caratteri quando possibile (Google tronca; se serve più lungo, le parole chiave stanno nei primi 50).
2. **Description 120-160 caratteri**, con la keyword e una promessa concreta.
3. **Slug corto e keyword-first**, mai cambiarlo dopo la pubblicazione (romperebbe URL indicizzati; se inevitabile serve redirect 301).
4. **Lunghezza**: 900+ parole minimo, 1.200-1.800 per i pilastri. Il conteggio conta meno della completezza: l'articolo deve essere la risposta più completa d'Italia sul tema.
5. **Struttura**: intro che aggancia (2-3 paragrafi) → H2 puliti → `## Domande frequenti` SEMPRE in fondo (3-5 domande in grassetto che finiscono con `?` → diventa FAQPage schema automaticamente).
6. **Liste numerate SEMPRE a caporigo** (`1. ` a inizio riga): il renderer le trasforma in `<ol>`. Mai enumerare in un paragrafo unico.
7. **Link markdown** `[testo](url)`: interni relativi (`/blog/slug`, `/cerca-ritiro`), il renderer li supporta (whitelist: `/`, https, mailto).
8. **2-4 link interni per articolo**: ai fratelli di cluster + 1 CTA contestuale. Ogni pilastro nuovo va linkato DAI satelliti esistenti (aggiornare 2-3 vecchi articoli quando esce un pilastro).
9. **Onestà radicale**: cosa dice la ricerca E cosa non dice, prezzi veri in euro, controindicazioni, "quando serve un professionista". È il differenziante del brand e ciò che Google/LLM premiano.
10. **Firma vera**: discipline energetiche/divinatorie → `Valentina · Aurya`; B2B/fiscale/pratico → `Davide · Aurya`; guide generali → `Aurya`. Mai anonimo.
11. **Zero trattini lunghi** (— e –) nel copy. Voce evocativa ma concreta.
12. **Categoria** solo se il tema mappa su RETREAT_CATEGORIES (yoga, meditazione, detox, suono, massaggio, breathwork, cammini, femminile, aziendale); altrimenti None. La categoria determina cover e articleSection.
13. **Mai inventare fatti**: strutture con nome, statistiche, citazioni. Fasce di prezzo = quelle mappate nei nostri articoli. Norme fiscali = verificare le cifre correnti PRIMA di scrivere (WebSearch) e datare l'articolo ("guida 2026").
14. **Contenuti sanitari/fiscali**: sempre disclaimer esplicito e rimando al professionista. Mai promesse di cura, mai consigli fiscali definitivi.

## 3. Come si pubblica

- **Batch da seed**: un modulo per mese (`scripts/seed_blog_articles_mN.py`, lista `ARTICLES_MN`), importato in `seed_blog_initial_articles.py`. Il seed è idempotente per slug (non tocca articoli esistenti: le modifiche admin sono al sicuro), genera le cover mancanti e pinga IndexNow.
- **Singoli**: ArticleEditor in `/admin` (cover e IndexNow automatici al publish).
- Dopo ogni batch in produzione: verificare `https://aurya.life/api/public/sitemap-articles.xml` e un articolo a campione (`curl | grep articleBody`).

## 4. Link building (budget zero, in ordine di priorità)

1. **Badge fondatori**: "Prenotabile su Aurya" sui siti degli operatori (link a tema, in ingresso, naturale). Offrirlo nel programma fondatori.
2. **Directory di settore**: OlisticMap (gratuita), ItaliaOlistica, Trustpilot. Un giro solo, fatto bene.
3. **Digital PR della storia**: pitch a media benessere e startup (la coppia operatrice olistica + tecnologo che costruisce "la casa dei ritiri").
4. **Guest post**: 1/mese su blog di settore, in cambio di visibilità reciproca. Mai comprare link.
5. **Osservatorio Aurya** (quando i dati ci sono): il report annuale è il magnete di backlink definitivo.

## 5. GEO / LLM optimization (come gli assistenti AI ci leggono)

- Il contenuto INTEGRALE di ogni articolo è nel JSON-LD (`articleBody`): i crawler AI senza JS lo leggono dall'HTML iniziale.
- `llms.txt` presenta il sito e le guide di riferimento: aggiornarlo quando nascono nuovi pilastri.
- Lo stile "risposta diretta + onestà + numeri veri" è esattamente ciò che i motori generativi citano: ogni FAQ ben scritta è una potenziale risposta citata con fonte Aurya.
- robots.txt NON blocca i crawler AI (scelta deliberata: vogliamo essere la fonte).
- Frasi auto-contenute e attribuibili ("In Italia un weekend di ritiro parte da 250-400 euro") sono più citabili di giri di parole: scrivere pensando alla frase che l'assistente estrarrà.

## 6. ⚠️ AL LANCIO UFFICIALE: la sostituzione dei riferimenti pre-lancio

Gli articoli scritti in pre-lancio contengono pattern da sostituire
quando PRELAUNCH_MODE viene spento. Censimento (2026-07-11): TUTTI i 19
articoli hanno 1 CTA landing + 0-2 frasi pre-lancio. I pattern esatti:

| Pattern attuale | Sostituzione al lancio |
|---|---|
| `[raccontaci cosa cerchi](/cerca-ritiro)` e varianti | link alla directory pertinente: `/ritiri`, `/ritiri/{categoria}` o `/destinazioni/{luogo}` |
| `[Presentati qui](/per-operatori)` (articoli B2B) | resta valido (la landing operatori sopravvive al lancio) ma il copy "entrano da fondatori" va aggiornato quando il programma fondatori chiude |
| "al lancio ti proporremo…" / "al lancio riceverai…" | "esplora i ritiri su Aurya" / link diretto alla directory |
| "stiamo riunendo…" / "stiamo costruendo…" / "sta per aprire" | presente: "su Aurya trovi…" / "Aurya riunisce…" |

Procedura: uno script di riscrittura sui contenuti in DB (o passata
manuale dall'ArticleEditor, ~19 articoli), da eseguire NELLO STESSO
giro del lancio (wipe campioni + flag OFF + redeploy). Aggiungere al
piano di lancio. I nuovi articoli scritti da qui al lancio devono
limitare le frasi pre-lancio alla SOLA chiusura CTA (mai nel corpo),
così la sostituzione resta meccanica.

## 7. Categorie di posizionamento a lungo termine (la mappa)

In ordine di attivazione (dettagli nel piano editoriale, sez. onde):

1. **Ritiri + regioni** (attivo): ritiri olistici/yoga/meditazione + Toscana, Puglia, Umbria, Sicilia… → directory programmatica al lancio
2. **Discipline** (attivo): glossario completo → futuri hub /discipline/{slug}
3. **B2B operatori** (attivo): promozione, prezzi, fiscalità, normativa → lead fondatori
4. **Benessere psicofisico** (attivo con pilastro): stress, sonno, ansia con onestà scientifica
5. **Local** (post-lancio): "vicino a Milano/Roma", disciplina×città
6. **Venue/strutture** (post-lancio): il terzo lato del marketplace
7. **Stagionali** (ricorrente, +3 mesi di anticipo): capodanno, estate, regali
8. **Osservatorio dati** (6-12 mesi post-lancio): report annuale
9. **Inglese** (fase 3): yoga retreat Italy, hreflang già pronto

## 8. Routine di monitoraggio

- **Quindicinale**: GSC (impression, click, posizione sulle 20 keyword sentinella), page_views first-party per canale search, conversione articolo→lead. Query inattese che spingono → accelerare quel cluster.
- **Mensile**: nuovi backlink, articoli fermi (rinforzare title + link interni), un articolo vecchio aggiornato (freshness).
- **Al cambio anno**: aggiornare gli articoli datati ("guida 2026" → verificare numeri fiscali/prezzi e ridatare).
- **Regola d'oro finale**: prima i pilastri del cluster corrente, poi il cluster nuovo. La review GSC decide, non l'entusiasmo.
