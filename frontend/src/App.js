import React, { useState, useCallback, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useParams } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { SiteConfigProvider, useSiteConfig } from "./context/SiteConfigContext";
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
const BlogIndexPage = lazy(() => import("./features/storefront/BlogIndexPage"));
const BlogArticlePage = lazy(() => import("./features/storefront/BlogArticlePage"));
const HowItWorksPage = lazy(() => import("./features/storefront/HowItWorksPage"));
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
import { trackPageView } from "./lib/analytics";
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
const EventsListPage = lazy(() => import("./features/events/EventsListPage"));
const EventWizard = lazy(() => import("./features/events/EventWizard"));
import RetreatsCalendarPage from "./features/storefront/RetreatsCalendarPage";
import OperatorProfilePage from "./features/storefront/OperatorProfilePage";
// PV3 — l'intervista Aurya su pagina propria, in continuità col profilo
import OperatorInterviewPage from "./features/storefront/OperatorInterviewPage";
import OperatorsIndexPage from "./features/storefront/OperatorsIndexPage";
import DestinationsPage from "./features/storefront/DestinationsPage";
const ServiceWizard = lazy(() => import("./features/services/ServiceWizard"));
const ListinoPage = lazy(() => import("./features/listino/ListinoPage"));
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
// PS3 — la vecchia pagina impostazioni store non e' piu' raggiungibile:
// la rotta /store-settings (mai linkata, autodichiarata deprecata) ora
// redirige a /settings. Il file resta nel repo per il mondo legacy.
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
const VisibilityPage = lazy(() => import("./features/visibility/VisibilityPage"));
const OperatorLandingPage = lazy(() => import("./features/prelaunch/OperatorLandingPage"));
// RT1 — /cerca-ritiro redirige su /newsletter: il pubblico viaggiatori
// si coltiva in newsletter finche' non c'e' nulla da prenotare. Il
// componente TravelerLandingPage resta nel repo (il suo form torna
// utile in RT4).
const NewsletterLandingPage = lazy(() => import("./features/prelaunch/NewsletterLandingPage"));
const NewsletterConfirmPage = lazy(() => import("./features/prelaunch/NewsletterConfirmPage"));
const NewsletterPreferencesPage = lazy(() => import("./features/prelaunch/NewsletterPreferencesPage"));
// RT2 — le pagine della fase rete
const NetworkHomePage = lazy(() => import("./features/network/NetworkHomePage"));
const ManifestoPage = lazy(() => import("./features/network/ManifestoPage"));
// SW3 — Chi siamo torna una pagina propria: il Manifesto e' la
// posizione, Chi siamo sono le persone (sostituisce AboutAuryaPage,
// rimossa dal repo con la sua voce vecchia).
const ChiSiamoPage = lazy(() => import("./features/network/ChiSiamoPage"));
const NetworkOperatorsPage = lazy(() => import("./features/network/NetworkOperatorsPage"));
const CashflowDataPage = lazy(() => import("./features/cashflow/CashflowDataPage"));
const PosPage = lazy(() => import("./features/stores/PosPage"));
import StorefrontPage from "./features/storefront/StorefrontPage";
import EventLandingPage from "./features/storefront/EventLandingPage";
import TicketLandingPage from "./features/storefront/TicketLandingPage";
import AccountLoginPage from './features/account/AccountLoginPage';
import AccountVerifyEmailPage from './features/account/AccountVerifyEmailPage';
import AccountResetPasswordPage from './features/account/AccountResetPasswordPage';
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
import { CheckoutSuccessPage, CheckoutCancelPage, PayLinkUnavailablePage } from "./features/storefront/CheckoutResultPage";
const TeamPage = lazy(() => import("./features/team/TeamPage"));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage"));
const PublicProfilePage = lazy(() => import("./features/settings/PublicProfilePage"));
// PL17 — lazy come tutte le pagine admin: da eager trascinava Layout
// (e con lui TUTTE le traduzioni back-office) nel bundle pubblico.
const IniziaPage = lazy(() => import("./features/onboarding/IniziaPage"));
const AdminPage = lazy(() => import("./features/admin/AdminPage"));
const PlansPage = lazy(() => import("./pages/PlansPage"));

