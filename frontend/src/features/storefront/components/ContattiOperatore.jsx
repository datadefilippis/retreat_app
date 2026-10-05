/**
 * ContattiOperatore — i recapiti dell'operatore dietro la porta (R2, 25/9/2026).
 *
 * Piano docs/ANALISI_REGISTRAZIONE_OBBLIGATORIA_2026-09-25.md, lotto R2.
 * Il profilo JSON, con l'interruttore CONTATTI_DIETRO_PORTA acceso, dice
 * solo COSA c'e' (`contacts.porta` + has_phone/has_email/has_instagram/
 * has_facebook/has_website): i valori arrivano da
 * GET /public/operator/{slug}/contatti, che vuole il Bearer dell'account
 * Aurya e registra la richiesta per l'operatore (il lead).
 *
 * Con sessione aperta (cliente, operatore o regia): chiama e mostra.
 * Senza: spiega e monta PortaAurya (entra o crea con password). La
 * comunicazione all'operatore di chi ha chiesto sta nell'Informativa
 * (7-ter); il founder (26/9) non la vuole scritta nel riquadro. Con l'interruttore spento
 * (`contacts.porta` assente) rende ESATTAMENTE i blocchi di ieri: telefono
 * in chiaro, email al clic (MostraEmail), social in chiaro.
 *
 * Due varianti di vestito: 'profilo' (/o/, lista dl) e 'store' (riga).
 */
import React, { useEffect, useState } from 'react';
import { Esito } from '../../../lib/esito';   // FL1: il risultato si vede dove hai cliccato
import { useTranslation } from 'react-i18next';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';
import api from '../../../api/client';
import PortaAurya from '../../account/PortaAurya';
import MostraEmail from './MostraEmail';
import { datiTracciamento, metaContact } from '../../../lib/meta';   // MP2: Contact a Meta

const extUrl = (u) => (u && !u.startsWith('http') ? `https://${u}` : u);
/* 26/9 (founder): qualunque sessione aperta basta — cliente (platform_token)
   o gestionale (token: operatore e regia). Il client giusto porta il suo Bearer. */
const sessione = () => {
  try {
    if (localStorage.getItem(PLATFORM_TOKEN_KEY)) return 'cliente';
    if (localStorage.getItem('token')) return 'gestionale';
  } catch { /* private mode */ }
  return null;
};

/** true se c'e' qualcosa da mostrare (chi monta decide se aprire il riquadro) */
export function haContatti(data) {
  const c = data?.contacts || {};
  const s = data?.socials || {};
  if (c.porta) return !!(c.has_phone || c.has_email || c.has_instagram || c.has_facebook || c.has_website);
  return !!(c.public_phone || c.has_email || s.instagram || s.website || s.facebook);
}

