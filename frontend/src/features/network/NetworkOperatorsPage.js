/**
 * NetworkOperatorsPage — /operatori in fase network (RT3, piano
 * sito-rete).
 *
 * NON e' una directory: con pochi profili una landing curata sembra
 * selettiva, una directory con filtri sembra abbandonata. Racconta
 * cos'e' la rete e con che criterio si entra, poi le schede dei
 * membri (network_member=True, sigillo del system admin). I filtri
 * arrivano a 25+ profili, URL invariato. In fase marketplace questo
 * URL torna all'aggregatore pieno (OperatorsGate).
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Quote, MapPin } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import VerifiedAuryaBadge from '../../components/VerifiedAuryaBadge';
import BrandPayoff from '../../components/BrandPayoff';

export default function NetworkOperatorsPage() {
  const { t } = useTranslation('landings');
  const [members, setMembers] = useState(null);   // null = caricamento

  useSeoMeta({
    title: t('nwOps.seoTitle', { defaultValue: 'La rete degli operatori | Aurya' }),
    description: t('nwOps.seoDesc', { defaultValue: 'Gli operatori olistici della rete Aurya: scelti uno a uno, intervistati e raccontati. Persone vere, pratiche serie.' }),
    canonicalPath: '/operatori',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/network/members')
      .then(res => { if (mounted) setMembers(res.data?.items || []); })
      .catch(() => { if (mounted) setMembers([]); });
    return () => { mounted = false; };
  }, []);

  const criteria = [
    t('nwOps.c1', { defaultValue: 'Una pratica reale, esercitata con continuità e serietà.' }),
    t('nwOps.c2', { defaultValue: 'La disponibilità a raccontarsi: l’intervista è la porta di ingresso.' }),
    t('nwOps.c3', { defaultValue: 'La cura verso le persone che si affidano, prima di ogni logica di vendita.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <header className="relative bg-gradient-sidebar text-white overflow-hidden">
          <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
          }} />
          <div className="relative max-w-3xl mx-auto px-4 py-14 text-center">
            <BrandPayoff tone="deep" size="xs" className="mb-3" />
            <h1 className="font-display text-3xl md:text-4xl font-bold">
              {t('nwOps.title', { defaultValue: 'La rete degli operatori' })}
            </h1>
            <p className="text-white/85 mt-4 text-lg leading-relaxed">
              {t('nwOps.intro', { defaultValue: 'Non un elenco: una rete. Ogni operatore che vedi qui è stato incontrato, intervistato e accolto. Uno alla volta.' })}
            </p>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-12 space-y-12">
          {/* Con che criterio si entra */}
          <section className="max-w-2xl mx-auto">
            <h2 className="font-heading text-xl font-semibold text-foreground text-center">
              {t('nwOps.criteriaTitle', { defaultValue: 'Con che criterio scegliamo' })}
            </h2>
            <ul className="mt-5 space-y-3">
              {criteria.map((c, i) => (
                <li key={i} className="flex items-start gap-3 rounded-xl border border-border bg-card p-4">
                  <span className="font-brand text-[#8a7440] text-sm mt-0.5">{String(i + 1).padStart(2, '0')}</span>
                  <span className="text-muted-foreground leading-relaxed">{c}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Le schede dei membri */}
          <section>
            <h2 className="font-heading text-xl font-semibold text-foreground text-center mb-6">
              {t('nwOps.membersTitle', { defaultValue: 'I membri della rete' })}
            </h2>
            {members === null ? (
              <p className="text-sm text-muted-foreground text-center py-10">…</p>
            ) : members.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center max-w-xl mx-auto">
                <Quote className="h-6 w-6 mx-auto text-[#8a7440]" aria-hidden />
                <p className="text-muted-foreground mt-3 leading-relaxed">
                  {t('nwOps.membersEmpty', { defaultValue: 'Le prime interviste sono in corso: i profili arrivano qui uno alla volta, quando sono pronti a essere raccontati bene.' })}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                {members.map(m => (
                  /* PV3 — la card intera porta al profilo (link steso
                     sull'area), ma "Leggi l'intervista" è un link VERO
                     alla pagina dedicata /o/:slug/intervista */
                  <div key={m.slug}
                       className="group relative rounded-2xl border border-border bg-card overflow-hidden hover:shadow-md transition-shadow flex">
                    <Link to={`/o/${m.slug}`} aria-label={m.name}
                          className="absolute inset-0 z-0" />
                    {(m.portrait_url || m.cover_url) && (
                      <img src={m.portrait_url || m.cover_url} alt="" loading="lazy"
                           className="h-full w-28 object-cover shrink-0" />
                    )}
                    <div className="p-4 flex flex-col justify-center">
                      <h3 className="font-heading text-base font-semibold text-foreground group-hover:text-[#376254]">
                        {m.name}
                      </h3>
                      {/* PV4 — il sigillo sotto il nome (on-light):
                          intervista pubblicata dal system admin */}
                      {m.verified && (
                        <p className="mt-1">
                          <VerifiedAuryaBadge variant="on-light" size="sm" />
                        </p>
                      )}
                      {m.tagline && (
                        <p className="text-sm text-muted-foreground mt-0.5 leading-snug">{m.tagline}</p>
                      )}
                      {(m.city || m.region) && (
                        <p className="text-xs text-muted-foreground mt-1.5 inline-flex items-center gap-1">
                          <MapPin className="h-3 w-3" aria-hidden />
                          {[m.city, m.region].filter(Boolean).join(', ')}
                        </p>
                      )}
                      {/* TW2 — il listino gia' in card: da X euro, N servizi */}
                      {m.services_count > 0 && (
                        <p className="text-xs text-gray-600 mt-1.5">
                          {m.price_from != null
                            ? t('nwOps.priceFrom', { price: Math.round(m.price_from), count: m.services_count, defaultValue: 'da {{price}}€ · {{count}} servizi' })
                            : t('nwOps.servicesCount', { count: m.services_count, defaultValue: '{{count}} servizi a listino' })}
                        </p>
                      )}
                      {m.has_interview && (
                        <Link to={`/o/${m.slug}/intervista`}
                              className="relative z-10 inline-block text-[11px] font-semibold uppercase tracking-wide text-[#8a7440] mt-2 hover:underline">
                          {t('nwOps.readInterview', { defaultValue: 'Leggi l’intervista' })}
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* CTA candidatura */}
          <section className="rounded-3xl bg-gradient-sidebar text-white p-8 text-center overflow-hidden relative">
            <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
              background: 'radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
            }} />
            <div className="relative">
              <h2 className="font-heading text-2xl font-semibold">
                {t('nwOps.ctaTitle', { defaultValue: 'Vuoi farne parte?' })}
              </h2>
              <p className="text-white/85 mt-2 max-w-xl mx-auto leading-relaxed">
                {t('nwOps.ctaBody', { defaultValue: 'Raccontaci chi sei e cosa fai. Se c’è sintonia ti intervistiamo e costruiamo insieme il tuo profilo pubblico.' })}
              </p>
              <Link to="/entra-nella-rete" className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-white text-[#376254] px-6 py-2.5 text-sm font-semibold hover:bg-gray-100">
                {t('nwOps.ctaButton', { defaultValue: 'Entra nella rete' })} <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
          </section>
        </main>
      </div>
    </MarketplaceShell>
  );
}
