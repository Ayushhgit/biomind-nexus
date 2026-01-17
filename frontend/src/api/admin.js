/**
 * BioMind Nexus - Admin API Client
 * 
 * Handles admin-only requests for audit logs, user management, and sessions.
 */

const API_BASE_URL = 'http://10.20.72.65:8000/api/v1';

/**
 * Get authentication headers
 */
function getAuthHeaders() {
    const token = localStorage.getItem('biomind_access_token');
    const sessionId = localStorage.getItem('biomind_session_id');

    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Session-ID': sessionId,
    };
}

// =============================================================================
// Audit Log API
// =============================================================================

/**
 * Get audit logs (admin only)
 * @param {Object} options - Query options
 * @returns {Promise<{logs: Array, total: number, page: number}>}
 */
export async function getAuditLogs(options = {}) {
    const params = new URLSearchParams({
        page: options.page || 1,
        page_size: options.pageSize || 50,
    });

    if (options.eventType) {
        params.append('event_type', options.eventType);
    }
    if (options.userId) {
        params.append('user_id', options.userId);
    }

    const response = await fetch(`${API_BASE_URL}/admin/audit/logs?${params}`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch audit logs');
    }

    return response.json();
}

// =============================================================================
// User Management API
// =============================================================================

/**
 * List all users (admin only)
 * @returns {Promise<{users: Array, total: number}>}
 */
export async function listUsers() {
    const response = await fetch(`${API_BASE_URL}/admin/users`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch users');
    }

    return response.json();
}

/**
 * Update user (admin only)
 * @param {string} userId - User ID
 * @param {Object} update - Update data { is_active, role }
 */
export async function updateUser(userId, update) {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(update),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update user');
    }

    return response.json();
}

/**
 * Revoke all sessions for a user (admin only)
 * @param {string} userId - User ID
 */
export async function revokeUserSessions(userId) {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/revoke-sessions`, {
        method: 'POST',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to revoke sessions');
    }

    return response.json();
}

// =============================================================================
// Session Management API
// =============================================================================

/**
 * List active sessions (admin only)
 * @returns {Promise<{sessions: Array, total: number}>}
 */
export async function listActiveSessions() {
    const response = await fetch(`${API_BASE_URL}/admin/sessions`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch sessions');
    }

    return response.json();
}

/**
 * Revoke a single session (admin only)
 * @param {string} sessionId - Session ID
 */
export async function revokeSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/admin/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to revoke session');
    }

    return response.json();
}
