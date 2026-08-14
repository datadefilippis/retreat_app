/**
 * LinkPageCard — l'editor della pagina link (LK3, 14/8/2026).
 *
 * Vive dentro Profilo pubblico. Il percorso dell'operatore e' TRE
 * gesti: attiva → copia → incolla nella bio di Instagram. Tutto il
 * resto e' opzionale e si salva DA SOLO a ogni tocco (niente bottone
 * Salva da ricordare: il PATCH parte subito e il server risponde con
 * lo stato normalizzato, id dei link compresi).
 *
 * I blocchi vivi sono accesi di default: la pagina e' piena senza
 * configurare nulla. I link personalizzati chiedono solo etichetta e
 * indirizzo (https). L'anteprima e' la pagina VERA in una cornice
 * telefono: quello che vedi e' quello che vede chi clicca.
 */
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link2, Copy, ExternalLink, ArrowUp, ArrowDown, X, Loader2, Check } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Switch } from '../../components/ui/switch';
import api from '../../api/client';

/* Le stesse 4 atmosfere della pagina pubblica, in miniatura. */
const THEME_SWATCHES = [
  { key: 'salvia', dot: 'bg-[#8a9979]', label: 'Salvia' },
  { key: 'terra', dot: 'bg-gradient-to-br from-[#f2ddc9] to-[#c98d5f]', label: 'Terra' },
  { key: 'notte', dot: 'bg-[#181c19]', label: 'Notte' },
  { key: 'carta', dot: 'bg-white border-2 border-stone-900', label: 'Carta' },
];

const BLOCK_LABELS = [
  ['upcoming', 'Il prossimo ritiro'],
  ['listino', 'Prenota una seduta'],
  ['whatsapp', 'WhatsApp'],
  ['socials', 'I tuoi social'],
  ['profile', 'Scopri chi sono'],
];

