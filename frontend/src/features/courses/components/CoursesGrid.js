/**
 * CoursesGrid — admin grid of video course products.
 *
 * Mirrors DigitalsGrid (Release 3) so the admin sees video courses in
 * `/products?type=course` with the same look-and-feel as the other 5
 * product types. The "underlying" content entity (Course → modules →
 * lessons) keeps living in /courses/:id; this grid is purely the
 * commerce-side surface that lists Product(item_type='course').
 *
 * Click on a card → /courses/:course_id  (the existing CourseEditor
 * dashboard with all its tabs: Dati corso, Moduli/lezioni, Vendita,
 * Bunny, Iscritti). The course_id is derived from
 * `product.metadata.course_id` set at auto-create time by
 * routers/courses._ensure_linked_product (no extra round-trip).
 *
 * NEVER touches the existing course feature (CourseEditor, SalesCard,
 * BunnyConfigCard, EnrollmentsSection, the customer player flow,
 * /account/courses, the Bunny signed URL pipeline). Read-only on
 * `productsAPI.list()` + `coursesAPI.list()` for the lesson counts
 * + a single `productsAPI.update({is_published})` for the inline
 * status toggle.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { productsAPI } from '../../../api';
import { coursesAPI } from '../../../api/courses';
import { organizationsAPI } from '../../../api/organizations';
import { toast } from 'sonner';
import ProductCardBase from '../../products/components/ProductCardBase';
import BunnyManagerDialog from '../bunny-manager/BunnyManagerDialog';
import { useCurrency } from '../../../context/AuthContext';


// Presentational classes only — labels resolved at render time via t().
const STATUS_CFG = {
  published: { cls: 'bg-green-100 text-green-900' },
  draft:     { cls: 'bg-gray-100 text-gray-700' },
};


/**
 * StatusChip — toggle online/offline for the linked Product. The
 * backend SalesCard owns the proper publish-gate (price > 0, lessons,
 * Bunny config) — here we only refuse the optimistic toggle for the
 * obvious blockers (no price, no video) so the admin doesn't pay a
 * round-trip just to see a 4xx. The server stays the source of truth.
 */
