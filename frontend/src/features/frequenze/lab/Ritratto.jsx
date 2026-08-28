/**
 * IL RITRATTO — il pannello (LB3+LB4, 27-28/8/2026).
 *
 * LB3: registri 6 secondi di cio' che il banco sta guardando (il
 * microfono se l'orecchio e' aperto — la campana, il bicchiere —
 * altrimenti le sorgenti del banco stesso) e l'analisi OFFLINE
 * (lab/ritrattista.js) scrive la carta d'identita' del suono:
 * parziali, rapporti, doppietti, tempi di vita.
 *
 * LB4: dal ritratto la FONDERIA rifonde il suono (sintesi additiva,
 * lab/fonderia.js) — e qui vive il laboratorio vero: l'A/B con
 * l'originale registrato, il colpo e il tenuto, i parziali che si
 * spengono uno a uno sentendo subito la differenza, il respiro che
 * allunga le vite. Il WAV si porta a casa (e' anche l'uscita per gli
 * ampli della cimatica); il system admin puo' consegnare la campana
 * alla libreria suoni (categoria Campane) — il ponte col prodotto.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { frequenciesAPI } from '../../../api/frequencies';
import { analizza } from './ritrattista';
import { campana, renderizzaWav } from './fonderia';

const SECONDI = 6;

export default function Ritratto({ ottieniLab }) {
  const { user } = useAuth();
  const [fase, setFase] = useState('pronto');     // pronto | registro | analizzo
  const [conto, setConto] = useState(0);
  const [esito, setEsito] = useState(null);       // il ritratto, o null
  const [niente, setNiente] = useState(false);    // analisi senza esito
  const [spenti, setSpenti] = useState([]);       // parziali esclusi (hz)
  const [respiro, setRespiro] = useState(1);      // moltiplicatore delle vite
  const [inSuono, setInSuono] = useState(null);   // 'orig'|'colpo'|'tenuto'
  const [msg, setMsg] = useState('');
  const labRef = useRef(null);
  const contoRef = useRef(null);
  const presaRef = useRef(null);                  // i campioni registrati
  const srRef = useRef(44100);
  const vivoRef = useRef(null);                   // {ferma} di cio' che suona

  const zittisci = () => {
    if (vivoRef.current) { vivoRef.current.ferma(); vivoRef.current = null; }
    setInSuono(null);
  };
  useEffect(() => () => { clearInterval(contoRef.current); zittisci(); },
    []);   // eslint-disable-line react-hooks/exhaustive-deps

  const registra = async () => {
    const lab = ottieniLab();                     // nel gesto: iOS lo esige
    labRef.current = lab;
    try { await lab.ctx.resume(); } catch { /* gia' attivo */ }
    zittisci();
    setEsito(null); setNiente(false); setSpenti([]); setMsg('');
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
      presaRef.current = campioni; srRef.current = sampleRate;
      setEsito(r); setNiente(!r);
      setFase('pronto');
    } catch {
      clearInterval(contoRef.current);
      setNiente(true); setFase('pronto');
    }
  };

  /* ── LB4: l'A/B e la rifusione ─────────────────────────────── */
  const suonaOriginale = async () => {
    const lab = labRef.current; if (!lab || !presaRef.current) return;
    zittisci();
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    const buf = lab.ctx.createBuffer(1, presaRef.current.length, srRef.current);
    buf.copyToChannel(presaRef.current, 0);
    const src = lab.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(lab.ingresso);
    src.onended = () => setInSuono((cosa) => (cosa === 'orig' ? null : cosa));
    src.start();
    vivoRef.current = { ferma: () => { try { src.stop(); } catch { /* gia' */ } } };
    setInSuono('orig');
  };

  const suonaRifusa = async (modo) => {
    const lab = labRef.current; if (!lab || !esito) return;
    zittisci();
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    const esec = campana(lab.ctx, lab.ingresso, esito, { modo, respiro, spenti });
    if (!esec) return;
    vivoRef.current = esec;
    setInSuono(modo);
    if (modo === 'colpo') {
      setTimeout(() => setInSuono((cosa) => (cosa === 'colpo' ? null : cosa)),
        esec.durataSec * 1000);
    }
  };

  const scaricaWav = async () => {
    if (!esito) return;
    setMsg('Preparo il WAV…');
    const blob = await renderizzaWav(esito,
      { modo: 'tenuto', secondi: 10, respiro, spenti });
    if (!blob) { setMsg('Niente da rendere.'); return; }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campana-${Math.round(esito.fondamentaleHz)}hz.wav`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    setMsg('WAV pronto: 10 s di tenuto, per ascolto o per un ampli.');
  };

  const inLibreria = async () => {
    if (!esito) return;
    setMsg('Rifondo e consegno alla libreria…');
    try {
      const blob = await renderizzaWav(esito,
        { modo: 'tenuto', secondi: 30, respiro, spenti });
      await frequenciesAPI.uploadSound({
        file: new File([blob], `campana-${Math.round(esito.fondamentaleHz)}hz.wav`,
          { type: 'audio/wav' }),
        title: `Campana rifatta · ${Math.round(esito.fondamentaleHz)} Hz`,
        category: 'campane',
        durationSec: 30,
        licenseNote: 'rifusa nel Lab dal ritratto (LB4)',
      });
      setMsg('Consegnata: la trovi in Crea, categoria Campane.');
    } catch {
      setMsg('Consegna non riuscita.');
    }
  };

  const alternaParziale = (hz) => setSpenti((v) => (
    v.includes(hz) ? v.filter((x) => x !== hz) : [...v, hz]));

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
                  <th title="Il parziale suona nella rifusione?">on</th>
                  <th>Hz</th><th>forza</th><th>rapporto</th>
                  <th>scarto</th><th>vita (T60)</th><th>doppietto</th>
                </tr>
              </thead>
              <tbody>
                {esito.parziali.map((p) => (
                  <tr key={p.hz}
                    className={(p.hz === esito.fondamentaleHz ? 'fondo' : '')
                      + (spenti.includes(p.hz) ? ' spento' : '')}>
                    <td>
                      <input type="checkbox" checked={!spenti.includes(p.hz)}
                        aria-label={`Parziale ${p.hz} Hz nella rifusione`}
                        onChange={() => alternaParziale(p.hz)} />
                    </td>
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

          {/* ── LB4: LA CAMPANA RIFATTA ── */}
          <div className="lab-fonderia" data-testid="lab-fonderia">
            <h3>La campana rifatta</h3>
            <div className="lab-fonderia-gesti">
              <button type="button" className={'lab-freeze' + (inSuono === 'orig' ? ' fermo' : '')}
                data-testid="lab-ab-originale"
                onClick={() => (inSuono === 'orig' ? zittisci() : suonaOriginale())}>
                {inSuono === 'orig' ? '■ Originale' : '▶ Originale'}
              </button>
              <button type="button" className={'lab-freeze' + (inSuono === 'colpo' ? ' fermo' : '')}
                data-testid="lab-ab-colpo"
                onClick={() => (inSuono === 'colpo' ? zittisci() : suonaRifusa('colpo'))}>
                {inSuono === 'colpo' ? '■ Colpo' : '▶ Colpo'}
              </button>
              <button type="button" className={'lab-freeze' + (inSuono === 'tenuto' ? ' fermo' : '')}
                data-testid="lab-ab-tenuto"
                onClick={() => (inSuono === 'tenuto' ? zittisci() : suonaRifusa('tenuto'))}>
                {inSuono === 'tenuto' ? '■ Tenuto' : '▶ Tenuto'}
              </button>
              <label className="lab-par lab-respiro">
                <span>Respiro <b>×{String(respiro).replace('.', ',')}</b></span>
                <input type="range" className="lab-slider" min="0.25" max="4"
                  step="0.25" value={respiro}
                  onChange={(e) => setRespiro(+e.target.value)} />
              </label>
            </div>
            <div className="lab-fonderia-gesti">
              <button type="button" className="lab-freeze"
                data-testid="lab-fonderia-wav" onClick={scaricaWav}>
                ⤓ WAV (tenuto, 10 s)
              </button>
              {user?.role === 'system_admin' && (
                <button type="button" className="lab-freeze"
                  data-testid="lab-fonderia-libreria" onClick={inLibreria}>
                  → Nella libreria (Campane)
                </button>
              )}
            </div>
            {msg && <p className="lab-volume" aria-live="polite">{msg}</p>}
            <p className="lab-didascalia" data-testid="lab-fonderia-didascalia">
              <b>L&rsquo;A/B è il laboratorio.</b> Originale e rifusione,
              stesso orecchio: la rifusione è la SOMMA dei modi in
              tabella — spegnine uno e risenti; se manca qualcosa, è
              ciò che il ritratto non ha catturato (l&rsquo;attacco
              percussivo, il rumore del battente). Il <b>tenuto</b> fa
              cantare la campana come strofinata — è anche il WAV per
              gli esperimenti di cimatica.
            </p>
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
