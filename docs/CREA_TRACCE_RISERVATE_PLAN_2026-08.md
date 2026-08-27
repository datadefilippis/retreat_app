# Crea Studio — sblocco automatico con l'abbonamento e TRACCE RISERVATE (ciclo TR, v2)

*Piano v2, deciso col founder il 27/8/2026. Supera la v1 su un punto:
Studio NON è un modulo a prezzo separato — si accende AUTOMATICAMENTE
con l'abbonamento Aurya Pro esistente (19€), prova gratuita compresa.
Il resto della v1 (due cappelli, tre visibilità, esclusione dalla
pubblica) resta e qui si dettaglia. Obiettivi dichiarati dal founder:
preciso, isolato, scalabile, e SOPRATTUTTO: non rompere ciò che oggi
funziona — in produzione lui e Valentina usano Crea e pubblicano
nelle Meditazioni, e devono continuare a farlo identico.*

---

## 0 · I fatti del sistema (verificati in codice, non supposti)

- `organizations.plan` ∈ `free|starter|pro|enterprise`;
  `organizations.billing_status` ∈ `none|trialing|active|past_due|canceled|manual`.
- La memoria anti-doppia-prova ESISTE già:
  `has_used_trial_plan_slug` (sopravvive a cancellazioni e rientri).
- `organizations.sound_composer` è il privilegio manuale del system
  admin (pannello `/admin/sound` con audit) che oggi cancella l'unico
  gate dei 12 endpoint del compositore.
- Il provisioning piani (`services/plan_provisioning.py`) e il
  lifecycle billing esistono e NON vanno toccati.

## 1 · Il principio architetturale: DERIVARE, MAI SINCRONIZZARE

Lo sblocco automatico non scrive nessun flag alla sottoscrizione: si
CALCOLA a ogni richiesta da ciò che è già vero. Una funzione pura,
in un posto solo:

```python
# services/studio_access.py — l'UNICA definizione di "Studio attivo"
def studio_attivo(org) -> bool:
    if org.get("sound_studio_override") == "off":   # kill switch
        return False
    if org.get("sound_composer"):                    # founder, Valentina
        return True
    if org.get("sound_studio_override") == "on":     # partnership/manuale
        return True
    return (org.get("plan") == "pro"
            and org.get("billing_status") in ("active", "trialing", "manual"))
```

