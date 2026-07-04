/**
 * CourseEditor — admin form for Course create/edit (Release 4 Step 2).
 *
 * Two modes share the same component:
 *
 *   /courses/new       → `mode=create`. Minimal form (title + slug + policy).
 *                        On submit, redirects to /courses/:id so the admin
 *                        can add modules/lessons in edit mode.
 *
 *   /courses/:id       → `mode=edit`. Two cards stacked:
 *                          (1) Dati corso — top-level fields
 *                          (2) Moduli e lezioni — nested CRUD
 *                        Each section is saved with its own server round-trip
 *                        so the admin can abandon a half-filled lesson
 *                        without losing the rest.
 *
 * Design principles:
 *   - NO drag-drop (deferred to Step 9). Reorder via "↑ / ↓" buttons or
 *     the numeric `order` input in the module/lesson forms.
 *   - Optimistic UI where possible, but every write hits the server
 *     and we re-render from the returned course object → single source
 *     of truth stays in the DB, not in React state.
 *   - Errors surface as toasts; inline validation keeps the form usable.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { coursesAPI, bunnyIntegrationAPI } from '../../api/courses';
// Onda 26 — same admin-shell invariant as CoursesPage. Without
// <AppLayout> the sidebar disappears as soon as the user navigates
// from /courses to /courses/new or /courses/:id (create + edit modes
// both render through this component).
import { AppLayout } from '../../components/Layout';
import EnrollmentsSection from './EnrollmentsSection';
import SalesCard from './SalesCard';
import BunnyStatusWidget from './BunnyStatusWidget';


/* ═════════════════════════════════════════════════════════════════════════
   Shared helpers
   ═════════════════════════════════════════════════════════════════════════ */

function slugify(s) {
  return String(s || '')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // strip accents
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
}


function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  if (s === 0) return `${m} min`;
  return `${m}:${String(s).padStart(2, '0')}`;
}


const BUNNY_GUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;


/* ═════════════════════════════════════════════════════════════════════════
   Top-level Course fields form
   ═════════════════════════════════════════════════════════════════════════ */

