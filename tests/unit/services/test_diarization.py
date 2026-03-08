"""Tests for the speaker diarization service (diarize library)."""

import pytest
import soundfile as sf
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import numpy as np

from talekeeper.services.diarization import (
    _merge_segments,
    _build_segments_from_labels,
    _compress_dynamic_range,
    _extract_embeddings_with_progress,
    _extract_fine_stride_embeddings,
    _find_speaker_change_points,
    _flag_overlap_subsegments,
    _normalize_audio_file,
    _normalize_segment_audio,
    _split_segment_at_changes,
    _split_transcript_segments,
    _detect_speaker_changes,
    align_speakers_with_transcript,
    diarize,
    diarize_with_signatures,
    _resolve_hf_token,
    unload_models,
    SpeakerSegment,
    CHANGE_DETECTION_WINDOW,
    CHANGE_DETECTION_STEP,
    MIN_SEGMENT_DURATION,
)


# ---- _compress_dynamic_range tests ----


def test_compress_dynamic_range_boosts_quiet_sections():
    """_compress_dynamic_range boosts quiet sections independently of loud ones."""
    sr = 16000
    # 1s quiet (RMS ~0.01), then 1s loud (RMS ~0.3)
    quiet = np.full(sr, 0.01, dtype=np.float64)
    loud = np.full(sr, 0.3, dtype=np.float64)
    audio = np.concatenate([quiet, loud])

    result = _compress_dynamic_range(audio, sr, target_rms=0.1)

    # Quiet section should be boosted significantly
    quiet_rms_before = float(np.sqrt(np.mean(quiet ** 2)))
    quiet_rms_after = float(np.sqrt(np.mean(result[:sr] ** 2)))
    assert quiet_rms_after > quiet_rms_before * 2  # at least 2x boost

    # Loud section should be reduced
    loud_rms_after = float(np.sqrt(np.mean(result[sr:] ** 2)))
    assert loud_rms_after < 0.3


def test_compress_dynamic_range_silent_passthrough():
    """_compress_dynamic_range doesn't amplify near-silent audio."""
    sr = 16000
    audio = np.full(sr, 1e-8, dtype=np.float64)
    result = _compress_dynamic_range(audio, sr)

    # Should remain very quiet (scale=1.0 for silent windows)
    result_rms = float(np.sqrt(np.mean(result ** 2)))
    assert result_rms < 0.001


# ---- _normalize_audio_file tests ----


def test_normalize_audio_file_returns_temp_path(tmp_path):
    """_normalize_audio_file writes a compressed WAV and returns its path."""
    sr = 16000
    audio = np.full(sr, 0.01, dtype=np.float64)  # 1s quiet
    src = tmp_path / "quiet.wav"
    sf.write(str(src), audio, sr)

    norm_path = _normalize_audio_file(src)
    try:
        assert norm_path.exists()
        assert norm_path != src  # should be a temp file, not the original

        data, _ = sf.read(str(norm_path))
        assert len(data) == sr  # same length
    finally:
        norm_path.unlink(missing_ok=True)


# ---- _normalize_segment_audio tests ----


def test_normalize_segment_audio_adjusts_rms():
    """_normalize_segment_audio scales audio to target RMS."""
    # Create a signal with known RMS (~0.05)
    audio = np.full(1600, 0.05, dtype=np.float64)
    result = _normalize_segment_audio(audio, target_rms=0.1)

    result_rms = float(np.sqrt(np.mean(result ** 2)))
    assert abs(result_rms - 0.1) < 0.001


def test_normalize_segment_audio_silent_passthrough():
    """_normalize_segment_audio passes near-silent audio through unchanged."""
    audio = np.full(1600, 1e-8, dtype=np.float64)
    result = _normalize_segment_audio(audio)

    np.testing.assert_array_equal(result, audio)


