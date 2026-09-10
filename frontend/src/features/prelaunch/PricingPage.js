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

/* I prezzi dal 1° gennaio 2027 — devono combaciare col piano di
   business (docs/AURYA_PIANO_BUSINESS_2026-09.md) e, da gennaio, col seed. */
export const PRICING_2027 = { spinta: 19, club: 49, pro: 119, pro_monthly: 12 };
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

/* I vantaggi dei piani a pagamento: SOLO quelli che sappiamo consegnare
   da gennaio (founder 10/9: «non proponiamo ciò che non abbiamo»). Il
   resto (la rete che lavora, la quota sugli ascolti, i 45 minuti) vive
   nel piano di business e arriva in pagina quando e' vero. */
const SPINTA = [
  ['Il ritiro in prima fila', 'In cima a Ritiri ed esperienze, sopra l’elenco per data, fino al giorno del ritiro.'],
  ['Un invio nella Lettera', 'Un’email agli iscritti del Cerchio della tua zona e dei tuoi temi, con la scheda del ritiro.'],
  ['Un post su Instagram', 'Sull’account di Aurya, con il link al ritiro.'],
];

const CLUB = [
  ['La prima fila su tutti i tuoi ritiri, tutto l’anno', 'Selezione in cima, un invio nella Lettera per ogni ritiro (fino a due al mese), un post al mese.'],
  ['Badge e precedenza nella tua zona', 'Nella directory, a parità di profilo, vieni prima.'],
  ['Il racconto breve', 'Otto domande, e scriviamo noi la tua storia sul profilo.'],
  ['Risposta entro due giorni', 'Via email, da Valentina.'],
];

const PRO = [
  ['Tutto il Club, per primo', 'Primo tra i Club in prima fila; fino a tre invii al mese.'],
  ['L’intervista completa', 'Una conversazione con Valentina, il badge Verificato Aurya, una pagina nel Magazine.'],
  ['Aurya Sound Studio', 'Crea Studio: componi meditazioni con la tua voce, basi e frequenze; le pubblichi con un link e le condividi coi tuoi clienti.'],
  ['WhatsApp con Valentina', 'Con orari scritti.'],
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
    description: t('pricing.seoDesc2', { defaultValue: 'Aurya non prende commissioni, mai. Gli strumenti sono gratis per sempre. Dal 2027, se vuoi la prima fila: la Spinta per un ritiro a 19 €, il Club a 49 € l’anno, il Pro a 119 €.' }),
  });

  const verita = [
    t('pricing.v1', { defaultValue: 'Aurya non prende commissioni. Mai. Né sui ritiri, né sui servizi, né online né offline: quello che incassi è tuo.' }),
    t('pricing.v2', { defaultValue: 'Gli strumenti sono gratis per sempre: profilo, listino, richieste, calendario, clienti, recensioni, eventi e ritiri con la caparra, la pagina link.' }),
    t('pricing.v3', { defaultValue: 'Fino al 31 dicembre 2026 Aurya non ha alcun costo, di nessun tipo.' }),
    t('pricing.v4', { defaultValue: 'Dal 1° gennaio 2027 si paga solo la prima fila, cioè le persone che ti portiamo, e la tua voce. Qui sotto trovi i prezzi, da oggi, così sai cosa succede a gennaio. Oggi non c’è niente da comprare: i piani si accendono a gennaio, e i vantaggi li scriviamo per intero a dicembre, quando saranno veri.' }),
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

        {/* Le quattro porte, dal 1° gennaio 2027 */}
        <div className="mx-auto mt-14 max-w-6xl">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground" data-testid="pricing-from">
            {t('pricing.from2027', { defaultValue: 'I prezzi dal 1° gennaio 2027' })}
          </p>
          <div className="mt-6 grid gap-6 lg:grid-cols-2 xl:grid-cols-4" data-testid="pricing-plans">
            <Scheda testid="plan-free" domanda="Posso lavorare?" nome="Gratis"
                    prezzo="0 €" sotto="Per sempre. Nessuna commissione." voci={GRATIS} />
            <Scheda testid="plan-spinta" domanda="Ho un ritiro da riempire" nome="Spinta"
                    prezzo={`${PRICING_2027.spinta} €`} sotto="Una volta, per un ritiro." voci={SPINTA} />
            <Scheda testid="plan-club" domanda="Voglio persone e lavoro, tutto l’anno" nome="Club Aurya" evidenza
                    prezzo={`${PRICING_2027.club} € l’anno`} sotto="Quattro euro al mese, pagati una volta." voci={CLUB} />
            <Scheda testid="plan-pro" domanda="La mia voce, il mio racconto, qualcuno accanto" nome="Pro"
                    prezzo={`${PRICING_2027.pro} € l’anno`} sotto={`oppure ${PRICING_2027.pro_monthly} € al mese.`} voci={PRO} />
          </div>
        </div>

        {/* I cancelli e la garanzia: le promesse vere */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-cancelli">
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.gateTitle', { defaultValue: 'Il Club si accende quando la fila c’è.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.gateBody', { defaultValue: 'Vendere la prima fila prima che esista sarebbe una bugia. Il Club si vende quando il Cerchio ha 300 iscritti confermati, ci sono 10 ritiri in programma e il sito fa 1.000 visite al mese. Finché questi tre numeri non sono veri, il Club resta gratis per tutti, e te lo diciamo qui. La Spinta si propone solo quando nella tua zona c’è davvero qualcuno da avvisare.' })}
            </p>
          </div>
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.foundersTitle', { defaultValue: 'I fondatori.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.foundersBody', { defaultValue: 'I primi venti operatori olistici che pubblicano il profilo entro il 31 ottobre 2026 hanno il Club regalato fino al 30 giugno 2027, il badge permanente, il prezzo del Pro bloccato per sempre e la prima chiamata quando la rete lavora.' })}
            </p>
          </div>
          <div className="rounded-2xl border bg-card px-5 py-4">
            <p className="text-sm font-semibold text-foreground">
              {t('pricing.guaranteeTitle', { defaultValue: 'La garanzia.' })}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {t('pricing.guaranteeBody', { defaultValue: 'Club e Pro: trenta giorni, se non ti serve ti rimborsiamo. La Spinta: se l’email non parte, ti rimborsiamo. Nessun contratto, nessun rinnovo a sorpresa: ti avvisiamo trenta giorni prima e disdici quando vuoi.' })}
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
