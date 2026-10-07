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
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, Sparkles } from 'lucide-react';
import { AppLayout, Header } from '../components/Layout';
import { prodottiAperti } from '../features/prodotti/stato';
import { accademiaAperta } from '../features/accademia/stato';   // AC1
import { useAuth } from '../context/AuthContext';
import { modulesAPI } from '../api/modules';
import { paymentConnectionsAPI } from '../api/paymentConnections';

// P0 (6/10/2026) — la scheda Prodotti si accende con P1 (digitali): finche'
// il wizard non esiste resta «In arrivo», ma dice gia' cosa serve (gli
// incassi collegati) e lo stato lo legge dal registro dei moduli
// (/modules/active), non da una costante.
// 6/10 sera: l'interruttore vive in features/prodotti/stato.js (lo legge
// anche il cancello delle rotte in App.js): finche' e' false la scheda e'
// un'ANTEPRIMA oscurata e /prodotti non si apre.

export default function StrumentiPage() {
  const { user } = useAuth();
  const studioAttivo = !!user?.sound_crea;

  // P0 — il modulo Prodotti nel registro + lo stato degli incassi
  const [moduloProdotti, setModuloProdotti] = useState(null);   // null = non caricato
  const [moduloAccademia, setModuloAccademia] = useState(null);   // AC0 — il modulo Accademia nel registro
  const [incassi, setIncassi] = useState(null);
  useEffect(() => {
    let vivo = true;
    modulesAPI.listActive()
      .then(res => {
        if (!vivo) return;
        const attivi = res.data || [];
        setModuloProdotti(attivi.find(m => m.module_key === 'prodotti') || false);
        setModuloAccademia(attivi.find(m => m.module_key === 'accademia') || false);   // AC0
      })
      .catch(() => { if (vivo) { setModuloProdotti(false); setModuloAccademia(false); } });
    paymentConnectionsAPI.getStatus()
      .then(res => { if (vivo) setIncassi(res.data || null); })
      .catch(() => {});
    return () => { vivo = false; };
  }, []);
  const prodottiNelPiano = !!(moduloProdotti && moduloProdotti.is_active);
  const accademiaNelPiano = !!(moduloAccademia && moduloAccademia.is_active);
  const accademiaAttiva = accademiaNelPiano && accademiaAperta(user);   // anteprima: aperta solo ai piloti
  const prodottiAttivi = prodottiNelPiano && prodottiAperti(user);   // anteprima: aperto solo ai piloti
  const incassiPronti = !!incassi?.checkout_available;

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
    {
      key: 'prodotti',
      nome: 'Prodotti',
      copertina: '/media/hero-blog.webp',
      focus: '50% 40%',
      attivo: prodottiAttivi,
      inArrivo: !prodottiAttivi,
      // testo del founder (6/10 sera)
      claim: 'Porta le tue pratiche anche fuori dalla stanza.',
      descrizione: [
        'Vendi dal tuo profilo Aurya ciò che hai creato: libri, guide, meditazioni, audio, percorsi e kit. '
        + 'Chi ti segue può acquistare direttamente da te, in modo semplice e sicuro.',
        'I prodotti digitali vengono consegnati subito dopo l\'acquisto, mentre per quelli fisici puoi gestire '
        + 'ritiro o spedizione. Gli ordini e gli incassi restano collegati al tuo gestionale, così hai tutto in un unico posto.',
      ],
      dettaglio: prodottiAttivi
        ? (incassiPronti ? 'Incluso nel tuo piano. Incassi collegati.' : 'Incluso nel tuo piano. Prima collega gli incassi.')
        : 'In arrivo: è già previsto nel tuo piano.',
      // l'anteprima: cosa potrai fare, detto prima che si apra (testo del founder)
      anteprima: prodottiAttivi ? null : [
        ['Digitale', 'guide, PDF, audio e altri contenuti, consegnati automaticamente dopo il pagamento.'],
        ['Fisico', 'libri, kit e prodotti da ritirare o spedire.'],
        ['Vendita dal tuo profilo', 'chi ti conosce su Aurya può acquistare direttamente da te.'],
        ['Gestione semplice', 'ordini, pagamenti e prodotti restano collegati al tuo spazio Aurya.'],
      ],
      // in arrivo: NESSUN pulsante (founder: «incassi collegati non significa nulla»)
      azioni: prodottiAttivi
        ? [{ label: 'I miei prodotti', to: '/prodotti', primary: true, testid: 'strumenti-apri-prodotti' }]
        : [],
    },
    {
      // AC0 (6/10/2026) — l'Accademia in ANTEPRIMA: le pagine arrivano con AC1
      key: 'accademia',
      nome: 'Accademia',
      copertina: '/media/hero-destination.webp',
      focus: '50% 45%',
      claim: 'I tuoi percorsi, seguiti da chiunque, ovunque.',
      attivo: accademiaAttiva,
      inArrivo: !accademiaAttiva,
      descrizione: [
        'Crea un corso online con moduli e lezioni video: lo carichi dal browser, Aurya si occupa del resto. '
        + 'Chi lo compra lo segue nel suo account, lezione dopo lezione, con i progressi salvati.',
        'Il corso vive sul tuo profilo con una pagina da condividere; ordini e incassi restano nel tuo gestionale.',
      ],
      dettaglio: accademiaAttiva ? 'Incluso nel tuo piano.' : (accademiaNelPiano ? 'In arrivo: è già previsto nel tuo piano.' : 'In arrivo.'),
      anteprima: accademiaAttiva ? null : [
        ['Lezioni video', 'carichi il file, si codifica da solo, la durata si legge da sola.'],
        ['Moduli e progressi', 'chi studia riprende da dove era e vede il percorso completarsi.'],
        ['Vendita dal profilo', 'una pagina per corso, acquisto con l\'account Aurya, Stripe sul tuo conto.'],
        ['Anteprime gratuite', 'una lezione aperta a tutti, per far capire di cosa si tratta.'],
      ],
      azioni: accademiaAttiva ? [{ label: 'I miei corsi', to: '/accademia', primary: true, testid: 'strumenti-apri-accademia' }] : [],
    },
  ];

  return (
    <AppLayout>
      <Header
        title="Strumenti"
        subtitle="I moduli che espandono la tua pratica. Ne arriveranno altri, sempre qui."
      />
      {/* 6/10 sera (founder: «margini giusti come nelle altre pagine»): lo
          stesso contenitore della Dashboard e di Ordini (p-4 md:p-8), le
          schede allineate in alto e una larghezza massima da lettura */}
      <div className="p-4 md:p-8 animate-fade-in space-y-6" data-testid="strumenti-page">
        <div className="grid max-w-5xl items-start gap-6 lg:grid-cols-2 lg:gap-8">
          {strumenti.map((s) => (
            <div key={s.key} data-testid={`strumento-${s.key}`}
              className={`group overflow-hidden rounded-2xl border bg-white shadow-sm
                         transition duration-200 hover:-translate-y-0.5
                         hover:shadow-[0_18px_40px_-18px_rgba(20,33,43,0.35)]
                         ${s.inArrivo ? 'opacity-[0.82] saturate-[0.85]' : ''}`}
              aria-describedby={s.inArrivo ? `strumento-${s.key}-anteprima` : undefined}>
              {/* la COPERTINA: il mondo dello strumento, con lo stato sopra */}
              <div className="relative h-44 overflow-hidden">
                <img src={s.copertina} alt="" aria-hidden loading="lazy"
                  className="h-full w-full object-cover transition-transform
                             duration-[1200ms] ease-out group-hover:scale-[1.04]"
                  style={{ objectPosition: s.focus }} />
                <div aria-hidden className="absolute inset-0"
                  style={{ background:
                    'linear-gradient(180deg, rgba(14,27,30,.15) 0%, rgba(14,27,30,.72) 100%)' }} />
                <span className={`absolute right-4 top-4 rounded-full border backdrop-blur-sm ${
                    s.attivo
                      ? 'border-emerald-300/60 bg-emerald-950/40 px-2.5 py-0.5 text-[11px] font-medium text-emerald-200'
                      : s.inArrivo
                        ? 'border-amber-200/80 bg-amber-400/95 px-3.5 py-1 text-xs font-semibold uppercase tracking-wide text-amber-950 shadow-sm'
                        : 'border-amber-300/60 bg-amber-950/40 px-2.5 py-0.5 text-[11px] font-medium text-amber-200'}`}
                  data-testid={`strumento-${s.key}-stato`}>
                  {s.attivo ? 'Attivo' : (s.inArrivo ? 'In arrivo' : 'Da attivare')}
                </span>
                <div className="absolute bottom-4 left-5 right-5">
                  <h3 className="font-display text-xl text-white">{s.nome}</h3>
                  <p className="mt-0.5 text-sm text-white/80">{s.claim}</p>
                </div>
              </div>
              <div className="p-5">
                {(Array.isArray(s.descrizione) ? s.descrizione : [s.descrizione]).map((par) => (
                  <p key={par} className="text-sm leading-relaxed text-gray-600 [&+&]:mt-2">{par}</p>
                ))}
                <p className={`mt-3 text-xs ${s.inArrivo ? 'font-semibold text-amber-800' : 'text-gray-400'}`}
                   data-testid={`strumento-${s.key}-dettaglio`}>{s.dettaglio}</p>
                {/* 6/10 sera: l'ANTEPRIMA di uno strumento in arrivo — si capisce
                    cosa arriva, senza un pulsante che promette un clic che non c'e' */}
                {s.anteprima && (
                  <ul id={`strumento-${s.key}-anteprima`} data-testid={`strumento-${s.key}-anteprima`}
                      className="mt-3 space-y-1 rounded-xl bg-gray-50 px-4 py-3 text-xs leading-relaxed text-gray-500">
                    {s.anteprima.map(([titolo, testo]) => (
                      <li key={titolo} className="flex gap-2">
                        <span aria-hidden>·</span>
                        <span><span className="font-medium text-gray-700">{titolo}:</span> {testo}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {s.azioni.length > 0 && (
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
                )}
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