// Customer Identity Foundation (v9.0)
import { CustomerAuthProvider } from "./context/CustomerAuthContext";
import CustomerProtectedRoute from "./features/customer-portal/CustomerProtectedRoute";
// Auth pages — Phase 5 of the customer area refactor moved each one
// into a dedicated file under customer-portal/auth/. The shared
// AuthShell + useStoreInfo helpers live alongside.
// PS4 — restano SOLO le pagine strutturali per il player corsi legacy
// (login = target del gate CustomerProtectedRoute, recupero password e
// verifica email = link nelle email gia' spedite). La signup legacy e'
// rediretta: i nuovi utenti passano da /account/accedi (login Aurya).
import CustomerLoginPage from "./features/customer-portal/auth/LoginPage";
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
// PS4 — del portale clienti legacy restano SOLO i corsi (il player e
// il suo indice): le email "Vai al corso" gia' spedite puntano a
// /account/courses/<enrollment_id> e il player usa il JWT customer.
// Ordini e profilo legacy sono rediretti all'account Aurya (/account).
import CustomerCoursesIndexPage from "./features/customer-portal/pages/CoursesIndexPage";
import CustomerCoursePlayerPage from "./features/customer-portal/pages/CoursePlayerPage";

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

// RB3 — la SPA manteneva la posizione di scroll tra le pagine: chi
// navigava dal footer atterrava in FONDO alla pagina nuova. Al cambio
// di pathname si riparte dall'alto; i cambi di sola query (filtri,
// vista mappa) non scrollano, chi sta filtrando non va disturbato.
// HP2 — ...tranne quando l'URL porta un'ancora. Un link tipo
// /entra-nella-rete#presentati e' una destinazione precisa: mandarlo in
// cima alla pagina e' esattamente il bug che RB3 voleva risolvere, al
// contrario. Il router tiene la history in memoria, quindi il salto
// nativo del browser non avviene: lo facciamo qui, per TUTTE le ancore
// del sito e non caso per caso.
// Il bersaglio puo' arrivare in ritardo: le pagine sono lazy, quindi al
// commit della rotta l'ancora spesso non esiste ancora. Si riprova a
// intervalli per un paio di secondi, poi si smette in silenzio.
// Timer e non requestAnimationFrame: rAF viene sospeso quando la scheda
// non e' in primo piano, e chi apre un link con ancora in una scheda di
// sfondo la troverebbe in cima invece che sull'ancora.
// Salto sempre istantaneo: un'ancora si comporta come un'ancora, e
// nessuno vuole vedersi scorrere sotto gli occhi mezza pagina che non ha
// chiesto di vedere.
const ANCHOR_RETRY_MS = 60;
const ANCHOR_GIVE_UP_MS = 2000;

function ScrollToTop() {
  const { pathname, hash } = useLocation();
  React.useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0);
      return undefined;
    }
    let timer = 0;
    let waited = 0;
    const seek = () => {
      let el = null;
      // un hash qualsiasi (#, #!, caratteri strani) non deve far
      // esplodere querySelector e portarsi via la navigazione
      try { el = document.querySelector(hash); } catch { el = null; }
      if (el) {
        el.scrollIntoView({ behavior: 'auto', block: 'start' });
        return;
      }
      waited += ANCHOR_RETRY_MS;
      if (waited < ANCHOR_GIVE_UP_MS) timer = window.setTimeout(seek, ANCHOR_RETRY_MS);
    };
    seek();
    return () => window.clearTimeout(timer);
  }, [pathname, hash]);
  return null;
}

// PL4→RT2 — la home segue la fase: network = la home della rete
// (manifesto, Magazine, candidatura, newsletter), marketplace = la
// directory dei ritiri. Per TUTTI, anche l'admin loggato: vedi sempre
// cio' che vede il pubblico. Il back-office resta su /dashboard.
function HomeGate() {
  const { sitePhase, loading } = useSiteConfig();
  if (loading) return null;
  if (sitePhase === 'network') return <NetworkHomePage />;
  return <RetreatsCalendarPage />;
}

