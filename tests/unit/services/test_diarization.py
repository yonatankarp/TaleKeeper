"""Tests for the speaker diarization service (diarize library)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import numpy as np

from talekeeper.services.diarization import (
    _merge_segments,
    _build_segments_from_labels,
    _extract_embeddings_with_progress,
    align_speakers_with_transcript,
    diarize,
    diarize_with_signatures,
    _resolve_hf_token,
    unload_models,
    SpeakerSegment,
)


# ---- Engine-agnostic tests ----


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


# ---- _build_segments_from_labels tests ----


def test_build_segments_from_labels():
    """_build_segments_from_labels converts clustering output to SpeakerSegments."""
    # Mock speech segments (not directly used by the function, but part of the API)
    speech_segments = [MagicMock(start=0.0, end=3.0), MagicMock(start=5.0, end=8.0)]

    subsegments = [
        (0.0, 1.2, 0),
        (0.6, 1.8, 0),
        (5.0, 6.2, 1),
        (5.6, 6.8, 1),
    ]
    labels = np.array([0, 0, 1, 1])

    segments = _build_segments_from_labels(speech_segments, subsegments, labels)

    # Should merge adjacent same-speaker segments
    assert len(segments) == 2
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 1.8
    assert segments[1].speaker_label == "SPEAKER_01"
    assert segments[1].start_time == 5.0
    assert segments[1].end_time == 6.8


def test_build_segments_from_labels_empty():
    """_build_segments_from_labels returns empty list for no subsegments."""
    segments = _build_segments_from_labels([], [], np.array([]))
    assert segments == []


# ---- _extract_embeddings_with_progress tests ----


@patch("talekeeper.services.diarization.sf")
@patch("talekeeper.services.diarization.wespeakerruntime", create=True)
def test_extract_embeddings_with_progress_callback(mock_wespeaker_module, mock_sf):
    """_extract_embeddings_with_progress invokes callback with (current, total)."""
    # We need to patch the import inside the function
    # Mock audio read
    mock_sf.read.return_value = (np.zeros(48000), 16000)  # 3s of silence
    mock_sf.write = MagicMock()

    # Create fake speech segments with .start and .end
    class FakeSpeechSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    speech_segments = [FakeSpeechSeg(0.0, 1.0), FakeSpeechSeg(1.5, 2.5)]

    # Mock wespeakerruntime.Speaker
    mock_speaker_instance = MagicMock()
    mock_speaker_instance.extract_embedding.return_value = np.random.randn(1, 256).astype(np.float32)

    progress_calls = []

    def progress_cb(stage, detail):
        if stage == "embeddings":
            progress_calls.append((detail["current"], detail["total"]))

    with patch("wespeakerruntime.Speaker", return_value=mock_speaker_instance):
        embeddings, subsegments = _extract_embeddings_with_progress(
            Path("test.wav"), speech_segments, progress_callback=progress_cb
        )

    # Should have called progress for each segment
    assert len(progress_calls) == 2
    assert progress_calls[0] == (1, 2)
    assert progress_calls[1] == (2, 2)
    assert embeddings.shape[1] == 256


# ---- Diarization tests ----


@patch("talekeeper.services.diarization.cluster_speakers", create=True)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
@patch("talekeeper.services.diarization.run_vad", create=True)
def test_diarize(mock_run_vad, mock_extract, mock_cluster):
    """diarize runs the pipeline and returns merged speaker segments."""

    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    mock_run_vad.return_value = [FakeSeg(0.0, 3.0), FakeSeg(5.0, 8.0)]

    embeddings = np.random.randn(4, 256).astype(np.float32)
    subsegments = [
        (0.0, 1.2, 0),
        (0.6, 1.8, 0),
        (5.0, 6.2, 1),
        (5.6, 6.8, 1),
    ]
    mock_extract.return_value = (embeddings, subsegments)

    labels = np.array([0, 0, 1, 1])
    mock_cluster.return_value = (labels, None)

    # Need to patch the imports inside diarize()
    with patch("talekeeper.services.diarization.diarize.__module__", "talekeeper.services.diarization"):
        # Actually call the function directly — the mocks above patch at module level
        # but diarize() imports from diarize.vad and diarize.clustering inside the function.
        # We need to patch those properly.
        pass

    # Let's use a different approach — patch the actual imports
    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        segments = diarize(Path("test.wav"))

    assert len(segments) == 2
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[0].start_time == 0.0
    assert segments[1].speaker_label == "SPEAKER_01"


@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_passes_num_speakers(mock_extract):
    """diarize passes num_speakers to cluster_speakers()."""
    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    mock_run_vad = MagicMock(return_value=[FakeSeg(0.0, 3.0)])

    embeddings = np.random.randn(1, 256).astype(np.float32)
    mock_extract.return_value = (embeddings, [(0.0, 1.2, 0)])

    mock_cluster = MagicMock(return_value=(np.array([0]), None))

    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        diarize(Path("test.wav"), num_speakers=3)

    mock_cluster.assert_called_once()
    _, kwargs = mock_cluster.call_args
    assert kwargs["num_speakers"] == 3


# ---- Signature matching tests ----


@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_with_signatures_matches_above_threshold(mock_extract):
    """diarize_with_signatures matches speakers above similarity threshold."""
    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    mock_run_vad = MagicMock(return_value=[FakeSeg(0.0, 5.0), FakeSeg(5.0, 10.0)])

    # Two speakers, each with a distinct 256-dim embedding
    emb_speaker_0 = np.zeros(256, dtype=np.float32)
    emb_speaker_0[0] = 1.0  # points along dim 0
    emb_speaker_1 = np.zeros(256, dtype=np.float32)
    emb_speaker_1[1] = 1.0  # points along dim 1

    embeddings = np.stack([emb_speaker_0, emb_speaker_1])
    subsegments = [(0.0, 5.0, 0), (5.0, 10.0, 1)]
    mock_extract.return_value = (embeddings, subsegments)

    # Clustering assigns label 0 to first, label 1 to second
    labels = np.array([0, 1])
    mock_cluster = MagicMock(return_value=(labels, None))

    # Signatures matching the embeddings
    sig1 = np.zeros(256, dtype=np.float32)
    sig1[0] = 1.0  # matches speaker 0
    sig2 = np.zeros(256, dtype=np.float32)
    sig2[1] = 1.0  # matches speaker 1

    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        segments = diarize_with_signatures(
            Path("test.wav"),
            signatures=[(101, sig1), (102, sig2)],
            similarity_threshold=0.5,
        )

    labels_out = [s.speaker_label for s in segments]
    assert "roster_101" in labels_out
    assert "roster_102" in labels_out


@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_with_signatures_unknown_below_threshold(mock_extract):
    """diarize_with_signatures labels speakers below threshold as Unknown."""
    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    mock_run_vad = MagicMock(return_value=[FakeSeg(0.0, 5.0)])

    # Speaker embedding is orthogonal to signature
    emb = np.zeros(256, dtype=np.float32)
    emb[2] = 1.0  # points along dim 2

    embeddings = np.stack([emb])
    subsegments = [(0.0, 5.0, 0)]
    mock_extract.return_value = (embeddings, subsegments)

    labels = np.array([0])
    mock_cluster = MagicMock(return_value=(labels, None))

    sig1 = np.zeros(256, dtype=np.float32)
    sig1[0] = 1.0  # orthogonal to speaker

    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        segments = diarize_with_signatures(
            Path("test.wav"),
            signatures=[(101, sig1)],
            similarity_threshold=0.5,
        )

    assert all(s.speaker_label == "Unknown Speaker" for s in segments)


# ---- HF token resolution tests ----


async def test_resolve_hf_token_from_settings(db):
    """_resolve_hf_token reads and decrypts token from settings table."""
    from talekeeper.routers.settings import _encrypt

    encrypted = _encrypt("hf_test_token_123")
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('hf_token', ?)",
        (encrypted,),
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
