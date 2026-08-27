# La BUSSOLA di Aurya Sound — analisi UX e piano (ciclo NV, 27/8/2026)

*Richiesta founder: «mi viene il dubbio che sia caotico, che l'utente
si perda e non trovi Crea». Il dubbio è fondato. Questa è l'analisi
dei percorsi reali (letta dal codice, non dai ricordi) e il piano.*

---

## 1 · L'analisi: dove ci si perde oggi

**A. La parola «Sound» dice due cose diverse.** Nel menu del sito
chiaro «Sound» porta alla landing di sistema (/sound). Nella
passerella del mondo scuro «Sound» porta alla biblioteca
(/sound/esplora). Stessa parola, due destinazioni: chi passa di là
impara che «Sound» non è un posto, ed è il modo più rapido per
disorientare.

**B. La navigazione del mondo scuro è SPARSA su tre barre.** Le
stanze di Aurya Sound oggi si raggiungono da posti diversi:
- la passerella (topbar): Meditazioni · Sound · Lab · Magazine;
- il viewswitch nell'header di FrequenzePage: Esplora · Crea · Impara;
- una tbpill nella topbar: «Le mie tracce» (il fratello di Crea, in
  un'altra barra!);
- il Lab è una pagina a sé, promossa a voce di primo livello.
Risultato: Crea e Le mie tracce — i pulsanti PIÙ critici per
l'operatore — vivono in due barre diverse, e il Lab (uno strumento
della biblioteca) pesa quanto le Meditazioni. Non c'è UNA barra che
dica «queste sono le stanze, tu sei qui».

**C. I filtri delle basi si spengono a vicenda.** Nel mondo Suoni di
Crea, selezionato un «momento del viaggio», i timbri (Natura, Droni…)
diventano `disabled` con un tooltip che ordina di tornare su «Tutti».
Due assi che il modello dati già tratta come ortogonali (momento È
trasversale alle categorie, dice il commento nel codice) sono
mutuamente esclusivi SOLO nella UI: l'utente che vuole «Catarsi +
Natura» non può, e non capisce perché.

**D. Il funnel professionale nel mondo scuro è un sussurro.** La
striscia «Per i professionisti» esiste solo in fondo alla porta di
/sound/esplora. Un operatore loggato SENZA chiavi che gira per
biblioteca, guida o meditazioni non incontra mai Crea Studio: il
prodotto da vendere è invisibile proprio a chi dovrebbe comprarlo.

**E. La pagina Strumenti è giusta ma spoglia.** La carta di Sound
Studio è testo su bianco: manca la copertina che faccia dire «questo
è un prodotto», e la pagina non ha il respiro delle superfici nuove.

**La gerarchia dei pulsanti critici, come DOVREBBE essere:**
- per il VISITATORE: Ascolta (anteprima/esperienze) → Lettera;
- per l'ISCRITTO: Meditazioni → ascolto completo;
- per l'OPERATORE senza chiavi: il trigger a Crea Studio, OVUNQUE;
- per l'OPERATORE con chiavi: Crea e Le mie tracce, SEMPRE a un
  click, nella stessa barra.

## 2 · Il piano (onde NV)

- **NV1 — Strumenti col vestito buono** (½ giornata): la carta di
  Sound Studio prende la COPERTINA (la spirale di luce — la stessa
  identità della landing Studio) con velo scuro e titolo sopra;
  layout moderno (cover-top, hover, badge di stato sull'immagine);
  la carta «prossimi strumenti» resta sobria. La pagina prende il
  respiro delle superfici nuove.

- **NV2 — la passerella dice la verità** (¼ giornata): la voce
  «Sound» diventa **«Biblioteca»** (è il suo nome anche sulla landing:
  la porta si chiama «La Biblioteca» — una parola sola, coerente);
  la voce «Lab» ESCE dalla passerella. Passerella finale:
  Meditazioni · Biblioteca · Magazine (+ Professional per chi ha il
  privilegio). Guardie DN/sistema evolute con la decisione.

- **NV3 — UNA barra delle stanze** (1 giornata): il viewswitch
  diventa la barra unica del mondo Sound, condivisa da FrequenzePage
  E SoundLabPage: **Esplora · Lab · Impara** per tutti, più
  **Crea · Le mie tracce** per chi ha le chiavi (Crea conserva il
  conteggio dei livelli). «Le mie tracce» esce dalla topbar ed entra
  nella barra, accanto a Crea. Il Lab smette di essere un'isola:
  stessa barra, stessa stanza, si arriva e si torna senza pensarci.
  È la risposta a «l'utente non trova Crea»: quando ha le chiavi,
  Crea è nella barra delle stanze, sempre, evidenziato.

- **NV4 — i filtri si combinano** (½ giornata): momento × timbro in
  AND, niente più `disabled`: ogni combinazione è cliccabile; se il
  risultato è vuoto, un messaggio onesto («Nessuna base Natura per la
  Catarsi — prova ad allentare uno dei due») con il click che
  allenta. Le due righe di filtri si presentano per quello che sono:
  due assi («Momento del viaggio» / «Timbro»), etichettati.

- **NV5 — il trigger professionale, ovunque serva** (½ giornata):
  per anonimi e operatori SENZA chiavi, una riga discreta ma
  presente nelle stanze del mondo scuro (biblioteca, guida,
  meditazioni): «Sei un professionista del benessere? Componi le tue
  meditazioni con Crea Studio →» (/sound/studio). Un componente
  solo, montato dove serve; sparisce per chi ha già le chiavi.
  Nome coerente OVUNQUE: Crea Studio (mai «Sound Pro»).

- **NV6 — il collaudo dei percorsi** (½ giornata): tre traversate
  complete verificate a schermo — visitatore (landing → anteprima →
  Lettera), iscritto (meditazioni → ascolto), operatore con chiavi
  (login → barra → Crea → salva → Le mie tracce → condividi) — più
  le guardie: passerella fotografata col nome nuovo, barra delle
  stanze con Crea per chi ha chiavi, filtri mai disabled, trigger
  presente per chi non le ha.

## 3 · Decisioni prese nel piano (da confermare col founder)

1. Il nome della voce del mondo scuro: **«Biblioteca»** (alternative
   scartate: «Esplora» è un verbo non un posto; «Frequenze» è gergo).
2. Il Lab sta nella barra delle stanze, terzo dopo Esplora — non
   più voce di menu.
3. Il trigger professionale usa il nome «Crea Studio» ovunque.
4. «Le mie tracce» accanto a Crea nella barra (non più in topbar).

## 4 · Fuori scope (detto per non rifarlo)

Ricerca nelle basi, riordino drag-and-drop dei livelli, breadcrumb,
onboarding a tooltip. Prima la bussola, poi gli ornamenti.
