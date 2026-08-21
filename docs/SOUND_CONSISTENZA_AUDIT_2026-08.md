# Aurya Sound — audit di consistenza pre-go-live (21 agosto 2026)

Domanda del founder: ciò che scriviamo e ciò che facciamo ascoltare è
coerente? Diciamo A e facciamo sentire B? Le frequenze dichiarate
corrispondono? I parametri in Crea agiscono davvero? E i respiri —
troppo finti — vanno tolti?

Metodo: ho confrontato **ogni scheda** (titolo, riga Hz, testo,
approfondisci) col suo `cfg` numerico e con ciò che le due sintesi
producono; ho verificato i percorsi dell'editor; le misure citate sono
quelle già fatte strumentando render e anteprima nei cicli ONDA.

---

## 1. Il verdetto d'insieme

**L'impianto è onesto e regge.** Le 38 schede dichiarano valori che il
motore suona davvero (verificato numero per numero: i toni suonano il
loro hertz esatto, le bande un valore dentro la banda dichiarata, i
ritmi del corpo il ritmo promesso — misurato 6,0 / 60,0 / 120,0 cicli
al minuto). I testi distinguono con rigore raro fenomeno e
attribuzione, e i gradi A/B/C sono usati con giudizio. Le due sintesi
(render e anteprima) concordano nelle misure fatte. Il patto «niente
promesse terapeutiche» è rispettato ovunque.

Ma l'audit ha trovato **9 punti** da sistemare, di cui 3 sono vere
incoerenze «diciamo A, suona B» e 2 sono comandi che non fanno nulla.
Nessuno è grave da solo; insieme, per un go-live, vanno chiusi.

## 2. Le incoerenze vere (diciamo A, suona B)

### C1 — «Armoniche di Schumann»: promette quattro modi, ne suona uno
La riga sotto il titolo dice «≈14, 20, 26, 33 Hz · modi risonanti» —
plurale. Il cfg suona **solo 14,3 Hz**. Chi ascolta credendo di sentire
«le armoniche» sente un isocronico singolo.
*Fix minimo:* riga → «≈14 Hz · il secondo modo (e gli altri: 20, 26,
33)» e una frase nell'approfondisci: «in ascolto c'è il secondo modo».
*Fix pieno:* un ciclo a gradini che attraversa 14,3 → 20 → 26 → 33 (la
curva `steps` esiste già).

