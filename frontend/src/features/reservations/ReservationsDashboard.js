/**
 * ReservationsDashboard — admin list of all IssuedReservation rows for the org.
 *
 * Route: /reservations  (Onda 16 Fase 5)
 *
 * This is the operational counterpart to OrdersPage, but scoped to post-
 * confirmation reservation entities (not draft/confirmed orders). It exists
 * so a merchant with lots of bookings (e.g. a B&B with 30 reservations/week)
 * doesn't have to drill into each order separately to find a single RSV code,
 * resend a confirmation email, or download an ICS file.
 *
 * Mutation surface is intentionally minimal: admins resend emails here;
 * creating and cancelling still happens through the order flow.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import {
  BookMarked, Search, Loader2, RefreshCw, ExternalLink, Mail, Download,
  Calendar as CalendarIcon, Clock as ClockIcon, X as XIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { issuedReservationsAPI } from '../../api/issuedReservations';
import CopyButton from '../orders/components/CopyButton';

function formatDateIt(ymd) {
  if (!ymd) return '';
  try {
    const [y, m, d] = ymd.split('-').map(Number);
    const dt = new Date(y, m - 1, d, 12, 0, 0);
    return dt.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return ymd;
  }
}

function ReservationWhen({ r }) {
  if (r.reservation_flavor === 'range') {
    return (
      <div className="flex items-center gap-1.5 text-xs">
        <CalendarIcon className="h-3 w-3 text-muted-foreground" />
        <span>
          {formatDateIt(r.date_from)}
          {r.date_to && r.date_to !== r.date_from && ` → ${formatDateIt(r.date_to)}`}
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <ClockIcon className="h-3 w-3 text-muted-foreground" />
      <span>
        {formatDateIt(r.slot_date)}
        {r.slot_start_time && ` · ${r.slot_start_time}`}
        {r.slot_end_time && ` → ${r.slot_end_time}`}
      </span>
    </div>
  );
}

export default function ReservationsDashboard() {
  const { t } = useTranslation('reservations');
  const navigate = useNavigate();

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [resendingId, setResendingId] = useState(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState('active'); // active | cancelled | all
  const [filterFlavor, setFilterFlavor] = useState('all');    // range | slot | all
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setErrored(false);
    try {
      const params = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterFlavor !== 'all') params.flavor = filterFlavor;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (appliedSearch) params.search = appliedSearch;
      const res = await issuedReservationsAPI.list(params);
      setRows(res.data?.reservations || []);
    } catch {
      setErrored(true);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterFlavor, dateFrom, dateTo, appliedSearch]);

  useEffect(() => {
    load();
  }, [load]);

  const resetFilters = () => {
    setFilterStatus('active');
    setFilterFlavor('all');
    setDateFrom('');
    setDateTo('');
    setSearchTerm('');
    setAppliedSearch('');
  };

  const handleDownloadIcs = async (r) => {
    if (!r.access_token) return;
    try {
      const res = await issuedReservationsAPI.downloadIcs(r.access_token);
      const blob = new Blob([res.data], { type: 'text/calendar' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prenotazione-${r.code || r.id}.ics`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t('actions.download_ics_error', { defaultValue: 'Download ICS fallito' }));
    }
  };

  const handleResend = async (r) => {
    if (r.status === 'cancelled') {
      toast.error(t('resend.cancelled_not_allowed'));
      return;
    }
    setResendingId(r.id);
    try {
      await issuedReservationsAPI.resend(r.id);
      toast.success(t('resend.success'));
      await load();
    } catch {
      toast.error(t('resend.error'));
    } finally {
      setResendingId(null);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setAppliedSearch(searchTerm.trim());
  };

  const hasActiveFilters = useMemo(
    () => filterStatus !== 'active' || filterFlavor !== 'all' || dateFrom || dateTo || appliedSearch,
    [filterStatus, filterFlavor, dateFrom, dateTo, appliedSearch],
  );

  return (
    <AppLayout>
      <Header title={t('dashboard.title')} />
      <PageSubheader
        icon={BookMarked}
        title={t('dashboard.title')}
        description={t('dashboard.subtitle')}
        actions={
          <Button variant="outline" size="sm" onClick={load} className="gap-1.5">
            <RefreshCw className="h-4 w-4" />
          </Button>
        }
      />

      <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-4">
        {/* Filters bar */}
        <div className="rounded-lg border bg-card p-3 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {/* Status toggle */}
            <div className="inline-flex rounded-md border overflow-hidden text-xs">
              {['active', 'cancelled', 'all'].map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setFilterStatus(v)}
                  className={`px-2.5 py-1.5 transition-colors ${
                    filterStatus === v ? 'bg-primary text-primary-foreground' : 'bg-transparent hover:bg-muted'
                  }`}
                >
                  {t(`filters.status_${v}`)}
                </button>
              ))}
            </div>

            {/* Flavor toggle */}
            <div className="inline-flex rounded-md border overflow-hidden text-xs">
              {['all', 'range', 'slot'].map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setFilterFlavor(v)}
                  className={`px-2.5 py-1.5 transition-colors ${
                    filterFlavor === v ? 'bg-primary text-primary-foreground' : 'bg-transparent hover:bg-muted'
                  }`}
                >
                  {t(`filters.flavor_${v}`)}
                </button>
              ))}
            </div>

            {/* Date range */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">{t('filters.date_from')}</span>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="h-8 w-[140px] text-xs"
              />
              <span className="text-muted-foreground">{t('filters.date_to')}</span>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="h-8 w-[140px] text-xs"
              />
            </div>

            {/* Search */}
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-1.5 flex-1 min-w-[220px]">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder={t('filters.search_placeholder')}
                  className="h-8 pl-8 text-xs"
                />
              </div>
              <Button type="submit" size="sm" variant="outline" className="h-8 gap-1">
                <Search className="h-3.5 w-3.5" />
              </Button>
            </form>

            {hasActiveFilters && (
              <Button type="button" size="sm" variant="ghost" onClick={resetFilters} className="h-8 gap-1 text-xs">
                <XIcon className="h-3.5 w-3.5" />
                {t('filters.clear')}
              </Button>
            )}
          </div>
        </div>

        {/* Table / states */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : errored ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <h3 className="font-semibold text-destructive">{t('dashboard.error')}</h3>
            <Button className="mt-4" onClick={load} variant="outline">
              {t('dashboard.retry')}
            </Button>
          </div>
        ) : rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <BookMarked className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <h3 className="font-semibold">{t('dashboard.empty')}</h3>
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => navigate('/reservations/new')}
            >
              {t('dashboard.empty_cta')}
            </Button>
          </div>
        ) : (
          <div className="rounded-lg border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="text-left px-3 py-2">{t('columns.code')}</th>
                    <th className="text-left px-3 py-2">{t('columns.product')}</th>
                    <th className="text-left px-3 py-2">{t('columns.customer')}</th>
                    <th className="text-left px-3 py-2">{t('columns.type')}</th>
                    <th className="text-left px-3 py-2">{t('columns.when')}</th>
                    <th className="text-left px-3 py-2">{t('columns.status')}</th>
                    <th className="text-right px-3 py-2">{t('columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const cancelled = r.status === 'cancelled';
                    const canDownloadIcs = !!r.access_token && !cancelled;
                    const landingUrl = r.access_token ? `/rsv/${r.access_token}` : null;
                    return (
                      <tr key={r.id} className={`border-t hover:bg-muted/30 ${cancelled ? 'opacity-60' : ''}`}>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-medium">{r.code}</span>
                            <CopyButton value={r.code} title={t('actions.copy_code')} />
                          </div>
                        </td>
                        <td className="px-3 py-2 max-w-[180px]">
                          <div className="truncate" title={r.product_name}>{r.product_name}</div>
                        </td>
                        <td className="px-3 py-2 max-w-[200px]">
                          {r.holder_name && <div className="truncate">{r.holder_name}</div>}
                          {r.holder_email && (
                            <div className="text-xs text-muted-foreground truncate">{r.holder_email}</div>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <Badge className={`text-[10px] ${
                            r.reservation_flavor === 'range'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-purple-100 text-purple-700'
                          }`}>
                            {t(`flavor.${r.reservation_flavor}`)}
                          </Badge>
                        </td>
                        <td className="px-3 py-2">
                          <ReservationWhen r={r} />
                        </td>
                        <td className="px-3 py-2">
                          <Badge className={`text-[10px] ${
                            cancelled
                              ? 'bg-red-100 text-red-700'
                              : 'bg-emerald-100 text-emerald-700'
                          }`}>
                            {t(`status.${r.status}`)}
                          </Badge>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-end gap-0.5">
                            {landingUrl && (
                              <a
                                href={landingUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-muted transition-colors"
                                title={t('actions.open_landing')}
                              >
                                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
                              </a>
                            )}
                            {!cancelled && (
                              <button
                                type="button"
                                onClick={() => handleResend(r)}
                                disabled={resendingId === r.id}
                                className="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-muted transition-colors disabled:opacity-50"
                                title={t('actions.resend')}
                              >
                                {resendingId === r.id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                                )}
                              </button>
                            )}
                            {canDownloadIcs && (
                              <button
                                type="button"
                                onClick={() => handleDownloadIcs(r)}
                                className="inline-flex items-center justify-center h-7 w-7 rounded hover:bg-muted transition-colors"
                                title={t('actions.download_ics')}
                              >
                                <Download className="h-3.5 w-3.5 text-muted-foreground" />
                              </button>
                            )}
                            {r.order_id && (
                              <button
                                type="button"
                                onClick={() => navigate(`/orders?selected=${r.order_id}`)}
                                className="ml-1 text-[11px] text-primary hover:underline"
                                title={t('actions.open_order')}
                              >
                                {t('actions.open_order')}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {rows.length >= 200 && (
              <div className="border-t px-3 py-2 text-center text-xs text-muted-foreground">
                {t('dashboard.load_more')} — {t('dashboard.loading')}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
