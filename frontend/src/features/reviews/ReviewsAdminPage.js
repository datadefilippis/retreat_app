/**
 * ReviewsAdminPage — /reviews nel back-office (PR3).
 *
 * La plancia recensioni dell'operatore: media + distribuzione, tab
 * Pubblicate / In attesa / Segnalate, risposta inline, moderazione dei
 * pending (solo quelli: le verificate non si governano — credibilità
 * marketplace), segnalazione abusi e il TOGGLE per accettare recensioni
 * anche da chi non ha ancora prenotato (reviews_open).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import api from '../../api/client';
import { AppLayout, Header } from '../../components/Layout';

function Stars({ value }) {
  const full = Math.round(value || 0);
  return (
    <span aria-label={`${value} su 5`}>
      <span className="text-amber-500">{'★'.repeat(full)}</span>
      <span className="text-gray-300">{'★'.repeat(5 - full)}</span>
    </span>
  );
}

function fmtDay(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return (iso || '').slice(0, 10); }
}

function ReviewCard({ r, onReply, onModerate, onFlag, t, i18n }) {
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyText, setReplyText] = useState(r.reply?.body || '');
  const [busy, setBusy] = useState(false);

  const sendReply = async () => {
    setBusy(true);
    try {
      await onReply(r.id, replyText);
      setReplyOpen(false);
    } finally { setBusy(false); }
  };

  return (
    <article className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold text-foreground">{r.author_name}</span>
        {r.verified ? (
          <span className="rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-medium">
            ✓ {t('reviews.verified', { defaultValue: 'Cliente verificato' })}
          </span>
        ) : (
          <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 text-[11px] font-medium">
            {t('reviews.unverified', { defaultValue: 'Non cliente' })}
          </span>
        )}
        {r.status === 'flagged' && (
          <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-[11px] font-medium">
            {t('reviews.flagged', { defaultValue: 'Segnalata' })}
          </span>
        )}
        <span className="ml-auto text-xs text-muted-foreground">{fmtDay(r.created_at, i18n.language)}</span>
      </div>
      <Stars value={r.rating} />
      {r.title && <p className="font-medium text-foreground mt-1">{r.title}</p>}
      <p className="text-sm text-gray-700 mt-1 whitespace-pre-line">{r.body}</p>

      {r.reply?.body && !replyOpen && (
        <div className="mt-3 rounded-lg bg-secondary/60 p-3 border-l-2 border-primary">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-primary mb-1">
            {t('reviews.yourReply', { defaultValue: 'La tua risposta' })}
          </p>
          <p className="text-sm text-gray-700 whitespace-pre-line">{r.reply.body}</p>
        </div>
      )}

      {replyOpen && (
        <div className="mt-3 space-y-2">
          <textarea rows={3} maxLength={1000} value={replyText}
                    onChange={e => setReplyText(e.target.value)}
                    placeholder={t('reviews.replyPlaceholder', { defaultValue: 'Ringrazia, chiarisci, invita a tornare — la risposta è pubblica.' })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="flex gap-2">
            <button type="button" disabled={busy || replyText.trim().length === 0} onClick={sendReply}
                    className="rounded-full bg-primary text-white px-4 py-1.5 text-xs font-semibold disabled:opacity-60">
              {t('reviews.sendReply', { defaultValue: 'Pubblica risposta' })}
            </button>
            <button type="button" onClick={() => setReplyOpen(false)}
                    className="rounded-full border border-border px-4 py-1.5 text-xs">
              {t('reviews.cancel', { defaultValue: 'Annulla' })}
            </button>
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {r.status === 'pending' && !r.verified && (
          <>
            <button type="button" onClick={() => onModerate(r.id, 'approve')}
                    className="rounded-full bg-primary text-white px-3 py-1 font-semibold">
              {t('reviews.approve', { defaultValue: 'Approva' })}
            </button>
            <button type="button" onClick={() => onModerate(r.id, 'reject')}
                    className="rounded-full border border-red-300 text-red-700 px-3 py-1 font-semibold">
              {t('reviews.reject', { defaultValue: 'Rifiuta' })}
            </button>
          </>
        )}
        {!replyOpen && r.status !== 'flagged' && (
          <button type="button" onClick={() => setReplyOpen(true)}
                  className="rounded-full border border-border px-3 py-1 font-medium hover:border-primary">
            {r.reply?.body
              ? t('reviews.editReply', { defaultValue: 'Modifica risposta' })
              : t('reviews.reply', { defaultValue: 'Rispondi' })}
          </button>
        )}
        {r.status === 'published' && (
          <button type="button" onClick={() => onFlag(r.id)}
                  className="rounded-full border border-border px-3 py-1 text-muted-foreground hover:border-red-300 hover:text-red-700">
            {t('reviews.flag', { defaultValue: 'Segnala abuso' })}
          </button>
        )}
      </div>
    </article>
  );
}

export default function ReviewsAdminPage() {
  const { t, i18n } = useTranslation('common');
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('published');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (status = tab) => {
    setLoading(true);
    try {
      const res = await api.get('/reviews', { params: { status } });
      setData(res.data);
    } catch {
      toast.error(t('reviews.loadError', { defaultValue: 'Errore nel caricamento' }));
    } finally { setLoading(false); }
  }, [tab, t]);

  useEffect(() => { load(tab); }, [tab, load]);

  const onReply = async (id, body) => {
    try {
      await api.post(`/reviews/${id}/reply`, { body });
      toast.success(t('reviews.replySent', { defaultValue: 'Risposta pubblicata' }));
      load();
    } catch { toast.error(t('reviews.genericError', { defaultValue: 'Errore, riprova' })); }
  };
  const onModerate = async (id, action) => {
    try {
      await api.patch(`/reviews/${id}/moderate`, { action });
      toast.success(action === 'approve'
        ? t('reviews.approved', { defaultValue: 'Recensione pubblicata' })
        : t('reviews.rejected', { defaultValue: 'Recensione rifiutata' }));
      load();
    } catch { toast.error(t('reviews.genericError', { defaultValue: 'Errore, riprova' })); }
  };
  const onFlag = async (id) => {
    try {
      await api.post(`/reviews/${id}/flag`);
      toast.success(t('reviews.flaggedOk', { defaultValue: 'Segnalata: nascosta in attesa di revisione' }));
      load();
    } catch { toast.error(t('reviews.genericError', { defaultValue: 'Errore, riprova' })); }
  };
  const toggleOpen = async () => {
    try {
      const res = await api.patch('/reviews/settings', { reviews_open: !data?.reviews_open });
      setData(d => ({ ...d, reviews_open: res.data.reviews_open }));
      toast.success(res.data.reviews_open
        ? t('reviews.openOn', { defaultValue: 'Ora chiunque può lasciare una recensione (con la tua approvazione)' })
        : t('reviews.openOff', { defaultValue: 'Solo i clienti possono recensire' }));
    } catch { toast.error(t('reviews.genericError', { defaultValue: 'Errore, riprova' })); }
  };

  const stats = data?.stats;
  const dist = stats?.distribution || {};
  const maxDist = Math.max(1, ...Object.values(dist));
  const items = data?.items || [];

  const TABS = [
    ['published', t('reviews.tabPublished', { defaultValue: 'Pubblicate' })],
    ['pending', t('reviews.tabPending', { defaultValue: 'In attesa' })],
    ['flagged', t('reviews.tabFlagged', { defaultValue: 'Segnalate' })],
  ];

  return (
    <AppLayout>
      <Header
        title={t('reviews.title', { defaultValue: 'Recensioni' })}
        subtitle={t('reviews.subtitle', { defaultValue: 'Cosa dicono di te i viaggiatori — e come rispondi.' })}
      />
      <div className="p-4 md:p-8 max-w-4xl">

      {/* Header: media + distribuzione + toggle */}
      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr_auto] gap-6 rounded-2xl border border-border bg-card p-5 mb-6 items-center">
        <div className="text-center">
          <p className="text-4xl font-bold text-foreground">{stats?.avg ?? '—'}</p>
          {stats?.avg != null && <Stars value={stats.avg} />}
          <p className="text-xs text-muted-foreground mt-1">
            {t('reviews.total', { count: stats?.count || 0, defaultValue: '{{count}} recensioni' })}
          </p>
        </div>
        <div className="space-y-1 max-w-xs">
          {[5, 4, 3, 2, 1].map(v => (
            <div key={v} className="flex items-center gap-2 text-xs">
              <span className="w-3 text-muted-foreground">{v}</span>
              <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                <div className="h-full bg-amber-400"
                     style={{ width: `${((dist[String(v)] || 0) / maxDist) * 100}%` }} />
              </div>
              <span className="w-6 text-right text-muted-foreground">{dist[String(v)] || 0}</span>
            </div>
          ))}
        </div>
        <label className="flex items-start gap-3 cursor-pointer max-w-[240px]">
          <input type="checkbox" checked={Boolean(data?.reviews_open)} onChange={toggleOpen}
                 className="mt-1 h-4 w-4 accent-[#376254]" />
          <span className="text-xs text-muted-foreground">
            <span className="block font-semibold text-foreground mb-0.5">
              {t('reviews.openToggle', { defaultValue: 'Accetta recensioni da chi non ha ancora prenotato' })}
            </span>
            {t('reviews.openToggleHint', { defaultValue: 'Appariranno solo dopo la tua approvazione e senza il badge "Cliente verificato".' })}
          </span>
        </label>
      </div>

      {/* Tab */}
      <div className="flex gap-2 mb-4">
        {TABS.map(([key, label]) => (
          <button key={key} type="button" onClick={() => setTab(key)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                    tab === key ? 'bg-primary text-white' : 'border border-border text-foreground hover:border-primary'}`}>
            {label}
            {key === 'pending' && data?.pending_count > 0 && (
              <span className="ml-1.5 rounded-full bg-amber-400 text-amber-950 px-1.5 text-[11px] font-bold">
                {data.pending_count}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2].map(i => <div key={i} className="h-28 rounded-xl border border-border bg-card animate-pulse" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-10 text-center">
          <p className="text-3xl mb-2" aria-hidden>★</p>
          <p className="font-semibold text-foreground">
            {t('reviews.emptyTitle', { defaultValue: 'Nessuna recensione qui' })}
          </p>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
            {t('reviews.emptyBody', { defaultValue: 'I clienti possono recensirti dalla tua pagina profilo. Condividila dopo ogni ritiro: è il modo più veloce per costruire fiducia.' })}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(r => (
            <ReviewCard key={r.id} r={r} onReply={onReply}
                        onModerate={onModerate} onFlag={onFlag} t={t} i18n={i18n} />
          ))}
        </div>
      )}
      </div>
    </AppLayout>
  );
}
