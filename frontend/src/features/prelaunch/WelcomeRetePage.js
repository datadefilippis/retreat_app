/**
 * WelcomeRetePage — /benvenuto (ciclo RD, 19/8/2026).
 *
 * Il secondo tempo della registrazione diretta: l'account e' gia'
 * nato (signup INTATTO, 4 campi), qui si raccolgono le informazioni
 * che prima vivevano nel form di candidatura — citta', telefono,
 * Instagram, di cosa ti occupi — e si salvano DOVE SERVONO: nel
 * profilo pubblico, sugli stessi campi che alimentano directory,
 * mappa e discipline. Zero modelli nuovi, zero rischio sul flusso
 * auth: un solo PATCH sull'endpoint del profilo che esiste da F2.0.
 *
 * Tutto facoltativo e saltabile: e' un benvenuto, non un cancello.
 * Da qui si prosegue su /inizia, che resta l'onboarding vero.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import { BrandLogo } from '../../components/BrandLogo';
import { DISCIPLINE_FAMILIES, DISCIPLINES_MAX } from '../../lib/disciplines';

export default function WelcomeRetePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation('landings');
  // ID-nonies — la destinazione che l'accesso portava con se': la
  // tappa del benvenuto la conserva e la riconsegna. Solo percorsi
  // interni (mai '//': stessa regola di ogni next della porta).
  const rawNext = searchParams.get('next') || '';
  const dest = rawNext.startsWith('/') && !rawNext.startsWith('//')
    ? rawNext : '/dashboard';
  const [city, setCity] = useState('');
  const [phone, setPhone] = useState('');
  const [instagram, setInstagram] = useState('');
  const [disciplines, setDisciplines] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Solidita': se qualcuno con un profilo gia' vivo capita qui (link
  // vecchio, refresh), i suoi dati si PRECARICANO — cosi' salvare non
  // puo' mai cancellare cio' che c'era. Best-effort: se la GET fallisce
  // si parte vuoti, e i campi vuoti non vengono comunque inviati.
  useEffect(() => {
    let alive = true;
    // gia' fatto (o saltato) in passato? si tira dritto al lavoro
    api.get('/organizations/current/onboarding-status').then((r) => {
      if (alive && r.data?.welcome_seen) navigate(dest, { replace: true });
    }).catch(() => { /* nel dubbio si mostra: e' saltabile */ });
    api.get('/organizations/current/public-profile').then((r) => {
      if (!alive) return;
      const pp = r.data || {};
      if (pp.city) setCity(pp.city);
      if (pp.public_phone) setPhone(pp.public_phone);
      if (pp.instagram) setInstagram(pp.instagram);
      if (Array.isArray(pp.disciplines) && pp.disciplines.length) {
        setDisciplines(pp.disciplines);
      }
    }).catch(() => { /* profilo nuovo: si parte vuoti */ });
    return () => { alive = false; };
  }, []);

  const toggle = (slug) => setDisciplines((cur) => (
    cur.includes(slug) ? cur.filter((s) => s !== slug)
      : cur.length >= DISCIPLINES_MAX ? cur : [...cur, slug]
  ));

  // ID-octies (20/8, founder) — compilato o saltato, si atterra sulla
  // DASHBOARD: li' vive l'accompagnamento a passi (il banner che porta
  // a /inizia). E si timbra il passaggio, cosi' il benvenuto non
  // ricompare a ogni accesso.
  const next = async () => {
    try { await api.post('/organizations/current/welcome-seen'); }
    catch { /* il timbro non deve mai bloccare il percorso */ }
    navigate(dest, { replace: true });
  };

  const save = async (e) => {
    e.preventDefault();
    // niente da salvare = e' un salto, non un errore
    if (!city.trim() && !phone.trim() && !instagram.trim() && !disciplines.length) {
      next();
      return;
    }
    setSaving(true);
    setError('');
    try {
      const payload = {};
      if (city.trim()) payload.city = city.trim();
      if (phone.trim()) payload.public_phone = phone.trim();
      if (instagram.trim()) payload.instagram = instagram.trim().replace(/^@/, '');
      if (disciplines.length) payload.disciplines = disciplines;
      await api.patch('/organizations/current/public-profile', payload);
      next();
    } catch {
      setError(t('welcomeRete.error', { defaultValue: 'Non siamo riusciti a salvare. Puoi riprovare, o farlo più tardi dal tuo profilo.' }));
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf7f0] flex items-start justify-center px-4 py-12">
      <div className="w-full max-w-xl" data-testid="welcome-rete">
        <div className="flex justify-center mb-8"><BrandLogo size="sm" /></div>
        <h1 className="font-display text-3xl text-center text-[#2e4b3f] mb-3">
          {t('welcomeRete.title', { defaultValue: 'Benvenuto nella rete.' })}
        </h1>
        <p className="text-center text-gray-600 mb-10 leading-relaxed">
          {t('welcomeRete.lead', { defaultValue: 'Raccontaci due cose su di te: ci aiutano a conoscerti e a preparare la conversazione con cui costruiremo il racconto del tuo lavoro. Puoi anche saltare e farlo più tardi.' })}
        </p>

        <form onSubmit={save} className="space-y-6 bg-white rounded-2xl border border-gray-200 p-7 shadow-sm">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('welcomeRete.disciplines', { defaultValue: 'Di cosa ti occupi?' })}
            </label>
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1" data-testid="welcome-disciplines">
              {DISCIPLINE_FAMILIES.map((fam) => (
                <div key={fam.slug}>
                  <div className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">{fam.label}</div>
                  <div className="flex flex-wrap gap-1.5">
                    {fam.items.map((d) => (
                      <button key={d.slug} type="button" onClick={() => toggle(d.slug)}
                        className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                          disciplines.includes(d.slug)
                            ? 'bg-[#376254] text-white border-[#376254]'
                            : 'bg-white text-gray-600 border-gray-300 hover:border-[#376254]'}`}>
                        {d.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                {t('welcomeRete.city', { defaultValue: 'La tua città' })}
              </label>
              <input type="text" value={city} onChange={(e) => setCity(e.target.value)}
                maxLength={80} placeholder="Es. Ostuni"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#376254] focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                {t('welcomeRete.phone', { defaultValue: 'Telefono' })}
              </label>
              <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                maxLength={40} placeholder="Facoltativo"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#376254] focus:outline-none" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">
              {t('welcomeRete.instagram', { defaultValue: 'Instagram' })}
            </label>
            <input type="text" value={instagram} onChange={(e) => setInstagram(e.target.value)}
              maxLength={120} placeholder="@iltuoprofilo"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#376254] focus:outline-none" />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex items-center justify-between gap-4 pt-1">
            <button type="button" onClick={next} data-testid="welcome-skip"
              className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2">
              {t('welcomeRete.skip', { defaultValue: 'Lo faccio più tardi' })}
            </button>
            <button type="submit" disabled={saving} data-testid="welcome-save"
              className="rounded-lg bg-[#376254] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#2e5346] disabled:opacity-50">
              {saving
                ? t('welcomeRete.saving', { defaultValue: 'Salvo…' })
                : t('welcomeRete.continue', { defaultValue: 'Continua' })}
            </button>
          </div>
        </form>

        <p className="text-center text-xs text-gray-400 mt-6 leading-relaxed max-w-md mx-auto">
          {t('welcomeRete.note', { defaultValue: 'Queste informazioni vanno nel tuo profilo pubblico e puoi cambiarle quando vuoi. Nei prossimi giorni ti scriveremo per conoscerci: il racconto del tuo lavoro lo costruiamo insieme.' })}
        </p>
      </div>
    </div>
  );
}
