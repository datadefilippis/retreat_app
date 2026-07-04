import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  ShieldCheck, Loader2, RefreshCw, Play, CheckCircle2, AlertTriangle, Link2,
} from 'lucide-react';
import { dataIntegrityAPI } from '../../api/dataIntegrity';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

function CoverageBar({ label, linked, unlinked, pct }) {
  const total = linked + unlinked;
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{pct}% <span className="text-muted-foreground font-normal">({linked}/{total})</span></span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

function CoverageSection({ coverage, loading }) {
  const { t } = useTranslation('data_integrity');
  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">{t('coverage.title')}</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="h-8 bg-muted rounded animate-pulse" />)}
        </CardContent>
      </Card>
    );
  }

  if (!coverage || Object.keys(coverage).length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">{t('coverage.title')}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t('coverage.no_data')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" />
          {t('coverage.title')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {Object.entries(coverage).map(([dsType, dsData]) => (
          <div key={dsType}>
            <h4 className="text-sm font-semibold mb-2">{t(`dataset.${dsType}`, { defaultValue: dsType })}
              <span className="text-xs text-muted-foreground font-normal ml-2">{dsData.total} {t('coverage.total_records')}</span>
            </h4>
            <div className="space-y-2">
              {Object.entries(dsData).filter(([k]) => k !== 'total').map(([entityKey, stats]) => (
                <CoverageBar
                  key={entityKey}
                  label={t(`entity.${entityKey}`, { defaultValue: entityKey })}
                  linked={stats.linked}
                  unlinked={stats.unlinked}
                  pct={stats.pct}
                />
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

/* ── Relink Preview/Apply ─────────────────────────────────────────────────── */

function RelinkSection({ isAdmin, onCoverageRefresh }) {
  const { t } = useTranslation('data_integrity');
  const [datasetType, setDatasetType] = useState('sales');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const runPreview = async () => {
    setLoading(true);
    setPreview(null);
    setConfirmOpen(false);
    try {
      const res = await dataIntegrityAPI.relink(datasetType, true);
      setPreview(res.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('relink.toast_scan_error'));
    } finally { setLoading(false); }
  };

  const runApply = async () => {
    setApplying(true);
    try {
      const res = await dataIntegrityAPI.relink(datasetType, false);
      const applied = res.data?.links_applied || 0;
      toast.success(t('relink.toast_applied', { count: applied }));
      setPreview(null);
      setConfirmOpen(false);
      onCoverageRefresh?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('relink.toast_apply_error'));
    } finally { setApplying(false); }
  };

  if (!isAdmin) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">{t('relink.title')}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t('relink.admin_only')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Link2 className="h-4 w-4" />
          {t('relink.title')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {t('relink.description')}
        </p>

        {/* Dataset selector + preview button */}
        <div className="flex items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">{t('relink.dataset_label')}</label>
            <select
              value={datasetType}
              onChange={(e) => { setDatasetType(e.target.value); setPreview(null); setConfirmOpen(false); }}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            >
              <option value="sales">{t('dataset.sales')}</option>
              <option value="purchases">{t('dataset.purchases')}</option>
              <option value="expenses">{t('dataset.expenses')}</option>
            </select>
          </div>
          <Button variant="outline" size="sm" onClick={runPreview} disabled={loading} className="gap-1.5">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {t('relink.preview')}
          </Button>
        </div>

        {/* Preview results */}
        {preview && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">{t('relink.scan_result')}</h4>
              <Badge className={`text-xs ${preview.candidates_found > 0 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>
                {preview.candidates_found > 0 ? `${preview.candidates_found} ${t('relink.candidates')}` : t('relink.no_candidates')}
              </Badge>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-md bg-background p-2">
                <p className="text-xs text-muted-foreground">{t('relink.scanned')}</p>
                <p className="text-lg font-bold">{preview.scanned}</p>
              </div>
              <div className="rounded-md bg-background p-2">
                <p className="text-xs text-muted-foreground">{t('relink.candidates_label')}</p>
                <p className="text-lg font-bold text-blue-600">{preview.candidates_found}</p>
              </div>
              <div className="rounded-md bg-background p-2">
                <p className="text-xs text-muted-foreground">{t('relink.resolver')}</p>
                <p className="text-xs font-medium mt-1">
                  {Object.entries(preview.map_sizes || {}).map(([k, v]) => `${k}: ${v}`).join(', ') || '-'}
                </p>
              </div>
            </div>

            {/* By entity breakdown */}
            {preview.by_entity && Object.keys(preview.by_entity).length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">{t('relink.by_entity')}</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(preview.by_entity).map(([entity, count]) => (
                    <Badge key={entity} variant="outline" className="text-xs">
                      {t(`entity.${entity}`, { defaultValue: entity })}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Samples */}
            {preview.samples && preview.samples.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">{t('relink.samples')}</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {preview.samples.map((s, i) => (
                    <div key={i} className="text-xs rounded bg-background p-2 flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <span className="text-muted-foreground">{s.date}</span>
                        <span className="ml-2 truncate">{s.description}</span>
                      </div>
                      <div className="shrink-0 flex gap-1">
                        {Object.entries(s.links).map(([k, v]) => (
                          <Badge key={k} className="text-[10px] px-1.5 py-0 bg-emerald-50 text-emerald-600">
                            {t(`entity.${k}`, { defaultValue: k })}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Apply action */}
            {preview.candidates_found > 0 && (
              <div className="border-t pt-3">
                {!confirmOpen ? (
                  <Button size="sm" onClick={() => setConfirmOpen(true)} className="gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t('relink.apply')} {t('relink.links', { count: preview.candidates_found })}
                  </Button>
                ) : (
                  <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                    <div className="flex-1">
                      <p className="text-xs font-medium text-amber-800">
                        {t('relink.confirm_title')} {t('relink.confirm_desc', { count: preview.candidates_found })}
                      </p>
                      <p className="text-[11px] text-amber-600 mt-0.5">{t('relink.confirm_audit')}</p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button variant="outline" size="sm" onClick={() => setConfirmOpen(false)} disabled={applying}>
                        {t('relink.cancel')}
                      </Button>
                      <Button size="sm" onClick={runApply} disabled={applying} className="gap-1">
                        {applying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                        {t('relink.confirm')}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */

export default function DataIntegrityPage() {
  const { t } = useTranslation('data_integrity');
  const { user } = useAuth();
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);

  const isAdmin = user?.role === 'admin' || user?.role === 'system_admin';

  const loadCoverage = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dataIntegrityAPI.getCoverage();
      setCoverage(res.data?.coverage || {});
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadCoverage(); }, [loadCoverage]);

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')}>
        <Button variant="outline" size="sm" onClick={loadCoverage} className="gap-1">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </Header>

      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
        <CoverageSection coverage={coverage} loading={loading} />
        <RelinkSection isAdmin={isAdmin} onCoverageRefresh={loadCoverage} />
      </div>
    </AppLayout>
  );
}
