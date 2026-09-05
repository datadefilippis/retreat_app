# Search Console: 74 pagine non indicizzate — analisi (5/9/2026)

Referto GSC del founder: 74 URL non indicizzati. Ragioni: 34
«Pagina duplicata, Google ha scelto una canonica diversa», 26
«Rilevata, ma attualmente non indicizzata», 8 «Pagina alternativa con
tag canonical appropriato», 3 «Pagina con reindirizzamento», 2
«Esclusa da noindex», 1 «404».

Metodo: non ho la lista degli URL di GSC (si esporta dal report);
ho crawlato il sito vero come Googlebot: le 131 URL della sitemap, le
79 radici del registro rotte (`backend/config/rotte.json`), le
varianti classiche (barra finale, `?lang=`, `/index.html`, maiuscole,
rotte del gestionale) e i link interni resi ai bot da home, directory,
profili, Magazine e Sound.

## Cosa è a posto (e spiega 13 dei 74)

- **Sitemap pulita**: 131 URL, tutte 200, tutte con canonical uguale
  a se stesse, nessun noindex, un solo duplicato dichiarato
  (`/esplora-operatori` → canonical `/operatori`, corretto).
- **8 «alternativa con canonical appropriato»**: sono le varianti che
  dichiarano bene la loro canonica: `/operatori/`,
  `/operatori?categoria=…`, `/esplora-operatori/…`, `?lang=en/de/fr`
  (servono l'italiano con canonical alla base). Comportamento giusto,
  nessuna azione.
- **3 «con reindirizzamento»**: `http://` → `https://`, `www.` →
  senza, e il rimando in JavaScript di `/esplora-operatori` verso
  `/operatori`. Giusto; solo il terzo si può rendere un 301 vero.
- **2 «noindex»**: le rotte del gestionale (`/dashboard`, `/reviews`,
  …) hanno `X-Robots-Tag: noindex, nofollow` da nginx e le rotte di
  servizio (`/login`, `/accedi`, `/termini`, …) hanno il meta noindex
  dal renderer. Voluto.

## I difetti veri trovati (candidati ai 34 duplicati e ai 26 «rilevata»)

1. **Dieci radici di prefisso indicizzabili e vuote.** `/e`, `/p`,
   `/s`, `/o`, `/r`, `/co`, `/dg`, `/ph`, `/l`, `/frequenze` senza
   slug rispondono 200 con la stessa shell da 41 caratteri, senza
   canonical e senza noindex. Per Google sono dieci pagine identiche:
   ne sceglie una e le altre diventano «duplicate, canonica diversa».
   Vanno in 404 (o noindex) dal registro nginx.
2. **`/index.html` è un doppione della home**: 200, contenuto della
   build, nessun canonical. Serve un 301 a `/`.
3. **`/ritiri` è contraddittoria**: serve il testo della home con
   canonical `/` E noindex insieme. Va un 301 a `/`.
4. **Tre pagine Sound praticamente vuote per i bot**: `/sound` (55
   caratteri di testo), `/sound/impara` (60), `/sound/impara/glossario`
   (60). Sono la porta del mondo Sound e per Google sono gusci: o
   duplicati fra loro o «rilevate, non indicizzate». Il renderer deve
   dare loro il testo vero, come fa per la home.
5. **Le cinque stanze del Lab rendono 330-360 caratteri** (solo
   titolo e domanda): il «Perché ti interessa» e le tre azioni vivono
   in React e i bot non li vedono. Stessa cura del punto 4.
6. **Le 14 pagine di categoria del Magazine sono orfane per i bot**:
   la shell di `/blog` linka 48 articoli ma nessuna categoria, e
   rendono 440-1.430 caratteri (in gran parte la lista). Sono
   distinte (14 hash diversi) ma deboli: candidate a «rilevata, non
   indicizzata».
7. **La home non linka nessun profilo** (0 link a `/o/…`): i
   professionisti sono raggiungibili solo via `/operatori`. E i
   profili rendono 500-930 caratteri.
8. **Un timeout osservato**: durante il crawl una richiesta a
   `/sound/esplora/432-hz?lang=en` è andata oltre i 25 secondi (le
   successive 0,2 s). Un caso isolato, ma Googlebot con un timeout
   segna «rilevata, non indicizzata». Da tenere d'occhio (log nginx).

Contenuti robusti: 61 articoli su 62 sopra i 1.500 caratteri
(mediana 9.200), le 38 schede Sound fra 900 e 2.600, gli articoli
linkano 7-11 altri articoli e `/operatori`.

## Cosa non posso dire senza la lista

I 34 e i 26 sono etichette di Google su URL che non vedo. I difetti
1-5 spiegano con certezza almeno 15 duplicati; il resto è
probabilmente URL scoperte in passato (vecchie rotte, varianti) che
il report elenca. Esportando da GSC le due tabelle («duplicata» e
«rilevata») la mappa diventa esatta e la cura mirata.

## Piano proposto (ciclo IX, indicizzazione)

**IX1. Chiudere i gusci.** Nel generatore nginx dal registro: le
radici dei prefissi con slug (`/e`, `/p`, `/s`, `/o`, `/r`, `/co`,
`/dg`, `/ph`, `/l`, `/frequenze`) senza slug → 404 del renderer;
`/index.html` → 301 `/`; `/ritiri` → 301 `/`; `/esplora-operatori`
(e `/{categoria}`) → 301 `/operatori`. Guardia in `collauda_rotte`.

**IX2. Testo vero ai bot dove oggi c'è il guscio.** Renderer per
`/sound`, `/sound/impara`, `/sound/impara/glossario` e le cinque
stanze del Lab con lo stesso testo che vede l'utente (domanda,
perché, azioni), come già per home, profili e brand. Guardia:
nessuna URL in sitemap sotto i 400 caratteri di testo reso.

