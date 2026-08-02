/**
 * MovementIndex — l'indice dei movimenti di una pagina lunga (DS1).
 *
 * IL PERCHE'. Su Manifesto e Chi siamo il problema non e' che il testo
 * sia lungo: e' che il lettore non sa MAI quanto e' lungo. Senza un
 * indice, una pagina di posizione e' un tunnel: si scorre al buio, e
 * chi non sa quanto manca smette prima. L'indice fa due cose insieme,
 * e la seconda vale piu' della prima: dice dove si puo' andare, e dice
 * dove si e'.
 *
 * DUE FORME, UNA SOLA VERITA'.
 *   variant="rail" → la colonna appiccicata a lato, da xl in su. Non e'
 *     un menu che accompagna: e' un segnalibro. Vive DENTRO la regione
 *     dei movimenti (uno strato in `absolute inset-0` sul contenitore
 *     `relative` che li avvolge, con dentro un elemento `sticky`):
 *     compare quando i movimenti cominciano e sparisce quando
 *     finiscono, senza galleggiare sopra l'apertura e sopra la firma,
 *     dove non avrebbe niente da indicare. Lo strato non intercetta il
 *     mouse (`pointer-events-none`), solo la colonna lo fa: non ruba un
 *     clic al testo che le sta accanto.
 *   variant="row" → la riga di ancore scorrevole, sotto l'apertura, da
 *     xl in giu'. Sul telefono una colonna a lato non esiste: lo spazio
 *     laterale non c'e'. La riga fa lo stesso lavoro in orizzontale, e
 *     sta sotto l'apertura perche' e' li' che serve — subito dopo aver
 *     capito di che pagina si tratta.
 *
 * PERCHE' DA xl E NON DA lg. La colonna vuole 11rem di larghezza piu'
 * 2,5rem d'aria: sotto i 1280px non c'e' margine laterale sufficiente
 * accanto a una colonna di testo da 48rem, e la colonna finirebbe sopra
 * le parole. Meglio la riga che una colonna che si sovrappone.
 *
 * ANCORE VERE. Ogni voce e' un <a href="#id"> che funziona anche senza
 * JavaScript: se il gestore non gira, il browser fa il salto nativo. Il
 * gestore, quando gira, aggiunge tre cose e nient'altro:
 *   1. lo scorrimento morbido, ma solo a chi non ha chiesto meno
 *      movimento (prefers-reduced-motion: il salto secco resta secco);
 *   2. il FUOCO sulla sezione di arrivo, che il salto nativo darebbe da
 *      solo e uno scorrimento via JS invece perderebbe: senza, chi
 *      naviga da tastiera scorre la pagina ma continua a tabulare da
 *      dove era;
 *   3. l'hash nell'URL via replaceState, cosi' l'indirizzo resta
 *      condivisibile senza impilare una voce di cronologia per ogni
 *      clic.
 *
 * DOVE SI E'. E' attiva l'ultima sezione il cui bordo alto ha superato
 * la linea del 45% dello schermo (il perche' della regola e del modo di
 * calcolarla sta su useMovementSpy, qui sotto). `aria-current` porta la
 * stessa informazione a chi non vede l'evidenziazione.
 *
 * Contrasti (misurati): voce attiva #212C28 sul crema di fondo
 * #FAF8F5 → 13,61:1; voce a riposo la stessa al 70% → 5,30:1. Nella
 * riga, pastiglia attiva crema su salvia #2f5749 → 7,28:1, pastiglia a
 * riposo (75%) → 6,20:1. Minimo AA per il corpo: 4,5:1.
 */
import React, { useEffect, useState } from 'react';

const FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-2 focus-visible:ring-offset-background';

/**
 * useMovementSpy — quale sezione sta attraversando il centro.
 *
 * LA REGOLA: e' attiva l'ultima sezione il cui bordo alto ha gia'
 * superato la linea del 45% dello schermo. Non "quella dentro una
 * striscia", perche' fra un movimento e l'altro puo' esserci qualcosa
 * che movimento non e' (una fascia fotografica): in quel tratto nessuna
 * sezione sarebbe dentro la striscia e l'indice si spegnerebbe nel
 * mezzo. Con la regola del sorpasso, invece, resta accesa la voce che
 * si e' appena letta, che e' anche la risposta giusta.
 *
 * PERCHE' UN ASCOLTO DELLO SCORRIMENTO E NON UN IntersectionObserver.
 * L'osservatore sembra la scelta ovvia e in DS1 e' stato provato per
 * primo: non regge in due situazioni che capitano davvero, la pagina
 * dentro un frame (anteprime, strumenti di cattura) e la scheda non
 * visibile, dove il browser smette di consegnare le intersezioni e
 * l'indice resta acceso sulla voce sbagliata finche' non si ricarica.
 * L'ascolto e' passivo e coalizzato in un rAF: si legge la posizione di
 * quattro elementi al massimo una volta per fotogramma, e solo mentre
 * si scorre. Costa meno di quanto si teme e non ha modi di sbagliare.
 */
