import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import {
  Truck, Plus, Pencil, Trash2, Search, Loader2, Info, RefreshCw, ExternalLink,
} from 'lucide-react';
import { suppliersAPI } from '../../api';
import { toast } from 'sonner';

export default function SuppliersPage() {
  const { t } = useTranslation('entities');
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [suppRes, metRes] = await Promise.all([
        suppliersAPI.list(false),
        suppliersAPI.getMetrics().catch(() => ({ data: { metrics: {} } })),
      ]);
      setItems(suppRes.data || []);
      setMetrics(metRes.data?.metrics || {});
    } catch { /* empty */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(s => s.name?.toLowerCase().includes(q) || s.category?.toLowerCase().includes(q));
  }, [items, search]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', external_id: '', email: '', phone: '', address: '', category: '' });
    setDialogOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      name: item.name || '', external_id: item.external_id || '',
      email: item.email || '', phone: item.phone || '',
      address: item.address || '', category: item.category || '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name?.trim()) return;
    setSaving(true);
    try {
      const data = {
        name: form.name.trim(),
        external_id: form.external_id?.trim() || null,
        email: form.email?.trim() || null,
        phone: form.phone?.trim() || null,
        address: form.address?.trim() || null,
        category: form.category?.trim() || null,
      };
      if (editing) { await suppliersAPI.update(editing.id, data); }
      else { await suppliersAPI.create(data); }
      toast.success(t('suppliers.save_success'));
      setDialogOpen(false);
      load();
    } catch { toast.error(t('suppliers.save_error')); }
    finally { setSaving(false); }
  };

  const handleDeactivate = async (item) => {
    if (!window.confirm(t('suppliers.deactivate_confirm'))) return;
    try { await suppliersAPI.deactivate(item.id); toast.success(t('suppliers.delete_success')); load(); }
    catch { toast.error(t('suppliers.delete_error')); }
  };

  return (
    <AppLayout>
      <Header title={t('suppliers.title')} subtitle={t('suppliers.subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={load}
              className="gap-1 shrink-0"
              aria-label={t('suppliers.refresh', { defaultValue: 'Refresh' })}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={openCreate} className="gap-1.5">
              <Plus className="h-4 w-4" /> {t('suppliers.add')}
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 space-y-4 max-w-7xl mx-auto">
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm text-blue-800">
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" /><p>{t('suppliers.guide')}</p>
        </div>

        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder={t('suppliers.search')} value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>

        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Truck className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <h3 className="font-semibold">{t('suppliers.empty')}</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md">{t('suppliers.empty_desc')}</p>
            <Button className="mt-4" onClick={openCreate}><Plus className="h-4 w-4 mr-2" />{t('suppliers.add')}</Button>
          </div>
        ) : (
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b bg-muted/30">
                  <th className="text-left px-4 py-3 font-medium">{t('suppliers.name')}</th>
                  <th className="text-right px-4 py-3 font-medium hidden sm:table-cell">{t('suppliers.total_spend')}</th>
                  <th className="text-right px-4 py-3 font-medium hidden md:table-cell">{t('suppliers.purchase_count')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">{t('suppliers.last_purchase')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">{t('suppliers.category')}</th>
                  <th className="text-center px-4 py-3 font-medium">{t('suppliers.status')}</th>
                  <th className="px-4 py-3 w-20"></th>
                </tr></thead>
                <tbody>
                  {filtered.map(s => {
                    const m = metrics[s.id] || {};
                    return (
                    <tr key={s.id} className="border-b last:border-0 hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">
                        {s.name}
                        {m.top_categories?.length > 0 && (
                          <p className="text-[11px] text-muted-foreground mt-0.5">{m.top_categories.join(', ')}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right hidden sm:table-cell font-mono">
                        {m.total_spend ? `€ ${m.total_spend.toLocaleString('it-IT', { minimumFractionDigits: 2 })}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right text-muted-foreground hidden md:table-cell">{m.purchase_count || '-'}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden lg:table-cell">{m.last_purchase || '-'}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden lg:table-cell">{s.category || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge className={s.is_active !== false ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}>
                          {s.is_active !== false ? t('suppliers.active') : t('suppliers.inactive')}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 justify-end">
                          {m.purchase_count > 0 && (
                            <button onClick={() => navigate(`/modules/cashflow/data/purchases?supplier_id=${s.id}`)} className="p-1.5 rounded hover:bg-blue-100 text-blue-600" title={t('suppliers.view_purchases')}>
                              <ExternalLink className="h-3.5 w-3.5" />
                            </button>
                          )}
                          <button onClick={() => openEdit(s)} className="p-1.5 rounded hover:bg-muted"><Pencil className="h-3.5 w-3.5" /></button>
                          {s.is_active !== false && (
                            <button onClick={() => handleDeactivate(s)} className="p-1.5 rounded hover:bg-destructive/10 hover:text-destructive"><Trash2 className="h-3.5 w-3.5" /></button>
                          )}
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>{editing ? t('suppliers.edit') : t('suppliers.add')}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div><Label>{t('suppliers.name')} *</Label><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>{t('suppliers.external_id')}</Label><Input value={form.external_id} onChange={e => setForm({...form, external_id: e.target.value})} placeholder={t('suppliers.external_id_placeholder')} /></div>
              <div><Label>{t('suppliers.category')}</Label><Input value={form.category} onChange={e => setForm({...form, category: e.target.value})} placeholder={t('suppliers.category_placeholder')} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>{t('suppliers.email')}</Label><Input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></div>
              <div><Label>{t('suppliers.phone')}</Label><Input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
            </div>
            <div><Label>{t('suppliers.address')}</Label><Input value={form.address} onChange={e => setForm({...form, address: e.target.value})} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('suppliers.cancel')}</Button>
            <Button onClick={handleSave} disabled={saving || !form.name?.trim()}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editing ? t('suppliers.save') : t('suppliers.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
