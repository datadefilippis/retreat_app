/**
 * ServiceDashboardPage — impostazioni AVANZATE di un servizio
 * (ciclo Potatura, onda PS2, 30 lug 2026).
 *
 * Route: /services/:product_id (authenticated)
 *
 * Il posto primario per configurare un servizio e' la riga espansa del
 * listino (/listino): nome, prezzo, durata, stato, opzioni, incasso,
 * requisiti. Questa pagina tiene SOLO cio' che non ha altra casa:
 *   - Header compatto: nome (read-only) + back + Anteprima/Copia/Duplica
 *   - Descrizione estesa della landing (con multilingua) + copertina
 *   - Traduzioni di nome e nota
 *   - Disponibilita': calendario ufficiale / regole orari per-giorno
 *     + richiesta data/ora personalizzata
 *   - Campi aggiuntivi al checkout
 *
 * Il salvataggio manda SOLO i campi governati qui (PATCH parziale,
 * exclude_unset lato API); il metadata fa merge su quello esistente
 * per non azzerare i campi del listino (durata, requisiti, ...).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
// deep-link diretto (/services/:id): il bundle i18n admin non e' ancora
// caricato dal Layout — stesso fix di EventWizard
import '../../i18n-admin';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { availabilityAPI } from '../../api/availability';
import FieldEditorList from '../events/components/FieldEditorList';
import { pruneFieldConfigs } from '../events/components/fieldConfigUtils';
import AvailabilityRulesEditor from './components/AvailabilityRulesEditor';
import useLandingUrl from '../products/hooks/useLandingUrl';
import MultiLangSection from '../../components/MultiLangSection';


export default function ServiceDashboardPage() {
  const { product_id: productId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation('products');
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);


  // Multilingua manuale — lingue offerte dall'operatore (per campo);
  // salvate sul prodotto via PATCH translations
  const [trName, setTrName] = useState({});
  const [trDescription, setTrDescription] = useState({});
  const [trLong, setTrLong] = useState({});
  const buildTranslationsPayload = () => {
    const langs = new Set([...Object.keys(trName), ...Object.keys(trDescription), ...Object.keys(trLong)]);
    const out = {};
    langs.forEach(l => {
      const e = {};
      if ((trName[l] || '').trim()) e.name = trName[l].trim();
      if ((trDescription[l] || '').trim()) e.description = trDescription[l].trim();
      if ((trLong[l] || '').trim()) e.long_description = trLong[l].trim();
      if (Object.keys(e).length) out[l] = e;
    });
    return out;
  };
  // PS2 — solo i campi che questa pagina governa davvero. name e
  // description restano come riferimento IT (read-only qui, si
  // modificano dal listino).
  const [productForm, setProductForm] = useState({
    name: '', description: '',
    duration_minutes: 60,
    service_allow_custom_request: false,
    // Onda 15 — "Usa calendario ufficiale" flag (see wizard for rationale)
    use_default_schedule: false,
    order_fields: [],
    long_description: '',
    cover_image_url: '',
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [duplicating, setDuplicating] = useState(false);

  const [rules, setRules] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const prodRes = await productsAPI.list(false);
      const prod = (prodRes.data || []).find(p => p.id === productId);
      if (!prod) { setError('not_found'); return; }
      if (prod.item_type !== 'service') { setError('wrong_type'); return; }
      setProduct(prod);

      const meta = prod.metadata || {};
      const ptr = prod.translations || {};
      const trN = {}, trD = {}, trL = {};
      Object.entries(ptr).forEach(([l, f]) => {
        if (f?.name) trN[l] = f.name;
        if (f?.description) trD[l] = f.description;
        if (f?.long_description) trL[l] = f.long_description;
      });
      setTrName(trN);
      setTrDescription(trD);
      setTrLong(trL);
      setProductForm({
        name: prod.name || '',
        description: prod.description || '',
        duration_minutes: meta.duration_minutes ?? 60,
        service_allow_custom_request: !!meta.service_allow_custom_request,
        use_default_schedule: !!meta.use_default_schedule,
        order_fields: meta.order_fields || [],
        long_description: meta.long_description || '',
        cover_image_url: meta.cover_image_url || '',
      });

      const rulesRes = await availabilityAPI.listRules(null, productId).catch(() => ({ data: { rules: [] } }));
      setRules(rulesRes.data?.rules || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.status === 404 ? 'not_found' : 'generic');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  const saveProduct = async () => {
    setSavingProduct(true);
    try {
      const existingMeta = product?.metadata || {};
      // PS2 — payload parziale: nessun campo del listino (nome, prezzo,
      // durata, stato, incasso, requisiti, foto) viene inviato, quindi
      // non puo' essere azzerato. Il metadata e' merge su quello
      // esistente perche' l'API lo sostituisce per intero.
      const upd = {
        translations: buildTranslationsPayload(),
        metadata: {
          ...existingMeta,
          service_allow_custom_request: !!productForm.service_allow_custom_request,
          use_default_schedule: !!productForm.use_default_schedule,
          order_fields: pruneFieldConfigs(productForm.order_fields),
          long_description: productForm.long_description?.trim() || null,
          cover_image_url: productForm.cover_image_url?.trim() || null,
        },
      };
      const res = await productsAPI.update(productId, upd);
      // Merge backend response to pick up slug updates
      const updatedProd = res.data || upd;
      setProduct(prev => prev ? { ...prev, ...updatedProd } : prev);
      toast.success(t('dashboards.service.toasts.updated'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.common.saveError'));
    } finally { setSavingProduct(false); }
  };

  // Flag booleani con persistenza immediata (pattern Onda 15): PATCH del
  // solo metadata, merge sull'esistente.
  const saveMetaFlag = async (field, next, toastOn, toastOff) => {
    const prev = productForm[field];
    setProductForm(f => ({ ...f, [field]: next }));
    try {
      const existingMeta = product?.metadata || {};
      const merged = {
        ...existingMeta,
        service_allow_custom_request: !!productForm.service_allow_custom_request,
        use_default_schedule: !!productForm.use_default_schedule,
        [field]: next,
      };
      await productsAPI.update(productId, { metadata: merged });
      setProduct(p => p ? { ...p, metadata: merged } : p);
      toast.success(next ? toastOn : toastOff);
    } catch {
      setProductForm(f => ({ ...f, [field]: prev }));
      toast.error(t('dashboards.common.saveError'));
    }
  };

  const handleDuplicate = async () => {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const res = await productsAPI.duplicate(productId);
      toast.success(t('dashboards.service.toasts.duplicated'));
      const newId = res.data?.id;
      if (newId) navigate(`/services/${newId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.service.toasts.duplicateError'));
    } finally {
      setDuplicating(false);
    }
  };

  // Server-resolved landing URL (respects visibility / publish).
  const {
    landingPath: landingUrl,
    landingUrl: landingUrlAbsolute,
    blockers: landingBlockers,
  } = useLandingUrl(productId);

  const copyLandingUrl = async () => {
    if (!landingUrlAbsolute) return;
    try {
      await navigator.clipboard.writeText(landingUrlAbsolute);
      toast.success(t('dashboards.common.linkCopied'));
    } catch {
      toast.error(t('dashboards.common.linkCopyError'));
    }
  };

  // Rules: delete-all + recreate (dataset is tiny)
  const saveRules = async (nextRules) => {
    try {
      for (const old of rules) {
        if (old.id) {
          try { await availabilityAPI.deleteRule(old.id); } catch { /* ignore */ }
        }
      }
      const created = [];
      for (const r of nextRules) {
        try {
          const res = await availabilityAPI.createRule({
            product_id: productId,
            day_of_week: r.day_of_week,
            start_time: r.start_time,
            end_time: r.end_time,
            slot_duration_minutes: r.slot_duration_minutes || 60,
          });
          created.push(res.data);
        } catch { /* ignore individual failures */ }
      }
      setRules(created.length ? created : nextRules);
      toast.success(t('dashboards.service.toasts.availabilityUpdated'));
    } catch {
      toast.error(t('dashboards.service.toasts.availabilityError'));
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">{t('dashboards.common.loading')}</div>;
  }
  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.service.notFound')}</h1>
          <button onClick={() => navigate('/listino')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('dashboards.service.back')}
          </button>
        </div>
      </div>
    );
  }
  if (error === 'wrong_type') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.service.invalidType')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.service.invalidTypeDesc')}</p>
          <button onClick={() => navigate('/listino')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">{t('dashboards.service.back')}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header compatto — il nome si modifica dal listino */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-6">
          <Link to="/listino" className="inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">{t('dashboards.service.back')}</Link>
          <p className="text-[10px] uppercase tracking-widest text-gray-400 mt-2">
            {t('dashboards.service.pageTitle', { defaultValue: 'Impostazioni avanzate del servizio' })}
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mt-1">{productForm.name || t('dashboards.service.fallbackName')}</h1>
          <p className="text-xs text-gray-500 mt-1">
            {t('dashboards.service.baseHint', { defaultValue: 'Nome, prezzo, durata e stato si modificano dal listino.' })}
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-8 space-y-5">
        {/* Action bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {landingUrl ? (
            <a
              href={landingUrl}
              target="_blank" rel="noopener noreferrer"
              className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 text-center"
            >{t('dashboards.service.landingPreview')}</a>
          ) : (
            <div
              className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center"
              title={landingBlockers.length ? landingBlockers.join('\n') : undefined}
            >
              {t('dashboards.service.landingUnavailable')}
              {landingBlockers.length > 0 && (
                <p className="text-[11px] mt-0.5 text-gray-400">{landingBlockers[0]}</p>
              )}
            </div>
          )}
          <button
            type="button" onClick={copyLandingUrl}
            disabled={!landingUrl}
            title={!landingUrl && landingBlockers.length ? landingBlockers.join('\n') : undefined}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{t('dashboards.service.landingCopy')}</button>
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{duplicating ? t('dashboards.service.duplicateLoading') : t('dashboards.service.duplicateBtn')}</button>
        </div>

        {/* ── Descrizione estesa + copertina della landing ─────────── */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.service.longDescTitle')}</h2>
          <p className="text-xs text-gray-500">
            {t('dashboards.service.longDescDescPrefix')}<code>##</code>{t('dashboards.service.longDescDescSuffix')}<code>{t('dashboards.service.longDescBoldNote')}</code>, <code>{t('dashboards.service.longDescListNote')}</code>.
          </p>
          <textarea
            value={productForm.long_description}
            onChange={e => setProductForm(f => ({ ...f, long_description: e.target.value }))}
            rows={8} maxLength={5000}
            placeholder={t('dashboards.service.longDescPlaceholder')}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
          />
          <MultiLangSection fields={[
            { key: 'long_description', label: null, it: productForm.long_description,
              value: trLong, onChange: setTrLong, rows: 5, maxLength: 5000 },
          ]}>{null}</MultiLangSection>

          {/* Copertina della landing (PS2: prima nel pannello prodotto) */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              {t('dashboards.service.coverLabel', { defaultValue: 'Immagine di copertina della landing' })}
            </label>
            <input type="url" value={productForm.cover_image_url}
              onChange={e => setProductForm(f => ({ ...f, cover_image_url: e.target.value }))}
              placeholder={t('dashboards.service.coverPlaceholder', { defaultValue: 'Indirizzo dell\'immagine (https://...)' })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
            <p className="text-[10px] text-gray-400 mt-0.5">
              {t('dashboards.service.coverHint', { defaultValue: 'Se vuota si usa la foto del servizio caricata nel listino.' })}
            </p>
            {productForm.cover_image_url && (
              <img src={productForm.cover_image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
            )}
          </div>

          <div className="flex justify-end">
            <button type="button" onClick={saveProduct}
              disabled={savingProduct}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
            >{savingProduct ? t('dashboards.common.saving') : t('dashboards.common.saveDescription')}</button>
          </div>
        </div>

        {/* ── Traduzioni di nome e nota (PS2: sezione propria) ─────── */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">
            {t('dashboards.service.translationsTitle', { defaultValue: 'Traduzioni' })}
          </h2>
          <p className="text-xs text-gray-500">
            {t('dashboards.service.translationsDesc', { defaultValue: 'Nome e nota del servizio nelle altre lingue offerte ai clienti. I testi italiani si modificano dal listino.' })}
          </p>
          <MultiLangSection fields={[
            { key: 'name', label: t('dashboards.service.transNameLabel', { defaultValue: 'Nome' }), it: productForm.name,
              value: trName, onChange: setTrName, input: true, maxLength: 255 },
            { key: 'description', label: t('dashboards.service.transNoteLabel', { defaultValue: 'Nota (descrizione breve)' }), it: productForm.description,
              value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
          ]}>{null}</MultiLangSection>
          <div className="flex justify-end">
            <button type="button" onClick={saveProduct}
              disabled={savingProduct}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
            >{savingProduct ? t('dashboards.common.saving') : t('dashboards.service.translationsSave', { defaultValue: 'Salva traduzioni' })}</button>
          </div>
        </div>

        {/* ── Availability (Onda 15: toggle calendario standard) ───── */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!productForm.use_default_schedule}
              onChange={(e) => saveMetaFlag(
                'use_default_schedule', e.target.checked,
                t('dashboards.service.toasts.calendarOn'),
                t('dashboards.service.toasts.calendarOff'))}
              className="mt-1 rounded border-gray-300"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-900">
                {t('dashboards.service.calendarTitle')}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {t('dashboards.service.calendarDesc')}
              </p>
            </div>
          </label>

          {productForm.use_default_schedule ? (
            <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-xs text-gray-600 flex items-center justify-between gap-3">
              <span>{t('dashboards.service.calendarFilterHint')}</span>
              <Link
                to="/calendar"
                className="shrink-0 font-medium text-gray-900 underline hover:no-underline"
              >
                {t('dashboards.service.openCalendar')}
              </Link>
            </div>
          ) : (
            <AvailabilityRulesEditor
              rules={rules}
              onChange={(next) => {
                setRules(next);
                saveRules(next);
              }}
              defaultSlotMinutes={Number(productForm.duration_minutes) || 60}
            />
          )}

          {/* PS2: prima nel pannello prodotto — e' una regola di
              disponibilita', quindi vive qui. */}
          <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-gray-200 bg-gray-50 p-3">
            <input
              type="checkbox"
              checked={productForm.service_allow_custom_request}
              onChange={e => saveMetaFlag(
                'service_allow_custom_request', e.target.checked,
                t('dashboards.service.toasts.updated'),
                t('dashboards.service.toasts.updated'))}
              className="mt-0.5 h-4 w-4 rounded border-gray-300"
            />
            <div className="flex-1">
              <span className="block text-sm font-semibold text-gray-900">
                {t('dashboards.service.allowCustomTitle', { defaultValue: 'Permetti richiesta data/ora personalizzata' })}
              </span>
              <span className="block text-xs text-gray-500 mt-0.5">
                {t('dashboards.service.allowCustomHint', { defaultValue: 'In aggiunta agli slot calcolati dalla disponibilità.' })}
              </span>
            </div>
          </label>
        </div>

        {/* ── Order custom fields (FieldEditorList) ────────────────── */}
        <FieldEditorList
          fields={productForm.order_fields || []}
          onChange={(next) => {
            setProductForm(f => ({ ...f, order_fields: next }));
          }}
          title={t('dashboards.service.orderFieldsTitle')}
          subtitle={t('dashboards.service.orderFieldsSubtitle')}
          emptyHint={t('dashboards.service.orderFieldsEmpty')}
        />
        <div className="flex justify-end -mt-2">
          <button type="button" onClick={saveProduct}
            disabled={savingProduct}
            className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
          >{savingProduct ? t('dashboards.common.saving') : t('dashboards.service.orderFieldsSave', { defaultValue: 'Salva campi' })}</button>
        </div>
      </div>
    </div>
  );
}
