# SEO — Audit profondo e piano operativo (4 agosto 2026)

Ruolo: senior SEO. Obiettivo: scalare i motori di ricerca con il Magazine
come motore, in fase rete (niente marketplace attivo). Tutto verificato
sul sito reale in locale; le voci di ricerca esterna citano le fonti.

---

## 1. Verdetto in tre righe

Le fondamenta on-site sono sopra la media (JSON-LD ricco, sitemap onesta,
canonical/hreflang corretti, 55.000 parole senza orfani). Il difetto
capitale è UNO: **il corpo degli articoli non è nell'HTML** — i crawler
ricevono un body vuoto. Finché non si corregge, stiamo correndo con il
freno a mano tirato; corretto quello, la partita si gioca su contenuti
(dove siamo già forti) e autorevolezza (dove siamo a zero: dominio nuovo,
zero backlink).

---

## 2. Audit tecnico — cosa ho verificato

### 2.1 CRITICO — body vuoto per i crawler (P0)

`GET /__seo/blog/<slug>` serve head perfetto (title, description,
canonical, hreflang it+x-default, OG, BlogPosting con articleBody,
BreadcrumbList, FAQPage) ma il body è:

    <body><noscript>…</noscript><div id="root"></div></body>

Misurato: 108 byte di body visibile. Le conseguenze:
- Google indicizza via rendering JS (seconda ondata): più lento, più
  costoso in crawl budget, meno affidabile su un dominio senza storia.
- Bing e i motori AI (Perplexity, GPTBot, ClaudeBot, Amazonbot) spesso
  NON eseguono JS: per loro i nostri articoli sono pagine vuote con
  buoni metadati. In un'epoca in cui le risposte AI citano fonti, è
  traffico e autorevolezza regalati ad altri.
- L'articleBody nel JSON-LD NON sostituisce il contenuto visibile ai
  fini del ranking.

**Fix**: la shell (`routers/seo_shell.py`) renderizza già i metadati
server-side; va estesa a renderizzare il CONTENUTO markdown→HTML dentro
`<div id="root">` (stesso subset del renderer legale: h2/h3, paragrafi,
liste, grassetti, link). React monta sopra e sostituisce — pattern
standard. Vale per: articoli, hub /blog, pagine categoria (lista
articoli come HTML), e in misura minore manifesto/chi-siamo/landing
(meno critici: pagine di brand, non di ranking).

### 2.2 llms.txt stantio (P1)

