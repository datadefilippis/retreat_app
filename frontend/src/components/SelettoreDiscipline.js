/**
 * SelettoreDiscipline — UN modo solo di scegliere le discipline (24/9/2026,
 * founder: «abbiamo raggiunto molte categorie, orientarsi è complicato»).
 *
 * 52 voci in 7 famiglie non si mostrano tutte insieme. Il processo, in
 * due mosse:
 *   1. CERCA: scrivi come parli («psicologa», «massaggiatrice», «gestalt»)
 *      e trovi la voce, anche per sinonimo (lib/disciplines CERCA_ANCHE);
 *   2. oppure SFOGLIA: le famiglie sono righe chiuse («Corpo & Movimento ·
 *      9 voci»), se ne apre una alla volta; sopra, «Le più scelte» per
 *      partire subito.
 * Le scelte stanno sempre in alto, con la × per toglierle, e il contatore
 * x/10. Stesso componente nell'editor del profilo e in /benvenuto: una
 * sola cosa da mantenere, gli stessi data-testid (pp-disc-*).
 *
 * Il toggle e' FUNZIONALE (onToggle(slug), il padre aggiorna con
 * setState(f => …)): due tap ravvicinati non si sovrascrivono (DI2).
 */
import React, { useMemo, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import {
  DISCIPLINE_FAMILIES, DISCIPLINES_MAX, PIU_SCELTE, cercaDiscipline, disciplineLabel,
} from '../lib/disciplines';

const chipCls = (sel, full) => `rounded-full border px-3 py-1 text-xs transition-colors ${
  sel ? 'border-[#376254] bg-[#376254] text-white'
    : full ? 'border-input text-muted-foreground/40 cursor-not-allowed'
      : 'border-input text-foreground hover:border-[#8a9979] hover:bg-[#376254]/5'}`;

export default function SelettoreDiscipline({
  value = [], onToggle, query = '', onQuery, max = DISCIPLINES_MAX,
  placeholder = 'Cerca: yoga, reiki, psicoterapia, massaggio…', autoFocus = false,
}) {
  const [aperta, setAperta] = useState(null);      // una famiglia alla volta
  const scelte = value || [];
  const full = scelte.length >= max;
  const q = (query || '').trim();
  const risultati = useMemo(() => (q ? cercaDiscipline(q) : []), [q]);

  const Chip = ({ d }) => {
    const sel = scelte.includes(d.slug);
    return (
      <button key={d.slug} type="button" disabled={!sel && full}
        data-testid={`pp-disc-${d.slug}`}
        onClick={() => onToggle(d.slug)}
        className={chipCls(sel, !sel && full)}>
        {d.label}
      </button>
    );
  };

  return (
    <div className="space-y-3" data-testid="selettore-discipline">
      {/* 0. le scelte, sempre in alto */}
      <div className="flex flex-wrap items-center gap-1.5 min-h-[28px]" data-testid="disc-scelte">
        {scelte.length === 0 ? (
          <span className="text-xs text-muted-foreground">Nessuna disciplina scelta: cerca qui sotto o sfoglia le famiglie.</span>
        ) : scelte.map((s) => (
          <span key={s} className="inline-flex items-center gap-1 rounded-full bg-[#376254] text-white px-2.5 py-0.5 text-xs">
            {disciplineLabel(s)}
            <button type="button" aria-label={`Togli ${disciplineLabel(s)}`} onClick={() => onToggle(s)}
              className="rounded-full hover:bg-white/20 p-0.5"><X className="h-3 w-3" aria-hidden /></button>
          </span>
        ))}
        <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">{scelte.length}/{max}</span>
      </div>

      {/* 1. cerca */}
      <input value={query} onChange={(e) => onQuery(e.target.value)} autoFocus={autoFocus}
        placeholder={placeholder} data-testid="disc-search" aria-label="Cerca una disciplina"
        className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />

      {q ? (
        risultati.length === 0 ? (
          <p className="text-xs text-muted-foreground" data-testid="disc-nessuna">
            Nessuna voce per «{q}». Prova con un'altra parola, oppure sfoglia le famiglie cancellando la ricerca.
          </p>
        ) : (
          <div className="space-y-2" data-testid="disc-risultati">
            {DISCIPLINE_FAMILIES.map((fam) => {
              const dentro = risultati.filter((d) => fam.items.some((i) => i.slug === d.slug));
              if (!dentro.length) return null;
              return (
                <div key={fam.slug}>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">{fam.label}</p>
                  <div className="flex flex-wrap gap-1.5">{dentro.map((d) => <Chip key={d.slug} d={d} />)}</div>
                </div>
              );
            })}
          </div>
        )
      ) : (
        <>
          {/* 2a. le più scelte: per partire senza sfogliare */}
          {PIU_SCELTE.some((s) => !scelte.includes(s)) && (
            <div data-testid="disc-piu-scelte">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">Le più scelte</p>
              <div className="flex flex-wrap gap-1.5">
                {PIU_SCELTE.filter((s) => !scelte.includes(s)).map((s) => <Chip key={s} d={{ slug: s, label: disciplineLabel(s) }} />)}
              </div>
            </div>
          )}
          {/* 2b. le famiglie, chiuse: una riga ciascuna, se ne apre una */}
          <div className="rounded-lg border divide-y" data-testid="disc-famiglie">
            {DISCIPLINE_FAMILIES.map((fam) => {
              const n = fam.items.filter((d) => scelte.includes(d.slug)).length;
              const open = aperta === fam.slug;
              return (
                <div key={fam.slug}>
                  <button type="button" onClick={() => setAperta(open ? null : fam.slug)}
                    aria-expanded={open} data-testid={`disc-fam-${fam.slug}`}
                    className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-muted/40">
                    <span className="font-medium">{fam.label}</span>
                    <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      {n > 0 ? <span className="rounded-full bg-[#376254]/10 text-[#376254] px-2 py-0.5">{n} {n === 1 ? 'scelta' : 'scelte'}</span> : <span>{fam.items.length} voci</span>}
                      <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
                    </span>
                  </button>
                  {open && (
                    <div className="flex flex-wrap gap-1.5 px-3 pb-3">
                      {fam.items.map((d) => <Chip key={d.slug} d={d} />)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
