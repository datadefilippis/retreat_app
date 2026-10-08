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
import { SOUND_PIU_ATTIVO } from '../stato';
import { prova, emailDellaProva, migraVecchieChiavi } from '../../../lib/cerchio';
import { creaAccount } from '../../../utils/authLinks';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
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

const Cuore = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.2S5.6 16 3.2 12.4C1.1 9.3 2.7 5.4 6 5.4c2 0 3.1 1 4.2 2.5.7 1 .9 1 1.6 0C12.9 6.4 14 5.4 16 5.4c3.3 0 4.9 3.9 2.8 7C16.4 16 12 20.2 12 20.2z" /></svg>);

/** la card di una meditazione: copertina (o velo del tono), durata, titolo, chi guida */
export function CardMeditazione({ t, da = 'casa', playlist = null, fav = false, onCuore = null }) {
  const href = `/frequenze/${t.slug}?da=${da}${playlist ? `&playlist=${encodeURIComponent(playlist)}` : ''}`;
  return (
    <div className={`mcard tono-${TONI[t.intent] || 'oro'}`} data-testid="casa-card">
      <Link to={href} className="mcover" aria-label={`Ascolta ${t.title}`}>
        {t.cover_url && <img src={t.cover_url} alt="" loading="lazy" />}
        {t.accesso === 'piu' && <span className="mpiu" title={SOUND_PIU_ATTIVO ? 'Riservata al Più' : 'Presto nel Più: oggi la ascolti col Cerchio'}>{SOUND_PIU_ATTIVO ? 'PIÙ' : 'PRESTO NEL PIÙ'}</span>}
        <span className="mdurata">{fmtMin(t.duration_sec)}</span>
      </Link>
      {onCuore && (
        <button type="button" className={`mcuore${fav ? ' on' : ''}`} aria-pressed={fav}
          title={fav ? 'Togli dalle preferite' : 'Salva tra le preferite'} onClick={() => onCuore(t.slug)}><Cuore /></button>
      )}
      <Link to={href} className="mcorpo">
        <h3>{t.title}</h3>
        <span className="mmeta">
          {t.intent ? `${INTENTI[t.intent] || t.intent} · ` : ''}{t.guida_nome || t.operator?.name}{t.has_voce ? ' · con la voce' : ''}
        </span>
      </Link>
    </div>
  );
}

export function CardPlaylist({ p }) {
  return (
    <Link to={`/meditazioni/playlist/${p.slug}`} className="mcard playlist tono-oro" data-testid="casa-playlist-card">
      <span className="mcover">
        {p.cover_url && <img src={p.cover_url} alt="" loading="lazy" />}
        {p.accesso === 'piu' && <span className="mpiu">PIÙ</span>}
        <span className="mconta">{p.tracce_count} {p.tracce_count === 1 ? 'meditazione' : 'meditazioni'} · {fmtMin(p.duration_sec)}</span>
      </span>
      <span className="mcorpo"><h3>{p.title}</h3>{p.description && <span className="mmeta">{p.description.slice(0, 90)}</span>}</span>
    </Link>
  );
}

/* SN4 — la card di un Percorso (corso con lezioni Suono): porta alla pagina del corso */
export function CardPercorso({ c }) {
  const prezzo = c.price != null ? `${Number(c.price).toFixed(0)} €` : '';
  return (
    <a href={c.url} className="mcard tono-oro" data-testid="casa-percorso-card">
      <span className="mcover">
        {c.image_url && <img src={c.image_url} alt="" loading="lazy" />}
        <span className="mpiu" style={{ background: 'rgba(47,87,73,.92)', color: '#fff' }}>PERCORSO</span>
        {prezzo && <span className="mdurata">{prezzo}</span>}
      </span>
      <span className="mcorpo">
        <h3>{c.name}</h3>
        <span className="mmeta">{c.suono_count} {c.suono_count === 1 ? 'meditazione' : 'meditazioni'} · {c.lezioni_count} lezioni · {c.org?.name}</span>
      </span>
    </a>
  );
}

function Riga({ id, titolo, sub, children, griglia = false }) {
  const n = React.Children.count(children);
  if (!n) return null;
  return (
    <section className="casa-sezione" id={id} data-testid={`casa-riga-${id}`}>
      <h2>{titolo}</h2>
      {sub && <p className="casa-sub">{sub}</p>}
      <div className={`riga${griglia ? ' griglia' : ''}`}>{children}</div>
    </section>
  );
}

