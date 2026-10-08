# Le meditazioni: piano di refinement (lotto «MR»)

8/10/2026, sera. Richiesta del founder: copertine tutte dello stesso
formato, il cuore su ogni meditazione, l'ascolto che parte dove sei (niente
nuova pagina dalla playlist o dalle card), le categorie decise dal system
admin e assegnate quando si crea, e un design più moderno e stiloso della
casa. Tutto **senza rompere nulla**: motore, cancello, link condivisi, Crea.

Dipende da: `docs/PIANO_AURYA_SOUND_2026-10-08.md` (SN0–SN4, fatti in locale).

---

## 0. Le regole del lotto

- **Il motore non si tocca.** `engine/*` (synth, continuo, assets, veglia) resta
  com'è: il lettore nuovo lo USA, non lo riscrive.
- **La pagina `/frequenze/:slug` resta** com'è: è il link che si condivide,
  ha la shell SEO, il cancello, il Visual, il continuo. Il lettore in casa è
  un secondo modo di ascoltare, non un sostituto.
- **Ogni lotto dietro il suo flag** in `features/frequenze/stato.js`, le
  pagine di ieri restano accanto finché la prova dal vivo non è chiusa.
- **Una guardia per lotto** (`tests/test_meditazioni_mr*.py`), prova dal
  vivo a 375 px e desktop, build di produzione, suite completa pulita.
- **Nessuna migrazione distruttiva**: campi nuovi, default = oggi.

---

## MR1. Copertine, un formato solo (½ giornata)

**Oggi**: la foto si comprime in browser (lato lungo 1600, WebP) e si salva
così com'è; le card la ritagliano con `object-fit: cover`, ma la vetrina «Di
oggi» e la playlist la mostrano in proporzioni diverse: l'insieme sembra
disomogeneo.

**Dopo**: **un master quadrato** (1:1, 1200×1200, WebP) per meditazioni e
playlist, uguale ovunque; la vetrina e la pagina della playlist lo usano con
un velo di tono sotto, così anche una foto «sbagliata» sta bene.

1. **Server** (`services/copertine_sound.py`, Pillow già in uso per le
   copertine del Magazine): all'upload la foto si **ritaglia al centro** in
   quadrato e si ridimensiona a 1200, WebP qualità 84; si salva **una sola
   versione**. Vale per `POST /tracks/{id}/copertina` e
   `POST /playlists/{id}/copertina`. Le copertine già caricate (oggi: solo
   in locale) si rifanno con uno script `scripts/copertine_sound_quadrate.py`
   che rilegge i file e li riscrive.
2. **Client** (`CasaCampi`): l'anteprima prima del salvataggio mostra il
   quadrato che uscirà (ritaglio al centro); un avviso se la foto è più
   piccola di 800 px.
3. **Fallback bello** per chi non ha foto (decisione 4: solo rete di
   sicurezza): la copertina generata dal tono della categoria con il titolo
   in Cormorant, **generata una volta** sul server (come le cover degli
   articoli, `services/article_cover.py`) e salvata come `cover_url`, così
   la card social e l'email la mostrano uguale.
4. CSS: `.mcover` passa a `aspect-ratio: 1`, la vetrina «Di oggi» usa la
   foto quadrata a sinistra su desktop e in testa su telefono (16:9 con
   `object-position: center`), la pagina playlist già è quadrata.

**Non si rompe**: il campo resta `cover_url`; chi non carica nulla vede il
fallback; i test di SN0 restano verdi (si aggiunge solo il ritaglio).

---

## MR2. Il cuore su ogni meditazione (½ giornata)

