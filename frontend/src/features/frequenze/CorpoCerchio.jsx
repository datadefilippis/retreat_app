/**
 * IL CORPO DEL CERCHIO — le parole del cancello e le due porte per chi e'
 * gia' dentro, UGUALI su ogni soglia dell'ascolto (25/9/2026, founder:
 * «sto condividendo sui social il link delle meditazioni: per chi deve
 * iscriversi la pagina deve essere chiara, ad alto valore, e portare a
 * registrarsi senza esitazione, lasciandoci piu' dati possibili con
 * trasparenza»).
 *
 * Qui vive SOLO la presentazione:
 *   ValoreCerchio  — il testo del founder (titolo, cosa c'e' dentro, i
 *                    tre benefici) in due vestiti, scuro (mondo Sound) e
 *                    chiaro (landing);
 *   FiduciaCerchio — la riga sotto il bottone: gratis, un clic per uscire;
 *   PorteCerchio   — «Sei già nel Cerchio?» e «Hai un account Aurya?»,
 *                    due riquadri in evidenza invece di una riga grigia.
 * I form, i testid e il cervello (iscriviESblocca / sblocca) restano nei
 * cancelli che montano questi pezzi: CancelloLettera (traccia e landing)
 * e MeditazioniPage (la vetrina). Le guardie leggono i testid la'.
 */
import React from 'react';

export const TITOLO_CERCHIO = 'Entra nel Cerchio di Aurya';
export const CTA_ISCRIVITI = 'Iscriviti gratuitamente e inizia ad ascoltare';
export const BENEFICI = [
  'accesso alle nuove esperienze sonore di Aurya',
  'i ritiri e le esperienze in anteprima',
  'la Lettera di Aurya, con storie, pratiche e ispirazioni per coltivare il tuo benessere',
];
/* il secondo capoverso del founder: uguale sulla traccia e sulla vetrina
   (la guardia LX lo pretende anche in llms.txt, services/identita.py) */
export const COSA_ASCOLTI = 'L’iscrizione è gratuita e ti permette di ascoltare le esperienze '
  + 'di Aurya Sound pensate per accompagnare il sonno, la meditazione, il rilassamento '
  + 'e la concentrazione.';

/** Titolo e valore. `intro` e' la prima frase, che cambia con la soglia
 *  («Questa esperienza sonora…» sulla traccia, «Le esperienze sonore…»
 *  sulla vetrina). */
