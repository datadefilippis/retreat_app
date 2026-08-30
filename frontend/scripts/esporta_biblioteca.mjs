/**
 * FA7 (piano FARO, 30/8/2026) — l'esportatore della biblioteca.
 *
 * La fonte del contenuto resta content/biblioteca.js (frontend, la
 * casa editoriale); il backend pero' deve SERVIRE quel testo ai
 * crawler (shell SSR) e non puo' leggere il frontend in produzione.
 * Questo script la esporta in backend/config/biblioteca_seo.json
 * (COMMITTATO): slug stabile → scheda completa.
 *
 * Quando si aggiunge una scheda: rilanciare
 *   node scripts/esporta_biblioteca.mjs
 * La guardia di parita' (test_faro_seo.py) fa rosso finche' non lo fai.
 */
import { BIB } from '../src/features/frequenze/content/biblioteca.js';
import { sluggifica } from '../src/features/frequenze/content/slugScheda.js';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const qui = dirname(fileURLToPath(import.meta.url));
const out = {};
for (const [categoria, schede] of Object.entries(BIB)) {
  for (const s of schede) {
    const slug = sluggifica(s.t);
    if (out[slug]) throw new Error(`slug doppio: ${slug}`);
    out[slug] = { t: s.t, hz: s.hz, g: s.g, uso: s.uso, body: s.body,
      full: s.full, categoria, group: s.group || null };
  }
}
const dest = join(qui, '..', '..', 'backend', 'config', 'biblioteca_seo.json');
writeFileSync(dest, JSON.stringify(out, null, 1));
console.log(`esportate ${Object.keys(out).length} schede → ${dest}`);
