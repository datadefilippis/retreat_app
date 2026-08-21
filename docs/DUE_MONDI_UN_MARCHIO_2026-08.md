# Due mondi, un marchio — sito Aurya e Aurya Sound (21 agosto 2026)

Domanda del founder: sito/gestionale e Sound/meditazioni hanno design e
colori completamente diversi. I due prodotti restano separati — ma la
differenza è fuorviante per chi passa dall'uno all'altro? Serve
uniformare qualcosa (il menu? qualcosa in comune)?

Analisi sul codice e sulle due superfici viste affiancate.

---

## 1. Il fatto che ribalta la domanda

Le due palette **non sono due palette**. Sono la stessa, a due livelli
di luce. Numeri veri, presi dai token:

| ruolo | sito Aurya | Aurya Sound | distanza |
|---|---|---|---|
| crema / avorio | `hsl(42, 35%, 97%)` | `bone hsl(41, 27%, 88%)` | **1° di tinta** |
| oro | `#c9b37e hsl(42, 41%, 64%)` | `lamp hsl(33, 67%, 62%)` | 9° di tinta, **stessa luminosità** |
| verde/acqua | `hsl(158, 28%, 30%)` | `water hsl(174, 31%, 57%)` | 16° di tinta, **stessa saturazione** |
| fondo scuro | footer `hsl(160, 28%, 13%)` | `panel hsl(191, 32%, 13%)` | 31° di tinta, **stessa luminosità** |

E la tipografia dei titoli è **letteralmente lo stesso font**: Iowan Old
Style regge sia «Il mondo del benessere è largo» nel Magazine sia «Le
*meditazioni* di Aurya» nel buio.

C'è di più: il **footer del sito è già scuro** — verde-petrolio con un
filo d'oro sopra — cioè esattamente il registro di Sound. E l'eroe del
Magazine è un'immagine scura con serif chiaro. Il buio non è un
territorio straniero: è già il secondo tempo del sito.

**Quindi la percezione di «completamente diversi» non nasce dal
colore.** Nasce da tre cose, di cui solo la prima è voluta.

## 2. Da dove nasce davvero lo stacco

**a) L'inversione di luce (voluta, da tenere).** Chiaro-su-crema per
leggere e scegliere; scuro per ascoltare a occhi chiusi. È giusto così:
un lettore multimediale al buio è una convenzione che la gente conosce,
e serve al prodotto. Nessuno si confonde perché un cinema è buio.

**b) Due derive accidentali.** L'acqua di Sound è 30° più blu del verde
di marca, e l'oro è 26 punti più saturo. Sono scivolamenti nati dal
prototipo, non decisioni: sono loro a far sembrare «un'altra azienda»
quello che è solo «la stessa stanza di sera».

**c) La perdita di tutti i punti fissi — il vero problema.** Passando
il confine spariscono in blocco:

| | sito | Sound |
|---|---|---|
| navigazione | 6 voci (Magazine, Sound, Meditazioni, Manifesto, La Rete, Chi siamo) | **nessuna** |
| identità (omino) | sempre presente, due mondi nel menu | **assente** |
| uscita | logo + footer completo | logo «torna al sito» + 4 link in fondo |
| marchio | `AURYA` in Cinzel, maiuscolo, tracking 0.28em | `Aurya` in serif minuscolo + mono |

L'ultima riga è la più grave e la meno visibile: **il marchio è scritto
in due modi diversi**. Stesso medaglione, due lockup. È l'unica cosa
che davvero non deve mai cambiare tra due prodotti della stessa casa.

E l'assenza dell'omino ha una conseguenza concreta, non estetica: chi è
loggato entra nelle meditazioni e **smette di vedere che è loggato**.
Non può uscire, non può raggiungere il suo account, non sa chi è. In un
mondo dove esistono i preferiti e i contenuti riservati, è un vuoto.

## 3. Cosa penso

**Non uniformare i due design. Uniformare le costanti.**

Il valore di Sound è anche il suo essere un altro posto: uno strumento,
non una vetrina. Ripitturarlo di crema lo ucciderebbe, e portarci
dentro Tailwind/shadcn butterebbe via l'isolamento `.fqz`, che è un
asset (Sound non può rompere il gestionale, e viceversa).

Ma «prodotti separati» non vuol dire «marche separate». La regola che
userei, in una riga:

> **Cambia la luce, non l'identità.**
> Marchio, oro, verde e serif sono gli stessi ovunque. Cambiano il
> fondo, la densità e il tono della voce.

Con questa regola il passaggio smette di essere uno stacco e diventa
quello che è: entrare nella stessa casa la sera.

## 4. Cosa suggerisco, in ordine di rapporto valore/costo

### DN1 — Un solo marchio (mezz'ora, impatto massimo)
Il lockup di Sound diventa quello del sito: medaglione + `AURYA` in
Cinzel maiuscolo, stesso tracking, stesso oro. Sotto, in mono, resta la
firma del mondo: `SOUND` invece di «torna al sito» (l'uscita è già il
clic sul marchio, come su ogni sito).

### DN2 — L'omino anche nel buio (mezza giornata)
Una versione scura, minima, dello stesso menu del sito, in alto a
destra nella `topbar` di tutte le viste Sound: chi sei, il tuo account,
il gestionale se sei operatore, Esci. Stesse voci, stessa logica
(`lib/cerchio` e i due token la conoscono già): cambia solo la pelle.
Chiude il vuoto vero, non quello estetico.

### DN3 — Un oro solo, un verde solo (un'ora)
Allineare `--lamp` all'oro di marca e `--water` al verde di marca,
schiarendoli quanto serve per il fondo scuro **senza spostare la
tinta**. Il buio resta buio; la famiglia diventa esatta. Da fare a
occhio sui contrasti (AA sul testo mono piccolo).

### DN4 — Una passerella, non un menu completo (mezza giornata)
Nella `topbar` di Sound, accanto al marchio, le due o tre voci che
servono davvero lì: *Meditazioni · Sound · Magazine*. Non l'intero menu
del sito: solo il filo per non sentirsi in un vicolo. E, dall'altro
lato, la voce «Sound» del menu del sito può portare un piccolo segno
(un punto d'oro) che prepara al cambio di luce.

### DN5 — Dirlo, una volta (mezz'ora)
Sulla landing `/sound` una riga sola, sotto il titolo: «Aurya Sound è
lo studio di Aurya: qui si compone e si ascolta.» Una frase che dichiara
la parentela costa meno di qualunque restyling e la rende ovvia.

### Cosa NON farei
- non portare il crema dentro Sound;
- non portare Tailwind/shadcn dentro `.fqz` (né il contrario);
- non replicare l'intero menu del sito nel buio: sarebbe rumore in un
  posto fatto per chiudere gli occhi;
- non unificare i due shell: il confine tecnico è sano.

## 5. Ordine

DN1 e DN2 da soli chiudono il 90% del problema: uno risolve la marca,
l'altro l'orientamento. DN3 e DN4 rifiniscono, DN5 è una riga di testo.
Totale realistico: ~1,5 giornate, nessun rischio sui flussi.

Verifica: aprire `/blog` e `/meditazioni` affiancate. Dopo DN1+DN3 il
marchio e gli accenti devono essere indistinguibili da una schermata
all'altra; il resto — fondo, densità, mono — può e deve restare diverso.
