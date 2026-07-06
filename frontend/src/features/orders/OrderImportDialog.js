import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useDropzone } from 'react-dropzone';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Upload, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, X, Download,
} from 'lucide-react';
import { ordersAPI } from '../../api';
import { toast } from 'sonner';
import { isPaywallHandled } from '../../utils/handleApiError';
import { ColumnMappingDialog } from './ColumnMappingDialog';

// ── Example CSV template ──────────────────────────────────────────────────────
const EXAMPLE_CSV = `cliente,email,data,prodotto,quantita,prezzo_unitario,sconto,categoria,note,scadenza,stato_pagamento
Mario Rossi,mario@example.com,2026-03-01,Pizza Margherita,10,8.50,0,food,Ordine pranzo,,pagato
Mario Rossi,mario@example.com,2026-03-01,Tiramisù,5,6.00,0,dessert,,,pagato
Luigi Bianchi,luigi@bianchi.it,2026-03-01,Pasta Carbonara,3,12.00,10,food,Sconto fedeltà,2026-03-15,pending
Anna Verdi,,2026-03-02,Vino Rosso,2,18.50,0,beverage,,2026-03-10,pending
Anna Verdi,,2026-03-02,Bruschetta,4,5.00,0,appetizer,,,pending
Luigi Bianchi,luigi@bianchi.it,2026-03-03,Pizza Diavola,8,9.00,5,food,Ordine per evento,2026-03-20,pending`;

