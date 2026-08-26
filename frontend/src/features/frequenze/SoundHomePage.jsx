/**
 * /sound — LA LANDING DI AURYA SOUND (26/8/2026 sera, seconda mano).
 *
 * Il testo e' del founder, verbatim. Il disegno risponde alle tre
 * cose che mi ha chiesto guardando la prima mano: testi PIU' GRANDI
 * (la scala del sito — i lead a `Lede`, il corpo a text-base/lg, non
 * piu' un 15px minuto), piu' CONTRASTO (le sezioni si alternano
 * chiaro/scuro invece di scorrere tutte crema) e l'ORO di marca dove
 * non sporca: occhielli, filetti, numerali, i richiami sulle bande.
 *
 * LE FOTOGRAFIE SONO UN RACCONTO. La pagina e' chiara come il sito, e
 * il BUIO arriva dove stai per entrare nel suono:
 *   onda    il vortice — l'apertura
 *   seta    le trame morbide — «poi puoi semplicemente ascoltare»
 *   trame   le scie — le Meditazioni, dove il linguaggio cambia
 *   fuoco   il blu che diventa arancio — il futuro, la risposta
 * L'ultima e' scelta apposta: e' la sola con del caldo dentro, e sta
 * dove il discorso smette di parlare di suono e comincia a parlare
 * di persone.
 */
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, Lede, PhotoBand, PhotoOpener, Section,
} from '../../components/editorial';
import {
  Bottone, Occhiello, ORO, Richiamo, Righe, Rilievo, Scheda, Testo, VERDE,
} from './soundKit';

const ONDA = '/media/sound/onda.jpg';
const SETA = '/media/sound/seta.jpg';
const TRAME = '/media/sound/trame.jpg';
const FUOCO = '/media/sound/fuoco.jpg';

const PASSI = [
  ['01', 'Studiamo', 'Partiamo da fenomeni sonori, ritmici e fisiologici e analizziamo ciò che è disponibile.'],
  ['02', 'Progettiamo', 'Trasformiamo i principi in una struttura sonora.'],
  ['03', 'Misuriamo', 'Utilizziamo il Sound Lab per verificare ciò che abbiamo costruito.'],
  ['04', 'Ascoltiamo', 'Lo trasformiamo in un’esperienza reale.'],
  ['05', 'Documentiamo', 'La struttura e le basi dell’esperienza rimangono leggibili.'],
];

const ESPERIENZE = [
  {
    id: 'calm', titolo: 'CALM', sotto: '6 minuti per rallentare.',
    righe: ['Un fondo stabile. Un respiro sonoro che si distende. Un battito lento che appare e poi scompare.',
      'Un’esperienza costruita per accompagnarti verso un ritmo più quieto.'],
  },
  {
    id: 'ground', titolo: 'GROUND', sotto: '8 minuti per scendere di tono.',
    righe: ['Un registro grave. Una pulsazione lenta. Materia sonora. Poi sempre meno.',
      'GROUND lavora sulla percezione del peso, della profondità e dello spazio attraverso il suono.'],
  },
  {
    id: 'respiro', titolo: 'RESPIRO', sotto: '10 minuti a sei respiri al minuto.',
    righe: ['Una nota che sale mentre inspiri e scende mentre espiri. Un tocco segna ogni svolta.',
      'Non devi contare: devi solo seguire. È il ritmo costante a essere la pratica.'],
  },
];

