import json
import pytest
from unittest.mock import MagicMock, patch

from src.models import PredictionLog, CopilotLog
from src.llm_copilot import CopilotEngine, _log_copilot_query, _fetch_case_context, _explanation_cache

@pytest.fixture
def mock_db(db_session):
    # Insert a test prediction log
    tx_json = {"amount": 1000, "type": "TRANSFER"}
    log = PredictionLog(
        transaction_json=tx_json,
        ml_probability=0.95,
        final_risk_level="CRITICAL",
        ml_risk_level="CRITICAL",
        ml_risk_score=95,
        final_risk_score=95,
        policy_override_applied=True,
        policy_reasons_json=["Amount over threshold"],
        created_at="2026-07-05T10:00:00Z"
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return db_session, log.id

def test_fetch_case_context(mock_db):
    db_session, log_id = mock_db
    context = _fetch_case_context(None, prediction_log_id=log_id)
    assert context is not None
    assert context["prediction_log_id"] == log_id
    assert context["ml_probability"] == 0.95
    assert context["final_risk_level"] == "CRITICAL"
    assert context["policy_override_applied"] is True
    assert "Amount over threshold" in context["policy_reasons"]

def test_log_copilot_query(mock_db):
    db_session, log_id = mock_db
    _log_copilot_query(
        db_path=None,
        prediction_log_id=log_id,
        case_id=None,
        context={"test": "context"},
        response="This is a test response",
        latency_ms=150,
        is_cached=False,
        error=None,
        tokens_used=42
    )
    
    row = db_session.query(CopilotLog).first()
    assert row is not None
    assert row.prediction_log_id == log_id
    assert row.llm_response == "This is a test response"
    assert row.tokens_used == 42

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
@patch('src.llm_copilot.CopilotEngine._get_client')
@patch('src.llm_copilot.CopilotEngine._add_xai_to_context')
def test_copilot_explain_success(mock_add_xai, mock_get_client, mock_db):
    db_session, log_id = mock_db
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Mocked explanation of the transaction.")]
    mock_message.usage = MagicMock(input_tokens=10, output_tokens=20)
    mock_client.messages.create.return_value = mock_message
    
    mock_add_xai.side_effect = lambda x: x
    
    engine = CopilotEngine(db_path=None)
    result = engine.explain(prediction_log_id=log_id)
    
    assert result["error"] is None
    assert result["explanation"] == "Mocked explanation of the transaction."
    assert not result["is_cached"]
    assert result["latency_ms"] > 0
    
    row = db_session.query(CopilotLog).order_by(CopilotLog.id.desc()).first()
    assert row.llm_response == "Mocked explanation of the transaction."


@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
@patch('src.llm_copilot.CopilotEngine._get_client')
@patch('src.llm_copilot.CopilotEngine._add_xai_to_context')
def test_copilot_explain_timeout(mock_add_xai, mock_get_client, mock_db):
    db_session, log_id = mock_db
    _explanation_cache.clear()
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_client.messages.create.side_effect = TimeoutError("API timed out")
    mock_add_xai.side_effect = lambda x: x
    
    engine = CopilotEngine(db_path=None)
    result = engine.explain(prediction_log_id=log_id)
    
    assert result["error"] == "TIMEOUT"
    assert result["explanation"] is None
    
    row = db_session.query(CopilotLog).order_by(CopilotLog.id.desc()).first()
    assert row.error == "TIMEOUT"


def test_rag_retriever():
    """Verify TF-IDF & cosine similarity RAG retrieval returns relevant docs."""
    from src.llm_copilot import ComplianceKnowledgeRetriever
    retriever = ComplianceKnowledgeRetriever()
    results = retriever.retrieve("account balance reduced to zero transfer money laundering", top_k=2)
    assert len(results) > 0
    assert any("DOC-101" in d["id"] or "AML" in d["category"] for d in results)
