/**
 * PricingPage — /costi (AB3, 13/8/2026).
 *
 * La pagina che risponde fino in fondo a "Quanto costa?" per un
 * operatore poco digitale. Tre verita' in testa (gratis oggi, nessun
 * costo fino al 31/12/2026, poi due strade), poi i due piani spiegati
 * voce per voce in parole umane: niente sigle, niente gergo.
 *
 * Regole:
 * - solo italiano (linea 2/8): nessuna traduzione x4
 * - i numeri (19 EUR, 190 EUR, 5%) sono TIMBRATI qui e protetti da una
 *   guardia che li confronta col seed backend: se il listino cambia,
 *   la pagina non puo' mentire in silenzio
 * - voce del brand: frasi brevi, tu diretto, zero superlativi
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Check, ArrowRight } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { Section, DisplayTitle, Lede } from '../../components/editorial';

/* Prezzi mostrati — devono combaciare col seed backend (guardia AB). */
export const PRICING = { pro_monthly: 19, pro_yearly: 190, free_fee: 5 };

/* Le voci, spiegate a chi non mastica gestionali: etichetta corta
   (la stessa che si ritrova in Impostazioni) + spiegazione piana. */
const FREE_FEATURES = [
  ['Il tuo profilo pubblico',
   'La tua pagina su Aurya: chi sei, le foto, i tuoi servizi e i tuoi ritiri. La condividi con un link.'],
  ['Listino con richieste di appuntamento',
   'Metti i tuoi servizi con prezzo e durata. Chi visita la pagina ti manda la richiesta: tu confermi.'],
  ['Ritiri ed eventi senza limiti',
   'Pubblichi quanti ritiri e incontri vuoi, ognuno con la sua pagina, le date e i posti.'],
  ['Caparre, rate e link di pagamento',
   'Il partecipante paga la caparra online e riceve i link per il saldo. Le scadenze si gestiscono da sole.'],
  ['Promemoria di pagamento automatici',
   'Vedi chi ti deve cosa e mandi il sollecito con un click, col messaggio già scritto.'],
  ['Partecipanti, check-in e pass',
   'La lista di chi arriva, con un pass personale da mostrare all’ingresso. Tu lo spunti dal telefono.'],
  ['Email automatiche di conferma e promemoria',
   'Chi prenota riceve conferma e promemoria senza che tu debba scrivere nulla.'],
  ['Lista contatti e storico clienti',
   'Chi è venuto, quando, per cosa. La tua rubrica si costruisce da sola, con i consensi in regola.'],
  ['Newsletter e moduli di iscrizione',
   'Un modulo per raccogliere iscritti e scrivere loro quando hai qualcosa da dire.'],
  ['I tuoi conti sotto controllo',
   'Incassato, in arrivo, in ritardo: una pagina sola, anche per contanti e bonifici segnati a mano.'],
];

const PRO_FEATURES = [
  ['Tutto il piano Gratis',
   'Ogni cosa della colonna qui accanto, senza eccezioni.'],
  ['Zero commissioni',
   `Nessuna percentuale sugli incassi online: quello che incassi resta tuo. Col piano Gratis, Aurya trattiene il ${PRICING.free_fee}% solo sui pagamenti online.`],
  ['In evidenza nel calendario pubblico',
   'A parità di data, i tuoi ritiri compaiono per primi, con il segno ✦ In evidenza.'],
  ['Supporto prioritario',
   'Le tue richieste passano davanti: ti rispondiamo per primi.'],
  // TR6 (27/8) — Studio e' incluso nel Pro: la promessa sta anche qui
  ['Aurya Sound Studio',
   'Componi meditazioni con la tua voce, basi sonore e frequenze, dal browser. Le condividi in privato coi tuoi clienti: un link a persona, revocabile.'],
];

