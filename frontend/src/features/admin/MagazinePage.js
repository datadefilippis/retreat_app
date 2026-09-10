/**
 * MagazinePage — /admin/magazine (SA-R, 10/9/2026 sera).
 *
 * Il Magazine si scrive da qui: articoli, bozze, anteprima. Era un tab
 * dell'Admin Panel; e' contenuto, non tecnica, quindi ha la sua voce.
 */
import React from 'react';
import { Newspaper } from 'lucide-react';
import AdminPageShell from './AdminPageShell';
import BlogAdminTab from './BlogAdminTab';

const TABS = [
  { value: 'articoli', label: 'Articoli', icon: Newspaper, element: <BlogAdminTab /> },
];

export default function MagazinePage() {
  return (
    <AdminPageShell title="Magazine" subtitle="Gli articoli di Aurya" tabs={TABS} testid="admin-magazine" />
  );
}
