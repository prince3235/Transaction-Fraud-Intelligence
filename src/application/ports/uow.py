import abc
from .repository import AbstractRepository

class AbstractUnitOfWork(abc.ABC):
    """
    Abstract Base Class for Unit of Work.
    Ensures that all operations within a block are treated as a single transaction.
    """
    
    # We will declare repositories here that the UoW manages.
    # We'll use Any for type hints temporarily until specific repositories are created,
    # or define base repository properties.
    users: AbstractRepository
    prediction_logs: AbstractRepository
    fraud_cases: AbstractRepository
    business_rules: AbstractRepository
    organizations: AbstractRepository
    audit_logs: AbstractRepository

    def __enter__(self) -> 'AbstractUnitOfWork':
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.rollback()
        # Optionally, we can decide to auto-commit on success, 
        # but typically explicit commit is safer for financial systems.

    @abc.abstractmethod
    def commit(self):
        """Commit the current transaction."""
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        """Rollback the current transaction."""
        raise NotImplementedError
