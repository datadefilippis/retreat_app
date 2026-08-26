/**
 * IL RITO DELLA SESSIONE (S3, 26/8/2026).
 *
 * Tre momenti, come in uno studio: la PREPARAZIONE (con chi, come si
 * sente), l'ASCOLTO (schermo pulito, solo il tempo che resta), il
 * CONGEDO (come si sente ora, e le note dell'operatore). Alla fine la
 * sessione sta nel registro — è quello il prodotto.
 *
 * QUI NON C'È UN PLAYER NUOVO: l'ascolto è creaAscolto, il player
 * condiviso delle esperienze — ponte iOS, wake lock, sorveglianza del
 * contesto e avviso cuffie stanno già lì dentro. Questo componente
 * orchestra e registra, non suona.
 *
 * L'ORDINE DELL'AVVIO, e il suo perché: prima il suono, poi il
 * server. `avvia()` deve partire DENTRO il gesto (l'AudioContext lo
 * esige); la registrazione della sessione parte subito dopo, e se il
 * server rifiuta si spegne tutto e si dice perché. Il contrario —
 * prima il server, poi il suono — metterebbe una attesa di rete fra
 * il dito e il contesto audio.
 *
 * GLI ESITI SONO ONESTI, uno per strada:
 *   arriva in fondo da solo        → completata
 *   l'operatore preme Termina      → interrotta
 *   il contesto muore (onPerso)    → PERSA, chiusa SUBITO sul server
 *                                    (il vissuto si completa dopo,
 *                                    con l'aggiornamento)
 * L'ascolto dichiarato è trascorso() del player; il server lo cappa
 * comunque — un numero riferito, reso onesto due volte.
 *
 * IL VISSUTO: «da 1 a 10» è la risposta della persona, riportata
 * dall'operatore. Non è una misura, non promette niente, e resta
 * l'unico dato d'esito finché non esisteranno misure vere (S7+, in
 * una collezione separata).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { customersAPI } from '../../../api/customers';
import { soundProAPI } from '../../../api/soundPro';
import { creaAscolto } from '../esperienze/ascolto';
import { useSafetyGate } from '../SafetyCurtain';

const mmss = (s) => {
  const t = Math.max(0, Math.round(s || 0));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
};

/** La scala del vissuto: dieci tacche, nessun aggettivo. */
function Scala({ valore, onScegli, testid }) {
  return (
    <div className="rito-scala" role="group" data-testid={testid}>
      {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
        <button key={n} type="button"
          className={`rito-tacca${valore === n ? ' on' : ''}`}
          onClick={() => onScegli(valore === n ? null : n)}
          aria-pressed={valore === n}>{n}</button>
      ))}
    </div>
  );
}

