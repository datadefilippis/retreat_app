# IL FARO — Aurya Sound gratuito come canale di marketing
### Piano completo, olistico e profondo (v2 consolidata, 30/8/2026)

*La cornice del founder: il mondo gratuito di Aurya Sound non è un
regalo generico — è IL canale di acquisizione. Ogni pagina deve
(1) farsi trovare da Google, (2) dare valore vero a un neofita
senza dare nulla per scontato, (3) trasformare quel valore in un
contatto — email prima, account poi — al momento giusto e in modo
tracciato. Questo documento è il piano intero: strategia, prodotto,
lingua, SEO, trigger e misura.*

---

## PARTE I — LA STRATEGIA: il funnel del faro

```
Google/social → PAGINA DI VALORE (scheda, stanza, esperienza)
      → VALORE VISSUTO (ascolti, provi, misuri, salvi)
      → MICRO-CONVERSIONE: EMAIL (la Lettera — sblocca contenuto)
      → CONVERSIONE: ACCOUNT (persistenza — il quaderno ti segue)
      → (poi, fuori da questo piano: meditazioni, operatori, Pro)
```

**La scala dei due gradini** — ogni superficie chiede UNA cosa sola:
- **EMAIL (Lettera)** = la chiave dei *contenuti*: meditazioni
  complete, nuove schede, esperienze. La chiede chi sta CONSUMANDO
  (fine anteprima, fondo scheda, fine esperienza).
- **ACCOUNT** = la chiave della *persistenza*: quaderni ovunque,
  preferiti. Lo chiede chi sta CREANDO/SALVANDO (primo salvataggio
  nei quaderni). Chi ha già l'email riceve l'invito all'account come
  secondo passo naturale, mai come primo muro.

Regole d'oro: mai due inviti nella stessa schermata; mai un popup
che interrompe un gesto; il materiale gratuito RESTA gratuito (i
trigger offrono di più, non tolgono); ogni trigger porta la sua
`source` così l'admin sa da dove arriva ogni contatto.

---

## PARTE II — LE FONDAMENTA DI PRODOTTO (attriti da togliere subito)

### FA1 — Lo sweep si ferma (la decisione RZ vale ovunque)
Nel Banco «interrompere = tenere la nota» è la scelta vecchia già
bocciata dal founder nelle Risonanze. Fix: stop sweep = **silenzio**
+ cattura della frequenza del momento (numero cliccabile per
risuonarla). Guardia che codifica il principio per ogni stanza:
**mai un suono che continua dopo uno stop**.

### FA2 — La via del ritorno si vede
Pill sticky in alto a sinistra in ogni stanza («← Sala del Lab»),
sfondo pieno, visibile nello scroll, tap-target mobile. Una classe
nel telaio Stanza.jsx → vale per tutte le stanze, presenti e future.

### FA3 — Il Ritratto salva solo nel quaderno
Il bottone libreria (visibile in realtà al solo system admin — il
founder lo vedeva perché loggato da admin) esce comunque dalla
stanza: il gesto dell'utente è il quaderno; l'admin carica dalla
sua casa (/admin/sound).

---

## PARTE III — LA PERSISTENZA: i quaderni che ti seguono (FA4)

Oggi i quaderni (scoperte Risonanze + ritratti) vivono in
localStorage: un dispositivo, una vita. Il processo — solido,
semplice, scalabile:

1. **Backend**: collezione `sound_quaderni`, un documento per
   account (`platform_account_id`), voci dei due registri con
   `client_id` univoco e `salvata_il`. API `GET/PUT
   /api/sound/quaderni` (auth account). Tetto voci (200) e payload
   minimo (numeri ed etichette, MAI audio): costo server ~zero.
2. **Sync dolce**: al login — o al salvataggio se già loggato — il
   client fonde locale+server per `client_id` (niente duplicati,
   vince il più recente). Anonimo/offline = localStorage come oggi:
   nessun salvataggio mai perso o bloccato.
3. **Il momento dell'invito** (il trigger account): al PRIMO
   salvataggio della sessione, riga non bloccante sotto la
   conferma: *«Salvato su questo dispositivo. Con un account Aurya
   (gratis) il tuo quaderno ti segue ovunque → Crea account ·
   Accedi»*, con `?next=` di ritorno alla stanza. Al ritorno: sync
   automatico + «Il tuo quaderno ora ti segue», una volta sola.
