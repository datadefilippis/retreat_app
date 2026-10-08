/**
 * stato.js — i flag del mondo Sound (piano Aurya Sound, 8/10/2026).
 *
 * SOUND_CASA_NUOVA (SN1): la casa delle meditazioni (casa/MeditazioniCasa),
 * la passerella unica e l'hub /sound al posto della vetrina, della passerella
 * a tre voci e della landing. Le pagine vecchie restano accanto finche' la
 * prova dal vivo non e' chiusa: a false si torna a ieri in un colpo.
 *
 * SOUND_PIU_ATTIVO (SN4): l'abbonamento ascoltatore (Più, 39 €/anno, solo
 * annuale). Qui il flag del FRONTEND (pagina /meditazioni/piu, badge e
 * inviti); il server ha il suo (`SOUND_PIU_ATTIVO` nell'ambiente) che chiude
 * checkout e portale. Il giorno dell'accensione si alzano entrambi
 * (docs/SOUND_PIU_ACCENSIONE_2026-10-08.md).
 */
export const SOUND_CASA_NUOVA = true;
export const SOUND_PIU_ATTIVO = false;
/* SOUND_ANNUNCI_ATTIVI (founder 8/10/2026 sera): «Annuncia al Cerchio» non si
   vede e non parte finche' le meditazioni non ci sono. Il server ha lo stesso
   interruttore nell'ambiente (SOUND_ANNUNCI_ATTIVI): spento, risponde 404. */
export const SOUND_ANNUNCI_ATTIVI = false;
export const PIU_PREZZO = '39 € l\'anno';
