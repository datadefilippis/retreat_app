/**
 * SetupWizardDashboardCard — smart wrapper that mounts the setup wizard
 * widget inside the merchant dashboard (Fase 2 Track F — Step 8).
 *
 * Responsibilities:
 *   1. Fetch wizard data via the `useSetupWizard` hook.
 *   2. Persist a per-org "dismissed" flag in localStorage so users who
 *      explicitly remove the widget (typically after the setup is
 *      complete) don't see it reappear on every page reload.
 *   3. Render the pure presentational `SetupWizardWidget` with the right
 *      handlers wired in.
 *
 * Why a separate component (instead of mounting SetupWizardWidget
 * directly in DashboardPage):
 *   - Keeps DashboardPage.js untouched apart from a single import +
 *     mount line.
 *   - Encapsulates the dismiss-persistence concern; the widget itself
 *     stays pure-presentational (testable in isolation).
 *   - Makes it trivial to mount the same wizard elsewhere later (e.g.
 *     a /setup standalone page, an onboarding tour overlay) without
 *     duplicating the dismiss logic.
 *
 * Default state: visible for all orgs that haven't dismissed it.
 * Removal flow:
 *   user clicks "Rimuovi dalla dashboard" →
 *     localStorage.setItem('setup_wizard_dismissed:<org_id>', '1') →
 *     this component returns null on next render.
 *
 * To re-enable the widget on the same browser, the user (or admin)
 * deletes the localStorage entry. A "show wizard again" UI affordance
 * may come later if support tickets show it's needed.
 */

import React, { useCallback, useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSetupWizard } from './hooks/useSetupWizard';
import { SetupWizardWidget } from './widget/SetupWizardWidget';


// localStorage key prefix. Per-org so users with multiple orgs (rare but
// possible via session swap) keep dismiss state separate.
const DISMISS_KEY_PREFIX = 'setup_wizard_dismissed:';


function isDismissed(orgId) {
  if (!orgId || typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(DISMISS_KEY_PREFIX + orgId) === '1';
  } catch {
    return false;
  }
}


function setDismissed(orgId) {
  if (!orgId || typeof window === 'undefined') return;
  try {
    localStorage.setItem(DISMISS_KEY_PREFIX + orgId, '1');
  } catch {
    /* localStorage unavailable — best-effort, no fallback needed */
  }
}


export function SetupWizardDashboardCard() {
  const { user } = useAuth();
  const orgId = user?.organization_id;

  // Local UI state — toggled by the user clicking "remove" on the widget.
  // Initialized from localStorage so dismissals persist across reloads.
  const [dismissed, setDismissedState] = useState(() => isDismissed(orgId));

  // If the org changes (e.g. session swap), re-evaluate the dismiss flag.
  useEffect(() => {
    setDismissedState(isDismissed(orgId));
  }, [orgId]);

  // Only fetch when we actually have a user (auth ready) AND the user
  // hasn't dismissed the widget — avoids a useless API call.
  const enabled = !!user && !dismissed;
  const { data, loading, error, refresh } = useSetupWizard({ enabled });

  const handleRemove = useCallback(() => {
    setDismissed(orgId);
    setDismissedState(true);
  }, [orgId]);

  // Hidden states that render nothing:
  //   - user not loaded yet (auth still initialising)
  //   - user dismissed the widget
  //   - wizard returned null (org doesn't exist — defensive)
  if (!user) return null;
  if (dismissed) return null;

  return (
    <SetupWizardWidget
      data={data}
      loading={loading}
      error={error}
      onRefresh={refresh}
      onRemove={handleRemove}
      defaultExpanded={false}
    />
  );
}