def test_normalize_segment_audio_clips():
    """_normalize_segment_audio clips scaled values to [-1, 1]."""
    # Large amplitude that, after scaling to target_rms=0.1, would exceed 1.0
    audio = np.array([5.0, -5.0, 5.0, -5.0], dtype=np.float64)
    result = _normalize_segment_audio(audio, target_rms=0.5)

    assert float(np.max(result)) <= 1.0
    assert float(np.min(result)) >= -1.0


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


# ---- _flag_overlap_subsegments tests ----


def test_flag_overlap_subsegments_ambiguous_embedding_flagged():
    """_flag_overlap_subsegments flags embeddings equidistant between two clusters.

    Uses 5 clear embeddings per cluster so the single ambiguous embedding doesn't
    dominate its cluster's centroid, ensuring the ratio test fires correctly.
    """
    emb0 = np.zeros(256, dtype=np.float32)
    emb0[0] = 1.0  # cluster 0 direction: dim 0

    emb1 = np.zeros(256, dtype=np.float32)
    emb1[1] = 1.0  # cluster 1 direction: dim 1

    # Ambiguous: 45 degrees between both clusters
    emb_ambiguous = np.zeros(256, dtype=np.float32)
    emb_ambiguous[0] = 1.0
    emb_ambiguous[1] = 1.0

    # 5 clear embeddings for each cluster, 1 ambiguous assigned to cluster 0
    embeddings = np.vstack([
        np.stack([emb0] * 5),
        np.stack([emb1] * 5),
        emb_ambiguous.reshape(1, -1),
    ])
    labels = np.array([0] * 5 + [1] * 5 + [0])

    mask = _flag_overlap_subsegments(embeddings, labels, threshold=0.85)

    assert not np.any(mask[:5])   # clear cluster 0 embeddings — not flagged
    assert not np.any(mask[5:10]) # clear cluster 1 embeddings — not flagged
    assert mask[10]               # ambiguous embedding — flagged


def test_flag_overlap_subsegments_clear_embedding_not_flagged():
    """_flag_overlap_subsegments does not flag clearly separated embeddings."""
    emb0 = np.zeros(256, dtype=np.float32)
    emb0[0] = 1.0
    emb1 = np.zeros(256, dtype=np.float32)
    emb1[1] = 1.0

    embeddings = np.stack([emb0, emb1])
    labels = np.array([0, 1])

    mask = _flag_overlap_subsegments(embeddings, labels, threshold=0.85)

    assert not mask[0]
    assert not mask[1]


def test_flag_overlap_subsegments_single_cluster_empty_mask():
    """_flag_overlap_subsegments returns all-False mask for single-cluster input."""
    embeddings = np.random.randn(4, 256).astype(np.float32)
    labels = np.array([0, 0, 0, 0])

    mask = _flag_overlap_subsegments(embeddings, labels, threshold=0.85)

    assert mask.shape == (4,)
    assert not np.any(mask)


def test_flag_overlap_subsegments_empty_input():
    """_flag_overlap_subsegments handles empty input without error."""
    mask = _flag_overlap_subsegments(
        np.empty((0, 256), dtype=np.float32), np.array([]), threshold=0.85
    )
    assert mask.shape == (0,)


# ---- _build_segments_from_labels with overlap mask ----


def test_build_segments_from_labels_with_overlap_mask():
    """_build_segments_from_labels assigns [crosstalk] label to masked subsegments."""
    speech_segments = [MagicMock(start=0.0, end=6.0)]
    subsegments = [
        (0.0, 1.2, 0),
        (1.2, 2.4, 0),
        (2.4, 3.6, 0),
    ]
    labels = np.array([0, 1, 0])
    overlap_mask = np.array([False, True, False])

    segments = _build_segments_from_labels(speech_segments, subsegments, labels, overlap_mask)

    labels_out = [s.speaker_label for s in segments]
    assert "SPEAKER_00" in labels_out
    assert "[crosstalk]" in labels_out
    # [crosstalk] segment spans 1.2-2.4
    crosstalk_seg = next(s for s in segments if s.speaker_label == "[crosstalk]")
    assert crosstalk_seg.start_time == 1.2
    assert crosstalk_seg.end_time == 2.4


