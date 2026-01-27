import React from 'react';
import './ResearchPreview.css';

const ResearchPreview = ({ progress, agentStatus, currentMessage }) => {
  // Debug: Log when component renders
  React.useEffect(() => {
    console.log('🔄 ResearchPreview rendered:', { progress, currentMessage, agentStatus });
  }, [progress, currentMessage, agentStatus]);
  const agents = [
    {
      id: 'planner',
      name: 'Planner Agent',
      icon: '📋',
      description: 'Creating research strategy',
      color: '#6b9fff'
    },
    {
      id: 'research',
      name: 'Research Agent',
      icon: '🔍',
      description: 'Gathering deep insights',
      color: '#b19cd9'
    },
    {
      id: 'synthesizer',
      name: 'Synthesizer Agent',
      icon: '✨',
      description: 'Compiling final report',
      color: '#7dd3a0'
    }
  ];

  const getAgentStatus = (agentId) => {
    return agentStatus[agentId] || 'pending';
  };

  const getAgentMessage = (agentId) => {
    if (agentStatus[`${agentId}_message`]) {
      return agentStatus[`${agentId}_message`];
    }
    return null;
  };

  const getPreviewData = (agentId) => {
    const status = getAgentStatus(agentId);
    if (status === 'completed' && agentStatus[`${agentId}_data`]) {
      return agentStatus[`${agentId}_data`];
    }
    return null;
  };

  return (
    <div className="research-preview">
      <div className="preview-header">
        <div className="preview-title-row">
          <h3 className="preview-title">Research in Progress</h3>
          <span className="progress-text">{progress}%</span>
        </div>
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${progress}%` }}></div>
        </div>
        {currentMessage && (
          <p className="current-message">{currentMessage}</p>
        )}
      </div>

      <div className="agents-preview">
        {agents.map((agent, index) => {
          const status = getAgentStatus(agent.id);
          const previewData = getPreviewData(agent.id);
          const agentMessage = getAgentMessage(agent.id);
          const isActive = status === 'working';
          const isCompleted = status === 'completed';
          const prevAgentCompleted = index > 0 && getAgentStatus(agents[index - 1].id) === 'completed';
          
          return (
            <div key={agent.id}>
              {/* Handoff indicator */}
              {index > 0 && isActive && prevAgentCompleted && (
                <div className="handoff-indicator">
                  <span className="handoff-arrow">↓</span>
                  <span className="handoff-text">Handing off to {agent.name}</span>
                </div>
              )}
              
              <div 
                className={`agent-card ${status}`}
                style={{ '--agent-color': agent.color }}
              >
                <div className="agent-header">
                  <div className="agent-icon-wrapper">
                    <span className="agent-icon">{agent.icon}</span>
                    {isActive && <div className="pulse-ring"></div>}
                    {isCompleted && <div className="checkmark">✓</div>}
                  </div>
                  <div className="agent-info">
                    <h4 className="agent-name">{agent.name}</h4>
                    <p className="agent-description">
                      {status === 'pending' && 'Waiting...'}
                      {isActive && (
                        <span className="working-text">
                          {agentMessage || agent.description}
                        </span>
                      )}
                      {isCompleted && (
                        <span className="completed-text">✓ Completed</span>
                      )}
                    </p>
                  </div>
                  {isActive && (
                    <div className="agent-progress-indicator">
                      <div className="mini-spinner"></div>
                    </div>
                  )}
                </div>

                {previewData && status === 'completed' && (
                  <div className="agent-preview">
                    {agent.id === 'planner' && previewData.plan && (
                      <div className="preview-content">
                        {previewData.plan.understanding && (
                          <p className="preview-text">
                            <strong>Plan:</strong> {previewData.plan.understanding.substring(0, 120)}...
                          </p>
                        )}
                        {previewData.plan.sub_questions && previewData.plan.sub_questions.length > 0 && (
                          <div className="preview-tags">
                            {previewData.plan.sub_questions.slice(0, 3).map((q, i) => (
                              <span key={i} className="preview-tag">{q.substring(0, 40)}...</span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {agent.id === 'research' && previewData.findings && (
                      <div className="preview-content">
                        {previewData.findings.core_facts && previewData.findings.core_facts.length > 0 && (
                          <div className="preview-section">
                            <p className="preview-text">
                              <strong>Found:</strong> {previewData.findings.core_facts[0]?.substring(0, 100)}...
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {agent.id === 'synthesizer' && previewData.synthesis && (
                      <div className="preview-content">
                        {previewData.synthesis.overview && (
                          <p className="preview-text">
                            {previewData.synthesis.overview.substring(0, 150)}...
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {previewData && isCompleted && (
                  <div className="agent-output-badge">
                    <span>Output ready</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ResearchPreview;
