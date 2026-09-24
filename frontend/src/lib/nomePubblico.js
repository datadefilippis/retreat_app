/**
 * Identità pubblica (P1, 24/9/2026) — specchio di backend/services/nome_pubblico.py.
 * STESSA regola: persona + marchio diversi → «Valentina · Brillare»; solo
 * persona → «Valentina»; solo marchio → il marchio com'è; marchio che
 * contiene già la persona → il marchio. Serve all'anteprima dell'editor;
 * il pubblico riceve `name` già composto dal server.
 */
export const SEPARATORE = ' · ';
export const NOME_PERSONA_MAX = 80;

const pulito = (s) => String(s || '').split(/\s+/).filter(Boolean).join(' ').trim();

export function contienePersona(marchio, persona) {
  const m = pulito(marchio).toLowerCase();
  const parti = pulito(persona).toLowerCase().split(' ').filter((p) => p.length > 2);
  // basta UNA parola del nome dentro il marchio: niente «Valentina Rossi · Valentina - Brillare»
  return parti.length > 0 && parti.some((p) => m.includes(p));
}

export function nomePubblico(persona, marchio) {
  const p = pulito(persona).slice(0, NOME_PERSONA_MAX);
  const m = pulito(marchio);
  if (p && m && p.toLowerCase() !== m.toLowerCase() && !contienePersona(m, p)) return `${p}${SEPARATORE}${m}`;
  if (p && m) return m;   // stessa stringa, o marchio che contiene già la persona
  return p || m;
}

/** Il nome ha una parola sola? (avviso morbido alla registrazione) */
export const unaParolaSola = (nome) => pulito(nome).split(' ').length < 2;
