# Aurya Più: il giorno dell'accensione

Preparato l'8/10/2026 con SN4 (piano Aurya Sound §5.2). Tutto quello che
serve è scritto e provato; qui c'è la lista di ciò che si fa **quando il
founder decide** di accendere l'abbonamento ascoltatore (39 €/anno, solo
annuale, decisione 5). Niente di questo è applicato oggi.

## 1. Stripe (conto di Aurya, non Connect)

1. Prodotto «Aurya Più» con un prezzo ricorrente **annuale** di 39 € (IVA
   inclusa, come i piani Pro). Copiare l'id del prezzo (`price_…`).
2. Webhook dedicato: endpoint `https://aurya.life/api/public/sound/piu/webhook`,
   eventi `checkout.session.completed`, `customer.subscription.created`,
   `customer.subscription.updated`, `customer.subscription.deleted`,
   `invoice.payment_failed`. Copiare il segreto (`whsec_…`).
3. Portale clienti: attivo, con «disdici» e «cambia carta» consentiti.

## 2. Ambiente di produzione (`/opt/aurya/.env.production`)

```
SOUND_PIU_ATTIVO=1
STRIPE_PIU_PRICE_ID=price_…
STRIPE_PIU_WEBHOOK_SECRET=whsec_…
```

Il backend va ricreato per leggere l'ambiente (`docker compose up -d --force-recreate backend`).

## 3. Frontend

In `frontend/src/features/frequenze/stato.js`: `SOUND_PIU_ATTIVO = true`.
Da quel momento: `/meditazioni/piu` si vede, il badge «Presto nel Più» diventa
«Riservata al Più» con il rimando, la sezione «Aurya Più» compare in
`/account`, i bottoni «Entra nel Più» e «Gestisci» aprono Stripe.

## 4. Il cancello del Più (da costruire il giorno stesso, ~mezza giornata)

Oggi **nessun paywall**: una meditazione segnata «Più» si ascolta col
Cerchio. All'accensione il player e il server chiudono l'ascolto intero
delle tracce `accesso = piu` a chi non è `abbonato`:
- server: `_has_catalog_access` resta; si aggiunge `_ha_il_piu(request)`
  (Bearer piattaforma → `stato_account(account)["abbonato"]`) e il
  master-pass / la ricetta intera si negano con `403 {"error": "piu"}`;
- player: con `403 piu` si apre il cancello del Più (copertina in vista,
  «Entra nel Più · 39 € l'anno», «Sei già nel Più? Accedi»), l'anteprima
  di 90 s resta per tutti;
- playlist «Più»: la pagina si vede, l'ascolto intero segue la regola della
  traccia.

## 5. Testi preparati

### /costi (sezione nuova, dopo i piani dei professionisti)

> **Per chi ascolta: Aurya Più.** Il Cerchio resta gratuito: con la tua email
> ascolti tutte le meditazioni aperte. Aurya Più aggiunge le meditazioni e
> le playlist riservate, le nuove in anteprima e «riprendi da dove eri» su
> ogni telefono. **39 € l'anno**, solo annuale, si disdice quando vuoi dal
> tuo account. Niente pubblicità, niente giochi a punti.

### /meditazioni/piu (già nella pagina, `COSA_DA_IL_PIU`)

- Le meditazioni e le playlist riservate al Più, intere
- Le nuove ogni settimana, prima di tutti
- Riprendi da dove eri, su ogni telefono
- Nessuna pubblicità, nessun gioco a punti: solo il suono

### Termini (v2.14, da applicare con lo script di sblocco)

> **Aurya Più.** Aurya Più è un abbonamento annuale (39 € IVA inclusa) che
> dà accesso, per la durata dell'abbonamento, alle meditazioni e alle
> playlist contrassegnate «Più» su aurya.life. Si acquista con l'account
> Aurya tramite Stripe; si rinnova automaticamente ogni anno salvo disdetta,
> che si fa in qualsiasi momento dal proprio account e ha effetto alla fine
> del periodo pagato. Il diritto di recesso di 14 giorni vale dal primo
> acquisto; i contenuti restano di Aurya e dei professionisti che li hanno
> composti, e non sono scaricabili né rivendibili.

## 6. Comunicazione

Annuncio al Cerchio (la stessa via di «nuova meditazione», SN2) e una riga
nella Lettera. Nessun popup in casa: il Più si incontra sul badge, nella
pagina e nell'account.

## 7. Regia

Lo stato del Più dell'utente si legge in Regia → Utenti → scheda
(`account.piu`: status, scadenza, disdetta). Un omaggio si dà scrivendo
`piu.omaggio_until` sull'account (script, non interfaccia, per ora).
