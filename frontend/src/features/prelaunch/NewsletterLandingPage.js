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
 * parte ACCESA, con la città), la Lettera quando vale la pena. Il
 * salvataggio del Lab richiede l'account: si promette solo come
 * «passo dopo» (il ponte vive nella pagina di conferma).
 *
 * LE TRE REGOLE DI CONVERSIONE:
 *   1. il form sta nel PRIMO SCHERMO (hero a due colonne su desktop,
 *      form subito sotto il titolo su mobile); CP (10/9 notte): NON si
 *      ripete piu' in fondo, la chiusura e' un bottone che ci riporta,
 *      e l'elenco dei benefici nell'hero e' uscito (la frase di
 *      apertura li dice gia', le tre schede li spiegano);
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
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Headphones, CalendarHeart, Mail } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';
import {
  Section, DisplayTitle, Lede, PhotoOpener, EditorialCta,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/hero-destination.webp';
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
      {/* founder 3/9 sera: nome e interessi restano nel form (il nome
          e' il saluto delle email, gli interessi rendono vera
          l'anteprima «nella tua zona, sui tuoi temi»): niente variante
          leggera qui, solo la preferenza accesa */}
      <LeadForm
        type="traveler"
        subscribe
        compact
        showName
        experiencesOptIn
        experiencesDefault
        accent={SAGE}
        context="newsletter"
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
    title: t('nl.seoTitle', { defaultValue: 'Il Cerchio di Aurya | Meditazioni gratuite e ritiri in anteprima' }),
    description: t('nl.seoDesc', { defaultValue: 'Entra nel Cerchio di Aurya: meditazioni riservate gratuite, ritiri ed esperienze olistiche in anteprima nella tua zona e la Lettera, quando vale la pena. Ti cancelli con un clic.' }),
    canonicalPath: '/newsletter',
  });

  /* il form e' uno solo (nel primo schermo): la chiusura ci riporta */
  const scrollToForm = (e) => {
    e.preventDefault();
    const riduci = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.getElementById('iscriviti')?.scrollIntoView({ behavior: riduci ? 'auto' : 'smooth', block: 'start' });
  };

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
      // founder 3/9 sera: nessuna cadenza dichiarata (una frequenza
      // promessa e' un vincolo, non un valore): arriva quando vale la pena
      title: t('nl.r3t', { defaultValue: 'La Lettera' }),
      body: t('nl.r3b', { defaultValue: 'Una pratica raccontata bene e una persona della rete da conoscere.' }),
    },
  ];

  /* founder 3/9 sera: via le righe che «sembrano quasi fake» (chi
     scrive, nessun automatismo...). Al loro posto una cosa che si puo'
     FARE prima di entrare: due assaggi veri, che sono la prova migliore. */
  const assaggi = [
    {
      // founder 3/9 sera: l'assaggio deve essere DAVVERO senza
      // iscrizione — vive su Aurya Sound (l'anteprima da 90 secondi),
      // non su /meditazioni che chiede subito di entrare
      to: '/sound',
      title: t('nl.a1t', { defaultValue: 'Ascolta un assaggio' }),
      body: t('nl.a1b', { defaultValue: 'Su Aurya Sound ascolti novanta secondi di una meditazione riservata, senza iscriverti. Se ti fa bene, il resto è dentro.' }),
      cta: t('nl.a1c', { defaultValue: 'Vai su Aurya Sound' }),
    },
    {
      to: '/operatori',
      title: t('nl.a2t', { defaultValue: 'Guarda chi c’è nella rete' }),
      body: t('nl.a2b', { defaultValue: 'I professionisti che raccontiamo, con i loro servizi e i loro ritiri: sono loro che ti avviseremo per primi.' }),
      cta: t('nl.a2c', { defaultValue: 'Scopri i professionisti' }),
    },
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
              {/* CP (10/9 notte): qui c'era l'elenco delle tre cose che
                  ricevi, cioe' la frase qui sopra ripetuta a capo: le tre
                  schede sotto le spiegano una volta sola. */}
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

        {/* ── 3. PROVA PRIMA DI ENTRARE — due assaggi veri ─────────── */}
        <Section tone="sand" rhythm="screen" width="max-w-5xl" labelledBy="nl-who-title">
          <div data-testid="nl-who">
            <DisplayTitle as="h2" id="nl-who-title" size="section" measure="title">
              {t('nl.whoTitle', { defaultValue: 'Prova prima di entrare.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-2">
              {assaggi.map((a) => (
                <Link key={a.to} to={a.to}
                      className="group flex h-full flex-col rounded-[1.75rem] bg-white p-7 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] transition-shadow hover:shadow-[0_1px_2px_rgba(30,47,40,0.06),0_24px_48px_-24px_rgba(30,47,40,0.35)] sm:p-8">
                  <h3 className="font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
                    {a.title}
                  </h3>
                  <p className="mt-3 max-w-[46ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">
                    {a.body}
                  </p>
                  <span className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-[#2f5749] group-hover:underline">
                    {a.cta} →
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 4. LA CHIUSURA — un bottone, non un secondo form ────────
            CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili
            logici e storytelling»): il form e' UNO, nel primo schermo;
            chi ha letto fino in fondo ci torna con un clic. */}
        <Section tone="sage" rhythm="screen" width="max-w-2xl" labelledBy="nl-end-title">
          <div data-testid="nl-end">
            <DisplayTitle as="h2" id="nl-end-title" size="section" measure="title">
              {t('nl.endTitle', { defaultValue: 'Entra nel Cerchio.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-6">
              {t('nl.end1', { defaultValue: 'Scriviamo solo quando vale il tuo tempo. Ti cancelli con un clic.' })}
            </Lede>
            <div className="mt-8">
              <EditorialCta href="#iscriviti" onClick={scrollToForm} variant="solid" tone="dark" data-testid="nl-end-cta">
                {t('nl.cta', { defaultValue: 'Entra nel Cerchio' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
