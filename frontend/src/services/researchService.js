import api, { safeStorage } from './authService';

export const researchService = {
  async conductResearch(topic) {
    return api.post('/api/research/', { topic });
  },

  async getHistory() {
    return api.get('/api/research/history/');
  },

  async getHistoryItem(id) {
    return api.get(`/api/research/history/${id}/`);
  },

  async renameHistoryItem(id, topic) {
    return api.patch(`/api/research/history/${id}/`, { topic });
  },

  async deleteHistoryItem(id) {
    return api.delete(`/api/research/history/${id}/`);
  },


  /**
   * Conduct research with streaming updates using Server-Sent Events
   * @param {string} topic - Research topic
   * @param {Function} onProgress - Callback for progress updates
   * @param {Function} onComplete - Callback for final result
   * @param {Function} onError - Callback for errors
   * @returns {Promise} Promise that resolves when stream completes
   */
  async conductResearchStreaming(topic, onProgress, onComplete, onError) {
    return new Promise((resolve, reject) => {
      const token = safeStorage.getItem('token');
      if (!token) {
        const error = new Error('No authentication token found');
        if (onError) onError({ message: error.message, error: error });
        reject(error);
        return;
      }

      const baseUrl = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');
      const url = `${baseUrl}/api/research/stream/`;

      console.log('Starting streaming research for topic:', topic);

      // Use fetch with POST for SSE (EventSource doesn't support POST)
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
        body: JSON.stringify({ topic }),
      })
        .then(response => {
          console.log('Response received:', response.status, response.statusText);

          if (!response.ok) {
            return response.text().then(text => {
              console.error('Response not OK:', text);
              try {
                const err = JSON.parse(text);
                throw new Error(err.error || `HTTP error! status: ${response.status}`);
              } catch {
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
              }
            });
          }

          if (!response.body) {
            throw new Error('Response body is null - cannot read stream');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let completedCleanly = false;

          const readStream = () => {
            reader.read().then(({ done, value }) => {
              if (done) {
                console.log('Stream completed');
                if (!completedCleanly) {
                  const err = new Error('Research stream closed before completing. The request may have timed out — please try again.');
                  if (onError) onError({ message: err.message, error: err });
                  reject(err);
                } else {
                  resolve();
                }
                return;
              }

              const chunk = decoder.decode(value, { stream: true });
              buffer += chunk;

              // Process complete lines
              const lines = buffer.split('\n');
              buffer = lines.pop() || ''; // Keep incomplete line in buffer

              for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine) continue;

                if (trimmedLine.startsWith('data: ')) {
                  try {
                    const jsonStr = trimmedLine.slice(6).trim();
                    if (!jsonStr) continue;

                    const data = JSON.parse(jsonStr);

                    if (data.type === 'error') {
                      console.error('SSE Error:', data);
                      if (onError) onError(data);
                      reject(new Error(data.message || data.error));
                      return;
                    } else if (data.type === 'complete') {
                      console.log('SSE Complete');
                      completedCleanly = true;
                      if (onComplete) onComplete(data);
                      resolve(data);
                      return;
                    } else if (data.type === 'progress' || data.type === 'node_update') {
                      // node_update events from LangGraph streaming include compat
                      // fields (agent, status, message, progress) set by the backend.
                      // Called synchronously (no setTimeout) so that all node_update
                      // state updates are batched BEFORE onComplete fires.
                      if (onProgress) onProgress(data);
                    } else {
                      console.log('Unknown update type:', data.type);
                    }
                  } catch (e) {
                    console.error('Error parsing SSE data:', e);
                  }
                } else if (trimmedLine.startsWith(':')) {
                  // SSE comment, ignore
                  continue;
                }
              }

              // Continue reading
              readStream();
            }).catch(err => {
              console.error('Stream read error:', err);
              if (onError) onError({ message: err.message, error: err });
              reject(err);
            });
          };

          readStream();
        })
        .catch(err => {
          console.error('Fetch error:', err);
          const errorMessage = err.message || 'Network error. Please check if the backend server is running.';
          if (onError) onError({ message: errorMessage, error: err });
          reject(new Error(errorMessage));
        });
    });
  },
};
