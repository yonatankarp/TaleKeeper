"""Tests for the transcription service."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from pathlib import Path

from talekeeper.services.transcription import (
    transcribe,
    transcribe_stream,
    transcribe_chunked,
    TranscriptSegment,
    ChunkProgress,
)
import talekeeper.services.transcription as mod


@dataclass
class FakeSegment:
    text: str
    start: float
    end: float


@patch("talekeeper.services.transcription.get_model")
def test_transcribe(mock_get_model):
    """transcribe returns a list of TranscriptSegment from WhisperModel output."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        [FakeSegment(" Hello ", 0.0, 1.0), FakeSegment(" World ", 1.0, 2.0)],
        None,
    )
    mock_get_model.return_value = mock_model

    result = transcribe(Path("test.wav"))

    assert len(result) == 2
    assert isinstance(result[0], TranscriptSegment)
    assert result[0].text == "Hello"
    assert result[0].start_time == 0.0
    assert result[0].end_time == 1.0
    assert result[1].text == "World"
    assert result[1].start_time == 1.0
    assert result[1].end_time == 2.0


@patch("talekeeper.services.transcription.get_model")
def test_transcribe_stream(mock_get_model):
    """transcribe_stream yields TranscriptSegment objects one at a time."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        [FakeSegment(" Hello ", 0.0, 1.0), FakeSegment(" World ", 1.0, 2.0)],
        None,
    )
    mock_get_model.return_value = mock_model

    segments = list(transcribe_stream(Path("test.wav")))

    assert len(segments) == 2
    assert all(isinstance(s, TranscriptSegment) for s in segments)
    assert segments[0].text == "Hello"
    assert segments[1].text == "World"


def test_get_model_caching():
    """get_model caches the WhisperModel and returns the same instance on repeat calls."""
    # Reset the module-level cache
    mod._model = None
    mod._model_size = None

    with patch("talekeeper.services.transcription.WhisperModel") as MockWhisper:
        mock_instance = MagicMock()
        MockWhisper.return_value = mock_instance

        m1 = mod.get_model("medium")
        m2 = mod.get_model("medium")

        assert m1 is m2
        MockWhisper.assert_called_once()

    # Clean up
    mod._model = None
    mod._model_size = None


def test_transcribe_chunked():
    """transcribe_chunked yields ChunkProgress first, then TranscriptSegments."""
    import pydub
    import talekeeper.services.audio as audio_mod

    # Mock pydub.AudioSegment to report short audio (single chunk)
    mock_audio = MagicMock()
    mock_audio.__len__ = MagicMock(return_value=60_000)

    orig_as = pydub.AudioSegment
    orig_split = audio_mod.split_audio_to_chunks

    try:
        pydub.AudioSegment = MagicMock()
        pydub.AudioSegment.from_file.return_value = mock_audio

        audio_mod.split_audio_to_chunks = MagicMock(
            return_value=iter([(0, Path("chunk.wav"), 0, 60_000)])
        )

        with patch("talekeeper.services.transcription.transcribe_stream") as mock_stream:
            mock_stream.return_value = iter([
                TranscriptSegment(text="Hello", start_time=0.0, end_time=1.0),
                TranscriptSegment(text="World", start_time=1.0, end_time=2.0),
            ])

            results = list(transcribe_chunked(Path("test.wav")))

        # First item should be ChunkProgress
        assert isinstance(results[0], ChunkProgress)
        assert results[0].chunk == 1
        assert results[0].total_chunks == 1

        # Remaining items should be TranscriptSegments
        transcript_results = [r for r in results if isinstance(r, TranscriptSegment)]
        assert len(transcript_results) == 2
        assert transcript_results[0].text == "Hello"
        assert transcript_results[1].text == "World"
    finally:
        pydub.AudioSegment = orig_as
        audio_mod.split_audio_to_chunks = orig_split
