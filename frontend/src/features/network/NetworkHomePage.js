/**
 * NetworkHomePage — la home della fase rete (RT2, piano sito-rete).
 *
 * Identita' e direzione in dieci secondi per chi arriva da Instagram:
 *   1. hero col posizionamento in una frase + CTA newsletter
 *   2. il manifesto in tre righe → /manifesto
 *   3. gli ultimi 3 articoli del Magazine (valore vero, subito)
 *   4. blocco operatori → /entra-nella-rete
 *   5. fascia newsletter
 * I blocchi si sostituiscono con le fasi, l'URL mai: in fase
 * marketplace questa home cede il posto alla directory (HomeGate).
 * Il blocco "intervista in evidenza" arriva con RT3, quando esistono
 * i primi membri della rete.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Mail, Users, BookOpen } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';

export default function NetworkHomePage() {
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [articles, setArticles] = useState([]);

  useSeoMeta({
    title: t('nwHome.seoTitle', { defaultValue: 'Aurya | La rete del benessere olistico in Italia' }),
    description: t('nwHome.seoDesc', { defaultValue: 'Operatori olistici veri, raccontati attraverso interviste. Storie, pratiche e persone del benessere in Italia.' }),
    canonicalPath: '/',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: 3 } })
      .then(res => { if (mounted) setArticles(res.data?.items || []); })
      .catch(() => { /* il blocco articoli semplicemente non compare */ });
    return () => { mounted = false; };
  }, [lang]);

  const fmtDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return ''; }
  };

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        {/* 1 — hero: posizionamento in una frase, non uno slogan */}
        <header className="relative text-white overflow-hidden">
          <img aria-hidden src="/media/hero-blog.webp" alt="" fetchPriority="high"
               className="absolute inset-0 w-full h-full object-cover" />
          <div aria-hidden className="absolute inset-0 pointer-events-none bg-gradient-to-b from-[#14231d]/85 via-[#14231d]/60 to-[#0e1a15]/90" />
          <div className="relative max-w-4xl mx-auto px-4 py-20 md:py-28 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-xs md:text-sm text-[#ecd9a8] mb-4 select-none text-hero-shadow">Connect · Heal · Grow</p>
            <h1 className="font-display text-3xl md:text-5xl font-semibold text-hero-shadow max-w-3xl mx-auto">
              {t('nwHome.heroTitle', { defaultValue: 'Il benessere olistico in Italia ha dei volti. Noi li raccontiamo.' })}
            </h1>
            <p className="text-white/90 mt-4 text-lg leading-relaxed max-w-2xl mx-auto text-hero-shadow">
              {t('nwHome.heroSub', { defaultValue: 'Aurya è la rete degli operatori olistici scelti uno a uno: interviste vere, pratiche serie, storie che meritano fiducia.' })}
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link to="/newsletter" className="inline-flex items-center gap-2 rounded-full bg-white text-[#376254] px-6 py-3 text-sm font-semibold hover:bg-gray-100 shadow-lg">
                <Mail className="h-4 w-4" aria-hidden />
                {t('nwHome.heroCta', { defaultValue: 'Ricevi la lettera di Aurya' })}
              </Link>
              <Link to="/blog" className="inline-flex items-center gap-2 rounded-full border border-white/40 bg-black/20 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm hover:bg-black/35">
                <BookOpen className="h-4 w-4" aria-hidden />
                {t('nwHome.heroCta2', { defaultValue: 'Leggi il Magazine' })}
              </Link>
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-12 space-y-14">
          {/* 2 — il manifesto in tre righe */}
          <section className="text-center max-w-2xl mx-auto">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8a7440]">
              {t('nwHome.manifestoEyebrow', { defaultValue: 'Il nostro manifesto' })}
            </p>
            <p className="font-heading text-xl md:text-2xl text-foreground mt-3 leading-relaxed">
              {t('nwHome.manifestoLines', { defaultValue: 'Crediamo che dietro ogni pratica seria ci sia una persona che merita di essere conosciuta. Per questo costruiamo una rete, non un elenco: operatori scelti, intervistati e raccontati con cura.' })}
            </p>
            <Link to="/manifesto" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-[#376254] hover:underline">
              {t('nwHome.manifestoLink', { defaultValue: 'Leggi il manifesto' })} <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </section>

          {/* 3 — gli ultimi articoli del Magazine */}
          {articles.length > 0 && (
            <section>
              <div className="flex items-end justify-between mb-5">
                <h2 className="font-heading text-2xl font-semibold text-foreground">
                  {t('nwHome.articlesTitle', { defaultValue: 'Dal Magazine' })}
                </h2>
                <Link to="/blog" className="text-sm font-semibold text-[#376254] hover:underline inline-flex items-center gap-1">
                  {t('nwHome.articlesAll', { defaultValue: 'Tutti gli articoli' })} <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                {articles.map(a => (
                  <Link key={a.slug} to={`/blog/${a.slug}`}
                        className="group rounded-2xl border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow flex flex-col">
                    {a.featured_image_url && (
                      <img src={a.featured_image_url} alt="" loading="lazy"
                           className="h-36 w-full object-cover group-hover:brightness-95 transition" />
                    )}
                    <div className="p-4 flex flex-col flex-1">
                      <p className="text-[11px] text-gray-400">{fmtDate(a.published_at)}</p>
                      <h3 className="font-heading text-sm font-semibold text-foreground mt-1 leading-snug">
                        {a.title}
                      </h3>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* 4 — blocco operatori: la rete */}
          <section className="rounded-3xl bg-gradient-sidebar text-white p-8 md:p-10 overflow-hidden relative">
            <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
              background: 'radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
            }} />
            <div className="relative md:flex md:items-center md:justify-between md:gap-8">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#d6c49a]">
                  {t('nwHome.networkEyebrow', { defaultValue: 'Per gli operatori' })}
                </p>
                <h2 className="font-heading text-2xl font-semibold mt-2">
                  {t('nwHome.networkTitle', { defaultValue: 'La rete cresce una persona alla volta' })}
                </h2>
                <p className="text-white/85 mt-2 max-w-xl leading-relaxed">
                  {t('nwHome.networkBody', { defaultValue: 'Ti intervistiamo, raccontiamo il tuo lavoro e ti diamo un profilo pubblico curato, visibile sui motori di ricerca e sui nostri canali. Gratuitamente: chiediamo solo di condividere la tua storia.' })}
                </p>
              </div>
              <div className="mt-6 md:mt-0 shrink-0">
                <Link to="/entra-nella-rete" className="inline-flex items-center gap-2 rounded-full bg-white text-[#376254] px-6 py-3 text-sm font-semibold hover:bg-gray-100">
                  <Users className="h-4 w-4" aria-hidden />
                  {t('nwHome.networkCta', { defaultValue: 'Entra nella rete' })}
                </Link>
              </div>
            </div>
          </section>

          {/* 5 — fascia newsletter con promessa concreta */}
          <section className="rounded-3xl border border-border bg-card p-8 text-center">
            <Mail className="h-7 w-7 mx-auto text-[#8a7440]" aria-hidden />
            <h2 className="font-heading text-2xl font-semibold text-foreground mt-3">
              {t('nwHome.nlTitle', { defaultValue: 'La lettera di Aurya' })}
            </h2>
            <p className="text-muted-foreground mt-2 max-w-xl mx-auto leading-relaxed">
              {t('nwHome.nlBody', { defaultValue: 'Pratiche, storie e persone del benessere olistico, direttamente nella tua casella. Niente rumore, niente fretta.' })}
            </p>
            <Link to="/newsletter" className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-[#376254] text-white px-6 py-2.5 text-sm font-semibold hover:bg-[#2c4f43]">
              {t('nwHome.nlCta', { defaultValue: 'Iscriviti' })} <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </section>
        </main>
      </div>
    </MarketplaceShell>
  );
}
