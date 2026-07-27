/**
 * NewsletterPreferencesPage — /newsletter/preferenze/:token (BN2).
 *
 * Il centro preferenze dell'iscritto, senza login (token firmato
 * dall'email): temi (categorie del Magazine), formato (tutto / solo
 * pratiche), alert ritiri per zona (DORMIENTE in fase rete: il copy
 * lo dice onestamente), e l'unsubscribe a un click (GDPR Art. 7(3)).
 */
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Check, Loader2 } from 'lucide-react';
import api from '../../api/client';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import useItalianOnly from '../../lib/useItalianOnly';

const GREEN = '#376254';

const REGION_LABELS = {
  'abruzzo': 'Abruzzo', 'basilicata': 'Basilicata', 'calabria': 'Calabria',
  'campania': 'Campania', 'emilia-romagna': 'Emilia-Romagna',
  'friuli-venezia-giulia': 'Friuli-Venezia Giulia', 'lazio': 'Lazio',
  'liguria': 'Liguria', 'lombardia': 'Lombardia', 'marche': 'Marche',
  'molise': 'Molise', 'piemonte': 'Piemonte', 'puglia': 'Puglia',
  'sardegna': 'Sardegna', 'sicilia': 'Sicilia', 'toscana': 'Toscana',
  'trentino-alto-adige': 'Trentino-Alto Adige', 'umbria': 'Umbria',
  'valle-d-aosta': 'Valle d’Aosta', 'veneto': 'Veneto',
};

