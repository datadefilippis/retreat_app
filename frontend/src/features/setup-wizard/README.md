# Setup Wizard — Frontend (Fase 2 Track F)

Self-contained React module that renders the dynamic onboarding wizard
in the dashboard.

## Folders

| Folder | Role |
|---|---|
| `widget/`   | Pure presentational React components |
| `hooks/`    | Data-fetching hook (`useSetupWizard`) — added in Step 6 |
| `api/`      | Axios wrapper for `GET /api/setup/wizard` — added in Step 6 |
| `lib/`      | Helpers (icon mapping, CTA resolver) |

## Public API (consumer surface)

The module exposes ONE public component:

```jsx
import { SetupWizardWidget } from 'features/setup-wizard/widget/SetupWizardWidget';

<SetupWizardWidget
  data={wizardResponse}     // SetupWizardResponse from /api/setup/wizard
  loading={false}           // shows skeleton when true
  error={null}              // shows retry banner when set
  onRefresh={() => ...}     // refresh button handler
  onRemove={() => ...}      // optional "remove from dashboard" handler
  defaultExpanded={true}    // initial collapsed/expanded state
/>
```

Everything else is internal.

## Design rules

- **No API calls inside components**: data flows in via props from the
  hook (`useSetupWizard` in Step 6). Components are pure. Easy to test.
- **i18n-first**: every user-visible string comes from
  `t('key', { ns: 'setup_wizard' })`. Hardcoded copy is a bug.
- **No hardcoded plan logic**: components don't know about plan slugs.
  They render whatever sections/steps the backend tells them to.
- **Multi-CTA aware**: a step may have 1, 2, or 3 CTAs (manual / import /
  configure). The first is primary, others secondary/ghost.
- **Self-contained styling**: imports only `components/ui/*` (shadcn) and
  `lucide-react`. No global CSS, no module-scoped CSS.

## Component graph

```
SetupWizardWidget
├── SetupProgressBar (header, always visible)
├── (collapsed view) — single-line "next step" pointer
└── (expanded view)
    └── SetupSectionGroup × N
        └── SetupStepRow × M
            └── SetupStepCTAs (1-3 buttons)
```

## Adding a new icon

If you add a new step with `icon_key="something-new"`, register the mapping in
`lib/stepIcons.js` so the icon renders. Unknown icons silently fall back to
the generic `Circle` icon — the widget never breaks on missing icons.

## Adding a new translation language

Drop `frontend/public/locales/<lang>/setup_wizard.json`. The widget will pick
it up automatically via the i18n config (no code change needed).

## Step rollout (current state)

- ✅ Step 4 — components scaffold (this folder)
- ⏳ Step 5 — i18n files
- ⏳ Step 6 — useSetupWizard hook + API client
- ⏳ Step 7 — multi-CTA refinements
- ⏳ Step 8 — register in dashboard widgetRegistry + auto-pin
