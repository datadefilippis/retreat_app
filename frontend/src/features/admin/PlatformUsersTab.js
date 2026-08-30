import React, { useCallback, useEffect, useRef, useState } from 'react';
import { adminAPI } from '../../api';
import { StatCard } from '../../components/charts';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  UserRound, BadgeCheck, Mail, ShoppingBag, RefreshCw, Loader2,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

/**
 * PlatformUsersTab (UT1) — la clientela FINALE del marketplace.
 *
 * Chi compra e si iscrive, non gli operatori (quelli stanno nella tab
 * Users). Un utente = una email: account Aurya + guest (ordini senza
 * account) in un'unica tabella. Sola lettura: GET /admin/platform/users
 * (lista + StatCard globali) e /users/detail (drill-down al click).
 */

const eur = (v) => `€${Number(v || 0).toLocaleString('it-IT', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})}`;

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('it-IT', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return String(iso).slice(0, 10); }
};

const TypeBadge = ({ type, verified }) => {
  if (type !== 'account') {
    return (
      <Badge variant="outline" className="border-amber-400 text-amber-700">
        Ospite
      </Badge>
    );
  }
  return verified ? (
    <Badge className="bg-[#376254] hover:bg-[#376254] text-white">
      <BadgeCheck className="mr-1 h-3 w-3" /> Account verificato
    </Badge>
  ) : (
    <Badge variant="outline">Account</Badge>
  );
};

const NEWSLETTER_META = {
  confirmed:    { dot: 'bg-emerald-500', label: 'Iscritto' },
  pending:      { dot: 'bg-amber-400',  label: 'In attesa' },
  unsubscribed: { dot: 'bg-red-400',    label: 'Disiscritto' },
};

const NewsletterDot = ({ status }) => {
  const meta = NEWSLETTER_META[status];
  if (!meta) return <span className="text-muted-foreground text-sm">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-sm">
      <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
};

const ORDER_STATUS_STYLE = {
  confirmed: 'bg-emerald-100 text-emerald-800',
  completed: 'bg-emerald-100 text-emerald-800',
  draft:     'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-700',
};

const CHANNEL_LABELS = {
  marketplace: 'Calendario', store: 'Store', manual: 'Manuale', pos: 'POS',
};

const PAGE_SIZE = 25;

