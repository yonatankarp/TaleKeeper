"""Database package for TaleKeeper."""

from talekeeper.db.connection import get_db, init_db

__all__ = ["get_db", "init_db"]
