/**
 * CALM — il primo protocollo esperienziale di Aurya Sound
 * (STEP 8, 26/8/2026).
 *
 * E' DATI, non codice: uno score come quelli che il motore
 * (engine/synth.js) suona da sempre. Nessuna nuova API, nessun
 * secondo motore — l'esperienza chiede a `startPreview` di suonare
 * questo, esattamente come fa una traccia pubblicata.
 *
 * SEI MINUTI, e sono una scelta. Il nemico numero uno di
 * un'esperienza sonora non e' la noia: e' non arrivare in fondo. Sei
 * minuti si fanno ADESSO, senza programmare nulla, e bastano per un
 * arco vero in cinque tempi con code d'entrata e d'uscita oneste. A
 * cinque il congedo diventa frettoloso; oltre gli otto diventa «una
 * meditazione», qualcosa a cui ci si deve dedicare.
 *
 * TRE ELEMENTI, TRE MESTIERI — e nient'altro. Niente 432, niente
 * 528, niente campane, niente rumore, niente voce, niente riverbero:
 * il miscuglio olistico e' proprio cio' che questo protocollo non
 * vuole essere.
 *
 *   IL FONDO (bordone, 110 Hz) e' la stanza. Da' all'orecchio
 *   qualcosa di fermo su cui posarsi, e fa si' che il silenzio della
 *   fine sia un silenzio abitato invece di un vuoto.
 *
 *   IL RESPIRO (respiro guidato, 220 Hz) e' il protagonista e l'unico
 *   vero dispositivo: un ritmo udibile che RALLENTA, da 8 a 5,5 cicli
 *   al minuto. Non chiede nulla — chi vuole lo segue. (Il metodo non
 *   imita l'aria: e' un accordo di armoniche che si apre inspirando e
 *   si chiude espirando, con l'espirazione piu' lunga.)
 *
 *   IL BATTITO (binaurale, 330 Hz, differenza 7 → 6 Hz) e' un
 *   movimento interno nella parte piu' immobile. Entra quando il
 *   respiro ha gia' rallentato ed esce prima del congedo.
 *
 * LE TRE PORTANTI SONO IMPARENTATE — 110, 220, 330: la stessa nota,
 * la sua ottava e la sua quinta. Si fondono invece di litigare.
 *
 * ONESTA': qui non si afferma nessun effetto fisiologico. Il
 * binaurale e' descritto per quello che si sente — un battito lento
 * fra i due canali — e non per stati cerebrali che non possiamo
 * sostenere. Chi vuole la scienza la trova nella biblioteca, dove
 * ogni scheda dichiara il suo livello di evidenza.
 */
import { layer } from './protocolli';

export const CALM_DURATA = 360;          // 6:00
export const CALM_FADE_IN = 12;
export const CALM_FADE_OUT = 24;

/* I tempi in secondi, scritti una volta sola: li leggono lo score,
   la pagina e le guardie. */
export const CALM_TEMPI = Object.freeze({
  respiroDa: 6, respiroA: 320,
  battitoDa: 150, battitoA: 270,
});

/* Le fasi sono marcatori narrativi (il motore le porta nello score,
   la pagina non le mostra: durante l'ascolto lo schermo tace). */
export const CALM_FASI = Object.freeze([
  { t: 0, name: 'arrivo' },
  { t: 90, name: 'rallentamento' },
  { t: 150, name: 'sosta' },
  { t: 270, name: 'rientro' },
  { t: 320, name: 'congedo' },
]);

/** cicli al minuto → hertz (il motore ragiona in Hz anche per il respiro) */
const alMinuto = (n) => n / 60;

export function costruisciCalm(d = CALM_DURATA) {
  const T = CALM_TEMPI;
  return {
    score_version: 1,
    duration_sec: d,
    fade_in_sec: CALM_FADE_IN,
    fade_out_sec: CALM_FADE_OUT,
    layers: [
      layer({
        name: 'Fondo', method: 'drone', carrier: 110,
        start: 0, end: d, gain: 0.22, duration: d,
      }),
      layer({
        name: 'Respiro', method: 'breath', carrier: 220,
        f0: alMinuto(8), f1: alMinuto(5.5), curve: 'exp',
        start: T.respiroDa, end: T.respiroA, gain: 0.30, duration: d,
      }),
      layer({
        name: 'Battito', method: 'bin', carrier: 330,
        f0: 7, f1: 6, curve: 'exp',
        start: T.battitoDa, end: T.battitoA, gain: 0.16, duration: d,
      }),
    ],
    phases: CALM_FASI.map((f) => ({ ...f })),
  };
}
