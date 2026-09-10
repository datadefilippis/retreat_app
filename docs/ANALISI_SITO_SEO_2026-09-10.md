# Aurya, 10 settembre 2026 sera — Il sito dopo il rebranding: funnel, ridondanza, SEO

Analisi fatta a rebranding compiuto, sul sito in locale allineato a `main`
(stato non ancora in produzione). Ogni affermazione viene da una verifica:
i testi delle pagine letti come li legge una persona, la shell SEO letta
come la legge un crawler, i numeri di produzione dove esistono.

Il documento ha tre parti: **1.** com'è il sito oggi, pagina per pagina;
**2.** i funnel e la ridondanza, con le proposte; **3.** la SEO, con quello
che è già stato corretto stasera e quello che resta. In fondo, il piano.

---

## 1. Il sito oggi

Sette pagine cardine pubbliche più tre mondi (Magazine, Sound, profili).
Parole contate sul testo che vede il crawler.

| Pagina | Scopo | Parole | Uscite principali |
|---|---|---|---|
| `/` home | le due porte | 843 | Trova il mio ritiro · Crea il tuo spazio · Scopri gli operatori · Magazine · Sound · Manifesto · form Cerchio |
| `/cerca-ritiro` | landing di chi cerca → Cerchio | 452 | form (14 vie, dove, budget) ×2 · Sound · Professionisti · Apri il tuo spazio |
| `/entra-nella-rete` | landing operatore → account | 1.471 | Apri il tuo spazio ×6 · profili · Crea Studio · piani · FAQ · form |
| `/operatori` | directory | 216 | filtri, schede, profilo |
| `/o/{slug}` | profilo operatore | ~300 | servizi, ritiri, recensioni, contatti |
| `/esperienze` | calendario ritiri (fuori dal menu) | 93 | schede · Trovami il mio ritiro · Apri il tuo spazio |
| `/newsletter` | landing del Cerchio | 314 | form ×2 · Sound · Professionisti |
| `/meditazioni` | vetrina meditazioni (cancello) | 247 | form email · tracce |
| `/sound` | biblioteca del suono | 338 | Biblioteca · Impara · Lab · Meditazioni |
| `/blog` | Magazine | 1.807 | articoli, categorie, box «Trovami il mio ritiro» |
| `/chi-siamo` | le persone | 518 | Manifesto · Professionisti · Cerchio · Magazine |
| `/manifesto` | il perché | 560 | Magazine · Cerchio · Sei un professionista? |
| `/aziende` | team building su misura | 393 | modulo |
| `/costi` | i piani 2027 | 147 | (nessuna uscita) |

Il menu pubblico ha quattro voci: Professionisti, Magazine, Sound, Chi
siamo. La home apre sulle due porte. Da stasera «Ritiri ed esperienze»
non è nel menu: resta viva dal link e si accende nei motori da sola
quando avrà ritiri.

---

## 2. I funnel

### 2.1 Chi cerca (viaggiatore)

**Il percorso**: home → «Trova il mio ritiro» → `/cerca-ritiro` → form
(nome, email, 14 vie, dove, budget) → email «Benvenuto nel Cerchio: un
clic e sei dentro» → conferma → meditazioni aperte + benvenuto adattivo →
(quando ci sarà) ritiro proposto per zona e vie.

**Cosa funziona**: una sola azione per pagina; la promessa è onesta («ti
scriviamo quando c'è»); il form è lo stesso ovunque (stessa struttura,
stesso vocabolario, verificato stasera); il benvenuto dice cose diverse a
chi cerca un ritiro e a chi voleva solo le meditazioni.

**Ridondanza misurata**: su `/cerca-ritiro` i tre benefici del Cerchio
(meditazioni, Lettera, ritiri) compaiono **tre volte** (lista in alto,
tre schede «Cosa succede dopo», seconda lista nel form in fondo) e il form
intero è ripetuto due volte. Su `/newsletter` lo stesso: benefici ×3, form
×2. Le due pagine, `/cerca-ritiro` e `/newsletter`, dicono la stessa cosa
con due titoli e portano allo stesso posto (il Cerchio).

