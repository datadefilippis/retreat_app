# Aurya Sound Lab: consolidamento e multipiattaforma (analisi, 5/9/2026)

Referto del founder (4/9, dal telefono, stanza Ritratto):

1. campana tibetana suonata **forte**: niente ritratto, il Lab dice che
   «ha sentito frequenze ma sembrava una voce»; solo suonata **piano**
   esce la tabella;
2. riascoltando il ritratto dal telefono «scattava e tremava tutto»;
3. design non ottimizzato mobile, pulsanti fuori schermo.

Richiesta: analisi profonda, Lab consistente e «super ottimizzato
multipiattaforma», non solo il Ritratto. Questo documento è l'analisi;
niente è stato implementato.

## Cosa è stato verificato (con misure, non a occhio)

### 1. La campana forte diventa «voce»: riprodotto al banco sintetico

Il verdetto che il founder ha letto è quello di `natura: 'melodia'`
(«La nota si muove... è una melodia, o un parlato»), oppure quello di
`intonato` («la firma di una voce o di una corda»). Nasce nella
**via armonica** di `lab/ritrattista.js` (`_viaArmonica`), che si tenta
sempre e decide con tre cancelli: 60% dei fotogrammi con una
fondamentale, picchi sulla serie armonica, almeno due armoniche. Il
cancello «mutevole» (spread della fondamentale > 12%) parla PRIMA degli
altri due e produce il verdetto melodia.

Banco di prova in node con il codice vero (`ritrattista.js` +
`accordatore.js`, copiati nello scratchpad) e campane sintetiche con
modi inarmonici 1 : 2,71 : 5,15 : 8,3 e doppietti che battono (2-6 Hz,
lo «shimmer» di ogni campana tibetana vera):

| segnale | verdetto oggi |
|---|---|
| campana delicata (acuti deboli) + doppietti | modi (giusto) |
| campana FORTE + doppietti | **melodia 72→578 Hz** |
| campana forte + limiter del mic | **melodia** |
| campana fortissima con clipping | **melodia** |
| campana con acuti dominanti | **melodia** |
| campana grave 110 Hz forte | **melodia 98→298** |
| voce tenuta con vibrato | intonato (giusto) |
| voce glissando, parlato | melodia (giusto) |
| bicchiere, corda pizzicata | modi / intonato (giusto) |

Il meccanismo, letto sulla traccia dell'accordatore fotogramma per
fotogramma: su una campana forte l'autocorrelazione **salta fra i
modi e i loro sottoperiodi** (73, 214, 575 Hz: `221 73 221 73 572 217
205 72 218...`), perché con un colpo forte gli acuti sono tanto forti
quanto il fondamentale e i doppietti li fanno pulsare. Il tracker trova
«una fondamentale» in oltre il 60% dei fotogrammi (primo cancello
passato), lo spread supera il 12% (secondo cancello) e il Lab conclude
«la nota si muove». Con un colpo delicato gli acuti sono deboli, il
tracker resta fermo sul fondamentale e si passa dalla via dei modi.
Esattamente il sintomo del founder: forte = voce, piano = ritratto.

Bug secondario scoperto: quando il microfono del telefono **satura**
(limiter o clipping, normale con una campana a 20 cm), l'analisi non
lo dice e scrive una tabella sbagliata (fondamentale a 120/152 Hz da
prodotti di intermodulazione invece di 214). Oggi nessun avviso.

Prototipi di cura provati al banco (nello scratchpad, non nel repo):
- cancello «percussivo» (energia che cade > 12 dB nella coda) + test
  di continuità del tracker: campane 5/6 giuste, ma la voce con
  vibrato scivola a «modi» (gli errori d'ottava del tracker contano
  come salti) → non basta così;
- conteggio dei grappoli di altezza ripiegati nell'ottava: non
  separa, perché il battimento dei doppietti sparge le letture del
  fondamentale (193-221 Hz) in più grappoli.

Lezione: il segnale sintetico è utile per riprodurre il bug, non per
tarare la cura. Il banco è anche **non deterministico** (rumore da
`Math.random`): un caso cambiava verdetto fra due esecuzioni.

### 2. «Scattava e tremava» in riascolto: tre cause nel codice

