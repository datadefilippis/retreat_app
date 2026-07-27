# Blog + Newsletter: audit olistico e piano (luglio 2026)

Contesto: fase rete (docs/SITO_RETE_PIANO_2026-07.md). Il blog e' l'unico
asset concreto gia' vivo: 19 articoli indicizzati su aurya.life. Deve
diventare tre cose insieme: il punto di riferimento italiano sul
benessere olistico (autorevolezza), il primo punto di conversione
(newsletter), e il motore SEO che porta traffico a tutto il resto.
Regola del founder: niente fuffa, informazioni vere e utili.

---

## PARTE 1 — Diagnosi dello stato attuale (verificata, non presunta)

### 1a. Contenuti (19 articoli live, letti e misurati)

Cosa c'e' di buono, da NON buttare:
- La voce e' giusta: onesta, pratica, senza esoterismi gratuiti. Gli
  articoli dicono "cosa dice la scienza onestamente", citano
  controindicazioni, danno prezzi reali. E' esattamente il
  posizionamento "punto di riferimento credibile".
- Tre cluster gia' formati:
  1. Pratiche (11 articoli): meditazione, breathwork, reiki, campane,
     gong, digiuno, cerchi di donne, costellazioni, tarocchi, tema
     natale, stress. Intento informazionale, top of funnel.
  2. Mondo ritiri (5): come scegliere, cosa portare, quanto costa,
     Toscana, Puglia. Intento commerciale, mid funnel.
  3. Operatori (3): prezzo giusto, partita IVA, come promuovere.
     B2B, perfettamente allineato al pivot rete (attirano gli
     operatori che vogliamo intervistare).
- Struttura pulita: 6-8 H2 per articolo, blocco Domande frequenti
  (che genera FAQPage schema), 1-6 link interni, meta description
  145-165 caratteri.

