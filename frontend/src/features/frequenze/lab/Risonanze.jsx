/**
 * LE RISONANZE — il cercatore (LB6, 28/8/2026).
 *
 * Il Lab si chiude a cerchio: GENERA (lo sweep lento della voce A) →
 * ECCITA (l'altoparlante investe l'oggetto: bottiglia, bicchiere,
 * piastra) → ASCOLTA (il microfono sente la risposta) → MISURA (il
 * Goertzel alla frequenza CORRENTE dello sweep, letta dal motore con
 * freqOra — il numero e il suono sono la stessa verita').
 *
 * La curva eccitazione→risposta si disegna DAL VIVO mentre lo sweep
 * corre; alla fine i picchi emergono dal pavimento e diventano le
 * risonanze del TUO oggetto — salvabili nel quaderno di banco (su
 * questo dispositivo) ed esportabili come WAV per un amplificatore
 * (l'altoparlante del telefono sotto i ~200 Hz non muove niente).
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi } from './quadro';
import { goertzel } from './ritrattista';
import { trovaPicchi, tonoWav, sweepWav, leggiQuaderno,
  salvaNelQuaderno, cancellaDalQuaderno } from './cimatica';

const F_MIN_GRAFICO = 20;

const scarica = (blob, nome) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nome; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
};

export default function Risonanze({ ottieniLab, ottieniAnalisi }) {
  const [da, setDa] = useState('60');
  const [a, setA] = useState('1200');
  const [durata, setDurata] = useState('45');
  const [inCorsa, setInCorsa] = useState(false);
  const [picchi, setPicchi] = useState(null);     // null = mai corso
  const [msg, setMsg] = useState('');
  const [quaderno, setQuaderno] = useState(leggiQuaderno);
  const labRef = useRef(null);
  const telaRef = useRef(null);
  const puntiRef = useRef([]);                    // {hz, db} della corsa
  const corsaRef = useRef(false);
  const ultimaRef = useRef(0);
  const bufRef = useRef(null);
  const limitiRef = useRef([60, 1200]);

  const numero = (t, min, max, rip) => {
    const v = parseFloat(String(t).replace(',', '.'));
    return Number.isFinite(v) ? Math.min(Math.max(v, min), max) : rip;
  };

  const misura = async () => {
    const lab = ottieniLab();                     // nel gesto
    labRef.current = lab;
    if (corsaRef.current) {                       // fermare a meta'
      corsaRef.current = false; setInCorsa(false);
      lab.generatore.ferma();
      concludi();
      return;
    }
    setMsg('');
    if (!lab.orecchio.attivo()) {
      try { await lab.orecchio.apri(); } catch {
        setMsg('Per misurare la risposta serve il microfono: senza, sentirei solo me stesso.');
        return;
      }
    }
    const f0 = numero(da, 20, 18000, 60);
    const f1 = numero(a, 20, 18000, 1200);
    const sec = numero(durata, 10, 300, 45);
    setDa(String(f0)); setA(String(f1)); setDurata(String(sec));
    limitiRef.current = [Math.min(f0, f1), Math.max(f0, f1)];
    puntiRef.current = [];
    setPicchi(null);
    lab.generatore.imposta({ forma: 'sine', amp: 0.5, orecchio: 'entrambe',
      fase: 1e-7 });
    lab.generatore.imposta({ freq: f0 });
    await lab.generatore.avvia();
    lab.generatore.imposta({ freq: f1, secondi: sec });
    corsaRef.current = true; setInCorsa(true);
  };

  const concludi = () => {
    const trovati = trovaPicchi(puntiRef.current);
    setPicchi(trovati);
    setMsg(trovati.length
      ? `${trovati.length} risonanze trovate: sono i punti dove il tuo oggetto canta.`
      : 'Nessun picco netto: prova più piano con lo sweep (durata maggiore) o più vicino all’oggetto.');
  };

  /* il campionatore + il pittore: in coda al giro del banco */
  useEffect(() => iscrivi(() => {
    const lab = labRef.current;
    const tela = telaRef.current;
    if (!tela) return;

    /* campiona (10 volte al secondo) mentre la corsa e' viva */
    if (lab && corsaRef.current) {
      const s = lab.generatore.stato();
      const ora = performance.now();
      if (ora - ultimaRef.current >= 100) {
        ultimaRef.current = ora;
        const analisi = ottieniAnalisi();
        if (analisi) {
          const N = analisi.analyser.fftSize;
          if (!bufRef.current || bufRef.current.length !== N) {
            bufRef.current = new Float32Array(N);
          }
          analisi.tempo(bufRef.current);
          const sr = analisi.analyser.context.sampleRate;
          const amp = goertzel(bufRef.current, 0, Math.min(N, 4096), sr, s.freq);
          puntiRef.current.push({ hz: s.freq,
            db: 20 * Math.log10(Math.max(amp, 1e-7)) });
        }
        if (!s.corsa) {                            // la rampa e' finita
          corsaRef.current = false; setInCorsa(false);
          lab.generatore.ferma();
          concludi();
        }
      }
    }

    /* il disegno della curva */
    const dpr = window.devicePixelRatio || 1;
    const W = Math.round(tela.clientWidth * dpr);
    const H = Math.round(tela.clientHeight * dpr);
    if (!W || !H) return;
    if (tela.width !== W || tela.height !== H) { tela.width = W; tela.height = H; }
    const c2d = tela.getContext('2d');
    const st = getComputedStyle(tela);
    const linea = st.getPropertyValue('--line-soft').trim() || '#1B2E32';
    const acqua = st.getPropertyValue('--water').trim() || '#66B79C';
    const oro = st.getPropertyValue('--lamp').trim() || '#C9B37E';
    const nota = st.getPropertyValue('--dimmer').trim() || '#86A0A4';
    c2d.clearRect(0, 0, W, H);
    const [l0, l1] = limitiRef.current;
    const lo = Math.log10(Math.max(F_MIN_GRAFICO, l0)), hi = Math.log10(l1);
    const xDaHz = (hz) => ((Math.log10(hz) - lo) / (hi - lo || 1)) * W;
    c2d.strokeStyle = linea; c2d.lineWidth = 1;
    c2d.beginPath();
    for (let q = 1; q < 4; q++) {
      const y = (H * q) / 4;
      c2d.moveTo(0, y); c2d.lineTo(W, y);
    }
    c2d.stroke();
    const punti = puntiRef.current;
    if (punti.length > 1) {
      const dbs = punti.map((p) => p.db);
      const dMin = Math.min(...dbs) - 2, dMax = Math.max(...dbs) + 2;
      const yDaDb = (v) => H - ((v - dMin) / (dMax - dMin || 1)) * H * 0.92 - H * 0.04;
      c2d.strokeStyle = acqua;
      c2d.lineWidth = Math.max(1.25, 1.25 * dpr);
      c2d.lineJoin = 'round';
      c2d.shadowBlur = 4 * dpr; c2d.shadowColor = acqua;
      c2d.beginPath();
      punti.forEach((p, i) => {
        const x = xDaHz(p.hz), y = yDaDb(p.db);
        if (i === 0) c2d.moveTo(x, y); else c2d.lineTo(x, y);
      });
      c2d.stroke();
      c2d.shadowBlur = 0;
      /* i picchi trovati, in oro con la quota */
      (picchi || []).forEach((p) => {
        const x = xDaHz(p.hz);
        c2d.strokeStyle = oro;
        c2d.beginPath(); c2d.moveTo(x, 6 * dpr); c2d.lineTo(x, H); c2d.stroke();
        c2d.fillStyle = oro;
        c2d.font = `${Math.round(10 * dpr)}px ui-monospace, Menlo, monospace`;
        c2d.textAlign = x > W - 50 * dpr ? 'right' : 'left';
        c2d.fillText(`${String(p.hz).replace('.', ',')}`,
          x + (x > W - 50 * dpr ? -4 : 4) * dpr, 14 * dpr);
      });
    } else {
      c2d.fillStyle = nota;
      c2d.font = `${Math.round(10 * dpr)}px ui-monospace, Menlo, monospace`;
      c2d.textAlign = 'center';
      c2d.fillText('la curva eccitazione → risposta si disegna qui, dal vivo',
        W / 2, H / 2);
    }
  }), [ottieniAnalisi, picchi]);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => {
    if (corsaRef.current) labRef.current?.generatore.ferma();
  }, []);

  const salva = () => {
    if (!picchi || !picchi.length) return;
    const voce = {
      quando: new Date().toISOString().slice(0, 16).replace('T', ' '),
      da: limitiRef.current[0], a: limitiRef.current[1],
      risonanze: picchi.map((p) => p.hz),
    };
    if (salvaNelQuaderno(voce)) {
      setQuaderno(leggiQuaderno());
      setMsg('Salvato nel quaderno di banco (resta su questo dispositivo).');
    } else setMsg('Quaderno non disponibile su questo browser.');
  };

  return (
    <section className="lab-card lab-risonanze" data-testid="lab-risonanze">
      <div className="lab-chead">
        <h2>Le Risonanze</h2>
        <span className="lab-cnote">genera → eccita → ascolta → misura: il cerchio del banco</span>
      </div>

      <div className="lab-sweep-campi">
        <label>Da
          <input value={da} inputMode="decimal" data-testid="lab-ris-da"
            disabled={inCorsa} onChange={(e) => setDa(e.target.value)} />
          <i>Hz</i>
        </label>
        <label>A
          <input value={a} inputMode="decimal" data-testid="lab-ris-a"
            disabled={inCorsa} onChange={(e) => setA(e.target.value)} />
          <i>Hz</i>
        </label>
        <label>Durata
          <input value={durata} inputMode="decimal" data-testid="lab-ris-durata"
            disabled={inCorsa} onChange={(e) => setDurata(e.target.value)} />
          <i>s</i>
        </label>
        <button type="button" className={'lab-play' + (inCorsa ? ' fermo' : '')}
          data-testid="lab-ris-misura" onClick={misura}>
          {inCorsa ? '■ Ferma la misura' : '◉ Misura le risonanze'}
        </button>
      </div>
      <p className="lab-volume">
        Metti l&rsquo;oggetto (bottiglia, bicchiere, piastra) vicino
        all&rsquo;altoparlante e al microfono. Lo sweep lo interroga piano:
        dove la curva fa un picco, l&rsquo;oggetto canta.
      </p>
      {msg && <p className="lab-volume" aria-live="polite" data-testid="lab-ris-msg">{msg}</p>}

      <canvas ref={telaRef} className="lab-tela lab-ris-tela" role="img"
        aria-label="Curva eccitazione-risposta con le risonanze trovate" />

      {picchi && picchi.length > 0 && (
        <div className="lab-ris-esito" data-testid="lab-ris-esito">
          {picchi.map((p) => (
            <span key={p.hz} className="lab-ris-picco">
              <b>{String(p.hz).replace('.', ',')} Hz</b> (+{String(p.db).replace('.', ',')} dB)
              <button type="button" className="chip" title="Scarica 30 s di tono a questa frequenza (WAV per un ampli)"
                onClick={async () => scarica(await tonoWav(p.hz, 30), `tono-${p.hz}hz.wav`)}>
                ⤓ tono
              </button>
            </span>
          ))}
          <button type="button" className="lab-freeze" data-testid="lab-ris-salva"
            onClick={salva}>Salva nel quaderno</button>
        </div>
      )}

      <div className="lab-fonderia-gesti">
        <button type="button" className="lab-freeze" data-testid="lab-ris-wav-sweep"
          onClick={async () => scarica(
            await sweepWav(numero(da, 20, 18000, 60), numero(a, 20, 18000, 1200),
              numero(durata, 10, 300, 45)),
            'sweep.wav')}>
          ⤓ WAV dello sweep
        </button>
        <span className="lab-cnote">per amplificatori e attuatori esterni —
          sotto i 200 Hz l&rsquo;altoparlante del telefono non muove niente</span>
      </div>

      {quaderno.length > 0 && (
        <div className="lab-quaderno" data-testid="lab-quaderno">
          <h3>Il quaderno di banco</h3>
          {quaderno.map((v, i) => (
            <div key={`${v.quando}-${i}`} className="lab-quaderno-riga">
              <span>{v.quando} · {v.da}→{v.a} Hz</span>
              <b>{(v.risonanze || []).map((hz) => String(hz).replace('.', ',')).join(' · ')} Hz</b>
              <button type="button" className="ghost" title="Elimina"
                onClick={() => setQuaderno(cancellaDalQuaderno(i))}>×</button>
            </div>
          ))}
          <p className="lab-cnote">gli esperimenti restano su questo dispositivo</p>
        </div>
      )}

      {/* la didascalia — ogni modulo si racconta (regola LB) */}
      <p className="lab-didascalia" data-testid="lab-ris-didascalia">
        <b>Cimatica, primo passo.</b> Ogni oggetto risuona solo sulle
        sue frequenze: lo sweep gliele chiede tutte, il microfono
        ascolta quando risponde. Trovata la risonanza, tienila addosso
        all&rsquo;oggetto col tono fermo (o col WAV su un ampli) e GUARDA:
        riso sulla lattina, acqua nel bicchiere — le figure che si
        formano sono i suoi modi, resi visibili.
      </p>
    </section>
  );
}
