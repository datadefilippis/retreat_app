import React, { createContext, useCallback, useContext, useMemo, useState, useEffect } from 'react';
import axios from 'axios';
import i18n from '../i18n';

const getApiUrl = () => process.env.REACT_APP_BACKEND_URL || '';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/** Shortcut: returns the org currency code (e.g. "EUR", "USD"). */
export const useCurrency = () => {
  const { user } = useAuth();
  return user?.currency || 'EUR';
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Check auth status on mount.
  // Uses raw axios with an explicit Authorization header so that:
  //  - auth calls are self-contained and don't rely on global axios state
  //  - the api instance (client.js) remains the single owner for feature calls
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const apiUrl = getApiUrl();
          const response = await axios.get(`${apiUrl}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setUser(response.data);
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  // Sync i18n language when user locale changes (after login, auth check, or refreshUser).
  //
  // Storefront / customer-portal routes are EXCLUDED from this writer:
  // those surfaces have their own locale resolvers (`useStorefrontLocaleSync`
  // for /s, /e, /p, /co, /r, /ph, /dg, /t, /b, /d, /rsv and customer auth;
  // CustomerAuthContext for /account/*) which read from the merchant's
  // store config or the customer's own profile rather than the admin's
  // user.locale. Without this gate, an admin who's logged in and opens
  // their storefront in the same tab would see the storefront painted in
  // the admin language regardless of the merchant's configured primary —
  // because AuthContext's effect (parent in the tree) fires AFTER the
  // resolver bridge's effect (child) and overwrites the corrected lang.
  useEffect(() => {
    if (!user?.locale) return;
    if (i18n.language === user.locale) return;
    // Cheap pathname check — runs only when this effect fires, which is
    // already rate-limited to user.locale changes (≤1 per session).
    if (typeof window !== 'undefined') {
      const path = window.location.pathname || '';
      // Match a public storefront route — REQUIRES a path segment after
      // the route prefix (e.g. `/s/<slug>`, `/co/<slug>/<product>`),
      // not just the bare `/s` or `/p`. The latter aren't routed
      // anywhere in App.js but the precision here keeps the gate tight
      // and avoids accidentally swallowing future admin routes that
      // happen to start with the same letter.
      const isStorefrontRoute = /^\/(?:s|e|p|co|r|ph|dg|t|b|d|rsv)\/[^/]+/.test(path);
      const isCustomerArea = /^\/account(?:\/|$)/.test(path);
      if (isStorefrontRoute || isCustomerArea) return;
    }
    i18n.changeLanguage(user.locale);
  }, [user?.locale]);

  const login = useCallback(async (email, password) => {
    const apiUrl = getApiUrl();
    const response = await axios.post(`${apiUrl}/api/auth/login`, {
      email,
      password
    });

    const { access_token, user: userData } = response.data;
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);

    return userData;
  }, []);

  const signup = useCallback(async (email, password, name, organizationName, inviteToken, acceptedTerms, locale, website) => {
    const apiUrl = getApiUrl();
    const payload = {
      email,
      password,
      name,
      organization_name: organizationName,
      accepted_terms: acceptedTerms || false,
    };
    if (inviteToken) payload.invite_token = inviteToken;
    if (locale) payload.locale = locale;
    // Track O Step 5.1 — honeypot anti-bot field (corresponds to
    // hidden input in SignupPage). Always send the value (even empty
    // string for humans) so backend can validate consistently.
    // See backend/core/honeypot.py for the threat model.
    if (website !== undefined && website !== null) {
      payload.website = website;
    }
    const response = await axios.post(`${apiUrl}/api/auth/signup`, payload);

    // v6.0: Backend returns 202 with status=verification_required for open signups
    if (response.status === 202 || response.data?.status === 'verification_required') {
      return 'verification_required';
    }

    const { access_token, user: userData } = response.data;
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);

    return userData;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  }, []);

  /**
   * Re-fetch /api/auth/me and update the user state.
   * Call this after actions that change user fields (e.g. must_change_password cleared
   * after a successful password change in SettingsPage).
   */
  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) return;
    try {
      const apiUrl = getApiUrl();
      const response = await axios.get(`${apiUrl}/api/auth/me`, {
        headers: { Authorization: `Bearer ${storedToken}` },
      });
      setUser(response.data);
    } catch (error) {
      console.error('refreshUser failed:', error);
    }
  }, []);

  const value = useMemo(() => ({
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    signup,
    logout,
    refreshUser,
  }), [user, token, loading, login, signup, logout, refreshUser]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
