/**
 * ValidationRulesPage — Data Validation Rules management UI
 *
 * Allows admins to:
 *  1. View all validation rules for each dataset type
 *  2. Create new rules with type-specific value inputs
 *  3. Toggle active/inactive status per rule
 *  4. Delete rules permanently
 *
 * Rules created here are applied on the next file upload by the
 * dataset_service validation engine (v2.2).
 */
import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { validationRulesAPI } from '../../api';
import { ShieldCheck, Plus, Trash2, ToggleLeft, ToggleRight, X } from 'lucide-react';
import { toast } from 'sonner';


// ── Constants ─────────────────────────────────────────────────────────────────

const TABS = [
  { key: 'sales',     label: 'Vendite' },
  { key: 'expenses',  label: 'Spese' },
  { key: 'purchases', label: 'Acquisti' },
];

const CANONICAL_FIELDS = {
  sales:     ['date', 'amount', 'category', 'description', 'customer_name', 'customer_id'],
  expenses:  ['date', 'amount', 'category', 'description', 'vendor_name', 'vendor_id'],
  purchases: ['date', 'amount', 'category', 'description', 'product_name', 'quantity', 'vendor_name'],
};

const RULE_TYPES = [
  { value: 'required',           label: 'Obbligatorio',          needsValue: false },
  { value: 'min_value',          label: 'Valore Minimo',         needsValue: true },
  { value: 'max_value',          label: 'Valore Massimo',        needsValue: true },
  { value: 'date_range',         label: 'Intervallo Date',       needsValue: true },
  { value: 'category_whitelist', label: 'Categorie Consentite',  needsValue: true },
];

const RULE_TYPE_LABELS = Object.fromEntries(RULE_TYPES.map((r) => [r.value, r.label]));

const EMPTY_FORM = {
  field_name: '',
  rule_type: 'required',
  error_message: '',
  num_value: '',
  date_start: '',
  date_end: '',
  list_value: '',
};


// ── Helpers ───────────────────────────────────────────────────────────────────

/** Convert form state to API rule_value based on rule_type. */
function buildRuleValue(form) {
  switch (form.rule_type) {
    case 'required':
      return null;
    case 'min_value':
    case 'max_value': {
      const n = parseFloat(form.num_value);
      return isNaN(n) ? null : n;
    }
    case 'date_range':
      return {
        start: form.date_start || null,
        end: form.date_end || null,
      };
    case 'category_whitelist':
      return form.list_value
        .split(/[\n,]/)
        .map((s) => s.trim())
        .filter(Boolean);
    default:
      return null;
  }
}

/** Render rule_value as a concise human-readable string. */
function renderRuleValue(rule) {
  const v = rule.rule_value;
  switch (rule.rule_type) {
    case 'required':
      return '—';
    case 'min_value':
      return `≥ ${v}`;
    case 'max_value':
      return `≤ ${v}`;
    case 'date_range': {
      const bounds = v || {};
      const parts = [bounds.start, bounds.end].filter(Boolean);
      return parts.join(' → ') || '—';
    }
    case 'category_whitelist': {
      const list = Array.isArray(v) ? v : [];
      if (!list.length) return '—';
      const preview = list.slice(0, 3).join(', ');
      return list.length > 3 ? `${preview} … (+${list.length - 3})` : preview;
    }
    default:
      return v !== null && v !== undefined ? String(v) : '—';
  }
}

/** Validate form before submit. Returns error message or null. */
function validateForm(form) {
  if (!form.field_name) return 'Seleziona un campo';
  if (form.rule_type === 'min_value' || form.rule_type === 'max_value') {
    if (!form.num_value || isNaN(parseFloat(form.num_value))) return 'Inserisci un valore numerico valido';
  }
  if (form.rule_type === 'date_range') {
    if (!form.date_start && !form.date_end) return 'Inserisci almeno una data (inizio o fine)';
  }
  if (form.rule_type === 'category_whitelist') {
    const list = form.list_value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
    if (!list.length) return 'Inserisci almeno una categoria';
  }
  return null;
}


// ── Rule value input (dynamic by rule_type) ───────────────────────────────────