a) **Il microfono resta aperto durante l'A/B.** `Ritratto.registra()`
apre l'orecchio da solo (caso del founder del 28/8) e non lo chiude
mai. Aprire il mic fa `analisi.sorgente(mic)`: da quel momento
l'analyser del banco guarda **il microfono**, non il master. Quando
poi si preme Originale/Colpo/Tenuto, `RitrattoVisual` (la sagoma dello
spettro vivo) e `OndaViva` (la forma d'onda con trigger) leggono ciò
che il microfono del telefono sente dall'altoparlante: rumore di
stanza, ripresa dell'altoparlante, il trigger non aggancia mai
(«in corsa» / «agganciata» che lampeggia), la sagoma balla. Su desktop
con le cuffie non si nota. In più `OndaViva` chiama `setAggancio` a
ogni fotogramma: se l'aggancio cambia ogni frame, React ridisegna il
pannello 60 volte al secondo. Questo è il «tremava».

b) **Costo del disegno per fotogramma.** Misurato nel browser di
sviluppo con l'esito sintetico e il Tenuto in ascolto (dpr 2, tele da
918 px): 1,23 ms/frame con l'Onda viva accesa contro 0,07 ms/frame con
le sole corde. L'Onda viva è il 95% del costo: tre tracciati da 2048
punti, un livello fuori schermo a piena risoluzione, `shadowBlur` a
8·dpr. Su un telefono (dpr 3, GPU più lenta, blur software in WebKit)
l'ordine di grandezza atteso è 10-40 ms/frame, cioè fotogrammi persi.
Il ponte audio è un `<audio>` alimentato da un MediaStream: su iOS un
thread principale saturo fa **scattare** proprio quel canale. Con il
mic aperto gira anche l'accordatore dell'Orecchio (autocorrelazione su
4096 campioni ogni 90 ms, O(N·lag) in JS puro) e ridisegna il numero.