### C2 — «Gamma» e «40 Hz» suonano IDENTICHE, e nessuno lo dice
Stesso metodo, stesso battito, stessa portante (`iso 40, carrier 200`).
Due schede diverse, stesso identico audio: legittimo (una racconta la
banda, l'altra lo stimolo studiato) ma va dichiarato, o chi le prova
in fila pensa a un errore.
*Fix:* una riga incrociata su entrambe («è lo stesso stimolo della
scheda …») — oppure differenziare la Gamma (es. binaurale a 40).

### C3 — «Tono puro 136 Hz»: si chiama 136, suona 136,1
Dettaglio, ma è esattamente il genere di scarto che il brand non si
può permettere: il nome nel cfg dice `136 Hz`, il carrier è `136.1`
(l'Om). *Fix:* nome → «Tono puro 136,1 Hz», e nel testo dire che è lo
stesso tono della scheda Om (anche questa è una quasi-ridondanza
voluta: lì si parla del metodo, là della frequenza — dichiararlo).

## 3. Comandi che non fanno nulla (peggio di un testo impreciso)

### C4 — Sulla scheda in ascolto, il campo «battito» è morto per 3 metodi
La barra dei controlli live mostra sempre `volume` + `battito` (o
`frequenza` per il tono). Ma per **bordone, discesa infinita e
respiro** il campo battito non è collegato a niente: `setBeat` agisce
su `lfo`/`vR`, che per quei metodi sono nulli. L'utente digita, non
cambia nulla, e conclude che Aurya Sound è rotto.
*Fix:* per `drone` mostrare `frequenza` (agisce su `setCarrier`); per
`shepard` e `breath` o si collega il campo (ottave/min, respiri/min)
o si nasconde. **Da fare prima del go-live.**

### C5 — In Crea, le modifiche NON toccano la sessione in ascolto (tranne il volume)
Risposta diretta alla domanda del founder: **no, non si adattano.**
Durante «Ascolta sessione» solo il volume del livello è collegato al
vivo (`setLayerGain`). Battito, portante, metodo, curva, **muto**:
cambiano lo stato ma non il suono — si sentono solo fermando e
riascoltando. Nessun testo lo dice.
È una scelta tecnica difendibile (le curve sono disegnate alla
partenza), ma **muta e non dichiarata** diventa un'incoerenza: l'utente
preme «muto» e il livello continua a suonare.
*Fix minimo:* riavvio automatico della sessione dal punto in cui era
quando cambia un parametro strutturale (stop + start con `fromT`
esiste già per il seek). *Fix intermedio:* almeno il MUTO agisce al
vivo (è un gain: `setLayerGain(id, 0)`), e una riga sotto il player:
«le altre modifiche si sentono al prossimo ascolto».

### C6 — Le tre schede nuove non dicono se serve la cuffia
La mappa `LISTEN` («🎧 solo in cuffia / 🔊 anche in altoparlante») non
ha voci per `drone`, `shepard`, `breath`: le schede nuove escono senza
la riga che tutte le altre hanno. Tutte e tre suonano bene in
altoparlante → aggiungere le tre voci.

## 4. La domanda sui Metodi: «perché non mostriamo la frequenza?»

Perché un metodo **non è** una frequenza: è una tecnica, e la riga
sotto il titolo descrive la tecnica («due toni · uno per orecchio»).
Ma la scheda **suona** un esempio concreto, e quello ha numeri: il
binaurale suona 400 Hz con battito 10→6, il bilaterale 220 Hz a 1 Hz…
Oggi quei numeri non sono scritti da nessuna parte: l'utente sente
qualcosa di preciso senza sapere cosa.
*Fix:* aggiungere alla riga (o sotto) «in ascolto: portante 400 Hz ·
battito 10→6 Hz» per ognuna delle 11 schede Metodi. Onesto, didattico,
e coerente col resto del catalogo dove i numeri ci sono.

## 5. I respiri — la deep analysis richiesta

### Perché suonano finti (analisi da sound engineer)
Il respiro sintetico ha già la forma giusta (asimmetria 3,5/5 s, pausa,
timbro che si apre e chiude — misurato). Ma un respiro **vero** ha tre
cose che nessun rumore filtrato avrà mai:

1. **struttura formantica**: l'aria passa per naso/bocca, cavità che
   risuonano; il nostro è rumore bianco filtrato, cioè vento;
2. **variabilità ciclo su ciclo**: nessun respiro umano è identico al
   precedente (periodo ±5%, ampiezza, piccole irregolarità); il nostro
   è perfettamente periodico — ed è QUESTO che il cervello riconosce
   subito come artificiale;
3. **i transienti**: l'attacco dell'inspirazione vera è più rapido e
   «sporco» (turbolenza), la fine dell'espirazione ha spesso un
   micro-colpo.

Siamo nella **uncanny valley**: abbastanza simile da evocare un
respiro, abbastanza diverso da suonare falso. Il founder lo sente
giusto.

### Le quattro strade

| | strada | pro | contro |
|---|---|---|---|
| A | **Smettere di imitare**: il pacer dichiarato — un suono astratto (bordone o tono morbido) che si gonfia e sgonfia con la forma del respiro già costruita | onestissimo («non imita il respiro: lo guida»), zero uncanny valley, riusa tutto il lavoro ONDA 6 (forma, pausa, timbro) | meno «suggestivo» di un soffio |
| B | **Registrazione vera** dalla libreria (regola del founder: i suoni veri non si imitano) | realismo assoluto | un respiro registrato ha UN ritmo fisso: non può seguire f0, né la marea che rallenta; andrebbe registrato a 6/min esatti, e la «marea del respiro» morirebbe |
| C | **Più realismo sintetico** (jitter di periodo, formanti, transienti) | migliora | non uscirà mai dalla valle: più realismo = più evidente ciò che manca |
| D | **Togliere le 3 schede** respiro (tenendo cuore e cammino) | pulizia | si butta l'unico contenuto con evidenza vera (la respirazione lenta), e il lavoro ONDA 6 |

### La mia raccomandazione: A, con un innesto di B
Il valore della scheda **è il ritmo, non il realismo** — lo dice già il
testo («il suono fa il metronomo»). L'errore è stato dare al metronomo
un timbro che *finge* di essere aria. La coerenza si ristabilisce
cambiando il timbro, non la funzione:

- il `breath` suona un **gonfiarsi e sgonfiarsi astratto e dichiarato**
  (es. il bordone armonico dentro l'inviluppo del respiro: sale
  chiaro, scende cupo, tace — la catena c'è già, cambia la sorgente:
  da rumore a tono);
- i testi passano da «respiro» a **«guida del respiro»**: «questo
  suono non imita un respiro: ti dà il passo. Sali quando sale, scendi
  quando scende, fermati nella pausa»;
- *(innesto B, facoltativo e successivo)*: una base **registrata** di
  respiro vero a 6/min in libreria (categoria Corpo), per chi vuole il
  realismo — dove il ritmo fisso non è un limite perché è il ritmo
  giusto.

Così nessuno può dire «suona finto»: non finge più niente. E la marea
del respiro (il rallentare graduale) sopravvive, perché un tono
astratto può seguire qualunque curva.

## 6. Minori, da nota

- **N1** — la scheda «Scegliere la portante» dichiara i default (400
  bin / 180 altri) ma metà delle schede usa portanti diverse per
  scelta (Delta 140, Gamma 200, cuore 110, bilaterale 220…). Una
  frase: «le schede di questa biblioteca a volte scelgono altre
  portanti, ed è il motivo per cui suonano diverse tra loro».
- **N2** — `inhale`/`exhale` esistono nel modello ma non nell'editor:
  chi compone non può cambiarle. Va bene per ora (default sensati), ma
  o si espongono o si documenta che sono fisse.
- **N3** — i nomi-file «solfeggio» della libreria basi che non
  corrispondono all'audio: già sistemato nel ciclo SL (titoli
  neutri); resta vero per i file sorgente su disco, irrilevante per
  l'utente.
- **N4** — le 9 Solfeggio: nove schede quasi identiche (tone, cambia
  solo il carrier). Non è un'incoerenza — è il sistema che è fatto
  così, e i testi lo smontano con onestà — ma in griglia occupano più
  spazio di quel che dicono. Possibile (non necessario) raggrupparle
  in una scheda sola con selettore.

## 7. Priorità per il go-live

| # | cosa | tipo | costo |
|---|---|---|---|
| 1 | C4 — campi morti sulle schede live | comando finto | ½ h |
| 2 | C5 — muto al vivo + riga «al prossimo ascolto» (o riavvio auto) | comando finto | 1-2 h |
| 3 | C6 — riga cuffie/altoparlante per i 3 metodi nuovi | gap | 10 min |
| 4 | C1 — armoniche di Schumann | A vs B | ½ h |
| 5 | §5 — respiri → guida dichiarata (strada A) | identità | ½ giornata |
| 6 | §4 — «in ascolto: …» sulle 11 schede Metodi | trasparenza | 1 h |
| 7 | C2, C3, N1 | precisione | 1 h |

Totale: **~1,5 giornate** per un catalogo che a quel punto regge
qualunque orecchio esperto: niente comandi finti, niente promesse
plurali con audio singolare, e un respiro che non finge.
