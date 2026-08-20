/**
 * NewsletterConfirmPage — /newsletter/conferma/:token (BN2).
 *
 * La landing del click nell'email di double opt-in: conferma
 * l'iscrizione (POST confirm, idempotente), consegna il lead magnet
 * se configurato (la promessa era "dopo la conferma") e offre la
 * porta alle preferenze. Pagina noindex (token), servita 200 dalla
 * shell.
 */
import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Check, Download, Loader2, SlidersHorizontal } from 'lucide-react';
import api from '../../api/client';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import useItalianOnly from '../../lib/useItalianOnly';
import { useSiteConfig } from '../../context/SiteConfigContext';
import { trackEvent } from '../../lib/analytics';
import { salvaProva, emailDellaProva } from '../../lib/cerchio';
import { creaAccount } from '../../utils/authLinks';

const GOLD = '#8a7440';

export default function NewsletterConfirmPage() {
  useItalianOnly();
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation('prelaunch');
  const { leadMagnetUrl } = useSiteConfig();
  const [state, setState] = useState('working'); // working | done | expired | invalid
  // BN3→SB3 — next: il cancello da cui e' partita l'iscrizione (path
  // interni noti: il backend valida, qui doppio filtro). Prima solo il
  // blog: chi partiva dalle meditazioni riceveva un link che non
  // tornava li'.
  const rawNext = searchParams.get('next') || '';
  const nextOk = ['/blog/', '/meditazioni', '/frequenze/']
    .some((r) => rawNext === r.replace(/\/$/, '') || rawNext.startsWith(r));
  const next = nextOk && !rawNext.includes('//') ? rawNext : null;
  const nextLabel = rawNext.startsWith('/blog/')
    ? t('nlConfirm.backToGuide', { defaultValue: 'Torna alla guida sbloccata' })
    : rawNext.startsWith('/frequenze/')
      ? t('nlConfirm.backToTrack', { defaultValue: 'Torna alla sessione sbloccata' })
      : t('nlConfirm.backToMeditations', { defaultValue: 'Torna alle meditazioni sbloccate' });

  useSeoMeta({
    title: t('nlConfirm.seoTitle', { defaultValue: 'Conferma iscrizione | Aurya' }),
    noindex: true,
  });

  useEffect(() => {
    let mounted = true;
    api.post('/public/newsletter/confirm', { token })
      .then(() => {
        if (!mounted) return;
        setState('done');
        // BN3 — il token resta nel browser: sblocca le guide riservate
        // a ogni visita futura, senza dover ripassare dall'email
        salvaProva(token);   // SB1: la prova unica apre guide E meditazioni
        trackEvent('generate_lead', { lead_type: 'subscriber', lead_context: 'confirm' });
      })
      .catch((err) => {
        if (!mounted) return;
        setState(err?.response?.status === 410 ? 'expired' : 'invalid');
      });
    return () => { mounted = false; };
  }, [token]);

  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
      </header>
      <main className="mx-auto max-w-xl px-5 pb-20 pt-16 text-center">
        {state === 'working' && (
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-[#8a7440]" aria-label="…" />
        )}

        {state === 'done' && (
          <div data-testid="nl-confirm-done">
            <span className="inline-flex h-14 w-14 items-center justify-center rounded-full"
                  style={{ backgroundColor: GOLD }}>
              <Check className="h-7 w-7 text-white" />
            </span>
            <h1 className="mt-5 font-brand text-3xl text-gray-900">
              {t('nlConfirm.title', { defaultValue: 'Iscrizione confermata' })}
            </h1>
            <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-gray-600">
              {t('nlConfirm.body', { defaultValue: 'Benvenuto nella lettera di Aurya. La prossima arriva anche a te: una pratica raccontata bene, una persona della rete, zero rumore.' })}
            </p>
            {leadMagnetUrl && (
              <a href={leadMagnetUrl} target="_blank" rel="noopener noreferrer"
                 onClick={() => trackEvent('lead_magnet_download', { source: 'confirm' })}
                 className="mt-6 inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white"
                 style={{ backgroundColor: GOLD }}>
                <Download className="h-4 w-4" aria-hidden />
                {t('nl.magnetCta', { defaultValue: 'Scarica il materiale di benvenuto' })}
              </a>
            )}
            {next && (
              <div className="mt-6">
                <Link to={next}
                      className="inline-flex items-center gap-2 rounded-full border-2 border-[#376254] px-6 py-3 text-sm font-semibold text-[#376254] hover:bg-[#376254] hover:text-white transition-colors"
                      data-testid="nl-confirm-next">
                  {nextLabel} →
                </Link>
              </div>
            )}
            {!localStorage.getItem('platform_token') && !localStorage.getItem('token') && (
              <p className="mt-6 text-sm text-gray-600" data-testid="ponte-account">
                {t('nlConfirm.ponte', { defaultValue: 'Vuoi ritrovare guide e meditazioni su ogni dispositivo?' })}{' '}
                <a href={creaAccount(emailDellaProva(), next)} data-testid="ponte-account-crea"
                  className="underline text-[#376254]">
                  {t('nlConfirm.ponteCta', { defaultValue: 'Crea il tuo account Aurya' })}
                </a>
              </p>
            )}
            <div className="mt-8">
              <Link to={`/newsletter/preferenze/${token}`}
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-[#376254] underline">
                <SlidersHorizontal className="h-4 w-4" aria-hidden />
                {t('nlConfirm.prefs', { defaultValue: 'Scegli cosa ricevere (temi, ritiri nella tua zona)' })}
              </Link>
            </div>
          </div>
        )}

        {(state === 'expired' || state === 'invalid') && (
          <div data-testid="nl-confirm-error">
            <h1 className="font-brand text-2xl text-gray-900">
              {state === 'expired'
                ? t('nlConfirm.expired', { defaultValue: 'Questo link è scaduto' })
                : t('nlConfirm.invalid', { defaultValue: 'Questo link non è valido' })}
            </h1>
            <p className="mx-auto mt-3 max-w-md text-sm text-gray-600">
              {t('nlConfirm.retry', { defaultValue: 'Nessun problema: iscriviti di nuovo dalla pagina della newsletter e ti invieremo un link fresco.' })}
            </p>
            <Link to="/newsletter"
                  className="mt-6 inline-flex rounded-full px-6 py-3 text-sm font-semibold text-white"
                  style={{ backgroundColor: GOLD }}>
              {t('nlConfirm.toNewsletter', { defaultValue: 'Vai alla newsletter' })}
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
