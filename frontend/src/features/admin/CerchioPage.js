/**
 * CerchioPage — /admin/cerchio (SA-R, 10/9/2026 sera).
 *
 * «Iscritti al Cerchio»: il controllo completo della newsletter in una
 * pagina propria del menu System. Due tab: gli iscritti (stato, porta,
 * preferenze sui ritiri, zona, email ricevute, disiscrizione) e i
 * contatti raccolti dalle landing di luglio (LeadsTab), che restano
 * contatti veri ma non sono iscritti al Cerchio.
 */
import React from 'react';
import { Users, Inbox, Mail } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import IscrittiTab from './IscrittiTab';
import LeadsTab from './LeadsTab';
import SequenzeTab from './SequenzeTab';

const TABS = [
  { value: 'iscritti', label: 'Iscritti', icon: Users, element: <IscrittiTab /> },
  { value: 'contatti', label: 'Contatti dalle landing', icon: Inbox, element: <LeadsTab /> },
  { value: 'email', label: 'Email automatiche', icon: Mail, element: <SequenzeTab /> },
];

export default function CerchioPage() {
  return (
    <AdminPageShell title="Iscritti al Cerchio" subtitle="Chi è dentro, da dove è entrato, cosa cerca"
                    tabs={TABS} testid="admin-cerchio" />
  );
}
