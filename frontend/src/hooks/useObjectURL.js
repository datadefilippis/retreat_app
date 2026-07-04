/**
 * useObjectURL — auto-revoking blob URL for File / Blob previews.
 *
 * 2026-05-20 — The audit found that EventWizard (riga 544, 555, 743,
 * 753) creates blob URLs with ``URL.createObjectURL(file)`` for image
 * previews but never calls ``URL.revokeObjectURL`` to release them.
 * Each unrevoked URL holds the underlying file in memory; in stress
 * testing the leak is visible in DevTools → Memory.
 *
 * The hook handles the lifecycle:
 *
 *   const previewUrl = useObjectURL(imageFile);
 *
 *   {previewUrl && <img src={previewUrl} alt="preview" />}
 *
 * Behaviour:
 *   · ``imageFile`` is null/undefined → returns null, nothing allocated.
 *   · ``imageFile`` changes → previous URL is revoked first, new one
 *     is allocated and returned.
 *   · Component unmounts → final URL is revoked.
 *   · ``imageFile`` is already a string (e.g. a remote URL from the
 *     server) → passes it through unchanged; never tries to revoke a
 *     string that wasn't created by ``createObjectURL``.
 *
 * The hook is safe to call with ANY shape ``imageFile`` may have during
 * a wizard: null (initial), File (user uploaded), string (server URL
 * loaded for edit-mode). Same code path for all.
 */

import { useEffect, useState } from 'react';


export function useObjectURL(fileOrBlob) {
  const [url, setUrl] = useState(() => _initial(fileOrBlob));

  useEffect(() => {
    // Pass-through: caller gave us a string URL (e.g. https://cdn/image.jpg)
    if (typeof fileOrBlob === 'string') {
      setUrl(fileOrBlob);
      return undefined;
    }
    // No file → clear and skip allocation.
    if (!fileOrBlob) {
      setUrl(null);
      return undefined;
    }
    // Defensive: not a Blob → don't try to call createObjectURL.
    if (typeof Blob !== 'undefined' && !(fileOrBlob instanceof Blob)) {
      setUrl(null);
      return undefined;
    }
    let allocated = null;
    try {
      allocated = URL.createObjectURL(fileOrBlob);
      setUrl(allocated);
    } catch {
      setUrl(null);
      return undefined;
    }
    return () => {
      if (allocated) {
        try { URL.revokeObjectURL(allocated); } catch { /* ignore */ }
      }
    };
  }, [fileOrBlob]);

  return url;
}


function _initial(fileOrBlob) {
  if (typeof fileOrBlob === 'string') return fileOrBlob;
  return null;
}


export default useObjectURL;
