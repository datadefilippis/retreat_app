/**
 * AdminOrgBillingActions — le azioni di fatturazione (ciclo PA, 30/8/2026).
 *
 * Due sole sezioni, perche' due sole esistono nella verita' di Aurya:
 *   1. Utilizzo   — i numeri veri dell'org (metriche dei moduli vivi)
 *   2. Impersona  — token di 30 minuti per entrare come l'org
 *
 * Sono USCITI (PA4): Custom-Plan (i piani sono quattro, non su
 * misura), gli add-on (zero in prod, svuotati da AB5) e l'estensione
 * del trial (il Pro ha trial_days: 0 — il trial non esiste). Le
 * rotte backend restano: e' la UI a dire solo cio' che esiste.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, Activity, UserCheck, AlertCircle, ExternalLink } from 'lucide-react';
import { adminAPI } from '../../api';
import { nomePiano, nomeStato, nomeMetrica } from './pianiAurya';
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
        <span>Piano: <strong className="text-foreground">{nomePiano(data.commercial_plan_slug)}</strong></span>
        <span>·</span>
        <span>Stato: <strong className="text-foreground">{nomeStato(data.billing_status)}</strong></span>
        {data.legacy_pricing_lock && <Badge className="bg-purple-50 text-purple-700 border-0 text-[10px]">🔒 Legacy</Badge>}
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Utilizzo</h4>
        <div className="space-y-1.5">
          {/* PA4 — solo la verita': le metriche dei moduli SPENTI
              (l'AI chat che su Aurya non esiste) non si mostrano */}
          {(data.metrics || []).filter((m) => m.status !== 'off').map((m) => (
            <div key={`${m.module}.${m.key}`} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-gray-50 border border-gray-100">
              <span className="font-medium">{nomeMetrica(m.module, m.key)}</span>
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

// ── Top-level component ─────────────────────────────────────────────────────

export default function AdminOrgBillingActions({ orgId, onClose }) {
  const [section, setSection] = useState('usage');

  if (!orgId) return null;

  const sections = [
    { key: 'usage', label: 'Utilizzo', icon: Activity },
    { key: 'impersonate', label: 'Impersona', icon: UserCheck },
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
        {section === 'impersonate' && <ImpersonatePanel orgId={orgId} />}
      </div>
    </div>
  );
}
