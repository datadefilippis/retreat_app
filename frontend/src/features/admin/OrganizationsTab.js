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
  Building2, ChevronRight, RefreshCw, CreditCard, Loader2,
  AlertTriangle, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../../lib/utils';
import { PIANI, nomePiano, classePiano, nomeStato } from './pianiAurya';
import AdminOrgBillingActions from './AdminOrgBillingActions';

// ── Helpers ───────────────────────────────────────────────────────────────────


const STATUS_COLORS = {
  active:   'bg-green-100 text-green-700',
  trialing: 'bg-blue-100 text-blue-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-gray-100 text-gray-700',
  manual:   'bg-purple-100 text-purple-700',
  none:     'bg-gray-100 text-gray-500',
};

const PlanBadge = ({ plan }) => (
  <Badge className={classePiano(plan)}>{nomePiano(plan)}</Badge>
);

const StatusBadge = ({ isActive }) =>
  isActive ? (
    <Badge className="bg-green-100 text-green-800">Active</Badge>
  ) : (
    <Badge className="bg-red-100 text-red-800">Suspended</Badge>
  );

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
    // RO (30/8) — bonifica AFianco: via il catalogo moduli e i pricing
    // plans per-modulo (l'era pre-Aurya). Gli abbonamenti VERI sono i
    // piani commerciali (free/retreat/pro): solo quelli si caricano.
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
    setBillingData(null);
    setReconcileResult(null);
    try {
      const orgRes = await adminAPI.getOrganization(orgId);
      setDetailData(orgRes.data);
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

  // ── RT3 — Membro della rete ─────────────────────────────────────────────────

  const handleToggleLegacy = async (org) => {
    try {
      await adminAPI.setLegacyCommerce(org.id, !org.legacy_commerce);
      toast.success(org.legacy_commerce
        ? 'Commerce legacy congelato' : 'Commerce legacy riattivato');
      fetchOrgs();
    } catch { toast.error('Operazione non riuscita'); }
  };

  const handleToggleNetwork = async (org) => {
    const next = !org.network_member;
    const key = `${org.id}_network`;
    setAction(key, true);
    try {
      await adminAPI.setNetworkMember(org.id, next);
      toast.success(next
        ? `"${org.name}" accolta nella rete`
        : `"${org.name}" rimossa dalla rete`);
      fetchOrgs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Aggiornamento rete fallito');
    } finally {
      setAction(key, false);
    }
  };

  // RO (30/8) — il lucchetto della directory: governa /esplora-operatori
  // (la rete resta un sigillo a parte; questo e' solo «appari nelle liste»)
  const handleToggleDirectory = async (org) => {
    const next = !org.directory_listed;
    const key = `${org.id}_directory`;
    setAction(key, true);
    try {
      await adminAPI.setDirectoryListed(org.id, next);
      toast.success(next
        ? `"${org.name}" di nuovo nelle liste pubbliche`
        : `"${org.name}" nascosta dalle liste pubbliche`);
      fetchOrgs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Aggiornamento directory fallito');
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
              Aggiorna
            </Button>
            <Button variant="ghost" size="sm" onClick={handleRunAuditNow}
              disabled={auditRunning} title="Verifica che ogni org sia allineata al suo piano">
              {auditRunning ? 'Controllo…' : 'Controlla i piani'}
            </Button>
          </div>
          {/* Onda 10 Step E.2 — drift overview banner. Always rendered; visual
              severity reflects current per-org overview. Click a metric to
              jump-filter the table; "Run scan" hits the same audit as the
              daily cron job (Step E.1) and refreshes the overview. */}
          {/* PA3 (30/8, la verita' di Aurya): il banner parla SOLO
              quando c'e' un problema — il verde permanente era rumore
              quotidiano. Il controllo a mano vive nel bottone qui sotto. */}
          {anyIssue && (<>
          <div
            className={`mt-3 rounded-md border px-3 py-2 ${
              driftCount > 0
                ? 'border-red-200 bg-red-50'
                : 'border-amber-200 bg-amber-50'
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
                  Piani da riallineare
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
              <span className="text-xs text-muted-foreground">Piano:</span>
              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger className="h-7 text-xs w-[140px]">
                  <SelectValue placeholder="All plans" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tutti i piani</SelectItem>
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

              <span className="text-xs text-muted-foreground ml-1">Stato:</span>
              <Select value={billingStatusFilter} onValueChange={setBillingStatusFilter}>
                <SelectTrigger className="h-7 text-xs w-[140px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tutti gli stati</SelectItem>
                  <SelectItem value="active">Attivo</SelectItem>
                  <SelectItem value="manual">Manuale</SelectItem>
                  <SelectItem value="past_due">Pagamento scaduto</SelectItem>
                  <SelectItem value="canceled">Annullato</SelectItem>
                  <SelectItem value="none">—</SelectItem>
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
          </>)}
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
                    <TableHead>Nome</TableHead>
                    <TableHead>Piano</TableHead>
                    <TableHead>Profilo</TableHead>
                    <TableHead>Stato</TableHead>
                    <TableHead>Creata</TableHead>
                    <TableHead className="text-right">Azioni</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOrgs.map((org) => {
                    const ov = commercialOverview[org.id];
                    return (
                    <TableRow key={org.id}>
                      <TableCell>
                        <div className="font-medium">{org.name}</div>
                        {org.admin_email && (
                          <div className="text-xs text-muted-foreground">{org.admin_email}</div>
                        )}
                        {ov?.recommended_action && (
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {ACTION_LABELS[ov.recommended_action] || ov.recommended_action}
                          </div>
                        )}
                      </TableCell>
                      <TableCell><PlanBadge plan={org.commercial_plan_slug || org.plan} /></TableCell>
                      <TableCell>
                        {org.profile_published && org.profile_slug ? (
                          <a href={`/o/${org.profile_slug}`} target="_blank"
                            rel="noreferrer"
                            className="text-xs text-primary underline underline-offset-2"
                            title="Apri il profilo pubblico">
                            /o/{org.profile_slug} ↗
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground"
                            title="La vetrina non e' pubblicata: non appare in esplora-operatori">
                            non pubblicato
                          </span>
                        )}
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
                            Dettagli
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openPlanDialog(org)}
                          >
                            Piano
                          </Button>
                          {/* RT3 — sigillo della rete: accogli/rimuovi
                              il membro (governa /operatori in fase network) */}
                          <Button
                            variant={org.network_member ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleToggleNetwork(org)}
                            disabled={actionLoading[`${org.id}_network`]}
                            title="Membro della rete Aurya"
                          >
                            {org.network_member ? '✓ Rete' : 'Rete'}
                          </Button>
                          {/* RO (30/8) — il lucchetto della directory:
                              governa la presenza nelle liste pubbliche
                              (/esplora-operatori, sitemap). Ha effetto
                              visibile solo a vetrina pubblicata. */}
                          <Button
                            variant={org.directory_listed ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleToggleDirectory(org)}
                            disabled={actionLoading[`${org.id}_directory`]}
                            title={org.profile_published
                              ? 'Presenza nelle liste pubbliche (esplora-operatori)'
                              : 'Vetrina non pubblicata: il lucchetto vale da quando pubblica'}
                          >
                            {org.directory_listed ? '✓ Directory' : 'Directory'}
                          </Button>
                          {/* TW3 — la strada di ritorno del commerce
                              legacy (physical/digital/corsi/store) */}
                          <Button
                            variant={org.legacy_commerce ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleToggleLegacy(org)}
                            title="Commerce legacy (fisici, digitali, corsi, store)"
                          >
                            {org.legacy_commerce ? '✓ Legacy' : 'Legacy'}
                          </Button>
                          <Button
                            variant={org.is_active ? 'destructive' : 'default'}
                            size="sm"
                            onClick={() => handleToggleStatus(org)}
                            disabled={actionLoading[`${org.id}_status`]}
                          >
                            {org.is_active ? 'Sospendi' : 'Riattiva'}
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
              {/* ── RO (30/8): LO SPECCHIETTO — l'essenziale per la
                  regia: chi e', come si raggiunge, dove appare, e i
                  quattro gesti (rete, directory, sospendi, elimina).
                  Via Industry/Currency/Timezone: reperti AFianco. */}
              {(() => {
                const riga = orgs.find((o) => o.id === detailData.id) || {};
                const titolare = (detailData.users || []).find((u) => u.role === 'admin')
                  || (detailData.users || [])[0];
                return (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-muted-foreground">Piano: </span>
                        <PlanBadge plan={detailData.commercial_plan_slug || riga.commercial_plan_slug} />
                      </div>
                      <div>
                        <span className="text-muted-foreground">Stato: </span>
                        <StatusBadge isActive={detailData.is_active} />
                      </div>
                      <div>
                        <span className="text-muted-foreground">Titolare: </span>
                        {titolare ? `${titolare.name}` : '—'}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Email: </span>
                        {titolare?.email || riga.admin_email || '—'}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Creata: </span>
                        {formatDate(detailData.created_at)}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Profilo pubblico: </span>
                        {riga.profile_published && riga.profile_slug ? (
                          <a href={`/o/${riga.profile_slug}`} target="_blank" rel="noreferrer"
                            className="text-primary underline underline-offset-2">
                            /o/{riga.profile_slug} ↗
                          </a>
                        ) : 'non pubblicato'}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Rete: </span>
                        {riga.network_member ? '✓ membro' : '—'}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Directory: </span>
                        {riga.directory_listed ? '✓ nelle liste' : 'nascosta'}
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      <Button size="sm"
                        variant={riga.network_member ? 'default' : 'outline'}
                        disabled={actionLoading[`${riga.id}_network`]}
                        onClick={() => handleToggleNetwork(riga)}>
                        {riga.network_member ? '✓ Rete' : 'Rete'}
                      </Button>
                      <Button size="sm"
                        variant={riga.directory_listed ? 'default' : 'outline'}
                        disabled={actionLoading[`${riga.id}_directory`]}
                        onClick={() => handleToggleDirectory(riga)}>
                        {riga.directory_listed ? '✓ Directory' : 'Directory'}
                      </Button>
                      <Button size="sm"
                        variant={detailData.is_active ? 'destructive' : 'default'}
                        disabled={actionLoading[`${riga.id}_status`]}
                        onClick={() => handleToggleStatus(riga)}>
                        {detailData.is_active ? 'Sospendi' : 'Riattiva'}
                      </Button>
                      <Button size="sm" variant="outline"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => { setDeleteOrg(riga); setDeleteConfirmName(''); }}>
                        <Trash2 className="h-3.5 w-3.5 mr-1" /> Elimina
                      </Button>
                    </div>
                  </div>
                );
              })()}

              {/* ── Billing Detail (v5+) ──────────────────────────────── */}
              {billingData && (
                <div>
                  <h3 className="font-semibold mb-1 flex items-center gap-1.5">
                    <CreditCard className="h-4 w-4" />
                    Abbonamento
                  </h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                    <span className="text-muted-foreground">Commercial Plan</span>
                    <span><PlanBadge plan={billingData.commercial_plan_slug} /></span>

                    <span className="text-muted-foreground">Billing Status</span>
                    <span>
                      <Badge className={STATUS_COLORS[billingData.billing_status] || STATUS_COLORS.none}>
                        {nomeStato(billingData.billing_status)}
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
                {/* PA3 (30/8) — il MOTORE si ripiega: drift e
                    riallineamento al piano vivono qui, dichiarati come
                    cosa tecnica, non in prima linea. */}
                {(() => {
                  const ov = commercialOverview[detailData.id];
                  const problemi = ov && (ov.is_out_of_sync || ov.has_warnings);
                  return (
                    <details className="mt-6 rounded border px-3 py-2"
                      data-testid="org-stato-tecnico">
                      <summary className="text-sm font-semibold text-muted-foreground cursor-pointer">
                        Stato tecnico (provisioning) — {problemi ? '⚠ da riallineare' : 'allineato'}
                      </summary>
                      <div className="mt-3 space-y-2 text-sm">
                        <p className="text-muted-foreground">
                          Ogni piano accende le sue funzioni in automatico.
                          Se qui segna un disallineamento, «Riallinea»
                          riporta l'org alla definizione del suo piano.
                        </p>
                        <Button variant="outline" size="sm"
                          onClick={async () => {
                            try {
                              await adminAPI.reprovisionOrg(detailData.id);
                              toast.success('Org riallineata al suo piano');
                              fetchCommercialOverview();
                            } catch (err) {
                              toast.error(err.response?.data?.detail || 'Riallineamento fallito');
                            }
                          }}>
                          Riallinea al piano
                        </Button>
                      </div>
                    </details>
                  );
                })()}

                <div className="mt-6">
                  <h3 className="font-semibold mb-2 text-sm uppercase tracking-wide text-muted-foreground">
                    Azioni di fatturazione
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

      {/* ── Dialog «Cambia piano» (PA2) ─────────────────────────────────── */}
      <Dialog open={planOpen} onOpenChange={setPlanOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Cambia piano — {planOrg?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Piano attuale:{' '}
              <strong>{nomePiano(planOrg?.commercial_plan_slug || planOrg?.plan || 'retreat_free')}</strong>
            </p>
            <Select value={planValue} onValueChange={setPlanValue}>
              <SelectTrigger>
                <SelectValue placeholder="Scegli il piano…" />
              </SelectTrigger>
              <SelectContent>
                {commercialPlans.map((cp) => (
                  <SelectItem key={cp.slug} value={cp.slug}>
                    {nomePiano(cp.slug)}
                    {cp.price_monthly > 0 ? ` — €${cp.price_monthly}/mese` : ' — gratuito'}
                    {PIANI[cp.slug]?.riservato ? ' · riservato (solo admin)' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {PIANI[planValue]?.riservato && (
              <p className="text-xs text-amber-700">
                Piano riservato: non compare nel pricing pubblico, lo
                assegni solo tu.
              </p>
            )}
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setPlanOpen(false)}>
                Annulla
              </Button>
              <Button
                onClick={handleSavePlan}
                disabled={planSaving || !planValue}
              >
                {planSaving ? 'Salvo…' : 'Assegna il piano'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
              <p>• Ordini, incassi e prenotazioni</p>
              <p>• Clienti e listino (servizi, ritiri, eventi)</p>
              <p>• Profilo pubblico, foto e file caricati</p>
              <p>• Tracce e condivisioni di Aurya Sound</p>
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
