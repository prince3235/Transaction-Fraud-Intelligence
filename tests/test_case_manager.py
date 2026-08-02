import pytest
from src.case_manager import create_case, get_sla_metrics
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork

def test_case_creation_and_sla_metrics(db_session):
    """Verify case creation and SLA compliance metrics calculation."""
    uow = SQLAlchemyUnitOfWork(session_factory=lambda: db_session)
    
    case_dict = create_case(
        uow=uow,
        prediction_log_id=None,
        title="High Velocity Test Fraud Case",
        description="Testing SLA breach calculation",
        priority="Critical",
        created_by="analyst_test",
    )
    
    assert case_dict["case_id"].startswith("FCS-")
    assert case_dict["priority"] == "Critical"
    assert case_dict["status"] == "Open"
    
    sla_data = get_sla_metrics(uow)
    assert sla_data["total_active_cases"] >= 1
    assert "compliance_percentage" in sla_data
    assert "breached_count" in sla_data
