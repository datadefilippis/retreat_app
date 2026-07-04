/**
 * Wave GDPR-Admin Phase E — public sub-processors page.
 *
 * Renders the locale-aware registry returned by
 *   GET /api/legal/sub-processors?lang=<xx>
 *
 * GDPR Art. 28.3.i + Art. 13.1.f require that the chain of data
 * sub-processors and the international-transfer mechanisms be
 * DISCOVERABLE INDEPENDENTLY from the full Privacy Policy text — this
 * page is that surface.
 *
 * Public, no auth. Linked from:
 *   - Footer of PrivacyPolicyPage + TermsOfServicePage
 *   - ReconsentModal (Phase E)
 *   - Future: the signup form, the cookie banner "details" link.
 *
 * Locale resolution mirrors PrivacyPolicyPage / TermsOfServicePage:
 *   1. ?lang= query string (used by signup + reconsent modal)
 *   2. i18n.language
 *   3. "it" (backend default fallback)
 */
import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TrendingUp, ArrowLeft, ExternalLink } from 'lucide-react';

import { fetchSubProcessors } from '../services/legalService';

// ISO-2 country code → emoji flag (cheap, no extra dep)
function flagOf(cc) {
  if (!cc || cc.length !== 2) return '';
  const base = 0x1f1e6;
  const codePoints = cc.toUpperCase().split('').map((c) => base + c.charCodeAt(0) - 'A'.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

export default function SubProcessorsPage() {
  const { t, i18n } = useTranslation('legal');
  const location = useLocation();

  const params = new URLSearchParams(location.search);
  const requestedLang = (params.get('lang') || i18n.language || 'it').toLowerCase();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    fetchSubProcessors(requestedLang)
      .then((res) => {
        if (active) {
          setData(res);
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
      <header className="border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
              <TrendingUp className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-heading text-xl font-bold tracking-tight">
              AFianco
            </span>
          </Link>
          <Link
            to={`/privacy?lang=${requestedLang}`}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('sub_processors.back_to_privacy')}
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight">
          {t('sub_processors.page_title')}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {t('sub_processors.page_subtitle')}
        </p>

        {loading && (
          <p className="mt-8 text-sm text-muted-foreground">
            {t('sub_processors.loading')}
          </p>
        )}

        {error && (
          <div className="mt-8 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-300">
            {t('sub_processors.error_load')}
          </div>
        )}

        {data && (
          <>
            {/* Controller block + version metadata */}
            <section className="mt-6 rounded-lg border bg-card p-4 text-sm">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {t('sub_processors.controller_label')}
                  </p>
                  <p className="mt-1 font-medium">
                    {data.controller.name}
                  </p>
                  <p className="text-muted-foreground">
                    {data.controller.city}, {data.controller.country}
                  </p>
                  <a
                    href={`mailto:${data.controller.email}`}
                    className="text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {data.controller.email}
                  </a>
                </div>
                <div className="sm:text-right">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {t('sub_processors.version_label')}
                  </p>
                  <p className="mt-1 font-mono text-sm">
                    {data.version_tag}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-wide text-muted-foreground">
                    {t('sub_processors.binding_locale_label')}
                  </p>
                  <p className="mt-1 text-sm uppercase">
                    {data.binding_locale}
                  </p>
                </div>
              </div>
            </section>

            {/* Sub-processors table — responsive: cards on mobile, table on >=md */}
            <section className="mt-8">
              {/* Desktop table */}
              <div className="hidden md:block overflow-hidden rounded-lg border">
                <table className="w-full divide-y text-sm">
                  <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">{t('sub_processors.table_name')}</th>
                      <th className="px-4 py-3 font-medium">{t('sub_processors.table_country')}</th>
                      <th className="px-4 py-3 font-medium">{t('sub_processors.table_purpose')}</th>
                      <th className="px-4 py-3 font-medium">{t('sub_processors.table_data')}</th>
                      <th className="px-4 py-3 font-medium">{t('sub_processors.table_safeguard')}</th>
                      <th className="px-4 py-3 font-medium" />
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.sub_processors.map((sp) => (
                      <tr key={sp.id} className="align-top">
                        <td className="px-4 py-3 font-medium whitespace-nowrap">{sp.name}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span aria-hidden className="mr-1">{flagOf(sp.country_code)}</span>
                          {sp.country_code}
                        </td>
                        <td className="px-4 py-3">{sp.purpose}</td>
                        <td className="px-4 py-3">{sp.data}</td>
                        <td className="px-4 py-3">
                          <span className={sp.is_eu_eea
                            ? 'inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                            : 'inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                          }>
                            {sp.safeguard}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <a
                            href={sp.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            {t('sub_processors.table_link')}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="md:hidden flex flex-col gap-3">
                {data.sub_processors.map((sp) => (
                  <div key={sp.id} className="rounded-lg border bg-card p-4 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold">{sp.name}</p>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        <span aria-hidden className="mr-1">{flagOf(sp.country_code)}</span>
                        {sp.country_code}
                      </span>
                    </div>
                    <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
                      <dt className="text-muted-foreground">{t('sub_processors.table_purpose')}</dt>
                      <dd>{sp.purpose}</dd>
                      <dt className="text-muted-foreground">{t('sub_processors.table_data')}</dt>
                      <dd>{sp.data}</dd>
                      <dt className="text-muted-foreground">{t('sub_processors.table_safeguard')}</dt>
                      <dd>{sp.safeguard}</dd>
                    </dl>
                    <a
                      href={sp.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
                    >
                      <ExternalLink className="h-3 w-3" />
                      {t('sub_processors.table_link')}
                    </a>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
