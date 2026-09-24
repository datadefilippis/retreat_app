/**
 * OperatorHome — il radar dell'operatore (D3 → CF4 → IG4).
 *
 * Auto-alimentata, zero configurazione: in 5 secondi si vede come va
 * il business e cosa fare adesso. CF4 assorbe qui i widget pinnabili
 * (rimossi): la home non si configura, si legge.
 *
 * IG4 (3/9/2026, ciclo VETRINA) — la lettura in un colpo solo, dall'alto:
 *   0. Avviso calendario bloccato (GT1b) — se c'è, viene prima di tutto.
 *   1. Panoramica — tre numeri del MESE con il loro significato:
 *      incassato · in arrivo · prenotazioni. Ogni tessera è un link
 *      alla pagina dove si approfondisce.
 *   4. Visite al profilo (in fondo, IG5 su richiesta del founder):
 *      quante persone aprono la pagina pubblica e quante TRAMITE
 *      Aurya (directory+ricerca), con gli ultimi 30 giorni. Evolve la
 *      card «Visibilità» VT5 (compariva solo con visite > 0; uno zero
 *      è una verità). Modulo commerce spento → niente sezione.
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
import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Calendar, Wallet, ListTodo, ArrowRight, Users, Eye, CalendarCheck, Clock } from 'lucide-react';
import api from '../../api/client';
import { MiniBars } from '../../components/charts';
import { formatCurrency } from '../../lib/utils';
import { useAuth, useCurrency } from '../../context/AuthContext';
import useDatiFreschi from '../../hooks/useDatiFreschi';

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
  const { user } = useAuth();
  // DF1 (16/9) — la regia (system_admin) non e' admin di un'organizzazione:
  // la lista recensioni le risponde 403 per ruolo. Non si chiede: niente
  // rumore nei log, nessun cambiamento per gli operatori.
  const chiediRecensioni = user?.role !== 'system_admin';
  // P3 — il recapito: una GET a parte, solo per chi e' admin della sua org
  const [telefonoMancante, setTelefonoMancante] = useState(false);
  const [telefono, setTelefono] = useState('');
  const [telefonoStato, setTelefonoStato] = useState('');
  useEffect(() => {
    if (!chiediRecensioni) return undefined;
    let vivo = true;
    api.get('/organizations/current/public-profile')
      .then((r) => { if (vivo) setTelefonoMancante(!(r.data || {}).public_phone); })
      .catch(() => { /* niente riga: mai un avviso su un dato che non si conosce */ });
    return () => { vivo = false; };
  }, [chiediRecensioni]);

  // DF1 — il caricamento e' una funzione riusabile: al montaggio come
  // prima, e di nuovo quando la scheda torna visibile dopo un'assenza
  // (useDatiFreschi), cosi' chi riapre il telefono vede i dati di adesso.
  const carica = useCallback((eVivo = () => true) => Promise.allSettled([
      api.get('/event-occurrences/admin/list', { params: { status: 'published', when: 'upcoming', limit: 4 } }),
      api.get('/orders/payments-overview'),
      api.get('/analytics/cashflow'),
      chiediRecensioni ? api.get('/reviews', { params: { status: 'pending' } }) : Promise.reject(new Error('regia')),
      api.get('/organizations/current/onboarding-status'),
      api.get('/analytics/visibility'),
    ]).then(([occRes, payRes, cfRes, revRes, obRes, visRes]) => {
      if (!eVivo()) return;
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
    }), [chiediRecensioni]);

  useEffect(() => {
    let mounted = true;
    carica(() => mounted);
    return () => { mounted = false; };
  }, [carica]);
  useDatiFreschi(carica);

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
  // IG5 (founder 3/9) — «quante visite ricevo TRAMITE Aurya»: il
  // backend distingue gia' i canali (directory+search = Aurya; social/
  // direct/store = da fuori). aurya_visits e' la sua somma.
  const daAurya = visAvailable ? (visibility?.aurya_visits || 0) : 0;
  const daFuori = Math.max(0, visitsCur - daAurya);
  const giorni30 = (visAvailable ? (visibility?.last_30d || []) : []).map((d) => ({
    label: String(d.day || '').slice(8, 10), value: d.visits || 0,
  }));

  const cardCls = 'rounded-2xl border bg-card p-4 flex flex-col';
  const headCls = 'flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3';
  const todoRow = 'flex items-center justify-between rounded-lg border px-3 py-2 transition-colors';
  const footLink = 'mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground';

  // SD6 (14/9/2026) — dal 10/9 i ritiri «su richiesta» SONO in lista senza
  // Stripe: il vecchio riquadro (GT1b: pubblicato && !Stripe) avvisava
  // anche loro. Ora scatta SOLO se c'e' un ritiro «prenotazione online»
  // senza Stripe pronto: l'unico che resta fuori (services/ritiri_visibilita).
  const calendarBlocked = obSteps && Number(obSteps.retreats_direct_no_stripe || 0) > 0;

  return (
    <div className="space-y-5" data-testid="operator-home">
    {/* P3 (24/9, founder) — chi si e' iscritto prima del telefono obbligatorio
        non ha un recapito: una riga finche' non lo mette, qui, senza
        cambiare pagina. Resta privato (show_contacts spento). */}
    {telefonoMancante && (
      <form className="rounded-2xl border border-[#376254]/30 bg-[#376254]/5 p-4 flex flex-wrap items-center gap-3"
        data-testid="home-telefono"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!telefono.trim()) return;
          setTelefonoStato('salvo');
          try {
            await api.patch('/organizations/current/public-profile', { public_phone: telefono.trim() });
            setTelefonoMancante(false);
          } catch { setTelefonoStato('errore'); }
        }}>
        <div className="text-sm flex-1 min-w-[220px]">
          <p className="font-semibold text-[#2e4b3f]">
            {t('home.telefono_titolo', { defaultValue: 'Aurya non ha un tuo recapito' })}
          </p>
          <p className="text-[#2e4b3f]/80 mt-0.5">
            {t('home.telefono_corpo', { defaultValue: 'Un telefono per raggiungerti se serve. Resta privato: non compare sulla tua pagina finché non lo decidi tu.' })}
          </p>
          {telefonoStato === 'errore' && <p className="text-xs text-red-700 mt-1">Non sembra un numero valido: da 8 a 15 cifre.</p>}
        </div>
        <input type="tel" value={telefono} onChange={(e) => setTelefono(e.target.value)} inputMode="tel"
          placeholder="+39 …" className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-44" />
        <button type="submit" className="rounded-lg bg-[#376254] text-white text-sm font-semibold px-4 py-2 disabled:opacity-60"
          disabled={telefonoStato === 'salvo'}>
          {t('home.telefono_salva', { defaultValue: 'Salva' })}
        </button>
      </form>
    )}
    {calendarBlocked && (
      <div className="rounded-2xl border border-[#C97B5D]/50 bg-[#C97B5D]/10 p-4 flex items-start gap-3">
        <span aria-hidden>⚠️</span>
        <div className="text-sm">
          <p className="font-semibold text-[#8a4a33]">
            {t('home.calendar_blocked_title', { defaultValue: 'Un tuo ritiro con prenotazione online non compare' })}
          </p>
          <p className="text-[#8a4a33]/90 mt-0.5">
            {t('home.calendar_blocked_body', { defaultValue: 'Finché Stripe non è attivo il pagamento sul sito non parte, quindi il ritiro resta fuori da Ritiri ed esperienze. Collega i pagamenti, oppure mettilo «su richiesta»: comparirà subito e la richiesta ti arriverà via email.' })}
          </p>
          <span className="inline-flex flex-wrap gap-x-4 mt-1.5">
            <Link to="/settings" className="text-sm font-semibold text-[#376254] hover:underline">
              {t('home.calendar_blocked_cta', { defaultValue: 'Collega i pagamenti' })} →
            </Link>
            <Link to="/events" className="text-sm font-semibold text-[#376254] hover:underline">
              {t('home.calendar_blocked_cta2', { defaultValue: 'Mettilo su richiesta' })} →
            </Link>
          </span>
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
      <div className={`grid gap-3 grid-cols-2 ${visAvailable ? 'lg:grid-cols-3' : 'lg:grid-cols-2'}`} data-testid="home-panoramica">
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
                <Link to="/reviews?status=pending" className={`${todoRow} border-border bg-muted/40 hover:bg-muted`}>
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

    {/* ── 4. Visite al profilo (IG5, founder): quante persone aprono la
        pagina pubblica e QUANTE arrivano tramite Aurya. In basso, una
        riga sola: numero del mese con confronto, la quota Aurya, gli
        ultimi 30 giorni. Modulo spento → la sezione non c'e'. ── */}
    {visAvailable && (
      <section className={cardCls} data-testid="home-visite" aria-labelledby="home-visite-titolo">
        <div className={headCls}>
          <Eye className="h-3.5 w-3.5" />
          <span id="home-visite-titolo">{t('home.visits_title', { defaultValue: 'Visite al profilo, questo mese' })}</span>
        </div>
        {visibility === null ? (
          <div className="h-16 animate-pulse rounded-lg bg-muted" />
        ) : (
          <div className="grid gap-4 md:grid-cols-[auto_1fr] md:items-end">
            <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
              <div>
                <p className="text-3xl font-bold tracking-tight tabular-nums leading-none">{visitsCur}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {(visitsCur || visitsPrev)
                    ? <Delta cur={visitsCur} prev={visitsPrev} t={t} />
                    : t('home.tile_visits_sub', { defaultValue: 'chi apre la tua pagina pubblica' })}
                </p>
              </div>
              <dl className="flex gap-5 text-sm">
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {t('home.visits_from_aurya', { defaultValue: 'tramite Aurya' })}
                  </dt>
                  <dd className="font-semibold tabular-nums text-[#376254]">{daAurya}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {t('home.visits_from_outside', { defaultValue: 'da link tuoi e social' })}
                  </dt>
                  <dd className="font-semibold tabular-nums">{daFuori}</dd>
                </div>
              </dl>
            </div>
            {giorni30.some((g) => g.value > 0) && (
              <div className="min-w-0">
                <MiniBars data={giorni30} height={40} valueFormatter={(v) => `${v}`} />
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {t('home.visits_30d', { defaultValue: 'ultimi 30 giorni' })}
                </p>
              </div>
            )}
          </div>
        )}
        <Link to="/visibilita" className={footLink}>
          {t('home.visibility_all', { defaultValue: 'Vai a Visibilità' })} <ArrowRight className="h-3 w-3" />
        </Link>
      </section>
    )}
    </div>
  );
}