# ---- align_speakers_with_transcript with [crosstalk] ----


def test_align_speakers_with_transcript_crosstalk_segment():
    """Segment aligned to [crosstalk] gets is_overlap=1 and no speaker_label assigned."""
    speaker_segs = [
        SpeakerSegment("[crosstalk]", 2.0, 4.0),
        SpeakerSegment("SPEAKER_00", 4.0, 8.0),
    ]
    transcript_segs = [
        {"id": 1, "start_time": 2.5, "end_time": 3.5, "text": "mumble"},
        {"id": 2, "start_time": 5.0, "end_time": 7.0, "text": "hello"},
    ]

    aligned = align_speakers_with_transcript(speaker_segs, transcript_segs)

    overlap_seg = next(s for s in aligned if s["id"] == 1)
    clear_seg = next(s for s in aligned if s["id"] == 2)

    assert overlap_seg["is_overlap"] == 1
    assert overlap_seg.get("speaker_label") is None
    assert clear_seg["is_overlap"] == 0
    assert clear_seg["speaker_label"] == "SPEAKER_00"


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


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes", side_effect=lambda path, segs, cb=None: segs)
@patch("talekeeper.services.diarization.cluster_speakers", create=True)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
@patch("talekeeper.services.diarization.run_vad", create=True)
def test_diarize(mock_run_vad, mock_extract, mock_cluster, mock_detect, mock_norm):
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


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes", side_effect=lambda path, segs, cb=None: segs)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_passes_num_speakers(mock_extract, mock_detect, mock_norm):
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


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes", side_effect=lambda path, segs, cb=None: segs)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_with_signatures_matches_above_threshold(mock_extract, mock_detect, mock_norm):
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


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes", side_effect=lambda path, segs, cb=None: segs)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_with_signatures_unknown_below_threshold(mock_extract, mock_detect, mock_norm):
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


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes", side_effect=lambda path, segs, cb=None: segs)
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_with_signatures_no_double_assignment(mock_extract, mock_detect, mock_norm):
    """Hungarian algorithm prevents two clusters from matching the same signature.

    Greedy argmax would assign both cluster 0 and cluster 1 to roster_101 (since both
    score higher against sig1 than sig2). Hungarian finds the globally optimal 1:1
    assignment so cluster 1 is correctly matched to roster_102.
    """
    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    mock_run_vad = MagicMock(return_value=[FakeSeg(0.0, 5.0), FakeSeg(5.0, 10.0)])

    # sig1 points along dim 0, sig2 along dim 1
    sig1 = np.zeros(256, dtype=np.float32)
    sig1[0] = 1.0
    sig2 = np.zeros(256, dtype=np.float32)
    sig2[1] = 1.0

    # cluster 0: very close to sig1 (greedy picks sig1 ✓)
    # cluster 1: slightly closer to sig1 than sig2, but sig2 is a much better overall fit
    # Cosine sims: cluster0→sig1=0.99, cluster0→sig2=0.1, cluster1→sig1=0.8, cluster1→sig2=0.9
    emb0 = np.zeros(256, dtype=np.float32)
    emb0[0] = 0.99
    emb0[1] = 0.1
    norm0 = np.linalg.norm(emb0)
    emb0 /= norm0

    emb1 = np.zeros(256, dtype=np.float32)
    emb1[0] = 0.8
    emb1[1] = 0.9
    norm1 = np.linalg.norm(emb1)
    emb1 /= norm1

    embeddings = np.stack([emb0, emb1])
    subsegments = [(0.0, 5.0, 0), (5.0, 10.0, 1)]
    mock_extract.return_value = (embeddings, subsegments)

    labels = np.array([0, 1])
    mock_cluster = MagicMock(return_value=(labels, None))

    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        segments = diarize_with_signatures(
            Path("test.wav"),
            signatures=[(101, sig1), (102, sig2)],
            similarity_threshold=0.5,
        )

    labels_out = {s.speaker_label for s in segments}
    # Both speakers should be matched — no double assignment leaves one as Unknown
    assert "roster_101" in labels_out
    assert "roster_102" in labels_out
    assert "Unknown Speaker" not in labels_out


