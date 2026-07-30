from typing import TypeVar, Type, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.application.ports.repository import AbstractRepository
from src.models import (
    User, PredictionLog, FraudCase, BusinessRule, Organization, AuditLog
)

T = TypeVar('T')

class SQLAlchemyRepository(AbstractRepository[T]):
    """
    Generic SQLAlchemy Implementation of the AbstractRepository.
    """
    
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    def get(self, id: Any) -> Optional[T]:
        return self.session.get(self.model_class, id)

    def get_all(self, **filters) -> List[T]:
        stmt = select(self.model_class)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model_class, key) == value)
        return self.session.execute(stmt).scalars().all()

    def update(self, entity: T) -> T:
        # With SQLAlchemy, if the entity is already attached to the session,
        # changes are tracked automatically. This explicit method can be used
        # if the entity is detached, or simply for API completeness.
        self.session.add(entity)
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)

class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: Session):
        super().__init__(session, User)
        
    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.session.execute(stmt).scalars().first()

class PredictionLogRepository(SQLAlchemyRepository[PredictionLog]):
    def __init__(self, session: Session):
        super().__init__(session, PredictionLog)
        
    def get_recent(self, limit: int = 50) -> List[PredictionLog]:
        stmt = select(PredictionLog).order_by(PredictionLog.id.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()

class FraudCaseRepository(SQLAlchemyRepository[FraudCase]):
    def __init__(self, session: Session):
        super().__init__(session, FraudCase)
        
    def get_by_case_id(self, case_id: str) -> Optional[FraudCase]:
        stmt = select(FraudCase).where(FraudCase.case_id == case_id)
        return self.session.execute(stmt).scalars().first()

class BusinessRuleRepository(SQLAlchemyRepository[BusinessRule]):
    def __init__(self, session: Session):
        super().__init__(session, BusinessRule)

class OrganizationRepository(SQLAlchemyRepository[Organization]):
    def __init__(self, session: Session):
        super().__init__(session, Organization)

class AuditLogRepository(SQLAlchemyRepository[AuditLog]):
    def __init__(self, session: Session):
        super().__init__(session, AuditLog)
        
    def get_recent(self, limit: int = 200, **filters) -> List[AuditLog]:
        stmt = select(AuditLog)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(AuditLog, key) == value)
        stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()
