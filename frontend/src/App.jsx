import React, { useState, useEffect } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import AdminDashboard from './components/AdminDashboard';
import { getStoredAuth, getCurrentUser } from './api/auth';

/**
 * BioMind Nexus - Main Application
 * 
 * Role-based routing:
 * - Admin users → AdminDashboard (audit logs, user management)
 * - Researcher users → Dashboard (query interface, knowledge graph)
 */

// ============================================
// Global Styles
// ============================================
const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  html, body, #root {
    height: 100%;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                 'Helvetica Neue', Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background: #f8fafc;
    color: #0f172a;
  }
`;

// ============================================
// Styled Components
// ============================================
const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f8fafc;
  gap: 1rem;

  p {
    color: #64748b;
    font-size: 0.95rem;
  }
`;

const LoadingSpinner = styled.div`
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

// ============================================
// Component
// ============================================
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
            <>
                <GlobalStyle />
                <LoadingContainer>
                    <LoadingSpinner />
                    <p>Loading BioMind Nexus...</p>
                </LoadingContainer>
            </>
        );
    }

    // Route based on authentication and role
    const renderDashboard = () => {
        if (!isAuthenticated) {
            return <LoginPage onLoginSuccess={handleLoginSuccess} />;
        }

        // Role-based routing
        const userRole = user?.role?.toLowerCase();

        if (userRole === 'admin') {
            return <AdminDashboard user={user} onLogout={handleLogout} />;
        }

        // Default to researcher dashboard
        return <Dashboard user={user} onLogout={handleLogout} />;
    };

    return (
        <>
            <GlobalStyle />
            {renderDashboard()}
        </>
    );
}
