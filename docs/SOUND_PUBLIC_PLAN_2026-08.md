# Aurya Sound pubblico — Audit, architettura, SEO, funnel (ciclo SP, 19/8/2026)

**Stato: PIANO — nessuna riga di codice modificata.**

Distinzione di prodotto: per il pubblico «Esplora» significa
LEGGI → APPROFONDISCI → IMPARA → ORIENTATI. L'ascolto, la sessione e
Crea restano valore professionale degli operatori.

---

## FASE 0 — AUDIT DELL'ARCHITETTURA ATTUALE (fatto, con riferimenti)

### Routing e autenticazione (frontend)

| Rotta | Oggi | Meccanismo |
|---|---|---|
| `/sound/*` (esplora, crea, impara, tracce) | PROTETTA tutta | `ProtectedRoute` (App.js) → `/login?next=` |
| `/frequenze/:slug` | pubblica | player traccia pubblicata, cancello Lettera |
| `/meditazioni` | pubblica | vetrina con schermo-invito |

La vista è derivata dall'URL (ciclo LN): rendere pubbliche SOLO
esplora/impara è questione di spostare il cancello dalla wildcard al
segmento — l'infrastruttura c'è già.

### API backend (routers/frequencies.py) — verificato endpoint per endpoint

| Endpoint | Auth oggi | Note |
|---|---|---|
| CRUD `/tracks*`, publish/unpublish | `get_current_user` + filtro `organization_id` su OGNI query (guardia `test_router_sempre_org_scoped`) | bozze, mix, export: **già protetti a livello di autorizzazione**, non solo di UI |
| `/voice*` (spezzoni voce) | `get_current_user` + org-scoped | idem |
| `/public/{slug}` | pubblica, SOLO `status: published` | è il player pubblico esistente |
| `/catalog`, `/favorites` | cancello Lettera (HMAC) / platform account | ecosistema meditazioni |
| `GET /sounds` (basi audio) | **NESSUNA AUTH** (riga 451) | vedi «Audio», sotto |
| `POST/DELETE /sounds` | `require_system_admin` | scrittura blindata |

**Conclusione dell'audit di autorizzazione:** nascondere il player NON è
l'unica protezione. Sessioni, bozze, voce, pubblicazione ed export sono
già dietro autorizzazione server-side org-scoped. Un visitatore che
digita `/sound/crea` a mano finisce su `/login?next=`; uno che chiama
le API a mano prende 401/403. Ciò che il piano deve aggiungere è solo
la **separazione dentro** `/sound/*`.

### Audio — come nasce, dove vive (punto 9 della richiesta)

Tre nature diverse, tre risposte diverse:

1. **Frequenze e metodi (neuro)**: NON esistono file. Sono sintetizzati
   nel browser con WebAudio (`engine/synth.js`). Non c'è nessun URL da
   proteggere. Verità tecnica da mettere a verbale: la sintesi è
   codice JavaScript nel bundle — un motore client-side non è
   segretabile (chiunque sappia programmare può generare un tono a
   440 Hz). La protezione qui è **di prodotto**: nessuna UI di ascolto
   per il pubblico, nessun controllo che invochi il motore. È la
   protezione giusta per questo asset, perché l'asset vero non è «il
   suono»: è il compositore, la libreria curata, la pubblicazione.
2. **Basi audio curate (FQ2)**: file veri in `uploads/audio/`, serviti
   dallo static mount `/uploads` (server.py:576) **già pubblico oggi**,
   e `GET /api/frequencies/sounds` lista gli URL **senza auth**. Non è
   un errore introdotto: serve al player pubblico. Ma per la biblioteca
   pubblica la regola è: **il mondo «Suoni» non si mostra ai
   visitatori** (è materiale di lavoro, non contenuto editoriale).
   Rischio pre-esistente segnalato: chi conosce l'URL può scaricare le
   basi; mitigazione futura (URL firmati) fuori dallo scope di questo
   ciclo, decisione founder.
3. **Voce degli operatori**: org-scoped con auth; nel payload pubblico
   viaggiano solo gli spezzoni delle tracce PUBBLICATE. Intatto.

### Componenti

- `FrequenzePage.js` (~1.500 righe): workspace completo. `renderCard`
  è una funzione interna: nome, hz, badge, uso, body, riga cuffie,
  Approfondisci + **Ascolta** + **+ sessione**.