I gap concreti:
- G1. PROFONDITA'. Media 800 parole (max 1.227). Buoni articoli, ma
  nessuno e' "la risorsa definitiva" che vince una SERP competitiva.
  Le query money (es. "ritiri yoga italia", "meditazione per
  principianti") le vincono risorse da 2.000+ parole con struttura
  ricca. Oggi siamo credibili ma battibili.
- G2. ZERO FUNNEL. 1 solo articolo su 19 nomina la newsletter, zero
  CTA di iscrizione. L'unica CTA e' "Vivi un ritiro di X" che punta a
  /ritiri: che in fase rete REDIRIGE ALLA HOME. Il blog oggi converte
  letteralmente nulla, e la sua unica CTA e' rotta di fatto.
- G3. ZERO FONTI ESTERNE. Nessun link a studi, PubMed, linee guida.
  Per E-E-A-T (e per il lettore) le affermazioni "secondo la ricerca"
  vanno linkate alla ricerca.
- G4. ORFANI DI CATEGORIA. 10 articoli su 19 senza category (=
  nessun link contestuale, niente articleSection nello schema, esclusi
  dai filtri categoria). 3 categorie della tassonomia sono a zero
  articoli: massaggio, cammini, aziendale.
- G5. ZERO IMMAGINI nel corpo (solo cover autogenerata), autore
  sempre "Aurya" (Organization: manca la firma umana che per YMYL
  conta), tutto pubblicato lo stesso giorno (11 luglio): nessun
  segnale di freschezza, nessuna cadenza.
- G6. SOLO ITALIANO. Il modello supporta en/de/fr ma 0 traduzioni.
  (Non prioritario ora: prima vincere in italiano.)

### 1b. SEO tecnica (gia' forte, poco da fare)

- Articolo: BlogPosting + FAQPage + BreadcrumbList, canonical,
  hreflang it/x-default, articleBody nel markup per crawler senza JS,
  wordCount, dateModified. Ottimo.
- Sitemap-articles con hub + 19 URL, lastmod, IndexNow al publish.
- Hub /blog: solo BreadcrumbList, manca ItemList/CollectionPage; le
  viste categoria (/blog?categoria=x) sono query param, quindi NON
  indicizzabili come pagine hub. Unica vera mancanza tecnica.

### 1c. Funnel e newsletter (qui e' il vuoto)

Due binari paralleli che NON si parlano:
- Binario A, "lettera di Aurya": LeadForm su /newsletter e 2 landing →
  POST /public/leads → collection prelaunch_leads. Campi ricchi
  (citta', interessi, budget, travel) ma: niente double opt-in,
  niente preferenze di iscrizione strutturate, niente pagina gestione,
  nessun motore di invio. Export CSV manuale dall'admin.
- Binario B, modulo Newsletter per-org (feature degli operatori):
  form embeddabili, org-scoped, iscritti in Customer Insights. NON e'
  la newsletter di Aurya e non va confuso ne' riusato per Aurya: serve
  gli operatori.
- Invio email: solo transazionale via Brevo HTTP API. Nessun sistema
  di campagne/broadcast verso iscritti. Gli iscritti vengono SOLO
  raccolti.
- Lead magnet: un singolo URL globale da env, consegnato dopo
  l'iscrizione. Zero gating reale, zero libreria.
- GDPR: consenso richiesto solo dal form (il backend non lo impone),
  nessun double opt-in. Per email marketing in Italia il double
  opt-in e' lo standard di fatto (prova del consenso): da sistemare
  PRIMA di iniziare a spedire davvero.

---

## PARTE 2 — Strategia

### Il principio

Un solo motore a 4 stadi, tutto misurabile:

  Google (articolo utile) → fiducia (contenuto vero, fonti, volti)
  → conversione (newsletter con promessa specifica + guide riservate)
  → relazione (lettera segmentata sulle preferenze → ritiri al flip)

Il blog NON vende ritiri in fase rete: alimenta la lista. La lista e'
l'asset che al flip marketplace diventa domanda pronta.

### Le 5 scelte strategiche

S1. UNA newsletter, UN modello iscritto, con preferenze. Si supera
    prelaunch_leads come contenitore della lettera: nasce il
    "subscriber Aurya" con preferenze strutturate:
    - temi: tutte le categorie / solo alcune (tassonomia esistente)
    - formato: tutti gli articoli / solo pratiche ed esercizi
    - alert ritiri: zona (regioni, riuso della geografia directory) o
      tutta Italia (dormiente in fase rete, si accende al flip)
    I lead pre-lancio esistenti migrano dentro (hanno gia' interests/
    city: si mappano alle preferenze).
    Double opt-in: email di conferma via Brevo con token firmato
    (l'infrastruttura token c'e' gia' per l'unsubscribe).

S2. GUIDE RISERVATE (gated) come motore di iscrizione, fatte bene:
    non "articolo nascosto per forzare l'email", ma guide
    genuinamente piu' profonde (2.500+ parole, checklist scaricabili)
    dove il gate E' il double opt-in: ti iscrivi → email di conferma →
    il link nella mail sblocca la guida. Un piccione, tre fagioli:
    conversione, conferma GDPR, email verificata.
    L'articolo gated resta indicizzabile con l'anteprima (primi 2-3
    paragrafi + indice dei contenuti visibili): Google vede una pagina
    vera, l'utente vede esattamente cosa ottiene iscrivendosi.
    Regola: MAI gated i contenuti che devono scalare le SERP da soli;
    gated solo le guide "compendio" che aggregano un cluster.

S3. FUNNEL SUL BLOG, contestuale per cluster. Ogni articolo ha:
    - CTA newsletter di fine articolo, con promessa contestuale:
      articoli pratiche → "una pratica ogni due settimane";
      articoli ritiri → "avvisami sui ritiri nella mia zona";
      articoli operatori → CTA /entra-nella-rete (il B2B converte
      alla rete, non alla lettera).
    - Box correlati (stesso cluster) per sessioni piu' lunghe.
    - Lead magnet per cluster (non piu' uno globale): pratiche →
      kit audio/PDF pratiche; ritiri → checklist "scegli il ritiro
      giusto"; operatori → guida fiscale completa.
    La CTA "Vivi un ritiro" diventa di fase: in network punta alla
    newsletter con contesto zona, in marketplace torna a /ritiri.

S4. CONTENUTO: upgrade prima di espandere. Prima si portano i 19
    articoli allo standard "risorsa definitiva" (profondita' dove la
    SERP lo chiede, fonti, immagini, categorie complete, firma
    umana), POI si espande con cadenza fissa. L'espansione segue i
    cluster che servono al business:
    - locali (le SERP "ritiri yoga + regione" sono le piu' vicine
      alla transazione): Umbria, Sicilia, Sardegna, Lago di Garda,
      Piemonte, Trentino
    - categorie scoperte: massaggio, cammini, aziendale
    - pratiche ed esercizi step-by-step (il formato piu' iscrivibile)
    - interviste della rete ripubblicate come articoli (ponte col
      pivot: ogni intervista e' anche contenuto SEO con volto vero)
    Cadenza sostenibile: 2 articoli a settimana, giorno fisso.

S5. INVIO: Brevo, non un sender fatto in casa. Gli iscritti (con
    attributi preferenze) si sincronizzano su liste/attributi Brevo;
    le campagne si scrivono e spediscono dalla dashboard Brevo
    segmentando sugli attributi. Il nostro DB resta la fonte di
    verita'; Brevo e' il braccio. Costruire un campaign engine
    interno oggi sarebbe over-engineering puro.

### Cosa NON facciamo (per onesta' col principio "no fuffa")

- Niente pop-up aggressivi/exit intent: promessa chiara nel flusso
  di lettura, non interruzioni.
- Niente contenuto AI-generico di riempimento: ogni articolo nuovo
  passa dallo standard qualita' (fonti, esperienza concreta, onesta'
  su limiti e controindicazioni).
- Niente gate su articoli informazionali di base.
- Niente traduzioni ora: prima autorevolezza in italiano.

---

## PARTE 3 — Piano operativo (onde BN, step-by-step come RT)

### BN0 — Decisioni founder (bloccano i testi, non i lavori tecnici)
- Conferma nome/promessa lettera ("La lettera di Aurya", ogni due
  settimane) — gia' in sospeso da RT0
- Quali 3 lead magnet per cluster (proposte pronte in S3)
- Firma degli articoli: "Davide e Valentina · Aurya"? (per E-E-A-T
  serve il volto umano; il campo author_name c'e' gia')
- Approvazione delle 2 guide gated di partenza (proposta: "La guida
  completa ai ritiri olistici in Italia" e "Il kit delle pratiche
  quotidiane"; per gli operatori la guida fiscale resta APERTA come
  biglietto da visita della rete)

### BN1 — Funnel sul blog (quick win, zero modello dati)
- Componente NewsletterCTA contestuale per categoria (promessa
  diversa per cluster) in fondo a ogni articolo + variante compatta
  nel hub /blog
- Box "Continua a leggere" (correlati per categoria, poi stesso
  cluster) nella pagina articolo
- CTA di fase: "Vivi un ritiro di X" → in network punta a /newsletter
  (contesto retreat_alert), in marketplace torna a /ritiri/X
- Fix categorie: assegnare le category ai 10 articoli orfani (riuso
  tassonomia; "operatori" non ha categoria → resta None ma la CTA
  diventa /entra-nella-rete)
- GA4: generate_lead con lead_context=blog_article + categoria

### BN2 — Modello subscriber + double opt-in + preferenze
- Collection newsletter_subscribers (Aurya-level): email, status
  (pending/confirmed/unsubscribed), preferenze {topics[], format,
  retreat_alert{scope, regions[]}}, source (article/landing/gate),
  consenso timbrato, token
- Double opt-in: POST subscribe → email conferma Brevo con link
  firmato → confirmed (+ sblocco eventuale contenuto gated)
- Pagina /newsletter/preferenze/{token}: gestione preferenze e
  unsubscribe (un click dal footer di ogni lettera)
- Migrazione prelaunch_leads type=traveler → subscribers pending
  (con invito a confermare alla prima campagna) mappando interests →
  topics, city → regione
- LeadForm evoluto: opt-in preferenze inline (chip categorie gia'
  esistenti nel form: si riusano)

### BN3 — Guide riservate (gated)
- Campo access: "public" | "subscriber" su Article (Create+Update+
  editor admin) + anteprima: il pubblico vede intro + indice, lo
  sblocco avviene col token subscriber (dal link email di conferma o
  di una lettera)
- SEO shell: la pagina gated serve l'anteprima nel markup (niente
  cloaking: Google vede cio' che vede l'utente non iscritto)
- Le 2 guide di partenza scritte allo standard (2.500+ parole, fonti,
  checklist scaricabile)
- Lead magnet per cluster al posto dell'URL globale env

### BN4 — Upgrade dei 19 articoli (contenuto, a lotti)
- Lotto 1 (i 5 commerciali): portarli a risorsa definitiva
  (2.000+ parole dove serve, fonti, immagini con alt, tabelle
  prezzi/stagioni), refresh dateModified reale
- Lotto 2 (gli 11 pratiche): fonti esterne (studi citati), sezione
  "esercizio da fare oggi" standard, cross-link sistematico
- Lotto 3 (i 3 operatori): CTA rete, casi veri dalle interviste
- Firma umana ove deciso in BN0

### BN5 — Espansione con cadenza
- Calendario editoriale: 2/settimana, giorno fisso; priorita': locali
  (6 regioni), categorie scoperte (3), pratiche step-by-step,
  interviste-articolo della rete
- Hub categoria indicizzabili: /blog/categoria/{slug} come rotta vera
  (shell + ItemList + sitemap) al posto del query param
- Guardie: articolo pubblicato DEVE avere category, description
  120-165, almeno 2 link interni, blocco FAQ

### BN6 — Invio e misura
- Sync subscribers → Brevo (contatti + attributi preferenze) al
  confirm/update, cancellazione al unsubscribe
- Prima lettera vera spedita da Brevo segmentando su topics
- Dashboard admin minima: iscritti per stato/fonte/tema, tasso
  conferma, crescita settimanale
- KPI: GSC (impression, click, query), GA4 (generate_lead per
  context, lead_magnet_download, funnel articolo→iscritto),
  iscritti confermati/settimana, % articoli con conversione

### Dipendenze e ordine
BN1 subito (nessuna dipendenza). BN2 prima di BN3 (il gate usa il
token subscriber). BN4-BN5 in parallelo continuo (contenuto). BN6
dopo BN2. L'alert ritiri per zona resta DORMIENTE (preferenza
raccolta da subito, invii solo al flip marketplace: in fase rete non
ci sono ritiri prenotabili da segnalare, e va detto onestamente
nel form: "ti avviseremo quando apriremo le prenotazioni").

---

## Nota tecnica di riuso (per non ricostruire)

- Chip interessi del LeadForm ≈ categorie tassonomia: mappa diretta
  interests → topics
- Geografia: le regioni della directory (geo AN3) sono le zone
  dell'alert ritiri
- Token firmati: pattern gia' in marketing_consent (unsubscribe)
- Brevo: email_service gia' pronto (HTTP API, retry, fallback log)
- FAQ → FAQPage schema: gia' automatico se il markdown ha
  "## Domande frequenti" (standard da imporre in guardia BN5)
- MultiLangSection editor: pronto per quando si tradurra'
