import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Switch } from '../../components/ui/switch';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from '../../components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import { MailPlus, Copy, XCircle, Loader2 } from 'lucide-react';
import { adminAPI } from '../../api';
import { toast } from 'sonner';


const STATUS_BADGES = {
  pending: <Badge variant="outline" className="border-green-300 text-green-700">Pending</Badge>,
  used:    <Badge variant="secondary">Used</Badge>,
  revoked: <Badge variant="destructive">Revoked</Badge>,
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('it-IT', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
};


const InvitesTab = () => {
  // ── Registration Mode Toggle ────────────────────────────────────────
  const [regMode, setRegMode] = useState('open');
  const [modeLoading, setModeLoading] = useState(true);

  const fetchMode = useCallback(async () => {
    try {
      const data = await adminAPI.getRegistrationMode();
      setRegMode(data.registration_mode);
    } catch {
      toast.error('Failed to load registration mode');
    } finally {
      setModeLoading(false);
    }
  }, []);

  useEffect(() => { fetchMode(); }, [fetchMode]);

  const handleToggleMode = async (checked) => {
    const newMode = checked ? 'invite_only' : 'open';
    setModeLoading(true);
    try {
      await adminAPI.setRegistrationMode(newMode);
      setRegMode(newMode);
      toast.success(`Registration mode: ${newMode === 'invite_only' ? 'Invite only' : 'Open'}`);
    } catch {
      toast.error('Failed to update registration mode');
    } finally {
      setModeLoading(false);
    }
  };

  // ── Invite CRUD ─────────────────────────────────────────────────────
  const [invites, setInvites] = useState([]);
  const [total, setTotal] = useState(0);
  const [invitesLoading, setInvitesLoading] = useState(true);

  const fetchInvites = useCallback(async () => {
    try {
      const data = await adminAPI.listInvites(0, 100);
      setInvites(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error('Failed to load invites');
    } finally {
      setInvitesLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvites(); }, [fetchInvites]);

  // ── Create Invite Dialog ────────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdUrl, setCreatedUrl] = useState('');

  const handleCreateInvite = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const data = await adminAPI.createInvite(inviteEmail);
      setCreatedUrl(data.invite_url || '');
      toast.success(`Invite sent to ${inviteEmail}`);
      setInviteEmail('');
      fetchInvites();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create invite');
    } finally {
      setCreating(false);
    }
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(createdUrl);
    toast.success('Link copied to clipboard');
  };

  const handleCloseCreateDialog = (open) => {
    if (!open) {
      setCreatedUrl('');
      setInviteEmail('');
    }
    setCreateOpen(open);
  };

  // ── Revoke ──────────────────────────────────────────────────────────
  const [revokingId, setRevokingId] = useState(null);

  const handleRevoke = async (inviteId) => {
    setRevokingId(inviteId);
    try {
      await adminAPI.revokeInvite(inviteId);
      toast.success('Invite revoked');
      fetchInvites();
    } catch {
      toast.error('Failed to revoke invite');
    } finally {
      setRevokingId(null);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Registration Mode Toggle */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Registration Mode</CardTitle>
          <CardDescription>
            Control whether new users can sign up freely or only via invitation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Invite-only registration</p>
              <p className="text-sm text-muted-foreground">
                {regMode === 'invite_only'
                  ? 'Only users with an invite link can register.'
                  : 'Anyone can create an account.'}
              </p>
            </div>
            <Switch
              checked={regMode === 'invite_only'}
              onCheckedChange={handleToggleMode}
              disabled={modeLoading}
            />
          </div>
        </CardContent>
      </Card>

      {/* Invite Management */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Platform Invitations</CardTitle>
            <CardDescription>{total} invite(s) total</CardDescription>
          </div>
          <Dialog open={createOpen} onOpenChange={handleCloseCreateDialog}>
            <DialogTrigger asChild>
              <Button size="sm">
                <MailPlus className="h-4 w-4 mr-2" />
                Invite User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite New User</DialogTitle>
                <DialogDescription>
                  Send an invitation link to a new user. The link expires in 7 days.
                </DialogDescription>
              </DialogHeader>

              {createdUrl ? (
                <div className="space-y-4 pt-2">
                  <div className="rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-800">
                    Invitation created successfully!
                  </div>
                  <div className="space-y-1.5">
                    <Label>Invite Link</Label>
                    <div className="flex gap-2">
                      <Input value={createdUrl} readOnly className="font-mono text-xs" />
                      <Button variant="outline" size="icon" onClick={handleCopyUrl}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Share this link with the user. It can only be used once.
                    </p>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateInvite} className="space-y-4 pt-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="invite-email">Email</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="user@company.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={creating}>
                    {creating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <MailPlus className="h-4 w-4 mr-2" />
                        Send Invitation
                      </>
                    )}
                  </Button>
                </form>
              )}
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {invitesLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading invites...</div>
          ) : invites.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No invitations yet. Click "Invite User" to send one.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invites.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell className="font-medium">{inv.email}</TableCell>
                    <TableCell>{STATUS_BADGES[inv.status] || inv.status}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{fmtDate(inv.created_at)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{fmtDate(inv.expires_at)}</TableCell>
                    <TableCell className="text-right">
                      {inv.status === 'pending' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRevoke(inv.id)}
                          disabled={revokingId === inv.id}
                        >
                          {revokingId === inv.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <XCircle className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default InvitesTab;
