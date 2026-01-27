import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { researchService } from '../services/researchService';
import './Home.css';

const Home = () => {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!topic.trim()) {
      toast.error('Please enter a research topic');
      return;
    }

    setLoading(true);
    const loadingToast = toast.loading('Conducting research with AI agents...', {
      icon: '🔍',
    });

    try {
      const response = await researchService.conductResearch(topic.trim());
      toast.dismiss(loadingToast);
      toast.success('Research completed! Viewing results...', {
        icon: '✨',
      });
      // Store results and navigate to results page
      setTimeout(() => {
        navigate('/results', { state: { researchData: response.data } });
      }, 500);
    } catch (err) {
      toast.dismiss(loadingToast);
      toast.error(err.response?.data?.error || 'Research failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="home-container">
      <header className="home-header">
        <div className="header-content">
          <h1 className="header-title">Research Platform</h1>
          <div className="header-actions">
            <span className="user-email">{user?.email}</span>
            <button 
              onClick={() => {
                toast.success('Logged out successfully', { icon: '👋' });
                logout();
              }} 
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
              {loading ? (
                <>
                  <span className="spinner" style={{ marginRight: '8px' }}></span>
                  Researching...
                </>
              ) : (
                'Start Research'
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default Home;
