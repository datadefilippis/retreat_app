# Aurya Sound / Esplora: piano di refinement (lotto «ES»)

8/10/2026, sera. Richiesta del founder: «l'intero design di esplorazione è
caotico e poco user-friendly; l'utente non deve usare sforzo cognitivo;
tutto più immediato, semplice, moderno, stiloso, navigabile, utile».
La casa delle meditazioni è il riferimento appena fatto (lotto MR).

## 0. Diagnosi (dal codice e dallo schermo, 375 px e desktop)

**/sound/esplora non è una pagina: è una vista del compositore.** La
rotta `/sound/*` apre `FrequenzePage` (2.900 righe, l'atelier Crea) con
`view = esplora | impara | crea | tracce`. Il pubblico naviga dentro lo
strumento dell'autore. Da qui nasce il caos:

| Cosa si vede | Perché è un problema |
|---|---|
| **Due navigazioni** una sotto l'altra: la passerella (Meditazioni · Il suono · Crea) e le «stanze» (Esplora · Lab · Impara · Crea · Le mie tracce) | due menu con voci doppie; su telefono «Le mie tracce» sborda a destra |
| «Il suono» in passerella porta alla landing chiara | si esce dal posto in cui si è |
| **Tre avvisi** in testa: la pastiglia «Controindicazioni», il riquadro «Cuffie e volume…», «Cosa devo sapere» | l'avviso vero sta già nel sipario prima del primo suono: qui è rumore |
| Il selettore «Frequenze / Suoni» | «Suoni» sono le **basi del compositore**: non riguardano chi esplora |
| Un paragrafo introduttivo, poi 4 pastiglie di famiglia, la legenda A/B/C con «Come leggere questa biblioteca», l'intro di famiglia, la chiave dei metodi | sei blocchi di testo prima della prima scheda |
| 36 schede lunghe, ognuna con «Approfondisci», «Ascolta», «+ Sessione»; più suoni insieme «si combinano», con una barra «N in riproduzione» | «+ Sessione» è dell'autore; «combinare» è un gesto da atelier; la pagina è 3.600 px su telefono |
| La «Fondamenta» (Impara) è una pagina unica di 7.500 px | si legge male, non si ritrova il punto |
| In fondo il «TriggerStudio» (vendita di Crea Studio) | un funnel per professionisti in mezzo al pubblico |

**Cosa è già buono e si tiene**: la **pagina-scheda** `/sound/esplora/{slug}`
(titolo, Hz, uso, grado di evidenza, sei capitoli brevi, breadcrumb,
sorelle, ponte al Lab); il contenuto delle 36 schede (`content/biblioteca.js`,
una fonte per pagina e SEO); le cinque stanze del Lab; il motore delle
anteprime (`engine/synth.startPreview`).

## 1. Il principio

**Il suono ha tre porte e una sola voce.** Dalla casa delle meditazioni si
entra ne «Il suono» (già oggi un foglio: Esplora le frequenze · Le
fondamenta · Il Lab). Dentro, una sola navigazione: la passerella sopra e
un **selettore a tre** (Frequenze · Fondamenta · Lab) che resta lo stesso
nelle tre porte. Niente stanze, niente «Suoni», niente «Le mie tracce»:
chi compone ha «Crea» in passerella e lì trova il suo atelier intero.

Tutto ciò che è dell'autore (Sessione, basi, combinazioni, upload della
regia) esce dal pubblico e resta in Crea, intatto.

## 2. I lotti

### ES0 La porta e la mappa (½ giornata) — fatto il primo passo
- **«Il suono» non porta mai fuori**: il foglio con le tre porte si apre da
  ogni pagina scura (casa, esplora, fondamenta, Lab, scheda), con la porta
  corrente segnata. **Fatto ora** (vedi §5).
- `/sound/esplora`, `/sound/impara` diventano **pagine proprie**
  (`esplora/BibliotecaPage.jsx`, `esplora/FondamentaPage.jsx`) con il
  selettore a tre; le viste dentro `FrequenzePage` restano per Crea
  (`/sound/crea`, `/sound/tracce`) e per i 17 file di test che le leggono.
  Flag `SOUND_ESPLORA_NUOVA`.
- Le stanze (`StanzeSound`) spariscono dal pubblico; «Le mie tracce» e
  «Crea» vivono dentro Crea.

### ES1 La biblioteca come catalogo visivo (1,5 giorni)
- **Testata corta**: «Le frequenze», una riga («36 schede: cosa sono, a cosa
  servono, come si ascoltano»), il selettore.
