import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import { Sparkles, Compass, Download, Loader2, RefreshCw, Check, Building2 } from 'lucide-react';
import { adminAPI } from '../../api';
import { toast } from 'sonner';

/**
 * LeadsTab (PL7) — lead raccolti dalle landing di pre-lancio.
 *
 * Sola lettura + export CSV. I lead sono contatti veri: restano anche
 * dopo il wipe dei sample. Endpoint GET /admin/leads (require_system_admin).
 *
 * Lotto D (24/9/2026) — la stessa componente vive in due posti: nel
 * Cerchio (solo viaggiatori) e nella regia operatori, tab Account (solo
 * professionisti). La prop `tipo` filtra; senza, mostra tutti. Le due
 * colonne nuove dicono se il contatto e' gia' nel Cerchio (`iscritto`,
 * B5) e se ha creato l'account (`organizzazione_id` → link all'org).
 */

const TYPE_BADGE = {
  operator: (
    <Badge variant="outline" className="border-[#C97B5D]/40 text-[#C97B5D]">
      <Sparkles className="mr-1 h-3 w-3" /> Professionista
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
  // Lotto D — in coda i legami (iscritto al Cerchio, organizzazione)
  const head = ['email', 'type', 'name', 'phone', 'link', 'city', 'interests',
                'travel', 'budget', 'activity', 'disciplines', 'venue_type',
                'capacity', 'language', 'consent', 'created_at', 'message',
                'iscritto', 'organizzazione_id'];
  const esc = (v) => {
    const s = v == null ? '' : Array.isArray(v) ? v.join('; ') : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head.join(',')];
  rows.forEach((r) => lines.push(head.map((k) => esc(r[k])).join(',')));
  return lines.join('\n');
};

/** Sintesi leggibile della profilazione: interessi+raggio+budget
 *  (viaggiatore) o attività+dettaglio+telefono (professionista). */
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

/* il link alla regia dell'organizzazione: la lista delle org, con l'id
   nella query per chi la apre (la scheda 360° la cerca da li') */
const linkOrg = (id) => `/admin/operatori?tab=organizzazioni&org=${encodeURIComponent(id)}`;

const LeadsTab = ({ tipo = undefined }) => {
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

  // Lotto D — il filtro per tipo: la componente e' la stessa, la lista no
  const visibili = useMemo(
    () => (tipo ? rows.filter((r) => (r.type || 'traveler') === tipo) : rows),
    [rows, tipo]);

  const handleExport = () => {
    if (!visibili.length) return;
    const blob = new Blob([toCsv(visibili)], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = tipo === 'operator' ? 'aurya-lead-professionisti.csv'
      : tipo === 'traveler' ? 'aurya-lead-viaggiatori.csv' : 'aurya-lead-prelancio.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // SA-R (10/9/2026 sera): il polso e la lista degli iscritti al Cerchio vivono
  // nel tab «Iscritti» (IscrittiTab): qui restano solo i lead delle landing.
  const total = visibili.length;
  const nelCerchio = visibili.filter((r) => r.iscritto).length;

  return (
    <div className="space-y-6" data-testid={`leads-tab${tipo ? `-${tipo}` : ''}`}>
      {/* Conteggi */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{tipo ? 'Contatti' : 'Lead totali'}</CardDescription>
            <CardTitle className="text-3xl">{total}</CardTitle>
          </CardHeader>
        </Card>
        {tipo !== 'traveler' && (
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-[#C97B5D]" /> Professionisti
              </CardDescription>
              <CardTitle className="text-3xl">{counts.operator || 0}</CardTitle>
            </CardHeader>
          </Card>
        )}
        {tipo !== 'operator' && (
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1.5">
                <Compass className="h-3.5 w-3.5 text-[#376254]" /> Viaggiatori
              </CardDescription>
              <CardTitle className="text-3xl">{counts.traveler || 0}</CardTitle>
            </CardHeader>
          </Card>
        )}
        {tipo && (
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-emerald-700" /> Già nel Cerchio
              </CardDescription>
              <CardTitle className="text-3xl">{nelCerchio}</CardTitle>
            </CardHeader>
          </Card>
        )}
      </div>

      {/* Tabella */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">
              {tipo === 'operator' ? 'Candidature dei professionisti'
                : tipo === 'traveler' ? 'Contatti dei viaggiatori' : 'Lead pre-lancio'}
            </CardTitle>
            <CardDescription>
              {tipo === 'operator'
                ? 'Chi si è presentato dalla landing dei professionisti. «Account» dice se ha poi creato la sua organizzazione.'
                : 'Contatti raccolti dalle landing. Restano anche dopo il wipe dei sample; «Iscritto» dice se sono anche nel Cerchio.'}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchLeads} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="sm" onClick={handleExport} disabled={!visibili.length}>
              <Download className="mr-2 h-4 w-4" /> Esporta CSV
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Carico i lead...
            </div>
          ) : visibili.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              Ancora nessun contatto. Compaiono qui appena qualcuno si iscrive dalle landing.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    {!tipo && <TableHead>Tipo</TableHead>}
                    <TableHead>Nome</TableHead>
                    <TableHead>Località</TableHead>
                    <TableHead>Profilo</TableHead>
                    <TableHead>Arrivato il</TableHead>
                    <TableHead>Iscritto</TableHead>
                    <TableHead>Account</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibili.map((r, i) => (
                    <TableRow key={`${r.email}-${r.type}-${i}`} data-testid="leads-riga">
                      <TableCell className="font-medium">{r.email}</TableCell>
                      {!tipo && <TableCell>{TYPE_BADGE[r.type] || r.type}</TableCell>}
                      <TableCell className="text-sm text-muted-foreground">{r.name || '—'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{r.city || '—'}</TableCell>
                      {/* PL10 — sintesi profilazione: interessi+budget o attività+telefono;
                          la descrizione del professionista appare come titolo al passaggio */}
                      <TableCell className="max-w-[260px] truncate text-sm text-muted-foreground"
                                 title={r.message || undefined}>
                        {leadDetails(r)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{fmtDate(r.created_at)}</TableCell>
                      {/* Lotto D — B5: lo stesso essere umano nelle altre liste */}
                      <TableCell className="text-sm" data-testid="leads-iscritto">
                        {r.iscritto
                          ? <span className="inline-flex items-center gap-1 text-emerald-700" title="È nel Cerchio"><Check className="h-4 w-4" /> sì</span>
                          : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="text-sm" data-testid="leads-account">
                        {r.organizzazione_id
                          ? <Link to={linkOrg(r.organizzazione_id)} className="inline-flex items-center gap-1 underline underline-offset-2">
                              <Building2 className="h-4 w-4" /> apri
                            </Link>
                          : <span className="text-muted-foreground">—</span>}
                      </TableCell>
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
