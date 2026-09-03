/**
 * OperatorHome — il radar dell'operatore (D3 → CF4 → IG4).
 *
 * Auto-alimentata, zero configurazione: in 5 secondi si vede come va
 * il business e cosa fare adesso. CF4 assorbe qui i widget pinnabili
 * (rimossi): la home non si configura, si legge.
 *
 * IG4 (3/9/2026, ciclo VETRINA) — la lettura in un colpo solo, dall'alto:
 *   0. Avviso calendario bloccato (GT1b) — se c'è, viene prima di tutto.
 *   1. Panoramica — quattro numeri del MESE con il loro significato:
 *      incassato · in arrivo · prenotazioni · visite al profilo.
 *      Ogni tessera è un link alla pagina dove si approfondisce.
 *      La card «Visibilità» (VT5) si fonde qui: prima stava in fondo
 *      e compariva solo con visite > 0; uno zero è una verità.
 *   2. Da fare — le azioni PRIMA dei grafici: ordini da gestire,
 *      bozze, recensioni, ritardi. Ogni voce è un link al posto dove
 *      si agisce. Se non c'è nulla, una riga serena, non una card.
 *   3. Prossimi ritiri (posti come barra) · Andamento incassi mese per
 *      mese, fino al mese corrente (i secchi del cashflow includono 3
 *      mesi futuri a zero: nel grafico sembravano un crollo). Il totale
 *      «12 mesi» resta la cifra rotante del summary, come in /incassi.
 *   Nessun saluto con il nome: un saluto declinato sbaglia genere
 *   (scartato dal founder). La riga di apertura è la data di oggi,
 *   uguale per tutti.
 *
 * Fonti (le STESSE di prima, nessuna chiamata nuova):
 *   · /event-occurrences/admin/list  — prossimi ritiri, posti
 *   · /analytics/cashflow            — incassi (stessa fonte di /incassi)
 *   · /orders/payments-overview      — conteggi da-fare ordini
 *   · /reviews?status=pending        — recensioni in attesa
 *   · /organizations/current/onboarding-status — signals (stripe/ritiri)
 *   · /analytics/visibility          — visite/prenotazioni del mese
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar, Wallet, ListTodo, ArrowRight, Users, Eye, CalendarCheck, Clock } from 'lucide-react';
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

const todayLong = (lang) => {
  try {
    const s = new Date().toLocaleDateString(lang, { weekday: 'long', day: 'numeric', month: 'long' });
    return s.charAt(0).toUpperCase() + s.slice(1);
  } catch { return ''; }
};

const currentYm = () => new Date().toISOString().slice(0, 7);

/** confronto col mese scorso, in parole: niente frecce da decifrare */
function Delta({ cur, prev, t }) {
  if (!cur && !prev) return null;
  const d = (cur || 0) - (prev || 0);
  if (d === 0) {
    return <span className="text-[11px] text-muted-foreground">{t('home.delta_same', { defaultValue: 'come il mese scorso' })}</span>;
  }
  const up = d > 0;
  return (
    <span className={`text-[11px] font-medium ${up ? 'text-[#376254]' : 'text-muted-foreground'}`}>
      {up ? '+' : '−'}{Math.abs(d)} {t('home.delta_vs', { defaultValue: 'sul mese scorso' })}
    </span>
  );
}

/** una tessera della Panoramica: numero grande, cosa significa, dove approfondire */
function Tessera({ to, icon: Icon, label, value, sub, loading, testid }) {
  return (
    <Link
      to={to}
      data-testid={testid}
      className="group rounded-2xl border bg-card p-4 flex flex-col gap-1 min-h-[104px] hover:border-[#376254]/40 hover:shadow-sm transition-all"
    >
      <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {label}
      </span>
      {loading ? (
        <span className="h-8 w-24 animate-pulse rounded-md bg-muted mt-1" />
      ) : (
        <span className="text-2xl md:text-[28px] leading-tight font-bold tracking-tight tabular-nums text-foreground group-hover:text-[#376254] transition-colors">
          {value}
        </span>
      )}
      <span className="min-h-[16px] text-xs text-muted-foreground leading-snug">{sub}</span>
    </Link>
  );
}

