/**
 * SoundHubPage — IL SUONO, l'hub (SN1, 8/10/2026, piano Aurya Sound §4.0).
 *
 * /sound smette di essere una seconda home con la sua vetrina: e' la porta
 * di chi vuole CAPIRE il suono, con tre riquadri (le schede delle
 * frequenze, le fondamenta col glossario, il Lab) e il rimando alla casa
 * delle meditazioni per chi vuole ascoltare. Chi compone trova Crea
 * dall'omino, non qui. Luce del sito (guscio chiaro), come la landing che
 * sostituisce.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import MarketplaceShell from '../../storefront/components/MarketplaceShell';
import useSeoMeta from '../../storefront/lib/useSeoMeta';
import { Section, DisplayTitle, Lede } from '../../../components/editorial';
import { BIB } from '../content/biblioteca';

const RIQUADRI = [
  { to: '/sound/esplora', titolo: 'Esplora le frequenze', testo: 'Le schede: bande cerebrali, altre frequenze, metodi. Cosa sono, a cosa servono, come si ascoltano.', eyebrow: 'Le schede' },
  { to: '/sound/impara', titolo: 'Le fondamenta', testo: 'Come funziona il suono che accompagna una meditazione, con parole semplici e un glossario.', eyebrow: 'Impara' },
  { to: '/sound/lab', titolo: 'Il Lab', testo: 'Cinque stanze per provare con le orecchie: banco, orecchio, ritratto, meraviglie, risonanze.', eyebrow: 'Prova' },
];

export default function SoundHubPage() {
  const schede = Object.values(BIB || {}).reduce((n, lista) => n + (Array.isArray(lista) ? lista.length : 0), 0);
  useSeoMeta({
    title: 'Aurya Sound | Il suono che accompagna le meditazioni',
    description: 'Le frequenze, le fondamenta e il Lab di Aurya Sound: capire il suono prima di ascoltarlo. Le meditazioni si ascoltano nella casa delle meditazioni.',
    canonicalPath: '/sound',
  });
  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="sound-hub">
        <Section tone="cream" rhythm="screen" width="max-w-4xl" id="sound-hub-testa" labelledBy="sound-hub-title">
          <p className="eyebrow">Aurya Sound</p>
          <DisplayTitle as="h1" id="sound-hub-title" size="section" measure="title">Il suono, spiegato.</DisplayTitle>
          <Lede size="lead" className="mt-6">
            Dietro ogni meditazione di Aurya c'è un suono composto apposta: frequenze, basi, voce. Qui lo capisci prima di ascoltarlo.
          </Lede>
          <div className="mt-10 grid gap-4 sm:grid-cols-3" data-testid="sound-hub-riquadri">
            {RIQUADRI.map((r) => (
              <Link key={r.to} to={r.to} className="group rounded-2xl border border-gray-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-md">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8a7440]">{r.eyebrow}{r.to === '/sound/esplora' && schede ? ` · ${schede}` : ''}</p>
                <h2 className="mt-1 font-display text-xl text-gray-900">{r.titolo}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{r.testo}</p>
              </Link>
            ))}
          </div>
        </Section>
        <Section tone="sand" rhythm="screen" width="max-w-4xl" id="sound-hub-ascolta" labelledBy="sound-hub-ascolta-title">
          <DisplayTitle as="h2" id="sound-hub-ascolta-title" size="section" measure="title">Vuoi ascoltare?</DisplayTitle>
          <Lede size="body" className="mt-4">Le meditazioni composte dai professionisti della rete, con playlist e copertine, vivono nella loro casa. L'assaggio di novanta secondi è per tutti; l'ascolto intero per chi è nel Cerchio di Aurya.</Lede>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/meditazioni" className="inline-flex min-h-[46px] items-center rounded-full bg-[#2f5749] px-6 text-sm font-semibold text-white" data-testid="sound-hub-meditazioni">Le meditazioni</Link>
            <Link to="/newsletter" className="inline-flex min-h-[46px] items-center rounded-full border border-gray-300 bg-white px-6 text-sm font-medium text-gray-800">Il Cerchio</Link>
          </div>
        </Section>
      </div>
    </MarketplaceShell>
  );
}
