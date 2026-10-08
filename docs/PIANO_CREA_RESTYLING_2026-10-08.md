# Crea: piano di restyling (lotto «CR»)

8/10/2026, sera. Richiesta del founder: «Crea è rimasto col vecchio design:
restyling per renderlo più user-friendly e funzionale, design moderno,
stiloso, facile. Attento a non buggare nulla: come funzionalità, Crea
funziona bene». Solo piano, nessuna modifica al codice.

La casa delle meditazioni (lotto MR) ed Esplora (lotto ES) sono il
riferimento: stessa grammatica (card, pastiglie, fogli, barra in basso,
selettore a tre), `casa.css` + `esplora.css`.

## 0. Diagnosi (dal codice e dallo schermo, 375 px e desktop)

### Com'è fatto
- **Crea è una sezione di `FrequenzePage.js`**: 3.100 righe, un solo
  componente, 52 `useState`, quattro viste da URL (`/sound/esplora|crea|
  impara|tracce`). Ogni segmento sconosciuto cade su `explore`. Il CSS è
  `frequenze.css` (1.573 righe), condiviso da tutte le viste.
- **Il motore è a parte e sano**: `engine/*` (synth, render MP3, voce,
  spazio/stanza, guida respiro, continuo, veglia), `visual/*` (scena,
  Studio), `api/frequencies.js` (20 chiamate), `CasaCampi` (campi della
  casa, playlist). Le ricette hanno un contratto (`scorePayload()`,
  `score_version`, firme salvata/pubblicata) pinzato da 15 file di test.
- **Cosa funziona e non si discute**: ascolto in sessione con riavvio
  dolce, protocolli, livelli neuro/base/voce/guida, taglio e pulizia della
  voce, durata auto/fissa, nasce/si spegne, stanza e spazio in cuffia,
  scena, export MP3, salva/aggiorna bozza, pubblica (Meditazioni o
  riservata), campana d'uscita se la sessione non è salvata, URL =
  verità (`?bozza=`), avvisi cuffie e memoria.

### Cosa si vede (telefono 375 px)
| Cosa | Misura | Perché è un problema |
|---|---|---|
| **Testata doppia** prima dello strumento: h1 «Aurya Sound» + sottotitolo, pastiglia «Controindicazioni», barra delle stanze (Esplora · Lab · Impara · Crea · Le mie tracce), riquadro cuffie | ~520 px | lo strumento comincia a metà del secondo schermo; «Le mie tracce» sborda a destra (pagina larga 411 su 375) |
| **La barra di comando** (`createbar`) è sticky e alta | **447 px** (233 su desktop) | copre il 55 % dello schermo: la linea del tempo scorre *sotto* la barra; dentro ci stanno 9 cose (▶, Reset, scena, durata, Impostazioni col riassunto, seekbar, stato, Esporta, Salva/Pubblica) |
| Lo **stato** (`status`) in mono dentro la barra | | messaggi di protocollo, errori di tempo, conferme di salvataggio nello stesso posto, senza gerarchia |
| **L'ordine della pagina**: barra → scena → avvisi → protocolli → leggio voce → legenda A/B/C → linea del tempo → nota binaurale | | **la sessione, cioè ciò che si sta costruendo, sta in fondo**, sotto i protocolli e la voce |
| **Un livello** (`row`): nome, volume, entra/esce, poi 3–4 righe di controlli con etichette mono sottolineate (metodo, timbro, portante, battito da→a, curva, respiro, muto, spazio, effetto, pulizia, parte da) | 300+ px a livello; 2 livelli = 1 schermo | tutte le opzioni sempre a vista: per cambiare un volume si scorre tra portanti e curve |
| **Aggiungere** un suono: in Crea non c'è un «+»; si aggiunge dai protocolli, dal leggio voce, o da Esplora («+ sessione» sulle card, basi, guide) | | la via Esplora → Crea è il gesto base del compositore, ma **vedi il punto sotto** |
| **Le mie tracce**: 19 card da 570 px l'una | 9.700 px | ogni card mostra tutto sempre aperto (copertina, categoria, momento, tag, accesso, Più, vetrina, annuncio, ascolti, 3 bottoni) |
| Leggio voce in mezzo alla pagina, «Spezzoni senza sessione (6)» aperto, select «prova gli spezzoni con» | | utile, ma prima della sessione |
| Legenda A/B/C e nota binaurale ripetute in Crea | | testo della biblioteca, già nel foglio ⓘ di Esplora |

