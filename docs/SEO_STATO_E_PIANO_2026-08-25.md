# SEO — Stato reale e piano per scalare (25 agosto 2026, sera)

Scritto dopo il deploy GS1-GS7 e dopo aver ispezionato la **produzione
vera** (HTML servito ai crawler, database, header di rete). Sostituisce
come fotografia il piano di stamattina, che resta valido nella
strategia.

---

## PARTE 1 — La tua domanda: «network_member = 0, i profili non si
## indicizzano? Ma c'è la pagina esplora operatori»

### Sono due pagine diverse, e nessuna delle due mostra i professionisti veri

| | `/operatori` | `/esplora-operatori` |
|---|---|---|
| Cos'è | la **landing della rete**, fase network | anteprima del marketplace, «deliberatamente non linkata» (tua richiesta del 29/7) |
| In sitemap | sì | no |
| Crawler | **permessa** | **VIETATA** — `robots.txt` dice `Disallow: /esplora-` |
| Chi mostra | i membri della rete (`network_member = true`) | chi ha prodotti prenotabili (gate marketplace) |
| Oggi mostra | **nessuno** (0 membri) | **i 6 SAMPLE seedati**, cioè Masseria degli Ulivi, Rifugio del Bosco, Cascina Luna, Borgo del Suono, Casa Serena, Eremo del Lago |

Quindi: **la pagina che stai guardando elenca sei organizzazioni finte**
messe lì come campioni di prova, ed è la pagina che abbiamo chiesto a
Google di ignorare.

### Le persone vere che hai in produzione

Su 13 organizzazioni: 6 sono sample, 1 è Aurya stessa (esclusa dagli
elenchi). Restano **6 professionisti reali**:

| Nome | Profilo | Stato |
|---|---|---|
| Brillare \| Il Sole Dentro ~ Valentina | `/o/brillare-il-sole-dentro` | vivo, ora 757 caratteri ai crawler |
| Ilaria | `/o/ilaria` | vivo, 597 caratteri |
| Rigveda di Claudia Cannatà | `/o/rigveda-di-claudia-cannata` | vivo, 547 caratteri |
| a.s.d. sport life dolomiti | `/o/a-s-d-sport-life-dolomiti` | vivo |
| Goccia di Luna | — | **nessuna pagina pubblica** (manca lo slug) |
| Metodo Oltre | — | **nessuna pagina pubblica** (manca lo slug) |

### La risposta precisa

Le pagine profilo **esistono e rispondono**. Da stasera **parlano**
anche ai crawler (prima erano 46 caratteri: era il difetto GS7 che ho
chiuso poche ore fa). Ma **Google non ha modo di scoprirle**: non sono
in nessuna sitemap, e nessuna pagina indicizzabile le linka. Un motore
trova le pagine solo per link o per sitemap; una pagina che esiste ma
non è raggiungibile, per lui non esiste.

Il flag `network_member` è la chiave che apre entrambe le porte: mette
il profilo **nella sitemap-operators** e **nel corpo di `/operatori`**
(dove ora ho messo i link veri). Marcarli è un'azione da system admin,
due minuti, e accende quattro pagine di qualità — le uniche pagine che
nessun elenco di categoria può replicare.

**Da decidere con te**: `/esplora-operatori` oggi mostra sei nomi
inventati. In fase rete è una pagina che promette un marketplace
spento. O si spegne, o si riempie di veri: tenerla così è l'unica cosa
che, se qualcuno ci arriva, fa male al brand.

---

## PARTE 2 — Stato SEO al 25 agosto, misurato

### Riparato oggi (in produzione, tag `prod-2026-08-25`)

| | Prima | Ora |
|---|---|---|
| Home ai crawler | 46 caratteri, **in inglese** | 3.610 caratteri, 8 link ad articoli |
| Profili professionisti | 46 caratteri | 547-757 caratteri |
| `/operatori`, `/manifesto`, `/chi-siamo`, `/newsletter`, `/entra-nella-rete` | 46 caratteri | corpo con h1 e link |
| `/login` `/inizia` `/termini` `/privacy` `/account` | indicizzabili (e alcune GIÀ indicizzate) | `noindex` |
| robots | `Disallow: /api/` bloccava il rendering | `Allow: /api/public/` |
| hreflang | en/de/fr bugiardi | solo `it` + `x-default` |

### Già solido (da prima)

47 articoli con corpo SSR completo (9.257 caratteri sul Reiki),
BlogPosting + FAQPage + BreadcrumbList, sitemap corrette (62 URL
articoli), canonical puliti, `llms.txt` con tutti i 47 pezzi, IndexNow
attivo (è il motivo per cui **Bing ci indicizza già**), redirect
http→https e www→apex a posto, TTFB 0,27-0,41s.

### I difetti che restano — misurati stasera

**D1 — NESSUNA COMPRESSIONE (P0, nuovo).**
`main.js` = **2.045.088 byte serviti non compressi**, anche quando il
browser chiede `gzip, br`. Il CSS altri 189 KB. Nella conf nginx non
c'è **una sola direttiva `gzip`**. Con gzip quel bundle scenderebbe a
~500 KB: significa 1,5 MB in meno su ogni prima visita, su ogni
telefono in 4G. Impatta LCP (Core Web Vitals = segnale di ranking) e
il budget di rendering che Google spende su di noi. È il fix col
miglior rapporto minuti/risultato che ci sia.

