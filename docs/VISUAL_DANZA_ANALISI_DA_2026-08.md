# Il ballerino — analisi della correlazione suono→visual (ciclo DA)

**Data**: 22 agosto 2026 · **Stato**: analisi, in attesa del «procedi»
**Richiesta founder**: «le forme si muovono anche senza suono, stessa
modalità […] voglio che la connessione visual+suono sia REALE: ogni nota,
ogni frequenza, ogni ritmo deve produrre un effetto vero di movimento. Non
un unico movimento standard: un oggetto che si muove come un ballerino e si
adatta alla musica.»

---

## 1. Il verdetto, coi numeri del codice

Il founder ha ragione, e non è un'impressione: è aritmetica. Il moto della
scena oggi è dominato da **tre metronomi interni** che girano anche nel
silenzio assoluto:

| Sorgente di moto | Formula (nel codice) | Dipende dall'audio? |
|---|---|---|
| Il tempo della scena | `tAcc += dt·speed·(0.5 + energia·1.1)` | poco: **a silenzio scorre al 65-70%** della velocità di quando suona |
| Il respiro (la «spina dorsale del moto», parola del prototipo) | `breathPhase += dt/S.breath` | **MAI**: è un metronomo puro |
| I gesti dei petali (reach/fat/curl/dome) | seni autonomi su `t` con ampiezze 0.16-0.22 + audio con ampiezze 0.10-0.34 | l'audio pesa **~15-20% del gesto** |

E il rilevatore di «colpo» — l'unico evento ritmico — scatta solo su un
salto dei **bassi** (`kick > .035`): pensato per percussioni. Ma le
meditazioni Aurya **non hanno percussioni**: sono droni, battiti binaurali
e isochronic (0.05–60 Hz, da contratto dello score), maree lente, respiri
guidati. Il loro ritmo vive nella **modulazione d'ampiezza**, non nei
transienti. Risultato: su una meditazione tipica il colpo non scatta mai,
le bande sono quasi costanti, e ciò che si vede è al 100% il balletto dei
metronomi interni — identico a sessione ferma.

Tre difetti collaterali scoperti nell'analisi:

1. **Stop ≠ quiete**: in Crea, dopo lo stop la scena resta montata
   (`elapsed > 0`) con l'analizzatore che legge silenzio → il 65-70% del
   moto continua, uguale a prima. È esattamente ciò che il founder ha
   visto.
2. **Due orecchie diverse**: lo strumento usa il suo analyser con
   lisciatura 0.88; studio e meditazione usano l'analizzatore prestato di
   analisi.js a 0.5. Stessa scena, nervosismo diverso a seconda della
   porta da cui entri.
3. **Reactivity conta poco**: il selettore Calm/Soft/Deep/Full moltiplica
   pesi già piccoli — cambia poco perché modula il 20% del moto, non
   l'80%.

## 2. Il principio del consolidamento: l'energia è il carburante

Oggi l'audio è un **condimento** su un moto autonomo. Va rovesciato:

> **Nessun suono → quasi ferma. Suono → tutto il moto viene da lì.**

- Il tempo della scena scorre in funzione dell'energia, con un pavimento
  di *veglia* molto basso (~0.1: viva, ma visibilmente in attesa).
- Il respiro non è più un metronomo: la sua **ampiezza** è modulata
  dall'energia, e quando nella sessione c'è un ritmo lento vero (marea,
  respiro guidato), la sua **fase si aggancia a quello** (§3).
- I seni autonomi dei petali scendono di ampiezza; le componenti audio
  salgono. Rapporto obiettivo: **audio ≥ 70% del gesto** a suono attivo.
- Allo stop, la scena scivola in veglia in un paio di secondi — si VEDE
  che il suono se n'è andato. (Niente congelamento secco: brand.)

## 3. L'orecchio nuovo: sentire il ritmo che c'è davvero

Un solo estrattore (il «polso»), condiviso da strumento, studio e
meditazione — stessa lisciatura, stessa verità:

```
polso = {
  energia,          // inviluppo complessivo, liscio
  colpo,            // transiente su TUTTO lo spettro (flusso spettrale),
                    // non solo bassi: becca anche un cambio di nota
  battitoHz,        // il battito di MODULAZIONE (0.3–14 Hz): stimato
                    // dall'inviluppo dei bassi/medi — è l'entrainment
  faseBattito,      // 0..1 dentro il ciclo del battito
  ondaLenta,        // inviluppo lentissimo (maree, crescendo, respiri)
  brillantezza,     // centroide spettrale → scintillio/colore
}
```

