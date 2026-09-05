/**
 * LE MERAVIGLIE — il pannello (LB5, 28/8/2026).
 *
 * Il catalogo delle onde belle E oneste: ogni riga e' un esperimento
 * con il suo cartellino (A = documentato, C = tradizione), una
 * suona alla volta, e la didascalia si apre con l'esperimento —
 * perche' la meraviglia senza spiegazione e' marketing, e la
 * spiegazione senza meraviglia e' un manuale.
 *
 * React e' solo la mano: i fenomeni vivono in lab/fenomeni.js.
 */
import React, { useEffect, useRef, useState } from 'react';
import { MERAVIGLIE } from './fenomeni';

const FAMIGLIE = [
  ['spazio', 'Lo spazio'],
  ['geometria', 'La geometria'],
  ['illusione', 'L’illusione'],
  ['banco', 'Il banco classico'],
];
const CARTELLINI = {
  A: ['A', 'Fenomeno documentato dalla fisica e dalla psicoacustica'],
  C: ['C', 'Valore simbolico della tradizione, il fenomeno resta vero'],
};

export default function Meraviglie({ ottieniLab }) {
  const [viva, setViva] = useState(null);         // id della meraviglia attiva
  const labRef = useRef(null);
  const vivoRef = useRef(null);                   // {ferma} in corso

  const zittisci = () => {
    if (vivoRef.current) { vivoRef.current.ferma(); vivoRef.current = null; }
    setViva(null);
    /* il ronzio del 5/9: anche le meraviglie sono ospiti del banco —
       quando tacciono il ponte va rilasciato, o l'<audio> resta in play
       su uno stream muto (loop dell'ultimo buffer su iOS) */
    try { labRef.current?.rilasciaSeMuto(); } catch { /* via */ }
  };
  useEffect(() => () => {
    if (vivoRef.current) vivoRef.current.ferma();
  }, []);

  const alterna = async (m) => {
    if (viva === m.id) { zittisci(); return; }
    zittisci();
    const lab = ottieniLab();                     // nel gesto: iOS lo esige
    labRef.current = lab;
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    vivoRef.current = m.avvia(lab);
    setViva(m.id);
  };

  return (
    <section className="lab-card lab-meraviglie" data-testid="lab-meraviglie">
      <div className="lab-chead">
        <h2>Le Meraviglie</h2>
        <span className="lab-cnote">fenomeni veri, mostrati dal lato giusto, una alla volta</span>
      </div>

      {FAMIGLIE.map(([fam, titolo]) => (
        <div key={fam} className="lab-mer-famiglia">
          <h3>{titolo}</h3>
          {MERAVIGLIE.filter((m) => m.famiglia === fam).map((m) => (
            <div key={m.id}
              className={'lab-mer' + (viva === m.id ? ' viva' : '')}
              data-testid={`lab-mer-${m.id}`}>
              <div className="lab-mer-riga">
                <button type="button"
                  className={'lab-freeze' + (viva === m.id ? ' fermo' : '')}
                  data-testid={`lab-mer-${m.id}-play`}
                  onClick={() => alterna(m)}>
                  {viva === m.id ? '■' : '▶'}
                </button>
                <div className="lab-mer-testo">
                  <b>{m.nome}</b>
                  <span>{m.riga}</span>
                </div>
                <i className={`lab-cartellino c${m.cartellino}`}
                  title={CARTELLINI[m.cartellino][1]}>
                  {CARTELLINI[m.cartellino][0]}
                </i>
              </div>
              {viva === m.id && (
                <p className="lab-didascalia" data-testid={`lab-mer-${m.id}-didascalia`}>
                  {m.didascalia}
                </p>
              )}
            </div>
          ))}
        </div>
      ))}

      <p className="lab-didascalia" data-testid="lab-mer-onesta">
        <b>Perché i cartellini.</b> Qui fuori si vendono «frequenze 3D»
        e onde miracolose. Il suono spazializzato esiste (è l&rsquo;HRTF del
        Vortice); un&rsquo;onda «tridimensionale di suo» no, un&rsquo;onda di
        pressione è un&rsquo;onda di pressione. Ogni meraviglia di questo
        catalogo è un fenomeno che puoi misurare con gli strumenti qui
        sopra: è la differenza tra stupire e mentire.
      </p>
    </section>
  );
}
