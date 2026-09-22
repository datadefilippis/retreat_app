# Aurya Sound · Crea — analisi e piano «esperienze immersive» (22 settembre 2026)

Obiettivo del founder: consolidare Crea come strumento di lavoro (prima suo, poi
dei clienti paganti) per creare sessioni di breathwork, danza estatica e
meditazioni in cinque stili (catartico, rilascio, energizzante, amorevole,
rilassante), con un'immersione profonda in cuffia («9D», rotazione a 360°),
senza perdere la semplicità di Crea. Prima del deploy arrivano altre tracce
registrate dal founder (il suo respiro, i conteggi «inspira 1-2-3-4»).

Tutto quello che segue è misurato sul codice e sui file, non ricordato.

---

## 1. Dove siamo (fatti)

**La libreria** (`audio_assets`, 185 suoni in locale, 185 in prod, 74 tappeti):

| categoria (timbro) | suoni | | momento del viaggio | suoni |
|---|---|---|---|---|
| ambient | 104 | | senza momento | 61 |
| natura | 21 | | arrivo | 43 |
| ritmi | 21 | | ascesa | 27 |
| droni | 15 | | attivazione | 20 |
| campane | 10 | | rientro | 20 |
| corpo | 6 | | **catarsi** | **14** |
| voce | 6 | | | |
| transizioni | 2 | | | |

Due assi ortogonali già in piedi: il **timbro** (8 categorie, parità
backend/frontend sotto guardia) e il **momento** (arrivo → attivazione →
catarsi → ascesa → rientro). L'asset non ha campi `bpm`, `energia`, `tags`,
`loop`: loop e livello sono proprietà del layer nella ricetta.

**Crea** è una ricetta (`frequency_tracks`, `score_version` 1-3), non un file:
tre tipi di strato (`audio` dalla libreria, `voice` registrata in-app con
pulizia e preset riverbero/eco, `neuro` sintetizzato: binaurale, isocrono,
bilaterale, rumore, tono, drone, shepard, **breath**), fino a 24 strati, 60 s
→ 30:00, fasi, visual. Anteprima dal vivo (`engine/synth.js`), master MP3
192k reso una volta nel browser dell'autore alla pubblicazione
(`engine/render.js`, OfflineAudioContext), ascolto pubblico = streaming del
master. Sei ricette pronte (`content/protocolli.js`: Dormire, Meditare,
Rilassare, Concentrare, Elaborare, Energizzare), tutte di sintesi.

**Il respiro** esiste già come sintesi: metodo `breath` (inviluppo, altezza
che scivola, tocco alla svolta, `inhale/exhale`) e l'esperienza `/sound/respiro`
(10 minuti a sei atti al minuto, rapporto 4:6). Nessuna voce registrata,
nessun conteggio, nessun respiro vero, nessuna struttura a round.

**Lo spazio**: nel motore di Crea **non c'è spazializzazione**. Esistono uno
StereoPanner solo per il metodo bilaterale, un pan fisso 0,35 sul doubling
della voce e un riverbero sintetico (ConvolverNode con impulso generato) sulla
voce. L'unico HRTF del repo è nel Lab (`lab/fenomeni.js`, «Orbita»: PannerNode
HRTF con due LFO in quadratura sulle posizioni X/Z). Il render offline e
l'anteprima dal vivo costruiscono il grafo ciascuno per conto proprio: ogni
cosa nuova va scritta UNA volta in un modulo condiviso (come `attackRelease`).

**Le 23 tracce nuove** (`~/Desktop/ecstatic_dance/estasi`, tutte mp3, 6 h di
materiale): 9 in `meditative`, 11 in `move`, 3 in `voice`. I nomi sono nel
formato di Pixabay (autore-titolo-id): la licenza da scrivere è la Pixabay
Content License, da confermare. Due tracce da 25 minuti e una da 21 diventano
tappeti (190 s) come le altre lunghe.