- **Le quattro famiglie come card grandi** col loro tono (Bande cerebrali ·
  Altre frequenze · Ritmi del corpo · Metodi), con una riga di spiegazione
  (l'attuale `CAT_INTRO`, ridotta a una frase) e il numero di schede.
- Dentro una famiglia: **griglia di schede compatte** (nome, Hz, uso in una
  riga, il grado come puntino A/B/C con tooltip), stesse card della casa
  (raggio 20, ombra, ▶ al tocco). Niente testo lungo nella card: il testo
  è nella pagina-scheda.
- **Ascolto: una alla volta**, nella **stessa barra in basso della casa**
  (`LettoreBarra`): tocchi ▶ e senti 30–60 s della frequenza; la barra dice
  cosa suona, quanto, e ha «Apri la scheda». Il «combinare» resta in Crea.
- «Approfondisci» = il titolo della card apre la pagina-scheda.
- Ricerca e filtri come nella casa: un campo (nome, Hz, uso) e le pastiglie
  delle famiglie; su telefono nel foglio dalla barra.
- `+ Sessione` solo per chi compone, come oggi, ma **dentro la scheda**,
  non su ogni card.

### ES2 Le informazioni al posto giusto (½ giornata)
- Via dalla testata la pastiglia «Controindicazioni» e il riquadro cuffie:
  il **sipario** prima del primo suono resta (una volta ogni 90 giorni) e
  una riga discreta a piè di pagina rimanda a «Cosa devo sapere».
- La legenda A/B/C e «Come leggere questa biblioteca» in **un foglio ⓘ**
  aperto dal grado sulla card o dall'icona in testata.
- La chiave dei metodi (binaurale, monaurale…) diventa la riga di
  spiegazione della famiglia «Metodi», non un pannello.
- Il «TriggerStudio» esce dalle pagine pubbliche (resta su `/sound/studio`
  e nella landing).

### ES3 La pagina-scheda (½ giornata)
- In testa **▶ Ascolta** (nella barra), «Prova nel Lab» quando la stanza
  esiste, e **← Famiglia** per tornare alla griglia dov'eri (`?da=`, come
  i Percorsi).
- Sorelle come card compatte scorrevoli; «precedente / successiva» nella
  famiglia.
- «Le meditazioni che la usano»: le meditazioni pubblicate con questa
  frequenza nella ricetta (dato già nelle tracce: `score.layers`), con il
  cuore e il ▶ della casa. È il ponte che oggi manca tra lo studio e
  l'ascolto.