4. **Perché è scalabile**: un solo schema per tutti i registri
   presenti e futuri (se domani il Banco salva preset, è una voce
   in più, non una collezione in più).

---

## PARTE IV — LA LINGUA: il Lab spiegato come a un bambino (FA6)

La biblioteca ha la voce giusta; il Lab la adotta con METODO:

1. **Inventario totale**: ogni stanza → sezione → controllo,
   slider, bottone, grafico, numero. Niente esiste senza
   spiegazione. (L'inventario è il primo deliverable dell'onda:
   tabella stanza×elemento×didascalia.)
2. **Il pattern in tre voci**, identico ovunque:
   - *Cosa stai guardando* — una frase PRIMA di ogni grafico;
   - *Cosa succede se…* — sotto ogni controllo («alza questo e
     senti il suono farsi più…»);
   - *La parola difficile* — ogni termine tecnico spiegato tra
     parentesi alla prima apparizione + link al glossario
     («frequenza (quante volte l'onda si ripete in un secondo)»).
3. **L'apertura di ogni stanza** = una storia di 4 righe: cosa
   farai, cosa proverai, cosa scoprirai, il PRIMO GESTO evidenziato
   («Comincia da qui: premi ▶»).
4. **Tono**: umano, curioso, zero scontato; l'onestà di casa (il
   cartellino su ciò che non è dimostrato resta sacro).
5. **Guardia di completezza**: test che associa ogni controllo del
   Lab alla sua didascalia — un controllo nuovo senza spiegazione fa
   rosso.

*Nota strategica: questi testi sono anche il carburante SEO della
Parte V — si scrivono una volta, servono due padroni.*

---

## PARTE V — IL MOTORE SEO: da 1 pagina a ~50, in modo scalabile (FA7)

### V.1 Architettura hub & spoke
```
/sound (hub di sistema)
 ├── /sound/esplora (pillar: la biblioteca)
 │     └── /sound/esplora/{slug} ← NUOVO: ~40 spoke, una per scheda
 ├── /sound/impara (pillar: le fondamenta) + /glossario
 ├── /sound/lab (pillar: il laboratorio)
 │     └── /sound/lab/{stanza} (5 spoke, già vive)
 ├── /sound/calm · /sound/ground (esperienze)
 └── /meditazioni (il ponte verso la Lettera)
```
Ogni spoke linka: il suo pillar, 2-3 sorelle affini, e la stanza
del Lab dove PROVARE il fenomeno (Delta → Banco; battiti binaurali
→ Banco/XY; risonanza → Risonanze). L'interlink è parte del
template, non buona volontà.

### V.2 Le pagine-scheda (il cuore)
`/sound/esplora/{slug}` per ogni scheda della biblioteca (Delta,
Theta, Alpha, 432 Hz, battiti binaurali, rumore rosa, campane,
respiro guidato…). La biblioteca è GIÀ dati (biblioteca.js): la
pagina client riusa la scheda esistente con player; la **shell SSR
serve il testo intero** (cos'è, il grado di evidenza col cartellino
A/B/C, come si ascolta, cosa NON promettiamo — la voce onesta di
casa è anche il nostro differenziatore SEO in un mercato di claim
gonfiati). Contenuto unico e vero, mai thin.

### V.3 Scalabilità del motore
Il template è guidato dai DATI: scheda nuova in biblioteca.js →
pagina, shell, sitemap, JSON-LD e interlink nascono DA SOLI. Guardia
di parità: ogni scheda della biblioteca ha la sua URL nella sitemap
e la sua shell (il test conta le tre liste e le confronta).

### V.4 Igiene tecnica (checklist per OGNI url del mondo Sound)
- title unico ≤60 char con intento di ricerca; meta description
  ≤155 col beneficio; H1 unico = promessa della pagina;
- canonical esplicito; OG/Twitter card con immagine;
- JSON-LD: `Article` (schede e impara), `FAQPage` dove il formato è
  domanda/risposta (le stanze del Lab GIÀ lo sono), `BreadcrumbList`
  (Sound → Esplora → Delta) ovunque;
- sitemap con lastmod onesto (dalla data di modifica del contenuto);
- alt su ogni immagine; heading semantici; niente testo solo-JS:
  quello che l'utente legge, il crawler lo legge (la shell SSR);
- le rotte-app restano noindex (già così dal ciclo GS).

### V.5 Mappa delle query (il perché delle ~40 pagine)
Ogni scheda intercetta ricerche vere di neofiti: «onde delta
sonno», «frequenza 432 hz cosa significa», «battiti binaurali come
funzionano», «rumore rosa per dormire», «campane tibetane
frequenza»… La nostra risposta è diversa da tutte: onesta
(cartellino di evidenza) e PROVABILE SUL POSTO (il player e il Lab).
Nessun claim medico, mai (regola di casa, anche penale-SEO: Google
punisce lo YMYL gonfiato — la nostra onestà è un vantaggio tecnico).

### V.6 Misura e ciclo
Dopo il deploy: sitemap ricaricata in GSC (founder), poi ogni
settimana: pagine indicizzate, query/click per pagina, CTR. Le
schede che tirano generano sorelle (es. «Delta» tira → nasce
«musica per dormire: cosa dice la scienza»). Il motore cresce dove
Google dice che c'è domanda.

---

## PARTE VI — I TRIGGER: la mappa strategica (FA5 + FA8)

Un componente-invito unico («InvitoSound», fratello leggero del
CancelloLettera: qui niente cancelli — il gratuito resta gratuito),
due varianti (email / account), sempre con `source`. La mappa:

| Dove | Momento | Chiede | Source |
|---|---|---|---|
| Scheda biblioteca (fondo) | finita la lettura | EMAIL — «ricevi le nuove schede» | `sound:esplora:{slug}` |
| Calm / Ground | fine esperienza (esiste, si allinea) | EMAIL — «altre esperienze in arrivo» | `sound:calm` / `sound:ground` |
| Stanza del Lab (fondo) | dopo l'uso | EMAIL — «il Lab cresce, ti avvisiamo» | `sound:lab:{stanza}` |
| Quaderni (RZ + Ritratto) | PRIMO salvataggio | ACCOUNT — «il quaderno ti segue ovunque» | `sound:quaderno:{stanza}` |
| Landing /sound | fine anteprima 90s (ciclo FN, già live) | EMAIL — cancello meditazione | `cancello:{slug}` |
| /meditazioni | lucchetto (già live) | EMAIL | `frequenze:{slug}` |

Chi ha già l'email e salva nel quaderno → l'invito diventa account.
Chi ha già l'account → nessun invito, mai.

**Lato admin (verificato)**: ogni subscribe porta già `source`; il
dettaglio utente mostra «da: {fonte}» e c'è l'aggregato per fonte.
Si aggiunge: colonna «Fonte» nella lista iscritti + filtro, e le
fonti `sound:*` compaiono da sole quando i trigger vanno live →
targeting per canale senza lavoro nuovo.

---

## PARTE VII — MISURA DEL FUNNEL (il cruscotto del faro)

KPI, tutti già derivabili dai dati che il piano produce:
1. iscritti per fonte `sound:*` / settimana (admin, FA5);
2. account creati dal trigger quaderno (source sul signup, via
   `?next=` + source param — si annota nel funnel esistente);
3. pagine indicizzate e click GSC sulle URL /sound/* (founder + GS);
4. ascolti anteprima → iscrizioni (giro FN, già misurabile dai log).
Niente dashboard nuova in questo ciclo: i numeri vivono dove già
stanno (admin iscritti, GSC, UT1); una dashboard dedicata è un'onda
futura se i volumi la meritano.

---

## ORDINE, EFFORT, DEPLOY

1. **FA1+FA2+FA3** — attriti via (½ giornata) → deployabile subito
2. **FA4** — quaderni persistenti + trigger account (1 giornata)
3. **FA5** — tassonomia fonti + colonna admin (½ giornata)
4. **FA6** — la lingua del Lab (1½ giornate; produce i testi di FA7)
5. **FA7** — il motore SEO (1½ giornate)
6. **FA8** — la mappa trigger completa (½ giornata)

Totale ~5-6 giornate, a tappe deployabili. Ogni onda: collaudo nel
pane + guardie. Dopo FA7: sitemap in GSC (gesto del founder).

*In attesa del «procedi» (tutto in sequenza, o per onde).*
