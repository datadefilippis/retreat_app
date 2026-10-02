# Discipline gestite dalla regia — analisi e piano

*2 ottobre 2026. Richiesta del founder: un'operatrice fa «regressione vite passate metodo Brian Weiss», pranic healing e Access Bars. Servono voci nuove? E il system admin deve poter aggiungere discipline da solo, dal suo pannello, rendendole disponibili a tutti. Analisi profonda, piano scalabile, zero regressioni.*

## 0. Risposta per l'operatrice (oggi)

| Cosa fa | Voce da scegliere | Nota |
|---|---|---|
| Regressione vite passate (metodo Brian Weiss) | **Regressione & Vite passate** (famiglia Meditazione & Mente) | voce nuova, aggiunta oggi; «Brian Weiss» e «ipnosi regressiva» sono sinonimi nella ricerca, l'etichetta resta generica (regola DI6: niente marchi nelle etichette, come per Access Bars che però è ormai nome comune) |
| Pranic healer | **Pranoterapia** (Energia & Vibrazione) | già esistente; da oggi si trova anche scrivendo «pranic healing», «pranic healer», «prana» |
| Access Bars | **Access Bars** (Energia & Vibrazione) | già esistente |

Totale 60 voci. Fino al deploy la voce nuova è solo in locale.

## 1. Come funziona oggi (e perché ogni aggiunta costa un giro)

La tassonomia è **codice**, in cinque punti che devono restare allineati:

1. `backend/models/disciplines.py` — famiglie, slug, etichette (la fonte); `clean_disciplines` valida ciò che l'operatore salva.
2. `backend/models/retreat_taxonomy.py` — disciplina → categoria di ritiro (directory, filtri «Cosa»).
3. `backend/services/pagine_locali.py` — disciplina → categoria articoli (pagine locali `/operatori/{disciplina}[/{regione}]`, «Vedi anche», sitemap).
4. `frontend/src/lib/disciplines.js` — specchio identico + sinonimi di ricerca + «più scelte»; lo leggono 8 schermate (selettore, profilo pubblico, directory, listino, benvenuto, regia).
5. `backend/tests/test_selettore_discipline.py` — guardia di parità e conteggi.

Chi la consuma nel backend: `profilo_pubblico` (validazione), `public.py` (directory e profilo), `seo_shell` (titoli e JSON-LD), `pagine_locali` (SEO locale), `server.py` (llms). Nel frontend: 8 file via il modulo.

Costi di oggi: ogni voce = modifica a 5 file + guardia + suite + giro di deploy (2 minuti) + rischio di dimenticare un punto (le guardie lo bloccano, ma lo bloccano a me, non all'operatore che aspetta). Dal 24/9 abbiamo fatto sette aggiunte così.

## 2. Il disegno: un registro vivo con il codice come base

Principio: **il codice resta la base (le 60 voci di oggi, con le loro guardie); il database aggiunge.** Nessuna voce di codice si cancella da remoto. Così tutto ciò che oggi funziona non può rompersi: nel peggior caso, se il database è vuoto o irraggiungibile, si vede la tassonomia di oggi.

### 2.1 Dati

Collezione `discipline_extra` (una riga per voce aggiunta dalla regia):

```
slug           «regressione-vite-passate»  (minuscolo, trattini, unico, IMMUTABILE)
label          «Regressione & Vite passate»
famiglia       uno degli slug famiglia esistenti (corpo | mente | massaggio | energia | natura | psiche | anima)
categoria      categoria di ritiro esistente (yoga, meditazione, massaggio, reiki, crescita, …)
cat_articoli   categoria articoli esistente (stesse chiavi di CATEGORIA_ARTICOLI)
sinonimi       lista di parole per la ricerca
attiva         true/false (spegnere, mai cancellare: chi l'ha scelta la tiene)
creata_da / creata_il / aggiornata_il / motivo
```

Regole: lo slug non si modifica mai (vive nei profili degli operatori e negli URL delle pagine locali); l'etichetta e i sinonimi sì; una voce di codice può ricevere dal database solo **sinonimi in più** (override parziale, mai dell'etichetta). Le famiglie e le categorie restano di codice: sono poche, stabili, e reggono SEO e filtri.

### 2.2 Backend

- `services/discipline_vive.py`: `tassonomia()` → unisce codice + `discipline_extra` attive, con cache in memoria di 60 secondi e invalidazione esplicita quando la regia salva. Espone `DISCIPLINE()`, `FAMIGLIE()`, `CATEGORIA_RITIRO(slug)`, `CATEGORIA_ARTICOLI(slug)`, `SINONIMI()`.
- I cinque consumatori passano dalle costanti alle funzioni (stesso nome, stesso contratto). `clean_disciplines` accetta gli slug del registro vivo. Le costanti di codice restano come base e per le guardie.
- `GET /public/discipline` (cache HTTP 5 minuti): famiglie, voci, sinonimi, «più scelte». È ciò che il frontend carica all'avvio.
- Regia: `GET/POST /admin/discipline`, `PATCH /admin/discipline/{slug}` (label, sinonimi, famiglia, categorie, attiva), con `motivo` obbligatorio e riga di audit `DISCIPLINA_ADMIN_EDIT`, come per il profilo. Validazioni: slug canonico e libero (né di codice né già usato), famiglia e categorie dalla rosa, etichetta 2–60 caratteri, al massimo 12 sinonimi. Mai DELETE: solo `attiva=false`.
- Pagine locali e sitemap: una voce nuova entra automaticamente; la pagina `/operatori/{slug}` nasce quando tre profili la dichiarano (soglia già esistente), quindi niente pagine vuote indicizzate.

