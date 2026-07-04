import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from '../../components/ui/table';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '../../components/ui/alert-dialog';
import {
  ShieldAlert, ShieldCheck, Plus, Pencil, Trash2, AlertTriangle,
  Power, RefreshCw,
} from 'lucide-react';
import { adminAPI } from '../../api';

/**
 * AIGovernanceBudgetsSection — Wave 8C.2.
 *
 * Two stacked panels:
 *   1. Kill switch (platform-wide AI on/off + load-shed throttle %)
 *   2. Budgets CRUD with live current_spend_usd progress bars
 *
 * Backend endpoints (Wave 8B):
 *   GET    /api/admin/ai-budgets
 *   POST   /api/admin/ai-budgets
 *   PATCH  /api/admin/ai-budgets/{id}
 *   DELETE /api/admin/ai-budgets/{id}
 *   GET    /api/admin/ai-governance/kill-switch
 *   POST   /api/admin/ai-governance/kill-switch
 */

const SCOPE_OPTIONS = [
  { value: 'global',  label: 'Global (entire platform)' },
  { value: 'org',     label: 'Organization' },
  { value: 'user',    label: 'User' },
  { value: 'feature', label: 'Feature (chat / digest / ...)' },
  { value: 'agent',   label: 'Agent (financial_analyst / ...)' },
];

const PERIOD_OPTIONS = [
  { value: 'daily',   label: 'Daily'   },
  { value: 'monthly', label: 'Monthly' },
  { value: 'yearly',  label: 'Yearly'  },
];