**IX3. Maglia interna.** La shell di `/blog` linka le 14 categorie
(e ogni categoria una riga di introduzione vera); la home linka i
professionisti in evidenza; ogni articolo linka la sua categoria.
Le categorie con meno di tre articoli si accorpano.

**IX4. Guardia anti-guscio.** Test che percorre le rotte del
registro come Googlebot in locale: 200 indicizzabile ⇒ testo ≥ 100
caratteri e canonical presente; identici fra loro ⇒ fallisce.

**IX5. Lettura di GSC dopo la cura.** Con l'export delle liste:
verifica URL per URL, «Convalida correzione» sui gruppi risolti,
richiesta di indicizzazione per le 10-15 pagine che contano.

Costo: IX1 e IX4 un'ora e solo nginx più guardie; IX2 mezza
giornata nel renderer; IX3 mezza giornata. Nessun cambio di
struttura del sito.

## Stato (5/9/2026, sera)

- **IX1 FATTO**: registro con `solo_con_slug`, `rimandi`,
  `rimandi_prefisso`; nginx generato con 404 delle radici e 301 veri,
  prima del renderer; resolver e `collauda_rotte` allineati.
- **IX2 FATTO**: `/sound` 55 → 2.447 caratteri, `/sound/impara` 60 →
  1.950, glossario 60 → 4.076 (dati copiati da `guida.js` con guardia
  di parità), stanze del Lab 330 → 1.100 con domanda, perché, azioni.
- **IX3 FATTO**: `/blog` linka le 15 categorie con una riga; categoria
  con intro e ritorno; briciola nell'articolo; otto professionisti in
  home.
- **IX4 FATTO**: `tests/test_indicizzazione_ix.py`, 332 verdi con le
  guardie SEO e Lab.
- **IX5 DA FARE**: dopo il deploy (serve il riavvio di nginx: la conf è
  un bind-mount) rileggere Search Console con l'export delle liste,
  «Convalida correzione» sui gruppi risolti, richiesta di
  indicizzazione per le pagine che contano.
