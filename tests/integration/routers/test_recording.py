"""Tests for recording and audio upload API endpoints."""

import io

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(db) -> dict:
    """Create campaign -> session. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 1', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_audio(client: AsyncClient, tmp_path) -> None:
    """POST /api/sessions/{id}/upload-audio accepts a multipart audio file."""
    async with get_db() as db:
        ids = await _seed(db)

    session_id = ids["session_id"]
    resp = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("test.mp3", io.BytesIO(b"fake-audio-data"), "audio/mpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio_path" in data
