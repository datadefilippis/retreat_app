# Aurya Lab: piano di refinement olistico (lotto «LA»)

8/10/2026, sera. Richiesta del founder: «in Aurya Sound abbiamo rifatto il
design di tutto tranne che di Aurya Lab: refinement olistico, navigabile,
moderno, stiloso, ottimizzato, far capire tutto in modo semplice. Senza
toccare le funzionalità: solo design, usabilità e aspetto. Zero
regressioni.» Solo piano, nessuna modifica al codice.

I riferimenti sono le pagine già rifatte: la casa (MR), Esplora (ES), Crea
(CR): stessa grammatica (card raggio 20, pastiglie, selettore a tre,
fogli, barra in basso), stessi gettoni (`casa.css`, `esplora.css`,
`crea/crea.css`).

## 0. Diagnosi (dal codice e dallo schermo, 375 px e 1240 px)

### Com'è fatto
- **Il Lab è già una casa con stanze** (ciclo LU, 28/8): la Sala
  (`lab/LabSala.jsx`) e cinque stanze (`/sound/lab/banco|orecchio|
  ritratto|meraviglie|risonanze`), ognuna una pagina sottile (30–35 righe)
  che monta il telaio `lab/Stanza.jsx` (testata, «Perché ti interessa»,
  «Cosa puoi fare qui», riga di sicurezza, ponte al glossario, invito,
  piede) e dentro gli strumenti.
- **Gli strumenti sono moduli puliti**: `Generatore`, `SecondaVoce`,
  `LettureBanco` (con `Oscilloscopio`, `Spettro`, `Spettrogramma`),
  `Orecchio`, `Ritratto` (+ `RitrattoVisual`, `OndaViva`), `Meraviglie`,
  `Risonanze`, `Percorsi`, `InvitoQuaderno`. Il motore (`motore.js`,
  `fonderia.js`, `ritrattista.js`, `cimatica.js`, `accordatore.js`,
  `fenomeni.js`, `quadro.js`, `usaLab.js`) è a parte e non si tocca.
- **Il vestito è `lab/lab.css`** (516 righe, 9 media query), cresciuto a
  strati (LB1…LB8, LU, RZ, LM4, LM5, FA2/FA4) sopra `frequenze.css`.
- **I pin**: `tests/test_sound_lab.py` (480 assert) legge testid,
  stringhe e alcune regole CSS esatte (`.fqz .lab-ritorno{` con
  `position:sticky` e `linear-gradient`, `.fqz .lab-rz-tono{position:sticky`,
  `.fqz .lab-ondaviva{`, `.fqz .lab-freeze,…`, `.fqz .lab-quaderno-riga b{…`,
  `.fqz .lab-ritratto-colA,…`, `.lab-freq-num input{font-size:32px !important}`,
  `.lab-slider::-webkit-slider-thumb{width:22px;height:22px`); e
  `test_sound_sistema` vuole la stringa `StanzeSound` in `LabSala.jsx` e
  `Stanza.jsx`. Il restyling lavora **sopra** queste regole, non le
  sostituisce.

