# Account & checkout: directory vs store — deep analysis (9 luglio 2026)

Domanda founder: dove crea l'account l'utente della directory? Il
checkout è lo stesso dello store? Ci sono conflitti tra registrazione
di piattaforma e registrazione sullo store del singolo operatore?
Vincoli: solido, snello, l'utente directory NON deve finire sullo
store, registrazione a livello di PIATTAFORMA.

## I fatti (verificati nel codice, non a memoria)

### Fatto 1 — Esistono GIÀ due sistemi di account, separati by design ✅
| | Account store (operatore) | Passaporto (piattaforma) |
|---|---|---|
| Collection | `customer_accounts` (org-scoped) | `platform_accounts` (globale) |
| Login | email+password, dentro lo store | SOLO magic link, niente password |
| Token/client | customerClient (per-store) | platformClient (dedicato) |
| A che serve | cliente abituale di UN negozio | viaggiatore: tutti gli ordini di TUTTI gli operatori |
| Dove si entra | /account/login?store=slug (guscio store) | /account/accedi (guscio marketplace) |

Non si autenticano mai l'uno contro l'altro, non condividono token né
password. **La stessa email può esistere in entrambi senza alcun
conflitto**: sono due relazioni diverse (cliente-del-negozio vs
viaggiatore-della-piattaforma).

### Fatto 2 — Il collante è l'email, e funziona già da solo ✅
Ogni ordine (da store O da directory) viene agganciato al Passaporto
in automatico (`order_creation_service` → `link_order_to_platform_account`,
best-effort) e dopo il pagamento parte l'email di claim ("ritrova i
tuoi viaggi", cooldown 24h). **L'utente directory non deve registrarsi
PRIMA di comprare**: compra da ospite con la sua email, e il Passaporto
lo aspetta — anche per gli acquisti fatti in passato (claim retroattivo).
Questo è il pattern più snello possibile: zero attrito nel funnel di
pagamento, account dopo.

### Fatto 3 — MA il checkout della directory ti porta nello store ⚠️
Verificato in `EventLandingPage`: "Procedi al checkout" fa
`navigate('/s/{slug}', {state:{preloadCart}})` — apre la PAGINA DELLO
STORE dell'operatore col dialog di checkout. E quel dialog offre la
**registrazione org-scoped** (Fase C1: checkbox "crea account" +
password → `customer-auth/signup` sullo store).

Conseguenze (il problema che hai fiutato):
1. l'utente directory *esce* dal marketplace e si ritrova nella
   vetrina di un negozio (nav categorie, login store, altro brand);
2. se spunta "crea account" al checkout, crea l'account SBAGLIATO per
   il suo caso: uno per-negozio con password, invece del Passaporto.

Nessun danno ai soldi (il motore caparre/direct-charge è lo stesso ed
è giusto che sia così: il contratto è con l'operatore), ma il percorso
è incoerente col marketplace.

## La decisione di architettura (raccomandazione)

**UN solo motore di checkout, DUE vestiti.** Non si duplica il flusso
che tocca i soldi (è collaudato con pagamenti veri): si porta il
CONTESTO attraverso il checkout, come già fatto per le landing
(`?store=1`). Regola simmetrica a quella esistente:

- contesto **store** → checkout com'è oggi (vetrina, registrazione
  org-scoped offerta: è il cliente del negozio);
- contesto **marketplace** → stesso dialog, ma:
  - **niente vetrina intorno**: il dialog si apre subito, guscio
    ridotto (logo + lucchetto, come da piano M1), alla chiusura si
    torna alla LANDING (non allo store);
  - **niente registrazione org-scoped**: il blocco C1 sparisce;
  - al suo posto una riga informativa: "I tuoi viaggi in un posto
    solo: dopo l'acquisto ricevi il link al tuo Passaporto" (zero
    campi, zero attrito);
  - **success screen marketplace**: "🎫 biglietto via email" +
    bottone "Attiva il tuo Passaporto" (magic link, endpoint già
    esistente, enumeration-safe) + "Torna ai ritiri" → /ritiri.

### Perché è la scelta solida
- Il flusso dei SOLDI non si tocca: stesso ordine, stessa caparra,
  stessa fee per-org, stessi webhook, stessa suite di test.
- I due sistemi di account restano intatti e ignari l'uno dell'altro;
  cambia solo COSA viene offerto in quale contesto.
- Il Passaporto resta post-acquisto (mai un muro di login prima di
  pagare — il killer di conversione n°1 nei checkout).
- Implementazione piccola: 1 param di contesto + 3 rami condizionali
  nel dialog + success screen. Niente migrazioni, niente API nuove.

### Multi-operatore nello stesso carrello: NO (per scelta)
"Comprare da più operatori insieme" = oggi: un checkout per operatore,
e il Passaporto unifica DOPO (è già il design P2, ed è come funziona
il denaro: un direct charge per organizzatore). Un carrello unico
multi-operatore richiederebbe N pagamenti orchestrati in una sessione
sola — complessità enorme per un caso che nei ritiri non esiste
(nessuno prenota due ritiri nello stesso minuto). Se un giorno
servisse, il Passaporto è già il posto giusto da cui farlo.

## Piano operativo (0,5-1 gg)

- [ ] **K1** — contesto marketplace nel checkout: la landing (senza
      `?store=1`) passa `ctx=mktp` insieme al preloadCart; lo
      StorefrontPage con ctx=mktp apre il dialog subito, nasconde
      vetrina/nav (guscio minimal M1), su chiusura torna alla landing
- [ ] **K2** — dialog in ctx=mktp: via il blocco registrazione C1,
      dentro la riga informativa Passaporto (i18n ×4)
- [ ] **K3** — success screen in ctx=mktp: CTA "Attiva il tuo
      Passaporto" (chiama la request magic-link esistente con l'email
      dell'ordine) + "Torna ai ritiri"; in ctx store resta com'è
- [ ] **K4** — guard-test: in ctx=mktp il markup non contiene il
      signup org-scoped; il flusso ordine/caparra INVARIATO (stessi
      test soldi verdi)
- **DoD**: directory → landing → checkout → pagamento → "Attiva il
  Passaporto", senza MAI vedere la vetrina di un negozio; nello store
  tutto identico a oggi.