**Proposta**
1. `/cerca-ritiro`: tenere hero + form in alto, le tre schede «Cosa
   succede dopo» (sono la spiegazione), «Prova prima di entrare» (Sound),
   e in fondo **un solo bottone** che riporta al form in alto, non un
   secondo form. Tolgo la seconda lista di benefici.
2. `/newsletter`: diventa la porta del Cerchio per chi arriva dalle
   meditazioni e dal Magazine, con una promessa più corta (meditazioni
   prima, ritiri dopo) e **un form solo**; oppure si fonde in
   `/cerca-ritiro` con un rimando 301. La seconda è più semplice: una
   pagina sola per un'azione sola. Decisione del founder.
3. Home: oggi sotto le due porte ci sono cinque riquadri (Magazine,
   Professionisti, Esperienze «prossimamente», Sound, Manifesto), il
   blocco Magazine, il blocco «per i professionisti», il form del
   Cerchio. Sono 843 parole per una pagina che deve fare due cose. Terrei:
   le due porte, i tre pilastri (Professionisti, Magazine, Sound), il
   form del Cerchio. Il riquadro «Esperienze — prossimamente» esce (la
   pagina è fuori dal menu per scelta), il «perché esiste Aurya» va nel
   Manifesto che c'è già, il blocco dei fondatori va in Chi siamo.

### 2.2 L'operatore

**Il percorso**: home «Crea il tuo spazio» o `/entra-nella-rete` → form
(nome, attività, email, password, due consensi) → «Apri la tua email: un
clic e sei dentro» → clic → sessione → `/benvenuto` (discipline, città)
→ dashboard → pagina online → email «La tua pagina è online» + Telegram →
giorni 5/10/15 se la pagina resta a metà → primo ritiro.

**Cosa funziona** (verificato stasera da utente vero): niente secondo
login, ogni vicolo cieco ha un'uscita (link scaduto, secondo clic, login
prima della verifica), la sequenza parla solo quando serve.

**Ridondanza**: la landing è lunga, 1.471 parole, e chiede «Apri il tuo
spazio» sei volte. Non è un male in sé (è una landing di vendita), ma tre
blocchi dicono cose già dette:
- «E il tuo profilo può essere scoperto anche su Aurya» ripete la scheda
  «Ti possono trovare» di poco sopra;
- il blocco «Chi c'è dietro Aurya» ripete `/chi-siamo` (e il link c'è);
- la chiusura «Il tuo lavoro merita un posto tutto suo» ripete l'hero
  parola per parola.

**Proposta**: tolgo i tre blocchi, resta tutto il resto (è il testo del
founder: schede, «perché entrare ora», prezzi, tre passi, FAQ, form). La
pagina scende sotto le 1.100 parole senza perdere un argomento.

### 2.3 Chi siamo e Manifesto

Sono due pagine con la stessa apertura («Tutto inizia da una domanda» /
«Ogni percorso di benessere inizia da una domanda»), lo stesso passaggio
sulle «fondamenta» e gli stessi quattro passi. Il Manifesto ha i principi;
Chi siamo ha le persone. **Proposta**: Chi siamo tiene solo le persone
(Valentina, Davide, la foto, «scrivici») e rimanda al Manifesto per il
perché; i quattro passi restano in un posto solo (il Manifesto, sezione
«Cosa stiamo costruendo»).

### 2.4 Le frasi che tornano

Contate sui testi delle pagine cardine:
- «Gratis per sempre, senza commissioni»: 5 volte fra home e landing
  operatore. È la promessa: va bene ripeterla, ma non nella stessa pagina
  tre volte (landing: hero, prezzi, chiusura).
- I tre benefici del Cerchio: 6 volte fra `/cerca-ritiro`, `/newsletter`,
  home, Manifesto.
- «raccontati uno a uno»: 4 volte (home, directory, Manifesto, aziende).
  È la firma di Aurya: la terrei in home e directory, non altrove.

