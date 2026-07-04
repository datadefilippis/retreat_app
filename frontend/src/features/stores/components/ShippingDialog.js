/**
 * ShippingDialog — admin modal to configure shipping options for ONE store.
 *
 * Two tabs:
 *   1. "Questo store" — options with store_id = store.id (per-store only)
 *   2. "Globali" — options with store_id = null (visible on all stores of the org)
 *
 * Data flow:
 *   - On open, load BOTH scopes via two independent `shippingOptionsAPI.list`
 *     calls (store + global).
 *   - Each tab edits its own scope's rows via `ShippingOptionsEditor`.
 *   - "Salva" button performs a delete-all + recreate for the CURRENT tab's
 *     scope. Simpler than a diff-based sync, and the dataset is < 10 rows.
 *
 * Reconciliation is scope-local: saving the "Questo store" tab does NOT
 * affect globals and vice versa. The admin can close without saving if
 * they change their mind (confirmation omitted for brevity — low stakes).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import {
  ResponsiveDialog, ResponsiveDialogContent, ResponsiveDialogHeader,
  ResponsiveDialogTitle, ResponsiveDialogFooter,
} from '../../../components/ui/responsive-dialog';
import { Button } from '../../../components/ui/button';
import { Truck, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { shippingOptionsAPI } from '../../../api/shippingOptions';
import ShippingOptionsEditor from './ShippingOptionsEditor';


function stripLocalFields(row) {
  // Backend rejects unknown fields only softly, but we keep the payload
  // clean — id is included ONLY when it already existed on the server
  // (meaning the row was loaded, not newly-added). We don't need to
  // send the id because we do a delete-all + recreate anyway.
  const { _localId, id, organization_id, store_id, created_at, updated_at, ...rest } = row;
  // Coerce numeric strings produced by the number inputs back to numbers.
  if (rest.base_price !== undefined) {
    const n = Number(rest.base_price);
    rest.base_price = Number.isFinite(n) ? n : 0;
  }
  if (rest.free_shipping_threshold === '' || rest.free_shipping_threshold === null || rest.free_shipping_threshold === undefined) {
    rest.free_shipping_threshold = null;
  } else {
    const n = Number(rest.free_shipping_threshold);
    rest.free_shipping_threshold = Number.isFinite(n) ? n : null;
  }
  return rest;
}


export default function ShippingDialog({ open, store, onClose }) {
  const { t } = useTranslation('stores');
  const storeId = store?.id || null;
  const storeName = store?.name || '';

  const [activeTab, setActiveTab] = useState('store'); // 'store' | 'global'
  const [storeRows, setStoreRows] = useState([]);
  const [globalRows, setGlobalRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!open || !storeId) return;
    setLoading(true);
    try {
      const [sRes, gRes] = await Promise.all([
        shippingOptionsAPI.list({ storeId, scope: 'store' }),
        shippingOptionsAPI.list({ scope: 'global' }),
      ]);
      setStoreRows(sRes.data?.options || []);
      setGlobalRows(gRes.data?.options || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('shipping.toast.load_error'));
      setStoreRows([]);
      setGlobalRows([]);
    } finally {
      setLoading(false);
    }
  }, [open, storeId, t]);

  useEffect(() => { load(); }, [load]);

  // Reset state on close to avoid showing stale rows when reopening for
  // another store.
  useEffect(() => {
    if (!open) {
      setStoreRows([]);
      setGlobalRows([]);
      setActiveTab('store');
    }
  }, [open]);

  const saveCurrentScope = async () => {
    setSaving(true);
    try {
      const rows = activeTab === 'store' ? storeRows : globalRows;
      const scopedStoreId = activeTab === 'store' ? storeId : null;

      // Validate — reject empty labels so we don't persist rubbish rows
      // silently. base_price ge=0 is handled by the number input.
      for (const r of rows) {
        if (!r.label?.trim()) {
          toast.error(t('shipping.toast.name_required'));
          setSaving(false);
          return;
        }
        if (r.base_price !== '' && Number(r.base_price) < 0) {
          toast.error(t('shipping.toast.price_negative'));
          setSaving(false);
          return;
        }
      }

      // Delete-all + recreate for this scope. The backend does NOT expose
      // a bulk endpoint yet, so we issue N+M calls. The dataset is tiny
      // (<10 options in practice) so latency is acceptable.
      const res = activeTab === 'store'
        ? await shippingOptionsAPI.list({ storeId, scope: 'store' })
        : await shippingOptionsAPI.list({ scope: 'global' });
      const existing = res.data?.options || [];

      for (const old of existing) {
        try { await shippingOptionsAPI.delete(old.id); } catch { /* ignore */ }
      }
      const created = [];
      for (let i = 0; i < rows.length; i++) {
        const payload = {
          ...stripLocalFields(rows[i]),
          store_id: scopedStoreId,
          sort_order: i,
        };
        try {
          const r = await shippingOptionsAPI.create(payload);
          created.push(r.data);
        } catch (err) {
          toast.warning(t('shipping.toast.row_warning', {
            label: rows[i].label,
            detail: err?.response?.data?.detail || t('shipping.toast.row_warning_generic'),
          }));
        }
      }

      if (activeTab === 'store') setStoreRows(created);
      else setGlobalRows(created);
      toast.success(t('shipping.toast.saved'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('shipping.toast.save_error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={(v) => { if (!v) onClose?.(); }}>
      <ResponsiveDialogContent className="sm:max-w-2xl max-h-[90vh] sm:max-h-[85vh] overflow-y-auto">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <Truck className="h-4 w-4" />
            {t('shipping.title', { storeName })}
          </ResponsiveDialogTitle>
          <p className="text-xs text-gray-500 mt-1">
            {t('shipping.description')}
          </p>
        </ResponsiveDialogHeader>

        {/* Tab switcher */}
        <div className="flex gap-1 border-b">
          <button
            type="button"
            onClick={() => setActiveTab('store')}
            className={`px-3 py-2 text-sm font-semibold transition-colors border-b-2 ${
              activeTab === 'store'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-900'
            }`}
          >
            {t('shipping.tabs.store')}
            <span className="ml-1.5 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] tabular-nums">
              {storeRows.length}
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('global')}
            className={`px-3 py-2 text-sm font-semibold transition-colors border-b-2 ${
              activeTab === 'global'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-900'
            }`}
          >
            {t('shipping.tabs.global')}
            <span className="ml-1.5 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] tabular-nums">
              {globalRows.length}
            </span>
          </button>
        </div>

        {/* Scope hint — Trans interpolation pulls <strong> tags into the
            translated body so the emphasis lands on the same words in
            every language ("solo"/"only"/"nur"/"uniquement"). */}
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
          {activeTab === 'store' ? (
            <Trans
              i18nKey="shipping.hint.store"
              ns="stores"
              values={{ storeName }}
              components={[<strong />, <strong />]}
            />
          ) : (
            <Trans
              i18nKey="shipping.hint.global"
              ns="stores"
              components={[<strong />]}
            />
          )}
        </div>

        <div className="py-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            </div>
          ) : activeTab === 'store' ? (
            <ShippingOptionsEditor
              options={storeRows}
              onChange={setStoreRows}
              storeId={storeId}
            />
          ) : (
            <ShippingOptionsEditor
              options={globalRows}
              onChange={setGlobalRows}
              storeId={null}
            />
          )}
        </div>

        <ResponsiveDialogFooter>
          <Button
            variant="outline"
            onClick={() => onClose?.()}
            disabled={saving}
            className="w-full sm:w-auto"
          >
            {t('shipping.actions.close')}
          </Button>
          <Button
            onClick={saveCurrentScope}
            disabled={saving || loading}
            className="w-full sm:w-auto gap-2"
          >
            {saving && <Loader2 className="h-3 w-3 animate-spin" />}
            {activeTab === 'store'
              ? t('shipping.actions.save_store')
              : t('shipping.actions.save_global')}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
