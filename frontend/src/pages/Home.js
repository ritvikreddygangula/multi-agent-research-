import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { researchService } from '../services/researchService';
import AgentGraphView from '../components/AgentGraphView';
import HistorySidebar from '../components/HistorySidebar';
import './Home.css';

/**
 * Maps a live SSE event (agent + progress) to the exact node states that
 * should be shown on the graph at that moment.
 *
 * The backend streams three agents:
 *   planner    → progress 5-30
 *   research   → progress 32-65
 *   synthesizer→ progress 67-100
 *
 * We spread those across all 10 LangGraph nodes so every SSE event causes
 * at least one visible transition.
 */
function resolveNodeStates(agent, progress) {
  const s = {
    planner:      'pending',
    rag_retrieval:'pending',
    branch_0:     'pending',
    branch_1:     'pending',
    branch_2:     'pending',
    branch_3:     'pending',
    branch_4:     'pending',
    aggregator:   'pending',
    critic:       'pending',
    synthesizer:  'pending',
  };

  // ── Planner phase ──────────────────────────────────────────────────────
  if (progress >= 5)  s.planner       = progress >= 30 ? 'done' : 'running';

  // ── RAG retrieval ──────────────────────────────────────────────────────
  if (progress >= 30) s.rag_retrieval = progress >= 32 ? 'done' : 'running';

  // ── Parallel branches ──────────────────────────────────────────────────
  if (progress >= 32) {
    // All 5 branches start running together
    s.branch_0 = progress >= 42 ? 'done' : 'running';
    s.branch_1 = progress >= 47 ? 'done' : 'running';
    s.branch_2 = progress >= 52 ? 'done' : 'running';
    s.branch_3 = progress >= 57 ? 'done' : 'running';
    s.branch_4 = progress >= 62 ? 'done' : 'running';
  }

  // ── Aggregator ─────────────────────────────────────────────────────────
  if (progress >= 55) s.aggregator    = progress >= 65 ? 'done' : 'running';

  // ── Critic ─────────────────────────────────────────────────────────────
  if (progress >= 65) s.critic        = progress >= 67 ? 'done' : 'running';

  // ── Synthesizer ────────────────────────────────────────────────────────
  if (progress >= 67) s.synthesizer   = progress >= 95 ? 'done' : 'running';

  return s;
}

const Home = () => {
  const [topic, setTopic]               = useState('');
  const [loading, setLoading]           = useState(false);
  const [showPreview, setShowPreview]   = useState(false);
  const [progress, setProgress]         = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [nodeStatuses, setNodeStatuses] = useState({});
  const [resultData, setResultData]     = useState(null);
  const [sidebarOpen, setSidebarOpen]   = useState(false);

  const { logout, user } = useAuth();
  const navigate = useNavigate();

  // Navigate to results once we have data
  useEffect(() => {
    if (!resultData) return;
    const t = setTimeout(() => {
      navigate('/results', { state: { researchData: resultData } });
    }, 1500);
    return () => clearTimeout(t);
  }, [resultData, navigate]);

  // ── Submit ───────────────────────────────────────────────────────────────

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topic.trim()) { toast.error('Please enter a research topic'); return; }

    setLoading(true);
    setShowPreview(true);
    setProgress(0);
    setCurrentMessage('Connecting to research pipeline...');
    setNodeStatuses({ planner: 'running' });
    setResultData(null);

    try {
      const streamPromise = researchService.conductResearchStreaming(
        topic.trim(),

        // onProgress — synchronous, fires for every SSE event.
        // Drives graph state from the actual progress number.
        (update) => {
          if (!update) return;
          if (update.type !== 'progress' && update.type !== 'node_update') return;

          const p = update.progress || 0;
          setProgress(p);
          if (update.message) setCurrentMessage(update.message);
          setNodeStatuses(resolveNodeStates(update.agent || update.node || '', p));
        },

        // onComplete
        (result) => {
          setProgress(100);
          setCurrentMessage('Research complete.');
          setNodeStatuses({
            planner: 'done', rag_retrieval: 'done',
            branch_0: 'done', branch_1: 'done', branch_2: 'done',
            branch_3: 'done', branch_4: 'done',
            aggregator: 'done', critic: 'done', synthesizer: 'done',
          });
          toast.success('Research completed!', { icon: '✨' });
          setResultData(result);
        },

        // onError — fallback to non-streaming
        async (error) => {
          console.error('Streaming error:', error);
          if (error.message?.includes('fetch') || error.message?.includes('Network')) {
            toast.loading('Stream unavailable — falling back to standard mode...', { id: 'fb' });
            setCurrentMessage('Running in standard mode...');
            try {
              const response = await researchService.conductResearch(topic.trim());
              toast.dismiss('fb');
              setProgress(100);
              setCurrentMessage('Research complete.');
              setNodeStatuses({
                planner: 'done', rag_retrieval: 'done',
                branch_0: 'done', branch_1: 'done', branch_2: 'done',
                branch_3: 'done', branch_4: 'done',
                aggregator: 'done', critic: 'done', synthesizer: 'done',
              });
              toast.success('Research completed!', { icon: '✨' });
              setResultData(response.data);
            } catch (fbErr) {
              toast.dismiss('fb');
              toast.error(fbErr.response?.data?.error || 'Research failed.');
              setLoading(false);
              setShowPreview(false);
            }
          } else {
            toast.error(error.message || 'Research failed.');
            setLoading(false);
            setShowPreview(false);
          }
        }
      );

      await Promise.race([
        streamPromise,
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Stream timeout')), 300000)
        ),
      ]);

    } catch (err) {
      console.error('Research error:', err);
      toast.error(err.message || 'Research failed.');
      setLoading(false);
      setShowPreview(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="home-container">
      <header className="home-header">
        <div className="header-content">
          <h1 className="header-title">Research Platform</h1>
          <div className="header-actions">
            <button onClick={() => setSidebarOpen(true)} className="btn btn-secondary">
              History
            </button>
            <span className="user-email">{user?.email}</span>
            <button
              onClick={() => { toast.success('Logged out', { icon: '👋' }); logout(); }}
              className="btn btn-secondary"
              style={{ marginLeft: '16px' }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="home-main">
        <div className="home-content">
          <div className="welcome-section">
            <h2 className="welcome-title">What would you like to research?</h2>
            <p className="welcome-subtitle">
              Enter a topic and our AI research team will conduct a comprehensive analysis
            </p>
          </div>

          <form onSubmit={handleSubmit} className="research-form">
            <div className="input-wrapper">
              <textarea
                className="research-input"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., The impact of artificial intelligence on healthcare"
                rows={4}
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary research-submit"
              disabled={loading || !topic.trim()}
            >
              {loading
                ? <><span className="spinner" style={{ marginRight: '8px' }} />Researching...</>
                : 'Start Research'}
            </button>
          </form>

          {showPreview && (
            <AgentGraphView
              nodeStatuses={nodeStatuses}
              progress={progress}
              currentMessage={currentMessage}
            />
          )}
        </div>
      </main>

      <HistorySidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
    </div>
  );
};

export default Home;