const Icona = ({ d }) => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d={d} /></svg>);
const ICONE = {
  esplora: 'M3 12h18M3 6h18M3 18h12',
  playlist: 'M4 6h12M4 12h12M4 18h8M18 10v8m0-8l3 2',
  cerca: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16l-4.3-4.3',
  preferite: 'M12 20.2S5.6 16 3.2 12.4C1.1 9.3 2.7 5.4 6 5.4c2 0 3.1 1 4.2 2.5.7 1 .9 1 1.6 0C12.9 6.4 14 5.4 16 5.4c3.3 0 4.9 3.9 2.8 7C16.4 16 12 20.2 12 20.2z',
  impara: 'M4 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4zM20 5h-7a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h8z',
};

export default function MeditazioniCasa() {
  const navigate = useNavigate();
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
  const [favorites, setFavorites] = useState([]);
  const [heartAsk, setHeartAsk] = useState(false);
  const [safety, setSafety] = useState(false);
  const [q, setQ] = useState('');
  const [intent, setIntent] = useState('');
  const [durata, setDurata] = useState('');       // '' | 'breve' | 'media' | 'lunga'
  const [voce, setVoce] = useState('');           // '' | 'con' | 'senza'
  const [attiva, setAttiva] = useState('esplora');
  const cercaRef = useRef(null);

  const carica = async () => {
    try {
      let r;
      const prima = async (url) => (hasAccount ? platformApi.get(url) : frequenciesAPI.getCatalog(prova(), null));
      r = await prima('/frequencies/catalog');
      let tutte = r.data.items || [];
      let before = r.data.next_before;
      // la casa vuole tutto il catalogo in mano (le righe si calcolano qui): si pagina fino in fondo
      for (let giri = 0; before && giri < 10; giri += 1) {
        const rr = hasAccount ? await platformApi.get('/frequencies/catalog', { params: { before } }) : await frequenciesAPI.getCatalog(prova(), before);
        tutte = [...tutte, ...(rr.data.items || [])]; before = rr.data.next_before;
      }
      setItems(tutte); setLocked(false);
      try {
        const pr = hasAccount ? await platformApi.get('/frequencies/playlists') : await frequenciesAPI.playlists.pubbliche(prova());
        setPlaylists(pr.data.items || []);
      } catch { setPlaylists([]); }
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setLocked(true); setItems([]); setTeaserCount(detail?.tracks_count ?? 0);
    }
  };
  /* SN3 — il tuo spazio: «riprendi da dove eri» e gli ascolti recenti vivono
     sull'account (la persistenza e' dell'account, decisione del piano) */
  const [spazio, setSpazio] = useState({ riprendi: null, recenti: [] });
  const caricaSpazio = async () => {
    if (!hasAccount) return;
    try {
      const me = (await platformApi.get('/platform/me')).data;
      setSpazio({ riprendi: me.sound_riprendi || null, recenti: me.sound_recenti || [] });
    } catch { /* non bloccante */ }
  };
  const caricaPreferite = async () => {
    if (!hasAccount) return;
    try { setFavorites((await platformApi.get('/frequencies/favorites')).data.slugs || []); } catch { /* non bloccante */ }
  };
  useEffect(() => { migraVecchieChiavi().finally(() => { carica(); caricaPreferite(); caricaSpazio(); }); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleFavorite = async (slug) => {
    if (!hasAccount) { setHeartAsk(true); return; }
    const isFav = favorites.includes(slug);
    setFavorites((f) => (isFav ? f.filter((s) => s !== slug) : [...f, slug]));
    try { if (isFav) await platformApi.delete(`/frequencies/favorites/${slug}`); else await platformApi.put(`/frequencies/favorites/${slug}`); }
    catch { caricaPreferite(); }
  };

  // ── le righe, dal catalogo ──
  const tutte = useMemo(() => items || [], [items]);
  const cercando = !!(q.trim() || intent || durata || voce);
  const filtrate = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return tutte.filter((t) => {
      if (intent && t.intent !== intent) return false;
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
  const intentiPresenti = Object.keys(INTENTI).filter((i) => tutte.some((t) => t.intent === i));
  const preferite = tutte.filter((t) => favorites.includes(t.slug));
  const perSlug = Object.fromEntries(tutte.map((t) => [t.slug, t]));
  const recenti = (spazio.recenti || []).map((s) => perSlug[s]).filter(Boolean).slice(0, 12);
  const riprendi = spazio.riprendi && perSlug[spazio.riprendi.slug] && spazio.riprendi.secondo > 5
    ? { t: perSlug[spazio.riprendi.slug], secondo: spazio.riprendi.secondo } : null;

  const vaiA = (id) => { setAttiva(id); const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); };

  if (locked) return <SogliaCerchio teaserCount={teaserCount} onSbloccato={() => carica()} />;

  return (
    <div className="fqz med casa" data-testid="casa-meditazioni">
      <SoundTopbar firma="Meditazioni" qui="/meditazioni" />
      <header>
        <div>
          <h1>Le <em>meditazioni</em> di Aurya</h1>
          <div className="sub">scegli, ascolta, riprendi quando vuoi</div>
        </div>
        {hasAccount && (
          <button type="button" className="backcard" onClick={() => navigate('/account')}>
            <span className="bc-ic">♥</span>
            <span><span className="bc-t">Il tuo account</span><br /><span className="bc-s">preferite e corsi</span></span>
          </button>
        )}
      </header>
      <main id="esplora">
        {items === null ? null : tutte.length === 0 ? (
          <div className="emptycreate"><p>Ancora nessuna meditazione pubblicata: le prime stanno arrivando. Intanto puoi conoscere <Link to="/sound" style={{ color: 'var(--water)' }}>il suono</Link>.</p></div>
        ) : (
          <>
            {/* ── di oggi ── */}
            {!cercando && (playlistVetrina || vetrina) && (
              <section className="casa-sezione" style={{ marginTop: 6 }} data-testid="casa-oggi">
                <div className={`oggi tono-${TONI[vetrina?.intent] || 'oro'}`}>
                  <div className="oggi-cover">{(playlistVetrina?.cover_url || vetrina?.cover_url) && <img src={playlistVetrina?.cover_url || vetrina.cover_url} alt="" />}</div>
                  <div className="oggi-corpo">
                    <span className="etichetta">{playlistVetrina ? 'La playlist di oggi' : 'Di oggi'}</span>
                    <h3>{playlistVetrina ? playlistVetrina.title : vetrina.title}</h3>
                    <span className="body">{playlistVetrina
                      ? `${playlistVetrina.tracce_count} meditazioni · ${fmtMin(playlistVetrina.duration_sec)}${playlistVetrina.description ? ` · ${playlistVetrina.description.slice(0, 120)}` : ''}`
                      : `${vetrina.intent ? `${INTENTI[vetrina.intent]} · ` : ''}${fmtMin(vetrina.duration_sec)} · ${vetrina.guida_nome || vetrina.operator?.name || ''}${vetrina.description ? ` · ${vetrina.description.slice(0, 120)}` : ''}`}</span>
                    <div style={{ marginTop: 'auto', paddingTop: 10 }}>
                      {playlistVetrina
                        ? <Link to={`/meditazioni/playlist/${playlistVetrina.slug}`} className="casa-cta" data-testid="casa-oggi-ascolta">Apri la playlist</Link>
                        : <Link to={`/frequenze/${vetrina.slug}?da=vetrina`} className="casa-cta" data-testid="casa-oggi-ascolta">▶ Ascolta</Link>}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* ── cerca e filtri ── */}
            <div className="cerca" id="cerca" data-testid="casa-cerca">
              <input ref={cercaRef} type="search" value={q} placeholder="Cerca una meditazione, un tema, chi la guida" aria-label="Cerca" onChange={(e) => setQ(e.target.value)} />
            </div>
            <div className="filtri" data-testid="casa-filtri">
              <button type="button" className={`filtro${!intent ? ' on' : ''}`} onClick={() => setIntent('')}>Tutte</button>
              {intentiPresenti.map((i) => <button key={i} type="button" className={`filtro${intent === i ? ' on' : ''}`} onClick={() => setIntent(intent === i ? '' : i)}>{INTENTI[i]}</button>)}
              <span style={{ width: 8 }} />
              {[['breve', '≤ 10 min'], ['media', '10–20 min'], ['lunga', '20+ min']].map(([v, l]) => (
                <button key={v} type="button" className={`filtro${durata === v ? ' on' : ''}`} onClick={() => setDurata(durata === v ? '' : v)}>{l}</button>))}
              <span style={{ width: 8 }} />
              {[['con', 'Con la voce'], ['senza', 'Solo suono']].map(([v, l]) => (
                <button key={v} type="button" className={`filtro${voce === v ? ' on' : ''}`} onClick={() => setVoce(voce === v ? '' : v)}>{l}</button>))}
            </div>

            {cercando ? (
              <Riga id="risultati" titolo={`${filtrate.length} ${filtrate.length === 1 ? 'meditazione' : 'meditazioni'}`} griglia>
                {filtrate.map((t) => <CardMeditazione key={t.slug} t={t} da="cerca" fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
              </Riga>
            ) : (
              <>
                <Riga id="percorsi" titolo="Percorsi" sub="Corsi con le meditazioni dentro: si comprano nell'Accademia, si ascoltano qui.">
                  {percorsi.map((c) => <CardPercorso key={c.product_id} c={c} />)}
                </Riga>
                <Riga id="playlist" titolo="Playlist" sub="Raccolte curate, da ascoltare in fila.">
                  {playlists.map((p) => <CardPlaylist key={p.id} p={p} />)}
                </Riga>
                {/* ── SN3: il tuo spazio (con l'account): riprendi · recenti · preferite ── */}
                {hasAccount && (riprendi || recenti.length > 0 || preferite.length > 0) && (
                  <section className="casa-sezione" id="tuo-spazio" data-testid="casa-tuo-spazio">
                    <h2>Il tuo spazio</h2>
                    <p className="casa-sub">Dove eri rimasta o rimasto, cosa hai ascoltato, cosa hai salvato.</p>
                    {riprendi && (
                      <Link to={`/frequenze/${riprendi.t.slug}?da=riprendi&t=${riprendi.secondo}`} className={`oggi tono-${TONI[riprendi.t.intent] || 'oro'}`}
                        style={{ textDecoration: 'none', color: 'inherit', marginBottom: 18 }} data-testid="casa-riprendi">
                        <div className="oggi-cover" style={{ minHeight: 120 }}>{riprendi.t.cover_url && <img src={riprendi.t.cover_url} alt="" />}</div>
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
                          {recenti.map((t) => <CardMeditazione key={t.slug} t={t} da="recenti" fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                        </div>
                      </>
                    )}
                    {preferite.length > 0 && (
                      <>
                        <h2 style={{ fontSize: 18, marginTop: 10 }} id="preferite">Le tue preferite</h2>
                        <div className="riga" data-testid="casa-preferite">
                          {preferite.map((t) => <CardMeditazione key={t.slug} t={t} da="preferiti" fav onCuore={toggleFavorite} />)}
                        </div>
                      </>
                    )}
                  </section>
                )}
                <Riga id="per-iniziare" titolo="Per iniziare" sub="Dieci minuti o meno.">
                  {brevi.map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="novita" titolo="Novità">
                  {novita.map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="piu-ascoltate" titolo="Le più ascoltate">
                  {piuAscoltate.map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                {intentiPresenti.map((i) => (
                  <Riga key={i} id={`per-${i}`} titolo={`Per ${INTENTI[i].toLowerCase()}`}>
                    {tutte.filter((t) => t.intent === i).slice(0, 12).map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                  </Riga>
                ))}
                <Riga id="con-la-voce" titolo="Con la voce">
                  {conVoce.map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
                </Riga>
                <Riga id="solo-suono" titolo="Solo suono">
                  {soloSuono.map((t) => <CardMeditazione key={t.slug} t={t} fav={favorites.includes(t.slug)} onCuore={toggleFavorite} />)}
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
        <button type="button" className={attiva === 'esplora' ? 'on' : ''} onClick={() => { setAttiva('esplora'); window.scrollTo({ top: 0, behavior: 'smooth' }); }}><Icona d={ICONE.esplora} />Esplora</button>
        <button type="button" className={attiva === 'playlist' ? 'on' : ''} onClick={() => vaiA('playlist')}><Icona d={ICONE.playlist} />Playlist</button>
        <button type="button" className={attiva === 'cerca' ? 'on' : ''} onClick={() => { vaiA('cerca'); setTimeout(() => cercaRef.current?.focus(), 400); }}><Icona d={ICONE.cerca} />Cerca</button>
        <button type="button" className={attiva === 'tuo-spazio' ? 'on' : ''} data-testid="casa-barra-tuoi"
          onClick={() => (hasAccount ? vaiA('tuo-spazio') : setHeartAsk(true))}><Icona d={ICONE.preferite} />I tuoi</button>
        <a href="/sound/impara"><Icona d={ICONE.impara} />Impara</a>
      </nav>

      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      {heartAsk && (
        <div className="gate" onClick={() => setHeartAsk(false)}>
          <div className="gatebox" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <h2>Il tuo spazio vive nel tuo account</h2>
            <p>Preferite, ascolti recenti e «riprendi da dove eri» si ritrovano su ogni telefono con un account Aurya, gratuito: lo stesso di corsi e prenotazioni.</p>
            <div className="gatefoot" style={{ gap: 8 }}>
              <button type="button" className="primary" onClick={() => { window.location.href = creaAccount(emailDellaProva() || '', '/meditazioni'); }}>Crea il tuo account</button>
              <button type="button" onClick={() => setHeartAsk(false)}>Non ora</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
