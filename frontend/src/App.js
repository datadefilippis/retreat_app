import React, { useState, useCallback, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AiAccessProvider } from "./hooks/useAiAccess";
import { BillingProvider } from "./hooks/useBilling";
import { EntitlementsProvider } from "./hooks/useEntitlements";
import { Toaster } from "./components/ui/sonner";
import ErrorBoundary from "./components/ErrorBoundary";
import { ReadOnlyGraceBanner } from "./components/ReadOnlyGraceBanner";
// v5.8 / Onda 9.R — QuotaExceededBanner removed (replaced by QuotaExceededPaywall modal)
// import { QuotaExceededBanner } from "./components/QuotaExceededBanner";
import { BillingStatusBanner } from "./components/BillingStatusBanner";
import ModuleAccessPaywall from "./components/ModuleAccessPaywall";
import QuotaExceededPaywall from "./components/QuotaExceededPaywall";

// Pages
import { LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from "./pages/AuthPages";
// Onda 28 — blocking page for authenticated users who haven't verified
// their email yet. Wrapped by RequireAuthOnly (defined in this file).
const VerifyEmailRequiredPage = lazy(() => import("./features/auth/VerifyEmailRequiredPage"));
import PrivacyPolicyPage from "./pages/PrivacyPolicyPage";
import TermsOfServicePage from "./pages/TermsOfServicePage";
import SubProcessorsPage from "./pages/SubProcessorsPage";
// Wave GDPR-Commerce Piece 1b (2026-05-19) — tokenised marketing unsubscribe page
import MarketingUnsubscribePage from "./pages/MarketingUnsubscribePage";
// Wave GDPR-Commerce CG-2 — public per-store legal pages
import { StorefrontPrivacyPage, StorefrontTermsPage } from "./pages/StorefrontLegalPage";
// Wave GDPR-Commerce CG-4 — blocking customer re-consent modal
import CustomerReconsentModal from "./features/customer-portal/CustomerReconsentModal";
// Wave GDPR-Admin Phase E — re-consent modal + cookie disclosure
import ReconsentModal from "./components/legal/ReconsentModal";
import CookieConsentBanner from "./components/legal/CookieConsentBanner";
const ModulesPage = lazy(() => import("./pages/ModulesPage"));

// Features
const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage"));
// CustomersLightPage legacy removed during Phase-3 single-brain
// consolidation. Its routes are served by CustomerInsightsPage.
const CustomerInsightsPage = lazy(() => import("./features/customer-insights/CustomerInsightsPage"));
const ProductPerformancePage = lazy(() => import("./features/product-catalog/ProductPerformancePage"));
const ProductsPage = lazy(() => import("./features/products/ProductsPage"));
const CheckInPage = lazy(() => import("./features/events/CheckInPage"));
const EventDashboardPage = lazy(() => import("./features/events/EventDashboardPage"));
const EventWizard = lazy(() => import("./features/events/EventWizard"));
import RetreatsCalendarPage from "./features/storefront/RetreatsCalendarPage";
import OperatorProfilePage from "./features/storefront/OperatorProfilePage";
import OperatorsIndexPage from "./features/storefront/OperatorsIndexPage";
import DestinationsPage from "./features/storefront/DestinationsPage";
import ExperiencesPage from "./features/storefront/ExperiencesPage";
const ServiceWizard = lazy(() => import("./features/services/ServiceWizard"));
const ReservationWizard = lazy(() => import("./features/reservations/ReservationWizard"));
const PhysicalWizard = lazy(() => import("./features/physicals/PhysicalWizard"));
const PhysicalDashboardPage = lazy(() => import("./features/physicals/PhysicalDashboardPage"));
const DigitalWizard = lazy(() => import("./features/digitals/DigitalWizard"));
const DigitalDashboardPage = lazy(() => import("./features/digitals/DigitalDashboardPage"));
// Release 4 (Courses) Step 2 — admin UI for video courses
const CoursesPage = lazy(() => import("./features/courses/CoursesPage"));
const CourseEditor = lazy(() => import("./features/courses/CourseEditor"));
const ReservationsDashboard = lazy(() => import("./features/reservations/ReservationsDashboard"));
const ReservationDashboardPage = lazy(() => import("./features/reservations/ReservationDashboardPage"));
const ServiceDashboardPage = lazy(() => import("./features/services/ServiceDashboardPage"));
const TicketsManagementPage = lazy(() => import("./features/events/TicketsManagementPage"));
const CustomersMgmtPage = lazy(() => import("./features/customers-mgmt/CustomersMgmtPage"));
const SuppliersPage = lazy(() => import("./features/suppliers/SuppliersPage"));
const OrdersPage = lazy(() => import("./features/orders/OrdersPage"));
const CalendarPage = lazy(() => import("./features/calendar/CalendarPage"));
const CouponsPage = lazy(() => import("./features/coupons/CouponsPage"));
const DataIntegrityPage = lazy(() => import("./features/data-integrity/DataIntegrityPage"));
const StoreSettingsPage = lazy(() => import("./features/store-settings/StoreSettingsPage"));
// Wave GDPR-Commerce CG-7 — admin DPA page
const DpaPage = lazy(() => import("./pages/DpaPage"));
// SetupPage removed in Fase 2 Track F Step 9 (replaced by the dynamic
// dashboard SetupWizardWidget in features/setup-wizard/). The /setup
// route below now redirects to /dashboard for backward-compat with any
// stale links/emails pointing at /setup.
const StoresPage = lazy(() => import("./features/stores/StoresPage"));
const NewsletterPage = lazy(() => import("./features/newsletter/NewsletterPage"));
const ReviewsAdminPage = lazy(() => import("./features/reviews/ReviewsAdminPage"));
const IncassiPage = lazy(() => import("./features/cashflow/IncassiPage"));
const CashflowDataPage = lazy(() => import("./features/cashflow/CashflowDataPage"));
const PosPage = lazy(() => import("./features/stores/PosPage"));
import StorefrontPage from "./features/storefront/StorefrontPage";
import EventLandingPage from "./features/storefront/EventLandingPage";
import TicketLandingPage from "./features/storefront/TicketLandingPage";
import AccountLoginPage from './features/account/AccountLoginPage';
import AccountPage from './features/account/AccountPage';
import BookingLandingPage from "./features/storefront/BookingLandingPage";
import ReservationConfirmationPage from "./features/storefront/ReservationConfirmationPage";
import ProductLandingPage from "./features/storefront/ProductLandingPage";
import ReservationLandingPage from "./features/storefront/ReservationLandingPage";
import PhysicalLandingPage from "./features/storefront/PhysicalLandingPage";
import DigitalLandingPage from "./features/storefront/DigitalLandingPage";
import CourseLandingPage from "./features/storefront/CourseLandingPage";
// Step 4 of the language-system refactor: wraps every public storefront
// surface with StoreMetaProvider + locale sync so the i18n resolver has
// the merchant's allowed-languages list available on first render.
import PublicStorefrontShell from "./features/storefront/PublicStorefrontShell";
import DownloadLandingPage from "./features/storefront/DownloadLandingPage";
import { CheckoutSuccessPage, CheckoutCancelPage } from "./features/storefront/CheckoutResultPage";
const TeamPage = lazy(() => import("./features/team/TeamPage"));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage"));
const PublicProfilePage = lazy(() => import("./features/settings/PublicProfilePage"));
import IniziaPage from "./features/onboarding/IniziaPage";
const AdminPage = lazy(() => import("./features/admin/AdminPage"));
const PlansPage = lazy(() => import("./pages/PlansPage"));

// Customer Identity Foundation (v9.0)
import { CustomerAuthProvider } from "./context/CustomerAuthContext";
import CustomerProtectedRoute from "./features/customer-portal/CustomerProtectedRoute";
// Auth pages — Phase 5 of the customer area refactor moved each one
// into a dedicated file under customer-portal/auth/. The shared
// AuthShell + useStoreInfo helpers live alongside. Phase 6 will turn
// the legacy CustomerPortalPages.js into a thin re-export shim.
import CustomerLoginPage from "./features/customer-portal/auth/LoginPage";
import CustomerSignupPage from "./features/customer-portal/auth/SignupPage";
import CustomerForgotPasswordPage from "./features/customer-portal/auth/ForgotPasswordPage";
import CustomerResetPasswordPage from "./features/customer-portal/auth/ResetPasswordPage";
import CustomerVerifyEmailPage from "./features/customer-portal/auth/VerifyEmailPage";

// Customer area refactor — Phase 3: portal pages now mount inside
// <CustomerLayout> (TopBar + Sidebar + email banner shared chrome).
// The legacy CustomerPortalPage / CustomerOrderDetailPage / MyCoursesPage
// imports are intentionally NOT re-added here — their routes are now
// served by the new pages/* below. The old files stay in the codebase
// for the auth re-exports above (until Phase 6 turns them into a shim).
import CustomerLayout from "./features/customer-portal/layout/CustomerLayout";
// Phase 4 dashboard HomePage was removed in a follow-up — it added an
// extra hop after login without delivering value over the orders list.
// /account now redirects straight to /account/orders (see route below).
import CustomerOrdersPage from "./features/customer-portal/pages/OrdersPage";
import CustomerOrderDetailPageNew from "./features/customer-portal/pages/OrderDetailPage";
import CustomerCoursesIndexPage from "./features/customer-portal/pages/CoursesIndexPage";
import CustomerCoursePlayerPage from "./features/customer-portal/pages/CoursePlayerPage";
import CustomerProfilePage from "./features/customer-portal/pages/ProfilePage";

// Protected Route Component
//
// Onda 28 — Email-verification gate. Requires:
//   1. authenticated (token + user)
//   2. user.email_verified === true
// (system_admin role bypasses #2 — operational continuity.)
//
// If authenticated but not yet verified, redirect to
// /verify-email-required, which is wrapped in RequireAuthOnly below
// (= the only protected page accessible to unverified users).
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Onda 28 — email verification gate. Strictly compare to false so
  // that legacy /me responses without the field (or transient race
  // conditions during context load) don't false-positive a redirect.
  if (user && user.role !== "system_admin" && user.email_verified === false) {
    return <Navigate to="/verify-email-required" replace />;
  }

  return children;
};

