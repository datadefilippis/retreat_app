/**
 * GROUND — la seconda esperienza di Aurya Sound (STEP 9, 26/8/2026).
 *
 * Come CALM: dati, non codice. Nessuna API nuova, nessun metodo nuovo,
 * il motore non e' stato toccato.
 *
 * DOVE CALM CREA SPAZIO, GROUND CREA PESO. E la differenza non e' un
 * aggettivo, e' costruita:
 *   - un'ottava piu' in basso (Re invece di La);
 *   - CALM aggiunge (il battito entra a meta'), GROUND SOTTRAE: si
 *     semplifica andando avanti, e finisce con una cosa sola;
 *   - CALM non ha materia (solo toni), GROUND ha il rumore bruno;
 *   - CALM e' fermo al centro, GROUND si apre alla fine.
 *
 * QUATTRO LIVELLI, mai piu' di tre insieme:
 *
 *   IL PESO (bordone, 73,42 Hz — Re2) e' la terra: sta sotto e non
 *   cambia mai. Il metodo costruisce una triade naturale (fondamentale
 *   · 1,25 · 1,5), qui 73,4 / 91,8 / 110,1 — un grappolo compatto e
 *   caldo. La sua quinta cade su 110,1: la nota di CALM. Le due
 *   esperienze sono imparentate senza volerlo.
 *
 *   LA MATERIA (rumore bruno) e' il corpo. Il bruno e' il piu' cupo
 *   dei tre e sta nello stesso registro del peso: lo ispessisce invece
 *   di coprirlo. Nel motore il rumore e' un VEICOLO DI RITMO — viene
 *   modulato dal battito — quindi il suo gonfiarsi ogni 11→17 secondi
 *   e' una marea, non un ronzio.
 *
 *   LA PULSAZIONE (isocronico, 146,83 Hz = l'ottava esatta del peso)
 *   e' il passo: un tono a intermittenza, 33 → 24 impulsi al minuto.
 *   Deliberatamente sotto qualsiasi tempo musicale (il piu' lento sta
 *   sopra i 40) e sotto un battito cardiaco a riposo: ritmica senza
 *   diventare una canzone e senza imitare il cuore.
 *
 *   L'APERTURA (bilaterale, 220,25 Hz = tre volte il peso) e' spazio:
 *   un tono alto e quieto che dondola fra le orecchie ogni ~8 secondi.
 *   E' un fenomeno spaziale, non neurologico. Entra quando la materia
 *   se ne va: l'apertura E' la sottrazione, il dondolio la rende
 *   percepibile.
 *
 * LE PORTANTI SONO LA STESSA SERIE ARMONICA (73,42 · ×2 · ×3):
 * verificato nel Lab, rapporti 2,000 e 3,000. Non aggiungono note:
 * fondono in un corpo solo visto da tre altezze.
 *
 * COSA NON C'E', e perche': nessun binaurale (lo usa CALM, e GROUND
 * dev'essere un altro posto); nessuna discesa infinita (non si posa
 * mai, e qui tutto deve posarsi); nessun tono discendente (verificato:
 * nel motore `tone` ha frequenza fissa — non e' esprimibile, e non si
 * aggira).
 *
 * IL GUADAGNO DELLA MATERIA E' 0,07, e non e' un caso: misurando il
 * motore vero, a 0,20 il rumore risultava PIU' FORTE del peso (rms
 * -17,0 contro -22,0 dB), perche' il rumore bruno ha moltiplicatori
 * interni che rendono il numero nominale ingannevole. A 0,07 sta 9 dB
 * sotto: una presenza, non un letto.
 *
 * LE CUFFIE. Le tre portanti stanno tutte sotto i 500 Hz della soglia
 * di casa (engine/altoparlante.js): dall'altoparlante di un telefono
 * GROUND perde la fondazione e resta il passo senza il peso — cioe'
 * perde proprio cio' che e'. Il testo lo dice, e l'avviso di sistema
 * lo ripete da solo.
 */
import { layer } from './protocolli';

export const GROUND_DURATA = 480;          // 8:00
export const GROUND_FADE_IN = 16;
export const GROUND_FADE_OUT = 30;

/* I tempi in secondi: li leggono lo score, le fasi e le guardie. */
export const GROUND_TEMPI = Object.freeze({
  materiaDa: 60, materiaA: 340,
  pulsazioneDa: 150, pulsazioneA: 400,
  aperturaDa: 330, aperturaA: 420,
});

export const GROUND_FASI = Object.freeze([
  { t: 0, name: 'arrivo' },
  { t: 60, name: 'peso' },
  { t: 150, name: 'stabilità' },
  { t: 330, name: 'apertura' },
  { t: 420, name: 'congedo' },
]);

export function costruisciGround(d = GROUND_DURATA) {
  const T = GROUND_TEMPI;
  return {
    score_version: 1,
    duration_sec: d,
    fade_in_sec: GROUND_FADE_IN,
    fade_out_sec: GROUND_FADE_OUT,
    layers: [
      layer({
        name: 'Peso', method: 'drone', carrier: 73.42,
        start: 0, end: d, gain: 0.26, duration: d,
      }),
      layer({
        name: 'Materia', method: 'noise', color: 'brown',
        f0: 0.09, f1: 0.06, curve: 'exp',
        start: T.materiaDa, end: T.materiaA, gain: 0.07, duration: d,
      }),
      layer({
        name: 'Pulsazione', method: 'iso', carrier: 146.83,
        f0: 0.55, f1: 0.40, curve: 'exp',
        start: T.pulsazioneDa, end: T.pulsazioneA, gain: 0.16, duration: d,
      }),
      layer({
        name: 'Apertura', method: 'bil', carrier: 220.25,
        f0: 0.12, f1: 0.12,
        start: T.aperturaDa, end: T.aperturaA, gain: 0.13, duration: d,
      }),
    ],
    phases: GROUND_FASI.map((f) => ({ ...f })),
  };
}
