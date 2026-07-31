/**
 * PillarCard — una delle tre colonne di "Cosa troverai su Aurya"
 * (HP2, rivestita in HP3).
 *
 * Tre schede affiancate che NON sono tre bottoni: sono tre promesse.
 * Per questo la scheda intera non e' cliccabile e il link resta uno
 * solo, in fondo, dichiarato. Una card-link avrebbe reso la terza
 * ("In arrivo") un'anomalia muta dentro una fila di superfici
 * cliccabili; cosi' invece la differenza e' leggibile: due hanno un
 * invito, una ha un'etichetta.
 *
 * HP3 — la scheda diventa un oggetto: fotografia in testa (3:2),
 * superficie bianca, angoli generosi, ombra tenue. Serve a due cose:
 * togliere bianco alla pagina e dare alle tre promesse un peso visivo
 * pari a quello del testo che le circonda.
 *
 * Regole di forma:
 *   1. altezza allineata (h-full + mt-auto sul piede): il titolo della
 *      colonna 2 non deve ballare rispetto alle altre;
 *   2. spazio del piede SEMPRE riservato, anche quando il piede e'
 *      un'etichetta e non un link → zero salti, zero righe orfane;
 *   3. l'immagine ha un rapporto dichiarato (aspect-[3/2]) e le
 *      dimensioni native in width/height: lo spazio e' prenotato
 *      prima che il file arrivi, quindi niente salto di layout;
 *   4. sollevamento e zoom SOLO dove c'e' qualcosa da aprire (la
 *      scheda "In arrivo" resta ferma: muoversi sotto il mouse
 *      promette un clic che non esiste) e SOLO in motion-safe.
 *
 * NOTA DIREZIONE CREATIVA (il segno in testa alla scheda)
 * ------------------------------------------------------
 * La specifica del founder chiedeva le emoji 📖 🌿 ✨, nate quando la
 * scheda era di solo testo e serviva un appiglio per l'occhio. Con la
 * fotografia in testa quell'appiglio c'e' gia', e l'emoji diventa un
 * secondo segno che compete col primo: due "icone" a tre centimetri
 * l'una dall'altra, di cui una disegnata dal sistema operativo (la
 * stessa emoji cambia forma, colore e peso tra iOS, Android e
 * Windows: e' l'unico elemento della pagina che non controlliamo).
 * Per questo il default HP3 e' variant="plain": foto, titolo, testo,
 * invito. Le altre due varianti restano vive e si provano cambiando
 * UNA parola in NetworkHomePage (PILLAR_VARIANT):
 *   variant="emoji"   → la specifica originale, le emoji sopra il titolo
 *   variant="numeral" → numerali serif 01 / 02 / 03 nel verde salvia,
 *                       identici ovunque, che danno alla fila un
 *                       ordine di lettura esplicito
 * Decide il founder.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-2 focus-visible:ring-offset-white rounded-sm';

const SURFACE = 'flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]';

/* il sollevamento vive qui e non in una classe globale: deve poter
   sparire per la terza scheda, che non ha dove portarti */
const LIFT = 'motion-safe:transition-[transform,box-shadow] motion-safe:duration-300 motion-safe:hover:-translate-y-1 hover:shadow-[0_2px_4px_rgba(30,47,40,0.05),0_28px_56px_-28px_rgba(30,47,40,0.38)]';

export default function PillarCard({
  icon,
  numeral,
  variant = 'plain',
  image,
  imageAlt = '',
  title,
  text,
  to,
  ctaLabel,
  badge,
  headingId,
  ...rest
}) {
  const openable = Boolean(to);
  return (
    <article className={`group ${SURFACE} ${openable ? LIFT : ''}`} {...rest}>
      {image && (
        <div className="aspect-[3/2] w-full overflow-hidden bg-[#e8e2d4]">
          <img
            src={image}
            alt={imageAlt}
            width="900"
            height="600"
            loading="lazy"
            decoding="async"
            className={`h-full w-full object-cover ${
              openable
                ? 'motion-safe:transition-transform motion-safe:duration-[900ms] motion-safe:ease-out motion-safe:group-hover:scale-[1.05]'
                /* l'anticipazione: la foto c'e' ma non e' ancora
                   accesa. La desaturazione dice "non ancora" prima che
                   l'occhio arrivi all'etichetta in fondo. */
                : 'grayscale-[0.72] opacity-90'
            }`}
          />
        </div>
      )}

      <div className="flex flex-1 flex-col p-6 sm:p-7">
        {/* il segno: riga ad altezza fissa in entrambe le varianti,
            cosi' passare da emoji a numerali non muove di un pixel il
            titolo. Con la foto in testa (variant plain) non si stampa
            proprio: due segni sopra lo stesso titolo sono uno di
            troppo. */}
        {variant !== 'plain' && (
          <p className="flex h-9 items-center" aria-hidden>
            {variant === 'numeral' ? (
              <span className="font-display text-2xl leading-none text-[#2f5749]/70 tracking-[0.02em]">
                {numeral}
              </span>
            ) : (
              <span className="text-[1.75rem] leading-none">{icon}</span>
            )}
          </p>
        )}

        <h3
          id={headingId}
          className={`font-display text-[1.4rem] sm:text-2xl leading-tight text-foreground ${variant === 'plain' ? '' : 'mt-5'}`}
        >
          {title}
        </h3>

        <p className="mt-3 max-w-[46ch] text-pretty text-[0.975rem] sm:text-base leading-relaxed text-foreground/75">
          {text}
        </p>

        {/* piede: sempre presente, sempre alla stessa quota */}
        <div className="mt-auto pt-6">
          {to ? (
            <Link
              to={to}
              className={`inline-flex items-center gap-2 text-[#2f5749] text-[0.975rem] font-medium underline underline-offset-[6px]
                          decoration-[#2f5749]/35 hover:decoration-[#2f5749] transition-colors ${FOCUS}`}
            >
              <span>{ctaLabel}</span>
              <ArrowRight className="h-4 w-4 shrink-0 motion-safe:transition-transform motion-safe:duration-300 motion-safe:group-hover:translate-x-1" aria-hidden />
            </Link>
          ) : (
            /* stato "in arrivo": NON e' un bottone disabilitato (un
               bottone disabilitato promette un clic che non arriva mai e
               sparisce dalla tabulazione lasciando un buco). E' un
               sostantivo: un'etichetta di stato, leggibile e ferma. */
            /* HP2 — /75 e non /60: a 12px con lo spazio tra le lettere
               largo, il grigio al 60% stava a 4.03:1 su bianco, sotto il
               minimo AA. Al 75% sale a 6.37:1 e resta comunque piu'
               leggero del titolo. */
            <span
              className="inline-flex items-center rounded-full border border-foreground/25 px-3 py-1
                         text-xs uppercase tracking-[0.16em] text-foreground/75"
            >
              {badge}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
