/**
 * Wave GDPR-Commerce Phase CG-2 — public storefront legal page.
 *
 * Used by both ``/s/:slug/privacy`` and ``/s/:slug/terms`` routes via
 * the ``doc_type`` prop. We unify rendering because the two pages
 * share 95% of their logic — fetch by slug, render markdown, surface
 * status + version metadata — and the only divergence is the doc type
 * and the i18n keys for the title.
 *
 * Locale model (PS5, 30/7/2026 — supera il cornerstone CG-1)
 * -------------------------------
 * La pagina chiede al backend il documento nella LINGUA UTENTE
 * (i18n.language → ?lang=): l'informativa autogenerata esiste x4
 * lingue, quindi l'utente italiano legge italiano anche su uno store
 * con lingua primaria inglese. Fa comunque fede la versione in
 * ``binding_locale`` (la lingua di riferimento dello store): quando la
 * lingua servita differisce, mostriamo la riga "Fa fede la versione
 * in X". I documenti CUSTOM pubblicati esistono solo nelle lingue
 * scritte dal merchant: lingua richiesta se c'e', altrimenti binding.
 *
 * Empty / not-configured fallback
 * -------------------------------
 * The backend returns 200 with status="not_configured" (or "draft")
 * when the merchant has not yet published. We render a graceful
 * "Contact the merchant" panel rather than a 404 — the rest of the
 * storefront stays usable while the merchant completes configuration.
 *
 * No login required — these pages are part of the public storefront.
 */
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TrendingUp, ArrowLeft, AlertTriangle, Globe } from 'lucide-react';

import LegalMarkdownRenderer from '../components/legal/LegalMarkdownRenderer';
import {
  fetchStorefrontPrivacy,
  fetchStorefrontTerms,
} from '../services/legalService';

const LOCALE_LABELS = {
  it: 'Italiano',
  en: 'English',
  de: 'Deutsch',
  fr: 'Français',
};

