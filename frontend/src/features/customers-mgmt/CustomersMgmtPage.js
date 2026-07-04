import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import {
  Users, Plus, Pencil, Trash2, Search, Loader2, Info, RefreshCw,
} from 'lucide-react';
import { customersAPI } from '../../api';
import { toast } from 'sonner';

export default function CustomersMgmtPage() {
  const { t } = useTranslation('entities');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await customersAPI.list(false);
      setItems(res.data || []);
    } catch { /* empty */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(c => c.name?.toLowerCase().includes(q) || c.email?.toLowerCase().includes(q));
  }, [items, search]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', external_id: '', email: '', phone: '', address: '' });
    setDialogOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      name: item.name || '', external_id: item.external_id || '',
      email: item.email || '', phone: item.phone || '', address: item.address || '',
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
      };
      if (editing) { await customersAPI.update(editing.id, data); }
      else { await customersAPI.create(data); }
      toast.success(t('customers.save_success'));
      setDialogOpen(false);
      load();
    } catch { toast.error(t('customers.save_error')); }
    finally { setSaving(false); }
  };

  const handleDeactivate = async (item) => {
    if (!window.confirm(t('customers.deactivate_confirm'))) return;
    try { await customersAPI.deactivate(item.id); toast.success(t('customers.delete_success')); load(); }
    catch { toast.error(t('customers.delete_error')); }
  };

  return (
    <AppLayout>
      <Header title={t('customers.title')} subtitle={t('customers.subtitle')}>
        <Button variant="outline" size="sm" onClick={load} className="gap-1"><RefreshCw className="h-4 w-4" /></Button>
        <Button size="sm" onClick={openCreate} className="gap-2"><Plus className="h-4 w-4" /> {t('customers.add')}</Button>
      </Header>

      <div className="p-4 md:p-6 space-y-4 max-w-7xl mx-auto">
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm text-blue-800">
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" /><p>{t('customers.guide')}</p>
        </div>

        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder={t('customers.search')} value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>

        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <h3 className="font-semibold">{t('customers.empty')}</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md">{t('customers.empty_desc')}</p>
            <Button className="mt-4" onClick={openCreate}><Plus className="h-4 w-4 mr-2" />{t('customers.add')}</Button>
          </div>
        ) : (
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b bg-muted/30">
                  <th className="text-left px-4 py-3 font-medium">{t('customers.name')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden md:table-cell">{t('customers.external_id')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">{t('customers.email')}</th>
                  <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">{t('customers.phone')}</th>
                  <th className="text-center px-4 py-3 font-medium">{t('customers.status')}</th>
                  <th className="px-4 py-3 w-20"></th>
                </tr></thead>
                <tbody>
                  {filtered.map(c => (
                    <tr key={c.id} className="border-b last:border-0 hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{c.name}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">{c.external_id || '-'}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">{c.email || '-'}</td>
                      <td className="px-4 py-3 text-muted-foreground hidden lg:table-cell">{c.phone || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge className={c.is_active !== false ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}>
                          {c.is_active !== false ? t('customers.active') : t('customers.inactive')}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 justify-end">
                          <button onClick={() => openEdit(c)} className="p-1.5 rounded hover:bg-muted"><Pencil className="h-3.5 w-3.5" /></button>
                          {c.is_active !== false && (
                            <button onClick={() => handleDeactivate(c)} className="p-1.5 rounded hover:bg-destructive/10 hover:text-destructive"><Trash2 className="h-3.5 w-3.5" /></button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>{editing ? t('customers.edit') : t('customers.add')}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div><Label>{t('customers.name')} *</Label><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div><Label>{t('customers.external_id')}</Label><Input value={form.external_id} onChange={e => setForm({...form, external_id: e.target.value})} placeholder="es. CL-001" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>{t('customers.email')}</Label><Input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></div>
              <div><Label>{t('customers.phone')}</Label><Input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
            </div>
            <div><Label>{t('customers.address')}</Label><Input value={form.address} onChange={e => setForm({...form, address: e.target.value})} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Annulla</Button>
            <Button onClick={handleSave} disabled={saving || !form.name?.trim()}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editing ? 'Salva' : 'Crea'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
