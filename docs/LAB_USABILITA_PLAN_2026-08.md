# Il Lab usabile — analisi e piano (ciclo LU, 28/8/2026)

*La diagnosi del founder, a ciclo LB appena chiuso: «abbiamo tutto in
una pagina e poco si capisce a cosa serve cosa. Io stesso che sono
neofita non capisco nulla — come usarlo, per quale fine, perché».
Ha ragione, ed è la diagnosi giusta al momento giusto: il ciclo LB ha
costruito gli STRUMENTI (otto onde, 91 guardie, fisica misurata); ora
il laboratorio va reso ABITABILE. Questo piano fa due cose: verifica
che quel che c'è sia solido, e lo ristruttura perché una persona
qualunque capisca cosa farci.*

---

## 1 · L'analisi: cosa c'è e cosa non va

**Cosa c'è (solido, misurato):** nove pannelli su una pagina sola —
Generatore (con sweep e passo fine), Sorgente B, Orecchio
(accordatore), Ritratto+Fonderia, tre letture col congela, Meraviglie
(13 fenomeni), Risonanze (con quaderno), Percorsi. Motore React-free
con phase-lock, analisi ospite, ingresso per i suonatori di banco.

**Cosa non va (i quattro difetti, in ordine di gravità):**

1. **La pagina è un magazzino, non un laboratorio.** ~4.000 righe di
   pannelli in colonna: chi entra vede una parete di strumenti senza
   sapere quale prendere. L'indice (LB8) aiuta chi GIÀ sa cosa
   cercare — il neofita no.
2. **Manca il PERCHÉ prima del COSA.** Le didascalie (regola LB)
   spiegano ogni modulo, ma spiegano *come funziona*, non *a cosa ti
   serve*. Un neofita davanti a «Spettro — le frequenze che
   compongono il segnale» legge parole giuste e non sa ancora perché
   dovrebbe interessargli.
3. **Il gergo non è tutto tradotto.** Hz, dB, parziale, fondamentale,
   T60, dBFS, Nyquist: alcuni hanno la spiegazione accanto, altri no.
   E `/sound/impara` (le fondamenta) esiste già ma il Lab non ci
   porta mai nel punto giusto.
4. **Un solo URL per otto esperienze.** Non si può dire a qualcuno
   «prova l'accordatore» con un link: si atterra sempre sul magazzino
   intero. (E per la SEO: una pagina = una sola query presidiata.)

**Verifica di solidità (fatta ora, cosa resta da fare):** suite 91
verdi sul Lab e 284 su Sound; build ok; il chunk del Lab è lazy. Da
collaudare nel ciclo: il ciclo di vita del motore quando le stanze
diventano pagine (creazione/spegnimento per pagina), i fogli mobile
stanza per stanza, e il collaudo col MICROFONO VERO che solo il
founder può fare (accordatore, ritratto di una campana, risonanze di
una bottiglia — il pannello di automazione blocca la cattura).

## 2 · Il principio della ristrutturazione

**Da una pagina-magazzino a una CASA con le stanze.** Ogni stanza:

- UN indirizzo suo (link condivisibile, SEO sua);
- UNA domanda a cui risponde, scritta in testa in linguaggio umano;
- il blocco «**Perché ti interessa**» (2-3 righe per il neofita) e
  «**Cosa puoi fare qui**» (3 azioni concrete) PRIMA degli strumenti;
- gli strumenti che le servono, e solo quelli;
- le didascalie esistenti (il come) restano al loro posto.

La mappa:

| URL | Stanza | La domanda a cui risponde |
|---|---|---|
| `/sound/lab` | **La Sala** (hub) | «Cos'è questo posto e da dove parto?» |
| `/sound/lab/banco` | **Il Banco** | «Com'è fatto un suono?» — Generatore, Voce B, le tre letture |
| `/sound/lab/orecchio` | **L'Orecchio** | «Che nota è? Che suono fa il mondo?» — mic, accordatore, letture |
| `/sound/lab/ritratto` | **Il Ritratto** | «Di cosa è fatto il suono del MIO oggetto?» — cattura, tabella, fonderia A/B |
| `/sound/lab/meraviglie` | **Le Meraviglie** | «Cosa sa fare davvero il suono (senza trucchi)?» — i 13 fenomeni |
| `/sound/lab/risonanze` | **Le Risonanze** | «A quale frequenza canta il mio oggetto?» — cercatore, quaderno, WAV (cimatica) |

I **Percorsi** vivono nella Sala (sono la porta del neofita) e i loro
passi portano alle stanze giuste con link veri tra pagine.

## 3 · Le onde

### LU1 — La mappa: rotte, shell, Sala *(1,5 giornate)*
- Le sei rotte in App.js (lazy, stesso chunk lab); la shell SEO
  impara OGNI sotto-percorso (`_meta_sound`: title/description/
  canonical per stanza — la trappola del 22/8 è in memoria) e il
  corpo per i crawler si aggiorna; sitemap con le stanze; la voce
  «Lab» di StanzeSound continua a portare alla Sala.
