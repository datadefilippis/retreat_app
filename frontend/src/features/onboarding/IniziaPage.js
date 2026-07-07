/**
 * IniziaPage — /inizia (O2, 5/7/2026). docs/ONBOARDING_PLAN.md.
 *
 * La checklist che accompagna l'operatore dal signup al primo ritiro
 * online. Stato SEMPRE derivato dai dati (onboarding-status): chi fa
 * le cose a modo suo la vede comunque aggiornarsi. Ordine = binario
 * (store-first: senza store la pubblicazione e' bloccata dal backend).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Skeleton } from '../../components/ui/skeleton';
import {
  CreditCard, Store, Tent, Rocket, Sparkles, Check, ArrowRight,
  ExternalLink, PartyPopper,
} from 'lucide-react';
import api from '../../api/client';

export default function IniziaPage() {
  const { t } = useTranslation('dashboard');
  const [status, setStatus] = useState(null);

  const load = useCallback(() => {
    api.get('/organizations/current/onboarding-status')
      .then(res => setStatus(res.data))
      .catch(() => setStatus({ steps: {}, completed_count: 0, total: 5, links: {} }));
  }, []);

  useEffect(() => {
    load();
    // il ritorno dagli step (Stripe hosted, wizard...) riatterra qui:
    // ricarica lo stato quando la pagina torna in focus
    const onFocus = () => load();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [load]);

  if (!status) {
    return (
      <AppLayout>
        <Header title={t('onboarding.title', { defaultValue: 'Inizia qui' })} />
        <div className="p-4 md:p-8 max-w-3xl"><Skeleton className="h-96 w-full rounded-2xl" /></div>
      </AppLayout>
    );
  }

  const s = status.steps || {};
  const links = status.links || {};
  const pct = Math.round((status.completed_count / status.total) * 100);

  // GT6 — scala del valore profilo-first: il gradino 0 è la VETRINA,
  // completabile senza store, prodotti o Stripe (salvi la bio → sei
  // online su /o/…). Il resto segue nell'ordine del percorso reale.
  const STEPS = [
    {
      key: 'profile_completed', icon: Sparkles, minutes: 10,
      title: t('onboarding.profile_title', { defaultValue: 'La tua vetrina' }),
      why: t('onboarding.profile_why', { defaultValue: 'Bio, foto e social: la tua pagina professionale in 4 lingue, indicizzata su Google. Senza store, senza prodotti — salvi e sei online.' }),
      cta: t('onboarding.profile_cta', { defaultValue: 'Crea la vetrina' }),
      href: '/public-profile',
    },
    {
      key: 'stripe_connected', icon: CreditCard, minutes: 5,
      title: t('onboarding.stripe_title', { defaultValue: 'Collega i pagamenti' }),
      why: t('onboarding.stripe_why', { defaultValue: 'È dove arrivano i tuoi incassi: direttamente sul tuo conto, con caparre e saldi gestiti in automatico. Serve anche per comparire nel calendario pubblico.' }),
      cta: t('onboarding.stripe_cta', { defaultValue: 'Collega Stripe' }),
      href: '/settings',
    },
    {
      key: 'store_created', icon: Store, minutes: 4,
      title: t('onboarding.store_title', { defaultValue: 'Crea il tuo store' }),
      why: t('onboarding.store_why', { defaultValue: "L'indirizzo pubblico delle tue pagine — con il profilo che diventa la tua pagina Chi siamo." }),
      cta: t('onboarding.store_cta', { defaultValue: 'Crea lo store' }),
      href: '/stores',
    },
    {
      key: 'retreat_created', icon: Tent, minutes: 5,
      title: t('onboarding.retreat_title', { defaultValue: 'Il tuo primo ritiro' }),
      why: t('onboarding.retreat_why', { defaultValue: 'Titolo, categoria, date, posti e caparra: il wizard ti guida in 5 passi.' }),
      cta: t('onboarding.retreat_cta', { defaultValue: 'Crea il ritiro' }),
      href: '/events/new',
    },
    {
      key: 'retreat_published', icon: Rocket, minutes: 1,
      title: t('onboarding.publish_title', { defaultValue: 'Metti online' }),
      why: t('onboarding.publish_why', { defaultValue: 'Un click e il ritiro è prenotabile: appare nel tuo store E nella directory dei ritiri.' }),
      cta: t('onboarding.publish_cta', { defaultValue: 'Vai ai tuoi ritiri' }),
      href: '/events',
    },
  ];

  return (
    <AppLayout>
      <Header
        title={t('onboarding.title', { defaultValue: 'Inizia qui' })}
        subtitle={t('onboarding.subtitle', { defaultValue: 'Dal primo accesso al primo ritiro online — ti accompagniamo noi.' })}
      />
      <div className="p-4 md:p-8 max-w-3xl space-y-4">

        {/* Barra progresso */}
        <div className="rounded-2xl border bg-card p-4">
          <div className="flex items-center justify-between text-sm font-medium">
            <span>
              {t('onboarding.progress', {
                done: status.completed_count, total: status.total,
                defaultValue: '{{done}} di {{total}} completati',
              })}
            </span>
            <span className="text-muted-foreground">{pct}%</span>
          </div>
          <div className="mt-2 h-2.5 rounded-full bg-muted overflow-hidden">
            <div className="h-full rounded-full bg-primary transition-all duration-500"
                 style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Sei online! */}
        {status.is_complete && (
          <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-5">
            <div className="flex items-center gap-2 text-primary font-bold">
              <PartyPopper className="h-5 w-5" />
              {t('onboarding.done_title', { defaultValue: 'Sei online!' })}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {t('onboarding.done_body', { defaultValue: 'Le tue pagine sono vive. Ecco dove ti trovano i partecipanti:' })}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {links.landing && (
                <a href={links.landing} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-1.5 rounded-full bg-primary text-primary-foreground px-4 py-1.5 text-sm font-semibold">
                  {t('onboarding.link_landing', { defaultValue: 'La pagina del ritiro' })} <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              {links.store && (
                <a href={links.store} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 text-primary px-4 py-1.5 text-sm font-semibold">
                  {t('onboarding.link_store', { defaultValue: 'Il tuo store' })} <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              {links.profile && (
                <a href={links.profile} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 text-primary px-4 py-1.5 text-sm font-semibold">
                  {t('onboarding.link_profile', { defaultValue: 'Il tuo profilo' })} <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              <a href={links.directory || '/ritiri'} target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 text-primary px-4 py-1.5 text-sm font-semibold">
                {t('onboarding.link_directory', { defaultValue: 'La directory dei ritiri' })} <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              {t('onboarding.done_next', { defaultValue: 'Da qui in poi: le caparre arrivano da sole, i promemoria di saldo partono in automatico, e gli ordini li trovi in Ordini.' })}
            </p>
          </div>
        )}

        {/* Step */}
        {STEPS.map((step, idx) => {
          const done = Boolean(s[step.key]);
          const Icon = step.icon;
          const isNext = !done && STEPS.slice(0, idx).every(prev => s[prev.key] || prev.optional);
          return (
            <div key={step.key}
                 className={`rounded-2xl border bg-card p-4 flex items-start gap-4 transition-all ${
                   done ? 'opacity-70' : isNext ? 'border-primary/40 shadow-md' : ''
                 }`}>
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                done ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
              }`}>
                {done ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className={`font-semibold ${done ? 'line-through text-muted-foreground' : ''}`}>
                    {idx + 1}. {step.title}
                  </p>
                  {step.optional && !done && (
                    <span className="text-[10px] rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
                      {t('onboarding.optional', { defaultValue: 'consigliato' })}
                    </span>
                  )}
                  {!done && (
                    <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
                      ~{step.minutes} min
                    </span>
                  )}
                </div>
                {!done && (
                  <>
                    <p className="text-sm text-muted-foreground mt-0.5">{step.why}</p>
                    <div className="mt-2.5 flex flex-wrap items-center gap-3">
                      <Link to={step.href}
                            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-semibold ${
                              isNext ? 'bg-primary text-primary-foreground' : 'border text-foreground hover:bg-muted/50'
                            }`}>
                        {step.cta} <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                      {step.secondary && (
                        <Link to={step.secondary.href}
                              className="text-xs text-primary hover:underline">
                          {step.secondary.label}
                        </Link>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </AppLayout>
  );
}
