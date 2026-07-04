/**
 * useStoreMeta — accessor hook for the StoreMetaContext.
 *
 * Lives in /hooks (rather than next to the context file) so call sites
 * can import it from a stable path matching the rest of the hooks
 * (`useStorefrontLocale`, `useCartCount`, …) without leaking the context
 * implementation detail.
 *
 * Usage:
 *
 *   function MyLanding() {
 *     const { storefrontLanguages, storeInfo, status } = useStoreMeta();
 *     if (status === 'loading') return <Skeleton />;
 *     // …
 *   }
 *
 * Defensive: when called outside `<StoreMetaProvider>`, returns the
 * default value (status='idle'). Components that need the data must
 * branch on `status`; `storefrontLanguages` may legitimately be null
 * during loading or when no provider is mounted.
 */

import { useStoreMetaContext } from '../context/StoreMetaContext';


export function useStoreMeta() {
  return useStoreMetaContext();
}
