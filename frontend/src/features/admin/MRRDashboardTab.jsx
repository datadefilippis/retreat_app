/**
 * MRRDashboardTab — cross-org billing health dashboard for system admins.
 *
 * Onda 8 (v5.8). Pulls /api/admin/billing-overview/mrr and renders:
 *   · Big-number MRR (€/mo), active subs, active addons, churn 30d
 *   · Breakdown table: MRR per plan slug
 *   · Breakdown table: MRR per addon slug (which packs are popular)
 *   · Upselling candidates list (orgs with quota warnings in last 7d)
 *
 * Read-only / no side effects. Refreshes manually via "Refresh" button.
 * No timeseries — point-in-time snapshot only (timeseries needs daily
 * sampling, out of scope for v5.8).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, RefreshCw, TrendingUp, Users, Package, TrendingDown, ExternalLink } from 'lucide-react';
import { adminAPI } from '../../api';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';


function _formatEur(v) {
  if (v == null) return '€0';
  return `€${Number(v).toFixed(2)}`;
}


export default function MRRDashboardTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminAPI.getMrrOverview();
      setData(res);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground p-6">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading MRR dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 p-4 rounded text-red-800 text-sm">
        Failed to load: {String(error)}
      </div>
    );
  }

  if (!data) return null;

  const planEntries = Object.entries(data.mrr_by_plan || {}).sort((a, b) => b[1] - a[1]);
  const addonEntries = Object.entries(data.mrr_by_addon || {}).sort((a, b) => b[1] - a[1]);
  const candidates = data.upsell_candidates || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Billing overview</h2>
          <p className="text-xs text-muted-foreground">
            Snapshot at: {new Date(data.snapshot_at).toLocaleString()}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
          Refresh
        </Button>
      </div>

      {/* Big numbers grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" /> MRR
            </div>
            <div className="text-2xl font-bold font-heading">
              {_formatEur(data.mrr_current)}
            </div>
            <div className="text-[11px] text-muted-foreground mt-0.5">monthly recurring</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" /> Active subs
            </div>
            <div className="text-2xl font-bold font-heading">{data.active_subs_count}</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">incl. trialing</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
              <Package className="h-3.5 w-3.5" /> Active addons
            </div>
            <div className="text-2xl font-bold font-heading">{data.active_addons_count}</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">across all orgs</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
              <TrendingDown className="h-3.5 w-3.5" /> Churn 30d
            </div>
            <div className="text-2xl font-bold font-heading">{data.churn_30d}</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">canceled subs</div>
          </CardContent>
        </Card>
      </div>

      {/* Breakdowns */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">MRR by plan</CardTitle>
          </CardHeader>
          <CardContent>
            {planEntries.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No active subs.</p>
            ) : (
              <div className="space-y-1">
                {planEntries.map(([slug, mrr]) => (
                  <div key={slug} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-gray-50">
                    <span className="font-medium">{slug}</span>
                    <span className="tabular-nums font-semibold">{_formatEur(mrr)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">MRR by addon</CardTitle>
          </CardHeader>
          <CardContent>
            {addonEntries.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No active addons.</p>
            ) : (
              <div className="space-y-1">
                {addonEntries.map(([slug, mrr]) => (
                  <div key={slug} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-blue-50">
                    <span className="font-medium">{slug}</span>
                    <span className="tabular-nums font-semibold">{_formatEur(mrr)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Upsell candidates */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Upsell candidates (last 7 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {candidates.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              No orgs hit a quota threshold in the last 7 days.
            </p>
          ) : (
            <div className="space-y-1.5">
              {candidates.map((c) => (
                <div key={c.org_id} className="flex items-center gap-3 text-sm py-1.5 px-2 rounded border bg-amber-50/50 border-amber-100">
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-[11px] truncate">{c.org_id}</div>
                    <div className="text-xs text-muted-foreground">
                      Plan: <strong>{c.commercial_plan_slug}</strong>
                      <span className="mx-1">·</span>
                      Hit: {(c.metrics_hit || []).join(', ')}
                    </div>
                  </div>
                  <Badge className="bg-amber-100 text-amber-800 border-0 text-[10px] flex-shrink-0">
                    {c.last_sent ? new Date(c.last_sent).toLocaleDateString() : '-'}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
