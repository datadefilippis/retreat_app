import React, { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '../../api';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Skeleton } from '../../components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import { Users, RefreshCw, Copy, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../../lib/utils';

// ── Helpers ───────────────────────────────────────────────────────────────────

const roleColors = {
  system_admin: 'bg-red-100 text-red-800',
  admin:        'bg-purple-100 text-purple-800',
  user:         'bg-blue-100 text-blue-700',
};

const RoleBadge = ({ role }) => (
  <Badge className={roleColors[role] || 'bg-gray-100 text-gray-700'}>{role}</Badge>
);

const StatusBadge = ({ isActive }) =>
  isActive ? (
    <Badge className="bg-green-100 text-green-800">Active</Badge>
  ) : (
    <Badge className="bg-red-100 text-red-800">Inactive</Badge>
  );

// ── Component ─────────────────────────────────────────────────────────────────

const UsersTab = () => {
  const [users, setUsers]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [total, setTotal]       = useState(0);

  // Filters (applied on explicit fetch or filter change)
  const [filterRole, setFilterRole]     = useState('');
  const [filterActive, setFilterActive] = useState('');

  // Reset-password dialog
  const [resetOpen, setResetOpen]       = useState(false);
  const [resetTarget, setResetTarget]   = useState(null);
  const [resetResult, setResetResult]   = useState(null);
  const [resetting, setResetting]       = useState(false);

  // Per-row action loading  { "<userId>_status": bool }
  const [actionLoading, setActionLoading] = useState({});
  const setAction = (key, val) =>
    setActionLoading((prev) => ({ ...prev, [key]: val }));

  // ── Data fetch ──────────────────────────────────────────────────────────────

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    const params = { limit: 100 };
    if (filterRole)   params.role      = filterRole;
    if (filterActive) params.is_active = filterActive === 'true';
    try {
      const res = await adminAPI.listUsers(params);
      setUsers(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [filterRole, filterActive]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // ── Activate / Deactivate ───────────────────────────────────────────────────

  const handleToggleStatus = async (u) => {
    const newStatus = !u.is_active;
    const verb = newStatus ? 'activate' : 'deactivate';
    if (!window.confirm(`Are you sure you want to ${verb} "${u.name}" (${u.email})?`)) return;

    const key = `${u.id}_status`;
    setAction(key, true);
    try {
      await adminAPI.setUserStatus(u.id, newStatus);
      toast.success(`User ${newStatus ? 'activated' : 'deactivated'}`);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update user status');
    } finally {
      setAction(key, false);
    }
  };

  // ── Reset Password ──────────────────────────────────────────────────────────

  const openResetDialog = (u) => {
    setResetTarget(u);
    setResetResult(null);
    setResetOpen(true);
  };

  const handleResetPassword = async () => {
    setResetting(true);
    try {
      const res = await adminAPI.resetUserPassword(resetTarget.id);
      setResetResult(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password');
    } finally {
      setResetting(false);
    }
  };

  const handleCopyPassword = () => {
    navigator.clipboard.writeText(resetResult.temporary_password);
    toast.success('Password copied to clipboard');
  };

  const handleCloseReset = () => {
    setResetOpen(false);
    setResetResult(null);
    setResetTarget(null);
  };

  // ── Hard Delete User ────────────────────────────────────────────────────────

  const handleDeleteUser = async (u) => {
    if (!window.confirm(
      `ELIMINAZIONE PERMANENTE\n\nSei sicuro di voler eliminare definitivamente l'utente "${u.name}" (${u.email})?\n\nQuesta azione è irreversibile.`
    )) return;

    const key = `${u.id}_delete`;
    setAction(key, true);
    try {
      await adminAPI.hardDeleteUser(u.id);
      toast.success(`Utente "${u.email}" eliminato definitivamente`);
      fetchUsers();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to delete user';
      toast.error(detail);
    } finally {
      setAction(key, false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      <Card className="border border-border">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Users className="h-5 w-5" />
                Users
              </CardTitle>
              <CardDescription>
                {total} user{total !== 1 ? 's' : ''} on the platform
              </CardDescription>
            </div>

            {/* Filters + Refresh */}
            <div className="flex items-center gap-2 flex-wrap">
              <Select
                value={filterRole || 'all'}
                onValueChange={(v) => setFilterRole(v === 'all' ? '' : v)}
              >
                <SelectTrigger className="w-38 h-8">
                  <SelectValue placeholder="All roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All roles</SelectItem>
                  <SelectItem value="system_admin">System Admin</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="user">User</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filterActive || 'all'}
                onValueChange={(v) => setFilterActive(v === 'all' ? '' : v)}
              >
                <SelectTrigger className="w-32 h-8">
                  <SelectValue placeholder="All status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All status</SelectItem>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="sm" onClick={fetchUsers} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
            </div>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              {filterRole || filterActive
                ? 'No users match the selected filters.'
                : 'No users found.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Org ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell>
                        <div className="font-medium">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </TableCell>
                      <TableCell><RoleBadge role={u.role} /></TableCell>
                      <TableCell className="text-xs font-mono text-muted-foreground">
                        {u.organization_id
                          ? `${u.organization_id.slice(0, 8)}…`
                          : '—'}
                      </TableCell>
                      <TableCell><StatusBadge isActive={u.is_active} /></TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {u.last_login_at ? formatDate(u.last_login_at) : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        {/* system_admin accounts cannot be modified from here */}
                        {u.role !== 'system_admin' && (
                          <div className="flex justify-end gap-1">
                            <Button
                              variant={u.is_active ? 'outline' : 'default'}
                              size="sm"
                              onClick={() => handleToggleStatus(u)}
                              disabled={actionLoading[`${u.id}_status`]}
                            >
                              {u.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openResetDialog(u)}
                            >
                              Reset Pwd
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleDeleteUser(u)}
                              disabled={actionLoading[`${u.id}_delete`]}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Reset Password Dialog ─────────────────────────────────────────── */}
      <Dialog open={resetOpen} onOpenChange={(open) => { if (!open) handleCloseReset(); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
          </DialogHeader>

          {!resetResult ? (
            /* Step 1 — confirmation */
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Generate a one-time temporary password for{' '}
                <strong>{resetTarget?.name}</strong> ({resetTarget?.email}).
              </p>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                ⚠️ The password will be shown once. Transmit it via a secure out-of-band channel.
              </p>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={handleCloseReset}>
                  Cancel
                </Button>
                <Button onClick={handleResetPassword} disabled={resetting}>
                  {resetting ? 'Generating…' : 'Generate Password'}
                </Button>
              </div>
            </div>
          ) : (
            /* Step 2 — show result */
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Temporary Password</Label>
                <div className="flex gap-2">
                  <Input
                    value={resetResult.temporary_password}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button variant="outline" size="icon" onClick={handleCopyPassword}>
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                ⚠️ {resetResult.warning}
              </p>
              <Button className="w-full" onClick={handleCloseReset}>
                Done
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UsersTab;
