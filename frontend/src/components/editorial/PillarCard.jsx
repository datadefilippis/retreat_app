/**
 * PillarCard — una delle tre colonne di "Cosa troverai su Aurya" (HP2).
 *
 * Tre schede affiancate che NON sono tre bottoni: sono tre promesse.
 * Per questo la scheda intera non e' cliccabile e il link resta uno
 * solo, in fondo, dichiarato. Una card-link avrebbe reso la terza
 * ("In arrivo") un'anomalia muta dentro una fila di superfici
 * cliccabili; cosi' invece la differenza e' leggibile: due hanno un
 * invito, una ha un'etichetta.
 *
 * Regole di forma:
 *   1. altezza allineata (h-full + mt-auto sul piede): il titolo della
 *      colonna 2 non deve ballare rispetto alle altre;
 *   2. spazio del piede SEMPRE riservato, anche quando il piede e'
 *      un'etichetta e non un link → zero salti, zero righe orfane;
 *   3. il segno in testa e' decorativo: aria-hidden, perche' il senso
 *      sta nel titolo. Uno screen reader non deve sentire "libro".
 *
 * NOTA DIREZIONE CREATIVA (emoji vs. segno editoriale)
 * ----------------------------------------------------
 * La specifica del founder chiede le emoji 📖 🌿 ✨ ed e' quello che
 * il sito mostra oggi (variant="emoji", il default). Il dubbio: le
 * emoji sono renderizzate dal SISTEMA operativo, quindi lo stesso
 * simbolo cambia disegno, colore e peso tra iOS, Android e Windows.
 * Su una pagina che si regge su una serif e tre colori questo e'
 * l'unico elemento che non controlliamo, ed e' anche l'unico che
 * "parla" come una chat.
 * Alternativa proposta, gia' implementata qui: variant="numeral",
 * numerali serif 01 / 02 / 03 nel verde salvia, che riprendono la
 * tipografia del brand, restano identici ovunque, pesano zero e
 * danno alla fila un ordine di lettura esplicito.
 * Si prova cambiando UNA parola in NetworkHomePage (PILLAR_VARIANT).
 * Decide il founder.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-2 focus-visible:ring-offset-white rounded-sm';

export default function PillarCard({
  icon,
  numeral,
  variant = 'emoji',
  title,
  text,
  to,
  ctaLabel,
  badge,
  headingId,
  ...rest
}) {
  return (
    <article className="flex h-full flex-col" {...rest}>
      {/* il segno: riga a altezza fissa in entrambe le varianti, cosi'
          passare da emoji a numerali non muove di un pixel il titolo */}
      <p className="flex h-9 items-center" aria-hidden>
        {variant === 'numeral' ? (
          <span className="font-display text-2xl leading-none text-[#2f5749]/70 tracking-[0.02em]">
            {numeral}
          </span>
        ) : (
          <span className="text-[1.75rem] leading-none">{icon}</span>
        )}
      </p>

      <h3
        id={headingId}
        className="font-display text-2xl sm:text-[1.75rem] leading-tight mt-5 text-foreground"
      >
        {title}
      </h3>

      <p className="mt-4 max-w-[46ch] text-base leading-relaxed text-foreground/75">
        {text}
      </p>

      {/* piede: sempre presente, sempre alla stessa quota */}
      <div className="mt-auto pt-7">
        {to ? (
          <Link
            to={to}
            className={`inline-flex items-center gap-2 text-[#2f5749] text-base font-medium underline underline-offset-[6px]
                        decoration-[#2f5749]/35 hover:decoration-[#2f5749] transition-colors ${FOCUS}`}
          >
            <span>{ctaLabel}</span>
            <ArrowRight className="h-4 w-4 shrink-0" aria-hidden />
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
    </article>
  );
}
