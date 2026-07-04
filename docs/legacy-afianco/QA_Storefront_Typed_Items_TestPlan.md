# QA Test Plan — Typed Public Storefront & Request Flow

**Version**: 1.0
**Scope**: Public storefront rendering, interaction, submission, and downstream order verification across all item types (physical, service, rental, event_ticket, inquiry).
**Prerequisites**: Local dev environment or staging with backend + frontend running. Admin access to create test products and view orders.

---

## 1. Test Data Setup

Create the following products in the admin Products page. All must have `is_published = true`.

| # | Name | item_type | price_mode | unit_price | unit_label | metadata | Notes |
|---|------|-----------|------------|------------|------------|----------|-------|
| P1 | Scatola Cartone | physical | fixed | 12.50 | pz | — | Standard physical item |
| P2 | Consulenza Marketing | service | fixed | 80.00 | servizio | duration_label: "60 min" | Service with duration |
| P3 | Generatore Elettrico | rental | fixed | 45.00 | giorno | rental_unit: "giorno" | Rental item |
| P4 | Cena in Masseria | event_ticket | fixed | 55.00 | posto | — | Event ticket |
| P5 | Progetto Custom | service | inquiry | — | — | — | Inquiry-priced item |
| P6 | Lampada Vintage | physical | fixed | 0 | pz | — | Zero-price edge case |

**Event Occurrences for P4** (create via Products > Edit > Date evento):

| Occ | start_at | location | price_override | status |
|-----|----------|----------|---------------|--------|
| O1 | 2026-08-14T20:30 | Sala Principale | — | published |
| O2 | 2026-08-21T20:30 | Terrazza | 65.00 | published |
| O3 | 2026-09-01T20:30 | Sala Principale | — | draft |

**Organization**: Must have `public_slug` set (e.g. "test-org") and `is_active = true`.

**Storefront URL**: `http://localhost:3000/s/test-org`

---

## 2. Storefront Rendering Tests

### R1 — Catalog loads correctly
- **Action**: Navigate to `/s/test-org`
- **Expected**: Page loads, header shows org name, "Catalogo prodotti" subtitle. All 6 products visible as cards in a grid.
- **Pass**: All products render, no console errors.

### R2 — Physical product card (P1)
- **Action**: Inspect P1 card
- **Expected**: Name "Scatola Cartone", no type badge (physical has none), price "€ 12,50", unit label "/ pz", qty selector visible (-, 0, +).
- **Pass**: All elements present, no extra type-specific sections.

### R3 — Service product card (P2)
- **Action**: Inspect P2 card
- **Expected**: Name, "Servizio" badge (blue pill), price "€ 80,00 / servizio", duration "60 min" shown as gray subtitle. Qty selector visible.
- **Pass**: Duration label visible, badge correct.

### R4 — Rental product card (P3)
- **Action**: Inspect P3 card
- **Expected**: Name, "Noleggio" badge (blue pill), price "€ 45,00 / giorno", "Per giorno" subtitle. "Periodo richiesto" section with two date inputs labeled "Da" and "A (opzionale)". Notes input below. Qty selector NOT visible (no date selected yet).
- **Pass**: Date inputs labeled correctly, qty hidden until date entered.

### R5 — Event ticket card (P4)
- **Action**: Inspect P4 card
- **Expected**: Name, "Evento" badge (blue pill), price "€ 55,00 / posto". Occurrence dropdown showing "Scegli data" label with 2 options (O1 and O2 only — O3 is draft, must NOT appear). Qty selector NOT visible (no occurrence selected).
- **Pass**: Only published occurrences shown, qty hidden.

### R6 — Occurrence dropdown content (P4)
- **Action**: Open P4 occurrence dropdown
- **Expected**: Placeholder "— Seleziona data —", then:
  - "gio 14 ago 2026 — 20:30 . Sala Principale"
  - "gio 21 ago 2026 — 20:30 . Terrazza"
- **Pass**: Dates formatted in Italian, location shown after dot separator.

### R7 — Inquiry product card (P5)
- **Action**: Inspect P5 card
- **Expected**: Name, "Servizio" badge, "Prezzo su richiesta" text (not a price). No qty selector. Instead: "Richiedi info" toggle button.
- **Pass**: No price shown, toggle button present.

### R8 — Zero-price product card (P6)
- **Action**: Inspect P6 card
- **Expected**: Name, price "€ 0,00", qty selector visible.
- **Pass**: Zero price displayed honestly, qty works.

---

## 3. Interaction & Gating Tests

### G1 — Physical qty selection
- **Action**: Click + on P1 twice, then - once
- **Expected**: Qty goes 0 → 1 → 2 → 1. "Richiedi ordine (1)" button appears in header.
- **Pass**: Qty updates correctly, header button appears/updates.

