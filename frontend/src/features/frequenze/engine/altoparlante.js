/**
 * Frequenze by Aurya — cosa esce davvero dall'altoparlante di un
 * telefono (AT1, 21/8/2026).
 *
 * Il fatto fisico: sotto i ~500 Hz l'altoparlante di un telefono non
 * riproduce quasi nulla — non e' un guasto, e' la dimensione della
 * membrana. 27 schede su 32 hanno il loro tono li' sotto: chi ascolta
 * dal telefono senza cuffie preme play e sente il silenzio.
 *
 * Il web NON puo' sapere se le cuffie sono collegate (nessuna API lo
 * dice, per privacy). Quindi non si puo' avvisare «solo chi ne ha
 * bisogno»: si puo' scegliere QUANDO (al play, non in un cartello
 * all'ingresso) e SU COSA (solo le schede davvero mute, cosi' quando
 * l'avviso compare significa qualcosa). Il «dove» — solo su telefono —
 * lo decide la stessa media query di .solo-telefono nel CSS: una
 * regola sola per «questo e' un telefono», non due.
 *
 * Questo modulo e' l'unica verita' sul tema: le pagine importano da
 * qui, non si ricalcolano una soglia propria (guardia nei test).
 */

export const SOGLIA_TELEFONO_HZ = 500;

/* La frequenza DOMINANTE: quella che decide se dal telefono si sente
   qualcosa. Non e' il battito (che e' un ritmo, non un'altezza) ma la
   portante — la nota che l'orecchio sente davvero.
   - noise: banda larga, l'altoparlante ne riproduce la parte alta →
     si sente sempre qualcosa → nessun avviso;
   - shepard: 7 voci su 7 ottave, ma il peso sta intorno alla portante:
     e' lei a decidere;
   - drone: le parti (1×, 1.5×, 1.25×) restano nell'ottava della
     portante: idem;
   - breath: fondamentale = portante, armoniche deboli sopra: idem.
   I default rispecchiano startCardLive: bin → 400, gli altri → 180. */
export function frequenzaDominante(cfg) {
  if (!cfg || cfg.method === 'noise') return null;
  return cfg.carrier ?? (cfg.method === 'bin' || !cfg.method ? 400 : 180);
}

const fmtHz = (hz) => String(hz).replace('.', ',');

/* I metodi in cui il numero in cima alla scheda E' GIA' questo tono
   («432 Hz», «Bordone 110 Hz»): li' ripeterlo non crea equivoci. */
const TONO_E_IL_TITOLO = { tone: 1, drone: 1 };

/**
 * Il messaggio per UNA scheda.
 *
 * Deve dire il numero vero — un avviso che dice «110 Hz» spiega, uno
 * generico ammonisce — ma soprattutto deve dire CHE COSA e' quel
 * numero. Sulle schede ritmiche il titolo porta gia' una frequenza che
 * e' un'ALTRA cosa: Delta dice «0,5–4 Hz» (il ritmo) e suona su una
 * portante di 140 Hz (il tono). Un avviso che lascia cadere «140 Hz»
 * accanto a «0,5–4 Hz» senza spiegare mette in contraddizione la
 * scheda con se stessa — proprio dove il testo lungo insegna che «una
 * banda EEG e una frequenza sonora non sono la stessa cosa».
 */
export function avvisoCuffie(cfg) {
  const hz = frequenzaDominante(cfg);
  if (hz == null || hz >= SOGLIA_TELEFONO_HZ) return null;
  const m = cfg.method || 'bin';
  const coda = `troppo grave per l'altoparlante del telefono: servono le cuffie.`;
  if (m === 'shepard') return `Le voci più gravi della discesa sono ${coda}`;
  if (TONO_E_IL_TITOLO[m]) return `Un tono di ${fmtHz(hz)} Hz è ${coda}`;
  return `Il ritmo viaggia su un tono di ${fmtHz(hz)} Hz, ${coda}`;
}

/* Il messaggio per uno SCORE (pagina pubblica): guarda i livelli neuro
   udibili e nomina il piu' grave. Le basi audio e la voce si sentono
   comunque — ed e' proprio il caso subdolo: si sente la voce, e le
   frequenze mancano in silenzio. */
export function avvisoCuffieScore(score) {
  const gravi = (score?.layers || [])
    .filter((l) => (l.kind || 'neuro') === 'neuro' && !l.mute && (l.gain ?? 1) > 0)
    .map((l) => frequenzaDominante(l))
    .filter((hz) => hz != null && hz < SOGLIA_TELEFONO_HZ);
  if (!gravi.length) return null;
  const hz = Math.min(...gravi);
  const altro = (score.layers || []).some(
    (l) => l.kind === 'audio' || l.kind === 'voice');
  // Anche qui il numero va presentato per quello che e': il TONO su cui
  // viaggiano le frequenze, non il ritmo che la sessione dichiara.
  return altro
    ? `Dal telefono servono le cuffie: il tono più grave (${fmtHz(hz)} Hz) non esce dall'altoparlante, anche se voce e basi si sentono.`
    : `Dal telefono servono le cuffie: il tono su cui viaggiano le frequenze (${fmtHz(hz)} Hz) non esce dall'altoparlante.`;
}
