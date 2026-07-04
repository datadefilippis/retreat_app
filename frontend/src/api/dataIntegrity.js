import api from './client';

export const dataIntegrityAPI = {
  getCoverage: () => api.get('/data-integrity/coverage'),
  relink: (datasetType, dryRun = true) =>
    api.post('/data-integrity/relink', { dataset_type: datasetType, dry_run: dryRun }),
};
