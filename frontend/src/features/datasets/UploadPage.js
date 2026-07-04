import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';
import { datasetsAPI } from '../../api';
import { formatCurrency } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';
import {
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  X,
  Download,
  ArrowRight,
  AlertTriangle,
  Link2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { isPaywallHandled } from '../../utils/handleApiError';
import { ColumnMappingDialog } from './ColumnMappingDialog';
import { DuplicateWarningDialog } from './DuplicateWarningDialog';

// ── Upload result card ────────────────────────────────────────────────────────
const UploadResultCard = ({ result, onReset }) => {
  const [showAllErrors, setShowAllErrors] = useState(false);

  const allErrors = result.errors || [];
  const parsingErrors = allErrors.filter(e => !e.includes('[validation]'));
  const validationErrors = allErrors.filter(e => e.includes('[validation]'));
  const visibleErrors = showAllErrors ? allErrors : allErrors.slice(0, 3);
  const hasErrors = allErrors.length > 0;

  return (
    <div className="space-y-4 p-4 rounded-lg bg-green-50 border border-green-200">
      <div className="flex items-center gap-2 text-green-800">
        <CheckCircle2 className="h-5 w-5 shrink-0" />
        <span className="font-medium">Upload completato</span>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Righe caricate</span>
          <span className="font-semibold">{result.row_count.toLocaleString()}</span>
        </div>
        {result.duplicate_rows_skipped > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Righe duplicate rimosse</span>
            <Badge className="bg-blue-100 text-blue-800 border-0">
              {result.duplicate_rows_skipped}
            </Badge>
          </div>
        )}
        {result.validation_rows_skipped > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Righe scartate (validation)</span>
            <Badge className="bg-amber-100 text-amber-800 border-0">
              {result.validation_rows_skipped}
            </Badge>
          </div>
        )}
        {result.validation_rules_active > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Regole attive applicate</span>
            <Badge variant="secondary">{result.validation_rules_active}</Badge>
          </div>
        )}
      </div>

      {/* Duplicate warning */}
      {result.duplicate_warning && (
        <div className="flex items-start gap-2 p-3 rounded bg-amber-50 border border-amber-200">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
          <span className="text-sm text-amber-800">{result.duplicate_warning}</span>
        </div>
      )}

      <div className="border-t border-green-200" />

      {hasErrors ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
            <span className="text-sm font-medium text-amber-800">
              {allErrors.length} {allErrors.length === 1 ? 'riga ignorata' : 'righe ignorate'}
            </span>
            {parsingErrors.length > 0 && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                {parsingErrors.length} parsing
              </Badge>
            )}
            {validationErrors.length > 0 && (
              <Badge variant="outline" className="text-xs border-amber-300 text-amber-700">
                {validationErrors.length} validation
              </Badge>
            )}
          </div>
          <ul className="space-y-1.5">
            {visibleErrors.map((err, i) => {
              const isValidation = err.includes('[validation]');
              const display = isValidation
                ? err.replace(/\[validation\]:\s*/, '').replace(/\[validation\]/, '').trim()
                : err;
              return (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Badge
                    variant="outline"
                    className={`text-xs shrink-0 mt-0.5 ${
                      isValidation ? 'border-amber-300 text-amber-700' : 'text-muted-foreground'
                    }`}
                  >
                    {isValidation ? 'validation' : 'parsing'}
                  </Badge>
                  <span className="text-muted-foreground break-all">{display}</span>
                </li>
              );
            })}
          </ul>
          {allErrors.length > 3 && (
            <button
              className="text-xs text-primary hover:underline"
              onClick={() => setShowAllErrors(v => !v)}
            >
              {showAllErrors ? 'Mostra meno' : `Mostra altri ${allErrors.length - 3} errori`}
            </button>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-green-700 text-sm">
          <CheckCircle2 className="h-4 w-4" />
          <span>Nessun errore trovato</span>
        </div>
      )}

      {/* Entity linking stats (v7.0) */}
      {result.entity_linking_stats && Object.values(result.entity_linking_stats).some(v => v > 0) && (() => {
        const s = result.entity_linking_stats;
        const lines = [];
        if ((s.customers_linked || 0) + (s.customers_unresolved || 0) > 0) {
          lines.push({ label: 'Clienti', linked: s.customers_linked || 0, unresolved: s.customers_unresolved || 0 });
        }
        if ((s.products_linked || 0) + (s.products_unresolved || 0) > 0) {
          lines.push({ label: 'Prodotti', linked: s.products_linked || 0, unresolved: s.products_unresolved || 0 });
        }
        if ((s.suppliers_linked || 0) + (s.suppliers_unresolved || 0) > 0) {
          lines.push({ label: 'Fornitori', linked: s.suppliers_linked || 0, unresolved: s.suppliers_unresolved || 0 });
        }
        if (lines.length === 0) return null;
        return (
          <div className="space-y-2 p-3 rounded bg-blue-50 border border-blue-200">
            <div className="flex items-center gap-2 text-blue-800 text-sm font-medium">
              <Link2 className="h-4 w-4 shrink-0" />
              Collegamento automatico dati
            </div>
            {lines.map((l, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{l.label}</span>
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-100 text-green-700 border-0">{l.linked} collegati</Badge>
                  {l.unresolved > 0 && (
                    <Badge className="bg-amber-100 text-amber-700 border-0">{l.unresolved} non riconosciuti</Badge>
                  )}
                </div>
              </div>
            ))}
            {lines.some(l => l.unresolved > 0) && (
              <p className="text-xs text-blue-700 mt-1">
                Verifica i nomi o codici in Dati base per migliorare il collegamento.
              </p>
            )}
          </div>
        );
      })()}

      <div className="border-t border-green-200" />

      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onReset} className="flex-1">
          Carica altro
        </Button>
        <Button size="sm" asChild className="flex-1 gap-1.5">
          <Link to="/modules/cashflow">
            Vai al Cashflow Monitor
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      </div>
    </div>
  );
};


