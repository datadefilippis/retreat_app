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
  Clock, BookOpen,
} from 'lucide-react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
// FQ3 — sezione preferiti meditazioni: componente isolato del modulo
// Frequenze, si carica da solo e sparisce se vuoto
import AccountFavorites from '../frequenze/AccountFavorites';
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

// AP2 — 'gio 31 lug, 15:00': la data e ora dell'appuntamento scelto al
// checkout servizi (service_slot dalla proiezione /platform/me/orders).
const fmtSlot = (slot, lang) => {
  if (!slot?.date) return null;
  try {
    const day = new Date(`${slot.date}T${slot.start_time || '00:00'}`)
      .toLocaleDateString(lang, { weekday: 'short', day: 'numeric', month: 'short' });
    return slot.start_time ? `${day}, ${slot.start_time}` : day;
  } catch { return slot.date; }
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
  // AP2 — guide riservate (solo per iscritti confermati alla lettera)
  const [guides, setGuides] = useState(null);

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

  // AP2 — lista delle guide riservate: stesso endpoint pubblico del blog
  // (/public/articles, flag gated), stessa regola lingua del Magazine.
  useEffect(() => {
    if (!me?.newsletter_subscriber) return undefined;
    let mounted = true;
    const lang = (i18n.language || 'it').slice(0, 2);
    platformApi.get('/public/articles', { params: { lang, page_size: 50 } })
      .then(res => {
        if (mounted) setGuides((res.data?.items || []).filter(a => a.gated));
      })
      .catch(() => { if (mounted) setGuides([]); });
    return () => { mounted = false; };
  }, [me, i18n.language]);

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
  // AP2 — anche l'appuntamento di un servizio (service_slot) conta come
  // data di inizio per la divisione prossimi/passati; gli annullati non
  // stanno mai tra i prossimi.
  const startOf = (o) => o.start_at
    || (o.service_slot?.date
      ? `${o.service_slot.date}T${o.service_slot.start_time || '00:00'}` : null);
  const upcoming = orders.filter(o => o.status !== 'cancelled'
    && startOf(o) && startOf(o) >= now);
  const past = orders.filter(o => !upcoming.includes(o));
  const dueRows = orders.flatMap(o =>
    (o.payment_rows || [])
      .filter(r => r.pay_token)
      .map(r => ({ ...r, order: o })));

  // AP2 — badge di stato chiaro: la coppia status + transaction_mode
  // della proiezione ordini. Un draft in modalita' richiesta E' una
  // richiesta inviata; un draft direct e' in attesa di pagamento (le
  // righe pagamento sotto dicono gia' tutto, niente badge).
  const statusBadge = (o) => {
    if (o.status === 'cancelled') {
      return { label: t('landings:account.statusCancelled', { defaultValue: 'Annullato' }), cls: 'bg-red-50 text-red-600' };
    }
    if (o.status === 'completed') {
      return { label: t('landings:account.statusCompleted', { defaultValue: 'Completato' }), cls: 'bg-gray-100 text-gray-600' };
    }
    if (o.status === 'confirmed') {
      return { label: t('landings:account.statusConfirmed', { defaultValue: 'Confermato' }), cls: 'bg-emerald-50 text-emerald-700' };
    }
    if (o.status === 'draft' && o.transaction_mode === 'request') {
      return { label: t('landings:account.statusRequestSent', { defaultValue: 'Richiesta inviata' }), cls: 'bg-amber-50 text-amber-800' };
    }
    return null;
  };

  const OrderCard = ({ o }) => {
    const badge = statusBadge(o);
    return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate">{o.retreat_title}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {o.operator_name}{o.order_number ? ` · ${o.order_number}` : ''}
          </p>
          {badge && (
            <span className={`mt-1.5 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.cls}`}
              data-testid="order-status-badge">
              {badge.label}
            </span>
          )}
        </div>
        <span className="shrink-0 text-sm font-bold text-gray-900">
          {new Intl.NumberFormat('it-IT', { style: 'currency', currency: o.currency || 'EUR', maximumFractionDigits: 0 }).format(o.total || 0)}
        </span>
      </div>
      {(o.start_at || o.location || o.service_slot) && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          {o.start_at && (
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" />{fmtDate(o.start_at, i18n.language)}
            </span>
          )}
          {!o.start_at && o.service_slot && (
            <span className="inline-flex items-center gap-1" data-testid="order-service-slot">
              <Clock className="h-3 w-3" />
              {t('landings:account.appointment', { defaultValue: 'Appuntamento' })}: {fmtSlot(o.service_slot, i18n.language)}
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
      {/* TA2 — le prenotazioni servizio hanno la loro landing /b/ come i
          pass /t/: prima il link viveva solo nell'email di conferma. */}
      {(o.bookings || []).filter(bk => bk.access_token).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {o.bookings.filter(bk => bk.access_token).map((bk, i) => (
            <Link key={bk.access_token} to={`/b/${bk.access_token}`}
              className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline">
              <Ticket className="h-3 w-3" />
              {t('landings:account.bookingN', {
                n: i + 1,
                defaultValue: (o.bookings.filter(b2 => b2.access_token).length > 1
                  ? `Appuntamento ${i + 1}` : 'Dettagli appuntamento'),
              })}
            </Link>
          ))}
        </div>
      )}
    </div>
    );
  };

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

        <AccountFavorites />

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

        {/* AP2 — Guide e materiale: le guide riservate del Magazine per
            gli iscritti confermati alla lettera; per gli altri, l'invito
            a iscriversi (/newsletter). */}
        <section data-testid="account-guides">
          <h2 className="text-sm font-semibold text-gray-900 mb-2">
            {t('landings:account.guidesTitle', { defaultValue: 'Guide e materiale' })}
          </h2>
          {me.newsletter_subscriber ? (
            guides === null ? (
              <div className="rounded-2xl border border-gray-200 bg-white p-5 flex justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            ) : guides.length === 0 ? (
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-sm text-gray-600">
                  {t('landings:account.guidesEmpty', { defaultValue: 'Nessuna guida riservata disponibile in questa lingua, per ora.' })}
                </p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-white divide-y divide-gray-100">
                <p className="px-4 pt-3 pb-1 text-xs text-gray-500">
                  {t('landings:account.guidesIntro', { defaultValue: 'Sei iscritto alla lettera di Aurya: queste guide sono sbloccate per te.' })}
                </p>
                {guides.map(g => (
                  <Link key={g.slug} to={`/blog/${g.slug}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50 transition-colors">
                    <span className="flex items-center gap-2 min-w-0">
                      <BookOpen className="h-4 w-4 shrink-0 text-primary" />
                      <span className="text-sm text-gray-900 truncate">{g.title}</span>
                    </span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-gray-400" />
                  </Link>
                ))}
              </div>
            )
          ) : (
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="text-sm text-gray-600">
                {t('landings:account.guidesInvite', { defaultValue: 'Le guide riservate del Magazine sono per chi riceve la lettera di Aurya. L\'iscrizione è gratuita e la annulli quando vuoi.' })}
              </p>
              <Link to="/newsletter"
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                {t('landings:account.guidesCta', { defaultValue: 'Iscriviti alla lettera' })}
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </section>

        {/* TA5 — Il tuo account: password, dati (GDPR), sessioni.
            Export e cancellazione esistevano solo come API: la promessa
            dell'email di claim ("puoi impostare una password") e i
            diritti GDPR ora hanno una superficie. */}
        <AccountSettingsSection me={me} authHeaders={authHeaders} onLogout={logout} t={t} />
      </main>
    </div>
    </MarketplaceShell>
  );
}

function AccountSettingsSection({ me, authHeaders, onLogout, t }) {
  const [pwOpen, setPwOpen] = useState(false);
  const [pwCurrent, setPwCurrent] = useState('');
  const [pwNew, setPwNew] = useState('');
  const [pwMsg, setPwMsg] = useState(null);
  const [pwSaving, setPwSaving] = useState(false);
  const [hasPassword, setHasPassword] = useState(!!me?.has_password);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const savePassword = async (e) => {
    e.preventDefault();
    setPwSaving(true); setPwMsg(null);
    try {
      await platformApi.post('/platform/me/password', {
        new_password: pwNew,
        current_password: hasPassword ? pwCurrent : undefined,
      }, { headers: authHeaders() });
      setPwMsg({ ok: true, text: t('landings:account.pwSaved', { defaultValue: 'Password salvata. Da ora puoi accedere con email e password.' }) });
      setHasPassword(true); setPwCurrent(''); setPwNew('');
    } catch (err) {
      setPwMsg({ ok: false, text: err?.response?.data?.detail || t('landings:account.pwError', { defaultValue: 'Non siamo riusciti a salvare la password.' }) });
    } finally { setPwSaving(false); }
  };

  const downloadData = async () => {
    try {
      const res = await platformApi.get('/platform/me/export', { headers: authHeaders() });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'aurya-i-miei-dati.json';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch { /* best-effort */ }
  };

  const logoutAll = async () => {
    try {
      await platformApi.post('/platform/auth/logout-all', {}, { headers: authHeaders() });
    } catch { /* il logout locale avviene comunque */ }
    onLogout();
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await platformApi.delete('/platform/me', { headers: authHeaders() });
      onLogout();
    } catch {
      setDeleting(false);
    }
  };

  return (
    <section data-testid="account-settings">
      <h2 className="text-sm font-semibold text-gray-900 mb-2">
        {t('landings:account.settingsTitle', { defaultValue: 'Il tuo account' })}
      </h2>
      <div className="rounded-2xl border border-gray-200 bg-white divide-y divide-gray-100">
        <div className="px-4 py-3">
          <button type="button" onClick={() => setPwOpen(v => !v)}
            className="flex w-full items-center justify-between text-sm text-gray-900">
            <span>{hasPassword
              ? t('landings:account.pwChange', { defaultValue: 'Cambia password' })
              : t('landings:account.pwSet', { defaultValue: 'Imposta una password' })}</span>
            <ChevronRight className={`h-4 w-4 text-gray-400 transition-transform ${pwOpen ? 'rotate-90' : ''}`} />
          </button>
          {pwOpen && (
            <form onSubmit={savePassword} className="mt-3 space-y-2">
              {hasPassword && (
                <input type="password" required value={pwCurrent}
                  onChange={e => setPwCurrent(e.target.value)}
                  placeholder={t('landings:account.pwCurrent', { defaultValue: 'Password attuale' })}
                  autoComplete="current-password"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              )}
              <input type="password" required value={pwNew}
                onChange={e => setPwNew(e.target.value)}
                placeholder={t('landings:account.pwNew', { defaultValue: 'Nuova password (min 12 caratteri, maiuscola, minuscola, numero)' })}
                autoComplete="new-password" minLength={12}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              {pwMsg && (
                <p className={`text-xs ${pwMsg.ok ? 'text-emerald-700' : 'text-red-600'}`}>{pwMsg.text}</p>
              )}
              <button type="submit" disabled={pwSaving}
                className="rounded-lg bg-primary text-white px-4 py-2 text-sm font-semibold disabled:opacity-50">
                {pwSaving
                  ? t('landings:account.pwSaving', { defaultValue: 'Salvataggio…' })
                  : t('landings:account.pwSave', { defaultValue: 'Salva password' })}
              </button>
            </form>
          )}
        </div>
        <button type="button" onClick={downloadData}
          className="flex w-full items-center justify-between px-4 py-3 text-sm text-gray-900 hover:bg-gray-50">
          <span>{t('landings:account.dataExport', { defaultValue: 'Scarica i tuoi dati' })}</span>
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </button>
        <button type="button" onClick={logoutAll}
          className="flex w-full items-center justify-between px-4 py-3 text-sm text-gray-900 hover:bg-gray-50">
          <span>{t('landings:account.logoutAll', { defaultValue: 'Esci da tutti i dispositivi' })}</span>
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </button>
        <div className="px-4 py-3">
          {!deleteOpen ? (
            <button type="button" onClick={() => setDeleteOpen(true)}
              className="text-sm text-red-600 hover:underline">
              {t('landings:account.deleteAccount', { defaultValue: 'Elimina il mio account' })}
            </button>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-gray-600">
                {t('landings:account.deleteConfirmText', { defaultValue: 'L\'account e i tuoi dati Aurya vengono eliminati. Gli ordini già fatti restano agli operatori come previsto dalla legge, ma non saranno più collegati a te. L\'operazione non si può annullare.' })}
              </p>
              <div className="flex gap-2">
                <button type="button" onClick={deleteAccount} disabled={deleting}
                  className="rounded-lg bg-red-600 text-white px-3 py-1.5 text-xs font-semibold disabled:opacity-50">
                  {deleting
                    ? t('landings:account.deleting', { defaultValue: 'Eliminazione…' })
                    : t('landings:account.deleteConfirm', { defaultValue: 'Sì, elimina definitivamente' })}
                </button>
                <button type="button" onClick={() => setDeleteOpen(false)}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700">
                  {t('landings:account.deleteCancel', { defaultValue: 'Annulla' })}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
