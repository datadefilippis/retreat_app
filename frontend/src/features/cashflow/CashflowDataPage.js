import React, { useState } from 'react';
import { Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { FolderOpen, Download } from 'lucide-react';
import { toast } from 'sonner';
import { exportAPI } from '../../api';
import { SalesSection } from './SalesSection';
import { ExpensesSection } from './ExpensesSection';
import { PurchasesSection } from './PurchasesSection';
import { FixedCostsSection } from './FixedCostsSection';
import { useTranslation } from 'react-i18next';
import QuotaProgressBanner from '../../components/QuotaProgressBanner';
import { useEntitlements } from '../../hooks/useEntitlements';

const VALID_TABS = ['sales', 'expenses', 'purchases', 'fixed_costs'];

export const CashflowDataPage = () => {
  const { t } = useTranslation('cashflow_monitor');
  const { tab } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [exporting, setExporting] = useState(false);

  const supplierId = searchParams.get('supplier_id');

  const activeTab = VALID_TABS.includes(tab) ? tab : 'sales';

  // Onda 10 Step F.2 — surface a page-level QuotaProgressBanner for the
  // data_rows quota. Banner self-hides if usage <60% (see component logic),
  // so the page renders unchanged for healthy orgs. Shared across all 4
  // tabs because every cashflow CRUD path counts against the same quota.
  const { getMetric } = useEntitlements();
  const dataRowsMetric = getMetric('data_rows');

  const handleTabChange = (newTab) => {
    navigate(`/modules/cashflow/data/${newTab}`, { replace: true });
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportAPI.downloadCashflow(activeTab, 'all');
      toast.success(t('data_page.export_done'));
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        toast.error(t('data_page.export_pro'));
      } else {
        toast.error(t('data_page.export_error'));
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppLayout>
      <Header title={t('data_page.title')} subtitle={t('data_page.subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleExport}
              disabled={exporting}
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">
                {exporting ? t('data_page.exporting') : t('data_page.export_csv')}
              </span>
              <span className="sm:hidden">
                {exporting ? t('data_page.exporting') : t('data_page.export_csv_short', { defaultValue: 'CSV' })}
              </span>
            </Button>
            <Link to="/datasets">
              <Button variant="outline" size="sm" className="gap-1.5">
                <FolderOpen className="h-4 w-4" />
                <span className="hidden sm:inline">{t('data_page.manage_files')}</span>
                <span className="sm:hidden">{t('data_page.manage_files_short', { defaultValue: 'File' })}</span>
              </Button>
            </Link>
          </>
        }
      />

      <div className="page-container section-gap animate-fade-in">
        {dataRowsMetric && (
          <QuotaProgressBanner
            metric="data_rows"
            used={dataRowsMetric.used || 0}
            limit={dataRowsMetric.limit ?? 0}
            addonSlug={dataRowsMetric.addon_slug}
            onUpgradeClick={() => navigate('/billing')}
            className="mb-4"
          />
        )}
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="w-full md:w-auto">
            <TabsTrigger value="sales" className="flex-1 md:flex-none px-2.5 md:px-4 text-xs md:text-sm">{t('data_page.tab_sales')}</TabsTrigger>
            <TabsTrigger value="expenses" className="flex-1 md:flex-none px-2.5 md:px-4 text-xs md:text-sm">{t('data_page.tab_expenses')}</TabsTrigger>
            <TabsTrigger value="purchases" className="flex-1 md:flex-none px-2.5 md:px-4 text-xs md:text-sm">{t('data_page.tab_purchases')}</TabsTrigger>
            <TabsTrigger value="fixed_costs" className="flex-1 md:flex-none px-2.5 md:px-4 text-xs md:text-sm">{t('data_page.tab_fixed_costs')}</TabsTrigger>
          </TabsList>

          <TabsContent value="sales" className="mt-6">
            <SalesSection />
          </TabsContent>

          <TabsContent value="expenses" className="mt-6">
            <ExpensesSection />
          </TabsContent>

          <TabsContent value="purchases" className="mt-6">
            <PurchasesSection supplierId={supplierId} />
          </TabsContent>

          <TabsContent value="fixed_costs" className="mt-6">
            <FixedCostsSection />
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
};

export default CashflowDataPage;
