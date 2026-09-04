/**
 * NewsletterLandingPage — /newsletter: «Il Cerchio di Aurya» (CN1).
 *
 * STORIA. Nata come «La Lettera di Aurya» (LT1, copy del founder:
 * «Una lettera, ogni tanto», il form come sezione 4 di 5). Misurata
 * il 3/9/2026: 256 parole, il form a 5.900 px (quarto schermo),
 * apertura fatta di anti-promesse («viviamo in un mondo pieno di
 * notifiche»), nessun vantaggio concreto in pagina. In produzione 9
 * iscritti, 3 confermati, 1 solo dalla landing; chi si iscriveva per
 * sbloccare una meditazione confermava (2 su 2). Il founder: «deve
 * convertire meglio... era più coinvolgente quando dicevamo che
 * ricevevano info sui prossimi ritiri... ragionare come marketing
 * manager senza perdere umanità».
 *
 * LA STRATEGIA (docs/NEWSLETTER_CONVERSIONE_PIANO_2026-09.md): da
 * newsletter ad APPARTENENZA. Il nome è «Il Cerchio di Aurya» (nel
 * codice la prova dell'iscrizione si chiamava già cerchio). La
 * Lettera resta: è una delle cose che ricevi, non più il titolo.
 * La pila di valore è solo di cose vere, nell'ordine in cui
 * convertono: meditazioni riservate (sbloccate dall'email confermata),
 * ritiri ed esperienze in anteprima (la preferenza esiste già: qui
 * parte ACCESA, con la città), la Lettera ogni due settimane. Il
 * salvataggio del Lab richiede l'account: si promette solo come
 * «passo dopo» (il ponte vive nella pagina di conferma).
 *
 * LE TRE REGOLE DI CONVERSIONE:
 *   1. il form sta nel PRIMO SCHERMO (hero a due colonne su desktop,
 *      form subito sotto il titolo su mobile) e si ripete in fondo;
 *   2. una promessa concreta per riga, senza conteggi ne' date
 *      (founder: «meno dettagli inutili»);
 *   3. si dice cosa ricevi, mai cosa non faremo.
 *
 * LA MECCANICA NON SI TOCCA: LeadForm con `subscribe`, POST
 * /public/newsletter/subscribe, doppio opt-in, consenso obbligatorio
 * col suo testo. Cambiano i campi mostrati (email + città + preferenza
 * ritiri accesa) e le parole. Rotta, endpoint e chiavi i18n restano
 * «newsletter»/«nl»: sono nomi tecnici, non un vestito.
 *
 * FOTO: hero-destination (già il volto della Lettera in home: chi
 * clicca ritrova la stessa immagine) nell'apertura; i fondatori nella
 * firma. Contrasti: crema pieno sui veli calcolati di PhotoOpener
 * (misure LT1 in git), foreground su sabbia/bianco > 12.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Headphones, CalendarHeart, Mail } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';
import {
  Section, DisplayTitle, Lede, PhotoOpener,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/hero-destination.webp';
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';
const SAGE = '#2f5749';

/** la scheda del form: bianco pieno, l'unico della pagina, così l'occhio ci finisce dentro */
function SchedaForm({ t, id, context, titolo }) {
  return (
    <div id={id}
         className="rounded-[1.75rem] bg-white p-5 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-7"
         data-testid={`nl-form-${context}`}>
      {titolo && (
        <p className="mb-4 font-display text-xl leading-tight text-foreground sm:text-2xl">
          {titolo}
        </p>
      )}
      <LeadForm
        type="traveler"
        subscribe
        compact
        showName={false}
        experiencesOptIn
        experiencesDefault
        experiencesLight
        accent={SAGE}
        context={context === 'hero' ? 'newsletter' : 'newsletter_fondo'}
        ctaLabel={t('nl.cta', { defaultValue: 'Entra nel Cerchio' })}
        consentText={t('nl.consent', { defaultValue: 'Acconsento a ricevere le email del Cerchio di Aurya.' })}
        thanksBody={t('nl.thanksDoi', { defaultValue: 'Quasi dentro: apri la tua casella e clicca «Entro nel Cerchio» nell’email che ti abbiamo appena mandato.' })}
      />
      <p className="mt-4 text-xs leading-relaxed text-foreground/60">
        {t('nl.trust', { defaultValue: 'Una conferma via email, poi sei dentro. Gratis, e ti cancelli con un clic.' })}
      </p>
    </div>
  );
}

