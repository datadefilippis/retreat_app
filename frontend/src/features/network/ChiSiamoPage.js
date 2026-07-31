/**
 * ChiSiamoPage — /chi-siamo (SW3, redesign sul Blueprint).
 *
 * Il Manifesto e' la posizione, Chi siamo sono le persone. Due domande
 * diverse, due pagine: qui non si ridice la teoria, la si indica.
 *
 * Cinque battute, e la pagina finisce presto (e' un incontro, non un
 * curriculum):
 *   1. APERTURA      le tre negazioni della landing operatori tornano
 *                    qui come titolo, poi una riga su chi siamo
 *   2. LA STORIA     l'incontro di due mestieri, in prima persona
 *                    plurale, col materiale reale e niente altro
 *   3. LE PERSONE    Valentina e Davide, due ritratti brevi, la foto
 *                    vera grande e non filtrata
 *   4. COSA CI GUIDA la teoria citata (non riscritta) e il rimando al
 *                    manifesto: l'unica ancora verde della pagina
 *   5. CHIUSURA      doppia CTA discreta: il manifesto e la mail
 *
 * Il materiale dei ritratti e' quello verificato dei fondatori (le
 * chiavi aboutPage.faces* nate con la pagina vecchia): qui e' detto
 * nella voce v3, ma non aggiunge un solo fatto che non fosse gia'
 * scritto. La foto e l'alt sono gli stessi di /manifesto e della
 * landing operatori: una sola immagine vera, tre superfici.
 *
 * Fondi: crema, sabbia, bianco, VERDE, crema. Una sola ancora tonale
 * (movimento 4), come vuole il Blueprint. Contrasti misurati sul
 * salvia #2f5749: crema piena 7,28:1, oro dell'occhiello chiaro
 * 4,74:1. Minimo AA: 4,5:1. Movimento: solo il reveal del kit.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, TitleLine, Lede, Quote, EditorialCta,
} from '../../components/editorial';

/* La mail vera del contatto: una sola costante, cosi' la chiusura e i
   test guardano lo stesso posto. */
const CONTACT_MAIL = 'info@aurya.life';

