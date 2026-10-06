/**
 * Lo stato dell'Accademia per gli operatori (AC0, 6/10/2026): come i
 * Prodotti, il modulo esce in ANTEPRIMA. La scheda in Strumenti si vede,
 * leggermente oscurata, e dice cosa arriva; le pagine /accademia/* (AC1)
 * resteranno chiuse finche' il founder non da' il via. Lo sblocco e' `true`
 * + un giro frontend. I piloti vedono tutto aperto per provare in locale.
 */
export const ACCADEMIA_UI_PRONTA = false;

export const PILOTI_ACCADEMIA = ['admin@demo.com'];

export function accademiaAperta(user) {
  if (ACCADEMIA_UI_PRONTA) return true;
  const email = String(user?.email || '').toLowerCase();
  return PILOTI_ACCADEMIA.includes(email);
}
