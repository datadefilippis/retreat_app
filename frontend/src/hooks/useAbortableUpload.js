/**
 * useAbortableUpload — wrapper around a long-running axios upload call
 * that:
 *
 *   1. Provides an AbortController.signal to the caller's axios POST.
 *   2. Aborts the in-flight upload automatically on component unmount.
 *   3. Ignores the response after unmount (no setState-on-unmounted
 *      component warnings).
 *
 * 2026-05-20 — The audit found that all 5 wizards do something like:
 *
 *     await productsAPI.uploadImage(productId, file);
 *
 * with no signal. If the user navigates away during a 10s upload of
 * a large image, the request keeps going on the wire (wasted bandwidth,
 * possible billing if metered) AND any post-completion state update on
 * the unmounted component triggers a React warning.
 *
 * Usage:
 *
 *   const upload = useAbortableUpload();
 *
 *   const onSubmit = async () => {
 *     // ...
 *     await upload.run((signal) =>
 *       productsAPI.uploadImage(productId, file, { signal })
 *     );
 *   };
 *
 * The caller's function receives the signal as its single argument and
 * is expected to pass it to axios (``api.post(url, body, { signal })``).
 *
 * Return value:
 *
 *   {
 *     run: (taskFn) => Promise<any | null>
 *       Executes ``taskFn(signal)`` and returns whatever the task resolves
 *       to, or ``null`` if the upload was aborted or the component
 *       unmounted before the response arrived. Errors that are NOT
 *       AbortError propagate normally so the caller's try/catch sees
 *       them.
 *
 *     abort: () => void
 *       Cancel the current upload (idempotent — no-op if nothing running).
 *
 *     isRunning: () => boolean
 *   }
 *
 * Note that ``run`` is intentionally NOT debounced — the caller chooses
 * when to start. The hook merely owns the lifetime.
 */

import { useCallback, useEffect, useRef } from 'react';


export function useAbortableUpload() {
  const controllerRef = useRef(null);
  const mountedRef = useRef(true);

  // Cleanup: abort any in-flight upload on unmount and flag the ref
  // so post-resolution code can short-circuit.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const c = controllerRef.current;
      if (c) {
        try { c.abort(); } catch { /* ignore */ }
      }
      controllerRef.current = null;
    };
  }, []);

  const run = useCallback(async (taskFn) => {
    if (typeof taskFn !== 'function') {
      throw new TypeError('useAbortableUpload.run: taskFn must be a function');
    }
    // If a previous upload is still running, abort it first — the caller
    // is starting a fresh one and we don't want two concurrent uploads.
    if (controllerRef.current) {
      try { controllerRef.current.abort(); } catch { /* ignore */ }
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const result = await taskFn(controller.signal);
      // If we unmounted mid-flight, suppress the result to prevent
      // setState-on-unmounted-component warnings in the caller.
      if (!mountedRef.current || controller.signal.aborted) return null;
      return result;
    } catch (err) {
      // Axios maps abort to ``ERR_CANCELED`` / ``AbortError``. Treat both
      // as a silent null result so callers can write ``if (res) {...}``
      // without special-casing the abort reason.
      const code = err?.code || err?.name;
      if (code === 'ERR_CANCELED' || code === 'CanceledError' || code === 'AbortError') {
        return null;
      }
      if (controller.signal.aborted) return null;
      throw err;
    } finally {
      // Only clear the ref if it's still pointing at OUR controller —
      // a concurrent ``run`` may have replaced it already.
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
    }
  }, []);

  const abort = useCallback(() => {
    const c = controllerRef.current;
    if (c) {
      try { c.abort(); } catch { /* ignore */ }
      controllerRef.current = null;
    }
  }, []);

  const isRunning = useCallback(() => !!controllerRef.current, []);

  return { run, abort, isRunning };
}


export default useAbortableUpload;
