from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .sqlite_adapter import SQLiteDatabase


class DatabaseConnection(Protocol):
    provider: str
    db: object

    async def close(self) -> None:
        ...


class MongoDatabaseConnection:
    """Motor/MongoDB connection provider."""

    provider = "mongo"

    def __init__(self) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")

        if not mongo_url:
            raise ValueError("MONGO_URL is required when DB_BACKEND=mongo")
        if not db_name:
            raise ValueError("DB_NAME is required when DB_BACKEND=mongo")

        timeout_ms = int(os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000"))
        self.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=timeout_ms,
        )
        self.db = self.client[db_name]

    async def close(self) -> None:
        self.client.close()


class SQLiteDatabaseConnection:
    """SQLite connection provider for local demo mode."""

    provider = "sqlite"

    def __init__(self, backend_dir: Path) -> None:
        configured_path = os.environ.get("SQLITE_DB_PATH")
        db_path = Path(configured_path) if configured_path else backend_dir / "cloudcatcher.sqlite3"
        if not db_path.is_absolute():
            db_path = backend_dir / db_path

        self.db = SQLiteDatabase(db_path)
        self.db.initialize()

    async def close(self) -> None:
        await self.db.close()


def create_database_connection(backend_dir: Path) -> DatabaseConnection:
    """Create the configured database connection.

    `sqlite` is the default because the local demo should work without an
    external service. Set `DB_BACKEND=mongo` to use the existing MongoDB path.
    """

    provider = os.environ.get("DB_BACKEND", "sqlite").strip().lower()

    if provider in {"sqlite", "sqlite3"}:
        return SQLiteDatabaseConnection(backend_dir)
    if provider in {"mongo", "mongodb"}:
        return MongoDatabaseConnection()

    raise ValueError(f"Unsupported DB_BACKEND: {provider}")
