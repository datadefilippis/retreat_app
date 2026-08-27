/**
 * /ascolta/{token} — LA PAGINA DEL CLIENTE (TR4, 27/8/2026).
 *
 * Chi arriva qui ha ricevuto un LINK PERSONALE dal proprio
 * professionista (ciclo TR: un link per contatto, revocabile a
 * persona). Niente account, niente cancelli della Lettera: la porta
 * E' il token, verificato dal server a ogni gesto.
 *
 * La pagina e' volutamente SPOGLIA: titolo, chi l'ha composta, play.
 * E' il momento d'ascolto di un cliente, non una vetrina — nessun
 * funnel, nessun invito, solo le controindicazioni (che sono di
 * tutti) e il marchio discreto in testa.
 *
 * Il suono: il MASTER in streaming via <audio> (lettoreDaUrl, lo
 * stesso lettore del cerchio: Media Session, schermo bloccato,
 * seek). Se il link e' spento (revocato, o l'abbonamento del
 * professionista e' decaduto — decisione founder v3) il server
 * risponde col messaggio NEUTRO e la pagina lo riporta cosi' com'e':
 * mai la contabilita' dell'operatore davanti al suo cliente.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { frequenciesAPI } from '../../api/frequencies';
import { lettoreDaUrl } from './engine/continuo';
import SeekBar from './SeekBar';
import { SafetyCurtain, SafetyLine } from './SafetyCurtain';
import SoundTopbar from './SoundTopbar';
import './frequenze.css';
import './meditazioni.css';

const fmt = (s) => {
  s = Math.max(0, Math.round(s || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

export default function AscoltaPage() {
  const { token } = useParams();
  const [track, setTrack] = useState(null);
  const [spento, setSpento] = useState('');     // il messaggio neutro
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [safety, setSafety] = useState(false);
  const contRef = useRef(null);

  useEffect(() => {
    document.title = 'Ascolto riservato | Aurya Sound';
    let vivo = true;
    frequenciesAPI.getCondivisa(token)
      .then((r) => { if (vivo) setTrack(r.data); })
      .catch((e) => {
        if (vivo) {
          setSpento(typeof e?.response?.data?.detail === 'string'
            ? e.response.data.detail
            : 'Questo ascolto non è al momento disponibile.');
        }
      });
    return () => { vivo = false; };
  }, [token]);

  const d = track?.score?.duration_sec || track?.duration_sec || 0;

  const stop = () => { contRef.current?.pause(); };
  useEffect(() => () => {
    if (contRef.current) { contRef.current.dispose(); contRef.current = null; }
  }, []);

  const play = (fromT = 0) => {
    if (!track) return;
    if (!contRef.current) {
      contRef.current = lettoreDaUrl(
        frequenciesAPI.condivisaMasterUrl(token), d,
        { titolo: track.title, autore: track.operator?.name }, {
          onPlay: () => setPlaying(true),
          onPause: () => setPlaying(false),
          onEnd: () => { setPlaying(false); setElapsed(0); },
          onTime: (t) => setElapsed(t),
        });
    }
    contRef.current.seek(fromT);
    contRef.current.play();
  };

  return (
    <div className="fqz med" data-testid="ascolta-page">
      <SoundTopbar firma="Sound" />
      <main style={{ maxWidth: 640 }}>
        {spento ? (
          <section className="bib" style={{ textAlign: 'center', marginTop: 40 }}
            data-testid="ascolta-spento">
            <h2 style={{ fontSize: 24 }}>{spento}</h2>
            <p style={{ color: 'var(--dim)', fontSize: 14, marginTop: 10 }}>
              Se pensi sia un errore, chiedi un nuovo link a chi te
              l’ha inviato.
            </p>
          </section>
        ) : !track ? (
          <p style={{ color: 'var(--dim)', textAlign: 'center', marginTop: 60 }}
            aria-live="polite">Un momento.</p>
        ) : (
          <section className="bib" data-testid="ascolta-player">
            <div className="learn-kicker">Un ascolto riservato per te</div>
            <h2 style={{ fontSize: 27, marginBottom: 4 }}>{track.title}</h2>
            {track.operator?.name && (
              <p style={{ color: 'var(--dim)', marginBottom: 14 }}>
                di <b style={{ color: 'var(--bone)' }}>{track.operator.name}</b>
                {' '}· {Math.round(d / 60)} min
              </p>
            )}
            {track.description && (
              <p style={{ color: 'var(--dim)', lineHeight: 1.65 }}>
                {track.description}
              </p>
            )}
            <SafetyLine onOpen={() => setSafety(true)} />
            <div className="createbar" style={{ position: 'static', marginTop: 16 }}>
              <button type="button" className={`cb-play${playing ? ' suona' : ''}`}
                data-testid="ascolta-play"
                onClick={() => (playing ? stop()
                  : play(elapsed >= d - 1 ? 0 : elapsed))}>
                {playing ? `⏸ ${fmt(elapsed)}`
                  : elapsed > 0 ? '▶ Riprendi' : '▶ Ascolta'}
              </button>
              <SeekBar cur={elapsed} tot={d} fmt={fmt}
                testid="ascolta-seekbar"
                titolo="Trascina o tocca per spostarti"
                onCommit={(t) => { setElapsed(t); play(t); }} />
            </div>
            <p style={{ color: 'var(--dimmer)', fontSize: 12, marginTop: 18 }}>
              Questo link è personale: ti è stato inviato dal tuo
              professionista.
            </p>
          </section>
        )}
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/sound">Aurya Sound</a>
        <a href="/">Aurya</a>
      </footer>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
    </div>
  );
}