- **La Sala**: il racconto in tre righe («la biblioteca spiega il
  suono, qui il suono si tocca»), poi le stanze come CARTE — nome,
  la domanda a cui rispondono, cosa ci farai (3 voci) — poi i
  Percorsi in evidenza con il «Da dove parto?» per profili:
  *curioso* → Misura la tua bottiglia; *musicista* → l'accordatore;
  *professionista del suono* → il ritratto della tua campana.
- Redirect onesti: le vecchie ancore `#lab-sezione-*` della pagina
  unica muoiono con la pagina unica — chi arriva con un vecchio link
  atterra sulla Sala.

### LU2 — Le Letture come blocco riusabile *(1 giornata)*
- Oscilloscopio + Spettro + Spettrogramma + il comando Congela
  diventano UN componente (`LettureBanco`) montabile per stanza —
  oggi sono figli sciolti della pagina unica. Il contratto non
  cambia: ricevono `ottieniAnalisi` (e `ottieniXY` dove ha senso).
- Ogni stanza monta ciò che le serve: il Banco tutte e tre; Orecchio
  tutte e tre (guardano il mic); Ritratto nessuna (ha la sua
  tabella); Meraviglie spettro+spettrogramma (le prove di Tartini e
  Shepard); Risonanze la sua curva.
- Il ciclo di vita del motore per-pagina si collauda: entrare in una
  stanza, suonare, uscire, entrare in un'altra — mai due contesti
  vivi, mai suono orfano (spegni() allo smontaggio c'è già: si
  verifica che regga il giro).

### LU3 — Le stanze, una a una *(1,5 giornate)*
- Ogni stanza nasce con la sua TESTATA DIDATTICA, scritta per un
  neofita assoluto. Il tono, con un esempio completo (il Banco):
  - *la domanda*: «Com'è fatto un suono?»
  - *perché ti interessa*: «Ogni suono che senti — una voce, una
    campana, il mare — è fatto di onde. Qui ne generi una TU, e la
    guardi mentre suona: è il modo più veloce per capire cosa
    significano parole come frequenza, volume, timbro.»
  - *cosa puoi fare qui*: «Genera un tono e guardalo muoversi ·
    Accendi due voci e senti l'interferenza · Passa in XY e guarda
    la geometria di un intervallo».
- La Sorgente B si sposta DENTRO il Banco (era già lì
  concettualmente); il passo fine resta sul Generatore; la safety
  line resta su ogni stanza che suona.

### LU4 — La lingua del neofita e il ponte con Impara *(1 giornata)*
- Revisione di TUTTE le etichette e didascalie con una prova
  dichiarata: *ogni frase deve reggere davanti a chi non ha mai
  sentito la parola «frequenza»*. Il gergo che resta (Hz, dB,
  parziale, T60) diventa cliccabile: un **glossario in
  `/sound/impara`** (che già esiste ed è «le fondamenta») con ancore
  per termine — il Lab linka il punto giusto, non la pagina intera.
  Niente nomi di algoritmi nelle UI (Goertzel, FFT restano nei
  commenti del codice).
- Le didascalie si sdoppiano dove serve: prima riga = a cosa serve
  (per tutti), poi il come (per chi vuole).

### LU5 — I Percorsi tra le stanze *(½ giornata)*
- I tre percorsi diventano cross-pagina: ogni passo porta alla
  stanza giusta col link vero; il passo «attivo» si può riprendere
  (il percorso ricorda dove sei — sessionStorage, non un account).
- Il «Da dove parto?» della Sala è la loro vetrina.

### LU6 — Consolidamento: guardie, mobile, collaudo *(1 giornata)*
- **Migrazione delle guardie**: molte fotografano «tutto in
  SoundLabPage» (l'ordine del banco, i 4 consumatori dell'analisi,
  le ancore) — si evolvono stanza per stanza, con la storia nel
  docstring come da casa.
- **Mobile stanza per stanza**: i fogli alla maniera di VM1 dove i
  comandi affollano; la regola dei 767px è in memoria.
- **Il collaudo del racconto** (LB8, ora fattibile davvero): una
  persona che non ha mai visto il Lab attraversa Sala → una stanza
  → un percorso senza perdersi. Se si perde, è un difetto nostro.
- Peso: le stanze restano nello stesso chunk lazy del Lab (niente
  chunk per stanza: è un'app piccola, la mappa non deve costare).

## 4 · Cosa NON si tocca

Il motore (React-free, ponte, analisi ospite, phase-lock), la
matematica (accordatore, ritrattista, fonderia, cimatica), i 13
fenomeni, le 91 guardie di sostanza. Questo ciclo sposta MURI, non
fondamenta.

## 5 · Ordine e totale

LU1 → LU2 → LU3 → LU4 → LU5 → LU6, ~6,5 giornate. Ogni onda lascia
il Lab funzionante (la pagina unica muore solo quando le stanze sono
tutte in piedi, dentro LU3).

---

*In attesa del «procedi» — si parte da LU1.*
