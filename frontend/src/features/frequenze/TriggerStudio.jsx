/**
 * TriggerStudio — il funnel professionale nel mondo scuro (NV5, 27/8).
 *
 * L'analisi BUSSOLA: la via professionale era un sussurro in fondo a
 * una pagina ritirata — un operatore senza chiavi poteva girare tutto
 * il mondo Sound senza mai incontrare Crea Studio. Questo e' il
 * cartello: UNA riga discreta ma presente nelle stanze (biblioteca,
 * guida, meditazioni), che sparisce per chi le chiavi le ha gia'.
 *
 * Un componente solo, un nome solo (Crea Studio), una destinazione
 * sola (/sound/studio, la landing col form).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function TriggerStudio() {
  const { user } = useAuth();
  if (user?.sound_crea) return null;    // chi ha le chiavi non vede vetrine
  return (
    <div className="trigger-studio" data-testid="trigger-studio">
      <span>
        Sei un professionista del benessere? Componi le tue meditazioni
        e condividile coi tuoi clienti.
      </span>
      <Link to="/sound/studio">Scopri Crea Studio →</Link>
    </div>
  );
}
