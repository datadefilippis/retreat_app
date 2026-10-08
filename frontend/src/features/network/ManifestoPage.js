/**
 * ManifestoPage — /manifesto (MF3, 8/10/2026: il manifesto riscritto dal
 * founder, «Il benessere non ha una sola strada»).
 *
 * Il testo e' del founder, parola per parola (ritoccata solo la
 * punteggiatura tipografica). Vive in UN dizionario (TESTI) che e' anche il
 * locale IT (locales/it/landings.json → manifesto.*) e il corpus che i bot
 * leggono (services/identita.corpo_manifesto): una sola fonte, tre uscite.
 * Solo italiano.
 *
 * I DODICI BLOCCHI del founder e la grammatica visiva approvata (apertura
 * fotografica scura, alternanza dei fondi, una fascia a tutta larghezza,
 * un'unica sezione verde col trattamento piu' forte, la firma con la foto
 * vera):
 *   1 apertura (h1 + le cinque righe) → crema con «Aurya nasce da qui»
 *   2 Perche' esistiamo → sabbia, le tre domande in corsivo
 *   3 Un luogo per scoprire → crema, la terna «prima di scegliere…»
 *   4 Una rete di persone → sabbia; la FASCIA porta le due righe che lo
 *     chiudono («la fiducia non nasce da un algoritmo»)
 *   5 Il nostro modo di vedere il benessere → bianco, da rivista, col
 *     perno «non e' una destinazione»
 *   6 La conoscenza prima della scelta → crema, con l'unica CTA a meta'
 *     pagina (il Magazine, sottovoce)
 *   7 Anche chi accompagna ha bisogno di uno spazio → sabbia
 *   8 La nostra visione → bianco
 *   9 Una rete che cresce → crema, i cinque fronti in colonne sotto il
 *     filo d'oro e la terna finale
 *  10 I principi da cui non ci allontaneremo → VERDE, sei voci numerate
 *  11 Non un altro portale → sabbia, «Questa e' Aurya»
 *  12 Entra nel Cerchio → la firma, nello split con la foto dei fondatori
 *
 * ALTERNANZA DEI FONDI: scuro(foto) → crema → sabbia → crema → sabbia →
 * FOTO → bianco → crema → sabbia → bianco → crema → VERDE → sabbia → crema.
 * Contrasti e movimento: come in MF2 (il kit editoriale non e' cambiato).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import {
  Section, DisplayTitle, Lede, EditorialCta,
  PhotoOpener, PhotoBand, PhotoSplit,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/prelaunch/r04.jpg';  // mano in gyan mudra
const BAND_PHOTO = '/media/prelaunch/r01.jpg';    // al torrente, verde pieno
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';

/* Il testo del founder (8/10/2026), parola per parola. */
export const TESTI = {
  "seoTitle": "Il manifesto di Aurya | Il benessere non ha una sola strada",
  "seoDesc": "Perché esiste Aurya, come vediamo il benessere, la rete che stiamo costruendo e i principi da cui non ci allontaneremo. Il manifesto, scritto dai fondatori.",
  "eyebrow": "Il manifesto",
  "heroTitle": "Il benessere non ha una sola strada.",
  "hero1": "Ogni persona attraversa momenti diversi.",
  "hero2": "A volte abbiamo bisogno di fermarci.",
  "hero3": "Altre volte di ritrovare energia.",
  "hero4": "Di respirare, muoverci, ascoltare, imparare.",
  "hero5": "O semplicemente di incontrare qualcuno che sappia accompagnarci.",
  "intro1": "Oggi le possibilità sono moltissime.",
  "intro2": "Pratiche, professionisti, ritiri, percorsi, esperienze.",
  "intro3": "Ma avere più possibilità non significa necessariamente sapere dove andare.",
  "intro4": "Aurya nasce da qui.",
  "intro5": "Dalla volontà di rendere il mondo del benessere più comprensibile, più accessibile e più umano.",
  "whyTitle": "Perché esistiamo",
  "why1": "Crediamo che prendersi cura di sé non dovrebbe essere complicato.",
  "why2": "Eppure, quando iniziamo a cercare, incontriamo un mondo enorme: discipline diverse, approcci diversi, professionisti diversi, parole che spesso non conosciamo.",
  "why3": "Come capire cosa può essere giusto per noi?",
  "why4": "Di chi fidarsi?",
  "why5": "Da dove iniziare?",
  "why6": "Aurya non vuole rispondere a queste domande al posto tuo.",
  "why7": "Vuole aiutarti a trovare le tue risposte.",
  "why8": "Perché non esiste una pratica giusta per tutti.",
  "why9": "Esiste ciò che può essere giusto per te, in questo momento della tua vita.",
  "believeTitle": "Un luogo per scoprire",
  "scoprire1": "Aurya mette in relazione persone, professionisti ed esperienze.",
  "scoprire2": "Puoi conoscere chi lavora nel mondo del benessere, approfondire pratiche e approcci, scoprire ritiri, percorsi ed esperienze.",
  "scoprire3": "Puoi partire da una curiosità, da un bisogno o semplicemente dalla voglia di provare qualcosa di nuovo.",
  "scoprire4": "Prima di scegliere, puoi conoscere.",
  "scoprire5": "Prima di vivere un’esperienza, puoi capire.",
  "scoprire6": "E poi scegliere liberamente la tua strada.",
  "reteTitle": "Una rete di persone",
  "rete1": "Aurya non vuole essere un semplice elenco di professionisti.",
  "rete2": "Stiamo costruendo una rete.",
  "rete3": "Una rete di operatori, insegnanti, facilitatori e realtà che ogni giorno mettono il proprio sapere e la propria esperienza al servizio degli altri.",
  "rete4": "Persone diverse. Approcci diversi. Storie diverse.",
  "rete5": "Non vogliamo uniformarle.",
  "rete6": "Vogliamo farle conoscere.",
  "bandLine1": "Perché la fiducia non nasce da un algoritmo.",
  "bandLine2": "Nasce quando puoi vedere chi c’è dall’altra parte.",
  "howTitle": "Il nostro modo di vedere il benessere",
  "modo1": "Non crediamo nelle formule universali.",
  "modo2": "Non crediamo che esista un metodo capace di funzionare per tutti.",
  "modo3": "E non crediamo che una pratica debba essere migliore di un’altra per avere valore.",
  "modo4": "Crediamo nella possibilità di esplorare.",
  "modo5": "Di provare.",
  "modo6": "Di ascoltarsi.",
  "modo7": "Di cambiare direzione.",
  "modo8": "Di trovare, nel tempo, ciò che ci fa stare bene.",
  "howClose1": "Il benessere non è una destinazione.",
  "howClose2": "È una relazione con noi stessi che cambia nel tempo.",
  "conoscenzaTitle": "La conoscenza prima della scelta",
  "conoscenza1": "Per questo Aurya non è soltanto un luogo dove trovare esperienze.",
  "conoscenza2": "È anche un luogo dove comprendere.",
  "conoscenza3": "Attraverso il Magazine, le storie, le guide, i contenuti degli operatori e le esperienze che entrano nella rete, vogliamo creare uno spazio in cui poter fare domande e avvicinarsi al benessere con curiosità.",
  "conoscenza4": "Senza promesse miracolose.",
  "conoscenza5": "Senza verità assolute.",
  "conoscenza6": "Senza dover credere a qualcosa prima ancora di averlo compreso.",
  "ctaMagazine": "Esplora il Magazine",
  "accompagnaTitle": "Anche chi accompagna ha bisogno di uno spazio",
  "accompagna1": "Il benessere non esiste senza le persone che lo rendono possibile.",
  "accompagna2": "Per questo Aurya è anche uno spazio per chi lavora in questo mondo.",
  "accompagna3": "Uno spazio per raccontarsi, farsi conoscere, condividere il proprio sapere e costruire esperienze.",
  "accompagna4": "Per pubblicare percorsi, organizzare ritiri, proporre formazione e raggiungere nuove persone.",
  "accompagna5": "Vogliamo dare agli operatori strumenti che li aiutino a fare meglio il proprio lavoro, senza trasformare il loro lavoro in qualcosa di impersonale.",
  "accompagnaClose1": "La tecnologia deve servire la relazione.",
  "accompagnaClose2": "Non sostituirla.",
  "visioneTitle": "La nostra visione",
  "visione1": "Immaginiamo un mondo in cui prendersi cura di sé sia una parte naturale della vita.",
  "visione2": "Un mondo in cui, nei diversi momenti della propria vita, una persona possa trovare più facilmente qualcuno da cui imparare, una pratica da esplorare, un’esperienza da vivere o semplicemente uno spazio in cui fermarsi.",
  "visione3": "E immaginiamo un mondo in cui chi lavora nel benessere possa crescere, condividere la propria conoscenza e costruire il proprio percorso professionale rimanendo fedele alla propria identità.",
  "visioneClose": "Aurya vuole contribuire a costruire questo mondo.",
  "visione4": "Non creando una nuova verità sul benessere.",
  "visione5": "Ma creando connessioni tra le tante realtà che già esistono.",
  "buildingTitle": "Una rete che cresce",
  "buildingLead": "Aurya è già iniziata.",
  "building1": "Ci sono i primi operatori.",
  "building2": "Le prime esperienze.",
  "building3": "I primi ritiri.",
  "building4": "Le prime persone che stanno entrando nella rete.",
  "building5": "E da qui continueremo a crescere.",
  "buildingStep1": "Esperienze in presenza e online.",
  "buildingStep2": "Ritiri e percorsi.",
  "buildingStep3": "Formazione e conoscenza.",
  "buildingStep4": "Strumenti per gli operatori.",
  "buildingStep5": "Nuove possibilità per chi cerca.",
  "building6": "Non sappiamo ancora esattamente quanto potrà diventare grande questa rete.",
  "building7": "Ma sappiamo come vogliamo costruirla.",
  "buildingClose1": "Una persona alla volta.",
  "buildingClose2": "Un’esperienza alla volta.",
  "buildingClose3": "Una relazione alla volta.",
  "principlesTitle": "I principi da cui non ci allontaneremo",
  "p1Title": "Le persone prima della piattaforma",
  "p1Body": "La tecnologia ha valore quando rende più semplici le relazioni.",
  "p2Title": "La curiosità prima delle certezze",
  "p2Body": "Non abbiamo una verità da imporre. Abbiamo un mondo da esplorare.",
  "p3Title": "La conoscenza prima della scelta",
  "p3Body": "Comprendere ci permette di scegliere con maggiore consapevolezza.",
  "p4Title": "La fiducia richiede tempo",
  "p4Body": "Preferiamo conoscere le persone piuttosto che riempire semplicemente un catalogo.",
  "p5Title": "La diversità è una ricchezza",
  "p5Body": "Approcci diversi possono convivere senza che uno debba cancellare l’altro.",
  "p6Title": "Costruiamo insieme",
  "p6Body": "Aurya crescerà ascoltando le persone che ne fanno parte.",
  "portaleTitle": "Non un altro portale.",
  "portale1": "Non vogliamo costruire semplicemente un posto dove cercare un professionista o prenotare un’esperienza.",
  "portale2": "Vogliamo costruire un luogo in cui il mondo del benessere possa incontrarsi.",
  "portale3": "Dove chi cerca possa scoprire.",
  "portale4": "Dove chi accompagna possa raccontarsi.",
  "portale5": "Dove la conoscenza possa circolare.",
  "portale6": "Dove le esperienze possano nascere.",
  "portale7": "E dove, nel tempo, possa prendere forma una comunità.",
  "portaleClose": "Questa è Aurya.",
  "portale8": "Una rete per esplorare il benessere, senza una sola strada da seguire.",
  "portale9": "E siamo solo all’inizio.",
  "followTitle": "Entra nel Cerchio",
  "followP1": "Se vuoi seguire ciò che stiamo costruendo, entra nel Cerchio di Aurya.",
  "followP2": "Riceverai nuove esperienze, ritiri, percorsi, storie e occasioni per conoscere le persone che stanno dando forma alla rete.",
  "followP3": "Scriveremo quando avremo qualcosa che vale davvero il tuo tempo.",
  "signature": "Davide e Valentina",
  "ctaLetterPrimary": "Entra nel Cerchio di Aurya",
  "ctaPro": "Sei un professionista?",
  "foundersAlt": "Davide e Valentina, i fondatori di Aurya, in riva al mare",
};

