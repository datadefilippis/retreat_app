# System Admin 360° — analisi e piano di consolidamento

**Data:** 2026-07-07 · **Contesto:** post-ciclo GT (monetizzazione blindata: GT1/GT1b canale marketplace, GT2 calcolatore, GT3 featured, GT7 visibilità directory lato operatore). Ora il controllo va chiuso ANCHE lato piattaforma.

---

## PARTE 1 — Cosa c'è oggi (inventario verificato nel codice)

La superficie system admin è **grande e solida sul piano abbonamenti/governance**: 68 endpoint (routers `admin.py`, `admin_catalog.py`, `admin_feature_flags.py`), tutti al 100% dietro `require_system_admin`, tutti coperti da `test_invariants_security.py`. Frontend: `/admin` con 7 tab (Organizations, Users, Catalog, Audit Log, Invites, Billing/MRR, AI Governance), ~7.200 righe.

Cosa funziona bene e NON va toccato:
- **Catalogo commerciale maturo**: CRUD piani + tier, pricing con validazione Stripe, archiviazione, piani custom per org, trial (grant/extend/history), addon manuali, reconcile/drift audit Stripe↔DB.
- **Gestione org/utenti da support**: sospendi, impersona (JWT 30min), reset password, unlock, verify email forzato, hard delete con cascata, inviti + registration mode.
- **MRR dashboard**: MRR corrente, per piano, per addon, churn 30gg, candidati upsell da quota warnings.
- **Audit trail globale** filtrabile.

Zone morte note (implementate, senza UI): bulk actions, trial-history, feature-flags per org, verify/unlock forzati. Tutte testate; usabili via API.

## PARTE 2 — Dove NON è più consistente con la nuova app operatori

Il system admin è rimasto alla **fase "SaaS a moduli"** (AFianco): vede abbonamenti, non vede il **marketplace**. Dopo i cicli GT il business di Aurya ha DUE motori (canone + fee sul transato marketplace) e il secondo è completamente invisibile:

1. **Le fee di piattaforma non esistono nei dati** (verificato): il webhook Stripe marca l'ordine `collected` con l'id del payment intent ma NON timbra né l'importo incassato né la fee trattenuta. La percentuale finisce solo nell'audit log alla creazione del checkout. Oggi "quanto ho guadagnato dall'operatore X" non è interrogabile senza chiamare Stripe.
2. **La directory non ha una plancia**: chi è listato e chi no (gate GT1b), quanti ritiri futuri sono nel calendario, chi è featured, quante org sono bloccate da Stripe mancante — zero visibilità aggregata. GT7 l'ha data all'operatore, non a te.
3. **Nessuna scheda business per operatore**: store, eventi pubblicati (in directory vs solo store), ordini per canale (marketplace/store/manuale/POS), GMV, incassato online vs manuale, recensioni, iscritti newsletter — sono tutti dati che ESISTONO ma non sono aggregati per org lato admin.
4. **KPI di testa poveri**: la stat row di /admin mostra solo n. org, sospese, n. utenti. Niente GMV, transato online, fee, ordini marketplace.
5. **Ordini pre-GT1 senza canale**: 23/25 ordini dev hanno `sales_channel` vuoto — le statistiche per canale richiedono un backfill (regola: ordini storici → 'store' se da storefront, 'manual' se da gestionale; derivabile da campi esistenti).
6. **Residui d'epoca**: org con piano legacy `free` accanto ai piani `retreat_*`; endpoint `PUT /plan` deprecato. Il tab AI Governance resta utile (le traduzioni LLM passano di lì) ma va etichettato per quello che è oggi.

## PARTE 3 — Principio guida

Stessa filosofia dell'app operatore: **realtà dei dati, insight → azione**. La dashboard admin non è un report: ogni numero deve rispondere a "come va il MIO business", "come va il business DEGLI operatori", "a chi devo proporre cosa". Riuso del kit grafico `components/charts` (StatCard/TrendArea/DonutSplit/MiniBars) — l'admin non merita un design system a parte.

## PARTE 4 — Il piano (ciclo SA)

