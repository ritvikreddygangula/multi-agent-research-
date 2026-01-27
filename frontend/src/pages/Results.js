import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Results.css';

const Results = () => {
  const { logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const researchData = location.state?.researchData;

  // Redirect to home if no research data
  React.useEffect(() => {
    if (!researchData) {
      navigate('/home');
    }
  }, [researchData, navigate]);

  if (!researchData) {
    return null;
  }

  const handleNewResearch = () => {
    navigate('/home');
  };

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
            <button onClick={logout} className="btn btn-secondary" style={{ marginLeft: '16px' }}>
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="results-main">
        <div className="results-content">
          <div className="results-header-section">
            <h2 className="results-topic">{researchData.topic}</h2>
            <button onClick={handleNewResearch} className="btn btn-primary">
              Research New Topic
            </button>
          </div>

          <div className="results-sections">
            {researchData.overview && (
              <section className="result-section">
                <h3 className="section-title">Overview</h3>
                <p className="section-content">{researchData.overview}</p>
              </section>
            )}

            {researchData.key_concepts && researchData.key_concepts.length > 0 && (
              <section className="result-section">
                <h3 className="section-title">Key Concepts</h3>
                <ul className="concept-list">
                  {researchData.key_concepts.map((concept, index) => (
                    <li key={index} className="concept-item">
                      {concept}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {researchData.important_findings && researchData.important_findings.length > 0 && (
              <section className="result-section">
                <h3 className="section-title">Important Findings</h3>
                <ul className="findings-list">
                  {researchData.important_findings.map((finding, index) => (
                    <li key={index} className="finding-item">
                      {finding}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {researchData.summary && (
              <section className="result-section">
                <h3 className="section-title">Summary</h3>
                <p className="section-content">{researchData.summary}</p>
              </section>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Results;
