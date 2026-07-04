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

import { useContext, useEffect } from 'react';
import { UNSAFE_DataRouterContext, useBlocker } from 'react-router-dom';


// Browser-controlled default message. Modern browsers ignore the string
// and show their own ("Reload site? Changes you made may not be saved.")
// but we keep the value here for older browsers + clarity.
const DEFAULT_BEFOREUNLOAD_MSG = 'Hai modifiche non salvate. Sei sicuro di voler uscire?';

// Blocker inerte per quando l'app NON gira dentro un data router.
const NOOP_BLOCKER = { state: 'unblocked', proceed: () => {}, reset: () => {} };


export function useUnsavedChangesPrompt(isDirty, message = DEFAULT_BEFOREUNLOAD_MSG) {
  // ── In-app navigation (React Router 7 useBlocker) ─────────────────
  //
  // BUG EREDITATO (fix retreat fork 4/7/2026): useBlocker richiede un
  // DATA router (createBrowserRouter/RouterProvider), ma App.js monta il
  // classico <BrowserRouter> → OGNI wizard che usa questo hook crashava
  // al mount con "useBlocker must be used within a data router" (mai
  // visto in BI_PMI: la CI non girava e l'error boundary lo mascherava).
  // Finché l'app non migra al data router, degradiamo con grazia: senza
  // contesto → blocker no-op (resta comunque la protezione beforeunload
  // su chiusura/reload del tab, che copre il caso peggiore).
  //
  // La presenza del contesto è FISSA per tutta la vita dell'app (il tipo
  // di router non cambia a runtime), quindi la chiamata condizionale
  // dell'hook ha ordine stabile ed è sicura.
  const dataRouterCtx = useContext(UNSAFE_DataRouterContext);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const blocker = dataRouterCtx ? useBlocker(({ currentLocation, nextLocation }) => (
    isDirty && currentLocation.pathname !== nextLocation.pathname
  )) : NOOP_BLOCKER;

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
