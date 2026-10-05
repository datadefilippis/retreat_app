/**
 * IscrittiTab — SA-R (10/9/2026 sera, founder): «pieno controllo sugli
 * iscritti al Cerchio: preferenze sui ritiri, zona, tutto quello che
 * hanno dato, da dove si sono iscritti, email; e verificare che chi si
 * disiscrive cambi stato nel pannello».
 *
 * Lotto D (24/9/2026, docs/ANALISI_SYSTEM_ADMIN_2026-09-24.md §3.3) —
 * la pagina rifatta sul backend del Lotto B:
 *  - in testa LA MAPPA: quattro card + tre ripartizioni (budget, dove,
 *    canale) che cliccate diventano filtri;
 *  - i filtri: testo, stato, canale › superficie (due tendine
 *    collegate), porta, fonte, budget, dove, regione, vie, avviso
 *    ritiri, verificato, periodo, tag;
 *  - la tabella con le COLONNE A SCELTA (selettore `iscritti-colonne`,
 *    scelta ricordata nel browser);
 *  - la SCHEDA (`iscritti-scheda`): i sei blocchi, il registro del
 *    consenso leggibile, la cronologia, le note e i tag;
 *  - le AZIONI, ognuna con la sua conferma e la sua riga di audit lato
 *    backend: reinvia conferma, conferma a mano (motivo), preferenze,
 *    nota, tag, disiscrivi, elimina (GDPR, a due passi).
 * Tutto da GET /admin/subscribers (+ /admin/subscribers/{email} per la
 * scheda), che e' l'unica verita' sugli iscritti.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  Download, RefreshCw, Search, UserMinus, Users, UserCheck, UserX, Clock,
  Columns3, Send, BadgeCheck, SlidersHorizontal, StickyNote, Tag as TagIcon, Trash2, X, ShieldCheck,
} from 'lucide-react';
import api from '../../api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../../components/ui/sheet';
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { StatCard } from '../../components/charts';

/* ── vocabolario (lo stesso del backend: routers/subscribers.py) ───────── */
const STATI = { confirmed: 'confermato', pending: 'in attesa', unsubscribed: 'disiscritto' };
const STATO_CLS = {
  confirmed: 'bg-emerald-100 text-emerald-800',
  pending: 'bg-amber-100 text-amber-800',
  unsubscribed: 'bg-gray-200 text-gray-700',
};
const VIE = {
  yoga: 'Yoga', meditazione: 'Meditazione', breathwork: 'Respiro', suono: 'Suono', reiki: 'Reiki',
  costellazioni: 'Costellazioni', astrologia: 'Astrologia', ayurveda: 'Ayurveda', tantra: 'Tantra',
  detox: 'Detox', cammini: 'Cammini', femminile: 'Cerchi & femminile', crescita: 'Crescita', misto: 'Un po’ di tutto',
};
const DOVE = { near: 'vicino a casa', italy: 'in Italia', anywhere: 'ovunque', abroad: 'anche all’estero' };
const BUDGET = { under500: 'fino a 500 €', '500to1000': '500–1000 €', over1000: 'oltre 1000 €', flexible: 'flessibile' };
// ET3 (2/10/2026) — le fasce d'eta' (ETA_FASCE nel backend)
const ETA = { '18-29': '18–29', '30-44': '30–44', '45-59': '45–59', '60+': '60 e oltre' };
const REGIONI = {
  abruzzo: 'Abruzzo', basilicata: 'Basilicata', calabria: 'Calabria', campania: 'Campania',
  'emilia-romagna': 'Emilia-Romagna', 'friuli-venezia-giulia': 'Friuli-Venezia Giulia', lazio: 'Lazio',
  liguria: 'Liguria', lombardia: 'Lombardia', marche: 'Marche', molise: 'Molise', piemonte: 'Piemonte',
  puglia: 'Puglia', sardegna: 'Sardegna', sicilia: 'Sicilia', toscana: 'Toscana',
  'trentino-alto-adige': 'Trentino-Alto Adige', umbria: 'Umbria', 'valle-d-aosta': 'Valle d’Aosta', veneto: 'Veneto',
};
const PORTE = { meditazioni: 'meditazioni', altro: 'altre porte' };
const MODALITA = {
  singolo: 'singolo opt-in', doppio: 'doppio opt-in', manuale: 'a mano (admin)',
  prelancio: 'prelancio', 'singolo-senza-prova': 'singolo, senza prova',
};
const VERIFICA_TIPO = { link: 'clic su un link', admin: 'a mano', confirm: 'email di conferma', account: 'account Aurya' };
const LIMITE = 50;
const CHIAVE_COLONNE = 'iscritti-colonne';

