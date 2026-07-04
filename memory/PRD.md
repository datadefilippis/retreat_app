# AFianco - Product Requirements Document

## Original Problem Statement
Build a complete SaaS web application called AFianco - an AI-assisted monitoring system for business performance. Companies upload data, activate analysis modules, and receive KPI dashboards, charts, anomaly alerts, and AI explanations. MVP focuses on Daily Cashflow Monitor module using sales and expenses data.

## User Choices
- **AI Provider**: Anthropic Claude via Anthropic SDK
- **Authentication**: JWT-based custom auth (email/password)
- **Storage**: Local file storage for MVP
- **Demo Data**: Pre-populated with realistic restaurant data
- **Design**: Professional enterprise SaaS aesthetic

## Architecture

### Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: Anthropic Claude via Anthropic SDK

### Multi-Tenant Architecture
- Organization-level data isolation
- Role-based access control (Admin, User)
- JWT authentication with secure password hashing

### Code Architecture (Post-Refactoring)
```
/app/backend/
├── models/           # Pydantic models split by entity
├── repositories/     # MongoDB query layer
├── services/         # Business logic (auth, alerts, insights, datasets)
├── routers/          # API endpoints (auth, datasets, modules, alerts, insights)
├── modules/          # Modular feature system
│   ├── __init__.py   # ModuleRegistry
│   ├── base.py       # BaseModule abstract class
│   └── cashflow_monitor/  # First module implementation
│       ├── config.py      # MODULE_KEY, MODULE_NAME, etc.
│       ├── router.py      # Analytics endpoints
│       └── service.py     # Analytics logic
└── server.py         # FastAPI app

/app/frontend/src/
├── api/              # API client files split by feature
├── features/         # Feature-based page organization
│   ├── dashboard/
│   ├── cashflow/
│   ├── datasets/
│   ├── alerts/
│   ├── insights/
│   ├── team/
│   └── settings/
├── pages/            # Landing & Auth pages only
├── components/       # Shared UI components
└── context/          # React context (Auth)
```

### Modular System
- ModuleRegistry pattern for scalability
- BaseAnalysisModule structure
- CashflowMonitorModule as first implementation

## User Personas

### Admin
- Manage team members
- Upload datasets
- Activate/deactivate modules
- View all dashboards, alerts, insights
- Update organization settings

### User/Analyst
- View dashboards and analytics
- View alerts and insights
- Upload datasets (if permitted)

## Core Requirements

### Implemented Features
- [x] Multi-tenant organization management
- [x] JWT authentication (signup/login)
- [x] CSV upload for sales and expenses
- [x] XLSX/XLS file upload support (NEW)
- [x] Smart data parsing (multi-format dates, currency symbols, EU/US numbers)
- [x] Data validation and parsing
- [x] Daily cashflow calculations
- [x] KPI dashboard with 6 metrics
- [x] Charts (sales trend, expenses trend, net cashflow, comparisons)
- [x] Category breakdown charts (Pie and Bar) (NEW)
- [x] 7-day moving averages
- [x] Anomaly detection (10%/20%/30% thresholds)
- [x] Alert generation and management
- [x] AI explanation layer via GPT-4o
- [x] Date filtering (7d/30d/90d)
- [x] Team management
- [x] Dataset download functionality (NEW)
- [x] Audit logging
- [x] Demo data seeding

### Pages Implemented
1. Landing page
2. Login page
3. Signup page
4. Dashboard
5. Cashflow Monitor module
6. Upload Data page
7. Datasets page
8. Modules page
9. Alerts page
10. Insights page
11. Team page
12. Settings page

## Implementation History

### March 7, 2026 - MVP Complete
- Created complete backend with FastAPI
- Implemented MongoDB models and indexes
- Built authentication system with JWT
- Created dataset upload with CSV validation
- Implemented analytics calculations (KPIs, aggregations)
- Built anomaly detection algorithm
- Integrated AI explanations via Anthropic Claude
- Created responsive frontend with Shadcn UI
- Built all 12 pages with proper routing
- Added demo data seeding for restaurant
- Fixed router endpoint trailing slash issue

