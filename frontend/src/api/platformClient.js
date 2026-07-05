/**
 * platformApi — client dedicato al Passaporto Ritiri (P3).
 *
 * SEPARATO da api/client.js di proposito: quello inietta il token ADMIN
 * (localStorage 'token') su ogni richiesta e redirige a /login su 401 —
 * comportamenti giusti per la dashboard operatore, sbagliati per le
 * pagine pubbliche /account (un utente finale non deve mai finire sul
 * login admin). Qui: token piattaforma, niente redirect globali (il 401
 * lo gestiscono le pagine).
 */
import axios from 'axios';

export const PLATFORM_TOKEN_KEY = 'platform_token';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const platformApi = axios.create();

platformApi.interceptors.request.use((config) => {
  if (config.url && !config.url.startsWith('http')) {
    const path = config.url.startsWith('/api')
      ? config.url
      : `/api${config.url.startsWith('/') ? '' : '/'}${config.url}`;
    config.url = `${BACKEND_URL}${path}`;
  }
  delete config.baseURL;

  const token = localStorage.getItem(PLATFORM_TOKEN_KEY);
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default platformApi;
