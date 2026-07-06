/**
 * StoreAbout — la pagina "Chi siamo" DENTRO il guscio dello store (S3).
 * docs/STORE_FIX_PLAN.md: dentro un negozio non si esce mai — stesso
 * header, stessa nav, stesso carrello. Contenuto = profilo pubblico
 * (stessa fonte di /o/:slug, guscio diverso).
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../../api/client';

export default function StoreAbout({ slug }) {
  const { t, i18n } = useTranslation(['storefront', 'landings']);
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.get(`/public/operator/${slug}`)
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setFailed(true); });
    return () => { mounted = false; };
  }, [slug]);

  if (failed) {
    return (
      <p className="text-sm text-gray-500 py-12 text-center">
        {t('storefront:about.loadError', { defaultValue: 'Contenuto non disponibile al momento.' })}
      </p>
    );
  }
  if (!data) {
    return (
      <div className="space-y-4 py-4">
        <div className="h-44 rounded-2xl bg-gray-100 animate-pulse" />
        <div className="h-4 w-2/3 rounded bg-gray-100 animate-pulse" />
        <div className="h-4 w-1/2 rounded bg-gray-100 animate-pulse" />
      </div>
    );
  }

  const socials = data.socials || {};
  const extUrl = (u) => (u && !u.startsWith('http') ? `https://${u}` : u);

  return (
    <div className="space-y-6 py-4">
      {/* Cover + identita' */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-sidebar text-white">
        {data.cover_url && (
          <>
            <img src={data.cover_url} alt="" className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-black/45" />
          </>
        )}
        <div className="relative px-6 py-10 flex items-center gap-4">
          {data.logo_url && (
            <img src={data.logo_url} alt="" className="h-16 w-16 rounded-full object-cover border-2 border-white/40 shrink-0" />
          )}
          <div>
            <h1 className="text-2xl font-bold">{data.name}</h1>
            {(data.city || data.region) && (
              <p className="text-white/80 text-sm mt-0.5">
                {[data.city, data.region].filter(Boolean).join(', ')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bio */}
      {data.bio && (
        <p className="text-gray-700 leading-relaxed max-w-2xl whitespace-pre-line">{data.bio}</p>
      )}

      {/* Social + contatti */}
      {(Object.keys(socials).length > 0 || data.contacts) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {socials.instagram && (
            <a href={extUrl(socials.instagram)} target="_blank" rel="noreferrer"
               className="text-primary hover:underline">Instagram</a>
          )}
          {socials.website && (
            <a href={extUrl(socials.website)} target="_blank" rel="noreferrer"
               className="text-primary hover:underline">
              {t('landings:operator.website', { defaultValue: 'Sito web' })}
            </a>
          )}
          {socials.facebook && (
            <a href={extUrl(socials.facebook)} target="_blank" rel="noreferrer"
               className="text-primary hover:underline">Facebook</a>
          )}
          {data.contacts?.public_email && (
            <a href={`mailto:${data.contacts.public_email}`}
               className="text-gray-600 hover:underline">{data.contacts.public_email}</a>
          )}
          {data.contacts?.public_phone && (
            <span className="text-gray-600">{data.contacts.public_phone}</span>
          )}
        </div>
      )}
    </div>
  );
}
