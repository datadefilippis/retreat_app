/**
 * TravelerLandingPage — /cerca-ritiro: «Trovami il mio ritiro».
 *
 * RB4 (10/9/2026, REBRANDING — docs/REBRANDING_STRATEGIA_2026-09.md).
 * La porta di chi cerca. In luglio questa pagina (con zero contenuti)
 * raccoglieva contatti «cerco un ritiro»; dal 4/8 rimandava al Cerchio
 * e i contatti sono finiti a zero: «Entra nel Cerchio» e' un
 * contenitore, «Trovami il mio ritiro» e' l'oggetto del desiderio.
 *
 * La porta si chiama con l'oggetto; il Cerchio resta il nome di cio'
 * che ricevi. Il modulo e' quello di luglio, che funzionava (nome,
 * email, dove vivi, cosa ti chiama, quanto lontano, quanto vorresti
 * investire) e ISCRIVE AL CERCHIO con la preferenza «ritiri ed
 * esperienze» accesa: stessa meccanica (LeadForm `subscribe`, doppio
 * opt-in, consenso col suo testo), zero flussi nuovi.
 *
 * Cosa succede dopo, detto PRIMA: subito le meditazioni riservate;
 * la Lettera quando vale la pena (mai una cadenza dichiarata: regola
 * del founder, 3/9); il 15 gennaio 2027 la selezione dei ritiri di
 * primavera 2027, scelti per quello che ci hai detto.
 *
 * Grammatica: la stessa del Cerchio (CN1) — form nel primo schermo,
 * promesse concrete una per riga, assaggi veri prima di entrare. Foto:
 * hero-destination (l'uliveto), che e' gia' il volto della porta in home.
 *
 * CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili logici e
 * storytelling»): il modulo era DUE volte (apertura e fondo) e i tre
 * benefici del Cerchio tre volte. Ora il modulo e' uno, in apertura; la
 * chiusura e' un bottone che ci riporta. Il filo resta: il desiderio e
 * la domanda (1) → cosa succede dopo (2) → perche' fidarsi (3) → prova
 * prima (4) → torna al modulo (5).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Headphones, Mail, CalendarHeart, Leaf, ShieldCheck, MapPin } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';

// RB12 (10/9/2026) — dal Magazine si arriva con ?tema=<categoria>: il
// chip corrispondente parte acceso (vocabolario dei chip di LeadForm).
const TEMA_TO_CHIP = { yoga: 'yoga', meditazione: 'meditation', breathwork: 'breathwork',
  suono: 'sound', femminile: 'women', cammini: 'nature', detox: 'detox', massaggio: 'mixed',
  // TX (10/9/2026): le categorie nuove del Magazine → il chip della via
  reiki: 'reiki', costellazioni: 'constellations', astrologia: 'astrology',
  ayurveda: 'ayurveda', tantra: 'tantra', crescita: 'growth' };
function temaIniziale() {
  if (typeof window === 'undefined') return [];
  const tema = new URLSearchParams(window.location.search).get('tema');
  return TEMA_TO_CHIP[tema] ? [TEMA_TO_CHIP[tema]] : [];
}
import {
  Section, DisplayTitle, Lede, PhotoOpener, EditorialCta,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/hero-destination.webp';
const SAGE = '#2f5749';

/** la scheda del modulo: bianco pieno, l'unico bianco della pagina */
function SchedaForm({ t, id, context, titolo }) {
  return (
    <div id={id}
         className="rounded-[1.75rem] bg-white p-5 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-7"
         data-testid={`tr-form-${context}`}>
      {titolo && (
        <p className="mb-4 font-display text-xl leading-tight text-foreground sm:text-2xl">
          {titolo}
        </p>
      )}
      {/* il modulo di luglio: nome, email, dove vivi, cosa ti chiama,
          quanto lontano, quanto investire. Iscrive al Cerchio con la
          preferenza ritiri ACCESA (wantsExperiencesAlways). */}
      <LeadForm
        type="traveler"
        subscribe
        showName
        wantsExperiencesAlways
        initialInterests={temaIniziale()}
        accent={SAGE}
        context="cerca-ritiro"
        ctaLabel={t('tr.cta', { defaultValue: 'Trovami il mio ritiro' })}
        consentText={t('tr.consent', { defaultValue: 'Acconsento a ricevere le email del Cerchio di Aurya, con ritiri ed esperienze selezionati in base alle mie preferenze.' })}
        thanksBody={t('tr.thanksDoi', { defaultValue: 'Quasi dentro: apri la tua casella e conferma. Appena confermi si aprono le meditazioni riservate, e da lì in poi ricevi ritiri ed esperienze pensati sui tuoi interessi e le tue preferenze.' })}
      />
      <p className="mt-4 text-xs leading-relaxed text-foreground/60">
        {t('tr.trust', { defaultValue: 'Una conferma via email, poi sei dentro. Gratis e puoi cancellarti con un clic.' })}
      </p>
      {/* PL22 — il canale diretto resta: c'e' chi i form non li ama */}
      <p className="mt-2 text-xs text-foreground/60">
        {t('tr.directT', { defaultValue: 'Preferisci scriverci direttamente?' })}{' '}
        <a href="mailto:info@aurya.life" className="font-medium underline underline-offset-2 text-[#2f5749]">info@aurya.life</a>
      </p>
    </div>
  );
}

