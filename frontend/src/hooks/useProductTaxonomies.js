/**
 * useProductTaxonomies — le categorie per tipo prodotto, dal backend
 * (V4: fonte unica models/retreat_taxonomy, la stessa che valida).
 * Ritorna {} finche' carica; i wizard rendono il dropdown quando c'e'.
 */
import { useEffect, useState } from 'react';
import api from '../api/client';

export default function useProductTaxonomies() {
  const [taxonomies, setTaxonomies] = useState({});
  useEffect(() => {
    let mounted = true;
    api.get('/products/taxonomies')
      .then(res => { if (mounted) setTaxonomies(res.data || {}); })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);
  return taxonomies;
}
