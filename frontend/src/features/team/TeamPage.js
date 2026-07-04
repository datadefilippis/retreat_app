import React, { useState, useEffect } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Separator } from '../../components/ui/separator';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { organizationsAPI } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { formatDate } from '../../lib/utils';
import {
  Users,
  UserPlus,
  Shield,
  User,
  Trash2,
  Crown,
  RefreshCw,
  Copy,
  CheckCheck,
  AlertTriangle,
  UserCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

// ── TeamPage ──────────────────────────────────────────────────────────────────

export const TeamPage = () => {
  const { t } = useTranslation('team');
  const { user } = useAuth();
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);

  // Invite dialog
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteData, setInviteData] = useState({ email: '', name: '', role: 'user' });
  const [inviting, setInviting] = useState(false);

  // Temp password dialog (shown after successful invite)
  const [tempPwData, setTempPwData] = useState(null); // { name, email, tempPassword }
  const [copiedPw, setCopiedPw] = useState(false);

  // Remove confirmation dialog
  const [removeConfirmId, setRemoveConfirmId] = useState(null); // user_id to confirm

  // Per-row action loading (role change / remove / reactivate)
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const isAdmin = user?.role === 'admin';

  const fetchTeam = async () => {
    setLoading(true);
    try {
      const response = await organizationsAPI.getTeam();
      setTeam(response.data);
    } catch (error) {
      toast.error(t('toast.load_error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTeam(); }, []);

  // ── Invite ────────────────────────────────────────────────────────────────
  const handleInvite = async (e) => {
    e.preventDefault();
    setInviting(true);
    try {
      const response = await organizationsAPI.inviteUser(inviteData);
      setInviteOpen(false);
      setInviteData({ email: '', name: '', role: 'user' });
      // Show temp password in a dedicated dialog
      setTempPwData({
        name:         response.data.name,
        email:        response.data.email,
        tempPassword: response.data.temp_password,
      });
      fetchTeam();
    } catch (error) {
      // Onda 17 — when the backend returns 429 (team_members quota
      // exceeded) or 403 (module/feature not available), the global
      // paywall modal opens via the axios interceptor. Close THIS
      // dialog so the user does not end up with two stacked modals.
      // Skip the toast for the same reason (the paywall already
      // explains the situation in detail — a redundant red toast on
      // top would create the "double notification" UX bug).
      if (error.__handled_by_paywall) {
        setInviteOpen(false);
      } else {
        const detail = error.response?.data?.detail;
        const msg = typeof detail === 'object' ? detail.message : detail;
        toast.error(msg || t('toast.invite_error'));
      }
    } finally {
      setInviting(false);
    }
  };

  const handleCopyTempPw = () => {
    navigator.clipboard.writeText(tempPwData.tempPassword).then(() => {
      setCopiedPw(true);
      setTimeout(() => setCopiedPw(false), 2000);
    });
  };

  // ── Role change ───────────────────────────────────────────────────────────
  const handleUpdateRole = async (userId, newRole) => {
    setActionLoadingId(userId);
    try {
      await organizationsAPI.updateUserRole(userId, newRole);
      toast.success(t('toast.role_updated'));
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('toast.role_error'));
    } finally {
      setActionLoadingId(null);
    }
  };

  // ── Remove ────────────────────────────────────────────────────────────────
  const handleRemoveConfirmed = async () => {
    const userId = removeConfirmId;
    setActionLoadingId(userId);
    setRemoveConfirmId(null);
    try {
      await organizationsAPI.removeUser(userId);
      toast.success(t('toast.member_removed'));
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('toast.remove_error'));
    } finally {
      setActionLoadingId(null);
    }
  };

  // ── Reactivate ────────────────────────────────────────────────────────────
  const handleReactivate = async (userId) => {
    setActionLoadingId(userId);
    try {
      await organizationsAPI.reactivateUser(userId);
      toast.success(t('toast.member_reactivated'));
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('toast.reactivate_error'));
    } finally {
      setActionLoadingId(null);
    }
  };

  // ── Helpers ───────────────────────────────────────────────────────────────
  const memberToRemove = removeConfirmId ? team.find((m) => m.id === removeConfirmId) : null;

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />
      {isAdmin && (
        <PageSubheader
          actions={
            <Button
              size="sm"
              onClick={() => setInviteOpen(true)}
              data-testid="invite-member-btn"
              className="gap-1.5"
            >
              <UserPlus className="h-4 w-4" />
              {t('invite.button')}
            </Button>
          }
        />
      )}

      {/* Invite Dialog — lifted out of Header so it is not nested inside
          a component that we removed from this subtree. The open state is
          controlled by inviteOpen + setInviteOpen exactly as before. */}
      {isAdmin && (
        <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('invite.dialog_title')}</DialogTitle>
              <DialogDescription>{t('invite.dialog_desc')}</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleInvite} className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <Label htmlFor="invite-name">{t('invite.name')}</Label>
                <Input
                  id="invite-name"
                  placeholder={t('invite.name_placeholder')}
                  value={inviteData.name}
                  onChange={(e) => setInviteData({ ...inviteData, name: e.target.value })}
                  required
                  data-testid="invite-name-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invite-email">{t('invite.email')}</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder={t('invite.email_placeholder')}
                  value={inviteData.email}
                  onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                  required
                  data-testid="invite-email-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invite-role">{t('invite.role')}</Label>
                <Select
                  value={inviteData.role}
                  onValueChange={(v) => setInviteData({ ...inviteData, role: v })}
                >
                  <SelectTrigger data-testid="invite-role-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">{t('roles.user_analyst')}</SelectItem>
                    <SelectItem value="admin">{t('roles.admin')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={inviting}
                  data-testid="send-invite-btn"
                >
                  {inviting ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      {t('invite.submitting')}
                    </>
                  ) : t('invite.submit')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      <div className="p-4 md:p-8 space-y-6 animate-fade-in">

        {/* ── Team members table ── */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Users className="h-5 w-5" />
              {t('members.card_title')}
            </CardTitle>
            <CardDescription>
              {t('members.count', { count: team.length })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('members.col_member')}</TableHead>
                      <TableHead>{t('members.col_role')}</TableHead>
                      <TableHead>{t('members.col_added')}</TableHead>
                      <TableHead>{t('members.col_status')}</TableHead>
                      {isAdmin && <TableHead className="text-right">{t('members.col_actions')}</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody data-testid="team-table">
                    {team.map((member) => {
                      const isCurrentUser = member.id === user?.id;
                      const isActionsLoading = actionLoadingId === member.id;

                      return (
                        <TableRow key={member.id} className={!member.is_active ? 'opacity-60' : ''}>
                          {/* Member info */}
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground shrink-0">
                                {member.name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div className="font-medium flex items-center gap-2">
                                  {member.name}
                                  {isCurrentUser && (
                                    <Badge variant="outline" className="text-xs">{t('members.you_badge')}</Badge>
                                  )}
                                </div>
                                <div className="text-sm text-muted-foreground">{member.email}</div>
                              </div>
                            </div>
                          </TableCell>

                          {/* Role badge */}
                          <TableCell>
                            {member.role === 'admin' ? (
                              <Badge className="bg-purple-100 text-purple-800 border-0">
                                <Crown className="h-3 w-3 mr-1" />
                                {t('roles.admin')}
                              </Badge>
                            ) : (
                              <Badge variant="outline">
                                <User className="h-3 w-3 mr-1" />
                                {t('roles.user')}
                              </Badge>
                            )}
                          </TableCell>

                          {/* Date */}
                          <TableCell>{formatDate(member.created_at)}</TableCell>

                          {/* Status */}
                          <TableCell>
                            {member.is_active ? (
                              <Badge className="bg-green-100 text-green-800 border-0">{t('status.active')}</Badge>
                            ) : (
                              <Badge variant="outline" className="text-muted-foreground">
                                {t('status.inactive')}
                              </Badge>
                            )}
                          </TableCell>

                          {/* Actions — admin only, not on own row */}
                          {isAdmin && (
                            <TableCell className="text-right">
                              {!isCurrentUser && (
                                <div className="flex justify-end items-center gap-2">
                                  {member.is_active ? (
                                    <>
                                      {/* Role selector */}
                                      <Select
                                        value={member.role}
                                        onValueChange={(role) => handleUpdateRole(member.id, role)}
                                        disabled={isActionsLoading}
                                      >
                                        <SelectTrigger className="w-28 h-8" data-testid={`role-select-${member.id}`}>
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="user">{t('roles.user')}</SelectItem>
                                          <SelectItem value="admin">{t('roles.admin')}</SelectItem>
                                        </SelectContent>
                                      </Select>

                                      {/* Remove button */}
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={() => setRemoveConfirmId(member.id)}
                                        disabled={isActionsLoading}
                                        data-testid={`remove-${member.id}`}
                                      >
                                        {isActionsLoading
                                          ? <RefreshCw className="h-4 w-4 animate-spin" />
                                          : <Trash2 className="h-4 w-4 text-red-600" />
                                        }
                                      </Button>
                                    </>
                                  ) : (
                                    /* Reactivate button for inactive members */
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      className="h-8 gap-1.5"
                                      onClick={() => handleReactivate(member.id)}
                                      disabled={isActionsLoading}
                                      data-testid={`reactivate-${member.id}`}
                                    >
                                      {isActionsLoading
                                        ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                        : <UserCheck className="h-3.5 w-3.5" />
                                      }
                                      {t('actions.reactivate')}
                                    </Button>
                                  )}
                                </div>
                              )}
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Role permissions info ── */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" />
              {t('permissions.card_title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Crown className="h-4 w-4 text-purple-600" />
                  <span className="font-medium">{t('permissions.admin_title')}</span>
                </div>
                <ul className="text-sm text-muted-foreground space-y-1.5 ml-6">
                  <li>{'\u2022'} {t('permissions.admin_p1')}</li>
                  <li>{'\u2022'} {t('permissions.admin_p2')}</li>
                  <li>{'\u2022'} {t('permissions.admin_p3')}</li>
                  <li>{'\u2022'} {t('permissions.admin_p4')}</li>
                  <li>{'\u2022'} {t('permissions.admin_p5')}</li>
                </ul>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <User className="h-4 w-4 text-blue-600" />
                  <span className="font-medium">{t('permissions.user_title')}</span>
                </div>
                <ul className="text-sm text-muted-foreground space-y-1.5 ml-6">
                  <li>{'\u2022'} {t('permissions.user_p1')}</li>
                  <li>{'\u2022'} {t('permissions.user_p2')}</li>
                  <li>{'\u2022'} {t('permissions.user_p3')}</li>
                  <li>{'\u2022'} {t('permissions.user_p4')}</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Confirmation dialog: remove member ── */}
      <Dialog open={!!removeConfirmId} onOpenChange={(open) => !open && setRemoveConfirmId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              {t('remove.dialog_title')}
            </DialogTitle>
            <DialogDescription>
              {memberToRemove && t('remove.dialog_desc', { name: memberToRemove.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 pt-2">
            <Button variant="outline" onClick={() => setRemoveConfirmId(null)}>
              {t('remove.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemoveConfirmed}
              data-testid="confirm-remove-btn"
            >
              {t('remove.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Temp password dialog — shown after successful invite ── */}
      <Dialog open={!!tempPwData} onOpenChange={(open) => !open && setTempPwData(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {t('created.dialog_title')}
            </DialogTitle>
            <DialogDescription>
              {tempPwData && t('created.dialog_desc', { name: tempPwData.name })}
            </DialogDescription>
          </DialogHeader>

          {tempPwData && (
            <div className="space-y-3 py-2">
              <Separator />
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t('created.temp_password')}
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-sm select-all">
                  {tempPwData.tempPassword}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-9 w-9 shrink-0"
                  onClick={handleCopyTempPw}
                  data-testid="copy-temp-pw-btn"
                >
                  {copiedPw
                    ? <CheckCheck className="h-4 w-4 text-green-600" />
                    : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {t('created.hint')}
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              className="w-full"
              onClick={() => setTempPwData(null)}
              data-testid="close-temp-pw-btn"
            >
              {t('created.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
};

export default TeamPage;
