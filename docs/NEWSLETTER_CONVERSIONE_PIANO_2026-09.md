# IL CERCHIO — da «Lettera» a appartenenza (piano strategico, 3/9/2026)

*Founder: «la landing della Lettera deve convertire meglio... nessuno si
è iscritto da lì... era più coinvolgente quando dicevamo che iscrivendosi
ricevevano info sui prossimi ritiri ed esperienze... ragionare come
marketing manager senza perdere umanità. Obiettivo: convertire,
raccogliere lead e iscritti.» Prima l'analisi, poi il piano.*

## 0 · I fatti (misurati, 3/9/2026)

**La landing /newsletter oggi**
- 256 parole, 4 sezioni, **il form è a 5.900 px**: quarto schermo. Il
  bottone dell'hero («Ricevi la Lettera») scrolla fin laggiù.
- La proposta di valore è un'ANTI-promessa: «Una lettera, ogni tanto.
  Viviamo in un mondo pieno di notifiche. Noi preferiamo scrivere
  quando abbiamo davvero qualcosa». Dice cosa NON faremo. Elegante,
  ma non dà un motivo per lasciare l'email oggi.
- Il vantaggio concreto che esiste già — meditazioni riservate,
  anteprima ritiri — **non compare mai** nella pagina. L'opt-in
  «Avvisami quando Aurya propone esperienze e ritiri» è una casella
  in fondo al form, spenta.

**Il funnel in produzione (9 iscritti totali)**
| Stato | Fonte | N |
|---|---|---|
| confermati | cancello meditazione (frequenze:…) | 2 |
| confermati | landing /newsletter | 1 |
| in attesa di conferma | lead pre-lancio | 4 |
| in attesa | home | 1 |
| in attesa | gestionale | 1 |

Due verità: (1) **chi si iscrive per sbloccare qualcosa conferma**
(2 su 2 dal cancello delle meditazioni); chi si iscrive «per la
lettera» spesso no; (2) **6 su 9 non hanno mai confermato**: il doppio
opt-in perde due terzi. L'email di conferma ha oggetto «Conferma la
tua iscrizione alla lettera di Aurya» e parla solo della lettera: non
dice cosa si sblocca confermando.

**Cosa sblocca davvero l'iscrizione (dal codice, non a memoria)**
- Email confermata (`aurya_nl_token`, stato `confirmed`) = chiave dei
  CONTENUTI: le meditazioni riservate del catalogo Sound
  (frequencies.py: 403 «locked» senza).
- Account Aurya (gratuito, email+password) = chiave della PERSISTENZA:
  salvare i quaderni del Lab (quadernoRemoto: `haAccount`) e ritrovare
  guide e meditazioni su ogni dispositivo. **Il Lab si salva con
  l'account, NON con la newsletter**: la landing può promettere il
  salvataggio solo come «passo dopo» (il ponte esiste già nella pagina
  di conferma).
- In prod oggi il catalogo riservato ha **1 traccia** (tracks_count 1).
  Localmente ne esistono 124 importate. Promettere «meditazioni
  riservate» al plurale con una traccia sola è la bugia più veloce da
  scoprire: **CN0 viene prima di tutto**.

**Il nome**: «La Lettera di Aurya» è il nome di un PRODOTTO EDITORIALE
(una email). Non nomina l'appartenenza né i vantaggi. Nel codice, la
prova dell'iscrizione si chiama già «cerchio» (lib/cerchio.js:
`prova()`, «sblocchi una volta, sblocchi tutto»): il nome giusto era
già lì.

## 1 · La strategia (marketing manager, tono umano)

**Da newsletter a appartenenza.** Non «ricevi una lettera» ma «entra
nel Cerchio»: chi lascia l'email entra in un gruppo che riceve le cose
PRIMA e ha accesso a cose che gli altri non hanno. La Lettera resta,
ma diventa una delle quattro cose che ricevi, non il titolo.