# ---- Speaker change detection tests ----


@patch("talekeeper.services.diarization.sf")
@patch("talekeeper.services.diarization.wespeakerruntime", create=True)
def test_extract_fine_stride_embeddings(mock_wespeaker_module, mock_sf):
    """_extract_fine_stride_embeddings produces correct number of windows and embedding shape."""
    # 5 seconds of audio at 16kHz
    audio_data = np.zeros(80000, dtype=np.float32)
    sr = 16000

    mock_speaker_instance = MagicMock()
    mock_speaker_instance.extract_embedding.return_value = np.random.randn(1, 256).astype(np.float32)
    mock_sf.write = MagicMock()

    with patch("wespeakerruntime.Speaker", return_value=mock_speaker_instance):
        embeddings, timestamps = _extract_fine_stride_embeddings(audio_data, sr, 0.0, 5.0)

    # Window=0.4s, step=0.2s, seg=5.0s → windows at 0.0, 0.2, 0.4, ..., 4.6
    # Number of windows: floor((5.0 - 0.4) / 0.2) + 1 = 23
    assert embeddings.shape[1] == 256
    assert embeddings.shape[0] == len(timestamps)
    assert embeddings.shape[0] > 0
    # Each timestamp should be the center of a 0.4s window
    for ts in timestamps:
        assert ts >= 0.0
        assert ts <= 5.0


def test_find_speaker_change_points_detects_transitions():
    """_find_speaker_change_points detects change points at speaker transitions."""
    # Create embeddings: 5 from speaker A (dim 0), 5 from speaker B (dim 1)
    emb_a = np.zeros(256, dtype=np.float32)
    emb_a[0] = 1.0
    emb_b = np.zeros(256, dtype=np.float32)
    emb_b[1] = 1.0

    # 10 embeddings: 5xA then 5xB
    embeddings = np.stack([emb_a] * 5 + [emb_b] * 5)
    timestamps = [0.3 * i + 0.3 for i in range(10)]

    change_times = _find_speaker_change_points(embeddings, timestamps)

    # Should detect exactly one change point between index 4 and 5
    assert len(change_times) == 1
    # Change should be between timestamp[4] and timestamp[5]
    expected = (timestamps[4] + timestamps[5]) / 2.0
    assert abs(change_times[0] - expected) < 0.01


def test_find_speaker_change_points_single_speaker():
    """_find_speaker_change_points detects no changes for single-speaker embeddings."""
    emb = np.zeros(256, dtype=np.float32)
    emb[0] = 1.0
    # Add small noise so embeddings aren't identical (which would cause NaN cosine distance)
    embeddings = np.stack([emb + np.random.randn(256) * 0.01 for _ in range(10)])
    timestamps = [0.3 * i + 0.3 for i in range(10)]

    change_times = _find_speaker_change_points(embeddings, timestamps)

    assert len(change_times) == 0


def test_split_segment_at_changes():
    """_split_segment_at_changes splits correctly and merges short sub-segments."""
    # Segment from 0.0 to 10.0, split at 3.0 and 7.0
    sub_segs = _split_segment_at_changes(0.0, 10.0, [3.0, 7.0])

    assert len(sub_segs) == 3
    assert sub_segs[0] == (0.0, 3.0)
    assert sub_segs[1] == (3.0, 7.0)
    assert sub_segs[2] == (7.0, 10.0)


def test_split_segment_at_changes_merges_short():
    """_split_segment_at_changes merges sub-segments shorter than MIN_SEGMENT_DURATION."""
    # Split at 0.2 would create a 0.2s sub-segment — should merge with neighbor
    sub_segs = _split_segment_at_changes(0.0, 5.0, [0.2])

    # The 0.0-0.2 segment is too short and merges with 0.2-5.0
    assert len(sub_segs) == 1
    assert sub_segs[0] == (0.0, 5.0)


