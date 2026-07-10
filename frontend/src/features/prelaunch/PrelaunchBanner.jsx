/**
 * PrelaunchBanner — avviso "anteprima lancio" sopra le pagine di
 * esplorazione (PL6, doppia CTA PL12).
 *
 * Si mostra SOLO in pre-lancio (useSiteConfig). L'esplorazione è il
 * mezzo, il lead è il fine: da QUALSIASI pagina di anteprima si torna
 * sempre alle due landing — CTA primaria per il pubblico della pagina
 * (audience) + strada secondaria per l'altro pubblico, sempre visibile.
 * A flag spento non renderizza nulla.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Sparkles, ArrowRight } from 'lucide-react';
import { useSiteConfig } from '../../context/SiteConfigContext';

export default function PrelaunchBanner({ audience = 'traveler' }) {
  const { prelaunch } = useSiteConfig();
  const { t } = useTranslation('prelaunch');
  if (!prelaunch) return null;

  const primaryTo = audience === 'operator' ? '/per-operatori' : '/cerca-ritiro';
  const otherTo = audience === 'operator' ? '/cerca-ritiro' : '/per-operatori';
  const otherLabel = audience === 'operator'
    ? t('op.switch', { defaultValue: 'Cerchi un ritiro?' })
    : t('tr.switch', { defaultValue: 'Sei un operatore?' });

  return (
    <div className="mx-auto max-w-6xl px-4 pt-4">
      <div className="flex flex-col items-start gap-3 rounded-2xl border border-[#376254]/30 bg-[#376254]/8 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2.5">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[#376254]" />
          <p className="text-sm text-[#2b3a34]">
            <span className="font-semibold">
              {t('banner.title', { defaultValue: 'Stiamo preparando il lancio.' })}
            </span>{' '}
            {t('banner.body', { defaultValue: 'Questi sono ritiri d’esempio: presto qui troverai quelli veri, prenotabili online.' })}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Link to={primaryTo}
                className="inline-flex items-center gap-1 rounded-full bg-[#376254] px-3.5 py-1.5 text-xs font-semibold text-white hover:opacity-90">
            {t('banner.cta', { defaultValue: 'Avvisami al lancio' })} <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link to={otherTo}
                className="inline-flex items-center rounded-full border border-[#376254]/40 bg-white px-3.5 py-1.5 text-xs font-semibold text-[#376254] hover:bg-[#376254]/10">
            {otherLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
