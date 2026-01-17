"""
BioMind Nexus - Audit Integrity Tests

Tests for audit log integrity and hash chain verification.
Ensures tamper-evidence and chain validation work correctly.

Run with: pytest tests/test_audit_integrity.py
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock

from backend.audit.hash_chain import (
    compute_event_hash,
    compute_genesis_hash,
    verify_chain,
)


class TestHashComputation:
    """Tests for hash computation functions."""
    
    def test_compute_event_hash_deterministic(self):
        """Same inputs should produce same hash."""
        hash1 = compute_event_hash(
            event_id="123",
            event_type="query",
            user_id="user1",
            action="invoke_agent",
            prev_hash="abc123",
        )
        
        hash2 = compute_event_hash(
            event_id="123",
            event_type="query",
            user_id="user1",
            action="invoke_agent",
            prev_hash="abc123",
        )
        
        assert hash1 == hash2
    
    def test_compute_event_hash_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = compute_event_hash(
            event_id="123",
            event_type="query",
            user_id="user1",
            action="invoke_agent",
            prev_hash="abc123",
        )
        
        hash2 = compute_event_hash(
            event_id="124",  # Different event_id
            event_type="query",
            user_id="user1",
            action="invoke_agent",
            prev_hash="abc123",
        )
        
        assert hash1 != hash2
    
    def test_genesis_hash_includes_date(self):
        """Genesis hash should be different for different dates."""
        hash1 = compute_genesis_hash(date(2024, 1, 1))
        hash2 = compute_genesis_hash(date(2024, 1, 2))
        
        assert hash1 != hash2
    
    def test_genesis_hash_deterministic(self):
        """Same date should produce same genesis hash."""
        hash1 = compute_genesis_hash(date(2024, 1, 1))
        hash2 = compute_genesis_hash(date(2024, 1, 1))
        
        assert hash1 == hash2


class TestChainVerification:
    """Tests for hash chain verification."""
    
    @pytest.mark.asyncio
    async def test_empty_chain_valid(self):
        """Empty chain should be considered valid."""
        mock_session = MagicMock()
        mock_session.execute.return_value = iter([])  # No events
        
        result = await verify_chain(mock_session, date(2024, 1, 1))
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_broken_chain_detected(self):
        """Modified events should break the chain."""
        # TODO: Implement with proper chain setup
        pass
    
    @pytest.mark.asyncio
    async def test_valid_chain_passes(self):
        """Properly chained events should pass verification."""
        # TODO: Implement with proper chain setup
        pass
