"""Shared test fixtures for TaleKeeper backend tests."""

import json as _json
import tempfile
from pathlib import Path
from unittest.mock import patch

import aiosqlite
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


@pytest_asyncio.fixture
async def db(tmp_path: Path):
    """Yield an initialized aiosqlite connection to a temp database."""
    db_path = tmp_path / "test.db"
    with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
        await init_db()
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys=ON")
            yield conn


async def create_campaign(
    db: aiosqlite.Connection,
    *,
    name: str = "Test Campaign",
    description: str = "",
    language: str = "en",
    num_speakers: int = 5,
) -> int:
    """Insert a campaign row and return the campaign ID."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name, description, language, num_speakers) VALUES (?, ?, ?, ?)",
        (name, description, language, num_speakers),
    )
    await db.commit()
    return cursor.lastrowid


async def create_session(
    db: aiosqlite.Connection,
    campaign_id: int,
    *,
    name: str = "Test Session",
    date: str = "2025-01-01",
    status: str = "draft",
    language: str = "en",
) -> int:
    """Insert a session row and return the session ID."""
    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date, status, language) VALUES (?, ?, ?, ?, ?)",
        (campaign_id, name, date, status, language),
    )
    await db.commit()
    return cursor.lastrowid


async def create_speaker(
    db: aiosqlite.Connection,
    session_id: int,
    *,
    diarization_label: str = "SPEAKER_00",
    player_name: str | None = None,
    character_name: str | None = None,
) -> int:
    """Insert a speaker row and return the speaker ID."""
    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) VALUES (?, ?, ?, ?)",
        (session_id, diarization_label, player_name, character_name),
    )
    await db.commit()
    return cursor.lastrowid


async def create_segment(
    db: aiosqlite.Connection,
    session_id: int,
    speaker_id: int | None = None,
    *,
    text: str = "Hello world",
    start_time: float = 0.0,
    end_time: float = 1.0,
) -> int:
    """Insert a transcript_segment row and return the segment ID."""
    cursor = await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
        (session_id, speaker_id, text, start_time, end_time),
    )
    await db.commit()
    return cursor.lastrowid


def parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into a list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = []
    for line in text.split("\n"):
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:"):].strip())
        elif line.strip() == "" and current_event is not None:
            data_str = "\n".join(current_data)
            try:
                data = _json.loads(data_str)
            except _json.JSONDecodeError:
                data = data_str
            events.append({"event": current_event, "data": data})
            current_event = None
            current_data = []
        elif line.startswith(":"):
            pass  # SSE comment/padding, ignore
    return events
