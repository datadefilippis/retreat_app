import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Trash2, RefreshCw, Pencil, Check, X, Filter, RotateCcw } from 'lucide-react';
import { fixedCostsAPI } from '../../api';
import { useCashflowFilters } from './hooks/useCashflowFilters';
import CashflowFilterPopup from './components/CashflowFilterPopup';
import { formatCurrency, formatDate } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { FixedCostEntryForm } from './FixedCostEntryForm';
import { ModuleDatasetManager } from '../../components/ModuleDatasetManager';

// CATEGORY_LABELS and FREQUENCY_LABELS resolved inside component via useTranslation

const isActive = (fc) => {
  if (!fc.end_date) return true;
  return new Date(fc.end_date) >= new Date();
};

export const FixedCostsSection = () => {
  const { t } = useTranslation('cashflow_monitor');

  const CATEGORY_LABELS = {
    affitto: t('enums.cat_rent'),
    stipendio: t('enums.cat_salary'),
    finanziamento: t('enums.cat_financing'),
    leasing: t('enums.cat_leasing'),
    abbonamento: t('enums.cat_subscription'),
    altro: t('enums.cat_other'),
  };

  const FREQUENCY_LABELS = {
    mensile: t('enums.freq_monthly'),
    settimanale: t('enums.freq_weekly'),
    trimestrale: t('enums.freq_quarterly'),
    annuale: t('enums.freq_annual'),
  };
  const currency = useCurrency();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  // Multi-field filter popup (see SalesSection for the wider pattern note).
  const [filterOpen, setFilterOpen] = useState(false);
  const { filters, setFilters, filtered, activeCount, reset: resetFilters } =
    useCashflowFilters({ records, categoryType: 'fixed_costs' });

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      // 2026-05-20 — Request the backend's max (le=500 in
      // routers/fixed_costs.py). The previous default (limit=200)
      // truncated the table for orgs with >200 fixed costs and the
      // client-side filter would silently miss those rows.
      // The CashflowModulePage dashboard widget that calls
      // ``fixedCostsAPI.list({ limit: 100 })`` is unchanged — it
      // intentionally requests only the top 100 for the recap card.
      const res = await fixedCostsAPI.list({ limit: 500 });
      setRecords(res.data || []);
    } catch (error) {
      console.error('Failed to fetch fixed costs:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const handleDelete = async (id) => {
    try {
      await fixedCostsAPI.delete(id);
      setRecords(prev => prev.filter(r => r.id !== id));
      toast.success(t('toast.fixed_cost_deleted'));
    } catch {
      toast.error(t('toast.delete_error'));
    }
  };

  const startEdit = (r) => {
    setEditingId(r.id);
    setEditValues({
      name: r.name || '',
      category: r.category || 'altro',
      amount: r.amount || 0,
      frequency: r.frequency || 'mensile',
      start_date: r.start_date || '',
      end_date: r.end_date || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSave = async () => {
    try {
      const original = records.find(r => r.id === editingId);
      const updates = {};
      if (editValues.name !== (original.name || '')) updates.name = editValues.name;
      if (editValues.category !== (original.category || 'altro')) updates.category = editValues.category;
      if (Number(editValues.amount) !== (original.amount || 0)) updates.amount = Number(editValues.amount);
      if (editValues.frequency !== (original.frequency || 'mensile')) updates.frequency = editValues.frequency;
      if (editValues.start_date !== (original.start_date || '')) updates.start_date = editValues.start_date;
      if (editValues.end_date !== (original.end_date || '')) updates.end_date = editValues.end_date || null;

      if (Object.keys(updates).length === 0) {
        cancelEdit();
        return;
      }

      await fixedCostsAPI.update(editingId, updates);
      setRecords(prev => prev.map(r => r.id === editingId ? { ...r, ...updates } : r));
      toast.success(t('toast.record_updated'));
      cancelEdit();
    } catch {
      toast.error(t('toast.update_error'));
    }
  };

  const isEditingRow = (id) => editingId === id;

  return (
    <div className="space-y-6">
      <Tabs defaultValue="manual">
        <TabsList>
          <TabsTrigger value="manual">{t('sections.tab_manual')}</TabsTrigger>
          <TabsTrigger value="import">{t('sections.tab_import')}</TabsTrigger>
        </TabsList>
        <TabsContent value="manual" className="mt-4">
          <FixedCostEntryForm onSaved={fetchRecords} />
        </TabsContent>
        <TabsContent value="import" className="mt-4">
          <ModuleDatasetManager datasetType="fixed_costs" onUploadComplete={fetchRecords} />
        </TabsContent>
      </Tabs>

      {/* Records table */}
      <Card className="border border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3 gap-2">
          <CardTitle className="text-base font-heading">
            Costi Fissi Registrati ({activeCount > 0 ? `${filtered.length}/${records.length}` : records.length})
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant={activeCount > 0 ? 'default' : 'outline'}
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => setFilterOpen(true)}
              aria-label={t('filters.button_label')}
            >
              <Filter className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t('filters.button_label')}</span>
              {activeCount > 0 && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 ml-0.5">
                  {activeCount}
                </Badge>
              )}
            </Button>
            {activeCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-muted-foreground hover:text-foreground"
                onClick={resetFilters}
                aria-label={t('filters.reset')}
                title={t('filters.reset')}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={fetchRecords} aria-label={t('sections.refresh', { defaultValue: 'Refresh' })}>
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CashflowFilterPopup
          open={filterOpen}
          onOpenChange={setFilterOpen}
          categoryType="fixed_costs"
          value={filters}
          onChange={setFilters}
          onReset={resetFilters}
          options={{}}
          activeCount={activeCount}
        />
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.loading')}</div>
          ) : records.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.empty_fixed_costs')}</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 space-y-3">
              <p className="text-sm text-muted-foreground">{t('filters.no_results_filtered')}</p>
              <Button variant="outline" size="sm" onClick={resetFilters}>
                {t('filters.reset')}
              </Button>
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 pr-3">{t('forms.name')}</th>
                      <th className="pb-2 pr-3">{t('forms.category')}</th>
                      <th className="pb-2 pr-3">{t('forms.amount')}</th>
                      <th className="pb-2 pr-3">{t('forms.frequency')}</th>
                      <th className="pb-2 pr-3">{t('forms.start_date')}</th>
                      <th className="pb-2 pr-3">{t('forms.end_date')}</th>
                      <th className="pb-2 pr-3">{t('sections.status')}</th>
                      <th className="pb-2 pr-3">{t('sections.source')}</th>
                      <th className="pb-2 w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((r) => (
                      <tr key={r.id} className={`border-b last:border-0 ${isEditingRow(r.id) ? 'bg-primary/5' : 'hover:bg-muted/50'}`}>
                        <td className="py-2 pr-3 font-medium">
                          {isEditingRow(r.id) ? (
                            <input type="text" value={editValues.name} onChange={(e) => setEditValues(v => ({ ...v, name: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-32" />
                          ) : r.name}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditingRow(r.id) ? (
                            <select value={editValues.category} onChange={(e) => setEditValues(v => ({ ...v, category: e.target.value }))} className="h-7 px-1 text-sm border rounded w-28">
                              {Object.entries(CATEGORY_LABELS).map(([k, label]) => (
                                <option key={k} value={k}>{label}</option>
                              ))}
                            </select>
                          ) : (
                            <Badge variant="outline" className="text-xs">{CATEGORY_LABELS[r.category] || r.category}</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3 font-medium">
                          {isEditingRow(r.id) ? (
                            <input type="number" step="0.01" value={editValues.amount} onChange={(e) => setEditValues(v => ({ ...v, amount: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-24" />
                          ) : formatCurrency(r.amount, currency)}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditingRow(r.id) ? (
                            <select value={editValues.frequency} onChange={(e) => setEditValues(v => ({ ...v, frequency: e.target.value }))} className="h-7 px-1 text-sm border rounded w-28">
                              {Object.entries(FREQUENCY_LABELS).map(([k, label]) => (
                                <option key={k} value={k}>{label}</option>
                              ))}
                            </select>
                          ) : (FREQUENCY_LABELS[r.frequency] || r.frequency)}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditingRow(r.id) ? (
                            <input type="date" value={editValues.start_date} onChange={(e) => setEditValues(v => ({ ...v, start_date: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-32" />
                          ) : formatDate(r.start_date)}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditingRow(r.id) ? (
                            <input type="date" value={editValues.end_date} onChange={(e) => setEditValues(v => ({ ...v, end_date: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-32" />
                          ) : (r.end_date ? formatDate(r.end_date) : '-')}
                        </td>
                        <td className="py-2 pr-3">
                          {isActive(r) ? (
                            <Badge className="bg-green-100 text-green-700 text-xs">{t('sections.active_badge')}</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-500 text-xs">{t('sections.inactive_badge')}</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge variant="secondary" className="text-xs">
                            {r.source_label || (r.dataset_id === 'manual' ? t('sections.source_manual') : t('sections.source_file'))}
                          </Badge>
                        </td>
                        <td className="py-2">
                          {isEditingRow(r.id) ? (
                            <div className="flex gap-1">
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleSave}>
                                <Check className="h-3.5 w-3.5 text-green-600" />
                              </Button>
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={cancelEdit}>
                                <X className="h-3.5 w-3.5 text-red-500" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex gap-1">
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => startEdit(r)}>
                                <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                              </Button>
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleDelete(r.id)}>
                                <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                              </Button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile card layout */}
              <div className="md:hidden space-y-3">
                {filtered.map((r) => (
                  <div key={r.id} className={`rounded-xl border p-4 space-y-2 ${isEditingRow(r.id) ? 'bg-primary/5 border-primary/20' : 'bg-muted/30'}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {isActive(r) ? (
                          <Badge className="bg-green-100 text-green-700 text-[10px]">{t('sections.active_badge')}</Badge>
                        ) : (
                          <Badge className="bg-gray-100 text-gray-500 text-[10px]">{t('enums.payment_overdue')}</Badge>
                        )}
                        <Badge variant="secondary" className="text-[10px]">
                          {r.source_label || (r.dataset_id === 'manual' ? t('sections.source_manual') : t('sections.source_file'))}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1">
                        {isEditingRow(r.id) ? (
                          <>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleSave}>
                              <Check className="h-3.5 w-3.5 text-green-600" />
                            </Button>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={cancelEdit}>
                              <X className="h-3.5 w-3.5 text-red-500" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => startEdit(r)}>
                              <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                            </Button>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleDelete(r.id)}>
                              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                    {isEditingRow(r.id) ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.name')}</label>
                          <input type="text" value={editValues.name} onChange={(e) => setEditValues(v => ({ ...v, name: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.category')}</label>
                          <select value={editValues.category} onChange={(e) => setEditValues(v => ({ ...v, category: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded bg-background">
                            {Object.entries(CATEGORY_LABELS).map(([k, label]) => (
                              <option key={k} value={k}>{label}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.amount')}</label>
                          <input type="number" step="0.01" value={editValues.amount} onChange={(e) => setEditValues(v => ({ ...v, amount: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.frequency')}</label>
                          <select value={editValues.frequency} onChange={(e) => setEditValues(v => ({ ...v, frequency: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded bg-background">
                            {Object.entries(FREQUENCY_LABELS).map(([k, label]) => (
                              <option key={k} value={k}>{label}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Data Inizio</label>
                          <input type="date" value={editValues.start_date} onChange={(e) => setEditValues(v => ({ ...v, start_date: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Data Fine</label>
                          <input type="date" value={editValues.end_date} onChange={(e) => setEditValues(v => ({ ...v, end_date: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold">{r.name}</span>
                          <span className="text-base font-semibold">{formatCurrency(r.amount, currency)}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
                          <Badge variant="outline" className="text-xs">{CATEGORY_LABELS[r.category] || r.category}</Badge>
                          <span>{FREQUENCY_LABELS[r.frequency] || r.frequency}</span>
                          <span>{formatDate(r.start_date)} — {r.end_date ? formatDate(r.end_date) : 'No scad.'}</span>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default FixedCostsSection;
