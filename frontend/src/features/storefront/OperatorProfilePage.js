/**
 * OperatorProfilePage — /o/:org_slug (Fase 5).
 * Vetrina pubblica dell'organizzatore: brand, bio, prossimi ritiri.
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';

function fmtPrice(n) {
  if (n == null) return null;
  try {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
  } catch { return `${n} €`; }
}
function fmtDates(s, e, lang = 'it-IT') {
  try {
    const d = new Date(s);
    const o = { day: 'numeric', month: 'short' };
    if (!e) return d.toLocaleDateString(lang, { ...o, year: 'numeric' });
    return `${d.toLocaleDateString(lang, o)} – ${new Date(e).toLocaleDateString(lang, { ...o, year: 'numeric' })}`;
  } catch { return s; }
}

export default function OperatorProfilePage() {
  const { org_slug } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.get(`/public/operator/${org_slug}`)
      .then(res => { if (mounted) setData(res.data); })
      .catch(err => { if (mounted) setNotFound(err?.response?.status === 404); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [org_slug]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">…</div>;
  if (notFound || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-2">
        <p className="text-lg font-semibold text-gray-900">{t('landings:operator.notFound')}</p>
        <Link to="/ritiri" className="text-emerald-700 underline">{t('landings:operator.backToCalendar')}</Link>
      </div>
    );
  }

  const accent = data.brand_color || '#111827';

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="text-white" style={{ backgroundColor: accent }}>
        <div className="max-w-5xl mx-auto px-4 py-10 flex items-center gap-4">
          {data.logo_url && (
            <img src={data.logo_url} alt="" className="h-16 w-16 rounded-full object-cover bg-white/10" />
          )}
          <div>
            <h1 className="text-2xl font-bold">{data.name}</h1>
            {data.city && <p className="text-white/80 text-sm mt-0.5">{data.city}</p>}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {data.bio && (
          <p className="text-gray-700 leading-relaxed mb-6 max-w-2xl">{data.bio}</p>
        )}

        <h2 className="text-base font-semibold text-gray-900 mb-3">
          {t('landings:operator.upcoming', { count: data.upcoming_count })}
        </h2>
        {data.upcoming.length === 0 ? (
          <p className="text-gray-500">{t('landings:operator.noUpcoming')}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.upcoming.map(item => (
              <Link key={item.url} to={item.url}
                className="rounded-xl border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow">
                <div className="h-32 bg-gray-100">
                  {item.cover_image_url
                    ? <img src={item.cover_image_url} alt="" loading="lazy" className="w-full h-full object-cover" />
                    : <div className="w-full h-full flex items-center justify-center text-3xl">🧘</div>}
                </div>
                <div className="p-3">
                  <h3 className="font-semibold text-gray-900 line-clamp-2">{item.title}</h3>
                  <p className="text-sm text-gray-600 mt-0.5">
                    {fmtDates(item.start_at, item.end_at, i18n.language)}
                    {(item.city || item.region) && <> · {[item.city, item.region].filter(Boolean).join(', ')}</>}
                  </p>
                  {item.price_from != null && (
                    <p className="font-bold text-gray-900 mt-1">
                      {t('landings:calendar.priceFrom', { price: fmtPrice(item.price_from) })}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
