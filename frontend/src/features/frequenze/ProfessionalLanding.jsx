/**
 * /sound/professional — LA PAGINA DI VENDITA (L4, rivista L3-bis).
 *
 * Visione founder: le pagine di PRESENTAZIONE stanno nel mondo
 * chiaro del sito; il blu comincia quando si entra nello strumento.
 * Quindi: MarketplaceShell + kit editoriale — e le partiture, che
 * sono del mondo scuro, compaiono come FINESTRE: riquadri .fqz
 * incastonati nella pagina chiara. Una scelta che è anche un
 * racconto: ecco come si vede, di là.
 *
 * IL REGISTRO DELLA VOCE (C0): scienza in avanti — l'ASSR in
 * apertura, le review nominate — e i limiti presenti ma mai in
 * apertura. Niente percentuali da sondaggio, niente promesse.
 * Le partiture sono generate dagli score REALI del catalogo.
 *
 * Il filo: ti fidi (prova gratis) → capisci (teorie, partiture) →
 * vuoi (rito, registro) → chiedi l'invito (funnel leads esistente).
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, EditorialCta, Lede, Section,
} from '../../components/editorial';
import Partitura from './pro/Partitura';
import { CATALOGO } from './pro/catalogo';
import { PERCORSI } from './pro/percorsi';
import { messaggio } from './pro/errori';
import './frequenze.css';

const PILASTRI = [
  {
    t: 'Il metodo',
    d: 'Protocolli d’ascolto con un arco preciso e basi dichiarate '
      + 'scheda per scheda, percorsi di più settimane con dose e '
      + 'cadenza, controindicazioni serie. Il suono smette di essere '
      + 'un sottofondo e diventa parte del tuo lavoro.',
  },
  {
    t: 'La memoria',
    d: 'Ogni sessione resta nel registro: con chi, cosa, com’è '
      + 'andata. Alla seduta dopo leggi «la volta scorsa: da 4 a 7» '
      + 'invece di andare a memoria. È la differenza fra mettere '
      + 'musica e condurre una pratica di cui rispondi.',
  },
  {
    t: 'La misura',
    d: 'Il vissuto dichiarato dalla persona, prima e dopo, disegnato '
      + 'nel tempo. E nella direzione di sviluppo: la variabilità '
      + 'cardiaca durante la respirazione guidata — l’evidenza più '
      + 'forte di tutto questo campo.',
  },
];

/* la FINESTRA: un riquadro del mondo scuro dentro la pagina chiara */
function Finestra({ children }) {
  return (
    <div className="fqz rounded-2xl p-4 sm:p-5"
      style={{ background: '#0E1B1E', border: '1px solid #1B2E32' }}>
      {children}
    </div>
  );
}

