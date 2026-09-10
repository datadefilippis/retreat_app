/**
 * AziendePage — /aziende: «Aurya per le aziende» (P13, 10/9/2026, piano
 * di business §3.1 B).
 *
 * Il team building alla Masseria e' il servizio a margine piu' alto e
 * piu' veloce, e da' lavoro pagato ai professionisti della rete. Un'
 * azienda ci ha gia' contattati. La pagina e' una landing con un modulo:
 * due formati con prezzo «da», chi conduce, dove, come funziona, le
 * domande vere. La richiesta finisce nelle «richieste» del pannello
 * (tipo team_building): il preventivo lo scrivono Davide e Valentina.
 *
 * Regole della casa: niente che non abbiamo (niente foto finche' non ci
 * sono le tre della sala a volta; niente sedi «da voi»), nessuna
 * urgenza, i prezzi del piano e basta. Solo italiano.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { BRAND_EMAIL } from '../../config/brand';
import { Section, DisplayTitle, Lede, EditorialCta } from '../../components/editorial';

const input = 'mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring';

const FORMATI = [
  { k: 'giornata', nome: 'Giornata «Respiro»', durata: '6 ore', prezzo: 'da 130 € a persona', nota: 'minimo 12 persone',
    cosa: 'Accoglienza, respiro e suono con Valentina e un professionista della rete, pranzo, cerchio di chiusura.' },
  { k: 'due_giorni', nome: 'Due giorni «Rientro»', durata: 'con pernotto', prezzo: 'da 320 € a persona', nota: 'dalle 12 alle 25 persone',
    cosa: 'Yoga al mattino, un cammino, il suono la sera, i pasti. Si dorme alla Masseria.' },
  { k: 'su_misura', nome: 'Su misura', durata: 'oltre le 25 persone', prezzo: 'preventivo', nota: 'o un programma vostro',
    cosa: 'Ci dite cosa avete in mente: vi diciamo cosa possiamo fare, con chi, e quanto costa.' },
];

const FAQ = [
  ['Quante persone?', 'Dalle 12 alle 25 per i due formati. Oltre, su misura: dipende dalla sala e da quanti professionisti servono.'],
  ['Serve esperienza di yoga o meditazione?', 'No. Tutto è guidato e pensato per chi comincia. Chi non vuole fare una cosa la guarda, e va bene così.'],
  ['Chi conduce, davvero?', 'Valentina e i professionisti della rete Aurya, con nome e volto: li trovate nella pagina dei professionisti. Sono pagati per il loro lavoro.'],
  ['Come si paga?', 'Preventivo scritto, conferma con una caparra con bonifico, saldo dopo la giornata. Una fattura sola, di Aurya.'],
];

function Modulo() {
  const [f, setF] = useState({ azienda: '', nome: '', email: '', telefono: '', persone: '', periodo: '', formato: 'non_so', messaggio: '' });
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
        periodo: f.periodo.trim(), formato: f.formato, messaggio: f.messaggio.trim() || null,
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
          Vi scriviamo entro due giorni lavorativi con il preventivo. Vi abbiamo mandato una ricevuta via email.
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
        <label className="block text-sm sm:col-span-2"><span className="text-muted-foreground">Formato</span>
          <select value={f.formato} onChange={set('formato')} className={input} data-testid="az-formato">
            <option value="non_so">Non lo sappiamo ancora</option>
            <option value="giornata">Giornata «Respiro»</option>
            <option value="due_giorni">Due giorni «Rientro»</option>
            <option value="su_misura">Su misura</option>
          </select></label>
        <label className="block text-sm sm:col-span-2"><span className="text-muted-foreground">Cosa avete in mente (facoltativo)</span>
          <textarea rows={3} value={f.messaggio} onChange={set('messaggio')} className={input} placeholder="l’occasione, il gruppo, cosa vi piacerebbe portare a casa" /></label>
      </div>
      {errore && <p className="text-sm text-red-700" data-testid="az-errore">{errore}</p>}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">Nessun impegno: il preventivo è scritto, e decidete dopo averlo letto.</p>
        <button type="submit" disabled={busy} data-testid="az-invia"
                className="rounded-full bg-[#2f5749] px-6 py-3 text-sm font-semibold text-white disabled:opacity-60">
          {busy ? 'Invio…' : 'Chiedete il preventivo'}
        </button>
      </div>
    </form>
  );
}

export default function AziendePage() {
  useSeoMeta({
    title: 'Aurya per le aziende | Team building alla Masseria, con professionisti veri',
    description: 'Una giornata fuori per il vostro team: respiro, suono, un cammino, un pranzo lungo. Alla Masseria, con Valentina e i professionisti della rete Aurya. Giornata da 130 € a persona, due giorni da 320 €.',
    canonicalPath: '/aziende',
  });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <Section tone="cream" rhythm="screen" width="max-w-5xl" labelledBy="az-title">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Aurya per le aziende</p>
          <DisplayTitle as="h1" id="az-title" size="hero" measure="title" className="mt-4">
            Una giornata fuori, con persone vere a condurla.
          </DisplayTitle>
          <Lede size="lead" className="mt-6">
            Un team building alla Masseria: respiro, suono, un cammino, un pranzo lungo.
            Lo conducono Valentina e i professionisti della rete Aurya, pagati per il loro lavoro.
            Niente slide, niente giochi di ruolo.
          </Lede>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:gap-6">
            <EditorialCta href="#az-modulo" variant="solid" data-testid="az-cta-hero">Chiedete il preventivo</EditorialCta>
            <EditorialCta href="#az-formati" variant="quiet">I due formati</EditorialCta>
          </div>
        </Section>

        <Section tone="sand" rhythm="flow" width="max-w-5xl" labelledBy="az-formati-title">
          <div id="az-formati" data-testid="az-formati">
            <DisplayTitle as="h2" id="az-formati-title" size="section" measure="title">Due formati, e il su misura.</DisplayTitle>
            <div className="mt-8 grid gap-6 md:grid-cols-3">
              {FORMATI.map((x) => (
                <article key={x.k} className="flex flex-col rounded-[1.5rem] border border-border bg-card p-6" data-testid={`az-formato-${x.k}`}>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{x.durata}</p>
                  <h3 className="mt-1 font-display text-2xl text-foreground">{x.nome}</h3>
                  <p className="mt-3 text-sm text-muted-foreground">{x.cosa}</p>
                  <p className="mt-auto pt-5 text-base font-semibold text-foreground">{x.prezzo}</p>
                  <p className="text-xs text-muted-foreground">{x.nota}</p>
                </article>
              ))}
            </div>
            <p className="mt-6 text-sm text-muted-foreground">Prezzo a persona. Il preventivo dice tutto quello che comprende, riga per riga.</p>
          </div>
        </Section>

        <Section tone="paper" rhythm="flow" width="max-w-5xl" labelledBy="az-chi-title">
          <div className="grid gap-10 md:grid-cols-2" data-testid="az-chi-dove">
            <div>
              <DisplayTitle as="h2" id="az-chi-title" size="section" measure="title">Chi conduce.</DisplayTitle>
              <p className="mt-4 text-base text-muted-foreground">
                Valentina, che ha fondato Aurya, e i professionisti della rete: insegnanti di yoga e respiro,
                operatori del suono, guide di cammino. Persone che fanno questo lavoro ogni giorno e che trovate,
                con nome e volto, <Link to="/operatori" className="underline">tra i professionisti di Aurya</Link>.
              </p>
            </div>
            <div>
              <DisplayTitle as="h2" size="section" measure="title">Dove.</DisplayTitle>
              <p className="mt-4 text-base text-muted-foreground">
                La Masseria: una sala a volta per il lavoro insieme, la campagna intorno per camminare,
                una cucina per il pranzo. La casa di campagna della famiglia di Aurya.
              </p>
            </div>
          </div>
        </Section>

        <Section tone="cream" rhythm="flow" width="max-w-5xl" labelledBy="az-come-title">
          <div data-testid="az-come">
            <DisplayTitle as="h2" id="az-come-title" size="section" measure="title">Come funziona.</DisplayTitle>
            <ol className="mt-8 grid gap-6 md:grid-cols-3">
              {[
                ['Ci scrivete', 'Persone, periodo, formato. Due minuti, qui sotto.'],
                ['Vi rispondiamo entro due giorni lavorativi', 'Un preventivo che dice tutto: programma, chi conduce, cosa comprende.'],
                ['Fissiamo la data', 'Conferma con una caparra con bonifico, saldo dopo la giornata. Una fattura sola, di Aurya.'],
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
            <DisplayTitle as="h2" id="az-modulo-title" size="section" measure="title">Chiedete il preventivo.</DisplayTitle>
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
