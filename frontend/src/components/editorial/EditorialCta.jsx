/**
 * EditorialCta — l'unica azione di una sezione, sempre uguale a se'
 * stessa. Tre pesi, non venti classi copiate:
 *   solid  → la sola azione forte della pagina (hero)
 *   quiet  → invito di sezione, testo con filo sotto
 *   light  → quiet sul fondo salvia
 * Il focus e' sempre visibile (anello a contrasto sul fondo giusto).
 *
 * HP4 — `tone`. Gli stessi tre pesi esistono in due mondi: sui fondi
 * chiari del sito (tone="paper", il default) e sopra una fotografia o
 * un video scuro (tone="dark", l'hero della home di rete). Non e' una
 * quarta variante, perche' il PESO non cambia: cambia il fondo sotto.
 * Sul video il verde pieno del `solid` sparirebbe (verde di brand
 * contro verde scurito: ~1,1:1 di stacco dal contorno, sotto il 3:1
 * che serve a un componente di interfaccia), quindi li' il bottone
 * pieno diventa crema con testo verde scuro e il `quiet` prende il
 * trattamento chiaro. Cosi' la pagina continua a dichiarare
 * `variant="solid"` e `variant="quiet"`: la gerarchia delle azioni
 * resta leggibile nel codice, il vestito lo decide il tono.
 *
 * OL1 — `href`. Alcune azioni non cambiano pagina: portano a un blocco
 * della pagina che si sta gia' leggendo (la landing operatori ha tre
 * CTA che scorrono al form). Un <Link to="#ancora"> del router
 * funzionerebbe solo la PRIMA volta: al secondo clic la location non
 * cambia, l'effetto di ScrollToTop non riparte e il bottone diventa
 * muto. Con `href` il componente rende un <a> vero e lascia lo
 * scorrimento al chiamante, che sa se il visitatore ha chiesto meno
 * movimento. Il vestito e' identico: chi guarda non deve accorgersi
 * della differenza fra un'azione che cambia pagina e una che no.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 rounded-full';

const VARIANTS = {
  solid: `inline-flex items-center gap-2.5 bg-[#2f5749] text-[#f6f2e8] px-8 py-4 text-base font-medium
          hover:bg-[#25453a] transition-colors focus-visible:ring-[#2f5749] focus-visible:ring-offset-background`,
  quiet: `inline-flex items-center gap-2 text-[#2f5749] text-base font-medium underline underline-offset-[6px]
          decoration-[#2f5749]/35 hover:decoration-[#2f5749] transition-colors px-1 py-1
          focus-visible:ring-[#2f5749] focus-visible:ring-offset-background`,
  light: `inline-flex items-center gap-2 text-[#f6f2e8] text-base font-medium underline underline-offset-[6px]
          decoration-[#f6f2e8]/40 hover:decoration-[#f6f2e8] transition-colors px-1 py-1
          focus-visible:ring-[#f6f2e8] focus-visible:ring-offset-[#2f5749]`,
};

/* Sopra media scuri: l'anello di focus e' CHIARO e l'offset e' scuro
   come il velo dell'hero, cosi' il fuoco si vede anche dove sotto
   passa il fotogramma piu' luminoso del tramonto. */
const VARIANTS_DARK = {
  solid: `inline-flex items-center gap-2.5 bg-[#f6f2e8] text-[#1c2e27] px-8 py-4 text-base font-semibold
          shadow-[0_12px_34px_-14px_rgba(0,0,0,0.7)] hover:bg-white transition-colors
          focus-visible:ring-[#f6f2e8] focus-visible:ring-offset-[#12211b]`,
  quiet: `inline-flex items-center gap-2 text-[#f6f2e8] text-base font-medium underline underline-offset-[6px]
          decoration-[#f6f2e8]/55 hover:decoration-[#f6f2e8] transition-colors px-1 py-1 text-hero-shadow
          focus-visible:ring-[#f6f2e8] focus-visible:ring-offset-[#12211b]`,
  light: `inline-flex items-center gap-2 text-[#f6f2e8] text-base font-medium underline underline-offset-[6px]
          decoration-[#f6f2e8]/55 hover:decoration-[#f6f2e8] transition-colors px-1 py-1 text-hero-shadow
          focus-visible:ring-[#f6f2e8] focus-visible:ring-offset-[#12211b]`,
};

export default function EditorialCta({
  to,
  href,
  variant = 'quiet',
  tone = 'paper',
  className = '',
  children,
  ...rest
}) {
  const set = tone === 'dark' ? VARIANTS_DARK : VARIANTS;
  const cls = `${set[variant] || set.quiet} ${FOCUS} ${className}`;
  const inner = (
    <>
      <span>{children}</span>
      <ArrowRight className="h-4 w-4 shrink-0" aria-hidden />
    </>
  );
  if (href) {
    return <a href={href} className={cls} {...rest}>{inner}</a>;
  }
  return <Link to={to} className={cls} {...rest}>{inner}</Link>;
}
