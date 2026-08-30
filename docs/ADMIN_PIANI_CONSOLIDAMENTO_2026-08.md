# System admin e i piani — analisi di consolidamento (ciclo PA, 30/8/2026)

*Il founder: «in Details/Plan/Commercial vedo ancora piani ed
elementi fuori scope: su Aurya abbiamo solo il gratuito e il Pro da
19. Il resto è vecchio, obsoleto, fuorviante.» Analisi condotta sui
DATI di produzione + sul codice.*

## 1 · La realtà di Aurya (fatti, non impressioni)

**I piani commerciali in prod sono 4, e NON sono tutti reperti:**

| Slug | Nome | Prezzo | Natura |
|---|---|---|---|
| `retreat_free` | Gratis | 0€ | pubblico, self-serve |
| `retreat_pro` | Pro | 19€/mese (190 annuo) | pubblico, self-serve |
| `retreat_founding` | Founding | 0€ | **decisione founder 4/7**: primi organizzatori, tutto Pro gratis 3 mesi, solo-admin, invisibile al pubblico |
| `retreat_partner` | Partner | 0€ | **decisione founder 5/7**: 0% fee (Masseria, partnership), solo-admin, invisibile |

Founding e Partner **non sono AFianco**: sono leve tue, nascoste dal
pricing pubblico. Da decidere se restano (raccomando di sì).
Oggi in prod: 9 org, tutte su Gratis.

**Il reperto vero è sotto**: 26 `pricing_plans` per 5 moduli AFianco
(ai_assistant, cashflow, commerce, product_catalog, customers_light)
e 45 `module_subscriptions`. ATTENZIONE: questa è la MECCANICA
interna del provisioning — ogni piano commerciale si «traduce» in
piani-modulo (è così che il Pro accende le cose). Non si butta: si
smette di MOSTRARLA come se fosse l'offerta.

## 2 · Le superfici fuorvianti, una a una

1. **PlanBadge**: mostra slug crudi (`retreat_free`) con una palette
   per piani che non esistono più (free/core/enterprise/starter) —
   quindi sempre grigio e in gergo. Deve dire **Gratis / Pro /
   Founding / Partner**.
2. **Dialog «Plan»**: i piani elencati sono giusti (i 4 veri), ma il
   copy dice «re-provisions all module subscriptions» — gergo interno
   in una UI di prima linea, e tutto in inglese.
3. **Dialog «Commercial» (Phase 3C)**: espone drift flags e
   «provisioned modules» coi nomi AFianco + bottone «Align to
   catalog». È PLUMBING: utile al tecnico, fuorviante come pannello
   principale accanto a «Plan».
4. **Colonna «Sync» + banner drift permanente** in testa alla
   tabella (con «Run scan», HIGH/MEDIUM): per 9 org su 2 piani è
   rumore quotidiano. L'allarme serve SOLO quando c'è un problema.
5. **Billing actions**: «Custom Plan» (crea piani su misura con
   template *enterprise (Custom)*) e «Add-ons» (0 addon in prod,
   svuotati da AB5) sono fuori scope; «Extend Trial» pure — il Pro
   ha `trial_days: 0`, in Aurya IL TRIAL NON ESISTE. Restano utili:
   **Usage** (asciugata) e **Impersonate**.
6. **Filtri e stati** in inglese (trialing, past_due, canceled…) e
   il filtro Status offre stati che nessuna org ha mai avuto.
7. **Dialog di eliminazione**: elenca «conversazioni AI» tra i dati.

## 3 · Il principio

**L'admin parla la lingua dell'offerta, non del motore.** Prima
linea: 4 piani coi loro nomi, stato di fatturazione in italiano,
azioni che esistono davvero. Il motore (moduli, provisioning, drift)
resta — ripiegato in un pannello tecnico dichiarato, per il giorno
che serve.

## 4 · Le onde

### PA1 — I piani col loro nome
PlanBadge con mappa vera (`retreat_free`→«Gratis» grigio,
`retreat_pro`→«Pro» viola, `retreat_founding`→«Founding» oro,
`retreat_partner`→«Partner» verde) + fallback onesto per slug ignoti.
Stati billing in italiano (attivo/in prova/scaduto/annullato/
manuale/—) ovunque compaiono.

### PA2 — Il dialog Piano in italiano
Titolo «Cambia piano», i 4 piani con una riga di descrizione vera
(e l'etichetta «riservato — solo admin» su Founding/Partner), via il
gergo del provisioning dal copy. Resta l'unico posto per assegnare
piani.

### PA3 — Il motore si ripiega
- Bottone «Commercial» VIA dalla riga; il contenuto (drift, moduli
  provisionati, Align) diventa una sezione `<details>` «Stato
  tecnico (provisioning)» in fondo al Details.
- Colonna «Sync» via dalla tabella; il banner drift compare SOLO se
  l'audit trova problemi (verde permanente = rumore); «Run scan»
  resta dentro il banner quando visibile.

### PA4 — Azioni vere
Via i pannelli Custom Plan, Add-ons, Extend Trial (le rotte backend
restano; sparisce la UI). Restano Usage — coi soli numeri veri di
Aurya — e Impersonate.

### PA5 — Le briciole
Filtro Status coi soli stati esistenti e in italiano; dialog di
eliminazione senza «conversazioni AI»; testi della pagina in
italiano dove oggi sono in inglese (Suspend→Sospendi, ecc.).

### PA-decisione (tua): Founding e Partner
Tenerli così (raccomandato: leve strategiche già pronte, invisibili
al pubblico) o archiviarli. Se li tieni, PA1-2 li mostrano col
cartellino «riservato».

## 5 · Collaudo
Riga org: badge «Gratis», niente Sync; dialog Piano coi 4 nomi e
descrizioni; Details con specchietto + stato tecnico ripiegato;
billing actions = Usage+Impersonate; guardie su badge/copy/pannelli
usciti. Effort: ~½ giornata. In attesa del «procedi» (e della
decisione su Founding/Partner).
