"""Integration tests for transcript API endpoints."""

import pytest
from httpx import AsyncClient

from talekeeper.db import get_db


@pytest.mark.asyncio
async def test_get_transcript_with_segments(client: AsyncClient) -> None:
    # Seed data via direct DB access
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES ('C')"
        )
        campaign_id = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'S', '2025-01-01')",
            (campaign_id,),
        )
        session_id = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO speakers (session_id, diarization_label, player_name) VALUES (?, 'SPEAKER_00', 'Alice')",
            (session_id,),
        )
        speaker_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) VALUES (?, ?, 'Hello', 0.0, 1.0)",
            (session_id, speaker_id),
        )
        await db.commit()

    resp = await client.get(f"/api/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    segment = data[0]
    assert segment["text"] == "Hello"
    assert segment["start_time"] == 0.0
    assert segment["end_time"] == 1.0
    assert segment["player_name"] == "Alice"
    assert segment["diarization_label"] == "SPEAKER_00"
    assert segment["session_id"] == session_id
    assert segment["speaker_id"] == speaker_id


@pytest.mark.asyncio
async def test_get_transcript_empty_session(client: AsyncClient) -> None:
    # Create campaign and session with no segments
    campaign_resp = await client.post(
        "/api/campaigns", json={"name": "Empty Campaign"}
    )
    campaign_id = campaign_resp.json()["id"]

    session_resp = await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "Empty Session", "date": "2025-06-01"},
    )
    session_id = session_resp.json()["id"]

    resp = await client.get(f"/api/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0
