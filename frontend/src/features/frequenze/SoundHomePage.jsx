/**
 * /sound — LA LANDING DI AURYA SOUND (L3-ter, 26/8/2026 sera).
 *
 * Il testo e' del founder, verbatim: e' la sua voce, e non si
 * riscrive. Qui c'e' solo il disegno — i colori del sito (crema,
 * bianco, il verde d'ancora), il kit editoriale di casa, e le TRE
 * FOTOGRAFIE come bande scure.
 *
 * LE BANDE SCURE SONO UN RACCONTO, non decorazione: la pagina e'
 * chiara come tutto il sito, e il BLU compare dove stai per entrare
 * nel suono. `onda` (il vortice radiale) apre; `trame` accompagna le
 * Meditazioni, dove il linguaggio cambia e si entra nell'esperienza;
 * `materia` sta sotto il futuro (biofeedback), che e' la parte che
 * ancora non si tocca.
 *
 * I MOVIMENTI, nell'ordine del testo:
 *   apertura · non tutto il suono e' musica · le tre porte
 *   (esplora/impara/sperimenta) · le esperienze · le meditazioni ·
 *   i due linguaggi · Professional (lo strumento, e lo storico) ·
 *   l'onestà · il processo in cinque tempi · il futuro · il congedo
 */
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, EditorialCta, Lede, PhotoBand, PhotoOpener, Section,
} from '../../components/editorial';

const ONDA = '/media/sound/onda.jpg';        // il vortice: l'apertura
const TRAME = '/media/sound/trame.jpg';      // le meditazioni
const MATERIA = '/media/sound/materia.jpg';  // il futuro

/* una riga sola, in colonna: il ritmo del testo del founder vuole
   respiro fra un fenomeno e l'altro */
function Righe({ voci, className = '' }) {
  return (
    <div className={`mt-6 space-y-4 ${className}`}>
      {voci.map((v) => (
        <p key={v} className="text-[15px] leading-7 text-muted-foreground">{v}</p>
      ))}
    </div>
  );
}

function Porta({ occhiello, titolo, children, to, cta, testid }) {
  return (
    <article className="rounded-2xl border border-[#e5ddcb] bg-white p-7 flex flex-col"
      data-testid={testid}>
      <p className="text-[10px] tracking-[0.2em] uppercase text-[#2f5749] mb-3">
        {occhiello}
      </p>
      <h3 className="font-serif text-2xl mb-4">{titolo}</h3>
      <div className="text-sm leading-6 text-muted-foreground space-y-3 flex-1">
        {children}
      </div>
      <div className="mt-6">
        <EditorialCta to={to} variant="quiet">{cta}</EditorialCta>
      </div>
    </article>
  );
}

const PASSI = [
  ['01', 'Studiamo', 'Partiamo da fenomeni sonori, ritmici e fisiologici e analizziamo ciò che è disponibile.'],
  ['02', 'Progettiamo', 'Trasformiamo i principi in una struttura sonora.'],
  ['03', 'Misuriamo', 'Utilizziamo il Sound Lab per verificare ciò che abbiamo costruito.'],
  ['04', 'Ascoltiamo', 'Lo trasformiamo in un’esperienza reale.'],
  ['05', 'Documentiamo', 'La struttura e le basi dell’esperienza rimangono leggibili.'],
];

