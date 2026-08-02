/**
 * ManifestoPage — /manifesto (MF2: il manifesto riscritto dal founder).
 *
 * COSA CAMBIA. Il testo e' nuovo da cima a fondo ed e' del founder: qui
 * viene riportato parola per parola, ritoccata solo la punteggiatura
 * tipografica (apostrofi curvi, accenti). Sono SETTE blocchi al posto
 * dei quattro di DS1, quindi il ritmo e' stato rifatto, non allungato:
 * la grammatica visiva approvata (apertura fotografica scura, alternanza
 * dei fondi, fascia a tutta larghezza a meta' percorso, un'unica sezione
 * verde col trattamento piu' forte, firma con la foto vera) resta la
 * stessa, ma i blocchi ci sono stati rimontati sopra.
 * Solo italiano: le chiavi vivono nel locale IT con defaultValue
 * italiano e non vengono propagate a en/de/fr (richiesta del founder).
 *
 * I SETTE BLOCCHI, E DOVE SONO FINITI.
 *   1 PERCHE' ESISTIAMO      → apertura fotografica r04 (la frase madre
 *                              e le tre domande, dentro l'immagine) +
 *                              la sezione crema che le risponde, con
 *                              l'ancora al Magazine.
 *   2 IN COSA CREDIAMO       → sabbia, la coppia "non e' una
 *                              destinazione / e' un percorso" in corpo
 *                              display come perno, i due capoversi
 *                              affiancati.
 *   ~ LA FASCIA              → r01 da bordo a bordo con le due righe
 *                              che CHIUDONO il blocco 2 ("Il nostro
 *                              lavoro non e' scegliere al posto tuo"):
 *                              non e' testo aggiunto, e' testo spostato
 *                              di due centimetri, nel punto in cui la
 *                              lettura ha bisogno di fermarsi.
 *   3 COME VOGLIAMO FARLO    → bianco, impaginato da rivista: titolo in
 *                              colonna a sinistra, il ragionamento a
 *                              destra, la coppia oggi/domani staccata in
 *                              un inciso col filo d'oro, e l'ancora alla
 *                              Lettera.
 *   4 I NOSTRI PRINCIPI      → VERDE, il blocco piu' forte della pagina.
 *                              E' l'unico punto in cui il founder prende
 *                              impegni verificabili, e prende il posto
 *                              (e il trattamento) che in DS1 aveva
 *                              "Cosa non faremo mai": titolo piu' grande
 *                              di tutti, cinque voci numerate in oro con
 *                              un filo a separarle, il doppio dell'aria
 *                              sopra e sotto.
 *   5 COSA STIAMO COSTRUENDO → crema, i tre tempi (oggi / nei prossimi
 *                              mesi / poi) in tre colonne sotto un filo
 *                              d'oro: una linea del tempo senza toccare
 *                              una parola, perche' ogni colonna e' la
 *                              frase intera del founder.
 *   6 SE SEI UN PROFESSIONISTA → sabbia, due colonne e l'unica azione
 *                              piena della pagina.
 *   7 SE VUOI SEGUIRE IL PROGETTO → la firma. Il blocco 7 e' ospitato
 *                              DENTRO lo split con la fotografia vera
 *                              dei fondatori: e' l'unico modo di tenere
 *                              la firma in chiusura senza impilare tre
 *                              congedi di fila (6, 7 e una firma a
 *                              parte). La promessa "scriveremo solo
 *                              quando avremo qualcosa che vale il tuo
 *                              tempo" viene detta guardando in faccia
 *                              chi la fa.
 *
 * ALTERNANZA DEI FONDI (regola DS: due sezioni adiacenti non hanno mai
 * lo stesso fondo): scuro(foto) → crema → sabbia → FOTO a tutta
 * larghezza → bianco → VERDE → crema → sabbia → crema.
 *
 * CONTRASTI (minimo AA: 4,5:1 corpo, 3:1 display). Le misure delle due
 * fotografie sono quelle prese sui loro pixel e documentate in
 * PhotoOpener e PhotoBand; le altre sono calcolate sui colori pieni.
 *   apertura, crema #f6f2e8 sul velo di r04 ....... 8,84:1 / 7,96:1
 *   apertura, le domande (crema al 90%) ........... ~7,5:1 / ~6,8:1
 *   apertura, occhiello oro #d6c49a sul velo ...... 5,75:1
 *   fascia, crema #f6f2e8 sul velo di r01 ......... 6,78:1 / 6,10:1
 *   crema pieno su salvia #2f5749 ................. 7,28:1
 *   crema al 90% su salvia ........................ 6,26:1
 *   numeri oro #d6c49a su salvia .................. 4,74:1
 *   frase display (85%) su sabbia ................. 7,93:1
 *   inciso oggi/domani (70%) su bianco ............ 5,45:1
 * (dove ci sono due numeri sono le misure a 1440px e a 390px, prese sul
 * pixel peggiore del riquadro che il testo occupa davvero)
 *
 * MOVIMENTO. Solo la dissolvenza d'ingresso del kit, spenta da
 * prefers-reduced-motion. Nessuna parallasse, niente che parta da solo.
 * Nessun indice dei movimenti: scelta del founder.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import {
  Section, DisplayTitle, Lede, EditorialCta,
  PhotoOpener, PhotoBand, PhotoSplit,
} from '../../components/editorial';

/* Le fotografie assegnate a questa pagina dal magazzino
   (docs/DESIGN_PASS_DS_2026-08.md §Il magazzino foto). Restano queste:
   le altre sono gia' su pagine vicine, e la stessa foto a due clic di
   distanza si nota subito. */