### G2 — Rental date gating
- **Action**: On P3, try to find qty selector before entering a date
- **Expected**: Qty selector is not visible.
- **Action**: Enter "Da" date = 2026-08-14
- **Expected**: Qty selector appears. Click + once.
- **Pass**: Qty gated behind date entry.

### G3 — Rental date clear resets qty
- **Action**: On P3 with qty=1 and date set, clear the "Da" date field
- **Expected**: Qty resets to 0, qty selector disappears, product removed from header count.
- **Pass**: No orphaned qty without date.

### G4 — Rental end date minimum
- **Action**: On P3, set "Da" = 2026-08-14, then click "A" field
- **Expected**: "A" date picker does not allow dates before 2026-08-14.
- **Pass**: `min` attribute enforced.

### G5 — Event occurrence gating
- **Action**: On P4, try to find qty selector before selecting an occurrence
- **Expected**: Qty selector not visible.
- **Action**: Select O1 from dropdown
- **Expected**: Qty selector appears.
- **Pass**: Qty gated behind occurrence selection.

### G6 — Event occurrence deselect resets qty
- **Action**: On P4 with occurrence selected and qty=2, change dropdown back to "— Seleziona data —"
- **Expected**: Qty resets to 0, qty selector disappears.
- **Pass**: No orphaned qty without occurrence.

### G7 — Event occurrence price override display
- **Action**: Select O2 (price_override = 65.00) on P4
- **Expected**: Price on card changes from "€ 55,00" to "€ 65,00".
- **Action**: Switch to O1 (no override)
- **Expected**: Price returns to "€ 55,00".
- **Pass**: Price updates dynamically with occurrence selection.

### G8 — Inquiry toggle
- **Action**: Click "Richiedi info" on P5
- **Expected**: Button changes to "Selezionato" (dark bg), header shows "Richiedi ordine (1)".
- **Action**: Click again
- **Expected**: Button returns to "Richiedi info", header button disappears.
- **Pass**: Toggle works both ways.

### G9 — Header button visibility
- **Action**: Remove all selections (qty=0 for all)
- **Expected**: "Richiedi ordine" button not visible in header.
- **Pass**: Button only appears with selections.

---

## 4. Summary / Cart Tests

### S1 — Physical item in summary
- **Action**: Select P1 qty=3, click "Richiedi ordine"
- **Expected**: Modal opens. Summary shows "Scatola Cartone x 3" with "€ 37,50". Total: "€ 37,50".
- **Pass**: Line and total correct.

### S2 — Event item with occurrence in summary
- **Action**: Select P4 with O2 (price_override=65), qty=2
- **Expected**: Summary shows "Cena in Masseria x 2" → "€ 130,00". Below: occurrence date formatted in Italian (e.g. "gio 21 ago 2026 — 20:30"). Total: "Totale stimato € 130,00".
- **Pass**: Occurrence date visible, override price used.

### S3 — Rental item in summary
- **Action**: Select P3 with dates 14 ago → 17 ago, qty=1
- **Expected**: Summary shows "Generatore Elettrico x 1" → "€ 45,00". Below: "14 ago → 17 ago" (localized Italian dates, not raw ISO).
- **Pass**: Rental period shown, dates formatted.

### S4 — Inquiry item in summary
- **Action**: Select P5 (inquiry toggle), plus P1 qty=1
- **Expected**: Summary shows:
  - "Progetto Custom x 1" → "Su richiesta" (NOT "€ 0,00")
  - "Scatola Cartone x 1" → "€ 12,50"
  - Total label: "Subtotale stimato" (not "Totale stimato")
  - Total value: "€ 12,50" (inquiry excluded from sum)
- **Pass**: Inquiry shows text label, total label changes, sum excludes inquiry.

### S5 — Mixed cart summary
- **Action**: Select P1 qty=1, P3 with dates, P4 with O1, P5 inquiry toggle
- **Expected**: All 4 items in summary with correct prices, dates, occurrence info. "Subtotale stimato" label. Inquiry item shows "Su richiesta".
- **Pass**: All types coexist cleanly.

---

## 5. Submit / Request Tests

### SUB1 — Valid physical-only submission
- **Setup**: P1 qty=2
- **Action**: Fill name, email, submit
- **Expected**: Success screen. "Richiesta inviata". Text mentions org name with correct accent ("e stata" must be "è stata").
- **Pass**: Request succeeds, confirmation shown.