const PlatformUsersTab = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  // filtri in riga singola
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [fType, setFType] = useState('all');        // all|account|guest
  const [fNewsletter, setFNewsletter] = useState('all'); // all|yes|no
  const [fOrders, setFOrders] = useState('all');    // all|yes|no
  const [sort, setSort] = useState('last_order');
  const debounceRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(debounceRef.current);
  }, [search]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE, sort };
      if (debounced) params.search = debounced;
      if (fType === 'guest') params.guests_only = true;
      if (fType === 'account') params.accounts_only = true;
      if (fType === 'verified') { params.accounts_only = true; params.verified = true; }
      if (fNewsletter !== 'all') params.newsletter = fNewsletter === 'yes';
      if (fOrders !== 'all') params.has_orders = fOrders === 'yes';
      setData(await adminAPI.listPlatformUsers(params));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Impossibile caricare gli utenti');
    } finally {
      setLoading(false);
    }
  }, [page, debounced, fType, fNewsletter, fOrders, sort]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // Se i dati si restringono (refresh da pagina alta), torna a pagina 1:
  // mai una tabella vuota con la paginazione sparita.
  useEffect(() => {
    if (data && page > 1 && data.items.length === 0) setPage(1);
  }, [data, page]);

  // ── Drill-down ──
  const [detailEmail, setDetailEmail] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const openDetail = async (email) => {
    setDetailEmail(email);
    setDetailLoading(true);
    setDetail(null);
    try {
      setDetail(await adminAPI.getPlatformUserDetail(email));
    } catch {
      toast.error('Impossibile caricare il dettaglio utente');
      setDetailEmail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const stats = data?.stats || {};
  const items = data?.items || [];
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const account = detail?.account;

  const resetToFirstPage = (setter) => (v) => { setter(v); setPage(1); };

  return (
    <div className="space-y-6">
      {/* StatCard — fotografie GLOBALI (non filtrate) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard loading={loading && !data} icon={UserRound}
                  label="Utenti totali" value={String(stats.users_total ?? '—')} />
        <StatCard loading={loading && !data} icon={BadgeCheck}
                  label="Verificati" value={String(stats.verified ?? '—')} />
        <StatCard loading={loading && !data} icon={Mail}
                  label="Iscritti newsletter" value={String(stats.newsletter_confirmed ?? '—')} />
        <StatCard loading={loading && !data} icon={ShoppingBag}
                  label="Con ordini" value={String(stats.with_orders ?? '—')} />
      </div>

      {/* Ricerca + filtri in riga singola */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca email o nome…"
          className="h-9 w-full sm:w-56"
          data-testid="ut1-search"
        />
        <Select value={fType} onValueChange={resetToFirstPage(setFType)}>
          <SelectTrigger className="h-9 w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti i tipi</SelectItem>
            <SelectItem value="account">Solo account</SelectItem>
            <SelectItem value="verified">Solo verificati</SelectItem>
            <SelectItem value="guest">Solo ospiti</SelectItem>
          </SelectContent>
        </Select>
        <Select value={fNewsletter} onValueChange={resetToFirstPage(setFNewsletter)}>
          <SelectTrigger className="h-9 w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Newsletter: tutti</SelectItem>
            <SelectItem value="yes">Iscritti</SelectItem>
            <SelectItem value="no">Non iscritti</SelectItem>
          </SelectContent>
        </Select>
        <Select value={fOrders} onValueChange={resetToFirstPage(setFOrders)}>
          <SelectTrigger className="h-9 w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Ordini: tutti</SelectItem>
            <SelectItem value="yes">Con ordini</SelectItem>
            <SelectItem value="no">Senza ordini</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={resetToFirstPage(setSort)}>
          <SelectTrigger className="h-9 w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="last_order">Ultimo ordine</SelectItem>
            <SelectItem value="orders">Numero ordini</SelectItem>
            <SelectItem value="spent">Speso</SelectItem>
            <SelectItem value="created">Registrazione</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" className="h-9"
                onClick={fetchUsers} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Tabella */}
      {loading && !data ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center rounded-xl border border-dashed border-border">
          Nessun utente trovato con questi filtri.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Utente</TableHead>
                <TableHead>Newsletter</TableHead>
                <TableHead>Fonte</TableHead>
                <TableHead className="text-right">Ordini</TableHead>
                <TableHead className="text-right">Speso</TableHead>
                <TableHead>Operatori</TableHead>
                <TableHead>Ultimo ordine</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((u) => (
                <TableRow key={u.email} onClick={() => openDetail(u.email)}
                          className="cursor-pointer"
                          data-testid={`ut1-row-${u.email}`}>
                  <TableCell>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{u.name || u.email}</span>
                      <TypeBadge type={u.type} verified={u.email_verified} />
                    </div>
                    {u.name && (
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    )}
                  </TableCell>
                  <TableCell><NewsletterDot status={u.newsletter_status} /></TableCell>
                  {/* FA5 (FARO) — da dove arriva l'iscrizione: il
                      canale si legge in riga, senza aprire il dettaglio */}
                  <TableCell className="text-xs text-muted-foreground"
                    title={u.newsletter_source || ''}>
                    {u.newsletter_source
                      ? (u.newsletter_source.length > 22
                        ? u.newsletter_source.slice(0, 22) + '…'
                        : u.newsletter_source)
                      : '—'}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-medium">{u.orders_count}</span>
                    {u.orders_count > u.confirmed_orders && (
                      <span className="text-xs text-muted-foreground"> ({u.confirmed_orders} conf.)</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {u.total_spent > 0 ? eur(u.total_spent) : '—'}
                  </TableCell>
                  <TableCell>
                    {u.operators_count === 0 ? (
                      <span className="text-muted-foreground text-sm">—</span>
                    ) : (
                      <span className="text-sm" title={u.operators.join(', ')}>
                        {u.operators.slice(0, 2).join(', ')}
                        {u.operators_count > 2 && (
                          <span className="text-muted-foreground"> +{u.operators_count - 2}</span>
                        )}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {fmtDate(u.last_order_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Paginazione */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {total} utenti — pagina {page} di {pages}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1 || loading}
                    onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft className="h-4 w-4" /> Precedente
            </Button>
            <Button variant="outline" size="sm" disabled={page >= pages || loading}
                    onClick={() => setPage((p) => p + 1)}>
              Successiva <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Drill-down ── */}
      <Dialog open={Boolean(detailEmail)}
              onOpenChange={(open) => { if (!open) { setDetailEmail(null); setDetail(null); } }}>
        <DialogContent className="max-w-2xl max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex flex-wrap items-center gap-2 pr-6">
              <UserRound className="h-4 w-4 text-[#8a7440]" />
              {detail?.account?.name || detail?.email || detailEmail}
              {detail && (
                <TypeBadge type={detail.type}
                           verified={Boolean(detail.account?.email_verified)} />
              )}
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Carico il dettaglio...
            </div>
          ) : detail && (
            <div className="space-y-5">
              {/* Anagrafica */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Email</p>
                  <p className="break-all">{detail.email}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Registrato</p>
                  <p>{fmtDate(account?.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Ultimo accesso</p>
                  <p>{fmtDate(account?.last_login_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Lingua</p>
                  <p>{account?.language ? account.language.toUpperCase() : '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Telefono</p>
                  <p>{account?.phone || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Newsletter</p>
                  <NewsletterDot status={detail.newsletter?.status} />
                  {/* NW3 — la FONTE dell'iscrizione, che il backend
                      mandava gia' e nessuno mostrava */}
                  {detail.newsletter?.source && (
                    <p className="text-xs text-muted-foreground">
                      da: {detail.newsletter.source}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Consenso Aurya</p>
                  <p>{fmtDate(detail.consents?.aurya_legal?.accepted_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Marketing operatori</p>
                  <p>{detail.customers?.some((c) => c.marketing_opted_in) ? 'Sì' : 'No'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Speso (confermato)</p>
                  <p className="font-medium">{eur(detail.total_spent)}</p>
                </div>
              </div>

              {/* Ordini */}
              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Ordini ({detail.orders_count})
                </h3>
                {detail.orders.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nessun ordine.</p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Data</TableHead>
                          <TableHead>Operatore</TableHead>
                          <TableHead>Stato</TableHead>
                          <TableHead>Canale</TableHead>
                          <TableHead className="text-right">Totale</TableHead>
                          <TableHead>Rif.</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detail.orders.map((o) => (
                          <TableRow key={o.id}>
                            <TableCell className="text-sm whitespace-nowrap">
                              {fmtDate(o.created_at)}
                            </TableCell>
                            <TableCell className="text-sm">{o.operator_name}</TableCell>
                            <TableCell>
                              <Badge className={ORDER_STATUS_STYLE[o.status] || 'bg-gray-100 text-gray-600'}>
                                {o.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm">
                              {CHANNEL_LABELS[o.sales_channel] || o.sales_channel || '—'}
                            </TableCell>
                            <TableCell className="text-right text-sm font-medium whitespace-nowrap">
                              {eur(o.total)}
                            </TableCell>
                            <TableCell className="text-xs font-mono text-muted-foreground">
                              {o.order_number || `${o.id.slice(0, 8)}…`}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>

              {/* Record cliente per operatore */}
              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Schede cliente presso gli operatori ({detail.customers.length})
                </h3>
                {detail.customers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nessuna scheda cliente.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {detail.customers.map((c) => (
                      <li key={c.id || `${c.organization_id}-${c.created_at}`}
                          className="flex flex-wrap items-center gap-2 text-sm rounded-lg border border-border px-3 py-2">
                        <span className="font-medium">{c.organization_name}</span>
                        <span className="text-xs text-muted-foreground">
                          dal {fmtDate(c.created_at)}
                        </span>
                        {c.marketing_opted_in ? (
                          <Badge className="bg-emerald-100 text-emerald-800 ml-auto">Marketing sì</Badge>
                        ) : (
                          <Badge variant="outline" className="ml-auto">Marketing no</Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Consensi (audit) */}
              {(detail.consents?.audit_by_source || []).length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-2">Audit consensi</h3>
                  <ul className="space-y-1 text-sm">
                    {detail.consents.audit_by_source.map((a) => (
                      <li key={a.source} className="flex items-center gap-2">
                        <span className="font-mono text-xs">{a.source}</span>
                        <span className="text-muted-foreground text-xs">
                          × {a.n} — ultimo: {fmtDate(a.last_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PlatformUsersTab;
