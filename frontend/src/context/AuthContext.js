import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService, safeStorage } from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  useEffect(() => {
    const storedToken = safeStorage.getItem('token');
    const storedUser = safeStorage.getItem('user');

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      authService.setAuthToken(storedToken);
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authService.login(email, password);
      const { user, tokens } = response.data;
      
      setUser(user);
      setToken(tokens.access);
      safeStorage.setItem('token', tokens.access);
      safeStorage.setItem('refresh_token', tokens.refresh);
      safeStorage.setItem('user', JSON.stringify(user));
      authService.setAuthToken(tokens.access);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed. Please try again.'
      };
    }
  };

  const signup = async (email, username, password, passwordConfirm) => {
    try {
      const response = await authService.signup(email, username, password, passwordConfirm);
      const { user, tokens } = response.data;
      
      setUser(user);
      setToken(tokens.access);
      safeStorage.setItem('token', tokens.access);
      safeStorage.setItem('refresh_token', tokens.refresh);
      safeStorage.setItem('user', JSON.stringify(user));
      authService.setAuthToken(tokens.access);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || error.response?.data?.password?.[0] || 'Signup failed. Please try again.'
      };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    safeStorage.removeItem('token');
    safeStorage.removeItem('refresh_token');
    safeStorage.removeItem('user');
    authService.setAuthToken(null);
  };

  const value = {
    user,
    token,
    login,
    signup,
    logout,
    loading,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
