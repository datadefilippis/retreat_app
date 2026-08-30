# Il funnel delle landing — analisi e piano (ciclo FN, 30/8/2026)

*Il test del founder: ascolta l'anteprima di 90 secondi in landing,
clicca «Continua l'ascolto» — e la pagina della meditazione completa
gli chiede di RIASCOLTARE altri 90 secondi prima di mostrare il
cancello. Il momento più caldo del funnel (ha appena consumato
l'anteprima e vuole il resto) viene raffreddato da un secondo
pedaggio. E quando il cancello finalmente appare, parla in gergo
interno («la Lettera di Aurya») a qualcuno che non sa cosa sia.*

## 1 · La diagnosi, da marketing expert

**Il funnel consumer oggi** (landing /sound → sezione Meditazioni):

```
play 90s → patto inline («L'ascolto completo è di chi riceve la
Lettera» + 2 link) → /frequenze/slug → ALTRI 90s → cancello
(«iscriviti alla Lettera di Aurya») → form → conferma email
```

I difetti, in ordine di gravità:

1. **Il doppio pedaggio.** `PublicFrequencyPage` apre il cancello
   solo a `t ≥ PREVIEW_SEC` *su quella pagina* — non sa che
   l'anteprima è già stata consumata in landing. Il visitatore più
   caldo del sito riascolta 90 secondi identici. Tasso di caduta
   garantito.
2. **Il gergo.** «L'ascolto completo è di chi riceve la Lettera» è
   una bella frase per chi conosce Aurya — per un visitatore freddo
   è un indovinello. Il valore («la meditazione completa, gratis»)
   e il prezzo («l'iscrizione alla newsletter») non sono mai detti
   in chiaro.
3. **L'iscrizione è lontana dal desiderio.** A fine anteprima il
   form NON c'è: ci sono due link. Ogni salto di pagina tra «voglio
   il resto» e «lascio l'email» è attrito puro. Il popup che chiede
   il founder è giusto: il form deve comparire lì, subito.
4. **Il trigger sepolto.** «Tutte le Meditazioni →» è un link
   testuale sotto il player — il catalogo (9 meditazioni vere) è il
   secondo gancio più forte della pagina ed è invisibile.
5. **Dispersione dell'hero.** L'hero di /sound ha due CTA: «Esplora»
   (biblioteca editoriale, freddo) e «Per i professionisti» (altro
   pubblico). Il gancio più caldo — *ascolti una meditazione vera
   adesso* — sta tre sezioni sotto e l'hero non lo dice.
6. **Crea Studio (/sound/studio)**: hero forte, ma «Accesso su
   invito» è ripetuto due volte, manca la prova sociale (le
   meditazioni pubblicate SONO il portfolio di Crea) e il form
   chiede il «racconto» senza dire cosa succede dopo.

## 2 · Il principio

**Un solo pedaggio, detto in chiaro, pagabile sul posto.**
L'anteprima si ascolta UNA volta; quando finisce, l'invito appare
subito, dice in italiano semplice cosa ottieni e cosa costa
(«la meditazione completa è gratis: serve l'iscrizione alla
newsletter»), e il form è lì — niente salti di pagina. Chi paga il
pedaggio è sbloccato ovunque (il cerchio già funziona così).

## 3 · Le onde

### FN1 — Il pedaggio si paga una volta *(il fix del founder)*
Fine anteprima in landing → segno di sessione
(`fqz_anteprima_finita` in sessionStorage, best-effort) e link
«Continua l'ascolto» con `?da=anteprima`. `PublicFrequencyPage`,
se NON sbloccato e (parametro o segno presente) → **cancello aperto
all'arrivo**, senza riascolto. Il «riascolta l'anteprima» resta come
via d'uscita. Chi arriva da un link condiviso (senza segno) vive il
flusso di oggi: 90s liberi, poi cancello.

### FN2 — Il cancello parla chiaro *(via il gergo)*
Un componente unico del cancello (oggi è markup duplicato in
concetti tra landing e pagina traccia) con il copy nuovo:

> **La meditazione completa è riservata agli iscritti.**
> L'iscrizione alla newsletter di Aurya — la Lettera — è gratuita:
> pratiche, esperienze e nuove meditazioni, una volta ogni tanto.
> [email] [✓ consenso] **Iscriviti e continua l'ascolto →**
> Sei già iscritto? Sblocca con la tua email.

Plain language prima, il brand («la Lettera») come apposizione, mai
come premessa. Stesso linguaggio ovunque il cancello compare.

### FN3 — Il popup a fine anteprima *(l'iscrizione sul posto)*
A fine 90s in landing il patto non è più due link: è **il cancello
stesso**, lì, con il form (riusa `iscriviESblocca` del cerchio — la
meccanica esiste già). Chi si iscrive resta in landing, sbloccato, e
la CTA diventa «Ascolta la meditazione completa →». Chi non vuole ha
«Tutte le Meditazioni» e il riascolto.

### FN4 — Il trigger in evidenza
«Tutte le Meditazioni» diventa un **Bottone pieno (oro)** con il
numero vero («Le 9 Meditazioni →», contato dal catalogo), presente:
sotto il player, dentro il cancello di fine anteprima, e in chiusura
di pagina. L'hero di /sound guadagna la CTA calda: primaria
**«Ascolta una meditazione — 90 secondi»** (àncora al player),
secondaria «Esplora». Il richiamo professionale ESCE dall'hero (vive
già nella band Crea, sezione 5 — un pubblico, una porta).

### FN5 — Crea Studio, rifinitura marketing
- «Accesso su invito» detto UNA volta (nel form, non anche nell'hero);
- prova sociale: sopra il form, la riga «Le meditazioni che senti su
  Aurya nascono qui» con link a /meditazioni;
- il form dice cosa succede dopo («ti rispondiamo entro pochi
  giorni, si parte con una call di 20 minuti»);
- hero: resta «La tua voce, le tue meditazioni» (funziona), CTA
  unica #accesso.

### FN6 — Potatura della landing Sound
Le sezioni 6-7-8 (evidenza/processo/futuro) si compattano: la
promessa di metodo in UNA sezione con tre righe ciascuna — la landing
oggi ha 8 sezioni e il funnel ne regge 6. Niente sezioni nuove.

## 4 · Collaudo (misurabile)
Anteprima in landing → fine → form lì → iscrizione → sbloccato senza
cambiare pagina; «Continua l'ascolto» → cancello GIÀ aperto (zero
riascolto); link condiviso freddo → 90s liberi poi cancello; copy
senza «Lettera» come premessa in nessun cancello; bottone «Le N
Meditazioni» con N vero; guardie su segno di sessione, parametro,
copy e gerarchia CTA.

*Ordine: FN1+FN2 (stesso cancello), FN3, FN4, FN5, FN6.
Effort: ~1 giornata. In attesa del «procedi».*
