import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import {
  ShoppingCart, Plus, Trash2, Loader2, RefreshCw, Check, X as XIcon,
  Clock, CheckCircle2, Ban, AlertTriangle, Package, Truck, MapPin, Upload,
  ExternalLink,
} from 'lucide-react';
import { ordersAPI, customersAPI, productsAPI } from '../../api';
import { eventOccurrencesAPI } from '../../api/eventOccurrences';
import { toast } from 'sonner';
import QuotaProgressBanner from '../../components/QuotaProgressBanner';
import { useEntitlements } from '../../hooks/useEntitlements';
import { isPaywallHandled } from '../../utils/handleApiError';
import { ITEM_TYPE_LABELS, getItemTypeBadgeClass } from '../../constants/itemTypes';
import { OrderImportDialog } from './OrderImportDialog';
import TrackingDialog from './TrackingDialog';
import OrderCustomerCard from './components/OrderCustomerCard';
import OrderFieldsSection from './components/OrderFieldsSection';
import CopyButton from './components/CopyButton';
import OrderLineItem from './components/OrderLineItem';
import IssuedEntitiesSection from './components/IssuedEntitiesSection';
import { useCurrency } from '../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../lib/utils';

/**
 * CH compliance v1: currency-aware money formatter for the merchant UI.
 * `currency` falls back to "EUR" so legacy call paths without an order
 * snapshot keep their previous formatting. CHF orders flow through the
 * Swiss-style branch in `lib/utils.formatCurrency`.
 */
const fmtMoney = (v, currency = 'EUR') =>
  v != null ? fmtCurrency(Number(v), currency) : '-';

/* ── Badge config (single source of truth) ─────────────────────────────────── */

const STATUS = {
  draft:     { key: 'draft',     className: 'bg-gray-100 text-gray-700' },
  confirmed: { key: 'confirmed', className: 'bg-blue-100 text-blue-700' },
  completed: { key: 'completed', className: 'bg-emerald-100 text-emerald-700' },
  cancelled: { key: 'cancelled', className: 'bg-red-100 text-red-700' },
  expired:   { key: 'expired',   className: 'bg-amber-100 text-amber-700' },
};

const PAYMENT = {
  pending: { key: 'pending', className: 'bg-amber-100 text-amber-700' },
  paid:    { key: 'paid',    className: 'bg-emerald-100 text-emerald-700' },
  overdue: { key: 'overdue', className: 'bg-red-100 text-red-700' },
};

const SOURCE = {
  storefront:          { key: 'storefront',          className: 'bg-purple-100 text-purple-700' },
  storefront_direct:   { key: 'storefront_direct',   className: 'bg-blue-100 text-blue-700' },
  storefront_approval: { key: 'storefront_approval', className: 'bg-amber-100 text-amber-700' },
  manual:              { key: 'manual',              className: 'bg-gray-100 text-gray-500' },
  import:              { key: 'import',              className: 'bg-teal-100 text-teal-700' },
};

const getSource = (o) => {
  if (o.source?.startsWith('storefront')) return o.source;
  if (o.source === 'import') return 'import';
  return 'manual';
};

const statusBadge = (key, t) => {
  const s = STATUS[key] || STATUS.draft;
  return <Badge className={`text-xs ${s.className}`}>{t(`status.${key}`)}</Badge>;
};

const paymentBadge = (key, t) => {
  const p = PAYMENT[key] || PAYMENT.pending;
  return <Badge className={`text-xs ${p.className}`}>{t(`payment.${key}`)}</Badge>;
};

const sourceBadge = (key, t) => {
  const s = SOURCE[key] || SOURCE.manual;
  return <Badge className={`text-[10px] px-1.5 py-0 ${s.className}`}>{t(`source.${s.key}`)}</Badge>;
};

/* ── Order Form Dialog ─────────────────────────────────────────────────────── */

