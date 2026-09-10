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
 *   1. HERO       il tuo spazio, pronto oggi     foto + offerta + CTA + la prova
 *   2. COSA HAI   sei schede                     (ol-go)
 *   3. CREA STUDIO le tue meditazioni            (ol-studio)
 *   4. PERCHE' ORA il patto fondatori            schede + contatore vero (ol-now)
 *   5. QUANTO COSTA base gratis, il piu' dal 2027 (ol-prezzi)
 *   6. COME SI COMINCIA tre passi                tre schede con foto (ol-join)
 *   7. FAQ        sei domande                    <details>, una alla volta
 *   8. REGISTRAZIONE si comincia da te           #presentati, InlineSignupForm:
 *                                               E' LA CHIUSURA.
 * La sezione «Per chi e' Aurya» (il no e il si') e' USCITA: respingeva
 * proprio l'operatore che vuole visibilita', cioe' quello che si iscrive.
 * CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili logici e
 * storytelling»): sono uscite anche la fascia «E il tuo profilo puo'
 * essere scoperto anche su Aurya» (ripeteva la scheda «Ti possono
 * trovare» e la voce del patto), «Chi c'e' dietro Aurya» (la foto e le
 * due righe di /chi-siamo, che ora e' un filo di una riga nel modulo) e
 * la chiusura verde «Il tuo lavoro merita un posto tutto suo» (l'hero
 * parola per parola, col bottone che riportava al modulo di un
 * centimetro sopra). Da 1.471 a ~1.050 parole, stessi argomenti.
 *
 * FONDI: dark(foto) → sabbia → crema → sabbia → crema → sabbia → crema
 * → bianco → sabbia. Due sezioni adiacenti non hanno mai lo stesso fondo.
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
  Section, DisplayTitle, Lede, EditorialCta,
} from '../../components/editorial';

/** l'ancora del form: destinazione delle CTA interne e dei link che
    arrivano da fuori (/entra-nella-rete#presentati dalla home) */
const FORM_ANCHOR = '#presentati';

/** la prova (founder 10/9 sera): la directory con TUTTI gli operatori
    gia' dentro, non un profilo solo. */
const PROOF_PROFILE = '/operatori';