### 2.5 Cosa NON toccare
- Le due porte in home e il loro ordine.
- Il modulo di `/cerca-ritiro` (14 vie, dove, budget): è la fonte della
  personalizzazione e ora è coerente con le categorie dei ritiri.
- La landing operatore nei suoi argomenti (è il testo del founder).
- `/costi`: breve, onesto, senza uscite: è una pagina di consultazione.

---

## 3. SEO

### 3.1 Cosa c'è già, ed è solido
- **Shell server-side** per ogni pagina pubblica: titolo, descrizione,
  canonica, robots, Open Graph, JSON-LD, corpo leggibile. Il client
  ripete gli stessi meta (verificato che non li annulli).
- **Noindex deciso dal dato**: `/esperienze` e le pagine categoria non
  entrano negli indici finché non hanno ritiri (soglia dieci per le
  categorie); la sitemap segue la stessa regola.
- **JSON-LD**: LocalBusiness con indirizzo, geo, rating, listino
  (profili); Event con luogo, date, offerta (ritiri); FAQPage sulla
  landing operatore; ItemList sulla directory; Organization + WebSite in
  home; BreadcrumbList.
- **Sitemap** in tre file (core, operatori, articoli), **llms.txt** con i
  pilastri, **IndexNow** al publish, HEAD per i fetcher AI, hreflang solo
  italiano + x-default (giusto: il contenuto è solo italiano).
- Registro delle rotte: l'ignoto fa 404, i doppioni storici sono 301.

### 3.2 Cosa ho corretto stasera (SEO-R)
1. **Profilo operatore**: titolo con le discipline e la città («Giulia
   Serra · Reiki, Meditazione a Ostuni | Aurya») invece di «ritiri a
   Ostuni», falso per chi non ne organizza; descrizione di ripiego che
   dice discipline, città, «servizi con prezzo, ritiri e recensioni
   verificate». Client e shell dicono lo stesso titolo.
2. **Landing del ritiro**: descrizione mai vuota («Ritiro di yoga a Ostuni,
   dal 4 ottobre 2026. Lo conduce X. Da 800 €, posti limitati…»); se il
   ritiro non ha foto, l'anteprima usa la copertina di chi lo organizza;
   briciole su `/esperienze/{categoria}`.
3. **Directory**: titolo «Operatori olistici e professionisti del
   benessere in Italia | Aurya» (la parola che la gente cerca).
4. **Anteprime di condivisione**: ogni pagina cardine ha la sua immagine
   (Cerchio, meditazioni, chi siamo, manifesto, aziende, costi,
   esperienze), non più il logo generico.
5. Titoli entro i ~60 caratteri per `/cerca-ritiro` e `/newsletter`.
6. `/strutture` e `/struttura` (segmenti prenotati) rispondono 404 invece
   di un guscio della home senza canonica.
7. La sitemap non dichiara più `/esplora-operatori`, che è un 301.
8. Le sei categorie nuove del Magazine hanno riga d'introduzione,
   copertina, icona ed etichetta.

### 3.3 Le parole chiave: come si posiziona Aurya
**Operatori** — le ricerche sono «reiki Ostuni», «operatore olistico
Bari», «sound healing Puglia», «yoga Lecce». Oggi il profilo risponde
con nome · discipline · città nel titolo, LocalBusiness con indirizzo e
geo, e la bio. Manca un **livello intermedio**: le pagine «disciplina ×
zona» (`/operatori/reiki/puglia`). La directory ha già le pagine per
categoria di servizio (`/operatori/{categoria}`) ma non per disciplina né
per regione. È la mossa con più resa: 40 discipline × 20 regioni, aperte
**solo quando hanno almeno tre operatori** (stessa regola dei ritiri),
con titolo «Operatori di Reiki in Puglia | Aurya», elenco vero, JSON-LD
ItemList. Da fare quando la directory supera i 30 profili: prima
sarebbero pagine sottili.