### SA1 — Fee ledger: il fondamento dati (~½ giornata)
Senza questo, tutto il resto è stima.
- Al webhook (`payment_checkout_service.reconcile`): timbra su `order.payment_checkout` anche `amount_total_minor` (dalla session Stripe), `application_fee_percent` (già noto alla creazione) e `platform_fee_minor` calcolata. Da quel momento ogni incasso online porta la fee scolpita.
- **Storico**: script one-shot che ricostruisce i tre campi per gli ordini `collected` esistenti (percentuale dall'audit log `payment.checkout.created`, importo dal totale ordine).
- **Backfill `sales_channel`** sugli ordini pre-GT1 (derivazione da origine ordine).
- Guardie: il webhook DEVE timbrare la fee (test sul source), gli aggregati admin leggono solo campi timbrati.

### SA2 — Tab "Panoramica": il business a colpo d'occhio (~1 giornata)
Sostituisce la stat row povera. Endpoint `GET /api/admin/platform-overview` (cache 60s):
- **StatCard riga 1 (i miei soldi)**: fee incassate (mese + 12m), MRR (riuso endpoint esistente), ricavo totale piattaforma = fee + MRR, transato online fee-bearing del mese.
- **StatCard riga 2 (il marketplace)**: GMV totale 12m (ordini confermati, tutti i canali), n. ordini marketplace vs store vs gestionale (30gg), org attive / org visibili in directory / ritiri futuri nel calendario.
- **TrendArea 12 mesi**: GMV per mese con serie separata "transato online" (quello che ti paga).
- **DonutSplit**: GMV per canale + GMV per anima (item_type) a livello piattaforma.

### SA3 — Tab "Directory": la plancia del marketplace (~1 giornata)
Tabella operatori con le STESSE condizioni del gate GT1b (riuso della logica GT7, elevata a org-level):
- Colonne: org, piano (badge ✦ se featured), **in directory sì/no + motivi** (mode_request / stripe_not_ready / niente ritiri pubblicati / no pagina pubblica), n. ritiri futuri listati, n. ritiri esclusi, richieste vs prenotazioni dirette (30gg), rating recensioni.
- Azioni per riga: apri profilo pubblico, apri scheda operatore (SA4), assegna piano/trial (riuso `AdminOrgBillingActions`).
- KPI di testa: % org listate, ritiri nel calendario, org bloccate solo-da-Stripe (i tuoi lead di attivazione più caldi).

### SA4 — Scheda Operatore 360° (~1–1,5 giornate)
Drill-in dalla riga org (estende `OrgDetailDialog`/`OrganizationsTab`), endpoint `GET /api/admin/organizations/{id}/business-profile`:
- **Presenza**: store (n. + link), profilo pubblico (link), eventi pubblicati totali / in directory / esclusi (con motivi GT7), lingue attive.
- **Transazioni**: ordini per canale (marketplace/store/manuale/POS), GMV 12m, incassato online vs manuale, ticket medio, trend MiniBars 12 mesi.
- **I miei guadagni da questa org**: fee generate (mese/12m/lifetime, da SA1) + canone → ricavo totale, break-even Gratis↔Pro calcolato (riuso logica GT2 lato piattaforma).
- **Relazione**: piano + storia trial (espone il trial-history già esistente senza UI), moduli attivi, recensioni (media, n.), iscritti newsletter, ultimo login, età account.
- Azioni: impersona, assegna piano/trial/addon, sospendi (tutto già esistente — solo raggruppato).

### SA5 — Tab "Segnali": da dati a proposte (~½–1 giornata)
La lista che ti dice OGNI GIORNO a chi proporre cosa (motore del GTM 1-a-1):
- **Pro conviene**: org Gratis sopra ~967€/mese di transato online → "proponi Pro" (risparmio calcolato, riuso formula GT2).
- **Sbloccabili**: org con ritiri pubblicati ma fuori directory SOLO per Stripe → un'attivazione = inventario in più nel calendario.
- **A rischio**: org senza ordini da 60gg / mai pubblicato nulla / trial in scadenza senza conversione.
- **In crescita**: org con GMV in accelerazione → candidate featured/casi studio.
Ogni segnale con azione one-click (assegna trial, apri scheda, copia email operatore).

### SA6 — Pulizie di coerenza (~½ giornata, spalmabile)
- Migrare/etichettare le org con piano legacy `free` (in dev: 1 org) e ritirare `PUT /plan` deprecato.
- Esporre in UI le zone morte utili: trial-history dentro SA4 (fatto lì), bulk actions dietro un pannello "Operazioni" minimale SE serve pre-lancio (altrimenti restano API).
- Rinominare il tab "AI Governance" in "AI & Traduzioni" (oggi il consumo è quasi solo traduzione LLM) — nessuna rimozione.
- Guardia i18n: l'area admin è EN/IT? verificare e allineare (namespace admin).

## PARTE 5 — Ordine e razionale

SA1 → SA2 → SA3 → SA4 → SA5 → SA6. SA1 è prerequisito di tutto (senza fee ledger i "guadagni per operatore" sono stime); SA2/SA3 danno subito il controllo che chiedi; SA4 è la profondità; SA5 è il moltiplicatore commerciale del tuo GTM; SA6 si può intrecciare. Totale stimato: ~4,5–5,5 giornate di lavoro.

**Non nel piano (esplicitamente):** nessun nuovo ruolo intermedio, nessuna scrittura manuale delle fee (solo Stripe/webhook scrivono), nessun pannello che duplichi la dashboard Stripe — qui si aggrega ciò che è NOSTRO (ordini, piani, directory), Stripe resta la verità contabile.
