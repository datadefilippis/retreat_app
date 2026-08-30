/**
 * /sound/studio — CREA STUDIO, la landing della via professionale
 * (27/8/2026, deciso col founder).
 *
 * La storia di questa pagina: Professional e' uscito dalla vetrina
 * (il catalogo da solo non supera il valore del premere play) e la
 * promessa professionale di Aurya Sound e' diventata l'ATELIER — Crea,
 * lo strumento con cui il founder ha composto l'intero catalogo e le
 * meditazioni. Questa landing lo racconta e raccoglie l'interesse sul
 * funnel leads (interests: sound_crea). Il modulo vero e proprio e'
 * il ciclo TR (docs/CREA_TRACCE_RISERVATE_PLAN_2026-08.md).
 *
 * Scheletro ereditato dalla ProfessionalLanding (che resta viva e non
 * linkata: asset SEO): apertura fotografica → il problema → come
 * funziona → la prova (le onde vive) → il privato → per chi + form.
 * Fotografie: spirale (struttura e precisione — l'atelier), caleido
 * (la ripetizione che diventa forma — il privato).
 *
 * LA PROVA E' VERA anche qui: le finestre OndaViva si muovono con gli
 * score del catalogo (costruisci()), e la pagina NON suona.
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
import { messaggio } from './pro/errori';

const SPIRALE = '/media/sound/spirale.jpg';
const CALEIDO = '/media/sound/caleido.jpg';

const PASSI = [
  ['Registra', 'La tua voce, dal browser: accogli, guidi, congedi. Spezzoni che tagli e piazzi dove servono.'],
  ['Componi', 'Basi sonore dalla libreria, frequenze del motore, la scena visiva. Tutto in un unico strumento.'],
  ['Condividi', 'Un link riservato per i tuoi clienti. Fuori dal catalogo pubblico, dentro la tua pratica.'],
];

const PRATICHE = ['Meditazione', 'Breathwork', 'Yoga e pratiche corporee',
  'Sound healing', 'Percorsi di rilassamento', 'Accompagnamento olistico'];

/* la FINESTRA sull'onda: di la' dal vetro c'e' Aurya Sound */
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