const Pivot = ({ righe, className = '' }) => (
  <p className={`font-display text-balance text-[1.5rem] font-medium leading-[1.22] tracking-[-0.015em] text-foreground/85 sm:text-[1.9rem] lg:text-[2.1rem] ${className}`}>
    {righe.map((r) => <span key={r} className="block">{r}</span>)}
  </p>
);

export default function ManifestoPage() {
  const { t } = useTranslation('landings');
  const m = (k) => t(`manifesto.${k}`, { defaultValue: TESTI[k] });

  useSeoMeta({
    title: t('manifesto.seoTitle', { defaultValue: TESTI.seoTitle }),
    description: t('manifesto.seoDesc', { defaultValue: TESTI.seoDesc }),
    canonicalPath: '/manifesto',
  });

  const principles = [
    { title: t('manifesto.p1Title', { defaultValue: TESTI.p1Title }), body: t('manifesto.p1Body', { defaultValue: TESTI.p1Body }) },
    { title: t('manifesto.p2Title', { defaultValue: TESTI.p2Title }), body: t('manifesto.p2Body', { defaultValue: TESTI.p2Body }) },
    { title: t('manifesto.p3Title', { defaultValue: TESTI.p3Title }), body: t('manifesto.p3Body', { defaultValue: TESTI.p3Body }) },
    { title: t('manifesto.p4Title', { defaultValue: TESTI.p4Title }), body: t('manifesto.p4Body', { defaultValue: TESTI.p4Body }) },
    { title: t('manifesto.p5Title', { defaultValue: TESTI.p5Title }), body: t('manifesto.p5Body', { defaultValue: TESTI.p5Body }) },
    { title: t('manifesto.p6Title', { defaultValue: TESTI.p6Title }), body: t('manifesto.p6Body', { defaultValue: TESTI.p6Body }) },
  ];
  const fronti = ['buildingStep1', 'buildingStep2', 'buildingStep3', 'buildingStep4', 'buildingStep5'].map(m);

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA — l'h1 e le cinque righe ─────────────────── */}
        <PhotoOpener data-testid="mf-open" image={OPENER_PHOTO} focus="52% 46%" height="tall" align="left"
                     width="max-w-3xl" labelledBy="mf-open-title" eyebrow={m('eyebrow')}>
          <DisplayTitle as="h1" id="mf-open-title" size="manifesto" measure="wide" className="text-hero-shadow">
            {t('manifesto.heroTitle', { defaultValue: TESTI.heroTitle })}
          </DisplayTitle>
          <div aria-hidden className="gold-rule mt-8 max-w-[9rem]" />
          <p className="mt-8 font-display text-balance text-lg leading-snug text-hero-shadow sm:text-xl lg:text-[1.6rem]">{m('hero1')}</p>
          <div className="mt-4 space-y-2 text-hero-shadow sm:space-y-2.5">
            {['hero2', 'hero3', 'hero4', 'hero5'].map((k) => (
              <p key={k} className="font-display text-balance text-lg italic leading-snug opacity-90 sm:text-xl lg:text-[1.45rem]">{m(k)}</p>
            ))}
          </div>
        </PhotoOpener>

        {/* il resto del blocco 1, sul chiaro: «Aurya nasce da qui» */}
        <Section tone="cream" rhythm="screen" width="max-w-3xl" id="mf-inizio" labelledBy="mf-open-title">
          <div data-testid="mf-intro">
            <Lede size="lead">{m('intro1')}</Lede>
            <Lede size="body" className="mt-4">{m('intro2')}</Lede>
            <Lede size="body" className="mt-4">{m('intro3')}</Lede>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <Pivot className="mt-10 max-w-[26ch]" righe={[m('intro4')]} />
            <Lede size="body" className="mt-6">{m('intro5')}</Lede>
          </div>
        </Section>

        {/* ── 2. PERCHE' ESISTIAMO ──────────────────────────────────── */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl" id="mf-perche" labelledBy="mf-why-title">
          <div data-testid="mf-why">
            <DisplayTitle as="h2" id="mf-why-title" size="section" measure="title">
              {t('manifesto.whyTitle', { defaultValue: TESTI.whyTitle })}
            </DisplayTitle>
            <Lede size="lead" className="mt-8">{m('why1')}</Lede>
            <Lede size="body" className="mt-5">{m('why2')}</Lede>
            <div className="mt-8 space-y-2">
              {['why3', 'why4', 'why5'].map((k) => (
                <p key={k} className="font-display text-balance text-lg italic leading-snug text-foreground/85 sm:text-xl">{m(k)}</p>
              ))}
            </div>
            <Lede size="body" className="mt-8">{m('why6')}</Lede>
            <Pivot className="mt-5 max-w-[28ch]" righe={[m('why7')]} />
            <Lede size="body" className="mt-8">{m('why8')}</Lede>
            <Lede size="lead" className="mt-3">{m('why9')}</Lede>
          </div>
        </Section>

        {/* ── 3. UN LUOGO PER SCOPRIRE ─────────────────────────────── */}
        <Section tone="cream" rhythm="screen" width="max-w-3xl" id="mf-scoprire" labelledBy="mf-believe-title">
          <div data-testid="mf-believe">
            <DisplayTitle as="h2" id="mf-believe-title" size="section" measure="title">
              {t('manifesto.believeTitle', { defaultValue: TESTI.believeTitle })}
            </DisplayTitle>
            <Lede size="lead" className="mt-8">{m('scoprire1')}</Lede>
            <div className="mt-6 grid gap-6 sm:gap-9 lg:grid-cols-2">
              <Lede size="body">{m('scoprire2')}</Lede>
              <Lede size="body">{m('scoprire3')}</Lede>
            </div>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <Pivot className="mt-10 max-w-[26ch]" righe={[m('scoprire4'), m('scoprire5'), m('scoprire6')]} />
          </div>
        </Section>

        {/* ── 4. UNA RETE DI PERSONE ───────────────────────────────── */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl" id="mf-rete" labelledBy="mf-rete-title">
          <div data-testid="mf-rete">
            <DisplayTitle as="h2" id="mf-rete-title" size="section" measure="title">{m('reteTitle')}</DisplayTitle>
            <Lede size="body" className="mt-8">{m('rete1')}</Lede>
            <Lede size="lead" className="mt-3">{m('rete2')}</Lede>
            <Lede size="body" className="mt-6">{m('rete3')}</Lede>
            <Lede size="body" className="mt-6">{m('rete4')}</Lede>
            <Pivot className="mt-8 max-w-[26ch]" righe={[m('rete5'), m('rete6')]} />
          </div>
        </Section>

        {/* ── LA FASCIA — le due righe che chiudono il blocco 4 ─────── */}
        <PhotoBand image={BAND_PHOTO} focus="50% 34%" width="max-w-3xl">
          <p className="max-w-[24ch] font-display text-balance text-[1.75rem] font-medium leading-[1.16] tracking-[-0.015em] text-hero-shadow sm:text-[2.4rem] lg:text-[3rem]">
            <span className="block">{m('bandLine1')}</span>
            <span className="block">{m('bandLine2')}</span>
          </p>
        </PhotoBand>

        {/* ── 5. IL NOSTRO MODO DI VEDERE IL BENESSERE ─────────────── */}
        <Section tone="paper" rhythm="screen" width="max-w-3xl" id="mf-modo" labelledBy="mf-how-title">
          <div data-testid="mf-how" className="grid gap-8 lg:grid-cols-12 lg:gap-10">
            <div className="lg:col-span-4">
              <DisplayTitle as="h2" id="mf-how-title" size="section" measure="tight" className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                {t('manifesto.howTitle', { defaultValue: TESTI.howTitle })}
              </DisplayTitle>
            </div>
            <div className="lg:col-span-8">
              <Lede size="body">{m('modo1')}</Lede>
              <Lede size="body" className="mt-4">{m('modo2')}</Lede>
              <Lede size="body" className="mt-4">{m('modo3')}</Lede>
              <div className="mt-9 border-l-2 border-[#7d6a3a]/50 pl-5 sm:pl-6">
                <Lede size="body" tone="quiet">{m('modo4')}</Lede>
                {['modo5', 'modo6', 'modo7', 'modo8'].map((k) => (
                  <Lede key={k} size="body" tone="quiet" className="mt-2">{m(k)}</Lede>
                ))}
              </div>
              <p className="mt-10 max-w-[26ch] font-display text-balance text-[1.35rem] font-medium leading-[1.24] tracking-[-0.015em] sm:text-[1.7rem] lg:text-[1.85rem]">
                <span className="block">{m('howClose1')}</span>
                <span className="block">{m('howClose2')}</span>
              </p>
            </div>
          </div>
        </Section>

        {/* ── 6. LA CONOSCENZA PRIMA DELLA SCELTA — con il Magazine ─── */}
        <Section tone="cream" rhythm="screen" width="max-w-3xl" id="mf-conoscenza" labelledBy="mf-conoscenza-title">
          <div data-testid="mf-conoscenza">
            <DisplayTitle as="h2" id="mf-conoscenza-title" size="section" measure="title">{m('conoscenzaTitle')}</DisplayTitle>
            <Lede size="body" className="mt-8">{m('conoscenza1')}</Lede>
            <Lede size="lead" className="mt-3">{m('conoscenza2')}</Lede>
            <Lede size="body" className="mt-6">{m('conoscenza3')}</Lede>
            <div className="mt-8 space-y-1.5">
              {['conoscenza4', 'conoscenza5', 'conoscenza6'].map((k) => (
                <p key={k} className="font-display text-balance text-lg leading-snug text-foreground/85 sm:text-xl">{m(k)}</p>
              ))}
            </div>
            <div className="mt-9">
              <EditorialCta to="/blog" variant="quiet" data-testid="mf-cta-magazine-top">{m('ctaMagazine')}</EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. ANCHE CHI ACCOMPAGNA HA BISOGNO DI UNO SPAZIO ─────── */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl" id="mf-accompagna" labelledBy="mf-accompagna-title">
          <div data-testid="mf-accompagna">
            <DisplayTitle as="h2" id="mf-accompagna-title" size="section" measure="title">{m('accompagnaTitle')}</DisplayTitle>
            <Lede size="lead" className="mt-8">{m('accompagna1')}</Lede>
            <Lede size="body" className="mt-5">{m('accompagna2')}</Lede>
            <div className="mt-6 grid gap-6 sm:gap-9 lg:grid-cols-2">
              <Lede size="body">{m('accompagna3')}</Lede>
              <Lede size="body">{m('accompagna4')}</Lede>
            </div>
            <Lede size="body" className="mt-6">{m('accompagna5')}</Lede>
            <Pivot className="mt-9 max-w-[26ch]" righe={[m('accompagnaClose1'), m('accompagnaClose2')]} />
          </div>
        </Section>

        {/* ── 8. LA NOSTRA VISIONE ─────────────────────────────────── */}
        <Section tone="paper" rhythm="screen" width="max-w-3xl" id="mf-visione" labelledBy="mf-visione-title">
          <div data-testid="mf-visione">
            <DisplayTitle as="h2" id="mf-visione-title" size="section" measure="title">{m('visioneTitle')}</DisplayTitle>
            <Lede size="lead" className="mt-8">{m('visione1')}</Lede>
            <Lede size="body" className="mt-5">{m('visione2')}</Lede>
            <Lede size="body" className="mt-5">{m('visione3')}</Lede>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <Pivot className="mt-10 max-w-[26ch]" righe={[m('visioneClose')]} />
            <Lede size="body" className="mt-6">{m('visione4')}</Lede>
            <Lede size="body" className="mt-2">{m('visione5')}</Lede>
          </div>
        </Section>

        {/* ── 9. UNA RETE CHE CRESCE ───────────────────────────────── */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl" id="mf-cresce" labelledBy="mf-building-title">
          <div data-testid="mf-building">
            <div className="max-w-3xl">
              <DisplayTitle as="h2" id="mf-building-title" size="section" measure="title">
                {t('manifesto.buildingTitle', { defaultValue: TESTI.buildingTitle })}
              </DisplayTitle>
              <Lede size="lead" className="mt-6">{m('buildingLead')}</Lede>
              <div className="mt-6 space-y-1.5">
                {['building1', 'building2', 'building3', 'building4'].map((k) => (
                  <p key={k} className="font-display text-balance text-lg leading-snug text-foreground/85 sm:text-xl">{m(k)}</p>
                ))}
              </div>
              <Lede size="body" className="mt-6">{m('building5')}</Lede>
            </div>
            <ol className="mt-12 grid list-none gap-8 p-0 sm:mt-14 sm:grid-cols-2 sm:gap-10 lg:grid-cols-5">
              {fronti.map((s) => (
                <li key={s}>
                  <div aria-hidden className="gold-rule" />
                  <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3] tracking-[-0.01em] text-foreground/85 sm:text-[1.35rem]">{s}</p>
                </li>
              ))}
            </ol>
            <div className="mt-12 max-w-3xl">
              <Lede size="body">{m('building6')}</Lede>
              <Lede size="body" className="mt-2">{m('building7')}</Lede>
              <Pivot className="mt-10 max-w-[24ch]" righe={[m('buildingClose1'), m('buildingClose2'), m('buildingClose3')]} />
            </div>
          </div>
        </Section>

        {/* ── 10. I PRINCIPI — l'ancora verde, sei voci ────────────── */}
        <Section tone="sage" rhythm="none" width="max-w-4xl" id="mf-principi" labelledBy="mf-principles-title" innerClassName="py-24 sm:py-32 lg:py-40">
          <div data-testid="mf-principles">
            <DisplayTitle as="h2" id="mf-principles-title" size="section" measure="title" className="text-[2.4rem] sm:text-[3.2rem] lg:text-[4rem] lg:leading-[1.04]">
              {t('manifesto.principlesTitle', { defaultValue: TESTI.principlesTitle })}
            </DisplayTitle>
            <ol className="mt-12 list-none border-t border-[#f6f2e8]/20 p-0 sm:mt-14">
              {principles.map((p, i) => (
                <li key={p.title} className="border-b border-[#f6f2e8]/20 py-7 sm:py-9">
                  <div className="grid gap-3 lg:grid-cols-12 lg:gap-8">
                    <div className="lg:col-span-7">
                      <p className="eyebrow eyebrow-light mb-3">{String(i + 1).padStart(2, '0')}</p>
                      <p className="font-display text-balance text-[1.4rem] font-medium leading-[1.2] tracking-[-0.015em] sm:text-[1.75rem] lg:text-[1.95rem]">{p.title}</p>
                    </div>
                    <div className="lg:col-span-5 lg:pt-9">
                      <Lede size="body" tone="inherit" className="opacity-90">{p.body}</Lede>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </Section>

        {/* ── 11. NON UN ALTRO PORTALE ─────────────────────────────── */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl" id="mf-portale" labelledBy="mf-portale-title">
          <div data-testid="mf-portale">
            <DisplayTitle as="h2" id="mf-portale-title" size="section" measure="title">{m('portaleTitle')}</DisplayTitle>
            <Lede size="body" className="mt-8">{m('portale1')}</Lede>
            <Lede size="lead" className="mt-4">{m('portale2')}</Lede>
            <div className="mt-8 space-y-1.5">
              {['portale3', 'portale4', 'portale5', 'portale6', 'portale7'].map((k) => (
                <p key={k} className="font-display text-balance text-lg leading-snug text-foreground/85 sm:text-xl">{m(k)}</p>
              ))}
            </div>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <Pivot className="mt-10 max-w-[26ch]" righe={[m('portaleClose')]} />
            <Lede size="body" className="mt-6">{m('portale8')}</Lede>
            <Lede size="body" className="mt-2">{m('portale9')}</Lede>
          </div>
        </Section>

        {/* ── 12. ENTRA NEL CERCHIO — la firma ─────────────────────── */}
        <PhotoSplit id="mf-firma" image={FOUNDERS_PHOTO} imageAlt={m('foundersAlt')} focus="50% 38%" side="left" tone="cream"
                    imageWidth="900" imageHeight="886" labelledBy="mf-follow-title">
          <div data-testid="mf-follow">
            <DisplayTitle as="h2" id="mf-follow-title" size="section" measure="title">
              {t('manifesto.followTitle', { defaultValue: TESTI.followTitle })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">{m('followP1')}</Lede>
            <Lede size="body" className="mt-4">{m('followP2')}</Lede>
            <Lede size="body" className="mt-4">{m('followP3')}</Lede>
            <p className="mt-7 font-display text-xl italic sm:text-2xl">{m('signature')}</p>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/newsletter" variant="solid" data-testid="mf-cta-letter">{m('ctaLetterPrimary')}</EditorialCta>
              <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="mf-cta-pro">{m('ctaPro')}</EditorialCta>
            </div>
          </div>
        </PhotoSplit>

      </div>
    </MarketplaceShell>
  );
}
