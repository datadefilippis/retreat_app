/**
 * CustomerInsightsPage — Phase 2 of the customer insights restructuring.
 *
 * Replaces the legacy CustomersLightPage at the /customers route. The
 * legacy page stays mounted at /customers-legacy for 30 days as
 * safety-net (cf. PHASE_2 plan in CUSTOMER_INSIGHTS_FORMULAS.md).
 *
 * Layout
 * ──────
 *   [period selector]  ───────────────────────────  [refresh]
 *   ┌─ KPI grid ────────────────────────────────────────────┐
 *   │  Each card has 3-part info-box (def / calc / read)    │
 *   │  Cards for risk segments are clickable → drill        │
 *   └───────────────────────────────────────────────────────┘
 *   [segment filters]  [status filters]
 *   ┌─ Concentration ──┐ ┌─ Segment distribution ──────────┐
 *   │ top5 / top10     │ │ list + bar widget               │
 *   └──────────────────┘ └──────────────────────────────────┘
 *   ┌─ Customer table  ────────────────────────────────────┐
 *   │  filters + pagination + export CSV                    │
 *   └───────────────────────────────────────────────────────┘
 *
 * State stays local (URL search params later in Phase 2.5 if it adds
 * value — for v1 the page-mount-default works fine).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { RefreshCw, AlertTriangle, Info, ChevronDown, Users, UserPlus, MessageCircle, Phone } from 'lucide-react';
import { useCurrency } from '../../context/AuthContext';
import { formatCurrency } from '../../lib/utils';
import { AppLayout, Header } from '../../components/Layout';
import { customerInsightsAPI } from '../../api/customerInsights';
import { useLocale } from './hooks/useLocale';
import { PeriodSelector } from '../../components/insights/PeriodSelector';
// SegmentFilters is now rendered inside CustomerTable (filters apply
// to the table only, not to the KPI grid above).
import { KpiOverviewSection } from './components/KpiOverviewSection';
import { CustomerTable } from './components/CustomerTable';
import { CustomerProfileSlide } from './components/CustomerProfileSlide';
import { StatCard, DonutSplit } from '../../components/charts';
import ContactActions from '../../components/ContactActions';

// CF6 — semantica fissa segmenti nella palette del kit (inattivi = terracotta)
const SEGMENT_COLORS = {
  top: '#376254',
  active: '#5E8073',
  new: '#B9A96B',
  occasional: '#A9695B',
  inactive: '#C97B5D',
};

const PAGE_SIZE = 50;

export default function CustomerInsightsPage() {
  const { t } = useTranslation('customerInsights');
  const currency = useCurrency();

  // Filter state
  // RF4 — 12 mesi: il respiro giusto per un'attività stagionale
  const [period, setPeriod] = useState('12m');
  const [segment, setSegment] = useState(null);
  const [customerStatus, setCustomerStatus] = useState(null);
  // CI-admin-vis: two new filter states, null = no filter (default).
  // Owned at page level so they participate in the list-fetch
  // useEffect, the page-reset useEffect, AND the export call.
  const [hasAccount, setHasAccount] = useState(null);
  const [marketingOptedIn, setMarketingOptedIn] = useState(null);
  const [search, setSearch] = useState('');

  // Data state
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);

  const [customersData, setCustomersData] = useState(null);
  const [customersLoading, setCustomersLoading] = useState(true);
  const [page, setPage] = useState(1);

  // Profile slide state
  const [profileCustomerId, setProfileCustomerId] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);

  // CF6 — conteggi azionabili (totali da liste filtrate, pageSize=1)
  const [recontactCount, setRecontactCount] = useState(null);
  const [crossSell, setCrossSell] = useState(null);
  const [crossSellOpen, setCrossSellOpen] = useState(false);
  const [withPhoneCount, setWithPhoneCount] = useState(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      customerInsightsAPI.getCustomers({ segment: 'inactive', marketingOptedIn: true, page: 1, pageSize: 1 }),
      customerInsightsAPI.getCustomers({ hasPhone: true, page: 1, pageSize: 1 }),
      customerInsightsAPI.crossSell(),
    ]).then(([rec, ph, xs]) => {
      if (cancelled) return;
      setRecontactCount(rec.status === 'fulfilled' ? (rec.value.data?.total ?? 0) : 0);
      setWithPhoneCount(ph.status === 'fulfilled' ? (ph.value.data?.total ?? 0) : 0);
      setCrossSell(xs.status === 'fulfilled' ? xs.value.data : null);
    });
    return () => { cancelled = true; };
  }, []);

  // Filtro pronto "Da ricontattare": la lista È il piano di ricontatto
  const applyRecontactFilter = () => {
    setSegment('inactive');
    setCustomerStatus(null);
    setMarketingOptedIn(true);
  };

  // ── Fetch overview ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setOverviewLoading(true);
    setOverviewError(null);
    customerInsightsAPI.getOverview({ period })
      .then((res) => {
        if (cancelled) return;
        setOverview(res.data);
      })
      .catch((err) => {
        if (cancelled) return;
        setOverviewError(err?.response?.data?.detail || err?.message || 'unknown');
      })
      .finally(() => {
        if (!cancelled) setOverviewLoading(false);
      });
    return () => { cancelled = true; };
  }, [period]);

  // ── Fetch customer list ───────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setCustomersLoading(true);
    customerInsightsAPI.getCustomers({
      segment,
      customerStatus,
      hasAccount,
      marketingOptedIn,
      search: search || undefined,
      page,
      pageSize: PAGE_SIZE,
    })
      .then((res) => {
        if (cancelled) return;
        setCustomersData(res.data);
      })
      .catch(() => {
        if (cancelled) return;
        setCustomersData({ total: 0, rows: [], page: 1 });
      })
      .finally(() => {
        if (!cancelled) setCustomersLoading(false);
      });
    return () => { cancelled = true; };
  }, [segment, customerStatus, hasAccount, marketingOptedIn, search, page]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [segment, customerStatus, hasAccount, marketingOptedIn, search]);

  // ── Drill-down from KPI cards ────────────────────────────────────
  const onSegmentDrill = (drillKey) => {
    if (drillKey === 'at_risk_status') {
      setCustomerStatus('at_risk');
      setSegment(null);
    } else if (drillKey === 'inactive_segment') {
      setSegment('inactive');
      setCustomerStatus(null);
    }
  };

  const onSelectCustomer = (customerId) => {
    setProfileCustomerId(customerId);
    setProfileOpen(true);
  };

  const profileCustomerSummary = useMemo(() => {
    if (!profileCustomerId || !customersData?.rows) return null;
    return customersData.rows.find((r) => r.customer_id === profileCustomerId) || null;
  }, [profileCustomerId, customersData]);

  const onExportCsv = async () => {
    // Goes through axios so the JWT bearer token is attached. Using
    // window.open would skip the Authorization header → 403 from the
    // backend. The helper triggers the actual download via a hidden
    // <a download> element backed by an object URL.
    try {
      // CI-admin-vis: the export now respects the two new filters too,
      // so a merchant who filtered "Iscritti al marketing" gets a CSV
      // ready to feed Mailchimp/Brevo without manual post-processing.
      await customerInsightsAPI.exportCustomers({
        segment,
        customerStatus,
        hasAccount,
        marketingOptedIn,
      });
    } catch (err) {
      // Surface the failure inline; very rare path so a soft alert is OK.
      // eslint-disable-next-line no-alert
      alert(t('page.errorBody'));
      // eslint-disable-next-line no-console
      console.error('exportCustomers failed', err);
    }
  };

  const onRefresh = () => {
    setOverviewLoading(true);
    setCustomersLoading(true);
    customerInsightsAPI.getOverview({ period })
      .then((res) => setOverview(res.data))
      .finally(() => setOverviewLoading(false));
    customerInsightsAPI.getCustomers({
      segment, customerStatus, hasAccount, marketingOptedIn,
      page, pageSize: PAGE_SIZE,
    })
      .then((res) => setCustomersData(res.data))
      .finally(() => setCustomersLoading(false));
  };

  // ── Render ────────────────────────────────────────────────────────
  return (
    <AppLayout>
      <Header
        title={t('page.title')}
        subtitle={t('page.subtitle')}
      />
      <div className="p-4 md:p-6 space-y-5 max-w-7xl mx-auto">
        {/* Period selector + refresh row */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <PeriodSelector value={period} onChange={setPeriod} />
          <Button
            size="sm"
            variant="outline"
            onClick={onRefresh}
            disabled={overviewLoading || customersLoading}
            className="h-7 text-xs self-start md:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${
              (overviewLoading || customersLoading) ? 'animate-spin' : ''
            }`} />
            {t('page.refreshButton')}
          </Button>
        </div>

      {/* Error banner */}
      {overviewError && (
        <Card className="border-red-200 bg-red-50/50 dark:bg-red-950/10">
          <CardContent className="p-3 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 text-red-600 shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-red-900 dark:text-red-300">
                {t('page.errorTitle')}
              </p>
              <p className="text-xs text-red-800 dark:text-red-400/80 mt-0.5">
                {String(overviewError)}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* CF6 — 4 numeri essenziali: come va + dove agire */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          loading={overviewLoading}
          icon={Users}
          label={t('essential.total', { defaultValue: 'Clienti totali' })}
          value={overview?.concentration?.total_customers?.toLocaleString()}
        />
        <StatCard
          loading={overviewLoading}
          icon={UserPlus}
          label={t('essential.new', { defaultValue: 'Nuovi (periodo)' })}
          value={overview?.kpis?.new_customers?.value?.toLocaleString()}
          delta={overview?.kpis?.new_customers?.delta_pct}
        />
        <button type="button" onClick={applyRecontactFilter} className="text-left"
                title={t('essential.recontactHint', { defaultValue: 'Inattivi con consenso marketing: clicca per vedere la lista' })}>
          <StatCard
            loading={recontactCount === null}
            icon={MessageCircle}
            accent={Boolean(recontactCount)}
            label={t('essential.recontact', { defaultValue: 'Da ricontattare' })}
            value={recontactCount?.toLocaleString()}
            sublabel={t('essential.recontactSub', { defaultValue: 'inattivi con consenso' })}
          />
        </button>
        <StatCard
          loading={withPhoneCount === null}
          icon={Phone}
          label={t('essential.withPhone', { defaultValue: 'Con telefono' })}
          value={withPhoneCount?.toLocaleString()}
          sublabel={t('essential.withPhoneSub', { defaultValue: 'raggiungibili su WhatsApp' })}
        />
      </div>

      {/* CF6 — UN grafico: composizione clienti per segmento */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{t('segments.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DonutSplit
            height={190}
            colors={SEGMENT_COLORS}
            data={(overview?.segments || []).map((sg) => ({
              key: sg.segment,
              label: t(`segment.${sg.segment}`, { defaultValue: sg.segment }),
              value: sg.count,
            }))}
          />
        </CardContent>
      </Card>

      {/* CG4 — cross-sell: chi ha fatto un ritiro ma mai una consulenza */}
      {crossSell && crossSell.count > 0 && (
        <div className="rounded-2xl border border-[#376254]/30 bg-[#376254]/5 p-4">
          <button type="button" onClick={() => setCrossSellOpen((v) => !v)}
                  className="w-full text-left flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-[#376254]">
                {t('crossSell.title', {
                  defaultValue: '{{count}} clienti hanno fatto un ritiro ma mai una consulenza',
                  count: crossSell.count,
                })}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t('crossSell.hint', { defaultValue: 'Il cross-sell più naturale: hanno già fiducia in te. Il messaggio è pronto.' })}
              </p>
            </div>
            <span className="text-xs text-[#376254] shrink-0">
              {crossSellOpen
                ? t('crossSell.hide', { defaultValue: 'Nascondi' })
                : t('crossSell.show', { defaultValue: 'Vedi lista' })}
            </span>
          </button>
          {crossSellOpen && (
            <ul className="mt-3 divide-y divide-border">
              {crossSell.candidates.map((c) => (
                <li key={c.customer_id} className="flex items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{c.name || '—'}</p>
                    <p className="text-xs text-muted-foreground truncate">{c.email || c.phone || ''}</p>
                  </div>
                  <ContactActions
                    name={c.name}
                    email={c.email}
                    phone={c.phone}
                    customerId={c.customer_id}
                    context="generic"
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Customer table — filters live INSIDE the card so it's
          visually obvious they only affect this list, not the KPI
          grid above. */}
      <CustomerTable
        data={customersData}
        loading={customersLoading}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
        onSelectCustomer={onSelectCustomer}
        onExportCsv={onExportCsv}
        segment={segment}
        onSegmentChange={setSegment}
        customerStatus={customerStatus}
        onStatusChange={setCustomerStatus}
        hasAccount={hasAccount}
        onHasAccountChange={setHasAccount}
        marketingOptedIn={marketingOptedIn}
        onMarketingOptedInChange={setMarketingOptedIn}
        search={search}
        onSearchChange={setSearch}
      />

      {/* CF6 — l'analitica pesante resta, ma non fa rumore: accordion chiuso */}
      <div className="rounded-2xl border border-border">
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground hover:bg-muted/40 rounded-2xl transition-colors"
        >
          {t('essential.advanced', { defaultValue: 'Analisi avanzata (KPI dettagliati, concentrazione, ricavo per segmento)' })}
          <ChevronDown className={`h-4 w-4 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
        </button>
        {advancedOpen && (
          <div className="p-4 pt-1 space-y-4">
            <KpiOverviewSection
              kpis={overview?.kpis}
              loading={overviewLoading}
              period={overview?.period}
              onSegmentDrill={onSegmentDrill}
            />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ConcentrationCard data={overview?.concentration} loading={overviewLoading} currency={currency} />
              <SegmentDistributionCard
                segments={overview?.segments}
                loading={overviewLoading}
                onSegmentClick={(s) => setSegment(s)}
                currency={currency}
              />
            </div>
          </div>
        )}
      </div>

      {/* Profile slide-over */}
      <CustomerProfileSlide
        customerId={profileCustomerId}
        customerSummary={profileCustomerSummary}
        open={profileOpen}
        onOpenChange={setProfileOpen}
      />
      </div>
    </AppLayout>
  );
}


