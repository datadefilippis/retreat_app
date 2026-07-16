import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from '../../components/ui/table';
import { Skeleton } from '../../components/ui/skeleton';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Tabs, TabsContent } from '../../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  Zap, AlertTriangle, Database, Activity, RefreshCw, TrendingUp,
  TrendingDown, Search, X,
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, Cell,
} from 'recharts';
import { adminAPI } from '../../api';

/**
 * AIGovernanceTab — dashboard spesa AI (traduzioni e strumenti contenuti).
 *
 * Consolidamento ADM 16/7/2026: la potatura R4 dell'AI legacy ha rimosso
 * dal backend budgets, kill switch, governance audit e drill-down
 * conversazioni — le sezioni che li usavano sono state tolte QUI, perche'
 * il Promise.all falliva in blocco su endpoint 404 e l'intera tab
 * risultava rotta. Restano le TRE fonti che esistono davvero:
 *
 *   /api/admin/ai-usage/summary
 *   /api/admin/ai-usage/timeseries
 *   /api/admin/ai-usage/by-user
 */

const PERIOD_OPTIONS = [
  { value: 7,  label: '7 days'  },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
];

const CHART_COLORS = [
  '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
  '#a855f7', '#06b6d4', '#ec4899',
];

const AUTO_REFRESH_INTERVAL_MS = 60_000;

// ── Helpers ──────────────────────────────────────────────────────────────────

function isoDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function formatUSD(value) {
  if (value === null || value === undefined) return '—';
  if (value < 0.01 && value > 0) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}