export default function SoundHomePage() {
  useEffect(() => {
    document.title = 'Aurya Sound — Il suono può diventare uno strumento | Aurya';
  }, []);

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="sound-home">

        {/* ── APERTURA ── */}
        <PhotoOpener image={ONDA} focus="50% 50%" height="tall" align="left"
          width="max-w-3xl" labelledBy="sh-title" eyebrow="Aurya Sound"
          data-testid="sh-open">
          <DisplayTitle as="h1" id="sh-title" size="manifesto" measure="wide"
            className="text-hero-shadow">
            Il suono può diventare uno strumento.
          </DisplayTitle>
          <p className="mt-6 max-w-xl text-[15px] leading-7 text-white/90 text-hero-shadow">
            Frequenze, ritmo, respiro, spazio e musica. Aurya Sound è uno
            spazio per esplorare il suono, comprenderne i meccanismi e
            trasformarlo in esperienze da ascoltare.
          </p>
          <p className="mt-5 max-w-xl text-[15px] leading-7 text-white/90 text-hero-shadow">
            Puoi studiarlo. Puoi sperimentarlo. Puoi semplicemente
            ascoltarlo. E, se sei un professionista, puoi portarlo nel
            tuo lavoro.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <EditorialCta to="/sound/esplora" variant="solid" tone="dark"
              data-testid="sh-cta-esplora">Esplora Aurya Sound</EditorialCta>
            <EditorialCta to="/sound/professional" variant="quiet" tone="dark"
              data-testid="sld-pro-link">Scopri Sound Professional →</EditorialCta>
          </div>
        </PhotoOpener>

        {/* ── NON TUTTO IL SUONO È MUSICA ── */}
        <Section tone="cream" labelledBy="sh-fenomeni">
          <DisplayTitle id="sh-fenomeni">Non tutto il suono è musica.</DisplayTitle>
          <Righe className="max-w-2xl" voci={[
            'Un tono può cambiare lentamente.',
            'Un ritmo può diventare più lento.',
            'Due frequenze possono creare un battito percepibile nello spazio tra le orecchie.',
            'Una nota grave può trasformare completamente la percezione di un ambiente.',
            'Il respiro può diventare ritmo.',
          ]} />
          <p className="mt-8 max-w-2xl text-[15px] leading-7">
            Sono fenomeni diversi. Aurya Sound nasce per esplorarli e
            trasformarli in esperienze sonore progettate.
          </p>
          <p className="mt-4 max-w-2xl font-serif text-xl">
            Non una raccolta di tracce. Un modo diverso di lavorare con
            il suono.
          </p>
        </Section>

        {/* ── LE TRE PORTE ── */}
        <Section tone="sand" labelledBy="sh-porte">
          <DisplayTitle id="sh-porte">Parti da ciò che ti incuriosisce.</DisplayTitle>
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            <Porta occhiello="Esplora" titolo="La Biblioteca"
              to="/sound/esplora" cta="Esplora la Biblioteca →"
              testid="sh-porta-esplora">
              <p>Che cos’è davvero un binaural beat? Cosa succede quando
                ascolti un tono isocronico? Cosa significa una frequenza
                di 10 Hz?</p>
              <p>Aurya raccoglie 36 schede organizzate in quattro mondi:
                bande cerebrali, altre frequenze, ritmi del corpo,
                metodi.</p>
              <p>Ogni scheda parte dal fenomeno e ti aiuta a orientarti.</p>
            </Porta>
            <Porta occhiello="Impara" titolo="Il linguaggio del suono"
              to="/sound/impara" cta="Inizia a imparare →"
              testid="sh-porta-impara">
              <p>Frequenza. Ampiezza. Binaurale. Entrainment. Isocronico.
                Spettro. Ritmo.</p>
              <p>Parole che incontri continuamente quando entri nel mondo
                del sound.</p>
              <p>Abbiamo raccolto i concetti essenziali in una guida
                semplice, senza trasformare il suono in qualcosa di più
                misterioso di quanto sia.</p>
            </Porta>
            <Porta occhiello="Sperimenta" titolo="Sound Lab"
              to="/sound/lab" cta="Entra nel Lab →" testid="sh-porta-lab">
              <p>Qui puoi smettere di leggere e iniziare a vedere.</p>
              <p>Genera una frequenza. Osserva la forma d’onda. Guarda lo
                spettro. Segui uno sweep.</p>
              <p>Il Lab mostra il segnale reale che stai ascoltando, non
                una rappresentazione preparata. È il nostro banco di
                prova — ed è anche il modo più semplice per iniziare a
                giocare con il suono.</p>
            </Porta>
          </div>
        </Section>

        {/* ── LE ESPERIENZE ── */}
        <Section tone="paper" labelledBy="sh-esperienze"
          data-testid="sh-porta-esperienze">
          <DisplayTitle id="sh-esperienze">Poi puoi semplicemente ascoltare.</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            Perché alla fine il suono non è fatto per essere studiato
            soltanto. È fatto per essere vissuto. Tre esperienze brevi,
            accessibili gratuitamente.
          </Lede>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-[#e5ddcb] p-7">
              <h3 className="font-serif text-2xl">CALM</h3>
              <p className="text-sm text-[#2f5749] mb-4">6 minuti per rallentare.</p>
              <div className="text-sm leading-6 text-muted-foreground space-y-2">
                <p>Un fondo stabile. Un respiro sonoro che si distende.
                  Un battito lento che appare e poi scompare.</p>
                <p>Un’esperienza costruita per accompagnarti verso un
                  ritmo più quieto.</p>
              </div>
              <div className="mt-6">
                <EditorialCta to="/sound/calm" variant="quiet">Ascolta CALM →</EditorialCta>
              </div>
            </div>
            <div className="rounded-2xl border border-[#e5ddcb] p-7">
              <h3 className="font-serif text-2xl">GROUND</h3>
              <p className="text-sm text-[#2f5749] mb-4">8 minuti per scendere di tono.</p>
              <div className="text-sm leading-6 text-muted-foreground space-y-2">
                <p>Un registro grave. Una pulsazione lenta. Materia
                  sonora. Poi sempre meno.</p>
                <p>GROUND lavora sulla percezione del peso, della
                  profondità e dello spazio attraverso il suono.</p>
              </div>
              <div className="mt-6">
                <EditorialCta to="/sound/ground" variant="quiet">Ascolta GROUND →</EditorialCta>
              </div>
            </div>
            <div className="rounded-2xl border border-[#e5ddcb] p-7">
              <h3 className="font-serif text-2xl">RESPIRO</h3>
              <p className="text-sm text-[#2f5749] mb-4">10 minuti a sei respiri al minuto.</p>
              <div className="text-sm leading-6 text-muted-foreground space-y-2">
                <p>Una nota che sale mentre inspiri e scende mentre
                  espiri. Un tocco segna ogni svolta.</p>
                <p>Non devi contare: devi solo seguire. È il ritmo
                  costante a essere la pratica.</p>
              </div>
              <div className="mt-6">
                <EditorialCta to="/sound/respiro" variant="quiet">Ascolta RESPIRO →</EditorialCta>
              </div>
            </div>
          </div>
        </Section>

        {/* ── LE MEDITAZIONI: qui il linguaggio cambia ── */}
        <PhotoBand image={TRAME} focus="50% 50%" width="max-w-3xl"
          labelledBy="sh-meditazioni" data-testid="sh-porta-meditazioni">
          <p className="text-[10px] tracking-[0.2em] uppercase text-white/70 mb-4">
            E poi c’è un altro modo di usare il suono
          </p>
          <DisplayTitle id="sh-meditazioni" className="text-white text-hero-shadow">
            Le Meditazioni Aurya
          </DisplayTitle>
          <div className="mt-6 max-w-xl space-y-4 text-[15px] leading-7 text-white/90 text-hero-shadow">
            <p>Non tutto deve essere un protocollo. A volte il suono non
              deve spiegarti qualcosa: deve semplicemente accompagnarti.</p>
            <p>Voce. Musica. Paesaggi sonori. Composizioni originali.
              Silenzio.</p>
            <p>Qui il linguaggio cambia. Non siamo più nel laboratorio:
              siamo dentro l’esperienza. Ogni meditazione nasce come un
              piccolo viaggio — una voce apre lo spazio, il suono lo
              accompagna, la musica cambia insieme alla pratica. E
              quando finisce, non deve essere rimasto altro che quello
              che ti serviva.</p>
          </div>
          <div className="mt-8">
            <EditorialCta to="/meditazioni" variant="solid" tone="dark">
              Scopri le Meditazioni →
            </EditorialCta>
          </div>
          <p className="mt-6 text-xs text-white/70">
            Le Meditazioni Aurya vengono pubblicate attraverso La Lettera.
          </p>
        </PhotoBand>

        {/* ── I DUE LINGUAGGI ── */}
        <Section tone="cream" labelledBy="sh-due">
          <DisplayTitle id="sh-due">Due modi diversi di lavorare con il suono.</DisplayTitle>
          <div className="mt-10 grid gap-8 md:grid-cols-2 max-w-4xl">
            <div className="border-l-2 border-[#c9b37e] pl-6">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-3">
                Esperienze sonore
              </p>
              <p className="font-serif text-xl mb-3">CALM, GROUND, RESPIRO.</p>
              <p className="text-sm leading-6 text-muted-foreground">
                Suono come fenomeno. Struttura, ritmo, frequenza,
                percezione.
              </p>
            </div>
            <div className="border-l-2 border-[#2f5749] pl-6">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-3">
                Meditazioni Aurya
              </p>
              <p className="font-serif text-xl mb-3">Voce, musica e paesaggio sonoro.</p>
              <p className="text-sm leading-6 text-muted-foreground">
                Suono come esperienza narrativa.
              </p>
            </div>
          </div>
          <p className="mt-10 max-w-2xl font-serif text-xl">
            Due linguaggi diversi. Lo stesso desiderio: creare esperienze
            che abbiano senso ascoltare.
          </p>
        </Section>

        {/* ── PROFESSIONAL ── */}
        <Section tone="sage" labelledBy="sh-pro" data-testid="sld-professional">
          <p className="text-[10px] tracking-[0.2em] uppercase opacity-70 mb-4">
            Ma il suono può diventare anche uno strumento professionale
          </p>
          <DisplayTitle id="sh-pro" className="text-[#f6f2e8]">
            Aurya Sound Professional
          </DisplayTitle>
          <div className="mt-6 max-w-2xl space-y-4 text-[15px] leading-7 opacity-90">
            <p>Se lavori con persone attraverso meditazione,
              respirazione, pratiche corporee o percorsi di benessere,
              probabilmente non hai bisogno di un altro software per
              creare musica. Hai bisogno di strumenti pronti per il tuo
              lavoro.</p>
            <p className="font-serif text-xl">Non devi progettare una
              frequenza. Devi scegliere un’esperienza.</p>
            <p>Aurya Sound Professional mette a disposizione una libreria
              di protocolli sonori strutturati, progettati per essere
              utilizzati durante le sessioni. Ogni protocollo ha una
              propria struttura: intento, durata, progressione, elementi
              sonori, basi di riferimento, indicazioni di conduzione.</p>
            <p>Tu scegli. Aurya fa il resto.</p>
          </div>

          <div className="mt-10 max-w-2xl border-t border-[#f6f2e8]/20 pt-8 space-y-4 text-[15px] leading-7 opacity-90">
            <p className="font-serif text-xl opacity-100">
              E il lavoro continua dopo l’ascolto.
            </p>
            <p>Una sessione non dovrebbe scomparire quando il suono
              finisce. Con Professional mantieni uno storico delle
              esperienze utilizzate con le persone che accompagni: quale
              protocollo, quale versione, quando, quanto è durato, le tue
              note.</p>
            <p>Non ricordare: registrare. Non improvvisare ogni volta:
              costruire un percorso.</p>
          </div>
          <div className="mt-9">
            <EditorialCta to="/sound/professional" variant="solid" tone="dark">
              Scopri Sound Professional →
            </EditorialCta>
          </div>
        </Section>

        {/* ── L'ONESTÀ ── */}
        <Section tone="paper" labelledBy="sh-evidenza">
          <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-4">
            Il nostro approccio parte da una cosa semplice
          </p>
          <DisplayTitle id="sh-evidenza">
            Non tutte le frequenze hanno la stessa evidenza.
          </DisplayTitle>
          <div className="mt-6 max-w-2xl space-y-4 text-[15px] leading-7 text-muted-foreground">
            <p>Il mondo del suono è pieno di affermazioni. Alcune hanno
              basi interessanti. Altre sono ancora oggetto di ricerca.
              Altre appartengono alla tradizione. Noi preferiamo
              distinguerle.</p>
            <p>Per questo Aurya Sound non promette che una determinata
              frequenza possa «guarire», «riparare» o agire su uno
              specifico organo.</p>
          </div>
          <div className="mt-8 max-w-2xl space-y-2 font-serif text-xl">
            <p>Raccontiamo quello che sappiamo.</p>
            <p>Distinguiamo quello che non sappiamo.</p>
            <p>E lasciamo spazio all’esperienza.</p>
          </div>
          <p className="mt-8 max-w-2xl text-[15px] leading-7 text-muted-foreground">
            È il nostro modo di costruire qualcosa che possa durare.
          </p>
        </Section>

        {/* ── IL PROCESSO ── */}
        <Section tone="sand" labelledBy="sh-processo">
          <DisplayTitle id="sh-processo">Dalla ricerca all’esperienza.</DisplayTitle>
          <Lede size="small" className="mt-4">Il processo è semplice.</Lede>
          <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
            {PASSI.map(([n, titolo, testo]) => (
              <li key={n}>
                <p className="font-mono text-xs text-[#c9b37e] mb-3">{n}</p>
                <h3 className="font-serif text-lg mb-2">{titolo}</h3>
                <p className="text-sm leading-6 text-muted-foreground">{testo}</p>
              </li>
            ))}
          </ol>
          <p className="mt-12 max-w-2xl font-serif text-xl">
            Il suono può essere affascinante senza diventare misterioso.
          </p>
        </Section>

        {/* ── IL FUTURO ── */}
        <PhotoBand image={MATERIA} focus="50% 50%" width="max-w-3xl"
          labelledBy="sh-futuro" data-testid="sh-futuro">
          <p className="text-[10px] tracking-[0.2em] uppercase text-white/70 mb-4">
            E questo è solo l’inizio
          </p>
          <DisplayTitle id="sh-futuro" className="text-white text-hero-shadow">
            Dal suono alla risposta.
          </DisplayTitle>
          <div className="mt-6 max-w-xl space-y-4 text-[15px] leading-7 text-white/90 text-hero-shadow">
            <p>Oggi Aurya Sound lavora principalmente sul suono. Ma
              stiamo costruendo qualcosa di più interessante.</p>
            <p>Il prossimo passo di Sound Professional è il biofeedback:
              non soltanto creare uno stimolo, ma poter osservare cosa
              succede durante una sessione. Respirazione. Variabilità.
              Segnali fisiologici. Risposta nel tempo.</p>
            <p>Il professionista al centro. Il suono come stimolo, i dati
              come osservazione, l’esperienza come percorso.</p>
          </div>
        </PhotoBand>

        {/* ── IL CONGEDO ── */}
        <Section tone="cream" labelledBy="sh-fine">
          <DisplayTitle id="sh-fine">Aurya Sound</DisplayTitle>
          <div className="mt-5 space-y-1 font-serif text-xl">
            <p>Esplora il suono.</p>
            <p>Ascoltalo.</p>
            <p>Impara a usarlo.</p>
          </div>
          <div className="mt-8">
            <EditorialCta to="/sound/esplora" variant="solid">
              Esplora gratuitamente →
            </EditorialCta>
          </div>

          <div className="mt-16 border-t border-[#e5ddcb] pt-10 max-w-2xl">
            <p className="font-serif text-xl mb-3">
              Se sei un professionista del benessere
            </p>
            <p className="text-[15px] leading-7 text-muted-foreground mb-6">
              Porta Aurya Sound nelle tue sessioni.
            </p>
            <EditorialCta to="/sound/professional" variant="quiet">
              Scopri Sound Professional →
            </EditorialCta>
          </div>

          <div className="mt-16 grid gap-8 sm:grid-cols-2 max-w-3xl text-sm">
            <div>
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-3">
                Aurya Sound
              </p>
              <p className="text-muted-foreground">
                <Link to="/sound/esplora" className="hover:text-foreground">Biblioteca</Link> ·{' '}
                <Link to="/sound/impara" className="hover:text-foreground">Impara</Link> ·{' '}
                <Link to="/sound/lab" className="hover:text-foreground">Lab</Link> ·{' '}
                <Link to="/sound/calm" className="hover:text-foreground">Esperienze</Link> ·{' '}
                <Link to="/meditazioni" className="hover:text-foreground">Meditazioni</Link>
              </p>
            </div>
            <div>
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-3">
                Aurya Sound Professional
              </p>
              <p className="text-muted-foreground">
                Protocolli · Sessioni · Percorsi · Storico · Biofeedback
              </p>
            </div>
          </div>

          <p className="mt-12 max-w-2xl text-xs leading-5 text-muted-foreground"
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