### 2.3 Frontend

- `lib/disciplines.js` resta con la tassonomia di codice **come fallback** e aggiunge `caricaDiscipline()` che chiede `/public/discipline` una volta per sessione (cache in memoria + `sessionStorage`), e un hook `useDiscipline()` che le 8 schermate usano al posto delle costanti. Se la rete manca: fallback al codice, nessuna schermata vuota.
- `SelettoreDiscipline`, `disciplineLabel`, `cercaDiscipline` leggono dal registro vivo.
- Regia: nella pagina **Operatori** una nuova scheda **«Discipline»**: tabella per famiglia (etichetta, slug, origine codice/regia, quante volte scelta, attiva), bottone «Aggiungi disciplina» (etichetta → slug proposto e modificabile prima del salvataggio, famiglia, categoria ritiri, categoria articoli, sinonimi, motivo) e modifica di etichetta/sinonimi/stato. Anteprima: «si troverà cercando …».

### 2.4 Guardie e migrazione

- La guardia di parità resta sul codice (le 60 voci). Si aggiunge `test_discipline_vive.py`: unione codice+db, slug di codice non sovrascrivibili, slug immutabile, voce spenta ancora valida per chi l'ha, cache invalidata al salvataggio, endpoint pubblico con le voci extra, audit, 403 per chi non è regia.
- Nessuna migrazione dati: il database parte vuoto. Le voci future nascono dalla regia; quelle già in codice restano dove sono (chi vorrà, un giorno, può spostarle nel db con uno script, ma non serve).
- Interruttore `DISCIPLINE_VIVE` (spento = il frontend non chiama l'endpoint e il backend ignora il database): si accende dopo la prova in prod, si spegne in dieci secondi.

## 3. Lotti

| Lotto | Cosa | Stima | Rischio |
|---|---|---|---|
| **DV1 registro** | collezione, `discipline_vive`, consumatori backend sulle funzioni, endpoint pubblico, guardia | 1 giorno | basso: con db vuoto il risultato è identico a oggi (guardia che lo prova) |
| **DV2 regia** | rotte admin con motivo e audit, scheda «Discipline» in Operatori, anteprima e validazioni | 1 giorno | basso: solo regia |
| **DV3 frontend vivo** | `useDiscipline()` nelle 8 schermate con fallback al codice, selettore e ricerca | mezza giornata | medio-basso: fallback identico a oggi, interruttore |
| **DV4 prova e accensione** | deploy spento, prova sulla copia di prod, prima voce aggiunta dalla regia, accensione | mezza giornata | — |

Ordine DV1 → DV2 → DV3 → DV4, circa tre giorni. Dopo DV4 una disciplina nuova è un minuto in regia, senza deploy, e la vedono subito operatori, directory, pagine locali e Magazine.

## 4. Cosa può rompersi e come lo si evita

- **Slug cambiato dopo l'uso** → profili e URL orfani. Mai modificabile dopo il salvataggio; la regia vede l'anteprima dello slug prima di confermare.
- **Cancellazione** → operatori con una disciplina sparita. Non esiste: solo «spenta», che resta valida per chi l'ha e sparisce solo dal selettore.
- **Doppioni** («Massaggio» e «massaggio») → lo slug canonico è unico, e un controllo di somiglianza sulle etichette avvisa («esiste già Massaggio olistico: sei sicuro?»).
- **Cache vecchia** → la regia aggiunge e non vede. Invalidazione esplicita al salvataggio lato backend; frontend con cache di sessione e un «Aggiorna».
- **SEO** → nessuna pagina locale nasce prima della soglia di tre profili; i titoli e il JSON-LD leggono l'etichetta dal registro vivo; l'URL usa lo slug immutabile.
- **Guardie storiche** che leggono le costanti → restano verdi perché le costanti restano; le nuove guardie coprono l'unione.

## 5. Cosa non fare

- Spostare le 60 voci di codice nel database «per pulizia»: perde la guardia di parità e non dà nulla.
- Etichette con nomi di marchio nelle voci (i marchi vanno nei sinonimi, come fatto oggi per Weiss e Pranic).
- Famiglie o categorie creabili dalla regia: sono il telaio di SEO e filtri, e cambiano una volta l'anno, non una al giorno.
- Cancellazioni.

## 6. Decisioni del founder

1. Via con DV1–DV4 (tre giorni) o restiamo al giro manuale (gratis, ma ogni voce passa da me)?
2. La scheda «Discipline» in Operatori va bene come posto, o la preferisci nel Tecnico?
3. La voce «Regressione & Vite passate» è pronta in locale: deploy subito perché l'operatrice sta creando il profilo?
