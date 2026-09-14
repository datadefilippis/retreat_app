/**
 * PricingPage — /costi.
 *
 * AB3 (13/8/2026): la pagina che risponde fino in fondo a «Quanto
 * costa?» per un operatore poco digitale. P1 (10/9/2026, piano di
 * business): il modello cambia — AURYA NON PRENDE COMMISSIONI, MAI.
 * Il 5% sugli incassi online e' uscito (si aggirava, obbligava a
 * Stripe chi non era pronto, ci metteva nel flusso del denaro); si
 * paga solo la PROMOZIONE (la prima fila) e la voce. I piani del 2027
 * sono scritti qui da oggi, come testo, perche' l'operatore deve
 * sapere cosa succede a gennaio; non si comprano prima del 1/1/2027
 * (fino ad allora tutto e' gratis e non c'e' niente da comprare).
 *
 * Regole:
 * - solo italiano; voce del brand: frasi brevi, tu diretto, zero superlativi
 * - i numeri del 2027 sono TIMBRATI qui (PRICING_2027) e protetti da
 *   una guardia; il catalogo backend li seguira' con la migrazione di
 *   gennaio (P4), finche' allora la fee del Gratis e' 0 (guardia)
 * - i tre cancelli del Club sono scritti come regola, non come contatori
 *   vivi: quelli arrivano con P8
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Check, ArrowRight } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { Section, DisplayTitle, Lede } from '../../components/editorial';

/* I prezzi dal 1° gennaio 2027 — devono combaciare col seed
   (seed_commercial_plans.retreat_pro) e col piano
   docs/PIANO_ABBONAMENTI_PRO19_2026-09.md. AB-R3 (14/9/2026, founder con
   Valentina): UN abbonamento, il Pro, 19 €/mese o 200 €/anno. */
export const PRICING_2027 = { pro_mese: 19, pro_anno: 200 };
/* La commissione di Aurya, oggi e per sempre. La guardia la confronta col seed. */
export const AURYA_FEE = 0;

const GRATIS = [
  ['Il tuo profilo pubblico nella directory',
   'La tua pagina su Aurya: chi sei, le foto, i tuoi servizi e i tuoi ritiri. Indicizzata su Google. La condividi con un link.'],
  ['Listino con richieste di appuntamento',
   'Metti i tuoi servizi con prezzo e durata. Chi visita la pagina ti manda la richiesta: tu confermi.'],
  ['Eventi e ritiri senza limiti',
   'Pubblichi quanti ritiri e incontri vuoi, ognuno con la sua pagina, le date e i posti. Compaiono in Ritiri ed esperienze.'],
  ['La caparra come vuoi tu',
   'Con il bonifico (chi prenota riceve importo, IBAN e scadenza, tu confermi con un clic) oppure online, se colleghi Stripe. Nessuna commissione di Aurya, in nessuno dei due casi.'],
  ['Partecipanti, promemoria e pass',
   'La lista di chi arriva, i promemoria automatici, un pass da mostrare all’ingresso.'],
  ['Clienti, ordini e conti',
   'Chi è venuto, quando, per cosa. Incassato, in arrivo, in ritardo: una pagina sola.'],
  ['Recensioni verificate',
   'Solo chi ha prenotato può lasciarne una. Tu rispondi.'],
  ['Un link solo per Instagram',
   'La tua pagina /@nome: servizi, eventi, ritiri, recensioni, la tua storia. Tutto nello stesso posto.'],
];

/* Il Pro: le quattro cose in piu' (founder 13-14/9), piu' la prima fila.
   Studio si accende da solo col piano; Lettera, social, intervista e
   reel li facciamo noi, li chiedi dal gestionale quando vuoi. */
const PRO = [
  ['Aurya Sound Studio (Crea Studio)', 'Componi le tue meditazioni con la tua voce, basi e frequenze; le condividi coi tuoi clienti con un link.'],
  ['I tuoi eventi nella Lettera del Cerchio', 'Quando pubblichi un ritiro o un evento, lo mandiamo agli iscritti del Cerchio della tua zona.'],
  ['I tuoi eventi sui social di Aurya', 'Pubblicati sui nostri canali, con la tua foto e il tuo link.'],
  ['L’intervista e i reel', 'Una conversazione con noi, la pagina nel Magazine, e i reel che ti presentano ai nostri follower.'],
  ['La prima fila', 'I tuoi ritiri in cima a Ritiri ed esperienze, tutto l’anno.'],
];

/* Chi entra nel 2026 (patto, 14/9): i vantaggi del Pro senza Sound, gratis. */
const PATTO_2026 = [
  ['L’intervista', 'Fatta da noi, con la pagina nel Magazine.'],
  ['I tuoi eventi sui social di Aurya', 'Sui nostri canali, gratis.'],
  ['La Lettera del Cerchio, se serve', 'I tuoi eventi agli iscritti della tua zona.'],
];

