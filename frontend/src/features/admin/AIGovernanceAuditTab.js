import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '../../components/ui/card';
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from '../../components/ui/table';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import {
  RefreshCw, History, AlertTriangle, Power, ShieldAlert,
  Pencil, Plus, Trash2,
} from 'lucide-react';
import { adminAPI } from '../../api';

/**
 * AIGovernanceAuditTab — Wave 10.C.6.
 *
 * Lists kill-switch toggles and budget CRUD operations from the existing
 * audit_logs collection, filtered to resource_type in (ai_governance,
 * ai_budget).
 *
 * Source: /api/admin/ai-governance/audit-log
 */

function formatTimestamp(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function ActionBadge({ action }) {
  // Pick an icon + colour per action so the operator can scan quickly.
  const map = {
    kill_switch_updated: { icon: Power, color: 'bg-amber-100 text-amber-800 border-amber-200', label: 'Kill switch' },
    budget_created:      { icon: Plus,  color: 'bg-green-100 text-green-800 border-green-200', label: 'Created' },
    budget_upserted:     { icon: Pencil, color: 'bg-blue-100 text-blue-800 border-blue-200',   label: 'Re-upserted' },
    budget_updated:      { icon: Pencil, color: 'bg-blue-100 text-blue-800 border-blue-200',   label: 'Updated' },
    budget_deleted:      { icon: Trash2, color: 'bg-red-100 text-red-800 border-red-200',      label: 'Deleted' },
  };
  const entry = map[action] || { icon: AlertTriangle,
                                 color: 'bg-gray-100 text-gray-800 border-gray-200',
                                 label: action };
  const Icon = entry.icon;
  return (
    <Badge variant="outline" className={`text-xs ${entry.color}`}>
      <Icon className="h-3 w-3 mr-1 inline-block" />
      {entry.label}
    </Badge>
  );
}

function ResourceBadge({ type }) {
  if (type === 'ai_governance') {
    return (
      <Badge variant="outline" className="text-xs">
        <ShieldAlert className="h-3 w-3 mr-1 inline-block" />
        Kill switch
      </Badge>
    );
  }
  if (type === 'ai_budget') {
    return <Badge variant="outline" className="text-xs">Budget</Badge>;
  }
  return <Badge variant="outline" className="text-xs">{type}</Badge>;
}

function renderDetails(details) {
  if (!details || Object.keys(details).length === 0) {
    return <span className="text-muted-foreground text-xs">—</span>;
  }
  // For kill switch: ai_enabled + throttle + reason
  if ('ai_enabled' in details) {
    return (
      <div className="text-xs space-y-0.5">
        <div>
          <span className="font-mono">enabled=</span>
          <strong>{String(details.ai_enabled)}</strong>
          <span className="mx-1">·</span>
          <span className="font-mono">throttle=</span>
          <strong>{details.ai_throttle_pct}%</strong>
        </div>
        {details.reason && (
          <div className="text-muted-foreground italic">{details.reason}</div>
        )}
      </div>
    );
  }
  // For budget create/upsert: show scope + limits
  if ('scope' in details && 'hard_limit_usd' in details) {
    return (
      <div className="text-xs space-y-0.5">
        <div>
          <span className="font-mono">{details.scope}/{details.scope_id || '*'}</span>
          <span className="mx-1">·</span>
          <span className="font-mono">{details.period}</span>
        </div>
        <div>
          soft <strong>${details.soft_limit_usd?.toFixed?.(2) ?? details.soft_limit_usd}</strong>
          <span className="mx-1">·</span>
          hard <strong>${details.hard_limit_usd?.toFixed?.(2) ?? details.hard_limit_usd}</strong>
        </div>
        {details.notes && (
          <div className="text-muted-foreground italic truncate max-w-[400px]">{details.notes}</div>
        )}
      </div>
    );
  }
  // For budget update: list of changes
  if ('changes' in details) {
    const keys = Object.keys(details.changes || {});
    if (keys.length === 0) return <span className="text-xs text-muted-foreground">no changes</span>;
    return (
      <div className="text-xs space-y-0.5">
        {keys.map((k) => (
          <div key={k}>
            <span className="font-mono text-muted-foreground">{k}:</span>{' '}
            <strong>{String(details.changes[k])}</strong>
          </div>
        ))}
      </div>
    );
  }
  // Snapshot of deleted budget
  if ('snapshot' in details && details.snapshot) {
    const s = details.snapshot;
    return (
      <div className="text-xs space-y-0.5">
        <div>
          deleted <span className="font-mono">{s.scope}/{s.scope_id || '*'}</span>
          <span className="mx-1">·</span>
          <span className="font-mono">{s.period}</span>
        </div>
        {s.hard_limit_usd != null && (
          <div>was hard ${s.hard_limit_usd?.toFixed?.(2) ?? s.hard_limit_usd}</div>
        )}
      </div>
    );
  }
  // Fallback: JSON dump
  return (
    <pre className="text-xs text-muted-foreground overflow-hidden max-w-[400px]">
      {JSON.stringify(details, null, 0)}
    </pre>
  );
}

const PAGE_SIZE = 50;

const AIGovernanceAuditTab = () => {
  const [rows, setRows] = useState(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (currentOffset) => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminAPI.getAIGovernanceAuditLog({
        limit: PAGE_SIZE,
        offset: currentOffset,
      });
      setRows(res.rows || []);
      setTotal(res.total || 0);
      setOffset(res.offset || 0);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(0);
  }, [load]);

  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <div className="space-y-4">
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-4 pb-4 flex items-center gap-2 text-red-700">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-blue-600" />
              Governance history
            </CardTitle>
            <CardDescription>
              Kill-switch toggles and budget CRUD operations, newest first.
              Persisted in the platform audit log (365-day TTL).
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => load(offset)}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {rows === null ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : rows.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No governance mutations recorded yet. As you toggle the kill
              switch or create/edit/delete budgets, the actions will appear here.
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="whitespace-nowrap">When</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Details</TableHead>
                    <TableHead>Actor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-xs whitespace-nowrap">
                        {formatTimestamp(r.created_at)}
                      </TableCell>
                      <TableCell>
                        <ResourceBadge type={r.resource_type} />
                      </TableCell>
                      <TableCell>
                        <ActionBadge action={r.action} />
                      </TableCell>
                      <TableCell>
                        {renderDetails(r.details)}
                      </TableCell>
                      <TableCell className="text-xs font-mono whitespace-nowrap">
                        {r.user_id === 'system'
                          ? <Badge variant="outline" className="text-xs">system</Badge>
                          : (r.user_id ? r.user_id.slice(-12) : '—')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex items-center justify-between gap-3 pt-4">
                <p className="text-xs text-muted-foreground">
                  Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canPrev || loading}
                    onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canNext || loading}
                    onClick={() => load(offset + PAGE_SIZE)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AIGovernanceAuditTab;
