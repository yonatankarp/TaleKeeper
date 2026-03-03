"""Tests for the speaker diarization service (pyannote.audio)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import numpy as np

from talekeeper.services.diarization import (
    _merge_segments,
    align_speakers_with_transcript,
    diarize,
    diarize_with_signatures,
    _resolve_hf_token,
    unload_models,
    SpeakerSegment,
)


# ---- Engine-agnostic tests (5.8) ----


def test_merge_segments():
    """_merge_segments merges adjacent segments with the same speaker label."""
    segs = [
        SpeakerSegment("A", 0.0, 1.0),
        SpeakerSegment("A", 1.0, 2.0),
        SpeakerSegment("B", 2.0, 3.0),
    ]
    merged = _merge_segments(segs)

    assert len(merged) == 2
    assert merged[0].speaker_label == "A"
    assert merged[0].start_time == 0.0
    assert merged[0].end_time == 2.0
    assert merged[1].speaker_label == "B"
    assert merged[1].start_time == 2.0
    assert merged[1].end_time == 3.0


def test_merge_segments_empty():
    """_merge_segments returns empty list for empty input."""
    assert _merge_segments([]) == []


def test_align_speakers_with_transcript():
    """align_speakers_with_transcript assigns correct speaker labels by overlap."""
    speaker_segs = [
        SpeakerSegment("A", 0.0, 5.0),
        SpeakerSegment("B", 5.0, 10.0),
    ]
    transcript_segs = [
        {"start_time": 0.5, "end_time": 2.0, "text": "hello"},
        {"start_time": 6.0, "end_time": 8.0, "text": "world"},
    ]

    aligned = align_speakers_with_transcript(speaker_segs, transcript_segs)

    assert len(aligned) == 2
    assert aligned[0]["speaker_label"] == "A"
    assert aligned[1]["speaker_label"] == "B"


# ---- Pyannote diarization tests (5.10) ----


class FakeSegment:
    """Mock pyannote Segment."""
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.duration = end - start


class FakeAnnotation:
    """Mock pyannote Annotation."""
    def __init__(self, tracks):
        self._tracks = tracks  # list of (segment, track_name, speaker_label)

    def itertracks(self, yield_label=False):
        for seg, track, label in self._tracks:
            if yield_label:
                yield seg, track, label
            else:
                yield seg, track

    def labels(self):
        return list(set(label for _, _, label in self._tracks))

    def label_timeline(self, label):
        return [seg for seg, _, lbl in self._tracks if lbl == label]


@patch("talekeeper.services.diarization._get_pipeline")
def test_diarize_with_pyannote(mock_get_pipeline):
    """diarize runs pyannote pipeline and returns merged speaker segments."""
    fake_tracks = [
        (FakeSegment(0.0, 3.0), "A", "SPEAKER_00"),
        (FakeSegment(3.0, 5.0), "B", "SPEAKER_01"),
        (FakeSegment(5.0, 7.0), "C", "SPEAKER_00"),
    ]
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = FakeAnnotation(fake_tracks)
    mock_get_pipeline.return_value = mock_pipeline

    segments = diarize(Path("test.wav"), hf_token="fake-token")

    assert len(segments) == 3
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 3.0
    assert segments[1].speaker_label == "SPEAKER_01"
    assert segments[2].speaker_label == "SPEAKER_00"


@patch("talekeeper.services.diarization._get_pipeline")
def test_diarize_passes_num_speakers(mock_get_pipeline):
    """diarize passes num_speakers to pyannote pipeline."""
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = FakeAnnotation([])
    mock_get_pipeline.return_value = mock_pipeline

    diarize(Path("test.wav"), num_speakers=3, hf_token="fake-token")

    mock_pipeline.assert_called_once_with(str(Path("test.wav")), num_speakers=3)


# ---- Signature matching tests (5.11) ----


@patch("talekeeper.services.diarization._get_embedding_model")
@patch("talekeeper.services.diarization._get_pipeline")
def test_diarize_with_signatures_matches_above_threshold(mock_get_pipeline, mock_get_emb):
    """diarize_with_signatures matches speakers above similarity threshold."""
    # Two pyannote speakers
    fake_tracks = [
        (FakeSegment(0.0, 5.0), "A", "SPEAKER_00"),
        (FakeSegment(5.0, 10.0), "B", "SPEAKER_01"),
    ]
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = FakeAnnotation(fake_tracks)
    mock_get_pipeline.return_value = mock_pipeline

    # Mock embedding model: returns embeddings that match signatures
    emb_speaker_00 = np.array([1.0, 0.0, 0.0])  # matches signature 1
    emb_speaker_01 = np.array([0.0, 1.0, 0.0])  # matches signature 2

    mock_emb_model = MagicMock()
    call_count = [0]
    def mock_crop(wav, seg):
        nonlocal call_count
        # First calls are for SPEAKER_00, later for SPEAKER_01
        if any(seg.start == t.start for t in fake_tracks[0][0:1]):
            return emb_speaker_00
        return emb_speaker_01
    # Use side_effect to return different embeddings based on segment
    mock_emb_model.crop = MagicMock(side_effect=[emb_speaker_00, emb_speaker_01])
    mock_get_emb.return_value = mock_emb_model

    # Signatures: two roster entries with orthogonal embeddings
    sig1 = np.array([1.0, 0.0, 0.0])  # roster 101
    sig2 = np.array([0.0, 1.0, 0.0])  # roster 102

    segments = diarize_with_signatures(
        Path("test.wav"),
        signatures=[(101, sig1), (102, sig2)],
        similarity_threshold=0.5,
        hf_token="fake-token",
    )

    # Should match both speakers to roster entries
    labels = [s.speaker_label for s in segments]
    assert "roster_101" in labels
    assert "roster_102" in labels


@patch("talekeeper.services.diarization._get_embedding_model")
@patch("talekeeper.services.diarization._get_pipeline")
def test_diarize_with_signatures_unknown_below_threshold(mock_get_pipeline, mock_get_emb):
    """diarize_with_signatures labels speakers below threshold as Unknown."""
    fake_tracks = [
        (FakeSegment(0.0, 5.0), "A", "SPEAKER_00"),
    ]
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = FakeAnnotation(fake_tracks)
    mock_get_pipeline.return_value = mock_pipeline

    # Speaker embedding is orthogonal to all signatures
    emb = np.array([0.0, 0.0, 1.0])
    mock_emb_model = MagicMock()
    mock_emb_model.crop = MagicMock(return_value=emb)
    mock_get_emb.return_value = mock_emb_model

    sig1 = np.array([1.0, 0.0, 0.0])

    segments = diarize_with_signatures(
        Path("test.wav"),
        signatures=[(101, sig1)],
        similarity_threshold=0.5,
        hf_token="fake-token",
    )

    assert all(s.speaker_label == "Unknown Speaker" for s in segments)


# ---- HF token resolution tests (5.12) ----


async def test_resolve_hf_token_from_settings(db):
    """_resolve_hf_token reads token from settings table."""
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('hf_token', 'hf_test_token_123')"
    )
    await db.commit()

    token = await _resolve_hf_token()
    assert token == "hf_test_token_123"


async def test_resolve_hf_token_from_env(db):
    """_resolve_hf_token falls back to HF_TOKEN env var."""
    # Clear settings
    await db.execute("DELETE FROM settings WHERE key = 'hf_token'")
    await db.commit()

    with patch.dict("os.environ", {"HF_TOKEN": "hf_env_token_456"}):
        token = await _resolve_hf_token()
        assert token == "hf_env_token_456"


async def test_resolve_hf_token_missing_raises(db):
    """_resolve_hf_token raises ValueError when no token configured."""
    await db.execute("DELETE FROM settings WHERE key = 'hf_token'")
    await db.commit()

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="HuggingFace token required"):
            await _resolve_hf_token()
