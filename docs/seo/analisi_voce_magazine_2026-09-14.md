# Analisi della voce del Magazine — 14 settembre 2026 (prima della revisione)

Misure sui 52 articoli pubblicati, calcolate con `scratchpad/analisi_voce.py` sul testo piano (link e titoli esclusi). Serve come base di confronto per la revisione editoriale (docs/REDAZIONE_VOCE_AURYA.md).

```
ARCHIVIO: 52 articoli, 75337 parole
frasi: media 15.8 parole, mediana 14.0, oltre 35 parole: 196 su 4780 (4%), oltre 50: 32
paragrafi: media 39 parole, oltre 90: 51 su 1949 (3%)
intro prima del primo H2: media 109 parole, max 172
menzioni Aurya: media 0.2 per articolo, max 4; bullet per articolo media 1.7

FRASI A EFFETTO (totale archivio):
   407  domanda retorica
    45  non è… è (stessa frase)
    30  come se / come un(a) (similitudine)
    14  vale più di
     8  non X, ma Y (contrapposizione)
     6  E poi c'è
     5  la parte (più) importante/che conta
     3  Non è X. È Y.
     3  Ed è (proprio) qui/lì
     3  va detto / detto semplice / onestamente
     2  che nessuno dice/racconta
     2  due punti + frase a effetto
     1  Il punto è
     1  la strada di casa
     0  non si tratta di… ma
     0  La vera domanda
     0  non è un lusso
     0  Il corpo lo sa
     0  non è magia

ESPRESSIONI RICORRENTI (n-grammi in >= 6 articoli):
  24 articoli,  39 volte: vale la pena
  24 articoli,  30 volte: ed è il
  21 articoli,  30 volte: ed è la
  20 articoli,  29 volte: motivo per cui
  20 articoli,  28 volte: il motivo per
  20 articoli,  28 volte: il motivo per cui
  20 articoli,  25 volte: è il motivo
  20 articoli,  20 volte: capire se un
  20 articoli,  20 volte: se un operatore
  20 articoli,  20 volte: capire se un operatore
  19 articoli,  27 volte: è la parte
  19 articoli,  25 volte: la parte che
```

## Cosa emerge

- Quasi ogni articolo apre con una scena costruita (formula scena → spiegazione → promessa → introduzione); le introduzioni sono lunghe (109 parole in media prima del primo H2, fino a 172).
- Domande retoriche: 407 in 52 articoli, otto per articolo.
- Tic ricorrenti in decine di articoli: «vale la pena» (24), «ed è il/la» (30+30), «il motivo per cui» (28), «è la parte che» (25), «è il modo più», «vale più di», «il momento in cui», «tutto il resto», «è il punto», «la maggior parte delle persone», «non è… è» nella stessa frase (45), similitudini «come se/come un» (30).
- I cinque articoli del 14/9 hanno frasi troppo cariche (19-22 parole di media, 11-15% oltre le 35) e paragrafi da 140-176 parole.
- Funziona già: profondità, fonti, prezzi veri, struttura H2 → FAQ, link interni, Aurya poco presente (0,2 menzioni per articolo).

## Dopo la revisione (14 settembre 2026, sera — NA11, in produzione)

Tutti i 52 articoli sono stati riscritti nella voce del brief e pubblicati con
`backend/scripts/na11_revisione_voce.py` (testi in `na11_revisioni.json`).
Vincoli rispettati e verificati a macchina su ogni articolo: titolo invariato,
link identici (stessi URL, stesso numero), stesso numero di FAQ, nessun numero,
fonte o dato nuovo, lunghezza fra il 75% e il 110%, menzioni di Aurya non
aumentate, nessuna frase promozionale. Backup della collezione prima della
scrittura: `/root/articles_pre_na11.archive` sul server.

Misure sul corpo degli articoli (FAQ escluse dove indicato), prima → dopo:

```
parole                              74.972 → 69.671  (−7%)
parole per frase (media)              16,4 → 13,0
frasi oltre 35 parole                  196 → 29     (4,3% → 0,5%)
paragrafi oltre 90 parole               51 → 15
intro prima del primo H2 (media)       109 → 72 parole (max 172 → 108)
intro oltre 90 parole (la «scena»)      40 → 2 articoli
domande retoriche nel corpo             81 → 70 (quelle rimaste sono domande da fare all'operatore o al programma)
tic e formule nel corpo                265 → 84
```

## Secondo giro: il filo logico (16 settembre 2026 — NA12, in produzione)

Applicata la sezione 7 del sistema editoriale (`docs/AURYA_MAGAZINE_SISTEMA_EDITORIALE.md`)
ai 52 articoli: per ognuno è stato scritto il percorso mentale del lettore e
confrontato con gli H2. Esito: 34 «ok così» (struttura già nell'ordine delle
domande; in 12 di questi solo una frase d'intro che anticipa il percorso) e
18 «riordinati» (sezioni spostate o unite, raccordi riscritti, testo delle
sezioni parola per parola). Pubblicati 29 articoli (`na12_struttura.json`),
backup `/root/articles_pre_na12.archive`. Voce intatta: nessun tic in più,
nessuna domanda retorica in più, link identici, FAQ mai in aumento (5 FAQ
doppione tolte: assicurazione, bio, promuovere, digiuno), numeri invariati.

Riordinati: assicurazione RC, bio professionale, bagno di gong, cammini
italiani, cerchi di donne, operatore serio, promuovere un ritiro, insegnante
di yoga, costellazioni, digiuno, domande da fare, meditazione per chi inizia,
partita IVA, prezzo giusto, Reiki, shiatsu, tarocchi, Toscana.

Due correzioni fatte a mano nello stesso giro: il link «bagni di foresta»
nella guida Toscana puntava alla guida dei cammini (ora alla guida giusta);
«ventidue domande» era un conteggio sbagliato (sono ventotto: corretto in
description, in «come scegliere un ritiro» e in «quanto costano»).

Due eccezioni accettate a mano nel primo giro: una lista in più in «ciclo mestruale» (i
segnali da portare dal medico) e in «cerchi di donne», «bagno di gong»,
«alimentazione ayurvedica», «promuovere un ritiro» (una per articolo, come
ammesso dal brief); nel «kit pratiche» l'ultima FAQ era una frase senza «?» e
ora è una domanda (stesso contenuto, ora leggibile dal parser delle FAQ).
