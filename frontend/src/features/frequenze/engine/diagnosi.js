/**
 * Il pannello di DIAGNOSI del suono (22/8/2026) — ?diag=1
 *
 * Nato da un silenzio che non si lasciava spiegare: su iPhone tutti e
 * quattro i canali audio della pagina di prova suonavano, ma la
 * sessione vera restava muta. A quel punto le ipotesi da scrivania
 * sono finite: serve VEDERE il flusso reale sul dispositivo reale.
 *
 * Si aggancia alla pagina viva (Crea, meditazione) e mostra a schermo,
 * due volte al secondo:
 * - lo stato del contesto e la sua STORIA (ogni statechange, con l'ora);
 * - il currentTime: se non avanza, il contesto e' fermo comunque;
 * - il LIVELLO misurato dall'analizzatore: >0 = il grafo PRODUCE suono
 *   (se non lo senti, muore all'uscita); 0 = il grafo tace (il problema
 *   e' a monte);
 * - il ponte: in play? muto? con lo stream?
 * - gli errori JS e le promesse rifiutate, che su telefono nessuno vede.
 *
 * «Copia» mette tutto negli appunti, da incollare in chat. Il pannello
 * esiste SOLO con ?diag=1 nell'URL: nessun costo per gli utenti.
 */
export function diagnosiAttiva() {
  try {
    return typeof window !== 'undefined'
      && new URLSearchParams(window.location.search).get('diag') === '1';
  } catch { return false; }
}

export function avviaDiagnosi({ ctx, analyser, ponte, etichetta = '' }) {
  if (!diagnosiAttiva() || !ctx) return null;
  if (ctx._fqzDiag) { ctx._fqzDiag.aggiorna({ analyser, ponte }); return ctx._fqzDiag; }

  const eventi = [];
  const ora = () => new Date().toISOString().slice(11, 23);
  const nota = (t) => { eventi.push(ora() + ' ' + t); if (eventi.length > 40) eventi.shift(); };
  nota('diagnosi avviata (' + etichetta + '), stato=' + ctx.state
    + ', sr=' + ctx.sampleRate);

  ctx.addEventListener('statechange', () => nota('statechange → ' + ctx.state));
  window.addEventListener('error', (e) => nota('ERRORE: ' + (e.message || e.type)));
  window.addEventListener('unhandledrejection',
    (e) => nota('PROMESSA RIFIUTATA: ' + (e.reason && (e.reason.message || e.reason))));

  const box = document.createElement('div');
  box.setAttribute('style',
    'position:fixed;left:8px;right:8px;bottom:8px;z-index:99999;'
    + 'background:rgba(5,10,12,.94);color:#cfe;border:1px solid #2C5259;'
    + 'border-radius:10px;padding:10px;font:11px/1.5 ui-monospace,Menlo,monospace;'
    + 'max-height:45vh;overflow:auto;white-space:pre-wrap');
  const testo = document.createElement('div');
  const copia = document.createElement('button');
  copia.textContent = '📋 copia il rapporto';
  copia.setAttribute('style',
    'margin-top:6px;padding:8px 12px;border-radius:8px;border:0;'
    + 'background:#7EC1BA;color:#08201D;font-weight:700');
  box.appendChild(testo); box.appendChild(copia);
  document.body.appendChild(box);

  let riferimenti = { analyser, ponte };
  const buf = new Uint8Array(256);
  let ultimoCT = -1;

  function quadro() {
    const a = riferimenti.analyser;
    let livello = 'n/d (analizzatore assente)';
    if (a) {
      try {
        a.getByteFrequencyData(buf.subarray(0, Math.min(buf.length, a.frequencyBinCount)));
        let m = 0;
        for (let i = 0; i < Math.min(buf.length, a.frequencyBinCount); i++) {
          if (buf[i] > m) m = buf[i];
        }
        livello = m;
      } catch (e) { livello = 'errore: ' + e.message; }
    }
    const p = riferimenti.ponte || ctx._fqzPonte;
    const ct = ctx.currentTime;
    const avanzaCT = ct > ultimoCT ? 'AVANZA' : 'FERMO';
    ultimoCT = ct;
    return {
      dove: etichetta,
      stato: ctx.state,
      sampleRate: ctx.sampleRate,
      currentTime: +ct.toFixed(2) + ' (' + avanzaCT + ')',
      livelloGrafo: livello,
      ponte: p ? {
        inPlay: !p.el.paused, muto: p.el.muted, volume: p.el.volume,
        conStream: !!p.el.srcObject, readyState: p.el.readyState,
      } : 'assente',
      audioSession: (navigator.audioSession && navigator.audioSession.type) || 'API assente',
      eventi: eventi.slice(-14),
    };
  }

  const timer = setInterval(() => {
    try { testo.textContent = JSON.stringify(quadro(), null, 1); } catch (e) {
      testo.textContent = 'diagnosi rotta: ' + e.message;
    }
  }, 500);

  copia.onclick = () => {
    const r = JSON.stringify({ ua: navigator.userAgent, ...quadro(), eventi }, null, 1);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(r).then(
        () => { copia.textContent = '✓ copiato — incolla in chat'; },
        () => { testo.textContent = r; });
    } else { testo.textContent = r; }
  };

  const manico = {
    nota,
    aggiorna(nuovi) { riferimenti = { ...riferimenti, ...nuovi }; },
    spegni() { clearInterval(timer); box.remove(); },
  };
  ctx._fqzDiag = manico;
  return manico;
}
