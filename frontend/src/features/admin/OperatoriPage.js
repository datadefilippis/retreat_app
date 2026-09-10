/**
 * OperatoriPage — /admin/operatori (SA-R, 10/9/2026 sera).
 *
 * Le organizzazioni iscritte e tutto quello che serve per seguirle:
 * la lista con badge, rete, piano e azioni (OrganizationsTab), la
 * plancia della directory pubblica, le interviste (Verificato Aurya),
 * la coda delle recensioni segnalate e gli account degli operatori.
 */
import React from 'react';
import { Building2, Globe2, Mic, ShieldAlert, Users } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import OrganizationsTab from './OrganizationsTab';
import DirectoryAdminTab from './DirectoryAdminTab';
import InterviewsTab from './InterviewsTab';
import FlaggedReviewsTab from './FlaggedReviewsTab';
import UsersTab from './UsersTab';

const TABS = [
  { value: 'organizzazioni', label: 'Organizzazioni', icon: Building2, element: <OrganizationsTab /> },
  { value: 'directory', label: 'Directory', icon: Globe2, element: <DirectoryAdminTab /> },
  { value: 'interviste', label: 'Interviste', icon: Mic, element: <InterviewsTab /> },
  { value: 'segnalazioni', label: 'Segnalazioni', icon: ShieldAlert, element: <FlaggedReviewsTab /> },
  { value: 'account', label: 'Account operatori', icon: Users, element: <UsersTab /> },
];

export default function OperatoriPage() {
  return (
    <AdminPageShell title="Operatori" subtitle="Le organizzazioni iscritte, la directory, le interviste"
                    tabs={TABS} testid="admin-operatori" />
  );
}
