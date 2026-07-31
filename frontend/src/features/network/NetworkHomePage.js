/**
 * NetworkHomePage — la home della fase rete.
 *
 * HP1 (31/7/2026) — riscritta sulla direzione di brand v3
 * (docs/BRAND_HOME_AURYA_2026-07.md). Sette battute, una schermata
 * ciascuna, in alternanza prova/pensiero:
 *   1. HERO        la convinzione        (sola tipografia, UNA cta)
 *   2. LE PERSONE  la prova              (immagini, gated sui dati)
 *   3. IL TEMPO    il criterio invisibile(sola tipografia, NESSUNA cta)
 *   4. IL MAGAZINE lo sguardo            (immagini, gated sui dati)
 *   5. IL MANIFESTO il picco             (fondo salvia, una frase)
 *   6. LA LETTERA  restare
 *   7. OPERATORI   l'invito
 *
 * Copy e ordine sono CHIUSI: si toccano solo su nuova direzione.
 * Il vestito (tipografia, ritmo, componenti) vive in
 * components/editorial, cosi' manifesto e magazine potranno
 * riusarlo senza copiare classi.
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
  Section, DisplayTitle, Lede, PersonCard, ArticleCard, EditorialCta,
} from '../../components/editorial';

/** quante persone al massimo: tre volti sono una prova, sei un elenco */
const MAX_PEOPLE = 3;

