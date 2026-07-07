/**
 * BlogAdminTab — AN5: il blog di Aurya si scrive da qui.
 *
 * Lista articoli (bozze e pubblicati) + editor inline sul pattern
 * multilingua unificato: campi italiani sempre visibili, traduzioni
 * en/de/fr nelle tab di MultiLangSection (translationsOnly), anteprima
 * markdown con lo stesso renderer delle pagine legal. Scrive solo il
 * system admin; il backend rifiuta comunque chi non lo è.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import api from '../../api/client';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import MultiLangSection from '../../components/MultiLangSection';
import LegalMarkdownRenderer from '../../components/legal/LegalMarkdownRenderer';

const EMPTY = {
  title: '',
  description: '',
  content: '',
  category: '',
  featured_image_url: '',
};

const inputCls = 'w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none';

export default function BlogAdminTab() {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // editing: null = lista, 'new' = creazione, {doc} = modifica
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [titleTr, setTitleTr] = useState({});
  const [descTr, setDescTr] = useState({});
  const [contentTr, setContentTr] = useState({});
  const [preview, setPreview] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/admin/articles');
      setItems(res.data?.items || []);
      setCategories(res.data?.categories || {});
    } catch (e) {
      setError('Impossibile caricare gli articoli.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openEditor = async (item) => {
    setPreview(false);
    if (!item) {
      setForm(EMPTY);
      setTitleTr({}); setDescTr({}); setContentTr({});
      setEditing('new');
      return;
    }
    // la lista non porta il content: si rilegge il documento intero
    const res = await api.get(`/admin/articles/${item.id}`);
    const doc = res.data;
    setForm({
      title: doc.title || '',
      description: doc.description || '',
      content: doc.content || '',
      category: doc.category || '',
      featured_image_url: doc.featured_image_url || '',
    });
    const tr = doc.translations || {};
    const pick = (field) => Object.fromEntries(
      Object.entries(tr).map(([l, v]) => [l, (v || {})[field] || '']));
    setTitleTr(pick('title'));
    setDescTr(pick('description'));
    setContentTr(pick('content'));
    setEditing(doc);
  };

  const buildTranslations = () => {
    const out = {};
    for (const lang of ['en', 'de', 'fr']) {
      const entry = {
        title: (titleTr[lang] || '').trim() || null,
        description: (descTr[lang] || '').trim() || null,
        content: (contentTr[lang] || '').trim() || null,
      };
      if (entry.title || entry.description || entry.content) out[lang] = entry;
    }
    return out;
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: form.title.trim(),
        description: form.description.trim() || null,
        content: form.content,
        category: form.category || null,
        featured_image_url: form.featured_image_url.trim() || null,
        translations: buildTranslations(),
      };
      if (editing === 'new') {
        await api.post('/admin/articles', payload);
      } else {
        await api.patch(`/admin/articles/${editing.id}`, payload);
      }
      setEditing(null);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail
        ? JSON.stringify(e.response.data.detail)
        : 'Salvataggio non riuscito.');
    } finally {
      setSaving(false);
    }
  };

  const togglePublish = async (item) => {
    await api.patch(`/admin/articles/${item.id}`, { published: !item.published });
    await load();
  };

  const remove = async (item) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Eliminare definitivamente "${item.title}"?`)) return;
    await api.delete(`/admin/articles/${item.id}`);
    await load();
  };

  // ── Editor ──────────────────────────────────────────────────────────
  if (editing) {
    const isNew = editing === 'new';
    return (
      <div className="max-w-3xl space-y-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {isNew ? 'Nuovo articolo' : `Modifica: ${editing.title}`}
          </h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(null)}>
              Annulla
            </Button>
            <Button size="sm" onClick={save}
                    disabled={saving || !form.title.trim() || !form.content.trim()}
                    data-testid="article-save">
              {saving ? 'Salvataggio…' : 'Salva'}
            </Button>
          </div>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Titolo (italiano)</label>
          <input type="text" value={form.title} maxLength={180}
                 onChange={e => setForm({ ...form, title: e.target.value })}
                 className={inputCls} data-testid="article-title" />
          {!isNew && (
            <p className="mt-1 text-[11px] text-gray-400">
              Slug: /blog/{editing.slug} (cambia il titolo senza toccare lo slug: i link restano validi)
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Categoria</label>
            <select value={form.category}
                    onChange={e => setForm({ ...form, category: e.target.value })}
                    className={inputCls} data-testid="article-category">
              <option value="">Nessuna categoria</option>
              {Object.entries(categories).map(([slug, label]) => (
                <option key={slug} value={slug}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Immagine in evidenza (URL)</label>
            <input type="text" value={form.featured_image_url}
                   placeholder="https://… (vuoto: al publish si genera la cover Aurya)"
                   onChange={e => setForm({ ...form, featured_image_url: e.target.value })}
                   className={inputCls} />
            {!isNew && (
              <button type="button" data-testid="article-regen-cover"
                      onClick={async () => {
                        try {
                          const res = await api.post(`/admin/articles/${editing.id}/cover`);
                          setForm(f => ({ ...f, featured_image_url: res.data.featured_image_url }));
                        } catch { setError('Rigenerazione cover non riuscita.'); }
                      }}
                      className="mt-1.5 text-xs font-medium text-primary hover:underline">
                Rigenera la cover Aurya (sovrascrive l'immagine)
              </button>
            )}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Descrizione breve (SEO + card)</label>
          <textarea value={form.description} rows={2} maxLength={400}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    className={`${inputCls} resize-y`} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-medium text-gray-600">Contenuto (markdown)</label>
            <button type="button" onClick={() => setPreview(!preview)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              <Eye className="h-3.5 w-3.5" /> {preview ? 'Torna all\'editor' : 'Anteprima'}
            </button>
          </div>
          {preview ? (
            <div className="rounded-md border border-gray-200 bg-white p-4">
              <LegalMarkdownRenderer content={form.content || '_Nessun contenuto._'} />
            </div>
          ) : (
            <textarea value={form.content} rows={16}
                      placeholder={'## Titolo di sezione\n\nParagrafo in **markdown**…'}
                      onChange={e => setForm({ ...form, content: e.target.value })}
                      className={`${inputCls} resize-y font-mono text-xs`}
                      data-testid="article-content" />
          )}
        </div>

        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">
            Traduzioni (un articolo appare nella lista in una lingua solo se titolo e contenuto sono tradotti)
          </p>
          <MultiLangSection
            fields={[
              { key: 'title', label: 'Titolo', it: form.title, input: true, maxLength: 180, value: titleTr, onChange: setTitleTr },
              { key: 'description', label: 'Descrizione breve', it: form.description, rows: 2, maxLength: 400, value: descTr, onChange: setDescTr },
              { key: 'content', label: 'Contenuto (markdown)', it: form.content, rows: 12, value: contentTr, onChange: setContentTr },
            ]}
          />
        </div>
      </div>
    );
  }

  // ── Lista ───────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Blog</h2>
          <p className="text-sm text-gray-500">
            Articoli olistici del marketplace: la lista pubblica vive su /blog.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button size="sm" onClick={() => openEditor(null)} data-testid="article-new">
            <Plus className="h-4 w-4 mr-1" /> Nuovo articolo
          </Button>
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {items.length === 0 && !loading ? (
        <p className="text-sm text-gray-500 py-10 text-center">
          Nessun articolo ancora. Il primo semina la SEO di domani.
        </p>
      ) : (
        <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
          {items.map(item => (
            <div key={item.id} className="flex items-center gap-3 p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-gray-900 truncate">{item.title}</p>
                  <Badge variant={item.published ? 'default' : 'secondary'}>
                    {item.published ? 'Pubblicato' : 'Bozza'}
                  </Badge>
                  {item.category && (
                    <span className="text-xs text-gray-500">{categories[item.category] || item.category}</span>
                  )}
                  {(item.translated_langs || []).map(l => (
                    <span key={l} className="text-[10px] uppercase font-semibold text-emerald-600">{l}</span>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-0.5 truncate">/blog/{item.slug}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => togglePublish(item)}>
                {item.published ? 'Ritira' : 'Pubblica'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openEditor(item)} aria-label="Modifica">
                <Pencil className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => remove(item)} aria-label="Elimina"
                      className="text-red-500 hover:text-red-700">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
