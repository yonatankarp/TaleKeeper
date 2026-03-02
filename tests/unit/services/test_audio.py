"""Tests for the audio conversion and splitting service."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from talekeeper.services.audio import (
    audio_to_wav,
    webm_to_wav,
    split_audio_to_chunks,
    compute_primary_zone,
    DEFAULT_CHUNK_DURATION_MS,
    DEFAULT_OVERLAP_MS,
)


@patch("talekeeper.services.audio.AudioSegment")
def test_audio_to_wav(mock_audio_segment_cls, tmp_path):
    """audio_to_wav converts any audio to 16kHz mono WAV."""
    src = tmp_path / "input.mp3"
    src.touch()

    mock_audio = MagicMock()
    mock_audio.set_channels.return_value = mock_audio
    mock_audio.set_frame_rate.return_value = mock_audio
    mock_audio_segment_cls.from_file.return_value = mock_audio

    result = audio_to_wav(src)

    mock_audio_segment_cls.from_file.assert_called_once_with(str(src))
    mock_audio.set_channels.assert_called_once_with(1)
    mock_audio.set_frame_rate.assert_called_once_with(16000)
    mock_audio.export.assert_called_once_with(str(src.with_suffix(".wav")), format="wav")
    assert result == src.with_suffix(".wav")


@patch("talekeeper.services.audio.AudioSegment")
def test_webm_to_wav(mock_audio_segment_cls, tmp_path):
    """webm_to_wav converts WebM audio to 16kHz mono WAV."""
    src = tmp_path / "recording.webm"
    src.touch()

    mock_audio = MagicMock()
    mock_audio.set_channels.return_value = mock_audio
    mock_audio.set_frame_rate.return_value = mock_audio
    mock_audio_segment_cls.from_file.return_value = mock_audio

    result = webm_to_wav(src)

    mock_audio_segment_cls.from_file.assert_called_once_with(str(src), format="webm")
    mock_audio.set_channels.assert_called_once_with(1)
    mock_audio.set_frame_rate.assert_called_once_with(16000)
    mock_audio.export.assert_called_once_with(str(src.with_suffix(".wav")), format="wav")
    assert result == src.with_suffix(".wav")


@patch("talekeeper.services.audio.AudioSegment")
def test_split_audio_to_chunks_short_file(mock_audio_segment_cls, tmp_path):
    """Short audio (under chunk_duration_ms) yields a single chunk."""
    src = tmp_path / "short.wav"
    src.touch()

    # Duration shorter than one chunk (e.g. 60 seconds = 60000 ms)
    mock_audio = MagicMock()
    mock_audio.__len__ = MagicMock(return_value=60_000)
    mock_audio.set_channels.return_value = mock_audio
    mock_audio.set_frame_rate.return_value = mock_audio
    mock_audio_segment_cls.from_file.return_value = mock_audio

    chunks = list(split_audio_to_chunks(src))

    assert len(chunks) == 1
    chunk_index, wav_path, start_ms, end_ms = chunks[0]
    assert chunk_index == 0
    assert start_ms == 0
    assert end_ms == 60_000


def test_compute_primary_zone():
    """compute_primary_zone returns correct zones for first, middle, and last chunks."""
    overlap_ms = 30_000  # 30 seconds
    total_chunks = 3

    # First chunk (index=0): zone_start = chunk_start, zone_end = chunk_end - overlap/2
    zone_start, zone_end = compute_primary_zone(0, 0, 300_000, total_chunks, overlap_ms)
    assert zone_start == 0.0
    assert zone_end == (300_000 - 15_000) / 1000.0  # 285.0

    # Middle chunk (index=1): zone_start = start + overlap/2, zone_end = end - overlap/2
    zone_start, zone_end = compute_primary_zone(1, 270_000, 570_000, total_chunks, overlap_ms)
    assert zone_start == (270_000 + 15_000) / 1000.0  # 285.0
    assert zone_end == (570_000 - 15_000) / 1000.0  # 555.0

    # Last chunk (index=2): zone_start = start + overlap/2, zone_end = chunk_end
    zone_start, zone_end = compute_primary_zone(2, 540_000, 700_000, total_chunks, overlap_ms)
    assert zone_start == (540_000 + 15_000) / 1000.0  # 555.0
    assert zone_end == 700_000 / 1000.0  # 700.0
