# L'anello e il numero — ciclo AT4 (21 agosto 2026)

Due segnalazioni del founder dopo il deploy:

1. *«i suoni riesco ad ascoltarli anche se il telefono si blocca ma le
   frequenze no, come mai? riesci a uniformare?»*
2. *«su Delta scriviamo in alto 0,5–4 Hz e poi in basso 140 Hz, cioè
   quanti Hz sono?»* — con il timore che l'avviso sia fuorviante.

Entrambe centrate. La seconda era un difetto mio.

---

## 1. Perché i suoni reggevano e le frequenze no

Non era un caso: erano due meccanismi diversi.

| cosa | come suona | blocco schermo |
|---|---|---|
| **suoni** della libreria | `new Audio()` con `loop = true` — un file in un media element | **regge** |
| **frequenze** | sintesi WebAudio dal vivo | il browser la **sospende** |

Uniformarle significa dare anche alle frequenze un file da mettere in
un `<audio loop>`. Il che apre il problema vero.

## 2. Il problema di un file che gira: la giunzione

Se alla fine del file le fasi non sono quelle dell'inizio, si sente un
**clic a ogni giro**. Su uno strumento da meditazione è inaccettabile.

La soluzione non è un trucco, è aritmetica: si sceglie una durata **D**
che chiuda insieme *tutte* le componenti periodiche della scheda —
la portante, il battito, e il respiro lento del motore (l'ondulazione
±8 % con periodo 26 s che `envAt` aggiunge a ogni livello).

Misurato sul catalogo:

- **28 schede su 36 chiudono in 26 secondi esatti**;
- 4 in 130 s (136,1 Om, Armoniche Schumann, Ritmo del respiro, Battimento lento);
- Schumann 7,83 non chiude entro un tempo ragionevole col respiro:
  ripiega su 100 s, dove chiudono portante e battito.

Due accortezze che il calcolo da solo non copre:

- **`envAt` apre ogni livello con un attacco fino a 12 s** e lo chiude
  con un rilascio fino a 16 s: renderizzati dentro l'anello, farebbero
  *pulsare* il giro. Quindi si renderizza una finestra più larga (30 s
  di margine per lato) e si **ritaglia il centro**, dove il livello è in
  tenuta piena.
- **rumore e discesa Shepard non hanno fase che torna** (il rumore è
  casuale, le voci Shepard accumulano fase per sempre). Per loro
  interviene una **dissolvenza incrociata** di 1,5 s — che dove il
  calcolo *è* esatto non cambia un solo campione, perché mescola il
  segnale con se stesso. Per questo si applica sempre: gratis dove non
  serve, decisiva dove serve.

### La misura, sul motore vero

Non sulla fiducia: ho eseguito `neuroSample` — lo stesso codice del
render — e confrontato il campione a `M` con quello a `M+D`.

| esito | schede |
|---|---|
| **scatto 0,0000 % del picco** | **32 su 33** |
| 0,49 % (−46 dB), coperto dalla dissolvenza | Schumann 7,83 |

## 3. Quale frequenza entra nell'anello

Un **tragitto non si ripete all'infinito**: Delta va da 4 a 2,5 Hz in
tre minuti. L'anello è il punto d'**arrivo** — cioè dove si sta quando
si ascolta a lungo. E se chi ascolta ha preso il comando col campo
della frequenza, l'anello tiene **il suo numero**: quello che ha
davanti agli occhi.

Una sola frequenza per volta: due anelli sovrapposti sono un
pasticcio, non una sessione. Chi vuole sovrapporle usa «+ sessione».

## 4. Il numero che non diceva che cosa fosse

Delta mostra in cima **«0,5–4 Hz»** (la banda EEG, cioè il *ritmo*) e
suona su una portante di **140 Hz** (il *tono*). Il mio avviso lasciava
cadere «140 Hz non esce dall'altoparlante» senza dire quale delle due
cose fosse — mettendo la scheda in contraddizione con se stessa,
proprio dove il suo testo lungo insegna che *«una banda EEG e una
frequenza sonora non sono la stessa cosa»*.

Ora l'avviso **presenta** il numero, in tre forme secondo il metodo:

| metodo | testo |
|---|---|
| ritmici (iso, bin, mono, bil, breath) | «Il ritmo viaggia su un tono di **140 Hz**, troppo grave per l'altoparlante del telefono: servono le cuffie.» |
| tone, drone — dove il titolo **è già** il tono | «Un tono di **174 Hz** è troppo grave per…» |
| shepard — sette voci su sette ottave | «Le voci più gravi della discesa sono troppo gravi per…» |

E nella sessione pubblica: «il tono su cui viaggiano le frequenze
(140 Hz)», non «140 Hz» e basta.

## 5. Guardie

`test_ascolto_telefono.py` sale a **35**. Le nuove difendono ciò che si
romperebbe in silenzio: il periodo di 26 s deve restare **lo stesso
numero** in `anello.js` e in `envAt` (se cambia solo di là, ogni anello
ricomincia a scattare e non se ne accorge nessuno fino all'orecchio di
chi ascolta); il margine deve superare attacco e rilascio; l'ordine
della ricerca (prima i multipli del respiro); un solo lettore per
sessione e anello; l'anello non dichiara una fine né comandi di
spostamento; e nessun «numero nudo» torna nei testi.

## 6. Restano aperti

- **«Crea» sembra muta sul telefono** — diagnosi in §7, da decidere;
- il pulsante compare solo su telefono, come il resto del ciclo AT: è
  lì che lo schermo si blocca.

## 7. Perché «Crea» sembra non suonare (diagnosi, non ancora risolto)

Segnalazione: *«ho fatto una registrazione, clicco play ma non sento
nulla; qualsiasi elemento aggiungo alla sessione non si riproduce»*.

Non è l'altoparlante: **una voce sta ben sopra i 500 Hz**. È che la
sessione parte da quasi zero e ci mette molto ad arrivare:

| tempo dal play | volume |
|---|---|
| 2 s | **1,5 %** |
| 3 s | **4,7 %** |
| 5 s | 18,8 % |
| 12 s | 100 % |

La dissolvenza d'ingresso della sessione (10 s, predefinita) si
**moltiplica** per l'attacco del livello (fino a 12 s, dentro `envAt` —
un comportamento del motore che l'operatore non vede e non controlla).
Le schede in Esplora salgono invece in **1,5 secondi**: ecco perché lì
si sente e in Crea no.

Su un telefono, al 4,7 % e con una portante grave, i primi secondi sono
indistinguibili dal silenzio. Chi preme play e aspetta due secondi
conclude — ragionevolmente — che è rotto.

Tre strade, da scegliere:

1. **dirlo** (nessun cambio all'audio): mentre la dissolvenza sale, la
   riga di stato lo scrive — «dissolvenza d'ingresso: il volume sale»;
2. **anteprima senza dissolvenza**: in Crea si ascolta per verificare,
   non per meditare; la dissolvenza resterebbe nella traccia
   pubblicata. Cambia l'anteprima, non l'opera;
3. **accorciare l'attacco dentro `envAt`**: cambia l'audio di tutto,
   compreso ciò che è già pubblicato. Da non fare senza una decisione
   esplicita.

Consiglio la 1 subito e la 2 come scelta tua, perché la 2 tocca il
significato di «ascolta» dentro lo studio.
