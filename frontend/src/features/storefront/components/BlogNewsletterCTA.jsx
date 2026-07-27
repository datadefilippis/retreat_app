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
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, Users, ArrowRight } from 'lucide-react';
import LeadForm from '../../prelaunch/LeadForm';

const GREEN = '#376254';
const GOLD = '#8a7440';

// Le categorie il cui lettore sta scegliendo un ritiro (promessa
// avviso), non imparando una pratica (promessa lettera).
const RETREAT_PROMISE_CATS = new Set(['ritiri', 'yoga']);

export function blogCluster(category) {
  if (category === 'operatori') return 'operator';
  if (RETREAT_PROMISE_CATS.has(category)) return 'retreat';
  return 'practice';
}

export default function BlogNewsletterCTA({ category = null }) {
  const { t } = useTranslation('prelaunch');
  const cluster = blogCluster(category);

  if (cluster === 'operator') {
    return (
      <aside className="mt-10 rounded-2xl border border-[#8a7440]/25 bg-[#8a7440]/5 p-6"
             data-testid="blog-cta-network">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                style={{ backgroundColor: `${GOLD}22` }}>
            <Users className="h-4.5 w-4.5" style={{ color: GOLD }} aria-hidden />
          </span>
          <div className="flex-1">
            <p className="font-heading font-semibold text-foreground">
              {t('blogCta.opTitle', { defaultValue: 'Fai questo lavoro anche tu?' })}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('blogCta.opBody', { defaultValue: 'Aurya sta costruendo la rete degli operatori olistici in Italia: ti intervistiamo, raccontiamo il tuo lavoro e ti diamo un profilo pubblico curato e visibile sui motori di ricerca. Gratuitamente.' })}
            </p>
            <Link to="/entra-nella-rete"
                  className="mt-3 inline-flex items-center gap-1.5 rounded-full px-5 py-2.5 text-sm font-semibold text-white"
                  style={{ backgroundColor: GOLD }}>
              {t('blogCta.opCta', { defaultValue: 'Scopri la rete' })}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </div>
      </aside>
    );
  }

  const isRetreat = cluster === 'retreat';
  return (
    <aside className="mt-10 rounded-2xl border border-[#376254]/25 bg-[#376254]/5 p-6"
           data-testid="blog-cta-newsletter">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: `${GREEN}22` }}>
          <Mail className="h-4.5 w-4.5" style={{ color: GREEN }} aria-hidden />
        </span>
        <div className="flex-1">
          <p className="font-heading font-semibold text-foreground">
            {isRetreat
              ? t('blogCta.rtTitle', { defaultValue: 'Il ritiro giusto, quando ci sarà' })
              : t('blogCta.prTitle', { defaultValue: 'Una pratica alla volta, raccontata bene' })}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {isRetreat
              ? t('blogCta.rtBody', { defaultValue: 'Quando apriremo le prenotazioni ti avviseremo sui ritiri che meritano, anche nella tua zona. Nel frattempo ricevi la lettera di Aurya: pratiche, storie e persone vere, ogni due settimane.' })
              : t('blogCta.prBody', { defaultValue: 'La lettera di Aurya: ogni due settimane una pratica approfondita e una persona della rete. Niente rumore, mai spam, ti disiscrivi quando vuoi.' })}
          </p>
          <div className="mt-4 max-w-md">
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
        </div>
      </div>
    </aside>
  );
}