**Oggi** il cuore c'è solo sulle card della casa; manca sulla vetrina «Di
oggi», sulle righe della pagina playlist, sulla pagina della meditazione e
nei risultati della ricerca (c'è, ma non nel riquadro «Riprendi»).

1. Un hook unico **`usePreferite()`** (`casa/preferite.js`): stato, toggle
   ottimistico, invito all'account se manca (lo stesso modal di oggi),
   cache in memoria per la sessione così ogni pagina la legge una volta.
2. Un componente **`Cuore`** unico (dimensione e colore oro di casa) usato
   in: card, vetrina «Di oggi», «Riprendi», righe della playlist, testata del
   player (`/frequenze/:slug`) e nel lettore in casa (MR3).
3. **Preferite anche per le playlist**: `PUT/DELETE /frequencies/favorites/playlist/{slug}`
   (stessa collezione, campo `kind`), cuore sulla card playlist e in testa
   alla pagina playlist; nella sezione «Il tuo spazio» una riga «Playlist
   salvate».

**Non si rompe**: `/frequencies/favorites` risponde come oggi (`slugs`), in
più `playlists`; `AccountFavorites` dell'account continua a leggere `slugs`.

---

## MR3. L'ascolto parte dove sei: il lettore in casa (2 giorni)

**Oggi** ogni «Ascolta» porta a `/frequenze/:slug`. **Dopo**: in casa e
nella playlist si ascolta **lì**, con un lettore fisso in basso; la pagina
della meditazione resta per il link condiviso, il Visual e il continuo.

1. **Estrarre il cuore dell'ascolto** da `PublicFrequencyPage` in un hook
   **`useAscolto(track)`** (`casa/useAscolto.js`): le tre vie già esistenti
   nello stesso ordine di oggi (anteprima 90 s se non sbloccati → master mp3
   con pass → sintesi dal vivo come ripiego), il tempo, play/pausa/seek,
   fine traccia, gli eventi di ascolto (SN0) e il «riprendi» (SN3). **La
   pagina della meditazione passa a usare lo stesso hook**: un solo motore
   d'ascolto, due interfacce. Questo è il passo delicato: si fa a parità di
   comportamento, con i test di oggi (anteprima, cancello, master, quartili)
   che devono restare verdi, e si prova sul telefono (iOS: il gesto, il pass
   pre-scorta).
2. **`LettoreBarra`** (`casa/LettoreBarra.jsx`): barra fissa in basso, sopra
   la barra di navigazione su telefono: copertina, titolo, chi guida,
   play/pausa, barra del tempo, precedente/successiva dentro una playlist,
   cuore, «apri» (va alla pagina intera per Visual/continuo). Un solo
   lettore per tutta la casa (contesto React `LettoreProvider` montato in
   `MeditazioniCasa` e `PlaylistPage`); cambiare meditazione sostituisce
   la traccia senza ricaricare la pagina.
3. **Il cancello in casa**: senza Cerchio l'anteprima suona nella barra e a
   90 s si apre un **foglio** (bottom sheet) con `CancelloLettera` e la
   copertina (SN2), stesso testo di oggi; sbloccato, riparte da capo col
   master. Mai un secondo cancello.
4. **Card e righe**: il tasto «▶» sulla card avvia nella barra; il titolo
   apre il **dettaglio in un foglio** (copertina grande, descrizione, cuore,
   «Ascolta», «Apri la pagina»); un link «condividi» copia l'URL pubblico.
   Nella playlist «Ascolta tutta» avvia la prima nella barra e continua da
   sola; ogni riga ha il suo «▶».
5. **Media Session** (predisposizione app, SN5): titolo, chi guida,
   copertina e play/pausa sullo schermo bloccato quando suona il master.
6. **Sipario di sicurezza**: la prima volta in casa, prima del primo suono,
   come oggi (`useSafetyGate`), una volta sola per 90 giorni.

**Non si rompe**: `/frequenze/:slug` resta e passa a `useAscolto` solo
quando i suoi test sono verdi; il flag `SOUND_LETTORE_IN_CASA` tiene il
vecchio comportamento (link alla pagina) finché non è provato.

---

## MR4. Le categorie: un registro del system admin (1 giorno)

**Oggi** la scoperta gira su `intent` (sei valori fissi nel codice), più
`momento` e `tags`. **Dopo**: le **categorie** le crea il system admin, in
un'area di Sound, e si assegnano quando si crea la meditazione; i filtri e
le righe della casa seguono il registro. Stesso disegno del registro vivo
delle discipline (DV1–DV3): slug immutabile, mai cancellazioni, ordine,
senza deploy.

1. **Registro** `sound_categorie` {slug, label, descrizione, tono
   (salvia/viola/acqua/oro/…), ordine, attiva, intent_di_base?} in
   `services/categorie_sound.py` (cache in memoria + ricarica come
   `discipline_vive`). **Seme**: le sei categorie di oggi (Dormire,
   Meditare, Rilassare, Concentrare, Elaborare, Energizzare) con lo stesso
   slug di `intent`, così **nulla cambia** finché il founder non ne aggiunge.
2. **Regia → Sound → Categorie** (`admin/SoundCategorieTab`): aggiungi,
   rinomina, riordina, spegni (mai cancella); anteprima del tono; conteggio
   delle meditazioni per categoria.
3. **Traccia**: campo `categoria` (slug del registro). In Crea, **si sceglie
   al salvataggio del titolo** (prima cosa, con il tono visibile) e si può
   cambiare in «Le mie tracce»; **obbligatoria per pubblicare**. Le tracce
   esistenti prendono `categoria = intent` (script una tantum, idempotente).
   `intent` resta: lo usa il motore per i preset e le pagine vecchie; la
   casa e i filtri leggono `categoria`.
4. **Playlist**: `categoria` facoltativa (la riga «Per dormire» mostra anche
   le playlist di quella categoria).
5. **Casa e ricerca**: filtri = categorie attive con meditazioni; righe «Per
   …» nell'ordine del registro; la pagina `/meditazioni?categoria=dormire`
   diventa un indirizzo condivisibile (shell SEO: CollectionPage per
   categoria, come le categorie del Magazine).

**Non si rompe**: `intent` e i suoi test restano; le API rispondono gli
stessi campi più `categoria`; senza registro, le sei di oggi.

---

## MR5. Il design della casa, più moderno (1,5 giorni)

Riferimenti: le app di meditazione (Calm, Insight Timer, Headspace) nella
loro parte migliore: **spazio, foto, poche parole**. Aurya ci mette il suo
buio caldo, l'oro di marca, il Cormorant.

1. **La testata**: saluto per chi ha l'account («Buonasera, Giulia») o «Le
   meditazioni», sottotitolo breve; la copertina di «Di oggi» **a tutta
   larghezza** con sfumatura dal basso, titolo sopra la foto, un solo tasto
   oro «Ascolta»; su desktop 2 colonne (foto 5/8, testo 3/8).
2. **Card** più grandi (raggio 20 px, ombra morbida, copertina quadrata, il
   «▶» che appare al passaggio e sempre su telefono), titolo su due righe
   massimo, sotto chi guida · durata; il cuore in alto a destra.
3. **Righe** con titolo + «Vedi tutte» (apre la griglia filtrata), scorrimento
   a scatti con 1,3 card visibili su telefono (si capisce che si scorre),
   frecce su desktop.
4. **Cerca** come **foglio**: tocchi «Cerca» nella barra → foglio con il
   campo, le categorie come pastiglie con il tono, durata e voce; risultati
   sotto in griglia. Fuori dal foglio la casa resta pulita.
5. **Barra in basso** in vetro (sfocatura), icone più grandi, etichette
   solo sull'attiva; il lettore (MR3) si appoggia sopra.
6. **Scheletri** durante il caricamento (niente pagina vuota che salta),
   transizioni di 200 ms, `prefers-reduced-motion` rispettato.
7. **Tipografia**: titoli 28/22/17, corpo 15, etichette mono 11 maiuscole
   come oggi; contrasto verificato (AA) sul buio.
8. **Stati vuoti** con una frase e un gesto («Ancora nessuna preferita:
   tocca il cuore su una meditazione»).

Si fa **per ultimo**, sopra MR1–MR4, con screenshot prima/dopo a 375 px e
1280 px per il founder.

---

## Ordine, tempi, cancelli

| Lotto | Cosa | Giorni | Flag |
|---|---|---|---|
| MR1 | copertine quadrate + fallback generato | ½ | nessuno (solo upload) |
| MR2 | il cuore ovunque + playlist preferite | ½ | nessuno |
| MR4 | registro categorie + Regia + Crea | 1 | `SOUND_CATEGORIE_VIVE` |
| MR3 | lettore in casa (hook unico + barra + foglio) | 2 | `SOUND_LETTORE_IN_CASA` |
| MR5 | design della casa | 1,5 | nello stesso flag di SN1 |

Totale **≈ 5,5 giorni**. MR4 prima di MR3 perché il lettore mostra la
categoria; MR5 per ultimo perché disegna sopra tutto. Ogni lotto: commit,
nessun deploy senza «go».

## Stato (8/10/2026, sera)

- **MR1 FATTO** in locale (`da73cd03`): copertine 1:1 1200 WebP all'upload (traccia e playlist), copertina generata alla pubblicazione se manca (tono + anello + titolo), script `copertine_sound_quadrate.py`, card quadrate. Nota per MR5: il badge «Presto nel Più» e il cuore coprono l'etichetta «Aurya Sound» delle copertine generate: si abbassa l'etichetta o si sposta il badge.
- **MR2 FATTO** in locale (`c3d72ed0`): hook `usePreferite` + componente `Cuore`; cuore su card, vetrina, riprendi, playlist (card e pagina, righe), player; playlist salvate (stessa collezione, prefisso) nel tuo spazio e nell'account.
- **MR4 FATTO** in locale (`f6f800c1`): registro `sound_categorie` con seme «Meditazioni guidate», Regia → Sound → Categorie, select in Crea e in Le mie tracce, obbligo per pubblicare in pubblico, filtri e righe della casa per categoria, `?categoria=`.
- **MR3 FATTO** in locale (`77f694d6`): un lettore solo per casa e playlist (`casa/lettore.js` + `LettoreBarra`) sui due file che la pagina pubblica già usa (anteprima 90 s, master mp3) con lo stesso `lettoreDaUrl`; **niente sintesi dal vivo nella barra**: una meditazione senza master si apre nella pagina intera. Sipario, cancello nel foglio, eventi, riprendi/recenti, playlist che continua. Card: copertina suona, titolo apre il foglio di dettaglio; playlist: «Ascolta tutta» e righe nella barra. La pagina `/frequenze/:slug` e il motore non cambiano (scelta prudente rispetto al piano, che prevedeva di far passare anche la pagina dall'hook: si farà quando il lettore in casa avrà girato in prod). Lezione: barra, foglio e sipario vanno DENTRO il `.fqz` (gli stili sono scoped). Al pubblico niente Visual (`VISUAL_PUBBLICO_ATTIVO=false`).
- **MR6 FATTO** in locale (`6fb07fc8`): la landing di `/sound` torna, ottimizzata (via CALM/GROUND, rimando alla casa, vetrina del giorno da `GET /frequencies/public/vetrina`); l'hub resta dietro `SOUND_HUB_SEMPLICE=false`.
- **MR5 FATTO** in locale: testata col saluto, vetrina a tutta larghezza su telefono, card più grandi con titolo su due righe, «Vedi tutte» (quando la riga è tagliata), ricerca nel foglio su telefono, pastiglie col tono della categoria, barra in vetro, scheletri, stati vuoti, `prefers-reduced-motion`.

**Il lotto MR è completo in locale.** Rimandi aperti: badge/cuore che coprono l'etichetta delle copertine generate (piccolo), la pagina intera che passi dall'hook del lettore (dopo la prova in prod), la ricerca inline su tablet (oggi dal foglio sotto 900 px).

## Decisioni del founder (8/10/2026, sera)

1. **Copertine 1:1.**
2. **Una sola categoria per ora: «Meditazioni guidate».** Le altre le crea il
   founder in prod dalla Regia e devono comparire subito nella scelta di
   «nuova meditazione». Quindi il seme NON sono le sei di `intent`: il
   registro parte con una voce; `intent` resta interno (motore e pagine
   vecchie), le tracce esistenti prendono «meditazioni-guidate».
3. **Tutto si ascolta subito, dove si è.** Al pubblico niente Visual (c'è la
   copertina) e niente pagina in più per la singola meditazione: card → suona
   nella barra, foglio di dettaglio per leggere. **Solo la playlist ha la sua
   pagina** con le tracce. `/frequenze/:slug` resta come **link condiviso e
   pagina SEO** (email, social), col lettore e senza il Visual per il pubblico.
4. **Categoria obbligatoria per pubblicare.**
