/**
 * IL RITRATTO — il pannello (LB3, 27/8/2026).
 *
 * Registri 6 secondi di cio' che il banco sta guardando (il
 * microfono se l'orecchio e' aperto — la campana, il bicchiere —
 * altrimenti le sorgenti del banco stesso) e l'analisi OFFLINE
 * (lab/ritratto.js: FFT nostra, vertice parabolico, Goertzel per gli
 * inviluppi) scrive la carta d'identita' del suono: parziali,
 * rapporti, doppietti, tempi di vita.
 *
 * Il ritratto e' DATI (JSON): si legge, si confronta, e in LB4 si
 * risintetizza. React qui e' solo la mano e la tabella.
 */
import React, { useEffect, useRef, useState } from 'react';
import { analizza } from './ritrattista';

const SECONDI = 6;

export default function Ritratto({ ottieniLab }) {
  const [fase, setFase] = useState('pronto');     // pronto | registro | analizzo
  const [conto, setConto] = useState(0);
  const [esito, setEsito] = useState(null);       // il ritratto, o null
  const [niente, setNiente] = useState(false);    // analisi senza esito
  const labRef = useRef(null);
  const contoRef = useRef(null);

  useEffect(() => () => { clearInterval(contoRef.current); }, []);

  const registra = async () => {
    const lab = ottieniLab();                     // nel gesto: iOS lo esige
    labRef.current = lab;
    try { await lab.ctx.resume(); } catch { /* gia' attivo */ }
    setEsito(null); setNiente(false);
    setFase('registro'); setConto(SECONDI);
    contoRef.current = setInterval(
      () => setConto((c) => Math.max(0, c - 1)), 1000);
    try {
      const { campioni, sampleRate } = await lab.analisi.registra(SECONDI);
      clearInterval(contoRef.current);
      setFase('analizzo');
      /* un respiro al browser prima del conto pesante */
      await new Promise((r) => setTimeout(r, 30));
      const r = analizza(campioni, sampleRate);
      setEsito(r); setNiente(!r);
      setFase('pronto');
    } catch {
      clearInterval(contoRef.current);
      setNiente(true); setFase('pronto');
    }
  };

  const micAperto = labRef.current?.orecchio.attivo();

  return (
    <section className="lab-card lab-ritratto" data-testid="lab-ritratto">
      <div className="lab-chead">
        <h2>Il Ritratto</h2>
        <span className="lab-cnote">sei secondi di suono → la carta d&rsquo;identità acustica</span>
      </div>

      <div className="lab-azione">
        <button type="button" className={'lab-play' + (fase !== 'pronto' ? ' fermo' : '')}
          data-testid="lab-ritratto-registra"
          disabled={fase !== 'pronto'} onClick={registra}>
          {fase === 'registro' ? `● Registro… ${conto}`
            : fase === 'analizzo' ? '◌ Analizzo…'
              : '● Registra e analizza'}
        </button>
        <p className="lab-volume">
          {micAperto
            ? 'Registro dal microfono: colpisci la campana (o il bicchiere) appena parte il conto.'
            : 'Registro ciò che il banco sta guardando: apri il microfono per ritrarre il mondo, o lascia le sorgenti per ritrarre una sintesi.'}
        </p>
      </div>

      {niente && (
        <p className="lab-orecchio-errore" data-testid="lab-ritratto-vuoto">
          Non ho trovato un suono da ritrarre: troppo piano, o troppo
          breve. Riprova più vicino al microfono.
        </p>
      )}

      {esito && (
        <div className="lab-ritratto-esito" data-testid="lab-ritratto-esito">
          <p className="lab-ritratto-riga">
            Fondamentale <b>{esito.fondamentaleHz} Hz</b>
            {' '}· {esito.continuo ? 'suono tenuto · analizzati' : 'coda analizzata'}
            {' '}{String(esito.codaSec).replace('.', ',')} s
            {esito.rumoreFondoDb !== null
              && ` · fondo della stanza ${esito.rumoreFondoDb} dB`}
          </p>
          <div className="lab-ritratto-scroll">
            <table className="lab-ritratto-tabella">
              <thead>
                <tr>
                  <th>Hz</th><th>forza</th><th>rapporto</th>
                  <th>scarto</th><th>vita (T60)</th><th>doppietto</th>
                </tr>
              </thead>
              <tbody>
                {esito.parziali.map((p) => (
                  <tr key={p.hz}
                    className={p.hz === esito.fondamentaleHz ? 'fondo' : undefined}>
                    <td>{p.hz}</td>
                    <td>{p.db} dB</td>
                    <td>{String(p.rapporto).replace('.', ',')}</td>
                    <td>{p.cents > 0 ? '+' : ''}{p.cents} cent</td>
                    <td>{p.t60 === null ? '—' : `${String(p.t60).replace('.', ',')} s`}</td>
                    <td>{p.doppietto
                      ? `sì · batte a ${String(p.doppietto.battito).replace('.', ',')} Hz`
                      : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="lab-ritratto-onesta">
            Le <b>frequenze</b> sono affidabili al decimo di Hz; le
            <b> ampiezze</b> sotto i 100 Hz e sopra i 15 kHz sono
            indicative — un microfono da telefono colora lo spettro.
          </p>
        </div>
      )}

      {/* la didascalia — ogni modulo si racconta (regola LB) */}
      <p className="lab-didascalia" data-testid="lab-ritratto-didascalia">
        <b>Cosa stai leggendo.</b> Ogni oggetto vibra solo sui suoi
        modi: la tabella è l&rsquo;elenco dei modi del tuo suono. Una corda
        ha rapporti quasi interi (2, 3, 4…); una campana no — e i
        <b> doppietti</b>, coppie di modi quasi coincidenti, sono lo
        «shimmer» che senti girare. La colonna <b>vita</b> dice quanto
        ogni modo resiste prima di spegnersi: gli acuti muoiono prima.
      </p>
    </section>
  );
}
