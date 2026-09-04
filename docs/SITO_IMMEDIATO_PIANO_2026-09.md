# SITO IMMEDIATO — meno parole, più persone (piano di refinement, 3/9/2026)

*Il founder: «un'operatrice olistica è finita sul sito: il progetto è bello,
ma ci sono troppe informazioni, uno si stanca a leggere e molla». E:
«ora che abbiamo qualche operatore, La Rete va sostituita da
esplora-operatori». Vincolo: non stravolgere. Rendere immediato.*

## 0 · Misurato sul sito reso (3/9/2026, localhost = prod)

| Pagina | Parole | Sezioni (h2) | Cosa chiede al visitatore |
|---|---|---|---|
| Home `/` | 529 | 5 | Esplora il Magazine · Per i professionisti (hero) + 6 CTA sotto |
| La Rete `/operatori` | 423 | 5 | Conosci la visione · Entra nella rete · Ricevi la Lettera |
| Esplora `/esplora-operatori` | 237 (+ filtri) | 0 | Vicino a me · filtri · Vista rapida (fa, non spiega) |
| Manifesto | 486 | 7 | Entra nella rete · Ricevi la Lettera |
| Chi siamo | 417 | 4 | Entra nella rete · Ricevi la Lettera |
| Entra nella rete (`/per-operatori`) | **945** | 8 | Crea il tuo account |

Header: **7 voci** + ricerca + pill (Magazine · Sound · Meditazioni ·
Manifesto · La Rete · Chi siamo · Per i professionisti). Footer: 20 link.
In prod: **8 operatori** con profilo pubblicato; La Rete ne mostra gli
stessi 8 (nessuna intervista verificata ancora).

## 1 · Diagnosi (perché ci si stanca)

1. **Il sito si spiega cinque volte.** «Stiamo costruendo una rete di
   professionisti, una persona alla volta, raccontati con cura» compare
   in home (due sezioni), La Rete, Manifesto, Chi siamo, Entra nella
   rete. Chi legge tre pagine legge tre volte lo stesso perché. Non è
   che ci siano troppe informazioni: è che ce n'è **una, ripetuta**.
2. **Ogni pagina finisce con le stesse due porte** («Entra nella rete»
   + «Ricevi la Lettera»): 5 pagine × 2 CTA. Le porte perdono valore.
3. **La pagina La Rete contraddice se stessa**: «Presto potrai conoscere
   le prime persone» sopra 8 schede vere. Copy scritto quando la rete
   era vuota.
4. **Il visitatore che cerca un professionista non ha una porta in
   alto.** Nel hero della home le CTA sono Magazine e Professionisti
   (=diventa operatore). «Scopri la rete» è nella terza card, sotto due
   paragrafi di visione. Poi arriva su La Rete, altri 200 parole prima
   di una faccia. Esplora invece **mostra le persone subito** con
   filtri, mappa e prezzi: è la pagina giusta, ma non è linkata dal
   menu.
5. **Due pagine «chi siamo» nel menu principale** (Manifesto + Chi
   siamo = 900 parole) e **due voci per lo stesso mondo** (Sound +
   Meditazioni). Sette voci in header per un sito che ha tre cose da
   offrire: persone, contenuti, suono.
6. **Il funnel professionista è lungo**: 5 porte (pill, home, La Rete,
   Manifesto, footer) → una pagina da 945 parole e 8 sezioni con la
   CTA in fondo.
7. **La Lettera è chiesta in quattro posti** (home, La Rete, Manifesto,
   footer).

Verdetto: non è carico cognitivo da complessità, è **carico da
ridondanza**. Il visitatore non si perde nella struttura: si stanca
perché la struttura gli ripete la stessa promessa invece di mostrargli
le persone.

## 2 · I principi (i paletti del non-stravolgere)

- **Una cosa per pagina, detta una volta.** Il perché vive nel
  Manifesto. Le altre pagine lo linkano, non lo ripetono.
- **Le persone prima delle parole.** Dove ci sono professionisti veri,
  si vedono nel primo schermo.
- **Una porta per funnel**: chi cerca → Professionisti; chi offre →
  Per i professionisti (pill); chi vuole seguire → Lettera (in fondo
  alla home e nel footer, basta).
- Nessuna pagina muore: si accorcia, si ricollega, o redirige.
- URL stabili (SEO: shell SSR, sitemap, canonical già su `/operatori`).

## 3 · Le onde

### SR1 — LA RETE DIVENTA LA DIRECTORY (la richiesta del founder)
- `/operatori` resta l'URL (canonico, in sitemap, shell SSR pronto) ma
  **rende la pagina esplora** anche in fase network: OperatorsGate →
  OperatorsIndexPage sempre; `/esplora-operatori` → redirect a
  `/operatori` (e `/esplora-operatori/:categoria` → `/operatori/:categoria`).
  NetworkOperatorsPage resta nel codice, spenta (torna utile per una
  landing «come nasce la rete» se servirà).
- **Regola di visibilità unica**: profilo pubblicato + non escluso
  dalla directory (interruttore admin RO). `network_member` resta il
  flag della rete «raccontata» (badge Verificato = intervista), non un
  cancello. Oggi in prod le due liste coincidono (8 e 8).