// RequireAuthOnly — wraps the /verify-email-required page only.
// Lets through any authenticated user EXCEPT one who's already
// verified (or is a system_admin) — those get redirected straight to
// /dashboard, since the verification page is irrelevant for them.
//
// Onda 28: this is the inverse gate of ProtectedRoute — it accepts
// users that ProtectedRoute rejects, and rejects users that
// ProtectedRoute accepts. The two together cleanly partition the
// authenticated user space without overlap.
const RequireAuthOnly = ({ children }) => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Already verified (or system_admin) → no reason to stay on the
  // verification page; bounce to dashboard.
  if (user && (user.role === "system_admin" || user.email_verified !== false)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// System Admin Route — only accessible to users with role === "system_admin".
// Regular org users (admin / user) are silently redirected to /dashboard.
const SystemAdminRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== "system_admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// S0.1 — redirect che porta la query string con sé (Navigate 'to' string
// la perderebbe: i link /ritiri?categoria=yoga devono filtrare la home).
const RedirectPreservingQuery = ({ to }) => {
  const location = useLocation();
  return <Navigate to={{ pathname: to, search: location.search }} replace />;
};

// S6 — fallback dei chunk lazy del back-office: stesso spinner delle
// route guard. Le pagine PUBBLICHE restano nel bundle principale (sono
// la superficie SEO e devono idratare subito).
const RouteFallback = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

// Public Route (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
    <Routes>
      {/* S0.1 — la ROOT è il marketplace: la pagina con l'autorità
          del dominio è la directory pubblica, non la login operatori.
          Chi è loggato vede comunque la home pubblica (il back-office
          si raggiunge dal menu / da /dashboard). */}
      <Route path="/" element={<RetreatsCalendarPage />} />
      {/* S0.1 — la login operatori vive su /login (via dalla root) */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      {/* Static legal pages — always accessible, no auth wrapper */}
      <Route path="/privacy" element={<PrivacyPolicyPage />} />
      <Route path="/terms" element={<TermsOfServicePage />} />
      {/* R5 — il footer marketplace punta a /termini (URL italiano):
          prima era un 404. Stessa pagina di /terms. */}
      <Route path="/termini" element={<TermsOfServicePage />} />
      {/* Wave GDPR-Admin Phase E — public sub-processor registry
          (GDPR Art. 28.3.i + 13.1.f). Discoverable independently from
          the full Privacy Policy text. */}
      <Route path="/legal/sub-processors" element={<SubProcessorsPage />} />
      {/* Wave GDPR-Commerce Piece 1b — public marketing-consent unsubscribe.
          Token in the path → no auth, no app chrome. The page handles
          its own brand header so the customer recognises afianco at the
          top while the call-to-action is about the merchant they're
          leaving (Art. 7(3) symmetry requirement). */}
      <Route path="/u/:token" element={<MarketingUnsubscribePage />} />
      {/* Public storefront — no auth, no layout
          --------------------------------------------------------------
          Each slug-bearing route is wrapped in <PublicStorefrontShell>
          so the i18n resolver and store branding work consistently
          across surfaces (Step 4 of the language-system refactor).

          Token-based routes (/t, /b, /d, /rsv) are intentionally NOT
          wrapped at this level: their slug is in the response payload,
          not the URL. Those landing pages mount their own
          <PublicStorefrontShell slug={data.store_slug}> after fetch. */}
      <Route path="/s/checkout-success" element={<CheckoutSuccessPage />} />
      <Route path="/s/checkout-cancel" element={<CheckoutCancelPage />} />
      {/* Wave GDPR-Commerce CG-2 — public per-store legal pages.
          The merchant edits docs in /settings/gdpr; here we serve the
          published version in their chosen display_locale (the same
          to all customers regardless of their UI language). */}
      <Route path="/s/:slug/privacy" element={<StorefrontPrivacyPage />} />
      <Route path="/s/:slug/terms" element={<StorefrontTermsPage />} />
      <Route path="/s/:slug" element={
        <PublicStorefrontShell slugParamName="slug" showFloatingSwitcher={false}>
          <StorefrontPage />
        </PublicStorefrontShell>
      } />
      {/* Phase 7.5 — per-category storefront page.
          Renders the SAME StorefrontPage component as `/s/:slug`; the
          page reads `useParams().category` and filters the product
          grid to a single item-type bucket. Cart state survives the
          remount because useStorefrontCart persists via sessionStorage
          (scoped by store slug — see hooks/useCartStorage.js). The
          root route `/s/:slug` redirects to the first non-empty
          category once the catalog loads, so visitors landing on
          the root URL get sent to a populated category page. */}
      <Route path="/s/:slug/c/:category" element={
        <PublicStorefrontShell slugParamName="slug" showFloatingSwitcher={false}>
          <StorefrontPage />
        </PublicStorefrontShell>
      } />
      {/* S3 — Chi siamo DENTRO il guscio store: stessa shell, stesso
          carrello; il contenuto e' il profilo pubblico. /o/:slug resta
          per il contesto directory. */}
      <Route path="/s/:slug/chi-siamo" element={
        <PublicStorefrontShell slugParamName="slug" showFloatingSwitcher={false}>
          <StorefrontPage aboutMode />
        </PublicStorefrontShell>
      } />
      {/* E3: public event landing page — deep-link per-occurrence.
          Has StorefrontHeader → its inline switcher covers /e, no
          floating dup. */}
      {/* /ritiri → home: la directory È la home (S0.1). Redirect che
          PRESERVA la query (?categoria=... dai link footer/condivisi). */}
      <Route path="/ritiri" element={<RedirectPreservingQuery to="/" />} />
      <Route path="/ritiri/:categoria" element={<RetreatsCalendarPage />} />
      <Route path="/ritiri/:categoria/:regione" element={<RetreatsCalendarPage />} />
      {/* S2 — aggregatori pubblici: organizzatori, destinazioni, esperienze */}
      <Route path="/operatori" element={<OperatorsIndexPage />} />
      <Route path="/operatori/:categoria" element={<OperatorsIndexPage />} />
      <Route path="/destinazioni" element={<DestinationsPage />} />
      <Route path="/destinazioni/:luogo" element={<DestinationsPage />} />
      <Route path="/esperienze" element={<ExperiencesPage />} />
      <Route path="/esperienze/:categoria" element={<ExperiencesPage />} />
      <Route path="/o/:org_slug" element={<OperatorProfilePage />} />

      <Route path="/e/:org_slug/:slug" element={
        <PublicStorefrontShell showFloatingSwitcher={false}><EventLandingPage /></PublicStorefrontShell>
      } />
      {/* Onda 13: generic product landing page (primarily services).
          Same StorefrontHeader → inline switcher only. */}
      <Route path="/p/:org_slug/:product_slug" element={
        <PublicStorefrontShell showFloatingSwitcher={false}><ProductLandingPage /></PublicStorefrontShell>
      } />
      {/* F1 Onda 8: public ticket landing — QR + event details for one holder */}
      <Route path="/t/:token" element={<TicketLandingPage />} />
      {/* P3 Passaporto Ritiri — area personale utente finale (pubblica, noindex) */}
      <Route path="/account/accedi" element={<AccountLoginPage />} />
      <Route path="/account" element={<AccountPage />} />
      {/* Onda 14: public booking landing — service appointment details + .ics */}
      <Route path="/b/:token" element={<BookingLandingPage />} />
      {/* Onda 16: public reservation landing (rental range + slot) */}
      <Route path="/r/:org_slug/:product_slug" element={
        <PublicStorefrontShell><ReservationLandingPage /></PublicStorefrontShell>
      } />
      {/* Release 2 (Physical) — dedicated public landing for physical products */}
      <Route path="/ph/:org_slug/:product_slug" element={
        <PublicStorefrontShell><PhysicalLandingPage /></PublicStorefrontShell>
      } />
      {/* Release 3 (Digital) — product landing + token-gated download landing */}
      <Route path="/dg/:org_slug/:product_slug" element={
        <PublicStorefrontShell><DigitalLandingPage /></PublicStorefrontShell>
      } />
      <Route path="/d/:access_token" element={<DownloadLandingPage />} />
      {/* Release 4 (Courses) — public landing for video courses */}
      <Route path="/co/:org_slug/:product_slug" element={
        <PublicStorefrontShell><CourseLandingPage /></PublicStorefrontShell>
      } />
      {/* Onda 16 Fase 5: post-confirmation reservation landing (token-based) */}
      <Route path="/rsv/:token" element={<ReservationConfirmationPage />} />
      {/* Customer Portal (v9.0) — separate from admin auth */}
      {/* ── Auth pages — kept OUTSIDE the CustomerLayout shell ──────────
          Login / signup / forgot-password / reset / verify-email use
          their own AuthShell (centered card, no sidebar). They never
          render the portal chrome. */}
      <Route path="/account/login" element={<CustomerLoginPage />} />
      <Route path="/account/signup" element={<CustomerSignupPage />} />
      <Route path="/account/forgot-password" element={<CustomerForgotPasswordPage />} />
      <Route path="/account/reset-password" element={<CustomerResetPasswordPage />} />
      <Route path="/account/verify-email" element={<CustomerVerifyEmailPage />} />

      {/* ── Customer portal pages — nested under <CustomerLayout> ───────
          Every authenticated page renders inside the shell (TopBar +
          Sidebar + email verify banner). The pages themselves only
          return their specific content; the layout provides the chrome.

          /account               → redirect to /account/orders
                                   (the dashboard HomePage was tried
                                   in an earlier phase but removed —
                                   the orders list is value enough).
          /account/orders        → OrdersPage (the customer's home now)
          /account/orders/:id    → OrderDetailPage
          /account/courses       → CoursesIndexPage
          /account/courses/:id   → CoursePlayerPage
          /account/profile       → ProfilePage (account + password +
                                   email verification)

          ProtectedRoute is wrapped around the layout itself so
          everything below is gated by the customer JWT. */}
      <Route element={<CustomerProtectedRoute><CustomerLayout /></CustomerProtectedRoute>}>
        {/* /account is a thin redirect to the orders list. The
            previous Phase 4 dashboard HomePage was removed because
            it added an extra hop after login without delivering
            value over the orders list itself. The orders list IS
            the customer portal home now. */}
        <Route path="/account" element={<Navigate to="/account/orders" replace />} />
        <Route path="/account/orders" element={<CustomerOrdersPage />} />
        <Route path="/account/orders/:orderId" element={<CustomerOrderDetailPageNew />} />
        <Route path="/account/courses" element={<CustomerCoursesIndexPage />} />
        <Route path="/account/courses/:enrollment_id" element={<CustomerCoursePlayerPage />} />
        {/* Phase 4 — new ProfilePage (account data + password + email
            verification). The Profilo entry in the sidebar lands here. */}
        <Route path="/account/profile" element={<CustomerProfilePage />} />
      </Route>
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <SignupPage />
          </PublicRoute>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <PublicRoute>
            <ForgotPasswordPage />
          </PublicRoute>
        }
      />
      {/* Reset-password is intentionally NOT wrapped in PublicRoute so that  */}
      {/* an already-logged-in user can still follow a reset link if needed.  */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      {/* Email verification — public, no auth wrapper (user clicks link from email) */}
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      {/* Onda 28 — blocking page for authenticated-but-unverified users.
          Wrapped by RequireAuthOnly so:
            - unauthenticated users bounce to "/"
            - already-verified or system_admin users bounce to /dashboard
            - authenticated-but-unverified users see the page (and only this page) */}
      <Route
        path="/verify-email-required"
        element={
          <RequireAuthOnly>
            <VerifyEmailRequiredPage />
          </RequireAuthOnly>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      {/* Customer insights — both URLs serve the same component:
            • /modules/customers-light   canonical merchant URL
              (preserved across the legacy cutover; the sidebar menu
              link still points here)
            • /modules/customer-insights alias kept for anyone who
              bookmarked the Phase-2 URL during the short rollout
          The legacy /modules/_legacy/customers-light route was
          removed when the legacy package was deleted. */}
      <Route
        path="/modules/customers-light"
        element={
          <ProtectedRoute>
            <CustomerInsightsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/modules/customer-insights"
        element={
          <ProtectedRoute>
            <CustomerInsightsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/modules/product-catalog"
        element={
          <ProtectedRoute>
            <ProductPerformancePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/modules"
        element={
          <ProtectedRoute>
            <ModulesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={<ProtectedRoute><ProductsPage /></ProtectedRoute>}
      />
      {/* Onda 7 M1 — /events is now embedded inside /products?type=event_ticket.
          Keep this redirect so existing bookmarks and the old sidebar link
          still land on the unified hub. EventsListPage retained for now as
          a backward-compat wrapper (see its own comment). */}
      <Route
        path="/events"
        element={<Navigate to="/products?type=event_ticket" replace />}
      />
      {/* G2: guided event creation wizard (dedicated flow for event_ticket) */}
      <Route
        path="/events/new"
        element={<ProtectedRoute><EventWizard /></ProtectedRoute>}
      />
      {/* E6: unified admin dashboard for one event occurrence */}
      <Route
        path="/events/:occurrence_id"
        element={<ProtectedRoute><EventDashboardPage /></ProtectedRoute>}
      />
      {/* F5 Onda 12: service wizard + dashboard (consulenze, servizi a slot) */}
      <Route
        path="/services/new"
        element={<ProtectedRoute><ServiceWizard /></ProtectedRoute>}
      />
      <Route
        path="/services/:product_id"
        element={<ProtectedRoute><ServiceDashboardPage /></ProtectedRoute>}
      />
      {/* Onda 16 — Reservation wizard (unified rental + slot) */}
      <Route
        path="/reservations/new"
        element={<ProtectedRoute><ReservationWizard /></ProtectedRoute>}
      />
      {/* Release 2 (Physical) — dedicated wizard for item_type=physical */}
      <Route
        path="/physicals/new"
        element={<ProtectedRoute><PhysicalWizard /></ProtectedRoute>}
      />
      <Route
        path="/physicals/:product_id"
        element={<ProtectedRoute><PhysicalDashboardPage /></ProtectedRoute>}
      />
      {/* Release 3 (Digital) — wizard + dashboard for item_type=digital */}
      <Route
        path="/digitals/new"
        element={<ProtectedRoute><DigitalWizard /></ProtectedRoute>}
      />
      <Route
        path="/digitals/:product_id"
        element={<ProtectedRoute><DigitalDashboardPage /></ProtectedRoute>}
      />
      {/* Release 4 (Courses) — admin CRUD for video courses */}
      <Route
        path="/courses"
        element={<ProtectedRoute><CoursesPage /></ProtectedRoute>}
      />
      <Route
        path="/courses/new"
        element={<ProtectedRoute><CourseEditor /></ProtectedRoute>}
      />
      <Route
        path="/courses/:course_id"
        element={<ProtectedRoute><CourseEditor /></ProtectedRoute>}
      />
      {/* Onda 16 Fase 5 — Admin reservations dashboard (list di IssuedReservation) */}
      <Route
        path="/reservations"
        element={<ProtectedRoute><ReservationsDashboard /></ProtectedRoute>}
      />
      {/* Consolidamento UI prodotti — dashboard del singolo rental/reservation product */}
      <Route
        path="/reservations/:product_id"
        element={<ProtectedRoute><ReservationDashboardPage /></ProtectedRoute>}
      />
      {/* E5: admin door-scanner for an event occurrence */}
      <Route
        path="/events/:occurrence_id/check-in"
        element={<ProtectedRoute><CheckInPage /></ProtectedRoute>}
      />
      {/* G4: ticketing management — resend email, void single, broadcast */}
      <Route
        path="/events/:occurrence_id/tickets"
        element={<ProtectedRoute><TicketsManagementPage /></ProtectedRoute>}
      />
      <Route
        path="/customers"
        element={<ProtectedRoute><CustomersMgmtPage /></ProtectedRoute>}
      />
      <Route
        path="/suppliers"
        element={<ProtectedRoute><SuppliersPage /></ProtectedRoute>}
      />
      <Route
        path="/orders"
        element={<ProtectedRoute><OrdersPage /></ProtectedRoute>}
      />
      <Route
        path="/calendar"
        element={<ProtectedRoute><CalendarPage /></ProtectedRoute>}
      />
      {/* Coupons moved into StoresPage — redirect for bookmarks */}
      <Route path="/coupons" element={<Navigate to="/stores" replace />} />
      <Route
        path="/data-integrity"
        element={<ProtectedRoute><DataIntegrityPage /></ProtectedRoute>}
      />
      <Route
        path="/store-settings"
        element={<ProtectedRoute><StoreSettingsPage /></ProtectedRoute>}
      />
      {/* Wave GDPR-Commerce CG-7 — admin DPA (Data Processing Agreement)
          page. Required by GDPR Art. 28 for the platform↔merchant
          relationship. Protected: only the merchant org's admins. */}
      <Route
        path="/settings/legal/dpa"
        element={<ProtectedRoute><DpaPage /></ProtectedRoute>}
      />
      {/* Backward-compat redirect for any stale /setup link (emails,
          bookmarks, previous deploys). The dynamic Setup Wizard now
          lives as a widget on /dashboard — no dedicated page anymore. */}
      <Route
        path="/setup"
        element={<Navigate to="/dashboard" replace />}
      />
      <Route
        path="/stores"
        element={<ProtectedRoute><StoresPage /></ProtectedRoute>}
      />
      <Route
        path="/newsletter"
        element={<ProtectedRoute><NewsletterPage /></ProtectedRoute>}
      />
      <Route
        path="/pos/:storeId"
        element={<ProtectedRoute><PosPage /></ProtectedRoute>}
      />
      <Route
        path="/team"
        element={
          <ProtectedRoute>
            <TeamPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/plans"
        element={
          <ProtectedRoute>
            <PlansPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      {/* O2 — onboarding guidato: la checklist del primo avvio */}
      <Route
        path="/inizia"
        element={
          <ProtectedRoute>
            <IniziaPage />
          </ProtectedRoute>
        }
      />
      {/* F2.0 — editor del profilo pubblico operatore (/o/:slug) */}
      <Route
        path="/public-profile"
        element={
          <ProtectedRoute>
            <PublicProfilePage />
          </ProtectedRoute>
        }
      />
      {/* PR3 — plancia recensioni operatore */}
      <Route
        path="/reviews"
        element={
          <ProtectedRoute>
            <ReviewsAdminPage />
          </ProtectedRoute>
        }
      />
      {/* CF3 — tesoreria operatore */}
      <Route
        path="/incassi"
        element={
          <ProtectedRoute>
            <IncassiPage />
          </ProtectedRoute>
        }
      />
      {/* CG0 — pagina Dati ripristinata: registro vendite (sync ordini +
          manuale), spese, acquisti, costi fissi */}
      <Route
        path="/modules/cashflow/data/:tab?"
        element={
          <ProtectedRoute>
            <CashflowDataPage />
          </ProtectedRoute>
        }
      />

      {/* System Admin Control Panel — requires role === "system_admin" */}
      <Route
        path="/admin"
        element={
          <SystemAdminRoute>
            <AdminPage />
          </SystemAdminRoute>
        }
      />

      {/* Catch all - redirect to login */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}

function App() {
  // v6.0: Banner precedence — when BillingStatusBanner (blocking) is visible,
  // suppress the softer ReadOnlyGraceBanner to avoid confusing double banners.
  const [billingBannerVisible, setBillingBannerVisible] = useState(false);
  const handleBillingBannerVisible = useCallback((v) => setBillingBannerVisible(v), []);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <CustomerAuthProvider>
          <BillingProvider>
            <AiAccessProvider>
              <EntitlementsProvider>
                <BillingStatusBanner onVisible={handleBillingBannerVisible} />
                {!billingBannerVisible && <ReadOnlyGraceBanner />}
                {/* v5.8 / Onda 9.R — QuotaExceededBanner rimosso: era ridondante
                    con <QuotaExceededPaywall />. L'utente percepiva "popup duplicato"
                    + il banner appariva sotto la sidebar (z-index conflict).
                    Il modal paywall e' piu' chiaro, action-oriented, e non ha
                    problemi di z-index.
                <QuotaExceededBanner /> */}
                <QuotaExceededPaywall />
                <ModuleAccessPaywall />
                {/* Wave GDPR-Admin Phase E — blocking re-consent modal.
                    Self-gating: renders nothing unless the authenticated
                    user has consent_needs_refresh=true. Lives inside the
                    AuthProvider tree because it consumes useAuth(). */}
                <ReconsentModal />
                {/* Wave GDPR-Commerce CG-4 — customer-side parallel modal.
                    Self-gating on customer.consent_needs_refresh from
                    /api/customer/me. Mounted inside CustomerAuthProvider
                    because it consumes useCustomerAuth(). Renders
                    nothing in the happy path. */}
                <CustomerReconsentModal />
                {/* Wave GDPR-Admin Phase E — cookie / tracking disclosure.
                    Non-blocking; auto-hides after first acceptance
                    (localStorage afianco_cookie_disclosure_v1). Shown to
                    everyone (public + authenticated), which is what
                    transparency requires under ePrivacy Recital 25. */}
                <CookieConsentBanner />
                <AppRoutes />
                <Toaster position="top-right" richColors />
              </EntitlementsProvider>
            </AiAccessProvider>
          </BillingProvider>
          </CustomerAuthProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
