/**
 * ServiceCustomRequestForm — proposta libera di data/ora per un servizio
 * (Onda 14 Parte B).
 *
 * PN3 (PROFILO_NEGOZIO_PIANO_2026-07) — componente spostato TALE E QUALE
 * da ProductLandingPage.js (era la locale `CustomRequestForm`) cosi' che
 * l'acquisto inline sul profilo /o/ possa riusare gli stessi campi senza
 * duplicare la logica (incrementi 15 min, end_time derivato dalla durata).
 *
 * Usato quando il servizio NON ha regole di disponibilita' (o il merchant
 * consente la richiesta libera accanto alle regole). Il cliente propone
 * data/ora preferite + note. Al submit la selezione viaggia come uno slot
 * — booking_date/start/end + rental_notes — e il validatore la accetta
 * senza match di regola quando service_allow_custom_request e' attivo.
 */

import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';


export default function ServiceCustomRequestForm({ durationMinutes, value, onChange }) {
  const { t } = useTranslation('landings');
  const today = new Date();
  const minDate = today.toISOString().slice(0, 10);

  // Build 15-min increments between 08:00 and 21:00
  const timeSlots = useMemo(() => {
    const arr = [];
    for (let h = 8; h <= 21; h += 1) {
      for (const m of [0, 15, 30, 45]) {
        if (h === 21 && m > 0) break;
        arr.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
      }
    }
    return arr;
  }, []);

  const duration = durationMinutes || 60;

  const handleChange = (field, raw) => {
    const next = { ...(value || {}), [field]: raw };
    // Whenever date or start_time change, recompute end_time from duration
    if (field === 'start_time' || field === 'date') {
      const st = field === 'start_time' ? raw : (next.start_time || null);
      if (st) {
        const [h, m] = st.split(':').map(Number);
        const endMin = h * 60 + m + duration;
        const eh = Math.floor(endMin / 60) % 24;
        const em = endMin % 60;
        next.end_time = `${String(eh).padStart(2, '0')}:${String(em).padStart(2, '0')}`;
      } else {
        next.end_time = null;
      }
    }
    onChange(next);
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.preferredDate')}</span>
          <input
            type="date"
            min={minDate}
            value={value?.date || ''}
            onChange={(e) => handleChange('date', e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block">
          <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.preferredTime')}</span>
          <select
            value={value?.start_time || ''}
            onChange={(e) => handleChange('start_time', e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
          >
            <option value="">{t('landings:product.customRequest.selectPlaceholder')}</option>
            {timeSlots.map(slot => <option key={slot} value={slot}>{slot}</option>)}
          </select>
        </label>
      </div>
      <label className="block">
        <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.notesLabel')}</span>
        <textarea
          rows={2}
          placeholder={t('landings:product.customRequest.notesPlaceholder')}
          value={value?.notes || ''}
          onChange={(e) => handleChange('notes', e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
      </label>
      <p className="text-[11px] text-gray-500">
        {t('landings:product.customRequest.footerHint', { minutes: duration })}
      </p>
    </div>
  );
}
