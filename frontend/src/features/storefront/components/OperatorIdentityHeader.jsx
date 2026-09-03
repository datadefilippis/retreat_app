/**
 * OperatorIdentityHeader — la testata identitaria dell'operatore (PV3;
 * ridisegnata col ciclo IG, 3/9/2026).
 *
 * UNA sola testata per profilo (/o/:slug) e pagina intervista: lo
 * STESSO componente, quindi non può divergere (decisione PV3).
 *
 * IG1 (founder, il carosello): prima la cover mangiava il primo
 * schermo del telefono col nome annegato nella foto. Ora il disegno
 * è quello della card d'identità: la cover è una BANDA ad altezza
 * fissa (qualunque proporzione abbia la foto caricata: object-cover
 * ritaglia, mai il layout che balla), e sotto sale una CARD bianca
 * con l'avatar tondo (ritaglio alto-centrale: sicuro per i ritratti
 * verticali), il nome, la tagline, la città e la fila dei badge.
 * Uno screenshot del primo schermo ora mostra CHI SEI, non solo una
 * foto.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Flower2, MapPin } from 'lucide-react';
import VerifiedAuryaBadge from '../../../components/VerifiedAuryaBadge';
// DI — label discipline (specchio di models/disciplines.py)
import { disciplineLabel } from '../../../lib/disciplines';

/* la destinazione: /destinazioni/{regione|città} come link interno
   (era nell'aside: ora la città ha UNA casa, qui) */
export function placeSlugOf(data) {
  const base = data.region || data.city;
  if (!base) return null;
  return String(base).toLowerCase().normalize('NFKD')
    .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export default function OperatorIdentityHeader({ data, t }) {
  const accent = data.brand_color || '#16281F';
  const rs = data.reviews_stats;
  /* l'avatar: il logo se c'è, altrimenti il ritratto — sempre tondo,
     sempre ritagliato dal centro-alto (le teste restano dentro con
     qualunque proporzione di foto) */
  const avatar = data.logo_url || data.portrait_url;
  const luogo = [data.city, data.region].filter(Boolean).join(', ');
  const placeSlug = placeSlugOf(data);
  const discipline = Array.isArray(data.disciplines) ? data.disciplines : [];
  return (
    <header className="relative" data-testid="operator-identity">
      {/* la cover: banda ad altezza FISSA — ogni foto va bene */}
      <div className="relative h-44 sm:h-60 overflow-hidden"
           style={{ backgroundColor: accent }}>
        {data.cover_url && (
          <img src={data.cover_url} alt="" aria-hidden fetchPriority="high"
               className="absolute inset-0 w-full h-full object-cover" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
      </div>

      {/* la card d'identità che sale sopra la cover */}
      <div className="max-w-6xl mx-auto px-4">
        <div className="relative -mt-12 sm:-mt-14 rounded-2xl border border-gray-200
                        bg-white shadow-[0_10px_30px_-16px_rgba(22,40,31,0.35)]
                        p-5 sm:p-6"
             data-testid="identity-card">
          <div className="flex items-start gap-4">
            {avatar && (
              <img src={avatar} alt={data.logo_url ? `Logo di ${data.name}` : `Foto di ${data.name}`}
                   className="h-20 w-20 sm:h-24 sm:w-24 shrink-0 rounded-full
                              object-cover object-[center_25%] bg-gray-100
                              ring-2 ring-[#c9b37e]/70 shadow-md" />
            )}
            <div className="min-w-0 flex-1 pt-0.5">
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground leading-tight">
                {data.name}
              </h1>
              {data.tagline && (
                <p className="text-gray-600 mt-1 text-sm sm:text-base line-clamp-2">
                  {data.tagline}
                </p>
              )}
              {luogo && (
                <p className="mt-1.5 flex items-center gap-1 text-sm text-gray-500">
                  <MapPin className="h-3.5 w-3.5 text-[#376254]" aria-hidden />
                  {placeSlug ? (
                    <Link to={`/destinazioni/${placeSlug}`} className="hover:text-[#376254] hover:underline">
                      {luogo}
                    </Link>
                  ) : luogo}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {/* PV4 — badge "Verificato Aurya": prima della fila,
                solo a intervista pubblicata */}
            {data.interview_verified_at && (
              <span data-testid="verified-badge-slot">
                <VerifiedAuryaBadge variant="on-light" size="md" />
              </span>
            )}
            {data.featured && (
              <span className="rounded-full bg-[#c9b37e]/20 text-[#8a7440] px-2.5 py-1 text-[11px] font-semibold">
                ✦ {t('landings:calendar.featured', { defaultValue: 'In evidenza' })}
              </span>
            )}
            {rs?.count > 0 && (
              <span className="rounded-full bg-gray-100 text-gray-700 px-2.5 py-1 text-[11px] font-medium">
                ★ {rs.avg} · {t('landings:reviews.countShort', { count: rs.count, defaultValue: '{{count}} recensioni' })}
              </span>
            )}
            {/* 30/8 (founder): «su Aurya dal» = member_since, mai
                founded_year (sarebbe una bugia) */}
            {data.member_since && (
              <span className="rounded-full bg-[#376254]/10 text-[#376254] px-2.5 py-1 text-[11px] font-medium">
                ✓ {t('landings:operator.memberSince', { defaultValue: 'Professionista del benessere su Aurya dal {{year}}', year: data.member_since })}
              </span>
            )}
            {data.retreats_organized > 0 && (
              <span className="rounded-full bg-gray-100 text-gray-700 px-2.5 py-1 text-[11px] font-medium">
                <Flower2 className="inline h-3 w-3 mr-0.5 align-[-1px] text-[#376254]" aria-hidden />
                {t('landings:operator.retreatsOrganized', { defaultValue: '{{count}} ritiri organizzati', count: data.retreats_organized })}
              </span>
            )}
          </div>
          {/* DI (founder 14/8) — le discipline dichiarate: sono identità,
              quindi stanno qui (IG5: prima vivevano nell'aside, che su
              mobile le mostrava lontano dal nome). Chip nel verde del
              brand, label da lib/disciplines.js */}
          {discipline.length > 0 && (
            <div className="mt-4 rounded-xl border border-[#376254]/15 bg-[#376254]/[0.04] px-3.5 py-3"
                 data-testid="profile-disciplines">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#376254] mb-2">
                {t('landings:operator.myDisciplines', { defaultValue: 'Le mie discipline' })}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {discipline.map(d => (
                  <span key={d} className="rounded-full bg-white border border-[#376254]/25 px-2.5 py-0.5 text-xs font-medium text-[#376254]">
                    {disciplineLabel(d)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
