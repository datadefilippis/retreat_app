/**
 * IL CANCELLO DELLA LETTERA — un solo cancello, due mondi (FN2, 30/8).
 *
 * Nato dal test del founder: il cancello di /frequenze parlava in
 * gergo interno («l'ascolto completo è di chi riceve la Lettera») a
 * visitatori che non sanno cosa sia la Lettera. Qui il copy dice le
 * cose in chiaro — cosa ottieni (la meditazione completa), cosa
 * costa (l'iscrizione gratuita al Cerchio) — e il brand («la
 * Lettera») è un'apposizione, mai una premessa.
 *
 * 25/9/2026 (founder, link delle meditazioni condiviso sui social): il
 * cancello diventa una pagina di valore. Il testo e' del founder
 * («Entra nel Cerchio di Aurya… Iscriviti gratuitamente e inizia ad
 * ascoltare»), le due strade di chi e' gia' dentro — «Sei già nel
 * Cerchio? Sblocca con la tua email» e «Hai un account Aurya?» — sono
 * due riquadri in evidenza, non una riga grigia in fondo. Parole e porte
 * vivono in CorpoCerchio.jsx, uguali sulla vetrina /meditazioni.
 *
 * E' UN componente per TUTTI i cancelli dell'ascolto: la pagina
 * traccia (variante 'scuro', dentro il suo overlay fqz) e la landing
 * (variante 'chiaro', dentro la card dell'anteprima — FN3:
 * l'iscrizione si fa sul posto, senza cambiare pagina). La meccanica
 * e' il cerchio (SB): iscriviESblocca → 'sbloccato' subito se gia'
 * confermato, altrimenti double opt-in con ritorno.
 */
import React, { useState } from 'react';
import { sblocca, iscriviESblocca, testoAttesa } from '../../lib/cerchio';
import { testoConsenso } from '../../lib/testiConsenso';
import { creaAccount, entraInAurya } from '../../utils/authLinks';
import AvvisamiRitiri, { useAvvisamiRitiri } from '../prelaunch/AvvisamiRitiri';
import { ValoreCerchio, FiduciaCerchio, PorteCerchio, CTA_ISCRIVITI } from './CorpoCerchio';

/* US (10/9/2026 notte, founder: «nella newsletter delle meditazioni non
   mettiamo opzioni di ritiri?»): anche il cancello chiede, con LO STESSO
   blocco di /cerca-ritiro. Spento di default: chi vuole solo la
   meditazione lascia solo l'email (FV5). L'oro di casa sullo scuro. */
const ORO = '#d6c49a';

const fmtMin = (s) => `${Math.round((s || 0) / 60)} minuti`;

