/**
 * /sound — LA LANDING DI AURYA SOUND (27/8/2026, quinta mano).
 *
 * La quinta mano cuce IL FILO UNICO. Il difetto visto dal founder:
 * la pagina faceva ascoltare una meditazione («Ascolta subito») e la
 * sezione DOPO presentava le Meditazioni come una novita' — il
 * racconto si mangiava la coda. E in giro restavano concetti di
 * Professional (biofeedback di sessione, «portalo nel tuo lavoro»
 * senza dire come) che abbiamo tolto dalla vetrina.
 *
 * L'ARCO ADESSO E' UNO, e ogni sezione prepara la successiva:
 *   1. il suono come strumento          (apertura)
 *   2. non tutto il suono e' musica     (i fenomeni)
 *   3. studialo                          (le tre porte)
 *   4. poi il linguaggio cambia: LE MEDITAZIONI — e ne ascolti una
 *      ADESSO (anteprima 90s, patto della Lettera; la materia prima
 *      CALM/GROUND in coda come radice, non come doppione)
 *   5. chi le compone? l'atelier: CREA — ed e' qui che il racconto
 *      diventa il trigger per i professionisti (/sound/studio)
 *   6. chiunque componga, le regole non cambiano (l'onesta')
 *   7. il metodo (i cinque passi)
 *   8. il futuro: dal suono alla vibrazione (senza gergo da catalogo)
 *   9. il congedo (esplora + la porta di Crea Studio)
 *
 * I trigger verso Crea Studio sono TRE, a intensita' crescente:
 * il richiamo nell'apertura, la banda «chi le compone», il box del
 * congedo. Le sezioni «due linguaggi» e il pitch salvia sono morte:
 * dicevano cose che il filo ora dice da solo.
 *
 * LE FOTOGRAFIE SONO UN RACCONTO:
 *   onda    il vortice — l'apertura
 *   trame   le scie — chi compone, l'atelier
 *   fuoco   il blu che diventa arancio — il futuro, la vibrazione
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { frequenciesAPI } from '../../api/frequencies';
import CancelloLettera from './CancelloLettera';
import { prova } from '../../lib/cerchio';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, Lede, PhotoBand, PhotoOpener, Section,
} from '../../components/editorial';
import {
  Bottone, Occhiello, ORO, Richiamo, Rilievo, Testo, VERDE,
} from './soundKit';

const ONDA = '/media/sound/onda.jpg';
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

/* IL CAMPIONE-EROE in vetrina (founder 27/8): la meditazione vera di
   produzione. Se in un ambiente la traccia non esiste, la sezione si
   piega con grazia: niente player, resta il racconto. Quando ci
   saranno piu' meditazioni, qui nascera' il flag «in vetrina». */
const VETRINA_SLUG = 'meditazione-mondo-nuovo-onde-delta';

/* la materia prima: complete e gratuite, la radice del linguaggio */
const ASSAGGI = [
  ['CALM', '/sound/calm', '6 minuti per rallentare'],
  ['GROUND', '/sound/ground', '8 minuti per toccare terra'],
];

const fmtMin = (s) => `${Math.round((s || 0) / 60)} minuti`;

/* ── il player dell'anteprima: un patto, non una trappola ──────────
   Un <audio> puro sul file dei 90 secondi (M3): niente motore,
   niente WebAudio — la pagina resta leggera. A fine corsa l'invito. */
