# Il ballerino — analisi della correlazione suono→visual (ciclo DA)

**Data**: 22 agosto 2026 · **Stato**: analisi, in attesa del «procedi»
**Richiesta founder**: «le forme si muovono anche senza suono, stessa
modalità […] voglio che la connessione visual+suono sia REALE: ogni nota,
ogni frequenza, ogni ritmo deve produrre un effetto vero di movimento. Non
un unico movimento standard: un oggetto che si muove come un ballerino e si
adatta alla musica.»

---

## 1. Il verdetto, coi numeri del codice

Il founder ha ragione, e non è un'impressione: è aritmetica. Il moto della
scena oggi è dominato da **tre metronomi interni** che girano anche nel
silenzio assoluto:

| Sorgente di moto | Formula (nel codice) | Dipende dall'audio? |
|---|---|---|
| Il tempo della scena | `tAcc += dt·speed·(0.5 + energia·1.1)` | poco: **a silenzio scorre al 65-70%** della velocità di quando suona |
| Il respiro (la «spina dorsale del moto», parola del prototipo) | `breathPhase += dt/S.breath` | **MAI**: è un metronomo puro |
| I gesti dei petali (reach/fat/curl/dome) | seni autonomi su `t` con ampiezze 0.16-0.22 + audio con ampiezze 0.10-0.34 | l'audio pesa **~15-20% del gesto** |

E il rilevatore di «colpo» — l'unico evento ritmico — scatta solo su un
salto dei **bassi** (`kick > .035`): pensato per percussioni. Ma le
meditazioni Aurya **non hanno percussioni**: sono droni, battiti binaurali
e isochronic (0.05–60 Hz, da contratto dello score), maree lente, respiri
guidati. Il loro ritmo vive nella **modulazione d'ampiezza**, non nei
transienti. Risultato: su una meditazione tipica il colpo non scatta mai,
le bande sono quasi costanti, e ciò che si vede è al 100% il balletto dei
metronomi interni — identico a sessione ferma.

Tre difetti collaterali scoperti nell'analisi:

1. **Stop ≠ quiete**: in Crea, dopo lo stop la scena resta montata
   (`elapsed > 0`) con l'analizzatore che legge silenzio → il 65-70% del
   moto continua, uguale a prima. È esattamente ciò che il founder ha
   visto.
2. **Due orecchie diverse**: lo strumento usa il suo analyser con
   lisciatura 0.88; studio e meditazione usano l'analizzatore prestato di
   analisi.js a 0.5. Stessa scena, nervosismo diverso a seconda della
   porta da cui entri.
3. **Reactivity conta poco**: il selettore Calm/Soft/Deep/Full moltiplica
   pesi già piccoli — cambia poco perché modula il 20% del moto, non
   l'80%.

## 2. Il principio del consolidamento: l'energia è il carburante

Oggi l'audio è un **condimento** su un moto autonomo. Va rovesciato:

> **Nessun suono → quasi ferma. Suono → tutto il moto viene da lì.**

- Il tempo della scena scorre in funzione dell'energia, con un pavimento
  di *veglia* molto basso (~0.1: viva, ma visibilmente in attesa).
- Il respiro non è più un metronomo: la sua **ampiezza** è modulata
  dall'energia, e quando nella sessione c'è un ritmo lento vero (marea,
  respiro guidato), la sua **fase si aggancia a quello** (§3).
- I seni autonomi dei petali scendono di ampiezza; le componenti audio
  salgono. Rapporto obiettivo: **audio ≥ 70% del gesto** a suono attivo.
- Allo stop, la scena scivola in veglia in un paio di secondi — si VEDE
  che il suono se n'è andato. (Niente congelamento secco: brand.)

## 3. L'orecchio nuovo: sentire il ritmo che c'è davvero

Un solo estrattore (il «polso»), condiviso da strumento, studio e
meditazione — stessa lisciatura, stessa verità:

```
polso = {
  energia,          // inviluppo complessivo, liscio
  colpo,            // transiente su TUTTO lo spettro (flusso spettrale),
                    // non solo bassi: becca anche un cambio di nota
  battitoHz,        // il battito di MODULAZIONE (0.3–14 Hz): stimato
                    // dall'inviluppo dei bassi/medi — è l'entrainment
  faseBattito,      // 0..1 dentro il ciclo del battito
  ondaLenta,        // inviluppo lentissimo (maree, crescendo, respiri)
  brillantezza,     // centroide spettrale → scintillio/colore
}
```

