import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Anteprima LIVE del form newsletter (F7).
 *
 * Riusa lo STESSO web component dell'embed (`<afianco-newsletter-form>`) in
 * modalità preview: carica una volta il bundle SDK (servito dal frontend in
 * /embed/v1/) e inietta la config corrente via property `config` + `preview`.
 * Nessuna duplicazione del rendering, nessun fetch/submit reale: l'anteprima
 * riflette in tempo reale campi, colori e link privacy non ancora salvati.
 */

let _bundlePromise = null;

function ensureBundle() {
  if (typeof window === 'undefined') return Promise.resolve();
  if (window.customElements && window.customElements.get('afianco-newsletter-form')) {
    return Promise.resolve();
  }
  if (_bundlePromise) return _bundlePromise;
  _bundlePromise = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.type = 'module';
    // Il bundle è servito dal frontend (public/embed/v1) → stessa origine.
    s.src = `${window.location.origin}/embed/v1/afianco-embed.es.js`;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('bundle load failed'));
    document.head.appendChild(s);
  });
  return _bundlePromise;
}

export default function NewsletterFormPreview({ config }) {
  const { t } = useTranslation('newsletter');
  const ref = useRef(null);
  const [ready, setReady] = useState(
    !!(typeof window !== 'undefined' && window.customElements?.get('afianco-newsletter-form')),
  );
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    ensureBundle().then(() => { if (alive) setReady(true); }).catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, []);

  // Inietta la config (oggetto) via property ogni volta che cambia.
  useEffect(() => {
    if (ready && ref.current) {
      ref.current.preview = true;
      ref.current.config = config;
    }
  }, [ready, config]);

  return (
    <div className="rounded-xl border bg-white p-4 min-h-[160px]">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">{t('preview.title')}</div>
      {failed ? (
        <div className="text-xs text-muted-foreground">{t('preview.unavailable')}</div>
      ) : ready ? (
        React.createElement('afianco-newsletter-form', { ref, preview: 'true' })
      ) : (
        <div className="text-xs text-muted-foreground">{t('preview.loading')}</div>
      )}
    </div>
  );
}