export default function CreaStudioLanding() {
  useEffect(() => {
    document.title = 'Crea Studio: componi le tue meditazioni | Aurya';
  }, []);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [racconto, setRacconto] = useState('');
  const [stato, setStato] = useState(null);   // null | 'invio' | 'fatto' | errore

  /* gli score VERI del catalogo: la prova che lo strumento esiste */
  const calm = useMemo(
    () => CATALOGO.find((p) => p.id === 'calm')?.costruisci(), []);
  const ground = useMemo(
    () => CATALOGO.find((p) => p.id === 'ground')?.costruisci(), []);

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
          || 'Crea Studio, richiesta di accesso',
        interests: ['sound_crea'],
      });
      setStato('fatto');
    } catch (err) {
      setStato(messaggio(err, 'Non inviato: riprova fra un momento.'));
    }
  };

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="studio-landing">

        {/* ── APERTURA ───────────────────────────────────────────── */}
        <PhotoOpener image={SPIRALE} focus="62% 55%" height="tall" align="left"
          width="max-w-4xl" labelledBy="studio-title" data-testid="studio-open">
          <Occhiello tono="chiaro">Crea Studio</Occhiello>
          <DisplayTitle as="h1" id="studio-title" size="hero" measure="wide"
            className="text-hero-shadow">
            La tua voce, le tue meditazioni.
          </DisplayTitle>
          <Lede className="mt-8 max-w-2xl text-white/90 text-hero-shadow" tone="inherit">
            L’atelier con cui nascono le meditazioni di Aurya, aperto ai
            professionisti del benessere.
          </Lede>
          <div className="mt-7 max-w-xl space-y-2 text-base sm:text-lg text-white/75 text-hero-shadow">
            <p>Non un’app di meditazioni già fatte.</p>
            <p>Non serve uno studio di registrazione.</p>
            <p>Non serve saper produrre audio.</p>
          </div>
          <p className="mt-8 font-serif text-2xl sm:text-3xl text-white text-hero-shadow">
            Componi con la tua voce.<br />
            Condividi in privato con i tuoi clienti.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Bottone href="#accesso" tono="chiaro" testid="studio-cta-hero">
              Richiedi l’accesso →
            </Bottone>
          </div>
        </PhotoOpener>

        {/* ── IL PROBLEMA → LA PROMESSA ──────────────────────────── */}
        <Section tone="cream" labelledBy="studio-entra">
          <DisplayTitle id="studio-entra" size="section">
            La tua guida finisce quando finisce la sessione.
          </DisplayTitle>
          <div className="mt-8 grid gap-12 lg:grid-cols-2 max-w-5xl">
            <div className="space-y-5">
              <Testo>
                Dal vivo, la tua voce accompagna: apre lo spazio, guida
                il respiro, chiude il cerchio. Poi la persona torna a
                casa, e di quella voce non resta niente, fino alla
                prossima sessione.
              </Testo>
            </div>
            <div className="space-y-5">
              <Testo>
                Con Crea Studio la tua guida diventa una meditazione:
                i tuoi clienti la riascoltano quando serve davvero —
                la sera, in viaggio, nei giorni tra una sessione e
                l’altra.
              </Testo>
              <Rilievo>
                La tua pratica continua a lavorare anche quando tu non
                ci sei.
              </Rilievo>
            </div>
          </div>
        </Section>

        {/* ── COME FUNZIONA ──────────────────────────────────────── */}
        <Section tone="sand" labelledBy="studio-come" data-testid="studio-passi">
          <Occhiello>Tre gesti, dal browser</Occhiello>
          <DisplayTitle id="studio-come" size="section">
            Registra. Componi. Condividi.
          </DisplayTitle>
          <div className="mt-12 grid gap-7 lg:grid-cols-3">
            {PASSI.map(([titolo, testo], i) => (
              <Scheda key={titolo} titolo={titolo}
                occhiello={`0${i + 1}`}
                accento={i === 1 ? VERDE : ORO}>
                <p>{testo}</p>
              </Scheda>
            ))}
          </div>
          <Testo className="mt-9 max-w-2xl">
            Niente da installare, niente da montare: funziona dal
            browser, su computer e tablet. Il suono lo rende Aurya —
            tu porti la voce e l’intenzione.
          </Testo>
        </Section>

        {/* ── LA PROVA ───────────────────────────────────────────── */}
        <Section tone="cream" labelledBy="studio-prova" data-testid="studio-prova">
          <Occhiello>Non è una promessa: è già successo</Occhiello>
          <DisplayTitle id="studio-prova" size="section">
            Con Crea sono nate le meditazioni di Aurya.
          </DisplayTitle>
          <Lede size="small" className="mt-5 max-w-2xl">
            Le esperienze e le meditazioni che ascolti su Aurya Sound
            sono composte con questo strumento. Queste onde si muovono
            con i loro numeri veri.
          </Lede>
          <div className="mt-10 grid gap-7 lg:grid-cols-2 max-w-5xl">
            {ground && (
              <Finestra etichetta="GROUND" sotto="8 minuti · registro grave">
                <OndaViva score={ground} altezza={200} />
              </Finestra>
            )}
            {calm && (
              <Finestra etichetta="CALM" sotto="6 minuti · battito lento">
                <OndaViva score={calm} altezza={200} />
              </Finestra>
            )}
          </div>
        </Section>

        {/* ── IL PRIVATO (banda) ─────────────────────────────────── */}
        <PhotoBand image={CALEIDO} focus="50% 50%" width="max-w-4xl"
          labelledBy="studio-privato" data-testid="studio-privato">
          <Occhiello tono="chiaro">Fuori dalla vetrina, dentro la tua pratica</Occhiello>
          <DisplayTitle id="studio-privato" size="section"
            className="text-white text-hero-shadow">
            Le tue meditazioni restano tue.
          </DisplayTitle>
          <div className="mt-7 max-w-2xl space-y-5">
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Quello che componi non entra nel catalogo pubblico di
              Aurya: lo condividi tu, con un link riservato, alle
              persone che scegli. E puoi revocarlo quando vuoi.
            </p>
            <p className="font-serif text-2xl sm:text-3xl text-white text-hero-shadow">
              Il tuo repertorio, il tuo nome,<br />i tuoi clienti.
            </p>
            <p className="text-base sm:text-lg leading-relaxed" style={{ color: '#e0cfa4' }}>
              E domani: meditazioni assegnate per persona, percorsi nel
              tempo, l’ascolto che si vede. Un passo alla volta.
            </p>
          </div>
        </PhotoBand>

        {/* ── PER CHI + ACCESSO ──────────────────────────────────── */}
        <Section tone="cream" labelledBy="studio-accesso" id="accesso"
          data-testid="studio-invito">
          <Occhiello>Per chi lavora con le persone</Occhiello>
          <DisplayTitle id="studio-accesso" size="section">
            Porta la tua voce oltre la sessione.
          </DisplayTitle>
          <ul className="mt-8 flex flex-wrap gap-3 max-w-3xl">
            {PRATICHE.map((p) => (
              <li key={p} className="rounded-full px-5 py-2 text-base"
                style={{ background: '#f2ece0' }}>{p}</li>
            ))}
          </ul>
          <Testo className="mt-8 max-w-2xl">
            Stiamo aprendo Crea Studio progressivamente, su invito o in
            partnership: vogliamo costruirlo insieme a chi lo userà
            davvero con i propri clienti.
          </Testo>
          {/* FN5 (30/8), la prova sociale: il portfolio di Crea sono
              le meditazioni gia' pubblicate. Chi esita, ascolta. */}
          <Rilievo className="mt-6 max-w-2xl" data-testid="studio-prova-sociale">
            Le meditazioni che senti su Aurya{' '}
            <Link to="/meditazioni" className="underline underline-offset-4">
              nascono qui</Link>.
          </Rilievo>

          {stato === 'fatto' ? (
            <div className="mt-10 max-w-2xl rounded-2xl border-2 p-8"
              style={{ borderColor: ORO }} data-testid="studio-grazie">
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
                e come lavori. Ti rispondiamo in pochi giorni: si parte
                con una chiacchierata di venti minuti.
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                <input type="text" value={nome} placeholder="Il tuo nome"
                  onChange={(e) => setNome(e.target.value)}
                  data-testid="studio-nome"
                  className="rounded-xl border border-[#d8cfba] bg-white
                             px-5 py-4 text-base" />
                <input type="email" value={email} required
                  placeholder="La tua email"
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="studio-email"
                  className="rounded-xl border border-[#d8cfba] bg-white
                             px-5 py-4 text-base" />
              </div>
              <textarea value={racconto} rows={3} maxLength={1000}
                placeholder="Chi sei e come lavori"
                onChange={(e) => setRacconto(e.target.value)}
                data-testid="studio-racconto"
                className="mt-4 w-full rounded-xl border border-[#d8cfba] bg-white
                           px-5 py-4 text-base" />
              <div className="mt-7 flex flex-wrap items-center gap-5">
                <button type="submit" disabled={stato === 'invio'}
                  data-testid="studio-invia"
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
            <Occhiello>Crea Studio</Occhiello>
            <p className="text-base text-muted-foreground">
              La tua voce · Basi sonore · Frequenze · Scena visiva · Link riservati
            </p>
            <p className="mt-8 max-w-3xl text-sm leading-relaxed text-muted-foreground"
              data-testid="studio-disclaimer">
              Crea Studio è uno strumento per comporre esperienze di
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
