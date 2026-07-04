import api from './client';

export const validationRulesAPI = {
  /**
   * List validation rules, optionally filtered by dataset_type.
   * @param {string} [datasetType] - "sales" | "expenses" | "purchases"
   */
  list: (datasetType) => {
    const params = datasetType ? { dataset_type: datasetType } : {};
    return api.get('/validation-rules', { params });
  },

  /**
   * Create a new validation rule.
   * @param {{ dataset_type, field_name, rule_type, rule_value?, error_message?, is_active? }} data
   */
  create: (data) =>
    api.post('/validation-rules', data),

  /**
   * Partially update a rule (is_active, rule_value, error_message).
   * @param {string} ruleId
   * @param {{ is_active?: boolean, rule_value?: any, error_message?: string }} data
   */
  update: (ruleId, data) =>
    api.patch(`/validation-rules/${ruleId}`, data),

  /**
   * Hard-delete a validation rule.
   * @param {string} ruleId
   */
  delete: (ruleId) =>
    api.delete(`/validation-rules/${ruleId}`),
};
