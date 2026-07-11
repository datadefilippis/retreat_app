# Audit SEO olistico — Aurya (11 luglio 2026, snapshot pre-lancio)

> Valutazione da Senior SEO Specialist dell'intera piattaforma, con
> verifiche LIVE su aurya.life. Complementare a SEO_PLAYBOOK.md
> (operativo) e SEO_STRATEGY_2026-07.md (mercato).

## Scorecard

| Area | Voto | Sintesi |
|---|---|---|
| Infrastruttura tecnica | 9/10 | Shell server-side, sitemap index, hreflang, IndexNow, canonical: sopra lo standard di settore |
| Structured data | 8/10 | BlogPosting+articleBody, FAQPage, Event, LocalBusiness, Breadcrumb. Manca Organization sulla home |
| GEO / LLM readiness | 9/10 | articleBody nel primo HTML, llms.txt, FAQ citabili: avanti rispetto al 95% dei siti italiani |
| Contenuti / E-E-A-T | 7/10 | 19 articoli con firma vera e onestà radicale; mancano pagine autore e i pezzi sono sotto la lunghezza pilastro |
| Architettura & internal linking | 7/10 | Hub-spoke impostato, link in-content; mancano articoli correlati automatici e hub /discipline |
| Igiene di crawling | 6/10 | SOFT-404: gli URL inesistenti rispondono 200. Robots ora corretto, ma questo va chiuso |
| Off-page / autorità | 2/10 | Dominio a zero backlink: normale a day-zero, ma è il collo di bottiglia dei prossimi 6 mesi |
| Misurazione | 6/10 | GA4+consenso live, first-party attivo; GSC a giorno zero, nessun evento conversione configurato |

**Voto complessivo: 7.5/10** — fondamenta da sito maturo su un dominio
neonato. Il rischio non è tecnico: è di esecuzione editoriale e link
building nei prossimi 6 mesi.

## Punti di forza (sopra lo standard)

1. SEO shell server-side identica per bot e umani (niente cloaking, niente dipendenza dal rendering JS di Google).
2. articleBody integrale + FAQPage nel primo HTML: i motori generativi ci leggono per intero; llms.txt li orienta.
3. Sitemap index a 5 livelli con lastmod + IndexNow su ogni publish.
4. Reversibilità del pre-lancio: noindex e gate spariscono col flag, senza interventi manuali (guardie di regressione a protezione).
5. Onestà radicale come strategia E-E-A-T: prezzi veri, controindicazioni, "cosa dice la ricerca": il differenziante che nessun competitor può copiare in fretta.
6. Consent Mode v2 e privacy allineata: nessun rischio di sanzioni che vanifichi il lavoro organico.

## GAP prioritizzati

### P0 — da chiudere prima del lancio
1. **Soft-404** (VERIFICATO live): `aurya.life/qualsiasi-cosa-inesistente` risponde HTTP 200 con la shell neutra. Google li marca "soft 404", spreca crawl budget e diluisce la qualità percepita del dominio. Fix: la shell deve rispondere 404 quando il resolver non trova nulla E il path non è una rotta SPA nota (whitelist di prefissi validi). Effort: mezza giornata con guardie.
2. **Organization schema assente sulla home** (verificato: solo WebSite). Serve il blocco Organization con logo, sameAs (profili social quando esistono), founder: è la base dell'entità "Aurya" nel Knowledge Graph e delle citazioni LLM. Effort: 2 ore.
3. **Eventi di conversione GA4**: oggi misuriamo visite ma non lead. L'invio del form lead (traveler/operator) va tracciato come evento `generate_lead` e marcato conversione in GA4. Senza, non sapremo mai quale articolo/canale porta lead. Effort: 2-3 ore.

### P1 — prime 4 settimane
4. **Pagine autore** (`/autori/valentina`, `/autori/davide`): bio, credenziali (Reiki terzo livello), foto, elenco articoli; `Person.url` nel JSON-LD degli articoli punta lì. È il moltiplicatore E-E-A-T dell'intero Magazine. Effort: 1 giorno.
5. **Articoli correlati automatici** in fondo a ogni articolo (stessa categoria / stesso cluster): oggi l'internal linking vive solo nei link in-content. Effort: mezza giornata (l'API lista per categoria esiste già).
6. **Allungare i pilastri**: i 19 articoli viaggiano a 700-830 parole; i 4-5 pilastri di cluster vanno portati a 1.500+ con sezioni aggiuntive (tabelle comparative, esempi). Effort: editoriale, 30-45 min a pezzo.
7. **Profili social del brand** linkati dal footer e nel sameAs: segnali di entità, oggi assenti.

### P2 — con il lancio o subito dopo
8. **Hub /discipline/{slug}** programmatici (il ponte informazionale→transazionale già nel piano, fase 3).
9. **Review schema** sulle recensioni verificate (rich snippet ★) appena la directory è indicizzabile.
10. **Redirect strategy per il lancio**: gli URL noindex diventano indicizzabili col flag; pianificare il giro IndexNow di massa + resubmit sitemap nel runbook di lancio (già nel playbook, da eseguire).
11. **Link building attivo** (il vero collo di bottiglia): badge fondatori, 3 directory, primo pitch PR. Nessuna riga di codice: solo esecuzione.
12. **Immagini**: alt descrittivi sulle cover nel listing blog; valutare WebP responsive (srcset) sulle cover se LCP mobile peggiora.

## Cosa NON serve fare (anti-rumore)
- Migrare le sitemap fuori da /api/ (l'Allow nel robots è sufficiente e standard).
- AMP, infinite scroll SEO, paginazione rel=prev/next (deprecata).
- Tradurre gli articoli ora (IT-first confermata dalla strategia).
- Ossessionarsi con GSC nei primi 14 giorni: proprietà a giorno zero, i dati arrivano.

## Roadmap consigliata
- **Questa settimana**: P0.1 (soft-404), P0.2 (Organization), P0.3 (evento lead GA4). Un giorno di lavoro totale, chiude ogni debito tecnico.
- **Settimane 2-4**: P1 (autori, correlati, pilastri allungati) + cadenza editoriale 2/settimana + prime 3 directory.
- **Al lancio**: runbook playbook sez. 6 (swap riferimenti pre-lancio, flip noindex, IndexNow di massa, Review schema).
- **Post-lancio**: onde A/B/C del piano editoriale + link building continuativo.
