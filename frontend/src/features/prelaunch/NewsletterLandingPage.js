/**
 * NewsletterLandingPage — /newsletter: «Il Cerchio di Aurya».
 *
 * STORIA. Nata come «La Lettera di Aurya» (LT1), rifatta come
 * APPARTENENZA (CN1, 3/9/2026: form nel primo schermo, promesse
 * concrete, assaggi veri; docs/NEWSLETTER_CONVERSIONE_PIANO_2026-09.md),
 * potata con CP (10/9: un solo form, la chiusura e' un bottone).
 *
 * LA SECONDA VIA (founder, 6/10/2026): /newsletter e' la seconda porta
 * del Cerchio accanto a /cerca-ritiro. Qui si entra con NOME ed EMAIL e
 * basta; tutto quello che riguarda i ritiri e' FACOLTATIVO e si apre
 * con una casella («Vorrei ricevere anche ritiri ed esperienze in linea
 * con i miei interessi»). Aperta, la casella mostra ESATTAMENTE i campi
 * di /cerca-ritiro — dove vivi, dove ti immagini il ritiro, quanto
 * investire, la tua eta', le quattordici vie gia' aperte — perche' il
 * blocco e' lo stesso (PreferenzeRitiri dentro AvvisamiRitiri, FV5/US).
 * Prima la preferenza partiva ACCESA (CN1): ora parte SPENTA, perche'
 * chi vuole un ritiro ha la sua porta e chi vuole solo il Cerchio non
 * deve scavalcare cinque campi.
 *
 * Il testo e' quello del founder (6/10), riga per riga: apertura, tre
 * cose che trovi, «prima di entrare puoi ascoltare», «puoi conoscere le
 * persone», chiusura «Ci vediamo nel Cerchio».
 *
 * LA MECCANICA NON SI TOCCA: LeadForm con `subscribe`, POST
 * /public/newsletter/subscribe, doppio opt-in, consenso obbligatorio
 * col suo testo versionato (lib/testiConsenso.js). Rotta, endpoint e
 * chiavi i18n restano «newsletter»/«nl»: nomi tecnici, non un vestito.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Headphones, CalendarHeart, Mail } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';
import { testoConsenso } from '../../lib/testiConsenso';
import {
  Section, DisplayTitle, Lede, PhotoOpener, EditorialCta,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/hero-destination.webp';
const SAGE = '#2f5749';

/** la scheda del form: bianco pieno, l'unico della pagina, così l'occhio ci finisce dentro */
function SchedaForm({ t, id, context }) {
  return (
    <div id={id}
         className="rounded-[1.75rem] bg-white p-5 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-7"
         data-testid={`nl-form-${context}`}>
      {/* founder 6/10: nome ed email, poi la casella FACOLTATIVA dei ritiri
          (spenta) che apre gli stessi campi di /cerca-ritiro, vie comprese */}
      <LeadForm
        type="traveler"
        subscribe
        compact
        showName
        experiencesOptIn
        vieAperte
        experiencesLabel={t('nl.expFlag', { defaultValue: 'Vorrei ricevere anche ritiri ed esperienze in linea con i miei interessi' })}
        experiencesHint={t('nl.expHint', { defaultValue: 'Se vuoi, raccontaci qualcosa in più su di te. Ci aiuterà a farti arrivare solo proposte che possono davvero interessarti.' })}
        accent={SAGE}
        context="newsletter"
        ctaLabel={t('nl.cta', { defaultValue: 'Entra nel Cerchio' })}
        /* Lotto D (24/9/2026): il testo della casella e' UNO su tutte le
           porte, versionato in lib/testiConsenso.js (non passa da i18n) */
        consentText={testoConsenso().testo}
        thanksBody={t('nl.thanksDoi', { defaultValue: 'Quasi dentro: apri la tua casella e clicca «Entro nel Cerchio» nell’email che ti abbiamo appena mandato.' })}
      />
      {/* la riga di fiducia: vera con o senza doppio opt-in */}
      <p className="mt-4 text-xs leading-relaxed text-foreground/60">
        {t('nl.trust', { defaultValue: 'Puoi cambiare idea in qualsiasi momento. Gratis, e ti cancelli con un clic.' })}
      </p>
    </div>
  );
}

