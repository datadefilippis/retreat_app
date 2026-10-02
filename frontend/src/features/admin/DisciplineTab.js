/**
 * DisciplineTab — le discipline dalla regia (DV2, 2/10/2026).
 *
 * Piano: docs/ANALISI_DISCIPLINE_DINAMICHE_2026-10-02.md. Il system admin
 * vede tutte le discipline per famiglia (origine codice o regia, quante
 * volte scelte), ne aggiunge una nuova con cinque campi (etichetta, famiglia,
 * categoria dei ritiri, categoria del Magazine, sinonimi) e un motivo, e
 * corregge etichetta e sinonimi o spegne una voce della regia. Regole del
 * server: slug immutabile (si vede in anteprima prima di salvare), mai
 * cancellazioni, delle voci di codice si arricchiscono solo i sinonimi.
 * Dopo ogni salvataggio il registro vivo del frontend si ricarica: la voce
 * e' subito nel selettore di tutti.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Power, Pencil, RefreshCw, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { adminAPI } from '../../api';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Skeleton } from '../../components/ui/skeleton';
import { caricaDiscipline } from '../../lib/disciplines';

const MOTIVO_MIN = 3;
const pulito = (v) => String(v || '').trim();

export default function DisciplineTab() {
  const [dati, setDati] = useState(null);
  const [errore, setErrore] = useState(false);
  const [apri, setApri] = useState(false);
  const [form, setForm] = useState({ label: '', famiglia: '', categoria: '', cat_articoli: '', sinonimi: '', motivo: '' });
  const [anteprima, setAnteprima] = useState(null);
  const [salvo, setSalvo] = useState(false);
  const [modifica, setModifica] = useState(null);   // { slug, origine, label, sinonimi, attiva, motivo }

  const carica = useCallback(async () => {
    try { setDati(await adminAPI.getDiscipline()); setErrore(false); }
    catch { setErrore(true); }
  }, []);
  useEffect(() => { carica(); }, [carica]);

  // anteprima dello slug e delle voci simili mentre si scrive l'etichetta
  useEffect(() => {
    const label = pulito(form.label);
    if (label.length < 2) { setAnteprima(null); return undefined; }
    const t = setTimeout(() => {
      adminAPI.anteprimaDisciplina(label).then(setAnteprima).catch(() => setAnteprima(null));
    }, 300);
    return () => clearTimeout(t);
  }, [form.label]);

  const rosa = dati?.rosa || { famiglie: [], categorie_ritiro: [], categorie_articoli: [] };
  const motivoOk = pulito(form.motivo).length >= MOTIVO_MIN;
  const pronto = pulito(form.label).length >= 2 && form.famiglia && form.categoria && motivoOk && anteprima?.slug_valido && !anteprima?.esiste;

  const dopoSalvataggio = async (msg) => {
    toast.success(msg);
    await carica();
    await caricaDiscipline(true);          // il registro vivo del frontend, subito
  };

  const crea = async () => {
    if (!pronto) return;
    setSalvo(true);
    try {
      await adminAPI.creaDisciplina({
        label: pulito(form.label), famiglia: form.famiglia, categoria: form.categoria,
        cat_articoli: form.cat_articoli || form.categoria, sinonimi: form.sinonimi, motivo: pulito(form.motivo),
      });
      setForm({ label: '', famiglia: '', categoria: '', cat_articoli: '', sinonimi: '', motivo: '' });
      setAnteprima(null); setApri(false);
      await dopoSalvataggio('Disciplina aggiunta: è già nel selettore di tutti gli operatori.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSalvo(false); }
  };

  const salvaModifica = async () => {
    if (!modifica || pulito(modifica.motivo).length < MOTIVO_MIN) return;
    setSalvo(true);
    try {
      const body = { motivo: pulito(modifica.motivo), sinonimi: modifica.sinonimi };
      if (modifica.origine === 'regia') { body.label = pulito(modifica.label); body.attiva = modifica.attiva; }
      await adminAPI.modificaDisciplina(modifica.slug, body);
      setModifica(null);
      await dopoSalvataggio('Disciplina aggiornata.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSalvo(false); }
  };

  const totaleRegia = useMemo(() => (dati?.extra || []).filter((d) => !d.arricchimento).length, [dati]);

  if (errore) return <p className="text-sm text-red-700">Impossibile caricare le discipline.</p>;
  if (!dati) return <Skeleton className="h-64 w-full rounded-xl" />;

  const selectCls = 'w-full rounded-md border bg-background px-3 py-2 text-sm';

  return (
    <div className="space-y-4" data-testid="admin-discipline">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{dati.totale} discipline in {dati.famiglie.length} famiglie · {totaleRegia} aggiunte dalla regia</p>
          <p className="text-xs text-muted-foreground">
            {dati.vive
              ? 'Registro vivo acceso: quello che salvi qui è subito disponibile a tutti, senza deploy.'
              : 'Registro vivo SPENTO sul server (DISCIPLINE_VIVE): puoi preparare le voci, ma gli operatori vedono solo quelle di codice.'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={carica}><RefreshCw className="h-3.5 w-3.5 mr-1.5" />Aggiorna</Button>
          <Button size="sm" onClick={() => setApri((v) => !v)} data-testid="admin-discipline-aggiungi">
            <Plus className="h-3.5 w-3.5 mr-1.5" />Aggiungi disciplina
          </Button>
        </div>
      </div>

      {apri && (
        <form className="rounded-xl border border-[#376254]/30 bg-[#376254]/5 p-4 space-y-3 text-sm"
          data-testid="admin-discipline-form" onSubmit={(e) => { e.preventDefault(); crea(); }}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="dd-label">Nome (come lo leggerà la gente)</Label>
              <Input id="dd-label" value={form.label} maxLength={60} placeholder="es. Massaggio svedese"
                onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))} data-testid="admin-discipline-label" />
              {anteprima && (
                <p className="mt-1 text-[11px] text-muted-foreground" data-testid="admin-discipline-slug">
                  Identificativo (fisso dopo il salvataggio): <code>{anteprima.slug || '—'}</code>
                  {anteprima.esiste && <span className="text-red-700"> · esiste già</span>}
                  {anteprima.simili?.length > 0 && !anteprima.esiste && (
                    <span className="text-amber-700"> · simili: {anteprima.simili.map((s) => s.label).join(', ')}</span>
                  )}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="dd-fam">Famiglia</Label>
              <select id="dd-fam" className={selectCls} value={form.famiglia} data-testid="admin-discipline-famiglia"
                onChange={(e) => setForm((f) => ({ ...f, famiglia: e.target.value }))}>
                <option value="">— scegli —</option>
                {rosa.famiglie.map((f) => <option key={f.slug} value={f.slug}>{f.label}</option>)}
              </select>
            </div>
            <div>
              <Label htmlFor="dd-cat">Categoria dei ritiri (filtri della directory)</Label>
              <select id="dd-cat" className={selectCls} value={form.categoria} data-testid="admin-discipline-categoria"
                onChange={(e) => setForm((f) => ({ ...f, categoria: e.target.value }))}>
                <option value="">— scegli —</option>
                {rosa.categorie_ritiro.map((c) => <option key={c.slug} value={c.slug}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <Label htmlFor="dd-art">Categoria del Magazine (articoli e pagine locali)</Label>
              <select id="dd-art" className={selectCls} value={form.cat_articoli} data-testid="admin-discipline-articoli"
                onChange={(e) => setForm((f) => ({ ...f, cat_articoli: e.target.value }))}>
                <option value="">— come la categoria dei ritiri —</option>
                {rosa.categorie_articoli.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="dd-sin">Parole per la ricerca (sinonimi, separati da virgola)</Label>
            <Textarea id="dd-sin" rows={2} value={form.sinonimi} placeholder="es. svedese, massaggio rilassante, decontratturante"
              onChange={(e) => setForm((f) => ({ ...f, sinonimi: e.target.value }))} data-testid="admin-discipline-sinonimi" />
          </div>
          <div>
            <Label htmlFor="dd-motivo">Motivo (resta nel registro)</Label>
            <Input id="dd-motivo" value={form.motivo} maxLength={300} placeholder="es. richiesta dell'operatrice X del 2/10"
              onChange={(e) => setForm((f) => ({ ...f, motivo: e.target.value }))} data-testid="admin-discipline-motivo" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              {pulito(form.label) && anteprima?.slug ? `Si troverà cercando: ${[pulito(form.label), ...pulito(form.sinonimi).split(',').map((s) => s.trim()).filter(Boolean)].join(', ')}` : 'Compila nome, famiglia, categoria e motivo.'}
            </span>
            <Button type="submit" size="sm" disabled={!pronto || salvo} data-testid="admin-discipline-salva">
              {salvo ? 'Salvo…' : 'Salva e rendi disponibile'}
            </Button>
          </div>
        </form>
      )}

      {modifica && (
        <form className="rounded-xl border p-4 space-y-3 text-sm" data-testid="admin-discipline-modifica"
          onSubmit={(e) => { e.preventDefault(); salvaModifica(); }}>
          <p className="font-semibold">
            <Pencil className="inline h-3.5 w-3.5 mr-1" />{modifica.origine === 'regia' ? 'Modifica' : 'Sinonimi in più per'} <code>{modifica.slug}</code>
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {modifica.origine === 'regia' && (
              <div>
                <Label>Nome</Label>
                <Input value={modifica.label} maxLength={60} onChange={(e) => setModifica((m) => ({ ...m, label: e.target.value }))} />
              </div>
            )}
            <div className={modifica.origine === 'regia' ? '' : 'sm:col-span-2'}>
              <Label>Sinonimi (virgola)</Label>
              <Input value={modifica.sinonimi} onChange={(e) => setModifica((m) => ({ ...m, sinonimi: e.target.value }))} />
            </div>
            {modifica.origine === 'regia' && (
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={!!modifica.attiva} onChange={(e) => setModifica((m) => ({ ...m, attiva: e.target.checked }))} />
                Attiva nel selettore (spenta: resta valida per chi l’ha già scelta)
              </label>
            )}
            <div className={modifica.origine === 'regia' ? '' : 'sm:col-span-2'}>
              <Label>Motivo</Label>
              <Input value={modifica.motivo} maxLength={300} onChange={(e) => setModifica((m) => ({ ...m, motivo: e.target.value }))} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setModifica(null)}>Annulla</Button>
            <Button type="submit" size="sm" disabled={salvo || pulito(modifica.motivo).length < MOTIVO_MIN}>Salva</Button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {dati.famiglie.map((fam) => (
          <div key={fam.slug} className="rounded-xl border p-3" data-testid={`admin-discipline-famiglia-${fam.slug}`}>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">{fam.label} · {fam.items.length}</p>
            <ul className="divide-y">
              {fam.items.map((d) => (
                <li key={d.slug} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 text-sm" data-testid={`admin-discipline-riga-${d.slug}`}>
                  <span className={`font-medium ${d.attiva ? '' : 'line-through text-muted-foreground'}`}>{d.label}</span>
                  <code className="text-[11px] text-muted-foreground">{d.slug}</code>
                  {d.origine === 'regia' && <span className="rounded-full bg-[#faf6ec] px-2 py-0.5 text-[10px] text-[#8a7440]"><Sparkles className="inline h-3 w-3 mr-0.5" />regia</span>}
                  <span className="text-[11px] text-muted-foreground">{d.usi} {d.usi === 1 ? 'profilo' : 'profili'}</span>
                  {d.sinonimi_extra?.length > 0 && <span className="text-[11px] text-muted-foreground">+ {d.sinonimi_extra.join(', ')}</span>}
                  <button type="button" className="ml-auto text-[11px] underline text-muted-foreground hover:text-foreground"
                    onClick={() => setModifica({ slug: d.slug, origine: d.origine, label: d.label, sinonimi: (d.sinonimi_extra || []).join(', '), attiva: d.attiva, motivo: '' })}>
                    {d.origine === 'regia' ? 'Modifica' : 'Sinonimi'}
                  </button>
                  {d.origine === 'regia' && !d.attiva && <Power className="h-3 w-3 text-muted-foreground" aria-label="spenta" />}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
