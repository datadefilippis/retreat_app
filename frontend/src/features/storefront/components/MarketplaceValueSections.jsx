/**
 * MarketplaceValueSections — AN1: l'anima di Aurya sulla home.
 *
 * Tre sezioni sotto il calendario (docs/BRAND_AURYA.md):
 *   1. Come funziona — i 4 passi (scegli → caparra → vivi → recensisci)
 *   2. Perché Aurya — le 4 promesse (recensioni verificate, caparra
 *      protetta, Passaporto, operatori italiani)
 *   3. Sei un organizzatore? — il CTA che su mobile spariva dall'header
 *
 * Copy in landings.json (brandHome.*) ×4 lingue. Solo sulla home senza
 * filtri attivi: chi sta già cercando non va interrotto.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Compass, ShieldCheck, Ticket, MessageSquareHeart, BadgeCheck,
  Wallet, BookUser, MapPin, ArrowRight,
} from 'lucide-react';

const HOW_STEPS = [
  { icon: Compass, t: 'brandHome.how1t', b: 'brandHome.how1b' },
  { icon: Wallet, t: 'brandHome.how2t', b: 'brandHome.how2b' },
  { icon: Ticket, t: 'brandHome.how3t', b: 'brandHome.how3b' },
  { icon: MessageSquareHeart, t: 'brandHome.how4t', b: 'brandHome.how4b' },
];

const WHY_ITEMS = [
  { icon: BadgeCheck, t: 'brandHome.why1t', b: 'brandHome.why1b' },
  { icon: ShieldCheck, t: 'brandHome.why2t', b: 'brandHome.why2b' },
  { icon: BookUser, t: 'brandHome.why3t', b: 'brandHome.why3b' },
  { icon: MapPin, t: 'brandHome.why4t', b: 'brandHome.why4b' },
];

export default function MarketplaceValueSections() {
  const { t } = useTranslation('landings');

  return (
    <div className="border-t border-border bg-white">
      <div className="max-w-6xl mx-auto px-4 py-14 space-y-14">

        {/* Come funziona */}
        <section aria-labelledby="how-title">
<p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#8a7440] mb-2 select-none text-center">Connect · Heal · Grow</p>
          <h2 id="how-title" className="font-display text-2xl md:text-3xl font-bold text-foreground text-center">
            {t('brandHome.howTitle')}
          </h2>
          <div aria-hidden className="gold-rule max-w-xs mx-auto mt-4" />
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {HOW_STEPS.map((s, i) => (
              <div key={s.t} className="card-lift relative rounded-2xl border border-[#8a7440]/20 bg-card p-6 shadow-sm">
                <span aria-hidden className="absolute -top-3.5 left-6 h-8 w-8 rounded-full bg-gradient-to-br from-[#8a7440] to-[#6d5a30] text-[#f6f3ec] text-sm font-bold flex items-center justify-center shadow-md ring-2 ring-[#f6f3ec]">
                  {i + 1}
                </span>
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#376254]/10 mt-2">
                  <s.icon className="h-6 w-6 text-[#376254]" aria-hidden />
                </span>
                <h3 className="font-heading font-semibold text-foreground mt-4">{t(s.t)}</h3>
                <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">{t(s.b)}</p>
              </div>
            ))}
          </div>
          <p className="text-center mt-6">
            <Link to="/come-funziona" className="text-sm font-semibold text-[#376254] hover:underline">
              {t('brandHome.howTitle')} <ArrowRight className="inline h-3.5 w-3.5" aria-hidden />
            </Link>
          </p>
        </section>

        {/* Perché Aurya */}
        <section aria-labelledby="why-title" className="rounded-3xl bg-gradient-sidebar text-white p-8 md:p-12 relative overflow-hidden">
          <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
          }} />
          <div className="relative">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-2 select-none text-center">Connect · Heal · Grow</p>
            <h2 id="why-title" className="font-display text-2xl md:text-3xl font-bold text-center">
              {t('brandHome.whyTitle')}
            </h2>
            <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
              {WHY_ITEMS.map((w) => (
                <div key={w.t} className="text-center sm:text-left">
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-[#d6c49a]/50 bg-white/5">
                    <w.icon className="h-6 w-6 text-[#ecd9a8]" aria-hidden />
                  </span>
                  <h3 className="font-heading font-semibold mt-3">{t(w.t)}</h3>
                  <p className="text-sm text-white/75 mt-1.5 leading-relaxed">{t(w.b)}</p>
                </div>
              ))}
            </div>
            <p className="text-center mt-8">
              <Link to="/chi-siamo" className="inline-flex items-center gap-1.5 rounded-full border border-white/40 px-5 py-2 text-sm font-semibold hover:bg-white/10">
                {t('aboutPage.title')} <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </p>
          </div>
        </section>

        {/* Sei un organizzatore? */}
        <section aria-labelledby="org-title" className="aura-corner rounded-3xl border border-[#C97B5D]/30 bg-gradient-to-br from-[#C97B5D]/10 via-[#f6f3ec] to-[#f6f3ec] p-6 md:p-10 flex flex-col md:flex-row md:items-center gap-4 shadow-sm">
          <div className="flex-1">
            <h2 id="org-title" className="font-display text-xl md:text-2xl font-bold text-foreground">
              {t('brandHome.orgTitle')}
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">{t('brandHome.orgBody')}</p>
          </div>
          <Link
            to="/inizia"
            className="shrink-0 inline-flex items-center justify-center gap-1.5 rounded-full bg-[#C97B5D] text-white px-7 py-3 text-sm font-semibold hover:bg-[#b56a4e] shadow-lg shadow-[#C97B5D]/30 transition-transform hover:-translate-y-0.5"
          >
            {t('brandHome.orgCta')} <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </section>
      </div>
    </div>
  );
}
