/**
 * RESPIRO — dieci minuti a sei atti al minuto (C2, 26/8/2026).
 *
 * LA SCHEDA CON LE BASI PIU' SOLIDE DI TUTTO IL CATALOGO, e per una
 * ragione che si puo' dire in una riga: qui la pratica documentata
 * non e' «ascoltare un suono», e' RESPIRARE A UN CERTO RITMO. Il
 * suono e' la guida, e la letteratura sulla respirazione di risonanza
 * (Lehrer, Gevirtz) parla proprio di quello.
 *
 * I NUMERI, che sono la sostanza:
 *   - SEI ATTI AL MINUTO — il centro della finestra di risonanza
 *     (4,5-6,5). Un RCT del 2026 ha mostrato che il ritmo fisso a
 *     0,1 Hz vale quanto quello personalizzato: possiamo dare a tutti
 *     lo stesso protocollo senza doverlo misurare persona per persona.
 *   - RAPPORTO 4:6 fra inspirazione ed espirazione — la
 *     raccomandazione per massimizzare l'ampiezza della variabilita'
 *     cardiaca. Qui: 3,6 s dentro, 5,4 s fuori, 1 s di pausa.
 *   - COSTANTE. Niente discese, niente sorprese: la pratica e' stare
 *     a quel ritmo, e la costanza E' il protocollo.
 *
 * LA GUIDA CHE SI PUO' ANTICIPARE (`guida: true`). Il respiro-texture
 * dice dove sei; una guida deve dire QUANDO CAMBIERA', o si insegue
 * invece di respirare insieme. Quindi: l'altezza scivola su
 * inspirando e giu' espirando (la pendenza si sente, e fa prevedere
 * l'arrivo) e un tocco discreto segna la svolta di ogni fase. Sono le
 * due convenzioni dei pacer uditivi seri; il resto — imitare il suono
 * di un respiro — l'abbiamo provato e buttato: era finto.
 *
 * DUE VOCI SOLE. Un fondo che tiene lo spazio, e la guida sopra.
 * Nessun battito, nessuna materia: qui l'attenzione ha UN posto dove
 * stare, e aggiungere sarebbe togliere.
 *
 * COSA NON PROMETTE. Che respirare lentamente faccia bene a chiunque
 * per qualsiasi cosa: la scheda dichiara cosa dice la letteratura e
 * dove finisce. E finche' non ci sara' un sensore (roadmap S7), qui
 * si GUIDA soltanto: non si misura niente, e non lo diciamo.
 */
import { layer } from './protocolli';

export const RESPIRO_DURATA = 600;         // 10:00
export const RESPIRO_FADE_IN = 12;
export const RESPIRO_FADE_OUT = 24;

/** atti al minuto → Hz del ciclo (la stessa conversione di CALM) */
export const alMinuto = (n) => n / 60;

/** Il ritmo della pratica, e il rapporto fra le due fasi. */
export const RESPIRO_AL_MINUTO = 6;
export const RESPIRO_INSPIRA = 0.36;       // 3,6 s del ciclo da 10 s
export const RESPIRO_ESPIRA = 0.54;        // 5,4 s — il rapporto e' 4:6

/* Il fondo comincia subito; la guida entra dopo mezzo minuto, quando
   la stanza si e' fatta silenziosa, e resta fino al congedo. */
export const RESPIRO_TEMPI = Object.freeze({
  guidaDa: 30, guidaA: 570,
});

export const RESPIRO_FASI = Object.freeze([
  { t: 0, name: 'arrivo' },
  { t: 30, name: 'la guida' },
  { t: 570, name: 'congedo' },
]);

export function costruisciRespiro(d = RESPIRO_DURATA) {
  const T = RESPIRO_TEMPI;
  return {
    score_version: 1,
    duration_sec: d,
    fade_in_sec: RESPIRO_FADE_IN,
    fade_out_sec: RESPIRO_FADE_OUT,
    layers: [
      layer({
        /* il fondo: sotto la guida, mai in gara con lei */
        name: 'Fondo', method: 'drone', carrier: 110,
        start: 0, end: d, gain: 0.16, duration: d,
      }),
      layer({
        /* LA GUIDA: 220 Hz che sale di tre semitoni inspirando e
           torna espirando. f0 = f1 = il ritmo, costante per tutta la
           pratica — e' proprio la costanza il protocollo. */
        name: 'Guida', method: 'breath', carrier: 220,
        f0: alMinuto(RESPIRO_AL_MINUTO), f1: alMinuto(RESPIRO_AL_MINUTO),
        inhale: RESPIRO_INSPIRA, exhale: RESPIRO_ESPIRA,
        guida: true,
        start: T.guidaDa, end: T.guidaA, gain: 0.30, duration: d,
      }),
    ],
    phases: RESPIRO_FASI.map((f) => ({ ...f })),
  };
}