const HERO_PHOTO = '/media/hero-organizer.webp';

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

  useSeoMeta({
    title: t('opPro.seoTitle', { defaultValue: "Per operatori olistici: il tuo spazio professionale, pronto oggi | Aurya" }),
    description: t('opPro.seoDesc', { defaultValue: "Una pagina tutta tua per presentarti, mostrare i tuoi servizi, ricevere prenotazioni e organizzare eventi e ritiri. Un solo link da condividere. Gratis per sempre, senza commissioni." }),
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

  /* Tutto quello che ti serve: sei schede, un verbo, una frase che resta. */
  const voices = [
    { title: t('opPro.v1t', { defaultValue: "Racconti chi sei." }),
      body: t('opPro.v1b', { defaultValue: "Crea la tua pagina professionale con la tua foto, la tua storia, le pratiche che proponi, i tuoi servizi e le recensioni dei tuoi clienti." }),
      key: t('opPro.v1k', { defaultValue: "Chi arriva sulla tua pagina capisce subito chi sei e cosa offri." }) },
    { title: t('opPro.v2t', { defaultValue: "Ti possono trovare." }),
      body: t('opPro.v2b', { defaultValue: "Il tuo profilo è pubblico e può essere trovato anche su Google. Inoltre, puoi comparire nella directory di Aurya, dove le persone cercano operatori, pratiche, eventi e ritiri." }),
      key: t('opPro.v2k', { defaultValue: "Non devi essere tu a portare ogni persona sulla tua pagina." }) },
    { title: t('opPro.v3t', { defaultValue: "Ricevi prenotazioni." }),
      body: t('opPro.v3b', { defaultValue: "Pubblica i tuoi servizi con prezzo e disponibilità. Chi è interessato può chiederti un appuntamento direttamente dalla tua pagina. Il calendario ti mostra gli appuntamenti già fissati, così sai sempre quando sei disponibile." }),
      key: t('opPro.v3k', { defaultValue: "Meno messaggi per organizzare gli appuntamenti." }) },
    { title: t('opPro.v4t', { defaultValue: "Organizzi i tuoi eventi e ritiri." }),
      body: t('opPro.v4b', { defaultValue: "Crea la pagina del tuo evento o del tuo ritiro con data, luogo, descrizione, prezzo e posti disponibili. Le persone possono iscriversi online e pagare la caparra. Tu vedi in un unico posto chi si è iscritto e quanto ha già pagato." }),
      key: t('opPro.v4k', { defaultValue: "Tu organizzi l’esperienza. Aurya ti aiuta a gestire le iscrizioni." }) },
    { title: t('opPro.v5t', { defaultValue: "Hai un solo link da condividere." }),
      body: t('opPro.v5b', { defaultValue: "Mettilo nella bio di Instagram, su WhatsApp o invialo direttamente ai tuoi clienti. Dentro trovano la tua storia, i tuoi servizi, gli eventi, i ritiri e le recensioni." }),
      key: t('opPro.v5k', { defaultValue: "Un solo link al posto di tanti link diversi." }) },
    { title: t('opPro.v6t', { defaultValue: "Tieni tutto sotto controllo." }),
      body: t('opPro.v6b', { defaultValue: "Clienti, prenotazioni, ordini e incassi in un unico posto." }),
      key: t('opPro.v6k', { defaultValue: "Meno fogli, meno messaggi e meno cose da ricordare." }) },
  ];
  /* Perche' entrare ora: quattro vantaggi da fondatore. */
  const patto = [
    { title: t('opPro.nowB1t', { defaultValue: "Club Fondatori" }),
      body: t('opPro.nowB1b', { defaultValue: "Gratuito fino al 30 giugno 2027. Il tuo ritiro viene messo in evidenza e puoi essere presente nella Lettera di Aurya dedicata alla tua zona." }) },
    { title: t('opPro.nowB2t', { defaultValue: "Badge Fondatore" }),
      body: t('opPro.nowB2b', { defaultValue: "Resta per sempre sul tuo profilo." }) },
    { title: t('opPro.nowB3t', { defaultValue: "Prezzo Pro bloccato" }),
      body: t('opPro.nowB3b', { defaultValue: "Se in futuro scegli il piano Pro, mantieni per sempre il prezzo riservato ai fondatori." }) },
    { title: t('opPro.nowB4t', { defaultValue: "Opportunità dalla rete" }),
      body: t('opPro.nowB4b', { defaultValue: "I fondatori saranno tra i primi operatori contattati quando nasceranno richieste per team building, ritiri aziendali ed esperienze di gruppo." }) },
  ];
  /* Quanto costa: il base per sempre, il piu' dal 2027. */
  const prezzi = [
    { title: t('opPro.prezzi1t', { defaultValue: "Spinta · 19 € per ritiro" }),
      body: t('opPro.prezzi1b', { defaultValue: "Metti il tuo ritiro in evidenza nella sezione Ritiri ed esperienze e nella Lettera di Aurya dedicata alla sua zona." }) },
    { title: t('opPro.prezzi2t', { defaultValue: "Club · 49 € l’anno" }),
      body: t('opPro.prezzi2b', { defaultValue: "Metti in evidenza tutti i tuoi ritiri, compari nella Lettera della tua zona e hai priorità nelle opportunità che arrivano dalla rete." }) },
    { title: t('opPro.prezzi3t', { defaultValue: "Pro · 119 € l’anno" }),
      body: t('opPro.prezzi3b', { defaultValue: "Tutto quello che offre il Club, più Crea Studio e assistenza diretta su WhatsApp." }) },
  ];
  /* Come si comincia: tre passi, tre schede. */
  const cards = [
    { numeral: '01', title: t('opPro.j1t', { defaultValue: "Crei il tuo account." }), body: t('opPro.j1b', { defaultValue: "Inserisci nome, email e password. Ci metti circa un minuto. Non serve la carta." }) },
    { numeral: '02', title: t('opPro.j2t', { defaultValue: "Crei la tua pagina." }), body: t('opPro.j2b', { defaultValue: "Aggiungi una foto, racconta chi sei e inserisci il tuo primo servizio. La tua pagina è online e puoi subito condividere il link." }) },
    { numeral: '03', title: t('opPro.j3t', { defaultValue: "Entri nella rete." }), body: t('opPro.j3b', { defaultValue: "Quando il tuo profilo è online, entri nel gruppo Telegram degli operatori Aurya. Lì trovi le novità, le richieste che arrivano e puoi parlare direttamente con noi. Se vuoi, ti aiutiamo anche a raccontare il tuo lavoro su Aurya e a ottenere il badge Verificato Aurya." }) },
  ];
  /* Sei domande, risposte brevi e oneste, una alla volta (SR5). */
  const faq = [
    {
      q: t('opPro.faq1q', { defaultValue: "Quanto costa?" }),
      a: (
        <ul className="list-disc space-y-2 pl-5">
          <li>{t('opPro.faq1b1', { defaultValue: "Il piano base è sempre gratuito e senza commissioni: Aurya non prende commissioni su quello che guadagni." })}</li>
          <li>{t('opPro.faq1b2', { defaultValue: "Dal 2027 puoi scegliere di aggiungere servizi a pagamento, ma non sei obbligato: la Spinta per un ritiro (19 €), il Club (49 € l’anno) o il Pro (119 € l’anno)." })}</li>
          <li>
            {t('opPro.faq1b3', { defaultValue: "Tutti i piani, riga per riga: " })}
            <Link to="/costi" className="font-semibold text-primary underline underline-offset-2">
              {t('opPro.faq1b3cta', { defaultValue: "scopri i piani e i costi" })}
            </Link>
          </li>
        </ul>
      ),
    },
    { q: t('opPro.faq4q', { defaultValue: "Posso usare Aurya anche se ho già un sito?" }), a: t('opPro.faq4a', { defaultValue: "Sì. Puoi continuare a usare il tuo sito e usare Aurya per presentare i tuoi servizi, ricevere prenotazioni e gestire eventi e ritiri." }) },
    { q: t('opPro.faq3q', { defaultValue: "Posso continuare a usare Instagram?" }), a: t('opPro.faq3a2', { defaultValue: "Certo. Puoi mettere il tuo link Aurya nella bio di Instagram e portare le persone direttamente alla tua pagina, ai tuoi servizi e alle tue esperienze." }) },
    { q: t('opPro.faq5q', { defaultValue: "Posso continuare a ricevere prenotazioni da WhatsApp o telefono?" }), a: t('opPro.faq5a2', { defaultValue: "Sì. Puoi continuare a usare i tuoi canali abituali e inserire manualmente le prenotazioni nel tuo calendario Aurya." }) },
    { q: t('opPro.faq2q', { defaultValue: "Le persone possono trovare il mio profilo anche se non mi conoscono?" }), a: t('opPro.faq2a3', { defaultValue: "Sì. Il tuo profilo è pubblico, può essere trovato su Google e può comparire nella directory di Aurya." }) },
    { q: t('opPro.faq6q', { defaultValue: "Posso smettere di usare Aurya quando voglio?" }), a: t('opPro.faq6a', { defaultValue: "Sì. Non ci sono vincoli." }) },
  ];

  const ctaOpen = t('opPro.ctaOpen', { defaultValue: "Apri il tuo spazio" });
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
                {/* founder 10/9 sera: l'occhiello grande, nell'oro di casa */}
                <p className="mb-5 text-lg font-semibold uppercase tracking-[0.16em] text-[#d6c49a] text-hero-shadow sm:text-xl"
                   data-testid="ol-hero-eyebrow">
                  {t('opPro.heroEyebrow', { defaultValue: "Per operatori e operatrici olistiche" })}
                </p>
                <DisplayTitle as="h1" id="ol-hero-title" size="heroLines" measure="lines" className="text-hero-shadow">
                  {t('opPro.heroTitle', { defaultValue: "Il tuo spazio professionale, pronto oggi." })}
                </DisplayTitle>
                <div className="mt-7 space-y-4 sm:mt-9 sm:space-y-5">
                  <Lede size="body" tone="inherit" className="text-hero-shadow font-semibold">{t('opPro.heroP1', { defaultValue: "Una pagina tutta tua per presentarti, mostrare i tuoi servizi, ricevere prenotazioni e organizzare eventi e ritiri." })}</Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">{t('opPro.heroP2', { defaultValue: "Condividi un solo link su Instagram, WhatsApp o dove vuoi." })}</Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow font-semibold">{t('opPro.heroP3', { defaultValue: "Gratis per sempre, senza commissioni." })}</Lede>
                </div>
                <div className="mt-9 sm:mt-10">
                  <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" tone="dark" data-testid="ol-hero-cta-top">{ctaOpen}</EditorialCta>
                  <p className="mt-3 text-sm opacity-80 text-hero-shadow">{t('opPro.heroNote', { defaultValue: "Un minuto per registrarti. Nessuna carta." })}</p>
                </div>
              </div>
            </div>
          </div>
          {/* la prova, sul chiaro: un profilo VERO vale piu' di ogni promessa */}
          <Section tone="sand" rhythm="flow" width="max-w-5xl">
            <DisplayTitle as="p" size="section" measure="lines"
                          className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.3rem]">
              {t('opPro.heroP4', { defaultValue: "È già disponibile." })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">{t('opPro.heroP5', { defaultValue: "Guarda i profili degli operatori già dentro: servizi, recensioni e ritiri in programma, tutto sulla stessa pagina." })}</Lede>
            {/* founder 10/9 sera: UN bottone pieno (apri il tuo spazio), la prova
                come voce discreta verso la directory di tutti gli operatori */}
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              {/* su telefono prima la prova (viene prima nel testo), poi il bottone;
                  da sm il bottone pieno resta a sinistra */}
              <EditorialCta to={PROOF_PROFILE} variant="quiet" data-testid="ol-hero-cta-alt"
                            className="order-1 sm:order-2">
                {t('opPro.ctaProof', { defaultValue: "Guarda i profili degli operatori" })}
              </EditorialCta>
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-hero-cta"
                            className="order-2 sm:order-1">{ctaOpen}</EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 2. TUTTO QUELLO CHE TI SERVE — sei schede ─────────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-go-title" width="max-w-6xl">
          <div id="sound" data-testid="ol-go">
            <DisplayTitle as="h2" id="ol-go-title" size="section" measure="title">{t('opPro.goTitle', { defaultValue: "Tutto quello che ti serve, in un unico posto." })}</DisplayTitle>
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
          </div>
        </Section>

        {/* ── 3. CREA STUDIO — le tue meditazioni (SP3: strumento vero) ── */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-studio-title" width="max-w-5xl">
          <div data-testid="ol-studio">
            <DisplayTitle as="h2" id="ol-studio-title" size="section" measure="title">{t('opPro.studioTitle', { defaultValue: "Crea anche le tue meditazioni." })}</DisplayTitle>
            <p className="mt-6 font-display text-[1.35rem] leading-snug text-foreground sm:text-[1.6rem]">{t('opPro.studioSub', { defaultValue: "Crea Studio, il tuo spazio per creare meditazioni." })}</p>
            <Lede size="lead" className="mt-4 max-w-[62ch]">{t('opPro.goSoon', { defaultValue: "Puoi unire musica, frequenze e la tua voce per creare una meditazione personalizzata e condividerla con un link." })}</Lede>
            <div className="mt-8 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <Link to="/sound/studio" data-testid="ol-voice-studio"
                    className="font-semibold text-[#2f5749] underline underline-offset-4">
                {t('opPro.goSoonCta', { defaultValue: "Scopri Crea Studio" })} →
              </Link>
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-go-cta">{ctaOpen}</EditorialCta>
            </div>
          </div>
        </Section>

        {/* CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili
            logici e storytelling»): qui c'era la fascia «E il tuo profilo
            puo' essere scoperto anche su Aurya» (ol-rete). Diceva la
            scheda «Ti possono trovare» (sopra) e la voce «Opportunita'
            dalla rete» del patto (sotto), con una foto in mezzo. Via. */}

        {/* ── 4. PERCHE' ENTRARE ORA — il patto fondatori ──────────── */}
        {/* founder 10/9 sera: via la foto a fianco («sembra finita li' per caso»):
            solo testo e schede */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-now-title" width="max-w-5xl">
         <div data-testid="ol-now">
          <DisplayTitle as="h2" id="ol-now-title" size="section" measure="title">{t('opPro.nowTitle', { defaultValue: "Perché entrare ora." })}</DisplayTitle>
          <Lede size="lead" className="mt-7">{t('opPro.nowP1', { defaultValue: "I primi 20 operatori che pubblicano il proprio profilo entro il 31 ottobre 2026 entrano come operatori fondatori di Aurya." })}</Lede>
          <ul className="mt-8 grid list-none gap-4 p-0 sm:grid-cols-2" data-testid="ol-now-patto">
            {patto.map((b) => (
              <li key={b.title} className="rounded-2xl bg-white/80 p-5 ring-1 ring-[#1e2f28]/[0.07]">
                <p className="font-display text-[1.2rem] leading-tight text-foreground">{b.title}</p>
                <p className="mt-2 text-sm leading-snug text-foreground/80">{b.body}</p>
              </li>
            ))}
          </ul>
          <p className="mt-7 font-display text-[1.35rem] leading-snug text-foreground sm:text-[1.6rem]"
             data-testid="ol-fondatori-contatore">
            {rimasti !== null
              ? t('opPro.nowCount', { defaultValue: '{{rimasti}} posti su {{tetto}} ancora disponibili.', rimasti, tetto: fondatori.tetto })
              : t('opPro.nowCountFallback', { defaultValue: "Venti posti, poi la parola fondatori sparisce da questa pagina." })}
          </p>
          <p className="mt-6 max-w-[52ch] text-base font-semibold leading-relaxed text-foreground">
            {t('opPro.nowCloseA2', { defaultValue: "Non cerchiamo semplicemente iscritti." })}{' '}
            {t('opPro.nowCloseB2', { defaultValue: "Cerchiamo i primi operatori con cui costruire la rete di Aurya." })}
          </p>
          <div className="mt-8"><EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" data-testid="ol-now-cta">{t('opPro.nowCta', { defaultValue: "Diventa operatore fondatore" })}</EditorialCta></div>
         </div>
        </Section>

        {/* ── 6. QUANTO COSTA — il base per sempre, il piu' dal 2027 ─── */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-prezzi-title" width="max-w-5xl">
          <div data-testid="ol-prezzi">
            <DisplayTitle as="h2" id="ol-prezzi-title" size="section" measure="title">{t('opPro.prezziTitle', { defaultValue: "Quanto costa." })}</DisplayTitle>
            <p className="mt-6 font-display text-[1.6rem] leading-tight text-[#2f5749] sm:text-[2rem]">{t('opPro.prezziP1', { defaultValue: "Il piano base è gratuito per sempre." })}</p>
            <p className="mt-3 text-lg font-semibold leading-snug text-foreground">{t('opPro.prezziP2', { defaultValue: "Non paghi un abbonamento e non paghi commissioni su quello che guadagni." })}</p>
            <Lede size="lead" className="mt-4 max-w-[62ch]">{t('opPro.prezziP3', { defaultValue: "Tutto quello che hai visto sopra è incluso nel piano base. Dal 2027 puoi scegliere di aggiungere servizi a pagamento, solo se ti servono." })}</Lede>
            <ul className="mt-8 grid list-none gap-4 p-0 sm:grid-cols-3">
              {prezzi.map((x, i) => (
                <li key={x.title} className="rounded-2xl bg-white p-5 ring-1 ring-[#1e2f28]/[0.07]" data-testid={`ol-prezzi-${i + 1}`}>
                  <p className="font-display text-[1.2rem] leading-tight text-foreground">{x.title}</p>
                  <p className="mt-2 text-sm leading-relaxed text-foreground/75">{x.body}</p>
                </li>
              ))}
            </ul>
            <div className="mt-7">
              <EditorialCta to="/costi" variant="quiet" data-testid="ol-prezzi-cta">{t('opPro.prezziCta', { defaultValue: "Scopri tutti i piani" })}</EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. COME SI COMINCIA — tre passi, tre schede ──────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-join-title" width="max-w-6xl">
          <div data-testid="ol-join">
            <DisplayTitle as="h2" id="ol-join-title" size="section" measure="title">{t('opPro.joinTitle', { defaultValue: "Come si comincia." })}</DisplayTitle>
            <ul className="mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-3">
              {cards.map((c) => (
                <li key={c.numeral} data-testid={`ol-card-${c.numeral}`} className="h-full">
                  <OfferCard image={CARD_PHOTOS[c.numeral]} numeral={c.numeral} title={c.title} body={c.body} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 8. DOMANDE — una alla volta (SR5) ──────────────────── */}
        <Section tone="paper" rhythm="screen" labelledBy="ol-faq-title" width="max-w-3xl">
          <div data-testid="ol-faq">
            <DisplayTitle as="h2" id="ol-faq-title" size="section" measure="title">{t('opPro.faqTitle', { defaultValue: "Domande frequenti." })}</DisplayTitle>
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

        {/* CP (10/9 notte): qui c'era «Chi c'e' dietro Aurya» (ol-who), la
            stessa foto e le stesse due righe di /chi-siamo. La fiducia
            resta come filo, in una riga dentro la registrazione. */}

        {/* ── 8. LA REGISTRAZIONE — si comincia da te. E' la chiusura:
               la pagina finisce sull'azione, non su un'altra ancora. ── */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-form-title" width="max-w-6xl"
                 id="presentati" className="scroll-mt-20">
          <div data-testid="ol-form" className="grid gap-10 lg:grid-cols-12 lg:items-start lg:gap-16">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                            className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.6rem]">
                {t('opPro.formTitle2', { defaultValue: "Si comincia da te." })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7 font-semibold">{t('opPro.formA3', { defaultValue: "Crea il tuo account in un minuto e pubblica la tua pagina." })}</Lede>
              <Lede size="body" className="mt-5">{t('opPro.formC3', { defaultValue: "Quando sei online, entri nella rete degli operatori Aurya." })}</Lede>
              <Lede size="body" className="mt-3">{t('opPro.formD3', { defaultValue: "E se vuoi, possiamo aiutarti a raccontare meglio il tuo lavoro." })}</Lede>
              {/* il filo della fiducia: chi c'e' dietro, in una riga */}
              <p className="mt-6 text-sm text-foreground/70">
                {t('opPro.formWho', { defaultValue: 'Dietro Aurya ci siamo noi, Valentina e Davide.' })}{' '}
                <Link to="/chi-siamo" data-testid="ol-who-cta"
                      className="font-medium text-[#2f5749] underline underline-offset-[4px] decoration-[#2f5749]/40 hover:decoration-[#2f5749]">
                  {t('opPro.whoCta', { defaultValue: "Conosci la nostra storia" })}
                </Link>
              </p>
              <p className="mt-4 flex flex-wrap items-center gap-1.5 text-sm text-foreground/70">
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
        {/* CP (10/9 notte): qui c'era la chiusura verde «Il tuo lavoro
            merita un posto tutto suo» (ol-end): ripeteva l'hero parola
            per parola e il suo bottone riportava al modulo di un
            centimetro sopra. La pagina finisce sul modulo. */}
      </div>
    </MarketplaceShell>
  );
}
