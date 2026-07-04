/**
 * LoginPage — route entry point for /account/login.
 *
 * Phase 5 of the customer area refactor. Thin wrapper around the
 * shared AuthPage component (which handles both login and signup
 * via a tab toggle). The route picks the initial tab; the customer
 * can still switch in-place without leaving the page.
 *
 * Why separate file? App.js routes need a stable default export per
 * route — using <AuthPage initialMode="login" /> directly inline is
 * also fine but a named file makes the route table more readable
 * and gives us a place to attach login-specific instrumentation
 * (analytics, A/B tests) without polluting AuthPage.
 */

import React from 'react';
import AuthPage from './AuthPage';

export default function LoginPage() {
  return <AuthPage initialMode="login" />;
}
