/**
 * Aurya Sound — controindicazioni: UNA fonte sola (SF, 20/8/2026).
 *
 * Prima di oggi lo stesso avviso viveva riscritto in tre punti (il
 * sipario del compositore, la pagina pubblica di una traccia, l'elenco
 * delle meditazioni), con parole diverse: il giorno in cui se ne
 * correggeva uno, gli altri due restavano indietro. Da qui in avanti il
 * testo sta scritto una volta e le pagine lo citano — con una guardia
 * nei test che impedisce di riscriverlo a mano altrove.
 *
 * La regola decisa dal founder (20/8): il sipario si apre PRIMA DEL
 * SUONO, non prima della pagina — chi legge la Guida non incontra un
 * muro medico — e si ripresenta ogni 90 giorni. In piu', un pulsante
 * «Controindicazioni» sempre visibile per rileggerle quando si vuole,
 * senza dover aspettare che scada nulla.
 *
 * L'accettazione resta LOCALE (nessun dato personale in piu': niente
 * da dichiarare nella privacy policy).
 */

/* Cambiare questo numero riapre il sipario a tutti: si alza SOLO
   quando cambia la sostanza dell'avviso, mai per una virgola. */
export const SAFETY_VERSION = 1;
export const SAFETY_DAYS = 90;
const KEY = 'fqz_safety';

export const SAFETY_TITLE = 'Prima di ascoltare';

export const SAFETY_INTRO = "Aurya Sound genera stimolazione uditiva "
  + '(battiti binaurali, toni isocronici e monoaurali, stimolazione '
  + 'bilaterale, toni puri). Non è un dispositivo medico e non '
  + 'diagnostica, cura o previene alcuna condizione.';

/* La riga che resta sempre a vista accanto a chi sta per ascoltare:
   una sola, corta, senza allarmismo — il resto è a un clic. */
export const SAFETY_LINE = '🎧 Cuffie e volume moderato. '
  + 'Non adatto in caso di epilessia o pacemaker.';

export const SAFETY_WARN = 'Non usare in caso di epilessia o storia di '
  + 'convulsioni, con pacemaker o dispositivi impiantati. In gravidanza, '
  + 'consultare prima il medico. Mai durante la guida o l\'uso di macchinari.';

export const SAFETY_POINTS = [
  ['Volume moderato.', 'Se il battito si sente nettamente sopra il resto, è troppo forte.'],
  ['Cuffie.', "Le componenti binaurali danno l'effetto solo in cuffia: dalle casse il suono si sente comunque, ma cambia natura."],
  ['Rientro.', 'Ogni sessione profonda termina con una risalita graduale — i protocolli la contengono già.'],
  ['Stimolazione bilaterale.', "Componente sonoro usato anche nell'EMDR, ma l'EMDR è un protocollo clinico condotto da terapeuti formati: questo strumento non lo sostituisce."],
  ['Disagio.', 'In caso di vertigini, nausea o malessere, interrompere l’ascolto.'],
];

/** Vero se l'avviso è stato accettato, nella versione corrente e da
 *  meno di SAFETY_DAYS giorni. Un localStorage illeggibile o di una
 *  versione vecchia vale come «mai accettato»: in dubbio si mostra. */
export function safetyAccepted() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (!raw || raw.v !== SAFETY_VERSION || !raw.t) return false;
    return (Date.now() - raw.t) < SAFETY_DAYS * 24 * 3600 * 1000;
  } catch { return false; }
}

export function acceptSafety() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ v: SAFETY_VERSION, t: Date.now() }));
  } catch { /* navigazione privata: si richiederà di nuovo, va bene così */ }
}
