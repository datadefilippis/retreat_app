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
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import { frequenciesAPI } from '../../api/frequencies';
import { SafetyCurtain, SafetyLine } from './SafetyCurtain';
import { creaAccount, entraInAurya } from '../../utils/authLinks';
import { prova, emailDellaProva, sblocca, iscriviESblocca, migraVecchieChiavi } from '../../lib/cerchio';
import './frequenze.css';
import './meditazioni.css';
import SoundTopbar from './SoundTopbar';
import TriggerStudio from './TriggerStudio';

/* il cuore disegnato (founder 26/8): un gesto, non un carattere */
const Cuore = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 20.2S5.6 16 3.2 12.4C1.1 9.3 2.7 5.4 6 5.4c2 0 3.1 1 4.2 2.5.7 1 .9 1 1.6 0C12.9 6.4 14 5.4 16 5.4c3.3 0 4.9 3.9 2.8 7C16.4 16 12 20.2 12 20.2z" />
  </svg>
);

const INTENTS = {
  dormire: 'Dormire', meditare: 'Meditare', rilassare: 'Rilassare',
  concentrare: 'Concentrare', elaborare: 'Elaborare', energizzare: 'Energizzare',
};

/* founder 26/8 — ogni intento porta la sua tonalita' (famiglia di
   marca, versioni da fondo chiaro): un velo in testa alla carta e
   l'onda-firma. Il contrasto senza il kitsch. */
const TONI = {
  dormire: 'viola', elaborare: 'viola',
  meditare: 'salvia', concentrare: 'acqua',
  rilassare: 'oro', energizzare: 'oro',
};

