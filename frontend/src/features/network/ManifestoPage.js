/**
 * ManifestoPage — /manifesto (SW1 per il copy, DS1 per il disegno).
 *
 * IL COPY NON E' CAMBIATO DI UNA PAROLA. Cambia dove sta, su che fondo,
 * quanto e' grande e cosa ha accanto. Le chiavi manifesto.* e
 * aboutPage.faces* sono le stesse, tradotte nelle stesse quattro
 * lingue: DS1 e' un passaggio di disegno, non di scrittura.
 *
 * IL DIFETTO CHE SI CORREGGE (docs/DESIGN_PASS_DS_2026-08.md). La
 * pagina apriva con la frase-teoria gigante al centro del crema vuoto.
 * E' un'apertura che funziona su carta, dove il foglio ha un bordo e la
 * frase ha un peso; in un browser il crema non ha bordo, e una frase
 * sospesa nel niente non apre niente. Sotto, quattro sezioni di sola
 * colonna di testo, tutte con lo stesso ritmo, senza un punto in cui
 * l'occhio potesse fermarsi o capire quanto mancava.
 *
 * COSA FA ORA, IN ORDINE.
 *   APERTURA   r04 (la mano in gyan mudra, macro su fondo scuro) a
 *              tutta larghezza, col titolo DENTRO l'immagine. E' la
 *              foto piu' scura del magazzino, e quindi quella che
 *              regge meglio un'ancora: il velo e' calcolato sui suoi
 *              pixel (8,84:1 a 1440, 7,96:1 a 390 — PhotoOpener).
 *   SOGLIA     crema: le due righe che spiegano la teoria, e sotto
 *              l'indice dei movimenti nella sua forma da telefono.
 *   MOVIMENTO 2 sabbia: il mondo. La constatazione prende il corpo
 *              display e diventa il perno della sezione; i due
 *              capoversi che argomentano stanno affiancati, cosi' la
 *              sezione si legge in due colpi d'occhio invece che in
 *              una colonna sola.
 *   FASCIA     r01 a tutta larghezza col payoff sopra: il respiro di
 *              meta' percorso, l'unico punto in cui si smette di
 *              leggere. Il payoff era gia' in pagina (era l'eco sotto
 *              la teoria): qui e' spostato, non aggiunto.
 *   MOVIMENTO 3 bianco: come lavoriamo, impaginato da rivista — il
 *              titolo in colonna a sinistra, i gesti a destra, e il
 *              badge staccato in un inciso col filo d'oro, perche' non
 *              e' un quarto gesto ma la provenienza di quello che si
 *              legge.
 *   MOVIMENTO 4 VERDE, l'unica ancora tonale: cosa non faremo mai. E'
 *              la parte piu' rara della pagina (nessuno pubblica i
 *              propri divieti) e ora ha il trattamento piu' forte:
 *              titolo piu' grande di tutti gli altri, i cinque no in
 *              display serif uno per riga separati da fili, e il
 *              doppio dell'aria sopra e sotto.
 *   FIRMA      i fondatori a mezza pagina di fotografia vera, non piu'
 *              in una colonna da cinque dodicesimi.
 *
 * ALTERNANZA DEI FONDI, come chiede la grammatica DS: scuro(foto) →
 * crema → sabbia → FOTO a tutta larghezza → bianco → VERDE → crema.
 * Due sezioni adiacenti non hanno mai lo stesso fondo.
 *
 * CONTRASTI MISURATI (minimo AA: 4,5:1 corpo, 3:1 display).
 *   apertura, crema #f6f2e8 sul velo di r04 ....... 8,84:1 / 7,96:1
 *   apertura, occhiello oro #d6c49a sul velo ...... 5,75:1
 *   fascia, payoff oro #ecd9a8 sul velo di r01 .... 5,44:1 / 4,89:1
 *   crema pieno su salvia #2f5749 ................. 7,28:1
 *   crema al 90% su salvia ........................ 6,26:1
 *   indice, voce attiva su crema .................. 13,61:1
 *   indice, voce a riposo (70%) su crema .......... 5,30:1
 *   indice, pastiglia attiva: crema su salvia ..... 7,28:1
 *   mov.2 frase display (85%) su sabbia ........... 7,93:1
 *   mov.3 inciso del badge (70%) su bianco ........ 5,45:1
 * (dove ci sono due numeri sono le misure a 1440px e a 390px, prese
 * sul pixel peggiore del riquadro che il testo occupa davvero)
 *
 * MOVIMENTO. Solo la dissolvenza d'ingresso del kit e lo scorrimento
 * morbido dell'indice, entrambi spenti da prefers-reduced-motion.
 * Nessuna parallasse, nessuna animazione che parte da sola.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, Lede, EditorialCta,
  PhotoOpener, PhotoBand, PhotoSplit, MovementIndex,
} from '../../components/editorial';

/* Le due fotografie assegnate a questa pagina dal magazzino (DS §Il
   magazzino foto). Sono due e non tre: le altre sono gia' su pagine
   vicine, e la stessa foto a due clic di distanza si nota subito. */