def test_split_segment_at_changes_empty():
    """_split_segment_at_changes returns original segment when no change points."""
    sub_segs = _split_segment_at_changes(0.0, 10.0, [])

    assert len(sub_segs) == 1
    assert sub_segs[0] == (0.0, 10.0)


@patch("talekeeper.services.diarization._extract_fine_stride_embeddings")
@patch("talekeeper.services.diarization.sf")
def test_detect_speaker_changes(mock_sf, mock_fine_embed):
    """_detect_speaker_changes processes long segments and passes short ones through."""
    mock_sf.read.return_value = (np.zeros(160000), 16000)

    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    # One short segment (0.7s < MIN_CHANGE_DETECTION_DURATION=2.0s) and one long segment (5.0s)
    short_seg = FakeSeg(0.0, 0.7)
    long_seg = FakeSeg(2.0, 7.0)

    # For the long segment, return embeddings with a speaker change
    emb_a = np.zeros(256, dtype=np.float32)
    emb_a[0] = 1.0
    emb_b = np.zeros(256, dtype=np.float32)
    emb_b[1] = 1.0
    embeddings = np.stack([emb_a] * 5 + [emb_b] * 5)
    timestamps = [2.0 + 0.3 * i + 0.3 for i in range(10)]
    mock_fine_embed.return_value = (embeddings, timestamps)

    progress_calls = []
    def progress_cb(stage, detail):
        progress_calls.append((stage, detail))

    result = _detect_speaker_changes(Path("test.wav"), [short_seg, long_seg], progress_cb)

    # Short segment should pass through unchanged
    assert result[0] is short_seg
    # Long segment should be split (at least 2 sub-segments)
    assert len(result) >= 3  # 1 short + at least 2 from split
    # Progress should have start and done events
    stages = [c[0] for c in progress_calls]
    assert "change_detection_start" in stages
    assert "change_detection_done" in stages


@patch("talekeeper.services.diarization._normalize_audio_file", side_effect=lambda p: p)
@patch("talekeeper.services.diarization._detect_speaker_changes")
@patch("talekeeper.services.diarization._extract_embeddings_with_progress")
def test_diarize_calls_detect_speaker_changes(mock_extract, mock_detect, mock_norm):
    """diarize() calls _detect_speaker_changes() in the pipeline."""
    class FakeSeg:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    vad_segs = [FakeSeg(0.0, 3.0)]
    mock_run_vad = MagicMock(return_value=vad_segs)

    # _detect_speaker_changes returns segments unchanged
    mock_detect.return_value = vad_segs

    embeddings = np.random.randn(1, 256).astype(np.float32)
    mock_extract.return_value = (embeddings, [(0.0, 1.2, 0)])

    mock_cluster = MagicMock(return_value=(np.array([0]), None))

    with patch.dict("sys.modules", {
        "diarize.vad": MagicMock(run_vad=mock_run_vad),
        "diarize.clustering": MagicMock(cluster_speakers=mock_cluster),
    }):
        diarize(Path("test.wav"))

    mock_detect.assert_called_once()


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


# ---- _split_transcript_segments tests ----


def _make_t_seg(id, start, end, text="hello world foo bar baz"):
    return {"id": id, "session_id": 1, "text": text, "start_time": start, "end_time": end}


def test_split_transcript_segments_single_speaker_unchanged():
    """_split_transcript_segments leaves segment unchanged when only one speaker overlaps."""
    t_segs = [_make_t_seg(1, 0.0, 5.0)]
    speaker_segs = [SpeakerSegment("SPEAKER_00", 0.0, 5.0)]

    result = _split_transcript_segments(t_segs, speaker_segs)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["start_time"] == 0.0
    assert result[0]["end_time"] == 5.0


