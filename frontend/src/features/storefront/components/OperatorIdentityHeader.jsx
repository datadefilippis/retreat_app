/**
 * OperatorIdentityHeader — la testata identitaria dell'operatore (PV3,
 * docs/PROFILO_VERIFICATO_PIANO_2026-07.md).
 *
 * UNA sola testata per profilo (/o/:slug) e pagina intervista
 * (/o/:slug/intervista): stessa cover con overlay, stesso avatar,
 * stessa fila di badge. La continuità tra le due pagine (richiesta
 * founder) non è "stile simile": è lo STESSO componente, quindi non
 * può divergere. PV4 aggiungerà qui il badge Verificato Aurya e
 * comparirà su entrambe le pagine gratis.
 */
import React from 'react';
import { Flower2 } from 'lucide-react';
import VerifiedAuryaBadge from '../../../components/VerifiedAuryaBadge';

export default function OperatorIdentityHeader({ data, t }) {
  const accent = data.brand_color || '#16281F';
  const rs = data.reviews_stats;
  return (
    <header className="text-white relative mt-2" style={{ backgroundColor: accent }}>
      {data.cover_url && (
        <>
          <img src={data.cover_url} alt="" aria-hidden fetchPriority="high"
               className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/45" />
        </>
      )}
      <div className="relative max-w-6xl mx-auto px-4 py-14 flex items-center gap-5">
        {data.logo_url && (
          <img src={data.logo_url} alt={`Logo di ${data.name}`}
               className="h-20 w-20 rounded-full object-cover bg-white/10 border-2 border-white/50 shadow-lg" />
        )}
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold">{data.name}</h1>
          {data.tagline && (
            <p className="text-white/90 mt-1">{data.tagline}</p>
          )}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {/* PV4 — badge "Verificato Aurya": PRIMA di In evidenza,
                solo quando l'intervista è pubblicata (il payload espone
                interview_verified_at soltanto in quel caso). La fila
                badge è unica per profilo e pagina intervista: appare
                su entrambe. */}
            {data.interview_verified_at && (
              <span data-testid="verified-badge-slot">
                <VerifiedAuryaBadge variant="on-photo" size="md" />
              </span>
            )}
            {/* GT3 — badge dei piani "In evidenza" */}
            {data.featured && (
              <span className="rounded-full bg-white/25 backdrop-blur px-2.5 py-1 text-[11px] font-semibold">
                ✦ {t('landings:calendar.featured', { defaultValue: 'In evidenza' })}
              </span>
            )}
            {rs?.count > 0 && (
              <span className="rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-medium">
                ★ {rs.avg} · {t('landings:reviews.countShort', { count: rs.count, defaultValue: '{{count}} recensioni' })}
              </span>
            )}
            {(data.founded_year || data.member_since) && (
              <span className="rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-medium">
                ✓ {t('landings:operator.memberSince', { defaultValue: 'Professionista del benessere dal {{year}}', year: data.founded_year || data.member_since })}
              </span>
            )}
            {data.retreats_organized > 0 && (
              <span className="rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-medium">
                <Flower2 className="inline h-3 w-3 mr-0.5 align-[-1px]" aria-hidden /> {t('landings:operator.retreatsOrganized', { defaultValue: '{{count}} ritiri organizzati', count: data.retreats_organized })}
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