**La pila di valore (solo cose vere, nell'ordine in cui convertono)**
1. **Meditazioni riservate, gratis, subito** — appena confermi.
   (Richiede CN0: almeno 5 tracce pubblicate in prod.)
2. **Ritiri ed esperienze in anteprima** — nella tua zona e sui temi
   che scegli, prima che siano pieni. (Il meccanismo esiste: opt-in
   esperienze + città + interessi in `preferences`; oggi è nascosto.)
3. **La Lettera** — ogni due settimane, una pratica raccontata bene e
   una persona della rete.
4. **Un passo dopo, se vuoi**: l'account gratuito per salvare le tue
   sessioni del Lab e ritrovare tutto su ogni dispositivo.

**Il nome: «Il Cerchio di Aurya»** (proposta; alternative: «Dentro
Aurya», «Aurya Insieme»). Coerente col codice, con «ci si fida di
qualcuno», con l'idea di rete. Titolo di landing: **«Entra nel Cerchio
di Aurya.»** Sottotitolo: «Meditazioni riservate, ritiri in anteprima
e una lettera quando vale la pena. Gratis, e senza rumore.»

**Le tre regole di conversione**
- **Il form nel primo schermo** (email + il bottone), non a 5.900 px.
  Il resto della pagina serve a chi vuole capire di più, non a chi ha
  già deciso. Form ripetuto in fondo.
- **Una promessa concreta per riga, con la prova accanto**: «N
  meditazioni riservate» (numero vero dal catalogo), «il prossimo
  ritiro» (dalla directory, se c'è), «l'ultima Lettera» (link
  all'archivio se esiste).
- **Il doppio opt-in vende, non chiede**: oggetto «Un passo e sei nel
  Cerchio: conferma per sbloccare le meditazioni»; nel corpo, cosa si
  sblocca; nella pagina di conferma, la meditazione si apre SUBITO.

**Tono**: umano, diretto, mai «notifiche/rumore/spam» come prima
parola (è la grammatica del sospetto). Si parla di cosa ricevi, non di
cosa non faremo. Una frase per idea, niente aggettivi doppi.

## 2 · La landing rigenerata (struttura e copy proposto)

1. **Hero (con form)** — eyebrow «Il Cerchio di Aurya» · H1 «Entra nel
   Cerchio di Aurya.» · una riga «Meditazioni riservate, ritiri in
   anteprima e una lettera quando vale la pena. Gratis.» · **form**:
   email, [città, facoltativa], casella consenso (obbligatoria, come
   oggi), preferenza «Avvisami di ritiri ed esperienze nella mia zona»
   **accesa di default** (è una preferenza dentro lo stesso consenso,
   non un secondo consenso), bottone **«Entra nel Cerchio»** · sotto,
   micro-riga di fiducia: «Una conferma via email, poi sei dentro. Ti
   cancelli con un clic.»
2. **Cosa ricevi** — tre card: «Meditazioni riservate» (ascolta
   un'anteprima da 90 secondi qui, senza iscriverti: il pedaggio FN
   già esiste) · «Ritiri ed esperienze in anteprima» (la prossima
   data, se c'è) · «La Lettera, ogni due settimane». Niente conteggi.
3. **Per chi è** — 3 righe del founder (tenere il tono di oggi: «per
   chi preferisce capire prima di scegliere»).
4. **Chi scrive** — Davide e Valentina, foto, due righe, firma.
5. **Form ripetuto** + «Prima di salutarci» ridotto a una riga di
   promessa («Scriveremo solo quando vale il tuo tempo. Ti cancelli
   con un clic.»).
Target: ≤ 300 parole, form visibile senza scroll su mobile.

## 3 · Le onde

- **CN0 — Lo scaffale (founder, contenuto)** — *decisione founder 3/9:
  «parliamo di meditazioni riservate anche se solo 1 disponibile, a
  breve ne faccio altre... meno dettagli inutili»*. Quindi NON blocca e
  in pagina si dice solo **«meditazioni riservate»**: niente conteggi,
  niente «la prima è pronta», niente date. Lo scaffale cresce dietro.
- **CN1 — La landing** (mezza giornata): struttura sopra, LeadForm
  invariato nella meccanica (stesso endpoint, stesso doppio opt-in),
  esperienze accese di default sulla landing, numeri veri dal
  catalogo, GA `generate_lead` già presente (context «landing»).
- **CN2 — Il doppio opt-in che vende** (ore): oggetto e corpo
  dell'email di conferma; pagina di conferma con la meditazione
  aperta subito e il ponte all'account; **promemoria a 48 h** ai
  pending (un job, una sola volta, «ti manca un clic»): con 6
  pending su 9 è la leva più economica che abbiamo.
- **CN3 — Il ribrand sul sito** (mezza giornata): ~80 citazioni di
  «Lettera» in 20 file (landing, home, MeditazioniPage, CancelloLettera,
  InvitoSound, PublicFrequencyPage, SoundHomePage, LeadForm, Manifesto,
  Chi siamo, footer, AccountLoginPage, cerchio.js, i18n
  landings/prelaunch, seo_shell ×4, email di conferma). Regola: «Il
  Cerchio» è l'appartenenza, «la Lettera» resta il nome dell'email
  dentro il Cerchio (non si cancella, si ricolloca). Cancello delle
  meditazioni: «Le meditazioni complete sono per chi è nel Cerchio.
  Entrare è gratis: lascia l'email, conferma, ascolta.»
- **CN4 — Il footer della pagina link** (10 minuti): «Sei un
  professionista del benessere? → Crea il tuo profilo» porta a
  `/entra-nella-rete` invece che a `/accedi` (LinkPage.js:386).
  Guardia.
- **CN5 — Guardie e misura**: guardia «il form sta nel primo schermo»
  (ordine nel sorgente), «niente anti-promessa in apertura», parità
  nome; metriche da leggere in GA dopo 30 giorni: iscritti/visite
  landing (target ≥ 5%), confermati/iscritti (target ≥ 70%, oggi 33%).

Ordine: CN4 (subito) → CN1 → CN2 → CN3 → CN5; CN0 cresce in parallelo
(contenuto del founder). Deploy in un giro col go del founder.

## 3b · Stato al 3/9/2026 sera (founder: «1. il cerchio di aurya 2. sì accesa di default 3. sì. procedi»)

- **CN4 FATTO**: footer pagina link → /entra-nella-rete (guardia LK5 evoluta).
- **CN1 FATTO**: landing rigenerata (form nel primo schermo + in fondo,
  pila di valore vera, chi scrive, 268 parole); LeadForm con
  `experiencesDefault` + `experiencesLight` (solo città); consenso
  esplicito e spento. Meccanica invariata.
- **CN2 FATTO**: email di conferma «Un clic e sei nel Cerchio di Aurya»
  (dice cosa si sblocca, bottone «Entro nel Cerchio»); pagina di
  conferma «Sei nel Cerchio» + «Ascolta le meditazioni riservate»;
  promemoria unico a 48h-7g (services/cerchio_reminder.py, job ogni 6h,
  marcato prima dell'invio).
- **CN3 FATTO**: ribrand delle porte (home, cancello meditazioni,
  MeditazioniPage, Sound, Manifesto, Chi siamo, footer, account,
  Magazine, shell SEO, email di accesso). Regola: «il Cerchio» è
  l'appartenenza, «la Lettera» resta il nome dell'email.
- **CN5 FATTO**: tests/test_cerchio_cn.py; metriche GA da leggere a 30
  giorni (generate_lead landing vs confirm).
- **CN0** cresce in parallelo (contenuto del founder), nessun numero in pagina.
- **Rifinitura della sera (founder)**: il form della landing torna
  COMPLETO (nome, email, città, raggio, interessi; preferenza accesa,
  consenso spento); via ogni cadenza dichiarata («La Lettera, quando
  vale la pena», mai «ogni due settimane»: è un vincolo); via le righe
  che «sembrano finte» (chi scrive, nessun automatismo) → al loro
  posto «Prova prima di entrare»: due assaggi veri e cliccabili
  (novanta secondi di meditazione riservata; chi c'è nella rete).
- Deploy: col go del founder, dopo il build di audit.

## 3c · Revisione dei funnel (founder: «nessuna strada chiusa»)

Mappa misurata pagina per pagina (porte verso newsletter,
professionisti, entra-nella-rete, Sound, meditazioni, Studio). Le
cinque azioni: iscriversi al Cerchio · cercare un professionista ·
farsi professionista · andare su Sound/meditazioni · scoprire Studio.
Vicoli ciechi trovati e chiusi:
- /meditazioni chiedeva subito di entrare, senza assaggio (e la card
  «assaggio» della landing ci portava dritto): riga «Vuoi prima un
  assaggio? Novanta secondi su Aurya Sound» + card della landing →
  /sound, dove l'anteprima vive davvero;
- /operatori: testo ad alto valore + link «Sei un professionista?
  Entra nella rete» (non al Manifesto);
- /entra-nella-rete: zero link a Sound/Studio → la voce «Componi
  meditazioni con la tua voce» presenta e linka Crea Studio; «la parte
  pubblica ancora non c'è» era falso dal SR1 → «è aperta».
- Regole di testo: nessuna cadenza, nessuna frase che non porta valore
  («non a scadenza»), nessuna promessa che poi si scontra con un
  cancello.

## 4 · Decisioni da prendere prima di partire (PRESE il 3/9)
1. **Il nome**: «Il Cerchio di Aurya» (consigliato) / «Dentro Aurya» /
   altro.
2. ~~Quante meditazioni prima del lancio~~ — PRESA: in pagina solo
   «meditazioni riservate», senza numeri né «in arrivo».
3. **Preferenza esperienze accesa di default** sulla landing (sì,
   consigliato: è una preferenza, il consenso resta esplicito).
4. **Il promemoria a 48 h** ai non confermati (sì, consigliato: una
   sola email, mai più di una).
