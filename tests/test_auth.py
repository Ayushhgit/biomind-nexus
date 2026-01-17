"""
BioMind Nexus - Authentication Test Suite

Comprehensive tests for:
- Login success/failure scenarios
- Session management
- RBAC enforcement
- Security attack prevention

Run with: pytest tests/test_auth.py -v
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from backend.auth.models import User, Session, Role
from backend.auth.password import hash_password, verify_password, needs_rehash
from backend.auth.tokens import create_access_token, verify_access_token, InvalidTokenError
from backend.auth import sessions as session_service
from tests.conftest import login_user, auth_headers


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================

class TestPasswordHashing:
    """Unit tests for bcrypt password utilities."""
    
    def test_hash_password_creates_bcrypt_hash(self):
        """Password hashing creates valid bcrypt hash."""
        hashed = hash_password("SecurePassword123")
        
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
    
    def test_verify_password_correct(self):
        """Correct password verification returns True."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password verification returns False."""
        hashed = hash_password("SecurePassword123")
        
        assert verify_password("WrongPassword", hashed) is False
    
    def test_verify_password_empty_string(self):
        """Empty password fails verification."""
        hashed = hash_password("SecurePassword123")
        
        assert verify_password("", hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Same password generates different hashes (salted)."""
        password = "SecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_needs_rehash_old_work_factor(self):
        """Detects when password needs rehashing."""
        # Create hash with work factor 10 (simulated old hash)
        import bcrypt
        old_hash = bcrypt.hashpw(b"password", bcrypt.gensalt(rounds=10)).decode()
        
        assert needs_rehash(old_hash, target_work_factor=12) is True
    
    def test_needs_rehash_current_factor(self):
        """Current work factor doesn't need rehash."""
        current_hash = hash_password("password")
        
        assert needs_rehash(current_hash) is False


# =============================================================================
# JWT TOKEN TESTS
# =============================================================================

class TestJWTTokens:
    """Unit tests for JWT token creation and validation."""
    
    def test_create_access_token_returns_string(self):
        """Token creation returns valid JWT string and token ID."""
        user_id = uuid4()
        session_id = uuid4()
        
        token, jti = create_access_token(user_id, "researcher", session_id)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT has header.payload.signature
        assert len(jti) == 32  # Hex token ID
    
    def test_verify_access_token_valid(self):
        """Valid token verification returns payload."""
        user_id = uuid4()
        session_id = uuid4()
        
        token, jti = create_access_token(user_id, "researcher", session_id)
        payload = verify_access_token(token)
        
        assert payload.sub == str(user_id)
        assert payload.role == "researcher"
        assert payload.sid == str(session_id)
        assert payload.jti == jti
    
    def test_verify_access_token_invalid(self):
        """Invalid token raises exception."""
        with pytest.raises(InvalidTokenError):
            verify_access_token("invalid.token.here")
    
    def test_verify_access_token_tampered(self):
        """Tampered token raises exception."""
        user_id = uuid4()
        session_id = uuid4()
        
        token, _ = create_access_token(user_id, "researcher", session_id)
        
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1] + "tampered"
        tampered_token = ".".join(parts)
        
        with pytest.raises(InvalidTokenError):
            verify_access_token(tampered_token)
    
    def test_token_contains_session_id(self):
        """Token payload includes session ID for server-side validation."""
        user_id = uuid4()
        session_id = uuid4()
        
        token, _ = create_access_token(user_id, "admin", session_id)
        payload = verify_access_token(token)
        
        assert payload.sid == str(session_id)


# =============================================================================
# LOGIN ENDPOINT TESTS
# =============================================================================