export default function LinkPageCard({ slug, initial }) {
  const { t } = useTranslation('settings');
  const [lp, setLp] = useState(initial || {
    enabled: false, theme: 'salvia', links: [],
    blocks: { upcoming: true, listino: true, profile: true, whatsapp: true, socials: true },
  });
  const [saving, setSaving] = useState(false);
  const [rev, setRev] = useState(0);           // ricarica l'anteprima
  const [newLabel, setNewLabel] = useState('');
  const [newUrl, setNewUrl] = useState('');

  const pageUrl = useMemo(
    () => (slug ? `${window.location.origin}/@${slug}` : null), [slug]);

  const persist = async (next) => {
    setLp(next);                                // ottimista: UI subito
    setSaving(true);
    try {
      const res = await api.patch('/organizations/current/public-profile',
        { link_page: next });
      // lo stato NORMALIZZATO dal server (id assegnati, tetti applicati)
      if (res.data?.link_page) setLp(res.data.link_page);
      setRev(r => r + 1);
    } catch {
      toast.error(t('linkPage.saveError', { defaultValue: 'Salvataggio non riuscito, riprova.' }));
    } finally {
      setSaving(false);
    }
  };

  const setBlock = (key, val) =>
    persist({ ...lp, blocks: { ...lp.blocks, [key]: val } });

  const addLink = () => {
    const label = newLabel.trim();
    let url = newUrl.trim();
    if (url && !/^https?:\/\//i.test(url)) url = `https://${url}`;
    if (!label || !url.startsWith('https://')) {
      toast.error(t('linkPage.addInvalid', {
        defaultValue: 'Serve un nome e un indirizzo che inizia con https://' }));
      return;
    }
    persist({ ...lp, links: [...(lp.links || []), { label, url, active: true }] });
    setNewLabel(''); setNewUrl('');
  };

  const removeLink = (id) =>
    persist({ ...lp, links: (lp.links || []).filter(l => l.id !== id) });

  const moveLink = (id, dir) => {
    const links = [...(lp.links || [])];
    const i = links.findIndex(l => l.id === id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= links.length) return;
    [links[i], links[j]] = [links[j], links[i]];
    persist({ ...lp, links });
  };

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(pageUrl);
      toast.success(t('linkPage.copied', { defaultValue: 'Link copiato: incollalo nella bio di Instagram.' }));
    } catch {
      toast.error(t('linkPage.copyError', { defaultValue: 'Copia non riuscita.' }));
    }
  };

  return (
    <div className="rounded-2xl border bg-white shadow-sm lg:col-span-2" data-testid="linkpage-card">
      <div className="flex items-start justify-between gap-4 px-5 pt-5">
        <div>
          <h3 className="flex items-center gap-2 font-bold text-gray-900">
            <Link2 className="h-4 w-4 text-primary" aria-hidden />
            {t('linkPage.title', { defaultValue: 'La tua pagina link' })}
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('linkPage.subtitle', { defaultValue: 'Un solo link per la bio di Instagram: dentro ci sono il tuo prossimo ritiro, il listino e i link che vuoi tu.' })}
          </p>
        </div>
        <Switch checked={!!lp.enabled} disabled={!slug}
                onCheckedChange={(v) => persist({ ...lp, enabled: v })}
                data-testid="linkpage-toggle" aria-label="Attiva la pagina link" />
      </div>

      {!slug && (
        <p className="px-5 pb-5 pt-3 text-sm text-muted-foreground">
          {t('linkPage.needProfile', { defaultValue: 'Salva prima il profilo: il tuo indirizzo pubblico nasce da lì.' })}
        </p>
      )}

      {slug && !lp.enabled && (
        <p className="px-5 pb-5 pt-3 text-sm text-muted-foreground">
          {t('linkPage.offHint', { defaultValue: 'Attivala e ottieni subito il link da mettere in bio: la pagina si riempie da sola con quello che hai già configurato.' })}
        </p>
      )}

      {slug && lp.enabled && (
        <div className="grid gap-6 px-5 pb-5 pt-4 lg:grid-cols-[1fr_260px]">
          <div className="space-y-6">

            {/* ── Il link, in grande: e' il prodotto ──────────────── */}
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4"
                 data-testid="linkpage-url">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {t('linkPage.yourUrl', { defaultValue: 'Il tuo link' })}
              </p>
              <p className="mt-1 break-all font-mono text-sm font-semibold text-foreground">
                {pageUrl.replace(/^https?:\/\//, '')}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" onClick={copyUrl} data-testid="linkpage-copy">
                  <Copy className="mr-1.5 h-3.5 w-3.5" />
                  {t('linkPage.copy', { defaultValue: 'Copia' })}
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <a href={`https://wa.me/?text=${encodeURIComponent(pageUrl)}`}
                     target="_blank" rel="noopener noreferrer">
                    {t('linkPage.share', { defaultValue: 'Condividi su WhatsApp' })}
                  </a>
                </Button>
                <Button size="sm" variant="ghost" asChild>
                  <a href={`/@${slug}`} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    {t('linkPage.open', { defaultValue: 'Apri' })}
                  </a>
                </Button>
              </div>
            </div>

            {/* ── Tema ────────────────────────────────────────────── */}
            <div>
              <p className="text-sm font-semibold text-foreground">
                {t('linkPage.theme', { defaultValue: 'Atmosfera' })}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {THEME_SWATCHES.map(({ key, dot, label }) => (
                  <button key={key} type="button"
                          onClick={() => persist({ ...lp, theme: key })}
                          data-testid={`linkpage-theme-${key}`}
                          className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
                            lp.theme === key
                              ? 'border-primary ring-2 ring-primary/30'
                              : 'border-gray-200 hover:border-gray-400'}`}>
                    <span className={`h-4 w-4 rounded-full ${dot}`} aria-hidden />
                    {label}
                    {lp.theme === key && <Check className="h-3 w-3 text-primary" />}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Blocchi vivi ────────────────────────────────────── */}
            <div>
              <p className="text-sm font-semibold text-foreground">
                {t('linkPage.blocks', { defaultValue: 'Cosa mostrare' })}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t('linkPage.blocksHint', { defaultValue: 'Si aggiornano da soli: il ritiro col prossimo in calendario, il listino coi tuoi servizi.' })}
              </p>
              <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {BLOCK_LABELS.map(([key, label]) => (
                  <label key={key}
                         className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 text-sm">
                    <span>{t(`linkPage.block_${key}`, { defaultValue: label })}</span>
                    <Switch checked={lp.blocks?.[key] !== false}
                            onCheckedChange={(v) => setBlock(key, v)} />
                  </label>
                ))}
              </div>
            </div>

            {/* ── I link personalizzati ───────────────────────────── */}
            <div>
              <p className="text-sm font-semibold text-foreground">
                {t('linkPage.customLinks', { defaultValue: 'I tuoi link' })}
              </p>
              {(lp.links || []).length > 0 && (
                <ul className="mt-2 space-y-1.5">
                  {lp.links.map((l, i) => (
                    <li key={l.id}
                        className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{l.label}</p>
                        <p className="truncate text-xs text-muted-foreground">{l.url}</p>
                      </div>
                      <button type="button" onClick={() => moveLink(l.id, -1)} disabled={i === 0}
                              className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                              aria-label="Sposta su"><ArrowUp className="h-4 w-4" /></button>
                      <button type="button" onClick={() => moveLink(l.id, +1)}
                              disabled={i === lp.links.length - 1}
                              className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                              aria-label="Sposta giù"><ArrowDown className="h-4 w-4" /></button>
                      <button type="button" onClick={() => removeLink(l.id)}
                              className="rounded p-1 text-gray-400 hover:text-red-600"
                              aria-label="Rimuovi"><X className="h-4 w-4" /></button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                <Input placeholder={t('linkPage.labelPh', { defaultValue: 'Nome (es. Il mio canale YouTube)' })}
                       value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
                       className="sm:flex-1" data-testid="linkpage-new-label" />
                <Input placeholder="https://…" value={newUrl}
                       onChange={(e) => setNewUrl(e.target.value)}
                       onKeyDown={(e) => e.key === 'Enter' && addLink()}
                       className="sm:flex-1" data-testid="linkpage-new-url" />
                <Button variant="outline" onClick={addLink} data-testid="linkpage-add">
                  {t('linkPage.add', { defaultValue: 'Aggiungi' })}
                </Button>
              </div>
            </div>
          </div>

          {/* ── Anteprima: la pagina VERA in cornice telefono ─────── */}
          <div className="hidden lg:block">
            <p className="text-sm font-semibold text-foreground">
              {t('linkPage.preview', { defaultValue: 'Anteprima' })}
            </p>
            <div className="mt-2 overflow-hidden rounded-[28px] border-[6px] border-gray-900 bg-gray-900 shadow-lg">
              <iframe key={rev} src={`/l/${slug}`} title="Anteprima pagina link"
                      className="h-[440px] w-full rounded-[22px] bg-white"
                      data-testid="linkpage-preview" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