### Un buco lasciato dal lotto ES (solo in locale, non in prod)
Dopo ES, `/sound/esplora` è la biblioteca pubblica nuova, senza «+
sessione». La biblioteca **del compositore** (frequenze con «+ sessione»,
basi con momento/timbro, upload, guide respiro) è ancora viva ma **non ha
più un link**: risponde su qualunque segmento sconosciuto, ad esempio
`/sound/libreria` e `/sound/libreria?mondo=suoni` (verificato: 36
schede e 259 basi con «+ sessione»). Oggi i link del compositore (barra
delle stanze «Esplora», il vuoto «Torna a Esplora», il piede «Vai a Crea»)
portano alla pubblica. **Si chiude in CR0, mezz'ora.**

## 1. Il principio

**Lo strumento al centro, tutto il resto a portata.** Crea ha tre zone:
1. **la barra**, una riga sola, sempre a vista: ▶/⏸, il tempo con la
   barra di scorrimento, la pill della durata, «+ Aggiungi», «⋯»;
2. **la sessione**, subito sotto: la linea del tempo e i livelli come
   card (testata compatta, corpo ripiegabile);
3. **il cassetto «Aggiungi»**, un foglio con tutto ciò che entra in una
   sessione: frequenze, basi, la tua voce, guida del respiro, protocolli.

**Il mix nasce dalle fonti** (founder, 8/10 sera): in Crea servono i
suoni e le tracce **a un tocco, senza cambiare pagina**, altrimenti non
si mixa. Quindi il cassetto non è un menu: è il **banco del mix**, sempre
accanto alla sessione. Su desktop è una **colonna fissa a sinistra**
(fonti) con la sessione a destra; su telefono un **foglio a mezza
altezza** che lascia la sessione e la barra a vista. Si cerca, si
ascolta in anteprima **mentre la sessione suona** (si combinano, come
oggi) e «+ sessione» mette il suono al punto del cursore.

Salva e Pubblica stanno in una **barra fissa in basso** (come il lettore
della casa), con lo stato che parla lì (un toast, non una riga mono).
Le Impostazioni (titolo, categoria, nasce/si spegne, stanza), la scena,
Reset, Esporta stanno dietro «⋯».

Il componente resta **uno**: stato, effetti e funzioni di `FrequenzePage`
non si toccano. Il restyling è un **vestito nuovo** (JSX della vista
`create`/`mine` + un CSS suo) sugli stessi handler, gli stessi `testid`,
lo stesso contratto delle ricette.

## 2. I lotti

### CR0 La via per aggiungere (½ giornata) — da fare subito
- La biblioteca del compositore ha un indirizzo suo: `/sound/libreria`
  (+ `?mondo=suoni`, `?categoria=`), cioè la vista `explore` di
  `FrequenzePage` com'è oggi. `PATH_VIEW` la riconosce esplicitamente.
- I link del compositore puntano lì: la barra delle stanze (voce
  «Libreria» al posto di «Esplora»), il vuoto di Crea («Apri la
  libreria»), il piede «Vai a Crea» resta. In Crea, in attesa di CR3,
  **due bottoni a vista** sopra la sessione: «Suoni» (`/sound/libreria?
  mondo=suoni`) e «Frequenze» (`/sound/libreria`): la sessione in
  costruzione sopravvive al cambio di pagina (stesso componente), quindi
  si va, si aggiunge, si torna col piede «Vai a Crea».