// RT1 (piano sito-rete) — in fase network la vetrina ritiri NON esiste
// per il visitatore: niente anteprima di campioni, il valore lo danno
// Magazine, Manifesto e (RT3) i profili della rete. In fase marketplace
// resta il redirect S0 alla home (la home È la directory).
function RitiriGate() {
  const { loading } = useSiteConfig();
  if (loading) return null;   // evita il redirect prima di sapere la fase
  // In entrambe le fasi /ritiri riporta alla home: in network la
  // vetrina non esiste, in marketplace la home E' la directory (S0).
  return <RedirectPreservingQuery to="/" />;
}

// PP2 — le pagine categoria seguono la stessa regola di /ritiri: in
// fase network la vetrina non esiste (i campioni sfocati che restavano
// qui erano un residuo dell'era prelaunch), in marketplace la
// categoria e' una pagina vera.
function RitiriCategoryGate() {
  const { sitePhase, loading } = useSiteConfig();
  if (loading) return null;
  if (sitePhase === 'network') return <RedirectPreservingQuery to="/" />;
  return <RetreatsCalendarPage />;
}

// PL23→RT3 — in fase network /operatori E' la landing della rete:
// cos'e', con che criterio si entra, le schede dei membri. In
// marketplace torna l'aggregatore pieno con mappa e filtri.
function OperatorsGate() {
  const { sitePhase, loading } = useSiteConfig();
  if (loading) return null;
  if (sitePhase === 'network') return <NetworkOperatorsPage />;
  return <OperatorsIndexPage />;
}

function DestinationsGate() {
  const { sitePhase, loading } = useSiteConfig();
  if (loading) return null;
  if (sitePhase === 'network') return <Navigate to="/" replace />;
  return <DestinationsPage />;
}

// LC2 — /come-funziona racconta il percorso d'acquisto (caparra,
// prenotazione, recensione): in fase network quel percorso non esiste
// e la pagina prometteva un marketplace spento. Il posto dove si
// spiega "come funziona Aurya" oggi e' il Manifesto.
function HowItWorksGate() {
  const { sitePhase, loading } = useSiteConfig();
  if (loading) return null;
  if (sitePhase === 'network') return <Navigate to="/manifesto" replace />;
  return <HowItWorksPage />;
}

// GA1 — una page_view per ogni navigazione SPA (config con
// send_page_view: false, quindi niente doppi conteggi).
// PS6.4 — oltre al ping analytics, si tiene traccia della ROTTA DI
// PROVENIENZA in sessionStorage (aurya:nav:prev): serve alle superfici
// di checkout per derivare il canale dell'ordine dalla superficie
// reale (profilo vs marketplace). Solo pathname; il refresh non
// sovrascrive prev (cur non cambia), quindi la provenienza sopravvive
// a un F5 sulla landing.
function AnalyticsPageViews() {
  const location = useLocation();
  React.useEffect(() => {
    trackPageView(location.pathname + location.search);
    try {
      const cur = sessionStorage.getItem('aurya:nav:cur');
      if (cur !== location.pathname) {
        if (cur) sessionStorage.setItem('aurya:nav:prev', cur);
        sessionStorage.setItem('aurya:nav:cur', location.pathname);
      }
    } catch { /* storage inaccessibile: nessuna provenienza */ }
  }, [location.pathname, location.search]);
  return null;
}

