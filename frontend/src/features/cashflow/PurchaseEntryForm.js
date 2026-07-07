import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Plus, Trash2, Save, Lock } from 'lucide-react';
import { purchasesAPI } from '../../api';
import { formatCurrency } from '../../lib/utils';
import { parseLocaleNumber } from '../../lib/parseLocaleNumber';
import { CreatableAutocomplete } from '../../components/CreatableAutocomplete';
import { useCurrency, useAuth } from '../../context/AuthContext';
import { useEntitlements } from '../../hooks/useEntitlements';
import { isPaywallHandled } from '../../utils/handleApiError';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

const makeEmptyRow = (defaultIva) => ({
  date: new Date().toISOString().split('T')[0],
  supplier_name: '',
  quantity: '',
  unit: 'kg',
  unit_price: '',
  iva: defaultIva != null ? String(defaultIva) : '',
  category: '',
  category_macro: '',
  description: '',
  invoice_number: '',
  due_date: '',
  payment_status: '',
});

const IVA_DEFAULT_OPTIONS = ['22', '10', '4', '0'];

const UNITS = ['kg', 'pezzi', 'metri', 'litri'];

export const PurchaseEntryForm = ({ onSaved }) => {
  const { t } = useTranslation('cashflow_monitor');
  const { user } = useAuth();
  const defaultIva = user?.default_iva;

  // v5.8 / Onda 9.Y.0.2 (Step D) — Pre-emptive UI gate, see SalesEntryForm.
  const { quotaExhausted, getMetric } = useEntitlements();
  const dataRowsExhausted = quotaExhausted('cashflow_monitor', 'data_rows');
  const dataRowsMetric = getMetric('data_rows');

  const PAYMENT_STATUSES = [
    { value: '', label: '—' },
    { value: 'pending', label: t('enums.payment_pending') },
    { value: 'paid', label: t('enums.payment_paid') },
    { value: 'overdue', label: t('enums.payment_overdue') },
  ];
  const currency = useCurrency();
  const [rows, setRows] = useState([makeEmptyRow(defaultIva)]);
  const [supplierOptions, setSupplierOptions] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [categoryMacroOptions, setCategoryMacroOptions] = useState([]);
  const [saving, setSaving] = useState(false);

  // Load suggestions on mount
  useEffect(() => {
    purchasesAPI.getSuppliers().then(res => setSupplierOptions(res.data || [])).catch(() => {});
    purchasesAPI.getCategories().then(res => setCategoryOptions(res.data || [])).catch(() => {});
    purchasesAPI.getCategoriesMacro().then(res => setCategoryMacroOptions(res.data || [])).catch(() => {});
  }, []);

  const updateRow = (idx, field, value) => {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r));
  };

  const addRow = () => setRows(prev => [...prev, makeEmptyRow(defaultIva)]);

  const removeRow = (idx) => {
    if (rows.length === 1) return;
    setRows(prev => prev.filter((_, i) => i !== idx));
  };

  const getTotal = (row) => {
    const q = parseLocaleNumber(row.quantity) || 0;
    const p = parseLocaleNumber(row.unit_price) || 0;
    return q * p;
  };

  const runningTotal = rows.reduce((sum, r) => sum + getTotal(r), 0);

  const handleSave = async () => {
    const valid = rows.filter(r => r.date && r.supplier_name && r.quantity && r.unit_price);
    if (valid.length === 0) {
      toast.error(t('validation.purchase_complete_row'));
      return;
    }
    const hasInvalid = valid.some(r => parseLocaleNumber(r.quantity) <= 0 || parseLocaleNumber(r.unit_price) <= 0);
    if (hasInvalid) {
      toast.error(t('validation.purchase_positive'));
      return;
    }
    setSaving(true);
    try {
      const records = valid.map(r => {
        const ivaNum = r.iva !== '' && r.iva != null ? parseLocaleNumber(r.iva) : null;
        return {
          date: r.date,
          supplier_name: r.supplier_name,
          quantity: parseLocaleNumber(r.quantity),
          unit: r.unit,
          unit_price: parseLocaleNumber(r.unit_price),
          iva: ivaNum != null && !isNaN(ivaNum) ? ivaNum : null,
          category: r.category || null,
          category_macro: r.category_macro || null,
          description: r.description || null,
          invoice_number: r.invoice_number || null,
          due_date: r.due_date || null,
          payment_status: r.payment_status || null,
        };
      });
      const res = await purchasesAPI.create(records);
      toast.success(t('toast.purchases_saved', { count: res.data.inserted }));
      // Optimistic refresh
      records.forEach(r => {
        if (r.supplier_name && !supplierOptions.includes(r.supplier_name)) {
          setSupplierOptions(prev => [...prev, r.supplier_name].sort());
        }
        if (r.category && !categoryOptions.includes(r.category)) {
          setCategoryOptions(prev => [...prev, r.category].sort());
        }
        if (r.category_macro && !categoryMacroOptions.includes(r.category_macro)) {
          setCategoryMacroOptions(prev => [...prev, r.category_macro].sort());
        }
      });
      setRows([makeEmptyRow(defaultIva)]);
      if (onSaved) onSaved();
    } catch (error) {
      // v5.8 / Onda 9.Y.0.2 (Step E) — paywall (cashflow_monitor.data_rows
      // QUOTA_EXCEEDED) ora si apre tramite axios interceptor. Skip generic
      // toast altrimenti compete col modal e l utente lo dismissa per primo,
      // mancando l upgrade CTA. Stesso pattern usato in SalesEntryForm /
      // ExpensesEntryForm dal v5.8 / Onda 9.O.
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
        <CardTitle className="text-base font-heading">{t('forms.title_purchases')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.date')}</th>
                <th className="pb-2 pr-2 min-w-[160px]">{t('forms.supplier')}</th>
                <th className="pb-2 pr-2 min-w-[80px]">{t('forms.quantity')}</th>
                <th className="pb-2 pr-2 min-w-[80px]">{t('forms.unit')}</th>
                <th className="pb-2 pr-2 min-w-[100px]">{t('forms.unit_price')}</th>
                <th className="pb-2 pr-2 min-w-[100px]">{t('forms.total')}</th>
                <th className="pb-2 pr-2 min-w-[80px]" title={t('forms.iva_tooltip')}>{t('forms.iva')}</th>
                <th className="pb-2 pr-2 min-w-[100px]" title={t('forms.total_with_iva_tooltip')}>{t('forms.total_with_iva')}</th>
                <th className="pb-2 pr-2 min-w-[120px]" title={t('forms.product_tooltip')}>{t('forms.product')}</th>
                <th className="pb-2 pr-2 min-w-[120px]" title={t('forms.purchase_category_tooltip')}>{t('forms.purchase_category')}</th>
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.due_date')}</th>
                <th className="pb-2 pr-2 min-w-[100px]">{t('forms.payment_status')}</th>
                <th className="pb-2 pr-2 min-w-[140px]">Descrizione</th>
                <th className="pb-2 pr-2 min-w-[110px]">N. Fattura</th>
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
                    <CreatableAutocomplete value={row.supplier_name} onChange={v => updateRow(idx, 'supplier_name', v)} options={supplierOptions} placeholder={t('forms.placeholder_supplier')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" inputMode="decimal" value={row.quantity} onChange={e => updateRow(idx, 'quantity', e.target.value)} placeholder="0" className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Select value={row.unit} onValueChange={v => updateRow(idx, 'unit', v)}>
                      <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {UNITS.map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" inputMode="decimal" value={row.unit_price} onChange={e => updateRow(idx, 'unit_price', e.target.value)} placeholder="0,00" className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <span className="text-xs font-medium">{formatCurrency(getTotal(row), currency)}</span>
                  </td>
                  <td className="py-1.5 pr-2">
                    <CreatableAutocomplete value={row.iva} onChange={v => updateRow(idx, 'iva', v)} options={IVA_DEFAULT_OPTIONS} placeholder="—" className="h-8 text-xs w-16" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <span className="text-xs text-muted-foreground">
                      {row.iva !== '' && row.iva != null && parseLocaleNumber(row.iva) > 0
                        ? formatCurrency(getTotal(row) * (1 + parseLocaleNumber(row.iva) / 100), currency)
                        : '—'}
                    </span>
                  </td>
                  <td className="py-1.5 pr-2">
                    <CreatableAutocomplete value={row.category} onChange={v => updateRow(idx, 'category', v)} options={categoryOptions} placeholder={t('forms.placeholder_category')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <CreatableAutocomplete value={row.category_macro} onChange={v => updateRow(idx, 'category_macro', v)} options={categoryMacroOptions} placeholder={t('forms.placeholder_category')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="date" value={row.due_date} onChange={e => updateRow(idx, 'due_date', e.target.value)} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <select value={row.payment_status} onChange={e => updateRow(idx, 'payment_status', e.target.value)} className="h-8 px-1.5 text-xs border rounded bg-background w-full">
                      {PAYMENT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" value={row.description} onChange={e => updateRow(idx, 'description', e.target.value)} placeholder="Descrizione" className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" value={row.invoice_number} onChange={e => updateRow(idx, 'invoice_number', e.target.value)} placeholder="N. Fattura" className="h-8 text-xs" />
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
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-foreground">{formatCurrency(getTotal(row), currency)}</span>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeRow(idx)} disabled={rows.length === 1}>
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.date')}</label>
                  <Input type="date" value={row.date} onChange={e => updateRow(idx, 'date', e.target.value)} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.supplier')}</label>
                  <CreatableAutocomplete value={row.supplier_name} onChange={v => updateRow(idx, 'supplier_name', v)} options={supplierOptions} placeholder={t('forms.placeholder_supplier')} className="h-10 text-sm" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.quantity')}</label>
                  <Input type="text" inputMode="decimal" value={row.quantity} onChange={e => updateRow(idx, 'quantity', e.target.value)} placeholder="0" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.unit')}</label>
                  <Select value={row.unit} onValueChange={v => updateRow(idx, 'unit', v)}>
                    <SelectTrigger className="h-10 text-sm w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {UNITS.map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.unit_price')}</label>
                  <Input type="text" inputMode="decimal" value={row.unit_price} onChange={e => updateRow(idx, 'unit_price', e.target.value)} placeholder="0,00" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.iva_percent', 'IVA %')}</label>
                  <CreatableAutocomplete value={row.iva} onChange={v => updateRow(idx, 'iva', v)} options={IVA_DEFAULT_OPTIONS} placeholder="—" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.total_with_iva', 'Totale con IVA')}</label>
                  <span className="text-sm text-muted-foreground leading-10 block">
                    {row.iva !== '' && row.iva != null && parseLocaleNumber(row.iva) > 0
                      ? formatCurrency(getTotal(row) * (1 + parseLocaleNumber(row.iva) / 100), currency)
                      : '—'}
                  </span>
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.product')}</label>
                  <CreatableAutocomplete value={row.category} onChange={v => updateRow(idx, 'category', v)} options={categoryOptions} placeholder={t('forms.product_tooltip')} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-visible">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block" title={t('forms.category_macro_tooltip')}>{t('forms.purchase_category')}</label>
                  <CreatableAutocomplete value={row.category_macro} onChange={v => updateRow(idx, 'category_macro', v)} options={categoryMacroOptions} placeholder={t('forms.placeholder_type_category')} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.due_date')}</label>
                  <Input type="date" value={row.due_date} onChange={e => updateRow(idx, 'due_date', e.target.value)} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.payment_status')}</label>
                  <select value={row.payment_status} onChange={e => updateRow(idx, 'payment_status', e.target.value)} className="h-10 w-full px-2 text-sm border rounded bg-background">
                    {PAYMENT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                <div className="col-span-2 min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Descrizione</label>
                  <Input type="text" value={row.description} onChange={e => updateRow(idx, 'description', e.target.value)} placeholder="Descrizione" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">N. Fattura</label>
                  <Input type="text" value={row.invoice_number} onChange={e => updateRow(idx, 'invoice_number', e.target.value)} placeholder="N. Fattura" className="h-10 text-sm w-full" />
                </div>
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

export default PurchaseEntryForm;
