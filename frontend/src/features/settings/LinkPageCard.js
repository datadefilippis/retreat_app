/**
 * LinkPageCard — l'editor della pagina link (LK3, rifatto in LK6).
 *
 * Il percorso resta TRE gesti: attiva → copia → incolla in bio. Tutto
 * si salva DA SOLO a ogni tocco (il server risponde normalizzato, id
 * e ordine compresi).
 *
 * LK6 (feedback founder 14/8):
 * - UNA lista sola, riordinabile con le frecce: blocchi vivi e link
 *   personalizzati insieme, nell'ordine che appare sulla pagina
 * - i link personalizzati si MODIFICANO (matita), non solo si tolgono
 * - i blocchi si spiegano da soli: WhatsApp spento e guidato se manca
 *   il numero, social idem, ritiro/listino dicono quando appariranno
 * - l'anteprima e' la pagina vera; i click dentro aprono in una
 *   scheda nuova (mai piu' intrappolati nella cornice)
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Link2, Copy, ExternalLink, ArrowUp, ArrowDown, X, Loader2, Check,
  Pencil, CalendarDays, ListChecks, MessageCircle, User, AlertCircle,
} from 'lucide-react';
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

const BLOCK_META = {
  'block:upcoming': { key: 'upcoming', icon: CalendarDays, label: 'Il prossimo ritiro' },
  'block:listino': { key: 'listino', icon: ListChecks, label: 'Prenota una seduta' },
  'block:whatsapp': { key: 'whatsapp', icon: MessageCircle, label: 'WhatsApp' },
  'block:profile': { key: 'profile', icon: User, label: 'Scopri chi sono' },
};

export default function LinkPageCard({
  slug, initial, hasSocials, hasPhone, onGoToSocials, onGoToContacts,
}) {
  const { t } = useTranslation('settings');
  const [lp, setLp] = useState(initial || {
    enabled: false, theme: 'salvia', links: [], order: [],
    blocks: { upcoming: true, listino: true, profile: true, whatsapp: true, socials: true },
  });
  const [saving, setSaving] = useState(false);
  const [rev, setRev] = useState(0);            // ricarica l'anteprima
  const [newLabel, setNewLabel] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editLabel, setEditLabel] = useState('');
  const [editUrl, setEditUrl] = useState('');
  // LK6 — per dire la verita' sui blocchi ("apparira' quando…") serve
  // sapere cosa esiste davvero: una lettura del payload pubblico basta
  const [pub, setPub] = useState(null);

  useEffect(() => {
    if (!slug) return undefined;
    let alive = true;
    api.get(`/public/operator/${slug}`)
      .then((r) => { if (alive) setPub(r.data); })
      .catch(() => {});
    return () => { alive = false; };
  }, [slug]);

  const hasUpcoming = (pub?.upcoming || []).length > 0;
  const hasListino = (pub?.listino || []).length > 0;

  const pageUrl = useMemo(
    () => (slug ? `${window.location.origin}/@${slug}` : null), [slug]);

  const persist = async (next) => {
    setLp(next);                                 // ottimista: UI subito
    setSaving(true);
    try {
      const res = await api.patch('/organizations/current/public-profile',
        { link_page: next });
      // lo stato NORMALIZZATO dal server (id e ordine completati)
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

  const normalizeUrl = (raw) => {
    let url = (raw || '').trim();
    if (url && !/^https?:\/\//i.test(url)) url = `https://${url}`;
    return url;
  };

  const addLink = () => {
    const label = newLabel.trim();
    const url = normalizeUrl(newUrl);
    if (!label || !url.startsWith('https://')) {
      toast.error(t('linkPage.addInvalid', {
        defaultValue: 'Serve un nome e un indirizzo che inizia con https://' }));
      return;
    }
    persist({ ...lp, links: [...(lp.links || []), { label, url, active: true }] });
    setNewLabel(''); setNewUrl('');
  };

  const startEdit = (l) => {
    setEditingId(l.id); setEditLabel(l.label); setEditUrl(l.url);
  };

  const saveEdit = () => {
    const label = editLabel.trim();
    const url = normalizeUrl(editUrl);
    if (!label || !url.startsWith('https://')) {
      toast.error(t('linkPage.addInvalid', {
        defaultValue: 'Serve un nome e un indirizzo che inizia con https://' }));
      return;
    }
    persist({
      ...lp,
      links: (lp.links || []).map(l =>
        l.id === editingId ? { ...l, label, url } : l),
    });
    setEditingId(null);
  };

  const removeLink = (id) =>
    persist({ ...lp, links: (lp.links || []).filter(l => l.id !== id) });

  const move = (key, dir) => {
    const order = [...(lp.order || [])];
    const i = order.indexOf(key);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    persist({ ...lp, order });
  };

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(pageUrl);
      toast.success(t('linkPage.copied', { defaultValue: 'Link copiato: incollalo nella bio di Instagram.' }));
    } catch {
      toast.error(t('linkPage.copyError', { defaultValue: 'Copia non riuscita.' }));
    }
  };

  /* ── una riga della lista unica ──────────────────────────────── */

  const arrows = (key, i, total) => (
    <span className="flex shrink-0">
      <button type="button" onClick={() => move(key, -1)} disabled={i === 0}
              className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
              aria-label="Sposta su"><ArrowUp className="h-4 w-4" /></button>
      <button type="button" onClick={() => move(key, +1)} disabled={i === total - 1}
              className="rounded p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
              aria-label="Sposta giù"><ArrowDown className="h-4 w-4" /></button>
    </span>
  );

  const blockRow = (key, i, total) => {
    const meta = BLOCK_META[key];
    if (!meta) return null;
    const Icon = meta.icon;
    const isWhatsapp = meta.key === 'whatsapp';
    const missingPhone = isWhatsapp && !hasPhone;
    // "apparira' quando…": la riga dice da dove nasce il contenuto
    let hint = null;
    if (meta.key === 'upcoming' && !hasUpcoming) {
      hint = t('linkPage.hintUpcoming', { defaultValue: 'Apparirà quando pubblichi il prossimo ritiro.' });
    } else if (meta.key === 'listino' && !hasListino) {
      hint = t('linkPage.hintListino', { defaultValue: 'Apparirà quando aggiungi un servizio al listino.' });
    }
    return (
      <li key={key} data-testid={`linkpage-row-${meta.key}`}
          className="rounded-lg border border-gray-100 px-3 py-2">
        <div className="flex items-center gap-2">
          {arrows(key, i, total)}
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {t(`linkPage.block_${meta.key}`, { defaultValue: meta.label })}
            </p>
            {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
            {missingPhone && (
              <button type="button" onClick={onGoToContacts}
                      data-testid="linkpage-goto-contacts"
                      className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                <AlertCircle className="h-3 w-3" />
                {t('linkPage.needPhone', { defaultValue: 'Aggiungi il tuo numero nei contatti del profilo' })}
              </button>
            )}
          </div>
          <Switch checked={!missingPhone && lp.blocks?.[meta.key] !== false}
                  disabled={missingPhone}
                  onCheckedChange={(v) => setBlock(meta.key, v)} />
        </div>
      </li>
    );
  };

  const linkRow = (key, i, total) => {
    const l = (lp.links || []).find(x => `link:${x.id}` === key);
    if (!l) return null;
    if (editingId === l.id) {
      return (
        <li key={key} className="rounded-lg border border-primary/40 px-3 py-2 space-y-2">
          <Input value={editLabel} onChange={(e) => setEditLabel(e.target.value)}
                 placeholder={t('linkPage.labelPh', { defaultValue: 'Nome (es. Il mio canale YouTube)' })} />
          <Input value={editUrl} onChange={(e) => setEditUrl(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
                 placeholder="https://…" />
          <div className="flex gap-2">
            <Button size="sm" onClick={saveEdit} data-testid="linkpage-edit-save">
              {t('linkPage.editSave', { defaultValue: 'Salva' })}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
              {t('linkPage.editCancel', { defaultValue: 'Annulla' })}
            </Button>
          </div>
        </li>
      );
    }
    return (
      <li key={key} className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2">
        {arrows(key, i, total)}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{l.label}</p>
          <p className="truncate text-xs text-muted-foreground">{l.url}</p>
        </div>
        <button type="button" onClick={() => startEdit(l)}
                data-testid={`linkpage-edit-${l.id}`}
                className="rounded p-1 text-gray-400 hover:text-gray-700"
                aria-label="Modifica"><Pencil className="h-4 w-4" /></button>
        <button type="button" onClick={() => removeLink(l.id)}
                className="rounded p-1 text-gray-400 hover:text-red-600"
                aria-label="Rimuovi"><X className="h-4 w-4" /></button>
      </li>
    );
  };

  const order = lp.order || [];

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
            {t('linkPage.subtitle', { defaultValue: 'Un solo link per la bio di Instagram: dentro ci sono il tuo prossimo ritiro, il listino e i link che vuoi tu. Ogni modifica si salva da sola.' })}
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

            {/* ── LA lista: blocchi e link insieme, nel TUO ordine ── */}
            <div>
              <p className="text-sm font-semibold text-foreground">
                {t('linkPage.list', { defaultValue: 'La tua pagina, riga per riga' })}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t('linkPage.listHint', { defaultValue: 'Le frecce cambiano l’ordine: è lo stesso che vedono i tuoi clienti. I blocchi si aggiornano da soli.' })}
              </p>
              <ul className="mt-2 space-y-1.5" data-testid="linkpage-order-list">
                {order.map((key, i) =>
                  key.startsWith('block:')
                    ? blockRow(key, i, order.length)
                    : linkRow(key, i, order.length))}
              </ul>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                <Input placeholder={t('linkPage.labelPh', { defaultValue: 'Nome (es. Il mio canale YouTube)' })}
                       value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
                       className="sm:flex-1" data-testid="linkpage-new-label" />
                <Input placeholder="https://…" value={newUrl}
                       onChange={(e) => setNewUrl(e.target.value)}
                       onKeyDown={(e) => e.key === 'Enter' && addLink()}
                       className="sm:flex-1" data-testid="linkpage-new-url" />
                <Button variant="outline" onClick={addLink} data-testid="linkpage-add">
                  {t('linkPage.add', { defaultValue: 'Aggiungi link' })}
                </Button>
              </div>
            </div>

            {/* ── Icone social sotto al nome ──────────────────────── */}
            <div className="rounded-lg border border-gray-100 px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {t('linkPage.block_socials', { defaultValue: 'Icone social sotto al nome' })}
                  </p>
                  {!hasSocials && (
                    <button type="button" onClick={onGoToSocials}
                            data-testid="linkpage-goto-socials"
                            className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                      <AlertCircle className="h-3 w-3" />
                      {t('linkPage.needSocials', { defaultValue: 'Aggiungi i tuoi social qui sopra, nel profilo' })}
                    </button>
                  )}
                </div>
                <Switch checked={hasSocials && lp.blocks?.socials !== false}
                        disabled={!hasSocials}
                        onCheckedChange={(v) => setBlock('socials', v)} />
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
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              {t('linkPage.previewHint', { defaultValue: 'I click nell’anteprima aprono in una scheda nuova.' })}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
