/**
 * MeditazioniCasa — LA CASA DELLE MEDITAZIONI (SN1, 8/10/2026, piano Aurya
 * Sound §4.1). /meditazioni ridisegnata come un'app di meditazione:
 *
 *   Di oggi (la vetrina)  →  cerca e filtri  →  le righe: Playlist · Per
 *   iniziare · Novità · Le più ascoltate · per intento · Con la voce · Solo
 *   suono · Le tue preferite  →  la barra in basso su telefono.
 *
 * Stesso cancello di sempre: senza sblocco si vede la SOGLIA DEL CERCHIO
 * (SogliaCerchio, lo stesso componente della vetrina vecchia); il catalogo
 * e le playlist arrivano dal server solo con la prova. Niente motore qui:
 * solo dati e vetrina.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';
import { frequenciesAPI } from '../../../api/frequencies';
import { storefrontAPI } from '../../../api/storefront';
import { CASA_CONSIGLI, SOUND_PIU_ATTIVO, SOUND_LETTORE_IN_CASA } from '../stato';
import { LettoreProvider, useLettore } from './lettore';
import { LettoreBarra, SchedaMeditazione } from './LettoreBarra';
import { prova, migraVecchieChiavi } from '../../../lib/cerchio';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
import Cuore, { InvitoAccount } from './Cuore';
import { usePreferite } from './preferite';
import { componiCasa, persona as costruisciPersona, FASCE_DURATA, fasciaDurata } from './consigli';   // CS: il motore dei consigli
import SoundTopbar from '../SoundTopbar';
import { SogliaCerchio } from '../MeditazioniPage';
import '../frequenze.css';
import '../meditazioni.css';
import './casa.css';

export const INTENTI = {
  dormire: 'Dormire', meditare: 'Meditare', rilassare: 'Rilassare',
  concentrare: 'Concentrare', elaborare: 'Elaborare', energizzare: 'Energizzare',
};
export const TONI = { dormire: 'viola', elaborare: 'viola', meditare: 'salvia', concentrare: 'acqua', rilassare: 'oro', energizzare: 'oro' };
export const fmtMin = (s) => { const m = Math.round((s || 0) / 60); return m < 1 ? `${Math.max(1, Math.round(s || 0))} s` : `${m} min`; };
export const fmtMinSec = (s) => { const t = Math.max(0, Math.round(s || 0)); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`; };

/** la card di una meditazione: copertina (o velo del tono), durata, titolo, chi guida.
    MR2: il cuore c'e' SEMPRE (fav/onCuore arrivano dall'hook condiviso, o da chi la monta).
    MR3: con il lettore in casa la copertina SUONA (onPlay) e il titolo apre il foglio (onApri);
    senza (flag spento o chi la monta non li passa) la card porta alla pagina come prima. */
export function CardMeditazione({ t, da = 'casa', playlist = null, fav = false, onCuore = null, onPlay = null, onApri = null }) {
  const href = `/frequenze/${t.slug}?da=${da}${playlist ? `&playlist=${encodeURIComponent(playlist)}` : ''}`;
  const inCasa = SOUND_LETTORE_IN_CASA && !!onPlay;
  const Cover = inCasa ? 'div' : Link;
  const coverProps = inCasa ? { role: 'button', tabIndex: 0, onClick: () => onPlay(t), onKeyDown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPlay(t); } } } : { to: href };
  const Corpo = inCasa ? 'div' : Link;
  const corpoProps = inCasa ? { role: 'button', tabIndex: 0, onClick: () => (onApri ? onApri(t) : onPlay(t)) } : { to: href };
  return (
    <div className={`mcard tono-${TONI[t.intent] || 'oro'}`} data-testid="casa-card">
      <Cover className={`mcover${inCasa ? ' senza-link' : ''}`} aria-label={`Ascolta ${t.title}`} {...coverProps}>
        {t.cover_url && <img src={t.cover_url} alt="" loading="lazy" />}
        {t.accesso === 'piu' && <span className="mpiu" title={SOUND_PIU_ATTIVO ? 'Riservata al Più' : 'Presto nel Più: oggi la ascolti col Cerchio'}>{SOUND_PIU_ATTIVO ? 'PIÙ' : 'PRESTO NEL PIÙ'}</span>}
        <span className="mdurata">{fmtMin(t.duration_sec)}</span>
        {inCasa && <span className="mplay" aria-hidden="true" data-testid="casa-play"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg></span>}
      </Cover>
      {onCuore && <Cuore on={fav} onClick={() => onCuore(t.slug)} titolo={t.title} testid="casa-cuore" />}
      <Corpo className={`mcorpo${inCasa ? ' senza-link' : ''}`} {...corpoProps}>
        <h3>{t.title}</h3>
        <span className="mmeta">
          {t.intent ? `${INTENTI[t.intent] || t.intent} · ` : ''}{t.guida_nome || t.operator?.name}{t.has_voce ? ' · con la voce' : ''}
        </span>
      </Corpo>
    </div>
  );
}

