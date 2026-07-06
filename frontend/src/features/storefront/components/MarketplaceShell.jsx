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
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BRAND_NAME, BRAND_MOTTO } from '../../../config/brand';
import { persistMarketplaceLang, getMarketplaceLang } from '../../../hooks/useStorefrontLocale';

const LANGS = ['it', 'en', 'de', 'fr'];

function LangSwitcher() {
  const { t, i18n } = useTranslation('landings');
  const cur = (i18n.language || 'it').slice(0, 2);
  // L1 — la scelta viene persistita (aurya_lang) e vince sui default
  // dello store in contesto marketplace: niente più flip di lingua
  // entrando in un prodotto o al checkout.
  const choose = (l) => {
    persistMarketplaceLang(l);
    i18n.changeLanguage(l);
  };
  return (
    <div
      className="flex items-center gap-0.5"
      title={t('marketplace.langFilterNote', {
        defaultValue: 'Scegli la lingua: vedrai i ritiri e le esperienze tenuti in quella lingua.',
      })}
    >
      {LANGS.map(l => (
        <button
          key={l}
          type="button"
          onClick={() => choose(l)}
          className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase transition-colors ${
            cur === l
              ? 'bg-primary text-white'
              : 'text-gray-500 hover:bg-gray-100'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

export default function MarketplaceShell({ children, minimal = false, noSearch = false }) {
  const { t, i18n } = useTranslation('landings');
  const navigate = useNavigate();

  // L1 — ogni superficie marketplace riafferma al mount la lingua del
  // viaggiatore: la scelta salvata (aurya_lang) o l'italiano, la faccia
  // di default della piattaforma. Copre sia il ritorno da una vetrina
  // negozio sia la navigazione SPA dall'admin (il cui AuthContext non
  // ri-scatta e lascerebbe la lingua dell'operatore). Sulle landing il
  // resolver dello store (PublicStorefrontShell, effetto padre → gira
  // dopo) resta l'ultima parola quando il negozio non offre la lingua.
  useEffect(() => {
    const wanted = getMarketplaceLang() || 'it';
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
              🔒 {t('marketplace.securePayment', { defaultValue: 'Pagamento sicuro' })}
            </span>
          ) : (
            <>
              {/* Scorciatoia ricerca — riporta alla directory (che ha i filtri) */}
              {!noSearch && (
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="hidden sm:flex items-center gap-2 rounded-full border border-gray-300 bg-white pl-4 pr-2 py-1.5 text-sm text-gray-500 hover:shadow-md transition-shadow"
                >
                  <span>{t('marketplace.searchShortcut', { defaultValue: 'Dove? · Quando? · Che ritiro?' })}</span>
                  <span className="rounded-full bg-primary text-white h-6 w-6 flex items-center justify-center text-xs" aria-hidden>🔍</span>
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
                  className="rounded-full border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:border-primary hover:text-primary transition-colors whitespace-nowrap"
                >
                  {t('marketplace.myTrips', { defaultValue: 'Le mie esperienze' })}
                </Link>
              </div>
            </>
          )}
        </div>
      </header>

      <div className="flex-1">{children}</div>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      {!minimal && (
        <footer className="border-t border-gray-200 bg-white mt-12">
          <div className="max-w-6xl mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
            <div>
              <div className="mb-2 flex items-center gap-2.5">
                <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-8 w-8 select-none" draggable={false} />
                <span className="flex flex-col select-none">
                  <span className="font-brand font-medium uppercase tracking-[0.28em] text-base leading-none text-[#8a7440]">{BRAND_NAME}</span>
                  <span className="font-brand uppercase tracking-[0.3em] text-[9px] mt-1 text-[#8a7440]/80">{BRAND_MOTTO}</span>
                </span>
              </div>
              <p className="text-gray-500 text-xs leading-relaxed">
                {t('marketplace.tagline', { defaultValue: 'Trova e prenota ritiri olistici in tutto il mondo — con caparra, senza pensieri.' })}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-900 mb-2 text-xs uppercase tracking-wide">
                {t('marketplace.footerExplore', { defaultValue: 'Esplora' })}
              </p>
              <ul className="space-y-1.5 text-gray-600">
                <li><Link to="/ritiri?categoria=yoga" className="hover:text-primary">Yoga</Link></li>
                <li><Link to="/ritiri?categoria=meditazione" className="hover:text-primary">{t('categories.meditazione', { defaultValue: 'Meditazione & Mindfulness' })}</Link></li>
                <li><Link to="/ritiri?categoria=detox" className="hover:text-primary">{t('categories.detox', { defaultValue: 'Detox & Digiuno' })}</Link></li>
                <li><Link to="/" className="hover:text-primary">{t('marketplace.footerAll', { defaultValue: 'Tutti i ritiri' })}</Link></li>
                <li><Link to="/operatori" className="hover:text-primary">{t('marketplace.footerOperators', { defaultValue: 'Tutti gli organizzatori' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-gray-900 mb-2 text-xs uppercase tracking-wide">
                {t('marketplace.footerAccount', { defaultValue: 'Il tuo account' })}
              </p>
              <ul className="space-y-1.5 text-gray-600">
                <li><Link to="/account" className="hover:text-primary">{t('marketplace.myTrips', { defaultValue: 'Le mie esperienze' })}</Link></li>
                <li><Link to="/account/accedi" className="hover:text-primary">{t('marketplace.signIn', { defaultValue: 'Accedi' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-gray-900 mb-2 text-xs uppercase tracking-wide">
                {t('marketplace.footerOrganizers', { defaultValue: 'Organizzatori' })}
              </p>
              <ul className="space-y-1.5 text-gray-600">
                <li><Link to="/inizia" className="hover:text-primary">{t('marketplace.startSelling', { defaultValue: 'Porta i tuoi ritiri online' })}</Link></li>
                <li><Link to="/login" className="hover:text-primary">{t('marketplace.operatorLogin', { defaultValue: 'Area operatori' })}</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-100">
            <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400">
              <span>© {BRAND_NAME}</span>
              <Link to="/privacy" className="hover:text-gray-600">Privacy</Link>
              <Link to="/termini" className="hover:text-gray-600">{t('marketplace.terms', { defaultValue: 'Termini' })}</Link>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
