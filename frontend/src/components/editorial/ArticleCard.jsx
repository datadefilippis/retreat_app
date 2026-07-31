/**
 * ArticleCard — impaginazione da rivista, non card promozionale:
 * niente bordo, niente ombra, niente bottone. Il titolo E' il link.
 *
 * variant lead    → l'articolo grande (copertina 16:9 sopra)
 *         compact → i secondari (miniatura 4:3 a sinistra)
 * Lo spazio immagine e' sempre riservato: nessun salto di layout.
 *
 * HP3 — tre ritocchi, nessuno strutturale:
 *   1. la copertina ha angoli propri (rounded-2xl / xl) e uno zoom
 *      lentissimo al passaggio del mouse, solo in motion-safe;
 *   2. la categoria diventa un chip verde e la data torna a essere
 *      una data leggibile invece di un'altra maiuscoletta spaziata:
 *      erano due informazioni diverse stampate con la stessa voce, e
 *      la data ci perdeva sempre;
 *   3. la miniatura del compatto passa da francobollo quadrato di
 *      96px a 4:3 da 128px: le copertine autogenerate del Magazine
 *      sono orizzontali e nel quadrato perdevano meta' titolo.
 */
import React from 'react';
import { Link } from 'react-router-dom';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-4 focus-visible:ring-offset-white rounded-sm';

const ZOOM = 'motion-safe:transition-transform motion-safe:duration-[900ms] motion-safe:ease-out motion-safe:group-hover:scale-[1.05]';

/** categoria = chip (una classificazione), data = testo (un fatto)
 *  SW4 — `badge` e' lo slot per una nota di STATO della scheda (oggi
 *  solo "Per gli iscritti", la promessa BN3 che va vista gia' in
 *  lista). Sta nel kit e non nella pagina perche' la riga di occhiello
 *  e' una misura condivisa: montarlo fuori l'avrebbe disallineata. */
function Kicker({ category, date, badge, className = '' }) {
  if (!category && !date && !badge) return null;
  return (
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-2 ${className}`}>
      {category && (
        <span className="inline-flex items-center rounded-full bg-[#2f5749]/10 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.12em] text-[#2f5749]">
          {category}
        </span>
      )}
      {date && (
        <span className="text-[13px] text-foreground/65">{date}</span>
      )}
      {badge}
    </div>
  );
}

export default function ArticleCard({ article, variant = 'compact', date, category, badge, eager = false }) {
  const { slug, title, featured_image_url: image, description } = article || {};
  // `category` arriva gia' tradotta dal chiamante; se manca si ripiega
  // sullo slug del payload (meglio uno slug che un buco).
  const kicker = category || article?.category;
  const to = `/blog/${slug}`;

  if (variant === 'lead') {
    return (
      <article className="group">
        <Link to={to} className={`block ${FOCUS}`}>
          <div className="aspect-[16/9] w-full overflow-hidden rounded-2xl bg-[#e8e2d4]">
            {image && (
              <img
                src={image}
                alt=""
                width="1200"
                height="675"
                loading={eager ? 'eager' : 'lazy'}
                decoding="async"
                className={`h-full w-full object-cover ${ZOOM}`}
              />
            )}
          </div>
          <Kicker category={kicker} date={date} badge={badge} className="mt-6" />
          <h3 className="font-display text-[1.7rem] sm:text-[2.1rem] leading-[1.14] mt-3 max-w-[26ch] text-balance text-foreground group-hover:text-[#2f5749] transition-colors">
            {title}
          </h3>
        </Link>
        {description && (
          <p className="text-[0.975rem] sm:text-base text-foreground/70 mt-3 max-w-[58ch] leading-relaxed">
            {description}
          </p>
        )}
      </article>
    );
  }

  return (
    <article className="group">
      {/* sempre orizzontale: la miniatura tiene il secondo piano
          davvero secondario. Una copertina a piena colonna qui farebbe
          concorrenza all'articolo grande e la gerarchia sparirebbe. */}
      <Link to={to} className={`flex gap-4 sm:gap-5 items-start ${FOCUS}`}>
        <div className="aspect-[4/3] w-28 sm:w-32 shrink-0 overflow-hidden rounded-xl bg-[#e8e2d4]">
          {image && (
            <img
              src={image}
              alt=""
              width="1200"
              height="675"
              loading="lazy"
              decoding="async"
              className={`h-full w-full object-cover ${ZOOM}`}
            />
          )}
        </div>
        <div className="min-w-0">
          <Kicker category={kicker} date={date} badge={badge} />
          <h3 className="font-display text-[1.0625rem] sm:text-lg leading-snug mt-2 max-w-[28ch] text-pretty text-foreground group-hover:text-[#2f5749] transition-colors">
            {title}
          </h3>
        </div>
      </Link>
    </article>
  );
}
