/**
 * NL-octies (20/8/2026, founder) — un solo posto per i link alla porta.
 *
 * Il difetto che ha fatto nascere questo file: dal gate delle meditazioni
 * «Crealo gratis» portava a `/accedi?next=/meditazioni`, cioe' alla
 * SCHERMATA DI ACCESSO invece che a quella di registrazione, e l'email
 * appena digitata andava persa. Dalle guide del Magazine, invece, l'email
 * veniva mantenuta: due comportamenti per lo stesso gesto, a seconda di
 * dove ci si trovava. La regola stava scritta a mano, ogni volta, in ogni
 * pagina — quindi divergeva.
 *
 * Qui la regola e' una sola, e chi la usa non puo' sbagliarla:
 *   - `vista` decide QUALE schermata si apre (crea / recupero / accesso);
 *   - `email` la porta con se', cosi' non si ridigita;
 *   - `next` dice dove tornare dopo, cioe' il contenuto da cui si e'
 *     partiti.
 *
 * La porta (`AccountLoginPage`) legge tutti e tre i parametri.
 */

/** Link alla porta di Aurya. Tutti i campi sono facoltativi. */
export function portaAurya({ vista, email, next } = {}) {
  const q = new URLSearchParams();
  if (vista) q.set('vista', vista);                 // 'crea' | 'recupero'
  if (next) q.set('next', next);
  const pulita = (email || '').trim();
  if (pulita) q.set('email', pulita);
  const s = q.toString();
  return s ? `/accedi?${s}` : '/accedi';
}

/** «Crea il tuo account» — la registrazione, non l'accesso. */
export const creaAccount = (email, next) =>
  portaAurya({ vista: 'crea', email, next });

/** «Accedi» — con l'email gia' scritta, se c'e'. */
export const entraInAurya = (email, next) => portaAurya({ email, next });
