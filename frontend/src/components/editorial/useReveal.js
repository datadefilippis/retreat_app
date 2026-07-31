/**
 * useReveal — dissolvenza breve all'ingresso in viewport (HP1).
 *
 * Regole (docs/BRAND_HOME_AURYA_2026-07.md §6: "dissolvenze brevi
 * all'ingresso, nient'altro"):
 *   1. si anima SOLO l'opacita' → zero layout shift, zero overflow;
 *   2. il default e' visibile: si nasconde solo dopo aver verificato
 *      che IntersectionObserver esista. Se il JS non gira, il testo
 *      c'e' lo stesso;
 *   3. prefers-reduced-motion: reduce → non si nasconde mai nulla,
 *      nemmeno per un frame (la guardia sta anche in CSS).
 *
 * Restituisce { ref, className } da spalmare sull'elemento.
 */
import { useEffect, useRef, useState } from 'react';

const REDUCED = '(prefers-reduced-motion: reduce)';

export default function useReveal() {
  const ref = useRef(null);
  // parte "non ancora deciso": nessuna classe → elemento visibile
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduced = typeof window.matchMedia === 'function'
      && window.matchMedia(REDUCED).matches;
    if (reduced || typeof IntersectionObserver !== 'function') return undefined;

    // gia' in viewport al primo paint (l'hero): niente lampeggio
    const box = el.getBoundingClientRect();
    if (box.top < window.innerHeight * 0.9) return undefined;

    setHidden(true);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setHidden(false);
          io.disconnect();
        }
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.01 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return { ref, className: `editorial-reveal${hidden ? ' is-hidden' : ''}` };
}
