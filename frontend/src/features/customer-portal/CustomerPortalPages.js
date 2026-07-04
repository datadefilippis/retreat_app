/**
 * CustomerPortalPages — backward-compatibility shim (Phase 6).
 *
 * Until Phase 5 of the customer area refactor this file was a 1170-line
 * monolith holding login + signup + forgot/reset/verify + the orders
 * page + the order-detail page, all glued together with inline helpers
 * (AuthShell, EmailVerificationBanner, MyCoursesPreview, STATUS_BADGES).
 *
 * Refactor map:
 *   • Auth pages (Login / Signup / Forgot / Reset / VerifyEmail)
 *       → moved to ./auth/*Page.jsx
 *   • Shared chrome AuthShell + useStoreInfo hook
 *       → ./auth/AuthShell.jsx
 *   • EmailVerificationBanner
 *       → ./layout/EmailVerificationBanner.jsx
 *   • Orders list (CustomerPortalPage)
 *       → REPLACED by ./pages/HomePage.jsx (new dashboard) +
 *         ./pages/OrdersPage.jsx (full list under <CustomerLayout>)
 *   • Order detail (CustomerOrderDetailPage)
 *       → ./pages/OrderDetailPage.jsx
 *   • STATUS_BADGES + resolveOrderBadge + formatItemsSummary
 *       → ./utils/orderStatus.js
 *   • MyCoursesPreview inline tile
 *       → ./components/CoursePreviewCard.jsx
 *
 * After Phase 5 the only external consumer of this file (App.js) was
 * already cut over to the new auth/ folder. We keep the file alive as
 * a thin re-export so any forgotten importer (tests, snippets, future
 * code paths copy-pasted from old commits) continues to resolve. The
 * dead `CustomerPortalPage` and `CustomerOrderDetailPage` named
 * exports are intentionally NOT re-exposed — their replacements live
 * under different routes (the dashboard at `/account` and the new
 * detail page at `/account/orders/:id`) so any old import would point
 * at code that was never meant to ship in the new IA.
 *
 * Phase 7 may delete this file outright once we're confident no
 * external surface relies on it. For now: ~30 lines instead of 1170,
 * which is the cleanup value we wanted from this phase.
 */

export { default as CustomerLoginPage } from './auth/LoginPage';
export { default as CustomerSignupPage } from './auth/SignupPage';
export { default as CustomerForgotPasswordPage } from './auth/ForgotPasswordPage';
export { default as CustomerResetPasswordPage } from './auth/ResetPasswordPage';
export { default as CustomerVerifyEmailPage } from './auth/VerifyEmailPage';
