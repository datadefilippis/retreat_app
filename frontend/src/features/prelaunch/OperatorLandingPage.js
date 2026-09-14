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
 *   3. PERCHE' ORA il patto 2026 (testo del founder 14/9) + contatore (ol-now)
 *   4. QUANTO COSTA Gratis e Pro a confronto, link ad Aurya Sound (ol-prezzi)
 *      (14/9: via «Crea anche le tue meditazioni», toglieva il focus)
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
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Mail, UserRound, Search, CalendarCheck2, Mountain, Link2, ClipboardCheck,
  Newspaper, Megaphone, Send, Award, Check,
} from 'lucide-react';
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

/* DS-L (14/9/2026, founder: «un tocco piu' stiloso»): il numerale sta
   SULLA foto come pillola d'oro, la foto respira al passaggio (scala
   1.04 in 700 ms), la scheda si solleva. Solo dove il hover esiste. */
function OfferCard({ image, numeral, title, body }) {
  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white
                        ring-1 ring-[#1e2f28]/[0.07]
                        shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]
                        motion-safe:transition-all motion-safe:duration-500
                        hover:-translate-y-1 hover:shadow-[0_2px_4px_rgba(30,47,40,0.05),0_28px_56px_-24px_rgba(30,47,40,0.40)]">
      <div className="relative aspect-[3/2] w-full overflow-hidden bg-[#e8e2d4]">
        <img src={image} alt="" width="900" height="600" loading="lazy" decoding="async"
             className="h-full w-full object-cover motion-safe:transition-transform motion-safe:duration-700 group-hover:scale-[1.04]" />
        <span className="absolute left-4 top-4 inline-flex h-9 min-w-9 items-center justify-center rounded-full
                         bg-[#0e1a15]/70 px-3 font-display text-sm tracking-[0.12em] text-[#d6c49a] backdrop-blur-sm ring-1 ring-[#d6c49a]/40"
              aria-hidden>{numeral}</span>
      </div>
      <div className="flex flex-1 flex-col p-7 sm:p-8">
        <div aria-hidden className="gold-rule mb-4 max-w-[3rem]" />
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

/* DS-L — i riquadri entrano uno dopo l'altro quando la griglia arriva in
   vista (classe ol-stagger in index.css). Default VISIBILE: senza
   IntersectionObserver, o con «meno movimento», non si nasconde nulla. */
function useStagger() {
  const ref = useRef(null);
  const [dentro, setDentro] = useState(true);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver !== 'function') return undefined;
    if (typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.85) return undefined;
    setDentro(false);
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { setDentro(true); io.disconnect(); }
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return { ref, className: `ol-stagger${dentro ? ' is-in' : ''}` };
}

const ICONE_VOCI = [UserRound, Search, CalendarCheck2, Mountain, Link2, ClipboardCheck];
const ICONE_PATTO = [Newspaper, Megaphone, Send, Award];

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  const griglia = useStagger();
  const grigliaPatto = useStagger();
  const grigliaPassi = useStagger();

  useSeoMeta({
    title: t('opPro.seoTitle', { defaultValue: "Per operatori olistici: il tuo spazio professionale, pronto oggi | Aurya" }),
    description: t('opPro.seoDesc', { defaultValue: "Una pagina tutta tua per presentarti, mostrare i tuoi servizi, ricevere prenotazioni e organizzare eventi e ritiri. Un solo link da condividere. Gratis per sempre, senza commissioni." }),
    canonicalPath: '/entra-nella-rete',
  });

  /* founder 14/9/2026: niente countdown in pagina (un conto alla rovescia
     diventa subito obsoleto). La data e' scritta nel testo; /public/fondatori
     resta la fonte del badge, non di questa pagina. */

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
    { title: t('opPro.v2t', { defaultValue: "Fatti trovare." }),
      body: t('opPro.v2b', { defaultValue: "Il tuo profilo è pubblico e può essere trovato anche su Google. Inoltre, puoi comparire nella directory di Aurya, dove le persone cercano operatori, pratiche, eventi e ritiri." }),
      key: t('opPro.v2k', { defaultValue: "La tua pagina può essere trovata anche da chi cerca un operatore o una pratica come la tua." }) },
    { title: t('opPro.v3t', { defaultValue: "Ricevi prenotazioni." }),
      body: t('opPro.v3b', { defaultValue: "Pubblica i tuoi servizi, indica prezzi e disponibilità e ricevi le richieste di appuntamento direttamente dalla tua pagina. Il calendario ti mostra gli appuntamenti già fissati, così sai sempre quando sei disponibile." }),
      key: t('opPro.v3k', { defaultValue: "Meno messaggi per organizzare gli appuntamenti." }) },
    { title: t('opPro.v4t', { defaultValue: "Organizzi i tuoi eventi e ritiri." }),
      body: t('opPro.v4b', { defaultValue: "Crea la pagina del tuo evento o del tuo ritiro con data, luogo, descrizione, prezzo e posti disponibili. Le persone possono iscriversi direttamente online e pagare la caparra. Tu vedi chi si è iscritto e quanto ha già pagato." }),
      key: t('opPro.v4k', { defaultValue: "Tu pensi all’esperienza. Aurya ti aiuta con le iscrizioni." }) },
    { title: t('opPro.v5t', { defaultValue: "Un solo link per tutto il tuo lavoro." }),
      body: t('opPro.v5b', { defaultValue: "Mettilo nella bio di Instagram, su WhatsApp o invialo direttamente ai tuoi clienti. Dentro trovano la tua storia, i tuoi servizi, gli eventi, i ritiri e le recensioni." }),
      key: t('opPro.v5k', { defaultValue: "Un solo link al posto di tanti link diversi." }) },
    { title: t('opPro.v6t', { defaultValue: "Tieni tutto in ordine." }),
      body: t('opPro.v6b', { defaultValue: "Prenotazioni, clienti, pagamenti e recensioni sempre a portata di mano." }),
      key: t('opPro.v6k', { defaultValue: "Meno fogli, meno messaggi e meno cose da ricordare." }) },
  ];
  /* Perche' entrare ora — AB-R3 (14/9/2026, founder con Valentina): chi
     pubblica il profilo entro il 31/12/2026 ha i vantaggi del Pro senza
     Sound, gratis. Tre schede piu' il badge per i primi venti. */
  const patto = [
    { title: t('opPro.nowC1t', { defaultValue: "Un’intervista nel Magazine" }),
      body: t('opPro.nowC1b', { defaultValue: "Raccontaci il tuo percorso e il tuo lavoro. Pubblicheremo la tua storia nel Magazine di Aurya, gratuitamente." }) },
    { title: t('opPro.nowC2t', { defaultValue: "I tuoi eventi sui social di Aurya" }),
      body: t('opPro.nowC2b', { defaultValue: "Possiamo raccontare i tuoi eventi e ritiri sui nostri canali, con la tua foto e il link alla tua pagina." }) },
    { title: t('opPro.nowC3t', { defaultValue: "La Lettera del Cerchio" }),
      body: t('opPro.nowC3b', { defaultValue: "Quando hai un ritiro o un evento adatto agli interessi degli iscritti della tua zona, possiamo segnalarlo nella Lettera del Cerchio." }) },
    { title: t('opPro.nowB2t', { defaultValue: "Badge Fondatore" }),
      body: t('opPro.nowB2b2', { defaultValue: "I primi 20 operatori avranno il badge Fondatore per sempre sul proprio profilo." }) },
  ];
  /* Quanto costa (founder 14/9): Gratis e Pro a confronto diretto.
     Nella riga di Studio il link ad Aurya Sound, per scoprire di piu'. */
  const baseRighe = [
    t('opPro.g1', { defaultValue: "Profilo pubblico e pagina link" }),
    t('opPro.g2', { defaultValue: "Listino, calendario e prenotazioni" }),
    t('opPro.g3', { defaultValue: "Eventi e ritiri con caparra e iscrizioni" }),
    t('opPro.g4', { defaultValue: "Clienti, pagamenti e recensioni" }),
    t('opPro.g5', { defaultValue: "Zero commissioni su quello che incassi" }),
  ];
  const proRighe = [
    { testo: t('opPro.pro1', { defaultValue: "Crea Studio: meditazioni personalizzate con musica, frequenze e la tua voce" }), link: '/sound',
      linkLabel: t('opPro.pro1link', { defaultValue: "Scopri Aurya Sound" }) },
    { testo: t('opPro.pro2', { defaultValue: "I tuoi eventi nella Lettera del Cerchio della tua zona" }) },
    { testo: t('opPro.pro3', { defaultValue: "I tuoi eventi sui social di Aurya" }) },
    { testo: t('opPro.pro4', { defaultValue: "L’intervista e i reel che ti raccontano" }) },
    { testo: t('opPro.pro5', { defaultValue: "I tuoi ritiri in prima fila" }) },
  ];
  /* Come si comincia: tre passi, tre schede. */
  const cards = [
    { numeral: '01', title: t('opPro.j1t', { defaultValue: "Crei il tuo account." }), body: t('opPro.j1b', { defaultValue: "Inserisci nome, email e password. Ci metti circa un minuto. Non serve la carta." }) },
    { numeral: '02', title: t('opPro.j2t', { defaultValue: "Crei la tua pagina." }), body: t('opPro.j2b', { defaultValue: "Aggiungi una foto, racconta chi sei e inserisci il tuo primo servizio. La tua pagina è online e puoi subito condividere il link." }) },
    { numeral: '03', title: t('opPro.j3t', { defaultValue: "Entri nella rete." }), body: t('opPro.j3b', { defaultValue: "Quando il tuo profilo è online, entri nel gruppo Telegram degli operatori Aurya. Lì trovi le novità, puoi parlare direttamente con noi e vedi le richieste di eventi e ritiri che ci arrivano. Se vuoi, ti aiutiamo anche a raccontare il tuo lavoro e a ottenere il badge Verificato Aurya." }) },
  ];
  /* Sei domande, risposte brevi e oneste, una alla volta (SR5). */
  const faq = [
    {
      q: t('opPro.faq1q', { defaultValue: "Quanto costa?" }),
      a: (
        <ul className="list-disc space-y-2 pl-5">
          <li>{t('opPro.faq1b1', { defaultValue: "Il piano base è gratuito per sempre. Non paghi un abbonamento e non paghi commissioni su prenotazioni o pagamenti." })}</li>
          <li>{t('opPro.faq1b2', { defaultValue: "Dal 2027 puoi scegliere il piano Pro se vuoi funzioni aggiuntive: 19 € al mese o 200 € l’anno." })}</li>
          <li>
            {t('opPro.faq1b3', { defaultValue: "Tutti i piani, riga per riga: " })}
            <Link to="/costi" className="font-semibold text-primary underline underline-offset-2">
              {t('opPro.faq1b3cta', { defaultValue: "scopri i piani e i costi" })}
            </Link>
          </li>
        </ul>
      ),
    },
    { q: t('opPro.faq4q', { defaultValue: "Posso usare Aurya anche se ho già un sito?" }), a: t('opPro.faq4a', { defaultValue: "Sì. Puoi usare Aurya insieme al tuo sito. Può diventare la pagina che condividi su Instagram e WhatsApp per mostrare servizi, prenotazioni, eventi e ritiri." }) },
    { q: t('opPro.faq3q', { defaultValue: "Posso continuare a usare Instagram?" }), a: t('opPro.faq3a2', { defaultValue: "Certo. Puoi mettere il tuo link Aurya nella bio di Instagram e continuare a usare il tuo profilo normalmente." }) },
    { q: t('opPro.faq5q', { defaultValue: "Posso continuare a ricevere prenotazioni da WhatsApp o telefono?" }), a: t('opPro.faq5a2', { defaultValue: "Sì. Aurya aggiunge un altro modo per ricevere prenotazioni. Puoi continuare a usare i canali che già utilizzi." }) },
    { q: t('opPro.faq2q', { defaultValue: "Le persone possono trovare il mio profilo anche se non mi conoscono?" }), a: t('opPro.faq2a3', { defaultValue: "Sì. Il profilo è pubblico e può essere trovato tramite Google e nella directory degli operatori Aurya." }) },
    { q: t('opPro.faq6q', { defaultValue: "Posso smettere di usare Aurya quando voglio?" }), a: t('opPro.faq6a', { defaultValue: "Sì. Puoi smettere di usare Aurya quando vuoi." }) },
  ];

  const ctaOpen = t('opPro.ctaOpen', { defaultValue: "Apri il tuo spazio" });

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
            <Lede size="lead" className="mt-6">{t('opPro.heroP5', { defaultValue: "Guarda un profilo vero: servizi, recensioni e ritiri in programma, tutto sulla stessa pagina." })}</Lede>
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
            <DisplayTitle as="h2" id="ol-go-title" size="section" measure="title">{t('opPro.goTitle', { defaultValue: "Cosa puoi fare con Aurya." })}</DisplayTitle>
            {/* DS-L: numerale d'oro + icona in un cerchio salvia, fondo che
                sfuma verso il crema, la frase-chiave con un filo a sinistra,
                sollevamento al passaggio, ingresso a scalare */}
            <ul ref={griglia.ref} className={`mt-10 grid list-none gap-6 p-0 sm:mt-12 sm:grid-cols-2 lg:grid-cols-3 ${griglia.className}`}>
              {voices.map((v, i) => {
                const Icona = ICONE_VOCI[i] || UserRound;
                return (
                  <li key={v.title}
                      className="group relative flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-gradient-to-b from-white to-[#faf7f0]
                                 p-7 ring-1 ring-[#1e2f28]/[0.07]
                                 shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]
                                 motion-safe:transition-all motion-safe:duration-500
                                 hover:-translate-y-1 hover:ring-[#c9b37e]/60 hover:shadow-[0_2px_4px_rgba(30,47,40,0.05),0_28px_56px_-24px_rgba(30,47,40,0.40)]">
                    <div className="flex items-start justify-between gap-4">
                      <p className="eyebrow" aria-hidden>{String(i + 1).padStart(2, '0')}</p>
                      <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]
                                       motion-safe:transition-colors group-hover:bg-[#2f5749] group-hover:text-[#f6f2e8]">
                        <Icona className="h-5 w-5" aria-hidden />
                      </span>
                    </div>
                    <h3 className="mt-5 font-display text-[1.45rem] leading-tight text-foreground sm:text-2xl">{v.title}</h3>
                    <p className="mt-3 text-[0.975rem] leading-relaxed text-foreground/75">{v.body}</p>
                    <p className="mt-auto border-l-2 border-[#c9b37e] pl-3 pt-0 text-[0.975rem] font-semibold leading-snug text-[#2f5749]"
                       style={{ marginTop: 'auto', paddingTop: 0 }}>
                      <span className="block pt-5">{v.key}</span>
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        </Section>

        {/* founder 14/9/2026: via la sezione «Crea anche le tue meditazioni»
            — toglieva il focus dall'entrare nella rete. Studio vive nella
            scheda Pro di «Quanto costa», con il link ad Aurya Sound. */}

        {/* CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili
            logici e storytelling»): qui c'era la fascia «E il tuo profilo
            puo' essere scoperto anche su Aurya» (ol-rete). Diceva la
            scheda «Ti possono trovare» (sopra) e la voce «Opportunita'
            dalla rete» del patto (sotto), con una foto in mezzo. Via. */}

        {/* ── 4. PERCHE' ENTRARE ORA — il testo del founder (14/9/2026) ── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-now-title" width="max-w-5xl">
         <div data-testid="ol-now">
          <DisplayTitle as="h2" id="ol-now-title" size="section" measure="title">{t('opPro.nowTitle', { defaultValue: "Perché entrare ora" })}</DisplayTitle>
          <Lede size="lead" className="mt-7">{t('opPro.nowP1', { defaultValue: "Entra entro il 31 dicembre 2026 e ricevi gratuitamente alcuni vantaggi che dal 2027 saranno disponibili nel piano Pro." })}</Lede>
          <Lede size="body" className="mt-3 font-semibold">{t('opPro.nowP2', { defaultValue: "Il piano base, invece, resta gratuito per sempre." })}</Lede>
          <p className="mt-8 font-display text-[1.35rem] leading-snug text-foreground sm:text-[1.6rem]">{t('opPro.nowSub', { defaultValue: "Entrando ora hai anche:" })}</p>
          {/* DS-L: quattro schede con un'icona e un filo d'oro in testa,
              ingresso a scalare; la chiusura «Entra tra i primi» in un
              pannello salvia (l'unica ancora scura della pagina dopo l'hero) */}
          <ul ref={grigliaPatto.ref} className={`mt-5 grid list-none gap-4 p-0 sm:grid-cols-2 ${grigliaPatto.className}`} data-testid="ol-now-patto">
            {patto.map((b, i) => {
              const Icona = ICONE_PATTO[i] || Award;
              return (
                <li key={b.title}
                    className="group relative overflow-hidden rounded-2xl bg-white p-5 ring-1 ring-[#1e2f28]/[0.07]
                               motion-safe:transition-all motion-safe:duration-500 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-24px_rgba(30,47,40,0.35)]">
                  <div aria-hidden className="gold-rule absolute inset-x-5 top-0" />
                  <div className="flex items-start gap-4">
                    <span className="mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#c9b37e]/20 text-[#7d6a3a]">
                      <Icona className="h-[18px] w-[18px]" aria-hidden />
                    </span>
                    <div>
                      <p className="font-display text-[1.2rem] leading-tight text-foreground">{b.title}</p>
                      <p className="mt-2 text-sm leading-snug text-foreground/80">{b.body}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="relative mt-10 overflow-hidden rounded-[1.75rem] bg-[#2f5749] px-7 py-8 text-[#f6f2e8] sm:px-10 sm:py-10" data-testid="ol-now-posto">
            <div aria-hidden className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[#d6c49a]/10 blur-2xl" />
            <div aria-hidden className="gold-rule mb-6 max-w-[6rem] opacity-90" />
            <p className="font-display text-[1.5rem] leading-snug sm:text-[1.9rem]">{t('opPro.nowPostoT', { defaultValue: "Entra tra i primi operatori di Aurya." })}</p>
            <p className="mt-4 max-w-[52ch] text-base font-semibold leading-relaxed">
              {t('opPro.nowCloseA2', { defaultValue: "Non cerchiamo semplicemente iscritti." })}{' '}
              {t('opPro.nowCloseB2', { defaultValue: "Cerchiamo i primi operatori con cui costruire la rete di Aurya." })}
            </p>
            <p className="mt-3 max-w-[52ch] text-base leading-relaxed opacity-90">{t('opPro.nowEntra', { defaultValue: "Entra entro il 31 dicembre 2026 per avere questi vantaggi." })}</p>
            <div className="mt-7"><EditorialCta href={FORM_ANCHOR} onClick={scrollToForm} variant="solid" tone="dark" data-testid="ol-now-cta">{ctaOpen}</EditorialCta></div>
          </div>
         </div>
        </Section>

        {/* ── 6. QUANTO COSTA — il base per sempre, il piu' dal 2027 ─── */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-prezzi-title" width="max-w-5xl">
          <div data-testid="ol-prezzi">
            <DisplayTitle as="h2" id="ol-prezzi-title" size="section" measure="title">{t('opPro.prezziTitle', { defaultValue: "Quanto costa." })}</DisplayTitle>
            <p className="mt-6 font-display text-[1.6rem] leading-tight text-[#2f5749] sm:text-[2rem]">{t('opPro.prezziP1', { defaultValue: "Il piano base è gratuito per sempre." })}</p>
            <p className="mt-3 text-lg font-semibold leading-snug text-foreground">{t('opPro.prezziP2', { defaultValue: "Non paghi un abbonamento e non paghi commissioni su quello che guadagni." })}</p>
            <Lede size="lead" className="mt-4 max-w-[62ch]">{t('opPro.prezziP3', { defaultValue: "Tutto quello che hai visto sopra è incluso nel piano base. Dal 1° gennaio 2027, se vuoi funzioni aggiuntive, puoi scegliere il piano Pro." })}</Lede>
            {/* founder 14/9: i due piani a confronto diretto */}
            {/* DS-L: il piano base in bianco con le spunte salvia, il Pro
                in salvia scuro con l'oro (il contrasto dice «e' il piu'»),
                prezzo grande in display, l'eyebrow con la data */}
            <div className="mt-8 grid gap-5 sm:grid-cols-2" data-testid="ol-prezzi-confronto">
              <div className="flex flex-col rounded-[1.75rem] bg-white p-7 ring-1 ring-[#1e2f28]/[0.07]
                              shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]" data-testid="ol-prezzi-base">
                <p className="eyebrow">{t('opPro.baseEyebrow', { defaultValue: "Piano base" })}</p>
                <p className="mt-3 font-display text-[2.4rem] leading-none text-foreground">0 €</p>
                <p className="mt-2 text-sm text-foreground/70">{t('opPro.baseSotto', { defaultValue: "Per sempre." })}</p>
                <div aria-hidden className="gold-rule my-5" />
                <ul className="space-y-2.5">
                  {baseRighe.map((riga) => (
                    <li key={riga} className="flex items-start gap-3 text-[0.975rem] leading-relaxed text-foreground/85">
                      <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
                        <Check className="h-3 w-3" aria-hidden />
                      </span>
                      <span>{riga}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative flex flex-col overflow-hidden rounded-[1.75rem] bg-[#2f5749] p-7 text-[#f6f2e8]
                              shadow-[0_18px_44px_-20px_rgba(47,87,73,0.55)]" data-testid="ol-prezzi-pro">
                <div aria-hidden className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-[#d6c49a]/10 blur-2xl" />
                <p className="eyebrow eyebrow-light">{t('opPro.proEyebrow', { defaultValue: "Pro · dal 1° gennaio 2027" })}</p>
                <p className="mt-3 font-display text-[2.4rem] leading-none">19 € <span className="text-[1.1rem] opacity-80">al mese</span></p>
                <p className="mt-2 text-sm opacity-85">{t('opPro.proSotto2', { defaultValue: "Oppure 200 € l’anno. Tutto il piano base, più:" })}</p>
                <div aria-hidden className="gold-rule my-5 opacity-90" />
                <ul className="space-y-2.5">
                  {proRighe.map((r) => (
                    <li key={r.testo} className="flex items-start gap-3 text-[0.975rem] leading-relaxed">
                      <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#d6c49a]/20 text-[#d6c49a]">
                        <Check className="h-3 w-3" aria-hidden />
                      </span>
                      <span>
                        {r.testo}
                        {r.link && (
                          <>{' '}<Link to={r.link} data-testid="ol-prezzi-sound" className="font-semibold text-[#f6f2e8] underline decoration-[#d6c49a] underline-offset-4 hover:text-[#d6c49a]">{r.linkLabel} →</Link></>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
                {/* il titolo intero resta nel DOM per chi legge senza stile e per la shell */}
                <p className="sr-only">{t('opPro.proTitolo', { defaultValue: "Pro · 19 € al mese, o 200 € l’anno" })}</p>
              </div>
            </div>
            <div className="mt-7">
              <EditorialCta to="/costi" variant="quiet" data-testid="ol-prezzi-cta">{t('opPro.prezziCta', { defaultValue: "Scopri tutti i piani" })}</EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. COME SI COMINCIA — tre passi, tre schede ──────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-join-title" width="max-w-6xl">
          <div data-testid="ol-join">
            <DisplayTitle as="h2" id="ol-join-title" size="section" measure="title">{t('opPro.joinTitle', { defaultValue: "Come si comincia." })}</DisplayTitle>
            <ul ref={grigliaPassi.ref} className={`mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-3 ${grigliaPassi.className}`}>
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
                                      motion-safe:transition-colors hover:text-[#2f5749]
                                      [&::-webkit-details-marker]:hidden">
                    <span>{f.q}</span>
                    <span aria-hidden className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full
                                                 ring-1 ring-[#c9b37e]/70 text-[#8a7440] transition-transform group-open:rotate-45 group-open:bg-[#c9b37e]/15">+</span>
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
              {/* founder 14/9: l'ultima spinta prima della registrazione */}
              <p className="mb-6 font-display text-[1.2rem] leading-snug text-foreground/85 sm:text-[1.35rem]" data-testid="ol-form-sintesi">
                {t('opPro.formSintesi1', { defaultValue: "Una pagina per presentarti. Un link da condividere. Un posto dove ricevere prenotazioni e organizzare i tuoi eventi." })}
                {' '}<span className="font-semibold text-[#2f5749]">{t('opPro.formSintesi2', { defaultValue: "Gratis per sempre." })}</span>
              </p>
              <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                            className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.6rem]">
                {t('opPro.formTitle2', { defaultValue: "Si comincia da te." })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7 font-semibold">{t('opPro.formA3', { defaultValue: "Crea il tuo account in un minuto e pubblica la tua pagina. Quando sei online, puoi subito condividere il tuo link." })}</Lede>
              <Lede size="body" className="mt-5">{t('opPro.formC3', { defaultValue: "Entri nel gruppo Telegram degli operatori Aurya." })}</Lede>
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