/* ── helper di lettura ────────────────────────────────────────────────── */
const data = (v) => (v ? new Date(v).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—');
const dataOra = (v) => (v ? new Date(v).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');
const vie = (r) => (r.interests || []).map((k) => VIE[k] || k).join(', ');
const alertTesto = (r) => {
  const a = r.retreat_alert || {};
  if (!a.enabled) return 'no';
  if (a.scope === 'regions' && (a.regions || []).length) return (a.regions || []).map((x) => REGIONI[x] || x).join(', ');
  return 'tutta Italia';
};
const testoVerifica = (r) => {
  if (!r.verificato_at) return null;
  const vd = r.verificato_da || {};
  return `${dataOra(r.verificato_at)} · ${VERIFICA_TIPO[vd.tipo] || vd.tipo || '?'}${vd.dettaglio ? ` (${vd.dettaglio})` : ''}`;
};

/* ── le colonne: chiave, etichetta, cella. Le prime dieci sono le predefinite. */
const COLONNE = [
  { k: 'email', label: 'Email', fisso: true, cella: (r) => <span className="font-mono text-xs">{r.email}</span> },
  { k: 'name', label: 'Nome', cella: (r) => r.name || '—' },
  { k: 'status', label: 'Stato', cella: (r) => <StatoPill status={r.status} /> },
  { k: 'provenienza', label: 'Provenienza', cella: (r, e) => <Provenienza p={r.provenienza} etich={e} /> },
  { k: 'created_at', label: 'Iscritto il', cella: (r) => data(r.created_at) },
  { k: 'budget', label: 'Budget', cella: (r) => BUDGET[r.budget] || r.budget || '—' },
  // ET3 — la fascia d'eta', se l'iscritto l'ha data; `nuova` = si accende
  // anche per chi aveva gia' salvato la sua scelta di colonne
  { k: 'eta', label: 'Età', nuova: true, cella: (r) => ETA[r.eta] || '—' },
  { k: 'travel', label: 'Dove', cella: (r) => DOVE[r.travel] || '—' },
  { k: 'city', label: 'Città', cella: (r) => r.city || '—' },
  { k: 'alert', label: 'Avviso ritiri', cella: (r) => alertTesto(r) },
  // 24/9 sera (founder): le vie (interessi per i ritiri) si vedono SUBITO
  { k: 'interests', label: 'Vie', cella: (r) => vie(r) || '—' },
  // «Email inviate» = le automatiche che il sistema ha mandato (conferma o
  // benvenuto, promemoria, passi della sequenza). Non sappiamo se le hanno
  // aperte; sappiamo se hanno cliccato: colonna «Verificato».
  { k: 'n_email', label: 'Email inviate', titolo: 'Email automatiche mandate dal sistema: conferma o benvenuto, promemoria, sequenza. Aperte non lo sappiamo; cliccate = Verificato.',
    cella: (r) => <span title={emailDettaglio(r)}>{r.n_email ?? (r.sequenza || []).length}</span> },
  { k: 'topics', label: 'Temi', cella: (r) => (r.topics || []).join(', ') || '—' },
  { k: 'language', label: 'Lingua', cella: (r) => r.language || '—' },
  { k: 'confirmed_at', label: 'Confermato il', cella: (r) => data(r.confirmed_at) },
  { k: 'porta', label: 'Porta', cella: (r) => PORTE[r.porta] || r.porta || '—' },
  // MP4 (5/10/2026) — la campagna (utm_campaign) e l'inserzione (utm_content) delle sponsorizzate
  { k: 'campagna', label: 'Campagna', titolo: 'utm_campaign · utm_content della provenienza (le sponsorizzate)',
    cella: (r) => (r.provenienza?.utm?.campaign ? `${r.provenienza.utm.campaign}${r.provenienza.utm.content ? ` · ${r.provenienza.utm.content}` : ''}` : '—') },
  { k: 'ultima_email_at', label: 'Ultima email', cella: (r) => data(r.ultima_email_at) },
  { k: 'tag', label: 'Tag', cella: (r) => (r.tag || []).join(', ') || '—' },
  { k: 'consenso', label: 'Consenso', cella: (r) => (r.consenso ? `${MODALITA[r.consenso.modalita] || r.consenso.modalita || '?'} · ${r.consenso.versione || '?'}` : '—') },
  { k: 'verificato', label: 'Verificato', cella: (r) => (r.verificato_at ? data(r.verificato_at) : 'no') },
];
const COLONNE_DEFAULT = COLONNE.slice(0, 12).map((c) => c.k);   // ET3: 11 → 12 (Età)

/* «conferma 12/09, benvenuto_ritiri 15/09»: il dettaglio dietro il numero */
function emailDettaglio(r) {
  const v = r.email_dettaglio || [];
  if (!v.length) return 'Nessuna email automatica registrata';
  return v.map((e) => `${e.tipo} ${e.at ? data(e.at) : ''}`.trim()).join(', ');
}

function leggiColonne() {
  try {
    const raw = JSON.parse(localStorage.getItem(CHIAVE_COLONNE) || 'null');
    if (Array.isArray(raw) && raw.length) {
      const valide = raw.filter((k) => COLONNE.some((c) => c.k === k));
      if (valide.length) {
        const base = valide.includes('email') ? valide : ['email', ...valide];
        // ET3 — una colonna `nuova` si offre UNA volta anche a chi ha gia' una
        // scelta salvata (al suo posto nell'ordine di COLONNE); poi l'admin la
        // tiene o la toglie come le altre
        let offerte = [];
        try { offerte = JSON.parse(localStorage.getItem(CHIAVE_OFFERTE) || '[]'); } catch { offerte = []; }
        const nuove = COLONNE.filter((c) => c.nuova && !base.includes(c.k) && !offerte.includes(c.k)).map((c) => c.k);
        if (!nuove.length) return base;
        try { localStorage.setItem(CHIAVE_OFFERTE, JSON.stringify([...offerte, ...nuove])); } catch { /* private mode */ }
        const unione = COLONNE.map((c) => c.k).filter((k) => base.includes(k) || nuove.includes(k));
        salvaColonne(unione);
        return unione;
      }
    }
  } catch { /* private mode o JSON rotto: predefinite */ }
  return COLONNE_DEFAULT;
}
const CHIAVE_OFFERTE = 'iscritti-colonne-offerte';
function salvaColonne(keys) {
  try { localStorage.setItem(CHIAVE_COLONNE, JSON.stringify(keys)); } catch { /* private mode */ }
}

function StatoPill({ status }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATO_CLS[status] || ''}`}
          data-testid={`iscritti-stato-${status}`}>{STATI[status] || status}</span>
  );
}

function Provenienza({ p, etich }) {
  if (!p) return '—';
  return (
    <span className="text-xs">
      {etich(p.canale)} <span className="text-muted-foreground">›</span> {etich(p.superficie)}
      {p.dettaglio ? <span className="text-muted-foreground"> · {p.dettaglio}</span> : null}
    </span>
  );
}

/** la riga del consenso in italiano: «ha accettato il testo v3 il 12/9
 *  alle 18:42 da cerca-ritiro, IP …» */
function consensoLeggibile(s, etich) {
  const c = s.consenso;
  if (!c) return null;
  const dove = s.provenienza?.superficie ? etich(s.provenienza.superficie) : (c.pagina || 'una pagina del sito');
  return `Ha accettato il testo ${c.versione || '?'} il ${dataOra(c.at)} da ${dove}`
    + `${c.ip ? `, IP ${c.ip}` : ''}${c.modalita ? ` (${MODALITA[c.modalita] || c.modalita})` : ''}.`;
}

const selCls = 'rounded-md border border-border bg-background px-2 py-1.5 text-sm';
const chipCls = (attivo) => `rounded-full border px-2.5 py-0.5 text-xs transition ${attivo
  ? 'border-foreground bg-foreground text-background' : 'border-border bg-background hover:bg-muted'}`;

const FILTRI_VUOTI = {
  status: '', porta: '', source: '', experiences: '', region: '', interest: '', q: '',
  canale: '', superficie: '', budget: '', travel: '', verificato: '', dal: '', al: '', tag: '',
  eta: '',                                                   // ET3
  campagna: '', inserzione: '',                              // MP4
};

export default function IscrittiTab() {
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [sources, setSources] = useState([]);
  const [canali, setCanali] = useState([]);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState(FILTRI_VUOTI);
  const [colonne, setColonne] = useState(leggiColonne);
  // la scheda: la riga aperta (dalla lista) + il dettaglio completo (dal GET)
  const [aperto, setAperto] = useState(null);
  const [scheda, setScheda] = useState(null);
  const [schedaLoading, setSchedaLoading] = useState(false);
  // l'azione in corso: { tipo, motivo, passo, ... }
  const [azione, setAzione] = useState(null);
  const [inCorso, setInCorso] = useState(false);
  const [nota, setNota] = useState('');
  const [nuovoTag, setNuovoTag] = useState('');

  /* etichette umane di canale/superficie: dalla tassonomia del backend */
  const etichette = useMemo(() => {
    const m = {};
    (canali || []).forEach((c) => {
      m[c.canale] = c.label;
      (c.superfici || []).forEach((s) => { m[s.superficie] = s.label; });
    });
    return m;
  }, [canali]);
  const etich = useCallback((k) => (k ? (etichette[k] || k) : '—'), [etichette]);

  const params = useMemo(() => {
    const p = { skip, limit: LIMITE };
    Object.entries(f).forEach(([k, v]) => { if (v) p[k] = v; });
    return p;
  }, [f, skip]);

  const carica = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get('/admin/subscribers', { params }),
      api.get('/admin/newsletter-stats'),
    ]).then(([l, s]) => {
      setRows(l.data.items || []); setTotal(l.data.total || 0);
      setSources(l.data.sources || []); setCanali(l.data.canali || []);
      setStats(s.data);
    }).catch(() => toast.error('Non riesco a caricare gli iscritti'))
      .finally(() => setLoading(false));
  }, [params]);
  useEffect(() => { carica(); }, [carica]);

  const setFiltro = (k) => (e) => {
    const v = e && e.target ? e.target.value : e;
    setSkip(0);
    setF((prev) => (k === 'canale'
      ? { ...prev, canale: v, superficie: '' }      // le due tendine sono collegate
      : k === 'campagna'
        ? { ...prev, campagna: v, inserzione: '' }  // MP4: idem campagna › inserzione
        : { ...prev, [k]: v }));
  };
  const toggleFiltro = (k, v) => setFiltro(k)(f[k] === v ? '' : v);
  const azzera = () => { setSkip(0); setF(FILTRI_VUOTI); };
  const filtriAttivi = Object.values(f).filter(Boolean).length;

  const toggleColonna = (k) => {
    setColonne((prev) => {
      const next = prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k];
      const ordinate = COLONNE.map((c) => c.k).filter((x) => next.includes(x));
      salvaColonne(ordinate);
      return ordinate;
    });
  };
  const colonneVisibili = COLONNE.filter((c) => colonne.includes(c.k));

  const esporta = async () => {
    try {
      const r = await api.get('/admin/subscribers/export.csv', { params: { ...params, skip: 0, limit: 5000 }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a'); a.href = url; a.download = 'iscritti-cerchio.csv'; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Export non riuscito'); }
  };

  /* ── la scheda ─────────────────────────────────────────────────────── */
  const caricaScheda = useCallback(async (email) => {
    setSchedaLoading(true);
    try {
      const r = await api.get(`/admin/subscribers/${encodeURIComponent(email)}`);
      setScheda(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Non riesco ad aprire la scheda');
    } finally { setSchedaLoading(false); }
  }, []);
  const apri = (r) => { setAperto(r); setScheda(null); setNota(''); setNuovoTag(''); caricaScheda(r.email); };
  const chiudi = () => { setAperto(null); setScheda(null); setAzione(null); };
  const s = scheda || aperto;   // finche' il dettaglio arriva, si legge la riga

  /* dopo ogni scrittura: la scheda si rilegge, la lista anche */
  const dopo = async (email, messaggio) => {
    if (messaggio) toast.success(messaggio);
    setAzione(null);
    await caricaScheda(email);
    carica();
  };
  const errore = (e, fallback) => toast.error(e?.response?.data?.detail || fallback);

  const eseguiAzione = async () => {
    if (!s || !azione || inCorso) return;
    const email = s.email;
    setInCorso(true);
    try {
      if (azione.tipo === 'reinvia') {
        await api.post('/admin/subscribers/reinvia-conferma', { email });
        await dopo(email, `Email di conferma rimandata a ${email}`);
      } else if (azione.tipo === 'conferma') {
        if ((azione.motivo || '').trim().length < 3) { toast.error('Scrivi il motivo (almeno 3 caratteri)'); return; }
        await api.post('/admin/subscribers/conferma', { email, motivo: azione.motivo.trim() });
        await dopo(email, `${email} è confermato`);
      } else if (azione.tipo === 'preferenze') {
        const p = azione.pref;
        await api.patch(`/admin/subscribers/${encodeURIComponent(email)}/preferenze`, {
          name: p.name, city: p.city, travel: p.travel || null, budget: p.budget || null,
          eta: p.eta || '',                                  // ET3 — "" = togli
          interests: p.interests,
          retreat_alert: { enabled: p.alertEnabled, scope: p.alertScope, regions: p.alertRegions },
        });
        await dopo(email, 'Preferenze salvate');
      } else if (azione.tipo === 'disiscrivi') {
        await api.post('/admin/subscribers/disiscrivi', { email });
        await dopo(email, `${email} è disiscritto`);
      } else if (azione.tipo === 'elimina') {
        if ((azione.motivo || '').trim().length < 3) { toast.error('Scrivi il motivo (almeno 3 caratteri)'); return; }
        if (azione.passo !== 2) { setAzione({ ...azione, passo: 2 }); return; }
        await api.delete(`/admin/subscribers/${encodeURIComponent(email)}`, { data: { motivo: azione.motivo.trim() } });
        toast.success(`${email} è stato cancellato`);
        chiudi(); carica();
      }
    } catch (e) { errore(e, 'Non riuscito'); }
    finally { setInCorso(false); }
  };

  const aggiungiNota = async () => {
    if (!s || !nota.trim()) return;
    setInCorso(true);
    try {
      await api.post(`/admin/subscribers/${encodeURIComponent(s.email)}/note`, { testo: nota.trim() });
      setNota('');
      await dopo(s.email, 'Nota aggiunta');
    } catch (e) { errore(e, 'Nota non salvata'); }
    finally { setInCorso(false); }
  };

  const salvaTag = async (tag) => {
    if (!s) return;
    setInCorso(true);
    try {
      await api.put(`/admin/subscribers/${encodeURIComponent(s.email)}/tag`, { tag });
      setNuovoTag('');
      await dopo(s.email, null);
    } catch (e) { errore(e, 'Tag non salvati'); }
    finally { setInCorso(false); }
  };
  const aggiungiTag = () => {
    const t = nuovoTag.trim().toLowerCase();
    if (!t) return;
    salvaTag([...(s.tag || []).filter((x) => x !== t), t]);
  };
  const togliTag = (t) => salvaTag((s.tag || []).filter((x) => x !== t));

  const apriPreferenze = () => {
    const a = s.retreat_alert || {};
    setAzione({
      tipo: 'preferenze',
      pref: {
        name: s.name || '', city: s.city || '', travel: s.travel || '', budget: s.budget || '',
        eta: s.eta || '',
        interests: [...(s.interests || [])],
        alertEnabled: !!a.enabled, alertScope: a.scope || 'italy', alertRegions: [...(a.regions || [])],
      },
    });
  };
  const setPref = (k, v) => setAzione((prev) => ({ ...prev, pref: { ...prev.pref, [k]: v } }));
  const togliInPref = (k, v) => setPref(k, (azione.pref[k] || []).includes(v)
    ? azione.pref[k].filter((x) => x !== v) : [...azione.pref[k], v]);

  const byStatus = stats?.by_status || {};
  const canaleScelto = (canali || []).find((c) => c.canale === f.canale);
  const campagnaScelta = (stats?.by_campagna || []).find((c) => c.campagna === f.campagna);   // MP4

  return (
    <div className="space-y-6" data-testid="iscritti-tab">
      {/* ── LA MAPPA ────────────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard loading={!stats} icon={Users} label="Iscritti in tutto" value={stats ? `${stats.total}` : '—'}
                  sublabel={stats ? `${stats.verificati ?? 0} con indirizzo verificato` : ''} />
        <StatCard loading={!stats} icon={UserCheck} label="Confermati" value={`${byStatus.confirmed || 0}`}
                  sublabel={stats ? `conferma ${Math.round((stats.confirm_rate || 0) * 100)}% · +${(stats.weekly_new || []).slice(-1)[0]?.n ?? 0} nell’ultima settimana` : ''} />
        <StatCard loading={!stats} icon={Clock} label="In attesa del clic" value={`${byStatus.pending || 0}`}
                  sublabel="promemoria dopo 48 ore, una volta" />
        <StatCard loading={!stats} icon={UserX} label="Disiscritti" value={`${byStatus.unsubscribed || 0}`}
                  sublabel="restano a DB per non riscriverli" />
      </div>

      {stats && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4" data-testid="iscritti-ripartizioni">
          <Ripartizione titolo="Per budget" testid="iscritti-rip-budget"
                        voci={(stats.by_budget || []).map((x) => ({ k: x.budget, label: BUDGET[x.budget] || x.budget, n: x.n }))}
                        attivo={f.budget} onClick={(k) => toggleFiltro('budget', k)} />
          <Ripartizione titolo="Per età" testid="iscritti-rip-eta"
                        voci={(stats.by_eta || []).map((x) => ({ k: x.eta, label: ETA[x.eta] || x.eta, n: x.n }))}
                        attivo={f.eta} onClick={(k) => toggleFiltro('eta', k)} />
          <Ripartizione titolo="Per dove" testid="iscritti-rip-dove"
                        voci={(stats.by_travel || []).map((x) => ({ k: x.travel, label: DOVE[x.travel] || x.travel, n: x.n }))}
                        attivo={f.travel} onClick={(k) => toggleFiltro('travel', k)} />
          <Ripartizione titolo="Per canale" testid="iscritti-rip-canale"
                        voci={(stats.by_canale || []).map((x) => ({ k: x.canale, label: x.label || etich(x.canale), n: x.n }))}
                        attivo={f.canale} onClick={(k) => toggleFiltro('canale', k)} />
          {/* MP4 — le sponsorizzate: «campagna 12 · 7 conf.» = 12 iscritti, 7 confermati */}
          <Ripartizione titolo="Per campagna" testid="iscritti-rip-campagna"
                        voci={(stats.by_campagna || []).map((x) => ({ k: x.campagna, label: x.campagna, n: `${x.n} · ${x.confermati} conf.` }))}
                        attivo={f.campagna} onClick={(k) => toggleFiltro('campagna', k)} />
        </div>
      )}

      <Card className="border border-border">
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg">Gli iscritti al Cerchio</CardTitle>
          <CardDescription>
            Ogni riga dice chi è, da dove è entrata e cosa ci ha detto. Clicca una riga per la scheda completa,
            con le azioni. Chi si disiscrive dal link nelle email compare qui come «disiscritto» con la data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ── I FILTRI ──────────────────────────────────────────────── */}
          <div className="flex flex-wrap items-center gap-2" data-testid="iscritti-filtri">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={f.q} onChange={setFiltro('q')} placeholder="cerca email" className="h-9 w-44 pl-8" data-testid="iscritti-f-q" />
            </div>
            <select value={f.status} onChange={setFiltro('status')} className={selCls} data-testid="iscritti-f-stato">
              <option value="">tutti gli stati</option>
              {Object.entries(STATI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.canale} onChange={setFiltro('canale')} className={selCls} data-testid="iscritti-f-canale">
              <option value="">tutti i canali</option>
              {(canali || []).map((c) => <option key={c.canale} value={c.canale}>{c.label}</option>)}
            </select>
            <select value={f.superficie} onChange={setFiltro('superficie')} className={selCls}
                    disabled={!canaleScelto} data-testid="iscritti-f-superficie">
              <option value="">{canaleScelto ? 'tutte le superfici' : 'superficie (scegli un canale)'}</option>
              {(canaleScelto?.superfici || []).map((x) => <option key={x.superficie} value={x.superficie}>{x.label}</option>)}
            </select>
            <select value={f.porta} onChange={setFiltro('porta')} className={selCls} data-testid="iscritti-f-porta">
              <option value="">tutte le porte</option>
              {Object.entries(PORTE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.source} onChange={setFiltro('source')} className={selCls} data-testid="iscritti-f-fonte">
              <option value="">tutte le fonti</option>
              {sources.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
            {/* MP4 — campagna › inserzione (dalle ripartizioni del server) */}
            <select value={f.campagna} onChange={setFiltro('campagna')} className={selCls} data-testid="iscritti-f-campagna">
              <option value="">tutte le campagne</option>
              {(stats?.by_campagna || []).map((c) => <option key={c.campagna} value={c.campagna}>{c.campagna} ({c.n})</option>)}
            </select>
            <select value={f.inserzione} onChange={setFiltro('inserzione')} className={selCls}
                    disabled={!campagnaScelta} data-testid="iscritti-f-inserzione">
              <option value="">{campagnaScelta ? 'tutte le inserzioni' : 'inserzione (scegli una campagna)'}</option>
              {(campagnaScelta?.inserzioni || []).map((x) => <option key={x.inserzione} value={x.inserzione}>{x.inserzione} ({x.n})</option>)}
            </select>
            <select value={f.budget} onChange={setFiltro('budget')} className={selCls} data-testid="iscritti-f-budget">
              <option value="">budget: tutti</option>
              {Object.entries(BUDGET).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.travel} onChange={setFiltro('travel')} className={selCls} data-testid="iscritti-f-dove">
              <option value="">dove: tutti</option>
              {Object.entries(DOVE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.eta} onChange={setFiltro('eta')} className={selCls} data-testid="iscritti-f-eta">
              <option value="">età: tutte</option>
              {Object.entries(ETA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.region} onChange={setFiltro('region')} className={selCls} data-testid="iscritti-f-regione">
              <option value="">tutte le regioni</option>
              {Object.entries(REGIONI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.interest} onChange={setFiltro('interest')} className={selCls} data-testid="iscritti-f-via">
              <option value="">tutte le vie</option>
              {Object.entries(VIE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={f.experiences} onChange={setFiltro('experiences')} className={selCls} data-testid="iscritti-f-ritiri">
              <option value="">ritiri: tutti</option>
              <option value="yes">vuole i ritiri</option>
              <option value="no">non li ha chiesti</option>
            </select>
            <select value={f.verificato} onChange={setFiltro('verificato')} className={selCls} data-testid="iscritti-f-verificato">
              <option value="">verificato: tutti</option>
              <option value="si">indirizzo verificato</option>
              <option value="no">mai verificato</option>
            </select>
            <label className="flex items-center gap-1 text-xs text-muted-foreground">dal
              <input type="date" value={f.dal} onChange={setFiltro('dal')} className={selCls} data-testid="iscritti-f-dal" />
            </label>
            <label className="flex items-center gap-1 text-xs text-muted-foreground">al
              <input type="date" value={f.al} onChange={setFiltro('al')} className={selCls} data-testid="iscritti-f-al" />
            </label>
            <Input value={f.tag} onChange={setFiltro('tag')} placeholder="tag" className="h-9 w-28" data-testid="iscritti-f-tag" />
            {filtriAttivi > 0 && (
              <Button variant="ghost" size="sm" onClick={azzera} data-testid="iscritti-f-azzera">
                <X className="mr-1 h-4 w-4" />azzera ({filtriAttivi})
              </Button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" data-testid="iscritti-colonne">
                  <Columns3 className="mr-1 h-4 w-4" />Colonne ({colonneVisibili.length})
                </Button>
              </PopoverTrigger>
              <PopoverContent align="start" className="w-64">
                <p className="mb-2 text-xs text-muted-foreground">Le colonne che vuoi vedere. La scelta resta in questo browser.</p>
                <div className="grid grid-cols-2 gap-1.5">
                  {COLONNE.map((c) => (
                    <label key={c.k} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={colonne.includes(c.k)} disabled={c.fisso}
                             onChange={() => toggleColonna(c.k)} data-testid={`iscritti-colonna-${c.k}`} />
                      {c.label}
                    </label>
                  ))}
                </div>
                <Button variant="ghost" size="sm" className="mt-2 w-full"
                        onClick={() => { setColonne(COLONNE_DEFAULT); salvaColonne(COLONNE_DEFAULT); }}>
                  Torna alle predefinite
                </Button>
              </PopoverContent>
            </Popover>
            <Button variant="outline" size="sm" onClick={carica}><RefreshCw className="mr-1 h-4 w-4" />Aggiorna</Button>
            <Button variant="outline" size="sm" onClick={esporta} data-testid="iscritti-export"><Download className="mr-1 h-4 w-4" />CSV</Button>
            <span className="ml-auto text-sm text-muted-foreground" data-testid="iscritti-totale">{total} {total === 1 ? 'persona' : 'persone'}</span>
          </div>

          {/* ── LA TABELLA ────────────────────────────────────────────── */}
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {colonneVisibili.map((c) => <TableHead key={c.k}>{c.label}</TableHead>)}
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && rows.length === 0 ? (
                  <TableRow><TableCell colSpan={colonneVisibili.length} className="text-center text-sm text-muted-foreground">Carico…</TableCell></TableRow>
                ) : rows.length === 0 ? (
                  <TableRow><TableCell colSpan={colonneVisibili.length} className="text-center text-sm text-muted-foreground">Nessuno con questi filtri.</TableCell></TableRow>
                ) : rows.map((r) => (
                  <TableRow key={r.email} className="cursor-pointer" onClick={() => apri(r)} data-testid="iscritti-riga">
                    {colonneVisibili.map((c) => (
                      <TableCell key={c.k} className={c.k === 'email' ? '' : 'text-xs'}>{c.cella(r, etich)}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {total > LIMITE && (
            <div className="flex items-center justify-between text-sm">
              <Button variant="outline" size="sm" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - LIMITE))}>← precedenti</Button>
              <span className="text-muted-foreground">{skip + 1}–{Math.min(skip + LIMITE, total)} di {total}</span>
              <Button variant="outline" size="sm" disabled={skip + LIMITE >= total} onClick={() => setSkip(skip + LIMITE)}>successivi →</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── LA SCHEDA ───────────────────────────────────────────────────── */}
      <Sheet open={!!aperto} onOpenChange={(o) => { if (!o) chiudi(); }}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl" data-testid="iscritti-scheda">
          {s && (
            <div className="space-y-5 text-sm" data-testid="iscritti-dettaglio">
              <SheetHeader>
                <SheetTitle className="font-mono text-base">{s.email}</SheetTitle>
                <SheetDescription className="flex flex-wrap items-center gap-2">
                  <StatoPill status={s.status} />
                  {s.verificato_at && (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-700"><ShieldCheck className="h-3.5 w-3.5" />verificato</span>
                  )}
                  {schedaLoading && <span className="text-xs text-muted-foreground">carico la scheda…</span>}
                </SheetDescription>
              </SheetHeader>

              {/* le azioni */}
              <div className="flex flex-wrap gap-2" data-testid="iscritti-azioni">
                {s.status === 'pending' && (
                  <Button variant="outline" size="sm" onClick={() => setAzione({ tipo: 'reinvia' })} data-testid="iscritti-reinvia">
                    <Send className="mr-1 h-4 w-4" />Reinvia conferma
                  </Button>
                )}
                {s.status !== 'confirmed' && (
                  <Button variant="outline" size="sm" onClick={() => setAzione({ tipo: 'conferma', motivo: '' })} data-testid="iscritti-conferma">
                    <BadgeCheck className="mr-1 h-4 w-4" />Conferma a mano
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={apriPreferenze} data-testid="iscritti-preferenze">
                  <SlidersHorizontal className="mr-1 h-4 w-4" />Preferenze
                </Button>
                {s.status !== 'unsubscribed' && (
                  <Button variant="outline" size="sm" onClick={() => setAzione({ tipo: 'disiscrivi' })} data-testid="iscritti-disiscrivi">
                    <UserMinus className="mr-1 h-4 w-4" />Disiscrivi
                  </Button>
                )}
                <Button variant="outline" size="sm" className="text-red-700 hover:text-red-800"
                        onClick={() => setAzione({ tipo: 'elimina', motivo: '', passo: 1 })} data-testid="iscritti-elimina">
                  <Trash2 className="mr-1 h-4 w-4" />Elimina
                </Button>
              </div>

              {/* 1 · identità */}
              <Blocco titolo="Identità">
                <Riga k="Nome" v={s.name || '—'} />
                <Riga k="Lingua" v={s.language || '—'} />
                <Riga k="Stato" v={`${STATI[s.status] || s.status}${s.unsubscribed_by ? ` (da ${s.unsubscribed_by})` : ''}`} />
                <Riga k="Tag" v={(
                  <div className="flex flex-wrap items-center gap-1.5">
                    {(s.tag || []).map((t) => (
                      <span key={t} className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs">
                        <TagIcon className="h-3 w-3" />{t}
                        <button type="button" onClick={() => togliTag(t)} aria-label={`togli ${t}`} className="opacity-60 hover:opacity-100"><X className="h-3 w-3" /></button>
                      </span>
                    ))}
                    <form className="flex items-center gap-1" onSubmit={(e) => { e.preventDefault(); aggiungiTag(); }}>
                      <Input value={nuovoTag} onChange={(e) => setNuovoTag(e.target.value)} placeholder="nuovo tag"
                             className="h-7 w-28 text-xs" data-testid="iscritti-tag" />
                      <Button type="submit" variant="ghost" size="sm" className="h-7 px-2" disabled={!nuovoTag.trim() || inCorso}>+</Button>
                    </form>
                  </div>
                )} />
                {scheda?.legami && (
                  <Riga k="Legami" v={(
                    <span className="text-xs">
                      {scheda.legami.account
                        ? <>account Aurya ({scheda.legami.account.role}{scheda.legami.account.email_verified ? ', email verificata' : ''})</>
                        : 'nessun account'}
                      {scheda.legami.lead ? <> · lead {scheda.legami.lead.type} del {data(scheda.legami.lead.created_at)}{scheda.legami.lead.phone ? ` · ${scheda.legami.lead.phone}` : ''}</> : null}
                      {scheda.legami.organizzazione_id
                        ? <> · <a className="underline" href={`/admin/operatori?tab=organizzazioni&org=${encodeURIComponent(scheda.legami.organizzazione_id)}`}>organizzazione</a></>
                        : null}
                    </span>
                  )} />
                )}
              </Blocco>

              {/* 2 · consenso */}
              <Blocco titolo="Consenso" testid="iscritti-consenso">
                {s.consenso ? (
                  <>
                    <p>{consensoLeggibile(s, etich)}</p>
                    {s.consenso.testo && <p className="rounded-md bg-muted px-3 py-2 text-xs italic">«{s.consenso.testo}»</p>}
                    {s.consenso.pagina && <Riga k="Pagina" v={<span className="break-all text-xs">{s.consenso.pagina}</span>} />}
                    {s.consenso.user_agent && <Riga k="Browser" v={<span className="break-all text-xs text-muted-foreground">{s.consenso.user_agent}</span>} />}
                  </>
                ) : (
                  <p className="text-muted-foreground">Nessun registro del consenso: iscrizione precedente al registro (24/9/2026).</p>
                )}
              </Blocco>

              {/* 3 · provenienza */}
              <Blocco titolo="Provenienza">
                <Riga k="Canale › superficie" v={<Provenienza p={s.provenienza} etich={etich} />} />
                <Riga k="Porta" v={s.provenienza?.porta || PORTE[s.porta] || s.porta || '—'} />
                <Riga k="Fonte grezza" v={<span className="font-mono text-xs">{s.source}</span>} />
                {s.provenienza?.url && <Riga k="URL" v={<span className="break-all text-xs">{s.provenienza.url}</span>} />}
                {s.provenienza?.referrer && <Riga k="Arrivo da" v={<span className="break-all text-xs">{s.provenienza.referrer}</span>} />}
                {s.provenienza?.utm && (
                  <Riga k="UTM" v={['source', 'medium', 'campaign', 'content', 'term'].map((k) => s.provenienza.utm[k] && `${k}=${s.provenienza.utm[k]}`).filter(Boolean).join(' · ') || '—'} />
                )}
                {s.provenienza?.click_ids && <Riga k="Clic pubblicitario" v={Object.keys(s.provenienza.click_ids).join(', ')} />}
                {s.provenienza?.tracciamento && (
                  <Riga k="Pixel Meta" v={s.provenienza.tracciamento.marketing ? 'consenso marketing: sì (evento mandato anche dal server)' : 'consenso marketing: no (nessun evento)'} />
                )}
                {s.provenienza?.dispositivo && <Riga k="Dispositivo" v={s.provenienza.dispositivo} />}
              </Blocco>

              {/* 4 · interessi */}
              <Blocco titolo="Interessi">
                <Riga k="Vie" v={vie(s) || '—'} />
                <Riga k="Temi Magazine" v={(s.topics || []).join(', ') || '—'} />
                <Riga k="Formato" v={s.format || '—'} />
                <Riga k="Città" v={s.city || '—'} />
                <Riga k="Dove" v={DOVE[s.travel] || '—'} />
                <Riga k="Budget" v={BUDGET[s.budget] || s.budget || '—'} />
                <Riga k="Età" v={ETA[s.eta] || '—'} />
              </Blocco>

              {/* 5 · ritiri */}
              <Blocco titolo="Ritiri">
                <Riga k="Avviso ritiri" v={alertTesto(s)} />
              </Blocco>

              {/* 6 · ciclo di vita */}
              <Blocco titolo="Ciclo di vita">
                <Riga k="Iscritto il" v={dataOra(s.created_at)} />
                <Riga k="Confermato il" v={dataOra(s.confirmed_at)} />
                <Riga k="Verificato" v={testoVerifica(s) || 'no'} />
                <Riga k="Promemoria" v={s.reminder_sent_at ? dataOra(s.reminder_sent_at) : '—'} />
                <Riga k="Disiscritto il" v={s.unsubscribed_at ? `${dataOra(s.unsubscribed_at)}${s.unsubscribed_by ? ` (${s.unsubscribed_by})` : ''}` : '—'} />
                <Riga k="Indirizzo" v={s.email_status ? `${s.email_status}${scheda?.email_status_at ? ` dal ${data(scheda.email_status_at)}` : ''}` : 'ok'} />
                <Riga k="Email inviate" v={`${s.n_email ?? (s.sequenza || []).length}${s.ultima_email_at ? ` · ultima ${data(s.ultima_email_at)}` : ''} — ${emailDettaglio(s)}`} />
                {scheda?.sequenza_dettaglio && Object.keys(scheda.sequenza_dettaglio).length > 0 && (
                  <Riga k="Sequenza" v={(
                    <ul className="space-y-0.5 text-xs">
                      {Object.entries(scheda.sequenza_dettaglio).map(([passo, v]) => (
                        <li key={passo}><span className="font-mono">{passo}</span> · {String(v)}</li>
                      ))}
                    </ul>
                  )} />
                )}
              </Blocco>

              {/* cronologia */}
              <Blocco titolo="Cronologia" testid="iscritti-cronologia">
                {scheda?.cronologia?.length ? (
                  <ol className="space-y-1.5">
                    {scheda.cronologia.map((c, i) => (
                      <li key={`${c.at}-${c.tipo}-${i}`} className="grid grid-cols-[8.5rem_1fr] gap-2 text-xs">
                        <span className="text-muted-foreground">{dataOra(c.at)}</span>
                        <span><span className="rounded bg-muted px-1 py-0.5 font-mono text-[10px]">{c.tipo}</span> {c.testo}{c.dettaglio ? <span className="text-muted-foreground"> · {c.dettaglio}</span> : null}</span>
                      </li>
                    ))}
                  </ol>
                ) : <p className="text-muted-foreground">{schedaLoading ? 'carico…' : 'Niente ancora.'}</p>}
              </Blocco>

              {/* note */}
              <Blocco titolo="Note" testid="iscritti-note">
                {(scheda?.note || []).length > 0 && (
                  <ul className="space-y-1.5">
                    {scheda.note.map((n) => (
                      <li key={n.id} className="rounded-md bg-muted px-3 py-2 text-xs">
                        <span className="text-muted-foreground">{dataOra(n.at)}{n.da ? ` · ${n.da}` : ''}</span>
                        <p className="mt-0.5 whitespace-pre-wrap">{n.testo}</p>
                      </li>
                    ))}
                  </ul>
                )}
                <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); aggiungiNota(); }}>
                  <Textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={2} maxLength={2000}
                            placeholder="una nota per chi guarda questa scheda dopo di te" data-testid="iscritti-nota" />
                  <Button type="submit" variant="outline" size="sm" disabled={!nota.trim() || inCorso}>
                    <StickyNote className="mr-1 h-4 w-4" />Aggiungi nota
                  </Button>
                </form>
              </Blocco>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* ── LE CONFERME ─────────────────────────────────────────────────── */}
      <Dialog open={!!azione && !!s} onOpenChange={(o) => { if (!o) setAzione(null); }}>
        <DialogContent className="max-w-md" data-testid={azione ? `iscritti-dialogo-${azione.tipo}` : 'iscritti-dialogo'}>
          {azione && s && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {azione.tipo === 'reinvia' && 'Rimandare l’email di conferma?'}
                  {azione.tipo === 'conferma' && 'Confermare a mano questo iscritto?'}
                  {azione.tipo === 'preferenze' && 'Preferenze dell’iscritto'}
                  {azione.tipo === 'disiscrivi' && 'Disiscrivere dal Cerchio?'}
                  {azione.tipo === 'elimina' && (azione.passo === 2 ? 'Ultimo passo: cancellazione definitiva' : 'Cancellare questo iscritto (GDPR)?')}
                </DialogTitle>
                <DialogDescription className="font-mono text-xs">{s.email}</DialogDescription>
              </DialogHeader>

              {azione.tipo === 'reinvia' && (
                <p>Riceve di nuovo l’email con il link «Entro nel Cerchio». Solo per chi è ancora in attesa.</p>
              )}
              {azione.tipo === 'conferma' && (
                <div className="space-y-2">
                  <p>Per chi si è iscritto a voce o via messaggio. Passa a «confermato» con modalità «a mano» e riceve il benvenuto. Il motivo resta nell’audit.</p>
                  <Textarea value={azione.motivo} onChange={(e) => setAzione({ ...azione, motivo: e.target.value })} rows={2}
                            maxLength={300} placeholder="motivo (obbligatorio): es. «me l’ha chiesto su WhatsApp il 20/9»"
                            data-testid="iscritti-motivo" />
                </div>
              )}
              {azione.tipo === 'disiscrivi' && (
                <p>Stesso effetto del link nelle email: non riceve più nulla, resta a DB come «disiscritto» con la data e chi l’ha fatto.</p>
              )}
              {azione.tipo === 'elimina' && azione.passo !== 2 && (
                <div className="space-y-2">
                  <p>Cancellazione su richiesta (art. 17): il documento sparisce, Brevo lo mette in blacklist, resta solo la riga di audit col motivo.</p>
                  <Textarea value={azione.motivo} onChange={(e) => setAzione({ ...azione, motivo: e.target.value })} rows={2}
                            maxLength={300} placeholder="motivo (obbligatorio): es. «richiesta via email del 22/9»"
                            data-testid="iscritti-motivo" />
                </div>
              )}
              {azione.tipo === 'elimina' && azione.passo === 2 && (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-800">
                  Non si torna indietro: <b>{s.email}</b> sparisce dal Cerchio e dalle liste Brevo. Motivo: «{azione.motivo}».
                </p>
              )}
              {azione.tipo === 'preferenze' && (
                <div className="space-y-3" data-testid="iscritti-preferenze-form">
                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs">Nome
                      <Input value={azione.pref.name} onChange={(e) => setPref('name', e.target.value)} className="mt-1 h-9" />
                    </label>
                    <label className="text-xs">Città
                      <Input value={azione.pref.city} onChange={(e) => setPref('city', e.target.value)} className="mt-1 h-9" />
                    </label>
                    <label className="text-xs">Dove
                      <select value={azione.pref.travel} onChange={(e) => setPref('travel', e.target.value)} className={`${selCls} mt-1 w-full`}>
                        <option value="">—</option>
                        {Object.entries(DOVE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </label>
                    <label className="text-xs">Budget
                      <select value={azione.pref.budget} onChange={(e) => setPref('budget', e.target.value)} className={`${selCls} mt-1 w-full`}>
                        <option value="">—</option>
                        {Object.entries(BUDGET).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </label>
                    <label className="text-xs">Età
                      <select value={azione.pref.eta} onChange={(e) => setPref('eta', e.target.value)} className={`${selCls} mt-1 w-full`} data-testid="iscritti-pref-eta">
                        <option value="">—</option>
                        {Object.entries(ETA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </label>
                  </div>
                  <div>
                    <p className="text-xs">Vie</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {Object.entries(VIE).map(([k, v]) => (
                        <button type="button" key={k} className={chipCls(azione.pref.interests.includes(k))}
                                onClick={() => togliInPref('interests', k)}>{v}</button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 text-xs">
                      <input type="checkbox" checked={azione.pref.alertEnabled} onChange={(e) => setPref('alertEnabled', e.target.checked)} />
                      Vuole l’avviso sui ritiri
                    </label>
                    {azione.pref.alertEnabled && (
                      <>
                        <select value={azione.pref.alertScope} onChange={(e) => setPref('alertScope', e.target.value)} className={`${selCls} w-full`}>
                          <option value="italy">tutta Italia</option>
                          <option value="regions">solo alcune regioni</option>
                        </select>
                        {azione.pref.alertScope === 'regions' && (
                          <div className="flex flex-wrap gap-1.5">
                            {Object.entries(REGIONI).map(([k, v]) => (
                              <button type="button" key={k} className={chipCls(azione.pref.alertRegions.includes(k))}
                                      onClick={() => togliInPref('alertRegions', k)}>{v}</button>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}

              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setAzione(null)} disabled={inCorso}>Annulla</Button>
                <Button onClick={eseguiAzione} disabled={inCorso}
                        variant={azione.tipo === 'elimina' && azione.passo === 2 ? 'destructive' : 'default'}
                        data-testid="iscritti-conferma-azione">
                  {azione.tipo === 'reinvia' && 'Rimanda l’email'}
                  {azione.tipo === 'conferma' && 'Conferma'}
                  {azione.tipo === 'preferenze' && 'Salva'}
                  {azione.tipo === 'disiscrivi' && 'Disiscrivi'}
                  {azione.tipo === 'elimina' && (azione.passo === 2 ? 'Elimina definitivamente' : 'Continua')}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ── pezzi della scheda ──────────────────────────────────────────────── */
function Blocco({ titolo, testid, children }) {
  return (
    <section className="space-y-1.5 rounded-lg border border-border p-3" data-testid={testid}>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{titolo}</h3>
      {children}
    </section>
  );
}

function Riga({ k, v }) {
  return (
    <div className="grid grid-cols-[8.5rem_1fr] gap-2">
      <span className="text-muted-foreground">{k}</span>
      <span className="min-w-0">{v}</span>
    </div>
  );
}

function Ripartizione({ titolo, voci, attivo, onClick, testid }) {
  return (
    <div className="rounded-lg border border-border p-3" data-testid={testid}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{titolo}</p>
      {voci.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : (
        <div className="flex flex-wrap gap-1.5">
          {voci.map((x) => (
            <button type="button" key={x.k} className={chipCls(attivo === x.k)} onClick={() => onClick(x.k)}
                    title={attivo === x.k ? 'togli il filtro' : 'filtra'}>
              {x.label} <span className="opacity-70">{x.n}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
