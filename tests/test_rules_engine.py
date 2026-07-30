import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.rules_engine import create_rule, _evaluate_single_rule, seed_default_rules, evaluate_rules
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from src.models import Base

@pytest.fixture
def temp_uow(tmp_path):
    db_file = tmp_path / "test_rules.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SQLAlchemyUnitOfWork(session_factory=SessionLocal)

def test_rule_matching_simpleeval():
    rule = {
        "name": "Test Rule",
        "condition_json": "amount > 50000 and type_risk_score >= 3"
    }
    # Should match
    assert _evaluate_single_rule(rule, {"amount": 60000, "type_risk_score": 4}) is True
    # Should not match
    assert _evaluate_single_rule(rule, {"amount": 40000, "type_risk_score": 4}) is False

def test_malicious_payload_rejected_at_creation(temp_uow):
    malicious_rules = [
        "__import__('os').system('ls')",
        "open('test.txt', 'w')",
        "eval('1+1')"
    ]
    
    for payload in malicious_rules:
        with pytest.raises(ValueError, match="Invalid expression|Invalid rule"):
            create_rule(
                uow=temp_uow,
                name=f"Malicious {payload}",
                description="Test",
                rule_type="compound",
                condition=payload,
                action="flag",
                risk_level_bump="HIGH",
                priority=50
            )

def test_malformed_rule_rejected(temp_uow):
    with pytest.raises(ValueError, match="Invalid rule syntax"):
        create_rule(
            uow=temp_uow,
            name="Bad Syntax",
            description="Test",
            rule_type="compound",
            condition="amount >>== 5",
            action="flag",
            risk_level_bump="HIGH",
            priority=50
        )

def test_undefined_feature_fails_closed():
    rule = {
        "name": "Test Undefined",
        "condition_json": "missing_feature > 50"
    }
    # It should not crash, it should just return False
    assert _evaluate_single_rule(rule, {"amount": 100}) is False
