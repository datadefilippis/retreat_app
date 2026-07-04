import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import { Plus, Trash2, Loader2, Tag, RefreshCw } from 'lucide-react';
import { couponsAPI } from '../../api/coupons';
import { useCurrency } from '../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../lib/utils';
import { toast } from 'sonner';

export default function CouponsPage() {
  const orgCurrency = useCurrency();
  const fmtMoney = (v) => fmtCurrency(Number(v) || 0, orgCurrency);
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ code: '', discount_pct: '', discount_amount: '', min_order_amount: '', max_uses: '', valid_from: '', valid_to: '' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await couponsAPI.list();
      setCoupons(res.data || []);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.code.trim()) return;
    if (!form.discount_pct && !form.discount_amount) {
      toast.error('Inserisci sconto percentuale o importo fisso');
      return;
    }
    setSaving(true);
    try {
      const data = {
        code: form.code.trim().toUpperCase(),
        discount_pct: form.discount_pct ? parseFloat(form.discount_pct) : null,
        discount_amount: form.discount_amount ? parseFloat(form.discount_amount) : null,
        min_order_amount: form.min_order_amount ? parseFloat(form.min_order_amount) : null,
        max_uses: form.max_uses ? parseInt(form.max_uses) : null,
        valid_from: form.valid_from || null,
        valid_to: form.valid_to || null,
      };
      await couponsAPI.create(data);
      toast.success('Coupon creato');
      setDialogOpen(false);
      setForm({ code: '', discount_pct: '', discount_amount: '', min_order_amount: '', max_uses: '', valid_from: '', valid_to: '' });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Errore nella creazione');
    } finally { setSaving(false); }
  };

  const handleToggle = async (coupon) => {
    try {
      await couponsAPI.update(coupon.id, { is_active: !coupon.is_active });
      setCoupons(prev => prev.map(c => c.id === coupon.id ? { ...c, is_active: !c.is_active } : c));
    } catch { toast.error('Errore'); }
  };

  const handleDelete = async (coupon) => {
    if (!window.confirm(`Eliminare il coupon ${coupon.code}?`)) return;
    try {
      await couponsAPI.delete(coupon.id);
      setCoupons(prev => prev.filter(c => c.id !== coupon.id));
      toast.success('Coupon eliminato');
    } catch { toast.error('Errore'); }
  };

  return (
    <AppLayout>
      <Header title="Coupon & Promozioni" subtitle="Gestisci codici sconto per il tuo storefront" />
      <PageSubheader
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={load}
              className="shrink-0"
              aria-label="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={() => setDialogOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> Nuovo Coupon
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : coupons.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <Tag className="h-12 w-12 text-muted-foreground/40 mx-auto" />
            <h3 className="font-semibold">Nessun coupon</h3>
            <p className="text-sm text-muted-foreground">Crea il tuo primo codice promo</p>
            <Button onClick={() => setDialogOpen(true)}><Plus className="h-4 w-4 mr-2" /> Nuovo Coupon</Button>
          </div>
        ) : (
          <div className="space-y-2">
            {coupons.map(c => (
              <div key={c.id} className={`rounded-xl border p-4 flex items-center justify-between ${!c.is_active ? 'opacity-50' : ''}`}>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm">{c.code}</span>
                    {c.discount_pct && <Badge className="text-[10px] bg-emerald-100 text-emerald-700">{c.discount_pct}% sconto</Badge>}
                    {c.discount_amount && <Badge className="text-[10px] bg-blue-100 text-blue-700">{fmtMoney(c.discount_amount)} sconto</Badge>}
                    {!c.is_active && <Badge className="text-[10px] bg-gray-100 text-gray-500">Disattivo</Badge>}
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    {c.max_uses && <span>Usi: {c.current_uses || 0}/{c.max_uses}</span>}
                    {c.valid_from && <span>Dal: {c.valid_from}</span>}
                    {c.valid_to && <span>Al: {c.valid_to}</span>}
                    {c.min_order_amount && <span>Min: {fmtMoney(c.min_order_amount)}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="text-xs" onClick={() => handleToggle(c)}>
                    {c.is_active ? 'Disattiva' : 'Attiva'}
                  </Button>
                  <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(c)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nuovo Coupon</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Codice *</Label>
              <Input value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))}
                placeholder="Es: SUMMER2026" maxLength={30} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Sconto %</Label>
                <Input type="number" step="1" min="0" max="100" value={form.discount_pct}
                  onChange={e => setForm(f => ({ ...f, discount_pct: e.target.value, discount_amount: '' }))}
                  placeholder="Es: 10" />
              </div>
              <div>
                <Label className="text-xs">Oppure importo fisso €</Label>
                <Input type="number" step="0.01" min="0" value={form.discount_amount}
                  onChange={e => setForm(f => ({ ...f, discount_amount: e.target.value, discount_pct: '' }))}
                  placeholder="Es: 5.00" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Ordine minimo €</Label>
                <Input type="number" step="0.01" value={form.min_order_amount}
                  onChange={e => setForm(f => ({ ...f, min_order_amount: e.target.value }))} placeholder="Opzionale" />
              </div>
              <div>
                <Label className="text-xs">Usi massimi</Label>
                <Input type="number" step="1" min="1" value={form.max_uses}
                  onChange={e => setForm(f => ({ ...f, max_uses: e.target.value }))} placeholder="Illimitato" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Valido dal</Label>
                <Input type="date" value={form.valid_from} onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Valido fino al</Label>
                <Input type="date" value={form.valid_to} onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Annulla</Button>
            <Button size="sm" onClick={handleCreate} disabled={saving} className="gap-1.5">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Tag className="h-3.5 w-3.5" />}
              Crea Coupon
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
