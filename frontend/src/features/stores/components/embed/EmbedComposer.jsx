/**
 * EmbedComposer — pannello "Componi" (Embed à-la-carte, Fase 4).
 *
 * Builder data-driven: la UI deriva dal ``blocks_catalog`` restituito dal
 * backend (embed-info). L'utente seleziona blocchi (carrello, account,
 * categorie, singolo prodotto), li configura, e il backend genera lo snippet
 * (``POST /embed-snippet``) — unica fonte di verita', nessun drift.
 *
 * Modulare: questo file orchestra; i pezzi (checklist, picker, output) sono
 * piccoli componenti locali. Aggiungere un blocco lato backend lo fa comparire
 * qui automaticamente (eccetto eventuali picker custom di config).
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../../../../components/ui/button';
import { Copy, Check, Loader2, ShoppingCart, User, LayoutGrid, Package } from 'lucide-react';
import { toast } from 'sonner';
import { storeEmbedAPI } from '../../../../api/storeEmbed';
import { productsAPI } from '../../../../api/products';

const ICONS = {
  'cart-button': ShoppingCart,
  'account-button': User,
  categories: LayoutGrid,
  product: Package,
};

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// Backend URL per le chiamate /embed/* dall'anteprima (dev: localhost:8000).
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Bundle servito same-origin (CRA in dev, app origin in prod servono /embed/v1).
function bundleSrc() {
  return `${window.location.origin}/embed/v1/afianco-embed.es.js`;
}

/**
 * Costruisce il documento (srcdoc) per l'anteprima live in iframe.
 * Usa il bundle locale + base-url backend + preview-token (read-only) così
 * l'embed funziona dall'origin admin senza toccare gli allowed_origins.
 */
function buildPreviewDoc({ slug, token, result }) {
  const elements = (result.elements || []).map((e) => e.html).join('\n');
  const singletons = (result.singletons || []).map((s) => s.html).join('\n');
  const baseAttr = BACKEND_URL ? ` data-afianco-base-url="${BACKEND_URL}"` : '';
  return `<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;padding:14px;font-family:system-ui,-apple-system,sans-serif;background:#fff}</style>
<script type="module" src="${bundleSrc()}" data-afianco-slug="${slug}"${baseAttr} data-afianco-preview-token="${token}"></script>
</head><body>
${elements}
${singletons}
</body></html>`;
}

