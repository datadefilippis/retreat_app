/**
 * SCEGLI PERSONA — cerca, o crea al volo (M-CRM, 26/8/2026).
 *
 * La domanda del founder: «i clienti da dove derivano? e se un
 * cliente non c'è?». La risposta: dal CRM del gestionale — la STESSA
 * collezione `customers`, un elenco solo — e se non c'è si crea QUI,
 * col nome e basta: due secondi prima di una sessione, non un modulo.
 * Non serve «sincronizzare col gestionale»: il cliente creato da
 * Sound Professional È nel gestionale, perché la fonte è una.
 *
 * Un campo unico: scrivi e filtra; se nessuno corrisponde, la prima
 * voce diventa «Crea "Nome"». La scelta è sempre reversibile (×).
 * Usato dal rito, dalla scheda percorso e dal registro (lì senza
 * creazione: un filtro non inventa persone).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { customersAPI } from '../../../api/customers';
import { messaggio } from './errori';
import './pro.css';   // il componente porta il suo vestito (usato anche fuori da /sound/pro)

export default function ScegliPersona({
  valore,            // {id, nome} | null
  onScegli,          // ({id, nome} | null) =>
  permettiCrea = true,
  placeholder = 'Cerca per nome…',
  testid = 'scegli-persona',
}) {
  const [clienti, setClienti] = useState([]);
  const [testo, setTesto] = useState('');
  const [aperto, setAperto] = useState(false);
  const [creando, setCreando] = useState(false);
  const [errore, setErrore] = useState(null);
  const riquadro = useRef(null);

  useEffect(() => {
    let vivo = true;
    customersAPI.list(true, 500)
      .then((r) => { if (vivo) setClienti(r.data || []); })
      .catch(() => { /* senza elenco resta la creazione */ });
    return () => { vivo = false; };
  }, []);

  /* chiudersi quando si clicca fuori: un menu che resta aperto è rumore */
  useEffect(() => {
    const giu = (e) => {
      if (riquadro.current && !riquadro.current.contains(e.target)) setAperto(false);
    };
    document.addEventListener('mousedown', giu);
    return () => document.removeEventListener('mousedown', giu);
  }, []);

  const filtro = testo.trim().toLowerCase();
  const trovati = useMemo(
    () => (filtro
      ? clienti.filter((c) => (c.name || '').toLowerCase().includes(filtro))
      : clienti).slice(0, 8),
    [clienti, filtro]);
  const esatto = clienti.some(
    (c) => (c.name || '').toLowerCase() === filtro);

  const scegli = (c) => {
    onScegli({ id: c.id, nome: c.name });
    setTesto('');
    setAperto(false);
  };

  const crea = async () => {
    const nome = testo.trim();
    if (!nome || creando) return;
    setCreando(true);
    setErrore(null);
    try {
      const { data } = await customersAPI.create({ name: nome });
      setClienti((prec) => [...prec, data]);
      scegli(data);
    } catch (e) {
      setErrore(messaggio(e, 'Non creato: riprova.'));
    } finally {
      setCreando(false);
    }
  };

  if (valore) {
    return (
      <div className="persona-scelta" data-testid={`${testid}-scelta`}>
        <span>{valore.nome}</span>
        <button type="button" className="ghost" title="Togli il legame"
          onClick={() => onScegli(null)}
          data-testid={`${testid}-togli`}>×</button>
      </div>
    );
  }

  return (
    <div className="persona" ref={riquadro}>
      <input type="text" value={testo} placeholder={placeholder}
        onChange={(e) => { setTesto(e.target.value); setAperto(true); }}
        onFocus={() => setAperto(true)}
        data-testid={testid} />
      {aperto && (trovati.length > 0 || (permettiCrea && filtro)) && (
        <ul className="persona-tendina" data-testid={`${testid}-tendina`}>
          {trovati.map((c) => (
            <li key={c.id}>
              <button type="button" onClick={() => scegli(c)}>{c.name}</button>
            </li>
          ))}
          {permettiCrea && filtro && !esatto && (
            <li className="persona-crea">
              <button type="button" onClick={crea} disabled={creando}
                data-testid={`${testid}-crea`}>
                {creando ? 'Creo…' : `+ Crea «${testo.trim()}»`}
              </button>
            </li>
          )}
        </ul>
      )}
      {errore && <p className="pro-errore">{errore}</p>}
    </div>
  );
}