- Contenuto editoriale già separato dal codice: `content/biblioteca.js`
  (card + full), `content/guida.js` (Guida + Glossario), `GuidaView.js`
  (resa editoriale pura, zero audio — guardia esistente).
- Il motore è importato staticamente da FrequenzePage e dal player
  pubblico; `GuidaView` non lo tocca.
- Sipario d'ingresso (`fqz_gate_ok`): overlay una-tantum in FrequenzePage.

### SEO oggi

- Shell server-side esistente e matura (`routers/seo_shell.py`): meta +
  corpo per i crawler, pattern già usato per Magazine/manifesto.
- Sitemap fase rete: home, manifesto, chi-siamo, rete, newsletter,
  operatori. **Niente Sound**: oggi il modulo è invisibile a Google.
- Menu pubblico fase rete: poche voci (Manifesto, La rete, Magazine…).

---

## ARCHITETTURA PROPOSTA (punto 14 — un componente, varianti di accesso)

### Il principio

**Stesse rotte, stessa pagina, capacità derivate dall'autenticazione.**
Niente `PublicFrequencyCard` vs `OperatorFrequencyCard`: si estrae la
card in un componente condiviso e le pagine le passano le azioni.

```
/sound                    PUBBLICA   landing editoriale leggera (nuova, shell SEO)
/sound/esplora            PUBBLICA   biblioteca: card senza Ascolta/+ Sessione per gli anonimi
/sound/impara(+glossario) PUBBLICA   Guida «Le fondamenta» com'è (è già editoriale pura)
/sound/crea               PROTETTA   redirect /login?next= (già funzionante dal ciclo LN)
/sound/tracce             PROTETTA   idem
/frequenze/:slug          INVARIATA  player pubblico (namespace intoccabile)
/meditazioni              INVARIATA
```

### Le capacità (un solo flag, derivato, mai fidarsi del client per le API)

```js
// dentro FrequenzePage — l'utente org autenticato compone e ascolta
const canCompose = !!user;   // useAuth: null per visitatori
```

