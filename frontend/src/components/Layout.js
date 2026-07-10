import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
// PL17 — side-effect: registra i namespace i18n del back-office.
// Layout è il guscio di OGNI pagina admin (tutte lazy): le traduzioni
// admin viaggiano nei loro chunk e si registrano prima del render,
// tenendo ~307KB gzip fuori dal bundle del visitatore pubblico.
import '../i18n-admin';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useEntitlements } from '../hooks/useEntitlements';
import {
  LayoutDashboard,
  Blocks,
  Bell,
  Sparkles,
  Settings,
  Users,
  TrendingUp,
  LogOut,
  Menu,
  X,
  ChevronDown,
  Database,
  ShieldAlert,
  Zap,
  Package,
  UserRound,
  Truck,
  ShoppingCart,
  CalendarDays,
  ShieldCheck,
  Store,
  Globe,
  Mail,
  Tag,
  Ticket,
  BookMarked,
  UserCircle,
  Star,
  Wallet,
  Eye,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
// 2026-05-22 — sidebar brand mark. Uses the white wordmark variant
// since the sidebar lives over the navy gradient background.
import { BrandLogo } from '../components/BrandLogo';
import { modulesAPI } from '../api/modules';
import { useTranslation } from 'react-i18next';

// ─── Sidebar context (condiviso tra Sidebar, Header, AppLayout) ──────────────

const SidebarContext = createContext({ open: false, setOpen: () => {} });
export const useSidebar = () => useContext(SidebarContext);

// ─── Navigazione: parte fissa (sempre visibile) ──────────────────────────────
// nameKey maps to common:nav.* translations. Resolved at render time in Sidebar.
const fixedNavTop = [
  { nameKey: 'nav.dashboard', href: '/dashboard', icon: LayoutDashboard, end: true },
];

// Mappa module_key → voce menu (solo moduli con pagina dedicata)
// ── Module-aware nav entries (merged entity + intelligence) ──────────────

const moduleNavMap = {
  // R4: cashflow_monitor rimosso (BI legacy); commerce_signals dentro
  // customers_light (nessuna voce standalone).
};

// Operations — always visible
const operationsNav = [
  { nameKey: 'nav.orders',          href: '/orders',          icon: ShoppingCart, end: true },
  { nameKey: 'nav.calendar',        href: '/calendar',        icon: CalendarDays, end: true },
  { nameKey: 'nav.stores',          href: '/stores',           icon: Globe,        end: true },
  // PR1 — la vetrina dell'operatore raggiungibile dal menu
  { nameKey: 'nav.public_profile',  href: '/public-profile',    icon: UserCircle,   end: true },
  { nameKey: 'nav.newsletter',      href: '/newsletter',       icon: Mail,         end: true },
];

// System — admin tools
const systemNav = [
  { nameKey: 'nav.modules',         href: '/modules',         icon: Blocks,      end: true },
  { nameKey: 'nav.data_integrity',  href: '/data-integrity',  icon: ShieldCheck, end: true },
  { nameKey: 'nav.team',            href: '/team',            icon: Users },
  { nameKey: 'nav.settings',        href: '/settings',        icon: Settings },
];

// ─── NavGroup (collapsible submenu) ──────────────────────────────────────────

const NavGroup = ({ item, navLinkClass, location }) => {
  const { t } = useTranslation('common');
  const resolve = (navItem) => navItem.nameKey ? t(navItem.nameKey) : navItem.name;

  const isChildActive = item.children.some((child) =>
    child.end
      ? location.pathname === child.href
      : location.pathname.startsWith(child.href)
  );
  const [expanded, setExpanded] = useState(isChildActive);

  // Auto-expand when a child becomes active
  useEffect(() => {
    if (isChildActive) setExpanded(true);
  }, [isChildActive]);

  return (
    <div>
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`group flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isChildActive
            ? 'text-white'
            : 'text-white/60 hover:bg-white/10 hover:text-white'
        }`}
      >
        <item.icon className="h-4 w-4" />
        <span className="flex-1 text-left">{resolve(item)}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>
      {expanded && (
        <div className="ml-4 mt-1 space-y-1 border-l border-white/20 pl-3">
          {item.children.map((child) => (
            <NavLink
              key={child.href}
              to={child.href}
              end={child.end}
              data-testid={`nav-${(child.nameKey || child.name || '').toLowerCase().replace(/[\s.]+/g, '-')}`}
              className={navLinkClass}
            >
              {child.icon && <child.icon className="h-3.5 w-3.5" />}
              {!child.icon && <TrendingUp className="h-3.5 w-3.5" />}
              {resolve(child)}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Sidebar ─────────────────────────────────────────────────────────────────

export const Sidebar = () => {
  const { user, logout } = useAuth();
  // Consolidamento WS-2 — gating a grana fine del menu (feature-key)
  const { canUse } = useEntitlements();
  const { t } = useTranslation('common');
  const navigate = useNavigate();
  const location = useLocation();
  const { open, setOpen } = useSidebar();
  const [activeModuleKeys, setActiveModuleKeys] = useState([]);
  const [unseenOrders, setUnseenOrders] = useState(0);

  const resolveName = (item) => item.nameKey ? t(item.nameKey) : item.name;

  // Poll unseen order count every 60s
  useEffect(() => {
    if (!user) return;
    const fetchUnseen = async () => {
      try {
        const { ordersAPI } = await import('../api');
        const res = await ordersAPI.getUnseenCount();
        setUnseenOrders(res.data?.unseen_count || 0);
      } catch { /* empty */ }
    };
    fetchUnseen();
    const interval = setInterval(fetchUnseen, 60000);
    return () => clearInterval(interval);
  }, [user]);

  // Mark seen when navigating to /orders
  useEffect(() => {
    if (location.pathname === '/orders' && unseenOrders > 0) {
      const mark = async () => {
        try {
          const { ordersAPI } = await import('../api');
          await ordersAPI.markSeen();
          setUnseenOrders(0);
        } catch { /* empty */ }
      };
      mark();
    }
  }, [location.pathname, unseenOrders]);

  // Fetch active modules — also listens for custom 'modules-changed' event
  const fetchActiveModules = useCallback(async () => {
    if (!user) return;
    try {
      const res = await modulesAPI.listActive();
      const keys = (res.data || []).map((m) => m.module_key);
      setActiveModuleKeys(keys);
    } catch {
      setActiveModuleKeys([]);
    }
  }, [user]);

  useEffect(() => { fetchActiveModules(); }, [fetchActiveModules]);

  // Listen for module changes from any page (ModulesPage dispatches this)
  useEffect(() => {
    const handler = () => fetchActiveModules();
    window.addEventListener('modules-changed', handler);
    return () => window.removeEventListener('modules-changed', handler);
  }, [fetchActiveModules]);

  // Build dynamic navigation based on active modules
  const activeSet = new Set(activeModuleKeys);
  const moduleNavItems = activeModuleKeys
    .filter((key) => moduleNavMap[key])
    .map((key) => moduleNavMap[key]);

  // Operations — only with commerce module active
  const dynamicOpsNav = [];
  if (activeSet.has('commerce')) {
    dynamicOpsNav.push(
      { nameKey: 'nav.orders', href: '/orders', icon: ShoppingCart, end: true },
      // CF3 — la tesoreria dell'operatore
      { nameKey: 'nav.cashflow', href: '/incassi', icon: Wallet, end: true },
      // CG0 — registro dati (vendite sync+manuale, spese, acquisti, costi fissi)
      { nameKey: 'nav.data', href: '/modules/cashflow/data/sales', icon: Database, end: false },
      // WS-2: Affitti solo se il piano abilita i noleggi (retreat: no)
      ...(canUse('commerce', 'rentals')
        ? [{ nameKey: 'nav.reservations', href: '/reservations', icon: BookMarked, end: true }]
        : []),
      { nameKey: 'nav.calendar', href: '/calendar', icon: CalendarDays, end: true },
      { nameKey: 'nav.stores', href: '/stores', icon: Globe, end: true },
      // PR1 — la vetrina dell'operatore raggiungibile dal menu
      { nameKey: 'nav.public_profile', href: '/public-profile', icon: UserCircle, end: true },
      // PR3 — plancia recensioni
      { nameKey: 'nav.reviews', href: '/reviews', icon: Star, end: true },
      // VT5 — lo specchietto della visibilita' su Aurya
      { nameKey: 'nav.visibility', href: '/visibilita', icon: Eye, end: true },
      { nameKey: 'nav.newsletter', href: '/newsletter', icon: Mail, end: true },
    );
  }

  // Entity nav: conditional on modules
  const hasCustomerIntel = activeSet.has('customers_light');
  const hasProductCatalog = activeSet.has('product_catalog');
  const hasCommerce = activeSet.has('commerce');

  const entityNav = [];

  // Products: only with commerce
  if (hasCommerce) {
    entityNav.push(hasProductCatalog ? {
      nameKey: 'nav.products', icon: Package,
      children: [
        { nameKey: 'nav.products', href: '/products', end: true },
        { nameKey: 'modules.product_catalog', href: '/modules/product-catalog', end: true },
      ],
    } : { nameKey: 'nav.products', href: '/products', icon: Package, end: true });
    // Onda 7 M1 — "Eventi" rimosso dalla sidebar: gli eventi si gestiscono
    // dentro /products?type=event_ticket (chip 🎫). Nessun link duplicato.

    // Bunny multi-library Step 6 — dedicated "Corsi" entry. Discoverable
    // top-level admin path that hosts the unified BunnyManagerCard
    // (multi-library config) + the courses list. Without this entry,
    // /courses was reachable only via deep-link or the TypePicker on
    // the products page — the cognitive overhead the unification
    // addresses.
    entityNav.push({
      nameKey: 'nav.courses', href: '/courses', icon: BookMarked, end: true,
    });
  }

  // Customers: only with customers_light module
  // The /modules/customers-light URL serves the NEW insights page
  // (Phase 2+). The legacy read-only page lives at
  // /modules/_legacy/customers-light for the 30-day safety-net
  // window but is intentionally absent from the menu.
  if (hasCustomerIntel) {
    entityNav.push({
      nameKey: 'nav.customers', icon: UserRound,
      children: [
        { nameKey: 'modules.customers_light', href: '/modules/customers-light', end: true },
        { nameKey: 'nav.customers', href: '/customers', end: true },
      ],
    });
  }

  // Suppliers: cashflow attivo E feature abilitata (WS-2: nel verticale
  // ritiri il cashflow core resta — gestionale — ma i fornitori no)
  if (activeSet.has('cashflow_monitor') && canUse('cashflow_monitor', 'suppliers')) {
    entityNav.push({ nameKey: 'nav.suppliers', href: '/suppliers', icon: Truck, end: true });
  }

  // System nav: filtro a grana fine (WS-2). Cashflow core può essere
  // acceso (gestionale) senza trascinarsi anomalie/AI/qualità dati.
  const dynamicSystemNav = systemNav.filter(item => {
    if (item.href === '/data-integrity') {
      return activeSet.has('cashflow_monitor') && canUse('cashflow_monitor', 'data_quality');
    }
    if (item.href === '/modules') {
      // piani retreat fissi: l'operatore non deve (ri)attivare moduli a mano
      return user?.role === 'system_admin';
    }
    return true;
  });

  const navigation = [...fixedNavTop, ...moduleNavItems, ...dynamicOpsNav];

  // Chiudi sidebar su cambio route (mobile)
  useEffect(() => {
    setOpen(false);
  }, [location.pathname, setOpen]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navLinkClass = ({ isActive }) =>
    `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-white/15 text-white border-l-2 border-white'
        : 'text-white/60 hover:bg-white/10 hover:text-white'
    }`;

  return (
    <>
      {/* Overlay mobile */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-50 h-screen w-64 border-r border-white/10 bg-gradient-sidebar text-white shadow-lg transition-transform duration-200 ease-in-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="flex h-full flex-col">
          {/* Logo + close button mobile */}
          <div className="flex h-16 items-center justify-between border-b border-white/10 px-6">
            <BrandLogo size="xs" variant="light" />
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 md:hidden text-white hover:bg-white/10"
              onClick={() => setOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-3 py-4">
            <nav className="space-y-1">
              {navigation.map((item) =>
                item.children ? (
                  <NavGroup key={item.name || item.nameKey} item={item} navLinkClass={navLinkClass} location={location} />
                ) : (
                  <NavLink
                    key={item.nameKey || item.name}
                    to={item.href}
                    end={item.end}
                    data-testid={`nav-${(item.nameKey || item.name).toLowerCase().replace(/[\s.]+/g, '-')}`}
                    className={navLinkClass}
                  >
                    <item.icon className="h-4 w-4" />
                    {resolveName(item)}
                    {item.href === '/orders' && unseenOrders > 0 && (
                      <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                        {unseenOrders > 9 ? '9+' : unseenOrders}
                      </span>
                    )}
                  </NavLink>
                )
              )}
            </nav>

            <Separator className="my-4 bg-white/10" />

            {/* Entity + Intelligence (merged) */}
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-white/40">
              {t('nav.master_data')}
            </p>
            <nav className="space-y-1 mb-4">
              {entityNav.map((item) =>
                item.children ? (
                  <NavGroup key={item.nameKey} item={item} navLinkClass={navLinkClass} location={location} />
                ) : (
                  <NavLink
                    key={item.nameKey}
                    to={item.href}
                    end={item.end}
                    data-testid={`nav-${item.nameKey.replace(/[\s.]+/g, '-')}`}
                    className={navLinkClass}
                  >
                    <item.icon className="h-4 w-4" />
                    {resolveName(item)}
                  </NavLink>
                )
              )}
            </nav>

            <Separator className="my-4 bg-white/10" />

            {/* System */}
            <nav className="space-y-1">
              {dynamicSystemNav.map((item) => (
                <NavLink
                  key={item.nameKey || item.name}
                  to={item.href}
                  end={item.end}
                  data-testid={`nav-${(item.nameKey || item.name).toLowerCase().replace(/[\s.]+/g, '-')}`}
                  className={navLinkClass}
                >
                  <item.icon className="h-4 w-4" />
                  {resolveName(item)}
                </NavLink>
              ))}
            </nav>

            {/* System Admin section — only visible to system_admin role */}
            {user?.role === 'system_admin' && (
              <>
                <Separator className="my-4 bg-white/10" />
                <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-white/40">
                  System
                </p>
                <nav className="space-y-1">
                  <NavLink
                    to="/admin"
                    data-testid="nav-admin"
                    className={navLinkClass}
                  >
                    <ShieldAlert className="h-4 w-4" />
                    Admin Panel
                  </NavLink>
                </nav>
              </>
            )}
          </ScrollArea>

          {/* User section */}
          <div className="border-t border-white/10 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20 text-sm font-medium text-white">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sm font-medium text-white">{user?.name}</p>
                <p className="truncate text-xs text-white/50">{user?.email}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                data-testid="logout-btn"
                className="h-8 w-8 text-white/60 hover:text-white hover:bg-white/10"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

// ─── Header ──────────────────────────────────────────────────────────────────

export const Header = ({ title, subtitle, children }) => {
  const { setOpen } = useSidebar();

  return (
    <header className="sticky top-0 z-30 border-b border-border/50 bg-white/70 backdrop-blur-xl">
      <div className="flex h-14 md:h-16 items-center justify-between gap-2 px-4 md:px-8">
        {/* Left cluster: flex-1 min-w-0 lets this side yield space gracefully
            when children (buttons, filters) on the right are wide. Without it,
            both sides fight for space and the title can overlap / break. */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Hamburger — solo mobile */}
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 md:hidden shrink-0"
            onClick={() => setOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          {/* Title column — min-w-0 is required on the direct parent of any
              element that uses truncate inside a flex container. */}
          <div className="min-w-0 flex-1">
            <h1 className="font-heading text-lg md:text-xl font-bold tracking-tight truncate">
              {title}
            </h1>
            {subtitle && (
              <p className="text-xs md:text-sm text-muted-foreground hidden sm:block truncate">
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {/* Right cluster: shrink-0 so action buttons never get squished —
            the title is what yields when space is tight. */}
        {children && (
          <div className="flex items-center gap-2 md:gap-3 shrink-0">{children}</div>
        )}
      </div>
    </header>
  );
};

// ─── AppLayout ───────────────────────────────────────────────────────────────
//
// INVARIANT (Onda 26):
// Every component that is the target of a <ProtectedRoute> in App.js MUST
// wrap its returned JSX in <AppLayout>. AppLayout mounts the <Sidebar />
// and applies md:pl-64, so the menu stays visible across navigations.
// Pages that return a bare <div className="min-h-screen ...> instead will
// render full-bleed without the sidebar — the user clicks a menu item and
// the menu vanishes. That bug is easy to introduce because:
//   • The routing layer doesn't enforce the wrap (it just renders the
//     component returned by the route).
//   • Internal navigation (`<Link to="/courses/new">`) re-renders the
//     page as the new route's component, not as a child of any layout.
//
// Canonical pattern (see DashboardPage / ProductsPage / SettingsPage):
//
//   import { AppLayout, Header } from '../../components/Layout';
//
//   export default function MyAdminPage() {
//     // ...hooks...
//     return (
//       <AppLayout>
//         <Header title="..." subtitle="..." />
//         {/* page content */}
//       </AppLayout>
//     );
//   }
//
// <Header /> is OPTIONAL — pages that already render their own inline
// header are free to skip it. AppLayout is NOT optional for protected
// admin routes.
//
// Public pages (storefront, landing, login, signup, customer-portal
// /account/*) live under different layouts and intentionally do NOT use
// AppLayout. They use their own dedicated shells.
//
export const AppLayout = ({ children }) => {
  const [open, setOpen] = useState(false);

  return (
    <SidebarContext.Provider value={{ open, setOpen }}>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="md:pl-64">
          {children}
        </main>
      </div>
    </SidebarContext.Provider>
  );
};

export default AppLayout;
