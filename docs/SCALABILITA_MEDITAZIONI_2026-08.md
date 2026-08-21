# Le meditazioni scalano? — analisi con numeri (21 agosto 2026)

Domanda del founder: se gli operatori iniziano a pubblicare mix da 30
minuti, il server si appesantisce in modo esponenziale?

**Risposta corta: il server no — regge benissimo, per come è fatto.
Il collo di bottiglia è altrove, e non si vede in nessuna metrica del
server: è la RAM del telefono di chi ascolta.**

---

## 1. Perché il server è quasi immune (la scelta che paga)

Una meditazione **non è un file audio: è una ricetta**. Il documento
salvato è uno score JSON; la sintesi avviene nel browser di chi
ascolta. Misurato su una traccia vera: **581 byte**. Un mix ricco da
dieci livelli sta in ~3 KB.

| cosa | 1 meditazione | 1.000 meditazioni |
|---|---|---|
| spazio in Mongo | ~0,6–3 KB | **~3 MB** |
| CPU del server per ascolto | **zero** (sintetizza il browser) | zero |
| basi audio | condivise | **le stesse 62, 635 MB — non cresce** |

Le basi sono una **libreria condivisa**: mille meditazioni che usano
«Atmosfera» puntano allo stesso file. Il solo dato che cresce
davvero per operatore è la **voce registrata** (~1 MB/minuto), oggi 4 MB
in tutto.

Quindi: pubblicare non pesa. **Ascoltare** pesa.

## 2. Il vero limite: la memoria di chi ascolta (misurato)

Per suonare una sessione il motore **scarica e decodifica l'intera
base**: WebAudio ha bisogno del buffer completo per programmare
l'ascolto. Misurato in browser su «Beatitudine», 30 minuti, 55,4 MB:

| grandezza | valore |
|---|---|
| file scaricato | 55,4 MB |
| tempo di decodifica | **4,9 s** |
| **RAM occupata dal buffer decodificato** | **611 MB** |

Non è un errore di misura: 1.816 s × 44.100 Hz × 2 canali × 4 byte.
L'audio compresso «esplode» ×11 quando diventa suono.

**Conseguenza pratica**: una sessione con **due** basi da 30 minuti
chiede **~1,2 GB** al dispositivo. Su desktop passa; **su un telefono
è un crash** (Safari iOS chiude la scheda ben prima). È esattamente lo
scenario della domanda — operatori che pubblicano mix lunghi — e il
limite scatta sul dispositivo, non sul server.

Nota: il tetto di 60 MB che ho messo alla cache dei buffer protegge
dall'**accumulo** fra un ascolto e l'altro, ma non riduce il costo
della base **in uso**.

## 3. Banda: sostenibile, ma senza rete di sicurezza

Nessun CDN: tutto esce dal singolo VPS.

| ascolti/mese | banda (2 basi ≈ 115 MB) |
|---|---|
| 1.000 | 112 GB |
| 10.000 | 1,1 TB |
| 50.000 | 5,6 TB |

I 20 TB inclusi Hetzner reggono fino a ~170.000 ascolti/mese: il tetto
economico è lontano. Attenuante importante: `/uploads` risponde
`immutable, max-age=1 anno`, quindi **chi riascolta non riscarica**.

## 4. Il difetto vero e proprio, oggi (database)

La vetrina `/meditazioni` interroga così:

```
find({status: "published"}).sort("published_at", -1).to_list(500)
```

Verificato col query planner: **`SORT → COLLSCAN`** — scansione
dell'intera collezione e ordinamento in memoria. Non esiste un indice
su `(status, published_at)`.

Tre problemi, in ordine di gravità:

1. **`to_list(500)` tronca in silenzio**: alla meditazione numero 501,
   le più vecchie spariscono dalla vetrina senza che nessuno se ne
   accorga. Non c'è paginazione;
2. **COLLSCAN**: invisibile a 20 tracce, pesante a 5.000 — e la
   scansione tocca anche le bozze, che sono la maggioranza;
3. la proiezione porta **l'intero array `score.layers`** solo per
   contarli: si trasferiscono i livelli di 500 documenti per stampare
   un numero.

Il contatore degli ascolti (`$inc` su `plays_total`) usa invece lo
slug, che **è** indicizzato: quello va bene.

## 5. Cosa farei, in ordine di valore

### A. Il tetto onesto sulle basi lunghe (il più importante)
Il problema non è il numero di meditazioni: è la **durata delle basi**.
Tre strade, dalla più economica:

1. **una base lunga si può LOOPARE**: il layer ha già `loop`. Una base
   ambient di 2 minuti in loop suona come una da 30 e costa **40 MB di
   RAM invece di 611**. Basterebbe curare la libreria con basi corte e
   loopabili (le 30 minuti diventano ridondanti) — zero codice;
2. **avvisare l'operatore in Crea** quando la sessione supera una
   soglia di memoria stimata («questa sessione chiede ~1,2 GB: su
   molti telefoni non partirà»);
3. streaming a pezzi delle basi (MediaSource): risolve davvero, ma è
   un lavoro serio e fragile su iOS. Solo se 1 e 2 non bastano.

### B. L'indice e la paginazione della vetrina
Indice `(status, published_at)`, proiezione che **non** porta i livelli
(un campo `layers_count` calcolato alla pubblicazione), e paginazione
al posto del `to_list(500)`. Mezza giornata, e la vetrina regge
decine di migliaia di tracce.

### C. Quando servirà davvero: CDN sugli /uploads
Non oggi. Diventa la mossa giusta oltre le decine di migliaia di
ascolti mensili, o appena arrivano ascoltatori fuori dall'Europa.

## 6. Giudizio

L'impianto è **giusto**: la scelta di salvare la ricetta e non l'audio
è ciò che rende il server quasi indifferente al numero di meditazioni.
Non c'è nessuna crescita esponenziale lato server.

Ma «scala bene» non è ancora vero fino in fondo, per due motivi
diversi da quello temuto: **una vetrina che tronca a 500 senza dirlo**,
e **basi lunghe che chiedono al telefono più memoria di quanta ne
abbia**. Entrambi si sistemano prima che diventino visibili — e il
primo dei due, oggi, costa solo una scelta di curatela.
