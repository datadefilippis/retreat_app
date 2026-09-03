/**
 * DashboardPage — il radar unico dell'operatore (CF4, INSIGHTS_ACTION_PLAN).
 *
 * CF4 ha assorbito il sistema di widget pinnabili (widgetRegistry,
 * DashboardWidgetCard, PinToDashboardButton, /api/preferences/dashboard):
 * la home non si configura, si legge. Tutto il contenuto vive in
 * OperatorHome — auto-alimentata, letta dall'alto in un colpo (IG4):
 * i quattro numeri del mese, le cose da fare con link all'azione,
 * prossimi ritiri e andamento incassi (stessa fonte di /incassi).
 * L'analisi approfondita vive nelle pagine dedicate: /incassi,
 * /reviews, /modules/customers-light.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import OperatorHome from './OperatorHome';
import OnboardingBanner from './OnboardingBanner';

export const DashboardPage = () => {
  const { t } = useTranslation('dashboard');
  return (
    <AppLayout>
      <Header title={t('title')} subtitle={t('subtitle')} />
      <div className="p-4 md:p-8 animate-fade-in space-y-6">
        {/* O3 — banner onboarding finché la configurazione non è completa */}
        <OnboardingBanner />
        <OperatorHome />
      </div>
    </AppLayout>
  );
};

export default DashboardPage;