const RuleValueInput = ({ ruleType, form, onChange }) => {
  if (ruleType === 'required') {
    return <span className="text-sm text-muted-foreground">Nessun valore necessario</span>;
  }
  if (ruleType === 'min_value' || ruleType === 'max_value') {
    return (
      <Input
        type="number"
        placeholder={ruleType === 'min_value' ? 'Valore minimo' : 'Valore massimo'}
        value={form.num_value}
        onChange={(e) => onChange('num_value', e.target.value)}
        className="w-40"
      />
    );
  }
  if (ruleType === 'date_range') {
    return (
      <div className="flex items-center gap-2">
        <Input
          type="date"
          placeholder="Data inizio"
          value={form.date_start}
          onChange={(e) => onChange('date_start', e.target.value)}
          className="w-40"
        />
        <span className="text-muted-foreground text-sm">→</span>
        <Input
          type="date"
          placeholder="Data fine"
          value={form.date_end}
          onChange={(e) => onChange('date_end', e.target.value)}
          className="w-40"
        />
      </div>
    );
  }
  if (ruleType === 'category_whitelist') {
    return (
      <Textarea
        placeholder={"Una categoria per riga (o separata da virgola)\nes. vendita, abbonamento, servizio"}
        value={form.list_value}
        onChange={(e) => onChange('list_value', e.target.value)}
        className="h-24 w-72 text-sm"
      />
    );
  }
  return null;
};


// ── Add rule form ─────────────────────────────────────────────────────────────