`/llms.txt` racconta la fase MARKETPLACE («prenotare ritiri… caparra…
gestionale gratuiti, commissione»). È la vetrina per i crawler AI e
dice cose oggi false. Va riscritto phase-aware: fase rete = spazio
editoriale + rete di professionisti raccontati, con l'indice dei
33 articoli (llms.txt supporta liste di link con descrizione — è
esattamente il nostro caso d'uso).

### 2.3 Rifiniture on-page (P2)

- `og:type` = "website" sugli articoli → deve essere "article" +
  `article:published_time` / `article:modified_time`.
- `datePublished` nel JSON-LD senza timezone ("2026-07-27T16:19:44.647000")
  → aggiungere +00:00 (Google lo tollera ma la validazione lo segnala).
- 11 title sopra i 60 caratteri (prima del suffisso "| Aurya" che
  aggiunge 8): rischio troncamento in SERP. Elenco: rebirthing (69),
  differenze-tipi-di-yoga (74), breathwork (71), digiuno (68),
  costellazioni (65), + 6 tra 61-63. Da riscrivere tenendo la keyword
  primaria nei primi 50 caratteri.
- Sitemap/robots: GIÀ SISTEMATI (LC1) — indice phase-aware, 46 URL
  del Magazine, sotto-sitemap commerciali vuote in rete.

### 2.4 Fuori dal codice (P1, richiede il founder)

- **Google Search Console**: verifica proprietà ancora in sospeso
  (nota di luglio). Senza GSC siamo ciechi: niente query report,
  niente stato indicizzazione, niente segnalazione problemi. È il
  prerequisito di TUTTA la misura.
- Bing Webmaster Tools: import da GSC in un click; con IndexNow già
  implementato (SEO2c) Bing recepisce i publish in ore.
- GA4 è già attivo con Consent Mode v2 (GA1).

---

## 3. Audit contenuti — lo stato del Magazine

**I numeri** (misurati sul DB): 33 articoli, ~55.000 parole, media
1.660 parole/articolo (min 1.070, max 2.742). Ogni articolo: 6-13 H2,
description 113-148 caratteri (tutte presenti, tutte nel taglio),
2-11 link interni in uscita, ZERO articoli orfani. 12 cluster tematici,
FAQPage su ogni articolo, cover WebP autogenerate distinte.

**Qualità**: lo standard narrativo (scena in apertura, pratiche guidate
cosa-fai/cosa-senti/cosa-va-storto, dati veri con fonte, niente promesse
di guarigione) è ESATTAMENTE ciò che Google chiama "helpful content" e
che i competitor enciclopedici non hanno. Questa è la nostra arma.

**I gap**:
1. **E-E-A-T debole**: autore = "Aurya" (Organization) senza volto;
   le fonti citate (Britton, JAMA Psychiatry, Carlson/Nature) sono
   nominate nel testo ma NON linkate — un link alla fonte primaria è
   il segnale di competenza più economico che esista. Manca un blocco
   "chi scrive" che colleghi l'articolo a /chi-siamo.
2. **Nessuna pagina pilastro trasversale**: le categorie hub sono
   buone porte, ma manca la pagina che intercetta la query madre
   («discipline olistiche: quali sono», «operatore olistico: cosa fa»)
   e smista verso i 12 cluster.
3. **Cluster costi scoperto**: «quanto costa una seduta di reiki /
   shiatsu / un ritiro» — intento fortissimo, pre-transazionale,
   quasi scoperto nelle SERP italiane (i competitor enciclopedici non
   parlano di prezzi). Noi abbiamo già la voce giusta per farlo
   (trasparenza, niente vendita).
4. **Cluster professione B2B sottile**: abbiamo partita-iva e
   promozione; mancano «codice ATECO operatore olistico»,
   «assicurazione RC operatore olistico», «legge 4/2013 spiegata».
   Concorrenza bassissima, e ogni lettore è UN LEAD del funnel
   professionisti — il funnel che conta adesso.

---

## 4. Il campo di gara — query e concorrenti

### 4.1 Query informazionali «X cos'è / come funziona / benefici»

Chi occupa le SERP (verificato su «reiki cos'è»): LifeGate, Starbene,
Melarossa, EventiYoga, dottoremaeveroche.it (debunking), verticali come
ilreiki.it. Sopra tutti, per il benessere generalista:
my-personaltrainer.it (16M utenti/mese), cure-naturali.it, starbene.it —
siti costruiti al 99,6% su query informazionali, DA altissima.

**Lettura strategica**: non li battiamo frontalmente su «reiki cos'è»
nel breve. Li aggiriamo su un intento che NON coprono: la **guida del
consumatore** («cosa aspettarsi dalla seduta», «come scegliere», «le
domande da fare», «quanto costa», «bandiere rosse») — più vicino alla
decisione, meno presidiato, perfettamente allineato al brand «ci si
fida di qualcuno». I nostri articoli sono GIÀ tagliati così: è la
strategia giusta, va spinta, non cambiata.

### 4.2 Query ritiri

Chi c'è: EventiYoga (aggregatore eventi), Zorba il Buddha, Santosha,
Alberi Maestri (strutture singole ben posizionate), WeRoad (viaggi),
Italia Olistica, più gli internazionali (BookRetreats, Tripaneer).
In fase rete non vendiamo ritiri: presidiamo il territorio con contenuti
(«come scegliere un ritiro», «quanto costa un ritiro», «cosa portare»)
che al flip marketplace diventano il funnel d'acquisto già indicizzato.

### 4.3 Concorrenti directory/rete (i più vicini a noi)

Italia Olistica (operatori + scuole + viaggi), cure-naturali.it/operatori,
e i registri di categoria (CONACREIS, R.E.O.O., RIMOI, ANPICOF, UNI-PRO).
Tutti hanno elenchi; NESSUNO ha profili raccontati con interviste
verificate. La nostra differenziazione SEO al riempirsi della rete:
profili /o/ con Person/LocalBusiness schema, contenuto biografico unico
(l'intervista) e il badge come provenienza — pagine che nessun elenco
può replicare.

### 4.4 Motori AI

Le risposte AI (Google AI Overview, Perplexity, ChatGPT) pescano da
fonti leggibili senza JS e ben strutturate. Con SE1 (contenuto nel
body) + SE2 (llms.txt onesto) + FAQPage già presente diventiamo
citabili; oggi non lo siamo.

---

## 5. Piano operativo — ciclo SE (in ordine di leva)

| Passo | Cosa | Perché prima |
|-------|------|--------------|
| SE1 | **SSR del contenuto** nella shell: articoli (markdown→HTML nel body), hub /blog e categorie (liste come HTML); og:type article; timezone date; guardie «il body contiene l'articolo» | Il freno a mano: ogni altro sforzo rende di più dopo questo |
| SE2 | **llms.txt phase-aware** con indice del Magazine; verifica robots per i crawler AI | Vetrina per i motori AI, oggi racconta un sito che non esiste |
| SE3 | **GSC + Bing** (founder): verifica proprietà, submit sitemap, baseline query. Io preparo la checklist e i meta tag di verifica | Senza misura non c'è iterazione |
| SE4 | **Title pass**: 11 title >60 riscritti, keyword nei primi 50 caratteri, H1 può restare narrativo (title SEO ≠ H1) | 30 minuti di lavoro, CTR in SERP |
| SE5 | **E-E-A-T pass**: link alle fonti primarie citate (JAMA, Nature…), blocco «chi scrive» → /chi-siamo, author markup coerente, «aggiornato il» visibile | Il segnale di fiducia più economico disponibile |
| SE6 | **Espansione contenuti** (8-10 articoli, standard narrativo esistente): filone costi («quanto costa una seduta di reiki/shiatsu/naturopatia», «quanto costa un ritiro»), filone professione («codice ATECO», «assicurazione RC», «legge 4/2013»), filone ritiri consumer («come scegliere un ritiro», «cosa portare») | Cluster a bassa concorrenza e alto intento; il filone professione genera lead operatori |
| SE7 | **Pagina pilastro** «Le discipline olistiche: la mappa» (la parola del brand: «Questa è la mappa») che smista ai 12 cluster + intro categorie arricchite | Intercetta le query madre e concentra il link interno |
| SE8 | **Autorevolezza off-site** (con il founder): profili social del brand (sameAs nel Knowledge Graph, già predisposto), presenza nelle directory legittime del settore, prime relazioni con siti/newsletter del settore | Il tetto di vetro: senza backlink i DA alti restano irraggiungibili sulle query grosse |
| SE9 | **Ritmo e misura**: report mensile GSC (query, impression, posizioni), 2 articoli/mese a regime, refresh dei pezzi che entrano in pagina 2 | La SEO è un'abitudine, non un progetto |

Dipendenze: SE3 e SE8 richiedono te; tutto il resto è implementabile da
me in locale con il pattern soliti (script idempotenti, guardie, commit
per passo, deploy solo su tuo ok).

## 6. Cosa NON fare (esperienza, non prudenza)

- Niente keyword stuffing né titoli-esca: la voce del brand È il
  vantaggio competitivo, Google la premia da Helpful Content in poi.
- Niente traduzioni ×4 per «più mercati»: dominio nuovo, forza va
  concentrata sull'italiano (decisione solo-italiano già presa: giusta
  anche per la SEO).
- Niente link building comprata: su un dominio giovane è il modo più
  rapido per farsi filtrare.
- Niente contenuti «migliori X» con classifiche finché la rete è vuota:
  promettere elenchi che non abbiamo è il rimbalzo assicurato.
