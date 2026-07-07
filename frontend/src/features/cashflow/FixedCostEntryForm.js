import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Checkbox } from '../../components/ui/checkbox';
import { Plus, Trash2, Save, Lock } from 'lucide-react';
import { fixedCostsAPI } from '../../api';
import { formatCurrency } from '../../lib/utils';
import { parseLocaleNumber } from '../../lib/parseLocaleNumber';
import { useCurrency } from '../../context/AuthContext';
import { useEntitlements } from '../../hooks/useEntitlements';
import { isPaywallHandled } from '../../utils/handleApiError';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

// CATEGORIES and FREQUENCIES are resolved inside the component via useTranslation

const EMPTY_ROW = {
  name: '',
  category: '',
  customCategory: '',
  isCustomCategory: false,
  amount: '',
  frequency: 'mensile',
  start_date: new Date().toISOString().split('T')[0],
  end_date: '',
  no_expiry: true,
};

export const FixedCostEntryForm = ({ onSaved }) => {
  const { t } = useTranslation('cashflow_monitor');

  // v5.8 / Onda 9.Y.0.2 (Step D) — Pre-emptive UI gate, see SalesEntryForm.
  const { quotaExhausted, getMetric } = useEntitlements();
  const dataRowsExhausted = quotaExhausted('cashflow_monitor', 'data_rows');
  const dataRowsMetric = getMetric('data_rows');

  const CATEGORIES = [
    { value: 'affitto', label: t('enums.cat_rent') },
    { value: 'stipendio', label: t('enums.cat_salary') },
    { value: 'finanziamento', label: t('enums.cat_financing') },
    { value: 'leasing', label: t('enums.cat_leasing') },
    { value: 'abbonamento', label: t('enums.cat_subscription') },
    { value: '__nuova__', label: t('forms.new_category') },
  ];

  const FREQUENCIES = [
    { value: 'mensile', label: t('enums.freq_monthly') },
    { value: 'settimanale', label: t('enums.freq_weekly') },
    { value: 'trimestrale', label: t('enums.freq_quarterly') },
    { value: 'annuale', label: t('enums.freq_annual') },
  ];
  const currency = useCurrency();
  const [rows, setRows] = useState([{ ...EMPTY_ROW }]);
  const [saving, setSaving] = useState(false);

  const updateRow = (idx, field, value) => {
    setRows(prev => prev.map((r, i) => {
      if (i !== idx) return r;
      const updated = { ...r, [field]: value };
      if (field === 'no_expiry' && value) {
        updated.end_date = '';
      }
      // When user selects "Nuova Categoria", switch to custom input mode
      if (field === 'category' && value === '__nuova__') {
        updated.isCustomCategory = true;
        updated.category = '';
        updated.customCategory = '';
      }
      return updated;
    }));
  };

  const addRow = () => setRows(prev => [...prev, { ...EMPTY_ROW }]);

  const removeRow = (idx) => {
    if (rows.length === 1) return;
    setRows(prev => prev.filter((_, i) => i !== idx));
  };

  const monthlyEstimate = rows.reduce((sum, r) => {
    const amount = parseLocaleNumber(r.amount) || 0;
    const freqMultiplier = { mensile: 1, settimanale: 4.33, trimestrale: 1 / 3, annuale: 1 / 12 };
    return sum + amount * (freqMultiplier[r.frequency] || 1);
  }, 0);

  const handleSave = async () => {
    const valid = rows.filter(r => r.name && r.amount && r.start_date && (r.category || r.customCategory));
    if (valid.length === 0) {
      toast.error(t('validation.fixed_complete_row'));
      return;
    }
    const hasInvalid = valid.some(r => parseLocaleNumber(r.amount) <= 0);
    if (hasInvalid) {
      toast.error(t('validation.fixed_amount_positive'));
      return;
    }
    setSaving(true);
    try {
      const records = valid.map(r => ({
        name: r.name,
        category: r.isCustomCategory ? r.customCategory.trim() : r.category,
        amount: parseLocaleNumber(r.amount),
        frequency: r.frequency,
        start_date: r.start_date,
        end_date: r.no_expiry ? null : (r.end_date || null),
      }));
      const res = await fixedCostsAPI.createBulk(records);
      toast.success(t('toast.fixed_costs_saved', { count: res.data.inserted }));
      setRows([{ ...EMPTY_ROW }]);
      if (onSaved) onSaved();
    } catch (error) {
      // v5.8 / Onda 9.Y.0.2 (Step E) — paywall handles cashflow_monitor.data_rows.
      // Skip generic toast to keep paywall in focus.
      if (!isPaywallHandled(error)) {
        toast.error(t('toast.save_error'));
      }
    } finally {
      setSaving(false);
    }
  };

  const CategoryField = ({ row, idx, inputClass }) => {
    if (row.isCustomCategory) {
      return (
        <div className="flex items-center gap-1">
          <Input
            value={row.customCategory}
            onChange={e => updateRow(idx, 'customCategory', e.target.value)}
            placeholder={t('forms.placeholder_type_category')}
            className={`${inputClass} flex-1`}
            autoFocus
          />
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 shrink-0"
            title={t('forms.back_to_list')}
            onClick={() => setRows(prev => prev.map((r, i) => i === idx ? { ...r, isCustomCategory: false, customCategory: '', category: '' } : r))}
          >
            x
          </Button>
        </div>
      );
    }
    return (
      <Select value={row.category} onValueChange={v => updateRow(idx, 'category', v)}>
        <SelectTrigger className={inputClass}><SelectValue placeholder={t('forms.placeholder_select')} /></SelectTrigger>
        <SelectContent>
          {CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
        </SelectContent>
      </Select>
    );
  };

  return (
    <Card className="border border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-heading">{t('forms.title_fixed_costs')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-2 min-w-[140px]">{t('forms.name')}</th>
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.category')}</th>
                <th className="pb-2 pr-2 min-w-[100px]">{t('forms.amount')}</th>
                <th className="pb-2 pr-2 min-w-[110px]">{t('forms.frequency')}</th>
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.start_date')}</th>
                <th className="pb-2 pr-2 min-w-[120px]">{t('forms.end_date')}</th>
                <th className="pb-2 pr-2 min-w-[90px]">{t('forms.no_expiry')}</th>
                <th className="pb-2 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="py-1.5 pr-2">
                    <Input value={row.name} onChange={e => updateRow(idx, 'name', e.target.value)} placeholder={t('forms.placeholder_fixed_name')} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <CategoryField row={row} idx={idx} inputClass="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="text" inputMode="decimal" value={row.amount} onChange={e => updateRow(idx, 'amount', e.target.value)} placeholder="0,00" className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Select value={row.frequency} onValueChange={v => updateRow(idx, 'frequency', v)}>
                      <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FREQUENCIES.map(f => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="date" value={row.start_date} onChange={e => updateRow(idx, 'start_date', e.target.value)} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input type="date" value={row.end_date} onChange={e => updateRow(idx, 'end_date', e.target.value)} disabled={row.no_expiry} className="h-8 text-xs" />
                  </td>
                  <td className="py-1.5 pr-2">
                    <div className="flex items-center justify-center">
                      <Checkbox checked={row.no_expiry} onCheckedChange={v => updateRow(idx, 'no_expiry', v)} />
                    </div>
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
                <div className="col-span-2 min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.name')}</label>
                  <Input value={row.name} onChange={e => updateRow(idx, 'name', e.target.value)} placeholder={t('forms.placeholder_fixed_name')} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Categoria</label>
                  <CategoryField row={row} idx={idx} inputClass="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.amount')}</label>
                  <Input type="text" inputMode="decimal" value={row.amount} onChange={e => updateRow(idx, 'amount', e.target.value)} placeholder="0,00" className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.frequency')}</label>
                  <Select value={row.frequency} onValueChange={v => updateRow(idx, 'frequency', v)}>
                    <SelectTrigger className="h-10 text-sm w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {FREQUENCIES.map(f => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.start_date')}</label>
                  <Input type="date" value={row.start_date} onChange={e => updateRow(idx, 'start_date', e.target.value)} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 overflow-hidden">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.end_date')}</label>
                  <Input type="date" value={row.end_date} onChange={e => updateRow(idx, 'end_date', e.target.value)} disabled={row.no_expiry} className="h-10 text-sm w-full" />
                </div>
                <div className="min-w-0 flex items-center gap-2 pt-2">
                  <Checkbox checked={row.no_expiry} onCheckedChange={v => updateRow(idx, 'no_expiry', v)} />
                  <label className="text-xs font-medium text-muted-foreground">{t('forms.no_expiry_label')}</label>
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
              <span className="text-sm font-medium">{t('forms.monthly_estimate')}{formatCurrency(monthlyEstimate, currency)}</span>
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

export default FixedCostEntryForm;