c) **La sessione iOS in play-and-record.** Con il mic aperto il motore
dichiara `navigator.audioSession.type = 'play-and-record'`: su iPhone
la riproduzione passa in regime di cattura (elaborazione «da
chiamata», volume e via d'uscita diversi). Ipotesi da verificare sul
telefono del founder, non misurata qui.

### 3. Layout mobile: riprodotto, ed è solo il Ritratto

Sonda sui sei percorsi del Lab a 375 px (viewport iPhone):

| stanza | larghezza scroll | elementi fuori schermo |
|---|---|---|
| /sound/lab (Sala) | 375 | nessuno |
| /banco | 375 | nessuno |
| /orecchio | 375 | nessuno |
| /meraviglie | 375 | nessuno |
| /risonanze | 375 | nessuno |
| **/ritratto con esito** | **499** | tela, tabella, gesti della fonderia, «⤓ WAV» (bordo destro a 498 px) |

Causa: `.lab-ritratto-griglia` sotto i 1080 px diventa una colonna
`1fr`, che per la specifica delle griglie vale `minmax(auto, 1fr)`: la
colonna non scende sotto il **min-content** del contenuto, e la
tabella dei parziali è `white-space:nowrap` (461 px). Il contenitore
`overflow-x:auto` non serve a nulla perché è l'item di griglia a non
restringersi. La tela, i gesti e il pulsante WAV seguono la colonna a
461 px. Cura da una riga: `min-width:0` sulle due colonne (o
`minmax(0,1fr)` nel breakpoint), mantenendo la stringa desktop che la
guardia `test_sound_lab.py` pretende.

Nota: il banner cookie a 375 px sta dentro (351 px). Appare in inglese
perché segue la lingua del browser, non è un difetto del Lab.

## Piano proposto (ciclo «LM», Lab Mobile)

Ordine per rischio decrescente e per valore per chi usa il telefono.

**LM0. Il referto dal telefono vero (prima di tarare).** Aggiungere al
Ritratto «⤓ Scarica la registrazione» (i campioni crudi in WAV: la
funzione `renderizzaWav` c'è già) e nel messaggio d'esito il picco in
dBFS con l'avviso di saturazione. Il founder registra la sua campana
forte e piano e mi manda i due WAV: la cura si tara su quelli. Un
suono sintetico riproduce il bug ma non sostituisce lo strumento vero.

**LM1. Il verdetto «voce» sulla campana.** In `ritrattista.js`, prima
di dichiarare «melodia»: un oggetto colpito ha attacco e decadimento,
una voce no; i suoi modi forti stanno a rapporti non interi fra loro;
il suo tracker salta fra pochi valori fissi. La regola definitiva si
sceglie sui WAV di LM0, con un banco **deterministico** (rumore
seedato) in `frontend` eseguito da una guardia pytest: campane forte e
piano (vere), voce tenuta, glissando, parlato, bicchiere, corda. In
più: il clipping si misura e si dice («troppo vicino al microfono,
tabella indicativa»), e il verdetto melodia non nomina più «voce» se
il suono decade.

**LM2. Il microfono si chiude quando l'A/B suona.** Il Ritratto che ha
aperto l'orecchio da solo lo chiude prima di Originale/Colpo/Tenuto
(o, meglio, `analisi.sorgente(master)` per la durata dell'ascolto e
mic ripristinato dopo), così la sagoma e l'onda viva leggono il
master come promesso nel loro contratto. `OndaViva` aggiorna
`aggancio` solo quando cambia davvero (ref + confronto), non a ogni
fotogramma. Su iOS la sessione torna `playback` durante l'ascolto.

**LM3. Disegno a budget sul telefono.** Un solo criterio nel quadro:
se `devicePixelRatio > 1.5` o il frame precedente ha superato 12 ms,
si disegna a dpr 1,5 massimo, `shadowBlur` sostituito da un secondo
tratto semitrasparente (la guardia LB7 chiede la parola `shadowBlur`
nel sorgente dell'Oscilloscopio: resta, dietro il criterio), scia
ridotta a metà risoluzione, tracciati a passo 2 px. Obiettivo: sotto i
4 ms/frame su un iPhone di fascia media. Misura con lo stesso
`__fqzQuadro.unGiro()` usato oggi, prima e dopo.

**LM4. Il Ritratto entra nello schermo.** `min-width:0` sulle colonne
della griglia; tabella dei parziali con colonne ridotte sotto i 640 px
(Hz, forza, vita; rapporto e doppietto come riga secondaria), gesti
della fonderia a larghezza piena e tap-target da 44 px, pulsante WAV
con etichetta corta. Verifica automatica: sonda di overflow a 375 px su
tutte e sei le stanze come guardia (oggi solo il Ritratto sbaglia, la
guardia impedisce che le altre lo seguano).

**LM5. Coerenza multipiattaforma delle sei stanze.** Stesso giro di
sonda su 320/375/414/768 px, con esito del Ritratto e quaderni pieni;
sticky (pill «Sala del Lab» e barra del tono delle Risonanze) che non
coprono i comandi; slider e checkbox della tabella con area tattile
adeguata; testi mono che non spingono la larghezza.

**LM6. Verifica sul telefono del founder.** Con LM0 in prod il founder
ripete i tre gesti (campana forte, riascolto, scroll) e mi manda WAV e
screenshot: chiusura del ciclo sui dati veri.

## Stato (5/9/2026, sera)

- **LM0 RIVISTO dal founder**: «siamo live, l'utente non scarica
  file». Il pulsante di download è uscito; resta l'avviso di
  saturazione con picco in dBFS e la cura.
- **LM1 FATTO senza WAV veri**: tre regole fisiche nella via armonica
  prima del verdetto «melodia»: continuità del tracker (salti fra i
  modi, ripiegati nell'ottava), simultaneità dei gradini (Goertzel:
  in una campana i due modi suonano insieme, in una melodia le note
  vengono una dopo l'altra), bande laterali del vibrato raggruppate
  con tolleranza che cresce con k. Banco deterministico `lab/banco`:
  12/12 (sei campane forti → modi, voce con vibrato → intonato,
  glissando e parlato → melodia); sweep su 6 semi 71/72, e l'unico
  scarto è un glissando letto «intonato», mai una campana letta
  «voce». `clipping`, `piccoDb`, `percussivo` nel ritratto; la melodia
  di un suono che decade non nomina la voce.
- **LM2 FATTO**: analyser sul master durante l'A/B e mic ripristinato a
  suono finito (naturale o fermato); `setAggancio` solo al cambio.
- **LM3 FATTO**: `economia()` / `dprTela()` / `forzaEconomia()` nel
  quadro; le sei tele prendono il dpr dal quadro e il bagliore solo
  fuori economia. Misura: 1,23 → 0,54 ms/frame (dpr 2, economia).
- **LM4 FATTO**: sonda a 375 px = 375 (era 499); tabella nel suo
  scorrimento, gesti a griglia, chip a capo.
- **LM5 FATTO**: sonda a 320/375/414/768 sulle sei stanze (nessun
  elemento fuori schermo) e tap da pollice sui dispositivi a tocco
  (`pointer: coarse`: bersagli 40 px, pomelli 22, caselle 20; col
  mouse nulla cambia). Verifica in emulazione touch: zero bersagli
  sotto i 36 px.
- **LM6 DA FARE**: verifica sul telefono del founder (a voce, senza
  file: campana forte e piano, riascolto, scroll).

## Cosa NON cambia
- Il contratto dei pannelli (un solo rAF nel quadro, niente nodi
  audio nei visual, il mic mai verso l'uscita).
- Le quattro nature del ritratto e la via armonica: si affinano i
  cancelli, non si rifà l'analisi.
- Nessuna regressione su desktop: le guardie esistenti del Lab (173
  test in `test_sound_lab.py`) restano e si evolvono con docstring.

## Materiale di lavoro
- Banco sintetico e prototipi: scratchpad della sessione (`rit/`:
  `segnali.mjs`, `banco.mjs`, `ritrattista_cura*.mjs`). Da rifare
  deterministico in LM1 dentro il repo.
- Misure browser: costo per fotogramma 1,23 vs 0,07 ms (dpr 2);
  overflow 499/375 px nel Ritratto con esito.
