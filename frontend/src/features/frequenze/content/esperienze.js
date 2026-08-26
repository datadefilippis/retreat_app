/**
 * IL REGISTRO DELLE ESPERIENZE INTEGRATE (26/8/2026).
 *
 * Non e' un CMS e non vuole diventarlo: e' l'elenco delle esperienze
 * che Aurya spedisce dentro il prodotto, con il minimo che serve a
 * presentarle e a costruirne lo score. Le esperienze degli OPERATORI
 * sono un'altra cosa e vivono nel database.
 *
 * Aggiungere un'esperienza significa: scrivere il suo protocollo (uno
 * score, cioe' dati) e registrarla qui. Non si programma un motore.
 *
 * Ogni voce ha soltanto:
 *   titolo, sottotitolo   cosa vede chi arriva
 *   racconto              la riga onesta su com'e' fatta
 *   durata                secondi (il tetto di casa e' 10 minuti)
 *   costruisci(d)         → lo score, valido secondo il contratto v1
 *
 * L'avviso cuffie NON sta qui: lo calcola il motore dallo score
 * (engine/altoparlante.js), perche' dipende dai toni che l'esperienza
 * usa davvero — non da un'etichetta che qualcuno potrebbe dimenticare
 * di aggiornare.
 */
import { costruisciCalm, CALM_DURATA } from './calm';

export const ESPERIENZE = Object.freeze({
  calm: {
    id: 'calm',
    titolo: 'CALM',
    sottotitolo: 'Una breve esperienza sonora per creare uno spazio di calma.',
    racconto: 'Sei minuti. Un suono che rallenta, e ti lascia rallentare.',
    durata: CALM_DURATA,
    costruisci: costruisciCalm,
  },
});

export const esperienza = (id) => ESPERIENZE[id] || null;
