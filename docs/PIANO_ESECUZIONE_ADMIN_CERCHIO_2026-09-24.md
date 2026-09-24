# Piano di esecuzione: regia operatori + Cerchio (24/9/2026)

Riferimento analitico: `docs/ANALISI_SYSTEM_ADMIN_2026-09-24.md`. Qui i **contratti** che ogni pezzo rispetta, così i lotti si costruiscono in parallelo, restano isolati e non si rompono a vicenda. Decisioni del founder: strada B (email da subito, conferma solo per i riservati), legale v2.7, «procediamo sia newsletter che system admin».

Regole comuni a tutti i lotti
- Solo campi **aggiunti**, mai rinominati o rimossi. Nessun cambio di comportamento verso operatori e iscritti in prod finché l'interruttore `CERCHIO_SINGOLO_OPTIN` resta spento.
- Ogni scrittura da admin lascia una riga in `audit_logs` (forma canonica `admin.py:3201`: `id, actor_user_id, actor_role, organization_id, action, target_type, target_id, metadata, created_at`).
- Test di guardia nuovi per ogni lotto; i test esistenti citati sotto **non si toccano** se non per allinearli a un cambio dichiarato.
- Niente commit dagli agenti: si committa per lotto dopo la suite.

## Lotto A · Regia operatori

**A1 `services/stato_profilo.py`**
```python
async def stato_profilo(org: dict) -> dict
# → {"stato": "account"|"bozza"|"pagina"|"online", "n_servizi": int, "slug": str|None, "bio_len": int}
```
Regole (riusa `services.sequenze.stato_operatore`, non le ricalcola): `account` = nessuna bio; `bozza` = bio ma `pagina` falso (nessuno slug); `pagina` = `pagina` vero e `n_servizi == 0`; `online` = `pagina` vero e `n_servizi > 0`.

**A2 `GET /admin/organizations`** (`routers/admin.py`): nuovi parametri opzionali `q` (nome org, `public_profile.nome_persona`, email titolare, telefono, slug: match case-insensitive), `stato` (uno dei quattro), `telefono` (`si|no`). Risposta `OrgListResponse` invariata nella forma (`items`, `total`, …) più `conteggi: {account, bozza, pagina, online}` calcolati sull'insieme filtrato solo da `q`. Riga `OrgSummary` + campi nuovi tutti opzionali: `nome_persona, nome_pubblico, telefono, telefono_pubblico, stato_profilo, n_servizi, bio_len, email_verificata`. Il repository passa a una proiezione esplicita (tutti i campi che `_org_summary` legge + `public_profile.nome_persona/public_phone/show_contacts/bio`). Restano i letterali guardati da `test_regia_operatori.py`: `slug_pubblico`, `pubblicate = set(slug_pubblico)`, `email_titolare`, `"is_published": True`, e in `models/admin.py` `directory_listed, profile_published, admin_email, profile_slug`.

**A3 `services/profilo_pubblico.py`** (estrazione, zero cambi di comportamento):
```python
def pulisci(body: dict, org: dict) -> dict          # updates pronti per $set (tutta la logica oggi inline in update_public_profile: whitelist _PUBLIC_PROFILE_FIELDS, nome_persona, social, show_contacts, link_page, name, photos, languages, disciplines, translations, lat/lng, sedi/specchi)
async def dopo_salvataggio(org_id: str, updates: dict) -> None   # geocoding, allinea sedi, superficie pubblica, cache, IndexNow
```
`_PUBLIC_PROFILE_FIELDS` resta definito (o re-esportato) in `routers/organizations.py` perché `test_nome_pubblico_p1.py` e `test_bio_p2.py` lo leggono lì. La rotta dell'operatore chiama `pulisci` + `dopo_salvataggio`.

**A4 `PATCH /admin/organizations/{org_id}/public-profile`** (system admin): body = stesso corpo dell'operatore + `motivo: str` (obbligatorio, 3–300) + `name` facoltativo. Usa `pulisci`/`dopo_salvataggio`. Audit `action: "PUBLIC_PROFILE_ADMIN_EDIT"`, `target_type: "organization"`, `metadata: {campi: [...], prima: {campo: valore_breve}, dopo: {...}, motivo}` (valori troncati a 120 caratteri). Risposta: lo stesso payload della GET del profilo. Nessuna email all'operatore.

