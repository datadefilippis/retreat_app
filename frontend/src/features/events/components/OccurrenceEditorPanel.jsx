/**
 * OccurrenceEditorPanel — list + create form for the occurrences of a
 * single event_ticket product.
 *
 * Why this file exists
 * --------------------
 * For an event-type product (item_type="event_ticket"), the merchant
 * needs to add successive occurrences (date #2, date #3, …) AFTER the
 * initial wizard run that created the product + first occurrence.
 * Today this is the only surface in the app that lets them do that.
 *
 * Before this extraction the same JSX + state lived inline inside the
 * legacy Dialog of ``ProductsPage.js`` (lines ~1262-1513). That Dialog
 * is slated for removal (see ``docs/PRODUCTS_ARCHITECTURE.md`` Phase 4)
 * and pulling this panel out is the prerequisite — otherwise we'd lose
 * the only path to "add another date" for an existing event product.
 *
 * Extraction policy
 * -----------------
 * This panel is a **strictly faithful** extraction of the inline JSX:
 *
 *   - Same fields, same Tailwind classes, same i18n keys.
 *   - Same API calls (eventOccurrencesAPI.create / update).
 *   - Same status-change optimistic pattern (no rollback on error —
 *     pre-existing behaviour, documented as Bug A in the PR-2 audit;
 *     fix deferred to a dedicated follow-up so this PR stays a no-op
 *     in terms of behaviour).
 *
 * Architecture: controlled component
 * ----------------------------------
 * The parent owns the ``occurrences`` array because two callers consume
 * it: the panel itself, AND a sibling warning ("no occurrences yet" in
 * the profile-readiness card, ProductsPage:959). The panel can never
 * be the source of truth or those two views would drift.
 *
 * The parent passes its setter as ``onOccurrencesChange`` so the panel
 * can use the familiar functional-update pattern (``prev => [...prev,
 * next]``) without any reducer ceremony. ``occForm`` is purely local
 * because nobody outside the panel needs to read or write it.
 *
 * Reset behaviour: ``useEffect([productId])`` clears ``occForm`` when
 * the parent switches to a different product. Radix Dialog unmounts
 * children on close, so this is defensive (the effect also covers the
 * future case where the panel is rendered outside a Dialog, e.g. on a
 * dedicated route in a later refactor).
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Badge } from '../../../components/ui/badge';
import { eventOccurrencesAPI } from '../../../api/eventOccurrences';


// TODO: dedupe to features/events/lib/constants.js — duplicated from
// ProductsPage.js for now to keep PR-2 a strictly faithful extraction.
// The follow-up move is trivial (this is the only other user) and is
// best done together with the legacy Dialog removal (PR-4).
const OCCURRENCE_STATUS = {
  draft: { key: 'draft', className: 'bg-gray-100 text-gray-700' },
  published: { key: 'published', className: 'bg-emerald-100 text-emerald-700' },
  closed: { key: 'closed', className: 'bg-amber-100 text-amber-700' },
  cancelled: { key: 'cancelled', className: 'bg-red-100 text-red-700' },
};


// Default shape for the "new occurrence" form. Centralised here so the
// "+ Add new" button doesn't repeat the literal object inline like it
// did in the legacy Dialog. The ``showDetails`` flag drives the
// collapsible venue sub-form below the basics.
const NEW_OCC_FORM_DEFAULTS = {
  start_at: '',
  end_at: '',
  location: '',
  capacity: '',
  price_override: '',
  notes: '',
  // E2: structured event details (all optional)
  venue_name: '',
  address: '',
  city: '',
  postal_code: '',
  country: '',
  latitude: '',
  longitude: '',
  map_url: '',
  cover_image_url: '',
  long_description: '',
  showDetails: false,
};


export default function OccurrenceEditorPanel({
  productId,
  occurrences,
  onOccurrencesChange,
}) {
  const { t } = useTranslation(['catalog', 'products']);

  // Form state for the "new occurrence" composer. null = closed,
  // object = open with the in-progress draft. Local to the panel: no
  // sibling needs to read or write it.
  const [occForm, setOccForm] = useState(null);

  // Reset the in-progress form whenever the parent switches product.
  // Defensive against future callers that don't unmount the panel
  // between products (today the Radix Dialog does, but we don't want
  // to rely on that contract).
  useEffect(() => {
    setOccForm(null);
  }, [productId]);

  // Defensive guard: the parent already gates rendering on
  // ``editing && form.item_type === 'event_ticket'``, but a misuse
  // (panel mounted without a productId) would crash the create handler.
  if (!productId) return null;

  // ── Handlers ────────────────────────────────────────────────────────────

  /** Open the new-occurrence composer with a clean draft. */
  const handleOpenNewForm = () => {
    setOccForm({ ...NEW_OCC_FORM_DEFAULTS });
  };

  /** Toggle the collapsible "venue details" sub-form inside the composer. */
  const handleToggleDetails = () => {
    setOccForm((f) => f ? { ...f, showDetails: !f.showDetails } : f);
  };

  /**
   * Status-change handler — fires on the inline <select> next to each
   * occurrence row. Pattern preserved verbatim from the legacy Dialog:
   * write to backend FIRST, then optimistically update the parent's
   * list. On error the list stays at its previous value (the API
   * never wrote, so we're consistent). The toast surfaces the failure
   * so the merchant can retry.
   */
  const handleStatusChange = async (occ, nextStatus) => {
    try {
      await eventOccurrencesAPI.update(occ.id, { status: nextStatus });
      onOccurrencesChange((prev) =>
        prev.map((o) => (o.id === occ.id ? { ...o, status: nextStatus } : o))
      );
    } catch {
      toast.error(t('catalog:occurrence_section.toast_status_error'));
    }
  };

  /**
   * Submit handler for the new-occurrence composer. Builds the payload
   * the way the legacy Dialog did — empty optional fields are
   * normalised to null so the backend keeps them unset rather than
   * storing empty strings.
   */
  const handleCreateOccurrence = async () => {
    try {
      const payload = {
        product_id: productId,
        start_at: occForm.start_at,
        end_at: occForm.end_at || null,
        location: occForm.location?.trim() || null,
        capacity: occForm.capacity ? parseInt(occForm.capacity, 10) : null,
        price_override: occForm.price_override ? parseFloat(occForm.price_override) : null,
        // E2 additions — only include when non-empty so the backend's
        // optional fields stay null rather than being stored as "".
        venue_name: occForm.venue_name?.trim() || null,
        address: occForm.address?.trim() || null,
        city: occForm.city?.trim() || null,
        postal_code: occForm.postal_code?.trim() || null,
        country: occForm.country?.trim() || null,
        latitude: occForm.latitude !== '' ? parseFloat(occForm.latitude) : null,
        longitude: occForm.longitude !== '' ? parseFloat(occForm.longitude) : null,
        cover_image_url: occForm.cover_image_url?.trim() || null,
        long_description: occForm.long_description?.trim() || null,
      };
      const res = await eventOccurrencesAPI.create(payload);
      onOccurrencesChange((prev) => [...prev, res.data]);
      setOccForm(null);
      toast.success(t('catalog:occurrence_section.toast_created'));
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t('catalog:occurrence_section.toast_create_error')
      );
    }
  };

  /** Cancel the in-progress form without saving. */
  const handleCancelForm = () => setOccForm(null);

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="border-t pt-3 space-y-2">
      {/* Header — section label + "+ Add new" trigger */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {t('catalog:occurrence_section.title')}
          </p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {t('catalog:occurrence_section.subtitle')}
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenNewForm}
          className="text-xs text-primary hover:underline"
        >
          {t('catalog:occurrence_section.add_new')}
        </button>
      </div>

      {/* Empty state — only when no occurrences AND no in-progress form */}
      {occurrences.length === 0 && !occForm && (
        <p className="text-xs text-muted-foreground">
          {t('catalog:occurrence_section.empty')}
        </p>
      )}

      {/* Occurrence list */}
      {occurrences.map((occ) => {
        const statusMeta = OCCURRENCE_STATUS[occ.status] || OCCURRENCE_STATUS.draft;
        return (
          <div
            key={occ.id}
            className="flex items-center justify-between rounded-lg border p-2 text-xs"
          >
            <div>
              <p className="font-medium">
                {occ.start_at?.replace('T', ' ').slice(0, 16)}
              </p>
              {occ.location && (
                <p className="text-muted-foreground">{occ.location}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {occ.capacity && (
                <span className="text-muted-foreground">
                  {occ.capacity} {t('catalog:occurrence_section.seats')}
                </span>
              )}
              {/* E6: quick link to the unified event dashboard */}
              <Link
                to={`/events/${occ.id}`}
                className="text-[10px] text-primary hover:underline font-medium"
                title={t('products:form.openEventDashboard')}
              >
                {t('products:form.manageLink')}
              </Link>
              <Badge className={`text-[10px] ${statusMeta.className}`}>
                {t(`catalog:occurrence_status.${statusMeta.key}`)}
              </Badge>
              <select
                value={occ.status || 'draft'}
                onChange={(e) => handleStatusChange(occ, e.target.value)}
                className="rounded border px-1 py-0.5 text-[10px] bg-background"
              >
                <option value="draft">{t('catalog:occurrence_status.draft')}</option>
                <option value="published">{t('catalog:occurrence_status.published')}</option>
                <option value="closed">{t('catalog:occurrence_status.closed')}</option>
                <option value="cancelled">{t('catalog:occurrence_status.cancelled')}</option>
              </select>
            </div>
          </div>
        );
      })}

      {/* New occurrence composer */}
      {occForm && (
        <div className="rounded-lg border p-3 space-y-2 bg-muted/30">
          {/* Row 1: start + end */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-xs">{t('catalog:occurrence_section.form_start')} *</Label>
              <Input
                type="datetime-local"
                value={occForm.start_at}
                onChange={(e) => setOccForm({ ...occForm, start_at: e.target.value })}
                className="text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">{t('catalog:occurrence_section.form_end')}</Label>
              <Input
                type="datetime-local"
                value={occForm.end_at}
                onChange={(e) => setOccForm({ ...occForm, end_at: e.target.value })}
                className="text-xs"
              />
            </div>
          </div>

          {/* Row 2: location + capacity + price_override */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <Label className="text-xs">{t('catalog:occurrence_section.form_location')}</Label>
              <Input
                value={occForm.location}
                onChange={(e) => setOccForm({ ...occForm, location: e.target.value })}
                className="text-xs"
                placeholder={t('catalog:occurrence_section.form_location_placeholder')}
              />
            </div>
            <div>
              <Label className="text-xs">{t('catalog:occurrence_section.form_capacity')}</Label>
              <Input
                type="number"
                min="1"
                value={occForm.capacity}
                onChange={(e) => setOccForm({ ...occForm, capacity: e.target.value })}
                className="text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">{t('catalog:occurrence_section.form_price_override')}</Label>
              <Input
                type="number"
                step="0.01"
                value={occForm.price_override}
                onChange={(e) => setOccForm({ ...occForm, price_override: e.target.value })}
                className="text-xs"
              />
            </div>
          </div>

          {/* E2: collapsible "venue details" sub-form */}
          <div className="border-t pt-2 mt-1">
            <button
              type="button"
              onClick={handleToggleDetails}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <span className="flex items-center gap-1.5">
                <span className={`inline-block transition-transform ${occForm.showDetails ? 'rotate-90' : ''}`}>▸</span>
                {t('products:venue.title')}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {t('products:form.fieldsCounter', {
                  count: [
                    occForm.venue_name,
                    occForm.address,
                    occForm.cover_image_url,
                    occForm.long_description,
                  ].filter(Boolean).length,
                })}
              </span>
            </button>

            {occForm.showDetails && (
              <div className="mt-3 space-y-3">
                {/* Venue name + street address */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">{t('products:venue.venueName')}</Label>
                    <Input
                      value={occForm.venue_name}
                      onChange={(e) => setOccForm({ ...occForm, venue_name: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.venueNamePlaceholder')}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">{t('products:venue.address')}</Label>
                    <Input
                      value={occForm.address}
                      onChange={(e) => setOccForm({ ...occForm, address: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.addressPlaceholder')}
                    />
                  </div>
                </div>

                {/* City + postal + country (2-letter ISO) */}
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <Label className="text-xs">{t('products:venue.city')}</Label>
                    <Input
                      value={occForm.city}
                      onChange={(e) => setOccForm({ ...occForm, city: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.cityPlaceholder')}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">{t('products:venue.postalCode')}</Label>
                    <Input
                      value={occForm.postal_code}
                      onChange={(e) => setOccForm({ ...occForm, postal_code: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.postalCodePlaceholder')}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">{t('products:venue.country')}</Label>
                    <Input
                      value={occForm.country}
                      onChange={(e) => setOccForm({ ...occForm, country: e.target.value.toUpperCase() })}
                      className="text-xs uppercase"
                      maxLength={2}
                      placeholder={t('products:venue.countryPlaceholder')}
                    />
                  </div>
                </div>

                {/* Lat/lng — manual paste from Google Maps */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">{t('products:venue.latitude')}</Label>
                    <Input
                      type="number"
                      step="any"
                      value={occForm.latitude}
                      onChange={(e) => setOccForm({ ...occForm, latitude: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.latitudePlaceholder')}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">{t('products:venue.longitude')}</Label>
                    <Input
                      type="number"
                      step="any"
                      value={occForm.longitude}
                      onChange={(e) => setOccForm({ ...occForm, longitude: e.target.value })}
                      className="text-xs"
                      placeholder={t('products:venue.longitudePlaceholder')}
                    />
                  </div>
                </div>
                <p className="text-[10px] text-muted-foreground -mt-1">
                  {t('products:venue.coordsHint')}
                </p>

                {/* Cover image URL */}
                <div>
                  <Label className="text-xs">{t('products:venue.coverUrl')}</Label>
                  <Input
                    value={occForm.cover_image_url}
                    onChange={(e) => setOccForm({ ...occForm, cover_image_url: e.target.value })}
                    className="text-xs"
                    placeholder={t('products:venue.coverUrlPlaceholder')}
                  />
                </div>

                {/* Long description (Markdown-capable, 5000 char cap) */}
                <div>
                  <Label className="text-xs">{t('products:venue.longDescription')}</Label>
                  <textarea
                    value={occForm.long_description}
                    onChange={(e) => setOccForm({ ...occForm, long_description: e.target.value })}
                    rows={4}
                    className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs"
                    placeholder={t('products:venue.longDescriptionPlaceholder')}
                    maxLength={5000}
                  />
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {t('products:venue.markdownHint')}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Action row — Create disabled until start_at is set */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              disabled={!occForm.start_at}
              onClick={handleCreateOccurrence}
              className="px-3 py-1 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50"
            >
              {t('catalog:occurrence_section.form_create')}
            </button>
            <button
              type="button"
              onClick={handleCancelForm}
              className="px-3 py-1 rounded-md border text-xs"
            >
              {t('catalog:occurrence_section.form_cancel')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


