# Products Domain — Architecture Reference

> **Audience**: engineers touching `frontend/src/features/products/` or any
> per-type module (`physicals`, `services`, `reservations`, `digitals`,
> `events`, `courses`). Read this **before** adding/removing files.
>
> **Last updated**: PR-4 — legacy Dialog removed, ProductsPage is now a
> lite hub (1526 → ~705 LoC).
> **Status**: target topology complete. Phases 0-4 of the consolidation
> roadmap are done; Phase 5 (hook extraction) and Phase 6 (booking
> migration) remain optional and data-driven.

---

## 1. Why this document exists

Recent product-domain work uncovered two confusion sources that cost
developer time:

1. **Two coexisting CRUD paradigms** — a legacy `Dialog` inside
   `ProductsPage.js` AND five per-type `Wizard` + `DashboardPage` modules.
   Both LOOK alive in the code but only the latter is reachable in
   normal user flows. A developer touching the wrong one ships changes
   nobody sees.
2. **Cross-tipo intertwining** — code in `features/products/` references
   per-type behaviours (e.g. event occurrence editor JSX embedded in
   the legacy Dialog) while per-type modules reference shared products
   helpers. Eliminating the legacy without first extracting these
   intertwined pieces breaks live features.

This document is the source of truth for "which file owns what".

---

## 2. User flows (what really happens)

For every product type, the user journey is **identical in shape**:

```
/products                            (ProductsPage.js — hub + filtered grid)
   │
   ├─→ click "+ Nuovo prodotto"
   │     └─→ TypePicker dialog (inline in ProductsPage.js, lines ~675-738)
   │           │
   │           ├─→ Physical    → navigate('/physicals/new')      → PhysicalWizard
   │           ├─→ Service     → navigate('/services/new')       → ServiceWizard
   │           ├─→ Rental rng  → navigate('/reservations/new?flavor=range')
   │           ├─→ Rental slot → navigate('/reservations/new?flavor=slot')
   │           ├─→ Digital     → navigate('/digitals/new')       → DigitalWizard
   │           ├─→ Event       → navigate('/events/new')         → EventWizard
   │           └─→ Course      → checkBunnyAndProceed('/courses/new')
   │
   └─→ click "Modifica" on a product card
         │
         ├─→ Physical  → navigate('/physicals/:id')   → PhysicalDashboardPage
         ├─→ Service   → navigate('/services/:id')    → ServiceDashboardPage
         ├─→ Rental    → navigate('/reservations/:id') → ReservationDashboardPage
         ├─→ Digital   → navigate('/digitals/:id')    → DigitalDashboardPage
         ├─→ Event     → navigate('/events/:occ_id')  → EventDashboardPage
         └─→ Course    → navigate('/courses/:id')     → CourseEditor
```

**Status update (PR-4)**: the legacy ``Dialog`` inside ``ProductsPage.js``
has been removed entirely, together with ``openCreate`` / ``openEdit`` /
``handleSave`` and their associated state. The page is now a pure hub:
TypePicker + filtered grid + per-type embedded grids. Every create and
edit flow lives in its dedicated wizard/dashboard route.

The event occurrence list+composer that used to live inline inside the
Dialog was extracted in PR-2 into
``features/events/components/OccurrenceEditorPanel.jsx`` — a controlled
component whose contract (``productId`` + ``occurrences`` +
``onOccurrencesChange``) is documented inside the file. After PR-4
nobody imports it anymore; the file is intentionally retained so a
future "manage occurrences for an event product" surface (e.g. a
dedicated ``/events/products/:id/occurrences`` route) can re-mount it
without re-deriving the form logic.

---

## 3. Target file topology

```
frontend/src/features/
├── products/                        ← HUB + SHARED ONLY
│   ├── ProductsPage.js              ← lite hub: TypePicker + filtered grid
│   ├── hooks/
│   │   └── useLandingUrl.js         ← shared helper for landing URLs
│   └── components/
│       ├── ProductCardBase.js       ← reusable card (4 grids use it)
│       └── CostSourceEditor.jsx     ← W1.S5 cost composition editor
│
├── physicals/
│   ├── PhysicalWizard.js            ← CREATE
│   ├── PhysicalDashboardPage.js     ← VIEW + EDIT
│   └── components/PhysicalsGrid.js  ← LIST (embedded in /products)
│
├── services/
│   ├── ServiceWizard.js
│   ├── ServiceDashboardPage.js
│   └── components/ServicesGrid.js
│
├── reservations/                     ← rental (range + slot flavors)
│   ├── ReservationWizard.js
│   ├── ReservationDashboardPage.js
│   └── components/ReservationsGrid.js
│
├── digitals/
│   ├── DigitalWizard.js
│   ├── DigitalDashboardPage.js
│   └── components/DigitalsGrid.js
│
├── events/                           ← event_ticket (atomic occurrence model)
│   ├── EventWizard.js
│   ├── EventDashboardPage.js
│   ├── components/
│   │   ├── EventsGrid.js
│   │   ├── FieldEditorList.js       ← shared with services (attendee fields)
│   │   └── OccurrenceEditorDialog.jsx  ← Phase 3 extraction target
│   └── checkin/                      ← QR check-in flow (CheckInPage.js)
│
└── courses/                          ← Bunny Stream integration
    ├── CoursesPage.js
    ├── CourseEditor.js
    ├── components/CoursesGrid.js
    └── bunny-manager/
        ├── BunnyManagerDialog.js
        ├── BunnyManagerBody.js
        ├── useBunnyManager.js
        └── BunnyStatusWidget.js
```

