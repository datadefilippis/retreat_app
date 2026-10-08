/**
 * CreaVista — IL VESTITO NUOVO DI CREA (lotto CR, 8/10/2026 sera).
 *
 * docs/PIANO_CREA_RESTYLING_2026-10-08.md. Il principio: lo strumento al
 * centro, tutto il resto a portata. Tre zone: la BARRA (una riga: ▶,
 * tempo, durata, «+ Aggiungi», «⋯»), la SESSIONE subito sotto (la linea
 * del tempo coi livelli ripiegabili), il BANCO DEL MIX (frequenze, suoni,
 * voce, respiro, protocolli, le tue tracce), colonna fissa su desktop e
 * foglio a mezza altezza su telefono. Salva/Pubblica in una barra fissa in
 * basso, con lo stato che parla lì.
 *
 * Questo file NON ha stato di sessione: riceve `kit`, l'oggetto dei gesti
 * e dei valori di FrequenzePage (stesse funzioni, stessi handler, stesso
 * contratto delle ricette). Qui vive solo lo stato dell'interfaccia
 * (fogli aperti, scheda del banco, ricerca). Il vestito vecchio resta in
 * FrequenzePage dietro ?vestito=vecchio finché il founder non dà l'ok.
 */
import React, { useEffect, useMemo, useState } from 'react';
import SeekBar from '../SeekBar';
import AuryaMode from '../visual/AuryaMode';
import { BIB } from '../content/biblioteca';
import { FAMIGLIE, GRADI } from '../content/biblioteca_testi';
import { PROTOCOLLI } from '../content/protocolli';
import { STANZE } from '../engine/spazio';
import './crea.css';

const Play = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>);
const Pausa = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h4v14H6zm8 0h4v14h-4z" /></svg>);
const Stop = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h10v10H7z" /></svg>);

/* ── il selettore: Crea · Fonti · Le mie tracce (stessa forma di Esplora) ── */
export function SelettoreCrea({ attiva, badge = 0, onFonti, navigate }) {
  const voci = [
    ['crea', 'Crea', () => navigate('/sound/crea')],
    ['fonti', 'Fonti', onFonti],
    ['tracce', 'Le mie tracce', () => navigate('/sound/tracce')],
  ];
  return (
    <nav className="sel-tre cr-sel" data-testid="cr-sel">
      {voci.map(([id, label, fn]) => (
        <button key={id} type="button"
          className={`sel-tre-voce${attiva === id ? ' on' : ''}`}
          aria-current={attiva === id ? 'page' : undefined}
          data-testid={`cr-sel-${id}`}
          onClick={() => { if (attiva !== id || id === 'fonti') fn(); }}>
          {label}{id === 'crea' && badge > 0 && <span className="cr-badge">{badge}</span>}
        </button>
      ))}
    </nav>
  );
}

