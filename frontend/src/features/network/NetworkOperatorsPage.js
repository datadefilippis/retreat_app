/**
 * NetworkOperatorsPage — /operatori (SW5, redesign sul Blueprint).
 *
 * Dallo schema "elenco con criteri" allo schema LE PERSONE
 * (AURYA_BLUEPRINT_2026-07 cap. 2: "le persone vengono prima delle
 * discipline"). Quattro battute:
 *   1. APERTURA     dietro ogni pratica c'e' qualcuno, e qui lo vedi
 *   2. COME SI ENTRA i criteri riscritti come GESTI nostri, non come
 *                    requisiti tuoi (cap. 2.3: il criterio e' invisibile,
 *                    si dice il gesto e mai il giudizio)
 *   3. LE PERSONE    le schede grandi: foto, nome, pratica, luogo e UNA
 *                    citazione presa dall'intervista
 *   4. L'INVITO      l'unica ancora verde, poi la porta della candidatura
 *
 * LA CITAZIONE. Arriva da /public/network/members (campo `quote`), che
 * la espone SOLO a intervista pubblicata: la sceglie a mano il system
 * admin nell'editor dell'intervista. Non e' un estratto automatico, ed
 * e' giusto cosi': quale frase valga la pena leggere sotto un nome lo
 * sa solo chi quella conversazione l'ha fatta. Senza citazione la
 * scheda non si rompe (PersonCard ripiega sulla tagline) e senza
 * nessuna delle due resta il volto col nome: e' comunque una persona.
 *
 * NON E' UNA DIRECTORY, e con pochi profili nemmeno lo sembra: niente
 * filtri, niente conteggi, niente prezzi. Il listino resta sul profilo,
 * dove ha un senso; qui vale solo chi e' quella persona. I filtri
 * tornano a 25+ profili, URL invariato; in fase marketplace questo URL
 * torna all'aggregatore pieno (OperatorsGate).
 *
 * Fondi: crema, sabbia, bianco, VERDE. Una sola ancora tonale, in
 * chiusura. Contrasti misurati sul salvia #2f5749: crema piena 7,28:1,
 * crema al 90% 6,24:1 (minimo AA 4,5:1). Movimento: solo il reveal del
 * kit (dissolvenza, reduced-motion rispettato).
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, TitleLine, Lede, PersonCard, EditorialCta,
} from '../../components/editorial';

export default function NetworkOperatorsPage() {
  const { t } = useTranslation('landings');
  const [members, setMembers] = useState(null);   // null = caricamento

  useSeoMeta({
    title: t('nwOps.seoTitle', { defaultValue: 'Le persone della rete | Aurya' }),
    // 146 caratteri: chi sono e da dove viene quello che leggerai. Taglio a 158.
    description: t('nwOps.seoDesc', { defaultValue: 'Gli operatori della rete Aurya, incontrati uno a uno: chi sono, cosa praticano, dove lavorano. Accanto a ogni nome una frase presa dalla loro voce.' }),
    canonicalPath: '/operatori',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/network/members')
      .then(res => { if (mounted) setMembers(res.data?.items || []); })
      .catch(() => { if (mounted) setMembers([]); });
    return () => { mounted = false; };
  }, []);

  /* La griglia si stringe quando le persone sono poche: tre colonne
     con due schede lasciano un buco che sembra un errore di
     caricamento, e in fase rete essere pochi non e' un difetto da
     nascondere (Blueprint cap. 5: la lentezza si racconta, non si
     maschera). Da tre in su la pagina respira su tre colonne. */
  const few = !members || members.length <= 2;
  const gridCols = few
    ? 'sm:grid-cols-2 max-w-3xl'
    : 'sm:grid-cols-2 lg:grid-cols-3';

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA ──────────────────────────────────────────
            Due frasi, due righe volute (<TitleLine>): la prima e' la
            verita' sul mondo, la seconda il gesto. Mai l'ordine
            inverso, sennò diventa pubblicita' (Blueprint cap. 9). */}
        <Section tone="cream" rhythm="hero" labelledBy="nw-open-title">
          <div data-testid="nw-open">
            <p className="eyebrow mb-5">
              {t('nwOps.eyebrow', { defaultValue: 'La rete' })}
            </p>
            <DisplayTitle as="h1" id="nw-open-title" size="heroLines" measure="lines">
              <TitleLine>
                {t('nwOps.line1', { defaultValue: 'Dietro ogni pratica c’è una persona.' })}
              </TitleLine>
              <TitleLine>
                {t('nwOps.line2', { defaultValue: 'Qui la puoi conoscere.' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-8">
              {t('nwOps.lead', { defaultValue: 'Le persone di questa pagina le abbiamo incontrate una a una. Quello che leggi accanto al loro nome l’hanno detto loro.' })}
            </Lede>
            <BrandPayoff tone="cream" size="sm" className="mt-9" />
          </div>
        </Section>

        {/* ── 2. COME SI ENTRA — i gesti, non i requisiti ──────────
            Prima erano tre righe numerate che dicevano al lettore cosa
            doveva avere ("una pratica reale", "la disponibilita' a
            raccontarsi"): una lista di requisiti e' un giudizio
            travestito. Qui sono tre coppie parallele in prima persona
            plurale, e la chiusa toglie di mezzo l'idea della soglia da
            superare. */}
        <Section tone="sand" rhythm="screen" labelledBy="nw-how-title">
          <div data-testid="nw-how">
            <DisplayTitle as="h2" id="nw-how-title" size="section" measure="title">
              {t('nwOps.howTitle', { defaultValue: 'Come si entra.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('nwOps.howP1', { defaultValue: 'Un profilo si compila in cinque minuti. Una persona no: la andiamo a conoscere, e per quello ci vuole tempo.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwOps.howP2', { defaultValue: 'Le domande gentili dicono poco. Ne facciamo anche di scomode, e teniamo le risposte per intero, senza riassumerle.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwOps.howP3', { defaultValue: 'Chi legge merita di sapere da dove viene un racconto. Firmiamo il nostro: i profili nati così portano il segno Verificato Aurya.' })}
            </Lede>
            <Lede size="body" tone="quiet" className="mt-8">
              {t('nwOps.howClose', { defaultValue: 'Non c’è un modulo che apre questa porta. C’è una conversazione, e il tempo che serve a farla bene.' })}
            </Lede>
          </div>
        </Section>

        {/* ── 3. LE PERSONE — le schede grandi ─────────────────────
            Fondo bianco: e' il punto piu' luminoso della pagina, e i
            ritratti si staccano come oggetti. L'ordine di lettura lo
            decide PersonCard (volto → nome → pratica e luogo → sigillo
            → voce): qui la pagina mette solo il ritmo della griglia.
            "Leggi l'intervista" e' un link VERO alla pagina dedicata
            (PV3), e compare solo dove l'intervista e' pubblicata. */}
        <Section tone="paper" rhythm="screen" labelledBy="nw-people-title"
                 width="max-w-6xl">
          <div data-testid="nw-people">
            <DisplayTitle as="h2" id="nw-people-title" size="section" measure="title">
              {t('nwOps.peopleTitle', { defaultValue: 'Le persone.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-5">
              {t('nwOps.peopleSub', { defaultValue: 'Sono poche, e le conosciamo tutte. Continueranno ad arrivare una alla volta.' })}
            </Lede>

            {members === null ? (
              /* /70 e non /60: al 60% il testo scende a 4,03:1, sotto
                 il minimo AA. Stessa soglia del tono `quiet` del kit. */
              <p className="mt-10 text-sm text-foreground/70" aria-live="polite">
                {t('nwOps.loading', { defaultValue: 'Un momento.' })}
              </p>
            ) : members.length === 0 ? (
              /* Stato vuoto onesto: nessun riquadro tratteggiato che
                 gridi "manca qualcosa". Una riga che dice come stanno
                 davvero le cose, nel tono del resto della pagina. */
              <div data-testid="nw-people-empty">
                <Lede size="body" tone="quiet" className="mt-10">
                  {t('nwOps.peopleEmpty', { defaultValue: 'Le prime interviste sono in corso. I profili arrivano qui quando sono pronti a essere raccontati bene, non prima.' })}
                </Lede>
              </div>
            ) : (
              <ul className={`mt-12 grid list-none gap-x-8 gap-y-14 p-0 sm:mt-14 ${gridCols}`}>
                {members.map(m => (
                  <li key={m.slug} data-testid="nw-person">
                    <PersonCard
                      person={{
                        ...m,
                        // la pratica arriva come slug stabile: la label
                        // la risolve l'i18n, come nell'aggregatore
                        category: m.category
                          ? t(`categories.${m.category}`, { defaultValue: m.category })
                          : null,
                      }}
                      /* 280 = il tetto che il system admin ha gia'
                         davanti quando sceglie la frase. Tagliarla
                         una seconda volta qui vorrebbe dire mettere
                         dei puntini su una scelta editoriale gia'
                         fatta: chi l'ha scritta sa dove finisce. */
                      quoteMaxChars={280}
                    />
                    {m.has_interview && (
                      <p className="mt-4">
                        <EditorialCta to={`/o/${m.slug}/intervista`} variant="quiet">
                          {t('nwOps.readInterview', { defaultValue: 'Leggi l’intervista' })}
                        </EditorialCta>
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Section>

        {/* ── 4. L'INVITO — l'unica ancora verde ───────────────────
            Chi e' arrivato in fondo ha appena letto delle persone: la
            domanda giusta non e' "iscriviti", e' "vuoi farne parte".
            Due porte: la candidatura e il manifesto, per chi prima
            vuole sapere come la pensiamo. */}
        <Section tone="sage" rhythm="screen" labelledBy="nw-join-title">
          <div data-testid="nw-join">
            <DisplayTitle as="h2" id="nw-join-title" size="section" measure="tight">
              {t('nwOps.joinTitle', { defaultValue: 'Vuoi farne parte?' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7">
              {t('nwOps.joinBody', { defaultValue: 'Se lavori nel benessere e ti va di raccontarti, il primo passo è parlarne. Ci dici chi sei e cosa fai, e vediamo se c’è sintonia.' })}
            </Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/entra-nella-rete" variant="light"
                            data-testid="nw-join-cta">
                {t('nwOps.joinCta', { defaultValue: 'Entra nella rete' })}
              </EditorialCta>
              <EditorialCta to="/manifesto" variant="light"
                            data-testid="nw-join-cta-alt">
                {t('nwOps.joinCtaAlt', { defaultValue: 'Leggi il manifesto' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
