"""Database foundation for enterprise access-control services."""

from .session import database_available, get_database_manager

__all__ = ["database_available", "get_database_manager"]
