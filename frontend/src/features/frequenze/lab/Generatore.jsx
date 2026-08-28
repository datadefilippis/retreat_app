/**
 * GENERATORE — il pannello sorgente del Lab (STEP 1, 25/8/2026).
 *
 * React qui e' solo la mano sui comandi: il suono vive in motore.js.
 * Il pannello riceve `ottieniLab()` dalla pagina (il motore si crea
 * al primo gesto — AudioContext e ponte vogliono un tocco, iOS docet)
 * e non possiede nessun nodo audio.
 *
 * La frequenza ha DUE mani: il campo (decimali, virgola tollerata,
 * Invio o blur per confermare — il pattern del campo tempo di Crea) e
 * lo slider logaritmico (20 Hz–20 kHz: meta' corsa = meta' ottave,
 * non meta' Hertz). Il numero e' il protagonista: grande, mono, oro.
 *
 * Nessuna onda animata finta: le sagome del selettore sono comandi.
 * L'onda VERA si vedra' quando l'oscilloscopio leggera' l'analyser
 * (STEP 2) — mostrare un'animazione scollegata dal segnale e'
 * esattamente cio' che questo Lab promette di non fare.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { FORME, ORECCHIE } from './motore';
import { iscrivi } from './quadro';
import { notaVicina } from './note';
import { CAT_LINK } from '../content/biblioteca';

const MIN_UI = 20, MAX_UI = 20000;

/* slider 0..1 ↔ Hz, scala log: pos 0.5 ≈ 632 Hz, non 10 kHz */
const posAHz = (p) => MIN_UI * Math.pow(MAX_UI / MIN_UI, p);
const hzAPos = (hz) => Math.log(hz / MIN_UI) / Math.log(MAX_UI / MIN_UI);


const ETICHETTE = {
  sine: 'Sinusoide', square: 'Quadra',
  triangle: 'Triangolare', sawtooth: 'Dente di sega',
};

/* sagome disegnate, non icone da DAW: un periodo, tratto sottile */
const SAGOME = {
  sine: 'M2 12 Q 9 2, 16 12 T 30 12',
  square: 'M2 19 L2 5 L16 5 L16 19 L30 19 L30 5',
  triangle: 'M2 12 L9 4 L23 20 L30 12',
  sawtooth: 'M2 20 L16 4 L16 20 L30 4',
};

