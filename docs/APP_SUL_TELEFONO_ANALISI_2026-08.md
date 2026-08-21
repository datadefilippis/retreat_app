# «Scarica l'app» — analisi di fattibilità (21 agosto 2026)

Richiesta del founder: un pulsante — nel gestionale e sul sito — che
con un clic installi il gestionale Aurya sul telefono. Non è un'app
nativa: si tratta di aggiungere la pagina web alla schermata Home.
Domanda: si può fare in automatico su tutti i telefoni e i browser?

---

## 1. La risposta breve

**No, non su tutti — e la differenza non dipende da noi.**

| dove | un clic? | cosa possiamo fare davvero |
|---|---|---|
| **Android** — Chrome, Edge, Samsung, Opera | **sì** | intercettiamo `beforeinstallprompt` e apriamo il dialogo vero di sistema |
| **Desktop** — Chrome, Edge | **sì** | idem, l'app finisce tra le applicazioni |
| **iPhone/iPad** — Safari | **no** | Apple non espone nessuna API: l'utente deve fare Condividi → «Aggiungi a Home». Il massimo è una guida illustrata in due passaggi |
| **iPhone** — Chrome, Firefox | no | sono Safari sotto il vestito; da iOS 16.4 possono aggiungere a Home, ma sempre a mano |
| **browser dentro le app** (Instagram, Facebook) | **no** | non possono installare: serve prima «apri in Safari/Chrome» |

Quindi il pulsante si può fare, e su Android è davvero **un clic**. Su
iPhone diventa **un clic che apre le istruzioni giuste**: non è un
ripiego nostro, è l'unica strada che il sistema consente. Chi promette
l'installazione automatica su iPhone, semplicemente, non la sta
facendo.

## 2. Cosa manca oggi (nulla è installabile, in questo momento)

Ho controllato il progetto: **non siamo installabili da nessuna
parte**. Mancano i tre requisiti di base.

1. **Non esiste `manifest.json`.** Il file che CRA genera è stato tolto
   (in `index.html` restano solo i commenti che lo citano). Senza
   manifesto nessun browser propone l'installazione.
2. **Non esiste un service worker.** Chrome non fa comparire il
   dialogo se non c'è un service worker che gestisca `fetch`. È il
   requisito più delicato (vedi §5: è anche il modo classico di
   rompersi un sito).
3. **L'icona da 512 non è da 512.** `logo-aurya-512.png` misura
   **511×512**: se il manifesto dichiara `sizes: "512x512"` il browser
   scarta l'icona e l'installabilità salta. Va rigenerata quadrata.

C'è invece già: HTTPS, `apple-touch-icon` (iOS userà quello) e le
icone 128/729. Il `theme-color` è `#000000`, cioè il default di
Create React App: diventerebbe il colore della barra di sistema
nell'app installata, e va messo sul verde di marca.

## 3. La decisione di prodotto: quante app?

Il manifesto che conta è **quello della pagina da cui si installa**, e
questo apre una scelta.

