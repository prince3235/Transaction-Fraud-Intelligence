from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator, JSON

Base = declarative_base()

class FlexibleJSON(TypeDecorator):
    """
    Use JSONB for PostgreSQL, but fallback to generic JSON for SQLite (if ever used).
    """
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, nullable=False)
    transaction_json = Column(FlexibleJSON, nullable=False)
    ml_probability = Column(Float, nullable=False)
    ml_risk_level = Column(String, nullable=False)
    ml_risk_score = Column(Integer, nullable=False)
    final_risk_level = Column(String, nullable=False)
    final_risk_score = Column(Integer, nullable=False)
    policy_override_applied = Column(Boolean, nullable=False)
    policy_reasons_json = Column(FlexibleJSON, nullable=False)
    suspicious_signal_count = Column(Integer)
    alert_json = Column(FlexibleJSON)
    status = Column(String, nullable=False, default="APPROVED")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='Viewer')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(String, nullable=False)
    last_login = Column(String)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(String)
    old_value_json = Column(FlexibleJSON)
    new_value_json = Column(FlexibleJSON)
    ip_address = Column(String, default="127.0.0.1")
    reason = Column(String)
    timestamp = Column(String, nullable=False)

class FraudCase(Base):
    __tablename__ = "fraud_cases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, unique=True, nullable=False)
    prediction_log_id = Column(Integer, ForeignKey("prediction_logs.id"))
    status = Column(String, nullable=False, default="Open")
    priority = Column(String, nullable=False, default="Medium")
    assigned_to = Column(String)
    title = Column(String, nullable=False)
    description = Column(String)
    evidence_json = Column(FlexibleJSON, default=[])
    notes_json = Column(FlexibleJSON, default=[])
    timeline_json = Column(FlexibleJSON, default=[])
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    resolved_at = Column(String)

class BusinessRule(Base):
    __tablename__ = "business_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False, default="")
    rule_type = Column(String, nullable=False, default="threshold")
    condition_json = Column(String, nullable=False, default="") # String instead of JSON for rules engine
    action = Column(String, nullable=False, default="flag")
    risk_level_bump = Column(String, nullable=False, default="MEDIUM")
    priority = Column(Integer, nullable=False, default=50)
    is_active = Column(Boolean, nullable=False, default=True)
    triggered_count = Column(Integer, nullable=False, default=0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, unique=True, nullable=False)
    pkl_path = Column(String, nullable=False)
    roc_auc = Column(Float)
    pr_auc = Column(Float)
    precision_val = Column(Float)
    recall_val = Column(Float)
    f1_val = Column(Float)
    n_estimators = Column(Integer)
    training_date = Column(String, nullable=False)
    dataset_size = Column(Integer)
    feature_count = Column(Integer)
    notes = Column(String)
    is_production = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(String, nullable=False)

class DriftSnapshot(Base):
    __tablename__ = "drift_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String, nullable=False)
    feature_name = Column(String, nullable=False)
    psi_score = Column(Float, nullable=False)
    alert_triggered = Column(Boolean, nullable=False, default=False)
    baseline_mean = Column(Float)
    current_mean = Column(Float)
    baseline_std = Column(Float)
    current_std = Column(Float)
    created_at = Column(String, nullable=False)

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, unique=True, nullable=False)
    total_transactions = Column(Integer, nullable=False, default=0)
    fraud_count = Column(Integer, nullable=False, default=0)
    avg_amount = Column(Float, nullable=False, default=0.0)
    max_amount = Column(Float, nullable=False, default=0.0)
    risk_score_avg = Column(Float, nullable=False, default=0.0)
    last_transaction_at = Column(String)
    first_transaction_at = Column(String)
    risk_trend = Column(String, nullable=False, default="STABLE")
    device_count = Column(Integer, nullable=False, default=1)
    country_count = Column(Integer, nullable=False, default=1)
    updated_at = Column(String, nullable=False)

class AnalystMetric(Base):
    __tablename__ = "analyst_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    cases_resolved = Column(Integer, nullable=False, default=0)
    avg_resolution_mins = Column(Float, nullable=False, default=0.0)
    false_positive_count = Column(Integer, nullable=False, default=0)
    true_positive_count = Column(Integer, nullable=False, default=0)
    cases_escalated = Column(Integer, nullable=False, default=0)
    period = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class CopilotLog(Base):
    __tablename__ = "copilot_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String)
    prediction_log_id = Column(Integer)
    query_context_json = Column(FlexibleJSON, nullable=False)
    llm_response = Column(String)
    model_used = Column(String, nullable=False, default="claude-sonnet-4-5")
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    is_cached = Column(Boolean, nullable=False, default=False)
    error = Column(String)
    created_at = Column(String, nullable=False)
