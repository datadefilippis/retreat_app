/**
 * ShareStoreModal — modale "Condividi store" per merchant dashboard.
 *
 * Track E Step 2.3 — UX consolidation embed commerce.
 * Track E Step 2.4.1 — UX polish multipiattaforma (modern + responsive).
 *
 * 2 tab Shadcn UI:
 *   1. "Link"      — hosted URL afianco.ch/s/{slug} + copy
 *      (funziona SEMPRE per store pubblicati, nessun setup richiesto)
 *
 *   2. "Embed"     — manage allowed_origins + snippet HTML
 *      (richiede aggiunta dominio merchant + bundle JS deployato)
 *
 * Data flow:
 *   1. On open → storeEmbedAPI.getEmbedInfo(store.id) carica snippet,
 *      bundle URL, hosted URL, allowed_origins, embed_status
 *   2. Tab 1: copia hosted URL via clipboard API
 *   3. Tab 2: user add/remove origin client-side, Save → PATCH
 *
 * UX principles (E2.4.1):
 *   - Responsive: mobile-first, gracefully scales to desktop
 *   - No overflow: text-wrap, break-all, max-height + scroll body
 *   - Modern: badges, color-coded status, clear hierarchy
 *   - Touch-friendly: button targets >=40px, tap zones ample
 *   - Accessible: labels, focus rings, keyboard nav (Enter to add)
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ResponsiveDialog, ResponsiveDialogContent, ResponsiveDialogHeader,
  ResponsiveDialogTitle, ResponsiveDialogFooter,
} from '../../../components/ui/responsive-dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../../../components/ui/tabs';
import {
  Share2, Copy, Check, Globe, Code, Loader2, Plus, X, ExternalLink,
  AlertTriangle, CheckCircle2, Info, MessageCircle, QrCode,
} from 'lucide-react';
import { toast } from 'sonner';
import { storeEmbedAPI } from '../../../api/storeEmbed';
import EmbedComposer from './embed/EmbedComposer';
import ErrorBoundary from '../../../components/ErrorBoundary';


/**
 * Copy text to clipboard via navigator API (HTTPS-only requirement).
 * Returns true if successful. Toast feedback handled by caller.
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for legacy browsers / HTTP context: use deprecated execCommand
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      return true;
    } catch {
      return false;
    }
  }
}


/**
 * Validate single origin client-side (lighter version del backend).
 * Backend e' fonte di verita' (riusa _validate_allowed_origins Pydantic).
 * Quello qui e' solo feedback UX immediato.
 */
function validateOriginClientSide(origin) {
  if (!origin || typeof origin !== 'string') {
    return { valid: false, error: 'required' };
  }
  const trimmed = origin.trim();
  if (!trimmed) {
    return { valid: false, error: 'empty' };
  }
  if (trimmed === '*' || trimmed === 'null') {
    return { valid: false, error: 'wildcard_or_null' };
  }
  if (!trimmed.match(/^https?:\/\//)) {
    return { valid: false, error: 'protocol' };
  }
  if (trimmed.length > 200) {
    return { valid: false, error: 'too_long' };
  }
  return { valid: true, normalized: trimmed };
}


// ── Small UI helpers ──────────────────────────────────────────────────


/**
 * StatusBadge — visual indicator for embed_status.
 * Returns appropriate Badge component for "active" | "no_origins" |
 * "store_unpublished".
 */
function StatusBadge({ status, originCount }) {
  if (status === 'active') {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Attivo · {originCount} {originCount === 1 ? 'dominio' : 'domini'}
      </div>
    );
  }
  if (status === 'no_origins') {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-xs font-medium text-amber-700">
        <AlertTriangle className="h-3.5 w-3.5" />
        Da configurare
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600">
      <Info className="h-3.5 w-3.5" />
      Store non pubblicato
    </div>
  );
}


/**
 * OriginRow — single allowed_origin entry with remove action.
 * Layout: stack on mobile, flex-row on tablet+, URL wraps if too long.
 */
