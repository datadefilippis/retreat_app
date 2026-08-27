/**
 * /strumenti — GLI STRUMENTI DELL'OPERATORE (TR6 + NV1, 27/8/2026).
 *
 * La casa dei moduli premium del gestionale: oggi Aurya Sound Studio,
 * domani i moduli che verranno — sempre qui, sempre con lo stesso
 * patto. Ogni carta dice tre cose: cos'e', se ce l'hai, il gesto
 * giusto (APRI se attivo, ATTIVA IL PRO se no — il pagamento resta
 * su /plans: questa e' una vetrina, non una cassa).
 *
 * NV1 (revisione founder): ogni strumento ha la sua COPERTINA — per
 * Sound Studio la spirale di luce, la stessa identita' della landing
 * /sound/studio. Il badge di stato vive sull'immagine; la carta e'
 * cover-top, moderna, con il rialzo all'hover.
 *
 * Lo stato arriva da user.sound_crea, derivato dal server a ogni
 * /auth/me — la stessa verita' del portiere delle API.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, Sparkles } from 'lucide-react';
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
      copertina: '/media/sound/spirale.jpg',
      focus: '62% 55%',
      attivo: studioAttivo,
      claim: 'La tua voce, le tue meditazioni.',
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
        <div className="grid gap-6 lg:grid-cols-2">
          {strumenti.map((s) => (
            <div key={s.key} data-testid={`strumento-${s.key}`}
              className="group overflow-hidden rounded-2xl border bg-white shadow-sm
                         transition duration-200 hover:-translate-y-0.5
                         hover:shadow-[0_18px_40px_-18px_rgba(20,33,43,0.35)]">
              {/* la COPERTINA: il mondo dello strumento, con lo stato sopra */}
              <div className="relative h-44 overflow-hidden">
                <img src={s.copertina} alt="" aria-hidden loading="lazy"
                  className="h-full w-full object-cover transition-transform
                             duration-[1200ms] ease-out group-hover:scale-[1.04]"
                  style={{ objectPosition: s.focus }} />
                <div aria-hidden className="absolute inset-0"
                  style={{ background:
                    'linear-gradient(180deg, rgba(14,27,30,.15) 0%, rgba(14,27,30,.72) 100%)' }} />
                <span className={`absolute right-4 top-4 rounded-full border px-2.5
                                  py-0.5 text-[11px] font-medium backdrop-blur-sm ${
                    s.attivo
                      ? 'border-emerald-300/60 bg-emerald-950/40 text-emerald-200'
                      : 'border-amber-300/60 bg-amber-950/40 text-amber-200'}`}
                  data-testid={`strumento-${s.key}-stato`}>
                  {s.attivo ? 'Attivo' : 'Da attivare'}
                </span>
                <div className="absolute bottom-4 left-5 right-5">
                  <h3 className="font-display text-xl text-white">{s.nome}</h3>
                  <p className="mt-0.5 text-sm text-white/80">{s.claim}</p>
                </div>
              </div>
              <div className="p-5">
                <p className="text-sm leading-relaxed text-gray-600">
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
          ))}

          {/* il posto dei prossimi: dichiarato, non finto */}
          <div className="flex min-h-[280px] items-center justify-center rounded-2xl
                          border border-dashed p-6 text-center"
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
