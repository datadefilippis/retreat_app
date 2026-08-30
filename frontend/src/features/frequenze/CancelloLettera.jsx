/**
 * IL CANCELLO DELLA LETTERA — un solo cancello, due mondi (FN2, 30/8).
 *
 * Nato dal test del founder: il cancello di /frequenze parlava in
 * gergo interno («l'ascolto completo è di chi riceve la Lettera») a
 * visitatori che non sanno cosa sia la Lettera. Qui il copy dice le
 * cose in chiaro — cosa ottieni (la meditazione completa), cosa
 * costa (l'iscrizione gratuita alla newsletter) — e il brand («la
 * Lettera») è un'apposizione, mai una premessa.
 *
 * E' UN componente per TUTTI i cancelli dell'ascolto: la pagina
 * traccia (variante 'scuro', dentro il suo overlay fqz) e la landing
 * (variante 'chiaro', dentro la card dell'anteprima — FN3:
 * l'iscrizione si fa sul posto, senza cambiare pagina). La meccanica
 * e' il cerchio (SB): iscriviESblocca → 'sbloccato' subito se gia'
 * confermato, altrimenti double opt-in con ritorno.
 */
import React, { useState } from 'react';
import { sblocca, iscriviESblocca } from '../../lib/cerchio';
import { creaAccount, entraInAurya } from '../../utils/authLinks';

const fmtMin = (s) => `${Math.round((s || 0) / 60)} minuti`;

export default function CancelloLettera({
  slug, returnTo, durataSec = 0, variante = 'scuro',
  onSbloccato, children,
}) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [invio, setInvio] = useState(false);
  const [attesa, setAttesa] = useState(false);
  const [msg, setMsg] = useState('');
  const chiaro = variante === 'chiaro';
  const dove = returnTo || (slug ? `/frequenze/${slug}` : '/meditazioni');

  const iscrivi = async (e) => {
    e.preventDefault();
    if (!consent) { setMsg('Serve il consenso alla newsletter'); return; }
    setInvio(true); setMsg('');
    try {
      const esito = await iscriviESblocca({
        email, source: `cancello:${slug || 'landing'}`, returnTo: dove,
      });
      if (esito === 'sbloccato') { onSbloccato && onSbloccato(); }
      else setAttesa(true);
    } catch (err) {
      setMsg(err?.response?.data?.detail || 'Iscrizione non riuscita, riprova');
    } finally { setInvio(false); }
  };

  const giaIscritto = async () => {
    if (!email) { setMsg('Scrivi la tua email qui sopra e ripremi'); return; }
    setInvio(true); setMsg('');
    try { await sblocca(email); onSbloccato && onSbloccato(); }
    catch (err) {
      setMsg(err?.response?.data?.detail || 'Email non riconosciuta');
    } finally { setInvio(false); }
  };

  /* i vestiti dei due mondi: la sostanza non cambia */
  const S = chiaro ? {
    titolo: 'font-serif text-2xl sm:text-3xl mb-3',
    corpo: 'text-base text-muted-foreground',
    input: 'flex-1 min-w-[200px] rounded-xl border border-[#d8cfba] bg-white px-5 py-3.5 text-base',
    bottone: 'inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-base font-medium transition hover:opacity-90 disabled:opacity-50',
    nota: 'text-sm text-muted-foreground',
    warn: 'mt-4 rounded-xl border border-[#c9b37e] bg-[#faf6ec] px-5 py-4 text-sm',
    err: 'mt-3 text-sm text-[#a03434]',
  } : null;

  return (
    <div data-testid="cancello-lettera">
      <h2 className={chiaro ? S.titolo : undefined}>
        La meditazione completa è riservata agli iscritti.
      </h2>
      <p className={chiaro ? S.corpo : undefined}>
        {durataSec > 120 && <>Sono {fmtMin(durataSec)} in tutto. </>}
        L&rsquo;iscrizione alla newsletter di Aurya — la Lettera — è
        <b> gratuita</b>: pratiche, esperienze e nuove meditazioni,
        ogni tanto. Ti sblocchi una volta e ascolti tutto.
      </p>
      {attesa && (
        <div className={chiaro ? S.warn : 'warnbox'}
          style={chiaro ? undefined : { margin: '12px 0', textAlign: 'left' }}
          data-testid="cancello-attesa">
          Ti abbiamo scritto: apri l&rsquo;email e clicca il link di
          conferma. Ti riporta qui, con la meditazione intera sbloccata.
        </div>
      )}
      <form onSubmit={iscrivi} className={chiaro ? 'mt-5' : undefined}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input type="email" required value={email}
            placeholder="la tua email"
            onChange={(e) => setEmail(e.target.value)}
            className={chiaro ? S.input : undefined}
            style={chiaro ? undefined : { flex: 1, minWidth: 200 }} />
          <button type="submit" disabled={invio}
            className={chiaro ? S.bottone : 'primary'}
            style={chiaro ? { background: '#14212b', color: '#f6f2e8' } : undefined}
            data-testid="cancello-iscriviti">
            {invio ? 'Un attimo…' : 'Iscriviti e continua l’ascolto →'}
          </button>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start',
                        fontSize: 12, marginTop: 10, cursor: 'pointer' }}
          className={chiaro ? 'text-muted-foreground' : undefined}>
          <input type="checkbox" checked={consent}
            onChange={(e) => setConsent(e.target.checked)} />
          <span>Acconsento a ricevere la newsletter (la Lettera di
            Aurya). Confermerai dall&rsquo;email che ti arriva;
            disiscrizione in un click.
            {' '}<a href="/privacy" target="_blank" rel="noreferrer"
              style={chiaro ? undefined : { color: 'var(--water)' }}
              className={chiaro ? 'underline' : undefined}>Privacy</a></span>
        </label>
      </form>
      {msg && (
        <p className={chiaro ? S.err : undefined}
          style={chiaro ? undefined : { color: 'var(--alert)', fontSize: 12, marginTop: 8 }}>
          {msg}
        </p>
      )}
      <p className={chiaro ? 'mt-4 text-sm text-muted-foreground' : undefined}
        style={chiaro ? undefined : { fontSize: 12.5, color: 'var(--dim)', marginTop: 14 }}>
        Sei già iscritto?{' '}
        <button type="button" data-testid="cancello-gia-iscritto"
          className={chiaro ? 'underline' : 'readmore'}
          style={chiaro ? undefined : { display: 'inline' }}
          onClick={giaIscritto}>Sblocca con la tua email</button>
        {' '}· hai un account Aurya?{' '}
        <a href={entraInAurya(email, dove)} data-testid="cancello-accedi"
          className={chiaro ? 'underline' : undefined}
          style={chiaro ? undefined : { color: 'var(--water)' }}>Accedi</a>
        {' '}· <a href={creaAccount(email, dove)} data-testid="cancello-crea"
          className={chiaro ? 'underline' : undefined}
          style={chiaro ? undefined : { color: 'var(--water)' }}>Crealo gratis</a>
      </p>
      {children}
    </div>
  );
}
