import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TrendingUp, ArrowLeft, AlertCircle, Globe } from 'lucide-react';

import LegalMarkdownRenderer from '../components/legal/LegalMarkdownRenderer';
import { fetchLegalDocument } from '../services/legalService';

/**
 * PrivacyPolicyPage — Wave GDPR-Admin Phase C (2026-05-16).
 *
 * Pre-Phase-C: JSX with hardcoded Italian content at /privacy.
 * Post-Phase-C: thin shell that fetches the markdown bundle from
 * `GET /api/legal/privacy?lang={locale}` and renders via
 * LegalMarkdownRenderer. Locale resolution priority:
 *
 *   1. ?lang= query string  (used by signup form to pass user's locale)
 *   2. i18n.language        (current UI language)
 *   3. "it"                 (fallback — backend handles this internally)
 *
 * Backend serves a JSON envelope:
 *   { content: "...", locale_actual: "en", is_draft: true, ... }
 *
 * When ``is_draft=true`` (currently EN/DE/FR) we show a yellow banner
 * "translation in progress" with a link to the Italian binding version.
 *
 * The pre-Phase-C route ``/privacy`` still works unchanged — it just
 * fetches dynamically now instead of rendering a JSX block.
 */
const PrivacyPolicyPage = () => {
  const { i18n, t } = useTranslation();
  const location = useLocation();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Resolve requested locale: ?lang= wins, else i18n.language, else 'it'
  const params = new URLSearchParams(location.search);
  const requestedLang = (params.get('lang') || i18n.language || 'it').toLowerCase();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    fetchLegalDocument('privacy', requestedLang)
      .then((data) => {
        if (active) {
          setDoc(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err);
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [requestedLang]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-8 w-8 select-none" draggable={false} />
            <span className="font-brand font-medium uppercase tracking-[0.28em] text-lg text-[#8a7440]">
              Aurya
            </span>
          </Link>
          <Link
            to="/signup"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('legal.back_to_signup', 'Torna alla registrazione')}
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-12">
        {loading && (
          <div className="text-sm text-muted-foreground">
            {t('legal.loading', 'Caricamento informativa in corso...')}
          </div>
        )}

        {error && (
          <div className="border border-destructive bg-destructive/10 p-4 rounded-md text-sm text-destructive">
            {t(
              'legal.error',
              'Impossibile caricare l\'informativa. Riprova piu\' tardi o contatta info@aurya.life.'
            )}
          </div>
        )}

        {doc && !loading && !error && (
          <>
            {/* Draft banner — shown only for EN/DE/FR until Phase D
                lands with the validated translations. The Italian
                version is always the binding reference. */}
            {doc.is_draft && (
              <div className="mb-6 flex items-start gap-3 border-l-4 border-warning bg-warning/10 p-4 rounded-r-md text-sm">
                <AlertCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium mb-1">
                    {t(
                      'legal.draft_title',
                      'Traduzione in corso di validazione'
                    )}
                  </p>
                  <p className="text-muted-foreground">
                    {t(
                      'legal.draft_body',
                      'Questa traduzione e\' una bozza tecnica in attesa di revisione legale. La versione italiana resta il riferimento vincolante.'
                    )}{' '}
                    <Link
                      to="/privacy?lang=it"
                      className="text-primary underline"
                    >
                      {t('legal.see_italian', 'Vedi la versione italiana')}
                    </Link>
                  </p>
                </div>
              </div>
            )}

            {/* Locale switcher — minimal "Globe" dropdown if multiple
                locales are available. Always visible so users know
                the doc is available in other languages. */}
            {doc.available_locales && doc.available_locales.length > 1 && (
              <div className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
                <Globe className="h-4 w-4" />
                <span>
                  {t('legal.also_available', 'Disponibile anche in')}:
                </span>
                {doc.available_locales
                  .filter((l) => l !== doc.locale_actual)
                  .map((l) => (
                    <Link
                      key={l}
                      to={`/privacy?lang=${l}`}
                      className="text-primary hover:underline uppercase"
                    >
                      {l}
                    </Link>
                  ))}
                <span className="ml-auto text-muted-foreground/70">
                  v: {doc.version_tag}
                </span>
              </div>
            )}

            <LegalMarkdownRenderer content={doc.content} />

            {/* Wave GDPR-Admin Phase E — footer link to the public
                sub-processor registry. Required by GDPR Art. 28.3.i +
                Art. 13.1.f: the chain of processors must be
                discoverable independently of the full Privacy text. */}
            <div className="mt-12 border-t border-border pt-6 text-sm text-muted-foreground">
              <Link
                to={`/legal/sub-processors?lang=${doc.locale_actual || requestedLang}`}
                className="text-primary hover:underline"
              >
                {t('legal.sub_processors_link', 'Vedi l\'elenco dei sub-responsabili')}
              </Link>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default PrivacyPolicyPage;
