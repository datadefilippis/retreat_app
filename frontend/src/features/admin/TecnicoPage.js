/**
 * TecnicoPage — /admin/tecnico (SA-R, 10/9/2026 sera).
 *
 * Gli aspetti tecnici, fuori dalle pagine di lavoro quotidiano: i
 * segnali (da dati a proposte), gli abbonamenti (MRR e stato dei
 * canoni), il catalogo dei piani, gli inviti e il registro delle
 * azioni (audit log).
 */
import React from 'react';
import { Sparkles, TrendingUp, Package, MailPlus, ScrollText } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import SignalsTab from './SignalsTab';
import MRRDashboardTab from './MRRDashboardTab';
import CatalogTab from './CatalogTab';
import InvitesTab from './InvitesTab';
import AuditLogTab from './AuditLogTab';

const TABS = [
  { value: 'segnali', label: 'Segnali', icon: Sparkles, element: <SignalsTab /> },
  { value: 'abbonamenti', label: 'Abbonamenti', icon: TrendingUp, element: <MRRDashboardTab /> },
  { value: 'catalogo', label: 'Catalogo piani', icon: Package, element: <CatalogTab /> },
  { value: 'inviti', label: 'Inviti', icon: MailPlus, element: <InvitesTab /> },
  { value: 'audit', label: 'Audit log', icon: ScrollText, element: <AuditLogTab /> },
];

export default function TecnicoPage() {
  return (
    <AdminPageShell title="Tecnico" subtitle="Segnali, abbonamenti, catalogo, inviti, registro"
                    tabs={TABS} testid="admin-tecnico" />
  );
}
