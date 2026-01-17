import React, { useState } from 'react';
import { login, storeAuth } from '../api/auth';
import './LoginPage.css';

/**
 * BioMind Nexus Login Page
 * 
 * Professional light-themed login for biomedical research platform.
 */
export default function LoginPage({ onLoginSuccess }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const response = await login(email, password);
            storeAuth(response.access_token, response.session_id, response.expires_in);
            onLoginSuccess(response);
        } catch (err) {
            setError(err.message || 'Invalid credentials. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-container">
            {/* Left Panel - Branding */}
            <div className="login-branding">
                <div className="branding-content">
                    <div className="logo-container">
                        <div className="logo-icon">
                            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" fill="none" />
                                <path d="M24 8 L24 40 M16 14 L24 24 L16 34 M32 14 L24 24 L32 34"
                                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                <circle cx="24" cy="24" r="4" fill="currentColor" />
                            </svg>
                        </div>
                        <h1 className="logo-text">BioMind Nexus</h1>
                    </div>
                    <p className="branding-tagline">
                        AI-Driven Drug Repurposing Platform
                    </p>
                    <div className="branding-features">
                        <div className="feature-item">
                            <span className="feature-icon">🔬</span>
                            <span>Intelligent Literature Analysis</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🧬</span>
                            <span>Drug-Gene-Disease Insights</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🔐</span>
                            <span>Secure & Auditable Research</span>
                        </div>
                    </div>
                </div>
                <p className="branding-footer">
                    Accelerating biomedical discovery with responsible AI
                </p>
            </div>

            {/* Right Panel - Login Form */}
            <div className="login-form-panel">
                <div className="login-form-container">
                    <div className="login-header">
                        <h2>Welcome Back</h2>
                        <p>Sign in to access your research dashboard</p>
                    </div>

                    <form onSubmit={handleSubmit} className="login-form">
                        {error && (
                            <div className="error-message">
                                <svg className="error-icon" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <span>{error}</span>
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="email">Email Address</label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="researcher@institution.edu"
                                required
                                autoComplete="email"
                                disabled={isLoading}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                required
                                autoComplete="current-password"
                                disabled={isLoading}
                            />
                        </div>

                        <button
                            type="submit"
                            className="login-button"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <span className="spinner"></span>
                                    Authenticating...
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    <div className="login-footer">
                        <p className="security-notice">
                            <svg className="lock-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                            </svg>
                            Secure authentication with audit logging
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
