# Gli URL che rispondono 200 — analisi profonda e raccomandazione

25 agosto 2026. Richiesta: *«voglio un'analisi delle URL che rispondono
200; se impatta SEO lo facciamo ora che abbiamo ancora pochi operatori
e non ci pensiamo più»*.

Ho fatto il censimento. La conclusione è controintuitiva e la scrivo
subito: **il soft-404 esiste ma oggi non ci sta facendo danno — e
cercandolo ho trovato due difetti veri, che ho già chiuso.**

---

## 1. Il censimento

### Cosa risponde correttamente 404

Tutti i percorsi che passano dal renderer server-side:

| URL provato | Risposta |
|---|---|
| `/blog/non-esiste` | **404** ✓ |
| `/o/non-esiste` | **404** ✓ |
| `/e/x/y` | **404** ✓ |
| `/blog/categoria/inventata` | **404** ✓ |
| `/.env` | **404** ✓ |

### Cosa risponde 200 senza essere contenuto

Tutto ciò che **non** passa dal renderer:

| URL provato | Risposta |
|---|---|
| `/pagina-inventata` | 200, corpo vuoto, nessun noindex |
| `/xyz123` | 200 |
| `/a/b/c` | 200 |
| `/wp-admin` | 200 |
| `/admin-login` | 200 |

Il meccanismo: nginx manda al renderer **solo un elenco di prefissi
noti**; tutto il resto va al contenitore del frontend, che per
qualunque percorso serve `index.html` con 200 (è il comportamento
standard di una single-page app). La SPA poi riporta l'utente a casa.

**Numeri del sito**: 131 rotte dichiarate, **79 primi segmenti
distinti**. Il renderer ne conosce una trentina.

---

## 2. L'impatto reale, misurato

Qui sta il punto che cambia la decisione. Ho controllato **cosa è
finito davvero negli indici** (via l'indice di Bing, che ci ha già
scansionati): compaiono la home, `/blog`, cinque articoli e `/login`.
**Nessun URL inventato.** Nemmeno uno.

È logico: un motore non inventa indirizzi, li segue. E per arrivare su
`/pagina-inventata` servirebbe che qualcuno la linkasse — dall'esterno,
o da un nostro link rotto. Ho verificato anche questo: i link interni
di home e blog puntano tutti a pagine reali e dichiarate in sitemap
(77 URL).

**Quindi il soft-404 è un rischio latente, non un danno in corso.**
Diventerebbe reale se: un sito esterno ci linkasse un indirizzo
sbagliato, un aggregatore mangiasse un URL, o noi pubblicassimo un
link rotto. Casi possibili, non frequenti.

Cosa costa oggi, concretamente: qualche voce «Soft 404» nel rapporto
Pagine di Search Console (che spaventa più di quanto pesi), e un po' di
crawl budget sprecato se qualcuno ci arriva.

---

## 3. Il difetto vero che il censimento ha trovato

Cercando i soft-404 ho trovato di peggio, ed era esattamente il tipo di
cosa che si scopre solo elencando gli URL uno per uno.

**`/meditazioni` e `/costi` erano pagine mute.** Non URL inventati:
pagine vere. `/meditazioni` è persino **nel menu del sito** e linkata
dalla landing di Sound; `/costi` è la pagina che risponde alla domanda
che ogni professionista fa per prima. Tutte e due servivano ai crawler
**46 caratteri** e il titolo marketplace di luglio — «Aurya | Ritiri ed
esperienze olistiche» — perché non erano nell'elenco dei prefissi noti.

Il difetto della home, in piccolo, su due pagine che nessuno aveva
pensato di controllare, e che per una persona funzionano benissimo.

**Già chiuso** (in produzione): meta oneste, corpo server-side, dentro
la sitemap. Da 46 a ~285 caratteri.

E ho messo sotto guardia **la regola che mancava**: una pagina pubblica
o passa dal renderer, o è muta; chi ne aggiunge una deve toccare tre
posti (renderer, nginx, sitemap) e il test li verifica tutti e tre.
La prossima volta il buco si vede subito, non fra un mese in GSC.

---

## 4. Il soft-404: le tre strade, con i rischi veri

### Strada A — Enumerare tutte le rotte e mandare il resto al 404

Si elencano i 79 segmenti noti in nginx; qualunque altro percorso va al
renderer, che risponde 404.

*Pro*: soft-404 risolto alla radice, per sempre.
*Contro*: **se dimentico un segmento, quella pagina dell'app risponde
404 quando la si apre da un link diretto o da un refresh** — non in
navigazione interna, quindi il bug è invisibile a chi sviluppa e
visibile a chi lavora. Con 79 segmenti e 14 sotto-rotte solo per
`/account`, la probabilità di dimenticarne uno non è teorica. E i
segmenti nuovi che aggiungeremo dovranno ricordarsi di questa lista.

### Strada B — `noindex` su tutto ciò che non passa dal renderer

Una riga in nginx: quello che serve il frontend esce con
`X-Robots-Tag: noindex`.

*Pro*: rischio quasi nullo, risolve l'indicizzazione della spazzatura.
*Contro*: **è esattamente la trappola in cui siamo appena caduti.**
Oggi tutto ciò che non passa dal renderer è o una rotta d'app o
spazzatura — ma lo era anche ieri, e ieri lì dentro c'erano
`/meditazioni` e `/costi`. Con questa regola, il giorno che qualcuno
aggiunge una pagina pubblica e dimentica di dichiararla, non sarebbe
solo muta: sarebbe **attivamente esclusa** dagli indici, in silenzio.
Trasformerebbe una dimenticanza recuperabile in un danno silenzioso.

### Strada C — Lasciare com'è e sorvegliare

*Pro*: rischio zero.
*Contro*: qualche «Soft 404» in GSC quando capiterà.

---

## 5. La mia raccomandazione

**Strada A, ma non stasera — e non a mano.**

Il tuo istinto è giusto: si fa ora che gli operatori sono quattro, non
quando saranno duecento. Ma il modo in cui si fa cambia tutto il
rischio: **l'elenco delle rotte non va scritto a mano, va generato dal
codice** — `App.js` le dichiara tutte, e un test può confrontare la
lista generata con quella in nginx e fallire quando divergono. Così non
si tratta di ricordarsi: se qualcuno aggiunge una rotta e non aggiorna
l'elenco, la suite diventa rossa prima del deploy.

Con quella rete, la Strada A diventa sicura quanto la C.

Il lavoro è di mezza giornata: estrarre le rotte, generare l'elenco,
scrivere la guardia di parità, provare **tutte e 79** le rotte una per
una in produzione dopo il deploy. La parte lunga è l'ultima, ed è
quella che non si salta.

**Nel frattempo non stiamo perdendo niente**: nessun URL inventato è
negli indici, e i due difetti che costavano davvero traffico —
`/meditazioni` e `/costi` mute — sono già chiusi.

---

## 6. Se vuoi procedere

Dimmi quando, e lo faccio in questo ordine:

1. Estrarre le 131 rotte da `App.js` e derivare i segmenti;
2. generare l'elenco nginx dal codice, con la guardia di parità che
   diventa rossa se qualcuno aggiunge una rotta e dimentica l'elenco;
3. far rispondere 404 a ciò che resta fuori;
4. **provare tutte e 79 le rotte in produzione dopo il deploy** — è il
   passo che rende la cosa sicura, ed è anche l'unico che non si può
   accelerare;
5. rimettere `/pagina-inventata` alla prova, e chiudere.
