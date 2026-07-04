import React, { useState, useEffect } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Skeleton } from '../../components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { datasetsAPI } from '../../api';
import { formatDate } from '../../lib/utils';
import {
  FileSpreadsheet,
  Trash2,
  Eye,
  Upload,
  CheckCircle2,
  Download,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

// ── Dataset type metadata ───────────────────────────────────────────────────

const DATASET_TYPES = [
  {
    key: 'sales',
    title: 'Dataset Vendite',
    description: 'File di entrate/vendite caricati',
    emptyTitle: 'Nessun dato di vendita',
    emptyDesc: 'Carica i ricavi per generare KPI, grafici e alert automatici.',
    uploadLabel: 'Carica Vendite',
  },
  {
    key: 'expenses',
    title: 'Dataset Spese',
    description: 'File di spese/uscite caricati',
    emptyTitle: 'Nessun dato di spesa',
    emptyDesc: 'Carica le spese per calcolare il cashflow netto e identificare anomalie.',
    uploadLabel: 'Carica Spese',
  },
  {
    key: 'purchases',
    title: 'Dataset Acquisti',
    description: 'File di acquisti da fornitori caricati',
    emptyTitle: 'Nessun dato di acquisto',
    emptyDesc: 'Carica gli acquisti per monitorare i costi fornitori e ottimizzare le spese.',
    uploadLabel: 'Carica Acquisti',
  },
  {
    key: 'fixed_costs',
    title: 'Dataset Costi Fissi',
    description: 'File di costi fissi caricati',
    emptyTitle: 'Nessun costo fisso',
    emptyDesc: 'Carica i costi fissi per monitorare affitti, stipendi e abbonamenti ricorrenti.',
    uploadLabel: 'Carica Costi Fissi',
  },
];

const ITEMS_PER_PAGE = 5;


// ── Reusable dataset section component ──────────────────────────────────────

const DatasetSection = ({
  meta,
  datasets,
  loading,
  onPreview,
  onDownload,
  onDelete,
  onToggleActive,
  previewData,
  previewLoading,
}) => {
  const filtered = datasets.filter((d) => d.dataset_type === meta.key);
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when dataset count changes (e.g. after delete)
  useEffect(() => {
    setCurrentPage(1);
  }, [filtered.length]);

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginated = filtered.slice(startIdx, startIdx + ITEMS_PER_PAGE);

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle className="font-heading text-lg">{meta.title}</CardTitle>
        <CardDescription>{meta.description}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : filtered.length > 0 ? (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Righe</TableHead>
                  <TableHead>Data Caricamento</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginated.map((dataset) => (
                  <TableRow key={dataset.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                        {dataset.name}
                      </div>
                    </TableCell>
                    <TableCell>{dataset.row_count.toLocaleString()}</TableCell>
                    <TableCell>{formatDate(dataset.created_at)}</TableCell>
                    <TableCell>
                      <button
                        onClick={() => onToggleActive(dataset.id, dataset.is_active)}
                        className="cursor-pointer"
                        title={dataset.is_active ? 'Clicca per disattivare' : 'Clicca per attivare'}
                      >
                        {dataset.is_active ? (
                          <Badge className="bg-green-100 text-green-800 hover:bg-green-200 transition-colors">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Attivo
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="hover:bg-muted transition-colors">
                            Inattivo
                          </Badge>
                        )}
                      </button>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => onPreview(dataset.id)}
                              title="Anteprima"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-3xl">
                            <DialogHeader>
                              <DialogTitle>Anteprima: {dataset.name}</DialogTitle>
                            </DialogHeader>
                            {previewLoading ? (
                              <Skeleton className="h-64 w-full" />
                            ) : previewData ? (
                              <div className="overflow-x-auto">
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      {previewData.preview_rows.length > 0 &&
                                        Object.keys(previewData.preview_rows[0]).map((col) => (
                                          <TableHead key={col}>{col}</TableHead>
                                        ))}
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {previewData.preview_rows.map((row, i) => (
                                      <TableRow key={i}>
                                        {Object.values(row).map((val, j) => (
                                          <TableCell key={j}>{val != null ? String(val) : '-'}</TableCell>
                                        ))}
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                                <p className="text-sm text-muted-foreground mt-2">
                                  Mostrando {previewData.preview_rows.length} di {previewData.total_rows} righe
                                </p>
                              </div>
                            ) : null}
                          </DialogContent>
                        </Dialog>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onDownload(dataset.id, dataset.name)}
                          title="Scarica file originale"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onDelete(dataset.id)}
                          title="Elimina dataset e record associati"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <p className="text-sm text-muted-foreground">
                  Pagina {currentPage} di {totalPages} · {filtered.length} file totali
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage((p) => p - 1)}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Precedente
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage((p) => p + 1)}
                  >
                    Successivo
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-center max-w-sm mx-auto gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
              <FileSpreadsheet className="h-7 w-7 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-semibold">{meta.emptyTitle}</p>
              <p className="text-sm text-muted-foreground mt-1">{meta.emptyDesc}</p>
            </div>
            <Link to={`/modules/cashflow/data/${meta.key}`}>
              <Button variant="outline" size="sm" className="gap-2 mt-1">
                <Upload className="h-3.5 w-3.5" />
                {meta.uploadLabel}
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
};


// ── Main component ──────────────────────────────────────────────────────────

export const DatasetsPage = () => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const response = await datasetsAPI.list();
      setDatasets(response.data);
    } catch (error) {
      toast.error('Errore nel caricamento dei dataset');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handlePreview = async (datasetId) => {
    setPreviewLoading(true);
    try {
      const response = await datasetsAPI.preview(datasetId);
      setPreviewData(response.data);
    } catch (error) {
      toast.error('Errore nel caricamento dell\'anteprima');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDelete = async (datasetId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo dataset? Tutti i record associati verranno rimossi.')) return;

    try {
      await datasetsAPI.delete(datasetId);
      toast.success('Dataset eliminato con successo');
      fetchDatasets();
    } catch (error) {
      toast.error('Errore nell\'eliminazione del dataset');
    }
  };

  const handleToggleActive = async (datasetId, currentIsActive) => {
    try {
      const resp = await datasetsAPI.toggleActive(datasetId);
      const newStatus = resp.data.is_active;
      // Optimistic update: update datasets list locally
      setDatasets((prev) =>
        prev.map((d) => (d.id === datasetId ? { ...d, is_active: newStatus } : d))
      );
      toast.success(newStatus ? 'Dataset attivato' : 'Dataset disattivato');
    } catch (error) {
      toast.error('Errore nel cambio di stato del dataset');
    }
  };

  const handleDownload = async (datasetId, datasetName) => {
    try {
      const token = localStorage.getItem('token');
      const baseUrl = window.location.origin;
      const downloadUrl = `${baseUrl}/api/datasets/${datasetId}/download`;

      const response = await fetch(downloadUrl, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = datasetName || 'dataset';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Download avviato');
    } catch (error) {
      toast.error('Errore nel download del dataset');
    }
  };

  return (
    <AppLayout>
      <Header title="Gestione File" subtitle="Visualizza, scarica o elimina i file caricati">
        <Link to="/modules/cashflow/data">
          <Button data-testid="upload-new-btn">
            <Upload className="h-4 w-4 mr-2" />
            Carica Nuovo File
          </Button>
        </Link>
      </Header>

      <div className="page-container section-gap animate-fade-in">
        {DATASET_TYPES.map((meta) => (
          <DatasetSection
            key={meta.key}
            meta={meta}
            datasets={datasets}
            loading={loading}
            onPreview={handlePreview}
            onDownload={handleDownload}
            onDelete={handleDelete}
            onToggleActive={handleToggleActive}
            previewData={previewData}
            previewLoading={previewLoading}
          />
        ))}
      </div>
    </AppLayout>
  );
};

export default DatasetsPage;
