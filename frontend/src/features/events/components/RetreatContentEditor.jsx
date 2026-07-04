/**
 * RetreatContentEditor — editor dei contenuti della pagina di vendita
 * (Fase 3 retreat): programma giorno-per-giorno, galleria, incluso/escluso,
 * FAQ. Un'unica card nella dashboard del ritiro, un solo Salva (PATCH
 * occurrence). I contenuti rendono live sulla landing pubblica.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { eventOccurrencesAPI } from '../../../api/eventOccurrences';

const EMPTY_ITEM = { time: '', title: '', description: '' };

function linesToList(text) {
  return text.split('\n').map(s => s.trim()).filter(Boolean).slice(0, 20);
}

export default function RetreatContentEditor({ occurrenceId, occurrence }) {
  const { t } = useTranslation('products');
  const [agenda, setAgenda] = useState([]);
  const [gallery, setGallery] = useState([]);
  const [galleryInput, setGalleryInput] = useState('');
  const [includedText, setIncludedText] = useState('');
  const [excludedText, setExcludedText] = useState('');
  const [faq, setFaq] = useState([]);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!occurrence) return;
    setAgenda((occurrence.agenda || []).map(d => ({
      label: d.label || '',
      items: (d.items || []).map(i => ({ ...EMPTY_ITEM, ...i })),
    })));
    setGallery(occurrence.gallery_urls || []);
    setIncludedText((occurrence.included || []).join('\n'));
    setExcludedText((occurrence.excluded || []).join('\n'));
    setFaq((occurrence.faq || []).map(f => ({ q: f.q || '', a: f.a || '' })));
    setDirty(false);
  }, [occurrence]);

  const touch = (fn) => (...args) => { setDirty(true); fn(...args); };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        agenda: agenda
          .filter(d => d.label.trim())
          .map(d => ({
            label: d.label.trim(),
            items: d.items
              .filter(i => i.title.trim())
              .map(i => ({
                time: i.time?.trim() || null,
                title: i.title.trim(),
                description: i.description?.trim() || null,
              })),
          })),
        gallery_urls: gallery.filter(Boolean).slice(0, 12),
        included: linesToList(includedText),
        excluded: linesToList(excludedText),
        faq: faq.filter(f => f.q.trim() && f.a.trim())
                .map(f => ({ q: f.q.trim(), a: f.a.trim() })),
      };
      await eventOccurrencesAPI.update(occurrenceId, payload);
      toast.success(t('dashboards.event.content.savedOk'));
      setDirty(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.content.savedErr'));
    } finally { setSaving(false); }
  };

  const inputCls = 'w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm focus:border-gray-900 focus:ring-gray-900';
  const smallBtn = 'rounded border border-gray-300 px-2 py-1 text-[11px] font-medium text-gray-700 hover:border-gray-900';

  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-sm font-semibold text-gray-900">
          {t('dashboards.event.content.title')}
        </h2>
        <button
          type="button"
          onClick={save}
          disabled={saving || !dirty}
          className="rounded-md bg-gray-900 text-white px-4 py-1.5 text-xs font-semibold disabled:opacity-40"
        >
          {saving ? t('dashboards.event.content.saving') : t('dashboards.event.content.save')}
        </button>
      </div>
      <p className="text-xs text-gray-500 mb-4">{t('dashboards.event.content.subtitle')}</p>

      {/* ── Programma ── */}
      <section className="mb-5">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
          {t('dashboards.event.content.agendaHeading')}
        </h3>
        <div className="space-y-3">
          {agenda.map((day, di) => (
            <div key={di} className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 mb-2">
                <input
                  className={inputCls}
                  placeholder={t('dashboards.event.content.dayLabelPh')}
                  value={day.label}
                  onChange={touch(e => setAgenda(a => a.map((d, i) =>
                    i === di ? { ...d, label: e.target.value } : d)))}
                />
                <button type="button" className={smallBtn}
                  onClick={touch(() => setAgenda(a => a.filter((_, i) => i !== di)))}>
                  ✕
                </button>
              </div>
              <div className="space-y-1.5">
                {day.items.map((item, ii) => (
                  <div key={ii} className="flex gap-1.5">
                    <input
                      className={`${inputCls} !w-20 shrink-0`}
                      placeholder="07:30"
                      value={item.time || ''}
                      onChange={touch(e => setAgenda(a => a.map((d, i) =>
                        i === di ? { ...d, items: d.items.map((x, j) =>
                          j === ii ? { ...x, time: e.target.value } : x) } : d)))}
                    />
                    <input
                      className={inputCls}
                      placeholder={t('dashboards.event.content.itemTitlePh')}
                      value={item.title}
                      onChange={touch(e => setAgenda(a => a.map((d, i) =>
                        i === di ? { ...d, items: d.items.map((x, j) =>
                          j === ii ? { ...x, title: e.target.value } : x) } : d)))}
                    />
                    <input
                      className={inputCls}
                      placeholder={t('dashboards.event.content.itemDescPh')}
                      value={item.description || ''}
                      onChange={touch(e => setAgenda(a => a.map((d, i) =>
                        i === di ? { ...d, items: d.items.map((x, j) =>
                          j === ii ? { ...x, description: e.target.value } : x) } : d)))}
                    />
                    <button type="button" className={smallBtn}
                      onClick={touch(() => setAgenda(a => a.map((d, i) =>
                        i === di ? { ...d, items: d.items.filter((_, j) => j !== ii) } : d)))}>
                      ✕
                    </button>
                  </div>
                ))}
                <button type="button" className={smallBtn}
                  onClick={touch(() => setAgenda(a => a.map((d, i) =>
                    i === di ? { ...d, items: [...d.items, { ...EMPTY_ITEM }] } : d)))}>
                  + {t('dashboards.event.content.addItem')}
                </button>
              </div>
            </div>
          ))}
          <button type="button" className={smallBtn}
            onClick={touch(() => setAgenda(a => [...a, {
              label: t('dashboards.event.content.dayLabelDefault', { n: a.length + 1 }),
              items: [{ ...EMPTY_ITEM }],
            }]))}>
            + {t('dashboards.event.content.addDay')}
          </button>
        </div>
      </section>

      {/* ── Galleria ── */}
      <section className="mb-5">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
          {t('dashboards.event.content.galleryHeading')}
        </h3>
        <div className="flex flex-wrap gap-2 mb-2">
          {gallery.map((url, i) => (
            <div key={i} className="relative">
              <img src={url} alt="" className="h-16 w-24 object-cover rounded border border-gray-200" />
              <button type="button"
                className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-gray-900 text-white text-[10px]"
                onClick={touch(() => setGallery(g => g.filter((_, j) => j !== i)))}>
                ✕
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder={t('dashboards.event.content.galleryPh')}
            value={galleryInput}
            onChange={e => setGalleryInput(e.target.value)}
          />
          <button type="button" className={smallBtn}
            onClick={touch(() => {
              const url = galleryInput.trim();
              if (url) { setGallery(g => [...g, url].slice(0, 12)); setGalleryInput(''); }
            })}>
            + {t('dashboards.event.content.addPhoto')}
          </button>
        </div>
      </section>

      {/* ── Incluso / Non incluso ── */}
      <section className="mb-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
            {t('dashboards.event.content.includedHeading')}
          </h3>
          <textarea
            rows={4}
            className={inputCls}
            placeholder={t('dashboards.event.content.listPh')}
            value={includedText}
            onChange={touch(e => setIncludedText(e.target.value))}
          />
        </div>
        <div>
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
            {t('dashboards.event.content.excludedHeading')}
          </h3>
          <textarea
            rows={4}
            className={inputCls}
            placeholder={t('dashboards.event.content.listPh')}
            value={excludedText}
            onChange={touch(e => setExcludedText(e.target.value))}
          />
        </div>
      </section>

      {/* ── FAQ ── */}
      <section>
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
          FAQ
        </h3>
        <div className="space-y-2">
          {faq.map((entry, i) => (
            <div key={i} className="flex gap-1.5">
              <input
                className={inputCls}
                placeholder={t('dashboards.event.content.faqQPh')}
                value={entry.q}
                onChange={touch(e => setFaq(f => f.map((x, j) =>
                  j === i ? { ...x, q: e.target.value } : x)))}
              />
              <input
                className={inputCls}
                placeholder={t('dashboards.event.content.faqAPh')}
                value={entry.a}
                onChange={touch(e => setFaq(f => f.map((x, j) =>
                  j === i ? { ...x, a: e.target.value } : x)))}
              />
              <button type="button" className={smallBtn}
                onClick={touch(() => setFaq(f => f.filter((_, j) => j !== i)))}>
                ✕
              </button>
            </div>
          ))}
          <button type="button" className={smallBtn}
            onClick={touch(() => setFaq(f => [...f, { q: '', a: '' }]))}>
            + {t('dashboards.event.content.addFaq')}
          </button>
        </div>
      </section>
    </div>
  );
}
