# Aurya, 14 settembre 2026 — Il piano unico: Gratis e Pro a 19 €

*Stato 14/9 sera: AB-R1..R6 IMPLEMENTATI in locale (commit «feat(AB-R)»),
annuale 200 € (founder), price id Stripe del founder nella migrazione
(solo chiave live), vendita dal 1/1/2027, patto fino al 31/12/2026 per
tutti col badge ai primi venti, prima fila nel Pro. Non in produzione.*

Decisione del founder (13/9, con Valentina): **per iniziare c'è solo la
versione gratuita**, con l'uso completo del gestionale. Poi **un solo
abbonamento, Pro, a 19 € al mese o 228 € all'anno**, che oltre a tutto il
gratuito comprende:

1. **Aurya Sound**: Crea Studio, per comporre le proprie meditazioni;
2. **la newsletter per gli eventi**: i tuoi ritiri ed eventi nella Lettera
   del Cerchio della tua zona;
3. **la pubblicazione degli eventi sui social** di Aurya;
4. **l'intervista** all'operatore, con eventuali **reel** che lo
   sponsorizzano.

**Aggiunta del 14/9**: **chi entra prima del 31 dicembre 2026 ha i
vantaggi del Pro senza Sound**, gratis: l'intervista, la sponsorizzazione
sui canali social di Aurya, l'eventuale newsletter. Dal 1° gennaio 2027
chi vuole la sponsorizzazione passa all'abbonamento; l'app resta gratuita.
Il «30 giugno 2027» sparisce: il patto dei fondatori È questo, i vantaggi
di entrare subito.

Inoltre, per ora, **il pulsante «Chiedi la regia»** nella sezione eventi
del gestionale **si nasconde** (la regia va ancora consolidata).

Questo documento è il piano di refinement: cosa cambia, dove, in che
ordine, e le cinque decisioni che servono prima di scrivere codice.
Zero commissioni resta la regola fissa (10/9).

---

## 1. Da dove partiamo (inventario, verificato nel codice)

Oggi il catalogo ha **cinque piani** e il sito ne parla in **sette
posti**, con tre prezzi diversi da quello deciso.

| Dove | Cosa dice oggi | File |
|---|---|---|
| Catalogo | Gratis · Club 49 €/anno · Pro 119 €/anno · Club Fondatori · Partner; vendita dal 1/1/2027 | `backend/services/seed_commercial_plans.py` |
| Migrazioni già in prod | catalogo_2027_v1, stripe_prezzi_2027_v1 (price id live di Club 49 e Pro 119) | `backend/services/seed_pricing.py` |
| Landing operatore | «Quanto costa»: Spinta 19 €/ritiro, Club 49, Pro 119; FAQ «Quanto costa?»; patto fondatori «Club gratis fino al 30/6/2027», «prezzo Pro bloccato»; sezione Crea Studio | `OperatorLandingPage.js` + `locales/it/prelaunch.json` (opPro) |
| /costi | quattro colonne (Gratis, Spinta, Club, Pro), «Il Club si accende quando la fila c'è», fondatori, garanzia 30 giorni | `features/prelaunch/PricingPage.js` + shell SEO |
| Gestionale, Piani e costi | tre schede (Gratis, Club, Pro), banner fondatori, testi in `settings.json` billing.retreat | `pages/RetreatPlansPage.js` |
| Admin | badge dei cinque piani, assegnazione piano | `admin/pianiAurya.js`, `OrganizationsTab.js` |
| Studio | si accende per organizzazione col flag `sound_composer` dal pannello, NON dal piano | `routers/frequencies.py`, `admin/sound` |

Fuori dal codice: il PDF del piano di business (10/9) dice Club 49 / Pro
119; la memoria di lavoro pure. Vanno aggiornati.

**Cosa non tocca nessuno**: la promessa «Gratis per sempre, senza
commissioni» (home, landing, /costi, FAQ), il motore dei moduli, Stripe
Connect degli operatori.

