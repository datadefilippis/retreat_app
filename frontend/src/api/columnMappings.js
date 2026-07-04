import api from './client';

export const columnMappingsAPI = {
  list: (datasetType) => {
    const params = datasetType ? { dataset_type: datasetType } : {};
    return api.get('/column-mappings', { params });
  },

  create: (data) =>
    api.post('/column-mappings', data),

  deactivate: (mappingId) =>
    api.delete(`/column-mappings/${mappingId}`),

  /**
   * Upsert a complete set of mappings for one dataset_type in a single call.
   *
   * @param {{ dataset_type: string, mappings: { source_column: string, target_field: string, transform?: string }[] }} data
   */
  saveBatch: (data) =>
    api.post('/column-mappings/batch', data),

  getProfile: (datasetId) =>
    api.get(`/column-mappings/profiles/${datasetId}`),
};
