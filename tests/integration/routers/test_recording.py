"""Tests for recording and audio upload API endpoints."""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from talekeeper.db import get_db
from talekeeper.services.transcription import TranscriptSegment, ChunkProgress
from conftest import parse_sse_events


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


async def _seed_with_audio(db, tmp_path: Path) -> dict:
    """Create campaign -> session with a fake audio file on disk. Return IDs + audio_path."""
    ids = await _seed(db)
    session_id = ids["session_id"]

    audio_file = tmp_path / "fake_audio.webm"
    audio_file.write_bytes(b"fake-audio-bytes")

    await db.execute(
        "UPDATE sessions SET audio_path = ? WHERE id = ?",
        (str(audio_file), session_id),
    )
    await db.commit()

    ids["audio_path"] = str(audio_file)
    return ids


# ---------------------------------------------------------------------------
# Task 3: process-audio SSE happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("talekeeper.services.audio.audio_to_wav")
@patch("talekeeper.services.diarization.run_final_diarization", new_callable=AsyncMock)
@patch("talekeeper.services.transcription.transcribe_chunked")
async def test_process_audio_sse_happy_path(
    mock_transcribe: MagicMock,
    mock_diarize: AsyncMock,
    mock_audio_to_wav: MagicMock,
    client: AsyncClient,
    tmp_path: Path,
) -> None:
    """POST /api/sessions/{id}/process-audio streams SSE with progress, segments, phase, done."""
    # 1. Seed campaign + session with audio file
    async with get_db() as db:
        ids = await _seed_with_audio(db, tmp_path)

    session_id = ids["session_id"]

    # 2. Configure mocks
    # transcribe_chunked is a generator yielding ChunkProgress and TranscriptSegment
    def fake_transcribe_chunked(audio_path, model_size="medium", language="en"):
        yield ChunkProgress(chunk=1, total_chunks=2)
        yield TranscriptSegment(text="The dragon attacked.", start_time=0.0, end_time=3.0)
        yield ChunkProgress(chunk=2, total_chunks=2)
        yield TranscriptSegment(text="We fought bravely.", start_time=3.0, end_time=6.0)

    mock_transcribe.side_effect = fake_transcribe_chunked

    # audio_to_wav returns a fake wav path
    fake_wav = tmp_path / "fake.wav"
    fake_wav.write_bytes(b"fake-wav")
    mock_audio_to_wav.return_value = fake_wav

    # run_final_diarization is async, returns None
    mock_diarize.return_value = None

    # 3. Call the endpoint
    resp = await client.post(f"/api/sessions/{session_id}/process-audio")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    # 4. Parse SSE events
    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    # Verify we got the expected event sequence
    assert "progress" in event_types
    assert "segment" in event_types
    assert "phase" in event_types
    assert "done" in event_types

    # Check progress events
    progress_events = [e for e in events if e["event"] == "progress"]
    assert len(progress_events) == 2
    assert progress_events[0]["data"]["chunk"] == 1
    assert progress_events[0]["data"]["total_chunks"] == 2
    assert progress_events[1]["data"]["chunk"] == 2

    # Check segment events
    segment_events = [e for e in events if e["event"] == "segment"]
    assert len(segment_events) == 2
    assert segment_events[0]["data"]["text"] == "The dragon attacked."
    assert segment_events[0]["data"]["start_time"] == 0.0
    assert segment_events[0]["data"]["end_time"] == 3.0
    assert segment_events[1]["data"]["text"] == "We fought bravely."

    # Check phase event
    phase_events = [e for e in events if e["event"] == "phase"]
    assert len(phase_events) == 1
    assert phase_events[0]["data"]["phase"] == "diarization"

    # Check done event
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["data"]["segments_count"] == 2

    # Verify segments were persisted to DB
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT text, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
            (session_id,),
        )
        assert len(rows) == 2
        assert rows[0]["text"] == "The dragon attacked."
        assert rows[1]["text"] == "We fought bravely."

    # Verify session status was set to completed
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM sessions WHERE id = ?", (session_id,),
        )
        assert rows[0]["status"] == "completed"

    # Verify mocks were called
    mock_transcribe.assert_called_once()
    mock_audio_to_wav.assert_called_once()
    mock_diarize.assert_called_once()