function Recapiti({ valori, variante, t }) {
  const riga = variante === 'store';
  const link = riga ? 'text-primary hover:underline' : 'text-primary hover:underline break-all';
  return (
    <Esito className={riga ? 'flex flex-wrap items-center gap-x-4 gap-y-2 text-sm' : 'space-y-2 text-sm'} data-testid="contatti-aperti">
      {valori.public_phone && (
        <div className="flex items-start gap-2"><span aria-hidden>📞</span>
          <a href={`tel:${valori.public_phone}`} className="text-gray-700 hover:underline">{valori.public_phone}</a></div>
      )}
      {valori.public_email && (
        <div className="flex items-start gap-2"><span aria-hidden>✉️</span>
          <a href={`mailto:${valori.public_email}`} className={link}>{valori.public_email}</a></div>
      )}
      {(valori.instagram || valori.website || valori.facebook) && (
        <div className={riga ? 'contents' : 'flex flex-wrap gap-3 pt-2'}>
          {valori.instagram && <a href={extUrl(valori.instagram)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Instagram</a>}
          {valori.website && <a href={extUrl(valori.website)} target="_blank" rel="noreferrer" className="text-primary hover:underline">{t('landings:operator.website', { defaultValue: 'Sito web' })}</a>}
          {valori.facebook && <a href={extUrl(valori.facebook)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Facebook</a>}
        </div>
      )}
    </Esito>
  );
}

export default function ContattiOperatore({ slug, data, variante = 'profilo' }) {
  const { t } = useTranslation();
  const c = data?.contacts || {};
  const s = data?.socials || {};
  const [valori, setValori] = useState(null);
  // porta (nessuna sessione, o sessione scaduta) | carico | aperto | errore
  const [stato, setStato] = useState(() => (sessione() ? 'carico' : 'porta'));

  const apri = async () => {
    setStato('carico');
    try {
      const client = sessione() === 'gestionale' ? api : platformApi;
      // MP2 — col consenso marketing il server riceve lo stesso event_id (e i
      // cookie _fbp/_fbc) per mandare il Contact alla Conversions API una volta sola
      const tr = datiTracciamento('contact');
      const params = tr.marketing ? { ev: tr.event_id, ...(tr.fbp ? { fbp: tr.fbp } : {}), ...(tr.fbc ? { fbc: tr.fbc } : {}) } : {};
      const r = await client.get(`/public/operator/${slug}/contatti`, { params });
      setValori(r.data || {}); setStato('aperto');
      if (r.data?.registrato) metaContact({ eventID: tr.event_id, slug });   // solo quando e' una richiesta vera
    } catch (err) {
      if (err?.response?.status === 401) { setStato('porta'); return; }   // sessione scaduta: torna la porta
      setStato('errore');
    }
  };
  useEffect(() => { if (c.porta && sessione()) apri(); }, [slug]);   // eslint-disable-line react-hooks/exhaustive-deps

  /* ── interruttore spento: i blocchi di ieri, identici ── */
  if (!c.porta) {
    if (variante === 'store') {
      return (
        <>
          {s.instagram && <a href={extUrl(s.instagram)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Instagram</a>}
          {s.website && <a href={extUrl(s.website)} target="_blank" rel="noreferrer" className="text-primary hover:underline">{t('landings:operator.website', { defaultValue: 'Sito web' })}</a>}
          {s.facebook && <a href={extUrl(s.facebook)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Facebook</a>}
          {c.has_email && <MostraEmail slug={slug} className="text-gray-600" />}
          {c.public_phone && <span className="text-gray-600">{c.public_phone}</span>}
        </>
      );
    }
    return (
      <>
        <dl className="space-y-2 text-sm">
          {c.has_email && (<div className="flex items-start gap-2"><span aria-hidden>✉️</span><MostraEmail slug={slug} /></div>)}
          {c.public_phone && (<div className="flex items-start gap-2"><span aria-hidden>📞</span><span className="text-gray-700">{c.public_phone}</span></div>)}
        </dl>
        {(s.instagram || s.website || s.facebook) && (
          <div className="mt-4 pt-3 border-t border-border flex flex-wrap gap-3 text-sm">
            {s.instagram && <a href={extUrl(s.instagram)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Instagram</a>}
            {s.website && <a href={extUrl(s.website)} target="_blank" rel="noreferrer" className="text-primary hover:underline">{t('landings:operator.website', { defaultValue: 'Sito web' })}</a>}
            {s.facebook && <a href={extUrl(s.facebook)} target="_blank" rel="noreferrer" className="text-primary hover:underline">Facebook</a>}
          </div>
        )}
      </>
    );
  }

  /* ── interruttore acceso: dietro la porta ── */
  if (stato === 'aperto' && valori) return <Recapiti valori={valori} variante={variante} t={t} />;
  if (stato === 'carico') return <p className="text-sm text-muted-foreground" data-testid="contatti-carico">{t('landings:operator.contattiCarico', { defaultValue: 'Un attimo…' })}</p>;
  if (stato === 'errore') return <p className="text-sm text-muted-foreground" data-testid="contatti-errore">{t('landings:operator.contattiErrore', { defaultValue: 'Contatti non disponibili ora, riprova tra poco.' })}</p>;

  const cosa = [
    c.has_phone && t('landings:operator.contattiTelefono', { defaultValue: 'telefono' }),
    c.has_email && t('landings:operator.contattiEmail', { defaultValue: 'email' }),
    c.has_instagram && 'Instagram',
    c.has_facebook && 'Facebook',
    c.has_website && t('landings:operator.contattiSito', { defaultValue: 'sito' }),
  ].filter(Boolean).join(', ');
  return (
    <div className="space-y-3" data-testid="contatti-porta">
      <p className="text-sm text-gray-700">
        {t('landings:operator.contattiPorta', {
          defaultValue: 'Per vedere {{cosa}} entra con il tuo account Aurya, o crealo in un minuto.', cosa,
        })}
      </p>
      <PortaAurya contesto="contatti" onDentro={() => apri()} />
    </div>
  );
}
