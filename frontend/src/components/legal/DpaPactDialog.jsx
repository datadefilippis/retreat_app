/**
 * DpaPactDialog — PV7 "Prima di vendere su Aurya"
 * (docs/PROFILO_VERIFICATO_PIANO_2026-07.md).
 *
 * IL patto di responsabilita': un solo concetto, una sola firma.
 * Presenta in modo leggibile:
 *   a. sintesi in 4 punti della responsabilita' dell'operatore
 *      (titolare autonomo dei dati dei SUOI clienti, Aurya responsabile
 *      ex art. 28, condizioni oneste, informativa autogenerata);
 *   b. il testo del DPA scrollabile (riusa GET /api/legal/dpa, la
 *      macchina CG-7 — nessun testo duplicato);
 *   c. link alla SUA informativa autogenerata (/s/{slug}/privacy).
 * Checkbox "Ho letto e accetto" + Accetta → POST /legal/dpa/acknowledge
 * (audit immutabile + stamp durevole sull'org). UNA volta per org: la
 * cache condivisa (useDpaStatus) si aggiorna e il dialog non ricompare.
 *
 * Usato da: ListinoPage e EventWizard (gate alla creazione), banner in
 * /listino e /events. onAccepted permette di RIPRENDERE l'azione che il
 * gate aveva fermato (es. il salvataggio della riga di listino).
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ExternalLink, FileSignature, Loader2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import LegalMarkdownRenderer from './LegalMarkdownRenderer';
import { dpaAPI } from '../../api/auth';
import { storesAPI } from '../../api/stores';
import useDpaStatus, { markDpaAcknowledged } from '../../hooks/useDpaStatus';

const LOCALES = ['it', 'en', 'de', 'fr'];

export default function DpaPactDialog({ open, onOpenChange, onAccepted }) {
  const { t, i18n } = useTranslation('legal');
  const locale = LOCALES.includes(i18n.language) ? i18n.language : 'it';

  const { acknowledged, acknowledgedAt } = useDpaStatus();
  const [doc, setDoc] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [storeSlug, setStoreSlug] = useState(null);
  const [checked, setChecked] = useState(false);
  const [acking, setAcking] = useState(false);

  // Il testo del DPA e lo slug dell'informativa si caricano alla prima
  // apertura (lazy: il dialog spesso non si apre mai).
  useEffect(() => {
    if (!open || doc) return undefined;
    let alive = true;
    dpaAPI.get(locale).then(
      (d) => { if (alive) { setDoc(d); setLoadError(false); } },
      () => { if (alive) setLoadError(true); },
    );
    storesAPI.list()
      .then((res) => {
        if (!alive) return;
        const stores = res?.data?.stores || [];
        const s = stores.find((x) => x.is_default) || stores[0] || null;
        if (s?.slug) setStoreSlug(s.slug);
      })
      .catch(() => { /* link best-effort: senza slug si omette */ });
    return () => { alive = false; };
  }, [open, doc, locale]);

  const handleAccept = async () => {
    if (!checked || acking) return;
    setAcking(true);
    try {
      const result = await dpaAPI.acknowledge(locale);
      // already_acknowledged = idempotente (doppio click, doppia tab):
      // per l'utente e' comunque "fatto", nessun errore.
      markDpaAcknowledged({
        acknowledged_at: result.acknowledged_at,
        locale: result.locale,
        version_tag: result.version_tag,
      });
      toast.success(t('dpa.pact.acceptedToast', {
        defaultValue: 'Patto accettato: puoi vendere su Aurya.',
      }));
      onOpenChange(false);
      onAccepted?.();
    } catch {
      toast.error(t('dpa.pact.acceptError', {
        defaultValue: "L'accettazione non e' andata a buon fine. Riprova.",
      }));
    } finally {
      setAcking(false);
    }
  };

  const points = [
    t('dpa.pact.point1', {
      defaultValue: 'Sei il titolare autonomo dei dati dei tuoi clienti: decidi tu perché e come trattarli.',
    }),
    t('dpa.pact.point2', {
      defaultValue: 'Aurya tratta quei dati per conto tuo, come responsabile ai sensi dell’art. 28 GDPR, secondo l’accordo qui sotto.',
    }),
    t('dpa.pact.point3', {
      defaultValue: 'Ti impegni a vendere con condizioni oneste e a rispondere alle richieste privacy dei tuoi clienti.',
    }),
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl w-[calc(100vw-2rem)] max-h-[88vh] overflow-y-auto"
        data-testid="dpa-pact-dialog"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSignature className="h-5 w-5 text-primary" />
            {t('dpa.pact.title', { defaultValue: 'Prima di vendere su Aurya' })}
          </DialogTitle>
          <DialogDescription>
            {t('dpa.pact.intro', {
              defaultValue: 'Un patto solo, una firma sola: la tua responsabilità verso i tuoi clienti. Dopo, non te lo chiederemo mai più.',
            })}
          </DialogDescription>
        </DialogHeader>

        {acknowledged ? (
          <div
            className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
            data-testid="dpa-pact-already"
          >
            <ShieldCheck className="h-4 w-4 shrink-0" />
            {t('dpa.pact.acceptedBadge', {
              defaultValue: 'Accettato il {{date}}',
              date: acknowledgedAt
                ? new Date(acknowledgedAt).toLocaleDateString(i18n.language)
                : '—',
            })}
          </div>
        ) : (
          <>
            {/* a. sintesi leggibile */}
            <ul className="space-y-2" data-testid="dpa-pact-summary">
              {points.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  {p}
                </li>
              ))}
              <li className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                <span>
                  {t('dpa.pact.point4', {
                    defaultValue: 'La tua informativa privacy è generata automaticamente con i tuoi dati:',
                  })}{' '}
                  {storeSlug ? (
                    <a
                      href={`/s/${storeSlug}/privacy`}
                      target="_blank"
                      rel="noreferrer"
                      data-testid="dpa-pact-privacy-link"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      {t('dpa.pact.privacyLink', { defaultValue: 'vedila qui' })}
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                    </a>
                  ) : (
                    <span className="text-muted-foreground">
                      {t('dpa.pact.privacyLinkFallback', {
                        defaultValue: 'la trovi in Impostazioni → Condizioni dell’operatore',
                      })}
                    </span>
                  )}
                </span>
              </li>
            </ul>

            {/* b. testo del DPA scrollabile (macchina CG-7 riusata) */}
            <div
              className="max-h-56 overflow-y-auto rounded-md border border-border bg-muted/30 p-3"
              data-testid="dpa-pact-doc"
            >
              {loadError && (
                <p className="text-sm text-red-700">
                  {t('dpa.pact.loadError', {
                    defaultValue: 'Il testo dell’accordo non si carica. Riprova tra poco.',
                  })}
                </p>
              )}
              {!doc && !loadError && (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  {t('dpa.pact.loading', { defaultValue: 'Carico l’accordo…' })}
                </p>
              )}
              {doc && <LegalMarkdownRenderer content={doc.content} />}
            </div>

            {/* c. firma */}
            <label className="flex cursor-pointer items-start gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => setChecked(e.target.checked)}
                className="mt-0.5 rounded border-gray-300"
                data-testid="dpa-pact-checkbox"
              />
              {t('dpa.pact.checkbox', {
                defaultValue: 'Ho letto e accetto l’accordo sul trattamento dei dati (art. 28) e la mia responsabilità di titolare.',
              })}
            </label>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={acking}>
                {t('dpa.pact.later', { defaultValue: 'Non ora' })}
              </Button>
              <Button
                onClick={handleAccept}
                disabled={!checked || acking || !doc}
                data-testid="dpa-pact-accept"
              >
                {acking && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden />}
                {t('dpa.pact.accept', { defaultValue: 'Accetta e continua' })}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
