/**
 * FA7 — lo slug di una scheda della biblioteca: UNA regola, due
 * padroni (le rotte del frontend e l'export per la shell SSR).
 * Stabile per costruzione: cambiare questa funzione cambia gli URL
 * pubblici — non si tocca senza una migrazione di redirect.
 */
export function sluggifica(titolo) {
  return String(titolo || '')
    .toLowerCase()
    .replace(/à/g, 'a').replace(/è|é/g, 'e').replace(/ì/g, 'i')
    .replace(/ò/g, 'o').replace(/ù/g, 'u')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