**A5 Frontend** `features/admin/OrganizationsTab.js` (+ `api/admin.js`): casella «Cerca nome, email, telefono» (`data-testid="org-cerca"`), quattro chip di stato con conteggi (`org-stato-<stato>`), interruttore «senza telefono» (`org-senza-telefono`); colonna «Chi» (nome pubblico, sotto email e telefono con lucchetto se privato, `org-chi`), colonna «Profilo» (chip stato + link `/o/slug` + «N servizi»). Restano i letterali guardati: `handleToggleDirectory`, `setDirectoryListed`, `'✓ Directory' : 'Directory'`, `org.admin_email`, `` /o/${org.profile_slug} ``, `non pubblicato` (può restare nel ramo `account`), e nel dettaglio i quattro gesti entro 6000 caratteri dopo `LO SPECCHIETTO`. Nuovo `features/admin/OrgProfiloAdminTab.js`: form compatto (nome persona, attività, tagline, bio con contatore e guida, telefono + pubblico/privato, `SelettoreDiscipline`, sede con `LocationAutocomplete`, Instagram/sito/Facebook, **motivo** obbligatorio), anteprima «Nome · Marchio» con `lib/nomePubblico.js`, salva → `PATCH` admin, testids `admin-profilo-form`, `admin-profilo-motivo`, `admin-profilo-salva`. Montato dalla scheda dell'operatore (`OrgBusinessProfileDialog` o dal dettaglio) e la scheda 360° aperta dal nome in lista. Coda «da rivedere» (`org-da-rivedere`): filtro rapido che elenca bio < 300, nome solo marchio (nessun `nome_persona`), senza telefono, pagina senza listino.

Guardia: `tests/test_regia_operatori_sa.py`.

## Lotto B · Cerchio, dati (backend)

**B1 `services/provenienza.py`**
```python
def classifica(source: str|None, porta: str|None = None, url: str|None = None) -> dict
# → {"canale": ..., "superficie": ..., "dettaglio": str|None, "porta": str|None}
ETICHETTE = {canale: label, superficie: label}   # per l'admin
```
Tassonomia: canale ∈ `sito` (superfici `cerca-ritiro, home, landing-cerchio, esperienze`), `magazine` (`articolo, guida, cta-categoria`), `sound` (`meditazioni, cancello, esplora, lab, frequenza`), `account` (`signup, signup-pro, reinvio`), `gestionale` (`lettera-operatore`), `prelancio` (`lead-viaggiatore, lead-professionista`), `manuale` (`admin, import`), `altro` (`sconosciuta`). `dettaglio` = lo slug/categoria dopo `:`/`_`. La `porta` resta l'asse separato (`?porta=`/UTM), calcolata come oggi da `sequenze.porta_cerchio` per non cambiare le sequenze.
Scrittura all'iscrizione (`POST /public/newsletter/subscribe`): campo `provenienza: {canale, superficie, dettaglio, porta, url, referrer, utm: {source, medium, campaign}, dispositivo}`; il payload accetta in più `url, referrer, utm (dict), consenso_versione`. Script `scripts/migra_provenienza.py [--prova]`: rimappa gli esistenti da `source`; idempotente.

