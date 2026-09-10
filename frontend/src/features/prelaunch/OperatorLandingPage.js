/**
 * OperatorLandingPage — /entra-nella-rete, la landing dell'OPERATORE OLISTICO.
 *
 * RB2-bis (10/9/2026 sera, founder): «l'operatore chiede una chiamata,
 * chiede i prezzi, dice che si iscrive e si prende tempo». Meno sforzo
 * cognitivo: sei schede con un titolo-verbo e una frase in grassetto
 * che dice il vantaggio, la rete, il patto fondatori in quattro
 * schede col contatore vero, tre passi, sei domande, i volti, il form.
 * Il patto: 20 fondatori entro il 31/10/2026, Club Fondatori gratis
 * fino al 30/6/2027 (routers/fondatori.py e' la fonte delle date),
 * niente «post al mese». Tono: quello della proposta del founder.
 *
 * RB2 (10/9/2026, REBRANDING — docs/REBRANDING_STRATEGIA_2026-09.md).
 * Dal 4/8 questa pagina parlava di «rete», «presenza» e «conversazione»
 * e si contraddiceva sul come si entra (candidatura + «account in un
 * minuto»); diceva «con calma», «una conversazione alla volta» e «se
 * vuoi solo comparire in un elenco non fa per te». Gli operatori la
 * leggevano, dicevano «interessante» e rimandavano: stavano facendo
 * quello che la pagina chiedeva. L'offerta vera (profilo, listino,
 * prenotazioni, eventi e ritiri con caparra, un link solo) stava a meta'
 * pagina in un elenco senza prove.
 *
 * Ora la pagina segue il trittico della voce per chi opera: COSA HAI,
 * PERCHE' ORA, COME SI ENTRA. Concreto, veloce, verbi e numeri. La
 * fiducia resta nel tono, non nella lentezza. Lessico: «operatore
 * olistico» (e' come il target si chiama), mai «gestionale».
 *
 * L'IMPIANTO VISIVO NON SI SMONTA (docs/DESIGN_PASS_DS_2026-08.md):
 * ancora scura in apertura, foto vere, alternanza dei fondi, blocchi a
 * schede, ancore multiple verso l'azione. I testid restano gli stessi
 * (le guardie seguono il dispositivo): cambia l'ordine e il copy.
 *
 * OTTO SEZIONI, copy in `opPro` (namespace prelaunch, solo italiano):
 *   1. HERO       il tuo spazio, pronto oggi     foto + offerta + CTA
 *   2. COSA HAI   gli strumenti, al presente     fascia foto + registro verde   (ol-go)
 *   3. PERCHE' ORA il patto fondatori            due colonne + contatore vero   (ol-now)
 *   4. COME SI ENTRA tre passi                   tre schede con foto            (ol-join)
 *   5. FAQ        sei domande                    <details>, una alla volta
 *   6. CHI SIAMO  i volti veri                   Valentina e Davide
 *   7. REGISTRAZIONE si comincia da te           #presentati, InlineSignupForm
 *   8. CHIUSURA   il tuo spazio e' pronto        ancora verde
 * La sezione «Per chi e' Aurya» (il no e il si') e' USCITA: respingeva
 * proprio l'operatore che vuole visibilita', cioe' quello che si iscrive.
 *
 * FONDI: dark(foto) → sabbia → FOTO A TUTTA LARGHEZZA → VERDE → crema
 * → sabbia → bianco → sabbia → crema → VERDE. Due sezioni adiacenti non
 * hanno mai lo stesso fondo; le due ancore verdi (2 e 8) non si toccano.
 *
 * IL CONTATORE DEI FONDATORI e' VERO: GET /public/fondatori (tetto,
 * rimasti, scadenza). Se la rete non risponde, la frase resta senza
 * numero: mai un contatore inventato.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import InlineSignupForm from './InlineSignupForm';
import {
  Section, DisplayTitle, TitleLine, Lede, EditorialCta, PhotoBand, PhotoSplit,
} from '../../components/editorial';

/** l'ancora del form: destinazione delle CTA interne e dei link che
    arrivano da fuori (/entra-nella-rete#presentati dalla home) */
const FORM_ANCHOR = '#presentati';

/** un profilo VERO da mostrare come prova: listino, recensioni, un
    evento in programma. E' la prova che nessun elenco puo' dare. */
const PROOF_PROFILE = '/o/selva-viva-di-olisticamente-silvia';

