import React, { useState, useEffect } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Separator } from '../../components/ui/separator';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { organizationsAPI, authAPI } from '../../api';
import { Switch } from '../../components/ui/switch';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useBilling } from '../../hooks/useBilling';
import { useEntitlements } from '../../hooks/useEntitlements';
import BillingSection from '../../components/BillingSection';
import PaymentConnectionsCard from './PaymentConnectionsCard';
import PaymentMethodsSection from './sections/PaymentMethodsSection';
import {
  Building,
  Save,
  Globe,
  BadgeEuro,
  Info,
  Lock,
  ShieldAlert,
  Languages,
  AlertTriangle,
  Trash2,
  Bell,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { SUPPORTED_LANGUAGES } from '../../i18n';

// ── Static option catalogs ────────────────────────────────────────────────────

const TIMEZONES = [
  { value: 'Europe/Rome',       label: 'Roma / Milano (CET)' },
  { value: 'Europe/London',     label: 'London (GMT)' },
  { value: 'Europe/Paris',      label: 'Paris / Madrid / Berlin (CET)' },
  { value: 'Europe/Zurich',     label: 'Zurich (CET)' },
  { value: 'Europe/Warsaw',     label: 'Warsaw (CET)' },
  { value: 'Europe/Bucharest',  label: 'Bucharest (EET)' },
  { value: 'UTC',               label: 'UTC' },
  { value: 'America/New_York',  label: 'New York (EST)' },
  { value: 'America/Chicago',   label: 'Chicago (CST)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST)' },
  { value: 'America/Sao_Paulo', label: 'Sao Paulo (BRT)' },
  { value: 'Asia/Dubai',        label: 'Dubai (GST)' },
  { value: 'Asia/Tokyo',        label: 'Tokyo (JST)' },
  { value: 'Australia/Sydney',  label: 'Sydney (AEDT)' },
];

// CH compliance v1: aligned with the backend ``SUPPORTED_CURRENCIES``
// in ``services/currency_service.py``. Adding a code here without
// updating the backend will surface as a 422 on PUT /organizations.
const CURRENCIES = [
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'CHF', label: 'CHF — Swiss Franc' },
];

// ── Language Selector ─────────────────────────────────────────────────────────

