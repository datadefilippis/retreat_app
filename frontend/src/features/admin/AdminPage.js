/**
 * AdminPage — /admin, la DASHBOARD del system admin (SA-R, 10/9/2026 sera).
 *
 * Il founder: «l'Admin Panel ha troppa roba: pulirla, togliere cio' che
 * non serve, spostare le cose in pagine separate dal menu». Da 15 tab a
 * un menu di sette voci: Dashboard (qui: i numeri del lunedi', i soldi,
 * gli ordini per operatore, i clienti), Iscritti al Cerchio, Operatori,
 * Magazine, Aurya Sound, le ricettive, Tecnico. La tab «AI & Traduzioni» e'
 * stata tolta (founder). I vecchi link `/admin?tab=…` (email, segnalibri)
 * arrivano qui e vengono RINVIATI alla pagina nuova: nessun flusso
 * spaccato.
 */
import React from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { TrendingUp, ShoppingCart, UserRound } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import PlatformOverviewTab from './PlatformOverviewTab';
import OrdiniTab from './OrdiniTab';
import PlatformUsersTab from './PlatformUsersTab';

// i tab di ieri → la pagina di oggi
const RINVII = {
  directory: '/admin/operatori?tab=directory',
  signals: '/admin/tecnico?tab=segnali',
  organizations: '/admin/operatori?tab=organizzazioni',
  users: '/admin/operatori?tab=account',
  'platform-users': '/admin?tab=clienti',
  catalog: '/admin/tecnico?tab=catalogo',
  'audit-log': '/admin/tecnico?tab=audit',
  invites: '/admin/tecnico?tab=inviti',
  billing: '/admin/tecnico?tab=abbonamenti',
  'ai-governance': '/admin/tecnico',
  blog: '/admin/magazine',
  leads: '/admin/cerchio?tab=contatti',
  interviews: '/admin/operatori?tab=interviste',
  reviews: '/admin/operatori?tab=segnalazioni',
};

const TABS = [
  { value: 'overview', label: 'Panoramica', icon: TrendingUp, element: <PlatformOverviewTab /> },
  { value: 'ordini', label: 'Ordini', icon: ShoppingCart, element: <OrdiniTab /> },
  { value: 'clienti', label: 'Clienti', icon: UserRound, element: <PlatformUsersTab /> },
];

export default function AdminPage() {
  const [params] = useSearchParams();
  const vecchio = params.get('tab');
  if (vecchio && RINVII[vecchio]) return <Navigate to={RINVII[vecchio]} replace />;
  return (
    <AdminPageShell title="Dashboard" subtitle="Come sta andando Aurya: la fila, i ritiri, i soldi, gli ordini"
                    tabs={TABS} testid="admin-dashboard" />
  );
}
