/**
 * RisposteCard — FV7-bis (10/9/2026 sera, founder: «dove l'operatore
 * imposta l'indirizzo di risposta? non prende quello dell'account?»).
 *
 * Le email che i clienti ricevono a nome dell'operatore (richiesta,
 * conferma, biglietto, promemoria caparra) partono da noreply@aurya.life
 * ma rispondono a LUI. Qui si vede a quale indirizzo, e da dove viene:
 * di default l'email dell'account (o il contatto, se l'ha messo nelle
 * condizioni), e si puo' cambiare con un indirizzo dedicato. Prima
 * l'unico posto era la pagina del negozio, nascosta nel mondo snello.
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { toast } from 'sonner';
import { Reply, Save } from 'lucide-react';
import api from '../../../api/client';

const FONTI = {
  impostato: 'l’indirizzo che hai scelto qui sotto',
  contatto: 'l’email di contatto delle tue condizioni di vendita',
  notifiche: 'l’indirizzo dove ricevi le notifiche',
  account: 'l’email del tuo account',
};

export default function RisposteCard() {
  const [dati, setDati] = useState(null);
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);

  const carica = () => api.get('/organizations/current/risposte-clienti')
    .then((r) => { setDati(r.data); setEmail(r.data?.impostato || ''); })
    .catch(() => setDati({ email: null, fonte: null }));
  useEffect(() => { carica(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.put('/organizations/current/risposte-clienti', { email: email.trim() });
      setDati(r.data); setEmail(r.data?.impostato || '');
      toast.success(r.data?.impostato
        ? `Le risposte dei clienti arrivano a ${r.data.email}`
        : `Indirizzo dedicato tolto: le risposte arrivano a ${r.data?.email}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail?.[0]?.msg || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSaving(false); }
  };

  return (
    <Card className="border border-border" data-testid="risposte-card">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Reply className="h-5 w-5" />
          Dove rispondono i tuoi clienti
        </CardTitle>
        <CardDescription>
          Le email che i clienti ricevono a tuo nome (richiesta di un posto, conferma, biglietto,
          promemoria della caparra) partono da Aurya, ma quando premono «rispondi» scrivono a te.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {dati && (
          <p className="text-sm" data-testid="risposte-effettivo">
            Oggi arrivano a <strong>{dati.email || '—'}</strong>
            {dati.fonte && FONTI[dati.fonte] ? <span className="text-muted-foreground">, cioè {FONTI[dati.fonte]}.</span> : null}
          </p>
        )}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="block flex-1 text-sm">
            <span className="text-muted-foreground">Un indirizzo dedicato (facoltativo)</span>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="lascia vuoto per usare l’email del tuo account"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              data-testid="risposte-email"
            />
          </label>
          <Button onClick={save} disabled={saving || !dati} data-testid="risposte-salva">
            <Save className="mr-2 h-4 w-4" />{saving ? 'Salvo…' : 'Salva'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