### SUB2 — Valid mixed submission
- **Setup**: P1 qty=1, P4 with O2 qty=1, P3 with date 2026-08-14 qty=1
- **Action**: Fill name, email, phone, notes, submit
- **Expected**: Success screen.
- **Pass**: All item types accepted together.

### SUB3 — Missing name/email validation
- **Setup**: P1 qty=1
- **Action**: Leave name empty, try to submit
- **Expected**: Form does not submit (HTML5 `required` attribute).
- **Action**: Fill name, leave email empty
- **Expected**: Form does not submit.
- **Pass**: Required fields enforced.

### SUB4 — Invalid email format
- **Setup**: P1 qty=1
- **Action**: Enter email "notanemail", submit
- **Expected**: HTML5 email validation blocks submission.
- **Pass**: Email format validated.

### SUB5 — Empty cart submission impossible
- **Setup**: No items selected
- **Expected**: "Richiedi ordine" button not visible in header. Cannot open modal.
- **Pass**: Cannot reach submit without items.

### SUB6 — Server validation: event without occurrence
- **Setup**: This scenario should be prevented by frontend gating (G5). However, if tested via API:
- **Action**: POST `/api/public/order-request` with event_ticket item and no occurrence_id
- **Expected**: 400 error: "occurrence_id is required for event_ticket product..."
- **Pass**: Server rejects invalid event request.

### SUB7 — Server validation: rental without date
- **Action**: POST `/api/public/order-request` with rental item and no rental_date_from
- **Expected**: 400 error: "rental_date_from is required for rental product..."
- **Pass**: Server rejects invalid rental request.

### SUB8 — Server validation: non-published occurrence
- **Action**: POST with occurrence_id = O3 (draft status)
- **Expected**: 400 error: "Occurrence ... not found or not published"
- **Pass**: Server rejects draft occurrence.

### SUB9 — Server pricing authority
- **Action**: POST with event_ticket item, include `unit_price: 1.00` in the OrderLineCreate
- **Expected**: Created order line has server-resolved price (55.00 or 65.00 depending on occurrence), NOT 1.00.
- **Pass**: Client price ignored for storefront orders.

---

## 6. Downstream Admin / Orders Verification

After each successful submission, the tester must verify the resulting draft order in the admin Orders page.

### ADM1 — Draft order appears in list
- **Setup**: Submit any valid storefront request
- **Action**: Go to Orders page, refresh
- **Expected**: New order at top of list. Status: "Bozza". Source badge: "Web" (purple). Order number: "-" (assigned on confirmation).
- **Pass**: Order visible with correct badges.

### ADM2 — Event badge in list
- **Setup**: Submit request with P4 (event_ticket)
- **Expected**: Order row shows "Evento" badge (blue) next to order number.
- **Pass**: Badge visible.

### ADM3 — Rental badge in list
- **Setup**: Submit request with P3 (rental)
- **Expected**: Order row shows "Noleggio" badge (orange) next to order number.
- **Pass**: Badge visible.

### ADM4 — Mixed badge display
- **Setup**: Submit request with both P4 and P3
- **Expected**: Both "Evento" (blue) and "Noleggio" (orange) badges shown, compact and readable.
- **Pass**: Both badges coexist.

### ADM5 — Event line in detail panel
- **Setup**: Submit request with P4, occurrence O1
- **Action**: Click order row to open detail panel
- **Expected**: Line item shows:
  - Product name "Cena in Masseria"
  - "Evento" badge (blue)
  - Formatted date: "gio 14 ago 2026 — 20:30 . Sala Principale"
  - Price: € 55,00 (base price, no override on O1)
- **Pass**: All occurrence context visible.

### ADM6 — Event line with price override
- **Setup**: Submit with P4, occurrence O2 (price_override=65)
- **Action**: Open detail panel
- **Expected**: Line price shows € 65,00 (not € 55,00). Occurrence date and "Terrazza" location visible.
- **Pass**: Override price used and displayed correctly.

### ADM7 — Rental line in detail panel
- **Setup**: Submit with P3, dates 2026-08-14 to 2026-08-17, notes "Consegna al mattino"
- **Action**: Open detail panel
- **Expected**: Line item shows:
  - Product name "Generatore Elettrico"
  - "Noleggio" badge (orange)
  - Date range: "2026-08-14 → 2026-08-17"
  - Notes: ". Consegna al mattino"
- **Pass**: All rental context visible.

### ADM8 — Rental line without end date
- **Setup**: Submit with P3, only "Da" date, no "A" date
- **Expected**: Detail shows date without arrow/end date.
- **Pass**: Graceful rendering without end date.

### ADM9 — Physical line unchanged
- **Setup**: Submit with P1
- **Expected**: Line shows product name, qty, price. No "Evento" or "Noleggio" badge. No date/location info.
- **Pass**: Physical lines remain clean.

