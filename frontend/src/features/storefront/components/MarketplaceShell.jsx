/**
 * MarketplaceShell — il guscio del marketplace (M1,
 * docs/MARKETPLACE_DESIGN_PLAN.md). "Dentro il marketplace non ti
 * perdi mai": header sticky + footer comuni su TUTTE le pagine lato
 * viaggiatore (directory, landing ritiro, profilo operatore, account).
 *
 * Il gemello lato negozio esiste già (StorefrontHeader/CategoryNav +
 * StoreContextNav): la landing indossa QUEL guscio con ?store=1 e
 * QUESTO in tutti gli altri casi.
 *
 * props:
 *   minimal  — header ridotto (solo logo+lucchetto): per il checkout,
 *              dove si converte e non si naviga
 *   noSearch — nasconde la scorciatoia ricerca (es. sulla directory
 *              stessa, che HA già la ricerca in hero)
 */
import React, { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BRAND_NAME, BRAND_MOTTO } from '../../../config/brand';
import { Search, Menu, X, Lock, Globe, Check, ChevronDown } from 'lucide-react';
import { persistMarketplaceLang, getMarketplaceLang } from '../../../hooks/useStorefrontLocale';
import api from '../../../api/client';

// S5 — destinazioni top nel footer (link programmatici): cache a livello
// modulo, il footer è su ogni pagina e non deve rifetchare a ogni nav.
let _destCache = null;

const LANGS = [
  { code: 'it', label: 'Italiano' },
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Français' },
];