export default function NewsletterLandingPage() {
  const { t } = useTranslation('prelaunch');

  useSeoMeta({
    title: t('nl.seoTitle', { defaultValue: 'Il Cerchio di Aurya | Meditazioni riservate, ritiri in anteprima, una lettera quando vale' }),
    description: t('nl.seoDesc', { defaultValue: 'Entra nel Cerchio di Aurya: meditazioni riservate gratuite, ritiri ed esperienze olistiche in anteprima nella tua zona e la Lettera, ogni due settimane. Ti cancelli con un clic.' }),
    canonicalPath: '/newsletter',
  });

  const ricevi = [
    {
      Icon: Headphones,
      title: t('nl.r1t', { defaultValue: 'Meditazioni riservate' }),
      body: t('nl.r1b', { defaultValue: 'Sessioni complete di Aurya Sound che fuori dal Cerchio si possono solo assaggiare. Gratis, appena confermi.' }),
    },
    {
      Icon: CalendarHeart,
      title: t('nl.r2t', { defaultValue: 'Ritiri ed esperienze in anteprima' }),
      body: t('nl.r2b', { defaultValue: 'Ti avvisiamo prima degli altri quando un professionista della rete propone un ritiro o un’esperienza nella tua zona.' }),
    },
    {
      Icon: Mail,
      title: t('nl.r3t', { defaultValue: 'La Lettera, ogni due settimane' }),
      body: t('nl.r3b', { defaultValue: 'Una pratica raccontata bene e una persona della rete da conoscere. Si legge in cinque minuti, e vale il tempo che ci metti.' }),
    },
  ];

  const perChi = [
    t('nl.who1', { defaultValue: 'Per chi ama approfondire.' }),
    t('nl.who2', { defaultValue: 'Per chi preferisce capire prima di scegliere.' }),
    t('nl.who3', { defaultValue: 'Per chi cerca un professionista, un ritiro o una pratica, e vuole sapere prima degli altri.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA CON IL FORM — la regola numero uno ──────────
            Titolo e promessa a sinistra, il form a destra (desktop);
            su mobile il form segue il titolo entro il primo schermo. */}
        <PhotoOpener
          data-testid="nl-open"
          image={OPENER_PHOTO}
          focus="50% 50%"
          height="tall"
          align="left"
          width="max-w-6xl"
          labelledBy="nl-open-title"
          eyebrow={t('nl.eyebrow', { defaultValue: 'Il Cerchio di Aurya' })}
        >
          <div className="grid gap-8 lg:grid-cols-12 lg:items-start lg:gap-12">
            <div className="lg:col-span-6">
              <DisplayTitle as="h1" id="nl-open-title" size="hero" measure="title"
                            className="text-hero-shadow">
                {t('nl.title', { defaultValue: 'Entra nel Cerchio di Aurya.' })}
              </DisplayTitle>
              <p className="mt-6 max-w-[46ch] text-balance text-lg leading-relaxed text-hero-shadow opacity-95 sm:text-xl">
                {t('nl.lead', { defaultValue: 'Meditazioni riservate, ritiri ed esperienze in anteprima e una lettera quando vale la pena. Gratis.' })}
              </p>
              <ul className="mt-7 space-y-2 text-hero-shadow" data-testid="nl-open-valori">
                {ricevi.map(({ Icon, title }) => (
                  <li key={title} className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Icon className="h-5 w-5 shrink-0 text-[#d6c49a]" aria-hidden />
                    <span>{title}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="lg:col-span-6 lg:pt-2">
              <SchedaForm t={t} id="iscriviti" context="hero" />
            </div>
          </div>
        </PhotoOpener>

        {/* ── 2. COSA RICEVI — tre promesse vere, senza conteggi ────── */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl" labelledBy="nl-find-title">
          <div data-testid="nl-find">
            <DisplayTitle as="h2" id="nl-find-title" size="section" measure="title">
              {t('nl.findTitle', { defaultValue: 'Cosa ricevi, da subito.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-3">
              {ricevi.map(({ Icon, title, body }) => (
                <article key={title}
                         className="flex h-full flex-col rounded-[1.75rem] bg-white p-7 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="mt-5 font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
                    {title}
                  </h3>
                  <p className="mt-3 max-w-[46ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">
                    {body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 3. PER CHI E' + CHI SCRIVE — la fiducia, in una sezione ── */}
        <Section tone="sand" rhythm="screen" width="max-w-6xl" labelledBy="nl-who-title">
          <div data-testid="nl-who" className="grid gap-10 lg:grid-cols-12 lg:items-center lg:gap-14">
            <div className="lg:col-span-7">
              <DisplayTitle as="h2" id="nl-who-title" size="section" measure="title">
                {t('nl.whoTitle', { defaultValue: 'Per chi è il Cerchio?' })}
              </DisplayTitle>
              <div className="mt-7 space-y-2">
                {perChi.map((line) => (
                  <p key={line} className="text-balance text-lg leading-relaxed text-foreground/85 sm:text-xl">
                    {line}
                  </p>
                ))}
              </div>
              <p className="mt-7 max-w-[52ch] text-base leading-relaxed text-foreground/75 sm:text-lg">
                {t('nl.who4', { defaultValue: 'Lo scriviamo noi due, Davide e Valentina, con i professionisti che incontriamo. Nessun automatismo, nessuna casella riempita per riempirla.' })}
              </p>
              <p className="mt-5 font-display text-xl italic text-foreground sm:text-2xl">
                {t('nl.signature', { defaultValue: 'Davide e Valentina' })}
              </p>
            </div>
            <figure className="lg:col-span-5">
              <img src={FOUNDERS_PHOTO}
                   alt={t('nl.foundersAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya' })}
                   loading="lazy"
                   className="aspect-[4/5] w-full rounded-[1.75rem] object-cover object-[50%_35%] shadow-[0_18px_40px_-24px_rgba(30,47,40,0.35)]" />
            </figure>
          </div>
        </Section>

        {/* ── 4. IL FORM, DI NUOVO — per chi ha letto fino in fondo ──── */}
        <Section tone="sage" rhythm="screen" width="max-w-2xl" labelledBy="nl-end-title">
          <div data-testid="nl-end">
            <DisplayTitle as="h2" id="nl-end-title" size="section" measure="title">
              {t('nl.endTitle', { defaultValue: 'Entra nel Cerchio.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-6">
              {t('nl.end1', { defaultValue: 'Scriviamo solo quando vale il tuo tempo. Ti cancelli con un clic.' })}
            </Lede>
            <div className="mt-8">
              <SchedaForm t={t} id="iscriviti-fondo" context="fondo" />
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
