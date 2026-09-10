/**
 * OrdiniTab — SA-R (10/9/2026 sera, founder): «controllo sugli ordini
 * degli utenti, quali operatori».
 *
 * Gli ordini di TUTTA la piattaforma in una tabella (numero, operatore,
 * cliente, cosa, totale, stato, pagamento, origine, data) con il filtro
 * per operatore e per stato, e in testa il riepilogo per operatore degli
 * ultimi 30 giorni. Sola lettura: GET /admin/platform/ordini.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Button } from '../../components/ui/button';

const STATO = { draft: 'bozza', confirmed: 'confermato', completed: 'completato', cancelled: 'annullato' };
const PAGAMENTO = { pending: 'in attesa', paid: 'pagato', overdue: 'scaduto', partial: 'caparra', refunded: 'rimborsato', waived: 'non dovuto' };
const ORIGINE = { manual: 'manuale', storefront: 'online', storefront_direct: 'online', storefront_approval: 'su richiesta' };
const eur = (v, c = 'EUR') => new Intl.NumberFormat('it-IT', { style: 'currency', currency: c || 'EUR' }).format(Number(v) || 0);
const data = (v) => (v ? new Date(v).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—');
const selCls = 'rounded-md border border-border bg-background px-2 py-1.5 text-sm';

export default function OrdiniTab() {
  const [dati, setDati] = useState(null);
  const [org, setOrg] = useState('');
  const [stato, setStato] = useState('');
  const [loading, setLoading] = useState(true);

  const carica = useCallback(() => {
    setLoading(true);
    api.get('/admin/platform/ordini', { params: { limit: 100, org_id: org || undefined, stato: stato || undefined } })
      .then((r) => setDati(r.data))
      .catch(() => toast.error('Non riesco a caricare gli ordini'))
      .finally(() => setLoading(false));
  }, [org, stato]);
  useEffect(() => { carica(); }, [carica]);

  const perOperatore = dati?.per_operatore || [];
  const items = dati?.items || [];
  return (
    <div className="space-y-6" data-testid="ordini-tab">
      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg">Per operatore, ultimi 30 giorni</CardTitle>
          <CardDescription>Quanti ordini riceve ciascuno e quanto valgono. Clicca un operatore per vedere solo i suoi.</CardDescription>
        </CardHeader>
        <CardContent>
          {perOperatore.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nessun ordine negli ultimi 30 giorni.</p>
          ) : (
            <div className="flex flex-wrap gap-2" data-testid="ordini-per-operatore">
              {perOperatore.map((o) => (
                <button key={o.org_id} type="button" onClick={() => setOrg(org === o.org_id ? '' : o.org_id)}
                        className={`rounded-full border px-3 py-1.5 text-xs font-medium ${org === o.org_id ? 'border-[#2f5749] bg-[#2f5749] text-white' : 'border-border bg-background'}`}>
                  {o.nome} · {o.ordini} {o.ordini === 1 ? 'ordine' : 'ordini'} · {eur(o.totale)}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg">Gli ordini</CardTitle>
          <CardDescription>Gli ultimi cento, dal più recente. Il numero è quello che vede il cliente.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <select value={org} onChange={(e) => setOrg(e.target.value)} className={selCls} data-testid="ordini-f-operatore">
              <option value="">tutti gli operatori</option>
              {(dati?.operatori || []).map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
            </select>
            <select value={stato} onChange={(e) => setStato(e.target.value)} className={selCls} data-testid="ordini-f-stato">
              <option value="">tutti gli stati</option>
              {Object.entries(STATO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <Button variant="outline" size="sm" onClick={carica}><RefreshCw className="mr-1 h-4 w-4" />Aggiorna</Button>
            <span className="ml-auto text-sm text-muted-foreground">{items.length} {items.length === 1 ? 'ordine' : 'ordini'}</span>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Numero</TableHead>
                  <TableHead>Operatore</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Cosa</TableHead>
                  <TableHead className="text-right">Totale</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Pagamento</TableHead>
                  <TableHead>Origine</TableHead>
                  <TableHead>Data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && items.length === 0 ? (
                  <TableRow><TableCell colSpan={9} className="text-center text-sm text-muted-foreground">Carico…</TableCell></TableRow>
                ) : items.length === 0 ? (
                  <TableRow><TableCell colSpan={9} className="text-center text-sm text-muted-foreground">Nessun ordine con questi filtri.</TableCell></TableRow>
                ) : items.map((o) => (
                  <TableRow key={o.id} data-testid="ordini-riga">
                    <TableCell className="font-mono text-xs">{o.order_number || o.id.slice(0, 8)}</TableCell>
                    <TableCell className="text-sm">{o.org?.nome || '—'}</TableCell>
                    <TableCell className="text-xs">{o.customer?.nome || '—'}<br /><span className="font-mono text-muted-foreground">{o.customer?.email || ''}</span></TableCell>
                    <TableCell className="text-xs">{(o.righe || []).map((r) => `${r.qty > 1 ? r.qty + '× ' : ''}${r.nome}`).join(', ') || '—'}</TableCell>
                    <TableCell className="text-right text-sm font-medium">{eur(o.total, o.currency)}</TableCell>
                    <TableCell className="text-xs">{STATO[o.status] || o.status}</TableCell>
                    <TableCell className="text-xs">{PAGAMENTO[o.payment_status] || o.payment_status}</TableCell>
                    <TableCell className="text-xs">{ORIGINE[o.source] || o.source}</TableCell>
                    <TableCell className="text-xs">{data(o.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
