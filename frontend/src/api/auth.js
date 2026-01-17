/**
 * BioMind Nexus - Authentication API Client
 * 
 * Handles all authentication requests to the FastAPI backend.
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Login with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<{access_token: string, session_id: string, expires_in: number}>}
 */
export async function login(email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
    }

    return response.json();
}

/**
 * Logout and invalidate current session
 * @param {string} token - Access token
 * @param {string} sessionId - Current session ID
 * @returns {Promise<{message: string, sessions_invalidated: number}>}
 */
export async function logout(token, sessionId) {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-Session-ID': sessionId,
        },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Logout failed');
    }

    return response.json();
}

/**
 * Get current authenticated user info
 * @param {string} token - Access token
 * @param {string} sessionId - Current session ID
 * @returns {Promise<{id: string, email: string, role: string, is_active: boolean}>}
 */
export async function getCurrentUser(token, sessionId) {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-Session-ID': sessionId,
        },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get user info');
    }

    return response.json();
}

/**
 * Store auth tokens in localStorage
 */
export function storeAuth(accessToken, sessionId, expiresIn) {
    const expiresAt = Date.now() + (expiresIn * 1000);
    localStorage.setItem('biomind_access_token', accessToken);
    localStorage.setItem('biomind_session_id', sessionId);
    localStorage.setItem('biomind_expires_at', expiresAt.toString());
}

/**
 * Get stored auth tokens
 */
export function getStoredAuth() {
    const accessToken = localStorage.getItem('biomind_access_token');
    const sessionId = localStorage.getItem('biomind_session_id');
    const expiresAt = localStorage.getItem('biomind_expires_at');

    if (!accessToken || !sessionId || !expiresAt) {
        return null;
    }

    // Check if token is expired
    if (Date.now() > parseInt(expiresAt)) {
        clearAuth();
        return null;
    }

    return { accessToken, sessionId };
}

/**
 * Clear stored auth tokens
 */
export function clearAuth() {
    localStorage.removeItem('biomind_access_token');
    localStorage.removeItem('biomind_session_id');
    localStorage.removeItem('biomind_expires_at');
}
