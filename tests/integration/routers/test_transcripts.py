"""Integration tests for transcript API endpoints."""

from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from conftest import parse_sse_events
from talekeeper.db import get_db
from talekeeper.services.transcription import TranscriptSegment, ChunkProgress


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_session_with_audio(db, tmp_path: Path) -> dict:
    """Create campaign -> session with a fake audio_path on disk. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    audio_file = tmp_path / "session.webm"
    audio_file.write_bytes(b"fake-audio")

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date, audio_path, status) "
        "VALUES (?, 'Session 1', '2025-01-01', ?, 'completed')",
        (campaign_id, str(audio_file)),
    )
    session_id = cursor.lastrowid
    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "audio_file": audio_file,
    }


# ---------------------------------------------------------------------------
# Retranscribe SSE tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch(
    "talekeeper.services.diarization.run_final_diarization",
    new_callable=AsyncMock,
)
@patch("talekeeper.services.audio.webm_to_wav")
@patch("talekeeper.services.transcription.transcribe_chunked")
async def test_retranscribe_happy_path(
    mock_transcribe: MagicMock,
    mock_webm_to_wav: MagicMock,
    mock_diarize: AsyncMock,
    client: AsyncClient,
    tmp_path: Path,
) -> None:
    """POST /api/sessions/{id}/retranscribe streams progress, segment, done events."""
    async with get_db() as db:
        ids = await _seed_session_with_audio(db, tmp_path)

    session_id = ids["session_id"]

    # Set up mocks
    wav_file = tmp_path / "session.wav"
    wav_file.write_bytes(b"fake-wav")
    mock_webm_to_wav.return_value = wav_file

    mock_transcribe.return_value = iter([
        ChunkProgress(chunk=1, total_chunks=1),
        TranscriptSegment(text="Hello world", start_time=0.0, end_time=1.5),
        TranscriptSegment(text="Roll for initiative", start_time=1.5, end_time=3.0),
    ])

    resp = await client.post(
        f"/api/sessions/{session_id}/retranscribe",
        json={"model_size": "medium"},
    )
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)

    # Expect: progress, segment, segment, done
    event_types = [e["event"] for e in events]
    assert "progress" in event_types
    assert "segment" in event_types
    assert "done" in event_types

    progress_events = [e for e in events if e["event"] == "progress"]
    assert progress_events[0]["data"]["chunk"] == 1
    assert progress_events[0]["data"]["total_chunks"] == 1

    segment_events = [e for e in events if e["event"] == "segment"]
    assert len(segment_events) == 2
    assert segment_events[0]["data"]["text"] == "Hello world"
    assert segment_events[1]["data"]["text"] == "Roll for initiative"

    done_events = [e for e in events if e["event"] == "done"]
    assert done_events[0]["data"]["segments_count"] == 2

    # Verify mocks were called
    mock_transcribe.assert_called_once()
    mock_webm_to_wav.assert_called_once()
    mock_diarize.assert_called_once()

    # Verify session status is back to 'completed'
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM sessions WHERE id = ?", (session_id,)
        )
        assert rows[0]["status"] == "completed"

    # Verify segments were persisted
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
            (session_id,),
        )
        assert len(rows) == 2
        assert rows[0]["text"] == "Hello world"
        assert rows[1]["text"] == "Roll for initiative"


@pytest.mark.asyncio
async def test_retranscribe_no_audio(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/retranscribe returns 400 when no audio recorded."""
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
        await db.commit()

    resp = await client.post(
        f"/api/sessions/{session_id}/retranscribe",
        json={"model_size": "medium"},
    )
    assert resp.status_code == 400
    assert "No audio" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_retranscribe_session_not_found(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/retranscribe returns 404 for non-existent session."""
    resp = await client.post(
        "/api/sessions/99999/retranscribe",
        json={"model_size": "medium"},
    )
    assert resp.status_code == 404
    assert "Session not found" in resp.json()["detail"]