export function CardPlaylist({ p, fav = false, onCuore = null }) {
  return (
    <div className="mcard playlist tono-oro" data-testid="casa-playlist-card">
      <Link to={`/meditazioni/playlist/${p.slug}`} className="mcover" aria-label={`Apri la playlist ${p.title}`}>
        {p.cover_url && <img src={p.cover_url} alt="" loading="lazy" />}
        {p.accesso === 'piu' && <span className="mpiu">PIÙ</span>}
        <span className="mconta">{p.tracce_count} {p.tracce_count === 1 ? 'meditazione' : 'meditazioni'} · {fmtMin(p.duration_sec)}</span>
      </Link>
      {onCuore && <Cuore on={fav} onClick={() => onCuore(p.slug)} titolo={p.title} testid="casa-cuore-playlist" />}
      <Link to={`/meditazioni/playlist/${p.slug}`} className="mcorpo"><h3>{p.title}</h3>{p.description && <span className="mmeta">{p.description.slice(0, 90)}</span>}</Link>
    </div>
  );
}

/* SN4 — la card di un Percorso (corso con lezioni Suono): porta alla pagina del corso */
export function CardPercorso({ c }) {
  const prezzo = c.price != null ? `${Number(c.price).toFixed(0)} €` : '';
  return (
    <Link to={`${c.url}?da=meditazioni`} className="mcard tono-oro" data-testid="casa-percorso-card">
      <span className="mcover">
        {c.image_url && <img src={c.image_url} alt="" loading="lazy" />}
        <span className="mpiu" style={{ background: 'rgba(47,87,73,.92)', color: '#fff' }}>PERCORSO</span>
        {prezzo && <span className="mdurata">{prezzo}</span>}
      </span>
      <span className="mcorpo">
        <h3>{c.name}</h3>
        <span className="mmeta">{c.suono_count} {c.suono_count === 1 ? 'meditazione' : 'meditazioni'} · {c.lezioni_count} lezioni · {c.org?.name}</span>
      </span>
    </Link>
  );
}

function Riga({ id, titolo, sub, children, griglia = false, onTutte = null, tutteN = 0 }) {
  const n = React.Children.count(children);
  if (!n) return null;
  return (
    <section className="casa-sezione" id={id} data-testid={`casa-riga-${id}`}>
      <div className="casa-testa-riga">
        <div>
          <h2>{titolo}</h2>
          {sub && <p className="casa-sub">{sub}</p>}
        </div>
        {/* MR5 — «Vedi tutte» apre la griglia intera di questa riga */}
        {onTutte && tutteN > n && <button type="button" className="casa-tutte" onClick={onTutte} data-testid={`casa-tutte-${id}`}>Vedi tutte · {tutteN}</button>}
      </div>
      <div className={`riga${griglia ? ' griglia' : ''}`}>{children}</div>
    </section>
  );
}

/* MR5 — lo scheletro mentre il catalogo arriva: niente pagina vuota che salta */
function Scheletro() {
  return (
    <div data-testid="casa-scheletro">
      <div className="oggi skel" style={{ minHeight: 220, marginTop: 6 }} />
      {[0, 1].map((r) => (
        <section className="casa-sezione" key={r}>
          <div className="skel skel-titolo" />
          <div className="riga">{[0, 1, 2, 3].map((i) => <div key={i} className="mcard skel"><div className="mcover" /><div className="mcorpo"><div className="skel skel-riga" /><div className="skel skel-riga corta" /></div></div>)}</div>
        </section>
      ))}
    </div>
  );
}

const saluto = () => { const h = new Date().getHours(); return h < 6 ? 'Buonanotte' : h < 13 ? 'Buongiorno' : h < 18 ? 'Buon pomeriggio' : 'Buonasera'; };

const Icona = ({ d }) => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d={d} /></svg>);
const ICONE = {
  esplora: 'M3 12h18M3 6h18M3 18h12',
  playlist: 'M4 6h12M4 12h12M4 18h8M18 10v8m0-8l3 2',
  cerca: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16l-4.3-4.3',
  preferite: 'M12 20.2S5.6 16 3.2 12.4C1.1 9.3 2.7 5.4 6 5.4c2 0 3.1 1 4.2 2.5.7 1 .9 1 1.6 0C12.9 6.4 14 5.4 16 5.4c3.3 0 4.9 3.9 2.8 7C16.4 16 12 20.2 12 20.2z',
  impara: 'M4 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4zM20 5h-7a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h8z',
};

/* MR3 — la casa vive dentro il suo lettore: card e vetrina suonano nella barra */
export default function MeditazioniCasa() {
  return (
    <LettoreProvider>
      <MeditazioniCasaDentro />
    </LettoreProvider>
  );
}