function Scheda({ nome, prezzo, sotto, voci, evidenza, testid, domanda }) {
  return (
    <div className={`flex flex-col rounded-3xl border bg-card p-6 sm:p-7 ${evidenza ? 'border-primary/40 shadow-md' : ''}`}
         data-testid={testid}>
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{domanda}</p>
      <h2 className="mt-1 font-display text-3xl text-foreground">{nome}</h2>
      <div className={`mt-4 rounded-2xl px-4 py-3 ${evidenza ? 'bg-primary/10' : 'bg-muted/60'}`}>
        <p className="text-lg font-semibold text-foreground">{prezzo}</p>
        <p className="mt-0.5 text-sm text-muted-foreground">{sotto}</p>
      </div>
      <ul className="mt-5 space-y-3.5">
        {voci.map(([label, info]) => (
          <li key={label} className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Check className="h-3 w-3 text-primary" aria-hidden />
            </span>
            <div>
              <p className="text-sm font-semibold text-foreground">{label}</p>
              <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{info}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function PricingPage() {
  const { t } = useTranslation('prelaunch');

  useSeoMeta({
    title: t('pricing.seoTitle2', { defaultValue: 'Quanto costa Aurya | Gratis per sempre, senza commissioni' }),
    description: t('pricing.seoDesc3', { defaultValue: 'Aurya non prende commissioni, mai. Gli strumenti sono gratis per sempre. Dal 2027, se vuoi di più, c’è il Pro: 19 € al mese o 200 € l’anno.' }),
  });

  const verita = [
    t('pricing.v1', { defaultValue: 'Aurya non prende commissioni. Mai. Né sui ritiri, né sui servizi, né online né offline: quello che incassi è tuo.' }),
    t('pricing.v2', { defaultValue: 'Gli strumenti sono gratis per sempre: profilo, listino, richieste, calendario, clienti, recensioni, eventi e ritiri con la caparra, la pagina link.' }),
    t('pricing.v3', { defaultValue: 'Fino al 31 dicembre 2026 Aurya non ha alcun costo, di nessun tipo.' }),
    t('pricing.v5', { defaultValue: 'Dal 1° gennaio 2027, se vuoi di più, c’è un abbonamento solo: il Pro, 19 € al mese o 200 € l’anno. Dentro: Crea Studio per le tue meditazioni, i tuoi eventi nella Lettera del Cerchio e sui social di Aurya, l’intervista e i reel. L’app resta gratuita.' }),
  ];

  return (
    <MarketplaceShell>
      <Section className="pt-14 sm:pt-20">
        <div className="mx-auto max-w-3xl text-center">
          <DisplayTitle as="h1">
            {t('pricing.title', { defaultValue: 'Quanto costa Aurya' })}
          </DisplayTitle>
          <Lede className="mt-4">
            {t('pricing.lede2', { defaultValue: 'Gratis per sempre, senza commissioni. Te lo diciamo per intero.' })}
          </Lede>
        </div>

        {/* Le quattro verita' */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-truths">
          {verita.map((riga, i) => (
            <div key={i} className="flex items-start gap-3 rounded-2xl border bg-card px-4 py-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">{i + 1}</span>
              <p className="text-[15px] leading-relaxed text-foreground/85">{riga}</p>
            </div>
          ))}
        </div>

        {/* Due porte: Gratis per sempre, Pro dal 1° gennaio 2027 (AB-R3) */}
        <div className="mx-auto mt-14 max-w-4xl">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground" data-testid="pricing-from">
            {t('pricing.from2027', { defaultValue: 'I prezzi dal 1° gennaio 2027' })}
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-2" data-testid="pricing-plans">
            <Scheda testid="plan-free" domanda="Posso lavorare?" nome="Gratis"
                    prezzo="0 €" sotto="Per sempre. Nessuna commissione." voci={GRATIS} />
            <Scheda testid="plan-pro" domanda="Voglio essere raccontato e trovato" nome="Pro" evidenza
                    prezzo={`${PRICING_2027.pro_mese} € al mese`} sotto={`Oppure ${PRICING_2027.pro_anno} € l’anno. Dal 1° gennaio 2027.`} voci={PRO} />
          </div>
        </div>

        {/* Il patto e la garanzia: le promesse vere */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-cancelli">
          <div className="rounded-2xl border border-primary/30 bg-card px-5 py-4" data-testid="pricing-patto-2026">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.patto2026Title', { defaultValue: 'Chi entra nel 2026.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.patto2026Body', { defaultValue: 'Chi pubblica il profilo entro il 31 dicembre 2026 ha gratis i vantaggi del Pro, tranne Studio: l’intervista, i suoi eventi sui social di Aurya e, se serve, nella Lettera del Cerchio. Dal 2027 questi servizi sono nel Pro; l’app resta gratuita. Il badge Fondatore va ai primi venti.' })}
            </p>
            <ul className="mt-3 space-y-1.5">
              {PATTO_2026.map(([label, info]) => (
                <li key={label} className="flex items-start gap-2 text-sm">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                  <span><span className="font-semibold text-foreground">{label}</span> <span className="text-muted-foreground">{info}</span></span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.guaranteeTitle', { defaultValue: 'La garanzia.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.guaranteeBody2', { defaultValue: 'Pro: trenta giorni, se non ti serve ti rimborsiamo. Nessun contratto, nessun rinnovo a sorpresa: ti avvisiamo trenta giorni prima e disdici quando vuoi.' })}
            </p>
          </div>
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.stripeTitle', { defaultValue: 'E Stripe?' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.stripeBody', { defaultValue: 'Non sei obbligato. La caparra la ricevi con un bonifico, e Aurya ti aiuta a chiederla. Se vuoi incassare online, colleghi Stripe dalle impostazioni: le sue commissioni (circa l’1,5 per cento più 25 centesimi per carta europea) sono di Stripe, non nostre.' })}
            </p>
          </div>
        </div>

        {/* Uscita */}
        <div className="mx-auto mt-12 max-w-2xl pb-16 text-center">
          <Link to="/entra-nella-rete#presentati"
                className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground">
            {t('pricing.backCta2', { defaultValue: 'Apri il tuo spazio' })}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </Section>
    </MarketplaceShell>
  );
}
