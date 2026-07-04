/**
 * OperatorHome — la home dell'operatore ritiri (D3, 4/7/2026).
 *
 * Tre card auto-alimentate, zero configurazione: al primo login si
 * capisce in 5 secondi come va il business. Sostituisce come primo
 * impatto l'empty state tecnico "pinna i KPI dai moduli" (che resta
 * sotto, come personalizzazione avanzata).
 *
 *   1. Prossimi ritiri   — /event-occurrences/admin/list (published,
 *                          upcoming): data, posti venduti/capienza
 *   2. Incassi           — /orders/payments-overview (libro mastro):
 *                          incassato / in arrivo / in ritardo
 *   3. Da fare           — stessi conteggi della chip "Da gestire" di
 *                          Ordini (review_state) + bozze
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar, Wallet, ListTodo, ArrowRight, Users } from 'lucide-react';
import api from '../../api/client';

const eur = (minor) => new Intl.NumberFormat('it-IT', {
  style: 'currency', currency: 'EUR', maximumFractionDigits: 0,
}).format((minor || 0) / 100);

const fmtDate = (iso, lang) => {
  try {
    return new Date(iso).toLocaleDateString(lang, { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return iso; }
};

export default function OperatorHome() {
  const { t, i18n } = useTranslation('dashboard');
  const [retreats, setRetreats] = useState(null);   // null = loading
  const [payments, setPayments] = useState(null);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      api.get('/event-occurrences/admin/list', { params: { status: 'published', when: 'upcoming', limit: 4 } }),
      api.get('/orders/payments-overview'),
    ]).then(([occRes, payRes]) => {
      if (!mounted) return;
      // /admin/list risponde {events, total} — normalizza difensivamente
      const occData = occRes.status === 'fulfilled' ? occRes.value.data : null;
      setRetreats(Array.isArray(occData) ? occData : (occData?.events || []));
      setPayments(payRes.status === 'fulfilled' ? payRes.value.data : null);
    });
    return () => { mounted = false; };
  }, []);

  const todo = (payments?.needs_action_count || 0);
  const drafts = (payments?.draft_count || 0);

  const cardCls = 'rounded-2xl border bg-card p-4 flex flex-col';
  const headCls = 'flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3';

  return (
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

      {/* ── Incassi ── */}
      <div className={cardCls}>
        <div className={headCls}>
          <Wallet className="h-3.5 w-3.5" />
          {t('home.payments_title', { defaultValue: 'Incassi' })}
        </div>
        {payments === null ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : (
          <div className="flex-1 space-y-2">
            <div>
              <p className="text-2xl font-bold tracking-tight">{eur(payments.incassato_minor)}</p>
              <p className="text-xs text-muted-foreground">{t('home.payments_collected', { defaultValue: 'incassati' })}</p>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{t('home.payments_expected', { defaultValue: 'In arrivo' })}</span>
              <span className="font-semibold tabular-nums">{eur(payments.in_arrivo_minor)}</span>
            </div>
            {payments.in_ritardo_minor > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-destructive">{t('home.payments_overdue', { defaultValue: 'In ritardo' })}</span>
                <span className="font-semibold text-destructive tabular-nums">{eur(payments.in_ritardo_minor)}</span>
              </div>
            )}
          </div>
        )}
        <Link to="/orders" className="mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          {t('home.payments_all', { defaultValue: 'Vai agli ordini' })} <ArrowRight className="h-3 w-3" />
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
        ) : todo === 0 && drafts === 0 ? (
          <p className="flex-1 text-sm text-muted-foreground flex items-center">
            {t('home.todo_empty', { defaultValue: 'Tutto in ordine. Niente da gestire.' })}
          </p>
        ) : (
          <ul className="flex-1 space-y-2 text-sm">
            {todo > 0 && (
              <li>
                <Link to="/orders?triage=review" className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800 hover:bg-amber-100 transition-colors">
                  <span>{t('home.todo_review', { defaultValue: 'Ordini da gestire' })}</span>
                  <span className="font-bold">{todo}</span>
                </Link>
              </li>
            )}
            {drafts > 0 && (
              <li>
                <Link to="/orders?status=draft" className="flex items-center justify-between rounded-lg border bg-muted/40 px-3 py-2 hover:bg-muted transition-colors">
                  <span>{t('home.todo_drafts', { defaultValue: 'Bozze aperte' })}</span>
                  <span className="font-bold">{drafts}</span>
                </Link>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
