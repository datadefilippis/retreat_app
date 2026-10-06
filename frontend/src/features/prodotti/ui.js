/**
 * ui.js — IL KIT del modulo Prodotti (DP, 6/10/2026 sera).
 *
 * Founder: «design olistico: moderno, stiloso, pulito, user-friendly,
 * ottimizzato multipiattaforma». Un solo posto per campi, bottoni,
 * schede, passi e anteprima: le quattro pagine del gestionale parlano la
 * stessa lingua visiva e un ritocco qui vale ovunque.
 *
 * Regole:
 *   - un colore d'azione (salvia #2f5749), uno di stato (smeraldo = online,
 *     ambra = cosa manca), tutto il resto e' grigio caldo;
 *   - tocco minimo 40px, campi alti (py-2.5), etichette sopra, suggerimenti
 *     sotto in grigio: niente placeholder che sparisce con il testo;
 *   - su telefono tutto a una colonna, bottoni a tutta larghezza;
 *   - il tipo (fisico/digitale) NON e' mai un'etichetta pubblica (founder):
 *     lo racconta l'operatore nella descrizione.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Copy, ExternalLink, FileDown, Loader2, Package } from 'lucide-react';
import { toast } from 'sonner';
import { fmtEuro } from '../../api/prodotti';

export const SALVIA = '#2f5749';

export const campo = 'w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-[15px] sm:text-sm text-gray-900 '
  + 'placeholder:text-gray-400 transition focus:border-[#2f5749] focus:outline-none focus:ring-4 focus:ring-[#2f5749]/10 '
  + 'disabled:bg-gray-50';

/** etichetta sopra, suggerimento sotto: un campo si legge prima di scriverci */
export function Campo({ label, hint, obbligatorio = false, children, className = '' }) {
  return (
    <div className={className}>
      <label className="mb-1.5 block text-[13px] font-medium text-gray-800">
        {label}{obbligatorio && <span className="ml-0.5 text-[#2f5749]">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-xs leading-snug text-gray-500">{hint}</p>}
    </div>
  );
}

export function Scheda({ title, sub, children, className = '', ...rest }) {
  return (
    <section
      className={`rounded-2xl border border-gray-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04)] sm:p-6 ${className}`}
      {...rest}>
      {title && (
        <div className="mb-4">
          <h2 className="text-[15px] font-semibold text-gray-900">{title}</h2>
          {sub && <p className="mt-0.5 text-sm text-gray-500">{sub}</p>}
        </div>
      )}
      {children}
    </section>
  );
}

const BASE_BTN = 'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold '
  + 'transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2f5749]/20 disabled:cursor-not-allowed disabled:opacity-50';

export function Bottone({ variante = 'primario', caricando = false, children, className = '', ...rest }) {
  const look = variante === 'primario'
    ? 'bg-[#2f5749] text-white hover:bg-[#27493d] shadow-[0_6px_16px_-8px_rgba(47,87,73,0.6)]'
    : variante === 'pericolo'
      ? 'text-gray-500 hover:text-red-700 px-2'
      : 'border border-gray-200 bg-white text-gray-800 hover:bg-gray-50';
  return (
    <button type="button" className={`${BASE_BTN} ${look} ${className}`} {...rest}>
      {caricando ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : children}
    </button>
  );
}

export function LinkBottone({ variante = 'secondario', children, className = '', ...rest }) {
  const look = variante === 'primario'
    ? 'bg-[#2f5749] text-white hover:bg-[#27493d]'
    : 'border border-gray-200 bg-white text-gray-800 hover:bg-gray-50';
  return <Link className={`${BASE_BTN} ${look} ${className}`} {...rest}>{children}</Link>;
}

/** la classe di un passo del wizard: fatto · corrente · da fare */
export function classePasso(i, corrente) {
  if (i < corrente) return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (i === corrente) return 'border-[#2f5749] bg-[#2f5749] text-white shadow-[0_6px_16px_-8px_rgba(47,87,73,0.6)]';
  return 'border-gray-200 bg-white text-gray-400';
}

export function Ragioni({ ragioni, testid }) {
  if (!ragioni?.length) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid={testid}>
      <p className="font-semibold">Prima di pubblicare</p>
      <ul className="mt-1.5 space-y-1 pl-4 list-disc">{ragioni.map(r => <li key={r}>{r}</li>)}</ul>
      <Link to="/settings" className="mt-2 inline-block text-xs font-medium underline">Vai alle impostazioni</Link>
    </div>
  );
}

