/**
 * /accademia — I TUOI CORSI (AC1, 7/10/2026). Stesso stampo di /prodotti:
 * prerequisiti (riga verde quando ci sono), la quota video del piano, la
 * lista dei corsi (copertina, stato, lezioni pronte, durata, prezzo,
 * studenti), «Nuovo corso» → wizard in tre gesti.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle, ChevronRight, GraduationCap, Loader2, Plus, Users } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { accademiaAPI, fmtDurata } from '../../api/accademia';
import { fmtEuro } from '../../api/prodotti';
import { Bottone, Scheda, Vignetta, urlPagina } from '../prodotti/ui';

function Prerequisito({ ok, label, hint, to, testid }) {
  return (
    <li className="flex items-start gap-3" data-testid={testid}>
      {ok ? <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-emerald-600" aria-hidden /> : <AlertCircle className="mt-0.5 h-5 w-5 flex-none text-amber-600" aria-hidden />}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {!ok && hint && <p className="mt-0.5 text-xs leading-snug text-gray-500">{hint}</p>}
      </div>
      {!ok && to && <Link to={to} className="inline-flex min-h-[36px] items-center gap-1 rounded-full border border-gray-200 px-3 text-xs font-medium text-gray-800 hover:bg-gray-50">Vai <ChevronRight className="h-3.5 w-3.5" aria-hidden /></Link>}
    </li>
  );
}

export default function AccademiaPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [errore, setErrore] = useState(null);

  const load = useCallback(() => {
    accademiaAPI.list().then(res => setData(res.data)).catch(err => {
      const d = err?.response?.data?.detail;
      setErrore(d?.error === 'module_not_active' ? (d.message || "L'Accademia non è attiva per la tua organizzazione.") : 'Non riesco a caricare i corsi. Riprova fra poco.');
    });
  }, []);
  useEffect(() => { load(); }, [load]);

  const pre = data?.prerequisiti || {};
  const pronto = !!(pre.stripe_pronto && pre.patto && pre.pagina_pubblica);
  const corsi = data?.corsi || [];
  const quota = data?.quota_video;

  const copiaLink = async (c) => {
    const url = urlPagina(data?.public_slug, c.slug, 'corso');
    if (!url) return;
    try { await navigator.clipboard.writeText(url); toast.success('Link della pagina copiato.'); } catch { toast.error('Non sono riuscito a copiare il link.'); }
  };
  const togli = async (c) => {
    if (!window.confirm(`Togliere «${c.title}» dal catalogo? Chi l'ha già comprato continua a seguirlo.`)) return;
    try { await accademiaAPI.elimina(c.id); toast.success('Corso tolto.'); load(); }
    catch { toast.error('Non sono riuscito a toglierlo.'); }
  };

  return (
    <AppLayout>
      <Header title="Accademia" subtitle="I tuoi corsi online: chi li compra li segue nel suo account Aurya.">
        <Bottone onClick={() => navigate('/accademia/nuovo')} data-testid="accademia-nuovo" className="min-h-[40px]">
          <Plus className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">Nuovo corso</span><span className="sm:hidden">Nuovo</span>
        </Bottone>
      </Header>
      <div className="p-4 md:p-8 animate-fade-in max-w-4xl space-y-5" data-testid="accademia-page">
        {errore && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid="accademia-errore">{errore}</div>}

        {data && (pronto ? (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" data-testid="accademia-prerequisiti">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />
            <span className="font-medium">Sei pronto a vendere.</span>
            <span className="text-emerald-800/80">Incassi collegati, patto accettato, pagina online.</span>
          </div>
        ) : (
          <Scheda title="Prima di vendere" sub="Tre cose, una volta sola." data-testid="accademia-prerequisiti">
            <ul className="space-y-3">
              <Prerequisito ok={pre.stripe_pronto} testid="pre-stripe" label="Incassi collegati con Stripe" hint={pre.stripe_motivo || 'I corsi si pagano subito, online, sul tuo conto.'} to="/settings" />
              <Prerequisito ok={pre.patto} testid="pre-patto" label="Patto di responsabilità accettato" hint="Lo stesso di listino e ritiri: in Impostazioni → Condizioni dell'operatore." to="/settings" />
              <Prerequisito ok={pre.pagina_pubblica} testid="pre-pagina" label="La tua pagina pubblica è online" hint="Senza la pagina non c'è dove comprare." to="/profilo" />
            </ul>
          </Scheda>
        ))}

        {data && !data.bunny_attivo && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900" data-testid="accademia-bunny-spento">
            Il caricamento dei video non è ancora attivo su questo ambiente: puoi già creare i corsi, scrivere lezioni di testo e preparare i titoli.
          </p>
        )}

        {!data && !errore && <Loader2 className="h-5 w-5 animate-spin text-gray-400" />}
        {data && corsi.length === 0 && (
          <div className="rounded-2xl border border-dashed border-gray-300 p-8 text-center" data-testid="accademia-vuoto">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]"><GraduationCap className="h-6 w-6" aria-hidden /></span>
            <p className="mt-3 font-medium text-gray-900">Ancora nessun corso.</p>
            <p className="mt-1 text-sm text-gray-500">Il primo lo crei in tre gesti: il corso, le lezioni, pubblica.</p>
            <Bottone variante="secondario" onClick={() => navigate('/accademia/nuovo')} className="mt-4"><Plus className="h-4 w-4" aria-hidden /> Nuovo corso</Bottone>
          </div>
        )}
        {corsi.length > 0 && (
          <ul className="space-y-3" data-testid="accademia-lista">
            {corsi.map(c => (
              <li key={c.id} data-testid={`corso-${c.id}`} className="rounded-2xl border border-gray-200/80 bg-white p-3 shadow-[0_1px_2px_rgba(16,24,40,0.04)] transition hover:border-gray-300 sm:p-4">
                <div className="flex gap-3 sm:gap-4">
                  <Link to={`/accademia/${c.id}`} className="flex-none" aria-label={`Apri ${c.title}`}>
                    <Vignetta prodotto={{ image_url: c.cover_image_url, item_type: 'digital' }} className="h-20 w-28 rounded-xl sm:h-24 sm:w-36" />
                  </Link>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <Link to={`/accademia/${c.id}`} className="min-w-0 font-semibold leading-snug text-gray-900 line-clamp-2 hover:underline">{c.title}</Link>
                      <span className={`flex-none rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${c.is_published ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'}`} data-testid={`corso-${c.id}-stato`}>
                        {c.is_published ? 'Online' : 'Bozza'}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-xs text-gray-500">
                      {c.lezioni_pronte}/{c.lezioni_count} lezion{c.lezioni_count === 1 ? 'e' : 'i'} pront{c.lezioni_pronte === 1 ? 'a' : 'e'}
                      {c.durata_totale_seconds ? ` · ${fmtDurata(c.durata_totale_seconds)}` : ''} · {c.access_etichetta}{c.categoria_label ? ` · ${c.categoria_label}` : ''}
                    </p>
                    <div className="mt-2 flex items-baseline gap-3">
                      <span className="text-base font-bold text-[#2f5749]">{c.unit_price != null ? fmtEuro(c.unit_price) : 'Senza prezzo'}</span>
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500"><Users className="h-3.5 w-3.5" aria-hidden /> {c.studenti} student{c.studenti === 1 ? 'e' : 'i'}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
                  <Link to={`/accademia/${c.id}`} className="inline-flex min-h-[36px] items-center rounded-full border border-gray-200 px-4 text-xs font-medium text-gray-800 hover:bg-gray-50">Modifica</Link>
                  {c.is_published && c.slug && (
                    <button type="button" onClick={() => copiaLink(c)} className="inline-flex min-h-[36px] items-center rounded-full border border-gray-200 px-4 text-xs font-medium text-gray-800 hover:bg-gray-50" data-testid={`corso-${c.id}-link`}>Copia link</button>
                  )}
                  {!c.is_published && c.ragioni_pubblicazione?.length > 0 && <span className="text-xs text-amber-800">{c.ragioni_pubblicazione[0]}</span>}
                  <button type="button" onClick={() => togli(c)} className="ml-auto min-h-[36px] px-2 text-xs text-gray-400 hover:text-red-700">Togli</button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {data && (
          <p className="text-xs leading-relaxed text-gray-500" data-testid="accademia-commissione">
            {data.commissione?.course > 0
              ? <>Sui corsi venduti Aurya trattiene il <b className="text-gray-700">{data.commissione.course}%</b> col tuo piano, più i costi Stripe.</>
              : <>Col tuo piano Aurya non trattiene commissioni sui corsi: resta solo il costo di Stripe.</>}
            {' '}<Link to="/costi" className="underline">Come funziona</Link>
            {data.limiti?.corsi_max > 0 && <> · Il tuo piano: fino a {data.limiti.corsi_max} corsi, {data.limiti.lezioni_max} lezioni per corso, {data.limiti.video_gb} GB di video{quota ? ` (usati ${quota.usati_gb} GB)` : ''}.</>}
          </p>
        )}
      </div>
    </AppLayout>
  );
}
