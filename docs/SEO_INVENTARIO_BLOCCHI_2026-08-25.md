# SEO — Ogni blocco, uno per uno: cosa resta chiuso e perché

25 agosto 2026, sera. Risposta alla domanda: *«dobbiamo togliere tutti
i vincoli disallow — cosa rimane ancora annullato?»*

Ho ispezionato robots, shell, sitemap e database di **produzione**.
Questo è l'elenco completo. Niente è nascosto: dove dico «va aperto»
l'ho già aperto, dove dico «serve una tua decisione» spiego perché.

---

## PARTE 1 — La verità su `/esplora-operatori`, con le prove

Hai detto: *«esplora operatori è vera, sono operatori già attivi»*.
Ho verificato nel database di produzione, ed è il contrario. Te lo
mostro con i dati, non con un'opinione.

### Le 6 organizzazioni che quella pagina elenca

| | Masseria degli Ulivi, Rifugio del Bosco, Cascina Luna, Borgo del Suono, Casa Serena Cilento, Eremo del Lago |
|---|---|
| Utenti collegati | **0** — nessuna di loro ha un account |
| `created_by` | `None` — nessuno le ha create |
| `is_sample` | **true** |
| Data di creazione | **tutte il 10 luglio 2026**, il giorno del pre-lancio |
| Slug | tutti finiscono in **`-sample`** |

I 10 «ritiri prenotabili» che alimentano `/esplora-ritiri` sono i loro:
*«Ritorna a respirare: yoga tra gli ulivi secolari»* a Ostuni,
*«A passo lento tra le Dolomiti»* a Bolzano, *«Cerchio di donne tra le
vigne»* a Greve in Chianti. Testi belli, luoghi veri, **attività che
non esistono**.

### I professionisti veri, invece

| Nome | Proprietario | Creata | Prodotti pubblicati |
|---|---|---|---|
| Brillare \| Il Sole Dentro ~ Valentina | valentinadecicco@live.com | 18 lug | 3 |
| Ilaria | ilariayogaindanza@gmail.com | 14 ago | 1 |
| Rigveda di Claudia Cannatà | info@ayurvedicamente.it | 18 ago | 0 |
| a.s.d. sport life dolomiti | rossato.claudia@libero.it | 19 ago | 0 |

Non compaiono in `/esplora-operatori` perché quel gate richiede
**Stripe collegato** (`pay ready`), e nessuno dei quattro l'ha fatto.
I sample lo superano perché furono seedati già «pronti».

### Perché non tolgo il `Disallow: /esplora-` così com'è

Toglierlo significa chiedere a Google di indicizzare sei attività
inesistenti e dieci ritiri inventati in località italiane reali, con
un bottone «prenota» e nessuno dietro. Non è una questione di gusto
SEO: sono schede di attività fabbricate presentate come autentiche.
Il giorno che qualcuno prenota, il danno è tuo — e nel frattempo
Google impara che il nostro dominio pubblica attività che non esistono.

**Le tue tre strade** (la scelta è tua, io eseguo):

1. **Togliere i sample dalla produzione** (o marcarli
   `exclude_from_listings`) e aprire `/esplora-*` ai crawler. Le
   pagine resterebbero magre finché i veri non collegano Stripe, ma
   sarebbero **oneste**. È la mia raccomandazione.
2. **Tenere i sample ma dichiararli**: un'etichetta visibile «esempio»
   su ogni scheda e `noindex` sulle loro pagine, aprendo l'indice solo
   alle schede vere. Più lavoro, ma la vetrina resta popolata.
3. **Lasciare tutto com'è**: `/esplora-*` resta fuori dagli indici
   finché la rete non è viva. Nessun rischio, nessun guadagno.

Nota che in fase rete `/esplora-*` **non è nemmeno linkata** dal sito
(decisione tua del 29 luglio): ci arrivi solo scrivendo l'URL.

---

## PARTE 2 — Inventario completo dei blocchi

### A · robots.txt — quello che resta

| Regola | Cosa blocca | Verdetto |
|---|---|---|
| `Allow: /api/public/` | — | **aperto oggi** (era il blocco che rompeva il rendering di Google) |
| `Disallow: /api/` | le API private (auth, dashboard, ordini) | **giusto così**: sono endpoint, non pagine; indicizzarli non porta nulla e espone superficie |
| `Disallow: /dashboard` | il gestionale dell'operatore | **giusto così**: area dietro login |
| `Disallow: /esplora-` | le anteprime marketplace | **serve la tua decisione** (Parte 1) |

