import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Home from './pages/Home';
import Results from './pages/Results';
import History from './pages/History';
import PrivateRoute from './components/PrivateRoute';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-silver)',
                borderRadius: '12px',
                padding: '16px',
                boxShadow: 'var(--shadow-lg)',
                backdropFilter: 'blur(20px)',
              },
              success: {
                iconTheme: {
                  primary: 'var(--success-green)',
                  secondary: 'var(--bg-elevated)',
                },
                style: {
                  border: '1px solid var(--success-green)',
                  boxShadow: '0 0 20px var(--success-green-glow)',
                },
              },
              error: {
                iconTheme: {
                  primary: 'var(--error-red)',
                  secondary: 'var(--bg-elevated)',
                },
                style: {
                  border: '1px solid var(--error-red)',
                  boxShadow: '0 0 20px var(--error-red-glow)',
                },
              },
            }}
          />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/home"
              element={
                <PrivateRoute>
                  <Home />
                </PrivateRoute>
              }
            />
            <Route
              path="/results"
              element={
                <PrivateRoute>
                  <Results />
                </PrivateRoute>
              }
            />
            <Route
              path="/history"
              element={
                <PrivateRoute>
                  <History />
                </PrivateRoute>
              }
            />
            <Route path="/" element={<Navigate to="/home" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
