import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp, Settings, Lock } from 'lucide-react';
import { datasetsAPI } from '../api';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { useEntitlements } from '../hooks/useEntitlements';
import { ColumnMappingDialog } from '../features/datasets/ColumnMappingDialog';
import { DuplicateWarningDialog } from '../features/datasets/DuplicateWarningDialog';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';

// ── Import Result Panel ──────────────────────────────────────────────────────
// Shows a detailed, user-friendly summary of what happened during import.
// Replaces the old minimal "N righe" display with full transparency.

const ImportResultPanel = ({ result, t }) => {
  const [errorsExpanded, setErrorsExpanded] = React.useState(false);

  if (!result) return null;

  // Error state (HTTP error, not import result)
  if (!result.success) {
    return (
      <div className="flex items-start gap-2 text-sm p-3 rounded-md bg-red-50 text-red-700">
        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
        <span>{result.error}</span>
      </div>
    );
  }

  const data = result.data;
  const rowCount = data.row_count || 0;
  const errors = data.errors || [];
  const dupSkipped = data.duplicate_rows_skipped || 0;
  const valSkipped = data.validation_rows_skipped || 0;
  const totalSkipped = errors.length + dupSkipped + valSkipped;
  const hasIssues = totalSkipped > 0 || errors.length > 0;
  const displayErrors = errorsExpanded ? errors : errors.slice(0, 3);

  return (
    <div className={`text-sm p-3 rounded-md space-y-2 ${
      hasIssues ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'
    }`}>
      {/* Main success line */}
      <div className="flex items-center gap-2">
        <CheckCircle2 className={`h-4 w-4 shrink-0 ${hasIssues ? 'text-amber-600' : 'text-green-600'}`} />
        <span className={`font-medium ${hasIssues ? 'text-amber-800' : 'text-green-800'}`}>
          {t('upload.result_imported', { count: rowCount })}
        </span>
      </div>

      {/* Skipped rows summary */}
      {hasIssues && (
        <div className="ml-6 space-y-1">
          {errors.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-red-700">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              <span>{t('upload.result_parsing_errors', { count: errors.length })}</span>
            </div>
          )}
          {dupSkipped > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-blue-700">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              <span>{t('upload.result_duplicates_skipped', { count: dupSkipped })}</span>
            </div>
          )}
          {valSkipped > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-amber-700">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              <span>{t('upload.result_validation_skipped', { count: valSkipped })}</span>
            </div>
          )}
        </div>
      )}

      {/* Duplicate warning */}
      {data.duplicate_warning && (
        <div className="ml-6 flex items-start gap-1.5 text-xs text-amber-700">
          <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
          <span>{data.duplicate_warning}</span>
        </div>
      )}

      {/* Error detail list */}
      {errors.length > 0 && (
        <div className="ml-6 mt-2">
          <button
            onClick={() => setErrorsExpanded(!errorsExpanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1"
          >
            {errorsExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {t('upload.result_show_errors', { count: errors.length })}
          </button>
          {(errorsExpanded || errors.length <= 3) && (
            <ul className="space-y-0.5 text-xs text-red-600 font-mono">
              {displayErrors.map((err, i) => (
                <li key={i} className="truncate">{err}</li>
              ))}
              {!errorsExpanded && errors.length > 3 && (
                <li className="text-muted-foreground italic">
                  +{errors.length - 3} {t('upload.result_more_errors')}
                </li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};


const TYPE_CONFIG = {
  sales: {
    label: 'Vendite',
    description: 'CSV/XLSX con colonne: date, amount, category, description, channel',
    exampleCsv: 'date,amount,category,description,channel\n2025-01-15,1250.00,food_sales,Pranzo,dine_in',
  },
  expenses: {
    label: 'Spese',
    description: 'CSV/XLSX con colonne: date, amount, category, description, supplier',
    exampleCsv: 'date,amount,category,description,supplier\n2025-01-15,450.00,ingredients,Acquisto ingredienti,Food Supplier',
  },
  purchases: {
    label: 'Acquisti',
    description: 'CSV/XLSX con colonne: date, supplier_name, quantity, unit, unit_price, category',
    exampleCsv: 'date,supplier_name,quantity,unit,unit_price,category\n2025-01-15,Fornitore Carni SRL,25,kg,12.50,carni',
  },
  fixed_costs: {
    label: 'Costi Fissi',
    description: 'CSV/XLSX con colonne: name, category, amount, frequency, start_date, end_date',
    exampleCsv: 'name,category,amount,frequency,start_date,end_date\nAffitto,affitto,3500,mensile,2024-01-01,',
  },
};

export const ModuleDatasetManager = ({ datasetType, onUploadComplete }) => {
  const { t } = useTranslation('cashflow_monitor');
  const { t: tCommon } = useTranslation('common');
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const fileInputRef = useRef(null);
  const config = TYPE_CONFIG[datasetType] || TYPE_CONFIG.sales;

  // v5.8 / Onda 9.Y.0.2 (Step D) — Pre-emptive UI gate.
  // Imports write data_rows usage events (multiple per file). If the
  // org is already at quota, disable Upload pre-flight instead of
  // letting the user pick a file and getting a 429 mid-parse.
  const { quotaExhausted, getMetric } = useEntitlements();
  const dataRowsExhausted = quotaExhausted('cashflow_monitor', 'data_rows');
  const dataRowsMetric = getMetric('data_rows');

  // Column mapping dialog state
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [mappingData, setMappingData] = useState(null);
  const [mappingLoading, setMappingLoading] = useState(false);

  // Duplicate warning dialog state
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [duplicateData, setDuplicateData] = useState(null);

  // Quota exceeded dialog state
  const [quotaDialogOpen, setQuotaDialogOpen] = useState(false);
  const [quotaMessage, setQuotaMessage] = useState('');

  // Store pending file/name for re-upload after duplicate confirmation
  const pendingFileRef = useRef(null);
  const pendingNameRef = useRef('');

  const doUpload = async (file, name, confirmDuplicate = false, skipDuplicateRows = false) => {
    setUploading(true);
    setUploadResult(null);

    try {
      const response = await datasetsAPI.upload(file, name, datasetType, confirmDuplicate, skipDuplicateRows);
      setUploadResult({ success: true, data: response.data });
      const skippedMsg = response.data.duplicate_rows_skipped > 0
        ? `, ${response.data.duplicate_rows_skipped} duplicate rimosse`
        : '';
      toast.success(`Dataset "${name}" caricato con successo (${response.data.row_count} righe${skippedMsg})`);
      pendingFileRef.current = null;
      pendingNameRef.current = '';
      if (onUploadComplete) onUploadComplete(response.data);
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      // 409 duplicate found → show confirmation dialog
      if (status === 409 && detail && typeof detail === 'object' && detail.status === 'duplicate_found') {
        // Store file reference for re-upload on confirm
        pendingFileRef.current = file;
        pendingNameRef.current = name;
        setDuplicateData(detail);
        setDuplicateDialogOpen(true);
        return;
      }

      // 422 with needs_column_mapping → show mapping dialog
      if (status === 422 && detail && typeof detail === 'object' && detail.status === 'needs_column_mapping') {
        setMappingData(detail);
        setMappingDialogOpen(true);
        return;
      }

      // 429 QUOTA_EXCEEDED → show clear upgrade dialog
      if (status === 429 && detail && typeof detail === 'object' && detail.code === 'QUOTA_EXCEEDED') {
        setQuotaMessage(detail.message || t('upload.quota_exceeded_default', 'Hai raggiunto il limite di righe del piano gratuito.'));
        setQuotaDialogOpen(true);
        return;
      }

      // Other errors — always ensure detail is a string
      const errorMsg = typeof detail === 'string'
        ? detail
        : (typeof detail === 'object' && detail.message) ? detail.message : t('upload.upload_error');
      setUploadResult({ success: false, error: errorMsg });
      toast.error(errorMsg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const name = datasetName.trim() || file.name.replace(/\.[^/.]+$/, '');
    await doUpload(file, name, false);
  };

  // Pending mapping info for re-submission after duplicate confirmation
  const pendingMappingRef = useRef(null);

  const handleDuplicateConfirm = (skipDuplicateRows = false) => {
    setDuplicateDialogOpen(false);
    setDuplicateData(null);
    if (pendingMappingRef.current) {
      // Duplicate came from the mapping flow → re-call with confirmDuplicate
      const { tempId, mapping, saveMapping } = pendingMappingRef.current;
      pendingMappingRef.current = null;
      doMappingUpload(tempId, mapping, saveMapping, true, skipDuplicateRows);
    } else if (pendingFileRef.current) {
      // Duplicate came from the direct upload flow
      doUpload(pendingFileRef.current, pendingNameRef.current, true, skipDuplicateRows);
    }
  };

  const doMappingUpload = async (tempId, mapping, saveMapping, confirmDuplicate = false, skipDuplicateRows = false) => {
    setMappingLoading(true);
    try {
      const resp = await datasetsAPI.uploadWithMapping(tempId, mapping, saveMapping, confirmDuplicate, skipDuplicateRows);
      setUploadResult({ success: true, data: resp.data });
      const skippedMsg = resp.data.duplicate_rows_skipped > 0
        ? `, ${resp.data.duplicate_rows_skipped} duplicate rimosse`
        : '';
      toast.success(`Dataset caricato con successo (${resp.data.row_count} righe${skippedMsg})`);
      setMappingDialogOpen(false);
      setMappingData(null);
      pendingFileRef.current = null;
      pendingNameRef.current = '';
      pendingMappingRef.current = null;
      if (onUploadComplete) onUploadComplete(resp.data);
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      // 409 duplicate found → show confirmation dialog
      if (status === 409 && detail && typeof detail === 'object' && detail.status === 'duplicate_found') {
        pendingMappingRef.current = { tempId, mapping, saveMapping };
        setMappingDialogOpen(false);
        setDuplicateData(detail);
        setDuplicateDialogOpen(true);
        return;
      }

      // 429 QUOTA_EXCEEDED → show clear upgrade dialog
      if (status === 429 && detail && typeof detail === 'object' && detail.code === 'QUOTA_EXCEEDED') {
        setMappingDialogOpen(false);
        setQuotaMessage(detail.message || t('upload.quota_exceeded_default', 'Hai raggiunto il limite di righe del piano gratuito.'));
        setQuotaDialogOpen(true);
        return;
      }

      const errorMsg = typeof detail === 'string'
        ? detail
        : (typeof detail === 'object' && detail.message) ? detail.message : t('upload.upload_error');
      toast.error(errorMsg);
    } finally {
      setMappingLoading(false);
    }
  };

  const handleMappingConfirm = async (mapping, saveMapping) => {
    if (!mappingData?.temp_upload_id) return;
    await doMappingUpload(mappingData.temp_upload_id, mapping, saveMapping, false);
  };

  const downloadExample = () => {
    const blob = new Blob([config.exampleCsv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `esempio_${datasetType}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-heading">
            <FileSpreadsheet className="inline h-4 w-4 mr-2" />
            {t('upload.import_label', { type: t(`upload.type_${datasetType}`) })}
          </CardTitle>
          <CardDescription className="text-xs">{config.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Input
              placeholder="Nome dataset (opzionale)"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="text-sm"
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                disabled={uploading || dataRowsExhausted}
                onClick={dataRowsExhausted ? undefined : () => fileInputRef.current?.click()}
                title={dataRowsExhausted
                  ? t('upload.quota_exhausted_hint', { defaultValue: 'Limite righe dati raggiunto. Aggiorna piano.' })
                  : undefined}
              >
                {dataRowsExhausted ? <Lock className="h-4 w-4 mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
                {uploading ? t('upload.uploading') : t('upload.select_file')}
              </Button>
              <Button variant="ghost" size="sm" onClick={downloadExample}>
                Esempio CSV
              </Button>
            </div>
            {dataRowsExhausted && dataRowsMetric && (
              <p className="text-xs text-muted-foreground">
                {t('upload.quota_exhausted_body', {
                  used: dataRowsMetric.used,
                  limit: dataRowsMetric.limit,
                  defaultValue: 'Hai raggiunto il limite di {{used}}/{{limit}} righe dati questo mese.',
                })}
                {' '}
                <Link to="/billing" className="underline font-medium text-primary">
                  {t('upload.quota_exhausted_cta', { defaultValue: 'Aggiorna piano' })}
                </Link>
              </p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleUpload}
            />
          </div>

          {uploadResult && (
            <ImportResultPanel
              result={uploadResult}
              t={t}
            />
          )}
        </CardContent>
      </Card>

      {/* Column mapping dialog */}
      <ColumnMappingDialog
        open={mappingDialogOpen}
        onClose={() => {
          setMappingDialogOpen(false);
          setMappingData(null);
        }}
        onConfirm={handleMappingConfirm}
        mappingData={mappingData}
        loading={mappingLoading}
      />

      {/* Duplicate warning dialog */}
      <DuplicateWarningDialog
        open={duplicateDialogOpen}
        onClose={() => {
          setDuplicateDialogOpen(false);
          setDuplicateData(null);
          pendingFileRef.current = null;
          pendingNameRef.current = '';
        }}
        onConfirm={handleDuplicateConfirm}
        duplicateData={duplicateData}
        loading={uploading}
      />

      {/* Quota exceeded dialog */}
      <Dialog open={quotaDialogOpen} onOpenChange={setQuotaDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-orange-100">
              <AlertTriangle className="h-6 w-6 text-orange-600" />
            </div>
            <DialogTitle className="text-center text-lg">
              {tCommon('quota.dialog_title')}
            </DialogTitle>
            <DialogDescription className="text-center text-sm text-muted-foreground mt-2">
              {tCommon('quota.dialog_description')}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2 mt-4">
            <Button
              onClick={() => { setQuotaDialogOpen(false); navigate('/settings'); }}
              className="w-full"
            >
              <Settings className="h-4 w-4 mr-2" />
              {tCommon('quota.dialog_go_settings')}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setQuotaDialogOpen(false)}
              className="w-full text-muted-foreground"
            >
              {tCommon('quota.dialog_close')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ModuleDatasetManager;