class TestLoginEndpoint:
    """Integration tests for POST /auth/login."""
    
    def test_login_success(self, client, test_researcher):
        """Successful login returns token and session."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "researcher@test.com",
                "password": "ResearchPass123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "session_id" in data
        assert data["expires_in"] > 0
    
    def test_login_invalid_password(self, client, test_researcher):
        """Invalid password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "researcher@test.com",
                "password": "WrongPassword123",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_user_not_found(self, client):
        """Non-existent user returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "SomePassword123",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_inactive_user(self, client, inactive_user):
        """Inactive user returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@test.com",
                "password": "InactivePass123",
            },
        )
        
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()
    
    def test_login_short_password_rejected(self, client):
        """Password less than 8 characters is rejected."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "short",
            },
        )
        
        assert response.status_code == 422  # Validation error


# =============================================================================
# LOGOUT ENDPOINT TESTS
# =============================================================================

class TestLogoutEndpoint:
    """Integration tests for POST /auth/logout."""
    
    def test_logout_invalidates_session(self, client, test_researcher):
        """Logout invalidates the session."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "researcher@test.com",
                "password": "ResearchPass123",
            },
        )
        tokens = login_response.json()
        
        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(tokens["access_token"], tokens["session_id"]),
        )
        
        assert logout_response.status_code == 200
        assert logout_response.json()["sessions_invalidated"] == 1
    
    def test_request_after_logout_fails(self, client, test_researcher):
        """Requests after logout are rejected."""
        # Login
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        headers = auth_headers(tokens["access_token"], tokens["session_id"])
        
        # Access protected endpoint (should work)
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # Logout
        client.post("/api/v1/auth/logout", headers=headers)
        
        # Try to access again (should fail)
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 401
    
    def test_logout_all_sessions(self, client, test_researcher):
        """Logout all sessions invalidates all active sessions."""
        # Create multiple sessions
        tokens1 = login_user(client, "researcher@test.com", "ResearchPass123")
        tokens2 = login_user(client, "researcher@test.com", "ResearchPass123")
        
        # Logout all from first session
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(tokens1["access_token"], tokens1["session_id"]),
            json={"all_sessions": True},
        )
        
        assert response.status_code == 200
        assert response.json()["sessions_invalidated"] >= 2
        
        # Both sessions should now be invalid
        me1 = client.get(
            "/api/v1/auth/me",
            headers=auth_headers(tokens1["access_token"], tokens1["session_id"]),
        )
        me2 = client.get(
            "/api/v1/auth/me",
            headers=auth_headers(tokens2["access_token"], tokens2["session_id"]),
        )
        
        assert me1.status_code == 401
        assert me2.status_code == 401


# =============================================================================
# SESSION VALIDATION TESTS
# =============================================================================

class TestSessionValidation:
    """Tests for session validation logic."""
    
    def test_missing_session_header_rejected(self, client, test_researcher):
        """Requests without X-Session-ID are rejected."""
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            # Missing X-Session-ID
        )
        
        assert response.status_code == 401
        assert "session" in response.json()["detail"].lower()
    
    def test_mismatched_session_rejected(self, client, test_researcher):
        """Token with wrong session ID is rejected."""
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        
        response = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "X-Session-ID": str(uuid4()),  # Wrong session ID
            },
        )
        
        assert response.status_code == 401


# =============================================================================
# RBAC PERMISSION TESTS
# =============================================================================

class TestRBACPermissions:
    """Tests for role-based access control."""
    
    def test_admin_can_create_user(self, client, db_session, test_admin):
        """Admin role can create new users."""
        tokens = login_user(client, "admin@test.com", "AdminPass123")
        
        response = client.post(
            "/api/v1/auth/users",
            headers=auth_headers(tokens["access_token"], tokens["session_id"]),
            json={
                "email": "newuser@test.com",
                "password": "NewUserPass123",
                "role": "researcher",
            },
        )
        
        assert response.status_code == 201
        assert response.json()["email"] == "newuser@test.com"
    
    def test_researcher_cannot_create_user(self, client, test_researcher):
        """Researcher role cannot create users."""
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        
        response = client.post(
            "/api/v1/auth/users",
            headers=auth_headers(tokens["access_token"], tokens["session_id"]),
            json={
                "email": "newuser@test.com",
                "password": "NewUserPass123",
                "role": "researcher",
            },
        )
        
        assert response.status_code == 403
        assert "Permission denied" in response.json()["detail"]
    
    def test_auditor_cannot_create_user(self, client, test_auditor):
        """Auditor role cannot create users."""
        tokens = login_user(client, "auditor@test.com", "AuditPass123")
        
        response = client.post(
            "/api/v1/auth/users",
            headers=auth_headers(tokens["access_token"], tokens["session_id"]),
            json={
                "email": "newuser@test.com",
                "password": "NewUserPass123",
                "role": "researcher",
            },
        )
        
        assert response.status_code == 403


