/**
 * IL REGISTRO DELLE ESPERIENZE INTEGRATE (26/8/2026).
 *
 * Non e' un CMS e non vuole diventarlo: e' l'elenco delle esperienze
 * che Aurya spedisce dentro il prodotto, con il minimo che serve a
 * presentarle e a costruirne lo score. Le esperienze degli OPERATORI
 * sono un'altra cosa e vivono nel database.
 *
 * Aggiungere un'esperienza significa: scrivere il suo protocollo (uno
 * score, cioe' dati) e registrarla qui. Non si programma un motore, e
 * dallo STEP 9 non si scrive nemmeno una pagina: la presentazione e'
 * una sola (esperienze/EsperienzaPage) e legge da qui.
 *
 * Ogni voce ha soltanto:
 *   titolo, sottotitolo   cosa vede chi arriva
 *   racconto              com'e' fatta, in una battuta
 *   cuffie                cosa cambia senza cuffie — parole diverse per
 *                         esperienze diverse, perche' la dipendenza dal
 *                         registro basso non e' la stessa
 *   durata                secondi (il tetto di casa e' 10 minuti)
 *   costruisci(d)         → lo score, valido secondo il contratto v1
 *
 * L'AVVISO cuffie vero e proprio NON sta qui: lo calcola il motore
 * dallo score (engine/altoparlante.js), perche' dipende dai toni che
 * l'esperienza usa davvero — non da un'etichetta che qualcuno
 * potrebbe dimenticare di aggiornare.
 */
import { costruisciCalm, CALM_DURATA } from './calm';
import { costruisciGround, GROUND_DURATA } from './ground';

export const ESPERIENZE = Object.freeze({
  calm: {
    id: 'calm',
    titolo: 'CALM',
    sottotitolo: 'Una breve esperienza sonora per creare uno spazio di calma.',
    racconto: 'Sei minuti. Un suono che rallenta, e ti lascia rallentare.',
    cuffie: 'Con le cuffie percepisci anche un battito lento fra i due '
      + 'canali. Le cuffie non sono obbligatorie, ma dall’altoparlante '
      + 'di un telefono i toni gravi si perdono: se puoi, usale.',
    durata: CALM_DURATA,
    costruisci: costruisciCalm,
  },
  ground: {
    id: 'ground',
    titolo: 'GROUND',
    sottotitolo: 'Otto minuti per ritrovare il peso.',
    racconto: 'Un registro basso che resta fermo, una materia sonora che '
      + 'va e viene, una pulsazione lenta. Andando avanti tutto si '
      + 'semplifica, e alla fine resta solo il peso.',
    cuffie: 'Qui le cuffie contano davvero: il peso di GROUND vive in un '
      + 'registro basso che l’altoparlante di un telefono non riesce a '
      + 'riprodurre. Con le cuffie, o un altoparlante vero, l’esperienza '
      + 'è intera.',
    durata: GROUND_DURATA,
    costruisci: costruisciGround,
  },
});

export const esperienza = (id) => ESPERIENZE[id] || null;
export const ELENCO = Object.values(ESPERIENZE);