export function ValoreCerchio({ chiaro = false, intro, kicker = 'Il Cerchio di Aurya · gratis' }) {
  if (chiaro) {
    return (
      <div data-testid="cerchio-valore">
        <p className="mb-2 font-mono text-[10.5px] uppercase tracking-[.16em] text-[#8a7440]">{kicker}</p>
        <h2 className="mb-3 font-serif text-2xl sm:text-3xl">{TITOLO_CERCHIO}</h2>
        <p className="text-base text-foreground/90">{intro}</p>
        <p className="mt-2 text-base text-muted-foreground">{COSA_ASCOLTI}</p>
        <p className="mt-3 text-sm font-medium text-foreground/90">Entrando nel Cerchio ricevi anche:</p>
        <ul className="mt-1.5 space-y-1.5">
          {BENEFICI.map((b) => (
            <li key={b} className="flex gap-2.5 text-sm text-muted-foreground">
              <span aria-hidden="true" className="mt-px shrink-0 text-[#2f5749]">✦</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return (
    <div className="cerchio-valore" data-testid="cerchio-valore">
      <p className="cerchio-kicker">{kicker}</p>
      <h2>{TITOLO_CERCHIO}</h2>
      <p className="lead">{intro}</p>
      <p>{COSA_ASCOLTI}</p>
      <p className="cerchio-anche">Entrando nel Cerchio ricevi anche:</p>
      <ul className="cerchio-benefici">
        {BENEFICI.map((b) => <li key={b}>{b}</li>)}
      </ul>
    </div>
  );
}

/** La riga sotto il bottone: la promessa che toglie l'esitazione. */
export function FiduciaCerchio({ chiaro = false }) {
  const testo = 'Gratis, senza carta di credito. Ti cancelli con un clic, quando vuoi.';
  return chiaro
    ? <p className="mt-2 text-center text-xs text-muted-foreground">{testo}</p>
    : <p className="cerchio-fiducia">{testo}</p>;
}

/**
 * Le due porte di chi e' gia' dentro. Chi le monta passa gli ELEMENTI
 * (bottone «Sblocca», link «Accedi» e «Crealo gratis») perche' i testid
 * e i link con l'email restano nel file del cancello; qui solo la
 * cornice e, quando serve, il campo email per lo sblocco
 * (`chiediEmail`: il bottone e' stato premuto senza email nel form).
 */
export function PorteCerchio({
  chiaro = false, sblocca, chiediEmail = false, email = '', setEmail, onSblocca, invio = false,
  msgSblocco = '', accedi, crea,
}) {
  const formSblocco = (
    <form onSubmit={(e) => { e.preventDefault(); onSblocca && onSblocca(); }}
      className={chiaro ? 'mt-1 flex flex-wrap gap-2' : 'porta-form'}
      data-testid="porta-sblocco-form">
      <input type="email" required autoFocus value={email} placeholder="l’email con cui sei entrato"
        onChange={(e) => setEmail && setEmail(e.target.value)}
        className={chiaro ? 'min-w-0 flex-1 rounded-xl border border-[#d8cfba] bg-white px-4 py-2.5 text-sm' : undefined}
        data-testid="porta-sblocco-email" />
      <button type="submit" disabled={invio}
        className={chiaro ? 'rounded-full border border-[#2f5749] px-4 py-2 text-sm font-semibold text-[#2f5749]' : undefined}>
        {invio ? 'Un attimo…' : 'Sblocca'}
      </button>
    </form>
  );
  if (chiaro) {
    return (
      <div className="mt-6 grid gap-3 border-t border-[#e6dfcf] pt-5 sm:grid-cols-2" data-testid="cerchio-porte">
        <div className="rounded-2xl border border-[#d8cfba] bg-white/60 p-4" data-testid="porta-sblocco">
          <h3 className="font-serif text-lg">Sei già nel Cerchio?</h3>
          <p className="mb-2.5 text-xs text-muted-foreground">Ti basta l’email con cui sei entrato: nessuna nuova iscrizione.</p>
          {chiediEmail ? formSblocco : sblocca}
          {msgSblocco && <p className="mt-2 text-xs text-[#a03434]">{msgSblocco}</p>}
        </div>
        <div className="rounded-2xl border border-[#d8cfba] bg-white/60 p-4" data-testid="porta-account">
          <h3 className="font-serif text-lg">Hai un account Aurya?</h3>
          <p className="mb-2.5 text-xs text-muted-foreground">Con l’account sei già dentro: entra e ascolta.</p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
            {accedi}
            <span className="text-muted-foreground">· Non ce l’hai? {crea}</span>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="cerchio-porte" data-testid="cerchio-porte">
      <div className="porta-cerchio" data-testid="porta-sblocco">
        <h3>Sei già nel Cerchio?</h3>
        <p>Ti basta l’email con cui sei entrato: nessuna nuova iscrizione.</p>
        {chiediEmail ? formSblocco : sblocca}
        {msgSblocco && <p className="porta-errore">{msgSblocco}</p>}
      </div>
      <div className="porta-cerchio" data-testid="porta-account">
        <h3>Hai un account Aurya?</h3>
        <p>Con l’account sei già dentro: entra e ascolta.</p>
        <div className="porta-azioni">
          {accedi}
          <span>· Non ce l’hai? {crea}</span>
        </div>
      </div>
    </div>
  );
}
