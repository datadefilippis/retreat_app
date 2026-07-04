import api from './client';

export const datasetsAPI = {
  list: (datasetType) => {
    const params = datasetType ? `?dataset_type=${datasetType}` : '';
    return api.get(`/datasets${params}`);
  },

  get: (id) => api.get(`/datasets/${id}`),

  preview: (id, limit = 20) => api.get(`/datasets/${id}/preview?limit=${limit}`),

  upload: (file, name, datasetType, confirmDuplicate = false, skipDuplicateRows = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('dataset_type', datasetType);
    if (confirmDuplicate) formData.append('confirm_duplicate', 'true');
    if (skipDuplicateRows) formData.append('skip_duplicate_rows', 'true');
    return api.post('/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  /**
   * Complete an upload with user-provided column mapping.
   * Called after a 422 response from upload() with status='needs_column_mapping'.
   *
   * @param {string} tempUploadId — ID from the 422 response detail
   * @param {Object} columnMapping — { fileColumn: targetField, ... }
   * @param {boolean} saveMapping — persist mapping for future uploads
   */
  uploadWithMapping: (tempUploadId, columnMapping, saveMapping = false, confirmDuplicate = false, skipDuplicateRows = false) => {
    const formData = new FormData();
    formData.append('temp_upload_id', tempUploadId);
    formData.append('column_mapping', JSON.stringify(columnMapping));
    formData.append('save_mapping', saveMapping);
    if (confirmDuplicate) formData.append('confirm_duplicate', 'true');
    if (skipDuplicateRows) formData.append('skip_duplicate_rows', 'true');
    return api.post('/datasets/upload-with-mapping', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  download: (id) => {
    const protocol = window.location.protocol;
    const host = window.location.host;
    const token = localStorage.getItem('token');
    return `${protocol}//${host}/api/datasets/${id}/download?token=${token}`;
  },

  /** Toggle a dataset's active/inactive status */
  toggleActive: (id) => api.patch(`/datasets/${id}/toggle-active`),

  delete: (id) => api.delete(`/datasets/${id}`)
};
