/**
 * useSubmitLock — atomic, synchronous, ref-based submit lock.
 *
 * 2026-05-20 — The 5 wizards all use ``const [submitting, setSubmitting]``
 * + ``<Button disabled={submitting}>`` to prevent double-submit. That
 * pattern has a microscopic race window: between the ``onClick`` firing
 * and React re-rendering the button as disabled, a fast second click
 * can still register and dispatch a SECOND submit handler. On a slow
 * network the user routinely double-clicks → two products created with
 * the same name.
 *
 * The fix is a synchronous ref check INSIDE the handler itself, BEFORE
 * any await. ``setSubmitting`` still runs (for the UI), but the ref is
 * what actually gates the second call.
 *
 * Usage:
 *
 *   const lock = useSubmitLock();
 *   const onSubmit = async () => {
 *     if (!lock.tryLock()) return;   // atomic — second click bounces here
 *     try {
 *       setSubmitting(true);
 *       await api.createProduct(...);
 *     } finally {
 *       setSubmitting(false);
 *       lock.unlock();
 *     }
 *   };
 *
 * The hook is intentionally tiny — no state, no effect, no re-render
 * cost. It pairs WITH (not REPLACES) the existing ``submitting`` state.
 */

import { useCallback, useRef } from 'react';


export function useSubmitLock() {
  const lockedRef = useRef(false);

  const tryLock = useCallback(() => {
    if (lockedRef.current) return false;
    lockedRef.current = true;
    return true;
  }, []);

  const unlock = useCallback(() => {
    lockedRef.current = false;
  }, []);

  const isLocked = useCallback(() => lockedRef.current, []);

  return { tryLock, unlock, isLocked };
}


export default useSubmitLock;