# ---------------------------------------------------------------------------
# Task 4: process-audio error cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_audio_session_not_found(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/process-audio returns 404 for nonexistent session."""
    resp = await client.post("/api/sessions/99999/process-audio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_process_audio_no_audio(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/process-audio returns 400 when session has no audio_path."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.post(f"/api/sessions/{ids['session_id']}/process-audio")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Task 5: download audio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_audio(client: AsyncClient, tmp_path: Path) -> None:
    """GET /api/sessions/{id}/audio returns the audio file when it exists."""
    async with get_db() as db:
        ids = await _seed_with_audio(db, tmp_path)

    session_id = ids["session_id"]
    resp = await client.get(f"/api/sessions/{session_id}/audio")
    assert resp.status_code == 200
    assert resp.content == b"fake-audio-bytes"


@pytest.mark.asyncio
async def test_download_audio_no_audio(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/audio returns 404 when no audio_path is set."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/audio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_audio_file_missing(client: AsyncClient, tmp_path: Path) -> None:
    """GET /api/sessions/{id}/audio returns 404 when audio_path is set but file does not exist."""
    async with get_db() as db:
        ids = await _seed(db)
        # Set audio_path to a nonexistent file
        await db.execute(
            "UPDATE sessions SET audio_path = ? WHERE id = ?",
            (str(tmp_path / "nonexistent.webm"), ids["session_id"]),
        )
        await db.commit()

    resp = await client.get(f"/api/sessions/{ids['session_id']}/audio")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 6: upload-audio MIME + replacement
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


@pytest.mark.asyncio
async def test_upload_audio_invalid_mime(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/upload-audio returns 400 for non-audio MIME type."""
    async with get_db() as db:
        ids = await _seed(db)

    session_id = ids["session_id"]
    resp = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("document.pdf", io.BytesIO(b"not-audio"), "application/pdf")},
    )
    assert resp.status_code == 400
    assert "audio" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_audio_replaces_existing(client: AsyncClient) -> None:
    """Uploading audio twice clears old segments and speakers."""
    async with get_db() as db:
        ids = await _seed(db)

    session_id = ids["session_id"]

    # First upload
    resp1 = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("first.mp3", io.BytesIO(b"audio-data-1"), "audio/mpeg")},
    )
    assert resp1.status_code == 200
    first_path = resp1.json()["audio_path"]

    # Seed transcript segments and speakers for this session (simulating post-processing)
    async with get_db() as db:
        await db.execute(
            "INSERT INTO speakers (session_id, diarization_label) VALUES (?, 'SPEAKER_00')",
            (session_id,),
        )
        cursor = await db.execute(
            "SELECT id FROM speakers WHERE session_id = ?", (session_id,),
        )
        speaker_row = await cursor.fetchone()
        speaker_id = speaker_row[0]

        await db.execute(
            "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
            "VALUES (?, ?, 'Old transcript text', 0.0, 5.0)",
            (session_id, speaker_id),
        )
        await db.commit()

    # Verify segments and speakers exist before second upload
    async with get_db() as db:
        seg_rows = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE session_id = ?", (session_id,),
        )
        spk_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE session_id = ?", (session_id,),
        )
        assert len(seg_rows) == 1
        assert len(spk_rows) == 1

    # Second upload — should clear old segments and speakers
    resp2 = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("second.wav", io.BytesIO(b"audio-data-2"), "audio/wav")},
    )
    assert resp2.status_code == 200
    second_path = resp2.json()["audio_path"]
    assert second_path != first_path  # Different extension

    # Verify old segments and speakers were cleared
    async with get_db() as db:
        seg_rows = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE session_id = ?", (session_id,),
        )
        spk_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE session_id = ?", (session_id,),
        )
        assert len(seg_rows) == 0, "Old transcript segments should be cleared on re-upload"
        assert len(spk_rows) == 0, "Old speakers should be cleared on re-upload"