// TW3 (piano Listino) — la vetrina /s/{slug} e' migrata sul profilo
// /o/{slug}: redirect SPA (gli URL non muoiono mai, invariante I6).
// Le pagine legal (/s/x/privacy, /terms) e checkout restano vive.
// RS3 fix — /s/x?checkout=1 e' l'handoff del checkout dalle landing
// /e/ e /p/: DEVE aprire il modale sullo storefront, non redirigere
// al profilo (I2, I3: il motore di acquisto non si tocca).
// PS6.1 — il consenso al checkout va LATCHATO al mount: StorefrontPage
// consuma ?checkout=1 (strip del param con navigate replace) e azzera il
// Router state dopo l'idratazione; senza latch questa guardia rivaluterebbe
// wantsCheckout=false e rimbalzerebbe al profilo A MODALE APERTO.
function StoreToProfileRedirect() {
  const { slug } = useParams();
  const location = useLocation();
  const [grant] = React.useState(() =>
    new URLSearchParams(location.search).has('checkout')
    || Boolean(location.state?.preloadCart));
  if (grant) return <StorefrontPage />;
  return <Navigate to={`/o/${slug}`} replace />;
}

function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
    <AnalyticsPageViews />
    <Routes>
      {/* S0.1 — la ROOT è il marketplace: la pagina con l'autorità
          del dominio è la directory pubblica, non la login operatori.
          Chi è loggato vede comunque la home pubblica (il back-office
          si raggiunge dal menu / da /dashboard). */}
      <Route path="/" element={<HomeGate />} />
      {/* RT1 (piano sito-rete) — la sitemap della fase rete. Gli URL
          nuovi nascono ORA e non cambieranno mai; i contenuti si
          riempiono nelle onde successive (RT2 manifesto+home, RT3
          rete, RT4 newsletter). I vecchi URL redirigono. */}
      <Route path="/manifesto" element={<ManifestoPage />} />
      <Route path="/entra-nella-rete" element={<OperatorLandingPage />} />
      <Route path="/newsletter" element={<NewsletterLandingPage />} />
      {/* BN2 — pagine token del double opt-in (noindex, servite 200 dalla shell) */}
      <Route path="/newsletter/conferma/:token" element={<NewsletterConfirmPage />} />
      <Route path="/newsletter/preferenze/:token" element={<NewsletterPreferencesPage />} />
      {/* HP2 — /magazine e' il nome che il brand usa a voce (header,
          footer, home). La rotta CANONICA resta /blog: e' quella in
          sitemap, gia' indicizzata e spinta con IndexNow, e non si
          rinomina per una questione di lessico. /magazine esiste come
          alias cosi' chi lo digita o lo trova scritto arriva a casa.
          Promuovere /magazine a canonica e' una decisione SEO a se':
          servirebbero sitemap, 301 lato server e un nuovo IndexNow. */}
      <Route path="/magazine" element={<Navigate to="/blog" replace />} />
      {/* HP5 — stessa storia di /magazine: "la rete" e' il nome che il
          brand usa a voce, /operatori e' l'indirizzo canonico gia' in
          sitemap. L'alias esiste perche' chi digita /rete deve arrivare
          a casa, non su un 404. */}
      <Route path="/rete" element={<Navigate to="/operatori" replace />} />
      {/* SW3 — /chi-siamo e' una pagina vera, non piu' un redirect sul
          Manifesto: il footer di fase rete la linka e chi ci clicca
          deve trovare le persone, non la posizione. */}
      <Route path="/chi-siamo" element={<ChiSiamoPage />} />
      {/* redirect permanenti dei vecchi percorsi */}
      <Route path="/per-operatori" element={<Navigate to="/entra-nella-rete" replace />} />
      <Route path="/cerca-ritiro" element={<Navigate to="/newsletter" replace />} />
      {/* S0.1 — la login operatori vive su /login (via dalla root) */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route path="/come-funziona" element={<HowItWorksGate />} />
      {/* AN5 — il blog di Aurya */}
      {/* SEO1 (11/7, decisione founder): il blog è il motore SEO del
          pre-lancio e resta SEMPRE attivo, flag o non flag. */}
      <Route path="/blog" element={<BlogIndexPage />} />
      {/* BN5 — hub categoria indicizzabili (rotta vera, non query param) */}
      <Route path="/blog/categoria/:categoria" element={<BlogIndexPage />} />
      <Route path="/blog/:slug" element={<BlogArticlePage />} />
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
      {/* PS6.3 — atterraggio dei link /pay/{token} non piu' servibili:
          il backend reindirizza qui, mai piu' JSON nudo da email. */}
      <Route path="/s/pay-non-disponibile" element={<PayLinkUnavailablePage />} />
      {/* Wave GDPR-Commerce CG-2 — public per-store legal pages.
          The merchant edits docs in /settings/gdpr; here we serve the
          published version in their chosen display_locale (the same
          to all customers regardless of their UI language). */}
      <Route path="/s/:slug/privacy" element={<StorefrontPrivacyPage />} />
      <Route path="/s/:slug/terms" element={<StorefrontTermsPage />} />
      <Route path="/s/:slug" element={<StoreToProfileRedirect />} />
      {/* Phase 7.5 — per-category storefront page.
          Renders the SAME StorefrontPage component as `/s/:slug`; the
          page reads `useParams().category` and filters the product
          grid to a single item-type bucket. Cart state survives the
          remount because useStorefrontCart persists via sessionStorage
          (scoped by store slug — see hooks/useCartStorage.js). The
          root route `/s/:slug` redirects to the first non-empty
          category once the catalog loads, so visitors landing on
          the root URL get sent to a populated category page. */}
      <Route path="/s/:slug/c/:category" element={<StoreToProfileRedirect />} />
      {/* S3 — Chi siamo DENTRO il guscio store: stessa shell, stesso
          carrello; il contenuto e' il profilo pubblico. /o/:slug resta
          per il contesto directory. */}
      <Route path="/s/:slug/chi-siamo" element={<StoreToProfileRedirect />} />
      {/* E3: public event landing page — deep-link per-occurrence.
          Has StorefrontHeader → its inline switcher covers /e, no
          floating dup. */}
      {/* /ritiri → home: la directory È la home (S0.1). Redirect che
          PRESERVA la query (?categoria=... dai link footer/condivisi). */}
      <Route path="/ritiri" element={<RitiriGate />} />
      <Route path="/ritiri/:categoria" element={<RitiriCategoryGate />} />
      <Route path="/ritiri/:categoria/:regione" element={<RitiriCategoryGate />} />
      {/* S2 — aggregatori pubblici: organizzatori, destinazioni, esperienze */}
      <Route path="/operatori" element={<OperatorsGate />} />
      {/* LM3+ — anteprima pubblica del marketplace operatori, NON
          linkata nei menu (richiesta founder 29/7): stessa pagina
          della fase marketplace, raggiungibile solo via URL diretto */}
      <Route path="/esplora-operatori" element={<OperatorsIndexPage />} />
      <Route path="/esplora-operatori/:categoria" element={<OperatorsIndexPage />} />
      {/* PN (richiesta founder 29/7) — anteprima non linkata della
          directory ritiri: stessa pagina di /ritiri (marketplace) in
          OGNI fase, con dati veri via ?preview=1 e noindex. Nessuna
          voce di menu: si raggiunge solo via URL diretto. */}
      <Route path="/esplora-ritiri" element={<RetreatsCalendarPage />} />
      <Route path="/esplora-ritiri/:categoria" element={<RetreatsCalendarPage />} />
      <Route path="/esplora-ritiri/:categoria/:regione" element={<RetreatsCalendarPage />} />
      <Route path="/operatori/:categoria" element={<OperatorsGate />} />
      <Route path="/destinazioni" element={<DestinationsGate />} />
      <Route path="/destinazioni/:luogo" element={<DestinationsGate />} />
      {/* DS3 (decisione founder 7/7): /esperienze fuori per ora — la
          pagina resta nel repo (storefront/), pronta a tornare */}
      <Route path="/esperienze/*" element={<Navigate to="/" replace />} />
      <Route path="/o/:org_slug" element={<OperatorProfilePage />} />
      {/* PV3 — pagina intervista pubblica: stessa testata del profilo,
          redirect a /o/:slug se l'intervista non è pubblicata */}
      <Route path="/o/:org_slug/intervista" element={<OperatorInterviewPage />} />

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
      <Route path="/account/verifica" element={<AccountVerifyEmailPage />} />
      <Route path="/account/nuova-password" element={<AccountResetPasswordPage />} />
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
      {/* Customer Portal legacy — PS4: UN SOLO login utente.
          Restano vive SOLO le rotte strutturali per il player corsi:
            /account/login           target del gate CustomerProtectedRoute
                                     (+ link dai checkout legacy /s/, /p/)
            /account/forgot-password linkata da /account/login e dalle
                                     email di recupero password
            /account/reset-password  link nelle email di reset (JWT customer)
            /account/verify-email    link nelle email di verifica firma
            /account/courses(+/:id)  player corsi: le email "Vai al corso"
                                     puntano a /account/courses/<enrollment_id>
          Tutto il resto del vecchio portale (signup, ordini, profilo)
          redirige alle rotte Aurya: la history acquisti vive in
          /account (platform account), il login unico e' /account/accedi. */}
      <Route path="/account/login" element={<CustomerLoginPage />} />
      <Route path="/account/signup" element={<Navigate to="/account/accedi" replace />} />
      <Route path="/account/forgot-password" element={<CustomerForgotPasswordPage />} />
      <Route path="/account/reset-password" element={<CustomerResetPasswordPage />} />
      <Route path="/account/verify-email" element={<CustomerVerifyEmailPage />} />
      {/* Ordini e profilo legacy → account Aurya (vecchie email
          /account/orders/<id> atterrano sul gate /account, che senza
          token piattaforma rimanda a /account/accedi). */}
      <Route path="/account/orders" element={<Navigate to="/account" replace />} />
      <Route path="/account/orders/:orderId" element={<Navigate to="/account" replace />} />
      <Route path="/account/profile" element={<Navigate to="/account" replace />} />

      {/* ── Player corsi legacy — nested under <CustomerLayout> ───────
          Gated dal JWT customer (CustomerProtectedRoute). Il doppio
          /account che viveva qui (redirect morto a /account/orders,
          oscurato dalla rotta Aurya sopra) e' stato potato in PS4. */}
      <Route element={<CustomerProtectedRoute><CustomerLayout /></CustomerProtectedRoute>}>
        <Route path="/account/courses" element={<CustomerCoursesIndexPage />} />
        <Route path="/account/courses/:enrollment_id" element={<CustomerCoursePlayerPage />} />
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
      {/* RS1 — Ritiri e' una pagina di ritiri: niente hub multi-tipo.
          ProductsPage resta viva su /products per il commerce legacy. */}
      <Route
        path="/events"
        element={<ProtectedRoute><EventsListPage /></ProtectedRoute>}
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
        path="/listino"
        element={<ProtectedRoute><ListinoPage /></ProtectedRoute>}
      />
      {/* TW1 — la creazione servizi passa dal Listino; il wizard resta
          l'editor AVANZATO su /services/:id */}
      <Route
        path="/services/new"
        element={<Navigate to="/listino" replace />}
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
      {/* PS3 — rotta deprecata: le impostazioni vivono in /settings */}
      <Route path="/store-settings" element={<Navigate to="/settings" replace />} />
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
      {/* BN2 — /newsletter e' del PUBBLICO (landing lettera): il modulo
          newsletter degli operatori vive su /newsletter-forms (il path
          pubblico veniva matchato per primo e oscurava questa pagina) */}
      <Route
        path="/newsletter-forms"
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
      {/* VT5 — specchietto visibilita' operatore */}
      <Route
        path="/visibilita"
        element={
          <ProtectedRoute>
            <VisibilityPage />
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
        <SiteConfigProvider>
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
                <ScrollToTop />
                <AppRoutes />
                <Toaster position="top-right" richColors />
              </EntitlementsProvider>
            </AiAccessProvider>
          </BillingProvider>
          </CustomerAuthProvider>
        </AuthProvider>
        </SiteConfigProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
