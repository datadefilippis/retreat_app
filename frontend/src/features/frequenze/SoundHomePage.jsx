/**
 * /sound — LA LANDING DI AURYA SOUND (26/8/2026 sera, terza mano).
 *
 * La terza mano risponde alla revisione PM+UX del founder:
 *  - VIA le frasi ellittiche coi due punti («Non ricordare:
 *    registrare») — si scrive in italiano, con frasi intere
 *  - MENO negazioni: una pagina che dice sempre «non» finisce per
 *    non dire niente
 *  - le tre PORTE più quadrate e più in evidenza: copy corto, carta
 *    intera cliccabile, rialzo all'hover
 *  - da ascoltare SOLO CALM e GROUND (decisione founder: RESPIRO
 *    resta nel catalogo ma non in vetrina)
 *
 * LE FOTOGRAFIE SONO UN RACCONTO. La pagina e' chiara come il sito, e
 * il BUIO arriva dove stai per entrare nel suono:
 *   onda    il vortice — l'apertura
 *   seta    le trame morbide — «poi puoi semplicemente ascoltare»
 *   trame   le scie — le Meditazioni, dove il linguaggio cambia
 *   fuoco   il blu che diventa arancio — il futuro, la risposta
 */
import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, Lede, PhotoBand, PhotoOpener, Section,
} from '../../components/editorial';
import {
  Bottone, Occhiello, ORO, Richiamo, Rilievo, Testo, VERDE,
} from './soundKit';

const ONDA = '/media/sound/onda.jpg';
const SETA = '/media/sound/seta.jpg';
const TRAME = '/media/sound/trame.jpg';
const FUOCO = '/media/sound/fuoco.jpg';

const PASSI = [
  ['01', 'Studiamo', 'Partiamo dai fenomeni sonori, ritmici e fisiologici e da ciò che la ricerca dice davvero.'],
  ['02', 'Progettiamo', 'Trasformiamo i principi in una struttura sonora.'],
  ['03', 'Misuriamo', 'Verifichiamo nel Sound Lab ciò che abbiamo costruito.'],
  ['04', 'Ascoltiamo', 'Ne facciamo un’esperienza reale, da vivere in cuffia.'],
  ['05', 'Documentiamo', 'La struttura e le basi restano leggibili, per chiunque.'],
];

/* le PORTE: copy corto, carta intera cliccabile */
const PORTE = [
  {
    id: 'sh-porta-esplora', occhiello: 'Esplora', titolo: 'La Biblioteca',
    to: '/sound/esplora', accento: ORO, cta: 'Esplora la Biblioteca',
    testo: '36 schede in quattro mondi: bande cerebrali, frequenze, ritmi del corpo, metodi. Ogni scheda parte dal fenomeno, mai dal mito.',
  },
  {
    id: 'sh-porta-impara', occhiello: 'Impara', titolo: 'Il linguaggio del suono',
    to: '/sound/impara', accento: VERDE, cta: 'Inizia a imparare',
    testo: 'Frequenza, binaurale, entrainment, spettro: le parole del suono spiegate in una guida semplice, senza mistero aggiunto.',
  },
  {
    id: 'sh-porta-lab', occhiello: 'Sperimenta', titolo: 'Sound Lab',
    to: '/sound/lab', accento: ORO, cta: 'Entra nel Lab',
    testo: 'Genera una frequenza e guarda il segnale vero: forma d’onda, spettro, sweep. Il modo più diretto per giocare con il suono.',
  },
];

/* da ascoltare: SOLO CALM e GROUND (decisione founder, 26/8) */
const ESPERIENZE = [
  {
    id: 'calm', titolo: 'CALM', sotto: '6 minuti per rallentare.',
    righe: ['Un fondo stabile. Un respiro sonoro che si distende. Un battito lento che appare e poi scompare.',
      'Costruita per accompagnarti verso un ritmo più quieto.'],
  },
  {
    id: 'ground', titolo: 'GROUND', sotto: '8 minuti per toccare terra.',
    righe: ['Un registro grave, una pulsazione lenta, materia sonora che piano piano si dirada.',
      'GROUND lavora sulla percezione del peso, della profondità e dello spazio.'],
  },
];

