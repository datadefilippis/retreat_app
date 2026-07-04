import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Trash2, RefreshCw, Pencil, Check, X, Filter, RotateCcw } from 'lucide-react';
import { purchasesAPI } from '../../api';
// Phase 2 — server-side filter + pagination. ``supplierId`` from the
// parent page (CashflowDataPage) becomes an ``extraParams`` constraint
// passed to the hook, ensuring every query stays scoped to the
// supplier even when the user touches no filter in the popup.
import { useCashflowQuery } from './hooks/useCashflowQuery';
import CashflowFilterPopup from './components/CashflowFilterPopup';
import { CashflowPagination } from './components/CashflowPagination';
import { formatCurrency, formatDate } from '../../lib/utils';
import { parseLocaleNumber } from '../../lib/parseLocaleNumber';
import { useCurrency } from '../../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { CreatableAutocomplete } from '../../components/CreatableAutocomplete';

const IVA_DEFAULT_OPTIONS = ['22', '10', '4', '0'];

const PAYMENT_STATUSES = [
  { value: '', label: '—' },
  { value: 'pending', label: 'In attesa' },
  { value: 'paid', label: 'Pagato' },
  { value: 'overdue', label: 'Scaduto' },
];

const statusBadgeVariant = (s) => {
  if (s === 'paid') return 'default';
  if (s === 'overdue') return 'destructive';
  if (s === 'pending') return 'secondary';
  return 'outline';
};

const statusLabel = (s) => {
  const found = PAYMENT_STATUSES.find(ps => ps.value === s);
  return found ? found.label : s || '—';
};
import { toast } from 'sonner';
import { PurchaseEntryForm } from './PurchaseEntryForm';
import { ModuleDatasetManager } from '../../components/ModuleDatasetManager';

const UNITS = ['kg', 'pezzi', 'metri', 'litri'];

