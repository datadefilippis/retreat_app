/**
 * OperatoriPage — /admin/operatori (SA-R, 10/9/2026 sera).
 *
 * Le organizzazioni iscritte e tutto quello che serve per seguirle:
 * la lista con badge, rete, piano e azioni (OrganizationsTab), la
 * plancia della directory pubblica, le interviste (Verificato Aurya),
 * la coda delle recensioni segnalate e gli account degli operatori.
 */
import React from 'react';
import { Building2, Globe2, Mic, ShieldAlert, Users, Sparkles } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import OrganizationsTab from './OrganizationsTab';
import DirectoryAdminTab from './DirectoryAdminTab';
import InterviewsTab from './InterviewsTab';
import FlaggedReviewsTab from './FlaggedReviewsTab';
import UsersTab from './UsersTab';
import LeadsTab from './LeadsTab';
import DisciplineTab from './DisciplineTab';

/* Lotto D (24/9/2026) — i lead professionisti delle landing stanno
   QUI, sotto gli account (stessa componente del Cerchio, filtrata):
   sono candidature alla rete, non iscritti alla Lettera. */
function AccountETab() {
  return (
    <div className="space-y-10">
      <UsersTab />
      <section data-testid="admin-lead-professionisti">
        <h2 className="mb-4 font-heading text-lg font-semibold">Contatti dalle landing (professionisti)</h2>
        <LeadsTab tipo="operator" />
      </section>
    </div>
  );
}

const TABS = [
  { value: 'organizzazioni', label: 'Organizzazioni', icon: Building2, element: <OrganizationsTab /> },
  { value: 'directory', label: 'Directory', icon: Globe2, element: <DirectoryAdminTab /> },
  { value: 'interviste', label: 'Interviste', icon: Mic, element: <InterviewsTab /> },
  { value: 'segnalazioni', label: 'Segnalazioni', icon: ShieldAlert, element: <FlaggedReviewsTab /> },
  { value: 'account', label: 'Account operatori', icon: Users, element: <AccountETab /> },
  // DV2 (2/10/2026): le discipline dalla regia, senza deploy
  { value: 'discipline', label: 'Discipline', icon: Sparkles, element: <DisciplineTab /> },
];

export default function OperatoriPage() {
  return (
    <AdminPageShell title="Operatori" subtitle="Le organizzazioni iscritte, la directory, le interviste"
                    tabs={TABS} testid="admin-operatori" />
  );
}