### Cosa si vede (telefono 375 px)
| Cosa | Misura | Perché è un problema |
|---|---|---|
| **Testata doppia** in ogni stanza: pill «← Sala del Lab» sticky, h1, domanda, poi la **barra delle stanze vecchia** (Esplora · Lab · Impara · Crea · Le mie tracce) | «Le mie tracce» sborda: pagina larga **411 px su 375** in tutte le stanze | il Lab è l'unica pagina del suono senza il selettore a tre (la Sala ce l'ha, le stanze no); due navigazioni diverse a un tocco di distanza |
| **Prima dello strumento: 800–860 px** di testo («Perché ti interessa» + «Cosa puoi fare qui») | Banco 814, Orecchio 792, Ritratto 859, Meraviglie 834 | lo strumento comincia al secondo schermo; chi torna la seconda volta rilegge la stessa spiegazione |
| **Il Banco è una colonna**: Generatore (forme, numerone, cursori, ampiezza, fase, dove suona, ▶) → Sweep → Sorgente B → poi Oscilloscopio, Spettro, Spettrogramma | **4.576 px**; 15 bottoni e 14 campi; su desktop (1240) ancora una colonna da 760 px, oscilloscopio a 1.900 px dal generatore | **si gira la manopola e non si vede l'onda**: le letture, cioè la prova, stanno tre schermi sotto; su desktop lo spazio ai lati è vuoto |
| L'Orecchio: microfono, poi le tre letture; le Meraviglie: 13 fenomeni + «il banco classico» + le letture | 2.846 e **4.069 px** | ogni stanza ripete sotto le stesse tre tele; su telefono lo spettrogramma è una tela da scorrere |
| «Cosa sta succedendo / Cosa stai leggendo / Perché i cartellini»: blocchi di 6–10 righe dentro le card | | spiegano bene ma **sempre aperti**, prima o in mezzo al gesto |
| Pulsanti e pastiglie **mono maiuscole piccole** (10–11 px), card raggio 12, bordo 1 px, sfondi quasi uguali | | è il vestito di agosto: non la grammatica di oggi (raggio 20, oro pieno sul gesto primario, pastiglie) |
| Il Ritratto: ▶ «Registra e analizza» al centro, poi tabella, A/B, fonderia, quaderno | 2.114 px | buono; manca solo un ritmo chiaro «1 registra → 2 leggi → 3 confronta» |
| Le Risonanze: sweep «da / a / durata» + «Misura», la curva, i picchi «tienila», il quaderno | 2.238 px | la barra del tono è già sticky; il resto è una colonna di numeri |
| In fondo a ogni stanza: riga cuffie, ponte al glossario, invito al Cerchio, piede | | tre code uguali in sei pagine |
| La Sala: 5 carte + «Da dove parto?» + 3 percorsi + nota + trigger | 2.483 px | le carte sono già l'idea giusta; manca il tono per stanza, le carte sono grigie e uguali |

**Cosa è già buono e si tiene**: la struttura a domande (una stanza =
una domanda), il telaio unico, i percorsi guidati, l'onestà (cartellini
A/B/C, «quello che senti è quello che vedi»), la pill di ritorno sticky,
il numerone della frequenza, il cruscotto sticky delle Risonanze, i tap da
pollice (LM5), le didascalie.

## 1. Il principio

**Lo strumento in primo piano, la spiegazione a portata.** Ogni stanza
si apre con la domanda e lo strumento; «Perché ti interessa» e «Cosa puoi
fare qui» restano, ma dietro un foglio «?» (aperto da soli la prima volta,
poi ripiegati: la scelta si ricorda nel browser). Le letture stanno
**accanto** al gesto: su desktop due colonne (comandi a sinistra, tele a
destra, sticky), sul telefono la tela principale **sotto il dito**, sticky
in alto mentre si scorre fra i comandi, le altre due in schede.

Una sola navigazione: la passerella sopra, il **selettore a tre**
(Frequenze · Fondamenta · Lab) in testa a ogni stanza, e sotto la **riga
delle stanze** (cinque pastiglie, la corrente accesa) per passare da una
stanza all'altra senza tornare in Sala. La Sala resta la porta: carte col
tono, i percorsi, «da dove parto?».