- **Copertina** (chiara su cosa stiamo costruendo, senza ridondanza):
  - eyebrow: `La rete Aurya`
  - H1: `I professionisti del benessere`
  - una riga: `Persone che conosciamo una per una: la loro storia, il
    modo in cui lavorano e, quando vuoi, una sessione, un evento o un
    ritiro da prenotare qui.`
  - link discreto: `Come nasce la rete →` (Manifesto). Fine. Niente
    «stiamo costruendo», niente «presto».
  - le schede mostrano già ★, città, «Verificato», prezzo da: il
    criterio si vede, non si dichiara.
- **Inventario link da cambiare** (da `grep /operatori`): header ×2
  (navOperators/navNetwork → una voce sola «Professionisti»), footer,
  ProductLandingPage, OperatorInterviewPage (breadcrumb + JSON-LD),
  OperatorProfilePage breadcrumb, BlogIndexPage CTA, OperatorsIndexPage
  (il link «esempio» che oggi rimanda a La Rete), NetworkHomePage,
  IniziaPage (link directory), admin InterviewsTab/OrganizationsTab
  (testi di aiuto), rotte.json (nota), seo_shell.py: 7 punti dove
  `/operatori` è descritto come «landing della rete» (title, meta,
  breadcrumb «Professionisti», link interni) → title «Professionisti
  del benessere | Aurya», description dalla copertina; seo.py sitemap
  invariata. Guardie: quelle che fissano `sitePhase === 'network' →
  NetworkOperatorsPage` e i title della shell evolvono con nota.

### SR2 — HOME IN QUATTRO BATTUTE (da 529 a ~330 parole)
- Hero: titolo com'è, **una** frase, CTA primaria **«Scopri i
  professionisti»** (→ /operatori), secondaria «Per i professionisti».
- Blocco «Un luogo dove conoscere…» + le tre card Magazine/Professionisti/
  Esperienze: restano le card (sono le tre porte), sparisce il
  paragrafo introduttivo doppio; la card Professionisti mostra **3
  volti veri** (avatar + nome + città dalla directory) invece del
  testo «stiamo costruendo».
- «Perché esiste Aurya?» (7 righe): via dalla home, è il Manifesto.
  Resta una riga sola sotto le card: «Perché Aurya → Manifesto».
- Sound: com'è. Magazine: com'è. Sezione professionisti: da 8 righe a
  2 + CTA. Lettera: resta (è l'unico form del sito).

### SR3 — HEADER A CINQUE VOCI
`Professionisti · Magazine · Sound · Chi siamo` + pill **Per i
professionisti** (+ ricerca). Meditazioni vive dentro Sound (la
passerella Sound l'ha già: Meditazioni · Aurya Sound · Aurya Lab).
Manifesto vive dentro Chi siamo (link in testa) e nel footer. Le due
rotte restano vive, indicizzate, linkate: escono solo dal menu.

### SR4 — MANIFESTO E CHI SIAMO: LE DUE CODE VIA
Entrambe chiudono con «Se sei un professionista» + «Se vuoi seguire il
progetto» (≈120 parole ciascuna). Diventano **una striscia comune di
due righe** (componente `DuePorte`: «Sei un professionista? Entra
nella rete →» · «Vuoi seguire il progetto? La Lettera →»), usata in
fondo a Manifesto, Chi siamo e articoli del Magazine. Chi siamo apre
con un link «Il perché, in una pagina → Manifesto».

### SR5 — ENTRA NELLA RETE DA 945 A ~450 PAROLE
Struttura: hero (titolo + 2 righe + **CTA subito**) → «Quello che puoi
già fare» (3 righe: profilo, listino prenotabile, ritiri) → «Come
funziona» (3 passi, una riga l'uno) → FAQ **ripiegate** (accordion) →
CTA finale. «Per chi è Aurya» e la poesia finale («Le reti non
nascono da una piattaforma») migrano nel Manifesto, che è casa loro.

### SR6 — LA LETTERA IN DUE POSTI
Form in fondo alla home; link nel footer e nella striscia DuePorte.
Via i blocchi Lettera da La Rete (sparisce con SR1) e Manifesto.

### SR7 — GUARDIE E SEO
- Guardia «una promessa sola»: la frase «stiamo costruendo una rete»
  può vivere in UNA pagina (Manifesto); nelle altre, rosso.
- Guardia «due porte»: massimo una CTA «Entra nella rete» per pagina.
- Shell SSR e sitemap: `/operatori` title/description nuovi; redirect
  `/esplora-operatori` → `/operatori` anche in nginx (rotte.json) per
  i crawler; nessun URL indicizzato muore.
- Collaudo: parole per pagina dopo (target: home ≤ 330, pro ≤ 450),
  click-through dei tre funnel in locale, screenshot mobile prima/dopo.

## 4 · Ordine e sforzo
SR1 (mezza giornata, è la richiesta) → SR3 (ore) → SR2 (mezza
giornata) → SR4+SR6 (ore) → SR5 (mezza giornata) → SR7 trasversale.
Totale ~2 giornate. Deploy in uno o due giri, col go del founder.

## 5 · Decisione da prendere prima di SR1
La directory mostra **tutti i profili pubblicati** (regola esplora,
oggi 8) oppure **solo i membri della rete** (flag admin, oggi gli
stessi 8)? Proposta: pubblicati e non esclusi, con «Verificato» come
segno della cura. Così un nuovo operatore che si registra e pubblica
si vede subito, e il founder governa le eccezioni dall'interruttore
Directory già esistente.