// ── Sub-section: concentration card ──────────────────────────────────────


function ConcentrationCard({ data, loading, currency }) {
  const { t } = useTranslation('customerInsights');
  const locale = useLocale();
  const [showInfo, setShowInfo] = useState(false);

  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium flex items-center gap-1.5">
          {t('concentration.title')}
          <button
            onClick={() => setShowInfo((v) => !v)}
            className="text-muted-foreground/40 hover:text-primary"
            aria-label={t('insightCard.infoButton')}
            type="button"
          >
            <Info className="h-3 w-3" />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {showInfo ? (
          <div className="space-y-1.5 text-xs text-muted-foreground bg-primary/[0.02] rounded p-3 border border-primary/20">
            <p>{t('concentration.infobox.def')}</p>
            <p className="italic text-muted-foreground/70">{t('concentration.infobox.calc')}</p>
            <p className="font-medium text-foreground/70">{t('concentration.infobox.read')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Metric
              label={t('concentration.top5')}
              value={loading ? '\u2026' : formatPct(data?.top_5_share_pct, locale)}
            />
            <Metric
              label={t('concentration.top10')}
              value={loading ? '\u2026' : formatPct(data?.top_10_share_pct, locale)}
            />
            <Metric
              label={t('concentration.totalCustomers')}
              value={loading ? '\u2026' : (data?.total_customers ?? 0).toLocaleString(locale)}
            />
            <Metric
              label={t('concentration.totalRevenue')}
              value={loading ? '\u2026' : formatCurrency(data?.total_revenue || 0, currency)}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}


// ── Sub-section: segment distribution card ─────────────────────────────


function SegmentDistributionCard({ segments, loading, onSegmentClick, currency }) {
  const { t } = useTranslation('customerInsights');
  const locale = useLocale();
  const [showInfo, setShowInfo] = useState(false);

  const total = (segments || []).reduce((sum, s) => sum + (s.revenue || 0), 0);

  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium flex items-center gap-1.5">
          {t('segments.title')}
          <button
            onClick={() => setShowInfo((v) => !v)}
            className="text-muted-foreground/40 hover:text-primary"
            aria-label={t('insightCard.infoButton')}
            type="button"
          >
            <Info className="h-3 w-3" />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {showInfo ? (
          <div className="space-y-1.5 text-xs text-muted-foreground bg-primary/[0.02] rounded p-3 border border-primary/20">
            <p>{t('segments.infobox.def')}</p>
            <p className="italic text-muted-foreground/70">{t('segments.infobox.calc')}</p>
            <p className="font-medium text-foreground/70">{t('segments.infobox.read')}</p>
          </div>
        ) : loading ? (
          <p className="text-sm text-muted-foreground">\u2026</p>
        ) : !segments || segments.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t('page.empty')}
          </p>
        ) : (
          <ul className="space-y-1.5">
            {segments.map((s) => (
              <li
                key={s.segment}
                onClick={() => onSegmentClick(s.segment)}
                className="flex items-center justify-between text-sm cursor-pointer hover:bg-muted/40 rounded px-2 py-1.5 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-medium">
                    {t(`segment.${s.segment}`, { defaultValue: s.segment })}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {s.count} {t('segments.countLabel')}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="tabular-nums text-muted-foreground">
                    {formatCurrency(s.revenue || 0, currency)}
                  </span>
                  <BarSparkline pct={(s.revenue / total) * 100 || 0} />
                  <span className="font-medium tabular-nums w-12 text-right">
                    {formatPct(s.pct_of_revenue, locale)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}


function Metric({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-heading text-lg font-semibold mt-0.5">{value}</p>
    </div>
  );
}


function BarSparkline({ pct }) {
  const width = Math.max(0, Math.min(100, pct));
  return (
    <span className="inline-block w-16 h-1.5 rounded bg-muted overflow-hidden align-middle">
      <span
        className="block h-full bg-primary/60"
        style={{ width: `${width}%` }}
      />
    </span>
  );
}


function formatPct(v, locale = 'it-IT') {
  if (v == null) return '\u2014';
  return `${v.toLocaleString(locale, { maximumFractionDigits: 1 })}\u00A0%`;
}
