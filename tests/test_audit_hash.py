import pytest
from src.auth import calculate_audit_log_hash, verify_audit_log_chain, log_audit_event
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork

def test_audit_log_hash_chaining(db_session):
    """Verify SHA-256 Merkle chain calculation and audit log integrity check."""
    uow = SQLAlchemyUnitOfWork(session_factory=lambda: db_session)
    
    log_audit_event(uow, username="admin_test", action="LOGIN", ip_address="127.0.0.1")
    log_audit_event(uow, username="admin_test", action="UPDATE_POLICY", reason="Risk threshold update")
    
    result = verify_audit_log_chain(uow)
    assert result["total_logs_verified"] >= 2
    assert result["chain_valid"] is True
    assert len(result["latest_head_hash"]) == 64  # SHA-256 hex string length
