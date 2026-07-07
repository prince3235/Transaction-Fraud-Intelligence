import json
from pathlib import Path
import pytest
from src.rules_engine import create_rule, _evaluate_single_rule, seed_default_rules, evaluate_rules

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_rules.db"
    # To use rules_engine properly, it expects the db schema to exist.
    import sqlite3
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS business_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            rule_type       TEXT NOT NULL DEFAULT 'threshold',
            condition_json  TEXT NOT NULL DEFAULT '{}',
            action          TEXT NOT NULL DEFAULT 'flag',
            risk_level_bump TEXT NOT NULL DEFAULT 'MEDIUM',
            priority        INTEGER NOT NULL DEFAULT 50,
            is_active       INTEGER NOT NULL DEFAULT 1,
            triggered_count INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()
    return db_file

def test_rule_matching_simpleeval():
    rule = {
        "name": "Test Rule",
        "condition_json": "amount > 50000 and type_risk_score >= 3"
    }
    # Should match
    assert _evaluate_single_rule(rule, {"amount": 60000, "type_risk_score": 4}) is True
    # Should not match
    assert _evaluate_single_rule(rule, {"amount": 40000, "type_risk_score": 4}) is False

def test_malicious_payload_rejected_at_creation(temp_db):
    malicious_rules = [
        "__import__('os').system('ls')",
        "open('test.txt', 'w')",
        "eval('1+1')"
    ]
    
    for payload in malicious_rules:
        with pytest.raises(ValueError, match="Invalid expression|Invalid rule"):
            create_rule(
                db_path=temp_db,
                name=f"Malicious {payload}",
                description="Test",
                rule_type="compound",
                condition=payload,
                action="flag",
                risk_level_bump="HIGH",
                priority=50
            )

def test_malformed_rule_rejected(temp_db):
    with pytest.raises(ValueError, match="Invalid rule syntax"):
        create_rule(
            db_path=temp_db,
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
