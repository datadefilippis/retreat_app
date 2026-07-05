/**
 * OnboardingBanner — O3 (5/7/2026): finche' la configurazione non e'
 * completa, la dashboard indirizza a /inizia. Stato derivato dai dati
 * (onboarding-status): quando tutto e' fatto sparisce da solo.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Rocket, ArrowRight } from 'lucide-react';
import api from '../../api/client';

export default function OnboardingBanner() {
  const { t } = useTranslation('dashboard');
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.get('/organizations/current/onboarding-status')
      .then(res => { if (mounted) setStatus(res.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);

  if (!status || status.is_complete) return null;
  const missing = status.total - status.completed_count;

  return (
    <Link to="/inizia"
          className="flex items-center justify-between gap-3 rounded-2xl border border-primary/30 bg-primary/5 px-4 py-3 hover:bg-primary/10 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <Rocket className="h-5 w-5 text-primary shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground truncate">
            {t('onboarding.banner_title', { defaultValue: 'Completa la configurazione' })}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('onboarding.banner_body', {
              count: missing,
              defaultValue: 'Ti mancano {{count}} passi per essere online.',
            })}
          </p>
        </div>
      </div>
      <ArrowRight className="h-4 w-4 text-primary shrink-0" />
    </Link>
  );
}
