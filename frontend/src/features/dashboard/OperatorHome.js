/**
 * OperatorHome — il radar dell'operatore (D3 → CF4, INSIGHTS_ACTION_PLAN).
 *
 * Tre card auto-alimentate, zero configurazione: in 5 secondi si vede
 * come va il business e cosa fare adesso. CF4 assorbe qui i widget
 * pinnabili (rimossi): la home non si configura, si legge.
 *
 *   1. Prossimi ritiri — /event-occurrences/admin/list: data, posti
 *   2. Incassi         — /analytics/cashflow (STESSA fonte della
 *                        pagina /incassi: nessun numero parallelo):
 *                        incassato/in arrivo/in ritardo + sparkline
 *                        mensile → link a /incassi
 *   3. Da fare         — ordini da gestire, bozze, recensioni in
 *                        attesa, pagamenti in ritardo: ogni voce è un
 *                        link al posto dove si agisce
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar, Wallet, ListTodo, ArrowRight, Users, Eye } from 'lucide-react';
import api from '../../api/client';
import { MiniBars } from '../../components/charts';
import { formatCurrency } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';

const fmtDate = (iso, lang) => {
  try {
    return new Date(iso).toLocaleDateString(lang, { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return iso; }
};

const monthShort = (ym, lang) => {
  try {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString(lang, { month: 'short' });
  } catch { return ym; }
};

export default function OperatorHome() {
  const { t, i18n } = useTranslation('dashboard');
  const currency = useCurrency();
  const [retreats, setRetreats] = useState(null);   // null = loading
  const [payments, setPayments] = useState(null);   // conteggi da-fare ordini
  const [cashflow, setCashflow] = useState(null);   // fonte unica incassi
  const [reviewsPending, setReviewsPending] = useState(0);
  const [obSteps, setObSteps] = useState(null);
  const [visibility, setVisibility] = useState(null); // VT5 — specchietto

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      api.get('/event-occurrences/admin/list', { params: { status: 'published', when: 'upcoming', limit: 4 } }),
      api.get('/orders/payments-overview'),
      api.get('/analytics/cashflow'),
      api.get('/reviews', { params: { status: 'pending' } }),
      api.get('/organizations/current/onboarding-status'),
      api.get('/analytics/visibility'),
    ]).then(([occRes, payRes, cfRes, revRes, obRes, visRes]) => {
      if (!mounted) return;
      const occData = occRes.status === 'fulfilled' ? occRes.value.data : null;
      setRetreats(Array.isArray(occData) ? occData : (occData?.events || []));
      setPayments(payRes.status === 'fulfilled' ? payRes.value.data : {});
      setCashflow(cfRes.status === 'fulfilled' ? cfRes.value.data : {});
      setReviewsPending(revRes.status === 'fulfilled' ? (revRes.value.data?.pending_count || 0) : 0);
      setObSteps(obRes.status === 'fulfilled' ? (obRes.value.data?.steps || null) : null);
      setVisibility(visRes.status === 'fulfilled' ? visRes.value.data : null);
    });
    return () => { mounted = false; };
  }, []);

  const fmt = (n) => formatCurrency(n || 0, currency);
  const todo = (payments?.needs_action_count || 0);
  const drafts = (payments?.draft_count || 0);
  const s = cashflow?.summary;
  const overdueCount = (cashflow?.overdue || []).length;
  const bars = (cashflow?.months || []).map((m) => ({
    label: monthShort(m.month, i18n.language), value: m.incassato,
  }));
  const nothingTodo = todo === 0 && drafts === 0 && reviewsPending === 0 && overdueCount === 0;

  const cardCls = 'rounded-2xl border bg-card p-4 flex flex-col';
  const headCls = 'flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3';
  const todoRow = 'flex items-center justify-between rounded-lg border px-3 py-2 transition-colors';

  // GT1b — il calendario pubblico mostra solo ritiri prenotabili online:
  // se hai pubblicato ma Stripe non è attivo, i tuoi ritiri NON compaiono.
  const calendarBlocked = obSteps && obSteps.retreat_published && !obSteps.stripe_connected;

  return (
    <div className="space-y-4">
    {calendarBlocked && (
      <div className="rounded-2xl border border-[#C97B5D]/50 bg-[#C97B5D]/10 p-4 flex items-start gap-3">
        <span aria-hidden>⚠️</span>
        <div className="text-sm">
          <p className="font-semibold text-[#8a4a33]">
            {t('home.calendar_blocked_title', { defaultValue: 'I tuoi ritiri non compaiono nel calendario pubblico' })}
          </p>
          <p className="text-[#8a4a33]/90 mt-0.5">
            {t('home.calendar_blocked_body', { defaultValue: 'Nel calendario di Aurya entrano solo i ritiri prenotabili online. Attiva i pagamenti per essere visibile e ricevere prenotazioni.' })}
          </p>
          <Link to="/settings" className="inline-block mt-1.5 text-sm font-semibold text-[#376254] hover:underline">
            {t('home.calendar_blocked_cta', { defaultValue: 'Attiva i pagamenti online' })} →
          </Link>
        </div>
      </div>
    )}
    <div className="grid gap-4 md:grid-cols-3">
      {/* ── Prossimi ritiri ── */}
      <div className={cardCls}>
        <div className={headCls}>
          <Calendar className="h-3.5 w-3.5" />
          {t('home.upcoming_title', { defaultValue: 'Prossimi ritiri' })}
        </div>
        {retreats === null ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : retreats.length === 0 ? (
          <div className="flex-1 flex flex-col justify-center">
            <p className="text-sm text-muted-foreground">
              {t('home.upcoming_empty', { defaultValue: 'Nessun ritiro in programma.' })}
            </p>
            <Link to="/events/new" className="text-sm font-medium text-primary hover:underline mt-1">
              {t('home.upcoming_cta', { defaultValue: 'Crea il primo ritiro' })} →
            </Link>
          </div>
        ) : (
          <ul className="space-y-2.5 flex-1">
            {retreats.map((r) => (
              <li key={r.id}>
                <Link to={`/events/${r.id}`} className="group flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                      {r.product_name}
                    </p>
                    <p className="text-xs text-muted-foreground">{fmtDate(r.start_at, i18n.language)}</p>
                  </div>
                  {r.capacity > 0 && (
                    <span className="shrink-0 inline-flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
                      <Users className="h-3 w-3" />
                      {r.reserved_seats ?? 0}/{r.capacity}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
        <Link to="/events" className="mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          {t('home.upcoming_all', { defaultValue: 'Tutti i ritiri' })} <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* ── Incassi (fonte: /analytics/cashflow, come la pagina) ── */}
      <div className={cardCls}>
        <div className={headCls}>
          <Wallet className="h-3.5 w-3.5" />
          {t('home.payments_title', { defaultValue: 'Incassi' })}
        </div>
        {cashflow === null ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : (
          <div className="flex-1 space-y-2">
            <div>
              <p className="text-2xl font-bold tracking-tight">{fmt(s?.incassato)}</p>
              <p className="text-xs text-muted-foreground">{t('home.payments_collected12m', { defaultValue: 'incassati (12 mesi)' })}</p>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{t('home.payments_expected', { defaultValue: 'In arrivo' })}</span>
              <span className="font-semibold tabular-nums">{fmt(s?.in_arrivo)}</span>
            </div>
            {(s?.in_ritardo || 0) > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-[#C97B5D]">{t('home.payments_overdue', { defaultValue: 'In ritardo' })}</span>
                <span className="font-semibold text-[#C97B5D] tabular-nums">{fmt(s.in_ritardo)}</span>
              </div>
            )}
            {bars.some((b) => b.value > 0) && (
              <MiniBars data={bars} height={44} valueFormatter={fmt} />
            )}
          </div>
        )}
        <Link to="/incassi" className="mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          {t('home.payments_all_cf', { defaultValue: 'Vai a Incassi' })} <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* ── Da fare ── */}
      <div className={cardCls}>
        <div className={headCls}>
          <ListTodo className="h-3.5 w-3.5" />
          {t('home.todo_title', { defaultValue: 'Da fare' })}
        </div>
        {payments === null ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : nothingTodo ? (
          <p className="flex-1 text-sm text-muted-foreground flex items-center">
            {t('home.todo_empty', { defaultValue: 'Tutto in ordine. Niente da gestire.' })}
          </p>
        ) : (
          <ul className="flex-1 space-y-2 text-sm">
            {overdueCount > 0 && (
              <li>
                <Link to="/incassi" className={`${todoRow} border-[#C97B5D]/50 bg-[#C97B5D]/10 text-[#8a4a33] hover:bg-[#C97B5D]/20`}>
                  <span>{t('home.todo_overdue', { defaultValue: 'Pagamenti in ritardo' })}</span>
                  <span className="font-bold">{overdueCount}</span>
                </Link>
              </li>
            )}
            {todo > 0 && (
              <li>
                <Link to="/orders?triage=review" className={`${todoRow} border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100`}>
                  <span>{t('home.todo_review', { defaultValue: 'Ordini da gestire' })}</span>
                  <span className="font-bold">{todo}</span>
                </Link>
              </li>
            )}
            {reviewsPending > 0 && (
              <li>
                <Link to="/reviews" className={`${todoRow} border-border bg-muted/40 hover:bg-muted`}>
                  <span>{t('home.todo_reviews', { defaultValue: 'Recensioni in attesa' })}</span>
                  <span className="font-bold">{reviewsPending}</span>
                </Link>
              </li>
            )}
            {drafts > 0 && (
              <li>
                <Link to="/orders?status=draft" className={`${todoRow} border-border bg-muted/40 hover:bg-muted`}>
                  <span>{t('home.todo_drafts', { defaultValue: 'Bozze aperte' })}</span>
                  <span className="font-bold">{drafts}</span>
                </Link>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>

    {/* ── Visibilità (VT5): il funnel del mese in una riga ── */}
    {(visibility?.summary?.visits?.current || 0) > 0 && (
      <div className="mt-4 rounded-2xl border bg-card p-4">
        <div className={headCls}>
          <Eye className="h-3.5 w-3.5" />
          {t('home.visibility_title', { defaultValue: 'Visibilità' })}
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <span>
            <span className="font-bold tabular-nums">{visibility.summary.impressions?.current || 0}</span>{' '}
            <span className="text-muted-foreground">{t('home.visibility_impressions', { defaultValue: 'impression' })}</span>
          </span>
          <span>
            <span className="font-bold tabular-nums">{visibility.summary.visits.current}</span>{' '}
            <span className="text-muted-foreground">{t('home.visibility_visits', { defaultValue: 'visite' })}</span>
          </span>
          <span>
            <span className="font-bold tabular-nums">{visibility.summary.bookings?.current || 0}</span>{' '}
            <span className="text-muted-foreground">{t('home.visibility_bookings', { defaultValue: 'prenotazioni' })}</span>
          </span>
          <Link to="/visibilita" className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
            {t('home.visibility_all', { defaultValue: 'Vai a Visibilità' })} <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    )}
    </div>
  );
}
