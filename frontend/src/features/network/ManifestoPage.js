/**
 * ManifestoPage — /manifesto (SW1, redesign sul Blueprint).
 *
 * La pagina piu' linkata del sito (meta' delle CTA porta qui) detta
 * nella voce v3. Quattro movimenti, dal Blueprint cap. 0/2/9:
 *   1. LA TEORIA          la frase sola, grande, molto vuoto attorno
 *   2. IL MONDO           il problema detto piano, mai lamento
 *   3. COME LAVORIAMO     i gesti in prima persona plurale, il badge
 *                         come provenienza (mai come medaglia)
 *   4. COSA NON FAREMO MAI la lista dei divieti resa pubblica:
 *                         l'unica ancora verde della pagina
 *   FIRMA                 i fondatori col materiale reale di
 *                         aboutPage.faces* + doppia CTA discreta
 *
 * Ogni frase segue il dispositivo a coppia: prima una verita' sul
 * mondo, poi un nostro gesto. Se si parte da noi, e' pubblicita'.
 *
 * Fondi: crema, sabbia, bianco, VERDE, crema. Una sola ancora verde
 * (il Blueprint ne ammette due non adiacenti; qui basta il movimento
 * 4, che sul verde diventa solenne al punto giusto). Contrasti
 * misurati sul salvia #2f5749: crema piena 7,28:1, crema al 90%
 * 6,24:1, oro dell'occhiello 4,74:1. Minimo AA: 4,5:1.
 * Movimento: solo il reveal del kit (dissolvenza, reduced-motion ok).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, Lede, EditorialCta,
} from '../../components/editorial';

export default function ManifestoPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('manifesto.seoTitle', { defaultValue: 'Il manifesto di Aurya | Ogni percorso inizia da un incontro di fiducia' }),
    // 133 caratteri: la teoria, poi l'indice della pagina. Taglio a 158.
    description: t('manifesto.seoDesc', { defaultValue: "Ogni percorso di benessere inizia da un incontro di fiducia. Come lavoriamo, cosa non faremo mai e chi c'è dietro Aurya, detto piano." }),
    canonicalPath: '/manifesto',
  });

  /* La lista dei mai: cinque no, uno per riga. L'ordine va dal mondo
     (classifiche, promesse) verso di noi (le parole di questa pagina):
     l'ultimo no e' anche il piu' facile da verificare, perche' sta
     scritto proprio qui. */
  const nevers = [
    t('manifesto.never1', { defaultValue: 'Non venderemo posizioni in classifica.' }),
    t('manifesto.never2', { defaultValue: 'Non pubblicheremo promesse di guarigione.' }),
    t('manifesto.never3', { defaultValue: 'Non chiameremo le persone utenti.' }),
    t('manifesto.never4', { defaultValue: 'Non racconteremo qualcuno che non abbiamo incontrato.' }),
    t('manifesto.never5', { defaultValue: 'Non riempiremo questa pagina di parole che non pensiamo.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. LA TEORIA — la frase sola, grande ─────────────────
            Centrata e con il ritmo pieno: il vuoto attorno E' il
            trattamento. Sotto, due righe che la spiegano senza
            gonfiarla; il payoff torna come eco, nell'occhiello d'oro
            di brand, non come seconda tesi. */}
        <Section tone="cream" rhythm="screen" labelledBy="mf-theory-title">
          <div data-testid="mf-theory" className="text-center">
            <p className="eyebrow mb-6">
              {t('manifesto.eyebrow', { defaultValue: 'Il manifesto' })}
            </p>
            <DisplayTitle as="h1" id="mf-theory-title" size="manifesto" measure="wide"
                          className="mx-auto">
              {t('manifesto.theoryTitle', { defaultValue: 'Ogni percorso di benessere inizia da un incontro di fiducia.' })}
            </DisplayTitle>
            <Lede size="lead" className="mx-auto mt-8">
              {t('manifesto.theoryBody', { defaultValue: 'Non si sceglie una disciplina. Si sceglie una persona, e le si affida qualcosa di intimo. Tutto quello che facciamo parte da qui.' })}
            </Lede>
            <BrandPayoff tone="cream" size="sm" className="mt-10" />
          </div>
        </Section>

        {/* ── 2. IL MONDO COME LO VEDIAMO — il problema detto piano ─
            Constatazione, mai lamento: il terzo paragrafo lo dice
            esplicitamente ("non e' colpa di nessuno") e riporta il
            discorso sul lettore. Fondo sabbia: un gradino piu' caldo,
            nessuna enfasi. */}
        <Section tone="sand" rhythm="screen" labelledBy="mf-world-title">
          <div data-testid="mf-world">
            <DisplayTitle as="h2" id="mf-world-title" size="section" measure="title">
              {t('manifesto.worldTitle', { defaultValue: 'Il mondo come lo vediamo.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('manifesto.worldP1', { defaultValue: 'Trovare qualcuno di cui fidarsi è difficile.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('manifesto.worldP2', { defaultValue: 'Profili ovunque, appigli da nessuna parte. Le promesse sono tante e le persone si vedono poco. Chi lavora bene sparisce in mezzo a chi promette di più.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('manifesto.worldP3', { defaultValue: 'Non è colpa di nessuno. Ma quando la scelta è così personale, hai bisogno di sapere chi hai davanti.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 3. COME LAVORIAMO — i gesti ──────────────────────────
            Tre coppie parallele (verita' sul mondo → nostro gesto) e
            poi il badge, che non e' un quarto gesto: e' la provenienza
            di quello che il lettore trovera' scritto. Fondo bianco, il
            punto piu' luminoso della pagina, prima del verde. */}
        <Section tone="paper" rhythm="screen" labelledBy="mf-work-title">
          <div data-testid="mf-work">
            <DisplayTitle as="h2" id="mf-work-title" size="section" measure="title">
              {t('manifesto.workTitle', { defaultValue: 'Come lavoriamo.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-7">
              {t('manifesto.workP1', { defaultValue: 'Per conoscere qualcuno ci vuole tempo. Ce lo prendiamo: incontriamo le persone una a una.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('manifesto.workP2', { defaultValue: 'Le domande gentili non bastano. Ne facciamo anche di scomode, e ascoltiamo le risposte.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('manifesto.workP3', { defaultValue: 'Le cose serie vanno spiegate. Scriviamo quello che abbiamo capito, anche i limiti: per chi è una pratica, e per chi non è.' })}
            </Lede>
            <Lede size="body" tone="quiet" className="mt-8">
              {t('manifesto.workBadge', { defaultValue: 'Quando un profilo nasce così, lo trovi segnato: Verificato Aurya. Non è una medaglia. Ti dice da dove viene quello che stai leggendo.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 4. COSA NON FAREMO MAI — l'ancora verde ──────────────
            La lista dei divieti resa pubblica e' un atto di fiducia:
            nessun altro la scrive. Il verde pieno la rende solenne al
            punto giusto. Ogni riga a piena opacita' (7,28:1); la
            chiusa al 90% (6,24:1). I fili fra le righe sono
            decorativi, non testo. */}
        <Section tone="sage" rhythm="screen" labelledBy="mf-never-title">
          <div data-testid="mf-never">
            <DisplayTitle as="h2" id="mf-never-title" size="section" measure="title">
              {t('manifesto.neverTitle', { defaultValue: 'Cosa non faremo mai.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7">
              {t('manifesto.neverIntro', { defaultValue: 'Una promessa vale per quello che esclude. Questa lista è pubblica: puoi ricordarcela quando vuoi.' })}
            </Lede>
            <ul className="mt-10 max-w-[62ch] list-none divide-y divide-[#f6f2e8]/15 border-y border-[#f6f2e8]/15 p-0">
              {nevers.map((riga) => (
                <li key={riga} className="py-5 text-lg leading-relaxed sm:text-xl">
                  {riga}
                </li>
              ))}
            </ul>
            <Lede size="body" tone="inherit" className="mt-8 opacity-90">
              {t('manifesto.neverClose', { defaultValue: 'Ogni no è anche un limite che ci diamo. Ma chi ammette un limite viene creduto sul resto.' })}
            </Lede>
          </div>
        </Section>

        {/* ── FIRMA — i fondatori, col materiale reale ─────────────
            Foto vera e testo gia' esistente (aboutPage.faces*, x4):
            qui non si inventa niente, si firma. Le due CTA finali
            sono discrete apposta: dopo una pagina di posizione, la
            porta giusta e' un filo sotto il testo, non un bottone. */}
        <Section tone="cream" rhythm="flow" labelledBy="mf-sign-title" width="max-w-6xl">
          <div data-testid="mf-sign" className="grid gap-10 lg:grid-cols-12 lg:items-center lg:gap-14">
            <div className="lg:col-span-5">
              <img
                src="/media/chisiamo-aurya.jpg"
                alt={t('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
                width="1200"
                height="900"
                loading="lazy"
                decoding="async"
                className="w-full rounded-3xl object-cover"
              />
            </div>
            <div className="lg:col-span-7">
              <p className="eyebrow mb-5">
                {t('aboutPage.facesEyebrow', { defaultValue: 'Ci presentiamo' })}
              </p>
              <DisplayTitle as="h2" id="mf-sign-title" size="section" measure="title">
                {t('aboutPage.facesTitle', { defaultValue: 'Siamo Davide e Valentina' })}
              </DisplayTitle>
              <Lede size="body" className="mt-6">
                {t('aboutPage.facesBody1')}
              </Lede>
              <Lede size="body" className="mt-4">
                {t('aboutPage.facesBody2')}
              </Lede>
              {/* la firma: display serif corsivo, come una firma vera */}
              <p className="mt-7 font-display text-xl italic sm:text-2xl">
                {t('manifesto.signature', { defaultValue: 'Davide e Valentina' })}
              </p>
              <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
                <EditorialCta to="/operatori" variant="quiet" data-testid="mf-cta-people">
                  {t('manifesto.ctaPeople', { defaultValue: 'Conosci le persone' })}
                </EditorialCta>
                <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="mf-cta-operators">
                  {t('manifesto.ctaOperators', { defaultValue: 'Sei un operatore? Parliamone' })}
                </EditorialCta>
              </div>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
