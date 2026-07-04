/**
 * TrackingDialog — prompt admin for carrier tracking when marking an order as
 * "shipped" (Release 1 Physical).
 *
 * The dialog auto-generates a tracking URL from a template the admin picks
 * (Poste, DHL, GLS, UPS, FedEx, Amazon) by substituting the `{code}` token
 * with the typed tracking number. A "Custom URL" option lets the admin paste
 * a ready-made link (or leave it blank — only the number will travel to the
 * customer email).
 *
 * Both fields are optional: the admin can confirm without any tracking at all
 * (status still transitions to `shipped`) so flows without tracking data stay
 * one click away.
 */

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Truck, Loader2 } from 'lucide-react';


// URL templates keyed by provider. `{code}` is the placeholder substituted by
// the typed tracking number. `custom` is a free-text path — the admin pastes
// the already-built URL.
const PROVIDERS = [
  { key: 'auto',    labelKey: 'fulfillment.tracking_provider_auto',    template: '' },
  { key: 'poste',   labelKey: 'fulfillment.tracking_provider_poste',   template: 'https://www.poste.it/cerca/index.html#/risultati-spedizioni/{code}' },
  { key: 'brt',     labelKey: 'fulfillment.tracking_provider_brt',     template: 'https://vas.brt.it/vas/sped_det_show.hsm?Nspediz={code}' },
  { key: 'gls',     labelKey: 'fulfillment.tracking_provider_gls',     template: 'https://www.gls-italy.com/ita/servizi-on-line/ricerca-spedizioni?locnumber={code}' },
  { key: 'sda',     labelKey: 'fulfillment.tracking_provider_sda',     template: 'https://www.sda.it/wps/portal/Servizi_online/ricerca_spedizioni?locale=it&tracing_number={code}' },
  { key: 'dhl',     labelKey: 'fulfillment.tracking_provider_dhl',     template: 'https://www.dhl.com/global-en/home/tracking/tracking-parcel.html?submit=1&tracking-id={code}' },
  { key: 'ups',     labelKey: 'fulfillment.tracking_provider_ups',     template: 'https://www.ups.com/track?loc=it_IT&tracknum={code}' },
  { key: 'fedex',   labelKey: 'fulfillment.tracking_provider_fedex',   template: 'https://www.fedex.com/fedextrack/?trknbr={code}' },
  { key: 'amazon',  labelKey: 'fulfillment.tracking_provider_amazon',  template: 'https://track.amazon.com/tracking/{code}' },
  { key: 'custom',  labelKey: 'fulfillment.tracking_provider_custom',  template: '' },
];


/**
 * @param {object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {(tracking: {tracking_number?: string, tracking_url?: string}) => Promise<void>} props.onConfirm
 * @param {string} [props.orderRef]  optional label shown in the header
 * @param {boolean} [props.submitting] disables the confirm button while API is in flight
 */
export default function TrackingDialog({
  open, onClose, onConfirm, orderRef, submitting = false,
}) {
  const { t } = useTranslation('orders');
  const [provider, setProvider] = useState('auto');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [customUrl, setCustomUrl] = useState('');

  const computedUrl = useMemo(() => {
    if (provider === 'custom') return customUrl.trim();
    if (provider === 'auto') return '';
    const tpl = PROVIDERS.find(p => p.key === provider)?.template || '';
    const code = trackingNumber.trim();
    if (!tpl || !code) return '';
    return tpl.replace('{code}', encodeURIComponent(code));
  }, [provider, trackingNumber, customUrl]);

  const handleClose = () => {
    if (submitting) return;
    setProvider('auto');
    setTrackingNumber('');
    setCustomUrl('');
    onClose?.();
  };

  const handleConfirm = async () => {
    const payload = {};
    const code = trackingNumber.trim();
    if (code) payload.tracking_number = code;
    if (computedUrl) payload.tracking_url = computedUrl;
    await onConfirm(payload);
    // Parent is responsible for closing on success; reset local state here so
    // the next open starts clean.
    setProvider('auto');
    setTrackingNumber('');
    setCustomUrl('');
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Truck className="h-4 w-4" />
            {t('fulfillment.tracking_dialog_title', { defaultValue: 'Segna come spedito' })}
          </DialogTitle>
          {orderRef && (
            <p className="text-xs text-muted-foreground">
              {t('fulfillment.tracking_dialog_ref', { defaultValue: 'Ordine' })} {orderRef}
            </p>
          )}
        </DialogHeader>

        <div className="space-y-3 py-2">
          <p className="text-xs text-muted-foreground">
            {t('fulfillment.tracking_dialog_hint', {
              defaultValue: 'Aggiungi il codice tracking per permettere al cliente di seguire il pacco. Entrambi i campi sono opzionali.',
            })}
          </p>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              {t('fulfillment.tracking_number_label', { defaultValue: 'Codice tracking' })}
            </label>
            <input
              type="text"
              value={trackingNumber}
              onChange={(e) => setTrackingNumber(e.target.value)}
              placeholder="es. 1Z999AA10123456784"
              maxLength={120}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              {t('fulfillment.tracking_provider_label', { defaultValue: 'Corriere' })}
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            >
              {PROVIDERS.map(p => (
                <option key={p.key} value={p.key}>
                  {t(p.labelKey, { defaultValue: p.key })}
                </option>
              ))}
            </select>
          </div>

          {provider === 'custom' && (
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                {t('fulfillment.tracking_url_label', { defaultValue: 'URL di tracking' })}
              </label>
              <input
                type="url"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder="https://..."
                maxLength={500}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </div>
          )}

          {computedUrl && provider !== 'custom' && (
            <p className="text-[11px] text-gray-500 break-all">
              {t('fulfillment.tracking_url_preview', { defaultValue: 'Anteprima URL' })}: {computedUrl}
            </p>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={handleClose} disabled={submitting}>
            {t('fulfillment.tracking_cancel', { defaultValue: 'Annulla' })}
          </Button>
          <Button onClick={handleConfirm} disabled={submitting} className="gap-2">
            {submitting && <Loader2 className="h-3 w-3 animate-spin" />}
            {t('fulfillment.tracking_confirm', { defaultValue: 'Conferma spedizione' })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