function StatusChip({ isPublished, productId, onStatusChange, blockerLabel }) {
  const { t } = useTranslation('products');
  const cfg = isPublished ? STATUS_CFG.published : STATUS_CFG.draft;
  const [saving, setSaving] = useState(false);

  const toggle = async (e) => {
    e.stopPropagation();
    e.preventDefault();
    const next = !isPublished;
    if (next && blockerLabel) {
      toast.error(blockerLabel);
      return;
    }
    setSaving(true);
    try {
      await productsAPI.update(productId, { is_published: next });
      onStatusChange(productId, next);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('grids.common.statusChangeError');
      toast.error(String(msg));
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={saving}
      title={isPublished
        ? t('grids.common.toggleToOffline')
        : (blockerLabel ? blockerLabel : t('grids.common.toggleToOnline'))}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.cls} hover:opacity-90 ${saving ? 'opacity-60' : ''}`}
    >
      {isPublished ? t('grids.common.statusOnline') : t('grids.common.statusOffline')}
    </button>
  );
}


/**
 * CourseCard — one card in the grid. Reads from the Product (commerce
 * fields) + the joined Course doc (content fields: modules / lessons
 * / videos). The two come from separate endpoints — the parent merges
 * them and passes the joined object as `course` (may be null when the
 * link is missing for legacy or freshly-created products).
 */
function CourseCard({ product, course, orgSlug, onStatusChange }) {
  const orgCurrency = useCurrency();
  const { t } = useTranslation('products');
  const meta = product.metadata || {};
  // Cover image: prefer Course.cover_image_url (the admin sets it on
  // the content side); fall back to product.image_url. For a brand-new
  // course neither may be set → fallback emoji takes over.
  const hero = course?.cover_image_url || meta.cover_image_url || product.image_url;

  // Lesson stats — the headline of a course card.
  const modules = course?.modules || [];
  const allLessons = modules.flatMap(m => m.lessons || []);
  const lessonsTotal = allLessons.length;
  const lessonsWithVideo = allLessons.filter(l => !!l.bunny_video_guid).length;
  const totalDurationSec = allLessons.reduce((s, l) => s + (l.duration_seconds || 0), 0);

  // Overline string: structured snippet showing the most useful state
  // at a glance ("3 moduli · 12 lezioni · 4h · ⚠ 2 video mancanti").
  const parts = [];
  if (modules.length > 0) parts.push(t('grids.course.moduleCount', { count: modules.length }));
  if (lessonsTotal > 0) parts.push(t('grids.course.lessonCount', { count: lessonsTotal }));
  if (totalDurationSec > 0) {
    const mins = Math.round(totalDurationSec / 60);
    if (mins >= 60) {
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      parts.push(m === 0 ? `${h}h` : `${h}h ${m}m`);
    } else {
      parts.push(`${mins} min`);
    }
  }
  if (lessonsTotal > 0 && lessonsWithVideo < lessonsTotal) {
    parts.push(t('grids.course.videoMissingCount', { count: lessonsTotal - lessonsWithVideo }));
  } else if (lessonsTotal === 0) {
    parts.push(t('grids.course.noLessons'));
  }

  // Optimistic publish-gate blocker — covers the most common cases.
  // Authoritative gate is on the SalesCard inside CourseEditor; backend
  // accepts/refuses regardless of this UI hint.
  let blockerLabel = null;
  if (!product.unit_price || Number(product.unit_price) <= 0) {
    blockerLabel = t('grids.course.publishBlocker.noPrice');
  } else if (lessonsTotal === 0) {
    blockerLabel = t('grids.course.publishBlocker.noLessons');
  } else if (lessonsWithVideo === 0) {
    blockerLabel = t('grids.course.publishBlocker.noVideos');
  }

  // course_id is the canonical link from Product → Course content.
  // Set by routers/courses._ensure_linked_product on auto-create.
  const courseId = meta.course_id;
  const editorHref = courseId ? `/courses/${courseId}` : null;

  // Public landing preview — only meaningful when the product has a
  // slug AND the org has a published store to host it.
  const secondaryCta = product.slug && orgSlug
    ? {
        href: `/co/${encodeURIComponent(orgSlug)}/${product.slug}`,
        title: t('grids.course.previewLandingPublic'),
        label: '🔗',
      }
    : null;

  // Edge case: course_id missing on the product (rare — pre-fix legacy
  // rows). Render a clear "broken link" hint instead of letting the
  // admin click into a 404.
  if (!editorHref) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm">
        <div className="font-semibold text-amber-900 mb-1">{product.name || t('grids.common.noName')}</div>
        <p className="text-xs text-amber-800">
          ⚠️ {t('grids.course.broken.title')}{' '}
          <a href="/courses" className="underline font-semibold">{t('grids.course.broken.openCourses')}</a>{' '}
          {t('grids.course.broken.rebuildLink')}
        </p>
      </div>
    );
  }

  return (
    <ProductCardBase
      hero={{
        src: hero,
        // Indigo→blue gradient distinguishes courses from digitals
        // (teal), physical (orange), services (purple), reservations
        // (green). Picked to align with the 🎓 emoji + the "Vendita"
        // card accent already used in CourseEditor.
        gradientFrom: 'from-indigo-700',
        gradientTo: 'to-blue-500',
        fallbackEmoji: '🎓',
        typeBadge: t('grids.course.typeBadge'),
      }}
      href={editorHref}
      title={product.name || course?.title || t('grids.common.noName')}
      overline={parts.join(' · ')}
      description={product.description || course?.description}
      price={product.unit_price}
      currency={product.currency || orgCurrency}
      statusChip={
        <StatusChip
          isPublished={!!product.is_published}
          productId={product.id}
          onStatusChange={onStatusChange}
          blockerLabel={blockerLabel}
        />
      }
      secondaryCta={secondaryCta}
    />
  );
}


export default function CoursesGrid({ embedded = false, onCreateClick = null }) {
  const { t } = useTranslation('products');
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [videoFilter, setVideoFilter] = useState('');     // '' | 'with_videos' | 'missing_videos'
  const [products, setProducts] = useState([]);
  const [coursesById, setCoursesById] = useState({});
  const [orgSlug, setOrgSlug] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Bunny config state — surfaced as a header button + dialog so the
  // admin can configure the integration without leaving the grid.
  // Step 5 of the bunny consolidation: store the REAL verification
  // status (string from `last_verification_status` set by the backend
  // auto-verify hook) instead of a boolean derived from "fields are
  // filled in". Possible values: 'ok' | 'unauthorized' |
  // 'library_not_found' | 'network_error' | 'unknown' | 'not_configured'.
  const [bunnyStatus, setBunnyStatus] = useState('not_configured');
  const [bunnyDialogOpen, setBunnyDialogOpen] = useState(false);

  const handleStatusChange = useCallback((productId, isPublished) => {
    setProducts(prev => prev.map(p => p.id === productId ? { ...p, is_published: isPublished } : p));
  }, []);

  /**
   * Single load: pulls Products + Courses + Stores in parallel. The
   * Course join is needed for lesson count / duration / "missing video"
   * filter — those fields don't live on the Product. Bounded N+1 is
   * avoided by fetching the full course list once (capped at 500 by
   * the backend) and indexing by id.
   */
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { storesAPI } = await import('../../../api/stores');
      const [prodRes, coursesRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        coursesAPI.list({ activeOnly: false }).catch(() => ({ data: [] })),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);

      const all = prodRes.data || [];
      const courseProducts = all.filter(
        p => p.item_type === 'course' && p.is_active !== false,
      );
      setProducts(courseProducts);

      // Build the id→course map. coursesAPI.list() returns an array.
      const courseList = Array.isArray(coursesRes.data)
        ? coursesRes.data
        : (coursesRes.data?.courses || []);
      const map = {};
      for (const c of courseList) {
        if (c && c.id) map[c.id] = c;
      }
      setCoursesById(map);

      const publishedStore = (storesRes.data?.stores || []).find(s => s.is_published);
      setOrgSlug(publishedStore?.slug || null);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('grids.course.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Independent fetch for the Bunny status indicator on the header
  // button. Kept separate from the main load so it can be refreshed
  // cheaply after the dialog saves new credentials.
  //
  // Step 5: reads the persisted `last_verification_status` produced
  // by the backend auto-verify hook. Falls back to 'not_configured'
  // when the integration is missing OR for legacy orgs that haven't
  // been touched since the auto-verify hook went live (no status
  // field yet — they'll get 'unknown' once they next save).
  const refreshBunnyStatus = useCallback(async () => {
    try {
      const { data } = await organizationsAPI.getCurrent();
      const b = data?.integrations?.bunny;
      if (!b?.library_id || !b?.api_key) {
        setBunnyStatus('not_configured');
        return;
      }
      // Real status from backend, or 'unknown' for legacy orgs without
      // the status field populated yet (they'll resolve on next save).
      setBunnyStatus(b.last_verification_status || 'unknown');
    } catch {
      setBunnyStatus('not_configured');
    }
  }, []);

  useEffect(() => { load(); refreshBunnyStatus(); }, [load, refreshBunnyStatus]);

  /**
   * Computed list. Three filters layer: status (online/offline),
   * video-completeness (every lesson has a Bunny GUID or not), and
   * free-text search across name/description/category.
   */
  const filtered = useMemo(() => {
    let list = products;

    if (statusFilter === 'published') list = list.filter(p => p.is_published);
    else if (statusFilter === 'draft') list = list.filter(p => !p.is_published);

    if (videoFilter) {
      list = list.filter(p => {
        const c = coursesById[p.metadata?.course_id];
        const lessons = (c?.modules || []).flatMap(m => m.lessons || []);
        const total = lessons.length;
        const withVideo = lessons.filter(l => !!l.bunny_video_guid).length;
        if (videoFilter === 'with_videos') {
          return total > 0 && withVideo === total;
        }
        if (videoFilter === 'missing_videos') {
          return total === 0 || withVideo < total;
        }
        return true;
      });
    }

    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      list = list.filter(p => {
        const c = coursesById[p.metadata?.course_id];
        return (
          p.name?.toLowerCase().includes(needle) ||
          p.description?.toLowerCase().includes(needle) ||
          p.category?.toLowerCase().includes(needle) ||
          c?.title?.toLowerCase().includes(needle) ||
          c?.instructor_name?.toLowerCase().includes(needle)
        );
      });
    }
    return list;
  }, [products, coursesById, statusFilter, videoFilter, q]);

  const wrapperClass = embedded ? '' : 'min-h-screen bg-gray-50';

  // Header row with the Bunny config trigger + create button. Always
  // rendered (both embedded + standalone) because both flows benefit
  // from the access. Embedded mode skips the page title to stay
  // hosted within ProductsPage.
  //
  // Step 5: 3-way visual state instead of boolean. The "errore" branch
  // is the new addition — used to be a false-positive ✓ Connesso when
  // the admin entered wrong credentials.
  const bunnyButton = (() => {
    if (bunnyStatus === 'ok') {
      return {
        label: t('grids.course.bunny.connected'),
        title: t('grids.course.bunny.connectedTitle'),
        cls: 'bg-white border border-gray-300 text-gray-800 hover:bg-gray-50',
      };
    }
    if (bunnyStatus === 'not_configured') {
      return {
        label: t('grids.course.bunny.configure'),
        title: t('grids.course.bunny.configureTitle'),
        cls: 'bg-amber-50 border border-amber-300 text-amber-900 hover:bg-amber-100',
      };
    }
    // unauthorized / library_not_found / network_error / unknown
    const label = bunnyStatus === 'network_error'
      ? t('grids.course.bunny.offline')
      : t('grids.course.bunny.error');
    return {
      label,
      title: t('grids.course.bunny.errorTitle'),
      cls: bunnyStatus === 'network_error'
        ? 'bg-amber-50 border border-amber-300 text-amber-900 hover:bg-amber-100'
        : 'bg-red-50 border border-red-300 text-red-900 hover:bg-red-100',
    };
  })();

  const ActionRow = (
    <div className={`flex items-center justify-end gap-2 ${embedded ? 'mb-2' : ''}`}>
      <button
        type="button"
        onClick={() => setBunnyDialogOpen(true)}
        title={bunnyButton.title}
        className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-semibold whitespace-nowrap transition-colors ${bunnyButton.cls}`}
      >
        🐰 {bunnyButton.label}
      </button>
      {onCreateClick && (
        <button
          type="button"
          onClick={onCreateClick}
          className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 whitespace-nowrap"
        >
          {t('grids.course.newCta')}
        </button>
      )}
    </div>
  );

  return (
    <div className={wrapperClass}>
      {!embedded && (
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{t('grids.course.title')}</h1>
              <p className="text-xs text-gray-500">{t('grids.course.subtitle')}</p>
            </div>
            {ActionRow}
          </div>
        </div>
      )}
      {embedded && ActionRow}

      {/* Filter row */}
      <div className={`${embedded ? '' : 'bg-white border-b sticky'} top-0 z-[5]`}>
        <div className={`${embedded ? '' : 'max-w-6xl mx-auto'} px-0 sm:px-0 py-2 flex flex-wrap items-center gap-2`}>
          {[
            { k: '',          labelKey: 'grids.common.statusFilterAll' },
            { k: 'published', labelKey: 'grids.common.statusOnline' },
            { k: 'draft',     labelKey: 'grids.common.statusOffline' },
          ].map(tab => (
            <button
              key={tab.k || 'all'}
              type="button"
              onClick={() => setStatusFilter(tab.k)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                statusFilter === tab.k
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(tab.labelKey)}</button>
          ))}
          <div className="w-px h-5 bg-gray-200 mx-1" aria-hidden />
          {[
            { k: '',                labelKey: 'grids.course.videoFilter.any' },
            { k: 'with_videos',     labelKey: 'grids.course.videoFilter.complete' },
            { k: 'missing_videos',  labelKey: 'grids.course.videoFilter.missing' },
          ].map(tab => (
            <button
              key={tab.k || 'video-all'}
              type="button"
              onClick={() => setVideoFilter(tab.k)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                videoFilter === tab.k
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(tab.labelKey)}</button>
          ))}
          <div className="flex-1" />
          <input
            type="search"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder={t('grids.course.searchPlaceholder')}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none min-w-[180px]"
          />
        </div>
      </div>

      <div className={`${embedded ? '' : 'max-w-6xl mx-auto px-4 sm:px-6'} py-4 sm:py-6`}>
        {loading && (
          <div className="text-center text-sm text-gray-500 py-12">{t('grids.common.loading')}</div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-10 text-center">
            <div className="text-4xl mb-2">🎓</div>
            <h2 className="text-lg font-semibold text-gray-900">{t('grids.course.emptyTitle')}</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              {q || statusFilter || videoFilter
                ? t('grids.common.tryRemoveFilters')
                : t('grids.course.emptyDescFirst')}
            </p>
            {!q && !statusFilter && !videoFilter && onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >
                {t('grids.course.firstCreateCta')}
              </button>
            )}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {t('grids.course.count', { count: filtered.length })}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map(p => (
                <CourseCard
                  key={p.id}
                  product={p}
                  course={coursesById[p.metadata?.course_id] || null}
                  orgSlug={orgSlug}
                  onStatusChange={handleStatusChange}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Bunny manager dialog — unified multi-library aware. The
          dialog renders the right mode (migrate / empty / list / edit)
          based on org state. We refresh our header-button status when
          it closes so the badge stays in sync with any save inside. */}
      <BunnyManagerDialog
        open={bunnyDialogOpen}
        onClose={() => {
          setBunnyDialogOpen(false);
          refreshBunnyStatus();
        }}
      />
    </div>
  );
}
