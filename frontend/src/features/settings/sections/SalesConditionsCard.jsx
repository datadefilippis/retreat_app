/**
 * SalesConditionsCard — RS3 "Patti chiari" + PS5 consolidamento GDPR
 * (docs/RITIRI_INTEGRITA_PIANO_2026-07.md,
 *  docs/POTATURA_STORE_PIANO_2026-07.md onda PS5).
 *
 * Le condizioni dell'operatore in UN posto raggiungibile nel mondo
 * snello (Impostazioni, non dentro Stores):
 * 1. politica di cancellazione di default (scaglioni giorni → %
 *    rimborso), ereditata dal wizard ritiro come "Le mie condizioni"
 * 2. requisiti del servizio (hint: si scrivono per-servizio)
 * 3. dati del titolare per l'informativa autogenerata (mini-form 3
 *    campi che scrive sullo STORE doc: nome, email, paese — gli stessi
 *    campi che l'autogen legge con precedenza, vedi
 *    backend/routers/legal.py::_build_autogen_template_vars)
 * 4. link alla pagina pubblica /s/{slug}/privacy (autogenerata, x4
 *    lingue) + riga DPA art. 28 con stato firmato/da firmare.
 *
 * PS5: l'operatore NON scrive privacy — l'editor legale custom resta
 * raggiungibile SOLO dal mondo legacy (/stores, /newsletter-forms);
 * chi ha gia' pubblicato documenti propri resta servito dall'envelope
 * esistente.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { toast } from 'sonner';
import { ExternalLink, FileSignature, Save, Scale } from 'lucide-react';
import api from '../../../api/client';
import { organizationsAPI } from '../../../api';
import { storesAPI } from '../../../api/stores';

const PRESETS = {
  flessibile: [
    { days_before: 15, refund_percent: 100 },
    { days_before: 5, refund_percent: 50 },
    { days_before: 0, refund_percent: 0 },
  ],
  equilibrata: [
    { days_before: 60, refund_percent: 100 },
    { days_before: 30, refund_percent: 50 },
    { days_before: 0, refund_percent: 0 },
  ],
  rigida: [
    { days_before: 60, refund_percent: 50 },
    { days_before: 30, refund_percent: 25 },
    { days_before: 0, refund_percent: 0 },
  ],
};

export default function SalesConditionsCard() {
  const [policy, setPolicy] = useState(null);   // null = non impostata
  const [saving, setSaving] = useState(false);
  const [store, setStore] = useState(null);
  // PS5 — mini-form titolare (nome, email, paese) + stato DPA
  const [owner, setOwner] = useState({ name: '', email: '', country: '' });
  const [ownerSaving, setOwnerSaving] = useState(false);
  const [dpa, setDpa] = useState(null);         // null = non caricato

  useEffect(() => {
    api.get('/organizations/current')
      .then(res => {
        const p = res.data?.settings?.default_cancellation_policy;
        if (Array.isArray(p) && p.length) setPolicy(p);
      })
      .catch(() => {});
    // lo store tecnico esiste sempre (ensure-default e' idempotente):
    // e' l'indirizzo dove vive l'informativa autogenerata
    storesAPI.ensureDefault()
      .catch(() => {})
      .then(() => storesAPI.list())
      .then(res => {
        const stores = res?.data?.stores || [];
        const s = stores.find(x => x.is_default) || stores[0] || null;
        setStore(s);
        if (s) {
          // precompilazione dai dati correnti dello store: sono gli
          // stessi campi che l'informativa autogenerata legge
          setOwner({
            name: s.name || '',
            email: s.contact_email || '',
            country: s.country || '',
          });
        }
      })
      .catch(() => {});
    // PS5 — stato DPA art. 28 (non bloccante, solo visibile)
    api.get('/legal/dpa/status')
      .then(res => setDpa(res.data))
      .catch(() => {});
  }, []);

  const saveOwner = async () => {
    if (!store) return;
    setOwnerSaving(true);
    try {
      const payload = {
        contact_email: owner.email.trim(),
        country: owner.country.trim(),
      };
      // il nome non puo' essere svuotato (e' il nome dello store doc)
      if (owner.name.trim()) payload.name = owner.name.trim();
      const res = await storesAPI.update(store.id, payload);
      setStore(prev => ({ ...(prev || {}), ...(res?.data || payload) }));
      toast.success("Dati del titolare salvati: l'informativa li usa subito");
    } catch (e) {
      toast.error(e?.response?.data?.detail?.[0]?.msg
        || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setOwnerSaving(false); }
  };

  const rows = policy || PRESETS.equilibrata;

  const updateRow = (idx, field, value) => {
    setPolicy(rows.map((r, i) => i === idx ? { ...r, [field]: value } : r));
  };

  const save = async () => {
    setSaving(true);
    try {
      await organizationsAPI.update({
        default_cancellation_policy: rows.map(r => ({
          days_before: Number(r.days_before),
          refund_percent: Number(r.refund_percent),
        })),
      });
      toast.success('Condizioni salvate: i nuovi ritiri le erediteranno');
    } catch (e) {
      toast.error(e?.response?.data?.detail?.[0]?.msg
        || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setSaving(false); }
  };

  return (
    <Card className="border border-border" data-testid="sales-conditions-card">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Scale className="h-5 w-5" />
          Condizioni dell'operatore
        </CardTitle>
        <CardDescription>
          Le TUE regole, quelle che il cliente accetta quando prenota: politica di
          cancellazione e requisiti specifici del servizio. Ai termini e alla privacy
          della piattaforma pensa Aurya: il cliente li accetta una volta sola, sul
          suo account.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">

        {/* 1. Politica di cancellazione di default */}
        <div>
          <p className="text-sm font-semibold text-foreground">La tua politica di cancellazione</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-2">
            Vale come punto di partenza per ogni nuovo ritiro (nel wizard la trovi
            come "Le mie condizioni"). Ogni ritiro puo' comunque personalizzarla.
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries({ flessibile: 'Flessibile', equilibrata: 'Equilibrata', rigida: 'Rigida' }).map(([k, label]) => (
              <Button key={k} type="button" variant="outline" size="sm"
                      onClick={() => setPolicy(PRESETS[k].map(x => ({ ...x })))}>
                {label}
              </Button>
            ))}
          </div>
          <div className="space-y-2">
            {rows.map((tier, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground w-24 shrink-0">
                  {idx === rows.length - 1 ? 'Dopo, o no show' : 'Fino a'}
                </span>
                {idx < rows.length - 1 && (
                  <>
                    <input type="number" min="0" value={tier.days_before}
                           onChange={e => updateRow(idx, 'days_before', e.target.value)}
                           className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                    <span className="text-muted-foreground">giorni prima</span>
                  </>
                )}
                <span className="text-muted-foreground ml-auto">rimborso</span>
                <input type="number" min="0" max="100" value={tier.refund_percent}
                       onChange={e => updateRow(idx, 'refund_percent', e.target.value)}
                       className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                <span className="text-muted-foreground">%</span>
              </div>
            ))}
          </div>
          <Button size="sm" className="mt-3" disabled={saving || !policy} onClick={save}
                  data-testid="save-cancellation-policy">
            <Save className="mr-1.5 h-4 w-4" />
            Salva la politica
          </Button>
        </div>

        {/* 2. Requisiti del servizio — si scrivono per-servizio */}
        <div className="border-t pt-4" data-testid="service-requirements-hint">
          <p className="text-sm font-semibold text-foreground">Requisiti e condizioni del servizio</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-2">
            Cosa deve sapere o dichiarare il cliente prima di prenotare (es.
            dichiarazione di assenza di controindicazioni mediche). Si scrivono
            sul singolo servizio, nella riga del <a href="/listino" className="underline text-primary">listino</a>,
            o nel passo Regole del wizard ritiro: al checkout compaiono in una
            casella di accettazione dedicata, insieme alla politica di cancellazione.
          </p>
        </div>

        {/* 3. PS5 — dati del titolare per l'informativa autogenerata.
            Scrivono sullo STORE doc (name, contact_email, country): la
            precedenza lato backend fa vincere questi campi sui vecchi
            template_vars, quindi l'informativa e' sempre coerente. */}
        <div className="border-t pt-4" data-testid="owner-data-form">
          <p className="text-sm font-semibold text-foreground">Dati del titolare per l'informativa</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-2">
            Per i dati dei tuoi clienti sei tu il titolare del trattamento:
            questi tre campi compaiono nella tua informativa privacy.
          </p>
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="text-xs text-muted-foreground">
              Nome (attivita' o persona)
              <input type="text" value={owner.name} maxLength={255}
                     onChange={e => setOwner(o => ({ ...o, name: e.target.value }))}
                     data-testid="owner-name-input"
                     className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm text-foreground" />
            </label>
            <label className="text-xs text-muted-foreground">
              Email di contatto
              <input type="email" value={owner.email} maxLength={255}
                     onChange={e => setOwner(o => ({ ...o, email: e.target.value }))}
                     data-testid="owner-email-input"
                     className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm text-foreground" />
            </label>
            <label className="text-xs text-muted-foreground">
              Paese
              <input type="text" value={owner.country} maxLength={100}
                     onChange={e => setOwner(o => ({ ...o, country: e.target.value }))}
                     data-testid="owner-country-input"
                     className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm text-foreground" />
            </label>
          </div>
          <Button size="sm" className="mt-3" disabled={ownerSaving || !store}
                  onClick={saveOwner} data-testid="save-owner-data">
            <Save className="mr-1.5 h-4 w-4" />
            Salva i dati del titolare
          </Button>
          <p className="text-xs text-muted-foreground mt-3">
            La tua informativa privacy viene generata automaticamente con
            questi dati, nelle 4 lingue della piattaforma:{' '}
            {store?.slug ? (
              <a href={`/s/${store.slug}/privacy`} target="_blank" rel="noreferrer"
                 data-testid="autogen-privacy-link"
                 className="inline-flex items-center gap-1 text-primary hover:underline">
                vedila qui
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : (
              <span>vedila dal tuo profilo pubblico</span>
            )}
            . Ai termini e alla privacy della piattaforma pensa Aurya.
          </p>
        </div>

        {/* 4. PS5 — DPA art. 28 in superficie: Aurya tratta i dati dei
            tuoi clienti per conto tuo, l'accordo va confermato. Non
            bloccante, solo visibile. */}
        <div className="border-t pt-4" data-testid="dpa-row">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <p className="text-sm font-semibold text-foreground flex items-center gap-1.5">
              <FileSignature className="h-4 w-4" />
              Accordo sul trattamento dei dati (art. 28)
            </p>
            {dpa?.acknowledged ? (
              <span className="text-xs rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5"
                    data-testid="dpa-status-signed">
                Firmato il {dpa.acknowledged_at
                  ? new Date(dpa.acknowledged_at).toLocaleDateString('it-IT')
                  : '—'}
              </span>
            ) : (
              <span className="text-xs rounded-full bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5"
                    data-testid="dpa-status-pending">
                Da firmare
              </span>
            )}
            <Link to="/settings/legal/dpa"
                  data-testid="dpa-page-link"
                  className="text-sm text-primary hover:underline">
              {dpa?.acknowledged ? 'Rileggi l\'accordo' : 'Leggi e conferma'}
            </Link>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            L'accordo con cui Aurya tratta i dati dei tuoi clienti per conto
            tuo, come richiede il GDPR.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