/* l'onda-firma: una riga di suono disegnata, nel colore del tono */
const OndaFirma = () => (
  <svg className="med-onda" viewBox="0 0 120 12" aria-hidden="true"
    preserveAspectRatio="none">
    <path d="M0 6 C 10 0, 20 12, 30 6 S 50 0, 60 6 S 80 12, 90 6 S 110 0, 120 6" />
  </svg>
);
const fmt = (s) => {
  s = Math.max(0, Math.round(s || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
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
  const [ponteVia, setPonteVia] = useState(() => {
    try { return sessionStorage.getItem('aurya_ponte_via') === '1'; }
    catch { return false; }
  });

  /* ES4 — la vetrina e' paginata: il server manda al massimo 100
     tracce e un cursore (`next_before`). Prima era to_list(500): alla
     501esima le piu' vecchie sarebbero SPARITE in silenzio. */
  const [nextBefore, setNextBefore] = useState(null);
  const loadCatalog = async (before = null) => {
    try {
      let r;
      if (hasAccount) {
        // il Bearer platform sblocca da solo (verificato dal server)
        r = await platformApi.get('/frequencies/catalog',
          before ? { params: { before } } : {});
      } else {
        r = await frequenciesAPI.getCatalog(prova(), before);
      }
      setItems((prev) => before ? [...(prev || []), ...(r.data.items || [])]
                               : (r.data.items || []));
      setNextBefore(r.data.next_before || null);
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
  useEffect(() => {
    // SB1 — i browser con la vecchia coppia HMAC migrano alla prova unica
    migraVecchieChiavi().finally(() => { loadCatalog(); loadFavorites(); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* NL-septies (20/8) — una regola sola per tutti i contenuti
     riservati: la prima iscrizione si conferma dall'email (il clic
     prova che la casella e' tua), chi e' gia' confermato sblocca
     dichiarando l'indirizzo. Prima qui bastava scrivere un'email
     qualsiasi: il cancello si apriva senza conferma. */
  const [attesaConferma, setAttesaConferma] = useState(false);
  const subscribe = async (e) => {
    e.preventDefault();
    if (!consent) { setMsg('Serve il consenso alla Lettera'); return; }
    setBusy(true); setMsg('');
    try {
      const esito = await iscriviESblocca({
        email, source: 'meditazioni', returnTo: '/meditazioni',
      });
      if (esito === 'sbloccato') await loadCatalog();
      else setAttesaConferma(true);   // prima iscrizione: click nell'email
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
      <div className="fqz med" data-testid="fqz-meditazioni-locked">
        {/* MD (20/8) — le uscite: senza menu del sito, da qui non si
            tornava piu' indietro. Stesso rimedio di Aurya Sound. */}
        <SoundTopbar firma="Meditazioni" qui="/meditazioni" />
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
            {attesaConferma && (
              /* NL-septies — prima iscrizione: il cancello si apre col
                 clic nell'email, come per le guide del Magazine */
              <div className="warnbox" style={{ maxWidth: 440, margin: '18px auto 0', textAlign: 'left' }}
                data-testid="med-attesa-conferma">
                Ti abbiamo scritto: apri l’email e clicca il link di conferma.
                Il link ti riporta qui, con le meditazioni sbloccate.
              </div>
            )}
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
                    await sblocca(email);
                    await loadCatalog();
                  } catch (err) {
                    setMsg(err?.response?.data?.detail || 'Email non riconosciuta');
                  } finally { setBusy(false); }
                }}>Sblocca con la tua email</button>
            </p>
            {/* NL-octies (20/8, founder) — «Crealo gratis» portava alla
                schermata di ACCESSO e buttava via l'email appena
                scritta. Le due strade ora dicono ciascuna la sua, e si
                portano dietro l'indirizzo e il ritorno qui. */}
            <p style={{ fontSize: 13, color: 'var(--dim)', marginTop: 8 }}>
              Hai un account Aurya?{' '}
              <a href={entraInAurya(email, '/meditazioni')}
                data-testid="med-gate-accedi"
                style={{ color: 'var(--water)' }}>Accedi</a>
              {' '}· non ce l'hai?{' '}
              <a href={creaAccount(email, '/meditazioni')}
                data-testid="med-gate-crea"
                style={{ color: 'var(--water)' }}>Crealo gratis</a>
            </p>
          </section>
        </main>
        <footer className="fqzfoot" data-testid="fqz-foot">
          <a href="/">← Torna su Aurya</a>
          <a href="/sound">Aurya Sound</a>
          <a href="/blog">Magazine</a>
          <a href="/newsletter">La Lettera</a>
        </footer>
      </div>
    );
  }

  /* ── catalogo sbloccato ── */
  return (
    <div className="fqz med" data-testid="fqz-meditazioni">
      {/* MD (20/8) — le uscite: senza menu del sito, da qui non si
          tornava piu' indietro. Stesso rimedio di Aurya Sound. */}
      <SoundTopbar firma="Meditazioni" qui="/meditazioni" />

      {/* SB6 (20/8, founder) — l'iscritto fedele senza account e' a un
          passo dal finalizzare: l'invito vive dove lui e' gia' dentro,
          con l'email della prova, e si puo' congedare. */}
      {!hasAccount && prova() && !ponteVia && (
        <div className="warnbox" data-testid="ponte-account"
          style={{ maxWidth: 720, margin: '14px auto 0', display: 'flex',
                   gap: 10, alignItems: 'center', justifyContent: 'space-between',
                   flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13 }}>
            Vuoi ritrovare meditazioni, guide e preferite su ogni dispositivo?{' '}
            <a href={creaAccount(emailDellaProva(), '/meditazioni')}
              data-testid="ponte-account-crea"
              style={{ color: 'var(--water)' }}>Crea il tuo account</a> — un minuto.
          </span>
          <button type="button" className="ghost" data-testid="ponte-account-via"
            style={{ padding: '2px 8px', fontSize: 12 }}
            onClick={() => { setPonteVia(true);
              try { sessionStorage.setItem('aurya_ponte_via', '1'); } catch { /* ok */ } }}>
            Non ora
          </button>
        </div>
      )}
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
                {shown.map((t) => {
                  const fav = favorites.includes(t.slug);
                  return (
                    <div key={t.slug}
                      className={`card med-tono-${TONI[t.intent] || 'oro'}`}>
                      {/* founder 26/8 — il cuore e' un gesto disegnato */}
                      <button type="button" aria-pressed={fav}
                        className={`med-cuore${fav ? ' on' : ''}`}
                        title={fav ? 'Togli dalle preferite' : 'Salva tra le preferite'}
                        onClick={() => toggleFavorite(t.slug)}>
                        <Cuore />
                      </button>
                      {t.intent && (
                        <div className="med-intento">{INTENTS[t.intent] || t.intent}</div>
                      )}
                      <h3>{t.title}</h3>
                      <div className="med-dati">
                        {fmt(t.duration_sec)}
                        {t.plays_total > 0 && ` · ${t.plays_total} ascolti`}
                      </div>
                      <OndaFirma />
                      {t.description && <div className="body">{t.description.slice(0, 120)}</div>}
                      {/* founder 26/8 — la firma e' il NOME di chi l'ha
                          composta, non un'etichetta */}
                      <div className="med-piede">
                        {t.operator?.slug ? (
                          <Link to={`/o/${t.operator.slug}`} className="med-firma">
                            <i>di </i><b>{t.operator?.name}</b>
                          </Link>
                        ) : (
                          <span className="med-firma"><i>di </i><b>{t.operator?.name}</b></span>
                        )}
                        <Link to={`/frequenze/${t.slug}`} className="med-ascolta">
                          Ascolta
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
              {nextBefore && (
                <p style={{ textAlign: 'center', marginTop: 18 }}>
                  <button type="button" className="readmore"
                    data-testid="fqz-carica-altre"
                    onClick={() => loadCatalog(nextBefore)}>
                    Carica altre meditazioni
                  </button>
                </p>
              )}
            </>
          )}
          {/* SF — stesso testo di tutto Aurya Sound, da content/safety.js */}
          <SafetyLine onOpen={() => setSafety(true)} />
        </section>
      </main>
      {/* NV5 — il funnel professionale anche qui: chi ascolta le
          meditazioni degli altri e' spesso chi potrebbe comporle */}
      <main style={{ marginTop: 0 }}><TriggerStudio /></main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/">← Torna su Aurya</a>
        <a href="/sound">Aurya Sound</a>
        <a href="/blog">Magazine</a>
        <a href="/newsletter">La Lettera</a>
      </footer>

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
                onClick={() => { window.location.href = creaAccount(email, '/meditazioni'); }}>
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
