"""Shared test fixtures for TaleKeeper backend tests."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from talekeeper.db.connection import init_db


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path):
    """Point the database to a temporary file for each test."""
    db_path = tmp_path / "test.db"
    with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
        yield


@pytest_asyncio.fixture
async def client(tmp_path: Path):
    """Provide an httpx AsyncClient wired to the FastAPI app."""
    db_path = tmp_path / "test.db"
    with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
        await init_db()
        from talekeeper.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
