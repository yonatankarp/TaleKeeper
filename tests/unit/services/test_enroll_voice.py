"""Unit tests for enroll_speaker_voice in the diarization service."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from talekeeper.services.diarization import enroll_speaker_voice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(**kwargs):
    """Return a dict-like object that supports dict() conversion."""
    return kwargs


def _make_db_context(fetchall_side_effects: list):
    """Return an async context manager yielding a mock DB with configured fetchall results."""
    mock_db = MagicMock()
    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effects)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield mock_db

    return _ctx, mock_db


def _speaker_row(speaker_id=1, session_id=10, player_name="Alice", character_name="Gandalf"):
    return [_make_row(id=speaker_id, session_id=session_id, player_name=player_name, character_name=character_name)]


def _session_row(session_id=10, campaign_id=5, audio_path="/fake/audio.webm"):
    return [_make_row(id=session_id, campaign_id=campaign_id, audio_path=audio_path)]


def _roster_row(roster_entry_id=20):
    return [_make_row(id=roster_entry_id)]


def _segment_rows(*ranges):
    """Build segment rows from (start, end) tuples."""
    return [_make_row(start_time=s, end_time=e) for s, e in ranges]


def _fake_embedding(dim=256):
    emb = np.random.default_rng(42).random(dim).astype(np.float64)
    emb /= np.linalg.norm(emb)
    return emb


# ---------------------------------------------------------------------------
# Task 1.2 — New signature creation path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enroll_creates_new_signature(tmp_path):
    """New signature row is created with correct embedding and num_samples."""
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake")
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")

    embedding = _fake_embedding()

    # DB query responses: speaker, session, roster, segments, no existing signature
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=str(audio_file)),
        _roster_row(roster_entry_id=20),
        _segment_rows((0.0, 5.0), (5.0, 10.0)),
        [],  # no existing signature
    ]
    # Reuse same mock db for both context manager calls
    mock_db = MagicMock()
    call_count = [0]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", return_value=embedding),
        patch("talekeeper.services.audio.audio_to_wav", return_value=wav_file),
        patch("talekeeper.services.diarization.Path.exists", return_value=True),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    # Verify INSERT was called with correct num_samples (2 segments)
    insert_calls = [
        c for c in mock_db.execute.call_args_list
        if "INSERT INTO voice_signatures" in str(c)
    ]
    assert len(insert_calls) == 1
    args = insert_calls[0][0][1]  # positional tuple
    stored_embedding = np.array(json.loads(args[2]))
    assert np.allclose(stored_embedding, embedding, atol=1e-6)
    num_samples = args[4]
    assert num_samples == 2


# ---------------------------------------------------------------------------
# Task 1.3 — Weighted merge with existing signature
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enroll_merges_with_existing_signature(tmp_path):
    """Weighted merge accumulates num_samples and moves embedding toward new data."""
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake")
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")

    rng = np.random.default_rng(0)
    old_embedding = rng.random(256).astype(np.float64)
    old_embedding /= np.linalg.norm(old_embedding)
    new_embedding = rng.random(256).astype(np.float64)
    new_embedding /= np.linalg.norm(new_embedding)

    old_count = 10
    new_count = 3  # 3 segments

    existing_sig = [_make_row(embedding=json.dumps(old_embedding.tolist()), num_samples=old_count)]

    mock_db = MagicMock()
    call_count = [0]
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=str(audio_file)),
        _roster_row(),
        _segment_rows((0.0, 5.0), (5.0, 10.0), (10.0, 15.0)),
        existing_sig,
    ]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", return_value=new_embedding),
        patch("talekeeper.services.audio.audio_to_wav", return_value=wav_file),
        patch("talekeeper.services.diarization.Path.exists", return_value=True),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    insert_calls = [
        c for c in mock_db.execute.call_args_list
        if "INSERT INTO voice_signatures" in str(c)
    ]
    assert len(insert_calls) == 1
    args = insert_calls[0][0][1]

    # num_samples should accumulate
    stored_num_samples = args[4]
    assert stored_num_samples == old_count + new_count

    # Direction of merged embedding should be between old and new (weighted toward old)
    stored_embedding = np.array(json.loads(args[2]))
    assert stored_embedding.shape == old_embedding.shape

    # Similarity to old embedding should be higher than similarity to new (old_count > new_count)
    sim_to_old = float(stored_embedding @ old_embedding)
    sim_to_new = float(stored_embedding @ new_embedding)
    assert sim_to_old > sim_to_new, (
        f"Expected merged embedding closer to old (sim_old={sim_to_old:.3f}, sim_new={sim_to_new:.3f})"
    )

    # Stored embedding should be L2-normalized
    assert abs(np.linalg.norm(stored_embedding) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# Task 1.4 — 120s audio sampling cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enroll_caps_audio_at_120s(tmp_path):
    """Segments totalling 300s are capped to ~120s; extract_speaker_embedding receives ≤120s."""
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake")
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")

    # 10 segments of 30s each = 300s total
    segs = [(i * 30.0, i * 30.0 + 30.0) for i in range(10)]

    embedding = _fake_embedding()
    captured_ranges = []

    def fake_extract(wav_path, time_ranges):
        captured_ranges.extend(time_ranges)
        return embedding

    mock_db = MagicMock()
    call_count = [0]
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=str(audio_file)),
        _roster_row(),
        _segment_rows(*segs),
        [],  # no existing sig
    ]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", side_effect=fake_extract),
        patch("talekeeper.services.audio.audio_to_wav", return_value=wav_file),
        patch("talekeeper.services.diarization.Path.exists", return_value=True),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    # Total duration of passed time_ranges must not exceed 120s
    total_duration = sum(end - start for start, end in captured_ranges)
    assert total_duration <= 120.0 + 0.5, f"Expected ≤120s but got {total_duration:.1f}s"
    assert total_duration > 0, "Should have passed some ranges"


# ---------------------------------------------------------------------------
# Task 1.5 — No-op edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enroll_noop_no_roster_match(tmp_path):
    """No signature created when speaker names don't match any active roster entry."""
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake")

    mock_db = MagicMock()
    call_count = [0]
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=str(audio_file)),
        [],  # no roster match
    ]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    mock_extract = MagicMock()
    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", mock_extract),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    mock_extract.assert_not_called()
    insert_calls = [c for c in mock_db.execute.call_args_list if "INSERT" in str(c)]
    assert len(insert_calls) == 0


