/**
 * BonificoCard — P2 (10/9/2026, piano di business, decisione founder).
 *
 * I primi operatori ci hanno detto che Stripe e' complesso e che
 * preferiscono il bonifico. Il bonifico e' la strada principale della
 * caparra; Stripe resta facoltativo (PaymentConnectionsCard, sopra).
 *
 * Tre campi sull'organizzazione (PUT /organizations/current):
 *   bank_iban, bank_holder, deposit_days. Con l'IBAN, chi chiede un
 * posto in un ritiro «su richiesta» riceve nella stessa email le
 * istruzioni per la caparra (importo dal piano di pagamento del
 * ritiro, IBAN, causale, scadenza). Quando il bonifico arriva,
 * l'operatore segna «caparra ricevuta» sull'ordine.
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { toast } from 'sonner';
import { Landmark, Save } from 'lucide-react';
import { organizationsAPI } from '../../../api';

export default function BonificoCard() {
  const [form, setForm] = useState({ bank_iban: '', bank_holder: '', deposit_days: 5 });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    organizationsAPI.getCurrent()
      .then(res => {
        const o = res.data || {};
        setForm({
          bank_iban: o.bank_iban || '',
          bank_holder: o.bank_holder || '',
          deposit_days: o.deposit_days || 5,
        });
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const set = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }));

  const save = async () => {
    setSaving(true);
    try {
      const giorni = Math.min(30, Math.max(1, Number(form.deposit_days) || 5));
      const res = await organizationsAPI.updateCurrent({
        bank_iban: form.bank_iban.trim(),
        bank_holder: form.bank_holder.trim(),
        deposit_days: giorni,
      });
      const o = res.data || {};
      setForm({ bank_iban: o.bank_iban || '', bank_holder: o.bank_holder || '', deposit_days: o.deposit_days || giorni });
      toast.success(o.bank_iban
        ? 'Bonifico salvato: le istruzioni per la caparra partono da sole'
        : 'Bonifico spento: chi chiede un posto riceve solo «ti contatteremo»');
    } catch (e) {
      toast.error(e?.response?.data?.detail?.[0]?.msg
        || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSaving(false); }
  };

  const attivo = !!form.bank_iban.trim();

  return (
    <Card className="border border-border" data-testid="bonifico-card">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Landmark className="h-5 w-5" />
          La caparra con bonifico
        </CardTitle>
        <CardDescription>
          La strada semplice, senza Stripe. Con il tuo IBAN, chi chiede un posto in un ritiro
          «su richiesta» riceve subito le istruzioni per la caparra: importo, IBAN, causale e
          scadenza. Quando il bonifico arriva, segni «caparra ricevuta» nell’ordine e il posto è suo.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-muted-foreground">IBAN</span>
            <input
              value={form.bank_iban}
              onChange={set('bank_iban')}
              placeholder="IT60 X054 2811 1010 0000 0123 456"
              autoComplete="off"
              spellCheck={false}
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm"
              data-testid="bonifico-iban"
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Intestato a</span>
            <input
              value={form.bank_holder}
              onChange={set('bank_holder')}
              placeholder="Nome e cognome, o la tua attività"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              data-testid="bonifico-intestatario"
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Giorni per fare il bonifico</span>
            <input
              type="number" min={1} max={30}
              value={form.deposit_days}
              onChange={set('deposit_days')}
              className="mt-1 w-32 rounded-md border border-border bg-background px-3 py-2 text-sm"
              data-testid="bonifico-giorni"
            />
          </label>
        </div>
        <p className="text-xs text-muted-foreground" data-testid="bonifico-stato">
          {!loaded ? 'Carico…' : attivo
            ? 'Acceso: l’importo della caparra segue il piano di pagamento del ritiro (o il totale, se non c’è un piano). Aurya non tocca i soldi: senza commissioni, mai.'
            : 'Spento: senza IBAN chi chiede un posto riceve solo «ti contatteremo», e la caparra la chiedi tu a mano.'}
        </p>
        <div className="flex justify-end">
          <Button onClick={save} disabled={saving || !loaded} data-testid="bonifico-salva">
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Salvo…' : 'Salva'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
