/**
 * OrgBrandingDialog — admin form for the org-level branding cascade.
 *
 * Step 5 of the "olistic settings" feature. The form lets the admin
 * set defaults that flow down to every store of the org (logo, brand
 * colors, favicon-ready). Per-store branding still wins when set —
 * this dialog only configures the **fallback** layer.
 *
 * Pattern reuse: the layout (logo + color pickers + live preview)
 * mirrors the per-store branding accordion inside StoresPage.js so
 * the admin sees a familiar UI. Differences:
 *
 *   • Header banner explaining the cascade
 *   • "Rimuovi" buttons next to logo + color fields, since this is a
 *     dedicated dialog where clearing has a clear meaning ("torno
 *     a non avere default org, ogni store fa per sé")
 *   • No SEO / email / fulfillment / language sections — those are
 *     intentionally left at the per-store level (they're surface-
 *     specific and not part of the brand identity)
 *
 * Open/close is controlled from StoresPage via the `open` prop and
 * `onClose` callback. The component fetches its own data on every
 * open so a recently-uploaded logo from another tab is reflected.
 *
 * i18n
 * ----
 * All user-visible strings flow through the `stores` namespace under
 * `org_branding.*`. The dialog has no admin-locale fallback layer of
 * its own — it relies on the parent admin AuthContext having already
 * called `i18n.changeLanguage(user.locale)` on mount, which is the
 * standard contract for all admin surfaces. The Trans interpolation
 * on the cascade-banner body uses `<1>` to bold "tutti gli store"
 * (or its translation) without splitting the sentence into pieces.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2, CheckCircle2, X, Upload } from 'lucide-react';
import {
  ResponsiveDialog, ResponsiveDialogContent, ResponsiveDialogHeader,
  ResponsiveDialogTitle, ResponsiveDialogFooter,
} from '../../../components/ui/responsive-dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { orgBrandingAPI } from '../../../api/orgBranding';


export default function OrgBrandingDialog({ open, onClose }) {
  const { t } = useTranslation('stores');
  // The form mirrors the four backend fields. We keep them as strings
  // (never `null`) for controlled-input convenience; the save
  // function maps "" → null when sending the PATCH so the backend can
  // distinguish "not set" from "explicit clear".
  const [form, setForm] = useState({
    logo_url: '',
    brand_color: '',
    brand_color_text: '',
    favicon_url: '',
  });
  const [logoUrl, setLogoUrl] = useState(null);  // separate from form.logo_url for cache-busting
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Fetch current org-level branding when the dialog opens. We don't
  // cache between opens — a fresh GET ensures the form reflects any
  // changes made elsewhere (e.g. from another tab or user).
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    orgBrandingAPI.get()
      .then(res => {
        if (cancelled) return;
        const data = res.data || {};
        setForm({
          logo_url: data.logo_url || '',
          brand_color: data.brand_color || '',
          brand_color_text: data.brand_color_text || '',
          favicon_url: data.favicon_url || '',
        });
        setLogoUrl(data.logo_url || null);
      })
      .catch(() => {
        // Silent — empty form is the right starting state when the
        // org has never configured branding.
        if (!cancelled) {
          setForm({ logo_url: '', brand_color: '', brand_color_text: '', favicon_url: '' });
          setLogoUrl(null);
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open]);

  const handleUploadLogo = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await orgBrandingAPI.uploadLogo(file);
      const newUrl = res.data?.logo_url;
      if (newUrl) {
        // Cache-bust so <img> reloads even when the server keeps the
        // same URL (we replace the file in place with the same name
        // when the extension matches).
        const bust = newUrl.includes('?') ? '&' : '?';
        const busted = `${newUrl}${bust}t=${Date.now()}`;
        setLogoUrl(busted);
        setForm(f => ({ ...f, logo_url: newUrl }));  // store the un-busted URL
      }
      toast.success(t('org_branding.toast.logo_uploaded'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('org_branding.toast.logo_upload_error'));
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteLogo = async () => {
    if (!logoUrl && !form.logo_url) return;
    setUploading(true);
    try {
      await orgBrandingAPI.deleteLogo();
      setLogoUrl(null);
      setForm(f => ({ ...f, logo_url: '' }));
      toast.success(t('org_branding.toast.logo_removed'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('org_branding.toast.logo_remove_error'));
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Convert empty strings to null for the PATCH body so the
      // backend stores them as "not set" instead of "explicit clear"
      // — more useful here because the dialog has explicit "Rimuovi"
      // buttons for the explicit-clear case.
      const payload = {};
      if (form.brand_color.trim()) payload.brand_color = form.brand_color.trim();
      if (form.brand_color_text.trim()) payload.brand_color_text = form.brand_color_text.trim();
      // logo_url is managed by the upload/delete endpoints — don't
      // touch it here unless the admin pasted a manual URL (rare).
      if (form.logo_url && form.logo_url !== logoUrl?.split('?')[0]) {
        payload.logo_url = form.logo_url.trim();
      }
      // favicon_url is in the schema but not yet UI-exposed; leave for
      // future iteration without removing the field plumbing.

      if (Object.keys(payload).length > 0) {
        await orgBrandingAPI.update(payload);
      }
      toast.success(t('org_branding.toast.saved'));
      onClose?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('org_branding.toast.save_error'));
    } finally {
      setSaving(false);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm(t('org_branding.clear_all.confirm'))) {
      return;
    }
    setSaving(true);
    try {
      await orgBrandingAPI.clear();
      setForm({ logo_url: '', brand_color: '', brand_color_text: '', favicon_url: '' });
      setLogoUrl(null);
      toast.success(t('org_branding.toast.cleared'));
      onClose?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('org_branding.toast.clear_error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={(v) => { if (!v) onClose?.(); }}>
      <ResponsiveDialogContent className="sm:max-w-lg max-h-[90vh] sm:max-h-[85vh] overflow-y-auto">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>{t('org_branding.title_emoji')}</ResponsiveDialogTitle>
        </ResponsiveDialogHeader>

        <div className="px-4 sm:px-0 pb-2 space-y-4">
          {/* Cascade-explainer banner — sets expectations BEFORE the
              admin starts filling fields, so they understand why a
              global value may not show up on a specific store. */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
            <p className="font-semibold mb-0.5">{t('org_branding.banner.heading')}</p>
            <p>
              <Trans
                i18nKey="org_branding.banner.body"
                ns="stores"
                components={[<strong />]}
              />
            </p>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {/* ── Logo ────────────────────────────────────────────── */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold">{t('org_branding.logo.label')}</Label>
                <p className="text-xs text-muted-foreground">
                  {t('org_branding.logo.hint')}
                </p>
                <div className="flex items-center gap-4">
                  {logoUrl ? (
                    <img
                      src={logoUrl}
                      alt={t('org_branding.logo.alt')}
                      className="h-16 w-16 rounded-lg object-cover border"
                    />
                  ) : (
                    <div className="h-16 w-16 rounded-lg bg-muted flex items-center justify-center text-muted-foreground text-xs border">
                      {t('org_branding.logo.placeholder')}
                    </div>
                  )}
                  <div className="flex-1 min-w-0 space-y-2">
                    <label className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline cursor-pointer">
                      <Upload className="h-3.5 w-3.5" />
                      {logoUrl ? t('org_branding.logo.replace') : t('org_branding.logo.upload')}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp,image/svg+xml"
                        className="hidden"
                        disabled={uploading}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleUploadLogo(file);
                          if (e.target) e.target.value = '';
                        }}
                      />
                    </label>
                    {logoUrl && (
                      <button
                        type="button"
                        onClick={handleDeleteLogo}
                        disabled={uploading}
                        className="block text-xs text-destructive hover:underline"
                      >
                        {t('org_branding.logo.remove')}
                      </button>
                    )}
                    <p className="text-[10px] text-muted-foreground">
                      {t('org_branding.logo.format_hint')}
                    </p>
                  </div>
                </div>
              </div>

              {/* ── Colori ──────────────────────────────────────────── */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold">{t('org_branding.colors.label')}</Label>
                <p className="text-xs text-muted-foreground">
                  {t('org_branding.colors.hint')}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">{t('org_branding.colors.brand_color')}</Label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={form.brand_color || '#1a1a1a'}
                        onChange={e => setForm(f => ({ ...f, brand_color: e.target.value }))}
                        className="w-10 h-10 rounded border cursor-pointer shrink-0"
                      />
                      <Input
                        value={form.brand_color}
                        onChange={e => setForm(f => ({ ...f, brand_color: e.target.value }))}
                        placeholder="#1a1a1a"
                        className="flex-1 text-sm"
                        maxLength={32}
                      />
                      {form.brand_color && (
                        <button
                          type="button"
                          onClick={() => setForm(f => ({ ...f, brand_color: '' }))}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground"
                          aria-label={t('org_branding.colors.remove_brand_aria')}
                          title={t('org_branding.colors.remove_short')}
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">{t('org_branding.colors.text_color')}</Label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={form.brand_color_text || '#ffffff'}
                        onChange={e => setForm(f => ({ ...f, brand_color_text: e.target.value }))}
                        className="w-10 h-10 rounded border cursor-pointer shrink-0"
                      />
                      <Input
                        value={form.brand_color_text}
                        onChange={e => setForm(f => ({ ...f, brand_color_text: e.target.value }))}
                        placeholder="#ffffff"
                        className="flex-1 text-sm"
                        maxLength={32}
                      />
                      {form.brand_color_text && (
                        <button
                          type="button"
                          onClick={() => setForm(f => ({ ...f, brand_color_text: '' }))}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground"
                          aria-label={t('org_branding.colors.remove_text_aria')}
                          title={t('org_branding.colors.remove_short')}
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Live preview — mirrors what AuthShell + storefront
                    headers will look like with these colors. Only shows
                    when at least the brand color is set. */}
                {form.brand_color && (
                  <div
                    className="rounded-lg p-3 text-sm flex items-center gap-3 mt-2"
                    style={{ backgroundColor: form.brand_color, color: form.brand_color_text || '#fff' }}
                  >
                    {logoUrl && (
                      <img src={logoUrl} alt="" className="h-8 w-8 rounded object-cover" />
                    )}
                    <span className="font-semibold">{t('org_branding.preview')}</span>
                  </div>
                )}
              </div>

              {/* ── Future sections placeholder ─────────────────────── */}
              <details className="rounded-lg border bg-muted/30 px-3 py-2">
                <summary className="text-xs font-medium text-muted-foreground cursor-pointer">
                  {t('org_branding.future.summary')}
                </summary>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('org_branding.future.body')}
                </p>
              </details>

              {/* Clear-all (destructive) — separated visually from save */}
              <button
                type="button"
                onClick={handleClearAll}
                disabled={saving}
                className="w-full text-xs text-destructive hover:underline pt-2 border-t"
              >
                {t('org_branding.clear_all.button')}
              </button>
            </>
          )}
        </div>

        <ResponsiveDialogFooter>
          <Button
            variant="outline"
            onClick={() => onClose?.()}
            className="w-full sm:w-auto"
            disabled={saving}
          >
            {t('org_branding.actions.cancel')}
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || loading || uploading}
            className="gap-1.5 w-full sm:w-auto"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            {t('org_branding.actions.save')}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