export default function ChiSiamoPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('chiSiamo.seoTitle', { defaultValue: 'Chi siamo | Aurya' }),
    // 153 caratteri: chi siamo e cosa facciamo, senza aggettivi. Taglio a 158.
    description: t('chiSiamo.seoDesc', { defaultValue: 'Siamo Valentina e Davide, la coppia dietro Aurya. Andiamo a conoscere chi lavora nel benessere, una persona alla volta, e raccontiamo quello che vediamo.' }),
    canonicalPath: '/chi-siamo',
  });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA — le tre negazioni ───────────────────────
            Sono tre FRASI, non un a-capo estetico: ognuna e' una
            <TitleLine>, cosi' in ogni lingua restano tre righe. Lo
            stesso attacco della landing operatori, perche' e' vero in
            entrambi i posti; qui pero' finisce sul nostro nome, non
            sulla proposta. Il payoff torna sotto come eco. */}
        <Section tone="cream" rhythm="hero" labelledBy="cs-open-title">
          <div data-testid="cs-open">
            <p className="eyebrow mb-5">
              {t('chiSiamo.eyebrow', { defaultValue: 'Chi siamo' })}
            </p>
            <DisplayTitle as="h1" id="cs-open-title" size="heroLines" measure="lines">
              <TitleLine>
                {t('chiSiamo.line1', { defaultValue: "Non siamo un'agenzia." })}
              </TitleLine>
              <TitleLine>
                {t('chiSiamo.line2', { defaultValue: 'Non siamo un software.' })}
              </TitleLine>
              <TitleLine>
                {t('chiSiamo.line3', { defaultValue: 'Non siamo una directory.' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-8">
              {t('chiSiamo.lead', { defaultValue: 'Siamo Valentina e Davide. Andiamo a conoscere chi lavora nel benessere, una persona alla volta, e scriviamo quello che abbiamo capito.' })}
            </Lede>
            <BrandPayoff tone="cream" size="sm" className="mt-9" />
          </div>
        </Section>

        {/* ── 2. LA STORIA — due mestieri che si incontrano ────────
            Prima persona plurale, mai aziendale: quattro paragrafi
            brevi che vanno dal noi privato (siamo una coppia) al noi
            di lavoro (Aurya nasce li'). Niente date inventate, niente
            aneddoti: solo quello che sappiamo per certo. */}
        <Section tone="sand" rhythm="screen" labelledBy="cs-story-title">
          <div data-testid="cs-story">
            <DisplayTitle as="h2" id="cs-story-title" size="section" measure="title">
              {t('chiSiamo.storyTitle', { defaultValue: 'Come è nata Aurya.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('chiSiamo.storyP1', { defaultValue: 'Prima di essere un progetto siamo una coppia. Ci ha uniti la stessa cosa: la crescita personale, il lavoro su di sé, quello che cambia una persona da dentro.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('chiSiamo.storyP2', { defaultValue: 'Valentina lavora con le persone. Davide lavora nel digitale. Per anni sono stati due mestieri che non si parlavano.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('chiSiamo.storyP3', { defaultValue: "Poi abbiamo visto la stessa cosa da due lati. Chi pratica con serietà fatica a farsi trovare, chi cerca non sa di chi fidarsi, e in mezzo non c'è nessuno che vada a conoscere le persone una a una." })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('chiSiamo.storyP4', { defaultValue: 'Aurya nasce lì, nel punto in cui i nostri due mestieri si incontrano.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 3. LE PERSONE — la foto vera e due ritratti brevi ────
            La fotografia non e' un ornamento: e' il motivo per cui
            questa pagina esiste, quindi e' grande e non ha filtri ne'
            velature. Taglio 4:5 come sulla landing (l'originale e'
            quasi quadrato: il 4:3 tagliava fronte e mare).
            I due ritratti dicono SOLO fatti gia' verificati. */}
        <Section tone="paper" rhythm="flow" labelledBy="cs-faces-title" width="max-w-6xl">
          <div data-testid="cs-faces">
            <DisplayTitle as="h2" id="cs-faces-title" size="section" measure="title">
              {t('chiSiamo.facesTitle', { defaultValue: 'Valentina e Davide.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-10 sm:mt-12 lg:grid-cols-12 lg:items-center lg:gap-14">
              <div className="lg:col-span-5">
                <img
                  src="/media/chisiamo-aurya.jpg"
                  alt={t('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
                  width="900"
                  height="1125"
                  loading="lazy"
                  decoding="async"
                  className="aspect-[4/5] w-full rounded-[1.75rem] object-cover shadow-[0_18px_48px_-28px_rgba(30,47,40,0.45)]"
                />
              </div>
              <div className="lg:col-span-7">
                <h3 className="font-display text-[1.5rem] leading-tight text-foreground sm:text-[1.75rem]">
                  {t('chiSiamo.valentinaName', { defaultValue: 'Valentina' })}
                </h3>
                <Lede size="body" className="mt-3">
                  {t('chiSiamo.valentinaBody', { defaultValue: 'Operatrice Reiki di terzo livello. Accompagna le persone con letture evolutive di tarocchi e oracoli e con lo studio delle mappe natali. Di Aurya guarda il lato che pesa di più: sa cosa vuol dire avere davanti qualcuno che si affida.' })}
                </Lede>
                <h3 className="mt-9 font-display text-[1.5rem] leading-tight text-foreground sm:text-[1.75rem]">
                  {t('chiSiamo.davideName', { defaultValue: 'Davide' })}
                </h3>
                <Lede size="body" className="mt-3">
                  {t('chiSiamo.davideBody', { defaultValue: 'Lavora nel digitale. Da anni costruisce strumenti che mettono in contatto le persone, e di Aurya cura tutto quello che vedi e usi. Il suo mestiere qui serve a una cosa sola: togliere gli ostacoli fra te e la persona giusta.' })}
                </Lede>
              </div>
            </div>
            <Lede size="body" tone="quiet" className="mt-10">
              {t('chiSiamo.facesClose', { defaultValue: 'Su una cosa non abbiamo mai avuto dubbi: le persone cambiano, e chi le accompagna fa un lavoro serio. Aurya è il modo che abbiamo trovato per dargli lo spazio che merita.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 4. COSA CI GUIDA — la teoria citata, non riscritta ───
            L'unica ancora verde. La frase del Blueprint sta qui fra
            virgolette, come una citazione da un'altra pagina: chi
            vuole il ragionamento intero lo trova nel manifesto, e la
            CTA sotto ce lo porta. Duplicare il Manifesto sarebbe il
            modo piu' rapido di indebolirlo. */}
        <Section tone="sage" rhythm="screen" labelledBy="cs-guide-title">
          <div data-testid="cs-guide">
            <DisplayTitle as="h2" id="cs-guide-title" size="section" measure="title">
              {t('chiSiamo.guideTitle', { defaultValue: 'Cosa ci guida.' })}
            </DisplayTitle>
            <Quote size="page" className="mt-8">
              {t('chiSiamo.guideTheory', { defaultValue: 'Ogni percorso di benessere inizia da un incontro di fiducia.' })}
            </Quote>
            <Lede size="body" tone="inherit" className="mt-8 opacity-90">
              {t('chiSiamo.guideBody', { defaultValue: 'È la convinzione da cui parte tutto quello che facciamo, e anche tutto quello che non faremo mai. Per intero sta scritta nel manifesto.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 5. CHIUSURA — due porte, nessun bottone ──────────────
            Dopo una pagina di presentazioni la porta giusta e' un filo
            sotto il testo. La mail e' un <a href="mailto:"> vero: si
            apre nel client di chi legge, senza form di mezzo. */}
        <Section tone="cream" rhythm="flow" labelledBy="cs-close-title">
          <div data-testid="cs-close">
            <DisplayTitle as="h2" id="cs-close-title" size="section" measure="title">
              {t('chiSiamo.closeTitle', { defaultValue: 'Facciamo conoscenza.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">
              {t('chiSiamo.closeBody', { defaultValue: 'Come la pensiamo lo dice il manifesto, per intero. Se invece hai una domanda da farci, scriverci è la strada più corta.' })}
            </Lede>
            <div className="mt-8 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/manifesto" variant="quiet" data-testid="cs-cta-manifesto">
                {t('chiSiamo.ctaManifesto', { defaultValue: 'Leggi il manifesto' })}
              </EditorialCta>
              <EditorialCta href={`mailto:${CONTACT_MAIL}`} variant="quiet" data-testid="cs-cta-write">
                {t('chiSiamo.ctaWrite', { defaultValue: 'Scrivici' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
