"""Tests for speaker management API endpoints."""

from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from conftest import parse_sse_events
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


# ---------------------------------------------------------------------------
# Re-diarize SSE helpers
# ---------------------------------------------------------------------------

async def _seed_completed_session_with_audio(db, tmp_path: Path) -> dict:
    """Create campaign -> session (completed, with audio) -> speaker -> segment."""
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

    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name) "
        "VALUES (?, 'SPEAKER_00', 'Alice')",
        (session_id,),
    )
    speaker_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'Hello world', 0.0, 1.0)",
        (session_id, speaker_id),
    )
    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'Roll for initiative', 1.0, 2.0)",
        (session_id, speaker_id),
    )

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "audio_file": audio_file,
        "speaker_id": speaker_id,
    }


# ---------------------------------------------------------------------------
# Re-diarize SSE tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch(
    "talekeeper.services.diarization.run_final_diarization",
    new_callable=AsyncMock,
)
@patch("talekeeper.services.audio.audio_to_wav")
async def test_re_diarize_happy_path(
    mock_audio_to_wav: MagicMock,
    mock_diarize: AsyncMock,
    client: AsyncClient,
    tmp_path: Path,
) -> None:
    """POST /api/sessions/{id}/re-diarize streams phase and done events."""
    async with get_db() as db:
        ids = await _seed_completed_session_with_audio(db, tmp_path)

    session_id = ids["session_id"]

    # Set up mocks
    wav_file = tmp_path / "session.wav"
    wav_file.write_bytes(b"fake-wav")
    mock_audio_to_wav.return_value = wav_file

    resp = await client.post(
        f"/api/sessions/{session_id}/re-diarize",
        json={"num_speakers": 3},
    )
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)

    # Expect: phase, done
    event_types = [e["event"] for e in events]
    assert "phase" in event_types
    assert "done" in event_types

    phase_events = [e for e in events if e["event"] == "phase"]
    assert phase_events[0]["data"]["phase"] == "diarization"

    done_events = [e for e in events if e["event"] == "done"]
    assert "segments_count" in done_events[0]["data"]

    # Verify mocks were called
    mock_audio_to_wav.assert_called_once()
    mock_diarize.assert_called_once()
    # Verify num_speakers_override was passed
    call_kwargs = mock_diarize.call_args
    assert call_kwargs[1]["num_speakers_override"] == 3

    # Verify session status is back to 'completed'
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM sessions WHERE id = ?", (session_id,)
        )
        assert rows[0]["status"] == "completed"

    # Verify old speakers were cleaned up (run_final_diarization is mocked so no new ones created)
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE session_id = ?", (session_id,)
        )
        assert len(rows) == 0


@pytest.mark.asyncio
async def test_re_diarize_session_not_completed(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/re-diarize returns 409 when session status is draft."""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES ('C')"
        )
        campaign_id = cursor.lastrowid

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, audio_path, status) "
            "VALUES (?, 'S', '2025-01-01', '/tmp/fake.webm', 'draft')",
            (campaign_id,),
        )
        session_id = cursor.lastrowid
        await db.commit()

    resp = await client.post(
        f"/api/sessions/{session_id}/re-diarize",
        json={"num_speakers": 3},
    )
    assert resp.status_code == 409
    assert "currently being processed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_re_diarize_no_audio(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/re-diarize returns 400 when no audio recorded."""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES ('C')"
        )
        campaign_id = cursor.lastrowid

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, status) "
            "VALUES (?, 'S', '2025-01-01', 'completed')",
            (campaign_id,),
        )
        session_id = cursor.lastrowid
        await db.commit()

    resp = await client.post(
        f"/api/sessions/{session_id}/re-diarize",
        json={"num_speakers": 3},
    )
    assert resp.status_code == 400
    assert "No audio" in resp.json()["detail"]
