import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { researchService } from '../services/researchService';
import './History.css';

function ConfidencePill({ score }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const cls = pct >= 75 ? 'high' : pct >= 50 ? 'mid' : 'low';
  return <span className={`h-confidence h-confidence--${cls}`}>{pct}%</span>;
}

function HistoryCard({ run, onDelete, onRename, onOpen }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(run.topic);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitRename = async () => {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === run.topic) { setEditing(false); setDraft(run.topic); return; }
    setEditing(false);
    await onRename(run.id, trimmed);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') commitRename();
    if (e.key === 'Escape') { setEditing(false); setDraft(run.topic); }
  };

  const date = new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <div className="hcard" onClick={() => !editing && onOpen(run)}>
      <div className="hcard__top">
        {editing ? (
          <input
            ref={inputRef}
            className="hcard__rename-input"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleKeyDown}
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <h3 className="hcard__topic">{run.topic}</h3>
        )}
        <ConfidencePill score={run.confidence_score} />
      </div>

      {run.executive_summary && (
        <p className="hcard__summary">{run.executive_summary.slice(0, 160)}{run.executive_summary.length > 160 ? '…' : ''}</p>
      )}

      <div className="hcard__meta">
        <span className="hcard__date">{date}</span>
        {run.sources?.length > 0 && (
          <span className="hcard__sources-count">{run.sources.length} sources</span>
        )}
        {run.important_findings?.length > 0 && (
          <span className="hcard__findings-count">{run.important_findings.length} findings</span>
        )}
      </div>

      <div className="hcard__actions" onClick={e => e.stopPropagation()}>
        <button className="hcard__btn hcard__btn--open" onClick={() => onOpen(run)}>View</button>
        <button className="hcard__btn hcard__btn--rename" onClick={() => { setEditing(true); setDraft(run.topic); }}>Rename</button>
        <button className="hcard__btn hcard__btn--delete" onClick={() => onDelete(run.id)}>Delete</button>
      </div>
    </div>
  );
}

const History = () => {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    researchService.getHistory()
      .then(res => setRuns(res.data))
      .catch(() => toast.error('Could not load history.'))
      .finally(() => setLoading(false));
  }, []);

  const handleOpen = (run) => {
    navigate('/results', {
      state: {
        researchData: {
          topic: run.topic,
          run_id: run.run_id,
          executive_summary: run.executive_summary,
          key_concepts: run.key_concepts,
          important_findings: run.important_findings,
          summary: run.summary,
          sources: run.sources,
          confidence_score: run.confidence_score,
        },
      },
    });
  };

  const handleDelete = async (id) => {
    try {
      await researchService.deleteHistoryItem(id);
      setRuns(prev => prev.filter(r => r.id !== id));
      toast.success('Deleted.');
    } catch {
      toast.error('Delete failed.');
    }
  };

  const handleRename = async (id, topic) => {
    try {
      const res = await researchService.renameHistoryItem(id, topic);
      setRuns(prev => prev.map(r => r.id === id ? res.data : r));
      toast.success('Renamed.');
    } catch {
      toast.error('Rename failed.');
    }
  };

  return (
    <div className="history-container">
      <header className="results-header">
        <div className="header-content">
          <h1 className="header-title">Research Platform</h1>
          <div className="header-actions">
            <button onClick={() => navigate('/home')} className="btn btn-secondary">New Research</button>
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

      <main className="history-main">
        <div className="history-content">
          <div className="history-hero">
            <h2 className="history-title">Research History</h2>
            <p className="history-subtitle">
              {runs.length === 0 && !loading
                ? 'No saved runs yet. Start a new research to get going.'
                : `${runs.length} saved run${runs.length !== 1 ? 's' : ''}`}
            </p>
          </div>

          {loading && (
            <div className="history-loading">
              <span className="spinner" />
              <span>Loading history...</span>
            </div>
          )}

          {!loading && runs.length === 0 && (
            <div className="history-empty">
              <p>Nothing here yet.</p>
              <button className="btn btn-primary" onClick={() => navigate('/home')}>
                Start Researching
              </button>
            </div>
          )}

          <div className="history-grid">
            {runs.map(run => (
              <HistoryCard
                key={run.id}
                run={run}
                onOpen={handleOpen}
                onDelete={handleDelete}
                onRename={handleRename}
              />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default History;
