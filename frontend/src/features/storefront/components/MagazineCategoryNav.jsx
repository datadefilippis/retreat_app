/**
 * MagazineCategoryNav — MG1: le categorie diventano una navigazione
 * che si guarda, non una fila di pastiglie da leggere.
 *
 * IL PROBLEMA. Con dodici categorie, la barra di pastiglie testuali
 * costringeva a leggerle tutte per trovarne una, e non diceva niente
 * su cosa ci fosse dentro: "Suono & Sound Healing" e "Cerchi &
 * Femminile" hanno lo stesso peso visivo e la stessa promessa, cioe'
 * nessuna. Il founder l'ha detto in una riga: la navigazione fra
 * categorie deve essere piu' visual e semplice.
 *
 * LA SOLUZIONE, e il motivo per cui non e' arbitraria: OGNI CATEGORIA
 * HA GIA' UN COLORE. Le copertine autogenerate lo usano da SW4
 * (backend/services/article_cover.py), quindi una scheda salvia sopra
 * una griglia di copertine salvia non e' una decorazione, e' la stessa
 * classificazione detta due volte. Chi ha visto la copertina dell'
 * articolo sullo yoga riconosce il verde prima di leggere la parola.
 *
 * I COLORI QUI SONO IL CALCO di CATEGORY_PALETTES e
 * EDITORIAL_PALETTES: il primo dei due toni di ogni coppia, quello di
 * fondo. Se una palette cambia di la', va cambiata anche qui — e' un
 * duplicato consapevole, perche' l'alternativa (esporre le palette in
 * un endpoint) costerebbe una chiamata per una manciata di byte che
 * non cambiano mai.
 *
 * Il conteggio non e' un vezzo: dice se dietro una porta c'e' una
 * stanza o un ripostiglio, ed e' l'informazione che manca di piu'
 * quando si sceglie dove entrare.
 *
 * Ogni scheda e' un <Link> a una rotta vera e indicizzabile, come
 * erano le pastiglie: la navigazione cambia vestito, non natura.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import CategorySigil from './CategorySigil';

/* Il calco delle palette del generatore di copertine. */
const COLORE = {
  yoga: '#376254',
  meditazione: '#2f4f4f',
  detox: '#3e5c3e',
  suono: '#483e5c',
  massaggio: '#7a523e',
  breathwork: '#345266',
  cammini: '#485234',
  femminile: '#703e52',
  aziendale: '#3e4852',
  ritiri: '#604e32',
  energia: '#4e3e6c',
  operatori: '#2c4a42',
  scegliere: '#3a4660',
  ayurveda: '#68422c',
};
const RIPIEGO = '#376254';

export function coloreCategoria(slug) {
  return COLORE[slug] || RIPIEGO;
}

/**
 * @param {string[]} categorie  slug, nell'ordine in cui vanno mostrate
 * @param {Record<string,number>} conteggi  slug → numero di articoli
 * @param {string} attiva  slug della categoria corrente, '' per Tutti
 * @param {number} totale  quanti articoli in tutto (per la voce Tutti)
 */
export default function MagazineCategoryNav({
  categorie, conteggi, attiva = '', totale = 0, className = '',
}) {
  const { t } = useTranslation('landings');
  const etichetta = (slug) => t(`categories.${slug}`, { defaultValue: slug });

  const scheda = (slug, nome, n, colore, corrente) => (
    <li key={slug || 'tutti'}>
      <Link
        to={slug ? `/blog/categoria/${slug}` : '/blog'}
        aria-current={corrente ? 'page' : undefined}
        data-testid="mag-cat-card"
        className={`group relative flex h-full min-h-[5.5rem] flex-col justify-between
                    gap-2 overflow-hidden rounded-xl px-4 py-3.5
                    transition-[transform,box-shadow] duration-200
                    focus-visible:outline-none focus-visible:ring-2
                    focus-visible:ring-offset-2 focus-visible:ring-offset-background
                    motion-safe:hover:-translate-y-0.5
                    ${corrente ? 'text-[#f6f2e8] shadow-md' : 'text-[#f6f2e8]/95 hover:shadow-md'}`}
        style={{
          backgroundColor: colore,
          /* la corrente si stacca con un filo chiaro invece che con un
             colore diverso: il colore e' gia' l'identita' della
             categoria e non puo' fare anche da stato */
          boxShadow: corrente ? `0 0 0 2px #f6f2e8, 0 0 0 4px ${colore}` : undefined,
          '--tw-ring-color': colore,
        }}
      >
        {/* MG2 — il segno della categoria, lo stesso che sta sulle sue
            copertine. Sborda dall'angolo (il contenitore taglia) e sta
            al 22%: e' un riconoscimento, non un'illustrazione, e deve
            restare sotto il nome senza contendergli la lettura.
            Cresce appena al passaggio del mouse, che e' l'unico
            momento in cui vale la pena guardarlo. */}
        {slug && (
          <CategorySigil
            categoria={slug}
            className="pointer-events-none absolute -right-5 -top-5 h-24 w-24 opacity-[0.22]
                       transition-transform duration-300 motion-safe:group-hover:scale-110"
          />
        )}
        <span className="relative text-[0.95rem] font-medium leading-snug">{nome}</span>
        <span className="relative text-[11px] uppercase tracking-[0.12em] opacity-75">
          {n === 1
            ? t('blog.catCountOne', { defaultValue: '1 articolo' })
            : t('blog.catCount', { count: n, defaultValue: '{{count}} articoli' })}
        </span>
      </Link>
    </li>
  );

  return (
    <nav aria-label={t('blog.catNavLabel', { defaultValue: 'Categorie del Magazine' })}
         data-testid="mag-cat-nav" className={className}>
      <ul className="grid list-none grid-cols-2 gap-2.5 p-0 sm:grid-cols-3 lg:grid-cols-4">
        {scheda('', t('blog.allArticles', { defaultValue: 'Tutti gli articoli' }),
                totale, '#212c28', !attiva)}
        {categorie.map(slug => scheda(
          slug, etichetta(slug), conteggi[slug] || 0,
          coloreCategoria(slug), attiva === slug))}
      </ul>
    </nav>
  );
}