**B2 Consenso** `services/testi_consenso.py`: dizionario `TESTI = {"cerchio-v3": "Sì, mandami la Lettera del Cerchio di Aurya (meditazioni, guide, ritiri). Ti cancelli con un clic.", ...}` con le versioni storiche (`cerchio-v1` = «Acconsento a ricevere le email del Cerchio di Aurya.», `cerchio-v2` = variante «Confermerai dall'email…», `lettera-v1` = «Acconsento a ricevere la lettera di Aurya via email.», `lancio-v1` = «Acconsento a essere contattato via email sul lancio di Aurya.») e `VERSIONE_CORRENTE = "cerchio-v3"`. Specchio FE `lib/testiConsenso.js` (guardia di parità). All'iscrizione: `consenso: {at, testo, versione, ip, user_agent, pagina, modalita}` con `modalita` iniziale `singolo`; alla conferma diventa `doppio`. Riga in `consent_audit` con `document_type="aurya_newsletter"`, `source ∈ {newsletter_subscribe, newsletter_confirm, newsletter_unsubscribe, newsletter_admin_confirm}`, `version_tag` = versione, `version_hash` = `hash_document_text(testo)` (aggiungere i valori agli enum di `consent_audit_repository.py`). Retroattivo (`scripts/migra_consenso_cerchio.py [--prova]`): confermati → `doppio`; `source == prelaunch_lead` → `prelancio` con `testo = lancio-v1`; altri pending → `singolo-senza-prova`.

**B3 Verifica «per uso»** `services/verifica_email.py`:
```python
async def segna_verificato(email: str, tipo: str, dettaglio: str = "") -> dict
# tipo ∈ conferma | clic | otp | admin. Effetti: aurya_subscribers → verificato_at, verificato_da{tipo, dettaglio}; se status == "pending" → status "confirmed", confirmed_at (= la conferma implicita: i sei cancelli restano intatti) e parte invia_subito("cerchio") come oggi; users (stessa email) → email_verified True se era falso. Idempotente.
def link_verificante(email: str, path: str) -> str   # /api/public/newsletter/v/{token}?to={path}
```
Rotta `GET /public/newsletter/v/{token}` (30/min): decodifica il token dell'iscritto (`core/subscriber_token.py`), `segna_verificato(email, "clic", to)`, 302 verso `to` (solo percorsi interni; default `/`). `POST /public/newsletter/confirm` chiama `segna_verificato(email, "conferma")` oltre a quanto fa oggi. Backfill: confermati senza `verificato_at` → `verificato_at = confirmed_at`, `verificato_da = {tipo: "conferma"}` (nello script B2).

**B4 Admin iscritti** (`routers/subscribers.py`), tutti system admin, tutti con audit (`target_type: "subscriber"`):
- `GET /admin/subscribers`: parametri in più `canale, superficie, budget, travel, dal, al, verificato (si|no), tag`; la riga (`_riga_iscritto`) aggiunge `provenienza, consenso (senza ip in lista), verificato_at, verificato_da, email_status, n_email, ultima_email_at, tag, n_note`; risposta con `canali` (lista con etichette) oltre a `sources`.
- `GET /admin/subscribers/{email}`: scheda completa (tutti i blocchi + cronologia: iscritto, promemoria, confermato/verificato, passi sequenza, disiscritto, note, righe di audit).
- `POST /admin/subscribers/reinvia-conferma` `{email}`; `POST /admin/subscribers/conferma` `{email, motivo}` → `segna_verificato(email, "admin", motivo)`, `modalita: manuale`; `PATCH /admin/subscribers/{email}/preferenze` (stessi campi di `PUT /public/newsletter/preferences`); `POST /admin/subscribers/{email}/note` `{testo}`; `PUT /admin/subscribers/{email}/tag` `{tag: [..]}`; `DELETE /admin/subscribers/{email}` `{motivo}` (cancellazione GDPR: `delete_one` + Brevo blacklist + audit).
- `GET /admin/newsletter-stats`: in più `by_budget, by_travel, by_canale, by_regione, verificati`.
- CSV: colonne in più `canale, superficie, porta, budget, consenso_modalita, consenso_versione, verificato_at, n_email`.
- Brevo sync: attributi `AURYA_BUDGET`, `AURYA_CANALE`.

**B5 Lead** `GET /admin/leads`: aggiunge per riga `iscritto: bool` (email presente in `aurya_subscribers`) e `organizzazione_id` se l'email coincide con un utente admin (lega il lead professionista all'org). Nessun altro cambio.

