/**
 * AziendePage — /aziende: «Aurya per le aziende» (P13, 10/9/2026, piano
 * di business §3.1 B).
 *
 * Decisione founder (10/9 sera): NON solo la Masseria, NIENTE formati
 * pre-fatti con prezzo («non li abbiamo ancora, vanno studiati»). Un
 * servizio ON DEMAND: Aurya si presenta come team building e ritiri
 * aziendali, esperienze costruite ad hoc con la rete di operatori e di
 * strutture, condotte dai professionisti o da Valentina e Davide, con
 * un prezzo pattuito su cio' che l'azienda vuole. La richiesta finisce
 * nelle «richieste» del pannello (tipo team_building): la proposta la
 * scrivono Davide e Valentina.
 *
 * Regole della casa: niente che non abbiamo (niente prezzi, niente
 * formati, niente foto), nessuna urgenza. Solo italiano.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { BRAND_EMAIL } from '../../config/brand';
import { Section, DisplayTitle, Lede, EditorialCta } from '../../components/editorial';

const input = 'mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring';

const COSA = [
  { k: 'giorno', nome: 'Team building di un giorno', cosa: 'Mezza giornata o una giornata intera, in una struttura della rete scelta con voi: respiro, suono, yoga, un cammino, un cerchio di chiusura.' },
  { k: 'ritiro', nome: 'Ritiri aziendali', cosa: 'Due o tre giorni fuori, con un programma che alterna pratica, cammino e tempo vuoto. Si dorme in una struttura che conosciamo di persona.' },
  { k: 'momento', nome: 'Un momento dentro un evento vostro', cosa: 'Un’ora di respiro o di suono dentro una convention, un kick-off, una giornata di formazione. Arriviamo noi.' },
];

const FAQ = [
  ['Quante persone?', 'Dipende da cosa volete fare: dai team piccoli ai gruppi grandi, con più professionisti quando servono. Ce lo dite, e costruiamo su quello.'],
  ['Dove?', 'In una struttura della rete Aurya, scelta con voi: vicino a dove siete quando possibile, fuori città quando il senso è staccare.'],
  ['Serve esperienza di yoga o meditazione?', 'No. Tutto è guidato e pensato per chi comincia. Chi non vuole fare una cosa la guarda, e va bene così.'],
  ['Chi conduce, davvero?', 'I professionisti della rete Aurya, con nome e volto: li trovate nella pagina dei professionisti. E Valentina e Davide, che l’hanno fondata. Sono pagati per il loro lavoro.'],
  ['Quanto costa?', 'Non c’è un listino: il prezzo si pattuisce sulla proposta, dopo la chiamata, e sta scritto tutto nella proposta. Conferma con una caparra con bonifico, saldo dopo, una fattura sola, di Aurya.'],
];

function Modulo() {
  const [f, setF] = useState({ azienda: '', nome: '', email: '', telefono: '', persone: '', periodo: '', messaggio: '' });
  const [busy, setBusy] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState('');
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const invia = async (e) => {
    e.preventDefault();
    setErrore('');
    if (!f.azienda.trim() || !f.nome.trim() || !f.email.trim() || !f.persone || !f.periodo.trim()) {
      setErrore('Servono azienda, nome, email, persone e periodo.');
      return;
    }
    setBusy(true);
    try {
      await api.post('/public/aziende/richiesta', {
        azienda: f.azienda.trim(), nome: f.nome.trim(), email: f.email.trim(),
        telefono: f.telefono.trim() || null, persone: Number(f.persone),
        periodo: f.periodo.trim(), messaggio: f.messaggio.trim() || null,
      });
      setFatto(true);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setErrore(typeof d === 'string' ? d : 'Richiesta non inviata. Riprovate, o scriveteci a ' + BRAND_EMAIL + '.');
    } finally { setBusy(false); }
  };

  if (fatto) {
    return (
      <div data-testid="az-fatto" className="rounded-[1.5rem] border border-border bg-card p-6">
        <p className="font-display text-2xl text-foreground">Ricevuta.</p>
        <p className="mt-2 text-base text-muted-foreground">
          Vi scriviamo entro due giorni lavorativi per fissare una chiamata. Vi abbiamo mandato una ricevuta via email.
        </p>
      </div>
    );
  }
  return (
    <form onSubmit={invia} data-testid="az-form" className="rounded-[1.5rem] border border-border bg-card p-6 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm"><span className="text-muted-foreground">Azienda</span>
          <input value={f.azienda} onChange={set('azienda')} className={input} required data-testid="az-azienda" /></label>
        <label className="block text-sm"><span className="text-muted-foreground">Chi scrive</span>
          <input value={f.nome} onChange={set('nome')} className={input} required placeholder="nome e cognome" /></label>
        <label className="block text-sm"><span className="text-muted-foreground">Email</span>
          <input type="email" value={f.email} onChange={set('email')} className={input} required data-testid="az-email" /></label>
        <label className="block text-sm"><span className="text-muted-foreground">Telefono (se volete essere chiamati)</span>
          <input value={f.telefono} onChange={set('telefono')} className={input} /></label>
        <label className="block text-sm"><span className="text-muted-foreground">Quante persone</span>
          <input type="number" min={1} max={500} value={f.persone} onChange={set('persone')} className={input} required data-testid="az-persone" /></label>
        <label className="block text-sm"><span className="text-muted-foreground">Periodo</span>
          <input value={f.periodo} onChange={set('periodo')} className={input} required placeholder="es. fine novembre, o primavera 2027" data-testid="az-periodo" /></label>
        <label className="block text-sm sm:col-span-2"><span className="text-muted-foreground">Cosa avete in mente</span>
          <textarea rows={4} value={f.messaggio} onChange={set('messaggio')} className={input} data-testid="az-messaggio"
                    placeholder="l’occasione, il gruppo, cosa vorreste portare a casa, un giorno o più giorni, vicino o lontano" /></label>
      </div>
      {errore && <p className="text-sm text-red-700" data-testid="az-errore">{errore}</p>}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">Nessun impegno: la proposta è scritta, e decidete dopo averla letta.</p>
        <button type="submit" disabled={busy} data-testid="az-invia"
                className="rounded-full bg-[#2f5749] px-6 py-3 text-sm font-semibold text-white disabled:opacity-60">
          {busy ? 'Invio…' : 'Raccontateci cosa volete'}
        </button>
      </div>
    </form>
  );
}

export default function AziendePage() {
  useSeoMeta({
    title: 'Aurya per le aziende | Team building e ritiri aziendali su misura',
    description: 'Esperienze di team building e ritiri aziendali costruiti su misura per il vostro team, con la rete Aurya di professionisti del benessere e di strutture. Prezzo pattuito su quello che volete.',
    canonicalPath: '/aziende',
  });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <Section tone="cream" rhythm="screen" width="max-w-5xl" labelledBy="az-title">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Aurya per le aziende</p>
          <DisplayTitle as="h1" id="az-title" size="hero" measure="title" className="mt-4">
            Team building e ritiri aziendali, costruiti su misura.
          </DisplayTitle>
          <Lede size="lead" className="mt-6">
            Un’esperienza per il vostro team pensata da zero su di voi: respiro, suono, yoga, un cammino,
            un cerchio, una notte fuori. La costruiamo con la rete Aurya: professionisti del benessere che
            fanno questo lavoro ogni giorno e strutture che conosciamo di persona. Niente slide, niente giochi di ruolo.
          </Lede>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:gap-6">
            <EditorialCta href="#az-modulo" variant="solid" data-testid="az-cta-hero">Raccontateci cosa volete</EditorialCta>
            <EditorialCta href="#az-cosa" variant="quiet">Cosa facciamo</EditorialCta>
          </div>
        </Section>

        <Section tone="sand" rhythm="flow" width="max-w-5xl" labelledBy="az-cosa-title">
          <div id="az-cosa" data-testid="az-cosa">
            <DisplayTitle as="h2" id="az-cosa-title" size="section" measure="title">Cosa facciamo.</DisplayTitle>
            <div className="mt-8 grid gap-6 md:grid-cols-3">
              {COSA.map((x) => (
                <article key={x.k} className="flex flex-col rounded-[1.5rem] border border-border bg-card p-6" data-testid={`az-cosa-${x.k}`}>
                  <h3 className="font-display text-2xl text-foreground">{x.nome}</h3>
                  <p className="mt-3 text-sm text-muted-foreground">{x.cosa}</p>
                </article>
              ))}
            </div>
            <p className="mt-6 text-sm text-muted-foreground">
              Nessun pacchetto: ogni esperienza nasce dalla chiamata con voi. Cambiano le persone, il posto, la durata, il ritmo.
            </p>
          </div>
        </Section>

        <Section tone="paper" rhythm="flow" width="max-w-5xl" labelledBy="az-chi-title">
          <div className="grid gap-10 md:grid-cols-2" data-testid="az-chi-rete">
            <div>
              <DisplayTitle as="h2" id="az-chi-title" size="section" measure="title">Chi conduce.</DisplayTitle>
              <p className="mt-4 text-base text-muted-foreground">
                I professionisti della rete Aurya: insegnanti di yoga e respiro, operatori del suono, guide di cammino,
                facilitatori di cerchi. Persone che fanno questo lavoro ogni giorno e che trovate, con nome e volto,
                <Link to="/operatori" className="underline"> tra i professionisti di Aurya</Link>. E Valentina e Davide,
                che l’hanno fondata. Scegliamo le persone giuste per il vostro gruppo, e le paghiamo per il loro lavoro.
              </p>
            </div>
            <div>
              <DisplayTitle as="h2" size="section" measure="title">La rete.</DisplayTitle>
              <p className="mt-4 text-base text-muted-foreground">
                Aurya è una rete: professionisti del benessere raccontati uno a uno, e strutture per i ritiri viste di
                persona. Per un’azienda vuol dire una cosa sola: non un fornitore con un catalogo, ma persone e posti
                scelti per voi, ogni volta.
              </p>
            </div>
          </div>
        </Section>

        <Section tone="cream" rhythm="flow" width="max-w-5xl" labelledBy="az-come-title">
          <div data-testid="az-come">
            <DisplayTitle as="h2" id="az-come-title" size="section" measure="title">Come funziona.</DisplayTitle>
            <ol className="mt-8 grid gap-6 md:grid-cols-3">
              {[
                ['Ci scrivete', 'Quante persone, quando, cosa vorreste portare a casa. Due minuti, qui sotto.'],
                ['Vi chiamiamo', 'Entro due giorni lavorativi. Poi arriva una proposta scritta: programma, chi conduce, dove, e il prezzo, pattuito su quello che volete.'],
                ['Fissiamo la data', 'Conferma con una caparra con bonifico, saldo dopo. Una fattura sola, di Aurya.'],
              ].map(([t, b], i) => (
                <li key={t} className="rounded-[1.5rem] border border-border bg-card p-6">
                  <p className="font-display text-3xl text-[#2f5749]">{i + 1}</p>
                  <p className="mt-2 font-semibold text-foreground">{t}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{b}</p>
                </li>
              ))}
            </ol>
          </div>
        </Section>

        <Section tone="sage" rhythm="flow" width="max-w-3xl" labelledBy="az-modulo-title">
          <div id="az-modulo">
            <DisplayTitle as="h2" id="az-modulo-title" size="section" measure="title">Raccontateci cosa volete.</DisplayTitle>
            <div className="mt-8"><Modulo /></div>
            <p className="mt-4 text-sm text-muted-foreground">
              Preferite scrivere? <a href={`mailto:${BRAND_EMAIL}`} className="underline">{BRAND_EMAIL}</a>
            </p>
          </div>
        </Section>

        <Section tone="paper" rhythm="flow" width="max-w-3xl" labelledBy="az-faq-title">
          <div data-testid="az-faq">
            <DisplayTitle as="h2" id="az-faq-title" size="section" measure="title">Le domande vere.</DisplayTitle>
            <dl className="mt-8 divide-y divide-border">
              {FAQ.map(([q, a]) => (
                <div key={q} className="py-5">
                  <dt className="font-semibold text-foreground">{q}</dt>
                  <dd className="mt-1 text-sm text-muted-foreground">{a}</dd>
                </div>
              ))}
            </dl>
          </div>
        </Section>
      </div>
    </MarketplaceShell>
  );
}