function OrderFormDialog({ open, onClose, onSaved, editing, prefillCustomerId, customers, products, onCustomerCreated, t }) {
  // While editing an existing order we honour its snapshot; new orders
  // borrow the org's currency so the live total reads in the right unit
  // before the server stamps the snapshot at create-time.
  const orgCurrency = useCurrency();
  const formCurrency = editing?.currency || orgCurrency;
  const [form, setForm] = useState({ customer_id: '', notes: '', due_date: '', items: [] });
  const [saving, setSaving] = useState(false);
  const [newCustOpen, setNewCustOpen] = useState(false);
  const [newCust, setNewCust] = useState({ name: '', email: '', phone: '', address: '' });
  const [newCustSaving, setNewCustSaving] = useState(false);

  useEffect(() => {
    if (open) {
      if (editing) {
        setForm({
          customer_id: editing.customer_id || '',
          notes: editing.notes || '',
          due_date: editing.due_date || '',
          items: (editing.items || []).map(it => ({
            product_id: it.product_id,
            quantity: it.quantity,
            unit_price: it.unit_price,
            occurrence_id: it.occurrence_id || '',
          })),
        });
      } else {
        setForm({
          customer_id: prefillCustomerId || '',
          notes: '', due_date: '',
          items: [{ product_id: '', quantity: 1, unit_price: '', occurrence_id: '' }],
        });
      }
    }
  }, [open, editing]);

  // WS-1.3 — date disponibili per i prodotti-ritiro nel form manuale:
  // scegliendo la data, l'ordine genera lo schedule (caparra/saldo) come
  // dal sito. Prenotazione telefonica con piano pagamenti in un form.
  const [occByProduct, setOccByProduct] = React.useState({});
  const loadOccurrences = React.useCallback(async (productId) => {
    if (!productId || occByProduct[productId]) return;
    try {
      const res = await eventOccurrencesAPI.list(productId);
      const occs = (res.data || []).filter(o => ['draft', 'published'].includes(o.status));
      setOccByProduct(m => ({ ...m, [productId]: occs }));
    } catch { /* prodotto non-evento: nessuna data */ }
  }, [occByProduct]);

  const addItem = () => setForm(f => ({ ...f, items: [...f.items, { product_id: '', quantity: 1, unit_price: '', occurrence_id: '' }] }));
  const removeItem = (i) => setForm(f => ({ ...f, items: f.items.filter((_, idx) => idx !== i) }));
  const updateItem = (i, field, value) => setForm(f => ({
    ...f, items: f.items.map((it, idx) => idx === i ? { ...it, [field]: value } : it),
  }));

  const lineTotal = (item) => {
    const prod = products.find(p => p.id === item.product_id);
    const price = item.unit_price !== '' ? parseFloat(item.unit_price) : (prod?.unit_price || 0);
    return (parseFloat(item.quantity) || 0) * (price || 0);
  };
  const isLineValid = (item) => item.product_id && parseFloat(item.quantity) > 0;
  const isLineComplete = (item) => isLineValid(item) && lineTotal(item) > 0;
  const orderTotal = form.items.reduce((sum, it) => sum + lineTotal(it), 0);
  const validLines = form.items.filter(isLineValid).length;
  const canSave = form.customer_id && validLines > 0 && form.items.every(isLineValid);
  const hasZeroTotal = canSave && orderTotal === 0;

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        customer_id: form.customer_id,
        notes: form.notes || null,
        due_date: form.due_date || null,
        items: form.items.map(it => ({
          product_id: it.product_id,
          quantity: parseFloat(it.quantity),
          unit_price: it.unit_price !== '' ? parseFloat(it.unit_price) : null,
          // WS-1.3: la data del ritiro attiva lo schedule pagamenti
          occurrence_id: it.occurrence_id || null,
        })),
      };
      if (editing) {
        await ordersAPI.update(editing.id, payload);
        toast.success(t('toast.updated'));
      } else {
        await ordersAPI.create(payload);
        toast.success(t('toast.created'));
      }
      onSaved();
      onClose();
    } catch (err) {
      // v5.8 / Onda 9.O — commerce.orders_monthly quota → paywall takes over.
      // v5.8 / Onda 9.R — close the order dialog so paywall is the single modal.
      // v5.8 / Onda 9.Y.0.1 — fix ReferenceError: this handler lives inside
      // <OrderFormDialog> which receives `onClose` as prop, NOT the parent's
      // `setDialogOpen` setter. Calling setDialogOpen here threw at runtime
      // any time the backend rejected with a paywall code (429 orders_monthly,
      // 403 checkout_stripe), which prevented the paywall modal from opening
      // and gave the false impression that the gate was broken.
      if (isPaywallHandled(err)) {
        onClose();
      } else {
        toast.error(err?.response?.data?.detail || t('toast.error'));
      }
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editing ? t('form.edit_order') : t('form.new_order')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Customer */}
          <div>
            <Label>{t('form.customer')} *</Label>
            {newCustOpen ? (
              <div className="mt-1 rounded-lg border p-3 space-y-2 bg-muted/30">
                <p className="text-xs font-medium text-muted-foreground mb-1">{t('form.new_customer')}</p>
                <input
                  type="text" placeholder={t('form.new_customer_name')} required value={newCust.name}
                  onChange={e => setNewCust({ ...newCust, name: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="email" placeholder={t('form.new_customer_email')} value={newCust.email}
                    onChange={e => setNewCust({ ...newCust, email: e.target.value })}
                    className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  />
                  <input
                    type="tel" placeholder={t('form.new_customer_phone')} value={newCust.phone}
                    onChange={e => setNewCust({ ...newCust, phone: e.target.value })}
                    className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  />
                </div>
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    disabled={!newCust.name.trim() || newCustSaving}
                    onClick={async () => {
                      setNewCustSaving(true);
                      try {
                        const res = await customersAPI.create({
                          name: newCust.name.trim(),
                          email: newCust.email.trim() || null,
                          phone: newCust.phone.trim() || null,
                        });
                        const created = res.data;
                        onCustomerCreated(created);
                        setForm(f => ({ ...f, customer_id: created.id }));
                        setNewCustOpen(false);
                        setNewCust({ name: '', email: '', phone: '', address: '' });
                        toast.success(t('toast.customer_created'));
                      } catch (err) {
                        toast.error(err?.response?.data?.detail || t('toast.customer_error'));
                      } finally { setNewCustSaving(false); }
                    }}
                    className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50"
                  >
                    {newCustSaving ? '...' : t('form_extra.create_btn')}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setNewCustOpen(false); setNewCust({ name: '', email: '', phone: '', address: '' }); }}
                    className="px-3 py-1.5 rounded-md border text-xs"
                  >
                    {t('form.new_customer_cancel')}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2 mt-1">
                <select
                  value={form.customer_id}
                  onChange={e => setForm({ ...form, customer_id: e.target.value })}
                  className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">{t('form.customer_placeholder')}</option>
                  {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <button
                  type="button"
                  onClick={() => setNewCustOpen(true)}
                  className="shrink-0 px-3 py-2 rounded-md border border-dashed text-xs text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
                >
                  {t('form.new_customer_btn')}
                </button>
              </div>
            )}
          </div>

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>{t('form.items')}</Label>
              <Button variant="outline" size="sm" onClick={addItem} className="gap-1">
                <Plus className="h-3.5 w-3.5" /> {t('form.add_item')}
              </Button>
            </div>
            {products.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('form.no_products')}</p>
            ) : (
              <div className="space-y-2">
                {form.items.map((item, i) => {
                  const prod = products.find(p => p.id === item.product_id);
                  const incomplete = item.product_id && !isLineComplete(item);
                  const missing = !item.product_id;
                  return (
                    <div key={i} className={`flex items-end gap-2 rounded-lg border p-2 ${incomplete ? 'border-amber-300 bg-amber-50/30' : missing ? 'border-dashed' : ''}`}>
                      <div className="flex-1 min-w-0">
                        <Label className="text-xs">{t('form.product')}</Label>
                        <select
                          value={item.product_id}
                          onChange={e => {
                            const p = products.find(pp => pp.id === e.target.value);
                            updateItem(i, 'product_id', e.target.value);
                            updateItem(i, 'occurrence_id', '');
                            if (p?.unit_price) updateItem(i, 'unit_price', p.unit_price);
                            if (p?.item_type === 'event_ticket') loadOccurrences(p.id);
                          }}
                          className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                        >
                          <option value="">{t('form.product_placeholder')}</option>
                          {products.map(p => <option key={p.id} value={p.id}>{p.name}{p.sku ? ` (${p.sku})` : ''}</option>)}
                        </select>
                        {prod?.item_type === 'event_ticket' && (
                          <select
                            value={item.occurrence_id || ''}
                            onChange={e => updateItem(i, 'occurrence_id', e.target.value)}
                            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs"
                          >
                            <option value="">{t('form.occurrence_placeholder')}</option>
                            {(occByProduct[prod.id] || []).map(o => (
                              <option key={o.id} value={o.id}>
                                {new Date(o.start_at).toLocaleDateString('it-IT')} {o.venue_name || o.city || ''}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                      <div className="w-16">
                        <Label className="text-xs">{t('form.quantity')}</Label>
                        <Input type="number" min="1" step="1" value={item.quantity}
                          onChange={e => updateItem(i, 'quantity', e.target.value)} className="px-2 py-1.5" />
                      </div>
                      <div className="w-24">
                        <Label className="text-xs">{t('form.unit_price')}</Label>
                        <Input type="number" step="0.01" value={item.unit_price}
                          placeholder={prod?.unit_price?.toFixed(2) || '0.00'}
                          onChange={e => updateItem(i, 'unit_price', e.target.value)} className="px-2 py-1.5" />
                      </div>
                      <div className="w-24 text-right">
                        <Label className="text-xs">{t('form.line_total')}</Label>
                        <p className="text-sm font-medium py-1.5">{fmtMoney(lineTotal(item), formCurrency)}</p>
                      </div>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeItem(i)} disabled={form.items.length <= 1}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Total */}
          <div className="flex items-center justify-between border-t pt-3 bg-muted/20 -mx-6 px-6 py-3 rounded-b-lg">
            <div className="text-xs text-muted-foreground">
              {t('form.products_count', { count: validLines })}
              {hasZeroTotal && <span className="ml-2 text-amber-600">— {t('form.zero_total_hint')}</span>}
            </div>
            <div className="text-right">
              <span className="text-xs text-muted-foreground">{t('form.total')}</span>
              <p className={`text-xl font-bold ${hasZeroTotal ? 'text-amber-600' : ''}`}>{fmtMoney(orderTotal, formCurrency)}</p>
            </div>
          </div>

          {/* Notes + due date */}
          <div className="grid grid-cols-2 gap-3">
            <div><Label>{t('form.due_date')}</Label><Input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} /></div>
            <div><Label>{t('form.notes')}</Label><Textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={1} /></div>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <div className="flex-1 text-xs text-muted-foreground hidden sm:block">
            {!canSave && form.items.length > 0 && (
              !form.customer_id ? t('form.hint_select_customer') :
              validLines === 0 ? t('form.hint_add_product') :
              t('form.hint_complete_lines')
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              {editing ? t('form_extra.close') : t('form_extra.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={saving || !canSave}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editing ? t('form.save_changes') : t('form.save_draft')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ── Payment Operations Section ────────────────────────────────────────────── */

// Build a direct link to the payment intent in the Stripe Dashboard.
// For Connect-collected charges we scope the link to the connected account so
// the admin lands on the right view. Mode (test/live) is inferred from the
// Checkout Session reference prefix — Stripe prefixes "cs_test_" in test mode
// and "cs_live_" in live mode, which is the most reliable signal we have
// without adding a server-side field.
function stripeDashboardUrl({ stripe_payment_intent_id, connected_account_id, reference }) {
  if (!stripe_payment_intent_id) return null;
  const mode = reference?.startsWith('cs_test_') ? 'test' : null; // live URL omits segment
  const parts = ['https://dashboard.stripe.com'];
  if (mode) parts.push(mode);
  if (connected_account_id) {
    parts.push(`connect/accounts/${connected_account_id}`);
  }
  parts.push(`payments/${stripe_payment_intent_id}`);
  return parts.join('/');
}

// Parse payment expiry and decide whether it should be surfaced to the admin.
// Returns null when no expiry is set or the order is not awaiting payment.
// hoursRemaining < 24 → warn=true (amber badge).
function parsePaymentExpiry(order) {
  const pc = order.payment_checkout || {};
  // Stripe checkout sessions typically expose expires_at; server may also store
  // payment_intent_expires_at on the order. Accept either.
  const iso = order.payment_intent_expires_at || pc.expires_at || pc.payment_intent_expires_at;
  if (!iso) return null;
  if (order.payment_intent !== 'required') return null;
  if (order.status !== 'draft') return null;
  try {
    const d = typeof iso === 'number' ? new Date(iso * 1000) : new Date(iso);
    const now = new Date();
    const msLeft = d.getTime() - now.getTime();
    const hours = msLeft / (1000 * 60 * 60);
    return {
      expiresAt: d,
      expired: msLeft <= 0,
      hoursRemaining: hours,
      warn: hours > 0 && hours < 24,
    };
  } catch {
    return null;
  }
}

function PaymentOpsSection({ order, onAction }) {
  const { t } = useTranslation('orders');
  const pc = order.payment_checkout || {};
  const isPaidNotConfirmed = order.payment_intent === 'collected' && order.status === 'draft';
  const isAwaitingPayment = order.payment_intent === 'required' && order.status === 'draft';
  const hasConfirmError = !!pc.confirm_error;
  const processedEvents = Array.isArray(pc.processed_events) ? pc.processed_events : [];
  const dashboardUrl = stripeDashboardUrl(pc);
  const expiry = parsePaymentExpiry(order);
  const hasCoupon = !!(order.coupon_code || order.discount_amount);

  return (
    <div className="rounded-lg border p-3 space-y-2">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{t('payment.pending', 'Payment')}</h4>

      {expiry && (expiry.expired || expiry.warn) && (
        <div className={`rounded-md p-2 text-xs flex items-center gap-2 ${
          expiry.expired
            ? 'bg-red-50 border border-red-200 text-red-700'
            : 'bg-amber-50 border border-amber-200 text-amber-700'
        }`}>
          <Clock className="h-3.5 w-3.5 shrink-0" />
          {expiry.expired
            ? t('payment_ops.expired', { defaultValue: 'Sessione pagamento scaduta' })
            : t('payment_ops.expires_soon', {
                hours: Math.max(1, Math.round(expiry.hoursRemaining)),
                defaultValue: `Scade tra circa ${Math.max(1, Math.round(expiry.hoursRemaining))}h`,
              })}
          <span className="ml-auto text-[10px]">
            {expiry.expiresAt.toLocaleString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      )}

      {hasCoupon && (
        <div className="text-xs text-muted-foreground">
          {order.coupon_code && (
            <span>
              {t('payment_ops.coupon', { defaultValue: 'Coupon' })}:{' '}
              <span className="font-mono font-medium text-foreground">{order.coupon_code}</span>
            </span>
          )}
          {order.discount_amount && (
            <span className="ml-2">
              {t('payment_ops.discount', { defaultValue: 'Sconto' })}:{' '}
              <span className="font-medium text-foreground">
                {fmtMoney(order.discount_amount, order.currency)}
              </span>
            </span>
          )}
        </div>
      )}

      {isPaidNotConfirmed && (
        <div className="rounded-md bg-red-50 border border-red-200 p-2 text-xs text-red-700 space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0" />
            <span className="font-semibold">{t('payment_ops.paid_not_confirmed')}</span>
          </div>
          {hasConfirmError && (
            <p className="ml-4 text-[11px] text-red-500">{t('payment_ops.error_label')}: {pc.confirm_error}</p>
          )}
          <Button
            size="sm"
            className="w-full gap-1.5 mt-1"
            onClick={() => onAction(order.id, 'confirm')}
          >
            <Check className="h-3.5 w-3.5" />
            {t('payment_ops.retry_confirm')}
          </Button>
          <p className="text-[11px] text-red-400 text-center">{t('payment_ops.retry_safe')}</p>
        </div>
      )}

      {isAwaitingPayment && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs text-blue-700">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shrink-0" />
            {t('payment_ops.awaiting_payment')}
          </div>
          {/* Fase 6a: manual pull fallback when the webhook is late/lost. */}
          {pc.reference && (
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-1.5 text-xs"
              onClick={() => onAction(order.id, 'verifyPayment')}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {t('payment_ops.verify_payment', { defaultValue: 'Verifica stato pagamento su Stripe' })}
            </Button>
          )}
        </div>
      )}

      {order.payment_intent === 'collected' && order.status !== 'draft' && (
        <div className="flex items-center gap-2 text-xs text-emerald-700">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {t('payment_ops.paid_confirmed')}
        </div>
      )}

      {(pc.reference || pc.stripe_payment_intent_id || pc.connected_account_id) && (
        <div className="text-[11px] text-muted-foreground space-y-0.5 border-t pt-1.5 mt-1.5">
          {pc.provider && <p>{t('payment_ops.ref_provider')}: <span className="font-medium">{pc.provider}</span></p>}
          {pc.reference && <p>{t('payment_ops.ref_session')}: <span className="font-mono">{pc.reference.slice(0, 24)}...</span></p>}
          {pc.stripe_payment_intent_id && (
            <p className="flex items-center gap-1">
              <span>{t('payment_ops.ref_payment_intent')}:</span>
              <span className="font-mono">{pc.stripe_payment_intent_id.slice(0, 24)}...</span>
              {dashboardUrl && (
                <a
                  href={dashboardUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-0.5 underline text-blue-600 ml-1"
                  title={t('payment_ops.open_in_stripe', { defaultValue: 'Apri in Stripe Dashboard' })}
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </p>
          )}
          {pc.connected_account_id && <p>{t('payment_ops.ref_account')}: <span className="font-mono">{pc.connected_account_id}</span></p>}
          {pc.completed_at && <p>{t('payment_ops.ref_completed')}: {pc.completed_at.slice(0, 19).replace('T', ' ')}</p>}
          {pc.url && isAwaitingPayment && (
            <p>{t('payment_ops.ref_link')}: <a href={pc.url} target="_blank" rel="noopener noreferrer" className="underline text-blue-600">{t('payment_ops.open_checkout')}</a></p>
          )}
        </div>
      )}

      {/* Webhook event trail — helps diagnose "why is this order not confirmed yet". */}
      {processedEvents.length > 0 && (
        <details className="text-[11px] text-muted-foreground border-t pt-1.5 mt-1.5">
          <summary className="cursor-pointer hover:text-foreground">
            {t('payment_ops.webhook_events', { defaultValue: 'Eventi webhook elaborati' })}
            <span className="ml-1 font-mono">({processedEvents.length})</span>
          </summary>
          <ul className="mt-1 space-y-0.5 pl-2">
            {processedEvents.map((eventId) => (
              <li key={eventId} className="font-mono text-[10px] truncate">
                {eventId}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/* ── Order Detail Panel (slide-over) ────────────────────────────────────────── */


// ── WS-1.2 consolidamento — scadenze pagamenti nel dettaglio ordine ─────────
// Prima lo schedule (caparra/saldo/rate) si vedeva SOLO nella dashboard del
// ritiro: chi apriva l'ordine dalla lista non vedeva nulla. Ora è qui, con
// le stesse azioni (segna pagato, proroga, condona, copia link pagamento).

function OrderScheduleSection({ order, t }) {
  const [schedule, setSchedule] = React.useState(null);
  const [events, setEvents] = React.useState([]);
  const [busy, setBusy] = React.useState(null);

  const load = React.useCallback(async () => {
    try {
      const res = await ordersAPI.getPaymentSchedule(order.id);
      setSchedule(res.data?.schedule || null);
      setEvents(res.data?.events || []);
    } catch { setSchedule(null); }
  }, [order.id]);

  React.useEffect(() => { load(); }, [load]);

  if (!schedule || (schedule.rows || []).length < 2) return null;

  const fmt = (m) => new Intl.NumberFormat('it-IT',
    { style: 'currency', currency: schedule.currency || 'EUR' }).format((m || 0) / 100);
  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('it-IT') : '';

  const act = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); await load(); }
    catch (err) { toast.error(err?.response?.data?.detail || t('toast.error')); }
    finally { setBusy(false); }
  };

  return (
    <div className="border-t pt-3">
      <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
        {t('schedule.title')}
      </p>
      <div className="space-y-1.5">
        {(schedule.rows || []).map(r => (
          <div key={r.seq} className="flex items-center justify-between gap-2 text-xs">
            <span className="text-gray-600">
              {r.label} · <span className="tabular-nums font-medium">{fmt(r.amount_minor)}</span>
              {' — '}
              <span className="font-semibold">{t(`schedule.status.${r.status}`, { defaultValue: r.status })}</span>
              {['pending', 'processing', 'overdue', 'at_risk'].includes(r.status)
                ? <span className="text-gray-400"> · {t('schedule.due', { date: fmtDate(r.due_at) })}</span>
                : r.paid_at
                  ? <span className="text-gray-400"> · {fmtDate(r.paid_at)}</span>
                  : null}
              {r.manual_note && <span className="text-gray-400"> · {r.manual_note}</span>}
            </span>
            {['pending', 'overdue', 'at_risk'].includes(r.status) && (
              <span className="shrink-0 flex gap-1">
                <button type="button" disabled={busy}
                  className="rounded border border-gray-300 px-1.5 py-0.5 text-[10px] hover:border-gray-900"
                  onClick={() => {
                    const note = window.prompt(t('settle.note_prompt'));
                    if (note && note.trim())
                      act(() => ordersAPI.markSchedulePaidManual(order.id, r.seq, note.trim()), t('settle.ok'));
                  }}>
                  {t('schedule.mark_paid')}
                </button>
                <button type="button" disabled={busy}
                  className="rounded border border-gray-300 px-1.5 py-0.5 text-[10px] hover:border-gray-900"
                  onClick={() => {
                    const d = window.prompt(t('schedule.postpone_prompt'));
                    if (d && /^\d{4}-\d{2}-\d{2}$/.test(d.trim()))
                      act(() => ordersAPI.postponeScheduleRow(order.id, r.seq, `${d.trim()}T12:00:00+00:00`), t('schedule.postpone_ok'));
                  }}>
                  {t('schedule.postpone')}
                </button>
                {r.pay_token && (
                  <button type="button" disabled={busy}
                    className="rounded border border-gray-300 px-1.5 py-0.5 text-[10px] hover:border-gray-900"
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/api/public/pay/${r.pay_token}`);
                      toast.success(t('schedule.link_copied'));
                    }}>
                    {t('schedule.copy_link')}
                  </button>
                )}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function OrderDetailPanel({ order, onClose, onAction, onEdit, onSettleManual, t }) {
  const navigate = useNavigate();
  if (!order) return null;

  const isClosed = order.status === 'completed' || order.status === 'cancelled';

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className={`fixed right-0 top-0 h-full w-full sm:w-[28rem] bg-card border-l z-50 overflow-y-auto shadow-xl ${isClosed ? 'opacity-95' : ''}`}>
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading text-lg font-semibold">{order.order_number || t('form.new_order')}</h3>
              {order.order_number && (
                <CopyButton value={order.order_number} title={t('detail.copy_order_number', { defaultValue: 'Copia numero ordine' })} />
              )}
              {sourceBadge(getSource(order), t)}
            </div>
            <button
              className="text-sm text-muted-foreground hover:text-primary hover:underline transition-colors text-left"
              onClick={() => { onClose(); navigate(`/modules/customers-light`); }}
              title={t('detail.view_customer', { defaultValue: 'View customer' })}
            >{order.customer_name}</button>
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <XIcon className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {/* ═══ SECTION 0: Customer contact (admin order management consolidation) ═══ */}
          <OrderCustomerCard order={order} t={t} />

          {/* ═══ SECTION 1: Status & Context ═══ */}
          <div className="space-y-2">
            {/* Status + payment row */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {statusBadge(order.status, t)}
                {paymentBadge(order.payment_status, t)}
              </div>
              <span className="text-xs text-muted-foreground">{order.order_date || '-'}</span>
            </div>

            {/* Review/urgency context — the most important signal */}
            {order.review_reason && order.review_state !== 'fulfilled_unpaid' && (
              <div className={`flex items-center gap-2 rounded-lg p-2 text-xs ${
                order.review_state === 'paid_needs_confirm' ? 'bg-red-50 border border-red-200 text-red-700' :
                order.review_state === 'needs_approval' || (order.review_state === 'needs_payment' && order.review_reason !== 'awaiting_payment')
                  ? 'bg-amber-50 border border-amber-200 text-amber-700'
                  : order.review_state === 'needs_review' ? 'bg-amber-50 border border-amber-200 text-amber-700'
                  : 'bg-blue-50 border border-blue-200 text-blue-700'
              }`}>
                {order.review_state === 'paid_needs_confirm' ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> :
                 order.review_state === 'needs_approval' ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> :
                 <Clock className="h-3.5 w-3.5 shrink-0" />}
                <span>{t(`review.${order.review_reason}`, { defaultValue: order.review_reason })}</span>
              </div>
            )}

            {/* Fulfilled but unpaid — prompt (Modulo 5) */}
            {order.review_state === 'fulfilled_unpaid' && (
              <div className="flex items-center justify-between gap-2 rounded-lg p-2.5 text-xs bg-amber-50 border border-amber-200 text-amber-700">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  <span>{t('review.delivered_not_paid')}</span>
                </div>
                {(order.actions?.mark_paid?.allowed) && (
                  <Button size="sm" className="h-6 text-[11px] gap-1 px-2 bg-amber-600 hover:bg-amber-700"
                    onClick={() => onAction(order.id, 'markPaid')}>
                    {t('detail.mark_paid_inline')}
                  </Button>
                )}
              </div>
            )}

            {/* Payment toggle (Modulo 4) */}
            {(order.actions?.mark_paid?.allowed || order.actions?.mark_unpaid?.allowed) && !order.review_state?.startsWith('fulfilled') && (
              <div className="flex items-center gap-2">
                {order.actions?.mark_paid?.allowed && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-xs text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                    onClick={() => onAction(order.id, 'markPaid')}>
                    <CheckCircle2 className="h-3.5 w-3.5" /> {t('actions.mark_paid')}
                  </Button>
                )}
                {order.actions?.mark_unpaid?.allowed && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-xs text-amber-600 border-amber-200 hover:bg-amber-50"
                    onClick={() => onAction(order.id, 'markUnpaid')}>
                    <Clock className="h-3.5 w-3.5" /> {t('actions.mark_unpaid')}
                  </Button>
                )}
              </div>
            )}

            {/* Payment operations (inline in context, not a separate section) */}
            {order.payment_intent && order.payment_intent !== 'none' && (
              <>
                <PaymentOpsSection order={order} onAction={onAction} />
                <OrderScheduleSection order={order} t={t} />
              </>
            )}
          </div>

          {/* ═══ SECTION 2: Actions (before content — decide, then review details) ═══ */}
          {(() => {
            const a = order.actions || {};
            const anyAction = a.confirm?.allowed || a.complete?.allowed || a.cancel?.allowed || a.edit?.allowed || a.settle_manual?.allowed;
            if (!anyAction) return null;
            return (
              <div className="border-t border-b py-3 space-y-2">
                {a.confirm?.allowed && (
                  <>
                    <Button size="sm" className="w-full gap-2" onClick={() => onAction(order.id, 'confirm')}>
                      <Check className="h-4 w-4" /> {t('actions.confirm')}
                    </Button>
                    {a.confirm?.warn_text && <p className="text-[11px] text-muted-foreground text-center">{t(`action_confirm.${a.confirm.warn_text}`, { defaultValue: a.confirm.warn_text })}</p>}
                  </>
                )}
                {a.settle_manual?.allowed && (
                  <>
                    <Button size="sm" variant="outline"
                      className="w-full gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                      onClick={() => onSettleManual(order)}>
                      <Check className="h-4 w-4" /> {t('actions.settle_manual')}
                    </Button>
                    <p className="text-[11px] text-muted-foreground text-center">
                      {t('actions.settle_manual_hint')}
                    </p>
                  </>
                )}
                {a.complete?.allowed && (
                  <Button size="sm" className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => onAction(order.id, 'complete')}>
                    <CheckCircle2 className="h-4 w-4" /> {t('actions.complete')}
                  </Button>
                )}
                <div className="flex gap-2">
                  {a.edit?.allowed && (
                    <Button variant="outline" size="sm" className="flex-1 gap-1" onClick={() => onEdit(order)}>
                      <Clock className="h-3.5 w-3.5" /> {t('actions.edit')}
                    </Button>
                  )}
                  {a.cancel?.allowed && (
                    <Button variant="outline" size="sm"
                      className={`flex-1 gap-1 ${a.cancel.severity === 'danger' ? 'text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200' : 'text-red-600 hover:text-red-700 hover:bg-red-50'}`}
                      onClick={() => onAction(order.id, 'cancel')}>
                      <Ban className="h-3.5 w-3.5" /> {t('actions.cancel')}
                    </Button>
                  )}
                </div>
                {a.cancel?.warn_text && (
                  <p className={`text-[11px] text-center ${a.cancel.severity === 'danger' ? 'text-red-500' : 'text-muted-foreground'}`}>{t(`action_confirm.${a.cancel.warn_text}`, { defaultValue: a.cancel.warn_text })}</p>
                )}
              </div>
            );
          })()}

          {/* ═══ SECTION 2b: Fulfillment (v10.0) ═══ */}
          {(() => {
            const ff = order.fulfillment;
            if (!ff || ff.mode === 'not_required') return null;
            const ffActions = order.fulfillment_actions || {};
            const hasAnyFfAction = Object.values(ffActions).some(a => a?.allowed);
            const FF_STATUS_BADGE = {
              pending: { label: t('fulfillment.status_pending'), className: 'bg-amber-100 text-amber-700' },
              shipped: { label: t('fulfillment.status_shipped'), className: 'bg-blue-100 text-blue-700' },
              delivered: { label: t('fulfillment.status_delivered'), className: 'bg-emerald-100 text-emerald-700' },
              ready_for_pickup: { label: t('fulfillment.status_ready_for_pickup'), className: 'bg-indigo-100 text-indigo-700' },
              picked_up: { label: t('fulfillment.status_picked_up'), className: 'bg-emerald-100 text-emerald-700' },
              fulfilled: { label: t('fulfillment.status_fulfilled'), className: 'bg-emerald-100 text-emerald-700' },
            };
            const badge = FF_STATUS_BADGE[ff.status] || FF_STATUS_BADGE.pending;
            const MODE_ICON = { shipping: Truck, local_pickup: MapPin, manual_arrangement: Package };
            const ModeIcon = MODE_ICON[ff.mode] || Package;
            return (
              <div className="border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <ModeIcon className="h-4 w-4 text-muted-foreground" />
                    {t(`fulfillment.mode_${ff.mode}`)}
                  </div>
                  <Badge className={`text-[10px] ${badge.className}`}>{badge.label}</Badge>
                </div>
                {/* Shipping address — structured when present (modern orders),
                    flattened string otherwise (legacy / external clients). */}
                {ff.shipping_address_details ? (() => {
                  const d = ff.shipping_address_details;
                  const streetLine = [d.line1, d.civic].filter(Boolean).join(' ');
                  const cityLine = [d.postal_code, d.city, d.province ? `(${d.province})` : null]
                    .filter(Boolean).join(' ');
                  const country = d.country && d.country !== 'IT' ? d.country : null;
                  return (
                    <div className="text-xs text-muted-foreground space-y-0">
                      <p className="font-medium">{t('fulfillment.address')}:</p>
                      {d.recipient_name && <p className="pl-3">{d.recipient_name}</p>}
                      {streetLine && <p className="pl-3">{streetLine}</p>}
                      {cityLine && <p className="pl-3">{cityLine}</p>}
                      {country && <p className="pl-3">{country}</p>}
                    </div>
                  );
                })() : ff.shipping_address ? (
                  <p className="text-xs text-muted-foreground">{t('fulfillment.address')}: {ff.shipping_address}</p>
                ) : null}
                {/* Shipping option snapshot — rendered only when the order
                    was placed with an explicit option. Legacy orders have
                    no shipping_option_label and this row is suppressed. */}
                {ff.shipping_option_label && (
                  <p className="text-xs text-muted-foreground flex items-center gap-1 flex-wrap">
                    <Truck className="h-3 w-3" />
                    <span>
                      {t('fulfillment.shipping_label', { defaultValue: 'Spedizione' })}:
                      {' '}{ff.shipping_option_label}
                    </span>
                    <span className="font-medium tabular-nums">
                      {Number(ff.shipping_cost || 0) > 0
                        ? `— ${fmtMoney(ff.shipping_cost, order.currency)}`
                        : <span className="text-green-700 font-semibold">— GRATIS</span>}
                    </span>
                  </p>
                )}
                {ff.fulfillment_notes && (
                  <p className="text-xs text-muted-foreground">{t('fulfillment.notes')}: {ff.fulfillment_notes}</p>
                )}
                {ff.shipped_at && <p className="text-xs text-muted-foreground">{t('fulfillment.shipped_at')}: {ff.shipped_at.slice(0, 10)}</p>}
                {ff.delivered_at && <p className="text-xs text-muted-foreground">{t('fulfillment.delivered_at')}: {ff.delivered_at.slice(0, 10)}</p>}
                {(ff.tracking_number || ff.tracking_url) && (
                  <p className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1">
                      <Truck className="h-3 w-3" />
                      {t('fulfillment.tracking_number_label', { defaultValue: 'Codice tracking' })}:
                    </span>
                    {ff.tracking_number && <span className="font-mono tabular-nums">{ff.tracking_number}</span>}
                    {ff.tracking_url && (
                      <a
                        href={ff.tracking_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {t('fulfillment.tracking_open_link', { defaultValue: 'Traccia il pacco' })}
                      </a>
                    )}
                  </p>
                )}
                {hasAnyFfAction && (
                  <div className="flex gap-2 pt-1">
                    {ffActions.mark_shipped?.allowed && (
                      <Button size="sm" variant="outline" className="flex-1 gap-1 text-xs" onClick={() => onAction(order.id, 'fulfillment', 'shipped')}>
                        <Truck className="h-3 w-3" /> {t('fulfillment.action_ship')}
                      </Button>
                    )}
                    {ffActions.mark_delivered?.allowed && (
                      <Button size="sm" variant="outline" className="flex-1 gap-1 text-xs" onClick={() => onAction(order.id, 'fulfillment', 'delivered')}>
                        <CheckCircle2 className="h-3 w-3" /> {t('fulfillment.action_deliver')}
                      </Button>
                    )}
                    {ffActions.mark_ready_for_pickup?.allowed && (
                      <Button size="sm" variant="outline" className="flex-1 gap-1 text-xs" onClick={() => onAction(order.id, 'fulfillment', 'ready_for_pickup')}>
                        <MapPin className="h-3 w-3" /> {t('fulfillment.action_ready')}
                      </Button>
                    )}
                    {ffActions.mark_picked_up?.allowed && (
                      <Button size="sm" variant="outline" className="flex-1 gap-1 text-xs" onClick={() => onAction(order.id, 'fulfillment', 'picked_up')}>
                        <CheckCircle2 className="h-3 w-3" /> {t('fulfillment.action_picked_up')}
                      </Button>
                    )}
                    {ffActions.mark_fulfilled?.allowed && (
                      <Button size="sm" variant="outline" className="flex-1 gap-1 text-xs" onClick={() => onAction(order.id, 'fulfillment', 'fulfilled')}>
                        <CheckCircle2 className="h-3 w-3" /> {t('fulfillment.action_fulfilled')}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Closed state */}
          {isClosed && (
            <div className={`text-center text-xs py-2 ${order.status === 'completed' ? 'text-emerald-600' : 'text-muted-foreground'}`}>
              {order.status === 'completed' ? t('detail.completed_note') : t('detail.cancelled_note')}
            </div>
          )}

          {/* ═══ Shipping Address Card (Modulo 3) ═══ */}
          {order.fulfillment?.mode === 'shipping' && (order.fulfillment?.shipping_address || order.fulfillment?.shipping_address_details || order.contact_phone) && (
            <div className={`rounded-lg border p-3 space-y-1.5 ${
              order.fulfillment?.status === 'pending' ? 'border-amber-200 bg-amber-50/50' : 'border-gray-200'
            }`}>
              <div className="flex items-center gap-2 text-sm font-medium">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                {t('fulfillment.shipping_destination')}
                {order.fulfillment?.status === 'pending' && (
                  <Badge className="text-[10px] bg-amber-100 text-amber-700">{t('fulfillment.to_ship')}</Badge>
                )}
              </div>
              {/* Prefer structured rendering (multi-line, carrier-friendly).
                  Fall back to the legacy flattened string for pre-release
                  orders. */}
              {order.fulfillment?.shipping_address_details ? (() => {
                const d = order.fulfillment.shipping_address_details;
                const streetLine = [d.line1, d.civic].filter(Boolean).join(' ');
                const cityLine = [d.postal_code, d.city, d.province ? `(${d.province})` : null]
                  .filter(Boolean).join(' ');
                const country = d.country && d.country !== 'IT' ? d.country : null;
                return (
                  <div className="text-sm pl-6 space-y-0 leading-tight">
                    {d.recipient_name && <p className="font-medium">{d.recipient_name}</p>}
                    {streetLine && <p>{streetLine}</p>}
                    {cityLine && <p>{cityLine}</p>}
                    {country && <p className="text-xs text-muted-foreground">{country}</p>}
                  </div>
                );
              })() : order.fulfillment?.shipping_address ? (
                <p className="text-sm pl-6">{order.fulfillment.shipping_address}</p>
              ) : null}
              {order.contact_phone && (
                <p className="text-xs text-muted-foreground pl-6">📞 {order.contact_phone}</p>
              )}
            </div>
          )}

          {/* ═══ SECTION 3: Content & Details ═══ */}
          {/* Composition note */}
          {order.composition?.message && (
            <div className="flex items-center gap-2 rounded-lg bg-gray-50 border border-gray-200 p-2 text-xs text-gray-600">
              <span>{order.composition.message}</span>
            </div>
          )}

          {order.notes && (
            <div className="text-sm">
              <span className="text-muted-foreground">{t('form.notes')}</span>
              <p>{order.notes}</p>
            </div>
          )}

          {/* Custom checkout fields (F2 Onda 9) */}
          <OrderFieldsSection order={order} t={t} />

          {/* Line items */}
          <div>
            <h4 className="text-sm font-semibold mb-2">{t('form.items')}</h4>
            <div className="space-y-2">
              {(order.items || []).map((item, i) => (
                <OrderLineItem key={i} item={item} t={t} />
              ))}
            </div>
          </div>

          {/* Issued entities (tickets / bookings / reservations) */}
          <IssuedEntitiesSection orderId={order.id} orderStatus={order.status} t={t} />

          {/* Total */}
          <div className="flex justify-between items-center border-t pt-3">
            <span className="font-semibold">{t('form.total')}</span>
            <span className="text-lg font-bold">{fmtMoney(order.total, order.currency)}</span>
          </div>

          {/* Download receipt */}
          {(order.status === 'confirmed' || order.status === 'completed') && (
            <button
              onClick={async () => {
                try {
                  const res = await ordersAPI.downloadReceipt(order.id);
                  const url = window.URL.createObjectURL(new Blob([res.data]));
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `ricevuta_${order.order_number || order.id.slice(0,8)}.pdf`;
                  a.click();
                  window.URL.revokeObjectURL(url);
                } catch { /* empty */ }
              }}
              className="w-full text-center text-xs text-primary hover:underline py-2"
            >
              {t('detail.download_receipt')}
            </button>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────────────── */

export default function OrdersPage() {
  const { t } = useTranslation('orders');
  const navigate = useNavigate();
  const { getMetric } = useEntitlements();
  const ordersMonthlyMetric = getMetric('orders_monthly');
  const [searchParams, setSearchParams] = useSearchParams();
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [pendingReselect, setPendingReselect] = useState(null);
  const [prefillCustomerId, setPrefillCustomerId] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterSource, setFilterSource] = useState('all');
  const [filterPayment, setFilterPayment] = useState('all');
  const [filterReview, setFilterReview] = useState('all');
  const [filterItemType, setFilterItemType] = useState('all');  // all | event_ticket | service | rental | physical
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');  // YYYY-MM-DD
  const [filterDateTo, setFilterDateTo] = useState('');      // YYYY-MM-DD
  const [datePreset, setDatePreset] = useState('');          // '7d' | '30d' | 'thismonth' | 'custom'
  const [filterCustomerId, setFilterCustomerId] = useState(null);
  const [triageContext, setTriageContext] = useState(null); // 'drafts' | 'review' | 'fulfillment' | null
  // D2 (4/7/2026) — i filtri secondari vivono in un pannello collassabile:
  // sopra la tabella resta UNA riga (chips vita + ricerca + Filtri).
  const [advancedOpen, setAdvancedOpen] = useState(false);
  // Release 1 (Physical) — tracking capture dialog, opened on mark_shipped
  // instead of dispatching the fulfillment PATCH directly.
  const [trackingDialog, setTrackingDialog] = useState(null); // { orderId, orderRef } | null
  const [trackingSubmitting, setTrackingSubmitting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // Handle filter_customer URL param (from customer profile deep-link)
  useEffect(() => {
    const cid = searchParams.get('filter_customer');
    if (cid && !loading) {
      setFilterCustomerId(cid);
      searchParams.delete('filter_customer');
      setSearchParams(searchParams, { replace: true });
    }
  }, [loading, searchParams, setSearchParams]);

  // Handle selected URL param (deep-link to a specific order, e.g. from
  // ReservationsDashboard "Apri ordine"). Opens the detail panel as soon as
  // the orders list has loaded.
  useEffect(() => {
    const sid = searchParams.get('selected');
    if (!sid || loading) return;
    const target = orders.find(o => o.id === sid);
    if (target) {
      setSelectedOrder(target);
    }
    searchParams.delete('selected');
    setSearchParams(searchParams, { replace: true });
  }, [loading, orders, searchParams, setSearchParams]);

  // Fase 2 Track F — Setup Wizard deep-link: ?action=import opens the
  // OrderImportDialog directly so the user lands one click away from
  // their CSV. Pure additive: no param → no behaviour change.
  useEffect(() => {
    if (searchParams.get('action') !== 'import') return;
    setImportOpen(true);
    searchParams.delete('action');
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Handle dashboard triage params: ?status=draft, ?triage=review|fulfillment
  useEffect(() => {
    let changed = false;
    const statusParam = searchParams.get('status');
    const triageParam = searchParams.get('triage');

    if (statusParam && !loading && ['draft', 'confirmed', 'completed', 'cancelled'].includes(statusParam)) {
      setFilterStatus(statusParam);
      setTriageContext(statusParam === 'draft' ? 'drafts' : null);
      searchParams.delete('status');
      changed = true;
    }
    if (triageParam && !loading) {
      if (triageParam === 'review') {
        setFilterReview('any');
        setTriageContext('review');
      } else if (triageParam === 'fulfillment') {
        setTriageContext('fulfillment');
      } else if (triageParam === 'paid_unconfirmed') {
        setTriageContext('paid_unconfirmed');
      }
      searchParams.delete('triage');
      changed = true;
    }
    if (changed) setSearchParams(searchParams, { replace: true });
  }, [loading, searchParams, setSearchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredOrders = useMemo(() => {
    let list = orders;
    if (filterCustomerId) list = list.filter(o => o.customer_id === filterCustomerId);
    if (filterStatus === 'active') list = list.filter(o => o.status === 'draft' || o.status === 'confirmed');
    else if (filterStatus !== 'all') list = list.filter(o => o.status === filterStatus);
    if (filterSource === 'storefront') list = list.filter(o => o.source?.startsWith('storefront'));
    else if (filterSource === 'manual') list = list.filter(o => !o.source?.startsWith('storefront'));
    if (filterPayment === 'needs_attention') list = list.filter(o => o.payment_intent === 'collected' && o.status === 'draft');
    else if (filterPayment === 'awaiting') list = list.filter(o => o.payment_intent === 'required' && o.status === 'draft');
    else if (filterPayment === 'collected') list = list.filter(o => o.payment_intent === 'collected');
    if (filterReview === 'needs_approval') list = list.filter(o => o.review_state === 'needs_approval');
    else if (filterReview === 'needs_review') list = list.filter(o => o.review_state === 'needs_review' || o.review_state === 'needs_approval');
    else if (filterReview === 'any') list = list.filter(o => o.review_state);
    // Onda 14 — item type filter: match if at least one line is of the selected type.
    // 'physical' also matches lines with undefined item_type (legacy pre-typed orders).
    if (filterItemType !== 'all') {
      list = list.filter(o => (o.items || []).some(it => {
        const t = it.item_type || 'physical';
        return t === filterItemType;
      }));
    }
    // Onda 14 — text search across order_number, customer_name, customer_email.
    // Client-side substring match, case-insensitive.
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      list = list.filter(o => (
        (o.order_number || '').toLowerCase().includes(q) ||
        (o.customer_name || '').toLowerCase().includes(q) ||
        (o.customer_email || '').toLowerCase().includes(q) ||
        (o.id || '').toLowerCase().includes(q)
      ));
    }
    // Onda 14 — date range filter on order_date. ISO lexicographic
    // comparison is equivalent to temporal ordering for YYYY-MM-DD.
    // Order date falls back to created_at's date portion when missing.
    if (filterDateFrom || filterDateTo) {
      list = list.filter(o => {
        const d = o.order_date || (o.created_at ? o.created_at.slice(0, 10) : '');
        if (!d) return false;
        if (filterDateFrom && d < filterDateFrom) return false;
        if (filterDateTo && d > filterDateTo) return false;
        return true;
      });
    }
    // Triage: fulfillment pending (precise filter)
    if (triageContext === 'fulfillment') {
      list = list.filter(o =>
        o.status === 'confirmed' &&
        o.fulfillment?.mode && o.fulfillment.mode !== 'not_required' &&
        o.fulfillment?.status === 'pending'
      );
    }
    // Triage: paid but unconfirmed (precise filter)
    if (triageContext === 'paid_unconfirmed') {
      list = list.filter(o => o.status === 'draft' && o.payment_intent === 'collected');
    }
    return list;
  }, [orders, filterStatus, filterSource, filterPayment, filterReview, filterItemType, searchQuery, filterDateFrom, filterDateTo, triageContext, filterCustomerId]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ordRes, custRes, prodRes] = await Promise.all([
        ordersAPI.list(),
        customersAPI.list(true),
        productsAPI.list(true),
      ]);
      setOrders(ordRes.data?.orders || []);
      setCustomers(custRes.data || []);
      setProducts(prodRes.data || []);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Re-select order after action-triggered reload (keeps panel open with fresh data)
  useEffect(() => {
    if (pendingReselect && !loading && orders.length > 0) {
      const fresh = orders.find(o => o.id === pendingReselect);
      if (fresh) setSelectedOrder(fresh);
      setPendingReselect(null);
    }
  }, [pendingReselect, loading, orders]);

  // Auto-select order from URL param (calendar deep-link)
  useEffect(() => {
    const oid = searchParams.get('order_id');
    if (oid && !loading && orders.length > 0) {
      const order = orders.find(o => o.id === oid);
      if (order) setSelectedOrder(order);
      searchParams.delete('order_id');
      setSearchParams(searchParams, { replace: true });
    }
  }, [loading, orders, searchParams, setSearchParams]);

  // Auto-open new order dialog with pre-selected customer from URL param
  useEffect(() => {
    const cid = searchParams.get('customer_id');
    if (cid && !loading && customers.length > 0) {
      const exists = customers.find(c => c.id === cid);
      if (exists) {
        setPrefillCustomerId(cid);
        setEditing(null);
        setDialogOpen(true);
      }
      // Clear the param so refresh doesn't re-trigger
      searchParams.delete('customer_id');
      setSearchParams(searchParams, { replace: true });
    }
  }, [loading, customers, searchParams, setSearchParams]);

  const handleSettleManual = async (order) => {
    // Il caso bonifico: scope caparra o tutto, nota obbligatoria.
    const hasSchedule = !!order.payment_state || undefined;
    let scope = 'full';
    if (window.confirm(t('settle.scope_question'))) {
      scope = 'deposit';
    }
    const note = window.prompt(t('settle.note_prompt'));
    if (!note || !note.trim()) return;
    try {
      await ordersAPI.settleManual(order.id, note.trim(), scope);
      toast.success(t('settle.ok'));
      setSelectedOrder(null);
      await load();
      setPendingReselect(order.id);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    }
  };

  const handleAction = async (orderId, action, ffStatus) => {
    // Fulfillment action (v10.0)
    if (action === 'fulfillment' && ffStatus) {
      // Release 1 (Physical) — intercept mark_shipped to prompt for tracking.
      // Other transitions keep the original confirm() flow.
      if (ffStatus === 'shipped') {
        const match = orders.find(o => o.id === orderId);
        const ref = match?.order_number || String(orderId).slice(0, 12);
        setTrackingDialog({ orderId, orderRef: ref });
        return;
      }
      const confirmText = t(`fulfillment.confirm_${ffStatus}`, { defaultValue: t('fulfillment.confirm_default') });
      if (!window.confirm(confirmText)) return;
      try {
        await ordersAPI.updateFulfillment(orderId, ffStatus);
        toast.success(t('fulfillment.toast_updated'));
        setSelectedOrder(null);
        setPendingReselect(orderId);
        await load();
      } catch (err) {
        toast.error(err?.response?.data?.detail || t('toast.error'));
      }
      return;
    }

    // Fase 6a: pull payment state from Stripe for a stuck order.
    // Idempotent, no confirm dialog — just a read+maybe-reconcile.
    if (action === 'verifyPayment') {
      try {
        const res = await ordersAPI.verifyPayment(orderId);
        const data = res.data || {};
        const msgMap = {
          reconciled: t('payment_ops.toast_verify_reconciled', {
            number: data.order_number,
            defaultValue: `Pagamento confermato. Ordine ${data.order_number || ''}.`,
          }),
          already_reconciled: t('payment_ops.toast_verify_already', {
            defaultValue: 'Ordine già confermato.',
          }),
          still_unpaid: t('payment_ops.toast_verify_unpaid', {
            defaultValue: 'Stripe segnala il pagamento non ancora ricevuto.',
          }),
          session_not_found: t('payment_ops.toast_verify_no_session', {
            defaultValue: 'Nessuna sessione Stripe associata all\'ordine.',
          }),
        };
        const message = msgMap[data.status] || t('payment_ops.toast_verify_generic', {
          defaultValue: 'Verifica completata.',
        });
        if (data.status === 'reconciled' || data.status === 'already_reconciled') {
          toast.success(message);
        } else {
          toast.info(message);
        }
        setPendingReselect(orderId);
        await load();
      } catch (err) {
        toast.error(err?.response?.data?.detail || t('toast.error'));
      }
      return;
    }

    // Policy-driven confirmation: use confirm_text from backend action policy
    const order = orders.find(o => o.id === orderId);
    // Map camelCase action names to snake_case policy keys
    const policyKey = { markPaid: 'mark_paid', markUnpaid: 'mark_unpaid' }[action] || action;
    const actionPolicy = order?.actions?.[policyKey];
    const confirmCode = actionPolicy?.confirm_text;
    const confirmText = confirmCode ? t(`action_confirm.${confirmCode}`, { defaultValue: confirmCode }) : t(`actions.${action}_dialog`);
    if (!window.confirm(confirmText)) return;
    try {
      const res = await ordersAPI[action](orderId);
      if (action === 'markPaid') {
        toast.success(t('toast.marked_paid'));
      } else if (action === 'markUnpaid') {
        toast.success(t('toast.marked_unpaid'));
      } else if (action === 'confirm') {
        const order = res.data;
        const lineCount = order?.items?.length || 0;
        toast.success(
          t('toast.confirmed_detail', {
            number: order?.order_number || '',
            count: lineCount,
            defaultValue: `Ordine ${order?.order_number} confermato — ${lineCount} registrazioni cashflow generate`,
          })
        );
      } else if (action === 'cancel') {
        toast.success(t('toast.cancelled'));
      } else {
        toast.success(t('toast.completed'));
      }
      // Reload and keep panel open with fresh data
      setEditing(null);
      setPrefillCustomerId(null);
      setSelectedOrder(null);
      await load();
      // Re-select the order to refresh panel with updated data (panel stays open)
      setPendingReselect(orderId);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    }
  };

  const openEdit = (order) => {
    if (order.status !== 'draft') return;
    setEditing(order);
    setDialogOpen(true);
  };

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={load}
              className="gap-1 shrink-0"
              aria-label={t('actions.refresh', { defaultValue: 'Refresh' })}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setImportOpen(true)}
              className="gap-1.5"
            >
              <Upload className="h-4 w-4" />
              <span className="hidden sm:inline">{t('actions.import')}</span>
            </Button>
            <Button
              size="sm"
              onClick={() => { setEditing(null); setDialogOpen(true); }}
              className="gap-1.5"
            >
              <Plus className="h-4 w-4" />
              <span>{t('actions.create')}</span>
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 max-w-7xl mx-auto">
        {/* Onda 10 Step F.2 — orders_monthly quota progress (self-hides
            below 60% and on unlimited plans). */}
        {ordersMonthlyMetric && (
          <QuotaProgressBanner
            metric="orders_monthly"
            used={ordersMonthlyMetric.used || 0}
            limit={ordersMonthlyMetric.limit ?? 0}
            addonSlug={ordersMonthlyMetric.addon_slug}
            onUpgradeClick={() => navigate('/billing')}
            className="mb-4"
          />
        )}
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <ShoppingCart className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <h3 className="font-semibold">{t('list.empty')}</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md">{t('list.empty_desc')}</p>
            <Button className="mt-4" onClick={() => { setEditing(null); setDialogOpen(true); }}>
              <Plus className="h-4 w-4 mr-2" />{t('actions.create')}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Customer filter banner */}
            {filterCustomerId && (() => {
              const cust = customers.find(c => c.id === filterCustomerId);
              return (
                <div className="flex items-center justify-between rounded-lg border bg-blue-50 border-blue-200 px-3 py-2 text-xs text-blue-700">
                  <span>{t('filter.by_customer', { name: cust?.name || filterCustomerId.slice(0, 8) })}</span>
                  <button onClick={() => setFilterCustomerId(null)} className="ml-2 underline hover:no-underline">{t('filter.clear')}</button>
                </div>
              );
            })()}

            {/* Triage context banner — shown when arriving from dashboard signal */}
            {triageContext && (
              <div className="flex items-center justify-between rounded-lg border px-3 py-2 text-xs bg-primary/5 border-primary/20">
                <span className="text-primary font-medium">
                  {triageContext === 'drafts' && t('triage.banner_drafts', { defaultValue: 'Ordini in bozza' })}
                  {triageContext === 'review' && t('triage.banner_review', { defaultValue: 'Ordini da gestire' })}
                  {triageContext === 'fulfillment' && t('triage.banner_fulfillment', { defaultValue: 'Consegne in attesa' })}
                  {triageContext === 'paid_unconfirmed' && t('triage.banner_paid_unconfirmed', { defaultValue: 'Ordini pagati da confermare' })}
                </span>
                <button
                  onClick={() => { setTriageContext(null); setFilterStatus('all'); setFilterReview('all'); }}
                  className="text-muted-foreground hover:text-foreground ml-2"
                >
                  &times;
                </button>
              </div>
            )}

            {/* D2 (4/7/2026) — UNA riga di controllo: chips vita + ricerca +
                Filtri. Tutti i filtri secondari (stato fine, tipo, periodo,
                canale, pagamento) vivono nel pannello collassabile sotto:
                niente piu' 7 file di controlli ridondanti sopra la tabella. */}
            {(() => {
              const attention = orders.filter(o => o.review_state).length;
              const advancedActive = [
                filterStatus !== 'all' && filterStatus !== 'active',
                filterItemType !== 'all',
                filterSource !== 'all',
                filterPayment !== 'all',
                Boolean(filterDateFrom || filterDateTo),
              ].filter(Boolean).length;
              const anyFilter = advancedActive > 0 || filterStatus !== 'all' || filterReview !== 'all' || searchQuery;
              const chipCls = (active, tone) => `flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground border-primary'
                  : tone === 'warn'
                    ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                    : 'bg-card text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`;
              const resetLife = () => { setFilterReview('all'); setTriageContext(null); };
              return (
                <div className="flex flex-wrap items-center gap-2">
                  {attention > 0 && (
                    <button
                      onClick={() => { resetLife(); setFilterReview('any'); setFilterStatus('all'); }}
                      className={chipCls(filterReview === 'any', 'warn')}
                    >
                      {t('queue.needs_action')}
                      <span className="font-bold">{attention}</span>
                    </button>
                  )}
                  <button
                    onClick={() => { resetLife(); setFilterStatus('active'); }}
                    className={chipCls(filterStatus === 'active' && filterReview !== 'any')}
                  >
                    {t('filter.life_active', { defaultValue: 'In corso' })}
                  </button>
                  <button
                    onClick={() => { resetLife(); setFilterStatus('all'); }}
                    className={chipCls(filterStatus === 'all' && filterReview !== 'any' && advancedActive === 0)}
                  >
                    {t('list.filter_all')}
                  </button>

                  <div className="relative flex-1 min-w-[180px] max-w-xs">
                    <input
                      type="text"
                      placeholder={t('list.search_placeholder', { defaultValue: 'Cerca ordine o cliente…' })}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="h-8 w-full pl-2.5 pr-7 rounded-full border bg-card text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-sm leading-none"
                      >×</button>
                    )}
                  </div>

                  <button
                    onClick={() => setAdvancedOpen(v => !v)}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      advancedOpen || advancedActive > 0
                        ? 'border-primary/40 bg-primary/5 text-primary'
                        : 'bg-card text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {t('filter.advanced', { defaultValue: 'Filtri' })}
                    {advancedActive > 0 && (
                      <span className="rounded-full bg-primary text-primary-foreground px-1.5 text-[10px] font-bold">{advancedActive}</span>
                    )}
                  </button>

                  {anyFilter && (
                    <span className="text-xs text-muted-foreground">{filteredOrders.length} / {orders.length}</span>
                  )}
                </div>
              );
            })()}

            {/* Pannello filtri avanzati — collassabile, righe etichettate */}
            {advancedOpen && (
              <div className="rounded-xl border bg-card p-3 space-y-2.5 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-20 text-muted-foreground">{t('filter.label_status', { defaultValue: 'Stato' })}</span>
                  {['all', 'draft', 'confirmed', 'completed', 'cancelled'].map(v => (
                    <button key={v} onClick={() => setFilterStatus(v)}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                        filterStatus === v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                      }`}>
                      {v === 'all' ? t('list.filter_all') : t(`status.${v}`)}
                    </button>
                  ))}
                </div>

                {(() => {
                  const typesPresent = new Set();
                  orders.forEach(o => (o.items || []).forEach(it => typesPresent.add(it.item_type || 'physical')));
                  if (typesPresent.size <= 1) return null;
                  const TYPE_LABELS = {
                    event_ticket: t('filter.type_events', { defaultValue: 'Ritiri' }),
                    service: t('filter.type_services', { defaultValue: 'Servizi' }),
                    rental: t('filter.type_rentals', { defaultValue: 'Noleggi' }),
                    booking: t('filter.type_bookings', { defaultValue: 'Prenotazioni' }),
                    physical: t('filter.type_physical', { defaultValue: 'Prodotti' }),
                  };
                  const order = ['all', 'event_ticket', 'service', 'rental', 'booking', 'physical'];
                  return (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="w-20 text-muted-foreground">{t('filter.label_type', { defaultValue: 'Tipo' })}</span>
                      {order.filter(v => v === 'all' || typesPresent.has(v)).map(v => (
                        <button key={v} onClick={() => setFilterItemType(v)}
                          className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                            filterItemType === v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                          }`}>
                          {v === 'all' ? t('list.filter_all') : TYPE_LABELS[v]}
                        </button>
                      ))}
                    </div>
                  );
                })()}

                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-20 text-muted-foreground">{t('filter.label_period', { defaultValue: 'Periodo' })}</span>
                  {(() => {
                    const today = new Date();
                    const toISO = (d) => {
                      const y = d.getFullYear();
                      const m = String(d.getMonth() + 1).padStart(2, '0');
                      const dd = String(d.getDate()).padStart(2, '0');
                      return `${y}-${m}-${dd}`;
                    };
                    const applyPreset = (preset) => {
                      setDatePreset(preset);
                      if (preset === '') { setFilterDateFrom(''); setFilterDateTo(''); return; }
                      if (preset === 'today') { const iso = toISO(today); setFilterDateFrom(iso); setFilterDateTo(iso); return; }
                      if (preset === '7d') { const from = new Date(today); from.setDate(from.getDate() - 6); setFilterDateFrom(toISO(from)); setFilterDateTo(toISO(today)); return; }
                      if (preset === '30d') { const from = new Date(today); from.setDate(from.getDate() - 29); setFilterDateFrom(toISO(from)); setFilterDateTo(toISO(today)); return; }
                      if (preset === 'thismonth') { const from = new Date(today.getFullYear(), today.getMonth(), 1); setFilterDateFrom(toISO(from)); setFilterDateTo(toISO(today)); return; }
                    };
                    const PRESETS = [
                      { key: '', label: t('filter.date_all', { defaultValue: 'Sempre' }) },
                      { key: 'today', label: t('filter.date_today', { defaultValue: 'Oggi' }) },
                      { key: '7d', label: t('filter.date_7d', { defaultValue: '7gg' }) },
                      { key: '30d', label: t('filter.date_30d', { defaultValue: '30gg' }) },
                      { key: 'thismonth', label: t('filter.date_thismonth', { defaultValue: 'Mese' }) },
                    ];
                    return PRESETS.map(p => (
                      <button key={p.key || 'all'} onClick={() => applyPreset(p.key)}
                        className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                          datePreset === p.key ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                        }`}>
                        {p.label}
                      </button>
                    ));
                  })()}
                  <input type="date" value={filterDateFrom}
                    onChange={(e) => { setFilterDateFrom(e.target.value); setDatePreset('custom'); }}
                    className="h-7 px-2 rounded-md border bg-card" />
                  <span className="text-muted-foreground">→</span>
                  <input type="date" value={filterDateTo}
                    onChange={(e) => { setFilterDateTo(e.target.value); setDatePreset('custom'); }}
                    className="h-7 px-2 rounded-md border bg-card" />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-20 text-muted-foreground">{t('filter.label_channel', { defaultValue: 'Canale' })}</span>
                  {['all', 'manual', 'storefront'].map(v => (
                    <button key={v} onClick={() => setFilterSource(v)}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                        filterSource === v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                      }`}>
                      {v === 'all' ? t('list.filter_all') : t(`source.${v}`)}
                    </button>
                  ))}
                </div>

                {orders.some(o => o.payment_intent && o.payment_intent !== 'none') && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="w-20 text-muted-foreground">{t('filter.label_payment', { defaultValue: 'Pagamento' })}</span>
                    {[
                      { key: 'all', labelKey: 'list.filter_all' },
                      { key: 'needs_attention', labelKey: 'filter.payment_collected' },
                      { key: 'awaiting', labelKey: 'filter.awaiting_payment' },
                    ].map(v => (
                      <button key={v.key} onClick={() => setFilterPayment(v.key)}
                        className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                          filterPayment === v.key ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                        }`}>
                        {t(v.labelKey)}
                      </button>
                    ))}
                  </div>
                )}

                <div className="flex justify-end border-t pt-2">
                  <button
                    onClick={() => {
                      setFilterStatus('all'); setFilterSource('all'); setFilterPayment('all');
                      setFilterReview('all'); setFilterItemType('all');
                      setFilterDateFrom(''); setFilterDateTo(''); setDatePreset('');
                      setSearchQuery(''); setAdvancedOpen(false);
                    }}
                    className="text-muted-foreground hover:text-foreground underline"
                  >
                    {t('filter.reset_all', { defaultValue: 'Azzera filtri' })}
                  </button>
                </div>
              </div>
            )}

          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b bg-muted/30">
                  <th className="text-left px-4 py-3 font-medium">{t('list.order_number')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('list.customer')}</th>
                  <th className="text-center px-4 py-3 font-medium">{t('list.status')}</th>
                  <th className="text-center px-4 py-3 font-medium hidden sm:table-cell">{t('list.payment')}</th>
                  <th className="text-right px-4 py-3 font-medium">{t('list.total')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden md:table-cell">{t('list.date')}</th>
                  <th className="px-4 py-3 w-32"></th>
                </tr></thead>
                <tbody>
                  {filteredOrders.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">
                      {t('list.no_results')}
                    </td></tr>
                  ) : filteredOrders.map(o => (
                    <tr key={o.id} className="border-b last:border-0 hover:bg-muted/20 cursor-pointer" onClick={() => setSelectedOrder(o)}>
                      <td className="px-4 py-3 font-mono text-xs">
                        {o.order_number || '-'}
                        {/* D2 — un solo badge per riga (lo stato): canale e
                            tipo diventano testo discreto, il colore torna a
                            significare qualcosa. */}
                        <div className="mt-0.5 text-[10px] font-sans text-muted-foreground">
                          {t(`source.${(SOURCE[getSource(o)] || SOURCE.manual).key}`)}
                          {[...new Set((o.items || []).map(it => it.item_type).filter(k => k && k !== 'physical' && ITEM_TYPE_LABELS[k]))]
                            .map(k => ` · ${ITEM_TYPE_LABELS[k]}`).join('')}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-1.5">
                          {o.review_state === 'paid_needs_confirm' && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0" title={t(`review.${o.review_reason}`, { defaultValue: 'Conferma necessaria' })} />}
                          {o.review_state === 'needs_approval' && <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" title={t(`review.${o.review_reason}`, { defaultValue: 'Approvazione richiesta' })} />}
                          {o.review_state === 'needs_review' && <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title={t(`review.${o.review_reason}`, { defaultValue: 'Da verificare' })} />}
                          {o.review_state === 'needs_payment' && o.review_reason !== 'awaiting_payment' && <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" title={t(`review.${o.review_reason}`, { defaultValue: 'Verifica necessaria' })} />}
                          <span className="truncate">{o.customer_name || '-'}</span>
                        </div>
                        {/* Onda 14 — Inline meta: first event occurrence date or first booking slot,
                            helps the admin triage without opening the detail panel. */}
                        {(() => {
                          const items = o.items || [];
                          const eventItem = items.find(it => it.occurrence_start_at);
                          if (eventItem) {
                            try {
                              const d = new Date(eventItem.occurrence_start_at);
                              const pretty = d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
                                + ' · ' + d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
                              return <div className="text-[11px] text-muted-foreground mt-0.5 truncate">🎟 {pretty}</div>;
                            } catch { return null; }
                          }
                          const bookingItem = items.find(it => it.booking_date);
                          if (bookingItem) {
                            try {
                              const d = new Date(bookingItem.booking_date + 'T12:00');
                              const pretty = d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
                                + (bookingItem.booking_start_time ? ` · ${bookingItem.booking_start_time}` : '');
                              return <div className="text-[11px] text-muted-foreground mt-0.5 truncate">📅 {pretty}</div>;
                            } catch { return null; }
                          }
                          const rentalItem = items.find(it => it.rental_date_from);
                          if (rentalItem) {
                            return <div className="text-[11px] text-muted-foreground mt-0.5 truncate">🧾 {rentalItem.rental_date_from}{rentalItem.rental_date_to ? ` → ${rentalItem.rental_date_to}` : ''}</div>;
                          }
                          return null;
                        })()}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {statusBadge(o.status, t)}
                      </td>
                      <td className="px-4 py-3 text-center hidden sm:table-cell">
                        {paymentBadge(o.payment_status, t)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">{fmtMoney(o.total, o.currency)}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">{o.order_date || '-'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 justify-end">
                          {o.actions?.edit?.allowed && (
                            <button onClick={(e) => { e.stopPropagation(); openEdit(o); }} className="p-1.5 rounded hover:bg-muted" title={t('actions.edit')}>
                              <Clock className="h-3.5 w-3.5" />
                            </button>
                          )}
                          {o.actions?.confirm?.allowed && (
                            <button onClick={(e) => { e.stopPropagation(); handleAction(o.id, 'confirm'); }} className="p-1.5 rounded hover:bg-blue-100 text-blue-700" title={t('actions.confirm')}>
                              <Check className="h-3.5 w-3.5" />
                            </button>
                          )}
                          {o.actions?.complete?.allowed && (
                            <button onClick={(e) => { e.stopPropagation(); handleAction(o.id, 'complete'); }} className="p-1.5 rounded hover:bg-emerald-100 text-emerald-700" title={t('actions.complete')}>
                              <CheckCircle2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                          {o.actions?.cancel?.allowed && (
                            <button onClick={(e) => { e.stopPropagation(); handleAction(o.id, 'cancel'); }} className="p-1.5 rounded hover:bg-red-100 text-red-700" title={t('actions.cancel')}>
                              <Ban className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          </div>
        )}
      </div>

      <OrderFormDialog
        open={dialogOpen}
        onClose={() => { setDialogOpen(false); setEditing(null); setPrefillCustomerId(null); }}
        onSaved={() => { setPrefillCustomerId(null); setEditing(null); load(); }}
        editing={editing}
        prefillCustomerId={prefillCustomerId}
        customers={customers}
        products={products}
        onCustomerCreated={(c) => setCustomers(prev => [...prev, c].sort((a, b) => a.name.localeCompare(b.name)))}
        t={t}
      />

      {selectedOrder && (
        <OrderDetailPanel
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          onAction={(id, action, ffStatus) => handleAction(id, action, ffStatus)}
          onEdit={(o) => { setSelectedOrder(null); openEdit(o); }}
          onSettleManual={(o) => handleSettleManual(o)}
          t={t}
        />
      )}

      <OrderImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onDone={load}
      />

      {/* Release 1 (Physical) — tracking capture at mark_shipped */}
      <TrackingDialog
        open={!!trackingDialog}
        onClose={() => setTrackingDialog(null)}
        submitting={trackingSubmitting}
        orderRef={trackingDialog?.orderRef}
        onConfirm={async (payload) => {
          if (!trackingDialog) return;
          setTrackingSubmitting(true);
          try {
            await ordersAPI.updateFulfillment(trackingDialog.orderId, 'shipped', payload);
            toast.success(t('fulfillment.toast_updated'));
            setSelectedOrder(null);
            setPendingReselect(trackingDialog.orderId);
            await load();
            setTrackingDialog(null);
          } catch (err) {
            toast.error(err?.response?.data?.detail || t('toast.error'));
          } finally {
            setTrackingSubmitting(false);
          }
        }}
      />
    </AppLayout>
  );
}