Il pezzo di valore è `battitoHz`: le nostre meditazioni HANNO un ritmo
preciso — il battito isochronic/binaurale scelto dall'operatore — ed è
esattamente ciò che oggi la scena ignora. Agganciare i petali alla **fase
del battito di entrainment** significa che una sessione a 8 Hz pulsa
diversamente da una a 2 Hz: ogni ricetta balla la SUA musica.

**Vincolo di sicurezza non negoziabile**: il battito guida MOVIMENTO e
fase spaziale (aprirsi, propagarsi, torcersi) — **mai lampeggi di
luminanza globale sopra ~3 Hz** (fotosensibilità; il sipario avvisa già,
ma la miglior difesa è non costruire uno strobo). Sopra i ~3 Hz la
pulsazione si traduce in onde che viaggiano nello spazio, non in luce che
sbatte.

## 4. Le coreografie: sette forme, sette balli

«Non deve essere un unico movimento standard.» Oggi i 7 modi condividono
gli stessi uniform globali. Il consolidamento dà a ogni forma la sua
mappa:

| Forma | Il suo ballo |
|---|---|
| Breath | segue `ondaLenta` (se la sessione ha un respiro guidato, respira CON lui) |
| Nebula | densità e turbolenza ∝ energia; il colpo la squarcia |
| Spiral | velocità di avvolgimento ∝ bassi; i bracci si stringono sul colpo |
| Flow | il campo scorre a velocità ∝ energia, la direzione vira con la brillantezza |
| Mandala | i petali si aprono in fase col `battitoHz`; il colpo lancia un'ONDA radiale che attraversa le corone |
| Helix | torsione ∝ medi, passo ∝ bassi, scintillio ∝ alti |
| Ripple | **event-driven**: ogni colpo EMETTE un anello vero che viaggia |

La novità strutturale: **eventi propagativi**. Oggi il colpo è un uniform
che decade (tutta la scena sobbalza insieme). Un ballerino non sobbalza:
il gesto *attraversa* il corpo. Tecnica: il colpo scrive un timestamp
(`uHitT`), il vertex shader calcola l'onda in funzione della distanza dal
centro — il movimento si propaga, a costo zero di CPU.

## 5. La prova, non a occhio

- **Tracce-sonda** (solo dev): un isochronic puro a 2 Hz → si deve VEDERE
  pulsare a 2 Hz; un drone piatto → scena in veglia lenta; un colpo secco
  → un'onda sola che attraversa. Verifica col registratore di frame
  (varianza degli uniform), non a sensazione.
- **Guardie statiche**: pavimento del tempo ≤ 0.15; ampiezza dei seni
  autonomi ≤ metà della componente audio corrispondente; una sola
  lisciatura dichiarata; niente `Math.random` nel loop del polso; il
  vincolo anti-strobo (nessun mapping battito→brightness).
- **Una sola orecchia**: la lisciatura dell'analyser diventa un numero
  condiviso (tabelle/standard), identico per strumento, studio e
  meditazione.

## 6. Le onde del ciclo DA

- **DA1 — Il silenzio si sente**: energia come carburante (pavimenti giù,
  respiro/drift/tempo scalati), scivolata in veglia allo stop. È il fix
  del difetto segnalato, consegnabile da solo.
- **DA2 — L'orecchio (il polso)**: estrattore unico con flusso spettrale,
  battito di modulazione 0.3–14 Hz, onda lenta, brillantezza; lisciatura
  unificata.