function AnteprimaMeditazione({ track, ctaMeditazioni }) {
  const el = useRef(null);
  const [vivo, setVivo] = useState(false);
  const [cur, setCur] = useState(0);
  const [fine, setFine] = useState(false);
  const [sbloccato, setSbloccato] = useState(!!prova());
  const tot = 90;
  const toggle = () => {
    const a = el.current;
    if (!a) return;
    if (vivo) { a.pause(); return; }
    a.play().catch(() => { /* gesto negato: resta il ▶ */ });
  };
  return (
    <div className="rounded-2xl border-2 p-7 sm:p-9" style={{ borderColor: ORO }}
      data-testid="sh-anteprima">
      <Occhiello>
        Anteprima · i primi 90 secondi
        {(track.score?.duration_sec || track.duration_sec) > 180
          && ` di ${fmtMin(track.score?.duration_sec || track.duration_sec)}`}
      </Occhiello>
      <p className="font-serif text-2xl sm:text-3xl mb-1">{track.title}</p>
      {track.operator?.name && (
        <p className="text-sm text-muted-foreground mb-6">
          di {track.operator.name}
        </p>
      )}
      <audio ref={el} src={track.anteprima_url} preload="none"
        onPlay={() => setVivo(true)} onPause={() => setVivo(false)}
        onTimeUpdate={(e) => setCur(e.target.currentTime)}
        onEnded={() => {
          setVivo(false); setFine(true);
          /* FN1 — il segno del pedaggio pagato: la pagina traccia
             aprira' il cancello all'arrivo, senza secondo ascolto */
          try { sessionStorage.setItem('fqz_anteprima_finita', '1'); } catch { /* privato */ }
        }} />
      {fine ? (
        sbloccato ? (
          /* FN3, iscritto SUL POSTO: la landing non ti molla */
          <div data-testid="sh-anteprima-sbloccata">
            <Rilievo>Sei dentro. Buon ascolto.</Rilievo>
            <div className="mt-6 flex flex-wrap items-center gap-6">
              <Bottone to={`/frequenze/${track.slug}`}>
                Ascolta la meditazione completa →
              </Bottone>
              <Richiamo to="/meditazioni">{ctaMeditazioni}</Richiamo>
            </div>
          </div>
        ) : (
          /* FN2+FN3 — a fine anteprima il cancello appare QUI, subito,
             col form: niente salti di pagina tra il desiderio e l'email */
          <div data-testid="sh-anteprima-patto">
            <CancelloLettera slug={track.slug} variante="chiaro"
              durataSec={track.score?.duration_sec || track.duration_sec}
              onSbloccato={() => setSbloccato(true)}>
              <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
                <button type="button" className="underline"
                  onClick={() => { setFine(false); setCur(0); }}>
                  Riascolta l’anteprima
                </button>
                <Link to="/meditazioni" className="underline">{ctaMeditazioni}</Link>
              </div>
            </CancelloLettera>
          </div>
        )
      ) : (
        <div className="flex items-center gap-5">
          <button type="button" onClick={toggle} data-testid="sh-anteprima-play"
            aria-label={vivo ? 'Pausa' : 'Ascolta l’anteprima'}
            className="grid h-14 w-14 shrink-0 place-items-center rounded-full
                       text-xl transition hover:opacity-90"
            style={{ background: ORO, color: '#14212b' }}>
            {vivo ? '❚❚' : '▶'}
          </button>
          <div className="min-w-0 flex-1">
            <div className="h-1.5 w-full overflow-hidden rounded-full"
              style={{ background: '#EDE5D2' }}>
              <div className="h-full rounded-full transition-[width] duration-300"
                style={{ width: `${Math.min(100, (cur / tot) * 100)}%`, background: ORO }} />
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {vivo ? 'Chiudi gli occhi. Al resto pensa la voce.'
                : 'Premi play: si ascolta da qui, in cuffia è un’altra cosa.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SoundHomePage() {
  useEffect(() => {
    document.title = 'Aurya Sound: il suono può diventare uno strumento | Aurya';
  }, []);
  /* il campione in vetrina: se la traccia non c'e' (altro ambiente),
     la sezione si piega con grazia — mai una scatola rotta */
  const [vetrina, setVetrina] = useState(null);
  /* FN4 — il numero VERO del catalogo: se il server e' sbloccato
     conta gli item, da chiuso il 403 porta tracks_count. Fallback:
     il bottone parla senza numero. */
  const [quante, setQuante] = useState(0);
  useEffect(() => {
    let vivo = true;
    frequenciesAPI.getPublic(VETRINA_SLUG)
      .then((r) => { if (vivo && r.data?.anteprima_url) setVetrina(r.data); })
      .catch(() => { /* niente vetrina: la pagina vive lo stesso */ });
    frequenciesAPI.getCatalog(prova())
      .then((r) => { if (vivo) setQuante((r.data?.items || []).length); })
      .catch((e) => {
        const n = e?.response?.data?.detail?.tracks_count;
        if (vivo && n) setQuante(n);
      });
    return () => { vivo = false; };
  }, []);

  const ctaMeditazioni = quante > 1
    ? `Le ${quante} Meditazioni →` : 'Tutte le Meditazioni →';

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="sound-home">

        {/* ── 1 · APERTURA ───────────────────────────────────────── */}
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
            Puoi studiarlo, sperimentarlo, o semplicemente ascoltarlo.
            E se accompagni persone, puoi comporlo per loro.
          </p>
          {/* FN4 (30/8), l'hero vende il gancio piu' caldo: la
              meditazione che ascolti ADESSO. Il richiamo professionale
              esce dall'hero: ha la sua band (sezione Crea), un
              pubblico, una porta. */}
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Bottone href="#sh-esperienze" tono="chiaro" testid="sh-cta-ascolta">
              Ascolta una meditazione, 90 secondi
            </Bottone>
            <Richiamo to="/sound/esplora" tono="chiaro" testid="sh-cta-esplora">
              Esplora Aurya Sound →
            </Richiamo>
          </div>
        </PhotoOpener>

        {/* ── 2 · NON TUTTO IL SUONO È MUSICA ─────────────────────── */}
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

        {/* ── 3 · LE TRE PORTE (studia) ───────────────────────────── */}
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

        {/* ── 4 · LE MEDITAZIONI, e ne ascolti una ADESSO ─────────
            Il punto in cui il linguaggio cambia: dal laboratorio
            all'esperienza. La sezione E' la presentazione delle
            Meditazioni, e la prova e' immediata: il player. */}
        <Section tone="paper" labelledBy="sh-esperienze"
          data-testid="sh-porta-esperienze">
          <Occhiello>Poi il linguaggio cambia</Occhiello>
          <DisplayTitle id="sh-esperienze" size="section">
            Dallo studio all’esperienza: le Meditazioni.
          </DisplayTitle>
          <Lede size="small" className="mt-5 max-w-3xl">
            Fin qui il suono si spiega. Nelle Meditazioni ti accompagna:
            una voce apre lo spazio, la musica e il paesaggio sonoro lo
            tengono, e il suono smette di essere un fenomeno da capire.
            La prova migliore è farla, adesso.
          </Lede>
          {vetrina && (
            <div className="mt-10 max-w-3xl">
              <AnteprimaMeditazione track={vetrina} ctaMeditazioni={ctaMeditazioni} />
            </div>
          )}
          <div className="mt-8">
            <Bottone to="/meditazioni" testid="sh-porta-meditazioni">
              {ctaMeditazioni}
            </Bottone>
          </div>
          <div className="mt-10 max-w-3xl border-t pt-7"
            style={{ borderColor: '#e8e0ce' }}>
            <p className="text-base text-muted-foreground">
              E se vuoi sentire da dove nasce questo linguaggio, il
              fenomeno nudo, senza voce, due esperienze complete e
              gratuite:
            </p>
            <div className="mt-4 flex flex-wrap gap-x-8 gap-y-3">
              {ASSAGGI.map(([nome, to, sotto]) => (
                <Richiamo key={nome} to={to}>
                  {nome} <span className="text-muted-foreground">· {sotto}</span>
                </Richiamo>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 5 · CHI LE COMPONE: CREA, il trigger nel racconto ────
            La domanda che il player ha appena piantato («chi ha fatto
            questa voce?») trova qui la risposta, e la risposta E' la
            via professionale. */}
        <PhotoBand image={TRAME} focus="50% 50%" width="max-w-4xl"
          labelledBy="sh-crea" data-testid="sld-crea">
          <Occhiello tono="chiaro">Ogni meditazione ha una voce</Occhiello>
          <DisplayTitle id="sh-crea" size="section"
            className="text-white text-hero-shadow">
            Composte con Crea, l’atelier di Aurya.
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              La meditazione che hai appena sentito è nata qui: la voce
              registrata dal browser, le basi sonore, le frequenze, la
              scena visiva. Un unico strumento, nessuno studio di
              registrazione.
            </p>
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              E lo stesso atelier ora si apre, su invito, a chi
              accompagna persone.
            </p>
            <p className="font-serif text-2xl sm:text-3xl text-white text-hero-shadow">
              Le tue meditazioni, con la tua voce.<br />
              Condivise in privato con i tuoi clienti.
            </p>
          </div>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Bottone to="/sound/studio" tono="chiaro" testid="sld-crea-cta">
              Scopri Crea Studio →
            </Bottone>
            <span className="text-sm text-white/60">
              Accesso su invito. Le meditazioni che componi restano tue.
            </span>
          </div>
        </PhotoBand>

        {/* ── 6 · L'ONESTÀ, chiunque componga, le regole non cambiano */}
        <Section tone="cream" labelledBy="sh-evidenza">
          <Occhiello>Chiunque componga, le regole non cambiano</Occhiello>
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
        </Section>

        {/* ── 7 · IL METODO ──────────────────────────────────────── */}
        <Section tone="sand" labelledBy="sh-processo">
          <DisplayTitle id="sh-processo" size="section">
            Dalla ricerca all’esperienza.
          </DisplayTitle>
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
        </Section>

        {/* ── 8 · IL FUTURO, dal suono alla vibrazione ─────────────
            Niente gergo da catalogo professionale: la visione di
            Aurya Sound, detta per tutti. */}
        <PhotoBand image={FUOCO} focus="50% 45%" width="max-w-4xl"
          labelledBy="sh-futuro" data-testid="sh-futuro">
          <Occhiello tono="chiaro">E questo è solo l’inizio</Occhiello>
          <DisplayTitle id="sh-futuro" size="section"
            className="text-white text-hero-shadow">
            Dal suono alla vibrazione.
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Oggi il suono di Aurya si ascolta. Il passo su cui stiamo
              lavorando è quello in cui si sente: la vibrazione che
              arriva al corpo, e la risposta, respiro, battito, che
              si può osservare nel tempo.
            </p>
            <p className="font-serif text-2xl text-white text-hero-shadow">
              Il suono come stimolo. Il corpo come risposta.
              L’esperienza come viaggio.
            </p>
          </div>
        </PhotoBand>

        {/* ── 9 · IL CONGEDO ─────────────────────────────────────── */}
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
              Componi le tue meditazioni con Crea Studio.
            </p>
            <Bottone to="/sound/studio">Scopri Crea Studio →</Bottone>
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
                <Link to="/sound/studio" className="hover:text-foreground">Crea Studio</Link>
                {' '}· La tua voce · Meditazioni private per i tuoi clienti
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
