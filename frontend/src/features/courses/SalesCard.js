/**
 * SalesCard — commerce-side controls for a Course (Release 4 follow-up).
 *
 * Owns the paired Product fields that drive the storefront:
 *   - unit_price + currency
 *   - store_ids (which storefronts expose the course)
 *   - is_published (the go-live switch)
 *   - transaction_mode (direct | request | approval)
 *   - landing URL preview (per assigned store)
 *
 * The Product is fetched via GET /api/courses/:id/product (fetch-or-create
 * on the backend — so the card is always populated even for legacy courses
 * that existed before the auto-create endpoint).
 *
 * UX rules:
 *   - Publish is GATED: cannot go online with no price OR no video GUIDs
 *     OR no Bunny config. Server would accept it but we refuse at the
 *     UI layer with clear inline hints so the merchant knows why.
 *   - Slug changes here propagate to the Course slug server-side (same
 *     landing URL pattern for both sides of the pair).
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { coursesAPI } from '../../api/courses';
import { storesAPI } from '../../api/stores';


/* ─── Helpers ─────────────────────────────────────────────────────────────── */

function countVideosReady(course) {
  const lessons = (course?.modules || []).flatMap(m => m.lessons || []);
  const withVideo = lessons.filter(l => !!l.bunny_video_guid);
  return { total: lessons.length, withVideo: withVideo.length };
}


/* ─── Component ───────────────────────────────────────────────────────────── */

