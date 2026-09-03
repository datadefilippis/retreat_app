/**
 * MiniCalendario — l'agenda dell'operatore in vetrina (IG3, 3/9/2026).
 *
 * Disegnato SUI DATI CHE IL PROFILO GIÀ RICEVE (data.upcoming: i
 * ritiri/eventi futuri): zero API nuove. I giorni con qualcosa in
 * agenda si accendono in verde; il tap porta alla pagina dell'evento
 * (il percorso di prenotazione esistente). Se l'agenda è vuota, il
 * calendario NON si monta: mai una griglia vuota in vetrina.
 * Mostra il mese del primo appuntamento futuro (non per forza il
 * corrente: un'agenda di ottobre si mostra a ottobre).
 */
import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';

const GIORNI = ['L', 'M', 'M', 'G', 'V', 'S', 'D'];
const MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];

export default function MiniCalendario({ upcoming, t }) {
  const quadro = useMemo(() => {
    const eventi = (upcoming || [])
      .filter((e) => e.start_at)
      .map((e) => ({ ...e, inizio: new Date(e.start_at),
        fine: new Date(e.end_at || e.start_at) }))
      .filter((e) => !Number.isNaN(e.inizio.getTime()));
    if (!eventi.length) return null;
    const primo = eventi.reduce((a, b) => (a.inizio < b.inizio ? a : b));
    const anno = primo.inizio.getFullYear();
    const mese = primo.inizio.getMonth();
    /* i giorni accesi: ogni giorno coperto da un evento del mese */
    const accesi = new Map();
    eventi.forEach((e) => {
      const d = new Date(e.inizio);
      while (d <= e.fine) {
        if (d.getFullYear() === anno && d.getMonth() === mese) {
          if (!accesi.has(d.getDate())) accesi.set(d.getDate(), e.url);
        }
        d.setDate(d.getDate() + 1);
      }
    });
    const primoGiorno = (new Date(anno, mese, 1).getDay() + 6) % 7; // lun=0
    const nGiorni = new Date(anno, mese + 1, 0).getDate();
    return { anno, mese, accesi, primoGiorno, nGiorni };
  }, [upcoming]);

  if (!quadro) return null;
  const celle = [
    ...Array.from({ length: quadro.primoGiorno }, () => null),
    ...Array.from({ length: quadro.nGiorni }, (_, i) => i + 1),
  ];
  return (
    <section id="calendario" className="mt-8 scroll-mt-20"
      data-testid="profile-calendario">
      <h2 className="profile-h2 font-heading text-xl font-bold text-foreground mb-3 flex items-center gap-2.5 before:content-[''] before:h-5 before:w-1 before:rounded-full before:bg-[#c9b37e]">
        {t('landings:operator.calendar', { defaultValue: 'Calendario' })}
      </h2>
      <div className="rounded-2xl border border-gray-200 bg-white p-4 max-w-sm">
        <p className="text-sm font-semibold text-gray-800 mb-3">
          {MESI[quadro.mese]} {quadro.anno}
        </p>
        <div className="grid grid-cols-7 gap-1 text-center">
          {GIORNI.map((g, i) => (
            <span key={`${g}${i}`} className="text-[11px] font-medium text-gray-400">{g}</span>
          ))}
          {celle.map((giorno, i) => {
            if (!giorno) return <span key={`v${i}`} />;
            const url = quadro.accesi.get(giorno);
            return url ? (
              <Link key={giorno} to={url}
                title={t('landings:operator.calendarDay', { defaultValue: 'Vedi cosa c’è in programma' })}
                className="aspect-square flex items-center justify-center rounded-full
                           bg-[#376254] text-white text-xs font-semibold
                           hover:bg-[#2c4f43] transition-colors">
                {giorno}
              </Link>
            ) : (
              <span key={giorno}
                className="aspect-square flex items-center justify-center text-xs text-gray-500">
                {giorno}
              </span>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-gray-500">
          {t('landings:operator.calendarHint', { defaultValue: 'I giorni in verde hanno un appuntamento in programma: tocca per vedere.' })}
        </p>
      </div>
    </section>
  );
}
