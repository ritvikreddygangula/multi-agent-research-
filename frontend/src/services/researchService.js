import api from './authService';

export const researchService = {
  async conductResearch(topic) {
    return api.post('/api/research/', { topic });
  },
};
