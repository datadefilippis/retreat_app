# Inventario olistico funzionalità × abbonamenti (4 luglio 2026)

Richiesta founder: illustrare TUTTE le feature degli abbonamenti in modo
chiaro e non fuorviante (mancava perfino l'e-commerce). Questo è
l'inventario completo della piattaforma e come si distribuisce sui piani.
Source of truth tecnico: `seed_pricing.py` (tier `*_retreat_*`) +
`seed_commercial_plans.py` (features_display → i18n `billing.features.*`).

## Inventario funzionalità della piattaforma

| Funzionalità | Gratis | Pro | Founding |
|---|---|---|---|
| Ritiri illimitati con pagina prenotabile | ✓ | ✓ | ✓ |
| **Negozio online (e-commerce completo)** | 1 store | 3 store | 3 store |
| Tipi prodotto: ritiri, servizi, fisici, digitali, corsi video | ✓ | ✓ | ✓ |
| Prodotti a catalogo | 100 | ∞ | ∞ |
| Visibilità nel calendario pubblico /ritiri | ✓ | ✓ + evidenza | ✓ + evidenza |
| Caparre, rate, link di pagamento eterni | ✓ | ✓ | ✓ |
| Promemoria di pagamento automatici (dunning) | ✓ | ✓ | ✓ |
| Partecipanti, check-in, pass QR | ✓ | ✓ | ✓ |
| Email automatiche pre/post ritiro (T-7/T-1/T+2) | ✓ | ✓ | ✓ |
| Newsletter + moduli iscrizione embeddabili | ✓ | ✓ | ✓ |
| Gestionale incassi (Cashflow + Dati, export CSV/PDF) | ✓ | ✓ | ✓ |
| Anagrafica clienti | base | insight avanzati | insight avanzati |
| Coupon e codici sconto | ✓ | ✓ | ✓ |
| Membri team | 2 | 5 | 5 |
| Storefront multilingua (it/en/de/fr) | ✓ | ✓ | ✓ |
| Supporto | standard | prioritario | prioritario + feedback settimanale |
| **Fee piattaforma sul transato** | **5%** | **2%** | **2%** |

**Piano Partner** (5/7/2026): quarto piano NASCOSTO — tutto Pro, 0€ e **0% di fee** — per org proprie (Masseria) e partnership. Mai in pagina pricing, assegnabile solo dal system admin (PUT /admin/organizations/{id}/commercial-plan, slug `retreat_partner`); il provider Stripe omette application_fee quando la fee è 0 (testato).
| Canone | 0€ | 29€/mese (290€/anno) | 0€ per 3 mesi (poi Pro) |

Le commissioni Stripe (≈1,5% + 0,25€ carte EU) sono SEPARATE e le incassa
Stripe, non noi — dichiarato in pagina piani e card fatturazione.

## Regole di coerenza (per non regredire)
1. **Tier dedicati**: i piani retreat puntano SOLO a tier `*_retreat_*`
   (catalogo, commerce) — mai ai tier AFianco. Testato in
   `test_retreat_plans.py::TestRetreatDedicatedTiers`.
2. **"Uso corrente" in Impostazioni** riflette questi tier: prodotti
   x/100 (Gratis) o ∞ (Pro), store 1/3, team 2/5, righe e ordini ∞.
3. **Fee**: governata dal seed (non modificabile da admin UI — mostrata
   read-only nel catalogo system admin); sincronizzata su org a ogni
   provisioning.
4. **System admin**: catalogo con `public_only=False` → vede e assegna
   anche `retreat_founding` (nascosto dal pricing pubblico). Utente dev:
   `sysadmin@demo.com` / `demo1234`.
5. Ogni nuova funzionalità di piattaforma DEVE aggiungere la sua voce
   qui e in `features_display` — l'omissione è fuorviante quanto la
   promessa falsa.
