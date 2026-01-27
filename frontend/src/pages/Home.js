import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { researchService } from '../services/researchService';
import ResearchPreview from '../components/ResearchPreview';
import './Home.css';

const Home = () => {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [agentStatus, setAgentStatus] = useState({
    planner: 'pending',
    research: 'pending',
    synthesizer: 'pending'
  });
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!topic.trim()) {
      toast.error('Please enter a research topic');
      return;
    }

    setLoading(true);
    setShowPreview(true);
    setProgress(0); // Start at 0% - backend will send updates
    setCurrentMessage('Connecting to research service...');
    setAgentStatus({
      planner: 'pending',
      research: 'pending',
      synthesizer: 'pending'
    });
    
    console.log('🔍 Starting research for:', topic.trim());

    try {
      console.log('🚀 Attempting streaming research...');
      
      // Try streaming first
      const streamPromise = researchService.conductResearchStreaming(
        topic.trim(),
        // onProgress callback
        (update) => {
          console.log('🔄 Progress callback triggered:', update);
          if (update && update.type === 'progress') {
            const newProgress = update.progress || 0;
            console.log(`📈 Setting progress to: ${newProgress}%`);
            
            // Force state update - always update progress
            setProgress(newProgress);
            
            // Update current message
            if (update.message) {
              console.log(`💬 Setting message: ${update.message}`);
              setCurrentMessage(update.message);
            }
            
            // Update agent status
            if (update.agent && update.agent !== 'system') {
              console.log(`🤖 Updating agent ${update.agent} to status: ${update.status}`);
              setAgentStatus(prev => ({
                ...prev,
                [update.agent]: update.status || 'working',
                [`${update.agent}_message`]: update.message || null,
                [`${update.agent}_data`]: update.data || null
              }));
            } else if (update.agent === 'system') {
              // System updates - just update message and progress
              if (update.message) {
                setCurrentMessage(update.message);
              }
            }
          } else {
            console.warn('⚠️ Unexpected update format:', update);
          }
        },
        // onComplete callback
        (result) => {
          setProgress(100);
          setAgentStatus({
            planner: 'completed',
            research: 'completed',
            synthesizer: 'completed'
          });
          
          toast.success('Research completed! Viewing results...', {
            icon: '✨',
          });
          
          setTimeout(() => {
            navigate('/results', { state: { researchData: result } });
          }, 1000);
        },
        // onError callback
        async (error) => {
          console.error('❌ Streaming error:', error);
          console.error('Error details:', error.message, error.stack);
          
          // Show error in preview
          setCurrentMessage(`Error: ${error.message}`);
          
          // Fallback to regular endpoint if streaming fails
          if (error.message && (error.message.includes('fetch') || error.message.includes('Network'))) {
            console.log('🔄 Falling back to regular endpoint...');
            toast.loading('Streaming unavailable, using standard research...', { id: 'fallback' });
            
            // Simulate progress while falling back
            setProgress(20);
            setCurrentMessage('Using standard research mode...');
            
            try {
              const response = await researchService.conductResearch(topic.trim());
              toast.dismiss('fallback');
              setProgress(100);
              setCurrentMessage('Research completed!');
              toast.success('Research completed! Viewing results...', {
                icon: '✨',
              });
              setTimeout(() => {
                navigate('/results', { state: { researchData: response.data } });
              }, 500);
            } catch (fallbackErr) {
              toast.dismiss('fallback');
              toast.error(fallbackErr.response?.data?.error || 'Research failed. Please try again.');
              setLoading(false);
              setShowPreview(false);
            }
          } else {
            toast.error(error.message || 'Research failed. Please try again.');
            setLoading(false);
            setShowPreview(false);
          }
        }
      );
      
      // Add timeout to detect if stream is stuck
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error('Stream timeout - no updates received'));
        }, 60000); // 60 second timeout
      });
      
      await Promise.race([streamPromise, timeoutPromise]);
      
    } catch (err) {
      console.error('Research error:', err);
      // Fallback to regular endpoint
      if (err.message && err.message.includes('fetch')) {
        toast.loading('Falling back to standard research...', { id: 'fallback' });
        try {
          const response = await researchService.conductResearch(topic.trim());
          toast.dismiss('fallback');
          toast.success('Research completed! Viewing results...', {
            icon: '✨',
          });
          navigate('/results', { state: { researchData: response.data } });
        } catch (fallbackErr) {
          toast.dismiss('fallback');
          toast.error(fallbackErr.response?.data?.error || 'Research failed. Please try again.');
          setLoading(false);
          setShowPreview(false);
        }
      } else {
        toast.error(err.message || 'Research failed. Please try again.');
        setLoading(false);
        setShowPreview(false);
      }
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

          {showPreview && loading && (
            <ResearchPreview 
              progress={progress} 
              agentStatus={agentStatus}
              currentMessage={currentMessage}
            />
          )}
        </div>
      </main>
    </div>
  );
};

export default Home;
