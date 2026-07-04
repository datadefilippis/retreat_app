/**
 * ColumnMappingsPage — Dataset Column Mappings UI
 *
 * Allows users to:
 *  1. Select a dataset for Vendite / Spese / Acquisti
 *  2. See each raw column with its detected type and sample values
 *  3. Assign (or clear) a canonical target field via a select
 *  4. Save all changes in a single batch call
 *
 * Existing active mappings for a dataset_type are pre-loaded and used
 * to initialise the selects; columns without existing mappings are
 * pre-filled from the profile's `suggested_mapping` when available.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { datasetsAPI, columnMappingsAPI } from '../../api';
import { Save, Columns, Info, Trash2 } from 'lucide-react';
import { toast } from 'sonner';


// ── Constants ─────────────────────────────────────────────────────────────────

/** Canonical target fields available for each dataset type.
 *  Aligned with backend _TARGET_FIELDS in dataset_service.py. */
const CANONICAL_FIELDS = {
  sales: [
    { value: 'date',            label: 'Data' },
    { value: 'amount',          label: 'Importo' },
    { value: 'category',        label: 'Categoria' },
    { value: 'description',     label: 'Descrizione' },
    { value: 'channel',         label: 'Canale' },
    { value: 'due_date',        label: 'Data Scadenza' },
    { value: 'payment_status',  label: 'Stato Pagamento' },
  ],
  expenses: [
    { value: 'date',            label: 'Data' },
    { value: 'amount',          label: 'Importo' },
    { value: 'category',        label: 'Categoria' },
    { value: 'description',     label: 'Descrizione' },
    { value: 'supplier',        label: 'Fornitore' },
    { value: 'due_date',        label: 'Data Scadenza' },
    { value: 'payment_status',  label: 'Stato Pagamento' },
    { value: 'is_paid',         label: 'Pagato' },
  ],
  purchases: [
    { value: 'date',            label: 'Data' },
    { value: 'supplier_name',   label: 'Nome Fornitore' },
    { value: 'total_price',     label: 'Totale' },
    { value: 'quantity',        label: 'Quantità' },
    { value: 'unit_price',      label: 'Prezzo Unitario' },
    { value: 'unit',            label: 'Unità di Misura' },
    { value: 'iva',             label: 'IVA %' },
    { value: 'total_with_iva',  label: 'Totale con IVA' },
    { value: 'category',        label: 'Prodotto' },
    { value: 'category_macro',  label: 'Categoria' },
    { value: 'description',     label: 'Descrizione' },
    { value: 'invoice_number',  label: 'Numero Fattura' },
    { value: 'due_date',        label: 'Data Scadenza' },
    { value: 'payment_status',  label: 'Stato Pagamento' },
  ],
  fixed_costs: [
    { value: 'name',            label: 'Nome Costo' },
    { value: 'amount',          label: 'Importo' },
    { value: 'frequency',       label: 'Frequenza' },
    { value: 'start_date',      label: 'Data Inizio' },
    { value: 'end_date',        label: 'Data Fine' },
    { value: 'category',        label: 'Categoria' },
    { value: 'description',     label: 'Descrizione' },
  ],
};

const TABS = [
  { key: 'sales',       label: 'Vendite' },
  { key: 'expenses',    label: 'Spese' },
  { key: 'purchases',   label: 'Acquisti' },
  { key: 'fixed_costs', label: 'Costi Fissi' },
];

/** Human-readable label for auto-detected column types. */
const TYPE_LABELS = {
  date:   'Data',
  amount: 'Numero',
  text:   'Testo',
  number: 'Numero',
};


// ── Helper ────────────────────────────────────────────────────────────────────

/** Build the initial source_column → target_field map from existing mappings + suggestions. */
function buildLocalMappings(profileColumns, existingMappings) {
  const existing = {};
  for (const m of existingMappings) {
    existing[m.source_column] = m.target_field;
  }

  const result = {};
  for (const col of profileColumns) {
    if (existing[col.column_name] !== undefined) {
      result[col.column_name] = existing[col.column_name];
    } else if (col.suggested_mapping) {
      result[col.column_name] = col.suggested_mapping;
    } else {
      result[col.column_name] = '';
    }
  }
  return result;
}