const AddRuleForm = ({ datasetType, onSaved, onCancel }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const set = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Reset value fields when rule_type changes
  const handleRuleTypeChange = (value) => {
    setForm((prev) => ({
      ...prev,
      rule_type: value,
      num_value: '',
      date_start: '',
      date_end: '',
      list_value: '',
    }));
  };

  const handleSubmit = async () => {
    const err = validateForm(form);
    if (err) { toast.error(err); return; }

    setSaving(true);
    try {
      await validationRulesAPI.create({
        dataset_type: datasetType,
        field_name: form.field_name,
        rule_type: form.rule_type,
        rule_value: buildRuleValue(form),
        error_message: form.error_message.trim() || null,
        is_active: true,
      });
      toast.success('Regola creata');
      onSaved();
    } catch {
      toast.error('Creazione fallita');
    } finally {
      setSaving(false);
    }
  };

  const fields = CANONICAL_FIELDS[datasetType] || [];

  return (
    <Card className="border border-dashed border-border bg-muted/30">
      <CardHeader className="pb-3">
        <CardTitle className="font-heading text-sm flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Nuova Regola
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Row 1: field + rule type */}
        <div className="flex flex-wrap gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground font-medium">Campo</label>
            <Select value={form.field_name} onValueChange={(v) => set('field_name', v)}>
              <SelectTrigger className="w-44" data-testid="form-field-name">
                <SelectValue placeholder="Seleziona campo…" />
              </SelectTrigger>
              <SelectContent>
                {fields.map((f) => (
                  <SelectItem key={f} value={f}>{f}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground font-medium">Tipo Regola</label>
            <Select value={form.rule_type} onValueChange={handleRuleTypeChange}>
              <SelectTrigger className="w-52" data-testid="form-rule-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RULE_TYPES.map((rt) => (
                  <SelectItem key={rt.value} value={rt.value}>{rt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Row 2: rule value (dynamic) */}
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground font-medium">Valore</label>
          <RuleValueInput ruleType={form.rule_type} form={form} onChange={set} />
        </div>

        {/* Row 3: optional custom error message */}
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground font-medium">
            Messaggio errore personalizzato <span className="text-muted-foreground font-normal">(opzionale)</span>
          </label>
          <Input
            placeholder="es. L'importo deve essere positivo"
            value={form.error_message}
            onChange={(e) => set('error_message', e.target.value)}
            className="w-96"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <Button onClick={handleSubmit} disabled={saving} data-testid="save-rule-btn">
            {saving ? 'Salvataggio…' : 'Salva Regola'}
          </Button>
          <Button variant="ghost" onClick={onCancel} disabled={saving}>
            <X className="h-4 w-4 mr-1" />
            Annulla
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};


// ── Rules table ───────────────────────────────────────────────────────────────

const RulesTable = ({ rules, onToggle, onDelete }) => {
  if (!rules.length) {
    return (
      <div className="text-center py-10 text-muted-foreground">
        <ShieldCheck className="h-10 w-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Nessuna regola configurata per questo tipo di dataset.</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-36">Campo</TableHead>
          <TableHead className="w-44">Tipo</TableHead>
          <TableHead>Valore</TableHead>
          <TableHead className="w-56">Messaggio Errore</TableHead>
          <TableHead className="w-20 text-center">Stato</TableHead>
          <TableHead className="w-20 text-right">Azioni</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rules.map((rule) => (
          <TableRow key={rule.id} className={!rule.is_active ? 'opacity-50' : ''}>
            <TableCell className="font-mono text-sm font-medium">{rule.field_name}</TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">
                {RULE_TYPE_LABELS[rule.rule_type] ?? rule.rule_type}
              </Badge>
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {renderRuleValue(rule)}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
              {rule.error_message || '—'}
            </TableCell>
            <TableCell className="text-center">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title={rule.is_active ? 'Disattiva' : 'Attiva'}
                onClick={() => onToggle(rule)}
                data-testid={`toggle-${rule.id}`}
              >
                {rule.is_active
                  ? <ToggleRight className="h-5 w-5 text-green-600" />
                  : <ToggleLeft className="h-5 w-5 text-muted-foreground" />
                }
              </Button>
            </TableCell>
            <TableCell className="text-right">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-red-600"
                title="Elimina regola"
                onClick={() => onDelete(rule.id)}
                data-testid={`delete-${rule.id}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};


// ── Tab panel ─────────────────────────────────────────────────────────────────

const DatasetTypeTab = ({ datasetType }) => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const res = await validationRulesAPI.list(datasetType);
      setRules(res.data ?? []);
    } catch {
      toast.error('Impossibile caricare le regole');
    } finally {
      setLoading(false);
    }
  }, [datasetType]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleToggle = async (rule) => {
    try {
      const updated = await validationRulesAPI.update(rule.id, { is_active: !rule.is_active });
      setRules((prev) => prev.map((r) => r.id === rule.id ? updated.data : r));
      toast.success(rule.is_active ? 'Regola disattivata' : 'Regola attivata');
    } catch {
      toast.error('Aggiornamento fallito');
    }
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm('Eliminare questa regola? L\'azione non è reversibile.')) return;
    try {
      await validationRulesAPI.delete(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      toast.success('Regola eliminata');
    } catch {
      toast.error('Eliminazione fallita');
    }
  };

  const handleSaved = () => {
    setShowForm(false);
    loadRules();
  };

  const activeCount = rules.filter((r) => r.is_active).length;

  return (
    <div className="mt-6 space-y-4">
      <Card className="border border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="font-heading text-base flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                Regole di Validazione
              </CardTitle>
              <CardDescription className="mt-1">
                {loading ? 'Caricamento…' : (
                  <>
                    {rules.length === 0
                      ? 'Nessuna regola configurata'
                      : `${rules.length} regola${rules.length !== 1 ? 'e' : ''} totali, ${activeCount} attiv${activeCount !== 1 ? 'e' : 'a'}`
                    }
                  </>
                )}
              </CardDescription>
            </div>
            {!showForm && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowForm(true)}
                data-testid={`add-rule-${datasetType}`}
              >
                <Plus className="h-4 w-4 mr-2" />
                Aggiungi Regola
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : (
            <RulesTable
              rules={rules}
              onToggle={handleToggle}
              onDelete={handleDelete}
            />
          )}
        </CardContent>
      </Card>

      {showForm && (
        <AddRuleForm
          datasetType={datasetType}
          onSaved={handleSaved}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  );
};


// ── Main page ─────────────────────────────────────────────────────────────────

export const ValidationRulesPage = () => {
  const [activeTab, setActiveTab] = useState('sales');

  return (
    <AppLayout>
      <Header
        title="Regole di Validazione"
        subtitle="Configura le regole applicate automaticamente durante ogni upload"
      />

      <div className="page-container animate-fade-in">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            {TABS.map((tab) => (
              <TabsTrigger key={tab.key} value={tab.key} data-testid={`tab-${tab.key}`}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {TABS.map((tab) => (
            <TabsContent key={tab.key} value={tab.key}>
              {/* Mount/unmount resets state on tab switch */}
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

export default ValidationRulesPage;