export default function NetworkHomePage() {
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [articles, setArticles] = useState([]);
  const [members, setMembers] = useState([]);

  useSeoMeta({
    title: t('nwHome.seoTitle', { defaultValue: 'Aurya | Le persone del benessere in Italia' }),
    description: t('nwHome.seoDesc', { defaultValue: 'Non si sceglie una disciplina. Si sceglie una persona. Aurya ti fa conoscere chi pratica il benessere, prima che tu decida.' }),
    canonicalPath: '/',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: 3 } })
      .then(res => { if (mounted) setArticles(res.data?.items || []); })
      .catch(() => { /* niente articoli: la sezione non compare */ });
    return () => { mounted = false; };
  }, [lang]);

  useEffect(() => {
    let mounted = true;
    api.get('/public/network/members')
      .then(res => {
        if (!mounted) return;
        const items = res.data?.items || [];
        // chi ha un volto va davanti: la sezione e' una prova, e la
        // prova si vede. L'ordine dell'API (per nome) resta stabile
        // dentro i due gruppi.
        const withPhoto = items.filter(m => m.portrait_url || m.cover_url);
        const rest = items.filter(m => !(m.portrait_url || m.cover_url));
        setMembers([...withPhoto, ...rest].slice(0, MAX_PEOPLE));
      })
      .catch(() => { /* niente membri: la sezione non compare */ });
    return () => { mounted = false; };
  }, []);

  const fmtDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return ''; }
  };
  const catLabel = (slug) => (slug ? t(`categories.${slug}`, { defaultValue: slug }) : '');

  const [lead, ...secondary] = articles;

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — la convinzione ─────────────────────────────
            Sola tipografia su crema: senza la cover di una persona
            vera della rete, nessuna immagine e' meglio di una stock
            (BRAND_HOME §6.5). L'immagine si aggiunge qui il giorno
            in cui un membro ha una cover sua. */}
        {/* <section> e non <header>: il landmark banner e' gia' quello
            della shell, due banner confondono lo screen reader */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-hero-title"
                 className="border-b border-border/50">
          <div data-testid="hp-hero">
            <BrandPayoff tone="cream" size="xs" className="mb-6 sm:mb-8" />
            <DisplayTitle as="h1" id="hp-hero-title" size="hero" measure="tight">
              {t('nwHome.heroTitle', { defaultValue: 'Non si sceglie una disciplina. Si sceglie una persona.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7 sm:mt-9">
              {t('nwHome.heroSub', { defaultValue: 'Qui le conosci prima di decidere.' })}
            </Lede>
            {/* una sola azione: due bottoni sono un'esitazione */}
            <div className="mt-10 sm:mt-12">
              <EditorialCta to="/operatori" variant="solid" data-testid="hp-hero-cta">
                {t('nwHome.heroCta', { defaultValue: 'Conosci le persone' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 2. LE PERSONE — la prova ─────────────────────────────
            Niente griglie vuote: senza membri la sezione non esiste. */}
        {members.length > 0 && (
          <Section tone="paper" rhythm="flow" labelledBy="hp-people-title"
                   width="max-w-6xl">
            <div data-testid="hp-people">
              <DisplayTitle as="h2" id="hp-people-title" size="section" measure="title">
                {t('nwHome.peopleTitle', { defaultValue: 'Si sceglie meglio quando si sa chi si ha davanti.' })}
              </DisplayTitle>
              <Lede size="body" className="mt-6">
                {t('nwHome.peopleSub', { defaultValue: 'Chi sono, come lavorano, per chi lo fanno.' })}
              </Lede>
              <div className={`mt-14 grid gap-10 sm:gap-8 ${members.length === 1 ? 'sm:max-w-sm' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
                {members.map(m => (
                  <PersonCard key={m.slug} person={m} />
                ))}
              </div>
              <div className="mt-12">
                <EditorialCta to="/operatori" variant="quiet">
                  {t('nwHome.peopleCta', { defaultValue: 'Tutte le persone' })}
                </EditorialCta>
              </div>
            </div>
          </Section>
        )}

        {/* ── 3. IL TEMPO — il criterio invisibile ─────────────────
            NESSUNA CTA: voluto. Una pagina che non chiede sempre
            qualcosa sembra un brand, non un imbuto. */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-time-title">
          <div data-testid="hp-time">
            <DisplayTitle as="h2" id="hp-time-title" size="section" measure="tight">
              {t('nwHome.timeTitle', { defaultValue: 'Per conoscere qualcuno ci vuole tempo.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-8">
              {t('nwHome.timeBody', { defaultValue: 'Ce lo prendiamo, una persona alla volta. Facciamo domande, ascoltiamo e scriviamo quello che abbiamo capito. Anche i limiti.' })}
            </Lede>
            <Lede size="aside" tone="quiet" className="mt-8">
              {t('nwHome.timeNote', { defaultValue: 'Quando un profilo nasce così, lo trovi segnato.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 4. IL MAGAZINE — lo sguardo ──────────────────────────
            Uno grande, due piccoli. Zero articoli, zero sezione. */}
        {articles.length > 0 && (
          <Section tone="paper" rhythm="flow" labelledBy="hp-mag-title"
                   width="max-w-6xl">
            <div data-testid="hp-magazine">
              <DisplayTitle as="h2" id="hp-mag-title" size="section" measure="title">
                {t('nwHome.magTitle', { defaultValue: 'Le cose serie vanno spiegate.' })}
              </DisplayTitle>
              <Lede size="body" className="mt-6">
                {t('nwHome.magSub', { defaultValue: 'Pratiche, luoghi e persone. Senza scorciatoie.' })}
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
                <EditorialCta to="/blog" variant="quiet">
                  {t('nwHome.magCta', { defaultValue: 'Il Magazine' })}
                </EditorialCta>
              </div>
            </div>
          </Section>
        )}

        {/* ── 5. IL MANIFESTO — il picco ───────────────────────────
            Fondo salvia: e' l'unico cambio di fondo della pagina, e
            arriva dove serve il picco emotivo. Il crema piu' scuro
            non staccava abbastanza dal resto. */}
        <Section tone="sage" rhythm="screen" labelledBy="hp-manifesto-title"
                 innerClassName="text-center flex flex-col items-center">
          <div data-testid="hp-manifesto" className="flex flex-col items-center">
            <DisplayTitle as="h2" id="hp-manifesto-title" size="manifesto" measure="wide"
                          className="mx-auto">
              {t('nwHome.manifestoLine', { defaultValue: 'Il benessere è una questione di persone, non di promesse.' })}
            </DisplayTitle>
            <Lede size="aside" tone="quiet" className="mt-12 mx-auto">
              {t('nwHome.manifestoWhisper', { defaultValue: 'Col tempo qui potrai anche prenotare. Prima vogliamo che tu sappia con chi.' })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/manifesto" variant="light">
                {t('nwHome.manifestoCta', { defaultValue: 'Il manifesto' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 6. LA LETTERA — restare ────────────────────────────
            NOTA DIREZIONE CREATIVA: le battute 6 e 7 hanno la stessa
            forma esatta (titolo, riga, invito sottovoce) e stesso
            fondo: dopo il picco della salvia il finale scende in
            piano. Proposta per la prossima passata di copy: dare alla
            7 una forma diversa, per esempio la domanda che si fa a un
            operatore ("Come lavori?") messa in bocca a noi, cosi' la
            chiusura cambia registro invece di ripeterlo. Qui resta il
            testo approvato. */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-letter-title"
                 className="border-b border-border/50">
          <div data-testid="hp-letter">
            <DisplayTitle as="h2" id="hp-letter-title" size="section" measure="tight">
              {t('nwHome.letterTitle', { defaultValue: 'Ogni tanto scriviamo.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-7">
              {t('nwHome.letterSub', { defaultValue: 'Una persona da conoscere, una pratica da capire, un posto dove andare.' })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/newsletter" variant="quiet">
                {t('nwHome.letterCta', { defaultValue: 'Ricevi la lettera' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. PER GLI OPERATORI — l'invito ──────────────────── */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-pros-title">
          <div data-testid="hp-pros">
            <p className="eyebrow mb-6">
              {t('nwHome.prosEyebrow', { defaultValue: 'Per gli operatori' })}
            </p>
            <DisplayTitle as="h2" id="hp-pros-title" size="section" measure="tight">
              {t('nwHome.prosTitle', { defaultValue: 'Raccontaci come lavori.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-7">
              {t('nwHome.prosBody', { defaultValue: 'Ti facciamo qualche domanda. Ascoltiamo. Poi lo scriviamo con le tue parole.' })}
            </Lede>
            <div className="mt-10">
              <EditorialCta to="/entra-nella-rete" variant="quiet">
                {t('nwHome.prosCta', { defaultValue: 'Parliamone' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