function LanguageSelector() {
  const { t, i18n } = useTranslation('settings');
  const { refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);

  const handleChange = async (locale) => {
    if (locale === i18n.language) return;
    setSaving(true);
    try {
      await authAPI.updateLocale(locale);
      i18n.changeLanguage(locale);
      await refreshUser();
      toast.success(t('language.updated'));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Languages className="h-5 w-5" />
          {t('language.title')}
        </CardTitle>
        <CardDescription>{t('language.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleChange(lang.code)}
              disabled={saving}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                i18n.language === lang.code
                  ? 'border-primary bg-primary/5 text-primary font-medium'
                  : 'border-border hover:border-primary/50 text-foreground'
              }`}
            >
              <span className="text-lg">{lang.flag}</span>
              <span>{lang.label}</span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}


// ── SettingsPage ──────────────────────────────────────────────────────────────

export const SettingsPage = () => {
  const { t, i18n } = useTranslation('settings');
  const { user, refreshUser } = useAuth();
  const [organization, setOrganization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    industry: '',
    timezone: '',
    currency: '',
    public_slug: '',
  });
  // CH compliance v1: tracks whether the currency selector is still
  // mutable. The backend forbids changes once any order exists
  // (immutability rule); we mirror that on the UI to avoid an avoidable
  // 409 round-trip and to be transparent about the constraint.
  const [currencyCanChange, setCurrencyCanChange] = useState(true);

  const isAdmin = user?.role === 'admin';

  // ── Password change state ────────────────────────────────────────────────────
  const [pwForm, setPwForm] = useState({ current: '', new_pw: '', confirm: '' });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState('');

  const validatePassword = (pw) => {
    const errors = [];
    if (pw.length < 12) errors.push(t('validation.min_length'));
    if (!/[a-z]/.test(pw)) errors.push(t('validation.lowercase'));
    if (!/[A-Z]/.test(pw)) errors.push(t('validation.uppercase'));
    if (!/\d/.test(pw)) errors.push(t('validation.digit'));
    return errors.length ? t('validation.prefix') + errors.join(', ') + '.' : '';
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (pwForm.new_pw !== pwForm.confirm) {
      setPwError(t('security.mismatch'));
      return;
    }
    const valError = validatePassword(pwForm.new_pw);
    if (valError) {
      setPwError(valError);
      return;
    }
    setPwError('');
    setPwSaving(true);
    try {
      await authAPI.changePassword(pwForm.current, pwForm.new_pw);
      toast.success(t('security.success'));
      setPwForm({ current: '', new_pw: '', confirm: '' });
      await refreshUser();
    } catch (error) {
      const detail = error.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : detail || t('security.error');
      toast.error(msg);
    } finally {
      setPwSaving(false);
    }
  };

  const fetchOrganization = async () => {
    setLoading(true);
    try {
      // Parallel fetch: org doc + currency-info endpoint (telling us
      // whether we can still change currency). The currency-info call
      // is best-effort — if it fails we keep the selector enabled and
      // let the backend reject the change with its 409.
      const [orgResponse, currencyInfoResult] = await Promise.allSettled([
        organizationsAPI.getCurrent(),
        organizationsAPI.getCurrencyInfo(),
      ]);
      if (orgResponse.status !== 'fulfilled') {
        throw orgResponse.reason;
      }
      const org = orgResponse.value.data;
      setOrganization(org);
      setFormData({
        name:     org.name     || '',
        industry: org.industry || '',
        timezone: org.timezone || '',
        currency: org.currency || '',
        default_iva: org.settings?.default_iva ?? '',
        public_slug: org.public_slug || '',
      });
      if (currencyInfoResult.status === 'fulfilled') {
        const info = currencyInfoResult.value.data || {};
        setCurrencyCanChange(info.can_change !== false);
      }
    } catch (error) {
      toast.error(t('organization.load_error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrganization(); }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error(t('organization.name_required'));
      return;
    }
    setSaving(true);
    try {
      const payload = { ...formData };
      // Convert default_iva to number for backend (or null to clear)
      if (payload.default_iva !== '' && payload.default_iva != null) {
        payload.default_iva = parseFloat(payload.default_iva);
      } else {
        delete payload.default_iva;
      }
      // public_slug: send null to clear, trimmed string to set
      if (!payload.public_slug?.trim()) {
        delete payload.public_slug;
      } else {
        payload.public_slug = payload.public_slug.trim();
      }
      await organizationsAPI.updateCurrent(payload);
      toast.success(t('organization.saved'));
      fetchOrganization();
      await refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('organization.save_error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout>
      <Header title={t('title')} subtitle={t('subtitle')}>
        {/* F2.0 — accesso rapido all'editor del profilo pubblico */}
        <Link to="/public-profile">
          <Button variant="outline" size="sm">
            {t('publicProfile.title', { defaultValue: 'Profilo pubblico' })}
          </Button>
        </Link>
      </Header>

      <div className="p-4 md:p-8 space-y-6 animate-fade-in max-w-2xl">

        {/* ── Organization ── */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Building className="h-5 w-5" />
              {t('organization.card_title')}
            </CardTitle>
            <CardDescription>{t('organization.card_desc')}</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : (
              <form onSubmit={handleSave} className="space-y-5">
                <div className="space-y-1.5">
                  <Label htmlFor="org-name">{t('organization.name')}</Label>
                  <Input id="org-name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} disabled={!isAdmin} data-testid="org-name-input" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="org-industry">{t('organization.industry')}</Label>
                  <Input id="org-industry" placeholder={t('organization.industry_placeholder')} value={formData.industry} onChange={(e) => setFormData({ ...formData, industry: e.target.value })} disabled={!isAdmin} data-testid="org-industry-input" />
                </div>
                <Separator />
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="org-currency" className="flex items-center gap-1.5">
                      <BadgeEuro className="h-3.5 w-3.5 text-muted-foreground" />
                      {t('organization.currency')}
                    </Label>
                    {isAdmin && currencyCanChange ? (
                      <Select value={formData.currency} onValueChange={(v) => setFormData({ ...formData, currency: v })}>
                        <SelectTrigger id="org-currency" data-testid="org-currency-select">
                          <SelectValue placeholder={t('organization.currency_placeholder')} />
                        </SelectTrigger>
                        <SelectContent>
                          {CURRENCIES.map(({ value, label }) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input value={formData.currency || '\u2014'} disabled data-testid="org-currency-input" />
                    )}
                    {isAdmin && !currencyCanChange ? (
                      <p
                        className="text-xs text-muted-foreground"
                        data-testid="org-currency-locked-hint"
                      >
                        {t(
                          'organization.currency_locked',
                          'La valuta non puo piu essere modificata: ci sono ordini gia registrati per questa organizzazione.'
                        )}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="org-default-iva" className="flex items-center gap-1.5">
                      <BadgeEuro className="h-3.5 w-3.5 text-muted-foreground" />
                      {t('organization.default_iva', 'IVA predefinita acquisti (%)')}
                    </Label>
                    {isAdmin ? (
                      <Input
                        id="org-default-iva"
                        type="number"
                        min={0}
                        max={100}
                        step={0.5}
                        placeholder={t('organization.default_iva_placeholder', 'es. 22')}
                        value={formData.default_iva}
                        onChange={(e) => setFormData({ ...formData, default_iva: e.target.value })}
                      />
                    ) : (
                      <Input value={formData.default_iva || '\u2014'} disabled />
                    )}
                    <p className="text-xs text-muted-foreground">{t('organization.default_iva_hint', 'Valore pre-compilato per i nuovi acquisti')}</p>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="org-timezone" className="flex items-center gap-1.5">
                      <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                      {t('organization.timezone')}
                    </Label>
                    {isAdmin ? (
                      <Select value={formData.timezone} onValueChange={(v) => setFormData({ ...formData, timezone: v })}>
                        <SelectTrigger id="org-timezone" data-testid="org-timezone-select">
                          <SelectValue placeholder={t('organization.timezone_placeholder')} />
                        </SelectTrigger>
                        <SelectContent>
                          {TIMEZONES.map(({ value, label }) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input value={formData.timezone || '\u2014'} disabled data-testid="org-timezone-input" />
                    )}
                  </div>
                </div>
                <Separator />
                {/* Public storefront */}
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="org-slug" className="flex items-center gap-1.5">
                      {t('organization.public_slug', 'Indirizzo catalogo pubblico')}
                    </Label>
                    <div className="flex gap-2 mt-1">
                      <div className="flex items-center rounded-md border bg-muted px-3 text-sm text-muted-foreground shrink-0">
                        {window.location.origin}/s/
                      </div>
                      <Input
                        id="org-slug"
                        placeholder="il-tuo-negozio"
                        value={formData.public_slug}
                        onChange={(e) => setFormData({ ...formData, public_slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                        disabled={!isAdmin}
                        className="flex-1"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {t('organization.public_slug_hint', 'Imposta un indirizzo per rendere il tuo catalogo prodotti visibile pubblicamente. Lascia vuoto per disattivare.')}
                    </p>
                  </div>
                  {formData.public_slug && (
                    <div className="flex items-center gap-2 rounded-lg border bg-blue-50 p-3">
                      <p className="text-sm text-blue-800 flex-1">
                        {window.location.origin}/s/{formData.public_slug}
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(`${window.location.origin}/s/${formData.public_slug}`);
                          toast.success(t('organization.link_copied', 'Link copiato'));
                        }}
                        className="text-xs text-blue-700 hover:text-blue-900 font-medium shrink-0"
                      >
                        {t('organization.copy_link', 'Copia link')}
                      </button>
                      <a
                        href={`/s/${formData.public_slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-700 hover:text-blue-900 font-medium shrink-0"
                      >
                        {t('organization.open_catalog', 'Apri')}
                      </a>
                    </div>
                  )}
                </div>

                {isAdmin ? (
                  <Button type="submit" disabled={saving} data-testid="save-settings-btn" className="gap-2">
                    <Save className="h-4 w-4" />
                    {saving ? t('organization.saving') : t('organization.save')}
                  </Button>
                ) : (
                  <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2">
                    <Info className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">{t('organization.admin_only')}</p>
                  </div>
                )}
              </form>
            )}
          </CardContent>
        </Card>

        <LanguageSelector />

        {/* ── Billing (v5.4 — enriched subscription overview) ── */}
        <BillingSection />

        {/* ── Payment Connections ── */}
        <PaymentConnectionsCard isAdmin={isAdmin} />

        {/* ── CH compliance v1: Payment methods preflight (Stripe capabilities) ── */}
        {isAdmin ? <PaymentMethodsSection /> : null}

        {/* ── Profile ── */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="font-heading text-lg">{t('profile.card_title')}</CardTitle>
            <CardDescription>{t('profile.card_desc')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t('profile.name')}</p>
                <p className="text-sm font-medium">{user?.name || '\u2014'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t('profile.email')}</p>
                <p className="text-sm font-medium">{user?.email || '\u2014'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t('profile.role')}</p>
                {user?.role === 'admin' ? (
                  <Badge className="bg-purple-100 text-purple-800 border-0">{t('roles.admin')}</Badge>
                ) : (
                  <Badge variant="outline">{t('roles.user')}</Badge>
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t('profile.org_id')}</p>
                <p className="text-xs font-mono text-muted-foreground break-all">{user?.organization_id || '\u2014'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── Security ── */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Lock className="h-5 w-5" />{t('security.card_title')}
            </CardTitle>
            <CardDescription>{t('security.card_desc')}</CardDescription>
          </CardHeader>
          <CardContent>
            {user?.must_change_password && (
              <div className="mb-4 flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <p><span className="font-medium">{t('security.must_change_title')}</span> {t('security.must_change_desc')}</p>
              </div>
            )}
            <form onSubmit={handleChangePassword} className="space-y-4 max-w-sm">
              <div className="space-y-1.5">
                <Label htmlFor="pw-current">{t('security.current_password')}</Label>
                <Input id="pw-current" type="password" autoComplete="current-password" value={pwForm.current} onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })} required data-testid="pw-current-input" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw-new">{t('security.new_password')}</Label>
                <Input id="pw-new" type="password" autoComplete="new-password" placeholder={t('security.new_password_placeholder')} value={pwForm.new_pw} onChange={(e) => { setPwForm({ ...pwForm, new_pw: e.target.value }); setPwError(''); }} required minLength={12} className={pwError ? 'border-destructive' : ''} data-testid="pw-new-input" />
                {pwError ? (
                  <p className="text-xs text-destructive">{pwError}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">{t('security.password_hint')}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw-confirm">{t('security.confirm_password')}</Label>
                <Input id="pw-confirm" type="password" autoComplete="new-password" value={pwForm.confirm} onChange={(e) => { setPwForm({ ...pwForm, confirm: e.target.value }); setPwError(''); }} required data-testid="pw-confirm-input" />
              </div>
              <Button type="submit" variant="outline" disabled={pwSaving} className="gap-2" data-testid="pw-submit-btn">
                <Lock className="h-4 w-4" />{pwSaving ? t('security.saving') : t('security.submit')}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* ── Account Management (v6.0, GDPR art. 17) ────────────────────── */}
        {isAdmin && <AccountDeactivationSection />}

      </div>
    </AppLayout>
  );
};


