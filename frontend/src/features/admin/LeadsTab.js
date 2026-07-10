import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import { Sparkles, Compass, Download, Loader2, RefreshCw } from 'lucide-react';
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
  // PL10 — export completo: include i campi di profilazione dei form v2
  const head = ['email', 'type', 'name', 'phone', 'city', 'interests',
                'budget', 'activity', 'language', 'consent', 'created_at', 'message'];
  const esc = (v) => {
    const s = v == null ? '' : Array.isArray(v) ? v.join('; ') : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head.join(',')];
  rows.forEach((r) => lines.push(head.map((k) => esc(r[k])).join(',')));
  return lines.join('\n');
};

/** Sintesi leggibile della profilazione: interessi+budget (viaggiatore)
 *  o attività+telefono (operatore). */
const leadDetails = (r) => {
  const parts = [];
  if (r.type === 'operator') {
    if (r.activity) parts.push(r.activity);
    if (r.phone) parts.push(r.phone);
  } else {
    if (Array.isArray(r.interests) && r.interests.length) parts.push(r.interests.join(', '));
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

  const total = rows.length;

  return (
    <div className="space-y-6">
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