**Ritiri** — «ritiro yoga Puglia», «ritiro meditazione Toscana», «ritiro
olistico weekend». Le pagine `/esperienze/{categoria}/{regione}` esistono
e si accendono a dieci ritiri; il titolo dice «Ritiri di Yoga in Puglia».
Ogni ritiro ha Event JSON-LD: quando ce ne saranno, i rich results
(data, luogo, prezzo) sono già pronti.

**Magazine** — è il motore: 47 articoli, categorie che ora coincidono con
le categorie dei ritiri e con le vie di chi cerca, box «Trovami il mio
ritiro» per tema. Ogni articolo porta al form giusto con la via
preselezionata.

### 3.4 Cosa resta da fare (in ordine)
1. **Deploy**, poi in Search Console: reinviare le tre sitemap, chiedere
   l'indicizzazione di `/operatori`, dei profili nella rete, di
   `/cerca-ritiro` e `/entra-nella-rete`.
2. **Bing Webmaster Tools**: importare il sito da Search Console (un
   clic), verificare che IndexNow risponda (già implementato).
3. **Backlink**: ogni operatore nella rete mette il link al profilo nella
   bio di Instagram e sul suo sito (l'email «La tua pagina è online» lo
   chiede già); le strutture ricettive (fase 1) linkano Aurya; il
   Magazine cita fonti che possono citare.
4. **Pagine disciplina × zona** quando la directory supera i 30 profili.
5. **Recensioni**: sono nel JSON-LD (AggregateRating); con più profili
   recensiti, le stelle in SERP arrivano da sole.
6. **Velocità**: la home carica un video (poster prima); le pagine
   cardine hanno foto in webp. Da misurare in produzione con PageSpeed
   dopo il deploy; il calendario dei ritiri ora non ha più il video.
7. **Copy delle pagine** secondo la parte 2, se il founder è d'accordo:
   meno parole, stesse promesse.

### 3.5 Le anteprime quando si condivide un link (verificato)
| Link | Titolo | Descrizione | Immagine |
|---|---|---|---|
| home | Aurya · Il benessere inizia dalle persone | guide oneste + professionisti | tramonto (poster) |
| `/cerca-ritiro` | Trovami il mio ritiro · Ritiri olistici vicino a te | dicci cosa cerchi e dove… | girasoli |
| `/entra-nella-rete` | Per operatori olistici: il tuo spazio professionale, pronto oggi | una pagina tutta tua… | mani in mudra |
| `/operatori` | Operatori olistici e professionisti del benessere in Italia | scopri i professionisti… | logo Aurya |
| `/o/giulia-serra` | Giulia Serra · Reiki, Meditazione a Ostuni | «Reiki, meditazione e suono per tornare a respirare» | la sua copertina |
| ritiro | Nome · Ostuni · 4 ottobre 2026 | ritiro di yoga a Ostuni, dal…, lo conduce…, da 800 € | foto del ritiro o dell'operatore |
| `/newsletter` | Il Cerchio di Aurya · Meditazioni gratuite e ritiri in anteprima | entra nel Cerchio… | girasoli |
| `/esperienze` | Ritiri ed esperienze olistiche in programma | i ritiri… per data | il sole nelle mani |
| `/chi-siamo` | Chi siamo | Siamo Valentina e Davide… | la foto dei fondatori |

---

## 4. Il piano, in ordine

1. **Ora** (fatto stasera, in locale): SEO-R, menu, tassonomia unica,
   wizard solo italiano, verifica dei funnel.
2. **Copy** (serve il go del founder, è il suo testo): i tagli della
   parte 2 — landing operatore (tre blocchi), `/cerca-ritiro` (secondo
   form e seconda lista), home (riquadro «prossimamente», perché, fondatori),
   Chi siamo/Manifesto (i quattro passi in un posto solo), e la decisione
   su `/newsletter` (fondere o tenere).
3. **Deploy** completo (backend, frontend, nginx con force-recreate) e
   le azioni su Search Console e Bing del §3.4.
4. **Quando i numeri lo permettono**: pagine disciplina × zona (30
   profili), categorie ritiri (10 ritiri), Lettera per zona (50 iscritti
   in zona).