export default function OperatorHome() {
  const { t, i18n } = useTranslation('dashboard');
  const currency = useCurrency();
  const [retreats, setRetreats] = useState(null);   // null = loading
  const [payments, setPayments] = useState(null);   // conteggi da-fare ordini
  const [cashflow, setCashflow] = useState(null);   // fonte unica incassi
  const [reviewsPending, setReviewsPending] = useState(0);
  const [obSteps, setObSteps] = useState(null);
  const [visibility, setVisibility] = useState(null); // VT5 — visite/prenotazioni del mese

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
      // TW4 — nel mondo snello stripe/ritiri vivono in `signals`,
      // nel legacy restano dentro `steps`
      setObSteps(obRes.status === 'fulfilled'
        ? (obRes.value.data?.signals || obRes.value.data?.steps || null) : null);
      // modulo visibilità spento (403) o errore: le due tessere del
      // mese NON compaiono — mai uno zero finto (false = non disponibile)
      setVisibility(visRes.status === 'fulfilled' ? (visRes.value.data || {}) : false);
    });
    return () => { mounted = false; };
  }, []);

  const fmt = (n) => formatCurrency(n || 0, currency);
  const todo = (payments?.needs_action_count || 0);
  const drafts = (payments?.draft_count || 0);
  const s = cashflow?.summary;
  // DC2 — il conteggio vero dal backend (la lista e' troncata a 50):
  // prima importo e numero potevano raccontare due storie diverse
  const overdueCount = s?.in_ritardo_count ?? (cashflow?.overdue || []).length;
  const months = cashflow?.months || [];
  const ym = currentYm();
  // i secchi del cashflow sono 8 mesi passati + corrente + 3 FUTURI:
  // i futuri (incassato = 0 per definizione) nel grafico sembravano
  // un crollo. Si disegna fino al mese corrente compreso.
  const bars = months.filter((m) => m.month <= ym).map((m) => ({
    label: monthShort(m.month, i18n.language), value: m.incassato,
  }));
  // il mese corrente cercato per chiave, senza fidarsi dell'ordine
  const thisMonth = months.find((m) => m.month === ym) || months[months.length - 1] || null;
  const nothingTodo = todo === 0 && drafts === 0 && reviewsPending === 0 && overdueCount === 0;
  const visAvailable = visibility !== false;
  const vis = visAvailable ? visibility?.summary : null;
  const visitsCur = vis?.visits?.current || 0;
  const visitsPrev = vis?.visits?.previous || 0;
  const bookCur = vis?.bookings?.current || 0;
  const bookPrev = vis?.bookings?.previous || 0;

  const cardCls = 'rounded-2xl border bg-card p-4 flex flex-col';
  const headCls = 'flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3';
  const todoRow = 'flex items-center justify-between rounded-lg border px-3 py-2 transition-colors';
  const footLink = 'mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground';

  // GT1b — il calendario pubblico mostra solo ritiri prenotabili online:
  // se hai pubblicato ma Stripe non è attivo, i tuoi ritiri NON compaiono.
  const calendarBlocked = obSteps && obSteps.retreat_published && !obSteps.stripe_connected;

  return (
    <div className="space-y-5" data-testid="operator-home">
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

    {/* ── 1. Panoramica: i quattro numeri del mese ── */}
    <section aria-labelledby="home-panoramica">
      <div className="flex items-baseline justify-between gap-3 mb-2.5">
        <h2 id="home-panoramica" className="text-sm font-semibold text-foreground">
          {t('home.overview_title', { defaultValue: 'Questo mese' })}
        </h2>
        <p className="text-xs text-muted-foreground" data-testid="home-oggi">{todayLong(i18n.language)}</p>
      </div>
      <div className={`grid gap-3 grid-cols-2 ${visAvailable ? 'lg:grid-cols-4' : 'lg:grid-cols-2'}`} data-testid="home-panoramica">
        <Tessera
          to="/incassi"
          testid="tile-incassato"
          icon={Wallet}
          label={t('home.tile_collected', { defaultValue: 'Incassato' })}
          loading={cashflow === null}
          value={fmt(thisMonth?.incassato)}
          sub={t('home.tile_collected_sub', { defaultValue: '{{amount}} negli ultimi 12 mesi', amount: fmt(s?.incassato) })}
        />
        <Tessera
          to="/incassi"
          testid="tile-in-arrivo"
          icon={Clock}
          label={t('home.payments_expected', { defaultValue: 'In arrivo' })}
          loading={cashflow === null}
          value={fmt(s?.in_arrivo)}
          sub={(s?.in_ritardo || 0) > 0 ? (
            <span className="text-[#C97B5D] font-medium">
              {t('home.tile_overdue_sub', { defaultValue: '{{amount}} in ritardo', amount: fmt(s.in_ritardo) })}
            </span>
          ) : t('home.tile_expected_sub', { defaultValue: 'da incassare, già prenotato' })}
        />
        {visAvailable && (
          <>
            <Tessera
              to="/orders"
              testid="tile-prenotazioni"
              icon={CalendarCheck}
              label={t('home.visibility_bookings_title', { defaultValue: 'Prenotazioni' })}
              loading={visibility === null}
              value={bookCur}
              sub={(bookCur || bookPrev)
                ? <Delta cur={bookCur} prev={bookPrev} t={t} />
                : t('home.tile_bookings_sub', { defaultValue: 'ordini confermati nel mese' })}
            />
            <Tessera
              to="/visibilita"
              testid="tile-visite"
              icon={Eye}
              label={t('home.visibility_visits_title', { defaultValue: 'Visite al profilo' })}
              loading={visibility === null}
              value={visitsCur}
              sub={(visitsCur || visitsPrev)
                ? <Delta cur={visitsCur} prev={visitsPrev} t={t} />
                : t('home.tile_visits_sub', { defaultValue: 'chi apre la tua pagina pubblica' })}
            />
          </>
        )}
      </div>
    </section>

    {/* ── 2. Da fare: le azioni prima dei grafici ── */}
    <section aria-labelledby="home-dafare" data-testid="home-dafare">
      {payments === null ? (
        <div className="h-12 animate-pulse rounded-2xl bg-muted" />
      ) : nothingTodo ? (
        <p className="flex items-center gap-2 rounded-2xl border border-dashed px-4 py-3 text-sm text-muted-foreground">
          <ListTodo className="h-4 w-4 text-[#376254]" aria-hidden />
          <span id="home-dafare">{t('home.todo_empty', { defaultValue: 'Tutto in ordine. Niente da gestire.' })}</span>
        </p>
      ) : (
        <div className={cardCls}>
          <div className={headCls}>
            <ListTodo className="h-3.5 w-3.5" />
            <span id="home-dafare">{t('home.todo_title', { defaultValue: 'Da fare' })}</span>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            {overdueCount > 0 && (
              <li>
                <Link to="/incassi" className={`${todoRow} border-[#C97B5D]/50 bg-[#C97B5D]/10 text-[#8a4a33] hover:bg-[#C97B5D]/20`}>
                  <span>{t('home.todo_overdue', { defaultValue: 'Pagamenti in ritardo' })}</span>
                  <span className="font-bold tabular-nums">{overdueCount}</span>
                </Link>
              </li>
            )}
            {todo > 0 && (
              <li>
                <Link to="/orders?triage=review" className={`${todoRow} border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100`}>
                  <span>{t('home.todo_review', { defaultValue: 'Ordini da gestire' })}</span>
                  <span className="font-bold tabular-nums">{todo}</span>
                </Link>
              </li>
            )}
            {reviewsPending > 0 && (
              <li>
                <Link to="/reviews" className={`${todoRow} border-border bg-muted/40 hover:bg-muted`}>
                  <span>{t('home.todo_reviews', { defaultValue: 'Recensioni in attesa' })}</span>
                  <span className="font-bold tabular-nums">{reviewsPending}</span>
                </Link>
              </li>
            )}
            {drafts > 0 && (
              <li>
                <Link to="/orders?status=draft" className={`${todoRow} border-border bg-muted/40 hover:bg-muted`}>
                  <span>{t('home.todo_drafts', { defaultValue: 'Bozze aperte' })}</span>
                  <span className="font-bold tabular-nums">{drafts}</span>
                </Link>
              </li>
            )}
          </ul>
        </div>
      )}
    </section>

    {/* ── 3. Agenda e andamento ── */}
    <div className="grid gap-4 lg:grid-cols-5">
      {/* Prossimi ritiri — i posti come barra: si legge senza fare i conti */}
      <div className={`${cardCls} lg:col-span-2`} data-testid="home-ritiri">
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
          <ul className="space-y-3 flex-1">
            {retreats.map((r) => {
              const cap = r.capacity > 0 ? r.capacity : 0;
              const res = r.reserved_seats ?? 0;
              const pct = cap ? Math.min(100, Math.round((res / cap) * 100)) : 0;
              return (
                <li key={r.id}>
                  <Link to={`/events/${r.id}`} className="group block">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                        {r.product_name}
                      </p>
                      {cap > 0 && (
                        <span className="shrink-0 inline-flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
                          <Users className="h-3 w-3" aria-hidden />
                          {res}/{cap} {t('home.seats', { defaultValue: 'posti' })}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{fmtDate(r.start_at, i18n.language)}</p>
                    {cap > 0 && (
                      <div className="mt-1.5 h-1.5 w-full rounded-full bg-muted overflow-hidden" aria-hidden>
                        <div className="h-full rounded-full bg-[#376254]" style={{ width: `${pct}%` }} />
                      </div>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
        <Link to="/events" className={footLink}>
          {t('home.upcoming_all', { defaultValue: 'Tutti i ritiri' })} <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Andamento incassi (fonte: /analytics/cashflow, come la pagina) */}
      <div className={`${cardCls} lg:col-span-3`} data-testid="home-andamento">
        <div className={headCls}>
          <Wallet className="h-3.5 w-3.5" />
          {t('home.trend_title', { defaultValue: 'Andamento incassi, mese per mese' })}
        </div>
        {cashflow === null ? (
          <div className="h-24 animate-pulse rounded-lg bg-muted" />
        ) : bars.some((b) => b.value > 0) ? (
          <div className="flex-1 flex flex-col justify-end">
            <MiniBars data={bars} height={72} valueFormatter={fmt} />
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <span>
                <span className="font-semibold tabular-nums">{fmt(s?.incassato)}</span>{' '}
                <span className="text-muted-foreground">{t('home.payments_collected12m', { defaultValue: 'incassati (12 mesi)' })}</span>
              </span>
              {(s?.ticket_medio || 0) > 0 && (
                <span>
                  <span className="font-semibold tabular-nums">{fmt(s.ticket_medio)}</span>{' '}
                  <span className="text-muted-foreground">{t('home.avg_ticket', { defaultValue: 'per ordine, in media' })}</span>
                </span>
              )}
            </div>
          </div>
        ) : (
          <p className="flex-1 text-sm text-muted-foreground flex items-center">
            {t('home.trend_empty', { defaultValue: 'Il grafico si riempie con il primo incasso.' })}
          </p>
        )}
        <Link to="/incassi" className={footLink}>
          {t('home.payments_all_cf', { defaultValue: 'Vai a Incassi' })} <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
    </div>
  );
}
