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
/* SOUND_LETTORE_IN_CASA (MR3, 8/10/2026): l'ascolto parte dove sei — card e
   righe suonano nella barra in basso, il titolo apre il foglio; a false le
   card tornano a portare alla pagina della meditazione. */
export const SOUND_LETTORE_IN_CASA = true;
/* VISUAL_PUBBLICO_ATTIVO (MR3, founder decisione 3): al pubblico niente Visual
   sulla pagina della meditazione (c'e' la copertina); chi compone lo vede. */
export const VISUAL_PUBBLICO_ATTIVO = false;
export const PIU_PREZZO = '39 € l\'anno';
/* SOUND_HUB_SEMPLICE (MR6): a true /sound e' l'hub di pulsanti di SN1; a false
   (founder 8/10 sera) la landing esplicativa, ottimizzata. */
export const SOUND_HUB_SEMPLICE = false;
/* SOUND_ESPLORA_NUOVA (lotto ES, 8/10/2026): /sound/esplora e /sound/impara
   diventano pagine proprie (esplora/BibliotecaPage, esplora/FondamentaPage)
   con il selettore a tre; a false si torna alle viste dentro il compositore. */
export const SOUND_ESPLORA_NUOVA = true;
