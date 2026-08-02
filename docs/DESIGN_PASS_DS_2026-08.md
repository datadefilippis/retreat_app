# Ciclo DS — il design delle pagine del sito (2 ago 2026)

Richiesta del founder: «l'unica pagina che mi piace a livello di design
e' la landing per gli operatori. Migliora tutte le altre pagine
toccate: design moderno, visual, creativita', userfriendliness. Non
cosi' minimale come ora.» Nessun test: si tocca solo il design.

## Il metro di paragone
`frontend/src/features/prelaunch/OperatorLandingPage.js` e' la pagina
approvata. Cosa la fa funzionare, in ordine di importanza:
1. **Ancora scura in apertura**: il verde profondo regge un titolo
   grande e da' subito un carattere. Le altre pagine aprono su crema,
   e la crema da' aria ma non da' identita'.
2. **Foto vere e grandi**, non decorazioni da 200px.
3. **Alternanza di fondi** (verde → sabbia → crema → bianco → verde):
   ogni sezione si stacca dalla precedente, la pagina si legge a
   blocchi mentre si scorre.
4. **Blocchi a schede con foto**, non elenchi puntati.
5. **Ancore multiple verso l'azione**, mai una sola in fondo.

## Il difetto comune delle altre pagine
Sono colonne di testo centrate su crema. Il Manifesto apre con una
frase gigante su fondo vuoto: elegante in un PDF, muto in un browser.
Chi siamo, /operatori e il Magazine hanno lo stesso problema in
misura minore. Non manca il copy: manca il **ritmo visivo**.

## Grammatica DS (vale per tutte le pagine)
- **Apertura**: mai testo solo su fondo piatto. O foto a tutta
  larghezza col velo, o ancora verde piena, o accostamento
  foto/parola. Il titolo entra dentro l'immagine, non sopra il vuoto.
- **Alternanza obbligatoria**: due sezioni adiacenti non possono
  avere lo stesso fondo. La sequenza tipo: scuro → crema → foto a
  tutta larghezza → sabbia → bianco → scuro.
- **Una foto a tutta larghezza per pagina** almeno, come respiro a
  meta' percorso (il posto giusto per la frase-teoria del Blueprint).
- **Sezioni a due colonne** (foto / testo) alternate di lato: mai
  tre split di fila dallo stesso lato.
- **Navigabilita'**: sulle pagine lunghe (Manifesto, Chi siamo) un
  indice dei movimenti in colonna appiccicata a lato su desktop, che
  sul telefono diventa una riga di ancore sotto l'apertura. Serve a
  far capire quanto e' lunga la pagina e dove si e'.
- **Movimento discreto**: `useReveal` gia' esiste; le foto possono
  avere uno zoom lentissimo all'hover. Niente parallasse, niente
  animazioni che partono da sole. `prefers-reduced-motion` sempre
  rispettato.
- **Contrasto AA misurato** su ogni testo sopra foto: il velo si
  calcola, non si spera.
- Kit condiviso `components/editorial/`: i mattoni nuovi si
  aggiungono LI', mai stili inventati dentro una pagina.

## Il magazzino foto (dieci, piu' i ritratti)
Sono poche e vanno distribuite: la stessa foto su due pagine vicine
si nota subito.
- `r01.jpg` donna in meditazione al torrente, verde pieno, orizzontale
- `r02.jpg` meditare insieme (gruppo) — GIA' su landing e home
- `r03.jpg` una persona nel suo elemento — GIA' su landing
- `r04.jpg` mano in gyan mudra, macro, fondo scuro: bellissima per
  ancore scure e citazioni a tutta larghezza
- `r05.jpg` il cairn, una pietra alla volta — GIA' su landing
- `r06.jpg` — GIA' sulla home
- `r07.jpg` meditazione seduta sull'acqua, luce alta
- `r08.jpg` le mani di chi cura, da vicino — GIA' su landing
- `r09.jpg` la pratica nello spazio di tutti — GIA' su landing
- `r10.jpg` massaggio, mani sulla schiena, calde, macro
- `/media/chisiamo-aurya.jpg` i fondatori (unica foto vera nostra)
- `/media/aurya-hero.mp4` + poster: il tramonto, gia' sulla home
- `hero-organizer.webp`, `hero-blog.webp`, `hero-destination.webp`

Assegnazione per evitare ripetizioni:
- Manifesto → `r04` (ancora scura), `r01` (fascia a tutta larghezza)
- Chi siamo → `chisiamo-aurya` (grande, non francobollo), `r07`
- /operatori → `r10` in apertura, ritratti veri nelle schede
- Magazine → `hero-blog` in apertura, le copertine fanno il resto

LIMITE DA DIRE AL FOUNDER: sono foto d'archivio generiche. Con
queste il sito arriva a "curato"; per arrivare a "inconfondibile"
servono foto vere degli operatori della rete. E' la prossima leva,
piu' del codice.

## Onde
- **DS1** — kit: i mattoni visivi che mancano + Manifesto rifatto.
- **DS2** — Home di rete + Chi siamo.
- **DS3** — /operatori + Magazine (indice e scheda articolo).

Regole: nessun test (richiesta founder), verifica nel browser
obbligatoria a 1440 e 390, screenshot per il founder, il COPY NON SI
TOCCA (e' stato approvato onda per onda), commit per onda, prod ferma.
