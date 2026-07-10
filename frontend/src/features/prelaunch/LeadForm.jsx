/**
 * LeadForm — cattura lead pre-lancio (PL5). Condiviso da splash e landing.
 *
 * type: "operator" | "traveler". POST /public/leads (dedup lato server,
 * notifica a info@). GDPR: consenso esplicito obbligatorio. Stato di
 * successo gentile; best-effort (un errore non blocca mai l'utente).
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Check, Loader2 } from 'lucide-react';
import api from '../../api/client';

export default function LeadForm({ type = 'traveler', accent = '#376254' }) {
  const { t, i18n } = useTranslation('prelaunch');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState('idle');   // idle | sending | done

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !consent || state === 'sending') return;
    setState('sending');
    try {
      await api.post('/public/leads', {
        email: email.trim(), name: name.trim() || null, type,
        consent: true, language: (i18n.language || 'it').slice(0, 2),
      });
    } catch { /* best-effort: mostriamo comunque il grazie */ }
    setState('done');
  };

  if (state === 'done') {
    return (
      <div className="rounded-2xl border p-6 text-center"
           style={{ borderColor: `${accent}55`, background: `${accent}0d` }}>
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full"
             style={{ background: accent }}>
          <Check className="h-6 w-6 text-white" />
        </div>
        <p className="font-heading text-lg font-semibold text-foreground">
          {t('form.thanksTitle', { defaultValue: 'Ci sei!' })}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {t('form.thanksBody', { defaultValue: 'Ti scriviamo appena Aurya apre. A presto.' })}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <input
        type="text" value={name} onChange={(e) => setName(e.target.value)}
        placeholder={t('form.name', { defaultValue: 'Il tuo nome (facoltativo)' })}
        className="w-full rounded-xl border border-input bg-white px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2"
        style={{ '--tw-ring-color': accent }}
      />
      <input
        type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
        placeholder={t('form.email', { defaultValue: 'La tua email' })}
        className="w-full rounded-xl border border-input bg-white px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2"
        style={{ '--tw-ring-color': accent }}
      />
      <label className="flex items-start gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked={consent}
               onChange={(e) => setConsent(e.target.checked)}
               className="mt-0.5 h-4 w-4 shrink-0" required />
        <span>
          {t('form.consent', { defaultValue: 'Acconsento a essere contattato via email sul lancio di Aurya.' })}{' '}
          <a href="/privacy" target="_blank" rel="noreferrer" className="underline">
            {t('form.privacy', { defaultValue: 'Privacy' })}
          </a>
        </span>
      </label>
      <button
        type="submit" disabled={!email || !consent || state === 'sending'}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        style={{ background: accent }}
      >
        {state === 'sending'
          ? <Loader2 className="h-4 w-4 animate-spin" />
          : <>{t('form.cta', { defaultValue: 'Avvisami al lancio' })} <ArrowRight className="h-4 w-4" /></>}
      </button>
    </form>
  );
}
