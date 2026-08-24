# Piano — il visual torna a vedersi nelle meditazioni (24/8/2026)

Founder: «nelle meditazioni il suono non si visualizza più (visual
suono), come mai? per il compress dell'mp3? si può fixare e impostare
visual selezionato in crea?»

**L'intuizione è giusta: è una conseguenza del master.** Ma non della
compressione — di una condizione di una riga che nel frattempo ha
cambiato significato.

---

## La diagnosi

`PublicFrequencyPage.js:485`

```jsx
{guarda && lettore && !continuo && (
  <AuryaMode … visual={track.score?.visual || null} />
)}
```

**`!continuo`.** Quando fu scritta (AT3, 21/8) `continuo` voleva dire
«il caso raro in cui il suono esce da un `<audio>` invece che dal
motore»: si evitava di disegnare perché per analizzare quell'`<audio>`
bisognava portarlo dentro WebAudio, e su iOS questo lo rimette sotto il
tasto silenzioso e lo uccide a schermo bloccato. Giusto allora.

Poi è arrivato IL MASTER (23/8) e il caso raro è diventato **l'unico
caso**: `setContinuo(true)` sta su tutti e tre i rami vivi (anteprima,
master, sintesi). Da quel giorno la condizione non protegge più niente
— **spegne il visual sempre**, su ogni meditazione e ogni browser.

Non «non reagisce al suono»: proprio **non viene disegnato**.

Prova della deriva: il 23/8 avevo aggiunto `presaAnalisi()` — la presa
che porta al visual una *copia* del flusso senza dirottare l'uscita —
e la chiamo su entrambi i rami. Alimenta un analyser che **nessuno
disegna**. Codice morto che sembrava una funzione viva: il segno che le
due modifiche non si sono mai guardate in faccia.

E la scena scelta in Crea? Viaggia già nella ricetta (`score.visual`,
VC1) e la riga qui sopra la passa. **Non era rotta: era invisibile
perché lo era tutto il visual.** Togliendo `!continuo` torna anche
quella — la seconda domanda del founder ha la stessa risposta della
prima.

### Il secondo difetto, sotto il primo

`presaAnalisi` usa `HTMLMediaElement.captureStream()`. Due problemi:

1. **Safari non ce l'ha.** Né su iPhone né su Mac. Sul telefono del
   founder — dov'è nato «Guarda il suono» — la presa non può riuscire:
   restituisce `false` e la scena resterebbe in veglia anche dopo il
   fix. Metà del lavoro, la metà che si vede di meno.
2. **Si chiama troppo presto**: subito dopo `new Audio(url)`, quando
   l'elemento non ha ancora tracce. Su Chrome `getAudioTracks()` può
   essere vuoto → `false` anche dove funzionerebbe.

---

## La cura — tre onde

### VS1 · la scena torna a vedersi
Via `!continuo`. Al suo posto la condizione onesta: si disegna se c'è
**un'analisi viva**, qualunque sia la strada da cui arriva.

### VS2 · la presa al momento giusto
`presaAnalisi` si tenta al primo `playing` (l'elemento ha le tracce) e
non alla nascita. Se fallisce non si insiste: si passa a VS3.

### VS3 · lo spettro dipinto — la scena danza dove il flusso non si può ascoltare
Dove `captureStream` non esiste (Safari, iOS) il visual non ha un
segnale da guardare. Ma ha **la ricetta**, che è la verità della
composizione: sa quali livelli suonano adesso, con che guadagno, a che
portante e con che battito.

Si dipinge quindi uno spettro plausibile e si consegna al motore
attraverso **la stessa superficie di un AnalyserNode**
(`frequencyBinCount`, `fftSize`, `getByteFrequencyData`,
`getByteTimeDomainData`): il prototipo non può accorgersi della
differenza, e **nessuna riga del motore visivo va toccata**.

Onestà su cosa è e cosa non è:

| | flusso vero | spettro dipinto |
|---|---|---|
| struttura (livelli che entrano/escono, dissolvenze) | sì | **sì, esatta** |
| portante e battito dei livelli neuro | sì | **sì, dalla ricetta** |
| transienti veri di una base registrata | sì | no: un letto che respira |
| sillabe della voce | sì | no: una modulazione di parlato |

Non si finge un ascolto: si **suona la partitura per gli occhi**. Il
costo è zero (nessun file decodificato: erano loro il gigabyte di RAM
che abbiamo tolto) e funziona ovunque, iPhone compreso.

### VS3-bis · la rete che nessuno vede
Se `captureStream` riesce ma consegna silenzio (flusso *tainted*, un
caso che non si distingue dall'esterno), dopo 3 secondi di riproduzione
l'energia letta è ancora zero: allora si passa da soli allo spettro
dipinto. Mai una scena morta senza che nessuno se ne accorga.

La sorgente in uso si dichiara in `?ascolto=1`, dove già si racconta il
ramo di riproduzione — mai un comportamento muto.

---

## Cosa NON si tocca

Il suono. L'`<audio>` resta puro su tutti i rami: nessun
`createMediaElementSource`, nessun grafo in mezzo, l'ascolto a schermo
bloccato resta quello che è (la lezione AT3 vale ancora, ed è proprio
per non tradirla che nasce lo spettro dipinto invece della strada
comoda). Master, anteprima, pubblicazione, privilegio del comporre:
fermi.
