"""Tests for speaker management API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(db) -> dict:
    """Create campaign -> session -> 2 speakers -> 2 segments. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    # Add a roster entry for speaker-suggestions testing
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    roster_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 1', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) "
        "VALUES (?, 'SPEAKER_00', 'Alice', 'Gandalf')",
        (session_id,),
    )
    speaker_a = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) "
        "VALUES (?, 'SPEAKER_01', 'Bob', 'Frodo')",
        (session_id,),
    )
    speaker_b = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'Hello there', 0.0, 1.0)",
        (session_id, speaker_a),
    )
    seg_a = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'General Kenobi', 1.0, 2.0)",
        (session_id, speaker_b),
    )
    seg_b = cursor.lastrowid

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "speaker_a": speaker_a,
        "speaker_b": speaker_b,
        "seg_a": seg_a,
        "seg_b": seg_b,
        "roster_id": roster_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_speakers(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/speakers returns all speakers for the session."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/speakers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    labels = {s["diarization_label"] for s in data}
    assert labels == {"SPEAKER_00", "SPEAKER_01"}


@pytest.mark.asyncio
async def test_update_speaker(client: AsyncClient) -> None:
    """PUT /api/speakers/{id} updates the speaker's player_name."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.put(
        f"/api/speakers/{ids['speaker_a']}",
        json={"player_name": "Bob"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_name"] == "Bob"
    assert data["id"] == ids["speaker_a"]


@pytest.mark.asyncio
async def test_reassign_segment_speaker(client: AsyncClient) -> None:
    """PUT /api/transcript-segments/{id}/speaker reassigns the segment."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.put(
        f"/api/transcript-segments/{ids['seg_a']}/speaker",
        json={"speaker_id": ids["speaker_b"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["speaker_id"] == ids["speaker_b"]


@pytest.mark.asyncio
async def test_bulk_reassign_segments(client: AsyncClient) -> None:
    """PUT /api/sessions/{id}/reassign-segments bulk-reassigns segments."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.put(
        f"/api/sessions/{ids['session_id']}/reassign-segments",
        json={"segment_ids": [ids["seg_a"], ids["seg_b"]], "speaker_id": ids["speaker_a"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2


@pytest.mark.asyncio
async def test_speaker_suggestions(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/speaker-suggestions returns campaign roster entries."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/speaker-suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [r["player_name"] for r in data]
    assert "Alice" in names