export default function Generatore({ ottieniLab, onSuono }) {
  const [forma, setForma] = useState('sine');
  const [freq, setFreq] = useState(440);
  const [campo, setCampo] = useState('440');        // il testo mentre si scrive
  const [amp, setAmp] = useState(0.25);
  const [fase, setFase] = useState(0);              // gradi, per la mano
  const [orecchio, setOrecchio] = useState('entrambe');   // LB1: dove suona
  const [attivo, setAttivo] = useState(false);
  const labRef = useRef(null);

  /* LO SWEEP (STEP 6). I tre campi sono testo finche' non si parte:
     la corsa vera vive nel motore, come rampa sull'AudioParam. */
  const [da, setDa] = useState('100');
  const [a, setA] = useState('1600');
  const [durata, setDurata] = useState('8');
  const [inCorsa, setInCorsa] = useState(false);
  const corsaRef = useRef(false);
  const ultimaLettura = useRef(0);

  /* il motore, se gia' nato, segue ogni comando; se non e' nato,
     nascera' al primo Genera con lo stato corrente */
  const comanda = (patch) => { labRef.current?.generatore.imposta(patch); };

  const confermaCampo = () => {
    /* correzione parlante: virgola → punto, poi il clamp dichiarato */
    const v = parseFloat(String(campo).replace(',', '.'));
    if (!Number.isFinite(v)) { setCampo(String(freq)); return; }
    const f = Math.min(Math.max(v, MIN_UI), MAX_UI);
    setFreq(f); setCampo(String(f));
    comanda({ freq: f });
  };

  const scegliFreq = (f) => {
    const v = Math.round(f * 100) / 100;
    setFreq(v); setCampo(String(v));
    comanda({ freq: v });
  };

  /* l'unico punto in cui il suono si accende o si spegne: da qui si
     avvisa anche il banco, che deve poter dire la verita' quando
     congela (letture ferme «e il suono continua», oppure e basta) */
  const suono = (acceso) => { setAttivo(acceso); onSuono?.(acceso); };

  const alterna = async () => {
    const lab = ottieniLab();                       // nasce QUI, nel gesto
    labRef.current = lab;
    if (attivo) { lab.generatore.ferma(); suono(false); return; }
    lab.generatore.imposta({ forma, freq, amp, orecchio,
      fase: (fase * Math.PI) / 180 });
    await lab.generatore.avvia();
    suono(true);
  };

  /* smontaggio della pagina = silenzio, senza aspettare il GC */
  useEffect(() => () => { labRef.current?.generatore.ferma(); }, []);

  /* IL NUMERO SEGUE LA CORSA. Nessun orologio nuovo: ci si mette in
     coda al giro del banco (il quadro e' l'unico che batte il tempo)
     e si legge il motore, che e' l'unica verita' sulla frequenza. Si
     aggiorna una decina di volte al secondo: la cifra si legge, e
     React non lavora per nulla. */
  useEffect(() => iscrivi(() => {
    const lab = labRef.current;
    if (!lab) return;
    const s = lab.generatore.stato();
    if (s.corsa) {
      const ora = performance.now();
      if (ora - ultimaLettura.current < 80) return;
      ultimaLettura.current = ora;
      const v = Math.round(s.freq * 100) / 100;
      setFreq(v); setCampo(String(v));
      if (!corsaRef.current) { corsaRef.current = true; setInCorsa(true); }
    } else if (corsaRef.current) {
      corsaRef.current = false; setInCorsa(false);
      const v = Math.round(s.freq * 100) / 100;   // la meta', esatta
      setFreq(v); setCampo(String(v));
    }
  }), []);

  const numero = (testo, min, max, ripiego) => {
    const v = parseFloat(String(testo).replace(',', '.'));
    if (!Number.isFinite(v)) return ripiego;
    return Math.min(Math.max(v, min), max);
  };

  const alternaSweep = async () => {
    const lab = ottieniLab();                   // nel gesto: iOS lo esige
    labRef.current = lab;
    if (inCorsa) {                              // interrompere = tenere la nota
      lab.generatore.imposta({ freq: lab.generatore.stato().freq });
      corsaRef.current = false; setInCorsa(false);
      return;
    }
    if (!attivo) { await lab.generatore.avvia(); suono(true); }
    const f0 = numero(da, MIN_UI, MAX_UI, 100);
    const f1 = numero(a, MIN_UI, MAX_UI, 1600);
    const sec = numero(durata, 0.1, 300, 8);
    setDa(String(f0)); setA(String(f1)); setDurata(String(sec));
    lab.generatore.imposta({ forma, amp, fase: (fase * Math.PI) / 180 });
    lab.generatore.imposta({ freq: f0 });                 // si parte da qui
    lab.generatore.imposta({ freq: f1, secondi: sec });   // e si corre
    corsaRef.current = true; setInCorsa(true);
  };

  const nota = notaVicina(freq);

  return (
    <section className="lab-card" data-testid="lab-generatore">
      <div className="lab-chead">
        <h2>Generatore</h2>
        <span className="lab-cnote">un segnale, generato davvero dal tuo dispositivo</span>
      </div>

      {/* la forma */}
      <div className="lab-forme" role="radiogroup" aria-label="Forma d'onda">
        {FORME.map((f) => (
          <button key={f} type="button" role="radio" aria-checked={forma === f}
            className={'lab-forma' + (forma === f ? ' viva' : '')}
            onClick={() => { setForma(f); comanda({ forma: f }); }}>
            <svg viewBox="0 0 32 24" aria-hidden="true">
              <path d={SAGOME[f]} fill="none" stroke="currentColor"
                strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
            </svg>
            <i>{ETICHETTE[f]}</i>
          </button>
        ))}
      </div>

      {/* la frequenza — il protagonista */}
      <div className="lab-freq">
        <div className="lab-freq-num">
          <input value={campo} inputMode="decimal" aria-label="Frequenza in Hertz"
            data-testid="lab-freq-campo"
            onChange={(e) => setCampo(e.target.value)}
            onBlur={confermaCampo}
            onKeyDown={(e) => { if (e.key === 'Enter') { confermaCampo(); e.target.blur(); } }} />
          <b>Hz</b>
        </div>
        <input type="range" className="lab-slider" min="0" max="1" step="0.0005"
          aria-label="Frequenza (scala logaritmica)"
          value={hzAPos(freq)}
          onChange={(e) => scegliFreq(posAHz(+e.target.value))} />
        {/* LB6 — il passo fine della cimatica: i pattern vivono in
            finestre strette, ±0,1 Hz e' un gesto, non un numero
            da riscrivere */}
        <div className="lab-passofine">
          {[-1, -0.1, 0.1, 1].map((d) => (
            <button key={d} type="button" className="chip"
              data-testid={`lab-fine-${d}`}
              onClick={() => scegliFreq(Math.min(MAX_UI, Math.max(MIN_UI, freq + d)))}>
              {d > 0 ? '+' : '−'}{String(Math.abs(d)).replace('.', ',')}
            </button>
          ))}
        </div>
        <div className="lab-freq-note">
          <span>20 Hz</span>
          {nota && (
            <span className="lab-nota" data-testid="lab-nota">
              vicino a {nota.nome}{nota.cents !== 0 && ` (${nota.cents > 0 ? '+' : ''}${nota.cents} cent)`}
            </span>
          )}
          <span>20 kHz</span>
        </div>
      </div>

      {/* ampiezza e fase */}
      <div className="lab-parametri">
        <label className="lab-par">
          <span>Ampiezza <b>{Math.round(amp * 100)}%</b></span>
          <input type="range" className="lab-slider" min="0" max="1" step="0.01"
            value={amp}
            onChange={(e) => { const a = +e.target.value; setAmp(a); comanda({ amp: a }); }} />
        </label>
        <label className="lab-par">
          <span>Fase <b>{fase}°</b></span>
          <input type="range" className="lab-slider" min="0" max="360" step="1"
            value={fase}
            onChange={(e) => {
              const g = +e.target.value; setFase(g);
              comanda({ fase: (g * Math.PI) / 180 });
            }} />
          <small>da sola non si sente: accendi la Sorgente B alla
            stessa frequenza e portala a 180° — le onde si cancellano
            (interferenza)</small>
        </label>
        <label className="lab-par">
          <span>Dove suona</span>
          <select value={orecchio} aria-label="Canale della sorgente A"
            data-testid="lab-orecchio"
            onChange={(e) => { setOrecchio(e.target.value); comanda({ orecchio: e.target.value }); }}>
            {ORECCHIE.map((o) => (
              <option key={o} value={o}>
                {o === 'entrambe' ? 'Entrambe le orecchie'
                  : o === 'sinistra' ? 'Solo sinistra' : 'Solo destra'}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="lab-azione">
        <button type="button" className={'lab-play' + (attivo ? ' fermo' : '')}
          data-testid="lab-play" onClick={alterna}>
          {attivo ? '■ Ferma' : '▶ Genera'}
        </button>
        {/* la riga di sicurezza del Lab: il volume prima di tutto */}
        <p className="lab-volume" data-testid="lab-volume">
          Parti dal volume basso: un tono puro a piena ampiezza è più
          forte di quanto sembri, soprattutto in cuffia.
        </p>
      </div>

      {/* LO SWEEP: tre numeri e un comando. La corsa e' una rampa vera
          sull'AudioParam — nessun orologio, nessuna animazione. */}
      <div className="lab-sweep" data-testid="lab-sweep">
        <h3>Sweep</h3>
        <div className="lab-sweep-campi">
          <label>Da
            <input value={da} inputMode="decimal" data-testid="lab-sweep-da"
              disabled={inCorsa} onChange={(e) => setDa(e.target.value)} />
            <i>Hz</i>
          </label>
          <label>A
            <input value={a} inputMode="decimal" data-testid="lab-sweep-a"
              disabled={inCorsa} onChange={(e) => setA(e.target.value)} />
            <i>Hz</i>
          </label>
          <label>Durata
            <input value={durata} inputMode="decimal" data-testid="lab-sweep-durata"
              disabled={inCorsa} onChange={(e) => setDurata(e.target.value)} />
            <i>s</i>
          </label>
          <button type="button" data-testid="lab-sweep-avvia"
            className={'lab-freeze' + (inCorsa ? ' fermo' : '')}
            onClick={alternaSweep}>
            {inCorsa ? '■ Ferma sweep' : '↗ Avvia sweep'}
          </button>
        </div>
        <p className="lab-sweep-nota" data-testid="lab-sweep-nota">
          {inCorsa
            ? 'in corsa — la frequenza sale per ottave, non per Hertz'
            : 'la salita è esponenziale: raddoppi uguali in tempi uguali'}
        </p>
      </div>

      {/* il ponte con la biblioteca: il Lab e' la biblioteca che si tocca */}
      <p className="lab-biblio">
        Cosa dice la ricerca sulle frequenze?{' '}
        <Link to={CAT_LINK('Altre frequenze')}>Le schede della biblioteca →</Link>
      </p>
    </section>
  );
}