/** la vignetta del prodotto: foto, o un segno discreto al suo posto */
export function Vignetta({ prodotto, className = '' }) {
  const Icona = prodotto?.item_type === 'digital' ? FileDown : Package;
  return (
    <div className={`overflow-hidden bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2] ${className}`}>
      {prodotto?.image_url
        ? <img src={prodotto.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />
        : <div className="flex h-full w-full items-center justify-center text-[#2f5749]/35"><Icona className="h-7 w-7" aria-hidden /></div>}
    </div>
  );
}

/** «Così lo vedranno»: la card pubblica, senza etichetta di tipo (founder) */
export function AnteprimaProdotto({ prodotto, riga, testid }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white" data-testid={testid}>
      <Vignetta prodotto={prodotto} className="aspect-[16/9] w-full" />
      <div className="p-4">
        <p className="font-semibold leading-snug text-gray-900">{prodotto.name}</p>
        {prodotto.description && <p className="mt-1 text-sm leading-relaxed text-gray-600 line-clamp-3">{prodotto.description}</p>}
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-lg font-bold text-[#2f5749]">{fmtEuro(prodotto.unit_price)}</span>
          <span className="rounded-full bg-[#2f5749] px-4 py-1.5 text-sm font-semibold text-white">Compra</span>
        </div>
        {riga && <p className="mt-2 text-xs text-gray-500">{riga}</p>}
      </div>
    </div>
  );
}

export function urlPagina(orgSlug, slug) {
  if (!orgSlug || !slug) return null;
  const origin = typeof window !== 'undefined' ? window.location.origin : 'https://aurya.life';
  return `${origin}/prodotto/${orgSlug}/${slug}`;
}

/** il link della pagina del prodotto, da copiare e condividere */
export function LinkPagina({ orgSlug, slug, online }) {
  const [copiato, setCopiato] = useState(false);
  const url = urlPagina(orgSlug, slug);
  if (!url) return null;
  const copia = async () => {
    try { await navigator.clipboard.writeText(url); setCopiato(true); toast.success('Link copiato.'); setTimeout(() => setCopiato(false), 2000); }
    catch { toast.error('Non sono riuscito a copiare: seleziona il link e copialo.'); }
  };
  return (
    <div data-testid="prodotto-link-pagina">
      <p className="text-[13px] font-medium text-gray-800">La pagina del prodotto</p>
      <p className="mt-0.5 text-xs text-gray-500">
        {online ? 'Condividila dove vuoi: chi la apre legge il racconto e compra da lì.' : 'Si apre quando il prodotto è online.'}
      </p>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
        <code className="min-w-0 flex-1 truncate rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">{url}</code>
        <div className="flex gap-2">
          <Bottone variante="secondario" onClick={copia} className="min-h-[38px] px-4">
            {copiato ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />} Copia
          </Bottone>
          {online && (
            <a href={url} target="_blank" rel="noreferrer"
               className={`${BASE_BTN} min-h-[38px] border border-gray-200 bg-white px-4 text-gray-800 hover:bg-gray-50`}>
              <ExternalLink className="h-4 w-4" aria-hidden /> Apri
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

/** il selettore della copertina: un'area da toccare, non un input grezzo */
export function SceltaImmagine({ file, onFile, attuale, label = 'Copertina', hint }) {
  const [anteprima, setAnteprima] = useState(null);
  const scegli = (f) => {
    onFile(f || null);
    if (anteprima) URL.revokeObjectURL(anteprima);
    setAnteprima(f ? URL.createObjectURL(f) : null);
  };
  const src = anteprima || attuale;
  return (
    <Campo label={label} hint={hint}>
      <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-gray-300 p-3 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03]">
        <div className="h-14 w-14 flex-none overflow-hidden rounded-lg bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2]">
          {src && <img src={src} alt="" className="h-full w-full object-cover" />}
        </div>
        <span className="min-w-0 text-sm text-gray-700">
          <span className="block font-medium">{file ? file.name : (attuale ? 'Cambia immagine' : 'Scegli un\'immagine')}</span>
          <span className="block text-xs text-gray-500">JPG o PNG, orizzontale viene meglio.</span>
        </span>
        <input type="file" accept="image/*" className="hidden" onChange={e => scegli(e.target.files?.[0])} />
      </label>
    </Campo>
  );
}
