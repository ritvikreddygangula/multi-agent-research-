import api from './authService';

export const researchService = {
  async conductResearch(topic) {
    return api.post('/api/research/', { topic });
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
      const token = sessionStorage.getItem('token');
      if (!token) {
        const error = new Error('No authentication token found');
        if (onError) onError({ message: error.message, error: error });
        reject(error);
        return;
      }

      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const url = `${baseUrl}/api/research/stream/`;

      console.log('🚀 Starting streaming research for topic:', topic);
      
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
          console.log('📥 Response received:', response.status, response.statusText);
          console.log('📥 Content-Type:', response.headers.get('content-type'));
          
          if (!response.ok) {
            // Try to parse as JSON, fallback to status text
            return response.text().then(text => {
              console.error('❌ Response not OK:', text);
              try {
                const err = JSON.parse(text);
                throw new Error(err.error || `HTTP error! status: ${response.status}`);
              } catch {
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
              }
            });
          }
          
          // Check if response is actually SSE
          const contentType = response.headers.get('content-type');
          console.log('📥 Content-Type check:', contentType);
          
          if (!contentType || !contentType.includes('text/event-stream')) {
            console.warn('⚠️ Not SSE format, but continuing anyway. Content-Type:', contentType);
            // Don't throw, just continue - some servers don't set content-type correctly
          }
          
          if (!response.body) {
            throw new Error('Response body is null - cannot read stream');
          }
          
          console.log('✅ Starting to read stream...');
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const readStream = () => {
            reader.read().then(({ done, value }) => {
              if (done) {
                console.log('✅ Stream completed');
                if (buffer.trim()) {
                  console.log('⚠️ Remaining buffer:', buffer);
                }
                resolve();
                return;
              }

              const chunk = decoder.decode(value, { stream: true });
              console.log('📦 Received chunk:', chunk.substring(0, 100) + '...');
              buffer += chunk;
              
              // Process complete lines
              const lines = buffer.split('\n');
              buffer = lines.pop() || ''; // Keep incomplete line in buffer

              for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine) continue; // Skip empty lines
                
                if (trimmedLine.startsWith('data: ')) {
                  try {
                    const jsonStr = trimmedLine.slice(6).trim();
                    if (!jsonStr) {
                      console.log('⚠️ Empty data line');
                      continue;
                    }
                    
                    const data = JSON.parse(jsonStr);
                    console.log('📡 Received SSE update:', data);
                    
                    if (data.type === 'error') {
                      console.error('❌ SSE Error:', data);
                      if (onError) onError(data);
                      reject(new Error(data.message || data.error));
                      return;
                    } else if (data.type === 'complete') {
                      console.log('✅ SSE Complete:', data);
                      if (onComplete) onComplete(data);
                      resolve(data);
                      return;
                    } else if (data.type === 'progress' || data.type === 'node_update') {
                      // node_update events from LangGraph streaming include compat
                      // fields (agent, status, message, progress) set by the backend.
                      // Called synchronously (no setTimeout) so that all node_update
                      // state updates are batched BEFORE onComplete fires.
                      console.log('📊 SSE Progress/NodeUpdate:', data.type, data.node || data.agent, data.progress);
                      if (onProgress) onProgress(data);
                    } else {
                      console.log('⚠️ Unknown update type:', data.type);
                    }
                  } catch (e) {
                    console.error('❌ Error parsing SSE data:', e);
                    console.error('❌ Problematic line:', trimmedLine);
                  }
                } else if (trimmedLine.startsWith(':')) {
                  // SSE comment, ignore
                  continue;
                } else {
                  console.log('⚠️ Non-data line:', trimmedLine);
                }
              }

              // Continue reading
              readStream();
            }).catch(err => {
              console.error('❌ Stream read error:', err);
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
