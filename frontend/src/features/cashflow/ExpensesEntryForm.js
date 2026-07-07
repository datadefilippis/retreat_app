import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Plus, Trash2, Save, Lock } from 'lucide-react';
import { expensesAPI } from '../../api';
import { formatCurrency } from '../../lib/utils';
import { parseLocaleNumber } from '../../lib/parseLocaleNumber';
import { CreatableAutocomplete } from '../../components/CreatableAutocomplete';
import { useCurrency } from '../../context/AuthContext';
import { useEntitlements } from '../../hooks/useEntitlements';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { isPaywallHandled } from '../../utils/handleApiError';

const EMPTY_ROW = {
  date: new Date().toISOString().split('T')[0],
  amount: '',
  category: '',
  description: '',
  supplier: '',
};

export const ExpensesEntryForm = ({ onSaved }) => {
  const { t } = useTranslation('cashflow_monitor');
  const currency = useCurrency();

  // v5.8 / Onda 9.Y.0.2 (Step D) — Pre-emptive UI gate, see SalesEntryForm.
  const { quotaExhausted, getMetric } = useEntitlements();
  const dataRowsExhausted = quotaExhausted('cashflow_monitor', 'data_rows');
  const dataRowsMetric = getMetric('data_rows');

  const [rows, setRows] = useState([{ ...EMPTY_ROW }]);
  const [saving, setSaving] = useState(false);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [supplierOptions, setSupplierOptions] = useState([]);

  // Load suggestions on mount
  useEffect(() => {
    expensesAPI.getCategories().then(res => setCategoryOptions(res.data || [])).catch(() => {});
    expensesAPI.getSuppliers().then(res => setSupplierOptions(res.data || [])).catch(() => {});
  }, []);

  const updateRow = (idx, field, value) => {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r));
  };

  const addRow = () => setRows(prev => [...prev, { ...EMPTY_ROW }]);

  const removeRow = (idx) => {
    if (rows.length === 1) return;
    setRows(prev => prev.filter((_, i) => i !== idx));
  };

  const runningTotal = rows.reduce((sum, r) => sum + (parseLocaleNumber(r.amount) || 0), 0);

  const handleSave = async () => {
    const valid = rows.filter(r => r.date && r.amount);
    if (valid.length === 0) {
      toast.error(t('validation.min_one_row'));
      return;
    }
    const hasInvalid = valid.some(r => parseLocaleNumber(r.amount) <= 0);
    if (hasInvalid) {
      toast.error(t('validation.amount_positive'));
      return;
    }
    setSaving(true);
    try {
      const records = valid.map(r => ({
        date: r.date,
        amount: parseLocaleNumber(r.amount),
        category: r.category || null,
        description: r.description || null,
        supplier: r.supplier || null,
      }));
      const res = await expensesAPI.create(records);
      toast.success(t('toast.expenses_saved', { count: res.data.inserted }));
      // Optimistic refresh
      records.forEach(r => {
        if (r.category && !categoryOptions.includes(r.category)) {
          setCategoryOptions(prev => [...prev, r.category].sort());
        }
        if (r.supplier && !supplierOptions.includes(r.supplier)) {
          setSupplierOptions(prev => [...prev, r.supplier].sort());
        }
      });
      setRows([{ ...EMPTY_ROW }]);
      if (onSaved) onSaved();
    } catch (error) {
      // v5.8 / Onda 9.O — paywall handles cashflow_monitor.data_rows quota
      if (!isPaywallHandled(error)) {
        toast.error(t('toast.save_error'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-heading">{t('forms.title_expenses')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.date')}</th>
                <th className="pb-2 pr-2 min-w-[110px]">{t('forms.amount')}</th>
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.category')}</th>
                <th className="pb-2 pr-2 min-w-[160px]">{t('forms.description')}</th>
                <th className="pb-2 pr-2 min-w-[140px]">{t('forms.supplier')}</th>
                <th className="pb-2 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="py-1.5 pr-2">
                    <Input type="date" value={row.date} onChange={e => updateRow(idx, 'date', e.target.value)} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" inputMode="decimal" value={row.amount} onChange={e => updateRow(idx, 'amount', e.target.value)} placeholder="0,00" className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <CreatableAutocomplete value={row.category} onChange={v => updateRow(idx, 'category', v)} options={categoryOptions} placeholder={t('forms.placeholder_category')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input value={row.description} onChange={e => updateRow(idx, 'description', e.target.value)} placeholder={t('forms.placeholder_description')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <CreatableAutocomplete value={row.supplier} onChange={v => updateRow(idx, 'supplier', v)} options={supplierOptions} placeholder={t('forms.placeholder_supplier')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5">
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeRow(idx)} disabled={rows.length === 1}>
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile card layout */}
        <div className="md:hidden space-y-3">
          {rows.map((row, idx) => (
            <div key={idx} className="rounded-xl border bg-muted/30 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">{t('forms.row_n', { n: idx + 1 })}</span>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeRow(idx)} disabled={rows.length === 1}>
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.date')}</label>
                  <Input type="date" value={row.date} onChange={e => updateRow(idx, 'date', e.target.value)} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.amount')}</label>
                  <Input type="text" inputMode="decimal" value={row.amount} onChange={e => updateRow(idx, 'amount', e.target.value)} placeholder="0,00" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.category')}</label>
                  <CreatableAutocomplete value={row.category} onChange={v => updateRow(idx, 'category', v)} options={categoryOptions} placeholder={t('forms.placeholder_category')} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.supplier')}</label>
                  <CreatableAutocomplete value={row.supplier} onChange={v => updateRow(idx, 'supplier', v)} options={supplierOptions} placeholder={t('forms.placeholder_supplier')} className="h-10 text-sm w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.description')}</label>
                <Input value={row.description} onChange={e => updateRow(idx, 'description', e.target.value)} placeholder={t('forms.placeholder_description')} className="h-10 text-sm" />
              </div>
            </div>
          ))}
        </div>

        {/* Actions bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2 sticky bottom-0 bg-card pb-2 md:static">
          <Button variant="outline" size="sm" onClick={addRow} className="md:h-8 h-10">
            <Plus className="h-3.5 w-3.5 mr-1" /> {t('forms.add_row')}
          </Button>
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">{t('forms.total_label')}{formatCurrency(runningTotal, currency)}</span>
              <Button
                size="sm"
                onClick={dataRowsExhausted ? undefined : handleSave}
                disabled={saving || dataRowsExhausted}
                className="md:h-8 h-10"
                title={dataRowsExhausted
                  ? t('forms.quota_exhausted_hint', { defaultValue: 'Limite righe dati raggiunto. Aggiorna piano.' })
                  : undefined}
              >
                {dataRowsExhausted ? <Lock className="h-3.5 w-3.5 mr-1" /> : <Save className="h-3.5 w-3.5 mr-1" />}
                {saving ? t('forms.saving') : t('forms.save_all')}
              </Button>
            </div>
            {dataRowsExhausted && dataRowsMetric && (
              <p className="text-xs text-muted-foreground">
                {t('forms.quota_exhausted_body', {
                  used: dataRowsMetric.used,
                  limit: dataRowsMetric.limit,
                  defaultValue: 'Hai raggiunto il limite di {{used}}/{{limit}} righe dati questo mese.',
                })}
                {' '}
                <Link to="/billing" className="underline font-medium text-primary">
                  {t('forms.quota_exhausted_cta', { defaultValue: 'Aggiorna piano' })}
                </Link>
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ExpensesEntryForm;
