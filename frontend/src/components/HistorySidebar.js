import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { researchService } from '../services/researchService';
import './HistorySidebar.css';

function ConfidencePill({ score }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const cls = pct >= 75 ? 'high' : pct >= 50 ? 'mid' : 'low';
  return <span className={`hsb-pill hsb-pill--${cls}`}>{pct}%</span>;
}

function SidebarCard({ run, onOpen, onDelete, onRename }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft]     = useState(run.topic);
  const inputRef = useRef(null);

  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

  const commit = async () => {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === run.topic) { setEditing(false); setDraft(run.topic); return; }
    setEditing(false);
    await onRename(run.id, trimmed);
  };

  const date = new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  });

  return (
    <div className="hsb-card" onClick={() => !editing && onOpen(run)}>
      <div className="hsb-card__top">
        {editing ? (
          <input
            ref={inputRef}
            className="hsb-card__input"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') { setEditing(false); setDraft(run.topic); } }}
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <span className="hsb-card__topic">{run.topic}</span>
        )}
        <ConfidencePill score={run.confidence_score} />
      </div>

      <div className="hsb-card__meta">
        <span className="hsb-card__date">{date}</span>
        {run.sources?.length > 0 && <span className="hsb-card__tag">{run.sources.length} sources</span>}
        {run.important_findings?.length > 0 && <span className="hsb-card__tag">{run.important_findings.length} findings</span>}
      </div>

      <div className="hsb-card__actions" onClick={e => e.stopPropagation()}>
        <button className="hsb-card__btn hsb-card__btn--rename" onClick={() => { setEditing(true); setDraft(run.topic); }}>
          Rename
        </button>
        <button className="hsb-card__btn hsb-card__btn--delete" onClick={() => onDelete(run.id)}>
          Delete
        </button>
      </div>
    </div>
  );
}

const HistorySidebar = ({ open, onClose }) => {
  const [runs, setRuns]     = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    researchService.getHistory()
      .then(res => setRuns(res.data))
      .catch(() => toast.error('Could not load history.'))
      .finally(() => setLoading(false));
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  const handleOpen = (run) => {
    onClose();
    navigate('/results', {
      state: {
        researchData: {
          topic:              run.topic,
          run_id:             run.run_id,
          executive_summary:  run.executive_summary,
          key_concepts:       run.key_concepts,
          important_findings: run.important_findings,
          summary:            run.summary,
          sources:            run.sources,
          confidence_score:   run.confidence_score,
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
    <>
      {/* Backdrop */}
      <div
        className={`hsb-backdrop${open ? ' hsb-backdrop--visible' : ''}`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside className={`hsb-panel${open ? ' hsb-panel--open' : ''}`}>
        <div className="hsb-header">
          <h2 className="hsb-title">History</h2>
          <button className="hsb-close" onClick={onClose} aria-label="Close">
            &#x2715;
          </button>
        </div>

        <div className="hsb-body">
          {loading && (
            <div className="hsb-state">
              <span className="spinner" />
              <span>Loading...</span>
            </div>
          )}

          {!loading && runs.length === 0 && (
            <div className="hsb-state hsb-state--empty">
              No saved runs yet.
            </div>
          )}

          {!loading && runs.map(run => (
            <SidebarCard
              key={run.id}
              run={run}
              onOpen={handleOpen}
              onDelete={handleDelete}
              onRename={handleRename}
            />
          ))}
        </div>
      </aside>
    </>
  );
};

export default HistorySidebar;