- La pubblica `/sound/esplora` non cambia. Guardia: `tests/test_crea_cr0.py`.

### CR1 Testata e barra (1 giornata)
- Nella vista Crea spariscono h1 + sottotitolo + riquadro cuffie: resta la
  passerella (`SoundTopbar`, «Crea» corrente) e un **selettore a tre**
  (Crea · Fonti · Le mie tracce) con la stessa forma di quello di
  Esplora; «Fonti» apre il banco del mix (CR3; fino ad allora porta a
  `/sound/libreria`); la pastiglia Controindicazioni resta nella topbar.
- `createbar` diventa **una riga sticky ≤ 64 px**: ▶/⏸ (con «Preparo…»),
  tempo corrente / durata con la seekbar (`fq-crea-seekbar`), pill durata
  (`fq-durata`, apre il foglio durata com'è), «+ Aggiungi» (CR3), «⋯».
- «⋯» apre un foglio: Impostazioni (titolo, categoria `fq-categoria`,
  nasce/si spegne, stanza `fq-stanza`, nota spazio), Guarda il suono
  (`fq-guarda`), Reset, Esporta MP3 (`fq-export`). Il riassunto delle
  impostazioni (`fq-setup-riassunto`) vive sotto la barra come riga
  discreta.
- **Barra in basso fissa**: `Salva bozza / Aggiorna bozza` (`fq-save`),
  `Pubblica` / `Pubblicata, ritira` (`fq-publish`/`fq-unpublish`), e lo
  stato come toast che si spegne da solo (gli errori di tempo restano
  finché non si tocca).
- Gli avvisi (memoria, cuffie) diventano una riga sotto la barra, solo
  quando servono (già così).

### CR2 La sessione al centro (1,5 giorni)
- La linea del tempo subito sotto la barra. La `helpstrip` diventa un
  «?» che apre un foglio.
- **Fasi** come chip sopra il righello (aggiungi col tocco sul righello,
  rinomina in un foglio invece di `window.prompt`).
- **Il livello come card**: testata compatta sempre a vista — icona per
  tipo (onda/base/voce/respiro), nome (editabile al tocco), intervallo
  «1:30 → 4:00», volume (slider corto), muto, ×; sotto, la lane
  trascinabile (com'è, stessi handler `dragX`). Il corpo si apre con un
  tocco e raggruppa i controlli esistenti per **famiglia**: *Suono*
  (metodo, timbro/colore, portante, battito da→a, curva, respiro), *Tempo*
  (entra a, esce a, «da qui/fin qui», parte da), *Spazio* (spazio in
  cuffia), *Voce/Respiro* (effetto, quantità, pulizia, schema, respiri,
  round, vuoto/pieno/recupero, campana). Stessi `patchLayer`/`patchGuida`,
  stessi `testid` (`t-in-`, `t-out-`, `fq-space-`, `fq-guida-*`,
  `fq-clean-sel-`, `fq-layer-color`).
- Un solo livello aperto alla volta su telefono; su desktop quanti si
  vuole.
- Il vuoto: «La tua sessione è vuota» con tre bottoni veri (Protocollo,
  Libreria, Registra la voce).

### CR3 Il banco del mix (2 giorni)
- «+ Aggiungi» (barra) e «Fonti» (selettore) aprono il **banco**: su
  desktop (≥ 1024 px) una **colonna fissa a sinistra**, ~360 px, che
  resta aperta mentre si lavora sulla sessione a destra; su telefono un
  **foglio a mezza altezza** trascinabile (mezzo / tutto schermo) che
  lascia barra e sessione a vista; l'audio non si ferma mai.
- Cinque schede, con **un campo di ricerca comune** (nome, Hz, categoria,
  momento, titolo delle tracce):
  **Frequenze** (famiglie → schede, le card compatte di `BibliotecaPage`
  con ▶ anteprima e «+ sessione»: `addLayer`), **Basi** (momento ×
  timbro, le card di oggi con ▶ e «+ sessione»: `addSoundToSession`,
  upload per chi può), **Voce** (il leggio: REC, clip con ▶/taglio/
  pulizia/«+ sessione», spezzoni senza sessione), **Respiro** (guide:
  `fq-guida-add-`), **Protocolli** (le sei card con grado e durata:
  `loadProtocol`, con la conferma se la sessione non è vuota).
- **Le mie tracce come fonte** (nuova): nella scheda **Tracce** le
  proprie bozze e tracce pubblicate con «▶ anteprima» e «+ i suoi
  livelli», che **aggiunge i livelli di quella traccia alla sessione
  corrente** (dal `score` già salvato, spostati al punto del cursore,
  con un suffisso nel nome). È solo client: nessun backend. Serve a
  riusare una base già fatta (un'apertura, un tappeto) dentro un mix
  nuovo. «Apri» invece la sostituisce (com'è oggi, con la campana).
- Anteprima e sessione **insieme**: il ▶ di una scheda nel banco suona
  sopra la sessione in corso (come oggi in Esplora), così si prova il
  suono nel contesto prima di aggiungerlo; «+ sessione» lo mette al
  punto del cursore, e la card del livello nuovo lampeggia una volta.
- Il banco rende inutile uscire da Crea: `/sound/libreria` resta come
  pagina (CR0) ma i link del compositore puntano al banco.
- Il leggio voce esce dalla pagina: i clip usati si vedono nei livelli.

### CR4 Le mie tracce (1 giornata)
- Card compatte in griglia (copertina quadrata, titolo, stato come
  pastiglia: Bozza / Riservata / Nelle Meditazioni, durata · livelli ·
  ascolti), **un gesto primario** per stato (com'è: `fq-pubblica-
  meditazioni`, `fq-pubblica-riservata`, `fq-link-riservati`, Copia
  link) e «Apri» che porta in Crea con `?bozza=`.
- I campi della casa (`CampiCasa`: copertina, categoria, momento, tag,
  accesso, vetrina, annuncio, ascolti) dietro «Modifica» in un foglio;
  il componente non cambia, cambia dove si apre.
- Filtri in testa (Tutte · Bozze · Riservate · Pubbliche) e cerca; le
  playlist (`PlaylistPannello`) nel loro pannello sotto, com'è.

### CR5 Il vestito (trasversale, dentro CR1–CR4)
- `crea/crea.css` sui gettoni della casa (`casa.css`, `esplora.css`):
  card raggio 20, pastiglie, fogli, barra in basso, scheletri; etichette
  non più sottolineate; select e input vestiti; tipografia 22/17/15,
  mono 11 solo per i numeri.
- 375 px senza scroll orizzontale, bersagli ≥ 44 px, `prefers-reduced-
  motion`, la legenda A/B/C e la nota binaurale nel foglio ⓘ.

### CR6 Potatura (½ giornata, dopo CR3)
- Le viste `explore`/`impara` dentro `FrequenzePage` servono solo al
  compositore (`/sound/libreria`): `TriggerStudio` e i CTA pubblici
  escono da lì; `StanzeSound` diventa il selettore a due.
- Niente cancellazioni di codice che un test legge: si spegne, non si
  toglie.

## 3. Come non rompere nulla
- **Flag** `SOUND_CREA_NUOVO` in `stato.js`: ogni lotto si accende con
  il flag; `?vestito=vecchio` mostra la vista di oggi finché il founder
  non dà l'ok. Il flag si toglie a fine lotto, come per la casa.
- **Il componente resta `FrequenzePage`**: stato, effetti, funzioni,
  `scorePayload()`, `score_version`, firme, `?bozza=` non si toccano. Il
  JSX della vista `create` e `mine` si sposta in `crea/CreaVista.jsx` e
  `crea/TracceVista.jsx` come **funzioni di rendering che ricevono
  l'oggetto dei gesti** (play, patchLayer, save…), non come componenti
  con stato proprio.
- **Stessi `testid`**: i 15 file di test che leggono `FrequenzePage`
  restano verdi; le stringhe pinzate (`cb-play${playing ? ' suona' : ''}`,
  `fqz-voicedesk`, `cb-collapse`, `+ sessione`, `StanzeSound`,
  `view === 'explore' && canCompose && (`, `setView('create')`) restano
  nel file o nel modulo che il test legge. Nuove guardie
  `tests/test_crea_cr*.py`.
- **Prova a mano a ogni lotto** (375 px e desktop): protocollo → ascolta
  → cambia volume/entra/esce mentre suona → salva → ricarica → riapri
  la bozza → pubblica → ritira; voce: REC → taglio → pulizia → «+
  sessione» → salva; base con loop e «parte da»; guida respiro con
  round; durata fissa/auto; export MP3; campana d'uscita; «Le mie
  tracce»: copertina, categoria, Nelle Meditazioni, link riservati.
- **Suite completa e build** a ogni lotto; commit per lotto; nessun
  deploy senza «go».

## 4. Cosa NON si tocca
`engine/*`, `visual/*` (AuryaMode, StudioScena), `api/frequencies.js`,
il backend delle tracce/voce/basi, `CasaCampi` e `PlaylistPannello`
(SN0), `SafetyCurtain`, la biblioteca pubblica (`esplora/*`), le
ricette salvate (le bozze di ieri si aprono e suonano uguali).

## 5. Ordine e tempi

| Lotto | Giorni | Flag |
|---|---|---|
| CR0 la via per aggiungere | ½ | nessuno (solo link) |
| CR1 testata e barra | 1 | `SOUND_CREA_NUOVO` |
| CR2 la sessione al centro | 1,5 | idem |
| CR3 il banco del mix | 2 | idem |
| CR4 le mie tracce | 1 | idem |
| CR6 potatura | ½ | nessuno |

Totale **≈ 6,5 giorni**, CR5 dentro gli altri.

## 7. Stato (8/10 sera, «procediamo»)
- **CR0 FATTO** (commit `75bd0a9d`): `/sound/libreria` (+ `?mondo=suoni`) è la
  biblioteca del compositore; in Crea la riga «Aggiungi alla sessione»
  (Frequenze · Suoni · La tua voce); la barra delle stanze dice «Libreria»
  per chi compone; shell SEO noindex. Guardia `tests/test_crea_cr0.py`.
- **CR1 + CR2 + CR3 FATTI** in locale (flag `SOUND_CREA_NUOVO`,
  `?vestito=vecchio` mostra la vista di prima):
  - `crea/CreaVista.jsx` + `crea/crea.css`: selettore Crea · Fonti · Le mie
    tracce; barra a una riga (▶, scorrimento coi tempi, pill durata, «+»,
    «⋯»), 64 px su desktop e due righe (114 px) sul telefono; riga del
    riassunto (titolo · stanza · nasce/si spegne · categoria) che apre il
    foglio «La sessione» (titolo, categoria, nasce/si spegne, stanza, Guarda
    il suono, Esporta MP3, Svuota); foglio della durata con gli stessi
    preset; piede fisso con Salva/Aggiorna, Pubblica/ritira e lo stato come
    toast (7 s).
  - la sessione subito sotto: i livelli come card ripiegabili (nome, volume,
    muto e la lane a vista; tempo, suono, spazio, voce con un tocco: `aperti`
    in `renderRow`, stessi handler), 114 px chiusi sul telefono; il vuoto
    con quattro bottoni che aprono il banco.
  - il **banco del mix**: colonna fissa 380 px su desktop (≥ 1024), foglio a
    58 vh (o 90 vh) sul telefono; schede Frequenze (famiglie → schede, ▶ in
    anteprima sopra la sessione via `toggleCard`, «+» via `addCardToSession`,
    «ferma tutto / + tutte alla sessione»), Suoni (momento × timbro, ▶, «+»),
    Voce (il leggio di sempre, `leggioVoce`), Respiro (le guide), Protocolli
    (Carica, con la conferma di sempre), **Le tue tracce** («+ livelli»:
    `aggiungiLivelliDa` porta i livelli della traccia nella sessione dal
    punto in cui stai ascoltando; «Apri» la sostituisce). Ricerca comune.
  - in `FrequenzePage`: `kit` (l'oggetto dei gesti), `lineaDelTempo` e
    `leggioVoce` estratti una volta per i due vestiti, `aggiungiLivelliDa`,
    `data-vestito="nuovo"` sulla radice (la testata e la riga cuffie non si
    vedono nel nuovo; la pastiglia Controindicazioni e il sipario restano).
  - Verificato a 375 px e 1240 px: protocollo → ▶ → banco (anteprima e «+»
    mentre suona) → suoni → tracce «+ livelli» → «⋯» → durata → Salva
    abilitato. Guardia `tests/test_crea_cr1.py`.
  - Rimandi: l'upload delle basi della Regia resta nella libreria
    (`/sound/libreria?mondo=suoni`), non nel banco; il «?» della linea del
    tempo (helpstrip) è nascosto, tornerà come foglio in CR5.
- **CR4 FATTO** in locale (`crea/TracceVista.jsx`): card compatte in griglia
  (1/2/3 colonne; 190 px sul telefono contro 570), copertina quadrata che
  apre in Crea, stato come pastiglia, un gesto primario per stato con gli
  stessi handler e testid di TM1/TM2, «Modifica» che apre i campi della casa
  (`CampiCasa`, intatto) in un foglio con «Elimina», filtri coi conteggi e
  cerca, le playlist e i link riservati com'erano. Pagina da 9.700 a 4.463 px
  sul telefono. Guardia `tests/test_crea_cr4.py`.
- **CR6 FATTO** in locale: su `/sound/libreria` chi compone vede il selettore
  Crea · Fonti · Le mie tracce («Fonti» segnato) al posto della testata
  doppia; la libreria sotto è quella di sempre. Il trigger di Studio già si
  nascondeva a chi ha le chiavi. Non si è cancellato codice che un test legge:
  il vestito vecchio resta intero dietro `?vestito=vecchio` (si pota quando il
  founder dà l'ok al nuovo, aggiornando i pin).

## 8. Cosa resta da decidere
- Quando il founder dà l'ok al vestito nuovo: togliere il flag e il vestito
  vecchio (`createbar`, `fq-fonti`, la vista `mine` vecchia) e aggiornare i
  pin che li leggono (`test_ascolto_telefono` su `cb-play`, `test_frequencies_fq`
  su `cb-collapse`/`fqz-voicedesk`, `test_tracce_mie_tm` su `mine-del`,
  `test_sound_sn0` su `CampiCasa traccia={d}`).
- L'upload delle basi della Regia resta nella libreria, non nel banco.
- Tutto il lotto è solo in locale: deploy su «go».

## 6. Domande per il founder
1. **CR0 subito**? È il buco lasciato da ES (solo in locale): mezz'ora.
2. **Il banco del mix** (CR3): colonna fissa su desktop, foglio a mezza
   altezza su telefono, con Frequenze · Suoni · Voce · Respiro ·
   Protocolli · **Tracce** e una ricerca sola: va bene?
2b. **Le tue tracce come fonte**: «+ i suoi livelli» aggiunge i livelli di
   una tua traccia alla sessione corrente (riuso di una base già fatta):
   lo vuoi?
3. **I livelli come card ripiegabili** (volume, tempo e muto sempre a
   vista; il resto si apre con un tocco), o tutto a vista come oggi?
4. **Salva/Pubblica in una barra fissa in basso** (come il lettore della
   casa) o in alto nella barra?
5. **Le mie tracce**: i campi della casa dietro «Modifica», o sempre a
   vista come oggi?