export default function ProfessionalLanding() {
  useEffect(() => {
    document.title = 'Aurya Sound Professional — l’ascolto guidato per professionisti';
  }, []);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [stato, setStato] = useState(null);   // null | 'invio' | 'fatto' | errore

  const ground = CATALOGO.find((p) => p.id === 'ground');
  const rilassare = CATALOGO.find((p) => p.id === 'rilassare');

  const chiedi = async (e) => {
    e.preventDefault();
    if (!email.trim() || stato === 'invio') return;
    setStato('invio');
    try {
      await api.post('/public/leads', {
        type: 'operator',
        email: email.trim(),
        name: nome.trim() || null,
        message: 'Aurya Sound Professional — richiesta di invito',
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

        {/* ── APERTURA: il fatto misurabile ── */}
        <Section tone="cream" rhythm="hero" labelledBy="prof-title">
          <p className="text-xs tracking-[0.22em] uppercase text-muted-foreground mb-4">
            Aurya Sound Professional
          </p>
          <DisplayTitle as="h1" id="prof-title" size="manifesto" measure="wide">
            L’ascolto guidato
          </DisplayTitle>
          <Lede className="mt-6 max-w-2xl" data-testid="prof-lead">
            Il cervello segue la stimolazione sonora ritmica: si chiama
            risposta uditiva stazionaria (ASSR), è neurofisiologia
            consolidata. Su questa base, Aurya Sound Professional ti dà
            protocolli d’ascolto strutturati da condurre con i tuoi
            clienti — con le basi dichiarate, il registro di ogni
            sessione, e nessuna attrezzatura da comprare.
          </Lede>
          <div className="mt-8 flex flex-wrap items-center gap-5">
            <EditorialCta href="#invito" variant="solid">
              Richiedi l’invito
            </EditorialCta>
            <Link to="/sound/ground"
              className="text-sm underline underline-offset-4 text-muted-foreground hover:text-foreground">
              Ascolta GROUND, gratis, adesso →
            </Link>
          </div>
        </Section>

        {/* ── i tre pilastri ── */}
        <Section tone="paper" labelledBy="prof-pilastri-t" data-testid="prof-pilastri">
          <DisplayTitle id="prof-pilastri-t">Tre cose che una playlist non avrà mai</DisplayTitle>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {PILASTRI.map((p) => (
              <article key={p.t}
                className="rounded-2xl border border-[#e5ddcb] bg-background p-6">
                <h3 className="font-serif text-xl mb-3">{p.t}</h3>
                <p className="text-sm leading-6 text-muted-foreground">{p.d}</p>
              </article>
            ))}
          </div>
        </Section>

        {/* ── la prova visiva: finestre sul mondo scuro ── */}
        <Section tone="sand" labelledBy="prof-part-t" data-testid="prof-partiture">
          <DisplayTitle id="prof-part-t">Ogni protocollo si vede, prima di sentirsi</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            Queste sono partiture vere, generate dai protocolli reali —
            di là, nella stanza d’ascolto, la luce è questa. Le bande
            sono i suoni che entrano ed escono, lo spessore è
            l’intensità: niente è decorativo, se si vede è nel suono.
          </Lede>
          <div className="mt-8 grid gap-6 max-w-3xl">
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                GROUND — otto minuti di registro basso che si sente
                prima nel corpo che nelle orecchie.
              </p>
              {ground && <Finestra><Partitura score={ground.costruisci()} dettaglio /></Finestra>}
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                Rilassare — l’uso meglio documentato del catalogo: un
                battito binaurale che si stabilizza e ci resta
                (review: Garcia-Argibay 2019, Chaieb 2015).
              </p>
              {rilassare && <Finestra><Partitura score={rilassare.costruisci()} /></Finestra>}
            </div>
          </div>
        </Section>

        {/* ── percorsi ── */}
        <Section tone="paper" labelledBy="prof-pc-t" data-testid="prof-percorsi">
          <DisplayTitle id="prof-pc-t">Percorsi, non playlist</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            La pratica che funziona è quella che torna: percorsi di più
            settimane con una cadenza e una progressione, e il registro
            che ricorda a che punto è ogni persona.
          </Lede>
          <div className="mt-8 grid gap-5 sm:grid-cols-3 max-w-3xl">
            {PERCORSI.map((pc) => (
              <div key={pc.id}
                className="rounded-2xl border border-[#e5ddcb] bg-white p-5">
                <b className="font-serif text-lg block mb-1">{pc.titolo}</b>
                <span className="text-xs text-muted-foreground">
                  {pc.durata.settimane} settimane · {pc.durata.a_settimana} a settimana · {pc.tappe.length} tappe
                </span>
              </div>
            ))}
          </div>
        </Section>

        {/* ── l'onestà come firma ── */}
        <Section tone="sage" labelledBy="prof-onesta-t" data-testid="prof-onesta">
          <DisplayTitle id="prof-onesta-t" className="text-[#f6f2e8]">
            Le basi, in faccia
          </DisplayTitle>
          <Lede size="small" tone="inverse" className="mt-4 max-w-2xl opacity-90">
            Ogni scheda nomina la sua teoria e le sue fonti —
            entrainment uditivo, psicoacustica delle basse frequenze,
            respirazione di risonanza — e dichiara il grado di
            evidenza, punti di forza e confini compresi. Nessuna
            percentuale da sondaggio, nessuna promessa di stati: chi sa
            dove finisce la propria evidenza è chi la sta usando
            davvero. È il motivo per cui puoi proporla ai tuoi clienti
            a testa alta.
          </Lede>
        </Section>

        {/* ── la richiesta d'invito ── */}
        <Section tone="cream" labelledBy="prof-invito-t" id="invito"
          data-testid="prof-invito">
          <DisplayTitle id="prof-invito-t">Su invito, per cominciare bene</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            Stiamo aprendo Aurya Sound Professional a un gruppo
            ristretto di professionisti, per costruirlo con chi lo usa.
            Lascia la tua email: ti scriviamo noi.
          </Lede>
          {stato === 'fatto' ? (
            <p className="mt-6 text-[15px] text-[#2f5749]" data-testid="prof-grazie">
              Ricevuto. Ti scriviamo a breve — nel frattempo puoi{' '}
              <Link to="/sound" className="underline">esplorare Aurya Sound</Link>.
            </p>
          ) : (
            <form className="mt-8 flex flex-wrap gap-3 max-w-2xl" onSubmit={chiedi}>
              <input type="text" value={nome} placeholder="Il tuo nome"
                onChange={(e) => setNome(e.target.value)}
                className="flex-1 min-w-[180px] rounded-xl border border-[#d8cfba] bg-white px-4 py-3 text-sm"
                data-testid="prof-nome" />
              <input type="email" value={email} required
                placeholder="La tua email"
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 min-w-[220px] rounded-xl border border-[#d8cfba] bg-white px-4 py-3 text-sm"
                data-testid="prof-email" />
              <button type="submit" data-testid="prof-invia"
                disabled={stato === 'invio'}
                className="rounded-xl bg-[#2f5749] px-6 py-3 text-sm font-medium text-[#f6f2e8] hover:opacity-90 disabled:opacity-50">
                {stato === 'invio' ? 'Invio…' : 'Richiedi l’invito'}
              </button>
            </form>
          )}
          {typeof stato === 'string' && stato !== 'invio' && stato !== 'fatto' && (
            <p className="mt-3 text-sm text-red-700">{stato}</p>
          )}
          <p className="mt-4 text-xs text-muted-foreground">
            Niente spam: una richiesta, una risposta. I dati restano in
            Aurya (<Link to="/privacy" className="underline">privacy</Link>).
          </p>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