export const PurchasesSection = ({ supplierId = null }) => {
  const { t } = useTranslation('cashflow_monitor');
  const currency = useCurrency();
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [supplierOptions, setSupplierOptions] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [categoryMacroOptions, setCategoryMacroOptions] = useState([]);
  const [filterOpen, setFilterOpen] = useState(false);

  // Page-level scope: when the page is opened with a ?supplier_id=X
  // URL param, restrict every query to that supplier. Memoised so the
  // hook's fetch effect doesn't refire on every render (the hook's
  // dependency array includes extraParams). null = no scope.
  const extraParams = useMemo(
    () => (supplierId ? { supplierIds: [supplierId] } : undefined),
    [supplierId],
  );

  // Phase 2 — server-side filter + pagination. The popup binds to
  // the same ``filters`` / ``setFilters`` as before; predicates run
  // in Mongo instead of RAM.
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
  } = useCashflowQuery({
    categoryType: 'purchases',
    api: purchasesAPI,
    extraParams,
  });

  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const [suppRes, catRes, macroRes] = await Promise.all([
          purchasesAPI.getSuppliers(),
          purchasesAPI.getCategories(),
          purchasesAPI.getCategoriesMacro(),
        ]);
        setSupplierOptions(suppRes.data || []);
        setCategoryOptions(catRes.data || []);
        setCategoryMacroOptions(macroRes.data || []);
      } catch { /* silent */ }
    };
    loadSuggestions();
  }, []);

  const handleDelete = async (id) => {
    try {
      await purchasesAPI.delete(id);
      // Refetch keeps total accurate. See SalesSection for rationale.
      await refetch();
      toast.success(t('toast.purchase_deleted'));
    } catch {
      toast.error(t('toast.delete_error'));
    }
  };

  const startEdit = (r) => {
    setEditingId(r.id);
    setEditValues({
      date: r.date || '',
      supplier_name: r.supplier_name || '',
      quantity: r.quantity || 0,
      unit: r.unit || 'kg',
      unit_price: r.unit_price || 0,
      iva: r.iva != null ? String(r.iva) : '',
      category: r.category || '',
      category_macro: r.category_macro || '',
      description: r.description || '',
      invoice_number: r.invoice_number || '',
      due_date: r.due_date || '',
      payment_status: r.payment_status || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const editTotalPrice = () => {
    const qty = Number(editValues.quantity) || 0;
    const price = Number(editValues.unit_price) || 0;
    return qty * price;
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
      if (editValues.supplier_name !== (original.supplier_name || '')) updates.supplier_name = editValues.supplier_name;
      if (Number(editValues.quantity) !== (original.quantity || 0)) updates.quantity = Number(editValues.quantity);
      if (editValues.unit !== (original.unit || 'kg')) updates.unit = editValues.unit;
      if (Number(editValues.unit_price) !== (original.unit_price || 0)) updates.unit_price = Number(editValues.unit_price);
      // IVA: parse with locale tolerance, compare with null-awareness
      const parsedIva = editValues.iva !== '' && editValues.iva != null ? parseLocaleNumber(editValues.iva) : null;
      const newIva = parsedIva != null && !isNaN(parsedIva) ? parsedIva : null;
      const oldIva = original.iva ?? null;
      if (newIva !== oldIva) updates.iva = newIva;
      if (editValues.category !== (original.category || '')) updates.category = editValues.category || null;
      if (editValues.category_macro !== (original.category_macro || '')) updates.category_macro = editValues.category_macro || null;
      if (editValues.description !== (original.description || '')) updates.description = editValues.description || null;
      if (editValues.invoice_number !== (original.invoice_number || '')) updates.invoice_number = editValues.invoice_number || null;
      if (editValues.due_date !== (original.due_date || '')) updates.due_date = editValues.due_date || null;
      if (editValues.payment_status !== (original.payment_status || '')) updates.payment_status = editValues.payment_status || null;

      if (Object.keys(updates).length === 0) {
        cancelEdit();
        return;
      }

      await purchasesAPI.update(editingId, updates);
      // Refetch — total_price and total_with_iva are server-recomputed
      // on the patch (purchases router lines 130-157), so refetching
      // brings the canonical values back without re-doing the math here.
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
          <TabsTrigger value="import">{t('sections.tab_import')}</TabsTrigger>
        </TabsList>
        <TabsContent value="manual" className="mt-4">
          <PurchaseEntryForm onSaved={refetch} />
        </TabsContent>
        <TabsContent value="import" className="mt-4">
          <ModuleDatasetManager datasetType="purchases" onUploadComplete={refetch} />
        </TabsContent>
      </Tabs>

      {/* Records table */}
      <Card className="border border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3 gap-2">
          <CardTitle className="text-base font-heading">
            Acquisti Registrati ({total})
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
          categoryType="purchases"
          value={filters}
          onChange={setFilters}
          onReset={resetFilters}
          options={{
            suppliers: supplierOptions,
            categories: categoryOptions,
            categories_macro: categoryMacroOptions,
          }}
          activeCount={activeCount}
        />
        <CardContent>
          {loading && items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.loading')}</div>
          ) : total === 0 && activeCount === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.empty_purchases')}</div>
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
                      <th className="pb-2 pr-3">{t('forms.supplier')}</th>
                      <th className="pb-2 pr-3">{t('forms.quantity')}</th>
                      <th className="pb-2 pr-3">{t('forms.unit')}</th>
                      <th className="pb-2 pr-3">{t('forms.unit_price')}</th>
                      <th className="pb-2 pr-3">{t('forms.total')}</th>
                      <th className="pb-2 pr-3" title={t('forms.iva_tooltip')}>{t('forms.iva')}</th>
                      <th className="pb-2 pr-3" title={t('forms.total_with_iva_tooltip')}>{t('forms.total_with_iva')}</th>
                      <th className="pb-2 pr-3" title={t('forms.product_tooltip')}>{t('forms.product')}</th>
                      <th className="pb-2 pr-3" title={t('forms.purchase_category_tooltip')}>{t('forms.purchase_category')}</th>
                      <th className="pb-2 pr-3">Descrizione</th>
                      <th className="pb-2 pr-3">N. Fattura</th>
                      <th className="pb-2 pr-3">{t('forms.due_date')}</th>
                      <th className="pb-2 pr-3">{t('forms.payment_status')}</th>
                      <th className="pb-2 pr-3">Fonte</th>
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
                            <CreatableAutocomplete value={editValues.supplier_name} onChange={(val) => setEditValues(v => ({ ...v, supplier_name: val }))} options={supplierOptions} placeholder="Fornitore" className="h-7 text-sm w-28" />
                          ) : r.supplier_name}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="number" step="0.01" value={editValues.quantity} onChange={(e) => setEditValues(v => ({ ...v, quantity: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-16" />
                          ) : r.quantity}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <select value={editValues.unit} onChange={(e) => setEditValues(v => ({ ...v, unit: e.target.value }))} className="h-7 px-1 text-sm border rounded w-20">
                              {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                            </select>
                          ) : r.unit}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="number" step="0.01" value={editValues.unit_price} onChange={(e) => setEditValues(v => ({ ...v, unit_price: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-20" />
                          ) : formatCurrency(r.unit_price, currency)}
                        </td>
                        <td className="py-2 pr-3 font-medium">
                          {isEditing(r.id) ? (
                            <span className="text-muted-foreground">{formatCurrency(editTotalPrice(), currency)}</span>
                          ) : formatCurrency(r.total_price, currency)}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <CreatableAutocomplete value={editValues.iva != null ? String(editValues.iva) : ''} onChange={(val) => setEditValues(v => ({ ...v, iva: val }))} options={IVA_DEFAULT_OPTIONS} placeholder="—" className="h-7 text-sm w-16" />
                          ) : (r.iva != null ? `${r.iva}%` : '—')}
                        </td>
                        <td className="py-2 pr-3 text-muted-foreground">
                          {isEditing(r.id) ? (
                            (() => {
                              const ivaNum = editValues.iva ? parseLocaleNumber(editValues.iva) : null;
                              return ivaNum != null && !isNaN(ivaNum)
                                ? <span>{formatCurrency(editTotalPrice() * (1 + ivaNum / 100), currency)}</span>
                                : <span>—</span>;
                            })()
                          ) : (r.total_with_iva != null ? formatCurrency(r.total_with_iva, currency) : '—')}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <CreatableAutocomplete value={editValues.category} onChange={(val) => setEditValues(v => ({ ...v, category: val }))} options={categoryOptions} placeholder="Prodotto" className="h-7 text-sm w-24" />
                          ) : (
                            r.category && <Badge variant="outline" className="text-xs">{r.category}</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <CreatableAutocomplete value={editValues.category_macro} onChange={(val) => setEditValues(v => ({ ...v, category_macro: val }))} options={categoryMacroOptions} placeholder="Categoria" className="h-7 text-sm w-24" />
                          ) : (
                            r.category_macro && <Badge variant="outline" className="text-xs">{r.category_macro}</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="text" value={editValues.description} onChange={(e) => setEditValues(v => ({ ...v, description: e.target.value }))} placeholder="—" className="h-7 px-1.5 text-sm border rounded w-28" />
                          ) : (r.description || '—')}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="text" value={editValues.invoice_number} onChange={(e) => setEditValues(v => ({ ...v, invoice_number: e.target.value }))} placeholder="—" className="h-7 px-1.5 text-sm border rounded w-24" />
                          ) : (r.invoice_number || '—')}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <input type="date" value={editValues.due_date} onChange={(e) => setEditValues(v => ({ ...v, due_date: e.target.value }))} className="h-7 px-1.5 text-sm border rounded w-32" />
                          ) : (r.due_date ? formatDate(r.due_date) : '—')}
                        </td>
                        <td className="py-2 pr-3">
                          {isEditing(r.id) ? (
                            <select value={editValues.payment_status} onChange={(e) => setEditValues(v => ({ ...v, payment_status: e.target.value }))} className="h-7 px-1 text-sm border rounded w-24 bg-background">
                              {PAYMENT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                            </select>
                          ) : (
                            r.payment_status && <Badge variant={statusBadgeVariant(r.payment_status)} className="text-xs">{statusLabel(r.payment_status)}</Badge>
                          )}
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
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">{formatDate(r.date)}</span>
                        <Badge variant="secondary" className="text-[10px]">
                          {r.source_label || (r.dataset_id === 'manual' ? t('sections.source_manual') : t('sections.source_file'))}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1">
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
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.supplier')}</label>
                          <input type="text" value={editValues.supplier_name} onChange={(e) => setEditValues(v => ({ ...v, supplier_name: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Quantita</label>
                          <input type="number" step="0.01" value={editValues.quantity} onChange={(e) => setEditValues(v => ({ ...v, quantity: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Unita</label>
                          <select value={editValues.unit} onChange={(e) => setEditValues(v => ({ ...v, unit: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded bg-background">
                            {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.unit_price')}</label>
                          <input type="number" step="0.01" value={editValues.unit_price} onChange={(e) => setEditValues(v => ({ ...v, unit_price: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.product')}</label>
                          <input type="text" value={editValues.category} onChange={(e) => setEditValues(v => ({ ...v, category: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.due_date')}</label>
                          <input type="date" value={editValues.due_date} onChange={(e) => setEditValues(v => ({ ...v, due_date: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.payment_status')}</label>
                          <select value={editValues.payment_status} onChange={(e) => setEditValues(v => ({ ...v, payment_status: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded bg-background">
                            {PAYMENT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                          </select>
                        </div>
                        <div className="overflow-visible">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.iva_percent', 'IVA %')}</label>
                          <CreatableAutocomplete value={editValues.iva != null ? String(editValues.iva) : ''} onChange={(val) => setEditValues(v => ({ ...v, iva: val }))} options={IVA_DEFAULT_OPTIONS} placeholder="—" className="h-10 text-sm w-full" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block" title={t('forms.category_macro_tooltip', '')}>{t('forms.purchase_category', 'Categoria')}</label>
                          <input type="text" value={editValues.category_macro ?? ''} onChange={(e) => setEditValues(v => ({ ...v, category_macro: e.target.value }))} placeholder="Categoria" className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.description', 'Descrizione')}</label>
                          <input type="text" value={editValues.description ?? ''} onChange={(e) => setEditValues(v => ({ ...v, description: e.target.value }))} placeholder="Descrizione" className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.invoice_number', 'N. Fattura')}</label>
                          <input type="text" value={editValues.invoice_number ?? ''} onChange={(e) => setEditValues(v => ({ ...v, invoice_number: e.target.value }))} placeholder="N. Fattura" className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div className="col-span-2 flex justify-between items-center">
                          <div>
                            <span className="text-xs text-muted-foreground">{t('forms.total_label')}</span>{' '}
                            <span className="text-sm font-semibold">{formatCurrency(editTotalPrice(), currency)}</span>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground">{t('forms.total_with_iva', 'Tot. IVA')}</span>{' '}
                            <span className="text-sm font-semibold">
                              {(() => {
                                const ivaNum = parseFloat(editValues.iva);
                                return !isNaN(ivaNum) && ivaNum > 0
                                  ? formatCurrency(editTotalPrice() * (1 + ivaNum / 100), currency)
                                  : '—';
                              })()}
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{r.supplier_name}</span>
                          <span className="text-base font-semibold">{formatCurrency(r.total_price, currency)}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{r.quantity} {r.unit}</span>
                          <span>@ {formatCurrency(r.unit_price, currency)}</span>
                          {r.category && <Badge variant="outline" className="text-xs">{r.category}</Badge>}
                        </div>
                        {(r.due_date || r.payment_status) && (
                          <div className="flex items-center gap-2 flex-wrap">
                            {r.due_date && <span className="text-xs text-muted-foreground">Scad: {formatDate(r.due_date)}</span>}
                            {r.payment_status && <Badge variant={statusBadgeVariant(r.payment_status)} className="text-xs">{statusLabel(r.payment_status)}</Badge>}
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

export default PurchasesSection;