export default function SoundHomePage() {
  useEffect(() => {
    document.title = 'Aurya Sound — Il suono può diventare uno strumento | Aurya';
  }, []);

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
            <Richiamo to="/sound/professional" tono="chiaro" testid="sld-pro-link">
              Scopri Sound Professional →
            </Richiamo>
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
            Sono fenomeni diversi. Aurya Sound nasce per esplorarli e
            trasformarli in esperienze sonore progettate.
          </Testo>
          <Rilievo className="mt-6 max-w-2xl">
            Non una raccolta di tracce.<br />
            Un modo diverso di lavorare con il suono.
          </Rilievo>
        </Section>

        {/* ── LE TRE PORTE ───────────────────────────────────────── */}
        <Section tone="sand" labelledBy="sh-porte">
          <DisplayTitle id="sh-porte" size="section">
            Parti da ciò che ti incuriosisce.
          </DisplayTitle>
          <div className="mt-12 grid gap-7 lg:grid-cols-3">
            <Scheda occhiello="Esplora" titolo="La Biblioteca"
              testid="sh-porta-esplora"
              footer={<Richiamo to="/sound/esplora">Esplora la Biblioteca →</Richiamo>}>
              <p>Che cos’è davvero un binaural beat? Cosa succede quando
                ascolti un tono isocronico? Cosa significa una frequenza
                di 10 Hz?</p>
              <p>Aurya raccoglie <b className="text-foreground">36 schede</b> organizzate
                in quattro mondi: bande cerebrali, altre frequenze, ritmi
                del corpo, metodi.</p>
              <p>Ogni scheda parte dal fenomeno e ti aiuta a orientarti.</p>
            </Scheda>
            <Scheda occhiello="Impara" titolo="Il linguaggio del suono"
              testid="sh-porta-impara" accento={VERDE}
              footer={<Richiamo to="/sound/impara">Inizia a imparare →</Richiamo>}>
              <p className="font-serif text-lg text-foreground">
                Frequenza. Ampiezza. Binaurale. Entrainment. Isocronico.
                Spettro. Ritmo.
              </p>
              <p>Parole che incontri continuamente quando entri nel mondo
                del sound.</p>
              <p>Abbiamo raccolto i concetti essenziali in una guida
                semplice, senza trasformare il suono in qualcosa di più
                misterioso di quanto sia.</p>
            </Scheda>
            <Scheda occhiello="Sperimenta" titolo="Sound Lab"
              testid="sh-porta-lab"
              footer={<Richiamo to="/sound/lab">Entra nel Lab →</Richiamo>}>
              <p>Qui puoi smettere di leggere e iniziare a vedere.</p>
              <p>Genera una frequenza. Osserva la forma d’onda. Guarda lo
                spettro. Segui uno sweep.</p>
              <p>Il Lab mostra il segnale reale che stai ascoltando, non
                una rappresentazione preparata. È il nostro banco di
                prova — ed è anche il modo più semplice per iniziare a
                giocare con il suono.</p>
            </Scheda>
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
            Perché alla fine non è fatto per essere studiato soltanto.
            Tre esperienze brevi, accessibili gratuitamente.
          </p>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {ESPERIENZE.map((e) => (
              <div key={e.id}
                className="rounded-2xl border border-white/20 bg-black/25 backdrop-blur-sm p-7">
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
              Non tutto deve essere un protocollo. A volte il suono non
              deve spiegarti qualcosa: deve semplicemente accompagnarti.
            </p>
            <p className="font-serif text-2xl text-white text-hero-shadow">
              Voce. Musica. Paesaggi sonori. Composizioni originali. Silenzio.
            </p>
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Qui il linguaggio cambia. Non siamo più nel laboratorio:
              siamo dentro l’esperienza. Ogni meditazione nasce come un
              piccolo viaggio — una voce apre lo spazio, il suono lo
              accompagna, la musica cambia insieme alla pratica. E quando
              finisce, non deve essere rimasto altro che quello che ti
              serviva.
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
              <p className="font-serif text-2xl mb-4">CALM, GROUND, RESPIRO.</p>
              <Testo>Suono come fenomeno. Struttura, ritmo, frequenza, percezione.</Testo>
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
            Due linguaggi diversi. Lo stesso desiderio: creare esperienze
            che abbiano senso ascoltare.
          </Rilievo>
        </Section>

        {/* ── PROFESSIONAL ───────────────────────────────────────── */}
        <Section tone="sage" labelledBy="sh-pro" data-testid="sld-professional">
          <Occhiello tono="chiaro">
            Ma il suono può diventare anche uno strumento professionale
          </Occhiello>
          <DisplayTitle id="sh-pro" size="section" className="text-[#f6f2e8]">
            Aurya Sound Professional
          </DisplayTitle>
          <div className="mt-8 grid gap-10 lg:grid-cols-2 max-w-5xl">
            <div className="space-y-5">
              <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85">
                Se lavori con persone attraverso meditazione,
                respirazione, pratiche corporee o percorsi di benessere,
                probabilmente non hai bisogno di un altro software per
                creare musica. Hai bisogno di strumenti pronti per il tuo
                lavoro.
              </p>
              <p className="font-serif text-2xl sm:text-3xl text-[#f6f2e8]">
                Non devi progettare una frequenza.<br />
                Devi scegliere un’esperienza.
              </p>
            </div>
            <div className="space-y-5">
              <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85">
                Aurya Sound Professional mette a disposizione una libreria
                di protocolli sonori strutturati, progettati per essere
                utilizzati durante le sessioni. Ogni protocollo ha una
                propria struttura: intento, durata, progressione, elementi
                sonori, basi di riferimento, indicazioni di conduzione.
              </p>
              <p className="text-base sm:text-lg leading-relaxed text-[#f6f2e8]/85">
                Una sessione non dovrebbe scomparire quando il suono
                finisce: con Professional mantieni uno storico — quale
                protocollo, quale versione, quando, quanto è durato, le
                tue note.
              </p>
              <p className="font-serif text-xl" style={{ color: '#e0cfa4' }}>
                Non ricordare: registrare.<br />
                Non improvvisare ogni volta: costruire un percorso.
              </p>
            </div>
          </div>
          <div className="mt-12">
            <Bottone to="/sound/professional" tono="chiaro">
              Scopri Sound Professional →
            </Bottone>
          </div>
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
              basi interessanti. Altre sono ancora oggetto di ricerca.
              Altre appartengono alla tradizione. Noi preferiamo
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
          <Lede size="small" className="mt-5">Il processo è semplice.</Lede>
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
              Oggi Aurya Sound lavora principalmente sul suono. Ma stiamo
              costruendo qualcosa di più interessante.
            </p>
            <p className="text-base sm:text-lg leading-relaxed text-white/85 text-hero-shadow">
              Il prossimo passo di Sound Professional è il biofeedback:
              non soltanto creare uno stimolo, ma poter osservare cosa
              succede durante una sessione. Respirazione. Variabilità.
              Segnali fisiologici. Risposta nel tempo.
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
              Porta Aurya Sound nelle tue sessioni.
            </p>
            <Bottone to="/sound/professional">Scopri Sound Professional →</Bottone>
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
              <Occhiello>Aurya Sound Professional</Occhiello>
              <p className="text-base text-muted-foreground leading-relaxed">
                Protocolli · Sessioni · Percorsi · Storico · Biofeedback
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
