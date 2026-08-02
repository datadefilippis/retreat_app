/**
 * BlogNewsletterCTA — BN1 (docs/BLOG_NEWSLETTER_STRATEGIA_2026-07.md).
 *
 * Il blog e' il primo punto di conversione: ogni articolo chiude con
 * una proposta coerente col suo cluster, mai un popup.
 *  - pratiche (meditazione, breathwork, suono, energia...): la lettera
 *    di Aurya, promessa "una pratica raccontata bene ogni due settimane"
 *  - mondo ritiri (ritiri, yoga): avviso onesto "ti avvisiamo quando
 *    apriremo le prenotazioni, anche nella tua zona"
 *  - operatori: niente newsletter, la CTA converte alla rete
 *    (/entra-nella-rete): e' il lettore che vogliamo intervistare.
 * Form = LeadForm compact (solo email + consenso): nel flusso di
 * lettura ogni campo in piu' e' attrito. GA4: generate_lead con
 * lead_context per articolo/categoria.
 *
 * DS3 — il vestito, non la sostanza. Era un riquadro con bordo, angoli
 * tondi, fondo tinto e pastiglia con l'icona: un blocco promozionale
 * incollato in fondo alla colonna. Ora e' una BATTUTA della pagina, e
 * il fondo glielo da' la sezione che la ospita (sabbia, in entrambi i
 * chiamanti: indice del Magazine e scheda articolo). Riquadro dentro
 * riquadro non si fa: resta il filo d'oro come attacco, il titolo in
 * serif display e il corpo alla misura di lettura.
 * Contrasti misurati sul sabbia #f2ece0 (minimo AA 4,5:1):
 *   titolo #212C28 pieno 12,26:1 · corpo all'80% 6,83:1.
 * Le parole, le chiavi i18n e i data-testid non cambiano.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import LeadForm from '../../prelaunch/LeadForm';
import { DisplayTitle, Lede, EditorialCta } from '../../../components/editorial';

const GREEN = '#376254';

// Le categorie il cui lettore sta scegliendo un ritiro (promessa
// avviso), non imparando una pratica (promessa lettera).
const RETREAT_PROMISE_CATS = new Set(['ritiri', 'yoga']);

export function blogCluster(category) {
  if (category === 'operatori') return 'operator';
  if (RETREAT_PROMISE_CATS.has(category)) return 'retreat';
  return 'practice';
}

/* Il titolo della proposta: un gradino sotto il titolo della sezione
   che la ospita (non e' l'argomento della pagina, e' la porta). */
const TITLE = 'text-[1.55rem] sm:text-[1.8rem] lg:text-[2rem]';

export default function BlogNewsletterCTA({ category = null }) {
  const { t } = useTranslation('prelaunch');
  const cluster = blogCluster(category);

  if (cluster === 'operator') {
    return (
      <aside data-testid="blog-cta-network">
        <div aria-hidden className="gold-rule max-w-[7rem]" />
        <DisplayTitle as="h2" size="section" measure="title" className={`mt-6 ${TITLE}`}>
          {t('blogCta.opTitle', { defaultValue: 'Fai questo lavoro anche tu?' })}
        </DisplayTitle>
        <Lede size="body" className="mt-5">
          {t('blogCta.opBody', { defaultValue: 'Aurya sta costruendo la rete degli operatori olistici in Italia: ti intervistiamo, raccontiamo il tuo lavoro e ti diamo un profilo pubblico curato e visibile sui motori di ricerca. Gratuitamente.' })}
        </Lede>
        <p className="mt-7">
          <EditorialCta to="/entra-nella-rete" variant="quiet">
            {t('blogCta.opCta', { defaultValue: 'Scopri la rete' })}
          </EditorialCta>
        </p>
      </aside>
    );
  }

  const isRetreat = cluster === 'retreat';
  return (
    <aside data-testid="blog-cta-newsletter">
      <div aria-hidden className="gold-rule max-w-[7rem]" />
      <DisplayTitle as="h2" size="section" measure="title" className={`mt-6 ${TITLE}`}>
        {isRetreat
          ? t('blogCta.rtTitle', { defaultValue: 'Il ritiro giusto, quando ci sarà' })
          : t('blogCta.prTitle', { defaultValue: 'Una pratica alla volta, raccontata bene' })}
      </DisplayTitle>
      <Lede size="body" className="mt-5">
        {isRetreat
          ? t('blogCta.rtBody', { defaultValue: 'Quando apriremo le prenotazioni ti avviseremo sui ritiri che meritano, anche nella tua zona. Nel frattempo ricevi la lettera di Aurya: pratiche, storie e persone vere, ogni due settimane.' })
          : t('blogCta.prBody', { defaultValue: 'La lettera di Aurya: ogni due settimane una pratica approfondita e una persona della rete. Niente rumore, mai spam, ti disiscrivi quando vuoi.' })}
      </Lede>
      <div className="mt-7 max-w-md">
        <LeadForm
          type="traveler" compact subscribe accent={GREEN}
          context={category ? `blog_${category}` : 'blog'}
          consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere la lettera di Aurya via email.' })}
          ctaLabel={isRetreat
            ? t('blogCta.rtCta', { defaultValue: 'Tienimi aggiornato' })
            : t('blogCta.prCta', { defaultValue: 'Iscrivimi alla lettera' })}
          thanksBody={t('blogCta.thanksDoi', { defaultValue: 'Quasi fatto: controlla la tua casella e clicca il link di conferma che ti abbiamo appena inviato.' })}
        />
      </div>
    </aside>
  );
}
