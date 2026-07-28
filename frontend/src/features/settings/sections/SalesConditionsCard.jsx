/**
 * SalesConditionsCard — RS3 "Patti chiari"
 * (docs/RITIRI_INTEGRITA_PIANO_2026-07.md).
 *
 * Le condizioni dell'operatore in UN posto raggiungibile nel mondo
 * snello (Impostazioni, non dentro Stores):
 * 1. politica di cancellazione di default (scaglioni giorni → %
 *    rimborso), ereditata dal wizard ritiro come "Le mie condizioni"
 * 2. documenti legali (privacy + termini) via MerchantLegalDialog
 *    esistente, agganciato allo store tecnico
 * 3. link alla pagina pubblica /s/{slug}/terms (che risponde SEMPRE:
 *    autogenerata finche' l'operatore non pubblica la sua)
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { toast } from 'sonner';
import { ExternalLink, FileText, Save, Scale } from 'lucide-react';
import api from '../../../api/client';
import { organizationsAPI } from '../../../api';
import { storesAPI } from '../../../api/stores';
import MerchantLegalDialog from '../../stores/components/MerchantLegalDialog';

const PRESETS = {
  flessibile: [
    { days_before: 15, refund_percent: 100 },
    { days_before: 5, refund_percent: 50 },
    { days_before: 0, refund_percent: 0 },
  ],
  equilibrata: [
    { days_before: 60, refund_percent: 100 },
    { days_before: 30, refund_percent: 50 },
    { days_before: 0, refund_percent: 0 },
  ],
  rigida: [
    { days_before: 60, refund_percent: 50 },
    { days_before: 30, refund_percent: 25 },
    { days_before: 0, refund_percent: 0 },
  ],
};

export default function SalesConditionsCard() {
  const [policy, setPolicy] = useState(null);   // null = non impostata
  const [saving, setSaving] = useState(false);
  const [store, setStore] = useState(null);
  const [legalOpen, setLegalOpen] = useState(false);

  useEffect(() => {
    api.get('/organizations/current')
      .then(res => {
        const p = res.data?.settings?.default_cancellation_policy;
        if (Array.isArray(p) && p.length) setPolicy(p);
      })
      .catch(() => {});
    // lo store tecnico esiste sempre (ensure-default e' idempotente):
    // e' l'indirizzo dove vivono i documenti legali dell'operatore
    storesAPI.ensureDefault()
      .catch(() => {})
      .then(() => storesAPI.list())
      .then(res => {
        const stores = res?.data?.stores || [];
        setStore(stores.find(s => s.is_default) || stores[0] || null);
      })
      .catch(() => {});
  }, []);

  const rows = policy || PRESETS.equilibrata;

  const updateRow = (idx, field, value) => {
    setPolicy(rows.map((r, i) => i === idx ? { ...r, [field]: value } : r));
  };

  const save = async () => {
    setSaving(true);
    try {
      await organizationsAPI.update({
        default_cancellation_policy: rows.map(r => ({
          days_before: Number(r.days_before),
          refund_percent: Number(r.refund_percent),
        })),
      });
      toast.success('Condizioni salvate: i nuovi ritiri le erediteranno');
    } catch (e) {
      toast.error(e?.response?.data?.detail?.[0]?.msg
        || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSaving(false); }
  };

  return (
    <Card className="border border-border" data-testid="sales-conditions-card">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Scale className="h-5 w-5" />
          Condizioni di vendita
        </CardTitle>
        <CardDescription>
          Le regole che i tuoi clienti accettano quando prenotano: politica di
          cancellazione, privacy e termini. Compaiono sulle tue pagine e al checkout.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">

        {/* 1. Politica di cancellazione di default */}
        <div>
          <p className="text-sm font-semibold text-foreground">La tua politica di cancellazione</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-2">
            Vale come punto di partenza per ogni nuovo ritiro (nel wizard la trovi
            come "Le mie condizioni"). Ogni ritiro puo' comunque personalizzarla.
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries({ flessibile: 'Flessibile', equilibrata: 'Equilibrata', rigida: 'Rigida' }).map(([k, label]) => (
              <Button key={k} type="button" variant="outline" size="sm"
                      onClick={() => setPolicy(PRESETS[k].map(x => ({ ...x })))}>
                {label}
              </Button>
            ))}
          </div>
          <div className="space-y-2">
            {rows.map((tier, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground w-24 shrink-0">
                  {idx === rows.length - 1 ? 'Dopo, o no show' : 'Fino a'}
                </span>
                {idx < rows.length - 1 && (
                  <>
                    <input type="number" min="0" value={tier.days_before}
                           onChange={e => updateRow(idx, 'days_before', e.target.value)}
                           className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                    <span className="text-muted-foreground">giorni prima</span>
                  </>
                )}
                <span className="text-muted-foreground ml-auto">rimborso</span>
                <input type="number" min="0" max="100" value={tier.refund_percent}
                       onChange={e => updateRow(idx, 'refund_percent', e.target.value)}
                       className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                <span className="text-muted-foreground">%</span>
              </div>
            ))}
          </div>
          <Button size="sm" className="mt-3" disabled={saving || !policy} onClick={save}
                  data-testid="save-cancellation-policy">
            <Save className="mr-1.5 h-4 w-4" />
            Salva la politica
          </Button>
        </div>

        {/* 2. Documenti legali (privacy + termini) */}
        <div className="border-t pt-4">
          <p className="text-sm font-semibold text-foreground">Privacy e termini</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-2">
            I documenti che il cliente accetta al checkout. Finche' non li
            personalizzi, ne pubblichiamo una versione generata dai tuoi dati.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" disabled={!store}
                    onClick={() => setLegalOpen(true)} data-testid="edit-legal-docs">
              <FileText className="mr-1.5 h-4 w-4" />
              Modifica privacy e termini
            </Button>
            {store?.slug && (
              <a href={`/s/${store.slug}/terms`} target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
                <ExternalLink className="h-4 w-4" />
                Vedi come li vedono i clienti
              </a>
            )}
          </div>
        </div>
      </CardContent>

      <MerchantLegalDialog
        open={legalOpen && !!store}
        store={store}
        onClose={() => setLegalOpen(false)}
      />
    </Card>
  );
}
