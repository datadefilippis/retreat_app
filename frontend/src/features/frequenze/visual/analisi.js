/**
 * Aurya Mode — lo strato che ASCOLTA (AV1, 21/8/2026).
 *
 * Una sola verita' su «cosa sta facendo il suono adesso»: da qui
 * passano tutti i temi visivi, e nessuno di loro tocca mai un
 * AnalyserNode. Stessa disciplina del motore audio, dove analisi e
 * resa sono gemelle e una guardia le tiene d'accordo.
 *
 * Le bande sono quelle che un orecchio distingue davvero, non una
 * divisione aritmetica dello spettro: sotto i 200 Hz c'e' il corpo del
 * suono, sopra i 6 kHz c'e' l'aria. Ogni banda esce gia' LISCIATA —
 * un valore grezzo di FFT sfarfalla a 60 volte al secondo, e una
 * visualizzazione che sfarfalla non e' immersiva, e' nervosa.
 *
 * Il battito non si «rileva» con certezza (non e' un beat detector da
 * DJ): si misura quanto l'energia bassa supera la propria media
 * recente. Su una meditazione senza percussioni non trova battiti — ed
 * e' giusto cosi': la scena respira invece di pulsare.
 */

import { LISCIATURA_ANALYSER } from './tabelle';

/* Bande in Hz. Gli estremi contano: 20 Hz e' sotto l'udibile utile,
   20 kHz e' oltre quasi ogni orecchio adulto. */
export const BANDE = [
  { nome: 'bassi', da: 20, a: 200 },
  { nome: 'medioBassi', da: 200, a: 800 },
  { nome: 'medi', da: 800, a: 2500 },
  { nome: 'medioAlti', da: 2500, a: 6000 },
  { nome: 'alti', da: 6000, a: 20000 },
];

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
/* Lisciatura esponenziale: `k` e' quanto conta il valore NUOVO.
   Piccolo = movimento lento e nobile; grande = reattivo e nervoso.
   Ogni grandezza ha il suo tempo: l'energia complessiva si muove
   piano, i picchi devono essere immediati. */
const liscia = (vecchio, nuovo, k) => vecchio + (nuovo - vecchio) * k;

/**
 * Crea il lettore. NON crea il contesto audio e non lo chiude: si
 * innesta su un grafo che esiste gia' (il motore delle meditazioni,
 * un <audio>, il microfono) e resta un ospite.
 *
 * @param ctx   AudioContext vivo
 * @param fft   2048 = 1024 bin, ~21 Hz di risoluzione a 44,1 kHz:
 *              abbastanza fine per le bande, abbastanza grosso da
 *              costare poco su un telefono.
 */
export function creaLettore(ctx, { fft = 2048, analyser: prestato = null } = {}) {
  /* VS3 (24/8) — l'analizzatore puo' arrivare da FUORI: dove il flusso
     non si puo' spillare (Safari non ha captureStream sui media) la
     scena danza sulla RICETTA, dipinta con questa stessa superficie
     (ricetta.js). Da qui in giu' non cambia una riga: chi legge non
     deve sapere se sta guardando un segnale o una partitura. */
  const analyser = prestato || ctx.createAnalyser();
  if (!prestato) {
    analyser.fftSize = fft;
    /* La lisciatura DEL BROWSER viene dallo standard (DA2): un valore
       solo per strumento, studio e meditazione — due orecchie diverse
       facevano ballare la stessa scena in modi diversi. Resta bassa:
       le lisciature vere, banda per banda, le facciamo noi. */
    analyser.smoothingTimeConstant = LISCIATURA_ANALYSER;
    analyser.minDecibels = -90;
    analyser.maxDecibels = -10;
  }

  const bins = analyser.frequencyBinCount;
  const dati = new Uint8Array(bins);
  const hzPerBin = (analyser.context?.sampleRate || ctx.sampleRate) / 2 / bins;
  // indici precalcolati: fare la divisione a ogni fotogramma per ogni
  // banda e' lavoro inutile 60 volte al secondo
  const range = BANDE.map((b) => ({
    nome: b.nome,
    i0: Math.max(0, Math.floor(b.da / hzPerBin)),
    i1: Math.min(bins - 1, Math.ceil(b.a / hzPerBin)),
  }));

  const stato = {
    bande: Object.fromEntries(BANDE.map((b) => [b.nome, 0])),
    /* le bande GREZZE, senza lisciatura nostra: il motore immersivo ha
       il suo inseguitore asimmetrico, e dargli valori gia' lisciati
       significa lisciare due volte — la scena perde il colpo (successo:
       «non sono convinto che si muova col ritmo», founder). Le lisce
       restano per la Sorgente 2D, che un inseguitore non ce l'ha. */
    grezze: Object.fromEntries(BANDE.map((b) => [b.nome, 0])),
    energia: 0,
    dominante: 0,
    picco: 0,          // 0..1, scende da solo dopo un colpo
    battito: false,    // vero SOLO nel fotogramma del colpo
    mediaBassi: 0,
    spettro: dati,     // grezzo, per chi vuole disegnare le barre
    hzPerBin,
  };

  function leggi() {
    analyser.getByteFrequencyData(dati);

    let sommaTot = 0, maxV = 0, maxI = 0;
    for (const r of range) {
      let s = 0;
      for (let i = r.i0; i <= r.i1; i++) {
        const v = dati[i];
        s += v;
        if (v > maxV) { maxV = v; maxI = i; }
      }
      const grezzo = clamp01(s / ((r.i1 - r.i0 + 1) * 255));
      stato.grezze[r.nome] = grezzo;
      // i bassi seguono il colpo, gli alti scintillano: tempi diversi
      const k = r.nome === 'bassi' ? 0.35 : r.nome === 'alti' ? 0.45 : 0.28;
      stato.bande[r.nome] = liscia(stato.bande[r.nome], grezzo, k);
      sommaTot += grezzo;
    }

    stato.energia = liscia(stato.energia, clamp01(sommaTot / BANDE.length), 0.12);
    // la dominante salta di continuo se non la si tiene ferma un po'
    if (maxV > 40) stato.dominante = liscia(stato.dominante, maxI * hzPerBin, 0.15);

    /* Il colpo: l'energia bassa che supera del 35% la propria media
       lenta. La media si aggiorna DOPO il confronto, o un crescendo
       lento si mangerebbe da solo ogni picco. */
    const b = stato.bande.bassi;
    stato.battito = b > stato.mediaBassi * 1.35 && b > 0.12;
    stato.mediaBassi = liscia(stato.mediaBassi, b, 0.05);
    stato.picco = stato.battito ? 1 : Math.max(0, stato.picco - 0.06);

    return stato;
  }

  return { analyser, leggi, stato };
}