- **Un'app sola, il gestionale** (raccomandata). `start_url:
  /dashboard`, nome «Aurya Gestionale». Il pulsante sul sito pubblico
  vive dove stanno i professionisti — landing `/entra-nella-rete` e
  `/accedi` — non nelle pagine per chi cerca un ritiro: un visitatore
  non installa un sito che visiterà due volte, e due icone «Aurya»
  sullo stesso telefono confondono.
- **Due app** (gestionale + sito): tecnicamente possibile con due
  manifesti diversi su pagine diverse. Lo sconsiglio ora: raddoppia le
  icone, i nomi e la manutenzione per un pubblico che non lo chiede.

## 4. Come funziona il pulsante, in pratica

Un solo componente che si comporta in tre modi, perché tre sono le
situazioni vere:

1. **già installata** → il pulsante non compare (`display-mode:
   standalone` lo dice);
2. **installabile** (Android/desktop) → «Installa l'app» e il dialogo
   di sistema al clic;
3. **iPhone** → «Aggiungi alla Home» che apre un foglio con due
   passaggi illustrati: l'icona Condividi (quella con la freccia in
   su) e la voce «Aggiungi a Home». Con l'avvertenza per chi arriva da
   Instagram: «apri prima in Safari».

Detto in modo onesto nel testo: *non è un'app da scaricare da uno
store, è Aurya che si apre a tutto schermo dalla tua Home.* Chi si
aspetta l'App Store non deve sentirsi ingannato.

## 5. I rischi veri, prima di dire sì

**Il service worker è la parte pericolosa.** Un service worker scritto
male serve per settimane una versione vecchia del sito a chi l'ha già
visitato — e non c'è modo di forzarlo da remoto se non con altro
codice. Se lo facciamo, deve essere **minimo e network-first**: passa
tutto alla rete, non tiene cache di HTML e JS, esiste solo per
soddisfare il requisito e per rispondere «offline» con una pagina di
cortesia. Niente strategie furbe.

**iOS a schermo intero perde il browser.** In `standalone` non ci sono
i pulsanti avanti/indietro: la navigazione deve bastare a se stessa.
Il gestionale ha il suo menu, quindi regge — ma due flussi vanno
provati sul telefono vero prima del rilascio: **Stripe Connect**
(l'onboarding esce dall'app e su iOS può tornare senza sessione) e i
**link di verifica email**, che aprono Safari e non l'app installata.

**La sessione.** Un'app installata è un contesto suo: chi era già
loggato nel browser si ritrova sloggato al primo avvio. Non è un bug,
ma va detto — o il primo contatto con «l'app» è una schermata di
accesso inattesa.

## 6. Cosa serve, in ordine

| # | cosa | costo |
|---|---|---|
| 1 | icona 512×512 vera + una versione `maskable` (Android altrimenti la ritaglia dentro un cerchio bianco) | ½ h |
| 2 | `manifest.json` del gestionale + `theme-color` di marca | ½ h |
| 3 | service worker **minimo** network-first + pagina offline | 2 h |
| 4 | componente pulsante a tre stati (installata / installabile / iOS con guida) | 3 h |
| 5 | innesto: gestionale (Impostazioni o menu) + `/entra-nella-rete` e `/accedi` | 1 h |
| 6 | prova su iPhone e Android veri, incluso il ritorno da Stripe | 2 h |

Circa **un giorno e mezzo**, la metà del quale è verifica sui telefoni
— che qui non è un extra: è l'unico modo di sapere se funziona.

## 7. Il mio consiglio

**Farlo, con una promessa onesta.** Il valore per l'operatore è reale:
apre Aurya dalla Home come un'app, a tutto schermo, senza cercarla nel
browser. Ma il pulsante non deve dire «Scarica l'app»: su iPhone
sarebbe una promessa che il sistema non ci lascia mantenere, e la
delusione arriverebbe al primo tocco.

Direi **«Aurya sul tuo telefono»**, e sotto, piccolo: *si aggiunge
alla Home in un tocco — su iPhone in due*. È vero ovunque, e non
prepara nessuna sorpresa.


---

## 8. Ci sono alternative? (domanda del founder, 21/8)

Premessa che vale per tutte: **nessun sistema operativo permette a un
sito di mettere un'icona sul telefono di qualcuno senza il consenso di
quel qualcuno.** Non è un limite da aggirare: è la regola che impedisce
a qualunque pagina di riempirti la Home. «Un clic» significa sempre
*un clic dell'utente su un dialogo di sistema*, mai un clic nostro.

Dentro questo confine, le strade sono tre.

### A — App vera negli store (App Store / Play Store)
È **l'unica** che dà l'icona su iPhone con un tocco su «Installa», e
in più abilita notifiche e presenza nei negozi.
- **Come**: non serve riscrivere Aurya. Su Android una **TWA** (Trusted
  Web Activity) impacchetta la web app così com'è: la stessa Aurya,
  dentro un guscio, pubblicata su Play. Su iOS un wrapper equivalente.
- **Costi veri**: 25 € una tantum per Google, **99 €/anno** per Apple,
  più la revisione — e Apple rifiuta i gusci che sono solo un sito
  (linea guida 4.2). Il gestionale ha funzionalità sue, quindi
  passerebbe, ma va argomentato. Poi: ogni cambiamento importante
  richiede una nuova pubblicazione e una nuova revisione.
- **Quando ha senso**: quando gli operatori sono abbastanza da
  giustificarlo. Al 20/8 in produzione sono **sette**. Una scheda
  sull'App Store per sette persone costa più attenzione di quanta ne
  restituisca.

### B — Profilo di configurazione iOS (`.mobileconfig`)
Tecnicamente mette un'icona sulla Home di un iPhone. **Da non fare**:
l'utente deve scaricare un profilo, aprirlo nelle Impostazioni,
concedere l'installazione e superare l'avviso «Profilo non
verificato». È lo stesso meccanismo delle configurazioni aziendali —
per un utente normale è indistinguibile da un tentativo di truffa, e
ci farebbe sembrare quello che non siamo.

### C — La PWA (§1-§7)
Un clic vero su Android e desktop, due passaggi guidati su iPhone.
Zero costi ricorrenti, nessuna revisione, aggiornamenti immediati.

### La combinazione che consiglierei, se e quando
**C adesso, C+TWA quando la rete cresce.** La PWA copre subito tutti;
la TWA su Play costa 25 € una tantum e dà una presenza reale sul
negozio Android senza cambiare il codice. L'App Store lo affronterei
solo con numeri che lo giustificano, o quando servissero notifiche su
iPhone — che però, dettaglio utile, **funzionano già oggi sulle PWA
installate** da iOS 16.4 in poi.
