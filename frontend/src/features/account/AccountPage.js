/**
 * AccountPage — /account (P3, Passaporto Ritiri).
 *
 * L'area personale dell'utente finale: TUTTE le prenotazioni, di TUTTI
 * gli operatori, in un posto solo. Saldi in scadenza pagabili con un
 * click (i /pay link eterni del ledger), pass QR, profilo.
 * Mobile-first, noindex. Sessione: localStorage platform_token.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Loader2, Calendar, MapPin, Ticket, LogOut, CreditCard, ChevronRight,
} from 'lucide-react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import MarketplaceShell from '../storefront/components/MarketplaceShell';

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

const eur = (minor, currency = 'EUR') => new Intl.NumberFormat('it-IT', {
  style: 'currency', currency, maximumFractionDigits: 2,
}).format((minor || 0) / 100);

const fmtDate = (iso, lang) => {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(lang, {
      weekday: 'short', day: 'numeric', month: 'long', year: 'numeric',
    });
  } catch { return iso; }
};

const ROW_LABELS = {
  deposit: 'Caparra', balance: 'Saldo', installment: 'Rata', full: 'Pagamento',
};
const ROW_STATUS_STYLE = {
  paid: 'text-emerald-700', paid_manual: 'text-emerald-700',
  pending: 'text-gray-600', overdue: 'text-red-600 font-semibold',
  at_risk: 'text-amber-700',
};

export default function AccountPage() {
  const { t, i18n } = useTranslation('landings');
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState(false);

  useSeoMeta({ title: 'Le mie esperienze', noindex: true });
  useEffect(() => {
    const meta = document.createElement('meta');
    meta.name = 'robots'; meta.content = 'noindex';
    document.head.appendChild(meta);
    return () => { document.head.removeChild(meta); };
  }, []);

  const authHeaders = useCallback(() => {
    const tk = localStorage.getItem(PLATFORM_TOKEN_KEY);
    return tk ? { Authorization: `Bearer ${tk}` } : null;
  }, []);

  useEffect(() => {
    const headers = authHeaders();
    if (!headers) { navigate('/account/accedi', { replace: true }); return; }
    let mounted = true;
    Promise.all([
      platformApi.get('/platform/me', { headers }),
      platformApi.get('/platform/me/orders', { headers }),
    ]).then(([meRes, ordRes]) => {
      if (!mounted) return;
      setMe(meRes.data);
      setOrders(ordRes.data.orders || []);
    }).catch((err) => {
      if (!mounted) return;
      if (err?.response?.status === 401) {
        localStorage.removeItem(PLATFORM_TOKEN_KEY);
        navigate('/account/accedi', { replace: true });
      } else {
        setError(true);
      }
    });
    return () => { mounted = false; };
  }, [authHeaders, navigate]);

  const logout = () => {
    localStorage.removeItem(PLATFORM_TOKEN_KEY);
    navigate('/');
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <p className="text-sm text-gray-600">
          {t('landings:account.loadError', { defaultValue: 'Non riusciamo a caricare le prenotazioni. Riprova tra poco.' })}
        </p>
      </div>
    );
  }

  if (!me || orders === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const now = new Date().toISOString();
  const upcoming = orders.filter(o => o.start_at && o.start_at >= now);
  const past = orders.filter(o => !o.start_at || o.start_at < now);
  const dueRows = orders.flatMap(o =>
    (o.payment_rows || [])
      .filter(r => r.pay_token)
      .map(r => ({ ...r, order: o })));

  const OrderCard = ({ o }) => (
    <div className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate">{o.retreat_title}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {o.operator_name}{o.order_number ? ` · ${o.order_number}` : ''}
          </p>
        </div>
        <span className="shrink-0 text-sm font-bold text-gray-900">
          {new Intl.NumberFormat('it-IT', { style: 'currency', currency: o.currency || 'EUR', maximumFractionDigits: 0 }).format(o.total || 0)}
        </span>
      </div>
      {(o.start_at || o.location) && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          {o.start_at && (
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" />{fmtDate(o.start_at, i18n.language)}
            </span>
          )}
          {o.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3 w-3" />{o.location}
            </span>
          )}
        </div>
      )}
      {(o.payment_rows || []).length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2 space-y-1.5">
          {o.payment_rows.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className={ROW_STATUS_STYLE[r.status] || 'text-gray-600'}>
                {ROW_LABELS[r.kind] || r.kind} · {eur(r.amount_minor, o.currency)}
                {r.status === 'paid' || r.status === 'paid_manual'
                  ? ` — ${t('landings:account.rowPaid', { defaultValue: 'pagato' })}`
                  : r.due_at
                    ? ` — ${t('landings:account.rowDue', { defaultValue: 'entro il' })} ${new Date(r.due_at).toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' })}`
                    : ''}
              </span>
              {r.pay_token && (
                <a href={`${API_BASE}/api/public/pay/${r.pay_token}`}
                  className="inline-flex items-center gap-1 rounded-lg bg-primary text-primary-foreground px-2.5 py-1 font-semibold">
                  <CreditCard className="h-3 w-3" />
                  {t('landings:account.payNow', { defaultValue: 'Paga ora' })}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
      {(o.tickets || []).filter(tk => tk.access_token).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {o.tickets.filter(tk => tk.access_token).map((tk, i) => (
            <Link key={tk.access_token} to={`/t/${tk.access_token}`}
              className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline">
              <Ticket className="h-3 w-3" />
              {t('landings:account.ticketN', { n: i + 1, defaultValue: `Pass ${i + 1}` })}
            </Link>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <MarketplaceShell>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gradient-sidebar text-white">
        <div className="max-w-2xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">
              {t('landings:account.title', { defaultValue: 'Le mie prenotazioni' })}
            </h1>
            <p className="text-white/70 text-sm">{me.email}</p>
          </div>
          <button onClick={logout} aria-label="Esci"
            className="rounded-lg bg-white/10 p-2 hover:bg-white/20 transition-colors">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {dueRows.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-amber-800 mb-2">
              {t('landings:account.dueTitle', { defaultValue: 'Pagamenti in scadenza' })}
            </h2>
            <div className="space-y-2">
              {dueRows.map((r, i) => (
                <a key={i} href={`${API_BASE}/api/public/pay/${r.pay_token}`}
                  className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 hover:bg-amber-100 transition-colors">
                  <div className="text-sm">
                    <p className="font-semibold text-amber-900">
                      {ROW_LABELS[r.kind] || r.kind} · {eur(r.amount_minor, r.order.currency)}
                    </p>
                    <p className="text-xs text-amber-800">{r.order.retreat_title}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-amber-700" />
                </a>
              ))}
            </div>
          </section>
        )}

        <section>
          <h2 className="text-sm font-semibold text-gray-900 mb-2">
            {t('landings:account.upcomingTitle', { defaultValue: 'Prossimi ritiri' })}
          </h2>
          {upcoming.length === 0 ? (
            <div className="rounded-2xl border border-gray-200 bg-white p-5 text-center">
              <p className="text-sm text-gray-600">
                {t('landings:account.noUpcoming', { defaultValue: 'Nessun ritiro in programma.' })}
              </p>
              <Link to="/" className="text-sm font-medium text-primary hover:underline">
                {t('landings:account.browse', { defaultValue: 'Scopri i prossimi ritiri →' })}
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {upcoming.map(o => <OrderCard key={o.id} o={o} />)}
            </div>
          )}
        </section>

        {past.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-500 mb-2">
              {t('landings:account.pastTitle', { defaultValue: 'Passati' })}
            </h2>
            <div className="space-y-3 opacity-80">
              {past.map(o => <OrderCard key={o.id} o={o} />)}
            </div>
          </section>
        )}
      </main>
    </div>
    </MarketplaceShell>
  );
}
