/**
 * ProductProfileSlide — drill-down slide-over for a single product.
 *
 * Triggered from the KPI cards (top seller / most profitable) or by
 * clicking a row in the products table. Loads on-demand:
 *
 *   - The materialised metric row (for life-of-product totals)
 *   - The current resolved cost (via cost-preview/{product_id}) so
 *     the merchant sees the same decomposition that was used to
 *     compute the margin
 *
 * Mirror of CustomerProfileSlide in shape (Sheet + sections); only
 * the data sources differ.
 *
 * Props:
 *   productId     — UUID of the product to load
 *   summary       — optional partial row from the table for instant
 *                   header fill while the full payload is loading
 *   open          — controlled Sheet open state
 *   onOpenChange  — Sheet open-change handler
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../../../components/ui/sheet';
import { Skeleton } from '../../../components/ui/skeleton';
import { Button } from '../../../components/ui/button';
import { ExternalLink, AlertCircle, Loader2 } from 'lucide-react';
import { productCatalogAPI } from '../../../api/productCatalog';
import { productsAPI } from '../../../api/products';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';
import { productDashboardPath } from '../../../utils/productPaths';


// Map resolver "type" enum back to the i18n label key from the new
// product_cost namespace so the slide and the editor speak the same
// language across the app.
const _typeLabel = (type, t) =>
  t(`component.type.${type}_short`, { defaultValue: type, ns: 'product_cost' });


// ── Profile-button dispatch ──────────────────────────────────────────────────
//
// Maps the product's item_type to the per-type dashboard URL.  Uses the
// shared productDashboardPath() helper (utils/productPaths.js) for the
// 5 product types that key off product_id (physical, service, digital,
// rental, booking).  The two edge cases are handled inline:
//
//   • event_ticket → /products?type=event_ticket
//     EventDashboardPage takes occurrence_id, not product_id; a product
//     of type event_ticket has N occurrences. Without selecting one we
//     can't navigate to the dashboard, so we land on the type-filtered
//     hub view (NOT the legacy /products?product_id=... deep-link, which
//     would re-open the deprecated Dialog).
//
//   • course → /courses/{course_id}
//     CourseEditor takes course_id, not product_id.  Resolved lazily by
//     the caller via productsAPI.get() — see resolveAndOpenAnagraphic().

function _resolveAnagraphicHref(itemType, productId, courseId) {
  if (itemType === 'event_ticket') {
    // No occurrence_id available at this point; go to the filtered hub
    // so the admin can pick which occurrence to drill into. Anything
    // pointing at /products?product_id=... would re-open the legacy
    // Dialog (slated for removal in PR-4) — explicitly avoided here.
    return '/products?type=event_ticket';
  }
  if (itemType === 'course') {
    // courseId resolved lazily by the caller; if missing fall back to
    // the courses list so the admin still has a sensible destination.
    return courseId ? `/courses/${courseId}` : '/courses';
  }
  // 5 happy-path types — physical, service, digital, rental, booking.
  // productDashboardPath returns null if it can't dispatch (e.g.
  // missing productId), in which case we fall through to /products
  // (the lite hub, not the legacy Dialog).
  const dispatched = productDashboardPath({ itemType, productId });
  return dispatched || '/products';
}

// Choose the right i18n button label for the resolved item_type.
// Three buckets so we don't fragment translations across 7 strings.
function _anagraphicLabelKey(itemType) {
  if (itemType === 'event_ticket') return 'profile.open_events_list';
  if (itemType === 'course') return 'profile.open_course';
  return 'profile.open_product_profile';
}


export default function ProductProfileSlide({ productId, summary, open, onOpenChange }) {
  const { t } = useTranslation('product_catalog');
  const currency = useCurrency();

  const [metric, setMetric] = useState(null);
  const [costPreview, setCostPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  // Anagraphic-button state: navigating === we triggered productsAPI.get
  // to resolve a course_id and haven't navigated yet. UI disables the
  // button + shows a spinner so a fast double-click doesn't fire twice.
  const [navigating, setNavigating] = useState(false);

  useEffect(() => {
    if (!open || !productId) return;
    let cancelled = false;
    setLoading(true);
    setErrorMsg(null);

    Promise.all([
      productCatalogAPI.getProductMetric(productId).catch(() => null),
      productCatalogAPI.previewSavedCost(productId).catch(() => null),
    ])
      .then(([metricRes, costRes]) => {
        if (cancelled) return;
        setMetric(metricRes?.data || null);
        setCostPreview(costRes?.data || null);
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorMsg(err?.response?.data?.detail || err?.message || 'unknown');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, productId]);

  const displayName = metric?.product_name || summary?.product_name || t('profile.title');
  const sku = metric?.sku || summary?.sku;
  const category = metric?.category || summary?.category;

  // item_type: prefer the freshly-loaded metric (authoritative), fall
  // back to the row passed from the table for instant render before
  // the network call resolves. Defaults to undefined (button disabled
  // until known) rather than 'physical' to avoid a wrong-dispatch race.
  const itemType = metric?.item_type ?? summary?.item_type;
  const anagraphicLabelKey = useMemo(() => _anagraphicLabelKey(itemType), [itemType]);

  // Click handler for the anagraphic button.
  //
  // For 6 of the 7 product types the destination is computable
  // synchronously from item_type + product_id (resolved by
  // _resolveAnagraphicHref). For type=course we need course_id which
  // lives in product.metadata.course_id and is NOT carried by the
  // product_metrics_collection payload — so we do a single
  // productsAPI.get(productId) at click time and navigate once we have
  // the id. The lookup is only paid by course-type products, on click.
  const onAnagraphicClick = async () => {
    if (!productId || !itemType || navigating) return;

    if (itemType === 'course') {
      setNavigating(true);
      try {
        const { data } = await productsAPI.get(productId);
        const courseId = data?.metadata?.course_id || null;
        window.location.href = _resolveAnagraphicHref(itemType, productId, courseId);
      } catch (e) {
        // Network error or product missing: still land on /courses so
        // the admin isn't dead-ended on the slide. They can pick the
        // course manually from the list.
        window.location.href = '/courses';
      } finally {
        // Note: setNavigating(false) is reached only if navigation
        // fails to happen — window.location.href usually triggers a
        // full page unload before this line runs.
        setNavigating(false);
      }
      return;
    }

    // Synchronous dispatch for the 6 other types.
    window.location.href = _resolveAnagraphicHref(itemType, productId, null);
  };

  // Disable the button until we know enough to dispatch correctly.
  // - No productId: we can't navigate anywhere meaningful
  // - itemType unknown: we'd land on the wrong page (or the legacy hub)
  // - navigating: prevents double-clicks during the course_id lookup
  const anagraphicDisabled = !productId || !itemType || navigating;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md w-full overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-base pr-8">{displayName}</SheetTitle>
          {(sku || category) && (
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              {sku && <span>SKU: {sku}</span>}
              {sku && category && <span>·</span>}
              {category && <span>{category}</span>}
            </div>
          )}
        </SheetHeader>

        <div className="mt-4 space-y-5">
          {/* Action — open the dashboard/editor for the resolved item_type.
              Dispatches via productDashboardPath() (utils/productPaths.js)
              so the merchant lands on the *new* per-type dashboard
              (PhysicalDashboardPage, ServiceDashboardPage, …) instead of
              the deprecated generic editor at /products?product_id=. */}
          <div>
            <Button
              variant="outline"
              size="sm"
              className="text-xs w-full"
              onClick={onAnagraphicClick}
              disabled={anagraphicDisabled}
            >
              {navigating ? (
                <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
              ) : (
                <ExternalLink className="h-3 w-3 mr-1.5" />
              )}
              {t(anagraphicLabelKey)}
            </Button>
          </div>

          {/* Performance metrics block */}
          <Section title={t('profile.performance_section')}>
            {loading ? (
              <PerfSkeleton />
            ) : metric ? (
              <PerfBlock metric={metric} currency={currency} t={t} />
            ) : errorMsg ? (
              <ErrorRow msg={errorMsg} />
            ) : (
              <NoDataRow text={t('table.no_data')} />
            )}
          </Section>

          {/* Cost composition block */}
          <Section title={t('profile.cost_breakdown_section')}>
            {loading ? (
              <PerfSkeleton />
            ) : costPreview && costPreview.decomposition?.length > 0 ? (
              <CostBlock preview={costPreview} currency={currency} t={t} />
            ) : (
              <NoDataRow text={t('profile.cost_breakdown_empty')} />
            )}
          </Section>
        </div>
      </SheetContent>
    </Sheet>
  );
}


