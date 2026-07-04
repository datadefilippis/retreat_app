/**
 * Page-level embed config — Embed à-la-carte, Fase 1.
 *
 * Legge la configurazione una-tantum dichiarata sul tag <script> del bundle:
 *
 *   <script type="module" src=".../afianco-embed.es.js"
 *           data-afianco-slug="mio-store"
 *           data-afianco-base-url="http://localhost:8000"></script>
 *
 * Cosi' gli elementi à-la-carte (<afianco-cart-button>, ...) NON devono
 * ripetere slug/base-url: ereditano questo default. Un elemento puo'
 * comunque fare override con l'attributo `store="altro-slug"`.
 *
 * NB: in un ES module ``document.currentScript`` e' null, quindi si cerca
 * il primo <script> che porta ``data-afianco-slug``. Risultato cachato.
 */

export interface PageEmbedConfig {
  slug?: string;
  baseUrl?: string;
  /** Fase 5 — token preview read-only (solo anteprima dashboard). */
  previewToken?: string;
}

let _cached: PageEmbedConfig | null = null;

/** Legge (e cacha) la config di pagina dal tag script del bundle. */
export function getPageConfig(): PageEmbedConfig {
  if (_cached) return _cached;
  let slug: string | undefined;
  let baseUrl: string | undefined;
  let previewToken: string | undefined;
  try {
    const el = document.querySelector('script[data-afianco-slug]');
    if (el) {
      slug = el.getAttribute('data-afianco-slug') || undefined;
      baseUrl = el.getAttribute('data-afianco-base-url') || undefined;
      previewToken = el.getAttribute('data-afianco-preview-token') || undefined;
    }
  } catch {
    // SSR / no-DOM → nessuna config di pagina.
  }
  _cached = { slug, baseUrl, previewToken };
  return _cached;
}

/** Test-only: resetta la cache (i test possono cambiare i tag script). */
export function __resetPageConfigForTests(): void {
  _cached = null;
}