export default function CancelloLettera({
  slug, returnTo, durataSec = 0, variante = 'scuro',
  onSbloccato, children,
}) {
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [consent, setConsent] = useState(false);
  const [invio, setInvio] = useState(false);
  const [attesa, setAttesa] = useState(false);
  const [msg, setMsg] = useState('');
  const [msgPorta, setMsgPorta] = useState('');
  const [chiediEmail, setChiediEmail] = useState(false);
  const chiaro = variante === 'chiaro';
  const dove = returnTo || (slug ? `/frequenze/${slug}` : '/meditazioni');
  const avvisami = useAvvisamiRitiri(false);

  const iscrivi = async (e) => {
    e.preventDefault();
    if (!consent) { setMsg('Serve il consenso alle email del Cerchio: spunta la casella qui sopra.'); return; }
    setInvio(true); setMsg('');
    try {
      const esito = await iscriviESblocca({
        email, source: `cancello:${slug || 'landing'}`, returnTo: dove,
        name: nome.trim() || undefined, ritiri: avvisami.payload(),
      });
      if (esito === 'sbloccato') { onSbloccato && onSbloccato(); }
      else setAttesa(true);
    } catch (err) {
      setMsg(err?.response?.data?.detail || 'Iscrizione non riuscita, riprova');
    } finally { setInvio(false); }
  };

  /* la porta di chi e' gia' dentro: se l'email non e' ancora scritta il
     riquadro apre il suo campo (niente «scrivila qui sopra e ripremi») */
  const giaIscritto = async () => {
    if (!email) { setChiediEmail(true); return; }
    setInvio(true); setMsgPorta('');
    try { await sblocca(email); onSbloccato && onSbloccato(); }
    catch (err) {
      setMsgPorta(err?.response?.data?.detail
        || 'Non troviamo questa email nel Cerchio: controlla o iscriviti qui sopra.');
    } finally { setInvio(false); }
  };

  /* i vestiti dei due mondi: la sostanza non cambia */
  const S = chiaro ? {
    input: 'w-full rounded-xl border border-[#d8cfba] bg-white px-5 py-3.5 text-base',
    bottone: 'mt-3 inline-flex w-full items-center justify-center gap-2 rounded-full px-7 py-3.5 text-base font-medium transition hover:opacity-90 disabled:opacity-50',
    warn: 'mt-4 rounded-xl border border-[#c9b37e] bg-[#faf6ec] px-5 py-4 text-sm',
    err: 'mt-3 text-sm text-[#a03434]',
    link: 'font-semibold text-[#2f5749] underline underline-offset-2',
    porta: 'rounded-full border border-[#2f5749] px-4 py-2 text-sm font-semibold text-[#2f5749] transition hover:bg-[#2f5749]/5',
  } : null;

  return (
    <div data-testid="cancello-lettera">
      {/* CN3 (3/9/2026, piano IL CERCHIO): il cancello parla di
          appartenenza, non di newsletter — «Il Cerchio» e' il nome, «la
          Lettera» una delle cose che ricevi. Dal 25/9 il testo e' del
          founder e sta in CorpoCerchio. */}
      <ValoreCerchio chiaro={chiaro}
        intro={<>Questa esperienza sonora è disponibile per intero all’interno del Cerchio di Aurya.
          {durataSec > 120 && <> Sono {fmtMin(durataSec)} in tutto.</>}</>} />
      {attesa && (
        <div className={chiaro ? S.warn : 'warnbox'}
          style={chiaro ? undefined : { margin: '14px 0 0', textAlign: 'left' }}
          data-testid="cancello-attesa">
          {/* SO (3/10): la riga dice cosa e' partito davvero (benvenuto o conferma) */}
          {testoAttesa('con la meditazione intera sbloccata')}
        </div>
      )}
      <form onSubmit={iscrivi} className={chiaro ? 'mt-5' : 'cerchio-form'}>
        {/* US: il nome sopra l'email, facoltativo, come in ogni form del Cerchio */}
        <input type="text" value={nome} maxLength={80}
          placeholder="il tuo nome (facoltativo)"
          onChange={(e) => setNome(e.target.value)}
          className={chiaro ? `${S.input} mb-2` : undefined}
          data-testid="cancello-nome" />
        <input type="email" required value={email}
          placeholder="la tua email"
          onChange={(e) => setEmail(e.target.value)}
          className={chiaro ? S.input : undefined}
          data-testid="cancello-email" />
        <div style={{ marginTop: 10 }}>
          <AvvisamiRitiri {...avvisami} accent={chiaro ? '#2f5749' : ORO} scuro={!chiaro}
                          testid="cancello-avvisami" />
        </div>
        {/* US (founder: «il flag di accettazione e' piccolissimo»): casella
            18px nell'oro di casa, testo 13px leggibile sullo scuro */}
        <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', lineHeight: 1.45,
                        fontSize: 13, marginTop: 12, cursor: 'pointer', textAlign: 'left',
                        color: chiaro ? undefined : 'var(--bone)' }}
          className={chiaro ? 'text-muted-foreground' : undefined}>
          <input type="checkbox" checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            style={{ width: 18, height: 18, flex: 'none', marginTop: 1, accentColor: chiaro ? '#2f5749' : ORO }}
            data-testid="cancello-consenso" />
          {/* Lotto D (24/9/2026): il testo della casella e' UNO su tutte
              le porte, versionato in lib/testiConsenso.js */}
          <span>{testoConsenso().testo}
            {' '}<a href="/privacy" target="_blank" rel="noreferrer"
              style={chiaro ? undefined : { color: 'var(--water)' }}
              className={chiaro ? 'underline' : undefined}>Privacy</a></span>
        </label>
        {msg && (
          <p className={chiaro ? S.err : undefined}
            style={chiaro ? undefined : { color: 'var(--alert)', fontSize: 12.5, marginTop: 8 }}>
            {msg}
          </p>
        )}
        <button type="submit" disabled={invio}
          className={chiaro ? S.bottone : 'primary cerchio-cta'}
          style={chiaro ? { background: '#14212b', color: '#f6f2e8' } : undefined}
          data-testid="cancello-iscriviti">
          {invio ? 'Un attimo…' : `${CTA_ISCRIVITI} →`}
        </button>
        <FiduciaCerchio chiaro={chiaro} />
      </form>
      <PorteCerchio chiaro={chiaro}
        chiediEmail={chiediEmail} email={email} setEmail={setEmail}
        onSblocca={giaIscritto} invio={invio} msgSblocco={msgPorta}
        sblocca={(
          <button type="button" data-testid="cancello-gia-iscritto"
            className={chiaro ? S.porta : 'porta-azione'}
            onClick={giaIscritto}>Sblocca con la tua email</button>
        )}
        accedi={(
          <a href={entraInAurya(email, dove)} data-testid="cancello-accedi"
            className={chiaro ? S.porta : 'porta-azione'}>Accedi</a>
        )}
        crea={(
          <a href={creaAccount(email, dove)} data-testid="cancello-crea"
            className={chiaro ? S.link : 'porta-secondaria'}>Crealo gratis</a>
        )} />
      {children}
    </div>
  );
}
