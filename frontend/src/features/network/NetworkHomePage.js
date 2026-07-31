/**
 * NetworkHomePage — la home della fase rete.
 *
 * HP2 (31/7/2026) — riscritta sulla SPECIFICA DEFINITIVA del founder,
 * che supera la v3 di HP1. Sette sezioni, copy CHIUSO parola per
 * parola (si tocca solo il vestito: gerarchia, ritmo, componenti):
 *   1. HERO         la convinzione        due CTA (esplora / operatori)
 *   2. COSA TROVERAI le tre colonne       Magazine, Professionisti, Esperienze
 *   3. PERCHE'      la ragione            tre paragrafi, CTA manifesto
 *   4. DAL MAGAZINE la prova              gated sui dati
 *   5. LA RETE      il picco (salvia)     rete, non directory
 *   6. OPERATORI    l'invito              due CTA
 *   7. LA LETTERA   restare               newsletter
 *
 * Cosa e' USCITO rispetto a HP1: la sezione "Le persone" coi volti dei
 * membri. La sostituiscono la colonna "Professionisti" (sezione 2) e
 * la sezione 5, che raccontano la rete come promessa in costruzione
 * invece di mostrarla come griglia. Effetto collaterale positivo: il
 * gap segnalato su /public/network/members (nessun campo `quote` ne'
 * `category` nel payload, PersonCard costretta a ripiegare sulla
 * tagline) non e' piu' bloccante per la home. PersonCard resta nel kit
 * per /operatori e per il giorno in cui i volti torneranno.
 *
 * Il payoff di brand ("Ci si fida di qualcuno, non di qualcosa") resta
 * occhiello sopra l'H1: non si tocca.
 *
 * In fase marketplace questa home cede il posto alla directory
 * (HomeGate → RetreatsCalendarPage): quella e' un'altra pagina e non
 * viene toccata qui.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, TitleLine, Lede, ArticleCard, PillarCard, EditorialCta,
} from '../../components/editorial';

/* NOTA TECNICA — la rotta del Magazine.
   La specifica scrive /magazine, ma la rotta canonica e indicizzata e'
   /blog (sta in sitemap ed e' gia' stata spinta con IndexNow). /magazine
   ORA ESISTE come redirect (App.js), cosi' i link della specifica non
   cadono nel vuoto; da qui pero' linkiamo la canonica, perche' passare
   dal redirect costa un rimbalzo di rendering all'utente e diluisce il
   segnale interno verso l'URL che i motori conoscono.
   Il cambio di canonical /blog → /magazine e' una decisione SEO a se':
   richiede sitemap, 301 lato server e un nuovo giro di IndexNow. */
const MAGAZINE_PATH = '/blog';

/* La landing operatori ha UN solo form, con ancora #presentati.
   "Parliamone" ci porta dritto li' invece che in cima alla pagina. */
const OPERATOR_FORM_PATH = '/entra-nella-rete#presentati';

/* Il segno in testa alle tre colonne: 'emoji' e' la specifica del
   founder, 'numeral' l'alternativa editoriale (vedi la NOTA DIREZIONE
   CREATIVA in components/editorial/PillarCard.jsx). Si prova
   cambiando questa sola parola. */
const PILLAR_VARIANT = 'emoji';

/** quanti articoli in vetrina: uno grande, due piccoli */
const MAX_ARTICLES = 3;

