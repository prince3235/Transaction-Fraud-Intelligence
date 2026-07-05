import json
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.llm_copilot import CopilotEngine, _log_copilot_query, _fetch_case_context

@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "test_fraud.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Create required tables
    cur.execute("""
        CREATE TABLE prediction_logs (
            id INTEGER PRIMARY KEY,
            transaction_json TEXT,
            ml_probability REAL,
            final_risk_level TEXT,
            policy_override_applied INTEGER,
            policy_reasons_json TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE copilot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            prediction_log_id INTEGER,
            query_context_json TEXT NOT NULL,
            llm_response TEXT,
            model_used TEXT NOT NULL DEFAULT 'claude-sonnet-4-6',
            tokens_used INTEGER,
            latency_ms INTEGER,
            is_cached INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Insert a test prediction log
    tx_json = json.dumps({"amount": 1000, "type": "TRANSFER"})
    cur.execute(
        "INSERT INTO prediction_logs (id, transaction_json, ml_probability, final_risk_level, policy_override_applied, policy_reasons_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, tx_json, 0.95, "CRITICAL", 1, '["Amount over threshold"]', "2026-07-05T10:00:00Z")
    )
    
    con.commit()
    con.close()
    return db_path

def test_fetch_case_context(mock_db):
    context = _fetch_case_context(mock_db, prediction_log_id=1)
    assert context is not None
    assert context["prediction_log_id"] == 1
    assert context["ml_probability"] == 0.95
    assert context["final_risk_level"] == "CRITICAL"
    assert context["policy_override_applied"] is True
    assert "Amount over threshold" in context["policy_reasons"]

def test_log_copilot_query(mock_db):
    _log_copilot_query(
        db_path=mock_db,
        prediction_log_id=1,
        case_id=None,
        context={"test": "context"},
        response="This is a test response",
        latency_ms=150,
        is_cached=False,
        error=None,
        tokens_used=42
    )
    
    con = sqlite3.connect(mock_db)
    cur = con.cursor()
    row = cur.execute("SELECT * FROM copilot_logs").fetchone()
    con.close()
    
    assert row is not None
    assert row[2] == 1  # prediction_log_id
    assert row[4] == "This is a test response"
    assert row[6] == 42  # tokens_used

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
@patch('src.llm_copilot.CopilotEngine._get_client')
@patch('src.llm_copilot.CopilotEngine._add_xai_to_context')
def test_copilot_explain_success(mock_add_xai, mock_get_client, mock_db):
    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Setup mock API response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Mocked explanation of the transaction.")]
    mock_message.usage = MagicMock(input_tokens=10, output_tokens=20)
    mock_client.messages.create.return_value = mock_message
    
    # Pass through context unmodified
    mock_add_xai.side_effect = lambda x: x
    
    engine = CopilotEngine(db_path=mock_db)
    result = engine.explain(prediction_log_id=1)
    
    assert result["error"] is None
    assert result["explanation"] == "Mocked explanation of the transaction."
    assert not result["is_cached"]
    assert result["latency_ms"] > 0
    
    # Check that it was logged
    con = sqlite3.connect(mock_db)
    cur = con.cursor()
    row = cur.execute("SELECT llm_response FROM copilot_logs").fetchone()
    con.close()
    assert row[0] == "Mocked explanation of the transaction."

from src.llm_copilot import CopilotEngine, _log_copilot_query, _fetch_case_context, _explanation_cache

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
@patch('src.llm_copilot.CopilotEngine._get_client')
@patch('src.llm_copilot.CopilotEngine._add_xai_to_context')
def test_copilot_explain_timeout(mock_add_xai, mock_get_client, mock_db):
    _explanation_cache.clear()
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Force a timeout exception
    mock_client.messages.create.side_effect = TimeoutError("API timed out")
    
    mock_add_xai.side_effect = lambda x: x
    
    engine = CopilotEngine(db_path=mock_db)
    result = engine.explain(prediction_log_id=1)
    
    assert result["error"] == "TIMEOUT"
    assert result["explanation"] is None
    
    # Check that the error was logged
    con = sqlite3.connect(mock_db)
    cur = con.cursor()
    row = cur.execute("SELECT error FROM copilot_logs").fetchone()
    con.close()
    assert row[0] == "TIMEOUT"
