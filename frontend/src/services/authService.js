import axios from 'axios';

const API_BASE_URL = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');

// Safe storage: falls back to in-memory when sessionStorage is blocked
// (e.g. browser privacy mode or enhanced tracking protection)
const _memoryStore = {};
export const safeStorage = {
  getItem: (key) => {
    try { return sessionStorage.getItem(key); } catch { return _memoryStore[key] ?? null; }
  },
  setItem: (key, value) => {
    try { sessionStorage.setItem(key, value); } catch { _memoryStore[key] = value; }
  },
  removeItem: (key) => {
    try { sessionStorage.removeItem(key); } catch { delete _memoryStore[key]; }
  },
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const authService = {
  setAuthToken(token) {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  },

  async login(email, password) {
    return api.post('/api/auth/login/', { email, password });
  },

  async signup(email, username, password, passwordConfirm) {
    return api.post('/api/auth/signup/', {
      email,
      username,
      password,
      password_confirm: passwordConfirm,
    });
  },
};

export default api;
