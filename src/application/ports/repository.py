import abc
from typing import Generic, TypeVar, List, Optional, Any

T = TypeVar('T')

class AbstractRepository(Generic[T], abc.ABC):
    """
    Abstract Base Class for Repositories.
    Enforces a standard interface for data access.
    """
    
    @abc.abstractmethod
    def add(self, entity: T) -> T:
        """Add a new entity."""
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, id: Any) -> Optional[T]:
        """Get an entity by its primary key."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_all(self, **filters) -> List[T]:
        """Get all entities, optionally filtered."""
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, entity: T) -> None:
        """Delete an entity."""
        raise NotImplementedError
