from fastapi import Depends
from src.application.ports.uow import AbstractUnitOfWork
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork

def get_uow() -> AbstractUnitOfWork:
    """
    Dependency that provides a new instance of the Unit of Work for each request.
    """
    return SQLAlchemyUnitOfWork()
