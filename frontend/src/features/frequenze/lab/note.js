/**
 * LE NOTE (LB2, 27/8/2026) — una sola tabella per tutto il banco.
 *
 * Nata nel Generatore (STEP 1), estratta quando l'Orecchio ha avuto
 * bisogno della stessa risposta: «che nota e' questo Hz?». Nomencl.
 * italiana — il ponte col mondo musicale che il lettore della
 * biblioteca gia' conosce.
 */

export const NOTE = ['Do', 'Do♯', 'Re', 'Re♯', 'Mi', 'Fa', 'Fa♯', 'Sol', 'Sol♯', 'La', 'La♯', 'Si'];

export function notaVicina(hz) {
  if (!hz || hz <= 0) return null;
  const n = Math.round(12 * Math.log2(hz / 440));           // semitoni da La4
  const giusta = 440 * Math.pow(2, n / 12);
  const idx = ((n % 12) + 12 + 9) % 12;                     // La4 = indice 9
  const ottava = 4 + Math.floor((n + 9) / 12);
  const cents = Math.round(1200 * Math.log2(hz / giusta));
  return { nome: `${NOTE[idx]}${ottava}`, giusta, cents };
}