### ES4 Le fondamenta a capitoli (1 giornata)
- La guida unica di 7.500 px diventa **sei capitoli** con un indice in
  testa (quello che c'è, `gd-path`, ma come navigazione vera), un capitolo
  per schermata con «capitolo successivo», ancore condivisibili
  (`/sound/impara#metodi`), e il segno del punto in cui si è.
- Il **glossario** come lista cercabile (A–Z, un campo), ogni voce con il
  link alla scheda o al capitolo.
- Stesso selettore a tre in testa; nessun altro menu.

### ES5 Il Lab allineato (½ giornata)
- La sala con le cinque stanze come card della casa (tono, una riga, ▶
  «Entra»), «Da dove parto?» come tre pastiglie; dentro le stanze solo il
  selettore a tre sopra e «← Il Lab» dentro. Nessun cambio al motore delle
  stanze.

### ES6 Il linguaggio comune (trasversale, dentro ES1–ES5)
- Un foglio di stile `esplora/esplora.css` che **riusa i gettoni della
  casa** (`casa.css`: card, pastiglie, barra, foglio, scheletri): due mondi
  scuri, una grammatica.
- Tipografia: titoli 28/22/17, corpo 15, etichette mono 11; contrasto AA.
- Scheletri in caricamento; `prefers-reduced-motion`.
- Mobile first: 375 px senza scroll orizzontale, bersagli ≥ 44 px, il
  selettore a tre sempre a portata (in testa, sticky).

## 3. Cosa NON si tocca
Il motore (`engine/*`), Crea e le sue viste in `FrequenzePage`, il Lab
dentro le stanze, i testi delle 36 schede, la shell SEO delle schede e
della biblioteca (`seo_shell._meta_sound`, `data/biblioteca_seo.json`), i
17 file di test che leggono `FrequenzePage` e `SoundHomePage`.

## 4. Ordine, tempi, cancelli

| Lotto | Giorni | Flag |
|---|---|---|
| ES0 porta e mappa | ½ | `SOUND_ESPLORA_NUOVA` |
| ES1 biblioteca visiva | 1,5 | idem |
| ES2 informazioni al posto giusto | ½ | idem |
| ES3 pagina-scheda | ½ | nessuno (è già una pagina) |
| ES4 fondamenta a capitoli | 1 | idem |
| ES5 Lab allineato | ½ | nessuno (solo stile) |

Totale **≈ 4,5 giorni**, una guardia per lotto (`tests/test_esplora_es*.py`),
prova a 375 px e desktop, build e suite puliti, commit per lotto, nessun
deploy senza «go».

## 5. Fatto subito (8/10 sera)
- **«Il suono» non porta più fuori da nessuna pagina scura**: il foglio
  con le tre porte si apre anche da /sound/esplora, /sound/impara,
  /sound/lab e dalle schede, con la porta corrente evidenziata. La
  passerella segna «Il suono» come pagina corrente in tutte e tre.

## 6. Decisioni del founder (8/10 sera)
1. Un suono alla volta per il pubblico: **sì** (il «combinare» resta in Crea).
2. **Famiglie prima, schede dopo.**
3. Fondamenta a capitoli: **sì**.
4. «Meditazioni che usano questa frequenza»: **no**.

## 7. Stato: LOTTO ES FATTO in locale (8/10 sera)
- **ES0**: `esplora/BibliotecaPage.jsx` (/sound/esplora) e `esplora/FondamentaPage.jsx` (/sound/impara, /sound/impara/glossario) dietro `SOUND_ESPLORA_NUOVA`; il compositore (`FrequenzePage`, rotta /sound/*) resta intatto per Crea e per i test. `esplora/SelettoreTre.jsx` (Frequenze · Fondamenta · Lab) in ogni pagina del suono, anche nella scheda e nel Lab (`LabSala` lo mostra al posto delle stanze, la stringa `StanzeSound` resta per i pin).
- **ES1/ES2**: quattro famiglie come card col tono (`content/biblioteca_testi.js`: FAMIGLIE, CAT_INTRO, GRADI, HOWTO_BODY, METODI_CHIAVE, usati anche dal compositore), griglia di schede compatte, ▶ una alla volta nella `BarraAnteprima` (hook `esplora/anteprima.js` su `startCardLive`, sipario, 60 s), cerca su tutte le 36, foglio ⓘ per legenda e «come leggere», chiave dei metodi solo in Metodi; via avvisi doppi, basi, stanze, «Le mie tracce», «+ Sessione», TriggerStudio dal pubblico.
- **ES3**: la scheda con selettore, briciole «Le frequenze › Famiglia › Scheda» (`?famiglia=`), ▶ che suona qui, «← Tutte le schede di …», sorelle che portano la famiglia.
- **ES4**: fondamenta a capitoli (indice sticky, capitolo corrente via IntersectionObserver, ancore `#gd-…`, «capitolo successivo»), glossario; `GuidaView` intatta (l'indice suo è nascosto via CSS).
- **ES5/ES6**: Lab col selettore; `esplora/esplora.css` sulla grammatica della casa.
- Verificato a 375 px e desktop: famiglie → schede → ▶ (una sola suona, la barra cambia scheda) → scheda → «←»; capitoli; Lab. Guardie: `tests/test_esplora_es.py`.
- Rimandi: la ricerca del glossario (oggi la lista intera); le stanze del Lab interne mostrano ancora `StanzeSound` (`lab/Stanza.jsx`, pin): si allineano al selettore quando si potano le stanze.

## 8. Le meditazioni prima di tutto (8/10 sera, dopo il lotto)
Richiesta del founder: dal foglio «Il suono» non si esce verso la landing (al massimo un link alle meditazioni); nella landing il suono era più in evidenza delle meditazioni, che sono il valore principale.
- Foglio «Il suono»: via «La pagina di Aurya Sound →», in fondo solo «Le meditazioni →» (nascosto nella casa).
- Landing /sound: la **testata resta quella di prima** (decisione del founder: «Il suono può diventare uno strumento», «Ascolta una meditazione, 90 secondi» → ancora alla sezione, «Esplora Aurya Sound →»; titolo e meta SEO invariati); la sezione Meditazioni (anteprima 90 s, «Le N Meditazioni», rimando alla casa) sale **subito dopo l'apertura** con l'occhiello «Il cuore di Aurya Sound»; fenomeni e tre porte diventano «Dietro ogni meditazione»; Crea in fondo.
- Pin aggiornati: `test_meditazioni_mr7`, `test_sound_sistema` (ordine meditazioni < fenomeni < porte < Crea), `test_frequenze_movimento` (intro famiglie in `biblioteca_testi.js`).
