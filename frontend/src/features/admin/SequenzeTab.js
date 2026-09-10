/**
 * SequenzeTab — «Email automatiche» (FV4 → SA-R, 10/9/2026 sera).
 *
 * Il founder legge ogni email delle sequenze prima che parta, per un
 * destinatario vero (email) o fittizio, e puo' MANDARSELA come prova
 * («voglio vedere le email in anteprima e poterle mandare»). Viveva in
 * fondo alla Panoramica e non si trovava: ora e' un tab della pagina
 * Iscritti al Cerchio, accanto alle persone che le ricevono.
 * Stesso codice che invia; l'anteprima non parte e non marca niente,
 * la prova parte solo verso l'indirizzo scritto qui.
 */
import React, { useEffect, useState } from 'react';
import { Send } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { Button } from '../../components/ui/button';
import { useAuth } from '../../context/AuthContext';

const PUBBLICI = { operatore: 'operatore', cerchio: 'Cerchio' };

export default function SequenzeTab() {
  const { user } = useAuth();
  const [passi, setPassi] = useState(null);
  const [pubblico, setPubblico] = useState('operatore');
  const [passo, setPasso] = useState('np5');
  const [email, setEmail] = useState('');
  const [a, setA] = useState(user?.email || '');
  const [reso, setReso] = useState(null);
  const [caricando, setCaricando] = useState(false);
  const [mando, setMando] = useState(false);

  useEffect(() => {
    api.get('/admin/platform/sequenze/passi').then((r) => setPassi(r.data?.pubblici || null)).catch(() => setPassi({}));
  }, []);
  useEffect(() => { if (user?.email && !a) setA(user.email); }, [user, a]);

  const mostra = async () => {
    setCaricando(true);
    try {
      const r = await api.get('/admin/platform/sequenze/anteprima', { params: { pubblico, passo, email: email || undefined } });
      setReso(r.data);
    } catch {
      setReso({ nota: 'Anteprima non disponibile.' });
    } finally { setCaricando(false); }
  };

  const manda = async () => {
    if (!a.trim()) { toast.error('Scrivi a chi mandare la prova'); return; }
    setMando(true);
    try {
      const r = await api.post('/admin/platform/sequenze/prova', { pubblico, passo, email: email || null, a: a.trim() });
      toast.success(r.data?.inviata ? `Prova mandata a ${a.trim()}` : `Nessuna prova: ${r.data?.nota || 'niente da mandare'}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Invio non riuscito');
    } finally { setMando(false); }
  };

  const elenco = (passi && passi[pubblico]) || [];
  const sel = 'mt-1 block rounded-md border border-border bg-background px-2 py-1.5 text-sm';
  return (
    <div data-testid="sequenze-anteprima" className="rounded-2xl border border-border bg-card p-4 md:p-6">
      <p className="font-heading text-lg font-semibold text-foreground">Le email automatiche, in anteprima</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Scegli il pubblico e il passo. Con l’email di una persona vera vedi l’email come la riceverebbe lei
        (e la nota ti dice quale variante le partirebbe davvero). Da «Mostra» non parte niente;
        «Mandami una prova» la spedisce solo all’indirizzo che scrivi.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs">Pubblico
          <select value={pubblico}
                  onChange={(e) => { setPubblico(e.target.value); const primo = (passi?.[e.target.value] || [])[0]; if (primo) setPasso(primo.nome); setReso(null); }}
                  className={sel} data-testid="seq-pubblico">
            {Object.entries(PUBBLICI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="text-xs">Passo
          <select value={passo} onChange={(e) => { setPasso(e.target.value); setReso(null); }} className={sel} data-testid="seq-passo">
            {elenco.map((p) => (
              <option key={p.nome} value={p.nome}>
                {p.nome}{p.giorno != null ? ` · giorno ${p.giorno}` : ' · evento'}{p.a === 'admin' ? ' · a noi' : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs">Come la vedrebbe (email, facoltativa)
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="una persona vera"
                 className={`${sel} w-56`} data-testid="seq-email" />
        </label>
        <Button size="sm" onClick={mostra} disabled={caricando} data-testid="seq-mostra">{caricando ? 'Carico…' : 'Mostra'}</Button>
      </div>
      {elenco.length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          {elenco.find((p) => p.nome === passo)?.titolo}
        </p>
      )}
      {reso && (
        <div className="mt-5">
          {reso.oggetto ? (
            <>
              <p className="text-sm"><span className="text-muted-foreground">A:</span> {reso.destinatario}{reso.trovato ? '' : ' (destinatario fittizio)'}</p>
              {reso.nota && <p className="text-sm text-amber-700" data-testid="seq-nota">{reso.nota}</p>}
              <p className="text-sm font-semibold" data-testid="seq-oggetto">{reso.oggetto}</p>
              <iframe title="anteprima email" srcDoc={reso.html} className="mt-2 h-[560px] w-full rounded-md border border-border bg-white" />
              <div className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-dashed border-border p-3">
                <label className="text-xs">Mandami una prova a
                  <input value={a} onChange={(e) => setA(e.target.value)} placeholder="la tua email"
                         className={`${sel} w-64`} data-testid="seq-prova-a" />
                </label>
                <Button size="sm" variant="outline" onClick={manda} disabled={mando} data-testid="seq-prova">
                  <Send className="mr-1 h-4 w-4" />{mando ? 'Mando…' : 'Mandami una prova'}
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground" data-testid="seq-nota">{reso.nota || 'Niente da mostrare.'}</p>
          )}
        </div>
      )}
    </div>
  );
}
