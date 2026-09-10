/**
 * IscrittiTab — SA-R (10/9/2026 sera, founder): «pieno controllo sugli
 * iscritti al Cerchio: preferenze sui ritiri, zona, tutto quello che
 * hanno dato, da dove si sono iscritti, email; e verificare che chi si
 * disiscrive cambi stato nel pannello».
 *
 * Una tabella, i filtri che contano (stato, porta, fonte, vuole i
 * ritiri, regione, via, ricerca), i numeri in testa, il dettaglio di
 * una persona al clic (con «Disiscrivi» per le richieste che arrivano
 * a voce o via email), l'export CSV. Tutto da GET /admin/subscribers,
 * che e' l'unica verita' sugli iscritti.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, RefreshCw, Search, UserMinus } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { StatCard } from '../../components/charts';
import { Users, UserCheck, UserX, Clock } from 'lucide-react';

const STATI = { confirmed: 'confermato', pending: 'in attesa', unsubscribed: 'disiscritto' };
const STATO_CLS = {
  confirmed: 'bg-emerald-100 text-emerald-800',
  pending: 'bg-amber-100 text-amber-800',
  unsubscribed: 'bg-gray-200 text-gray-700',
};
const VIE = {
  yoga: 'Yoga', meditazione: 'Meditazione', breathwork: 'Respiro', suono: 'Suono', reiki: 'Reiki',
  costellazioni: 'Costellazioni', astrologia: 'Astrologia', ayurveda: 'Ayurveda', tantra: 'Tantra',
  detox: 'Detox', cammini: 'Cammini', cerchi: 'Cerchi', crescita: 'Crescita', misto: 'Un po’ di tutto',
};
const DOVE = { near: 'vicino a casa', italy: 'in Italia', anywhere: 'ovunque', abroad: 'anche all’estero' };
const BUDGET = { under500: 'fino a 500 €', '500to1000': '500–1000 €', over1000: 'oltre 1000 €', flexible: 'flessibile' };
const REGIONI = {
  abruzzo: 'Abruzzo', basilicata: 'Basilicata', calabria: 'Calabria', campania: 'Campania',
  'emilia-romagna': 'Emilia-Romagna', 'friuli-venezia-giulia': 'Friuli-Venezia Giulia', lazio: 'Lazio',
  liguria: 'Liguria', lombardia: 'Lombardia', marche: 'Marche', molise: 'Molise', piemonte: 'Piemonte',
  puglia: 'Puglia', sardegna: 'Sardegna', sicilia: 'Sicilia', toscana: 'Toscana',
  'trentino-alto-adige': 'Trentino-Alto Adige', umbria: 'Umbria', 'valle-d-aosta': 'Valle d’Aosta', veneto: 'Veneto',
};
const PORTE = { meditazioni: 'meditazioni', altro: 'altre porte' };
const LIMITE = 50;

const data = (v) => (v ? new Date(v).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—');
const dataOra = (v) => (v ? new Date(v).toLocaleString('it-IT') : '—');
const vie = (r) => (r.interests || []).map((k) => VIE[k] || k).join(', ');
const alertTesto = (r) => {
  const a = r.retreat_alert || {};
  if (!a.enabled) return 'no';
  if (a.scope === 'regions' && (a.regions || []).length) return (a.regions || []).map((x) => REGIONI[x] || x).join(', ');
  return 'tutta Italia';
};

const selCls = 'rounded-md border border-border bg-background px-2 py-1.5 text-sm';

export default function IscrittiTab() {
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [sources, setSources] = useState([]);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ status: '', porta: '', source: '', experiences: '', region: '', interest: '', q: '' });
  const [aperto, setAperto] = useState(null);

  const params = useMemo(() => {
    const p = { skip, limit: LIMITE };
    Object.entries(f).forEach(([k, v]) => { if (v) p[k] = v; });
    return p;
  }, [f, skip]);

  const carica = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get('/admin/subscribers', { params }),
      api.get('/admin/newsletter-stats'),
    ]).then(([l, s]) => {
      setRows(l.data.items || []); setTotal(l.data.total || 0); setSources(l.data.sources || []);
      setStats(s.data);
    }).catch(() => toast.error('Non riesco a caricare gli iscritti'))
      .finally(() => setLoading(false));
  }, [params]);
  useEffect(() => { carica(); }, [carica]);

  const setFiltro = (k) => (e) => { setSkip(0); setF((prev) => ({ ...prev, [k]: e.target.value })); };

  const esporta = async () => {
    try {
      const r = await api.get('/admin/subscribers/export.csv', { params: { ...params, skip: 0, limit: 5000 }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a'); a.href = url; a.download = 'iscritti-cerchio.csv'; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Export non riuscito'); }
  };

  const disiscrivi = async (email) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Disiscrivere ${email} dal Cerchio? Non riceverà più nulla.`)) return;
    try {
      const r = await api.post('/admin/subscribers/disiscrivi', { email });
      setAperto(r.data); carica();
      toast.success(`${email} è disiscritto`);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Non riuscito'); }
  };

  const byStatus = stats?.by_status || {};
  return (
    <div className="space-y-6" data-testid="iscritti-tab">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard loading={!stats} icon={Users} label="Iscritti in tutto" value={stats ? `${stats.total}` : '—'}
                  sublabel={stats ? `conferma ${Math.round((stats.confirm_rate || 0) * 100)}%` : ''} />
        <StatCard loading={!stats} icon={UserCheck} label="Confermati" value={`${byStatus.confirmed || 0}`}
                  sublabel={stats ? `+${(stats.weekly_new || []).slice(-1)[0]?.n ?? (stats.weekly_new || []).slice(-1)[0]?.count ?? 0} nell’ultima settimana` : ''} />
        <StatCard loading={!stats} icon={Clock} label="In attesa del clic" value={`${byStatus.pending || 0}`}
                  sublabel="promemoria dopo 48 ore, una volta" />
        <StatCard loading={!stats} icon={UserX} label="Disiscritti" value={`${byStatus.unsubscribed || 0}`}
                  sublabel="restano a DB per non riscriverli" />
      </div>

      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg">Gli iscritti al Cerchio</CardTitle>
          <CardDescription>
            Ogni riga dice chi è, com’è entrata e cosa ci ha detto. Clicca una riga per il dettaglio. Chi si disiscrive
            dal link nelle email compare qui come «disiscritto» con la data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2" data-testid="iscritti-filtri">
            <select value={f.status} onChange={setFiltro('status')} className={selCls} data-testid="iscritti-f-stato">
              <option value="">tutti gli stati</option>
              {Object.entries(STATI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.porta} onChange={setFiltro('porta')} className={selCls} data-testid="iscritti-f-porta">
              <option value="">tutte le porte</option>
              {Object.entries(PORTE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.source} onChange={setFiltro('source')} className={selCls} data-testid="iscritti-f-fonte">
              <option value="">tutte le fonti</option>
              {sources.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={f.experiences} onChange={setFiltro('experiences')} className={selCls} data-testid="iscritti-f-ritiri">
              <option value="">ritiri: tutti</option>
              <option value="yes">vuole i ritiri</option>
              <option value="no">non li ha chiesti</option>
            </select>
            <select value={f.region} onChange={setFiltro('region')} className={selCls}>
              <option value="">tutte le regioni</option>
              {Object.entries(REGIONI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.interest} onChange={setFiltro('interest')} className={selCls}>
              <option value="">tutte le vie</option>
              {Object.entries(VIE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={f.q} onChange={setFiltro('q')} placeholder="cerca email" className="h-9 w-48 pl-8" data-testid="iscritti-f-q" />
            </div>
            <Button variant="outline" size="sm" onClick={carica}><RefreshCw className="mr-1 h-4 w-4" />Aggiorna</Button>
            <Button variant="outline" size="sm" onClick={esporta} data-testid="iscritti-export"><Download className="mr-1 h-4 w-4" />CSV</Button>
            <span className="ml-auto text-sm text-muted-foreground" data-testid="iscritti-totale">{total} {total === 1 ? 'persona' : 'persone'}</span>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Nome</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Fonte</TableHead>
                  <TableHead>Iscritto</TableHead>
                  <TableHead>Confermato</TableHead>
                  <TableHead>Disiscritto</TableHead>
                  <TableHead>Vie</TableHead>
                  <TableHead>Città</TableHead>
                  <TableHead>Dove</TableHead>
                  <TableHead>Avviso ritiri</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && rows.length === 0 ? (
                  <TableRow><TableCell colSpan={11} className="text-center text-sm text-muted-foreground">Carico…</TableCell></TableRow>
                ) : rows.length === 0 ? (
                  <TableRow><TableCell colSpan={11} className="text-center text-sm text-muted-foreground">Nessuno con questi filtri.</TableCell></TableRow>
                ) : rows.map((r) => (
                  <TableRow key={r.email} className="cursor-pointer" onClick={() => setAperto(r)} data-testid="iscritti-riga">
                    <TableCell className="font-mono text-xs">{r.email}</TableCell>
                    <TableCell>{r.name || '—'}</TableCell>
                    <TableCell><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATO_CLS[r.status] || ''}`} data-testid={`iscritti-stato-${r.status}`}>{STATI[r.status] || r.status}</span></TableCell>
                    <TableCell className="text-xs"><span className="text-muted-foreground">{PORTE[r.porta] || r.porta}</span> · {r.source}</TableCell>
                    <TableCell className="text-xs">{data(r.created_at)}</TableCell>
                    <TableCell className="text-xs">{data(r.confirmed_at)}</TableCell>
                    <TableCell className="text-xs">{data(r.unsubscribed_at)}</TableCell>
                    <TableCell className="text-xs">{vie(r) || '—'}</TableCell>
                    <TableCell className="text-xs">{r.city || '—'}</TableCell>
                    <TableCell className="text-xs">{DOVE[r.travel] || '—'}</TableCell>
                    <TableCell className="text-xs">{alertTesto(r)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {total > LIMITE && (
            <div className="flex items-center justify-between text-sm">
              <Button variant="outline" size="sm" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - LIMITE))}>← precedenti</Button>
              <span className="text-muted-foreground">{skip + 1}–{Math.min(skip + LIMITE, total)} di {total}</span>
              <Button variant="outline" size="sm" disabled={skip + LIMITE >= total} onClick={() => setSkip(skip + LIMITE)}>successivi →</Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!aperto} onOpenChange={(o) => { if (!o) setAperto(null); }}>
        <DialogContent className="max-w-lg" data-testid="iscritti-dettaglio">
          {aperto && (
            <>
              <DialogHeader>
                <DialogTitle className="font-mono text-sm">{aperto.email}</DialogTitle>
              </DialogHeader>
              <dl className="grid grid-cols-[9rem_1fr] gap-y-2 text-sm">
                <dt className="text-muted-foreground">Nome</dt><dd>{aperto.name || '—'}</dd>
                <dt className="text-muted-foreground">Stato</dt><dd>{STATI[aperto.status] || aperto.status}{aperto.unsubscribed_by ? ` (da ${aperto.unsubscribed_by})` : ''}</dd>
                <dt className="text-muted-foreground">Porta · fonte</dt><dd>{PORTE[aperto.porta] || aperto.porta} · {aperto.source}</dd>
                <dt className="text-muted-foreground">Iscritto il</dt><dd>{dataOra(aperto.created_at)}</dd>
                <dt className="text-muted-foreground">Confermato il</dt><dd>{dataOra(aperto.confirmed_at)}</dd>
                <dt className="text-muted-foreground">Disiscritto il</dt><dd>{dataOra(aperto.unsubscribed_at)}</dd>
                <dt className="text-muted-foreground">Vie</dt><dd>{vie(aperto) || '—'}</dd>
                <dt className="text-muted-foreground">Città</dt><dd>{aperto.city || '—'}</dd>
                <dt className="text-muted-foreground">Dove</dt><dd>{DOVE[aperto.travel] || '—'}</dd>
                <dt className="text-muted-foreground">Budget</dt><dd>{BUDGET[aperto.budget] || aperto.budget || '—'}</dd>
                <dt className="text-muted-foreground">Avviso ritiri</dt><dd>{alertTesto(aperto)}</dd>
                <dt className="text-muted-foreground">Temi Magazine</dt><dd>{(aperto.topics || []).join(', ') || '—'}</dd>
                <dt className="text-muted-foreground">Lingua</dt><dd>{aperto.language || '—'}</dd>
                <dt className="text-muted-foreground">Email ricevute</dt><dd>{(aperto.sequenza || []).join(', ') || '—'}{aperto.reminder_sent_at ? ' · promemoria 48h' : ''}</dd>
              </dl>
              {aperto.status !== 'unsubscribed' && (
                <div className="mt-2 flex justify-end">
                  <Button variant="outline" size="sm" onClick={() => disiscrivi(aperto.email)} data-testid="iscritti-disiscrivi">
                    <UserMinus className="mr-1 h-4 w-4" />Disiscrivi
                  </Button>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