// ── Account Deactivation Section ─────────────────────────────────────────────

const AccountDeactivationSection = () => {
  const { t } = useTranslation('settings');
  const { logout } = useAuth();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dataSummary, setDataSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const handleOpenDialog = async () => {
    setDialogOpen(true);
    setPassword('');
    setConfirmed(false);
    // Fetch data summary
    setSummaryLoading(true);
    try {
      const data = await authAPI.getAccountDataSummary();
      setDataSummary(data);
    } catch {
      setDataSummary(null); // graceful degradation
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleDeactivate = async () => {
    setLoading(true);
    try {
      await authAPI.deactivateAccount(password);
      toast.warning(t('account.success', 'Account disattivato. Hai 30 giorni per riattivarlo.'));
      setDialogOpen(false);
      logout();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante la disattivazione');
    } finally {
      setLoading(false);
    }
  };

  const summaryItems = dataSummary ? [
    { label: t('account.data_sales', 'Vendite'), count: dataSummary.sales_count },
    { label: t('account.data_purchases', 'Acquisti'), count: dataSummary.purchases_count },
    { label: t('account.data_expenses', 'Spese'), count: dataSummary.expenses_count },
    { label: t('account.data_fixed_costs', 'Costi fissi'), count: dataSummary.fixed_costs_count },
    { label: t('account.data_customers', 'Clienti'), count: dataSummary.customers_count },
    { label: t('account.data_suppliers', 'Fornitori'), count: dataSummary.suppliers_count },
    { label: t('account.data_products', 'Prodotti'), count: dataSummary.products_count },
    { label: t('account.data_datasets', 'Dataset'), count: dataSummary.datasets_count },
  ].filter((item) => item.count > 0) : [];

  // ── Export GDPR ──────────────────────────────────────────────────────
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await authAPI.exportData();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `aurya_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success(t('account.export_success', 'Export completato'));
    } catch (error) {
      toast.error('Errore durante l\'export dei dati');
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      {/* Data Export (GDPR art. 20) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('account.export_title', 'Esporta i tuoi dati')}</CardTitle>
          <CardDescription>{t('account.export_desc', 'Scarica tutti i dati della tua organizzazione in formato ZIP (GDPR art. 20)')}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={handleExport} disabled={exporting} className="gap-2">
            {exporting ? (
              <>{t('account.export_loading', 'Preparazione export...')}</>
            ) : (
              <>{t('account.export_button', 'Scarica dati')}</>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Account Deactivation */}
      <Card className="border border-destructive/30">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            {t('account.card_title', 'Gestione Account')}
          </CardTitle>
          <CardDescription>{t('account.card_desc', 'Gestisci il tuo account e i tuoi dati')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-destructive/20 bg-destructive/5 p-4 space-y-3">
            <p className="text-sm font-medium text-destructive">{t('account.danger_zone', 'Zona pericolosa')}</p>
            <p className="text-sm text-muted-foreground">
              {t('account.deactivate_desc', 'Disattiva il tuo account. Avrai 30 giorni per riattivarlo, dopo i quali tutti i dati saranno cancellati definitivamente.')}
            </p>
            <Button variant="destructive" size="sm" onClick={handleOpenDialog} className="gap-2">
              <Trash2 className="h-4 w-4" />
              {t('account.deactivate_button', 'Disattiva account')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              {t('account.dialog_title', 'Conferma disattivazione')}
            </DialogTitle>
            <DialogDescription>
              {t('account.dialog_desc', 'Inserisci la tua password per confermare. Dopo 30 giorni tutti i dati saranno cancellati definitivamente.')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            {/* Data summary */}
            {summaryLoading ? (
              <div className="text-sm text-muted-foreground animate-pulse">{t('account.dialog_loading', 'Caricamento dati...')}</div>
            ) : summaryItems.length > 0 ? (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 space-y-1">
                <p className="text-sm font-medium text-amber-800">
                  {t('account.dialog_data_warning', 'Verranno eliminati definitivamente:')}
                </p>
                <ul className="text-sm text-amber-700 list-disc list-inside">
                  {summaryItems.map((item) => (
                    <li key={item.label}>{item.count} {item.label.toLowerCase()}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Password confirmation */}
            <div className="space-y-1.5">
              <Label htmlFor="deactivate-password">{t('security.current_password', 'Password attuale')}</Label>
              <Input
                id="deactivate-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>

            {/* Confirmation checkbox */}
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                id="deactivate-confirm"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-border"
              />
              <label htmlFor="deactivate-confirm" className="text-xs text-muted-foreground leading-relaxed">
                {t('account.dialog_checkbox', 'Confermo di voler disattivare il mio account')}
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2 pt-2">
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t('account.dialog_cancel', 'Annulla')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeactivate}
              disabled={loading || !password || !confirmed}
            >
              {loading ? t('account.dialog_loading_deactivate', 'Disattivazione...') : t('account.dialog_confirm', 'Disattiva account')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

// Wrapper di gating: monta le preferenze alert/report solo se il piano
// abilita almeno una delle feature che quelle preferenze governano.
export default SettingsPage;
