import React, { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '../../api';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  Building2, ChevronRight, RefreshCw, CreditCard, Loader2, Package,
  CheckCircle2, AlertTriangle, Info, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../../lib/utils';
import OrgCommercialStateDialog from './OrgCommercialStateDialog';
import AdminOrgBillingActions from './AdminOrgBillingActions';

// ── Helpers ───────────────────────────────────────────────────────────────────

const planColors = {
  free:       'bg-gray-100 text-gray-700',
  core:       'bg-blue-100 text-blue-700',
  pro:        'bg-violet-100 text-violet-700',
  enterprise: 'bg-amber-100 text-amber-700',
  // Legacy fallback
  starter:    'bg-blue-100 text-blue-700',
};

const STATUS_COLORS = {
  active:   'bg-green-100 text-green-700',
  trialing: 'bg-blue-100 text-blue-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-gray-100 text-gray-700',
  manual:   'bg-purple-100 text-purple-700',
  none:     'bg-gray-100 text-gray-500',
};

const PlanBadge = ({ plan }) => (
  <Badge className={planColors[plan] || 'bg-gray-100 text-gray-700'}>
    {plan || 'N/A'}
  </Badge>
);

const StatusBadge = ({ isActive }) =>
  isActive ? (
    <Badge className="bg-green-100 text-green-800">Active</Badge>
  ) : (
    <Badge className="bg-red-100 text-red-800">Suspended</Badge>
  );

const SyncBadge = ({ overview }) => {
  if (!overview) return <Badge className="bg-gray-50 text-gray-400 text-xs">—</Badge>;
  if (overview.is_out_of_sync) {
    return (
      <Badge className="bg-red-100 text-red-700 text-xs">
        <AlertTriangle className="h-3 w-3 mr-0.5" /> Drift
      </Badge>
    );
  }
  if (overview.has_warnings) {
    return (
      <Badge className="bg-amber-100 text-amber-700 text-xs">
        <Info className="h-3 w-3 mr-0.5" /> Warning
      </Badge>
    );
  }
  return (
    <Badge className="bg-green-100 text-green-700 text-xs">
      <CheckCircle2 className="h-3 w-3 mr-0.5" /> OK
    </Badge>
  );
};

const ACTION_LABELS = {
  review_missing_catalog_plan:      'Missing plan',
  consider_reprovision:             'Reprovision',
  review_unexpected_subscriptions:  'Unexpected subs',
  review_limits_drift:              'Limits drift',
  review_manual_assignment:         'Manual',
  review_billing_status:            'Billing',
  investigate_legacy_plan_fallback: 'Legacy fallback',
};

// ── Component ─────────────────────────────────────────────────────────────────

const OrganizationsTab = () => {
  const [orgs, setOrgs]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal]     = useState(0);

  // Known/available modules catalog (fetched once from /modules/available)
  // Used to show ALL modules in detail dialog, not just DB records.
  const [availableModules, setAvailableModules] = useState([]);

  // Detail dialog
  const [detailOpen, setDetailOpen]       = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData]       = useState(null);

  // Plan change dialog
  const [planOpen, setPlanOpen]     = useState(false);
  const [planOrg, setPlanOrg]       = useState(null);
  const [planValue, setPlanValue]   = useState('');
  const [planSaving, setPlanSaving] = useState(false);

  // Per-row action loading  { "<orgId>_status": bool, "<orgId>_<moduleKey>": bool }
  const [actionLoading, setActionLoading] = useState({});

  const setAction = (key, val) =>
    setActionLoading((prev) => ({ ...prev, [key]: val }));

  // Pricing plans (fetched once on mount)
  const [pricingPlans, setPricingPlans] = useState([]);

  // Subscriptions for the currently open detail dialog
  const [orgSubs, setOrgSubs] = useState([]);
  const [subsLoading, setSubsLoading] = useState(false);

  // Subscription change dialog
  const [subDialogOpen, setSubDialogOpen]     = useState(false);
  const [subDialogModule, setSubDialogModule] = useState('');
  const [subDialogPlanId, setSubDialogPlanId] = useState('');
  const [subSaving, setSubSaving]             = useState(false);

  // Commercial state dialog (Phase 3C)
  const [commercialStateOpen, setCommercialStateOpen] = useState(false);
  const [commercialStateOrgId, setCommercialStateOrgId] = useState(null);
  const [commercialStateOrgName, setCommercialStateOrgName] = useState('');

  // Commercial overview (Phase 3D)
  const [commercialOverview, setCommercialOverview] = useState({});  // keyed by org.id
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [commercialFilter, setCommercialFilter] = useState('all'); // all|drift|warnings|restricted

  // Onda 10 Step E.2 — drift audit on demand
  const [auditRunning, setAuditRunning] = useState(false);
  const [lastAuditSummary, setLastAuditSummary] = useState(null);
  const [lastAuditAt, setLastAuditAt] = useState(null);

  // Onda 10 Step E.3 — plan + billing status filters (compose with
  // commercialFilter; all default to 'all' = no narrowing).
  const [planFilter, setPlanFilter] = useState('all');
  const [billingStatusFilter, setBillingStatusFilter] = useState('all');

  // v5+ commercial billing state
  const [commercialPlans, setCommercialPlans] = useState([]);
  const [billingData, setBillingData]         = useState(null);
  const [reconcileResult, setReconcileResult] = useState(null);
  const [reconcileLoading, setReconcileLoading] = useState(false);

  // ── Fetch available module catalog once on mount ────────────────────────────

  useEffect(() => {
    adminAPI.listAvailableModules()
      .then((res) => {
        // Keep only available modules (skip future/unavailable ones)
        const avail = (res.data ?? []).filter((m) => m.is_available);
        setAvailableModules(avail);
      })
      .catch(() => {
        // Non-critical: detail dialog will fall back to showing only DB records
      });
    adminAPI.listPricingPlans()
      .then((res) => setPricingPlans(res.data ?? []))
      .catch(() => {});
    adminAPI.getCommercialPlans()
      .then((data) => setCommercialPlans(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  // ── Data fetch ──────────────────────────────────────────────────────────────

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminAPI.listOrganizations(0, 100);
      setOrgs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchOrgs(); }, [fetchOrgs]);

  // ── Commercial overview fetch ──────────────────────────────────────────────

  const fetchCommercialOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await adminAPI.getCommercialOverview(0, 200);
      const byId = {};
      (Array.isArray(data) ? data : []).forEach((s) => { byId[s.id] = s; });
      setCommercialOverview(byId);
    } catch {
      // Non-critical — table still works without commercial data
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => { fetchCommercialOverview(); }, [fetchCommercialOverview]);

  // ── Onda 10 Step E.2: drift audit on demand ─────────────────────────────────

  const handleRunAuditNow = useCallback(async () => {
    setAuditRunning(true);
    try {
      const result = await adminAPI.runBillingAuditNow();
      setLastAuditSummary(result);
      setLastAuditAt(new Date());
      const { scanned = 0, high_issues = 0, medium_issues = 0, email_sent } = result || {};
      if (high_issues > 0) {
        toast.error(
          `Drift audit: ${scanned} orgs · ${high_issues} HIGH · ${medium_issues} MEDIUM` +
          (email_sent ? ' · email digest sent' : ''),
        );
      } else if (medium_issues > 0) {
        toast.warning(`Drift audit: ${scanned} orgs · ${medium_issues} MEDIUM (no HIGH)`);
      } else {
        toast.success(`Drift audit: ${scanned} orgs · all clean`);
      }
      // Refresh per-org overview so banners and rows reflect latest state
      fetchCommercialOverview();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Audit failed');
    } finally {
      setAuditRunning(false);
    }
  }, [fetchCommercialOverview]);

  // Aggregate counts derived from commercialOverview (live, no extra fetch).
  const driftCount = orgs.filter((o) => commercialOverview[o.id]?.is_out_of_sync).length;
  const warningsCount = orgs.filter((o) => commercialOverview[o.id]?.has_warnings).length;
  const restrictedCount = orgs.filter(
    (o) => commercialOverview[o.id]?.drift_flags?.billing_restricted,
  ).length;
  const anyIssue = driftCount > 0 || warningsCount > 0 || restrictedCount > 0;

  // ── Detail dialog ───────────────────────────────────────────────────────────

  const openDetail = async (orgId) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailData(null);
    setOrgSubs([]);
    setBillingData(null);
    setReconcileResult(null);
    try {
      const [orgRes, subsRes] = await Promise.all([
        adminAPI.getOrganization(orgId),
        adminAPI.listOrgSubscriptions(orgId),
      ]);
      setDetailData(orgRes.data);
      setOrgSubs(subsRes.data ?? []);
      // Fetch billing data (non-blocking — detail dialog renders immediately)
      adminAPI.getOrgBilling(orgId)
        .then((data) => setBillingData(data))
        .catch(() => setBillingData(null));
    } catch (err) {
      toast.error('Failed to load organization details');
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  // ── Suspend / Reactivate ────────────────────────────────────────────────────

  const handleToggleStatus = async (org) => {
    const newStatus = !org.is_active;
    const verb = newStatus ? 'reactivate' : 'suspend';
    if (!window.confirm(`Are you sure you want to ${verb} "${org.name}"?`)) return;

    const key = `${org.id}_status`;
    setAction(key, true);
    try {
      await adminAPI.setOrgStatus(org.id, newStatus);
      toast.success(`Organization ${newStatus ? 'reactivated' : 'suspended'}`);
      fetchOrgs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update organization status');
    } finally {
      setAction(key, false);
    }
  };

  // ── Hard Delete Org ─────────────────────────────────────────────────────────

  const [deleteOrg, setDeleteOrg] = useState(null);
  const [deleteConfirmName, setDeleteConfirmName] = useState('');
  const [deleting, setDeleting] = useState(false);

  const handleDeleteOrg = async () => {
    setDeleting(true);
    try {
      const result = await adminAPI.hardDeleteOrganization(deleteOrg.id);
      const total = Object.values(result.deleted_counts || {}).filter(v => v > 0).reduce((a, b) => a + b, 0);
      toast.success(`Organizzazione "${deleteOrg.name}" eliminata — ${total} record rimossi`);
      setDeleteOrg(null);
      setDeleteConfirmName('');
      fetchOrgs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete organization');
    } finally {
      setDeleting(false);
    }
  };

  // ── Change Plan ─────────────────────────────────────────────────────────────

  const openPlanDialog = (org) => {
    setPlanOrg(org);
    setPlanValue(org.commercial_plan_slug || org.plan || 'free');
    setPlanOpen(true);
  };

  const handleSavePlan = async () => {
    if (!planValue) return;
    setPlanSaving(true);
    try {
      await adminAPI.setOrgCommercialPlan(planOrg.id, planValue);
      toast.success(`Commercial plan set to "${planValue}" for ${planOrg.name}`);
      setPlanOpen(false);
      fetchOrgs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error setting commercial plan');
    } finally {
      setPlanSaving(false);
    }
  };

  // ── Module toggle ───────────────────────────────────────────────────────────

  const handleToggleModule = async (orgId, moduleKey, isCurrentlyActive) => {
    // Explicit confirmation before any module state change
    const verb = isCurrentlyActive ? 'Deactivate' : 'Activate';
    if (!window.confirm(`${verb} module "${moduleKey}" for this organization?`)) return;

    const key = `${orgId}_${moduleKey}`;
    setAction(key, true);
    try {
      if (isCurrentlyActive) {
        await adminAPI.deactivateModule(orgId, moduleKey);
        toast.success(`Module "${moduleKey}" deactivated`);
      } else {
        await adminAPI.activateModule(orgId, moduleKey);
        toast.success(`Module "${moduleKey}" activated`);
      }
      // Refresh detail data separately — a refresh failure should not
      // hide the success toast or revert the optimistic UI update.
      try {
        const res = await adminAPI.getOrganization(orgId);
        setDetailData(res.data);
      } catch {
        toast.warning('Module updated — close and reopen Details for the latest state.');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update module');
    } finally {
      setAction(key, false);
    }
  };

  // ── Subscription handlers ──────────────────────────────────────────────────

  const openSubDialog = (moduleKey) => {
    const existing = orgSubs.find((s) => s.module_key === moduleKey);
    setSubDialogModule(moduleKey);
    setSubDialogPlanId(existing?.pricing_plan_id || '');
    setSubDialogOpen(true);
  };

  const handleSaveSub = async () => {
    if (!subDialogPlanId || !detailData) return;
    setSubSaving(true);
    try {
      await adminAPI.setOrgSubscription(detailData.id, subDialogModule, subDialogPlanId);
      toast.success(`Subscription updated for ${subDialogModule}`);
      setSubDialogOpen(false);
      // Refresh subscriptions
      const res = await adminAPI.listOrgSubscriptions(detailData.id);
      setOrgSubs(res.data ?? []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update subscription');
    } finally {
      setSubSaving(false);
    }
  };

  const handleCancelSub = async (moduleKey) => {
    if (!detailData) return;
    if (!window.confirm(`Cancel subscription for "${moduleKey}"? The org will fall back to the free tier.`)) return;
    const key = `${detailData.id}_sub_${moduleKey}`;
    setAction(key, true);
    try {
      await adminAPI.cancelOrgSubscription(detailData.id, moduleKey);
      toast.success(`Subscription cancelled for ${moduleKey}`);
      const res = await adminAPI.listOrgSubscriptions(detailData.id);
      setOrgSubs(res.data ?? []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to cancel subscription');
    } finally {
      setAction(key, false);
    }
  };

  // ── Reconcile ──────────────────────────────────────────────────────────────

  const handleReconcile = async (apply = false) => {
    if (!detailData) return;
    if (apply && !window.confirm(
      'Apply billing corrections from Stripe? This will update the database to match Stripe state.',
    )) return;
    setReconcileLoading(true);
    setReconcileResult(null);
    try {
      const result = await adminAPI.reconcileOrgBilling(detailData.id, apply);
      setReconcileResult(result);
      if (apply && result.applied) {
        toast.success('Billing corrections applied');
        // Refresh billing data
        adminAPI.getOrgBilling(detailData.id)
          .then((data) => setBillingData(data))
          .catch(() => {});
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reconcile failed');
    } finally {
      setReconcileLoading(false);
    }
  };

  // Get unique module keys that have pricing plans
  const modulesWithPlans = [...new Set(pricingPlans.map((p) => p.module_key))];

  // ── Module list for detail dialog ───────────────────────────────────────────
  //
  // Merges the platform-level catalog (availableModules) with the org's current
  // DB records (detailData.modules).  If the catalog isn't loaded yet, falls
  // back to showing only DB records.
  //
  const buildModuleList = (orgDetail) => {
    if (!orgDetail) return [];

    const dbMap = {};
    (orgDetail.modules ?? []).forEach((m) => { dbMap[m.module_key] = m; });

    if (availableModules.length > 0) {
      // Full merged view: catalog drives the list
      return availableModules.map((m) => ({
        module_key: m.key,
        name:       m.name,
        category:   m.category,
        is_active:  dbMap[m.key]?.is_active ?? false,
        in_db:      !!dbMap[m.key],
      }));
    }

    // Fallback: only DB records (catalog not loaded)
    return (orgDetail.modules ?? []).map((m) => ({
      module_key: m.module_key,
      name:       m.module_key,
      category:   null,
      is_active:  m.is_active,
      in_db:      true,
    }));
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      {/* ── Organizations list ────────────────────────────────────────────── */}
      <Card className="border border-border">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Organizations
              </CardTitle>
              <CardDescription>
                {total} organization{total !== 1 ? 's' : ''} on the platform
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => { fetchOrgs(); fetchCommercialOverview(); }} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
          {/* Onda 10 Step E.2 — drift overview banner. Always rendered; visual
              severity reflects current per-org overview. Click a metric to
              jump-filter the table; "Run scan" hits the same audit as the
              daily cron job (Step E.1) and refreshes the overview. */}
          <div
            className={`mt-3 rounded-md border px-3 py-2 ${
              driftCount > 0
                ? 'border-red-200 bg-red-50'
                : warningsCount > 0 || restrictedCount > 0
                ? 'border-amber-200 bg-amber-50'
                : 'border-emerald-200 bg-emerald-50'
            }`}
          >
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 text-sm">
                <AlertTriangle
                  className={`h-4 w-4 ${
                    anyIssue ? 'text-red-600' : 'text-emerald-600'
                  }`}
                />
                <span className="font-medium">
                  {anyIssue ? 'Catalog drift detected' : 'Catalog in sync'}
                </span>
                {lastAuditAt && (
                  <span className="text-xs text-muted-foreground">
                    · last scan {lastAuditAt.toLocaleTimeString()}
                    {lastAuditSummary?.email_sent ? ' · email sent' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={() => setCommercialFilter('drift')}
                  className={`text-xs px-2 py-1 rounded border ${
                    driftCount > 0
                      ? 'border-red-300 bg-white text-red-700 hover:bg-red-100'
                      : 'border-gray-200 bg-white text-gray-500'
                  }`}
                  disabled={driftCount === 0}
                  title="Show only orgs out-of-sync with catalog"
                >
                  <span className="font-semibold">{driftCount}</span> drift
                </button>
                <button
                  type="button"
                  onClick={() => setCommercialFilter('warnings')}
                  className={`text-xs px-2 py-1 rounded border ${
                    warningsCount > 0
                      ? 'border-amber-300 bg-white text-amber-700 hover:bg-amber-100'
                      : 'border-gray-200 bg-white text-gray-500'
                  }`}
                  disabled={warningsCount === 0}
                  title="Show only orgs with non-blocking warnings"
                >
                  <span className="font-semibold">{warningsCount}</span> warnings
                </button>
                <button
                  type="button"
                  onClick={() => setCommercialFilter('restricted')}
                  className={`text-xs px-2 py-1 rounded border ${
                    restrictedCount > 0
                      ? 'border-red-300 bg-white text-red-700 hover:bg-red-100'
                      : 'border-gray-200 bg-white text-gray-500'
                  }`}
                  disabled={restrictedCount === 0}
                  title="Show only orgs with restricted billing"
                >
                  <span className="font-semibold">{restrictedCount}</span> restricted
                </button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleRunAuditNow}
                  disabled={auditRunning}
                  title="Run the same audit as the daily cron — read-only"
                >
                  {auditRunning ? (
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3 w-3 mr-1" />
                  )}
                  Run scan
                </Button>
              </div>
            </div>
            {lastAuditSummary && (lastAuditSummary.high_issues > 0 || lastAuditSummary.medium_issues > 0) && (
              <div className="text-xs text-muted-foreground mt-1.5">
                Last scan: {lastAuditSummary.scanned} orgs scanned ·{' '}
                <span className="text-red-700 font-medium">
                  {lastAuditSummary.high_issues} HIGH
                </span>{' '}
                ·{' '}
                <span className="text-amber-700">
                  {lastAuditSummary.medium_issues} MEDIUM
                </span>
              </div>
            )}
          </div>

          {/* Commercial filter bar (Phase 3D) */}
          <div className="flex gap-1 mt-3 flex-wrap items-center">
            {[
              { key: 'all', label: 'All' },
              { key: 'drift', label: 'Drift', color: 'text-red-600' },
              { key: 'warnings', label: 'Warnings', color: 'text-amber-600' },
              { key: 'restricted', label: 'Billing restricted', color: 'text-red-600' },
            ].map(({ key, label, color }) => (
              <Button
                key={key}
                variant={commercialFilter === key ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setCommercialFilter(key)}
              >
                <span className={commercialFilter !== key ? color : ''}>{label}</span>
                {key !== 'all' && (
                  <span className="ml-1 opacity-70">
                    ({orgs.filter((o) => {
                      const ov = commercialOverview[o.id];
                      if (!ov) return false;
                      if (key === 'drift') return ov.is_out_of_sync;
                      if (key === 'warnings') return ov.has_warnings;
                      if (key === 'restricted') return ov.drift_flags?.billing_restricted;
                      return false;
                    }).length})
                  </span>
                )}
              </Button>
            ))}

            {/* Onda 10 Step E.3 — plan + billing status dropdowns. Compose
                with the commercial filter (AND). */}
            <div className="flex items-center gap-2 ml-2 pl-2 border-l border-border">
              <span className="text-xs text-muted-foreground">Plan:</span>
              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger className="h-7 text-xs w-[140px]">
                  <SelectValue placeholder="All plans" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All plans</SelectItem>
                  {commercialPlans
                    .filter((p) => !p.is_addon)
                    .map((p) => (
                      <SelectItem key={p.slug} value={p.slug}>
                        {p.name || p.slug}
                        {p.is_archived ? ' (archived)' : ''}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>

              <span className="text-xs text-muted-foreground ml-1">Status:</span>
              <Select value={billingStatusFilter} onValueChange={setBillingStatusFilter}>
                <SelectTrigger className="h-7 text-xs w-[140px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="trialing">Trialing</SelectItem>
                  <SelectItem value="past_due">Past due</SelectItem>
                  <SelectItem value="canceled">Canceled</SelectItem>
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                </SelectContent>
              </Select>

              {(planFilter !== 'all' || billingStatusFilter !== 'all') && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    setPlanFilter('all');
                    setBillingStatusFilter('all');
                  }}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
            </div>
          ) : orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No organizations found.
            </p>
          ) : (() => {
            // Apply commercial filter (Phase 3D) AND plan/status filter (Step E.3)
            const filteredOrgs = orgs.filter((o) => {
              // 1. Commercial state filter
              if (commercialFilter !== 'all') {
                const ov = commercialOverview[o.id];
                if (!ov) return false;
                if (commercialFilter === 'drift' && !ov.is_out_of_sync) return false;
                if (commercialFilter === 'warnings' && !ov.has_warnings) return false;
                if (commercialFilter === 'restricted' && !ov.drift_flags?.billing_restricted) return false;
              }
              // 2. Plan filter (commercial_plan_slug, fallback legacy plan)
              if (planFilter !== 'all') {
                const orgPlan = o.commercial_plan_slug || o.plan || 'free';
                if (orgPlan !== planFilter) return false;
              }
              // 3. Billing status filter
              if (billingStatusFilter !== 'all') {
                const status = o.billing_status || 'none';
                if (status !== billingStatusFilter) return false;
              }
              return true;
            });
            return filteredOrgs.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No organizations match the selected filter.
              </p>
            ) : (
            <div className="overflow-x-auto">
              {(commercialFilter !== 'all' || planFilter !== 'all' || billingStatusFilter !== 'all') && (
                <div className="text-xs text-muted-foreground mb-2">
                  Showing {filteredOrgs.length} of {orgs.length} orgs
                  {commercialFilter !== 'all' && ` · state: ${commercialFilter}`}
                  {planFilter !== 'all' && ` · plan: ${planFilter}`}
                  {billingStatusFilter !== 'all' && ` · status: ${billingStatusFilter}`}
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Sync</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOrgs.map((org) => {
                    const ov = commercialOverview[org.id];
                    return (
                    <TableRow key={org.id}>
                      <TableCell>
                        <div className="font-medium">{org.name}</div>
                        {org.industry && (
                          <div className="text-xs text-muted-foreground">{org.industry}</div>
                        )}
                        {ov?.recommended_action && (
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {ACTION_LABELS[ov.recommended_action] || ov.recommended_action}
                          </div>
                        )}
                      </TableCell>
                      <TableCell><PlanBadge plan={org.commercial_plan_slug || org.plan} /></TableCell>
                      <TableCell>
                        {overviewLoading
                          ? <Skeleton className="h-5 w-14" />
                          : <SyncBadge overview={ov} />}
                      </TableCell>
                      <TableCell><StatusBadge isActive={org.is_active} /></TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(org.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1 flex-wrap">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openDetail(org.id)}
                          >
                            <ChevronRight className="h-4 w-4 mr-1" />
                            Details
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openPlanDialog(org)}
                          >
                            Plan
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setCommercialStateOrgId(org.id);
                              setCommercialStateOrgName(org.name);
                              setCommercialStateOpen(true);
                            }}
                          >
                            <Package className="h-3.5 w-3.5 mr-1" />
                            Commercial
                          </Button>
                          <Button
                            variant={org.is_active ? 'destructive' : 'default'}
                            size="sm"
                            onClick={() => handleToggleStatus(org)}
                            disabled={actionLoading[`${org.id}_status`]}
                          >
                            {org.is_active ? 'Suspend' : 'Reactivate'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => { setDeleteOrg(org); setDeleteConfirmName(''); }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            );
          })()}
        </CardContent>
      </Card>

      {/* ── Org Detail Dialog ─────────────────────────────────────────────── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {detailData?.name || 'Organization Detail'}
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : detailData ? (
            <div className="space-y-6 text-sm">
              {/* ── Metadata grid ─────────────────────────────────────── */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-muted-foreground">Plan: </span>
                  <PlanBadge plan={detailData.commercial_plan_slug || detailData.plan} />
                </div>
                <div>
                  <span className="text-muted-foreground">Status: </span>
                  <StatusBadge isActive={detailData.is_active} />
                </div>
                <div>
                  <span className="text-muted-foreground">Industry: </span>
                  {detailData.industry || '—'}
                </div>
                <div>
                  <span className="text-muted-foreground">Currency: </span>
                  {detailData.currency || '—'}
                </div>
                <div>
                  <span className="text-muted-foreground">Timezone: </span>
                  {detailData.timezone || '—'}
                </div>
                <div>
                  <span className="text-muted-foreground">Created: </span>
                  {formatDate(detailData.created_at)}
                </div>
              </div>

              {/* ── Billing Detail (v5+) ──────────────────────────────── */}
              {billingData && (
                <div>
                  <h3 className="font-semibold mb-1 flex items-center gap-1.5">
                    <CreditCard className="h-4 w-4" />
                    Billing
                  </h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                    <span className="text-muted-foreground">Commercial Plan</span>
                    <span><PlanBadge plan={billingData.commercial_plan_slug} /></span>

                    <span className="text-muted-foreground">Billing Status</span>
                    <span>
                      <Badge className={STATUS_COLORS[billingData.billing_status] || STATUS_COLORS.none}>
                        {billingData.billing_status || 'none'}
                      </Badge>
                    </span>

                    <span className="text-muted-foreground">Interval</span>
                    <span>{billingData.billing_interval || '—'}</span>

                    <span className="text-muted-foreground">Trial Ends</span>
                    <span>{billingData.trial_ends_at ? formatDate(billingData.trial_ends_at) : '—'}</span>

                    <span className="text-muted-foreground">Current Period End</span>
                    <span>{billingData.current_period_end ? formatDate(billingData.current_period_end) : '—'}</span>

                    <span className="text-muted-foreground">Stripe Customer</span>
                    <span className="font-mono text-xs">{billingData.stripe_customer_id || '—'}</span>

                    <span className="text-muted-foreground">Stripe Subscription</span>
                    <span className="font-mono text-xs">{billingData.stripe_subscription_id || '—'}</span>

                    <span className="text-muted-foreground">Assigned By</span>
                    <span>{billingData.plan_assigned_by || '—'}</span>

                    {billingData.cancel_at_period_end && (
                      <>
                        <span className="text-muted-foreground">Cancels at Period End</span>
                        <span><Badge className="bg-orange-100 text-orange-700">Yes</Badge></span>
                      </>
                    )}
                  </div>

                  {/* Reconcile Action */}
                  {billingData.stripe_subscription_id && (
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReconcile(false)}
                          disabled={reconcileLoading}
                        >
                          {reconcileLoading
                            ? <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                            : <RefreshCw className="mr-2 h-3 w-3" />}
                          Check Stripe Sync
                        </Button>
                        {reconcileResult && !reconcileResult.in_sync && !reconcileResult.applied && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleReconcile(true)}
                            disabled={reconcileLoading}
                          >
                            Apply Corrections
                          </Button>
                        )}
                      </div>

                      {reconcileResult && (
                        <div className={`rounded-md p-2 text-xs ${
                          reconcileResult.in_sync
                            ? 'bg-green-50 text-green-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}>
                          {reconcileResult.in_sync ? (
                            'In sync with Stripe.'
                          ) : reconcileResult.reconciliation === 'no_stripe_subscription' ? (
                            'No Stripe subscription linked.'
                          ) : (
                            <div>
                              <p className="font-medium mb-1">Diffs found:</p>
                              {Object.entries(reconcileResult.diffs || {}).map(([field, diff]) => (
                                <div key={field} className="ml-2">
                                  <strong>{field}</strong>: {String(diff.internal)} → {String(diff.stripe)}
                                </div>
                              ))}
                              {reconcileResult.applied && (
                                <p className="mt-1 font-medium text-green-700">Corrections applied.</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── Modules (merged catalog view) ─────────────────────── */}
              {(() => {
                const moduleList = buildModuleList(detailData);
                const activeCount = moduleList.filter((m) => m.is_active).length;
                return (
                  <div>
                    <h3 className="font-semibold mb-1">
                      Modules
                    </h3>
                    <p className="text-xs text-muted-foreground mb-3">
                      {activeCount} active / {moduleList.length} available
                    </p>
                    {moduleList.length === 0 ? (
                      <p className="text-muted-foreground">No modules configured.</p>
                    ) : (
                      <div className="space-y-2">
                        {moduleList.map((mod) => (
                          <div
                            key={mod.module_key}
                            className="flex items-center justify-between rounded border px-3 py-2"
                          >
                            <div>
                              <span className="font-medium">{mod.name}</span>
                              {mod.category && (
                                <span className="ml-1.5 text-xs text-muted-foreground">
                                  · {mod.category}
                                </span>
                              )}
                              <span
                                className={`ml-2 text-xs font-medium ${
                                  mod.is_active ? 'text-green-600' : 'text-muted-foreground'
                                }`}
                              >
                                {mod.is_active ? 'active' : 'inactive'}
                              </span>
                            </div>
                            <Button
                              variant={mod.is_active ? 'outline' : 'default'}
                              size="sm"
                              disabled={actionLoading[`${detailData.id}_${mod.module_key}`]}
                              onClick={() =>
                                handleToggleModule(
                                  detailData.id,
                                  mod.module_key,
                                  mod.is_active,
                                )
                              }
                            >
                              {mod.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* ── Module Subscriptions (Advanced — collapsed) ─────── */}
              {modulesWithPlans.length > 0 && (
                <details className="mt-2">
                  <summary className="text-sm font-semibold text-muted-foreground cursor-pointer hover:text-foreground">
                    Module Subscriptions (Advanced) — {modulesWithPlans.length} modules
                  </summary>
                  <p className="text-xs text-muted-foreground mt-1 mb-3">
                    Per-module overrides bypass the commercial plan. Use &quot;Change Commercial Plan&quot; for normal plan changes.
                  </p>
                  <div className="space-y-2">
                    {modulesWithPlans.map((mk) => {
                      const sub = orgSubs.find((s) => s.module_key === mk);
                      return (
                        <div
                          key={mk}
                          className="flex items-center justify-between rounded border px-3 py-2"
                        >
                          <div>
                            <span className="font-medium">{mk}</span>
                            {sub ? (
                              <>
                                <Badge className="ml-2 bg-blue-100 text-blue-700">
                                  {sub.plan_name || sub.pricing_plan_id}
                                </Badge>
                                {sub.price_monthly != null && (
                                  <span className="ml-1.5 text-xs text-muted-foreground">
                                    {sub.price_monthly === 0
                                      ? 'Free'
                                      : `€${sub.price_monthly}/mo`}
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="ml-2 text-xs text-muted-foreground">
                                No subscription — free tier
                              </span>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openSubDialog(mk)}
                            >
                              {sub ? 'Change' : 'Assign'}
                            </Button>
                            {sub && (
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => handleCancelSub(mk)}
                                disabled={actionLoading[`${detailData.id}_sub_${mk}`]}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}

              {/* ── Users ─────────────────────────────────────────────── */}
              <div>
                <h3 className="font-semibold mb-3">
                  Users ({detailData.users?.length || 0})
                </h3>
                {detailData.users?.length === 0 ? (
                  <p className="text-muted-foreground">No users in this organization.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Role</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailData.users?.map((u) => (
                          <TableRow key={u.id}>
                            <TableCell className="font-medium">{u.name}</TableCell>
                            <TableCell className="text-muted-foreground">{u.email}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{u.role}</Badge>
                            </TableCell>
                            <TableCell>
                              <StatusBadge isActive={u.is_active} />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* ── v5.8 / Onda 8: System admin billing actions ──────────────
                    4 collapsible sub-panels: Usage / Custom Plan / Extend
                    Trial / Impersonate. Mounted at the bottom of the detail
                    dialog so existing fields stay above the fold. */}
                <div className="mt-6">
                  <h3 className="font-semibold mb-2 text-sm uppercase tracking-wide text-muted-foreground">
                    Billing actions
                  </h3>
                  <AdminOrgBillingActions
                    orgId={detailData.id}
                    onClose={() => { /* keep detail dialog open */ }}
                  />
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* ── Change Commercial Plan Dialog ─────────────────────────────────── */}
      <Dialog open={planOpen} onOpenChange={setPlanOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Change Commercial Plan — {planOrg?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Current plan:{' '}
              <strong>{planOrg?.commercial_plan_slug || planOrg?.plan || 'free'}</strong>
            </p>
            <p className="text-xs text-muted-foreground">
              This changes the effective billing plan and re-provisions all module subscriptions.
            </p>
            <Select value={planValue} onValueChange={setPlanValue}>
              <SelectTrigger>
                <SelectValue placeholder="Select plan…" />
              </SelectTrigger>
              <SelectContent>
                {commercialPlans.map((cp) => (
                  <SelectItem key={cp.slug} value={cp.slug}>
                    {cp.name}{' '}
                    {cp.price_monthly > 0 ? `(€${cp.price_monthly}/mo)` : '(Free)'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setPlanOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSavePlan}
                disabled={planSaving || !planValue}
              >
                {planSaving ? 'Saving…' : 'Set Commercial Plan'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── Subscription Change Dialog ──────────────────────────────────── */}
      <Dialog open={subDialogOpen} onOpenChange={setSubDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              <CreditCard className="inline h-4 w-4 mr-1.5 -mt-0.5" />
              Subscription — {subDialogModule}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Org: <strong>{detailData?.name}</strong>
            </p>
            <Select value={subDialogPlanId} onValueChange={setSubDialogPlanId}>
              <SelectTrigger>
                <SelectValue placeholder="Select pricing plan…" />
              </SelectTrigger>
              <SelectContent>
                {pricingPlans
                  .filter((p) => p.module_key === subDialogModule)
                  .map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name}
                      {p.price_monthly === 0
                        ? ' — Free'
                        : ` — €${p.price_monthly}/mo`}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setSubDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveSub}
                disabled={subSaving || !subDialogPlanId}
              >
                {subSaving ? 'Saving…' : 'Save Subscription'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── Commercial State Dialog (Phase 3C) ──────────────────────── */}
      <OrgCommercialStateDialog
        orgId={commercialStateOrgId}
        orgName={commercialStateOrgName}
        open={commercialStateOpen}
        onOpenChange={setCommercialStateOpen}
      />

      {/* ── Hard Delete Org Dialog ───────────────────────────────────── */}
      <Dialog open={!!deleteOrg} onOpenChange={(open) => { if (!open) { setDeleteOrg(null); setDeleteConfirmName(''); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <Trash2 className="h-5 w-5" />
              Eliminazione definitiva
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Stai per eliminare <strong>definitivamente</strong> l'organizzazione{' '}
              <strong>"{deleteOrg?.name}"</strong> e tutti i suoi dati:
            </p>
            <div className="text-xs bg-red-50 border border-red-200 rounded p-3 space-y-1 text-red-700">
              <p>• Tutti gli utenti dell'organizzazione</p>
              <p>• Acquisti, vendite, spese, costi fissi</p>
              <p>• Clienti, fornitori, prodotti</p>
              <p>• File caricati, conversazioni AI, alert</p>
              <p>• Abbonamento Stripe (se presente)</p>
              <p className="font-semibold pt-1">Questa azione è IRREVERSIBILE.</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">
                Digita "<strong>{deleteOrg?.name}</strong>" per confermare:
              </p>
              <Input
                value={deleteConfirmName}
                onChange={(e) => setDeleteConfirmName(e.target.value)}
                placeholder={deleteOrg?.name}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => { setDeleteOrg(null); setDeleteConfirmName(''); }}>
                Annulla
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteOrg}
                disabled={deleteConfirmName !== deleteOrg?.name || deleting}
              >
                {deleting ? 'Eliminazione in corso…' : 'Elimina definitivamente'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default OrganizationsTab;
