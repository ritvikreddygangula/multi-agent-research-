import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import AgentGraphView from '../components/AgentGraphView';
import './Results.css';

// All nodes completed — passed to the frozen graph snapshot
const ALL_DONE = {
  planner: 'done', rag_retrieval: 'done',
  branch_0: 'done', branch_1: 'done', branch_2: 'done',
  branch_3: 'done', branch_4: 'done',
  aggregator: 'done', critic: 'done', synthesizer: 'done',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function ConfidenceBadge({ score }) {
  if (typeof score !== 'number') return null;
  const pct = Math.round(score * 100);
  const color = pct >= 75 ? '#4ade80' : pct >= 50 ? '#fbbf24' : '#f87171';
  return (
    <div className="confidence-badge" style={{ borderColor: color }}>
      <svg width="36" height="36" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15" fill="none" stroke="#2a2a3a" strokeWidth="3" />
        <circle
          cx="18" cy="18" r="15" fill="none"
          stroke={color} strokeWidth="3"
          strokeDasharray={`${pct * 0.942} 100`}
          strokeLinecap="round"
          transform="rotate(-90 18 18)"
        />
      </svg>
      <div className="confidence-badge__text">
        <span className="confidence-badge__pct" style={{ color }}>{pct}%</span>
        <span className="confidence-badge__label">confidence</span>
      </div>
    </div>
  );
}

function SourceChip({ src }) {
  const label = src.title
    ? src.title.length > 45 ? src.title.slice(0, 45) + '…' : src.title
    : src.url;
  const typeColor = {
    web:       '#6b9fff',
    wikipedia: '#a78bfa',
    arxiv:     '#4ade80',
  }[src.source_type] || '#6b9fff';

  return (
    <a
      href={src.url}
      target="_blank"
      rel="noopener noreferrer"
      className="source-chip"
      title={src.snippet || src.title || src.url}
      style={{ borderColor: `${typeColor}40`, color: typeColor }}
    >
      {src.source_type && (
        <span className="source-chip__type" style={{ background: `${typeColor}22` }}>
          {src.source_type}
        </span>
      )}
      {label}
    </a>
  );
}

function FindingCard({ finding, index }) {
  const [expanded, setExpanded] = useState(false);

  // Legacy string finding
  if (typeof finding === 'string') {
    return (
      <div className="finding-card">
        <p className="finding-card__text">{finding}</p>
      </div>
    );
  }

  const pct = typeof finding.confidence === 'number'
    ? Math.round(finding.confidence * 100) : null;
  const barColor = pct === null ? '#6b9fff'
    : pct >= 75 ? '#4ade80' : pct >= 50 ? '#fbbf24' : '#f87171';
  const sources = finding.sources || [];

  return (
    <div className="finding-card">
      <div className="finding-card__header">
        <span className="finding-card__index">#{index + 1}</span>
        {pct !== null && (
          <div className="finding-card__bar-wrap" title={`Confidence: ${pct}%`}>
            <div
              className="finding-card__bar-fill"
              style={{ width: `${pct}%`, background: barColor }}
            />
          </div>
        )}
        {pct !== null && (
          <span className="finding-card__pct" style={{ color: barColor }}>{pct}%</span>
        )}
      </div>

      <p className="finding-card__text">{finding.finding}</p>

      {finding.sub_question && (
        <p className="finding-card__sub">
          <span className="finding-card__sub-label">From:</span> {finding.sub_question}
        </p>
      )}

      {sources.length > 0 && (
        <div className="finding-card__sources">
          {(expanded ? sources : sources.slice(0, 3)).map((src, i) => (
            <SourceChip key={i} src={src} />
          ))}
          {sources.length > 3 && (
            <button
              className="finding-card__toggle"
              onClick={() => setExpanded(e => !e)}
            >
              {expanded ? 'show less' : `+${sources.length - 3} more`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function FrozenGraph() {
  const [open, setOpen] = useState(false);
  return (
    <div className="frozen-graph-section">
      <button className="frozen-graph-toggle" onClick={() => setOpen(o => !o)}>
        <span>Agent Pipeline</span>
        <span className="frozen-graph-toggle__badge">completed</span>
        <span className="frozen-graph-toggle__chevron">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <AgentGraphView
          nodeStatuses={ALL_DONE}
          progress={100}
          currentMessage="Pipeline complete"
        />
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const Results = () => {
  const { logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const raw = location.state?.researchData;

  React.useEffect(() => {
    if (!raw) {
      toast.error('No research data found.');
      navigate('/home');
    }
  }, [raw, navigate]);

  if (!raw) return null;

  // Strip the SSE envelope field if present
  const { type: _type, ...researchData } = raw;

  const handleNewResearch = () => navigate('/home');

  const overview   = researchData.executive_summary || researchData.overview || '';
  const findings   = researchData.important_findings || [];
  const concepts   = researchData.key_concepts || [];
  const allSources = researchData.sources || [];
  const score      = researchData.confidence_score;

  return (
    <div className="results-container">
      <header className="results-header">
        <div className="header-content">
          <h1 className="header-title">Research Platform</h1>
          <div className="header-actions">
            <button onClick={handleNewResearch} className="btn btn-secondary">
              New Research
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

      <main className="results-main">
        <div className="results-content">

          {/* ── Topic + confidence ── */}
          <div className="results-hero">
            <div className="results-hero__left">
              <h2 className="results-topic">{researchData.topic}</h2>
              {researchData.run_id && (
                <span className="results-run-id">run {researchData.run_id.slice(0, 8)}</span>
              )}
            </div>
            <div className="results-hero__right">
              <ConfidenceBadge score={score} />
              <button onClick={handleNewResearch} className="btn btn-primary">
                Research New Topic
              </button>
            </div>
          </div>

          <div className="results-sections">

            {/* ── Overview ── */}
            {overview && (
              <section className="result-section">
                <h3 className="section-title">Overview</h3>
                <p className="section-content">{overview}</p>
              </section>
            )}

            {/* ── Key Concepts ── */}
            {concepts.length > 0 && (
              <section className="result-section">
                <h3 className="section-title">Key Concepts</h3>
                <ul className="concept-list">
                  {concepts.map((c, i) => (
                    <li key={i} className="concept-item">
                      {typeof c === 'string' ? c : c.concept || JSON.stringify(c)}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* ── Findings ── */}
            {findings.length > 0 && (
              <section className="result-section">
                <h3 className="section-title">
                  Findings
                  <span className="section-title__count">{findings.length}</span>
                </h3>
                <div className="findings-grid">
                  {findings.map((f, i) => (
                    <FindingCard key={i} finding={f} index={i} />
                  ))}
                </div>
              </section>
            )}

            {/* ── Summary ── */}
            {researchData.summary && (
              <section className="result-section">
                <h3 className="section-title">Summary</h3>
                <p className="section-content">{researchData.summary}</p>
              </section>
            )}

            {/* ── All Sources ── */}
            {allSources.length > 0 && (
              <section className="result-section">
                <h3 className="section-title">
                  Sources
                  <span className="section-title__count">{allSources.length}</span>
                </h3>
                <div className="sources-grid">
                  {allSources.map((src, i) => (
                    <SourceChip key={i} src={src} />
                  ))}
                </div>
              </section>
            )}

            {/* ── Frozen agent graph ── */}
            <FrozenGraph />

          </div>
        </div>
      </main>
    </div>
  );
};

export default Results;
