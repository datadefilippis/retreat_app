# Next step — stato e piano (4 luglio 2026)

## Dove siamo

**Fatto e su main (CI test verde):**
- Fasi 0–5 del master plan: fork pulito, motore caparre/rate (ledger + /pay/token + dunning), wizard ritiro, comunicazioni automatiche T-7/T-1/T+2, piattaforma pubblica (/ritiri, landing, profilo operatore, SEO).
- Consolidamento WS-1 (ordini/pagamenti: settle manuale con nota, bonifico esterno, bozze sbloccate), WS-2 (menu snellito plan-driven), WS-3 (type-picker Ritiro-first senza noleggi, calendario coerente, lessico posti/partecipanti).
- E2E con soldi veri: caparra 240€ su carta, fee 5% verificata sul PaymentIntent, saldo manuale, refund misto Stripe+fuori piattaforma.

**Manca (in ordine di dipendenza):**

## Blocco A — WS-4: chiudere il consolidamento (2–3 giorni)
Rifiniture UX, nessun rischio architetturale.
- [ ] A.1 Vista "richiede attenzione" in cima a Ordini (saldo scaduto, a rischio, pagato-non-confermato) — l'operatore vede in 2 secondi dove agire.
- [ ] A.2 Semplificare tab "Biglietti" del wizard: separare "posti e pacchetti" da "dati partecipanti".
- [ ] A.3 Cue contenuti ricchi al tab Pubblica (banner → editor contenuti).
- [ ] A.4 Empty states / microcopy italiano-ritiri sulle schermate chiave.

## Blocco B — Abbonamenti + modello di business (≈1 settimana) — la "parte da fixare"
La macchina self-serve ereditata ESISTE (checkout/modify/cancel/portal in billing.py). Va collegata ai piani retreat. Oggi la fee è un campo manuale su org (`application_fee_percent`), NON segue il piano: questo è il buco principale.

**B.0 Decisioni di business (founder — 30 minuti, bloccano il resto):**
| Decisione | Proposta sul tavolo | Da confermare |
|---|---|---|
| Free | 0€/mese, fee 5% sul transato | sì/no, fee % |
| Pro | 29€/mese, fee 2% | prezzo e fee % |
| Trial / founding | 3 mesi gratis ai primi 3–5 founding member | come si applica (coupon? piano?) |
| Annuale | sconto ~2 mesi (290€/anno)? | serve al lancio o dopo? |
| Limiti Free vs Pro | oggi identici tranne fee — differenziare? (es. Free max N ritiri attivi, no comms automatiche?) | cosa mettere dietro Pro |

**B.0 — DECISO (founder, 4/7/2026):** Free 0€+5% · Pro 29€/290€+2% · Founding = piano dedicato (retreat_founding: tutto Pro a 0€, non pubblico, assegnazione admin) · fee piattaforma dichiarata SEPARATA dalle commissioni Stripe in tutta la UI piani.

**B.1 ✅ (4/7/2026)** Fee agganciata al piano: al cambio piano (upgrade/downgrade/webhook Stripe Billing) → sync `org.application_fee_percent` dal commercial plan. Un solo punto di verità, transizione tracciata (audit log).
**B.2** Prodotti/prezzi Stripe Billing per retreat_pro (test → poi live), `stripe_price_id` sui piani, `is_self_serve=True` su retreat_pro.
**B.3 ✅ parziale (4/7/2026 — pagina piani retreat con fee split, cosa-è-incluso, esempio 100€; manca solo il banner upgrade in dashboard)** Pagina piano/upgrade nell'admin (riuso UI billing ereditata, copy ritiri) + banner upgrade in dashboard sopra 1.000€/mese di transato ("con Pro avresti risparmiato X€ questo mese" — il banner si paga da solo).
**B.4** Test: cambio piano → fee corretta sul prossimo checkout; downgrade → torna 5%; webhook subscription cancellata → downgrade automatico a Free.

## Blocco C — Fase 6: la fase interrotta (≈2 settimane)
Ripresa del master plan dove l'avevamo sospeso per consolidare.
- [ ] C.1 (=6.1) Onboarding operatore: registrazione → Stripe Connect Express → primo ritiro pubblicato in **<15 minuti**, testato con una persona reale non tecnica.
- [ ] C.2 (=6.3) Infra prod: VPS, docker-compose prod, dominio+TLS, Brevo nuovo (SPF/DKIM), Stripe piattaforma LIVE, uptime monitoring.
- [ ] C.3 (=6.4) Backup notturno + copia offsite + **restore provato**.
- [ ] C.4 (=6.5) GDPR/legale: privacy, cookie, termini operatori (modello Connect: vende l'operatore, noi intermediario tecnico), DPA.
- [ ] C.5 (=6.6) Security review pre-lancio (segreti, CORS, HSTS/CSP, endpoint admin, injection filtri pubblici, dipendenze — incluse le pip-audit rosse in CI).

## Blocco D — in parallelo, non dopo: validazione (Fase 0 business + Fase 7)
Il gate sovrano del piano: **le interviste agli organizzatori non sono mai partite**. Non serve la piattaforma finita per farle — servono ORA, perché B.0 (pricing) e C.1 (onboarding) si decidono meglio con 5 conversazioni vere.
- [ ] D.1 5–8 interviste a organizzatori di ritiri (rete Masseria + Instagram): come gestiscono oggi caparre/rate? cosa pagherebbero?
- [ ] D.2 Dogfooding: vendere i ritiri Masseria sulla piattaforma (primo cliente: noi) appena C.2 è su.
- [ ] D.3 3–5 founding member gratis 3 mesi con feedback settimanale.

## Ordine consigliato
1. **WS-4** (chiude il consolidamento, 2–3 gg) — intanto il founder risponde a **B.0**.
2. **Blocco B** abbonamenti (1 settimana) — sblocca il modello di business end-to-end in test.
3. **Blocco C** Fase 6 (2 settimane) — produzione.
4. **D.1 interviste**: partono SUBITO, in parallelo a tutto (bloccano il GO commerciale, non quello tecnico).

Lancio tecnico realistico: **~4 settimane** da oggi, se B.0 si decide questa settimana.
