/**
 * imageUploadFailedToast — persistent toast with Retry action.
 *
 * 2026-05-20 — Background: when a wizard succeeds the POST /products
 * but FAILS the subsequent uploadImage, the existing code shows a
 * silent ``toast.warning("Upload immagine fallito")`` that disappears
 * in 3-5 seconds. The user often misses it and ends up with a product
 * sitting in the catalog without an image, wondering why.
 *
 * The replacement:
 *   · sonner toast with ``duration: Infinity`` (stays until dismissed)
 *   · action button "Riprova" → calls the caller's onRetry()
 *   · cancel button "Ignora" → dismisses cleanly
 *
 * Usage:
 *
 *   try {
 *     await productsAPI.uploadImage(productId, file);
 *   } catch (err) {
 *     showImageUploadFailedToast({
 *       t,
 *       onRetry: () => productsAPI.uploadImage(productId, file),
 *     });
 *   }
 *
 * The toast is intentionally NOT auto-dismissed — losing an image upload
 * is a real concern that deserves merchant attention until acknowledged.
 */

import { toast } from 'sonner';


/**
 * @param {object} opts
 * @param {(key: string, fallback?: string|object) => string} [opts.t]
 *   Optional i18next ``t`` function for localised labels. When omitted,
 *   the toast uses Italian fallbacks (matches the primary market).
 * @param {() => Promise<any> | any} [opts.onRetry]
 *   Callback for the "Riprova" action button. The toast dismisses itself
 *   before invoking it; the caller is responsible for showing a fresh
 *   loading state.
 * @param {string} [opts.context]
 *   Optional extra context appended to the message (e.g. product name)
 *   so the merchant knows WHICH upload failed when multiple wizards are
 *   open in different tabs.
 */
export function showImageUploadFailedToast({ t, onRetry, context } = {}) {
  const tt = t || ((_k, opts) => (opts && opts.defaultValue) || _k);

  const baseMessage = tt('wizards.common.imageUpload.failed', {
    defaultValue: "Upload immagine fallito. Il prodotto è stato creato ma senza immagine.",
  });
  const message = context ? `${baseMessage} (${context})` : baseMessage;

  return toast.error(message, {
    duration: Infinity,  // stays until user acts
    action: onRetry
      ? {
          label: tt('wizards.common.imageUpload.retry', { defaultValue: 'Riprova' }),
          onClick: () => { onRetry(); },
        }
      : undefined,
    cancel: {
      label: tt('wizards.common.imageUpload.ignore', { defaultValue: 'Ignora' }),
      onClick: () => { /* noop — sonner dismisses on its own */ },
    },
  });
}


export default showImageUploadFailedToast;