- `canCompose=false` → card senza Ascolta/+ Sessione, niente barra
  «in riproduzione», mondo Suoni non renderizzato, bottoni Crea/Tracce
  del header sostituiti dalla CTA operatori, sipario d'ingresso saltato
  (è un patto d'uso per chi ascolta, non per chi legge).
- `canCompose=true` → **pixel-per-pixel il comportamento di oggi**.
- Le API restano l'unica vera frontiera (già org-scoped): il flag
  client governa solo cosa si disegna.

### La card condivisa (punto 4)

Estrarre `renderCard` in `SoundCard.js`:

```
<SoundCard entry={e} onLearn={...} actions={...} />
```

- **Operatore**: `actions` = gli stessi Ascolta / + sessione di oggi
  (handler passati da FrequenzePage: zero cambi di logica audio).
- **Pubblico**: `actions = null` → il footer della card mostra solo
  **Approfondisci**. Niente player finto disabilitato, niente lucchetti:
  la card è completa così — nome, frequenza, badge, uso, descrizione,
  riga cuffie (che per il pubblico è informazione educativa, non un
  comando).
- La CTA professionale NON sta sulla card in griglia (40 card = 40
  pubblicità: no). Sta **in fondo al popup Approfondisci**, una riga
  discreta dopo «Nella pratica Aurya»:
  *«Vuoi ascoltarla e usarla nelle tue sessioni? Scopri Aurya Sound
  per operatori →»* — il momento di massima intenzione, il posto meno
  invadente.

---

## CTA OPERATORI (punto 5) — gerarchia

| Livello | Dove | Testo | Perché |
|---|---|---|---|
| **Primaria (1)** | landing `/sound`, blocco dedicato dopo l'introduzione | «Vuoi andare oltre l'esplorazione?» + paragrafo valore + **Scopri Aurya Sound per operatori →** | un solo punto di vendita esplicito |
| Contestuale (2) | fondo del popup Approfondisci | «Vuoi ascoltarla e usarla nelle tue sessioni? →» | intenzione massima, invadenza minima |
| Contestuale (3) | fine della biblioteca (dopo l'ultima card, un blocco solo) | riprende la primaria in breve | chi ha scorso tutto è interessato |
| Contestuale (4) | chiusura della Guida: per il pubblico la sezione «Ora puoi esplorare» guadagna una seconda uscita | «…e gli operatori possono ascoltare e costruire» | la Guida già finisce con un bivio naturale |

Dove NON metterla: hero della biblioteca, ogni card, dopo ogni
categoria. Destinazione CTA: `/professionisti` (landing operatori
esistente) — non una pagina nuova.

## LANDING (punto 6) — Opzione C, versione leggera

- **A** (landing separata + biblioteca dietro): un click in più per il
  90% dei visitatori che vogliono leggere; due pagine da mantenere.
- **B** (`/sound` = direttamente biblioteca): forte per UX, ma la
  biblioteca è un'app scura client-rendered — come home page SEO del
  modulo è debole, e non c'è spazio per la CTA primaria senza sporcare
  la biblioteca.
- **C** (consigliata): `/sound` = **pagina editoriale breve** — cos'è
  Aurya Sound in tre battute, le tre categorie con un assaggio (3 card
  statiche, non doppione della biblioteca), il percorso della Guida, la
  CTA primaria operatori, il ponte «Le esperienze create dagli
  operatori» → `/meditazioni`. Poi biblioteca e Guida come pagine
  proprie. Nessun contenuto duplicato: la landing è un indice curato,
  non un riassunto.

## SEO (punti 7-8) — cosa merita un URL, cosa no

Principio anti thin-content: **una pagina per gruppo di senso, non per
entry**. Le 40 card non diventano 40 URL.

### Struttura consigliata (fase 6, incrementale)

| URL | Fonte contenuto | Intent | Note |
|---|---|---|---|
| `/sound` | landing nuova | navigazionale/informativo «aurya sound» | indicizzabile |
| `/sound/esplora` | biblioteca | informativo generico | indicizzabile, shell con elenco testuale delle card |
| `/sound/impara` | Guida (già scritta, 6 sezioni) | «onde cerebrali cosa sono», «entrainment» | il contenuto c'è GIÀ: solo shell |
| `/sound/impara/glossario` | glossario | definizionale | indicizzabile |
| `/sound/bande-cerebrali` | le 6 `full` delle bande, in una pagina unica | «onde delta/theta/alpha…» | UNA pagina ricca > 6 pagine thin; ancore #delta #theta |
| `/sound/metodi/battito-binaurale` | `full` binaurale + FAQ | «battiti binaurali cosa sono / funzionano» | l'unica pagina-metodo singola della prima ondata: contenuto già sostanzioso (cos'è, come funziona, cuffie, ricerca, limiti) |
| `/sound/frequenze/432-hz` | `full` 432 + 440 (confronto) | «432 hz verità» | seconda ondata, solo se la prima indicizza |
| `/sound/frequenze/solfeggio` | il GRUPPO delle 9 (una pagina) | «frequenze solfeggio» | mai 9 pagine singole |

Pagine rimandate finché non dimostrano valore: 40 Hz, Schumann,
pagine-metodo restanti. Niente `/sound/frequenze/delta` singole.

### Per tipologia (schema editoriale)

- **H1** = domanda o nome («Che cosa sono i battiti binaurali?»);
  **title** ≤ 60 char col brand in coda («Battiti binaurali: cosa sono
  e cosa dice la ricerca | Aurya»); **meta description** = la promessa
  onesta della pagina (no claim terapeutici — regola editoriale GD già
  in guardia).
- **Breadcrumb**: Aurya › Sound › Metodi › Battito binaurale
  (BreadcrumbList JSON-LD, modulo `seo_schema.py` esistente).
- **Structured data**: `Article` + `FAQPage` dove le sezioni «Cosa dice
  la ricerca / Cosa non sappiamo» diventano Q&A naturali (pattern
  `_extract_faq` già esistente per il blog).
- **Canonical**: self; gli hub linkano le figlie; le figlie linkano hub,
  Guida e le 2-3 pagine sorelle pertinenti; il Magazine può linkare
  /sound dai suoi articoli a tema.
- **Internal linking di chiusura** (funnel): ogni pagina finisce con il
  blocco «Vuoi ascoltare e utilizzare questo metodo nelle tue
  sessioni? Scopri Aurya Sound per operatori →».
- Nessun volume di ricerca inventato: si parte da poche pagine dense,
  GSC (attiva dal 5/8) dirà quali query arrivano davvero, e la seconda
  ondata si decide sui dati.
- **Vincolo tecnico**: il contenuto oggi vive nel bundle JS. Per la
  shell server le `full` vanno estratte in **JSON condiviso**
  (`content/biblioteca.json`) letto sia dal frontend (import) sia dal
  backend (filesystem, stesso repo sul VPS). Un'unica fonte, zero
  duplicazione — stesso pattern «contenuto ≠ codice» già adottato.

### Sitemap e robots

- In sitemap: `/sound`, `/sound/esplora`, `/sound/impara`,
  `/sound/impara/glossario` + le pagine SEO di fase 6.
- `noindex` + fuori sitemap: `/sound/crea`, `/sound/tracce` (già
  protette; il crawler riceve redirect → nessun contenuto).

## NEWSLETTER E MEDITAZIONI (punto 10) — prodotti separati, un solo filo

Nessuna modifica ai due sistemi. Il filo è già teso: il cancello
Lettera server-side (`/catalog/unlock`, HMAC) esiste, la vetrina
`/meditazioni` esiste, i preferiti nell'account esistono. Il piano
aggiunge SOLO due ponti editoriali:
- landing `/sound` → blocco «Le esperienze create dagli operatori» → `/meditazioni`;
- player pubblico e vetrina restano l'approdo naturale degli iscritti.

Percorso: contenuto educativo → Aurya Sound → esperienze degli
operatori → Lettera/account. Sound insegna, le meditazioni fanno
ascoltare (dietro Lettera), gli operatori creano.

## NAVIGAZIONE (punto 11)

- **Footer pubblico**: link «Aurya Sound» subito (costo zero).
- **Menu principale fase rete**: aggiungere la voce «Sound» — il menu
  ha poche voci e Sound è il contenuto che dà autorevolezza alla rete.
- **Home**: nessun blocco nuovo in questa fase (la home ha già i suoi
  equilibri dal brand v3); eventuale battuta in seconda fase.

## FUNNEL OPERATORI (punto 12) e punti di perdita

```
Google («battiti binaurali») → pagina metodo → Approfondisci/Guida
  → CTA «Vuoi ascoltare e utilizzare…» → /professionisti → registrazione
  → /sound/esplora (ora con Ascolta) → + Sessione → Crea → Pubblica
```

| Punto di perdita | Mitigazione |
|---|---|
| lettore soddisfatto che se ne va | va bene così: lascia autorevolezza; il retargeting è la Lettera (ponte /meditazioni), non un popup |
| CTA → landing professionisti generalista | la landing parla di ritiri/gestione: aggiungere ancora `#sound` o sezione dedicata (fase 3, piccolo) |
| post-registrazione si perde il filo | `?next=/sound/esplora` sul flusso registrazione (lo stesso meccanismo LN0) |
| pubblico che si aspetta di ascoltare | la card non promette ascolto; il popup dice chiaramente che è funzione professionale |

## SICUREZZA (punto 13) — matrice verificata

Già protetti server-side (nessun lavoro richiesto, solo guardie):
bozze, sessioni, mix, voce, publish, export (client-side dentro pagina
protetta), dati org. Da fare in questo ciclo:
- spostare il cancello routing da `/sound/*` ai soli `crea|tracce`;
- visitatore su esplora: nessuna chiamata authed (drafts/voice si
  chiamano solo se `canCompose`);
- guardia nuova: il payload di `GET /sounds` non entra nel DOM pubblico
  (mondo Suoni non renderizzato per anonimi);
- verbale rischi accettati: sintesi client non segretabile; byte basi
  audio già pubblici da FQ2 (decisione founder se stringerli, ciclo a parte).

## TEST MATRIX (punto 15)

| Scenario | Biblioteca | Guida | Approfondimenti | Audio | + Sessione | Crea | Tracce |
|---|---|---|---|---|---|---|---|
| Visitatore | ✅ legge | ✅ | ✅ (+CTA) | ❌ nessun controllo | ❌ assente | ❌ →login?next | ❌ →login?next |
| Account Aurya (viaggiatore) | ✅ legge | ✅ | ✅ | ❌ (meditazioni sbloccate a parte, com'è oggi) | ❌ | ❌ | ❌ |
| Operatore | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Operatore sloggato a metà | come visitatore al prossimo render | — | — | ❌ | ❌ | redirect | redirect |

E2E aggiuntivi: URL diretti (`/sound/crea` anonimo → login → next
riporta lì), refresh su ogni vista nei due ruoli, mobile (nav Guida a
capo, card senza footer bottoni), API a mano (401/403), crawler
(shell restituisce meta per /sound* pubbliche; crea/tracce redirect),
sitemap (pubbliche dentro, protette fuori), `/frequenze/<slug>` suona.

## PIANO DI IMPLEMENTAZIONE (punto 16)

- **SP0 — Audit** ✅ (questo documento).
- **SP1 — Separazione pubblico/operatori.** App.js: cancello per
  segmento (esplora/impara pubbliche, crea/tracce protette);
  FrequenzePage: `canCompose`, chiamate authed condizionate, sipario
  solo per chi ascolta. Rischio: regressione operatore → l'E2E
  operatore del ciclo LN rigirato identico. File: App.js,
  FrequenzePage.js. 
- **SP2 — Biblioteca pubblica.** Estrazione `SoundCard` (stessa resa,
  `actions` iniettate); per anonimi: no Ascolta/+ Sessione/livebar/
  mondo Suoni; header con CTA al posto di Crea/Tracce. Rischio:
  divergenza visiva card → screenshot prima/dopo per l'operatore.
  File: SoundCard.js (nuovo), FrequenzePage.js, frequenze.css.
- **SP3 — CTA professionali.** Le 4 posizioni della gerarchia; ancora
  `#sound` su /professionisti. File: SoundCard/popup, GuidaView.js,
  FrequenzePage.js, OperatorLandingPage.js.
- **SP4 — Landing /sound + navigazione.** Pagina landing (design fqz,
  contenuto-indice), voce menu + footer. File: SoundLandingPage.js
  (nuova), App.js, shell di navigazione network.
- **SP5 — SEO tecnico.** Estrazione contenuto in biblioteca.json
  (fonte unica FE+BE); shell entries per /sound* pubbliche; sitemap;
  noindex su protette; breadcrumb + Article/FAQ schema. File:
  content/*.json, seo_shell.py, seo.py, biblioteca.js (import json).
  Rischio: doppia fonte → guardia di parità JSON↔render.
- **SP6 — SEO editoriale.** Prima ondata: /sound/bande-cerebrali,
  /sound/metodi/battito-binaurale (+ eventuale solfeggio). Contenuti
  dalle `full` esistenti, estesi con FAQ; regola editoriale GD vigente
  (guardie anti-promessa già attive su questi file). Seconda ondata a
  dati GSC.
- **SP7 — QA e sicurezza.** Matrice completa nei 3 ruoli, guardie
  nuove (routing, no-drafts-anonimo, no-Suoni-anonimo, CTA presente,
  shell), batteria intera, verifica visiva mobile+desktop.

Ordine consigliato: SP1+SP2 insieme (un commit), poi SP3, SP4, SP5;
SP6 respira col tempo editoriale; SP7 chiude. Deploy solo su tuo go.

## RACCOMANDAZIONE FINALE (punto 17)

Se fosse il mio prodotto: **stesse rotte con capacità per ruolo (non
un sito pubblico parallelo), landing C leggera, SEO a pagine-gruppo
dense, CTA nel momento di intenzione (popup Approfondisci) e una sola
CTA primaria sulla landing.**

Perché:
1. **Protezione reale già dove serve** — l'audit mostra che il valore
   professionale (bozze, mix, voce, pubblicazione) è già dietro
   autorizzazione server-side org-scoped. Non serve costruire un
   secondo castello: serve aprire due porte (esplora, impara) che sono
   già editoriali.
2. **Zero duplicazione, zero deriva** — un componente card, un
   contenuto (biblioteca/guida già separati dal codice), una pagina.
   Due versioni pubbliche/private della biblioteca divergerebbero al
   terzo ciclo di editing.
3. **La conversione nasce dal valore, non dalla pressione** — tutto il
   lavoro editoriale appena fatto (Le fondamenta, badge di onestà,
   riscritture) È la landing ideale per un operatore serio: la CTA
   deve solo esserci quando la curiosità è massima.
4. **SEO onesto e difendibile** — poche pagine dense su contenuto già
   scritto e già passato al vaglio delle guardie anti-claim, su
   un'infrastruttura shell che esiste; l'espansione la decide GSC, non
   l'ottimismo.
5. **Il rischio residuo è nominato, non nascosto** — la sintesi client
   non è segretabile e i byte delle basi sono già pubblici da FQ2: lo
   sai e decidi tu se stringerli, invece di scoprirlo dopo.