export default function SalesCard({ course, courseId, onCourseSlugChanged }) {
  const { t } = useTranslation('products');
  const [product, setProduct] = useState(null);
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [draft, setDraft] = useState({
    unit_price: '',
    currency: 'EUR',
    transaction_mode: 'direct',
    is_published: false,
    store_ids: [],
    slug: '',
  });

  const TRANSACTION_MODES = useMemo(() => ([
    { k: 'direct',   l: t('dashboards.course.salesCard.modeDirect') },
    { k: 'request',  l: t('dashboards.course.salesCard.modeRequest') },
    { k: 'approval', l: t('dashboards.course.salesCard.modeApproval') },
  ]), [t]);

  // Fetch the paired Product + stores list (parallel).
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storesRes] = await Promise.all([
        coursesAPI.getLinkedProduct(courseId),
        storesAPI.list().catch(() => ({ data: [] })),
      ]);
      const p = prodRes.data || {};
      setProduct(p);
      setStores(Array.isArray(storesRes.data) ? storesRes.data : (storesRes.data?.stores || []));
      setDraft({
        unit_price: p.unit_price ?? '',
        currency: p.currency || 'EUR',
        transaction_mode: p.transaction_mode || 'direct',
        is_published: !!p.is_published,
        store_ids: Array.isArray(p.store_ids) ? p.store_ids : [],
        slug: p.slug || course?.slug || '',
      });
    } catch (e) {
      toast.error(t('dashboards.course.salesCard.loadError'));
    } finally {
      setLoading(false);
    }
  }, [courseId, course?.slug, t]);

  useEffect(() => { load(); }, [load]);

  // Dirty detection — shows/hides the "Salva" button.
  const dirty = useMemo(() => {
    if (!product) return false;
    return (
      String(draft.unit_price) !== String(product.unit_price ?? '')
      || draft.currency !== (product.currency || 'EUR')
      || draft.transaction_mode !== (product.transaction_mode || 'direct')
      || draft.is_published !== !!product.is_published
      || JSON.stringify([...(draft.store_ids || [])].sort())
         !== JSON.stringify([...(product.store_ids || [])].sort())
      || draft.slug !== (product.slug || '')
    );
  }, [draft, product]);

  // Publish gates. We compute truthfully so the UI shows the real blocker.
  const { total: totalLessons, withVideo: lessonsWithVideo } = countVideosReady(course);
  const blockers = [];
  if (!draft.unit_price || Number(draft.unit_price) <= 0) {
    blockers.push({ k: 'price', msg: t('dashboards.course.salesCard.blockerPrice') });
  }
  if (totalLessons === 0) {
    blockers.push({ k: 'lessons', msg: t('dashboards.course.salesCard.blockerLessons') });
  } else if (lessonsWithVideo === 0) {
    blockers.push({ k: 'videos', msg: t('dashboards.course.salesCard.blockerVideos') });
  }
  if (!course?.is_active) {
    blockers.push({ k: 'active', msg: t('dashboards.course.salesCard.blockerActive') });
  }
  const canPublish = blockers.length === 0;

  const handleSave = async () => {
    if (!product) return;

    // Refuse publish when any blocker exists (defensive — the submit
    // button disables but belt-and-suspenders).
    if (draft.is_published && !canPublish) {
      toast.error(t('dashboards.course.salesCard.toastPublishBlocked'));
      return;
    }

    setSaving(true);
    try {
      const payload = {
        unit_price: draft.unit_price === '' ? null : Number(draft.unit_price),
        currency: draft.currency,
        transaction_mode: draft.transaction_mode,
        is_published: draft.is_published,
        store_ids: draft.store_ids,
      };
      if (draft.slug && draft.slug !== product.slug) {
        payload.slug = draft.slug.trim();
      }
      const { data } = await coursesAPI.updateLinkedProduct(courseId, payload);
      setProduct(data);
      toast.success(draft.is_published ? t('dashboards.course.salesCard.toastPublishedOk') : t('dashboards.course.salesCard.toastSaved'));
      if (payload.slug && onCourseSlugChanged) onCourseSlugChanged(payload.slug);
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.salesCard.toastSaveError'));
    } finally {
      setSaving(false);
    }
  };

  const toggleStore = (storeId) => {
    setDraft(d => {
      const next = new Set(d.store_ids || []);
      if (next.has(storeId)) next.delete(storeId);
      else next.add(storeId);
      return { ...d, store_ids: Array.from(next) };
    });
  };

  /* ─── Landing URL preview ────────────────────────────────────────────── */
  // Resolves to /co/:store_slug/:product_slug. Picks the first assigned
  // store, falling back to any published store of the org so the admin
  // always sees something useful even before assigning stores.
  const landingStore = useMemo(() => {
    if (!stores.length) return null;
    const assigned = (draft.store_ids || []).map(id => stores.find(s => s.id === id)).filter(Boolean);
    if (assigned.length > 0) return assigned[0];
    return stores.find(s => s.is_published) || stores[0];
  }, [stores, draft.store_ids]);

  const landingUrl = landingStore?.slug && draft.slug
    ? `/co/${landingStore.slug}/${draft.slug}`
    : null;

  /* ─── Render ─────────────────────────────────────────────────────────── */

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            {t('dashboards.course.salesCard.title')}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {t('dashboards.course.salesCard.subtitle')}
          </p>
        </div>
        <StatusBadge isPublished={!!product?.is_published} />
      </div>

      {loading ? (
        <div className="text-sm text-gray-500 py-6 text-center">{t('dashboards.course.loading')}</div>
      ) : !product ? (
        <div className="text-sm text-red-700">
          {t('dashboards.course.salesCard.productMissing')}
        </div>
      ) : (
        <>
          {/* Prezzo + valuta */}
          <div className="grid grid-cols-[1fr_110px] gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
                {t('dashboards.course.salesCard.priceLabel')}
              </label>
              <input
                type="number"
                min={0}
                step={0.01}
                value={draft.unit_price}
                onChange={e => setDraft({ ...draft, unit_price: e.target.value })}
                placeholder={t('dashboards.course.salesCard.pricePlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
                {t('dashboards.course.salesCard.currencyLabel')}
              </label>
              <select
                value={draft.currency}
                onChange={e => setDraft({ ...draft, currency: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="CHF">CHF</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
          </div>

          {/* Transaction mode */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
              {t('dashboards.course.salesCard.modeLabel')}
            </label>
            <select
              value={draft.transaction_mode}
              onChange={e => setDraft({ ...draft, transaction_mode: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              {TRANSACTION_MODES.map(m => (
                <option key={m.k} value={m.k}>{m.l}</option>
              ))}
            </select>
          </div>

          {/* Store assignment */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
              {t('dashboards.course.salesCard.storesLabel')}
            </label>
            {stores.length === 0 ? (
              <p className="text-xs text-gray-500">
                {t('dashboards.course.salesCard.storesEmpty')}
              </p>
            ) : (
              <div className="space-y-1">
                {stores.map(s => (
                  <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(draft.store_ids || []).includes(s.id)}
                      onChange={() => toggleStore(s.id)}
                      className="rounded border-gray-300"
                    />
                    <span className="flex-1">{s.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      s.is_published ? 'bg-green-100 text-green-900' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {s.is_published ? t('dashboards.course.salesCard.storePublished') : t('dashboards.course.salesCard.storeDraft')}
                    </span>
                  </label>
                ))}
                {draft.store_ids.length === 0 && (
                  <p className="text-[11px] text-amber-700 mt-1">
                    {t('dashboards.course.salesCard.noneSelectedWarn')}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Landing URL preview */}
          {landingUrl && (
            <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2">
              <p className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                {t('dashboards.course.salesCard.urlLabel')}
              </p>
              <p className="text-xs font-mono text-gray-800 mt-0.5 truncate">{landingUrl}</p>
              {landingStore && !landingStore.is_published && (
                <p className="text-[11px] text-amber-700 mt-1">
                  {t('dashboards.course.salesCard.storeDraftWarn', { name: landingStore.name })}
                </p>
              )}
            </div>
          )}

          {/* Publish toggle + blockers */}
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.is_published}
                disabled={!canPublish && !draft.is_published}
                onChange={e => setDraft({ ...draft, is_published: e.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-semibold text-gray-900">
                {t('dashboards.course.salesCard.publishLabel')}
              </span>
            </label>
            {!canPublish && (
              <div className="text-[11px] text-amber-800 pl-6">
                <p className="font-semibold mb-0.5">{t('dashboards.course.salesCard.publishBlockers')}</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  {blockers.map(b => <li key={b.k}>{b.msg}</li>)}
                </ul>
              </div>
            )}
          </div>

          {/* Save button */}
          <div className="flex items-center justify-end pt-1">
            <button
              type="button"
              onClick={handleSave}
              disabled={!dirty || saving}
              className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? t('dashboards.course.lesson.saving') : dirty ? t('dashboards.course.salesCard.saveDirty') : t('dashboards.course.salesCard.saveClean')}
            </button>
          </div>
        </>
      )}
    </section>
  );
}


function StatusBadge({ isPublished }) {
  const { t } = useTranslation('products');
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${
      isPublished ? 'bg-green-100 text-green-900' : 'bg-gray-200 text-gray-700'
    }`}>
      {isPublished ? t('dashboards.course.salesCard.statusOnline') : t('dashboards.course.salesCard.statusOffline')}
    </span>
  );
}
