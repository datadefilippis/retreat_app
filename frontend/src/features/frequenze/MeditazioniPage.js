/**
 * Frequenze by Aurya — la vetrina delle meditazioni (FQ3, 18/8/2026).
 *
 * /meditazioni — TUTTE le sessioni pubblicate dagli operatori, in un
 * posto solo. La vetrina e' l'incentivo (decisione founder): senza
 * sblocco si vede SOLO lo schermo d'invito — iscriviti alla Lettera o
 * entra con l'account Aurya. Lo sblocco e' verificato server-side
 * (il catalogo risponde 403 senza prova): niente tende trasparenti.
 *
 * Preferiti: il cuore vive sull'account Aurya. Chi e' dentro solo via
 * Lettera vede il cuore come invito a creare l'account.
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/client';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import { frequenciesAPI } from '../../api/frequencies';
import { SafetyCurtain, SafetyLine } from './SafetyCurtain';
import './frequenze.css';

const UNLOCK_STORE = 'fqz_catalog_unlock';   // {email, token} iscritto Lettera
const INTENTS = {
  dormire: 'Dormire', meditare: 'Meditare', rilassare: 'Rilassare',
  concentrare: 'Concentrare', elaborare: 'Elaborare', energizzare: 'Energizzare',
};
const fmt = (s) => {
  s = Math.max(0, Math.round(s || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};
const storedUnlock = () => {
  try { return JSON.parse(localStorage.getItem(UNLOCK_STORE) || 'null'); }
  catch { return null; }
};

export default function MeditazioniPage() {
  const navigate = useNavigate();
  const hasAccount = !!localStorage.getItem(PLATFORM_TOKEN_KEY);
  const [items, setItems] = useState(null);      // null = non caricato
  const [locked, setLocked] = useState(false);
  const [teaserCount, setTeaserCount] = useState(0);
  const [intent, setIntent] = useState('');
  const [favorites, setFavorites] = useState([]); // slugs
  const [heartAsk, setHeartAsk] = useState(false);
  const [safety, setSafety] = useState(false);      // SF — lettura su richiesta
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const loadCatalog = async () => {
    try {
      let r;
      if (hasAccount) {
        // il Bearer platform sblocca da solo (verificato dal server)
        r = await platformApi.get('/frequencies/catalog');
      } else {
        r = await frequenciesAPI.getCatalog(storedUnlock());
      }
      setItems(r.data.items || []);
      setLocked(false);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setLocked(true);
      setItems([]);
      setTeaserCount(detail?.tracks_count ?? 0);
      if (detail?.error !== 'locked') setMsg('');
    }
  };
  const loadFavorites = async () => {
    if (!hasAccount) return;
    try { setFavorites((await platformApi.get('/frequencies/favorites')).data.slugs || []); }
    catch { /* preferiti non bloccanti */ }
  };
  useEffect(() => { loadCatalog(); loadFavorites(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe = async (e) => {
    e.preventDefault();
    if (!consent) { setMsg('Serve il consenso alla Lettera'); return; }
    setBusy(true); setMsg('');
    try {
      await api.post('/public/newsletter/subscribe', {
        email, consent: true, language: 'it',
        source: 'meditazioni', wants_experiences: true,
      });
      const r = await frequenciesAPI.catalogUnlock(email);
      localStorage.setItem(UNLOCK_STORE, JSON.stringify(r.data));
      localStorage.setItem('fqz_listener_ok', '1'); // il player non richiede due volte
      await loadCatalog();
    } catch (err) {
      setMsg(err?.response?.data?.detail || 'Iscrizione non riuscita, riprova');
    } finally { setBusy(false); }
  };

  const toggleFavorite = async (slug) => {
    if (!hasAccount) { setHeartAsk(true); return; }
    const isFav = favorites.includes(slug);
    setFavorites((f) => (isFav ? f.filter((s) => s !== slug) : [...f, slug]));
    try {
      if (isFav) await platformApi.delete(`/frequencies/favorites/${slug}`);
      else await platformApi.put(`/frequencies/favorites/${slug}`);
    } catch { loadFavorites(); }
  };

  const shown = (items || []).filter((t) => !intent || t.intent === intent);
  const intentsPresent = [...new Set((items || []).map((t) => t.intent).filter(Boolean))];

  /* ── schermo d'invito (catalogo bloccato) ── */
  if (locked) {
    return (
      <div className="fqz" data-testid="fqz-meditazioni-locked">
        <main style={{ maxWidth: 680, paddingTop: 40 }}>
          <header style={{ display: 'block', textAlign: 'center' }}>
            <h1>Le <em>meditazioni</em> di Aurya</h1>
            <div className="sub" style={{ marginTop: 6 }}>
              sessioni vibrazionali composte dagli operatori della rete
            </div>
          </header>
          <section className="bib" style={{ textAlign: 'center', marginTop: 10 }}>
            <p style={{ fontSize: 15, lineHeight: 1.7 }}>
              {teaserCount > 0
                ? <>Qui dentro {teaserCount === 1 ? "c'è una sessione composta" : `ci sono ${teaserCount} sessioni composte`} dagli operatori di Aurya — per dormire, meditare, rilassarsi, concentrarsi.</>
                : <>Qui vivranno le sessioni composte dagli operatori di Aurya — per dormire, meditare, rilassarsi, concentrarsi.</>}
              {' '}<b>L'ascolto è riservato a chi fa parte del cerchio</b>: chi riceve
              la Lettera o ha un account Aurya.
            </p>
            <form onSubmit={subscribe} style={{ maxWidth: 440, margin: '18px auto 0' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input type="email" required value={email} placeholder="la tua email"
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ flex: 1, minWidth: 200 }} />
                <button type="submit" className="primary" disabled={busy}>
                  {busy ? 'Un attimo…' : 'Iscriviti e sblocca'}
                </button>
              </div>
              <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start',
                              fontSize: 12, color: 'var(--dim)', marginTop: 10,
                              textAlign: 'left', cursor: 'pointer' }}>
                <input type="checkbox" checked={consent}
                  onChange={(e) => setConsent(e.target.checked)} />
                <span>Acconsento a ricevere la Lettera di Aurya — pratiche,
                  ritiri e nuove meditazioni, senza rumore. Disiscrizione in un
                  click. <a href="/privacy" target="_blank" rel="noreferrer"
                    style={{ color: 'var(--water)' }}>Privacy</a></span>
              </label>
            </form>
            {msg && <p style={{ color: 'var(--alert)', fontSize: 12, marginTop: 10 }}>{msg}</p>}
            <p style={{ fontSize: 13, color: 'var(--dim)', marginTop: 18 }}>
              Sei già iscritto alla Lettera?{' '}
              <button type="button" className="readmore" style={{ display: 'inline' }}
                onClick={async () => {
                  if (!email) { setMsg('Scrivi la tua email qui sopra e ripremi'); return; }
                  setBusy(true); setMsg('');
                  try {
                    const r = await frequenciesAPI.catalogUnlock(email);
                    localStorage.setItem(UNLOCK_STORE, JSON.stringify(r.data));
                    await loadCatalog();
                  } catch (err) {
                    setMsg(err?.response?.data?.detail || 'Email non riconosciuta');
                  } finally { setBusy(false); }
                }}>Sblocca con la tua email</button>
            </p>
            <p style={{ fontSize: 13, color: 'var(--dim)', marginTop: 8 }}>
              Hai un account Aurya?{' '}
              <a href="/account/accedi?next=/meditazioni"
                style={{ color: 'var(--water)' }}>Accedi</a>
              {' '}· non ce l'hai?{' '}
              <a href="/account/accedi?next=/meditazioni"
                style={{ color: 'var(--water)' }}>Crealo gratis</a>
            </p>
          </section>
        </main>
      </div>
    );
  }

  /* ── catalogo sbloccato ── */
  return (
    <div className="fqz" data-testid="fqz-meditazioni">
      <header>
        <div>
          <h1>Le <em>meditazioni</em> di Aurya</h1>
          <div className="sub">sessioni vibrazionali degli operatori della rete</div>
        </div>
        {hasAccount && (
          <button type="button" className="backcard"
            onClick={() => navigate('/account')}>
            <span className="bc-ic">♥</span>
            <span>
              <span className="bc-t">Le mie preferite</span><br />
              <span className="bc-s">nel tuo account</span>
            </span>
          </button>
        )}
      </header>
      <main>
        <section className="bib">
          {items === null ? null : items.length === 0 ? (
            <div className="emptycreate">
              <p>Ancora nessuna meditazione pubblicata: gli operatori stanno componendo. Torna presto.</p>
            </div>
          ) : (
            <>
              {intentsPresent.length > 1 && (
                <div className="tabs">
                  <div className="tabgroup">
                    <div className="tabgroup-row">
                      <button type="button" className={`tab tab-sound${intent === '' ? ' on' : ''}`}
                        onClick={() => setIntent('')}>Tutte</button>
                      {intentsPresent.map((i) => (
                        <button key={i} type="button"
                          className={`tab tab-sound${intent === i ? ' on' : ''}`}
                          onClick={() => setIntent(i)}>{INTENTS[i] || i}</button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div className="cards" data-testid="fq-catalog-cards">
                {shown.map((t) => (
                  <div key={t.slug} className="card">
                    <div className="head">
                      <h3>{t.title}</h3>
                      <button type="button" title={favorites.includes(t.slug)
                        ? 'Togli dalle preferite' : 'Salva tra le preferite'}
                        onClick={() => toggleFavorite(t.slug)}
                        style={{ border: 'none', background: 'none', fontSize: 16, padding: '0 2px',
                                 color: favorites.includes(t.slug) ? 'var(--alert)' : 'var(--dimmer)' }}>
                        {favorites.includes(t.slug) ? '♥' : '♡'}
                      </button>
                    </div>
                    {t.intent && <div className="hz">{INTENTS[t.intent] || t.intent}</div>}
                    <div className="uso">
                      {fmt(t.duration_sec)} · {t.operator?.name}
                      {t.plays_total > 0 && ` · ${t.plays_total} ascolti`}
                    </div>
                    {t.description && <div className="body">{t.description.slice(0, 120)}</div>}
                    <div className="foot">
                      {t.operator?.slug && (
                        <Link to={`/o/${t.operator.slug}`} className="add"
                          style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                          Chi la firma
                        </Link>
                      )}
                      <Link to={`/frequenze/${t.slug}`} className="live"
                        style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                        Ascolta
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          {/* SF — stesso testo di tutto Aurya Sound, da content/safety.js */}
          <SafetyLine onOpen={() => setSafety(true)} />
        </section>
      </main>

      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      {heartAsk && (
        <div className="gate" onClick={() => setHeartAsk(false)}>
          <div className="gatebox" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <h2>Le preferite vivono nel tuo account</h2>
            <p>Per salvare una meditazione e ritrovarla quando vuoi serve un
              account Aurya — gratuito, ed è lo stesso con cui segui prenotazioni
              e Passaporto.</p>
            <div className="gatefoot" style={{ gap: 8 }}>
              <button type="button" className="primary"
                onClick={() => { window.location.href = '/account/accedi?next=/meditazioni'; }}>
                Crea il tuo account
              </button>
              <button type="button" onClick={() => setHeartAsk(false)}>Non ora</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
