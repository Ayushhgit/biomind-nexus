import React from 'react';
import { logout, clearAuth } from '../api/auth';
import './Dashboard.css';

/**
 * BioMind Nexus Dashboard
 * 
 * Simple dashboard placeholder shown after successful login.
 */
export default function Dashboard({ user, onLogout }) {
    const handleLogout = async () => {
        try {
            const token = localStorage.getItem('biomind_access_token');
            const sessionId = localStorage.getItem('biomind_session_id');
            await logout(token, sessionId);
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            clearAuth();
            onLogout();
        }
    };

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div className="header-brand">
                    <div className="brand-icon">
                        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" fill="none" />
                            <path d="M24 8 L24 40 M16 14 L24 24 L16 34 M32 14 L24 24 L32 34"
                                stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                            <circle cx="24" cy="24" r="4" fill="currentColor" />
                        </svg>
                    </div>
                    <span className="brand-name">BioMind Nexus</span>
                </div>
                <div className="header-user">
                    <span className="user-email">{user?.email || 'Researcher'}</span>
                    <span className="user-role">{user?.role || 'researcher'}</span>
                    <button onClick={handleLogout} className="logout-button">
                        Sign Out
                    </button>
                </div>
            </header>

            <main className="dashboard-main">
                <div className="welcome-card">
                    <h1>Welcome to BioMind Nexus</h1>
                    <p>Your AI-driven drug repurposing research platform</p>
                    <div className="welcome-status">
                        <span className="status-badge">✓ Authenticated</span>
                        <span className="status-badge">✓ Session Active</span>
                    </div>
                </div>

                <div className="features-grid">
                    <div className="feature-card">
                        <div className="feature-icon">🔬</div>
                        <h3>Literature Analysis</h3>
                        <p>Query biomedical literature with AI-assisted reasoning</p>
                        <span className="coming-soon">Coming Soon</span>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon">🧬</div>
                        <h3>Knowledge Graph</h3>
                        <p>Explore drug-gene-disease relationships</p>
                        <span className="coming-soon">Coming Soon</span>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon">📋</div>
                        <h3>Innovation Dossier</h3>
                        <p>Generate audit-ready research reports</p>
                        <span className="coming-soon">Coming Soon</span>
                    </div>
                </div>
            </main>
        </div>
    );
}
