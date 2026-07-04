import React, { useState, useEffect } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Card, CardContent } from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import { Building2, Users, ScrollText, AlertTriangle, Package, MailPlus, TrendingUp, Zap } from 'lucide-react';
import { adminAPI } from '../../api';
import OrganizationsTab from './OrganizationsTab';
import UsersTab from './UsersTab';
import AuditLogTab from './AuditLogTab';
import CatalogTab from './CatalogTab';
import InvitesTab from './InvitesTab';
import MRRDashboardTab from './MRRDashboardTab';
import AIGovernanceTab from './AIGovernanceTab';

/**
 * AdminPage — System Admin Control Panel.
 *
 * Accessible only via SystemAdminRoute (role === "system_admin").
 * Three tabs: Organizations | Users | Audit Log.
 * All data is fetched from /api/admin/* endpoints which independently
 * enforce require_system_admin — even if this route were somehow bypassed,
 * every API call would return 403.
 */

// ── Stats row (platform KPIs at a glance) ─────────────────────────────────────

const StatCard = ({ label, value, highlight }) => (
  <Card className={`border ${highlight ? 'border-red-200' : 'border-border'}`}>
    <CardContent className="pt-4 pb-4">
      <div className={`text-2xl font-bold font-heading ${highlight ? 'text-red-600' : ''}`}>
        {value ?? <Skeleton className="h-7 w-10 inline-block" />}
      </div>
      <p className="text-sm text-muted-foreground mt-0.5">{label}</p>
    </CardContent>
  </Card>
);

const AdminStats = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadStats() {
      try {
        const [orgsRes, usersRes] = await Promise.all([
          adminAPI.listOrganizations(0, 200),
          adminAPI.listUsers({ limit: 1 }),
        ]);
        if (cancelled) return;
        const orgs = orgsRes.data.items ?? [];
        setStats({
          totalOrgs:    orgsRes.data.total,
          suspendedOrgs: orgs.filter((o) => !o.is_active).length,
          totalUsers:   usersRes.data.total,
        });
      } catch {
        // Stats are non-critical — fail silently
      }
    }
    loadStats();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="grid grid-cols-3 gap-3 mb-6">
      <StatCard label="Organizations"  value={stats?.totalOrgs} />
      <StatCard
        label="Suspended"
        value={stats?.suspendedOrgs}
        highlight={stats != null && stats.suspendedOrgs > 0}
      />
      <StatCard label="Total Users"    value={stats?.totalUsers} />
    </div>
  );
};

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
        <AdminStats />

        {/* Tabs list — becomes horizontally scrollable on phones so all 5
            tabs stay reachable without wrapping into a jagged multi-row
            block. scrollbar-hide is defined in index.css. */}
        <Tabs defaultValue="organizations">
          <TabsList className="mb-6 w-full sm:w-auto overflow-x-auto scrollbar-hide justify-start">
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
              AI Governance
            </TabsTrigger>
          </TabsList>

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
        </Tabs>
      </div>
    </AppLayout>
  );
};

export default AdminPage;