**Nessuna funzione cambia**: stessi componenti, stessi handler, stessi
testid, stesso motore. Il lotto tocca solo `Stanza.jsx` e `LabSala.jsx`
(l'ordine e la cornice), i wrapper delle cinque stanze (chi sta in quale
colonna) e un foglio di stile nuovo `lab/lab-vestito.css` che si posa sopra
`lab.css` (che resta com'è, coi suoi pin).

## 2. I lotti

### LA0 La cornice (½ giornata)
- `Stanza.jsx`: via la barra delle stanze vecchia (`StanzeSound` resta nel
  file, come in `LabSala`, dietro `SOUND_ESPLORA_NUOVA`), dentro il
  **selettore a tre** con «Lab» acceso; sotto, la **riga delle stanze**
  (Banco · Orecchio · Ritratto · Meraviglie · Risonanze, pastiglie
  scorrevoli, la corrente in oro). La pill «← Sala del Lab» resta (pin
  FA2).
- Larghezza: **375 px senza scroll orizzontale** (oggi 411).
- h1 + domanda più compatti; la domanda come sottotitolo in corsivo,
  non in mono maiuscolo.
- Guardia: `tests/test_lab_la.py`.

### LA1 La spiegazione a portata (½ giornata)
- «Perché ti interessa» e «Cosa puoi fare qui» diventano **un foglio
  «?»** (stesso `Foglio` di Crea) con un bottone in testata «Perché e
  cosa fare»; alla **prima visita** di ogni stanza il foglio si apre da
  solo, poi resta chiuso (`localStorage`, in try/catch, mai bloccante).
  Il testo (`perche`, `azioni`) non cambia: cambia dove si legge. I pin
  («Perché ti interessa», «Cosa puoi fare qui», `lab-testata`,
  `lab-domanda`) restano nel telaio.
- I blocchi «Cosa sta succedendo / Cosa stai leggendo / Perché i
  cartellini» dentro gli strumenti diventano **ripiegabili** (titolo a
  vista, testo con un tocco), chiusi di default sul telefono, aperti su
  desktop. Solo CSS + un attributo sul contenitore: il testo resta nel
  componente.
- Le tre code (riga cuffie, ponte al glossario, invito) si compattano in
  **una riga** sotto gli strumenti: 🎧 Controindicazioni · Glossario →, e
  l'invito al Cerchio una volta sola, più piccolo.

### LA2 Il Banco accanto alle letture (1 giornata)
- Desktop (≥ 1024): **due colonne**: a sinistra Generatore, Sweep,
  Sorgente B (scorrono); a destra le tre tele **sticky** (Oscilloscopio
  sopra, Spettro e Spettrogramma come schede sotto). Si gira la manopola
  e si vede l'onda.
- Telefono: la tela principale (Oscilloscopio) **sticky in alto**, bassa
  (120 px), mentre si scorre fra i comandi; sotto il generatore, le altre
  letture in schede (Spettro · Spettrogramma) a fine pagina. Il bottone
  «Congela» resta accanto alle tele.
- Il Generatore: le quattro forme come **pastiglie con la sagoma** in una
  riga, il numerone intatto (pin `font-size:32px`), ampiezza e fase come
  oggi; «Dove suona» inline; ▶ Genera in oro pieno (il gesto primario).
- Solo markup di contenitore nei wrapper (`LabBanco.jsx`: chi va a sinistra
  e chi a destra) e CSS: `Generatore`, `SecondaVoce`, `LettureBanco`
  intatti.

### LA3 Le altre stanze sullo stesso telaio (1 giornata)
- **L'Orecchio**: microfono + accordatore (la nota grande, i cents) a
  sinistra, le letture a destra/sticky come nel Banco.
- **Il Ritratto**: i tre tempi come **passi numerati** (1 Registra, 2
  Leggi la carta d'identità, 3 Confronta A/B e rifondi) con la stessa
  pastiglia numerata delle schede di Studio; la tabella dei modi e la
  fonderia com'erano; il quaderno sotto.
- **Le Meraviglie**: i 13 fenomeni come **card compatte** in griglia
  (nome, una riga, cartellino A/B/C come punto colorato, ▶ in oro), i tre
  gruppi (Lo spazio · La geometria · L'illusione) come intestazioni; «il
  banco classico» e le letture sotto, in schede.
- **Le Risonanze**: il cruscotto sticky resta (pin); «da / a / durata +
  Misura» in una riga; la curva; i picchi come **pastiglie «tienila»**;
  il quaderno come lista compatta.

### LA4 La Sala (½ giornata)
- Le cinque carte con il **tono della stanza** (salvia, acqua, oro,
  viola, sabbia: lo stesso velo delle famiglie di Esplora) e una sagoma
  (onda, orecchio, impronta, stella, campana), raggio 20, «Entra →» in oro.
- «Da dove parto?» come tre card orizzontali con un bottone, non righe di
  testo; i percorsi come oggi (si aprono), ma con il ▶ in oro e il numero
  dei passi.
- Il trigger di Studio resta in fondo (pin), con la grafica delle card.

### LA5 Il vestito (trasversale, dentro LA0–LA4)
- `lab/lab-vestito.css` sopra `lab.css`: card raggio 20, pastiglie,
  bottone primario oro pieno, chip con bordo, tipografia serif 22/17 per i
  titoli e 15 per il corpo, mono 11 solo per numeri ed etichette; contrasto
  AA; `prefers-reduced-motion`; bersagli ≥ 44 px (già LM5).
- Le tele: sfondo un po' più scuro del pannello, griglia tenue, raggio 14.
- Niente regola di `lab.css` cancellata: si sovrascrive con selettori più
  specifici (`.fqz.lab.vestito …`), così i pin sul CSS vecchio restano veri.

## 3. Come non rompere nulla
- **Flag** `LAB_VESTITO_NUOVO` in `stato.js`: la classe `vestito` sulla
  radice e il telaio nuovo si accendono col flag; `?vestito=vecchio` mostra
  il Lab di oggi, intero.
- **Gli strumenti non si toccano**: `Generatore`, `SecondaVoce`,
  `LettureBanco`, `Oscilloscopio`, `Spettro`, `Spettrogramma`, `Orecchio`,
  `Ritratto`, `RitrattoVisual`, `OndaViva`, `Meraviglie`, `Risonanze`,
  `Percorsi`, `InvitoQuaderno`, il motore e `usaLab`. Cambiano solo i
  wrapper (`LabBanco.jsx` ecc.: in quale colonna va cosa), `Stanza.jsx`,
  `LabSala.jsx`, e il CSS nuovo.
- **Stessi testid e stesse stringhe**; `lab.css` intatto; 480 assert di
  `test_sound_lab.py` verdi a ogni lotto; guardie nuove `tests/test_lab_la*.py`.
- **Prova a mano a ogni lotto** (375 e 1240): Banco (genera, sweep,
  sorgente B a 180°, XY, congela); Orecchio (microfono, accordatore);
  Ritratto (registra, tabella, A/B, fonderia, quaderno); Meraviglie (tre
  fenomeni, cartellini); Risonanze (misura, tienila, WAV, quaderno);
  percorsi dalla Sala; iOS: il motore nasce al primo tocco (nessun
  cambio).
- Suite completa e build a ogni lotto, commit per lotto, deploy su «go».

## 4. Cosa NON si tocca
Il motore e l'analisi (`lab/*.js`), gli strumenti, i testi delle stanze,
i cartellini, i percorsi, il quaderno (locale e remoto), la pill di
ritorno, il cruscotto sticky delle Risonanze, la shell SEO del Lab.

## 5. Ordine e tempi

| Lotto | Giorni | Flag |
|---|---|---|
| LA0 cornice | ½ | `LAB_VESTITO_NUOVO` |
| LA1 spiegazione a portata | ½ | idem |
| LA2 Banco accanto alle letture | 1 | idem |
| LA3 le altre stanze | 1 | idem |
| LA4 la Sala | ½ | idem |

Totale **≈ 3,5 giorni**, LA5 dentro gli altri.

## 6. Domande per il founder
1. **La spiegazione dietro «?»** (aperta da sola la prima volta, poi
   ripiegata), o sempre a vista com'è oggi?
2. **Le letture accanto ai comandi** (due colonne su desktop, tela sticky
   sul telefono): va bene?
3. **La riga delle stanze** in testa a ogni stanza, per passare da una
   all'altra senza tornare in Sala: sì?
4. **Le Meraviglie come griglia di card** (13 card compatte) invece della
   lista: sì?