function formatInt(n) {
  if (n === null || n === undefined) return '—';
  return n.toLocaleString();
}
function timeAgo(date) {
  if (!date) return null;
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

// ── KPI tile ─────────────────────────────────────────────────────────────────

const KPI = ({ icon: Icon, label, value, subtitle, accent }) => (
  <Card className={accent === 'warn' ? 'border-amber-200' : ''}>
    <CardContent className="pt-4 pb-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <div className="text-2xl font-bold font-heading mt-1">
            {value ?? <Skeleton className="h-7 w-20" />}
          </div>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1 truncate">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className={`p-2 rounded-md ${accent === 'warn' ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
    </CardContent>
  </Card>
);

// ── Main ─────────────────────────────────────────────────────────────────────

const AIGovernanceTab = () => {
  const [periodDays, setPeriodDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [byUser, setByUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Wave 10.C.1 — global organization filter. Drives every API call below.
  const [orgFilter, setOrgFilter] = useState('');  // "" = all orgs

  // Wave 10.C.3 — client-side search inputs.
  const [userSearch, setUserSearch] = useState('');

  // Wave 10.C.4 — fix the stale-after-midnight bug: endDate must
  // re-compute on every refreshTick / period change, not just at mount.
  const startDate = useMemo(() => isoDaysAgo(periodDays), [periodDays]);
  const endDate = useMemo(
    () => todayISO(),
    [periodDays, refreshTick],  // include refreshTick so a manual refresh after midnight rolls the date
  );

  const orgFilterParam = orgFilter || undefined;

  // Wave 10.C.1 — every fetch passes orgId so the filter is honoured.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [sumRes, tsRes, userRes] = await Promise.all([
          adminAPI.getAIUsageSummary(startDate, endDate),
          adminAPI.getAIUsageTimeseries(startDate, endDate, { orgId: orgFilterParam }),
          adminAPI.getAIUsageByUser(startDate, endDate, { orgId: orgFilterParam, limit: 200 }),
        ]);
        if (cancelled) return;
        setSummary(sumRes);
        setTimeseries(tsRes);
        setByUser(userRes);
        setLastRefreshedAt(new Date());
      } catch (e) {
        if (cancelled) return;
        setError(e?.response?.data?.detail || e?.message || 'Failed to load AI usage data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [startDate, endDate, refreshTick, orgFilterParam]);

  // Wave 10.C.5 — opt-in auto-refresh every 60s. Off by default.
  useEffect(() => {
    if (!autoRefresh) return undefined;
    const t = setInterval(() => setRefreshTick((x) => x + 1), AUTO_REFRESH_INTERVAL_MS);
    return () => clearInterval(t);
  }, [autoRefresh]);

  // ── Memoized: org dropdown options from summary.by_org ──────────────────
  // We re-derive this from whatever we have; summary is always fetched
  // unfiltered (so the dropdown options are global, even when filtered).
  const orgOptions = useMemo(() => {
    if (!summary?.by_org) return [];
    return summary.by_org.map((row) => ({
      value: row.organization_id,
      label: row.organization_name || row.organization_id?.slice(-12) || 'unknown',
    })).filter((o) => o.value);
  }, [summary]);

  // ── Memoized: filtered user table by search query ───────────────────────
  const filteredByUser = useMemo(() => {
    if (!byUser?.rows) return [];
    if (!userSearch.trim()) return byUser.rows;
    const q = userSearch.toLowerCase();
    return byUser.rows.filter((r) =>
      (r.organization_name || '').toLowerCase().includes(q) ||
      (r.user_name || '').toLowerCase().includes(q) ||
      (r.organization_id || '').toLowerCase().includes(q) ||
      (r.user_id || '').toLowerCase().includes(q) ||
      (r.feature || '').toLowerCase().includes(q) ||
      (r.agent_id || '').toLowerCase().includes(q)
    );
  }, [byUser, userSearch]);

  const hasData = summary && (summary.totals.events > 0);

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div>
        <h2 className="text-xl font-bold font-heading flex items-center gap-2">
          <Zap className="h-5 w-5 text-blue-600" />
          AI &amp; Traduzioni
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Platform-wide Anthropic spend (translations and content tools).
        </p>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsContent value="overview" className="space-y-6 pt-4">
          {/* ── Controls row 1: org filter + period + refresh ── */}
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 flex-wrap">
              {/* Wave 10.C.1 — org filter */}
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                <Select
                  value={orgFilter || '__all__'}
                  onValueChange={(v) => setOrgFilter(v === '__all__' ? '' : v)}
                >
                  <SelectTrigger className="w-[260px]">
                    <SelectValue placeholder="All organizations" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">All organizations</SelectItem>
                    {orgOptions.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {orgFilter && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setOrgFilter('')}
                    title="Clear org filter"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>

              <p className="text-xs text-muted-foreground">
                Window: <span className="font-mono">{startDate}</span> → <span className="font-mono">{endDate}</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              {PERIOD_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  variant={periodDays === opt.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setPeriodDays(opt.value)}
                  disabled={loading}
                >
                  {opt.label}
                </Button>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRefreshTick((t) => t + 1)}
                disabled={loading}
                title="Refresh now"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* ── Controls row 2: freshness + auto-refresh ── */}
          <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
            <div>
              {lastRefreshedAt && (
                <>Last refreshed <strong>{timeAgo(lastRefreshedAt)}</strong> · {lastRefreshedAt.toLocaleTimeString()}</>
              )}
            </div>
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="h-3.5 w-3.5"
              />
              <span>Auto-refresh every 60s</span>
            </label>
          </div>

          {/* ── Error banner ── */}
          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-4 pb-4 flex items-center gap-2 text-red-700">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm">{error}</span>
              </CardContent>
            </Card>
          )}

          {/* ── KPI row ── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KPI icon={Zap} label="Total cost"
                 value={summary ? formatUSD(summary.totals.cost_usd) : null}
                 subtitle={`Last ${periodDays} days (USD)${orgFilter ? ' · filtered' : ''}`} />
            <KPI icon={Activity} label="Events"
                 value={summary ? formatInt(summary.totals.events) : null}
                 subtitle={timeseries ? `${formatInt(timeseries.totals.tokens_total)} tokens` : null} />
            <KPI icon={Database} label="Organizations"
                 value={summary ? formatInt(summary.totals.distinct_orgs) : null}
                 subtitle="With AI activity" />
            <KPI icon={timeseries?.totals.cache_hit_ratio_pct >= 50 ? TrendingUp : TrendingDown}
                 label="Cache hit ratio"
                 value={timeseries ? `${timeseries.totals.cache_hit_ratio_pct}%` : null}
                 subtitle="Prompt cache savings"
                 accent={timeseries?.totals.cache_hit_ratio_pct < 20 ? 'warn' : undefined} />
          </div>

          {/* ── No-data state ── */}
          {!loading && summary && !hasData && (
            <Card>
              <CardContent className="pt-6 pb-6 text-center text-muted-foreground">
                No AI usage events in this window
                {orgFilter && <> for the selected organization</>}.
                Clear filters or change the period to see other data.
              </CardContent>
            </Card>
          )}

          {/* ── Daily trend ── */}
          {hasData && timeseries && (
            <Card>
              <CardHeader>
                <CardTitle>Daily cost trend</CardTitle>
                <CardDescription>USD spend per day{orgFilter ? ' for the filtered org' : ' across all orgs'}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 w-full">
                  <ResponsiveContainer>
                    <AreaChart data={timeseries.days}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }}
                             tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 11 }}
                             tickFormatter={(v) => `$${v.toFixed(2)}`} />
                      <Tooltip formatter={(v) => formatUSD(v)}
                               contentStyle={{ fontSize: 12 }} />
                      <Area type="monotone" dataKey="cost_usd"
                            stroke={CHART_COLORS[0]} fill={CHART_COLORS[0]}
                            fillOpacity={0.2} name="Cost USD" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── By feature + by agent ── */}
          {hasData && timeseries && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>By feature</CardTitle>
                  <CardDescription>Where the spend goes</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-56 w-full">
                    <ResponsiveContainer>
                      <BarChart data={timeseries.by_feature} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" tick={{ fontSize: 11 }}
                               tickFormatter={(v) => `$${v.toFixed(2)}`} />
                        <YAxis type="category" dataKey="feature" tick={{ fontSize: 11 }} width={130} />
                        <Tooltip formatter={(v) => formatUSD(v)} contentStyle={{ fontSize: 12 }} />
                        <Bar dataKey="cost_usd" name="Cost USD">
                          {timeseries.by_feature.map((_, idx) => (
                            <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>By agent</CardTitle>
                  <CardDescription>Which AI persona consumed budget</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-56 w-full">
                    <ResponsiveContainer>
                      <BarChart data={timeseries.by_agent} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" tick={{ fontSize: 11 }}
                               tickFormatter={(v) => `$${v.toFixed(2)}`} />
                        <YAxis type="category" dataKey="agent_id" tick={{ fontSize: 11 }} width={130} />
                        <Tooltip formatter={(v) => formatUSD(v)} contentStyle={{ fontSize: 12 }} />
                        <Bar dataKey="cost_usd" name="Cost USD">
                          {timeseries.by_agent.map((_, idx) => (
                            <Cell key={idx} fill={CHART_COLORS[(idx + 2) % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* ── Top organizations table ── */}
          {hasData && summary && summary.by_org.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Top organizations</CardTitle>
                <CardDescription>By total AI cost in the window. Click a row to filter to that org.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Organization</TableHead>
                      <TableHead className="text-right">Events</TableHead>
                      <TableHead className="text-right">Tokens (in/out)</TableHead>
                      <TableHead className="text-right">Distinct users</TableHead>
                      <TableHead className="text-right">Cost (USD)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.by_org.slice(0, 20).map((row) => (
                      <TableRow
                        key={row.organization_id || 'unknown'}
                        className="cursor-pointer hover:bg-muted/40"
                        onClick={() => row.organization_id && setOrgFilter(row.organization_id)}
                      >
                        <TableCell>
                          <div className="text-sm font-medium">
                            {row.organization_name || (
                              <span className="italic text-muted-foreground">unknown</span>
                            )}
                          </div>
                          <div className="text-xs font-mono text-muted-foreground">
                            {row.organization_id || '—'}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">{formatInt(row.events)}</TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground">
                          {formatInt(row.tokens_in)} / {formatInt(row.tokens_out)}
                        </TableCell>
                        <TableCell className="text-right">{formatInt(row.distinct_users_count)}</TableCell>
                        <TableCell className="text-right font-semibold">{formatUSD(row.cost_usd)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* ── Detail by user/agent/feature — Wave 10.C.3 (search) ── */}
          {hasData && byUser && byUser.rows.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
                <div>
                  <CardTitle>Detail by user / agent / feature</CardTitle>
                  <CardDescription>
                    {filteredByUser.length} of {byUser.rows.length} rows · sorted by cost
                  </CardDescription>
                </div>
                <div className="relative">
                  <Search className="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    placeholder="Search org / user / feature"
                    className="pl-7 h-8 w-[260px] text-xs"
                  />
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Org</TableHead>
                        <TableHead>User</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Feature</TableHead>
                        <TableHead className="text-right">Events</TableHead>
                        <TableHead className="text-right">Tokens</TableHead>
                        <TableHead className="text-right">Cost</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredByUser.slice(0, 100).map((row, idx) => (
                        <TableRow key={`${row.organization_id}-${row.user_id}-${row.agent_id}-${row.feature}-${idx}`}>
                          <TableCell className="text-xs">
                            {row.organization_name || (
                              <span className="font-mono text-muted-foreground">
                                {row.organization_id?.slice(-8) || '—'}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-xs">
                            {row.user_name || (
                              row.user_id
                                ? <span className="font-mono text-muted-foreground">{row.user_id.slice(-8)}</span>
                                : <Badge variant="outline" className="text-xs">system</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs">{row.agent_id || '—'}</TableCell>
                          <TableCell className="text-xs">{row.feature || '—'}</TableCell>
                          <TableCell className="text-right">{formatInt(row.events)}</TableCell>
                          <TableCell className="text-right text-xs">{formatInt(row.tokens_total)}</TableCell>
                          <TableCell className="text-right font-semibold">{formatUSD(row.cost_usd)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {filteredByUser.length === 0 && userSearch && (
                    <div className="py-6 text-center text-sm text-muted-foreground">
                      No rows match <strong>{userSearch}</strong>.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── Footer ── */}
          <p className="text-xs text-muted-foreground text-center pt-4">
            Costs are stored in USD (Anthropic's billing currency). Window: {startDate} → {endDate}.
            {orgFilter && <> Filtered to <span className="font-mono">{orgFilter.slice(-12)}</span>.</>}
          </p>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AIGovernanceTab;
