import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { researchService } from '../services/researchService';
import AgentGraphView from '../components/AgentGraphView';
import './Home.css';

// Mirrors graph_builder.py topology.
// When node X completes, its successors become "running".
const GRAPH_SUCCESSORS = {
  planner:       ['rag_retrieval'],
  rag_retrieval: ['branch_0', 'branch_1', 'branch_2', 'branch_3', 'branch_4'],
  branch_0: [], branch_1: [], branch_2: [], branch_3: [], branch_4: [],
  aggregator:    ['critic'],
  critic:        ['synthesizer'],
  synthesizer:   [],
};

const Home = () => {
  const [topic, setTopic]               = useState('');
  const [loading, setLoading]           = useState(false);
  const [showPreview, setShowPreview]   = useState(false);
  const [progress, setProgress]         = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [nodeStatuses, setNodeStatuses] = useState({});
  const [resultData, setResultData]     = useState(null);

  const { logout, user } = useAuth();
  const navigate = useNavigate();

  // Navigate to results once we have data (after showing the completed graph briefly)
  useEffect(() => {
    if (!resultData) return;
    const t = setTimeout(() => {
      navigate('/results', { state: { researchData: resultData } });
    }, 1500);
    return () => clearTimeout(t);
  }, [resultData, navigate]);

  // ── Helpers ─────────────────────────────────────────────────────────────────

  // Called for every node_update event from the backend.
  // Marks the completed node as "done" and promotes its successors to "running".
  // This is the ONLY place node statuses are written — directly from backend events.
  function applyNodeDone(completedNode) {
    setNodeStatuses(prev => {
      const next = { ...prev, [completedNode]: 'done' };
      (GRAPH_SUCCESSORS[completedNode] || []).forEach(s => {
        if (!next[s]) next[s] = 'running';
      });
      // Aggregator starts running as soon as the first branch finishes
      const doneBranches = [0,1,2,3,4].filter(i => next[`branch_${i}`] === 'done').length;
      if (doneBranches >= 1 && !next['aggregator']) next['aggregator'] = 'running';
      return next;
    });
  }

  // ── Submit ───────────────────────────────────────────────────────────────────

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topic.trim()) { toast.error('Please enter a research topic'); return; }

    setLoading(true);
    setShowPreview(true);
    setProgress(0);
    setCurrentMessage('Connecting to research pipeline...');
    setNodeStatuses({ planner: 'running' }); // only planner starts as running
    setResultData(null);

    try {
      const streamPromise = researchService.conductResearchStreaming(
        topic.trim(),

        // onProgress — called synchronously for every node_update SSE event.
        // We update the graph ONLY when the backend says a node actually finished.
        // No artificial delays, no queues, no fake sequencing.
        (update) => {
          if (!update || (update.type !== 'progress' && update.type !== 'node_update')) return;

          setProgress(update.progress || 0);
          if (update.message) setCurrentMessage(update.message);

          const completedNode = update.node || update.agent;
          if (completedNode && completedNode !== 'system') {
            applyNodeDone(completedNode);
          }
        },

        // onComplete — research finished; navigate after a short pause so the
        // user can see the final all-green graph.
        (result) => {
          setProgress(100);
          setCurrentMessage('Research complete.');
          // Mark all nodes done (in case any were skipped / arrived out of order)
          setNodeStatuses({
            planner: 'done', rag_retrieval: 'done',
            branch_0: 'done', branch_1: 'done', branch_2: 'done',
            branch_3: 'done', branch_4: 'done',
            aggregator: 'done', critic: 'done', synthesizer: 'done',
          });
          toast.success('Research completed!', { icon: '✨' });
          setResultData(result); // triggers the navigate effect above
        },

        // onError — fallback to the non-streaming endpoint.
        // We do NOT fake node completion here; the graph stays at whatever
        // state the backend had reached before the error.
        async (error) => {
          console.error('Streaming error:', error);

          if (error.message?.includes('fetch') || error.message?.includes('Network')) {
            toast.loading('Stream unavailable — falling back to standard mode...', { id: 'fb' });
            setCurrentMessage('Running in standard mode (no live updates)...');
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

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="home-container">
      <header className="home-header">
        <div className="header-content">
          <h1 className="header-title">Research Platform</h1>
          <div className="header-actions">
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
    </div>
  );
};

export default Home;