// ── Sub-component: mapping table ─────────────────────────────────────────────

const MappingTable = ({ profile, localMappings, canonicalFields, onChange }) => {
  if (!profile) return null;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-56">Colonna nel file</TableHead>
          <TableHead className="w-24">Tipo rilevato</TableHead>
          <TableHead className="w-64">Valori campione</TableHead>
          <TableHead>Campo canonico</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {profile.columns.map((col) => (
          <TableRow key={col.column_name}>
            <TableCell className="font-mono text-sm font-medium">
              {col.column_name}
            </TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">
                {TYPE_LABELS[col.detected_type] ?? col.detected_type}
              </Badge>
            </TableCell>
            <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
              {col.sample_values?.slice(0, 3).join(', ') || '—'}
            </TableCell>
            <TableCell>
              <Select
                value={localMappings[col.column_name] ?? ''}
                onValueChange={(val) => onChange(col.column_name, val)}
              >
                <SelectTrigger className="w-52">
                  <SelectValue placeholder="— non mappare —" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">— non mappare —</SelectItem>
                  {canonicalFields.map((f) => (
                    <SelectItem key={f.value} value={f.value}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};


// ── Sub-component: existing mappings summary ──────────────────────────────────

const ExistingMappingsList = ({ mappings, canonicalFields, onDelete }) => {
  if (!mappings || mappings.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-2">
        Nessun mapping attivo per questo tipo di dataset.
      </p>
    );
  }

  const labelFor = (value) =>
    canonicalFields.find((f) => f.value === value)?.label ?? value;

  return (
    <div className="divide-y divide-border">
      {mappings.map((m) => (
        <div key={m.id} className="flex items-center justify-between py-2 text-sm">
          <span>
            <span className="font-mono text-muted-foreground">{m.source_column}</span>
            <span className="mx-2 text-muted-foreground">→</span>
            <span className="font-medium">{labelFor(m.target_field)}</span>
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-red-600"
            onClick={() => onDelete(m.id)}
            title="Rimuovi mapping"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );
};


// ── Tab panel ─────────────────────────────────────────────────────────────────

const DatasetTypeTab = ({ datasetType }) => {
  const canonicalFields = CANONICAL_FIELDS[datasetType];

  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [profile, setProfile] = useState(null);
  const [existingMappings, setExistingMappings] = useState([]);
  const [localMappings, setLocalMappings] = useState({});

  const [datasetsLoading, setDatasetsLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load datasets and existing mappings for this type on mount
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setDatasetsLoading(true);
      try {
        const [dsRes, mapRes] = await Promise.all([
          datasetsAPI.list(),
          columnMappingsAPI.list(datasetType),
        ]);
        if (cancelled) return;
        const filtered = (dsRes.data ?? []).filter(
          (d) => d.dataset_type === datasetType
        );
        setDatasets(filtered);
        setExistingMappings(mapRes.data ?? []);
        // Auto-select first dataset if available
        if (filtered.length > 0) {
          setSelectedDatasetId(filtered[0].id);
        }
      } catch {
        if (!cancelled) toast.error('Impossibile caricare i dataset');
      } finally {
        if (!cancelled) setDatasetsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [datasetType]);

  // Load column profile when dataset selection changes
  useEffect(() => {
    if (!selectedDatasetId) {
      setProfile(null);
      setLocalMappings({});
      return;
    }

    let cancelled = false;
    const loadProfile = async () => {
      setProfileLoading(true);
      try {
        const res = await columnMappingsAPI.getProfile(selectedDatasetId);
        if (cancelled) return;
        const prof = res.data;
        setProfile(prof);
        setLocalMappings(buildLocalMappings(prof.columns, existingMappings));
      } catch {
        if (!cancelled) {
          setProfile(null);
          setLocalMappings({});
          toast.error('Profilo colonne non disponibile per questo dataset');
        }
      } finally {
        if (!cancelled) setProfileLoading(false);
      }
    };
    loadProfile();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId]);

  const handleMappingChange = useCallback((sourceColumn, targetField) => {
    setLocalMappings((prev) => ({ ...prev, [sourceColumn]: targetField }));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const mappingsPayload = Object.entries(localMappings).map(
        ([source_column, target_field]) => ({ source_column, target_field })
      );
      await columnMappingsAPI.saveBatch({
        dataset_type: datasetType,
        mappings: mappingsPayload,
      });
      // Refresh existing mappings list
      const mapRes = await columnMappingsAPI.list(datasetType);
      setExistingMappings(mapRes.data ?? []);
      toast.success('Mapping salvati');
    } catch {
      toast.error('Salvataggio fallito');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMapping = async (mappingId) => {
    try {
      await columnMappingsAPI.deactivate(mappingId);
      setExistingMappings((prev) => prev.filter((m) => m.id !== mappingId));
      toast.success('Mapping rimosso');
    } catch {
      toast.error('Rimozione fallita');
    }
  };

  // Count columns that have been assigned a target
  const mappedCount = Object.values(localMappings).filter(Boolean).length;
  const totalCount = profile?.columns?.length ?? 0;

  return (
    <div className="mt-6 space-y-6">
      {/* Dataset selector */}
      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-base">Seleziona Dataset</CardTitle>
          <CardDescription>
            Scegli il file da cui leggere le colonne rilevate
          </CardDescription>
        </CardHeader>
        <CardContent>
          {datasetsLoading ? (
            <Skeleton className="h-10 w-80" />
          ) : datasets.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun dataset di tipo <strong>{datasetType}</strong> caricato.
            </p>
          ) : (
            <Select
              value={selectedDatasetId}
              onValueChange={setSelectedDatasetId}
            >
              <SelectTrigger className="w-80" data-testid={`dataset-select-${datasetType}`}>
                <SelectValue placeholder="Scegli un dataset…" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </CardContent>
      </Card>

      {/* Column mapping table */}
      {selectedDatasetId && (
        <Card className="border border-border">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="font-heading text-base flex items-center gap-2">
                  <Columns className="h-4 w-4 text-muted-foreground" />
                  Mappatura Colonne
                </CardTitle>
                <CardDescription className="mt-1">
                  Associa ogni colonna del file al campo canonico corrispondente
                </CardDescription>
              </div>
              {!profileLoading && profile && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">
                    {mappedCount}/{totalCount} mappati
                  </span>
                  <Button
                    onClick={handleSave}
                    disabled={saving || mappedCount === 0}
                    data-testid={`save-mappings-${datasetType}`}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saving ? 'Salvataggio…' : 'Salva Mapping'}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {profileLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : profile ? (
              <MappingTable
                profile={profile}
                localMappings={localMappings}
                canonicalFields={canonicalFields}
                onChange={handleMappingChange}
              />
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Info className="h-4 w-4 flex-shrink-0" />
                <span>
                  Nessun profilo disponibile. Il profilo viene generato automaticamente
                  al momento del caricamento del file.
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Active mappings summary */}
      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-base">Mapping Attivi</CardTitle>
          <CardDescription>
            Regole di mapping attualmente salvate per <strong>{datasetType}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ExistingMappingsList
            mappings={existingMappings}
            canonicalFields={canonicalFields}
            onDelete={handleDeleteMapping}
          />
        </CardContent>
      </Card>
    </div>
  );
};


// ── Main page ─────────────────────────────────────────────────────────────────

export const ColumnMappingsPage = () => {
  const [activeTab, setActiveTab] = useState('sales');

  return (
    <AppLayout>
      <Header
        title="Column Mappings"
        subtitle="Definisci come le colonne dei tuoi file vengono interpretate"
      />

      <div className="page-container animate-fade-in">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            {TABS.map((tab) => (
              <TabsTrigger
                key={tab.key}
                value={tab.key}
                data-testid={`tab-${tab.key}`}
              >
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {TABS.map((tab) => (
            <TabsContent key={tab.key} value={tab.key}>
              {/* Mount/unmount to reset state when switching tabs */}
              {activeTab === tab.key && (
                <DatasetTypeTab datasetType={tab.key} />
              )}
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </AppLayout>
  );
};

export default ColumnMappingsPage;