Perché così e non con un flag scritto dai webhook: ogni copia
sincronizzata è una deriva che aspetta di succedere (abbonamento
scaduto ma flag rimasto acceso, o viceversa). Derivando, il giorno in
cui cambia il prezzo o si aggiunge un piano si tocca UNA funzione.
`sound_studio_override` è un campo nuovo, additivo, a tre stati
(assente = normale, `on` = concessione manuale, `off` = spegnimento
d'emergenza per-org): copre partnership e abusi senza toccare billing.

**La prova gratuita è quella che già esiste.** `billing_status ==
"trialing"` è uno stato del piano Pro col suo anti-doppia-prova
(`has_used_trial_plan_slug`): Studio si accende in prova perché
`trialing` è negli stati validi — zero codice nuovo per il trial, al
più una scelta commerciale (attivare i giorni di prova sul piano Pro
se oggi non sono configurati).

## 2 · I due cappelli: chi può cosa (e perché tu e Valentina non cambiate)

| Capacità | `sound_composer` (manuale) | Studio (derivato dal Pro) |
|---|---|---|
| Comporre in Crea | ✅ | ✅ |
| Pubblicare nelle **Meditazioni pubbliche** | ✅ | ❌ **mai** (403 dal server) |
| Pubblicare **riservato** + condividere link | ✅ | ✅ |

- I 12 endpoint del compositore passano da
  `require_sound_composer` a un nuovo `require_sound_crea` =
  `sound_composer OR studio_attivo(org)`. Il vecchio
  `require_sound_composer` NON si tocca: resta il gate della
  pubblicazione pubblica e del pannello admin.
- Il **publish** è il portiere unico della visibilità:
  `visibility="public"` richiede `sound_composer` (server-side, non
  una UI nascosta); senza, il server forza `private`. Tu e Valentina
  avete `sound_composer` → pubblicate in pubblico ESATTAMENTE come
  oggi, e in più potete creare condivisioni riservate.
- `/admin/sound` resta la regia: concessione composer invariata, in
  più la colonna (sola lettura) «Studio: attivo via Pro / override /
  spento» e il comando override on/off con audit.

## 3 · La condivisione: un LINK PER CONTATTO, revocabile a persona

Risposta alle tre domande del founder (il link è solo per quell'utente?
serve un account? come si revoca?):

**La condivisione è un oggetto di prima classe**, non un URL furbo:

```
sound_shares {
  id, org_id, track_id,
  contact_id,                  // il contatto CRM (ScegliPersona esiste già)
  token,                       // 128 bit random, opaco — NON un JWT
  stato: "attivo" | "revocato",
  creato_il, revocato_il,
  accessi: int, ultimo_accesso // il seme delle analytics future
}
// indici: token (unico), (org_id, track_id), (org_id, contact_id)
```

- **Un link a persona**: `/ascolta/{token}`. Ogni contatto riceve il
  SUO link. Revocare Marco non tocca il link di Giulia: la revoca è
  `stato="revocato"`, effetto immediato, un click. (Il token opaco in
  DB batte il JWT proprio qui: la revoca è vera, non "aspetta la
  scadenza".)
- **Niente account per chi ascolta** (fase 1, dichiarata onestamente
  nella UI): obbligare il cliente di uno yoga teacher a registrarsi
  su Aurya ucciderebbe l'uso al primo invio. Il modello di fiducia è
  «link personale, non in elenco, revocabile» — un gradino SOPRA
  l'unlisted di YouTube perché è per-persona e tracciato. Chi inoltra
  il link, inoltra il proprio nome: `ultimo_accesso`/`accessi`
  rendono visibile l'anomalia all'operatore.
- **Fase 2 (non ora, il modello la prevede)**: flag per-share
  `richiede_verifica` — il cliente conferma la propria email con un
  codice (riuso dell'infra del cerchio) e il server lega il token al
  cookie di prova. Fase 3 (non ora): account cliente vero.
- **Il suono viaggia sicuro**: il player della pagina `/ascolta` è il
  `PublicFrequencyPage` con un gate diverso — verificato lo share
  (esiste, attivo, traccia `private`+pubblicata, e Studio o composer
  dell'org... vedi §5 per il decaduto), il server conia il master-pass
  effimero già esistente (scope nuovo `fqz_condivisa`) e nginx serve
  i byte come oggi (X-Accel, Range nativo). Pagina `noindex`, fuori
  da sitemap e shell; rate-limit sulla rotta; nessun elenco pubblico
  di token da nessuna parte.
- **L'invio** riusa `ContactActions` (wa.me/mailto col gate GDPR già
  costruito): il messaggio precompilato porta il link. Niente email
  transazionali nuove in fase 1.

## 4 · Le tre visibilità della traccia (additive, zero migrazioni)

`draft` → `published/public` (composer only, com'è oggi: catalogo,
SEO) → `published/private` (Studio o composer: solo link per
contatto). Campo `visibility` con **assenza = public**: nessuna
migrazione, i documenti esistenti non si toccano. L'esclusione dal
pubblico è STRUTTURALE: il filtro `visibility != "private"` vive
nella query-base del catalogo (stile `_mio()`: un posto solo,
guardato), e da lì ereditano catalogo, sitemap, shell SEO, profilo
operatore, contatori della vetrina.

## 5 · Quando l'abbonamento decade (deciso ora, non scoperto poi)

- `past_due`/`canceled` → `studio_attivo` = false → **niente nuove**
  composizioni, pubblicazioni o condivisioni (403 con messaggio che
  spiega e porta a /costi).
- **Le condivisioni esistenti CONTINUANO a suonare**: il cliente
  finale non va punito per il rinnovo mancato del suo operatore. Le
  tracce restano (sono dati dell'org, mai cancellati dal billing).
  Il check della rotta `/ascolta` guarda lo share, NON lo stato
  dell'abbonamento. Se un giorno servirà un tetto, sarà una decisione
  esplicita, non un effetto collaterale.
- Riattivazione → tutto riprende da dov'era. Zero stati intermedi.

## 6 · Il muro anti-regressione (la parte "non bugghi l'attuale")

Guardie che DEVONO esistere prima del deploy, come test API veri:

1. **L'invarianza del founder**: org con `sound_composer` (senza Pro)
   → compone, pubblica in pubblico, la traccia appare in catalogo —
   il flusso di oggi, byte per byte. È il test che protegge te e
   Valentina.
2. Org Pro attiva senza composer → compone; publish `public` → 403;
   publish → `private` forzato; la traccia NON appare MAI in
   catalogo, sitemap, shell, profilo (ricerca per slug su tutte le
   superfici).
3. Org free/starter → 403 su tutti gli endpoint del compositore
   (com'è oggi per chi non ha il privilegio).
4. Share revocato → 403 su `/ascolta` e sul master; gli altri share
   della stessa traccia continuano.
5. Billing decaduto → niente nuove condivisioni, ma share esistente
   suona.
6. `trialing` → Studio attivo; trial già consumato
   (`has_used_trial_plan_slug`) → nessun secondo trial (già garantito
   dal billing esistente, la guardia lo fotografa).
7. Override `off` → tutto spento anche con Pro attivo (kill switch).

## 7 · Le onde

- **TR1 — l'accesso derivato** (½ giorno): `studio_access.py` +
  `require_sound_crea` sui 12 endpoint + campo override + colonna in
  `/admin/sound`. Guardie 1, 3, 6, 7.
- **TR2 — la visibilità** (½ giorno): campo `visibility`, portiere
  sul publish, filtro strutturale nella query-base. Guardia 2.
- **TR3 — gli share** (1 giorno): collezione+indici, endpoint
  crea/lista/revoca (org-scoped via `_mio`-style), rotta `/ascolta/
  {token}`, master-pass `fqz_condivisa`, `noindex`. Guardie 4, 5.
- **TR4 — la UI** (1 giorno): al publish la scelta (se composer)
  Meditazioni/Riservata; in «Le mie tracce» il pannello condivisioni
  (ScegliPersona → crea link → copia/WhatsApp via ContactActions →
  revoca); per gli org Pro senza composer la scelta non appare:
  riservata e basta. Empty-state in Crea per chi arriva dal Pro
  («Benvenuto nello Studio»).
- **TR5 — i doveri** (½ giorno): hard delete porta via share e master
  privati; riga ToS sulla titolarità dei contenuti («le meditazioni
  che componi restano tue» va scritto nel legal, non solo in
  landing); privacy: il contatto è già CRM (base contrattuale),
  l'ascoltatore anonimo non genera dati nuovi oltre il contatore.
- **TR6 — il collaudo del muro**: la suite del §6 completa, più lo
  smoke sul flusso intero (Pro si abbona → compone → condivide →
  cliente ascolta → revoca → 403).

Ordine: TR1→TR2→TR3 sono il cuore e vanno insieme in un branch;
TR4 sopra; TR5-TR6 prima di qualunque deploy. Niente deploy senza il
muro del §6 verde e senza il go esplicito.

## 8 · Cosa resta fuori (detto per non rifarlo)

Verifica email per-share (fase 2), account cliente (fase 3),
analytics d'ascolto oltre il contatore, percorsi/serie assegnati,
email transazionali, watermark audio. E il catalogo Professional
resta com'è: spento in vetrina, substrato della fase-vibrazioni.
