import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Trash2, RefreshCw, Pencil, Check, X, Filter, RotateCcw } from 'lucide-react';
import { salesAPI } from '../../api';
// Phase 2 (2026-05-20) — server-side filter + pagination. The hook
// owns ``filters`` (drives the popup), ``items``/``total``/``page``
// (the displayed slice), and async lifecycle. Migration from the
// previous client-side ``useCashflowFilters`` is data-source-only —
// the popup component, inline edit, and table layout are unchanged.
import { useCashflowQuery } from './hooks/useCashflowQuery';
import CashflowFilterPopup from './components/CashflowFilterPopup';
import { CashflowPagination } from './components/CashflowPagination';
import { formatCurrency, formatDate } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { CreatableAutocomplete } from '../../components/CreatableAutocomplete';

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
import { SalesEntryForm } from './SalesEntryForm';
import { ModuleDatasetManager } from '../../components/ModuleDatasetManager';

export const SalesSection = () => {
  const { t } = useTranslation('cashflow_monitor');
  const currency = useCurrency();
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [channelOptions, setChannelOptions] = useState([]);
  const [filterOpen, setFilterOpen] = useState(false);

  // Phase 2 — server-side filter + pagination. Drop-in replacement
  // for useCashflowFilters: the popup binds to the same ``filters`` /
  // ``setFilters``, but the predicate evaluation happens in Mongo
  // against the indexed collection rather than client-side.
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
  } = useCashflowQuery({ categoryType: 'sales', api: salesAPI });

  // Autocomplete options for inline edit + filter popup. These come
  // from category/channel-distinct endpoints and don't depend on the
  // current paginated slice, so we fetch them once on mount.
  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const [catRes, chRes] = await Promise.all([
          salesAPI.getCategories(),
          salesAPI.getChannels(),
        ]);
        setCategoryOptions(catRes.data || []);
        setChannelOptions(chRes.data || []);
      } catch { /* silent */ }
    };
    loadSuggestions();
  }, []);

  const handleDelete = async (id) => {
    try {
      await salesAPI.delete(id);
      // Refetch the current page from the server — total may have
      // dropped and the page contents shift up by one row. Doing it
      // server-side keeps the total counter accurate (an optimistic
      // local splice would leave the counter stale until next fetch).
      await refetch();
      toast.success(t('toast.sale_deleted'));
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
      channel: r.channel || '',
      due_date: r.due_date || '',
      payment_status: r.payment_status || '',
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
      if (editValues.channel !== (original.channel || '')) updates.channel = editValues.channel;
      if (editValues.due_date !== (original.due_date || '')) updates.due_date = editValues.due_date || null;
      if (editValues.payment_status !== (original.payment_status || '')) updates.payment_status = editValues.payment_status || null;

      if (Object.keys(updates).length === 0) {
        cancelEdit();
        return;
      }

      await salesAPI.update(editingId, updates);
      // Refetch so the updated row reflects backend state (especially
      // important if the patch changes a filter-relevant field — e.g.
      // changing payment_status with a payment_status filter active
      // could legitimately move the row off the current page).
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
          <SalesEntryForm onSaved={refetch} />
        </TabsContent>
        <TabsContent value="import" className="mt-4">
          <ModuleDatasetManager datasetType="sales" onUploadComplete={refetch} />
        </TabsContent>
      </Tabs>

      {/* Records table */}
      <Card className="border border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3 gap-2">
          <CardTitle className="text-base font-heading">
            {/* total is server-authoritative: when filters are active
                it's the count matching them, when none are active it's
                the org total. No more "filtered/all" double counter
                because the server doesn't return the unfiltered total
                in the same payload (one extra round-trip would be
                more cost than the visual benefit). */}
            Entrate Registrate ({total})
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
            {/* Reset button — rendered only when at least one filter is
                active. Sibling to the Filter trigger so the user clears
                everything without opening the popup first. */}
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
          categoryType="sales"
          value={filters}
          onChange={setFilters}
          onReset={resetFilters}
          options={{ categories: categoryOptions, channels: channelOptions }}
          activeCount={activeCount}
        />
        <CardContent>
          {loading && items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.loading')}</div>
          ) : total === 0 && activeCount === 0 ? (
            // Truly empty: the org has no sales records at all.
            <div className="text-center py-8 text-muted-foreground text-sm">{t('sections.empty_sales')}</div>
          ) : total === 0 && activeCount > 0 ? (
            // Filters active but no row matches: offer a one-click reset
            // so the merchant never feels trapped in an empty grid.
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
                      <th className="pb-2 pr-3">{t('forms.channel')}</th>
                      <th className="pb-2 pr-3">{t('forms.due_date')}</th>
                      <th className="pb-2 pr-3">{t('forms.payment_status')}</th>
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
                            <CreatableAutocomplete value={editValues.channel} onChange={(val) => setEditValues(v => ({ ...v, channel: val }))} options={channelOptions} placeholder="Canale" className="h-7 text-sm w-24" />
                          ) : (
                            r.channel && <Badge variant="secondary" className="text-xs">{r.channel}</Badge>
                          )}
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
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">{t('forms.date')}</label>
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
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Canale</label>
                          <CreatableAutocomplete value={editValues.channel} onChange={(val) => setEditValues(v => ({ ...v, channel: val }))} options={channelOptions} placeholder="Canale" className="h-10 w-full text-sm" />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Descrizione</label>
                          <input type="text" value={editValues.description} onChange={(e) => setEditValues(v => ({ ...v, description: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Scadenza</label>
                          <input type="date" value={editValues.due_date} onChange={(e) => setEditValues(v => ({ ...v, due_date: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded" />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-1 block">Stato Pag.</label>
                          <select value={editValues.payment_status} onChange={(e) => setEditValues(v => ({ ...v, payment_status: e.target.value }))} className="h-10 w-full px-2 text-sm border rounded bg-background">
                            {PAYMENT_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                          </select>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-base font-semibold">{formatCurrency(r.amount, currency)}</span>
                          {r.channel && <Badge variant="secondary" className="text-xs">{r.channel}</Badge>}
                        </div>
                        {(r.category || r.description) && (
                          <div className="flex items-center gap-2 flex-wrap">
                            {r.category && <Badge variant="outline" className="text-xs">{r.category}</Badge>}
                            {r.description && <span className="text-xs text-muted-foreground truncate">{r.description}</span>}
                          </div>
                        )}
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

              {/* Phase 2 pagination — replaces the client-side
                  "Load more" infinite-list pattern. The total counter
                  is server-authoritative; the user can jump to any
                  page within the result set. */}
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

export default SalesSection;