function formatUSD(value) {
  if (value === null || value === undefined) return '—';
  if (value < 0.01 && value > 0) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function progressPct(spent, limit) {
  if (!limit || limit <= 0 || spent == null) return 0;
  return Math.min(100, Math.round((spent / limit) * 100));
}

// ── Kill switch panel ────────────────────────────────────────────────────────

const KillSwitchPanel = ({ killSwitch, onChange, onRefresh, loading }) => {
  const [aiEnabled, setAiEnabled] = useState(true);
  const [throttle, setThrottle] = useState(0);
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Initialize when state arrives from server
  useEffect(() => {
    if (killSwitch) {
      setAiEnabled(killSwitch.ai_enabled ?? true);
      setThrottle(killSwitch.ai_throttle_pct ?? 0);
    }
  }, [killSwitch]);

  const isRestrictive = !aiEnabled || throttle > 0;
  const isDirty = killSwitch && (
    aiEnabled !== killSwitch.ai_enabled ||
    throttle !== killSwitch.ai_throttle_pct
  );

  const submit = async () => {
    if (isRestrictive && !reason.trim()) {
      setFeedback({ type: 'error', text: 'A reason is required when disabling or throttling AI.' });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      await adminAPI.setAIKillSwitch({
        ai_enabled: aiEnabled,
        ai_throttle_pct: Number(throttle),
        reason: reason.trim() || null,
      });
      setReason('');
      setFeedback({ type: 'ok', text: 'Kill switch updated.' });
      onChange();  // tell parent to refetch
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || 'Failed to update kill switch';
      setFeedback({ type: 'error', text: msg });
    } finally {
      setSaving(false);
    }
  };

  const banner = !killSwitch ? null
    : !killSwitch.ai_enabled ? (
        <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700 mb-3">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <div className="flex-1 min-w-0">
            <strong>AI globally disabled.</strong> All Anthropic calls are being refused.
            {killSwitch.kill_reason && (
              <span className="block text-xs mt-0.5 truncate">Reason: {killSwitch.kill_reason}</span>
            )}
          </div>
        </div>
      ) : killSwitch.ai_throttle_pct > 0 ? (
        <div className="flex items-center gap-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700 mb-3">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <div className="flex-1 min-w-0">
            <strong>Throttle active at {killSwitch.ai_throttle_pct}%.</strong> A random
            fraction of AI calls is being refused.
            {killSwitch.kill_reason && (
              <span className="block text-xs mt-0.5 truncate">Reason: {killSwitch.kill_reason}</span>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700 mb-3">
          <ShieldCheck className="h-4 w-4 shrink-0" />
          <span><strong>AI fully enabled.</strong> No throttle, no kill switch.</span>
        </div>
      );

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Power className="h-5 w-5 text-blue-600" />
            Kill switch
          </CardTitle>
          <CardDescription>
            Platform-wide AI on/off + load-shed throttle. Use sparingly — every change is audited.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent>
        {banner}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
          <div className="space-y-2">
            <Label className="text-sm">AI enabled</Label>
            <div className="flex items-center gap-3">
              <Switch checked={aiEnabled} onCheckedChange={setAiEnabled} />
              <span className="text-sm">
                {aiEnabled ? 'AI calls allowed' : 'All AI calls refused'}
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-sm" htmlFor="throttle">
              Throttle %
            </Label>
            <Input
              id="throttle"
              type="number"
              min={0}
              max={100}
              value={throttle}
              onChange={(e) => setThrottle(Math.min(100, Math.max(0, Number(e.target.value) || 0)))}
              disabled={!aiEnabled}
              className="w-32"
            />
            <p className="text-xs text-muted-foreground">
              0 = no throttle. 100 = refuse all calls (same effect as disabling).
            </p>
          </div>
        </div>

        {isRestrictive && (
          <div className="space-y-2 mb-3">
            <Label className="text-sm">
              Reason <span className="text-red-600">*</span>
            </Label>
            <Textarea
              placeholder="Why are you restricting AI? (audit trail)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
            />
          </div>
        )}

        {feedback && (
          <div className={`text-xs mb-2 ${feedback.type === 'ok' ? 'text-green-600' : 'text-red-600'}`}>
            {feedback.text}
          </div>
        )}

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {killSwitch?.activated_at && (
              <>Last change: {new Date(killSwitch.activated_at).toLocaleString()}
                {killSwitch.activated_by && <> · by <span className="font-mono">{killSwitch.activated_by.slice(-8)}</span></>}
              </>
            )}
          </p>
          <Button onClick={submit} disabled={saving || !isDirty}>
            {saving ? 'Saving...' : 'Apply'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

// ── Budget create/edit dialog ───────────────────────────────────────────────

const initialForm = {
  scope: 'org',
  scope_id: '',
  organization_id: '',
  period: 'monthly',
  soft_limit_usd: '',
  hard_limit_usd: '',
  hard_action: 'block',
  notes: '',
};

const BudgetDialog = ({ open, onClose, onSaved, editing }) => {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && editing) {
      setForm({
        scope: editing.scope,
        scope_id: editing.scope_id,
        organization_id: editing.organization_id || '',
        period: editing.period,
        soft_limit_usd: String(editing.soft_limit_usd ?? ''),
        hard_limit_usd: String(editing.hard_limit_usd ?? ''),
        hard_action: editing.hard_action || 'block',
        notes: editing.notes || '',
      });
    } else if (open) {
      setForm(initialForm);
    }
    setError(null);
  }, [open, editing]);

  const update = (field) => (eOrVal) => {
    const v = eOrVal?.target ? eOrVal.target.value : eOrVal;
    setForm((f) => ({ ...f, [field]: v }));
  };

  const submit = async () => {
    setError(null);
    const soft = Number(form.soft_limit_usd);
    const hard = Number(form.hard_limit_usd);
    if (!form.scope_id.trim()) {
      setError('scope_id is required.');
      return;
    }
    if (Number.isNaN(soft) || soft < 0) {
      setError('soft_limit_usd must be a non-negative number.');
      return;
    }
    if (Number.isNaN(hard) || hard < 0) {
      setError('hard_limit_usd must be a non-negative number.');
      return;
    }
    if (hard < soft) {
      setError('hard_limit_usd must be >= soft_limit_usd.');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        scope: form.scope,
        scope_id: form.scope_id.trim(),
        period: form.period,
        soft_limit_usd: soft,
        hard_limit_usd: hard,
        hard_action: form.hard_action,
        notes: form.notes.trim() || null,
        organization_id: form.organization_id.trim() || null,
      };
      if (editing?.id) {
        // PATCH only the mutable fields (scope tuple is immutable).
        await adminAPI.updateAIBudget(editing.id, {
          soft_limit_usd: payload.soft_limit_usd,
          hard_limit_usd: payload.hard_limit_usd,
          hard_action: payload.hard_action,
          notes: payload.notes,
        });
      } else {
        await adminAPI.createAIBudget(payload);
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const showOrgIdField = ['user', 'feature', 'agent'].includes(form.scope);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit budget' : 'New budget'}</DialogTitle>
          <DialogDescription>
            {editing
              ? 'Adjust the limits or notes. The scope tuple (scope + scope_id + period) is immutable.'
              : 'Cap AI spend for the chosen scope and period. The pre-flight check refuses calls when the hard limit is reached.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Scope</Label>
              <Select value={form.scope} onValueChange={update('scope')} disabled={!!editing}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SCOPE_OPTIONS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Period</Label>
              <Select value={form.period} onValueChange={update('period')} disabled={!!editing}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PERIOD_OPTIONS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">
              Scope ID
              {form.scope === 'global' && <span className="text-muted-foreground"> (use "*" for global)</span>}
            </Label>
            <Input
              value={form.scope_id}
              onChange={update('scope_id')}
              placeholder={
                form.scope === 'global' ? '*' :
                form.scope === 'org' ? 'org_xxx' :
                form.scope === 'user' ? 'user_xxx' :
                form.scope === 'feature' ? 'chat' :
                'financial_analyst'
              }
              disabled={!!editing}
              className="font-mono text-sm"
            />
          </div>

          {showOrgIdField && (
            <div className="space-y-1">
              <Label className="text-xs">
                Organization ID <span className="text-muted-foreground">(optional, restricts the scope to one org)</span>
              </Label>
              <Input
                value={form.organization_id}
                onChange={update('organization_id')}
                placeholder="org_xxx"
                disabled={!!editing}
                className="font-mono text-sm"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Soft limit (USD)</Label>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.soft_limit_usd}
                onChange={update('soft_limit_usd')}
                placeholder="7.00"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hard limit (USD)</Label>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.hard_limit_usd}
                onChange={update('hard_limit_usd')}
                placeholder="10.00"
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Notes</Label>
            <Textarea
              value={form.notes}
              onChange={update('notes')}
              placeholder="Why? (visible to all sysadmins)"
              rows={2}
            />
          </div>

          {error && (
            <div className="text-xs text-red-600 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" /> {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? 'Saving...' : (editing ? 'Save' : 'Create')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ── Budget row ──────────────────────────────────────────────────────────────

const BudgetRow = ({ budget, onEdit, onDelete }) => {
  const pct = progressPct(budget.current_spend_usd, budget.hard_limit_usd);
  const barColor = budget.hard_limit_reached
    ? 'bg-red-500'
    : budget.soft_limit_reached
    ? 'bg-amber-500'
    : 'bg-green-500';
  const rowClass = budget.hard_limit_reached
    ? 'bg-red-50'
    : budget.soft_limit_reached
    ? 'bg-amber-50'
    : '';
  const statusBadge = !budget.is_active
    ? <Badge variant="outline" className="text-xs">inactive</Badge>
    : budget.hard_limit_reached
    ? <Badge variant="destructive" className="text-xs">BLOCKED</Badge>
    : budget.soft_limit_reached
    ? <Badge className="text-xs bg-amber-100 text-amber-800 border-amber-200">soft hit</Badge>
    : <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">OK</Badge>;

  return (
    <TableRow className={rowClass}>
      <TableCell className="text-xs font-medium">{budget.scope}</TableCell>
      <TableCell className="font-mono text-xs">{budget.scope_id || '*'}</TableCell>
      <TableCell className="text-xs">{budget.period}</TableCell>
      <TableCell className="w-48">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-gray-100 rounded overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap min-w-[36px] text-right">
            {pct}%
          </span>
        </div>
      </TableCell>
      <TableCell className="text-right text-xs">
        <div>{formatUSD(budget.current_spend_usd)}</div>
        <div className="text-muted-foreground">
          / {formatUSD(budget.hard_limit_usd)}
        </div>
      </TableCell>
      <TableCell className="text-center">{statusBadge}</TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" onClick={() => onEdit(budget)} title="Edit">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700" title="Delete">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete budget?</AlertDialogTitle>
                <AlertDialogDescription>
                  Removing the budget on{' '}
                  <span className="font-mono">{budget.scope}/{budget.scope_id || '*'}</span> ({budget.period})
                  stops enforcement immediately. Current spend was {formatUSD(budget.current_spend_usd)} of {formatUSD(budget.hard_limit_usd)}.
                  This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => onDelete(budget)}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </TableCell>
    </TableRow>
  );
};

// ── Main section ────────────────────────────────────────────────────────────

const AIGovernanceBudgetsSection = () => {
  const [budgets, setBudgets] = useState(null);
  const [killSwitch, setKillSwitch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bRes, kRes] = await Promise.all([
        adminAPI.listAIBudgets({ limit: 200 }),
        adminAPI.getAIKillSwitch(),
      ]);
      setBudgets(bRes.budgets || []);
      setKillSwitch(kRes);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const handleDelete = async (budget) => {
    try {
      await adminAPI.deleteAIBudget(budget.id);
      reload();
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Delete failed');
    }
  };

  const openCreate = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (b) => { setEditing(b); setDialogOpen(true); };

  return (
    <div className="space-y-6">
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-4 pb-4 flex items-center gap-2 text-red-700">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </CardContent>
        </Card>
      )}

      <KillSwitchPanel
        killSwitch={killSwitch}
        onChange={reload}
        onRefresh={reload}
        loading={loading}
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
          <div>
            <CardTitle>Budgets</CardTitle>
            <CardDescription>
              Per-scope hard limits on Anthropic spend. Pre-flight check refuses calls when the hard limit is reached.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1" /> New budget
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {budgets === null ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : budgets.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No budgets configured yet. Click <strong>New budget</strong> to add the first cap.
              <br />
              Without budgets, AI spend is unbounded (kill switch is the only emergency stop).
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Scope</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead className="text-right">Spent / Limit</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {budgets.map((b) => (
                  <BudgetRow
                    key={b.id}
                    budget={b}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <BudgetDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSaved={reload}
        editing={editing}
      />
    </div>
  );
};

export default AIGovernanceBudgetsSection;