export default function TravelerLandingPage() {
  const { t } = useTranslation('prelaunch');

  useSeoMeta({
    title: t('tr.seoTitle', { defaultValue: 'Trovami il mio ritiro | Ritiri olistici vicino a te | Aurya' }),
    description: t('tr.seoDesc', { defaultValue: 'Dicci cosa cerchi e dove: ti avvisiamo quando troviamo un ritiro adatto a te, vicino a dove vuoi andare. Subito le meditazioni riservate, poi ritiri ed esperienze pensati sui tuoi interessi.' }),
    canonicalPath: '/cerca-ritiro',
  });

  /* il modulo e' uno solo (in apertura): la chiusura ci riporta */
  const scrollToForm = (e) => {
    e.preventDefault();
    const riduci = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.getElementById('racconta')?.scrollIntoView({ behavior: riduci ? 'auto' : 'smooth', block: 'start' });
  };

  /* cosa succede dopo, detto prima: tre tempi */
  const dopo = [
    {
      Icon: Headphones,
      when: t('tr.d1w', { defaultValue: 'Subito' }),
      label: t('tr.l1', { defaultValue: 'Meditazioni riservate' }),
      title: t('tr.d1t', { defaultValue: 'Le meditazioni riservate' }),
      body: t('tr.d1b', { defaultValue: 'Sessioni complete di Aurya Sound, disponibili gratuitamente per chi entra nel Cerchio.' }),
    },
    {
      Icon: Mail,
      when: t('tr.d2w', { defaultValue: 'Ogni tanto' }),
      label: t('tr.l2', { defaultValue: 'La Lettera di Aurya, con pratiche e persone della rete' }),
      title: t('tr.d2t', { defaultValue: 'La Lettera di Aurya' }),
      body: t('tr.d2b', { defaultValue: 'Un’email, solo quando vale la pena: una pratica raccontata bene, una persona della rete da conoscere, i ritiri da scoprire in anteprima.' }),
    },
    {
      Icon: CalendarHeart,
      // founder 10/9 sera: niente data («non voglio vincolarmi»), il vantaggio
      when: t('tr.d3w', { defaultValue: 'Quando c’è quello giusto' }),
      label: t('tr.l3', { defaultValue: 'Ritiri ed esperienze olistiche pensati sui tuoi interessi' }),
      title: t('tr.d3t', { defaultValue: 'Ritiri ed esperienze pensati per te' }),
      body: t('tr.d3b', { defaultValue: 'Ti proponiamo ritiri ed esperienze olistiche scelti in base ai tuoi interessi e alle tue preferenze: chi li conduce, il luogo, il prezzo e la caparra.' }),
    },
  ];

  /* le tre promesse di luglio, ancora vere */
  const promesse = [
    { Icon: Leaf, title: t('tr.b1t', { defaultValue: 'Scelti, non elencati' }),
      body: t('tr.b1b', { defaultValue: 'Dietro ogni ritiro c’è una persona, un luogo vero e le recensioni di chi c’è stato davvero. Sai a chi ti affidi, prima di partire.' }) },
    { Icon: ShieldCheck, title: t('tr.b2t', { defaultValue: 'Il posto è tuo, senza ansia' }),
      body: t('tr.b2b', { defaultValue: 'Blocchi con una caparra, il saldo arriva dopo e le condizioni sono chiare fin dall’inizio.' }) },
    { Icon: MapPin, title: t('tr.b3t', { defaultValue: 'Vicino a dove sei' }),
      body: t('tr.b3b', { defaultValue: 'Ci dici dove vuoi andare e ti proponiamo esperienze raggiungibili. A volte il viaggio che serve è a un’ora da casa.' }) },
  ];

  /* prova prima di entrare: due cose vere che si possono fare adesso */
  const assaggi = [
    {
      to: '/sound',
      title: t('tr.a1t', { defaultValue: 'Ascolta un assaggio' }),
      body: t('tr.a1b', { defaultValue: 'Su Aurya Sound puoi ascoltare novanta secondi di una meditazione riservata, senza iscriverti. Se vuoi continuare, il resto è dentro.' }),
      cta: t('tr.a1c', { defaultValue: 'Vai su Aurya Sound' }),
    },
    {
      to: '/operatori',
      title: t('tr.a2t', { defaultValue: 'Guarda chi c’è nella rete' }),
      body: t('tr.a2b', { defaultValue: 'I professionisti che raccontiamo, con i loro servizi e i loro ritiri.' }),
      cta: t('tr.a2c', { defaultValue: 'Scopri i professionisti' }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA CON IL MODULO — l'oggetto e la domanda ─────
            Titolo e promessa a sinistra, il modulo a destra; su mobile
            il modulo segue il titolo entro il primo schermo. */}
        <PhotoOpener
          data-testid="tr-open"
          image={OPENER_PHOTO}
          focus="50% 50%"
          height="tall"
          align="left"
          width="max-w-6xl"
          labelledBy="tr-open-title"
        >
          <div className="grid gap-8 lg:grid-cols-12 lg:items-start lg:gap-12">
            <div className="lg:col-span-6">
              <DisplayTitle as="h1" id="tr-open-title" size="hero" measure="title"
                            className="text-hero-shadow">
                {t('tr.title', { defaultValue: 'C’è un ritiro che ti sta aspettando.' })}
              </DisplayTitle>
              <p className="mt-6 max-w-[46ch] text-balance text-lg leading-relaxed text-hero-shadow opacity-95 sm:text-xl">
                {t('tr.subtitle', { defaultValue: 'Il silenzio di un uliveto, un cerchio di persone vere, il respiro che torna lento. Dicci cosa cerchi e dove. Ti avvisiamo quando troviamo un ritiro adatto a te, vicino a dove vuoi andare.' })}
              </p>
              <ul className="mt-7 space-y-2 text-hero-shadow" data-testid="tr-open-valori">
                {dopo.map(({ Icon, when, label, title }) => (
                  <li key={title} className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Icon className="h-5 w-5 shrink-0 text-[#d6c49a]" aria-hidden />
                    <span><span className="opacity-80">{when}:</span> {label || title}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="lg:col-span-6 lg:pt-2">
              <SchedaForm t={t} id="racconta" context="hero"
                          titolo={t('tr.formTitle', { defaultValue: 'Raccontaci cosa cerchi' })} />
            </div>
          </div>
        </PhotoOpener>

        {/* ── 2. COSA SUCCEDE DOPO — tre tempi, detti prima ─────────── */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl" labelledBy="tr-dopo-title">
          <div data-testid="tr-dopo">
            <DisplayTitle as="h2" id="tr-dopo-title" size="section" measure="title">
              {t('tr.dopoTitle', { defaultValue: 'Cosa succede dopo, detto prima.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-3">
              {dopo.map(({ Icon, when, title, body }) => (
                <article key={title}
                         className="flex h-full flex-col rounded-[1.75rem] bg-white p-7 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <p className="eyebrow mt-5">{when}</p>
                  <h3 className="mt-2 font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
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

        {/* ── 3. LE TRE PROMESSE — ancora vere ─────────────────────── */}
        <Section tone="sand" rhythm="screen" width="max-w-5xl" labelledBy="tr-promesse-title">
          <div data-testid="tr-promesse">
            <DisplayTitle as="h2" id="tr-promesse-title" size="section" measure="title">
              {t('tr.promesseTitle', { defaultValue: 'Persone, non annunci.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-3">
              {promesse.map(({ Icon, title, body }) => (
                <div key={title} className="flex gap-4">
                  <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <h3 className="font-display text-[1.25rem] leading-tight text-foreground sm:text-[1.4rem]">{title}</h3>
                    <p className="mt-2 max-w-[42ch] text-[0.975rem] leading-relaxed text-foreground/75">{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 4. PROVA PRIMA DI ENTRARE — due assaggi veri ─────────── */}
        <Section tone="paper" rhythm="screen" width="max-w-5xl" labelledBy="tr-prova-title">
          <div data-testid="tr-prova">
            <DisplayTitle as="h2" id="tr-prova-title" size="section" measure="title">
              {t('tr.provaTitle', { defaultValue: 'Prova prima di entrare.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-2">
              {assaggi.map((a) => (
                <Link key={a.to} to={a.to}
                      className="group flex h-full flex-col rounded-[1.75rem] bg-[#f4f1ea] p-7 ring-1 ring-[#1e2f28]/[0.07] transition-shadow hover:shadow-[0_1px_2px_rgba(30,47,40,0.06),0_24px_48px_-24px_rgba(30,47,40,0.35)] sm:p-8">
                  <h3 className="font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">{a.title}</h3>
                  <p className="mt-3 max-w-[46ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">{a.body}</p>
                  <span className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-[#2f5749] group-hover:underline">{a.cta} →</span>
                </Link>
              ))}
            </div>
            {/* la porta dell'altro pubblico, sottovoce: chi organizza
                ritiri e' arrivato qui per sbaglio, e ha la sua strada */}
            <p className="mt-10 text-sm text-foreground/70">
              {t('tr.switch2', { defaultValue: 'Organizzi ritiri o sei un operatore olistico?' })}{' '}
              <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="tr-switch">
                {t('tr.switchCta', { defaultValue: 'Apri il tuo spazio' })}
              </EditorialCta>
            </p>
          </div>
        </Section>

        {/* ── 5. LA CHIUSURA — un bottone, non un secondo modulo ──────
            CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili
            logici e storytelling»): il modulo e' UNO, in apertura. Chi
            ha letto fino in fondo ci torna con un clic; la pagina si
            chiude con la stessa frase con cui si e' aperta. */}
        <Section tone="sage" rhythm="screen" width="max-w-2xl" labelledBy="tr-end-title">
          <div data-testid="tr-end">
            <DisplayTitle as="h2" id="tr-end-title" size="section" measure="title">
              {t('tr.endTitle', { defaultValue: 'Raccontaci cosa cerchi.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-6">
              {t('tr.end1', { defaultValue: 'Trenta secondi. Ti scriviamo solo quando c’è qualcosa che può interessarti.' })}
            </Lede>
            <div className="mt-8">
              <EditorialCta href="#racconta" onClick={scrollToForm} variant="solid" tone="dark" data-testid="tr-end-cta">
                {t('tr.cta', { defaultValue: 'Trovami il mio ritiro' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