const OPENER_PHOTO = '/media/prelaunch/r04.jpg';  // mano in gyan mudra
const BAND_PHOTO = '/media/prelaunch/r01.jpg';    // al torrente, verde pieno
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';

/* L'indice riusa i titoli gia' approvati e tradotti: un indice non ha
   un copy proprio, ha i nomi delle cose a cui porta. Cade solo il punto
   fermo finale, che in una voce di navigazione non e' una frase ma un
   refuso: e' una scelta tipografica, non una riscrittura, e vale in
   tutte e quattro le lingue. */
const senzaPunto = (s) => String(s || '').replace(/\.\s*$/, '');

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

  /* Le quattro tappe navigabili. La teoria non c'e' perche' e'
     l'apertura: e' il posto da cui si parte, non una destinazione. */
  const movimenti = [
    { id: 'mf-mondo', label: senzaPunto(t('manifesto.worldTitle', { defaultValue: 'Il mondo come lo vediamo.' })) },
    { id: 'mf-lavoriamo', label: senzaPunto(t('manifesto.workTitle', { defaultValue: 'Come lavoriamo.' })) },
    { id: 'mf-mai', label: senzaPunto(t('manifesto.neverTitle', { defaultValue: 'Cosa non faremo mai.' })) },
    { id: 'mf-firma', label: senzaPunto(t('aboutPage.facesEyebrow', { defaultValue: 'Ci presentiamo' })) },
  ];
  const indiceLabel = t('manifesto.eyebrow', { defaultValue: 'Il manifesto' });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. LA TEORIA — l'apertura fotografica ────────────────
            La frase sola resta la frase sola: e' ancora l'unico h1 e
            non ha niente accanto. Cambia il fondo sotto, che da vuoto
            diventa una fotografia scura: la stessa frase, adesso,
            arriva dentro qualcosa invece che dentro il niente.
            L'occhiello e' in oro chiaro (eyebrow-light) perche' l'oro
            scuro nasce per i fondi chiari e qui sparirebbe. */}
        <PhotoOpener
          data-testid="mf-theory"
          image={OPENER_PHOTO}
          focus="52% 46%"
          height="tall"
          align="left"
          width="max-w-3xl"
          labelledBy="mf-theory-title"
          eyebrow={t('manifesto.eyebrow', { defaultValue: 'Il manifesto' })}
        >
          <DisplayTitle as="h1" id="mf-theory-title" size="manifesto" measure="wide" className="text-hero-shadow">
            {t('manifesto.theoryTitle', { defaultValue: 'Ogni percorso di benessere inizia da un incontro di fiducia.' })}
          </DisplayTitle>
        </PhotoOpener>

        {/* ── LA SOGLIA — le due righe che spiegano, sul chiaro ────
            Stessa scelta della landing operatori: il titolo sta sulla
            foto, l'argomento si legge sul chiaro. Qui sotto compare
            anche l'indice nella sua forma da telefono: subito dopo
            l'apertura, che e' il momento in cui serve sapere quanto e'
            lunga la pagina. */}
        <Section tone="cream" rhythm="flow" width="max-w-3xl">
          <div data-testid="mf-soglia">
            <Lede size="lead">
              {t('manifesto.theoryBody', { defaultValue: 'Non si sceglie una disciplina. Si sceglie una persona, e le si affida qualcosa di intimo. Tutto quello che facciamo parte da qui.' })}
            </Lede>
            <MovementIndex items={movimenti} label={indiceLabel} variant="row" className="mt-10" />
          </div>
        </Section>

        {/* ── I MOVIMENTI ──────────────────────────────────────────
            Il contenitore `relative` esiste per una ragione sola: e' la
            regione in cui l'indice a colonna ha senso. Comincia col
            primo movimento e finisce con l'ultimo; sopra c'e'
            l'apertura e sotto c'e' la firma, e in nessuno dei due
            l'indice avrebbe qualcosa da indicare. */}
        <div className="relative">
          <MovementIndex items={movimenti} label={indiceLabel} variant="rail" />

          {/* ── 2. IL MONDO COME LO VEDIAMO ────────────────────────
              Constatazione, mai lamento: il terzo capoverso lo dice
              esplicitamente ("non e' colpa di nessuno") e riporta il
              discorso sul lettore.
              DS1 — la prima riga passa al corpo display e diventa il
              perno: e' una frase di sei parole, e in corpo di lettura
              si perdeva fra le altre due. Gli altri due capoversi si
              affiancano: sono paralleli, e messi in colonna sembravano
              una spiegazione lunga il doppio di quello che e'. */}
          <Section tone="sand" rhythm="screen" width="max-w-3xl"
                   id="mf-mondo" labelledBy="mf-world-title"
                   className="scroll-mt-20 outline-none">
            <div data-testid="mf-world">
              <DisplayTitle as="h2" id="mf-world-title" size="section" measure="title">
                {t('manifesto.worldTitle', { defaultValue: 'Il mondo come lo vediamo.' })}
              </DisplayTitle>
              <DisplayTitle as="p" size="section" measure="wide"
                            className="mt-8 text-[1.5rem] leading-[1.22] text-foreground/85 sm:text-[1.9rem] lg:text-[2.1rem]">
                {t('manifesto.worldP1', { defaultValue: 'Trovare qualcuno di cui fidarsi è difficile.' })}
              </DisplayTitle>
              <div aria-hidden className="gold-rule mt-9 max-w-[10rem]" />
              <div className="mt-9 grid gap-7 sm:gap-10 lg:grid-cols-2">
                <Lede size="body">
                  {t('manifesto.worldP2', { defaultValue: 'Profili ovunque, appigli da nessuna parte. Le promesse sono tante e le persone si vedono poco. Chi lavora bene sparisce in mezzo a chi promette di più.' })}
                </Lede>
                <Lede size="body">
                  {t('manifesto.worldP3', { defaultValue: 'Non è colpa di nessuno. Ma quando la scelta è così personale, hai bisogno di sapere chi hai davanti.' })}
                </Lede>
              </div>
            </div>
          </Section>

          {/* ── LA FASCIA — il respiro di meta' percorso ───────────
              r01 da bordo a bordo, col payoff dentro l'immagine. Il
              payoff era gia' in pagina e fa lo stesso mestiere di
              prima (l'eco della teoria): e' spostato dove serve, cioe'
              nel punto in cui la lettura ha bisogno di fermarsi. E'
              anche l'unica volta in cui la pagina esce dalla sua
              colonna prima della firma. */}
          <PhotoBand image={BAND_PHOTO} focus="50% 34%" width="max-w-3xl">
            <BrandPayoff tone="hero" size="band" className="max-w-[22ch]" />
          </PhotoBand>

          {/* ── 3. COME LAVORIAMO — i gesti ────────────────────────
              Tre coppie parallele (verita' sul mondo → nostro gesto) e
              poi il badge, che non e' un quarto gesto: e' la
              provenienza di quello che il lettore trovera' scritto, e
              per questo si stacca in un inciso col filo d'oro invece
              di essere il quarto capoverso di fila. Fondo bianco, il
              punto piu' luminoso della pagina, prima del verde. */}
          <Section tone="paper" rhythm="screen" width="max-w-3xl"
                   id="mf-lavoriamo" labelledBy="mf-work-title"
                   className="scroll-mt-20 outline-none">
            <div data-testid="mf-work" className="grid gap-8 lg:grid-cols-12 lg:gap-10">
              <div className="lg:col-span-4">
                <DisplayTitle as="h2" id="mf-work-title" size="section" measure="tight"
                              className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                  {t('manifesto.workTitle', { defaultValue: 'Come lavoriamo.' })}
                </DisplayTitle>
              </div>
              <div className="lg:col-span-8">
                <Lede size="body">
                  {t('manifesto.workP1', { defaultValue: 'Per conoscere qualcuno ci vuole tempo. Ce lo prendiamo: incontriamo le persone una a una.' })}
                </Lede>
                <Lede size="body" className="mt-5">
                  {t('manifesto.workP2', { defaultValue: 'Le domande gentili non bastano. Ne facciamo anche di scomode, e ascoltiamo le risposte.' })}
                </Lede>
                <Lede size="body" className="mt-5">
                  {t('manifesto.workP3', { defaultValue: 'Le cose serie vanno spiegate. Scriviamo quello che abbiamo capito, anche i limiti: per chi è una pratica, e per chi non è.' })}
                </Lede>
                <div className="mt-9 border-l-2 border-[#7d6a3a]/50 pl-5 sm:pl-6">
                  <Lede size="body" tone="quiet">
                    {t('manifesto.workBadge', { defaultValue: 'Quando un profilo nasce così, lo trovi segnato: Verificato Aurya. Non è una medaglia. Ti dice da dove viene quello che stai leggendo.' })}
                  </Lede>
                </div>
              </div>
            </div>
          </Section>

          {/* ── 4. COSA NON FAREMO MAI — l'ancora verde ────────────
              La lista dei divieti resa pubblica e' un atto di fiducia:
              nessun altro la scrive. Per questo e' la sezione col
              trattamento piu' forte della pagina, e non piu' una
              sezione come le altre che capita di trovare sul verde:
              titolo piu' grande di ogni altro, i cinque no in display
              serif uno per riga con un filo a separarli, e il doppio
              dell'aria sopra e sotto (il ritmo lo mette qui il
              contenuto, per questo rhythm="none").
              Ogni riga a piena opacita' (7,28:1); intro e chiusa al
              90% (6,26:1). I fili sono decorativi, non testo. */}
          <Section tone="sage" rhythm="none" width="max-w-3xl"
                   id="mf-mai" labelledBy="mf-never-title"
                   className="scroll-mt-20 outline-none"
                   innerClassName="py-24 sm:py-32 lg:py-40">
            <div data-testid="mf-never">
              <DisplayTitle as="h2" id="mf-never-title" size="section" measure="title"
                            className="text-[2.4rem] sm:text-[3.2rem] lg:text-[4rem] lg:leading-[1.04]">
                {t('manifesto.neverTitle', { defaultValue: 'Cosa non faremo mai.' })}
              </DisplayTitle>
              <Lede size="lead" tone="inherit" className="mt-7 opacity-90">
                {t('manifesto.neverIntro', { defaultValue: 'Una promessa vale per quello che esclude. Questa lista è pubblica: puoi ricordarcela quando vuoi.' })}
              </Lede>
              <ul className="mt-12 list-none border-t border-[#f6f2e8]/20 p-0 sm:mt-14">
                {nevers.map((riga) => (
                  <li key={riga} className="border-b border-[#f6f2e8]/20 py-6 sm:py-7">
                    <p className="font-display text-balance text-[1.45rem] leading-[1.22] sm:text-[1.8rem] lg:text-[2rem]">
                      {riga}
                    </p>
                  </li>
                ))}
              </ul>
              <Lede size="body" tone="inherit" className="mt-10 opacity-90">
                {t('manifesto.neverClose', { defaultValue: 'Ogni no è anche un limite che ci diamo. Ma chi ammette un limite viene creduto sul resto.' })}
              </Lede>
            </div>
          </Section>
        </div>

        {/* ── FIRMA — i fondatori, col materiale reale ─────────────
            Foto vera e testo gia' esistente (aboutPage.faces*, x4): qui
            non si inventa niente, si firma.
            DS1 — la fotografia passa da cinque dodicesimi di colonna a
            mezza pagina piena, fino al bordo dello schermo: e' l'unica
            foto nostra del sito, e in un francobollo non si vedeva chi
            firma. Il ritratto sta a sinistra perche' e' la prima cosa
            che si incontra scendendo dal verde, e perche' e' l'unico
            split della pagina: non c'e' un lato da alternare.
            Le due CTA finali restano discrete apposta: dopo una pagina
            di posizione, la porta giusta e' un filo sotto il testo, non
            un bottone. */}
        <PhotoSplit
          id="mf-firma"
          image={FOUNDERS_PHOTO}
          imageAlt={t('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
          focus="50% 38%"
          side="left"
          tone="cream"
          imageWidth="900"
          imageHeight="886"
          labelledBy="mf-sign-title"
          className="scroll-mt-20 outline-none"
        >
          <div data-testid="mf-sign">
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
        </PhotoSplit>

      </div>
    </MarketplaceShell>
  );
}