function useMovementSpy(ids) {
  const key = ids.join('|');
  const [active, setActive] = useState(ids[0]);

  useEffect(() => {
    const list = key.split('|');
    if (!list.some((id) => document.getElementById(id))) return undefined;

    const LINE = 0.45;
    let queued = false;
    const compute = () => {
      queued = false;
      const line = window.innerHeight * LINE;
      let pick = list[0];
      list.forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= line) pick = id;
      });
      setActive(pick);
    };
    const onScroll = () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(compute);
    };

    compute();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, [key]);

  return active;
}

function goTo(e, id) {
  const el = typeof document !== 'undefined' && document.getElementById(id);
  if (!el) return; // niente bersaglio: lascia fare al link nativo
  e.preventDefault();
  const reduced = typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
  el.focus({ preventScroll: true });
  if (window.history?.replaceState) {
    window.history.replaceState(null, '', `#${id}`);
  }
}

export default function MovementIndex({
  items = [],
  label,
  variant = 'row',
  className = '',
}) {
  const active = useMovementSpy(items.map((i) => i.id));
  if (!items.length) return null;

  /* ── la colonna appiccicata (desktop largo) ─────────────────────── */
  if (variant === 'rail') {
    return (
      <div aria-hidden={false}
           className={`pointer-events-none absolute inset-0 hidden xl:block ${className}`}>
        <nav
          aria-label={label}
          /* 37,5rem = meta' della colonna di testo (24rem) + l'aria
             (2,5rem) + la larghezza della colonna stessa (11rem) */
          className="pointer-events-auto sticky top-28 w-44
                     ml-[max(1rem,calc(50%_-_37.5rem))]
                     rounded-[1.25rem] bg-background/95 p-2.5
                     ring-1 ring-[#1e2f28]/[0.08]
                     shadow-[0_18px_40px_-30px_rgba(30,47,40,0.45)]"
        >
          <ol className="list-none p-0">
            {items.map((it) => {
              const on = active === it.id;
              return (
                <li key={it.id}>
                  <a
                    href={`#${it.id}`}
                    onClick={(e) => goTo(e, it.id)}
                    aria-current={on ? 'true' : undefined}
                    className={`flex items-start gap-2.5 rounded-xl px-2.5 py-2
                                text-[0.8rem] leading-snug text-pretty ${FOCUS}
                                ${on ? 'text-foreground' : 'text-foreground/70 hover:text-foreground'}`}
                  >
                    <span
                      aria-hidden
                      className={`mt-[0.45rem] h-px shrink-0 bg-current
                                  motion-safe:transition-all motion-safe:duration-300
                                  ${on ? 'w-6 opacity-100' : 'w-3 opacity-60'}`}
                    />
                    <span>{it.label}</span>
                  </a>
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    );
  }

  /* ── la riga di ancore (telefono e desktop stretto) ──────────────── */
  return (
    <nav
      aria-label={label}
      /* i margini negativi riportano la riga ai bordi dello schermo: le
         pastiglie devono poter uscire dalla gutter mentre scorrono,
         altrimenti l'ultima sembra l'ultima e non lo e' */
      className={`xl:hidden -mx-6 sm:-mx-8 ${className}`}
    >
      <ol className="flex list-none gap-2 overflow-x-auto px-6 pb-1 sm:px-8
                     [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {items.map((it) => {
          const on = active === it.id;
          return (
            <li key={it.id} className="shrink-0">
              <a
                href={`#${it.id}`}
                onClick={(e) => goTo(e, it.id)}
                aria-current={on ? 'true' : undefined}
                className={`inline-flex items-center rounded-full border px-4 py-2
                            text-[0.8rem] leading-none ${FOCUS}
                            motion-safe:transition-colors
                            ${on
                              ? 'border-[#2f5749] bg-[#2f5749] text-[#f6f2e8]'
                              : 'border-foreground/20 text-foreground/75 hover:border-foreground/40'}`}
              >
                {it.label}
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