Guardie: `tests/test_cerchio_dati_cb.py`. Restano verdi: `test_cerchio_cn.py`, `test_newsletter_nw.py` (in particolare il letterale `'"source": d.get("source") or "(sconosciuta)"'` e `require_system_admin` su `/admin/subscribers`), `test_funnel_lettera_nl.py` (`_subscriber_ok` con `== "confirmed"`).

## Lotto C · Igiene invii e sequenze (backend, file disgiunti da B)

File: `services/email_service.py`, `services/email_gate.py`, `routers/webhooks/brevo.py`, `services/sequenze.py`, `services/email_sequenze.py`, `services/cerchio_reminder.py`, `services/background_service.py`.

**C1 Header** `List-Unsubscribe: <mailto:…>, <https://…/newsletter/preferenze/{token}>` e `List-Unsubscribe-Post: List-Unsubscribe=One-Click` nel payload Brevo, solo quando `send_email` riceve il nuovo parametro `unsubscribe_url` (le transazionali non lo passano). Le sequenze del Cerchio e il promemoria lo passano.
**C2 Gate** `is_email_blocked` consulta anche `aurya_subscribers.email_status`; il webhook Brevo scrive `email_status`/`email_status_at` anche lì (`hard_bounce → bounced`, `unsubscribed → unsubscribed` con `status` a `unsubscribed`, `spam → complaint`). Le email editoriali (sequenze `cerchio`, promemoria) **non** passano più `bypass_gate=True`; conferma e magic link sì.
**C3 Link verificanti**: i link nelle email del Cerchio (benvenuto, promemoria, Lettera) passano da `services.verifica_email.link_verificante(email, path)` (contratto B3; se il modulo non c'è ancora, importare in modo lazy e ripiegare sul link nudo).
**C4 Interruttore** `CERCHIO_SINGOLO_OPTIN` (env, default spento): acceso → `_FILTRO_SUB` = `{"status": {"$in": ["pending","confirmed"]}, "consent": True, "sospeso_at": {"$exists": False}}`, orologio dei passi `confirmed_at or created_at`, `invia_subito("cerchio")` anche all'iscrizione (chiamata da `subscribe` se acceso: esporre `invia_subito_se_singolo(email)`), promemoria a 48h con testo nuovo («Un clic e si aprono le meditazioni riservate» invece di «Ti manca un clic per entrare»), **sospensione** a 90 giorni per i `pending` mai verificati (`sospeso_at`, job accanto al promemoria, max 200/tick). Spento → tutto come oggi, byte per byte.

Guardie: `tests/test_igiene_invii_ci.py`. Restano verdi: `test_cerchio_cn.py` (`REMINDER_AFTER_HOURS = 48`, `REMINDER_WINDOW_DAYS = 7`, `reminder_sent_at: {$exists: False}`, ordine marca-poi-invia, `cerchio_reminder_job`; divieto di «ogni due settimane»).

## Lotto D · Frontend Cerchio

`features/admin/IscrittiTab.js` rifatta secondo §3.3 dell'analisi: mappa in testa (card + ripartizioni cliccabili budget/dove/canale), filtri (testo, stato, canale › superficie, porta, budget, dove, regione, vie, avviso ritiri, verificato, periodo), tabella con **colonne a scelta** (`iscritti-colonne`, scelta in `localStorage`, predefinite: Email · Nome · Stato · Provenienza · Iscritto il · Budget · Dove · Città · Avviso ritiri · Email ricevute), scheda iscritto (`iscritti-scheda`) con i sei blocchi e la cronologia, azioni (`iscritti-reinvia`, `iscritti-conferma`, `iscritti-preferenze`, `iscritti-nota`, `iscritti-tag`, `iscritti-disiscrivi`, `iscritti-elimina` a due passi). `LeadsTab.js`: colonna «Iscritto» e «Account» dai campi B5; i lead professionisti compaiono anche nel tab Account di `/admin/operatori` (stessa componente, filtrata). Forms pubblici: mandano `url, referrer, utm, consenso_versione` (da `lib/testiConsenso.js`) via `lib/cerchio.js` e `LeadForm.jsx`; il testo della casella viene da `lib/testiConsenso.js` (versione corrente) in ogni superficie.

Restano: `iscritti-tab`, `iscritti-riga`, `iscritti-stato-${status}`, `iscritti-export`, `iscritti-totale`, `iscritti-f-*`, `iscritti-dettaglio`, `iscritti-disiscrivi`; in LeadForm `experiencesOptIn`, `wants_experiences`, `PreferenzeRitiri`, `setState('error')`.

## Lotto E · Porte nuove e legale (dopo A–D)

E1 Checkout: campo opzionale `cerchio_optin: bool` nel corpo ordine → se vero, `subscribe` interno con `source="checkout"`, consenso con versione corrente, ip/ua della richiesta; casella non preselezionata sotto quella dell'operatore, stesso stile. E2 Account cliente: stessa casella. E3 Una riga con link verificante nell'email di conferma ordine e nella richiesta di recensione. E4 Bottone «Entra nel Cerchio» nella pagina grazie. E5 Legale v2.7 ×4 (frase newsletter + riga della tabella finalità per la newsletter di Aurya + conservazione della prova) e microcopy. E6 Login operatore senza verifica dietro `LOGIN_SENZA_VERIFICA` con le tre azioni dietro verifica (pagina online, IBAN/Stripe, embed).

## Ordine e deploy
A, B, C in parallelo (file disgiunti) → D → E. Deploy solo su «vai» del founder, con gli interruttori spenti finché la v2.7 non è in prod.

## Stato al 24/9 sera (tutto in locale, NIENTE in prod)

| lotto | commit | verificato |
|---|---|---|
| Legale v2.7 ×4 + hash | 96bcb77e | guardie legali verdi |
| E6 login senza verifica (`LOGIN_SENZA_VERIFICA`, spento) | 675dc3c7 | test_login_senza_verifica_e6 |
| A regia operatori | bd1a2c32 | browser: lista con chip/cerca/da rivedere, foglio Profilo su Sara, audit con prima/dopo/motivo |
| B dati Cerchio | 4683fe6a | API: iscrizione con provenienza+utm+consenso, link verificante → confermato, scheda, DELETE con audit; migrazioni locali eseguite |
| C igiene invii + `CERCHIO_SINGOLO_OPTIN` (spento) | dcd388d7 | dry-run identico prima/dopo |
| D frontend Cerchio | de33c837 | browser: Iscritti rifatta, scheda, conferma a mano |
| E porte (checkout, email ordine/recensione, grazie, `/entra`) | 6fd7beee | browser: casella separata non preselezionata al checkout di Giulia |
| «grazie» senza oracolo | 4cde8a3d | test_optin_singolo_subscribe |

Interruttori: `LOGIN_SENZA_VERIFICA` e `CERCHIO_SINGOLO_OPTIN` in `.env.production`, entrambi spenti al deploy; si accendono (riavvio backend) DOPO che la v2.7 e' in prod e il re-consent e' partito.

Dopo il deploy, in prod: `scripts/migra_provenienza.py --prova` → senza `--prova`; `scripts/migra_consenso_cerchio.py --prova` → senza. Poi decidere sui 4 lead del prelancio (una email di invito) e sul campo «quando».

## Deploy fatto — 24/9/2026 ore 12:45 UTC (tag `prod-2026-09-24-admin-cerchio`)

Prova generale sulla copia di prod (33 org, 20 pagine pubbliche identiche campo per campo, lista admin e profilo/onboarding senza errori su ogni documento). Giro in ~3 minuti con `deploy/giri/deploy-2026-09-24-admin-cerchio.sh`: backup di 8 collezioni + dump intero, frontend poi backend, 5 «profilo_online» pregressi segnati come saltati (nessuna email in ritardo), migrazioni provenienza e consenso eseguite su 39 iscritti (22 verificati), verifiche vive tutte 200, legale v2.7 servito, dry-run sequenze vuoto. **Interruttori `LOGIN_SENZA_VERIFICA` e `CERCHIO_SINGOLO_OPTIN` spenti**: si accendono in `.env.production` con riavvio del backend quando il founder decide.
