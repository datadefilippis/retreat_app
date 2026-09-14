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
   'La tua pagina su Aurya: chi sei, le tue foto, i tuoi servizi e i tuoi ritiri. È pubblica, può essere trovata su Google e puoi condividerla con un link.'],
  ['Listino con richieste di appuntamento',
   'Pubblica i tuoi servizi con prezzo e durata. Chi è interessato può chiederti un appuntamento dalla tua pagina e tu decidi quando confermarlo.'],
  ['Eventi e ritiri senza limiti',
   'Pubblichi tutti gli eventi e i ritiri che vuoi, ognuno con la propria pagina, le date e i posti disponibili. Compaiono in Ritiri ed esperienze.'],
  ['Ricevi la caparra come preferisci',
   'Puoi chiedere la caparra con un bonifico: chi prenota riceve importo, IBAN e scadenza e tu confermi il pagamento. Oppure puoi collegare Stripe e riceverla online. Aurya non applica commissioni, né con il bonifico né con Stripe.'],
  ['Partecipanti, promemoria e pass',
   'Vedi chi partecipa, invia promemoria automatici e usa un pass per l’ingresso.'],
  ['Clienti e pagamenti',
   'Vedi i tuoi clienti, le prenotazioni e i pagamenti ricevuti o ancora da ricevere.'],
  ['Recensioni verificate',
   'Solo chi ha prenotato attraverso Aurya può lasciare una recensione. Tu puoi rispondere.'],
  ['Un link solo per Instagram',
   'La tua pagina /@nome raccoglie servizi, eventi, ritiri, recensioni e la tua storia. Puoi metterla nella bio di Instagram e condividerla dove vuoi.'],
];

/* Il Pro: le quattro cose in piu' (founder 13-14/9) e i ritiri in evidenza.
   Studio si accende da solo col piano; Lettera, social, intervista e reel
   li facciamo noi, li chiedi dal gestionale quando vuoi. L'evidenza dei
   ritiri e' «possono»: l'interruttore per ritiro arriva con P5. */
const PRO = [
  ['Aurya Sound Studio (Crea Studio)', 'Componi le tue meditazioni con la tua voce, basi e frequenze e condividile con i tuoi clienti tramite un link.'],
  ['I tuoi eventi nella Lettera del Cerchio', 'Quando pubblichi un ritiro o un evento, possiamo segnalarlo agli iscritti del Cerchio interessati nella tua zona.'],
  ['I tuoi eventi sui social di Aurya', 'Possiamo raccontare i tuoi eventi e ritiri sui nostri canali, con la tua foto e il link alla tua pagina.'],
  ['L’intervista e i reel', 'Una conversazione con noi, una pagina nel Magazine e contenuti che raccontano il tuo lavoro.'],
  ['I tuoi ritiri in evidenza', 'I tuoi ritiri possono essere messi in evidenza nella sezione Ritiri ed esperienze.'],
];

/* Chi entra nel 2026 (patto, 14/9): i vantaggi del Pro senza Sound, gratis. */
const PATTO_2026 = [
  ['L’intervista', 'Una conversazione con noi e una pagina dedicata nel Magazine.'],
  ['I tuoi eventi sui social di Aurya', 'Possiamo raccontare i tuoi eventi e ritiri sui nostri canali, con il link alla tua pagina.'],
  ['La Lettera del Cerchio', 'Possiamo segnalare i tuoi eventi agli iscritti del Cerchio interessati nella tua zona.'],
];