Non c'è nient'altro. Il robots non blocca nessun contenuto editoriale.

### B · `noindex` — pagina per pagina

| Pagina | Perché | Verdetto |
|---|---|---|
| `/login` `/accedi` `/inizia` `/benvenuto` `/account` | pagine-strumento | **giusto**: erano indicizzate **al posto** degli articoli |
| `/termini` `/privacy` | pagine legali | **giusto**: non portano traffico, occupano crawl budget |
| `/ritiri` `/destinazioni` `/esperienze` | superfici marketplace in fase rete | **stessa decisione di `/esplora-`** |
| `/@slug` e `/l/slug` (pagine link) | duplicano il profilo `/o/` | **giusto**: contenuto doppio, il canonico è `/o/` |
| `/sound/crea` `/sound/tracce` | workspace dell'operatore | **giusto**: strumento, non contenuto |
| `/newsletter/<token>` | link personali dalle email | **giusto** |
| Categorie/destinazioni **vuote** | anti thin-content | **giusto**: pagina indice senza risultati = rimbalzo |

### C · Pagine che rispondono 404 ai crawler

`/come-funziona` — racconta il percorso d'acquisto (caparra,
prenotazione, recensione) che in fase rete non esiste. Anche la SPA
rimanda al Manifesto. **Corretto oggi**; tornerà da sola al lancio.

### D · Gate sui contenuti veri (qui c'è il guadagno vero)

| Gate | Effetto oggi | Cosa serve |
|---|---|---|
| **`network_member`** | **0 su 13** organizzazioni → `/operatori` vuota, `sitemap-operators` vuota, i 4 profili veri non scoperti da nessuno | **azione tua**: marcarli dal pannello admin. È il flag che dice «intervistato e accolto», quindi la decisione è editoriale, non tecnica: non lo tocco io |
| `public_slug` mancante | Goccia di Luna e Metodo Oltre non hanno pagina pubblica | assegnare lo slug (o decidere che non entrano ora) |
| Stripe non collegato | i 4 veri restano fuori dalle superfici marketplace | irrilevante in fase rete |
| Guide riservate (`access: subscriber`) | i crawler vedono l'anteprima, come i non iscritti | **giusto**: niente cloaking, markup paywall corretto |

---

## PARTE 3 — Fatto stasera, dopo il tuo messaggio

| | Prima | Ora (in produzione) |
|---|---|---|
| **Compressione** | assente: `main.js` 2.045.088 byte in chiaro | gzip: **575 KB** (−72%), CSS −84% |
| **`llms-full.txt`** | 404 | 47 articoli interi, 152 KB compressi — la porta dei motori generativi |
| **Link interni per articolo** | **2** su 47 | **6**, dal blocco «Continua a leggere» costruito sui dati |
| Home ai crawler | 46 caratteri inglesi | 3.610 caratteri + 8 link |
| Profili professionisti | 46 caratteri | 547-757 caratteri |
| Rotte app | indicizzabili | `noindex` |

---

## PARTE 4 — Quello che resta, in ordine

### Mio, e lo faccio appena dici

- **T3 · «In breve»**: 3-4 frasi fattuali in testa a ogni articolo,
  server-side. È il blocco che AI Overview e Perplexity citano. Serve
  un campo nuovo sull'articolo: posso generare una prima stesura da
  ogni pezzo e farla rivedere alla redazione.
- **T4 · link alle fonti**: gli studi (JAMA, Nature, Cochrane) sono
  **nominati e mai linkati** in 47 articoli. È il segnale E-E-A-T più
  economico che esista. Serve una passata editoriale: preparo l'elenco
  articolo per articolo e tu approvi.
- **T6 · title**: 6 superano i 60 caratteri e si troncano in SERP.
  Ti propongo le riscritture, l'H1 narrativo resta com'è.
- **`sameAs`**: appena mi dai gli URL social di Aurya.

### Tuo, e sblocca più di qualunque cosa io possa scrivere

1. **Decidere su `/esplora-*`** (le tre strade della Parte 1).
2. **Marcare i 4 professionisti** come membri della rete.
3. **GSC**: «Richiedi indicizzazione» su home, `/blog`, `/operatori`,
   i 4 profili, i 10 articoli di punta. **Bing Webmaster**: import.
4. **Backlink** — il tetto di vetro. Ogni professionista che linka il
   suo profilo Aurya dal proprio sito è il mattone che nessun
   concorrente può copiarci. Ora ha senso chiederlo: fino a stamattina
   quei profili erano pagine mute.