export default function NewsletterPreferencesPage() {
  useItalianOnly();
  const { token } = useParams();
  const { t } = useTranslation('prelaunch');
  const { t: tl } = useTranslation('landings');

  const [state, setState] = useState('loading'); // loading | ready | saving | saved | error | gone
  const [data, setData] = useState(null);
  const [topics, setTopics] = useState([]);
  const [format, setFormat] = useState('all');
  const [alert, setAlert] = useState({ enabled: false, scope: 'italy', regions: [] });

  useSeoMeta({
    title: t('nlPrefs.seoTitle', { defaultValue: 'Le tue preferenze | Aurya' }),
    noindex: true,
  });

  useEffect(() => {
    let mounted = true;
    api.get(`/public/newsletter/preferences/${token}`)
      .then(res => {
        if (!mounted) return;
        try { localStorage.setItem('aurya_nl_token', token); } catch { /* private mode */ }
        setData(res.data);
        setTopics(res.data.topics || []);
        setFormat(res.data.format || 'all');
        setAlert(res.data.retreat_alert || { enabled: false, scope: 'italy', regions: [] });
        setState('ready');
      })
      .catch(() => { if (mounted) setState('gone'); });
    return () => { mounted = false; };
  }, [token]);

  const toggleTopic = (slug) => setTopics(prev =>
    prev.includes(slug) ? prev.filter(x => x !== slug) : [...prev, slug]);
  const toggleRegion = (slug) => setAlert(prev => ({
    ...prev,
    regions: prev.regions.includes(slug)
      ? prev.regions.filter(x => x !== slug) : [...prev.regions, slug],
  }));

  const save = async () => {
    setState('saving');
    try {
      await api.put('/public/newsletter/preferences',
        { token, topics, format, retreat_alert: alert });
      setState('saved');
      setTimeout(() => setState('ready'), 2500);
    } catch { setState('error'); }
  };

  const unsubscribe = async () => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(t('nlPrefs.unsubConfirm', { defaultValue: 'Vuoi davvero disiscriverti dalla lettera di Aurya?' }))) return;
    try {
      await api.post('/public/newsletter/unsubscribe', { token });
      setData(d => ({ ...d, status: 'unsubscribed' }));
    } catch { setState('error'); }
  };

  const chip = (on) => `rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
    on ? 'bg-[#376254] border-[#376254] text-white'
       : 'border-gray-300 bg-white text-gray-600 hover:border-[#376254]/50'}`;

  if (state === 'loading') {
    return <div className="flex min-h-screen items-center justify-center bg-[#f7f9f6]">
      <Loader2 className="h-8 w-8 animate-spin text-[#376254]" aria-label="…" /></div>;
  }
  if (state === 'gone') {
    return (
      <div className="min-h-screen bg-[#f7f9f6] px-5 pt-24 text-center">
        <h1 className="font-brand text-2xl text-gray-900">
          {t('nlConfirm.invalid', { defaultValue: 'Questo link non è valido' })}
        </h1>
        <Link to="/newsletter" className="mt-4 inline-block text-sm text-[#376254] underline">
          {t('nlConfirm.toNewsletter', { defaultValue: 'Vai alla newsletter' })}
        </Link>
      </div>
    );
  }

  const unsubscribed = data?.status === 'unsubscribed';
  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
      </header>
      <main className="mx-auto max-w-xl px-5 pb-20 pt-8" data-testid="nl-prefs">
        <h1 className="font-brand text-2xl text-gray-900">
          {t('nlPrefs.title', { defaultValue: 'Le tue preferenze' })}
        </h1>
        <p className="mt-1 text-sm text-gray-500">{data?.email_masked}</p>

        {unsubscribed ? (
          <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-6 text-center">
            <p className="text-sm text-gray-700">
              {t('nlPrefs.unsubDone', { defaultValue: 'Sei disiscritto. Niente più lettere da noi, promesso. Se cambi idea, la porta resta aperta.' })}
            </p>
            <Link to="/newsletter" className="mt-3 inline-block text-sm text-[#376254] underline">
              {t('nlConfirm.toNewsletter', { defaultValue: 'Vai alla newsletter' })}
            </Link>
          </div>
        ) : (<>
          <section className="mt-8 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="font-heading text-sm font-semibold text-gray-900">
              {t('nlPrefs.topics', { defaultValue: 'I temi che ti interessano' })}
            </h2>
            <p className="mt-0.5 text-xs text-gray-500">
              {t('nlPrefs.topicsHint', { defaultValue: 'Nessuna scelta = ricevi tutto.' })}
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(data?.available_topics || []).map(slug => (
                <button key={slug} type="button" onClick={() => toggleTopic(slug)}
                        aria-pressed={topics.includes(slug)} className={chip(topics.includes(slug))}>
                  {tl(`categories.${slug}`, { defaultValue: slug })}
                </button>
              ))}
            </div>
          </section>

          <section className="mt-4 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="font-heading text-sm font-semibold text-gray-900">
              {t('nlPrefs.format', { defaultValue: 'Cosa vuoi ricevere' })}
            </h2>
            <div className="mt-3 space-y-2 text-sm text-gray-700">
              <label className="flex items-center gap-2">
                <input type="radio" name="format" checked={format === 'all'}
                       onChange={() => setFormat('all')} />
                {t('nlPrefs.formatAll', { defaultValue: 'Tutta la lettera (pratiche, storie, novità)' })}
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" name="format" checked={format === 'practices'}
                       onChange={() => setFormat('practices')} />
                {t('nlPrefs.formatPractices', { defaultValue: 'Solo pratiche ed esercizi' })}
              </label>
            </div>
          </section>

          <section className="mt-4 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="font-heading text-sm font-semibold text-gray-900">
              {t('nlPrefs.alert', { defaultValue: 'Avvisami sui ritiri' })}
            </h2>
            <p className="mt-0.5 text-xs text-gray-500">
              {t('nlPrefs.alertHint', { defaultValue: 'Le prenotazioni su Aurya non sono ancora aperte: raccogliamo la tua preferenza ora e ti avviseremo solo quando ci saranno ritiri veri da mostrarti.' })}
            </p>
            <label className="mt-3 flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={alert.enabled}
                     onChange={(e) => setAlert(a => ({ ...a, enabled: e.target.checked }))} />
              {t('nlPrefs.alertOn', { defaultValue: 'Sì, avvisami' })}
            </label>
            {alert.enabled && (
              <div className="mt-3">
                <div className="flex gap-4 text-sm text-gray-700">
                  <label className="flex items-center gap-2">
                    <input type="radio" name="scope" checked={alert.scope === 'italy'}
                           onChange={() => setAlert(a => ({ ...a, scope: 'italy' }))} />
                    {t('nlPrefs.scopeItaly', { defaultValue: 'Tutta Italia' })}
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="radio" name="scope" checked={alert.scope === 'regions'}
                           onChange={() => setAlert(a => ({ ...a, scope: 'regions' }))} />
                    {t('nlPrefs.scopeRegions', { defaultValue: 'Solo alcune regioni' })}
                  </label>
                </div>
                {alert.scope === 'regions' && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(data?.available_regions || []).map(slug => (
                      <button key={slug} type="button" onClick={() => toggleRegion(slug)}
                              aria-pressed={alert.regions.includes(slug)}
                              className={chip(alert.regions.includes(slug))}>
                        {REGION_LABELS[slug] || slug}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>

          <div className="mt-6 flex items-center gap-3">
            <button type="button" onClick={save} disabled={state === 'saving'}
                    className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white disabled:opacity-50"
                    style={{ backgroundColor: GREEN }}>
              {state === 'saving' ? <Loader2 className="h-4 w-4 animate-spin" />
                : state === 'saved' ? <><Check className="h-4 w-4" />{t('nlPrefs.saved', { defaultValue: 'Salvato' })}</>
                : t('nlPrefs.save', { defaultValue: 'Salva le preferenze' })}
            </button>
            {state === 'error' && (
              <span className="text-xs text-red-600">
                {t('nlPrefs.error', { defaultValue: 'Qualcosa è andato storto, riprova.' })}
              </span>
            )}
          </div>

          <button type="button" onClick={unsubscribe}
                  className="mt-8 text-xs text-gray-400 underline hover:text-gray-600">
            {t('nlPrefs.unsub', { defaultValue: 'Disiscrivimi dalla lettera' })}
          </button>
        </>)}
      </main>
    </div>
  );
}
