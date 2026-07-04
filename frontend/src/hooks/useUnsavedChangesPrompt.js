/**
 * useUnsavedChangesPrompt — warn the user before leaving a dirty form.
 *
 * 2026-05-20 — The audit found that NONE of the 5 wizards warn the user
 * if they navigate away (back button, click on sidebar link, close tab)
 * after filling part of the form. EventWizard is the worst — 4 steps
 * + multiple image uploads, ~10-15 minutes of work, lost silently on a
 * mis-click.
 *
 * This hook plugs both gaps with a SINGLE call:
 *
 *   useUnsavedChangesPrompt(isDirty, message?)
 *
 *   · While ``isDirty`` is true, ``beforeunload`` is registered so a
 *     tab close / reload triggers the browser's native confirm dialog
 *     (the message is browser-controlled — modern browsers ignore the
 *     custom text but DO show the prompt).
 *   · React Router 7 ``useBlocker`` is registered so in-app navigation
 *     (back button, link click, programmatic navigate) is intercepted.
 *     Returns ``{blocker}`` so the caller can render its own dialog.
 *
 * The hook is no-op when ``isDirty`` is false — no listeners attached,
 * no router blocker, zero overhead.
 *
 * Returns:
 *   {
 *     blocker: ReturnType<typeof useBlocker>,
 *     // The blocker has .state ("unblocked" | "blocked" | "proceeding"),
 *     // .proceed() to confirm, .reset() to cancel. Caller renders an
 *     // <AlertDialog> conditional on blocker.state === "blocked".
 *   }
 *
 * Example:
 *
 *   const { blocker } = useUnsavedChangesPrompt(isDirty);
 *
 *   return (
 *     <>
 *       <form>...</form>
 *       <UnsavedChangesDialog
 *         open={blocker.state === 'blocked'}
 *         onConfirm={() => blocker.proceed()}
 *         onCancel={() => blocker.reset()}
 *       />
 *     </>
 *   );
 */

import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';


// Browser-controlled default message. Modern browsers ignore the string
// and show their own ("Reload site? Changes you made may not be saved.")
// but we keep the value here for older browsers + clarity.
const DEFAULT_BEFOREUNLOAD_MSG = 'Hai modifiche non salvate. Sei sicuro di voler uscire?';


export function useUnsavedChangesPrompt(isDirty, message = DEFAULT_BEFOREUNLOAD_MSG) {
  // ── In-app navigation (React Router 7 useBlocker) ─────────────────
  //
  // The blocker callback runs on EVERY navigation attempt. We block iff:
  //   · isDirty is true, AND
  //   · the next location is different from the current one (the router
  //     occasionally re-asserts the current pathname after a query-string
  //     change — we don't want to prompt for that).
  const blocker = useBlocker(({ currentLocation, nextLocation }) => (
    isDirty && currentLocation.pathname !== nextLocation.pathname
  ));

  // ── Native tab close / reload (beforeunload) ──────────────────────
  useEffect(() => {
    if (!isDirty) return undefined;
    const handler = (e) => {
      // Per spec: setting returnValue triggers the confirmation prompt.
      // The string is shown by some older browsers; modern Chrome /
      // Firefox / Safari show their own message.
      e.preventDefault();
      e.returnValue = message;
      return message;
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty, message]);

  return { blocker };
}


export default useUnsavedChangesPrompt;