**Il file breathwork allegato** («21 Day Awakening, Week 1, IHT 2 rounds»,
11:38, un'unica traccia musica+voce): l'inviluppo mostra due round di
respirazione ritmica (0:00-4:40 e 6:40-7:40) con un periodo di **2,0 s per
fase**, cioè inspira 4 tempi / espira 4 tempi a circa 120 bpm, quindici
respiri al minuto; fra i round le fasi di ritenzione (4:40-6:40 e 7:40-8:40)
sono più quiete di 4-6 dB sui bassi ma la musica non si ferma; poi recupero e
una coda di integrazione (10:00-11:38) in dissolvenza. È esattamente la
struttura da riprodurre come ricetta: **round = respirazione ritmica →
ritenzione a polmoni vuoti → ritenzione a polmoni pieni → recupero**.

Il secondo file (Week 2, 4 round, 22:30) conferma e aggiunge la
progressione: 42 s di arrivo, round 1 di quasi 4 minuti di ritmo, poi round
via via più corti (1-2 minuti) con ritenzioni da 1 a 3,5 minuti, coda di
integrazione di 2,5 minuti; il periodo di fase scende a **1,5 s** (respiro
più rapido della settimana 1). Quindi la ricetta del respiro deve permettere
**per ogni round** un ritmo, una durata di respirazione e una durata di
ritenzione diversi, non un solo schema ripetuto.

---

## 2. Dove vanno le 23 tracce (proposta, da confermare all'ascolto)

Le categorie attuali sono per timbro. Per le esperienze servono tre parole
nuove, e una pulizia:

- **`danza`** (nuova): brani ritmici che portano il corpo, con un tempo.
  Oggi finirebbero in «ritmi» (che è percussione pura) o in «ambient».
- **`respiro`** (nuova): le guide del respiro registrate (conteggi, respiro
  del founder, campane di svolta). Vuota oggi, si riempie con le registrazioni.
- **`melodie`** (nuova): brani con un tema (violoncello, pianoforte, flauto,
  orchestrale). Oggi stanno in «ambient», che con 104 suoni su 185 è un
  contenitore senza significato. Non si sposta nulla d'ufficio: si propone
  una riassegnazione assistita (il censimento propone, il founder conferma
  ascoltando), come per i momenti.

| file | durata | categoria | momento | note |
|---|---|---|---|---|
| meditative/berwick soundscape for learning and relaxing | 21:14 | ambient | arrivo | tappeto |
| meditative/calling, angelic female vocal | 7:50 | voce | ascesa | voce cantata, non parlata |
| meditative/dereen cinematic orchestral uplifting | 4:15 | melodie | ascesa | |
| meditative/full moon deep relaxation | 25:00 | ambient | rientro | tappeto |
| meditative/jindalba, ancient flute river | 10:00 | melodie | arrivo | flauto su acqua |
| meditative/meditation at the river | 25:00 | ambient | arrivo | tappeto |
| meditative/mossman gorge, cello and piano | 9:46 | melodie | catarsi | emotivo, per il rilascio |
| meditative/the hollow of serenity, empowering | 3:29 | melodie | ascesa | |
| meditative/spiritual healing music | 7:12 | ambient | rientro | |
| move/be your word, melodic sport running | 7:12 | danza | attivazione | |
| move/eleven, chillout lounge | 9:55 | danza | attivazione | tempo morbido |
| move/moher, electronic uplifting | 6:29 | danza | ascesa | |
| move/breath of the earth (Welik) | 2:58 | danza | attivazione | serie organica |
| move/drift between fires (Welik) | 4:17 | danza | catarsi | |
| move/morning inside the chest (Welik) | 5:15 | danza | attivazione | |
| move/roots remember (Welik) | 3:57 | danza | arrivo | |
| move/twilight caravan (Welik) | 2:54 | danza | catarsi | |
| move/epic glory (Polytunes) | 4:35 | danza | ascesa | picco |
| move/lassana (Roman Sol) | 3:08 | danza | attivazione | |
| move/vibrazione gola sciamanica | 2:32 | voce | catarsi | canto di gola |
| voice/healing earth, celtic female vocal | 3:25 | voce | ascesa | |
| voice/healing earth, long version | 6:37 | voce | ascesa | stessa di sopra |
| voice/shaman grounding extended | 5:44 | voce | arrivo | sciamanica, radica |

Il momento è una proposta dal nome e dal carattere: confidenza alta per le
tre ambient lunghe e le voci, media per la serie Welik. Il founder corregge
nel CSV prima dell'import, come il 24 agosto.

**Campi nuovi sull'asset** (facoltativi, la libreria di prima resta valida):
`bpm` (misurato dallo script d'import dove c'è un tempo, altrimenti vuoto),
`energia` 1-5 (proposta dal livello e dal timbro, corretta dal founder),
`tags` liberi («tribale», «flauto», «coro»). Servono alle ricette modello
per scegliere i suoni giusti senza sfogliare 200 schede.

---

## 3. I gap per esperienza

**Breathwork.** C'è il pacer sintetico, manca tutto il resto: la voce che
conta, il respiro vero, la struttura a round con le ritenzioni, la musica
col tempo che tiene il ritmo, la campana di svolta. Un layer respiro oggi è
un'onda; una sessione di breathwork è una drammaturgia di 10-20 minuti.

**Danza estatica.** Non esiste la categoria, non esiste il tempo (bpm)
sull'asset, non esiste un modo di far salire e scendere il tempo lungo la
sessione (l'arco della danza: 60 → 130 → 70 bpm), non esiste il passaggio
fra due brani come in una selezione (oggi ogni strato ha il suo attacco e
rilascio, non si «incrociano»). E il tetto di 30 minuti, nato per l'ascolto a
schermo bloccato, è corto per una danza (45-60 minuti tipici): vedi la
decisione 4 in fondo.

**Meditazioni per stile.** La mappa stile → momento funziona: rilassante =
arrivo/rientro (63 suoni, abbondante); energizzante = attivazione/ascesa
(47); catartico = catarsi (**14 suoni**, quasi solo ambient e ritmi: è il
momento più povero, e il più importante della drammaturgia); amorevole = voce
cantata, violoncello, cori (**6 voci** in tutto: il gap più grande insieme al
catartico); rilascio = rientro con droni e respiro lento (ok). Le 23 tracce
nuove coprono in parte proprio catarsi (Welik, cello, gola sciamanica) e
amorevole (voci femminili, celtic): è il motivo per cui l'allocazione
sopra conta.

**Immersione.** Zero spazio nel motore. Il riverbero c'è solo sulla voce.
Tutto suona «al centro, davanti».

**Semplicità.** Crea oggi è già a tre gesti (scegli i suoni, ascolta,
pubblica). Ogni aggiunta deve entrare in un selettore per strato o in una
ricetta modello, mai in una schermata nuova.

---

## 4. Lo spazio: come si fa, dove, cosa ruota

**La tecnica.** In cuffia il «3D» è la spazializzazione HRTF: la Web Audio
API la fa nativa con `PannerNode` (`panningModel: 'HRTF'`), con posizione
x/y/z della sorgente rispetto alla testa. Una sorgente che **orbita** è un
panner la cui posizione è mossa da due oscillatori in quadratura (già scritto
nel Lab, funziona in Chrome, Safari e Firefox, anche in OfflineAudioContext).
Il «9D» del marketing è questo più un riverbero: sorgenti che girano attorno
alla testa dentro una stanza. Non c'è altro dietro.

**Dove va.** Un modulo nuovo `engine/spazio.js`, unica verità usata da tre
consumatori: l'anteprima dal vivo (`synth.js`), il master e l'export
(`render.js`), l'ascolto continuo (`continuo.js`). Dentro: la fabbrica del
panner con i preset, l'orbita (velocità, raggio, quota, verso), il bus
«Stanza» (un ConvolverNode condiviso, impulso sintetico come quello della
voce, quattro taglie). La ricetta cresce di un campo per strato,
`space: {preset, rate, radius}`, `score_version 4`; **assente = fermo**: le
tracce già pubblicate suonano identiche, byte per byte, e una guardia lo
verifica su un render di prova.

**Cosa ruota e cosa no** (la parte che decide la qualità):

- **Tappeti, natura, droni, melodie**: ruotano, lentamente. Per meditare la
  velocità giusta è 0,03-0,08 Hz (un giro ogni 12-30 s); lo 0,2 Hz dei video
  «8D» è un giostra, dopo dieci minuti disturba.
- **Danza**: orbite più rapide (un giro ogni 4-8 s) e sorgenti su lati
  opposti che si incrociano: qui il movimento è parte dell'energia.
- **La voce guida NON ruota** di default. Una voce che gira attorno alla
  testa perde intelligibilità e ancoraggio: in una meditazione guidata la
  voce è il punto fermo, davanti, vicina. Preset facoltativi: «si avvicina»
  (da 2 m a 0,5 m durante l'attacco) e «sussurro a lato» (fissa a 30°, per
  una seconda voce). La rotazione della voce resta possibile, mai
  automatica.
- **Binaurali: MAI nel panner.** Il battimento binaurale vive nella
  differenza fra orecchio destro e sinistro; l'HRTF mescola i canali e lo
  distrugge. Isocroni, rumore, droni e toni invece si possono muovere. Guardia
  di test dedicata.
- **Il respiro del founder e i conteggi**: fermi, davanti, come la voce.
  Al massimo il respiro «si allarga» (raggio che cresce con l'inspirazione):
  è un effetto di ampiezza, non di rotazione.

**I preset per strato** (un selettore accanto a «livello», come il preset
della voce): *fermo* · *respira* (oscilla piano, ±20°) · *orbita lenta* ·
*orbita* · *avvolge* (raggio largo, quota che sale, mandata alla Stanza).
Più un selettore di sessione **Stanza**: *asciutta* · *sala* · *tempio* ·
*cattedrale*. Cinque parole più quattro, niente numeri: chi vuole i numeri
li trova nel Lab (l'Orbita del Lab diventa il banco di prova, con il ponte
«Usa in Crea» già previsto da LB4).

**Cuffie o altoparlanti.** L'HRTF ha senso solo in cuffia; in altoparlante
resta uno stereo largo, non fa danni. L'avviso cuffie già esistente al play
si estende: «questa sessione è spaziale: in cuffia». Nel master pubblicato lo
spazio è cotto dentro (stereo binaurale): funziona in qualunque player.

**Costo.** Un panner HRTF per sorgente pesa sul telefono: dal vivo si tiene
lo spazio su al massimo sei strati contemporanei (oltre, i restanti passano a
`equalpower`, cioè stereo semplice) e la voce spaziale va nel bus dopo la sua
catena. Chi ascolta il pubblicato non paga nulla: è un file.

**Il visual.** La scena di Aurya Mode ha già la camera (`cam_x/y/z`): in un
secondo tempo la rotazione della sorgente principale può guidare la camera,
così occhi e orecchie girano insieme. Fuori da questo ciclo.

---

## 5. Il piano, a fasi rilasciabili

**F0 · Libreria e tassonomia** (1 giornata, subito).
Tre categorie nuove (`danza`, `respiro`, `melodie`) in backend e frontend con
le frasi di orientamento; campi `bpm`, `energia`, `tags` facoltativi;
censimento delle 23 tracce con la tabella sopra come CSV, correzione del
founder, import con momento e licenza Pixabay, tappeti per le tre lunghe;
riassegnazione assistita delle 104 «ambient» (proposte, conferma). Guardie:
parità dei vocabolari, nessun titolo con hertz non verificati.

**F1 · Il respiro registrato** (1 giornata di sviluppo + la sessione di
registrazione del founder).
Specifica di registrazione (sotto), nuovo tipo di strato **«guida del
respiro»**: si sceglie uno schema (4-4, 4-6, 4-7-8, quadrato 4-4-4-4,
coerenza 5-5, IHT 4-4 con ritenzioni) e i round (respirazione N minuti →
ritenzione a vuoto → ritenzione a pieno → recupero), e il motore monta i
clip del founder (conteggi, «trattieni», «rilascia», respiro nasale) sul
tempo scelto, con la campana di svolta e la sintesi `breath` sotto come
tappeto opzionale. La ricetta modello «Breathwork 2 round» riproduce la
struttura del file allegato con la voce di Aurya al posto di quella
originale. Guardie: i conteggi cadono sui battiti, la ritenzione è silenzio
di voce e non di musica, il layer è serializzabile come gli altri.

**F2 · Lo spazio** (2-3 giornate).
`engine/spazio.js`, preset per strato, Stanza, score v4, selettori in Crea,
avviso cuffie esteso, limite dei sei panner dal vivo, guardie (binaurale mai
nel panner; assente = identico; parità vivo/master). Collaudo con le cuffie
sul telefono del founder prima di ogni deploy.

**F3 · Le esperienze modello** (1-2 giornate).
Cinque ricette pronte in Crea, costruite dalla libreria per momento ed
energia, con lo spazio già impostato: *Breathwork 2 round*, *Danza 30*,
*Meditazione catartica*, *Rilascio*, *Amorevole*; le sei di sintesi restano.
Crea resta a tre gesti: scegli l'esperienza → aggiusta durata e voce →
ascolta e pubblica. Chi vuole parte dal modello e cambia un suono alla volta.

**F4 · La danza lunga** (decisione del founder, poi 1 giornata).
Le sessioni oltre 30 minuti sono possibili solo come master (file): il
render offline va fatto a blocchi per non saturare la RAM del telefono
dell'autore, e la modalità «sala» dichiara che non serve lo schermo bloccato.
Arco del tempo (bpm che sale e scende) e incrocio fra brani (crossfade con
allineamento sul battito) sono lo stesso ciclo.

**F5 · Deploy** dopo le registrazioni del founder e i collaudi in cuffia,
con la regola d'invarianza di sempre: il flusso di Valentina e le tracce
pubblicate non cambiano.

---

## 6. Specifica per le registrazioni del founder (F1)

- Stanza silenziosa, microfono a 15-20 cm, WAV 48 kHz mono 24 bit (il
  telefono in modalità «voce» va bene se non applica riduzione rumore
  aggressiva); 3 secondi di silenzio all'inizio di ogni file (serve alla
  sottrazione spettrale già in Crea).
- **Conteggi**, un file per numero e per direzione, tono uniforme, stessa
  distanza: «inspira» · «espira» · «trattieni» · «rilascia» · «uno, due,
  tre, quattro» · «cinque» · «sei» · «sette» · «otto» (ogni parola è un
  clip separato: il motore le monta sul tempo, così valgono per 4-4, 4-6,
  4-7-8 e il quadrato senza registrare ogni schema).
- **Frasi di svolta**: «ultimo respiro, poi espira tutto e trattieni» ·
  «inspira profondo e trattieni» · «rilascia» · «respira normalmente» ·
  «senti il corpo».
- **Il respiro vero**: 2 minuti a 4-4 nasale, 2 minuti a 4-6 (naso dentro,
  bocca fuori), 1 minuto di respiro di recupero; a tempo di metronomo a 60
  bpm in cuffia (non registrato), così ogni ciclo è allineabile.
- Nomi file: `respiro_conteggio_1.wav`, `respiro_parola_trattieni.wav`,
  `respiro_loop_4-4_nasale.wav`. Vanno nella categoria `respiro` con il
  campo `pattern` e il campo `parola`.

---

## 7. Decisioni per il founder

1. **Le tre categorie nuove** e la riassegnazione assistita delle 104
   «ambient»: sì, e con questi nomi?
2. **La tabella delle 23 tracce**: confermi o correggi categoria e momento
   all'ascolto (la Welik in particolare).
3. **Licenza**: le tracce vengono da Pixabay? Si scrive «Pixabay Content
   License» in blocco.
4. **La voce non ruota di default**: confermi. (È la scelta che tiene
   l'esperienza «profonda» invece che «da video»).
5. **La danza oltre i 30 minuti**: la vuoi ora (F4, con la modalità sala) o
   restiamo a 30 per questo giro?
6. **Ordine**: F0 → F1 → F2 → F3, con deploy unico dopo le tue
   registrazioni; oppure F0 + F2 subito (lo spazio non aspetta le
   registrazioni) e F1 + F3 quando i file ci sono.

---

## Stato (22 settembre, sera)

- **F0 FATTA** (commit 88c951b9): categorie `melodie`, `danza`, `respiro`; campi `bpm`/`energia`/`tags`; 23 tracce importate in locale con momento e licenza Pixabay, 16 tappeti collegati (`scripts/collega_tappeti.py`); proposta di riassegnazione delle 104 ambient in `docs/sound/riassegnazione_ambient_2026-09.csv`.
- **F2 FATTA** (952a0d76): `engine/spazio.js`, preset per strato e Stanza, score v4, selettori in Crea, master a blocchi con riporto della coda; provato nel browser (ascolto con orbita, export con tempio e un binaurale, bozza v4 salvata e ricaricata).
- **F4 FATTA** (commit successivo): tetto a 90 minuti, export e master lunghi a blocchi, 30 minuti solo per l'ascolto a schermo bloccato prima della pubblicazione.
- **F2b — il «non sento niente» (22/9 sera, founder)**. Tre cause, tre rimedi, tutti misurati nel browser (banco `window.__auryaSpazio.misura`, solo in sviluppo):
  1. **Bug**: `resolveAudioLayers`/`resolveVoiceLayers` (engine/assets.js) ricostruivano lo strato campo per campo e perdevano `space`; il motore legge `l.space` dallo strato risolto → nessun panner è mai nato, la Stanza non riceveva niente. Ora `space: l.space` in entrambi, con guardia.
  2. **Effetto tenue sui tappeti gravi e larghi**: l'HRTF da solo sposta un tono a 660 Hz di ~6 dB fra i due orecchi, ma a 110 Hz di ~2,5 dB, e un file stereo entra nel panner già spalmato su entrambi i lati. Rimedio in `creaSpazio()` (unica porta per vivo, master e continuo): downmix mono dello strato che si muove + StereoPanner «rinforzo» che segue lo stesso angolo (0,5-0,7). Sulla base reale «Be Your Word»: orbita lenta da +9 a −9 dB ogni 24 s, orbita ±9 dB ogni 8 s, respira ±5 dB. La voce «vicina» non ha rinforzo (si avvicina, non gira).
  3. **Cambio a sessione in corso**: spazio e Stanza ora fanno ripartire l'ascolto dal punto in cui era (il grafo si costruisce alla partenza).
- **F4b — «una melodia di 50 minuti non posso ascoltarla intera?»**: in Crea l'ascolto dal vivo è sempre intero. L'ascolto a schermo bloccato prima del master passava da un WAV in memoria (tetto 30 min): oltre i 30 ora si renderizza e comprime a blocchi in MP3 a 22050 Hz / 96 kbps (31,7 min → 21,7 MB in 46 s su desktop, decodifica intera verificata). `CONTINUO_MAX_SEC` = 5400 come il modello. Pubblicata, la traccia è il master in streaming, senza limiti.
- **F1 FATTA (22/9 sera, con le registrazioni del founder in ~/Desktop/memo)**. Dieci memo (AAC stereo, parole a −15/−22 dBFS, soffi a −35) → `scripts/prepara_respiro.py` (mono, picco a −3/−6 dBFS, AAC 96k) → `scripts/importa_respiro.py` (libreria, categoria `respiro`, campi `guida` e `ciclo_sec`). I cicli misurati sulla forma d'onda: «inspira 1 2 3 4 / espira 1 2 3 4» 8,4 s; «dentro/fuori» 7,8 s; conteggio nudo 6,8 s; respiro vero bocca 7,0 s; 3-3 6,8 s. Il tempo è quello della registrazione: il clip si ripete ogni `ciclo_sec`, non si stira la voce. CSV di verità: `docs/sound/respiro_founder_2026-09-22.csv`.
  Strato `kind:'guida'` (score v5): `respiri`, `round`, `vuoto_sec`, `pieno_sec`, `recupero_sec`, `campana`, `parole {inspira, espira}` (id dei clip). Partitura unica in `engine/guida.js` (`partituraGuida` → eventi; `montaGuida` li appoggia nella finestra: vivo, master a blocchi, continuo). Campana sintetica a 528 Hz, deterministica. In Crea: sui cicli il pulsante «+ guida», le parole non si aggiungono come basi; la riga ha schema (continuo / 2 round con ritenzioni), respiri, round, vuoto, pieno, recupero, campana, e ricalcola la fine. Provato: 20 respiri × 2 round = 40 clip, 2 «inspira», 2 «espira», 6 campane, bozza v5 salvata e riletta.
  **Manca ancora** (registrazioni del founder): «trattieni», «rilascia», «respira normalmente»; i numeri 5, 6, 7, 8 per 4-6 e 4-7-8 (oggi solo 4-4 e 3-3); un respiro nasale 4-6 di 2 minuti a metronomo.
- **F3** (esperienze modello) resta da fare. **Deploy** dopo: niente di tutto questo è in produzione.
