/**
 * PC3 (24/8/2026) — /admin/sound: chi può COMPORRE in Aurya Sound.
 *
 * Pagina SEPARATA (richiesta esplicita del founder: «una nuova pagina
 * nel menu, non una sezione nella stessa pagina come facciamo
 * sempre»). Elenca le organizzazioni con lo stato del privilegio
 * `sound_composer` e i numeri del loro comporre; l'interruttore parla
 * con /api/admin/sound/composers/{org_id} e ogni cambio finisce
 * nell'audit trail.
 */
import { useEffect, useMemo, useState } from 'react';
import { Music, Search, ShieldAlert } from 'lucide-react';
import { AppLayout, Header } from '../../components/Layout';
import { Switch } from '../../components/ui/switch';
import { Input } from '../../components/ui/input';
import api from '../../api/client';

const SoundAccessPage = () => {
  const [items, setItems] = useState(null);
  const [errore, setErrore] = useState('');
  const [filtro, setFiltro] = useState('');
  const [salvando, setSalvando] = useState(null);

  const carica = async () => {
    try {
      const r = await api.get('/admin/sound/composers');
      setItems(r.data.items || []);
      setErrore('');
    } catch (e) {
      setErrore(e?.response?.data?.detail || 'Elenco non raggiungibile');
    }
  };
  useEffect(() => { carica(); }, []);

  const visibili = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    if (!q) return items || [];
    return (items || []).filter((o) =>
      (o.name || '').toLowerCase().includes(q)
      || (o.email || '').toLowerCase().includes(q)
      || (o.slug || '').toLowerCase().includes(q));
  }, [items, filtro]);

  const commuta = async (org, enabled) => {
    setSalvando(org.id);
    try {
      await api.post(`/admin/sound/composers/${org.id}`, { enabled });
      setItems((prev) => prev.map((o) =>
        (o.id === org.id ? { ...o, sound_composer: enabled } : o)));
    } catch (e) {
      setErrore(e?.response?.data?.detail || 'Salvataggio fallito');
    } finally {
      setSalvando(null);
    }
  };

  const quando = (iso) => {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('it-IT'); }
    catch { return '—'; }
  };

  return (
    <AppLayout>
      <Header
        title="Aurya Sound — Compositori"
        subtitle="Chi può creare meditazioni: il privilegio si concede da qui"
      >
        <div className="flex items-center gap-1.5 rounded-md bg-red-50 border border-red-200 px-2.5 py-1 text-xs font-medium text-red-700 shrink-0">
          <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
          <span className="hidden sm:inline">Restricted area</span>
        </div>
      </Header>

      <div className="p-4 md:p-8 animate-fade-in max-w-4xl">
        <p className="text-sm text-gray-500 mb-4">
          Le superfici pubbliche (frequenze, tutorial, meditazioni già
          pubblicate) non dipendono da questo elenco: il privilegio
          governa il <em>comporre</em>. Ogni cambio finisce nell'audit log.
        </p>

        <div className="relative mb-4 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            placeholder="Cerca per nome, email o slug…"
            className="pl-9"
          />
        </div>

        {errore && (
          <p className="mb-4 text-sm text-red-600" data-testid="sound-access-error">{errore}</p>
        )}

        {items === null ? (
          <p className="text-sm text-gray-400">Carico…</p>
        ) : (
          <div className="rounded-lg border divide-y bg-white">
            {visibili.map((o) => (
              <div key={o.id} className="flex items-center gap-4 px-4 py-3"
                   data-testid={`sound-access-row-${o.id}`}>
                <Music className={`h-4 w-4 shrink-0 ${o.sound_composer ? 'text-emerald-600' : 'text-gray-300'}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {o.name || o.id}
                    {o.email && (
                      <span className="ml-2 font-normal text-gray-500">{o.email}</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {o.tracks_total > 0
                      ? `${o.tracks_total} tracce · ${o.tracks_published} pubblicate · ultima ${quando(o.last_track_at)}`
                      : 'Nessuna traccia'}
                  </p>
                </div>
                {/* TR1 — la CHIAVE 2, in sola lettura: si accende da
                    sola col piano Pro (o con l'override). L'interruttore
                    a destra resta la chiave 1 (Meditazioni pubbliche). */}
                <span data-testid={`studio-stato-${o.id}`}
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${
                    o.studio_override === 'off'
                      ? 'border-red-300 text-red-600'
                      : o.studio_attivo
                        ? 'border-emerald-300 text-emerald-700'
                        : 'border-gray-200 text-gray-400'}`}>
                  {o.studio_override === 'off' ? 'Studio spento (override)'
                    : !o.studio_attivo ? 'Studio: no'
                      : o.sound_composer ? 'Studio via concessione'
                        : o.studio_override === 'on' ? 'Studio via override'
                          : `Studio via ${o.plan || 'piano'}`}
                </span>
                <Switch
                  checked={o.sound_composer}
                  disabled={salvando === o.id}
                  onCheckedChange={(v) => commuta(o, v)}
                  aria-label={`Compositore: ${o.name}`}
                />
              </div>
            ))}
            {!visibili.length && (
              <p className="px-4 py-6 text-sm text-gray-400">Nessuna organizzazione trovata.</p>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default SoundAccessPage;
