/**
 * /strumenti — GLI STRUMENTI DELL'OPERATORE (TR6, 27/8/2026).
 *
 * La casa dei moduli premium del gestionale, voluta dal founder: oggi
 * ospita Aurya Sound Studio, domani i moduli che verranno — sempre
 * qui, sempre con lo stesso patto. Ogni carta dice tre cose: cos'e',
 * se ce l'hai, e il gesto giusto — APRI se e' attivo, ATTIVA IL PRO
 * se non lo e' (il pagamento resta sulla pagina piani esistente:
 * questa e' una vetrina, non una cassa).
 *
 * NON e' la vecchia /modules (attivazione tecnica dei moduli inclusi,
 * oggi solo-sysadmin per scelta CS3b): quella governa cosa e' acceso
 * dentro un piano, questa racconta cosa il piano puo' DARE. Lo stato
 * di Sound Studio arriva da user.sound_crea, derivato dal server a
 * ogni /auth/me — la stessa verita' del portiere delle API.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { AudioWaveform, ExternalLink, Sparkles } from 'lucide-react';
import { AppLayout, Header } from '../components/Layout';
import { useAuth } from '../context/AuthContext';

export default function StrumentiPage() {
  const { user } = useAuth();
  const studioAttivo = !!user?.sound_crea;

  /* il registro delle carte: aggiungerne una domani = una voce qui */
  const strumenti = [
    {
      key: 'sound_studio',
      nome: 'Aurya Sound Studio',
      icona: AudioWaveform,
      attivo: studioAttivo,
      descrizione:
        'Componi meditazioni con la tua voce, basi sonore e frequenze, '
        + 'direttamente dal browser. Le condividi in privato coi tuoi '
        + 'clienti: un link a persona, revocabile quando vuoi.',
      dettaglio: studioAttivo
        ? 'Incluso nel tuo piano.'
        : 'Si accende con il piano Aurya Pro.',
      azioni: studioAttivo
        ? [
          { label: 'Apri lo Studio', to: '/sound/crea', primary: true,
            testid: 'strumenti-apri-studio' },
          { label: 'Le mie tracce', to: '/sound/tracce' },
        ]
        : [
          { label: 'Attiva Aurya Pro', to: '/plans', primary: true,
            testid: 'strumenti-attiva-pro' },
          { label: 'Scopri Crea Studio', to: '/sound/studio' },
        ],
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="strumenti-page">
        <Header
          title="Strumenti"
          subtitle="I moduli che espandono la tua pratica. Ne arriveranno altri, sempre qui."
        />
        <div className="grid gap-5 lg:grid-cols-2">
          {strumenti.map((s) => (
            <div key={s.key} data-testid={`strumento-${s.key}`}
              className="relative overflow-hidden rounded-2xl border bg-white p-6 shadow-sm">
              <span aria-hidden
                className="absolute left-6 right-6 top-0 h-1 rounded-b"
                style={{ background: s.attivo ? '#2f5749' : '#c9b37e' }} />
              <div className="flex items-start gap-4">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl"
                  style={{ background: 'rgba(201,179,126,.15)', color: '#7d6a3a' }}>
                  <s.icona className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-gray-900">{s.nome}</h3>
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      s.attivo
                        ? 'border-emerald-300 text-emerald-700'
                        : 'border-amber-300 text-amber-700'}`}
                      data-testid={`strumento-${s.key}-stato`}>
                      {s.attivo ? 'Attivo' : 'Da attivare'}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">
                    {s.descrizione}
                  </p>
                  <p className="mt-2 text-xs text-gray-400">{s.dettaglio}</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    {s.azioni.map((a) => (
                      <Link key={a.label} to={a.to} data-testid={a.testid}
                        className={a.primary
                          ? 'inline-flex items-center gap-1.5 rounded-full px-4 py-2 '
                            + 'text-sm font-medium text-white transition hover:opacity-90'
                          : 'inline-flex items-center gap-1.5 rounded-full border px-4 '
                            + 'py-2 text-sm text-gray-700 transition hover:bg-gray-50'}
                        style={a.primary ? { background: '#2f5749' } : undefined}>
                        {a.label}
                        {!a.primary && <ExternalLink className="h-3.5 w-3.5" />}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* il posto dei prossimi: dichiarato, non finto */}
          <div className="flex items-center justify-center rounded-2xl border
                          border-dashed p-6 text-center"
            data-testid="strumenti-prossimi">
            <div className="text-gray-400">
              <Sparkles className="mx-auto mb-2 h-5 w-5" />
              <p className="text-sm">
                Qui arriveranno i prossimi strumenti di Aurya.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
