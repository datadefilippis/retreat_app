import React, { useState, useMemo } from 'react';
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
import { Label } from '../../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';

/**
 * ColumnMappingDialog — interactive column mapping modal.
 *
 * Shown when an upload returns 422 with status='needs_column_mapping'.
 * The user maps unrecognized file columns to target fields.
 *
 * Props:
 *   open              — boolean controlling dialog visibility
 *   onClose           — callback to close the dialog
 *   onConfirm         — (mapping: {fileCol: targetField}, saveMapping: boolean) => void
 *   mappingData       — the 422 detail object with:
 *     recognized_columns  — { fileCol: targetField }
 *     unmapped_columns    — [fileCol, ...]
 *     missing_required    — [targetField, ...]
 *     target_fields       — { fieldName: { label, required } }
 *     preview_rows        — [{ col: val, ... }, ...]
 *     all_file_columns    — [colName, ...]
 *   loading            — boolean while the confirm request is in flight
 */
export const ColumnMappingDialog = ({
  open,
  onClose,
  onConfirm,
  mappingData,
  loading = false,
}) => {
  // Editable mappings: initialized from auto-mapped + user overrides
  // Key: fileCol → selectedTargetField (or '_skip')
  const [editableMappings, setEditableMappings] = useState({});
  const [saveMapping, setSaveMapping] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const {
    recognized_columns = {},
    unmapped_columns = [],
    missing_required = [],
    target_fields = {},
    preview_rows = [],
    all_file_columns = [],
  } = mappingData || {};

  // Initialize editable mappings from recognized columns (once)
  React.useEffect(() => {
    if (mappingData && !initialized) {
      const initial = {};
      // Pre-fill auto-mapped columns so they appear in dropdowns
      for (const [fileCol, target] of Object.entries(recognized_columns)) {
        initial[fileCol] = target;
      }
      setEditableMappings(initial);
      setInitialized(true);
    }
  }, [mappingData, recognized_columns, initialized]);

  // All columns that need mapping UI: auto-mapped (editable) + unmapped
  const allMappableColumns = useMemo(() => {
    const autoMapped = Object.keys(recognized_columns);
    // Unmapped columns that aren't already in recognized
    const unmappedOnly = unmapped_columns.filter((c) => !recognized_columns[c]);
    return [...autoMapped, ...unmappedOnly];
  }, [recognized_columns, unmapped_columns]);

  // Determine which target fields are currently taken
  const takenTargets = useMemo(() => {
    const taken = new Set();
    Object.values(editableMappings).forEach((t) => {
      if (t && t !== '_skip') taken.add(t);
    });
    return taken;
  }, [editableMappings]);

  // Check if all required fields are now covered
  const coveredRequired = useMemo(() => {
    const allMappedTargets = new Set(
      Object.values(editableMappings).filter((t) => t && t !== '_skip')
    );
    return missing_required.every((req) => allMappedTargets.has(req));
  }, [editableMappings, missing_required]);

  const handleMappingChange = (fileCol, targetField) => {
    setEditableMappings((prev) => ({
      ...prev,
      [fileCol]: targetField,
    }));
  };

  const handleConfirm = () => {
    // Build final mapping from all editable mappings (exclude _skip and empty)
    const finalMapping = {};
    for (const [fileCol, target] of Object.entries(editableMappings)) {
      if (target && target !== '_skip') {
        finalMapping[fileCol] = target;
      }
    }
    onConfirm(finalMapping, saveMapping);
  };

  // Available target fields for a given file column (exclude already-taken ones,
  // except the one currently selected for this column)
  const getAvailableTargets = (fileCol) => {
    const currentSelection = editableMappings[fileCol];
    return Object.entries(target_fields).filter(
      ([fieldName]) =>
        !takenTargets.has(fieldName) || fieldName === currentSelection
    );
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-lg">
            Mappatura Colonne
          </DialogTitle>
          <DialogDescription>
            Alcune colonne del file non sono state riconosciute automaticamente.
            Seleziona a quale campo corrisponde ciascuna colonna.
          </DialogDescription>
        </DialogHeader>

        {/* Preview rows */}
        {preview_rows.length > 0 && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Anteprima dati (prime 3 righe)</Label>
            <div className="overflow-x-auto rounded border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {all_file_columns.map((col) => (
                      <TableHead key={col} className="text-xs font-mono whitespace-nowrap">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview_rows.map((row, i) => (
                    <TableRow key={i}>
                      {all_file_columns.map((col) => (
                        <TableCell key={col} className="text-xs font-mono whitespace-nowrap">
                          {row[col] || '-'}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* Column mapping — all columns are editable (auto-mapped + unmapped) */}
        {allMappableColumns.length > 0 && (
          <div className="space-y-3">
            <Label className="text-sm font-medium">
              Mappatura colonne
              {missing_required.length > 0 && !coveredRequired && (
                <span className="text-red-600 ml-2">
                  (campi obbligatori mancanti: {missing_required.filter((f) => !Object.values(editableMappings).includes(f)).map((f) => target_fields[f]?.label || f).join(', ')})
                </span>
              )}
            </Label>

            {allMappableColumns.map((fileCol) => {
              const isAutoMapped = fileCol in recognized_columns;
              return (
                <div key={fileCol} className="flex items-center gap-3">
                  <div className="min-w-[140px]">
                    <Badge variant={isAutoMapped ? 'secondary' : 'outline'} className="font-mono text-xs gap-1">
                      {isAutoMapped && <CheckCircle2 className="h-3 w-3 text-green-600" />}
                      {fileCol}
                    </Badge>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  <Select
                    value={editableMappings[fileCol] || ''}
                    onValueChange={(v) => handleMappingChange(fileCol, v)}
                  >
                    <SelectTrigger className="w-[220px]">
                      <SelectValue placeholder="Seleziona campo..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_skip">
                        <span className="text-muted-foreground">-- Ignora colonna --</span>
                      </SelectItem>
                      {getAvailableTargets(fileCol).map(([fieldName, meta]) => (
                        <SelectItem key={fieldName} value={fieldName}>
                          <span>{meta.label}</span>
                          {meta.required && <span className="text-red-500 ml-1">*</span>}
                          {meta.help && <span className="text-muted-foreground ml-1 text-xs">— {meta.help}</span>}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Show sample value */}
                  {preview_rows.length > 0 && (
                    <span className="text-xs text-muted-foreground font-mono truncate max-w-[150px]">
                      es: {preview_rows[0][fileCol] || '-'}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Validation status */}
        <div className="flex items-center gap-2 text-sm">
          {coveredRequired ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-green-700">Tutti i campi obbligatori sono mappati</span>
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <span className="text-amber-700">
                Mappa i campi obbligatori per continuare
              </span>
            </>
          )}
        </div>

        {/* Save mapping checkbox */}
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={saveMapping}
            onChange={(e) => setSaveMapping(e.target.checked)}
            className="rounded border-border"
          />
          <span className="text-muted-foreground">
            Salva mappatura per i prossimi caricamenti
          </span>
        </label>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!coveredRequired || loading}
          >
            {loading ? 'Caricamento...' : 'Conferma e Carica'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ColumnMappingDialog;