Il pezzo di valore è `battitoHz`: le nostre meditazioni HANNO un ritmo
preciso — il battito isochronic/binaurale scelto dall'operatore — ed è
esattamente ciò che oggi la scena ignora. Agganciare i petali alla **fase
del battito di entrainment** significa che una sessione a 8 Hz pulsa
diversamente da una a 2 Hz: ogni ricetta balla la SUA musica.

**Vincolo di sicurezza non negoziabile**: il battito guida MOVIMENTO e
fase spaziale (aprirsi, propagarsi, torcersi) — **mai lampeggi di
luminanza globale sopra ~3 Hz** (fotosensibilità; il sipario avvisa già,
ma la miglior difesa è non costruire uno strobo). Sopra i ~3 Hz la
pulsazione si traduce in onde che viaggiano nello spazio, non in luce che
sbatte.

## 4. Le coreografie: sette forme, sette balli

«Non deve essere un unico movimento standard.» Oggi i 7 modi condividono
gli stessi uniform globali. Il consolidamento dà a ogni forma la sua
mappa:

| Forma | Il suo ballo |
|---|---|
| Breath | segue `ondaLenta` (se la sessione ha un respiro guidato, respira CON lui) |
| Nebula | densità e turbolenza ∝ energia; il colpo la squarcia |
| Spiral | velocità di avvolgimento ∝ bassi; i bracci si stringono sul colpo |
| Flow | il campo scorre a velocità ∝ energia, la direzione vira con la brillantezza |
| Mandala | i petali si aprono in fase col `battitoHz`; il colpo lancia un'ONDA radiale che attraversa le corone |
| Helix | torsione ∝ medi, passo ∝ bassi, scintillio ∝ alti |
| Ripple | **event-driven**: ogni colpo EMETTE un anello vero che viaggia |

La novità strutturale: **eventi propagativi**. Oggi il colpo è un uniform
che decade (tutta la scena sobbalza insieme). Un ballerino non sobbalza:
il gesto *attraversa* il corpo. Tecnica: il colpo scrive un timestamp
(`uHitT`), il vertex shader calcola l'onda in funzione della distanza dal
centro — il movimento si propaga, a costo zero di CPU.

## 5. La prova, non a occhio

- **Tracce-sonda** (solo dev): un isochronic puro a 2 Hz → si deve VEDERE
  pulsare a 2 Hz; un drone piatto → scena in veglia lenta; un colpo secco
  → un'onda sola che attraversa. Verifica col registratore di frame
  (varianza degli uniform), non a sensazione.
- **Guardie statiche**: pavimento del tempo ≤ 0.15; ampiezza dei seni
  autonomi ≤ metà della componente audio corrispondente; una sola
  lisciatura dichiarata; niente `Math.random` nel loop del polso; il
  vincolo anti-strobo (nessun mapping battito→brightness).
- **Una sola orecchia**: la lisciatura dell'analyser diventa un numero
  condiviso (tabelle/standard), identico per strumento, studio e
  meditazione.

## 6. Le onde del ciclo DA

- **DA1 — Il silenzio si sente**: energia come carburante (pavimenti giù,
  respiro/drift/tempo scalati), scivolata in veglia allo stop. È il fix
  del difetto segnalato, consegnabile da solo.
- **DA2 — L'orecchio (il polso)**: estrattore unico con flusso spettrale,
  battito di modulazione 0.3–14 Hz, onda lenta, brillantezza; lisciatura
  unificata.
- **DA3 — Le coreografie**: mappe per-forma + eventi propagativi;
  Reactivity che governa davvero (a Full l'audio È il moto).
- **DA4 — La prova del ballerino**: tracce-sonda, verifica strumentale,
  taratura finale con il founder davanti a 3-4 ricette vere.

Ordine pensato per il valore: DA1 ripara la fiducia («se fermo il suono,
la scena lo sa»), DA2-DA3 costruiscono la danza, DA4 la dimostra.

## 7. Cosa NON cambia

- La scena salvata nella ricetta (forme, colori, cursori, inquadratura) e
  tutto il ciclo VC: il ballo è COME si muove, non COSA si è scelto.
- Il costo server: zero — tutto accade sul dispositivo, come ora.
- Il vincolo brand (palette dell'autore, niente arcobaleno d'ufficio) e
  il sipario sicurezza.
- `/sound/visual` con mic/traccia: il polso vale anche lì (un DJ set nel
  microfono ballerà per davvero — è il caso facile; il difficile e più
  prezioso sono le nostre meditazioni, ed è per quello che c'è DA2).
