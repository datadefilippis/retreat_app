# SEO — Perché siamo a zero, e il piano per scalare (25 agosto 2026)

Ruolo: senior SEO. Domanda del founder: «live da settimane, zero
impression, zero query in Search Console — com'è possibile con tutto
il contenuto che abbiamo?». Tutto ciò che segue è **misurato sul sito
vivo** (curl come Googlebot, indici pubblici), non dedotto.

---

## 1. La diagnosi in una riga

**Il Magazine è tecnicamente sano e Bing infatti ci ha già in indice.
Google no — perché siamo un dominio di 6 settimane con ZERO backlink,
e le uniche pagine che potrebbero convincerlo (home e pagine
d'ingresso) gli arrivano VUOTE.** Lo zero assoluto non è un mistero:
è la combinazione «nessun segnale esterno + porta d'ingresso muta».
Nessuna penalità, nessun blocco catastrofico: un motore freddo, mai
acceso, con il cavo d'alimentazione (i link esterni) non collegato.

---

## 2. Cosa ho verificato sul sito vivo (25/8)

### ✅ In salute (il lavoro di agosto HA funzionato)

| Cosa | Stato misurato |
|---|---|
| 47 articoli | **corpo completo nell'HTML** (9.257 caratteri visibili su /blog/reiki…), identico per Googlebot e browser (no cloaking), 0,35s di risposta |
| Hub /blog | SSR con **47 link** agli articoli: il grafo di crawl esiste |
| Sitemap | indice + 3 sotto-sitemap corrette: 47 articoli + 15 categorie + 12 core |
| Canonical / hreflang articoli | puliti (`it` + `x-default`, coerenti col solo-italiano) |
| robots.txt | permette le pagine, dichiara la sitemap |
| og:type | `article` sugli articoli ✓ |
| llms.txt | aggiornato, phase-aware, racconta la fase rete ✓ |
| IndexNow | chiave viva (200) — ed è il motivo per cui **Bing ci ha già indicizzati** (verificato via DuckDuckGo: home, /blog, articoli presenti) |
| Redirect | http→https e www→apex corretti (nessun problema di proprietà GSC frammentata) |
| JSON-LD | BlogPosting + FAQPage + BreadcrumbList sugli articoli |

### ❌ I blocchi trovati

**B1 — Le pagine d'ingresso sono VUOTE per i crawler (P0).**
Misurato: home = **46 caratteri** («You need to enable JavaScript…»).
Stessa cosa per `/operatori`, `/manifesto`, `/chi-siamo`. La home è la
pagina con più PageRank potenziale del sito e non dice NIENTE a Google:
né chi siamo, né che esiste un Magazine, né un solo link agli articoli.
Il rendering JS di seconda ondata esiste, ma su un dominio senza storia
Google lo centellina — e comunque (vedi B2) da noi fallirebbe.

**B2 — robots.txt blocca `/api/` (P0, aggrava B1).**
Le pagine non-SSR caricano i contenuti da `/api/public/…`. Il robots
dice `Disallow: /api/` (con la sola eccezione delle sitemap). Quando
Google prova a renderizzare la home col suo browser, le chiamate ai
contenuti vengono **bloccate dal nostro stesso robots** → anche la
seconda ondata produce una pagina vuota. Il combinato B1+B2 significa:
per Google la home non ha contenuto IN NESSUN MODO.

**B3 — Zero backlink (P0 strategico, il vero tetto).**
Dominio registrato ~luglio, contenuti live dal 6/8. Nessun link
esterno da nessun dominio. Google scopre il sito SOLO dalla sitemap,
non ha un solo segnale di fiducia terzo, e per un dominio così il
comportamento standard è: crawl lento, indicizzazione parziale
(«Discovered – currently not indexed»), ranking oltre pagina 5 →
**zero impression è l'esito atteso**, non un'anomalia. Le impression
si contano solo quando l'utente VEDE la pagina di risultati in cui
compari: in posizione 60 non esisti nemmeno come impression.

**B4 — Sporcizia nell'indice (P1).**
`/login` è indicizzabile (e su Bing è GIÀ in indice). Le pagine
app-only (login, /accedi, /account, aree Sound riservate) diluiscono
il crawl e fanno brutta vetrina in SERP.

**B5 — hreflang bugiardo sull'hub (P2).**
La sitemap dichiara per `/blog` alternate `en/de/fr` via `?lang=` che
servono contenuto identico in italiano. Segnale incoerente con la
decisione solo-italiano: rumore, non danno grave.

**B6 — Zero domanda brand (contesto, non bug).**
Nessuno cerca «aurya»: non c'è marketing, non c'è stampa. Anche le
impression brand — le prime ad apparire per qualsiasi sito nuovo —
non hanno un bacino da cui nascere.

---

## 3. FASE 0 — La verifica che posso fare solo con te (15 min, OGGI)

Prima di toccare codice, in Search Console (proprietà `aurya.life`):

1. **Indicizzazione → Pagine**: quante «indicizzate»? Quante in
   «Rilevata, ma attualmente non indicizzata» / «Scansionata, ma…»?
   Questo numero decide tutto: se indicizzate ≈ 0, la diagnosi sopra è
   confermata al 100%.
2. **Controllo URL** su 3 indirizzi: la home, `/blog`,
   `/blog/reiki-cose-come-funziona-una-sessione`. Per ciascuno:
   «URL su Google?» e, se no, il motivo dichiarato.
3. **Sitemap**: stato «Riuscita» e «Pagine trovate» ≈ 74?
4. **Sicurezza e azioni manuali**: deve dire «Nessun problema» (me lo
   aspetto, ma va escluso).
5. Cerca su Google `site:aurya.life` e dimmi quanti risultati vedi.

Con questi 5 dati il piano sotto si conferma o si corregge. Non serve
altro da parte tua per la fase tecnica.

---

## 4. Il piano — quattro fronti in ordine di leva

### FRONTE A — Aprire la porta a Google (io, questa settimana, locale)

| Passo | Cosa | Perché |
|---|---|---|
| A1 | **SSR delle pagine d'ingresso**: home, /manifesto, /chi-siamo, /operatori, /newsletter — contenuto reale nel body via SEO shell (stesso pattern già vivo sugli articoli), con **link agli articoli di punta dalla home** | La pagina più forte del sito deve presentare il sito e irrorare il Magazine di link interni |
| A2 | **robots.txt**: `Allow: /api/public/` prima del `Disallow: /api/` | La seconda ondata di rendering smette di fallire per mano nostra |
| A3 | **noindex sulle rotte app-only**: /login, /accedi, /account*, /sound/crea, /benvenuto, ecc. (X-Robots-Tag nella shell) | Fuori la sporcizia dall'indice, crawl budget al contenuto |
| A4 | **hreflang solo dove è vero**: via gli alternate en/de/fr dall'hub blog | Coerenza col solo-italiano |
| A5 | **«In breve» in testa agli articoli**: 3-4 frasi fattuali SSR (già scrivibili dal contenuto esistente) | È il blocco che AI Overview, Perplexity e ChatGPT citano; migliora anche il featured snippet |
| A6 | Guardie: «la home serve ≥N caratteri ai crawler», «/login ha noindex», «robots permette /api/public/» | Che non regredisca mai in silenzio — come per gli articoli |

### FRONTE B — Riscaldare l'indice (tu+io, subito dopo il deploy di A)

1. GSC → Controllo URL → **«Richiedi indicizzazione»** su: home,
   /blog, mappa delle discipline, e i 10 articoli a maggior potenziale
   (elenco pronto: reiki, yoga nidra, breathwork, costi, ATECO…).
   È l'unico acceleratore manuale legittimo che esiste.
2. **Bing Webmaster Tools**: importa la proprietà da GSC (2 click).
   Bing già ci indicizza; con la console misuriamo anche lì — e Bing
   alimenta ChatGPT/Copilot, che per la visibilità AI conta quanto
   Google.
3. Ricarica la sitemap in GSC dopo il deploy (lastmod si aggiorna).

### FRONTE C — L'autorevolezza: il vero motore (90 giorni, tu+io)

Senza link esterni tutto il resto è ottimizzare un'auto senza benzina.
In ordine di resa per sforzo:

| # | Azione | Nota |
|---|---|---|
| C1 | **Il volano dei professionisti intervistati** — ogni operatore che entra nella rete linka il proprio profilo Aurya dal suo sito/Instagram («Profilo verificato su Aurya» — badge già esistente, farne uno embeddabile con link) | È IL nostro asset strutturale: ogni intervista = 1 backlink tematico da un sito del settore. Nessun competitor-elenco può replicarlo |
| C2 | **Directory e registri legittimi del settore** (Italia Olistica, portali regionali benessere, elenchi associazioni CONACREIS/altre dove ammesso) | 5-10 link facili, tematici, puliti |
| C3 | **Digital PR sui dati che ABBIAMO già**: l'articolo costi diventa l'«Osservatorio prezzi del benessere olistico in Italia» — un numero citabile che nessuno pubblica; pitch a testate benessere/lifestyle e newsletter di settore | I giornalisti linkano i numeri, non le opinioni |
| C4 | **Profili social del brand attivi** + `sameAs` nell'Organization schema (predisposto, mancano gli URL) | Knowledge Graph + segnale d'esistenza |
| C5 | **2-3 guest post / interviste al founder** su blog di settore (la storia «piattaforma che verifica i professionisti uno a uno» è notiziabile di suo) | Link in profondità + domanda brand |
| C6 | La **Lettera** cita e viene citata: scambi di menzione con newsletter affini (non link scheme: menzioni editoriali reali) | Traffico diretto → segnali utente |

Obiettivo misurabile: **15-20 referring domain tematici in 90 giorni.**
Da lì Google ha una ragione per prenderci sul serio.

### FRONTE D — Contenuto e AI-readability (ritmo, non sprint)

1. **Ritmo 2 articoli/mese** (deciso e giusto) — priorità ai filoni
   già impostati: guida-del-consumatore e professione B2B (ogni
   lettore B2B è un lead della rete).
2. **Refresh trimestrale**: quando GSC comincerà a dare query, i pezzi
   in posizione 11-20 si aggiornano PRIMA di scriverne di nuovi.
3. **llms-full.txt**: indice completo con riassunto per articolo
   (llms.txt già buono; la versione full è ciò che i crawler AI
   preferiscono ingerire).
4. **«In breve» + dati con fonte linkata** in ogni articolo nuovo: il
   formato che le risposte AI citano.
5. Niente da cambiare nella voce: lo standard narrativo È l'arma.
   (E niente scorciatoie: keyword stuffing, link comprati, contenuti
   AI-generici — su un dominio giovane sono la via più rapida per un
   filtro.)

---

## 5. Aspettative oneste (così misuriamo senza illuderci)

| Quando | Cosa è realistico |
|---|---|
| Giorni 0-14 | Pagine indicizzate salgono (da ~0 a decine). PRIMA metrica da guardare: «indicizzate» in GSC, non le impression |
| Giorni 30-60 | Prime impression su coda lunghissima («domande da fare prima di un ritiro», «codice ateco operatore olistico») e prime query brand se parte C4/C5 |
| Giorni 60-90 | Primi click; 1-2 articoli in pagina 1-2 su query a bassa concorrenza (filone B2B/costi, dove i big non giocano) |
| 6 mesi | Con 15-20 referring domain: competizione vera sulle query «come scegliere / quanto costa»; le query grosse («reiki cos'è») restano una guerra di anni contro DA 80+ — le aggiriamo, come da strategia di agosto |

KPI in scala, in quest'ordine: **pagine indicizzate → impression →
click → lead** (Lettera + candidature professionisti). Report mensile.

---

## 6. Sequenza operativa proposta

1. **Oggi**: tu fai la FASE 0 (5 letture in GSC) e mi dici i numeri.
2. **Questa settimana**: io implemento il FRONTE A in locale (guardie
   comprese), deploy al tuo ok, poi FRONTE B insieme (30 min).
3. **Da subito e per 90 giorni**: FRONTE C — C1 si innesta nel flusso
   interviste esistente; C2-C5 calendarizzati, una azione a settimana.
4. **Ritmo**: FRONTE D come abitudine, report GSC mensile.