function OriginRow({ origin, onRemove, t }) {
  return (
    <div className="group flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:border-foreground/20">
      <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="flex-1 break-all font-mono text-xs sm:text-sm text-foreground">
        {origin}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 opacity-60 hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
        onClick={() => onRemove(origin)}
        data-testid={`remove-origin-${origin}`}
        title={t('share.remove_origin', { defaultValue: 'Rimuovi dominio' })}
        aria-label={`Rimuovi ${origin}`}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}


// ── Main component ─────────────────────────────────────────────────────


export default function ShareStoreModal({ store, open, onOpenChange }) {
  const { t } = useTranslation('stores');

  const [loading, setLoading] = useState(true);
  const [embedInfo, setEmbedInfo] = useState(null);
  const [error, setError] = useState(null);

  // Tab 2 state — local edits del allowed_origins array
  const [originsDraft, setOriginsDraft] = useState([]);
  const [newOriginInput, setNewOriginInput] = useState('');
  const [saving, setSaving] = useState(false);

  // Copy feedback per tab
  const [copiedField, setCopiedField] = useState(null);

  // Embed tab: modalita' "tutto lo store" (snippet completo) vs "componi"
  // (builder à-la-carte per blocchi singoli).
  const [embedMode, setEmbedMode] = useState('all'); // 'all' | 'compose'

  // Load embed info on open
  useEffect(() => {
    if (!open || !store?.id) return;
    setLoading(true);
    setError(null);
    storeEmbedAPI
      .getEmbedInfo(store.id)
      .then((res) => {
        setEmbedInfo(res.data);
        setOriginsDraft(res.data.allowed_origins || []);
      })
      .catch((err) => {
        const msg =
          err?.response?.data?.detail || err?.message || 'Errore caricamento';
        setError(msg);
        toast.error(typeof msg === 'string' ? msg : 'Errore caricamento embed info');
      })
      .finally(() => setLoading(false));
  }, [open, store?.id]);

  // Reset state on close
  useEffect(() => {
    if (!open) {
      setEmbedInfo(null);
      setOriginsDraft([]);
      setNewOriginInput('');
      setError(null);
      setCopiedField(null);
    }
  }, [open]);

  const handleCopy = useCallback(async (text, field) => {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopiedField(field);
      toast.success(t('share.copied', { defaultValue: 'Copiato negli appunti' }));
      setTimeout(() => setCopiedField(null), 2000);
    } else {
      toast.error(t('share.copy_failed', { defaultValue: 'Impossibile copiare' }));
    }
  }, [t]);

  const handleAddOrigin = useCallback(() => {
    const result = validateOriginClientSide(newOriginInput);
    if (!result.valid) {
      const errorMessages = {
        required: 'Inserisci un dominio.',
        empty: 'Il dominio non puo essere vuoto.',
        wildcard_or_null: 'Wildcard "*" o "null" non permessi.',
        protocol: 'Inizia con https:// (o http:// solo in sviluppo).',
        too_long: 'Dominio troppo lungo (max 200 caratteri).',
      };
      toast.error(errorMessages[result.error] || 'Dominio non valido');
      return;
    }
    if (originsDraft.includes(result.normalized)) {
      toast.error('Dominio gia presente nella lista.');
      return;
    }
    if (originsDraft.length >= 10) {
      toast.error('Massimo 10 domini per store.');
      return;
    }
    setOriginsDraft([...originsDraft, result.normalized]);
    setNewOriginInput('');
  }, [newOriginInput, originsDraft]);

  const handleRemoveOrigin = useCallback((origin) => {
    setOriginsDraft(originsDraft.filter((o) => o !== origin));
  }, [originsDraft]);

  const handleSaveOrigins = useCallback(async () => {
    if (!store?.id) return;
    setSaving(true);
    try {
      const res = await storeEmbedAPI.updateAllowedOrigins(store.id, originsDraft);
      setEmbedInfo(res.data);
      setOriginsDraft(res.data.allowed_origins || []);
      toast.success(t('share.saved', { defaultValue: 'Configurazione salvata' }));
    } catch (err) {
      const detail = err?.response?.data?.detail;
      let msg = 'Errore salvataggio';
      if (Array.isArray(detail) && detail.length > 0) {
        msg = detail[0].msg || msg;
      } else if (typeof detail === 'string') {
        msg = detail;
      }
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }, [store?.id, originsDraft, t]);

  // WhatsApp share helper (use case principale di Tab 1)
  const handleWhatsAppShare = useCallback(() => {
    if (!embedInfo?.hosted_url) return;
    const msg = encodeURIComponent(
      `Scopri il mio store: ${embedInfo.hosted_url}`
    );
    window.open(`https://wa.me/?text=${msg}`, '_blank', 'noopener,noreferrer');
  }, [embedInfo?.hosted_url]);

  // Detect unchanged → disable Save
  const originsUnchanged = useMemo(() => {
    if (!embedInfo) return true;
    return JSON.stringify(originsDraft) === JSON.stringify(embedInfo.allowed_origins || []);
  }, [embedInfo, originsDraft]);

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      {/*
        Track E Step 2.4.1 — UX polish:
        - max-w-3xl (768px) per accomodare snippet senza overflow
        - max-h-[85vh] + overflow-y-auto su body per tall content
        - gap-0 + flex-col per controllo preciso spacing
      */}
      <ResponsiveDialogContent className="sm:max-w-3xl gap-0 p-0 max-h-[90vh] flex flex-col">
        {/* ── Header ─────────────────────────────────────────────── */}
        <ResponsiveDialogHeader className="px-6 py-4 border-b border-border shrink-0">
          <ResponsiveDialogTitle className="flex items-start gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Share2 className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-base font-semibold">
                {t('share.title', { defaultValue: 'Condividi store' })}
              </div>
              {store?.name && (
                <div className="text-xs font-normal text-muted-foreground truncate">
                  {store.name}
                </div>
              )}
            </div>
            {/* Status badge inline (visible only when loaded) */}
            {!loading && embedInfo && (
              <div className="shrink-0 hidden sm:block">
                <StatusBadge
                  status={embedInfo.embed_status}
                  originCount={originsDraft.length}
                />
              </div>
            )}
          </ResponsiveDialogTitle>
        </ResponsiveDialogHeader>

        {/* ── Body (scrollable) ─────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && !loading && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <div>
                  <div className="font-medium">Errore caricamento</div>
                  <div className="text-xs mt-0.5 opacity-90">
                    {typeof error === 'string' ? error : 'Errore di rete'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && embedInfo && (
            <Tabs defaultValue="hosted" className="w-full">
              <TabsList className="grid w-full grid-cols-2 h-11">
                <TabsTrigger value="hosted" data-testid="share-tab-hosted" className="gap-1.5">
                  <Globe className="h-4 w-4" />
                  <span className="hidden xs:inline">
                    {t('share.tab_hosted', { defaultValue: 'Link' })}
                  </span>
                </TabsTrigger>
                <TabsTrigger value="embed" data-testid="share-tab-embed" className="gap-1.5">
                  <Code className="h-4 w-4" />
                  <span className="hidden xs:inline">
                    {t('share.tab_embed', { defaultValue: 'Embed' })}
                  </span>
                </TabsTrigger>
              </TabsList>

              {/* ── Tab 1: Hosted link ──────────────────────────── */}
              <TabsContent value="hosted" className="space-y-4 pt-5 mt-0">
                {!embedInfo.is_published ? (
                  <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-700" />
                    <div>
                      <div className="font-medium">Store non pubblicato</div>
                      <div className="text-xs mt-0.5 opacity-90">
                        Pubblica il tuo store per renderlo accessibile a questo link.
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {t('share.hosted_intro', {
                      defaultValue: 'Il tuo store e accessibile a questo indirizzo. Condividilo via WhatsApp, social, email o stampalo come QR code. Nessuna configurazione richiesta.'
                    })}
                  </p>
                )}

                {/* URL block — mobile stacks, desktop horizontal */}
                <div className="space-y-2">
                  <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {t('share.public_url', { defaultValue: 'URL pubblico' })}
                  </Label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input
                      value={embedInfo.hosted_url}
                      readOnly
                      className="font-mono text-xs sm:text-sm break-all flex-1"
                      data-testid="hosted-url-input"
                      onClick={(e) => e.target.select()}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="default"
                        className="flex-1 sm:flex-initial gap-2"
                        onClick={() => handleCopy(embedInfo.hosted_url, 'hosted')}
                        data-testid="copy-hosted-button"
                      >
                        {copiedField === 'hosted' ? (
                          <><Check className="h-4 w-4" /><span className="sm:hidden">Copiato</span></>
                        ) : (
                          <><Copy className="h-4 w-4" /><span className="sm:hidden">Copia</span></>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="default"
                        className="flex-1 sm:flex-initial gap-2"
                        onClick={() => window.open(embedInfo.hosted_url, '_blank', 'noopener,noreferrer')}
                        title={t('share.open_external', { defaultValue: 'Apri in nuova scheda' })}
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span className="sm:hidden">Apri</span>
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Quick share actions */}
                {embedInfo.is_published && (
                  <div className="space-y-2 pt-1">
                    <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      {t('share.quick_share', { defaultValue: 'Condivisione rapida' })}
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={handleWhatsAppShare}
                      >
                        <MessageCircle className="h-4 w-4" />
                        WhatsApp
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={() => {
                          // Generate QR code URL via public service
                          const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(embedInfo.hosted_url)}`;
                          window.open(qrUrl, '_blank', 'noopener,noreferrer');
                        }}
                      >
                        <QrCode className="h-4 w-4" />
                        QR Code
                      </Button>
                    </div>
                  </div>
                )}

                {/* Benefits list */}
                <div className="rounded-lg bg-muted/40 p-4 space-y-1.5 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Funziona sempre per store pubblicati</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Nessun setup tecnico richiesto</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Ideale per chi non ha un sito proprio</span>
                  </div>
                </div>
              </TabsContent>

              {/* ── Tab 2: Embed code ────────────────────────────── */}
              <TabsContent value="embed" className="space-y-5 pt-5 mt-0">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {t('share.embed_intro', {
                    defaultValue: 'Embedda il tuo store su un sito esterno (es. WordPress, Wix, sito personalizzato). Richiede autorizzare il dominio del sito host.'
                  })}
                </p>

                {/* Section 1: allowed_origins management */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <Label className="text-sm font-semibold flex items-center gap-2">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">1</span>
                      {t('share.allowed_origins_label', { defaultValue: 'Domini autorizzati' })}
                    </Label>
                    <span className="text-xs font-mono text-muted-foreground">
                      {originsDraft.length}/10
                    </span>
                  </div>

                  {originsDraft.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border bg-muted/30 px-4 py-6 text-center">
                      <Globe className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                      <p className="text-sm text-muted-foreground">
                        {t('share.no_origins', {
                          defaultValue: 'Nessun dominio autorizzato'
                        })}
                      </p>
                      <p className="text-xs text-muted-foreground/70 mt-1">
                        Aggiungi sotto almeno un dominio per attivare l'embed
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {originsDraft.map((origin) => (
                        <OriginRow
                          key={origin}
                          origin={origin}
                          onRemove={handleRemoveOrigin}
                          t={t}
                        />
                      ))}
                    </div>
                  )}

                  {/* Add origin input */}
                  <div className="flex flex-col sm:flex-row gap-2 pt-1">
                    <Input
                      placeholder="https://www.mioshop.com"
                      value={newOriginInput}
                      onChange={(e) => setNewOriginInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddOrigin();
                        }
                      }}
                      className="font-mono text-xs sm:text-sm"
                      data-testid="new-origin-input"
                    />
                    <Button
                      variant="default"
                      onClick={handleAddOrigin}
                      disabled={!newOriginInput.trim() || originsDraft.length >= 10}
                      className="gap-2 shrink-0"
                      data-testid="add-origin-button"
                    >
                      <Plus className="h-4 w-4" />
                      Aggiungi
                    </Button>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    <span className="font-mono">HTTPS</span> obbligatorio in produzione.
                    Max 10 domini. Wildcard <span className="font-mono">*</span> non permesso.
                  </p>
                </div>

                {/* Section 2: cosa embeddare — tutto lo store vs componi */}
                <div className="space-y-3">
                  <Label className="text-sm font-semibold flex items-center gap-2">
                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">2</span>
                    {t('share.snippet_label', { defaultValue: 'Codice da incollare' })}
                  </Label>

                  {/* Toggle modalita' */}
                  <div className="inline-flex rounded-lg border border-border bg-muted/30 p-0.5 text-sm">
                    <button
                      type="button"
                      onClick={() => setEmbedMode('all')}
                      data-testid="embed-mode-all"
                      className={`rounded-md px-3 py-1.5 font-medium transition-colors ${embedMode === 'all' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground'}`}
                    >
                      Tutto lo store
                    </button>
                    <button
                      type="button"
                      onClick={() => setEmbedMode('compose')}
                      data-testid="embed-mode-compose"
                      className={`rounded-md px-3 py-1.5 font-medium transition-colors ${embedMode === 'compose' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground'}`}
                    >
                      Componi
                    </button>
                  </div>

                  {embedMode === 'compose' ? (
                    <ErrorBoundary
                      fallback={(err, reset) => (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                          <div className="font-medium">Errore nel pannello "Componi"</div>
                          <div className="text-xs mt-0.5 opacity-90">
                            {err?.message || 'Errore imprevisto'}
                          </div>
                          <button
                            onClick={reset}
                            className="mt-2 text-xs font-semibold underline"
                          >
                            Riprova
                          </button>
                        </div>
                      )}
                    >
                      <EmbedComposer storeId={store?.id} embedInfo={embedInfo} />
                    </ErrorBoundary>
                  ) : (
                  <div className="relative rounded-lg border border-border bg-slate-950 text-slate-50">
                    {/* Copy button outside the scroll area */}
                    <div className="absolute right-2 top-2 z-10">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="gap-1.5 h-8 bg-slate-800 hover:bg-slate-700 text-slate-100 border-slate-700"
                        onClick={() => handleCopy(embedInfo.snippet, 'snippet')}
                        data-testid="copy-snippet-button"
                      >
                        {copiedField === 'snippet' ? (
                          <><Check className="h-3.5 w-3.5" />Copiato</>
                        ) : (
                          <><Copy className="h-3.5 w-3.5" />Copia</>
                        )}
                      </Button>
                    </div>
                    {/*
                      whitespace-pre-wrap: rispetta \n + permette wrap su line lunghe
                      break-all: spezza URL lunghi senza overflow orizzontale
                    */}
                    <pre
                      className="overflow-x-auto p-4 pr-24 text-xs leading-relaxed font-mono whitespace-pre-wrap break-all"
                      data-testid="embed-snippet"
                    >
                      {embedInfo.snippet}
                    </pre>
                  </div>
                  )}
                </div>

                {/* Status indicator (in-tab — desktop sees in header too) */}
                <div className="sm:hidden">
                  <StatusBadge
                    status={embedInfo.embed_status}
                    originCount={originsDraft.length}
                  />
                </div>

                {embedInfo.embed_status === 'no_origins' && (
                  <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-700" />
                    <div>
                      <div className="font-medium">Embed non funzionante</div>
                      <div className="text-xs mt-0.5 opacity-90">
                        Aggiungi almeno un dominio autorizzato sopra per attivare lo embed.
                      </div>
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </div>

        {/* ── Footer (sticky bottom) ────────────────────────────── */}
        <ResponsiveDialogFooter className="border-t border-border px-6 py-3 shrink-0 gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange?.(false)}
            className="w-full sm:w-auto"
          >
            {t('actions.close', { defaultValue: 'Chiudi' })}
          </Button>
          {/* Save button: appears only when unsaved changes on embed tab */}
          {embedInfo && !originsUnchanged && (
            <Button
              onClick={handleSaveOrigins}
              disabled={saving}
              className="w-full sm:w-auto gap-2"
              data-testid="save-origins-button"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('share.save_origins', { defaultValue: 'Salva modifiche' })}
            </Button>
          )}
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
