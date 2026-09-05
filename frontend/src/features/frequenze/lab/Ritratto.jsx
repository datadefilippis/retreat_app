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
 * ampli della cimatica). FA3 (FARO, 30/8): la consegna in libreria e'
 * uscita dalla stanza — il gesto qui e' il QUADERNO; l'admin carica
 * dalla sua casa (/admin/sound).
 */
import React, { useEffect, useRef, useState } from 'react';
import { analizza } from './ritrattista';
import { curaMicrofono } from './microfono';
import InvitoQuaderno from './InvitoQuaderno';
import { sincronizza, spingi } from './quadernoRemoto';
import { campana, renderizzaWav, wavDaCampioni, leggiRitratti, salvaRitratto,
  cancellaRitratto } from './fonderia';
import RitrattoVisual from './RitrattoVisual';
import OndaViva from './OndaViva';
import { notaVicina } from './note';

const SECONDI = 6;

export default function Ritratto({ ottieniLab, ottieniAnalisi = null }) {
  const [fase, setFase] = useState('pronto');     // pronto | registro | analizzo
  const [conto, setConto] = useState(0);
  const [esito, setEsito] = useState(null);       // il ritratto, o null
  const [niente, setNiente] = useState(false);    // analisi senza esito
  const [spenti, setSpenti] = useState([]);       // parziali esclusi (hz)
  const [respiro, setRespiro] = useState(1);      // moltiplicatore delle vite
  const [inSuono, setInSuono] = useState(null);   // 'orig'|'colpo'|'tenuto'|'q:i:modo'
  const [msg, setMsg] = useState('');
  /* Il quaderno dei ritratti (29/8): registro come nelle Risonanze */
  const [salvati, setSalvati] = useState(leggiRitratti);
  /* FA4, l'account fonde il quaderno remoto al volo */
  useEffect(() => {
    let vivo = true;
    sincronizza().then((ok) => { if (ok && vivo) setSalvati(leggiRitratti()); });
    return () => { vivo = false; };
  }, []);
  const [etichetta, setEtichetta] = useState('');
  /* LM0 (5/9): la registrazione cruda si porta a casa (il referto
     dal telefono vero) e la saturazione si dice */
  const [haPresa, setHaPresa] = useState(false);
  const [avviso, setAvviso] = useState('');
  const labRef = useRef(null);
  const contoRef = useRef(null);
  const presaRef = useRef(null);                  // i campioni registrati
  const srRef = useRef(44100);
  const vivoRef = useRef(null);                   // {ferma} di cio' che suona
  const micSpostatoRef = useRef(false);           // LM2: analyser sul master

  /* LM2 (5/9, «scattava e tremava» dal telefono): registrare apre il
     microfono e lo lascia aperto, e aprirlo sposta l'analyser sul
     mic. Poi l'A/B suonava dal master ma la sagoma e l'Onda viva
     leggevano il MICROFONO — cio' che il telefono sente dal suo
     altoparlante: trigger mai agganciato, sagoma che balla. Per la
     durata dell'ascolto l'analyser torna sul master (la promessa del
     contratto: «i campioni veri del master»), e quando il suono
     finisce il microfono torna sotto l'analyser. Il mic resta
     aperto: niente secondo permesso per registrare di nuovo. */
  const perAscolto = (lab) => {
    if (lab && lab.orecchio.attivo() && !micSpostatoRef.current) {
      lab.analisi.sorgente(null);
      micSpostatoRef.current = true;
    }
  };
  const ripristinaMic = () => {
    if (!micSpostatoRef.current) return;
    micSpostatoRef.current = false;
    const lab = labRef.current;
    const nodo = lab && lab.orecchio.attivo() ? lab.orecchio.nodo() : null;
    if (nodo) lab.analisi.sorgente(nodo);
  };

  const zittisci = () => {
    if (vivoRef.current) { vivoRef.current.ferma(); vivoRef.current = null; }
    setInSuono(null);
    ripristinaMic();
  };

  /* Gancio di collaudo (29/8): il pane di anteprima blocca il
     microfono, ma la fonderia e l'onda viva si devono poter provare
     — __fqzRitratto.provaEsito() monta un ritratto sintetico (tre
     modi da campana) senza registrare. Solo console, mai UI. */
  useEffect(() => {
    try {
      window.__fqzRitratto = {
        provaEsito: () => {
          labRef.current = ottieniLab();
          setNiente(false); setSpenti([]); setMsg('');
          setEsito({
            natura: 'modi', armonico: false, fondamentaleHz: 220,
            parziali: [
              { hz: 220, db: 0, t60: 2.2 },
              { hz: 587, db: -7, t60: 1.4 },
              { hz: 1122, db: -13, t60: 0.8 },
            ],
          });
        },
      };
    } catch { /* SSR/test */ }
    return () => { try { delete window.__fqzRitratto; } catch { /* via */ } };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { clearInterval(contoRef.current); zittisci(); },
    []);   // eslint-disable-line react-hooks/exhaustive-deps

  const registra = async () => {
    const lab = ottieniLab();                     // nel gesto: iOS lo esige
    labRef.current = lab;
    try { await lab.ctx.resume(); } catch { /* gia' attivo */ }
    zittisci();
    setEsito(null); setNiente(false); setSpenti([]); setMsg(''); setAvviso('');
    /* IL CASO DEL FOUNDER (28/8): registrava la voce ma il microfono
       era chiuso — il banco ascoltava il silenzio delle sorgenti
       spente e rispondeva «troppo piano». Ora il Ritratto apre
       l'orecchio DA SOLO quando nessuna sorgente sta suonando; se il
       microfono viene negato, lo si dice SUBITO, senza sprecare sei
       secondi di conto. */
    const suonaBanco = lab.generatore.stato().attivo
      || lab.generatore2.stato().attivo;
    if (!lab.orecchio.attivo() && !suonaBanco) {
      try { await lab.orecchio.apri(); } catch (e) {
        /* la rinascita col mic vivo (iOS, frequenze diverse) */
        if (e && e.name === 'RinascitaMic' && e.stream) {
          try {
            const nuovo = ottieniLab();
            labRef.current = nuovo;
            await nuovo.orecchio.adottaStream(e.stream);
          } catch (e2) {
            setNiente(false);
            setMsg(curaMicrofono(e2) + ' Oppure accendi una sorgente al Banco e ritrai quella.');
            return;
          }
        } else {
          setNiente(false);
          /* la voce unica del microfono (founder 30/8): dice la cura
             vera, non un generico «serve il microfono» */
          setMsg(curaMicrofono(e) + ' Oppure accendi una sorgente al Banco e ritrai quella.');
          return;
        }
      }
    }
    setFase('registro'); setConto(SECONDI);
    contoRef.current = setInterval(
      () => setConto((c) => Math.max(0, c - 1)), 1000);
    try {
      const { campioni, sampleRate } = await labRef.current.analisi.registra(SECONDI);
      clearInterval(contoRef.current);
      setFase('analizzo');
      /* un respiro al browser prima del conto pesante */
      await new Promise((r) => setTimeout(r, 30));
      const r = analizza(campioni, sampleRate);
      presaRef.current = campioni; srRef.current = sampleRate;
      setHaPresa(true);
      setEsito(r); setNiente(!r);
      /* LM1 (5/9): la saturazione si DICE, con la cura — la tabella
         c'e' ma porta l'asterisco */
      if (r && r.clipping) {
        setAvviso(`Il microfono ha saturato (picco ${String(r.piccoDb).replace('.', ',')} dBFS): frequenze e forze sono indicative. Allontana il telefono dalla campana o colpisci più piano, e riprova.`);
      }
      if (!r) {
        /* si guarda COSA e' andato storto, e lo si dice: il silenzio
           ha una cura diversa dal «troppo piano» */
        let picco = 0;
        for (let i = 0; i < campioni.length; i++) {
          const a = Math.abs(campioni[i]);
          if (a > picco) picco = a;
        }
        setMsg(picco < 0.003
          ? 'Ho ascoltato solo silenzio: controlla che il microfono sia aperto e che il volume d’ingresso non sia a zero.'
          : 'Ho sentito qualcosa ma troppo piano o troppo breve per un ritratto: riprova più vicino al microfono, con un suono tenuto.');
      }
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
    perAscolto(lab);
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    const buf = lab.ctx.createBuffer(1, presaRef.current.length, srRef.current);
    buf.copyToChannel(presaRef.current, 0);
    const src = lab.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(lab.ingresso);
    const mio = { ferma: () => { try { src.stop(); } catch { /* gia' */ } } };
    src.onended = () => {
      setInSuono((cosa) => (cosa === 'orig' ? null : cosa));
      /* finito da solo (non fermato da un altro suono): il mic torna */
      if (vivoRef.current === mio) { vivoRef.current = null; ripristinaMic(); }
    };
    src.start();
    vivoRef.current = mio;
    setInSuono('orig');
  };

  const suonaRifusa = async (modo) => {
    const lab = labRef.current; if (!lab || !esito) return;
    zittisci();
    perAscolto(lab);
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    const esec = campana(lab.ctx, lab.ingresso, esito, { modo, respiro, spenti });
    if (!esec) return;
    vivoRef.current = esec;
    setInSuono(modo);
    if (modo === 'colpo') {
      setTimeout(() => {
        setInSuono((cosa) => (cosa === 'colpo' ? null : cosa));
        if (vivoRef.current === esec) { vivoRef.current = null; ripristinaMic(); }
      }, esec.durataSec * 1000);
    }
  };

  /* ── il quaderno dei ritratti (29/8) ─────────────────────────────
     La lezione delle Risonanze, applicata qui: ogni voce si suona e
     si ferma SUL POSTO (▶ diventa ■ nella sua chip, mai risalire),
     e la voce ricorda anche spenti+respiro — la rifusione salvata
     suona come la sentivi quando l'hai salvata. */
  const salvaNelQuaderno = () => {
    if (!esito) return;
    const voce = {
      quando: new Date().toISOString().slice(0, 16).replace('T', ' '),
      etichetta: etichetta.trim().slice(0, 40) || null,
      esito, spenti, respiro,
    };
    if (salvaRitratto(voce)) {
      setSalvati(leggiRitratti());
      setEtichetta('');
      setMsg('Ritratto salvato nel quaderno.');
      spingi();
    } else setMsg('Quaderno non disponibile su questo browser.');
  };

  const suonaDalQuaderno = async (i, modo) => {
    const chiave = `q:${i}:${modo}`;
    if (inSuono === chiave) { zittisci(); return; }
    const voce = salvati[i]; if (!voce) return;
    const lab = ottieniLab();
    labRef.current = lab;
    zittisci();
    perAscolto(lab);
    try { await lab.ctx.resume(); } catch { /* attivo */ }
    await lab.ponte.avvia();
    const esec = campana(lab.ctx, lab.ingresso, voce.esito,
      { modo, respiro: voce.respiro ?? 1, spenti: voce.spenti || [] });
    if (!esec) return;
    vivoRef.current = esec;
    setInSuono(chiave);
    if (modo === 'colpo') {
      setTimeout(() => {
        setInSuono((cosa) => (cosa === chiave ? null : cosa));
        if (vivoRef.current === esec) { vivoRef.current = null; ripristinaMic(); }
      }, esec.durataSec * 1000);
    }
  };

  const apriDalQuaderno = (i) => {
    const voce = salvati[i]; if (!voce) return;
    zittisci();
    setEsito(voce.esito);
    setSpenti(voce.spenti || []);
    setRespiro(voce.respiro ?? 1);
    setNiente(false); presaRef.current = null; setHaPresa(false); setAvviso('');
    setMsg(`Ritratto «${voce.etichetta || 'senza nome'}» aperto dal quaderno, l’originale registrato non c’è: il quaderno ricorda la tabella, non la voce.`);
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

  /* LM0 (5/9): i campioni CRUDI in WAV, cosi' come il microfono li ha
     consegnati (niente rifusione). E' il referto: quando il ritratto
     sbaglia sul telefono, il file arriva al banco e la cura si tara
     sul suono vero, non su una campana sintetica. */
  const scaricaRegistrazione = () => {
    if (!presaRef.current) return;
    const blob = wavDaCampioni(presaRef.current, srRef.current);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `registrazione-ritratto-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.wav`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
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
        {haPresa && (
          <p className="lab-ritratto-presa" data-testid="lab-ritratto-presa">
            <button type="button" className="lab-freeze"
              data-testid="lab-ritratto-scarica-presa" onClick={scaricaRegistrazione}>
              ⤓ Scarica la registrazione (WAV)
            </button>
            <span className="lab-cnote">i sei secondi crudi, come li ha sentiti il microfono: se il ritratto sbaglia, mandaceli</span>
          </p>
        )}
      </div>

      {avviso && (
        <p className="lab-orecchio-errore lab-ritratto-avviso" data-testid="lab-ritratto-avviso"
          aria-live="polite">
          {avviso}
        </p>
      )}

      {msg && !esito && (
        <p className="lab-orecchio-errore" data-testid="lab-ritratto-vuoto">
          {msg}
        </p>
      )}

      {/* I VERDETTI-MAESTRO: quando il suono NON si puo' mettere in
          tabella, il Ritratto insegna il perche', non fallisce. */}
      {esito && esito.natura === 'soffio' && (
        <div className="lab-didascalia lab-verdetto" data-testid="lab-ritratto-soffio">
          <b>È un soffio.</b> Ho sentito energia ({esito.piccoDb} dB di
          picco) ma nessun modo: lo spettro è liscio, come il vento, il
          respiro o il mare. I soffi sono fatti di <b>rumore</b>, non di
          note, non c&rsquo;è una tabella da scrivere, e una somma di onde
          pure non può rifonderli. Se vuoi sentirne la famiglia, nelle
          Meraviglie ci sono i rumori colorati; se volevi ritrarre un
          oggetto, prova a <b>colpirlo</b>: il colpo sveglia i suoi modi.
        </div>
      )}
      {esito && esito.natura === 'melodia' && (
        <div className="lab-didascalia lab-verdetto" data-testid="lab-ritratto-melodia">
          <b>La nota si muove.</b> Ho sentito un suono intonato ma la
          fondamentale ha viaggiato da <b>{String(esito.f0minHz).replace('.', ',')} Hz</b>
          {notaVicina(esito.f0minHz) && ` (${notaVicina(esito.f0minHz).nome})`} a{' '}
          <b>{String(esito.f0maxHz).replace('.', ',')} Hz</b>
          {notaVicina(esito.f0maxHz) && ` (${notaVicina(esito.f0maxHz).nome})`}:
          {esito.percussivo ? (
            <>
              {' '}ma il suono <b>decade</b> come un oggetto colpito: se era
              una campana o un bicchiere suonati forte, i suoi modi hanno
              confuso la ricerca della nota. Colpisci <b>più piano</b> (o
              allontana il telefono) e riprova: il ritratto dei modi esce
              dal colpo leggero.
            </>
          ) : (
            <>
              è una melodia, o un parlato. Il ritratto fotografa <b>una</b> nota
              tenuta, canta un suono fermo («aaah» su una sola altezza) e
              riprova. Le melodie intere sono un altro mestiere: qui si
              studia com&rsquo;è fatto UN suono.
            </>
          )}
        </div>
      )}

      {esito && esito.parziali && (
        <div className="lab-ritratto-esito lab-ritratto-griglia" data-testid="lab-ritratto-esito">
        <div className="lab-ritratto-colA">
          <p className="lab-ritratto-riga">
            {esito.armonico ? 'Suono intonato · fondamentale ' : 'Fondamentale '}
            <b>{esito.fondamentaleHz} Hz</b>
            {esito.vibrato && (
              <span data-testid="lab-ritratto-vibrato">
                {' '}· vibrato ±{String(esito.vibrato.profonditaHz).replace('.', ',')} Hz
                {' '}a {String(esito.vibrato.rateHz).replace('.', ',')} Hz
              </span>
            )}
            {' '}· {esito.continuo ? 'suono tenuto · analizzati' : 'coda analizzata'}
            {' '}{String(esito.codaSec).replace('.', ',')} s
            {esito.rumoreFondoDb !== null
              && ` · fondo della stanza ${esito.rumoreFondoDb} dB`}
          </p>

          <RitrattoVisual esito={esito} ottieniAnalisi={ottieniAnalisi}
            vivo={inSuono !== null} />

          <p className="lab-ritratto-lettura" data-testid="lab-ritratto-lettura">
            {esito.natura === 'intonato'
              ? 'Suono intonato: le corde sono le tue armoniche, multipli esatti della fondamentale. È la firma di una voce o di una corda.'
              : 'Ogni riga della tabella è un «modo»: una delle note pure di cui è fatto il tuo suono. Una corda li ha in rapporti interi; una campana no, ed è per questo che suona da campana.'}
          </p>
        </div>

        <div className="lab-ritratto-colB">
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

          {/* ── LB4: LA RIFUSIONE ── */}
          <div className="lab-fonderia" data-testid="lab-fonderia">
            <h3>La rifusione, la copia sintetica costruita dalla tabella</h3>
            <p className="lab-volume" data-testid="lab-fonderia-spiega">
              <b>Colpo</b> la suona come un oggetto percosso (ogni modo
              parte e muore con la sua vita); <b>Tenuto</b> tiene i
              modi fermi, come una campana strofinata
              {esito.armonico ? ', e per un suono intonato respira col vibrato misurato' : ''}.
              Confrontala con l&rsquo;<b>Originale</b>: è il gioco.
            </p>
            <div className="lab-fonderia-gesti">
              <button type="button" className={'lab-freeze' + (inSuono === 'orig' ? ' fermo' : '')}
                data-testid="lab-ab-originale" disabled={!presaRef.current}
                title={presaRef.current ? undefined
                  : 'Ritratto aperto dal quaderno: l’originale non è salvato'}
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
            {/* L'ONDA VIVA (29/8): mentre l'A/B suona, la forma d'onda
                vera dal master, trigger dell'Oscilloscopio, scia al
                fosforo. Si apre solo col suono (di QUESTA fonderia:
                il quaderno ha la sua tela, accanto alle sue chip). */}
            <OndaViva ottieniAnalisi={ottieniAnalisi}
              attivo={['orig', 'colpo', 'tenuto'].includes(inSuono) ? inSuono : null} />
            <div className="lab-fonderia-gesti">
              <input type="text" className="lab-rz-etichetta"
                data-testid="lab-ritratto-etichetta"
                placeholder="etichetta («la mia campana»)…" maxLength={40}
                value={etichetta}
                onChange={(e) => setEtichetta(e.target.value)} />
              <button type="button" className="lab-freeze"
                data-testid="lab-ritratto-salva" onClick={salvaNelQuaderno}>
                Salva nel quaderno
              </button>
              <button type="button" className="lab-freeze"
                data-testid="lab-fonderia-wav" onClick={scaricaWav}>
                ⤓ WAV (tenuto, 10 s)
              </button>
              {/* FA3 (piano FARO, 30/8): la consegna in libreria e'
                  USCITA dalla stanza, il gesto dell'utente e' il
                  quaderno; il system admin carica dalla sua casa
                  (/admin/sound). Era comunque visibile solo a lui. */}
            </div>
            {msg && !niente && <p className="lab-volume" aria-live="polite">{msg}</p>}
            <p className="lab-didascalia" data-testid="lab-fonderia-didascalia">
              <b>L&rsquo;A/B è il laboratorio.</b> Originale e rifusione,
              stesso orecchio: la rifusione è la SOMMA dei modi in
              tabella, spegnine uno e risenti; ciò che manca è ciò
              che il ritratto non cattura. Per una <b>campana</b> è
              quasi tutto (l&rsquo;attacco percussivo a parte); per una
              <b> voce</b> la rifusione non sarà mai «te»: è il tuo
              spettro suonato da onde pure, senti l&rsquo;altezza e il
              colore delle vocali, non il respiro né le consonanti.
              Il <b>tenuto</b> è anche il WAV per la cimatica.
            </p>
          </div>

          </div>{/* /colB */}

          <p className="lab-ritratto-onesta">
            Le <b>frequenze</b> sono affidabili al decimo di Hz; le
            <b> ampiezze</b> sotto i 100 Hz e sopra i 15 kHz sono
            indicative, un microfono da telefono colora lo spettro.
          </p>
        </div>
      )}

      {/* IL QUADERNO DEI RITRATTI (29/8), il registro, come nelle
          Risonanze: vive anche senza un ritratto appena fatto, cosi'
          torni sulla pagina e risuoni la campana di ieri. Ogni voce
          si suona e si ferma SUL POSTO. */}
      {salvati.length > 0 && (
        <div className="lab-quaderno" data-testid="lab-ritratto-quaderno">
          <h3>Il quaderno dei ritratti</h3>
          {salvati.map((v, i) => (
            <div key={`${v.quando}-${i}`} className="lab-quaderno-riga">
              <span>{v.quando} · {v.etichetta || 'senza nome'}
                {' · '}{Math.round(v.esito?.fondamentaleHz || 0)} Hz
                {' · '}{(v.esito?.parziali || []).length} modi
              </span>
              <b>
                <button type="button"
                  className={'chip lab-quaderno-hz' + (inSuono === `q:${i}:colpo` ? ' on' : '')}
                  title={inSuono === `q:${i}:colpo` ? 'Ferma' : 'Rifondi: colpo'}
                  onClick={() => suonaDalQuaderno(i, 'colpo')}>
                  {inSuono === `q:${i}:colpo` ? '■' : '▶'} Colpo
                </button>
                <button type="button"
                  className={'chip lab-quaderno-hz' + (inSuono === `q:${i}:tenuto` ? ' on' : '')}
                  title={inSuono === `q:${i}:tenuto` ? 'Ferma' : 'Rifondi: tenuto'}
                  onClick={() => suonaDalQuaderno(i, 'tenuto')}>
                  {inSuono === `q:${i}:tenuto` ? '■' : '∿'} Tenuto
                </button>
                <button type="button" className="chip lab-quaderno-hz"
                  title="Apri questo ritratto: tabella, corde e fonderia"
                  onClick={() => apriDalQuaderno(i)}>
                  Apri
                </button>
              </b>
              <button type="button" className="ghost" title="Elimina"
                onClick={() => { if (String(inSuono).startsWith('q:')) zittisci(); setSalvati(cancellaRitratto(i)); }}>×</button>
            </div>
          ))}
          <OndaViva ottieniAnalisi={ottieniAnalisi}
            attivo={String(inSuono).startsWith('q:') ? inSuono : null}
            nome={String(inSuono).startsWith('q:')
              ? (salvati[+String(inSuono).split(':')[1]]?.etichetta || 'dal quaderno')
              : null} />
          <p className="lab-cnote">il quaderno ricorda la tabella, non la registrazione originale</p>
          <InvitoQuaderno stanza="ritratto" />
        </div>
      )}

      {/* la didascalia, ogni modulo si racconta (regola LB) */}
      <p className="lab-didascalia" data-testid="lab-ritratto-didascalia">
        <b>Cosa stai leggendo.</b> Ogni oggetto vibra solo sui suoi
        modi: la tabella è l&rsquo;elenco dei modi del tuo suono. Una corda
        ha rapporti quasi interi (2, 3, 4…); una campana no, e i
        <b> doppietti</b>, coppie di modi quasi coincidenti, sono lo
        «shimmer» che senti girare. La colonna <b>vita</b> dice quanto
        ogni modo resiste prima di spegnersi: gli acuti muoiono prima.
      </p>
    </section>
  );
}