---

## 2. Il modello nuovo, in una tabella

| | Gratis | Entrati entro il 31/12/2026 | Pro (dal 1/1/2027) |
|---|---|---|---|
| Prezzo | 0 €, per sempre | 0 € | 19 €/mese · 228 €/anno |
| Commissioni | zero | zero | zero |
| Gestionale completo (profilo, listino, prenotazioni, eventi e ritiri con caparra, clienti, recensioni, pagina link, newsletter ai propri clienti) | sì | sì | sì |
| Crea Studio (Aurya Sound) | no | no | **sì**, automatico |
| I tuoi eventi nella Lettera del Cerchio della tua zona | no | **sì**, se serve | **sì** |
| I tuoi eventi sui social di Aurya | no | **sì**, gratis | **sì** |
| Intervista + reel | no | **sì**, gratis | **sì**, su richiesta |
| Ritiri in prima fila su /esperienze | no | (proposta: sì) | **sì** (proposta) |

Spariscono: **Spinta** (19 € per ritiro), **Club** (49 €), la data del
**30 giugno 2027** e il «prezzo Pro bloccato». Il piano nascosto
`retreat_founding` diventa **«Entrato nel 2026»**: lo assegna il sistema a
chi pubblica il profilo entro il 31/12/2026, dà i tre servizi gratis (non
Studio), e dal 1/1/2027 resta com'è (l'app è gratuita) ma le nuove
sponsorizzazioni passano dal Pro. **Partner** invariato.

Le quattro cose del Pro sono di due nature, e il piano le tratta in modo
diverso:
- **automatiche** (Studio, prima fila): si accendono da sole quando il
  piano diventa attivo, si spengono quando scade;
- **servizi fatti da noi** (Lettera, social, intervista, reel): il piano
  dà il diritto, la consegna è manuale. Nel gestionale l'abbonato vede
  «Incluso: chiedilo quando vuoi» con un bottone che manda una richiesta
  a aurya.life@gmail.com e la registra nel pannello (stesso meccanismo di
  «Chiedi la regia», che infatti resta pronto dietro le quinte).

---

## 3. Le cinque decisioni da prendere prima (con la mia proposta)

1. **Da quando si vende.** Oggi il codice dice 1° gennaio 2027 e /costi
   promette «fino al 31 dicembre 2026 Aurya non ha alcun costo». Proposta:
   **tenere il 1/1/2027**. Il Pro si vede da subito (landing, /costi,
   gestionale) ma si compra da quel giorno. Coerente con quanto già
   detto agli operatori, e dà tre mesi per consolidare Studio e i servizi.
2. **228 € l'anno = 12 × 19, nessuno sconto.** Va bene, ma l'annuale
   allora non ha un motivo per esistere. Proposta: **190 € l'anno** (due
   mesi regalati, «paghi dieci mesi»): è la leva classica per incassare
   subito e ridurre le disdette. Se preferite 228, resta 228: il piano
   funziona uguale.