---

## 4. Architectural rules

These rules **must** hold for every PR touching the products domain.
They prevent the cross-tipo intertwining problem from re-emerging.

### R1 — One type, one module

Every product type owns a single subdirectory under `features/`. No
file in `features/{type-A}/` imports from `features/{type-B}/`. The
**only** allowed cross-type imports are from `features/products/`
(shared) into per-type modules — never the other way around.

**Exception**: `FieldEditorList.js` and `fieldConfigUtils.js` live
under `features/events/components/` for historical reasons; they are
used by both events and services. This is intentional and grandfathered
(documented here so nobody "fixes" it accidentally).

### R2 — Shared components live in `products/components/`

Any component used by ≥2 product types belongs in
`features/products/components/`. Examples today:
- `ProductCardBase.js` — used by physicals, reservations, digitals, courses grids
- `CostSourceEditor.jsx` — used by all 5 wizards + all 5 dashboards (Wave 1)

### R3 — Routing-first navigation

No `Dialog` is used to switch between **conceptual modes** (e.g. "create
this product type" vs "create that one"). Every entity-creation flow
has its own URL. The TypePicker is a one-off router-picker; once you
pick a type, you navigate to that type's wizard.

This is **why the legacy Dialog in ProductsPage.js is being removed**:
it violated R3 by trying to be a polymorphic create/edit dialog.

### R4 — Deprecated fields are explicitly dated and scoped

When a field becomes legacy, mark it with:
```js
// @deprecated since Wave X — removable when [condition documented]
```
Examples:
- `product.cost_price` — deprecated Wave 1, removable when backend
  drops the column AND zero frontend readers remain.
- `item_type === 'booking'` — deprecated Onda 16, removable when prod
  DB has zero `booking` rows.

### R5 — Wizards follow the 5-step skeleton

Every wizard exposes `TABS` constant, `activeTab` state, `nextTab()`/
`prevTab()`, `fieldError()` helper, `validateXxx()` per tab, an
`onSubmit()` that POSTs to `/api/products` and navigates to the
dashboard. Post-launch Phase 5 will extract this into a `useWizard()`
hook — until then, **follow the pattern exactly** to keep extraction
straightforward.

### R6 — `cost_source` is the authoritative cost basis

Since Wave 1, all cost-related reads (margin calculation, AI insight,
reconciliation) consume `product.cost_source`. The legacy `cost_price`
field is read **only as a backward-read fallback** by the backend
resolver during migration. Frontend wizards and dashboards write
exclusively to `cost_source`.

---

## 5. Modules: what's alive, what's legacy

### Alive — production code

| Module | Role | Notes |
|---|---|---|
| `ProductsPage.js` (lite hub portion: TypePicker, grid filter, summary chips) | Routing hub | Will shrink from 1439 → ~600 LoC after Phase 4 |
| 5 `*Wizard.js` | CREATE per type | All on the 5-step pattern (R5) |
| 5 `*DashboardPage.js` | VIEW + EDIT per type | All call `productsAPI.update` inline |
| 6 `*Grid.js` | LIST per type, embedded in /products | 4 use `ProductCardBase`, 2 use custom UI |
| `CostSourceEditor.jsx` | Cost composition (Wave 1) | Used by all wizards + dashboards |
| `ProductCardBase.js` | Shared card | 4 grids |
| `useLandingUrl.js` | Helper | 5 dashboards |
| `BunnyManagerDialog.js` + co. | Course/video integration | Only used by courses |

### Legacy — fully removed (PR-4)

| Module | Status |
|---|---|
| ~~`ProductsPage.js` Dialog~~ | Removed in PR-4 |
| ~~`ProductsPage.js` `openCreate` / `openEdit` / `handleSave`~~ | Removed in PR-4 |
| ~~`ProductsPage.js` `ProductCard` inline `onEdit` callback~~ | Refactored in PR-3: the card now uses `<Link>` resolved via `productCardDashboardHref` (event_ticket + course edge cases handled inline) |
| ~~`cost_price` field in legacy edit payload~~ | Removed (Wave 1 Phase 1) |
| ~~`features/reservations/ReservationsDashboard.js`~~ | **NOT dead** — admin list of IssuedReservation rows (route `/reservations`, Onda 16 Fase 5); audit initially mislabelled it. Confirmed alive by routing check in `App.js:558`. | Keep |

### Deprecated but actively supported (don't remove yet)

| Concept | Why kept | Removal trigger |
|---|---|---|
| `item_type === 'booking'` | Pre-Onda 16 merchants may still have booking products | `SELECT COUNT(*) FROM products WHERE item_type='booking'` returns 0 |
| Service `metadata.use_default_schedule` flag | Backend synthesises Mon-Fri 09-18 rules when true | When all services have explicit availability rules |
| Backend `product.cost_price` field | Backward-read fallback by cost_resolver | When all products carry `cost_source` (Wave 1.6) |

---

## 6. Phase roadmap (consolidation plan)

| Phase | Status | What |
|---|---|---|
| **0** | ✅ done | Documented architecture (this file), added `@deprecated` JSDoc + telemetry on legacy Dialog |
| **1** | ✅ done | Cleanup of legacy `cost_price` from Dialog payload (Wave 1) |
| **2** | ✅ done | Integrated `CostSourceEditor` in 5 wizards + 5 dashboards (Wave 1 W1.S5) |
| **3** | ✅ done (PR-2) | Extracted `OccurrenceEditorPanel.jsx` from the legacy Dialog. Now a controlled component in `features/events/components/`. Currently has no caller — intentionally kept for a future "manage occurrences" surface |
| **4** | ✅ done (PR-4) | Removed legacy Dialog entirely, plus `openCreate`/`openEdit`/`handleSave` and all Dialog-only state. ProductsPage shrunk 1526 → ~705 LoC |
| **5** | optional, post-launch | Extract `useWizard()` / `useDashboardForm()` hooks across the 5 wizards (DRY refactor; pure cosmetics, no behaviour change) |
| **6** | data-driven | Remove `item_type='booking'` after prod query confirms 0 active products |

### Related cleanup PRs (this cycle)

- **PR-0** — Fixed `ProductProfileSlide` "Apri scheda prodotto" button to
  dispatch to per-type dashboards via `productDashboardPath()` instead
  of opening the legacy generic edit Dialog.
- **PR-3** — Migrated 4 call sites of the legacy Dialog (ProductCard
  `onEdit`, empty-state button, TypePicker fallback, deep-link
  `useEffect`) to per-type navigation. Renamed handlers to `_DEAD_*`
  as a compile-time guard against regressions before PR-4.

---

## 7. PR review checklist

When reviewing a PR that touches the products domain:

- [ ] Files modified live in their type's module (no cross-type imports)?
- [ ] Shared components added to `features/products/components/`?
- [ ] Any new field has `@deprecated since` comment if marked for removal?
- [ ] Any new Dialog avoided in favour of an explicit route?
- [ ] Cost section uses `CostSourceEditor`, not direct `cost_source` form fields?
- [ ] Wizard added follows R5 skeleton (TABS, validate, onSubmit, navigate)?
- [ ] Smoke test: for each product type, the wizard opens and a save persists?

---

## 8. API endpoint map (for reference)

| Endpoint | Caller | Module |
|---|---|---|
| `POST /api/products` | All 5 wizards (except Event) | `productsAPI.create` |
| `POST /api/event-occurrences/wizard` | EventWizard | `eventOccurrencesAPI.wizard` (atomic: product + occurrence + tiers) |
| `PATCH /api/products/:id` | All 5 dashboards | `productsAPI.update` |
| `GET /api/products/:id` | All 5 dashboards | `productsAPI.get` |
| `POST /api/products/:id/image` | PhysicalWizard, DigitalWizard | `productsAPI.uploadImage` |
| `POST /api/products/:id/digital-file` | DigitalWizard | `productsAPI.uploadDigitalFile` |
| `POST /api/products/:id/extras` | PhysicalWizard, ReservationWizard | `productExtrasAPI.create` |
| `POST /api/availability-rules` | ServiceWizard | `availabilityAPI.createRule` |
| `POST /api/service-options` | ServiceWizard | `serviceOptionsAPI.create` |
| `POST /api/modules/product-catalog/cost-preview` | (CostSourceEditor — not used in current minimal version) | `productCatalogAPI.previewCost` |

---

## 9. Open questions / known gaps

- **Hook extraction (Phase 5)**: worth the 3-day investment only if
  wizards keep changing post-launch. If they stabilise, it's pure
  cosmetics — defer.
- **Booking migration script**: `backend/scripts/migrate_booking_to_rental_slot.py`
  exists already. Run on production once business confirms cutover
  window.
- **EventsGrid + ServicesGrid use custom UI** (not `ProductCardBase`).
  Standardising would deduplicate ~200 lines but might lose
  type-specific affordances (occurrence badges, availability hints).
  Investigate post-launch.