export default function NetworkHomePage() {
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [articles, setArticles] = useState([]);

  useSeoMeta({
    title: t('nwHome.seoTitle', { defaultValue: "Aurya | Il benessere inizia dalle persone" }),
    // 155 caratteri: la promessa dell'hero, tagliata dove finisce la
    // frase e non dove finisce lo spazio.
    description: t('nwHome.seoDesc', { defaultValue: "Scegliere un professionista del benessere significa affidargli qualcosa di personale. Aurya ti fa conoscere le persone dietro le pratiche." }),
    canonicalPath: '/',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: MAX_ARTICLES } })
      .then(res => { if (mounted) setArticles(res.data?.items || []); })
      .catch(() => { /* niente articoli: la sezione non compare */ });
    return () => { mounted = false; };
  }, [lang]);

  const fmtDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return ''; }
  };
  const catLabel = (slug) => (slug ? t(`categories.${slug}`, { defaultValue: slug }) : '');

  const [lead, ...secondary] = articles;

  /* Le tre colonne in un dato solo: l'ordine e' quello della specifica
     e la terza NON ha `to`, quindi PillarCard le da' l'etichetta di
     stato al posto del link. */
  const pillars = [
    {
      id: 'magazine',
      icon: '📖',
      numeral: '01',
      title: t('nwHome.pillarMagTitle', { defaultValue: "Magazine" }),
      text: t('nwHome.pillarMagText', { defaultValue: "Guide, approfondimenti e storie per orientarti nel mondo del benessere senza promesse facili." }),
      to: MAGAZINE_PATH,
      ctaLabel: t('nwHome.pillarMagCta', { defaultValue: "Leggi gli articoli" }),
    },
    {
      id: 'professionisti',
      icon: '🌿',
      numeral: '02',
      title: t('nwHome.pillarProTitle', { defaultValue: "Professionisti" }),
      text: t('nwHome.pillarProText', { defaultValue: "Stiamo costruendo una rete di professionisti raccontati con cura, uno alla volta. Ogni profilo nascerà da una conversazione, non da un semplice modulo." }),
      to: '/operatori',
      ctaLabel: t('nwHome.pillarProCta', { defaultValue: "Scopri il progetto" }),
    },
    {
      id: 'esperienze',
      icon: '✨',
      numeral: '03',
      title: t('nwHome.pillarExpTitle', { defaultValue: "Esperienze" }),
      text: t('nwHome.pillarExpText', { defaultValue: "Ritiri, workshop ed eventi selezionati per chi desidera vivere ciò che ha scoperto." }),
      // niente `to`: la terza colonna e' una promessa, non una porta
      badge: t('nwHome.pillarExpBadge', { defaultValue: "In arrivo" }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — la convinzione ─────────────────────────────
            Sola tipografia su crema: senza la cover di una persona
            vera della rete, nessuna immagine e' meglio di una stock.
            Larghezza max-w-6xl (e non 5xl come le altre): serve a far
            stare ciascuna delle due frasi del titolo su una riga sua
            anche su desktop, che e' il senso del "due righe". */}
        {/* <section> e non <header>: il landmark banner e' gia' quello
            della shell, due banner confondono lo screen reader */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-hero-title"
                 width="max-w-6xl" className="border-b border-border/50">
          <div data-testid="hp-hero">
            <BrandPayoff tone="cream" size="xs" className="mb-6 sm:mb-8" />
            <DisplayTitle as="h1" id="hp-hero-title" size="heroLines" measure="lines">
              <TitleLine>
                {t('nwHome.heroTitleA', { defaultValue: "Il benessere non inizia da una pratica." })}
              </TitleLine>
              <TitleLine>
                {t('nwHome.heroTitleB', { defaultValue: "Inizia dalle persone." })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-7 sm:mt-9">
              {t('nwHome.heroBody', { defaultValue: "Scegliere un professionista del benessere significa affidargli qualcosa di personale. Per questo Aurya nasce per aiutarti a conoscere le persone dietro le pratiche, comprendere i diversi approcci e orientarti con maggiore consapevolezza." })}
            </Lede>
            {/* due azioni, ma di peso diverso: la prima e' la porta di
                casa (il Magazine e' l'unica cosa gia' viva), la
                seconda smista l'altro pubblico senza contendersela.
                In colonna su mobile: affiancate, "Sei un operatore?"
                finirebbe schiacciata sotto i 375px. */}
            <div className="mt-10 sm:mt-12 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to={MAGAZINE_PATH} variant="solid" data-testid="hp-hero-cta">
                {t('nwHome.heroCta', { defaultValue: "Esplora il Magazine" })}
              </EditorialCta>
              <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="hp-hero-cta-alt">
                {t('nwHome.heroCtaAlt', { defaultValue: "Sei un operatore?" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 2. COSA TROVERAI — le tre colonne ────────────────────
            Fondo carta: stacca la mappa del sito dal racconto. Le tre
            schede hanno la stessa altezza e il piede alla stessa
            quota, cosi' "In arrivo" si legge come una differenza
            voluta e non come una card rotta. */}
        <Section tone="paper" rhythm="flow" labelledBy="hp-pillars-title"
                 width="max-w-6xl">
          <div data-testid="hp-pillars">
            <DisplayTitle as="h2" id="hp-pillars-title" size="section" measure="title">
              {t('nwHome.findTitle', { defaultValue: "Cosa troverai su Aurya." })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">
              <TitleLine>
                {t('nwHome.findSubA', { defaultValue: "Non un catalogo." })}
              </TitleLine>
              <TitleLine>
                {t('nwHome.findSubB', { defaultValue: "Uno spazio per capire, prima ancora di scegliere." })}
              </TitleLine>
            </Lede>
            {/* gap-y generoso: in colonna su mobile le tre promesse
                devono leggersi come tre blocchi, non come un elenco */}
            <ul className="mt-14 grid gap-14 sm:gap-12 lg:grid-cols-3 lg:gap-10 list-none p-0">
              {/* `id` esce dallo spread: e' la chiave della lista e il
                  nostro appiglio nei test, non un attributo da versare
                  sul DOM della scheda */}
              {pillars.map(({ id, ...card }) => (
                <li key={id} data-testid={`hp-pillar-${id}`}>
                  <PillarCard variant={PILLAR_VARIANT} {...card} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 3. PERCHE' ESISTE AURYA — la ragione ─────────────────
            Tre paragrafi in scala discendente di peso: il primo e'
            la tesi e sta al corpo del lede, gli altri due argomentano.
            L'occhio capisce dove comincia il ragionamento senza che
            nessuno gli metta un grassetto davanti. */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-why-title">
          <div data-testid="hp-why">
            <DisplayTitle as="h2" id="hp-why-title" size="section" measure="tight">
              {t('nwHome.whyTitle', { defaultValue: "Perché esiste Aurya?" })}
            </DisplayTitle>
            <Lede size="lead" className="mt-8">
              {t('nwHome.whyP1', { defaultValue: "Internet rende facile trovare informazioni. Molto più difficile è capire di chi fidarsi." })}
            </Lede>
            <Lede size="body" className="mt-6">
              {t('nwHome.whyP2', { defaultValue: "Ogni giorno migliaia di persone cercano un professionista, leggono recensioni sparse, visitano decine di siti e finiscono per scegliere quasi alla cieca." })}
            </Lede>
            <Lede size="body" className="mt-6">
              {t('nwHome.whyP3', { defaultValue: "Aurya nasce per cambiare questo. Vogliamo costruire uno spazio dove contenuti, persone ed esperienze possano essere conosciuti con il tempo e l'attenzione che meritano." })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/manifesto" variant="quiet" data-testid="hp-why-cta">
                {t('nwHome.whyCta', { defaultValue: "Leggi il Manifesto" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 4. DAL MAGAZINE — la prova ───────────────────────────
            Uno grande, due piccoli. Zero articoli, zero sezione: una
            griglia vuota direbbe "non abbiamo ancora niente" molto
            piu' forte del silenzio. */}
        {articles.length > 0 && (
          <Section tone="paper" rhythm="flow" labelledBy="hp-mag-title"
                   width="max-w-6xl">
            <div data-testid="hp-magazine">
              <DisplayTitle as="h2" id="hp-mag-title" size="section" measure="title">
                {t('nwHome.magTitle', { defaultValue: "Dal Magazine" })}
              </DisplayTitle>
              <Lede size="body" className="mt-6">
                {t('nwHome.magSub', { defaultValue: "Capire è il primo passo per scegliere bene." })}
              </Lede>
              <div className="mt-14 grid gap-12 lg:grid-cols-12 lg:gap-14">
                <div className="lg:col-span-7">
                  <ArticleCard article={lead} variant="lead"
                               category={catLabel(lead.category)}
                               date={fmtDate(lead.published_at)} />
                </div>
                {secondary.length > 0 && (
                  <div className="lg:col-span-5 grid gap-8 sm:grid-cols-2 lg:grid-cols-1 lg:content-start lg:gap-10 lg:pt-2">
                    {secondary.map(a => (
                      <ArticleCard key={a.slug} article={a} variant="compact"
                                   category={catLabel(a.category)}
                                   date={fmtDate(a.published_at)} />
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-14">
                <EditorialCta to={MAGAZINE_PATH} variant="quiet" data-testid="hp-mag-cta">
                  {t('nwHome.magCta', { defaultValue: "Tutti gli articoli" })}
                </EditorialCta>
              </div>
            </div>
          </Section>
        )}

        {/* ── 5. LA RETE — il picco ────────────────────────────────
            Unico cambio di fondo della pagina (salvia), messo dove la
            promessa e' piu' alta. Qui NON si nomina niente di
            commerciale: solo presenza. */}
        <Section tone="sage" rhythm="screen" labelledBy="hp-network-title">
          <div data-testid="hp-network">
            <DisplayTitle as="h2" id="hp-network-title" size="section" measure="lines">
              <TitleLine>
                {t('nwHome.netTitleA', { defaultValue: "Stiamo costruendo una rete." })}
              </TitleLine>
              <TitleLine>
                {t('nwHome.netTitleB', { defaultValue: "Non una directory." })}
              </TitleLine>
            </DisplayTitle>
            {/* tone inherit: sul salvia l'opacita' di default mangia
                contrasto, e il crema all'80% scenderebbe sotto AA */}
            <Lede size="body" tone="inherit" className="mt-8 opacity-90">
              {t('nwHome.netBody', { defaultValue: "Ogni professionista entrerà in Aurya attraverso un percorso di conoscenza reciproca. Prima ascoltiamo la sua storia. Poi la raccontiamo. Infine costruiamo insieme un profilo che nel tempo diventerà il punto di riferimento della sua presenza su Aurya." })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/entra-nella-rete" variant="light" data-testid="hp-network-cta">
                {t('nwHome.netCta', { defaultValue: "Scopri come entrare nella rete" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 6. PER GLI OPERATORI — l'invito ──────────────────────
            L'unica sezione con due CTA oltre all'hero: qui la doppia
            porta ha senso, perche' i due gesti sono davvero diversi
            (candidarsi / farsi due domande prima). */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-pros-title">
          <div data-testid="hp-pros">
            <p className="eyebrow mb-6">
              {t('nwHome.prosEyebrow', { defaultValue: "Per gli operatori" })}
            </p>
            <DisplayTitle as="h2" id="hp-pros-title" size="section" measure="tight">
              {t('nwHome.prosTitle', { defaultValue: "Il tuo lavoro merita più di un profilo." })}
            </DisplayTitle>
            <Lede size="lead" className="mt-8">
              {t('nwHome.prosP1', { defaultValue: "Aurya nasce per dare ai professionisti del benessere uno spazio che cresca insieme alla loro attività." })}
            </Lede>
            <Lede size="body" className="mt-6">
              {t('nwHome.prosP2', { defaultValue: "Oggi significa raccontare il tuo percorso. Domani significherà anche ricevere richieste, pubblicare servizi, organizzare esperienze, raccogliere recensioni e gestire tutto da un unico luogo." })}
            </Lede>
            <Lede size="body" className="mt-6">
              {t('nwHome.prosP3', { defaultValue: "Stiamo costruendo tutto questo insieme ai primi professionisti che scelgono di far parte della rete." })}
            </Lede>
            <div className="mt-10 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/entra-nella-rete" variant="solid" data-testid="hp-pros-cta">
                {t('nwHome.prosCta', { defaultValue: "Entra tra i primi operatori" })}
              </EditorialCta>
              <EditorialCta to={OPERATOR_FORM_PATH} variant="quiet" data-testid="hp-pros-cta-alt">
                {t('nwHome.prosCtaAlt', { defaultValue: "Parliamone" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. LA LETTERA — restare ──────────────────────────────
            Il testo e' fatto di frasi cortissime: la misura di riga qui
            e' stretta apposta (max-w-[30ch]), cosi' le frasi cadono
            una per riga e il ritmo si vede invece di doverlo
            immaginare. La chiusa scende di tono: e' il commento, non
            l'elenco. */}
        <Section tone="paper" rhythm="screen" labelledBy="hp-letter-title">
          <div data-testid="hp-letter">
            <DisplayTitle as="h2" id="hp-letter-title" size="section" measure="tight">
              {t('nwHome.letterTitle', { defaultValue: "Ricevi la Lettera di Aurya." })}
            </DisplayTitle>
            <Lede size="lead" className="mt-8 max-w-[30ch]">
              {t('nwHome.letterBody', { defaultValue: "Una volta ogni tanto. Una persona da conoscere. Una pratica da capire. Un luogo da scoprire." })}
            </Lede>
            <Lede size="body" tone="quiet" className="mt-5 max-w-[30ch]">
              {t('nwHome.letterClose', { defaultValue: "Niente rumore. Solo ciò che vale il tuo tempo." })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/newsletter" variant="quiet" data-testid="hp-letter-cta">
                {t('nwHome.letterCta', { defaultValue: "Iscriviti" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
