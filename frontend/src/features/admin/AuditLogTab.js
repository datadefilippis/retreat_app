import React, { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '../../api';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import { ScrollText, RefreshCw, Filter, X } from 'lucide-react';
import { toast } from 'sonner';

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Format an ISO datetime string to a human-readable local datetime.
 * e.g. "12 Mar 2026, 14:32:05"
 */
function formatDateTime(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-GB', {
    day:    '2-digit',
    month:  'short',
    year:   'numeric',
    hour:   '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Color-code audit log actions by semantic category.
 */
function actionBadgeClass(action) {
  if (!action) return 'bg-gray-100 text-gray-700';
  if (action.includes('suspend')    || action.includes('deactivate'))
    return 'bg-red-100 text-red-800';
  if (action.includes('reactivate') || action.includes('activate'))
    return 'bg-green-100 text-green-800';
  if (action.includes('reset_password'))
    return 'bg-amber-100 text-amber-800';
  if (action.includes('plan'))
    return 'bg-blue-100 text-blue-800';
  if (action === 'login')
    return 'bg-gray-100 text-gray-500';
  return 'bg-gray-100 text-gray-700';
}

/**
 * Render a compact key=value summary of the details dict.
 * Skips any key called "password" for safety.
 */
function formatDetails(details) {
  if (!details || Object.keys(details).length === 0) return '—';
  return Object.entries(details)
    .filter(([k]) => k !== 'password')
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join('  ');
}

// ── Component ─────────────────────────────────────────────────────────────────

const AuditLogTab = () => {
  const [logs, setLogs]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal]     = useState(0);

  // Filter inputs (live)
  const [inputOrgId,  setInputOrgId]  = useState('');
  const [inputUserId, setInputUserId] = useState('');
  const [inputAction, setInputAction] = useState('');

  // Applied filters — only update on explicit "Apply" or Enter
  const [applied, setApplied] = useState({ orgId: '', userId: '', action: '' });

  // ── Data fetch ──────────────────────────────────────────────────────────────

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    const params = { limit: 100 };
    if (applied.orgId)  params.org_id  = applied.orgId;
    if (applied.userId) params.user_id = applied.userId;
    if (applied.action) params.action  = applied.action;
    try {
      const res = await adminAPI.listAuditLog(params);
      setLogs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, [applied]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // ── Filter helpers ──────────────────────────────────────────────────────────

  const applyFilters = () => {
    setApplied({
      orgId:  inputOrgId.trim(),
      userId: inputUserId.trim(),
      action: inputAction.trim(),
    });
  };

  const clearFilters = () => {
    setInputOrgId('');
    setInputUserId('');
    setInputAction('');
    setApplied({ orgId: '', userId: '', action: '' });
  };

  const hasActiveFilters = applied.orgId || applied.userId || applied.action;

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') applyFilters();
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <Card className="border border-border">
      <CardHeader>
        <div className="flex flex-col gap-3">
          {/* Title row */}
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <ScrollText className="h-5 w-5" />
                Audit Log
              </CardTitle>
              <CardDescription>
                Global audit log — all organizations and system-admin actions
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>

          {/* Filter row */}
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Filter by org ID…"
              value={inputOrgId}
              onChange={(e) => setInputOrgId(e.target.value)}
              onKeyDown={handleKeyDown}
              className="h-8 w-44"
            />
            <Input
              placeholder="Filter by user ID…"
              value={inputUserId}
              onChange={(e) => setInputUserId(e.target.value)}
              onKeyDown={handleKeyDown}
              className="h-8 w-44"
            />
            <Input
              placeholder="Filter by action…"
              value={inputAction}
              onChange={(e) => setInputAction(e.target.value)}
              onKeyDown={handleKeyDown}
              className="h-8 w-36"
            />
            <Button size="sm" variant="outline" onClick={applyFilters}>
              <Filter className="h-3.5 w-3.5 mr-1" />
              Apply
            </Button>
            {hasActiveFilters && (
              <Button size="sm" variant="ghost" onClick={clearFilters}>
                <X className="h-3.5 w-3.5 mr-1" />
                Clear
              </Button>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            {total} total entries
            {hasActiveFilters ? ' matching filters' : ''}
          </p>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : logs.length === 0 ? (
          <p className="text-sm text-muted-foreground py-6 text-center">
            {hasActiveFilters
              ? 'No audit log entries match the current filters.'
              : 'No audit log entries found.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-nowrap">Timestamp</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDateTime(log.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge className={`text-xs ${actionBadgeClass(log.action)}`}>
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs font-mono text-muted-foreground">
                      {log.user_id ? `${log.user_id.slice(0, 8)}…` : '—'}
                    </TableCell>
                    <TableCell className="text-xs">
                      <span className="font-medium">{log.resource_type}</span>
                      {log.resource_id && (
                        <span className="ml-1 font-mono text-muted-foreground">
                          {log.resource_id.length > 16
                            ? `${log.resource_id.slice(0, 16)}…`
                            : log.resource_id}
                        </span>
                      )}
                    </TableCell>
                    <TableCell
                      className="text-xs text-muted-foreground max-w-xs truncate"
                      title={formatDetails(log.details)}
                    >
                      {formatDetails(log.details)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AuditLogTab;
