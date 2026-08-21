/**
 * Aurya Mode — la pagina strumento (AV2, 22/8/2026).
 *
 * «Integrata ma isolata» (founder): dentro il mondo Sound, ma una
 * stanza a se' — /sound/visual. Qui chiunque porta il SUO suono:
 * carica una traccia o accende il microfono, e la guarda coi sette
 * modi del motore immersivo.
 *
 * La regola che rende tutto questo gratuito e pulito: IL SUONO NON
 * LASCIA MAI IL DISPOSITIVO. La traccia si apre in un <audio> locale
 * (mai un upload), il microfono resta nel browser. Noi non riceviamo,
 * non ospitiamo, non vediamo — ed e' scritto in pagina, perche' e' una
 * promessa all'utente prima che un'architettura.
 *
 * Meccanica audio, coi suoi vincoli veri:
 * - la traccia: <audio> + MediaElementSource → lettore → altoparlanti.
 *   createMediaElementSource si puo' chiamare UNA volta per elemento:
 *   l'elemento e' uno solo e si cambia solo il src;
 * - il microfono: getUserMedia → lettore, e BASTA — mai verso gli
 *   altoparlanti, o il larsen e' garantito;
 * - un solo AudioContext per la pagina; cambiare sorgente stacca la
 *   precedente (il mic si SPEGNE davvero: track.stop(), non pausa —
 *   la spia del browser deve spegnersi).
 */
import React, { useEffect, useRef, useState } from 'react';
import { creaLettore } from './analisi';
import AuryaMode from './AuryaMode';
import SoundTopbar from '../SoundTopbar';
import '../frequenze.css';

export default function VisualPage() {
  useEffect(() => { document.title = 'Aurya Mode — Guarda il tuo suono'; }, []);
  const [sorgente, setSorgente] = useState(null);      // null | 'file' | 'mic'
  const [nomeFile, setNomeFile] = useState('');
  const [inPlay, setInPlay] = useState(false);
  const [errore, setErrore] = useState('');
  const [lettore, setLettore] = useState(null);

  const ctxRef = useRef(null);
  const lettoreRef = useRef(null);
  const audioElRef = useRef(null);       // l'<audio> della traccia (uno solo)
  const elSourceRef = useRef(null);      // il suo MediaElementSource (uno solo)
  const micStreamRef = useRef(null);
  const micSourceRef = useRef(null);
  const urlRef = useRef(null);
  const fileInputRef = useRef(null);

  const contesto = () => {
    if (!ctxRef.current) {
      ctxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      const l = creaLettore(ctxRef.current);
      lettoreRef.current = l;
      setLettore(l);
    }
    ctxRef.current.resume();
    return ctxRef.current;
  };

  const spegniMic = () => {
    micStreamRef.current?.getTracks().forEach((t) => t.stop());
    micStreamRef.current = null;
    try { micSourceRef.current?.disconnect(); } catch { /* gia' staccato */ }
    micSourceRef.current = null;
  };
  const fermaFile = () => {
    audioElRef.current?.pause();
    setInPlay(false);
  };

  /* ── sorgente: traccia locale ── */
  const apriFile = (file) => {
    setErrore('');
    const ctx = contesto();
    spegniMic();
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = URL.createObjectURL(file);
    if (!audioElRef.current) {
      const el = new Audio();
      el.loop = true;
      audioElRef.current = el;
      // UNA volta per elemento: da qui in poi si cambia solo il src
      elSourceRef.current = ctx.createMediaElementSource(el);
      elSourceRef.current.connect(lettoreRef.current.analyser);
      lettoreRef.current.analyser.connect(ctx.destination);
      el.addEventListener('play', () => setInPlay(true));
      el.addEventListener('pause', () => setInPlay(false));
    }
    audioElRef.current.src = urlRef.current;
    audioElRef.current.play().catch(() =>
      setErrore('Il browser ha bloccato la partenza: premi Ascolta.'));
    setNomeFile(file.name);
    setSorgente('file');
  };

  /* ── sorgente: microfono ── */
  const accendiMic = async () => {
    setErrore('');
    const ctx = contesto();
    fermaFile();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
      spegniMic();
      micStreamRef.current = stream;
      micSourceRef.current = ctx.createMediaStreamSource(stream);
      // SOLO verso il lettore: mai verso gli altoparlanti (larsen)
      micSourceRef.current.connect(lettoreRef.current.analyser);
      setSorgente('mic');
    } catch {
      setErrore('Microfono non disponibile o permesso negato.');
    }
  };

  const spegniTutto = () => {
    spegniMic();
    fermaFile();
    setSorgente(null);
  };

  useEffect(() => () => {
    spegniMic();
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current.removeAttribute('src');
      audioElRef.current.load();
    }
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    ctxRef.current?.close().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fqz" data-testid="fqz-visual" style={{ minHeight: '100vh' }}>
      <SoundTopbar firma="Mode" />
      <header>
        <div>
          <h1>Aurya <em>Mode</em></h1>
          <div className="sub">Guarda il tuo suono</div>
        </div>
      </header>
      <main style={{ maxWidth: 860 }}>
        <section className="bib">
          <p className="soundlead">
            Porta un suono — una tua traccia o il microfono — e guardalo
            diventare luce, nei sette modi di Aurya. {' '}
            <b>Tutto accade sul tuo dispositivo: il tuo audio non viene
            caricato da nessuna parte.</b>
          </p>

          <AuryaMode lettore={sorgente ? lettore : null} attivo
            altezza={460} />

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
            <input ref={fileInputRef} type="file" accept="audio/*"
              style={{ display: 'none' }}
              data-testid="visual-file"
              onChange={(e) => e.target.files?.[0] && apriFile(e.target.files[0])} />
            <button type="button" className="live" data-testid="visual-carica"
              onClick={() => fileInputRef.current?.click()}>
              {sorgente === 'file' ? `♪ ${nomeFile.slice(0, 28)}` : 'Carica una traccia'}
            </button>
            {sorgente === 'file' && (
              <button type="button" className="live"
                data-testid="visual-playpause"
                onClick={() => {
                  const el = audioElRef.current;
                  if (el.paused) el.play(); else el.pause();
                }}>
                {inPlay ? '⏸ Pausa' : '▶ Ascolta'}
              </button>
            )}
            <button type="button"
              className={sorgente === 'mic' ? 'primary' : 'live'}
              data-testid="visual-mic"
              onClick={() => (sorgente === 'mic' ? spegniTutto() : accendiMic())}>
              {sorgente === 'mic' ? '● Microfono attivo — spegni' : 'Usa il microfono'}
            </button>
          </div>
          {errore && (
            <p style={{ color: 'var(--alert)', fontSize: 13, marginTop: 10 }}>{errore}</p>
          )}
          <p style={{ color: 'var(--dim)', fontSize: 12.5, marginTop: 14 }}>
            Il pulsante in alto sulla scena cambia il modo. Con il
            microfono, il suono non esce dagli altoparlanti: si guarda
            soltanto — così puoi cantare, suonare o parlare senza ritorni.
          </p>
        </section>
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/sound">Aurya Sound</a>
        <a href="/meditazioni">Meditazioni</a>
        <a href="/">← Torna su Aurya</a>
      </footer>
    </div>
  );
}