const downloadExample = () => {
  const blob = new Blob([EXAMPLE_CSV], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'ordini_esempio.csv';
  a.click();
  URL.revokeObjectURL(url);
};

/**
 * OrderImportDialog — CSV/XLSX order import modal.
 *
 * Props:
 *   open     — boolean controlling dialog visibility
 *   onClose  — callback to close the dialog
 *   onDone   — callback after successful import (to refresh order list)
 */
export function OrderImportDialog({ open, onClose, onDone }) {
  const { t } = useTranslation('orders');

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Column mapping state
  const [mappingOpen, setMappingOpen] = useState(false);
  const [mappingData, setMappingData] = useState(null);
  const [mappingLoading, setMappingLoading] = useState(false);

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setMappingOpen(false);
    setMappingData(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
      setResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    try {
      const res = await ordersAPI.importOrders(file);
      setResult(res.data);
      toast.success(t('toast.import_success', {
        orders: res.data.orders_created,
        sales: res.data.sales_records_generated,
      }));
      onDone?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;

      // 422 → needs column mapping
      if (err?.response?.status === 422 && detail?.status === 'needs_column_mapping') {
        setMappingData(detail);
        setMappingOpen(true);
      } else if (isPaywallHandled(err)) {
        // v5.8 / Onda 9.Y.0.2 (Step E) — paywall (commerce.orders_monthly
        // OR cashflow_monitor.data_rows QUOTA_EXCEEDED) gestita dall axios
        // interceptor. Mostra solo l errore inline, niente toast competing.
        setError(detail?.message || t('toast.import_error'));
      } else {
        const msg = typeof detail === 'string' ? detail : (detail?.message || t('toast.import_error'));
        setError(msg);
        toast.error(msg);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleMappingConfirm = async (mapping) => {
    if (!mappingData?.temp_upload_id) return;
    setMappingLoading(true);

    try {
      const res = await ordersAPI.importOrdersWithMapping(
        mappingData.temp_upload_id,
        mapping,
      );
      setResult(res.data);
      setMappingOpen(false);
      setMappingData(null);
      toast.success(t('toast.import_success', {
        orders: res.data.orders_created,
        sales: res.data.sales_records_generated,
      }));
      onDone?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      // v5.8 / Onda 9.Y.0.2 (Step E) — paywall handles 429 quota.
      if (isPaywallHandled(err)) {
        setError(detail?.message || t('toast.import_error'));
        return;
      }
      const msg = typeof detail === 'string' ? detail : (detail?.message || t('toast.import_error'));
      setError(msg);
      toast.error(msg);
    } finally {
      setMappingLoading(false);
    }
  };

  return (
    <>
      <Dialog open={open && !mappingOpen} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              {t('actions.import')}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Result card */}
            {result ? (
              <div className="space-y-3 p-4 rounded-lg bg-green-50 border border-green-200">
                <div className="flex items-center gap-2 text-green-800">
                  <CheckCircle2 className="h-5 w-5 shrink-0" />
                  <span className="font-medium">{t('import.result_title')}</span>
                </div>
                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('import.orders_created')}</span>
                    <span className="font-semibold">{result.orders_created}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('import.cashflow_records')}</span>
                    <span className="font-semibold">{result.sales_records_generated}</span>
                  </div>
                  {result.customers_created > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{t('import.customers_created')}</span>
                      <Badge className="bg-blue-100 text-blue-800 border-0">
                        {result.customers_created}
                      </Badge>
                    </div>
                  )}
                  {result.customers_updated > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{t('import.customers_updated')}</span>
                      <Badge className="bg-blue-100 text-blue-800 border-0">
                        {result.customers_updated}
                      </Badge>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('import.rows_processed')}</span>
                    <span>{result.rows_processed}</span>
                  </div>
                  {result.rows_skipped > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{t('import.rows_skipped')}</span>
                      <Badge className="bg-amber-100 text-amber-800 border-0">
                        {result.rows_skipped}
                      </Badge>
                    </div>
                  )}
                </div>
                {result.errors?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs font-medium text-amber-700 flex items-center gap-1">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {t('import.warnings', { count: result.errors.length })}
                    </p>
                    <div className="max-h-32 overflow-y-auto text-xs text-muted-foreground space-y-0.5">
                      {result.errors.slice(0, 10).map((e, i) => (
                        <p key={i} className="leading-tight">{e}</p>
                      ))}
                    </div>
                  </div>
                )}
                <Button variant="outline" size="sm" className="w-full mt-2" onClick={reset}>
                  {t('import.import_another')}
                </Button>
              </div>
            ) : (
              <>
                {/* Drop zone */}
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
                    ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
                    ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <input {...getInputProps()} />
                  {file ? (
                    <div className="flex items-center justify-center gap-2">
                      <FileSpreadsheet className="h-5 w-5 text-green-600" />
                      <span className="text-sm font-medium">{file.name}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="ml-1 text-muted-foreground hover:text-foreground"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground/50" />
                      <p className="text-sm text-muted-foreground">
                        {isDragActive ? t('import.drag_active') : t('import.dropzone_hint')}
                      </p>
                    </div>
                  )}
                </div>

                {/* Info + example download */}
                <div className="text-xs text-muted-foreground space-y-1.5 px-1">
                  <p>{t('import.required_columns_plain')}</p>
                  <p>{t('import.optional_columns')}</p>
                  <p>{t('import.grouping_note')}</p>
                  <button
                    type="button"
                    onClick={downloadExample}
                    className="inline-flex items-center gap-1 text-primary hover:underline font-medium mt-0.5"
                  >
                    <Download className="h-3.5 w-3.5" />
                    {t('import.download_example')}
                  </button>
                </div>

                {/* Error */}
                {error && (
                  <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}
              </>
            )}
          </div>

          {!result && (
            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={uploading}>
                {t('import.cancel')}
              </Button>
              <Button onClick={handleUpload} disabled={!file || uploading} className="gap-2">
                {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('import.submit')}
              </Button>
            </DialogFooter>
          )}
          {result && (
            <DialogFooter>
              <Button onClick={handleClose}>{t('import.close')}</Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

      {/* Column Mapping Dialog (reused from datasets) */}
      <ColumnMappingDialog
        open={mappingOpen}
        onClose={() => { setMappingOpen(false); setMappingData(null); }}
        onConfirm={handleMappingConfirm}
        mappingData={mappingData}
        loading={mappingLoading}
      />
    </>
  );
}
