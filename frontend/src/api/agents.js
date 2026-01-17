/**
 * BioMind Nexus - Agents API Client
 * 
 * Handles all drug repurposing workflow requests to the FastAPI backend.
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

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

/**
 * Submit a drug repurposing query
 * @param {string} query - Natural language query
 * @param {Object} options - Query options
 * @returns {Promise<QueryResponse>}
 */
export async function submitQuery(query, options = {}) {
    const response = await fetch(`${API_BASE_URL}/agents/query`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
            query,
            max_candidates: options.maxCandidates || 10,
            min_confidence: options.minConfidence || 0.5,
            include_experimental: options.includeExperimental || false,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Query submission failed');
    }

    return response.json();
}

/**
 * Get example queries for the UI
 * @returns {Promise<{examples: Array}>}
 */
export async function getExampleQueries() {
    const response = await fetch(`${API_BASE_URL}/agents/examples`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get examples');
    }

    return response.json();
}

/**
 * Get available entity types
 * @returns {Promise<{entity_types: Array}>}
 */
export async function getEntityTypes() {
    const response = await fetch(`${API_BASE_URL}/agents/entities/types`, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get entity types');
    }

    return response.json();
}

/**
 * Get knowledge graph nodes (for visualization)
 * @param {string} entityType - Filter by entity type (drug, disease, gene)
 * @returns {Promise<Array>}
 */
export async function getGraphNodes(entityType = null) {
    const url = new URL(`${API_BASE_URL}/graph/nodes`);
    if (entityType) {
        url.searchParams.append('entity_type', entityType);
    }

    const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
    });

    if (!response.ok) {
        // Graph endpoint may not exist yet
        return { nodes: [], edges: [] };
    }

    return response.json();
}
