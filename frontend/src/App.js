import React, { useState, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import { getStoredAuth, getCurrentUser } from './api/auth';
import './App.css';

/**
 * BioMind Nexus - Main Application
 * 
 * Handles authentication state and routing between Login and Dashboard.
 */
export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const auth = getStoredAuth();
      if (auth) {
        try {
          const userData = await getCurrentUser(auth.accessToken, auth.sessionId);
          setUser(userData);
          setIsAuthenticated(true);
        } catch (err) {
          // Token invalid or expired
          console.log('Session expired, please login again');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const handleLoginSuccess = async (response) => {
    try {
      const userData = await getCurrentUser(response.access_token, response.session_id);
      setUser(userData);
      setIsAuthenticated(true);
    } catch (err) {
      console.error('Failed to get user info:', err);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
  };

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading BioMind Nexus...</p>
      </div>
    );
  }

  // Render Login or Dashboard based on auth state
  return isAuthenticated ? (
    <Dashboard user={user} onLogout={handleLogout} />
  ) : (
    <LoginPage onLoginSuccess={handleLoginSuccess} />
  );
}