def test_split_transcript_segments_two_speakers():
    """_split_transcript_segments splits at a single speaker boundary."""
    # 12s segment, speaker change at 6s → each child is exactly MIN_SPLIT_CHILD_DURATION
    t_segs = [_make_t_seg(1, 0.0, 12.0, "a b c d e f g h i j k l")]
    speaker_segs = [
        SpeakerSegment("SPEAKER_00", 0.0, 6.0),
        SpeakerSegment("SPEAKER_01", 6.0, 12.0),
    ]

    result = _split_transcript_segments(t_segs, speaker_segs)

    assert len(result) == 2
    # Both children get id=None and point to original
    assert result[0]["id"] is None
    assert result[0]["parent_segment_id"] == 1
    assert result[0]["start_time"] == 0.0
    assert result[0]["end_time"] == 6.0
    assert result[1]["id"] is None
    assert result[1]["parent_segment_id"] == 1
    assert result[1]["start_time"] == 6.0
    assert result[1]["end_time"] == 12.0
    assert result[1]["session_id"] == 1
    # Text split: 50%/50% of 12 words = 6 words each
    assert len(result[0]["text"].split()) == 6
    assert len(result[1]["text"].split()) == 6
    # All words preserved
    all_words = result[0]["text"].split() + result[1]["text"].split()
    assert all_words == "a b c d e f g h i j k l".split()


def test_split_transcript_segments_three_speakers():
    """_split_transcript_segments splits at two speaker boundaries."""
    # 15s segment, changes at 5s and 10s → each child is exactly MIN_SPLIT_CHILD_DURATION
    t_segs = [_make_t_seg(1, 0.0, 15.0, "a b c d e f g h i j k l m n o")]
    speaker_segs = [
        SpeakerSegment("SPEAKER_00", 0.0, 5.0),
        SpeakerSegment("SPEAKER_01", 5.0, 10.0),
        SpeakerSegment("SPEAKER_02", 10.0, 15.0),
    ]

    result = _split_transcript_segments(t_segs, speaker_segs)

    assert len(result) == 3
    # All children point to original
    for sub in result:
        assert sub["id"] is None
        assert sub["parent_segment_id"] == 1
    assert result[0]["start_time"] == 0.0
    assert result[1]["start_time"] == 5.0
    assert result[2]["start_time"] == 10.0
    # Each sub gets 5 words (equal thirds of 15 words)
    for sub in result:
        assert len(sub["text"].split()) == 5


def test_split_transcript_segments_short_boundary_not_split():
    """_split_transcript_segments skips split points that leave children < MIN_SPLIT_CHILD_DURATION."""
    # 10s segment, change at 4s → left child would be 4s < MIN_SPLIT_CHILD_DURATION=5s → no split
    t_segs = [_make_t_seg(1, 0.0, 10.0, "a b c d e f g h i j")]
    speaker_segs = [
        SpeakerSegment("SPEAKER_00", 0.0, 4.0),
        SpeakerSegment("SPEAKER_01", 4.0, 10.0),
    ]

    result = _split_transcript_segments(t_segs, speaker_segs)

    # 4s < MIN_SPLIT_CHILD_DURATION=5s → not a valid split point → original unchanged
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_split_transcript_segments_crosstalk_split_then_align():
    """Crosstalk diarization segment: after split+align the crosstalk sub gets is_overlap=1."""
    # 12s segment, change at 6s → each child is exactly MIN_SPLIT_CHILD_DURATION
    t_segs = [_make_t_seg(1, 0.0, 12.0, "a b c d e f g h i j k l")]
    speaker_segs = [
        SpeakerSegment("SPEAKER_00", 0.0, 6.0),
        SpeakerSegment("[crosstalk]", 6.0, 12.0),
    ]

    split_segs = _split_transcript_segments(t_segs, speaker_segs)
    assert len(split_segs) == 2

    aligned = align_speakers_with_transcript(speaker_segs, split_segs)

    speaker_sub = next(s for s in aligned if s["start_time"] < 6.0)
    crosstalk_sub = next(s for s in aligned if s["start_time"] >= 6.0)

    assert speaker_sub.get("speaker_label") == "SPEAKER_00"
    assert speaker_sub.get("is_overlap", 0) == 0
    assert crosstalk_sub.get("is_overlap") == 1
    assert crosstalk_sub.get("speaker_label") is None
