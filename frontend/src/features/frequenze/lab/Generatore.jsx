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
import { FORME } from './motore';
import { CAT_LINK } from '../content/biblioteca';

const MIN_UI = 20, MAX_UI = 20000;

/* slider 0..1 ↔ Hz, scala log: pos 0.5 ≈ 632 Hz, non 10 kHz */
const posAHz = (p) => MIN_UI * Math.pow(MAX_UI / MIN_UI, p);
const hzAPos = (hz) => Math.log(hz / MIN_UI) / Math.log(MAX_UI / MIN_UI);

/* la nota piu' vicina, nomenclatura italiana — il ponte col mondo
   musicale che il lettore della biblioteca gia' conosce */
const NOTE = ['Do', 'Do♯', 'Re', 'Re♯', 'Mi', 'Fa', 'Fa♯', 'Sol', 'Sol♯', 'La', 'La♯', 'Si'];
function notaVicina(hz) {
  if (!hz || hz <= 0) return null;
  const n = Math.round(12 * Math.log2(hz / 440));           // semitoni da La4
  const giusta = 440 * Math.pow(2, n / 12);
  const idx = ((n % 12) + 12 + 9) % 12;                     // La4 = indice 9
  const ottava = 4 + Math.floor((n + 9) / 12);
  const cents = Math.round(1200 * Math.log2(hz / giusta));
  return { nome: `${NOTE[idx]}${ottava}`, giusta, cents };
}

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

export default function Generatore({ ottieniLab }) {
  const [forma, setForma] = useState('sine');
  const [freq, setFreq] = useState(440);
  const [campo, setCampo] = useState('440');        // il testo mentre si scrive
  const [amp, setAmp] = useState(0.25);
  const [fase, setFase] = useState(0);              // gradi, per la mano
  const [attivo, setAttivo] = useState(false);
  const labRef = useRef(null);

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

  const alterna = async () => {
    const lab = ottieniLab();                       // nasce QUI, nel gesto
    labRef.current = lab;
    if (attivo) { lab.generatore.ferma(); setAttivo(false); return; }
    lab.generatore.imposta({ forma, freq, amp, fase: (fase * Math.PI) / 180 });
    await lab.generatore.avvia();
    setAttivo(true);
  };

  /* smontaggio della pagina = silenzio, senza aspettare il GC */
  useEffect(() => () => { labRef.current?.generatore.ferma(); }, []);

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
          <small>con una sorgente sola la fase non si sente: conterà
            quando le sorgenti saranno due (interferenza)</small>
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

      {/* il ponte con la biblioteca: il Lab e' la biblioteca che si tocca */}
      <p className="lab-biblio">
        Cosa dice la ricerca sulle frequenze?{' '}
        <Link to={CAT_LINK('Altre frequenze')}>Le schede della biblioteca →</Link>
      </p>
    </section>
  );
}
