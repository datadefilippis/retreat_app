import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Trash2, RefreshCw, Pencil, Check, X, Filter, RotateCcw } from 'lucide-react';
import { expensesAPI } from '../../api';
// Phase 2 (2026-05-20) — server-side filter + pagination. Drop-in
// replacement for useCashflowFilters; see SalesSection.js for the
// migration pattern note.
import { useCashflowQuery } from './hooks/useCashflowQuery';
import CashflowFilterPopup from './components/CashflowFilterPopup';
import { CashflowPagination } from './components/CashflowPagination';
import { formatCurrency, formatDate } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { ExpensesEntryForm } from './ExpensesEntryForm';
import { CreatableAutocomplete } from '../../components/CreatableAutocomplete';

export const ExpensesSection = () => {
  const { t } = useTranslation('cashflow_monitor');
  const currency = useCurrency();
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [supplierOptions, setSupplierOptions] = useState([]);
  const [filterOpen, setFilterOpen] = useState(false);

  // Phase 2 — server-side filter + pagination (50 rows/page).
  const {
    filters,
    setFilters,
    items,
    total,
    hasMore,
    page,
    setPage,
    pageSize,
    loading,
    activeCount,
    reset: resetFilters,
    refetch,
  } = useCashflowQuery({ categoryType: 'expenses', api: expensesAPI });

  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const [catRes, suppRes] = await Promise.all([
          expensesAPI.getCategories(),
          expensesAPI.getSuppliers(),
        ]);
        setCategoryOptions(catRes.data || []);
        setSupplierOptions(suppRes.data || []);
      } catch { /* silent */ }
    };
    loadSuggestions();
  }, []);

  const handleDelete = async (id) => {
    try {
      await expensesAPI.delete(id);
      // See SalesSection: refetch keeps the total counter accurate.
      await refetch();
      toast.success(t('toast.expense_deleted'));
    } catch {
      toast.error(t('toast.delete_error'));
    }
  };

  const startEdit = (r) => {
    setEditingId(r.id);
    setEditValues({
      date: r.date || '',
      amount: r.amount || 0,
      category: r.category || '',
      description: r.description || '',
      supplier: r.supplier || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSave = async () => {
    try {
      const original = items.find(r => r.id === editingId);
      if (!original) {
        cancelEdit();
        return;
      }
      const updates = {};
      if (editValues.date !== (original.date || '')) updates.date = editValues.date;
      if (Number(editValues.amount) !== (original.amount || 0)) updates.amount = Number(editValues.amount);
      if (editValues.category !== (original.category || '')) updates.category = editValues.category;
      if (editValues.description !== (original.description || '')) updates.description = editValues.description;
      if (editValues.supplier !== (original.supplier || '')) updates.supplier = editValues.supplier;

      if (Object.keys(updates).length === 0) {
        cancelEdit();
        return;
      }

      await expensesAPI.update(editingId, updates);
      await refetch();
      toast.success(t('toast.record_updated'));
      cancelEdit();
    } catch {
      toast.error(t('toast.update_error'));
    }
  };

  const isEditing = (id) => editingId === id;

  return (
    <div className="space-y-6">
      <Tabs defaultValue="manual">
        <TabsList>
          <TabsTrigger value="manual">{t('sections.tab_manual')}</TabsTrigger>
        </TabsList>
        <TabsContent value="manual" className="mt-4">
          <ExpensesEntryForm onSaved={refetch} />
        </TabsContent>
      </Tabs>

      {/* Records table */}
      <Card className="border border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3 gap-2">
          <CardTitle className="text-base font-heading">
            Uscite Registrate ({total})
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
            <Button variant="ghost" size="sm" onClick={refetch} aria-label={t('sections.refresh', { defaultValue: 'Refresh' })}>
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CashflowFilterPopup
          open={filterOpen}
          onOpenChange={setFilterOpen}
          categoryType="expenses"
          value={filters}
          onChange={setFilters}
          onReset={resetFilters}
          options={{ categories: categoryOptions, suppliers: supplierOptions }}
          activeCount={activeCount}
        />
        <CardContent>
          {loading && items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.loading')}</div>
          ) : total === 0 && activeCount === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.empty_expenses')}</div>
          ) : total === 0 && activeCount > 0 ? (
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
                      <th className="pb-2 pr-3">{t('forms.date')}</th>
                      <th className="pb-2 pr-3">{t('forms.amount')}</th>
                      <th className="pb-2 pr-3">{t('forms.category')}</th>
                      <th className="pb-2 pr-3">{t('forms.description')}</th>
                      <th className="pb-2 pr-3">{t('forms.supplier')}</th>
                      <th className="pb-2 pr-3">{t('sections.source')}</th>
                      <th className="pb-2 w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((r) => (
                      <tr key={r.id} className={`border-b last:border-0 ${isEditing(r.id) ? 'bg-primary/5' : 'hover:bg-muted/50'}`}>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="date" value={editValues.date} onChange={(e) => setEditValues(v => ({ ...v, date: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-32" />
                          ) : formatDate(r.date)}
                        </td>
                        <td className="py-2 pr-3 font-medium">
                          {isEditing(r.id) ? (
                            <input type="number" step="0.01" value={editValues.amount} onChange={(e) => setEditValues(v => ({ ...v, amount: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-24" />
                          ) : formatCurrency(r.amount, currency)}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <CreatableAutocomplete value={editValues.category} onChange={(val) => setEditValues(v => ({ ...v, category: val }))} options={categoryOptions} placeholder="Categoria" className="h-7 text-sm w-28" />
                          ) : (
                            r.category && <Badge variant="outline" className="text-xs">{r.category}</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3 text-muted-foreground">
                          {isEditing(r.id) ? (
                            <input type="text" value={editValues.description} onChange={(e) => setEditValues(v => ({ ...v, description: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-full" />
                          ) : (r.description || '-')}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <CreatableAutocomplete value={editValues.supplier} onChange={(val) => setEditValues(v => ({ ...v, supplier: val }))} options={supplierOptions} placeholder="Fornitore" className="h-7 text-sm w-28" />
                          ) : (r.supplier || '-')}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge variant="secondary" className="text-xs">
                            {r.source_label || (r.dataset_id === 'manual' ? t('sections.source_manual') : t('sections.source_file'))}
                          </Badge>
                        </td>
                        <td className="py-2">
                          {isEditing(r.id) ? (
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
                {items.map((r) => (
                  <div key={r.id} className={`rounded-xl border p-4 space-y-2 ${isEditing(r.id) ? 'bg-primary/5 border-primary/20' : 'bg-muted/30'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{formatDate(r.date)}</span>
                      <div className="flex items-center gap-1">
                        <Badge variant="secondary" className="text-[10px]">
                          {r.source_label || (r.dataset_id === 'manual' ? t('sections.source_manual') : t('sections.source_file'))}
                        </Badge>
                        {isEditing(r.id) ? (
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
                    {isEditing(r.id) ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Data</label>
                          <input type="date" value={editValues.date} onChange={(e) => setEditValues(v => ({ ...v, date: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Importo</label>
                          <input type="number" step="0.01" value={editValues.amount} onChange={(e) => setEditValues(v => ({ ...v, amount: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Categoria</label>
                          <CreatableAutocomplete value={editValues.category} onChange={(val) => setEditValues(v => ({ ...v, category: val }))} options={categoryOptions} placeholder="Categoria" className="h-10 w-full text-sm" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Fornitore</label>
                          <CreatableAutocomplete value={editValues.supplier} onChange={(val) => setEditValues(v => ({ ...v, supplier: val }))} options={supplierOptions} placeholder="Fornitore" className="h-10 w-full text-sm" />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Descrizione</label>
                          <input type="text" value={editValues.description} onChange={(e) => setEditValues(v => ({ ...v, description: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-base font-semibold">{formatCurrency(r.amount, currency)}</span>
                          {r.supplier && <span className="text-xs text-muted-foreground">{r.supplier}</span>}
                        </div>
                        {(r.category || r.description) && (
                          <div className="flex items-center gap-2 flex-wrap">
                            {r.category && <Badge variant="outline" className="text-xs">{r.category}</Badge>}
                            {r.description && <span className="text-xs text-muted-foreground truncate">{r.description}</span>}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>

              <CashflowPagination
                total={total}
                page={page}
                pageSize={pageSize}
                hasMore={hasMore}
                loading={loading}
                onChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ExpensesSection;
