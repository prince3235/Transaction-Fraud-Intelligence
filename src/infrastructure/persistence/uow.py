from sqlalchemy.orm import Session
from src.application.ports.uow import AbstractUnitOfWork
from src.infrastructure.persistence.repository import (
    UserRepository,
    PredictionLogRepository,
    FraudCaseRepository,
    BusinessRuleRepository,
    OrganizationRepository,
    AuditLogRepository
)
from src.db import SessionLocal

class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work.
    Manages the database session lifecycle and initializes repositories.
    """
    
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.session: Session = None

    def __enter__(self):
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.prediction_logs = PredictionLogRepository(self.session)
        self.fraud_cases = FraudCaseRepository(self.session)
        self.business_rules = BusinessRuleRepository(self.session)
        self.organizations = OrganizationRepository(self.session)
        self.audit_logs = AuditLogRepository(self.session)
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, traceback):
        super().__exit__(exc_type, exc_val, traceback)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
