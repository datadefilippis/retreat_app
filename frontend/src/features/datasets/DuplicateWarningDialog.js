import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Rows3, Filter } from 'lucide-react';
import { formatDate } from '../../lib/utils';

/**
 * DuplicateWarningDialog — shown when a file upload detects duplicates
 * (either file-level, row-level, or both).
 *
 * Props:
 *   open           — boolean controlling dialog visibility
 *   onClose        — callback to close the dialog (cancel upload)
 *   onConfirm      — callback to proceed with the upload anyway
 *   duplicateData  — the 409 detail object:
 *     {
 *       status: "duplicate_found",
 *       duplicates: [{name, row_count, created_at, is_active}],  // file-level
 *       count: number,
 *       row_duplicates: { duplicate_row_count, total_new_rows, sample_duplicates },
 *       message: string,
 *     }
 *   loading        — boolean while the confirm request is in flight
 */
export const DuplicateWarningDialog = ({
  open,
  onClose,
  onConfirm,
  duplicateData,
  loading = false,
}) => {
  const {
    duplicates = [],
    row_duplicates = null,
    message = '',
  } = duplicateData || {};

  const hasFileDupes = duplicates.length > 0;
  const hasRowDupes = row_duplicates && row_duplicates.duplicate_row_count > 0;

  const MAX_FILE_DUPES_SHOWN = 3;
  const MAX_ROW_SAMPLES_SHOWN = 3;
  const visibleFileDupes = duplicates.slice(0, MAX_FILE_DUPES_SHOWN);
  const hiddenFileDupesCount = duplicates.length - visibleFileDupes.length;
  const sampleRows = row_duplicates?.sample_duplicates || [];
  const visibleSampleRows = sampleRows.slice(0, MAX_ROW_SAMPLES_SHOWN);
  const hiddenSampleRowsCount = sampleRows.length - visibleSampleRows.length;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Duplicati rilevati
          </DialogTitle>
          <DialogDescription>
            {message || 'Sono stati trovati potenziali duplicati.'}
          </DialogDescription>
        </DialogHeader>

        {/* File-level duplicates */}
        {hasFileDupes && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
              Caricamenti precedenti con lo stesso nome file
            </div>
            <div className="overflow-x-auto rounded border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Nome Dataset</TableHead>
                    <TableHead className="text-xs">Righe</TableHead>
                    <TableHead className="text-xs">Data Caricamento</TableHead>
                    <TableHead className="text-xs">Stato</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleFileDupes.map((d, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-sm font-medium">{d.name}</TableCell>
                      <TableCell className="text-sm">{(d.row_count || 0).toLocaleString()}</TableCell>
                      <TableCell className="text-sm">{formatDate(d.created_at)}</TableCell>
                      <TableCell>
                        {d.is_active ? (
                          <Badge className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Attivo
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">Inattivo</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {hiddenFileDupesCount > 0 && (
              <p className="text-xs text-muted-foreground">
                ...e altri {hiddenFileDupesCount}. In totale ci sono{' '}
                <span className="font-semibold">{duplicates.length} file duplicati</span> con lo stesso nome.
              </p>
            )}
            {hiddenFileDupesCount === 0 && duplicates.length > 1 && (
              <p className="text-xs text-muted-foreground">
                In totale ci sono <span className="font-semibold">{duplicates.length} file duplicati</span> con lo stesso nome.
              </p>
            )}
          </div>
        )}

        {/* Row-level duplicates */}
        {hasRowDupes && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Rows3 className="h-4 w-4 text-muted-foreground" />
              Righe duplicate trovate nei dati esistenti
            </div>
            <div className="rounded border border-amber-200 bg-amber-50 p-3 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-amber-800">Righe duplicate trovate:</span>
                <Badge className="bg-amber-100 text-amber-800 border-0">
                  {row_duplicates.duplicate_row_count} su {row_duplicates.total_new_rows} righe totali
                </Badge>
              </div>

              {/* Sample duplicate rows (max 3) */}
              {visibleSampleRows.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-amber-700 font-medium">
                    Esempi di righe duplicate (prime {visibleSampleRows.length} di {row_duplicates.duplicate_row_count}):
                  </p>
                  <div className="overflow-x-auto rounded border border-amber-200 bg-white">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {Object.keys(visibleSampleRows[0]).map((col) => (
                            <TableHead key={col} className="text-xs font-mono">{col}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {visibleSampleRows.map((row, i) => (
                          <TableRow key={i}>
                            {Object.values(row).map((val, j) => (
                              <TableCell key={j} className="text-xs font-mono">
                                {val != null ? String(val) : '-'}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {hiddenSampleRowsCount > 0 && (
                    <p className="text-xs text-amber-600">
                      ...e altre {hiddenSampleRowsCount} righe duplicate non mostrate.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Puoi scegliere di caricare tutti i dati (inclusi i duplicati) oppure
          di caricare solo le righe nuove, escludendo quelle già presenti.
        </p>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button
            variant="secondary"
            onClick={() => onConfirm(true)}
            disabled={loading}
            className="gap-1.5"
          >
            <Filter className="h-3.5 w-3.5" />
            {loading ? 'Caricamento...' : 'Carica senza duplicati'}
          </Button>
          <Button onClick={() => onConfirm(false)} disabled={loading}>
            {loading ? 'Caricamento...' : 'Carica tutto'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DuplicateWarningDialog;
