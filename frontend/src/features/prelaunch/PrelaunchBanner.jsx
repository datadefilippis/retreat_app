/**
 * PrelaunchBanner — avviso "anteprima lancio" sopra la directory (PL6).
 *
 * Si mostra SOLO in pre-lancio (useSiteConfig): dice che i ritiri sono
 * esempi e invita a lasciare l'email. A flag spento non renderizza nulla.
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

  const to = audience === 'operator' ? '/per-operatori' : '/cerca-ritiro';
  return (
    <div className="mx-auto max-w-6xl px-4 pt-4">
      <div className="flex flex-col items-start gap-2 rounded-2xl border border-[#376254]/30 bg-[#376254]/8 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2.5">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[#376254]" />
          <p className="text-sm text-[#2b3a34]">
            <span className="font-semibold">
              {t('banner.title', { defaultValue: 'Stiamo preparando il lancio.' })}
            </span>{' '}
            {t('banner.body', { defaultValue: 'Questi sono ritiri d’esempio: presto qui troverai quelli veri, prenotabili online.' })}
          </p>
        </div>
        <Link to={to}
              className="inline-flex shrink-0 items-center gap-1 rounded-full bg-[#376254] px-3.5 py-1.5 text-xs font-semibold text-white hover:opacity-90">
          {t('banner.cta', { defaultValue: 'Avvisami al lancio' })} <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
