/**
 * L'ANDAMENTO — il vissuto disegnato (M5, 26/8/2026).
 *
 * La domanda dell'operatore: «con questa persona, sta servendo?». La
 * risposta onesta è il vissuto dichiarato, sessione dopo sessione:
 * per ogni sessione chiusa, un segmento verticale dal PRIMA al DOPO —
 * il delta si vede, non si racconta. La linea sottile unisce i DOPO:
 * l'andamento nel tempo.
 *
 * COSA NON FA, di proposito: non disegna le sessioni senza vissuto
 * (niente punti inventati), non interpola i buchi, non calcola medie
 * «di benessere» — è un grafico di dichiarazioni soggettive e la
 * geometria non gli aggiunge significato.
 *
 * PURO E SENZA IMPORT, come spartito.js: stessa disciplina, stessa
 * testabilità in Node.
 */

/**
 * @param sessioni  sessioni CHIUSE, in ordine cronologico ASCENDENTE
 * @returns {{ w, h, segmenti, linea, righe }}
 *   segmenti  [{x, y0, y1, verso}] — da pre a post (verso: 'su'|'giu'|'pari'),
 *             solo dove ci sono ENTRAMBI
 *   linea     [[x, y]] — i post (o il pre, se è l'unico dato), per la
 *             linea dell'andamento
 *   righe     [{y, valore}] — la scala 1..10, per gli assi
 */
export function andamento(sessioni, { w = 600, h = 90, margine = 12 } = {}) {
  const conVissuto = (sessioni || []).filter(
    (s) => s.feedback_pre != null || s.feedback_post != null);
  const n = conVissuto.length;
  const X = (i) => (n <= 1 ? w / 2 : margine + ((w - margine * 2) * i) / (n - 1));
  const Y = (v) => h - margine - ((h - margine * 2) * (v - 1)) / 9;

  const segmenti = [];
  const linea = [];
  conVissuto.forEach((s, i) => {
    const x = r2(X(i));
    const pre = s.feedback_pre, post = s.feedback_post;
    if (pre != null && post != null) {
      segmenti.push({
        x, y0: r2(Y(pre)), y1: r2(Y(post)),
        verso: post > pre ? 'su' : post < pre ? 'giu' : 'pari',
      });
    }
    const punto = post != null ? post : pre;
    linea.push([x, r2(Y(punto))]);
  });

  const righe = [1, 5, 10].map((v) => ({ y: r2(Y(v)), valore: v }));
  return { w, h, segmenti, linea, righe };
}

/**
 * La sintesi in parole: totali onesti e posizione nei percorsi.
 * @returns {{ totale, completate, interrotte, perse, percorsi:
 *             [{id, titolo, fatte, totale}] }}
 */
export function sintesi(sessioni) {
  const chiuse = (sessioni || []).filter((s) => s.stato !== 'in_corso');
  const conta = (stato) => chiuse.filter((s) => s.stato === stato).length;
  const perPercorso = {};
  chiuse.forEach((s) => {
    if (!s.percorso) return;
    const p = perPercorso[s.percorso.id]
      || (perPercorso[s.percorso.id] = {
        id: s.percorso.id, titolo: s.percorso.titolo,
        totale: s.percorso.totale, tappe: new Set(),
      });
    /* una tappa conta solo se COMPLETATA: il percorso è una
       progressione, non una collezione di tentativi */
    if (s.stato === 'completata') p.tappe.add(s.percorso.tappa);
  });
  return {
    totale: chiuse.length,
    completate: conta('completata'),
    interrotte: conta('interrotta'),
    perse: conta('persa'),
    percorsi: Object.values(perPercorso).map((p) => ({
      id: p.id, titolo: p.titolo, fatte: p.tappe.size, totale: p.totale,
    })),
  };
}

const r2 = (x) => Math.round(x * 100) / 100;