function StorefrontLegalPage({ docType }) {
  const { slug } = useParams();
  const { t, i18n } = useTranslation('legal');

  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // PS5 — lingua utente corrente, normalizzata a 2 lettere ("it-IT" →
  // "it"). Il backend valida: un valore fuori dalle 4 lingue supportate
  // equivale a nessun override (si serve la lingua dello store).
  const userLang = (i18n.language || '').slice(0, 2).toLowerCase();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const fetcher = docType === 'terms'
      ? fetchStorefrontTerms
      : fetchStorefrontPrivacy;
    fetcher(slug, userLang || undefined)
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
  }, [slug, docType, userLang]);

  // Header + breadcrumbs reused across both states (loading, error,
  // success). Storefront link is the user's escape route back to the shop.
  const Header = () => (
    <header className="border-b border-border">
      <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to={`/s/${slug}`} className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
            <TrendingUp className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-heading text-xl font-bold tracking-tight">
            {doc?.store_name || slug}
          </span>
        </Link>
        <Link
          to={`/s/${slug}`}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('storefront_legal.back_to_store', 'Torna al negozio')}
        </Link>
      </div>
    </header>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-12">
          <p className="text-sm text-muted-foreground">
            {t('storefront_legal.loading', 'Caricamento...')}
          </p>
        </main>
      </div>
    );
  }

  // True 404 from backend (slug doesn't exist) — error.response.status === 404
  const is404 = error && error.response && error.response.status === 404;

  if (is404) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-bold tracking-tight">
            {t('storefront_legal.not_found_title', 'Negozio non trovato')}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t(
              'storefront_legal.not_found_body',
              'Il negozio richiesto non esiste o non è disponibile.'
            )}
          </p>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-12">
          <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {t(
              'storefront_legal.error_load',
              'Impossibile caricare il documento. Riprova più tardi.'
            )}
          </div>
        </main>
      </div>
    );
  }

  // Graceful placeholder when merchant has not yet published their docs.
  const isPlaceholder =
    doc.status === 'not_configured' || doc.status === 'draft';

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight">
          {docType === 'terms'
            ? t('storefront_legal.terms_title', 'Termini e Condizioni')
            : t('storefront_legal.privacy_title', 'Informativa sulla Privacy')
          }
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {doc.store_name}
        </p>

        {/*
          Track E Step 7.5 — Auto-generated fallback banner.

          Pre-fix: status=not_configured|draft → banner giallo "Documento
          non ancora pubblicato" + NESSUN contenuto sotto. Customer NON
          poteva consultare alcuna informativa GDPR al momento del
          consenso → compliance gap (Art. 13 GDPR).

          Post-fix: il backend ora popola SEMPRE doc.content con un
          template default pre-fillato sui dati anagrafici store quando
          il merchant non ha pubblicato. La pagina mostra:
            1. banner azzurro informativo (doc auto-generato, non
               personalizzato dal merchant)
            2. il contenuto template renderizzato sotto (markdown)
          Customer ha SEMPRE un'informativa consultabile.
        */}
        {doc.is_autogenerated && doc.content && (
          <div className="mt-6 flex items-start gap-3 rounded-md border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-100">
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">
                {t(
                  'storefront_legal.autogen_title',
                  'Informativa generata automaticamente'
                )}
              </p>
              <p className="mt-1">
                {t(
                  'storefront_legal.autogen_body',
                  'Questo documento è una versione standard pre-compilata con i dati del negozio. Per la versione personalizzata definitiva contatta il merchant.'
                )}{' '}
                {doc.merchant_email && (
                  <>
                    {t('storefront_legal.contact_merchant', 'Contatto:')}{' '}
                    <a
                      href={`mailto:${doc.merchant_email}`}
                      className="underline"
                    >
                      {doc.merchant_email}
                    </a>
                  </>
                )}
              </p>
            </div>
          </div>
        )}

        {/* Edge case: status not_configured + template fallback failed.
            Last-resort placeholder (no content disponibile in nessun
            modo). Mantenuto per defensive UX. */}
        {isPlaceholder && !doc.content && (
          <div className="mt-6 flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">
                {t(
                  'storefront_legal.not_configured_title',
                  'Documento non ancora pubblicato'
                )}
              </p>
              <p className="mt-1">
                {t(
                  'storefront_legal.not_configured_body',
                  'Il negozio sta completando la configurazione legale.'
                )}{' '}
                {doc.merchant_email && (
                  <>
                    {t('storefront_legal.contact_merchant', 'Contatto:')}{' '}
                    <a
                      href={`mailto:${doc.merchant_email}`}
                      className="underline"
                    >
                      {doc.merchant_email}
                    </a>
                  </>
                )}
              </p>
            </div>
          </div>
        )}

        {(doc.binding_locale || doc.display_locale) && doc.content && (
          <div className="mt-6 space-y-1.5 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span>
                {t(
                  'storefront_legal.binding_locale_label',
                  'Lingua di riferimento legale:'
                )}{' '}
                <strong>
                  {LOCALE_LABELS[doc.binding_locale || doc.display_locale]
                    || (doc.binding_locale || doc.display_locale).toUpperCase()}
                </strong>
              </span>
              {doc.version_tag && (
                <span className="ml-auto text-muted-foreground/70">
                  v: {doc.version_tag}
                </span>
              )}
            </div>
            {/* PS5 — il documento e' servito nella lingua utente ma fa
                fede la versione nella lingua di riferimento dello store */}
            {doc.binding_locale && doc.display_locale
              && doc.display_locale !== doc.binding_locale && (
              <p data-testid="binding-locale-note">
                {t('storefront_legal.binding_note', {
                  defaultValue: 'Traduzione di cortesia: fa fede la versione in {{language}}.',
                  language: LOCALE_LABELS[doc.binding_locale]
                    || doc.binding_locale.toUpperCase(),
                })}
              </p>
            )}
          </div>
        )}

        {doc.content && (
          <div className="mt-4">
            <LegalMarkdownRenderer content={doc.content} />
          </div>
        )}

        {/* Cross-link to the sibling legal doc + storefront */}
        <div className="mt-12 border-t border-border pt-6 text-sm text-muted-foreground flex flex-wrap gap-x-6 gap-y-2">
          {docType === 'privacy' ? (
            <Link to={`/s/${slug}/terms`} className="text-primary hover:underline">
              {t('storefront_legal.see_terms', 'Vedi i Termini e Condizioni')}
            </Link>
          ) : (
            <Link to={`/s/${slug}/privacy`} className="text-primary hover:underline">
              {t('storefront_legal.see_privacy', 'Vedi l\'Informativa sulla Privacy')}
            </Link>
          )}
          {doc.merchant_email && (
            <a
              href={`mailto:${doc.merchant_email}`}
              className="text-primary hover:underline"
            >
              {t('storefront_legal.contact_label', 'Contatta il negozio')}
            </a>
          )}
        </div>
      </main>
    </div>
  );
}

// Thin wrappers — exported as named pages so App.js routing stays
// declarative and i18n / route matching is straightforward.

export function StorefrontPrivacyPage() {
  return <StorefrontLegalPage docType="privacy" />;
}

export function StorefrontTermsPage() {
  return <StorefrontLegalPage docType="terms" />;
}

export default StorefrontLegalPage;
