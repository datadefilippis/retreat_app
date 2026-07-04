/**
 * EventWizard — guided 4-step event creation (G2).
 *
 * Route: /events/new   (ProtectedRoute)
 *
 * Replaces the generic "New product" dialog for event_ticket creation.
 * Before this wizard a merchant had to:
 *   1. Open Products, click "New product"
 *   2. Fill a giant dialog shared with physical/service/rental
 *   3. Save the product
 *   4. Re-open it, scroll to "Date", add occurrence with capacity
 *   5. Expand "Dettagli evento (facoltativo)" for venue / cover / long
 *      description
 *   6. Realize ticket tiers aren't configurable from the UI at all
 *
 * Total ≈ 8 steps across 2 pages. The wizard collapses that into 4
 * focused tabs and creates product + occurrence + tiers atomically
 * via POST /api/event-occurrences/wizard.
 *
 * Tabs:
 *   1. Cosa offri   — name, description, cover image, base price
 *   2. Quando/dove  — start/end, capacity, venue + address + lat/lng
 *   3. Biglietti    — tiers with +/- rows, up/down reorder, validation
 *   4. Pubblica     — summary + publish toggle + Crea event
 *
 * Keeps the landing (E3) / dashboard (E6) / check-in (E5) surfaces
 * untouched — on success we navigate straight to /events/:occurrence_id
 * where the merchant can see the dashboard they just created.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import { toast } from 'sonner';
import { eventOccurrencesAPI } from '../../api/eventOccurrences';
import { storesAPI } from '../../api/stores';
import { productsAPI } from '../../api';
import FieldEditorList from './components/FieldEditorList';
import { pruneFieldConfigs } from './components/fieldConfigUtils';
import StripeRequiredAlert from '../../components/StripeRequiredAlert';
import { useCurrency, useAuth } from '../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../lib/utils';
// Wave 1 (W1.S5/Phase 2.4) — additive cost composition editor.
// For event tickets the cost usually represents venue/speaker amortised
// over expected attendance — declared manually is the most common
// configuration.
import CostSourceEditor from '../products/components/CostSourceEditor';

// 2026-05-20 — Hardening helpers (audit fix wave). EventWizard is the
// highest-risk surface (4 steps, multiple uploads, blob preview leak,
// complex tier validation) so every helper from the suite is wired in.
import { PriceInput } from '../../components/ui/PriceInput';
import { UnsavedChangesDialog } from '../../components/ui/UnsavedChangesDialog';
import { DraftRestoreBanner } from '../../components/ui/DraftRestoreBanner';
import { useSubmitLock } from '../../hooks/useSubmitLock';
import { useUnsavedChangesPrompt } from '../../hooks/useUnsavedChangesPrompt';
import { useWizardDraft } from '../../hooks/useWizardDraft';
import { useAbortableUpload } from '../../hooks/useAbortableUpload';
import { useObjectURL } from '../../hooks/useObjectURL';
import { showImageUploadFailedToast } from '../../lib/imageUploadFailedToast';


// ── Tab configuration ─────────────────────────────────────────────────────
// Tabs are addressed by stable `key`. Visible labels are resolved at
// render time via t('wizards.event.tabs.<key>') so translations stay
// in the JSON catalog.

const TABS = [
  { key: 'base',    n: 1 },
  { key: 'where',   n: 2 },
  { key: 'tickets', n: 3 },
  { key: 'publish', n: 4 },
];


// ── Validation helpers ────────────────────────────────────────────────────

function validateBase(state, t) {
  const errors = {};
  if (!state.name?.trim()) errors.name = t('wizards.common.validation.nameRequired');
  if (state.unit_price !== '' && state.unit_price !== null
      && state.unit_price !== undefined && Number(state.unit_price) < 0) {
    errors.unit_price = t('wizards.event.validation.priceNegative');
  }
  return errors;
}

function validateWhere(state, t) {
  const errors = {};
  if (!state.start_at) errors.start_at = t('wizards.event.validation.startRequired');
  if (state.end_at && state.start_at && state.end_at < state.start_at) {
    errors.end_at = t('wizards.event.validation.endAfterStart');
  }
  if (state.capacity !== '' && state.capacity !== null
      && state.capacity !== undefined && Number(state.capacity) < 1) {
    errors.capacity = t('wizards.event.validation.capacityMin');
  }
  if (state.latitude !== '' && state.latitude !== null
      && state.latitude !== undefined
      && (Number(state.latitude) < -90 || Number(state.latitude) > 90)) {
    errors.latitude = t('wizards.event.validation.latitudeRange');
  }
  if (state.longitude !== '' && state.longitude !== null
      && state.longitude !== undefined
      && (Number(state.longitude) < -180 || Number(state.longitude) > 180)) {
    errors.longitude = t('wizards.event.validation.longitudeRange');
  }
  return errors;
}

function validateTiers(tiers, occCapacity, t) {
  const errors = {};
  const rowErrors = [];
  let tierSum = 0;
  tiers.forEach((tier, idx) => {
    const row = {};
    if (!tier.label?.trim()) row.label = t('wizards.common.validation.nameRequired');
    if (tier.price === '' || tier.price === null || tier.price === undefined
        || Number.isNaN(Number(tier.price)) || Number(tier.price) < 0) {
      row.price = t('wizards.common.validation.priceInvalid');
    }
    if (tier.capacity !== '' && tier.capacity !== null && tier.capacity !== undefined
        && Number(tier.capacity) < 1) {
      row.capacity = t('wizards.event.validation.tierMin');
    }
    rowErrors[idx] = row;
    const cap = Number(tier.capacity);
    if (Number.isFinite(cap) && cap > 0) tierSum += cap;
  });
  // Soft warning: tier capacity sum vs occurrence capacity
  let capWarning = null;
  const occCap = Number(occCapacity);
  if (Number.isFinite(occCap) && occCap > 0 && tierSum > occCap) {
    capWarning = t('wizards.event.validation.capacityWarning', { tierSum, occCap });
  }
  errors.rows = rowErrors;
  if (capWarning) errors.warning = capWarning;
  return errors;
}


// ── Main component ───────────────────────────────────────────────────────

export default function EventWizard() {
  const orgCurrency = useCurrency();
  const navigate = useNavigate();
  const location = useLocation();
  const { t, i18n } = useTranslation('products');
  const [activeTab, setActiveTab] = useState('base');
  const [submitting, setSubmitting] = useState(false);

  // G6: Duplicate prefill hand-off. EventDashboardPage.handleDuplicate
  // navigates here with `state: { prefillData, sourceLabel }` where
  // prefillData is the backend's wizard-ready payload. We hydrate the
  // form on mount and clear the router state so a manual refresh
  // lands on a clean wizard instead of re-filling.
  const prefillRef = useRef(location.state?.prefillData || null);
  const [sourceLabel] = useState(location.state?.sourceLabel || null);

  const toInput = (v) => (v === null || v === undefined ? '' : String(v));

  // Tab 1 — base (seeded from prefill when present)
  const [base, setBase] = useState(() => {
    const p = prefillRef.current?.product || {};
    return {
      name: p.name || '',
      description: p.description || '',
      image_url: p.image_url || '',
      unit_price: toInput(p.unit_price),
      transaction_mode: p.transaction_mode || 'direct',
    };
  });

  // Pending image files — uploaded after wizard creates the product_id / occurrence_id
  // 2026-05-20 — Blob preview URLs are now managed by useObjectURL, which
  // automatically revokes them on unmount and on file replacement. The
  // previous setImageFilePreview/setCoverFilePreview path leaked one
  // blob URL per file picked (≈300KB-3MB held in memory per leak).
  const [imageFile, setImageFile] = useState(null);
  const imageFilePreview = useObjectURL(imageFile);
  const [coverFile, setCoverFile] = useState(null);
  const coverFilePreview = useObjectURL(coverFile);

  // Tab 2 — where
  const [where, setWhere] = useState(() => {
    const o = prefillRef.current?.occurrence || {};
    return {
      start_at: o.start_at || '',
      end_at: o.end_at || '',
      capacity: toInput(o.capacity),
      venue_name: o.venue_name || '',
      address: o.address || '',
      city: o.city || '',
      postal_code: o.postal_code || '',
      country: o.country || 'IT',
      latitude: toInput(o.latitude),
      longitude: toInput(o.longitude),
      cover_image_url: o.cover_image_url || '',
    };
  });

  // Tab 3 — tiers
  const [tiers, setTiers] = useState(() => {
    const src = prefillRef.current?.tiers || [];
    return src.map((t, i) => ({
      label: t.label || '',
      description: t.description || '',
      price: toInput(t.price),
      capacity: toInput(t.capacity),
      sort_order: t.sort_order ?? i,
    }));
  });

  // Wave 1 (W1.S5/Phase 2.4) — cost composition. Hydrated from prefill
  // when duplicating an existing event, otherwise null.
  const [costSource, setCostSource] = useState(() =>
    prefillRef.current?.product?.cost_source || null
  );

  // F1 (Onda 8) — require per-ticket attendee details (name/email/phone)
  // at checkout. When enabled, the storefront collects N holder forms if
  // quantity > 1 and each issued ticket gets its own holder + personal email.
  const [requiresAttendeeDetails, setRequiresAttendeeDetails] = useState(() =>
    prefillRef.current?.product?.metadata?.requires_attendee_details ?? false
  );
  // F2 (Onda 9) — email/phone required-ness + custom fields
  const [requireAttendeeEmail, setRequireAttendeeEmail] = useState(() =>
    prefillRef.current?.product?.metadata?.require_attendee_email ?? true
  );
  const [requireAttendeePhone, setRequireAttendeePhone] = useState(() =>
    prefillRef.current?.product?.metadata?.require_attendee_phone ?? false
  );
  const [attendeeFieldsCfg, setAttendeeFieldsCfg] = useState(() =>
    prefillRef.current?.product?.metadata?.attendee_fields || []
  );
  const [orderFieldsCfg, setOrderFieldsCfg] = useState(() =>
    prefillRef.current?.product?.metadata?.order_fields || []
  );
  // F4 Onda 11 — per-event Terms & Conditions override. Empty = use the
  // store-level default (if enabled on the store).
  const [termsContent, setTermsContent] = useState(() =>
    prefillRef.current?.product?.metadata?.terms_content || ''
  );

  // Tab 4 — publish + store assignment
  const [longDescription, setLongDescription] = useState(() =>
    prefillRef.current?.occurrence?.long_description || ''
  );
  const [publishNow, setPublishNow] = useState(false);
  // F4: store assignment — which storefronts carry this event product
  const [storeIds, setStoreIds] = useState(() =>
    prefillRef.current?.product?.store_ids || []
  );
  const [availableStores, setAvailableStores] = useState([]);
  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      setAvailableStores(res.data?.stores || []);
    } catch { /* stores optional */ }
  }, []);
  useEffect(() => { loadStores(); }, [loadStores]);

  // G6: clear location.state once hydrated so a manual refresh of
  // /events/new lands on a clean form instead of the duplicate data.
  useEffect(() => {
    if (prefillRef.current) {
      window.history.replaceState({}, '', window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── 2026-05-20 — Hardening hooks ────────────────────────────────────
  const formData = useMemo(() => ({
    base, where, tiers, costSource,
    requiresAttendeeDetails, requireAttendeeEmail, requireAttendeePhone,
    attendeeFieldsCfg, orderFieldsCfg, termsContent,
    longDescription, publishNow, storeIds,
  }), [
    base, where, tiers, costSource,
    requiresAttendeeDetails, requireAttendeeEmail, requireAttendeePhone,
    attendeeFieldsCfg, orderFieldsCfg, termsContent,
    longDescription, publishNow, storeIds,
  ]);

  const applyDraft = useCallback((d) => {
    if (!d || typeof d !== 'object') return;
    if (d.base) setBase(d.base);
    if (d.where) setWhere(d.where);
    if (Array.isArray(d.tiers)) setTiers(d.tiers);
    if ('costSource' in d) setCostSource(d.costSource);
    if ('requiresAttendeeDetails' in d) setRequiresAttendeeDetails(!!d.requiresAttendeeDetails);
    if ('requireAttendeeEmail' in d) setRequireAttendeeEmail(!!d.requireAttendeeEmail);
    if ('requireAttendeePhone' in d) setRequireAttendeePhone(!!d.requireAttendeePhone);
    if (Array.isArray(d.attendeeFieldsCfg)) setAttendeeFieldsCfg(d.attendeeFieldsCfg);
    if (Array.isArray(d.orderFieldsCfg)) setOrderFieldsCfg(d.orderFieldsCfg);
    if ('termsContent' in d) setTermsContent(d.termsContent);
    if ('longDescription' in d) setLongDescription(d.longDescription);
    if ('publishNow' in d) setPublishNow(!!d.publishNow);
    if (Array.isArray(d.storeIds)) setStoreIds(d.storeIds);
  }, []);

  const initialFormDataRef = useRef(null);
  useEffect(() => {
    if (initialFormDataRef.current === null) {
      initialFormDataRef.current = JSON.stringify(formData);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [submittedSuccessfully, setSubmittedSuccessfully] = useState(false);
  const isDirty = useMemo(() => {
    if (submittedSuccessfully) return false;
    if (initialFormDataRef.current === null) return false;
    return JSON.stringify(formData) !== initialFormDataRef.current
      || imageFile !== null || coverFile !== null;
  }, [formData, imageFile, coverFile, submittedSuccessfully]);

  const submitLock = useSubmitLock();
  const { blocker } = useUnsavedChangesPrompt(isDirty);

  const { user } = useAuth();
  const scopeKey = user?.id || user?.email || 'anonymous';
  const draft = useWizardDraft({
    wizardKey: 'event-create',
    scopeKey,
    formData,
    setFormData: applyDraft,
  });

  // Two independent uploaders so a slow cover upload doesn't cancel the
  // product image upload (or vice versa).
  const productImageUpload = useAbortableUpload();
  const coverImageUpload = useAbortableUpload();

  // Validation — per tab
  const errorsBase = useMemo(() => validateBase(base, t), [base, t]);
  const errorsWhere = useMemo(() => validateWhere(where, t), [where, t]);
  const errorsTiers = useMemo(() => validateTiers(tiers, where.capacity, t), [tiers, where.capacity, t]);

  const baseValid = Object.keys(errorsBase).length === 0;
  const whereValid = Object.keys(errorsWhere).length === 0;
  const tiersValid = errorsTiers.rows.every(r => !r || Object.keys(r).length === 0);
  const allValid = baseValid && whereValid && tiersValid;

  const tabHasErrors = {
    base: !baseValid,
    where: !whereValid,
    tickets: !tiersValid,
    publish: !allValid,
  };

  const currentTabIdx = TABS.findIndex(t => t.key === activeTab);
  const goToTab = (key) => setActiveTab(key);
  const nextTab = () => {
    const next = TABS[currentTabIdx + 1];
    if (next) setActiveTab(next.key);
  };
  const prevTab = () => {
    const prev = TABS[currentTabIdx - 1];
    if (prev) setActiveTab(prev.key);
  };

  // ── Tier operations ─────────────────────────────────────────────────
  const addTier = () => {
    setTiers(prev => [...prev, {
      label: '', description: '', price: '', capacity: '', sort_order: prev.length,
    }]);
  };
  const removeTier = (idx) => {
    setTiers(prev => prev.filter((_, i) => i !== idx).map((t, i) => ({ ...t, sort_order: i })));
  };
  const updateTier = (idx, patch) => {
    setTiers(prev => prev.map((t, i) => i === idx ? { ...t, ...patch } : t));
  };
  const moveTier = (idx, delta) => {
    setTiers(prev => {
      const next = [...prev];
      const target = idx + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next.map((t, i) => ({ ...t, sort_order: i }));
    });
  };

  // G6: HTML5 native drag & drop reorder. Tracks the source index in
  // state rather than dataTransfer to avoid serialization quirks.
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);
  const onTierDragStart = (idx) => (e) => {
    setDragIdx(idx);
    // Firefox requires setData to initiate drag
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', String(idx)); } catch {}
  };
  const onTierDragOver = (idx) => (e) => {
    e.preventDefault();  // required to allow drop
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIdx !== idx) setDragOverIdx(idx);
  };
  const onTierDragEnd = () => { setDragIdx(null); setDragOverIdx(null); };
  const onTierDrop = (idx) => (e) => {
    e.preventDefault();
    const from = dragIdx;
    setDragIdx(null); setDragOverIdx(null);
    if (from === null || from === idx) return;
    setTiers(prev => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(idx, 0, moved);
      return next.map((t, i) => ({ ...t, sort_order: i }));
    });
  };

  // ── Submit ───────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!allValid || submitting) return;
    // 2026-05-20 — atomic ref-based lock against fast double-click.
    if (!submitLock.tryLock()) return;
    setSubmitting(true);
    try {
      const payload = {
        product: {
          name: base.name.trim(),
          description: base.description?.trim() || null,
          image_url: base.image_url?.trim() || null,
          unit_price: base.unit_price !== '' ? Number(base.unit_price) : null,
          price_mode: 'fixed',
          transaction_mode: base.transaction_mode,
          // Keep product visibility in sync with the publish toggle so the
          // merchant has one mental model: "Pubblica subito" controls both the
          // product's catalog listing AND the first occurrence's status. This
          // mirrors ServiceWizard/ReservationWizard and avoids the trap where a
          // draft occurrence hides the product on the storefront even though the
          // merchant thought they'd published it.
          is_published: publishNow,
          store_ids: storeIds,
          metadata: {
            // F1 (Onda 8) — when true, the storefront checkout requires N
            // name+email+phone entries (one per seat) and each ticket is
            // issued with its own holder + receives a personal email.
            requires_attendee_details: requiresAttendeeDetails,
            // F2 (Onda 9) — per-field required-ness + custom fields
            require_attendee_email: requireAttendeeEmail,
            require_attendee_phone: requireAttendeePhone,
            attendee_fields: pruneFieldConfigs(attendeeFieldsCfg),
            order_fields: pruneFieldConfigs(orderFieldsCfg),
            // F4 (Onda 11) — optional per-event T&C override (markdown).
            // Empty → fallback to store-level T&C at checkout.
            terms_content: termsContent?.trim() || null,
          },
          // Wave 1 (W1.S5/Phase 2.4) — additive cost composition. Null
          // when unconfigured. Backend resolver returns margin=N/D for
          // such products.
          cost_source: costSource,
        },
        occurrence: {
          start_at: where.start_at,
          end_at: where.end_at || null,
          capacity: where.capacity !== '' ? Number(where.capacity) : null,
          status: publishNow ? 'published' : 'draft',
          venue_name: where.venue_name?.trim() || null,
          address: where.address?.trim() || null,
          city: where.city?.trim() || null,
          postal_code: where.postal_code?.trim() || null,
          country: where.country?.trim() || null,
          latitude: where.latitude !== '' ? Number(where.latitude) : null,
          longitude: where.longitude !== '' ? Number(where.longitude) : null,
          cover_image_url: where.cover_image_url?.trim() || null,
          long_description: longDescription?.trim() || null,
        },
        tiers: tiers.map((t, i) => ({
          label: t.label.trim(),
          description: t.description?.trim() || null,
          price: Number(t.price),
          capacity: t.capacity !== '' ? Number(t.capacity) : null,
          sort_order: i,
        })),
      };

      const res = await eventOccurrencesAPI.wizardCreate(payload);

      // Upload product image + cover image after creation (IDs only exist post-submit).
      // 2026-05-20 — Abortable uploads + persistent retry toasts.
      const productId = res.data?.product_id;
      const occurrenceId = res.data?.occurrence_id;

      if (imageFile && productId) {
        const fileToUpload = imageFile;
        try {
          await productImageUpload.run((signal) =>
            productsAPI.uploadImage(productId, fileToUpload, { signal }),
          );
        } catch {
          showImageUploadFailedToast({
            t,
            context: t('wizards.event.validation.uploadProductImage'),
            onRetry: async () => {
              try {
                await productsAPI.uploadImage(productId, fileToUpload);
                toast.success(t('wizards.common.imageUpload.retrySuccess', {
                  defaultValue: 'Immagine caricata correttamente.',
                }));
              } catch {
                showImageUploadFailedToast({ t, context: base.name });
              }
            },
          });
        }
      }
      if (coverFile && occurrenceId) {
        const fileToUpload = coverFile;
        try {
          await coverImageUpload.run((signal) =>
            eventOccurrencesAPI.uploadCoverImage(occurrenceId, fileToUpload, { signal }),
          );
        } catch {
          showImageUploadFailedToast({
            t,
            context: t('wizards.event.validation.uploadCoverImage'),
            onRetry: async () => {
              try {
                await eventOccurrencesAPI.uploadCoverImage(occurrenceId, fileToUpload);
                toast.success(t('wizards.common.imageUpload.retrySuccess', {
                  defaultValue: 'Immagine caricata correttamente.',
                }));
              } catch {
                showImageUploadFailedToast({ t, context: base.name });
              }
            },
          });
        }
      }

      // 2026-05-20 — Clear draft + suppress unsaved-changes prompt
      // before the post-create navigate.
      draft.discard();
      setSubmittedSuccessfully(true);
      toast.success(t('wizards.event.createdToast'));
      // Jump straight to the dashboard the merchant just created
      navigate(`/events/${occurrenceId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('wizards.event.validation.creationFailed'));
    } finally {
      setSubmitting(false);
      submitLock.unlock();
    }
  };

  // ── Render helpers ───────────────────────────────────────────────────
  const fieldError = (msg) => msg && (
    <p className="text-xs text-red-700 mt-1">{msg}</p>
  );

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        {/* Back bar — prominent top strip so the merchant always knows
            they can return to the Products hub without losing context. */}
        <div className="border-b border-gray-100 bg-gray-50">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-2">
            <Link
              to="/products?type=event_ticket"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              {t('wizards.event.back')}
            </Link>
          </div>
        </div>

        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
              {sourceLabel ? t('wizards.event.duplicateTitle') : t('wizards.event.title')}
            </h1>
            {sourceLabel && (
              <p className="text-[11px] text-gray-500 mt-0.5">
                <Trans
                  i18nKey="wizards.event.duplicateBanner"
                  ns="products"
                  values={{ source: sourceLabel }}
                  components={[<span key="0" className="font-medium text-gray-700" />]}
                />
              </p>
            )}
          </div>
          <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
            {t('wizards.common.stepCounter', { current: currentTabIdx + 1, total: TABS.length })}
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pb-3 flex gap-1 overflow-x-auto">
          {TABS.map((tab, i) => {
            const done = i < currentTabIdx && !tabHasErrors[tab.key];
            const active = tab.key === activeTab;
            const err = i < currentTabIdx && tabHasErrors[tab.key];
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => goToTab(tab.key)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap ${
                  active
                    ? 'bg-gray-900 text-white'
                    : err
                      ? 'bg-red-100 text-red-800 border border-red-200'
                      : done
                        ? 'bg-green-100 text-green-900'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="tabular-nums">{tab.n}</span>
                <span>{t(`wizards.event.tabs.${tab.key}`)}</span>
                {err && <span aria-hidden>!</span>}
                {done && <span aria-hidden>✓</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* 2026-05-20 — Draft restore banner — visible only if a saved
            <24h draft exists. EventWizard is the longest of the 5
            wizards so the autosave delta is especially valuable here. */}
        {draft.hasDraft && (
          <DraftRestoreBanner
            savedAt={draft.savedAt}
            onRestore={draft.restore}
            onDiscard={draft.discard}
          />
        )}

        {/* ── TAB 1: Cosa offri ─────────────────────────────────────── */}
        {activeTab === 'base' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.event.base.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.event.base.subtitle')}</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.base.nameLabel')}</label>
              <input
                type="text" value={base.name}
                onChange={e => setBase({ ...base, name: e.target.value })}
                maxLength={255}
                placeholder={t('wizards.event.base.namePlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
              {fieldError(errorsBase.name)}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.base.descriptionLabel')}</label>
              <textarea
                value={base.description}
                onChange={e => setBase({ ...base, description: e.target.value })}
                rows={2} maxLength={2000}
                placeholder={t('wizards.event.base.descriptionPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.base.imageLabel')}</label>
                {/* File picker — uploaded right after wizard creates the product */}
                <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900 transition-colors">
                  <span>📁 {imageFile ? imageFile.name : t('wizards.event.base.imageFileLabel')}</span>
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp"
                    className="hidden"
                    onChange={e => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      // 2026-05-20 — useObjectURL handles the blob URL
                      // lifecycle (create + revoke) automatically.
                      setImageFile(file);
                      setBase(prev => ({ ...prev, image_url: '' }));
                      e.target.value = '';
                    }}
                  />
                </label>
                {/* URL fallback */}
                <input
                  type="url" value={base.image_url}
                  onChange={e => {
                    setBase({ ...base, image_url: e.target.value });
                    // 2026-05-20 — useObjectURL revokes automatically when imageFile becomes null.
                    if (e.target.value) { setImageFile(null); }
                  }}
                  maxLength={500}
                  placeholder={t('wizards.common.imageUrlPlaceholder')}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {(imageFilePreview || base.image_url) && (
                  <img
                    src={imageFilePreview || base.image_url}
                    alt=""
                    className="mt-2 h-16 w-full object-cover rounded-md border"
                  />
                )}
                <p className="text-[11px] text-gray-500 mt-1">
                  {t('wizards.event.base.imageHint')}
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.base.priceLabel')}</label>
                {/* 2026-05-20 — locale-aware PriceInput (accepts "10,50"). */}
                <PriceInput
                  value={base.unit_price}
                  onValueChange={(_n, raw) => setBase({ ...base, unit_price: raw })}
                  min={0}
                  decimals={2}
                  placeholder={t('wizards.event.base.pricePlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  {t('wizards.event.base.priceHint')}
                </p>
                {fieldError(errorsBase.unit_price)}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.base.modeLabel')}</label>
              <div className="flex gap-2">
                {[
                  { v: 'direct',  labelKey: 'wizards.event.base.modeDirect' },
                  { v: 'request', labelKey: 'wizards.event.base.modeRequest' },
                ].map(opt => (
                  <button
                    key={opt.v} type="button"
                    onClick={() => setBase({ ...base, transaction_mode: opt.v })}
                    className={`flex-1 rounded-md border px-3 py-2 text-xs font-medium text-left ${
                      base.transaction_mode === opt.v
                        ? 'border-gray-900 bg-gray-50 text-gray-900'
                        : 'border-gray-300 text-gray-600 hover:border-gray-500'
                    }`}
                  >{t(opt.labelKey)}</button>
                ))}
              </div>
              <StripeRequiredAlert whenTransactionMode={base.transaction_mode} />
            </div>
          </div>
        )}

        {/* ── TAB 2: Quando e dove ──────────────────────────────────── */}
        {activeTab === 'where' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.event.where.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.event.where.subtitle')}</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.startLabel')}</label>
                <input
                  type="datetime-local" value={where.start_at}
                  onChange={e => setWhere({ ...where, start_at: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsWhere.start_at)}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.endLabel')}</label>
                <input
                  type="datetime-local" value={where.end_at}
                  onChange={e => setWhere({ ...where, end_at: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsWhere.end_at)}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.capacityLabel')}</label>
              <input
                type="number" min="1" value={where.capacity}
                onChange={e => setWhere({ ...where, capacity: e.target.value })}
                placeholder={t('wizards.event.where.capacityPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
              {fieldError(errorsWhere.capacity)}
            </div>

            <div className="border-t pt-3 space-y-3">
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t('wizards.event.where.locationHeader')}</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.venueNameLabel')}</label>
                  <input
                    type="text" value={where.venue_name}
                    onChange={e => setWhere({ ...where, venue_name: e.target.value })}
                    maxLength={150} placeholder={t('wizards.event.where.venueNamePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.addressLabel')}</label>
                  <input
                    type="text" value={where.address}
                    onChange={e => setWhere({ ...where, address: e.target.value })}
                    maxLength={255} placeholder={t('wizards.event.where.addressPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.cityLabel')}</label>
                  <input
                    type="text" value={where.city}
                    onChange={e => setWhere({ ...where, city: e.target.value })}
                    maxLength={100} placeholder={t('wizards.event.where.cityPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.postalCodeLabel')}</label>
                  <input
                    type="text" value={where.postal_code}
                    onChange={e => setWhere({ ...where, postal_code: e.target.value })}
                    maxLength={20} placeholder={t('wizards.event.where.postalCodePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.countryLabel')}</label>
                  <input
                    type="text" value={where.country}
                    onChange={e => setWhere({ ...where, country: e.target.value.toUpperCase() })}
                    maxLength={2} placeholder={t('wizards.event.where.countryPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm uppercase focus:border-gray-900 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.latitudeLabel')}</label>
                  <input
                    type="number" step="any" value={where.latitude}
                    onChange={e => setWhere({ ...where, latitude: e.target.value })}
                    placeholder={t('wizards.event.where.latitudePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  {fieldError(errorsWhere.latitude)}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.longitudeLabel')}</label>
                  <input
                    type="number" step="any" value={where.longitude}
                    onChange={e => setWhere({ ...where, longitude: e.target.value })}
                    placeholder={t('wizards.event.where.longitudePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  {fieldError(errorsWhere.longitude)}
                </div>
              </div>
              <p className="text-[11px] text-gray-500 -mt-1">
                {t('wizards.event.where.coordsHint')}
              </p>
            </div>

            <div className="border-t pt-3">
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.coverLabel')}</label>
              <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900 transition-colors">
                <span>📁 {coverFile ? coverFile.name : t('wizards.event.where.coverFileLabel')}</span>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    // 2026-05-20 — useObjectURL handles blob lifecycle.
                    setCoverFile(file);
                    setWhere(prev => ({ ...prev, cover_image_url: '' }));
                    e.target.value = '';
                  }}
                />
              </label>
              <input
                type="url" value={where.cover_image_url}
                onChange={e => {
                  setWhere({ ...where, cover_image_url: e.target.value });
                  if (e.target.value) { setCoverFile(null); }
                }}
                maxLength={500}
                placeholder={t('wizards.event.where.coverUrlPlaceholder')}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
              {(coverFilePreview || where.cover_image_url) && (
                <img src={coverFilePreview || where.cover_image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
              )}
            </div>
          </div>
        )}

        {/* ── TAB 3: Biglietti ──────────────────────────────────────── */}
        {activeTab === 'tickets' && (
          <div className="space-y-4">

          {/* F1: Attendee details policy — separate card above tiers */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={requiresAttendeeDetails}
                onChange={e => setRequiresAttendeeDetails(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
              />
              <div className="flex-1">
                <span className="block text-sm font-semibold text-gray-900">
                  {t('wizards.event.tickets.requireDetailsTitle')}
                </span>
                <span className="block text-xs text-gray-500 mt-0.5">
                  {requiresAttendeeDetails
                    ? t('wizards.event.tickets.requireDetailsDescOn')
                    : t('wizards.event.tickets.requireDetailsDescOff')}
                </span>
              </div>
            </label>

            {/* F2: contacts required-ness + custom fields (visible when policy is ON) */}
            {requiresAttendeeDetails && (
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  {t('wizards.event.tickets.baseFieldsHeading')}
                </p>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-900">{t('wizards.event.tickets.nameField')}</span>
                  <span className="text-xs text-gray-500">{t('wizards.event.tickets.alwaysRequired')}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-900">{t('wizards.event.tickets.emailField')}</span>
                  <label className="flex items-center gap-2 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={requireAttendeeEmail}
                      onChange={e => setRequireAttendeeEmail(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span>{t('wizards.event.tickets.emailRequired')}</span>
                  </label>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-900">{t('wizards.event.tickets.phoneField')}</span>
                  <label className="flex items-center gap-2 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={requireAttendeePhone}
                      onChange={e => setRequireAttendeePhone(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span>{t('wizards.event.tickets.phoneRequired')}</span>
                  </label>
                </div>
                {!requireAttendeeEmail && (
                  <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2 py-1">
                    {t('wizards.event.tickets.noEmailWarning')}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* F2: Custom fields (only when F1 toggle is ON) */}
          {requiresAttendeeDetails && (
            <FieldEditorList
              fields={attendeeFieldsCfg}
              onChange={setAttendeeFieldsCfg}
              title={t('wizards.event.tickets.attendeeFieldsTitle')}
              subtitle={t('wizards.event.tickets.attendeeFieldsSubtitle')}
              emptyHint={t('wizards.event.tickets.attendeeFieldsEmpty')}
            />
          )}

          <FieldEditorList
            fields={orderFieldsCfg}
            onChange={setOrderFieldsCfg}
            title={t('wizards.event.tickets.orderFieldsTitle')}
            subtitle={t('wizards.event.tickets.orderFieldsSubtitle')}
            emptyHint={t('wizards.event.tickets.orderFieldsEmpty')}
          />

          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-900">{t('wizards.event.tickets.tiersTitle')}</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t('wizards.event.tickets.tiersSubtitle')}
                </p>
              </div>
              <button
                type="button" onClick={addTier}
                className="shrink-0 text-xs font-semibold rounded-md bg-gray-900 text-white px-3 py-1.5 hover:bg-gray-800"
              >{t('wizards.event.tickets.addTierBtn')}</button>
            </div>

            {errorsTiers.warning && (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900">
                ⚠️ {errorsTiers.warning}
              </div>
            )}

            {tiers.length === 0 ? (
              <div className="rounded-lg border-2 border-dashed border-gray-200 p-6 text-center">
                <p className="text-sm text-gray-600">{t('wizards.event.tickets.noTiersTitle')}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {base.unit_price
                    ? t('wizards.event.tickets.noTiersDescWithPrice', { price: base.unit_price })
                    : t('wizards.event.tickets.noTiersDescNoPrice')}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {tiers.map((tier, idx) => {
                  const rowErr = errorsTiers.rows[idx] || {};
                  const isDragging = dragIdx === idx;
                  const isDropTarget = dragOverIdx === idx && dragIdx !== null && dragIdx !== idx;
                  return (
                    <div
                      key={idx}
                      draggable
                      onDragStart={onTierDragStart(idx)}
                      onDragOver={onTierDragOver(idx)}
                      onDrop={onTierDrop(idx)}
                      onDragEnd={onTierDragEnd}
                      className={`rounded-lg border p-3 space-y-2 transition ${
                        isDragging ? 'opacity-40 border-gray-300'
                          : isDropTarget ? 'border-gray-900 bg-gray-50'
                          : 'border-gray-200'
                      }`}
                    >
                      <div className="grid grid-cols-12 gap-2">
                        <div className="col-span-12 sm:col-span-5 flex items-start gap-2">
                          <span
                            className="mt-5 text-gray-400 cursor-grab active:cursor-grabbing select-none"
                            title={t('wizards.event.tickets.dragHint')}
                            aria-hidden
                          >⋮⋮</span>
                          <div className="flex-1 min-w-0">
                            <label className="block text-[11px] text-gray-600">{t('wizards.event.tickets.tierNameLabel')}</label>
                            <input
                              type="text" value={tier.label}
                              onChange={e => updateTier(idx, { label: e.target.value })}
                              maxLength={80} placeholder={t('wizards.event.tickets.tierNamePlaceholder')}
                              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                            />
                            {fieldError(rowErr.label)}
                          </div>
                        </div>
                        <div className="col-span-6 sm:col-span-3">
                          <label className="block text-[11px] text-gray-600">{t('wizards.event.tickets.tierPriceLabel')}</label>
                          {/* 2026-05-20 — Locale-aware PriceInput per tier. */}
                          <PriceInput
                            value={tier.price}
                            onValueChange={(_n, raw) => updateTier(idx, { price: raw })}
                            min={0}
                            decimals={2}
                            placeholder={t('wizards.event.tickets.tierPricePlaceholder')}
                            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                          {fieldError(rowErr.price)}
                        </div>
                        <div className="col-span-6 sm:col-span-3">
                          <label className="block text-[11px] text-gray-600">{t('wizards.event.tickets.tierCapacityLabel')}</label>
                          <input
                            type="number" min="1" max="1000000" value={tier.capacity}
                            onChange={e => updateTier(idx, { capacity: e.target.value })}
                            placeholder={t('wizards.event.tickets.tierCapacityPlaceholder')}
                            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                          {fieldError(rowErr.capacity)}
                        </div>
                        <div className="col-span-12 sm:col-span-1 flex sm:flex-col gap-1 items-end justify-end sm:pt-4">
                          <button
                            type="button" onClick={() => moveTier(idx, -1)}
                            disabled={idx === 0}
                            title={t('wizards.event.tickets.tierMoveUp')}
                            className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                          >↑</button>
                          <button
                            type="button" onClick={() => moveTier(idx, 1)}
                            disabled={idx === tiers.length - 1}
                            title={t('wizards.event.tickets.tierMoveDown')}
                            className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                          >↓</button>
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] text-gray-600">{t('wizards.event.tickets.tierDescLabel')}</label>
                        <input
                          type="text" value={tier.description}
                          onChange={e => updateTier(idx, { description: e.target.value })}
                          maxLength={500}
                          placeholder={t('wizards.event.tickets.tierDescPlaceholder')}
                          className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                        />
                      </div>
                      <div className="flex justify-end">
                        <button
                          type="button" onClick={() => removeTier(idx)}
                          className="text-[11px] text-red-700 hover:underline"
                        >{t('wizards.event.tickets.tierRemove')}</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* W1.S5/Phase 2.4 — Cost composition. Optional for events
              (typical configuration: a manual component for venue +
              speaker cost amortised over expected attendance). */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
            <div>
              <span className="text-sm font-medium text-gray-900">
                {t('product_cost:section.title', 'Costo del prodotto')}
              </span>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('product_cost:section.subtitle', 'Definisci come calcolare il margine per questo prodotto.')}
              </p>
            </div>
            <CostSourceEditor
              value={costSource}
              onChange={setCostSource}
            />
          </div>
          </div>
        )}

        {/* ── TAB 4: Pubblica ──────────────────────────────────────── */}
        {activeTab === 'publish' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.event.publish.longDescTitle')}</h2>
              <p className="text-xs text-gray-500">
                {t('wizards.event.publish.longDescDescPrefix')}<code>##</code>{t('wizards.event.publish.longDescDescSuffix')}
                <code> {t('wizards.event.publish.longDescBoldNote')}</code>, <code>{t('wizards.event.publish.longDescItalicNote')}</code>, <code>{t('wizards.event.publish.longDescListNote')}</code>.
              </p>
              <textarea
                value={longDescription}
                onChange={e => setLongDescription(e.target.value)}
                rows={8} maxLength={5000}
                placeholder={t('wizards.event.publish.longDescPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-gray-900 focus:outline-none resize-y"
              />
            </div>

            {/* F4 Onda 11 — per-event Terms & Conditions override */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.event.publish.termsTitle')}</h2>
              <p className="text-xs text-gray-500">
                {t('wizards.event.publish.termsDesc')}
              </p>
              <textarea
                value={termsContent}
                onChange={e => setTermsContent(e.target.value)}
                rows={6} maxLength={20000}
                placeholder={t('wizards.event.publish.termsPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-gray-900 focus:outline-none resize-y"
              />
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.summary.title')}</h2>
              <dl className="text-sm grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.name')}</dt><dd className="font-medium">{base.name || t('wizards.common.summary.emptyValue')}</dd></div>
                <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.mode')}</dt><dd className="font-medium">{base.transaction_mode === 'direct' ? t('wizards.common.summary.modeDirect') : t('wizards.common.summary.modeRequest')}</dd></div>
                <div><dt className="text-gray-500 text-xs">{t('wizards.event.publish.summaryDate')}</dt><dd className="font-medium">{where.start_at ? new Date(where.start_at).toLocaleString(i18n.language) : t('wizards.common.summary.emptyValue')}</dd></div>
                <div><dt className="text-gray-500 text-xs">{t('wizards.event.publish.summaryCapacity')}</dt><dd className="font-medium">{where.capacity || t('wizards.event.publish.summaryCapacityUnlimited')}</dd></div>
                <div className="sm:col-span-2"><dt className="text-gray-500 text-xs">{t('wizards.event.publish.summaryLocation')}</dt><dd className="font-medium">{[where.venue_name, where.city].filter(Boolean).join(' · ') || t('wizards.common.summary.emptyValue')}</dd></div>
                <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.basePrice')}</dt><dd className="font-medium">{base.unit_price !== '' ? fmtCurrency(Number(base.unit_price), orgCurrency) : t('wizards.common.summary.emptyValue')}</dd></div>
                <div><dt className="text-gray-500 text-xs">{t('wizards.event.publish.summaryTiersLabel')}</dt><dd className="font-medium">{tiers.length || t('wizards.event.publish.summaryTiersNone')}</dd></div>
              </dl>
            </div>

            {/* F4 — Store assignment. Canonical pattern shared with
                ServiceWizard + ReservationWizard: checkbox "Tutti gli store"
                + one checkbox per store. Always visible so the merchant
                has a clear signal of where the event will appear. */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-2">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.distribution.title')}</h2>
              {availableStores.length <= 1 ? (
                <>
                  <p className="text-xs text-gray-500">
                    {t('wizards.event.publish.distributionDesc')}
                  </p>
                  <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                    <span aria-hidden>✓</span>
                    <span>
                      {t('wizards.common.distribution.visibleAutoPrefix')} <strong>{availableStores[0]?.name || t('wizards.common.distribution.allStoresFallback')}</strong>
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs text-gray-500">{t('wizards.event.publish.distributionMultiDesc')}</p>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!storeIds.length}
                      onChange={() => setStoreIds([])}
                      className="rounded border-gray-300"
                    />
                    <span className={!storeIds.length ? 'font-medium' : 'text-gray-500'}>
                      {t('wizards.common.distribution.allStoresLabel')}
                    </span>
                  </label>
                  {availableStores.map(s => {
                    const isSpecific = storeIds.length > 0;
                    const checked = isSpecific && storeIds.includes(s.id);
                    return (
                      <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => setStoreIds(prev =>
                            prev.includes(s.id)
                              ? prev.filter(id => id !== s.id)
                              : [...prev, s.id]
                          )}
                          className="rounded border-gray-300"
                        />
                        <span>{s.name}</span>
                      </label>
                    );
                  })}
                </>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox" checked={publishNow}
                  onChange={e => setPublishNow(e.target.checked)}
                  className="mt-1"
                />
                <span className="text-sm">
                  <span className="font-semibold text-gray-900">{t('wizards.event.publish.publishToggleTitle')}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('wizards.event.publish.publishToggleDesc')}
                  </p>
                </span>
              </label>
            </div>

            {!allValid && (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900">
                {t('wizards.event.publish.validationErrorBanner')}
              </div>
            )}
          </div>
        )}

        {/* ── Footer navigation ─────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-2 pt-2">
          <button
            type="button" onClick={prevTab}
            disabled={currentTabIdx === 0}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:border-gray-900 disabled:opacity-40"
          >{t('wizards.common.back')}</button>

          {activeTab !== 'publish' ? (
            <button
              type="button" onClick={nextTab}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >{t('wizards.common.next')}</button>
          ) : (
            <button
              type="button" onClick={handleSubmit}
              disabled={!allValid || submitting}
              className="rounded-md bg-gray-900 text-white px-5 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
            >{submitting ? t('wizards.common.creating') : (publishNow ? t('wizards.event.publishCta') : t('wizards.common.saveDraft'))}</button>
          )}
        </div>
      </div>

      {/* 2026-05-20 — Confirm dialog when an in-app navigation is
          attempted while the form is dirty. The beforeunload listener
          handles native tab-close in parallel. */}
      <UnsavedChangesDialog
        open={blocker?.state === 'blocked'}
        onConfirm={() => blocker?.proceed?.()}
        onCancel={() => blocker?.reset?.()}
      />
    </div>
  );
}
