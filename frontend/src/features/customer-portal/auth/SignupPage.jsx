/**
 * SignupPage — route entry point for /account/signup.
 *
 * Phase 5 of the customer area refactor. Mirror of LoginPage:
 * picks the "Registrati" tab as the initial mode of the shared
 * AuthPage component. Customers can still toggle to login without
 * leaving the page.
 *
 * The signup flow itself (auto_login vs verification_required,
 * password rules, error handling) lives in AuthPage — see the
 * `handleSignup` callback there.
 */

import React from 'react';
import AuthPage from './AuthPage';

export default function SignupPage() {
  return <AuthPage initialMode="signup" />;
}