const OPENER_PHOTO = '/media/prelaunch/r04.jpg';  // mano in gyan mudra
const BAND_PHOTO = '/media/prelaunch/r01.jpg';    // al torrente, verde pieno
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';

export default function ManifestoPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('manifesto.seoTitle', { defaultValue: 'Il manifesto di Aurya | Ogni percorso di benessere inizia da una domanda' }),
    // 141 caratteri, taglio a 158.
    description: t('manifesto.seoDesc', { defaultValue: 'Perché esistiamo, in cosa crediamo e cosa stiamo costruendo. Il manifesto di Aurya e i cinque principi da cui parte ogni scelta che prendiamo.' }),
    canonicalPath: '/manifesto',
  });

  /* Le tre domande dell'apertura. Sono la voce di chi legge, non la
     nostra: per questo stanno in corsivo e sotto la frase madre. */
  const questions = [
    t('manifesto.q1', { defaultValue: 'Come faccio a capire qual è la pratica giusta per me?' }),
    t('manifesto.q2', { defaultValue: 'Di chi posso fidarmi?' }),
    t('manifesto.q3', { defaultValue: 'Da dove comincio?' }),
  ];

  /* I cinque principi: titolo e riga che lo spiega. L'ordine e' quello
     del founder e va dal fuori (le persone, la conoscenza) al dentro
     (come cresceremo, come continueremo a imparare). */
  const principles = [
    {
      title: t('manifesto.p1Title', { defaultValue: 'Le persone vengono prima delle piattaforme.' }),
      body: t('manifesto.p1Body', { defaultValue: 'La tecnologia ha valore solo quando rende più semplici le relazioni.' }),
    },
    {
      title: t('manifesto.p2Title', { defaultValue: 'La conoscenza viene prima della scelta.' }),
      body: t('manifesto.p2Body', { defaultValue: 'Comprendere una pratica è importante quanto viverla.' }),
    },
    {
      title: t('manifesto.p3Title', { defaultValue: 'La fiducia richiede tempo.' }),
      body: t('manifesto.p3Body', { defaultValue: 'Per questo preferiamo approfondire piuttosto che semplificare.' }),
    },
    {
      title: t('manifesto.p4Title', { defaultValue: 'Costruiamo insieme.' }),
      body: t('manifesto.p4Body', { defaultValue: 'Aurya crescerà ascoltando chi vive ogni giorno il mondo del benessere. Persone prima di funzionalità.' }),
    },
    {
      title: t('manifesto.p5Title', { defaultValue: 'Continuiamo a imparare.' }),
      body: t('manifesto.p5Body', { defaultValue: 'Non crediamo nelle verità assolute. Crediamo nella curiosità, nella ricerca e nel confronto.' }),
    },
  ];

  /* I tre tempi del blocco 5. Ogni voce e' la frase INTERA del founder:
     "oggi", "nei prossimi mesi" e "poi" stanno dentro la frase, non
     estratti come etichette, perche' estrarli vorrebbe dire riscriverle. */
  const steps = [
    t('manifesto.buildingStep1', { defaultValue: 'Oggi è uno spazio dove leggere, comprendere e orientarsi.' }),
    t('manifesto.buildingStep2', { defaultValue: 'Nei prossimi mesi inizieremo a raccontare i primi professionisti che entreranno nella rete.' }),
    t('manifesto.buildingStep3', { defaultValue: 'Poi arriveranno esperienze, workshop, ritiri e strumenti che renderanno più semplice organizzare e vivere il benessere.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── APERTURA — blocco 1, la domanda ──────────────────────
            La frase madre e' l'unico h1 e sta DENTRO la fotografia piu'
            scura del magazzino. Le tre domande le stanno sotto in
            corsivo: sono la voce del lettore, e sull'ancora scura
            funzionano come un'eco, non come un elenco. */}
        <PhotoOpener
          data-testid="mf-open"
          image={OPENER_PHOTO}
          focus="52% 46%"
          height="tall"
          align="left"
          width="max-w-3xl"
          labelledBy="mf-open-title"
          eyebrow={t('manifesto.eyebrow', { defaultValue: 'Il manifesto' })}
        >
          <DisplayTitle as="h1" id="mf-open-title" size="manifesto" measure="wide" className="text-hero-shadow">
            {t('manifesto.heroTitle', { defaultValue: 'Ogni percorso di benessere inizia da una domanda.' })}
          </DisplayTitle>
          <div aria-hidden className="gold-rule mt-8 max-w-[9rem]" />
          <div className="mt-8 space-y-2.5 text-hero-shadow sm:space-y-3">
            {questions.map((q) => (
              <p key={q} className="font-display text-balance text-lg italic leading-snug opacity-90 sm:text-xl lg:text-[1.6rem]">
                {q}
              </p>
            ))}
          </div>
        </PhotoOpener>

        {/* ── 1. PERCHE' ESISTIAMO — il resto del blocco, sul chiaro ─
            Stessa scelta della landing operatori (la pagina approvata):
            il titolo sta sulla foto, l'argomento si legge sul chiaro.
            La coppia "trovare / orientarsi" e' il perno della sezione e
            passa al corpo display: sono nove parole, in corpo di
            lettura si perdevano fra le altre. */}
        <Section tone="cream" rhythm="screen" width="max-w-3xl"
                 id="mf-perche" labelledBy="mf-why-title">
          <div data-testid="mf-why">
            <DisplayTitle as="h2" id="mf-why-title" size="section" measure="title">
              {t('manifesto.whyTitle', { defaultValue: 'Perché esistiamo' })}
            </DisplayTitle>
            <div className="mt-8 grid gap-6 sm:gap-9 lg:grid-cols-2">
              <Lede size="body">
                {t('manifesto.whyP1', { defaultValue: 'Negli ultimi anni il mondo del benessere è cresciuto moltissimo. Sono nate nuove discipline, nuovi professionisti e nuove opportunità per prendersi cura di sé.' })}
              </Lede>
              <Lede size="body">
                {t('manifesto.whyP2', { defaultValue: 'Ma, insieme alle possibilità, è cresciuta anche la confusione.' })}
              </Lede>
            </div>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <p className="mt-10 max-w-[26ch] font-display text-balance text-[1.5rem] font-medium leading-[1.22] tracking-[-0.015em] text-foreground/85 sm:text-[1.9rem] lg:text-[2.1rem]">
              <span className="block">{t('manifesto.whyPivot1', { defaultValue: 'Trovare informazioni è semplice.' })}</span>
              <span className="block">{t('manifesto.whyPivot2', { defaultValue: 'Orientarsi lo è molto meno.' })}</span>
            </p>
            <Lede size="lead" className="mt-10">
              {t('manifesto.whyClose1', { defaultValue: 'Aurya nasce da questa domanda.' })}
            </Lede>
            <Lede size="body" className="mt-4">
              {t('manifesto.whyClose2', { defaultValue: 'Non per dire alle persone quale strada seguire. Ma per aiutarle a comprenderla.' })}
            </Lede>
            <div className="mt-9">
              <EditorialCta to="/blog" variant="quiet" data-testid="mf-cta-magazine-top">
                {t('manifesto.ctaMagazine', { defaultValue: 'Esplora il Magazine' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 2. IN COSA CREDIAMO ──────────────────────────────────
            La coppia "non e' una destinazione / e' un percorso" prende
            il corpo display e diventa il perno; i due capoversi che
            argomentano stanno affiancati, cosi' la sezione si legge in
            due colpi d'occhio invece che in una colonna sola. Le due
            righe che la chiudono non sono qui: sono nella fascia. */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl"
                 id="mf-crediamo" labelledBy="mf-believe-title">
          <div data-testid="mf-believe">
            <DisplayTitle as="h2" id="mf-believe-title" size="section" measure="title">
              {t('manifesto.believeTitle', { defaultValue: 'In cosa crediamo' })}
            </DisplayTitle>
            <p className="mt-8 max-w-[30ch] font-display text-balance text-[1.5rem] font-medium leading-[1.22] tracking-[-0.015em] text-foreground/85 sm:text-[1.9rem] lg:text-[2.1rem]">
              <span className="block">{t('manifesto.believeLead1', { defaultValue: 'Crediamo che il benessere non sia una destinazione.' })}</span>
              <span className="block">{t('manifesto.believeLead2', { defaultValue: 'È un percorso.' })}</span>
            </p>
            <div aria-hidden className="gold-rule mt-9 max-w-[10rem]" />
            <div className="mt-9 grid gap-7 sm:gap-10 lg:grid-cols-2">
              <Lede size="body">
                {t('manifesto.believeP1', { defaultValue: 'Ogni persona è diversa. Ogni momento della vita è diverso. Per questo non esistono pratiche che funzionano per tutti.' })}
              </Lede>
              <Lede size="body">
                {t('manifesto.believeP2', { defaultValue: 'Esistono persone, esperienze e approcci che possono essere giusti in un determinato momento.' })}
              </Lede>
            </div>
          </div>
        </Section>

        {/* ── LA FASCIA — il respiro di meta' percorso ─────────────
            r01 da bordo a bordo con le due righe che chiudono il blocco
            2. Sono la frase piu' citabile del manifesto ("non e'
            scegliere al posto tuo"), e sono anche il punto in cui la
            pagina passa dal credere al fare: e' li' che serve smettere
            di leggere per un momento. E' l'unica volta, prima della
            firma, in cui la pagina esce dalla sua colonna. */}
        <PhotoBand image={BAND_PHOTO} focus="50% 34%" width="max-w-3xl">
          <p className="max-w-[24ch] font-display text-balance text-[1.75rem] font-medium leading-[1.16] tracking-[-0.015em] text-hero-shadow sm:text-[2.4rem] lg:text-[3rem]">
            <span className="block">{t('manifesto.bandLine1', { defaultValue: 'Il nostro lavoro non è scegliere al posto tuo.' })}</span>
            <span className="block">{t('manifesto.bandLine2', { defaultValue: 'È aiutarti a scegliere con maggiore consapevolezza.' })}</span>
          </p>
        </PhotoBand>

        {/* ── 3. COME VOGLIAMO FARLO ───────────────────────────────
            Impaginato da rivista: titolo in colonna a sinistra, il
            ragionamento a destra. La coppia oggi/domani si stacca in un
            inciso col filo d'oro, perche' non e' un altro capoverso del
            ragionamento: e' il calendario di quello che si e' appena
            letto. Fondo bianco, il punto piu' luminoso della pagina,
            subito prima del verde. */}
        <Section tone="paper" rhythm="screen" width="max-w-3xl"
                 id="mf-come" labelledBy="mf-how-title">
          <div data-testid="mf-how" className="grid gap-8 lg:grid-cols-12 lg:gap-10">
            <div className="lg:col-span-4">
              <DisplayTitle as="h2" id="mf-how-title" size="section" measure="tight"
                            className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                {t('manifesto.howTitle', { defaultValue: 'Come vogliamo farlo' })}
              </DisplayTitle>
            </div>
            <div className="lg:col-span-8">
              <Lede size="body">
                {t('manifesto.howP1', { defaultValue: 'Non vogliamo costruire l’ennesimo portale. Vogliamo costruire un luogo dove il benessere possa essere raccontato con calma, approfondito con curiosità e vissuto con fiducia.' })}
              </Lede>
              <Lede size="body" className="mt-5">
                {t('manifesto.howP2', { defaultValue: 'Per questo abbiamo deciso di partire dalle fondamenta.' })}
              </Lede>
              <div className="mt-9 border-l-2 border-[#7d6a3a]/50 pl-5 sm:pl-6">
                <Lede size="body" tone="quiet">
                  {t('manifesto.howP3', { defaultValue: 'Oggi lo facciamo attraverso contenuti, guide e storie.' })}
                </Lede>
                <Lede size="body" tone="quiet" className="mt-4">
                  {t('manifesto.howP4', { defaultValue: 'Domani lo faremo anche attraverso una rete di professionisti, esperienze e strumenti pensati per accompagnare chi vive e chi lavora nel mondo del benessere.' })}
                </Lede>
              </div>
              <p className="mt-10 max-w-[26ch] font-display text-balance text-[1.35rem] font-medium leading-[1.24] tracking-[-0.015em] sm:text-[1.7rem] lg:text-[1.85rem]">
                <span className="block">{t('manifesto.howClose1', { defaultValue: 'Preferiamo crescere lentamente.' })}</span>
                <span className="block">{t('manifesto.howClose2', { defaultValue: 'Ma costruire qualcosa che possa durare.' })}</span>
              </p>
              <div className="mt-9">
                <EditorialCta to="/newsletter" variant="quiet" data-testid="mf-cta-letter-top">
                  {t('manifesto.ctaLetter', { defaultValue: 'Ricevi la Lettera di Aurya' })}
                </EditorialCta>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 4. I NOSTRI PRINCIPI — l'ancora verde ────────────────
            E' l'unico punto della pagina in cui il founder prende
            impegni che si possono verificare, e per questo prende il
            trattamento piu' forte: titolo piu' grande di ogni altro, i
            cinque principi numerati in oro con un filo a separarli, e il
            doppio dell'aria sopra e sotto (il ritmo qui lo mette il
            contenuto, per questo rhythm="none").
            Su desktop ogni voce e' una riga di rivista: numero e
            principio a sinistra, la riga che lo spiega a destra. La
            lista e' una <ol> perche' l'ordine e' informazione (si va
            dalle persone alle nostre abitudini di lavoro); i fili sono
            decorativi e restano fuori dalla lettura ad alta voce. */}
        <Section tone="sage" rhythm="none" width="max-w-4xl"
                 id="mf-principi" labelledBy="mf-principles-title"
                 innerClassName="py-24 sm:py-32 lg:py-40">
          <div data-testid="mf-principles">
            <DisplayTitle as="h2" id="mf-principles-title" size="section" measure="title"
                          className="text-[2.4rem] sm:text-[3.2rem] lg:text-[4rem] lg:leading-[1.04]">
              {t('manifesto.principlesTitle', { defaultValue: 'I nostri principi' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7 opacity-90">
              {t('manifesto.principlesIntro', { defaultValue: 'Ogni scelta che prenderemo partirà sempre da questi principi.' })}
            </Lede>
            <ol className="mt-12 list-none border-t border-[#f6f2e8]/20 p-0 sm:mt-14">
              {principles.map((p, i) => (
                <li key={p.title} className="border-b border-[#f6f2e8]/20 py-7 sm:py-9">
                  <div className="grid gap-3 lg:grid-cols-12 lg:gap-8">
                    <div className="lg:col-span-7">
                      <p className="eyebrow eyebrow-light mb-3">
                        {String(i + 1).padStart(2, '0')}
                      </p>
                      <p className="font-display text-balance text-[1.4rem] font-medium leading-[1.2] tracking-[-0.015em] sm:text-[1.75rem] lg:text-[1.95rem]">
                        {p.title}
                      </p>
                    </div>
                    <div className="lg:col-span-5 lg:pt-9">
                      <Lede size="body" tone="inherit" className="opacity-90">
                        {p.body}
                      </Lede>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </Section>

        {/* ── 5. COSA STIAMO COSTRUENDO ────────────────────────────
            Tre tempi in tre colonne, ognuna sotto il suo filo d'oro:
            e' una linea del tempo senza aver toccato una parola, perche'
            "oggi", "nei prossimi mesi" e "poi" stanno gia' dentro le
            frasi del founder e ogni colonna e' la frase intera. Su
            telefono le colonne si impilano e i fili diventano quello che
            gia' sono: tre gradini. */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl"
                 id="mf-costruendo" labelledBy="mf-building-title">
          <div data-testid="mf-building">
            <div className="max-w-3xl">
              <DisplayTitle as="h2" id="mf-building-title" size="section" measure="title">
                {t('manifesto.buildingTitle', { defaultValue: 'Cosa stiamo costruendo' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-6">
                {t('manifesto.buildingLead', { defaultValue: 'Aurya è un progetto in evoluzione.' })}
              </Lede>
            </div>
            <ol className="mt-12 grid list-none gap-8 p-0 sm:mt-14 sm:gap-10 lg:grid-cols-3">
              {steps.map((s) => (
                <li key={s}>
                  <div aria-hidden className="gold-rule" />
                  <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3] tracking-[-0.01em] text-foreground/85 sm:text-[1.35rem]">
                    {s}
                  </p>
                </li>
              ))}
            </ol>
            <p className="mt-14 max-w-[24ch] font-display text-balance text-[1.5rem] font-medium leading-[1.22] tracking-[-0.015em] sm:text-[1.9rem] lg:text-[2.1rem]">
              <span className="block">{t('manifesto.buildingClose1', { defaultValue: 'Non vogliamo costruire tutto subito.' })}</span>
              <span className="block">{t('manifesto.buildingClose2', { defaultValue: 'Vogliamo costruirlo nel modo giusto.' })}</span>
            </p>
          </div>
        </Section>

        {/* ── 6. SE SEI UN PROFESSIONISTA ──────────────────────────
            Due colonne come il blocco 3, e l'unica azione PIENA della
            pagina: e' l'unico punto in cui si chiede qualcosa a
            qualcuno. L'indirizzo e' /entra-nella-rete e non /operatori:
            il testo dice "ci piacerebbe conoscerti", cioe' parla a chi
            deve ancora candidarsi, mentre /operatori e' la pagina di chi
            e' gia' stato raccontato. */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl"
                 id="mf-professionista" labelledBy="mf-pro-title">
          <div data-testid="mf-pro" className="grid gap-8 lg:grid-cols-12 lg:gap-10">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="mf-pro-title" size="section" measure="tight"
                            className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                {t('manifesto.proTitle', { defaultValue: 'Se sei un professionista' })}
              </DisplayTitle>
            </div>
            <div className="lg:col-span-7">
              <Lede size="body">
                {t('manifesto.proP1', { defaultValue: 'Stiamo iniziando a conoscere le prime persone che entreranno a far parte della rete Aurya.' })}
              </Lede>
              <Lede size="body" className="mt-5">
                {t('manifesto.proP2', { defaultValue: 'Se condividi questa visione e senti che il tuo lavoro merita di essere raccontato con cura, ci piacerebbe conoscerti.' })}
              </Lede>
              <div className="mt-8">
                <EditorialCta to="/entra-nella-rete" variant="solid" data-testid="mf-cta-pro">
                  {t('manifesto.ctaPro', { defaultValue: 'Scopri la pagina dedicata ai professionisti' })}
                </EditorialCta>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 7. SE VUOI SEGUIRE IL PROGETTO — la firma ────────────
            Il settimo blocco e' ospitato dentro lo split con la
            fotografia vera dei fondatori. Tenere la firma come nona
            sezione a se' avrebbe messo tre congedi di fila; qui invece
            l'ultima promessa ("scriveremo solo quando avremo qualcosa
            che vale davvero il tuo tempo") viene detta da due facce, e
            la firma la chiude come si chiude una lettera. E' anche
            l'unica fotografia nostra del sito: mezza pagina piena fino
            al bordo, non un francobollo.
            Le due azioni sono nell'ordine del founder: la Lettera piena,
            il Magazine sottovoce. */}
        <PhotoSplit
          id="mf-firma"
          image={FOUNDERS_PHOTO}
          imageAlt={t('manifesto.foundersAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
          focus="50% 38%"
          side="left"
          tone="cream"
          imageWidth="900"
          imageHeight="886"
          labelledBy="mf-follow-title"
        >
          <div data-testid="mf-follow">
            <DisplayTitle as="h2" id="mf-follow-title" size="section" measure="title">
              {t('manifesto.followTitle', { defaultValue: 'Se vuoi seguire il progetto' })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">
              {t('manifesto.followP1', { defaultValue: 'Aurya cambierà molto nei prossimi mesi.' })}
            </Lede>
            <Lede size="body" className="mt-4">
              {t('manifesto.followP2', { defaultValue: 'Se ti interessa il modo in cui immaginiamo il benessere e vuoi seguire questa evoluzione fin dall’inizio, puoi ricevere la nostra lettera.' })}
            </Lede>
            <Lede size="body" className="mt-4">
              {t('manifesto.followP3', { defaultValue: 'Scriveremo solo quando avremo qualcosa che vale davvero il tuo tempo.' })}
            </Lede>
            {/* la firma: display serif corsivo, come una firma vera */}
            <p className="mt-7 font-display text-xl italic sm:text-2xl">
              {t('manifesto.signature', { defaultValue: 'Davide e Valentina' })}
            </p>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/newsletter" variant="solid" data-testid="mf-cta-letter">
                {t('manifesto.ctaLetterPrimary', { defaultValue: 'Iscriviti alla Lettera di Aurya' })}
              </EditorialCta>
              <EditorialCta to="/blog" variant="quiet" data-testid="mf-cta-magazine">
                {t('manifesto.ctaMagazine', { defaultValue: 'Esplora il Magazine' })}
              </EditorialCta>
            </div>
          </div>
        </PhotoSplit>

      </div>
    </MarketplaceShell>
  );
}
