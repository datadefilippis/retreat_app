import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../../components/ui/table';
import {
  Mic, Loader2, RefreshCw, ArrowUp, ArrowDown, Trash2, Youtube,
  BadgeCheck, ExternalLink,
} from 'lucide-react';
import { adminAPI } from '../../api';
import { toast } from 'sonner';

/**
 * InterviewsTab (PV2) — l'intervista la scrive e pubblica il system admin.
 *
 * Lista org con stato intervista (nessuna/bozza/pubblicata) + editor:
 * Q&A (max 12, 200/2500), video YouTube opzionale (normalizzato dal
 * backend), Salva bozza / Pubblica / Spubblica / Rimuovi. La PRIMA
 * pubblicazione timbra interview_verified_at: la verità del badge
 * Verificato Aurya (PV4).
 */

const MAX_QA = 12;

// Specchio client della normalizzazione backend: serve solo per
// l'anteprima dell'ID riconosciuto, la verità resta nel PUT (422).
const ytVideoId = (url) => {
  const m = String(url || '').match(
    /^https?:\/\/(?:(?:www\.|m\.)?youtube\.com\/watch\?(?:[^#]*&)?v=|youtu\.be\/|(?:www\.|m\.)?youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})(?:[?&#/]|$)/
  );
  return m ? m[1] : null;
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('it-IT', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return iso; }
};

const STATUS_BADGE = {
  published: (
    <Badge className="bg-[#376254] hover:bg-[#376254] text-white">
      <BadgeCheck className="mr-1 h-3 w-3" /> Pubblicata
    </Badge>
  ),
  draft: (
    <Badge variant="outline" className="border-amber-400 text-amber-700">
      Bozza
    </Badge>
  ),
  none: <span className="text-muted-foreground text-sm">—</span>,
};

const InterviewsTab = () => {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  // ── Editor ──
  const [editorOrg, setEditorOrg] = useState(null);   // {id, name}
  const [editorLoading, setEditorLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [videoUrl, setVideoUrl] = useState('');
  const [published, setPublished] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState(null);
  const [slug, setSlug] = useState(null);
  const [saving, setSaving] = useState(false);

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminAPI.listOrganizations(0, 200);
      setOrgs(res.data.items || []);
    } catch {
      toast.error('Impossibile caricare le organizzazioni');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchOrgs(); }, [fetchOrgs]);

  const openEditor = async (org) => {
    setEditorOrg({ id: org.id, name: org.name });
    setEditorLoading(true);
    try {
      const data = await adminAPI.getOrgInterview(org.id);
      setItems((data.items || []).map(qa => ({ ...qa })));
      setVideoUrl(data.video_url || '');
      setPublished(Boolean(data.published));
      setVerifiedAt(data.verified_at || null);
      setSlug(data.public_slug || null);
    } catch {
      toast.error("Impossibile caricare l'intervista");
      setEditorOrg(null);
    } finally {
      setEditorLoading(false);
    }
  };

  const closeEditor = () => { if (!saving) setEditorOrg(null); };

  const setQa = (i, field, val) => setItems(prev => {
    const next = [...prev];
    next[i] = { ...next[i], [field]: val };
    return next;
  });

  const moveQa = (i, dir) => setItems(prev => {
    const j = i + dir;
    if (j < 0 || j >= prev.length) return prev;
    const next = [...prev];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  });

  const validItems = items.filter(
    qa => (qa.question || '').trim() && (qa.answer || '').trim());
  const videoId = ytVideoId(videoUrl);
  const videoInvalid = Boolean((videoUrl || '').trim()) && !videoId;

  const save = async (publish, { removed = false } = {}) => {
    if (videoInvalid) {
      toast.error('Link video non valido: serve un URL YouTube (youtube.com/watch, youtu.be o shorts)');
      return;
    }
    setSaving(true);
    try {
      const data = await adminAPI.setOrgInterview(editorOrg.id, {
        items: validItems,
        video_url: (videoUrl || '').trim() || null,
        published: publish,
      });
      setItems((data.items || []).map(qa => ({ ...qa })));
      setVideoUrl(data.video_url || '');
      setPublished(Boolean(data.published));
      setVerifiedAt(data.verified_at || null);
      toast.success(removed
        ? 'Intervista rimossa'
        : publish
          ? 'Intervista pubblicata: operatore verificato'
          : published && !publish
            ? 'Intervista spubblicata (badge rimosso)'
            : 'Bozza salvata');
      if (removed) setEditorOrg(null);
      fetchOrgs();
    } catch (err) {
      const msg = err?.response?.data?.detail;
      toast.error(typeof msg === 'string' && msg ? msg : 'Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const unpublish = () => {
    if (!window.confirm('Spubblicare l’intervista? L’operatore perde il badge Verificato e la sezione sparisce dal profilo pubblico.')) return;
    save(false);
  };

  const removeInterview = () => {
    if (!window.confirm('Rimuovere DEL TUTTO l’intervista (domande, video e stato)? L’operazione svuota anche la bozza.')) return;
    setItems([]);
    setVideoUrl('');
    // lo svuotamento passa dal PUT: items vuoti + published false
    setSaving(true);
    adminAPI.setOrgInterview(editorOrg.id, { items: [], video_url: null, published: false })
      .then(() => {
        toast.success('Intervista rimossa');
        setEditorOrg(null);
        fetchOrgs();
      })
      .catch(() => toast.error('Errore nella rimozione'))
      .finally(() => setSaving(false));
  };

  const rows = orgs.filter(o =>
    !filter.trim() || o.name.toLowerCase().includes(filter.trim().toLowerCase()));

  const counts = orgs.reduce((acc, o) => {
    acc[o.interview_status || 'none'] = (acc[o.interview_status || 'none'] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Mic className="h-5 w-5 text-[#8a7440]" /> Interviste
            </CardTitle>
            <CardDescription>
              L’intervista la realizza il team Aurya: alla pubblicazione l’operatore
              diventa Verificato ({counts.published || 0} pubblicate, {counts.draft || 0} in bozza).
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Input
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Cerca operatore…"
              className="h-9 w-full sm:w-52"
            />
            <Button variant="outline" size="sm" onClick={fetchOrgs} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Carico le organizzazioni...
            </div>
          ) : rows.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              Nessuna organizzazione trovata.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Operatore</TableHead>
                    <TableHead>Intervista</TableHead>
                    <TableHead>Verificato dal</TableHead>
                    <TableHead className="text-right">Azione</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map(o => (
                    <TableRow key={o.id} data-testid={`interview-row-${o.id}`}>
                      <TableCell className="font-medium">{o.name}</TableCell>
                      <TableCell>{STATUS_BADGE[o.interview_status] || STATUS_BADGE.none}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {fmtDate(o.interview_verified_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditor(o)}>
                          Apri
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Editor ── */}
      <Dialog open={Boolean(editorOrg)} onOpenChange={open => { if (!open) closeEditor(); }}>
        <DialogContent className="max-w-2xl max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex flex-wrap items-center gap-2 pr-6">
              <Mic className="h-4 w-4 text-[#8a7440]" />
              {editorOrg?.name}
              {published ? (
                <Badge className="bg-[#376254] hover:bg-[#376254] text-white">
                  <BadgeCheck className="mr-1 h-3 w-3" /> Pubblicata
                </Badge>
              ) : (
                <Badge variant="outline" className="border-amber-400 text-amber-700">
                  Non pubblicata
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {editorLoading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Carico l’intervista...
            </div>
          ) : (
            <div className="space-y-4">
              {published && verifiedAt && (
                <p className="text-xs text-muted-foreground">
                  Verificato dal {fmtDate(verifiedAt)}
                  {slug && (
                    <a href={`/o/${slug}#intervista`} target="_blank" rel="noreferrer"
                       className="ml-2 inline-flex items-center gap-1 text-[#376254] hover:underline">
                      Vedi sul profilo <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </p>
              )}

              {/* Video YouTube */}
              <div className="rounded-lg border p-3 space-y-1.5">
                <Label className="flex items-center gap-1.5">
                  <Youtube className="h-4 w-4 text-red-600" /> Video YouTube (opzionale)
                </Label>
                <Input
                  value={videoUrl}
                  onChange={e => setVideoUrl(e.target.value)}
                  placeholder="https://youtu.be/… oppure https://www.youtube.com/watch?v=…"
                  data-testid="interview-video-input"
                />
                {videoId ? (
                  <p className="text-xs text-[#376254]">
                    ✓ Video riconosciuto — ID <code className="font-mono">{videoId}</code>{' '}
                    (salvato come youtube.com/watch?v={videoId})
                  </p>
                ) : videoInvalid ? (
                  <p className="text-xs text-destructive">
                    Non sembra un link YouTube valido (accettati: youtube.com/watch, youtu.be, shorts).
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Solo YouTube: youtube.com/watch, youtu.be o youtube.com/shorts.
                  </p>
                )}
              </div>

              {/* Q&A */}
              <div className="space-y-3">
                <Label>Domande e risposte ({validItems.length}/{MAX_QA})</Label>
                {items.map((qa, i) => (
                  <div key={i} className="rounded-lg border p-3 space-y-2">
                    <div className="flex items-start gap-1.5">
                      <input
                        value={qa.question || ''}
                        onChange={e => setQa(i, 'question', e.target.value.slice(0, 200))}
                        placeholder="Domanda"
                        className="flex-1 min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <div className="flex shrink-0 gap-0.5">
                        <Button variant="ghost" size="icon" className="h-8 w-8"
                                disabled={i === 0} onClick={() => moveQa(i, -1)}
                                aria-label="Sposta su">
                          <ArrowUp className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8"
                                disabled={i === items.length - 1} onClick={() => moveQa(i, 1)}
                                aria-label="Sposta giù">
                          <ArrowDown className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive"
                                onClick={() => setItems(prev => prev.filter((_, j) => j !== i))}
                                aria-label="Rimuovi domanda">
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                    <textarea
                      value={qa.answer || ''}
                      onChange={e => setQa(i, 'answer', e.target.value.slice(0, 2500))}
                      rows={4}
                      placeholder="Risposta integrale (mai riassunta)"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-y"
                    />
                    <p className="text-right text-[11px] text-muted-foreground">
                      {(qa.question || '').length}/200 · {(qa.answer || '').length}/2500
                    </p>
                  </div>
                ))}
                {items.length < MAX_QA && (
                  <button type="button"
                    onClick={() => setItems(prev => [...prev, { question: '', answer: '' }])}
                    className="rounded-md border border-dashed border-border px-3 py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary w-full">
                    + Aggiungi domanda
                  </button>
                )}
              </div>

              {/* Azioni */}
              <div className="flex flex-wrap items-center gap-2 border-t pt-4">
                {published ? (
                  <>
                    <Button onClick={() => save(true)} disabled={saving || validItems.length === 0}
                            data-testid="interview-save-published">
                      {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Salva modifiche
                    </Button>
                    <Button variant="outline" onClick={unpublish} disabled={saving}
                            data-testid="interview-unpublish">
                      Spubblica
                    </Button>
                  </>
                ) : (
                  <>
                    <Button variant="outline" onClick={() => save(false)} disabled={saving}
                            data-testid="interview-save-draft">
                      {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Salva bozza
                    </Button>
                    <Button onClick={() => save(true)} disabled={saving || validItems.length === 0}
                            className="bg-[#376254] hover:bg-[#2c4f43]"
                            data-testid="interview-publish">
                      <BadgeCheck className="mr-2 h-4 w-4" /> Pubblica
                    </Button>
                  </>
                )}
                <div className="flex-1" />
                <Button variant="ghost" onClick={removeInterview} disabled={saving}
                        className="text-destructive hover:text-destructive"
                        data-testid="interview-remove">
                  <Trash2 className="mr-2 h-4 w-4" /> Rimuovi intervista
                </Button>
              </div>
              {validItems.length === 0 && (
                <p className="text-[11px] text-muted-foreground">
                  Per pubblicare serve almeno una coppia domanda+risposta completa.
                </p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default InterviewsTab;