/* ── un foglio: lo stesso «gate» del mondo, col corpo a scorrimento ── */
export function Foglio({ aperto, onChiudi, titolo, testid, children, largo = false }) {
  if (!aperto) return null;
  return (
    <div className="gate cr-foglio" onClick={onChiudi} data-testid={testid}>
      <div className={`gatebox${largo ? ' largo' : ''}`} onClick={(e) => e.stopPropagation()}>
        <div className="cr-foglio-testa">
          <h2>{titolo}</h2>
          <button type="button" className="cr-x" aria-label="Chiudi" onClick={onChiudi}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ── la barra: una riga sola, sempre a vista ── */
function Barra({ k, onAggiungi, onAltro, onDurata }) {
  const vuota = !k.layers.length;
  return (
    <div className="cr-barra" data-testid="cr-barra">
      <button type="button" className={`cr-play${k.playing ? ' suona' : ''}`} data-testid="cr-play"
        disabled={vuota} aria-label={k.playing ? 'Pausa' : 'Ascolta la sessione'}
        title={k.playing ? 'Pausa' : 'Ascolta la sessione'}
        onClick={() => (k.playing ? k.stopSession() : k.playGuarded(0))}>
        {k.preparing ? <span className="prep">◌</span> : k.playing ? <Pausa /> : <Play />}
      </button>
      <div className="cr-seek">
        {/* la SeekBar porta gia' i suoi tempi: la riga nostra solo a sessione vuota */}
        {vuota && (
          <div className="cr-tempo" data-testid="cr-tempo">
            <span>0:00</span>
            <span className="tot">{k.durataAuto ? '—' : k.fmt(k.duration)}</span>
          </div>
        )}
        {!vuota && (
          <SeekBar cur={k.elapsed} tot={k.duration} fmt={k.fmt}
            testid="cr-seekbar" titolo="Trascina o tocca per spostarti nella sessione"
            onCommit={(t) => k.seekTo(t)} />
        )}
      </div>
      <button type="button" className="cr-pill" data-testid="cr-durata" onClick={onDurata}
        title={k.durataAuto ? 'Durata automatica: segue le tracce. Tocca per fissarla' : 'Durata fissata. Tocca per cambiarla'}>
        ⏱ {vuota && k.durataAuto ? 'auto' : k.fmt(k.duration)}
      </button>
      <button type="button" className="cr-ico cr-aggiungi" data-testid="cr-aggiungi" onClick={onAggiungi}
        title="Aggiungi alla sessione: frequenze, suoni, la tua voce, respiro, protocolli, le tue tracce">+</button>
      <button type="button" className="cr-ico" data-testid="cr-altro" onClick={onAltro}
        title="Impostazioni, scena, reset, esporta">⋯</button>
    </div>
  );
}

/* ── il foglio della durata: gli stessi preset di sempre ── */
function FoglioDurata({ k, aperto, onChiudi }) {
  return (
    <Foglio aperto={aperto} onChiudi={onChiudi} titolo="Quanto dura" testid="fq-foglio-durata">
      <div className="foglio-durata cr-durata-corpo">
        <div className="fd-riga">
          {[10, 20, 30].map((s) => (
            <button key={`s${s}`} type="button" data-testid={`fq-durata-sec-${s}`}
              className={k.durataFissaSec === s ? 'su' : ''}
              onClick={() => k.fissaDurata(s)}>{s}″</button>
          ))}
          {[1, 5, 10, 15, 20, 30, 45, 60, 90].map((m) => (
            <button key={m} type="button"
              className={k.durataFissaSec === m * 60 ? 'su' : ''}
              onClick={() => k.fissaDurata(m * 60)}>{m}′</button>
          ))}
          <input type="text" inputMode="decimal" max="90" style={{ minWidth: 132 }}
            placeholder="min · 0:20 · 20s" data-testid="fq-durata-min"
            title="Minuti (es. 20), oppure m:ss (0:20, 1.30), oppure secondi (20s)"
            defaultValue={k.durataAuto ? '' : (k.durataFissaSec % 60 === 0 ? k.durataFissaSec / 60 : k.fmt(k.durataFissaSec))}
            onKeyDown={(e) => { if (e.key === 'Enter') k.fissaDurata(k.parseDurata(e.currentTarget.value)); }}
            onBlur={(e) => { if (e.target.value !== '') k.fissaDurata(k.parseDurata(e.target.value)); }} />
        </div>
        <button type="button" className={`fd-auto${k.durataAuto ? ' su' : ''}`}
          data-testid="fq-durata-auto" onClick={k.tornaDurataAuto}>
          Automatica, segue le tracce
        </button>
        <p className="fd-nota">Da 3 secondi a 90 minuti: scrivi «20s» o «0:20» per una
        traccia breve, un numero per i minuti. Qui in Crea la ascolti intera, sempre.
        Oltre i 30, master, export e ascolto a schermo bloccato si preparano a blocchi.</p>
      </div>
    </Foglio>
  );
}

/* ── «⋯»: impostazioni, scena, reset, esporta ── */
function FoglioAltro({ k, aperto, onChiudi }) {
  const vuota = !k.layers.length;
  return (
    <Foglio aperto={aperto} onChiudi={onChiudi} titolo="La sessione" testid="cr-foglio-altro">
      <div className="cr-campi">
        <label>Titolo
          <input type="text" value={k.title} placeholder="La mia sessione" data-testid="cr-titolo"
            onChange={(e) => k.setTitle(e.target.value)} />
        </label>
        <label title="La categoria della meditazione (dal registro della Regia): serve per pubblicare">Categoria
          <select value={k.categoria} data-testid="fq-categoria" onChange={(e) => k.setCategoria(e.target.value)}>
            <option value="">—</option>
            {k.categorie.map((c) => <option key={c.slug} value={c.slug}>{c.label}</option>)}
          </select>
        </label>
        <div className="cr-campi-riga">
          <label title="All'inizio il suono nasce dal silenzio e sale piano per questi secondi">Nasce in (s)
            <input type="number" value={k.fadeIn} min="0" max="120" step="1"
              onChange={(e) => k.setFadeIn(+e.target.value || 0)} />
          </label>
          <label title="Alla fine il suono si spegne dolcemente negli ultimi secondi">Si spegne in (s)
            <input type="number" value={k.fadeOut} min="0" max="120" step="1"
              onChange={(e) => k.setFadeOut(+e.target.value || 0)} />
          </label>
        </div>
        <label title={STANZE[k.stanza]?.hint}>🎧 Stanza
          <select data-testid="fq-stanza" value={k.stanza}
            onChange={(e) => { k.riavviaSeSuona(); k.setStanza(STANZE[e.target.value] ? e.target.value : 'asciutta'); }}>
            {Object.entries(STANZE).map(([key, s]) => <option key={key} value={key}>{s.label}</option>)}
          </select>
        </label>
        {k.hasSpace && (
          <p className="cr-nota" data-testid="fq-nota-spazio">
            🎧 Spazio e stanza si sentono in cuffia: in altoparlante restano uno stereo largo.
            Cambiali pure mentre ascolti: la sessione riparte dal punto in cui era.
          </p>
        )}
      </div>
      <div className="cr-azioni">
        <button type="button" data-testid="fq-guarda" disabled={vuota}
          className={k.guarda ? 'on' : ''}
          onClick={() => { k.setGuarda((g) => !g); onChiudi(); }}>
          ✦ {k.guarda ? 'Nascondi la scena' : 'Guarda il suono'}
        </button>
        <button type="button" data-testid="fq-export" disabled={!!k.esportando || vuota}
          title="Scarica la sessione come file MP3, per l'aula, per la chiavetta, per te"
          onClick={() => { k.esportaMp3(); onChiudi(); }}>
          {k.esportando
            ? `${k.esportando.fase}… ${Math.round(k.esportando.pct * 100)}%`
            : k.esportaDalMaster ? '⤓ Esporta MP3 (dal master, subito)' : `⤓ Esporta MP3 (~${k.pesoStimatoMB} MB)`}
        </button>
        <button type="button" className="pericolo" disabled={vuota} data-testid="cr-reset"
          onClick={() => { k.resetSession(); onChiudi(); }}>Svuota la sessione</button>
      </div>
    </Foglio>
  );
}

/* ── la barra in basso: salva, pubblica, e lo stato che parla ── */
function Piede({ k }) {
  const [vivo, setVivo] = useState('');
  useEffect(() => {
    if (!k.status) { setVivo(''); return undefined; }
    setVivo(k.status);
    const t = setTimeout(() => setVivo(''), 7000);
    return () => clearTimeout(t);
  }, [k.status]);
  const vuota = !k.layers.length;
  return (
    <div className="cr-piede" data-testid="cr-piede">
      <div className={`cr-stato${vivo ? ' su' : ''}`} data-testid="cr-stato" aria-live="polite">{vivo}</div>
      <div className="cr-piede-gesti">
        <button type="button" data-testid="fq-save" className="cr-salva"
          disabled={k.saving || vuota} onClick={k.save}>
          {k.saving ? 'Salvo…' : k.trackId ? 'Aggiorna bozza' : 'Salva bozza'}
        </button>
        {k.trackId && (k.trackStatus === 'published' ? (
          <button type="button" data-testid="fq-unpublish" className="cr-ritira"
            title={k.trackSlug ? `Pubblicata su /frequenze/${k.trackSlug}` : ''}
            onClick={k.unpublishTrack}>● Pubblicata · ritira</button>
        ) : (
          <button type="button" data-testid="fq-publish" className="cr-pubblica"
            disabled={vuota} onClick={k.publishTrack}>Pubblica</button>
        ))}
      </div>
    </div>
  );
}

/* ── il banco del mix ── */
const SCHEDE = [
  ['frequenze', '〰 Frequenze'],
  ['suoni', '♫ Suoni'],
  ['voce', '🎙 Voce'],
  ['respiro', '🫁 Respiro'],
  ['protocolli', '✦ Protocolli'],
  ['tracce', '◆ Le tue tracce'],
];

function VoceBanco({ k, q, famiglia, setFamiglia }) {
  const tutte = useMemo(() => FAMIGLIE.flatMap((f) => (BIB[f.chiave] || []).map((s, i) => ({ ...s, famiglia: f, chiave: `${f.chiave}:${i}` }))), []);
  const qq = q.trim().toLowerCase();
  const lista = qq.length >= 2
    ? tutte.filter((s) => `${s.t} ${s.hz || ''} ${s.uso || ''}`.toLowerCase().includes(qq))
    : famiglia ? tutte.filter((s) => s.famiglia.slug === famiglia) : [];
  const vive = k.liveKeys;
  return (
    <>
      {!qq && (
        <div className="cr-chips" data-testid="cr-famiglie">
          {FAMIGLIE.map((f) => (
            <button key={f.slug} type="button" className={`cr-chip${famiglia === f.slug ? ' on' : ''}`}
              data-testid={`cr-famiglia-${f.slug}`}
              onClick={() => setFamiglia(famiglia === f.slug ? null : f.slug)}>{f.chiave}</button>
          ))}
        </div>
      )}
      {!qq && !famiglia && <p className="cr-hint">Scegli una famiglia, o cerca. ▶ la senti sopra la sessione, «+» la porta nella linea del tempo.</p>}
      {vive.length > 0 && (
        <div className="cr-vive" data-testid="cr-vive">
          {vive.length} in anteprima · <button type="button" onClick={k.stopAllCards}>ferma tutto</button>
          {' · '}<button type="button" onClick={k.composeAllLive}>+ tutte alla sessione</button>
        </div>
      )}
      <div className="cr-lista">
        {lista.map((s) => {
          const live = !!k.liveCardsRef.current[s.chiave];
          return (
            <div key={s.chiave} className={`cr-voce${live ? ' suona' : ''}`} data-testid="cr-frequenza">
              <div className="cr-voce-testo">
                <b>{s.t}</b>
                <span>{s.hz}{s.g ? ` · ${s.g}` : ''}{s.uso ? ` · ${s.uso}` : ''}</span>
              </div>
              {s.cfg && (
                <button type="button" className="cr-mini-play" aria-label={live ? `Ferma ${s.t}` : `Ascolta ${s.t}`}
                  onClick={k.guard(() => k.toggleCard(s.chiave, s))}>{live ? <Stop /> : <Play />}</button>
              )}
              {s.cfg && (
                <button type="button" className="cr-mini-add" data-testid="cr-frequenza-add" aria-label={`Aggiungi ${s.t} alla sessione`}
                  onClick={() => k.addCardToSession(s)}>+</button>
              )}
            </div>
          );
        })}
      </div>
      {(qq || famiglia) && (
        <p className="cr-legenda">{Object.entries(GRADI).map(([g, v]) => `${g} ${v.label}`).join(' · ')}</p>
      )}
    </>
  );
}

function SuoniBanco({ k, q, respiro }) {
  const [momento, setMomento] = useState(null);
  const [timbro, setTimbro] = useState(null);
  const qq = q.trim().toLowerCase();
  const lista = k.sounds
    .filter((s) => (respiro ? !!s.guida : !s.guida))
    .filter((s) => !momento || s.moment === momento)
    .filter((s) => !timbro || s.category === timbro.toLowerCase())
    .filter((s) => !qq || `${s.title} ${s.category || ''}`.toLowerCase().includes(qq))
    .sort((a, b) => a.title.localeCompare(b.title, 'it', { numeric: true }));
  return (
    <>
      {!respiro && (
        <>
          <div className="cr-chips">
            {k.SOUND_MOMENTI.map(([key, label, aiuto]) => (
              <button key={key} type="button" title={aiuto} className={`cr-chip${momento === key ? ' on' : ''}`}
                onClick={() => setMomento(momento === key ? null : key)}>{label}</button>
            ))}
          </div>
          <div className="cr-chips piccole">
            {k.SOUND_CATS.map((c) => (
              <button key={c} type="button" className={`cr-chip${timbro === c ? ' on' : ''}`}
                onClick={() => setTimbro(timbro === c ? null : c)}>{c}</button>
            ))}
          </div>
        </>
      )}
      {respiro && <p className="cr-hint">Un ciclo del respiro entra come guida (si ripete, respiri e round nella riga); un clip breve una volta sola, dove stai ascoltando.</p>}
      {!lista.length && <p className="cr-hint">{k.sounds.length ? 'Nessuna base con questi filtri.' : 'Libreria in arrivo.'}</p>}
      <div className="cr-lista">
        {lista.map((s) => {
          const suona = k.previewingId === s.id;
          return (
            <div key={s.id} className={`cr-voce${suona ? ' suona' : ''}`} data-testid="cr-suono">
              <div className="cr-voce-testo">
                <b>{s.title}</b>
                <span>{k.fmt(s.duration_sec || 0)}{s.category ? ` · ${s.category}` : ''}{s.guida === 'ciclo' ? ` · ciclo ${String((s.ciclo_sec || 0).toFixed(1)).replace('.', ',')} s` : ''}</span>
              </div>
              <button type="button" className="cr-mini-play" aria-label={suona ? 'Ferma' : 'Ascolta'}
                onClick={() => k.toggleSoundPreview(s)}>
                {k.soundLoadingId === s.id ? <span className="prep">◌</span> : suona ? <Stop /> : <Play />}
              </button>
              <button type="button" className="cr-mini-add" data-testid={`fq-sound-add-${s.id}`}
                aria-label={`Aggiungi ${s.title} alla sessione`}
                title={k.eClipBreve(s) ? 'Una volta sola, nel punto in cui stai ascoltando' : 'In loop, sotto le frequenze'}
                onClick={() => k.addSoundToSession(s)}>+</button>
            </div>
          );
        })}
      </div>
    </>
  );
}

function ProtocolliBanco({ k }) {
  return (
    <div className="cr-lista">
      {Object.entries(PROTOCOLLI).map(([name, p]) => (
        <div key={name} className="cr-voce" data-testid={`cr-prot-${p.intent}`}>
          <div className="cr-voce-testo">
            <b>{name} <span className={`cr-grado ${p.grade}`}>{p.grade}</span></b>
            <span>{p.durataMin || 20}′ · {p.ev}</span>
          </div>
          <button type="button" className="cr-mini-add testo" onClick={() => k.loadProtocol(name)}>Carica</button>
        </div>
      ))}
    </div>
  );
}

function TracceBanco({ k, q }) {
  const qq = q.trim().toLowerCase();
  const lista = k.drafts.filter((d) => d.id !== k.trackId && (!qq || (d.title || '').toLowerCase().includes(qq)));
  if (!lista.length) return <p className="cr-hint">Nessun'altra traccia tua. «+ i suoi livelli» porta nella sessione i livelli di una traccia già fatta: un'apertura, un tappeto, una chiusura.</p>;
  return (
    <>
      <p className="cr-hint">«+ livelli» aggiunge i livelli di quella traccia alla sessione, dal punto in cui stai ascoltando. «Apri» la sostituisce.</p>
      <div className="cr-lista">
        {lista.map((d) => (
          <div key={d.id} className="cr-voce" data-testid="cr-traccia">
            <div className="cr-voce-testo">
              <b>{d.title || 'Senza titolo'}</b>
              <span>{k.fmt(d.duration_sec || 0)} · {d.layers_count} {d.layers_count === 1 ? 'livello' : 'livelli'} · {d.status === 'published' ? (d.visibility === 'private' ? 'riservata' : 'nelle Meditazioni') : 'bozza'}</span>
            </div>
            <button type="button" className="cr-mini-add testo" data-testid="cr-traccia-livelli"
              onClick={() => k.aggiungiLivelliDa(d)}>+ livelli</button>
            <button type="button" className="cr-mini-add testo tenue" onClick={() => k.openDraft(d.id)}>Apri</button>
          </div>
        ))}
      </div>
    </>
  );
}

function Banco({ k, aperto, scheda, setScheda, onChiudi }) {
  const [q, setQ] = useState('');
  const [famiglia, setFamiglia] = useState(null);
  const [alto, setAlto] = useState(false);
  useEffect(() => { setQ(''); }, [scheda]);
  if (!aperto) return null;
  return (
    <aside className={`cr-banco${alto ? ' alto' : ''}`} data-testid="cr-banco" aria-label="Il banco del mix">
      <div className="cr-banco-testa">
        <button type="button" className="cr-banco-maniglia" aria-label={alto ? 'Riduci il banco' : 'Allarga il banco'}
          onClick={() => setAlto((v) => !v)}><span /></button>
        <div className="cr-banco-schede" role="tablist">
          {SCHEDE.map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={scheda === id}
              className={`cr-chip${scheda === id ? ' on' : ''}`} data-testid={`cr-banco-${id}`}
              onClick={() => setScheda(id)}>{label}</button>
          ))}
        </div>
        <button type="button" className="cr-x" aria-label="Chiudi il banco" data-testid="cr-banco-chiudi" onClick={onChiudi}>×</button>
      </div>
      {scheda !== 'protocolli' && scheda !== 'voce' && (
        <input type="search" className="cr-cerca" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder={scheda === 'frequenze' ? 'Cerca una frequenza, un ritmo, un metodo' : scheda === 'tracce' ? 'Cerca fra le tue tracce' : 'Cerca una base'}
          aria-label="Cerca" data-testid="cr-cerca" />
      )}
      <div className="cr-banco-corpo">
        {scheda === 'frequenze' && <VoceBanco k={k} q={q} famiglia={famiglia} setFamiglia={setFamiglia} />}
        {scheda === 'suoni' && <SuoniBanco k={k} q={q} respiro={false} />}
        {scheda === 'respiro' && <SuoniBanco k={k} q={q} respiro />}
        {scheda === 'voce' && <div className="cr-leggio">{k.leggioVoce}</div>}
        {scheda === 'protocolli' && <ProtocolliBanco k={k} />}
        {scheda === 'tracce' && <TracceBanco k={k} q={q} />}
      </div>
    </aside>
  );
}

