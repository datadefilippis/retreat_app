/**
 * CatalogTab — Phase 3E
 *
 * Commercial Catalog Management inside System Admin.
 * Shows all commercial plans with management dialogs for:
 *   - safe metadata editing
 *   - module bundle composition
 *   - pricing (paired fields)
 *   - entitlement tier limits
 *   - catalog audit log
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { adminAPI } from '../../api';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import {
  Package, Settings, Layers, CreditCard, ScrollText,
  Loader2, Save, AlertTriangle, CheckCircle2, Plus, Archive, ArchiveRestore,
  Link2, RefreshCw, ShieldAlert,
} from 'lucide-react';
import { toast } from 'sonner';

// ── Helpers ──────────────────────────────────────────────────────────────────

const PLAN_COLORS = {
  free:       'bg-gray-100 text-gray-700',
  core:       'bg-blue-100 text-blue-700',
  pro:        'bg-violet-100 text-violet-700',
  enterprise: 'bg-amber-100 text-amber-700',
};

const SectionTitle = ({ icon: Icon, children }) => (
  <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-1.5">
    {Icon && <Icon className="h-4 w-4" />}
    {children}
  </h3>
);

const FieldRow = ({ label, children }) => (
  <div className="grid grid-cols-3 gap-3 items-center">
    <Label className="text-sm text-muted-foreground">{label}</Label>
    <div className="col-span-2">{children}</div>
  </div>
);

// ── Plan overview card ──────────────────────────────────────────────────────

const PlanCard = ({ plan, onManage }) => (
  <Card className="border">
    <CardContent className="pt-4 pb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge className={PLAN_COLORS[plan.slug] || 'bg-gray-100 text-gray-700'}>
            {plan.slug}
          </Badge>
          {plan.is_addon && (
            <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
              addon
            </Badge>
          )}
          {plan.is_archived && (
            <Badge variant="outline" className="text-xs bg-gray-100 text-gray-500 border-gray-300">
              archived
            </Badge>
          )}
          <span className="font-medium">{plan.name}</span>
        </div>
        <Button variant="outline" size="sm" onClick={() => onManage(plan)}>
          <Settings className="h-3.5 w-3.5 mr-1" /> Manage
        </Button>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground mt-2">
        <div>
          <span className="block font-medium text-foreground">
            €{plan.price_monthly ?? 0}/mo
          </span>
          {plan.price_yearly && <span>€{plan.price_yearly}/yr</span>}
        </div>
        <div>
          <span className="block font-medium text-foreground">
            {plan.trial_days}d trial
          </span>
        </div>
        <div className="flex gap-1 flex-wrap">
          {plan.is_public && <Badge variant="outline" className="text-xs">Public</Badge>}
          {plan.is_self_serve && <Badge variant="outline" className="text-xs">Self-serve</Badge>}
        </div>
        <div className="text-right">
          <span className="font-medium text-foreground">{plan.subscriber_count ?? 0}</span> orgs
        </div>
      </div>
      {plan.entitlements?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {plan.entitlements.map((e) => (
            <Badge key={e.module_key} variant="outline" className="text-xs">
              {e.module_key} → {e.pricing_plan_slug}
            </Badge>
          ))}
        </div>
      )}
    </CardContent>
  </Card>
);

// ══════════════════════════════════════════════════════════════════════════════
// Onda 11 Step 3 — Stripe linkage editor (system_admin)
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Self-contained section that lets the system_admin paste/edit the 3
 * Stripe linkage IDs (Product ID, monthly Price ID, optional yearly
 * Price ID) for a given plan or addon, with live drift checking against
 * Stripe and an active-subscription guardrail.
 *
 * Data flow:
 *   on mount        → GET /admin/catalog/plans/{slug}/stripe-linkage
 *   on save         → PATCH /admin/catalog/plans/{slug}/pricing
 *                     (only sends fields the admin changed)
 *   after save      → re-GET to refresh advisories and confirm zero drift
 *
 * Active-subscription guardrail:
 *   When `active_subscriptions.count > 0` AND the admin is changing
 *   `stripe_product_id`, the user must check the explicit ack
 *   checkbox; the payload sets `confirm_active_subscriptions: true`.
 *   If they forget, the backend returns 409 and we surface the error
 *   clearly.
 */
