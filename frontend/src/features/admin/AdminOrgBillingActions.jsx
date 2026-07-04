/**
 * AdminOrgBillingActions — system_admin per-org billing controls.
 *
 * Onda 8 (v5.8). Mounted inside the OrganizationsTab detail dialog.
 * Renders 4 collapsible sections:
 *   1. Usage    — usage-summary view for the selected org
 *   2. Custom Plan — form to create + apply a custom plan
 *   3. Extend Trial — quick form for trial_ends_at extension
 *   4. Impersonate — generate a 30min impersonation token + open in new tab
 *
 * All actions are audit-logged on the backend. The component is purely
 * additive — does not replace existing OrganizationsTab capabilities.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, Activity, Cog, Clock, UserCheck, AlertCircle, ExternalLink, Package, Plus, Trash2 } from 'lucide-react';
import { adminAPI } from '../../api';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';


function StatusBadge({ status }) {
  const colorMap = {
    ok: 'bg-gray-100 text-gray-700',
    info: 'bg-blue-100 text-blue-700',
    warn: 'bg-amber-100 text-amber-700',
    exceeded: 'bg-red-100 text-red-700',
    unlimited: 'bg-green-100 text-green-700',
    off: 'bg-gray-100 text-gray-500',
  };
  return <Badge className={`${colorMap[status] || 'bg-gray-100 text-gray-700'} border-0 text-[10px]`}>{status}</Badge>;
}


// ── Sub-component: Usage panel ───────────────────────────────────────────────

function UsagePanel({ orgId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminAPI.getOrgUsage(orgId);
      setData(res);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex items-center gap-2 text-sm text-muted-foreground p-3"><Loader2 className="h-4 w-4 animate-spin" /> Loading usage…</div>;
  if (error) return <div className="text-sm text-red-700 bg-red-50 border border-red-200 p-3 rounded">{String(error)}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Plan: <strong className="text-foreground">{data.commercial_plan_slug}</strong></span>
        <span>·</span>
        <span>Status: <strong className="text-foreground">{data.billing_status}</strong></span>
        {data.legacy_pricing_lock && <Badge className="bg-purple-50 text-purple-700 border-0 text-[10px]">🔒 Legacy</Badge>}
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Metrics</h4>
        <div className="space-y-1.5">
          {(data.metrics || []).map((m) => (
            <div key={m.key} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-gray-50 border border-gray-100">
              <span className="font-medium">{m.module}.{m.key}</span>
              <div className="flex items-center gap-2">
                <span className="tabular-nums text-xs text-muted-foreground">
                  {m.limit === -1 ? `${m.used} / ∞` : `${m.used} / ${m.limit}`}
                </span>
                <StatusBadge status={m.status} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {data.active_addons?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Active add-ons</h4>
          <div className="space-y-1">
            {data.active_addons.map((a) => (
              <div key={a.addon_slug} className="text-sm py-1.5 px-2 rounded bg-blue-50 border border-blue-100 flex items-center justify-between">
                <span className="font-medium">{a.name}</span>
                <span className="text-xs text-muted-foreground tabular-nums">×{a.quantity} · €{a.price_monthly}/mo</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.recent_quota_notices?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Recent quota notices ({data.recent_quota_notices.length})
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {data.recent_quota_notices.slice(0, 10).map((n, i) => (
              <div key={i} className="text-xs flex items-center gap-2 py-1 px-2 rounded bg-gray-50">
                <span className="font-mono text-[10px]">{n.period_start}</span>
                <span>{n.metric_key}</span>
                <Badge className={`${n.level === 'exceeded' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'} border-0 text-[10px]`}>
                  {n.level}
                </Badge>
                <span className="ml-auto text-muted-foreground">{n.used}/{n.effective_limit}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


// ── Sub-component: Custom plan creator ───────────────────────────────────────

function CustomPlanPanel({ orgId, onApplied }) {
  const [templateSlug, setTemplateSlug] = useState('core');
  const [overridesJson, setOverridesJson] = useState('{\n  "ai_assistant": {"chat": 500},\n  "commerce": {"orders_monthly": 5000}\n}');
  const [priceOverride, setPriceOverride] = useState('');
  const [trialOverride, setTrialOverride] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    setError(null);
    setResult(null);
    let overrides;
    try {
      overrides = JSON.parse(overridesJson);
    } catch (e) {
      setError('Overrides JSON is invalid');
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminAPI.createCustomPlan(orgId, {
        template_slug: templateSlug,
        overrides,
        price_monthly_override: priceOverride === '' ? null : Number(priceOverride),
        trial_days_override: trialOverride === '' ? null : Number(trialOverride),
        notes,
      });
      setResult(res);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApply = async () => {
    if (!result?.custom_plan_slug) return;
    setSubmitting(true);
    try {
      await adminAPI.setOrgCommercialPlan(orgId, result.custom_plan_slug, notes || 'Custom plan applied via Onda 8 admin UI');
      setResult({ ...result, applied: true });
      if (onApplied) onApplied(result.custom_plan_slug);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Template plan</label>
          <select
            value={templateSlug}
            onChange={(e) => setTemplateSlug(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          >
            <option value="free">free</option>
            <option value="starter">starter (Solo)</option>
            <option value="core">core (Commerce Starter)</option>
            <option value="pro">pro (Commerce Pro)</option>
            <option value="enterprise">enterprise (Custom)</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Price override (€/mo)</label>
          <input
            type="number"
            step="0.01"
            placeholder="leave blank = template price"
            value={priceOverride}
            onChange={(e) => setPriceOverride(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Trial days override</label>
          <input
            type="number"
            placeholder="leave blank = template trial"
            value={trialOverride}
            onChange={(e) => setTrialOverride(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Notes (audit)</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Beta partner — strategic deal"
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-muted-foreground mb-1 block">
          Limit overrides (JSON: {`{module: {feature: limit}}`})
        </label>
        <textarea
          value={overridesJson}
          onChange={(e) => setOverridesJson(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 text-xs font-mono border rounded-md"
          disabled={submitting}
        />
        <p className="text-[10px] text-muted-foreground mt-1">
          Use -1 for unlimited. Module keys: ai_assistant, cashflow_monitor, product_catalog, commerce, customers_light.
        </p>
      </div>

      {error && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 p-2 rounded flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
          <span>{String(error)}</span>
        </div>
      )}

      {result?.ok && !result.applied && (
        <div className="text-xs bg-amber-50 border border-amber-200 p-3 rounded space-y-2">
          <p className="font-medium text-amber-900">
            Custom plan created: <code className="font-mono">{result.custom_plan_slug}</code>
          </p>
          <p className="text-amber-800">{result.next_step}</p>
          <Button size="sm" onClick={handleApply} disabled={submitting}>
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
            Apply this plan now
          </Button>
        </div>
      )}

      {result?.applied && (
        <div className="text-xs bg-green-50 border border-green-200 p-3 rounded text-green-800">
          ✓ Plan applied. The org is now on <code className="font-mono">{result.custom_plan_slug}</code>.
        </div>
      )}

      {!result && (
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Create custom plan
        </Button>
      )}
    </div>
  );
}


// ── Sub-component: Trial extension ───────────────────────────────────────────

function ExtendTrialPanel({ orgId, onExtended }) {
  const [extraDays, setExtraDays] = useState(7);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    setError(null);
    setResult(null);
    if (!reason.trim()) {
      setError('Reason is required (audit trail).');
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminAPI.extendTrial(orgId, Number(extraDays), reason);
      setResult(res);
      if (onExtended) onExtended(res);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Extra days (1–365)</label>
          <input
            type="number"
            min={1}
            max={365}
            value={extraDays}
            onChange={(e) => setExtraDays(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground mb-1 block">Reason (required, audited)</label>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Beta tester, holiday support, partner agreement"
          className="w-full px-3 py-1.5 text-sm border rounded-md"
          disabled={submitting}
        />
      </div>

      {error && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 p-2 rounded">{String(error)}</div>
      )}

      {result?.ok && (
        <div className="text-xs bg-green-50 border border-green-200 p-3 rounded text-green-800">
          ✓ Trial extended. New end date: <strong>{new Date(result.new_trial_ends_at).toLocaleString()}</strong>
        </div>
      )}

      <Button onClick={handleSubmit} disabled={submitting || !reason.trim()}>
        {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
        Extend trial by {extraDays} days
      </Button>
    </div>
  );
}


// ── Sub-component: Impersonate ──────────────────────────────────────────────

function ImpersonatePanel({ orgId }) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleImpersonate = async () => {
    if (!window.confirm(
      `Generate a 30min impersonation token for org ${orgId}?\n\nThis WILL be audit-logged.`,
    )) return;

    setError(null);
    setSubmitting(true);
    try {
      const res = await adminAPI.impersonate(orgId, reason);
      setResult(res);
      // Store the impersonation token under a SEPARATE key so the system_admin's
      // own session is preserved. The impersonated UI consumes this via a
      // dedicated bootstrap path — out of scope for v5.8 onda 8 (this just
      // mints the token and shows it for debugging / support workflows).
      localStorage.setItem('impersonation_token', res.access_token);
      localStorage.setItem('impersonation_target', JSON.stringify(res.target_user));
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded flex items-start gap-2">
        <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
        <div>
          Impersonation is logged in the audit trail and TTL is 30 minutes.
          The token is stored locally as <code className="font-mono">impersonation_token</code> —
          a future onda will wire it to a dedicated UI path.
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-muted-foreground mb-1 block">Reason (audit)</label>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Customer reported a checkout bug"
          className="w-full px-3 py-1.5 text-sm border rounded-md"
          disabled={submitting}
        />
      </div>

      {error && <div className="text-xs text-red-700 bg-red-50 border border-red-200 p-2 rounded">{String(error)}</div>}

      {result?.ok && (
        <div className="text-xs bg-green-50 border border-green-200 p-3 rounded text-green-800 space-y-1">
          <div>✓ Token minted for <strong>{result.target_user?.email}</strong></div>
          <div>TTL: {result.ttl_minutes} min · stored in localStorage as <code className="font-mono">impersonation_token</code></div>
          <div className="break-all font-mono text-[10px] mt-1 p-2 bg-white rounded border border-green-200">
            {result.access_token.slice(0, 60)}…
          </div>
        </div>
      )}

      <Button onClick={handleImpersonate} disabled={submitting} variant="outline">
        {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserCheck className="h-4 w-4 mr-2" />}
        Mint impersonation token
      </Button>
    </div>
  );
}


// ── Sub-component: Add-ons (manual assign / remove) ─────────────────────────

function AddonsPanel({ orgId }) {
  const [active, setActive] = useState([]);
  const [available, setAvailable] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Assign form state
  const [pickedSlug, setPickedSlug] = useState('');
  const [pickedQty, setPickedQty] = useState(1);
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [activeRes, plansRes] = await Promise.all([
        adminAPI.listOrgAddons(orgId),
        adminAPI.getCommercialPlans(),
      ]);
      setActive(Array.isArray(activeRes) ? activeRes : []);
      const onlyAddons = (plansRes || []).filter((p) => p.is_addon);
      setAvailable(onlyAddons);
      if (onlyAddons.length > 0 && !pickedSlug) {
        setPickedSlug(onlyAddons[0].slug);
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setLoading(false);
    }
  }, [orgId, pickedSlug]);

  useEffect(() => { load(); }, [load]);

  const handleAssign = async () => {
    setError(null);
    if (!pickedSlug) { setError('Pick an add-on.'); return; }
    if (!reason.trim()) { setError('Reason is required (audit).'); return; }
    setSubmitting(true);
    try {
      await adminAPI.assignOrgAddon(orgId, {
        addon_slug: pickedSlug,
        quantity: Number(pickedQty) || 1,
        reason: reason.trim(),
        notes: notes.trim(),
      });
      setReason('');
      setNotes('');
      setPickedQty(1);
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (slug) => {
    const why = window.prompt(
      `Remove add-on "${slug}" from this org?\n\nReason (required, audit):`,
    );
    if (!why || !why.trim()) return;
    setSubmitting(true);
    try {
      const res = await adminAPI.removeOrgAddon(orgId, slug, why.trim());
      if (res?.stripe_warning) {
        // eslint-disable-next-line no-alert
        window.alert(res.stripe_warning);
      }
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  const pickedPlan = available.find((p) => p.slug === pickedSlug);

  return (
    <div className="space-y-5">
      {/* Active add-ons */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          Active add-ons {loading ? '' : `(${active.length})`}
        </h4>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground p-2">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : active.length === 0 ? (
          <div className="text-sm text-muted-foreground italic p-2">No active add-ons.</div>
        ) : (
          <div className="space-y-1.5">
            {active.map((a) => (
              <div
                key={a.addon_slug}
                className="flex items-center justify-between text-sm py-2 px-3 rounded border border-gray-200 bg-white"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{a.name}</span>
                    {a.is_custom_override && (
                      <Badge className="bg-purple-50 text-purple-700 border-0 text-[10px]">
                        custom override
                      </Badge>
                    )}
                  </div>
                  <div className="text-[11px] text-muted-foreground tabular-nums">
                    ×{a.quantity} · €{a.price_monthly}/mo · since {a.started_at?.slice(0, 10)}
                    {a.assigned_by ? ` · by ${a.assigned_by}` : ''}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  onClick={() => handleRemove(a.addon_slug)}
                  disabled={submitting}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assign form */}
      <div className="border-t pt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          Assign new add-on (custom override · no Stripe billing)
        </h4>
        <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded mb-3 flex items-start gap-2">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>
            This grants the add-on directly without going through Stripe. Use for
            comps, beta deals, or manual contracts. The org will NOT be billed
            for this add-on by Stripe.
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              Add-on
            </label>
            <select
              value={pickedSlug}
              onChange={(e) => setPickedSlug(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border rounded-md"
              disabled={submitting || available.length === 0}
            >
              {available.map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.name} (€{p.price_monthly}/mo · max ×{p.max_quantity || 1})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              Quantity (max {pickedPlan?.max_quantity || 1})
            </label>
            <input
              type="number"
              min={1}
              max={pickedPlan?.max_quantity || 1}
              value={pickedQty}
              onChange={(e) => setPickedQty(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border rounded-md"
              disabled={submitting}
            />
          </div>
        </div>

        <div className="mt-3">
          <label className="text-xs font-medium text-muted-foreground mb-1 block">
            Reason (required, audited)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Beta partner — comp for early adopter"
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>

        <div className="mt-3">
          <label className="text-xs font-medium text-muted-foreground mb-1 block">
            Notes (optional, persisted on the row)
          </label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Granted for 3 months"
            className="w-full px-3 py-1.5 text-sm border rounded-md"
            disabled={submitting}
          />
        </div>

        {error && (
          <div className="mt-3 text-xs text-red-700 bg-red-50 border border-red-200 p-2 rounded flex items-start gap-2">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
            <span>{String(error)}</span>
          </div>
        )}

        <div className="mt-3">
          <Button onClick={handleAssign} disabled={submitting || !pickedSlug || !reason.trim()}>
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Assign add-on
          </Button>
        </div>
      </div>
    </div>
  );
}


// ── Top-level component ─────────────────────────────────────────────────────

export default function AdminOrgBillingActions({ orgId, onClose }) {
  const [section, setSection] = useState('usage');

  if (!orgId) return null;

  const sections = [
    { key: 'usage', label: 'Usage', icon: Activity },
    { key: 'custom_plan', label: 'Custom Plan', icon: Cog },
    { key: 'addons', label: 'Add-ons', icon: Package },
    { key: 'extend_trial', label: 'Extend Trial', icon: Clock },
    { key: 'impersonate', label: 'Impersonate', icon: UserCheck },
  ];

  return (
    <div className="border rounded-lg bg-white">
      <div className="px-4 py-2 border-b bg-gray-50 flex items-center gap-2 overflow-x-auto">
        {sections.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => setSection(s.key)}
              className={`text-xs font-medium px-2.5 py-1 rounded inline-flex items-center gap-1.5 whitespace-nowrap transition-colors ${
                section === s.key
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Icon className="h-3 w-3" />
              {s.label}
            </button>
          );
        })}
      </div>
      <div className="p-4">
        {section === 'usage' && <UsagePanel orgId={orgId} />}
        {section === 'custom_plan' && <CustomPlanPanel orgId={orgId} onApplied={onClose} />}
        {section === 'addons' && <AddonsPanel orgId={orgId} />}
        {section === 'extend_trial' && <ExtendTrialPanel orgId={orgId} onExtended={onClose} />}
        {section === 'impersonate' && <ImpersonatePanel orgId={orgId} />}
      </div>
    </div>
  );
}