function CourseBasicsForm({ value, onChange, mode }) {
  const { t } = useTranslation('products');
  // Auto-fill slug from title when creating and the user hasn't customized it.
  const handleTitleChange = (title) => {
    const next = { ...value, title };
    if (mode === 'create' && !value._slugTouched) {
      next.slug = slugify(title);
    }
    onChange(next);
  };

  const handleSlugChange = (raw) => {
    onChange({ ...value, slug: slugify(raw), _slugTouched: true });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.basics.titleLabel')}
        </label>
        <input
          type="text"
          value={value.title || ''}
          onChange={e => handleTitleChange(e.target.value)}
          maxLength={255}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          placeholder={t('dashboards.course.basics.titlePlaceholder')}
        />
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.basics.slugLabel')}
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-mono">/co/{'{org}'}/</span>
          <input
            type="text"
            value={value.slug || ''}
            onChange={e => handleSlugChange(e.target.value)}
            maxLength={120}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-gray-900 focus:outline-none"
            placeholder={t('dashboards.course.basics.slugPlaceholder')}
          />
        </div>
        <p className="text-[11px] text-gray-500 mt-1">
          {t('dashboards.course.basics.slugHint')}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {t('dashboards.course.basics.instructorLabel')}
          </label>
          <input
            type="text"
            value={value.instructor_name || ''}
            onChange={e => onChange({ ...value, instructor_name: e.target.value })}
            maxLength={255}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            placeholder={t('dashboards.course.basics.instructorPlaceholder')}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {t('dashboards.course.basics.coverImageUrlLabel')}
          </label>
          <input
            type="url"
            value={value.cover_image_url || ''}
            onChange={e => onChange({ ...value, cover_image_url: e.target.value })}
            maxLength={2048}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            placeholder={t('dashboards.course.basics.coverImageUrlPlaceholder')}
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.basics.shortDescLabel')}
        </label>
        <textarea
          value={value.description || ''}
          onChange={e => onChange({ ...value, description: e.target.value })}
          maxLength={2000}
          rows={2}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          placeholder={t('dashboards.course.basics.shortDescPlaceholder')}
        />
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.basics.longDescLabel')}
        </label>
        <textarea
          value={value.long_description || ''}
          onChange={e => onChange({ ...value, long_description: e.target.value })}
          maxLength={20000}
          rows={4}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          placeholder={t('dashboards.course.basics.longDescPlaceholder')}
        />
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.basics.instructorBioLabel')}
        </label>
        <textarea
          value={value.instructor_bio || ''}
          onChange={e => onChange({ ...value, instructor_bio: e.target.value })}
          maxLength={4000}
          rows={3}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {t('dashboards.course.basics.policyLabel')}
          </label>
          <select
            value={value.access_policy || 'lifetime'}
            onChange={e => onChange({ ...value, access_policy: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          >
            <option value="lifetime">{t('dashboards.course.basics.policyLifetime')}</option>
            <option value="expiring">{t('dashboards.course.basics.policyExpiring')}</option>
          </select>
        </div>
        {value.access_policy === 'expiring' && (
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
              {t('dashboards.course.basics.expiryLabel')}
            </label>
            <input
              type="number"
              min={1}
              max={3650}
              value={value.access_expiry_days ?? ''}
              onChange={e => onChange({
                ...value,
                access_expiry_days: e.target.value === '' ? null : Number(e.target.value),
              })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              placeholder="365"
            />
          </div>
        )}
      </div>
    </div>
  );
}


/* ═════════════════════════════════════════════════════════════════════════
   Inline lesson form (sub-component of each module)
   ═════════════════════════════════════════════════════════════════════════ */

function LessonRow({ courseId, moduleId, lesson, totalLessons, onCourseUpdate, bunnyLibraries = [] }) {
  const { t } = useTranslation('products');
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => ({
    title: lesson.title || '',
    duration_seconds: lesson.duration_seconds || 0,
    bunny_video_guid: lesson.bunny_video_guid || '',
    // Multi-library Step 8: library reference. Empty string = use
    // org default at playback time (resolver fallback).
    bunny_library_id: lesson.bunny_library_id || '',
    description: lesson.description || '',
    is_preview: !!lesson.is_preview,
    order: lesson.order,
  }));
  const [saving, setSaving] = useState(false);

  const guidValid = !draft.bunny_video_guid || BUNNY_GUID_RE.test(draft.bunny_video_guid);

  const handleSave = async () => {
    if (!draft.title.trim()) {
      toast.error(t('dashboards.course.validation.lessonTitleRequired'));
      return;
    }
    if (!guidValid) {
      toast.error(t('dashboards.course.validation.guidInvalid'));
      return;
    }
    setSaving(true);
    try {
      // The endpoints return the full CourseResponse — we update the
      // parent state with that response instead of re-fetching, so the
      // accordion state + scroll position stay untouched.
      const { data } = await coursesAPI.updateLesson(courseId, moduleId, lesson.id, {
        title: draft.title.trim(),
        duration_seconds: Number(draft.duration_seconds) || 0,
        bunny_video_guid: draft.bunny_video_guid.trim() || null,
        // Multi-library Step 8: empty string maps to null (= clear
        // explicit reference, fall back to org default at playback).
        bunny_library_id: draft.bunny_library_id || null,
        description: draft.description || '',
        is_preview: draft.is_preview,
        order: Number(draft.order),
      });
      setEditing(false);
      onCourseUpdate?.(data);
      toast.success(t('dashboards.course.toasts.lessonUpdated'));
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.toasts.saveError'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(t('dashboards.course.toasts.lessonDeleteConfirm', { title: lesson.title }))) return;
    try {
      const { data } = await coursesAPI.deleteLesson(courseId, moduleId, lesson.id);
      onCourseUpdate?.(data);
      toast.success(t('dashboards.course.toasts.lessonDeleted'));
    } catch {
      toast.error(t('dashboards.course.toasts.lessonDeleteError'));
    }
  };

  const handleMove = async (direction) => {
    const newOrder = lesson.order + direction;
    if (newOrder < 0 || newOrder >= totalLessons) return;
    try {
      const { data } = await coursesAPI.updateLesson(courseId, moduleId, lesson.id, { order: newOrder });
      onCourseUpdate?.(data);
    } catch {
      toast.error(t('dashboards.course.toasts.lessonReorderError'));
    }
  };

  if (!editing) {
    return (
      <div className="flex items-center gap-3 px-3 py-2 border border-gray-100 rounded-md bg-white hover:bg-gray-50">
        <span className="text-xs text-gray-400 font-mono w-6">{lesson.order + 1}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">{lesson.title}</div>
          <div className="text-[11px] text-gray-500 flex items-center gap-2">
            <span>⏱ {formatDuration(lesson.duration_seconds)}</span>
            {lesson.bunny_video_guid ? (
              <span className="text-green-700">{t('dashboards.course.lesson.videoOk')}</span>
            ) : (
              <span className="text-amber-700">{t('dashboards.course.lesson.videoMissing')}</span>
            )}
            {lesson.is_preview && <span className="text-blue-700">{t('dashboards.course.lesson.preview')}</span>}
          </div>
        </div>
        <button
          type="button"
          onClick={() => handleMove(-1)}
          disabled={lesson.order === 0}
          className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
          aria-label={t('dashboards.course.lesson.moveUp')}
          title={t('dashboards.course.lesson.moveUp')}
        >↑</button>
        <button
          type="button"
          onClick={() => handleMove(+1)}
          disabled={lesson.order >= totalLessons - 1}
          className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
          aria-label={t('dashboards.course.lesson.moveDown')}
          title={t('dashboards.course.lesson.moveDown')}
        >↓</button>
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="text-xs font-semibold text-gray-700 hover:text-gray-900"
        >{t('dashboards.course.lesson.edit')}</button>
        <button
          type="button"
          onClick={handleDelete}
          className="text-xs font-semibold text-red-700 hover:text-red-900"
        >{t('dashboards.course.lesson.delete')}</button>
      </div>
    );
  }

  return (
    <div className="p-3 border border-gray-300 rounded-md bg-gray-50 space-y-2">
      <input
        type="text"
        value={draft.title}
        onChange={e => setDraft({ ...draft, title: e.target.value })}
        placeholder={t('dashboards.course.lesson.titlePlaceholder')}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <div>
          <label className="text-[11px] text-gray-600 block mb-0.5">{t('dashboards.course.lesson.durationLabel')}</label>
          <input
            type="number"
            min={0}
            value={draft.duration_seconds}
            onChange={e => setDraft({ ...draft, duration_seconds: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="md:col-span-2">
          <label className="text-[11px] text-gray-600 block mb-0.5">{t('dashboards.course.lesson.guidLabel')}</label>
          <input
            type="text"
            value={draft.bunny_video_guid}
            onChange={e => setDraft({ ...draft, bunny_video_guid: e.target.value })}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            className={`w-full rounded-md border px-2 py-1.5 text-xs font-mono ${
              guidValid ? 'border-gray-300' : 'border-red-400'
            }`}
          />
          {!guidValid && (
            <p className="text-[11px] text-red-700 mt-0.5">{t('dashboards.course.lesson.guidFormatError')}</p>
          )}
        </div>
      </div>

      {/* Multi-library Step 8: library dropdown. Visible only when
          the org has multi-library configured. Same UX as the add-form
          dropdown — empty value maps to null at save time. */}
      {bunnyLibraries.length > 0 && (
        <div>
          <label className="text-[11px] text-gray-600 block mb-0.5">{t('dashboards.course.lesson.libraryLabel')}</label>
          <select
            value={draft.bunny_library_id || ''}
            onChange={e => setDraft({ ...draft, bunny_library_id: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
          >
            <option value="">
              {bunnyLibraries.find(l => l.is_default)
                ? `Default (${bunnyLibraries.find(l => l.is_default)?.alias})`
                : t('dashboards.course.lesson.libraryDefault')}
            </option>
            {bunnyLibraries.map(l => (
              <option key={l.id} value={l.id}>
                {l.alias}{l.is_default ? ' ⭐ default' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      <textarea
        value={draft.description}
        onChange={e => setDraft({ ...draft, description: e.target.value })}
        placeholder={t('dashboards.course.lesson.descPlaceholder')}
        rows={2}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
      <label className="inline-flex items-center gap-2 text-xs text-gray-700">
        <input
          type="checkbox"
          checked={draft.is_preview}
          onChange={e => setDraft({ ...draft, is_preview: e.target.checked })}
          className="rounded border-gray-300"
        />
        {t('dashboards.course.lesson.previewToggle')}
      </label>
      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={() => { setEditing(false); setDraft({
            title: lesson.title || '',
            duration_seconds: lesson.duration_seconds || 0,
            bunny_video_guid: lesson.bunny_video_guid || '',
            bunny_library_id: lesson.bunny_library_id || '',
            description: lesson.description || '',
            is_preview: !!lesson.is_preview,
            order: lesson.order,
          }); }}
          className="text-xs font-semibold text-gray-600 hover:text-gray-900 px-3 py-1.5"
        >{t('dashboards.course.lesson.cancel')}</button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded-md bg-gray-900 text-white text-xs font-semibold px-3 py-1.5 hover:bg-gray-800 disabled:opacity-60"
        >{saving ? t('dashboards.course.lesson.saving') : t('dashboards.course.lesson.saveBtn')}</button>
      </div>
    </div>
  );
}


/* ═════════════════════════════════════════════════════════════════════════
   Module card (with inline lesson list)
   ═════════════════════════════════════════════════════════════════════════ */

function ModuleCard({ courseId, module, totalModules, onCourseUpdate, bunnyLibraries = [] }) {
  const { t } = useTranslation('products');
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(module.title);
  const [descDraft, setDescDraft] = useState(module.description || '');
  const [savingTitle, setSavingTitle] = useState(false);

  // Multi-library Step 8: lesson form gains an optional bunny_library_id
  // when the org has 2+ libraries (or even 1 from the new multi-library
  // path). Empty/null = use org default at playback time.
  const [newLesson, setNewLesson] = useState({
    title: '', duration_seconds: 0, bunny_video_guid: '', bunny_library_id: '',
  });
  const [addingLesson, setAddingLesson] = useState(false);
  // Ref on the "new lesson title" input so we can refocus after every
  // successful add — prevents the "scroll down to find the form every
  // time" fatigue when batch-adding lessons.
  const newLessonTitleRef = useRef(null);

  const guidValid = !newLesson.bunny_video_guid || BUNNY_GUID_RE.test(newLesson.bunny_video_guid);

  const handleSaveTitle = async () => {
    if (!titleDraft.trim()) { toast.error(t('dashboards.course.validation.moduleTitleRequired')); return; }
    setSavingTitle(true);
    try {
      const { data } = await coursesAPI.updateModule(courseId, module.id, {
        title: titleDraft.trim(),
        description: descDraft || null,
      });
      setEditingTitle(false);
      onCourseUpdate?.(data);
      toast.success(t('dashboards.course.toasts.moduleUpdated'));
    } catch {
      toast.error(t('dashboards.course.toasts.saveError'));
    } finally {
      setSavingTitle(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(t('dashboards.course.toasts.moduleDeleteConfirm', { title: module.title }))) return;
    try {
      const { data } = await coursesAPI.deleteModule(courseId, module.id);
      onCourseUpdate?.(data);
      toast.success(t('dashboards.course.toasts.moduleDeleted'));
    } catch {
      toast.error(t('dashboards.course.toasts.moduleDeleteError'));
    }
  };

  const handleMove = async (direction) => {
    const newOrder = module.order + direction;
    if (newOrder < 0 || newOrder >= totalModules) return;
    try {
      const { data } = await coursesAPI.updateModule(courseId, module.id, { order: newOrder });
      onCourseUpdate?.(data);
    } catch {
      toast.error(t('dashboards.course.toasts.moduleReorderError'));
    }
  };

  const handleAddLesson = async () => {
    if (!newLesson.title.trim()) { toast.error(t('dashboards.course.validation.lessonTitleRequired')); return; }
    if (!guidValid) { toast.error(t('dashboards.course.validation.guidInvalidShort')); return; }
    setAddingLesson(true);
    try {
      const { data } = await coursesAPI.addLesson(courseId, module.id, {
        title: newLesson.title.trim(),
        duration_seconds: Number(newLesson.duration_seconds) || 0,
        bunny_video_guid: newLesson.bunny_video_guid.trim() || null,
        // Multi-library Step 8: pass bunny_library_id when set; empty
        // string maps to null (= use org default at playback). Backend
        // validates the id against the org's bunny_libraries on save.
        bunny_library_id: newLesson.bunny_library_id || null,
        is_preview: false,
      });
      setNewLesson({ title: '', duration_seconds: 0, bunny_video_guid: '', bunny_library_id: '' });
      onCourseUpdate?.(data);
      toast.success(t('dashboards.course.toasts.lessonAdded'));
      // Keep the form visible + focused so the admin can type the next
      // lesson without scrolling. rAF waits for the DOM to settle after
      // the state update.
      requestAnimationFrame(() => {
        newLessonTitleRef.current?.focus();
        newLessonTitleRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.toasts.lessonAddError'));
    } finally {
      setAddingLesson(false);
    }
  };

  const lessons = module.lessons || [];

  return (
    <div className="border border-gray-200 bg-white rounded-xl shadow-sm p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-lg font-bold text-gray-400 w-8 shrink-0">
          {String(module.order + 1).padStart(2, '0')}
        </span>
        <div className="flex-1 min-w-0">
          {editingTitle ? (
            <div className="space-y-2">
              <input
                type="text"
                value={titleDraft}
                onChange={e => setTitleDraft(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-semibold"
                placeholder={t('dashboards.course.module.titlePlaceholder')}
              />
              <textarea
                value={descDraft}
                onChange={e => setDescDraft(e.target.value)}
                rows={2}
                placeholder={t('dashboards.course.module.descPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs"
              />
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setEditingTitle(false); setTitleDraft(module.title); setDescDraft(module.description || ''); }}
                  className="text-xs font-semibold text-gray-600 hover:text-gray-900 px-3 py-1.5"
                >{t('dashboards.course.module.cancel')}</button>
                <button
                  type="button"
                  onClick={handleSaveTitle}
                  disabled={savingTitle}
                  className="rounded-md bg-gray-900 text-white text-xs font-semibold px-3 py-1.5 hover:bg-gray-800 disabled:opacity-60"
                >{savingTitle ? t('dashboards.course.module.saving') : t('dashboards.course.module.saveBtn')}</button>
              </div>
            </div>
          ) : (
            <>
              <h3 className="text-base font-semibold text-gray-900">{module.title}</h3>
              {module.description && (
                <p className="text-xs text-gray-600 mt-0.5">{module.description}</p>
              )}
              <p className="text-[11px] text-gray-500 mt-1">
                {t('grids.course.lessonCount', { count: lessons.length })}
              </p>
            </>
          )}
        </div>
        {!editingTitle && (
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => handleMove(-1)}
              disabled={module.order === 0}
              className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
              title={t('dashboards.course.module.moveUp')}
            >↑</button>
            <button
              type="button"
              onClick={() => handleMove(+1)}
              disabled={module.order >= totalModules - 1}
              className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
              title={t('dashboards.course.module.moveDown')}
            >↓</button>
            <button
              type="button"
              onClick={() => setEditingTitle(true)}
              className="text-xs font-semibold text-gray-700 hover:text-gray-900 px-2"
            >{t('dashboards.course.module.edit')}</button>
            <button
              type="button"
              onClick={handleDelete}
              className="text-xs font-semibold text-red-700 hover:text-red-900 px-2"
            >{t('dashboards.course.module.delete')}</button>
          </div>
        )}
      </div>

      {/* Inline add-lesson form — positioned ABOVE the lessons list
          (was below). Reason: when batch-adding lessons, the form stays
          visible at the top of the card instead of sinking further down
          with every new lesson. Paired with autofocus + scrollIntoView
          on successful add (see handleAddLesson). */}
      <div className="border-y border-gray-100 py-3 space-y-2 bg-gray-50/40 -mx-4 px-4 sm:-mx-0 sm:px-0 sm:rounded-md sm:bg-transparent sm:border-0 sm:border-t sm:pt-3 sm:pb-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
          {t('dashboards.course.module.addLessonHeader')}
        </p>
        <input
          ref={newLessonTitleRef}
          type="text"
          value={newLesson.title}
          onChange={e => setNewLesson({ ...newLesson, title: e.target.value })}
          onKeyDown={e => { if (e.key === 'Enter' && newLesson.title.trim()) handleAddLesson(); }}
          placeholder={t('dashboards.course.module.newLessonPlaceholder')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input
            type="number"
            min={0}
            value={newLesson.duration_seconds}
            onChange={e => setNewLesson({ ...newLesson, duration_seconds: e.target.value })}
            placeholder={t('dashboards.course.module.newLessonDuration')}
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
          <input
            type="text"
            value={newLesson.bunny_video_guid}
            onChange={e => setNewLesson({ ...newLesson, bunny_video_guid: e.target.value })}
            placeholder={t('dashboards.course.module.newLessonGuid')}
            className={`md:col-span-2 rounded-md border px-2 py-1.5 text-xs font-mono ${
              guidValid ? 'border-gray-300' : 'border-red-400'
            }`}
          />
        </div>

        {/* Multi-library Step 8: library dropdown. Visible only when
            the org has 2+ libraries (or 1 from the multi-library path)
            — single-library or legacy orgs see no extra noise. The
            "Default" option lets the lesson use the org's default at
            resolve time. */}
        {bunnyLibraries.length > 0 && (
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">
              {t('dashboards.course.module.libraryLabel')}
            </label>
            <select
              value={newLesson.bunny_library_id || ''}
              onChange={e => setNewLesson({ ...newLesson, bunny_library_id: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
            >
              <option value="">
                {bunnyLibraries.find(l => l.is_default)
                  ? `Default (${bunnyLibraries.find(l => l.is_default)?.alias})`
                  : t('dashboards.course.lesson.libraryDefault')}
              </option>
              {bunnyLibraries.map(l => (
                <option key={l.id} value={l.id}>
                  {l.alias}{l.is_default ? ' ⭐ default' : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex items-center justify-between">
          <p className="text-[10px] text-gray-500">
            {t('dashboards.course.module.kbdHintBefore')} <kbd className="px-1 bg-gray-100 border border-gray-300 rounded">{t('dashboards.course.module.kbdEnter')}</kbd> {t('dashboards.course.module.kbdHintAfter')}
          </p>
          <button
            type="button"
            onClick={handleAddLesson}
            disabled={addingLesson}
            className="rounded-md bg-gray-900 text-white text-xs font-semibold px-3 py-1.5 hover:bg-gray-800 disabled:opacity-60"
          >{addingLesson ? t('dashboards.course.module.addingLesson') : t('dashboards.course.module.addLessonBtn')}</button>
        </div>
      </div>

      {/* Lessons list */}
      {lessons.length > 0 && (
        <div className="space-y-1.5">
          {lessons.map(l => (
            <LessonRow
              key={l.id}
              courseId={courseId}
              moduleId={module.id}
              lesson={l}
              totalLessons={lessons.length}
              onCourseUpdate={onCourseUpdate}
              bunnyLibraries={bunnyLibraries}
            />
          ))}
        </div>
      )}
    </div>
  );
}


/* ═════════════════════════════════════════════════════════════════════════
   Main CourseEditor (create + edit)
   ═════════════════════════════════════════════════════════════════════════ */

export default function CourseEditor() {
  const { t } = useTranslation('products');
  const { course_id: courseIdParam } = useParams();
  const navigate = useNavigate();
  const isCreate = !courseIdParam || courseIdParam === 'new';

  // Tab navigation: "edit" (default — modules, lessons, sales, bunny)
  // vs "enrollments" (full-width customer list with revoke). Persisted
  // via the `?view=` query param so deep-links + browser back/forward
  // work naturally. Create-mode (no course_id yet) has no Iscritti tab.
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = searchParams.get('view') === 'enrollments' && !isCreate
    ? 'enrollments'
    : 'edit';
  const setView = (next) => {
    const sp = new URLSearchParams(searchParams);
    if (next === 'edit') sp.delete('view');
    else sp.set('view', next);
    setSearchParams(sp, { replace: true });
  };

  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(!isCreate);
  const [error, setError] = useState(null);
  // Multi-library Step 8: list of org's Bunny libraries used to render
  // the "Library" dropdown in lesson forms. Empty for legacy orgs (no
  // multi-library yet) — the dropdown is hidden in that case so the
  // legacy single-library UX stays clean. Fetched once on mount; the
  // legacy `bunny` field is NOT included here on purpose (admins must
  // promote to multi-library before they can pick libraries per lesson).
  const [bunnyLibraries, setBunnyLibraries] = useState([]);
  const [savingBasics, setSavingBasics] = useState(false);
  const [basicsDraft, setBasicsDraft] = useState({
    title: '',
    slug: '',
    description: '',
    long_description: '',
    cover_image_url: '',
    instructor_name: '',
    instructor_bio: '',
    access_policy: 'lifetime',
    access_expiry_days: null,
    _slugTouched: false,
  });

  const [newModuleTitle, setNewModuleTitle] = useState('');
  const [addingModule, setAddingModule] = useState(false);

  const loadCourse = useCallback(async () => {
    if (isCreate) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await coursesAPI.get(courseIdParam);
      setCourse(data);
      setBasicsDraft({
        title: data.title || '',
        slug: data.slug || '',
        description: data.description || '',
        long_description: data.long_description || '',
        cover_image_url: data.cover_image_url || '',
        instructor_name: data.instructor_name || '',
        instructor_bio: data.instructor_bio || '',
        access_policy: data.access_policy || 'lifetime',
        access_expiry_days: data.access_expiry_days ?? null,
        _slugTouched: true,
      });
    } catch (e) {
      setError(e?.response?.data?.detail || t('dashboards.course.notFound'));
    } finally {
      setLoading(false);
    }
  }, [courseIdParam, isCreate]);

  useEffect(() => { loadCourse(); }, [loadCourse]);

  // Multi-library Step 8: fetch the org's Bunny libraries once on
  // mount to populate the lesson-form dropdown. Silent on failure —
  // the form falls back to "no dropdown" when the list is empty,
  // matching the legacy single-library UX exactly.
  useEffect(() => {
    let cancelled = false;
    bunnyIntegrationAPI.libraries.list()
      .then(res => {
        if (cancelled) return;
        setBunnyLibraries(res.data?.libraries || []);
      })
      .catch(() => {
        if (cancelled) return;
        setBunnyLibraries([]);
      });
    return () => { cancelled = true; };
  }, []);

  const handleSaveBasics = async () => {
    // Validation
    if (!basicsDraft.title.trim()) { toast.error(t('dashboards.course.validation.courseTitleRequired')); return; }
    if (!basicsDraft.slug.trim()) { toast.error(t('dashboards.course.validation.slugRequired')); return; }
    if (basicsDraft.access_policy === 'expiring' && !basicsDraft.access_expiry_days) {
      toast.error(t('dashboards.course.validation.expiryRequired')); return;
    }

    setSavingBasics(true);
    try {
      const payload = {
        title: basicsDraft.title.trim(),
        slug: basicsDraft.slug.trim(),
        description: basicsDraft.description || null,
        long_description: basicsDraft.long_description || null,
        cover_image_url: basicsDraft.cover_image_url || null,
        instructor_name: basicsDraft.instructor_name || null,
        instructor_bio: basicsDraft.instructor_bio || null,
        access_policy: basicsDraft.access_policy,
        access_expiry_days: basicsDraft.access_expiry_days,
      };

      if (isCreate) {
        const { data } = await coursesAPI.create(payload);
        toast.success(t('dashboards.course.toasts.courseCreated'));
        navigate(`/courses/${data.id}`, { replace: true });
      } else {
        await coursesAPI.update(courseIdParam, payload);
        toast.success(t('dashboards.course.toasts.courseUpdated'));
        await loadCourse();
      }
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.toasts.saveError'));
    } finally {
      setSavingBasics(false);
    }
  };

  const handleAddModule = async () => {
    if (!newModuleTitle.trim()) { toast.error(t('dashboards.course.validation.moduleTitleRequired')); return; }
    setAddingModule(true);
    try {
      const { data } = await coursesAPI.addModule(courseIdParam, { title: newModuleTitle.trim() });
      setNewModuleTitle('');
      // Silent state merge — avoids the full re-fetch flash that collapsed
      // accordions and reset scroll position on every mutation.
      handleCourseUpdate(data);
      toast.success(t('dashboards.course.toasts.moduleAdded'));
    } catch {
      toast.error(t('dashboards.course.toasts.moduleAddError'));
    } finally {
      setAddingModule(false);
    }
  };

  /* Silent merge — children call this with the full CourseResponse the
   * server just returned. Keeps children mounted (stable `key` on
   * module.id / lesson.id) so local UI state (accordion open, edit
   * drafts, scroll position) survives the mutation. */
  const handleCourseUpdate = useCallback((updatedCourse) => {
    if (!updatedCourse) return;
    setCourse(updatedCourse);
  }, []);

  const modules = course?.modules || [];

  /* ─── Render ──────────────────────────────────────────────────────── */

  return (
    <AppLayout>
      <div className={`mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6 ${
        isCreate ? 'max-w-4xl' : 'max-w-6xl'
      }`}>

        {/* Breadcrumb — back to the unified products page filtered on
            the course chip. Mirrors the pattern of the other product
            types (digital/physical/etc.) that all return to /products. */}
        <div className="text-sm">
          <Link to="/products?type=course" className="text-gray-500 hover:text-gray-900">
            {t('dashboards.course.back')}
          </Link>
        </div>

        {/* Loading / error */}
        {loading ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
            {t('dashboards.course.loading')}
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800">
            {String(error)}
          </div>
        ) : (
          <>
            {/* Title + status ribbon */}
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <span aria-hidden>🎓</span>
                  {isCreate ? t('dashboards.course.newTitle') : (course?.title || t('dashboards.course.newTitle'))}
                </h1>
                {!isCreate && (
                  <p className="text-xs text-gray-500 mt-1 font-mono">
                    /co/{'{store}'}/{course?.slug}
                  </p>
                )}
              </div>
              {!isCreate && (
                <div className="flex items-center gap-3 text-xs text-gray-600">
                  <span>{t('grids.course.moduleCount', { count: modules.length })}</span>
                  <span className="text-gray-300">·</span>
                  <span>
                    {t('grids.course.lessonCount', { count: modules.reduce((s, m) => s + (m.lessons?.length || 0), 0) })}
                  </span>
                  <span className="text-gray-300">·</span>
                  <span className={course?.is_active ? 'text-emerald-700' : 'text-gray-500'}>
                    {course?.is_active ? t('dashboards.course.active') : t('dashboards.course.archived')}
                  </span>
                </div>
              )}
            </div>

            {/* Tab navigation — hidden in create mode (no enrollments yet
                because the course doesn't exist server-side). The
                `?view=` query param keeps deep-links + browser
                back/forward in sync with the visible tab. */}
            {!isCreate && (
              <div className="border-b border-gray-200 -mb-2">
                <nav className="flex items-center gap-1" aria-label={t('dashboards.course.tabs.editHint')}>
                  {[
                    { key: 'edit',        label: t('dashboards.course.tabs.edit'),
                      hint: t('dashboards.course.tabs.editHint') },
                    { key: 'enrollments', label: t('dashboards.course.tabs.users'),
                      hint: t('dashboards.course.tabs.usersHint') },
                  ].map(tab => {
                    const active = activeView === tab.key;
                    return (
                      <button
                        key={tab.key}
                        type="button"
                        onClick={() => setView(tab.key)}
                        title={tab.hint}
                        className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
                          active
                            ? 'border-gray-900 text-gray-900'
                            : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
                        }`}
                      >
                        {tab.label}
                      </button>
                    );
                  })}
                </nav>
              </div>
            )}

            {/* 2-column dashboard layout — only when activeView === 'edit'
                (or when creating — create mode has no enrollments anyway). */}
            {(activeView === 'edit') && (
            <div className={isCreate
              ? 'space-y-6'
              : 'grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 items-start'
            }>

              {/* ── LEFT / MAIN: content (basics + modules) ────────────────── */}
              <div className="space-y-6 min-w-0">

                {/* Basics card */}
                <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-base font-semibold text-gray-900">{t('dashboards.course.panels.basics')}</h2>
                    <button
                      type="button"
                      onClick={handleSaveBasics}
                      disabled={savingBasics}
                      className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-60"
                    >
                      {savingBasics ? t('dashboards.course.basics.savingBtn') : (isCreate ? t('dashboards.course.basics.createBtn') : t('dashboards.course.basics.saveBtn'))}
                    </button>
                  </div>
                  <CourseBasicsForm
                    value={basicsDraft}
                    onChange={setBasicsDraft}
                    mode={isCreate ? 'create' : 'edit'}
                  />
                </section>

                {/* Modules section — only in edit mode (needs course.id) */}
                {!isCreate && (
                  <section className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-base font-semibold text-gray-900">
                        {t('dashboards.course.panels.modulesLessons')}
                      </h2>
                      <span className="text-xs text-gray-500">
                        {t('grids.course.moduleCount', { count: modules.length })}
                      </span>
                    </div>

                    {/* Onboarding state when the course is brand new */}
                    {modules.length === 0 ? (
                      <div className="bg-white rounded-xl border border-dashed border-blue-300 p-6 text-center text-sm text-gray-700 space-y-2">
                        <div className="text-3xl">📚</div>
                        <p className="font-semibold text-gray-900">{t('dashboards.course.modules.onboardingTitle')}</p>
                        <p className="text-xs text-gray-600 max-w-md mx-auto">
                          {t('dashboards.course.modules.onboardingStep1')}<br/>
                          {t('dashboards.course.modules.onboardingStep2')}<br/>
                          {t('dashboards.course.modules.onboardingStep3')}
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {modules.map(m => (
                          <ModuleCard
                            key={m.id}
                            courseId={courseIdParam}
                            module={m}
                            totalModules={modules.length}
                            onCourseUpdate={handleCourseUpdate}
                            bunnyLibraries={bunnyLibraries}
                          />
                        ))}
                      </div>
                    )}

                    {/* Add module */}
                    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                      <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
                        {t('dashboards.course.modules.addModuleLabel')}
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={newModuleTitle}
                          onChange={e => setNewModuleTitle(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') handleAddModule(); }}
                          placeholder={t('dashboards.course.modules.newModulePlaceholder')}
                          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={handleAddModule}
                          disabled={addingModule}
                          className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-60 whitespace-nowrap"
                        >
                          {addingModule ? t('dashboards.course.modules.addingModule') : t('dashboards.course.modules.addModuleBtn')}
                        </button>
                      </div>
                    </div>
                  </section>
                )}

                {/* Enrollments moved out of the main column → rendered as
                    a dedicated full-width section below the dashboard
                    grid. Keeps the editorial column focused on content
                    (modules + lessons) and gives the customer list its
                    own room for table columns. See after this </div>. */}
              </div>

              {/* ── RIGHT / SIDEBAR: commerce + infra (edit mode only) ─────── */}
              {!isCreate && (
                <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
                  <SalesCard
                    course={course}
                    courseId={courseIdParam}
                    onCourseSlugChanged={(newSlug) => {
                      // Course slug is synced server-side; reflect in our
                      // local state so the header URL + URL preview stay
                      // truthful without a full reload.
                      setCourse(c => c ? { ...c, slug: newSlug } : c);
                    }}
                  />
                  {/* Compact Bunny status — opens the full editor in a
                      modal. Replaces the inline BunnyConfigCard which
                      consumed a lot of sidebar height even when no
                      action was needed. */}
                  <BunnyStatusWidget />
                </div>
              )}
            </div>
            )}

            {/* ── ENROLLMENTS VIEW (tab "Utenti iscritti") ─────────────────
                Rendered only when activeView === 'enrollments'. Replaces
                the previous full-width section that lived underneath the
                edit dashboard — promoted to a dedicated tab so the admin
                clearly separates "modifica contenuto" from "gestisci
                iscritti". The EnrollmentsSection component itself is
                identical (CRUD + revoca modal preserved). */}
            {!isCreate && activeView === 'enrollments' && (
              <section className="space-y-3">
                <div className="flex items-baseline gap-3 flex-wrap">
                  <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                    {t('dashboards.course.enrollments.title')}
                  </h2>
                  <p className="text-xs text-gray-500">
                    {t('dashboards.course.enrollments.subtitle')}
                  </p>
                </div>
                <EnrollmentsSection courseId={courseIdParam} />
              </section>
            )}

            {/* Hint for create mode */}
            {isCreate && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-900">
                💡 <strong>{t('dashboards.course.createHint.label')}</strong> {t('dashboards.course.createHint.text')}
              </div>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