// ── Subcomponents ────────────────────────────────────────────────────────────

function Section({ title, children }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

function PerfBlock({ metric, currency, t }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <Cell label={t('table.revenue')}
            value={formatCurrency(metric.total_revenue, currency)} />
      <Cell label={t('table.cost')}
            value={metric.total_cost > 0 ? formatCurrency(metric.total_cost, currency) : 'N/D'} />
      <Cell label={t('table.margin')}
            value={metric.margin_pct != null ? `${metric.margin_pct.toFixed(1)}%` : 'N/D'} />
      <Cell label={t('table.units')}
            value={metric.total_units_sold ?? 0} />
    </div>
  );
}

function CostBlock({ preview, currency, t }) {
  const { value, decomposition } = preview;
  return (
    <div className="space-y-2">
      {decomposition.map((row, i) => (
        <div key={i}
             className={`flex items-center justify-between text-xs rounded px-2 py-1.5 ${
               row.failed ? 'bg-amber-50' : 'bg-muted/30'
             }`}>
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className="text-[10px] uppercase shrink-0 text-muted-foreground min-w-[60px]">
              {_typeLabel(row.type, t)}
            </span>
            <span className="truncate">{row.label}</span>
          </div>
          <div className="text-right shrink-0">
            {row.failed ? (
              <span className="text-amber-700 inline-flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                <span className="text-[10px]">{t('profile.cost_unconfigured')}</span>
              </span>
            ) : (
              <span className="font-semibold tabular-nums">
                {formatCurrency(row.contribution, currency)}
              </span>
            )}
          </div>
        </div>
      ))}
      {value != null && (
        <div className="border-t pt-2 flex items-center justify-between text-sm font-semibold">
          <span>{t('table.cost')}</span>
          <span className="tabular-nums">{formatCurrency(value, currency)}</span>
        </div>
      )}
    </div>
  );
}

function Cell({ label, value }) {
  return (
    <div className="rounded-md bg-muted/30 p-2">
      <div className="text-[10px] uppercase text-muted-foreground tracking-wide">{label}</div>
      <div className="text-sm font-semibold tabular-nums mt-0.5">{value}</div>
    </div>
  );
}

function PerfSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-2">
      {[1,2,3,4].map(i => <Skeleton key={i} className="h-12" />)}
    </div>
  );
}

function ErrorRow({ msg }) {
  return (
    <div className="rounded bg-red-50 border border-red-200 p-2 text-xs text-red-700 flex items-start gap-1">
      <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
      <span>{msg}</span>
    </div>
  );
}

function NoDataRow({ text }) {
  return (
    <p className="text-xs text-muted-foreground italic py-2 text-center bg-muted/20 rounded">
      {text}
    </p>
  );
}
