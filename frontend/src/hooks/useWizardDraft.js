/**
 * useWizardDraft — autosave + restore for long product-creation wizards.
 *
 * 2026-05-20 — The audit found that ZERO of the 5 wizards persist
 * in-progress form state. Combined with the lack of an unsaved-changes
 * prompt (fixed separately by ``useUnsavedChangesPrompt``), this means
 * any of these scenarios silently wipes 10+ minutes of work:
 *
 *   · The user closes the tab by mistake.
 *   · The JWT expires mid-wizard → the axios interceptor redirects to
 *     ``/login`` and the form data is gone.
 *   · The user opens a different store in another tab → some wizards
 *     re-mount on context change → state reset.
 *
 * This hook adds a draft layer with three properties:
 *
 *   1. PERSIST — every change to ``formData`` is autosaved to localStorage
 *      (debounced 800ms) under a key namespaced by ``wizardKey`` +
 *      ``scopeKey`` (typically ``user.id`` or ``organization_id`` — so
 *      different users on the same machine don't see each other's drafts).
 *
 *   2. RESTORE — on first mount, if a draft <24h old exists, the hook
 *      exposes ``hasDraft = true`` and the caller can render a prompt
 *      ("Riprendi bozza?" → calls ``restore()`` to overwrite formData).
 *
 *   3. CLEAR — on successful submit, the caller calls ``discard()`` to
 *      delete the draft so the next visit starts clean.
 *
 * Usage:
 *
 *   const { hasDraft, restore, discard } = useWizardDraft({
 *     wizardKey: 'physical-create',
 *     scopeKey: user.id,
 *     formData,
 *     setFormData,
 *   });
 *
 *   // …on successful POST /products:
 *   discard();
 *
 *   // …in the JSX:
 *   {hasDraft && <DraftRestoreBanner onRestore={restore} onDiscard={discard} />}
 *
 * Storage layout:
 *
 *   key   = ``afianco:draft:${wizardKey}:${scopeKey}``
 *   value = { v: 1, savedAt: <ms>, data: <serialised formData> }
 *
 *   TTL = 24h — older drafts auto-evict on read so storage doesn't
 *   accumulate forever.
 *
 * What's NOT persisted:
 *   · File objects (image previews, attachments). Files cannot be
 *     re-instantiated from a string; if the wizard captures a File,
 *     the draft restores everything ELSE and the user re-attaches.
 *   · Functions / class instances. Caller must pass plain data.
 *
 * Failure modes (defensive):
 *   · localStorage quota exceeded → silently skip persist, log a warn.
 *   · JSON parse error on read → treat as no-draft (auto-evict).
 *   · SSR / no window → no-op (returns hasDraft=false, all callbacks no-op).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';


const STORAGE_PREFIX = 'afianco:draft:';
const SCHEMA_VERSION = 1;
const TTL_MS = 24 * 60 * 60 * 1000;       // 24 hours
const AUTOSAVE_DEBOUNCE_MS = 800;


function _storageKey(wizardKey, scopeKey) {
  return `${STORAGE_PREFIX}${wizardKey}:${scopeKey || 'anonymous'}`;
}


function _hasWindow() {
  return typeof window !== 'undefined' && !!window.localStorage;
}


function _readDraft(key) {
  if (!_hasWindow()) return null;
  let raw;
  try {
    raw = window.localStorage.getItem(key);
  } catch {
    return null;  // Safari private mode etc.
  }
  if (!raw) return null;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // Corrupted — drop it.
    try { window.localStorage.removeItem(key); } catch { /* ignore */ }
    return null;
  }
  if (!parsed || parsed.v !== SCHEMA_VERSION) return null;
  if (typeof parsed.savedAt !== 'number') return null;
  if (Date.now() - parsed.savedAt > TTL_MS) {
    // Expired — drop it.
    try { window.localStorage.removeItem(key); } catch { /* ignore */ }
    return null;
  }
  return parsed;
}


function _writeDraft(key, data) {
  if (!_hasWindow()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify({
      v: SCHEMA_VERSION,
      savedAt: Date.now(),
      data,
    }));
  } catch (e) {
    // Quota / private mode — give up silently. Drafts are best-effort.
    // eslint-disable-next-line no-console
    if (typeof console !== 'undefined' && console.warn) {
      console.warn('useWizardDraft: persist failed:', e?.message || e);
    }
  }
}


function _clearDraft(key) {
  if (!_hasWindow()) return;
  try { window.localStorage.removeItem(key); } catch { /* ignore */ }
}


/**
 * @param {object} opts
 * @param {string} opts.wizardKey  — namespace (e.g. "physical-create")
 * @param {string} opts.scopeKey   — per-user/org isolation (e.g. user.id)
 * @param {object} opts.formData   — the current form state to autosave
 * @param {(data: object) => void} opts.setFormData — applier for restore
 * @param {boolean} [opts.enabled=true] — toggle for tests / edit-mode wizards
 * @returns {{ hasDraft: boolean, restore: () => void, discard: () => void,
 *             savedAt: number | null }}
 */
export function useWizardDraft({
  wizardKey,
  scopeKey,
  formData,
  setFormData,
  enabled = true,
}) {
  const key = useMemo(
    () => _storageKey(wizardKey, scopeKey),
    [wizardKey, scopeKey],
  );

  // On mount, look up any existing draft and expose it to the caller.
  // We do NOT auto-restore — the caller decides via UI ("Riprendi bozza?").
  const initialDraft = useMemo(
    () => (enabled ? _readDraft(key) : null),
    // intentionally only on mount — subsequent reads would clobber a
    // freshly-written autosave from our own setFormData calls
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [hasDraft, setHasDraft] = useState(!!initialDraft);

  // Autosave debounce: every formData change schedules a write 800ms
  // in the future, cancelling any in-flight save. Avoids writing on
  // every keystroke (which would hammer localStorage and feel slow).
  const debounceRef = useRef(null);
  useEffect(() => {
    if (!enabled) return undefined;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      _writeDraft(key, formData);
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [formData, key, enabled]);

  // ── Public actions ────────────────────────────────────────────────
  const restore = useCallback(() => {
    if (!initialDraft) return;
    // setFormData may be either a setter accepting a value or a setter
    // accepting (prev) => next. We pass the raw data; React handles both.
    setFormData(initialDraft.data);
    setHasDraft(false);  // banner hides after restore
  }, [initialDraft, setFormData]);

  const discard = useCallback(() => {
    _clearDraft(key);
    setHasDraft(false);
  }, [key]);

  return {
    hasDraft,
    restore,
    discard,
    savedAt: initialDraft?.savedAt ?? null,
  };
}


export default useWizardDraft;