export default function Rito({ protocollo, onEsci }) {
  /* preparazione | ascolto | congedo | salvato */
  const [fase, setFase] = useState('preparazione');
  const [clienti, setClienti] = useState([]);
  const [clienteId, setClienteId] = useState('');
  const [pre, setPre] = useState(null);
  const [post, setPost] = useState(null);
  const [note, setNote] = useState('');
  const [esito, setEsito] = useState(null);       // completata|interrotta|persa
  const [trascorso, setTrascorso] = useState(0);
  const [errore, setErrore] = useState(null);
  const [salvando, setSalvando] = useState(false);

  const ascoltoRef = useRef(null);
  const sessioneRef = useRef(null);     // {id, chiusa: bool}
  const ascoltatoRef = useRef(0);
  const { guard, curtain } = useSafetyGate();

  /* il cliente è un legame col CRM, facoltativo: la sessione anonima
     è legittima */
  useEffect(() => {
    let vivo = true;
    customersAPI.list(true, 200)
      .then((r) => { if (vivo) setClienti(r.data?.customers || r.data || []); })
      .catch(() => { /* senza lista si resta anonimi: non è un errore */ });
    return () => { vivo = false; };
  }, []);

  const ascolto = useCallback(() => {
    if (!ascoltoRef.current) {
      ascoltoRef.current = creaAscolto(protocollo.score, {
        onTic: (t) => { ascoltatoRef.current = t; setTrascorso(t); },
        onFine: () => { setEsito('completata'); setFase('congedo'); },
        /* schermo bloccato o contesto morto: la sessione si chiude
           SUBITO come persa — il registro non deve dipendere dal
           fatto che l'operatore torni a chiudere la pagina */
        onPerso: () => {
          setEsito('persa');
          const s = sessioneRef.current;
          if (s && !s.chiusa) {
            s.chiusa = true;
            soundProAPI.sessioni.chiudi(s.id, {
              esito: 'persa',
              ascolto_sec: Math.round(ascoltatoRef.current * 10) / 10,
            }).catch(() => { s.chiusa = false; });
          }
          setFase('congedo');
        },
      });
    }
    return ascoltoRef.current;
  }, [protocollo.score]);

  /* smontando non resta niente acceso; una sessione aperta e
     abbandonata si prova a chiuderla come interrotta — se la rete
     non fa in tempo, la raccoglie il ripescaggio in home */
  useEffect(() => () => {
    ascoltoRef.current?.smonta();
    const s = sessioneRef.current;
    if (s && !s.chiusa) {
      s.chiusa = true;
      soundProAPI.sessioni.chiudi(s.id, {
        esito: 'interrotta',
        ascolto_sec: Math.round(ascoltatoRef.current * 10) / 10,
      }).catch(() => { /* ripescaggio in home */ });
    }
  }, []);

  const avvia = async () => {
    setErrore(null);
    const a = ascolto();
    /* PRIMA il suono (dentro il gesto), POI il registro */
    await a.avvia();
    setFase('ascolto');
    try {
      const { data } = await soundProAPI.sessioni.apri({
        protocollo_tipo: protocollo.tipo,
        protocollo_id: protocollo.id,
        ...(clienteId ? { customer_id: clienteId } : {}),
        ...(pre != null ? { feedback_pre: pre } : {}),
      });
      sessioneRef.current = { id: data.id, chiusa: false };
    } catch (e) {
      a.ferma();
      setFase('preparazione');
      setErrore(e?.response?.data?.detail
        || 'La sessione non è stata registrata: ascolto fermato.');
    }
  };
  const avviaGuardato = guard(avvia);

  const termina = () => {
    ascoltoRef.current?.ferma();
    setEsito('interrotta');
    setFase('congedo');
  };

  const salva = async () => {
    setSalvando(true);
    setErrore(null);
    const s = sessioneRef.current;
    const vissuto = {
      ...(post != null ? { feedback_post: post } : {}),
      ...(note.trim() ? { note_operative: note.trim() } : {}),
    };
    try {
      if (s && !s.chiusa) {
        s.chiusa = true;
        await soundProAPI.sessioni.chiudi(s.id, {
          esito,
          ascolto_sec: Math.round(ascoltatoRef.current * 10) / 10,
          ...vissuto,
        });
      } else if (s && Object.keys(vissuto).length) {
        /* la persa è già chiusa: il vissuto arriva con l'aggiornamento */
        await soundProAPI.sessioni.aggiorna(s.id, vissuto);
      }
      setFase('salvato');
    } catch (e) {
      if (s) s.chiusa = false;
      setErrore(e?.response?.data?.detail || 'Non salvato: riprova.');
    } finally {
      setSalvando(false);
    }
  };

  const quota = Math.min(1, trascorso / (protocollo.durata_sec || 1));
  const avvisoCuffie = ascoltoRef.current?.avviso || null;

  /* ── ASCOLTO: schermo pulito, solo il tempo che resta ── */
  if (fase === 'ascolto') {
    return (
      <div className="rito rito-ascolto" data-testid="rito-ascolto">
        <p className="rito-titolo-quieto">{protocollo.titolo}</p>
        <div className="rito-barra" role="progressbar"
          aria-valuemin={0} aria-valuemax={protocollo.durata_sec}
          aria-valuenow={Math.round(trascorso)}>
          <i style={{ transform: `scaleX(${quota})` }} />
        </div>
        <p className="rito-resta" data-testid="rito-resta">
          {mmss(protocollo.durata_sec - trascorso)}
        </p>
        {avvisoCuffie && (
          <p className="rito-cuffie" data-testid="rito-cuffie">🎧 {avvisoCuffie}</p>
        )}
        <button type="button" className="ghost" onClick={termina}
          data-testid="rito-termina">Termina</button>
      </div>
    );
  }

  /* ── CONGEDO: l'esito onesto e il vissuto ── */
  if (fase === 'congedo' || fase === 'salvato') {
    return (
      <div className="rito" data-testid="rito-congedo">
        <h2>{protocollo.titolo}</h2>
        <p className="rito-esito" data-testid="rito-esito">
          {esito === 'completata' && `Arrivata in fondo · ${mmss(ascoltatoRef.current)} di ascolto.`}
          {esito === 'interrotta' && `Interrotta a ${mmss(ascoltatoRef.current)}.`}
          {esito === 'persa' && 'L’audio si è interrotto da solo (schermo bloccato o contesto perso): è registrato così.'}
        </p>
        {fase === 'salvato' ? (
          <>
            <p className="rito-fatto" data-testid="rito-fatto">Nel registro.</p>
            <button type="button" className="primary" onClick={onEsci}>
              Torna ai protocolli
            </button>
          </>
        ) : (
          <>
            <label className="pro-campo">
              <span className="pro-lab">Come si sente ora, da 1 a 10</span>
              <Scala valore={post} onScegli={setPost} testid="rito-post" />
            </label>
            <label className="pro-campo">
              <span className="pro-lab">Note della sessione</span>
              <textarea rows={3} value={note} maxLength={4000}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Come l’hai condotta, cosa hai osservato."
                data-testid="rito-note" />
              <span className="pro-aiuto">Private: restano tue.</span>
            </label>
            {errore && <p className="pro-errore">{errore}</p>}
            <button type="button" className="primary" onClick={salva}
              disabled={salvando} data-testid="rito-salva">
              {salvando ? 'Salvo…' : 'Salva nel registro'}
            </button>
          </>
        )}
      </div>
    );
  }

  /* ── PREPARAZIONE ── */
  return (
    <div className="rito" data-testid="rito-preparazione">
      <div className="pro-testata">
        <div>
          <h2>{protocollo.titolo}</h2>
          <p className="pro-sotto">
            {Math.round(protocollo.durata_sec / 60)} minuti
            {protocollo.cuffie_testo ? ` · ${protocollo.cuffie_testo}` : ''}
          </p>
        </div>
        <button type="button" className="ghost" onClick={onEsci}
          data-testid="rito-annulla">×</button>
      </div>

      <label className="pro-campo">
        <span className="pro-lab">Con chi <i>facoltativo</i></span>
        <select value={clienteId} onChange={(e) => setClienteId(e.target.value)}
          data-testid="rito-cliente">
          <option value="">Nessun legame — ascolto anonimo</option>
          {clienti.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </label>

      <label className="pro-campo">
        <span className="pro-lab">Come si sente, da 1 a 10 <i>facoltativo</i></span>
        <Scala valore={pre} onScegli={setPre} testid="rito-pre" />
      </label>

      {errore && <p className="pro-errore" data-testid="rito-errore">{errore}</p>}

      <button type="button" className="primary" onClick={avviaGuardato}
        data-testid="rito-avvia">Avvia l’ascolto</button>
      {curtain}
    </div>
  );
}