export default function SoundHomePage() {
  useEffect(() => {
    document.title = 'Aurya Sound — Il suono può diventare uno strumento | Aurya';
  }, []);
  /* la via professionale (founder 26/8 sera): si promuove CREA, non
     il catalogo Professional — il funnel e' lo stesso dei leads */
  const { hash } = useLocation();
  useEffect(() => {
    if (hash === '#professionisti') {
      document.getElementById('professionisti')?.scrollIntoView({ block: 'start' });
    }
  }, [hash]);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [stato, setStato] = useState(null);   // null | 'invio' | 'fatto' | errore
  const chiedi = async (e) => {
    e.preventDefault();
    if (!email.trim() || stato === 'invio') return;
    setStato('invio');
    try {
      await api.post('/public/leads', {
        type: 'operator',
        email: email.trim(),
        name: nome.trim() || null,
        message: 'Aurya Sound Crea — richiesta di accesso per professionisti',
        interests: ['sound_crea'],
      });
      setStato('fatto');
    } catch {
      setStato('Non inviato: riprova fra un momento.');
    }
  };

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="sound-home">

        {/* ── APERTURA ───────────────────────────────────────────── */}
        <PhotoOpener image={ONDA} focus="50% 50%" height="tall" align="left"
          width="max-w-4xl" labelledBy="sh-title" data-testid="sh-open">
          <Occhiello tono="chiaro">Aurya Sound</Occhiello>
          <DisplayTitle as="h1" id="sh-title" size="hero" measure="wide"
            className="text-hero-shadow">
            Il suono può diventare uno strumento.
          </DisplayTitle>
          <Lede className="mt-8 max-w-2xl text-white/90 text-hero-shadow" tone="inherit">
            Frequenze, ritmo, respiro, spazio e musica. Aurya Sound è uno
            spazio per esplorare il suono, comprenderne i meccanismi e
            trasformarlo in esperienze da ascoltare.
          </Lede>
          <p className="mt-6 max-w-2xl text-base sm:text-lg leading-relaxed text-white/80 text-hero-shadow">
            Puoi studiarlo. Puoi sperimentarlo. Puoi semplicemente
            ascoltarlo. E, se sei un professionista, puoi portarlo nel
            tuo lavoro.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Bottone to="/sound/esplora" tono="chiaro" testid="sh-cta-esplora">
              Esplora Aurya Sound
            </Bottone>
          </div>
        </PhotoOpener>

        {/* ── NON TUTTO IL SUONO È MUSICA ─────────────────────────── */}
        <Section tone="cream" labelledBy="sh-fenomeni">
          <DisplayTitle id="sh-fenomeni" size="section">
            Non tutto il suono è musica.
          </DisplayTitle>
          <div className="mt-10 grid gap-x-14 gap-y-5 md:grid-cols-2 max-w-4xl">
            {['Un tono può cambiare lentamente.',
              'Un ritmo può diventare più lento.',
              'Due frequenze possono creare un battito percepibile nello spazio tra le orecchie.',
              'Una nota grave può trasformare completamente la percezione di un ambiente.',
              'Il respiro può diventare ritmo.'].map((v) => (
                <div key={v} className="border-l-2 pl-5 py-1"
                  style={{ borderColor: ORO }}>
                  <Testo>{v}</Testo>
                </div>
              ))}
          </div>
          <Testo className="mt-12 max-w-2xl">
            Sono fenomeni diversi, e Aurya Sound nasce per esplorarli e
            trasformarli in esperienze sonore progettate.
          </Testo>
          <Rilievo className="mt-6 max-w-2xl">
            Non una raccolta di tracce: un modo diverso di ascoltare.
          </Rilievo>
        </Section>

        {/* ── LE TRE PORTE ───────────────────────────────────────── */}
        <Section tone="sand" labelledBy="sh-porte">
          <DisplayTitle id="sh-porte" size="section">
            Parti da ciò che ti incuriosisce.
          </DisplayTitle>
          <div className="mt-12 grid gap-7 lg:grid-cols-3">
            {PORTE.map((p) => (
              <Link key={p.id} to={p.to} data-testid={p.id}
                className="group relative flex flex-col rounded-2xl bg-white
                           border border-[#e8e0ce] p-8 lg:p-9 lg:min-h-[330px]
                           shadow-[0_1px_0_rgba(0,0,0,0.04)]
                           transition duration-200 hover:-translate-y-1
                           hover:shadow-[0_18px_40px_-18px_rgba(20,33,43,0.3)]
                           focus-visible:outline focus-visible:outline-2
                           focus-visible:outline-offset-2">
                <span aria-hidden
                  className="absolute left-8 right-8 top-0 h-1 rounded-b"
                  style={{ background: p.accento }} />
                <Occhiello className="mt-2">{p.occhiello}</Occhiello>
                <h3 className="font-serif text-2xl sm:text-3xl mb-4 text-foreground">
                  {p.titolo}
                </h3>
                <p className="flex-1 text-base leading-relaxed text-muted-foreground">
                  {p.testo}
                </p>
                <span className="mt-8 inline-flex items-center gap-2 self-start
                                 text-base text-foreground border-b pb-1
                                 border-[#c9b37e] transition
                                 group-hover:border-foreground">
                  {p.cta} →
                </span>
              </Link>
            ))}
          </div>
        </Section>

        {/* ── LE ESPERIENZE (banda scura) ─────────────────────────── */}
        <PhotoBand image={SETA} focus="50% 55%" width="max-w-5xl"
          labelledBy="sh-esperienze" data-testid="sh-porta-esperienze">
          <Occhiello tono="chiaro">Poi puoi semplicemente ascoltare</Occhiello>
          <DisplayTitle id="sh-esperienze" size="section"
            className="text-white text-hero-shadow">
            Il suono è fatto per essere vissuto.
          </DisplayTitle>
          <p className="mt-6 max-w-2xl text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
            Studiarlo è metà del viaggio. L’altra metà è ascoltarlo:
            due esperienze brevi, gratuite, da vivere in cuffia.
          </p>
          <div className="mt-12 grid gap-6 md:grid-cols-2 max-w-4xl">
            {ESPERIENZE.map((e) => (
              <div key={e.id}
                className="rounded-2xl border border-white/20 bg-black/25 backdrop-blur-sm p-8">
                <h3 className="font-serif text-3xl text-white">{e.titolo}</h3>
                <p className="mt-1 mb-5 text-sm" style={{ color: '#e0cfa4' }}>{e.sotto}</p>
                <div className="space-y-3 text-[15px] leading-relaxed text-white/80">
                  {e.righe.map((r) => <p key={r}>{r}</p>)}
                </div>
                <div className="mt-7">
                  <Richiamo to={`/sound/${e.id}`} tono="chiaro">
                    Ascolta {e.titolo} →
                  </Richiamo>
                </div>
              </div>
            ))}
          </div>
        </PhotoBand>

        {/* ── LE MEDITAZIONI ─────────────────────────────────────── */}
        <PhotoBand image={TRAME} focus="50% 50%" width="max-w-4xl"
          labelledBy="sh-meditazioni" data-testid="sh-porta-meditazioni">
          <Occhiello tono="chiaro">E poi c’è un altro modo di usare il suono</Occhiello>
          <DisplayTitle id="sh-meditazioni" size="section"
            className="text-white text-hero-shadow">
            Le Meditazioni Aurya
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Qui il linguaggio cambia: non siamo più nel laboratorio,
              siamo dentro l’esperienza. A volte il suono non deve
              spiegarti qualcosa — deve semplicemente accompagnarti.
            </p>
            <p className="font-serif text-2xl text-white text-hero-shadow">
              Voce. Musica. Paesaggi sonori. Composizioni originali. Silenzio.
            </p>
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Ogni meditazione nasce come un piccolo viaggio: una voce
              apre lo spazio, il suono lo accompagna, la musica cambia
              insieme alla pratica.
            </p>
          </div>
          <div className="mt-10">
            <Bottone to="/meditazioni" tono="chiaro">Scopri le Meditazioni →</Bottone>
          </div>
          <p className="mt-7 text-sm text-white/60">
            Le Meditazioni Aurya vengono pubblicate attraverso La Lettera.
          </p>
        </PhotoBand>

        {/* ── I DUE LINGUAGGI ────────────────────────────────────── */}
        <Section tone="paper" labelledBy="sh-due">
          <DisplayTitle id="sh-due" size="section">
            Due modi diversi di lavorare con il suono.
          </DisplayTitle>
          <div className="mt-12 grid gap-10 md:grid-cols-2 max-w-4xl">
            <div>
              <span aria-hidden className="block h-[3px] w-16 mb-6"
                style={{ background: ORO }} />
              <Occhiello>Esperienze sonore</Occhiello>
              <p className="font-serif text-2xl mb-4">CALM e GROUND.</p>
              <Testo>Suono come fenomeno: struttura, ritmo, frequenza, percezione.</Testo>
            </div>
            <div>
              <span aria-hidden className="block h-[3px] w-16 mb-6"
                style={{ background: VERDE }} />
              <Occhiello>Meditazioni Aurya</Occhiello>
              <p className="font-serif text-2xl mb-4">Voce, musica e paesaggio sonoro.</p>
              <Testo>Suono come esperienza narrativa.</Testo>
            </div>
          </div>
          <Rilievo className="mt-14 max-w-3xl">
            Due linguaggi diversi, lo stesso desiderio: creare esperienze
            che abbia senso ascoltare.
          </Rilievo>
        </Section>

        {/* ── LA VIA PROFESSIONALE: CREA ─────────────────────────────
            Deciso dal founder (26/8 sera): il catalogo Professional
            non si sponsorizza finche' il suo valore non superera' il
            premere play (la via delle vibrazioni e' la sua fase due).
            Quello che ha GIA' dimostrato valore e' l'atelier: qui si
            promette Crea — comporre per i propri clienti — e si
            raccoglie l'interesse sul funnel leads esistente. */}
        <Section tone="sage" labelledBy="sh-pro" id="professionisti"
          data-testid="sld-crea">
          <Occhiello tono="chiaro">
            Per chi accompagna persone
          </Occhiello>
          <DisplayTitle id="sh-pro" size="section" className="text-[#f6f2e8]">
            Componi per chi accompagni.
          </DisplayTitle>
          <div className="mt-8 max-w-3xl space-y-6">
            <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85">
              Crea è l’atelier con cui nascono le esperienze e le
              meditazioni di Aurya: voce, basi sonore, frequenze e
              scena visiva, in un unico strumento che funziona dal
              browser. Lo apriamo progressivamente a professionisti
              selezionati — su invito o in partnership.
            </p>
            <p className="font-serif text-2xl sm:text-3xl text-[#f6f2e8]">
              Le tue meditazioni, con la tua voce.<br />
              Condivise in privato con i tuoi clienti.
            </p>
          </div>
          {stato === 'fatto' ? (
            <p className="mt-10 max-w-2xl text-base sm:text-lg text-[#f6f2e8]"
              data-testid="sld-crea-grazie">
              Ricevuto. Ti ricontattiamo noi per raccontarti come funziona.
            </p>
          ) : (
            <form className="mt-10 flex max-w-2xl flex-wrap gap-4" onSubmit={chiedi}>
              <input type="text" value={nome} placeholder="Il tuo nome"
                onChange={(e) => setNome(e.target.value)}
                data-testid="sld-crea-nome"
                className="min-w-[180px] flex-1 rounded-xl border border-[#f6f2e8]/25
                           bg-[#f6f2e8]/10 px-5 py-3.5 text-base text-[#f6f2e8]
                           placeholder:text-[#f6f2e8]/50" />
              <input type="email" value={email} required placeholder="La tua email"
                onChange={(e) => setEmail(e.target.value)}
                data-testid="sld-crea-email"
                className="min-w-[220px] flex-1 rounded-xl border border-[#f6f2e8]/25
                           bg-[#f6f2e8]/10 px-5 py-3.5 text-base text-[#f6f2e8]
                           placeholder:text-[#f6f2e8]/50" />
              <button type="submit" disabled={stato === 'invio'}
                data-testid="sld-crea-invia"
                className="rounded-full px-7 py-3.5 text-base font-medium transition
                           hover:opacity-90 disabled:opacity-50"
                style={{ background: ORO, color: '#14212b' }}>
                {stato === 'invio' ? 'Invio…' : 'Raccontami di più →'}
              </button>
              {typeof stato === 'string' && stato !== 'invio' && (
                <p className="w-full text-sm text-[#ffd7d7]">{stato}</p>
              )}
            </form>
          )}
          <p className="mt-6 text-sm text-[#f6f2e8]/60">
            Accesso su invito. Le meditazioni che componi restano tue.
          </p>
        </Section>

        {/* ── L'ONESTÀ ───────────────────────────────────────────── */}
        <Section tone="cream" labelledBy="sh-evidenza">
          <Occhiello>Il nostro approccio parte da una cosa semplice</Occhiello>
          <DisplayTitle id="sh-evidenza" size="section">
            Non tutte le frequenze hanno la stessa evidenza.
          </DisplayTitle>
          <div className="mt-8 max-w-3xl space-y-5">
            <Testo>
              Il mondo del suono è pieno di affermazioni. Alcune hanno
              basi interessanti, altre sono ancora oggetto di ricerca,
              altre appartengono alla tradizione. Noi preferiamo
              distinguerle.
            </Testo>
            <Testo>
              Per questo Aurya Sound non promette che una determinata
              frequenza possa «guarire», «riparare» o agire su uno
              specifico organo.
            </Testo>
          </div>
          <div className="mt-12 max-w-3xl border-l-4 pl-8 space-y-3"
            style={{ borderColor: ORO }}>
            <Rilievo>Raccontiamo quello che sappiamo.</Rilievo>
            <Rilievo>Distinguiamo quello che non sappiamo.</Rilievo>
            <Rilievo>E lasciamo spazio all’esperienza.</Rilievo>
          </div>
          <Testo className="mt-10 max-w-2xl">
            È il nostro modo di costruire qualcosa che possa durare.
          </Testo>
        </Section>

        {/* ── IL PROCESSO ────────────────────────────────────────── */}
        <Section tone="sand" labelledBy="sh-processo">
          <DisplayTitle id="sh-processo" size="section">
            Dalla ricerca all’esperienza.
          </DisplayTitle>
          <Lede size="small" className="mt-5">
            Ogni esperienza nasce dallo stesso metodo.
          </Lede>
          <ol className="mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-5">
            {PASSI.map(([n, titolo, testo]) => (
              <li key={n}>
                <p className="font-serif text-5xl leading-none mb-5"
                  style={{ color: ORO }}>{n}</p>
                <h3 className="font-serif text-xl mb-3">{titolo}</h3>
                <p className="text-[15px] leading-relaxed text-muted-foreground">{testo}</p>
              </li>
            ))}
          </ol>
          <Rilievo className="mt-16 max-w-3xl">
            Il suono può essere affascinante senza diventare misterioso.
          </Rilievo>
        </Section>

        {/* ── IL FUTURO ──────────────────────────────────────────── */}
        <PhotoBand image={FUOCO} focus="50% 45%" width="max-w-4xl"
          labelledBy="sh-futuro" data-testid="sh-futuro">
          <Occhiello tono="chiaro">E questo è solo l’inizio</Occhiello>
          <DisplayTitle id="sh-futuro" size="section"
            className="text-white text-hero-shadow">
            Dal suono alla risposta.
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Oggi Aurya Sound lavora sul suono. Il prossimo passo è
              la risposta: non soltanto creare uno stimolo, ma poter
              osservare cosa succede durante una sessione —
              respirazione, variabilità, vibrazione, risposta nel tempo.
            </p>
            <p className="font-serif text-2xl text-white text-hero-shadow">
              Il suono come stimolo. I dati come osservazione.
              L’esperienza come percorso.
            </p>
          </div>
        </PhotoBand>

        {/* ── IL CONGEDO ─────────────────────────────────────────── */}
        <Section tone="cream" labelledBy="sh-fine">
          <DisplayTitle id="sh-fine" size="section">Aurya Sound</DisplayTitle>
          <div className="mt-6 space-y-2">
            <Rilievo>Esplora il suono.</Rilievo>
            <Rilievo>Ascoltalo.</Rilievo>
            <Rilievo>Impara a usarlo.</Rilievo>
          </div>
          <div className="mt-10">
            <Bottone to="/sound/esplora">Esplora gratuitamente →</Bottone>
          </div>

          <div className="mt-20 rounded-2xl border-2 p-9 max-w-3xl"
            style={{ borderColor: ORO }}>
            <Occhiello>Se sei un professionista del benessere</Occhiello>
            <p className="font-serif text-2xl sm:text-3xl mb-6">
              Componi le tue meditazioni con Crea.
            </p>
            <Bottone href="#professionisti">Raccontami di più →</Bottone>
          </div>

          <div className="mt-20 grid gap-10 sm:grid-cols-2 max-w-4xl">
            <div>
              <Occhiello>Aurya Sound</Occhiello>
              <p className="text-base text-muted-foreground leading-relaxed">
                <Link to="/sound/esplora" className="hover:text-foreground">Biblioteca</Link> ·{' '}
                <Link to="/sound/impara" className="hover:text-foreground">Impara</Link> ·{' '}
                <Link to="/sound/lab" className="hover:text-foreground">Lab</Link> ·{' '}
                <Link to="/sound/calm" className="hover:text-foreground">Esperienze</Link> ·{' '}
                <Link to="/meditazioni" className="hover:text-foreground">Meditazioni</Link>
              </p>
            </div>
            <div>
              <Occhiello>Per i professionisti</Occhiello>
              <p className="text-base text-muted-foreground leading-relaxed">
                Crea · Voce e basi sonore · Meditazioni private per i tuoi clienti
              </p>
            </div>
          </div>

          <p className="mt-14 max-w-3xl text-sm leading-relaxed text-muted-foreground"
            data-testid="sh-disclaimer">
            Aurya Sound è progettato per esperienze di esplorazione e
            benessere e non costituisce un dispositivo medico né
            sostituisce diagnosi o trattamenti sanitari.
          </p>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