// ── Picker: categorie (multi-select chips) ───────────────────────────────
function CategoryPicker({ categories, selected, onChange }) {
  if (!categories?.length) {
    return (
      <p className="text-xs text-muted-foreground">
        Nessuna categoria trovata: verra' embeddato l'intero catalogo.
      </p>
    );
  }
  const toggle = (slug) =>
    onChange(selected.includes(slug) ? selected.filter((s) => s !== slug) : [...selected, slug]);
  return (
    <div className="flex flex-wrap gap-1.5">
      {categories.map((c) => {
        const on = selected.includes(c.slug);
        return (
          <button
            key={c.slug}
            type="button"
            onClick={() => toggle(c.slug)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              on
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-muted-foreground hover:border-foreground/30'
            }`}
          >
            {c.name} {typeof c.count === 'number' ? `(${c.count})` : ''}
          </button>
        );
      })}
      <span className="self-center text-xs text-muted-foreground">
        {selected.length === 0 ? 'vuoto = tutte' : `${selected.length} selezionate`}
      </span>
    </div>
  );
}

// ── Picker: singolo prodotto ─────────────────────────────────────────────
function ProductPicker({ products, loading, value, onChange }) {
  if (loading) {
    return <p className="text-xs text-muted-foreground">Caricamento prodotti…</p>;
  }
  if (!products?.length) {
    return <p className="text-xs text-muted-foreground">Nessun prodotto pubblicato.</p>;
  }
  return (
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm"
    >
      <option value="">— seleziona un prodotto —</option>
      {products.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────
export default function EmbedComposer({ storeId, embedInfo }) {
  const catalog = useMemo(
    () => (embedInfo?.blocks_catalog || []).filter((b) => b.id !== 'full'),
    [embedInfo],
  );
  const categories = embedInfo?.categories || [];

  const [selected, setSelected] = useState([]); // block ids
  const [catSel, setCatSel] = useState([]); // category slugs
  const [productId, setProductId] = useState('');
  const [products, setProducts] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);

  const [result, setResult] = useState(null);
  const [composing, setComposing] = useState(false);
  const [copied, setCopied] = useState(false);

  // Anteprima live: token read-only per chiamare /embed/* dall'origin admin.
  const [preview, setPreview] = useState(null); // { token, slug }

  const wantsProduct = selected.includes('product');
  const wantsCategories = selected.includes('categories');

  // Recupera il preview token una volta per store (TTL 15 min, sessione breve).
  useEffect(() => {
    if (!storeId) return undefined;
    let cancelled = false;
    storeEmbedAPI
      .getPreviewToken(storeId)
      .then((res) => !cancelled && setPreview({ token: res.data.token, slug: res.data.slug }))
      .catch(() => !cancelled && setPreview(null));
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  // Lazy-load prodotti quando serve il picker.
  // NB: `productsLoading` NON va nelle deps — settarlo a true ri-eseguirebbe
  // l'effetto, il cui cleanup cancella il fetch in volo → loading infinito.
  useEffect(() => {
    if (!storeId || !wantsProduct || products.length) return;
    let cancelled = false;
    setProductsLoading(true);
    productsAPI
      .list(false, 500, storeId)
      .then((res) => {
        if (cancelled) return;
        const raw = res?.data;
        const items = Array.isArray(raw) ? raw : raw?.items || [];
        // mostra solo pubblicati (gli altri non renderizzerebbero via embed)
        setProducts(items.filter((p) => p.is_published !== false));
      })
      .catch(() => !cancelled && setProducts([]))
      .finally(() => !cancelled && setProductsLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantsProduct, products.length, storeId]);

  const toggleBlock = useCallback((id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }, []);

  // Config corrente derivata dalle selezioni.
  const config = useMemo(() => {
    const cfg = {};
    if (wantsCategories) cfg.categories = { categories: catSel };
    if (wantsProduct) cfg.product = { product_id: productId };
    return cfg;
  }, [wantsCategories, wantsProduct, catSel, productId]);

  // Recompute snippet (debounced) ad ogni cambio selezione/config.
  const selKey = selected.slice().sort().join(',');
  const cfgKey = JSON.stringify(config);
  useEffect(() => {
    if (!storeId || selected.length === 0) {
      setResult(null);
      return;
    }
    // product selezionato ma senza id → non comporre ancora.
    if (wantsProduct && !productId) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setComposing(true);
    const timer = setTimeout(() => {
      storeEmbedAPI
        .composeSnippet(storeId, selected, config)
        .then((res) => !cancelled && setResult(res.data))
        .catch((err) => {
          if (cancelled) return;
          const d = err?.response?.data?.detail;
          toast.error(typeof d === 'string' ? d : 'Errore generazione snippet');
          setResult(null);
        })
        .finally(() => !cancelled && setComposing(false));
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selKey, cfgKey, storeId]);

  const handleCopy = async () => {
    if (!result?.snippet) return;
    if (await copyText(result.snippet)) {
      setCopied(true);
      toast.success('Snippet copiato');
      setTimeout(() => setCopied(false), 2000);
    } else {
      toast.error('Impossibile copiare');
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Scegli gli elementi da embeddare separatamente (es. carrello e account nel
        menu, categorie o un singolo prodotto in pagine diverse). Genero lo snippet
        pronto da incollare.
      </p>

      {/* Checklist blocchi */}
      <div className="space-y-2">
        {catalog.map((b) => {
          const Icon = ICONS[b.id] || Package;
          const on = selected.includes(b.id);
          return (
            <div
              key={b.id}
              className={`rounded-lg border p-3 transition-colors ${
                on ? 'border-primary/50 bg-primary/5' : 'border-border'
              }`}
            >
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => toggleBlock(b.id)}
                  className="mt-1 h-4 w-4 accent-[var(--primary)]"
                />
                <span className="flex-1">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {b.label}
                  </span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {b.description}
                  </span>
                </span>
              </label>

              {/* Config inline del blocco */}
              {on && b.id === 'categories' && (
                <div className="mt-3 pl-7">
                  <CategoryPicker categories={categories} selected={catSel} onChange={setCatSel} />
                </div>
              )}
              {on && b.id === 'product' && (
                <div className="mt-3 pl-7">
                  <ProductPicker
                    products={products}
                    loading={productsLoading}
                    value={productId}
                    onChange={setProductId}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Anteprima live (iframe sandboxed, dati reali, sola lettura) */}
      {result && preview && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Anteprima live</span>
            <span className="text-xs text-muted-foreground">dati reali · sola lettura</span>
          </div>
          <iframe
            title="Anteprima embed"
            srcDoc={buildPreviewDoc({ slug: preview.slug, token: preview.token, result })}
            sandbox="allow-scripts allow-same-origin"
            className="w-full rounded-lg border border-border bg-white"
            style={{ height: 460 }}
            data-testid="embed-live-preview"
          />
        </div>
      )}

      {/* Output snippet */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Codice da incollare</span>
          {composing && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </div>

        {!result && selected.length === 0 && (
          <div className="rounded-lg border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
            Seleziona almeno un elemento per generare il codice.
          </div>
        )}
        {!result && wantsProduct && !productId && selected.length > 0 && (
          <div className="rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 py-4 text-center text-sm text-amber-800">
            Seleziona un prodotto per generare il codice.
          </div>
        )}

        {result && (
          <div className="relative rounded-lg border border-border bg-slate-950 text-slate-50">
            <div className="absolute right-2 top-2 z-10">
              <Button
                variant="secondary"
                size="sm"
                className="h-8 gap-1.5 border-slate-700 bg-slate-800 text-slate-100 hover:bg-slate-700"
                onClick={handleCopy}
                data-testid="copy-composed-snippet"
              >
                {copied ? <><Check className="h-3.5 w-3.5" />Copiato</> : <><Copy className="h-3.5 w-3.5" />Copia</>}
              </Button>
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap break-all p-4 pr-24 text-xs leading-relaxed font-mono">
              {result.snippet}
            </pre>
          </div>
        )}

        {result && (
          <div className="space-y-1.5 text-xs text-muted-foreground">
            <p>
              <strong>Dove incollare:</strong> Sezione 1 = una volta nel{' '}
              <code>&lt;head&gt;</code>. Sezione 2 = dove vuoi (anche pagine diverse).
              Sezione 3 = una volta a fine pagina (anche su tutte le pagine).
            </p>
            <p className="rounded-md bg-amber-50 border border-amber-200 px-2.5 py-2 text-amber-800">
              Perche' funzioni: il dominio del tuo sito deve essere tra i{' '}
              <strong>domini autorizzati</strong> qui sopra, e lo store dev'essere
              pubblicato. Su una pagina locale di test puo' apparire vuoto finche'
              non e' online.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