@pytest.mark.asyncio
async def test_enroll_noop_no_audio_path(tmp_path):
    """No signature created when session has no audio_path."""
    mock_db = MagicMock()
    call_count = [0]
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=None),
    ]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    mock_extract = MagicMock()
    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", mock_extract),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    mock_extract.assert_not_called()
    insert_calls = [c for c in mock_db.execute.call_args_list if "INSERT" in str(c)]
    assert len(insert_calls) == 0


@pytest.mark.asyncio
async def test_enroll_noop_no_segments(tmp_path):
    """No signature created when speaker has no transcript segments."""
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake")

    mock_db = MagicMock()
    call_count = [0]
    fetchall_responses = [
        _speaker_row(),
        _session_row(audio_path=str(audio_file)),
        _roster_row(),
        [],  # no segments
    ]

    async def fetchall_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return fetchall_responses[idx]

    mock_db.execute_fetchall = AsyncMock(side_effect=fetchall_side_effect)
    mock_db.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_db():
        yield mock_db

    mock_extract = MagicMock()
    with (
        patch("talekeeper.services.diarization.get_db", mock_get_db),
        patch("talekeeper.services.diarization.extract_speaker_embedding", mock_extract),
    ):
        await enroll_speaker_voice(speaker_id=1, session_id=10)

    mock_extract.assert_not_called()
    insert_calls = [c for c in mock_db.execute.call_args_list if "INSERT" in str(c)]
    assert len(insert_calls) == 0
