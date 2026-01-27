import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