// PL12 — esportato: riusato da splash e landing di pre-lancio (stessa
// UX lingua del resto del sito, stessa persistenza aurya_lang).
export function LangSwitcher() {
  const { t, i18n } = useTranslation('landings');
  const [open, setOpen] = React.useState(false);
  const boxRef = React.useRef(null);
  const cur = (i18n.language || 'it').slice(0, 2);

  // DS5 (founder 8/7) — un globo al posto della fila IT EN DE FR:
  // l'header respira, la scelta si apre solo quando serve.
  React.useEffect(() => {
    if (!open) return undefined;
    const close = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  // L1 — la scelta viene persistita (aurya_lang) e vince sui default
  // dello store in contesto marketplace: niente più flip di lingua
  // entrando in un prodotto o al checkout.
  const choose = (l) => {
    persistMarketplaceLang(l);
    i18n.changeLanguage(l);
    setOpen(false);
  };

  return (
    <div className="relative" ref={boxRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={t('marketplace.langFilterNote', {
          defaultValue: 'Scegli la lingua: vedrai i ritiri e le esperienze tenuti in quella lingua.',
        })}
        className="flex items-center gap-1 rounded-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-600 hover:border-primary hover:text-primary transition-colors"
      >
        <Globe className="h-4 w-4" aria-hidden />
        <span className="uppercase">{cur}</span>
        <ChevronDown className={`h-3 w-3 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>
      {open && (
        <ul role="listbox" aria-label="lingua"
            className="absolute right-0 mt-1.5 w-40 rounded-xl border border-gray-200 bg-white shadow-xl overflow-hidden z-50">
          {LANGS.map(l => (
            <li key={l.code}>
              <button
                type="button"
                role="option"
                aria-selected={cur === l.code}
                onClick={() => choose(l.code)}
                className={`w-full flex items-center justify-between px-3.5 py-2 text-sm transition-colors ${
                  cur === l.code ? 'text-[#376254] font-semibold bg-[#376254]/5' : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                {l.label}
                {cur === l.code && <Check className="h-4 w-4" aria-hidden />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// AN2 — il menu principale che mancava: le stesse voci su desktop
// (inline dopo il logo) e su mobile (pannello hamburger). Una sola
// definizione: chi aggiunge una superficie la aggiunge QUI.
const NAV_ITEMS = [
  { to: '/', key: 'marketplace.navRetreats', fallback: 'Ritiri' },
  { to: '/operatori', key: 'marketplace.navOperators', fallback: 'Organizzatori' },
  { to: '/destinazioni', key: 'marketplace.navDestinations', fallback: 'Destinazioni' },
  { to: '/blog', key: 'marketplace.navBlog', fallback: 'Blog' },
];

export default function MarketplaceShell({ children, minimal = false, noSearch = false }) {
  const { t, i18n } = useTranslation('landings');
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [destinations, setDestinations] = React.useState(_destCache || []);
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  useEffect(() => {
    if (_destCache) return;
    let mounted = true;
    api.get('/public/destinations')
      .then(res => {
        _destCache = (res.data?.items || []).slice(0, 4);
        if (mounted) setDestinations(_destCache);
      })
      .catch(() => { _destCache = []; });
    return () => { mounted = false; };
  }, []);

  // L1 — ogni superficie marketplace riafferma al mount la lingua del
  // viaggiatore: la scelta salvata (aurya_lang) o l'italiano, la faccia
  // di default della piattaforma. Copre sia il ritorno da una vetrina
  // negozio sia la navigazione SPA dall'admin (il cui AuthContext non
  // ri-scatta e lascerebbe la lingua dell'operatore). Sulle landing il
  // resolver dello store (PublicStorefrontShell, effetto padre → gira
  // dopo) resta l'ultima parola quando il negozio non offre la lingua.
  useEffect(() => {
    // S4 — ?lang= esplicito (deep-link, hreflang) VINCE e diventa la
    // preferenza: rende oneste le alternate ?lang=xx delle sitemap/head.
    let fromQuery = null;
    try {
      const q = (new URLSearchParams(window.location.search).get('lang') || '')
        .slice(0, 2).toLowerCase();
      if (['it', 'en', 'de', 'fr'].includes(q)) fromQuery = q;
    } catch { /* no-op */ }
    if (fromQuery) persistMarketplaceLang(fromQuery);
    const wanted = fromQuery || getMarketplaceLang() || 'it';
    if ((i18n.language || '').slice(0, 2) !== wanted) {
      i18n.changeLanguage(wanted);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 shrink-0" aria-label={BRAND_NAME}>
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-9 w-9 select-none" draggable={false} />
            <span className="font-brand font-medium uppercase tracking-[0.28em] text-lg leading-none text-[#8a7440] select-none">{BRAND_NAME}</span>
          </Link>

          {minimal ? (
            <span className="ml-auto text-xs text-gray-500 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5" aria-hidden /> {t('marketplace.securePayment', { defaultValue: 'Pagamento sicuro' })}
            </span>
          ) : (
            <>
              {/* AN2 — menu principale (desktop): gli aggregatori smettono
                  di essere scopribili solo dal footer */}
              <nav aria-label="principale" className="hidden lg:flex items-center gap-1 ml-2">
                {NAV_ITEMS.map((item) => {
                  const active = item.to === '/'
                    ? pathname === '/' || pathname.startsWith('/ritiri')
                    : pathname.startsWith(item.to);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      aria-current={active ? 'page' : undefined}
                      className={`rounded-full px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors ${
                        active
                          ? 'text-[#2c4f43] bg-[#376254]/10 font-semibold'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      }`}
                    >
                      {t(item.key, { defaultValue: item.fallback })}
                    </Link>
                  );
                })}
              </nav>

              {/* Scorciatoia ricerca — riporta alla directory (che ha i filtri) */}
              {!noSearch && (
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="hidden xl:flex items-center gap-2 rounded-full border border-gray-300 bg-white pl-4 pr-1.5 py-1 text-sm text-gray-500 hover:shadow-md transition-shadow whitespace-nowrap max-w-[240px]"
                >
                  <span className="truncate">{t('marketplace.searchShortcut', { defaultValue: 'Dove? · Quando? · Che ritiro?' })}</span>
                  <span className="rounded-full bg-primary text-white h-6 w-6 flex items-center justify-center shrink-0" aria-hidden>
                    <Search className="h-3.5 w-3.5" />
                  </span>
                </button>
              )}

              <div className="ml-auto flex items-center gap-2 sm:gap-3">
                <Link
                  to="/inizia"
                  className="hidden md:block text-xs font-medium text-gray-600 hover:text-gray-900 whitespace-nowrap"
                >
                  {t('marketplace.forOrganizers', { defaultValue: 'Sei un organizzatore?' })}
                </Link>
                <LangSwitcher />
                <Link
                  to="/account"
                  className="hidden sm:block rounded-full border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:border-primary hover:text-primary transition-colors whitespace-nowrap"
                >
                  {t('marketplace.myTrips', { defaultValue: 'Le mie esperienze' })}
                </Link>
                {/* AN2 — hamburger mobile: ricerca e CTA organizzatori non
                    spariscono più sotto i breakpoint */}
                <button
                  type="button"
                  onClick={() => setMobileNavOpen((o) => !o)}
                  aria-expanded={mobileNavOpen}
                  aria-label={mobileNavOpen
                    ? t('marketplace.navClose', { defaultValue: 'Chiudi menu' })
                    : t('marketplace.navMenu', { defaultValue: 'Menu' })}
                  className="lg:hidden rounded-full border border-gray-300 h-8 w-8 flex items-center justify-center text-gray-700 hover:border-primary"
                >
                  {mobileNavOpen ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
                </button>
              </div>
            </>
          )}
        </div>

        {/* AN2 — pannello mobile */}
        {!minimal && mobileNavOpen && (
          <nav aria-label="principale mobile" className="lg:hidden border-t border-gray-200 bg-white px-4 py-3">
            <ul className="space-y-1">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    onClick={() => setMobileNavOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
                  >
                    {t(item.key, { defaultValue: item.fallback })}
                  </Link>
                </li>
              ))}
              <li>
                <Link to="/chi-siamo" onClick={() => setMobileNavOpen(false)}
                      className="block rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100">
                  {t('aboutPage.title', { defaultValue: 'Chi siamo' })}
                </Link>
              </li>
              <li>
                <Link to="/come-funziona" onClick={() => setMobileNavOpen(false)}
                      className="block rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100">
                  {t('howPage.title', { defaultValue: 'Come funziona' })}
                </Link>
              </li>
              <li>
                <Link to="/account" onClick={() => setMobileNavOpen(false)}
                      className="block rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100">
                  {t('marketplace.myTrips', { defaultValue: 'Le mie esperienze' })}
                </Link>
              </li>
              <li className="pt-1">
                <Link to="/inizia" onClick={() => setMobileNavOpen(false)}
                      className="block rounded-lg bg-[#C97B5D]/10 border border-[#C97B5D]/40 px-3 py-2 text-sm font-semibold text-[#a8593f] hover:bg-[#C97B5D]/20">
                  {t('marketplace.forOrganizers', { defaultValue: 'Sei un organizzatore?' })}
                </Link>
              </li>
            </ul>
          </nav>
        )}
      </header>

      <div className="flex-1">{children}</div>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      {!minimal && (
        <footer className="relative mt-12 bg-gradient-sidebar text-white overflow-hidden">
          <div aria-hidden className="gold-rule absolute top-0 inset-x-0" />
          <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse 55% 75% at 88% 100%, rgba(193,102,61,0.16), transparent 55%)',
          }} />
          <div className="relative max-w-6xl mx-auto px-4 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
            <div>
              <div className="mb-2 flex items-center gap-2.5">
                <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-8 w-8 select-none" draggable={false} />
                <span className="flex flex-col select-none">
                  <span className="font-brand font-medium uppercase tracking-[0.28em] text-base leading-none text-[#d6c49a]">{BRAND_NAME}</span>
                  <span className="font-brand uppercase tracking-[0.3em] text-[9px] mt-1 text-[#d6c49a]/80">{BRAND_MOTTO}</span>
                </span>
              </div>
              <p className="text-white/60 text-xs leading-relaxed">
                {t('marketplace.tagline', { defaultValue: 'Trova e prenota ritiri olistici in Italia — con caparra protetta, senza pensieri.' })}
              </p>
              {/* AN1 — le pagine dell'anima */}
              <ul className="mt-3 space-y-1.5 text-white/70 text-xs">
                <li><Link to="/chi-siamo" className="hover:text-white">{t('aboutPage.title', { defaultValue: 'Chi siamo' })}</Link></li>
                <li><Link to="/come-funziona" className="hover:text-white">{t('howPage.title', { defaultValue: 'Come funziona' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-brand text-[#d6c49a] mb-3 text-[11px] uppercase tracking-[0.25em] select-none">
                {t('marketplace.footerExplore', { defaultValue: 'Esplora' })}
              </p>
              <ul className="space-y-1.5 text-white/70">
                {/* AN2 — link ai PATH SEO (/ritiri/{cat}), non alla query:
                    i crawler devono trovare le pagine categoria dai link
                    interni, non solo dalla sitemap */}
                <li><Link to="/ritiri/yoga" className="hover:text-white">Yoga</Link></li>
                <li><Link to="/ritiri/meditazione" className="hover:text-white">{t('categories.meditazione', { defaultValue: 'Meditazione & Mindfulness' })}</Link></li>
                <li><Link to="/ritiri/detox" className="hover:text-white">{t('categories.detox', { defaultValue: 'Detox & Digiuno' })}</Link></li>
                <li><Link to="/" className="hover:text-white">{t('marketplace.footerAll', { defaultValue: 'Tutti i ritiri' })}</Link></li>
                <li><Link to="/operatori" className="hover:text-white">{t('marketplace.footerOperators', { defaultValue: 'Tutti gli organizzatori' })}</Link></li>
                <li><Link to="/destinazioni" className="hover:text-white">{t('marketplace.footerDestinations', { defaultValue: 'Destinazioni' })}</Link></li>
                {destinations.map(d => (
                  <li key={d.slug}>
                    <Link to={`/destinazioni/${d.slug}`} className="hover:text-white pl-3 text-xs">
                      {d.label}
                    </Link>
                  </li>
                ))}
                <li><Link to="/blog" className="hover:text-white">{t('marketplace.navBlog', { defaultValue: 'Blog' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-brand text-[#d6c49a] mb-3 text-[11px] uppercase tracking-[0.25em] select-none">
                {t('marketplace.footerAccount', { defaultValue: 'Il tuo account' })}
              </p>
              <ul className="space-y-1.5 text-white/70">
                <li><Link to="/account" className="hover:text-white">{t('marketplace.myTrips', { defaultValue: 'Le mie esperienze' })}</Link></li>
                {/* AN7 — il Passaporto ha un nome anche in vetrina */}
                <li><Link to="/account" className="hover:text-white">{t('marketplace.passportLink', { defaultValue: 'Il tuo Passaporto Aurya' })}</Link></li>
                <li><Link to="/account/accedi" className="hover:text-white">{t('marketplace.signIn', { defaultValue: 'Accedi' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-brand text-[#d6c49a] mb-3 text-[11px] uppercase tracking-[0.25em] select-none">
                {t('marketplace.footerOrganizers', { defaultValue: 'Organizzatori' })}
              </p>
              <ul className="space-y-1.5 text-white/70">
                <li><Link to="/inizia" className="hover:text-white">{t('marketplace.startSelling', { defaultValue: 'Porta i tuoi ritiri online' })}</Link></li>
                <li><Link to="/login" className="hover:text-white">{t('marketplace.operatorLogin', { defaultValue: 'Area operatori' })}</Link></li>
              </ul>
            </div>
          </div>
          <div className="relative border-t border-white/10">
            <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-white/40">
              <span>© {BRAND_NAME}</span>
              <Link to="/privacy" className="hover:text-white/80">Privacy</Link>
              <Link to="/termini" className="hover:text-white/80">{t('marketplace.terms', { defaultValue: 'Termini' })}</Link>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
