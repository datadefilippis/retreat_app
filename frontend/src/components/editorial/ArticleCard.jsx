/**
 * ArticleCard — impaginazione da rivista, non card promozionale:
 * niente bordo, niente ombra, niente bottone. Categoria e data in
 * alto piccolissime, poi il titolo forte. Il titolo E' il link.
 *
 * variant lead    → l'articolo grande (immagine larga sopra)
 *         compact → i due piccoli (immagine quadrata a sinistra)
 * Lo spazio immagine e' sempre riservato: nessun salto di layout.
 */
import React from 'react';
import { Link } from 'react-router-dom';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-4 focus-visible:ring-offset-background rounded-sm';

function Kicker({ category, date, className = '' }) {
  const parts = [category, date].filter(Boolean);
  if (!parts.length) return null;
  return (
    <p className={`text-[11px] uppercase tracking-[0.18em] text-foreground/55 ${className}`}>
      {parts.join(' · ')}
    </p>
  );
}

export default function ArticleCard({ article, variant = 'compact', date, category, eager = false }) {
  const { slug, title, featured_image_url: image, description } = article || {};
  // `category` arriva gia' tradotta dal chiamante; se manca si ripiega
  // sullo slug del payload (meglio uno slug che un buco).
  const kicker = category || article?.category;
  const to = `/blog/${slug}`;

  if (variant === 'lead') {
    return (
      <article className="group">
        <Link to={to} className={`block ${FOCUS}`}>
          <div className="aspect-[16/9] w-full overflow-hidden bg-[#e8e2d4]">
            {image && (
              <img
                src={image}
                alt=""
                loading={eager ? 'eager' : 'lazy'}
                decoding="async"
                className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.02]"
              />
            )}
          </div>
          <Kicker category={kicker} date={date} className="mt-6" />
          <h3 className="font-display text-[1.75rem] sm:text-4xl leading-[1.12] mt-3 max-w-[24ch] text-foreground group-hover:text-[#2f5749] transition-colors">
            {title}
          </h3>
        </Link>
        {description && (
          <p className="text-base text-foreground/70 mt-3 max-w-[58ch] leading-relaxed">
            {description}
          </p>
        )}
      </article>
    );
  }

  return (
    <article className="group">
      {/* sempre orizzontale: il francobollo tiene il secondo piano
          davvero secondario. Un'immagine a piena colonna qui farebbe
          concorrenza all'articolo grande e la gerarchia sparirebbe. */}
      <Link to={to} className={`flex gap-5 items-start ${FOCUS}`}>
        <div className="h-24 w-24 sm:h-28 sm:w-28 shrink-0 overflow-hidden bg-[#e8e2d4]">
          {image && (
            <img
              src={image}
              alt=""
              loading="lazy"
              decoding="async"
              className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.02]"
            />
          )}
        </div>
        <div className="min-w-0">
          <Kicker category={kicker} date={date} />
          <h3 className="font-display text-lg sm:text-xl leading-snug mt-1.5 max-w-[28ch] text-foreground group-hover:text-[#2f5749] transition-colors">
            {title}
          </h3>
        </div>
      </Link>
    </article>
  );
}
