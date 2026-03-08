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
        json={"language": "en"},
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
        json={"language": "en"},
    )
    assert resp.status_code == 400
    assert "No audio" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_transcript_endpoint_returns_is_overlap(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/transcript returns is_overlap field on each segment."""
    async with get_db() as db:
        cursor = await db.execute("INSERT INTO campaigns (name) VALUES ('C')")
        campaign_id = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'S', '2025-01-01')",
            (campaign_id,),
        )
        session_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO transcript_segments (session_id, text, start_time, end_time, is_overlap) "
            "VALUES (?, 'Normal speech', 0.0, 1.0, 0)",
            (session_id,),
        )
        await db.execute(
            "INSERT INTO transcript_segments (session_id, text, start_time, end_time, is_overlap) "
            "VALUES (?, 'Crosstalk here', 1.0, 2.0, 1)",
            (session_id,),
        )
        await db.commit()

    resp = await client.get(f"/api/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Both segments must have the is_overlap field
    assert "is_overlap" in data[0]
    assert "is_overlap" in data[1]
    # Values match what was inserted
    assert data[0]["is_overlap"] == 0
    assert data[1]["is_overlap"] == 1


@pytest.mark.asyncio
async def test_db_migration_is_overlap_defaults_zero(client: AsyncClient) -> None:
    """Existing transcript_segments rows get is_overlap = 0 via migration default."""
    async with get_db() as db:
        cursor = await db.execute("INSERT INTO campaigns (name) VALUES ('MigC')")
        campaign_id = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'MigS', '2025-01-01')",
            (campaign_id,),
        )
        session_id = cursor.lastrowid
        # Insert without specifying is_overlap — should default to 0
        await db.execute(
            "INSERT INTO transcript_segments (session_id, text, start_time, end_time) "
            "VALUES (?, 'Legacy segment', 0.0, 2.0)",
            (session_id,),
        )
        await db.commit()

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT is_overlap FROM transcript_segments WHERE session_id = ?", (session_id,)
        )
    assert len(rows) == 1
    assert rows[0]["is_overlap"] == 0


@pytest.mark.asyncio
async def test_retranscribe_session_not_found(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/retranscribe returns 404 for non-existent session."""
    resp = await client.post(
        "/api/sessions/99999/retranscribe",
        json={"language": "en"},
    )
    assert resp.status_code == 404
    assert "Session not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_split_transcript_segments_db_insert(db) -> None:
    """_split_transcript_segments: split segments are correctly inserted into the DB.

    Simulates what run_final_diarization does when a transcript segment is split
    at a speaker boundary: the original row is updated (first sub-segment) and
    a new row is inserted (second sub-segment).
    """
    from talekeeper.services.diarization import _split_transcript_segments, SpeakerSegment

    cursor = await db.execute("INSERT INTO campaigns (name) VALUES ('C')")
    campaign_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'S', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
        (session_id, "a b c d e f g h i j k l", 0.0, 12.0),
    )
    original_id = cursor.lastrowid
    await db.commit()

    # Fetch as run_final_diarization would
    rows = await db.execute_fetchall(
        "SELECT id, session_id, text, start_time, end_time FROM transcript_segments WHERE session_id = ?",
        (session_id,),
    )
    transcript_segs = [dict(r) for r in rows]

    # Split at 6s: each child is exactly MIN_SPLIT_CHILD_DURATION (5s minimum satisfied)
    speaker_segs = [
        SpeakerSegment("SPEAKER_00", 0.0, 6.0),
        SpeakerSegment("SPEAKER_01", 6.0, 12.0),
    ]
    split_segs = _split_transcript_segments(transcript_segs, speaker_segs)
    assert len(split_segs) == 2

    # Simulate DB writes: INSERT both children (original row is left intact)
    for child in split_segs:
        assert child["id"] is None
        assert child["parent_segment_id"] == original_id
        await db.execute(
            "INSERT INTO transcript_segments (session_id, parent_segment_id, text, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
            (child["session_id"], child["parent_segment_id"], child["text"], child["start_time"], child["end_time"]),
        )
    await db.commit()

    # Original row still intact
    orig_row = await db.execute_fetchall(
        "SELECT id, start_time, end_time, text FROM transcript_segments WHERE id = ?",
        (original_id,),
    )
    assert orig_row[0]["start_time"] == 0.0
    assert orig_row[0]["end_time"] == 12.0

    # Children exist with correct boundaries
    child_rows = await db.execute_fetchall(
        "SELECT start_time, end_time, text FROM transcript_segments WHERE parent_segment_id = ? ORDER BY start_time",
        (original_id,),
    )
    assert len(child_rows) == 2
    assert child_rows[0]["start_time"] == 0.0
    assert child_rows[0]["end_time"] == 6.0
    assert child_rows[1]["start_time"] == 6.0
    assert child_rows[1]["end_time"] == 12.0
    # All original words preserved across children
    all_words = child_rows[0]["text"].split() + child_rows[1]["text"].split()
    assert all_words == "a b c d e f g h i j k l".split()

    # Verify re-diarize cleanup: delete children restores original-only state
    await db.execute(
        "DELETE FROM transcript_segments WHERE parent_segment_id IS NOT NULL AND session_id = ?",
        (session_id,),
    )
    await db.commit()
    remaining = await db.execute_fetchall(
        "SELECT id FROM transcript_segments WHERE session_id = ?", (session_id,)
    )
    assert len(remaining) == 1
    assert remaining[0]["id"] == original_id
