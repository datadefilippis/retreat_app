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
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BRAND_NAME, BRAND_GLYPH } from '../../../config/brand';

const LANGS = ['it', 'en', 'de', 'fr'];

function LangSwitcher() {
  const { i18n } = useTranslation();
  const cur = (i18n.language || 'it').slice(0, 2);
  return (
    <div className="flex items-center gap-0.5">
      {LANGS.map(l => (
        <button
          key={l}
          type="button"
          onClick={() => i18n.changeLanguage(l)}
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
  const { t } = useTranslation('landings');
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link to="/ritiri" className="flex items-center gap-1.5 shrink-0" aria-label={BRAND_NAME}>
            <span aria-hidden className="text-xl">{BRAND_GLYPH}</span>
            <span className="font-bold text-gray-900 tracking-tight">{BRAND_NAME}</span>
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
                  onClick={() => navigate('/ritiri')}
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
                  {t('marketplace.myTrips', { defaultValue: 'I miei viaggi' })}
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
              <p className="font-bold text-gray-900 mb-2">{BRAND_GLYPH} {BRAND_NAME}</p>
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
                <li><Link to="/ritiri" className="hover:text-primary">{t('marketplace.footerAll', { defaultValue: 'Tutti i ritiri' })}</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-gray-900 mb-2 text-xs uppercase tracking-wide">
                {t('marketplace.footerAccount', { defaultValue: 'Il tuo account' })}
              </p>
              <ul className="space-y-1.5 text-gray-600">
                <li><Link to="/account" className="hover:text-primary">{t('marketplace.myTrips', { defaultValue: 'I miei viaggi' })}</Link></li>
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