export default function PricingPage() {
  const { t } = useTranslation('prelaunch');

  useSeoMeta({
    title: t('pricing.seoTitle', { defaultValue: 'Piani e costi | Aurya' }),
    description: t('pricing.seoDesc', { defaultValue: 'L’utilizzo di Aurya è gratuito. Fino al 31 dicembre 2026 nessun costo, poi due piani semplici: Gratis con il 5% sugli incassi online, o Pro a 19 euro al mese senza commissioni.' }),
  });

  const cardCls = 'flex flex-col rounded-3xl border bg-card p-6 sm:p-8';

  return (
    <MarketplaceShell>
      <Section className="pt-14 sm:pt-20">
        <div className="mx-auto max-w-3xl text-center">
          <DisplayTitle as="h1">
            {t('pricing.title', { defaultValue: 'Quanto costa Aurya' })}
          </DisplayTitle>
          <Lede className="mt-4">
            {t('pricing.lede', { defaultValue: 'Te lo diciamo per intero, senza sorprese.' })}
          </Lede>
        </div>

        {/* Le tre verita' — le stesse della FAQ, per esteso */}
        <div className="mx-auto mt-10 max-w-2xl space-y-4" data-testid="pricing-truths">
          {[
            t('pricing.truth1', { defaultValue: 'L’utilizzo della piattaforma è sempre gratuito: profilo, listino, ritiri, clienti e conti non si pagano.' }),
            t('pricing.truth2', { defaultValue: 'Fino al 31 dicembre 2026 Aurya non ha alcun costo, nemmeno quando le prenotazioni arrivano tramite Aurya.' }),
            t('pricing.truth3', { defaultValue: 'Dopo quella data scegli tu una delle due strade qui sotto. Puoi cambiare idea quando vuoi.' }),
          ].map((riga, i) => (
            <div key={i} className="flex items-start gap-3 rounded-2xl border bg-card px-4 py-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">{i + 1}</span>
              <p className="text-[15px] leading-relaxed text-foreground/85">{riga}</p>
            </div>
          ))}
        </div>

        {/* I due piani */}
        <div className="mx-auto mt-14 grid max-w-4xl gap-6 lg:grid-cols-2" data-testid="pricing-plans">

          {/* Gratis */}
          <div className={cardCls} data-testid="plan-free">
            <h2 className="font-display text-3xl text-foreground">Gratis</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('pricing.freeTagline', { defaultValue: 'Per iniziare, e anche per restare.' })}
            </p>
            <div className="mt-5 rounded-2xl bg-muted/60 px-4 py-3.5">
              <p className="text-lg font-semibold text-foreground">
                {PRICING.free_fee}% {t('pricing.freeFeeLabel', { defaultValue: 'solo sugli incassi online' })}
              </p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {t('pricing.freeFeeHint', { defaultValue: 'Paghi solo quando incassi tramite Aurya. Contanti e bonifici che segni a mano non c’entrano: restano tuoi al 100%.' })}
              </p>
            </div>
            <ul className="mt-6 space-y-4">
              {FREE_FEATURES.map(([label, info]) => (
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

          {/* Pro */}
          <div className={`${cardCls} border-primary/40 shadow-md`} data-testid="plan-pro">
            <h2 className="font-display text-3xl text-foreground">Pro</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('pricing.proTagline', { defaultValue: 'Per chi incassa online con regolarità.' })}
            </p>
            <div className="mt-5 rounded-2xl bg-primary/10 px-4 py-3.5">
              <p className="text-lg font-semibold text-foreground">
                {PRICING.pro_monthly} € {t('pricing.proMonthLabel', { defaultValue: 'al mese' })}
              </p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {t('pricing.proYearHint', { defaultValue: `oppure ${PRICING.pro_yearly} € all’anno: paghi 10 mesi, 2 sono in regalo. E zero commissioni sugli incassi.` })}
              </p>
            </div>
            <ul className="mt-6 space-y-4">
              {PRO_FEATURES.map(([label, info]) => (
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
        </div>

        {/* Quale scegliere? — il conto fatto per loro */}
        <div className="mx-auto mt-10 max-w-2xl rounded-2xl border bg-card px-5 py-4"
             data-testid="pricing-which">
          <p className="text-sm font-semibold text-foreground">
            {t('pricing.whichTitle', { defaultValue: 'Quale conviene a te?' })}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            {t('pricing.whichBody', { defaultValue: `Il conto è semplice: con più di ${Math.round(PRICING.pro_monthly * 100 / PRICING.free_fee)} € di incassi online al mese, il Pro costa meno del ${PRICING.free_fee}%. Sotto quella soglia, resta sul Gratis: non ha scadenza e non ti chiede nulla.` })}
          </p>
        </div>

        {/* Uscita: torna al presentarsi */}
        <div className="mx-auto mt-12 max-w-2xl pb-16 text-center">
          <Link to="/entra-nella-rete#presentati"
                className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground">
            {t('pricing.backCta', { defaultValue: 'Presentati alla rete' })}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </Section>
    </MarketplaceShell>
  );
}