const HERO_PHOTO = '/media/hero-organizer.webp';
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';
const TOGETHER_PHOTO = '/media/prelaunch/r02.jpg';   // costruire insieme
const HORIZON_PHOTO = '/media/prelaunch/r05.jpg';    // il cairn: una pietra alla volta

/* Le tre schede della sezione «come si entra». DECORATIVE (alt=""). */
const CARD_PHOTOS = {
  '01': '/media/prelaunch/r03.jpg',  // una persona nel suo elemento
  '02': '/media/prelaunch/r08.jpg',  // le mani di chi cura, da vicino
  '03': '/media/prelaunch/r09.jpg',  // la pratica nello spazio di tutti
};

function OfferCard({ image, numeral, title, body }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white
                        ring-1 ring-[#1e2f28]/[0.07]
                        shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]">
      <div className="aspect-[3/2] w-full overflow-hidden bg-[#e8e2d4]">
        <img src={image} alt="" width="900" height="600" loading="lazy" decoding="async"
             className="h-full w-full object-cover" />
      </div>
      <div className="flex flex-1 flex-col p-7 sm:p-8">
        <p className="eyebrow mb-3">{numeral}</p>
        <h3 className="font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
          {title}
        </h3>
        <p className="mt-3 max-w-[52ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">
          {body}
        </p>
      </div>
    </article>
  );
}

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  const { t: tl } = useTranslation('landings');

  useSeoMeta({
    title: t('opPro.seoTitle', { defaultValue: 'Per operatori olistici: il tuo spazio professionale, pronto oggi | Aurya' }),
    description: t('opPro.seoDesc', { defaultValue: 'Profilo pubblico, servizi, prenotazioni, eventi e ritiri con iscrizioni online. Tutto in un unico posto, con un solo link da condividere. Gratis per sempre, senza commissioni.' }),
    canonicalPath: '/entra-nella-rete',
  });

  /* RB2 — il contatore vero dei fondatori. Senza risposta: nessun numero. */
  const [fondatori, setFondatori] = useState(null);
  useEffect(() => {
    api.get('/public/fondatori').then((r) => setFondatori(r.data)).catch(() => setFondatori(null));
  }, []);

  const prefersReducedMotion = () => typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('presentati')?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  /* Come si comincia: tre passi, tre schede. */
  const cards = [
    { numeral: '01',
      title: t('opPro.j1t', { defaultValue: 'Crea il tuo account.' }),
      body: t('opPro.j1b', { defaultValue: 'Nome, email e password. Un minuto. Nessuna carta.' }) },
    { numeral: '02',
      title: t('opPro.j2t', { defaultValue: 'Pubblica il tuo profilo.' }),
      body: t('opPro.j2b', { defaultValue: 'Aggiungi foto, storia e primo servizio. Sei online e hai già il tuo link da condividere.' }) },
    { numeral: '03',
      // founder 10/9 sera: niente attesa di una chiamata — il gruppo Telegram
      title: t('opPro.j3t', { defaultValue: 'Entra nel gruppo Telegram.' }),
      body: t('opPro.j3b', { defaultValue: 'Appena il profilo è online ti aggiungiamo al gruppo Telegram degli operatori Aurya: le novità, le richieste che arrivano, noi a un messaggio di distanza. Il racconto del tuo lavoro e il badge Verificato Aurya li costruiamo lì, quando vuoi tu.' }) },
  ];

  /* Tutto il tuo lavoro: sei schede, un verbo, una frase che resta.
     OF2: tutto al presente, solo cio' che il prodotto fa OGGI. */
  const voices = [1, 2, 3, 4, 5, 6].map((i) => ({
    title: t(`opPro.v${i}t`), body: t(`opPro.v${i}b`), key: t(`opPro.v${i}k`),
  }));

  /* Perche' entrare ora: quattro vantaggi da fondatore. */
  const patto = [1, 2, 3, 4].map((i) => ({
    title: t(`opPro.nowB${i}t`), body: t(`opPro.nowB${i}b`),
  }));

  /* Sei domande, risposte brevi e oneste, una alla volta (SR5). */
  const faq = [
    {
      q: t('opPro.faq1q', { defaultValue: 'Quanto costa?' }),
      a: (
        <ul className="list-disc space-y-2 pl-5">
          <li>{t('opPro.faq1b1', { defaultValue: 'L’utilizzo di Aurya è sempre gratuito, e Aurya non prende commissioni: quello che incassi è tuo.' })}</li>
          <li>{t('opPro.faq1b2', { defaultValue: 'Dal 2027 si paga solo la promozione, se la vuoi: la Spinta per un ritiro (19 €), il Club (49 € l’anno) o il Pro (119 € l’anno).' })}</li>
          <li>
            {t('opPro.faq1b3', { defaultValue: 'Gli operatori fondatori hanno il Club regalato fino al 30 giugno 2027 e il prezzo del Pro bloccato per sempre. ' })}
            <Link to="/costi" className="font-semibold text-primary underline underline-offset-2">
              {t('opPro.faq1b3cta', { defaultValue: 'Guarda i piani e i costi' })}
            </Link>
          </li>
        </ul>
      ),
    },
    { q: t('opPro.faq4q'), a: t('opPro.faq4a') },
    { q: t('opPro.faq3q'), a: t('opPro.faq3a2') },
    { q: t('opPro.faq5q'), a: t('opPro.faq5a2') },
    { q: t('opPro.faq6q'), a: t('opPro.faq6a') },
    { q: t('opPro.faq2q'), a: t('opPro.faq2a3') },
  ];

  const ctaOpen = t('opPro.ctaOpen', { defaultValue: 'Apri il tuo spazio' });
  const ctaJoin = t('opPro.ctaJoin', { defaultValue: 'Apri il tuo spazio' });
  const rimasti = fondatori && Number.isFinite(fondatori.rimasti) ? fondatori.rimasti : null;

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — il tuo spazio, pronto oggi ───────────────── */}
        <section data-testid="ol-hero" aria-labelledby="ol-hero-title">
          <div className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
            <img src={HERO_PHOTO} alt="" width="1920" height="1280" fetchPriority="high" decoding="async"
                 className="absolute inset-0 h-full w-full object-cover object-[50%_38%]
                            lg:left-auto lg:right-0 lg:w-[46%] lg:object-[38%_45%]" />
            <div aria-hidden className="absolute inset-0 bg-gradient-to-b from-[#0e1a15]/[0.78] via-[#0e1a15]/[0.62] to-[#0e1a15]/[0.90] lg:hidden" />
            <div aria-hidden className="absolute inset-0 bg-[radial-gradient(ellipse_92%_74%_at_36%_50%,rgba(14,26,21,0.52)_0%,rgba(14,26,21,0.34)_58%,rgba(14,26,21,0)_100%)] lg:hidden" />
            <div aria-hidden className="hidden lg:block absolute inset-y-0 left-[54%] w-44 bg-gradient-to-r from-[#0e1a15] to-transparent" />
            <div className="relative mx-auto w-full max-w-5xl px-6 py-16 sm:px-8 sm:py-24
                            lg:flex lg:min-h-[38rem] lg:flex-col lg:justify-center lg:py-24">
              <div className="lg:max-w-[30rem]">
                {/* founder 10/9 sera: l'occhiello era troppo piccolo — ora e' una
                    riga in oro, leggibile, che dice a chi parla la pagina */}
                <p className="mb-5 text-lg font-semibold uppercase tracking-[0.16em] text-[#d6c49a] text-hero-shadow sm:text-xl"
                   data-testid="ol-hero-eyebrow">
                  {t('opPro.heroEyebrow', { defaultValue: 'Per operatori e operatrici olistiche' })}
                </p>
                <DisplayTitle as="h1" id="ol-hero-title" size="heroLines" measure="lines" className="text-hero-shadow">
                  {t('opPro.heroTitle', { defaultValue: 'Il tuo spazio professionale, pronto oggi.' })}
                </DisplayTitle>
                <div className="mt-7 space-y-4 sm:mt-9 sm:space-y-5">
                  <Lede size="body" tone="inherit" className="text-hero-shadow font-semibold">
                    {t('opPro.heroP1')}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP2')}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow font-semibold">
                    {t('opPro.heroP3', { defaultValue: 'Gratis per sempre, senza commissioni.' })}
                  </Lede>
                </div>
                <div className="mt-9 sm:mt-10">
                  <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} tone="dark" variant="solid"
                                data-testid="ol-hero-cta-top">
                    {ctaOpen}
                  </EditorialCta>
                  <p className="mt-3 text-sm opacity-80 text-hero-shadow">
                    {t('opPro.heroNote', { defaultValue: 'Un minuto per registrarti. Nessuna carta.' })}
                  </p>
                </div>
              </div>
            </div>
          </div>
          {/* la prova, sul chiaro: un profilo VERO vale piu' di ogni promessa */}
          <Section tone="sand" rhythm="flow" width="max-w-5xl">
            <DisplayTitle as="p" size="section" measure="lines"
                          className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.3rem]">
              {t('opPro.heroP4')}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">{t('opPro.heroP5')}</Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-hero-cta">
                {ctaOpen}
              </EditorialCta>
              <EditorialCta to={PROOF_PROFILE} variant="quiet" data-testid="ol-hero-cta-alt">
                {t('opPro.ctaProof', { defaultValue: 'Guarda un profilo vero' })}
              </EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 2. TUTTO IL TUO LAVORO — sei schede, un verbo, una frase ──
            Bianco su crema: si legge a colpo d'occhio, niente registro
            da studiare. Il grassetto e' il vantaggio, non la funzione. */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-go-title" width="max-w-6xl">
          <div id="sound" data-testid="ol-go">
            <DisplayTitle as="h2" id="ol-go-title" size="section" measure="title">
              {t('opPro.goTitle')}
            </DisplayTitle>
            <ul className="mt-10 grid list-none gap-6 p-0 sm:mt-12 sm:grid-cols-2 lg:grid-cols-3">
              {voices.map((v) => (
                <li key={v.title}
                    className="flex h-full flex-col rounded-[1.75rem] bg-white p-7 ring-1 ring-[#1e2f28]/[0.07]
                               shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]">
                  <h3 className="font-display text-[1.45rem] leading-tight text-foreground sm:text-2xl">{v.title}</h3>
                  <p className="mt-3 text-[0.975rem] leading-relaxed text-foreground/75">{v.body}</p>
                  <p className="mt-auto pt-5 text-[0.975rem] font-semibold leading-snug text-[#2f5749]">{v.key}</p>
                </li>
              ))}
            </ul>
            {/* SP3 — Aurya Sound e' uno strumento gia' vero */}
            <Lede size="body" className="mt-10 max-w-[70ch]">
              {t('opPro.goSoon')}{' '}
              <Link to="/sound/studio" data-testid="ol-voice-studio"
                    className="font-semibold text-[#2f5749] underline underline-offset-4">
                {t('opPro.goSoonCta', { defaultValue: 'Scopri Crea Studio' })} →
              </Link>
            </Lede>
            <div className="mt-9">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-go-cta">
                {ctaOpen}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 2b. QUANTO COSTA — in alto, in chiaro (founder 10/9 sera):
            il base e' per sempre e tutto gratuito, si paga solo il piu'. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-prezzi-title" width="max-w-5xl">
          <div data-testid="ol-prezzi">
            <DisplayTitle as="h2" id="ol-prezzi-title" size="section" measure="title">
              {t('opPro.prezziTitle', { defaultValue: 'Quanto costa.' })}
            </DisplayTitle>
            <p className="mt-6 font-display text-[1.6rem] leading-tight text-[#2f5749] sm:text-[2rem]">
              {t('opPro.prezziP1', { defaultValue: 'Gratis per sempre, senza commissioni.' })}
            </p>
            <Lede size="lead" className="mt-4 max-w-[62ch]">
              {t('opPro.prezziP2', { defaultValue: 'Tutto quello che hai letto sopra è il piano base: non scade, non ha limiti nascosti e non prende una percentuale su quello che incassi. Si paga solo il più, se lo vuoi, dal 2027.' })}
            </Lede>
            <ul className="mt-8 grid list-none gap-4 p-0 sm:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <li key={i} className="rounded-2xl bg-white p-5 ring-1 ring-[#1e2f28]/[0.07]" data-testid={`ol-prezzi-${i}`}>
                  <p className="font-display text-[1.2rem] leading-tight text-foreground">{t(`opPro.prezzi${i}t`)}</p>
                  <p className="mt-2 text-sm leading-relaxed text-foreground/75">{t(`opPro.prezzi${i}b`)}</p>
                </li>
              ))}
            </ul>
            <div className="mt-7">
              <EditorialCta to="/costi" variant="quiet" data-testid="ol-prezzi-cta">
                {t('opPro.prezziCta', { defaultValue: 'Tutti i piani, riga per riga' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 3. LA RETE — il profilo non vive da solo ─────────────── */}
        <section data-testid="ol-rete" aria-labelledby="ol-rete-title">
          <PhotoBand as="div" image={HORIZON_PHOTO} focus="50% 40%" width="max-w-3xl">
            <DisplayTitle as="h2" id="ol-rete-title" size="section" measure="title" className="text-hero-shadow">
              {t('opPro.reteTitle')}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7 text-hero-shadow">{t('opPro.reteP1')}</Lede>
            <Lede size="lead" tone="inherit" className="mt-3 text-hero-shadow font-semibold">{t('opPro.reteP2')}</Lede>
            <Lede size="body" tone="inherit" className="mt-4 text-hero-shadow">{t('opPro.reteP3')}</Lede>
            <div className="mt-8">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" tone="dark" data-testid="ol-rete-cta">
                {ctaOpen}
              </EditorialCta>
            </div>
          </PhotoBand>
        </section>

        {/* ── 4. PERCHE' ENTRARE ORA — il patto fondatori ───────────
            Un tetto, una data, un contatore vero, quattro schede. */}
        <PhotoSplit image={TOGETHER_PHOTO} side="left" tone="sand" focus="50% 45%"
                    imageWidth="900" imageHeight="599" labelledBy="ol-now-title" data-testid="ol-now">
          <DisplayTitle as="h2" id="ol-now-title" size="section" measure="title">
            {t('opPro.nowTitle')}
          </DisplayTitle>
          <Lede size="lead" className="mt-7">{t('opPro.nowP1')}</Lede>
          <ul className="mt-8 grid list-none gap-4 p-0 sm:grid-cols-2" data-testid="ol-now-patto">
            {patto.map((b) => (
              <li key={b.title} className="rounded-2xl bg-white/80 p-5 ring-1 ring-[#1e2f28]/[0.07]">
                <p className="font-display text-[1.2rem] leading-tight text-foreground">{b.title}</p>
                <p className="mt-2 text-sm font-semibold leading-snug text-[#2f5749]">{b.body}</p>
              </li>
            ))}
          </ul>
          <p className="mt-7 font-display text-[1.35rem] leading-snug text-foreground sm:text-[1.6rem]"
             data-testid="ol-fondatori-contatore">
            {rimasti !== null
              ? t('opPro.nowCount', { defaultValue: '{{rimasti}} posti su {{tetto}} ancora disponibili.', rimasti, tetto: fondatori.tetto })
              : t('opPro.nowCountFallback', { defaultValue: 'Venti posti, poi la parola fondatori sparisce da questa pagina.' })}
          </p>
          <p className="mt-6 max-w-[52ch] text-base font-semibold leading-relaxed text-foreground">
            {t('opPro.nowCloseA2')} {t('opPro.nowCloseB2')}
          </p>
          <div className="mt-8">
            <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-now-cta">
              {t('opPro.nowCta', { defaultValue: 'Diventa operatore fondatore' })}
            </EditorialCta>
          </div>
        </PhotoSplit>

        {/* ── 5. COME SI COMINCIA — tre passi, tre schede ──────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-join-title" width="max-w-6xl">
          <div data-testid="ol-join">
            <DisplayTitle as="h2" id="ol-join-title" size="section" measure="title">
              {t('opPro.joinTitle')}
            </DisplayTitle>
            <ul className="mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-3">
              {cards.map((c) => (
                <li key={c.numeral} data-testid={`ol-card-${c.numeral}`} className="h-full">
                  <OfferCard image={CARD_PHOTOS[c.numeral]} numeral={c.numeral} title={c.title} body={c.body} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 6. DOMANDE — una alla volta (SR5) ──────────────────── */}
        <Section tone="paper" rhythm="screen" labelledBy="ol-faq-title" width="max-w-3xl">
          <div data-testid="ol-faq">
            <DisplayTitle as="h2" id="ol-faq-title" size="section" measure="title">
              {t('opPro.faqTitle', { defaultValue: 'Domande frequenti.' })}
            </DisplayTitle>
            <div className="mt-10 sm:mt-12" data-testid="ol-faq-list">
              {faq.map((f, i) => (
                <details key={f.q} className={`group py-5 ${i > 0 ? 'border-t border-[#1e2f28]/[0.10]' : 'pt-0'}`}>
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-4
                                      font-display text-[1.2rem] leading-snug text-foreground sm:text-[1.4rem]
                                      [&::-webkit-details-marker]:hidden">
                    <span>{f.q}</span>
                    <span aria-hidden className="mt-1 shrink-0 text-[#8a7440] transition-transform group-open:rotate-45">+</span>
                  </summary>
                  <div className="mt-3 max-w-[62ch] text-base leading-relaxed text-foreground/75 sm:text-lg">{f.a}</div>
                </details>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 7. CHI C'E' DIETRO AURYA — i volti veri ──────────────── */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-who-title" width="max-w-6xl">
          <div data-testid="ol-who">
            <p className="eyebrow mb-5">{t('opPro.whoEyebrow', { defaultValue: 'Chi c’è dietro Aurya' })}</p>
            <DisplayTitle as="h2" id="ol-who-title" size="section" measure="lines"
                          className="text-[1.9rem] leading-[1.14] sm:text-[2.4rem] lg:text-[2.9rem]">
              <TitleLine>{t('opPro.whoLine1', { defaultValue: 'Pratiche, eventi e ritiri' })}</TitleLine>
              <TitleLine>{t('opPro.whoLine2', { defaultValue: 'di benessere' })}</TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-7">{t('opPro.whoLead')}</Lede>
            <div className="mt-12 grid gap-9 sm:mt-14 lg:grid-cols-12 lg:items-center lg:gap-14">
              <div className="lg:col-span-5">
                <img src={FOUNDERS_PHOTO}
                     alt={tl('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
                     width="900" height="1125" loading="lazy" decoding="async"
                     className="aspect-[4/5] w-full rounded-[1.75rem] object-cover shadow-[0_18px_48px_-28px_rgba(30,47,40,0.45)]" />
              </div>
              <div className="lg:col-span-7">
                <p className="font-display text-[1.5rem] leading-snug text-foreground sm:text-[1.85rem]">
                  <span className="block">{t('opPro.whoV')}</span>
                  <span className="mt-3 block">{t('opPro.whoD')}</span>
                </p>
                <Lede size="body" className="mt-6">{t('opPro.whoP')}</Lede>
                <div className="mt-8">
                  <EditorialCta to="/chi-siamo" variant="quiet" data-testid="ol-who-cta">
                    {t('opPro.whoCta', { defaultValue: 'Conosci la nostra storia' })}
                  </EditorialCta>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 8. LA REGISTRAZIONE — si comincia da te ──────────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-form-title" width="max-w-6xl"
                 id="presentati" className="scroll-mt-20">
          <div data-testid="ol-form" className="grid gap-10 lg:grid-cols-12 lg:items-start lg:gap-16">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                            className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.6rem]">
                {t('opPro.formTitle2', { defaultValue: 'Si comincia da te.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7 font-semibold">{t('opPro.formA3')}</Lede>
              <Lede size="body" className="mt-5">{t('opPro.formC3')}</Lede>
              <Lede size="body" className="mt-3">{t('opPro.formD3')}</Lede>
              <p className="mt-8 flex flex-wrap items-center gap-1.5 text-sm text-foreground/70">
                <Mail className="h-4 w-4 shrink-0 text-[#2f5749]" aria-hidden />
                {t('op.directT', { defaultValue: 'Preferisci parlarne senza form?' })}{' '}
                <a href="mailto:info@aurya.life"
                   className="font-medium text-[#2f5749] underline underline-offset-[4px] decoration-[#2f5749]/40 hover:decoration-[#2f5749]">
                  info@aurya.life
                </a>
              </p>
            </div>
            <div className="lg:col-span-7">
              <div className="rounded-[1.75rem] bg-white p-6 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
                <InlineSignupForm />
              </div>
            </div>
          </div>
        </Section>

        {/* ── 9. CHIUSURA — l'ancora verde ─────────────────────────── */}
        <Section tone="sage" rhythm="screen" labelledBy="ol-end-title" width="max-w-5xl">
          <div data-testid="ol-end">
            <DisplayTitle as="h2" id="ol-end-title" size="section" measure="lines">
              <TitleLine>{t('opPro.endA')}</TitleLine>
              <TitleLine>{t('opPro.endB')}</TitleLine>
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7">
              <span className="block">{t('opPro.endC2')}</span>
              <span className="block">{t('opPro.endD2')}</span>
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">{t('opPro.endBody2')}</Lede>
            <div className="mt-9">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" tone="dark" data-testid="ol-end-cta">
                {ctaJoin}
              </EditorialCta>
            </div>
          </div>
        </Section>
      </div>
    </MarketplaceShell>
  );
}