**D2 — Profili invisibili (P0)** — vedi Parte 1: `network_member` = 0.
Azione tua, non di codice.

**D3 — Zero backlink (P0 strategico).** Invariato: nessun dominio ci
linka. È il tetto di vetro di tutto il resto.

**D4 — Zero link esterni alle fonti (P1).** Verificato sull'articolo
Reiki: 10 `<h2>`, buona struttura, ma **0 link esterni**. Gli studi
sono nominati nel testo (JAMA, Nature, Britton) e mai linkati. Il link
alla fonte primaria è il segnale E-E-A-T più economico che esista, e
oggi lo stiamo regalando.

**D5 — Link interni poveri (P1).** L'articolo Reiki linka **2** altri
articoli su 47. Il grafo interno è sottile: gli articoli non si
sostengono a vicenda, e il PageRank che arriva sulla home non si
distribuisce.

**D6 — 6 title su 12 superano i 60 caratteri (P2)**, quindi si
troncano in SERP (misurati fino a 67).

**D7 — Niente blocco «In breve» (P1 per gli LLM).** Le risposte AI
citano paragrafi auto-contenuti in testa. I nostri articoli aprono con
una scena narrativa (bellissima per l'umano, poco estraibile).

**D8 — `llms-full.txt` assente (404)** — è il formato che i crawler AI
preferiscono ingerire.

**D9 — `sameAs` vuoto**: l'Organization non dichiara profili social
(servono i tuoi URL). Nessun aggancio al Knowledge Graph.

**D10 — Due org senza pagina pubblica** (Goccia di Luna, Metodo Oltre):
sono nella rete ma non esistono per il web.

---

## PARTE 3 — Il piano per scalare

### Onda 1 — Tecnica, questa settimana (io)

| # | Cosa | Perché |
|---|---|---|
| **T1** | **gzip/brotli in nginx** su HTML, JS, CSS, JSON, XML, SVG | −75% sul primo caricamento. Il fix più economico del piano |
| T2 | **`llms-full.txt`**: indice completo con riassunto per articolo | La porta dei motori generativi |
| T3 | **Blocco «In breve»** in testa a ogni articolo (3-4 frasi fattuali), SSR e visibile | Ciò che AI Overview e Perplexity citano; migliora anche i featured snippet |
| T4 | **Link alle fonti** già citate nei 47 articoli (JAMA, Nature, Cochrane…), `rel="noopener"`, aperti in nuova scheda | E-E-A-T, a costo quasi zero |
| T5 | **Rete di link interni**: da 2 a 5-8 link per articolo, verso i pezzi dello stesso cluster + la pagina mappa | Distribuisce autorità, allunga la sessione |
| T6 | **Title pass** sui 6 lunghi (keyword nei primi 50 caratteri; l'H1 narrativo resta) | CTR in SERP |
| T7 | **Decidere `/esplora-operatori`**: spegnerla in fase rete o riempirla di veri | Oggi mostra sei nomi inventati |

### Onda 2 — Le persone (tu, questa settimana)

1. **Marca i 4 professionisti come membri della rete** dal pannello
   admin → accende `/operatori` e la sitemap.
2. **Dai uno slug pubblico** a Goccia di Luna e Metodo Oltre (o
   decidi che non entrano ora).
3. **GSC**: «Richiedi indicizzazione» su home, `/blog`, `/operatori`,
   i 4 profili e i 10 articoli di punta (ti preparo l'elenco).
4. **Bing Webmaster Tools**: import da GSC, 2 click.
5. **URL social** di Aurya → li metto in `sameAs`.

### Onda 3 — Autorevolezza, 90 giorni (insieme)

Invariata dal piano di stamattina, ed è quella che decide tutto:

- **C1 · il volano**: ogni professionista linka il proprio profilo
  Aurya dal suo sito/Instagram — badge embeddabile. **Ora ha senso
  farlo**: fino a stamattina quei profili erano pagine mute, e li
  avremmo mandati sul vuoto.
- **C2** directory e registri legittimi del settore (5-10 link).
- **C3** digital PR sui dati che già abbiamo: l'articolo costi diventa
  «Osservatorio prezzi del benessere olistico in Italia». I giornalisti
  linkano i numeri.
- **C4** profili social attivi + `sameAs`.
- **C5** 2-3 interviste al founder su blog di settore.

Obiettivo: **15-20 referring domain tematici in 90 giorni.**

### Onda 4 — Ritmo (continuo)

2 articoli/mese sui filoni scoperti (costi, professione B2B, guida del
consumatore); refresh dei pezzi che entreranno in posizione 11-20;
report GSC mensile su **pagine indicizzate → impression → click →
lead**.

---

## Cosa NON fare

Niente link comprati, niente keyword stuffing, niente traduzioni ×4
(la forza va concentrata sull'italiano), niente pagine-elenco che
promettono professionisti che non abbiamo. La voce del brand è il
vantaggio competitivo: si difende, non si diluisce.
