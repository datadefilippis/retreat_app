/**
 * Route guard for customer portal pages.
 *
 * Redirects to /account/login if not authenticated as a customer, with
 * two pieces of context preserved so the experience survives an email
 * landing on a brand-new device:
 *
 *   ?store=<slug>   from the current URL when present (the email
 *                   builder embeds it), with localStorage as a
 *                   fallback. The previous version of this guard read
 *                   ONLY the context's storeSlug, which comes from
 *                   localStorage — so a customer opening an order
 *                   email on a device that had never visited the
 *                   storefront landed on /account/login with no slug
 *                   and login surfaced "Account non esiste per questo
 *                   store" even though the URL had everything we
 *                   needed.
 *
 *   ?next=<path>    where the customer was trying to go. AuthPage
 *                   reads this after a successful login so the
 *                   customer lands directly on the deep page
 *                   (/account/orders/<id>) instead of the generic
 *                   orders list.
 *
 * The `next` value is sanitised to internal absolute paths only —
 * `http://attacker.com` would otherwise turn this into an open-
 * redirect vector. AuthPage validates again on the way out so the
 * trust boundary is symmetric.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useCustomerAuth } from '../../context/CustomerAuthContext';

const CustomerProtectedRoute = ({ children }) => {
  const { isCustomerAuthenticated, loading, storeSlug } = useCustomerAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!isCustomerAuthenticated) {
    // 1. Slug priority: query string on the current URL > context (localStorage).
    //    The query string wins because the email link is the most authoritative
    //    source — the customer arrived FROM that storefront moments ago.
    const params = new URLSearchParams(location.search);
    const urlSlug = params.get('store');
    const slug = urlSlug || storeSlug || '';

    // 2. `next` = where they were heading. We pass the path + the rest
    //    of the query string (minus `store` itself, which is rebuilt
    //    above) so AuthPage can route them straight to the deep page
    //    after login. Skip if they were already on /account/login.
    let nextParam = '';
    if (location.pathname && !location.pathname.startsWith('/account/login')
        && !location.pathname.startsWith('/account/signup')) {
      // Strip `store` from the query — the rebuilt URL re-adds it as a
      // top-level param so we don't ship the same key twice.
      params.delete('store');
      const remainingQs = params.toString();
      const fullPath = remainingQs
        ? `${location.pathname}?${remainingQs}`
        : location.pathname;
      nextParam = encodeURIComponent(fullPath);
    }

    const search = [
      slug && `store=${encodeURIComponent(slug)}`,
      nextParam && `next=${nextParam}`,
    ].filter(Boolean).join('&');

    const loginUrl = search ? `/account/login?${search}` : '/account/login';
    return <Navigate to={loginUrl} replace />;
  }

  return children;
};

export default CustomerProtectedRoute;