function MeditazioniCasaDentro() {
  const navigate = useNavigate();
  const L = useLettore();
  const suona = SOUND_LETTORE_IN_CASA && L ? (t, opz) => L.avvia(t, opz) : null;
  const apri = SOUND_LETTORE_IN_CASA && L ? (t) => L.apriScheda(t) : null;
  const propsCard = (da) => (suona ? { onPlay: (t) => suona(t, { da, playlist: null }), onApri: apri, da } : { da });
  const hasAccount = !!localStorage.getItem(PLATFORM_TOKEN_KEY);
  const [items, setItems] = useState(null);
  const [playlists, setPlaylists] = useState([]);
  /* SN4 — i PERCORSI: i corsi dell'Accademia con lezioni Suono (una sola
     cassa: si comprano nel corso, mai qui). Pubblici, senza cancello. */
  const [percorsi, setPercorsi] = useState([]);
  useEffect(() => {
    storefrontAPI.getCorsiDirectory({ suono: 1 }).then((r) => setPercorsi(r.data?.corsi || [])).catch(() => setPercorsi([]));
  }, []);
  const [locked, setLocked] = useState(false);
  const [teaserCount, setTeaserCount] = useState(0);
  /* MR2 — il cuore, uno: stato e gesti dall'hook condiviso (cache di sessione) */
  const pref = usePreferite();
  const favorites = [...pref.slugs];
  const heartAsk = pref.chiediAccount;
  const setHeartAsk = pref.setChiediAccount;
  const [safety, setSafety] = useState(false);
  const [q, setQ] = useState('');
  /* MR4 — i filtri e le righe seguono il REGISTRO delle categorie (Regia);
     ?categoria=slug e' un indirizzo condivisibile */
  const [categorie, setCategorie] = useState([]);
  useEffect(() => { frequenciesAPI.categorie().then((r) => setCategorie(r.data.items || [])).catch(() => setCategorie([])); }, []);
  const [intent, setIntent] = useState(() => { try { return new URLSearchParams(window.location.search).get('categoria') || ''; } catch { return ''; } });
  useEffect(() => {
    try {
      const u = new URL(window.location.href);
      if (intent) u.searchParams.set('categoria', intent); else u.searchParams.delete('categoria');
      window.history.replaceState(window.history.state, '', u.pathname + (u.search || ''));
    } catch { /* niente */ }
  }, [intent]);
  const [durata, setDurata] = useState('');       // '' | 'breve' | 'media' | 'lunga'
  const [voce, setVoce] = useState('');           // '' | 'con' | 'senza'
  const [attiva, setAttiva] = useState('esplora');
  /* MR5 — «Vedi tutte»: la griglia intera di una riga; e il foglio della ricerca su telefono */
  const [vista, setVista] = useState(null);          // {titolo, items} | null
  const [cercaAperta, setCercaAperta] = useState(false);
  const cercaRef = useRef(null);

  /* MR7 (8/10 sera, founder: «ero dentro, sono uscito e tornato, e mi chiedeva
     di iscrivermi») — la soglia si mostra SOLO se il server dice «locked».
     Prima qualunque errore (un token dell'account scaduto → 401, la rete)
     chiudeva la casa a chi era gia' nel Cerchio. Ora: con l'account si prova
     l'account; se risponde 401 si riprova con la prova del Cerchio; se cade
     la rete si dice «riprova», senza chiedere nulla. */
  const [errore, setErrore] = useState('');
  const carica = async () => {
    setErrore('');
    /* con l'account si manda ANCHE la prova del Cerchio, se c'e': il server la
       legge per prima, cosi' un token scaduto (401 o 403 da anonimo) non chiude
       la casa a chi e' nel Cerchio; e se cade lo stesso, si riprova solo con la prova */
    const conAccount = (before) => platformApi.get('/frequencies/catalog', {
      ...(before ? { params: { before } } : {}),
      ...(prova() ? { headers: { 'X-Fqz-Unlock': prova() } } : {}),
    });
    const conProva = (before) => frequenciesAPI.getCatalog(prova(), before || null);
    let via = hasAccount ? conAccount : conProva;
    const pagina = async (before) => {
      try { return await via(before); }
      catch (e) {
        const st = e?.response?.status;
        if (via === conAccount && (st === 401 || st === 403) && prova()) { via = conProva; return via(before); }   // token scaduto: la prova basta
        throw e;
      }
    };
    try {
      const r = await pagina(null);
      let tutte = r.data.items || [];
      let before = r.data.next_before;
      // la casa vuole tutto il catalogo in mano (le righe si calcolano qui): si pagina fino in fondo
      for (let giri = 0; before && giri < 10; giri += 1) {
        const rr = await pagina(before);
        tutte = [...tutte, ...(rr.data.items || [])]; before = rr.data.next_before;
      }
      setItems(tutte); setLocked(false);
      try {
        const pr = via === conAccount ? await platformApi.get('/frequencies/playlists') : await frequenciesAPI.playlists.pubbliche(prova());
        setPlaylists(pr.data.items || []);
      } catch { setPlaylists([]); }
    } catch (e) {
      const st = e?.response?.status;
      const detail = e?.response?.data?.detail;
      if (st === 403 || st === 401) {
        setLocked(true); setItems([]); setTeaserCount(detail?.tracks_count ?? 0);
      } else {
        setItems([]); setLocked(false);
        setErrore('Non riesco a raggiungere le meditazioni in questo momento.');
      }
    }
  };
  /* SN3 — il tuo spazio: «riprendi da dove eri» e gli ascolti recenti vivono
     sull'account (la persistenza e' dell'account, decisione del piano) */
  const [spazio, setSpazio] = useState({ riprendi: null, recenti: [], nome: '', abitudine: null });
  const caricaSpazio = async () => {
    if (!hasAccount) return;
    try {
      const me = (await platformApi.get('/platform/me')).data;
      setSpazio({ riprendi: me.sound_riprendi || null, recenti: me.sound_recenti || [], nome: (me.name || '').trim().split(' ')[0], abitudine: me.sound_abitudine || null });
    } catch { /* non bloccante */ }
  };
  useEffect(() => { migraVecchieChiavi().finally(() => { carica(); caricaSpazio(); }); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleFavorite = pref.toggle;

  // ── le righe, dal catalogo ──
  const tutte = useMemo(() => items || [], [items]);
  const cercando = !!(q.trim() || intent || durata || (!CASA_CONSIGLI && voce));
  const filtrate = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return tutte.filter((t) => {
      if (intent && (t.categoria || '') !== intent) return false;   // MR4: il filtro e' la categoria
      const d = t.duration_sec || 0;
      if (durata === 'breve' && d > 10 * 60) return false;
      if (durata === 'media' && (d <= 10 * 60 || d > 20 * 60)) return false;
      if (durata === 'lunga' && d <= 20 * 60) return false;
      if (voce === 'con' && !t.has_voce) return false;
      if (voce === 'senza' && t.has_voce) return false;
      if (qq && !(`${t.title} ${t.description || ''} ${t.guida_nome || ''} ${t.operator?.name || ''} ${(t.tags || []).join(' ')}`.toLowerCase().includes(qq))) return false;
      return true;
    });
  }, [tutte, q, intent, durata, voce]);
  /* SN2 — LA VETRINA A ROTAZIONE: fra tutto cio' che e' «in vetrina»
     (meditazioni e playlist) ne esce una al giorno, la stessa per tutti,
     senza sorteggi: il giorno decide. Senza nulla in vetrina, la piu' recente. */
  const giorno = Math.floor(Date.now() / 86400000);
  const inVetrina = [
    ...playlists.filter((p) => p.in_vetrina).map((p) => ({ playlist: p })),
    ...tutte.filter((t) => t.in_vetrina).map((t) => ({ traccia: t })),
  ];
  const scelta = inVetrina.length ? inVetrina[giorno % inVetrina.length] : (tutte[0] ? { traccia: tutte[0] } : null);
  const vetrina = scelta?.traccia || null;
  const playlistVetrina = scelta?.playlist || null;
  const brevi = tutte.filter((t) => (t.duration_sec || 0) <= 10 * 60).slice(0, 12);
  const novita = tutte.slice(0, 12);
  const piuAscoltate = [...tutte].filter((t) => t.plays_total > 0).sort((a, b) => b.plays_total - a.plays_total).slice(0, 12);
  const conVoce = tutte.filter((t) => t.has_voce).slice(0, 12);
  const soloSuono = tutte.filter((t) => !t.has_voce).slice(0, 12);
  const categoriePresenti = categorie.filter((c) => tutte.some((t) => t.categoria === c.slug));
  const preferite = tutte.filter((t) => favorites.includes(t.slug));
  const playlistSalvate = playlists.filter((p) => pref.playlists.has(p.slug));
  const perSlug = Object.fromEntries(tutte.map((t) => [t.slug, t]));
  const recenti = (spazio.recenti || []).map((s) => perSlug[s]).filter(Boolean).slice(0, 12);
  const riprendi = spazio.riprendi && perSlug[spazio.riprendi.slug] && spazio.riprendi.secondo > 5
    ? { t: perSlug[spazio.riprendi.slug], secondo: spazio.riprendi.secondo } : null;
  /* CS — la casa COMPOSTA: un bacino, una carta una volta, sezioni col perche'.
     La persona esiste solo con l'account; senza, contano ora, popolarita', novita'. */
  const casa = useMemo(() => {
    if (!CASA_CONSIGLI) return null;
    const pers = hasAccount
      ? costruisciPersona({ recenti: spazio.recenti || [], riprendi: spazio.riprendi, preferite: favorites, abitudine: spazio.abitudine, perSlug })
      : null;
    return componiCasa({ tutte, vetrina, persona: pers, categorie: categoriePresenti });
  }, [tutte, vetrina, hasAccount, spazio, favorites.join('|'), categoriePresenti]); // eslint-disable-line react-hooks/exhaustive-deps
  const fasceDurataPresenti = casa ? casa.fasceDurata : new Set(tutte.map((t) => fasciaDurata(t.duration_sec)));

  /* la carta «riprendi da dove eri», una per i due vestiti della casa */
  const cardRiprendi = (r) => (
    <Link to={`/frequenze/${r.t.slug}?da=riprendi&t=${r.secondo}`} className={`oggi tono-${TONI[r.t.intent] || 'oro'}`}
      style={{ textDecoration: 'none', color: 'inherit', marginBottom: 18 }} data-testid="casa-riprendi"
      onClick={(e) => { if (suona) { e.preventDefault(); suona(r.t, { da: 'riprendi', playlist: null, da_secondo: r.secondo }); } }}>
      <div className="oggi-cover" style={{ minHeight: 120 }}>{r.t.cover_url && <img src={r.t.cover_url} alt="" />}
        <Cuore on={favorites.includes(r.t.slug)} onClick={() => toggleFavorite(r.t.slug)} titolo={r.t.title} testid="casa-riprendi-cuore" />
      </div>
      <div className="oggi-corpo">
        <span className="etichetta">Riprendi da dove eri</span>
        <h3>{r.t.title}</h3>
        <span className="body">{fmtMinSec(r.secondo)} di {fmtMin(r.t.duration_sec)}{r.t.guida_nome || r.t.operator?.name ? ` · ${r.t.guida_nome || r.t.operator?.name}` : ''}</span>
        <div style={{ marginTop: 'auto', paddingTop: 10 }}><span className="casa-cta">▶ Riprendi</span></div>
      </div>
    </Link>
  );
  const vaiA = (id) => { setAttiva(id); const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); };

  if (locked) return <SogliaCerchio teaserCount={teaserCount} onSbloccato={() => carica()} />;

  return (
    <div className={`fqz med casa${L?.traccia ? ' con-lettore' : ''}`} data-testid="casa-meditazioni">
      <SoundTopbar firma="Meditazioni" qui="/meditazioni" />
      <header className="casa-testata">
        <div>
          {hasAccount && spazio.nome
            ? <h1>{saluto()}, <em>{spazio.nome}</em></h1>
            : <h1>Le <em>meditazioni</em> di Aurya</h1>}
          <div className="sub">{hasAccount ? 'cosa ascoltiamo oggi?' : 'scegli, ascolta, riprendi quando vuoi'}</div>
        </div>
        {hasAccount && (
          <button type="button" className="casa-account" onClick={() => navigate('/account')} data-testid="casa-account">Il tuo account →</button>
        )}
      </header>
      <main id="esplora">
        {items === null ? <Scheletro /> : errore ? (
          <div className="casa-vuoto" data-testid="casa-errore"><p>{errore}</p><button type="button" className="casa-tutte" onClick={carica}>Riprova</button></div>
        ) : tutte.length === 0 ? (
          <div className="emptycreate"><p>Ancora nessuna meditazione pubblicata: le prime stanno arrivando. Intanto puoi conoscere <Link to="/sound" style={{ color: 'var(--water)' }}>il suono</Link>.</p></div>
        ) : (
          <>
            {/* ── di oggi ── */}
            {!cercando && (playlistVetrina || vetrina) && (
              <section className="casa-sezione" style={{ marginTop: 6 }} data-testid="casa-oggi">
                <div className={`oggi grande tono-${TONI[vetrina?.intent] || 'oro'}`}>
                  <div className="oggi-cover">{(playlistVetrina?.cover_url || vetrina?.cover_url) && <img src={playlistVetrina?.cover_url || vetrina.cover_url} alt="" />}
                    {playlistVetrina
                      ? <Cuore on={pref.isFavPlaylist(playlistVetrina.slug)} onClick={() => pref.togglePlaylist(playlistVetrina.slug)} titolo={playlistVetrina.title} testid="casa-oggi-cuore" />
                      : <Cuore on={favorites.includes(vetrina.slug)} onClick={() => toggleFavorite(vetrina.slug)} titolo={vetrina.title} testid="casa-oggi-cuore" />}
                  </div>
                  <div className="oggi-corpo">
                    <span className="etichetta">{playlistVetrina ? 'La playlist di oggi' : 'Di oggi'}</span>
                    <h3>{playlistVetrina ? playlistVetrina.title : vetrina.title}</h3>
                    <span className="body">{playlistVetrina
                      ? `${playlistVetrina.tracce_count} meditazioni · ${fmtMin(playlistVetrina.duration_sec)}${playlistVetrina.description ? ` · ${playlistVetrina.description.slice(0, 120)}` : ''}`
                      : `${vetrina.intent ? `${INTENTI[vetrina.intent]} · ` : ''}${fmtMin(vetrina.duration_sec)} · ${vetrina.guida_nome || vetrina.operator?.name || ''}${vetrina.description ? ` · ${vetrina.description.slice(0, 120)}` : ''}`}</span>
                    <div style={{ marginTop: 'auto', paddingTop: 10 }}>
                      {playlistVetrina
                        ? <Link to={`/meditazioni/playlist/${playlistVetrina.slug}`} className="casa-cta" data-testid="casa-oggi-ascolta">Apri la playlist</Link>
                        : suona
                          ? <button type="button" className="casa-cta" style={{ border: 0, cursor: 'pointer' }} data-testid="casa-oggi-ascolta" onClick={() => suona(vetrina, { da: 'vetrina', playlist: null })}>▶ Ascolta</button>
                          : <Link to={`/frequenze/${vetrina.slug}?da=vetrina`} className="casa-cta" data-testid="casa-oggi-ascolta">▶ Ascolta</Link>}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* ── cerca e filtri: inline da desktop, in un foglio su telefono (MR5) ── */}
            {(() => {
              const filtriUI = (
                <>
                  <div className="cerca" id="cerca" data-testid="casa-cerca">
                    <input ref={cercaRef} type="search" value={q} placeholder="Cerca una meditazione, un tema, chi la guida" aria-label="Cerca" onChange={(e) => setQ(e.target.value)} />
                  </div>
                  <div className="filtri" data-testid="casa-filtri">
                    <button type="button" className={`filtro${!intent ? ' on' : ''}`} onClick={() => setIntent('')}>Tutte</button>
                    {categoriePresenti.map((c) => <button key={c.slug} type="button" className={`filtro tono-${c.tono || 'oro'}${intent === c.slug ? ' on' : ''}`} data-testid={`casa-filtro-${c.slug}`} onClick={() => setIntent(intent === c.slug ? '' : c.slug)}>{c.label}</button>)}
                    {!CASA_CONSIGLI && (
                      <>
                        <span style={{ width: 8 }} />
                        {[['breve', '≤ 10 min'], ['media', '10–20 min'], ['lunga', '20+ min']].map(([v, l]) => (
                          <button key={v} type="button" className={`filtro${durata === v ? ' on' : ''}`} onClick={() => setDurata(durata === v ? '' : v)}>{l}</button>))}
                        <span style={{ width: 8 }} />
                        {[['con', 'Con la voce'], ['senza', 'Solo suono']].map(([v, l]) => (
                          <button key={v} type="button" className={`filtro${voce === v ? ' on' : ''}`} onClick={() => setVoce(voce === v ? '' : v)}>{l}</button>))}
                      </>
                    )}
                  </div>
                  {/* CS1 (founder): la durata un livello sotto, in grigio, solo se nel
                      catalogo ci sono fasce diverse; via «Con la voce» e «Solo suono» */}
                  {CASA_CONSIGLI && fasceDurataPresenti.size >= 2 && (
                    <div className="filtri filtri-durata" data-testid="casa-filtri-durata">
                      <span className="filtri-etichetta">Durata</span>
                      {FASCE_DURATA.filter(([v]) => fasceDurataPresenti.has(v)).map(([v, l]) => (
                        <button key={v} type="button" className={`filtro${durata === v ? ' on' : ''}`} data-testid={`casa-durata-${v}`} onClick={() => setDurata(durata === v ? '' : v)}>{l}</button>))}
                    </div>
                  )}
                </>
              );
              return (
                <>
                  <div className="cerca-inline">{filtriUI}</div>
                  {cercaAperta && (
                    <div className="gate cerca-foglio" onClick={() => setCercaAperta(false)} data-testid="casa-cerca-foglio">
                      <div className="gatebox" onClick={(e) => e.stopPropagation()}>
                        <div className="casa-testa-riga"><h2 style={{ margin: 0 }}>Cerca</h2><button type="button" className="casa-tutte" onClick={() => setCercaAperta(false)}>Chiudi</button></div>
                        {filtriUI}
                        <p className="casa-sub" style={{ marginTop: 10 }}>{cercando ? `${filtrate.length} ${filtrate.length === 1 ? 'meditazione' : 'meditazioni'}` : 'Scrivi, o scegli una categoria.'}</p>
                        {cercando && <button type="button" className="casa-cta" style={{ border: 0, cursor: 'pointer' }} onClick={() => setCercaAperta(false)}>Vedi i risultati</button>}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}

            {(vista || cercando) && (
              <button type="button" className="casa-torna" data-testid="casa-torna" onClick={() => { setVista(null); setQ(''); setIntent(''); setDurata(''); setVoce(''); }}>← Tutte le meditazioni</button>
            )}
            {cercando ? (
              filtrate.length ? (
                <Riga id="risultati" titolo={`${filtrate.length} ${filtrate.length === 1 ? 'meditazione' : 'meditazioni'}`} griglia>
                  {filtrate.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('cerca')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
              ) : (
                <div className="casa-vuoto" data-testid="casa-vuoto">
                  <p>Nessuna meditazione per questa ricerca.</p>
                  <button type="button" className="casa-tutte" onClick={() => { setQ(''); setIntent(''); setDurata(''); setVoce(''); }}>Togli i filtri</button>
                </div>
              )
            ) : vista ? (
              <Riga id="vista" titolo={vista.titolo} griglia>
                {vista.items.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('vista')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
              </Riga>
            ) : casa ? (
              <>
                <Riga id="percorsi" titolo="Percorsi" sub="Corsi con le meditazioni dentro: si comprano nell'Accademia, si ascoltano qui.">
                  {percorsi.map((c) => <CardPercorso key={c.product_id} c={c} />)}
                </Riga>
                <Riga id="playlist" titolo="Playlist" sub="Raccolte curate, da ascoltare in fila.">
                  {playlists.map((p) => <CardPlaylist key={p.id} p={p} fav={pref.isFavPlaylist(p.slug)} onCuore={pref.togglePlaylist} />)}
                </Riga>
                {/* CS — il tuo spazio: riprendi e le preferite (solo se non sono gia' uscite) */}
                {hasAccount && (casa.riprendi || casa.preferite.length > 0 || playlistSalvate.length > 0) && (
                  <section className="casa-sezione" id="tuo-spazio" data-testid="casa-tuo-spazio">
                    <h2>Il tuo spazio</h2>
                    <p className="casa-sub">Dove eri rimasta o rimasto, cosa hai salvato.</p>
                    {casa.riprendi && cardRiprendi(casa.riprendi)}
                    {casa.preferite.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }} id="preferite">Le tue preferite</h2>
                        <div className="riga" data-testid="casa-preferite">
                          {casa.preferite.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('preferiti')} fav onCuore={toggleFavorite} />)}
                        </div>
                      </>
                    )}
                    {playlistSalvate.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }}>Playlist salvate</h2>
                        <div className="riga" data-testid="casa-playlist-salvate">
                          {playlistSalvate.map((p) => <CardPlaylist key={p.id} p={p} fav onCuore={pref.togglePlaylist} />)}
                        </div>
                      </>
                    )}
                  </section>
                )}
                {/* le sezioni composte: per questo momento, da scoprire — col perche' */}
                {casa.sezioni.map((sz) => (
                  <Riga key={sz.id} id={sz.id} titolo={sz.titolo} sub={sz.perche || undefined}
                    tutteN={sz.tutte ? sz.tutte.length : 0} onTutte={sz.tutte ? () => setVista({ titolo: sz.titolo, items: sz.tutte }) : null}>
                    {sz.items.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                  </Riga>
                ))}
                {casa.categorieRighe.map((c) => (
                  <Riga key={c.id} id={c.id} titolo={c.titolo} sub={c.perche || undefined} tutteN={c.tutte.length} onTutte={() => setIntent(c.categoria)}>
                    {c.items.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                  </Riga>
                ))}
                {/* 7. le altre: solo cio' che nessuna sezione ha gia' mostrato (niente
                    doppioni); la mappa intera sta dietro «Tutte le meditazioni» */}
                <Riga id="altre" titolo={casa.piccolo ? 'Le meditazioni' : 'Le altre meditazioni'} griglia>
                  {casa.altre.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('tutte')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                {tutte.length > 1 && (
                  <div className="casa-mappa" data-testid="casa-mappa">
                    <button type="button" className="casa-tutte grande" data-testid="casa-tutte-mappa" onClick={() => setVista({ titolo: 'Tutte le meditazioni', items: tutte })}>
                      Tutte le meditazioni · {tutte.length}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <>
                <Riga id="percorsi" titolo="Percorsi" sub="Corsi con le meditazioni dentro: si comprano nell'Accademia, si ascoltano qui.">
                  {percorsi.map((c) => <CardPercorso key={c.product_id} c={c} />)}
                </Riga>
                <Riga id="playlist" titolo="Playlist" sub="Raccolte curate, da ascoltare in fila.">
                  {playlists.map((p) => <CardPlaylist key={p.id} p={p} fav={pref.isFavPlaylist(p.slug)} onCuore={pref.togglePlaylist} />)}
                </Riga>
                {/* ── SN3: il tuo spazio (con l'account): riprendi · recenti · preferite ── */}
                {hasAccount && (riprendi || recenti.length > 0 || preferite.length > 0 || playlistSalvate.length > 0) && (
                  <section className="casa-sezione" id="tuo-spazio" data-testid="casa-tuo-spazio">
                    <h2>Il tuo spazio</h2>
                    <p className="casa-sub">Dove eri rimasta o rimasto, cosa hai ascoltato, cosa hai salvato.</p>
                    {riprendi && cardRiprendi(riprendi)}
                    {false && (
                      <Link to={`/frequenze/${riprendi.t.slug}?da=riprendi&t=${riprendi.secondo}`} className={`oggi tono-${TONI[riprendi.t.intent] || 'oro'}`}
                        style={{ textDecoration: 'none', color: 'inherit', marginBottom: 18 }} data-testid="casa-riprendi"
                        onClick={(e) => { if (suona) { e.preventDefault(); suona(riprendi.t, { da: 'riprendi', playlist: null, da_secondo: riprendi.secondo }); } }}>
                        <div className="oggi-cover" style={{ minHeight: 120 }}>{riprendi.t.cover_url && <img src={riprendi.t.cover_url} alt="" />}
                          <Cuore on={favorites.includes(riprendi.t.slug)} onClick={() => toggleFavorite(riprendi.t.slug)} titolo={riprendi.t.title} testid="casa-riprendi-cuore" />
                        </div>
                        <div className="oggi-corpo">
                          <span className="etichetta">Riprendi da dove eri</span>
                          <h3>{riprendi.t.title}</h3>
                          <span className="body">{fmtMinSec(riprendi.secondo)} di {fmtMin(riprendi.t.duration_sec)}{riprendi.t.guida_nome || riprendi.t.operator?.name ? ` · ${riprendi.t.guida_nome || riprendi.t.operator?.name}` : ''}</span>
                          <div style={{ marginTop: 'auto', paddingTop: 10 }}><span className="casa-cta">▶ Riprendi</span></div>
                        </div>
                      </Link>
                    )}
                    {recenti.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }}>Ascolti recenti</h2>
                        <div className="riga" data-testid="casa-recenti">
                          {recenti.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('recenti')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                        </div>
                      </>
                    )}
                    {preferite.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }} id="preferite">Le tue preferite</h2>
                        <div className="riga" data-testid="casa-preferite">
                          {preferite.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('preferiti')} fav onCuore={toggleFavorite} />)}
                        </div>
                      </>
                    )}
                    {playlistSalvate.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }}>Playlist salvate</h2>
                        <div className="riga" data-testid="casa-playlist-salvate">
                          {playlistSalvate.map((p) => <CardPlaylist key={p.id} p={p} fav onCuore={pref.togglePlaylist} />)}
                        </div>
                      </>
                    )}
                  </section>
                )}
                <Riga id="per-iniziare" titolo="Per iniziare" sub="Dieci minuti o meno." tutteN={tutte.filter((t) => (t.duration_sec || 0) <= 10 * 60).length} onTutte={() => setVista({ titolo: 'Per iniziare', items: tutte.filter((t) => (t.duration_sec || 0) <= 10 * 60) })}>
                  {brevi.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="novita" titolo="Novità" tutteN={tutte.length} onTutte={() => setVista({ titolo: 'Novità', items: tutte })}>
                  {novita.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="piu-ascoltate" titolo="Le più ascoltate" tutteN={tutte.filter((t) => t.plays_total > 0).length} onTutte={() => setVista({ titolo: 'Le più ascoltate', items: [...tutte].filter((t) => t.plays_total > 0).sort((a, b) => b.plays_total - a.plays_total) })}>
                  {piuAscoltate.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                {categoriePresenti.map((c) => (
                  <Riga key={c.slug} id={`cat-${c.slug}`} titolo={c.label} sub={c.descrizione || undefined} tutteN={tutte.filter((t) => t.categoria === c.slug).length} onTutte={() => setIntent(c.slug)}>
                    {tutte.filter((t) => t.categoria === c.slug).slice(0, 12).map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                  </Riga>
                ))}
                <Riga id="con-la-voce" titolo="Con la voce" tutteN={tutte.filter((t) => t.has_voce).length} onTutte={() => setVoce('con')}>
                  {conVoce.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="solo-suono" titolo="Solo suono" tutteN={tutte.filter((t) => !t.has_voce).length} onTutte={() => setVoce('senza')}>
                  {soloSuono.map((t) => <CardMeditazione key={t.slug} t={t} {...propsCard('casa')} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
              </>
            )}
          </>
        )}
        <div style={{ marginTop: 28 }}><SafetyLine onOpen={() => setSafety(true)} /></div>
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/">← Torna su Aurya</a><a href="/sound">Il suono</a><a href="/blog">Magazine</a><a href="/newsletter">Il Cerchio</a>
      </footer>

      {/* ── la barra in basso, solo telefono ── */}
      <nav className="casa-barra" aria-label="Le meditazioni" data-testid="casa-barra">
        <button type="button" className={attiva === 'esplora' ? 'on' : ''} onClick={() => { setAttiva('esplora'); setVista(null); setQ(''); setIntent(''); setDurata(''); setVoce(''); window.scrollTo({ top: 0, behavior: 'smooth' }); }}><Icona d={ICONE.esplora} />Esplora</button>
        <button type="button" className={attiva === 'playlist' ? 'on' : ''} onClick={() => vaiA('playlist')}><Icona d={ICONE.playlist} />Playlist</button>
        <button type="button" className={attiva === 'cerca' ? 'on' : ''} data-testid="casa-barra-cerca" onClick={() => { setAttiva('cerca'); setCercaAperta(true); }}><Icona d={ICONE.cerca} />Cerca</button>
        <button type="button" className={attiva === 'tuo-spazio' ? 'on' : ''} data-testid="casa-barra-tuoi"
          onClick={() => (hasAccount ? vaiA('tuo-spazio') : setHeartAsk(true))}><Icona d={ICONE.preferite} />I tuoi</button>
        <a href="/sound/impara"><Icona d={ICONE.impara} />Impara</a>
      </nav>

      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      <InvitoAccount aperto={heartAsk} onChiudi={() => setHeartAsk(false)} onDentro={pref.dopoAccount} />
      {/* MR3 — la barra, il foglio e il sipario vivono DENTRO il .fqz (gli stili sono scoped) */}
      <LettoreBarra />
      <SchedaMeditazione />
      {L?.curtain}
    </div>
  );
}