const StripeLinkageSection = ({ slug, isAddon }) => {
  const [linkage, setLinkage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    stripe_product_id: '',
    stripe_price_id_monthly: '',
    stripe_price_id_yearly: '',
  });
  const [ackActiveSubs, setAckActiveSubs] = useState(false);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  // Onda 11 Step 5 — audit history modal
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyEntries, setHistoryEntries] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Onda 21 — split the previous combined `refresh()` into two functions
  // with non-overlapping responsibilities. Same component, same backend
  // call, but the two callers (mount/save vs Re-check) need different
  // side-effects on the local form state:
  //
  //   loadInitial()    re-populates `form` from the DB snapshot. Called on
  //                    mount (to seed the form) and after a successful save
  //                    (to confirm the new values landed).
  //
  //   recheckRemote()  ONLY refreshes `linkage` (Stripe-side state +
  //                    advisories). Leaves `form` untouched so the user's
  //                    half-typed Product/Price IDs survive a Stripe re-poll.
  //
  // Pre-Onda-21 the single `refresh()` always called setForm, which wiped
  // user input every time the "Re-check" button fired — breaking the
  // workflow especially on addons where the DB starts with null Stripe
  // IDs (so the wipe was visible immediately). The fix is universal:
  // applies identically to all 5 commercial plans, all 4 addons, and any
  // future plan/addon created via the +New flow.
  const loadInitial = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminAPI.getPlanStripeLinkage(slug);
      setLinkage(data);
      setForm({
        stripe_product_id: data?.db_snapshot?.stripe_product_id || '',
        stripe_price_id_monthly: data?.db_snapshot?.stripe_price_id_monthly || '',
        stripe_price_id_yearly: data?.db_snapshot?.stripe_price_id_yearly || '',
      });
      setAckActiveSubs(false);  // reset on every fresh load
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load Stripe linkage');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  const recheckRemote = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminAPI.getPlanStripeLinkage(slug);
      setLinkage(data);
      // Intentionally NOT touching `form` or `ackActiveSubs` — the user
      // may be in the middle of typing new Stripe IDs and just wants to
      // see a fresh advisory drift snapshot.
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to recheck Stripe state');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { loadInitial(); }, [loadInitial]);

  const openHistory = useCallback(async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryEntries(null);
    try {
      const data = await adminAPI.getCatalogAuditLog({
        entity_type: 'commercial_plan',
        entity_id: slug,
        limit: 50,
      });
      // Surface only entries that touched a Stripe linkage field — this
      // includes monthly+yearly price ID changes (Phase 2e) AND product
      // ID changes (Onda 11 Step 1). update_pricing is the relevant
      // action; non-pricing audits (metadata/module_plans) are excluded.
      const linkageKeys = new Set([
        'stripe_product_id',
        'stripe_price_id_monthly',
        'stripe_price_id_yearly',
        'price_monthly',
        'price_yearly',
      ]);
      const filtered = (Array.isArray(data) ? data : []).filter((entry) => {
        if (entry.action !== 'update_pricing') return false;
        const changedKeys = Object.keys(entry.changes || {});
        return changedKeys.some((k) => linkageKeys.has(k));
      });
      setHistoryEntries(filtered);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load audit history');
      setHistoryEntries([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [slug]);

  if (loading || !linkage) {
    return (
      <section className="border rounded-lg p-4">
        <SectionTitle icon={Link2}>Stripe linking</SectionTitle>
        <Skeleton className="h-24 w-full" />
      </section>
    );
  }

  const db = linkage.db_snapshot || {};
  const remote = linkage.stripe_remote || {};
  const activeCount = linkage.active_subscriptions?.count || 0;

  // Detect "changed-vs-current" so we send only the diff to the backend.
  const productChanged = form.stripe_product_id !== (db.stripe_product_id || '');
  const monthlyIdChanged = form.stripe_price_id_monthly !== (db.stripe_price_id_monthly || '');
  const yearlyIdChanged = form.stripe_price_id_yearly !== (db.stripe_price_id_yearly || '');
  const anyChange = productChanged || monthlyIdChanged || yearlyIdChanged;

  // Per-field validity (regex matches backend pydantic patterns).
  const productValid = !form.stripe_product_id || /^prod_[A-Za-z0-9]+$/.test(form.stripe_product_id);
  const monthlyValid = !form.stripe_price_id_monthly || /^price_[A-Za-z0-9]+$/.test(form.stripe_price_id_monthly);
  const yearlyValid = !form.stripe_price_id_yearly || /^price_[A-Za-z0-9]+$/.test(form.stripe_price_id_yearly);
  const allValid = productValid && monthlyValid && yearlyValid;

  // Guardrail: if Product changes AND there are active subs, ack required.
  const needsAckActiveSubs = productChanged && activeCount > 0;
  const ackOk = !needsAckActiveSubs || ackActiveSubs;

  // Notes: required for any change (so audit trail has context).
  const notesOk = !anyChange || (notes.trim().length >= 5);

  const handleSave = async () => {
    if (!anyChange) {
      toast.info('No changes to save');
      return;
    }
    if (!allValid) {
      toast.error('One or more Stripe IDs have invalid format');
      return;
    }
    if (!ackOk) {
      toast.error(`${activeCount} active subscription(s) — confirm the impact first`);
      return;
    }
    if (!notesOk) {
      toast.error('Add a note (≥ 5 chars) explaining this linkage change');
      return;
    }
    setSaving(true);
    try {
      // Build minimal diff payload — only send what changed.
      // Pricing pairs require both price + price_id together, so when
      // the admin only changes a Price ID we must include the matching
      // current price value to satisfy the backend coherence rule.
      const payload = {};
      if (productChanged) payload.stripe_product_id = form.stripe_product_id || null;
      if (monthlyIdChanged) {
        payload.stripe_price_id_monthly = form.stripe_price_id_monthly;
        payload.price_monthly = Number(db.price_monthly ?? 0);
      }
      if (yearlyIdChanged) {
        payload.stripe_price_id_yearly = form.stripe_price_id_yearly;
        payload.price_yearly = Number(db.price_yearly ?? 0);
      }
      if (needsAckActiveSubs) payload.confirm_active_subscriptions = true;

      await adminAPI.patchPlanPricing(slug, payload, notes);
      toast.success('Stripe linkage updated');
      setNotes('');
      // Onda 21 — post-save: re-populate from DB so the admin sees the
      // freshly saved values reflected in the form (and the badges flip
      // from the pre-save state to the new live state). loadInitial is
      // the right call here, NOT recheckRemote — we DO want form to
      // sync to the new DB snapshot post-save.
      await loadInitial();
    } catch (err) {
      const detail = err.response?.data?.detail;
      // 409 from active-subs guardrail surfaces a structured detail
      if (typeof detail === 'object' && detail?.code === 'active_subscriptions_present') {
        toast.error(`Blocked: ${detail.affected_org_count} active subscriber(s). Tick the acknowledgement and retry.`);
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Failed to update Stripe linkage');
      }
    } finally {
      setSaving(false);
    }
  };

  // Status mini-badge per field, computed from remote validation.
  const productStatus = (() => {
    if (!db.stripe_product_id) return { label: 'unset', color: 'bg-gray-100 text-gray-600' };
    if (remote.product?.exists === false) return { label: 'NOT FOUND', color: 'bg-red-100 text-red-700' };
    if (remote.product?.active === false) return { label: 'archived', color: 'bg-amber-100 text-amber-700' };
    if (remote.product?.exists === true) return { label: '✓ live', color: 'bg-emerald-100 text-emerald-700' };
    return { label: '?', color: 'bg-gray-100 text-gray-600' };
  })();
  const priceStatus = (block) => {
    if (!block) return { label: '—', color: 'bg-gray-100 text-gray-600' };
    if (block.drift) return { label: `drift: ${block.reason || '?'}`, color: 'bg-red-100 text-red-700' };
    if (block.stripe_active === false) return { label: 'inactive', color: 'bg-amber-100 text-amber-700' };
    if (block.stripe_unit_amount != null) return { label: `✓ ${(block.stripe_unit_amount / 100).toFixed(2)} ${block.stripe_currency}`, color: 'bg-emerald-100 text-emerald-700' };
    return { label: '?', color: 'bg-gray-100 text-gray-600' };
  };
  const monthlyStatus = priceStatus(remote.price_monthly);
  const yearlyStatus = priceStatus(remote.price_yearly);

  return (
    <section className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <SectionTitle icon={Link2}>Stripe linking</SectionTitle>
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={recheckRemote} disabled={loading}>
          <RefreshCw className={`h-3 w-3 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Re-check
        </Button>
      </div>
      <p className="text-xs text-muted-foreground -mt-2">
        Edit the 3 Stripe linkage IDs. Changes only affect future
        checkouts — existing subscribers stay on the Product/Price
        their subscription was created with. Pre-create the new
        Product+Price on Stripe Dashboard, then paste the IDs here.
      </p>

      {/* Advisories */}
      {Array.isArray(linkage.advisories) && linkage.advisories.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 space-y-1">
          {linkage.advisories.map((a, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-amber-900">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5 text-amber-600" />
              <span>{a}</span>
            </div>
          ))}
        </div>
      )}

      {/* Field rows */}
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-3 items-center">
          <Label className="text-sm text-muted-foreground">Product ID</Label>
          <div className="col-span-2 flex items-center gap-2">
            <Input
              className="text-sm font-mono flex-1"
              placeholder="prod_..."
              value={form.stripe_product_id}
              onChange={(e) => setForm({ ...form, stripe_product_id: e.target.value.trim() })}
            />
            <Badge className={`text-xs ${productStatus.color}`}>{productStatus.label}</Badge>
            {!productValid && <span className="text-xs text-red-600">format</span>}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 items-center">
          <Label className="text-sm text-muted-foreground">Monthly Price ID</Label>
          <div className="col-span-2 flex items-center gap-2">
            <Input
              className="text-sm font-mono flex-1"
              placeholder="price_..."
              value={form.stripe_price_id_monthly}
              onChange={(e) => setForm({ ...form, stripe_price_id_monthly: e.target.value.trim() })}
            />
            <Badge className={`text-xs ${monthlyStatus.color}`}>{monthlyStatus.label}</Badge>
            {!monthlyValid && <span className="text-xs text-red-600">format</span>}
          </div>
        </div>

        {!isAddon && (
          <div className="grid grid-cols-3 gap-3 items-center">
            <Label className="text-sm text-muted-foreground">Yearly Price ID</Label>
            <div className="col-span-2 flex items-center gap-2">
              <Input
                className="text-sm font-mono flex-1"
                placeholder="price_... (optional)"
                value={form.stripe_price_id_yearly}
                onChange={(e) => setForm({ ...form, stripe_price_id_yearly: e.target.value.trim() })}
              />
              <Badge className={`text-xs ${yearlyStatus.color}`}>{yearlyStatus.label}</Badge>
              {!yearlyValid && <span className="text-xs text-red-600">format</span>}
            </div>
          </div>
        )}
      </div>

      {/* DB-side reference (read-only context) */}
      <div className="text-xs text-muted-foreground border-t pt-2">
        DB price: {db.price_monthly ?? '—'}/mo · {db.price_yearly ?? '—'}/yr · currency {db.currency}.
        {' '}Pricing values are edited in the Pricing section above.
      </div>

      {/* Active-subscriber guardrail */}
      {needsAckActiveSubs && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 space-y-2">
          <div className="flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-600" />
            <div className="text-xs text-red-900">
              <strong>{activeCount} active Stripe subscription(s)</strong> on this plan.
              Changing <code>stripe_product_id</code> will not migrate them — they
              keep their current Product/Price. New checkouts will use the new
              Product. To proceed, acknowledge the impact:
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-red-900">
            <input
              type="checkbox"
              checked={ackActiveSubs}
              onChange={(e) => setAckActiveSubs(e.target.checked)}
            />
            I understand existing subscribers stay on the old Product.
          </label>
        </div>
      )}

      {/* Onda 22 — Notes always visible so the requirement is discoverable
          before the admin types anything. Reveals to the user upfront that
          a note is needed for the audit trail. Hint text adjusts based on
          current state. */}
      <div>
        <Label className="text-xs text-muted-foreground">
          Note (≥ 5 caratteri, richiesto per audit){' '}
          {anyChange && notes.trim().length > 0 && notes.trim().length < 5 && (
            <span className="text-amber-700">— ancora {5 - notes.trim().length} car.</span>
          )}
        </Label>
        <Input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={anyChange
            ? 'es. "Linking Stripe Product+Price per addon AI"'
            : 'Compila i campi sopra, poi descrivi qui la modifica'}
          className="text-sm"
          disabled={!anyChange}
        />
      </div>

      <div className="flex flex-col gap-2 items-end">
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={openHistory}>
            <ScrollText className="h-3.5 w-3.5 mr-1" /> Audit history
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !anyChange || !allValid || !ackOk || !notesOk}
          >
            {saving ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</> : <><Save className="h-4 w-4 mr-1" /> Save linkage</>}
          </Button>
        </div>

        {/* Onda 22 — Inline hint listing exactly what is blocking the save.
            Only renders when the button IS disabled AND the user has
            started interacting (so we don't nag on the initial empty
            state). Universal across plans and addons. */}
        {!saving && anyChange && (!allValid || !ackOk || !notesOk) && (
          <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 max-w-md">
            <div className="font-medium mb-0.5">Per salvare manca:</div>
            <ul className="list-disc list-inside space-y-0.5">
              {!allValid && (
                <li>
                  Formato ID Stripe non valido. Product ID inizia con{' '}
                  <code>prod_</code>, Price ID con <code>price_</code>.
                </li>
              )}
              {!ackOk && (
                <li>
                  Spunta la conferma sopra (subscription attive impattate dal cambio Product).
                </li>
              )}
              {!notesOk && (
                <li>
                  Note di almeno 5 caratteri (campo qui sopra).
                </li>
              )}
            </ul>
          </div>
        )}
      </div>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5" /> Stripe linkage history — {slug}
            </DialogTitle>
            <DialogDescription>
              Every linkage / pricing mutation on this plan, most recent first.
            </DialogDescription>
          </DialogHeader>

          {historyLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !historyEntries || historyEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground italic py-6 text-center">
              No linkage changes yet on this plan.
            </p>
          ) : (
            <div className="space-y-3">
              {historyEntries.map((entry, idx) => (
                <div key={idx} className="border rounded p-3 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="font-mono text-muted-foreground">
                      {entry.performed_at}
                    </div>
                    <div>
                      <span className="text-muted-foreground">by </span>
                      <span className="font-medium">{entry.performed_by}</span>
                    </div>
                  </div>
                  {entry.notes && (
                    <div className="italic text-muted-foreground">"{entry.notes}"</div>
                  )}
                  <table className="w-full mt-2">
                    <tbody>
                      {Object.entries(entry.changes || {}).map(([field, diff]) => (
                        <tr key={field} className="border-t">
                          <td className="py-1 pr-2 font-mono text-xs text-muted-foreground">
                            {field}
                          </td>
                          <td className="py-1 px-1 text-red-700 line-through font-mono">
                            {diff.old === null || diff.old === undefined ? '∅' : String(diff.old)}
                          </td>
                          <td className="py-1 px-1 text-emerald-700 font-mono">
                            → {diff.new === null || diff.new === undefined ? '∅' : String(diff.new)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setHistoryOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// Plan Management Dialog
// ══════════════════════════════════════════════════════════════════════════════

const PlanManageDialog = ({ plan, open, onOpenChange, tiers, onRefresh, onEditTier }) => {
  // Metadata form
  const [meta, setMeta] = useState({});
  const [metaSaving, setMetaSaving] = useState(false);

  // Module plans form
  const [modulePlans, setModulePlans] = useState({});
  const [mpSaving, setMpSaving] = useState(false);

  // Pricing form
  const [pricing, setPricing] = useState({});
  const [pricingSaving, setPricingSaving] = useState(false);

  // Onda 24 Phase D — Addon-specific config (visible only when plan.is_addon)
  const [addonConfig, setAddonConfig] = useState({
    max_quantity: 1,
    compatible_plans: [],
    addon_provides_json: '{}',
  });
  const [addonSaving, setAddonSaving] = useState(false);

  // Init forms when plan changes
  useEffect(() => {
    if (plan) {
      setMeta({
        name: plan.name || '',
        description: plan.description || '',
        tagline: plan.tagline || '',
        trial_days: plan.trial_days ?? 0,
        sort_order: plan.sort_order ?? 0,
        is_public: plan.is_public ?? true,
        is_self_serve: plan.is_self_serve ?? true,
      });
      setModulePlans(plan.module_plans || {});
      setPricing({
        price_monthly: plan.price_monthly ?? 0,
        stripe_price_id_monthly: plan.stripe_price_id_monthly || '',
        price_yearly: plan.price_yearly ?? '',
        stripe_price_id_yearly: plan.stripe_price_id_yearly || '',
      });
      if (plan.is_addon) {
        setAddonConfig({
          max_quantity: plan.max_quantity ?? 1,
          compatible_plans: Array.isArray(plan.compatible_plans) ? plan.compatible_plans : [],
          addon_provides_json: JSON.stringify(plan.addon_provides || {}, null, 2),
        });
      }
    }
  }, [plan]);

  if (!plan) return null;

  const handleSaveMeta = async () => {
    setMetaSaving(true);
    try {
      await adminAPI.patchCatalogPlan(plan.slug, meta);
      toast.success('Plan metadata updated');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update metadata');
    } finally {
      setMetaSaving(false);
    }
  };

  // Onda 24 Phase D — Save addon-specific fields. Backend rejects on
  // non-addon plans (422 addon_fields_on_non_addon_plan); we only
  // expose this section when plan.is_addon=true so the request is
  // always valid by construction.
  const handleSaveAddonConfig = async () => {
    let provides;
    try {
      provides = JSON.parse(addonConfig.addon_provides_json);
      if (!provides || typeof provides !== 'object' || Array.isArray(provides)) {
        throw new Error('addon_provides must be a JSON object');
      }
    } catch (e) {
      toast.error(`addon_provides JSON non valido: ${e.message}`);
      return;
    }
    const payload = {
      addon_provides: provides,
      compatible_plans: addonConfig.compatible_plans,
      max_quantity: Number(addonConfig.max_quantity) || 1,
    };
    setAddonSaving(true);
    try {
      await adminAPI.patchCatalogPlan(plan.slug, payload);
      toast.success('Addon configuration updated');
      onRefresh();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail.message : (detail || 'Failed to update addon');
      toast.error(msg);
    } finally {
      setAddonSaving(false);
    }
  };

  const handleSaveModulePlans = async () => {
    if (!window.confirm(
      'Update module bundle?\n\n'
      + 'This changes the catalog definition for future provisioning.\n'
      + 'Already provisioned organizations are NOT automatically reprovisioned.'
    )) return;
    setMpSaving(true);
    try {
      const result = await adminAPI.patchPlanModulePlans(plan.slug, modulePlans);
      if (result?.changed) {
        toast.success('Module bundle updated');
      } else {
        toast.info('No changes detected');
      }
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update module plans');
    } finally {
      setMpSaving(false);
    }
  };

  const handleSavePricing = async () => {
    // Build pricing payload with only provided pairs
    const payload = {};
    if (pricing.price_monthly !== '' && pricing.stripe_price_id_monthly) {
      payload.price_monthly = Number(pricing.price_monthly);
      payload.stripe_price_id_monthly = pricing.stripe_price_id_monthly;
    }
    if (pricing.price_yearly !== '' && pricing.price_yearly != null && pricing.stripe_price_id_yearly) {
      payload.price_yearly = Number(pricing.price_yearly);
      payload.stripe_price_id_yearly = pricing.stripe_price_id_yearly;
    }

    if (!payload.price_monthly && !payload.price_yearly) {
      toast.error('At least one complete pricing pair is required');
      return;
    }

    if (!window.confirm(
      'Update pricing?\n\n'
      + 'This affects future checkout behavior.\n'
      + 'Existing subscribers are NOT migrated.\n'
      + 'Stripe is NOT mutated remotely.'
    )) return;

    setPricingSaving(true);
    try {
      const result = await adminAPI.patchPlanPricing(plan.slug, payload);
      if (result?.changed) {
        toast.success('Pricing updated');
      } else {
        toast.info('No pricing changes detected');
      }
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update pricing');
    } finally {
      setPricingSaving(false);
    }
  };

  // Get available tiers grouped by module for the bundle editor
  const tiersByModule = tiers || {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Manage Plan — {plan.name}
            <Badge className={PLAN_COLORS[plan.slug] || 'bg-gray-100 text-gray-700'}>
              {plan.slug}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* ── Section 1: Safe Metadata ────────────────────────────────── */}
          <section className="border rounded-lg p-4">
            <SectionTitle icon={Package}>Metadata</SectionTitle>
            <div className="space-y-3">
              <FieldRow label="Name">
                <Input value={meta.name} onChange={(e) => setMeta({ ...meta, name: e.target.value })} />
              </FieldRow>
              <FieldRow label="Description">
                <Input value={meta.description} onChange={(e) => setMeta({ ...meta, description: e.target.value })} />
              </FieldRow>
              <FieldRow label="Tagline">
                <Input value={meta.tagline} onChange={(e) => setMeta({ ...meta, tagline: e.target.value })} />
              </FieldRow>
              <FieldRow label="Trial days">
                <Input type="number" value={meta.trial_days} onChange={(e) => setMeta({ ...meta, trial_days: parseInt(e.target.value) || 0 })} className="w-24" />
              </FieldRow>
              <FieldRow label="Sort order">
                <Input type="number" value={meta.sort_order} onChange={(e) => setMeta({ ...meta, sort_order: parseInt(e.target.value) || 0 })} className="w-24" />
              </FieldRow>
              <FieldRow label="Public">
                <select
                  className="border rounded px-2 py-1 text-sm"
                  value={meta.is_public ? 'true' : 'false'}
                  onChange={(e) => setMeta({ ...meta, is_public: e.target.value === 'true' })}
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </FieldRow>
              <FieldRow label="Self-serve">
                <select
                  className="border rounded px-2 py-1 text-sm"
                  value={meta.is_self_serve ? 'true' : 'false'}
                  onChange={(e) => setMeta({ ...meta, is_self_serve: e.target.value === 'true' })}
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </FieldRow>
              <div className="flex justify-end">
                <Button size="sm" onClick={handleSaveMeta} disabled={metaSaving}>
                  {metaSaving ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</> : <><Save className="h-4 w-4 mr-1" /> Save Metadata</>}
                </Button>
              </div>
            </div>
          </section>

          {/* ── Section 2: Module Bundle ────────────────────────────────── */}
          <section className="border rounded-lg p-4">
            <SectionTitle icon={Layers}>Module Bundle (module_plans)</SectionTitle>
            <p className="text-xs text-muted-foreground mb-3">
              Changes affect future provisioning only. Already provisioned orgs are not reprovisioned.
            </p>
            <div className="space-y-2">
              {Object.entries(modulePlans).map(([mk, slugVal]) => (
                <div key={mk} className="grid grid-cols-3 gap-2 items-center">
                  <Label className="text-sm font-mono">{mk}</Label>
                  <div className="col-span-2 flex items-center gap-2">
                    {tiersByModule[mk]?.length > 0 ? (
                      <Select value={slugVal} onValueChange={(v) => setModulePlans({ ...modulePlans, [mk]: v })}>
                        <SelectTrigger className="h-8 text-sm flex-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {tiersByModule[mk].map((tier) => (
                            <SelectItem key={tier.slug} value={tier.slug}>
                              {tier.name} ({tier.slug})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input value={slugVal} onChange={(e) => setModulePlans({ ...modulePlans, [mk]: e.target.value })} className="h-8 text-sm flex-1" />
                    )}
                    {/* Onda 19 — jump-to-tier link. Closes this dialog,
                        switches the catalog view to "tiers", and flashes
                        the target tier card so the admin can edit its
                        limits inline. Wired via the onEditTier prop from
                        the parent CatalogTab. */}
                    {onEditTier && slugVal && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs flex-shrink-0"
                        title={`Modifica i limiti del tier ${slugVal}`}
                        onClick={() => onEditTier(slugVal)}
                      >
                        <Settings className="h-3 w-3 mr-1" />
                        Modifica tier
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-3">
              <Button size="sm" onClick={handleSaveModulePlans} disabled={mpSaving}>
                {mpSaving ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</> : <><Save className="h-4 w-4 mr-1" /> Save Bundle</>}
              </Button>
            </div>
          </section>

          {/* ── Section 3.5: Stripe linkage (Onda 11 Step 3) ────────────── */}
          <StripeLinkageSection slug={plan.slug} isAddon={!!plan.is_addon} />

          {/* ── Section 3: Pricing ──────────────────────────────────────── */}
          <section className="border rounded-lg p-4">
            <SectionTitle icon={CreditCard}>Pricing</SectionTitle>
            <p className="text-xs text-muted-foreground mb-3">
              Both price and Stripe Price ID must be updated as a pair. Changes affect future checkouts only.
            </p>
            <div className="space-y-3">
              <div className="border rounded p-3 space-y-2">
                <div className="text-xs font-medium text-muted-foreground">Monthly pair</div>
                <FieldRow label="Price (€/mo)">
                  <Input type="number" step="0.01" value={pricing.price_monthly} onChange={(e) => setPricing({ ...pricing, price_monthly: e.target.value })} className="w-32" />
                </FieldRow>
                <FieldRow label="Stripe Price ID">
                  <Input value={pricing.stripe_price_id_monthly} onChange={(e) => setPricing({ ...pricing, stripe_price_id_monthly: e.target.value })} placeholder="price_..." className="text-sm font-mono" />
                </FieldRow>
              </div>
              <div className="border rounded p-3 space-y-2">
                <div className="text-xs font-medium text-muted-foreground">Yearly pair</div>
                <FieldRow label="Price (€/yr)">
                  <Input type="number" step="0.01" value={pricing.price_yearly} onChange={(e) => setPricing({ ...pricing, price_yearly: e.target.value })} className="w-32" />
                </FieldRow>
                <FieldRow label="Stripe Price ID">
                  <Input value={pricing.stripe_price_id_yearly} onChange={(e) => setPricing({ ...pricing, stripe_price_id_yearly: e.target.value })} placeholder="price_..." className="text-sm font-mono" />
                </FieldRow>
              </div>
            </div>
            <div className="flex justify-end mt-3">
              <Button size="sm" onClick={handleSavePricing} disabled={pricingSaving}>
                {pricingSaving ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</> : <><Save className="h-4 w-4 mr-1" /> Save Pricing</>}
              </Button>
            </div>
          </section>

          {/* ── Onda 24 Phase D — Addon-specific config ─────────────────────
              Visible only for addons. Lets the admin edit max_quantity,
              compatible_plans, and addon_provides without resorting to
              direct DB edits. Backend rejects these fields on non-addon
              plans (422 addon_fields_on_non_addon_plan). */}
          {plan.is_addon && (
            <section className="border rounded-lg p-4">
              <SectionTitle icon={Package}>Addon Configuration</SectionTitle>
              <p className="text-xs text-muted-foreground mb-3">
                Definisce cosa l'addon fornisce, su quali piani è acquistabile,
                e quante volte può essere accumulato.
              </p>
              <div className="space-y-3">
                <FieldRow label="Max quantity">
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={addonConfig.max_quantity}
                    onChange={(e) => setAddonConfig({
                      ...addonConfig,
                      max_quantity: parseInt(e.target.value, 10) || 1,
                    })}
                    className="w-24"
                  />
                </FieldRow>
                <FieldRow label="Compatible plans">
                  <div className="flex flex-wrap gap-2">
                    {/* Multi-select via checkboxes; only non-addon plans listed */}
                    {(['free', 'starter', 'core', 'pro', 'enterprise']).map((slug) => {
                      const checked = addonConfig.compatible_plans.includes(slug);
                      return (
                        <label key={slug} className={`text-xs px-2 py-1 rounded border cursor-pointer ${
                          checked
                            ? 'bg-violet-50 border-violet-300 text-violet-800'
                            : 'bg-gray-50 border-gray-200 text-gray-600'
                        }`}>
                          <input
                            type="checkbox"
                            className="mr-1"
                            checked={checked}
                            onChange={(e) => {
                              const next = e.target.checked
                                ? [...addonConfig.compatible_plans, slug]
                                : addonConfig.compatible_plans.filter((s) => s !== slug);
                              setAddonConfig({ ...addonConfig, compatible_plans: next });
                            }}
                          />
                          {slug}
                        </label>
                      );
                    })}
                  </div>
                </FieldRow>
                <FieldRow label="addon_provides (JSON)">
                  <div className="space-y-1">
                    <textarea
                      value={addonConfig.addon_provides_json}
                      onChange={(e) => setAddonConfig({
                        ...addonConfig,
                        addon_provides_json: e.target.value,
                      })}
                      rows={5}
                      className="w-full text-xs font-mono border rounded p-2"
                      placeholder='{"ai_assistant": {"chat": 50}}'
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Mappa <code>{`{module_key: {feature_key: amount}}`}</code>.
                      Esempio: <code>{`{"ai_assistant": {"chat": 50}}`}</code> aggiunge 50 chat al limite del modulo ai_assistant.
                    </p>
                  </div>
                </FieldRow>
              </div>
              <div className="flex justify-end mt-3">
                <Button size="sm" onClick={handleSaveAddonConfig} disabled={addonSaving}>
                  {addonSaving ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Saving...</> : <><Save className="h-4 w-4 mr-1" /> Save Addon Config</>}
                </Button>
              </div>
            </section>
          )}

          {/* ── Read-only context ───────────────────────────────────────── */}
          <section className="text-xs text-muted-foreground border-t pt-3">
            <div>Slug: <span className="font-mono">{plan.slug}</span> (immutable)</div>
            <div>Subscribers: {plan.subscriber_count ?? 0} orgs</div>
            {plan.admin_modified_at && <div>Last admin edit: {plan.admin_modified_at}</div>}
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// Entitlement Tiers section
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Onda 19 — given a tier slug, return the list of CommercialPlans that
 * reference it via their module_plans mapping. Post-migration this is
 * always exactly 1 plan (1:1 isolation). For legacy/orphan tiers can be
 * 0 (unused) or, in transient states, 2+.
 */
const findPlansUsingTier = (tierSlug, allPlans) => {
  if (!Array.isArray(allPlans)) return [];
  return allPlans.filter((p) =>
    p?.module_plans
    && Object.values(p.module_plans).includes(tierSlug),
  );
};

const TierLimitsEditor = ({ tier, onSaved, usedByPlans = [], flashOnMount = false }) => {
  const [limits, setLimits] = useState(tier.limits || {});
  const [saving, setSaving] = useState(false);
  const containerRef = useRef(null);
  const [flashing, setFlashing] = useState(false);

  // Onda 19 — when navigated here from "Modifica tier" link in
  // PlanManageDialog, scroll into view + flash an orange highlight
  // for ~2.5s so the admin spots the right tier instantly.
  useEffect(() => {
    if (!flashOnMount) return undefined;
    setFlashing(true);
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    const t = setTimeout(() => setFlashing(false), 2500);
    return () => clearTimeout(t);
  }, [flashOnMount]);

  const handleSave = async () => {
    if (!window.confirm(
      `Update limits for "${tier.slug}"?\n\n`
      + 'This immediately changes enforcement for all organizations subscribed to this tier.'
    )) return;
    setSaving(true);
    try {
      const result = await adminAPI.patchTierLimits(tier.slug, limits);
      if (result?.changed) {
        toast.success(`Limits updated (${result.impact_count} active subscriptions affected)`);
      } else {
        toast.info('No changes detected');
      }
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update limits');
    } finally {
      setSaving(false);
    }
  };

  const sharedWarning = usedByPlans.length >= 2;

  return (
    <div
      ref={containerRef}
      className={`border rounded p-3 text-sm transition-colors duration-700 ${
        flashing ? 'border-amber-400 bg-amber-50' : ''
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex-1 min-w-0">
          <span className="font-medium">{tier.name}</span>
          <span className="ml-2 text-xs text-muted-foreground font-mono">{tier.slug}</span>
        </div>
        <Button variant="outline" size="sm" onClick={handleSave} disabled={saving} className="h-7 text-xs">
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}
          Save
        </Button>
      </div>

      {/* Onda 19 — Used-by chip row. Shows which CommercialPlans reference
          this tier. Post-Onda-19 migration this is always exactly 1.
          Multi-plan badges trigger a shared-tier warning. */}
      <div className="flex flex-wrap items-center gap-1.5 mb-2 text-xs">
        <span className="text-muted-foreground">Used by:</span>
        {usedByPlans.length === 0 ? (
          <Badge variant="outline" className="text-[11px] text-gray-500 italic">
            (none — orphan tier)
          </Badge>
        ) : (
          usedByPlans.map((p) => (
            <Badge
              key={p.slug}
              className={`${PLAN_COLORS[p.slug] || 'bg-gray-100 text-gray-700'} text-[11px]`}
            >
              {p.name || p.slug}
            </Badge>
          ))
        )}
        {sharedWarning && (
          <span className="text-[11px] text-amber-700 ml-1 inline-flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            shared by {usedByPlans.length} plans — edits affect all
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {Object.entries(limits).map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <Label className="text-xs text-muted-foreground w-28 truncate">{key}</Label>
            <Input
              type="number"
              value={val}
              onChange={(e) => setLimits({ ...limits, [key]: parseInt(e.target.value) })}
              className="h-7 w-20 text-xs"
            />
            <span className="text-xs text-muted-foreground">{val === -1 ? '∞' : ''}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// Audit section
// ══════════════════════════════════════════════════════════════════════════════

const AuditSection = ({ entries }) => {
  if (!entries || entries.length === 0) {
    return <p className="text-xs text-muted-foreground italic">No catalog audit entries yet.</p>;
  }
  return (
    <div className="space-y-2">
      {entries.map((e, i) => (
        <div key={e.id || i} className="border rounded p-2 text-xs">
          <div className="flex items-center justify-between">
            <Badge variant="outline">{e.action}</Badge>
            <span className="text-muted-foreground">{e.performed_at?.slice(0, 19)?.replace('T', ' ')}</span>
          </div>
          <div className="mt-1">
            <span className="text-muted-foreground">{e.entity_type}</span>
            <span className="mx-1">→</span>
            <span className="font-mono">{e.entity_id}</span>
            <span className="mx-2 text-muted-foreground">by {e.performed_by}</span>
          </div>
          {e.notes && <div className="mt-1 text-muted-foreground italic">{e.notes}</div>}
        </div>
      ))}
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// Onda 10 Step C.5 — "+ New" creator dialog
// ══════════════════════════════════════════════════════════════════════════════
//
// Single dialog component that handles 3 entity kinds via the `kind` prop:
//   · 'tier'  → POST /admin/catalog/entitlement-tiers (Step C.1)
//   · 'plan'  → POST /admin/catalog/plans            (Step C.2)
//   · 'addon' → POST /admin/catalog/addons           (Step C.3)
//
// Limits / addon_provides / module_plans are entered as raw JSON in a
// textarea — keeps the UI lean without losing flexibility. Future
// iterations can add structured editors per field type.

const NewCatalogEntityDialog = ({ kind, open, onOpenChange, onCreated }) => {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Reset form when opened or kind changes
  useEffect(() => {
    if (!open) return;
    setError(null);
    setForm(
      kind === 'tier'
        ? { slug: '', module_key: 'cashflow_monitor', name: '', limits_json: '{\n  "data_rows": 200\n}' }
        : kind === 'plan'
        ? {
            slug: '', name: '', description: '', tagline: '',
            price_monthly: '', price_yearly: '',
            module_plans_json: '{}',
            platform_limits_json: '{\n  "team_members": 1,\n  "chat_session_ttl_days": 30,\n  "stores_max_abuse_cap": 10\n}',
            auto_create_stripe: false,
          }
        : { // addon
            slug: '', name: '', description: '',
            price_monthly: '',
            addon_provides_json: '{\n  "ai_assistant": {\n    "chat": 50\n  }\n}',
            compatible_plans_csv: 'starter,core,pro',
            max_quantity: 1,
            auto_create_stripe: false,
          }
    );
  }, [open, kind]);

  const updateField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const parseJsonField = (raw, fieldLabel) => {
    if (!raw || raw.trim() === '') return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      throw new Error(`${fieldLabel} non e' JSON valido: ${e.message}`);
    }
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      let result;
      if (kind === 'tier') {
        const limits = parseJsonField(form.limits_json, 'Limits');
        result = await adminAPI.createTier({
          slug: form.slug,
          module_key: form.module_key,
          name: form.name,
          limits,
        });
        toast.success(`Tier "${form.slug}" creato`);
      } else if (kind === 'plan') {
        const module_plans = parseJsonField(form.module_plans_json, 'module_plans');
        const platform_limits = parseJsonField(form.platform_limits_json, 'platform_limits');
        result = await adminAPI.createPlan({
          slug: form.slug,
          name: form.name,
          description: form.description || '',
          tagline: form.tagline || '',
          price_monthly: parseFloat(form.price_monthly) || 0,
          price_yearly: form.price_yearly ? parseFloat(form.price_yearly) : null,
          module_plans: module_plans || undefined,
          platform_limits: platform_limits || undefined,
          auto_create_stripe: !!form.auto_create_stripe,
        });
        const stripe = result?.stripe;
        if (stripe?.error) {
          toast.warning(`Plan creato. Stripe failed: ${stripe.error}`);
        } else if (stripe?.result?.stripe_product_id) {
          toast.success(`Plan "${form.slug}" creato + Stripe ${stripe.result.stripe_product_id}`);
        } else {
          toast.success(`Plan "${form.slug}" creato`);
        }
      } else { // addon
        const addon_provides = parseJsonField(form.addon_provides_json, 'addon_provides');
        const compatible_plans = (form.compatible_plans_csv || '')
          .split(',').map((s) => s.trim()).filter(Boolean);
        result = await adminAPI.createAddon({
          slug: form.slug,
          name: form.name,
          description: form.description || '',
          price_monthly: parseFloat(form.price_monthly) || 0,
          addon_provides,
          compatible_plans: compatible_plans.length ? compatible_plans : undefined,
          max_quantity: parseInt(form.max_quantity) || 1,
          auto_create_stripe: !!form.auto_create_stripe,
        });
        const stripe = result?.stripe;
        if (stripe?.error) {
          toast.warning(`Addon creato. Stripe failed: ${stripe.error}`);
        } else if (stripe?.result?.stripe_product_id) {
          toast.success(`Addon "${form.slug}" creato + Stripe ${stripe.result.stripe_product_id}`);
        } else {
          toast.success(`Addon "${form.slug}" creato`);
        }
      }
      onCreated?.();
      onOpenChange(false);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Errore');
    } finally {
      setSaving(false);
    }
  };

  const titleByKind = { tier: 'Crea nuovo Tier', plan: 'Crea nuovo Plan', addon: 'Crea nuovo Addon' };
  const showStripeFlag = kind === 'plan' || kind === 'addon';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" /> {titleByKind[kind]}
          </DialogTitle>
          <DialogDescription>
            Onda 10 Step C — self-serve catalog creation. Audit log entry written on success.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {/* Common fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Slug *</Label>
              <Input
                placeholder="es. growth, cashflow_monitor_growth"
                value={form.slug || ''}
                onChange={(e) => updateField('slug', e.target.value.toLowerCase())}
              />
              <p className="text-[11px] text-muted-foreground mt-1">3-60 chars, [a-z0-9_]</p>
            </div>
            <div>
              <Label>Name *</Label>
              <Input
                placeholder="Display name"
                value={form.name || ''}
                onChange={(e) => updateField('name', e.target.value)}
              />
            </div>
          </div>

          {kind === 'tier' && (
            <>
              <div>
                <Label>Module key *</Label>
                <Input
                  placeholder="es. cashflow_monitor, ai_assistant, commerce"
                  value={form.module_key || ''}
                  onChange={(e) => updateField('module_key', e.target.value)}
                />
              </div>
              <div>
                <Label>Limits (JSON)</Label>
                <textarea
                  className="w-full text-xs font-mono border rounded p-2 min-h-[120px]"
                  value={form.limits_json || ''}
                  onChange={(e) => updateField('limits_json', e.target.value)}
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  Es: {`{"data_rows": 500, "export": -1, "alert_config": -1}`}
                </p>
              </div>
            </>
          )}

          {kind === 'plan' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Description</Label>
                  <Input value={form.description || ''} onChange={(e) => updateField('description', e.target.value)} />
                </div>
                <div>
                  <Label>Tagline</Label>
                  <Input value={form.tagline || ''} onChange={(e) => updateField('tagline', e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Price monthly (EUR)</Label>
                  <Input type="number" step="0.01" value={form.price_monthly || ''} onChange={(e) => updateField('price_monthly', e.target.value)} />
                </div>
                <div>
                  <Label>Price yearly (EUR)</Label>
                  <Input type="number" step="0.01" value={form.price_yearly || ''} onChange={(e) => updateField('price_yearly', e.target.value)} />
                </div>
              </div>
              <div>
                <Label>module_plans (JSON: {`{module_key: tier_slug}`})</Label>
                <textarea
                  className="w-full text-xs font-mono border rounded p-2 min-h-[100px]"
                  value={form.module_plans_json || ''}
                  onChange={(e) => updateField('module_plans_json', e.target.value)}
                />
              </div>
              <div>
                <Label>platform_limits (JSON)</Label>
                <textarea
                  className="w-full text-xs font-mono border rounded p-2 min-h-[100px]"
                  value={form.platform_limits_json || ''}
                  onChange={(e) => updateField('platform_limits_json', e.target.value)}
                />
              </div>
            </>
          )}

          {kind === 'addon' && (
            <>
              <div>
                <Label>Description</Label>
                <Input value={form.description || ''} onChange={(e) => updateField('description', e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Price monthly (EUR) *</Label>
                  <Input type="number" step="0.01" value={form.price_monthly || ''} onChange={(e) => updateField('price_monthly', e.target.value)} />
                </div>
                <div>
                  <Label>Max quantity</Label>
                  <Input type="number" min="1" value={form.max_quantity || 1} onChange={(e) => updateField('max_quantity', e.target.value)} />
                </div>
              </div>
              <div>
                <Label>addon_provides (JSON: {`{module: {feature: int}}`})</Label>
                <textarea
                  className="w-full text-xs font-mono border rounded p-2 min-h-[100px]"
                  value={form.addon_provides_json || ''}
                  onChange={(e) => updateField('addon_provides_json', e.target.value)}
                />
              </div>
              <div>
                <Label>Compatible plans (CSV)</Label>
                <Input
                  placeholder="es. starter,core,pro"
                  value={form.compatible_plans_csv || ''}
                  onChange={(e) => updateField('compatible_plans_csv', e.target.value)}
                />
              </div>
            </>
          )}

          {showStripeFlag && (
            <div className="flex items-center gap-2 p-3 rounded border bg-blue-50/30">
              <input
                type="checkbox"
                id="auto-stripe"
                checked={!!form.auto_create_stripe}
                onChange={(e) => updateField('auto_create_stripe', e.target.checked)}
              />
              <Label htmlFor="auto-stripe" className="text-sm font-normal cursor-pointer">
                <strong>Auto-create Stripe Product+Price</strong>
                <span className="text-muted-foreground ml-1">(C.4 flow, idempotente, non-fatal)</span>
              </Label>
            </div>
          )}

          {error && (
            <div className="p-2 rounded border-l-4 border-red-500 bg-red-50 text-sm text-red-700">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annulla</Button>
          <Button onClick={handleSubmit} disabled={saving || !form.slug || !form.name}>
            {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
            Crea
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// Main CatalogTab
// ══════════════════════════════════════════════════════════════════════════════

const CatalogTab = () => {
  const [plans, setPlans] = useState([]);
  const [tiers, setTiers] = useState({});
  const [auditEntries, setAuditEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Management dialog
  const [managePlan, setManagePlan] = useState(null);
  const [manageOpen, setManageOpen] = useState(false);

  // Onda 19 — flashTierSlug drives the orange-flash highlight in the
  // Tiers view when the admin clicks "Modifica tier" from the Plan
  // Manage Dialog. Set it before switching view to 'tiers' and the
  // matching TierLimitsEditor scrolls into view + flashes for 2.5s.
  const [flashTierSlug, setFlashTierSlug] = useState(null);

  // Onda 10 Step C.5 — "+ New" creator dialog state.
  // entityKind ∈ {'tier', 'plan', 'addon'} drives which form fields show.
  const [createOpen, setCreateOpen] = useState(false);
  const [createKind, setCreateKind] = useState('plan');

  // View mode: 'plans' | 'tiers' | 'audit'
  const [view, setView] = useState('plans');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [plansData, tiersData, auditData] = await Promise.all([
        adminAPI.getCatalogPlans(),
        adminAPI.getEntitlementTiers(),
        adminAPI.getCatalogAuditLog({ limit: 20 }),
      ]);
      setPlans(Array.isArray(plansData) ? plansData : []);
      setTiers(tiersData || {});
      setAuditEntries(Array.isArray(auditData) ? auditData : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleManage = (plan) => {
    setManagePlan(plan);
    setManageOpen(true);
  };

  const handleRefresh = () => {
    fetchAll();
    // Also refresh the plan in the dialog if open
    if (managePlan?.slug) {
      adminAPI.getCatalogPlan(managePlan.slug)
        .then((data) => setManagePlan(data))
        .catch(() => {});
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Commercial Catalog
              </CardTitle>
              <CardDescription>Manage plans, entitlements, pricing, and module bundles</CardDescription>
            </div>
            <div className="flex gap-1 items-center">
              <Button variant={view === 'plans' ? 'default' : 'outline'} size="sm" onClick={() => setView('plans')}>
                <Package className="h-3.5 w-3.5 mr-1" /> Plans
              </Button>
              <Button variant={view === 'tiers' ? 'default' : 'outline'} size="sm" onClick={() => setView('tiers')}>
                <Layers className="h-3.5 w-3.5 mr-1" /> Tiers
              </Button>
              <Button variant={view === 'audit' ? 'default' : 'outline'} size="sm" onClick={() => setView('audit')}>
                <ScrollText className="h-3.5 w-3.5 mr-1" /> Audit
              </Button>
              {/* Onda 10 Step C.5 — "+ New" buttons (visible only in plans/tiers view) */}
              <div className="ml-2 border-l pl-2 flex gap-1">
                <Button
                  variant="default" size="sm"
                  onClick={() => { setCreateKind('plan'); setCreateOpen(true); }}
                  title="Crea nuovo plan commerciale"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Plan
                </Button>
                <Button
                  variant="outline" size="sm"
                  onClick={() => { setCreateKind('tier'); setCreateOpen(true); }}
                  title="Crea nuovo entitlement tier"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Tier
                </Button>
                <Button
                  variant="outline" size="sm"
                  onClick={() => { setCreateKind('addon'); setCreateOpen(true); }}
                  title="Crea nuovo addon"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Addon
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Loading */}
          {loading && (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="py-6 text-center">
              <AlertTriangle className="h-8 w-8 mx-auto text-red-400 mb-2" />
              <p className="text-sm text-red-600">{error}</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={fetchAll}>Retry</Button>
            </div>
          )}

          {/* Plans view */}
          {!loading && !error && view === 'plans' && (
            <div className="space-y-3">
              {plans.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No commercial plans found.</p>
              ) : (
                plans.map((plan) => (
                  <PlanCard key={plan.slug} plan={plan} onManage={handleManage} />
                ))
              )}
            </div>
          )}

          {/* Tiers view */}
          {!loading && !error && view === 'tiers' && (
            <div className="space-y-4">
              {Object.keys(tiers).length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No entitlement tiers found.</p>
              ) : (
                Object.entries(tiers).map(([moduleKey, moduleTiers]) => (
                  <div key={moduleKey}>
                    <SectionTitle icon={Layers}>{moduleKey}</SectionTitle>
                    <div className="space-y-2">
                      {moduleTiers.map((tier) => (
                        <TierLimitsEditor
                          key={tier.slug}
                          tier={tier}
                          onSaved={fetchAll}
                          /* Onda 19 — pass the list of plans referencing
                             this tier so the editor can render
                             "Used by: [plan]" badges and the shared-tier
                             warning when applicable. */
                          usedByPlans={findPlansUsingTier(tier.slug, plans)}
                          flashOnMount={flashTierSlug === tier.slug}
                        />
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Audit view */}
          {!loading && !error && view === 'audit' && (
            <AuditSection entries={auditEntries} />
          )}
        </CardContent>
      </Card>

      {/* Plan Management Dialog */}
      <PlanManageDialog
        plan={managePlan}
        open={manageOpen}
        onOpenChange={setManageOpen}
        tiers={tiers}
        onRefresh={handleRefresh}
        /* Onda 19 — admin clicks "Modifica tier" inside the Module
           bundle section. Close the dialog, switch the catalog view
           to "tiers", and flash the target tier card so it pops out
           visually. The flash auto-clears in TierLimitsEditor. */
        onEditTier={(tierSlug) => {
          setManageOpen(false);
          setView('tiers');
          setFlashTierSlug(tierSlug);
          // Clear the flash signal after the editor has consumed it.
          // 3s > the 2.5s flash duration in TierLimitsEditor, so a
          // second click on the same tier still re-fires the flash.
          setTimeout(() => setFlashTierSlug(null), 3000);
        }}
      />

      {/* Onda 10 Step C.5 — New entity creator dialog */}
      <NewCatalogEntityDialog
        kind={createKind}
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={fetchAll}
      />
    </>
  );
};

export default CatalogTab;