- **DA3 — Le coreografie**: mappe per-forma + eventi propagativi;
  Reactivity che governa davvero (a Full l'audio È il moto).
- **DA4 — La prova del ballerino**: tracce-sonda, verifica strumentale,
  taratura finale con il founder davanti a 3-4 ricette vere.

Ordine pensato per il valore: DA1 ripara la fiducia («se fermo il suono,
la scena lo sa»), DA2-DA3 costruiscono la danza, DA4 la dimostra.

## 7. Cosa NON cambia

- La scena salvata nella ricetta (forme, colori, cursori, inquadratura) e
  tutto il ciclo VC: il ballo è COME si muove, non COSA si è scelto.
- Il costo server: zero — tutto accade sul dispositivo, come ora.
- Il vincolo brand (palette dell'autore, niente arcobaleno d'ufficio) e
  il sipario sicurezza.
- `/sound/visual` con mic/traccia: il polso vale anche lì (un DJ set nel
  microfono ballerà per davvero — è il caso facile; il difficile e più
  prezioso sono le nostre meditazioni, ed è per quello che c'è DA2).

---

# DA5 — Taratura v2: «scattoso, più stress che relax» (22 ago, sera)

**Feedback founder dopo il primo ascolto**: la pausa non ferma la scena;
il movimento è scattoso, «troppo su e giù rispetto alle note».

## La diagnosi (tutte cause verificate nel codice)

**Pausa che non ferma** — tre cause che si sommano:
1. la vita scende con tau ~2,5 s: servono 5-8 s prima che la quiete si
   percepisca;
2. la «veglia» è alta: tempo al 12%, respiro al 15%, deriva al 20%,
   orbita accesa — sommati, si legge «continua a muoversi»;
3. nessuna distinzione tra «suono debole» e «silenzio vero»: la pausa è
   silenzio VERO e merita una discesa rapida.

**Scattosità** — cinque cause che si sommano:
1. l'inseguitore delle bande sale in 0,25 s (k=4.2) e alimenta TUTTI i
   canali geometrici: ogni fluttuazione di nota entra nei muscoli;
2. **la camera** «Breathe» zooma con i bassi a 0,25 s: il su-e-giù che lo
   stomaco sente è soprattutto suo — il movimento di camera è il più
   stressante di tutti;
3. il colpo scatta troppo spesso (soglia 2.4×media): su musica con note
   ogni cambio lancia un'onda con ampiezze forti (reach +45%, luce +90%);
4. la fase del battito SALTA quando la fiducia oscilla intorno alla
   soglia (`fiducia > 0.2 ? fase : 0.25`): strappi periodici;
5. pesi DA3 tarati troppo alti per il contesto meditativo, e la taglia
   delle particelle pompa coi bassi.

## Il principio della cura: due velocità per due mestieri

L'ORECCHIO resta veloce (il colpo e il battito vanno sentiti al volo);
i MUSCOLI diventano lenti — gesti tai-chi: salita ~0,7 s, discesa ~1,8 s.
La camera lentissima (tau 2 s: accompagna, non insegue). Il colpo diventa
raro e prezioso: soglia più alta, periodo refrattario 1,6 s, ampiezze
dimezzate — un'onda ogni frase musicale, non una per nota. La fase del
battito non salta mai: continua a integrare, è l'AMPIEZZA che sfuma con
la fiducia (rampa, non soglia). La pausa diventa quiete vera: su silenzio
totale la vita scende in <1 s, e la veglia è un quadro che respira appena
(tempo 3,5%, deriva 6%, orbita spenta).

La Reactivity resta la manopola per chi vuole più nervo: Full moltiplica,
ma la base è calma — siamo una piattaforma di meditazione, non un club.

---

# DA6 — L'anima tonale: la melodia deve avere una forma (22 ago, notte)

**Richiesta founder**: «se una musica da bassa diventa sempre più alta mi
aspetto la stessa elevazione nel visual […] le forme devono rappresentare
una melodia, non muoversi randomicamente. Serve la stessa anima.»

## 1. La diagnosi: manca il terzo asse

La musica vive su tre assi, e il ballerino finora ne sente due:

| Asse | Domanda | Stato |
|---|---|---|
| **Dinamica** (energia) | *quanto* suono c'è | ✓ DA1 — la vita |
| **Ritmo** (tempo) | *quando* succede | ✓ DA2/DA3 — battito, colpo, onde |
| **Altezza** (registro, melodia) | *cosa* sta suonando | ✗ **quasi assente** |

Oggi bass/mid/high entrano come tre energie scalari — muovono *quanto*,
mai *dove*. Una melodia che sale di un'ottava cambia appena i pesi: la
scena non «sale» con lei. È esattamente ciò che il founder percepisce:
si muove, ma senza la logica della musica.

## 2. I principi (percezione cross-modale, non gusto)

La mappatura suono→spazio non è arbitraria: esistono associazioni
universali, misurate, le stesse che rendono leggibile qualsiasi
visualizzazione musicale:

1. **Altezza → elevazione**: note acute = alto, leggero; gravi = basso,
   massiccio. È l'associazione cross-modale più forte che si conosca
   (perfino i neonati la mostrano). → *la scena deve salire quando la
   musica sale*.
2. **Altezza → luce e finezza**: acuto = chiaro, minuto; grave = scuro,
   grande. → registro sulla banda colore (dentro la triade dell'autore)
   e sulla taglia delle particelle.
3. **Melodia → slancio**: non basta la posizione, serve la DERIVATA —
   una scala che sale è un gesto ascensionale, un glissando che scende è
   una ricaduta. → `slancio = d(registro)/dt`, lisciato.
4. **Spettro → topologia**: il principio da ingegnere del suono. Ogni
   forma ha una geometria naturale su cui STENDERE lo spettro — bassi al
   centro, acuti in periferia (mandala, spirale); bassi in basso, acuti
   in alto (elica). Così **ogni banda muove la SUA zona**: un basso che
   pulsa gonfia il cuore, un arpeggio acuto fa scintillare i bordi — in
   tempo reale, nota per nota, SENZA scuotere tutta la scena (che è ciò
   che in DA5 abbiamo reso calmo). Località = correlazione visibile
   senza nervosismo.

## 3. Cosa si aggiunge (DA6)

**All'orecchio (il polso)**:
- `spettro8`: 8 bande logaritmiche 60 Hz–8 kHz, lisciate con tempi medi
  (più vive dei muscoli globali, perché locali);
- `registro`: la bilancia grave↔acuto (centroide in ottave, già DA2, ora
  mappato davvero);
- `slancio`: la derivata del registro, lisciata e limitata — il gesto
  melodico.

**Agli shader** (uniform: `uSpettro[8]`, `uRegistro`, `uSlancio`):
- **elevazione globale**: il baricentro sale/scende col registro; lo
  slancio dà il moto ascensionale quando la melodia sale;
- **luce**: il registro sposta la banda colore verso la punta chiara
  della triade dell'autore (mai fuori palette);
- **taglia**: acuto = polvere fine, grave = globi morbidi;
- **zone spettrali per forma** (la topologia): mandala = corone
  (centro→bassi, bordo→acuti); spirale/ripple = raggio; elica = altezza;
  breath = guscio; nebula = quota. Ogni banda anima la sua zona.

**«Serve più 3D?»** — Risposta onesta: no, serve più *semantica* nello
spazio 3D che già c'è. L'elevazione, lo slancio e le zone spettrali
danno profondità percepita più di qualsiasi geometria nuova, perché il
movimento acquista significato. Se dopo questo il 3D sembrerà ancora
poco, il passo successivo è la parallasse (camera che respira sul
registro), non nuovi poligoni.

## 4. La prova (sonde tonali)

- tono puro a 100 Hz vs 1200 Hz → `registro` basso vs alto, scena bassa
  e scura vs alta e chiara;
- «discesa infinita» (shepard, già in libreria metodi) → `slancio`
  stabilmente negativo: la scena deve RICADERE con lei, per tutta la
  durata — il test perfetto perché il gesto non finisce mai;
- glissando (marea del battito) → l'onda viaggia attraverso le zone.

---

# CONSOLIDAMENTO FINALE (22 ago, sera) — lo stato dell'area visual

Rianalisi completa richiesta dal founder: tutte le superfici, tutte le
forme, l'anima sonora. Stato: SOLIDO, con il perimetro che segue.

## Le quattro superfici, una catena sola

| Superficie | Cosa monta | Verificato |
|---|---|---|
| `/sound/visual` (strumento) | prototipo integrale, mic/file, localStorage | ✓ pannelli, 12 forme, marchio |
| Studio (da Crea) | prototipo + pannelli, audio della sessione, «Fatto»→ricetta | ✓ giro completo con salvataggio |
| Preview in Crea | prototipo incorporato, scena della bozza, applica() al volo | ✓ cambia all'uscita dallo studio |
| Meditazione pubblica | prototipo incorporato, scena dell'AUTORE dalla ricetta | ✓ end-to-end (Torus via score) |

UN solo motore (prototipo.js), UN solo orecchio (polso, lisciatura nello
standard), UNA sola verità sui dati (score.visual, valori risolti,
inquadratura compresa, pose di casa per chi non la salva).

## L'anima sonora, forma per forma (stato da sound engineer)

Tutte le 12 forme bevono dal polso: vita (carburante), battito (fase
spaziale, con porta di profondità), colpo (flusso spettrale, onde
propagative con la forza del colpo), registro/slancio (elevazione),
zone spettrali (topologia per forma):

Breath=guscio (slow+battito) · Nebula=quota · Spiral=raggio+onda di
densità sul battito · Flow=raggio+brillantezza · Mandala=corone (cuore
bassi, bordo acuti) + armilla per banda · Helix=altezza + risalita con
la vita · Ripple=anelli emessi dal colpo · Flower=raggio + emersione
con l'onda lenta · Merkaba=radiale (cuore→punte) + controtempo
battito/onda · Torus=sezione + fiume con la vita · Ocean=lunghezza
d'onda + marea + spuma acuti · Portal=profondità + scorrimento con la
vita.

## Ciò che resta aperto (dichiarato, non urgente)

- Taratura estetica fine col founder su musica ricca (pesi per forma);
- AV3: export video MP4 (9:16/16:9) e «suono del PC» come sorgente;
- VC6d: play/pausa della sessione DENTRO lo studio;
- la X mobile va vista su un telefono vero (verifica strutturale ok);
- preset che adottino le forme nuove: scelta di firma del founder.

---

# IL CANALE DEL SUONO — analisi del silenzio su iPhone (22 ago, prod)

**Sintomo (founder, in produzione, iPhone + Brave)**: i suoni singoli si
sentono; la stessa base dentro una SESSIONE no; la meditazione pubblicata
no. Da desktop tutto funziona.

## I fatti, in matrice

| Percorso | Player | iPhone | Desktop |
|---|---|---|---|
| Anteprima suono (Crea) | `<audio>` element | ✅ | ✅ |
| Ascolto continuo | `<audio>` element | ✅ | ✅ |
| Sessione in Crea | WebAudio → destination | ❌ | ✅ |
| Meditazione pubblicata | WebAudio → destination | ❌ | ✅ |

Tre eliminazioni che la matrice impone:
- **non è Brave**: su iOS ogni browser è WebKit per obbligo (Brave,
  Chrome, Firefox inclusi) — le regole audio sono quelle di Safari;
- **non sono i file/codec**: la meditazione muta è PURAMENTE sintetica
  (oscillatori WebAudio, zero m4a);
- **non è il mio analizzatore**: rimetterlo in parallelo (fix
  precedente) era giusto ma non basta — il silenzio precede Aurya Mode
  come categoria: e' il canale.

## La causa

Su iOS WebKit i due player vivono in regimi diversi: un elemento
`<audio>` è «media playback» (musica: suona sempre); il grafo WebAudio
collegato a `ctx.destination` è trattato come suono di CONTORNO —
soggetto al silenziatore e a politiche più severe. La discriminante
osservata (si sente ↔ non si sente) coincide ESATTAMENTE con questa
riga di confine. È lo stesso motivo per cui l'ascolto continuo (ciclo
AT) fu costruito su `<audio>`.

## La soluzione: UN canale solo, ovunque

Principio: il suono del motore deve uscire dallo STESSO canale delle
anteprime che già funzionano su ogni dispositivo. Il ponte:

```
motore (WebAudio) → MediaStreamDestination → <audio playsinline>
                 ↘ analizzatore (osserva, in parallelo)
```

- **iPhone**: l'`<audio>` è musica → il silenziatore non lo azzera;
- **Android/desktop**: comportamento identico a prima, ma ora è UN solo
  percorso per tutte le piattaforme — ciò che si testa su una vale per
  le altre («consistente», richiesta founder);
- l'`<audio>.play()` avviene DENTRO il gesto (il tocco su Ascolta):
  nessuna politica di autoplay lo blocca;
- in più, dove esiste (iOS 16.4+): `navigator.audioSession.type =
  'playback'` — dichiara l'intento anche al sistema;
- l'analizzatore resta un osservatore in parallelo (fix precedente,
  ancora valido); l'ascolto continuo resta com'è (già `<audio>`).

## Il processo di verifica (strutturato, non a orecchio)

1. **grafo** (automatico, dal browser): `sess → MediaStreamDestination`
   presente, `sess → destination` ASSENTE, `<audio>` con `srcObject`
   attivo e `paused === false` durante il play;
2. **desktop** (verifico io): sessione in Crea + meditazione;
3. **iPhone Brave** (founder): suono singolo → sessione → meditazione
   pubblicata, col silenziatore in ENTRAMBE le posizioni;
4. **Android** (quando disponibile): stessa checklist.
