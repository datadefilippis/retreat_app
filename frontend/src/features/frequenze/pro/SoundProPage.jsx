/**
 * /sound/pro — IL BUILDER (Sound Professional P3, 26/8/2026).
 *
 *   Il Builder non crea suoni.
 *   Il Builder descrive un protocollo.
 *   Il compilatore lo traduce.
 *   Il motore lo esegue.
 *
 * Qui dentro non c'è un solo nodo audio, e non deve entrarci: nessun
 * import da engine/, nessuna anteprima, nessun player. Si scrive una
 * sequenza di passi e la si salva. L'ascolto è P4.
 *
 * NON È UNA DAW. Niente timeline, niente forme d'onda, niente
 * trascinamenti, niente mixer. Una colonna di passi, uno sotto
 * l'altro, come una ricetta — che è esattamente ciò che sono.
 *
 * LA MATEMATICA DEL TEMPO NON SI RIFÀ QUI: `durataTotale` viene dal
 * compilatore (pro/compilatore.js), lo stesso che il server ha come
 * gemello. Se il totale mostrato e il totale salvato divergessero,
 * sarebbe perché qualcuno ha ricopiato la formula: non lo facciamo.
 *
 * LA VERITÀ È DEL SERVER. Questa pagina valida l'ovvio per non far
 * perdere tempo (un numero fuori scala si vede subito), ma non è una
 * seconda copia del contratto: quando il server rifiuta, il suo
 * messaggio vince e si appende al passo che lo ha causato.
 *
 * RI-DESTINATA IN S1 (26/8, audit di prodotto): Sound Professional
 * non è un editor — l'operatore SCEGLIE, non compone. La home è il
 * CATALOGO (pro/catalogo.js, le schede oneste dei protocolli curati)
 * più i protocolli propri; il sequencer resta raggiungibile alle sue
 * rotte come porta avanzata, non come casa.
 *
 * DAL RITO IN POI (S3): da ogni scheda si AVVIA UNA SESSIONE. Il rito
 * vive in pro/Rito.jsx — è LUI a parlare col player condiviso; questa
 * pagina continua a non toccare l'audio (la guardia S1 lo impone), le
 * passa i dati e basta. Le sessioni rimaste aperte (scheda chiusa a
 * metà ascolto) si ripescano dalla home e si chiudono come
 * interrotte: il registro non deve avere righe eternamente in corso.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { soundProAPI } from '../../../api/soundPro';
import {
  BATTITO_MAX, BATTITO_MIN, PASSI_MAX, PORTANTE_MAX, PORTANTE_MIN,
  durataTotale,
} from './compilatore';
import { PERCENTO_DEFAULT, PERCENTO_MAX, PERCENTO_MIN, aGain, aPercento } from './volume';
import SoundTopbar from '../SoundTopbar';
import { SafetyCurtain } from '../SafetyCurtain';
import { CATALOGO, ORIGINI } from './catalogo';
import Rito from './Rito';
import '../frequenze.css';
import './pro.css';

/* I METODI ESPOSTI. Il DSL ne ha quattro e sono tutti e quattro
   chiari: si espongono tutti, con le parole dell'operatore e non
   quelle del motore. Chi ha bisogno del battito lo dichiara qui —
   la UI dei campi si accende da questa tabella, non da un `if`
   sparso nel JSX. */
export const METODI = [
  { id: 'tone', nome: 'Tono puro', battito: false,
    dice: 'Una frequenza sola, ferma.' },
  { id: 'drone', nome: 'Accordo', battito: false,
    dice: 'La frequenza con le sue parziali: più corposa di un tono puro.' },
  { id: 'bin', nome: 'Binaurale', battito: true, cuffie: true,
    dice: 'Due frequenze vicine, una per orecchio. Vuole le cuffie.' },
  { id: 'iso', nome: 'Isocronico', battito: true,
    dice: 'Una frequenza che pulsa. Funziona anche in cassa.' },
];
const METODO = Object.fromEntries(METODI.map((m) => [m.id, m]));

const DURATA_PASSO_DEFAULT = 180;

