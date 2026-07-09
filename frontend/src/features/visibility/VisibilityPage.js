/**
 * VisibilityPage — /visibilita (VT5, VISIBILITA_OPERATORE_PIANO).
 *
 * Lo specchietto della visibilità che Aurya produce all'operatore,
 * il funnel in quattro blocchi (quanto appari → chi arriva → da dove
 * → cosa converte):
 *   A. 4 StatCard mese corrente vs precedente:
 *      Impression · Visite · Visitatori unici · Prenotazioni
 *   B. Donut "Da dove arrivano" (via Aurya / tuo store / social / diretto)
 *      + card "la prova Aurya" (visite portate da directory+search)
 *   C. TrendArea visite 12 mesi + MiniBars ultimi 30 giorni
 *   D. Tabella per ritiro: visite, prenotazioni, conversione, canale
 *
 * Stato vuoto gentile: sotto 10 visite nel mese niente numeri nudi —
 * "i primi dati stanno arrivando" con la spinta a completare il
 * profilo. I numeri piccoli non devono mai imbarazzare.
 *
 * Fonte: GET /analytics/visibility (VT4). Misurazione first-party
 * anonima: nessun cookie, nessun IP, come promesso dal banner.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, Users, MousePointerClick, CalendarCheck, Sparkles, ArrowRight } from 'lucide-react';
import api from '../../api/client';
import { AppLayout, Header } from '../../components/Layout';
import { StatCard, TrendArea, MiniBars, DonutSplit } from '../../components/charts';

function monthLabel(ym, lang) {
  try {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString(lang, { month: 'short', year: '2-digit' });
  } catch { return ym; }
}

function dayShort(iso, lang) {
  try {
    return new Date(`${iso}T00:00:00`).toLocaleDateString(lang, { day: 'numeric', month: 'short' });
  } catch { return iso; }
}

function deltaPct(cur, prev) {
  if (!prev) return null; // primo mese: nessun confronto onesto possibile
  return ((cur - prev) / prev) * 100;
}

// colori fissi dei gruppi di provenienza (palette Salvia&Terracotta)
const GROUP_COLORS = {
  aurya: '#376254',   // via Aurya — salvia
  store: '#C97B5D',   // tuo store — terracotta
  social: '#B9A96B',  // social — oliva
  direct: '#8A9088',  // diretto — neutro
};

const MIN_VISITS_FOR_NUMBERS = 10;

export default function VisibilityPage() {
  const { t, i18n } = useTranslation('common');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api.get('/analytics/visibility')
      .then((res) => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData(null); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  const s = data?.summary || {};
  const channels = data?.channels || {};
  const visitsNow = s.visits?.current || 0;
  const tooEarly = !loading && visitsNow < MIN_VISITS_FOR_NUMBERS;

  // B — i 5 canali raccontati in 4 gruppi: via Aurya è la somma di
  // directory + search (è il traffico che senza Aurya non esisterebbe)
  const donutData = [
    { key: 'aurya', value: (channels.directory || 0) + (channels.search || 0),
      label: t('visibility.chAurya', { defaultValue: 'Via Aurya' }) },
    { key: 'store', value: channels.store || 0,
      label: t('visibility.chStore', { defaultValue: 'Tuo store' }) },
    { key: 'social', value: channels.social || 0,
      label: t('visibility.chSocial', { defaultValue: 'Social' }) },
    { key: 'direct', value: channels.direct || 0,
      label: t('visibility.chDirect', { defaultValue: 'Diretto' }) },
  ];

  const trendData = (data?.trend_12m || []).map((r) => ({
    label: monthLabel(r.month, lang), value: r.visits,
  }));
  const barsData = (data?.last_30d || []).map((r) => ({
    label: dayShort(r.day, lang), value: r.visits,
  }));

  const cardCls = 'rounded-xl border border-border bg-card p-4';

  return (
    <AppLayout>
      <Header
        title={t('visibility.title', { defaultValue: 'Visibilità' })}
        subtitle={t('visibility.subtitle', { defaultValue: 'Quante persone ti vedono e ti visitano su Aurya, e da dove arrivano.' })}
      />
      <div className="p-4 md:p-8 max-w-5xl space-y-6">

        {tooEarly ? (
          /* stato vuoto gentile: mai numeri nudi sotto soglia */
          <div className={`${cardCls} border-[#376254]/40 bg-[#376254]/5`}>
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 mt-0.5 text-[#376254]" aria-hidden />
              <div>
                <p className="font-semibold text-foreground">
                  {t('visibility.earlyTitle', { defaultValue: 'I primi dati stanno arrivando' })}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {t('visibility.earlyBody', { defaultValue: 'Qui vedrai quante volte appari nelle ricerche su Aurya, chi visita le tue pagine e quante visite diventano prenotazioni. Più il tuo profilo è completo, più ti fai trovare.' })}
                </p>
                <Link to="/inizia" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[#376254] hover:underline">
                  {t('visibility.earlyCta', { defaultValue: 'Completa il profilo' })} <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* A — il colpo d'occhio: mese corrente vs precedente */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard loading={loading} icon={Eye}
                        label={t('visibility.impressions', { defaultValue: 'Impression' })}
                        value={s.impressions?.current?.toLocaleString(lang)}
                        delta={deltaPct(s.impressions?.current, s.impressions?.previous)}
                        deltaLabel={t('visibility.vsPrevMonth', { defaultValue: 'vs mese prec.' })}
                        sublabel={t('visibility.impressionsSub', { defaultValue: 'apparizioni nelle ricerche' })} />
              <StatCard loading={loading} icon={MousePointerClick}
                        label={t('visibility.visits', { defaultValue: 'Visite' })}
                        value={visitsNow.toLocaleString(lang)}
                        delta={deltaPct(s.visits?.current, s.visits?.previous)}
                        deltaLabel={t('visibility.vsPrevMonth', { defaultValue: 'vs mese prec.' })} />
              <StatCard loading={loading} icon={Users}
                        label={t('visibility.uniques', { defaultValue: 'Visitatori unici' })}
                        value={s.uniques?.current?.toLocaleString(lang)}
                        delta={deltaPct(s.uniques?.current, s.uniques?.previous)}
                        deltaLabel={t('visibility.vsPrevMonth', { defaultValue: 'vs mese prec.' })} />
              <StatCard loading={loading} icon={CalendarCheck} accent
                        label={t('visibility.bookings', { defaultValue: 'Prenotazioni' })}
                        value={s.bookings?.current?.toLocaleString(lang)}
                        delta={deltaPct(s.bookings?.current, s.bookings?.previous)}
                        deltaLabel={t('visibility.vsPrevMonth', { defaultValue: 'vs mese prec.' })} />
            </div>

            {/* B — da dove arrivano + la prova Aurya */}
            <div className="grid lg:grid-cols-2 gap-4">
              <div className={cardCls}>
                <h2 className="text-sm font-semibold mb-2">
                  {t('visibility.channelsTitle', { defaultValue: 'Da dove arrivano le visite' })}
                </h2>
                <DonutSplit data={donutData} colors={GROUP_COLORS}
                            empty={t('visibility.noData', { defaultValue: 'Ancora nessuna visita questo mese.' })} />
              </div>
              <div className={`${cardCls} border-[#376254]/40 bg-[#376254]/5 flex flex-col justify-center`}>
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 mt-0.5 text-[#376254]" aria-hidden />
                  <div>
                    <p className="font-semibold text-foreground">
                      {t('visibility.proofTitle', { defaultValue: 'La prova Aurya' })}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {t('visibility.proofBody', {
                        defaultValue: 'Questo mese Aurya ti ha portato {{visits}} visite da directory e motori di ricerca: traffico che il tuo store da solo non avrebbe raggiunto.',
                        visits: (data?.aurya_visits || 0).toLocaleString(lang),
                      })}
                    </p>
                    <Link to="/public-profile" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[#376254] hover:underline">
                      {t('visibility.proofCta', { defaultValue: 'Cura il tuo profilo pubblico' })} <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* C — trend */}
            <div className={cardCls}>
              <h2 className="text-sm font-semibold mb-2">
                {t('visibility.trendTitle', { defaultValue: 'Visite negli ultimi 12 mesi' })}
              </h2>
              <TrendArea data={trendData}
                         empty={t('visibility.noData', { defaultValue: 'Ancora nessuna visita questo mese.' })} />
              <h3 className="text-xs text-muted-foreground mt-4 mb-1">
                {t('visibility.last30', { defaultValue: 'Ultimi 30 giorni' })}
              </h3>
              <MiniBars data={barsData} height={56}
                        empty={t('visibility.noData', { defaultValue: 'Ancora nessuna visita questo mese.' })} />
            </div>

            {/* D — per ritiro */}
            {(data?.per_retreat || []).length > 0 && (
              <div className={cardCls}>
                <h2 className="text-sm font-semibold mb-3">
                  {t('visibility.perRetreatTitle', { defaultValue: 'I tuoi ritiri questo mese' })}
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-muted-foreground border-b border-border">
                        <th className="py-2 pr-3 font-medium">{t('visibility.colRetreat', { defaultValue: 'Ritiro' })}</th>
                        <th className="py-2 pr-3 font-medium text-right">{t('visibility.colVisits', { defaultValue: 'Visite' })}</th>
                        <th className="py-2 pr-3 font-medium text-right">{t('visibility.colUniques', { defaultValue: 'Unici' })}</th>
                        <th className="py-2 pr-3 font-medium text-right">{t('visibility.colBookings', { defaultValue: 'Prenotazioni' })}</th>
                        <th className="py-2 pr-3 font-medium text-right">{t('visibility.colConversion', { defaultValue: 'Conversione' })}</th>
                        <th className="py-2 font-medium">{t('visibility.colChannel', { defaultValue: 'Canale principale' })}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.per_retreat.map((r) => (
                        <tr key={r.slug} className="border-b border-border/60 last:border-0">
                          <td className="py-2 pr-3 font-medium">{r.title}</td>
                          <td className="py-2 pr-3 text-right tabular-nums">{r.visits}</td>
                          <td className="py-2 pr-3 text-right tabular-nums">{r.uniques}</td>
                          <td className="py-2 pr-3 text-right tabular-nums">{r.bookings}</td>
                          <td className="py-2 pr-3 text-right tabular-nums">{r.conversion_pct}%</td>
                          <td className="py-2 text-muted-foreground">
                            {r.top_channel
                              ? t(`visibility.ch_${r.top_channel}`, { defaultValue: r.top_channel })
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {/* nota privacy: la promessa del banner resta vera */}
        <p className="text-xs text-muted-foreground">
          {t('visibility.privacyNote', { defaultValue: 'Misurazione anonima e aggregata, senza cookie e senza dati personali dei visitatori.' })}
        </p>
      </div>
    </AppLayout>
  );
}