### March 7, 2026 - Feature Enhancement
- Added XLSX/XLS file upload support (openpyxl, xlrd)
- Implemented smart parsing: multi-format dates, currency symbols ($€£), EU/US number formats
- Added dataset download functionality with original file preservation
- Added category breakdown analytics endpoints (sales/expenses by category)
- Added "By Category" tab in Cashflow Module with PieChart and BarChart visualizations
- Backend: 100% tests passed
- Frontend: All features working

### March 8, 2026 - Major Code Refactoring
- **STEP 1**: Split `models.py` into `backend/models/` package with separate files per entity
- **STEP 2**: Created `backend/repositories/` layer for MongoDB queries isolation
- **STEP 3**: Created `backend/services/` for business logic (auth, alerts, insights, datasets)
- **STEP 4**: Refactored routers to use services and repositories (clean separation of concerns)
- **STEP 5**: Created modular system with `backend/modules/` and ModuleRegistry for auto-discovery
  - Moved analytics from `routers/analytics.py` to `modules/cashflow_monitor/`
  - Module registry pattern for scalability
- **STEP 6**: Restructured frontend:
  - Created `frontend/src/api/` with separate API client files
  - Moved pages to `frontend/src/features/` (dashboard, cashflow, datasets, alerts, insights, team, settings)
  - Maintained backwards compatibility via re-exports
- All functionality preserved and working

## Prioritized Backlog

### P0 - Critical (MVP Done)
- [x] Core authentication
- [x] Data upload and validation
- [x] KPI calculations
- [x] Charts and visualizations
- [x] Anomaly detection
- [x] AI insights generation

### P1 - High Priority (Next Phase)
- [ ] Custom date range picker
- [ ] Export reports to PDF
- [ ] Email notifications for alerts
- [ ] User profile editing
- [ ] Password reset flow

### P2 - Medium Priority
- [x] Category breakdown charts (DONE)
- [ ] Trend forecasting
- [ ] Comparative analysis (vs industry)
- [ ] Dashboard customization
- [ ] Bulk data import

### P3 - Low Priority
- [ ] ERP integrations
- [ ] POS integrations
- [ ] Mobile responsive optimizations
- [ ] Advanced ML models
- [ ] Billing system

## Next Tasks
1. Add custom date range picker with calendar
2. Implement email notifications for critical alerts
3. Add data export functionality
4. Build user profile editing
5. Consider adding revenue forecasting module

## API Endpoints

### Authentication
- POST /api/auth/signup
- POST /api/auth/login
- GET /api/auth/me

### Organizations
- GET /api/organizations/current
- PUT /api/organizations/current
- GET /api/organizations/team
- POST /api/organizations/team/invite
- PUT /api/organizations/team/{user_id}/role
- DELETE /api/organizations/team/{user_id}

### Datasets
- GET /api/datasets
- POST /api/datasets/upload
- GET /api/datasets/{id}
- GET /api/datasets/{id}/preview
- GET /api/datasets/{id}/download (NEW)
- DELETE /api/datasets/{id}

### Analytics
- GET /api/analytics/kpis
- GET /api/analytics/charts
- GET /api/analytics/summary
- GET /api/analytics/categories/sales (NEW)
- GET /api/analytics/categories/expenses (NEW)
- GET /api/analytics/categories/trends (NEW)

### Modules
- GET /api/modules/available
- GET /api/modules/active
- POST /api/modules/{key}/activate
- POST /api/modules/{key}/deactivate
- GET /api/modules/{key}/status

### Alerts
- GET /api/alerts
- GET /api/alerts/count
- GET /api/alerts/{id}
- PUT /api/alerts/{id}/status
- POST /api/alerts/generate

### Insights
- GET /api/insights
- GET /api/insights/latest
- POST /api/insights/generate
- GET /api/insights/{id}

## Demo Credentials
- Email: admin@demo.com
- Password: demo123