3. **Il patto di chi entra nel 2026** (deciso il 14/9: intervista, social,
   eventuale newsletter, gratis; niente Sound; niente 30/6/2027). Resta
   da dire una cosa sola: **il tetto**. Oggi la landing dice «i primi
   venti entro il 31 ottobre» con badge Fondatore e contatore vero.
   Proposta: la scadenza diventa **31 dicembre 2026 per tutti, senza
   tetto** (chi pubblica il profilo entro l'anno ha i tre servizi); il
   **badge Fondatore resta ai primi venti**, perché è l'unica cosa che ha
   senso contare. Il contatore in landing passa da «posti rimasti» a
   «giorni rimasti».
4. **La prima fila** (ritiri in evidenza su /esperienze e nella Lettera
   di zona) era del Club. Proposta: **dentro il Pro**, è già implementata
   (`FEATURED_PLAN_SLUGS`) e rende il piano visibile sul sito.
5. **I prezzi in Stripe.** Servono due prezzi nuovi (19 mensile, 228 o
   190 annuale) sul prodotto Pro; quelli di agosto e del 2027 non
   servono più. Chi li crea: tu dalla dashboard di Stripe, oppure io
   via API con la chiave del server, col tuo ok esplicito.

---

## 4. I lavori, in ordine

Ogni pacchetto è un commit con le sue guardie. Tutto in locale, deploy
alla fine in un giro completo (backend + frontend), col metodo della
prova generale sulla copia di produzione.

### AB-R1 · Il catalogo (backend)
- `retreat_pro`: 19 €/mese, annuale (228 o 190), intervalli mese+anno,
  `available_from` = data decisa, descrizione e feature nuove
  (`retreat_sound_studio`, `retreat_pro_lettera_eventi`,
  `retreat_pro_social`, `retreat_pro_intervista_reel`, prima fila).
- `retreat_club`: `is_public: False`, `is_self_serve: False`, non più
  seedato come vendibile (resta nel DB per chi lo avesse: nessuno).
- `retreat_founding` → nome «Entrato nel 2026», descrizione «Intervista,
  i tuoi eventi sui social di Aurya e nella Lettera, gratis: il vantaggio
  di essere entrato subito»; feature: i tre servizi, NON Studio
  (`module_plans` = base); `retreat_partner` invariato.
- Assegnazione automatica: chi ha il profilo pubblicato (rete) entro il
  31/12/2026 riceve `retreat_founding` (oggi `ids_fondatori` lo calcola
  coi primi venti: la stessa funzione, con la scadenza nuova e senza
  tetto per i servizi; il tetto resta solo per il badge).
- Migrazione `catalogo_pro19_v1` (flag-gated, idempotente): allinea i
  campi admin-protetti, toglie i price id 2027, nasconde il Club,
  assegna «Entrato nel 2026» a chi ha diritto.
- Costanti: `VENDITA_PIANI_DAL` (1/1/2027), `SCADENZA` → 31/12/2026,
  `CLUB_FINO` sparisce.
- Guardie: `test_retreat_plans.py` (slug, prezzi, intervalli),
  `test_admin_piani_pa.py`, `test_rebranding_rb.py` (patto fondatori).

### AB-R2 · I diritti (backend)
- **Studio automatico**: in `plan_provisioning.provision_commercial_plan`
  (e nel webhook Stripe) il piano Pro/Fondatori/Partner accende
  `sound_composer`; la scadenza lo spegne. Il flag manuale dal pannello
  resta come eccezione (chi lo ha oggi lo tiene).
- **Prima fila**: già legata a `FEATURED_PLAN_SLUGS`, si verifica solo.
- **Servizi su richiesta**: endpoint `POST /organizations/current/richieste-pro`
  (tipo: lettera_eventi | social | intervista_reel) che riusa il
  meccanismo delle richieste di regia (`richieste_struttura`, tipo
  nuovo), email a aurya.life@gmail.com, riga nel pannello admin
  «Richieste», visibile solo se il piano è attivo (altrimenti 403 con
  messaggio «È incluso nel Pro»).
- Guardie: provisioning accende/spegne Studio; richiesta senza Pro → 403.

### AB-R3 · Landing e /costi (frontend + shell SEO)
- Landing «Quanto costa»: una frase («Il piano base è gratuito per
  sempre. Non paghi un abbonamento e non paghi commissioni») e **una
  scheda sola**: «Pro · 19 € al mese o 228 € l'anno» con le quattro righe
  (Studio, Lettera, social, intervista + reel) e «dal 1° gennaio 2027».
  Via le tre schede. FAQ «Quanto costa?» riscritta di conseguenza.
  Patto in landing («Perché entrare ora»): «Chi pubblica il profilo
  entro il 31 dicembre 2026 ha gratis l'intervista, i suoi eventi sui
  social di Aurya e nella Lettera del Cerchio. Dal 2027 questi servizi
  sono nel Pro. L'app resta gratuita.» Le quattro schede del patto
  diventano tre (intervista, social, Lettera) più il badge per i primi
  venti; via «Club Fondatori gratuito fino al 30 giugno 2027» e «prezzo
  Pro bloccato».
- /costi: **due colonne** (Gratis, Pro), il cancello «si accende quando»
  diventa la frase sulla data, fondatori aggiornati, garanzia 30 giorni
  solo sul Pro; shell SEO di /costi allineata (titolo resta «Gratis per
  sempre, senza commissioni»).
- Guardie: `test_rebranding_rb.py` (prezzi in landing e /costi),
  `test_seo_shell.py`.

### AB-R4 · Il gestionale (frontend)
- «Piani e costi»: **due schede** (Gratis con «Piano attuale», Pro con
  prezzo mese/anno e switch mensile-annuale, «In vendita dal…» finché
  non si vende, poi «Passa a Pro» → checkout Stripe). Banner fondatori
  con il testo nuovo. Via ogni riferimento al Club dai testi di
  `settings.json`.
- Nella scheda Pro, per l'abbonato: le quattro righe con lo stato
  (Studio «attivo», Lettera/social/intervista «chiedilo» col bottone).
- Studio (TriggerStudio, pagina Sound): il testo dice «incluso nel Pro»
  e porta a Piani e costi, non a un form.
- Guardie: `test_listino_tw.py`, `test_admin_piani_pa.py` (UI).

### AB-R5 · Il pannello (admin)
- Badge: Gratis, Pro, Fondatori, Partner (Club sparisce dalla legenda).
- Assegnazione piano dal pannello: le stesse quattro voci.
- Richieste Pro nella pagina Operatori (tipo, data, stato «fatta»).

### AB-R6 · La regia, nascosta
- `EventsListPage`: il pulsante «Chiedi la regia» esce dal DOM dietro un
  flag `REGIA_VISIBILE = false` nel file, dialogo e endpoint restano
  (serviranno per le richieste Pro). Guardia P13 evoluta.

### AB-R7 · Documenti, email, memoria
- Piano di business (MD + PDF): sezione monetizzazione aggiornata.
- Email delle sequenze: nessuna cita il Club (verificato), niente da fare.
- Memoria di lavoro: `monetizzazione-piani-2027` riscritta.

### Deploy
Prova generale sulla copia di prod (la migrazione gira, i fondatori
risultano col Pro gratis, Studio acceso a chi ha il piano), suite
completa, giro completo, verifica dal vivo di landing, /costi, Piani e
costi con un operatore vero (chiedo a te di aprirlo), pannello.

**Stima**: R1+R2 mezza giornata, R3+R4 mezza giornata, R5+R6+R7 due ore,
prova generale e deploy un'ora. Tutto in una giornata di lavoro.

---

## 5. Cosa dirà il sito, in breve

- Home, porta dell'operatore: invariata («Gratis per sempre, senza
  commissioni»).
- Landing, «Quanto costa»: *Il piano base è gratuito per sempre. Se vuoi
  di più, dal 1° gennaio 2027 c'è il Pro: 19 € al mese o 228 € l'anno.
  Crea Studio per le tue meditazioni, i tuoi eventi nella Lettera del
  Cerchio della tua zona e sui social di Aurya, l'intervista e i reel che
  ti raccontano.*
- Perché entrare ora: *Chi pubblica il profilo entro il 31 dicembre 2026
  ha gratis l'intervista, i suoi eventi sui social di Aurya e nella
  Lettera del Cerchio. Dal 2027 sono nel Pro. L'app resta gratuita.*
- Gestionale: *Sei nel piano Gratis. Il Pro si accende dal 1° gennaio
  2027.*