export default function NewsletterLandingPage() {
  const { t } = useTranslation('prelaunch');

  useSeoMeta({
    title: t('nl.seoTitle', { defaultValue: 'Il Cerchio di Aurya | Meditazioni gratuite e ritiri in anteprima' }),
    description: t('nl.seoDesc', { defaultValue: 'Entra nel Cerchio di Aurya: meditazioni da ascoltare, storie di persone, pratiche da provare e, se vuoi, ritiri ed esperienze in linea con i tuoi interessi.' }),
    canonicalPath: '/newsletter',
  });

  /* il form e' uno solo (nel primo schermo): la chiusura ci riporta */
  const scrollToForm = (e) => {
    e.preventDefault();
    const riduci = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.getElementById('iscriviti')?.scrollIntoView({ behavior: riduci ? 'auto' : 'smooth', block: 'start' });
  };

  /* founder 6/10: le tre cose che trovi, nel suo ordine */
  const trovi = [
    {
      Icon: Headphones,
      title: t('nl.r1t', { defaultValue: 'Una meditazione da ascoltare' }),
      body: t('nl.r1b', { defaultValue: 'Pratiche complete di Aurya Sound da portare con te, da ascoltare quando senti di averne bisogno.' }),
    },
    {
      Icon: Mail,
      title: t('nl.r2t', { defaultValue: 'La Lettera di Aurya' }),
      body: t('nl.r2b', { defaultValue: 'Una volta ogni tanto, quando abbiamo qualcosa da condividere. Una pratica, una storia, una persona della rete, un luogo che ci ha colpito. Qualcosa che pensiamo possa valere qualche minuto del tuo tempo.' }),
    },
    {
      Icon: CalendarHeart,
      title: t('nl.r3t', { defaultValue: 'I ritiri che potresti amare' }),
      body: t('nl.r3b', { defaultValue: 'Se scegli di raccontarci cosa cerchi, possiamo farti conoscere anche ritiri ed esperienze in linea con i tuoi interessi, nella zona che preferisci.' }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA CON IL FORM ─────────────────────────────────
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
                {t('nl.lead', { defaultValue: 'Un modo semplice per restare vicino a quello che ti fa stare bene.' })}
              </p>
              <p className="mt-4 max-w-[52ch] text-pretty text-base leading-relaxed text-hero-shadow opacity-90 sm:text-lg">
                {t('nl.lead2', { defaultValue: 'Riceverai meditazioni da ascoltare, storie di persone da conoscere, pratiche da provare e, quando ci sarà qualcosa che potrebbe interessarti, ritiri ed esperienze da scoprire.' })}
              </p>
            </div>
            <div className="lg:col-span-6 lg:pt-2">
              <SchedaForm t={t} id="iscriviti" context="hero" />
            </div>
          </div>
        </PhotoOpener>

        {/* ── 2. COSA TROVERAI NEL CERCHIO — tre cose vere ──────────── */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl" labelledBy="nl-find-title">
          <div data-testid="nl-find">
            <DisplayTitle as="h2" id="nl-find-title" size="section" measure="title">
              {t('nl.findTitle', { defaultValue: 'Cosa troverai nel Cerchio' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-3">
              {trovi.map(({ Icon, title, body }) => (
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

        {/* ── 3. PRIMA DI ENTRARE, PUOI ASCOLTARE ──────────────────────
            l'assaggio senza iscrizione vive su Aurya Sound (novanta
            secondi): non su /meditazioni, che chiede subito di entrare */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl" labelledBy="nl-who-title">
          <div data-testid="nl-who">
            <DisplayTitle as="h2" id="nl-who-title" size="section" measure="title">
              {t('nl.whoTitle', { defaultValue: 'Prima di entrare, puoi ascoltare.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">
              {t('nl.a1b', { defaultValue: 'Su Aurya Sound puoi ascoltare un assaggio di una delle meditazioni riservate al Cerchio.' })}
            </Lede>
            <p className="mt-3 text-pretty text-base leading-relaxed text-foreground/75 sm:text-lg">
              {t('nl.a1b2', { defaultValue: 'Novanta secondi, senza registrarti.' })}
            </p>
            <div className="mt-8">
              <EditorialCta to="/sound" variant="solid" data-testid="nl-assaggio">
                {t('nl.a1c', { defaultValue: 'Ascolta Aurya Sound' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 4. E PUOI CONOSCERE LE PERSONE ───────────────────────── */}
        <Section tone="cream" rhythm="screen" width="max-w-3xl" labelledBy="nl-rete-title">
          <div data-testid="nl-rete">
            <DisplayTitle as="h2" id="nl-rete-title" size="section" measure="title">
              {t('nl.a2t', { defaultValue: 'E puoi conoscere le persone che fanno parte di Aurya.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">
              {t('nl.a2b', { defaultValue: 'Operatori, insegnanti e professionisti che hanno scelto di condividere con noi il loro modo di lavorare, le loro pratiche e le loro esperienze.' })}
            </Lede>
            <div className="mt-8">
              <EditorialCta to="/operatori" variant="quiet" data-testid="nl-rete-cta">
                {t('nl.a2c', { defaultValue: 'Scopri la rete' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 5. LA CHIUSURA — un bottone, non un secondo form ────────
            CP (10/9/2026 notte): il form e' UNO, nel primo schermo;
            chi ha letto fino in fondo ci torna con un clic. */}
        <Section tone="sage" rhythm="screen" width="max-w-2xl" labelledBy="nl-end-title">
          <div data-testid="nl-end">
            <DisplayTitle as="h2" id="nl-end-title" size="section" measure="title">
              {t('nl.endTitle', { defaultValue: 'Ci vediamo nel Cerchio.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-6">
              {t('nl.end1', { defaultValue: 'Un posto dove trovare, ogni tanto, qualcosa che vale la pena fermarsi ad ascoltare.' })}
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