function Scheda({ nome, prezzo, sotto, nota, voci, evidenza, testid, domanda }) {
  return (
    <div className={`flex flex-col rounded-3xl border bg-card p-6 sm:p-7 ${evidenza ? 'border-primary/40 shadow-md' : ''}`}
         data-testid={testid}>
      {domanda && <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{domanda}</p>}
      <h2 className="mt-1 font-display text-3xl text-foreground">{nome}</h2>
      <div className={`mt-4 rounded-2xl px-4 py-3 ${evidenza ? 'bg-primary/10' : 'bg-muted/60'}`}>
        <p className="text-lg font-semibold text-foreground">{prezzo}</p>
        <p className="mt-0.5 text-sm text-muted-foreground">{sotto}</p>
        {nota && <p className="mt-2 text-sm font-medium text-foreground">{nota}</p>}
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

  /* founder 14/9: quattro punti, ognuno un titolo e una riga, senza ripetizioni */
  const verita = [
    [t('pricing.p1t', { defaultValue: 'Aurya non prende commissioni.' }),
     t('pricing.p1b', { defaultValue: 'Né sui ritiri né sui servizi. Quello che incassi è tuo.' })],
    [t('pricing.p2t', { defaultValue: 'Il piano base è gratuito per sempre.' }),
     t('pricing.p2b', { defaultValue: 'Profilo, servizi, prenotazioni, calendario, clienti, recensioni, eventi e ritiri con caparra e pagina link sono inclusi senza abbonamento.' })],
    [t('pricing.p3t', { defaultValue: 'Fino al 31 dicembre 2026 non paghi nulla.' }),
     t('pricing.p3b', { defaultValue: 'Puoi creare il tuo profilo, pubblicarlo e usare Aurya senza alcun costo.' })],
    [t('pricing.p4t', { defaultValue: 'Dal 1° gennaio 2027 puoi scegliere il Pro.' }),
     t('pricing.p4b', { defaultValue: 'Il Pro costa 19 € al mese o 200 € l’anno e aggiunge Crea Studio, la promozione dei tuoi eventi nella Lettera del Cerchio e sui social di Aurya, l’intervista e i reel.' })],
  ];

  return (
    <MarketplaceShell>
      <Section className="pt-14 sm:pt-20">
        <div className="mx-auto max-w-3xl text-center">
          <DisplayTitle as="h1">
            {t('pricing.title', { defaultValue: 'Quanto costa Aurya' })}
          </DisplayTitle>
          <Lede className="mt-4">
            {t('pricing.lede3', { defaultValue: 'Gratis per sempre, senza commissioni.' })}
          </Lede>
          <p className="mt-3 text-base leading-relaxed text-foreground/80" data-testid="pricing-sub">
            {t('pricing.sub', { defaultValue: 'Il piano base è gratuito per sempre. Aurya non prende commissioni su quello che incassi.' })}
          </p>
        </div>

        {/* Le quattro verita' */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-truths">
          {verita.map(([titolo, riga], i) => (
            <div key={i} className="flex items-start gap-3 rounded-2xl border bg-card px-4 py-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">{i + 1}</span>
              <p className="text-[15px] leading-relaxed text-foreground/85"><b className="text-foreground">{titolo}</b> {riga}</p>
            </div>
          ))}
          <p className="pt-1 text-center text-sm font-semibold text-foreground" data-testid="pricing-chiusa">
            {t('pricing.chiusa', { defaultValue: 'Il piano base resta gratuito.' })}
          </p>
        </div>

        {/* Due porte: Gratis per sempre, Pro dal 1° gennaio 2027 (AB-R3) */}
        <div className="mx-auto mt-14 max-w-4xl">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground" data-testid="pricing-from">
            {t('pricing.from2027', { defaultValue: 'I prezzi dal 1° gennaio 2027' })}
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-2" data-testid="pricing-plans">
            <Scheda testid="plan-free" nome="Gratis"
                    prezzo="0 €" sotto="Per sempre. Nessuna commissione." voci={GRATIS} />
            <Scheda testid="plan-pro" nome="Pro" evidenza
                    prezzo={`${PRICING_2027.pro_mese} € al mese`} sotto={`Oppure ${PRICING_2027.pro_anno} € l’anno. Dal 1° gennaio 2027.`}
                    nota="Il Pro aggiunge funzioni e visibilità. Il piano base resta gratuito." voci={PRO} />
          </div>
        </div>

        {/* Il patto e la garanzia: le promesse vere */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-cancelli">
          <div className="rounded-2xl border border-primary/30 bg-card px-5 py-4" data-testid="pricing-patto-2026">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.patto2026Title2', { defaultValue: 'Chi entra nel 2026' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.patto2026Body2', { defaultValue: 'Chi pubblica il proprio profilo entro il 31 dicembre 2026 riceve gratuitamente alcuni vantaggi che dal 2027 saranno inclusi nel Pro.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.patto2026Base', { defaultValue: 'Il piano base resta gratuito per sempre.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.patto2026Badge', { defaultValue: 'I primi 20 operatori ricevono anche il Badge Fondatore, per sempre sul proprio profilo.' })}
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
              {t('pricing.guaranteeBody3', { defaultValue: 'Il Pro ha una garanzia di 30 giorni: se ti accorgi che non fa per te, puoi chiedere il rimborso.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.guaranteeBody4', { defaultValue: 'Nessun contratto a lungo termine e nessun rinnovo a sorpresa. Ti avvisiamo 30 giorni prima del rinnovo e puoi disdire quando vuoi.' })}
            </p>
          </div>
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.stripeTitle', { defaultValue: 'E Stripe?' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.stripeBody2', { defaultValue: 'Non sei obbligato a usare Stripe.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.stripeBody3', { defaultValue: 'Puoi ricevere le caparre con un normale bonifico. Se invece vuoi permettere il pagamento online, puoi collegare Stripe dalle impostazioni.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.stripeBody4', { defaultValue: 'Le commissioni sui pagamenti online sono quelle applicate da Stripe, non da Aurya, e dipendono dalle tariffe di Stripe.' })}
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
