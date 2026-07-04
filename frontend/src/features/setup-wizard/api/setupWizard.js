/**
 * Setup Wizard API client (Fase 2 Track F — Step 6).
 *
 * Thin wrapper over the shared axios instance. Single endpoint:
 *
 *   GET /api/setup/wizard
 *     Returns SetupWizardResponse (see backend
 *     services/setup_wizard/step_models.py).
 *
 * The endpoint is read-only and idempotent — safe to call repeatedly.
 *
 * Auth: relies on the JWT cookie/header attached automatically by the
 * shared `api` client interceptor. No special handling here.
 */

import api from '../../../api/client';


export const setupWizardAPI = {
  /**
   * Fetch the personalized wizard payload for the current org.
   *
   * @returns Promise<AxiosResponse<SetupWizardResponse>>
   *
   * Backend returns:
   *   {
   *     org_id, plan_slug, plan_name_key, active_modules,
   *     sections: [{ module_key, title_key, steps: [...], done_count, total_count }],
   *     progress_pct, next_step_key, is_complete
   *   }
   */
  get: () => api.get('/setup/wizard'),
};