# =============================================================================
# SECURITY ATTACK TESTS
# =============================================================================

class TestSecurityAttacks:
    """Tests for security vulnerabilities."""
    
    def test_token_replay_after_logout(self, client, test_researcher):
        """Token replay after logout is blocked."""
        # Login and get token
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        headers = auth_headers(tokens["access_token"], tokens["session_id"])
        
        # Verify token works
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
        
        # Logout
        client.post("/api/v1/auth/logout", headers=headers)
        
        # Attempt token replay
        replay_response = client.get("/api/v1/auth/me", headers=headers)
        
        assert replay_response.status_code == 401
    
    def test_role_escalation_blocked(self, client, test_researcher, test_admin):
        """Users cannot escalate their own role."""
        # Login as researcher
        tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        headers = auth_headers(tokens["access_token"], tokens["session_id"])
        
        # Try to create an admin user (requires manage:users permission)
        response = client.post(
            "/api/v1/auth/users",
            headers=headers,
            json={
                "email": "hacker@test.com",
                "password": "HackerPass123",
                "role": "admin",  # Trying to create admin
            },
        )
        
        assert response.status_code == 403
    
    def test_invalid_jwt_rejected(self, client):
        """Completely invalid JWT is rejected."""
        response = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer totally.invalid.token",
                "X-Session-ID": str(uuid4()),
            },
        )
        
        assert response.status_code == 401
    
    def test_missing_authorization_header(self, client):
        """Missing Authorization header is rejected."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"X-Session-ID": str(uuid4())},
        )
        
        assert response.status_code == 401
    
    def test_sql_injection_email_blocked(self, client):
        """SQL injection in email is blocked."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "'; DROP TABLE users; --",
                "password": "password123",
            },
        )
        
        # Should fail validation (not a valid email)
        assert response.status_code == 422
    
    def test_cross_user_session_access_blocked(self, client, test_researcher, test_admin):
        """User cannot use another user's session."""
        # Login both users
        researcher_tokens = login_user(client, "researcher@test.com", "ResearchPass123")
        admin_tokens = login_user(client, "admin@test.com", "AdminPass123")
        
        # Try using admin's session ID with researcher's token
        response = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {researcher_tokens['access_token']}",
                "X-Session-ID": admin_tokens["session_id"],  # Wrong session
            },
        )
        
        assert response.status_code == 401


# =============================================================================
# INTEGRATION FLOW TEST
# =============================================================================

class TestFullAuthFlow:
    """End-to-end integration tests."""
    
    def test_full_auth_flow_login_action_logout_retry(self, client, test_researcher):
        """
        Complete authentication flow:
        1. Login
        2. Access protected resource
        3. Logout
        4. Retry access (must fail)
        """
        # Step 1: Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "researcher@test.com",
                "password": "ResearchPass123",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        headers = auth_headers(tokens["access_token"], tokens["session_id"])
        
        # Step 2: Access protected resource
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "researcher@test.com"
        
        # Step 3: Logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # Step 4: Retry access (must fail)
        retry_response = client.get("/api/v1/auth/me", headers=headers)
        assert retry_response.status_code == 401
    
    def test_multiple_concurrent_sessions(self, client, test_researcher):
        """User can have multiple concurrent sessions."""
        # Create 3 sessions
        sessions = []
        for _ in range(3):
            tokens = login_user(client, "researcher@test.com", "ResearchPass123")
            sessions.append(tokens)
        
        # All sessions should work
        for tokens in sessions:
            response = client.get(
                "/api/v1/auth/me",
                headers=auth_headers(tokens["access_token"], tokens["session_id"]),
            )
            assert response.status_code == 200
        
        # Invalidate first session
        client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(sessions[0]["access_token"], sessions[0]["session_id"]),
        )
        
        # First session should fail
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers(sessions[0]["access_token"], sessions[0]["session_id"]),
        )
        assert response.status_code == 401
        
        # Other sessions should still work
        for tokens in sessions[1:]:
            response = client.get(
                "/api/v1/auth/me",
                headers=auth_headers(tokens["access_token"], tokens["session_id"]),
            )
            assert response.status_code == 200
