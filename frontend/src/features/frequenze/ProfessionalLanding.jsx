/**
 * /sound/professional — LA PAGINA DI VENDITA (26/8/2026 sera,
 * seconda mano dopo la revisione PM+UX del founder).
 *
 * Pubblica e indicizzata: qui si SPIEGA e si DESIDERA; lo strumento
 * (/sound/pro) resta app e resta noindex.
 *
 * Cosa e' cambiato dalla prima mano:
 *  - VIA i doppioni: «Non è un nuovo Lab» e «Costruito per essere
 *    utilizzato» dicevano la stessa cosa in due sezioni — ora e' UNA
 *    sezione sola. «Per chi» non e' piu' un'isola: sta attaccata al
 *    form, come passo di qualificazione del funnel
 *  - VIA le frasi ellittiche coi due punti e le raffiche di «non»:
 *    resta la terzina del hero (e' la firma) e una lista sola
 *  - la scatola nera non mostra piu' finestre statiche: mostra
 *    L'ONDA VIVA — le voci degli score veri (costruisci() del
 *    catalogo) che si muovono a schermo, MUTE. La pagina non suona.
 *
 * Le fotografie: spirale (apertura — struttura e precisione), caleido
 * (i percorsi — la ripetizione che diventa forma), fuoco (il futuro).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, Lede, PhotoBand, PhotoOpener, Section,
} from '../../components/editorial';
import {
  Bottone, Occhiello, ORO, Rilievo, Scheda, Testo, VERDE,
} from './soundKit';
import OndaViva from './pro/OndaViva';
import { CATALOGO } from './pro/catalogo';
import { PERCORSI } from './pro/percorsi';
import { messaggio } from './pro/errori';

const SPIRALE = '/media/sound/spirale.jpg';
const CALEIDO = '/media/sound/caleido.jpg';
const FUOCO = '/media/sound/fuoco.jpg';

const PROTOCOLLI = [
  ['Rilassare', 'Stimolazione ritmica e una progressione verso frequenze più lente.'],
  ['GROUND', 'Registro basso, pulsazione, percezione del peso e dello spazio.'],
  ['CALM', 'Un arco breve intorno al rallentamento, al respiro sonoro e a un battito lento.'],
];

const STORICO = ['Persona', 'Protocollo', 'Versione', 'Data', 'Durata', 'Note'];

const PRINCIPI = ['Entrainment', 'Binaural beats', 'Stimolazione ritmica',
  'Psicoacustica', 'Respirazione'];

const PRATICHE = ['Meditazione', 'Breathwork', 'Sound healing',
  'Pratiche corporee', 'Percorsi di rilassamento', 'Esperienze olistiche'];

/* la FINESTRA sull'onda: un riquadro di Aurya Sound dentro la pagina
   chiara del sito. Col crepuscolo (26/8) la metafora torna VERA — di
   la' dal vetro c'e' davvero il petrolio. */
function Finestra({ etichetta, sotto, children }) {
  return (
    <figure className="rounded-2xl overflow-hidden"
      style={{ background: '#26454C', border: '1px solid #3A5F66' }}>
      <div className="p-4 sm:p-5">{children}</div>
      {etichetta && (
        <figcaption className="flex items-baseline justify-between px-5 pb-4">
          <span className="font-serif text-lg text-[#EAF2F0]">{etichetta}</span>
          {sotto && <span className="text-sm text-[#7FC9B0]">{sotto}</span>}
        </figcaption>
      )}
    </figure>
  );
}

