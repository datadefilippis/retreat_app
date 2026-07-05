/**
 * RetreatContentEditor — editor dei contenuti della pagina di vendita
 * (Fase 3 retreat): programma giorno-per-giorno, galleria, incluso/escluso,
 * FAQ. Un'unica card nella dashboard del ritiro, un solo Salva (PATCH
 * occurrence). I contenuti rendono live sulla landing pubblica.
 *
 * Multilingua manuale (decisione founder 6/7/2026, zero LLM): tab per
 * lingua in cima alla card. In Italiano si gestisce la STRUTTURA
 * (giorni, voci, orari, foto, quante FAQ); nelle tab EN/DE/FR si
 * traducono SOLO i testi, col testo italiano come placeholder. I testi
 * non tradotti restano in italiano sulla landing (fallback per campo);
 * se la struttura cambia dopo la traduzione, il blocco sfasato torna
 * italiano intero (guardia di cardinalità nel backend).
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { eventOccurrencesAPI } from '../../../api/eventOccurrences';

const EMPTY_ITEM = { time: '', title: '', description: '' };

const LANGS = [
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

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

  // Tab lingua attiva + traduzioni in editing. trContent è indicizzato
  // sugli indici dello stato di editing (giorno di, voce ii, faq i):
  // al salvataggio viene proiettato sulle stesse righe che finiscono
  // nel payload italiano, così gli indici restano allineati.
  const [contentLang, setContentLang] = useState('it');
  const [trContent, setTrContent] = useState({});

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
    // Idratazione traduzioni: gli array salvati sono allineati alla
    // struttura salvata (nessuna riga vuota), quindi gli indici
    // combaciano con lo stato di editing appena idratato.
    const tr = {};
    Object.entries(occurrence.translations || {}).forEach(([lang, blocks]) => {
      const entry = {};
      if (Array.isArray(blocks.agenda)) {
        entry.agenda = {};
        blocks.agenda.forEach((d, di) => {
          const items = {};
          (d?.items || []).forEach((x, ii) => {
            items[ii] = { title: x?.title || '', description: x?.description || '' };
          });
          entry.agenda[di] = { label: d?.label || '', items };
        });
      }
      if (Array.isArray(blocks.included)) entry.included = blocks.included.join('\n');
      if (Array.isArray(blocks.excluded)) entry.excluded = blocks.excluded.join('\n');
      if (Array.isArray(blocks.faq)) {
        entry.faq = {};
        blocks.faq.forEach((e, i) => { entry.faq[i] = { q: e?.q || '', a: e?.a || '' }; });
      }
      tr[lang] = entry;
    });
    setTrContent(tr);
    setDirty(false);
  }, [occurrence]);

  const touch = (fn) => (...args) => { setDirty(true); fn(...args); };

  // Aggiorna un pezzo di traduzione per la lingua attiva.
  const setTr = (updater) => {
    setDirty(true);
    setTrContent(prev => {
      const cur = prev[contentLang] || {};
      return { ...prev, [contentLang]: updater(cur) };
    });
  };
  const curTr = trContent[contentLang] || {};

  // La lingua ha almeno un testo compilato? (pallino sulla tab)
  const langHasContent = (lang) => {
    const e = trContent[lang];
    if (!e) return false;
    if ((e.included || '').trim() || (e.excluded || '').trim()) return true;
    if (Object.values(e.agenda || {}).some(d => (d.label || '').trim()
        || Object.values(d.items || {}).some(x => (x.title || '').trim() || (x.description || '').trim()))) return true;
    if (Object.values(e.faq || {}).some(x => (x.q || '').trim() || (x.a || '').trim())) return true;
    return false;
  };

  const save = async () => {
    setSaving(true);
    try {
      // Righe sorgente che entrano nel payload (stessa logica del filtro
      // sotto): servono anche per proiettare le traduzioni sugli stessi
      // indici, così backend e landing restano allineati.
      const srcDays = agenda
        .map((d, di) => ({ d, di }))
        .filter(({ d }) => d.label.trim())
        .map(({ d, di }) => ({
          di,
          label: d.label.trim(),
          items: d.items.map((i, ii) => ({ i, ii })).filter(({ i }) => i.title.trim()),
        }));
      const srcFaq = faq
        .map((f, i) => ({ f, i }))
        .filter(({ f }) => f.q.trim() && f.a.trim());

      const translations = {};
      Object.entries(trContent).forEach(([lang, e]) => {
        if (lang === 'it' || !e) return;
        const out = {};
        const trA = e.agenda || {};
        const days = srcDays.map(({ di, items }) => {
          const td = trA[di] || {};
          return {
            label: (td.label || '').trim() || null,
            items: items.map(({ ii }) => ({
              title: (td.items?.[ii]?.title || '').trim() || null,
              description: (td.items?.[ii]?.description || '').trim() || null,
            })),
          };
        });
        if (days.some(d => d.label || d.items.some(x => x.title || x.description))) {
          out.agenda = days;
        }
        // Liste riga-per-riga: la traduzione deve avere lo stesso numero
        // di righe della sorgente perché il merge è per indice; righe
        // mancanti restano vuote (→ fallback italiano su quella riga).
        const srcInc = linesToList(includedText);
        const srcExc = linesToList(excludedText);
        const trInc = (e.included || '').split('\n').map(s => s.trim());
        const trExc = (e.excluded || '').split('\n').map(s => s.trim());
        if (srcInc.length && trInc.some(Boolean)) {
          out.included = srcInc.map((_, i) => trInc[i] || '');
        }
        if (srcExc.length && trExc.some(Boolean)) {
          out.excluded = srcExc.map((_, i) => trExc[i] || '');
        }
        const trF = e.faq || {};
        const entries = srcFaq.map(({ i }) => ({
          q: (trF[i]?.q || '').trim() || null,
          a: (trF[i]?.a || '').trim() || null,
        }));
        if (entries.some(x => x.q || x.a)) out.faq = entries;
        if (Object.keys(out).length) translations[lang] = out;
      });

      const payload = {
        agenda: srcDays.map(({ label, items }) => ({
          label,
          items: items.map(({ i }) => ({
            time: i.time?.trim() || null,
            title: i.title.trim(),
            description: i.description?.trim() || null,
          })),
        })),
        gallery_urls: gallery.filter(Boolean).slice(0, 12),
        included: linesToList(includedText),
        excluded: linesToList(excludedText),
        faq: srcFaq.map(({ f }) => ({ q: f.q.trim(), a: f.a.trim() })),
        translations,
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

  const isIt = contentLang === 'it';

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
      <p className="text-xs text-gray-500 mb-3">{t('dashboards.event.content.subtitle')}</p>

      {/* ── Tab lingua ── */}
      <div className="flex items-center gap-1 mb-4 border-b border-gray-100 pb-2">
        {LANGS.map(l => (
          <button
            key={l.code}
            type="button"
            onClick={() => setContentLang(l.code)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              contentLang === l.code
                ? 'bg-gray-900 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span aria-hidden className="mr-1">{l.flag}</span>{l.label}
            {l.code !== 'it' && langHasContent(l.code) && (
              <span className={`ml-1 ${contentLang === l.code ? 'text-white/80' : 'text-emerald-600'}`}>●</span>
            )}
          </button>
        ))}
      </div>

      {!isIt && (
        <p className="text-[11px] text-gray-400 mb-4">
          {t('dashboards.event.content.trHint', {
            defaultValue: 'Traduci solo i testi: struttura, orari e foto si gestiscono in Italiano. I campi lasciati vuoti restano in italiano sulla pagina pubblica.',
          })}
        </p>
      )}

      {isIt ? (<>
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
      </>) : (<>
      {/* ═══ Vista traduzione: stessa struttura, solo testi ═══ */}

      {/* ── Programma (traduzione) ── */}
      {agenda.length > 0 && (
        <section className="mb-5">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
            {t('dashboards.event.content.agendaHeading')}
          </h3>
          <div className="space-y-3">
            {agenda.map((day, di) => (
              <div key={di} className="rounded-lg border border-gray-200 p-3">
                <input
                  className={`${inputCls} mb-2`}
                  placeholder={day.label || t('dashboards.event.content.dayLabelPh')}
                  value={curTr.agenda?.[di]?.label || ''}
                  onChange={e => setTr(cur => ({
                    ...cur,
                    agenda: { ...(cur.agenda || {}), [di]: {
                      ...(cur.agenda?.[di] || {}), label: e.target.value,
                    } },
                  }))}
                />
                <div className="space-y-1.5">
                  {day.items.map((item, ii) => (
                    <div key={ii} className="flex gap-1.5 items-center">
                      <span className="w-14 shrink-0 text-xs text-gray-400 text-right pr-1">
                        {item.time || '—'}
                      </span>
                      <input
                        className={inputCls}
                        placeholder={item.title || t('dashboards.event.content.itemTitlePh')}
                        value={curTr.agenda?.[di]?.items?.[ii]?.title || ''}
                        onChange={e => setTr(cur => ({
                          ...cur,
                          agenda: { ...(cur.agenda || {}), [di]: {
                            ...(cur.agenda?.[di] || {}),
                            items: { ...(cur.agenda?.[di]?.items || {}), [ii]: {
                              ...(cur.agenda?.[di]?.items?.[ii] || {}), title: e.target.value,
                            } },
                          } },
                        }))}
                      />
                      <input
                        className={inputCls}
                        placeholder={item.description || t('dashboards.event.content.itemDescPh')}
                        value={curTr.agenda?.[di]?.items?.[ii]?.description || ''}
                        onChange={e => setTr(cur => ({
                          ...cur,
                          agenda: { ...(cur.agenda || {}), [di]: {
                            ...(cur.agenda?.[di] || {}),
                            items: { ...(cur.agenda?.[di]?.items || {}), [ii]: {
                              ...(cur.agenda?.[di]?.items?.[ii] || {}), description: e.target.value,
                            } },
                          } },
                        }))}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Incluso / Non incluso (traduzione) ── */}
      {(includedText.trim() || excludedText.trim()) && (
        <section className="mb-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {includedText.trim() && (
            <div>
              <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                {t('dashboards.event.content.includedHeading')}
              </h3>
              <textarea
                rows={Math.max(4, linesToList(includedText).length)}
                className={inputCls}
                placeholder={includedText}
                value={curTr.included || ''}
                onChange={e => setTr(cur => ({ ...cur, included: e.target.value }))}
              />
              <p className="text-[11px] text-gray-400 mt-1">
                {t('dashboards.event.content.trLineHint', {
                  defaultValue: 'Una riga per voce, nello stesso ordine dell’italiano.',
                })}
              </p>
            </div>
          )}
          {excludedText.trim() && (
            <div>
              <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                {t('dashboards.event.content.excludedHeading')}
              </h3>
              <textarea
                rows={Math.max(4, linesToList(excludedText).length)}
                className={inputCls}
                placeholder={excludedText}
                value={curTr.excluded || ''}
                onChange={e => setTr(cur => ({ ...cur, excluded: e.target.value }))}
              />
            </div>
          )}
        </section>
      )}

      {/* ── FAQ (traduzione) ── */}
      {faq.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
            FAQ
          </h3>
          <div className="space-y-2">
            {faq.map((entry, i) => (
              <div key={i} className="flex gap-1.5">
                <input
                  className={inputCls}
                  placeholder={entry.q || t('dashboards.event.content.faqQPh')}
                  value={curTr.faq?.[i]?.q || ''}
                  onChange={e => setTr(cur => ({
                    ...cur,
                    faq: { ...(cur.faq || {}), [i]: { ...(cur.faq?.[i] || {}), q: e.target.value } },
                  }))}
                />
                <input
                  className={inputCls}
                  placeholder={entry.a || t('dashboards.event.content.faqAPh')}
                  value={curTr.faq?.[i]?.a || ''}
                  onChange={e => setTr(cur => ({
                    ...cur,
                    faq: { ...(cur.faq || {}), [i]: { ...(cur.faq?.[i] || {}), a: e.target.value } },
                  }))}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {agenda.length === 0 && !includedText.trim() && !excludedText.trim() && faq.length === 0 && (
        <p className="text-xs text-gray-400 py-6 text-center">
          {t('dashboards.event.content.trEmpty', {
            defaultValue: 'Prima compila i contenuti in Italiano: qui appariranno gli stessi campi da tradurre.',
          })}
        </p>
      )}
      </>)}
    </div>
  );
}
