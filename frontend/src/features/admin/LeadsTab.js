import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import { Sparkles, Compass, Download, Loader2, Mail, RefreshCw } from 'lucide-react';
import { adminAPI } from '../../api';
import { toast } from 'sonner';

/**
 * LeadsTab (PL7) — lead raccolti dalle landing di pre-lancio.
 *
 * Sola lettura + export CSV. I lead sono contatti veri: restano anche
 * dopo il wipe dei sample. Endpoint GET /admin/leads (require_system_admin).
 */

const TYPE_BADGE = {
  operator: (
    <Badge variant="outline" className="border-[#C97B5D]/40 text-[#C97B5D]">
      <Sparkles className="mr-1 h-3 w-3" /> Operatore
    </Badge>
  ),
  traveler: (
    <Badge variant="outline" className="border-[#376254]/40 text-[#376254]">
      <Compass className="mr-1 h-3 w-3" /> Viaggiatore
    </Badge>
  ),
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('it-IT', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
};

const toCsv = (rows) => {
  // PL10+PL13 — export completo: tutti i campi di profilazione dei form
  const head = ['email', 'type', 'name', 'phone', 'link', 'city', 'interests',
                'travel', 'budget', 'activity', 'disciplines', 'venue_type',
                'capacity', 'language', 'consent', 'created_at', 'message'];
  const esc = (v) => {
    const s = v == null ? '' : Array.isArray(v) ? v.join('; ') : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head.join(',')];
  rows.forEach((r) => lines.push(head.map((k) => esc(r[k])).join(',')));
  return lines.join('\n');
};

/** Sintesi leggibile della profilazione: interessi+raggio+budget
 *  (viaggiatore) o attività+dettaglio+telefono (operatore). */
const leadDetails = (r) => {
  const parts = [];
  if (r.type === 'operator') {
    if (r.activity) parts.push(r.activity);
    // PL13 — il dettaglio condizionale: discipline o struttura+capienza
    if (Array.isArray(r.disciplines) && r.disciplines.length) parts.push(r.disciplines.join(', '));
    if (r.venue_type) parts.push(r.venue_type + (r.capacity ? ` (${r.capacity})` : ''));
    if (r.phone) parts.push(r.phone);
    /* OL3 — sito o profilo social: e' la prima cosa che si guarda prima
       di rispondere a una candidatura, quindi sta nella sintesi. */
    if (r.link) parts.push(r.link);
  } else {
    if (Array.isArray(r.interests) && r.interests.length) parts.push(r.interests.join(', '));
    if (r.travel) parts.push(r.travel);
    if (r.budget) parts.push(r.budget);
  }
  return parts.join(' · ') || '—';
};

const LeadsTab = () => {
  const [rows, setRows] = useState([]);
  const [counts, setCounts] = useState({ operator: 0, traveler: 0 });
  const [loading, setLoading] = useState(true);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminAPI.listLeads(2000);
      setRows(data.items || []);
      setCounts(data.counts || { operator: 0, traveler: 0 });
    } catch {
      toast.error('Impossibile caricare i lead');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const handleExport = () => {
    if (!rows.length) return;
    const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aurya-lead-prelancio.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // BN6 — il polso della lettera di Aurya (aurya_subscribers)
  const [nlStats, setNlStats] = useState(null);
  useEffect(() => {
    adminAPI.newsletterStats()
      .then(res => setNlStats(res.data))
      .catch(() => setNlStats(null));
  }, []);

  // NW3 — la lista iscritti: ogni riga con FONTE, stato e preferenze
  const [subs, setSubs] = useState(null);
  const [subFilter, setSubFilter] = useState('all'); // all|confirmed|pending|unsubscribed|experiences
  useEffect(() => {
    const params = { limit: 100 };
    if (subFilter === 'experiences') params.experiences = 'yes';
    else if (subFilter !== 'all') params.status = subFilter;
    adminAPI.listSubscribers(params)
      .then(setSubs)
      .catch(() => setSubs(null));
  }, [subFilter]);

  const total = rows.length;

  return (
    <div className="space-y-6">
      {/* BN6 — La lettera di Aurya: iscritti e conferme */}
      {nlStats && (
        <Card data-testid="nl-admin-stats">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4 text-[#8a7440]" /> La lettera di Aurya
            </CardTitle>
            <CardDescription>
              Iscritti alla newsletter (double opt-in). Le campagne si spediscono da Brevo segmentando sugli attributi AURYA_*.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Iscritti totali</p>
                <p className="text-2xl font-semibold">{nlStats.total}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Confermati</p>
                <p className="text-2xl font-semibold text-[#376254]">{nlStats.by_status?.confirmed || 0}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">In attesa di conferma</p>
                <p className="text-2xl font-semibold text-amber-600">{nlStats.by_status?.pending || 0}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Tasso di conferma</p>
                <p className="text-2xl font-semibold">{Math.round((nlStats.confirm_rate || 0) * 100)}%</p>
              </div>
            </div>
            {(nlStats.by_source?.length > 0 || nlStats.by_topic?.length > 0) && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2 text-sm">
                {nlStats.by_source?.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-muted-foreground">Da dove si iscrivono</p>
                    {nlStats.by_source.slice(0, 6).map(r => (
                      <div key={r.source} className="flex justify-between border-b border-dashed border-gray-100 py-0.5">
                        <span className="text-gray-600">{r.source}</span>
                        <span className="font-medium">{r.n}</span>
                      </div>
                    ))}
                  </div>
                )}
                {nlStats.by_topic?.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-muted-foreground">Temi scelti</p>
                    {nlStats.by_topic.slice(0, 6).map(r => (
                      <div key={r.topic} className="flex justify-between border-b border-dashed border-gray-100 py-0.5">
                        <span className="text-gray-600">{r.topic}</span>
                        <span className="font-medium">{r.n}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* NW3 — la lista che mancava: ogni iscritto con la sua
                FONTE, lo stato e le preferenze esperienziali */}
            <div className="mt-5 border-t pt-4" data-testid="nl-admin-subscribers">
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                {[['all', 'Tutti'], ['confirmed', 'Confermati'],
                  ['pending', 'In attesa'], ['unsubscribed', 'Disiscritti'],
                  ['experiences', 'Vogliono esperienze']].map(([k, label]) => (
                  <Button key={k} size="sm"
                          variant={subFilter === k ? 'default' : 'outline'}
                          onClick={() => setSubFilter(k)}>
                    {label}
                  </Button>
                ))}
                {subs && (
                  <span className="ml-auto text-xs text-muted-foreground">
                    {subs.total} risultati
                  </span>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs text-muted-foreground">
                      <th className="py-1.5 pr-3 font-medium">Iscritto</th>
                      <th className="py-1.5 pr-3 font-medium">Stato</th>
                      <th className="py-1.5 pr-3 font-medium">Fonte</th>
                      <th className="py-1.5 pr-3 font-medium">Esperienze</th>
                      <th className="py-1.5 font-medium">Iscritto il</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(subs?.rows || []).map((s) => (
                      <tr key={s.email} className="border-b border-dashed border-gray-100 align-top">
                        <td className="py-1.5 pr-3">
                          <span className="font-medium">{s.email}</span>
                          {s.name && <span className="block text-xs text-muted-foreground">{s.name}</span>}
                        </td>
                        <td className="py-1.5 pr-3">
                          <Badge variant="outline" className={
                            s.status === 'confirmed' ? 'border-[#376254]/40 text-[#376254]'
                              : s.status === 'unsubscribed' ? 'border-gray-300 text-gray-400'
                                : 'border-amber-400/50 text-amber-600'}>
                            {s.status === 'confirmed' ? 'Confermato'
                              : s.status === 'unsubscribed' ? 'Disiscritto' : 'In attesa'}
                          </Badge>
                        </td>
                        <td className="py-1.5 pr-3 text-gray-600">{s.source}</td>
                        <td className="py-1.5 pr-3 text-xs text-gray-600">
                          {s.wants_experiences ? (
                            <>
                              {[s.city, s.travel === 'near' ? 'vicino' : s.travel === 'anywhere' ? 'ovunque' : null]
                                .filter(Boolean).join(' · ') || 'sì'}
                              {s.interests?.length > 0 && (
                                <span className="block">{s.interests.join(', ')}</span>
                              )}
                            </>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="py-1.5 text-xs text-muted-foreground">
                          {s.created_at ? new Date(s.created_at).toLocaleDateString('it-IT') : '—'}
                        </td>
                      </tr>
                    ))}
                    {subs && subs.rows.length === 0 && (
                      <tr><td colSpan={5} className="py-3 text-center text-xs text-muted-foreground">
                        Nessun iscritto con questo filtro.
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Conteggi */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Lead totali</CardDescription>
            <CardTitle className="text-3xl">{total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-[#C97B5D]" /> Operatori
            </CardDescription>
            <CardTitle className="text-3xl">{counts.operator || 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Compass className="h-3.5 w-3.5 text-[#376254]" /> Viaggiatori
            </CardDescription>
            <CardTitle className="text-3xl">{counts.traveler || 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Tabella */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Lead pre-lancio</CardTitle>
            <CardDescription>
              Iscritti dalle landing operatori/viaggiatori. Restano anche dopo il wipe dei sample.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchLeads} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="sm" onClick={handleExport} disabled={!rows.length}>
              <Download className="mr-2 h-4 w-4" /> Esporta CSV
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Carico i lead...
            </div>
          ) : rows.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              Ancora nessun lead. Compaiono qui appena qualcuno si iscrive dalle landing di pre-lancio.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Nome</TableHead>
                    <TableHead>Località</TableHead>
                    <TableHead>Profilo</TableHead>
                    <TableHead>Iscritto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r, i) => (
                    <TableRow key={`${r.email}-${r.type}-${i}`}>
                      <TableCell className="font-medium">{r.email}</TableCell>
                      <TableCell>{TYPE_BADGE[r.type] || r.type}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{r.name || '—'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{r.city || '—'}</TableCell>
                      {/* PL10 — sintesi profilazione: interessi+budget o attività+telefono;
                          la descrizione operatore appare come titolo al passaggio */}
                      <TableCell className="max-w-[260px] truncate text-sm text-muted-foreground"
                                 title={r.message || undefined}>
                        {leadDetails(r)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{fmtDate(r.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default LeadsTab;