export default function ProfessionalLanding() {
  useEffect(() => {
    document.title = 'Aurya Sound Professional: il suono nella tua pratica | Aurya';
  }, []);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [racconto, setRacconto] = useState('');
  const [stato, setStato] = useState(null);   // null | 'invio' | 'fatto' | errore

  /* gli score VERI del catalogo, calcolati una volta sola */
  const ground = useMemo(
    () => CATALOGO.find((p) => p.id === 'ground')?.costruisci(), []);
  const calm = useMemo(
    () => CATALOGO.find((p) => p.id === 'calm')?.costruisci(), []);

  const chiedi = async (e) => {
    e.preventDefault();
    if (!email.trim() || stato === 'invio') return;
    setStato('invio');
    try {
      await api.post('/public/leads', {
        type: 'operator',
        email: email.trim(),
        name: nome.trim() || null,
        message: racconto.trim()
          || 'Aurya Sound Professional, richiesta di accesso',
        interests: ['sound_professional'],
      });
      setStato('fatto');
    } catch (err) {
      setStato(messaggio(err, 'Non inviato: riprova fra un momento.'));
    }
  };

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="prof-landing">

        {/* ── APERTURA ───────────────────────────────────────────── */}
        <PhotoOpener image={SPIRALE} focus="62% 55%" height="tall" align="left"
          width="max-w-4xl" labelledBy="prof-title" data-testid="prof-open">
          <Occhiello tono="chiaro">Aurya Sound Professional</Occhiello>
          <DisplayTitle as="h1" id="prof-title" size="hero" measure="wide"
            className="text-hero-shadow">
            Il suono, portato nella tua pratica.
          </DisplayTitle>
          <Lede className="mt-8 max-w-2xl text-white/90 text-hero-shadow" tone="inherit">
            Protocolli sonori strutturati, pronti da condurre, con uno
            storico delle sessioni.
          </Lede>
          <div className="mt-7 max-w-xl space-y-2 text-base sm:text-lg text-white/75 text-hero-shadow">
            <p>Non una playlist.</p>
            <p>Non un generatore di frequenze.</p>
            <p>Non un’altra raccolta di tracce.</p>
          </div>
          <p className="mt-8 font-serif text-2xl sm:text-3xl text-white text-hero-shadow">
            Tu ti occupi della persona.<br />Aurya si occupa del suono.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Bottone href="#accesso" tono="chiaro" testid="prof-cta-hero">
              Richiedi l’accesso →
            </Bottone>
            <span className="text-sm text-white/60">Accesso su invito.</span>
          </div>
        </PhotoOpener>

        {/* ── IL PROBLEMA → LA PROMESSA ──────────────────────────── */}
        <Section tone="cream" labelledBy="prof-entra">
          <DisplayTitle id="prof-entra" size="section">
            Quando il suono entra davvero nella sessione.
          </DisplayTitle>
          <div className="mt-8 grid gap-12 lg:grid-cols-2 max-w-5xl">
            <div className="space-y-5">
              <Testo>
                Forse usi già musica o soundscape nel tuo lavoro. Ma una
                traccia rimane una traccia: parte, finisce, e quello che
                è successo resta soltanto nella tua memoria e nei tuoi
                appunti.
              </Testo>
            </div>
            <div className="space-y-5">
              <Testo>
                Aurya Sound Professional trasforma l’ascolto in una
                pratica strutturata.
              </Testo>
              <Rilievo>
                Ogni esperienza ha un’intenzione, una durata e una
                progressione. E ogni sessione lascia una traccia scritta.
              </Rilievo>
            </div>
          </div>
        </Section>

        {/* ── LA LIBRERIA ────────────────────────────────────────── */}
        <Section tone="sand" labelledBy="prof-libreria" data-testid="prof-protocolli">
          <Occhiello>La libreria dei protocolli</Occhiello>
          <DisplayTitle id="prof-libreria" size="section">
            Non devi costruire un protocollo.<br />
            Devi scegliere quale esperienza condurre.
          </DisplayTitle>
          <div className="mt-12 grid gap-7 lg:grid-cols-3">
            {PROTOCOLLI.map(([titolo, testo], i) => (
              <Scheda key={titolo} titolo={titolo}
                accento={i === 1 ? VERDE : ORO}
                testid={`prof-protocollo-${titolo.toLowerCase()}`}>
                <p>{testo}</p>
              </Scheda>
            ))}
          </div>
          <Testo className="mt-9 max-w-2xl">
            E altri protocolli, organizzati per intenzione di pratica:
            ognuno con struttura, durata, basi di riferimento e
            indicazioni di conduzione.
          </Testo>
          <Rilievo className="mt-8">Scegli. Conduci. Osserva.</Rilievo>
        </Section>

        {/* ── LA SCATOLA NERA → L'ONDA VIVA ──────────────────────── */}
        <Section tone="cream" labelledBy="prof-onda" data-testid="prof-onda">
          <Occhiello>Vedi il protocollo prima di ascoltarlo</Occhiello>
          <DisplayTitle id="prof-onda" size="section">
            Il suono non è una scatola nera.
          </DisplayTitle>
          <Lede size="small" className="mt-5 max-w-2xl">
            Queste onde non sono una decorazione: si muovono con i
            numeri veri di GROUND e CALM, le stesse voci, le stesse
            ampiezze, lo stesso battito che poi ascolti.
          </Lede>
          <div className="mt-10 grid gap-7 lg:grid-cols-2 max-w-5xl">
            {ground && (
              <Finestra etichetta="GROUND" sotto="8 minuti · registro grave">
                <OndaViva score={ground} altezza={210} />
              </Finestra>
            )}
            {calm && (
              <Finestra etichetta="CALM" sotto="6 minuti · battito lento">
                <OndaViva score={calm} altezza={210} />
              </Finestra>
            )}
          </div>
          <div className="mt-10 max-w-3xl space-y-4">
            <Testo>
              Di ogni protocollo puoi guardare l’arco completo: quando
              entra un elemento, quando scompare, come rallenta il ritmo.
            </Testo>
            <Rilievo>
              Quello che vedi corrisponde a ciò che suona.
            </Rilievo>
          </div>
        </Section>

        {/* ── LO STORICO ─────────────────────────────────────────── */}
        <Section tone="paper" labelledBy="prof-storico">
          <Occhiello>Una sessione non sparisce quando finisce</Occhiello>
          <DisplayTitle id="prof-storico" size="section">
            Il tuo lavoro rimane.
          </DisplayTitle>
          <div className="mt-10 grid gap-12 lg:grid-cols-2 max-w-5xl items-start">
            <div>
              <Testo className="mb-7">
                Per ogni sessione lo storico conserva ciò che ti serve
                la volta successiva.
              </Testo>
              <ul className="grid grid-cols-2 gap-3">
                {STORICO.map((v) => (
                  <li key={v}
                    className="rounded-xl border px-4 py-3 text-base"
                    style={{ borderColor: '#e8e0ce' }}>{v}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="rounded-2xl border-2 p-8" style={{ borderColor: ORO }}>
                <p className="text-sm mb-4" style={{ color: ORO }}>
                  Sessione precedente
                </p>
                <p className="font-serif text-3xl mb-2">GROUND · 8 min.</p>
                <p className="text-base text-muted-foreground">
                  Note: buona risposta nella fase finale.
                </p>
              </div>
              <div className="mt-8 space-y-3">
                <Rilievo>
                  La volta dopo non parti da zero: apri lo storico e
                  riparti da lì.
                </Rilievo>
              </div>
            </div>
          </div>
        </Section>

        {/* ── I PERCORSI (banda) ─────────────────────────────────── */}
        <PhotoBand image={CALEIDO} focus="50% 50%" width="max-w-5xl"
          labelledBy="prof-percorsi" data-testid="prof-percorsi">
          <Occhiello tono="chiaro">Dalla singola sessione al percorso</Occhiello>
          <DisplayTitle id="prof-percorsi" size="section"
            className="text-white text-hero-shadow">
            Una sessione è un episodio.<br />Un percorso è una pratica.
          </DisplayTitle>
          <p className="mt-7 max-w-2xl text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
            Con Professional puoi costruire percorsi strutturati nel
            tempo, con un inizio, una progressione e una continuità.
          </p>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {PERCORSI.map((pc) => (
              <div key={pc.id}
                className="rounded-2xl border border-white/20 bg-black/30 backdrop-blur-sm p-7">
                <h3 className="font-serif text-2xl text-white uppercase tracking-wide">
                  {pc.titolo}
                </h3>
                <p className="mt-2 mb-5 text-sm" style={{ color: '#e0cfa4' }}>
                  {pc.durata.settimane} settimane · {pc.durata.a_settimana} sessioni
                  a settimana · {pc.tappe.length} tappe
                </p>
                <p className="text-[15px] leading-relaxed text-white/80">
                  {pc.indicazioni}
                </p>
              </div>
            ))}
          </div>
        </PhotoBand>

        {/* ── LE BASI ────────────────────────────────────────────── */}
        <Section tone="sand" labelledBy="prof-basi" data-testid="prof-onesta">
          <Occhiello>Le basi, dichiarate</Occhiello>
          <DisplayTitle id="prof-basi" size="section">
            Sai sempre cosa stai proponendo.
          </DisplayTitle>
          <div className="mt-8 max-w-3xl space-y-5">
            <Testo>
              Il mondo delle frequenze è pieno di promesse. Aurya sceglie
              la strada opposta: ogni protocollo dichiara le proprie basi
              di riferimento e il principio sonoro che utilizza.
            </Testo>
          </div>
          <ul className="mt-10 flex flex-wrap gap-3">
            {PRINCIPI.map((p) => (
              <li key={p} className="rounded-full border-2 px-6 py-2.5 text-base"
                style={{ borderColor: ORO }}>{p}</li>
            ))}
          </ul>
          <div className="mt-10 max-w-3xl border-l-2 pl-6"
            style={{ borderColor: ORO }}>
            <Testo>
              Che il cervello segua un ritmo sonoro è un fatto misurato:
              si chiama risposta uditiva stazionaria (ASSR) ed è
              neurofisiologia consolidata, usata ogni giorno in
              audiologia clinica. Che questo accompagni il rilassamento
              è indicato dalle review sull’entrainment (Garcia-Argibay
              2019, Chaieb 2015), evidenza promettente, non definitiva.
            </Testo>
          </div>
          <Rilievo className="mt-10 max-w-3xl">
            E dove l’evidenza è limitata, lo diciamo.
          </Rilievo>
        </Section>

        {/* ── SEMPLICE PER SCELTA ────────────────────────────────── */}
        <Section tone="sage" labelledBy="prof-usare">
          <Occhiello tono="chiaro">Semplice per scelta</Occhiello>
          <DisplayTitle id="prof-usare" size="section" className="text-[#f6f2e8]">
            Apri il protocollo. Leggi la struttura.<br />Avvia l’ascolto.
          </DisplayTitle>
          <div className="mt-8 grid gap-12 lg:grid-cols-2 max-w-5xl">
            <div className="space-y-5">
              <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85">
                Professional non è un nuovo Sound Lab: il Lab esiste per
                chi vuole esplorare il suono, Professional per chi vuole
                usarlo nelle sessioni. Niente oscillatori da configurare,
                niente frequenze da calcolare, niente sessioni da montare
                ogni volta.
              </p>
              <p className="font-serif text-2xl" style={{ color: '#e0cfa4' }}>
                E torni a occuparti della persona che hai davanti.
              </p>
            </div>
            <div>
              <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85 mb-6">
                Funziona direttamente dal browser. Nessuna attrezzatura
                speciale, nessuna installazione.
              </p>
              <div className="flex flex-wrap gap-3">
                {['Computer', 'Tablet', 'Cuffie o sistema audio'].map((v) => (
                  <span key={v}
                    className="rounded-full border border-[#f6f2e8]/30 px-5 py-2 text-base text-[#f6f2e8]/90">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Section>

        {/* ── IL FUTURO ──────────────────────────────────────────── */}
        <PhotoBand image={FUOCO} focus="50% 45%" width="max-w-4xl"
          labelledBy="prof-futuro" data-testid="prof-futuro">
          <Occhiello tono="chiaro">E questo è solo il primo livello</Occhiello>
          <DisplayTitle id="prof-futuro" size="section"
            className="text-white text-hero-shadow">
            Stiamo costruendo il passo successivo.
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Oggi Professional lavora sullo stimolo sonoro. Il prossimo
              passo è osservare anche la risposta della persona:
              respirazione, variabilità cardiaca, andamento nel tempo.
            </p>
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Non per dire alla persona cosa dovrebbe sentire, per
              permettere a te di osservare ciò che accade durante la
              pratica.
            </p>
            <p className="font-serif text-2xl sm:text-3xl text-white text-hero-shadow">
              Suono → risposta → osservazione → nuova sessione.
            </p>
          </div>
        </PhotoBand>

        {/* ── L'ACCESSO (con la qualificazione) ──────────────────── */}
        <Section tone="cream" labelledBy="prof-accesso" id="accesso"
          data-testid="prof-invito">
          <Occhiello>Per chi lavora con le persone</Occhiello>
          <DisplayTitle id="prof-accesso" size="section">
            Porta il suono nella tua pratica.
          </DisplayTitle>
          <ul className="mt-8 flex flex-wrap gap-3 max-w-3xl">
            {PRATICHE.map((p) => (
              <li key={p} className="rounded-full px-5 py-2 text-base"
                style={{ background: '#f2ece0' }}>{p}</li>
            ))}
          </ul>
          <Testo className="mt-8 max-w-2xl">
            Professional non sostituisce il tuo metodo: ti dà un nuovo
            strumento con cui lavorare. Stiamo aprendo l’accesso
            progressivamente, per costruire il prodotto insieme a chi lo
            usa davvero nelle proprie sessioni.
          </Testo>

          {stato === 'fatto' ? (
            <div className="mt-10 max-w-2xl rounded-2xl border-2 p-8"
              style={{ borderColor: ORO }} data-testid="prof-grazie">
              <p className="font-serif text-2xl mb-3">
                Ricevuto. Ti ricontattiamo noi.
              </p>
              <p className="text-base text-muted-foreground">
                Nel frattempo puoi{' '}
                <Link to="/sound" className="underline">esplorare Aurya Sound</Link>:
                la biblioteca, il Lab e le esperienze sono liberi.
              </p>
            </div>
          ) : (
            <form className="mt-12 max-w-2xl rounded-2xl border-2 p-8 sm:p-10"
              style={{ borderColor: ORO }} onSubmit={chiedi}>
              <p className="font-serif text-2xl mb-2">Richiedi l’accesso</p>
              <p className="text-base text-muted-foreground mb-7">
                Lascia il tuo contatto e raccontaci in due righe chi sei
                e come lavori.
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                <input type="text" value={nome} placeholder="Il tuo nome"
                  onChange={(e) => setNome(e.target.value)}
                  data-testid="prof-nome"
                  className="rounded-xl border border-[#d8cfba] bg-white
                             px-5 py-4 text-base" />
                <input type="email" value={email} required
                  placeholder="La tua email"
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="prof-email"
                  className="rounded-xl border border-[#d8cfba] bg-white
                             px-5 py-4 text-base" />
              </div>
              <textarea value={racconto} rows={3} maxLength={1000}
                placeholder="Chi sei e come lavori"
                onChange={(e) => setRacconto(e.target.value)}
                data-testid="prof-racconto"
                className="mt-4 w-full rounded-xl border border-[#d8cfba] bg-white
                           px-5 py-4 text-base" />
              <div className="mt-7 flex flex-wrap items-center gap-5">
                <button type="submit" disabled={stato === 'invio'}
                  data-testid="prof-invia"
                  className="inline-flex items-center gap-2 rounded-full px-8 py-4
                             text-base font-medium transition hover:opacity-90 disabled:opacity-50"
                  style={{ background: VERDE, color: '#f6f2e8' }}>
                  {stato === 'invio' ? 'Invio…' : 'Richiedi l’accesso →'}
                </button>
                <span className="text-sm text-muted-foreground">Accesso su invito.</span>
              </div>
              {typeof stato === 'string' && stato !== 'invio' && (
                <p className="mt-4 text-base text-[#a03434]">{stato}</p>
              )}
            </form>
          )}

          <div className="mt-20 border-t pt-10" style={{ borderColor: '#e8e0ce' }}>
            <Occhiello>Aurya Sound Professional</Occhiello>
            <p className="text-base text-muted-foreground">
              Protocolli sonori · Sessioni · Percorsi · Storico · Biofeedback
            </p>
            <p className="mt-8 max-w-3xl text-sm leading-relaxed text-muted-foreground"
              data-testid="prof-disclaimer">
              Aurya Sound Professional è uno strumento per esperienze di
              benessere e accompagnamento. Non è un dispositivo medico e
              non sostituisce diagnosi, trattamenti o indicazioni di
              professionisti sanitari.
            </p>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
