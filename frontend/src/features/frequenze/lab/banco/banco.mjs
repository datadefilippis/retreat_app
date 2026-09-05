/**
 * IL BANCO DEL RITRATTISTA (LM1, 5/9/2026) — si lancia da node, senza
 * browser:   node banco.mjs        (dalla cartella lab/banco)
 * Stampa un verdetto per segnale e esce 1 se un caso PRETESO sbaglia;
 * i casi «lm1:» sono attesi sbagliati finche' la cura non e' tarata
 * sui WAV veri, e non fanno fallire. La guardia pytest lo esegue.
 *
 * Carica il ritrattista VERO (../ritrattista.js e ../accordatore.js)
 * riscrivendo solo gli import per node (ESM senza estensione).
 */
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { casi, ATTESO, sr } from './segnali.mjs';

const qui = dirname(fileURLToPath(import.meta.url));
const tmp = mkdtempSync(join(tmpdir(), 'fqz-banco-'));
writeFileSync(join(tmp, 'accordatore.mjs'), readFileSync(join(qui, '..', 'accordatore.js'), 'utf8'));
writeFileSync(join(tmp, 'ritrattista.mjs'),
  readFileSync(join(qui, '..', 'ritrattista.js'), 'utf8').replace("'./accordatore'", "'./accordatore.mjs'"));
const { analizza } = await import(pathToFileURL(join(tmp, 'ritrattista.mjs')).href);

let pretesiOk = 0, pretesi = 0, attesiLm1 = 0, sorprese = [];
for (const [nome, x] of Object.entries(casi())) {
  const r = analizza(x, sr);
  const nat = r ? r.natura : 'null';
  const atteso = ATTESO[nome];
  const lm1 = atteso.startsWith('lm1:');
  const bene = atteso.replace('lm1:', '').split('|').includes(nat);
  const riga = nome.padEnd(34) + ' → ' + nat.padEnd(9)
    + (r && r.fondamentaleHz ? ' f0=' + r.fondamentaleHz : '')
    + (r && r.f0minHz ? ` ${r.f0minHz}→${r.f0maxHz}` : '')
    + (r && r.clipping ? ' CLIP' : '') + (r && r.percussivo ? ' percussivo' : '');
  if (lm1) { attesiLm1++; console.log((bene ? '  ok* ' : ' lm1  ') + riga); if (bene) sorprese.push(nome); }
  else { pretesi++; if (bene) pretesiOk++; console.log((bene ? '  ok  ' : ' FAIL ') + riga); }
}
console.log(`\n${pretesiOk}/${pretesi} pretesi giusti, ${attesiLm1} casi in attesa della cura LM1`
  + (sorprese.length ? ` (gia' giusti: ${sorprese.join(', ')})` : ''));
process.exit(pretesiOk === pretesi ? 0 : 1);
