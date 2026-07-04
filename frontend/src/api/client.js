import axios from 'axios';

// Create axios instance
const api = axios.create({
  headers: {
    'Content-Type': 'application/json'
  }
});

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Set baseURL and fix URL on each request
api.interceptors.request.use((config) => {
  if (config.url && !config.url.startsWith('http')) {
    const path = config.url.startsWith('/api') ? config.url : `/api${config.url.startsWith('/') ? '' : '/'}${config.url}`;
    config.url = `${BACKEND_URL}${path}`;
  }

  delete config.baseURL;
  
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
});

// Handle auth errors (with dedup to avoid redirect storms)
let isRedirecting = false;
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !isRedirecting) {
      isRedirecting = true;
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    // v5.2: Surface READ_ONLY_GRACE 403 to the UI via custom event.
    // Backend returns { detail: { code: "READ_ONLY_GRACE", ... } } when
    // a downgraded org is in the 7-day read-only grace period.
    if (
      error.response?.status === 403 &&
      error.response?.data?.detail?.code === 'READ_ONLY_GRACE'
    ) {
      window.dispatchEvent(
        new CustomEvent('billing:read-only-grace', {
          detail: error.response.data.detail,
        })
      );
    }
    // v6.0: Surface blocking billing states (trial expired / past due beyond period).
    // These are non-dismissible — the user must resolve the billing issue.
    const billingCode = error.response?.data?.detail?.code;
    if (error.response?.status === 403 && billingCode === 'BILLING_TRIAL_EXPIRED') {
      window.dispatchEvent(
        new CustomEvent('billing:trial-expired', { detail: error.response.data.detail })
      );
    }
    if (error.response?.status === 403 && billingCode === 'BILLING_PAST_DUE') {
      window.dispatchEvent(
        new CustomEvent('billing:past-due', { detail: error.response.data.detail })
      );
    }
    // v5.8 / Onda 9.I — Surface module/feature access blocks as a paywall.
    // These fire when an org tries to use a module disabled in their plan
    // (e.g. Solo trying to create a store, Free trying to add a 51st product).
    // Without these dispatches the user sees a generic axios error with no
    // clue that they need to upgrade — these events let ModuleAccessPaywall
    // render a clear modal with an upgrade CTA.
    if (error.response?.status === 403 && billingCode === 'MODULE_NOT_AVAILABLE') {
      window.dispatchEvent(
        new CustomEvent('billing:module-not-available', { detail: error.response.data.detail })
      );
    }
    if (error.response?.status === 403 && billingCode === 'FEATURE_NOT_AVAILABLE') {
      window.dispatchEvent(
        new CustomEvent('billing:feature-not-available', { detail: error.response.data.detail })
      );
    }
    // Quota exceeded: surface 429 QUOTA_EXCEEDED to the UI via custom event.
    // Banner component listens for this and shows upgrade prompt.
    if (
      error.response?.status === 429 &&
      error.response?.data?.detail?.code === 'QUOTA_EXCEEDED'
    ) {
      window.dispatchEvent(
        new CustomEvent('billing:quota-exceeded', {
          detail: error.response.data.detail,
        })
      );
    }

    // v5.8 / Onda 9.O — Tag errors that have already been surfaced via a
    // global paywall/banner so per-component catch handlers can use
    // handleApiError() (frontend/src/utils/handleApiError.js) to skip
    // their local toast.error and avoid the "double notification" UX bug
    // where the user saw a generic red toast covering the explanatory
    // paywall.
    const code = error.response?.data?.detail?.code;
    const status = error.response?.status;
    const handledByPaywall =
      (status === 403 && (code === 'MODULE_NOT_AVAILABLE' || code === 'FEATURE_NOT_AVAILABLE'
                          || code === 'READ_ONLY_GRACE'
                          || code === 'BILLING_TRIAL_EXPIRED' || code === 'BILLING_PAST_DUE'))
      || (status === 429 && code === 'QUOTA_EXCEEDED');
    if (handledByPaywall) {
      // Mutate the error object — surviving through Promise.reject because
      // it's the same reference the catch block will receive.
      try { error.__handled_by_paywall = true; } catch (_) {}
    }

    return Promise.reject(error);
  }
);

export default api;
