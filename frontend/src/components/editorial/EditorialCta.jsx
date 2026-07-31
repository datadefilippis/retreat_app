/**
 * EditorialCta — l'unica azione di una sezione, sempre uguale a se'
 * stessa. Tre pesi, non venti classi copiate:
 *   solid  → la sola azione forte della pagina (hero)
 *   quiet  → invito di sezione, testo con filo sotto
 *   light  → quiet sul fondo salvia
 * Il focus e' sempre visibile (anello a contrasto sul fondo giusto).
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

export default function EditorialCta({
  to,
  variant = 'quiet',
  className = '',
  children,
  ...rest
}) {
  return (
    <Link
      to={to}
      className={`${VARIANTS[variant] || VARIANTS.quiet} ${FOCUS} ${className}`}
      {...rest}
    >
      <span>{children}</span>
      <ArrowRight className="h-4 w-4 shrink-0" aria-hidden />
    </Link>
  );
}