### ADM10 — Storefront order banner
- **Action**: Open any storefront-created order
- **Expected**: Purple info banner: "Ordine ricevuto dal catalogo pubblico"
- **Pass**: Source context visible.

### ADM11 — Confirm and verify SalesRecords bridge
- **Action**: Confirm a storefront draft order (click Conferma)
- **Expected**: Status changes to "Confermato". Order number assigned (e.g. "ORD-0001"). Toast mentions SalesRecords generated.
- **Pass**: Confirmation flow works for storefront orders.

---

## 7. Regression Checks

### REG1 — Manual order creation unaffected
- **Action**: Create an order via the admin "Nuovo ordine" button (not storefront)
- **Expected**: Form works normally. Client can set unit_price overrides. No rental/event fields shown. Order created as source "Manuale".
- **Pass**: Internal flow unchanged.

### REG2 — Invalid slug returns 404
- **Action**: Navigate to `/s/nonexistent-slug`
- **Expected**: "Catalogo non trovato" error page.
- **Pass**: 404 handled gracefully.

### REG3 — Empty catalog
- **Setup**: Create an org with no published products
- **Action**: Navigate to its storefront
- **Expected**: "Nessun prodotto disponibile" message.
- **Pass**: Empty state handled.

### REG4 — Rate limiting
- **Action**: Submit more than 5 order requests within 1 minute
- **Expected**: 429 Too Many Requests after 5th submission.
- **Pass**: Rate limiting active.

### REG5 — Product deactivation
- **Setup**: Deactivate P1 via admin
- **Action**: Refresh storefront
- **Expected**: P1 no longer visible in catalog.
- **Pass**: Deactivated products hidden.

### REG6 — Publish toggle
- **Setup**: Unpublish P2 via admin
- **Action**: Refresh storefront
- **Expected**: P2 no longer visible.
- **Action**: Re-publish P2
- **Expected**: P2 reappears.
- **Pass**: Publish toggle works.

---

## 8. Critical Pass/Fail Criteria

The storefront is **ready for real users** if ALL of the following pass:

| Category | Must-pass tests |
|----------|----------------|
| Rendering | R1-R7 (all cards render correctly) |
| Gating | G2, G3, G5, G6 (type-specific gating works, no orphaned state) |
| Pricing | G7, S2, SUB9 (server-authoritative, occurrence override works) |
| Summary | S4 (inquiry shows "Su richiesta", not zero) |
| Submission | SUB1, SUB2, SUB6, SUB7, SUB8 (valid and invalid paths handled) |
| Admin | ADM1, ADM5, ADM7, ADM9 (correct visibility per type) |
| Regression | REG1, REG2, REG3 (legacy flows unbroken) |

**Blockers**: Any failure in pricing authority (SUB9), gating (G2/G5), or server validation (SUB6/SUB7/SUB8) is a release blocker.

---

## 9. Top Risk Areas

1. **Occurrence filtering** — if draft/cancelled occurrences leak into the public dropdown, visitors could select invalid dates. Verify R5 and SUB8 carefully.
2. **Price override propagation** — the chain occurrence.price_override → order_service → order line must be verified end-to-end (G7 + ADM6 + SUB9).
3. **Rental date validation** — frontend gating can be bypassed via API. Server validation (SUB7) is the safety net.
4. **Mixed-type orders** — the combination of event + rental + physical + inquiry in one order is the highest-complexity path. Prioritize S5 + SUB2 + ADM4.
5. **State cleanup on deselect** — orphaned qty (G3, G6) could produce 400 errors on submit that confuse the user.

---

## 10. Recommended Execution Sequence

**Phase 1 — Rendering (15 min)**: R1-R8. Set up test data, verify all cards. Catches data setup issues early.

**Phase 2 — Interaction (15 min)**: G1-G9. Test each type's gating and reset behavior. Catches UX bugs.

**Phase 3 — Summary (10 min)**: S1-S5. Build a mixed cart, verify summary accuracy. Catches display bugs.

**Phase 4 — Submission (15 min)**: SUB1-SUB9. Valid and invalid paths. Catches validation gaps.

**Phase 5 — Admin verification (15 min)**: ADM1-ADM11. Verify downstream order state. Catches snapshot/bridge bugs.

**Phase 6 — Regression (10 min)**: REG1-REG6. Quick sanity checks on legacy paths.

**Total estimated time**: ~80 minutes for a thorough first pass.

**Tip**: Run Phase 1-3 in one browser tab (storefront), Phase 5-6 in another (admin). Phase 4 can be split between browser and API client (curl/Postman for server validation tests).
