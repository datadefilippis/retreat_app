# Onboarding operatore — piano (5 luglio 2026, Fase 6.1)

Obiettivo del master plan: registrazione → Stripe → primo ritiro pubblicato
in **meno di 15 minuti**, testato con una persona reale non tecnica.
Richiesta founder: processo semplice che INDIRIZZA l'utente in tutto il
percorso: registrati → configura Stripe → crea e-commerce → crea ritiro →
pubblica → cura la landing/profilo.

## 0 · Cosa esiste già (verificato)
Tutti i mattoni ci sono, ognuno per conto suo:
- `/signup` (registrazione org admin)
- Stripe Connect Express: `/payment-connections/stripe/express/start|refresh|complete` + PaymentConnectionsCard in Impostazioni
- Creazione store (StoresPage), wizard ritiro (5 tab), pubblicazione
- Editor Profilo pubblico (`/public-profile`, F2.0) con completezza %
- Dashboard home operatore (D3)

**Il gap è l'orchestrazione**: dopo il signup l'operatore atterra sulla
dashboard e deve INDOVINARE l'ordine giusto tra 8 voci di menu.

## 1 · Architettura: checklist guidata, stato derivato dai DATI

**Principio: niente flag "step completato" da mantenere — lo stato di ogni
step si DERIVA da ciò che esiste davvero** (stesso principio del motore
pagamenti: la verità sono i fatti). Un operatore che salta la checklist e
fa le cose a modo suo la vede comunque aggiornarsi.

```
GET /organizations/current/onboarding-status  →  {
  steps: {
    stripe_connected:   bool   ← connection stripe attiva
    store_created:      bool   ← store pubblicato o org.public_slug attivo
    retreat_created:    bool   ← ≥1 occurrence (anche draft)
    retreat_published:  bool   ← ≥1 occurrence published
    profile_completed:  bool   ← public_profile con bio+cover (≥50%)
  },
  completed_count, total, is_complete
}
```

## 2 · Il percorso utente

### O1 · Signup verticale ✅ (fatto 5/7/2026 — signup e riattivazione provisionano retreat_free; redirect a /inizia da fare col copy signup in O4)
- [ ] Il signup provisiona **retreat_free** (verificare: oggi che piano
      assegna? deve essere il baseline retreat) + org con defaults sensati
- [ ] Copy della pagina signup nel linguaggio ritiri (non "azienda/SaaS")
- [ ] Post-verifica email → redirect a **/inizia** (non alla dashboard nuda)

### O2 · Pagina "/inizia" ✅ (fatto 5/7/2026 — merge su main)
La spina dorsale. 5 card-step numerate, ognuna con: stato (✓/da fare),
spiegazione in 1 riga "perché serve", CTA che porta ESATTAMENTE al punto
giusto, e ritorno automatico a /inizia dopo il completamento.

Ordine RAFFINATO dal founder (5/7 sera) — e RINFORZATO dal codice: dal
fix store-first la pubblicazione E' BLOCCATA senza store (409
store_required + banner nel wizard), quindi l'ordine non e' un
suggerimento, e' il binario:

1. **Collega i pagamenti** (~5 min, in Impostazioni) — "È dove arrivano
   i tuoi incassi: direttamente sul tuo conto." CTA → Stripe Express
   (start → hosted onboarding → complete → torna qui col ✓)
2. **Crea il tuo store + profilo pubblico** (~4 min) — "L'indirizzo
   pubblico delle tue pagine + la pagina Chi siamo." Nome + slug
   (proposto dal nome org), poi CTA secondaria → /public-profile.
   Il profilo pubblico E' la pagina "Chi siamo" dello store (gia'
   linkata dal footer store → /o/:slug)
3. **Il tuo primo ritiro** (~5 min) — CTA → wizard (categoria
   obbligatoria; allocazione allo store nel tab Pubblica). Bozza
   sempre permessa; senza store il toggle Pubblica e' disabilitato
   col banner "Crea il tuo store"
4. **Metti online** (~1 min) — quando published: ✓ + card "Sei online!"
   con i LINK ESPLICITI di dove appare: landing (/e/...), store
   (/s/...), directory (/ritiri) e profilo (/o/...) — il founder vuole
   che l'operatore VEDA dove vivono le sue pagine
5. **Rifinisci il profilo** (~3 min) — completezza % (se non fatto
   allo step 2); consigliato, non blocca

- [ ] Barra progresso in alto ("3 di 5 completati")
- [ ] Stato SEMPRE derivato (endpoint sopra); zero scrittura
- [ ] Quando is_complete: card finale "Sei online!" con i 3 link che
      contano (landing, profilo, directory) + cosa succede ora (email
      automatiche, caparre, dove vede gli ordini)

### O3 · Aggancio in dashboard ✅ (fatto 5/7/2026 — banner data-driven)
- [ ] Se onboarding incompleto: banner in cima alla home operatore (D3)
      "Completa la configurazione — ti mancano N passi" → /inizia
- [ ] Voce menu "Inizia" visibile finché incompleto, poi sparisce
      (gating data-driven, come tutto il resto)

### O4 · Test con persona reale (0,5 gg + la persona)
- [ ] Cronometro: signup → ritiro pubblicato. Target < 15 min
- [ ] Osservare senza aiutare; ogni esitazione = un fix di copy/UX
- [ ] Ripetere finché il target è centrato

Totale: **~3 giorni** + il test. Nessun rischio sui flussi esistenti:
la checklist ORCHESTRA, non riscrive.

## 3 · Risposte alle domande founder (5/7)

**Dove si configura il profilo della landing?**
Impostazioni → bottone "Profilo pubblico" (o direttamente `/public-profile`):
cover, bio, città/regione, social, contatti opt-in, anteprima live,
"Copia link". Nel percorso onboarding diventa lo step 5.

**Come funziona la traduzione multilingua?**
L'operatore scrive i contenuti UNA volta, in italiano. Il job orario li
traduce in en/de/fr (LLM interno, hash-invalidation). Il VISITATORE vede
la pagina nella SUA lingua: il selettore lingua dello storefront (o la
lingua del browser) decide cosa servire — con badge "tradotto
automaticamente" e fallback all'italiano se la traduzione non c'è ancora.
Quindi sì: "tutto nella lingua dell'utente" è il comportamento voluto —
dell'utente FINALE. L'operatore non deve fare nulla. (In dev il job è
spento perché manca la chiave LLM nel .env: si accende in produzione.)
