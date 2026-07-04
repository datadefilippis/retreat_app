/**
 * OrgCommercialStateDialog — Phase 3C
 *
 * Displays the commercial-state diagnostic for one organization inside
 * the existing System Admin panel. Shows drift flags, provisioned modules,
 * catalog plan info, and offers a controlled reprovision action.
 *
 * Integrates with:
 *   GET  /admin/catalog/organizations/{org_id}/commercial-state
 *   POST /admin/catalog/organizations/{org_id}/reprovision-commercial-plan
 */

import React, { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '../../api';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import {
  AlertTriangle, CheckCircle2, Info, RefreshCw, Loader2,
  ShieldAlert, Package, Layers, Activity,
} from 'lucide-react';
import { toast } from 'sonner';

// ── Status/flag color helpers ────────────────────────────────────────────────

const BILLING_STATUS_COLORS = {
  active:   'bg-green-100 text-green-700',
  trialing: 'bg-blue-100 text-blue-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-gray-100 text-gray-700',
  manual:   'bg-purple-100 text-purple-700',
  none:     'bg-gray-100 text-gray-500',
};

const PLAN_COLORS = {
  free:       'bg-gray-100 text-gray-700',
  core:       'bg-blue-100 text-blue-700',
  pro:        'bg-violet-100 text-violet-700',
  enterprise: 'bg-amber-100 text-amber-700',
};

const DriftFlag = ({ label, value, variant = 'drift' }) => {
  if (!value) return null;
  const colors = variant === 'warning'
    ? 'bg-amber-50 text-amber-700 border-amber-200'
    : 'bg-red-50 text-red-700 border-red-200';
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium ${colors}`}>
      {variant === 'warning'
        ? <Info className="h-3.5 w-3.5 flex-shrink-0" />
        : <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />}
      {label}
    </div>
  );
};

const AlignedBadge = () => (
  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-green-200 bg-green-50 text-green-700 text-xs font-medium">
    <CheckCircle2 className="h-3.5 w-3.5" />
    Catalog-aligned
  </div>
);

const ACTION_LABELS = {
  review_missing_catalog_plan:      'Review missing catalog plan',
  consider_reprovision:             'Consider reprovision',
  review_unexpected_subscriptions:  'Review unexpected subscriptions',
  review_limits_drift:              'Review limits drift',
  review_manual_assignment:         'Review manual assignment',
  review_billing_status:            'Review billing status',
  investigate_legacy_plan_fallback: 'Investigate legacy plan fallback',
};

// ── Main component ──────────────────────────────────────────────────────────

const OrgCommercialStateDialog = ({ orgId, orgName, open, onOpenChange }) => {
  const [state, setState]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  // Reprovision state
  const [reprovisioning, setReprovisioning]     = useState(false);
  const [reprovisionResult, setReprovisionResult] = useState(null);

  const fetchState = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminAPI.getOrgCommercialState(orgId);
      setState(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load commercial state');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (open && orgId) {
      fetchState();
      setReprovisionResult(null);
    }
  }, [open, orgId, fetchState]);

  const handleReprovision = async () => {
    if (!window.confirm(
      'Reprovision this organization?\n\n'
      + '• Aligns module subscriptions to the current catalog definition\n'
      + '• Does NOT change pricing for existing Stripe subscribers\n'
      + '• Does NOT mutate Stripe directly\n\n'
      + 'This action is audited.'
    )) return;

    setReprovisioning(true);
    setReprovisionResult(null);
    try {
      const result = await adminAPI.reprovisionOrg(orgId);
      setReprovisionResult(result);
      if (result?.result?.changed) {
        toast.success('Organization reprovisioned successfully');
      } else {
        toast.info('Reprovision completed — no changes needed');
      }
      // Refresh state after reprovision
      await fetchState();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reprovision failed');
    } finally {
      setReprovisioning(false);
    }
  };

  const flags = state?.drift_flags || {};
  const summary = state?.summary || {};
  const org = state?.organization || {};
  const catalogPlan = state?.catalog_plan;
  const modules = state?.provisioned_modules || [];

  const hasDriftFlags = flags.catalog_plan_missing
    || flags.missing_module_subscriptions
    || flags.unexpected_module_subscriptions
    || flags.module_plan_mismatch
    || flags.limits_mismatch;

  const hasWarnings = flags.manual_assignment_detected
    || flags.billing_restricted
    || flags.legacy_plan_fallback_risk;

  const showReprovision = hasDriftFlags
    && !flags.catalog_plan_missing
    && summary.recommended_actions?.includes('consider_reprovision');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Commercial State — {orgName || orgId}
          </DialogTitle>
        </DialogHeader>

        {/* Loading */}
        {loading && (
          <div className="space-y-3 py-4">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="py-6 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-400 mb-2" />
            <p className="text-sm text-red-600">{error}</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={fetchState}>
              Retry
            </Button>
          </div>
        )}

        {/* Data loaded */}
        {state && !loading && !error && (
          <div className="space-y-5">

            {/* ── Organization Summary ──────────────────────────────────── */}
            <section>
              <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                <Activity className="h-4 w-4" /> Organization
              </h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                <div className="text-muted-foreground">Plan</div>
                <div>
                  <Badge className={PLAN_COLORS[org.commercial_plan_slug] || 'bg-gray-100 text-gray-700'}>
                    {org.commercial_plan_slug || 'N/A'}
                  </Badge>
                </div>
                <div className="text-muted-foreground">Billing Status</div>
                <div>
                  <Badge className={BILLING_STATUS_COLORS[org.billing_status] || 'bg-gray-100 text-gray-500'}>
                    {org.billing_status || 'none'}
                  </Badge>
                </div>
                {org.plan_assigned_by && (
                  <>
                    <div className="text-muted-foreground">Assigned by</div>
                    <div className="text-sm">{org.plan_assigned_by}</div>
                  </>
                )}
              </div>
            </section>

            {/* ── Drift & Sync Status ──────────────────────────────────── */}
            <section>
              <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4" /> Sync Status
              </h3>

              {!hasDriftFlags && !hasWarnings && <AlignedBadge />}

              <div className="flex flex-wrap gap-2">
                {/* Drift issues */}
                <DriftFlag label="Catalog plan missing" value={flags.catalog_plan_missing} />
                <DriftFlag label="Missing module subscriptions" value={flags.missing_module_subscriptions} />
                <DriftFlag label="Unexpected module subscriptions" value={flags.unexpected_module_subscriptions} />
                <DriftFlag label="Module-plan mismatch" value={flags.module_plan_mismatch} />
                <DriftFlag label="Limits mismatch" value={flags.limits_mismatch} />

                {/* Operational warnings */}
                <DriftFlag label="Manual assignment" value={flags.manual_assignment_detected} variant="warning" />
                <DriftFlag label="Billing restricted" value={flags.billing_restricted} variant="warning" />
                <DriftFlag label="Legacy plan fallback risk" value={flags.legacy_plan_fallback_risk} variant="warning" />
              </div>

              {/* Recommended actions */}
              {summary.recommended_actions?.length > 0 && (
                <div className="mt-3 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">Recommended actions:</div>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-0.5">
                    {summary.recommended_actions.map((a) => (
                      <li key={a}>{ACTION_LABELS[a] || a}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Detail lists */}
              {summary.missing_modules?.length > 0 && (
                <p className="text-xs text-red-600 mt-2">
                  Missing modules: {summary.missing_modules.join(', ')}
                </p>
              )}
              {summary.unexpected_modules?.length > 0 && (
                <p className="text-xs text-amber-600 mt-2">
                  Unexpected modules: {summary.unexpected_modules.join(', ')}
                </p>
              )}
              {summary.mismatched_modules?.length > 0 && (
                <p className="text-xs text-red-600 mt-2">
                  Mismatched tiers: {summary.mismatched_modules.join(', ')}
                </p>
              )}
            </section>

            {/* ── Catalog Plan Definition ───────────────────────────────── */}
            <section>
              <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                <Layers className="h-4 w-4" /> Catalog Plan
              </h3>
              {!catalogPlan ? (
                <p className="text-xs text-red-600 italic">
                  Catalog plan "{org.commercial_plan_slug}" not found in current catalog
                </p>
              ) : (
                <div className="text-sm space-y-2">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                    <div className="text-muted-foreground">Name</div>
                    <div>{catalogPlan.name}</div>
                    <div className="text-muted-foreground">Trial days</div>
                    <div>{catalogPlan.trial_days}</div>
                    <div className="text-muted-foreground">Pricing</div>
                    <div>
                      €{catalogPlan.price_monthly}/mo
                      {catalogPlan.price_yearly && ` · €${catalogPlan.price_yearly}/yr`}
                    </div>
                    <div className="text-muted-foreground">Visibility</div>
                    <div className="flex gap-1.5">
                      {catalogPlan.is_public && <Badge variant="outline" className="text-xs">Public</Badge>}
                      {catalogPlan.is_self_serve && <Badge variant="outline" className="text-xs">Self-serve</Badge>}
                      {!catalogPlan.is_public && <Badge variant="outline" className="text-xs text-muted-foreground">Hidden</Badge>}
                    </div>
                  </div>
                  {/* Module plans mapping */}
                  {catalogPlan.module_plans && Object.keys(catalogPlan.module_plans).length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs font-medium text-muted-foreground mb-1">Expected module tiers:</div>
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(catalogPlan.module_plans).map(([mk, slug]) => (
                          <Badge key={mk} variant="outline" className="text-xs">
                            {mk} → {slug}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* ── Provisioned Modules ──────────────────────────────────── */}
            <section>
              <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                <Package className="h-4 w-4" /> Provisioned Modules ({modules.length})
              </h3>
              {modules.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">No active module subscriptions</p>
              ) : (
                <div className="space-y-2">
                  {modules.map((m) => (
                    <div key={m.module_key} className="border rounded-md p-2.5 text-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{m.module_key}</span>
                        <Badge className="bg-green-100 text-green-700 text-xs">{m.status}</Badge>
                      </div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                        {m.pricing_plan_slug && (
                          <>
                            <div>Tier</div>
                            <div className="text-foreground">{m.pricing_plan_slug}</div>
                          </>
                        )}
                        {m.assigned_by && (
                          <>
                            <div>Assigned by</div>
                            <div className="text-foreground">{m.assigned_by}</div>
                          </>
                        )}
                        {m.limits && Object.keys(m.limits).length > 0 && (
                          <>
                            <div>Limits</div>
                            <div className="text-foreground">
                              {Object.entries(m.limits).map(([k, v]) => (
                                <span key={k} className="mr-2">{k}: {v === -1 ? '∞' : v}</span>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* ── Reprovision Action ───────────────────────────────────── */}
            <section className="border-t pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold">Reprovision to Catalog</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Re-align module subscriptions to the current catalog definition.
                    Does not affect Stripe or existing billing.
                  </p>
                </div>
                <Button
                  variant={showReprovision ? 'default' : 'outline'}
                  size="sm"
                  onClick={handleReprovision}
                  disabled={reprovisioning || flags.catalog_plan_missing}
                >
                  {reprovisioning ? (
                    <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Reprovisioning...</>
                  ) : (
                    <><RefreshCw className="h-4 w-4 mr-1" /> Reprovision</>
                  )}
                </Button>
              </div>

              {/* Reprovision result */}
              {reprovisionResult && (
                <div className={`mt-3 p-3 rounded-md text-xs border ${
                  reprovisionResult.result?.changed
                    ? 'bg-green-50 border-green-200'
                    : 'bg-gray-50 border-gray-200'
                }`}>
                  <div className="font-medium mb-1">
                    {reprovisionResult.result?.changed
                      ? '✓ Reprovision applied — subscriptions updated'
                      : '— No changes needed — already aligned'}
                  </div>
                  {reprovisionResult.result?.changed && reprovisionResult.before && (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div>
                        <div className="font-medium text-muted-foreground mb-0.5">Before</div>
                        {reprovisionResult.before.map((m) => (
                          <div key={m.module_key}>{m.module_key} → {m.pricing_plan_slug || '?'}</div>
                        ))}
                      </div>
                      <div>
                        <div className="font-medium text-muted-foreground mb-0.5">After</div>
                        {reprovisionResult.after.map((m) => (
                          <div key={m.module_key}>{m.module_key} → {m.pricing_plan_slug || '?'}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default OrgCommercialStateDialog;