/* ── la sessione vuota ── */
function Vuota({ onBanco }) {
  return (
    <div className="cr-vuoto" data-testid="cr-vuoto">
      <p>La tua sessione è vuota.</p>
      <div>
        <button type="button" onClick={() => onBanco('protocolli')}>✦ Parti da un protocollo</button>
        <button type="button" onClick={() => onBanco('frequenze')}>〰 Aggiungi una frequenza</button>
        <button type="button" onClick={() => onBanco('suoni')}>♫ Aggiungi una base</button>
        <button type="button" onClick={() => onBanco('voce')}>🎙 Registra la tua voce</button>
      </div>
    </div>
  );
}

export default function CreaVista({ kit: k }) {
  const [banco, setBanco] = useState(false);
  const [scheda, setScheda] = useState('frequenze');
  const [altro, setAltro] = useState(false);
  const [durata, setDurata] = useState(false);
  const apriBanco = (s) => { if (s) setScheda(s); setBanco(true); };
  const riassunto = `${STANZE[k.stanza]?.label || 'asciutta'} · nasce in ${k.fadeIn}s · si spegne in ${k.fadeOut}s${k.categoria ? ` · ${k.categorie.find((c) => c.slug === k.categoria)?.label || k.categoria}` : ''}`;
  return (
    <section className={`cr${banco ? ' con-banco' : ''}`} data-testid="crea-vista">
      <SelettoreCrea attiva="crea" badge={k.layers.length} navigate={k.navigate} onFonti={() => apriBanco()} />
      <Barra k={k} onAggiungi={() => apriBanco()} onAltro={() => setAltro(true)} onDurata={() => setDurata(true)} />
      <button type="button" className="cr-riassunto" data-testid="cr-riassunto" onClick={() => setAltro(true)}
        title="Titolo, categoria, apertura e chiusura, stanza">
        <b>{k.title || 'Senza titolo'}</b> · {riassunto}
      </button>
      {k.playing && (
        <div className="cr-avviso tenue" data-testid="fq-live-hint">volume e muto agiscono subito · le altre modifiche si sentono al prossimo ascolto</div>
      )}
      {k.memoria.mb >= 350 && (
        <div className="cr-avviso" data-testid="fq-stima-memoria">
          Questa sessione chiede circa <b>{k.memoria.mb} MB</b> al dispositivo: su molti telefoni non partirà.
          {k.memoria.colpevoli.length > 0 && <> Pesa soprattutto {k.memoria.colpevoli.join(', ')}: una base in loop suona uguale e pesa un decimo.</>}
        </div>
      )}
      {k.playing && k.avvisoCuffie && (
        <div className="cr-avviso solo-telefono-block" data-testid="fq-crea-avviso-cuffie">🎧 {k.avvisoCuffie}</div>
      )}
      {k.guarda && (
        <div className="creascena cr-scena" data-testid="fq-crea-scena">
          {k.lettoreRef.current && (k.playing || k.elapsed > 0) ? (
            <AuryaMode lettore={k.lettoreRef.current} attivo altezza={240} visual={k.visual} alTocco={() => k.setStudio(true)} />
          ) : (
            <p className="soundlead" data-testid="fq-scena-attesa">Premi ▶ e la scena si accende col tuo suono.</p>
          )}
          <button type="button" className="cr-chip" data-testid="fq-studio-apri" onClick={() => k.setStudio(true)}>✦ Scegli forma e colori</button>
        </div>
      )}

      <div className="cr-corpo">
        <Banco k={k} aperto={banco} scheda={scheda} setScheda={setScheda} onChiudi={() => setBanco(false)} />
        <div className="cr-sessione" data-testid="cr-sessione">
          {k.layers.length > 0 ? k.lineaDelTempo : <Vuota onBanco={apriBanco} />}
        </div>
      </div>

      <FoglioDurata k={k} aperto={durata} onChiudi={() => setDurata(false)} />
      <FoglioAltro k={k} aperto={altro} onChiudi={() => setAltro(false)} />
      <Piede k={k} />
    </section>
  );
}
