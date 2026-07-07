import React from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Building2, Users, ScrollText, AlertTriangle, Package, MailPlus, TrendingUp, Zap, Globe2, Sparkles, Newspaper } from 'lucide-react';
import PlatformOverviewTab from './PlatformOverviewTab';
import DirectoryAdminTab from './DirectoryAdminTab';
import SignalsTab from './SignalsTab';
import OrganizationsTab from './OrganizationsTab';
import UsersTab from './UsersTab';
import AuditLogTab from './AuditLogTab';
import CatalogTab from './CatalogTab';
import InvitesTab from './InvitesTab';
import MRRDashboardTab from './MRRDashboardTab';
import AIGovernanceTab from './AIGovernanceTab';
import BlogAdminTab from './BlogAdminTab';

/**
 * AdminPage — System Admin Control Panel.
 *
 * Accessible only via SystemAdminRoute (role === "system_admin").
 * Three tabs: Organizations | Users | Audit Log.
 * All data is fetched from /api/admin/* endpoints which independently
 * enforce require_system_admin — even if this route were somehow bypassed,
 * every API call would return 403.
 */

// ── Page ──────────────────────────────────────────────────────────────────────

const AdminPage = () => {
  return (
    <AppLayout>
      <Header
        title="System Admin"
        subtitle="Platform control panel — system administrator only"
      >
        <div className="flex items-center gap-1.5 rounded-md bg-red-50 border border-red-200 px-2.5 py-1 text-xs font-medium text-red-700 shrink-0">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span className="hidden sm:inline">Restricted area</span>
        </div>
      </Header>

      <div className="p-4 md:p-8 animate-fade-in">
        {/* SA2 — la vecchia stat row (org/utenti) vive dentro Panoramica:
            un solo posto per i KPI, niente doppioni sopra i tab. */}
        {/* Tabs list — becomes horizontally scrollable on phones so all
            tabs stay reachable without wrapping into a jagged multi-row
            block. scrollbar-hide is defined in index.css. */}
        <Tabs defaultValue="overview">
          <TabsList className="mb-6 w-full sm:w-auto overflow-x-auto scrollbar-hide justify-start">
            <TabsTrigger value="overview" className="flex items-center gap-2 shrink-0">
              <TrendingUp className="h-4 w-4" />
              Panoramica
            </TabsTrigger>
            <TabsTrigger value="directory" className="flex items-center gap-2 shrink-0">
              <Globe2 className="h-4 w-4" />
              Directory
            </TabsTrigger>
            <TabsTrigger value="signals" className="flex items-center gap-2 shrink-0">
              <Sparkles className="h-4 w-4" />
              Segnali
            </TabsTrigger>
            <TabsTrigger value="organizations" className="flex items-center gap-2 shrink-0">
              <Building2 className="h-4 w-4" />
              Organizations
            </TabsTrigger>
            <TabsTrigger value="users" className="flex items-center gap-2 shrink-0">
              <Users className="h-4 w-4" />
              Users
            </TabsTrigger>
            <TabsTrigger value="catalog" className="flex items-center gap-2 shrink-0">
              <Package className="h-4 w-4" />
              Catalog
            </TabsTrigger>
            <TabsTrigger value="audit-log" className="flex items-center gap-2 shrink-0">
              <ScrollText className="h-4 w-4" />
              Audit Log
            </TabsTrigger>
            <TabsTrigger value="invites" className="flex items-center gap-2 shrink-0">
              <MailPlus className="h-4 w-4" />
              Invites
            </TabsTrigger>
            <TabsTrigger value="billing" className="flex items-center gap-2 shrink-0">
              <TrendingUp className="h-4 w-4" />
              Billing
            </TabsTrigger>
            <TabsTrigger value="ai-governance" className="flex items-center gap-2 shrink-0">
              <Zap className="h-4 w-4" />
              AI & Traduzioni
            </TabsTrigger>
            <TabsTrigger value="blog" className="flex items-center gap-2 shrink-0">
              <Newspaper className="h-4 w-4" />
              Blog
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <PlatformOverviewTab />
          </TabsContent>

          <TabsContent value="directory">
            <DirectoryAdminTab />
          </TabsContent>

          <TabsContent value="signals">
            <SignalsTab />
          </TabsContent>

          <TabsContent value="organizations">
            <OrganizationsTab />
          </TabsContent>

          <TabsContent value="users">
            <UsersTab />
          </TabsContent>

          <TabsContent value="catalog">
            <CatalogTab />
          </TabsContent>

          <TabsContent value="audit-log">
            <AuditLogTab />
          </TabsContent>

          <TabsContent value="invites">
            <InvitesTab />
          </TabsContent>

          <TabsContent value="billing">
            <MRRDashboardTab />
          </TabsContent>

          <TabsContent value="ai-governance">
            <AIGovernanceTab />
          </TabsContent>

          <TabsContent value="blog">
            <BlogAdminTab />
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
};

export default AdminPage;
