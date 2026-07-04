import React from "react";
import ReactDOM from "react-dom/client";
// Phase 1 Step A2 — Sentry init via side-effect import. MUST be the first
// app-internal import so Sentry is set up before i18n / smartToast / App
// run, capturing any errors that occur during their initialization.
// Opt-in via REACT_APP_SENTRY_DSN env var; if unset, this is a noop.
import "@/observability";
import "@/index.css";
import "@/i18n"; // Initialize i18next before App renders
import { installSmartToast } from "@/lib/smartToastInit";
import App from "@/App";

// v5.8 / Onda 9.X — Install smart toast.error wrapper before any component
// renders. Catches every existing `toast.error(error.response?.data?.detail)`
// call across the codebase and:
//   - Suppresses the toast for billing codes (paywall handles those)
//   - Coerces dict payloads to string (avoids "[object Object]")
// Single point of control — no need to refactor 40+ catch blocks individually.
installSmartToast();

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
