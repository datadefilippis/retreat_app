/**
 * /sound — LA LANDING DI SISTEMA (L3-bis, 26/8/2026 sera).
 *
 * La visione del founder, alla lettera: UNA landing per tutta Aurya
 * Sound, coi colori e il design DEL SITO — il blu comincia solo
 * quando si entra davvero (biblioteca, esperienze, strumento). E
 * dev'essere STORYTELLING: lo scopo, le evidenze, le ispirazioni,
 * cosa c'è dentro — affascinare, non elencare.
 *
 * I MOVIMENTI (il kit editoriale di casa, come Chi siamo):
 *   APERTURA   il suono come materia, generato dal vivo
 *   MOV 1      perché esiste: contro il mercato delle promesse
 *   MOV 2      le basi: ASSR, entrainment, risonanza — nominate
 *   MOV 3      cosa trovi dentro: le quattro stanze (e l'avviso che
 *              di là la luce cambia)
 *   MOV 4      per chi accompagna: la via professionale (sage,
 *              l'ancora tonale del sito)
 *
 * La voce è quella C0: si può affascinare senza promettere — «il
 * registro basso si sente nel corpo» sì, «riequilibra» mai.
 */
import React, { useEffect } from 'react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import {
  DisplayTitle, EditorialCta, Lede, PillarCard, Section,
} from '../../components/editorial';

export default function SoundHomePage() {
  useEffect(() => {
    document.title = 'Aurya Sound — Il suono, spiegato e condotto | Aurya';
  }, []);

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background" data-testid="sound-home">

        {/* ── APERTURA ── */}
        <Section tone="cream" rhythm="hero" labelledBy="sh-title">
          <p className="text-xs tracking-[0.22em] uppercase text-muted-foreground mb-4">
            Aurya Sound
          </p>
          <DisplayTitle as="h1" id="sh-title" size="manifesto" measure="wide">
            Il suono, spiegato e condotto
          </DisplayTitle>
          <Lede className="mt-6 max-w-2xl">
            C’è un suono che non è una canzone e non è un sottofondo:
            un tono che sta, un battito che scivola, un registro basso
            che si sente prima nel corpo che nelle orecchie. Aurya
            Sound lo genera dal vivo, ogni volta — non file
            registrati, ma sintesi: la stessa esperienza respira
            sempre un po’ diversa, come una marea.
          </Lede>
        </Section>

        {/* ── MOV 1 · perché esiste ── */}
        <Section tone="paper" labelledBy="sh-perche">
          <DisplayTitle id="sh-perche">Perché esiste</DisplayTitle>
          <div className="mt-6 grid gap-8 md:grid-cols-2 max-w-4xl">
            <p className="text-[15px] leading-7 text-muted-foreground">
              Intorno al suono si promette di tutto: frequenze che
              «riparano», numeri magici, effetti garantiti. Aurya
              Sound nasce dal gesto opposto — un posto dove il suono
              si <em>spiega</em> prima di suonare: ogni scheda
              dichiara cosa sappiamo davvero, con quale grado di
              evidenza, e cosa resta tradizione.
            </p>
            <p className="text-[15px] leading-7 text-muted-foreground">
              È una scelta di rispetto — per chi ascolta e per chi
              accompagna. E, col tempo, è diventata la nostra firma:
              chi sa dove finisce la propria evidenza è chi la sta
              usando davvero.
            </p>
          </div>
        </Section>

        {/* ── MOV 2 · le basi ── */}
        <Section tone="sand" labelledBy="sh-basi">
          <DisplayTitle id="sh-basi">Le basi, nominate</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            Partiamo da un fatto misurabile: il cervello segue la
            stimolazione sonora ritmica — la risposta uditiva
            stazionaria (ASSR), neurofisiologia consolidata, usata
            perfino in audiologia clinica.
          </Lede>
          <div className="mt-8 grid gap-5 sm:grid-cols-3 max-w-4xl">
            <div>
              <h3 className="font-serif text-lg mb-2">Entrainment uditivo</h3>
              <p className="text-sm leading-6 text-muted-foreground">
                Battiti binaurali e toni isocronici: le review
                documentano effetti reali sul rilassamento e
                sull’ansia di stato — da piccoli a moderati, e lo
                scriviamo così.
              </p>
            </div>
            <div>
              <h3 className="font-serif text-lg mb-2">Respirazione di risonanza</h3>
              <p className="text-sm leading-6 text-muted-foreground">
                Sei atti al minuto, guidati dal suono: l’evidenza più
                forte di tutto questo campo, e la nostra direzione di
                sviluppo.
              </p>
            </div>
            <div>
              <h3 className="font-serif text-lg mb-2">Psicoacustica</h3>
              <p className="text-sm leading-6 text-muted-foreground">
                Il suono grave è percezione anche corporea: le nostre
                esperienze sono progettate e misurate al banco,
                frequenza per frequenza.
              </p>
            </div>
          </div>
        </Section>

        {/* ── MOV 3 · cosa trovi dentro ── */}
        <Section tone="paper" labelledBy="sh-dentro">
          <DisplayTitle id="sh-dentro">Cosa trovi, entrando</DisplayTitle>
          <Lede size="small" className="mt-4 max-w-2xl">
            Di là la luce cambia: il mondo del suono è blu e scuro,
            come una stanza d’ascolto. Quattro stanze, tutte aperte.
          </Lede>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <PillarCard
              title="La biblioteca"
              text="Trentotto schede su bande, frequenze e metodi: cosa sappiamo davvero, scheda per scheda."
              to="/sound/esplora"
              ctaLabel="Esplora, gratis"
              data-testid="sh-porta-esplora"
            />
            <PillarCard
              title="Le esperienze"
              text="CALM e GROUND: ascolti brevi e strutturati, da provare adesso, senza registrarsi."
              to="/sound/calm"
              ctaLabel="Ascolta CALM"
              data-testid="sh-porta-esperienze"
            />
            <PillarCard
              title="Il laboratorio"
              text="Il suono che si vede: genera un tono, osserva l’onda, misura lo spettro."
              to="/sound/lab"
              ctaLabel="Apri il Lab"
              data-testid="sh-porta-lab"
            />
            <PillarCard
              title="Le meditazioni"
              text="Sessioni complete composte con Aurya Sound. Si aprono con la Lettera, la nostra newsletter."
              to="/meditazioni"
              ctaLabel="Sfoglia"
              data-testid="sh-porta-meditazioni"
            />
          </div>
        </Section>

        {/* ── MOV 4 · per chi accompagna (l'ancora scura del sito) ── */}
        <Section tone="sage" labelledBy="sh-pro" data-testid="sld-professional">
          <p className="text-xs tracking-[0.22em] uppercase opacity-70 mb-4">
            Per i professionisti del benessere
          </p>
          <DisplayTitle id="sh-pro" className="text-[#f6f2e8]">
            L’ascolto guidato
          </DisplayTitle>
          <Lede size="small" tone="inverse" className="mt-4 max-w-2xl opacity-90">
            Aurya Sound Professional è lo strumento per condurre
            sessioni d’ascolto con i tuoi clienti: protocolli con basi
            dichiarate, percorsi con una cadenza, il registro di ogni
            sessione — «la volta scorsa: da 4 a 7» — e nessuna
            attrezzatura da comprare.
          </Lede>
          <div className="mt-8">
            <EditorialCta to="/sound/professional" variant="solid" tone="dark"
              data-testid="sld-pro-link">
              Scopri Professional
            </EditorialCta>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
