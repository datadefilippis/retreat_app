/**
 * LE RISONANZE — il cercatore (LB6; ciclo RZ 28/8/2026).
 *
 * Il caso della moneta del founder ha riscritto il pannello: metteva
 * una moneta sull'altoparlante, fermava lo sweep quando la vedeva
 * danzare — e il pannello buttava via il momento. Ora l'esperienza
 * e' un CICLO, non una corsa:
 *
 *   prepara → interroga (sweep) → TROVA (con la curva del microfono,
 *   o CON GLI OCCHI) → il fermo cattura la frequenza e il tono resta
 *   IN MANO → aggiusti fine, osservi l'oggetto → salvi nel quaderno
 *   → risuoni quando vuoi (dai picchi, dal quaderno).
 *
 * La via «a occhio» e' un metodo dichiarato: senza microfono lo
 * sweep parte lo stesso, il numerone dice dove sei, e i tuoi occhi
 * sono lo strumento. Il fermo dello sweep NON spegne il suono: la
 * nota resta esattamente dove l'hai fermata (e' il pattern del
 * Generatore: interrompere la rampa = tenere la nota).
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi } from './quadro';
import { goertzel } from './ritrattista';
import { notaVicina } from './note';
import { trovaPicchi, tonoWav, sweepWav, leggiQuaderno,
  salvaNelQuaderno, cancellaDalQuaderno } from './cimatica';

const F_MIN_GRAFICO = 20;

const scarica = (blob, nome) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nome; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
};

const scriviHz = (hz) => String((+hz).toFixed(1)).replace('.', ',');

export default function Risonanze({ ottieniLab, ottieniAnalisi }) {
  const [da, setDa] = useState('60');
  const [a, setA] = useState('1200');
  const [durata, setDurata] = useState('45');
  const [fase, setFase] = useState('pronto');     // pronto | sweep | tono
  const [occhio, setOcchio] = useState(false);    // misura senza microfono
  const [freqViva, setFreqViva] = useState(null); // il numerone durante lo sweep
  const [tonoHz, setTonoHz] = useState(null);     // il tono in mano
  const tonoHzRef = useRef(null);                 // la verita' sincrona del numero
  const [tonoVivo, setTonoVivo] = useState(false); // sta suonando?
  const [tonoAmp, setTonoAmp] = useState(0.5);
  const [etichetta, setEtichetta] = useState('');
  const [picchi, setPicchi] = useState(null);
  const [msg, setMsg] = useState('');
  const [quaderno, setQuaderno] = useState(leggiQuaderno);
  const labRef = useRef(null);
  const telaRef = useRef(null);
  const puntiRef = useRef([]);
  const faseRef = useRef('pronto');
  faseRef.current = fase;
  const occhioRef = useRef(false);
  const ultimaRef = useRef(0);
  const bufRef = useRef(null);
  const limitiRef = useRef([60, 1200]);

  const numero = (t, min, max, rip) => {
    const v = parseFloat(String(t).replace(',', '.'));
    return Number.isFinite(v) ? Math.min(Math.max(v, min), max) : rip;
  };

  /* ── L'INTERROGAZIONE (lo sweep) ─────────────────────────────── */
  const misura = async () => {
    const lab = ottieniLab();                     // nel gesto
    labRef.current = lab;
    if (faseRef.current === 'sweep') { fermaLoSweep(); return; }
    setMsg(''); setPicchi(null);
    /* RZ4 — senza microfono la misura non si nega: si dichiara la
       via A OCCHIO (sweep + i tuoi occhi), che e' come il founder
       ha trovato la risonanza della sua moneta */
    let aOcchio = false;
    if (!lab.orecchio.attivo()) {
      try { await lab.orecchio.apri(); } catch { aOcchio = true; }
    }
    occhioRef.current = aOcchio;
    setOcchio(aOcchio);
    const f0 = numero(da, 20, 18000, 60);
    const f1 = numero(a, 20, 18000, 1200);
    const sec = numero(durata, 10, 300, 45);
    setDa(String(f0)); setA(String(f1)); setDurata(String(sec));
    limitiRef.current = [Math.min(f0, f1), Math.max(f0, f1)];
    puntiRef.current = [];
    lab.generatore.imposta({ forma: 'sine', amp: 0.5, orecchio: 'entrambe',
      fase: 1e-7 });
    lab.generatore.imposta({ freq: f0 });
    await lab.generatore.avvia();
    lab.generatore.imposta({ freq: f1, secondi: sec });
    setFase('sweep');
  };

  /* IL FERMO E' UNA MISURA (RZ1, rivisto col founder 28/8: «quando
     stoppiamo il suono si deve fermare»): il fermo CATTURA la
     frequenza e fa SILENZIO — la misura resta in mano, e risentirla
     e' un gesto esplicito (▶ Tienila). Fermare ferma: com'e' giusto
     che sia. */
  const fermaLoSweep = () => {
    const lab = labRef.current;
    const qui = lab.generatore.stato().freq;      // PRIMA si legge, poi si spegne
    lab.generatore.ferma();
    tonoHzRef.current = +qui.toFixed(1);
    setTonoHz(tonoHzRef.current);
    setTonoVivo(false);
    setFase('tono');
    concludi(true);
  };

  const concludi = (fermatoAMano = false) => {
    const trovati = occhioRef.current ? [] : trovaPicchi(puntiRef.current);
    if (!occhioRef.current) setPicchi(trovati);
    if (fermatoAMano) {
      setMsg('Fermato: la frequenza è tua. ▶ Tienila per risentirla, aggiusta fine, salva.');
    } else if (occhioRef.current) {
      setMsg('Sweep finito. Se non hai visto l’oggetto vibrare, riprova più lento (durata maggiore) o su un campo diverso.');
    } else {
      setMsg(trovati.length
        ? `${trovati.length} risonanze trovate: sono i punti dove il tuo oggetto canta — ▶ per tenerle.`
        : 'Nessun picco netto dalla curva: prova più lento, più vicino, o a occhio (ferma tu quando vedi vibrare).');
    }
  };

  /* ── IL TONO IN MANO (RZ2): tre porte, una barra ─────────────── */
  const tieni = async (hz) => {
    const lab = ottieniLab();                     // nel gesto
    labRef.current = lab;
    lab.generatore.imposta({ forma: 'sine', amp: tonoAmp,
      orecchio: 'entrambe', fase: 1e-7 });
    lab.generatore.imposta({ freq: hz });
    await lab.generatore.avvia();
    tonoHzRef.current = +(+hz).toFixed(1);
    setTonoHz(tonoHzRef.current);
    setTonoVivo(true);
    setFase('tono');
    setMsg('');
  };

  const aggiusta = (dHz) => {
    const lab = labRef.current;
    /* a tono VIVO si parte dal MOTORE (stato React stantio: due
       tocchi rapidi si cancellavano — misurato); a tono spento si
       lavora sul numero, e il ▶ suonera' quello */
    const base = (tonoVivo && lab)
      ? lab.generatore.stato().freq : (tonoHzRef.current || 0);
    const nuovo = +Math.min(18000, Math.max(20, base + dHz)).toFixed(1);
    if (tonoVivo && lab) lab.generatore.imposta({ freq: nuovo });
    tonoHzRef.current = nuovo;
    setTonoHz(nuovo);
  };

  const cambiaAmp = (v) => {
    setTonoAmp(v);
    if (tonoVivo) labRef.current?.generatore.imposta({ amp: v });
  };

  /* ■ ferma il SUONO, la misura resta in mano; ✕ chiude la barra */
  /* UX (28/8, founder): «dai salvataggi clicco play ma per stoppare
     devo tornare su al cruscotto». Ogni ▶ e' un INTERRUTTORE SUL
     POSTO: se la SUA frequenza sta suonando mostra ■ e la spegne
     da li' — mai costringere lo scroll per fare silenzio. */
  const staSuonando = (hz) => tonoVivo
    && Math.abs((tonoHz || 0) - (+hz)) < 0.05;
  const alternaQui = (hz) => (staSuonando(hz) ? fermaTono() : tieni(hz));

  const fermaTono = () => {
    labRef.current?.generatore.ferma();
    setTonoVivo(false);
  };
  const chiudiTono = () => {
    if (tonoVivo) labRef.current?.generatore.ferma();
    setTonoVivo(false);
    setFase('pronto');
  };

  /* RZ5 — la SCOPERTA nel quaderno: una frequenza sola, etichettata */
  const salvaScoperta = () => {
    if (!tonoHzRef.current) return;
    const voce = {
      tipo: 'scoperta',
      quando: new Date().toISOString().slice(0, 16).replace('T', ' '),
      hz: tonoHzRef.current,
      etichetta: etichetta.trim().slice(0, 40) || null,
    };
    if (salvaNelQuaderno(voce)) {
      setQuaderno(leggiQuaderno());
      setEtichetta('');
      setMsg('Scoperta salvata nel quaderno (resta su questo dispositivo).');
    } else setMsg('Quaderno non disponibile su questo browser.');
  };

  const salvaSweep = () => {
    if (!picchi || !picchi.length) return;
    const voce = {
      tipo: 'sweep',
      quando: new Date().toISOString().slice(0, 16).replace('T', ' '),
      da: limitiRef.current[0], a: limitiRef.current[1],
      risonanze: picchi.map((p) => p.hz),
    };
    if (salvaNelQuaderno(voce)) {
      setQuaderno(leggiQuaderno());
      setMsg('Salvato nel quaderno di banco (resta su questo dispositivo).');
    } else setMsg('Quaderno non disponibile su questo browser.');
  };

  /* ── il campionatore + il numerone + il pittore ──────────────── */
  useEffect(() => iscrivi(() => {
    const lab = labRef.current;

    if (lab && faseRef.current === 'sweep') {
      const s = lab.generatore.stato();
      const ora = performance.now();
      if (ora - ultimaRef.current >= 100) {
        ultimaRef.current = ora;
        setFreqViva(s.freq);
        if (!occhioRef.current) {
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
        }
        if (!s.corsa) {                            // la rampa e' arrivata in fondo
          lab.generatore.ferma();
          setFase('pronto');
          concludi();
        }
      }
    }

    /* il disegno della curva (solo con la via del microfono) */
    const tela = telaRef.current;
    if (!tela) return;
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
      (picchi || []).forEach((p) => {
        const x = xDaHz(p.hz);
        c2d.strokeStyle = oro;
        c2d.beginPath(); c2d.moveTo(x, 6 * dpr); c2d.lineTo(x, H); c2d.stroke();
        c2d.fillStyle = oro;
        c2d.font = `${Math.round(10 * dpr)}px ui-monospace, Menlo, monospace`;
        c2d.textAlign = x > W - 50 * dpr ? 'right' : 'left';
        c2d.fillText(scriviHz(p.hz), x + (x > W - 50 * dpr ? -4 : 4) * dpr, 14 * dpr);
      });
    } else {
      c2d.fillStyle = nota;
      c2d.font = `${Math.round(10 * dpr)}px ui-monospace, Menlo, monospace`;
      c2d.textAlign = 'center';
      c2d.fillText(occhioRef.current
        ? 'via a occhio: niente curva — lo strumento sei tu'
        : 'la curva eccitazione → risposta si disegna qui, dal vivo',
        W / 2, H / 2);
    }
  }), [ottieniAnalisi, picchi]);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => { labRef.current?.generatore.ferma(); }, []);

  const notaTono = tonoHz ? notaVicina(tonoHz) : null;
  const notaViva = freqViva ? notaVicina(freqViva) : null;

  return (
    <section className="lab-card lab-risonanze" data-testid="lab-risonanze">
      <div className="lab-chead">
        <h2>Le Risonanze</h2>
        <span className="lab-cnote">genera → eccita → trova → tieni → osserva: il ciclo del banco</span>
      </div>

      {/* RZ6 — i quattro passi, sempre in vista */}
      <ol className="lab-rz-passi" data-testid="lab-rz-passi">
        <li><b>Prepara</b>: l&rsquo;oggetto (moneta, bottiglia, bicchiere) vicino all&rsquo;altoparlante.</li>
        <li><b>Interroga</b>: avvia lo sweep — col microfono la curva ascolta, senza <i>guardi tu</i>.</li>
        <li><b>Tieni</b>: quando canta (o danza), ferma: la nota resta in mano e la aggiusti fine.</li>
        <li><b>Salva</b>: la scoperta va nel quaderno, e la risuoni quando vuoi.</li>
      </ol>

      <div className="lab-sweep-campi">
        <label>Da
          <input value={da} inputMode="decimal" data-testid="lab-ris-da"
            disabled={fase === 'sweep'} onChange={(e) => setDa(e.target.value)} />
          <i>Hz</i>
        </label>
        <label>A
          <input value={a} inputMode="decimal" data-testid="lab-ris-a"
            disabled={fase === 'sweep'} onChange={(e) => setA(e.target.value)} />
          <i>Hz</i>
        </label>
        <label>Durata
          <input value={durata} inputMode="decimal" data-testid="lab-ris-durata"
            disabled={fase === 'sweep'} onChange={(e) => setDurata(e.target.value)} />
          <i>s</i>
        </label>
        <button type="button" className={'lab-play' + (fase === 'sweep' ? ' fermo' : '')}
          data-testid="lab-ris-misura" onClick={misura}>
          {fase === 'sweep' ? '■ Ferma QUI' : '◉ Interroga con lo sweep'}
        </button>
      </div>

      {/* il numerone dello sweep: dove siamo, mentre corriamo */}
      {fase === 'sweep' && freqViva && (
        <div className="lab-rz-viva" data-testid="lab-rz-viva">
          <span className="lab-rz-hz">{scriviHz(freqViva)}</span><b>Hz</b>
          {notaViva && <i>{notaViva.nome}</i>}
          <em>{occhio ? 'guarda l’oggetto: quando vibra, ferma' : 'la curva sta ascoltando'}</em>
        </div>
      )}

      {/* RZ1+RZ2 — IL TONO IN MANO */}
      {fase === 'tono' && tonoHz && (
        <div className="lab-rz-tono" data-testid="lab-rz-tono">
          <div className="lab-rz-tonoriga">
            <span className="lab-rz-hz">{scriviHz(tonoHz)}</span><b>Hz</b>
            {notaTono && (
              <i>{notaTono.nome}
                {notaTono.cents !== 0 && ` ${notaTono.cents > 0 ? '+' : ''}${notaTono.cents}c`}</i>
            )}
            <span className="lab-rz-chips">
              {[-1, -0.1, 0.1, 1].map((d) => (
                <button key={d} type="button" className="chip"
                  data-testid={`lab-rz-fine-${d}`}
                  onClick={() => aggiusta(d)}>
                  {d > 0 ? '+' : '−'}{String(Math.abs(d)).replace('.', ',')}
                </button>
              ))}
            </span>
          </div>
          <div className="lab-rz-tonoriga">
            <label className="lab-par lab-rz-amp">
              <span>Ampiezza <b>{Math.round(tonoAmp * 100)}%</b></span>
              <input type="range" className="lab-slider" min="0.05" max="0.9"
                step="0.05" value={tonoAmp}
                onChange={(e) => cambiaAmp(+e.target.value)} />
            </label>
            <input className="lab-rz-etichetta" value={etichetta}
              placeholder="etichetta (es. moneta)" maxLength={40}
              data-testid="lab-rz-etichetta"
              onChange={(e) => setEtichetta(e.target.value)} />
            <button type="button" className="lab-freeze"
              data-testid="lab-rz-salva-scoperta"
              onClick={salvaScoperta}>Salva scoperta</button>
            <button type="button" className="lab-freeze"
              onClick={async () => scarica(await tonoWav(tonoHz, 30),
                `tono-${tonoHz}hz.wav`)}>⤓ WAV</button>
            <button type="button"
              className={'lab-play' + (tonoVivo ? ' fermo' : '')}
              data-testid="lab-rz-tienila"
              onClick={() => (tonoVivo ? fermaTono() : tieni(tonoHzRef.current))}>
              {tonoVivo ? '■ Ferma' : '▶ Tienila'}
            </button>
            <button type="button" className="ghost" title="Chiudi la barra"
              data-testid="lab-rz-chiudi" onClick={chiudiTono}>✕</button>
          </div>
          <p className="lab-volume">
            {tonoVivo
              ? 'Sta suonando: aggiusta di ±0,1 e guarda l’oggetto — le risonanze vivono in finestre strette.'
              : 'Silenzio: la frequenza è tua. ▶ Tienila per risentirla quando vuoi.'}
          </p>
        </div>
      )}

      {msg && <p className="lab-volume" aria-live="polite" data-testid="lab-ris-msg">{msg}</p>}

      {!occhio && (
        <canvas ref={telaRef} className="lab-tela lab-ris-tela" role="img"
          aria-label="Curva eccitazione-risposta con le risonanze trovate" />
      )}

      {picchi && picchi.length > 0 && (
        <div className="lab-ris-esito" data-testid="lab-ris-esito">
          {picchi.map((p) => (
            <span key={p.hz} className="lab-ris-picco">
              <b>{scriviHz(p.hz)} Hz</b> (+{String(p.db).replace('.', ',')} dB)
              <button type="button"
                className={'chip' + (staSuonando(p.hz) ? ' on' : '')}
                data-testid={`lab-ris-tieni-${Math.round(p.hz)}`}
                title="Tieni questa frequenza: la senti e la aggiusti"
                onClick={() => alternaQui(p.hz)}>
                {staSuonando(p.hz) ? '■ Ferma' : '▶ Tienila'}
              </button>
              <button type="button" className="chip" title="Scarica 30 s di tono a questa frequenza (WAV per un ampli)"
                onClick={async () => scarica(await tonoWav(p.hz, 30), `tono-${p.hz}hz.wav`)}>
                ⤓
              </button>
            </span>
          ))}
          <button type="button" className="lab-freeze" data-testid="lab-ris-salva"
            onClick={salvaSweep}>Salva nel quaderno</button>
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

      {/* RZ5 — il quaderno vivo: sweep e scoperte, tutte risuonabili */}
      {quaderno.length > 0 && (
        <div className="lab-quaderno" data-testid="lab-quaderno">
          <h3>Il quaderno di banco</h3>
          {quaderno.map((v, i) => (
            <div key={`${v.quando}-${i}`} className="lab-quaderno-riga">
              <span>{v.quando}
                {v.tipo === 'scoperta'
                  ? ` · ${v.etichetta || 'scoperta'}`
                  : ` · ${v.da}→${v.a} Hz`}
              </span>
              <b>
                {(v.tipo === 'scoperta' ? [v.hz] : (v.risonanze || []))
                  .map((hz) => (
                    <button key={hz} type="button"
                      className={'chip lab-quaderno-hz' + (staSuonando(hz) ? ' on' : '')}
                      title={staSuonando(hz) ? 'Ferma' : 'Risuona questa frequenza'}
                      onClick={() => alternaQui(hz)}>
                      {staSuonando(hz) ? '■' : '▶'} {scriviHz(hz)}
                    </button>
                  ))}
              </b>
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
        sue frequenze: lo sweep gliele chiede tutte. Col microfono la
        curva ascolta la risposta; <b>senza, i tuoi occhi sono lo
        strumento</b> — se vedi l&rsquo;oggetto danzare, ferma: il banco
        ricorda dove eri e ti lascia la nota in mano. Trovata la
        risonanza, tienila addosso all&rsquo;oggetto e guarda: riso, acqua,
        monete — le figure che si formano sono i suoi modi, resi
        visibili.
      </p>
    </section>
  );
}