export const fmtTempo = (s) => {
  const v = Math.max(0, Math.round(s || 0));
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, '0')}`;
};

const passoNuovo = () => ({
  _k: `p${Math.random().toString(36).slice(2, 9)}`,
  metodo: 'tone',
  hz: 220,
  battito_hz: 8,
  battito_fine_hz: '',
  durata_sec: DURATA_PASSO_DEFAULT,
  pausa_dopo_sec: 0,
  percento: PERCENTO_DEFAULT,
});

/** Il passo della UI → il passo del DSL. Nient'altro esce di qui. */
export function versoDsl(p) {
  const passo = {
    metodo: p.metodo,
    hz: Number(p.hz),
    durata_sec: Number(p.durata_sec),
    pausa_dopo_sec: Number(p.pausa_dopo_sec) || 0,
    gain: aGain(Number(p.percento)),
  };
  if (METODO[p.metodo]?.battito) {
    passo.battito_hz = Number(p.battito_hz);
    /* vuoto = battito fermo: il compilatore metterà f1 = f0 */
    if (p.battito_fine_hz !== '' && p.battito_fine_hz != null) {
      passo.battito_fine_hz = Number(p.battito_fine_hz);
    }
  }
  return passo;
}

/** Il passo salvato → il passo della UI (riaprire non perde niente). */
export function daDsl(p, i) {
  return {
    _k: `s${i}`,
    metodo: p.metodo,
    hz: p.hz,
    battito_hz: p.battito_hz ?? 8,
    battito_fine_hz: p.battito_fine_hz ?? '',
    durata_sec: p.durata_sec,
    pausa_dopo_sec: p.pausa_dopo_sec ?? 0,
    percento: aPercento(p.gain),
  };
}

/** L'ovvio, e solo l'ovvio: la verità resta del server. */
export function guaiEvidenti(p) {
  const n = (v) => Number.isFinite(Number(v)) && String(v).trim() !== '';
  if (!n(p.hz) || p.hz < PORTANTE_MIN || p.hz > PORTANTE_MAX) {
    return `La frequenza va fra ${PORTANTE_MIN} e ${PORTANTE_MAX} Hz.`;
  }
  if (!n(p.durata_sec) || Number(p.durata_sec) < 1) {
    return 'La durata è almeno un secondo.';
  }
  if (Number(p.pausa_dopo_sec) < 0) return 'La pausa non può essere negativa.';
  if (METODO[p.metodo]?.battito) {
    const fuori = (v) => !n(v) || v < BATTITO_MIN || v > BATTITO_MAX;
    if (fuori(p.battito_hz)) {
      return `Il battito va fra ${BATTITO_MIN} e ${BATTITO_MAX} Hz.`;
    }
    if (p.battito_fine_hz !== '' && fuori(p.battito_fine_hz)) {
      return `Il battito finale va fra ${BATTITO_MIN} e ${BATTITO_MAX} Hz.`;
    }
  }
  return null;
}

/** «passo 3: frequenza 9000 fuori…» → {indice: 2, testo: 'frequenza…'} */
export function leggiErroreServer(detail) {
  const m = /^passo (\d+):\s*(.*)$/s.exec(detail || '');
  if (!m) return { indice: null, testo: detail || 'Salvataggio non riuscito.' };
  return { indice: Number(m[1]) - 1, testo: m[2] };
}

/* ── il campo, con la sua unità e il suo aiuto ─────────────────────── */
function Campo({ etichetta, unita, aiuto, children }) {
  return (
    <label className="pro-campo">
      <span className="pro-lab">{etichetta}{unita && <i> {unita}</i>}</span>
      {children}
      {aiuto && <span className="pro-aiuto">{aiuto}</span>}
    </label>
  );
}

/* ── UN PASSO ──────────────────────────────────────────────────────── */
function Passo({ p, i, ultimo, errore, onCambia, onTogli }) {
  const m = METODO[p.metodo] || METODI[0];
  const set = (campo) => (e) => onCambia(i, campo, e.target.value);
  return (
    <li className={`pro-passo${errore ? ' guasto' : ''}`} data-testid={`pro-passo-${i}`}>
      <div className="pro-passo-testa">
        <span className="pro-num">Passo {i + 1}</span>
        <select value={p.metodo} onChange={set('metodo')}
          aria-label={`Metodo del passo ${i + 1}`} data-testid={`pro-metodo-${i}`}>
          {METODI.map((v) => <option key={v.id} value={v.id}>{v.nome}</option>)}
        </select>
        <span className="pro-durata">{fmtTempo(p.durata_sec)}</span>
        <button type="button" className="ghost" title="Togli questo passo"
          onClick={() => onTogli(i)} data-testid={`pro-togli-${i}`}>×</button>
      </div>

      <p className="pro-dice">{m.dice}{m.cuffie && ' Chi ascolta deve avere le cuffie.'}</p>

      <div className="pro-griglia">
        <Campo etichetta="Frequenza" unita="Hz">
          <input type="number" value={p.hz} onChange={set('hz')}
            min={PORTANTE_MIN} max={PORTANTE_MAX} step="0.01"
            data-testid={`pro-hz-${i}`} />
        </Campo>

        {m.battito && (
          <>
            <Campo etichetta="Battito" unita="Hz">
              <input type="number" value={p.battito_hz} onChange={set('battito_hz')}
                min={BATTITO_MIN} max={BATTITO_MAX} step="0.01"
                data-testid={`pro-battito-${i}`} />
            </Campo>
            <Campo etichetta="Battito finale" unita="Hz"
              aiuto={p.battito_fine_hz === '' ? 'Vuoto: il battito resta fermo.'
                : 'Il battito scivola da uno all’altro lungo il passo.'}>
              <input type="number" value={p.battito_fine_hz}
                onChange={set('battito_fine_hz')} placeholder="—"
                min={BATTITO_MIN} max={BATTITO_MAX} step="0.01"
                data-testid={`pro-battito-fine-${i}`} />
            </Campo>
          </>
        )}

        <Campo etichetta="Durata" unita="secondi" aiuto={fmtTempo(p.durata_sec)}>
          <input type="number" value={p.durata_sec} onChange={set('durata_sec')}
            min="1" step="1" data-testid={`pro-durata-${i}`} />
        </Campo>

        {!ultimo && (
          <Campo etichetta="Pausa dopo" unita="secondi"
            aiuto={Number(p.pausa_dopo_sec) > 0 ? fmtTempo(p.pausa_dopo_sec) : 'Nessuna pausa.'}>
            <input type="number" value={p.pausa_dopo_sec}
              onChange={set('pausa_dopo_sec')} min="0" step="1"
              data-testid={`pro-pausa-${i}`} />
          </Campo>
        )}

        <Campo etichetta="Volume" unita={`${p.percento}%`}>
          <input type="range" value={p.percento} onChange={set('percento')}
            min={PERCENTO_MIN} max={PERCENTO_MAX} step="1"
            data-testid={`pro-volume-${i}`} />
        </Campo>
      </div>

      {errore && <p className="pro-errore" data-testid={`pro-errore-${i}`}>{errore}</p>}
    </li>
  );
}

/* ── IL RIEPILOGO: cosa succederà, in ordine ───────────────────────── */
function Riepilogo({ passi }) {
  const totale = durataTotale(passi.map(versoDsl));
  return (
    <aside className="pro-riepilogo" data-testid="pro-riepilogo">
      <h3>Cosa succederà</h3>
      <ol>
        {passi.map((p, i) => (
          <React.Fragment key={p._k}>
            <li>
              <span>Passo {i + 1} · {METODO[p.metodo]?.nome}</span>
              <b>{fmtTempo(p.durata_sec)}</b>
            </li>
            {i < passi.length - 1 && Number(p.pausa_dopo_sec) > 0 && (
              <li className="pausa">
                <span>Pausa</span><b>{fmtTempo(p.pausa_dopo_sec)}</b>
              </li>
            )}
          </React.Fragment>
        ))}
      </ol>
      <p className="pro-totale" data-testid="pro-totale">
        <span>Durata totale</span><b>{fmtTempo(totale)}</b>
      </p>
      {passi.length >= PASSI_MAX && (
        <p className="pro-aiuto">Hai raggiunto i {PASSI_MAX} passi.</p>
      )}
    </aside>
  );
}

/* ── L'EDITOR ──────────────────────────────────────────────────────── */
function Editor({ id, onSalvato }) {
  const navigate = useNavigate();
  const nuovo = !id || id === 'nuovo';
  const [caricando, setCaricando] = useState(!nuovo);
  const [salvando, setSalvando] = useState(false);
  const [protocollo, setProtocollo] = useState(null);
  const [nome, setNome] = useState('');
  const [descrizione, setDescrizione] = useState('');
  const [note, setNote] = useState('');
  const [passi, setPassi] = useState(() => [passoNuovo()]);
  const [erroriPasso, setErroriPasso] = useState({});
  const [avviso, setAvviso] = useState(null);

  useEffect(() => {
    if (nuovo) { setCaricando(false); return; }
    let vivo = true;
    (async () => {
      try {
        const { data } = await soundProAPI.get(id);
        if (!vivo) return;
        setProtocollo(data);
        setNome(data.nome || '');
        setDescrizione(data.descrizione || '');
        setNote(data.note_operative || '');
        setPassi((data.steps || []).map(daDsl));
      } catch (e) {
        if (vivo) setAvviso(e?.response?.data?.detail || 'Protocollo non trovato.');
      } finally {
        if (vivo) setCaricando(false);
      }
    })();
    return () => { vivo = false; };
  }, [id, nuovo]);

  const cambia = useCallback((i, campo, valore) => {
    setPassi((prec) => prec.map((p, k) => (k === i ? { ...p, [campo]: valore } : p)));
    setErroriPasso((prec) => (prec[i] ? { ...prec, [i]: null } : prec));
  }, []);
  const togli = useCallback((i) => {
    setPassi((prec) => (prec.length === 1 ? prec : prec.filter((_, k) => k !== i)));
    setErroriPasso({});
  }, []);
  const aggiungi = () => {
    setPassi((prec) => (prec.length >= PASSI_MAX ? prec : [...prec, passoNuovo()]));
  };

  const salva = async () => {
    setAvviso(null);
    if (!nome.trim()) { setAvviso('Dai un nome al protocollo.'); return; }
    /* l'ovvio, prima di disturbare il server */
    const evidenti = {};
    passi.forEach((p, i) => { const g = guaiEvidenti(p); if (g) evidenti[i] = g; });
    if (Object.keys(evidenti).length) {
      setErroriPasso(evidenti);
      setAvviso('Ci sono passi da sistemare.');
      return;
    }
    setErroriPasso({});
    setSalvando(true);
    /* SOLO il progetto: appartenenza, versione, durata e score sono
       del server — mandarli sarebbe un 422, non un'ignoranza */
    const corpo = {
      nome: nome.trim(),
      descrizione: descrizione.trim(),
      note_operative: note.trim(),
      steps: passi.map(versoDsl),
    };
    try {
      const { data } = protocollo
        ? await soundProAPI.update(protocollo.id, corpo)
        : await soundProAPI.create(corpo);
      setProtocollo(data);
      setPassi((data.steps || []).map(daDsl));
      setAvviso(`Salvato · versione ${data.versione} · ${fmtTempo(data.durata_sec)}`);
      onSalvato?.();
      if (!protocollo) navigate(`/sound/pro/${data.id}`, { replace: true });
    } catch (e) {
      const { indice, testo } = leggiErroreServer(e?.response?.data?.detail);
      if (indice != null) setErroriPasso({ [indice]: testo });
      setAvviso(indice != null ? `Passo ${indice + 1}: ${testo}` : testo);
    } finally {
      setSalvando(false);
    }
  };

  if (caricando) return <p className="pro-vuoto">Apro il protocollo…</p>;

  return (
    <div className="pro-editor" data-testid="pro-editor">
      <div className="pro-testata">
        <button type="button" className="ghost" onClick={() => navigate('/sound/pro')}>
          ← Tutti i protocolli
        </button>
        {protocollo && (
          <span className="pro-versione" data-testid="pro-versione">
            Versione {protocollo.versione}
            {protocollo.versioni_precedenti?.length > 0
              && ` · ${protocollo.versioni_precedenti.length} precedenti`}
          </span>
        )}
      </div>

      <section className="pro-scheda">
        <Campo etichetta="Nome del protocollo">
          <input type="text" value={nome} onChange={(e) => setNome(e.target.value)}
            placeholder="Per esempio: Radicamento della sera"
            maxLength={120} data-testid="pro-nome" />
        </Campo>
        <Campo etichetta="Descrizione" aiuto="Una riga per ricordarti a cosa serve.">
          <input type="text" value={descrizione} maxLength={2000}
            onChange={(e) => setDescrizione(e.target.value)} data-testid="pro-descrizione" />
        </Campo>
        <Campo etichetta="Note operative"
          aiuto="Appunti tuoi: come lo conduci, cosa dici, cosa hai notato.">
          <textarea value={note} rows={3} maxLength={4000}
            onChange={(e) => setNote(e.target.value)} data-testid="pro-note" />
        </Campo>
      </section>

      <div className="pro-corpo">
        <ol className="pro-passi">
          {passi.map((p, i) => (
            <Passo key={p._k} p={p} i={i} ultimo={i === passi.length - 1}
              errore={erroriPasso[i]} onCambia={cambia} onTogli={togli} />
          ))}
        </ol>
        <Riepilogo passi={passi} />
      </div>

      <div className="pro-azioni">
        <button type="button" onClick={aggiungi} disabled={passi.length >= PASSI_MAX}
          data-testid="pro-aggiungi">+ Aggiungi passo</button>
        <span className="pro-spazio" />
        {avviso && <span className="pro-avviso" data-testid="pro-avviso">{avviso}</span>}
        <button type="button" className="primary" onClick={salva} disabled={salvando}
          data-testid="pro-salva">
          {salvando ? 'Salvo…' : 'Salva protocollo'}
        </button>
      </div>
    </div>
  );
}

/* ── IL CATALOGO: le schede dei protocolli curati ──────────────────── */
function SchedaCore({ p, onChiudi, onAvvia }) {
  const [contro, setContro] = useState(false);
  const esperienza = p.origine === 'benessere';
  return (
    <div className="pro-scheda-core" data-testid={`pro-scheda-${p.id}`}>
      <div className="pro-testata">
        <div>
          <h2>{p.titolo}</h2>
          <p className="pro-sotto">{p.sottotitolo}</p>
        </div>
        <button type="button" className="ghost" onClick={onChiudi}
          data-testid="pro-scheda-chiudi">×</button>
      </div>

      <p className="pro-racconto">{p.racconto}</p>

      <dl className="pro-dati">
        <div><dt>Durata</dt><dd>{Math.round(p.durata_sec / 60)} minuti</dd></div>
        <div><dt>Quando usarlo</dt><dd>{p.indicazioni}</dd></div>
        <div>
          <dt>Cuffie</dt>
          <dd>
            {p.cuffie === 'necessarie' ? 'Necessarie' : 'Consigliate'}
            {p.cuffie_testo && <span className="pro-aiuto"> — {p.cuffie_testo}</span>}
          </dd>
        </div>
        <div><dt>Origine</dt><dd>{ORIGINI[p.origine]}</dd></div>
      </dl>

      {/* LA SCHEDA ONESTA: la nota di evidenza si mostra INTERA,
          punti deboli compresi — è il patto del brand */}
      <div className={`pro-evidenza${esperienza ? '' : ' con-grado'}`}
        data-testid={`pro-evidenza-${p.id}`}>
        {p.evidenza.grado && (
          <span className="pro-grado" title="Grado di evidenza">
            Evidenza {p.evidenza.grado}
          </span>
        )}
        <p>{p.evidenza.nota}</p>
        <span className="pro-revisione">Scheda rivista: {p.evidenza.revisione}</span>
      </div>

      <div className="pro-azioni-scheda">
        <button type="button" className="primary" data-testid="pro-avvia-core"
          onClick={() => onAvvia({
            tipo: 'core', id: p.id, titolo: p.titolo,
            durata_sec: p.durata_sec, cuffie_testo: p.cuffie_testo || null,
            score: p.costruisci(),
          })}>Avvia una sessione</button>
        <button type="button" className="ghost" onClick={() => setContro(true)}
          data-testid="pro-controindicazioni">Controindicazioni</button>
        {(p.id === 'calm' || p.id === 'ground') && (
          <a className="pro-ascolta-link" href={`/sound/${p.id}`}>
            Ascolta la versione pubblica →
          </a>
        )}
      </div>
      {contro && <SafetyCurtain mode="review" onClose={() => setContro(false)} />}
    </div>
  );
}

function Catalogo({ onAvvia }) {
  const [aperto, setAperto] = useState(null);
  const scelto = aperto ? CATALOGO.find((p) => p.id === aperto) : null;
  return (
    <section className="pro-catalogo" data-testid="pro-catalogo">
      <h2 className="pro-scaffale">Catalogo Aurya</h2>
      <p className="pro-scaffale-sotto">
        Protocolli curati e mantenuti da Aurya. Ogni scheda dichiara
        origine, evidenza e limiti: si sceglie sapendo cosa si sceglie.
      </p>
      {scelto ? (
        <SchedaCore p={scelto} onChiudi={() => setAperto(null)}
          onAvvia={onAvvia} />
      ) : (
        <div className="cards">
          {CATALOGO.map((p) => (
            <button key={p.id} type="button" className="card pro-core-card"
              onClick={() => setAperto(p.id)} data-testid={`pro-core-${p.id}`}>
              <div className="head">
                <h3>{p.titolo}</h3>
                {p.evidenza.grado
                  ? <span className="badge pro-badge-grado">{p.evidenza.grado}</span>
                  : <span className="badge pro-badge-aurya">AURYA</span>}
              </div>
              <div className="hz">
                {Math.round(p.durata_sec / 60)} min
                {' · '}{p.cuffie === 'necessarie' ? 'cuffie necessarie' : 'cuffie consigliate'}
              </div>
              <div className="body">{p.sottotitolo}</div>
              <div className="pro-quando">{ORIGINI[p.origine]}</div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

/* ── LA LISTA ──────────────────────────────────────────────────────── */
function Lista({ chiave, onAvvia }) {
  const navigate = useNavigate();
  const [stato, setStato] = useState(null);
  const [items, setItems] = useState(null);
  const [avviso, setAvviso] = useState(null);

  useEffect(() => {
    let vivo = true;
    setItems(null);
    (async () => {
      try {
        const { data } = await soundProAPI.list(stato);
        if (vivo) setItems(data.items || []);
      } catch (e) {
        if (vivo) { setItems([]); setAvviso(e?.response?.data?.detail || 'Non riesco a leggere i protocolli.'); }
      }
    })();
    return () => { vivo = false; };
  }, [stato, chiave]);

  const archivia = async (p) => {
    if (!window.confirm(`Archiviare «${p.nome}»? Resta consultabile fra gli archiviati.`)) return;
    try {
      await soundProAPI.archive(p.id);
      setItems((prec) => prec.filter((x) => x.id !== p.id));
    } catch (e) {
      setAvviso(e?.response?.data?.detail || 'Non archiviato.');
    }
  };

  return (
    <section data-testid="pro-lista">
      <div className="pro-testata">
        <div className="viewswitch">
          {[[null, 'In lavorazione'], ['attivo', 'Attivi'], ['archiviato', 'Archiviati']]
            .map(([v, label]) => (
              <button key={label} type="button"
                className={`vbtn${stato === v ? ' on' : ''}`}
                onClick={() => setStato(v)}
                data-testid={`pro-filtro-${v || 'tutti'}`}>{label}</button>
            ))}
        </div>
        <span className="pro-spazio" />
        <button type="button" className="primary" data-testid="pro-nuovo"
          onClick={() => navigate('/sound/pro/nuovo')}>+ Nuovo protocollo</button>
      </div>

      {avviso && <p className="pro-errore">{avviso}</p>}
      {items === null && <p className="pro-vuoto">Un momento…</p>}
      {items?.length === 0 && (
        <div className="emptycreate" data-testid="pro-lista-vuota">
          <p>{stato === 'archiviato'
            ? 'Nessun protocollo archiviato.'
            : <>Ancora nessun protocollo. <b>Nuovo protocollo</b> apre una pagina bianca: un passo alla volta.</>}</p>
        </div>
      )}

      {items?.length > 0 && (
        <div className="cards">
          {items.map((p) => (
            <div key={p.id} className="card" data-testid="pro-riga">
              <div className="head">
                <h3>{p.nome}</h3>
                <span className="badge" style={{
                  color: p.stato === 'attivo' ? 'var(--water)' : 'var(--dimmer)',
                  borderColor: p.stato === 'attivo' ? 'var(--water)' : 'var(--line)',
                }}>{p.stato.toUpperCase()}</span>
              </div>
              <div className="hz">
                {fmtTempo(p.durata_sec)} · {p.passi} {p.passi === 1 ? 'passo' : 'passi'}
                {' · '}versione {p.versione}
              </div>
              {p.descrizione && <div className="body">{p.descrizione}</div>}
              <div className="pro-quando">
                Ultima modifica {new Date(p.updated_at).toLocaleDateString('it-IT', {
                  day: 'numeric', month: 'long', year: 'numeric',
                })}
              </div>
              <div className="foot">
                {p.stato !== 'archiviato' && (
                  <button type="button" className="ghost" onClick={() => archivia(p)}>
                    Archivia
                  </button>
                )}
                <button type="button" className="add"
                  onClick={() => navigate(`/sound/pro/${p.id}`)}>Apri</button>
                {p.stato !== 'archiviato' && (
                  <button type="button" className="live" data-testid="pro-avvia-mio"
                    onClick={async () => {
                      try {
                        const { data } = await soundProAPI.get(p.id);
                        onAvvia({
                          tipo: 'operatore', id: data.id, titolo: data.nome,
                          durata_sec: data.durata_sec, score: data.score,
                        });
                      } catch (e) {
                        setAvviso(e?.response?.data?.detail || 'Protocollo non aperto.');
                      }
                    }}>Sessione</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/* ── IL RIPESCAGGIO: le sessioni rimaste aperte ────────────────────── */
function SessioniAperte({ chiave }) {
  const [aperte, setAperte] = useState([]);
  useEffect(() => {
    let vivo = true;
    soundProAPI.sessioni.list({ stato: 'in_corso' })
      .then((r) => { if (vivo) setAperte(r.data?.items || []); })
      .catch(() => { /* la home resta usabile anche senza */ });
    return () => { vivo = false; };
  }, [chiave]);
  if (!aperte.length) return null;
  const chiudi = async (id) => {
    try {
      /* ascolto sconosciuto: non si accredita niente — meglio uno
         zero onesto di una durata inventata dal muro */
      await soundProAPI.sessioni.chiudi(id, {
        esito: 'interrotta', ascolto_sec: 0,
      });
      setAperte((prec) => prec.filter((x) => x.id !== id));
    } catch { /* resta in lista, si riprova */ }
  };
  return (
    <div className="rito-ripescaggio" data-testid="pro-sessioni-aperte">
      <p>
        {aperte.length === 1
          ? 'Una sessione è rimasta aperta.'
          : `${aperte.length} sessioni sono rimaste aperte.`}
        {' '}Il registro non deve avere righe in corso per sempre:
      </p>
      {aperte.map((a) => (
        <div key={a.id} className="rito-ripescaggio-riga">
          <span>{a.protocollo?.titolo}</span>
          <button type="button" className="ghost" onClick={() => chiudi(a.id)}
            data-testid={`pro-chiudi-aperta-${a.id}`}>
            Chiudi come interrotta
          </button>
        </div>
      ))}
    </div>
  );
}

/* ── LA PAGINA ─────────────────────────────────────────────────────── */
export default function SoundProPage() {
  const { id } = useParams();
  const { user, loading } = useAuth();
  const [chiave, setChiave] = useState(0);
  const [rito, setRito] = useState(null);

  useEffect(() => { document.title = 'Protocolli — Aurya Sound Professional'; }, []);

  /* IL CANCELLO. Come in FrequenzePage: qui si decide solo COSA
     DISEGNARE — la frontiera vera sono le API, che rispondono 403
     senza il privilegio (require_sound_professional). */
  const abilitato = !!user?.sound_professional;

  useEffect(() => {
    if (!loading && !user) {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
  }, [loading, user]);

  const corpo = useMemo(() => {
    if (loading || !user) return <p className="pro-vuoto">Un momento…</p>;
    if (!abilitato) {
      return (
        <div className="soundsoon" data-testid="pro-senza-invito">
          <span className="soundsoon-ic">◆</span>
          <div>
            <strong>Aurya Sound Professional è su invito</strong>
            <span>
              I protocolli sono uno strumento di lavoro che stiamo aprendo
              a poche persone alla volta, per costruirlo insieme a chi lo usa.
              Se ti interessa, scrivici e ne parliamo.
            </span>
          </div>
        </div>
      );
    }
    if (id) return <Editor id={id} onSalvato={() => setChiave((k) => k + 1)} />;
    if (rito) {
      return <Rito protocollo={rito}
        onEsci={() => { setRito(null); setChiave((k) => k + 1); }} />;
    }
    return (
      <>
        <SessioniAperte chiave={chiave} />
        <Catalogo onAvvia={setRito} />
        <h2 className="pro-scaffale" data-testid="pro-scaffale-tuoi">I tuoi protocolli</h2>
        <p className="pro-scaffale-sotto">
          I protocolli che progetti tu, privati della tua organizzazione,
          con versioni e storia.
        </p>
        <Lista chiave={chiave} onAvvia={setRito} />
      </>
    );
  }, [loading, user, abilitato, id, chiave, rito]);

  return (
    <div className="fqz pro">
      <SoundTopbar firma="Professional" />
      <header>
        <div>
          <h1>I <em>protocolli</em></h1>
          <p className="sub">Sound Professional</p>
        </div>
      </header>
      <main>{corpo}</main>
    </div>
  );
}