// ── Main component ──────────────────────────────────────────────────────────

export const UploadPage = () => {
  const orgCurrency = useCurrency();
  const [datasetType, setDatasetType] = useState('sales');
  const [datasetName, setDatasetName] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [errors, setErrors] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // Column mapping dialog state
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [mappingData, setMappingData] = useState(null);
  const [mappingLoading, setMappingLoading] = useState(false);

  // Duplicate warning dialog state
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [duplicateData, setDuplicateData] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const uploadFile = acceptedFiles[0];
    if (!uploadFile) return;

    setFile(uploadFile);
    setUploadResult(null);
    setErrors([]);

    const fileExt = uploadFile.name.split('.').pop().toLowerCase();

    if (fileExt === 'csv') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n').filter(line => line.trim());

        if (lines.length < 2) {
          setErrors(['Il file sembra vuoto o non contiene righe di dati']);
          return;
        }

        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());

        // Parse first 10 rows for preview
        const previewRows = [];
        for (let i = 1; i < Math.min(lines.length, 11); i++) {
          const values = lines[i].split(',');
          const row = {};
          headers.forEach((h, idx) => {
            row[h] = values[idx]?.trim() || '';
          });
          previewRows.push(row);
        }

        setPreview({
          headers,
          rows: previewRows,
          totalRows: lines.length - 1,
        });
      };
      reader.readAsText(uploadFile);
    } else {
      setPreview({
        headers: ['File Excel — anteprima disponibile dopo il caricamento'],
        rows: [],
        totalRows: 'Sconosciuto (file Excel)',
        isExcel: true,
      });
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
  });

  const handleUpload = async (confirmDuplicate = false, skipDuplicateRows = false) => {
    if (!file || !datasetName) {
      toast.error('Inserisci un nome per il dataset');
      return;
    }

    setUploading(true);
    try {
      const resp = await datasetsAPI.upload(file, datasetName, datasetType, confirmDuplicate, skipDuplicateRows);
      toast.success('Dataset caricato con successo!');
      setUploadResult(resp.data);
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      // 409 duplicate found → show confirmation dialog
      if (status === 409 && detail?.status === 'duplicate_found') {
        setDuplicateData(detail);
        setDuplicateDialogOpen(true);
        return;
      }

      // 422 with needs_column_mapping → show mapping dialog
      if (status === 422 && detail?.status === 'needs_column_mapping') {
        setMappingData(detail);
        setMappingDialogOpen(true);
        return;
      }

      // v5.8 / Onda 9.Y.0.2 (Step E) — paywall (cashflow_monitor.data_rows
      // QUOTA_EXCEEDED on dataset upload) gestita dall axios interceptor.
      // Skip generic toasts to keep paywall the single visible modal.
      if (isPaywallHandled(error)) {
        return;
      }

      // Other errors
      if (typeof detail === 'string') {
        toast.error(detail);
        setErrors([detail]);
      } else if (detail?.errors) {
        setErrors(detail.errors);
        toast.error('Errore nel parsing del file');
      } else {
        toast.error('Errore durante il caricamento');
      }
    } finally {
      setUploading(false);
    }
  };

  // Pending mapping info (needed if 409 comes from uploadWithMapping)
  const [pendingMapping, setPendingMapping] = useState(null);

  const handleDuplicateConfirm = (skipDuplicateRows = false) => {
    setDuplicateDialogOpen(false);
    setDuplicateData(null);
    if (pendingMapping) {
      // Duplicate came from the mapping flow → re-call uploadWithMapping with confirmDuplicate
      const { tempId, mapping, saveMapping } = pendingMapping;
      setPendingMapping(null);
      doMappingUpload(tempId, mapping, saveMapping, true, skipDuplicateRows);
    } else {
      // Duplicate came from the direct upload flow
      handleUpload(true, skipDuplicateRows);
    }
  };

  const doMappingUpload = async (tempId, mapping, saveMapping, confirmDuplicate = false, skipDuplicateRows = false) => {
    setMappingLoading(true);
    try {
      const resp = await datasetsAPI.uploadWithMapping(tempId, mapping, saveMapping, confirmDuplicate, skipDuplicateRows);
      toast.success('Dataset caricato con successo!');
      setUploadResult(resp.data);
      setMappingDialogOpen(false);
      setMappingData(null);
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      // 409 duplicate found → show confirmation dialog
      if (status === 409 && detail?.status === 'duplicate_found') {
        setPendingMapping({ tempId, mapping, saveMapping });
        setMappingDialogOpen(false);
        setDuplicateData(detail);
        setDuplicateDialogOpen(true);
        return;
      }

      // v5.8 / Onda 9.Y.0.2 (Step E) — paywall handles 429 quota.
      if (isPaywallHandled(error)) {
        return;
      }

      toast.error(typeof detail === 'string' ? detail : 'Errore durante il caricamento');
    } finally {
      setMappingLoading(false);
    }
  };

  const handleMappingConfirm = async (mapping, saveMapping) => {
    if (!mappingData?.temp_upload_id) return;
    await doMappingUpload(mappingData.temp_upload_id, mapping, saveMapping, false);
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setErrors([]);
    setDatasetName('');
    setUploadResult(null);
    setMappingData(null);
  };

  // ── CSV examples ────────────────────────────────────────────────────────────

  const examples = {
    sales: `date,amount,category,description,channel
2026-03-01,1200,food_sales,Pranzo ristorante,dine_in
2026-03-02,900,food_sales,Pranzo ristorante,takeout
2026-03-03,1500,beverage_sales,Cena weekend,dine_in`,
    expenses: `date,amount,category,description,supplier
2026-03-01,300,ingredienti,Ingredienti pizza,Fornitore Food Co
2026-03-02,120,utenze,Elettricita,Utility Provider
2026-03-03,200,personale,Lavoratore temporaneo,Staff Agency`,
    purchases: `date,supplier_name,quantity,unit,unit_price,category,description
2026-03-01,Fornitore A,100,kg,5.50,materie_prime,Farina
2026-03-02,Fornitore B,50,lt,2.80,bevande,Latte
2026-03-03,Fornitore A,200,kg,3.20,materie_prime,Pomodori`,
    fixed_costs: `name,amount,frequency,start_date,end_date,category
Affitto locale,2500,mensile,2026-01-01,,affitto
Stipendio cuoco,1800,mensile,2026-01-01,,stipendio
Leasing forno,350,mensile,2026-01-01,2027-12-31,leasing`,
  };

  const downloadExample = (type) => {
    const content = examples[type] || examples.sales;
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}_esempio.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Column info per dataset type ──────────────────────────────────────────

  const columnInfo = {
    sales: {
      required: ['date', 'amount'],
      optional: ['category', 'description', 'channel'],
    },
    expenses: {
      required: ['date', 'amount'],
      optional: ['category', 'description', 'supplier'],
    },
    purchases: {
      required: ['date', 'supplier_name', 'quantity', 'unit_price'],
      optional: ['unit', 'category', 'description'],
    },
    fixed_costs: {
      required: ['name', 'amount', 'frequency', 'start_date'],
      optional: ['end_date', 'category'],
    },
  };

  const currentCols = columnInfo[datasetType] || columnInfo.sales;

  return (
    <AppLayout>
      <Header title="Carica Dati" subtitle="Importa i dati della tua azienda in formato CSV o Excel" />

      <div className="page-container section-gap animate-fade-in">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Upload Form */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Carica file CSV / Excel</CardTitle>
              <CardDescription>
                Seleziona il tipo di dati e carica il file. I dati verranno aggiunti a quelli esistenti.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Dataset Type Selection */}
              <div className="space-y-2">
                <Label>Tipo di dati</Label>
                <Select value={datasetType} onValueChange={setDatasetType}>
                  <SelectTrigger data-testid="dataset-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sales">Vendite / Entrate</SelectItem>
                    <SelectItem value="expenses">Spese / Uscite</SelectItem>
                    <SelectItem value="purchases">Acquisti Fornitori</SelectItem>
                    <SelectItem value="fixed_costs">Costi Fissi</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Dataset Name */}
              <div className="space-y-2">
                <Label htmlFor="dataset-name">Nome dataset</Label>
                <Input
                  id="dataset-name"
                  placeholder="es. Vendite Marzo 2026"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  data-testid="dataset-name-input"
                />
              </div>

              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-primary bg-primary/5' :
                  file ? 'border-green-500 bg-green-50' :
                  'border-border hover:border-primary/50'
                }`}
                data-testid="file-dropzone"
              >
                <input {...getInputProps()} />
                {file ? (
                  <div className="flex flex-col items-center">
                    <CheckCircle2 className="h-12 w-12 text-green-600 mb-4" />
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClear();
                      }}
                    >
                      <X className="h-4 w-4 mr-1" />
                      Rimuovi
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="font-medium">
                      {isDragActive ? 'Rilascia il file qui' : 'Trascina o clicca per caricare'}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Formati supportati: CSV, XLSX, XLS (max 50 MB)
                    </p>
                  </div>
                )}
              </div>

              {/* Errors */}
              {errors.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <div className="flex items-center gap-2 text-red-800 mb-2">
                    <AlertCircle className="h-4 w-4" />
                    <span className="font-medium">Errori</span>
                  </div>
                  <ul className="text-sm text-red-700 space-y-1">
                    {errors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                    {errors.length > 5 && (
                      <li>...e altri {errors.length - 5} errori</li>
                    )}
                  </ul>
                </div>
              )}

              {/* Upload result / Upload button */}
              {uploadResult ? (
                <UploadResultCard result={uploadResult} onReset={handleClear} />
              ) : (
                <Button
                  className="w-full"
                  disabled={!file || !datasetName || uploading}
                  onClick={handleUpload}
                  data-testid="upload-btn"
                >
                  {uploading ? 'Caricamento in corso...' : 'Carica dataset'}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Instructions */}
          <div className="space-y-6">
            <Card className="border border-border">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Formato richiesto</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Formati supportati</h4>
                  <div className="flex gap-2">
                    <Badge variant="secondary">CSV</Badge>
                    <Badge variant="secondary">XLSX</Badge>
                    <Badge variant="secondary">XLS</Badge>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Colonne obbligatorie</h4>
                  <div className="flex flex-wrap gap-2">
                    {currentCols.required.map((col) => (
                      <Badge key={col}>{col}</Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Colonne opzionali</h4>
                  <div className="flex flex-wrap gap-2">
                    {currentCols.optional.map((col) => (
                      <Badge key={col} variant="outline">{col}</Badge>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-border">
                  <h4 className="font-medium mb-2">Parsing intelligente</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>&#8226; Riconosce automaticamente varianti comuni dei nomi colonna</li>
                    <li>&#8226; Riconosce i formati data (AAAA-MM-GG, GG/MM/AAAA, ecc.)</li>
                    <li>&#8226; Gestisce simboli valuta e formati numerici EU/US</li>
                    <li>&#8226; Se le colonne non vengono riconosciute, ti guida nel mapping</li>
                    <li>&#8226; I nuovi dati si aggiungono a quelli esistenti (nessuna sovrascrittura)</li>
                  </ul>
                </div>

                <div className="pt-2 space-y-2">
                  <h4 className="font-medium">Scarica file di esempio</h4>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => downloadExample('sales')}>
                      <Download className="h-4 w-4 mr-2" />
                      Vendite
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => downloadExample('expenses')}>
                      <Download className="h-4 w-4 mr-2" />
                      Spese
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => downloadExample('purchases')}>
                      <Download className="h-4 w-4 mr-2" />
                      Acquisti
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => downloadExample('fixed_costs')}>
                      <Download className="h-4 w-4 mr-2" />
                      Costi Fissi
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Preview */}
            {preview && !preview.isExcel && preview.rows.length > 0 && (
              <Card className="border border-border">
                <CardHeader>
                  <CardTitle className="font-heading text-lg flex items-center gap-2">
                    <FileSpreadsheet className="h-5 w-5" />
                    Anteprima ({preview.totalRows} righe)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {preview.headers.map((h) => (
                            <TableHead key={h} className="font-code text-xs uppercase">
                              {h}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {preview.rows.map((row, i) => (
                          <TableRow key={i}>
                            {preview.headers.map((h) => (
                              <TableCell key={h} className="font-code text-sm">
                                {h === 'amount' ? formatCurrency(parseFloat(row[h]) || 0, orgCurrency) : row[h] || '-'}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {preview.totalRows > 10 && (
                    <p className="text-sm text-muted-foreground mt-2 text-center">
                      Mostrando le prime 10 di {preview.totalRows} righe
                    </p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

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
        }}
        onConfirm={handleDuplicateConfirm}
        duplicateData={duplicateData}
        loading={uploading}
      />
    </AppLayout>
  );
};

export default UploadPage;
