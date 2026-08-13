/**
 * OnboardingStrip — AC1 (13/8/2026, ciclo Accompagnamento).
 *
 * Il problema: l'operatore poco digitale clicca "Crea la tua pagina"
 * da /inizia, salva il profilo… e resta parcheggiato. La guida vive
 * solo su /inizia e nessuno gli dice di tornarci.
 *
 * La risposta: finché la configurazione non è completa, Profilo
 * pubblico e Listino portano in testa questa striscia. Dice a che
 * punto sei e qual è il prossimo passo, con UN solo bottone. Stato
 * SEMPRE derivato da onboarding-status (come /inizia): si aggiorna da
 * sola dopo ogni salvataggio tramite refreshKey. A configurazione
 * completa sparisce: zero rumore per chi è già online.
 *
 * Solo mondo snello: se il backend non manda il gradino 'online'
 * (org legacy_commerce) la striscia non compare.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Check, ArrowRight, Sparkles, ListChecks } from 'lucide-react';
import api from '../../api/client';

export default function OnboardingStrip({ step, refreshKey = 0, className = '' }) {
  const { t } = useTranslation('dashboard');
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.get('/organizations/current/onboarding-status')
      .then(res => { if (mounted) setStatus(res.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, [refreshKey]);

  if (!status || status.is_complete) return null;
  const s = status.steps || {};
  if (!('online' in s)) return null; // solo mondo snello

  // CS4 — cosa manca per spuntare Presentati (stessi check dell'editor)
  const missing = status.steps_detail?.profile?.missing || [];
  const profileHint = missing.includes('bio')
    ? t('onboarding.hint_bio', { defaultValue: 'racconta chi sei nella bio' })
    : t('onboarding.hint_cover_social', { defaultValue: 'aggiungi una foto di copertina o un link social (basta uno dei due)' });

  let done = false; let Icon = Sparkles; let title; let hint; let cta = null;
  if (step === 'profile') {
    if (!s.profile_completed) {
      title = t('onboarding.strip_profile_title', { defaultValue: 'Passo 1 di 3 — Presentati' });
      hint = t('onboarding.strip_profile_hint', {
        hint: profileHint,
        defaultValue: 'Per completare questo passo: {{hint}}',
      });
    } else {
      done = true; Icon = ListChecks;
      title = t('onboarding.strip_profile_done', { defaultValue: 'Presentati: fatto ✓' });
      hint = t('onboarding.strip_next_listino_hint', { defaultValue: 'Prossimo passo: i tuoi servizi con prezzo e durata.' });
      cta = { to: '/listino', label: t('onboarding.strip_next_listino_cta', { defaultValue: 'Vai al listino' }) };
    }
  } else if (step === 'listino') {
    if (!s.listino_filled) {
      Icon = ListChecks;
      title = t('onboarding.strip_listino_title', { defaultValue: 'Passo 2 di 3 — Il tuo listino' });
      hint = t('onboarding.strip_listino_hint', { defaultValue: 'Aggiungi un servizio con nome e prezzo: appare subito sulla tua pagina.' });
    } else if (!s.profile_completed) {
      done = true;
      title = t('onboarding.strip_listino_done', { defaultValue: 'Listino: fatto ✓' });
      hint = t('onboarding.strip_back_profile_hint', {
        hint: profileHint,
        defaultValue: 'Ti manca Presentati: {{hint}}',
      });
      cta = { to: '/public-profile', label: t('onboarding.strip_back_profile_cta', { defaultValue: 'Completa il profilo' }) };
    } else {
      // entrambi fatti ma non ancora online (caso raro: manca la
      // superficie pubblica) — la bussola resta /inizia
      done = true;
      title = t('onboarding.strip_almost_title', { defaultValue: 'Quasi fatto' });
      hint = t('onboarding.strip_almost_hint', { defaultValue: 'Un ultimo controllo e sei online.' });
      cta = { to: '/inizia', label: t('onboarding.strip_almost_cta', { defaultValue: 'Vedi cosa manca' }) };
    }
  } else {
    return null;
  }

  return (
    <div data-testid="onboarding-strip"
         className={`flex flex-wrap items-center gap-3 rounded-2xl border px-4 py-3 ${
           done ? 'border-primary/40 bg-primary/10' : 'border-primary/30 bg-primary/5'
         } ${className}`}>
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
        done ? 'bg-primary text-primary-foreground' : 'bg-primary/15 text-primary'
      }`}>
        {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      {cta && (
        <Link to={cta.to} data-testid="strip-next-cta"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-primary px-4 py-1.5 text-sm font-semibold text-primary-foreground">
          {cta.label} <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}
