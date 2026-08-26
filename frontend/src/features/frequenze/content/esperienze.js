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
 *   cuffie                UNA riga sola: cosa cambia con le cuffie. Il
 *                         dettaglio per i telefoni lo dicono gia' la riga
 *                         di sicurezza e l'avviso di sistema — dirlo tre
 *                         volte prima di partire era un muro di testo
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
import { costruisciRespiro, RESPIRO_DURATA, RESPIRO_AL_MINUTO } from './respiro';

export const ESPERIENZE = Object.freeze({
  calm: {
    id: 'calm',
    titolo: 'CALM',
    sottotitolo: 'Una breve esperienza sonora per creare uno spazio di calma.',
    racconto: 'Un suono che rallenta, e ti lascia rallentare.',
    cuffie: 'Con le cuffie percepisci anche un battito lento fra i due canali.',
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
    cuffie: 'Il peso di GROUND vive in un registro basso: con le cuffie, '
      + 'o un altoparlante vero, l’esperienza è intera.',
    durata: GROUND_DURATA,
    costruisci: costruisciGround,
  },
  respiro: {
    id: 'respiro',
    titolo: 'RESPIRO',
    sottotitolo: `Dieci minuti a ${RESPIRO_AL_MINUTO} respiri al minuto.`,
    racconto: 'Una nota che sale mentre inspiri e scende mentre '
      + 'espiri, e un tocco che segna ogni svolta: non devi contare, '
      + 'devi solo seguire. Il ritmo è costante — sei atti al minuto, '
      + 'con l’espirazione più lunga dell’inspirazione — ed è proprio '
      + 'la costanza a essere la pratica.',
    cuffie: 'In cuffia o in cassa: la guida si sente bene comunque, '
      + 'perché è una nota e non un battito fra le orecchie.',
    durata: RESPIRO_DURATA,
    costruisci: costruisciRespiro,
  },
});

export const esperienza = (id) => ESPERIENZE[id] || null;
export const ELENCO = Object.values(ESPERIENZE);
