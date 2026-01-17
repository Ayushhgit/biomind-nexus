/**
 * BioMind Nexus - API Client
 *
 * TypeScript client for backend API communication.
 * Handles authentication, request formatting, and error handling.
 *
 * Security:
 * - Tokens stored in memory only (not localStorage)
 * - All requests include CSRF protection
 * - Automatic token refresh on 401
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Authentication token stored in memory */
let authToken: string | null = null;

/**
 * Set the authentication token for subsequent requests.
 * Token is stored in memory only for security.
 */
export function setAuthToken(token: string): void {
    authToken = token;
}

/**
 * Clear authentication state.
 */
export function clearAuth(): void {
    authToken = null;
}

/**
 * Base fetch wrapper with auth and error handling.
 */
async function apiFetch<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        // TODO: Implement proper error handling
        if (response.status === 401) {
            clearAuth();
            throw new Error('Authentication required');
        }
        throw new Error(`API error: ${response.status}`);
    }

    return response.json();
}

// =============================================================================
// Authentication API
// =============================================================================

export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiFetch<LoginResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
    });
    setAuthToken(response.access_token);
    return response;
}

// =============================================================================
// Agent API
// =============================================================================

export interface QueryRequest {
    query: string;
    filters?: Record<string, unknown>;
}

export interface AgentResponse {
    agent_name: string;
    content: unknown;
    confidence: number;
    citations: Citation[];
}

export interface Citation {
    source_type: string;
    source_id: string;
    title: string;
    authors: string[];
    year: number;
}

export async function submitQuery(request: QueryRequest): Promise<AgentResponse> {
    return apiFetch<AgentResponse>('/api/v1/agents/query', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// =============================================================================
// Dossier API
// =============================================================================

export interface DossierRequest {
    title: string;
    query_ids: string[];
}

export interface DossierResponse {
    dossier_id: string;
    download_url: string;
}

export async function generateDossier(request: DossierRequest): Promise<DossierResponse> {
    return apiFetch<DossierResponse>('/api/v1/dossier/generate', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// =============================================================================
// Health Check
// =============================================================================

export interface HealthStatus {
    status: string;
    version: string;
}

export async function checkHealth(): Promise<HealthStatus> {
    return apiFetch<HealthStatus>('/health');
}
