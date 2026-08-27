/**
 * NuovoCliente — la porta di creazione manuale nel registro (27/8,
 * deciso dal founder).
 *
 * Il registro clienti (Customer Insights) nasceva come SPECCHIO: si
 * popola da solo con ordini, biglietti, iscrizioni. Ma la rubrica e'
 * UNA (collezione customers) e le porte di creazione erano solo
 * contestuali (rito, link riservati di Sound, ordine manuale): dal
 * menu snello un cliente non si poteva creare a mano. Questo bottone
 * chiude il buco — il cliente creato qui e' lo stesso che ScegliPersona
 * trova nel foglio dei link riservati, senza sincronizzare niente.
 *
 * Componente ISOLATO: bottone + dialogo, nessuno stato condiviso con
 * la pagina se non il callback `onCreato` (che la pagina usa per
 * ricaricare il registro).
 */
import React, { useState } from 'react';
import { toast } from 'sonner';
import { UserPlus } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '../../../components/ui/dialog';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { customersAPI } from '../../../api/customers';

const VUOTO = { name: '', email: '', phone: '' };

export default function NuovoCliente({ onCreato = null }) {
  const [aperto, setAperto] = useState(false);
  const [form, setForm] = useState(VUOTO);
  const [busy, setBusy] = useState(false);

  const campo = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const salva = async (e) => {
    e.preventDefault();
    const nome = form.name.trim();
    if (!nome || busy) return;
    setBusy(true);
    try {
      const { data } = await customersAPI.create({
        name: nome,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
      });
      toast.success(`Cliente «${data.name}» creato: è già in rubrica, ovunque.`);
      setForm(VUOTO);
      setAperto(false);
      if (onCreato) onCreato(data);
    } catch {
      toast.error('Cliente non creato: riprova.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        size="sm"
        className="h-7 text-xs gap-1.5"
        data-testid="ci-nuovo-cliente"
        onClick={() => setAperto(true)}
      >
        <UserPlus className="h-3.5 w-3.5" />
        Nuovo cliente
      </Button>
      <Dialog open={aperto} onOpenChange={(v) => { if (!busy) setAperto(v); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nuovo cliente</DialogTitle>
            <DialogDescription>
              Entra nella stessa rubrica di ordini, biglietti e link
              riservati: basta il nome, il resto quando serve.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={salva} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="nc-nome">Nome *</Label>
              <Input
                id="nc-nome"
                value={form.name}
                onChange={campo('name')}
                placeholder="Nome e cognome"
                maxLength={255}
                autoFocus
                data-testid="ci-nuovo-nome"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nc-email">Email</Label>
              <Input
                id="nc-email"
                type="email"
                value={form.email}
                onChange={campo('email')}
                placeholder="facoltativa"
                maxLength={320}
                data-testid="ci-nuovo-email"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nc-telefono">Telefono</Label>
              <Input
                id="nc-telefono"
                type="tel"
                value={form.phone}
                onChange={campo('phone')}
                placeholder="facoltativo"
                maxLength={40}
                data-testid="ci-nuovo-telefono"
              />
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setAperto(false)}
                disabled={busy}
              >
                Annulla
              </Button>
              <Button
                type="submit"
                disabled={!form.name.trim() || busy}
                data-testid="ci-nuovo-salva"
              >
                {busy ? 'Creo…' : 'Crea cliente'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
