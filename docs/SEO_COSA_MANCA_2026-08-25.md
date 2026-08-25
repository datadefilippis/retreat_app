# SEO — Cosa manca davvero, dopo l'audit del 25 agosto (sera tardi)

Domanda: *«manca ancora qualcosa del piano SEO per scalare?»*
Risposta: **sì, tre cose mie e tre tue.** Ma non sono più i buchi
grossi: quelli sono chiusi. Quello che resta è rifinitura di alto
valore e — soprattutto — il lavoro che nessun codice può fare.

---

## Cosa è stato chiuso oggi (tutto in produzione)

| | Prima | Ora |
|---|---|---|
| Home ai crawler | 46 caratteri **inglesi** | 3.610 caratteri + link agli articoli |
| Profili professionisti | 46 caratteri | 547-757 caratteri, in sitemap |
| `/esplora-operatori` | vietata ai crawler | indicizzata, 4 professionisti, canonical su sé stessa |
| `/esplora-ritiri` | vietata, piena di ritiri finti | pulita, `noindex` finché vuota, **si accende da sola** |
| Ritiri e operatori finti | 6 org + 10 ritiri inventati | **rimossi** (backup prima) |
| Compressione | assente, 2 MB di JS in chiaro | gzip: JS −72%, CSS −84% |
| Cache media | `no-cache` su tutto (video 1,6 MB) | 7 giorni |
| Link interni per articolo | 2 su 47 | 6 |
| `llms-full.txt` | 404 | 47 articoli interi |
| Rotte app (`/login`, `/inizia`…) | indicizzate **al posto** degli articoli | `noindex` |
| robots | bloccava il rendering di Google | `Allow: /api/public/` |
| `/esplora-operatori` linkata | **da nessuna pagina** | home, `/operatori`, ogni profilo |
| IndexNow | — | 12 URL segnalati stasera |

---

## Quello che manca — mio

### M1 · «In breve» in testa a ogni articolo — *il pezzo che manca per gli LLM*

Le risposte AI (Google AI Overview, Perplexity, ChatGPT) citano
**paragrafi auto-contenuti** all'inizio del testo. I nostri articoli
aprono con una scena narrativa: bellissima per chi legge, poco
estraibile per una macchina. Un blocco di 3-4 frasi fattuali in testa —
server-side, visibile — è oggi il singolo intervento con più resa sulla
visibilità AI, che per un dominio giovane è il canale dove si può
essere letti **subito** invece che fra mesi.

Serve un campo nuovo sull'articolo. Posso generare una prima stesura da
ogni pezzo e passarla alla redazione: la riscrittura resta vostra.

### M2 · I link alle fonti — *E-E-A-T che stiamo regalando*

Verificato: **zero link esterni** in 47 articoli. Gli studi (JAMA,
Nature, Cochrane, Britton) sono nominati nel testo e mai linkati. Il
link alla fonte primaria è il segnale di competenza più economico che
esista, ed è esattamente ciò che distingue un contenuto «helpful» da un
contenuto generico agli occhi di Google.

È una passata editoriale: preparo l'elenco articolo per articolo (quale
studio, quale URL ufficiale) e tu approvi prima che tocchi i testi.

### M3 · I 6 title che si troncano

Sei titoli superano i 60 caratteri e vengono tagliati in SERP, dove il
titolo è l'unica cosa che decide se ti cliccano. L'H1 narrativo resta
com'è: si cambia solo il title. Ti propongo le riscritture.

---

## Quello che manca — tuo, e vale più di tutto il resto

### T1 · I backlink — *il tetto di vetro*

Zero domini ci linkano. Con zero backlink, ogni ottimizzazione tecnica
è un'auto perfetta senza benzina. **Ora però il volano è pronto**: i
quattro profili parlano ai crawler e sono in sitemap, quindi chiedere a
Valentina, Ilaria, Claudia e Claudia di linkare il proprio profilo
Aurya dal loro sito o dalla bio Instagram ha finalmente senso — fino a
stamattina li avremmo mandati su pagine mute.

Obiettivo realistico: 15-20 domini in 90 giorni, tra profili dei
professionisti, directory di settore e una digital PR sui dati dei
costi.

### T2 · Search Console e Bing (30 minuti)

«Richiedi indicizzazione» su: home, `/blog`, `/esplora-operatori`, i 4
profili, i 10 articoli di punta. Poi importa la proprietà in Bing
Webmaster Tools — Bing ci indicizza già, e alimenta ChatGPT e Copilot.

### T3 · Due decisioni piccole

1. **Mettere «Professionisti» nel menu** puntando a
   `/esplora-operatori`: oggi è indicizzabile e linkata da tre pagine,
   ma non è una voce di navigazione. Chi arriva sul sito non la trova.
2. **Goccia di Luna e Metodo Oltre** non hanno uno slug pubblico:
   esistono nella rete ma non sul web. Assegnarlo o decidere che non
   entrano ora.

E se vuoi: gli **URL social** di Aurya, per dichiararli nell'entità
Organization (`sameAs`) e agganciare il Knowledge Graph.

---

## Due difetti noti che ho scelto di NON toccare oggi

**Soft-404.** Un URL inventato (`/pagina-inventata`) risponde 200 e la
SPA riporta l'utente alla home. Google lo classificherà come «soft
404»: spreca un po' di crawl budget e comparirà in Search Console.
Sistemarlo davvero significa far passare **tutte** le rotte dal
renderer server-side, incluse quelle dell'app: se ne dimentico una, si
rompe una pagina vera del gestionale. Con quattro operatori live il
rapporto rischio/beneficio non torna. Da fare quando c'è tempo per
verificarle una per una.

**Il video dell'hero (1,6 MB).** Si carica dopo l'evento `load` e ora
resta in cache una settimana, quindi non pesa sul primo disegno. Ma
resta il file più grosso del sito. Se un giorno vorrai spingere i Core
Web Vitals, la mossa è servirlo solo su desktop e connessioni veloci.

---

## L'ordine che consiglio

1. **Tu, questa settimana**: Search Console + Bing (30 min), la voce di
   menu, e la richiesta di link ai quattro professionisti.
2. **Io, quando dici**: M1 «In breve» (visibilità AI), poi M2 le fonti,
   poi M3 i title.
3. **Poi si misura**: pagine indicizzate → impression → click. Il primo
   numero da guardare fra due settimane è «indicizzate» in GSC, non le
   impression: è quello che dice se la porta si è davvero aperta.
