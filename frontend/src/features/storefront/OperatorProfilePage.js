/**
 * OperatorProfilePage — /o/:org_slug (Fase 5).
 * Vetrina pubblica dell'organizzatore: brand, bio, prossimi ritiri.
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import useSeoMeta from './lib/useSeoMeta';
import MarketplaceShell from './components/MarketplaceShell';

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

  // F3 — SEO profilo: title/description + JSON-LD Organization.
  // Hook chiamato incondizionatamente (prima dei return condizionali).
  useSeoMeta({
    title: data?.name ? `${data.name} — ritiri e profilo organizzatore` : undefined,
    description: data?.bio ? String(data.bio).slice(0, 155) : undefined,
    image: data?.cover_url || data?.logo_url || undefined,
    canonicalPath: `/o/${org_slug}`,
    jsonLd: data?.name ? {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: data.name,
      url: `${window.location.origin}/o/${org_slug}`,
      ...(data.logo_url ? { logo: data.logo_url } : {}),
      ...(data.bio ? { description: String(data.bio).slice(0, 300) } : {}),
      ...(Object.keys(data.socials || {}).length > 0
        ? { sameAs: Object.values(data.socials) } : {}),
    } : undefined,
  });

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">…</div>;
  if (notFound || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-2">
        <p className="text-lg font-semibold text-gray-900">{t('landings:operator.notFound')}</p>
        <Link to="/ritiri" className="text-emerald-700 underline">{t('landings:operator.backToCalendar')}</Link>
      </div>
    );
  }

  const accent = data.brand_color || '#16281F';
  const socials = data.socials || {};
  const extUrl = (u) => (u && !u.startsWith('http') ? `https://${u}` : u);

  return (
    <MarketplaceShell>
    <div className="bg-gray-50">
      {/* M1 — la barra "← Tutti i ritiri" (T2) e' stata assorbita dal
          guscio marketplace: il logo in header E il breadcrumb sotto
          riportano alla directory. */}
      <div className="max-w-5xl mx-auto px-4 pt-3">
        <nav className="text-xs text-gray-500">
          <Link to="/ritiri" className="hover:text-primary hover:underline">
            {t('landings:calendar.title', { defaultValue: 'Ritiri' })}
          </Link>
          <span className="mx-1.5" aria-hidden>›</span>
          <span className="text-gray-700">{data.name}</span>
        </nav>
      </div>

      {/* F2.0 — cover del profilo (se curata) sopra il brand header */}
      <header className="text-white relative" style={{ backgroundColor: accent }}>
        {data.cover_url && (
          <>
            <img src={data.cover_url} alt=""
                 className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-black/45" />
          </>
        )}
        <div className="relative max-w-5xl mx-auto px-4 py-12 flex items-center gap-4">
          {data.logo_url && (
            <img src={data.logo_url} alt="" className="h-16 w-16 rounded-full object-cover bg-white/10 border-2 border-white/40" />
          )}
          <div>
            <h1 className="font-display text-3xl font-bold">{data.name}</h1>
            {(data.city || data.region) && (
              <p className="text-white/80 text-sm mt-0.5">
                {[data.city, data.region].filter(Boolean).join(', ')}
              </p>
            )}
            {/* M3 — segnali di fiducia: la valuta dei marketplace */}
            <div className="flex flex-wrap items-center gap-2 mt-2.5">
              {data.member_since && (
                <span className="rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-medium">
                  ✓ {t('landings:operator.memberSince', { defaultValue: 'Organizzatore dal {{year}}', year: data.member_since })}
                </span>
              )}
              {data.retreats_organized > 0 && (
                <span className="rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-medium">
                  🧘 {t('landings:operator.retreatsOrganized', { defaultValue: '{{count}} ritiri organizzati', count: data.retreats_organized })}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {data.bio && (
          <p className="text-gray-700 leading-relaxed mb-4 max-w-2xl whitespace-pre-line">{data.bio}</p>
        )}

        {/* F2.0/F2.1 — social, contatti (opt-in) e link allo store */}
        {(Object.keys(socials).length > 0 || data.contacts || data.store_slug) && (
          <div className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            {socials.instagram && (
              <a href={extUrl(socials.instagram)} target="_blank" rel="noreferrer"
                 className="text-emerald-700 hover:underline">Instagram</a>
            )}
            {socials.website && (
              <a href={extUrl(socials.website)} target="_blank" rel="noreferrer"
                 className="text-emerald-700 hover:underline">
                {t('landings:operator.website', { defaultValue: 'Sito web' })}
              </a>
            )}
            {socials.facebook && (
              <a href={extUrl(socials.facebook)} target="_blank" rel="noreferrer"
                 className="text-emerald-700 hover:underline">Facebook</a>
            )}
            {data.contacts?.public_email && (
              <a href={`mailto:${data.contacts.public_email}`}
                 className="text-gray-600 hover:underline">{data.contacts.public_email}</a>
            )}
            {data.contacts?.public_phone && (
              <span className="text-gray-600">{data.contacts.public_phone}</span>
            )}
            {data.store_slug && (
              <Link to={`/s/${data.store_slug}`}
                    className="ml-auto rounded-full bg-emerald-700 text-white px-4 py-1.5 text-sm font-semibold hover:bg-emerald-800 transition-colors">
                {t('landings:operator.visitStore', { defaultValue: 'Visita il negozio' })} →
              </Link>
            )}
          </div>
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
    </MarketplaceShell>
  );
}
