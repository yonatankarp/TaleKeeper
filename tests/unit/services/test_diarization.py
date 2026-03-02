"""Tests for the speaker diarization service."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import numpy as np

from talekeeper.services.diarization import (
    _merge_segments,
    align_speakers_with_transcript,
    diarize,
    SpeakerSegment,
)


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


@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization._extract_windowed_embeddings")
@patch("talekeeper.services.diarization._cluster_embeddings")
def test_diarize(mock_cluster, mock_extract, mock_load):
    """diarize runs the full pipeline and returns merged speaker segments."""
    mock_load.return_value = MagicMock()
    mock_extract.return_value = (
        np.zeros((3, 192)),
        [(0.0, 1.5), (1.5, 3.0), (3.0, 4.5)],
    )
    # Labels: two windows are speaker 0, one is speaker 1
    mock_cluster.return_value = np.array([0, 0, 1])

    segments = diarize(Path("test.wav"))

    # Segments 0 and 1 share label SPEAKER_00 and should be merged
    assert len(segments) == 2
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 3.0
    assert segments[1].speaker_label == "SPEAKER_01"
    assert segments[1].start_time == 3.0
    assert segments[1].end_time == 4.5


@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization._extract_windowed_embeddings")
@patch("sklearn.cluster.AgglomerativeClustering")
def test_diarize_with_num_speakers(mock_agglo_cls, mock_extract, mock_load):
    """When num_speakers is provided, AgglomerativeClustering uses n_clusters."""
    mock_load.return_value = MagicMock()
    mock_extract.return_value = (
        np.zeros((4, 192)),
        [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0)],
    )

    mock_instance = MagicMock()
    mock_instance.fit_predict.return_value = np.array([0, 0, 1, 1])
    mock_agglo_cls.return_value = mock_instance

    segments = diarize("fake.wav", num_speakers=2)

    # 4 windows, but adjacent same-speaker windows get merged -> 2 segments
    assert len(segments) == 2
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[1].speaker_label == "SPEAKER_01"

    # Verify AgglomerativeClustering was called with n_clusters=2
    mock_agglo_cls.assert_called_once_with(
        n_clusters=2,
        metric="cosine",
        linkage="average",
    )


@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization._extract_windowed_embeddings")
@patch("sklearn.cluster.AgglomerativeClustering")
def test_diarize_without_num_speakers(mock_agglo_cls, mock_extract, mock_load):
    """When num_speakers is None, AgglomerativeClustering uses distance_threshold."""
    mock_load.return_value = MagicMock()
    mock_extract.return_value = (
        np.zeros((3, 192)),
        [(0.0, 1.5), (1.5, 3.0), (3.0, 4.5)],
    )

    mock_instance = MagicMock()
    mock_instance.fit_predict.return_value = np.array([0, 1, 0])
    mock_agglo_cls.return_value = mock_instance

    segments = diarize("fake.wav")

    # 3 windows with labels [0, 1, 0] — no adjacent merges possible -> 3 segments
    assert len(segments) == 3
    assert segments[0].speaker_label == "SPEAKER_00"
    assert segments[1].speaker_label == "SPEAKER_01"
    assert segments[2].speaker_label == "SPEAKER_00"

    # Verify AgglomerativeClustering was called with distance_threshold (not n_clusters)
    from talekeeper.services.diarization import COSINE_DISTANCE_THRESHOLD

    mock_agglo_cls.assert_called_once_with(
        n_clusters=None,
        distance_threshold=COSINE_DISTANCE_THRESHOLD,
        metric="cosine",
        linkage="average",
    )
