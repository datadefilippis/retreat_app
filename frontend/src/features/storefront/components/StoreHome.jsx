/**
 * StoreHome — la home vetrina dello store (V1, 5/7/2026 sera).
 * docs/VETRINE_CONSOLIDAMENTO_PLAN.md.
 *
 * Sostituisce l'atterraggio "lista di categoria secca": chi entra su
 * /s/:slug vede CHI è l'operatore (hero con cover/logo/bio → profilo),
 * COSA offre (categorie visuali con conteggi) e cosa c'è di vivo
 * (prossimi ritiri). Tutto dai dati già caricati (catalogo) + una
 * fetch best-effort del profilo pubblico.
 */
import { TypeIcon } from '../lib/categoryIcons';
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../../api/client';

// DS2 — icone anima store: lucide, via le emoji
// (mappa condivisa in ../lib/categoryIcons)

function fmtDate(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang, {
      weekday: 'short', day: 'numeric', month: 'short',
    });
  } catch { return iso; }
}

export default function StoreHome({ slug, catalog, availableCategories, currency }) {
  const { t, i18n } = useTranslation(['storefront', 'landings']);
  const [operator, setOperator] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.get(`/public/operator/${slug}`)
      .then(res => { if (mounted) setOperator(res.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, [slug]);

  // Prossimi ritiri: dalle occurrences già nel catalogo (zero fetch extra)
  const upcoming = useMemo(() => {
    const now = new Date().toISOString();
    const rows = [];
    for (const p of (catalog?.products || [])) {
      if (p.item_type !== 'event_ticket') continue;
      for (const occ of (p.occurrences || [])) {
        if (occ.start_at && occ.start_at >= now && occ.slug) {
          rows.push({ product: p, occ });
        }
      }
    }
    return rows.sort((a, b) => (a.occ.start_at < b.occ.start_at ? -1 : 1)).slice(0, 3);
  }, [catalog]);

  const storeName = catalog?.store?.name || operator?.name || '';

  return (
    <div className="space-y-8">
      {/* ── Hero brand ── */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-sidebar text-white">
        {operator?.cover_url && (
          <>
            <img src={operator.cover_url} alt=""
                 className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-black/50" />
          </>
        )}
        <div className="relative px-6 py-10 sm:px-10 sm:py-12 flex items-center gap-5">
          {operator?.logo_url && (
            <img src={operator.logo_url} alt=""
                 className="h-16 w-16 sm:h-20 sm:w-20 rounded-full object-cover border-2 border-white/40 shrink-0" />
          )}
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{storeName}</h1>
            {(operator?.city || operator?.region) && (
              <p className="text-white/75 text-sm mt-0.5">
                {[operator.city, operator.region].filter(Boolean).join(', ')}
              </p>
            )}
            {operator?.bio && (
              <p className="text-white/85 text-sm mt-2 line-clamp-2 max-w-xl">{operator.bio}</p>
            )}
            <Link to={`/s/${slug}/chi-siamo`}
                  className="mt-3 inline-block rounded-full bg-white/15 hover:bg-white/25 px-4 py-1.5 text-sm font-semibold transition-colors">
              {t('storefront:home.aboutCta', { defaultValue: 'Scopri chi siamo' })} →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Prossimi ritiri in evidenza ── */}
      {upcoming.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-900">
              {t('storefront:home.upcomingTitle', { defaultValue: 'Prossimi ritiri' })}
            </h2>
            <Link to={`/s/${slug}/c/eventi`} className="text-sm text-primary hover:underline">
              {t('storefront:home.seeAll', { defaultValue: 'Vedi tutti' })}
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcoming.map(({ product, occ }) => (
              <Link key={occ.id} to={`/e/${slug}/${occ.slug}?store=1`}
                    className="group rounded-2xl border border-gray-200 bg-white overflow-hidden hover-lift">
                <div className="relative h-36 bg-gray-100 overflow-hidden">
                  {(occ.cover_image_url || product.image_url) ? (
                    <img src={occ.cover_image_url || product.image_url} alt="" loading="lazy"
                         className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center" aria-hidden><TypeIcon type="eventi" className="h-10 w-10 opacity-70" /></div>
                  )}
                  <span className="absolute top-2.5 left-2.5 rounded-lg bg-white/95 px-2 py-1 text-[11px] font-bold text-gray-900 shadow">
                    {fmtDate(occ.start_at, i18n.language)}
                  </span>
                </div>
                <div className="p-3.5">
                  <p className="font-semibold text-gray-900 line-clamp-2">{product.name}</p>
                  {product.unit_price != null && (
                    <p className="text-sm text-gray-600 mt-1">
                      {t('landings:calendar.priceFrom', {
                        price: new Intl.NumberFormat('it-IT', { style: 'currency', currency: currency || 'EUR', maximumFractionDigits: 0 }).format(product.unit_price),
                      })}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
